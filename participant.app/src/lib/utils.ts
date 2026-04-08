import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPersonName(value: string | null | undefined) {
  const normalized = value?.trim() ?? "";

  if (!normalized) {
    return "";
  }

  const parts = normalized.split(/\s+/).filter(Boolean);

  if (parts.length <= 1) {
    return normalized.toLocaleUpperCase("tr-TR");
  }

  const firstNames = parts.slice(0, -1).join(" ");
  const lastName = parts[parts.length - 1].toLocaleUpperCase("tr-TR");
  return `${firstNames} ${lastName}`;
}

export function getDisplayLabel(
  fallbackName: string | null | undefined,
  greetingName?: string | null,
) {
  const preferredLabel = greetingName?.trim();
  if (preferredLabel) {
    return preferredLabel;
  }

  return formatPersonName(fallbackName);
}
