#!/usr/bin/env python3
"""
Test script for Interactive Planning Flow (Phase 6).

Tests:
1. Planning state management
2. Planning hooks
3. Subagent registration
4. System prompt integration

Run:
    cd /Users/padak/github/e2b-dataapps
    source .venv/bin/activate
    python scripts/test_planning_flow.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.planning import (
    PlanningState,
    PlanningStatus,
    DataRequirement,
    UIRequirement,
    ClarifyingQuestion,
    AppPlan,
    get_planning_state,
    update_planning_state,
    reset_planning_state,
    is_planning_complete,
    PLANNING_AGENT_PROMPT,
    PLAN_VALIDATOR_PROMPT,
    REQUIREMENTS_ANALYZER_PROMPT,
)
from backend.app.planning.planning_state import PLANNING_RESULT_SCHEMA, APP_PLAN_SCHEMA


def test_planning_state_creation():
    """Test that planning states are created correctly."""
    print("Testing planning state creation...")

    session_id = "test_session_001"
    state = get_planning_state(session_id)

    assert state.session_id == session_id
    assert state.status == PlanningStatus.NOT_STARTED
    assert state.original_request is None
    assert len(state.data_requirements) == 0
    assert len(state.ui_requirements) == 0

    print("  ✓ Planning state created correctly")


def test_planning_state_update():
    """Test updating planning state."""
    print("Testing planning state update...")

    session_id = "test_session_002"
    state = get_planning_state(session_id)

    # Update status
    updated = update_planning_state(
        session_id,
        status=PlanningStatus.EXPLORING_DATA,
        original_request="I need a dashboard for sales data"
    )

    assert updated.status == PlanningStatus.EXPLORING_DATA
    assert updated.original_request == "I need a dashboard for sales data"

    print("  ✓ Planning state updated correctly")


def test_planning_state_reset():
    """Test resetting planning state."""
    print("Testing planning state reset...")

    session_id = "test_session_003"

    # Create and modify state
    update_planning_state(
        session_id,
        status=PlanningStatus.BUILDING,
        original_request="some request"
    )

    # Reset
    state = reset_planning_state(session_id)

    assert state.status == PlanningStatus.NOT_STARTED
    assert state.original_request is None

    print("  ✓ Planning state reset correctly")


def test_data_requirement():
    """Test data requirement dataclass."""
    print("Testing data requirement...")

    req = DataRequirement(
        description="Customer purchase data",
        table_id="out.c-crm.customers",
        columns=["customer_id", "name", "total_purchases"],
        filters="total_purchases > 100",
        confirmed=False
    )

    assert req.description == "Customer purchase data"
    assert req.table_id == "out.c-crm.customers"
    assert len(req.columns) == 3
    assert not req.confirmed

    print("  ✓ Data requirement works correctly")


def test_ui_requirement():
    """Test UI requirement dataclass."""
    print("Testing UI requirement...")

    req = UIRequirement(
        component_type="table",
        description="Customer list with sorting and filtering",
        data_source="customers",
        interactions=["sort", "filter", "export"],
        confirmed=True
    )

    assert req.component_type == "table"
    assert "filter" in req.interactions
    assert req.confirmed

    print("  ✓ UI requirement works correctly")


def test_clarifying_question():
    """Test clarifying question dataclass."""
    print("Testing clarifying question...")

    q = ClarifyingQuestion(
        question="Which date range should be the default?",
        context="Need to determine initial data scope",
        category="ui",
        priority=2,
        options=["Last 7 days", "Last 30 days", "Last 90 days"],
        answer=None
    )

    assert q.priority == 2
    assert len(q.options) == 3
    assert q.answer is None

    print("  ✓ Clarifying question works correctly")


def test_app_plan():
    """Test app plan dataclass."""
    print("Testing app plan...")

    plan = AppPlan(
        name="Sales Dashboard",
        description="Interactive dashboard for sales analytics",
        data_requirements=[
            DataRequirement(description="Sales data", confirmed=True)
        ],
        ui_requirements=[
            UIRequirement(component_type="dashboard", description="Main view", confirmed=True)
        ],
        components_to_use=["DataTable", "KeboolaStoragePicker"],
        custom_components=["SalesChart"],
        estimated_complexity="moderate"
    )

    assert plan.name == "Sales Dashboard"
    assert len(plan.components_to_use) == 2
    assert plan.estimated_complexity == "moderate"

    print("  ✓ App plan works correctly")


def test_planning_state_is_ready_to_build():
    """Test is_ready_to_build logic."""
    print("Testing is_ready_to_build...")

    session_id = "test_session_004"
    state = get_planning_state(session_id)

    # Not ready initially
    assert not state.is_ready_to_build()

    # Add requirements but don't approve
    state.data_requirements.append(
        DataRequirement(description="test data", confirmed=True)
    )
    state.ui_requirements.append(
        UIRequirement(component_type="table", description="test", confirmed=True)
    )

    # Still not ready (not approved)
    assert not state.is_ready_to_build()

    # Approve plan
    state.status = PlanningStatus.PLAN_APPROVED

    # Now ready
    assert state.is_ready_to_build()

    print("  ✓ is_ready_to_build works correctly")


def test_planning_state_has_unanswered_questions():
    """Test unanswered questions detection."""
    print("Testing unanswered questions detection...")

    session_id = "test_session_005"
    state = get_planning_state(session_id)

    # No questions = no unanswered
    assert not state.has_unanswered_critical_questions()

    # Add a priority 1 question without answer
    state.pending_questions.append(
        ClarifyingQuestion(
            question="Critical question",
            context="test",
            category="data",
            priority=1,
            answer=None
        )
    )

    assert state.has_unanswered_critical_questions()

    # Answer it
    state.pending_questions[0].answer = "The answer"

    assert not state.has_unanswered_critical_questions()

    print("  ✓ Unanswered questions detection works correctly")


def test_planning_state_summarize():
    """Test state summary generation."""
    print("Testing state summary...")

    session_id = "test_session_006"
    state = get_planning_state(session_id)
    state.original_request = "Build a customer dashboard"
    state.status = PlanningStatus.GATHERING_REQUIREMENTS

    state.data_requirements.append(
        DataRequirement(description="Customer data", confirmed=True)
    )
    state.pending_questions.append(
        ClarifyingQuestion(
            question="Which metrics?",
            context="test",
            category="ui",
            priority=1,
            answer=None
        )
    )

    summary = state.summarize()

    assert "gathering_requirements" in summary
    assert "Customer data" in summary
    assert "Which metrics?" in summary

    print("  ✓ State summary generation works correctly")


def test_prompts_exist():
    """Test that planning prompts are defined."""
    print("Testing planning prompts...")

    assert PLANNING_AGENT_PROMPT and len(PLANNING_AGENT_PROMPT) > 100
    assert PLAN_VALIDATOR_PROMPT and len(PLAN_VALIDATOR_PROMPT) > 100
    assert REQUIREMENTS_ANALYZER_PROMPT and len(REQUIREMENTS_ANALYZER_PROMPT) > 100

    # Check key content
    assert "data exploration" in PLANNING_AGENT_PROMPT.lower() or "explore" in PLANNING_AGENT_PROMPT.lower()
    assert "json" in PLAN_VALIDATOR_PROMPT.lower()
    assert "requirements" in REQUIREMENTS_ANALYZER_PROMPT.lower()

    print("  ✓ Planning prompts are defined correctly")


def test_schemas_valid():
    """Test that JSON schemas are valid."""
    print("Testing JSON schemas...")

    # Check PLANNING_RESULT_SCHEMA
    assert PLANNING_RESULT_SCHEMA["type"] == "object"
    assert "status" in PLANNING_RESULT_SCHEMA["properties"]
    assert "understanding" in PLANNING_RESULT_SCHEMA["properties"]
    assert "clarifying_questions" in PLANNING_RESULT_SCHEMA["properties"]

    # Check APP_PLAN_SCHEMA
    assert APP_PLAN_SCHEMA["type"] == "object"
    assert "name" in APP_PLAN_SCHEMA["properties"]
    assert "pages" in APP_PLAN_SCHEMA["properties"]
    assert "data_sources" in APP_PLAN_SCHEMA["properties"]

    print("  ✓ JSON schemas are valid")


def test_agent_subagents_registered():
    """Test that planning subagents are registered in agent.py."""
    print("Testing subagent registration...")

    # Read agent.py and check content instead of importing (SDK takes too long)
    import os
    agent_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "backend", "app", "agent.py"
    )

    with open(agent_path, "r") as f:
        content = f.read()

    # Check planning subagents exist
    assert '"requirements-analyzer": AgentDefinition' in content
    assert '"planning-agent": AgentDefinition' in content
    assert '"plan-validator": AgentDefinition' in content

    # Check tools
    assert "mcp__keboola__list_buckets" in content
    assert "mcp__keboola__query_data" in content

    print("  ✓ Planning subagents registered correctly")


def test_hooks_registered():
    """Test that planning hooks are registered."""
    print("Testing hook registration...")

    # Read agent.py and check content instead of importing (SDK takes too long)
    import os
    agent_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "backend", "app", "agent.py"
    )

    with open(agent_path, "r") as f:
        content = f.read()

    # Check planning hooks exist
    assert "track_planning_state" in content
    assert "suggest_planning_on_new_request" in content
    assert "self_heal_planning_issues" in content

    # Check hooks are configured
    assert "HookMatcher(matcher=\"Write\", hooks=[suggest_planning_on_new_request])" in content
    assert "mcp__keboola__" in content and "track_planning_state" in content

    print("  ✓ Planning hooks registered correctly")


def test_system_prompt_includes_planning():
    """Test that system prompt includes planning instructions."""
    print("Testing system prompt integration...")

    # Read agent.py and check content instead of importing (SDK takes too long)
    import os
    agent_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "backend", "app", "agent.py"
    )

    with open(agent_path, "r") as f:
        content = f.read()

    # Check planning content is included
    assert "INTERACTIVE_PLANNING_PROMPT" in content
    assert "Planning Subagents" in content
    assert "requirements-analyzer" in content

    print("  ✓ System prompt includes planning instructions")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Interactive Planning Flow Tests (Phase 6)")
    print("=" * 60 + "\n")

    tests = [
        test_planning_state_creation,
        test_planning_state_update,
        test_planning_state_reset,
        test_data_requirement,
        test_ui_requirement,
        test_clarifying_question,
        test_app_plan,
        test_planning_state_is_ready_to_build,
        test_planning_state_has_unanswered_questions,
        test_planning_state_summarize,
        test_prompts_exist,
        test_schemas_valid,
        test_agent_subagents_registered,
        test_hooks_registered,
        test_system_prompt_includes_planning,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
