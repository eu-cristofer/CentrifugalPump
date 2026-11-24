"""
nodes.fluidpick — shared "which fluid drives this node" selection logic.

A fluid-consuming node (Rated Point, Test Points, Correction, Point) may have
**several** Fluid nodes wired into its multi-connection ``FluidSpec`` input.  A
``fluid_choice`` setting picks which one applies — the node's *default* option
(``"__default__"``) or a specific wired fluid identified by its ``name``.

Qt-agnostic and pure so it can be imported by node logic and tested directly.
The default-to-first-wired rule means connecting a Fluid node takes effect
immediately; the user can switch back to ``"__default__"`` in the dialog.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

DEFAULT = "__default__"


def resolve_fluid(specs: Sequence, choice: Optional[str]):
    """Return the chosen ``FluidSpec`` from ``specs``, or ``None`` for the node
    default.

    - no fluids wired            → ``None``
    - ``choice == "__default__"`` → ``None``
    - ``choice`` matches a name  → that spec (first match if names collide)
    - otherwise (unset / stale)  → ``specs[0]`` (default-to-first-wired)
    """
    if not specs:
        return None
    if choice == DEFAULT:
        return None
    if choice:
        for spec in specs:
            if spec.name == choice:
                return spec
    return specs[0]


def choice_options(
    specs: Sequence, default_label: Optional[str]
) -> List[Tuple[str, str]]:
    """``[(label, data)]`` pairs for :func:`pumpflow.nodes.ui.combo`.

    A leading default entry (unless ``default_label`` is ``None`` — e.g. the
    Point node, which has no own fluid) followed by one entry per wired fluid.
    """
    options: List[Tuple[str, str]] = []
    if default_label is not None:
        options.append((default_label, DEFAULT))
    for spec in specs:
        options.append((spec.name, spec.name))
    return options


def current_choice(specs: Sequence, choice: Optional[str]) -> str:
    """The combo ``data`` value that should be shown selected, accounting for
    the default-to-first-wired rule and stale/removed selections."""
    chosen = resolve_fluid(specs, choice)
    if chosen is None:
        return DEFAULT
    return chosen.name
