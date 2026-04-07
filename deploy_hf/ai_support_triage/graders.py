# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import logging
from typing import Dict, Any, List
from ai_support_triage.models import SupportAction, Category, Priority, EscalationTarget, TicketStatus

logger = logging.getLogger("ai_support_triage.graders")

def priority_distance(p1: Priority, p2: Priority) -> int:
    """Calculate numerical distance between two priorities."""
    levels = {Priority.LOW: 0, Priority.NORMAL: 1, Priority.HIGH: 2, Priority.CRITICAL: 3}
    v1 = levels.get(p1 if isinstance(p1, Priority) else Priority(p1), 0)
    v2 = levels.get(p2 if isinstance(p2, Priority) else Priority(p2), 0)
    return abs(v1 - v2)

def score_eq_and_professionalism(draft: str, task_id: str) -> float:
    """
    Legendary Feature: Emotional Intelligence & Professionalism Grader.
    Higher stakes on 'hard' tasks.
    """
    if not draft:
        return 0.0
        
    score = 1.0
    draft_lower = draft.lower()
    
    # 1. Structure Check (-0.2 total)
    greetings = ["hello", "hi", "dear", "good morning", "good afternoon"]
    if not any(g in draft_lower[:50] for g in greetings):
        score -= 0.1
        
    closings = ["regards", "best", "thank you", "sincerely", "support team"]
    if not any(c in draft_lower[-50:] for c in closings):
        score -= 0.1
    
    # 2. Empathy / EQ Check (0.4)
    empathy_keywords = ["understand", "apologize", "sorry", "assist", "help", "frustrating", "experience", "patience"]
    found_empathy = sum(1 for kw in empathy_keywords if kw in draft_lower)
    if found_empathy < 2:
        score -= 0.2
    
    # 3. Robotic Phrase Penalty (Stricter for Hard)
    robotic_phrases = ["as an ai", "i am programmed", "cannot fulfill", "policy dictates"]
    if any(p in draft_lower for p in robotic_phrases):
        score -= 0.3 if "hard" in task_id else 0.1
        
    return max(0.0, score)

def score_easy_task(action: SupportAction, task: Dict[str, Any]) -> float:
    """Grade easy classification tasks."""
    score = 0.0
    # Core categorization (0.6)
    if str(action.assigned_category) == str(task["expected_category"]):
        score += 0.3
    if str(action.assigned_priority) == str(task["expected_priority"]):
        score += 0.3
        
    # EQ Integration (0.4)
    eq = score_eq_and_professionalism(action.response_draft, task["id"])
    score += eq * 0.4
    
    return float(min(1.0, score))

def score_medium_task(action: SupportAction, task: Dict[str, Any]) -> float:
    """Grade medium composite tasks (Keyword + Routing)."""
    score = 0.0
    
    # Triage Accuracy (0.4)
    if str(action.assigned_category) == str(task["expected_category"]):
        score += 0.2
    if priority_distance(action.assigned_priority, task["expected_priority"]) == 0:
        score += 0.2
        
    # Routing (0.3)
    if str(action.escalated_to) == str(task["expected_escalation"]):
        score += 0.3
        
    # Quality & EQ (0.3)
    eq = score_eq_and_professionalism(action.response_draft, task["id"])
    
    # Keyword check
    draft = action.response_draft.lower()
    req_keywords = task.get("required_keywords", [])
    keyword_score = 0.0
    if req_keywords:
        found = sum(1 for kw in req_keywords if kw.lower() in draft)
        keyword_score = found / len(req_keywords)
        
    score += (eq * 0.15) + (keyword_score * 0.15)
    
    return float(min(1.0, score))

def score_hard_task(action: SupportAction, task: Dict[str, Any]) -> float:
    """Grade complex multi-constraint and multi-turn tasks."""
    score = 0.0
    draft = action.response_draft.lower()
    
    # 1. Action Alignment (0.3)
    if action.escalated_to == task.get("expected_escalation"):
        score += 0.15
    if action.new_status == task.get("expected_status"):
        score += 0.15
        
    # 2. Domain Specific Logic (0.4)
    # Hard_1: Security/Decoy
    if task["id"] == "hard_1":
        if action.escalated_to == EscalationTarget.LEGAL:
            score -= 0.3 # Fell for threat decoy
        elif action.escalated_to == EscalationTarget.MANAGEMENT:
            score += 0.2
            
    # Hard_2: Policy 4.2
    if task["id"] == "hard_2":
        if "refund" in draft and "process" in draft:
            score -= 0.4 # Violated Policy 4.2
        else:
            score += 0.2
            
    # Hard_3: GDPR article conflict
    if task["id"] == "hard_3":
        if "article 20" in draft and "portability" in draft:
            score += 0.2
        if "legal hold" in draft:
            score += 0.1
        if "article 17" in draft and "erasure" in draft:
            # Erasure must NOT happen if legal hold exists
            score -= 0.1 if "hold" not in draft else 0.0

    # 3. Quality & EQ (0.3)
    eq = score_eq_and_professionalism(action.response_draft, task["id"])
    
    # Optimal elements check
    opt_elements = task.get("optimal_response_elements", [])
    if opt_elements:
        found = sum(1 for el in opt_elements if el.lower() in draft)
        score += 0.1 * (found / len(opt_elements))
    
    score += eq * 0.2
    
    return float(max(0.0, min(1.0, score)))

def grade_task(action: SupportAction, task: Dict[str, Any]) -> float:
    """Unified entry point for grading."""
    try:
        t_id = task.get("id", "")
        if t_id.startswith("easy"):
            return score_easy_task(action, task)
        elif t_id.startswith("medium"):
            return score_medium_task(action, task)
        elif t_id.startswith("hard"):
            return score_hard_task(action, task)
        return 0.0
    except Exception as e:
        logger.error(f"Grader error: {e}")
        return 0.0
