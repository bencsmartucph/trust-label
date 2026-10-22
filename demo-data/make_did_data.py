"""Build the demo evidence for the difference-in-differences skill (did-cebi).

STAND-IN, SAY SO IN THE DEMO: the centre's real answer key is its legacy Stata do-file
(did_report.do). We can't run Stata here, so `old_way()` copies the do-file line by line
(bysort unit: keep if _N == 2, collapse (mean) outcome by group and period, the 2x2
difference, display %9.3f). Swap each expected.csv for a real log from the do-file.

The known-answer panel needs no do-file at all: it is built so the answer is exactly 2.000.

    python demo-data/make_did_data.py
"""
import csv
import json
import random
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent / "skills" / "did-cebi" / "evidence"
# Outcome: monthly earnings in 1,000 DKK. Units 1-15 are treated, 16-30 are controls.
UNITS = 30
TREATED = range(1, 16)
LEVEL, SPREAD, TREND, EFFECT, NOISE = 28.0, 3.0, 0.8, 1.5, 1.0
TERMS = ["Treated, before", "Treated, after", "Control, before", "Control, after", "Difference-in-differences"]


def panel(seed, drop=()):
    """One row per unit and period; `drop` plants units seen in only one period."""
    rng = random.Random(seed)
    drop = set(drop)
    rows = []
    for unit in range(1, UNITS + 1):
        is_treated = unit in TREATED
        level = rng.gauss(LEVEL, SPREAD)
        for period in ("pre", "post"):
            after = period == "post"
            outcome = level + after * (TREND + EFFECT * is_treated) + rng.gauss(0, NOISE)
            if (unit, period) in drop:
                continue
            rows.append({"unit": str(unit), "group": "treated" if is_treated else "control",
                         "period": period, "outcome": f"{outcome:.2f}"})
    return rows


def stata_round(x):
    """display %9.3f: round half away from zero on the stored double."""
    return str(Decimal(x).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def old_way(rows, balanced=True):
    """The do-file's lines, one at a time. balanced=False is only for the check below."""
    seen = {}
    for r in rows:
        seen.setdefault(r["unit"], set()).add(r["period"])
    kept = [r for r in rows if not balanced or len(seen[r["unit"]]) == 2]  # bysort unit: keep if _N == 2
    cells = {}
    for r in kept:  # collapse (mean) outcome, by(group period)
        cells.setdefault((r["group"], r["period"]), []).append(float(r["outcome"]))
    m = {k: sum(v) / len(v) for k, v in cells.items()}
    did = (m["treated", "post"] - m["treated", "pre"]) - (m["control", "post"] - m["control", "pre"])
    values = [m["treated", "pre"], m["treated", "post"], m["control", "pre"], m["control", "post"], did]
    for v in values:
        assert abs((v * 1000) % 1 - 0.5) > 1e-6, "a rounding tie: pick another seed"
    return [{"term": t, "value": stata_round(v)} for t, v in zip(TERMS, values)]


def known_answer():
    """Whole numbers: treated rise by 4, controls by 2, so the answer is exactly 2.000.
    Unit 7 is treated but seen only before, at 20: kept in, it pulls the answer to -0.250."""
    design = [(1, "treated", 10, 14), (2, "treated", 11, 15), (3, "treated", 12, 16),
              (4, "control", 10, 12), (5, "control", 11, 13), (6, "control", 12, 14)]
    rows = []
    for unit, group, before, after in design:
        rows.append({"unit": str(unit), "group": group, "period": "pre", "outcome": f"{before:.2f}"})
        rows.append({"unit": str(unit), "group": group, "period": "post", "outcome": f"{after:.2f}"})
    rows.append({"unit": "7", "group": "treated", "period": "pre", "outcome": "20.00"})
    answer = ["11.000", "15.000", "11.000", "13.000", "2.000"]
    return rows, [{"term": t, "value": v} for t, v in zip(TERMS, answer)]


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_job(folder, job, rows, expected):
    write_csv(EVIDENCE / folder / "input.csv", rows)
    write_csv(EVIDENCE / folder / "expected.csv", expected)
    (EVIDENCE / folder / "job.json").write_text(json.dumps(job, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    source = "Results from the legacy Stata do-file, saved at the time"
    for folder, date, title, seed, drop in [
        ("report-1", "2026-08-12", "Report 1", 21, ()),
        # Report 2: unit 17 left the sample before the follow-up, unit 8 joined late.
        ("report-2", "2026-09-02", "Report 2", 22, [(17, "post"), (8, "pre")]),
        ("report-3", "2026-09-24", "Report 3", 23, ()),
    ]:
        rows = panel(seed, drop)
        expected = old_way(rows)
        if drop:
            assert old_way(rows, balanced=False)[-1] != expected[-1], "the planted units must move the estimate"
        write_job(folder, {"title": title, "date": date, "kind": "old_way", "source": source}, rows, expected)

    rows, expected = known_answer()
    write_job("known-answer", {"title": "Known-answer panel", "date": "2026-10-14", "kind": "known_answer",
                               "source": "Built so the right answer is exactly 2.000", "short": "exactly 2.000"},
              rows, expected)
    print("wrote", EVIDENCE)
