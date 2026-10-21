# Demo: two minutes

**Before you go on:** run `python trust\trust.py serve`, open http://127.0.0.1:8765 on the projector, and open `trust\skills\qpcr-ddct\skill.json` in an editor in a second window, scrolled to `"failed_well_ct": 35`. In the blind test, click "Reset the test" if it was used in rehearsal.

| Time | On screen | Say |
|---|---|---|
| 0:00 | Shelf | "We asked the most advanced AI user here what would make her trust a colleague's pipeline. She said she didn't know: maybe an expert checked it. So we built the thing that says which expert checked it, against what, and when." |
| 0:15 | Shelf card | "Sofie shared her qPCR pipeline. The shelf shows three things: who made it, *matches the old way on 3 of 3 past plates*, and a best-before date." |
| 0:25 | Open the label, Plate 2 tab | "Every tick was checked by code just now. This is Plate 2 from September next to what the lab's Excel template gave at the time: identical, 18 of 18. And a receipt of what it actually read: 72 wells, one left out, and which one." |
| 0:45 | Editor: change `35` to `40`, save | "Now a colleague nudges one setting, the cut-off for failed wells." |
| 0:50 | Label turns amber | "Nobody had to notice. *Differs on Plate 2: 6 of 18 results changed.* The receipt says it now leaves out nothing." Change `40` back to `35` and save: it goes green again. |
| 1:05 | Blind test | Hand the clicker to someone from another table: "You've never seen this code. Two versions. Which would you run on your own plate?" |
| 1:20 | They pick; reveal | "The whole difference is two lines: one version stopped leaving out failed wells. Nobody read the code. The label caught it." |
| 1:35 | Use it on my data, then "Use a sample plate" | "Your plate, run by the good version. Every result comes back stamped: version, who checked it, when it last matched, and what it read." |
| 1:45 | (spoken) | The 30-day plan, below. |

**Say out loud:** the data is a demo. The "old way" is a stand-in for the lab's Excel template, and the names are placeholders.

**If you're running long,** cut "Use it on my data" first, then the reveal's code diff. Never cut the amber moment or the pick.

## The 30-day plan

**Owner: [the bioscience researcher].** Ben owns the checker.

- **By 28 Oct:** she picks three pipelines she trusts. For each one, she saves three past jobs whose outputs she trusted, plus one small known-answer dataset.
- **By 4 Nov:** a colleague in her field, not the author, signs each pipeline. All three go on the team's shelf with labels.
- **By 4 Nov:** one CEBI researcher shelves a difference-in-differences package, with the legacy system's outputs as the answer key. A second researcher runs it.
- **20 Nov:** count runs by people who didn't write the pipeline, amber events and the one-sentence reason for each, and how many were re-checked before their best-before.

## Three questions for the bioscience researcher (ask now)

1. "Think of the last analysis that turned out to be wrong, yours or a colleague's. Who caught it, and what did they compare it with?" *Her answer decides which evidence the label shows first.*
2. "The last time you took over someone else's script or Excel sheet, what did you do before you trusted its numbers? Do you still have outputs from runs you trusted?" *If yes, "matches the old way" is free. If not, lead with the known-answer dataset.*
3. "When you last shared a pipeline that worked, who did you send it to, and what did they ask you first?" *That tells us who the "checked by" person is in her field, and what the label is missing.*
