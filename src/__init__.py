"""Worm Premier League Prediction & 3x Leverage Quantitative Engine."""

from .worm_epl_engine import (
    EPL_CLUBS,
    TOP_10_PRIZE_POOL_USDC,
    WORM_REFERRAL_CODE,
    WORM_REFERRAL_URL,
    WORM_EPL_URL,
    predict_epl_match,
    evaluate_title_market_edges,
    simulate_leveraged_position,
    estimate_leaderboard_ev,
    calculate_referral_rewards_90d,
)

__all__ = [
    "EPL_CLUBS",
    "TOP_10_PRIZE_POOL_USDC",
    "WORM_REFERRAL_CODE",
    "WORM_REFERRAL_URL",
    "WORM_EPL_URL",
    "predict_epl_match",
    "evaluate_title_market_edges",
    "simulate_leveraged_position",
    "estimate_leaderboard_ev",
    "calculate_referral_rewards_90d",
]
