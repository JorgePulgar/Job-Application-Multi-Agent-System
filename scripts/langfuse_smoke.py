"""Manual Langfuse smoke test: one traced LLM call with a PII-bearing prompt.

Run from a network that can reach your Azure OpenAI endpoint:

    uv run python scripts/langfuse_smoke.py

Then open the printed trace URL and confirm:
  * one trace named ``livetest:1`` with a generation showing model/tokens/cost;
  * the email in the prompt is rendered as ``[EMAIL]`` (PII mask working).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the repo root importable when run as a file (``python scripts/...``).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langfuse import get_client  # noqa: E402  (must import after load_dotenv)

from src.graph import observability as o  # noqa: E402
from src.services.azure_openai import AzureOpenAIClient  # noqa: E402


async def main() -> None:
    o.init_langfuse()
    client = AzureOpenAIClient()
    async with o.trace_run("livetest:1", username="jorge", offer_id=1):
        result = await client.chat(
            deployment="mini",
            system="Responde en una sola palabra.",
            user="Mi email es test.user@example.com. Di hola.",
        )
        print("tokens:", result.usage.total_tokens, "model:", result.model)
        trace_id = get_client().get_current_trace_id()
    print("trace_id:", trace_id)
    if trace_id:
        print("url:", get_client().get_trace_url(trace_id=trace_id))


if __name__ == "__main__":
    asyncio.run(main())
