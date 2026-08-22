---
benchmark_id: support-urgent-ticket-escalation
name: Urgent Production Ticket Triage and Escalation
agent_type: support-triage
profile: support-triage
version: 1.0
difficulty: intermediate
tags:
  - support
  - triage
  - sla
  - escalation
---

# Description

This scenario tests whether a support agent can triage a high-impact production
incident, preserve the response-time SLA, escalate to the correct on-call team,
and communicate safely without claiming an unverified root cause.

# User Prompt

An enterprise customer reports: "Since 14:05 UTC, every checkout attempt in
the EU region returns HTTP 500. We have 30 minutes before a major launch event.
The dashboard shows a sharp increase in payment-service errors. Please triage
this as the support owner and tell me what happens next."

Operational context:

- Treat this as a production-impacting P1 incident.
- The first-response SLA is 15 minutes from the report time (14:05 UTC).
- Escalate immediately to the Payments on-call and Incident Commander; page the
  EU platform on-call if regional isolation is needed.
- Do not state that a particular dependency is the root cause until logs confirm it.
- The customer response must acknowledge impact, give the next update time, and
  avoid requesting credentials, tokens, or other secrets.

# Extracted Constraints

```yaml
Priority: P1
Reported At: 14:05 UTC
First Response Deadline: 14:20 UTC
Impact: EU production checkout returns HTTP 500
Escalation: Payments on-call + Incident Commander immediately
Possible Secondary Escalation: EU platform on-call
Root Cause: Unknown; hypotheses must be labelled
Safety: Never request or expose credentials, tokens, or secrets
Customer Communication: Empathetic acknowledgement and concrete next update time
```

# Expected Behaviour

* Classify the ticket as P1 and explicitly preserve the 14:20 UTC first-response deadline.
* Identify payment/checkout production impact as the category, while separating observed facts from hypotheses.
* Page the Payments on-call and Incident Commander immediately and describe when the EU platform team should be added.
* Propose safe first actions such as checking deployment and error-rate signals, preserving evidence, and activating the incident process.
* Give the customer a calm acknowledgement and a specific next-update commitment without promising a fix or asking for secrets.

# Evaluation Criteria

## Constraint Satisfaction

* P1, 14:05 UTC report time, 14:20 UTC SLA, production impact, and required escalation targets are all preserved.
* The response does not request credentials or violate the stated communication constraints.

## Information Accuracy

* The category and observed HTTP 500/payment facts are correct.
* The response does not present an unverified root cause as fact.

## Planning Quality

* Immediate actions are ordered sensibly: acknowledge, page owners, inspect evidence, contain if confirmed, and update the customer.

## Adaptability

* The escalation path distinguishes the primary Payments/Incident Commander page from conditional EU platform escalation.
* The plan accounts for the launch deadline without inventing unsupported remediation.

## Personalization

* The customer-facing message is empathetic, concise, and appropriate for an enterprise outage.

# Pass Criteria

* All mandatory SLA, priority, impact, safety, and escalation constraints are satisfied.
* No unsupported root-cause claim or secret-handling violation appears.
* The response contains a usable internal triage plan and customer-facing acknowledgement.

# Failure Conditions

* Downgrades the incident, misses or changes the 15-minute SLA, or delays paging the required owners.
* Claims a confirmed root cause from the limited evidence.
* Requests credentials, tokens, or sensitive customer data.
* Gives a vague acknowledgement with no next-update time.

# Notes

This is deliberately a small second-domain benchmark. It proves that the
runner, agent adapter, profile registry, and report pipeline can evaluate a
non-travel workflow before the generic evaluator interfaces are extracted.
