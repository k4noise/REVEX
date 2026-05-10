import type { DisplayMode } from "../../../model/templateElement";

export function safeNumber(value: unknown, fallback = 0): number {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "string" && value.trim() === "") return fallback;

  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function normalizeWeight(raw: unknown): number {
  const num = safeNumber(raw, 1);
  const rounded = Math.round(num);
  return clamp(rounded, 0, 20);
}

export function normalizeTotalPoints(raw: unknown): number {
  const num = safeNumber(raw, 1);
  const rounded = Math.round(num);
  return clamp(rounded, 1, 1000);
}

export function normalizeDisplayMode(
  mode: DisplayMode | null | undefined,
): DisplayMode | null {
  return mode ?? null;
}
