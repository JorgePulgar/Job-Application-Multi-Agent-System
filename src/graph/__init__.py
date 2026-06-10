"""LangGraph `evaluate_and_draft` subgraph (Phase 10.5).

Orchestrates the per-offer ``research -> eval -> draft`` slice as a LangGraph
subgraph: parallel research fan-out, a confidence loop, an ``interrupt()``
human-in-the-loop step, and a SQLite checkpointer for crash-resumable daily runs.

LangGraph is used standalone for orchestration only -- nodes call the existing
``AzureOpenAIClient`` + ``prompt_loader`` directly (no LangChain-classic
wrappers/chains/parsers), preserving prompt caching and structured outputs.
"""
