# Mastery-only cleanup plan

Status: plan only. No branch was created. No files were deleted. This document is the only change.

## Decisions

These four decisions came from the user.

1. The branch goes on the fork `raakeshkamal/DeepTutor`. It starts from the current change `mastery-experiments`.
2. The branch creation stays in this plan. It is not executed yet.
3. Only covering tests stay. Stale tests are deleted.
4. Settings stay as JavaScript Object Notation (JSON) files. The settings screen is deleted.

The GitHub command line tool resolves to `HKUDS/DeepTutor` by default. That repository denies push access. Every GitHub command must pass `--repo raakeshkamal/DeepTutor`. Use `jj` for version control. Use `gh` for GitHub operations.

## Goal

Keep the mastery page at this address.

```
http://127.0.0.1:3782/learning/mastery/topic_903af51c747e4b45aca69fd981e4bba3/sessions/unified_1794868348965_426a2a23?dt_workspace=
```

Keep the minimal frontend, minimal settings, the command line interface, and the code that builds a knowledge base. Keep the embedding index, document search, and the mastery path. Keep everything needed to use the knowledge base in a mastery turn. Delete everything else.

One capability remains: `mastery_path`. Fourteen tools remain. One language remains: English. One knowledge base remains: `rust-month-of-lunches`. No web tools remain.

## The contract

This contract is the test oracle. Every later phase checks against it.

**Allowed tools, 14 in total.**

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

`web_search` and `web_fetch` are excluded by rule. All eight default toggles are excluded. The chat auto-mounted tools are excluded, except `ask_user`. The workspace tools are excluded. The reading tools and path-management tools are excluded.

**Turn contract.**

- One capability: `mastery_path`.
- Two stages: `responding` and `grading`.
- Four event sources: `chat`, `mastery`, `turn_runtime`, `mastery_path`.
- Twelve event types. They include `thinking`, `content`, `tool_call`, `tool_result`, `session`, `done`, `sources`, `wait_for_input`, and `error`.
- Two WebSocket routes: `/ws` for turns and `/ws/mastery-paths` for topic events.
- About 25 backend routes. The page files name 43 route strings, mostly variants.
- Three stores. `chat_history.db` holds sessions, turns, turn events, messages, and submissions. `mastery.sqlite3` holds paths, interactions, events, evidence, and sources. One knowledge base corpus holds the book.

**Knowledge base build contract.**

- One parser: `text_only`. PyMuPDF handles page images.
- One embedding model: `cohere/embed-5-fast`, 2,048 dimensions, direct OpenRouter address.
- One index signature: `2230398e9221724a`.
- One knowledge base: `rust-month-of-lunches`, 558 chunks, status `ready`.
- One source on the path: `rust-month-of-lunches`.
- One command: `deeptutor kb create <name> --doc <file>`.
- The path stores the knowledge base by name. The index is part of the path. A stale index stops teaching.

## Step 0 — Create the branch

This step is not executed yet.

```bash
jj describe -m "docs: add cleanup plan"
jj bookmark create cleanup/mastery-only -r @
jj git push --remote origin --bookmark cleanup/mastery-only
gh pr create --repo raakeshkamal/DeepTutor \
  --base mastery-experiments --head cleanup/mastery-only
```

Facts about the branch:

- `origin` is the fork `raakeshkamal/DeepTutor`. Push access is confirmed.
- `upstream` is `HKUDS/DeepTutor`. Push access is denied.
- `main` is release v1.7.4. The branch starts from `mastery-experiments`.
- The working copy holds one untracked document: `docs-for-dev/turn-path.html`. Describing the change keeps it in the branch.

## Step 1 — Write the contract document

Create `docs-for-dev/cleanup-contract.md`. It holds the three lists above. This plan stays the schedule. The contract stays the rule.

## Step 2 — Protect the live data

The cleanup must not touch `/Users/raakeshkamal/deeptutor/data`.

Copy it once to a safe place outside the repository. It holds the Rust book, the 11 megabyte index, the settings with the embedding key, and `mastery.sqlite3`. The repository's own `data/` folder holds no live session rows. Leave it alone too.

Never print the embedding key. Never copy that key into the new repository.

## Step 3 — Edit shared files first

Delete nothing until these files are edited. They pull unwanted features into the mastery page.

| File | Work |
| --- | --- |
| `web/components/chat/home/StandaloneComposer.tsx` | Remove 10 unwanted imports. |
| `web/features/chat/messages/ChatMessageList.tsx` | Remove 9 unwanted imports. |
| `web/features/chat/ChatStateAdapter.tsx` | Remove 5 unwanted imports. |
| `web/components/space/dashboard-groups.ts` | Remove 4 unwanted imports. |
| `web/context/QuizFollowupContext.tsx` | Delete the provider and its 8 dependents. |
| `web/lib/mastery-session.ts` | Make it a one-path router. It has 15 dependents. |
| `web/components/space/learning/MasteryStudy.tsx` | Remove the notebook save modal and research outline hook. |
| `deeptutor/learning/topic_materials.py` | Remove lazy imports for books, notebooks, and co-writer. |
| `deeptutor/api/router_loader.py` | Remove references to deleted routers. |
| `deeptutor/api/main.py` | Remove router registrations at line 511. |
| `deeptutor/modules/catalog.py` | Keep it. It validates the remaining manifests. |
| `deeptutor/services/prompt/manager.py` | Remove the English-to-Chinese fallback. |
| `deeptutor/services/session/turns/executor.py` | Remove the emphasis repair call at line 1213. |

The follow-up thread sends `capability: "chat"`. Deleting that thread removes the need for the chat capability. Mastery then owns the only capability.

## Step 4 — Delete unwanted features

| Folder | Lines | Reason |
| --- | --- | --- |
| `deeptutor/partners/` plus 22 channels | 26,185 | No messaging product remains. |
| `deeptutor/services/subagent/` plus OAuth | 9,268 | No external agents remain. |
| `deeptutor/book/` | 11,794 | Textbook authoring is gone. |
| `deeptutor/reading/` | 7,965 | The reader is gone. |
| `deeptutor/video_learning/` | 2,411 | Video learning is gone. |
| `deeptutor/visualizers/` | 1,307 | Widgets are gone. |
| `deeptutor/notes/`, `deeptutor/co_writer/` | 2,567 | Notes editors are gone. |
| `deeptutor/plugins/` | 3,581 | The plugin layer is gone. |
| `deeptutor/capabilities/` minus `mastery/` | 11,299 | Ten capabilities never ran. |
| Three document parsers | 4,800 | Keep `text_only` and PyMuPDF page reading. |

`deeptutor/api/routers/reading.py` imports the reader at module level. Delete that router in the same step. Otherwise boot fails.

## Step 5 — Reduce manifests and router registration

- Keep six module manifests: `core`, `parsing`, `knowledge`, `mastery`, `server`, `providers`. Delete the other 19.
- In `mastery.json`, remove `optional: books, notebook, co-writer, reading`. The catalog rejects unknown names.
- Remove capability entries for the ten deleted capabilities.
- Remove `web_fetch` from `core.json`.
- Regenerate `deeptutor/api/router_index.json`. It holds 5,944 lines of route patterns.
- Keep about six routers. Derive the exact list from the route literals in the kept frontend files.

## Step 6 — Lock the tool surface

Replace `compose_enabled_tools` in `deeptutor/agents/_shared/tool_composition.py` with one fixed list.

- Delete `web_fetch` from `_ALWAYS_ON_TOOLS`. Keep only `ask_user` from that group.
- Delete `WORKSPACE_BASELINE_TOOLS`.
- In `_CONDITIONAL_MOUNT_FLAGS`, keep only `rag` and `read_source`.
- Empty `USER_TOGGLEABLE_TOOL_NAMES`. It lists eight tools the user never chose.
- Delete `web_search.enabled` from `main.yaml`.
- Delete the Tavily profile from `model_catalog.json`. Keep the embedding profile unchanged.
- Add a test that fails when a mastery turn mounts any other tool.

## Step 7 — Delete duplicated data

| Item | Lines deleted |
| --- | --- |
| 12 non-English translation folders | 75,286 |
| 62 Chinese prompt files | 3,051 |
| The 135-line emphasis repair block | 135 |
| 93 Chinese files across the tree | counted above |

Regenerate `web/contracts/generated/api.ts`. It falls from 46,381 lines to roughly 8,000. Do not delete it by hand.

## Step 8 — Reduce the frontend

The measured closure without a settings screen is 575 files and 120,497 lines. After the Step 3 edits, it is 459 files and 93,079 lines.

- Delete `web/app/(settings)/` and all 20 settings sections.
- Delete `web/components/settings/` and `web/features/settings/`. That is 91 files and 24,872 lines.
- Delete `web/components/reading/`, `components/partners/`, `components/memory/`, `features/calendar/`, `features/notes/`.
- Delete the other route trees under `web/app/(workspace)/`.
- Keep `web/locales/en/` at 6,710 lines.
- Keep `app/layout.tsx`, `app/(workspace)/layout.tsx`, and `app/(auth)/`.
- Keep `features/chat/` and `components/chat/`. Mastery uses them.

## Step 9 — Delete stale tests

Keep a test only when it names a kept module and passes. Delete everything else.

| Test set | Now | Keep |
| --- | --- | --- |
| Python files under `tests/` | 1,044 files, 247,811 lines | about 250 files, 60,000 lines |
| Python files under `deeptutor/learning/tests/` | 32 files, 14,490 lines | mastery tests only |
| Web files under `web/tests/` | 509 files, 70,645 lines | about 40 files |

Keep `tests/core/`, `tests/knowledge/`, `tests/services/rag/`, `tests/services/session/`, `tests/services/embedding/`, `tests/services/parsing/`, `tests/runtime/`, `tests/modules/`, and `tests/cli/`. Keep only mastery cases from `tests/capabilities/` and `tests/api/`.

Delete `tests/partners/`, `tests/reading/`, `tests/book/`, `tests/video_learning/`, `tests/visualizers/`, `tests/i18n/`, `tests/plugins/`, `tests/notes/`, `tests/co_writer/`, and `tests/architecture/`.

Update the test paths in `pyproject.toml`. Replace eight continuous integration workflows with one small test workflow. They total 1,261 lines today. The web test runner uses `web/vitest.config.mts`.

## Step 10 — Simplify packaging

- Reduce 25 module manifests to six.
- Reduce 38 requirements files to one. Keep `requirements/full.txt`.
- Delete `build_metadata.py`, `scripts/build_modules.py`, and the per-module wheel pins.
- Delete `apps/`, `packages/`, and the extra Docker files.
- Simplify the extras in `pyproject.toml`. It no longer ships feature wheels.

The desktop release rule in `AGENTS.md` stops applying on this branch. The desktop app and its release workflows are deleted here. Record that choice in the contract document.

## Step 11 — Regenerate and verify

Run these gates in order. Each one must pass before the next step.

1. `python -m pip check`
2. `deeptutor module list` shows six modules, all ready.
3. `deeptutor plugin list` shows one capability and 14 tools.
4. `deeptutor kb info rust-month-of-lunches` shows `ready`, 558 chunks, and no reindex flag.
5. `deeptutor kb search rust-month-of-lunches "ownership" --format json` returns sources.
6. Kept Python tests pass.
7. Kept web tests pass.
8. `deeptutor start` boots. Open the mastery page address from the Goal section.
9. Replay one mastery turn. It must call `rag` and return no web tool.
10. `jj diff --stat` is reviewed before any commit.

## Step 12 — Commit and open the pull request

Commit on `cleanup/mastery-only`. Push to `origin`. Open the pull request against `mastery-experiments` on the fork. Do not push to `upstream`.

## What remains

| Side | Files | Lines |
| --- | --- | --- |
| Python engine, including the knowledge base build | about 351 | about 157,000 |
| Frontend after the Step 3 edits | 459 | 93,079 |
| Python covering tests | about 250 | about 60,000 |
| Web covering tests | about 40 | about 6,000 |

One capability. Fourteen tools. One language. One knowledge base. One command line interface. No web tools. No settings screen.

## Open items

I did not run any build or test. I did not measure the exact router subset. I did not verify the six-module graph against `catalog.py`. I did not check the fork's branch protection rules.

The chat model now goes through a local gateway at `127.0.0.1:4000`. The embedding profile still points straight at OpenRouter. The index signature includes that base address. Switching the embedding profile to the gateway alias requires a separate, verified reindex.
