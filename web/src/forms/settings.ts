import type { Settings } from "../engine/types";

/** Typed reads of a runtime settings dict (the shape the desktop dialogs edit). */
export const getStr = (s: Settings, key: string, fallback = ""): string => {
  const v = s[key];
  return typeof v === "string" ? v : fallback;
};

export const getNum = (s: Settings, key: string, fallback = 0): number => {
  const v = s[key];
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
};

export const getNumOrNull = (s: Settings, key: string): number | null => {
  const v = s[key];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
};

export const getBool = (s: Settings, key: string, fallback = false): boolean => {
  const v = s[key];
  return typeof v === "boolean" ? v : fallback;
};
