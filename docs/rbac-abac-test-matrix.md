# RBAC/ABAC Test Matrix

Bu dokuman, canli sistemde rol + proje atamasi + modul yetkisi dogrulamasini tekrar edilebilir sekilde takip etmek icindir.

## Kapsam

- Merkezi middleware: `enforce_module_rbac_abac`
- Endpoint seviyesinde kontrol: `module-data` CRUD + `desk/search`
- Proje kapsam kontrolu: aktif proje / management scope
- Pasif proje write engeli: `block_writes_for_passive_project`

## Roller ve Beklenen Modul Erisimi

Varsayilan (override yokken):

- `superadmin`: tum moduller (management mode kisitlari haric)
- `tenant_admin`, `tenant_manager`, `superadmin_staff`: tum moduller
- `driver`, `greeter`, `supplier_admin`: `transfer`
- `participant`: `toplanti`, `duyurular`
- `interpreter`, `supertranslator`: `toplanti`, `tercuman`

## Kritik Senaryolar

1. Auth yokken `GET /module-data?module_name=kayit`: `401`
2. `driver` ile `GET /transfers`: `200`
3. `driver` ile `GET /desk/search?q=x`: `403`
4. `driver` ile `GET /module-data?module_name=kayit`: `403`
5. `tenant_manager` + aktif proje + modul aktif: ilgili moduller `200`
6. Pasif projede write (`POST/PUT/PATCH/DELETE`): `403`
7. `superadmin` management mode: proje secmeden sadece izinli yonetim akislarina erisim

## Otomatik Smoke Test

Script:

- `tools/rbac_abac_smoke.ps1`

Calistirma:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\rbac_abac_smoke.ps1
```

Script adimlari:

1. `/health` kontrolu
2. `superadmin` login
3. authsuz endpoint kontrolu (`401`)
4. aktif proje secimi
5. gecici `driver` olusturma
6. `driver` login + aktif proje set
7. `transfer` erisimi (`200`)
8. `desk` ve `kayit` engeli (`403`)
9. gecici kullanici deaktif etme

## Manuel Regression Checklist

1. Rol degisince `visible_modules` aninda guncelleniyor mu?
2. `UserProjectAccess.is_denied=true` oldugunda proje erisimi kapaniyor mu?
3. `ProjectModule.enabled=false` oldugunda modul kapaniyor mu?
4. Pasif proje write engeli butun write endpointlerde calisiyor mu?
5. Audit log kayitlari (`ops_events`) olusuyor mu?

