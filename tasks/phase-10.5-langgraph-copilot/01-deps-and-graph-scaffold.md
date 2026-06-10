# Phase 10.5 · Task 01 — Deps + graph package scaffold + state

## Objective
Add LangGraph/Langfuse, verify Python compatibility, and create the empty graph
package with the typed state object and a compile-only graph stub.

## Acceptance criteria
- [x] **Compatibility check first:** confirm `langgraph` + `langfuse` support the
      interpreter in use (venv is Python 3.14 — see README §8). If unsupported, stop
      and report; pin a working version or interpreter before adding deps.
      _Resolved clean on Python 3.14.3: langgraph 1.2.4, langfuse 4.7.1,
      langgraph-checkpoint-sqlite 3.1.0._
- [x] `uv add langgraph langfuse` (and `langgraph-checkpoint-sqlite` if the SQLite
      saver is a separate package for the resolved version). Lockfile committed.
- [x] `src/graph/__init__.py`, `src/graph/state.py`, `src/graph/build.py` created.
- [x] `src/graph/state.py` defines `EvaluateDraftState` (TypedDict, `total=False`)
      exactly per README §4. _The six Task-02 fit schemas are aliased to `Any`
      pending `src/models/fit.py`; keys/structure exact._
- [x] `src/graph/build.py` exposes `build_graph(checkpointer) -> Compiledgraph`
      that wires node stubs (each node a `pass`/placeholder returning `{}`) so the
      graph **compiles** and a smoke test can `.get_graph()`/draw it.
- [x] `mypy --strict src/graph/` passes (add `langgraph`/`langfuse` to mypy
      overrides if they ship no stubs).

## Files to create / modify
- `pyproject.toml`, `uv.lock`
- `src/graph/__init__.py`
- `src/graph/state.py`
- `src/graph/build.py`
- `tests/unit/test_graph_compiles.py`

## Dependencies
- Task 00 (approved).

## Estimated effort
**M**

## Testing notes
Smoke test: `build_graph(MemorySaver()).get_graph()` returns nodes/edges without
raising. No LLM calls yet.
