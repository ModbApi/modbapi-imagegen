#!/usr/bin/env python3
"""Create or edit a modbapi image task and print a Codex-renderable result."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://api.modbapi.com"
DEFAULT_MODEL = "gpt-image-2"


def load_local_key() -> str | None:
    """Load a locally-installed key file without printing or committing its value."""
    path = os.getenv("MODBAPI_API_KEY_FILE")
    if not path:
        codex_home = os.getenv("CODEX_HOME", os.path.expanduser("~/.codex"))
        path = os.path.join(codex_home, "secrets", "modbapi-imagegen.env")
    try:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                if line.startswith("MODBAPI_API_KEY="):
                    value = line.rstrip("\n").split("=", 1)[1]
                    if value:
                        return value
    except OSError:
        return None
    return None
TERMINAL_SUCCESS = {"completed", "succeeded"}
TERMINAL_FAILURE = {"failed", "cancelled", "canceled", "expired"}


def request_json(method: str, url: str, api_key: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {"error": {"message": detail or str(exc)}}
        message = parsed.get("error", {}).get("message") if isinstance(parsed.get("error"), dict) else None
        raise RuntimeError(f"HTTP {exc.code}: {message or detail or exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"request failed: {exc.reason}") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("API returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("API returned a non-object JSON response")
    return value


def first_image_url(payload: dict[str, Any]) -> str | None:
    detail = payload.get("detail")
    candidates: list[Any] = []
    if isinstance(detail, dict):
        candidates.append(detail.get("data"))
    candidates.append(payload.get("data"))
    for data in candidates:
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            for key in ("download_url", "url"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call modbapi async image tasks and print a Markdown image.")
    parser.add_argument("--prompt", required=True, help="Image generation or editing prompt")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.getenv("MODBAPI_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=os.getenv("MODBAPI_API_KEY") or load_local_key(), help=argparse.SUPPRESS)
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default=None)
    parser.add_argument("--response-format", choices=("url", "b64_json"), default="url")
    parser.add_argument("--edit", action="store_true", help="Use the image edit task endpoint")
    parser.add_argument("--image-url", action="append", default=[], help="Source image URL; repeat for multiple images")
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("MODBAPI_API_KEY is not set", file=sys.stderr)
        return 2
    if args.edit and not args.image_url:
        print("--edit requires at least one --image-url", file=sys.stderr)
        return 2
    if args.interval <= 0 or args.timeout <= 0:
        print("--interval and --timeout must be positive", file=sys.stderr)
        return 2

    base = args.base_url.rstrip("/") + "/"
    endpoint = urljoin(base, "v1/image-tasks/edits" if args.edit else "v1/image-tasks/generations")
    body: dict[str, Any] = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "response_format": args.response_format,
    }
    if args.quality:
        body["quality"] = args.quality
    if args.edit:
        body["images"] = [{"image_url": image_url} for image_url in args.image_url]

    try:
        created = request_json("POST", endpoint, args.api_key, body)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    task_id = created.get("task_id") or created.get("id")
    if not isinstance(task_id, str) or not task_id:
        direct_url = first_image_url(created)
        if direct_url:
            print(json.dumps({"status": "completed", "image_url": direct_url}, ensure_ascii=False))
            print(f"IMAGE_URL={direct_url}")
            print(f"![Generated image]({direct_url})")
            return 0
        print("ERROR: create response did not include task_id", file=sys.stderr)
        return 1

    deadline = time.monotonic() + args.timeout
    last_status = "unknown"
    while time.monotonic() < deadline:
        try:
            detail_url = urljoin(base, f"v1/image-tasks/{quote(task_id, safe='')}" )
            detail_url += "?" + urlencode({"detail": "true"})
            payload = request_json("GET", detail_url, args.api_key)
        except RuntimeError as exc:
            print(f"ERROR: polling task {task_id}: {exc}", file=sys.stderr)
            return 1
        status = str(payload.get("status", "unknown")).lower()
        if status != last_status:
            print(f"STATUS={status}", file=sys.stderr)
            last_status = status
        if status in TERMINAL_SUCCESS:
            image_url = first_image_url(payload)
            if not image_url:
                print(f"ERROR: task {task_id} completed without detail.data[].download_url", file=sys.stderr)
                return 1
            result = {"task_id": task_id, "status": status, "image_url": image_url}
            print(json.dumps(result, ensure_ascii=False))
            print(f"IMAGE_URL={image_url}")
            print(f"![Generated image]({image_url})")
            return 0
        if status in TERMINAL_FAILURE:
            error = payload.get("error")
            if isinstance(error, dict):
                error = error.get("message") or error
            print(f"ERROR: task {task_id} {status}: {error or 'no error detail'}", file=sys.stderr)
            return 1
        time.sleep(min(args.interval, max(0.0, deadline - time.monotonic())))

    print(f"ERROR: task {task_id} timed out after {args.timeout:g}s (last status: {last_status})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
