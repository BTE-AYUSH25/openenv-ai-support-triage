# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

from typing import Any, Dict
from dataclasses import asdict

from openenv_core.client_types import StepResult
from openenv_core.env_server.types import State
from openenv_core.http_env_client import HTTPEnvClient

from ai_support_triage.models import SupportAction, SupportObservation


class AiSupportTriageEnv(HTTPEnvClient[SupportAction, SupportObservation]):
    """
    Winner-grade HTTP client for the AI Support Triage Environment.
    Handles the structured StepResult and Observation parsing.
    """

    def _step_payload(self, action: SupportAction) -> Dict[str, Any]:
        """Convert SupportAction dataclass to JSON payload."""
        # Framework automatically serializes, but we can intercept for custom logic
        payload = asdict(action)
        payload.pop("metadata", None)
        return payload

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[SupportObservation]:
        """
        Parse server response into StepResult[SupportObservation].
        Handles the format: {"observation": {...}, "reward": float, "done": bool}
        """
        obs_data = payload.get("observation", {})
        
        # Instantiate SupportObservation (a dataclass)
        observation = SupportObservation(
            ticket_id=obs_data.get("ticket_id", ""),
            customer_tier=obs_data.get("customer_tier", ""),
            ticket_history=obs_data.get("ticket_history", []),
            current_message=obs_data.get("current_message", ""),
            turn_count=obs_data.get("turn_count", 1),
            system_instructions=obs_data.get("system_instructions", ""),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> State:
        """Parse server response into State object."""
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
