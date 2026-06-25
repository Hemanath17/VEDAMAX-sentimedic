"""Prompt templates for grounded medical answer generation."""

from src.generation.prompt_templates.system_prompts import build_system_prompt
from src.generation.prompt_templates.user_prompts import build_user_prompt

__all__ = ["build_system_prompt", "build_user_prompt"]
