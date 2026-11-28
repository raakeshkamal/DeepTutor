# Mastery-only cleanup contract

This document is the rule. `docs-for-dev/CLEANUP_PLAN.md` is the schedule.
Every phase checks against the three lists below. It was created on branch
`cleanup/mastery-only`, based on `mastery-experiments` @ `394a0acee`.

## 1. Allowed tools — 14 total

| Tool | Job |
| --- | --- |
| `mastery_prepare_lesson` | Build the next lesson from the path map. |
| `mastery_status` | Read progress on the current topic. |
| `mastery_quiz` | Pose a graded question. |
| `mastery_assess` | Grade a written explanation. |
| `mastery_grade` | Grade a choice answer. |
| `mastery_note_explained` | Record what the tutor just taught. |
| `mastery_skip_question` | Drop a pending question. |
| `mastery_mode` | Switch between study and review. |
| `mastery_profile` | Read the learner profile. |
| `mastery_defer_objective` | Move an objective later. |
| `mastery_repair_question` | Replace a broken question. |
| `rag` | Search the one knowledge base. |
| `read_source` | Read a passage from that knowledge base. |
| `ask_user` | Pause the loop for the learner's answer. |

Excluded by rule: `web_search` and `web_fetch`; all eight default toggles;
the chat auto-mounted tools except `ask_user`; the workspace tools; the
reading tools and path-management tools. A mastery turn may mount no other
tool.

## 2. Turn contract

- One capability: `mastery_path`.
- Two stages: `responding` and `grading`.
- Four event sources: `chat`, `mastery`, `turn_runtime`, `mastery_path`.
- Twelve event types, including `thinking`, `content`, `tool_call`,
  `tool_result`, `session`, `done`, `sources`, `wait_for_input`, and `error`.
- Two WebSocket routes: `/ws` for turns, `/ws/mastery-paths` for topic events.
- About 25 backend routes. The page files name 43 route strings, mostly variants.
- Three stores: `chat_history.db` (sessions, turns, turn events, messages,
  submissions), `mastery.sqlite3` (paths, interactions, events, evidence,
  sources), and one knowledge base corpus holding the book.

## 3. Knowledge base build contract

- One parser: `text_only`. PyMuPDF handles page images.
- One embedding model: `cohere/embed-5-fast`, 2,048 dimensions, direct
  OpenRouter address.
- One index signature: `2230398e9221724a`.
- One knowledge base: `rust-month-of-lunches`, 558 chunks, status `ready`.
- One source on the path: `rust-month-of-lunches`.
- One command: `deeptutor kb create <name> --doc <file>`.
- The path stores the knowledge base by name. The index is part of the path.
  A stale index stops teaching.

## Recorded decisions and exceptions

- Settings stay as JSON files. The settings screen is deleted.
- Only covering tests stay; stale tests are deleted.
- The branch is pushed to `origin` (`raakeshkamal/DeepTutor`); never to
  `upstream` (`HKUDS/DeepTutor`), which denies push access.
- **Desktop release exception (Step 10).** On this branch the desktop app,
  `apps/desktop/`, and its release workflows are deleted. The desktop release
  rule in `AGENTS.md` (Intel Mac DMG + Apple Silicon DMG + Windows installer
  and portable ZIP for every version, with `verify-release`) therefore stops
  applying on `cleanup/mastery-only`. It still applies on the mainline
  branches. No desktop artifact is published from this branch.

## Environment deviations (recorded, not silently applied)

The plan was written for a macOS workstation with jj and gh. This checkout
is a Linux workspace, so the following substitutions and gaps apply:

| Plan assumption | Observed here | Consequence |
| --- | --- | --- |
| `jj` for version control | not installed; no `.jj` repo; git worktree only | git is used as the fallback; `cleanup/mastery-only` was created with `git checkout -b` at `394a0acee`. |
| `gh` for GitHub operations | not installed; no `GH_TOKEN`/`GITHUB_TOKEN` and no `~/.config/gh/hosts.yml` | PR creation is blocked until credentials are supplied. |
| Untracked `docs-for-dev/turn-path.html` | already tracked in `394a0acee` | Step 0's `jj describe` would have described the wrong change; the plan document is committed on this branch instead. |
| Live data at `/Users/raakeshkamal/deeptutor/data` | path does not exist; no `data/` directory in the repository | Step 2 has nothing to copy in this workspace. No book, index, settings, embedding key, or `mastery.sqlite3` is present. No secret was read or copied. |
| Python toolchain | `python3` 3.13.5 present, but no `pip` and no project dependencies installed | `pip check`, `deeptutor module list`, `deeptutor plugin list`, `deeptutor kb ...`, `deeptutor start`, and the Python tests cannot be executed here. |
| Frontend toolchain | node/npm present, `web/node_modules` absent | `web/contracts/generated/api.ts` regeneration and web tests cannot be executed here. |

Verification gates 1–9 of Step 11 remain **unverified** in this workspace.
They must be run on the workstation that holds the live data before this
branch is merged. Gate 10 (`jj diff --stat`, here `git diff --stat`) is
reviewed before the commit.

## Execution record

| Step | State |
| --- | --- |
| 0 | `cleanup/mastery-only` created at `394a0acee` with `git checkout -b` (jj absent). `mastery-experiments` untouched. Push and PR attempted; see blockers below. |
| 1 | This file. |
| 2 | No live data exists in this workspace; repository `data/` is absent and was never created. No secret was read or copied. |
| 3 | Done for: `mastery-session.ts` (one-path router), `topic_materials.py` (no book/notebook/co-writer lazy imports), `prompt/manager.py` (English only), `executor.py` (emphasis repair call removed), `router_loader.py`/`main.py` (no static router table to edit — registration is manifest-driven via `api/module_routes.py`). **Not done:** the import cleanups in `StandaloneComposer.tsx`, `ChatMessageList.tsx`, `ChatStateAdapter.tsx`, `dashboard-groups.ts`, `MasteryStudy.tsx`, and the `QuizFollowupContext` provider removal — see deviations. |
| 4 | Deleted `partners`, `book`, `reading`, `video_learning`, `visualizers`, `notes`, `co_writer`, `plugins`, `services/subagent`, `services/partners`, `textbook_struct`, and every `capabilities/` subpackage except `mastery`. |
| 5 | Six manifests remain; all six validate against `catalog.manifests()` rules. `mastery.json` optional deps removed, its `tools_used` trimmed to the 14, stages set to `responding` + `grading`. Ten capability/loop/tool entries removed. `web_fetch` removed from `core.json` with the rest of its tool block. Ten router files remain. `router_index.json` reduced from 5,944 lines to a 4-line minimal index. |
| 6 | `compose_enabled_tools` now returns the fixed 14-tool list and ignores every gate/whitelist/forced argument. `_ALWAYS_ON_TOOLS = ("ask_user",)`; `WORKSPACE_BASELINE_TOOLS` deleted; `_CONDITIONAL_MOUNT_FLAGS` holds only `rag` and `read_source`; `USER_TOGGLEABLE_TOOL_NAMES = ()`. New guard test: `tests/runtime/test_mastery_tool_surface.py`. The default capability in `runtime/orchestrator.py` is now `mastery_path`; the partner/subagent hand-off branch is gone. |
| 7 | Non-English `web/locales/*`, Chinese prompt packs and `*CN*` docs removed. `web/contracts/generated/api.ts` **could not be regenerated** (generator needs pydantic/FastAPI) and was deliberately left in place rather than hand-deleted, per the plan. |
| 8 | Settings/reading/partners/memory/calendar/notes/co-writer/admin/utility/handoff route trees removed. `app/layout.tsx`, `app/(auth)/`, `app/(workspace)/layout.tsx`, `learning/mastery/**`, `locales/en/`, `features/chat/` and `components/chat/` kept. |
| 9 | Stale Python and web tests deleted; `pyproject.toml` testpaths updated to the kept directories. Eight CI workflows replaced by one `tests.yml`. |
| 10 | `apps/`, `packages/`, `packaging/`, extra compose/Docker files, `build_metadata.py`, `scripts/build_modules.py` and all requirements files except `requirements/full.txt` removed. Extras reduced to `full = []`. |
| 11 | See verification results below — all runtime gates blocked in this workspace. |
| 12 | Local commit made on `cleanup/mastery-only`; push/PR status recorded in the commit message and final report. |

### Deviations from the plan

* `web/context/QuizFollowupContext.tsx` and its dependents were **kept**. The kept mastery session layout, `ChatWorkspace`, `ChatViewerBridges` and `SessionViewerPanel` import it; deleting it without a TypeScript build would break the mastery page — the one surface the plan says to keep. It adds no capability and no tool.
* The large Step 3 React import cleanups and the `MasteryStudy.tsx` notebook-save/research-outline removals were **not** applied. They require coordinated edits across multi-thousand-line files and a type-check to confirm; no Node dependencies are installed here. The mastery route tree and its `components/`, `hooks/`, `lib/` closure were kept intact for the same reason.
* `deeptutor/tools/`, `deeptutor/agents/` and `deeptutor/services/` keep modules whose classes are still imported by `tools/builtin/__init__.py`; they are registered but the fixed composition never mounts them.
* `main.yaml` and `model_catalog.json` are runtime-settings files under `DEEPTUTOR_HOME`, not repository files. They do not exist in this workspace, so `web_search.enabled` and the Tavily profile could not be edited here. They must be removed on the workstation that holds the live data.
* `api.ts` remains stale (46,381 lines) and `router_index.json` was regenerated with a stdlib minimal index rather than `scripts/build_router_index.py`. A stale fingerprint is ignored by `RouterLoader`, so boot falls back to eager loading.

### Verification results (Step 11)

| Gate | Result |
| --- | --- |
| 1 `python -m pip check` | **Blocked** — no `pip`, no project dependencies installed. |
| 2 `deeptutor module list` | **Blocked** — CLI not installed. Static substitute: six manifests present, catalog rules validated. |
| 3 `deeptutor plugin list` | **Blocked** — CLI not installed. Static substitute: manifests declare exactly `mastery_path` and the 14 contracted tools. |
| 4 `deeptutor kb info rust-month-of-lunches` | **Blocked** — CLI and live KB corpus absent. |
| 5 `deeptutor kb search ...` | **Blocked** — same. |
| 6 Kept Python tests | **Blocked** — no `pytest`. Static substitute: 1,225 remaining `.py` files all compile with `py_compile`; 34 JSON files parse (one pre-existing JSONC `web/tsconfig.node-tests.json` aside); `pyproject.toml` parses with `tomllib`. |
| 7 Kept web tests | **Blocked** — `web/node_modules` and vitest absent. |
| 8 `deeptutor start` + mastery page | **Blocked** — CLI/deps absent. |
| 9 Replay a mastery turn | **Blocked** — same. |
| 10 `jj diff --stat` review | **Done** via the git equivalent: `git diff --stat` reviewed before the commit. |

Static import audit: **zero module-level imports** of deleted packages remain in the Python tree; 24 files still hold lazy/function-level references to deleted features. These are the residual work items for a workstation with the full toolchain.

### Remaining work before merge

1. Run gates 1–9 on the workstation with the live data at `/Users/raakeshkamal/deeptutor/data`.
2. Apply the deferred Step 3 frontend edits with `npm ci --legacy-peer-deps` and `npx tsc --noEmit` available.
3. Regenerate `web/contracts/generated/api.ts` with `scripts/export_frontend_contracts.py` and `router_index.json` with `scripts/build_router_index.py`.
4. Remove `web_search.enabled` from `main.yaml` and the Tavily profile from `model_catalog.json` in the live settings (without exposing the embedding key), then re-verify the `2230398e9221724a` index signature.
5. Open the PR against `mastery-experiments` on `raakeshkamal/DeepTutor` with `--repo raakeshkamal/DeepTutor` once `gh` and credentials are available.

## VPS verification (loopback fixture stack, same branch)

A second pass fixed the startup blockers found by testing the cleanup commit on
this VPS. All work stayed local on `cleanup/mastery-only`; no push and no PR.
Runtime home: `/srv/deeptutor-mastery/home` (isolated, dummy keys only).

### Restored individual files (each required by a retained feature)

| File | Why it was restored |
| --- | --- |
| `web/tests/setup/rendered.ts` | `web/vitest.config.mts` names it as the sole `setupFiles` entry. Without it the retained mastery vitest suite cannot start and the 134 `TS2339` jest-dom matcher errors remain. It is the original harness, unmodified. |
| `web/components/chat/home/AnswerModeMenu.tsx` | `ChatComposer.tsx` and `ComposerTray.tsx`, both used by the mastery composer, import its default export, `PartnerLinkMenu` and the `AnswerModeProps`/`PartnerLinkProps` types. Restored from the pre-cleanup commit with a one-line import change to the mastery-only `NeutralAvatar`. |
| `deeptutor/capabilities/prompts/en/turn_status.yaml` | `runtime/orchestrator.py` loads the `capabilities/turn_status` notice on an incomplete mastery turn. English only; the Chinese pack stays removed. |

### Stale references replaced with mastery-only code

* Packaging: `setup.py` no longer imports the deleted `build_metadata.py`; `pyproject.toml` declares static `project.optional-dependencies`; `requirements/full.txt` is a flat 55-line union of the six retained manifests (no `-r modules/*.txt`); `MANIFEST.in` drops deleted helpers.
* Module readiness: `catalog.source_checkout()` identifies a source checkout by `pyproject.toml` alone; `module_enabled()` returns `False` for legacy probes of deleted modules instead of raising.
* Plugins: `deeptutor_cli/plugin.py`, `runtime/registry/tool_registry.py` and `capability_registry.py` no longer import `deeptutor.plugins.*`; `deeptutor plugin list` now reports the 14 tools and one capability from the registries.
* Orchestrator: the default is `mastery_path`; the partner/subagent hand-off branch is gone.
* Startup: `app/container.py` no longer crashes on `module_enabled("books")`; `api/main.py` ignores calendar/partner background commands; `services/session/_turn_runtime_shared.py` no longer imports the deleted reader.
* Routes: `deeptutor/api/routers/mastery_compat.py` serves **empty** payloads for read-only probes the retained shared shell still makes (`/api/tools`, `/api/partners`, `/api/task-board` was already removed from the layout, etc.). These are compatibility shims, not restored features; no capability, tool or credential is exposed. `router_index.json` was regenerated with the correct fingerprint and no deferred patterns.
* Frontend: 34 missing-module imports removed or replaced by small mastery-only code (`NeutralAvatar`, inert partner navigation, English-only `i18n/init.ts`, notebook/calendar/settings trackers removed from layouts). `RichMarkdownRenderer`/`RichCodeBlock` are now static imports so fenced code in mastery questions renders deterministically.
* Generated contracts: with the backend deps installed, `scripts/export_frontend_contracts.py` refreshed `web/contracts/schema/openapi.json` and `npm run contracts:generate` rebuilt `web/contracts/generated/api.ts` from it (46,381 -> 18,048 lines). `npm run contracts:check` and typecheck pass; the file was regenerated, not hand-deleted.
* Tests: stale tests for deleted features were deleted; mastery-only regressions were kept or rewritten (`mastery-session.test.ts`, `mastery-study-layout.test.ts`, `test_orchestrator.py`, `test_chat_cli.py`, `tests/runtime/test_mastery_tool_surface.py`, `tests/api/test_mastery_compat.py`).

### Verified results

| Gate | Result |
| --- | --- |
| `uv venv` + `uv pip install -r requirements/full.txt` + editable install | OK (`deeptutor==1.7.4`) |
| `deeptutor module list` | 6 modules, all installed/enabled/ready |
| `deeptutor plugin list` / `plugin info mastery_path` | 1 capability (`mastery_path`, stages `responding`+`grading`), 14 tools |
| `python -m pytest -q` (with the API stopped so the runtime lease is free) | **3590 passed, 69 skipped** |
| `npm run typecheck` | **0 errors** (was 172) |
| `npx vitest run` | 19 files, **99 passed** |
| `npm run test:node` | **88/88 passed** |
| LiteLLM 1.101.0 policy + real HTTP proxy tests with fake upstreams | **9/9 passed**; proxy ready in 13.6s under a bounded 45s deadline; failure logs are redacted; fallback policy untouched |
| API + web + proxy + fake upstream startup on `127.0.0.1` | ports 8001 / 3782 / 4000 / 4098 all listening |
| Mastery page (fixture topic) in headless Chromium | HTTP 200, `data-chat-column` present, **0 console errors, 0 4xx/5xx requests** |
| Backend smoke (`/health`, `/api/modules`, `/api/capabilities/registered`, `/api/sessions`, `/api/knowledge-bases`) | HTTP 200 |
| Mastery turn (CLI, fixture LLM through the pinned proxy) | `done` with `status=completed`, streamed content, `tool_call_count=0`, no web tool |
| Tool-surface guard | exactly 14 tools registered and mounted; no `web_search`/`web_fetch`/`exec` |

### Genuine external blockers (not cleanup regressions)

The `rust-month-of-lunches` corpus, its 11 MB index and the `2230398e9221724a`
signature live on the Mac, not on this VPS. No live OpenRouter or OpenCode Go
credentials were supplied or used. Therefore `rag` was not exercised by the
turn, no embedding/KB build was performed, and gates 4/5 (`kb info`,
`kb search`) remain unverified. The Mac `mastery.sqlite3` topic/session rows are
absent, so the exact goal URL renders the route shell rather than the original
session history; a locally created fixture topic proves the route renders.
These are fixture checks, not live provider or live knowledge-base checks.
