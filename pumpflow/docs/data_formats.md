# Architecture

PumpLab is organized in four layers. Each layer depends only on the ones below
it, and **only `binding.py` is allowed to import from the `pump` library** — this
keeps the engineering physics in one auditable place.

```mermaid
flowchart TB
    subgraph UI["Presentation — PySide6"]
        APP["app.py · MainWindow / menus / file IO"]
        CANVAS["canvas/ · scene · view · node/edge/port items"]
        DLG["nodes/*.py dialogs + ui.py + plotting.py"]
    end
    subgraph LOGIC["Logic — Qt-agnostic"]
        NODES["nodes/base.py · the 7 node compute() methods"]
        SIG["signals.py · typed payloads"]
    end
    subgraph BIND["Binding"]
        B["binding.py"]
        MX["mathx.py · numfmt.py"]
    end
    subgraph LIB["Engineering library"]
        PUMP["pump · Fluid / DesignPoint / TestPoint / PerformanceCurve / PerformanceChecker / ReportGenerator"]
    end

    APP --> CANVAS --> NODES
    DLG --> NODES
    NODES --> SIG
    NODES --> B
    B --> MX
    B --> PUMP
```

---

## 1. The reactive data-flow model

Widgets never call each other directly. Each node declares typed **input** and
**output** ports; a link copies one node's cached output payload to another node's
input. When anything changes, the scene recomputes the whole graph in
dependency order.

```mermaid
flowchart LR
    subgraph "A node"
        direction TB
        IN["inputs (typed ports)"] --> COMPUTE["compute(inputs)"]
        COMPUTE --> OUT["outputs_cache {port: payload}"]
        COMPUTE --> STATUS["status + state dot"]
    end
    UP["upstream node.outputs_cache"] -->|edge| IN
    OUT -->|edge| DOWN["downstream node inputs"]
```

### Signal types and the ports that carry them

```mermaid
flowchart LR
    RP[["RatedPoint"]]
    TP[["TestPointSet"]]
    CC2[["CorrectedCurve"]]
    FM[["FittedModel"]]
    CR[["ComplianceResult"]]

    RP --> Correction
    TP --> Correction
    Correction --> CC2
    CC2 --> CurveFit
    CurveFit --> FM
    FM --> Plot
    FM --> Check
    RP --> Plot
    RP --> Check
    Check --> CR
    RP --> Report
    CC2 --> Report
    FM --> Report
    CR --> Report
```

Port compatibility rule (`port_item.PortItem.can_accept`): an output may connect
to an input when the signal types match (or either side is the wildcard `*`, used
by Report Export's `branch` input and the Plot's `image` output), the two ports
are on different nodes, and a **single-connection input** is not already occupied.

---

## 2. The evaluation loop

`GraphScene.evaluate()` runs on every meaningful change — a dialog edit, a new or
removed link, a deleted node, or a project load.

```mermaid
sequenceDiagram
    participant U as User
    participant D as Property Dialog
    participant S as GraphScene
    participant N as Nodes (topo order)
    participant B as binding.py
    participant P as pump library

    U->>D: edit a value / toggle
    D->>S: on_change → evaluate()
    S->>S: _topo_order() (Kahn)
    loop each node in order
        S->>N: gather inputs from upstream caches
        S->>N: run(inputs) → compute()
        N->>B: (correction / fit / check)
        B->>P: to_speed · to_fluid · fitter · PerformanceChecker
        P-->>B: corrected curve / coeffs / limits
        B-->>N: typed payload
        N-->>S: outputs_cache + status/state
        S->>S: node.refresh() (repaint)
    end
    S-->>U: canvas + downstream dialogs updated
```

**Ordering** uses a stable Kahn topological sort over the link graph; nodes left
over from a cycle are appended deterministically so evaluation never hangs.
**Error isolation**: a node that raises is caught and shown with an `error` state
and message (UI_SPEC §7) — its neighbours still evaluate.

---

## 3. Interactive edge creation

All link dragging lives in `GraphView` (not in the ports) so the view keeps full
control of the mouse and there is no grabber ambiguity.

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Dragging: press on a port
    note right of Dragging
        if a connected single-input is
        grabbed, its link detaches first
        (re-wire), keeping the far end
    end note
    Dragging --> Dragging: mouse move → rubber-band to cursor
    Dragging --> Connected: release on a compatible port
    Dragging --> Idle: release on empty space (cancel)
    Connected --> Idle: connect_ports() + evaluate()
```

Fan-out is supported because **output ports are always multi-connection**; merge
is supported because the Report Export `branch` input is declared `multi=True`.

---

## 4. The two-pump (A/B) topology

One shared **Rated Point** (the service datasheet) fans out to two independent
branches, each with its own **Test Points Table** (a physical unit TAG). Every
branch payload carries its `pump_tag`, so Report Export groups them unambiguously
into one consolidated document, and overall acceptance reflects **all** pumps.

```mermaid
flowchart LR
    RP["◆ Rated Point (shared service TAG)"]
    RP --> COA["↻ Correction A"]
    RP --> COB["↻ Correction B"]
    TPA["▦ Test Points · B-2351105A"] --> COA
    TPB["▦ Test Points · B-2351105B"] --> COB
    COA --> CFA["∿ Fit A"] --> CKA["✓ Check A"]
    COB --> CFB["∿ Fit B"] --> CKB["✓ Check B"]
    RP --> CKA
    RP --> CKB
    RP --> RE["▤ Report Export"]
    CKA --> RE
    CKB --> RE
    CFA --> RE
    CFB --> RE
    COA --> RE
    COB --> RE
```

---

## 5. Persistence boundaries

```mermaid
flowchart TB
    subgraph DISK["On disk"]
        PF[".pumpflow (project: nodes + links + settings)"]
        DJ[".json (§6.2 data-exchange: unit/rated/points)"]
        DOCX[".docx (ReportGenerator output)"]
        PNG[".png (per-pump plot)"]
    end
    SCENE["canvas/scene.py to_dict / load_dict"] <--> PF
    PERSIST["persistence.py rated_from_json / testset_from_json"] <--> DJ
    RE["report_export.py"] --> DOCX
    RE --> PNG
    RE --> DJ
```

- **`.pumpflow`** captures the entire canvas — node kinds, positions, links, and
  each widget's `settings`. It is the "save my work" format.
- **§6.2 JSON** is the lightweight interchange shape (single rated point + measured
  rows) and round-trips with existing files, including comma-decimal strings.
