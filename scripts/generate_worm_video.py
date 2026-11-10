#!/usr/bin/env python3
"""
Generate a crisp 60-second 1080p H.264 MP4 walkthrough video for Worm.wtf Premier League
Prediction Markets (`assets/worm_epl_prediction_walkthrough.mp4`) using PIL + ffmpeg.

Strictly adheres to Worm terminology guardrails: uses "Predict", "Prediction Market",
"Market Probability", and "Traders" exclusively.
"""

from __future__ import annotations

import math
import pathlib
import struct
import subprocess
import tempfile
import wave
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH = 1920
HEIGHT = 1080
FPS = 24
DURATION_SECONDS = 60
TOTAL_FRAMES = FPS * DURATION_SECONDS  # 1440 frames

FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
FONT_MONO = "/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf"

BG_DARK = (9, 12, 20)
CARD_BG = (17, 23, 38)
CARD_BORDER = (38, 52, 82)
SOL_GREEN = (20, 241, 149)
WORM_PURPLE = (153, 69, 255)
CYAN_ACCENT = (56, 189, 248)
AMBER_ACCENT = (251, 191, 36)
TEXT_WHITE = (245, 248, 255)
TEXT_MUTED = (156, 172, 198)


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def make_base_canvas() -> Image.Image:
    """Create a sleek dark-mode gradient canvas with subtle grid accents."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Subtle vertical gradient + top header glow
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(8 + 8 * (1.0 - t))
        g = int(12 + 14 * (1.0 - t))
        b = int(22 + 22 * (1.0 - t))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Subtle technical grid lines
    for x in range(0, WIDTH, 96):
        draw.line([(x, 0), (x, HEIGHT)], fill=(18, 26, 42), width=1)
    for y in range(0, HEIGHT, 96):
        draw.line([(0, y), (WIDTH, y)], fill=(18, 26, 42), width=1)

    # Top accent bar
    draw.rectangle([0, 0, WIDTH, 6], fill=SOL_GREEN)
    return img


def draw_top_bar(draw: ImageDraw.ImageDraw, step_label: str) -> None:
    f_brand = load_font(FONT_BOLD, 24)
    f_badge = load_font(FONT_MONO, 20)

    # Left brand pill
    draw.rounded_rectangle([72, 36, 456, 84], radius=24, fill=(18, 34, 36), outline=SOL_GREEN, width=2)
    draw.ellipse([90, 50, 110, 70], fill=SOL_GREEN)
    draw.text((124, 44), "WORM.WTF • SOLANA EPL", font=f_brand, fill=TEXT_WHITE)

    # Right scene indicator pill
    draw.rounded_rectangle([1440, 36, 1848, 84], radius=24, fill=CARD_BG, outline=CARD_BORDER, width=2)
    draw.text((1468, 46), step_label, font=f_badge, fill=CYAN_ACCENT)


def draw_bottom_bar(draw: ImageDraw.ImageDraw) -> None:
    f_footer = load_font(FONT_MONO, 22)
    draw.rounded_rectangle([72, 982, 1848, 1038], radius=14, fill=(13, 18, 30), outline=(32, 46, 72), width=1)
    draw.text((100, 996), "Predict Premier League Markets on Solana:", font=load_font(FONT_REG, 22), fill=TEXT_MUTED)
    draw.text((532, 996), "https://www.worm.wtf/r/bLytY0", font=f_footer, fill=SOL_GREEN)
    draw.text((1355, 996), "@wormwtf  •  Up to 3x Leverage", font=f_footer, fill=TEXT_WHITE)


def paste_screenshot_frame(
    canvas: Image.Image,
    screenshot_path: pathlib.Path,
    box: Tuple[int, int, int, int],
    caption: str,
) -> None:
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1

    # Drop shadow
    shadow = Image.new("RGBA", (w + 30, h + 30), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([10, 10, w + 20, h + 20], radius=22, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.paste(shadow, (x1 - 15, y1 - 10), shadow)

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([x1, y1, x2, y2], radius=18, fill=(22, 28, 44), outline=CARD_BORDER, width=2)

    # Browser chrome header
    header_h = 42
    draw.rounded_rectangle([x1 + 2, y1 + 2, x2 - 2, y1 + header_h], radius=16, fill=(26, 34, 54))
    draw.ellipse([x1 + 18, y1 + 14, x1 + 30, y1 + 26], fill=(239, 68, 68))
    draw.ellipse([x1 + 38, y1 + 14, x1 + 50, y1 + 26], fill=(245, 158, 11))
    draw.ellipse([x1 + 58, y1 + 14, x1 + 70, y1 + 26], fill=(34, 197, 94))
    draw.text((x1 + 92, y1 + 10), caption, font=load_font(FONT_MONO, 17), fill=TEXT_MUTED)

    shot = Image.open(screenshot_path).convert("RGB")
    inner_w = w - 16
    inner_h = h - header_h - 12
    shot_resized = shot.resize((inner_w, inner_h), Image.Resampling.LANCZOS)
    canvas.paste(shot_resized, (x1 + 8, y1 + header_h + 4))


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for word in words:
        candidate = f"{cur} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not cur:
            cur = candidate
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def build_scene_1() -> Image.Image:
    img = make_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_top_bar(draw, "01 / 06 • OVERVIEW")

    draw.text((72, 138), "ON-CHAIN SPORTS PREDICTION TERMINAL", font=load_font(FONT_MONO, 24), fill=SOL_GREEN)
    draw.text((72, 184), "Predict the Premier League", font=load_font(FONT_BOLD, 68), fill=TEXT_WHITE)
    draw.text((72, 268), "on Solana with Worm.wtf", font=load_font(FONT_BOLD, 68), fill=CYAN_ACCENT)

    subtitle = (
        "Trade real-time 0%–100% Market Probabilities across all 20 English Premier League clubs "
        "with instant USDC execution, up to 3x Leverage, and weekly Top-10 Trader rewards."
    )
    f_sub = load_font(FONT_REG, 30)
    y = 378
    for line in wrap_lines(draw, subtitle, f_sub, 1680):
        draw.text((72, y), line, font=f_sub, fill=TEXT_MUTED)
        y += 44

    cards = [
        ("LIVE % PROBABILITIES", "0% – 100%", "Transparent Market Probability pricing across EPL Matchweeks & Season Champion markets.", SOL_GREEN),
        ("CONVICTION LEVERAGE", "Up to 3x", "Amplify high-conviction EPL predictions with 1x, 2x, or 3x leverage & clear margin buffers.", WORM_PURPLE),
        ("WEEKLY TRADER PRIZES", "$1,500 USDC", "Compete on the weekly Premier League Top-10 Leaderboard plus 30% USDC referral rewards.", AMBER_ACCENT),
    ]

    for idx, (tag, big, desc, accent) in enumerate(cards):
        cx1 = 72 + idx * 604
        cx2 = cx1 + 568
        cy1, cy2 = 520, 920
        draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=22, fill=CARD_BG, outline=accent, width=2)
        draw.text((cx1 + 36, cy1 + 36), tag, font=load_font(FONT_MONO, 20), fill=accent)
        draw.text((cx1 + 36, cy1 + 88), big, font=load_font(FONT_BOLD, 62), fill=TEXT_WHITE)
        fy = cy1 + 195
        f_desc = load_font(FONT_REG, 25)
        for line in wrap_lines(draw, desc, f_desc, 496):
            draw.text((cx1 + 36, fy), line, font=f_desc, fill=TEXT_MUTED)
            fy += 38

    draw_bottom_bar(draw)
    return img


def build_scene_2(assets_dir: pathlib.Path) -> Image.Image:
    img = make_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_top_bar(draw, "02 / 06 • LIVE EPL MARKETS")

    draw.text((72, 136), "CLEAN MARKET PROBABILITIES", font=load_font(FONT_MONO, 22), fill=SOL_GREEN)
    draw.text((72, 178), "Every EPL Fixture", font=load_font(FONT_BOLD, 50), fill=TEXT_WHITE)
    draw.text((72, 240), "Priced in Clear %", font=load_font(FONT_BOLD, 50), fill=SOL_GREEN)

    bullets = [
        ("Dedicated Premier League Hub", "Navigate straight to Premier League matchweek & season-long prediction markets on worm.wtf."),
        ("Direct % Probability Pricing", "Arsenal at 77% means the market prices a 77% title probability — intuitive for analytical Traders."),
        ("Deep On-Chain Liquidity", "Over $178K+ volume on EPL Champion markets with instant Solana wallet execution."),
    ]
    y = 335
    for title, body in bullets:
        draw.rounded_rectangle([72, y, 710, y + 178], radius=16, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.ellipse([96, y + 28, 114, y + 46], fill=SOL_GREEN)
        draw.text((130, y + 20), title, font=load_font(FONT_BOLD, 25), fill=TEXT_WHITE)
        by = y + 64
        f_b = load_font(FONT_REG, 21)
        for line in wrap_lines(draw, body, f_b, 565):
            draw.text((96, by), line, font=f_b, fill=TEXT_MUTED)
            by += 31
        y += 198

    paste_screenshot_frame(
        img,
        assets_dir / "worm_epl_markets_live.png",
        (750, 136, 1848, 928),
        "worm.wtf/sports?league=eng.1  •  Live Premier League Prediction Markets",
    )
    draw_bottom_bar(draw)
    return img


def build_scene_3(assets_dir: pathlib.Path) -> Image.Image:
    img = make_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_top_bar(draw, "03 / 06 • PROBABILITY CHARTS")

    draw.text((72, 136), "REAL-TIME ORDERBOOKS & COMBOS", font=load_font(FONT_MONO, 22), fill=CYAN_ACCENT)
    draw.text((72, 178), "Trade Yes / No Shares", font=load_font(FONT_BOLD, 48), fill=TEXT_WHITE)
    draw.text((72, 240), "as Probabilities Shift", font=load_font(FONT_BOLD, 48), fill=CYAN_ACCENT)

    bullets = [
        ("Live EPL Title Market Snapshot", "Arsenal 77% • Brighton 7.1% • Man City 7.0% • Liverpool 6.1% • Chelsea 1.8%."),
        ("Exit Early or Hold to Settlement", "Traders do not have to wait for May — capture PnL whenever Market Probability moves in your favor."),
        ("Dixon-Coles Quantitative Edge", "Compare Poisson expected-goal probabilities vs. Worm market % to spot mispriced clubs."),
    ]
    y = 335
    for title, body in bullets:
        draw.rounded_rectangle([72, y, 710, y + 178], radius=16, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.ellipse([96, y + 28, 114, y + 46], fill=CYAN_ACCENT)
        draw.text((130, y + 20), title, font=load_font(FONT_BOLD, 25), fill=TEXT_WHITE)
        by = y + 64
        f_b = load_font(FONT_REG, 21)
        for line in wrap_lines(draw, body, f_b, 565):
            draw.text((96, by), line, font=f_b, fill=TEXT_MUTED)
            by += 31
        y += 198

    paste_screenshot_frame(
        img,
        assets_dir / "worm_epl_champion_odds_live.png",
        (750, 136, 1848, 928),
        "worm.wtf  •  EPL Champion Probability Curve & Leverage Ticket",
    )
    draw_bottom_bar(draw)
    return img


def build_scene_4(assets_dir: pathlib.Path) -> Image.Image:
    img = make_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_top_bar(draw, "04 / 06 • 1x TO 3x LEVERAGE")

    draw.text((72, 136), "CAPITAL EFFICIENCY FOR TRADERS", font=load_font(FONT_MONO, 22), fill=WORM_PURPLE)
    draw.text((72, 178), "Scale Conviction", font=load_font(FONT_BOLD, 50), fill=TEXT_WHITE)
    draw.text((72, 240), "with 1x – 3x Leverage", font=load_font(FONT_BOLD, 50), fill=WORM_PURPLE)

    # Quantitative simulation comparison card ($500 USDC collateral, 46% -> 64% Market Prob)
    draw.rounded_rectangle([72, 332, 710, 928], radius=18, fill=CARD_BG, outline=WORM_PURPLE, width=2)
    draw.text((100, 360), "SIMULATION: $500 USDC COLLATERAL", font=load_font(FONT_MONO, 20), fill=AMBER_ACCENT)
    draw.text((100, 396), "EPL Match Probability Move: 46% -> 64% YES", font=load_font(FONT_BOLD, 23), fill=TEXT_WHITE)

    tiers = [
        ("1.0x Spot", "$500 Exposure", "+$194.65 USDC (+38.9%)", "No Liquidation Risk", SOL_GREEN),
        ("2.0x Leverage", "$1,000 Exposure", "+$389.30 USDC (+77.9%)", "Buffer: 19.3% Prob Drop", CYAN_ACCENT),
        ("3.0x Leverage", "$1,500 Exposure", "+$583.96 USDC (+116.8%)", "Buffer: 11.7% Prob Drop", WORM_PURPLE),
    ]
    ty = 456
    for label, exp, pnl, buf, col in tiers:
        draw.rounded_rectangle([100, ty, 682, ty + 136], radius=14, fill=(12, 17, 29), outline=col, width=2)
        draw.text((122, ty + 16), label, font=load_font(FONT_BOLD, 25), fill=col)
        draw.text((430, ty + 20), exp, font=load_font(FONT_MONO, 19), fill=TEXT_MUTED)
        draw.text((122, ty + 56), pnl, font=load_font(FONT_BOLD, 26), fill=TEXT_WHITE)
        draw.text((122, ty + 96), buf, font=load_font(FONT_MONO, 18), fill=TEXT_MUTED)
        ty += 152

    paste_screenshot_frame(
        img,
        assets_dir / "worm_leverage_markets_live.png",
        (750, 136, 1848, 928),
        "worm.wtf  •  Dedicated Leverage Prediction Markets Hub",
    )
    draw_bottom_bar(draw)
    return img


def build_scene_5() -> Image.Image:
    img = make_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_top_bar(draw, "05 / 06 • LEADERBOARD & REWARDS")

    draw.text((72, 136), "DUAL USDC INCENTIVE ENGINE", font=load_font(FONT_MONO, 22), fill=AMBER_ACCENT)
    draw.text((72, 178), "Weekly $1,500 USDC Prizes + 30% Referral Share", font=load_font(FONT_BOLD, 54), fill=TEXT_WHITE)

    # Left Card: $1,500 Weekly Leaderboard
    draw.rounded_rectangle([72, 286, 936, 928], radius=22, fill=CARD_BG, outline=AMBER_ACCENT, width=2)
    draw.text((112, 324), "WEEKLY PREMIER LEAGUE LEADERBOARD", font=load_font(FONT_MONO, 21), fill=AMBER_ACCENT)
    draw.text((112, 366), "$1,500 USDC Every Matchweek", font=load_font(FONT_BOLD, 38), fill=TEXT_WHITE)

    ranks = [
        ("Rank #1 Top EPL Trader", "$450 USDC"),
        ("Rank #2 Runner-Up Trader", "$300 USDC"),
        ("Rank #3 Podium Trader", "$200 USDC"),
        ("Ranks #4 – #5 Traders", "$130 / $100 USDC"),
        ("Ranks #6 – #10 Traders", "$85 down to $45 USDC"),
    ]
    ry = 446
    for r_name, r_prize in ranks:
        draw.rounded_rectangle([112, ry, 896, ry + 76], radius=12, fill=(12, 17, 29), outline=CARD_BORDER, width=1)
        draw.text((138, ry + 22), r_name, font=load_font(FONT_REG, 24), fill=TEXT_WHITE)
        draw.text((620, ry + 22), r_prize, font=load_font(FONT_MONO, 24), fill=SOL_GREEN)
        ry += 90

    # Right Card: 30% Referral Flywheel
    draw.rounded_rectangle([984, 286, 1848, 928], radius=22, fill=CARD_BG, outline=SOL_GREEN, width=2)
    draw.text((1024, 324), "90-DAY CREATOR & TRADER REFERRALS", font=load_font(FONT_MONO, 21), fill=SOL_GREEN)
    draw.text((1024, 366), "Earn 30% of Fees in USDC", font=load_font(FONT_BOLD, 38), fill=TEXT_WHITE)

    ref_points = [
        "Onboard fellow Premier League Traders with your Worm link.",
        "Receive 30% of protocol trading fees in USDC for 90 full days.",
        "1x–3x leveraged volume scales notional fee generation directly.",
        "Example: 25 active Traders @ $1.2K/wk x 2.2x = $710+ USDC / 90d.",
    ]
    py = 452
    f_rp = load_font(FONT_REG, 24)
    for pt in ref_points:
        draw.ellipse([1024, py + 10, 1040, py + 26], fill=SOL_GREEN)
        for line in wrap_lines(draw, pt, f_rp, 740):
            draw.text((1058, py), line, font=f_rp, fill=TEXT_MUTED)
            py += 36
        py += 20

    draw.rounded_rectangle([1024, 804, 1808, 892], radius=14, fill=(16, 38, 36), outline=SOL_GREEN, width=2)
    draw.text((1052, 832), "Referral Link: https://www.worm.wtf/r/bLytY0", font=load_font(FONT_MONO, 25), fill=SOL_GREEN)

    draw_bottom_bar(draw)
    return img


def build_scene_6() -> Image.Image:
    img = make_base_canvas()
    draw = ImageDraw.Draw(img)
    draw_top_bar(draw, "06 / 06 • START PREDICTING")

    draw.rounded_rectangle([130, 150, 1790, 920], radius=30, fill=CARD_BG, outline=SOL_GREEN, width=3)

    draw.text((210, 210), "START PREDICTING PREMIER LEAGUE MARKETS ON SOLANA", font=load_font(FONT_MONO, 25), fill=SOL_GREEN)
    draw.text((210, 266), "Turn Football Insight into", font=load_font(FONT_BOLD, 64), fill=TEXT_WHITE)
    draw.text((210, 346), "Market Probability Alpha", font=load_font(FONT_BOLD, 64), fill=CYAN_ACCENT)

    steps = [
        ("1", "Open Worm.wtf via Referral Link & Connect Solana Wallet"),
        ("2", "Select Premier League Fixtures or Season Champion Markets (%)"),
        ("3", "Predict Yes/No at 1x–3x Leverage & Climb the $1,500 USDC Leaderboard"),
    ]
    sy = 465
    for num, label in steps:
        draw.rounded_rectangle([210, sy, 268, sy + 58], radius=12, fill=SOL_GREEN)
        draw.text((230, sy + 10), num, font=load_font(FONT_BOLD, 30), fill=BG_DARK)
        draw.text((292, sy + 12), label, font=load_font(FONT_REG, 30), fill=TEXT_WHITE)
        sy += 82

    # Prominent CTA Pill
    draw.rounded_rectangle([210, 738, 1280, 858], radius=22, fill=SOL_GREEN)
    draw.text((252, 768), "https://www.worm.wtf/r/bLytY0", font=load_font(FONT_MONO, 44), fill=BG_DARK)

    draw.rounded_rectangle([1315, 738, 1710, 858], radius=22, fill=(24, 32, 52), outline=WORM_PURPLE, width=2)
    draw.text((1355, 764), "Follow on X:", font=load_font(FONT_REG, 24), fill=TEXT_MUTED)
    draw.text((1355, 800), "@wormwtf", font=load_font(FONT_BOLD, 34), fill=TEXT_WHITE)

    draw_bottom_bar(draw)
    return img


def generate_ambient_wav(wav_path: pathlib.Path, duration_s: int) -> None:
    """Synthesize a clean, gentle C-major9 ambient pad audio track for smooth MP4 playback."""
    sample_rate = 22050
    total_samples = sample_rate * duration_s
    freqs = [130.81, 196.00, 246.94, 293.66, 329.63]  # Warm Cmaj9 chord

    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        chunk = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            # Gentle fade-in (2s) and fade-out (2.5s)
            env = 1.0
            if t < 2.0:
                env = t / 2.0
            elif t > duration_s - 2.5:
                env = max(0.0, (duration_s - t) / 2.5)

            lfo = 0.82 + 0.18 * math.sin(2.0 * math.pi * 0.25 * t)
            val = 0.0
            for idx, f in enumerate(freqs):
                val += math.sin(2.0 * math.pi * f * t) * (0.35 / (idx + 1.2))
            sample = int(max(-32767, min(32767, val * env * lfo * 4200)))
            chunk.extend(struct.pack("<h", sample))
            if len(chunk) >= 44100:
                wf.writeframes(chunk)
                chunk.clear()
        if chunk:
            wf.writeframes(chunk)


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    assets_dir = root / "assets"
    output_mp4 = assets_dir / "worm_epl_prediction_walkthrough.mp4"

    scenes = [
        build_scene_1(),
        build_scene_2(assets_dir),
        build_scene_3(assets_dir),
        build_scene_4(assets_dir),
        build_scene_5(),
        build_scene_6(),
    ]

    # Save preview frames for QA verification if desired
    frames_per_scene = TOTAL_FRAMES // len(scenes)  # 240 frames (10.0s) per scene
    fade_frames = 14  # ~0.58s smooth crossfade

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = pathlib.Path(tmpdir) / "ambient.wav"
        generate_ambient_wav(wav_path, DURATION_SECONDS)

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-i",
            str(wav_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_mp4),
        ]

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdin is not None

        for frame_idx in range(TOTAL_FRAMES):
            scene_idx = min(len(scenes) - 1, frame_idx // frames_per_scene)
            local_f = frame_idx % frames_per_scene

            if local_f < fade_frames and scene_idx > 0:
                alpha = local_f / float(fade_frames)
                frame = Image.blend(scenes[scene_idx - 1], scenes[scene_idx], alpha)
            else:
                frame = scenes[scene_idx].copy()

            draw = ImageDraw.Draw(frame)

            # Animated subtle highlight pulse on screenshot scenes (scenes 1, 2, 3 -> idx 1, 2, 3)
            pulse = int(150 + 95 * (0.5 + 0.5 * math.sin(2.0 * math.pi * (frame_idx / 24.0))))
            if scene_idx in (1, 2, 3):
                accent = (20, pulse, 149) if scene_idx == 1 else ((56, 189, pulse) if scene_idx == 2 else (pulse, 69, 255))
                draw.rounded_rectangle([748, 134, 1850, 930], radius=19, outline=accent, width=3)
            elif scene_idx == 5:
                # Pulse the CTA box on final slide
                draw.rounded_rectangle([206, 734, 1284, 862], radius=24, outline=(pulse, 255, 200), width=4)

            # Smooth bottom progress bar
            prog_w = int(WIDTH * ((frame_idx + 1) / float(TOTAL_FRAMES)))
            draw.rectangle([0, HEIGHT - 8, WIDTH, HEIGHT], fill=(20, 28, 44))
            draw.rectangle([0, HEIGHT - 8, prog_w, HEIGHT], fill=SOL_GREEN)

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        stderr_out = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"ffmpeg failed with code {ret}:\n{stderr_out}")

    print(f"Generated {output_mp4} ({output_mp4.stat().st_size / (1024 * 1024):.2f} MB)")


if __name__ == "__main__":
    main()
