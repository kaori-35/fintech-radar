import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .classifier import classify
from .feeds import fetch_feed
from .lark import LarkClient
from .models import Source
from .storage import Store
from .translator import build_translator


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_sources(path: str) -> list[Source]:
    return [Source.from_dict(item) for item in load_json(path) if item.get("enabled", True)]


def build_message(items) -> str:
    lines = [f"Fintech Radar: {len(items)} 条新动态"]
    grouped = {}
    for item in items:
        grouped.setdefault(item.primary_category, []).append(item)

    for category, category_items in sorted(grouped.items()):
        lines.append("")
        lines.append(f"[{category}]")
        for item in category_items[:8]:
            published = item.published_at.strftime("%Y-%m-%d") if item.published_at else "no date"
            title = item.title_zh or item.title
            summary = item.summary_zh or compact_summary(item.summary)
            lines.append(f"标题：{title}")
            lines.append(f"摘要：{summary or '暂无摘要'}")
            lines.append(f"来源：{item.source_name} · {published}")
            lines.append(f"链接：{item.link}")
            lines.append("")
        if len(category_items) > 8:
            lines.append(f"...另有 {len(category_items) - 8} 条")

    return "\n".join(lines)


def compact_summary(summary: str, limit: int = 220) -> str:
    cleaned = " ".join((summary or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def run_once(args) -> int:
    load_dotenv(args.env)
    sources_path = os.getenv("RADAR_SOURCES", args.sources)
    categories_path = os.getenv("RADAR_CATEGORIES", args.categories)
    db_path = os.getenv("RADAR_DB_PATH", args.db)

    sources = load_sources(sources_path)
    categories = load_json(categories_path)
    store = Store(db_path)
    if not args.dry_run or store.path.exists():
        store.init()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.lookback_days)
    future_cutoff = now + timedelta(days=args.future_grace_days)
    translator = build_translator()

    new_items = []
    for source in sources:
        if args.verbose:
            print(f"[fetch] {source.name}")
        try:
            feed_items = fetch_feed(source, timeout=args.timeout)
        except Exception as exc:
            print(f"[warn] {source.name}: {exc}")
            continue

        for item in feed_items:
            if item.published_at and item.published_at < cutoff:
                continue
            if item.published_at and item.published_at > future_cutoff:
                continue
            item.categories = classify(item, source.tags, categories)

            if store.has_item(item):
                continue

            if args.max_items and len(new_items) >= args.max_items:
                break

            try:
                item = translator.translate_item(item)
            except Exception as exc:
                print(f"[warn] translation failed for {item.title}: {exc}")
            if args.dry_run:
                new_items.append(item)
            elif store.insert_item(item):
                new_items.append(item)

        if args.max_items and len(new_items) >= args.max_items:
            break

    if not new_items:
        print("No new items.")
        return 0

    message = build_message(new_items)
    if args.dry_run:
        print(message)
        return 0

    webhook_url = os.getenv("LARK_WEBHOOK_URL", "")
    secret = os.getenv("LARK_SECRET", "")
    if not webhook_url:
        raise RuntimeError("LARK_WEBHOOK_URL is required unless --dry-run is used.")

    LarkClient(webhook_url=webhook_url, secret=secret).send_text(message)
    print(f"Sent {len(new_items)} item(s) to Lark.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Fintech/neobank RSS radar for Lark groups.")
    parser.add_argument("--once", action="store_true", help="Run one polling cycle.")
    parser.add_argument("--watch", action="store_true", help="Poll forever.")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds for --watch.")
    parser.add_argument("--dry-run", action="store_true", help="Print instead of sending to Lark.")
    parser.add_argument("--env", default=".env", help="Path to .env file.")
    parser.add_argument("--sources", default="config/sources.json", help="Path to sources JSON.")
    parser.add_argument("--categories", default="config/categories.json", help="Path to categories JSON.")
    parser.add_argument("--db", default="data/radar.sqlite3", help="Path to SQLite database.")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds.")
    parser.add_argument("--lookback-days", type=int, default=3, help="Ignore items older than this many days.")
    parser.add_argument("--max-items", type=int, default=0, help="Stop after collecting this many new items.")
    parser.add_argument("--verbose", action="store_true", help="Print source-by-source progress.")
    parser.add_argument(
        "--future-grace-days",
        type=int,
        default=1,
        help="Ignore items dated more than this many days in the future.",
    )
    args = parser.parse_args()

    if not args.once and not args.watch:
        args.once = True

    if args.once:
        raise SystemExit(run_once(args))

    while True:
        try:
            run_once(args)
        except Exception as exc:
            print(f"[error] {exc}")
        time.sleep(max(args.interval, 30))
