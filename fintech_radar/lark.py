import base64
import hashlib
import hmac
import json
import time
import urllib.request


class LarkClient:
    def __init__(self, webhook_url: str, secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret

    def send_text(self, text: str) -> None:
        payload = {
            "msg_type": "text",
            "content": {"text": text},
        }
        if self.secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = self._sign(timestamp)

        request = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8") or "{}")
        if body.get("code", 0) != 0:
            raise RuntimeError(f"Lark webhook failed: {body}")

    def _sign(self, timestamp: str) -> str:
        string_to_sign = f"{timestamp}\n{self.secret}"
        digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")
