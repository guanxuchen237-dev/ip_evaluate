# Virtual Reader DB-backed Tasks and Comments Design

## Goals
- Persist virtual reader simulations into MySQL for later sentiment analysis and modeling.
- Support both sync and async simulations with task status and comment retrieval.

## Non-goals
- UI or dashboard changes.
- Automatic migration of existing simulation results.

## Architecture
- `VirtualReaderTaskStore` connects to MySQL, ensures `novel_insights` and tables exist.
- `VirtualReaderService` creates tasks, runs agents in a thread pool, updates progress, stores comments.
- API layer exposes sync/async simulate, task status, and comment list endpoints.

## Data model
- `vr_task`: task_id, status, progress, group_id, category, title info, persona_ids JSON, totals, avg_score, emotion_distribution JSON, error, request_payload JSON.
- `vr_comment`: task_id, reader info, score, emotion, comment, simulated_duration, profile_snapshot JSON.

## Data flow
1. Client creates group or provides persona_ids.
2. API creates a task row and starts simulation.
3. Each agent writes a comment row; task progress is updated.
4. Task ends in `completed` or `failed`. Comments can be queried by task_id.

## Error handling
- Missing group marks task `failed`.
- Agent exceptions are captured; task error is updated but simulation continues.
- API validates required fields.

## Configuration
- Uses existing MySQL config from `ZONGHENG_CONFIG`.
- `INSIGHTS_DB_NAME` env var overrides default `novel_insights`.

## Testing
- Call `/virtual_reader/simulate_async` and poll `/virtual_reader/task/<task_id>`.
- Query `/virtual_reader/comments?task_id=...` and verify DB rows.
