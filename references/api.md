# modbapi async image-task API

Source: https://help.modbapi.com/#image-tasks (retrieved 2026-09-22).

The documented default origin is `https://api.modbapi.com`. Authenticate with `Authorization: Bearer <API_KEY>`.

| Operation | Method | Path |
|---|---|---|
| Generate | POST | `/v1/image-tasks/generations` |
| Edit | POST | `/v1/image-tasks/edits` |
| Detail | GET | `/v1/image-tasks/{task_id}?detail=true` |

Create requests return `202 Accepted` and a public `task_id`. Poll every 2–5 seconds. `queued` and `in_progress` are transient; `completed` is successful; `failed` and `cancelled` are terminal. For `response_format=url`, read `detail.data[].download_url` only after completion.

The async-task documentation does not enumerate `size`, but the image API requires a lowercase `WIDTHxHEIGHT` value. This skill provides aliases for `1024x1024`, `1024x576`, `576x1024`, `1024x768`, and `768x1024`, and passes any positive exact `WIDTHxHEIGHT` value through to the API. The downloaded image keeps the dimensions returned by the upstream model, including values such as `1672x940`.

When a task reaches `failed`, stop polling and do not automatically create a replacement task. The service returns the reserved amount for failed or cancelled tasks. Preserve `error.message`; an HTML/Next.js 404 response indicates an incompatible upstream task-query route, not a prompt rejection.

The CDN URL can be fetched successfully while still being blocked by a client's remote-image policy. The helper therefore validates and saves the completed image locally by default, then emits an absolute local path for inline rendering.
