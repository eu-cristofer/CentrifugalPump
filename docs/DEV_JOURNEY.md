# Dev Journey — your map when it feels like too much

> *A use case is a thin flow over the domain, proven by one test.*

> Read this file first whenever the repo feels overwhelming. It exists for one
> reason: to turn *"there's too much to do"* into *"here is the next one thing."*

## Read this when you're overwhelmed

You are not behind. You are **over halfway**, and the hardest part — the part
that makes a project feel impossible — is already done.

- **Your MVP already works.** The three use cases that define this product for
  the FAT engineer — [UC-02](product/use-cases.md#uc-02--verify-pump-performance-fat-),
  [UC-06](product/use-cases.md#uc-06--evaluate-speed-change-vfd-) and
  [UC-09](product/use-cases.md#uc-09--generate-report-) — are supported today.
  If you stopped now, you'd still have a tool that computes hydraulic
  quantities, fits curves, checks API 610 tolerances, and writes a `.docx`
  report.
- **You've shipped 7 sprints** (S0–S6, ≈56 h) and written **10 ADRs**. Every
  big decision is already captured. You are not deciding from scratch anymore;
  you are *executing decisions you already made.*
- Everything that feels like a mountain is **optional improvement**, not
  survival. The product survives without any of it.

So the feeling isn't "I have too much to build." It's "I'm looking at the whole
backlog at once." The cure is below.

## The one rule

**Only ever look at the next sprint. Never the whole list.**

Your sprint culture already enforces this ([docs/sprints/](sprints/README.md)):
one 8-hour `.md` file, one branch, one commit. The list below is just *which
sprint is next* — so you never have to hold the whole thing in your head. Open
the top unchecked item, ignore the rest, finish it, come back.

## The second rule — structure by domain, steer by use cases

When you wonder *"how should I organize the product?"*, the answer is **not**
"by use case." Use cases overlap and get reprioritized; if your modules mirrored
them you'd duplicate physics and churn the layout constantly. Instead:

- **Structure the code by the domain — the stable nouns.** A pump tool *has*
  fluids, points, curves, compliance rules, and reports no matter which use case
  calls them. That's what `pump/` already is, and it should stay that way.
- **Use cases are a *lens*, not a module.** They decide **what to build next**
  (priority) and **when it's done** (acceptance) — nothing more. A use case is a
  *flow that composes existing capabilities*, never a folder.

Your repo already embodies this in three layers — keep them clean:

| Layer | Where | Organized by |
|---|---|---|
| **Capabilities** (stable nouns) | `pump/` | the **domain** |
| **Flows** (wiring capabilities into user actions) | `pumpflow/` | user-facing pipelines |
| **Priority + acceptance** | `docs/product/use-cases.md` | the **use cases** |

**Rule of thumb:** if a use case forces a *new noun* (system curve, NPSH, impeller
trim), that noun goes in `pump/` as a reusable capability. If it only *arranges
existing nouns*, it's a flow in `pumpflow/` plus an acceptance test. Either way,
the use case itself is never a module:

> **A use case is a thin flow over the domain, proven by one test.**

(UC-06's whole acceptance is `curve.to_speed(N).to_speed(N0)` round-tripping to
`< 1e-6` — a use case expressed purely as a flow.)

## You are here

```
  S0 ✅  S1 ✅  S2 ✅  S3 ✅  S4 ✅  S5 ✅  S6 ✅  │  S7 ◀ YOU ARE HERE
  └──────────── MVP shipped & documented ─────────┘     └─ hardening / v1.1 ─→
```

Sprints S0–S6 built and documented the MVP. Everything from S7 onward is
turning your 10 *Proposed* ADRs into *Accepted* ones — paying down debt you
already identified, one ADR per sprint. That's it. No new mountains.

## The next sprints (sequenced for you)

Each row is one sprint-sized chunk tied to a decision you've **already made**.
Do them top to bottom. Don't skip ahead — the order goes cheap-and-safe first,
structural-and-deep later, features last.

| Next | Sprint | What it is | Backed by | Why this order |
|---|---|---|---|---|
| ◀ **now** | **S7 — Promote `mathx` into `pump`** | Finish moving water-density + spline into the library. `Water` class is **already done** ✅ — remaining: move `NaturalCubicSpline`/`r_squared`, decide on exact coefficients, delete the `pumpflow` copies, add tests. | [ADR 0009](adr/0009-promote-mathx-into-pump-library.md) | Already in flight — finish what's open before starting anything new. |
| 2 | **S8 — Correctness quick-wins (bundle)** | Three small fixes in one sprint: the Pint `NameError`, the Python-version floor, and version/deps alignment. | [ADR 0002](adr/0002-fix-pint-nameerror-in-units-core.md), [0003](adr/0003-correct-python-version-floor.md), [0010](adr/0010-align-versioning-and-declare-deps.md) | Tiny, safe, high-confidence. Momentum wins. |
| 3 | **S9 — Consolidate the `Point` hierarchy** | Kill the dead `Point` class; make `DesignPoint`/`TestPoint` the only path. | [ADR 0005](adr/0005-consolidate-point-hierarchy.md) | Unblocks cleaner refactors below. |
| 4 | **S10 — Replace `hasattr` duck-typing** | Make the optional-property handling explicit. | [ADR 0006](adr/0006-replace-hasattr-duck-typing.md) | Small, makes the next two safer. |
| 5 | **S11 — Split `PerformanceCurve` god-class** | Separate fitting / transforms / plotting responsibilities. | [ADR 0004](adr/0004-refactor-performancecurve-god-class.md) | The big structural one — do it once the easy cleanups are banked. |
| 6 | **S12 — Workbench hygiene** | Remove the ACL private-state leak; separate node logic from Qt dialogs. | [ADR 0007](adr/0007-remove-acl-private-state-leak.md), [ADR 0008](adr/0008-separate-node-logic-from-qt-dialogs.md) | UI-layer cleanup, isolated from physics. |
| 7+ | **v1.1 features** | New library capability, one UC per sprint: system curve (UC-03 → unblocks UC-04), NPSH (UC-05), impeller trim (UC-07), multi-pump compare (UC-08), pump catalogue (UC-01). | [use-cases.md](product/use-cases.md#deferred-to-v11-library-gaps--recorded-not-built-in-this-plan) | Only after the foundation is clean. Features on a shaky base cost double. |

When you finish a sprint, flip its ADR from **Proposed → Accepted**, add the row
to [the sprint index](sprints/README.md#sprint-index), and the next item becomes
"now." The list shrinks every time.

## Workflow: take one use case to production

This is the repeatable recipe. Run it once per use case — it's the same seven
steps every time, which is what stops a UC from feeling like an open-ended
project. (It mirrors your demo → assertion → pin → document → publish flow.)

1. **Frame it.** Confirm or write the UC entry in
   [use-cases.md](product/use-cases.md): *actor, trigger, input, output, and one
   concrete acceptance criterion.* If you can't state the acceptance in one
   sentence, the UC is still too vague to build.
2. **Find the gap.** Ask: does the domain capability this UC needs already exist
   in `pump/`? Check its status — ✅ means the nouns exist (it's just a flow); 🟡/❌
   means a capability is missing first.
3. **Capability first (only if there's a gap).** Add the missing **noun** to
   `pump/` — a class or method, `Q_`-in/`Q_`-out, with doctests. Never put physics
   in `pumpflow/`. This is the real work; the UC is thin on top.
4. **Write the acceptance test before the flow.** Put a failing demo in
   `tests/utilities_test.ipynb`, then promote it to a `test_*.py` assertion that
   expresses the UC *as a composition of capabilities* (like the `to_speed`
   round-trip). Red test = a precise target.
5. **Compose the flow.** Wire the capabilities into the user action: a library
   method/function, and — if it's a GUI flow — a `pumpflow` node that calls in
   **only** through `binding.py`. Make the test go green.
6. **Verify against the reference.** Match the reference notebook
   (`pump_api610_performance 1.ipynb`) and the API 610 tolerances. Numbers must
   agree, not just "run without error."
7. **Document & publish.** Docstrings on new capabilities; flip the UC status in
   use-cases.md (❌/🟡 → ✅); add a CHANGELOG entry; close the sprint (ADR → Accepted,
   sprint index updated).

### A use case is "in production" when…

- [ ] Its capability lives in `pump/` (not `pumpflow/`), with doctests.
- [ ] One `test_*.py` proves the flow against the reference / tolerances, and it's green.
- [ ] It's reachable by the user — a library call *and*, where relevant, a `pumpflow` node.
- [ ] use-cases.md shows it ✅, CHANGELOG mentions it, the sprint is committed.

Until all four are true, it's *in progress*, not done. When they're all true,
move to the next UC and don't look back.

## When you're stuck *inside* a sprint

Not "too much to do" but "stuck on this one thing":

1. **Shrink the unit.** A sprint too big to start is two sprints. Split it.
2. **Write the assertion first.** Your whole workflow is demo → assertion →
   pin. Put the failing test in `tests/utilities_test.ipynb` or a `test_*.py`
   *before* the code. Now you're not "building a feature," you're "making one
   line go green."
3. **One commit, one branch.** If the diff is sprawling, you took on too much —
   stash, narrow, resume.
4. **Stay inside the rules you already wrote.** Physics only in `pump`; the
   workbench only calls in via `binding.py`; always pass `Q_`. These aren't
   constraints slowing you down — they're decisions you *don't have to make
   again.*

## What "done" looks like

So the finish line is real and not infinite:

- **v1.0 (done-ish now):** UC-02, UC-06, UC-09 work; docs published. ✅
- **v1.0.x (S7–S12):** all 10 ADRs Accepted — clean, tested foundation.
- **v1.1 (features):** the deferred UCs, one per sprint, on a clean base.

That's the whole journey. Seven sprints behind you, roughly six of hardening
ahead, then features at your own pace. Open S7. Ignore the rest.
