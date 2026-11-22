"""Opt in the active catalog after proxy checks; keep embedding identity untouched."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil


def _move_background_jobs_to_go(out: dict) -> None:
    """Background jobs share the Go allowance; their selection IDs stay put."""
    task = out["services"].get("task")
    if not task or not task.get("active_profile_id"):
        return
    profile = next((p for p in task.get("profiles", []) if p["id"] == task["active_profile_id"]), None)
    if profile is None or profile.get("connection_id") != "conn-litellm":
        return
    model = next((m for m in profile.get("models", []) if m["id"] == task.get("active_model_id")), None)
    if model is None or model.get("model") != "deeptutor-openrouter":
        return
    profile["name"] = "Go DeepSeek V4.1 Flash (via LiteLLM)"
    model.update(
        name="DeepSeek V4.1 Flash (Go)", model="deeptutor-chat",
        context_window=1_000_000, reasoning_effort="max",
    )
    model.setdefault("capabilities", {})["vision"] = True


def proxy_catalog(catalog: dict, local_key: str) -> dict:
    """Keep existing chat selection IDs, and preserve the exact embedding profile."""
    out = deepcopy(catalog)
    profiles = out["services"]["llm"]["profiles"]
    service = out["services"]["llm"]
    main = next(p for p in profiles if p["id"] == service["active_profile_id"])
    model = next(m for m in main["models"] if m["id"] == service["active_model_id"])
    if model["model"] == "deeptutor-chat":
        # Upgrade existing installs without replacing an explicit override.
        model.setdefault("capabilities", {}).setdefault("vision", True)
        _move_background_jobs_to_go(out)
        return out
    if model["model"] != "meta/muse-ember":
        raise ValueError("The active model changed; inspect it before configuring this wrapper.")
    headers = {"x-opencode-session": "__deeptutor_conversation__"}
    connection = {
        "id": "conn-litellm", "name": "LiteLLM local", "provider": "custom",
        "api_key": local_key, "base_url": "http://127.0.0.1:4000/v1",
        "api_format": "openai_chat", "api_version": "", "extra_headers": headers,
    }
    if any(c["id"] == connection["id"] for c in out.get("connections", [])):
        raise ValueError("A conn-litellm connection already exists; do not overwrite it.")
    out.setdefault("connections", []).append(connection)
    original = deepcopy(main)
    for profile in (main, original):
        profile.update(
            binding="custom", connection_id=connection["id"], api_key=local_key,
            base_url=connection["base_url"], api_format="openai_chat",
            wire_api="chat_completions", extra_headers=deepcopy(headers),
        )
    main["name"] = "Go DeepSeek V4.1 Flash (via LiteLLM)"
    model.update(name="DeepSeek V4.1 Flash (Go; OpenRouter on quota exhaustion)", model="deeptutor-chat", context_window=1_000_000, reasoning_effort="max")
    # DeepTutor sees the Custom alias, not the vision-capable upstream model ID.
    model.setdefault("capabilities", {})["vision"] = True
    original["id"] = "llm-profile-litellm-openrouter"
    original["name"] = "OpenRouter Muse Ember (via LiteLLM)"
    original["models"] = [deepcopy(next(m for m in original["models"] if m["id"] == service["active_model_id"]))]
    original["models"][0].update(id="llm-model-litellm-muse", model="deeptutor-openrouter")
    profiles.append(original)
    # Background jobs share the Go allowance instead of paid OpenRouter.
    task = out["services"].setdefault("task", {})
    if not task.get("active_profile_id") and not task.get("profiles"):
        task_profile = deepcopy(main)
        task_profile["id"] = "task-profile-litellm-go"
        task_model = deepcopy(next(m for m in main["models"] if m["id"] == service["active_model_id"]))
        task_model.update(id="task-model-litellm-go", name="DeepSeek V4.1 Flash (Go)")
        task_profile["models"] = [task_model]
        task.update(
            active_profile_id=task_profile["id"],
            active_model_id=task_model["id"], profiles=[task_profile],
        )
    assert out["services"]["embedding"] == catalog["services"]["embedding"]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write only after proxy tests succeed.")
    args = parser.parse_args()
    os.umask(0o077)
    home = Path(os.environ.get("DEEPTUTOR_HOME", str(Path.home() / "deeptutor"))).resolve()
    path = home / "data/user/settings/model_catalog.json"
    catalog = json.loads(path.read_text())
    key = (home / "litellm/proxy.key").read_text().strip()
    out = proxy_catalog(catalog, key)
    if not args.apply:
        print("Dry run: chat and background jobs use Go; embeddings are unchanged.")
        return
    from deeptutor.services.config.model_catalog import ModelCatalogService

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = home / "backups" / f"pre-litellm-go-{stamp}"
    backup.mkdir(mode=0o700, parents=True)
    shutil.copy2(path, backup / path.name)
    start = home / "start.sh"
    if start.exists():
        shutil.copy2(start, backup / "start.sh")
    saved = ModelCatalogService(path).save(out)
    if saved["services"]["embedding"] != catalog["services"]["embedding"]:
        shutil.copy2(backup / path.name, path)
        raise RuntimeError("Embedding config changed during normalization; restored original catalog.")
    print(f"Catalog configured. Private rollback snapshot: {backup}")


if __name__ == "__main__":
    main()
