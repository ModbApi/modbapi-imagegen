---
name: modbapi-imagegen
description: Generate or edit images from Codex through the modbapi asynchronous image-task API, poll until completion, and render the returned image URL in the Codex client. Use when the user asks Codex to create or edit an image through modbapi; do not use for ordinary text-only requests.
---

# modbapi image generation for Codex

Use the included `scripts/modbapi_imagegen.py` helper. It implements the async API documented at <https://help.modbapi.com/#image-tasks>:

- Generation: `POST {base_url}/v1/image-tasks/generations`
- Editing: `POST {base_url}/v1/image-tasks/edits`
- Polling: `GET {base_url}/v1/image-tasks/{task_id}?detail=true`

## Configuration

Read the API key from `MODBAPI_API_KEY` unless the user supplied a key explicitly. If that variable is absent, the helper reads `$CODEX_HOME/secrets/modbapi-imagegen.env`, created by `scripts/install.sh`. The default base URL is `https://api.modbapi.com`; override it with `MODBAPI_BASE_URL` or `--base-url`. Do not print the API key. Use `response_format=url` so the completed task contains a displayable `detail.data[].download_url`.

## Installation and key setup

For a fresh checkout, run `scripts/install.sh` in an interactive terminal. It requests the API Key with hidden input and stores it at `$CODEX_HOME/secrets/modbapi-imagegen.env` with mode 600. A ChatGPT/Codex client may use the prompt in `INSTALL.md` to perform this checkout and request; never put the key in a chat message or repository file.

## Workflow

1. Convert the user's request into a concise prompt without inventing unrelated subjects. Preserve exact text that must appear in the image.
2. For a new image, run:

   ```sh
   python3 /Users/mtj/.codex/skills/modbapi-imagegen/scripts/modbapi_imagegen.py \
     --prompt "<prompt>" --model "<model>" --size "1024x1024" \
     --quality "high" --response-format url
   ```

   The model defaults to `gpt-image-2.5`; use the user's model when specified.
3. For an edit, add `--edit --image-url URL` once per source image. Keep edit invariants in the prompt (for example, “change only the background; keep the subject unchanged”).
4. The helper saves the returned task id, polls `queued`/`in_progress` every 3 seconds, and stops on `completed` or `failed`. Use `--timeout` for a different maximum wait (default 300 seconds).
5. On success, copy the helper's `IMAGE_URL` into a Markdown image so the Codex client displays it inline:

   `![<short description>](<IMAGE_URL>)`

   Also report the task id and status. Do not expose the API key. If the task fails, show the returned error message and stop polling; do not resubmit automatically.

## API details

- Send `Authorization: Bearer <API_KEY>` and `Content-Type: application/json`.
- Generation body: `model`, `prompt`, optional `size`, `quality`, and `response_format`.
- Edit body additionally contains `images: [{"image_url":"..."}]`.
- A successful create response is `202 Accepted` with `task_id`; creation does not mean the image is ready.
- Only read image URLs after `status=completed` and `detail=true`. The documented result is `detail.data[].download_url`.
- Treat `queued` and `in_progress` as transient. Treat `failed` and `cancelled` as terminal.
