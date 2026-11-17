# Training

Self-paced training for engineers who witness API 610 pump Factory Acceptance Tests with
`centrifugal-pump`.  Each module has three parts:
- a **guide** (this folder): what to check and why, with clause references;
- a **worked notebook** in [`use_cases/`](../../use_cases/) that runs the checks with the
  `pump` library and asserts the answers;
- **exercises** with answers at the end of the guide.

| Module | Topic | Notebook | Time |
|---|---|---|---|
| [TR-01](TR-01-witness-performance-test.md) | Witnessing an API 610 performance test: which tolerances apply, how to judge head, power, shut-off, efficiency, NPSH and vibration, and the traps | [`TR-01_witness_training.ipynb`](../../use_cases/TR-01_witness_training.ipynb) | about 2 h |

## Before you start

Read these concept pages first, or keep them open:
- {doc}`../concepts/head-components`: how head is computed from the gauges;
- {doc}`../concepts/affinity`: correcting the test to rated speed;
- {doc}`../concepts/acceptance-tolerances`: the tolerance tables, edition by edition;
- {doc}`../concepts/npsh`: NPSHa, NPSH3 and the two NPSH rules;
- {doc}`../concepts/mechanical-run`: the running test and vibration in RMS.

The use-case notebooks (UC-02 performance verification, UC-05 NPSH, UC-11 mechanical
run) are the worked examples behind each step.

## Sources

The tolerance values were checked on 2026-11-16 against the owner's licensed copies of
API 610 8th, 11th and 12th editions and Petrobras N-553 rev D and rev E.  Those texts are
**not** in the repository.  The training quotes clause numbers and short phrases only:
consult your own copy of the standard for the full text.
