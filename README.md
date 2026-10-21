# Trust labels

A shared app is only useful if someone who didn't write it can believe its output. This folder is the trust layer for the team's platform: every shared app carries a label that says **who checked it, against what, on which data, and until when**. Every line that can be checked is checked by code, on every run. A badge is not evidence; the label is.

## Run it

From the repo root, in PowerShell:

```powershell
python trust\trust.py serve
```

Open http://127.0.0.1:8765. Python 3.12, standard library only, nothing to install. `python trust\trust.py check` re-runs every check once and exits non-zero if any shelved app isn't green.

## The label, field by field

| Field | Why it's there | Borrowed from |
|---|---|---|
| **Status**, green or amber, plus one sentence | One glance, and the sentence says exactly what differs ("Differs on Plate 2: 6 of 18 results changed") | Nutrition label top line; SR 11-7 ongoing monitoring |
| **Against the old way** | Re-runs the app on real past jobs and compares with what the old process produced, to the decimals it reports | CEBI legacy reconciliation; AEA replication packages |
| **Against a known answer** | A tiny dataset built so the right answer is known before anything runs (here 4, 2 and ½) | nf-core's required test dataset; known-answer tests |
| **On which data** | Each past job is named, dated and fingerprinted, so "it matched" points at specific files | Data checksums (AEA, nf-core) |
| **This version** | A code fingerprint, and whether it's the exact version the checker signed | nf-core versioned releases; pinned environments |
| **Runs as** | Read from the code itself: plain code, no AI, no internet when it runs | Pinned environments; "No AI needed" from the send sorter |
| **Checked by** | A named person in your field who is not the author | SR 11-7 independent validation and effective challenge |
| **Best before** | The check date plus 30 days, then a person looks again | Half-Life (median instruction life ~30 days) |
| **Stated by the author** | What it does in plain steps, and who did each step: AI drafted, a person, or no AI. Marked "not checked" | Who presses send |
| **Problems reported** | Two different people reporting the same problem pauses the app | Two Strikes |

Every result the app produces carries a **stamp** (version, fingerprint, when it last matched, who checked it) and a **receipt** counted by code: how many rows it read, how many it used, and which it left out and why. That catches the convincing-sounding drift where a tool says it read everything and didn't.

## Files

- `trust.py` is the checker and the local server. It re-runs an app whenever its code, settings or evidence change, and writes `label.json` next to the app.
- `label.html` is the shelf, the label, the side-by-side view, "use it on my data" and the blind test.
- `skills/qpcr-ddct/` is the worked example: `skill.py` (the app), `skill.json` (who, what, settings, the sign-off) and `evidence/` (three past plates plus a known-answer plate).
- `skills/blind-a`, `skills/blind-b` are two versions of the same app for the blind test. One of them skips the failed-well filter.
- `demo-data/make_demo_data.py` builds the demo evidence.

## For the platform team: the contract

Attach `skills/<app>/label.json` to each app. The shelf needs only three fields: `made_by.name`, `summary` ("Matches the old way on 3 of 3 past plates") and `best_before`, coloured by `status` (`verified` is green; `differs`, `changed`, `expired` and `paused` are amber). The rest is the full label. To shelve a new app, add a folder with `skill.py` (a `run(rows, settings)` function), `skill.json` and `evidence/<job>/{input.csv, expected.csv, job.json}`, then have the checker sign it:

```powershell
python trust\trust.py sign qpcr-ddct "Dr Anders Kjær" "qPCR core facility"
```

## Honest notes

- **Demo data.** The "old way" outputs come from a stand-in that copies the Excel template's formulas (`demo-data/make_demo_data.py`), because Excel can't run here. Replace each `expected.csv` with a real export. The known-answer plate needs no stand-in: its answers are 4, 2 and ½ by construction.
- **Names are fictional.** Sofie Lund and Anders Kjær are placeholders. Put a real name on "Checked by" only with that person's consent.
- **Exact match** means equal at the precision the old way reports (2 decimals here). Plain code gives the same answer every time, so no tolerance is needed. Anything with AI at run time would need one.
