# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import logging
from typing import Dict, Any
from ai_support_triage.models import SupportAction, Priority, EscalationTarget

logger = logging.getLogger("ai_support_triage.graders")

def priority_distance(p1: Priority, p2: Priority) -> int:
    """Calculate numerical distance between two priorities."""
    levels = {Priority.LOW: 0, Priority.NORMAL: 1, Priority.HIGH: 2, Priority.CRITICAL: 3}
    return abs(levels.get(p1, 0) - levels.get(p2, 0))

def score_easy_task(action: SupportAction, task: Dict[str, Any]) -> float:
    """Grade easy classification tasks (Category & Priority)."""
    try:
        score = 0.0
        # Category check (0.5 points)
        if str(action.assigned_category) == str(task["expected_category"]):
            score += 0.5
        
        # Priority check (0.5 points)
        dist = priority_distance(action.assigned_priority, task["expected_priority"])
        if dist == 0:
            score += 0.5
        elif dist == 1:
            score += 0.25 # Partial credit for being close
            
        return float(score)
    except Exception as e:
        logger.error(f"Error grading easy task: {e}")
        return 0.0

def score_medium_task(action: SupportAction, task: Dict[str, Any]) -> float:
    """Grade medium composite tasks (Response keywords + Routing)."""
    try:
        score = 0.0
        
        # Metadata check (0.2 points)
        if str(action.assigned_category) == str(task["expected_category"]):
            score += 0.1
        if priority_distance(action.assigned_priority, task["expected_priority"]) == 0:
            score += 0.1
            
        # Escalation routing check (0.3 points)
        if str(action.escalated_to) == str(task["expected_escalation"]):
            score += 0.3
            
        # Response draft keyword check (0.5 points)
        draft = action.response_draft.lower()
        req_keywords = task.get("required_keywords", [])
        if req_keywords:
            found_count = sum(1 for kw in req_keywords if kw.lower() in draft)
            score += 0.5 * (found_count / len(req_keywords))
            
        # Forbidden phrase penalty (-0.3 points)
        for forbidden in task.get("forbidden_phrases", []):
            if forbidden.lower() in draft:
                score -= 0.3
                break
                
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.error(f"Error grading medium task: {e}")
        return 0.0

def score_hard_task(action: SupportAction, task: Dict[str, Any]) -> float:
    """Grade hard tasks (Hidden constraints + Multi-turn)."""
    try:
        score = 0.0
        
        # Core alignment (0.2)
        if action.escalated_to == task.get("expected_escalation"):
            score += 0.1
        if action.new_status == task.get("expected_status"):
            score += 0.1
            
        draft = action.response_draft.lower()
        
        # Multi-stage reasoning / Hidden constraint identification (0.5)
        opt_elements = task.get("optimal_response_elements", [])
        if opt_elements:
            found_count = sum(1 for el in opt_elements if el.lower() in draft)
            score += 0.5 * (found_count / len(opt_elements))
            
        # Decoy avoidance check (-0.2 penalty for falling for distractors)
        if task["id"] == "hard_1" and action.escalated_to == EscalationTarget.LEGAL:
            score -= 0.2 # Failed decoy check
        if task["id"] == "hard_2" and "refund processed" in draft:
            score -= 0.2 # Violated policy 4.2
            
        # General response quality / Professionalism (0.3)
        if len(draft) > 50:
            score += 0.3
            
        # Hard_3 specific: Conflict resolution (Article 20 must precede Article 17)
        if task["id"] == "hard_3":
            # Bonus for mentioning Article 20 Portability
            if "article 20" in draft:
                score += 0.2
            # Penalty for missing the Legal Hold conflict
            if "legal hold" not in draft:
                score -= 0.1
                
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.error(f"Error grading hard task: {e}")
        return 0.0

def grade_task(action: SupportAction, task: Dict[str, Any]) -> float:
    """Main grading entry point with Rule 8 fallback."""
    try:
        if task["id"].startswith("easy"):
            return score_easy_task(action, task)
        elif task["id"].startswith("medium"):
            return score_medium_task(action, task)
        elif task["id"].startswith("hard"):
            return score_hard_task(action, task)
        return 0.0
    except Exception as e:
        logger.critical(f"UNEXPECTED GRADER FAILURE: {e}")
        return 0.0
