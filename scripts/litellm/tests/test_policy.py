"""Offline integration tests; both upstreams are local stubs, never real accounts.

Run with the pinned LiteLLM interpreter and Python's standard unittest runner.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
import unittest

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import litellm
from proxy_hooks import QuotaOnlyRouter
import yaml

litellm.suppress_debug_info = True
litellm.turn_off_message_logging = True
litellm.redact_messages_in_exceptions = True


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        self.server.calls.append(body)
        if hasattr(self.server, "headers"):
            self.server.headers.append(dict(self.headers))
        status, message = self.server.status, self.server.message
        if status != 200:
            payload = json.dumps({"error": {"message": message, "type": "error", "code": "test_error"}}).encode()
            kind = "application/json"
        elif body.get("stream"):
            chunk = {"id": "test", "object": "chat.completion.chunk", "created": 0, "model": "test", "choices": [{"index": 0, "delta": {"content": "ok"}, "finish_reason": None}]}
            payload = ("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode()
            kind = "text/event-stream"
        else:
            payload = json.dumps({"id": "test", "object": "chat.completion", "created": 0, "model": "test", "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}}).encode()
            kind = "application/json"
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_):
        pass


class PolicyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.servers = []
        for _ in range(2):
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            server.status, server.message, server.calls = 200, "", []
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.servers.append(server)
        self.primary, self.fallback = self.servers
        config = yaml.safe_load(Path(__file__).resolve().parents[1].joinpath("config.yaml").read_text())
        models = deepcopy(config["model_list"][:2])
        for model, server in zip(models, self.servers):
            model["litellm_params"].update(api_base=f"http://127.0.0.1:{server.server_port}/v1", api_key="test-placeholder", timeout=5)
        self.router = QuotaOnlyRouter(model_list=models, **{**config["router_settings"], "timeout": 5, "stream_timeout": 5})

    async def asyncTearDown(self):
        self.router.reset()
        for server in self.servers:
            server.shutdown()
            server.server_close()

    async def call(self, stream=False):
        response = await self.router.acompletion(model="deeptutor-chat", messages=[{"role": "user", "content": "test"}], stream=stream, reasoning_effort="max")
        if stream:
            return "".join([c.choices[0].delta.content or "" async for c in response if c.choices])
        return response.choices[0].message.content

    async def test_healthy_go_does_not_call_openrouter(self):
        self.assertEqual(await self.call(), "ok")
        self.assertEqual(len(self.primary.calls), 1)
        self.assertEqual(len(self.fallback.calls), 0)

    async def test_explicit_quota_exhaustion_calls_openrouter_once(self):
        self.primary.status, self.primary.message = 429, "Go usage limit exceeded: weekly allowance"
        self.assertEqual(await self.call(), "ok")
        self.assertEqual(len(self.primary.calls), 1)
        self.assertEqual(len(self.fallback.calls), 1)
        self.assertEqual(self.fallback.calls[0]["model"], "meta/muse-ember")
        self.assertEqual(self.fallback.calls[0]["reasoning_effort"], "max")

    async def test_streaming_quota_fallback(self):
        self.primary.status, self.primary.message = 429, "Go monthly quota exhausted"
        self.assertEqual(await self.call(stream=True), "ok")
        self.assertEqual(len(self.fallback.calls), 1)

    async def test_openrouter_failure_ends_the_chain(self):
        self.primary.status, self.primary.message = 429, "Go allowance exhausted"
        self.fallback.status, self.fallback.message = 500, "test upstream failure"
        with self.assertRaises(Exception):
            await self.call()
        self.assertEqual(len(self.primary.calls), 1)
        self.assertEqual(len(self.fallback.calls), 1)

    async def test_other_go_errors_never_spend_openrouter_credit(self):
        for status, message in [(401, "invalid credentials"), (403, "privacy restriction"), (500, "upstream failure"), (429, "temporary rate limit")]:
            with self.subTest(status=status):
                self.primary.status, self.primary.message = status, message
                with self.assertRaises(Exception):
                    await self.call()
                self.assertEqual(len(self.fallback.calls), 0)


if __name__ == "__main__":
    unittest.main()
