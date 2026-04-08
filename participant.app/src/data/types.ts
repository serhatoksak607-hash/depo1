export type Role = "driver" | "greeter";
export type VisibilityOverride = "inherit" | "show" | "hide";
export type QrValidationMode =
  | "vehicle_strict"
  | "project_flexible"
  | "project_flexible_with_person_lock";
export type DynamicQrFormat =
  | "alphanumeric_6"
  | "signed_opaque"
  | "structured_context"
  | "one_time_hash";
export type AppType =
  | "driver"
  | "participant"
  | "greeter"
  | "agency_ops"
  | "field_ops"
  | "vehicle_ops";
export type TenantType = "vehicle_company" | "agency" | "customer_company" | "saas";

export type JobStatus = "ready" | "assigned" | "planned" | "completed";
export type ExpenseStatus = "submitted" | "approved" | "draft";

export interface PassengerInfo {
  tc: string;
  qr_code?: string;
  full_name: string;
  title: string;
  phone: string;
}

export interface RouteStop {
  label: string;
  value: string;
  main_location: string;
  sub_location: string;
  address_info: string;
  map_data?: {
    source: string;
    coordinates?: { lat: number; lng: number };
    address?: string;
  };
  map_share?: { policy: string; approved: boolean };
  boarding_passenger_tcs: string[];
  alighting_passenger_tcs: string[];
}

export interface ResolvedOperationPolicies {
  phone_visible: boolean;
  sms_allowed: boolean;
  whatsapp_allowed: boolean;
  qr_validation_mode: QrValidationMode;
  qr_rotation_enabled: boolean;
  qr_rotation_interval_seconds: number;
  qr_format_type: DynamicQrFormat;
  show_driver_own_qr_result_notice: boolean;
  show_driver_greeter_qr_result_notice: boolean;
  show_greeter_driver_qr_result_notice: boolean;
  allow_project_cross_vehicle: boolean;
  person_vehicle_restricted: boolean;
  flight_tracking_available: boolean;
}

export interface BrandingConfig {
  source: "creatro" | "vehicle_company" | "agency" | "project";
  logo_url?: string | null;
  hero_image_url?: string | null;
  primary_color?: string | null;
  base_color?: string | null;
  logo_fit_mode?: "contained" | "full-height";
  loading_logo_url?: string | null;
  loading_primary_color?: string | null;
  loading_base_color?: string | null;
}

export interface NavigationTabItem {
  key: TabKey;
  label: string;
  icon: string;
  enabled: boolean;
  order: number;
}

export interface NavigationConfig {
  home_route: string;
  tab_items: NavigationTabItem[];
  hidden_routes?: string[];
}

export interface ModuleState {
  enabled: boolean;
  visible: boolean;
  required?: boolean;
  mode?: string | null;
}

export interface ModuleConfig {
  shared_modules: Record<string, ModuleState>;
  company_modules: Record<string, ModuleState>;
  project_modules: Record<string, ModuleState>;
}

export interface RoleVisibilityConfig {
  role_id: string;
  visible_sections: string[];
  hidden_sections: string[];
  allowed_actions: string[];
  blocked_actions: string[];
}

export interface ContentConfig {
  app_title?: string | null;
  home_title?: string | null;
  empty_state_texts?: Record<string, string>;
  action_labels?: Record<string, string>;
  support_labels?: Record<string, string>;
  project_name?: string | null;
  project_date_range?: string | null;
  project_location?: string | null;
  project_qr_value?: string | null;
}

export interface PolicyBundleConfig {
  phone_visibility_policy_id?: string | null;
  sms_policy_id?: string | null;
  whatsapp_policy_id?: string | null;
  qr_validation_policy_id?: string | null;
  dynamic_qr_policy_id?: string | null;
  qr_result_visibility_policy_id?: string | null;
  vehicle_match_policy_id?: string | null;
  stage_action_policy_id?: string | null;
  branding_policy_id?: string | null;
}

export interface AppConfig {
  app_id: string;
  app_type: AppType;
  tenant_type: TenantType;
  tenant_id: string;
  company_id?: string | null;
  customer_company_id?: string | null;
  project_id?: string | null;
  config_version: string;
  branding: BrandingConfig;
  navigation: NavigationConfig;
  modules: ModuleConfig;
  role_visibility: RoleVisibilityConfig;
  content: ContentConfig;
  policy_bundle: PolicyBundleConfig;
}

export interface ShellProfile {
  role: Role;
  full_name: string;
  vehicle_label: string;
  plate_label: string;
}

export interface DynamicQrPolicy {
  enabled: boolean;
  intervalSeconds: number;
  formatType: DynamicQrFormat;
}

export interface QrResultVisibilityPolicy {
  showDriverOwnNotice: boolean;
  showDriverGreeterNotice: boolean;
  showGreeterDriverNotice: boolean;
}

export interface Operation {
  id: number;
  start_time: string;
  project_name?: string;
  passenger_name: string;
  greeting_name?: string | null;
  passenger_count: number;
  passenger_list: PassengerInfo[];
  flight_code: string;
  flight_scheduled_time?: string;
  flight_eta?: string | null;
  flight_tracking_url?: string | null;
  transfer_direction: "arrival" | "departure";
  start_location: string;
  end_location: string;
  route_share_policy?: string;
  route_stops?: RouteStop[];
  contact_name: string;
  contact_phone: string;
  status: JobStatus;
  operation_stages: string[];
  primary_action: string;
  project_phone_visibility_override?: VisibilityOverride;
  transfer_phone_visibility_override?: VisibilityOverride;
  project_sms_permission_override?: VisibilityOverride;
  transfer_sms_permission_override?: VisibilityOverride;
  project_whatsapp_permission_override?: VisibilityOverride;
  transfer_whatsapp_permission_override?: VisibilityOverride;
  resolved_policies: ResolvedOperationPolicies;
}

export interface Job {
  id: number;
  date: string;
  time: string;
  project_name: string;
  passenger_name: string;
  greeting_name?: string | null;
  flight_no: string;
  pickup_location: string;
  pickup_main_location: string;
  pickup_sub_location: string;
  dropoff_location: string;
  dropoff_main_location: string;
  dropoff_sub_location: string;
  transfer_point: string;
  transfer_point_main: string;
  transfer_point_sub: string;
  status: JobStatus;
  role_assignment: string;
  driver_action: string | null;
  greeter_action: string | null;
  can_add_expense: boolean;
  job_type?: "transfer" | "operational";
  operational_badge?: string | null;
  operational_note?: string | null;
}

export interface Expense {
  id: number;
  amount: number;
  currency: string;
  expense_type: string;
  description: string;
  status: ExpenseStatus;
  date: string;
  flow: "alacak" | "verecek";
  operation_label?: string | null;
  counterparty_label?: string | null;
  receipt_file_name?: string | null;
  receipt_detail?: string | null;
  settlement_status?: "bekliyor" | "isleniyor" | "tamamlandi";
}

export interface FileItem {
  id: number;
  name: string;
  type: "receipt" | "document" | "signage" | "legal" | "operation";
  category: "fisler" | "karsilama_tabelalari" | "yasal_evraklar" | "operasyon_belgeleri";
  date: string;
  important: boolean;
  savedToDevice: boolean;
  offline: boolean;
  operation_label?: string | null;
  project_name?: string | null;
}

export interface CoreBootstrapPayload {
  role: Role;
  appConfig: AppConfig;
  shellProfile: ShellProfile;
  operations: Operation[];
  jobsByDate: Record<string, Job[]>;
  expenses: Expense[];
  files: FileItem[];
  dynamicQrPolicy: DynamicQrPolicy | null;
  qrResultVisibility: QrResultVisibilityPolicy | null;
  syncedAt: string;
}

export interface PassengerMarkCommand {
  operationId: number;
  passengerTc: string;
  checked: boolean;
  actorRole: Role;
  vehicleContextId?: string | null;
}

export interface StageActionCommand {
  operationId: number;
  stageIndex: number;
  stageLabel: string;
  actorRole: Role;
  vehicleContextId?: string | null;
}

export interface QrArrivalEvent {
  operationId: number;
  passengerTc: string;
  actorRole: Role;
  vehicleContextId?: string | null;
  projectContextId?: string | null;
  recordedAt: string;
}

export interface CoreCommandResult {
  ok: boolean;
  commandId: string;
  acceptedAt: string;
}

export type TabKey =
  | "home"
  | "operations"
  | "jobs"
  | "expenses"
  | "files"
  | "notifications"
  | "qr-checkin";
