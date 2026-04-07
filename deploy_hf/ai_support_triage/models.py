# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, ValidationError

# Framework imports
from openenv_core.env_server.types import Action, Observation

# --- Enums for strict validation ---

class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class Category(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT_ACCESS = "account_access"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"

class EscalationTarget(str, Enum):
    NONE = "none"
    TIER_2_TECH = "tier_2_tech"
    MANAGER = "manager"
    LEGAL = "legal"
    SALES = "sales"
    MANAGEMENT = "management"
    SECURITY_TEAM = "security_team"

class TicketStatus(str, Enum):
    OPEN = "open"
    PENDING_CUSTOMER = "pending_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"

# --- Dataclasses for OpenEnv compatibility ---

@dataclass(kw_only=True)
class SupportAction(Action):
    response_draft: str
    assigned_category: Category
    assigned_priority: Priority
    escalated_to: EscalationTarget
    new_status: TicketStatus

@dataclass(kw_only=True)
class SupportObservation(Observation):
    ticket_id: str
    customer_tier: str
    ticket_history: List[Dict[str, Any]] = field(default_factory=list)
    current_message: str
    turn_count: int = 1
    system_instructions: str = ""
    done: bool = False
    reward: float = 0.0

# --- Pydantic Schemas for Rule 23 (Strict Validation) ---

class ActionSchema(BaseModel):
    """Pydantic schema for input validation before processing."""
    response_draft: str
    assigned_category: Category
    assigned_priority: Priority
    escalated_to: EscalationTarget
    new_status: TicketStatus

    model_config = {
        "use_enum_values": False
    }

def validate_action_data(data: Dict[str, Any]) -> ActionSchema:
    """Strictly validate incoming action data according to Rule 23."""
    try:
        return ActionSchema(**data)
    except ValidationError as e:
        raise ValueError(f"Schema validation failed: {e.json()}")
