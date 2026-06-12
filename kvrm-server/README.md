# kvrm-server

KVRM fail-closed action routing as an HTTP service. Upload a domain (action
registry + training cases), then route features through the full
selector-ensemble → support-gate → validator → executor pipeline. Every
decision lands in a SQLite audit log bound to the registry digest it ran
against.

## Run

```bash
pip install -e kvrm-core/ -e kvrm-server/
KVRM_SERVER_DATA=./data KVRM_API_KEYS=mysecret uvicorn kvrm_server.app:app
```

Or Docker (from the repo root):

```bash
docker build -f kvrm-server/Dockerfile -t kvrm-server .
docker run -p 8000:8000 -v kvrm-data:/data -e KVRM_API_KEYS=mysecret kvrm-server
```

Leave `KVRM_API_KEYS` unset for an open development server.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + domain list |
| POST | `/domains` | upload a domain (registry, train_cases, optional cases/config) |
| GET | `/domains` / `/domains/{name}` | inspect domains |
| POST | `/domains/{name}/train` | train the compact learned selector |
| POST | `/domains/{name}/route` | route features → decision + audit record |
| POST | `/domains/{name}/eval` | fail-closed metrics over eval cases |
| GET | `/domains/{name}/audit` | recent decisions from the audit log |

All endpoints except `/health` require `X-API-Key` when keys are configured.
Domains created by the server are standard KVRM domain directories — the
`kvrm` CLI works on them directly (`kvrm eval <data-root>/<name>`).
