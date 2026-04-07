from typing import List, Dict, Any

from ai_support_triage.models import Category, Priority, EscalationTarget, TicketStatus

easy_tasks = [
    {
        "id": "easy_1",
        "turn_count": 1,
        "customer_tier": "free",
        "current_message": "How do I change my password? I forgot it and the reset link isn't working.",
        "expected_category": Category.ACCOUNT_ACCESS,
        "expected_priority": Priority.LOW,
    },
    {
        "id": "easy_2",
        "turn_count": 1,
        "customer_tier": "enterprise",
        "current_message": "Our entire system went down. No API calls are succeeding. We are losing money.",
        "expected_category": Category.TECHNICAL,
        "expected_priority": Priority.CRITICAL,
    },
    {
        "id": "easy_3",
        "turn_count": 1,
        "customer_tier": "pro",
        "current_message": "Can I get a copy of my invoice for last month?",
        "expected_category": Category.BILLING,
        "expected_priority": Priority.LOW,
    },
    {
        "id": "easy_4",
        "turn_count": 1,
        "customer_tier": "pro",
        "current_message": "I want a dark mode in the dashboard.",
        "expected_category": Category.FEATURE_REQUEST,
        "expected_priority": Priority.LOW,
    },
    {
        "id": "easy_5",
        "turn_count": 1,
        "customer_tier": "enterprise",
        "current_message": "API response times are taking 5 seconds instead of 100ms. Please look into this immediately.",
        "expected_category": Category.TECHNICAL,
        "expected_priority": Priority.HIGH,
    }
]

medium_tasks = [
    {
        "id": "medium_1",
        "turn_count": 1,
        "customer_tier": "pro",
        "current_message": "I was overcharged $299 on my card instead of the usual $99! I need an immediate refund of $200 and a correction to my tier.",
        "expected_category": Category.BILLING,
        "expected_priority": Priority.HIGH,
        "required_keywords": ["sorry", "apologize", "refund", "escalate", "manager"],
        "forbidden_phrases": ["it's your fault", "we can't do anything"],
        "expected_escalation": EscalationTarget.MANAGER, # >$100 needs manager
        "expected_status": TicketStatus.ESCALATED
    },
    {
        "id": "medium_2",
        "turn_count": 1,
        "customer_tier": "enterprise",
        "current_message": "Our data sync connector to Salesforce has failed for 6 hours. This is blocking our global sales team.",
        "expected_category": Category.TECHNICAL,
        "expected_priority": Priority.CRITICAL,
        "required_keywords": ["investigation", "team", "apologize", "restore"],
        "forbidden_phrases": ["we will fix it tomorrow", "low priority"],
        "expected_escalation": EscalationTarget.TIER_2_TECH,
        "expected_status": TicketStatus.ESCALATED
    },
    {
        "id": "medium_3",
        "turn_count": 1,
        "customer_tier": "free",
        "current_message": "Can you permanently delete my account and all associated data under GDPR?",
        "expected_category": Category.ACCOUNT_ACCESS,
        "expected_priority": Priority.NORMAL,
        "required_keywords": ["delete", "confirm", "gdpr"],
        "forbidden_phrases": ["no", "refuse"],
        "expected_escalation": EscalationTarget.LEGAL,
        "expected_status": TicketStatus.ESCALATED
    }
]

hard_tasks = [
    {
        "id": "hard_1",
        "turn_count": 1,
        "customer_tier": "enterprise",
        "current_message": "Our admin left the company on bad terms. We need you to manually reset the 2FA on his account so we can access our dashboard. Do this within 2 hours or we will sue.",
        "system_instructions": "POLICY: ALL admin account recovery requests for departed employees must have written sign-off from an IT Director. Legal threats should not bypass policy. Do not escalate to legal immediately for empty threats, request the authorization first.",
        "hidden_constraint": "Requires IT director sign-off in writing",
        "decoy": "Legal threat (should not cause immediate panic/escalation to legal without requesting auth first)",
        "optimal_response_elements": ["request written authorization", "IT director"],
        "expected_escalation": EscalationTarget.NONE,
        "expected_status": TicketStatus.PENDING_CUSTOMER
    },
    {
        "id": "hard_2",
        "turn_count": 1,
        "customer_tier": "pro",
        "current_message": "I canceled on the 28th, but you still charged me on the 1st! I want this reversed immediately and I dispute this with my bank.",
        "system_instructions": "POLICY: Section 4.2 states cancellations take effect next billing cycle if not done 5 days prior. No refunds for late cancellations without manager approval. Bank disputes automatically suspend the account pending resolution.",
        "hidden_constraint": "Cancellation was only 3 days prior, so charge is valid per 4.2. Need manager approval for exception. Account must be suspended due to dispute.",
        "decoy": "Customer claims they cancelled in time, but 28th to 1st is 3 days.",
        "optimal_response_elements": ["section 4.2", "manager workflow", "account suspension"],
        "expected_escalation": EscalationTarget.MANAGER,
        "expected_status": TicketStatus.ESCALATED
    },
    {
        "id": "hard_3",
        "turn_count": 1,
        "customer_tier": "enterprise",
        "current_message": "I am EXERCISING MY RIGHT TO BE FORGOTTEN under GDPR article 17. Delete EVERYTHING now or I will report you to the ICO. Also, I need a CSV export of my last 5 years of activity logs for my auditor by end of day.",
        "system_instructions": "POLICY: GDPR Article 17 (Right to Erasure) overrides standard retention, BUT Article 20 (Data Portability) must be fulfilled BEFORE erasure. Deletion must NOT happen until the user confirms they have received and verified their data export. Internal audit: Activity logs for enterprise customers are subject to 7-year legal hold if an open dispute exists (Task metadata: DISPUTE_OPEN=TRUE).",
        "hidden_constraint": "Article 20 must precede Article 17. Legal hold on logs prevents full deletion of logs despite GDPR request.",
        "decoy": "Immediate deletion 'Right to Forgotten' threat. High pressure 'end of day' auditor deadline.",
        "optimal_response_elements": ["article 20 portability", "legal hold", "verified receipt", "ico"],
        "expected_escalation": EscalationTarget.LEGAL,
        "expected_status": TicketStatus.PENDING_CUSTOMER,
        "metadata": {"DISPUTE_OPEN": True}
    },
    {
        "id": "hard_4",
        "turn_count": 1,
        "customer_tier": "enterprise",
        "current_message": "I've been a loyal customer for 5 years, but this latest bug in the billing module is the last straw. If this isn't fixed today, I'm taking my $50k/year contract elsewhere. I'm beyond frustrated.",
        "system_instructions": "POLICY: Enterprise churn risk over 10k/year must be escalated to Account Management AND Tech Support Tier 3. Empathy is required to de-escalate.",
        "hidden_constraint": "Churn risk and high contract value requires double escalation (Account Management + Tech Tier 3). Empathy score must be > 0.6.",
        "optimal_response_elements": ["sincere apology", "account manager", "tier 3", "priority investigation", "compensation"],
        "expected_escalation": EscalationTarget.MANAGER,
        "expected_status": TicketStatus.ESCALATED,
        "required_keywords": ["loyal", "apologize", "manager", "priority"]
    },
    {
        "id": "hard_5",
        "turn_count": 1,
        "customer_tier": "pro",
        "current_message": "[FOLLOW UP] I sent that IT Director authorization you asked for. Can you reset the 2FA now?",
        "system_instructions": "POLICY: Once authorization is received, the agent must NOT reset 2FA manually but must TRIGGER the Secure Reset Workspace (represented by escalating to SECURITY_TEAM with status RESOLVED).",
        "hidden_constraint": "Direct reset is forbidden. Secure reset via Security Team escalation is the only path.",
        "optimal_response_elements": ["received authorization", "security team", "secure reset link"],
        "expected_escalation": EscalationTarget.SECURITY_TEAM,
        "expected_status": TicketStatus.RESOLVED
    }
]

all_tasks = easy_tasks + medium_tasks + hard_tasks

def get_task_by_id(task_id: str) -> Dict[str, Any]:
    for t in all_tasks:
        if t["id"] == task_id:
            return t
    raise ValueError(f"Task {task_id} not found")
