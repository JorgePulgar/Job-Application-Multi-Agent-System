# Phase 10.5 · Task 08 — draft_cover_letter node

## Objective
Final node: on approved APPLY/MAYBE, produce a tailored draft using the existing
proof-first rules and prohibited-words post-check.

## Acceptance criteria
- [x] `src/graph/nodes/draft.py` → `{"draft": CoverLetterDraft}`. `gpt-4o`,
      `response_format=CoverLetterDraft`.
- [x] Inputs: `parsed`, `dossier`, `fit.tailoring`, `human_decision.lead_angle`,
      the user profile/CV. Hook from `fit.tailoring.cover_letter_hook`.
      _lead angle = reviewer override if set, else the tailoring hook._
- [x] **Reuses the v1 prohibited-words + specificity post-check** (banned vocab,
      voice rules) — do not reimplement. Max 2 regen attempts; on failure set a
      `needs_manual_context` marker in state instead of shipping a generic draft.
      _New `draft_lint.lint_cover_letter` reuses the v1 `_check_*` primitives;
      flag = new state key `needs_manual_context` (returns draft=None)._
- [x] Disclosure rule honored: draft body NEVER mentions AI assistance. _Prompt
      forbids it + post-check has ES & EN disclosure patterns._
- [x] Specificity rule: must reference ≥1 concrete company fact from the dossier,
      else `needs_manual_context`. _Via reused `_check_specificity`._
- [x] Draft emitted in `parsed.detected_language` (English JD → English draft,
      Spanish JD → Spanish). Prohibited-words list applied per language.
- [x] **Add an English banned-cliché list** mirroring the v1 Spanish one
      (e.g. "passionate", "team player", "results-oriented", "go-getter",
      "hit the ground running") — the v1 list is Spanish-only. Post-check selects
      the list by `detected_language`. _`_PROHIBITED_EN_RAW` added; es uses the
      combined v1 list, en uses the English list._
- [x] Prompt `src/prompts/graph_draft.{system,user}.md` takes target language as a
      parameter.

## Files to create / modify
- `src/graph/nodes/draft.py`
- `src/prompts/graph_draft.system.md`
- `src/prompts/graph_draft.user.md`
- `tests/unit/test_node_draft.py`

## Dependencies
- Task 07.

## Estimated effort
**M**

## Testing notes
Mock LLM. Assert a draft containing a banned word triggers a regen; assert 2
failures yield `needs_manual_context`; assert no AI-disclosure string in body.
