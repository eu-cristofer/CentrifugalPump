import {
  type ReactNode,
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { type FormEngine, useEngine } from "./engineContext";

// ---- number parsing ----------------------------------------------------------

export interface Parsed {
  ok: boolean;
  /** the number, or null for an empty field; meaningless when !ok */
  value: number | null;
}

/**
 * Parse typed text; "," or "." is the decimal separator, "" is null.  With both
 * present the last one is the decimal separator ("1.234,56" and "1,234.56").
 */
export function parseNumber(text: string): Parsed {
  let t = text.trim();
  const comma = t.lastIndexOf(",");
  const dot = t.lastIndexOf(".");
  if (comma >= 0 && dot >= 0) {
    t = comma > dot ? t.replace(/\./g, "").replace(",", ".") : t.replace(/,/g, "");
  } else {
    t = t.replace(",", ".");
  }
  if (t === "") return { ok: true, value: null };
  const n = Number(t);
  return Number.isFinite(n) ? { ok: true, value: n } : { ok: false, value: null };
}

/** Display text of a value: "." decimal, no float noise. */
export function formatNumber(value: number | null): string {
  return value === null ? "" : String(Number(value.toPrecision(12)));
}

// ---- layout --------------------------------------------------------------------

const RowContext = createContext<{ id: string; label: string } | null>(null);

/** Uppercase section label, optionally with an (i) button (explain key). */
export function Section({ title, info }: { title: string; info?: string }) {
  return (
    <div className="form-section">
      <span className="section-label">{title}</span>
      {info && <InfoButton infoKey={info} />}
    </div>
  );
}

/** Label + control; the label is at least 150 px wide and wraps above under 480 px. */
export function Row({
  label,
  children,
  suffix,
  disabled,
}: {
  label: string;
  children: ReactNode;
  suffix?: string;
  /** greys the label with its (disabled) control */
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <RowContext.Provider value={{ id, label }}>
      <div className="form-row">
        <label className={`row-label${disabled ? " disabled" : ""}`} htmlFor={id}>
          {label}
        </label>
        <div className="row-control">{children}</div>
        {suffix && <span className="row-suffix">{suffix}</span>}
      </div>
    </RowContext.Provider>
  );
}

export function Divider() {
  return <hr className="form-hr" />;
}

export type BannerKind = "info" | "ok" | "warn" | "error";

export function Banner({ kind = "info", children }: { kind?: BannerKind; children: ReactNode }) {
  return (
    <div className={`banner banner-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

// ---- inputs ----------------------------------------------------------------------

export function TextField({
  value,
  onChange,
  placeholder,
  disabled,
  ariaLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  ariaLabel?: string;
}) {
  const row = useContext(RowContext);
  return (
    <input
      id={row?.id}
      className="field"
      type="text"
      value={value}
      placeholder={placeholder}
      disabled={disabled}
      aria-label={ariaLabel}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

/** Number input that accepts "," or "." and shows "."; empty is null. */
export function NumberField({
  value,
  onChange,
  disabled,
  placeholder,
  ariaLabel,
  id,
}: {
  value: number | null;
  onChange: (v: number | null) => void;
  disabled?: boolean;
  placeholder?: string;
  ariaLabel?: string;
  id?: string;
}) {
  const row = useContext(RowContext);
  const [text, setText] = useState(() => formatNumber(value));
  useEffect(() => {
    // an outside change (unit conversion, reset): show it; own typing is left alone
    setText((t) => {
      const p = parseNumber(t);
      return p.ok && p.value === value ? t : formatNumber(value);
    });
  }, [value]);
  return (
    <input
      id={id ?? row?.id}
      className="field field-number"
      type="text"
      inputMode="decimal"
      value={text}
      disabled={disabled}
      placeholder={placeholder}
      aria-label={ariaLabel}
      onChange={(e) => {
        setText(e.target.value);
        const p = parseNumber(e.target.value);
        if (p.ok) onChange(p.value);
      }}
    />
  );
}

export function Select({
  value,
  options,
  onChange,
  disabled,
  ariaLabel,
}: {
  value: string;
  /** [label, value] pairs */
  options: Array<[string, string]>;
  onChange: (v: string) => void;
  disabled?: boolean;
  ariaLabel?: string;
}) {
  const row = useContext(RowContext);
  const known = options.some(([, v]) => v === value);
  return (
    <select
      id={ariaLabel ? undefined : row?.id}
      className="field"
      value={value}
      disabled={disabled}
      aria-label={ariaLabel}
      onChange={(e) => onChange(e.target.value)}
    >
      {!known && <option value={value}>{value}</option>}
      {options.map(([label, v]) => (
        <option key={v} value={v}>
          {label}
        </option>
      ))}
    </select>
  );
}

export function Checkbox({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <label className={`checkbox${disabled ? " disabled" : ""}`}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="check-box" aria-hidden="true">
        {checked ? "✓" : ""}
      </span>
      <span>{label}</span>
    </label>
  );
}

// ---- units -------------------------------------------------------------------------

const optionCache = new WeakMap<object, Map<string, Promise<Array<[string, string]>>>>();

/** Display units of a dimension (from Python, cached per engine). */
export function loadUnitOptions(
  engine: Pick<FormEngine, "unitOptions">,
  dimension: string,
): Promise<Array<[string, string]>> {
  let byDim = optionCache.get(engine);
  if (!byDim) {
    byDim = new Map();
    optionCache.set(engine, byDim);
  }
  let p = byDim.get(dimension);
  if (!p) {
    p = engine.unitOptions(dimension);
    p.catch(() => byDim.delete(dimension));
    byDim.set(dimension, p);
  }
  return p;
}

export function useUnitOptions(dimension: string): Array<[string, string]> {
  const engine = useEngine();
  const [opts, setOpts] = useState<Array<[string, string]>>([]);
  useEffect(() => {
    let live = true;
    loadUnitOptions(engine, dimension).then(
      (o) => live && setOpts(o),
      () => undefined,
    );
    return () => {
      live = false;
    };
  }, [engine, dimension]);
  return opts;
}

/**
 * A quantity: number + display-unit select.  Changing the unit converts the shown
 * value in Python and reports both (like the desktop `ui.UnitField`).
 */
export function UnitField({
  dimension,
  value,
  unit,
  onChange,
  densRel = null,
  disabled,
}: {
  dimension: string;
  value: number | null;
  unit: string;
  onChange: (value: number | null, unit: string) => void;
  /** relative density, for density-coupled dimensions (viscosity) */
  densRel?: number | null;
  disabled?: boolean;
}) {
  const engine = useEngine();
  const row = useContext(RowContext);
  const options = useUnitOptions(dimension);
  const seq = useRef(0);
  const labels = options.map(([label]): [string, string] => [label, label]);
  return (
    <span className="unit-field">
      <NumberField value={value} disabled={disabled} onChange={(v) => onChange(v, unit)} />
      <Select
        value={unit}
        options={labels}
        disabled={disabled}
        ariaLabel={`${row?.label ?? dimension} unit`}
        onChange={(next) => {
          const id = ++seq.current;
          if (value === null || next === unit) {
            onChange(value, next);
            return;
          }
          engine.convert(value, unit, next, dimension, densRel).then(
            (v) => {
              if (id === seq.current) onChange(v ?? value, next);
            },
            () => undefined,
          );
        }}
      />
    </span>
  );
}

/** `value` of `fromUnit` expressed in `toUnit` (computed in Python); null until known. */
export function useConverted(
  value: number | null,
  fromUnit: string,
  toUnit: string,
  dimension: string,
  densRel: number | null = null,
): number | null {
  const engine = useEngine();
  const [out, setOut] = useState<number | null>(null);
  useEffect(() => {
    let live = true;
    if (value === null) {
      setOut(null);
      return;
    }
    engine.convert(value, fromUnit, toUnit, dimension, densRel).then(
      (v) => live && setOut(v),
      () => undefined,
    );
    return () => {
      live = false;
    };
  }, [engine, value, fromUnit, toUnit, dimension, densRel]);
  return out;
}

/** `values` of `fromUnit` expressed in `toUnit` (computed in Python); null until known. */
export function useConvertedMany(
  values: Array<number | null>,
  fromUnit: string,
  toUnit: string,
  dimension: string,
): Array<number | null> {
  const engine = useEngine();
  const key = JSON.stringify(values);
  const [out, setOut] = useState<{ key: string; list: Array<number | null> } | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all(
      values.map((v) =>
        v === null || fromUnit === toUnit
          ? Promise.resolve(v)
          : engine.convert(v, fromUnit, toUnit, dimension),
      ),
    ).then(
      (list) => live && setOut({ key, list }),
      () => undefined,
    );
    return () => {
      live = false;
    };
    // `key` stands for `values`
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine, key, fromUnit, toUnit, dimension]);
  if (fromUnit === toUnit) return values;
  return out && out.key === key ? out.list : values.map(() => null);
}

// ---- info ----------------------------------------------------------------------------

/** (i) button: toggles a popover with the `explain(key)` text (first line is the title). */
export function InfoButton({ infoKey }: { infoKey: string }) {
  const engine = useEngine();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState<string | null>(null);
  useEffect(() => {
    if (!open || text !== null) return;
    let live = true;
    engine.explain(infoKey).then(
      (t) => live && setText(t),
      () => live && setText(""),
    );
    return () => {
      live = false;
    };
  }, [open, text, engine, infoKey]);
  const [title, ...rest] = (text ?? "").split("\n");
  return (
    <span className="info">
      <button
        type="button"
        className="info-button"
        aria-label={`Info: ${infoKey}`}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        i
      </button>
      {open && (
        <div className="info-popover" role="note">
          {text === null ? (
            "…"
          ) : (
            <>
              <strong>{title}</strong>
              <div className="info-text">{rest.join("\n")}</div>
            </>
          )}
        </div>
      )}
    </span>
  );
}
