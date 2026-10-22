"""Bake the trust-label demo into one self-contained HTML file that runs anywhere.

The page replays results the checker really produced (green, and amber after the
failed-well cut-off goes from 35 to 40), so it needs no server: open it in a browser,
publish it as an artifact, or add it to the Toolbox store. It plays itself, then
waits at the blind test for a volunteer to pick.

    python build_standalone.py [extra-app-id ...]
"""
import copy
import json
import sys

import trust

APPS = ["qpcr-ddct", "blind-a", "blind-b"] + sys.argv[1:]
OUT = trust.ROOT / "standalone.html"


def slim(label):
    # The blind-test cards never show the side-by-side, so drop their bulk.
    if label.get("blind"):
        for e in label["evidence"]:
            e["rows"] = []
            if e.get("receipt"):
                e["receipt"]["plate"] = []
    return label


def snapshot():
    shelf = trust.Shelf()
    green = [slim(l) for l in shelf.labels(force=True) if l["id"] in APPS]
    skill = trust.load_skill(trust.SKILLS / "qpcr-ddct")
    skill["settings"]["failed_well_ct"] = 40
    skill["fingerprint"] = trust.fingerprint(skill["code"], json.dumps(skill["settings"], sort_keys=True), trust.RUNTIME)
    amber_label = trust.build_label(skill)
    before = next(l for l in green if l["id"] == "qpcr-ddct")
    track = copy.deepcopy(before["track_record"])
    track["checks"] += 1
    track["recent"] = (track["recent"] + [False])[-40:]
    track["last_differed"] = {"at": amber_label["last_run"], "since": amber_label["since"], "matched": False}
    amber_label["track_record"] = track
    amber = [amber_label if l["id"] == "qpcr-ddct" else l for l in green]
    sample = trust.read_text(trust.SAMPLE)
    return {"green": green, "amber": amber, "blind": trust.blind_diff(shelf), "sample": sample,
            "run": trust.run_on(shelf, "qpcr-ddct", sample)}


# Answers the page's /api calls from the snapshot instead of the server.
SHIM = """<script>window.SNAPSHOT = __SNAPSHOT__;</script>
<script>
(function () {
  const S = window.SNAPSHOT; let mode = "green";
  const reply = (o) => Promise.resolve(new Response(typeof o === "string" ? o : JSON.stringify(o), { status: 200 }));
  window.fetch = (url) => {
    const u = String(url);
    if (u.startsWith("/api/labels") || u.startsWith("/api/check")) return reply(S[mode]);
    if (u.startsWith("/api/blind")) return reply(S.blind);
    if (u.startsWith("/api/room")) return reply({ lan: null, votes: { A: 0, B: 0 } });
    if (u.startsWith("/api/sample")) return reply(S.sample);
    if (u.startsWith("/api/run")) return reply(S.run);
    return Promise.reject(new Error("offline"));
  };
  window.setCutoff = (amber) => {
    mode = amber ? "amber" : "green";
    const b = document.getElementById("cutoff");
    if (b) b.textContent = amber ? "Change it back: 40 \\u2192 35" : "Change the cut-off: 35 \\u2192 40";
  };
  window.cutoffIsAmber = () => mode === "amber";
})();
</script>
"""

# Routing without location.hash, so the page also works inside a sandboxed srcdoc frame.
ROUTER = """<script>
(function () {
  let hash = "#/";
  window.route = function () { const [view, id] = hash.replace(/^#\\/?/, "").split("/"); return { view: view || "shelf", id }; };
  window.go = function (h) { hash = h; state.runError = ""; render(); window.scrollTo(0, 0); };
  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;
    e.preventDefault();
    go(a.getAttribute("href"));
  }, true);
})();
</script>
"""

PLAYER = """<style>a[download] { display: none !important; }</style>
<div id="cap" style="position:fixed;left:50%;transform:translateX(-50%);bottom:68px;z-index:6;width:max-content;max-width:min(860px,calc(100vw - 32px));background:#1d1f24;color:#fff;border-radius:16px;padding:12px 18px;font:600 clamp(15px,2vw,21px)/1.35 Urbanist,'Segoe UI',sans-serif;box-shadow:0 12px 32px rgba(0,0,0,.25);display:none"></div>
<button id="play" style="position:fixed;left:12px;bottom:12px;z-index:5;border:0;border-radius:999px;padding:11px 16px;font:700 14px Urbanist,'Segoe UI',sans-serif;background:#3d74f0;color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.2);cursor:pointer">&#9654; Play the demo</button>
<button id="cutoff" onclick="setCutoff(!cutoffIsAmber())" style="position:fixed;right:12px;bottom:12px;z-index:5;border:0;border-radius:999px;padding:11px 16px;font:700 14px Urbanist,'Segoe UI',sans-serif;background:#1d1f24;color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.2);cursor:pointer">Change the cut-off: 35 &#8594; 40</button>
<script>
(function () {
  const cap = document.getElementById("cap"), play = document.getElementById("play");
  let timers = [], waiting = false;
  const say = (t) => { cap.textContent = t; cap.style.display = t ? "block" : "none"; };
  const at = (steps) => steps.forEach(([t, f]) => timers.push(setTimeout(f, t)));
  const click = (sel) => { const el = document.querySelector(sel); if (el) el.click(); };
  const stop = () => { timers.forEach(clearTimeout); timers = []; waiting = false; };
  const done = () => { say(""); play.disabled = false; play.textContent = "\\u25B6 Play again"; };
  const part1 = [
    [0, () => { setCutoff(false); state.pick = null; state.diff = null; go("#/"); say("A colleague shared an app. The shelf shows who made it, that it matches the old way on past work, and when it needs checking again."); }],
    [6500, () => { go("#/app/qpcr-ddct"); say("Its trust label. Every tick was checked by code; the rest is what people say. Checked by someone who isn't the author."); }],
    [13000, () => { click('[data-job="plate-2"]'); const r = document.querySelector(".receipt"); if (r && innerWidth < 900) r.scrollIntoView({ block: "center" }); say("A past job next to the old way: identical. The receipt: it read 72 rows, used 71, and left out one bad well."); }],
    [20000, () => { window.scrollTo(0, 0); say("Now someone changes one setting: the cut-off goes from 35 to 40\\u2026"); }],
    [22500, () => { setCutoff(true); }],
    [24500, () => { window.scrollTo(0, 0); say("Amber within seconds, and it says why: since Anders checked it, the cut-off went from 35 to 40."); }],
    [31500, () => { setCutoff(false); say("Changed back: green again. The track record keeps the amber bar."); }],
    [37500, () => { go("#/blind"); waiting = true; say("Your turn. Two versions of the same app, one broken. No biology needed: read the labels and tap the one you'd run."); }],
  ];
  const part2 = [
    [0, () => { setTimeout(() => { const r = document.querySelector(".reveal"); if (r) r.scrollIntoView({ block: "start" }); }, 500); say("The whole difference is three lines of code. Nobody read the code; the label caught it."); }],
    [7000, () => { say("Who presses send: the label says AI drafted the script, a person checked every step, and no AI runs it."); }],
    [13000, () => { say("Two strikes: if two different people report the same problem, the app pauses until its owner fixes it."); }],
    [19000, () => { say("Sharing is easy. Trust is the bottleneck. Your old work is the answer key."); }],
    [27000, done],
  ];
  document.addEventListener("click", (e) => {
    if (waiting && e.target.closest('[data-action="pick"]')) { waiting = false; at(part2); }
  });
  play.addEventListener("click", () => { stop(); play.disabled = true; play.textContent = "Playing\\u2026"; at(part1); });
  setTimeout(() => { if (!play.disabled) play.click(); }, 1500);  // starts by itself when opened
})();
</script>
</body>"""


def build():
    html = trust.read_text(trust.PAGE)
    data = json.dumps(snapshot(), ensure_ascii=False).replace("</", "<\\/")
    assert html.count("<script>\nconst state") == 1 and html.count("</body>") == 1
    html = html.replace("<script>\nconst state", SHIM.replace("__SNAPSHOT__", data) + "<script>\nconst state", 1)
    html = html.replace("</body>", ROUTER + PLAYER, 1)
    # the page's own polling would re-read location.hash on hashchange; drop that listener
    html = html.replace('window.addEventListener("hashchange", () => { state.runError = ""; render(); window.scrollTo(0, 0); });', "", 1)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(html) // 1024} KB, {len(html)} characters)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
