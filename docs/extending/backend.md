# Connecting a backend

Without a backend, Chalk writes the transcript to a file and saves artifacts locally (see [Artifacts and transcripts](../tasks/artifacts-and-transcripts.md)).
To collect runs in one place, set `backend_uri` in the run config (see [Run config](../running/run-config.md)):

```json
"backend_uri": "https://runs.example.com"
```

Chalk then streams each run's transcript to the backend, reports the run's state, and uploads artifacts through it.

## Endpoints

Chalk calls these HTTP endpoints on `backend_uri`.
Each request passes `run_id` as a query parameter, except presign, which sends it in the body.

| Request                                | Purpose                                                                                                                                                  |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /api/internal/create_transcript` | Starts a transcript.                                                                                                                                     |
| `GET /api/internal/transcript_length`  | Returns the number of stored events as a JSON number, or 404 if there are none.                                                                          |
| `POST /api/internal/append_transcript` | Sends `{"event": ..., "seq": n}` in the body. If Chalk writes the same `seq` again, the backend must overwrite the stored event, not append a new one. |
| `POST /api/internal/update_run_state`  | Sends `status` (`running`, `passed`, `failed`, `error`), `score` and token counts in the body.                                                           |
| `POST /api/artifacts/presign`          | Sends `{"run_id", "artifact_paths"}` in the body and returns `{"presigned_urls": {path: url}}`. Chalk then PUTs each file gzipped.                     |

### Transcripts

When a run starts, Chalk asks for the transcript length.
If it gets a 404, it creates the transcript.
Otherwise it reuses the existing one.
It then appends every event, with `seq` counting up from 0.
When a run reconnects, it replays its events from the start.
That's why a repeated `seq` must overwrite the stored event.

Chalk doesn't send streaming message chunks (`message_chunk`, `message_chunk_reset`).

### Run state

Chalk posts `update_run_state` after the task starts, after each token usage event, and when the task completes:

```json
{
    "status": "running",
    "score": null,
    "input_tokens": 1200,
    "output_tokens": 340,
    "cache_read_tokens": null,
    "cache_write_tokens": null
}
```

Token counts are totals for the run so far.
They're `null` until they're known.

### Artifacts

For each artifact, Chalk asks `presign` for one URL per file.
It then `PUT`s each file gzip-compressed, with `Content-Encoding: gzip`.
For a directory artifact, each file's path is `<directory name>/<path inside it>`.
If an upload fails, Chalk logs the failure, and the run doesn't fail because of it.

## Retries

Chalk retries `/api/internal/` requests on connection errors, timeouts and 5xx responses.
It uses exponential backoff and keeps trying for up to 25 minutes per request.
Each attempt times out after 30 seconds.
Other error responses aren't retried.
`presign` is retried the same way, but for up to 5 minutes, and each attempt times out after 60 seconds.

## Authentication

If the file at `CHALK_BACKEND_TOKEN_PATH` (default `/var/run/secrets/service-account-token`) exists, requests carry `Authorization: Bearer <token>`.
Chalk reads the file again for every request, so the token can rotate during a run.
If the file doesn't exist, requests carry no `Authorization` header.

## External agent

If you set `"agent": "external"` in the run config, the backend also supplies the model's messages.
Chalk still runs the steps and executes the tool calls.

| Request                             | Purpose                                                                          |
| ----------------------------------- | -------------------------------------------------------------------------------- |
| `GET /api/internal/get_message`     | Returns the next message, or 404 while there isn't one.                          |
| `POST /api/internal/delete_message` | Consumes the message that was just returned. The response must have a JSON body. |

`get_message` returns a `message_added` event.
Chalk treats it as a long poll: after a 404, it calls again right away.
If no message arrives within 120 minutes, the run fails with a timeout.
The external agent only works when `backend_uri` is set.

## Event schema

The events are the models in `chalk.schemas.transcript`, serialized as JSON.
Each event Chalk sends has a `type`, such as `task_started`, `message_added`, `scoring` or `task_completed`.
