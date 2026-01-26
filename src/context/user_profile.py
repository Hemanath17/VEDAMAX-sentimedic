"""User profile management with anonymization."""

from typing import Optional, Dict, Any, List
from datetime import datetime

from src.context.storage import get_storage_manager, UserProfileModel
from src.context.models import UserProfile
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class UserProfileManager:
    """
    Manages user profiles with anonymization.
    
    Personalization: Remembers user traits (age, conditions, preferences)
    to tailor responses (e.g., "prefers simple explanations").
    """

    def __init__(self):
        """Initialize user profile manager."""
        self.storage = get_storage_manager()
        logger.info("Initialized UserProfileManager")

    def create_or_update_profile(
        self,
        user_id: str,
        age_range: Optional[str] = None,
        conditions: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> UserProfile:
        """
        Create or update user profile.

        Args:
            user_id: Hashed user ID
            age_range: Age range (18-25, 26-35, 36-50, 51-65, 65+)
            conditions: List of medical conditions (anonymized)
            preferences: User preferences dict

        Returns:
            UserProfile object
        """
        with self.storage.get_session() as session:
            # Check if profile exists
            profile_model = session.query(UserProfileModel).filter(
                UserProfileModel.user_id == user_id
            ).first()

            if profile_model:
                # Update existing profile
                if age_range is not None:
                    profile_model.age_range = age_range
                if conditions is not None:
                    profile_model.conditions = conditions
                if preferences is not None:
                    # Merge preferences
                    current_prefs = profile_model.preferences or {}
                    current_prefs.update(preferences)
                    profile_model.preferences = current_prefs
                profile_model.updated_at = datetime.now()
                logger.info(f"Updated profile for user: {user_id}")
            else:
                # Create new profile
                profile_model = UserProfileModel(
                    user_id=user_id,
                    age_range=age_range,
                    conditions=conditions or [],
                    preferences=preferences or {},
                )
                session.add(profile_model)
                logger.info(f"Created profile for user: {user_id}")

            session.flush()

            # Convert to Pydantic model
            return UserProfile(
                user_id=profile_model.user_id,
                age_range=profile_model.age_range,
                conditions=profile_model.conditions or [],
                preferences=profile_model.preferences or {},
                created_at=profile_model.created_at,
                updated_at=profile_model.updated_at,
            )

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user profile.

        Args:
            user_id: Hashed user ID

        Returns:
            UserProfile if found, None otherwise
        """
        with self.storage.get_session() as session:
            profile_model = session.query(UserProfileModel).filter(
                UserProfileModel.user_id == user_id
            ).first()

            if not profile_model:
                return None

            return UserProfile(
                user_id=profile_model.user_id,
                age_range=profile_model.age_range,
                conditions=profile_model.conditions or [],
                preferences=profile_model.preferences or {},
                created_at=profile_model.created_at,
                updated_at=profile_model.updated_at,
            )

    def update_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
    ) -> Optional[UserProfile]:
        """
        Update user preferences.

        Args:
            user_id: Hashed user ID
            preferences: Preferences to update

        Returns:
            Updated UserProfile
        """
        return self.create_or_update_profile(
            user_id=user_id,
            preferences=preferences,
        )

    def add_condition(self, user_id: str, condition: str) -> Optional[UserProfile]:
        """
        Add a medical condition to user profile.

        Args:
            user_id: Hashed user ID
            condition: Medical condition (anonymized)

        Returns:
            Updated UserProfile
        """
        profile = self.get_profile(user_id)
        if not profile:
            # Create profile if doesn't exist
            profile = self.create_or_update_profile(user_id=user_id)

        conditions = profile.conditions.copy()
        if condition not in conditions:
            conditions.append(condition)

        return self.create_or_update_profile(
            user_id=user_id,
            conditions=conditions,
        )

    def delete_profile(self, user_id: str) -> bool:
        """
        Delete user profile (Privacy by Design - Right to Deletion).

        Args:
            user_id: Hashed user ID

        Returns:
            True if deleted, False if not found
        """
        with self.storage.get_session() as session:
            profile_model = session.query(UserProfileModel).filter(
                UserProfileModel.user_id == user_id
            ).first()

            if not profile_model:
                return False

            session.delete(profile_model)
            logger.info(f"Deleted profile for user: {user_id}")
            return True

    def get_personalization_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get personalization context from user profile.

        Args:
            user_id: Hashed user ID

        Returns:
            Personalization context dict
        """
        profile = self.get_profile(user_id)
        if not profile:
            return {}

        context = {
            "age_range": profile.age_range,
            "conditions": profile.conditions,
            "preferences": profile.preferences,
        }

        # Extract key preferences for easy access
        if profile.preferences:
            context["communication_style"] = profile.preferences.get("communication_style", "neutral")
            context["detail_level"] = profile.preferences.get("detail_level", "medium")
            context["language"] = profile.preferences.get("language", "en")

        return context

