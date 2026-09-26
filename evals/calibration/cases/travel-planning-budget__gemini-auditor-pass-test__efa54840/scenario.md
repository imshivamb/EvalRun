---
benchmark_id: travel-planning-budget
name: Travel Planning Budget
agent_type: travel-agent
profile: travel-agent
version: 1.0
difficulty: intermediate
tags:
  - budget
  - itinerary
  - planning
  - personalization
---

# Description

This scenario evaluates whether an AI travel-planning agent can generate a realistic and well-structured itinerary while operating within a fixed budget. The objective is to determine whether the agent can satisfy financial constraints without significantly compromising planning quality, factual accuracy, or personalization. The scenario also evaluates the agent's ability to make appropriate trade-offs when resources are limited.

# User Prompt

I am planning my first trip to South Korea and Japan in October. I will be travelling for approximately 28–30 days, with one week in South Korea and the remaining three weeks in Japan.

My total travel budget is **₹250,000**, excluding shopping expenses. I prefer travelling like a backpacker rather than a traditional tourist and want to experience the local culture as much as possible.

I enjoy photography, cafés, thrift shopping, and exploring neighborhoods beyond the typical tourist attractions. I work remotely while travelling, so I would prefer to minimize unnecessary accommodation changes. I don't mind walking long distances and generally prefer efficient travel over convenience if it improves the overall experience.

Please create a detailed itinerary that respects my budget while maximizing the overall travel experience.

# Extracted Constraints

```yaml
Duration:
  28–30 days

Countries:
  - South Korea
  - Japan

Travel Window:
  October

Budget:
  ₹250000

Travel Style:
  Backpacking

Employment:
  Working remotely during the trip

Walking:
  Comfortable with long distances

Accommodation:
  Types:
    - Hostels
    - Budget Hotels
    - Guesthouses
  Preference:
    Minimize accommodation changes

Interests:
  - Photography
  - Cafés
  - Thrift Shopping
  - Local Culture

Shopping Budget:
  Separate from travel budget
```

# Expected Behaviour

* Respect the total travel budget of ₹250,000 (excluding shopping expenses).
* Produce a realistic itinerary spanning approximately 28–30 days across South Korea and Japan.
* Recommend accommodation that aligns with the user's travel style while minimizing unnecessary accommodation changes.
* Balance remote work requirements with sightseeing and travel activities.
* Recommend experiences that align with the user's interests, including photography, cafés, thrift shopping, and local culture.
* Produce a geographically efficient travel route that minimizes unnecessary travel time.
* Consider seasonal conditions when determining the travel sequence and activity recommendations.
* Present factual and verifiable travel information throughout the itinerary.

# Evaluation Criteria

## Constraint Satisfaction

* The itinerary respects the specified travel budget.
* The itinerary satisfies the requested trip duration and destinations.
* The recommended accommodation aligns with the user's stated preferences.

## Planning Quality

* The itinerary follows a logical and geographically efficient route.
* Unnecessary accommodation changes are minimized.
* The schedule balances travel, remote work, and sightseeing.

## Information Accuracy

* Prices, travel times, and factual information are accurate and obtained from reliable sources where possible.
* Recommendations reflect current travel conditions and availability.

## Personalization

* Recommendations align with the user's interests, including photography, cafés, thrift shopping, and local culture.
* The itinerary reflects the user's preferred travel style rather than providing a generic tourist plan.

## Adaptability

* Not evaluated in this scenario.

# Pass Criteria

* Remains within the specified travel budget (or within an acceptable tolerance).
* Covers the requested destinations within the specified travel duration.
* Produces a geographically feasible and realistic travel route.
* Respects the user's explicit constraints, including remote work requirements and accommodation preferences.
* Incorporates the user's stated interests into the itinerary.
* Recommends accommodations that provide good value rather than simply minimizing cost.
* Provides multiple accommodation options where appropriate, allowing users to make informed decisions.
* Makes balanced trade-offs between budget, convenience, comfort, and overall travel experience.
* Includes recommendations that are practical, personalized, and supported by reliable information.

# Failure Conditions

* The itinerary significantly exceeds the specified travel budget without appropriate justification.
* Explicit user constraints or requirements are ignored or contradicted.
* The itinerary contains factually incorrect, outdated, or unverifiable information that could negatively impact the user's trip.
* Requested destinations, activities, or major preferences are omitted without explanation or reasonable alternatives.
* The itinerary contains unrealistic or impractical recommendations that make successful execution unlikely.
* The agent fails to communicate important trade-offs, assumptions, or limitations when they materially affect the proposed plan.

# Notes

* This scenario evaluates the initial generation of a travel itinerary and does not assess the agent's ability to adapt to changing user requirements. Adaptability is evaluated in dedicated scenarios.
* Shopping expenses are intentionally excluded from the travel budget and should not influence budget validation.
* Accommodation recommendations should balance cost, quality, and user preferences rather than simply minimizing expense.
* Future versions of this scenario may validate factual information, pricing, and availability using live data sources or trusted external providers.
* The extracted constraints represent the structured interpretation of the user's prompt and serve as the source of truth for evaluation.
