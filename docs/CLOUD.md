# Cloud deployment

CONTINUUM runs as one long-lived application container and a separate persistent FalkorDB service. The app serves the built frontend and API from one HTTPS origin. Keep **one worker and one replica**: sessions, login limits and the model concurrency gate are process-local. Restarting the application signs users out. This is a synthetic hackathon deployment, not a production readiness claim.

## Verified live demo — October 17, 2026

[Open CONTINUUM](https://continuum-omegaruby-production.up.railway.app/). The team must supply judge credentials separately; credentials and account hashes are excluded from the public repository. Use a viewer for read-only exploration or a reviewer for the synthetic approval workflow. Keep the administrator credential private.

The deployed application passed HTTPS login, Secure/HttpOnly/SameSite cookies, unauthenticated API denial, exact Origin checks, CSRF denial and read-only role denial. Real graph queries returned the recorded context. One labeled synthetic rehearsal withdrew Atlas's prerequisite, traced seven affected items, approved and completed one follow-up, then explicitly restored readiness. Its original incident and evidence remain in history.

FalkorDB uses the private provider network and a 500 MB persistent volume at `/data`. A real database restart was performed: AOF remained enabled, its last write status was OK, and the complete recap matched its pre-restart SHA-256. Later application deployments also retained these records. The original laptop graph remained at revision 40.

The full authenticated cloud agent called `assess_launch_readiness` for Beacon using `openai/gpt-oss-120b` on the account's confirmed Groq Free plan. The final answer cited all four required returned source versions and a validated dependency path. Natural-language entailment remains unverified. Evidence: [cloud verification report](../artifacts/cloud-verification.json), [actual agent/tool result](../artifacts/cloud-agent.json).

The runtime changes at commit `b5c04b8` passed **129 tests and actual Docker lifecycle checks** on [Linux CI](https://github.com/navneet-cerecode/continuum-omegaruby/actions/runs/39030348326). Hosting uses Railway trial credits, not a paid upgrade; credit exhaustion can stop the demo, and Groq Free rate limits can temporarily block inference. No always-free availability promise is made.

## Railway setup

Use an existing trial workspace. Do not upgrade or add a payment method automatically. Check the workspace's remaining credits before deploying. Trial credits and availability are temporary; complete local setup remains in the README.

1. Create a private service from `falkordb/falkordb:v4.14.11` named `falkordb`. Do not generate a public domain or TCP proxy for this database.
2. Attach the trial-sized persistent volume at `/data`. Set `REDIS_ARGS=--appendonly yes --appendfsync everysec --dir /data` and `FALKORDB_ARGS=TIMEOUT_DEFAULT 3000 TIMEOUT_MAX 5000`.
3. Add the application from the public source repository. In service settings choose the Dockerfile builder with path `Dockerfile`, one replica, `/api/healthz` as the healthcheck path and three retries on failure. The root Dockerfile builds the frontend, runs as a non-root user, seeds missing fixture records and listens on Railway's `PORT`. Railway no longer permits new services to use legacy `railway.json`; configure these settings in the dashboard or use the current Infrastructure as Code interface.
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

The laptop's Ollama endpoint is unavailable from a cloud container. An OpenAI-compatible hosted provider can use the `chat_completions` adapter. The example contains Groq's `https://api.groq.com/openai/v1` endpoint and `openai/gpt-oss-120b` model, listed on the current Free plan. Groq's Llama 3.3 model is now enterprise-only. An actual free-tier account and private API key must be supplied before claiming live inference works. Check current provider limits; do not enable paid usage without approval. With no valid provider key, deterministic exploration works and the agent reports unavailable explicitly. JSON mode is omitted from tool-calling requests for provider compatibility. A `finish_investigation` function carries the final answer through the same schema, source-ID and path validation; it cannot skip evidence retrieval or change records. Provider-private reasoning is not retained in messages.

## Verification and limits

The first deployment configuration passed **126 local tests**, including exact Origin and Host restrictions, Secure cookies, closed access on missing account configuration, private JSON loading and database TLS configuration. Subsequent hosted-model compatibility guards raised the total to **129**, all passing on Linux CI with the actual application Docker lifecycle checks. The live checks above were executed separately against the Railway deployment.

Before adding a live URL to the submission, verify HTTPS login, unauthenticated company-API denial, deterministic graph exploration, one complete workflow in a dedicated synthetic graph, actual model/tool calls when configured, and persistent graph history after a database restart. Keep the database private and record the deployed commit. Do not reuse the original local demo graph or reset its history. Readiness probes run at deployment time, not as continuous monitoring.

Recheck the existing deployment without repeating mutations:

```powershell
.venv\Scripts\python.exe scripts\verify-cloud.py basics --base-url https://continuum-omegaruby-production.up.railway.app
.venv\Scripts\python.exe scripts\verify-cloud.py agent --base-url https://continuum-omegaruby-production.up.railway.app
```

These commands read the ignored local credential file and never print passwords or session tokens. The separate `workflow` phase requires a fresh synthetic graph, creates a labeled rehearsal and refuses existing history; do not rerun it on an active workspace. The `persistence` phase compares the recap against the saved workflow snapshot after an operator-triggered restart.

Sources: [Railway healthchecks](https://docs.railway.com/deployments/healthchecks), [private domains](https://docs.railway.com/networking/domains/working-with-domains), [legacy config deprecation](https://docs.railway.com/config-as-code), [trial terms](https://docs.railway.com/pricing/free-trial), [volume limits](https://docs.railway.com/volumes/reference), [Groq model catalog](https://console.groq.com/docs/models), [Groq Free plan limits](https://console.groq.com/docs/rate-limits).
