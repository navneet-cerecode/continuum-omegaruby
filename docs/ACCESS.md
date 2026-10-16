# Accounts and company graph access

CONTINUUM has two explicit local modes. `CONTINUUM_ACCESS=demo` keeps the fictional workspace usable without credentials. `CONTINUUM_ACCESS=accounts` requires a signed-in account for every company API, including search, evidence, history and agent tools. The normal demo remains in demo mode; no participant password or personal identity has been invented.

## Provision and enable

Keep the backend stopped while provisioning or editing the identity configuration. Run from the project root:

```powershell
.venv\Scripts\python.exe scripts\manage-accounts.py workspace-admin --company northstar --graph continuum_release_final --role admin --person-id person-1
```

The command prompts twice for a password; do not put it in arguments or source files. It writes salted scrypt hashes to ignored `.runtime/accounts.json`. Choose a password of 15–256 characters. Set `CONTINUUM_ACCESS=accounts` in the ignored `.env`, then restart the backend. Open the app and sign in. Do not use synthetic QA passwords or an example credential for a real account. To rotate a password or change a role, rerun provisioning for that username. To revoke an account, remove it from the private configuration. Keep the file restricted to the application administrator.

The example maps `person-1`, fictional Maya Chen, to an authenticated account for the synthetic launch workflow. This verifies control of a local credential and records the account; it does not establish that a real person is Maya Chen or that a real security review occurred.

## Roles and boundaries

| Role | Allowed company operations |
|---|---|
| viewer | Read company records and run read-only model investigations |
| editor | Viewer operations plus withdrawal, response-plan creation, replacement evidence and follow-up transitions |
| reviewer | Editor operations plus task approval and restoration review; restoration reviewer ID must equal the account's mapped Person ID and the graph's current launch owner |
| admin | Reviewer operations plus reviewed Markdown source import |

The application enforces roles centrally on API routes. Viewer UI still permits browsing the workflows; a forbidden write returns an explicit denial. Import controls are hidden for non-admin accounts. Approved actions, transitions, withdrawals, replacement records and source imports record the authenticated account in the same guarded mutation. Local demo mutations are labeled `local-demo`. Existing records are not retroactively attributed to someone.

Company membership is administrator configuration. Each company must have a distinct FalkorDB graph name; duplicate mappings fail closed. A browser cannot choose a company or graph through a query parameter, header, entity ID or model prompt. The server selects the graph from the session's account configuration, and every organizational query, typed model tool and mutation uses that store. Tests send concurrent requests across two company graphs. Stable entity IDs can overlap safely between graphs. Project selection remains a view filter within the account's company.

Create a separate graph and seed it explicitly before adding a new company's first account. The fixture still models fictional Northstar Systems; graph separation does not create a real company's dataset. Database administrators can access all graphs: this is application-level company separation, not separate database credentials or infrastructure isolation.

## Sessions and operational constraints

Passwords use standard-library scrypt (`N=2^17`, `r=8`, `p=1`, random 16-byte salt), following [OWASP's fallback guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). The session cookie contains a random opaque token; the server keeps only its SHA-256 lookup hash. Cookies are HttpOnly and SameSite Strict. Mutations, including logout and model POSTs, require a synchronizer CSRF header in addition to origin/Host protections. The frontend keeps that CSRF token in memory. See [OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

Sessions last one hour, expire on server restart, and become invalid when the account's password, role, company or Person mapping changes. Logout revokes the session. Sign-in is limited to five attempts per client IP per five minutes; password hashing is serialized and session/rate-limit maps are bounded. Forwarded headers are not trusted as client identity. This implementation requires **one worker**; sessions and limits are process-local. It has no email verification, MFA, self-service recovery, externally verified identities or distributed quota service.

The loopback HTTP app sets `CONTINUUM_COOKIE_SECURE=false`. Set it true when HTTPS is actually configured. Public network exposure still needs a reviewed TLS/proxy configuration, host/origin policy, operational monitoring and independent security assessment. Host restrictions remain loopback-only. Do not interpret the account feature as a production deployment claim.

For Docker account mode use `compose.accounts.yaml` as an override after provisioning. It mounts the private identity file read-only and refuses to create a missing path. The application image's demo mode was built and run successfully on remote Linux CI; the account override is configuration-validated and its access behavior is covered through real native API/browser tests. Local Docker Desktop remains unavailable.
