import json
import os
from urllib.error import HTTPError
import urllib.request

from .models import FeedItem


class Translator:
    def translate_item(self, item: FeedItem) -> FeedItem:
        return item


class OpenAITranslator(Translator):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.disabled = False

    def translate_item(self, item: FeedItem) -> FeedItem:
        if self.disabled:
            return item

        prompt = {
            "title": item.title,
            "summary": item.summary[:1200],
            "source": item.source_name,
            "categories": item.categories,
        }
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You translate and summarize fintech news for a Chinese content "
                        "operations team at a fintech company. Return compact Simplified "
                        "Chinese. Keep company/product names in English when appropriate. "
                        "Return only JSON with keys title_zh and summary_zh. The summary "
                        "should be 1-2 sentences, explain why it matters, and stay factual."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            self.disabled = True
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API returned HTTP {exc.code}: {detail[:500]}") from exc

        result = parse_response_text(data)
        parsed = json.loads(result)
        item.title_zh = parsed.get("title_zh", "").strip()
        item.summary_zh = parsed.get("summary_zh", "").strip()
        return item


def build_translator() -> Translator:
    enabled = os.getenv("TRANSLATE_TO_ZH", "false").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return Translator()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("[warn] TRANSLATE_TO_ZH=true but OPENAI_API_KEY is not set; using original text.")
        return Translator()

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    return OpenAITranslator(api_key=api_key, model=model)


def parse_response_text(data: dict) -> str:
    if data.get("output_text"):
        return data["output_text"]

    parts = []
    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(content["text"])
    if parts:
        return "\n".join(parts)

    raise RuntimeError(f"Could not parse translation response: {data}")
