import { useEffect, useState } from "react";
import { type FormEngine, useEngine } from "./engineContext";

/** Load a value from the engine once per engine (and `key`); `initial` until it arrives. */
export function useLoaded<T>(
  load: (engine: FormEngine) => Promise<T>,
  initial: T,
  key = "",
): T {
  const engine = useEngine();
  const [value, setValue] = useState<T>(initial);
  useEffect(() => {
    let live = true;
    load(engine).then(
      (v) => live && setValue(v),
      () => undefined,
    );
    return () => {
      live = false;
    };
    // `load` is an inline closure; `key` says when it would load something else
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine, key]);
  return value;
}
