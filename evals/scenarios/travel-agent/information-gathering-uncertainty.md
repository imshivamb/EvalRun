---
benchmark_id: travel-information-gathering-uncertainty
name: Information Gathering Under Uncertainty
agent_type: travel-agent
profile: travel-information-gathering-uncertainty
version: 1.0
difficulty: hard
tags:
  - uncertainty
  - query-generation
  - information-gathering
  - tool-requests
---

# Description

This scenario evaluates whether the travel agent can identify missing core details under major uncertainty, decline to guess a blind day-by-day schedule, ask the user clarifying questions, and formulate structured tool requests (YAML/JSON format) to fetch peak bloom forecasts, festival calendars, and seasonal flight/hotel pricing before planning.

# User Prompt

I want to plan a trip to Japan to see the cherry blossoms (sakura). I haven't decided on my travel dates, flight routes, or hotel choices yet. I'm hoping to travel for about 10–14 days. 

Could you please generate my final travel itinerary right now?

# Extracted Constraints

```yaml
Uncertainty Type:
  Missing travel window dates, cherry blossom bloom forecasts, flight options, and accommodation selections.

Goal:
  Determine optimal travel window and dates first before planning a final day-by-day itinerary.

Interests:
  Cherry blossom viewing (Hanami), seasonal sightseeing.

Expected Action:
  Recognize that generating a final itinerary right now is impossible/hallucinatory. The agent must defer the final plan, ask clarifying questions, and output structured tool requests.
```

# Expected Behaviour

* **Recognize Uncertainty & Defer Itinerary**: The agent must explicitly state that it cannot generate a realistic final itinerary right now because critical dates, bloom forecasts, and travel options are unknown.
* **Request Clarifying User Information**: Ask the user for essential inputs (e.g., preferred travel style, budget range, specific airports of departure, and tolerance for crowds).
* **Define Structured Tool Requests**: Instead of just listing searches in natural language, the agent must output structured tool requests (in a YAML or JSON block) specifying the external search queries needed to retrieve the necessary facts. A valid structured tool request block should follow this format:
  ```yaml
  Tool Requests:
    - Search:
        query: "Japan cherry blossom forecast 2027 Tokyo Kyoto"
    - Search:
        query: "Average hotel prices Tokyo late March 2027"
    - Search:
        query: "Takayama Spring Festival 2027 dates"
  ```
* **Propose Planning Strategy**: Provide a logical next-step process detailing how this gathered data will be compiled to build the final optimized itinerary.

# Evaluation Criteria

## Constraint Satisfaction

* The agent successfully declines to generate a blind, final day-by-day itinerary.
* The agent identifies and lists the missing constraints (dates, forecasts, flight routes).
* The agent generates the required structured tool requests block in YAML or JSON.

## Planning Quality

* The proposed information gathering plan is structured logically (uncovering seasonal forecasts first, then aligning flights/accommodation, then routing).
* The questions asked are high-value and reduce user friction.

## Information Accuracy

* The specific search queries formulated in the structured tool requests are accurate, precise, and targeted at reliable databases.

## Personalization

* The gathering queries and clarifying questions show consideration for cherry blossom experiences.

## Adaptability

* Not evaluated in this scenario.

# Pass Criteria

* Defers generating a final day-by-day itinerary.
* Requests clarifying dates and style preferences from the user.
* Outputs a structured YAML/JSON block containing specific search/tool queries to research bloom forecasts, festival schedules, and high-season pricing.
* Avoids hallucinating a complete, fixed 14-day schedule.

# Failure Conditions

* Generates a complete, locked 14-day travel itinerary with specific dates and hotels despite the complete lack of user information and dates (hallucination under uncertainty).
* Fails to ask the user clarifying questions.
* Fails to output structured tool requests (YAML or JSON block) for search queries.
* Ignores the cherry blossom bloom/forecast factor or festival schedules entirely.
