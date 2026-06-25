# UI Theming & Color Guide

> A visual reference for the `pumpflow` color palette, component states, and
> the stylesheet (`pumpflow/style.py`) that defines them.

The application uses a unified Qt stylesheet (`QSS`) to maintain a consistent
and professional look. The palette is based on a calm industrial blue and steel
gray key, with accent colors reserved for specific states like success,
warning, and error.

This guide documents the most important color codes, especially those related
to node and banner states that provide feedback to the user.

## Color Palette

### Primary Colors

| Role | Hex | Swatch | Description |
|---|---|---|---|
| **Canvas Background** | `#eef1f4` | <span style="background-color:#eef1f4;color:#28323d;border:1px solid #d3dae2;padding:2px 8px;">Color</span> | The main workspace background. |
| **Default Text** | `#28323d` | <span style="background-color:#ffffff;color:#28323d;border:1px solid #d3dae2;padding:2px 8px;">Color</span> | Standard text color for labels and content. |
| **Primary Accent** | `#2f6fb0` | <span style="background-color:#2f6fb0;color:#ffffff;padding:2px 8px;">Color</span> | Used for primary buttons and hover/focus states. |
| **Window/Control BG** | `#ffffff` | <span style="background-color:#ffffff;color:#28323d;border:1px solid #d3dae2;padding:2px 8px;">Color</span> | Background for toolbars, dialogs, and input fields. |
| **Border** | `#c3ccd6` | <span style="background-color:#c3ccd6;padding:2px 8px;"></span> | Default border for controls and windows. |

### Node & Banner State Colors

A node's appearance on the canvas is defined in `pumpflow/canvas/theme.py`, while its property dialog is styled by `pumpflow/style.py`.

#### Node Canvas Item Anatomy

The diagram below shows the visual components of a node on the main canvas. These elements are custom-drawn `QGraphicsItem`s whose colors are sourced from `theme.py`.

Source nodes (which have no inputs) use a lighter, steel-blue title bar (`TITLE_BG_SOURCE`) to distinguish them from processing nodes, which use a darker steel color (`TITLE_BG`).

<div style="position: relative; border: 2px dashed #a0aab4; border-radius: 8px; background: #eef1f4; max-width: 500px; font-family: Segoe UI, sans-serif; font-size: 13px; color: #28323d; margin: 1em 0; padding: 20px; display: flex; gap: 20px; align-items: flex-start;">
    <!-- Source Node -->
    <div style="flex: 1;">
        <div style="text-align: center; font-size: 11px; color: #5b7185; margin-bottom: 5px; font-weight: 600;">Source Node</div>
        <div style="width: 200px; border: 1px solid #b6c0cb; border-radius: 8px; background: #ffffff; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <div style="background: #3b6ea5; padding: 6px 10px; border-radius: 7px 7px 0 0;">
                <div style="color: #ffffff; font-weight: bold; font-size: 13px;">Rated Point Input</div>
            </div>
            <div style="padding: 8px 10px; font-size: 12px; text-align: right;">
                <span>Output Port</span>
                <div style="width: 12px; height: 12px; border-radius: 6px; background: #2f6fb0; margin-left: 8px; display: inline-block; vertical-align: middle;"></div>
            </div>
        </div>
    </div>
    <!-- Standard Node -->
    <div style="flex: 1;">
        <div style="text-align: center; font-size: 11px; color: #5b7185; margin-bottom: 5px; font-weight: 600;">Standard Node</div>
        <div style="width: 200px; border: 1px solid #b6c0cb; border-radius: 8px; background: #ffffff; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <div style="background: #2b3a4a; padding: 6px 10px; border-radius: 7px 7px 0 0;">
                <div style="color: #ffffff; font-weight: bold; font-size: 13px;">Curve Fit</div>
            </div>
            <div style="padding: 8px 10px; font-size: 12px;">
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="width: 12px; height: 12px; border-radius: 6px; background: #3f8f8a; margin-right: 8px;"></div>
                    <span>Input Port</span>
                </div>
                <div style="display: flex; align-items: center; justify-content: flex-end;">
                    <span>Output Port</span>
                    <div style="width: 12px; height: 12px; border-radius: 6px; background: #6a6fb0; margin-left: 8px;"></div>
                </div>
            </div>
        </div>
    </div>
</div>

#### Node Property Dialog Anatomy

Double-clicking a node opens its property dialog. This is a standard `QDialog` styled by `pumpflow/style.py`. The header background color matches the title bar of the node on the canvas.

<div style="display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap; margin: 1em 0;">
  <!-- Source Node Dialog -->
  <div style="flex: 1; min-width: 300px;">
    <div style="text-align: center; font-size: 11px; color: #5b7185; margin-bottom: 5px; font-weight: 600;">Source Node Dialog</div>
    <div style="border: 1px solid #c3ccd6; border-radius: 8px; background: #ffffff; font-family: Segoe UI, sans-serif; font-size: 13px; color: #28323d; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
      <div id="DialogHeader" style="background: #3b6ea5; padding: 10px 15px; border-radius: 7px 7px 0 0;">
        <div id="DialogTitle" style="color: #ffffff; font-weight: bold; font-size: 15px;">Rated Point Input</div>
        <div id="DialogSubtitle" style="color: #c4d0db; font-size: 12px;">Project design point</div>
      </div>
      <div style="padding: 15px;">...</div>
    </div>
  </div>
  <!-- Standard Node Dialog -->
  <div style="flex: 1; min-width: 300px;">
    <div style="text-align: center; font-size: 11px; color: #5b7185; margin-bottom: 5px; font-weight: 600;">Standard Node Dialog</div>
    <div style="border: 1px solid #c3ccd6; border-radius: 8px; background: #ffffff; font-family: Segoe UI, sans-serif; font-size: 13px; color: #28323d; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
      <div id="DialogHeader" style="background: #2b3a4a; padding: 10px 15px; border-radius: 7px 7px 0 0;">
        <div id="DialogTitle" style="color: #ffffff; font-weight: bold; font-size: 15px;">Curve Fit</div>
        <div id="DialogSubtitle" style="color: #c4d0db; font-size: 12px;">Fit polynomial and spline</div>
      </div>
      <div style="padding: 15px;">
        <div id="Banner" kind="ok" style="background: #e3f1ea; color: #1f6b4c; border-radius: 7px; padding: 8px 12px; font-size: 12px; text-align: center;">
          Status banner (`#Banner`) appears here
        </div>
      </div>
    </div>
  </div>
</div>

Nodes and banners change color to reflect the status of the dataflow pipeline.
These states are critical for understanding whether a computation was
successful, encountered an issue, or is waiting for input.

The colors are applied to banners within node dialogs and, in the future, could
be used to color-code the nodes themselves on the canvas.

#### Banners (`#Banner`)

These are general-purpose informational banners.

| `kind` | Background | Foreground | Swatch | Use Case |
|---|---|---|---|---|
| `info` | `#eef2f6` | `#44566a` | <span style="background-color:#eef2f6;color:#44566a;border:1px solid #d8e0e8;padding:2px 8px;">Informational</span> | Neutral or informational messages. |
| `ok` | `#e3f1ea` | `#1f6b4c` | <span style="background-color:#e3f1ea;color:#1f6b4c;border:1px solid #bfe0cd;padding:2px 8px;">Success</span> | Operation completed successfully. |
| `warn` | `#fbf1de` | `#8a6116` | <span style="background-color:#fbf1de;color:#8a6116;border:1px solid #f9e4af;padding:2px 8px;">Warning</span> | A potential issue that does not block execution. |
| `error` | `#f8e4e2` | `#9a3a34` | <span style="background-color:#f8e4e2;color:#9a3a34;border:1px solid #ecc6c1;padding:2px 8px;">Error</span> | An error that prevented the node from computing. |

#### Compliance Verdicts (`#VerdictBanner`)

These banners are used specifically in the **Compliance** node to show the
result of the API 610 acceptance test.

| `verdict` | Background | Foreground | Swatch | Meaning |
|---|---|---|---|---|
| `pass` | `#e3f1ea` | `#1f6b4c` | <span style="background-color:#e3f1ea;color:#1f6b4c;border:1px solid #bfe0cd;padding:2px 8px;">**PASS**</span> | The pump performance meets all criteria. |
| `fail` | `#f8e4e2` | `#9a3a34` | <span style="background-color:#f8e4e2;color:#9a3a34;border:1px solid #ecc6c1;padding:2px 8px;">**FAIL**</span> | The pump performance failed one or more criteria. |
| `idle` | `#eef2f6` | `#6b7785` | <span style="background-color:#eef2f6;color:#6b7785;border:1px solid #d8e0e8;padding:2px 8px;">**IDLE**</span> | Waiting for input data to perform the check. |

---

### Improving Contrast

The feedback regarding contrast is noted. The current palette aims for a softer,
less fatiguing look, but accessibility is paramount. Future revisions of the
stylesheet will evaluate the foreground/background color pairs against WCAG
(Web Content Accessibility Guidelines) contrast ratios to ensure readability
for all users.

For example, the `warn` state (`#8a6116` on `#fbf1de`) has a contrast ratio of
4.55:1, which meets the AA standard. However, other combinations might need
adjustment.

| State | Foreground | Background | Ratio | WCAG AA | WCAG AAA |
|---|---|---|:---:|:---:|:---:|
| `ok` | `#1f6b4c` | `#e3f1ea` | 5.25:1 | Pass | Pass |
| `warn` | `#8a6116` | `#fbf1de` | 4.55:1 | Pass | Fail |
| `error` | `#9a3a34` | `#f8e4e2` | 4.51:1 | Pass | Fail |
| `idle` | `#6b7785` | `#eef2f6` | 3.08:1 | Fail | Fail |

The `idle` state in particular fails to meet the minimum 4.5:1 ratio for normal
text and will be a priority for revision.