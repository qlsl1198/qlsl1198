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
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{escape(title, quote=True)}" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">'
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#0f2027"/>'
        '<stop offset="0.55" stop-color="#203a43"/>'
        '<stop offset="1" stop-color="#192b42"/></linearGradient></defs>'
        f'<rect x="1" y="1" rx="20" width="{w-2}" height="{h-2}" '
        'fill="url(#bg)" stroke="#34526b" stroke-width="2"/>'
    )


def rect(x, y, w, h, fill, radius=0, opacity=1):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{radius}" fill="{fill}" opacity="{opacity}"/>')


def text(x, y, value, size=16, color="#dbeafe", weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{color}" '
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
    body = text(32, 48, "GitHub Overview", 26, "#ffffff", 700)
    body += text(32, 74, "Official GitHub API data - refreshed daily", 13, "#9cbad3")
    for i, (label, value) in enumerate(metrics):
        x = 32 + i * 216
        body += rect(x, 102, 197, 89, "#172e40", 13)
        body += text(x + 16, 131, label, 12, "#9cbad3", 700)
        body += text(x + 16, 175, f"{value:,}", 30, "#ffffff", 700)
    body += text(
        33, 217,
        f"{followers:,} followers  |  Current contribution streak: {streak} day(s)",
        14, "#9adfd2",
    )
    save("stats.svg", body, 900, 238)


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
    body = text(32, 48, "Most Used Languages", 26, "#ffffff", 700)
    body += text(
        32, 73, "Repository code bytes by language (public, non-fork projects)",
        13, "#9cbad3",
    )
    for i, (language, size) in enumerate(items):
        y = 103 + i * 37
        pct = size / total * 100
        body += text(32, y + 12, language, 14, "#ffffff", 600)
        body += rect(210, y, 582, 14, "#273e52", 7)
        body += rect(210, y, round(582 * pct / 100, 2), 14,
                     COLORS.get(language, "#8bb5ea"), 7)
        body += text(857, y + 12, f"{pct:.1f}%", 14, "#cbdcf2", 600, "end")
    body += text(32, 352, "Excludes forks and archived repositories", 12, "#9cbad3")
    save("languages.svg", body, 900, 371)


def make_contributions(calendar):
    weeks = calendar["weeks"][-52:]
    body = text(32, 45, "Contribution Activity", 26, "#ffffff", 700)
    body += text(
        32, 72,
        f"{calendar['totalContributions']:,} contributions in the last 12 months",
        14, "#9cbad3",
    )
    intensity = ["#1a3343", "#1b665e", "#279c89", "#38bdae", "#83e5cb"]
    for i, week in enumerate(weeks):
        for j, day in enumerate(week["contributionDays"]):
            count = day["contributionCount"]
            level = 0 if count == 0 else (1 if count < 3 else
                        2 if count < 6 else 3 if count < 12 else 4)
            body += rect(32 + 16 * i, 95 + 16 * j, 12, 12, intensity[level], 3)
    body += text(32, 223, "Less", 12, "#9cbad3")
    for k, color in enumerate(intensity):
        body += rect(76 + 17 * k, 212, 12, 12, color, 2)
    body += text(171, 223, "More", 12, "#9cbad3")
    body += text(865, 223, "GitHub contributions calendar", 12, "#9cbad3", anchor="end")
    save("contributions.svg", body, 900, 249)


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
