"""Local account sessions and server-controlled company graph selection.

Identity configuration is deployment data, never an organizational-state fallback.
One worker is required: sessions/rate limits intentionally reset on restart.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from hashlib import scrypt, sha256
import hmac
import json
import os
from pathlib import Path
import secrets
from threading import Lock, BoundedSemaphore
from time import monotonic

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from backend.graph import Store, valid_id

COOKIE = "continuum_session"
principal = ContextVar("continuum_principal", default=None)
company_store = ContextVar("continuum_company_store", default=None)


def required():
    mode = os.getenv("CONTINUUM_ACCESS", "demo")
    if mode not in ("demo", "accounts"):
        raise RuntimeError("CONTINUUM_ACCESS must be demo or accounts")
    return mode == "accounts"


def password_hash(password, salt=None):
    if not 15 <= len(password) <= 256:
        raise ValueError("Use a password between 15 and 256 characters")
    salt = salt or secrets.token_hex(16)
    value = scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt),
        n=2**17,
        r=8,
        p=1,
        maxmem=256 * 1024 * 1024,
        dklen=32,
    )
    return salt + ":" + value.hex()


def password_valid(password, encoded):
    try:
        salt, _ = encoded.split(":")
        return hmac.compare_digest(password_hash(password, salt), encoded)
    except (ValueError, TypeError):
        return False


def accounts():
    path = Path(os.getenv("CONTINUUM_ACCOUNTS_FILE", ".runtime/accounts.json"))
    try:
        raw = os.getenv("CONTINUUM_ACCOUNTS_JSON")
        data = json.loads(raw if raw else path.read_text(encoding="utf-8"))
        companies = data["companies"]
        users = data["users"]
        if not companies or len(companies) > 100 or not users or len(users) > 500:
            raise ValueError("Invalid account configuration")
        graphs = []
        for name, company in companies.items():
            valid_id(name)
            graph = valid_id(company["graph"])
            graphs.append(graph)
        if len(graphs) != len(set(graphs)):
            raise ValueError("Companies must use distinct graphs")
        for username, user in users.items():
            valid_id(username)
            if user["company"] not in companies or user["role"] not in (
                "viewer",
                "editor",
                "reviewer",
                "admin",
            ):
                raise ValueError("Invalid account scope")
            if user.get("person_id"):
                valid_id(user["person_id"])
            salt, digest = user["password_hash"].split(":")
            if len(bytes.fromhex(salt)) != 16 or len(bytes.fromhex(digest)) != 32:
                raise ValueError("Invalid password encoding")
        return data
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            503, "Account configuration is unavailable; access is closed"
        ) from exc


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,79}$")
    password: str = Field(min_length=1, max_length=256)


@dataclass
class Session:
    username: str
    account_fingerprint: str
    csrf: str
    expires: float


class Sessions:
    def __init__(self):
        self.sessions = {}
        self.failures = {}
        self.lock = Lock()
        self.hash_slot = BoundedSemaphore(1)

    def login(self, body, address):
        now = monotonic()
        key = address or "unknown"
        with self.lock:
            self.failures = {k: v for k, v in self.failures.items() if v[1] > now}
            count, until = self.failures.get(key, (0, now + 300))
            if count >= 5 or len(self.failures) >= 1000:
                raise HTTPException(
                    429, "Too many sign-in attempts. Try again in five minutes"
                )
            self.failures[key] = (count + 1, until)
        if not self.hash_slot.acquire(blocking=False):
            raise HTTPException(429, "A sign-in is in progress; try again shortly")
        try:
            data = accounts()
            user = data["users"].get(body.username)
            # Equal work for unknown usernames, without keeping a reusable password.
            encoded = user["password_hash"] if user else "00" * 16 + ":" + "00" * 32
            valid = (
                password_valid(
                    body.password
                    if len(body.password) >= 15
                    else "invalid-password-value",
                    encoded,
                )
                and len(body.password) >= 15
            )
            if not user or not valid:
                raise HTTPException(401, "Invalid username or password")
            token = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(32)
            with self.lock:
                self.sessions = {
                    k: v for k, v in self.sessions.items() if v.expires > now
                }
                if len(self.sessions) >= 1000:
                    raise HTTPException(429, "Session limit reached")
                self.sessions[sha256(token.encode()).hexdigest()] = Session(
                    body.username, fingerprint(user), csrf, now + 3600
                )
                self.failures.pop(key, None)
            return token, csrf
        finally:
            self.hash_slot.release()

    def resolve(self, token):
        with self.lock:
            session = (
                self.sessions.get(sha256(token.encode()).hexdigest()) if token else None
            )
        if not session or session.expires <= monotonic():
            raise HTTPException(401, "Sign in to continue")
        data = accounts()
        user = data["users"].get(session.username)
        if not user or fingerprint(user) != session.account_fingerprint:
            raise HTTPException(401, "Account changed; sign in again")
        return (
            session,
            {"username": session.username, **user},
            data["companies"][user["company"]],
        )

    def logout(self, token):
        with self.lock:
            self.sessions.pop(sha256(token.encode()).hexdigest(), None)


def fingerprint(user):
    return sha256(json.dumps(user, sort_keys=True).encode()).hexdigest()


sessions = Sessions()


def actor():
    user = principal.get()
    return user["username"] if user else "local-demo"


class ScopedStore:
    def __init__(self, default):
        self.default = default

    def __getattr__(self, name):
        return getattr(company_store.get() or self.default, name)


async def access(request: Request):
    if (
        not required()
        or not request.url.path.startswith("/api")
        or request.url.path in ("/api/auth/session", "/api/auth/login", "/api/healthz")
    ):
        yield
        return
    session, user, company = sessions.resolve(request.cookies.get(COOKIE, ""))
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not hmac.compare_digest(
            request.headers.get("x-csrf-token", ""), session.csrf
        ):
            raise HTTPException(403, "Refresh your session before changing records")
        path = request.url.path
        if path != "/api/auth/logout":
            role = user["role"]
            if path.startswith("/api/sources"):
                allowed = role == "admin"
            elif path.endswith("/approve"):
                allowed = role in ("reviewer", "admin")
            elif path == "/api/agent":
                allowed = True
            else:
                allowed = role in ("editor", "reviewer", "admin")
            if not allowed:
                raise HTTPException(403, "Your account cannot perform this action")
    user_token = principal.set({k: v for k, v in user.items() if k != "password_hash"})
    store_token = company_store.set(Store(company["graph"]))
    try:
        yield
    finally:
        company_store.reset(store_token)
        principal.reset(user_token)
