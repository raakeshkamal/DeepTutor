"""Start one authenticated, loopback-only LiteLLM instance using local credentials."""
from __future__ import annotations

from importlib.metadata import version
import json
import os
from pathlib import Path
import sys

PINNED_LITELLM = "1.101.0"


def load_credentials(home: Path) -> None:
    """Read the active connections without printing or duplicating upstream keys."""
    catalog = json.loads((home / "data/user/settings/model_catalog.json").read_text())
    connection = next(
        (c for c in catalog.get("connections", []) if c.get("id") == "conn-openrouter"), {}
    )
    router_key = os.environ.get("OPENROUTER_API_KEY") or connection.get("api_key")
    go_key = os.environ.get("OPENCODE_GO_API_KEY")
    if not go_key:
        auth_file = Path.home() / ".pi/agent/auth.json"
        auth = json.loads(auth_file.read_text()) if auth_file.exists() else {}
        go_key = auth.get("oc-go", {}).get("key")
    if not router_key or not go_key:
        raise RuntimeError("Configure both OpenRouter and OpenCode Go credentials before starting.")
    os.environ["OPENROUTER_API_KEY"] = router_key
    os.environ["OPENCODE_GO_API_KEY"] = go_key
    os.environ["DEEPTUTOR_LITELLM_KEY"] = (home / "litellm/proxy.key").read_text().strip()


def main() -> None:
    os.umask(0o077)
    if version("litellm") != PINNED_LITELLM:
        raise RuntimeError(f"This wrapper requires LiteLLM {PINNED_LITELLM}; re-run its policy tests before upgrading.")
    home = Path(os.environ.get("DEEPTUTOR_HOME", str(Path.home() / "deeptutor"))).resolve()
    load_credentials(home)
    # Prevent inherited credentials or debug flags from activating remote logging.
    os.environ["LITELLM_LOG"] = "ERROR"
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    os.environ.pop("DATABASE_URL", None)
    import litellm
    from proxy_hooks import QuotaOnlyRouter

    # Keep the standard proxy and its native streaming/embedding implementations.
    # Only the final decision to spend on fallback is narrowed by this subclass.
    litellm.Router = QuotaOnlyRouter
    config = os.environ.get("DEEPTUTOR_LITELLM_CONFIG", str(Path(__file__).with_name("config.yaml")))
    port = str(int(os.environ.get("DEEPTUTOR_LITELLM_PORT", "4000")))
    sys.argv = ["litellm", "--config", config, "--host", "127.0.0.1", "--port", port, "--num_workers", "1"]
    litellm.run_server()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never include arbitrary exception text: configuration errors can quote credentials.
        print(f"LiteLLM wrapper failed ({type(error).__name__}); check configuration and credentials.", file=sys.stderr)
        raise SystemExit(1)
