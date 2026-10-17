"""Explicit public-host configuration; local defaults stay loopback-only."""

from dataclasses import dataclass
import os
from urllib.parse import urlsplit

LOCAL_ORIGINS = {
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
}


@dataclass(frozen=True)
class Hosting:
    cloud: bool
    origin: str | None
    hosts: list[str]
    origins: set[str]


def configuration():
    mode = os.getenv("CONTINUUM_ENV", "local")
    if mode not in ("local", "cloud"):
        raise RuntimeError("CONTINUUM_ENV must be local or cloud")
    hosts = ["127.0.0.1", "localhost", "[::1]"]
    if mode == "local":
        return Hosting(False, None, hosts, LOCAL_ORIGINS)
    origin = os.getenv("CONTINUUM_PUBLIC_ORIGIN", "").rstrip("/")
    if not origin and os.getenv("RAILWAY_PUBLIC_DOMAIN"):
        origin = "https://" + os.environ["RAILWAY_PUBLIC_DOMAIN"]
    value = urlsplit(origin)
    if (
        value.scheme != "https"
        or not value.hostname
        or value.username
        or value.password
        or value.path
        or value.query
        or value.fragment
        or "*" in value.netloc
    ):
        raise RuntimeError("Cloud mode requires an exact HTTPS public origin")
    if os.getenv("CONTINUUM_ACCESS") != "accounts":
        raise RuntimeError(
            "Cloud mode requires account access; unauthenticated demo mode is refused"
        )
    if os.getenv("CONTINUUM_COOKIE_SECURE", "").lower() != "true":
        raise RuntimeError("Cloud mode requires Secure session cookies")
    # Railway deployment probes use this documented Host header.
    return Hosting(True, origin, hosts + [value.hostname, "healthcheck.railway.app"], {origin})
