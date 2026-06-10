# Phase 10.5 · Task 07 — human_review interrupt + SqliteSaver checkpointer

## Objective
Human-in-the-loop via `interrupt()` and durable pause via a SQLite checkpointer so
a paused application survives a process restart.

## Acceptance criteria
- [ ] `src/graph/nodes/human_review.py` calls LangGraph `interrupt()` presenting
      the `FitAssessment` (verdict, gaps, red flags) and any clarifying questions
      (the `ask_user_input_v0` equivalent from the skill — max 3, only when they'd
      change the verdict/tailoring).
- [ ] Resume payload validates into `HumanDecision` (`decision`, `lead_angle`,
      `clarifications`) and is written to state.
- [ ] Graph compiled with a **SqliteSaver** checkpointer pointing at the existing
      SQLite DB file (or a dedicated `graph_checkpoints.db` — decide and document);
      no new external DB.
- [ ] `thread_id` = stable `f"{username}:{offer_id}"` so a re-invoked run resumes
      the same paused application rather than starting over.
- [ ] If the user override is `skip`, graph ends without drafting.
- [ ] Demonstrate resume: a test interrupts, drops the in-memory graph, rebuilds
      from the checkpointer, and resumes to completion.

## Files to create / modify
- `src/graph/nodes/human_review.py`
- `src/graph/build.py` (checkpointer wiring)
- `tests/integration/test_interrupt_resume.py`

## Dependencies
- Task 06.

## Estimated effort
**L**

## Testing notes
Integration test with a mocked LLM: run until interrupt, assert state persisted in
the checkpointer, rebuild graph, `Command(resume=HumanDecision(...))`, assert it
proceeds to the draft node.
