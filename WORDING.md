# Frozen wording for the showcase

Exact strings from the running checker (`python trust\trust.py serve`), 21 Oct 18:48. These won't change before the demo. Anything added after this is listed under "New, optional".

## Shelf card (three things)

- Made by: `Sofie Lund`
- Evidence: `Matches the old way on 3 of 3 past plates` (amber: `Matches the old way on 2 of 3 past plates`)
- Best before: `13 Nov` · `23 days left`

## Label, green

- Kicker / name / sub: `TRUST LABEL` / `qPCR fold change` / `ΔΔCt method, relative to GAPDH · version 1.2`
- Status: **`Matches the old way`**: `Identical on 3 of 3 past plates, and it reproduces the known answer exactly.`
- CHECKED BY CODE
  - `Old way Plate 1, 14 Aug ........ identical ✓`
  - `Old way Plate 2, 3 Sep ......... identical ✓`
  - `Old way Plate 3, 22 Sep ........ identical ✓`
  - `Known answer 4, 2 and ½ ......... exact ✓`
  - `This version ........ the one Anders checked ✓` · `code fingerprint 0ccb9e6eef98`
  - `Runs as ........ plain code ✓` · `Plain Python 3.12, with nothing added. No AI, no internet, no add-ons.`
- SIGNED BY PEOPLE
  - `Made by ........ Sofie Lund`
  - `Checked by ........ Dr Anders Kjær` · `qPCR core facility · not the author ✓`
  - `Checked on ........ 14 Oct 2026`
  - `Best before ........ 13 Nov 2026` · `23 of 30 days left, then Anders looks again`
- STATED BY THE AUTHOR (`not checked`)
  1. `Leaves out failed wells: no signal, or a Ct of 35 or above.`
  2. `Averages the three repeat wells for each sample and gene.`
  3. `Compares each gene with GAPDH in the same sample.`
  4. `Compares each sample with the average control sample.`
  5. `Reports fold change: 2.00 means twice as much as in control.`
  - `AI drafted, a person checked` · Writing the script · `Sofie read each step against the Excel template`
  - `A person` · Checking the results · `Anders compared it with three past plates`
  - `No AI needed` · Running it · `plain code, the same every time`
- `Problems reported ........ none` · `If two different people report the same problem, the app pauses until Sofie fixes it.`
- Footer: `✓ means code checked it on this run. Everything else is what people say.`

## Receipt (Plate 2, green)

`Read all 72 wells in the file. Used 71, left out 1.`
`Left out well B12 (IL6 in C2): Ct 35.84, at or above 35.`

## The amber moment (`"failed_well_ct": 35` changed to `40` in skill.json)

- Status: **`Differs from the old way`**: `Differs on Plate 2: 6 of 18 results changed (biggest: IL6 in T2 is 219.96, the old way says 177.16).`
- `Old way Plate 2, 3 Sep ........ differs ≠` · `Known answer 4, 2 and ½ ........ differs ≠`
- Known answer: `Differs on Known-answer plate: 1 of 18 results changed (biggest: IL6 in T1 is 0.19, the known answer says 4.00).`
- `This version ........ not the one Anders checked ≠` · `code fingerprint 4bb5d2a656f2 · Anders checked 0ccb9e6eef98`
- Receipt on Plate 2: `Read all 72 wells in the file. Used 72, left out 0.`
- Change it back to 35: everything returns to green, fingerprint `0ccb9e6eef98` again.

## Stamp (sample plate, "Use it on my data")

```
# Trust stamp: qPCR fold change, version 1.2 (code 0ccb9e6eef98)
# Status when run: Matches the old way. Identical on 3 of 3 past plates, and it reproduces the known answer exactly.
# Last matched the old way: 2026-10-21 18:48:48
# Checked by: Dr Anders Kjær (qPCR core facility), 2026-10-14; best before 2026-11-13
# This run: 2026-10-21 18:48:48. Read all 72 wells in the file. Used 70, left out 2. Input file ef64fd6b19dd.
# Runs as: Plain Python 3.12, with nothing added. No AI, no internet, no add-ons.
# Left out well C2 (IL6 in Ctrl-3): Ct 36.10, at or above 35.
# Left out well F7 (HMOX1 in Drug-2): no signal.
```

On screen the stamp reads `TRUST STAMP · MATCHES THE OLD WAY` (amber: `NOT VERIFIED: DIFFERS FROM THE OLD WAY`), with rows App / Last matched / Checked by / This run / Receipt.

## Blind test

`Two versions of the same app. You wrote neither.` / `Which one would you run on your own plate? Use only the labels.` Version A is the broken one (it doesn't leave out failed wells). Reveal: `Version B is the one that matches the old way.` · `Both versions say they leave out failed wells. Only one does.` · `Nobody had to read this code. The label caught it.`

## New, optional (being added now, all additive)

- Under an amber status: `Since Anders checked it: the failed-well cut-off went from 35 to 40.`
- The receipt draws the plate: 96 wells, with left-out wells crossed.
- A `Track record` line: how many times it has been checked, and when it last differed.
