#!/usr/bin/env python3
"""Draft and publish a factual GitHub release radar to Paragraph."""

import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

WALLET = "0x658f5820602393Ba5b7208314BFD6227F0FA219A"
GITHUB = "https://api.github.com/search/repositories"
PARAGRAPH = "https://public.api.paragraph.com/api/v1/posts"
PARAGRAPH_ME = "https://public.api.paragraph.com/api/v1/me"
PUBLICATION = "https://paragraph.com/@hehmeme"
PUBLICATION_API = "https://public.api.paragraph.com/api/v1/publications/slug/hehmeme/posts/slug"
KEY_FILE = Path(".paragraph_api_key")


def request(url, *, token=None, body=None, missing_ok=False):
    headers = {"Accept": "application/json", "User-Agent": "release-radar/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    for attempt in range(2):
        try:
            with urlopen(Request(url, data=data, headers=headers), timeout=20) as response:
                return json.load(response)
        except HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            detail = error.read(300).decode(errors="replace")
            raise SystemExit(f"HTTP {error.code}: {detail}") from error
        except (TimeoutError, URLError) as error:
            if attempt:
                raise SystemExit(f"network_error={error}") from error


def fetch_repositories(now):
    since = (now - timedelta(days=2)).date().isoformat()
    query = f"topic:ai-agents pushed:>={since} stars:>=100 archived:false fork:false"
    url = f"{GITHUB}?{urlencode({'q': query, 'sort': 'updated', 'per_page': 20})}"
    items = request(url, token=os.getenv("GITHUB_TOKEN"))["items"]
    selected = [item for item in items if item.get("description") and item.get("license")
                and item["license"].get("spdx_id") != "NOASSERTION"
                and "awesome" not in item["name"].lower()
                and "curated" not in item["description"].lower()][:3]
    for item in selected:
        commits = f"https://api.github.com/repos/{item['full_name']}/commits?per_page=3"
        item["commits"] = request(commits, token=os.getenv("GITHUB_TOKEN"))
    return selected


def render(items, now):
    date = now.date().isoformat()
    lines = [
        f"# 3 Open-Source AI Agent Repos Shipping This Week — {date}",
        "",
        "Use this open-source AI agent radar to find work worth checking. It asks a simple question: what "
        "did maintainers ship? Stars show reach. Commits show motion. Neither proves quality.",
        "",
        "Each project has 100+ GitHub stars, a declared license, and activity in the last 48 hours. For "
        "example, a feature commit is more useful than a badge update when you are testing new behavior.",
        "",
        "The commit subjects below link directly to their diffs, so you can inspect what changed rather "
        "than taking a project description at face value.",
        "",
        "| Project | Language | Stars | License |",
        "|---|---:|---:|---|",
    ]
    for item in items:
        license_name = item["license"].get("spdx_id") or item["license"].get("name", "Declared")
        lines.append(f"| [{item['full_name']}]({item['html_url']}) | {item.get('language') or '—'} | "
                     f"{item['stargazers_count']:,} | {license_name} |")
    lines += ["", "## What changed", ""]
    for item in items:
        license_name = item["license"].get("spdx_id") or item["license"].get("name", "Declared")
        lines += [
            f"## [{item['full_name']}]({item['html_url']})",
            "",
            f"**What it is:** {item['description'].strip()}",
            "",
            "**Latest code movement:**",
            "",
        ]
        for commit in item["commits"]:
            subject = commit["commit"]["message"].splitlines()[0]
            lines.append(f"- [{subject}]({commit['html_url']})")
        lines += [
            "",
            f"**Project signal:** {item['stargazers_count']:,} stars · {license_name} · "
            f"{item.get('language') or 'Language not specified'} · repository updated {item['updated_at'][:10]}",
            "",
        ]
    lines += [
        "## How to use this radar",
        "",
        "Open the commit that matches your problem. Does the diff touch your use case? Can you run its tests? "
        "If the work is only documentation or maintenance, wait. If it changes behavior you need, test it "
        "locally before adoption. Activity is a discovery signal, not proof of quality or security.",
        "",
        "---",
        f"Data captured {date} from the GitHub public API. No paid placements.",
        "Need the machine-readable dataset? [Get the 25-project JSON/CSV activity shortlist for $2 USDC]"
        "(https://publish.new/ai-agent-repository-activity-shortlist-25-projects-eb236140).",
        f"Support this independently generated radar: `{WALLET}`",
        f"Referral: [Start your own Paragraph publication](https://paragraph.com/?referrer={WALLET}).",
        "",
    ]
    return "\n".join(lines)


def render_x(items, date):
    names = " · ".join(item["full_name"].split("/")[-1] for item in items)
    commit_count = sum(len(item["commits"]) for item in items)
    return ("Most AI-agent lists rank hype. Today's radar tracks recent code movement.\n\n"
            f"{names}\n\n"
            f"{commit_count} linked commits, plus license, language, and adoption signals. No paid placements.\n\n"
            f"{PUBLICATION}/ai-agent-radar-{date}\n")


def already_published(date):
    return request(f"{PUBLICATION_API}/ai-agent-radar-{date}", missing_ok=True) is not None


def paragraph_key():
    api_key = os.getenv("PARAGRAPH_API_KEY")
    if not api_key and KEY_FILE.exists():
        api_key = KEY_FILE.read_text().strip()
    if not api_key:
        raise SystemExit("Set PARAGRAPH_API_KEY with --setup-key")
    return api_key


def publish(path, send_newsletter=True):
    api_key = paragraph_key()
    markdown = path.read_text()
    title = markdown.splitlines()[0].removeprefix("# ")
    body = {
        "title": title,
        "markdown": markdown,
        "sendNewsletter": send_newsletter,
        "status": "published",
        "subtitle": "Three active projects, linked commits, and a practical adoption check.",
        "postPreview": "A commit-level look at three open-source AI agent projects shipping this week.",
    }
    if path.name.startswith("digest-"):
        body["slug"] = f"ai-agent-radar-{path.stem.removeprefix('digest-')}"
    result = request(PARAGRAPH, token=api_key, body=body)
    print(f"published_post_id={result['id']}")


def check_key():
    request(PARAGRAPH_ME, token=paragraph_key())
    print("paragraph_api_key=valid")


def setup_key():
    key = getpass.getpass("New Paragraph API key: ").strip()
    if not key.startswith("para_"):
        raise SystemExit("Invalid Paragraph API key")
    KEY_FILE.write_text(key)
    KEY_FILE.chmod(0o600)
    print("Paragraph API key saved locally with mode 600")


def self_test():
    item = {"full_name": "org/repo", "html_url": "https://example.test/repo",
            "description": "Useful project.", "license": {"spdx_id": "MIT"},
            "stargazers_count": 123, "language": "Python", "updated_at": "2026-07-12T00:00:00Z",
            "commits": [{"html_url": "https://example.test/commit",
                         "commit": {"message": "Ship feature\nbody"}}]}
    text = render([item], datetime(2026, 7, 12, tzinfo=timezone.utc))
    assert "org/repo" in text and "Ship feature" in text and WALLET in text
    print("self-test passed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", type=Path, metavar="FILE")
    parser.add_argument("--no-newsletter", action="store_true")
    parser.add_argument("--auto", action="store_true", help="generate and publish once per UTC day")
    parser.add_argument("--setup-key", action="store_true")
    parser.add_argument("--check-key", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.setup_key:
        setup_key()
    elif args.check_key:
        check_key()
    elif args.self_test:
        self_test()
    elif args.publish:
        publish(args.publish, send_newsletter=not args.no_newsletter)
    else:
        now = datetime.now(timezone.utc)
        marker = Path(f".published-{now.date().isoformat()}")
        if args.auto and (marker.exists() or already_published(now.date().isoformat())):
            print("evaluation=continue reason=already_published_today")
            return
        items = fetch_repositories(now)
        if len(items) < 3:
            raise SystemExit(f"evaluation=pivot reason=only_{len(items)}_eligible_repositories")
        article = render(items, now)
        social = render_x(items, now.date().isoformat())
        if len(article.split()) < 250 or len(social) > 280:
            raise SystemExit("evaluation=pivot reason=content_quality_gate")
        path = Path(f"digest-{now.date().isoformat()}.md")
        path.write_text(article)
        Path(f"x-post-{now.date().isoformat()}.md").write_text(social)
        print(f"draft={path} evaluation=continue candidates={len(items)}")
        if args.auto:
            publish(path)
            marker.touch()


if __name__ == "__main__":
    main()
