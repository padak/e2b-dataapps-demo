"""
Planning State Management for Interactive App Building.

This module manages the state of the planning process, tracking:
- What requirements have been gathered
- What clarifying questions are pending
- Whether the plan is complete enough to build

The state is session-scoped and thread-safe.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import threading
import logging

logger = logging.getLogger(__name__)


class PlanningStatus(Enum):
    """Status of the planning process."""
    NOT_STARTED = "not_started"
    GATHERING_REQUIREMENTS = "gathering_requirements"
    EXPLORING_DATA = "exploring_data"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    PLAN_READY = "plan_ready"
    PLAN_APPROVED = "plan_approved"
    BUILDING = "building"


@dataclass
class DataRequirement:
    """A specific data requirement for the app."""
    description: str
    table_id: Optional[str] = None  # e.g., "out.c-amplitude.events"
    columns: list[str] = field(default_factory=list)
    filters: Optional[str] = None  # SQL WHERE conditions
    aggregations: Optional[str] = None  # GROUP BY, SUM, etc.
    confirmed: bool = False


@dataclass
class UIRequirement:
    """A specific UI requirement for the app."""
    component_type: str  # "table", "chart", "form", "dashboard", etc.
    description: str
    data_source: Optional[str] = None  # Which DataRequirement this uses
    interactions: list[str] = field(default_factory=list)  # "filter", "sort", "export"
    confirmed: bool = False


@dataclass
class ClarifyingQuestion:
    """A question to ask the user for clarification."""
    question: str
    context: str  # Why we're asking this
    category: str  # "data", "ui", "interaction", "scope"
    priority: int  # 1 = must answer, 2 = should answer, 3 = nice to know
    options: list[str] = field(default_factory=list)  # Suggested answers
    answer: Optional[str] = None


@dataclass
class AppPlan:
    """Complete plan for the app to be built."""
    name: str
    description: str
    data_requirements: list[DataRequirement] = field(default_factory=list)
    ui_requirements: list[UIRequirement] = field(default_factory=list)
    components_to_use: list[str] = field(default_factory=list)  # From curated library
    custom_components: list[str] = field(default_factory=list)  # To generate
    estimated_complexity: str = "simple"  # "simple", "moderate", "complex"
    notes: list[str] = field(default_factory=list)


@dataclass
class PlanningState:
    """
    Complete state of the planning process for a session.

    This tracks everything from initial request to final plan.
    """
    session_id: str
    status: PlanningStatus = PlanningStatus.NOT_STARTED

    # User's original request
    original_request: Optional[str] = None

    # Data exploration results
    available_tables: list[dict] = field(default_factory=list)
    explored_schemas: list[str] = field(default_factory=list)
    data_samples: dict = field(default_factory=dict)  # table_id -> sample data

    # Requirements gathering
    data_requirements: list[DataRequirement] = field(default_factory=list)
    ui_requirements: list[UIRequirement] = field(default_factory=list)

    # Clarification
    pending_questions: list[ClarifyingQuestion] = field(default_factory=list)
    answered_questions: list[ClarifyingQuestion] = field(default_factory=list)

    # Final plan
    plan: Optional[AppPlan] = None

    # Self-healing: detected issues during planning
    planning_issues: list[str] = field(default_factory=list)
    auto_corrections: list[str] = field(default_factory=list)

    def has_unanswered_critical_questions(self) -> bool:
        """Check if there are unanswered critical questions."""
        return any(q.priority == 1 and q.answer is None for q in self.pending_questions)

    def get_next_question(self) -> Optional[ClarifyingQuestion]:
        """Get the next unanswered question by priority."""
        unanswered = [q for q in self.pending_questions if q.answer is None]
        if not unanswered:
            return None
        return sorted(unanswered, key=lambda q: q.priority)[0]

    def is_ready_to_build(self) -> bool:
        """Check if we have enough information to start building."""
        # Must have at least one data requirement
        if not self.data_requirements:
            return False

        # Must have at least one UI requirement
        if not self.ui_requirements:
            return False

        # Must not have unanswered critical questions
        if self.has_unanswered_critical_questions():
            return False

        # Plan must be approved
        if self.status != PlanningStatus.PLAN_APPROVED:
            return False

        return True

    def summarize(self) -> str:
        """Generate a human-readable summary of the planning state."""
        lines = [
            f"## Planning Status: {self.status.value}",
            "",
        ]

        if self.original_request:
            lines.extend([
                "### Original Request",
                f"> {self.original_request}",
                "",
            ])

        if self.data_requirements:
            lines.append("### Data Requirements")
            for i, req in enumerate(self.data_requirements, 1):
                status = "✓" if req.confirmed else "?"
                lines.append(f"{i}. [{status}] {req.description}")
                if req.table_id:
                    lines.append(f"   Table: `{req.table_id}`")
            lines.append("")

        if self.ui_requirements:
            lines.append("### UI Requirements")
            for i, req in enumerate(self.ui_requirements, 1):
                status = "✓" if req.confirmed else "?"
                lines.append(f"{i}. [{status}] {req.component_type}: {req.description}")
            lines.append("")

        pending = [q for q in self.pending_questions if q.answer is None]
        if pending:
            lines.append("### Pending Questions")
            for q in sorted(pending, key=lambda x: x.priority):
                priority_label = ["🔴", "🟡", "🟢"][q.priority - 1]
                lines.append(f"{priority_label} {q.question}")
            lines.append("")

        if self.planning_issues:
            lines.append("### Issues Detected")
            for issue in self.planning_issues:
                lines.append(f"⚠️ {issue}")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# SESSION STATE STORAGE
# =============================================================================

_planning_states: dict[str, PlanningState] = {}
_state_lock = threading.Lock()


def get_planning_state(session_id: str) -> PlanningState:
    """Get the planning state for a session, creating if needed."""
    with _state_lock:
        if session_id not in _planning_states:
            _planning_states[session_id] = PlanningState(session_id=session_id)
            logger.info(f"[PLANNING] Created new planning state for session {session_id}")
        return _planning_states[session_id]


def update_planning_state(session_id: str, **kwargs) -> PlanningState:
    """Update specific fields of the planning state."""
    with _state_lock:
        # Get or create state directly (don't call get_planning_state to avoid deadlock)
        if session_id not in _planning_states:
            _planning_states[session_id] = PlanningState(session_id=session_id)
            logger.info(f"[PLANNING] Created new planning state for session {session_id}")
        state = _planning_states[session_id]

        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
                logger.debug(f"[PLANNING] Session {session_id}: Updated {key}")
            else:
                logger.warning(f"[PLANNING] Session {session_id}: Unknown field {key}")
        return state


def reset_planning_state(session_id: str) -> PlanningState:
    """Reset the planning state for a session."""
    with _state_lock:
        _planning_states[session_id] = PlanningState(session_id=session_id)
        logger.info(f"[PLANNING] Reset planning state for session {session_id}")
        return _planning_states[session_id]


def is_planning_complete(session_id: str) -> bool:
    """Check if planning is complete and ready to build."""
    state = get_planning_state(session_id)
    return state.is_ready_to_build()


# =============================================================================
# STRUCTURED OUTPUT SCHEMAS (for Claude Agent SDK)
# =============================================================================

PLANNING_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["needs_clarification", "ready_to_plan", "plan_complete"],
            "description": "Current status of the planning process"
        },
        "understanding": {
            "type": "string",
            "description": "Summary of what we understand about the user's needs"
        },
        "data_requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "table_id": {"type": "string"},
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "confirmed": {"type": "boolean"}
                },
                "required": ["description"]
            }
        },
        "ui_requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "component_type": {"type": "string"},
                    "description": {"type": "string"},
                    "confirmed": {"type": "boolean"}
                },
                "required": ["component_type", "description"]
            }
        },
        "clarifying_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "context": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["data", "ui", "interaction", "scope"]
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["question", "category", "priority"]
            }
        },
        "recommended_components": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Components from curated library to use"
        },
        "estimated_complexity": {
            "type": "string",
            "enum": ["simple", "moderate", "complex"]
        },
        "next_action": {
            "type": "string",
            "description": "What the agent should do next"
        }
    },
    "required": ["status", "understanding", "next_action"]
}


APP_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "pages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "title": {"type": "string"},
                    "components": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["path", "title"]
            }
        },
        "data_sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "table_id": {"type": "string"},
                    "query": {"type": "string"}
                },
                "required": ["name", "table_id"]
            }
        },
        "api_routes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "method": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["path", "method"]
            }
        },
        "curated_components": {
            "type": "array",
            "items": {"type": "string"}
        },
        "custom_components": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["name", "description", "pages"]
}
