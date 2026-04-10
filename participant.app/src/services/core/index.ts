import type {
  CoreBootstrapPayload,
  PassengerMarkCommand,
  QrArrivalEvent,
  Role,
  StageActionCommand,
} from "@/data/types";
import {
  getAppConfig as getMockAppConfig,
  getCoreBootstrap as getMockCoreBootstrap,
  getExpenses as getMockExpenses,
  getFiles as getMockFiles,
  getShellProfile as getMockShellProfile,
  getStatusColor,
  getStatusLabel,
  isPassengerPhoneVisible,
  isSmsAllowed,
  isWhatsappAllowed,
  submitPassengerMarkCommand as submitMockPassengerMarkCommand,
  submitQrArrivalEvent as submitMockQrArrivalEvent,
  submitStageActionCommand as submitMockStageActionCommand,
} from "@/data/mock";

const bootstrapCache = new Map<Role, CoreBootstrapPayload>();
const inflightBootstrapRequests = new Map<Role, Promise<CoreBootstrapPayload>>();

function mergeBootstrapPayload(
  role: Role,
  remotePayload: Partial<CoreBootstrapPayload> | null | undefined,
): CoreBootstrapPayload {
  const mockPayload = getMockCoreBootstrap(role);
  if (!remotePayload) {
    return setBootstrapCache(role, mockPayload);
  }

  const mergedPayload: CoreBootstrapPayload = {
    ...mockPayload,
    ...remotePayload,
    role,
    appConfig: {
      ...mockPayload.appConfig,
      ...(remotePayload.appConfig || {}),
      branding: {
        ...mockPayload.appConfig.branding,
        ...(remotePayload.appConfig?.branding || {}),
      },
      navigation: {
        ...mockPayload.appConfig.navigation,
        ...(remotePayload.appConfig?.navigation || {}),
      },
      modules: {
        ...mockPayload.appConfig.modules,
        ...(remotePayload.appConfig?.modules || {}),
        shared_modules: {
          ...mockPayload.appConfig.modules.shared_modules,
          ...(remotePayload.appConfig?.modules?.shared_modules || {}),
        },
        company_modules: {
          ...mockPayload.appConfig.modules.company_modules,
          ...(remotePayload.appConfig?.modules?.company_modules || {}),
        },
        project_modules: {
          ...mockPayload.appConfig.modules.project_modules,
          ...(remotePayload.appConfig?.modules?.project_modules || {}),
        },
      },
      role_visibility: {
        ...mockPayload.appConfig.role_visibility,
        ...(remotePayload.appConfig?.role_visibility || {}),
      },
      content: {
        ...mockPayload.appConfig.content,
        ...(remotePayload.appConfig?.content || {}),
      },
      policy_bundle: {
        ...mockPayload.appConfig.policy_bundle,
        ...(remotePayload.appConfig?.policy_bundle || {}),
      },
    },
    shellProfile: {
      ...mockPayload.shellProfile,
      ...(remotePayload.shellProfile || {}),
    },
    operations: remotePayload.operations || mockPayload.operations,
    jobsByDate: remotePayload.jobsByDate || mockPayload.jobsByDate,
    expenses: remotePayload.expenses || mockPayload.expenses,
    files: remotePayload.files || mockPayload.files,
    dynamicQrPolicy: remotePayload.dynamicQrPolicy ?? mockPayload.dynamicQrPolicy,
    qrResultVisibility: remotePayload.qrResultVisibility ?? mockPayload.qrResultVisibility,
    syncedAt: remotePayload.syncedAt || mockPayload.syncedAt,
  };

  return setBootstrapCache(role, mergedPayload);
}

function getCoreApiUrl() {
  return import.meta.env.VITE_CORE_API_URL?.trim() || "";
}

function getBootstrapPath() {
  return import.meta.env.VITE_CORE_BOOTSTRAP_PATH?.trim() || "/api/app/bootstrap";
}

function canUseRemoteCore() {
  return Boolean(getCoreApiUrl());
}

function buildBootstrapUrl(role: Role) {
  const baseUrl = getCoreApiUrl().replace(/\/$/, "");
  const path = getBootstrapPath().startsWith("/") ? getBootstrapPath() : `/${getBootstrapPath()}`;
  const url = new URL(`${baseUrl}${path}`);
  url.searchParams.set("role", role);
  return url.toString();
}

async function fetchRemoteBootstrap(role: Role): Promise<CoreBootstrapPayload> {
  const response = await fetch(buildBootstrapUrl(role), {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Core bootstrap request failed: ${response.status}`);
  }

  return (await response.json()) as CoreBootstrapPayload;
}

function setBootstrapCache(role: Role, payload: CoreBootstrapPayload) {
  bootstrapCache.set(role, payload);
  return payload;
}

function buildMockBootstrap(role: Role) {
  return setBootstrapCache(role, getMockCoreBootstrap(role));
}

function readBootstrap(role: Role): CoreBootstrapPayload {
  const cached = bootstrapCache.get(role);
  if (cached) {
    return cached;
  }

  return buildMockBootstrap(role);
}

export async function loadCoreBootstrap(role: Role): Promise<CoreBootstrapPayload> {
  const cached = bootstrapCache.get(role);
  if (cached) {
    return cached;
  }

  const inflight = inflightBootstrapRequests.get(role);
  if (inflight) {
    return inflight;
  }

  const request = (async () => {
    try {
      if (canUseRemoteCore()) {
        const remotePayload = await fetchRemoteBootstrap(role);
        return mergeBootstrapPayload(role, remotePayload);
      }
    } catch (error) {
      console.warn("Core bootstrap fetch failed, falling back to mock data.", error);
    } finally {
      inflightBootstrapRequests.delete(role);
    }

    return buildMockBootstrap(role);
  })();

  inflightBootstrapRequests.set(role, request);
  return request;
}

export function getAppConfig(role: Role) {
  return readBootstrap(role).appConfig ?? getMockAppConfig(role);
}

export function getShellProfile(role: Role) {
  return readBootstrap(role).shellProfile ?? getMockShellProfile(role);
}

export function getCoreBootstrap(role: Role) {
  return readBootstrap(role);
}

export function getOperations(role: Role) {
  return readBootstrap(role).operations;
}

export function getDynamicQrPolicy(role: Role) {
  return readBootstrap(role).dynamicQrPolicy;
}

export function getQrResultVisibility(role: Role) {
  return readBootstrap(role).qrResultVisibility;
}

export function getJobsByDate(role: Role) {
  return readBootstrap(role).jobsByDate;
}

export function getExpenses() {
  return getMockExpenses();
}

export function getFiles() {
  return getMockFiles();
}

export async function submitPassengerMarkCommand(payload: PassengerMarkCommand) {
  return submitMockPassengerMarkCommand(payload);
}

export async function submitStageActionCommand(payload: StageActionCommand) {
  return submitMockStageActionCommand(payload);
}

export async function submitQrArrivalEvent(payload: QrArrivalEvent) {
  return submitMockQrArrivalEvent(payload);
}

export {
  getStatusColor,
  getStatusLabel,
  isPassengerPhoneVisible,
  isSmsAllowed,
  isWhatsappAllowed,
};
