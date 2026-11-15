#!/usr/bin/env python3
"""Render a GitHub-style contribution heatmap as a themed SVG.

Reads the contribution calendar for USERNAME via GitHub's GraphQL API
(authenticated with GITHUB_TOKEN) and writes profile/contrib.svg.
Pass --mock to render random data for local preview.
"""
import datetime as dt
import json
import os
import random
import sys
import urllib.request

USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER", "SANSKAR500")
OUT = os.path.join(os.path.dirname(__file__), "..", "profile", "contrib.svg")

BG = "#0a0a1a"
TEXT = "#C9D1D9"
ACCENT = "#00D4FF"
EMPTY = "#161b2e"
# Five intensity levels, dark to bright cyan.
LEVELS = ["#161b2e", "#0b3d4f", "#0c6b87", "#00a8cc", "#00d4ff"]

CELL = 11
GAP = 3
STEP = CELL + GAP
LEFT = 30
TOP = 84

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_calendar():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set")
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], cal["weeks"]


def mock_calendar():
    random.seed(7)
    start = dt.date.today() - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # align to Sunday
    weeks, total = [], 0
    for w in range(53):
        days = []
        for d in range(7):
            day = start + dt.timedelta(weeks=w, days=d)
            count = random.choice([0, 0, 1, 2, 3, 5, 8, 12]) if day <= dt.date.today() else 0
            total += count
            days.append({"date": day.isoformat(), "contributionCount": count})
        weeks.append({"contributionDays": days})
    return total, weeks


def level(count, max_count):
    if count == 0:
        return 0
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.5:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def render(total, weeks):
    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    max_count = max(counts) if counts and max(counts) > 0 else 1
    width = LEFT + len(weeks) * STEP + 20
    height = TOP + 7 * STEP + 26

    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'fill="none" xmlns="http://www.w3.org/2000/svg" role="img" '
        'aria-label="GitHub contribution graph">',
        "<style>",
        f".title {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {ACCENT}; }}",
        f".sub {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; }}",
        f".month {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; opacity: 0.7; }}",
        f".legend {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; opacity: 0.7; }}",
        "</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="{BG}" stroke="#1d2340"/>',
        f'<text x="20" y="32" class="title">Contribution Activity</text>',
        f'<text x="20" y="50" class="sub">{total:,} contributions in the last year</text>',
    ]

    # Month labels above the first week that starts a new month.
    last_month = None
    for i, week in enumerate(weeks):
        first = week["contributionDays"][0]["date"]
        month = dt.date.fromisoformat(first).strftime("%b")
        if month != last_month and i < len(weeks) - 2:
            parts.append(f'<text x="{LEFT + i * STEP}" y="{TOP - 10}" class="month">{month}</text>')
            last_month = month

    # Day labels (Mon, Wed, Fri).
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = TOP + row * STEP + CELL - 2
        parts.append(f'<text x="0" y="{y}" class="month">{label}</text>')

    # Cells.
    for i, week in enumerate(weeks):
        for j, day in enumerate(week["contributionDays"]):
            lvl = level(day["contributionCount"], max_count)
            color = LEVELS[lvl] if lvl else EMPTY
            x = LEFT + i * STEP
            y = TOP + j * STEP
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}">'
                f'<title>{day["contributionCount"]} contributions on {day["date"]}</title></rect>'
            )

    # Legend.
    lx = width - 20 - (len(LEVELS) * STEP + 60)
    ly = height - 14
    parts.append(f'<text x="{lx}" y="{ly}" class="legend">Less</text>')
    for k, color in enumerate(LEVELS):
        parts.append(
            f'<rect x="{lx + 34 + k * STEP}" y="{ly - 10}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>'
        )
    parts.append(f'<text x="{lx + 34 + len(LEVELS) * STEP + 2}" y="{ly}" class="legend">More</text>')

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    total, weeks = mock_calendar() if "--mock" in sys.argv else fetch_calendar()
    out = OUT if "--mock" not in sys.argv else "/tmp/claude-0/-home-claude/0e1faa65-8930-51c5-be45-87909e25b75f/scratchpad/contrib-mock.svg"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(total, weeks))
    print(f"wrote {out} ({total} contributions)")


if __name__ == "__main__":
    main()
