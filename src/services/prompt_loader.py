"""Load and interpolate prompt templates from src/prompts/*.md."""

from __future__ import annotations

import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def load(name: str, **variables: str) -> tuple[str, str]:
    """Load and interpolate both system and user prompt templates for *name*.

    Args:
        name: Prompt base name, e.g. ``"offer_filter"`` loads
              ``offer_filter.system.md`` and ``offer_filter.user.md``.
        **variables: Values to substitute for ``{{key}}`` placeholders.

    Returns:
        ``(system_prompt, user_prompt)`` with all placeholders resolved.

    Raises:
        FileNotFoundError: If either prompt file is missing.
        ValueError: If a ``{{placeholder}}`` in the template has no matching variable.
    """
    system = _load_file(f"{name}.system.md", **variables)
    user = _load_file(f"{name}.user.md", **variables)
    return system, user


def load_system(name: str, **variables: str) -> str:
    """Load and interpolate only the system prompt template for *name*.

    Args:
        name: Prompt base name.
        **variables: Placeholder substitutions.

    Returns:
        Interpolated system prompt string.
    """
    return _load_file(f"{name}.system.md", **variables)


def load_user(name: str, **variables: str) -> str:
    """Load and interpolate only the user prompt template for *name*.

    Args:
        name: Prompt base name.
        **variables: Placeholder substitutions.

    Returns:
        Interpolated user prompt string.
    """
    return _load_file(f"{name}.user.md", **variables)


def _load_file(filename: str, **variables: str) -> str:
    """Read a prompt file from the prompts directory and resolve ``{{var}}`` placeholders.

    Args:
        filename: File name relative to the prompts directory.
        **variables: Placeholder substitutions.

    Returns:
        Resolved prompt string.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If any placeholder is not covered by *variables*.
    """
    path = _PROMPTS_DIR / filename
    text = path.read_text(encoding="utf-8")

    placeholders = set(_VAR_RE.findall(text))
    missing = placeholders - set(variables)
    if missing:
        raise ValueError(
            f"Prompt template '{filename}' has unresolved placeholders: "
            f"{sorted(missing)}. Pass them as keyword arguments to load()."
        )

    return _VAR_RE.sub(lambda m: variables[m.group(1)], text)
