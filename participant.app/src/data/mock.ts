import coftTempLogo from "@/assets/brand/Ontur.png";
import vehicleHero from "@/assets/brand/vehicle-hero.jpg";
import type {
  AppConfig,
  CoreBootstrapPayload,
  CoreCommandResult,
  DynamicQrPolicy,
  Expense,
  FileItem,
  Job,
  Operation,
  PassengerMarkCommand,
  QrArrivalEvent,
  QrResultVisibilityPolicy,
  Role,
  ShellProfile,
  StageActionCommand,
  VisibilityOverride,
} from "./types";

const vehicleCompanyDefaults = {
  passengerPhoneVisible: false,
  smsAllowed: false,
  whatsappAllowed: false,
};

const sharedDriverTabs = [
  { key: "home", label: "Ana Sayfa", icon: "home", enabled: true, order: 1 },
  { key: "jobs", label: "Görevlerim", icon: "clipboard-list", enabled: true, order: 2 },
  { key: "operations", label: "Operasyon", icon: "navigation", enabled: true, order: 3 },
  { key: "notifications", label: "Bildirimler", icon: "bell", enabled: true, order: 4 },
  { key: "qr-checkin", label: "QR Okut", icon: "qr-code", enabled: true, order: 5 },
] as const;

const appConfigsByRole: Record<Role, AppConfig> = {
  driver: {
    app_id: "driver-coft-default",
    app_type: "driver",
    tenant_type: "vehicle_company",
    tenant_id: "coft-travel",
    company_id: "coft-travel",
    customer_company_id: "micetro",
    project_id: "antalya-vip",
    config_version: "2026.04.04-driver-01",
    branding: {
      source: "vehicle_company",
      logo_url: coftTempLogo,
      hero_image_url: vehicleHero,
      primary_color: "#D4AF37",
      base_color: "#091028",
      logo_fit_mode: "contained",
      loading_logo_url: coftTempLogo,
      loading_primary_color: "#D4AF37",
      loading_base_color: "#091028",
    },
    navigation: {
      home_route: "home",
      tab_items: [...sharedDriverTabs],
      hidden_routes: ["expenses", "files"],
    },
    modules: {
      shared_modules: {
        operations: { enabled: true, visible: true, required: true },
        tasks: { enabled: true, visible: true },
        qr_checkin: { enabled: true, visible: true },
        files: { enabled: true, visible: true },
        expenses: { enabled: true, visible: true },
        notifications: { enabled: true, visible: true },
      },
      company_modules: {
        flight_tracking: { enabled: true, visible: true },
        support_center: { enabled: true, visible: true },
        incident_reporting: { enabled: false, visible: false },
      },
      project_modules: {
        passenger_contact: { enabled: true, visible: true },
        route_planning: { enabled: true, visible: true },
        marketplace_entry: { enabled: false, visible: false },
      },
    },
    role_visibility: {
      role_id: "driver",
      visible_sections: ["home_profile", "operations", "files", "expenses", "qr_checkin"],
      hidden_sections: ["participant_directory", "tenant_admin"],
      allowed_actions: ["mark_passenger", "call_contact", "open_whatsapp", "advance_stage"],
      blocked_actions: ["admin_override", "policy_edit"],
    },
    content: {
      app_title: "driver-greeter-aplication",
      home_title: "Ana Sayfa",
      project_name: "Micetro İstanbul Zirvesi",
      project_date_range: "12-15 Ekim 2026",
      project_location: "İstanbul Kongre Merkezi",
      project_qr_value: "PROJECT:micetro-istanbul-zirvesi-2026|PARTICIPANT:Serhat-OKSAK",
      empty_state_texts: {
        alerts: "Şuan herşey yolunda...",
        notifications: "Tüm bildirimleri okudunuz.",
      },
    },
    policy_bundle: {
      phone_visibility_policy_id: "phone-vis-coft-default",
      sms_policy_id: "sms-coft-default",
      whatsapp_policy_id: "wa-coft-default",
      qr_validation_policy_id: "qr-driver-default",
      dynamic_qr_policy_id: "dynamic-qr-driver-default",
      qr_result_visibility_policy_id: "qr-result-visibility-driver-default",
      vehicle_match_policy_id: "vehicle-match-driver-default",
      stage_action_policy_id: "stage-driver-default",
      branding_policy_id: "brand-coft-default",
    },
  },
  greeter: {
    app_id: "greeter-coft-default",
    app_type: "greeter",
    tenant_type: "vehicle_company",
    tenant_id: "coft-travel",
    company_id: "coft-travel",
    customer_company_id: "micetro",
    project_id: "antalya-vip",
    config_version: "2026.04.04-greeter-01",
    branding: {
      source: "vehicle_company",
      logo_url: coftTempLogo,
      hero_image_url: vehicleHero,
      primary_color: "#D4AF37",
      base_color: "#091028",
      logo_fit_mode: "contained",
      loading_logo_url: coftTempLogo,
      loading_primary_color: "#D4AF37",
      loading_base_color: "#091028",
    },
    navigation: {
      home_route: "home",
      tab_items: [...sharedDriverTabs],
      hidden_routes: ["expenses", "files"],
    },
    modules: {
      shared_modules: {
        operations: { enabled: true, visible: true, required: true },
        tasks: { enabled: true, visible: true },
        qr_checkin: { enabled: true, visible: true },
        files: { enabled: true, visible: true },
        expenses: { enabled: true, visible: true },
        notifications: { enabled: true, visible: true },
      },
      company_modules: {
        flight_tracking: { enabled: true, visible: true },
        support_center: { enabled: true, visible: true },
        incident_reporting: { enabled: false, visible: false },
      },
      project_modules: {
        passenger_contact: { enabled: true, visible: true },
        route_planning: { enabled: true, visible: true },
        marketplace_entry: { enabled: false, visible: false },
      },
    },
    role_visibility: {
      role_id: "greeter",
      visible_sections: ["home_profile", "operations", "files", "expenses", "qr_checkin"],
      hidden_sections: ["participant_directory", "tenant_admin"],
      allowed_actions: ["mark_passenger", "call_contact", "open_whatsapp", "advance_stage"],
      blocked_actions: ["admin_override", "policy_edit"],
    },
    content: {
      app_title: "driver-greeter-aplication",
      home_title: "Ana Sayfa",
      project_name: "Micetro İstanbul Zirvesi",
      project_date_range: "12-15 Ekim 2026",
      project_location: "İstanbul Kongre Merkezi",
      project_qr_value: "PROJECT:micetro-istanbul-zirvesi-2026|PARTICIPANT:Serhat-OKSAK",
      empty_state_texts: {
        alerts: "Şuan herşey yolunda...",
        notifications: "Tüm bildirimleri okudunuz.",
      },
    },
    policy_bundle: {
      phone_visibility_policy_id: "phone-vis-greeter-default",
      sms_policy_id: "sms-greeter-default",
      whatsapp_policy_id: "wa-greeter-default",
      qr_validation_policy_id: "qr-greeter-default",
      dynamic_qr_policy_id: "dynamic-qr-greeter-default",
      qr_result_visibility_policy_id: "qr-result-visibility-greeter-default",
      vehicle_match_policy_id: "vehicle-match-greeter-default",
      stage_action_policy_id: "stage-greeter-default",
      branding_policy_id: "brand-coft-default",
    },
  },
};

const shellProfilesByRole: Record<Role, ShellProfile> = {
  driver: {
    role: "driver",
    full_name: "Serhat OKŞAK",
    vehicle_label: "Mercedes Vito Tourer",
    plate_label: "07 ABC 123",
  },
  greeter: {
    role: "greeter",
    full_name: "Selin Demir",
    vehicle_label: "Karşılama Ekibi",
    plate_label: "Terminal 2",
  },
};

function resolveVisibilityOverride(
  override: VisibilityOverride | undefined,
  fallback: boolean,
): boolean {
  if (override === "show") return true;
  if (override === "hide") return false;
  return fallback;
}

const driverOperations: Operation[] = [
  {
    id: 9012,
    start_time: "09:30",
    project_name: "Antalya VIP",
    passenger_name: "Ayşe Yılmaz",
    passenger_count: 2,
    passenger_list: [
      { tc: "12345678901", qr_code: "PAX-12345678901", full_name: "Ayşe Yılmaz", title: "Kadın", phone: "+90 532 100 11 22" },
      { tc: "12345678902", qr_code: "PAX-12345678902", full_name: "Mehmet Yılmaz", title: "Erkek", phone: "+90 532 100 11 33" },
    ],
    flight_code: "PC2012",
    flight_scheduled_time: "09:25",
    flight_eta: "09:12",
    flight_tracking_url: "https://www.flightradar24.com/data/flights/pc2012",
    transfer_direction: "arrival",
    start_location: "AYT Terminal 2",
    end_location: "Belek",
    route_share_policy: "approval_required",
    route_stops: [
      {
        label: "Başlangıç", value: "AYT Terminal 2", main_location: "AYT Airport", sub_location: "Terminal 2",
        address_info: "Antalya Havalimanı Terminal 2, Muratpaşa / Antalya",
        map_data: { source: "manual_coordinates", coordinates: { lat: 36.8987, lng: 30.8006 } },
        map_share: { policy: "auto", approved: true },
        boarding_passenger_tcs: ["12345678901", "12345678902"], alighting_passenger_tcs: [],
      },
      {
        label: "1. Durak", value: "Lara", main_location: "Lara", sub_location: "Titanic Lara",
        address_info: "Lara Turizm Yolu, Muratpaşa / Antalya",
        map_data: { source: "manual_coordinates", coordinates: { lat: 36.8556, lng: 30.8764 } },
        map_share: { policy: "auto", approved: true },
        boarding_passenger_tcs: [], alighting_passenger_tcs: ["12345678902"],
      },
      {
        label: "2. Durak", value: "Kundu", main_location: "Kundu", sub_location: "Royal Seginus",
        address_info: "Kundu Oteller Bölgesi, Aksu / Antalya",
        map_data: { source: "address", address: "Kundu Oteller Bölgesi, Aksu / Antalya" },
        map_share: { policy: "approval_required", approved: false },
        boarding_passenger_tcs: [], alighting_passenger_tcs: [],
      },
      {
        label: "Bitiş", value: "Belek", main_location: "Belek", sub_location: "Cornelia Diamond",
        address_info: "Belek, Serik / Antalya",
        map_data: { source: "manual_coordinates", coordinates: { lat: 36.8625, lng: 31.0557 } },
        map_share: { policy: "approval_required", approved: true },
        boarding_passenger_tcs: [], alighting_passenger_tcs: ["12345678901"],
      },
    ],
    contact_name: "Ayşe Aksoy",
    contact_phone: "+90 532 111 22 33",
    status: "ready",
    operation_stages: ["Hazırım", "Misafir alındı", "Misafir bırakıldı"],
    primary_action: "Misafir Araçta",
    project_phone_visibility_override: "show",
    transfer_phone_visibility_override: "inherit",
    project_sms_permission_override: "show",
    transfer_sms_permission_override: "inherit",
    project_whatsapp_permission_override: "hide",
    transfer_whatsapp_permission_override: "inherit",
    resolved_policies: {
      phone_visible: true,
      sms_allowed: true,
      whatsapp_allowed: false,
      qr_validation_mode: "vehicle_strict",
      qr_rotation_enabled: true,
      qr_rotation_interval_seconds: 15,
      qr_format_type: "signed_opaque",
      show_driver_own_qr_result_notice: false,
      show_driver_greeter_qr_result_notice: true,
      show_greeter_driver_qr_result_notice: false,
      allow_project_cross_vehicle: false,
      person_vehicle_restricted: true,
      flight_tracking_available: true,
    },
  },
  {
    id: 9013,
    start_time: "14:15",
    project_name: "Lara Premium",
    passenger_name: "Emre Kaya",
    passenger_count: 1,
    passenger_list: [{ tc: "12345678903", qr_code: "PAX-12345678903", full_name: "Emre Kaya", title: "Erkek", phone: "+90 533 444 00 11" }],
    flight_code: "TK2421",
    flight_eta: null,
    flight_tracking_url: "https://www.flightradar24.com/data/flights/tk2421",
    transfer_direction: "departure",
    start_location: "Kundu",
    end_location: "AYT İç Hatlar",
    contact_name: "Bora Yıldız",
    contact_phone: "+90 533 444 55 66",
    status: "assigned",
    operation_stages: ["Hazırım", "Misafir alındı", "Misafir bırakıldı"],
    primary_action: "Yola Çıktı",
    project_phone_visibility_override: "inherit",
    transfer_phone_visibility_override: "hide",
    project_sms_permission_override: "inherit",
    transfer_sms_permission_override: "hide",
    project_whatsapp_permission_override: "inherit",
    transfer_whatsapp_permission_override: "hide",
    resolved_policies: {
      phone_visible: false,
      sms_allowed: false,
      whatsapp_allowed: false,
      qr_validation_mode: "project_flexible",
      qr_rotation_enabled: true,
      qr_rotation_interval_seconds: 5,
      qr_format_type: "structured_context",
      show_driver_own_qr_result_notice: false,
      show_driver_greeter_qr_result_notice: true,
      show_greeter_driver_qr_result_notice: false,
      allow_project_cross_vehicle: true,
      person_vehicle_restricted: false,
      flight_tracking_available: true,
    },
  },
];

const greeterOperations: Operation[] = [
  {
    id: 9101,
    start_time: "09:05",
    project_name: "Antalya VIP",
    passenger_name: "Ayşe Yılmaz",
    passenger_count: 2,
    passenger_list: [
      { tc: "12345678904", qr_code: "PAX-12345678904", full_name: "Ayşe Yılmaz", title: "Kadın", phone: "+90 532 111 45 67" },
      { tc: "12345678905", qr_code: "PAX-12345678905", full_name: "Elif Yılmaz", title: "Kadın", phone: "+90 532 111 45 68" },
    ],
    flight_code: "PC2012",
    flight_scheduled_time: "09:25",
    flight_eta: "09:12",
    flight_tracking_url: "https://www.flightradar24.com/data/flights/pc2012",
    transfer_direction: "arrival",
    start_location: "AYT Terminal 2",
    end_location: "Sürücüye Teslim",
    route_share_policy: "auto",
    route_stops: [
      {
        label: "Başlangıç", value: "AYT Terminal 2", main_location: "AYT Airport", sub_location: "Terminal 2",
        address_info: "Antalya Havalimanı Terminal 2, Muratpaşa / Antalya",
        map_data: { source: "manual_coordinates", coordinates: { lat: 36.8987, lng: 30.8006 } },
        map_share: { policy: "auto", approved: true },
        boarding_passenger_tcs: [], alighting_passenger_tcs: [],
      },
      {
        label: "Karşılama", value: "Pano Noktası A", main_location: "AYT Airport", sub_location: "Pano Noktası A",
        address_info: "AYT Dış Hatlar Karşılama, Muratpaşa / Antalya",
        map_data: { source: "manual_coordinates", coordinates: { lat: 36.8991, lng: 30.8010 } },
        map_share: { policy: "auto", approved: true },
        boarding_passenger_tcs: ["12345678904", "12345678905"], alighting_passenger_tcs: [],
      },
      {
        label: "Teslim", value: "Sürücüye Teslim", main_location: "AYT Airport", sub_location: "Teslim Alanı",
        address_info: "AYT Otopark Bölgesi, Muratpaşa / Antalya",
        map_data: { source: "manual_coordinates", coordinates: { lat: 36.8980, lng: 30.7995 } },
        map_share: { policy: "auto", approved: true },
        boarding_passenger_tcs: [], alighting_passenger_tcs: ["12345678904", "12345678905"],
      },
    ],
    contact_name: "Selin Demir",
    contact_phone: "+90 532 222 33 44",
    status: "ready",
    operation_stages: ["Karşılama Başladı", "Misafir Bulundu", "Sürücüye Teslim"],
    primary_action: "Karşılama Başladı",
    project_phone_visibility_override: "show",
    transfer_phone_visibility_override: "inherit",
    project_sms_permission_override: "show",
    transfer_sms_permission_override: "inherit",
    project_whatsapp_permission_override: "show",
    transfer_whatsapp_permission_override: "inherit",
    resolved_policies: {
      phone_visible: true,
      sms_allowed: true,
      whatsapp_allowed: true,
      qr_validation_mode: "project_flexible_with_person_lock",
      qr_rotation_enabled: true,
      qr_rotation_interval_seconds: 10,
      qr_format_type: "one_time_hash",
      show_driver_own_qr_result_notice: false,
      show_driver_greeter_qr_result_notice: true,
      show_greeter_driver_qr_result_notice: true,
      allow_project_cross_vehicle: true,
      person_vehicle_restricted: true,
      flight_tracking_available: true,
    },
  },
];

const driverJobsByDate: Record<string, Job[]> = {
  "2026-04-01": [
    {
      id: 9012, date: "2026-04-01", time: "09:30", project_name: "Antalya VIP",
      passenger_name: "Ayşe Yılmaz", flight_no: "PC2012",
      pickup_location: "AYT Terminal 2", pickup_main_location: "AYT Airport", pickup_sub_location: "Terminal 2",
      dropoff_location: "Belek", dropoff_main_location: "Belek", dropoff_sub_location: "Cornelia Diamond",
      transfer_point: "Dış Hatlar", transfer_point_main: "AYT Airport", transfer_point_sub: "Dış Hatlar",
      status: "ready", role_assignment: "driver", driver_action: "yola_cikti", greeter_action: null, can_add_expense: true,
    },
    {
      id: 9013, date: "2026-04-01", time: "14:15", project_name: "Lara Premium",
      passenger_name: "Emre Kaya", flight_no: "TK2421",
      pickup_location: "AYT İç Hatlar", pickup_main_location: "AYT Airport", pickup_sub_location: "İç Hatlar",
      dropoff_location: "Kundu", dropoff_main_location: "Kundu", dropoff_sub_location: "Royal Seginus",
      transfer_point: "Kapı 3", transfer_point_main: "AYT Airport", transfer_point_sub: "Kapı 3",
      status: "assigned", role_assignment: "driver", driver_action: null, greeter_action: null, can_add_expense: true,
    },
    {
      id: 9901, date: "2026-04-01", time: "16:30", project_name: "Operasyon",
      passenger_name: "Araç Değişikliği", flight_no: "-",
      pickup_location: "Araç Teslim Noktası", pickup_main_location: "Eski Araç", pickup_sub_location: "07 ABC 123",
      dropoff_location: "Araç Teslim Noktası", dropoff_main_location: "Yeni Araç", dropoff_sub_location: "07 DEF 456",
      transfer_point: "Operasyon Merkezi", transfer_point_main: "Operasyon Merkezi", transfer_point_sub: "Araç Teslim",
      status: "assigned", role_assignment: "driver", driver_action: null, greeter_action: null, can_add_expense: false,
      job_type: "operational", operational_badge: "Araç Değişikliği",
      operational_note: "Yeni aracı teslim aldıktan sonra plaka değişikliğini onaylayın.",
    },
  ],
  "2026-04-02": [
    {
      id: 9014, date: "2026-04-02", time: "08:10", project_name: "Golf Summit",
      passenger_name: "Deniz Aksoy", flight_no: "XQ122",
      pickup_location: "AYT Terminal 1", pickup_main_location: "AYT Airport", pickup_sub_location: "Terminal 1",
      dropoff_location: "Serik", dropoff_main_location: "Serik", dropoff_sub_location: "Golf Club",
      transfer_point: "Dış Hatlar", transfer_point_main: "AYT Airport", transfer_point_sub: "Dış Hatlar",
      status: "planned", role_assignment: "driver", driver_action: null, greeter_action: null, can_add_expense: true,
    },
  ],
};

const greeterJobsByDate: Record<string, Job[]> = {
  "2026-04-01": [
    {
      id: 9101, date: "2026-04-01", time: "09:05", project_name: "Antalya VIP",
      passenger_name: "Ayşe Yılmaz", flight_no: "PC2012",
      pickup_location: "AYT Terminal 2", pickup_main_location: "AYT Airport", pickup_sub_location: "Terminal 2",
      dropoff_location: "Sürücüye Teslim", dropoff_main_location: "AYT Airport", dropoff_sub_location: "Teslim Alanı",
      transfer_point: "Pano Noktası A", transfer_point_main: "AYT Airport", transfer_point_sub: "Pano Noktası A",
      status: "ready", role_assignment: "greeter", driver_action: null, greeter_action: "karsilama_basladi", can_add_expense: true,
    },
  ],
};

const expenses: Expense[] = [
  {
    id: 1,
    amount: 150,
    currency: "TRY",
    expense_type: "transfer",
    description: "Otopark ücreti",
    status: "submitted",
    date: "2026-04-01",
    flow: "alacak",
    operation_label: "09:30 Antalya VIP",
    counterparty_label: "Antalya Havalimanı Otopark",
    receipt_file_name: "Otopark_fisi_01042026.jpg",
    receipt_detail: "Terminal 2 kısa süreli otopark fişi. 1 saat 24 dakika park süresi işlendi.",
    settlement_status: "bekliyor",
  },
  {
    id: 2,
    amount: 85,
    currency: "TRY",
    expense_type: "general",
    description: "Yakıt",
    status: "approved",
    date: "2026-04-01",
    flow: "alacak",
    operation_label: "14:15 Lara Premium",
    counterparty_label: "Shell Lara Şubesi",
    receipt_file_name: "Yakit_fisi_01042026.jpg",
    receipt_detail: "Kurşunsuz 95 yakıt alımı. Toplam 18.6 litre üzerinden işlendi.",
    settlement_status: "tamamlandi",
  },
  {
    id: 3,
    amount: 220,
    currency: "TRY",
    expense_type: "general",
    description: "Araç avans kapatma",
    status: "draft",
    date: "2026-04-02",
    flow: "verecek",
    operation_label: "Genel araç hesabı",
    counterparty_label: "Araç Operasyon Mutabakatı",
    receipt_file_name: null,
    receipt_detail: "Dönem avans kapatma kaydı. Belge daha sonra eklenebilir.",
    settlement_status: "isleniyor",
  },
];

const files: FileItem[] = [
  {
    id: 1,
    name: "Otopark_fisi_01042026.jpg",
    type: "receipt",
    category: "fisler",
    date: "2026-04-01",
    important: false,
    savedToDevice: true,
    offline: true,
    operation_label: "09:30 Antalya VIP",
    project_name: "Antalya VIP",
  },
  {
    id: 2,
    name: "VIP_Karsilama_Tabelasi_Ayse_Yilmaz.pdf",
    type: "signage",
    category: "karsilama_tabelalari",
    date: "2026-04-01",
    important: true,
    savedToDevice: false,
    offline: false,
    operation_label: "09:05 Karşılama",
    project_name: "Antalya VIP",
  },
  {
    id: 3,
    name: "Yakit_fisi_01042026.jpg",
    type: "receipt",
    category: "fisler",
    date: "2026-04-01",
    important: false,
    savedToDevice: true,
    offline: true,
    operation_label: "14:15 Lara Premium",
    project_name: "Lara Premium",
  },
  {
    id: 4,
    name: "Sigorta_belgesi.pdf",
    type: "legal",
    category: "yasal_evraklar",
    date: "2026-03-28",
    important: true,
    savedToDevice: true,
    offline: true,
    operation_label: null,
    project_name: null,
  },
  {
    id: 5,
    name: "Transfer_Notlari_Belek.pdf",
    type: "operation",
    category: "operasyon_belgeleri",
    date: "2026-04-01",
    important: false,
    savedToDevice: false,
    offline: false,
    operation_label: "09:30 Antalya VIP",
    project_name: "Antalya VIP",
  },
];

export function getOperations(role: Role): Operation[] {
  return role === "greeter" ? greeterOperations : driverOperations;
}

export function getAppConfig(role: Role): AppConfig {
  return appConfigsByRole[role];
}

export function getShellProfile(role: Role): ShellProfile {
  return shellProfilesByRole[role];
}

export function isPassengerPhoneVisible(operation: Operation): boolean {
  if (operation.resolved_policies) return operation.resolved_policies.phone_visible;
  const projectResolved = resolveVisibilityOverride(
    operation.project_phone_visibility_override,
    vehicleCompanyDefaults.passengerPhoneVisible,
  );

  return resolveVisibilityOverride(
    operation.transfer_phone_visibility_override,
    projectResolved,
  );
}

export function isSmsAllowed(operation: Operation): boolean {
  if (operation.resolved_policies) return operation.resolved_policies.sms_allowed;
  const projectResolved = resolveVisibilityOverride(
    operation.project_sms_permission_override,
    vehicleCompanyDefaults.smsAllowed,
  );

  return resolveVisibilityOverride(
    operation.transfer_sms_permission_override,
    projectResolved,
  );
}

export function isWhatsappAllowed(operation: Operation): boolean {
  if (operation.resolved_policies) return operation.resolved_policies.whatsapp_allowed;
  const projectResolved = resolveVisibilityOverride(
    operation.project_whatsapp_permission_override,
    vehicleCompanyDefaults.whatsappAllowed,
  );

  return resolveVisibilityOverride(
    operation.transfer_whatsapp_permission_override,
    projectResolved,
  );
}

export function getDynamicQrPolicy(operation: Operation): DynamicQrPolicy {
  return {
    enabled: operation.resolved_policies.qr_rotation_enabled,
    intervalSeconds: operation.resolved_policies.qr_rotation_interval_seconds,
    formatType: operation.resolved_policies.qr_format_type,
  };
}

export function getQrResultVisibility(operation: Operation): QrResultVisibilityPolicy {
  return {
    showDriverOwnNotice: operation.resolved_policies.show_driver_own_qr_result_notice,
    showDriverGreeterNotice: operation.resolved_policies.show_driver_greeter_qr_result_notice,
    showGreeterDriverNotice: operation.resolved_policies.show_greeter_driver_qr_result_notice,
  };
}

export function getCoreBootstrap(role: Role): CoreBootstrapPayload {
  const operations = getOperations(role);
  const firstOperation = operations[0];

  return {
    role,
    appConfig: getAppConfig(role),
    shellProfile: getShellProfile(role),
    operations,
    jobsByDate: getJobsByDate(role),
    expenses: getExpenses(),
    files: getFiles(),
    dynamicQrPolicy: firstOperation ? getDynamicQrPolicy(firstOperation) : null,
    qrResultVisibility: firstOperation ? getQrResultVisibility(firstOperation) : null,
    syncedAt: "2026-04-04T12:00:00+03:00",
  };
}

function buildCommandResult(seed: string): CoreCommandResult {
  return {
    ok: true,
    commandId: `mock-${seed}`,
    acceptedAt: new Date().toISOString(),
  };
}

export async function submitPassengerMarkCommand(
  _payload: PassengerMarkCommand,
): Promise<CoreCommandResult> {
  return buildCommandResult("passenger-mark");
}

export async function submitStageActionCommand(
  _payload: StageActionCommand,
): Promise<CoreCommandResult> {
  return buildCommandResult("stage-action");
}

export async function submitQrArrivalEvent(
  _payload: QrArrivalEvent,
): Promise<CoreCommandResult> {
  return buildCommandResult("qr-arrival");
}

export function getJobsByDate(role: Role): Record<string, Job[]> {
  return role === "greeter" ? greeterJobsByDate : driverJobsByDate;
}

export function getExpenses(): Expense[] {
  return expenses;
}

export function getFiles(): FileItem[] {
  return files;
}

export function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    ready: "Hazır", assigned: "Atandı", planned: "Planlandı",
    completed: "Tamamlandı", submitted: "Gönderildi", approved: "Onaylandı", draft: "Taslak",
  };
  return map[status] || status;
}

export function getStatusColor(status: string): { bg: string; text: string } {
  switch (status) {
    case "ready": return { bg: "bg-gold-500/15", text: "text-gold-500" };
    case "assigned": return { bg: "bg-azure-500/15", text: "text-azure-500" };
    case "planned": return { bg: "bg-success/15", text: "text-success" };
    case "completed": return { bg: "bg-success/15", text: "text-success" };
    case "submitted": return { bg: "bg-azure-500/15", text: "text-azure-500" };
    case "approved": return { bg: "bg-success/15", text: "text-success" };
    case "draft": return { bg: "bg-muted", text: "text-muted-foreground" };
    default: return { bg: "bg-muted", text: "text-muted-foreground" };
  }
}
