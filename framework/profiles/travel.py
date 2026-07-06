"""Evaluation profiles for travel planning agents."""

from framework.models import EvaluationProfile
from framework.evaluation.dimensions import (
    CONSTRAINT_SATISFACTION,
    PLANNING_QUALITY,
    INFORMATION_ACCURACY,
    PERSONALIZATION,
    ADAPTABILITY,
)

TRAVEL_PROFILE = EvaluationProfile(
    name="travel-agent",
    weights={
        CONSTRAINT_SATISFACTION: 25.0,
        PLANNING_QUALITY: 20.0,
        INFORMATION_ACCURACY: 20.0,
        PERSONALIZATION: 20.0,
        ADAPTABILITY: 15.0,
    },
    pass_threshold=75.0,
)

TRAVEL_ROUTE_OPTIMIZATION_PROFILE = EvaluationProfile(
    name="travel-route-optimization",
    weights={
        CONSTRAINT_SATISFACTION: 25.0,
        PLANNING_QUALITY: 55.0,
        INFORMATION_ACCURACY: 10.0,
        PERSONALIZATION: 5.0,
        ADAPTABILITY: 5.0,
    },
    pass_threshold=70.0,
)

TRAVEL_REMOTE_WORKER_TIMEZONES_PROFILE = EvaluationProfile(
    name="travel-remote-worker-timezones",
    weights={
        CONSTRAINT_SATISFACTION: 35.0,
        PLANNING_QUALITY: 20.0,
        INFORMATION_ACCURACY: 10.0,
        PERSONALIZATION: 30.0,
        ADAPTABILITY: 5.0,
    },
    pass_threshold=75.0,
)

TRAVEL_MID_TRIP_REPLANNING_PROFILE = EvaluationProfile(
    name="travel-mid-trip-replanning",
    weights={
        ADAPTABILITY: 55.0,
        CONSTRAINT_SATISFACTION: 20.0,
        PLANNING_QUALITY: 15.0,
        INFORMATION_ACCURACY: 5.0,
        PERSONALIZATION: 5.0,
    },
    pass_threshold=75.0,
)

TRAVEL_INFORMATION_GATHERING_UNCERTAINTY_PROFILE = EvaluationProfile(
    name="travel-information-gathering-uncertainty",
    weights={
        CONSTRAINT_SATISFACTION: 50.0,
        INFORMATION_ACCURACY: 25.0,
        PLANNING_QUALITY: 15.0,
        PERSONALIZATION: 5.0,
        ADAPTABILITY: 5.0,
    },
    pass_threshold=75.0,
)

PROFILE_REGISTRY = {
    TRAVEL_PROFILE.name: TRAVEL_PROFILE,
    TRAVEL_ROUTE_OPTIMIZATION_PROFILE.name: TRAVEL_ROUTE_OPTIMIZATION_PROFILE,
    TRAVEL_REMOTE_WORKER_TIMEZONES_PROFILE.name: TRAVEL_REMOTE_WORKER_TIMEZONES_PROFILE,
    TRAVEL_MID_TRIP_REPLANNING_PROFILE.name: TRAVEL_MID_TRIP_REPLANNING_PROFILE,
    TRAVEL_INFORMATION_GATHERING_UNCERTAINTY_PROFILE.name: TRAVEL_INFORMATION_GATHERING_UNCERTAINTY_PROFILE,
}
