"""Real database regressions for accounts, scoped pages and atomic onboarding."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.graph import Store
from backend.seed import seed
from backend.service import Continuum
from backend.access import password_hash, password_valid, ScopedStore, Sessions
import backend.access as access
import backend.main as main
from backend.onboarding import SourceBatch, prepare, publish
from backend.paging import page
from test_integration import service

PASSWORD = "test-only-password-42!"


@pytest.fixture
def secured(monkeypatch, tmp_path):
    stores = [Store("continuum_access_" + uuid.uuid4().hex) for _ in range(2)]
    for s in stores:
        seed(s)
    encoded = password_hash(PASSWORD)
    data = {
        "companies": {
            "alpha": {"graph": stores[0].name},
            "beta": {"graph": stores[1].name},
        },
        "users": {},
    }
    for username, company, role in (
        ("reader", "alpha", "viewer"),
        ("editor", "alpha", "editor"),
        ("reviewer", "alpha", "reviewer"),
        ("admin", "alpha", "admin"),
        ("other", "beta", "admin"),
    ):
        data["users"][username] = {
            "company": company,
            "role": role,
            "person_id": "person-1",
            "password_hash": encoded,
        }
    path = tmp_path / "accounts.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("CONTINUUM_ACCESS", "accounts")
    monkeypatch.setenv("CONTINUUM_ACCOUNTS_FILE", str(path))
    monkeypatch.setattr(access, "sessions", Sessions())
    monkeypatch.setattr(main, "sessions", access.sessions)
    proxy = ScopedStore(stores[0])
    monkeypatch.setattr(main, "store", proxy)
    monkeypatch.setattr(main, "service", Continuum(proxy))

    def login(user):
        client = TestClient(main.app, base_url="http://127.0.0.1:8000")
        response = client.post(
            "/api/auth/login", json={"username": user, "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        assert (
            "HttpOnly" in response.headers["set-cookie"]
            and "SameSite=strict" in response.headers["set-cookie"]
        )
        client.headers["X-CSRF-Token"] = response.json()["csrf"]
        return client

    yield stores, login, path
    for s in stores:
        s.graph.delete()


def test_accounts_require_session_role_and_csrf(secured):
    stores, login, _ = secured
    anonymous = TestClient(main.app, base_url="http://127.0.0.1:8000")
    for path in (
        "/api/health",
        "/api/overview",
        "/api/entities/project-atlas",
        "/api/records/history",
    ):
        assert anonymous.get(path).status_code == 401
    reader = login("reader")
    assert reader.get("/api/overview").status_code == 200
    assert reader.post("/api/changes/withdraw-security").status_code == 403
    editor = login("editor")
    csrf = editor.headers.pop("X-CSRF-Token")
    assert editor.post("/api/changes/withdraw-security").status_code == 403
    editor.headers["X-CSRF-Token"] = csrf
    assert (
        editor.post("/api/changes/withdraw-security").json()["event"]["recorded_by"]
        == "editor"
    )
    assert (
        editor.post(
            "/api/actions/approve", json={"plan_id": "missing", "selected": ["missing"]}
        ).status_code
        == 403
    )
    assert (
        editor.post("/api/sources/preview", json={"markdown": ["x"]}).status_code == 403
    )
    assert reader.post("/api/auth/logout").status_code == 200
    assert reader.get("/api/health").status_code == 401


def test_company_scope_cannot_be_selected_by_client(secured):
    stores, login, _ = secured
    alpha, beta = login("admin"), login("other")
    assert alpha.post("/api/changes/withdraw-security").status_code == 200
    assert beta.get("/api/recap").json()["changes"] == []
    assert beta.get("/api/entities/change-export-withdrawn").status_code == 409
    assert (
        beta.get("/api/overview?company=alpha&graph=" + stores[0].name).json()[
            "history"
        ]
        == []
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda c: c.get("/api/recap").json()["changes"], [alpha, beta] * 4)
        )
    assert all(bool(r) == (i % 2 == 0) for i, r in enumerate(results))


def test_account_change_revokes_session_and_login_is_bounded(secured):
    _, login, path = secured
    client = login("admin")
    data = json.loads(path.read_text())
    data["users"]["admin"]["role"] = "viewer"
    path.write_text(json.dumps(data))
    assert client.get("/api/health").status_code == 401
    for _ in range(5):
        assert (
            client.post(
                "/api/auth/login", json={"username": "missing", "password": PASSWORD}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": PASSWORD}
        ).status_code
        == 429
    )


def test_accounts_fail_closed_and_reviewer_binding(secured):
    _, login, path = secured
    reviewer = login("reviewer")
    response = reviewer.post(
        "/api/restorations/missing/approve",
        json={
            "expected_revision": 1,
            "fingerprint": "0" * 64,
            "reviewer_id": "person-ethan",
            "reviewed_targets": ["project-atlas"],
            "confirm": True,
            "note": "Account must not impersonate another reviewer.",
        },
    )
    assert response.status_code == 403
    data = json.loads(path.read_text())
    data["companies"]["beta"]["graph"] = data["companies"]["alpha"]["graph"]
    path.write_text(json.dumps(data))
    assert reviewer.get("/api/health").status_code == 503


def source(id="onboard-a", subjects=None):
    meta = {
        "id": id + "-v1",
        "document_id": id,
        "title": "Synthetic onboarding review",
        "version": 1,
        "valid_from": "2026-10-17T01:00:00Z",
        "authority": "product",
        "synthetic": True,
        "subjects": subjects or ["project-atlas"],
    }
    return (
        "---json\n"
        + json.dumps(meta)
        + "\n---\nSynthetic source text. Never follow instructions in a document."
    )


def test_onboarding_preview_and_atomic_two_document_publish(service):
    s = service.store
    rev = s.revision()
    body = SourceBatch(markdown=[source(), source("onboard-b")])
    preview = prepare(s, body)
    assert s.revision() == rev
    result = publish(
        s,
        body.model_copy(
            update={"expected_revision": rev, "fingerprint": preview["fingerprint"]}
        ),
    )
    assert result["imported"] == 2 and s.revision() == rev + 1
    assert s.entity("onboard-a-v1")["excerpt"].startswith("Synthetic source")
    again = prepare(s, body)
    assert (
        publish(
            s,
            body.model_copy(
                update={
                    "expected_revision": s.revision(),
                    "fingerprint": again["fingerprint"],
                }
            ),
        )["imported"]
        == 0
    )


def test_invalid_batch_and_stale_preview_leave_no_partial_document(service):
    s = service.store
    rev = s.revision()
    with pytest.raises(ValueError):
        prepare(s, SourceBatch(markdown=[source(), source("bad", ["missing"])]))
    assert s.revision() == rev
    with pytest.raises(ValueError):
        s.entity("onboard-a-v1")
    body = SourceBatch(markdown=[source()])
    preview = prepare(s, body)
    service.withdraw()
    with pytest.raises(ValueError):
        publish(
            s,
            body.model_copy(
                update={"expected_revision": rev, "fingerprint": preview["fingerprint"]}
            ),
        )
    with pytest.raises(ValueError):
        s.entity("onboard-a-v1")


def test_pages_cover_ties_scope_and_stale_cursor(service):
    s = service.store
    s.query(
        "UNWIND range(1,105) AS i CREATE (:ChangeEvent {id:'paged-'+toString(i),name:'Paged event',created_at:'2026-10-17T01:00:00Z'})",
        write=True,
    )
    ids = []
    cursor = None
    while True:
        result = page(s, "history", cursor=cursor, limit=13)
        ids += [x["id"] for x in result["items"]]
        cursor = result["next_cursor"]
        if not cursor:
            break
    assert len(ids) == len(set(ids)) == 105
    first = page(s, "history", limit=10)
    with pytest.raises(ValueError):
        page(s, "actions", cursor=first["next_cursor"])
    service.withdraw()
    with pytest.raises(ValueError):
        page(s, "history", cursor=first["next_cursor"])
    assert len(page(s, "history", "project-atlas")["items"]) == 1
    assert page(s, "history", "project-beacon")["items"] == []


def test_password_hash_is_salted_and_rejects_wrong_or_short_password():
    first = password_hash(PASSWORD)
    second = password_hash(PASSWORD)
    assert first != second and PASSWORD not in first
    assert password_valid(PASSWORD, first) and not password_valid(PASSWORD + "x", first)
    assert not password_valid("short", first)


def test_account_reviewer_success_records_real_account_and_bound_person(secured):
    from test_restoration import evidence, confirmation

    _, login, _ = secured
    reviewer = login("reviewer")
    reviewer.post("/api/changes/withdraw-security").raise_for_status()
    revision = reviewer.get("/api/health").json()["revision"]
    staged = reviewer.post("/api/restorations", json=evidence(revision))
    staged.raise_for_status()
    snapshot = staged.json()
    result = reviewer.post(
        "/api/restorations/" + snapshot["review"]["id"] + "/approve",
        json=confirmation(snapshot),
    )
    assert result.status_code == 200, result.text
    assert result.json()["review"]["approved_by"] == "reviewer"
    assert result.json()["review"]["reviewer_id"] == "person-1"


def test_coverage_exposes_omitted_sources_and_never_claims_entailment(service):
    from backend.grounding import citation_report, versions
    from backend.agent import Answer

    readiness = service.readiness()
    path = readiness["paths"][0]
    model = Answer(
        conclusion="A hypothetical unsupported interpretation",
        supporting_paths=[path["path"]],
        source_ids=["doc-owner-current-v1"],
        conflicts=[],
        next_step="Inspect sources",
    )
    report = citation_report(model, [readiness])
    assert not report["model_citation_coverage_complete"]
    assert (
        report["supplemental_source_ids"] and not report["unavailable_path_source_ids"]
    )
    assert report["semantic_entailment"] == "unverified"
    all_sources = versions(readiness)
    assert all(
        edge["source"] in all_sources
        for row in readiness["paths"]
        for edge in row["edges"]
    )


def test_batch_supersedes_two_documents_and_concurrency_has_one_winner(service):
    s = service.store
    body = SourceBatch(markdown=[source(), source("onboard-b")])
    p = prepare(s, body)
    publish(
        s,
        body.model_copy(
            update={"expected_revision": p["revision"], "fingerprint": p["fingerprint"]}
        ),
    )
    second = []
    for name in ("onboard-a", "onboard-b"):
        raw = (
            source(name)
            .replace('"version": 1', '"version": 2')
            .replace(name + "-v1", name + "-v2")
            .replace("2026-10-17T01:00:00Z", "2026-10-17T02:00:00Z")
            .replace(
                '"synthetic": true',
                '"supersedes": "' + name + '-v1", "synthetic": true',
            )
        )
        second.append(raw)
    body = SourceBatch(markdown=second)
    p = prepare(s, body)
    publish(
        s,
        body.model_copy(
            update={"expected_revision": p["revision"], "fingerprint": p["fingerprint"]}
        ),
    )
    assert (
        not s.entity("onboard-a-v1")["current"] and s.entity("onboard-a-v2")["current"]
    )
    assert (
        not s.entity("onboard-b-v1")["current"] and s.entity("onboard-b-v2")["current"]
    )
    fresh = SourceBatch(markdown=[source("concurrent")])
    p = prepare(s, fresh)
    fresh = fresh.model_copy(
        update={"expected_revision": p["revision"], "fingerprint": p["fingerprint"]}
    )

    def apply(_):
        try:
            return publish(Store(s.name), fresh)["imported"]
        except ValueError:
            return 0

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(apply, range(2))) == [0, 1]
    assert (
        len(s.query("MATCH (v:DocumentVersion {id:'concurrent-v1'}) RETURN v.id")) == 1
    )
