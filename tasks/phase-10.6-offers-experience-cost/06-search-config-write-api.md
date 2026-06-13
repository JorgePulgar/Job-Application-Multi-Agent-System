# Phase 10.6 · Task 06 — Search-config write API (per-user)

## Objective
Let each user change *what kind of offers they search for* from the dashboard, by
adding a write endpoint that persists the search-relevant subset of their profile.
The YAML stays the single source of truth (scrapers load `UserProfile.from_yaml`),
so the API edits and re-writes the user's YAML safely and validated.

## Acceptance criteria
- [x] New `PUT /users/{username}/search-config` (extend `api/routers/profile.py`
      or a new `search_config` router) accepting an editable subset:
      `target_roles`, `target_sectors`, `experience_level`,
      `location_preference` (modality + cities), `min_salary`. Other profile
      fields (CV, experiences, etc.) are **not** editable here.
      _Added to `profile.py`; `_EDITABLE_KEYS` allow-list bounds what is written._
- [x] Write path: load existing YAML → patch only the submitted fields →
      re-validate the **whole** profile through `UserProfile.model_validate` →
      write back to `config/users/{username}.yaml` preserving the non-edited
      fields. Reject (422) if validation fails; never write a partial/invalid file.
      _`test_put_updates_and_preserves_cv` asserts CV/experiences/email untouched;
      validation failure returns 422 before any write._
- [x] Input validated against Pydantic: `experience_level` must be a valid
      `ExperienceLevel`; `target_roles` non-empty; `min_salary` positive or null;
      `modality` a valid `Modality`. Unknown/extra keys rejected.
      _`SearchConfig` (+ `LocationPreferenceIO`) with `extra="forbid"` and
      field validators; FastAPI auto-422s the body._
- [x] Concurrency-safe enough for single-user local use: read-modify-write under a
      simple file lock or atomic temp-file replace (write temp, `os.replace`).
      No data loss on a malformed request.
      _`_atomic_write_yaml`: `tempfile.mkstemp` in the same dir + `os.replace`;
      temp cleaned on failure. 422 paths assert the file is byte-identical._
- [x] A matching `GET /users/{username}/search-config` returns just the editable
      subset (so the settings form can populate without dumping the whole CV).
      _`get_search_config`; `test_get_search_config_subset` asserts no `cv_summary`._
- [x] `mypy --strict` passes; tests: valid update round-trips and preserves CV
      fields; invalid `experience_level`/empty `target_roles` ⇒ 422 and file
      unchanged; non-existent user ⇒ 404.
      _mypy --strict green; `tests/integration/test_api_search_config.py` (8 tests)._

## Implementation notes
- `api/routers/profile.py` already reads `profiles_dir / f"{username}.yaml"` via
  the `get_profiles_dir` dependency — reuse it for the write path.
- Preserve YAML readability on write (`yaml.safe_dump`, `sort_keys=False`,
  `allow_unicode=True`) so the file stays human-editable + diff-friendly.
- This is the only write path to profile YAML; keep the editable allow-list
  explicit and small so the dashboard can never clobber CV/experience data.
- The user profiles are gitignored (`config/users/*` except `*.example`), so this
  writes runtime state, not committed config.

## Files to create / modify
- `api/routers/profile.py` (or new `api/routers/search_config.py`) + register
- `api/schemas.py` (SearchConfig in/out schema)
- `tests/unit/test_api_search_config.py` (new)

## Dependencies
- Task 04 (`experience_level` field must exist on the model).

## Estimated effort
**M**

## Testing notes
Round-trip test in a temp profiles dir: seed a full YAML, PUT a new
`target_roles` + `experience_level`, assert the file re-validates, the edited
fields changed, and CV/experiences are untouched. Assert atomic-replace leaves the
original intact on a validation failure.
