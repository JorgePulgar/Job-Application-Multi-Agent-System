# Phase 10.5 · Task 05 — assess_fit fan-in node + rubric prompt

## Objective
Merge the three branches into a single honest `FitAssessment`, encoding the
skill's decision rubric.

## Acceptance criteria
- [ ] `src/graph/nodes/assess_fit.py` → `{"fit": FitAssessment}`. `gpt-4o`,
      `response_format=FitAssessment`.
- [ ] Reads `parsed`, `dossier`, `sponsorship`, `requirements` from state.
- [ ] Prompt `src/prompts/graph_assess_fit.{system,user}.md` encodes README §6:
      - Hard SKIP blockers ONLY: no-right-to-work/sponsorship-not-offered,
        geo-lock excluding Spain, missing required language, stealth-senior (4+ yrs
        for a "junior" title).
      - Soft gaps NEVER a SKIP alone: missing degree, 1-2 yrs experience.
      - Unknowns go to `missing_info`, not invented.
      - `tailoring` populated only when recommendation is apply/maybe.
- [ ] Few-shot with 2-3 examples covering apply / maybe / skip (mirrors v1
      evaluator convention).
- [ ] `score` (0-100) consistent with `fit_level`/`recommendation`.
- [ ] User-facing text (`reasoning`, `red_flags`, `tailoring`) emitted in
      `parsed.detected_language`.

## Files to create / modify
- `src/graph/nodes/assess_fit.py`
- `src/prompts/graph_assess_fit.system.md`
- `src/prompts/graph_assess_fit.user.md`
- `tests/unit/test_node_assess_fit.py`

## Dependencies
- Task 04.

## Estimated effort
**M**

## Testing notes
Mock LLM. Assert: a missing-degree-only case does NOT yield `skip`; a
sponsorship-needed-not-offered case DOES yield `skip` with a red flag; `tailoring`
is `None` on skip.
