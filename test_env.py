# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import pytest
from ai_support_triage.server.ai_support_triage_environment import AiSupportTriageEnvironment
from ai_support_triage.models import SupportAction, Category, Priority, EscalationTarget, TicketStatus

def test_environment_reset():
    """Verify environment reset returns expected observation type."""
    env = AiSupportTriageEnvironment()
    env.select_task(task_id="easy_1")
    obs = env.reset()
    assert obs.ticket_id == "easy_1"
    assert obs.reward == 0.0 # Initial reward
    assert obs.done == False

def test_easy_grading_logic():
    """Verify classification grading for easy tasks."""
    env = AiSupportTriageEnvironment()
    env.select_task(task_id="easy_1") # password reset
    env.reset()
    
    # Correct action
    action = SupportAction(
        response_draft="Here is your reset link.",
        assigned_category=Category.ACCOUNT_ACCESS,
        assigned_priority=Priority.LOW,
        escalated_to=EscalationTarget.NONE,
        new_status=TicketStatus.RESOLVED
    )
    obs = env.step(action)
    assert obs.reward == 1.0 # Perfect classification

def test_medium_grading_keywords():
    """Verify keyword and routing grading for medium tasks."""
    env = AiSupportTriageEnvironment()
    env.select_task(task_id="medium_1") # overcharge refund
    env.reset()
    
    # Action with required keywords but suboptimal priority
    action = SupportAction(
        response_draft="I apologize for the overcharge. I will issue a refund and escalate to my manager.",
        assigned_category=Category.BILLING,
        assigned_priority=Priority.NORMAL, # Task expects HIGH
        escalated_to=EscalationTarget.MANAGER,
        new_status=TicketStatus.ESCALATED
    )
    obs = env.step(action)
    # 0.1 (cat) + 0.0 (prio) + 0.3 (routing) + 0.5 (keywords: apologize, refund, escalate, manager)
    # "sorry" is missing from keywords but 4/5 present. 0.5 * 0.8 = 0.4
    # 0.1 + 0.3 + 0.4 = 0.8
    assert 0.7 <= obs.reward <= 0.9

def test_hard_decoy_penalty():
    """Verify that falling for legal decoys results in a lower score."""
    env = AiSupportTriageEnvironment()
    env.select_task(task_id="hard_1") # admin recovery with threat
    env.reset()
    
    # Fails by escalating to legal without demanding authorization (Rule 8/23 constraint)
    action = SupportAction(
        response_draft="I've escalated your legal threat to our lawyers. I can reset it now.",
        assigned_category=Category.TECHNICAL,
        assigned_priority=Priority.CRITICAL,
        escalated_to=EscalationTarget.LEGAL, # Decoy: Legal threat should NOT be escalated immediately
        new_status=TicketStatus.ESCALATED
    )
    obs = env.step(action)
    assert obs.reward < 0.5
def test_legendary_logic():
    """Verify that the agent correctly handles Article 20 vs Article 17 conflict."""
    env = AiSupportTriageEnvironment()
    env.select_task(task_id="hard_3") # GDPR erasure vs Portability vs Legal Hold
    env.reset()
    
    # Correct action: Mention Article 20 and handle Legal Hold
    action = SupportAction(
        response_draft="We have received your GDPR request. Note Article 20 (Data Portability) must be fulfilled before erasure. Also, activity logs are on legal hold due to an open dispute.",
        assigned_category=Category.OTHER,
        assigned_priority=Priority.NORMAL,
        escalated_to=EscalationTarget.LEGAL,
        new_status=TicketStatus.PENDING_CUSTOMER
    )
    obs = env.step(action)
    assert obs.reward > 0.8

@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Rule 16: Verify metrics endpoint exists and returns JSON."""
    from ai_support_triage.server.app import app
    from httpx import AsyncClient, ASGITransport
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "metrics" in data
        assert "memory_usage_mb" in data["metrics"]

if __name__ == "__main__":
    pytest.main(["-v", __file__])
