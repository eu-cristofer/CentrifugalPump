# Spec-Driven Software Engineering: Adapting the CentrifugalPump Project to the OpenSpec Methodology

## Executive Summary
This analysis evaluates the adoption of the OpenSpec methodology within the `CentrifugalPump` project. By transitioning from the repository's custom, sequential 8-hour sprint framework to an integrated, spec-driven development paradigm, the project can mitigate architectural drift, establish persistent AI-agent context, and streamline the upcoming transition from the desktop-first PySide6 graphical interface to a modern, client-server web architecture. Grounded in the academic and empirical software engineering literature, this report outlines the theoretical fundamentals, evaluates the decision-to-implement trade-offs, and provides an actionable implementation roadmap.

---

## 1. Theoretical Fundamentals of OpenSpec
The OpenSpec framework is a modern synthesis of several core software engineering and requirements engineering methodologies: Specification-by-Example (SBE), Behavior-Driven Development (BDD), and Living Documentation. To understand OpenSpec, we must examine its foundational pillars.

### 1.1 Specification-by-Example (SBE) and Behavior-Driven Development (BDD)
Specification-by-Example (SBE) is a set of practices that builds a shared understanding of software requirements based on concrete examples rather than abstract declarations (Adzic, 2011). Behavior-Driven Development (BDD) extends this concept by using a domain-specific, natural-language DSL (Domain-Specific Language)—typically using the Gherkin syntax (GIVEN-WHEN-THEN)—to describe system behaviors (North, 2006).

OpenSpec integrates SBE and BDD into the planning phase. Rather than writing code and validating it after the fact, requirements are documented as structured scenarios:
* **GIVEN (Preconditions):** Establishes the initial state of the system (e.g., a specific fluid density and design point).
* **WHEN (Triggers):** Describes the action or event that occurs (e.g., evaluating compliance against API 610).
* **THEN (Expected Outcomes):** Dictates the verifiable change in state or output (e.g., returning a specific head tolerance verdict).

In traditional development, these specifications are either locked in detached wikis or compiled as unit tests. OpenSpec keeps them in the repository as markdown documents, which are highly readable for human developers and parseable for autonomous coding agents.

### 1.2 Living Documentation
Documentation in software projects frequently suffers from *documentation drift*, where the written requirements diverge from the actual behavior of the codebase as code is refactored (Martraire, 2019). Traditional "waterfall" requirements engineering (Larman & Basili, 2003) fails because it separates planning from implementation.

Martraire (2019) advocates for "Living Documentation," which posits that documentation must be:
1. **Colocated with the codebase:** Checked into the same Git repository.
2. **Versioned alongside code changes:** Captured as a single, atomic commit or pull request.
3. **Structured for queryability:** Capable of being indexed by developers, tools, and agents.

OpenSpec implements this by standardizing the directory layout (`openspec/specs/`) and organizing requirements by capabilities rather than file structures. It preserves functional requirements as a living asset, rather than throwing them away after planning.

### 1.3 Traceability and Change Proposals
Software traceability (Cleland-Huang et al., 2014) is the ability to link requirements, technical designs, implementation tasks, and actual code changes. High traceability reduces regression risks and prevents architectural drift during refactoring.

OpenSpec enforces traceability via **Change Proposals**. Every modification to the system is packaged in a self-contained directory (`openspec/changes/<change-id>/`) before coding begins:
* `proposal.md`: Captures the business case and intent.
* `design.md`: Documents technical design decisions and API contracts.
* `tasks.md`: Lists atomic, actionable development tasks.
* `specs/`: Isolates *spec deltas* (diffs of requirements) demonstrating how the change modifies system behavior.

This creates a pre-code safety net, catching misalignment before developers (or coding agents) write buggy implementations.

---

## 2. Evaluation: Should You Implement This?
To determine whether the `CentrifugalPump` project should adopt OpenSpec, we conduct a cost-benefit analysis based on the codebase's existing architecture.

### 2.1 Technical and Strategic Alignment
The `CentrifugalPump` project is characterized by a strong architectural boundary (the Anti-Corruption Layer in `pumpflow/binding.py`) that separates the headless domain library (`pump/`) from the GUI front-end (`pumpflow/`). 

#### Advantages of Adoption:
1. **Mitigation of Interface Leaks:** As the project moves toward a web architecture, keeping API data contracts (Pydantic schemas and endpoints) documented in a central, living spec (`openspec/specs/`) ensures that the frontend and backend teams (or agents) remain fully aligned on boundaries.
2. **AI-Agent Context Persistence:** Standard LLMs lose state and context between conversational sessions. In a repository without specs, an agent must "re-discover" the codebase structure via grepping and reading raw code on every run. By maintaining capability specifications in `openspec/specs/`, incoming agents immediately read these specs as their "source of truth," minimizing errors and hallucinated patterns.
3. **Formalizing the Sprint Lifecycle:** Currently, the project uses custom sprint markdown files (`docs/sprints/`). While highly disciplined, this is a hand-managed, non-standard format. Transitioning to OpenSpec's Change Proposal system standardizes your sprint workflows into a tool-agnostic, professional framework.

#### Disadvantages and Overhead:
1. **Maintenance Overhead:** In the early stages of rapid prototyping, writing formal specifications and change deltas can introduce a "planning tax." If a change is extremely trivial, writing a proposal might feel redundant.
2. **Methodology Discipline:** Spec-driven development succeeds only if developers commit to updating the specifications alongside code changes. If specifications are ignored, they revert to stale, dead documentation.

### 2.2 Decision Matrix
| Parameter | Current Model (Custom Sprints) | OpenSpec Model |
|---|---|---|
| **Specification Format** | Freeform markdown in notebooks and sprints | Structured Gherkin-style living specifications |
| **Traceability** | Implicit (relying on manual links in sprint files) | Explicit (via consolidated change package folders) |
| **Tool Integration** | Low (not integrated with AI/CLI agents natively) | High (natively parsed by OpenCode, Claude Code, etc.) |
| **Documentation Health** | High risk of drift as features evolve | Low risk of drift (specs are updated in lockstep with PRs) |

**Recommendation:** **Implement immediately.** The high degree of modular separation in your codebase makes it exceptionally well-suited for a spec-driven framework. The long-term benefits of AI context retention and streamlined API-boundary design heavily outweigh the minor overhead of requirements writing.

---

## 3. Implementation Roadmap: How and When

We recommend a phased roll-out that avoids halting development. Instead, the OpenSpec framework will be built out incrementally alongside your existing feature work, adhering to OpenSpec's "brownfield-first" philosophy.

### 3.1 Step-by-Step "How" Guide

#### Step 1: Install the CLI and Initialize the Structure
First, install the OpenSpec CLI globally to access standard scaffolding commands:
```bash
npm install -g @fission-ai/openspec@latest
```
Create the directory structure under your root directory:
```bash
mkdir -p openspec/specs/core-physics
mkdir -p openspec/specs/compliance-api610
mkdir -p openspec/specs/report-generation
mkdir -p openspec/specs/dataflow-workbench
mkdir -p openspec/changes
```

#### Step 2: Write Baseline Specs for Existing Core Capabilities
Do not try to document every line of code. Focus on the core system boundaries. Draft the baseline specs under `openspec/specs/`.

##### Example: `openspec/specs/compliance-api610/spec.md`
```markdown
# API 610 Compliance Specification

## Purpose
Evaluate a centrifugal pump's hydraulic performance curve against API 610 standards.

## Requirements

### Requirement: Shutoff Head Limit
The shutoff head of a pump SHALL be limited within specified performance bands relative to the rated design point.

#### Scenario: Verify compliance for compliant shutoff head
  GIVEN a DesignPoint with capacity 833 m3/h and head 73 m
  AND a PerformanceCurve with a shutoff head of 85 m
  WHEN evaluating API 610 compliance
  THEN the compliance verdict for shutoff head SHALL be COMPLIANT

#### Scenario: Verify compliance for non-compliant shutoff head
  GIVEN a DesignPoint with capacity 833 m3/h and head 73 m
  AND a PerformanceCurve with a shutoff head of 117 m
  WHEN evaluating API 610 compliance
  THEN the compliance verdict for shutoff head SHALL be NON_COMPLIANT
```

#### Step 3: Transition from Custom Sprints to OpenSpec Change Proposals
For your next milestone—developing the FastAPI web backend—initiate an OpenSpec change:
```bash
# This creates openspec/changes/s07-web-backend-api/
/openspec:proposal Scaffold FastAPI web backend for headless calculations
```
Inside the generated folder, fill out `design.md` detailing how the Pydantic schemas map to `pumpflow/signals.py` dataclasses, and structure your implementation tasks inside `tasks.md`.

---

### 3.2 Roadmap: "When" to Execute

```
               [ NOW ]
                  │
                  ▼
┌────────────────────────────────────────┐
│ Phase 1: Baseline Documentation        │ (Duration: 2-4 Hours)
│ - Scaffold openspec/ directory         │
│ - Draft baseline specifications for:   │
│   - core-physics (Pint units)          │
│   - compliance-api610                  │
│   - dataflow-workbench (signals)       │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Phase 2: Web API Transition (S7)       │ (Duration: Core S7 Sprint)
│ - Initialize Change Proposal:          │
│   "s07-web-backend-api"                │
│ - Design API contracts in design.md    │
│ - Execute development using tasks.md   │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Phase 3: Continuous Integration        │ (Duration: Post-Sprint 7)
│ - Integrate specs in PR reviews        │
│ - Run OpenSpec CLI to check spec deltas│
│ - Maintain living documentation        │
└────────────────────────────────────────┘
```

---

## 4. References

* Adzic, G. (2011). *Specification by Example: How Successful Teams Deliver the Right Software*. Manning Publications.
* Cleland-Huang, J., Gotel, O., & Huffman Hayes, J. (2014). *Software and Systems Traceability*. Springer.
* Larman, C., & Basili, V. R. (2003). Iterative and incremental development: A brief history. *Computer*, 36(6), 47-56.
* Martraire, C. (2019). *Living Documentation: Continuous Knowledge Sharing with Lean and Agile Software Development*. Addison-Wesley Professional.
* North, D. (2006). Introducing BDD. *Better Software*, 8(3), 22-27.
