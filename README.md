# Worm.wtf Premier League Quantitative Prediction & 3× Leverage Terminal (Solana)

[![Live Demo](https://img.shields.io/badge/Live_Terminal-GitHub_Pages-14F195?style=for-the-badge)](https://jeffrey-graham.github.io/worm-epl-solana-predictor/)
[![Predict on Worm.wtf](https://img.shields.io/badge/Predict_EPL_on_Worm.wtf-r%2FbLytY0-9945FF?style=for-the-badge)](https://www.worm.wtf/r/bLytY0)

An open-source quantitative analytics engine, interactive dark-mode web terminal, and 60-second 1080p walkthrough built for **Premier League Traders** on [**Worm.wtf**](https://www.worm.wtf/r/bLytY0) (`https://www.worm.wtf/sports?league=eng.1`).

---

## Key Capabilities

1. **20-Club Dixon-Coles / Bivariate Poisson Match Probability Engine (`src/worm_epl_engine.py`)**
   - Models offensive and defensive club strength across all **20 English Premier League clubs** with low-scoring correlation adjustments ($\tau_\rho$).
   - Compares quantitative `Home / Draw / Away` model probabilities against live **Worm.wtf Market Probabilities (`%`)** to surface actionable positive-EV prediction edges.
2. **1× / 2× / 3× Leveraged Position & Liquidation-Buffer Simulator**
   - Simulates `YES` and `NO` prediction positions from `1.0×` spot (zero liquidation risk) up to `3.0×` leverage.
   - Computes notional USDC exposure, protocol fees, net PnL, ROI `%`, exact liquidation probability thresholds, and safety buffers in percentage points.
3. **Weekly `$1,500 USDC` Top-10 Leaderboard EV Ranker & 90-Day `30%` USDC Referral Calculator**
   - Models expected weekly Matchweek leaderboard rewards (`$1,500 USDC` split across Top 10 EPL Traders) alongside 90-day `30%` USDC referral fee payouts (`https://www.worm.wtf/r/bLytY0`).
4. **Interactive Web Terminal (`index.html`) & 60-Second 1080p Video (`assets/worm_epl_prediction_walkthrough.mp4`)**
   - Zero-dependency interactive browser terminal + 1080p H.264 walkthrough featuring verified live `worm.wtf` Premier League & Leverage market screenshots.

---

## Quickstart & Verification

```bash
# Run full unit test suite (including strict Prediction Market terminology audit)
python3 -m unittest discover -s tests -v

# Generate live Matchweek quantitative JSON report
python3 -m src.worm_epl_engine

# Regenerate the 60-second 1080p H.264 walkthrough video
python3 scripts/generate_worm_video.py
```

## Links

- **Predict Premier League Markets on Worm.wtf (Referral):** [https://www.worm.wtf/r/bLytY0](https://www.worm.wtf/r/bLytY0)
- **Live Worm.wtf EPL Hub:** [https://www.worm.wtf/sports?league=eng.1](https://www.worm.wtf/sports?league=eng.1)
- **Interactive Analytics Terminal:** [https://jeffrey-graham.github.io/worm-epl-solana-predictor/](https://jeffrey-graham.github.io/worm-epl-solana-predictor/)
