import html
import re
import urllib.request
from urllib.parse import parse_qs, quote, urlparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .models import FeedItem, Source


NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def fetch_feed(source: Source, timeout: int = 15) -> list[FeedItem]:
    url = feed_url(source)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FintechLarkRadar/0.1 (+https://example.local)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()

    root = ET.fromstring(body)
    if root.tag.endswith("feed"):
        return parse_atom(source, root)
    return parse_rss(source, root)


def feed_url(source: Source) -> str:
    if source.type not in {"youtube", "youtube_playlist"}:
        return source.url

    if source.type == "youtube_playlist":
        playlist_id = youtube_playlist_id(source.url)
        if not playlist_id:
            raise ValueError("YouTube playlist source needs a URL with a list= playlist id.")
        return youtube_playlist_feed_url(playlist_id)

    if source.channel_id:
        return youtube_feed_url(source.channel_id)

    parsed = urlparse(source.url)
    if parsed.path.startswith("/feeds/videos.xml"):
        return source.url

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "channel":
        return youtube_feed_url(parts[1])

    query_channel = parse_qs(parsed.query).get("channel_id", [""])[0]
    if query_channel:
        return youtube_feed_url(query_channel)

    return youtube_feed_url(resolve_youtube_channel_id(source.url))


def youtube_feed_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={quote(channel_id.strip())}"


def youtube_playlist_feed_url(playlist_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?playlist_id={quote(playlist_id.strip())}"


def youtube_playlist_id(url: str) -> str:
    parsed = urlparse(url)
    return parse_qs(parsed.query).get("list", [""])[0]


def resolve_youtube_channel_id(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FintechLarkRadar/0.1 (+https://example.local)",
            "Accept": "text/html",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        page = response.read().decode("utf-8", errors="replace")

    patterns = [
        r'"channelId":"(UC[^"]+)"',
        r'"externalId":"(UC[^"]+)"',
        r'<link rel="canonical" href="https://www.youtube.com/channel/(UC[^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, page)
        if match:
            return match.group(1)

    raise ValueError(f"Could not resolve YouTube channel id from {url}")


def parse_rss(source: Source, root: ET.Element) -> list[FeedItem]:
    channel = root.find("channel")
    if channel is None:
        channel = root
    items = []
    for node in channel.findall("item"):
        title = text(node, "title")
        link = text(node, "link") or text(node, "guid")
        summary = text(node, "description") or text(node, "content:encoded")
        published = text(node, "pubDate") or text(node, "dc:date")
        if title and link:
            items.append(
                FeedItem(
                    source_name=source.name,
                    source_url=source.url,
                    title=clean(title),
                    link=link.strip(),
                    summary=clean(summary),
                    published_at=parse_date(published),
                    source_type=source.type,
                )
            )
    return items


def parse_atom(source: Source, root: ET.Element) -> list[FeedItem]:
    items = []
    for node in root.findall("atom:entry", NAMESPACES):
        title = text(node, "atom:title")
        link = atom_link(node)
        summary = text(node, "atom:summary") or text(node, "atom:content")
        published = text(node, "atom:published") or text(node, "atom:updated")
        if title and link:
            items.append(
                FeedItem(
                    source_name=source.name,
                    source_url=source.url,
                    title=clean(title),
                    link=link.strip(),
                    summary=clean(summary),
                    published_at=parse_date(published),
                    source_type=source.type,
                )
            )
    return items


def text(node: ET.Element, path: str) -> str:
    found = node.find(path, NAMESPACES)
    if found is None or found.text is None:
        return ""
    return found.text.strip()


def atom_link(node: ET.Element) -> str:
    for link in node.findall("atom:link", NAMESPACES):
        rel = link.attrib.get("rel", "alternate")
        href = link.attrib.get("href", "")
        if href and rel == "alternate":
            return href
    first = node.find("atom:link", NAMESPACES)
    return first.attrib.get("href", "") if first is not None else ""


def clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return " ".join(value.split())


def parse_date(value: str):
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
