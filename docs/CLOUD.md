# Cloud deployment

CONTINUUM runs as one long-lived application container and a separate persistent FalkorDB service. The app serves the built frontend and API from one HTTPS origin. Keep **one worker and one replica**: sessions, login limits and the model concurrency gate are process-local. Restarting the application signs users out. This is a synthetic hackathon deployment, not a production readiness claim.

## Railway setup

Use an existing trial workspace. Do not upgrade or add a payment method automatically. Check the workspace's remaining credits before deploying. Trial credits and availability are temporary; complete local setup remains in the README.

1. Create a private service from `falkordb/falkordb:v4.14.11` named `falkordb`. Do not generate a public domain or TCP proxy for this database.
2. Attach the trial-sized persistent volume at `/data`. Set `REDIS_ARGS=--appendonly yes --appendfsync everysec --dir /data` and `FALKORDB_ARGS=TIMEOUT_DEFAULT 3000 TIMEOUT_MAX 5000`.
3. Add the application from the public source repository. The root `Dockerfile` builds the frontend, runs as a non-root user, seeds missing fixture records and listens on Railway's `PORT`. `railway.json` sets one replica and `/api/healthz` as the readiness check.
4. Use `.env.cloud.example` as the variable checklist. Set the exact application HTTPS origin (or use Railway's injected `RAILWAY_PUBLIC_DOMAIN`), `CONTINUUM_ENV=cloud`, `CONTINUUM_ACCESS=accounts` and `CONTINUUM_COOKIE_SECURE=true`. Cloud startup refuses demo access and insecure cookies.
5. Use `falkordb.railway.internal:6379` for the graph connection and a new graph such as `continuum_cloud_demo`. Plain database transport is only intended inside the provider's private network. For an external TLS endpoint set `FALKORDB_TLS=true`; certificate and hostname verification remain enabled. Optional database username/password variables are server-side only.
6. Provision account hashes as described below, then put that JSON in the application's private `CONTINUUM_ACCOUNTS_JSON` variable. Never commit credentials, password hashes, private configuration or provider keys.
7. Generate the application's HTTPS domain and deploy. The allowed Host list includes the configured hostname and Railway's documented `healthcheck.railway.app` probe hostname. All writes require the exact public Origin; authenticated writes also require a CSRF token.

## Private account setup

From the repository root, provision a fresh account interactively:

```powershell
.venv\Scripts\python.exe scripts\manage-accounts.py workspace-admin --company northstar --graph continuum_cloud_demo --role admin --person-id person-1 --file .runtime/cloud-accounts.json
```

The password is entered locally, never as a command argument. Upload the generated JSON only as the private Railway variable. A separate `viewer` account can be used for evaluation without mutation permission. Keep admin credentials private. Only synthetic Northstar Systems data is included; the Person mapping is a fictional workflow actor.

## Cloud model

The laptop's Ollama endpoint is unavailable from a cloud container. An OpenAI-compatible hosted provider can use the existing `chat_completions` adapter. The example contains Groq's `https://api.groq.com/openai/v1` endpoint and `llama-3.3-70b-versatile` model. An actual free-tier account and private API key must be supplied before claiming live inference works. Check current provider limits; do not enable paid usage without approval. With no valid provider key, deterministic exploration works and the agent reports unavailable explicitly.

## Verification and limits

The deployment changes passed **126 local tests**, including exact Origin and Host restrictions, Secure cookies, closed access on missing account configuration, private JSON loading and database TLS configuration. Docker execution was previously verified on Linux CI; the cloud deployment still needs its own live checks.

Before adding a live URL to the submission, verify HTTPS login, unauthenticated company-API denial, deterministic graph exploration, one complete isolated workflow, actual model/tool calls when configured, and persistent graph history after a database restart. Keep the database private and record the deployed commit. Do not reuse the original local demo graph or reset its history. Readiness probes run at deployment time, not as continuous monitoring.

Sources: [Railway healthchecks](https://docs.railway.com/deployments/healthchecks), [private domains](https://docs.railway.com/networking/domains/working-with-domains), [trial terms](https://docs.railway.com/pricing/free-trial), [volume limits](https://docs.railway.com/volumes/reference), [Groq model documentation](https://console.groq.com/docs/model/llama-3.3-70b-versatile).
