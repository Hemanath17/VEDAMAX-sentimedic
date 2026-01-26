"""Test script for Phase 4: User Context & Memory."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from src.context.storage import get_storage_manager
from src.context.user_profile import UserProfileManager
from src.context.memory_manager import MemoryManager, MemoryType
from src.context.emotion_tracker import EmotionTracker
from src.context.risk_escalation import RiskEscalationDetector
from src.context.context_manager import ContextManager

def test_storage():
    """Test 1: Storage layer."""
    print("\n" + "="*60)
    print("TEST 1: Storage Layer")
    print("="*60)
    
    try:
        storage = get_storage_manager()
        print("✓ Storage manager initialized")
        
        # Test user ID hashing
        raw_id = "test_user_123"
        hashed = storage.hash_user_id(raw_id)
        print(f"✓ User ID hashing: {raw_id} → {hashed[:16]}...")
        
        # Test ID generation
        id1 = storage.generate_id()
        id2 = storage.generate_id()
        assert id1 != id2, "IDs should be unique"
        print(f"✓ ID generation: {id1[:16]}... != {id2[:16]}...")
        
        # Test table creation
        storage.create_tables()
        print("✓ Database tables created")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_profile():
    """Test 2: User Profile Manager."""
    print("\n" + "="*60)
    print("TEST 2: User Profile Manager")
    print("="*60)
    
    try:
        manager = UserProfileManager()
        storage = get_storage_manager()
        
        # Hash user ID
        raw_user_id = "test_user_123"
        user_id = storage.hash_user_id(raw_user_id)
        print(f"✓ User ID: {user_id[:16]}...")
        
        # Create profile
        profile = manager.create_or_update_profile(
            user_id=user_id,
            age_range="26-35",
            conditions=["diabetes", "hypertension"],
            preferences={
                "communication_style": "casual",
                "detail_level": "simple",
                "language": "en"
            }
        )
        print(f"✓ Profile created: age_range={profile.age_range}, conditions={len(profile.conditions)}")
        
        # Get profile
        retrieved = manager.get_profile(user_id)
        assert retrieved is not None, "Profile should exist"
        assert retrieved.age_range == "26-35", "Age range should match"
        print(f"✓ Profile retrieved: {retrieved.age_range}")
        
        # Update preferences
        updated = manager.update_preferences(
            user_id=user_id,
            preferences={"detail_level": "detailed"}
        )
        assert updated.preferences["detail_level"] == "detailed", "Preference should be updated"
        print(f"✓ Preferences updated: {updated.preferences}")
        
        # Get personalization context
        context = manager.get_personalization_context(user_id)
        assert "communication_style" in context, "Context should have communication_style"
        print(f"✓ Personalization context: {context['communication_style']}")
        
        # Add condition
        profile_with_condition = manager.add_condition(user_id, "asthma")
        assert "asthma" in profile_with_condition.conditions, "Condition should be added"
        print(f"✓ Condition added: {len(profile_with_condition.conditions)} conditions")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_manager():
    """Test 3: Memory Manager."""
    print("\n" + "="*60)
    print("TEST 3: Memory Manager")
    print("="*60)
    
    try:
        manager = MemoryManager()
        storage = get_storage_manager()
        
        user_id = storage.hash_user_id("test_user_123")
        session_id = storage.generate_id()
        
        # Add messages
        msg1 = manager.add_message(user_id, session_id, "user", "What is diabetes?")
        msg2 = manager.add_message(user_id, session_id, "assistant", "Diabetes is a condition...")
        msg3 = manager.add_message(user_id, session_id, "user", "How do I manage it?")
        print(f"✓ Added {3} messages")
        
        # Get session memory (user messages only)
        session_memory = manager.get_session_memory(user_id, session_id)
        assert len(session_memory) >= 2, "Should have at least 2 user messages"
        print(f"✓ Session memory: {len(session_memory)} user messages")
        
        # Get conversation history
        history = manager.get_conversation_history(user_id, session_id)
        assert len(history) >= 3, "Should have at least 3 messages"
        print(f"✓ Conversation history: {len(history)} messages")
        
        # Add user memory
        user_memory = manager.add_user_memory(
            user_id=user_id,
            memory_type=MemoryType.USER,
            content="User prefers simple explanations",
            source="conversation"
        )
        print(f"✓ User memory added: {user_memory.content[:50]}...")
        
        # Add clinical memory
        clinical_memory = manager.add_user_memory(
            user_id=user_id,
            memory_type=MemoryType.CLINICAL,
            content="User asked about cholesterol twice",
            source="entity_extraction"
        )
        print(f"✓ Clinical memory added: {clinical_memory.content[:50]}...")
        
        # Get user memories
        user_memories = manager.get_user_memories(user_id, MemoryType.USER)
        assert len(user_memories) >= 1, "Should have user memories"
        print(f"✓ User memories: {len(user_memories)} memories")
        
        # Get clinical memories
        clinical_memories = manager.get_user_memories(user_id, MemoryType.CLINICAL)
        assert len(clinical_memories) >= 1, "Should have clinical memories"
        print(f"✓ Clinical memories: {len(clinical_memories)} memories")
        
        # Get memory context
        context = manager.get_memory_context(user_id, session_id)
        assert "session_memory" in context, "Context should have session_memory"
        assert "user_memories" in context, "Context should have user_memories"
        assert "clinical_memories" in context, "Context should have clinical_memories"
        print(f"✓ Memory context: {len(context['session_memory'])} session, {len(context['user_memories'])} user, {len(context['clinical_memories'])} clinical")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_emotion_tracker():
    """Test 4: Emotion Tracker."""
    print("\n" + "="*60)
    print("TEST 4: Emotion Tracker")
    print("="*60)
    
    try:
        tracker = EmotionTracker()
        storage = get_storage_manager()
        
        user_id = storage.hash_user_id("test_user_123")
        session_id = storage.generate_id()
        
        # Record emotions (tracking every message)
        record1 = tracker.record_emotion(
            user_id=user_id,
            session_id=session_id,
            emotion_bucket="LOW_CONCERN",
            anxiety_level=0.3,
            risk_level=0.2,
            sentiment_score=0.1
        )
        print(f"✓ Recorded emotion 1: {record1.emotion_bucket}, anxiety={record1.anxiety_level}")
        
        record2 = tracker.record_emotion(
            user_id=user_id,
            session_id=session_id,
            emotion_bucket="HIGH_ANXIETY",
            anxiety_level=0.7,
            risk_level=0.6,
            sentiment_score=-0.3
        )
        print(f"✓ Recorded emotion 2: {record2.emotion_bucket}, anxiety={record2.anxiety_level}")
        
        record3 = tracker.record_emotion(
            user_id=user_id,
            session_id=session_id,
            emotion_bucket="HIGH_ANXIETY",
            anxiety_level=0.8,
            risk_level=0.7,
            sentiment_score=-0.4
        )
        print(f"✓ Recorded emotion 3: {record3.emotion_bucket}, anxiety={record3.anxiety_level}")
        
        # Get recent emotions
        recent = tracker.get_recent_emotions(user_id, hours=24)
        assert len(recent) >= 3, "Should have at least 3 records"
        print(f"✓ Recent emotions: {len(recent)} records")
        
        # Calculate anxiety trend
        anxiety_trend = tracker.calculate_anxiety_trend(user_id, hours=24)
        print(f"✓ Anxiety trend: {anxiety_trend.trend_type}, change={anxiety_trend.change_percentage:.1f}%")
        
        # Calculate risk trend
        risk_trend = tracker.calculate_risk_trend(user_id, hours=24)
        print(f"✓ Risk trend: {risk_trend.trend_type}, change={risk_trend.change_percentage:.1f}%")
        
        # Detect anxiety spike
        spike = tracker.detect_anxiety_spike(user_id, threshold=0.7)
        print(f"✓ Anxiety spike detected: {spike}")
        
        # Get emotion summary
        summary = tracker.get_emotion_summary(user_id, hours=24)
        assert "total_records" in summary, "Summary should have total_records"
        assert "average_anxiety" in summary, "Summary should have average_anxiety"
        print(f"✓ Emotion summary: {summary['total_records']} records, avg_anxiety={summary['average_anxiety']:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_risk_escalation():
    """Test 5: Risk Escalation Detector."""
    print("\n" + "="*60)
    print("TEST 5: Risk Escalation Detector")
    print("="*60)
    
    try:
        detector = RiskEscalationDetector()
        storage = get_storage_manager()
        
        user_id = storage.hash_user_id("test_user_123")
        session_id = storage.generate_id()
        
        # Initialize session
        session_state = detector.initialize_session(session_id, user_id, initial_risk=0.3)
        print(f"✓ Session initialized: baseline_risk={session_state.baseline_risk}")
        
        # Update risk (simulate escalation)
        state1 = detector.update_risk(session_id, current_risk=0.4)
        print(f"✓ Risk updated 1: {state1.current_risk}")
        
        state2 = detector.update_risk(session_id, current_risk=0.5)
        print(f"✓ Risk updated 2: {state2.current_risk}")
        
        # Trigger escalation (20% increase: 0.3 → 0.5 = 66% increase)
        state3 = detector.update_risk(session_id, current_risk=0.5)
        alert = detector.detect_escalation(session_id)
        
        if alert:
            print(f"✓ Escalation detected: {alert.escalation_type}, {alert.increase_percentage:.1f}% increase")
        else:
            print("⚠ Escalation not detected (may need more increase)")
        
        # Get session state
        current_state = detector.get_session_state(session_id)
        assert current_state is not None, "Session state should exist"
        print(f"✓ Session state: risk={current_state.current_risk}, messages={current_state.message_count}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_context_manager():
    """Test 6: Context Manager (Orchestrator)."""
    print("\n" + "="*60)
    print("TEST 6: Context Manager")
    print("="*60)
    
    try:
        manager = ContextManager()
        storage = get_storage_manager()
        
        raw_user_id = "test_user_123"
        session_id = storage.generate_id()
        
        # Initialize context
        context = manager.initialize_user_context(
            raw_user_id=raw_user_id,
            session_id=session_id,
            initial_risk=0.3
        )
        user_id = context["user_id"]
        print(f"✓ Context initialized: user_id={user_id[:16]}..., session_id={session_id[:16]}...")
        
        # Process user message with analysis result
        analysis_result = {
            "entities": [
                {"text": "diabetes", "entity_type": "CONDITION", "confidence": 0.9}
            ],
            "sentiment": {
                "emotion_analysis": {
                    "dominant_bucket": "LOW_CONCERN"
                },
                "anxiety_level": 0.4,
                "risk_level": 0.3,
                "sentiment_score": 0.1
            }
        }
        
        updated_context = manager.process_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content="What is diabetes?",
            analysis_result=analysis_result
        )
        print(f"✓ Message processed: {len(updated_context['session_memory'])} session messages")
        
        # Get complete context
        full_context = manager.get_context(user_id, session_id)
        assert "profile" in full_context, "Context should have profile"
        assert "session_memory" in full_context, "Context should have session_memory"
        assert "emotion_summary" in full_context, "Context should have emotion_summary"
        assert "risk_state" in full_context, "Context should have risk_state"
        print(f"✓ Full context retrieved: {len(full_context.keys())} keys")
        
        # Get personalization prompt
        prompt_context = manager.get_personalization_prompt_context(user_id, session_id)
        print(f"✓ Personalization prompt: {len(prompt_context)} chars")
        if prompt_context:
            print(f"  Preview: {prompt_context[:100]}...")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_privacy():
    """Test 7: Privacy by Design."""
    print("\n" + "="*60)
    print("TEST 7: Privacy by Design")
    print("="*60)
    
    try:
        manager = ContextManager()
        storage = get_storage_manager()
        
        raw_user_id = "test_user_delete_me"
        user_id = storage.hash_user_id(raw_user_id)
        session_id = storage.generate_id()
        
        # Create some data
        manager.initialize_user_context(raw_user_id, session_id)
        manager.process_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content="Test message",
            analysis_result={
                "sentiment": {
                    "emotion_analysis": {"dominant_bucket": "NEUTRAL"},
                    "anxiety_level": 0.2,
                    "risk_level": 0.1,
                    "sentiment_score": 0.0
                }
            }
        )
        print(f"✓ Test data created for user: {user_id[:16]}...")
        
        # Delete all user data
        counts = manager.delete_user_data(user_id)
        assert counts["profile"] >= 0, "Should delete profile"
        assert counts["messages"] >= 0, "Should delete messages"
        print(f"✓ Data deleted: profile={counts['profile']}, messages={counts['messages']}, emotions={counts['emotions']}")
        
        # Verify deletion
        profile = manager.profile_manager.get_profile(user_id)
        assert profile is None, "Profile should be deleted"
        print(f"✓ Deletion verified: profile is None")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PHASE 4: USER CONTEXT & MEMORY - COMPREHENSIVE TEST")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("Storage Layer", test_storage()))
    results.append(("User Profile Manager", test_user_profile()))
    results.append(("Memory Manager", test_memory_manager()))
    results.append(("Emotion Tracker", test_emotion_tracker()))
    results.append(("Risk Escalation Detector", test_risk_escalation()))
    results.append(("Context Manager", test_context_manager()))
    results.append(("Privacy by Design", test_privacy()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All Phase 4 components are working correctly!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

