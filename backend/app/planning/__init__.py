"""
Interactive Planning Module for App Builder Agent.

This module provides intelligent planning capabilities that:
- Analyze user requirements through structured dialogue
- Explore available data using Keboola MCP
- Generate clarifying questions based on context
- Validate plans before execution
- Self-heal by detecting missing requirements

The planning flow is designed to be agenticky - it doesn't follow
rigid templates but adapts to the user's actual needs.
"""

from .planning_state import (
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
)

from .planning_prompts import (
    PLANNING_AGENT_PROMPT,
    PLAN_VALIDATOR_PROMPT,
    REQUIREMENTS_ANALYZER_PROMPT,
)

__all__ = [
    # State management
    "PlanningState",
    "PlanningStatus",
    "DataRequirement",
    "UIRequirement",
    "ClarifyingQuestion",
    "AppPlan",
    "get_planning_state",
    "update_planning_state",
    "reset_planning_state",
    "is_planning_complete",
    # Prompts
    "PLANNING_AGENT_PROMPT",
    "PLAN_VALIDATOR_PROMPT",
    "REQUIREMENTS_ANALYZER_PROMPT",
]
