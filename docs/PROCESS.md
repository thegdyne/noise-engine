# Noise Engine Process

**Keep it lean. Ship things.**

---

## Feature Tiers

| Size | Examples | What you need | Time |
|------|----------|---------------|------|
| **Large** | FX System, Preset System | Spec + Rollout + CI gate | 1+ week |
| **Medium** | Keyboard Mode, MIDI Learn | Spec only | 2-5 days |
| **Small** | EQ labels, shortcuts | Just do it | < 1 day |

**Rule:** If you're writing more process than code, stop and reconsider.

---

## Spec Format (Large + Medium)

```markdown
---
status: draft | approved
---
# Feature Name

## What
One paragraph explaining what this does.

## Why
One paragraph explaining why we need it.

## How
Key technical decisions. Not exhaustive — just the important bits.

## Phases (Large only)
1. Phase name — what it delivers
2. Phase name — what it delivers

## Open Questions
- Things to figure out
```

That's it. No 500-line specs.

---

## Rollout Format (Large only)

```markdown
---
feature: Feature Name
status: draft | approved
---
# Feature Rollout

## Phase 1: Name
**Goal:** One sentence.
**Tasks:** Bullet list.
**Tests:** What to verify.
**Done when:** Exit criteria.

## Phase 2: Name
(same format)
```

---

## Backlog

One file: `BACKLOG.md`

```markdown
# Backlog

## Now
- [ ] Current focus item

## Next
- [ ] Item with approved spec
- [ ] Item with approved spec

## Mopup
- [ ] Small fix
- [ ] Small fix

## Ideas
- Future thing (no commitment)
```

No Jira. No Trello. No complex tracking. Checkboxes in markdown.

---

## Session Types

Before starting, decide what kind of session this is:

| Type | Duration | Do this | Don't do this |
|------|----------|---------|---------------|
| **Plan** | 30-60 min | Write specs, discuss design | Write code |
| **Build** | 2-4 hours | Implement one phase | Start new features |
| **Mopup** | 30-60 min | Clear small items | Start big things |
| **Review** | 30 min/week | Update backlog, check progress | Write code |

**Don't mix session types.** Mixing = half-finished everything.

---

## CI Gate (Large features only)

The spec-check workflow blocks PRs that touch gated paths without an approved spec and rollout.

Gated paths:
- `src/gui/fx*` → FX spec + rollout
- `src/gui/preset*` → Preset spec + rollout  
- `src/gui/imaginarium*` → Imaginarium spec + rollout

Everything else? No gate. Just ship it.

---

## Warning Signs (Claude will call these out)

🚩 **Over-engineering:**
- Spec longer than the code it describes
- Process docs for small features
- Multiple tracking systems
- Discussing process instead of building

🚩 **Under-engineering:**
- Large feature with no spec
- "I'll figure it out as I go" on complex systems
- Skipping tests on core functionality

---

## The Goal

Process exists to help you ship. If it's not helping, cut it.

Ask: "Will this process step catch a real problem, or does it just feel productive?"

---

*Last updated: December 2025*
