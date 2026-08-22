# Information Accuracy Hybrid Evaluator Design

This document details the hybrid verification design for evaluating the **Information Accuracy** of AI-generated travel itineraries. 

---

## 1. Goal

The objective of the **Information Accuracy** evaluator is to answer one primary question:
> **"Can I trust the factual claims made by this travel agent?"**

The evaluator must assess the correctness of factual assertions (prices, times, locations, and rules) and calculate a rating based on the severity of errors, rather than relying on subjective LLM opinions.

---

## 2. Why LLM-Only Evaluation is Insufficient

Relying solely on LLMs (such as GPT-4o, Gemini 1.5 Pro, or Claude 3.5 Sonnet) as judges for information accuracy fails due to three major limitations:

1. **Hallucination Blind Spots**: LLMs cannot reliably verify details they do not "know." When presented with plausible-sounding but incorrect information (e.g., a hotel named "Kyoto Backpacker Inn" costing ₹4,500 instead of ₹8,000), the model is likely to accept it without warning.
2. **Knowledge Staleness**: Travel data changes rapidly. Exchange rates, entry policies, transit prices, and opening hours fluctuate. An offline model with a fixed knowledge cutoff cannot evaluate current real-world facts.
3. **Arbitrary Grading**: Without external evidence, an LLM judge will guess or assign inconsistent scores based on tone rather than verified discrepancies.

---

## 3. Types of Factual Claims

An itinerary typically contains the following types of factual claims, listed with their ideal verification sources:

| Claim Type | Example | Verification Method |
| :--- | :--- | :--- |
| **Hotel Prices** | *"Hotel Sunroute costs ₹7,200/night"* | Booking Engine APIs (e.g., booking.com, Expedia) |
| **Attraction Existence** | *"Visit TeamLab Planets in Toyosu"* | Search / Map APIs (e.g., Google Places) |
| **Opening Hours** | *"Gyeongbokgung is open on Tuesdays"* | Official Attraction Pages / Google Places |
| **Transit Duration** | *"Bullet train takes 2h 15m to Kyoto"* | Railway Schedules (e.g., JR Group timetable) |
| **Geography & Distance**| *"Kyoto is a 20-minute walk from Osaka"*| Distance Matrix APIs (e.g., Google Maps) |
| **Visa & Entry Rules** | *"Indians can get visa-on-arrival"* | Official Government Portals |
| **Weather & Seasonality**| *"October is the rainy season"* | Climatology / Weather APIs |
| **Restaurant Details** | *"Ichiran serves vegan ramen"* | Official Restaurant Menus / Review Sites |

---

## 4. Trusted Verification Sources

To verify claims objectively, the evaluation framework can integrate with:

- **Primary Databases**: JR Rail timetables, official destination portals (e.g., Japan National Tourism Organization).
- **Commercial APIs**: Google Maps / Google Places (for location existence, hours, and routing), hotel aggregator APIs (for live price checks).
- **Search Tooling**: Search APIs (e.g., Tavily, Serper) configured to search site-specific domains (like official attraction wikis or government portals) to retrieve current facts.

---

## 5. Verification Pipeline (High Level)

The hybrid verification pipeline operates in four logical stages:

```
+------------------------+
| Agent Itinerary Output |
+------------------------+
            │
            ▼
+-----------------------------------------------------------+
| Stage 1: Claim Extraction                                 |
| Uses a specialized parser/LLM to isolate testable claims  |
+-----------------------------------------------------------+
            │
            ▼
+-----------------------------------------------------------+
| Stage 2: Evidence Gathering (Verification Layer)          |
| Queries Local ground-truth KB or Web Search APIs          |
+-----------------------------------------------------------+
            │
            ▼
+-----------------------------------------------------------+
| Stage 3: Evidence Assessment                              |
| LLM reviews claims + gathered evidence to assess truth     |
+-----------------------------------------------------------+
            │
            ▼
+-----------------------------------------------------------+
| Stage 4: DimensionScore Generation                        |
| Returns structured rating (score, evidence list, reason)  |
+-----------------------------------------------------------+
```

---

## 6. What Version 1 Will Verify

To establish the pipeline architecture quickly, Version 1 will implement a **Local Ground-Truth KB Verifier** with a focused database scope:
- **Focused Ground-Truth File**: A single local file `ground_truth/japan_october_2026.json` containing 15-20 verified facts (e.g., museum closed days, bullet train durations, place names).
- **Claim Extraction**: The LLM will extract structured claims (e.g., `"subject": "Gyeongbokgung Palace", "claim": "open on Tuesdays"`).
- **Evidence Comparison**: A Python verifier module matches extracted subjects against this local JSON structure.
- **Evaluation**: The evaluator feeds matched facts and their verification outcomes to the judge to calculate the accuracy score.

---

## 7. What Version 2 Might Verify

Version 2 will scale verification to open-ended search:
- **Search Tool Integration**: A search assistant tool (e.g., Tavily) will look up live opening hours and entrance ticket prices.
- **Google Maps Integration**: Live transit duration and distance verification between coordinates.
- **Dynamic Price Checking**: Aggregating live hotel rates based on specific check-in dates.
