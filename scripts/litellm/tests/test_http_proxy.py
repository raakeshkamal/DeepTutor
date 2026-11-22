"""Exercise the real proxy process with fake upstreams and fake credentials."""
from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from test_policy import Handler
import yaml


class HttpProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="dt-proxy-test-")
        cls.home = Path(cls.temp.name)
        (cls.home / "data/user/settings").mkdir(parents=True)
        (cls.home / "litellm").mkdir()
        (cls.home / "data/user/settings/model_catalog.json").write_text('{"connections": []}')
        cls.key = "local-test-only"
        (cls.home / "litellm/proxy.key").write_text(cls.key)
        cls.servers = []
        for _ in range(2):
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            server.status, server.message, server.calls, server.headers = 200, "", [], []
            threading.Thread(target=server.serve_forever, daemon=True).start()
            cls.servers.append(server)
        directory = Path(__file__).resolve().parents[1]
        config = yaml.safe_load((directory / "config.yaml").read_text())
        config = deepcopy(config)
        for model, server in zip(config["model_list"], cls.servers):
            model["litellm_params"].update(api_base=f"http://127.0.0.1:{server.server_port}/v1", api_key="upstream-test-only", timeout=5)
        cls.config = cls.home / "proxy.yaml"
        cls.config.write_text(yaml.safe_dump(config))
        with socket.socket() as port:
            port.bind(("127.0.0.1", 0))
            cls.port = port.getsockname()[1]
        cls.log = (cls.home / "proxy.log").open("w")
        cls.process = subprocess.Popen(
            [sys.executable, str(directory / "serve.py")], stdout=cls.log, stderr=cls.log,
            env={**os.environ, "DEEPTUTOR_HOME": str(cls.home), "DEEPTUTOR_LITELLM_CONFIG": str(cls.config), "DEEPTUTOR_LITELLM_PORT": str(cls.port), "OPENROUTER_API_KEY": "upstream-test-only", "OPENCODE_GO_API_KEY": "upstream-test-only"},
        )
        for _ in range(100):
            if cls.process.poll() is not None:
                cls.tearDownClass()
                raise RuntimeError("The offline proxy failed during startup.")
            try:
                r = urllib.request.Request(f"http://127.0.0.1:{cls.port}/v1/models", headers={"Authorization": "Bearer " + cls.key})
                with urllib.request.urlopen(r, timeout=1):
                    return
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        cls.tearDownClass()
        raise RuntimeError("The offline proxy never became ready.")

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            cls.process.wait()
        cls.log.close()
        for server in cls.servers:
            server.shutdown()
            server.server_close()
        cls.temp.cleanup()

    def setUp(self):
        for server in self.servers:
            server.status, server.message = 200, ""
            server.calls.clear()
            server.headers.clear()
        self.primary, self.fallback = self.servers

    def request(self, stream=False):
        data = {"model": "deeptutor-chat", "messages": [{"role": "user", "content": "test"}], "reasoning_effort": "max", "stream": stream}
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/chat/completions", data=json.dumps(data).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key, "x-opencode-session": "dt_offline_test"})
        return urllib.request.urlopen(r, timeout=15)

    def test_session_identity_and_authentication_are_separate(self):
        with self.request() as r:
            self.assertEqual(r.status, 200)
        headers = {k.lower(): v for k, v in self.primary.headers[0].items()}
        self.assertEqual(headers["x-opencode-session"], "dt_offline_test")
        self.assertIn("DeepTutor/", headers["user-agent"])
        self.assertEqual(headers["authorization"], "Bearer upstream-test-only")
        self.assertNotIn(self.key, str(headers))
        self.assertEqual(len(self.fallback.calls), 0)

    def test_streaming_quota_error_uses_exactly_one_fallback(self):
        self.primary.status, self.primary.message = 429, "Go weekly allowance exhausted"
        with self.request(stream=True) as r:
            self.assertIn(b"ok", r.read())
        self.assertEqual(len(self.primary.calls), 1)
        self.assertEqual(len(self.fallback.calls), 1)
        self.assertEqual(self.fallback.calls[0]["reasoning_effort"], "max")

    def test_authentication_failure_is_not_a_paid_fallback(self):
        self.primary.status, self.primary.message = 401, "invalid credential"
        with self.assertRaises(urllib.error.HTTPError):
            self.request()
        self.assertEqual(len(self.primary.calls), 1)
        self.assertEqual(len(self.fallback.calls), 0)


if __name__ == "__main__":
    unittest.main()
