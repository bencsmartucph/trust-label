"""Build the demo evidence for the qPCR skill.

STAND-IN, SAY SO IN THE DEMO: the lab's real answer key is its Excel template
(ddCt_v3.xlsx). We can't run Excel here, so `old_way()` copies the template's formulas
cell by cell (AVERAGEIFS over wells below Ct 35, ΔCt against GAPDH, ΔΔCt against the
control average, 2^-ΔΔCt, ROUND to 2 decimals). Swap each expected.csv for a real export.

The known-answer plate needs no formula at all: it is built so the answers are 4, 2 and ½.

    python demo-data/make_demo_data.py
"""
import csv
import json
import random
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent / "skills" / "qpcr-ddct" / "evidence"
# Typical Ct (control, treated). IL6 sits near the detection limit in controls,
# which is exactly where failed wells turn up.
MEANS = {"GAPDH": (18.2, 18.3), "IL6": (32.4, 26.3), "TNF": (27.1, 25.2), "HMOX1": (24.0, 22.6)}
GENES = list(MEANS)
COLUMNS = ["well", "sample", "group", "gene", "ct"]


def well_name(i):
    return "ABCDEFGH"[i // 12] + str(i % 12 + 1)


def plate(seed, controls, treated, overrides=()):
    rng = random.Random(seed)
    overrides = dict(overrides)
    rows = []
    for gene in GENES:
        for sample in controls + treated:
            is_treated = sample in treated
            biological = rng.gauss(0, 0.25)
            for rep in (1, 2, 3):
                ct = f"{MEANS[gene][is_treated] + biological + rng.gauss(0, 0.08):.2f}"
                assert float(ct) < 34.5, "only planted wells may fail"
                rows.append({
                    "well": well_name(len(rows)),
                    "sample": sample,
                    "group": "treated" if is_treated else "control",
                    "gene": gene,
                    "ct": overrides.get((gene, sample, rep), ct),
                })
    return rows


def excel_round(x):
    return str(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def old_way(rows):
    """The Excel template's formulas, one cell type at a time."""
    groups, cts = {}, {}
    for r in rows:
        groups[r["sample"]] = r["group"]
        try:
            value = float(r["ct"])
        except ValueError:  # "Undetermined" is text, AVERAGEIFS skips it
            continue
        if value < 35:
            cts.setdefault((r["gene"], r["sample"]), []).append(value)
    average = {k: sum(v) / len(v) for k, v in cts.items()}
    samples = list(groups)
    out = []
    for gene in GENES[1:]:
        dct = {s: average[(gene, s)] - average[("GAPDH", s)] for s in samples}
        control = [dct[s] for s in samples if groups[s] == "control"]
        base = sum(control) / len(control)
        for s in samples:
            out.append({"sample": s, "group": groups[s], "gene": gene,
                        "fold_change": excel_round(2 ** -(dct[s] - base))})
    return out


def known_answer():
    """Every replicate identical, so the answers are exact powers of two by construction."""
    design = {"GAPDH": (20.0, 20.0), "IL6": (26.0, 24.0), "TNF": (25.0, 24.0), "HMOX1": (23.0, 24.0)}
    answer = {"IL6": "4.00", "TNF": "2.00", "HMOX1": "0.50"}  # 2 cycles earlier, 1 earlier, 1 later
    controls, treated = ["C1", "C2", "C3"], ["T1", "T2", "T3"]
    rows, expected = [], []
    for gene in GENES:
        for sample in controls + treated:
            is_treated = sample in treated
            for rep in (1, 2, 3):
                ct = f"{design[gene][is_treated]:.2f}"
                if (gene, sample, rep) == ("IL6", "T1", 3):
                    ct = "37.20"  # a failed well: the right answer only comes out if it is left out
                rows.append({"well": well_name(len(rows)), "sample": sample,
                             "group": "treated" if is_treated else "control", "gene": gene, "ct": ct})
    for gene in GENES[1:]:
        for sample in controls + treated:
            expected.append({"sample": sample, "group": "treated" if sample in treated else "control",
                             "gene": gene, "fold_change": answer[gene] if sample in treated else "1.00"})
    return rows, expected


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
    c, t = ["C1", "C2", "C3"], ["T1", "T2", "T3"]
    source = "Results from the lab's Excel template, saved at the time"
    for folder, date, title, seed, overrides in [
        ("plate-1", "2026-08-14", "Plate 1", 11, ()),
        ("plate-2", "2026-09-03", "Plate 2", 12, [(("IL6", "C2", 3), "35.84")]),
        ("plate-3", "2026-09-22", "Plate 3", 13, [(("TNF", "T1", 2), "Undetermined")]),
    ]:
        rows = plate(seed, c, t, overrides)
        write_job(folder, {"title": title, "date": date, "kind": "old_way", "source": source}, rows, old_way(rows))

    rows, expected = known_answer()
    write_job("known-answer", {"title": "Known-answer plate", "date": "2026-10-14", "kind": "known_answer",
                               "source": "Built so the right answers are exactly 4, 2 and ½"}, rows, expected)

    yours = plate(7, ["Ctrl-1", "Ctrl-2", "Ctrl-3"], ["Drug-1", "Drug-2", "Drug-3"],
                  [(("IL6", "Ctrl-3", 2), "36.10"), (("HMOX1", "Drug-2", 1), "Undetermined")])
    write_csv(HERE / "your-plate.csv", yours)
    print("wrote", EVIDENCE, "and", HERE / "your-plate.csv")
