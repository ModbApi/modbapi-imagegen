#!/usr/bin/env python3
"""Create or edit a modbapi image task and print a Codex-renderable result."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://api.modbapi.com"
DEFAULT_MODEL = "gpt-image-2.5"
MAX_IMAGE_BYTES = 50 * 1024 * 1024
SIZE_PRESETS = {
    "1:1": "1024x1024",
    "16:9": "1024x576",
    "9:16": "576x1024",
    "4:3": "1024x768",
    "3:4": "768x1024",
}
IMAGE_EXTENSIONS = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


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


def normalize_size(value: str) -> str:
    normalized = value.strip().lower().replace("×", "x").replace(" ", "")
    if normalized in SIZE_PRESETS:
        return SIZE_PRESETS[normalized]
    match = re.fullmatch(r"([1-9]\d*)x([1-9]\d*)", normalized)
    if match:
        return normalized
    aliases = ", ".join(SIZE_PRESETS)
    raise argparse.ArgumentTypeError(
        f"invalid size {value!r}; use one of {aliases}, or an API-supported WIDTHxHEIGHT value"
    )


def default_output_dir() -> str:
    codex_home = os.getenv("CODEX_HOME", os.path.expanduser("~/.codex"))
    return os.path.join(codex_home, "generated_images", "modbapi")


def download_image(image_url: str, task_id: str, output: str | None = None) -> str:
    """Save a completed image locally so Codex can render it reliably."""
    parsed = urlparse(image_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("completed task returned an invalid image URL")

    request = Request(
        image_url,
        headers={"Accept": "image/*", "User-Agent": "modbapi-imagegen/1.0"},
        method="GET",
    )
    try:
        response = urlopen(request, timeout=60)
    except (HTTPError, URLError) as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(f"could not fetch completed image: {reason}") from exc

    with response:
        content_type = response.headers.get_content_type().lower()
        if not content_type.startswith("image/"):
            raise RuntimeError(f"completed image URL returned {content_type or 'unknown content type'}")
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > MAX_IMAGE_BYTES:
                    raise RuntimeError("completed image exceeds the 50 MiB download limit")
            except ValueError:
                pass

        extension = IMAGE_EXTENSIONS.get(content_type, os.path.splitext(parsed.path)[1] or ".img")
        if output:
            destination = os.path.abspath(os.path.expanduser(output))
        else:
            safe_task_id = re.sub(r"[^A-Za-z0-9._-]", "_", task_id)
            destination = os.path.join(default_output_dir(), f"{safe_task_id}{extension}")

        parent = os.path.dirname(destination) or os.curdir
        os.makedirs(parent, exist_ok=True)
        temp_path = ""
        total = 0
        try:
            with tempfile.NamedTemporaryFile(prefix=".modbapi-", suffix=extension, dir=parent, delete=False) as stream:
                temp_path = stream.name
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_IMAGE_BYTES:
                        raise RuntimeError("completed image exceeds the 50 MiB download limit")
                    stream.write(chunk)
            if total == 0:
                raise RuntimeError("completed image URL returned an empty response")
            os.replace(temp_path, destination)
        except Exception:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except FileNotFoundError:
                    pass
            raise
    return destination


def emit_result(task_id: str, status: str, image_url: str, output: str | None, url_only: bool) -> int:
    result = {"task_id": task_id, "status": status, "image_url": image_url}
    if not url_only:
        try:
            image_path = download_image(image_url, task_id, output)
        except RuntimeError as exc:
            print(f"ERROR: task {task_id} completed but {exc}", file=sys.stderr)
            return 1
        result["image_path"] = image_path
    print(json.dumps(result, ensure_ascii=False))
    print(f"IMAGE_URL={image_url}")
    if url_only:
        print(f"![Generated image]({image_url})")
    else:
        print(f"IMAGE_PATH={result['image_path']}")
        print(f"![Generated image]({result['image_path']})")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call modbapi async image tasks and print a Markdown image.")
    parser.add_argument("--prompt", required=True, help="Image generation or editing prompt")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.getenv("MODBAPI_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=os.getenv("MODBAPI_API_KEY") or load_local_key(), help=argparse.SUPPRESS)
    parser.add_argument(
        "--size",
        type=normalize_size,
        default=SIZE_PRESETS["1:1"],
        help="Preset ratio (1:1, 16:9, 9:16, 4:3, 3:4) or API-supported WIDTHxHEIGHT",
    )
    parser.add_argument("--quality", default=None)
    parser.add_argument("--response-format", choices=("url", "b64_json"), default="url")
    parser.add_argument("--output", help="Local image file; defaults to $CODEX_HOME/generated_images/modbapi/")
    parser.add_argument("--url-only", action="store_true", help="Do not save the image locally; render the remote URL")
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
            return emit_result(f"direct-{int(time.time())}", "completed", direct_url, args.output, args.url_only)
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
            return emit_result(task_id, status, image_url, args.output, args.url_only)
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
