# modbapi async image-task API

Source: https://help.modbapi.com/#image-tasks (retrieved 2026-09-22).

The default origin is `https://api.modbapi.com`. Authenticate with `Authorization: Bearer <API_KEY>`.

| Operation | Method | Path |
|---|---|---|
| Generate | POST | `/v1/image-tasks/generations` |
| Edit | POST | `/v1/image-tasks/edits` |
| Detail | GET | `/v1/image-tasks/{task_id}?detail=true` |

Create requests return `202 Accepted` and a public `task_id`. Poll every 2–5 seconds. `queued` and `in_progress` are transient; `completed` is successful; `failed` and `cancelled` are terminal. For `response_format=url`, read `detail.data[].download_url` only after completion.
