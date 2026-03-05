param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$AdminUser = "CreaTRO",
  [string]$AdminPass = "Micetro25+."
)

$ErrorActionPreference = "Stop"

function Invoke-Api {
  param(
    [Parameter(Mandatory = $true)][string]$Method,
    [Parameter(Mandatory = $true)][string]$Path,
    [hashtable]$Headers,
    $Body
  )
  $uri = "$BaseUrl$Path"
  $args = @{
    Uri = $uri
    Method = $Method
    UseBasicParsing = $true
    ErrorAction = "Stop"
  }
  if ($Headers) { $args.Headers = $Headers }
  if ($null -ne $Body) {
    $args.ContentType = "application/json"
    $args.Body = ($Body | ConvertTo-Json -Depth 8 -Compress)
  }
  try {
    $res = Invoke-WebRequest @args
    $json = $null
    if ($res.Content) { $json = $res.Content | ConvertFrom-Json }
    return [pscustomobject]@{ Status = [int]$res.StatusCode; Data = $json; Raw = $res.Content }
  } catch {
    $status = 0
    $raw = ""
    $errMsg = $_.Exception.Message
    if ($_.Exception.Response) {
      $status = [int]$_.Exception.Response.StatusCode.value__
      $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
      $raw = $reader.ReadToEnd()
      $reader.Close()
    }
    $json = $null
    if ($raw) {
      try { $json = $raw | ConvertFrom-Json } catch { $json = $null }
    }
    if (-not $raw -and $errMsg) { $raw = $errMsg }
    return [pscustomobject]@{ Status = $status; Data = $json; Raw = $raw }
  }
}

function Assert-Status {
  param(
    [string]$Name,
    [int[]]$Expected,
    $Result
  )
  if ($Expected -contains [int]$Result.Status) {
    Write-Host "[PASS] $Name => $($Result.Status)"
    return $true
  }
  Write-Host "[FAIL] $Name => got $($Result.Status), expected $($Expected -join ',')" -ForegroundColor Red
  if ($Result.Raw) { Write-Host "       body: $($Result.Raw)" }
  return $false
}

$allPassed = $true
$createdUserId = $null
$createdUsername = $null

# 1) Health
$health = Invoke-Api -Method "GET" -Path "/health"
$allPassed = (Assert-Status -Name "Health" -Expected @(200) -Result $health) -and $allPassed

# 2) Admin login
$login = Invoke-Api -Method "POST" -Path "/auth/login" -Body @{
  username = $AdminUser
  password = $AdminPass
}
$allPassed = (Assert-Status -Name "Admin login" -Expected @(200) -Result $login) -and $allPassed
if ($login.Status -ne 200 -or -not $login.Data.access_token) {
  Write-Host "Admin login failed, cannot continue." -ForegroundColor Red
  exit 1
}
$adminToken = [string]$login.Data.access_token
$adminHeaders = @{ Authorization = "Bearer $adminToken" }

# 3) Unauthorized check
$unauthModule = Invoke-Api -Method "GET" -Path "/module-data?module_name=kayit&limit=1"
$allPassed = (Assert-Status -Name "Module data without token" -Expected @(401) -Result $unauthModule) -and $allPassed

# 4) Pick active project
$projects = Invoke-Api -Method "GET" -Path "/projects" -Headers $adminHeaders
$allPassed = (Assert-Status -Name "List projects (admin)" -Expected @(200) -Result $projects) -and $allPassed
if ($projects.Status -ne 200 -or -not $projects.Data) {
  Write-Host "Project list unavailable, cannot continue." -ForegroundColor Red
  exit 1
}
$activeProject = @($projects.Data | Where-Object { $_.is_active -eq $true } | Select-Object -First 1)
if (-not $activeProject -or -not $activeProject[0]) {
  Write-Host "No active project found, cannot continue." -ForegroundColor Red
  exit 1
}
$projectId = [int]$activeProject[0].id
$tenantId = [int]$activeProject[0].tenant_id
Write-Host "Using project_id=$projectId tenant_id=$tenantId"

# 5) Create temporary driver user
$stamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$createdUsername = "rbac_driver_$stamp"
$driverPass = "TmpDriver!123"
$createUser = Invoke-Api -Method "POST" -Path "/users" -Headers $adminHeaders -Body @{
  username = $createdUsername
  password = $driverPass
  role = "driver"
  tenant_id = $tenantId
}
$allPassed = (Assert-Status -Name "Create temp driver" -Expected @(200) -Result $createUser) -and $allPassed
if ($createUser.Status -ne 200 -or -not $createUser.Data.id) {
  Write-Host "Driver create failed, cannot continue." -ForegroundColor Red
  exit 1
}
$createdUserId = [int]$createUser.Data.id

# 6) Driver login + active project
$driverLogin = Invoke-Api -Method "POST" -Path "/auth/login" -Body @{
  username = $createdUsername
  password = $driverPass
}
$allPassed = (Assert-Status -Name "Driver login" -Expected @(200) -Result $driverLogin) -and $allPassed
if ($driverLogin.Status -ne 200 -or -not $driverLogin.Data.access_token) {
  Write-Host "Driver login failed, cannot continue." -ForegroundColor Red
  exit 1
}
$driverToken = [string]$driverLogin.Data.access_token
$driverHeaders = @{ Authorization = "Bearer $driverToken" }

$setProject = Invoke-Api -Method "PUT" -Path "/auth/active-project" -Headers $driverHeaders -Body @{ project_id = $projectId }
$allPassed = (Assert-Status -Name "Driver set active project" -Expected @(200) -Result $setProject) -and $allPassed

# 7) Driver allowed in transfer
$driverTransfers = Invoke-Api -Method "GET" -Path "/transfers?limit=1" -Headers $driverHeaders
$allPassed = (Assert-Status -Name "Driver transfers access" -Expected @(200) -Result $driverTransfers) -and $allPassed

# 8) Driver blocked in kayit/desk
$driverDesk = Invoke-Api -Method "GET" -Path "/desk/search?q=test&limit=1" -Headers $driverHeaders
$allPassed = (Assert-Status -Name "Driver desk blocked" -Expected @(403) -Result $driverDesk) -and $allPassed

$driverModuleData = Invoke-Api -Method "GET" -Path "/module-data?module_name=kayit&limit=1" -Headers $driverHeaders
$allPassed = (Assert-Status -Name "Driver module-data kayit blocked" -Expected @(403) -Result $driverModuleData) -and $allPassed

# 9) Cleanup temporary user
if ($createdUserId) {
  $deactivate = Invoke-Api -Method "PUT" -Path "/users/$createdUserId" -Headers $adminHeaders -Body @{ is_active = $false }
  $allPassed = (Assert-Status -Name "Deactivate temp driver" -Expected @(200) -Result $deactivate) -and $allPassed
}

if ($allPassed) {
  Write-Host ""
  Write-Host "RBAC/ABAC smoke test: PASSED" -ForegroundColor Green
  exit 0
}

Write-Host ""
Write-Host "RBAC/ABAC smoke test: FAILED" -ForegroundColor Red
exit 2
