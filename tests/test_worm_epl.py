#!/usr/bin/env python3
"""Unit test suite for Worm Premier League Quantitative Prediction & 3x Leverage Engine."""

import pathlib
import re
import unittest

from src.worm_epl_engine import (
    EPL_CLUBS,
    TOP_10_PRIZE_POOL_USDC,
    WORM_EPL_URL,
    WORM_REFERRAL_CODE,
    WORM_REFERRAL_URL,
    build_featured_matchweek_report,
    calculate_referral_rewards_90d,
    estimate_leaderboard_ev,
    evaluate_title_market_edges,
    predict_epl_match,
    simulate_leveraged_position,
)


class TestWormEplEngine(unittest.TestCase):
    def test_twenty_epl_clubs_present_and_valid(self) -> None:
        self.assertEqual(len(EPL_CLUBS), 20)
        for code, club in EPL_CLUBS.items():
            self.assertEqual(code, club.code)
            self.assertGreater(club.attack_strength, 0.5)
            self.assertGreater(club.defense_strength, 0.5)
            self.assertGreater(club.worm_champion_market_pct, 0.0)
            self.assertTrue(club.primary_color.startswith("#"))

    def test_dixon_coles_probability_axioms(self) -> None:
        res = predict_epl_match(
            "ARS",
            "MCI",
            worm_market_home_pct=45.0,
            worm_market_draw_pct=27.0,
            worm_market_away_pct=28.0,
        )
        probs = res["probabilities"]
        total = probs["home_win"] + probs["draw"] + probs["away_win"]
        self.assertAlmostEqual(total, 1.0, places=5)

        mkt = res["market_probabilities_pct"]
        self.assertAlmostEqual(
            mkt["model_home_pct"] + mkt["model_draw_pct"] + mkt["model_away_pct"],
            100.0,
            places=2,
        )
        self.assertEqual(len(res["top_scorelines"]), 5)
        self.assertGreaterEqual(
            res["top_scorelines"][0]["probability_pct"],
            res["top_scorelines"][1]["probability_pct"],
        )

    def test_stronger_club_and_home_advantage(self) -> None:
        ars_vs_sou = predict_epl_match("ARS", "SOU")
        sou_vs_ars = predict_epl_match("SOU", "ARS")
        self.assertGreater(
            ars_vs_sou["probabilities"]["home_win"],
            ars_vs_sou["probabilities"]["away_win"],
        )
        # Arsenal at home vs Southampton should have higher win prob than Arsenal away
        self.assertGreater(
            ars_vs_sou["probabilities"]["home_win"],
            sou_vs_ars["probabilities"]["away_win"],
        )

    def test_invalid_matchup_raises(self) -> None:
        with self.assertRaises(ValueError):
            predict_epl_match("ARS", "ARS")
        with self.assertRaises(ValueError):
            predict_epl_match("XYZ", "ARS")

    def test_title_market_edges_sum_to_hundred_pct(self) -> None:
        edges = evaluate_title_market_edges()
        self.assertEqual(len(edges), 20)
        model_sum = sum(item["model_probability_pct"] for item in edges)
        self.assertAlmostEqual(model_sum, 100.0, delta=0.15)
        self.assertEqual(edges[0]["code"], "ARS")
        self.assertEqual(edges[0]["worm_market_pct"], 77.0)

    def test_leverage_simulator_scaling_and_liquidation_buffers(self) -> None:
        pos_1x = simulate_leveraged_position(
            collateral_usdc=500.0,
            entry_market_pct=50.0,
            exit_market_pct=65.0,
            leverage=1.0,
            side="YES",
        )
        pos_2x = simulate_leveraged_position(
            collateral_usdc=500.0,
            entry_market_pct=50.0,
            exit_market_pct=65.0,
            leverage=2.0,
            side="YES",
        )
        pos_3x = simulate_leveraged_position(
            collateral_usdc=500.0,
            entry_market_pct=50.0,
            exit_market_pct=65.0,
            leverage=3.0,
            side="YES",
        )

        self.assertIsNone(pos_1x["liquidation_market_pct"])
        self.assertFalse(pos_1x["liquidated"])
        self.assertGreater(pos_2x["net_pnl_usdc"], pos_1x["net_pnl_usdc"])
        self.assertGreater(pos_3x["net_pnl_usdc"], pos_2x["net_pnl_usdc"])

        # Higher leverage narrows liquidation buffer
        self.assertGreater(pos_2x["liquidation_buffer_pct"], pos_3x["liquidation_buffer_pct"])

    def test_leverage_liquidation_caps_loss_at_collateral(self) -> None:
        wiped = simulate_leveraged_position(
            collateral_usdc=300.0,
            entry_market_pct=60.0,
            exit_market_pct=10.0,
            leverage=3.0,
            side="YES",
        )
        self.assertTrue(wiped["liquidated"])
        self.assertEqual(wiped["net_pnl_usdc"], -300.0)
        self.assertEqual(wiped["final_equity_usdc"], 0.0)

        no_side = simulate_leveraged_position(
            collateral_usdc=300.0,
            entry_market_pct=60.0,
            exit_market_pct=35.0,
            leverage=2.5,
            side="NO",
        )
        self.assertFalse(no_side["liquidated"])
        self.assertGreater(no_side["net_pnl_usdc"], 0.0)

    def test_weekly_leaderboard_ev_ranker(self) -> None:
        self.assertAlmostEqual(sum(TOP_10_PRIZE_POOL_USDC.values()), 1500.0, places=2)
        low_vol = estimate_leaderboard_ev(weekly_volume_usdc=500.0, avg_edge_pct=2.0, leverage=1.0)
        high_vol = estimate_leaderboard_ev(weekly_volume_usdc=6000.0, avg_edge_pct=4.5, leverage=2.5)
        self.assertGreater(
            high_vol["top_10_finish_probability_pct"],
            low_vol["top_10_finish_probability_pct"],
        )
        self.assertGreater(
            high_vol["expected_leaderboard_bonus_usdc"],
            low_vol["expected_leaderboard_bonus_usdc"],
        )
        self.assertLessEqual(high_vol["projected_rank"], low_vol["projected_rank"])

    def test_referral_rewards_90d_calculator(self) -> None:
        ref = calculate_referral_rewards_90d(
            referred_traders=20,
            avg_weekly_collateral_usdc=1400.0,
            avg_leverage=2.0,
            platform_fee_bps=25.0,
            referral_fee_share=0.30,
            window_days=90,
        )
        self.assertEqual(ref["referral_code"], WORM_REFERRAL_CODE)
        self.assertEqual(ref["referral_url"], WORM_REFERRAL_URL)
        self.assertEqual(WORM_EPL_URL, "https://www.worm.wtf/sports?league=eng.1")
        # Daily notional = 20 * (1400 * 2.0 / 7) = 8000 USDC/day
        # 90d notional = 720,000 USDC; 0.25% fee = 1,800 USDC; 30% share = 540 USDC
        self.assertAlmostEqual(ref["notional_volume_90d_usdc"], 720000.0, places=2)
        self.assertAlmostEqual(ref["referrer_usdc_90d"], 540.0, places=2)
        self.assertAlmostEqual(ref["referrer_usdc_30d"] * 3.0, ref["referrer_usdc_90d"], places=2)

    def test_featured_report_and_strict_terminology_guardrail(self) -> None:
        report = build_featured_matchweek_report()
        self.assertEqual(report["club_count"], 20)
        self.assertEqual(len(report["featured_fixtures"]), 4)

        root_dir = pathlib.Path(__file__).resolve().parent.parent
        forbidden_tokens = [
            "b" + "et",
            "b" + "ets",
            "b" + "etting",
            "gambl" + "e",
            "gambl" + "ing",
            "wag" + "er",
            "wag" + "ers",
            "wag" + "ering",
            "cas" + "ino",
            "cas" + "inos",
        ]
        pattern = re.compile(r"\b(" + "|".join(forbidden_tokens) + r")\b", re.IGNORECASE)

        text_suffixes = {".py", ".html", ".md", ".js", ".css", ".json", ".txt"}
        violations = []
        for path in root_dir.rglob("*"):
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.is_file() and path.suffix.lower() in text_suffixes:
                content = path.read_text(encoding="utf-8", errors="ignore")
                matches = pattern.findall(content)
                if matches:
                    violations.append((str(path.relative_to(root_dir)), matches))

        self.assertEqual(
            violations,
            [],
            f"Terminology guardrail violated in files: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
