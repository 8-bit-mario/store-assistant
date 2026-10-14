# Store Assistant — Specification

A conversational LLM agent that saves stores (name + phone) and retrieves them behind a
passphrase, across any number of operations in one conversation, and ends with a saved
summary.

## 1. Stack

| Concern | Choice |
|---|---|
| Language / tooling | Python 3.14 via `uv` (pin 3.12 or 3.13 only if a dependency breaks). Dependencies added with `uv add` only. |
| Agent framework | LangGraph (explicit state machine) |
| LLM | OpenAI via `langchain-openai`; model name from `OPENAI_MODEL` |
| Tracing | LangSmith |
| App database | SQLite (stdlib `sqlite3`) |
| Conversation state | `SqliteSaver` from `langgraph-checkpoint-sqlite` |
| UI | Streamlit |
| Env loading | `python-dotenv` |
| Tests | `pytest`; lint/format `ruff`; types `mypy` |

Graph state and structured-output schemas are `TypedDict`s; validation is plain Python.

## 2. Configuration

All read from `.env` at startup. Missing required variables → the app fails fast at startup
with an error naming the missing variable (never its value).

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | yes | OpenAI auth |
| `OPENAI_MODEL` | yes | Model name; no default in code. Recommended: `gpt-5.4-mini` |
| `STORE_LOOKUP_PASSPHRASE` | yes | Secret gating lookups |
| `LANGSMITH_API_KEY` | yes | LangSmith auth |
| `LANGSMITH_TRACING` | yes | `true` to enable tracing |
| `LANGSMITH_PROJECT` | yes | Demo trace project |
| `STORE_ASSISTANT_DATA_DIR` | no | Directory for SQLite files; default `data/` |
| `STORE_ASSISTANT_CHECK_IN_SECONDS` | no | Inactivity check-in threshold (§5.7); default `60` |
| `STORE_ASSISTANT_EXPIRE_SECONDS` | no | Inactivity cancel threshold (§5.7); default `90`; must be greater than check-in |

`.env` is never printed or committed. `data/` is git-ignored.

## 3. Data model

### 3.1 App database — `data/store_assistant.sqlite`

```sql
CREATE TABLE stores (
    store_id        INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,          -- as the user typed it (trimmed)
    name_normalized TEXT NOT NULL UNIQUE,   -- lowercased, trimmed, inner whitespace collapsed
    phone           TEXT NOT NULL,          -- E.164, e.g. +15551234567
    created_at      TEXT NOT NULL,          -- ISO-8601 UTC
    updated_at      TEXT NOT NULL
);

CREATE TABLE conversation_summaries (
    conversation_summary_id INTEGER PRIMARY KEY,
    thread_id               TEXT NOT NULL,  -- LangGraph thread; matches LangSmith thread metadata
    summary                 TEXT NOT NULL,
    end_reason              TEXT NOT NULL CHECK (end_reason IN ('user_done', 'off_topic')),
    created_at              TEXT NOT NULL
);
```

Schema is created on startup if absent. All queries are parameterized.

### 3.2 Checkpoint database — `data/checkpoints.sqlite`

Owned by `SqliteSaver`. Kept separate so conversation state can be wiped without touching stores.
**Must never contain the passphrase or any passphrase attempt** (see §6).

## 4. Validation rules

### 4.1 Phone (US/NANP only)

- Accept common formats: `(555) 123-4567`, `555-123-4567`, `555.123.4567`, `5551234567`,
  `+1 555 123 4567`, `1-555-123-4567`.
- Strip everything except digits (and a leading `+`). Valid if 10 digits, or 11 digits starting
  with `1`.
- Area code (NPA) and exchange (NXX) must each start with 2–9.
- Normalize to E.164: `+1NPANXXXXXX`.
- Invalid → reprompt with a short explanation and an example; no attempt limit.

### 4.2 Store name

- Trimmed, non-empty, max 100 characters.
- `name_normalized` = lowercase, trimmed, internal whitespace collapsed to single spaces.
  `"Trader Joe's"` and `"  trader  JOE'S "` are the same store.

## 5. Conversation behaviour

### 5.1 Intents

Each new user message (not an interrupt answer) is classified by the LLM with structured output
(`with_structured_output(<TypedDict>, method="json_schema", strict=True)`, `temperature=0`):

```python
class Classification(TypedDict):
    intent: Literal["save", "lookup", "done", "off_topic", "on_topic_chat"]
    store_name: str | None   # extracted if present
    phone: str | None        # extracted raw, validated in code
```

`on_topic_chat` covers greetings, "what can you do?", thanks — answered with a short capability
reply; does not touch the off-topic counter.

### 5.2 Save flow

1. Use `store_name` / `phone` from classification if present; otherwise `interrupt()` to ask.
2. Validate phone (§4.1). If invalid, `interrupt()` again with the reason. Repeat until valid.
3. If `name_normalized` already exists: `interrupt()` asking
   *"Trader Joe's is already saved with +15551234567. Replace it with +15559876543?"*
   - yes → update phone and `updated_at`; no → keep existing record.
4. Persist, then confirm: *"Saved Trader Joe's — +15551234567."*
5. Append an action record to state (`saved` / `updated` / `kept_existing`).

### 5.3 Lookup flow

1. Use `store_name` from classification or `interrupt()` to ask.
2. Ask for the passphrase via `interrupt({"kind": "passphrase", ...})` — **every lookup**.
3. The turn handler (not the graph) checks it (§6) and resumes with `{"passphrase_ok": bool}`.
4. Wrong → reprompt; after **3** wrong attempts the lookup is cancelled, the user is told, and the
   conversation continues.
5. Correct → exact match on `name_normalized`.
   - Found: *"Trader Joe's: +15551234567."*
   - Not found: *"I don't have a store named 'Costco' saved. Want to save it, or look up a
     different name?"* (no fuzzy suggestions)
6. Append an action record (`lookup_found` / `lookup_not_found` / `lookup_cancelled_passphrase`).

### 5.4 Off-topic handling

- `off_topic_streak` counts **consecutive** off-topic messages; any other intent resets it to 0.
- Streak 1: steer back, list what the agent can do.
- Streak 2: steer back plus warning: *"One more off-topic message and I'll wrap up."*
- Streak 3: end conversation with `end_reason = off_topic` (§5.5).
- Every off-topic message appends an `off_topic_message` action (the fact only, never the text),
  so the summary can mention them.

### 5.5 Ending

Triggered by intent `done` ("I'm done", "I'm good", "that's all", …) → `end_reason = user_done`,
or by off-topic streak 3 → `end_reason = off_topic`.

1. LLM writes a 2–4 sentence plain-text summary built **only** from the structured action list
   in state and the end reason (so facts are stated, not inferred). Example:
   *"User saved Trader Joe's (+15551234567) and updated Costco. Looked up Trader Joe's
   successfully; one lookup was cancelled after 3 wrong passphrases. Conversation ended by user."*
2. Summary never contains the passphrase or attempts (they never reach the graph anyway).
3. Insert into `conversation_summaries` with `thread_id` and `end_reason`.
4. Show the summary as the closing message; set `ended = True` in state.

Closing the browser without "I'm done" writes no summary; the thread stays resumable.

### 5.6 Cancelling an operation

An operation is *in progress* while the graph is paused on an interrupt (name, phone,
overwrite confirmation, passphrase). It can be cancelled three ways:

1. **Keyword:** the user's reply to any non-passphrase prompt is, after trimming and lowercasing,
   one of `cancel`, `stop`, `never mind`, `nevermind`. Matched in code, not by the LLM.
2. **Cancel button:** shown in the UI whenever an operation is in progress (the only way to
   cancel at the passphrase prompt, since text typed there is checked as a passphrase).
3. **Inactivity timeout** (§5.7).

On cancel, the turn handler resumes the graph with `{"cancelled": True, "reason": "user" |
"timeout"}`, plus `"text"` holding the keyword when the user typed one, so the transcript shows
it as the user's reply. The node stops without side effects, tells the user the operation was
cancelled (for timeouts: *"No response, so I cancelled saving Trader Joe's."*), and appends an action
(`cancelled_by_user` / `cancelled_timeout`). The conversation stays open. Cancelling does not
touch the off-topic streak.

### 5.7 Inactivity timeout

Applies **only while an operation is in progress**; an idle conversation with nothing pending
never times out.

- 60 s with no user input after a prompt → the UI shows *"Are you still there?"* (UI-only
  notice, not added to graph state).
- 30 s more with no input (90 s total) → the operation is cancelled with reason `timeout`.
- Any input or button click resets the timer.
- Both thresholds are configurable (§2) so end-to-end tests can use short values; the defaults
  are 60 s and 90 s.
- The timing decision is a pure function, `inactivity_status(asked_at, now, check_in_after,
  expire_after) -> "active" | "check_in" | "expired"`, with the clock injected so it is
  unit-testable without waiting.
- `asked_at` is the time the prompt was raised, carried in the interrupt payload (a reprompt
  inside the same node does not create a new checkpoint, so checkpoint times can't be used).
- The timer only runs while the browser tab is open. When a thread is loaded and its pending
  operation is already expired, it is cancelled with reason `timeout` before rendering.

## 6. Passphrase handling

- Stored only in `.env` (`STORE_LOOKUP_PASSPHRASE`).
- Never in any prompt, LLM context, message history, graph state, checkpoint, or trace.
- When the graph is paused on a `passphrase` interrupt, the **turn handler** compares the user's
  input with `hmac.compare_digest` and resumes the graph with only `{"passphrase_ok": bool}`.
- The graph owns the policy (attempt counting, cancel after 3, performing the lookup).
- If the user types the correct passphrase anywhere else (a chat message or another prompt), the
  turn handler replaces it with `[passphrase entered]` before it reaches the graph.
- The UI collects it in `st.text_input(type="password")` and displays it in the transcript as
  `••••••`.

## 7. Agent architecture

### 7.1 State

```python
class AssistantState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]   # transcript (no passphrase text)
    actions: Annotated[list[Action], operator.add]        # structured record for the summary
    off_topic_streak: int
    classification: Classification | None
    end_reason: Literal["user_done", "off_topic"] | None
    ended: bool
```

### 7.2 Graph

```
START → classify ─┬─ save          → save_store        → END
                  ├─ lookup        → lookup_store      → END
                  ├─ on_topic_chat → answer_capability → END
                  ├─ off_topic     → handle_off_topic ─┬─ streak < 3 → END
                  │                                    └─ streak = 3 → summarize_and_end → END
                  └─ done          → summarize_and_end → END
```

- One graph invocation per user turn. A new message invokes with `{"messages": [HumanMessage]}`;
  an answer to a pending interrupt invokes with `Command(resume=...)`.
- Routing is plain Python on `classification["intent"]` and `off_topic_streak`.
- Interrupt payloads are dicts: `{"kind": "store_name" | "phone" | "confirm_overwrite" |
  "passphrase", "prompt": str}` so the UI knows what input widget to show.
- Nodes that interrupt re-run from the top on resume: any side effect (DB write) happens only
  after the last interrupt in that node.
- When a node finishes, it appends the prompt/answer exchange to `messages` (passphrase answers
  recorded as `[passphrase entered]`) so the transcript can be redrawn after reload.

### 7.3 Turn handler

A UI-independent function/class used by both Streamlit and tests:

- Input: `thread_id`, user text.
- Inspects the thread's pending interrupt (if any) to decide: new message vs resume; for
  `passphrase` interrupts, performs the check and resumes with `passphrase_ok`.
- Detects cancel keywords (§5.6) and exposes `cancel_operation(thread_id, reason)` for the
  Cancel button and the inactivity timeout.
- Refuses input on an ended thread.
- Returns: messages to display, the pending interrupt (kind + prompt + `asked_at`) if any, and
  `ended`.
- Passes LangSmith metadata: `{"thread_id": ...}` (enables the LangSmith Threads view), run name
  `store-assistant-turn`.

## 8. UI (Streamlit)

- Run: `uv run streamlit run src/store_assistant/ui/app.py`.
- Compiled graph + checkpointer + DB connection live in `st.cache_resource`.
- `thread_id` lives in `st.query_params["thread"]`. First load without it → generate a UUID and
  set it. Refresh or later visit with the URL (even after server restart) → reload transcript and
  any pending prompt from the checkpointer.
- Chat rendered with `st.chat_message`; normal input via `st.chat_input`; while a `passphrase`
  interrupt is pending, show `st.text_input(type="password")` instead.
- While an operation is in progress: a Cancel button, and an `@st.fragment(run_every="1s")`
  that evaluates `inactivity_status` and shows the check-in notice or triggers the timeout.
- Sidebar: current `thread_id` and a "New conversation" button (new UUID → new URL).
- Ended thread: read-only transcript with summary; input disabled; only "New conversation" works.

## 9. Tracing

- LangSmith via environment (`LANGSMITH_TRACING=true`); all LangGraph/LangChain runs traced
  automatically.
- Every turn tagged with `thread_id` metadata so a whole conversation is inspectable as one thread.
- Tests trace to a separate project, `store-assistant-tests` (set in `conftest.py`).
- Verification: a test asserts the passphrase string appears neither in the checkpoint DB nor in
  any graph input/state.

## 10. Project layout

Vertical slices, tests beside the code they test. Every code file starts with two `ABOUTME:`
comment lines.

```
src/store_assistant/
    __init__.py
    config.py                 # env loading, fail-fast settings
    conftest.py               # shared fixtures: tmp DBs, test LangSmith project
    validation/
        phone.py              # parse + normalize US phones
        store_name.py         # trim, length check, normalization
        tests/
    storage/
        database.py           # connection + schema creation
        stores.py             # StoreRepository
        summaries.py          # SummaryRepository
        tests/
    security/
        passphrase.py         # constant-time check
        tests/
    agent/
        state.py              # TypedDicts: state, classification, action
        classify.py           # LLM intent + entity extraction
        nodes/                # save_store, lookup_store, off_topic, capability, summarize
        graph.py              # build + compile graph
        tests/
    conversation/
        turns.py              # turn handler
        cancellation.py       # cancel keywords + inactivity_status
        tests/
    ui/
        app.py                # Streamlit app
        tests/                # AppTest end-to-end
```

Module files stay under 500 lines, functions under 50, line length 100 (ruff).

## 11. Testing

TDD throughout: failing test first, minimal code, refactor green.

| Level | Scope | LLM? |
|---|---|---|
| Unit | phone/name validation, repositories (save, duplicate, update, lookup, miss, summary insert), passphrase check, routing functions, off-topic streak logic, cancel keywords, `inactivity_status` with injected clock (59 s / 60 s / 89 s / 90 s boundaries) | No |
| Integration | compiled graph + real SQLite + `SqliteSaver` in `tmp_path`, via the turn handler: invalid-phone reprompt loop, overwrite confirm yes/no, 3 wrong passphrases cancel lookup, cancel keyword mid-save (no DB write), Cancel during passphrase, timeout cancel, expired operation cancelled on load, lookup miss, passphrase absent from checkpoint DB, streak reset | Yes (real OpenAI) |
| End-to-end | Streamlit `AppTest`: session 1 save → lookup (correct passphrase) → miss → "I'm done" → summary row with `user_done`; session 2 three off-topic messages → `off_topic` summary; resume via `thread` query param; Cancel button mid-save | Yes (real OpenAI) |

- No mocks anywhere.
- Assertions are deterministic: DB rows, state fields, `end_reason`, pending interrupt kind —
  never exact LLM wording.
- Each test uses its own DB files in `tmp_path`.
- LLM-calling tests marked `@pytest.mark.llm`; `uv run pytest -m "not llm"` gives a fast offline
  run. Full suite: `uv run pytest`.
- Test output must be clean (no stray warnings or errors).

## 12. Out of scope

International phone numbers, fuzzy name matching, deleting stores, multiple users/auth, a list of
past conversations in the UI, summaries for abandoned sessions, deployment.

## 13. Resolved during spec review

1. Cancelling: keyword, button and inactivity timeout (§5.6, §5.7).
2. Store name limits: non-empty, max 100 characters.
3. Model: `OPENAI_MODEL=gpt-5.4-mini`. Checked on 2026-10-13 against the account's model list:
   it accepts `temperature=0` and strict JSON-schema output; `gpt-6-luna` and `gpt-5.6-luna`
   reject `temperature=0`.
