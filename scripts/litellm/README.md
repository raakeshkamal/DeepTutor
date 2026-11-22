# Local LiteLLM gateway

This wrapper keeps DeepTutor's existing conversation engine and tools.
It does not run an OpenCode agent or replace mastery behavior.

## Routing

- `deeptutor-chat` calls Go's `deepseek-v4.1-flash` through its OpenAI-compatible endpoint.
- One paid fallback calls OpenRouter's `meta/muse-ember` after an explicit Go allowance rejection.
- Authentication errors, temporary rate limits, timeouts, and server errors do not authorize paid fallback.
- An OpenRouter failure ends the chain. There is no third model.
- `deeptutor-openrouter` still supports explicit OpenRouter calls.
- Background task jobs, including the mastery memory refresh, use `deeptutor-chat`.
- They share the Go allowance with chat and follow the same single paid fallback.
- `deeptutor-embeddings` is available and tested, but the active embedding profile remains direct.

Keep OpenCode Console's **Extra Usage** disabled if exhausted Go requests must reach the OpenRouter fallback.
Otherwise OpenCode can spend its own Console credit before returning an allowance error.
Go usage shares the same allowance as other clients using that subscription.
OpenCode documents coding-agent traffic requirements. A proxy does not change those requirements.

## Preserve the known model settings

DeepSeek V4.1 Flash uses a 1,000,000-token context and supports up to 384,000 output tokens.
The active chat profile explicitly records its context and `max` reasoning effort.
The existing per-agent output limits remain unchanged.

Muse Ember retains its 1,048,576-token context and `max` reasoning setting.
The pinned LiteLLM OpenRouter adapter rejects this model's reasoning parameter.
We therefore use its OpenAI-compatible endpoint explicitly and allow `reasoning_effort` through unchanged.
Do not globally drop unsupported parameters or silently turn reasoning off.
OpenRouter attribution headers are configured on the upstream route.

Cohere remains `cohere/embed-5-fast`, with 2,048 dimensions, through the original OpenRouter connection.
The direct and proxied vectors matched exactly during setup.
However, DeepTutor includes the endpoint URL in its index signature.
Keeping the active embedding profile unchanged preserves every existing index identity.
Do not switch it to the proxy alias without a separate, verified metadata migration.

The former main models were `xiaomi/mimo-v2.6-pro`, then `openai/gpt-6.1-terra`, followed by Muse Ember, then Go's `glm-5.3`.
A spare `z-ai/glm-5.3-flash` was removed before the fork migration.
Terra used a 1,050,000-token context. A saved snapshot records `xhigh` effort.
These are historical settings, not additional fallback routes.

## Existing fork patches

The following commits follow the v1.7.4 base on `mastery-experiments`:

1. `6d4751ae8afc` separates mastery memory generation from the reply budget.
2. `30664f7dd86d` refreshes mastery memory in the background.
3. `86a86476fd8e` avoids rewriting already-visible chat text after an empty round.
4. `e8beb855e65a` grades recent learner replies together.
5. `c907342ed3e8` validates code choices and prevents questions revealing their answers.

The last patch also preserves fenced code in question cards and answer choices.
The gateway leaves these patches and stored learner progress intact.

## Credentials and state

The source checkout supplies code. `DEEPTUTOR_HOME`, normally `~/deeptutor`, supplies private runtime state.
No upstream credentials belong in this directory or its YAML file.

The server reads OpenRouter credentials from `conn-openrouter` in the active runtime catalog.
It reads the Go key from `OPENCODE_GO_API_KEY`, or Pi's `oc-go` credential when that variable is absent.
It reads the local client key from `~/deeptutor/litellm/proxy.key`.
Files created by the wrapper use owner-only permissions.

The proxy listens only on `127.0.0.1:4000` and requires its local key.
The application resolves a hashed conversation identifier at request time.
Different conversations, owners, and workspaces get different identifiers.
Only that identifier is forwarded to Go. The local proxy key is not forwarded.

`proxy.log` records service status. `usage.jsonl` records usage without prompts, responses, or credentials.
Response headers identify the selected upstream with `x-deeptutor-route`.
Read upstream-reported cost and Go allowance separately; they represent different things.
This LiteLLM version strips Go-specific allowance fields from assembled streams.
Those log fields remain null when unavailable. Use OpenCode Console for authoritative allowance tracking.
There is no persistent response cache. Provider-side prompt caching remains available.

## Lifecycle

The wrapper uses the existing uv-managed LiteLLM tool environment, pinned to 1.101.0.
Its small router subclass restricts fallback to allowance errors.
This seam depends on that version. Re-run policy tests before upgrading LiteLLM.

Run the manager with the checkout environment:

```sh
uv run --no-project --python .venv/bin/python python scripts/litellm/manage.py start
uv run --no-project --python .venv/bin/python python scripts/litellm/manage.py status
uv run --no-project --python .venv/bin/python python scripts/litellm/manage.py stop
```

After live proxy checks succeed, configure the catalog explicitly:

```sh
DEEPTUTOR_HOME="$HOME/deeptutor" uv run --no-project --python .venv/bin/python python scripts/litellm/configure.py --apply
```

This creates a private rollback snapshot before changing the catalog.
It preserves existing chat selection IDs and the exact active embedding profile.
The provided `start.sh` template manages both the proxy and DeepTutor.
After taking the configuration snapshot, install it into the runtime home:

```sh
install -m 700 scripts/litellm/start.sh "$HOME/deeptutor/start.sh"
"$HOME/deeptutor/start.sh" restart
```

Restart DeepTutor after changing its settings, and verify the new process and live model resolution.

## Tests

The proxy policy tests use local upstream stubs. They never call paid providers.

```sh
uv run --no-project --python "$HOME/.local/share/uv/tools/litellm/bin/python" python -m unittest discover -s scripts/litellm/tests -v
uv run --no-project --python .venv/bin/python python -m pytest tests/services/llm/test_contextual_session_headers.py tests/services/test_local_litellm_catalog.py
```

Live checks must verify streaming, tool calls, Go billing, OpenRouter reasoning, and existing knowledge retrieval.
Never exhaust real allowance merely to test fallback. Use the local stub tests instead.

## Rollback

Stop DeepTutor before restoring the saved catalog and startup script from the same private snapshot.
Restart the restored direct setup, then stop the proxy with `manage.py stop`.
Do not delete runtime data, indexes, credentials, or the preserved OpenRouter connection.
