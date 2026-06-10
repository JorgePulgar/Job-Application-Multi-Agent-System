"""Node implementations for the ``evaluate_and_draft`` subgraph (Phase 10.5).

Each node is built by a ``make_*`` factory that captures its dependencies
(``AzureOpenAIClient`` + a session factory) and returns the actual
``(state) -> dict`` coroutine LangGraph calls. Dependencies are injected this way
(rather than via the node signature) so nodes stay pure ``(state)`` callables and
unit tests can pass mocks straight to the factory. ``build_graph`` wires the
returned closures in Tasks 06-07.
"""
