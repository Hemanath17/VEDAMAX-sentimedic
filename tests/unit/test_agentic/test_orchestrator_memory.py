# tests/unit/test_agentic/test_orchestrator_memory.py
from unittest.mock import MagicMock, patch

from src.agentic.router.orchestrator import TriageOrchestrator, _EMERGENCY_MESSAGE
from src.agentic.router.triage_agent import TriageLevel
from src.generation.response_generator import GeneratedAnswer
from src.retrieval.pipeline import RetrievalResult, RetrievalStatus


def _routine_triage():
    return type("T", (), {"level": TriageLevel.ROUTINE, "reason": "test"})()


def _emergency_triage():
    return type("T", (), {"level": TriageLevel.EMERGENCY, "reason": "test"})()


def _mock_generated_answer(text: str = "Grounded answer.") -> GeneratedAnswer:
    return GeneratedAnswer(
        answer=text,
        citations=[],
        disclaimer="Educational only.",
        status=RetrievalStatus.OK,
        used_patient_data=False,
        flagged_numbers=[],
    )


def _build_orchestrator(mock_context, mock_retrieval, mock_generator):
    return TriageOrchestrator(
        retrieval_pipeline=mock_retrieval,
        response_generator=mock_generator,
        context_manager=mock_context,
    )


@patch("src.agentic.router.orchestrator.run_triage", return_value=_routine_triage())
def test_process_message_called_for_user_and_assistant_on_normal_turn(mock_triage):
    mock_context = MagicMock()
    mock_context.get_personalization_prompt_context.return_value = "User prefers simple language."
    mock_context.get_context.return_value = {"escalation_alert": None}

    mock_retrieval = MagicMock()
    mock_retrieval.retrieve.return_value = RetrievalResult(
        status=RetrievalStatus.OK,
        chunks=[],
        message=None,
    )

    mock_generator = MagicMock()
    mock_generator.generate.return_value = _mock_generated_answer("Here is your answer.")

    orchestrator = _build_orchestrator(mock_context, mock_retrieval, mock_generator)

    result = orchestrator.handle(
        question="What is a normal glucose level?",
        session_id="session-abc",
        user_id="user-1",
    )

    assert result.triage_level == TriageLevel.ROUTINE
    assert mock_context.process_message.call_count == 2

    user_call = mock_context.process_message.call_args_list[0]
    assistant_call = mock_context.process_message.call_args_list[1]

    assert user_call.kwargs["role"] == "user"
    assert user_call.kwargs["content"] == "What is a normal glucose level?"
    assert user_call.kwargs["session_id"] == "session-abc"
    assert user_call.kwargs["user_id"] == "user-1"

    assert assistant_call.kwargs["role"] == "assistant"
    assert assistant_call.kwargs["content"] == "Here is your answer."


@patch("src.agentic.router.orchestrator.run_triage", return_value=_routine_triage())
def test_context_failure_does_not_block_retrieval_or_generation(mock_triage):
    mock_context = MagicMock()
    mock_context.process_message.side_effect = RuntimeError("postgres down")

    mock_retrieval = MagicMock()
    mock_retrieval.retrieve.return_value = RetrievalResult(
        status=RetrievalStatus.OK,
        chunks=[],
        message=None,
    )

    mock_generator = MagicMock()
    mock_generator.generate.return_value = _mock_generated_answer("Still works.")

    orchestrator = _build_orchestrator(mock_context, mock_retrieval, mock_generator)

    result = orchestrator.handle(
        question="What is HbA1c?",
        session_id="session-fail",
        user_id="user-1",
    )

    assert result.answer_text == "Still works."
    assert result.triage_level == TriageLevel.ROUTINE
    mock_retrieval.retrieve.assert_called_once()
    mock_generator.generate.assert_called_once()


@patch("src.agentic.router.orchestrator.run_triage", return_value=_emergency_triage())
def test_emergency_triage_wins_even_when_context_reports_no_escalation(mock_triage):
    mock_context = MagicMock()
    mock_context.get_context.return_value = {"escalation_alert": None}

    mock_retrieval = MagicMock()
    mock_generator = MagicMock()

    orchestrator = _build_orchestrator(mock_context, mock_retrieval, mock_generator)

    result = orchestrator.handle(
        question="I have crushing chest pain right now",
        session_id="session-emergency",
        user_id="user-1",
    )

    mock_retrieval.retrieve.assert_not_called()
    mock_generator.generate.assert_not_called()
    assert result.triage_level == TriageLevel.EMERGENCY
    assert result.answer_text == _EMERGENCY_MESSAGE

    assistant_call = mock_context.process_message.call_args_list[-1]
    assert assistant_call.kwargs["role"] == "assistant"
    assert assistant_call.kwargs["content"] == _EMERGENCY_MESSAGE


@patch("src.agentic.router.orchestrator.run_triage", return_value=_routine_triage())
def test_escalation_alert_forces_gentle_persona_without_bypassing_generation(mock_triage):
    mock_context = MagicMock()
    mock_context.get_personalization_prompt_context.return_value = ""
    mock_context.get_context.return_value = {
        "escalation_alert": {"severity": "high", "reason": "rising anxiety"},
    }

    mock_retrieval = MagicMock()
    mock_retrieval.retrieve.return_value = RetrievalResult(
        status=RetrievalStatus.OK,
        chunks=[],
        message=None,
    )

    mock_generator = MagicMock()
    mock_generator.generate.return_value = _mock_generated_answer("Gentle answer.")

    orchestrator = _build_orchestrator(mock_context, mock_retrieval, mock_generator)

    result = orchestrator.handle(
        question="Is my cholesterol okay?",
        session_id="session-escalation",
        user_id="user-1",
    )

    assert result.triage_level == TriageLevel.ROUTINE
    mock_retrieval.retrieve.assert_called_once()
    mock_generator.generate.assert_called_once_with(
        question="Is my cholesterol okay?",
        retrieval_result=mock_retrieval.retrieve.return_value,
        persona="gentle_and_reassuring",
        session_summary=None,
    )
