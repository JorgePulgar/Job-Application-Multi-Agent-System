# Phase 11 · Task 03 — WarmMessageWriter agent

## Objective
Generate a short Spanish warm-outreach message for an outreach target, following strict tone rules.

## Acceptance criteria
- [ ] `src/agents/warm_message_writer.py` implements `class WarmMessageWriter` with `async def write(self, target, company, profile, manual_context: Optional[str] = None) -> WarmMessageDraft`.
- [ ] `WarmMessageDraft` Pydantic model: `mensaje: str`, `length_mode: Literal["connection_request"|"follow_up"]`, `needs_manual_context: bool`, `flagged_reasons: list[str]`.
- [ ] Length: `connection_request` ≤ 300 chars, `follow_up` 600-800 chars. Mode picked by the agent based on context strength.
- [ ] Prompt rules (in `src/prompts/warm_message_writer.{system,user}.md`, Spanish):
  - Reference at least one specific fact about the person's work OR the company (from dossier or `manual_context`).
  - Tone: peer-to-peer, curious, low-pressure.
  - NEVER pitches, NEVER asks for a job, NEVER discloses AI assistance.
  - NEVER opens with: `espero que estés bien`, `vi tu perfil`, `estoy buscando oportunidades`.
  - Avoid the full prohibited words list from CLAUDE.md.
  - If no specific hook is available, return `needs_manual_context=True` with reasons.
- [ ] Reuses `draft_lint` (extended with warm-outreach-specific opener checks) — max 2 regen attempts, then flag.

## Files to create / modify
- `src/agents/warm_message_writer.py`
- `src/prompts/warm_message_writer.system.md`
- `src/prompts/warm_message_writer.user.md`
- `src/services/draft_lint.py` (extend with warm-outreach rules)
- `tests/unit/test_warm_message_writer.py`

## Dependencies
- Phase 11 / Tasks 01, 02

## Estimated effort
**M**

## Testing notes
Mock LLM. Cover: clean draft passes; draft with prohibited opener gets regenerated; no-hook scenario flags `needs_manual_context`. Length cap enforced.
