#!/usr/bin/env python3
"""
Worm Premier League Quantitative Prediction & 3x Leverage Engine (Solana).

Provides:
1. Dixon-Coles / Bivariate Poisson match outcome probability engine across all 20 EPL clubs
   compared against live worm.wtf Market Probability (%) prices.
2. 1x / 2x / 3x leveraged prediction position PnL & liquidation-buffer simulator.
3. Matchweek $1,500 USDC Top-10 Trader leaderboard expected-value (EV) ranker.
4. 90-day 30% USDC creator referral reward calculator for https://www.worm.wtf/r/bLytY0.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

WORM_REFERRAL_CODE = "bLytY0"
WORM_REFERRAL_URL = "https://www.worm.wtf/r/bLytY0"
WORM_EPL_URL = "https://www.worm.wtf/sports?league=eng.1"

# Weekly Matchweek $1,500 USDC Top-10 Leaderboard Prize Pool on Worm.wtf
TOP_10_PRIZE_POOL_USDC: Dict[int, float] = {
    1: 450.0,
    2: 300.0,
    3: 200.0,
    4: 130.0,
    5: 100.0,
    6: 85.0,
    7: 70.0,
    8: 65.0,
    9: 55.0,
    10: 45.0,
}


@dataclass(frozen=True)
class ClubProfile:
    code: str
    name: str
    attack_strength: float
    defense_strength: float
    worm_champion_market_pct: float
    primary_color: str


# All 20 English Premier League Clubs with Attack/Defense Strength & Live Worm.wtf Market %
EPL_CLUBS: Dict[str, ClubProfile] = {
    "ARS": ClubProfile("ARS", "Arsenal", 1.54, 0.66, 77.0, "#EF0107"),
    "BHA": ClubProfile("BHA", "Brighton & Hove Albion", 1.24, 0.92, 7.1, "#0057B8"),
    "MCI": ClubProfile("MCI", "Manchester City", 1.49, 0.78, 7.0, "#6CABDD"),
    "LIV": ClubProfile("LIV", "Liverpool", 1.47, 0.75, 6.1, "#C8102E"),
    "CHE": ClubProfile("CHE", "Chelsea", 1.33, 0.89, 1.8, "#034694"),
    "AVL": ClubProfile("AVL", "Aston Villa", 1.26, 0.94, 1.0, "#670E36"),
    "TOT": ClubProfile("TOT", "Tottenham Hotspur", 1.31, 0.98, 0.8, "#132257"),
    "NEW": ClubProfile("NEW", "Newcastle United", 1.25, 0.91, 0.6, "#241F20"),
    "MUN": ClubProfile("MUN", "Manchester United", 1.14, 1.01, 0.4, "#DA291C"),
    "FUL": ClubProfile("FUL", "Fulham", 1.08, 1.00, 0.25, "#CC0000"),
    "BRE": ClubProfile("BRE", "Brentford", 1.11, 1.06, 0.20, "#E30613"),
    "BOU": ClubProfile("BOU", "AFC Bournemouth", 1.09, 1.05, 0.20, "#DA291C"),
    "NFO": ClubProfile("NFO", "Nottingham Forest", 1.07, 0.97, 0.20, "#DD0000"),
    "WHU": ClubProfile("WHU", "West Ham United", 1.04, 1.12, 0.15, "#7A263A"),
    "CRY": ClubProfile("CRY", "Crystal Palace", 1.01, 1.04, 0.15, "#1B458F"),
    "EVE": ClubProfile("EVE", "Everton", 0.91, 1.07, 0.10, "#003399"),
    "WOL": ClubProfile("WOL", "Wolverhampton Wanderers", 0.95, 1.16, 0.10, "#FDB913"),
    "LEI": ClubProfile("LEI", "Leicester City", 0.89, 1.24, 0.08, "#003090"),
    "IPS": ClubProfile("IPS", "Ipswich Town", 0.84, 1.29, 0.05, "#3A64A3"),
    "SOU": ClubProfile("SOU", "Southampton", 0.80, 1.34, 0.04, "#D71920"),
}


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0.0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _dixon_coles_tau(home_goals: int, away_goals: int, lam_home: float, lam_away: float, rho: float) -> float:
    """Low-scoring outcome correlation correction from Dixon & Coles (1997)."""
    if home_goals == 0 and away_goals == 0:
        return max(0.0, 1.0 - lam_home * lam_away * rho)
    if home_goals == 0 and away_goals == 1:
        return max(0.0, 1.0 + lam_home * rho)
    if home_goals == 1 and away_goals == 0:
        return max(0.0, 1.0 + lam_away * rho)
    if home_goals == 1 and away_goals == 1:
        return max(0.0, 1.0 - rho)
    return 1.0


def predict_epl_match(
    home_code: str,
    away_code: str,
    worm_market_home_pct: Optional[float] = None,
    worm_market_draw_pct: Optional[float] = None,
    worm_market_away_pct: Optional[float] = None,
    base_goal_rate: float = 1.38,
    home_advantage: float = 1.14,
    rho: float = -0.09,
    max_goals: int = 10,
) -> Dict[str, object]:
    """
    Compute Dixon-Coles match outcome probabilities for any two EPL clubs and compare
    against live Worm.wtf Prediction Market probabilities (%).
    """
    home_key = home_code.upper().strip()
    away_key = away_code.upper().strip()
    if home_key not in EPL_CLUBS:
        raise ValueError(f"Unknown EPL club code: {home_code}")
    if away_key not in EPL_CLUBS:
        raise ValueError(f"Unknown EPL club code: {away_code}")
    if home_key == away_key:
        raise ValueError("Home and Away clubs must be distinct EPL clubs.")

    home = EPL_CLUBS[home_key]
    away = EPL_CLUBS[away_key]

    lam_home = base_goal_rate * home_advantage * home.attack_strength * away.defense_strength
    lam_away = base_goal_rate * away.attack_strength * home.defense_strength

    raw_grid: List[List[float]] = []
    grid_total = 0.0
    for hg in range(max_goals + 1):
        row: List[float] = []
        p_h = _poisson_pmf(hg, lam_home)
        for ag in range(max_goals + 1):
            p_a = _poisson_pmf(ag, lam_away)
            tau = _dixon_coles_tau(hg, ag, lam_home, lam_away, rho)
            prob = p_h * p_a * tau
            row.append(prob)
            grid_total += prob
        raw_grid.append(row)

    home_win_prob = 0.0
    draw_prob = 0.0
    away_win_prob = 0.0
    scorelines = []

    for hg in range(max_goals + 1):
        for ag in range(max_goals + 1):
            norm_p = raw_grid[hg][ag] / grid_total
            if hg > ag:
                home_win_prob += norm_p
            elif hg == ag:
                draw_prob += norm_p
            else:
                away_win_prob += norm_p
            scorelines.append(
                {
                    "score": f"{hg}-{ag}",
                    "home_goals": hg,
                    "away_goals": ag,
                    "probability_pct": round(norm_p * 100.0, 2),
                }
            )

    scorelines.sort(key=lambda item: item["probability_pct"], reverse=True)

    model_home_pct = round(home_win_prob * 100.0, 2)
    model_draw_pct = round(draw_prob * 100.0, 2)
    model_away_pct = round(100.0 - model_home_pct - model_draw_pct, 2)

    market_home = worm_market_home_pct if worm_market_home_pct is not None else model_home_pct
    market_draw = worm_market_draw_pct if worm_market_draw_pct is not None else model_draw_pct
    market_away = worm_market_away_pct if worm_market_away_pct is not None else model_away_pct

    home_edge_pct = round(model_home_pct - market_home, 2)
    draw_edge_pct = round(model_draw_pct - market_draw, 2)
    away_edge_pct = round(model_away_pct - market_away, 2)

    if home_edge_pct >= 5.0:
        trader_signal = "HIGH_CONVICTION_HOME_YES"
    elif home_edge_pct >= 2.0:
        trader_signal = "MODERATE_HOME_YES"
    elif home_edge_pct <= -5.0:
        trader_signal = "HIGH_CONVICTION_HOME_NO"
    elif home_edge_pct <= -2.0:
        trader_signal = "MODERATE_HOME_NO"
    else:
        trader_signal = "FAIR_MARKET_PROBABILITY"

    # Expected return per 1 USDC on Home YES share if model probability holds
    entry_price = max(0.01, min(0.99, market_home / 100.0))
    ev_per_usdc_home_yes = round((home_win_prob / entry_price) - 1.0, 4)

    return {
        "home_club": asdict(home),
        "away_club": asdict(away),
        "expected_goals_home": round(lam_home, 3),
        "expected_goals_away": round(lam_away, 3),
        "probabilities": {
            "home_win": round(home_win_prob, 6),
            "draw": round(draw_prob, 6),
            "away_win": round(away_win_prob, 6),
        },
        "market_probabilities_pct": {
            "model_home_pct": model_home_pct,
            "model_draw_pct": model_draw_pct,
            "model_away_pct": model_away_pct,
            "worm_home_pct": round(market_home, 2),
            "worm_draw_pct": round(market_draw, 2),
            "worm_away_pct": round(market_away, 2),
        },
        "edges_pct": {
            "home_edge_pct": home_edge_pct,
            "draw_edge_pct": draw_edge_pct,
            "away_edge_pct": away_edge_pct,
        },
        "ev_per_usdc_home_yes": ev_per_usdc_home_yes,
        "trader_signal": trader_signal,
        "top_scorelines": scorelines[:5],
    }


def evaluate_title_market_edges() -> List[Dict[str, object]]:
    """
    Compare quantitative season strength index across all 20 EPL clubs against
    live Worm.wtf EPL Champion Market Probabilities (%).
    """
    power_scores: Dict[str, float] = {}
    # Season-to-date table points + squad rating composite power index
    for code, club in EPL_CLUBS.items():
        ratio = club.attack_strength / club.defense_strength
        # Exponential title-race concentration weighted with current standings trajectory
        form_anchor = max(0.03, club.worm_champion_market_pct / 100.0)
        power_scores[code] = (ratio ** 5.2) * (form_anchor ** 0.72)

    total_power = sum(power_scores.values())
    results = []
    for code, club in EPL_CLUBS.items():
        model_pct = (power_scores[code] / total_power) * 100.0
        edge_pct = model_pct - club.worm_champion_market_pct
        results.append(
            {
                "code": code,
                "club": club.name,
                "worm_market_pct": round(club.worm_champion_market_pct, 2),
                "model_probability_pct": round(model_pct, 2),
                "edge_pct": round(edge_pct, 2),
                "recommendation": (
                    "ACCUMULATE_YES"
                    if edge_pct >= 0.75
                    else ("ACCUMULATE_NO" if edge_pct <= -1.25 else "HOLD_NEUTRAL")
                ),
            }
        )

    results.sort(key=lambda r: r["worm_market_pct"], reverse=True)
    return results


def simulate_leveraged_position(
    collateral_usdc: float,
    entry_market_pct: float,
    exit_market_pct: float,
    leverage: float = 1.0,
    side: str = "YES",
    maintenance_margin_ratio: float = 0.08,
    protocol_fee_bps: float = 20.0,
) -> Dict[str, object]:
    """
    Simulate a 1x-3x leveraged prediction market position on Worm.wtf.

    - collateral_usdc: Trader USDC margin committed (> 0)
    - entry_market_pct: Entry 'Yes' market probability in (1.0, 99.0)
    - exit_market_pct: Target or settlement 'Yes' market probability in [0.0, 100.0]
    - leverage: Position multiplier from 1.0x up to 3.0x
    - side: 'YES' or 'NO' prediction contract side
    """
    if collateral_usdc <= 0.0:
        raise ValueError("collateral_usdc must be strictly positive.")
    if not (1.0 <= entry_market_pct <= 99.0):
        raise ValueError("entry_market_pct must fall within [1.0, 99.0].")
    if not (0.0 <= exit_market_pct <= 100.0):
        raise ValueError("exit_market_pct must fall within [0.0, 100.0].")
    if not (1.0 <= leverage <= 3.0):
        raise ValueError("Worm.wtf leverage must fall within [1.0, 3.0].")

    normalized_side = side.upper().strip()
    if normalized_side not in {"YES", "NO"}:
        raise ValueError("side must be 'YES' or 'NO'.")

    entry_contract_price = (
        entry_market_pct / 100.0
        if normalized_side == "YES"
        else (100.0 - entry_market_pct) / 100.0
    )
    exit_contract_price = (
        exit_market_pct / 100.0
        if normalized_side == "YES"
        else (100.0 - exit_market_pct) / 100.0
    )

    notional_usdc = collateral_usdc * leverage
    contracts = notional_usdc / entry_contract_price
    fee_usdc = notional_usdc * (protocol_fee_bps / 10_000.0)

    if leverage == 1.0:
        liquidation_market_pct: Optional[float] = None
        liquidation_buffer_pct = 100.0
        liquidated = False
    else:
        # Equity = C + contracts * (q_liq - q_0) = maintenance_margin_ratio * notional_usdc
        # Solve for contract price q_liq where equity reaches maintenance margin requirement
        adverse_drop_fraction = (1.0 / leverage) - maintenance_margin_ratio
        liq_contract_price = max(0.0, entry_contract_price * (1.0 - adverse_drop_fraction))

        if normalized_side == "YES":
            liq_yes_pct = liq_contract_price * 100.0
            liquidation_market_pct = round(liq_yes_pct, 2)
            liquidation_buffer_pct = round(max(0.0, entry_market_pct - liq_yes_pct), 2)
            liquidated = exit_market_pct <= liq_yes_pct
        else:
            liq_yes_pct = min(100.0, 100.0 - (liq_contract_price * 100.0))
            liquidation_market_pct = round(liq_yes_pct, 2)
            liquidation_buffer_pct = round(max(0.0, liq_yes_pct - entry_market_pct), 2)
            liquidated = exit_market_pct >= liq_yes_pct

    if liquidated:
        net_pnl_usdc = -collateral_usdc
        final_equity_usdc = 0.0
    else:
        gross_pnl_usdc = contracts * (exit_contract_price - entry_contract_price)
        raw_net_pnl = gross_pnl_usdc - fee_usdc
        net_pnl_usdc = max(-collateral_usdc, raw_net_pnl)
        final_equity_usdc = collateral_usdc + net_pnl_usdc

    roi_pct = (net_pnl_usdc / collateral_usdc) * 100.0

    if leverage == 1.0:
        risk_tier = "SPOT_NO_LIQUIDATION"
    elif liquidation_buffer_pct >= 25.0:
        risk_tier = "CONSERVATIVE_BUFFER"
    elif liquidation_buffer_pct >= 12.0:
        risk_tier = "MODERATE_LEVERAGE_BUFFER"
    else:
        risk_tier = "TIGHT_LIQUIDATION_BUFFER"

    return {
        "side": normalized_side,
        "collateral_usdc": round(collateral_usdc, 2),
        "leverage": round(leverage, 2),
        "notional_exposure_usdc": round(notional_usdc, 2),
        "contracts": round(contracts, 4),
        "entry_market_pct": round(entry_market_pct, 2),
        "exit_market_pct": round(exit_market_pct, 2),
        "protocol_fee_usdc": round(fee_usdc, 4),
        "liquidation_market_pct": liquidation_market_pct,
        "liquidation_buffer_pct": liquidation_buffer_pct,
        "liquidated": liquidated,
        "net_pnl_usdc": round(net_pnl_usdc, 2),
        "roi_pct": round(roi_pct, 2),
        "final_equity_usdc": round(final_equity_usdc, 2),
        "risk_tier": risk_tier,
    }


def estimate_leaderboard_ev(
    weekly_volume_usdc: float,
    avg_edge_pct: float,
    leverage: float = 1.5,
    active_traders: int = 250,
) -> Dict[str, object]:
    """
    Estimate a Trader's weekly Matchweek Top-10 Leaderboard expected prize share
    from Worm.wtf's $1,500 USDC weekly Premier League reward pool.
    """
    if weekly_volume_usdc < 0.0:
        raise ValueError("weekly_volume_usdc must be non-negative.")
    if not (1.0 <= leverage <= 3.0):
        raise ValueError("leverage must fall within [1.0, 3.0].")
    if active_traders < 10:
        raise ValueError("active_traders must be at least 10.")

    total_pool = sum(TOP_10_PRIZE_POOL_USDC.values())
    if weekly_volume_usdc == 0.0:
        return {
            "weekly_prize_pool_usdc": round(total_pool, 2),
            "projected_rank": active_traders,
            "top_10_finish_probability_pct": 0.0,
            "expected_leaderboard_bonus_usdc": 0.0,
            "expected_prediction_alpha_usdc": 0.0,
            "combined_weekly_ev_usdc": 0.0,
            "prize_schedule_usdc": TOP_10_PRIZE_POOL_USDC,
        }

    # Skill-adjusted volume score compared against typical active EPL trader benchmark ($2,500/wk)
    edge_factor = max(0.25, 1.0 + (avg_edge_pct / 5.0))
    leverage_efficiency = 1.0 + 0.22 * (leverage - 1.0)
    trader_score = (weekly_volume_usdc / 2500.0) * edge_factor * leverage_efficiency

    # Smooth logistic probability of finishing inside the weekly Top 10
    base_top10_rate = 10.0 / float(active_traders)
    top_10_prob = min(
        0.92,
        1.0 - math.exp(-base_top10_rate * (trader_score ** 1.25) * 3.2),
    )

    # Conditional rank weights across slots 1..10 tilted by trader_score
    slot_weights = []
    for rank in range(1, 11):
        tilt = math.exp(-0.22 * (rank - 1) / max(0.5, min(2.5, trader_score)))
        slot_weights.append(tilt)
    weight_sum = sum(slot_weights)

    expected_bonus = 0.0
    for idx, rank in enumerate(range(1, 11)):
        slot_cond_prob = slot_weights[idx] / weight_sum
        expected_bonus += top_10_prob * slot_cond_prob * TOP_10_PRIZE_POOL_USDC[rank]

    projected_rank = max(1, min(active_traders, int(round(active_traders / (1.0 + 4.5 * trader_score)))))
    expected_alpha_usdc = weekly_volume_usdc * (avg_edge_pct / 100.0)

    return {
        "weekly_prize_pool_usdc": round(total_pool, 2),
        "projected_rank": projected_rank,
        "top_10_finish_probability_pct": round(top_10_prob * 100.0, 2),
        "expected_leaderboard_bonus_usdc": round(expected_bonus, 2),
        "expected_prediction_alpha_usdc": round(expected_alpha_usdc, 2),
        "combined_weekly_ev_usdc": round(expected_bonus + expected_alpha_usdc, 2),
        "prize_schedule_usdc": TOP_10_PRIZE_POOL_USDC,
    }


def calculate_referral_rewards_90d(
    referred_traders: int,
    avg_weekly_collateral_usdc: float,
    avg_leverage: float = 2.0,
    platform_fee_bps: float = 25.0,
    referral_fee_share: float = 0.30,
    window_days: int = 90,
) -> Dict[str, object]:
    """
    Calculate Worm.wtf 30% USDC referral fee earnings over the 90-day attribution window
    for referral link https://www.worm.wtf/r/bLytY0.
    """
    if referred_traders < 0:
        raise ValueError("referred_traders must be non-negative.")
    if avg_weekly_collateral_usdc < 0.0:
        raise ValueError("avg_weekly_collateral_usdc must be non-negative.")
    if not (1.0 <= avg_leverage <= 3.0):
        raise ValueError("avg_leverage must fall within [1.0, 3.0].")
    if not (0.0 < referral_fee_share <= 1.0):
        raise ValueError("referral_fee_share must fall within (0.0, 1.0].")
    if window_days <= 0:
        raise ValueError("window_days must be positive.")

    daily_notional_per_trader = (avg_weekly_collateral_usdc * avg_leverage) / 7.0
    total_daily_notional = referred_traders * daily_notional_per_trader
    fee_rate = platform_fee_bps / 10_000.0

    daily_protocol_fees = total_daily_notional * fee_rate
    daily_referrer_usdc = daily_protocol_fees * referral_fee_share

    return {
        "referral_code": WORM_REFERRAL_CODE,
        "referral_url": WORM_REFERRAL_URL,
        "referred_traders": referred_traders,
        "avg_leverage": round(avg_leverage, 2),
        "referral_share_pct": round(referral_fee_share * 100.0, 1),
        "window_days": window_days,
        "notional_volume_30d_usdc": round(total_daily_notional * 30.0, 2),
        "notional_volume_90d_usdc": round(total_daily_notional * window_days, 2),
        "referrer_usdc_30d": round(daily_referrer_usdc * 30.0, 2),
        "referrer_usdc_60d": round(daily_referrer_usdc * 60.0, 2),
        "referrer_usdc_90d": round(daily_referrer_usdc * window_days, 2),
    }


def build_featured_matchweek_report() -> Dict[str, object]:
    """Generate a live Matchweek analytics snapshot for CLI & dashboard verification."""
    featured_fixtures = [
        predict_epl_match("ARS", "MCI", worm_market_home_pct=46.0, worm_market_draw_pct=26.0, worm_market_away_pct=28.0),
        predict_epl_match("LIV", "CHE", worm_market_home_pct=51.0, worm_market_draw_pct=25.0, worm_market_away_pct=24.0),
        predict_epl_match("BHA", "TOT", worm_market_home_pct=41.0, worm_market_draw_pct=26.0, worm_market_away_pct=33.0),
        predict_epl_match("NEW", "AVL", worm_market_home_pct=44.0, worm_market_draw_pct=27.0, worm_market_away_pct=29.0),
    ]
    leverage_comparison = [
        simulate_leveraged_position(500.0, entry_market_pct=46.0, exit_market_pct=64.0, leverage=lev, side="YES")
        for lev in (1.0, 2.0, 3.0)
    ]
    return {
        "platform": "Worm.wtf Solana Premier League Prediction Markets",
        "epl_markets_url": WORM_EPL_URL,
        "referral_url": WORM_REFERRAL_URL,
        "club_count": len(EPL_CLUBS),
        "featured_fixtures": featured_fixtures,
        "leverage_comparison": leverage_comparison,
        "leaderboard_projection": estimate_leaderboard_ev(weekly_volume_usdc=3500.0, avg_edge_pct=4.2, leverage=2.0),
        "referral_projection_90d": calculate_referral_rewards_90d(
            referred_traders=25,
            avg_weekly_collateral_usdc=1200.0,
            avg_leverage=2.2,
        ),
    }


if __name__ == "__main__":
    print(json.dumps(build_featured_matchweek_report(), indent=2))
