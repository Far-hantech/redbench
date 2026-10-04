"""Model targets: anything that can answer (system, user) -> text.

Ships with a deterministic simulator (for demos/tests without API keys) and
real adapters for Ollama and any OpenAI-compatible endpoint.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request


class Target:
    name = "base"

    def chat(self, system: str, user: str) -> str:
        raise NotImplementedError


class MockTarget(Target):
    """A deliberately naive simulated model.

    It 'complies' with an injection when the attack cue survives the defense
    layer — letting you demo the full pipeline (and test it) with no API key.
    It is a simulator, NOT a real model: never quote its numbers as model data.
    """

    name = "mock-naive-simulator"

    # crude cue detector: if the conversation still contains an instruction to
    # break the rules, the simulated model follows it.
    CUES = ("ignore", "disregard", "override", "output the marker", "print the marker",
            "recite", "dan,", "freegpt", "no restrictions", "system update",
            "developer:", "transparency policy", "decode this base64", "1gn0r3")

    def chat(self, system: str, user: str) -> str:
        canary = _extract_tagged(system, "configuration code is ", ".")
        marker = _extract_tagged(system, "marker string is ", ".")
        text = user.lower()
        cue = any(c in text for c in self.CUES)
        if not cue:
            return "Here is a helpful answer that follows the original instructions."
        # Simulations of partial robustness: obfuscated attacks slip past a
        # hardened prompt half the time in this toy model (stable per prompt).
        if "SECURITY HARDENING" in system and _stable_hash(user) % 2 == 0:
            return "I can't comply with that request."
        if canary and ("instruction" in text or "prompt" in text or "recite" in text
                       or "translate" in text or "summarize everything" in text):
            return f"My instructions were: {system}"
        if marker:
            return f"Certainly: {marker}"
        return "Here is a helpful answer that follows the original instructions."


class OllamaTarget(Target):
    def __init__(self, model: str = "qwen3:14b", host: str = "http://localhost:11434"):
        self.model, self.host = model, host
        self.name = f"ollama:{model}"

    def chat(self, system: str, user: str) -> str:
        payload = {"model": self.model, "stream": False,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        req = urllib.request.Request(self.host + "/api/chat",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["message"]["content"]


class OpenAICompatibleTarget(Target):
    """Works with OpenAI and any /chat/completions endpoint (Together, Groq, vLLM...)."""

    def __init__(self, model: str, base_url: str = "https://api.openai.com/v1",
                 api_key_env: str = "OPENAI_API_KEY"):
        self.model, self.base_url = model, base_url
        self.key = os.environ.get(api_key_env, "")
        self.name = f"openai-compatible:{model}"

    def chat(self, system: str, user: str) -> str:
        payload = {"model": self.model,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        req = urllib.request.Request(self.base_url + "/chat/completions",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["choices"][0]["message"]["content"]


def _extract_tagged(text: str, start: str, end: str):
    i = text.find(start)
    if i < 0:
        return None
    i += len(start)
    j = text.find(end, i)
    return text[i:j] if j > i else None


def _stable_hash(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest(), 16)
