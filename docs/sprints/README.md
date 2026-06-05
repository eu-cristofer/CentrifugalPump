# Sprints

Work on CentrifugalPump is organized into **8-hour programming sprints**. Each
sprint is one focused `.md` file in this directory, sized so the task-checklist
hour estimates sum to ~8 h, and lands as a single commit on its branch.

This is example-driven development seeded by
[`tests/utilities_test.ipynb`](../../tests/utilities_test.ipynb): demos become
*assertions*, behaviour gets pinned, then documented and published. Priorities
follow the [audience](../product/audience.md) and
[use-case registry](../product/use-cases.md) — the FAT engineer (UC-02, UC-06,
UC-09) comes first.

## Sprint index

| Sprint | Title | Linked UC | Status |
|--------|-------|-----------|--------|
| [S0](sprint-00-product-context.md) | Product context & sprint scaffold | — | ✅ done |
| [S1](sprint-01-test-foundation.md) | Test foundation + units spec | UC-02 (foundation) | ✅ done |
| [S2](sprint-02-pin-mvp-physics.md) | Pin the MVP physics | UC-02, UC-06 | ✅ done |
| [S3](sprint-03-gui-openable-case.md) | GUI-openable case + persistence guard | UC-02, UC-09 | ✅ done |
| [S4](sprint-04-docstrings-doctests.md) | Docstrings & doctests | — | ✅ done |
| [S5](sprint-05-read-the-docs.md) | Read the Docs (Sphinx + autodoc) | — | ✅ done |
| [S6](sprint-06-readme-wrap.md) | Repo README + wrap | UC-09 (note) | ⬜ todo |

**Total: 7 sprints × 8 h ≈ 56 h.**

## Sprint template

Copy this for new sprints:

```markdown
# Sprint SN — <title> (8 h)

- **Goal:** <one sentence — the observable outcome>
- **Persona / UC:** <primary persona> · <UC-0N links>
- **Branch / commit:** <branch> — one commit

## Tasks (≈ 8 h)

- [ ] Task A — ~Xh
- [ ] Task B — ~Yh
- [ ] Task C — ~Zh   (estimates sum to 8)

## Files touched

- Create / Modify / Delete: <paths>

## Acceptance criteria

- <observable, testable outcome 1>
- <observable, testable outcome 2>

## Definition of Done

- [ ] All tasks checked, tests green, committed.
```
