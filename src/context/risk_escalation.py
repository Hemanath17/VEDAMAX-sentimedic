"""Risk escalation detection for safety monitoring."""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from src.context.storage import get_storage_manager, SessionStateModel
from src.context.models import SessionState, RiskEscalationAlert
from src.config.settings import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class RiskEscalationDetector:
    """
    Detects escalating risk within a session for safety interventions.
    
    Personalization: Triggers safety protocols and adjusts response tone.
    """

    def __init__(self):
        """Initialize risk escalation detector."""
        self.storage = get_storage_manager()
        self.threshold = settings.RISK_ESCALATION_THRESHOLD  # 20% increase
        self.duration_minutes = settings.RISK_ESCALATION_DURATION  # 5 minutes
        logger.info(
            f"Initialized RiskEscalationDetector "
            f"(threshold={self.threshold}, duration={self.duration_minutes}m)"
        )

    def initialize_session(
        self,
        session_id: str,
        user_id: str,
        initial_risk: float = 0.0,
    ) -> SessionState:
        """
        Initialize session with baseline risk.

        Args:
            session_id: Session ID
            user_id: User ID
            initial_risk: Initial risk level

        Returns:
            SessionState object
        """
        with self.storage.get_session() as session:
            # Check if session exists
            session_model = session.query(SessionStateModel).filter(
                SessionStateModel.session_id == session_id
            ).first()

            if session_model:
                # Update existing session
                session_model.baseline_risk = initial_risk
                session_model.current_risk = initial_risk
                session_model.last_updated = datetime.now()
            else:
                # Create new session
                session_model = SessionStateModel(
                    session_id=session_id,
                    user_id=user_id,
                    started_at=datetime.now(),
                    baseline_risk=initial_risk,
                    current_risk=initial_risk,
                    message_count=0,
                    escalation_detected=False,
                    last_updated=datetime.now(),
                )
                session.add(session_model)

            session.flush()

            return SessionState(
                session_id=session_model.session_id,
                user_id=session_model.user_id,
                started_at=session_model.started_at,
                baseline_risk=session_model.baseline_risk,
                current_risk=session_model.current_risk,
                message_count=session_model.message_count,
                escalation_detected=session_model.escalation_detected,
                last_updated=session_model.last_updated,
            )

    def update_risk(
        self,
        session_id: str,
        current_risk: float,
        increment_message: bool = True,
    ) -> SessionState:
        """
        Update current risk level for session.

        Args:
            session_id: Session ID
            current_risk: Current risk level
            increment_message: Whether to increment message count

        Returns:
            Updated SessionState
        """
        with self.storage.get_session() as session:
            session_model = session.query(SessionStateModel).filter(
                SessionStateModel.session_id == session_id
            ).first()

            if not session_model:
                logger.warning(f"Session {session_id} not found, initializing")
                # Initialize with current risk as baseline
                return self.initialize_session(session_id, "", current_risk)

            session_model.current_risk = current_risk
            if increment_message:
                session_model.message_count += 1
            session_model.last_updated = datetime.now()

            session.flush()

            return SessionState(
                session_id=session_model.session_id,
                user_id=session_model.user_id,
                started_at=session_model.started_at,
                baseline_risk=session_model.baseline_risk,
                current_risk=session_model.current_risk,
                message_count=session_model.message_count,
                escalation_detected=session_model.escalation_detected,
                last_updated=session_model.last_updated,
            )

    def detect_escalation(
        self,
        session_id: str,
    ) -> Optional[RiskEscalationAlert]:
        """
        Detect risk escalation in session.

        Args:
            session_id: Session ID

        Returns:
            RiskEscalationAlert if escalation detected, None otherwise
        """
        with self.storage.get_session() as session:
            session_model = session.query(SessionStateModel).filter(
                SessionStateModel.session_id == session_id
            ).first()

            if not session_model:
                return None

            baseline = session_model.baseline_risk
            current = session_model.current_risk

            # Calculate increase percentage
            if baseline == 0:
                increase_percentage = 100.0 if current > 0 else 0.0
            else:
                increase_percentage = ((current - baseline) / baseline) * 100.0

            # Check for escalation
            escalation_detected = False
            escalation_type = None

            # Type 1: Threshold escalation (20% increase)
            if increase_percentage >= (self.threshold * 100):
                escalation_detected = True
                escalation_type = "threshold"

            # Type 2: Sustained high risk
            if current >= 0.8 and session_model.message_count >= 3:
                # Check if high risk sustained for duration
                time_since_start = datetime.now() - session_model.started_at
                if time_since_start >= timedelta(minutes=self.duration_minutes):
                    escalation_detected = True
                    escalation_type = "sustained"

            # Type 3: Sudden spike (risk doubled)
            if baseline > 0 and current >= (baseline * 2):
                escalation_detected = True
                escalation_type = "spike"

            if escalation_detected:
                # Update session state
                session_model.escalation_detected = True

                alert = RiskEscalationAlert(
                    alert_id=self.storage.generate_id(),
                    session_id=session_id,
                    user_id=session_model.user_id,
                    escalation_type=escalation_type,
                    baseline_risk=baseline,
                    current_risk=current,
                    increase_percentage=increase_percentage,
                    detected_at=datetime.now(),
                    triggered=False,
                )

                logger.warning(
                    f"Risk escalation detected in session {session_id}: "
                    f"{escalation_type}, {increase_percentage:.1f}% increase"
                )

                return alert

            return None

    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """
        Get current session state.

        Args:
            session_id: Session ID

        Returns:
            SessionState if found, None otherwise
        """
        with self.storage.get_session() as session:
            session_model = session.query(SessionStateModel).filter(
                SessionStateModel.session_id == session_id
            ).first()

            if not session_model:
                return None

            return SessionState(
                session_id=session_model.session_id,
                user_id=session_model.user_id,
                started_at=session_model.started_at,
                baseline_risk=session_model.baseline_risk,
                current_risk=session_model.current_risk,
                message_count=session_model.message_count,
                escalation_detected=session_model.escalation_detected,
                last_updated=session_model.last_updated,
            )

    def reset_session(self, session_id: str) -> bool:
        """
        Reset session state (for new conversation).

        Args:
            session_id: Session ID

        Returns:
            True if reset, False if not found
        """
        with self.storage.get_session() as session:
            session_model = session.query(SessionStateModel).filter(
                SessionStateModel.session_id == session_id
            ).first()

            if not session_model:
                return False

            # Reset to current risk as new baseline
            session_model.baseline_risk = session_model.current_risk
            session_model.escalation_detected = False
            session_model.message_count = 0
            session_model.last_updated = datetime.now()

            return True

