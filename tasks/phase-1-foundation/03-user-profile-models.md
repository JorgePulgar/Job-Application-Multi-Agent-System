# Phase 1 · Task 03 — User profile Pydantic models

## Objective
Pydantic v2 models that validate the user profile YAML described in CLAUDE.md §3. These models become the canonical user representation used by every agent.

## Acceptance criteria
- [ ] `src/models/user_profile.py` defines:
  - `Experience` (company, role, start_date, end_date, achievements: list[str], technologies: list[str])
  - `Education` (institution, degree, start_date, end_date)
  - `Certification` (name, issuer, date)
  - `LocationPreference` (modality: enum `remote|hybrid|onsite`, cities: list[str])
  - `UserProfile` (username, nombre, email, phone, location, target_roles, target_sectors, tech_stack, languages, min_salary: Optional[int], location_preference, red_flags: list[str], cv_summary: str, experiences, education, certifications)
- [ ] All models use Pydantic v2 (`model_config = ConfigDict(...)`, validators with `@field_validator` / `@model_validator`).
- [ ] `username` must be lowercase, alphanumeric/underscore, 2-32 chars (validator).
- [ ] `email` validated as email format.
- [ ] `min_salary`, if set, must be a positive int.
- [ ] Helpers `UserProfile.from_yaml(path: Path) -> UserProfile` and `UserProfile.cv_for_prompt() -> str` (markdown formatted) exposed.

## Files to create / modify
- `src/models/__init__.py`
- `src/models/user_profile.py`
- `tests/unit/test_user_profile_models.py`

## Dependencies
- Phase 1 / Task 01

## Estimated effort
**M**

## Testing notes
Round-trip a minimal valid YAML into `UserProfile` and back; assert each validator rejects bad input (invalid username, negative salary, malformed email). Verify `cv_for_prompt()` is deterministic.
