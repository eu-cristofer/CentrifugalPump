import {
  Background,
  type Connection,
  Controls,
  type Edge,
  type IsValidConnection,
  type OnConnect,
  type OnDelete,
  type OnEdgesChange,
  type OnNodesChange,
  ReactFlow,
  ReactFlowProvider,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow,
} from "@xyflow/react";
import {
  type Dispatch,
  type Ref,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import type { CatalogEntry, EvaluateResult, PumpflowDoc } from "../engine/types";
import {
  type DocEdge,
  type View,
  docEdges,
  docNodes,
  docView,
  edgeId,
} from "../project/model";
import { canConnect } from "../project/ports";
import type { Action } from "../project/store";
import NodeCard, { type PumpNode } from "./NodeCard";
import { portColor } from "./card";

const nodeTypes = { pump: NodeCard };

export interface CanvasHandle {
  /** scene coordinates of the viewport centre */
  center(): { x: number; y: number };
  /** the view as the desktop saves it */
  view(): View;
}

interface CanvasProps {
  doc: PumpflowDoc;
  catalog: CatalogEntry[];
  result: EvaluateResult | null;
  openId: number;
  dispatch: Dispatch<Action>;
  onOpenNode: (id: string) => void;
  handle?: Ref<CanvasHandle>;
}

const round = (n: number, digits = 2) => {
  const f = 10 ** digits;
  return Math.round(n * f) / f;
};

function toDocEdge(c: Connection | Edge): DocEdge | null {
  if (!c.sourceHandle || !c.targetHandle) return null;
  return {
    src_node: c.source,
    src_port: c.sourceHandle,
    dst_node: c.target,
    dst_port: c.targetHandle,
  };
}

function Flow({ doc, catalog, result, dispatch, onOpenNode, handle }: CanvasProps) {
  const rf = useReactFlow<PumpNode, Edge>();
  const wrap = useRef<HTMLDivElement>(null);
  const view = docView(doc);

  const size = useCallback(() => {
    const el = wrap.current;
    return { w: el?.clientWidth || 800, h: el?.clientHeight || 600 };
  }, []);

  useImperativeHandle(
    handle,
    () => {
      const centre = () => {
        const vp = rf.getViewport();
        const { w, h } = size();
        return { x: (w / 2 - vp.x) / vp.zoom, y: (h / 2 - vp.y) / vp.zoom };
      };
      return {
        center: centre,
        view: () => {
          const c = centre();
          return { zoom: round(rf.getViewport().zoom, 4), cx: round(c.x), cy: round(c.y) };
        },
      };
    },
    [rf, size],
  );

  // Restore the saved view once per open (the provider is remounted on open).
  useEffect(() => {
    if (!view) return;
    const { w, h } = size();
    void rf.setViewport({
      x: w / 2 - view.cx * view.zoom,
      y: h / 2 - view.cy * view.zoom,
      zoom: view.zoom,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const byKind = useMemo(() => new Map(catalog.map((c) => [c.kind, c])), [catalog]);

  const derivedNodes = useMemo<PumpNode[]>(
    () =>
      docNodes(doc).map((n) => ({
        id: n.id,
        type: "pump",
        position: { x: n.x, y: n.y },
        data: { kind: n.kind, entry: byKind.get(n.kind), result: result?.nodes[n.id] },
      })),
    [doc, byKind, result],
  );

  const derivedEdges = useMemo<Edge[]>(() => {
    const kinds = new Map(docNodes(doc).map((n) => [n.id, n.kind]));
    return docEdges(doc).map((e) => {
      const kind = kinds.get(e.src_node);
      const type = kind
        ? byKind.get(kind)?.outputs.find((p) => p.name === e.src_port)?.type
        : undefined;
      return {
        id: edgeId(e),
        source: e.src_node,
        sourceHandle: e.src_port,
        target: e.dst_node,
        targetHandle: e.dst_port,
        style: { stroke: portColor(type ?? ""), strokeWidth: 2 },
      };
    });
  }, [doc, byKind]);

  // Local copies carry selection, measurements and in-flight drags; the document
  // stays the source of truth and re-seeds them whenever it changes.
  const [nodes, setNodes] = useState<PumpNode[]>(derivedNodes);
  const [edges, setEdges] = useState<Edge[]>(derivedEdges);

  useEffect(() => {
    setNodes((prev) => {
      const old = new Map(prev.map((n) => [n.id, n]));
      return derivedNodes.map((n) => {
        const o = old.get(n.id);
        if (!o) return n;
        return {
          ...n,
          position: o.dragging ? o.position : n.position,
          dragging: o.dragging,
          selected: o.selected,
          measured: o.measured,
        };
      });
    });
  }, [derivedNodes]);

  useEffect(() => {
    setEdges((prev) => {
      const selected = new Set(prev.filter((e) => e.selected).map((e) => e.id));
      return derivedEdges.map((e) => ({ ...e, selected: selected.has(e.id) }));
    });
  }, [derivedEdges]);

  const onNodesChange: OnNodesChange<PumpNode> = useCallback(
    (changes) => setNodes((ns) => applyNodeChanges(changes, ns)),
    [],
  );
  const onEdgesChange: OnEdgesChange<Edge> = useCallback(
    (changes) => setEdges((es) => applyEdgeChanges(changes, es)),
    [],
  );

  const onConnect: OnConnect = useCallback(
    (c) => {
      const edge = toDocEdge(c);
      if (edge) dispatch({ type: "connect", edge, catalog });
    },
    [dispatch, catalog],
  );

  const isValidConnection: IsValidConnection = useCallback(
    (c) => {
      const edge = toDocEdge(c);
      return edge !== null && canConnect(docNodes(doc), catalog, edge);
    },
    [doc, catalog],
  );

  const onDelete: OnDelete<PumpNode, Edge> = useCallback(
    ({ nodes: gone, edges: lost }) => {
      const docEdgeList: DocEdge[] = [];
      for (const e of lost) {
        const d = toDocEdge(e);
        if (d) docEdgeList.push(d);
      }
      dispatch({ type: "remove", nodeIds: gone.map((n) => n.id), edges: docEdgeList });
    },
    [dispatch],
  );

  return (
    <div className="canvas" ref={wrap}>
      <ReactFlow<PumpNode, Edge>
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        isValidConnection={isValidConnection}
        onDelete={onDelete}
        onNodeDragStop={(_e, _n, dragged) =>
          dispatch({
            type: "move",
            moves: dragged.map((n) => ({
              id: n.id,
              x: round(n.position.x, 1),
              y: round(n.position.y, 1),
            })),
          })
        }
        onNodeDoubleClick={(_e, node) => onOpenNode(node.id)}
        deleteKeyCode={["Delete", "Backspace"]}
        fitView={!view}
        minZoom={0.1}
        maxZoom={2}
      >
        <Background gap={26} color="var(--grid-dot)" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export default function Canvas(props: CanvasProps) {
  return (
    <ReactFlowProvider key={props.openId}>
      <Flow {...props} />
    </ReactFlowProvider>
  );
}
