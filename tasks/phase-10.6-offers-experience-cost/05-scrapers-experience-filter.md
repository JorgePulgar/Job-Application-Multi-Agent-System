# Phase 10.6 · Task 05 — Scrapers filter by experience

## Objective
Make the Adzuna and Jooble scrapers narrow their search to the user's
`experience_level` (Task 04) at scrape time — before any LLM spend — using native
platform filters where the API documents one, experience keywords otherwise, plus
a light post-fetch heuristic to drop obvious mismatches (e.g. junior search
returning a stealth-senior "5+ years" offer).

## Acceptance criteria
- [ ] Shared helper `src/services/experience_filter.py`: given an
      `ExperienceLevel` + target language, returns the keyword terms to add to a
      query and a `matches(level, title, description) -> bool` post-filter using
      the year-range + stealth-senior logic. No LLM — pure string/regex. Reuses
      the level→keywords and level→year_range from Task 04.
- [ ] **Adzuna** (`adzuna.py`): inject experience keywords into the documented
      query params (verify against the Adzuna API docs before using a param — do
      NOT invent params). Apply the post-filter. `experience_level is None` ⇒
      behavior unchanged.
- [ ] **Jooble** (`jooble.py`): add experience keywords to the POST `keywords`
      field; apply the post-filter. `None` ⇒ unchanged.
- [ ] No platform queried with a param absent from its official API docs. Where no
      native experience filter exists, the keyword + post-filter path runs and a
      debug log states which path executed.
- [ ] Rate-limit / pagination / dedup behavior preserved (`hash_unico` dedup
      across roles, per-minute interval).
- [ ] `mypy --strict` passes; `respx`-mocked tests assert: junior profile filters
      out a stealth-senior offer, senior profile keeps senior offers,
      `experience_level=None` returns the pre-existing result set.

## Implementation notes
- Confirmed scrapers in `src/agents/job_scraper/`: `adzuna.py`, `jooble.py`,
  `base.py`. No `wttj.py` (removed Phase 2/Task 09) — out of scope.
- `search(profile)` already receives the full `UserProfile`, so
  `profile.experience_level` is available without signature changes.
- Native-filter reality (verify, don't assume): Adzuna has no documented
  "experience" param; Jooble's public API is keyword/location/page only. So the
  keyword + post-filter path will likely be primary for both — satisfy the
  "native where available" criterion by checking and documenting that none exists.
- Keep heuristics conservative — a false drop hides a real offer. Drop only on
  explicit contradictions (junior search vs "5+ years required").

## Files to create / modify
- `src/services/experience_filter.py` (new)
- `src/agents/job_scraper/adzuna.py`
- `src/agents/job_scraper/jooble.py`
- `tests/unit/test_experience_filter.py` (new) + extend scraper tests

## Dependencies
- Task 04 (`experience_level` + mappings).

## Estimated effort
**M**

## Testing notes
`respx`-mocked responses with a mix of junior/mid/senior offers; assert filtered
output per level and the no-op when `experience_level is None`. Unit-test
`matches()` against stealth-senior phrasing in es + en.
