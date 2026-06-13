# Phase 10.6 · Task 04 — `experience_level` on UserProfile + YAML

## Objective
Add a per-user seniority setting that drives experience-based search filtering
(Task 05) and is editable from the dashboard (Tasks 06/07). Define the level →
year-range and level → search-keyword mapping once, in the model, as the single
source of truth.

## Acceptance criteria
- [ ] New `ExperienceLevel(StrEnum)` in `src/models/user_profile.py`:
      `junior`, `mid`, `senior`. Each maps to an inclusive year range
      (`junior = 0–2`, `mid = 2–5`, `senior = 5+`) via a `year_range` property
      → `tuple[int, int | None]`.
- [ ] `UserProfile` gains `experience_level: ExperienceLevel | None = None`
      (optional ⇒ existing profiles stay valid; `None` = no seniority filter).
      Google-style docstrings on field + enum.
- [ ] Per-language search-keyword lists per level (es + en) on the enum/model,
      e.g. `junior` ⇒ es: `["junior", "trainee", "becario", "prácticas",
      "sin experiencia"]` / en: `["junior", "entry level", "graduate", "trainee"]`;
      `senior` ⇒ es: `["senior", "sénior", "lead"]` / en: `["senior", "lead",
      "staff"]`. Consumed by Task 05 — defined here.
- [ ] Both real YAMLs **and** both `*.yaml.example` get
      `experience_level: junior` (decided 2026-06-13: **Jorge and Madalina are
      both junior / no experience**) with an inline comment explaining the levels.
- [ ] `mypy --strict` passes; unit test: enum→year_range, enum→keywords(lang),
      profile loads with and without the field, bad value rejected.

## Implementation notes
- `UserProfile.from_yaml` does `model_validate`; an optional field with a default
  is backward-compatible. No DB column ⇒ no Alembic migration here.
- Settings **display + editing** of this field is handled in Tasks 06 (write API)
  + 07 (editable settings UI) — not in this task.
- Keep year ranges + keyword lists in **one** place so Task 05 and any future
  locale-aware prompt (Phase 12) reuse them.

## Files to create / modify
- `src/models/user_profile.py`
- `config/users/jorge.yaml`, `config/users/madalina.yaml`
- `config/users/jorge.yaml.example`, `config/users/madalina.yaml.example`
- `tests/unit/test_user_profile.py` (extend)

## Dependencies
- None (independent of Tasks 01–03).

## Estimated effort
**S**

## Testing notes
Unit-test the enum mapping + keyword lists, and that both shipped YAMLs validate
with `experience_level: junior`.
