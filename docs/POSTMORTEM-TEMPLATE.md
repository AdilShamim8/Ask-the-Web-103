# Postmortem Template

Copy this file to `docs/incidents/YYYY-MM-DD-<slug>.md` and fill every
section. Blameless language only: we fix systems, not people.

---

* **Date:**
* **Severity:** S1 / S2 / S3
* **Duration:** (detection → mitigation → full recovery)
* **FMEA entry:** FM-XX (existing row updated?) or NEW
* **Runbook incident:** IN-X (followed? gaps?)

## Summary

Two or three sentences: what users experienced, for how long, at what
scale. No jargon — a product manager should understand it.

## Impact

* Requests affected (count / % of traffic)
* Latency / error-rate deltas (actual numbers from dashboards)
* Cost impact (USD — see `request_cost_usd` for the window)
* Trust impact (degraded answers served? disclosure present?)

## Timeline (all times UTC)

| Time | Event | Source |
| ---- | ----- | ------ |
|      | First bad deploy / trigger |  |
|      | First alert fired (which one? was it the RIGHT one?) |  |
|      | Acknowledged |  |
|      | Mitigation applied (rollback? breaker? config?) |  |
|      | Recovered — metrics back to baseline |  |

## Root Cause

The mechanism, not the person. "Config X allowed Y, which under
condition Z cascaded into W." Include the code path
(`module/file.py:line`) and why existing defenses didn't stop it.

## What Went Well

* Which alerts fired correctly, which mitigations worked as designed,
  which runbook steps applied cleanly.

## What Went Wrong

* Detection gaps, tooling gaps, process gaps, missing defenses.

## Action Items

| Action | Owner | Priority | FMEA/Guard | Due |
| ------ | ----- | -------- | ---------- | --- |
|        |       | P1/P2/P3 |            |    |

Rules:
1. Every action item gets a linked issue before this doc is merged.
2. A P1 action item that would have prevented this incident gets a
   TEST reproducing the gap — merged before this doc is merged.
3. Update the FMEA row within 48h (obligation from the FMEA doc).

## Lessons

What would we tell a new engineer joining the team next week?
