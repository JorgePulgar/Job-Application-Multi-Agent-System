# Phase 10.5 · Task 04 — Research fan-out (company / sponsorship / profile-match)

## Objective
Three parallel branches off `ingest_offer`, merged by `assess_fit`. This is the
fan-out/fan-in that justifies LangGraph over a chain.

## Acceptance criteria
- [ ] Fan-out wired with conditional `Send` (or parallel edges) from
      `ingest_offer` to all three branch nodes; all write disjoint state keys.
- [ ] `src/graph/nodes/research_company.py` → `{"dossier": CompanyDossier}`.
      **Reuses the existing `CompanyResearcher`** agent + web search; does not
      reimplement research. Skips/reuses if the company already has a dossier.
- [ ] `src/graph/nodes/sponsorship.py` → `{"sponsorship": SponsorshipSignal}`.
      `gpt-4o-mini`, structured output. Encodes the visa/geo logic from the skill:
      needs-sponsorship?, offered?, geo-viable-for-Spain (remote-EU/relocation)?,
      working language, decisive blocker. Prompt in
      `src/prompts/graph_sponsorship.{system,user}.md`.
- [ ] `src/graph/nodes/match_profile.py` → `{"requirements": RequirementMatch}`.
      `gpt-4o`, structured output. Maps each required/preferred skill to
      met/partial/missing against the user `YAML` profile; fills `standout_points`
      and `gaps`. Prompt in `src/prompts/graph_match.{system,user}.md`.
- [ ] Profile comes from `config/users/{username}.yaml` via the existing loader —
      **NOT** Claude memory (the skill's "memory wins" rule does not apply in a
      deployed graph).
- [ ] All three nodes use services-layer clients; caching enabled on stable system
      prompts + the CV.

## Files to create / modify
- `src/graph/nodes/research_company.py`
- `src/graph/nodes/sponsorship.py`
- `src/graph/nodes/match_profile.py`
- `src/prompts/graph_sponsorship.{system,user}.md`
- `src/prompts/graph_match.{system,user}.md`
- `tests/unit/test_node_research_fanout.py`

## Dependencies
- Task 03.

## Estimated effort
**L**

## Testing notes
Mock LLM + `CompanyResearcher` + `search_web`. Assert all three keys are present
after the fan-out and that `match_profile` reads the YAML profile, not memory.
Assert a US-onsite-no-sponsorship JD yields `geo_viable_for_spain=False` + a
`blocker`.
