# Store Assistant — TODO

State tracker for [plan.md](plan.md). Tick a step only after its tests, ruff, mypy and commit
are done.

## Before starting
- [x] `OPENAI_MODEL=gpt-5.4-mini` added to `.env`
- [x] `STORE_LOOKUP_PASSPHRASE` added to `.env`
- [x] El Don confirms the inactivity threshold env vars (step 21)

## Foundation
- [x] 1. Scaffold and tooling
- [x] 2. Config loading, fail fast, passphrase confinement guard

## Pure domain
- [x] 3. Phone validation
- [x] 4. Store name validation
- [x] 5. Passphrase check
- [x] 6. Cancel keywords + inactivity timing

## Persistence
- [x] 7. Database schema + connection
- [x] 8. Store repository
- [x] 9. Summary repository

## Agent
- [x] 10. State types + routing
- [x] 11. LLM classifier
- [x] 12. Graph v1: capability + off-topic
- [x] 13. Turn handler v1 + app composition root
- [x] 14. Ending + summaries
- [x] 15. Save flow
- [x] 16. Overwrite confirmation
- [x] 17. Lookup + passphrase gate
- [x] 18. Cancellation (keyword, button, timeout)

## UI
- [x] 19. Streamlit v1: chat, prompts, passphrase field, Cancel
- [x] 20. Streamlit v2: URL threads, resume, ended view
- [x] 21. Streamlit v3: inactivity fragment

## Wrap-up
- [x] 22. Full e2e scenarios, leak audit, README, LangSmith check

## Notes
- Interrupt timestamps travel in the payload: a reprompt inside one node creates no new checkpoint.
- SqliteSaver uses WAL mode; leak scans must read every file in the data directory.
- The correct passphrase typed outside a passphrase prompt is replaced before reaching the graph.
- AppTest does not tick `st.fragment(run_every=...)`; inactivity e2e covers check-in and timeout via reruns.
- Prompts follow OpenAI's GPT-5 prompting guide and live in agent/llm_prompts.py.
