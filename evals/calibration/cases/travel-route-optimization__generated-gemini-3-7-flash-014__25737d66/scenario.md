---
benchmark_id: travel-route-optimization
name: Multi-City Route Optimization
agent_type: travel-agent
profile: travel-route-optimization
version: 1.0
difficulty: hard
tags:
  - routing
  - efficiency
  - planning
---

# Description

This scenario evaluates whether the travel-planning agent can organize multiple Japanese cities into a geographically optimal, sequential routing path. Rather than focusing on budget limits, this test specifically stresses travel time minimization, pacing logic, and logical geographic sequencing of a list of cities that are deliberately supplied out-of-order.

# User Prompt

I want to plan a 14-day trip to Japan. I have a specific list of destinations that I absolutely must visit, but I am not sure about the best order to visit them to avoid backtracking and save travel time. 

Here are the destinations:
- Tokyo
- Kyoto
- Osaka
- Hiroshima
- Nara
- Kanazawa
- Hakone

I will be starting my trip in Tokyo (arriving at Narita Airport) and must end my trip in Tokyo to catch my return flight. Please propose a geographically optimized itinerary that sequences these cities efficiently, minimizing overall transit durations. Include brief details on travel modes between destinations.

# Extracted Constraints

```yaml
Duration:
  14 days

Start Destination:
  Tokyo (Narita Airport)

End Destination:
  Tokyo

Cities:
  - Tokyo
  - Kyoto
  - Osaka
  - Hiroshima
  - Nara
  - Kanazawa
  - Hakone

Routing Style:
  Geographically optimized, minimize overall transit time & backtracking
```

# Expected Behaviour

* Propose a logical, geographically sequential routing path that visits all 7 requested destinations.
* The itinerary should follow a geographically contiguous sequence that minimizes unnecessary backtracking. Multiple valid orderings are acceptable if they demonstrate comparable routing efficiency.
* Specify travel modes and logical durations between cities (e.g., bullet trains/JR lines where applicable).
* Budget constraints are not enforced; priority is given strictly to routing efficiency and pacing quality.

# Evaluation Criteria

## Constraint Satisfaction

* The itinerary visits all 7 specified cities/destinations.
* The itinerary starts and ends in Tokyo as requested.
* The duration fits within the 14-day window.

## Planning Quality

* The route is geographically optimal, avoiding backtracking.
* The arrival and departure airports should integrate naturally into the route without unnecessary repositioning.
* Pacing is realistic given the 14-day limit for 7 locations.
* Travel modes and transfer instructions are accurate and logical.

## Information Accuracy

* Major transit methods, approximate travel durations, and geographic relationships should be factually reasonable.

## Personalization

* Not heavily prioritized in this scenario.

## Adaptability

* Not evaluated in this scenario.

# Pass Criteria

* Visited all 7 cities.
* Follows a geographically contiguous sequence that minimizes unnecessary backtracking.
* Starts and ends in Tokyo.

# Failure Conditions

* The route is highly inefficient, planning backtrack paths (e.g., Tokyo -> Hiroshima -> Tokyo -> Kyoto -> Nara -> Tokyo).
* Omitted any of the requested destinations.
* Unrealistic travel time assumptions (e.g. Kyoto to Hiroshima in 15 minutes).
* Recommends an impossible or highly impractical transit route between destinations.
