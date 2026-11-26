/**
 * The viewer's decimal separator ("." or ",").
 *
 * A per-viewer convenience kept in localStorage (default point).  The Python
 * engine formats statuses and view texts with it (`evaluate(doc, sep)`); the
 * forms format their own numbers with the helpers below.  Typing accepts
 * either separator whatever the choice (`parseNumber`).  Reports follow their
 * language instead, in Python.
 */

export type DecimalSep = "." | ",";

const KEY = "pumpflow.decimalSeparator";

function load(): DecimalSep {
  try {
    return globalThis.localStorage?.getItem(KEY) === "," ? "," : ".";
  } catch {
    return ".";
  }
}

let current: DecimalSep = load();

export function decimalSep(): DecimalSep {
  return current;
}

/** Use `sep` from now on and remember it for this viewer. */
export function setDecimalSep(sep: DecimalSep): void {
  current = sep;
  try {
    globalThis.localStorage?.setItem(KEY, sep);
  } catch {
    /* private window or blocked storage: the choice lasts this session */
  }
}

/** Swap the decimal point of an already formatted number (no unit in `text`). */
export function localizeNumber(text: string): string {
  return current === "," ? text.replace(/\./g, ",") : text;
}

/** `v.toFixed(d)` with the separator; "—" for an unknown value. */
export function fixed(v: number | null | undefined, d: number): string {
  return v === null || v === undefined ? "—" : localizeNumber(v.toFixed(d));
}
