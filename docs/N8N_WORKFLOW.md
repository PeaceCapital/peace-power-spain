# n8n Workflow

This turns the `pc_war_room.jsx` backlog into an automation layer instead of a static task board.

## What This Optimizes

The war-room file is telling us three things:

- some tasks should stay manual and strategic
- some tasks should become recurring system checks
- some tasks should become daily production orchestration

n8n is a good fit for the second and third categories.

## Recommended Architecture

### 1. War Room Governor

Purpose:
- check whether the stack is actually ready to run
- surface blockers before a fake “daily run” pretends everything is live
- generate one operational payload for the dashboard / alerting layer

What it checks:
- OMIE network reachability
- ESIOS token/auth state
- OMIE history presence
- REE node file presence
- base pricer artifacts
- current dashboard snapshot, alerts, and briefing

Repo assets:
- workflow JSON: `ops/n8n/peace_power_war_room_governor.json`
- CLI adapter: `scripts/war_room_governor.py`

### 2. Daily Ops Runner

Recommended next workflow after the governor:
- run OMIE ingestion
- run ESIOS pulls once auth works
- rebuild curated market frame
- refresh pricer outputs
- generate daily briefing JSON / PDF
- push alerts to email, Slack, Teams, or Telegram

This is not fully wired yet because live OMIE and ESIOS are still blocked in your current environment.

### 3. Monthly Retrain

Recommended later workflow:
- first Monday of month
- rolling-window retrain
- version artifact
- update model card / changelog

## What Exists Now

The starter workflow is deliberately lean and stable.

Flow:

1. `Manual Trigger`
2. `Execute Command`
3. `Parse War Room JSON`
4. `Build Operator Payload`

The heavy lifting is done by:

```bash
PYTHONPATH=src python3 scripts/war_room_governor.py war-room
```

That command returns:
- blocker status
- dashboard snapshot
- alerts
- briefing bullets
- readiness rows

## Why This Shape Is Better

Instead of embedding brittle logic directly into n8n nodes:
- n8n handles orchestration
- Python handles repo-specific logic
- the dashboard and automation share the same signal/alert code

That makes the system easier to version and debug.

## How To Import

1. Open n8n.
2. Import:

`ops/n8n/peace_power_war_room_governor.json`

3. Update the repo path inside the `Run War Room Governor` node if your n8n host uses a different path.

## Add The Schedule

The workflow JSON is shipped with a manual trigger so it imports cleanly across n8n versions.

After import, add a `Schedule Trigger` in the UI and connect it to `Run War Room Governor`.

Suggested schedule:
- weekdays
- `07:15` Europe/Madrid

That gives you a blocker/readiness pass before the daily monitoring cycle.

## Self-Hosted Note

This workflow uses the `Execute Command` node, so the cleanest setup is **self-hosted n8n** on the same machine or server that has the repo checked out.

If you use n8n Cloud:
- replace `Execute Command` with an HTTP call to a local API wrapper
- or use SSH to a machine that can run the repo scripts

## Suggested Next Nodes

Once the base workflow is imported, the next best nodes to add are:

- Slack / Teams / Telegram:
  send the `headline`, `blockerSummary`, and briefing bullets

- Email:
  send the daily briefing to yourself or pilot users

- Google Drive / S3 / local file write:
  persist a dated JSON or Markdown briefing artifact

- IF node:
  branch if `headline == "Blocked"` so alerts go to you, while healthy runs go to the daily briefing chain

## War-Room Mapping

These war-room items are natural n8n automation targets:

- `d6` Build OMIE + ESIOS daily ingestion scheduler
- `m6` Monthly model retraining pipeline
- `p2` Build daily D-1 briefing PDF output
- `p5` Build live alert / newswire layer in Ops tab
- `p7` Deploy dashboard to private URL
- `p8` Build API endpoint for forecast output

These items should remain partly manual or research-led:

- `d3` Map BESS indicator IDs
- `d4` Map ATC IDs
- `m4` Build BESS sunset condition model
- `m5` Wire REE node map into ICS signal
- commercial outreach and strategic positioning

## Official n8n References

- Schedule Trigger: [docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/)
- Execute Command: [docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/)
- Code node: [docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code/)
- Workflow import/export: [docs](https://docs.n8n.io/workflows/export-import/)

## Practical Next Step

The fastest way to use this now:

1. Import the governor workflow.
2. Run it manually.
3. Confirm the JSON payload looks sensible.
4. Add a schedule.
5. Then wire Slack/email once you like the output.
