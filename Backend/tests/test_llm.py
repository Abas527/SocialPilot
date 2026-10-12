from dataclasses import replace
from types import SimpleNamespace

from pydantic import BaseModel

from core import llm


def test_qwen_request_disables_thinking(monkeypatch):
    monkeypatch.setattr(llm, "settings", replace(llm.settings, llm_model="qwen3.5:4b"))
    captured = {}

    def fake_post(url, *, json, timeout):
        captured.update(url=url, body=json, timeout=timeout)
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"message": {"content": "QWEN_OK"}},
        )

    monkeypatch.setattr(llm.httpx, "post", fake_post)

    assert llm.complete("test prompt") == "QWEN_OK"
    assert captured["url"].endswith("/api/chat")
    assert captured["body"]["model"] == "qwen3.5:4b"
    assert captured["body"]["think"] is False
    assert captured["body"]["stream"] is False


def test_non_qwen_ollama_request_omits_thinking_option(monkeypatch):
    monkeypatch.setattr(llm, "settings", replace(llm.settings, llm_model="llama3.1:8b"))
    captured = {}

    def fake_post(url, *, json, timeout):
        captured.update(body=json)
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"message": {"content": "OK"}},
        )

    monkeypatch.setattr(llm.httpx, "post", fake_post)

    assert llm.complete("test prompt") == "OK"
    assert "think" not in captured["body"]


def test_complete_json_sends_pydantic_schema_to_ollama(monkeypatch):
    class Result(BaseModel):
        ok: bool

    monkeypatch.setattr(
        llm,
        "settings",
        replace(llm.settings, llm_provider="ollama", llm_model="qwen3.5:4b"),
    )
    captured = {}

    def fake_post(url, *, json, timeout):
        captured.update(body=json)
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"message": {"content": '{"ok": true}'}},
        )

    monkeypatch.setattr(llm.httpx, "post", fake_post)

    assert llm.complete_json("Return ok=true.", Result).ok is True
    assert captured["body"]["format"]["type"] == "object"
    assert captured["body"]["format"]["properties"]["ok"]["type"] == "boolean"
    assert captured["body"]["think"] is False


def test_qwen25_coder_request_sets_context_and_omits_thinking(monkeypatch):
    monkeypatch.setattr(
        llm, "settings",
        replace(llm.settings, llm_provider="ollama", llm_model="qwen2.5-coder:7b", llm_num_ctx=8192),
    )
    captured = {}

    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": "ok"}}

    def fake_post(url, json, timeout):
        captured["body"] = json
        return Resp()

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    assert llm.complete("hi") == "ok"
    assert "think" not in captured["body"]
    assert captured["body"]["options"]["num_ctx"] == 8192
