# tests/unit/test_agentic/test_orchestrator.py
from unittest.mock import MagicMock
from src.agentic.router.orchestrator import TriageOrchestrator
from src.agentic.router.triage_agent import TriageLevel

def test_emergency_bypasses_retrieval_and_generation():
    mock_retrieval = MagicMock()
    mock_generator = MagicMock()
    orchestrator = TriageOrchestrator(
        retrieval_pipeline=mock_retrieval,
        response_generator=mock_generator,
    )
    # Force the triage path without calling the real LLM
    import src.agentic.router.orchestrator as orch_module
    orch_module.run_triage = lambda *a, **kw: type(
        "T", (), {"level": TriageLevel.EMERGENCY, "reason": "test"}
    )()

    result = orchestrator.handle("I have crushing chest pain right now")

    mock_retrieval.retrieve.assert_not_called()
    mock_generator.generate.assert_not_called()
    assert result.triage_level == TriageLevel.EMERGENCY
    assert "911" in result.answer_text or "988" in result.answer_text