---
name: modbapi-imagegen
description: Generate or edit images from Codex through the modbapi asynchronous image-task API, poll until completion, save the result locally, and render it in the Codex client. Use when the user asks Codex to create or edit an image through modbapi; do not use for ordinary text-only requests.
---

# modbapi image generation for Codex

Use the included `scripts/modbapi_imagegen.py` helper. It implements the async API documented at <https://help.modbapi.com/#image-tasks>:

- Generation: `POST {base_url}/v1/image-tasks/generations`
- Editing: `POST {base_url}/v1/image-tasks/edits`
- Polling: `GET {base_url}/v1/image-tasks/{task_id}?detail=true`

## Configuration

Read the API key from `MODBAPI_API_KEY` unless the user supplied a key explicitly. If that variable is absent, the helper reads `$CODEX_HOME/secrets/modbapi-imagegen.env`, created by `scripts/install.sh`. The default base URL is `https://api.modbapi.com`; override it with `MODBAPI_BASE_URL` or `--base-url`. Do not print the API key. Use `response_format=url` so the completed task contains a displayable `detail.data[].download_url`.

The helper provides these recommended 1K ratio aliases:

| Ratio | Size |
|---|---|
| `1:1` | `1024x1024` |
| `16:9` | `1024x576` |
| `9:16` | `576x1024` |
| `4:3` | `1024x768` |
| `3:4` | `768x1024` |

Pass either a ratio alias or a positive exact `WIDTHxHEIGHT` value to `--size`. Exact values such as `1672x940` are passed through unchanged; the remote API decides whether they are supported. Preserve the dimensions of the returned image instead of resizing it locally, because an upstream model may return a different native size.

## Installation and key setup

For a fresh checkout, run `scripts/install.sh` in an interactive terminal. It requests the API Key with hidden input and stores it at `$CODEX_HOME/secrets/modbapi-imagegen.env` with mode 600. A ChatGPT/Codex client may use the prompt in `INSTALL.md` to perform this checkout and request; never put the key in a chat message or repository file.

## Workflow

1. Convert the user's request into a concise prompt without inventing unrelated subjects. Preserve exact text that must appear in the image. For long, repetitive, or multi-view prompts, follow [references/prompting.md](references/prompting.md): choose one aspect ratio, resolve alternatives, state identity and wardrobe invariants once, and keep a short non-duplicated avoid list.
2. For a new image, run:

   ```sh
   python3 /Users/mtj/.codex/skills/modbapi-imagegen/scripts/modbapi_imagegen.py \
     --prompt "<prompt>" --model "<model>" --size "<ratio-or-size>" \
     --quality "high" --response-format url
   ```

   The model defaults to `gpt-image-2.5`; use the user's model when specified.
3. For an edit, add `--edit --image-url URL` once per source image. Keep edit invariants in the prompt (for example, “change only the background; keep the subject unchanged”).
4. The helper saves the returned task id, polls `queued`/`in_progress` every 3 seconds, and stops on `completed` or `failed`. Use `--timeout` for a different maximum wait (default 300 seconds). Per the API documentation, do not automatically resubmit a failed task. Report `error.message`; if it contains HTML or a 404 page, identify it as an upstream task-query route problem rather than a prompt problem.
5. On success, the helper downloads the completed image without resizing it, saves it to `$CODEX_HOME/generated_images/modbapi/`, and prints `IMAGE_PATH` plus ready-to-use Markdown. Copy that exact Markdown into the final response so the Codex client displays the local file inline:

   `![<short description>](<absolute IMAGE_PATH>)`

   Do not substitute `IMAGE_URL` in the Markdown; some CDN domains are not rendered by the client. Use `--output <path>` when the image belongs in the current project. `--url-only` preserves the old remote-URL behavior when explicitly needed. Also report the task id, status, and saved path. Do not expose the API key. If the task fails, show the returned error message and stop polling; do not resubmit automatically.

## API details

- Send `Authorization: Bearer <API_KEY>` and `Content-Type: application/json`.
- Generation body: `model`, `prompt`, optional `size`, `quality`, and `response_format`.
- Edit body additionally contains `images: [{"image_url":"..."}]`.
- A successful create response is `202 Accepted` with `task_id`; creation does not mean the image is ready.
- Only read image URLs after `status=completed` and `detail=true`. The documented result is `detail.data[].download_url`.
- Treat the remote URL as the source for the local result, not as the default display target. The helper validates an image content type, enforces a 50 MiB limit, and atomically writes the local file.
- Treat `queued` and `in_progress` as transient. Treat `failed` and `cancelled` as terminal.
