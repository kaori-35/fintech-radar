from .models import FeedItem


def normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def classify(item: FeedItem, source_tags: list[str], categories: dict[str, list[str]]) -> list[str]:
    haystack = normalize(" ".join([item.title, item.summary]))
    matched = []

    for category, keywords in categories.items():
        if any(normalize(keyword) in haystack for keyword in keywords):
            matched.append(category)

    if not matched:
        if "podcast" in source_tags:
            return ["podcast"]
        if "newsletter" in source_tags or "kol" in source_tags:
            return ["kol_newsletter"]
        return ["general_fintech"]

    return matched
