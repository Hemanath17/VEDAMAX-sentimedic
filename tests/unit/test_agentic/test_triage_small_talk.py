# tests/unit/test_agentic/test_triage_small_talk.py
from unittest.mock import MagicMock, patch

from src.agentic.router.orchestrator import (
    TriageOrchestrator,
    _SMALL_TALK_FALLBACK,
)
from src.agentic.router.triage_agent import (
    TriageLevel,
    TriageResult,
    _TRIAGE_SYSTEM_PROMPT,
    run_triage,
)
from src.generation.llm_client import LLMError


def _small_talk_triage():
    return TriageResult(level=TriageLevel.SMALL_TALK, reason="small_talk_detected")


class TestRunTriageSmallTalk:

    def test_llm_returns_small_talk_label(self):
        mock_client = MagicMock()
        mock_client.generate.return_value = "SMALL_TALK"
        result = run_triage("hello there", llm_client=mock_client)
        assert result.level == TriageLevel.SMALL_TALK

    def test_high_risk_level_does_not_override_small_talk(self):
        mock_client = MagicMock()
        mock_client.generate.return_value = "SMALL_TALK"
        result = run_triage("thanks!", risk_level=0.95, llm_client=mock_client)
        assert result.level == TriageLevel.SMALL_TALK

    def test_system_prompt_requires_health_questions_not_be_small_talk(self):
        assert "hi, is my glucose high?" in _TRIAGE_SYSTEM_PROMPT
        assert "ROUTINE, not SMALL_TALK" in _TRIAGE_SYSTEM_PROMPT
        assert "SMALL_TALK must never capture messages" in _TRIAGE_SYSTEM_PROMPT


class TestOrchestratorSmallTalk:

    @patch("src.agentic.router.orchestrator.run_triage", return_value=_small_talk_triage())
    def test_small_talk_skips_retrieval(self, _mock_triage):
        mock_retrieval = MagicMock()
        mock_generator = MagicMock()
        mock_context = MagicMock()
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "Hello! Good to see you."
        mock_generator.llm_client = mock_llm

        orchestrator = TriageOrchestrator(
            retrieval_pipeline=mock_retrieval,
            response_generator=mock_generator,
            context_manager=mock_context,
        )

        result = orchestrator.handle("hi", session_id="session-small-talk", user_id="user-1")

        mock_retrieval.retrieve.assert_not_called()
        assert result.triage_level == TriageLevel.SMALL_TALK

    @patch("src.agentic.router.orchestrator.run_triage", return_value=_small_talk_triage())
    def test_small_talk_skips_response_generator(self, _mock_triage):
        mock_retrieval = MagicMock()
        mock_generator = MagicMock()
        mock_context = MagicMock()
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "Hey there!"
        mock_generator.llm_client = mock_llm

        orchestrator = TriageOrchestrator(
            retrieval_pipeline=mock_retrieval,
            response_generator=mock_generator,
            context_manager=mock_context,
        )

        orchestrator.handle("hello", session_id="session-small-talk")

        mock_generator.generate.assert_not_called()

    @patch("src.agentic.router.orchestrator.run_triage", return_value=_small_talk_triage())
    def test_small_talk_llm_failure_uses_fallback(self, _mock_triage):
        mock_retrieval = MagicMock()
        mock_generator = MagicMock()
        mock_context = MagicMock()
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = LLMError("provider down")
        mock_generator.llm_client = mock_llm

        orchestrator = TriageOrchestrator(
            retrieval_pipeline=mock_retrieval,
            response_generator=mock_generator,
            context_manager=mock_context,
        )

        result = orchestrator.handle("good morning", session_id="session-fallback")

        assert result.answer_text == _SMALL_TALK_FALLBACK
        assert result.triage_level == TriageLevel.SMALL_TALK
