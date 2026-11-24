import { type Dispatch, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PumpflowDoc, Settings } from "../engine/types";
import { docNodes } from "../project/model";
import type { Action } from "../project/store";
import type { FormEngine } from "./engineContext";

export const FORM_DEBOUNCE_MS = 250;

export interface NodeForm {
  /** runtime settings (the desktop dialogs' keys); null until decoded */
  runtime: Settings | null;
  /** merge a patch; a key set to `undefined` is removed */
  update: (patch: Settings) => void;
  error: string;
}

/**
 * Runtime settings of one node for a form.  Edits show at once; after
 * FORM_DEBOUNCE_MS without edits they are encoded by Python and dispatched as one
 * `setSettings` (one undo step).  Stale encode responses are dropped, pending
 * edits are flushed on unmount, and an external change (undo/redo) reloads.
 */
export function useNodeForm(
  engine: Pick<FormEngine, "decodeSettings" | "encodeSettings">,
  doc: PumpflowDoc,
  nodeId: string,
  dispatch: Dispatch<Action>,
  delay: number = FORM_DEBOUNCE_MS,
): NodeForm {
  const node = useMemo(() => docNodes(doc).find((n) => n.id === nodeId), [doc, nodeId]);
  const kind = node?.kind ?? "";
  const encoded = node?.settings;
  const [runtime, setRuntime] = useState<Settings | null>(null);
  const [error, setError] = useState("");
  const runtimeRef = useRef<Settings | null>(null);
  const sent = useRef<Settings | null>(null);
  const encSeq = useRef(0);
  const decSeq = useRef(0);
  const pending = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flush = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    const rt = runtimeRef.current;
    if (!pending.current || !rt) return;
    pending.current = false;
    const id = ++encSeq.current;
    engine.encodeSettings(kind, rt).then(
      (enc) => {
        if (id !== encSeq.current) return; // stale: a newer edit or reload won
        sent.current = enc;
        dispatch({ type: "setSettings", id: nodeId, settings: enc });
      },
      (err: unknown) => setError(String(err)),
    );
  }, [engine, kind, nodeId, dispatch]);

  const flushRef = useRef(flush);
  useEffect(() => {
    flushRef.current = flush;
  }, [flush]);

  // load, and reload when the document changed under us (undo/redo)
  useEffect(() => {
    if (!encoded || encoded === sent.current) return;
    const id = ++decSeq.current;
    engine.decodeSettings(kind, encoded).then(
      (rt) => {
        if (id !== decSeq.current) return;
        if (timer.current) clearTimeout(timer.current);
        timer.current = null;
        pending.current = false;
        encSeq.current += 1;
        sent.current = null;
        runtimeRef.current = rt;
        setRuntime(rt);
        setError("");
      },
      (err: unknown) => {
        if (id === decSeq.current) setError(String(err));
      },
    );
  }, [engine, kind, encoded]);

  useEffect(
    () => () => {
      if (pending.current) flushRef.current();
    },
    [],
  );

  const update = useCallback(
    (patch: Settings) => {
      const next: Settings = { ...(runtimeRef.current ?? {}), ...patch };
      for (const [k, v] of Object.entries(patch)) if (v === undefined) delete next[k];
      runtimeRef.current = next;
      setRuntime(next);
      pending.current = true;
      encSeq.current += 1; // an in-flight older encode is now stale
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(flush, delay);
    },
    [flush, delay],
  );

  return { runtime, update, error };
}
