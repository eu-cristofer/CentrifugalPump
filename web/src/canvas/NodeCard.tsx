import { Handle, type Node, type NodeProps, Position, useStore } from "@xyflow/react";
import type { CatalogEntry, NodeResult } from "../engine/types";
import {
  LOW_DETAIL_ZOOM,
  STATE_GLYPH,
  portColor,
  stateColor,
  statusBeside,
  toneColors,
} from "./card";

export type NodeCardData = {
  kind: string;
  entry: CatalogEntry | undefined;
  result: NodeResult | undefined;
};
export type PumpNode = Node<NodeCardData, "pump">;

function Pill({
  text,
  tone,
  big = false,
  outline = false,
}: {
  text: string;
  tone: "ok" | "fail" | "warn";
  big?: boolean;
  outline?: boolean;
}) {
  const c = toneColors(tone);
  const style = outline
    ? { borderColor: c.fill, color: c.fill }
    : { background: c.fill, color: c.text, borderColor: c.fill };
  return (
    <span className={`pill${big ? " pill-big" : ""}${outline ? " pill-outline" : ""}`} style={style}>
      {text}
    </span>
  );
}

function StateDot({ state, big = false }: { state: NodeResult["state"]; big?: boolean }) {
  const glyph = STATE_GLYPH[state];
  const color = stateColor(state);
  return (
    <span
      className={`state-dot${big ? " state-dot-big" : ""}${glyph ? "" : " state-dot-idle"}`}
      data-state={state}
      style={glyph ? { background: color } : { borderColor: color }}
    >
      {glyph ?? ""}
    </span>
  );
}

/** The node body at a given zoom (UI_SPEC §3, §11); pure apart from the handles. */
export function NodeCardView({
  data,
  zoom,
  selected = false,
}: {
  data: NodeCardData;
  zoom: number;
  selected?: boolean;
}) {
  const { entry, result } = data;
  const title = entry?.title ?? data.kind;
  const glyph = entry?.glyph ?? "";
  const inputs = entry?.inputs ?? [];
  const outputs = entry?.outputs ?? [];
  const isSource = inputs.length === 0;
  const overview = zoom < LOW_DETAIL_ZOOM;
  const state = result?.state ?? "idle";
  const badge = result?.badge ?? null;
  const rows = Math.max(inputs.length, outputs.length);

  return (
    <div
      className={`node-card${selected ? " selected" : ""}${overview ? " overview" : ""}`}
      data-kind={data.kind}
    >
      <div className={`node-title${isSource ? " source" : ""}`}>
        <span className="node-glyph">{glyph}</span>
        <span className="node-title-text">{title}</span>
      </div>

      <div className="node-ports">
        {Array.from({ length: rows }, (_, i) => {
          const inp = inputs[i];
          const out = outputs[i];
          return (
            <div className="node-port-row" key={i}>
              <span className="port-label port-in">
                {inp && (
                  <>
                    <Handle
                      type="target"
                      position={Position.Left}
                      id={inp.name}
                      className="port-handle"
                      style={{ background: portColor(inp.type) }}
                    />
                    {!overview && inp.name}
                  </>
                )}
              </span>
              <span className="port-label port-out">
                {out && (
                  <>
                    <Handle
                      type="source"
                      position={Position.Right}
                      id={out.name}
                      className="port-handle"
                      style={{ background: portColor(out.type) }}
                    />
                    {!overview && out.name}
                  </>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {overview ? (
        <div className="node-overview" data-testid="overview">
          {badge ? <Pill text={badge[0]} tone={badge[1]} big /> : <StateDot state={state} big />}
        </div>
      ) : (
        <div className="node-status">
          {badge ? (
            <>
              <Pill text={badge[0]} tone={badge[1]} />
              {(result?.notes ?? []).map((note) => (
                <Pill key={note} text={note} tone="warn" outline />
              ))}
            </>
          ) : (
            <StateDot state={state} />
          )}
          <span className={`status-text${state === "ok" ? " status-ok" : ""}`}>
            {statusBeside(result?.status ?? "", badge)}
          </span>
        </div>
      )}
    </div>
  );
}

export default function NodeCard({ data, selected }: NodeProps<PumpNode>) {
  const zoom = useStore((s) => s.transform[2]);
  return <NodeCardView data={data} zoom={zoom} selected={selected} />;
}
