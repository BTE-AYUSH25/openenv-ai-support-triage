# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import logging
from uuid import uuid4
from typing import Dict, Any, List

from openenv_core.env_server.interfaces import Environment
from openenv_core.env_server.types import State

from ai_support_triage.models import SupportAction, SupportObservation, TicketStatus
import ai_support_triage.tasks as tasks
import ai_support_triage.graders as graders
import json
import time
import hashlib
import psutil
from os import path

# Configure structured logging
logger = logging.getLogger("ai_support_triage")

class AiSupportTriageEnvironment(Environment):
    """
    Winner-grade AI Support Triage Environment.
    Implements multi-turn capability and automated grading.
    """

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._reset_count = 0
        self._current_task: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []

    def select_task(self, task_id: str):
        """Set the task to be used in the next reset."""
        try:
            self._current_task = tasks.get_task_by_id(task_id).copy()
            logger.info(f"Task selected: {task_id}")
        except Exception as e:
            logger.error(f"Failed to select task {task_id}: {e}")

    def reset(self) -> SupportObservation:
        """
        Reset the environment with a clean state.
        """
        try:
            self._state = State(episode_id=str(uuid4()), step_count=0)
            self._reset_count += 1
            self._history = []
            
            # If no task was pre-selected, default to the first
            if not self._current_task:
                self.select_task(tasks.all_tasks[0]["id"])
            
            return SupportObservation(
                ticket_id=self._current_task["id"],
                customer_tier=self._current_task["customer_tier"],
                ticket_history=[],
                current_message=self._current_task["current_message"],
                turn_count=1,
                system_instructions=self._current_task.get("system_instructions", ""),
                done=False,
                reward=0.0, # Initial reward
                metadata={"reset_count": self._reset_count}
            )
        except Exception as e:
            logger.critical(f"Critical error during reset: {e}")
            raise RuntimeError(f"Failed to reset environment: {e}")

    def _calculate_checksum(self) -> str:
        """Rule 20: State Integrity Protection."""
        history_str = json.dumps(self._history, sort_keys=True)
        return hashlib.sha256(history_str.encode()).hexdigest()

    def step(self, action: SupportAction) -> SupportObservation:
        """
        Execute a step in the triage environment.
        Rule 23: Ensure input is validated and enums are correctly cast.
        """
        start_time = time.perf_counter()
        try:
            self._state.step_count += 1
            
            # Rule 23: Convert potential strings to Enums for deterministic comparison
            from ai_support_triage.models import validate_action_data, SupportAction as SupportActionDC
            from dataclasses import asdict
            
            item_data = asdict(action)
            item_data.pop("metadata", None)
            validated = validate_action_data(item_data)
            valid_action = SupportActionDC(**validated.model_dump())
            
            # Grade the action
            score = graders.grade_task(valid_action, self._current_task)
            
            # Capture the action in history
            self._history.append({"turn": self._state.step_count, "action": asdict(valid_action), "reward": score})
            
            # Legendary Feature: Audit Logging (Rule 16 extension)
            audit_entry = {
                "timestamp": str(time.time()),
                "episode_id": self._state.episode_id,
                "step": self._state.step_count,
                "task_id": self._current_task["id"],
                "action": asdict(valid_action),
                "reward": score
            }
            with open("audit.jsonl", "a") as f:
                f.write(json.dumps(audit_entry) + "\n")
            
            # Multi-turn logic
            required_turns = self._current_task.get("turn_count", 1)
            # Finish if turns exceeded or if agent resolves/escalates (standard behavior)
            from ai_support_triage.models import TicketStatus
            is_resolved = valid_action.new_status == TicketStatus.RESOLVED
            is_escalated = valid_action.new_status == TicketStatus.ESCALATED
            
            done = self._state.step_count >= required_turns or is_resolved or is_escalated
            
            execution_time = time.perf_counter() - start_time
            memory_usage = psutil.Process().memory_info().rss / (1024 * 1024)
            
            return SupportObservation(
                ticket_id=self._current_task["id"],
                customer_tier=self._current_task["customer_tier"],
                ticket_history=self._history,
                current_message="[SYSTEM]: Processing update." if not done else "[SYSTEM]: Task Complete.",
                turn_count=self._state.step_count + 1,
                system_instructions=self._current_task.get("system_instructions", ""),
                done=done,
                reward=float(score),
                metadata={
                    "checksum": self._calculate_checksum(),
                    "execution_time_ms": execution_time * 1000,
                    "memory_mb": memory_usage
                }
            )
        except Exception as e:
            logger.error(f"Error during step processing: {e}")
            return SupportObservation(
                ticket_id=self._current_task.get("id", "unknown"),
                customer_tier=self._current_task.get("customer_tier", "unknown"),
                ticket_history=self._history,
                current_message=f"SYSTEM ERROR: {str(e)}",
                turn_count=self._state.step_count,
                done=True,
                reward=-1.0,
                metadata={"error": str(e), "checksum": self._calculate_checksum()}
            )

    @property
    def state(self) -> State:
        return self._state
