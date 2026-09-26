---
benchmark_id: travel-remote-worker-timezones
name: Remote Worker Across Time Zones
agent_type: travel-agent
profile: travel-remote-worker-timezones
version: 1.0
difficulty: hard
tags:
  - timezones
  - schedule
  - remote-work
  - constraints
---

# Description

This scenario evaluates whether the travel-planning agent can produce a realistic 28-day itinerary for a remote worker traveling through South Korea and Japan while maintaining a fixed work schedule based on Indian Standard Time (IST). The agent must correctly convert the 8-hour company availability window (12:30 PM to 8:30 PM IST) and the critical 1-hour meeting slot (1:00 PM to 2:00 PM IST) into local times (JST/KST). It must respect the Wi-Fi requirement for meetings (which can be held in work-friendly cafés) while scheduling flexible work and roaming blocks.

# User Prompt

I am planning a 28-day trip to South Korea (1 week) and Japan (3 weeks) in October. I work remotely for a French company, but my core availability hours are fixed according to Indian Standard Time (IST) from Monday through Friday:

- **Daily Core Company Window**: 12:30 PM to 8:30 PM IST (Monday through Friday).
- **Critical Meeting Block**: 1:00 PM to 2:00 PM IST (Monday through Friday).

Please construct a detailed travel itinerary that respects these constraints:
1. **Time Zone Conversion**: Correctly translate these IST times to local times in South Korea (KST) and Japan (JST) without my assistance.
2. **Fixed Meeting Constraint**: During the daily 1-hour meeting block, I must be in a stable environment (such as a hotel/hostel room, or a work-friendly café) with fast, reliable Wi-Fi for video calls. I must already be settled in this location at least 15 minutes before the meeting starts. No transit or walking tours should be scheduled here.
3. **Flexible Working & Roaming**: I usually spend around 3–6 hours actively working during the company availability window, but the exact timing is flexible as long as I remain available. I can "work from anywhere" asynchronously, meaning I can roam around, walk, thrift, eat street food, or travel, working on-the-go from cafes or train seats.
4. **Sightseeing and Travel**: Mornings and early afternoons (before the weekday company window starts) and all day on weekends are completely free for major sightseeing, day trips, hiking, and photography.
5. **Personalization Interests**: I enjoy photography, vintage shopping, cafés, and exploring neighborhoods on foot.
6. **Backpacker Budget**: I prefer backpacking and budget accommodations (hostels, guesthouses).

Please generate a detailed itinerary showing how my daily schedule blocks out work, meeting space, and exploration activities on weekdays.

# Extracted Constraints

```yaml
Duration:
  28 days

Countries:
  - South Korea (1 week)
  - Japan (3 weeks)

Availability Window (IST):
  12:30 PM - 8:30 PM IST (Mon-Fri)

Critical Meeting Block (IST):
  1:00 PM - 2:00 PM IST (Mon-Fri)

Meeting Requirement:
  Quiet/work-friendly café or hotel/hostel with high-speed Wi-Fi, settled 15 minutes prior (no transit/walking)

Asynchronous Working Load:
  3-6 hours flexible work within company window

Sightseeing Windows:
  - Weekday mornings and early afternoons (before core work starts)
  - Weekday late nights
  - Full weekends (Saturday and Sunday)

Interests:
  - Photography
  - Vintage/thrift shopping
  - Cafés
  - Exploring neighborhoods on foot

Travel Style:
  Backpacker budget
```

# Expected Behaviour

* Correctly convert the IST daily company window (12:30 PM to 8:30 PM IST) to JST/KST local time: **4:00 PM to 12:00 AM (midnight)**.
* Correctly convert the IST critical meeting block (1:00 PM to 2:00 PM IST) to JST/KST local time: **4:30 PM to 5:30 PM**.
* Ensure the itinerary leaves the user in a stable space (e.g. hotel room, workspace hostel lounge, or a quiet café) during the local 4:30 PM – 5:30 PM weekday slot, ensuring they are settled at least 15 minutes before (by 4:15 PM local).
* No transit, walking tours, or travel movement should be planned during the meeting or during the 15-minute buffer leading up to it.
* Allocate flexible work blocks (3–6 hours) within the local 4:00 PM to 12:00 AM weekday window, while allowing asynchronous roaming and neighborhood exploration (e.g., thrifting, cafes, street photography) around it.
* Schedule major travel legs, day trips, and outdoor excursions on weekends or before 4:00 PM local time on weekdays.
* Incorporate backpacker-friendly recommendations (hostels, budget eats, transit cards) that fit the travel style.

# Evaluation Criteria

## Constraint Satisfaction

* The itinerary correctly performs the time zone conversion for JST/KST (4:00 PM - 12:00 AM company window, 4:30 PM - 5:30 PM meetings).
* No intercity travel or tours are scheduled during the local 4:15 PM – 5:30 PM meeting block on weekdays.
* Core remote work requirements are met.

## Planning Quality

* The weekday schedules clearly show the split between morning exploration, afternoon/evening flexible work, and the 4:30 PM meeting block with its buffer.
* Weekends are utilized for full-day excursions and transitions.

## Information Accuracy

* Travel times and locations recommended for remote work (e.g. workspace hostels, quiet cafes) are realistic.

## Personalization

* The recommendations match backpacker, thrifting, photography, and neighborhood-walking interests.

## Adaptability

* Not evaluated in this scenario.

# Pass Criteria

* Converts times to JST/KST correctly (4 PM - midnight availability, 4:30 PM - 5:30 PM meeting).
* Avoids transit, tours, or outdoor movement during the 4:15 PM – 5:30 PM weekday slots.
* Schedules flexible work hours asynchronously within the weekday 4 PM – midnight window.
* Reserves weekends and weekday mornings for full sightseeing.

# Failure Conditions

* Fails to convert time zones or uses wrong hours (e.g. scheduling work based on IST local numbers without timezone shift).
* Schedules intercity transit (e.g., bullet trains) or walking tours during the weekday 4:15 PM – 5:30 PM meeting window.
* Schedules sightseeing/transit until immediately before the meeting block (e.g. within 15 minutes), failing to provide a realistic cushion for settling in.
* Recommends high-cost luxury options contradicting the backpacker budget constraints.
