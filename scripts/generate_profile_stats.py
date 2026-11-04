#!/usr/bin/env python3
"""Generate self-hosted GitHub profile SVGs using GitHub's official API.

Requires GH_TOKEN. Only the Python standard library is used; assets are
committed by GitHub Actions so the README never depends on a third-party
stats image service. When the API fails, existing SVGs are preserved.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER = "qlsl1198"
OUTPUT = Path(__file__).resolve().parents[1] / "assets"
TOKEN = os.environ.get("GH_TOKEN", "")
COLORS = {
    "Java": "#b07219", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "Python": "#3572A5", "HTML": "#e34c26", "CSS": "#563d7c",
    "Dart": "#00B4AB", "Kotlin": "#A97BFF", "Swift": "#F05138",
    "Shell": "#89e051", "Go": "#00ADD8", "PHP": "#4F5D95",
    "C": "#555555", "C++": "#f34b7d", "Jupyter Notebook": "#DA5B0B",
}


def api(url, payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "qlsl1198-profile-stats",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": "Bearer " + TOKEN,
    }
    data = json.dumps(payload).encode("utf-8") if payload else None
    if payload:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method="POST" if payload else "GET")
    try:
        with urlopen(req, timeout=25) as response:
            return json.load(response)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"GitHub API request failed ({url}): {exc}") from exc


def svg_start(w, h, title):
    """Transparent cards: no large framed backgrounds or four boxed metrics."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{escape(title, quote=True)}" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">'
        '<style>'
        '.primary{fill:#24292f}.secondary{fill:#57606a}'
        '.accent{fill:#087f72}.track{fill:#dfe5ec}.empty{fill:#dce4eb}'
        '@media(prefers-color-scheme:dark){'
        '.primary{fill:#e6edf3}.secondary{fill:#8b949e}'
        '.accent{fill:#56d5b2}.track{fill:#263443}.empty{fill:#263443}'
        '}</style>'
    )


def rect(x, y, w, h, fill, radius=0, opacity=1):
    special = {"#dfe5ec": "track", "#dce4eb": "empty"}
    cls = f' class="{special[fill]}"' if fill in special else ''
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{radius}" fill="{fill}"{cls} opacity="{opacity}"/>')


def text(x, y, value, size=16, color="primary", weight=400, anchor="start"):
    # Use adaptive fill colors that remain legible in GitHub light/dark mode.
    aliases = {
        "#ffffff": "primary", "#cbdcf2": "primary",
        "#9cbad3": "secondary", "#9adfd2": "accent",
    }
    key = aliases.get(color, color)
    fg = f'class="{key}"' if key in ("primary", "secondary", "accent") else f'fill="{key}"'
    return (f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" {fg} '
            f'text-anchor="{anchor}">{escape(str(value))}</text>')


def save(name, content, w, h):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    new_value = svg_start(w, h, name.replace(".svg", "")) + content + "</svg>\n"
    if not path.exists() or path.read_text(encoding="utf-8") != new_value:
        path.write_text(new_value, encoding="utf-8")
        print("Generated", path)


def repositories():
    repos = []
    page = 1
    while True:
        batch = api(
            f"https://api.github.com/users/{USER}/repos"
            f"?per_page=100&page={page}&type=owner"
        )
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected GitHub repositories API response")
        repos.extend(r for r in batch if r.get("private") is False)
        if len(batch) < 100:
            break
        page += 1
    return repos


def calendar_data():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=365)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        followers { totalCount }
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    result = api(
        "https://api.github.com/graphql",
        {"query": query, "variables": {
            "login": USER, "from": start.isoformat(), "to": now.isoformat()
        }},
    )
    if result.get("errors"):
        raise RuntimeError("GitHub GraphQL: " + json.dumps(result["errors"]))
    user = result.get("data", {}).get("user")
    if not user:
        raise RuntimeError("GitHub user not found in GraphQL response")
    return (
        user["followers"]["totalCount"],
        user["contributionsCollection"]["contributionCalendar"],
    )


def make_stats(repos, followers, calendar):
    stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    original = sum(1 for r in repos if not r.get("fork"))
    total = calendar["totalContributions"]
    days = [d for week in calendar["weeks"] for d in week["contributionDays"]]
    today = datetime.now(timezone.utc).date().isoformat()
    eligible = sorted((d for d in days if d["date"] <= today), key=lambda x: x["date"])
    if eligible and eligible[-1]["contributionCount"] == 0:
        eligible = eligible[:-1]
    streak = 0
    for day in reversed(eligible):
        if day["contributionCount"] < 1:
            break
        streak += 1
    metrics = [
        ("PUBLIC REPOS", len(repos)),
        ("ORIGINAL REPOS", original),
        ("TOTAL STARS", stars),
        ("CONTRIBUTIONS / 1Y", total),
    ]
    body = text(25, 43, "GitHub Overview", 25, "primary", 700)
    body += text(25, 69, "Official GitHub API data · refreshed daily", 13, "secondary")
    for i, (label, value) in enumerate(metrics):
        x = 25 + i * 217
        body += text(x + 5, 120, f"{value:,}", 34, "primary", 700)
        body += text(x + 5, 146, label, 12, "secondary", 600)
        if i < len(metrics) - 1:
            xx = x + 204
            body += f'<line x1="{xx}" y1="95" x2="{xx}" y2="155" stroke="#a5b4c3" stroke-width="1" opacity=".45"/>'
    body += text(30, 191,
                 f"{followers:,} followers  ·  Current contribution streak: {streak} day(s)",
                 14, "accent")
    save("stats.svg", body, 900, 213)


def make_languages(repos):
    byte_counts = Counter()
    successes = 0
    for repo in repos:
        if repo.get("fork") or repo.get("archived") or repo.get("name") == USER:
            continue
        languages_url = repo.get("languages_url")
        if not languages_url:
            continue
        try:
            languages = api(languages_url)
            for language, size in languages.items():
                byte_counts[language] += int(size)
            successes += 1
        except RuntimeError as exc:
            print("Warning:", exc, file=sys.stderr)
    if not byte_counts or successes == 0:
        raise RuntimeError("No language data returned: refusing to overwrite the previous card")
    items = byte_counts.most_common(6)
    total = sum(byte_counts.values())
    body = text(25, 43, "Most Used Languages", 25, "primary", 700)
    body += text(25, 66, "Public, non-fork repositories · measured by code bytes", 13, "secondary")
    for i, (language, size) in enumerate(items):
        y = 94 + i * 36
        pct = size / total * 100
        body += text(28, y + 12, language, 14, "primary", 600)
        body += rect(210, y, 575, 13, "#dfe5ec", 7)
        body += rect(210, y, round(575 * pct / 100, 2), 13,
                     COLORS.get(language, "#8bb5ea"), 7)
        body += text(859, y + 12, f"{pct:.1f}%", 14, "secondary", 600, "end")
    body += text(25, 335, "Statistics describe repository files, not professional proficiency.", 12, "secondary")
    save("languages.svg", body, 900, 352)


def make_contributions(calendar):
    weeks = calendar["weeks"][-52:]
    body = text(25, 43, "Contribution Activity", 25, "primary", 700)
    body += text(25, 67, f"{calendar['totalContributions']:,} contributions in the last 12 months", 13, "secondary")
    intensity = ["#dce4eb", "#a2dacd", "#6cc9b7", "#2eab98", "#087f72"]
    for i, week in enumerate(weeks):
        for j, day in enumerate(week["contributionDays"]):
            count = day["contributionCount"]
            level = 0 if count == 0 else (1 if count < 3 else
                        2 if count < 6 else 3 if count < 12 else 4)
            body += rect(25 + 16 * i, 89 + 16 * j, 12, 12, intensity[level], 3)
    body += text(25, 215, "Less", 12, "secondary")
    for k, color in enumerate(intensity):
        body += rect(68 + 17 * k, 204, 12, 12, color, 2)
    body += text(163, 215, "More", 12, "secondary")
    save("contributions.svg", body, 900, 232)


def main():
    if not TOKEN:
        raise RuntimeError("GH_TOKEN is required. Run via GitHub Actions.")
    repos = repositories()
    followers, calendar = calendar_data()
    # Fetch and validate all API data before replacing any of the 3 cards.
    make_languages(repos)
    make_stats(repos, followers, calendar)
    make_contributions(calendar)


if __name__ == "__main__":
    main()
