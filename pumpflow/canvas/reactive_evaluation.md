# Reactive Evaluation Sequence Diagram

This document provides a UML sequence diagram illustrating the reactive evaluation process within the `pumpflow` canvas. This process is triggered whenever the graph changes, ensuring the entire pipeline remains up-to-date. The core logic resides in `GraphScene.evaluate()`.

```mermaid
sequenceDiagram
    participant User
    participant GraphView
    participant GraphScene
    participant NodeItem
    participant BaseNodeLogic

    alt Graph Modification (e.g., add/remove node, connect ports)
        User->>GraphView: Drags to connect ports
        GraphView->>GraphScene: connect_ports(src, dst)
        GraphScene->>GraphScene: evaluate()
        GraphScene->>GraphView: graph_changed.emit()
    else Direct Evaluation Call
        User->>GraphView: Deletes a node (presses Del)
        GraphView->>GraphScene: keyPressEvent()
        GraphScene->>GraphScene: remove_node() / remove_edge()
        GraphScene->>GraphScene: evaluate()
    end

    Note over GraphScene: Start of the reactive evaluation process.

    GraphScene->>GraphScene: _topo_order()
    Note right of GraphScene: Calculates execution order of nodes (Kahn's algorithm).
    GraphScene-->>GraphScene: returns ordered_nodes

    loop For each NodeItem in ordered_nodes
        GraphScene->>GraphScene: _gather_inputs(node)
        Note right of GraphScene: Collects outputs from upstream nodes' cache.
        GraphScene-->>GraphScene: returns inputs_bundle

        GraphScene->>BaseNodeLogic: run(inputs_bundle)
        activate BaseNodeLogic

        Note over BaseNodeLogic: Performs computation (e.g., calls `pump` library via `binding`).
        BaseNodeLogic-->>GraphScene: returns (updates outputs_cache)
        deactivate BaseNodeLogic

        alt On Exception
            GraphScene->>BaseNodeLogic: set_error(exception_string)
        end

        GraphScene->>NodeItem: refresh()
        activate NodeItem
        NodeItem->>NodeItem: update()
        Note right of NodeItem: Triggers repaint to show new state/status.
        deactivate NodeItem

    end

    Note over GraphScene: Evaluation complete. Canvas is now up-to-date.

```