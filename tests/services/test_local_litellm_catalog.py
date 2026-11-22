"""Opt-in gateway configuration must not invalidate existing knowledge indexes."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from deeptutor.services.config.model_catalog import ModelCatalogService

_spec = importlib.util.spec_from_file_location(
    "local_gateway_config", Path(__file__).resolve().parents[2] / "scripts/litellm/configure.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
proxy_catalog = _module.proxy_catalog


def catalog():
    return {
        "connections": [{"id": "conn-openrouter", "provider": "openrouter", "api_key": "upstream-placeholder", "base_url": "https://openrouter.ai/api/v1"}],
        "services": {
            "llm": {"active_profile_id": "chat", "active_model_id": "main", "profiles": [{"id": "chat", "binding": "openrouter", "connection_id": "conn-openrouter", "models": [{"id": "main", "model": "meta/muse-ember", "context_window": 1048576, "reasoning_effort": "max"}]}]},
            "embedding": {"active_profile_id": "emb", "active_model_id": "cohere", "profiles": [{"id": "emb", "binding": "openrouter", "connection_id": "conn-openrouter", "base_url": "https://openrouter.ai/api/v1/embeddings", "models": [{"id": "cohere", "model": "cohere/embed-5-fast", "dimension": 2048}]}]},
            "task": {"active_profile_id": None, "active_model_id": None, "profiles": []},
        },
    }


def test_keeps_embedding_identity_and_saved_chat_selection():
    before = catalog()
    original = deepcopy(before)
    after = proxy_catalog(before, "local-placeholder")
    assert before == original
    assert after["services"]["embedding"] == before["services"]["embedding"]
    chat = after["services"]["llm"]
    assert (chat["active_profile_id"], chat["active_model_id"]) == ("chat", "main")
    main = next(p for p in chat["profiles"] if p["id"] == "chat")
    assert main["models"][0]["model"] == "deeptutor-chat"
    assert main["models"][0]["capabilities"]["vision"] is True
    assert main["models"][0]["context_window"] == 1000000
    assert main["models"][0]["reasoning_effort"] == "max"
    assert main["wire_api"] == "chat_completions"
    assert after["connections"][0] == before["connections"][0]
    task_model = after["services"]["task"]["profiles"][0]["models"][0]
    assert task_model["model"] == "deeptutor-chat"
    assert task_model["context_window"] == 1000000


def test_catalog_normalization_preserves_embeddings(tmp_path):
    service = ModelCatalogService(tmp_path / "models.json")
    before = service.save(catalog())
    after = service.save(proxy_catalog(before, "local-placeholder"))
    assert after["services"]["embedding"] == before["services"]["embedding"]
    assert after["services"]["llm"]["profiles"][0]["models"][0]["capabilities"]["vision"] is True


def test_existing_gateway_catalog_gets_only_the_missing_vision_override():
    expected = proxy_catalog(catalog(), "local-placeholder")
    model = expected["services"]["llm"]["profiles"][0]["models"][0]
    model["capabilities"]["tools"] = True
    before = deepcopy(expected)
    before["services"]["llm"]["profiles"][0]["models"][0]["capabilities"].pop("vision")
    assert proxy_catalog(before, "local-placeholder") == expected
    assert "vision" not in before["services"]["llm"]["profiles"][0]["models"][0]["capabilities"]

    model["capabilities"]["vision"] = False
    assert proxy_catalog(expected, "local-placeholder") == expected


def test_repeated_apply_does_not_duplicate_profiles():
    first = proxy_catalog(catalog(), "local-placeholder")
    assert proxy_catalog(first, "local-placeholder") == first


def test_does_not_overwrite_another_main_model():
    data = catalog()
    data["services"]["llm"]["profiles"][0]["models"][0]["model"] = "another-model"
    with pytest.raises(ValueError, match="active model changed"):
        proxy_catalog(data, "local-placeholder")


def test_upgraded_background_jobs_move_to_go_with_stable_ids():
    before = proxy_catalog(catalog(), "local-placeholder")
    task = before["services"]["task"]
    # The earlier release pinned background jobs to OpenRouter Muse Ember.
    task["profiles"][0]["models"][0].update(model="deeptutor-openrouter", context_window=1048576)
    after = proxy_catalog(before, "local-placeholder")
    assert after["services"]["task"]["active_profile_id"] == task["active_profile_id"]
    assert after["services"]["task"]["active_model_id"] == task["active_model_id"]
    task_model = after["services"]["task"]["profiles"][0]["models"][0]
    assert task_model["model"] == "deeptutor-chat"
    assert task_model["context_window"] == 1000000


def test_foreign_background_model_is_left_alone():
    before = proxy_catalog(catalog(), "local-placeholder")
    before["services"]["task"]["profiles"][0]["models"][0]["model"] = "another-provider/model"
    after = proxy_catalog(before, "local-placeholder")
    model = after["services"]["task"]["profiles"][0]["models"][0]
    assert model["model"] == "another-provider/model"
