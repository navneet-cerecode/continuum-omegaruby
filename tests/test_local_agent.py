import json
import httpx
import pytest
from backend.agent import run_agent, AgentUnavailable


class Store:
    def revision(self):
        return 1

    def evidence(self, id):
        return [
            {
                "version": {
                    "id": "doc-security-approval-v1",
                    "excerpt": "Recorded review",
                }
            }
        ]


class Service:
    store = Store()


def test_local_json_agent_selects_tools_and_constrains_sources(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "simulated-local-not-live")
    monkeypatch.setenv("LLM_API_STYLE", "ollama_json")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    calls = []

    def handler(r):
        body = json.loads(r.content)
        calls.append(body)
        if len(calls) == 1:
            content = {
                "type": "tool_call",
                "name": "get_decision_evidence",
                "arguments": {"value": "approval-export"},
            }
        else:
            assert body["format"]["properties"]["answer"]["properties"]["source_ids"][
                "items"
            ]["enum"] == ["doc-security-approval-v1"]
            content = {
                "type": "final",
                "answer": {
                    "conclusion": "Review recorded evidence",
                    "supporting_paths": [],
                    "source_ids": ["doc-security-approval-v1"],
                    "conflicts": [],
                    "next_step": "Inspect the review",
                },
            }
        return httpx.Response(200, json={"message": {"content": json.dumps(content)}})

    result = run_agent(Service(), "Inspect the approval", httpx.MockTransport(handler))
    assert len(result["trace"]) == 1


def test_no_key_local_adapter_rejects_remote_endpoint(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "fake")
    monkeypatch.setenv("LLM_API_STYLE", "ollama_json")
    monkeypatch.setenv("LLM_BASE_URL", "https://remote.example")
    with pytest.raises(AgentUnavailable, match="local"):
        run_agent(Service(), "Inspect approval")
