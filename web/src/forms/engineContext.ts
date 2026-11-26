import { createContext, useContext } from "react";
import type { Engine } from "../engine/client";

/** The engine calls the forms make (so tests can pass a fake). */
export type FormEngine = Pick<
  Engine,
  | "decodeSettings"
  | "encodeSettings"
  | "unitOptions"
  | "convert"
  | "explain"
  | "standards"
  | "clients"
  | "standardLabel"
  | "waterDensity"
  | "waterProperties"
  | "pumpTypes"
  | "pumpTypeHint"
  | "atmosphere"
  | "parsePaste"
  | "nextTime"
  | "mrtOptions"
  | "parseMrtPaste"
  | "mrtStandardChannels"
  | "exportReport"
>;

export const EngineContext = createContext<FormEngine | null>(null);

export function useEngine(): FormEngine {
  const engine = useContext(EngineContext);
  if (!engine) throw new Error("EngineContext is missing");
  return engine;
}
