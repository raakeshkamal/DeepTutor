"""Local policy for the pinned LiteLLM proxy; never record message bodies or keys."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import litellm
from litellm.integrations.custom_logger import CustomLogger

logger = logging.getLogger(__name__)


def is_go_allowance_exhausted(error: Exception) -> bool:
    """Only an explicit Go usage-limit rejection authorizes paid fallback."""
    if getattr(error, "status_code", None) not in {402, 403, 429}:
        return False
    message = str(error).lower()
    return any(term in message for term in (
        "allowance", "usage limit", "usage_limit", "quota", "monthly limit",
        "weekly limit", "5-hour limit", "5 hour limit", "subscription limit",
    ))


class QuotaOnlyRouter(litellm.Router):
    """Keep LiteLLM's own routing, but restrict its one paid fallback.

    This overrides a version-sensitive router seam. serve.py pins the version;
    tests exercise it with actual proxy requests, including streamed failures.
    """

    async def async_function_with_fallbacks_common_utils(
        self, e, disable_fallbacks, fallbacks, context_window_fallbacks,
        content_policy_fallbacks, model_group, args, kwargs,
        include_fallback_errors=False,
    ):
        if model_group != "deeptutor-chat" or not is_go_allowance_exhausted(e):
            raise e
        logger.warning("Go allowance exhausted; using paid OpenRouter for this request.")
        return await super().async_function_with_fallbacks_common_utils(
            e, disable_fallbacks, fallbacks, context_window_fallbacks,
            content_policy_fallbacks, model_group, args, kwargs,
            include_fallback_errors=include_fallback_errors,
        )


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    return value.model_dump() if hasattr(value, "model_dump") else {}


class ProxyObserver(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        # Forward only the session identifier, never a client's authentication.
        if data.get("model") == "deeptutor-chat":
            incoming = (data.get("proxy_server_request") or {}).get("headers") or {}
            incoming = {k.lower(): v for k, v in incoming.items()}
            session = incoming.get("x-opencode-session", "")
            if not session or session == "__deeptutor_conversation__":
                from fastapi import HTTPException
                raise HTTPException(400, "A resolved x-opencode-session is required.")
            headers = dict(data.get("extra_headers") or {})
            headers["x-opencode-session"] = session
            data["extra_headers"] = headers
        return data

    async def async_pre_call_deployment_hook(self, kwargs, call_type):
        headers = dict(kwargs.get("extra_headers") or {})
        if str(kwargs.get("api_base", "")).startswith("https://opencode.ai/") or kwargs.get("model") in {"deepseek-v4.1-flash", "openai/deepseek-v4.1-flash"}:
            headers["User-Agent"] = "DeepTutor/1.7.4 (LiteLLM gateway)"
        else:
            headers = {k: v for k, v in headers.items() if k.lower() != "x-opencode-session"}
        kwargs["extra_headers"] = headers
        return kwargs

    async def async_post_call_response_headers_hook(
        self, data, user_api_key_dict, response, request_headers=None, litellm_call_info=None,
    ):
        info = litellm_call_info or {}
        base = str(info.get("api_base") or "")
        model_id = str((info.get("model_info") or {}).get("id") or "")
        if "opencode.ai" in base or model_id == "deeptutor-go-deepseek":
            route = "go"
        elif "openrouter.ai" in base or model_id.startswith("deeptutor-openrouter-") or info.get("custom_llm_provider") == "openrouter":
            route = "openrouter"
        else:
            return None
        return {"x-deeptutor-route": route}

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        # Stream assembly in this LiteLLM version drops Go-specific usage.
        # Keep those fields null when unavailable; do not fabricate allowance.
        usage = _as_dict(getattr(response_obj, "usage", None))
        self._record_usage(getattr(response_obj, "model", ""), usage, kwargs.get("response_cost"))

    def _record_usage(self, model, usage, response_cost=None):
        opencode = usage.get("opencode") or {}
        record = {
            "model": model,
            "billing_source": opencode.get("billing_source"),
            "go_allowance": opencode.get("allowance"),
            "cost": usage.get("cost", response_cost),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        }
        # The directory and file are created with owner-only permissions.
        home = Path(os.environ.get("DEEPTUTOR_HOME", str(Path.home() / "deeptutor")))
        path = home / "litellm" / "usage.jsonl"
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "a") as output:
            output.write(json.dumps(record) + "\n")


observer = ProxyObserver()
