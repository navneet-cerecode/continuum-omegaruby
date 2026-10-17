import os
from pathlib import Path
from typing import Literal
from threading import BoundedSemaphore
from fastapi import FastAPI, Request, Query, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from backend.http_guards import RequestGuards
from backend.graph import Store, GraphUnavailable
from backend.service import Continuum
from backend.agent import run_agent, AgentUnavailable, agent_configured
from backend.restoration import ReplacementEvidence, Revalidation
from backend.changes import Withdrawal
from backend.onboarding import SourceBatch
from backend.hosting import configuration
from backend.access import (
    access,
    ScopedStore,
    required,
    sessions,
    Login,
    COOKIE,
    principal,
)

hosting = configuration()
app = FastAPI(
    title="CONTINUUM · OmegaRuby", version="0.2.0", dependencies=[Depends(access)]
)
store = ScopedStore(Store())
service = Continuum(store)
model_slots = BoundedSemaphore(1)
app.add_middleware(RequestGuards)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=hosting.hosts,
    www_redirect=False,
)


@app.exception_handler(GraphUnavailable)
def db_error(request, exc):
    return JSONResponse(
        status_code=503, content={"error": str(exc), "dependency": "FalkorDB"}
    )


@app.exception_handler(AgentUnavailable)
def model_error(request, exc):
    return JSONResponse(
        status_code=503,
        content={"error": str(exc), "dependency": "model", "trace": exc.trace},
    )


@app.exception_handler(ValueError)
def input_error(request, exc):
    return JSONResponse(status_code=409, content={"error": str(exc)})


@app.middleware("http")
async def local_writes_only(request: Request, call_next):
    # Origin restrictions also defend login against cross-origin session replacement.
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and (
        (hosting.cloud and not origin) or (origin and origin not in hosting.origins)
    ):
        return JSONResponse(
            status_code=403, content={"error": "Cross-origin mutation refused"}
        )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-attr 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )
    response.headers["Cache-Control"] = (
        "no-store" if request.url.path.startswith("/api") else "no-cache"
    )
    return response


@app.get("/api/auth/session")
def auth_session(request: Request):
    if not required():
        return {
            "mode": "demo",
            "authenticated": False,
            "role": "demo",
            "company": "Northstar Systems",
        }
    try:
        session, user, company = sessions.resolve(request.cookies.get(COOKIE, ""))
    except HTTPException as exc:
        if exc.status_code == 401:
            return {"mode": "accounts", "authenticated": False}
        raise
    return {
        "mode": "accounts",
        "authenticated": True,
        "username": user["username"],
        "role": user["role"],
        "company": user["company"],
        "person_id": user.get("person_id"),
        "csrf": session.csrf,
    }


@app.post("/api/auth/login")
def login(body: Login, request: Request):
    if not required():
        raise HTTPException(409, "Accounts are not enabled in local demo mode")
    token, csrf = sessions.login(body, request.client.host if request.client else None)
    response = JSONResponse({"authenticated": True, "csrf": csrf})
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=os.getenv("CONTINUUM_COOKIE_SECURE", "false").lower() == "true",
        samesite="strict",
        max_age=3600,
        path="/",
    )
    return response


@app.post("/api/auth/logout")
def logout(request: Request):
    sessions.logout(request.cookies.get(COOKIE, ""))
    response = JSONResponse({"signed_out": True})
    response.delete_cookie(COOKIE, path="/")
    return response


@app.get("/api/health")
def health():
    revision = store.revision()
    return {
        "database": "available",
        "revision": revision,
        "agent_configured": agent_configured(),
        "synthetic": True,
        "team": "OmegaRuby",
    }


@app.get("/api/healthz")
def readiness_probe():
    if required():
        from backend.access import accounts

        accounts()
    store.revision()
    return {"status": "ready"}


@app.get("/api/overview")
def overview(
    project_id: str | None = None,
    prerequisite_id: str | None = None,
    event_id: str | None = None,
):
    return service.overview(project_id, prerequisite_id, event_id)


@app.get("/api/events/{event_id}")
def event_details(event_id: str, project_id: str | None = None):
    return service.event_details(event_id, project_id)


@app.get("/api/search")
def search(q: str = Query(default="", max_length=100)):
    return store.search(q)


@app.get("/api/records/{kind}")
def records(
    kind: str,
    project_id: str | None = None,
    cursor: str | None = Query(default=None, max_length=2000),
    limit: int = Query(default=25, ge=1, le=100),
):
    from backend.paging import page

    return page(store, kind, project_id, cursor, limit)


@app.post("/api/sources/preview")
def preview_sources(body: SourceBatch):
    from backend.onboarding import prepare

    return prepare(store, body)


@app.post("/api/sources/import")
def import_sources(body: SourceBatch):
    from backend.onboarding import publish

    return publish(store, body)


@app.get("/api/entities/{entity_id}")
def entity(entity_id: str):
    return store.inspect(entity_id)


@app.get("/api/readiness")
def readiness(project_id: str = "project-atlas"):
    return service.readiness(project_id)


@app.get("/api/impact/{entity_id}")
def impact(entity_id: str):
    return store.impact(entity_id)


@app.post("/api/changes/withdraw-security")
def change():
    return service.withdraw()


@app.post("/api/changes/withdraw")
def selected_change(body: Withdrawal):
    return service.withdraw(**body.model_dump())


@app.post("/api/plans")
def plan(event_id: str = "change-export-withdrawn"):
    return service.propose(event_id)


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,79}$")
    selected: list[str] = Field(min_length=1, max_length=20)


@app.post("/api/actions/approve")
def approve(body: Approval):
    return service.approve(body.plan_id, body.selected)


class Transition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["completed", "rejected"]


@app.patch("/api/actions/{action_id}")
def transition(action_id: str, body: Transition):
    return service.transition(action_id, body.state)


@app.get("/api/recap")
def recap(project_id: str | None = None):
    return service.recap(project_id)


@app.post("/api/restorations")
def record_replacement(body: ReplacementEvidence):
    from backend.restoration import record

    return record(store, body)


@app.get("/api/restorations/{review_id}")
def replacement_review(review_id: str):
    from backend.restoration import review

    return review(store, review_id)


@app.post("/api/restorations/{review_id}/approve")
def revalidate(review_id: str, body: Revalidation):
    from backend.restoration import approve

    user = principal.get()
    if user and user.get("person_id") != body.reviewer_id:
        raise HTTPException(
            403, "Reviewer must match your account's recorded Person ID"
        )
    return approve(store, review_id, body)


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=1500)
    project_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{0,79}$")
    event_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{0,79}$")


@app.post("/api/agent")
def agent(body: Question):
    if not model_slots.acquire(blocking=False):
        return JSONResponse(
            status_code=429,
            content={
                "error": "An investigation is already running. Wait for it to finish before asking again."
            },
        )
    try:
        question = body.question
        if body.event_id:
            service.event_details(body.event_id, body.project_id)
            question = "Selected incident ID: " + body.event_id + ". " + question
        if body.project_id:
            if store.entity(body.project_id)["kind"] != "Project":
                raise ValueError("Select a project ID")
            return run_agent(
                service,
                "Selected project ID: " + body.project_id + ". " + question,
            )
        return run_agent(service, question)
    finally:
        model_slots.release()


dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
