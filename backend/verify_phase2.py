#!/usr/bin/env python3
"""
Verification script for Phase 2 Multi-LLM Debate Engine
Tests all imports and basic functionality
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

def test_imports():
    """Test all Phase 2 imports"""
    print("🧪 Testing Phase 2 imports...\n")

    tests = []

    # Test models
    try:
        from app.models.debate import (
            Debate, DebateConfig, DebateRound, DebaterResponse,
            DebateStatus, DebateStreamEvent, ParticipantConfig,
            PersonaConfig, JudgeAssessment, DebateFormat
        )
        tests.append(("✅", "Debate models"))
    except Exception as e:
        tests.append(("❌", f"Debate models: {e}"))

    # Test token counter
    try:
        from app.utils.token_counter import token_counter
        tests.append(("✅", "Token counter"))
    except Exception as e:
        tests.append(("❌", f"Token counter: {e}"))

    # Test context manager
    try:
        from app.services.context_manager import context_manager
        tests.append(("✅", "Context manager"))
    except Exception as e:
        tests.append(("❌", f"Context manager: {e}"))

    # Test judge service
    try:
        from app.services.judge_service import judge_service
        tests.append(("✅", "Judge service"))
    except Exception as e:
        tests.append(("❌", f"Judge service: {e}"))

    # Test debate service
    try:
        from app.services.debate_service import debate_service
        tests.append(("✅", "Debate service"))
    except Exception as e:
        tests.append(("❌", f"Debate service: {e}"))

    # Test API routes
    try:
        from app.api.routes.debate import router
        tests.append(("✅", "Debate API routes"))
    except Exception as e:
        tests.append(("❌", f"Debate API routes: {e}"))

    # Print results
    for status, message in tests:
        print(f"{status} {message}")

    # Count successes
    success_count = sum(1 for status, _ in tests if status == "✅")
    total_count = len(tests)

    print(f"\n📊 Results: {success_count}/{total_count} tests passed")

    return success_count == total_count


def test_token_counter():
    """Test token counter functionality"""
    print("\n🧪 Testing token counter...\n")

    try:
        from app.utils.token_counter import token_counter

        # Test token counting
        text = "Hello, world! This is a test."
        tokens = token_counter.count_tokens(text, "gpt-4o")
        print(f"✅ Token counting: '{text}' = {tokens} tokens")

        # Test cost estimation
        cost = token_counter.estimate_cost(1000, 500, "gpt-4o")
        print(f"✅ Cost estimation: 1000 in + 500 out = ${cost:.4f}")

        # Test warning levels
        level = token_counter.get_cost_warning_level(0.75, 1.0)
        print(f"✅ Warning level: $0.75/$1.00 = {level}")

        return True
    except Exception as e:
        print(f"❌ Token counter test failed: {e}")
        return False


def test_debate_models():
    """Test debate model creation"""
    print("\n🧪 Testing debate models...\n")

    try:
        from app.models.debate import DebateConfig, ParticipantConfig, PersonaConfig

        # Create valid config
        config = DebateConfig(
            topic="Should AI development be open source?",
            participants=[
                ParticipantConfig(
                    model="gpt-4o",
                    persona=PersonaConfig(
                        name="Optimist",
                        role="Argue for open source"
                    )
                ),
                ParticipantConfig(
                    model="claude-3-5-sonnet-20241022",
                    persona=PersonaConfig(
                        name="Skeptic",
                        role="Argue for controlled development"
                    )
                )
            ]
        )

        print(f"✅ DebateConfig created: {config.topic}")
        print(f"✅ Participants: {len(config.participants)}")
        print(f"✅ Format: {config.format.value}")

        return True
    except Exception as e:
        print(f"❌ Debate model test failed: {e}")
        return False


def main():
    """Run all verification tests"""
    print("=" * 60)
    print("Phase 2: Multi-LLM Debate Engine - Verification")
    print("=" * 60)

    results = []

    # Test imports
    results.append(("Imports", test_imports()))

    # Test token counter
    results.append(("Token Counter", test_token_counter()))

    # Test models
    results.append(("Debate Models", test_debate_models()))

    # Print summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    # Overall result
    all_passed = all(passed for _, passed in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All verification tests PASSED!")
        print("✅ Phase 2 implementation is ready")
    else:
        print("⚠️  Some verification tests FAILED")
        print("❌ Please review errors above")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
