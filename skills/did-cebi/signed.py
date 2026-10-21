"""Difference-in-differences on a two-period panel, the same way the legacy Stata do-file does it.

run(rows, settings) takes the panel as rows (unit, group, period, outcome) and returns
(results, notes): the four group averages and the 2x2 estimate, plus a plain sentence for
every unit it left out, so the reader can see what was and wasn't used.
"""


def run(rows, settings):
    rows = [{k: v.strip() for k, v in r.items()} for r in rows]

    # 1. Leave out units not seen in both periods, when the balanced-panel rule is on.
    seen = {}
    for r in rows:
        seen.setdefault(r["unit"], set()).add(r["period"])
    keep, notes = set(seen), []
    if settings["balanced_panel"]:
        for unit, periods in seen.items():
            missing = [p for p in ("pre", "post") if p not in periods]
            if missing:
                keep.discard(unit)
                notes.append(f"Left out unit {unit}: no {missing[0]}-period observation.")

    # 2. Average the outcome for each group, before and after.
    cells = {}
    for r in rows:
        if r["unit"] in keep:
            cells.setdefault((r["group"], r["period"]), []).append(float(r["outcome"]))
    mean = {key: sum(values) / len(values) for key, values in cells.items()}

    # 3. The change for treated units minus the change for control units.
    did = (mean["treated", "post"] - mean["treated", "pre"]) - (mean["control", "post"] - mean["control", "pre"])

    terms = [
        ("Treated, before", mean["treated", "pre"]),
        ("Treated, after", mean["treated", "post"]),
        ("Control, before", mean["control", "pre"]),
        ("Control, after", mean["control", "post"]),
        ("Difference-in-differences", did),
    ]
    return [{"term": term, "value": f"{value:.3f}"} for term, value in terms], notes
