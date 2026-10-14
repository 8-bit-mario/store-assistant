# Store Assistant — TDD Implementation Plan

Source of truth: [spec.md](spec.md). Section references (§) point there.

## 1. Blueprint

The system is built bottom-up, from pure functions to the UI. Every layer is tested before the
next one depends on it.

```
ui/app.py (Streamlit)
   │  uses
conversation/turns.py (turn handler: new message vs resume, passphrase check, cancel, metadata)
   │  drives
agent/graph.py (LangGraph state machine + SqliteSaver)
   │  nodes use
agent/classify.py (LLM)   storage/* (SQLite)   validation/*   security/passphrase.py
                          conversation/cancellation.py (keywords, inactivity_status)
config.py (env, fail fast)
```

Build order:

1. **Foundation:** project scaffold, tooling, config.
2. **Pure domain:** phone and name validation, passphrase check, cancel keywords, inactivity
   timing.
3. **Persistence:** schema, store repository, summary repository.
4. **Agent core:** state types, routing functions, LLM classifier.
5. **Graph, grown one path at a time:** chat and off-topic paths first, then a turn handler
   wrapped around it, then ending and summaries, save, overwrite, lookup with passphrase, and
   cancellation.
6. **UI:** chat, then prompts, passphrase field and Cancel button, then URL resume and
   read-only ended threads, then the inactivity fragment.
7. **End-to-end and tracing:** `AppTest` scenarios, a passphrase-leak check across artifacts,
   README.

## 2. Chunks → steps

The first pass produced 7 chunks (the build order above). The second pass split them into the
steps below. In review, I checked each step for three things:

- (a) it adds one testable behaviour;
- (b) it is reachable from code that already exists, so no step leaves orphaned code;
- (c) it fits in a single focused session.

The graph was the riskiest chunk, so it is split by conversation path. Each path is wired into
the graph and the turn handler in the step that adds it.

| # | Step | Test types | LLM? |
|---|---|---|---|
| 1 | Scaffold and tooling | lint + unit | no |
| 2 | Config loading, fail fast | unit | no |
| 3 | Phone validation | unit | no |
| 4 | Store name validation | unit | no |
| 5 | Passphrase check | unit | no |
| 6 | Cancel keywords + `inactivity_status` | unit | no |
| 7 | Database schema + connection | unit | no |
| 8 | Store repository | unit | no |
| 9 | Summary repository | unit | no |
| 10 | State types + routing functions | unit | no |
| 11 | LLM classifier | integration | yes |
| 12 | Graph v1: classify → capability / off-topic redirect | integration | yes |
| 13 | Turn handler v1: new messages, metadata, transcript | integration | yes |
| 14 | Ending: `summarize_and_end` (done + off-topic 3) | integration | yes |
| 15 | Save flow: name/phone interrupts, reprompt, persist | integration | yes |
| 16 | Save flow: overwrite confirmation | integration | yes |
| 17 | Lookup flow + passphrase check in turn handler | integration | yes |
| 18 | Cancellation: keyword, `cancel_operation`, expired-on-load | integration | yes |
| 19 | Streamlit v1: chat + prompts + passphrase field + Cancel | e2e | yes |
| 20 | Streamlit v2: URL thread, resume, new conversation, read-only end | e2e | yes |
| 21 | Streamlit v3: inactivity fragment | unit + e2e | partly |
| 22 | Full e2e scenarios, passphrase-leak check, README | e2e | yes |

## 3. Ground rules (every prompt)

Every prompt below assumes these rules. The code-generation LLM must follow them.

- Work on branch `feature/store-assistant`. Commit at the end of each step with a
  conventional message (`feat(scope): …`, `test(scope): …`). Commits carry no AI attribution.
  Never change git identity. Never commit `.env`, `.claude/` or `data/`.
- **Strict TDD:** write the failing test, run it and see it fail for the right reason, write the
  minimum code to pass, run it green, then refactor.
- Add dependencies with `uv add` / `uv add --dev` only, never by editing `pyproject.toml`.
- Every code file starts with two lines: `# ABOUTME: …`.
- Python style: type hints everywhere, Google docstrings on public functions, ruff line length
  100, files under 500 lines, functions under 50.
- Tests live in a `tests/` folder next to the code they test. No mocks. Tests that call OpenAI
  are marked `@pytest.mark.llm`. Assert on state, DB rows and interrupt kinds, never on exact LLM
  wording.
- Never print or `cat` `.env`. To check a variable exists, count it (for example
  `rg -c '^OPENAI_MODEL=' .env`).
- Verify before claiming done: run `uv run pytest`, `uv run ruff check .`,
  `uv run ruff format --check .` and `uv run mypy src/`. Output must be clean.
- Use `rg`, not `grep` or `find`.

---

## 4. Prompts

### Step 1 — Scaffold and tooling

```text
Read spec.md (§1, §10) and plan.md §3 (ground rules).

Set up the Python project in the repo root (/Users/dev/Repos/TakeHome), on branch
feature/store-assistant.

1. `uv init --package --name store-assistant` (src layout, package `store_assistant`). Keep the
   Python version uv picks (3.14). Only pin 3.12/3.13 if a later dependency fails to install.
2. Runtime deps: `uv add langgraph langgraph-checkpoint-sqlite langchain-openai langsmith
   streamlit python-dotenv`.
   Dev deps: `uv add --dev pytest ruff mypy`.
3. Configure in pyproject.toml *via tool sections only* (these are config, not dependencies):
   - [tool.ruff] line-length = 100, sensible rule set (E, F, I, UP, B).
   - [tool.pytest.ini_options] testpaths = ["src"], markers = ["llm: calls the real OpenAI API"],
     filterwarnings = ["error"] so warnings fail tests (relax only for named third-party
     warnings, with a comment explaining why).
   - [tool.mypy] strict = true for src/.
4. Add `data/` to .gitignore.
5. Add a trivial `src/store_assistant/tests/test_package.py` that imports `store_assistant`.
6. Every code file gets the two ABOUTME lines (including __init__.py).

Verify: uv run pytest, ruff check, ruff format --check, mypy — all clean.
Commit: "chore: scaffold project with tooling".
```

### Step 2 — Config

```text
Read spec.md §2 and plan.md §3.

Create src/store_assistant/config.py with:
- A frozen dataclass `Settings` with fields: openai_model, store_lookup_passphrase,
  data_dir (pathlib.Path, default "data"), check_in_after and expire_after (timedelta,
  defaults 60 s / 90 s, from STORE_ASSISTANT_CHECK_IN_SECONDS / STORE_ASSISTANT_EXPIRE_SECONDS;
  non-integer, non-positive, or expire <= check-in raises a clear configuration error). (OPENAI_API_KEY and LANGSMITH_* are read by the
  libraries from the environment; Settings only *checks* they are present.)
- `class MissingSettingError(Exception)` whose message names the missing variable(s), never
  any value.
- `load_settings(environ: Mapping[str, str]) -> Settings` — pure, takes the mapping, raises
  MissingSettingError listing ALL missing required vars: OPENAI_API_KEY, OPENAI_MODEL,
  STORE_LOOKUP_PASSPHRASE, LANGSMITH_API_KEY, LANGSMITH_TRACING, LANGSMITH_PROJECT. Empty string
  counts as missing. STORE_ASSISTANT_DATA_DIR optional.
- `get_settings() -> Settings` — calls `dotenv.load_dotenv()` then `load_settings(os.environ)`.

TDD in src/store_assistant/tests/test_config.py (pass plain dicts, no monkeypatching needed):
- all present → Settings with correct values; default data_dir.
- one missing → error names it; several missing → all named.
- empty string treated as missing.
- error message never contains any provided value (assert a sentinel value is absent).
- Settings repr must not reveal the passphrase: use `field(repr=False)` and test it.

Add the passphrase confinement guard (spec §6) in
src/store_assistant/tests/test_passphrase_confinement.py. It parses every .py file under
src/store_assistant with `ast`, skipping `tests/` folders and `conftest.py`. It fails if any file
other than `config.py` and `conversation/turns.py` contains an attribute access
`.store_lookup_passphrase` or the string literal "STORE_LOOKUP_PASSPHRASE". The failure message
names each offending file and line. This makes it structurally impossible for nodes, prompts or
the UI to see the secret. Prove the guard works: add a temporary file that reads
`settings.store_lookup_passphrase`, watch the test fail, then delete the file.

Also create src/store_assistant/conftest.py with an autouse session fixture that sets
os.environ["LANGSMITH_PROJECT"] = "store-assistant-tests" after load_dotenv, so all test traces
go to the tests project (spec §9). Load .env there so LLM tests have keys.

Verify all checks. Commit: "feat(config): load and validate settings with passphrase guard".
```

### Step 3 — Phone validation

```text
Read spec.md §4.1 and plan.md §3.

Create src/store_assistant/validation/phone.py:
- `class InvalidPhoneError(ValueError)` with a user-facing `reason` attribute (e.g.
  "needs 10 digits", "area code can't start with 0 or 1", "exchange can't start with 0 or 1").
- `normalize_us_phone(raw: str) -> str` returning E.164 "+1NPANXXXXXX" or raising
  InvalidPhoneError.

TDD in validation/tests/test_phone.py with pytest.mark.parametrize:
- valid: "(555) 234-5678", "555-234-5678", "555.234.5678", "5552345678", "+1 555 234 5678",
  "1-555-234-5678", "  555 234 5678  " → "+15552345678".
- invalid: "", "abc", "555-1234" (7 digits), "25552345678" (11 digits not starting with 1),
  "123-456-7890" (area code starts 1), "055-234-5678", "555-034-5678", "555-134-5678",
  "+44 20 7946 0958", "555-234-56789" — each asserting the specific reason.
Note: letters mixed in ("555-CALL-NOW") are invalid; don't translate vanity numbers.

Verify all checks. Commit: "feat(validation): normalize and validate US phone numbers".
```

### Step 4 — Store name validation

```text
Read spec.md §4.2 and plan.md §3.

Create src/store_assistant/validation/store_name.py:
- `class InvalidStoreNameError(ValueError)` with `reason`.
- `clean_store_name(raw: str) -> str` — trims; raises if empty or > 100 chars after trimming.
- `normalize_store_name(name: str) -> str` — lowercase, trim, collapse internal whitespace.

TDD in validation/tests/test_store_name.py:
- "  Trader Joe's " → "Trader Joe's"; "" and "   " rejected; 100 chars ok, 101 rejected.
- normalize: "Trader Joe's" and "  trader   JOE'S " both → "trader joe's".

Verify all checks. Commit: "feat(validation): clean and normalize store names".
```

### Step 5 — Passphrase check

```text
Read spec.md §6 and plan.md §3.

Create src/store_assistant/security/passphrase.py:
- `is_correct_passphrase(attempt: str, expected: str) -> bool` using hmac.compare_digest on
  UTF-8 bytes. Attempt is stripped of surrounding whitespace; comparison is case-sensitive.
  Empty expected → raise ValueError (misconfiguration, fail fast).

TDD in security/tests/test_passphrase.py: exact match true; wrong, case-different, empty
attempt false; surrounding whitespace tolerated; non-ASCII passphrase works; empty expected
raises.

Verify all checks. Commit: "feat(security): constant-time passphrase check".
```

### Step 6 — Cancel keywords and inactivity timing

```text
Read spec.md §5.6, §5.7 and plan.md §3.

Create src/store_assistant/conversation/cancellation.py:
- Thresholds are parameters (from Settings, spec §2), not module constants.
- `is_cancel_request(text: str) -> bool` — trimmed, lowercased, trailing punctuation (.!) removed,
  in {"cancel", "stop", "never mind", "nevermind"}.
- `InactivityStatus = Literal["active", "check_in", "expired"]`
- `inactivity_status(asked_at: datetime, now: datetime, check_in_after: timedelta,
  expire_after: timedelta) -> InactivityStatus` — datetimes must be timezone-aware (raise
  ValueError otherwise).

TDD in conversation/tests/test_cancellation.py:
- keywords: "cancel", " Cancel ", "STOP!", "never mind", "nevermind." → True;
  "cancel my order at Costco", "don't stop", "" → False.
- timing boundaries with fixed datetimes and 60s/90s thresholds: 0s, 59s → active;
  60s, 89s → check_in; 90s, 600s → expired; naive datetime raises; a 1s/2s pair works too.

Verify all checks. Commit: "feat(conversation): cancel keywords and inactivity timing".
```

### Step 7 — Database schema and connection

```text
Read spec.md §3.1 and plan.md §3.

Create src/store_assistant/storage/database.py:
- `connect(path: Path) -> sqlite3.Connection` — creates parent dir, opens with
  check_same_thread=False (Streamlit runs callbacks on other threads), row_factory=sqlite3.Row,
  enables foreign_keys, and calls `create_schema`.
- `create_schema(conn)` — idempotent CREATE TABLE IF NOT EXISTS for `stores` and
  `conversation_summaries` exactly as in spec §3.1 (including UNIQUE and CHECK constraints).
- `utc_now_iso() -> str` helper for timestamps.

Add a `db_path` fixture (tmp_path / "store_assistant.sqlite") to src/store_assistant/conftest.py.

TDD in storage/tests/test_database.py: tables exist after connect; create_schema twice is
safe; UNIQUE on name_normalized enforced; CHECK on end_reason enforced; parent dir created.

Verify all checks. Commit: "feat(storage): sqlite connection and schema".
```

### Step 8 — Store repository

```text
Read spec.md §3.1, §4, §5.2, §5.3 and plan.md §3.

Create src/store_assistant/storage/stores.py:
- `@dataclass(frozen=True) class Store: store_id, name, phone, created_at, updated_at`.
- `class StoreRepository` taking a connection:
  - `find_by_name(name: str) -> Store | None` (normalizes via normalize_store_name)
  - `add(name: str, phone: str) -> Store` (expects already-cleaned name and E.164 phone; raises
    `DuplicateStoreError` if the normalized name exists)
  - `update_phone(name: str, phone: str) -> Store` (bumps updated_at; raises
    `StoreNotFoundError` if absent)
All SQL parameterized. Repository does not validate phone format (callers pass normalized
values) — but test that it round-trips exactly.

TDD in storage/tests/test_stores.py with the real DB from the db_path fixture:
- add then find (case/space-insensitive find); find miss → None; duplicate add raises;
  update_phone changes phone and updated_at, keeps created_at and original display name;
  update on missing raises; a name containing quotes ("Trader Joe's") round-trips.

Verify all checks. Commit: "feat(storage): store repository".
```

### Step 9 — Summary repository

```text
Read spec.md §3.1, §5.5 and plan.md §3.

Create src/store_assistant/storage/summaries.py:
- `EndReason = Literal["user_done", "off_topic"]`
- `@dataclass(frozen=True) class ConversationSummary: conversation_summary_id, thread_id,
  summary, end_reason, created_at`
- `class SummaryRepository`: `add(thread_id, summary, end_reason) -> ConversationSummary`,
  `find_by_thread(thread_id) -> ConversationSummary | None`.

TDD in storage/tests/test_summaries.py: add + find; find miss; invalid end_reason rejected by
the DB CHECK (sqlite3.IntegrityError) — test through the repository.

Verify all checks. Commit: "feat(storage): conversation summary repository".
```

### Step 10 — State types and routing

```text
Read spec.md §5.1, §5.4, §7.1, §7.2 and plan.md §3.

Create src/store_assistant/agent/state.py with TypedDicts:
- `Intent = Literal["save", "lookup", "done", "off_topic", "on_topic_chat"]`
- `Classification(TypedDict)`: intent, store_name: str | None, phone: str | None
- `ActionKind = Literal["saved", "updated", "kept_existing", "lookup_found",
  "lookup_not_found", "lookup_cancelled_passphrase", "cancelled_by_user", "cancelled_timeout"]`
- `Action(TypedDict)`: kind, store_name: str | None, phone: str | None
- `AssistantState(TypedDict)`: messages (Annotated add_messages), actions (Annotated
  operator.add), off_topic_streak, classification, end_reason, ended.
- `OFF_TOPIC_LIMIT = 3`

Create src/store_assistant/agent/routing.py with pure functions:
- `route_after_classify(state) -> str` returning the node name for each intent:
  "save_store", "lookup_store", "answer_capability", "handle_off_topic", "summarize_and_end".
- `next_off_topic_streak(intent, current) -> int` (off_topic → +1, anything else → 0).
- `route_after_off_topic(state) -> str` → "summarize_and_end" when streak >= OFF_TOPIC_LIMIT
  else END.

TDD in agent/tests/test_routing.py: every intent maps to its node; streak increments and
resets; route_after_off_topic at 2 vs 3.

Verify all checks. Commit: "feat(agent): state types and routing rules".
```

### Step 11 — LLM classifier

```text
Read spec.md §5.1 and plan.md §3. Use the langgraph-fundamentals and langchain-dependencies
skills for current API usage.

Create src/store_assistant/agent/classify.py:
- `build_chat_model(settings) -> ChatOpenAI` with model=settings.openai_model, temperature=0.
- `CLASSIFY_SYSTEM_PROMPT` — describes the assistant's scope (save store name + phone, look up
  a store's phone, finish), the five intents with examples, that greetings/"what can you do"/
  thanks are on_topic_chat, and to extract store_name and phone verbatim (don't reformat).
  The prompt must not mention or contain the passphrase.
- `classify(model, messages: list[AnyMessage]) -> Classification` using
  `model.with_structured_output(Classification, method="json_schema", strict=True)` over
  [system prompt] + the last few messages (context for follow-ups like "and Costco?").

TDD in agent/tests/test_classify.py, all `@pytest.mark.llm`, using real settings:
- parametrized table of utterances → intent: "save Trader Joe's 555-234-5678" (save, with name
  and phone extracted), "what's the number for Costco" (lookup, name "Costco"), "I'm done",
  "I'm good" (done), "who won the world cup?", "write me a poem" (off_topic), "hi", "what can
  you do?" (on_topic_chat).
- extracted phone is the raw text, not normalized.
Iterate on the prompt until the table passes reliably (run it 3 times).

Verify all checks. Commit: "feat(agent): LLM intent classifier".
```

### Step 12 — Graph v1: classify, capability, off-topic redirect

```text
Read spec.md §5.1, §5.4, §7.2 and plan.md §3. Use the langgraph-fundamentals and
langgraph-persistence skills.

Create src/store_assistant/agent/graph.py:
- `@dataclass class GraphDeps: model, stores: StoreRepository, summaries: SummaryRepository,
  settings` (passed via closures/functools.partial into nodes — no globals).
- `build_graph(deps, checkpointer) -> CompiledStateGraph`.
- Nodes for this step (in agent/nodes/):
  - `classify_node`: calls classify, stores `classification`, updates `off_topic_streak` via
    next_off_topic_streak.
  - `answer_capability` (agent/nodes/capability.py): appends a fixed AIMessage describing what
    the assistant can do (no LLM needed).
  - `handle_off_topic` (agent/nodes/off_topic.py): fixed redirect text; at streak 2 adds the
    warning "One more off-topic message and I'll wrap up."
- Edges: START → classify → conditional(route_after_classify) with an explicit path map. Keep
  the path map in one module-level dict, `INTENT_ROUTES`. Until their nodes exist, the route
  names "save_store", "lookup_store" and "summarize_and_end" map to "answer_capability", so
  every intent gets a reply. Steps 14, 15 and 17 each replace one entry.
  handle_off_topic → conditional(route_after_off_topic): END only until step 14.

TDD in agent/tests/test_graph_chat.py (`@pytest.mark.llm`), compiling with a real SqliteSaver
on tmp_path (fixture `checkpointer` added to conftest using
`SqliteSaver(sqlite3.connect(path, check_same_thread=False))`):
- "hi, what can you do?" → last AIMessage is the capability text; streak 0.
- two off-topic messages on the same thread → streak 2 and warning present; then an on-topic
  message resets streak to 0.
- state persists across invocations on the same thread_id (read via graph.get_state).

Verify all checks. Commit: "feat(agent): graph with capability and off-topic paths".
```

### Step 13 — Turn handler v1

```text
Read spec.md §7.3, §9 and plan.md §3. Use the langgraph-persistence and langsmith-trace skills
(reading only; do not install the LangSmith CLI or send feedback).

Create src/store_assistant/conversation/turns.py:
- `@dataclass(frozen=True) class PendingPrompt: kind, prompt, asked_at: datetime`
- `@dataclass(frozen=True) class TurnResult: messages: list[AnyMessage] (full transcript),
  pending: PendingPrompt | None, ended: bool`
- `class ConversationNotFoundError`, `class ConversationEndedError`.
- `class TurnHandler(graph, settings, clock: Callable[[], datetime] = utc now)`:
  - `start() -> str` returns a new uuid4 thread_id.
  - `send(thread_id, text) -> TurnResult`: if the thread has a pending interrupt, resume with
    Command(resume={"answer": text}); otherwise invoke with a HumanMessage. Raise
    ConversationEndedError if state.ended.
  - `view(thread_id) -> TurnResult` for redraws.
  - Every invoke passes config {"configurable": {"thread_id": ...},
    "metadata": {"thread_id": ...}, "run_name": "store-assistant-turn"}.
  - Pending prompt comes from the latest StateSnapshot's interrupts; asked_at from the
    snapshot's created_at.
Create src/store_assistant/app_factory.py: `build_app(settings) -> TurnHandler` wiring
connect(), repositories, model, SqliteSaver at data_dir/"checkpoints.sqlite", build_graph.
This is the single composition root used by the UI and the e2e tests.

TDD in conversation/tests/test_turns.py (`@pytest.mark.llm`, real tmp DBs via build_app with a
Settings whose data_dir=tmp_path):
- start returns distinct ids; send "hi" returns a transcript ending in the capability reply,
  pending None, ended False; view returns the same transcript.
- `send` on an unknown/empty thread works as a new conversation (document this choice).

Verify all checks. Commit: "feat(conversation): turn handler and app composition root".
```

### Step 14 — Ending and summaries

```text
Read spec.md §5.5 and plan.md §3.

Add agent/nodes/summarize.py `summarize_and_end`:
- Determines end_reason: "off_topic" if off_topic_streak >= OFF_TOPIC_LIMIT else "user_done".
- Calls the model with a summary prompt + transcript + a rendered list of `actions`, asking for
  2–4 plain sentences stating the facts from actions. Never includes passphrase content (none
  exists in state).
- Saves via SummaryRepository.add(thread_id from config, ...), appends the summary as the final
  AIMessage, sets ended=True, end_reason.
Wire it: add "summarize_and_end" to both conditional edge maps; handle_off_topic routes there at
streak 3.

TDD in agent/tests/test_graph_ending.py (`@pytest.mark.llm`, via TurnHandler):
- "hi" then "I'm done" → ended True, end_reason user_done, one summary row for the thread_id
  with non-empty text; further send raises ConversationEndedError.
- three off-topic messages → ended, end_reason off_topic, summary row exists.
- two off-topic, one on-topic, two off-topic → NOT ended (streak reset proven end-to-end).

Verify all checks. Commit: "feat(agent): end conversation with saved summary".
```

### Step 15 — Save flow

```text
Read spec.md §4, §5.2, §7.2 (interrupt rules) and plan.md §3. Use the
langgraph-human-in-the-loop skill.

Add agent/nodes/save.py `save_store`. Overwrite handling comes in step 16. In this step the
tests use new names only, and a duplicate name lets DuplicateStoreError propagate:
- name = classification store_name, else interrupt({"kind": "store_name", "prompt": ...});
  clean_store_name; on InvalidStoreNameError re-interrupt with the reason.
- phone = classification phone, else interrupt({"kind": "phone", ...}); normalize_us_phone;
  on InvalidPhoneError re-interrupt with the reason and an example. Loop until valid.
- Resume values arrive as {"answer": str}.
- Only after the last interrupt: StoreRepository.add, append Action(kind="saved"), append the
  prompt/answer exchange plus confirmation "Saved <name> — <phone>." to messages.
Wire "save_store" into the conditional edge map.

TDD in agent/tests/test_graph_save.py (`@pytest.mark.llm`, via TurnHandler, real DB):
- one-shot "save Trader Joe's 555-234-5678" → row with +15552345678, pending None.
- "save a store" → pending kind store_name → "Costco" → pending kind phone → "12345" →
  pending kind phone again (reprompt) → "(555) 876-5432" → row saved; only one row.
- transcript after completion contains the invalid attempt and the confirmation.
- no row exists while a prompt is pending (side effect after last interrupt).

Verify all checks. Commit: "feat(agent): save store flow with phone reprompt".
```

### Step 16 — Overwrite confirmation

```text
Read spec.md §5.2 step 3 and plan.md §3.

Extend save_store: before writing, if find_by_name returns a store, interrupt
({"kind": "confirm_overwrite", "prompt": "<Name> is already saved with <old>. Replace it with
<new>?"}). Interpret the answer with a small pure helper `parse_yes_no(text) -> bool | None`
(yes/y/yeah/sure/replace → True; no/n/nope/keep → False; else None → re-ask). Yes →
update_phone + Action "updated"; No → Action "kept_existing" and say the original was kept.

TDD:
- unit test parse_yes_no (agent/tests/test_yes_no.py).
- integration (`@pytest.mark.llm`): existing Costco; save Costco with a new number → pending
  confirm_overwrite → "yes" → phone updated; repeat with "no" → unchanged; "maybe" → re-asked.
  Names differing only by case/spacing trigger the confirmation.

Verify all checks. Commit: "feat(agent): confirm before overwriting an existing store".
```

### Step 17 — Lookup flow and passphrase gate

```text
Read spec.md §5.3, §6 and plan.md §3.

Add agent/nodes/lookup.py `lookup_store`:
- name from classification or interrupt kind store_name.
- Up to 3 times: interrupt({"kind": "passphrase", "prompt": ...}); resume value is
  {"passphrase_ok": bool}. On False with attempts left, re-prompt saying it was wrong. After 3
  failures: message + Action "lookup_cancelled_passphrase".
- On True: find_by_name → found message "<Name>: <phone>." + Action "lookup_found"; or miss
  message per spec + Action "lookup_not_found".
- Passphrase exchanges are recorded in messages as "[passphrase entered]".
Wire "lookup_store" into the edge map.

Extend TurnHandler.send: when the pending kind is "passphrase", call is_correct_passphrase
(text, settings.store_lookup_passphrase) and resume with {"passphrase_ok": result}. The raw text
is never passed to the graph. turns.py is one of only two files the confinement guard (step 2)
allows to touch the passphrase.

TDD (`@pytest.mark.llm`, via TurnHandler):
- saved store + "look up Trader Joe's" → pending passphrase → correct → found, phone in last
  message.
- wrong ×3 → cancelled action, conversation continues (ended False, pending None).
- wrong, then correct → found.
- miss → not-found action and message.
- Leak check: after these flows, read checkpoints.sqlite bytes (all tables, all blobs) and
  assert neither the real passphrase nor the wrong attempts appear anywhere. Use distinctive
  test passphrases (e.g. "zebra-quartz-71") so the check is meaningful.

Verify all checks. Commit: "feat(agent): passphrase-gated store lookup".
```

### Step 18 — Cancellation

```text
Read spec.md §5.6, §5.7 and plan.md §3.

Graph side: every node that interrupts accepts a resume value {"cancelled": True,
"reason": "user" | "timeout"} at any interrupt. Factor this into one helper in
agent/nodes/prompts.py, e.g. `ask(kind, prompt) -> str | dict` + `Cancelled` handling, so
save_store and lookup_store share it (no duplication). On cancel: no DB write, message
("Cancelled saving <name>." / "No response, so I cancelled …"), Action cancelled_by_user or
cancelled_timeout, off_topic_streak unchanged.

TurnHandler:
- send(): if pending kind != passphrase and is_cancel_request(text) → resume with cancelled
  reason "user".
- `cancel_operation(thread_id, reason)` for the button and the timer; no-op if nothing pending.
- view(): if pending and inactivity_status(asked_at, clock(), settings thresholds) == "expired" → cancel with reason
  "timeout" before returning (spec §5.7 expired-on-load).
- `inactivity(thread_id) -> InactivityStatus | None` for the UI fragment.

TDD (`@pytest.mark.llm`, real DBs, injected clock that the test advances):
- "cancel" at phone prompt → no row, cancelled_by_user action, pending None.
- cancel_operation(reason="user") at passphrase prompt → lookup not performed.
- typing "cancel" at the passphrase prompt counts as a wrong attempt (documented behaviour).
- clock +61s → inactivity "check_in"; +91s → view() cancels with cancelled_timeout.
- cancel does not change off_topic_streak.

Verify all checks. Commit: "feat(conversation): cancel operations by keyword, button or timeout".
```

### Step 19 — Streamlit v1

```text
Read spec.md §8 and plan.md §3.

Create src/store_assistant/ui/app.py:
- `@st.cache_resource` → build_app(get_settings()).
- thread_id kept in st.session_state for now (URL in step 20).
- Render the transcript with st.chat_message ("user"/"assistant").
- If pending kind == "passphrase": st.text_input(type="password", key=...) + submit; else
  st.chat_input. When pending (any kind), show a "Cancel" button calling cancel_operation.
- Show the pending prompt text as the latest assistant bubble.
- Passphrase entries are shown in the transcript as "••••••" (they're stored as
  "[passphrase entered]" — render that marker as dots).
Add a `[project.scripts]`-free run instruction to README later; for now document
`uv run streamlit run src/store_assistant/ui/app.py` in the module docstring.

TDD in ui/tests/test_app_e2e.py with streamlit.testing.v1.AppTest (`@pytest.mark.llm`), using
an env override STORE_ASSISTANT_DATA_DIR=tmp_path:
- "hi" via chat_input → capability reply rendered.
- "save a store" → store name prompt → "Costco" → phone → "555-876-5432" → confirmation
  rendered and row in DB.
- lookup → password input appears (not chat_input) → correct passphrase → phone shown.
- Cancel button during phone prompt → cancellation message, no row.

Verify all checks. Commit: "feat(ui): streamlit chat with prompts, passphrase field and cancel".
```

### Step 20 — Streamlit v2: URL threads and ended view

```text
Read spec.md §8 and plan.md §3.

- thread_id from st.query_params["thread"]; if absent, TurnHandler.start() and set it.
- On load, TurnHandler.view(thread_id) redraws transcript and pending prompt (and applies
  expired-on-load cancellation).
- Sidebar: thread_id caption + "New conversation" button (new id → query param).
- Ended thread: transcript including summary, input widgets hidden, an info line
  "This conversation has ended."

TDD (AppTest, `@pytest.mark.llm`):
- run app, send "hi", capture thread param; new AppTest with that query param → transcript
  restored (resume after "restart").
- New conversation button → different thread param, empty transcript.
- After "I'm done" → no chat_input rendered, summary visible; reloading by URL stays read-only.

Verify all checks. Commit: "feat(ui): resume conversations by URL and read-only ended threads".
```

### Step 21 — Streamlit v3: inactivity fragment

```text
Read spec.md §5.7, §8 and plan.md §3.

- Extract the UI decision into a pure function in ui/inactivity.py:
  `inactivity_notice(status) -> str | None` ("Are you still there?" for check_in, None
  otherwise) — unit tested.
- In app.py, when an operation is pending, render an `@st.fragment(run_every="1s")` that calls
  TurnHandler.inactivity(thread_id): check_in → show the notice; expired →
  cancel_operation(thread_id, "timeout") then st.rerun() (full app rerun).
- The TurnHandler clock is real time in the app; tests use the injected clock at the handler
  level (already covered in step 18).

TDD:
- unit test inactivity_notice.
- AppTest (`@pytest.mark.llm`): the thresholds come from optional env vars
  STORE_ASSISTANT_CHECK_IN_SECONDS / STORE_ASSISTANT_EXPIRE_SECONDS (defaults 60/90, read in
  Settings). The test sets them to 1/2, starts a save and waits with a real clock: after ~1s a
  rerun shows the notice; after ~2s a rerun shows the cancellation and no pending prompt.

Verify all checks. Commit: "feat(ui): inactivity check-in and timeout".
```

### Step 22 — Full scenarios, leak audit, README

```text
Read spec.md §9, §11 and plan.md §3.

1. Add ui/tests/test_scenarios_e2e.py (`@pytest.mark.llm`, AppTest, real OpenAI):
   - Session 1: save Trader Joe's → lookup with correct passphrase → lookup Costco (miss) →
     "I'm done" → conversation_summaries row with end_reason user_done for the URL's thread.
   - Session 2: three off-topic messages → off_topic summary row.
   - Both: assert the passphrase appears in neither SQLite file (byte scan), and not in any
     rendered element text.
2. README.md: what it is, setup (uv sync, .env variables by name only, OPENAI_MODEL
   recommendation), run the app, run tests (all / -m "not llm"), where to find traces in
   LangSmith (project, thread_id metadata), design notes (state machine, passphrase never
   enters the graph, cancellation/timeout), and the out-of-scope list from spec §12.
3. Run the full suite twice; it must be green and warning-free both times.
4. Manually launch the app (`uv run streamlit run src/store_assistant/ui/app.py`), run one
   conversation, and confirm the thread appears in the LangSmith project with the thread_id
   metadata. Report what you observed.

Commit: "test(e2e): full conversation scenarios and README".
```
