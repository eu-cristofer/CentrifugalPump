import { vi } from "vitest";
import type { FormEngine } from "./engineContext";

/** An engine double: identity codec, a tiny unit table, canned lookups. */
export function fakeEngine(): { [K in keyof FormEngine]: ReturnType<typeof vi.fn> } & FormEngine {
  const fake = {
    decodeSettings: vi.fn(async (_kind: string, s: Record<string, unknown>) => ({ ...s })),
    encodeSettings: vi.fn(async (_kind: string, s: Record<string, unknown>) => ({ ...s })),
    unitOptions: vi.fn(async (dim: string) =>
      dim === "capacity"
        ? [
            ["m³/h", "m**3/h"],
            ["US GPM", "gallon/min"],
          ]
        : [["m", "m"]],
    ),
    convert: vi.fn(async (v: number, from: string, to: string) =>
      from === "m³/h" && to === "US GPM" ? v * 4.40287 : v,
    ),
    explain: vi.fn(async (key: string) => `Title of ${key}\nBody of ${key}`),
    standards: vi.fn(async () => [
      ["api610:12", "API 610 12th"],
      ["api610:8", "API 610 8th"],
    ]),
    clients: vi.fn(async () => [["n553", "Petrobras N-553"]]),
    standardLabel: vi.fn(async (key: string, client: string | null) =>
      client ? `${key}+${client}` : key,
    ),
    waterDensity: vi.fn(async () => 998.2),
    waterProperties: vi.fn(async () => ({ density: 997, kinematic_cst: 0.9, dynamic_cp: 0.9 })),
    pumpTypes: vi.fn(async () => [["BB2", "Between bearings"]]),
    atmosphere: vi.fn(async () => 1.01325),
    parsePaste: vi.fn(async (text: string, columns: Record<string, string>, ref: string) => ({
      rows: text
        .split("\n")
        .filter((l) => l.trim())
        .map((l) => {
          const c = l.split("\t").map((x) => Number(x.replace(",", ".")));
          return { q: c[0] ?? null, p_suc: c[1] ?? null, p_dis: c[2] ?? null };
        }),
      columns,
      pressure_ref: ref,
      vibration: false,
      warnings: [] as string[],
    })),
    nextTime: vi.fn(async (rows: Array<{ time?: string }>) => {
      const t = rows.at(-1)?.time ?? "";
      const m = /^(\d{1,2}):(\d{2})$/.exec(t);
      if (!m) return "00:00";
      const total = (Number(m[1]) * 60 + Number(m[2]) + 15) % 1440;
      return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
    }),
    parseMrtPaste: vi.fn(async (text: string) =>
      text
        .split("\n")
        .filter((l) => /^\d{1,2}:\d{2}/.test(l))
        .map((l) => {
          const [time = "", ...rest] = l.split("\t");
          return { time, values: { Flow: Number((rest[0] ?? "").replace(",", ".")) } };
        }),
    ),
    mrtOptions: vi.fn(async () => ({
      roles: ["flow", "oil_temperature", "vibration_filtered", "other"],
      dimensions: ["capacity", "temperature", "vibration_velocity"],
      role_dimensions: {
        flow: "capacity",
        oil_temperature: "temperature",
        vibration_filtered: "vibration_velocity",
      },
    })),
    exportReport: vi.fn(async (_doc: unknown, fmt: string, lang: string | null) => ({
      filename: `Report.${fmt === "summary_xlsx" ? "xlsx" : fmt}`,
      mime: fmt === "html" ? "text/html" : "application/octet-stream",
      base64: btoa(fmt === "html" ? `<html><body>report ${lang}</body></html>` : "PK-bytes"),
    })),
    pumpTypeHint: vi.fn(async (code: string) => (code ? `hint ${code}` : "Not set")),
  };
  return fake as never;
}
