"""Trust labels for shared apps: evidence a non-author can inspect, checked by code.

    python trust/trust.py check                       re-run every app on its saved evidence, write label.json
    python trust/trust.py serve [--port 8765] [--lan] the same, plus the label page at http://127.0.0.1:8765;
                                                      --lan lets phones on the same wifi follow along and vote
    python trust/trust.py sign APP "Name" "Role" [--on YYYY-MM-DD]
                                                      record who checked this exact version of the code

Standard library only. No AI runs here: every check is plain code.
"""
from __future__ import annotations

import ast
import csv
import datetime as dt
import difflib
import hashlib
import io
import json
import platform
import re
import socket
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / "skills"
PAGE = ROOT / "label.html"
SAMPLE = ROOT / "demo-data" / "your-plate.csv"
RUNTIME = "Python " + ".".join(platform.python_version_tuple()[:2])
NETWORK = {"anthropic", "openai", "requests", "httpx", "aiohttp", "urllib", "http", "socket", "smtplib", "ftplib"}


# ---------- reading ----------

def read_text(path: Path) -> str:
    # Normalise line endings so a Windows save of the same text keeps the same fingerprint.
    return path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")


def fingerprint(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8") + b"\0")
    return h.hexdigest()[:12]


def parse_csv(text: str) -> list[dict]:
    return [dict(r) for r in csv.DictReader(io.StringIO(text))]


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def load_skill(folder: Path) -> dict:
    meta = json.loads(read_text(folder / "skill.json"))
    code = read_text(folder / "skill.py")
    meta["code"] = code
    meta["fingerprint"] = fingerprint(code, json.dumps(meta["settings"], sort_keys=True), RUNTIME)
    meta["folder"] = folder
    meta["evidence_dir"] = (folder / meta.get("evidence", "evidence")).resolve()
    return meta


def imports(code: str) -> list[str]:
    names = set()
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return sorted(names)


def plain_code(code: str) -> dict:
    """What the code can reach at run time, read from the code itself."""
    try:
        used = imports(code)
    except SyntaxError as exc:
        return {"ok": False, "imports": [], "sentence": f"The code does not parse: {exc.msg}, line {exc.lineno}."}
    outside = [m for m in used if m in NETWORK or m not in sys.stdlib_module_names]
    if outside:
        return {"ok": False, "imports": used, "sentence": "Reaches beyond plain code: " + ", ".join(outside) + "."}
    built_in = "only Python's own " + ", ".join(used) if used else "nothing added"
    return {"ok": True, "imports": used,
            "sentence": f"Plain {RUNTIME}, with {built_in}. No AI, no internet, no add-ons."}


# ---------- running ----------

def run_skill(skill: dict, rows: list[dict]) -> tuple[list[dict], list[str]]:
    module = types.ModuleType(skill["id"])
    exec(compile(skill["code"], str(skill["folder"] / "skill.py"), "exec"), module.__dict__)
    out = module.run([dict(r) for r in rows], dict(skill["settings"]))
    results, notes = out if isinstance(out, tuple) else (out, [])
    return [{k: str(v) for k, v in r.items()} for r in results], list(notes)


def receipt(skill: dict, rows: list[dict], text: str, notes: list[str], results: list[dict]) -> dict:
    """What the app actually read and left out, counted here rather than claimed by the app."""
    noun = skill.get("input_noun", "rows")
    left = len(notes)
    return {
        "read": len(rows), "used": len(rows) - left, "left_out": left, "notes": notes,
        "results": len(results), "input_fingerprint": fingerprint(text),
        "sentence": f"Read all {len(rows)} {noun} in the file. Used {len(rows) - left}, left out {left}.",
        "plate": plate_map(skill, rows, notes),
    }


def plate_map(skill: dict, rows: list[dict], notes: list[str]) -> list[dict]:
    """Every input row as a well on the plate, marked when a note says it was left out."""
    spec = skill.get("plate")
    if not spec:
        return []
    ids = {r.get(spec["id"]) for r in rows}
    out = set()
    for note in notes:
        hit = next((t for t in re.findall(r"[\w-]+", note) if t in ids), None)
        if hit:
            out.add(hit)
    return [{"id": r[spec["id"]], "colour": r.get(spec["colour_by"], ""), "label": spec["label"].format(**r),
             "value": r.get(spec["value"], ""), "out": r[spec["id"]] in out} for r in rows]


# ---------- comparing ----------

def compare(skill: dict, expected: list[dict], got: list[dict]) -> list[dict]:
    spec = skill["compare"]
    key = lambda r: tuple(r.get(c, "") for c in spec["key"])
    old = {key(r): r for r in expected}
    new = {key(r): r for r in got}
    order = [key(r) for r in expected] + [key(r) for r in got if key(r) not in old]
    rows = []
    for k in order:
        e, n = old.get(k), new.get(k)
        if e and n:
            differs = [c for c in e if e.get(c) != n.get(c)]
            state = "changed" if differs else "same"
        else:
            differs, state = [], "missing" if e else "extra"
        rows.append({"label": spec["row_label"].format(**(e or n)), "state": state, "differs_in": differs,
                     "old": (e or {}).get(spec["show"]), "new": (n or {}).get(spec["show"])})
    return rows


def gap(row: dict) -> float:
    try:
        return abs(float(row["new"]) - float(row["old"]))
    except (TypeError, ValueError):
        return 0.0


def describe(job: dict, rows: list[dict], against: str) -> str:
    total = sum(r["state"] != "extra" for r in rows)
    changed = [r for r in rows if r["state"] == "changed"]
    missing = sum(r["state"] == "missing" for r in rows)
    extra = sum(r["state"] == "extra" for r in rows)
    if not (changed or missing or extra):
        return f"Identical: all {total} results match {against}."
    parts = []
    if changed:
        parts.append(f"{len(changed)} of {total} results changed")
    if missing:
        parts.append(f"{missing} rows dropped")
    if extra:
        parts.append(f"{extra} extra rows")
    text = f"Differs on {job['title']}: " + ", ".join(parts)
    if changed:
        worst = max(changed, key=gap)
        text += f" (biggest: {worst['label']} is {worst['new']}, {against} says {worst['old']})"
    return text + "."


# ---------- the label ----------

def two_strikes(reports: list[dict]) -> str | None:
    """A problem pauses the app once two different people have reported it."""
    seen: dict[str, set] = {}
    for r in reports:
        seen.setdefault(r["problem"], set()).add(r["by"])
    return next((p for p, who in seen.items() if len(who) >= 2), None)


def check_evidence(skill: dict) -> list[dict]:
    evidence = []
    jobs = [p for p in skill["evidence_dir"].iterdir() if (p / "job.json").exists()]
    for job_dir in jobs:
        job = json.loads(read_text(job_dir / "job.json"))
        input_text = read_text(job_dir / "input.csv")
        expected_text = read_text(job_dir / "expected.csv")
        against = "the known answer" if job["kind"] == "known_answer" else "the old way"
        item = {**job, "id": job_dir.name, "against": against,
                "input_fingerprint": fingerprint(input_text), "expected_fingerprint": fingerprint(expected_text)}
        rows_in = parse_csv(input_text)
        try:
            results, notes = run_skill(skill, rows_in)
            rows = compare(skill, parse_csv(expected_text), results)
            item.update(rows=rows, sentence=describe(job, rows, against),
                        result="identical" if all(r["state"] == "same" for r in rows) else "differs",
                        receipt=receipt(skill, rows_in, input_text, notes, results))
        except Exception as exc:  # a crash is evidence too
            item.update(rows=[], result="differs", receipt=None,
                        sentence=f"Stopped on {job['title']}: {type(exc).__name__}: {exc}.")
        evidence.append(item)
    return sorted(evidence, key=lambda e: (e["kind"] == "known_answer", e["date"]))


def changes_since_check(skill: dict) -> str | None:
    """What is different from the exact version the checker signed, in plain words."""
    checked = skill.get("checked") or {}
    if not checked.get("skill_fingerprint") or checked["skill_fingerprint"] == skill["fingerprint"]:
        return None
    names = skill.get("setting_names", {})
    changes = []
    snapshot = skill["folder"] / "signed.json"
    signed_env = json.loads(read_text(snapshot)) if snapshot.exists() else {}
    before = signed_env.get("settings") or {}
    for k in [k for k in before if k in skill["settings"]] + [k for k in skill["settings"] if k not in before]:
        if before.get(k) != skill["settings"].get(k):
            plain = lambda v: ("on" if v else "off") if isinstance(v, bool) else v
            changes.append(f"{names.get(k, k)} went from {plain(before.get(k, 'unset'))} to {plain(skill['settings'].get(k))}")
    signed_code = skill["folder"] / "signed.py"
    if signed_code.exists():
        diff = list(difflib.ndiff(read_text(signed_code).splitlines(), skill["code"].splitlines()))
        removed = sum(line.startswith("- ") for line in diff)
        added = sum(line.startswith("+ ") for line in diff)
        if removed or added:
            parts = [f"{n} line{'s' * (n != 1)} of code {verb}" for n, verb in ((removed, "removed"), (added, "added")) if n]
            changes.append(" and ".join(parts))
    if signed_env.get("runtime") and signed_env["runtime"] != RUNTIME:
        changes.append(f"Python went from {signed_env['runtime']} to {RUNTIME}")
    who = re.sub(r"^(Dr|Prof)\.?\s+", "", checked.get("by", "")).split(" ")[0] or "the checker"
    return f"Since {who} checked it: " + ("; ".join(changes) if changes else "something outside the code changed") + "."


def record(folder: Path, label: dict) -> dict:
    """Append this check to the app's history and summarise the track record."""
    path = folder / "history.jsonl"
    entry = {"at": label["last_run"], "matched": label["matched_all"], "status": label["status"],
             "fingerprint": label["fingerprint"], "sentence": label["sentence"], "since": label["since"]}
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    history = [json.loads(line) for line in read_text(path).splitlines() if line.strip()]
    differed = [h for h in history if not h["matched"]]
    return {"checks": len(history), "matched": len(history) - len(differed), "since": history[0]["at"],
            "last_differed": differed[-1] if differed else None,
            "recent": [h["matched"] for h in history[-40:]]}


def build_label(skill: dict, previous: dict | None = None) -> dict:
    previous = previous or {}
    evidence = check_evidence(skill)
    past = [e for e in evidence if e["kind"] == "old_way"]
    known = [e for e in evidence if e["kind"] == "known_answer"]
    matched = sum(e["result"] == "identical" for e in past)
    all_match = all(e["result"] == "identical" for e in evidence)
    first_diff = next((e for e in evidence if e["result"] != "identical"), None)
    noun = skill.get("job_noun", "jobs")

    checked = skill.get("checked") or {}
    signed = bool(checked) and checked.get("skill_fingerprint") == skill["fingerprint"]
    best_before = days_left = None
    if checked.get("on"):
        best_before = dt.date.fromisoformat(checked["on"]) + dt.timedelta(days=skill.get("best_before_days", 30))
        days_left = (best_before - dt.date.today()).days
    checker = checked.get("by", "")
    strike = two_strikes(skill.get("reports", []))
    code = plain_code(skill["code"])

    summary = f"Matches the old way on {matched} of {len(past)} past {noun}"
    if strike:
        status, headline, sentence = "paused", "Paused until it is fixed", f"Two people reported the same problem: {strike}"
    elif not all_match:
        status, headline, sentence = "differs", f"Differs from {first_diff['against']}", first_diff["sentence"]
    elif not checked:
        status, headline, sentence = "changed", "Not checked by anyone yet", f"{summary}, but no one outside the author has signed it off."
    elif not signed:
        status, headline = "changed", "Changed since it was checked"
        sentence = f"{summary}, but {checker} checked an earlier version. It needs a new sign-off."
    elif days_left is not None and days_left < 0:
        status, headline = "expired", "Due for a re-check"
        sentence = f"{checker} checked it on {checked['on']}. It still matches, but it is past its best-before."
    else:
        status, headline = "verified", "Matches the old way"
        sentence = f"Identical on {matched} of {len(past)} past {noun}" + (
            ", and it reproduces the known answer exactly." if known else ".")

    return {
        **{k: skill.get(k) for k in ("id", "name", "subtitle", "version", "made_by", "what_it_does",
                                     "how_it_was_made", "old_way", "settings", "blind", "job_noun",
                                     "input_columns", "best_before_days")},
        "status": status, "headline": headline, "sentence": sentence, "since": changes_since_check(skill),
        "matched_all": all_match, "summary": summary, "past_jobs": len(past), "past_matched": matched,
        "known_answer": known[0]["result"] if known else None,
        "fingerprint": skill["fingerprint"], "signed": signed, "checked": checked,
        "checker_is_author": bool(checked) and checker == skill["made_by"]["name"],
        "best_before": best_before.isoformat() if best_before else None, "days_left": days_left,
        "plain_code": code, "runtime": RUNTIME,
        "reports": skill.get("reports", []),
        "last_run": now(),
        "last_matched": now() if all_match else previous.get("last_matched"),
        "evidence": evidence,
    }


def inputs_key(skill: dict) -> str:
    files = sorted(p for p in skill["evidence_dir"].rglob("*") if p.is_file())
    return fingerprint(skill["fingerprint"], read_text(skill["folder"] / "skill.json"),
                       *[str(p) + read_text(p) for p in files])


class Shelf:
    """Re-checks an app whenever its code, settings or evidence change; otherwise serves the last label."""

    def __init__(self):
        self.cache: dict[str, tuple[str, dict]] = {}
        self.lock = threading.Lock()

    def folders(self):
        return sorted(p for p in SKILLS.iterdir() if (p / "skill.json").exists())

    def labels(self, force: bool = False) -> list[dict]:
        out = []
        with self.lock:
            for folder in self.folders():
                try:
                    skill = load_skill(folder)
                    key = inputs_key(skill)
                except Exception as exc:
                    # e.g. skill.json saved half-edited: show amber, never a blank page
                    out.append({"id": folder.name, "name": folder.name, "subtitle": "", "version": "",
                                "status": "differs", "headline": "Can't be read",
                                "sentence": f"{type(exc).__name__}: {exc}", "summary": "Can't be read",
                                "made_by": {"name": "—", "role": ""}, "checked": {}, "signed": False,
                                "fingerprint": "", "best_before": None, "days_left": None,
                                "plain_code": {"ok": False, "imports": [], "sentence": "Not checked."},
                                "what_it_does": [], "how_it_was_made": [], "reports": [],
                                "input_columns": [], "evidence": [], "broken_file": True})
                    continue
                cached = self.cache.get(skill["id"])
                if force or not cached or cached[0] != key:
                    previous = cached[1] if cached else read_previous(folder)
                    label = build_label(skill, previous)
                    label["track_record"] = record(folder, label)
                    (folder / "label.json").write_text(json.dumps(label, indent=1, ensure_ascii=False) + "\n",
                                                       encoding="utf-8")
                    self.cache[skill["id"]] = (key, label)
                out.append(self.cache[skill["id"]][1])
        return out

    def label(self, skill_id: str) -> dict:
        return next(l for l in self.labels() if l["id"] == skill_id)


def read_previous(folder: Path) -> dict:
    try:
        return json.loads(read_text(folder / "label.json"))
    except (OSError, ValueError):
        return {}


# ---------- using it ----------

def stamp_lines(label: dict, rec: dict, run_at: str) -> list[str]:
    checked = label.get("checked") or {}
    matched = label.get("last_matched") or "never"
    return [
        f"Trust stamp: {label['name']}, version {label['version']} (code {label['fingerprint']})",
        f"Status when run: {label['headline']}. {label['sentence']}",
        f"Last matched the old way: {matched.replace('T', ' ')}",
        f"Checked by: {checked.get('by', 'no one yet')}"
        + (f" ({checked.get('role')}), {checked.get('on')}; best before {label['best_before']}" if checked else ""),
        f"This run: {run_at.replace('T', ' ')}. {rec['sentence']} Input file {rec['input_fingerprint']}.",
        f"Runs as: {label['plain_code']['sentence']}",
    ]


def run_on(shelf: Shelf, skill_id: str, text: str) -> dict:
    skill = load_skill(SKILLS / skill_id)
    label = shelf.label(skill_id)
    text = text.replace("\r\n", "\n")
    rows = parse_csv(text)
    need = skill["input_columns"]
    missing = [c for c in need if not rows or c not in rows[0]]
    if missing:
        raise ValueError(f"Your file needs these columns: {', '.join(need)}. Missing: {', '.join(missing)}.")
    results, notes = run_skill(skill, rows)
    rec = receipt(skill, rows, text, notes, results)
    run_at = now()
    lines = stamp_lines(label, rec, run_at)
    buf = io.StringIO()
    buf.write("".join(f"# {line}\n" for line in lines))
    buf.write("".join(f"# {note}\n" for note in notes))
    if results:
        writer = csv.DictWriter(buf, fieldnames=list(results[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    return {"results": results, "receipt": rec, "stamp": lines, "status": label["status"],
            "csv": buf.getvalue(), "filename": f"{skill_id}-stamped-{run_at[:10]}.csv", "run_at": run_at}


def blind_diff(shelf: Shelf) -> dict:
    """The whole difference between the two blind-test versions, to reveal after the pick."""
    skills = {}
    for folder in shelf.folders():
        meta = json.loads(read_text(folder / "skill.json"))
        if meta.get("blind"):
            skills[meta["blind"]] = read_text(folder / "skill.py").splitlines()
    lines = list(difflib.unified_diff(skills.get("A", []), skills.get("B", []), "A", "B", lineterm="", n=2))
    return {"diff": [l for l in lines[2:] if not l.startswith("@@")]}


# ---------- serving ----------

SHELF = Shelf()
# The room: phones on the same network follow the live label and vote in the blind test.
ROOM = {"lan": None, "votes": {"A": 0, "B": 0}}
ROOM_LOCK = threading.Lock()


def lan_address(port: int) -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # picks the outgoing interface; sends nothing
            return f"http://{s.getsockname()[0]}:{port}"
    except OSError:
        return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, code: int, body: bytes, kind: str, etag: str | None = None):
        if etag and self.headers.get("If-None-Match") == etag:
            self.send_response(304)  # a room full of phones polling: send the label only when it changed
            self.send_header("ETag", etag)
            self.end_headers()
            return
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-cache" if etag else "no-store")
        if etag:
            self.send_header("ETag", etag)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def json(self, data, code: int = 200, etag: bool = False):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        tag = f'"{hashlib.sha256(body).hexdigest()[:16]}"' if etag else None
        self.send(code, body, "application/json; charset=utf-8", tag)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html", "/label.html"):
            self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/api/labels":
            self.json(SHELF.labels(), etag=True)
        elif url.path == "/api/room":
            with ROOM_LOCK:
                self.json(ROOM)
        elif url.path == "/api/blind":
            self.json(blind_diff(SHELF))
        elif url.path == "/api/sample":
            self.send(200, SAMPLE.read_bytes(), "text/csv; charset=utf-8")
        else:
            self.send(404, b"Not found", "text/plain")

    def do_POST(self):
        url = urlparse(self.path)
        skill_id = parse_qs(url.query).get("app", [""])[0]
        try:
            if url.path == "/api/check":
                self.json(SHELF.labels(force=True))
            elif url.path == "/api/run":
                body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8-sig")
                self.json(run_on(SHELF, skill_id, body))
            elif url.path == "/api/vote":
                pick = parse_qs(url.query).get("v", [""])[0]
                with ROOM_LOCK:
                    if pick in ROOM["votes"]:
                        ROOM["votes"][pick] += 1
                    self.json(ROOM)
            elif url.path == "/api/vote/reset":
                with ROOM_LOCK:
                    ROOM["votes"] = {"A": 0, "B": 0}
                    self.json(ROOM)
            else:
                self.send(404, b"Not found", "text/plain")
        except Exception as exc:
            self.json({"error": str(exc)}, 400)


# ---------- command line ----------

def sign(skill_id: str, by: str, role: str, on: str | None):
    folder = SKILLS / skill_id
    meta = json.loads(read_text(folder / "skill.json"))
    skill = load_skill(folder)
    meta["checked"] = {"by": by, "role": role, "on": on or dt.date.today().isoformat(),
                       "skill_fingerprint": skill["fingerprint"]}
    # keep the exact code and settings that were checked, outside skill.json so an edit there can't touch them
    (folder / "signed.py").write_text(skill["code"], encoding="utf-8", newline="\n")
    (folder / "signed.json").write_text(json.dumps({"settings": skill["settings"], "runtime": RUNTIME}, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    (folder / "skill.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Signed {skill_id} {skill['fingerprint']} by {by} on {meta['checked']['on']}")


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    command = argv[1] if len(argv) > 1 else "check"
    if command == "sign":
        on = argv[argv.index("--on") + 1] if "--on" in argv else None
        sign(argv[2], argv[3], argv[4], on)
        return 0
    labels = SHELF.labels(force=True)
    for label in labels:
        mark = "OK " if label["status"] == "verified" else "!! "
        print(f"{mark}{label['id']:<12} {label['headline']}. {label['sentence']}")
    if command == "serve":
        port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8765
        host = "0.0.0.0" if "--lan" in argv else "127.0.0.1"
        print(f"Trust labels on http://127.0.0.1:{port}  (Ctrl+C to stop)")
        if "--lan" in argv:
            ROOM["lan"] = lan_address(port)
            print(f"Phones on the same wifi: {ROOM['lan']}")
        # On Windows, address reuse lets a second copy share the port silently; fail loudly instead.
        ThreadingHTTPServer.allow_reuse_address = sys.platform != "win32"
        try:
            server = ThreadingHTTPServer((host, port), Handler)
        except OSError:
            print(f"Port {port} is busy: the checker is probably already running. Close it or use --port {port + 1}.")
            return 2
        server.serve_forever()
    return 0 if all(l["status"] == "verified" for l in labels if not l.get("blind")) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
