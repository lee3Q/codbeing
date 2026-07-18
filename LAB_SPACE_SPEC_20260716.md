# codbeing Lab Space Spec

Date: 2026-07-16

## One-Line Identity

codbeing is a private consciousness laboratory where Sanggyu Lee can face himself as code, talk with research staff, run situation simulations, and update an evidence-grounded model of his own runtime.

## Product Position

codbeing is not starting as a SaaS product, counseling app, or general productivity tool.

The first version is a personal dogfooding lab for one user. If it becomes obviously useful through repeated personal use, the later direction is to open-source the framework so anyone can create their own private lab.

This order must not be reversed:

1. Make it genuinely useful for the owner.
2. Accumulate real personal runtime traces.
3. Prove that the lab produces insight worth returning to.
4. Only then generalize into an open-source personal lab framework.

## Core Feeling

Entering codbeing should feel like entering a research lab, not launching a command-line utility.

The user should feel:

- I am entering a place.
- The central asset of this place is "me as code."
- The staff here are not generic chatbots; they are researchers assigned to study and guide my runtime.
- I can either talk to researchers or avoid conversation and use structured choices/simulations.
- Every interaction leaves usable data, unless I explicitly mark it as not for analysis.

## Lab Map

### 1. Entrance

Purpose: establish the lab state and offer the next meaningful action.

The entrance should show:

- current runtime signal level
- latest available report
- available research staff
- active simulations
- whether external model assist is off/local/GLM
- 2-4 context-aware next actions

The entrance should not feel like a help page. It should feel like a control room.

### 2. Self Code

Purpose: let the user face "me as code."

Self Code is the evolving representation of the user's runtime. It should not present fixed personality labels. It should present evidence-backed modules.

Example modules:

- activation triggers
- judgment basis
- rejected options
- recurring avoidance
- hard mirror gates
- regret/reversal loops
- decision protocols
- current unresolved contradictions

Each module should include:

- current hypothesis
- supporting evidence
- confidence level
- missing data
- last updated time
- user override or correction

### 3. Research Staff Room

Purpose: talk with researchers, not generic assistants.

Research staff are persistent lab roles with distinct temperaments. Their tone should be configurable by the user.

Initial staff set:

- Analyst: structures traces and extracts runtime patterns.
- Hard Mirror: challenges self-excusing conclusions and weak logic.
- Simulator: creates situations and observes user reactions.
- Archivist: organizes evidence, summaries, and report history.
- Guide: suggests the next experiment or action without overloading the user.

Researcher settings:

- warmth
- directness
- pressure level
- humor
- distance/formality
- intervention strength

Research staff should be allowed to disagree with each other in future versions, but MVP can keep them as selectable roles.

### 4. Simulation Room

Purpose: collect runtime data without requiring open-ended conversation.

The user can enter a situation and respond through choices, short text, or staged dilemmas.

Simulation types:

- decision pressure
- conflict
- opportunity cost
- rejection/failure
- status threat
- delayed gratification
- moral compromise
- career/academic fork

Each simulation should produce:

- selected path
- hesitation or reversal if captured
- inferred trigger
- affected Self Code modules
- confidence delta
- suggested follow-up

### 5. Evidence Vault

Purpose: preserve the evidence trail behind every analysis.

The vault stores structured traces, reports, simulations, and user corrections.

Rules:

- private-first
- local by default
- no telemetry
- no raw personal logs unless explicitly imported
- no external model call without explicit selection and key availability
- every analysis claim must be traceable to evidence or marked as low-confidence inference

### 6. Analysis Chamber

Purpose: produce Runtime Analysis from accumulated evidence.

The analysis output should remain compatible with the existing codbeing claim:

- activation triggers
- judgment shifts
- baseline deviation
- contradiction/correction points
- regret/reversal loops
- likely internal reaction path
- decision protocol for the current case

The chamber should always show confidence and data sufficiency.

Output tiers:

- Insufficient Runtime Signal
- Mirror Only
- Hypothesis Draft
- Runtime Analysis
- Hard Mirror

## Interaction Modes

### Conversation Mode

The user speaks with a selected researcher.

The researcher can:

- ask questions
- interpret traces
- suggest simulations
- update Self Code hypotheses
- produce a report draft

Nothing should be permanently absorbed into Self Code without a visible confirmation or review path.

### Choice Mode

The user avoids open conversation and selects from structured actions.

Choice Mode should support:

- pick a simulation
- answer staged prompts
- inspect Self Code
- generate a report
- correct a hypothesis
- choose next experiment

Choice Mode is not a degraded version of the product. It is a first-class path.

### Hybrid Mode

The user can start in choices, then hand off to a researcher, or start in conversation and switch to simulation.

## Data Depth Principle

codbeing should not require one fixed amount of personal data.

The amount of data needed depends on:

- user goal
- desired confidence level
- sensitivity of the decision
- current mental state
- quality of prior traces
- whether the user wants a rough mirror or a high-confidence analysis

The system should say:

- what it can infer now
- how confident it is
- what data is missing
- what small experiment would raise confidence

It should not pretend that low-data analysis is high certainty.

## Deferred Features

These are intentionally not core for the next build:

- public accounts
- multi-user SaaS
- payment
- external sharing
- polished public onboarding
- open-source packaging
- 3D lab environment
- voice interface

They may matter later, but they should not distort the personal dogfooding MVP.

## MVP Success Criteria

The next codbeing UX iteration succeeds if:

1. Running `cb` feels like entering codbeing, not reading command help.
2. The user can see the state of the lab immediately.
3. The user can choose a researcher, simulation, or analysis path without memorizing commands.
4. Conversation and non-conversation paths both create usable runtime evidence.
5. Self Code feels like an evolving model of the user, not a static personality report.
6. Every analysis shows evidence, confidence, and missing data.
7. The user wants to return after real decisions because the lab has accumulated memory and context.

## Near-Term Build Direction

The current CLI can evolve into a terminal lab before any web app is built.

Recommended next step:

- `cb` opens an interactive lab entrance.
- The entrance detects traces/reports/config.
- It presents 2-4 context-aware options.
- Selecting an option enters a room-like flow:
  - Self Code
  - Research Staff
  - Simulation Room
  - Analysis Chamber
  - Evidence Vault
- Existing power-user commands remain available.

The implementation should preserve the current privacy baseline and local-first behavior.
