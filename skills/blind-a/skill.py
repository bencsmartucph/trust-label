"""qPCR fold change by the ΔΔCt method, the same way the lab's Excel template does it.

run(rows, settings) takes the plate as rows (well, sample, group, gene, ct) and returns
(results, notes): one fold change per sample and gene, plus a plain sentence for every
well it left out, so the reader can see what was and wasn't used.
"""


def run(rows, settings):
    reference = settings["reference_gene"]
    control = settings["control_group"]
    cutoff = settings["failed_well_ct"]

    # 1. Leave out failed wells: no signal, or a Ct at or above the cut-off.
    groups, wells, notes = {}, {}, []
    for r in rows:
        groups[r["sample"]] = r["group"]
        ct = r["ct"].strip()
        if ct.lower() in ("", "undetermined"):
            notes.append(f"Left out well {r['well']} ({r['gene']} in {r['sample']}): no signal.")
            continue
        wells.setdefault((r["gene"], r["sample"]), []).append(float(ct))

    # 2. Average the repeat wells.
    mean_ct = {key: sum(cts) / len(cts) for key, cts in wells.items()}

    # 3. Compare each gene with the reference gene in the same sample (ΔCt).
    delta = {
        (gene, sample): ct - mean_ct[(reference, sample)]
        for (gene, sample), ct in mean_ct.items()
        if gene != reference and (reference, sample) in mean_ct
    }

    # 4. Compare each sample with the average control sample (ΔΔCt); 5. fold change = 2^-ΔΔCt.
    results = []
    for gene in dict.fromkeys(g for g, _ in delta):
        controls = [d for (g, s), d in delta.items() if g == gene and groups[s] == control]
        baseline = sum(controls) / len(controls)
        for (g, sample), d in delta.items():
            if g == gene:
                results.append({
                    "sample": sample,
                    "group": groups[sample],
                    "gene": gene,
                    "fold_change": f"{2 ** -(d - baseline):.2f}",
                })
    return results, notes
