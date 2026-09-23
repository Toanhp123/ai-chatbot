# Architecture Decision Records

Use ADRs for decisions that materially constrain future implementation, change a frozen baseline, create a new cross-cutting contract, or select a difficult-to-reverse implementation mechanism.

Naming:

`NNNN-short-kebab-title.md`

Lean template:

```md
# ADR-NNNN — Title

- Status: proposed | accepted | superseded | rejected
- Date: YYYY-MM-DD
- Class: FROZEN change | cross-cutting implementation | compatibility | security | other
- Supersedes: D-xxx / ADR-NNNN / none
- Superseded by: none

## Context

What concrete evidence or requirement forces a decision now?

## Decision

What is chosen? State normative rules precisely.

## Consequences

What becomes easier/harder? What compatibility/migration cost follows?

## Alternatives considered

What credible alternatives were considered and why were they not selected?

## Fitness / verification

What automated test, architecture check, E2E, metric, or observable evidence proves the decision remains true?

## Revisit trigger

What specific evidence should reopen this decision?
```

Rules:

- Do not write an ADR for trivial/local reversible detail.
- A proposed ADR does not authorize implementation that violates the current baseline.
- A superseding ADR must update `../DECISIONS.md` and every canonical owner it changes in the same change.
- Prefer objective fitness functions/tests for rules that can be mechanically enforced.
