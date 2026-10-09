#!/usr/bin/env python3
"""Bulk plan-and-apply tool for monitor changes. Standard library only.

Subcommands
  fetch         read monitors by tag, name, id list or search query into a private file
  plan-redact   propose credential and personal-data removals for the fetched monitors
  build         add other proposed changes (normalize, hygiene) to the plan
  inspect       definition checks (owner, recovery, duplicates, muted...), no monitor text
  summary       print counts for the report (no monitor text)
  apply         apply approved plan items; a dry run unless --apply is given

Why it is shaped this way
  * The plan file holds the proposed text and a hash of the current value, never
    the current value, so a plan and its report cannot leak what was removed.
  * Nothing is written to a monitor without an approval file that names the plan
    by its id; a changed plan has a new id, so an old approval cannot cover it.
  * Each write is checked against the hash first (drift is skipped, not forced),
    only listed fields can change, and nothing is deleted, muted or resolved.

Credentials come from the environment (DD_API_KEY, DD_APP_KEY, DD_SITE) and are
never printed. Run as: python3 -I alarmctl.py <subcommand> ...
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("redact", os.path.join(HERE, "redact.py"))
redact = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(redact)

VERSION = 1
MODES = ("redact", "normalize", "hygiene")

# Dotted paths inside a monitor that a plan may change. Anything else is refused.
ALLOWED_FIELDS = {
    "name", "message", "tags", "priority",
    "options.escalation_message", "options.renotify_interval", "options.evaluation_delay",
    "options.require_full_window", "options.notify_no_data", "options.no_data_timeframe",
    "options.notify_audit", "options.include_tags", "options.new_group_delay",
    "options.thresholds.critical", "options.thresholds.warning",
    "options.thresholds.critical_recovery", "options.thresholds.warning_recovery",
    "query",
}
RISKY_FIELDS = {"query"}  # needs "allow_query": true on the item
REDACT_FIELDS = ("name", "message", "options.escalation_message")


class ToolError(Exception):
    pass


# -- small helpers --------------------------------------------------------
def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(value):
    return hashlib.sha256(canon(value).encode("utf-8")).hexdigest()


def get_path(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def set_path(obj, dotted, value):
    parts = dotted.split(".")
    cur = obj
    for part in parts[:-1]:
        if not isinstance(cur.get(part), dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


def write_private(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(data)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def plan_id(items):
    return sha([{k: v for k, v in it.items()} for it in items])[:16]


def finalize(plan):
    for n, it in enumerate(plan["items"], 1):
        it["id"] = "c%03d" % n
    plan["plan_id"] = plan_id(plan["items"])
    return plan


# -- Datadog API ----------------------------------------------------------
class Api:
    def __init__(self, base_url=None, sleep=0.0):
        site = os.environ.get("DD_SITE", "")
        self.base = (base_url or os.environ.get("DD_BASE_URL") or
                     ("https://api." + site if site else "")).rstrip("/")
        self.api_key = os.environ.get("DD_API_KEY", "")
        self.app_key = os.environ.get("DD_APP_KEY", "")
        self.sleep = sleep
        if not (self.base and self.api_key and self.app_key):
            raise ToolError("DD_SITE, DD_API_KEY and DD_APP_KEY must be set in the environment")

    def call(self, method, path, query=None, body=None):
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method, headers={
            "DD-API-KEY": self.api_key, "DD-APPLICATION-KEY": self.app_key,
            "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as err:
            # The body is never shown: an API can echo what was sent.
            raise ToolError("HTTP %d from %s %s" % (err.code, method, path.split("?")[0]))
        except urllib.error.URLError as err:
            raise ToolError("cannot reach the API: %s" % err.reason)


def fetch_monitors(api, args):
    monitors = []
    if args.ids:
        for mid in [x.strip() for x in args.ids.split(",") if x.strip()]:
            monitors.append(api.call("GET", "/api/v1/monitor/%s" % mid))
            time.sleep(api.sleep)
        return monitors
    if args.query:
        ids, page = [], 0
        while True:
            res = api.call("GET", "/api/v1/monitor/search",
                           {"query": args.query, "page": page, "per_page": 100})
            found = res.get("monitors", [])
            ids += [m["id"] for m in found]
            if len(found) < 100 or len(ids) >= args.limit:
                break
            page += 1
            time.sleep(api.sleep)
        for mid in ids[:args.limit]:
            monitors.append(api.call("GET", "/api/v1/monitor/%s" % mid))
            time.sleep(api.sleep)
        return monitors
    query = {"page_size": 100}
    if args.tag:
        query["monitor_tags"] = ",".join(args.tag)
    if args.name_contains:
        query["name"] = args.name_contains
    page = 0
    while len(monitors) < args.limit:
        query["page"] = page
        batch = api.call("GET", "/api/v1/monitor", dict(query))
        monitors += batch
        if len(batch) < 100:
            break
        page += 1
        time.sleep(api.sleep)
    return monitors[:args.limit]


# -- subcommands ----------------------------------------------------------
def cmd_fetch(args):
    if not (args.tag or args.name_contains or args.ids or args.query):
        raise ToolError("give a scope: --tag, --name-contains, --ids or --query "
                        "(refusing to fetch every monitor by accident)")
    api = Api(args.base_url, args.sleep)
    monitors = fetch_monitors(api, args)
    write_private(args.out, json.dumps({"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                        "monitors": monitors}))
    print(json.dumps({"fetched": len(monitors), "file": os.path.basename(args.out),
                      "ids": [m["id"] for m in monitors]}))


def new_plan(args, modes):
    return {"version": VERSION, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "scope": args.scope or "", "modes": modes, "items": []}


def label(monitor):
    # A monitor name is shown in the report, so it gets the same credential and
    # personal-data pass as everything else.
    r = redact.Redactor("team", in_place=True)
    return r.redact(monitor.get("name", ""))


def cmd_plan_redact(args):
    fetched = load_json(args.fetched)["monitors"]
    _, always, _ = redact.load_denylist(args.denylist)
    plan = new_plan(args, ["redact"])
    plan["review_notes"] = []
    for mon in fetched:
        for field in REDACT_FIELDS:
            current = get_path(mon, field)
            if not isinstance(current, str) or not current:
                continue
            red = redact.Redactor("team", [], [], always, in_place=True)
            proposed = red.redact(current)
            if red.possible:
                plan["review_notes"].append({
                    "monitor_id": mon["id"], "monitor": label(mon), "field": field,
                    "note": "%d long unnamed token(s) left in place; a person should look" % red.possible})
            if proposed == current:
                continue
            counts = dict(red.counts)
            plan["items"].append({
                "monitor_id": mon["id"], "monitor": label(mon), "mode": "redact", "field": field,
                "current_sha256": sha(current), "proposed": proposed, "redactions": counts,
                "needs_review": bool(red.possible),
                "reason": "Removes " + ", ".join("%d %s" % (n, c.lower()) for c, n in sorted(counts.items())),
                "risk": "low", "approver": "monitor owner"})
        tags = mon.get("tags") or []
        red = redact.Redactor("team", [], [], always, in_place=True)
        new_tags = [red.redact(t) for t in tags]
        if new_tags != tags:
            plan["items"].append({
                "monitor_id": mon["id"], "monitor": label(mon), "mode": "redact", "field": "tags",
                "current_sha256": sha(tags), "proposed": new_tags, "redactions": dict(red.counts),
                "needs_review": False, "reason": "Removes personal data from tags",
                "risk": "low", "approver": "monitor owner"})
    finalize(plan)
    write_private(args.out, json.dumps(plan, indent=1))
    print(json.dumps({"plan_id": plan["plan_id"], "items": len(plan["items"]),
                      "monitors_changed": len({i["monitor_id"] for i in plan["items"]}),
                      "review_notes": len(plan["review_notes"])}))


def cmd_build(args):
    fetched = {m["id"]: m for m in load_json(args.fetched)["monitors"]}
    plan = load_json(args.into) if os.path.exists(args.into) else new_plan(args, [])
    proposals = load_json(args.proposals)
    for p in proposals:
        for key in ("monitor_id", "mode", "field", "proposed", "reason", "risk", "approver"):
            if key not in p:
                raise ToolError("proposal lacks '%s'" % key)
        if p["mode"] not in MODES:
            raise ToolError("unknown mode '%s'" % p["mode"])
        if p["field"] not in ALLOWED_FIELDS:
            raise ToolError("field '%s' may not be changed by this tool" % p["field"])
        if p["field"] in RISKY_FIELDS and not p.get("allow_query"):
            raise ToolError("changing '%s' needs \"allow_query\": true on the proposal" % p["field"])
        mon = fetched.get(p["monitor_id"])
        if mon is None:
            raise ToolError("monitor %s is not in the fetched file" % p["monitor_id"])
        current = get_path(mon, p["field"])
        if p["mode"] in ("redact", "normalize", "hygiene") and p["field"] in ("message", "name") \
                and isinstance(p["proposed"], str):
            # Anything proposed as text passes the same filter, so no mode can write a credential.
            p["proposed"] = redact.Redactor("team", in_place=True).redact(p["proposed"])
        item = {k: p[k] for k in ("monitor_id", "mode", "field", "proposed", "reason", "risk", "approver")}
        for extra in ("evidence", "alerts_removed", "detection_cost", "allow_query"):
            if extra in p:
                item[extra] = p[extra]
        item["monitor"] = label(mon)
        item["current_sha256"] = sha(current)
        item["needs_review"] = False
        plan["items"].append(item)
        if p["mode"] not in plan["modes"]:
            plan["modes"].append(p["mode"])
    finalize(plan)
    write_private(args.into, json.dumps(plan, indent=1))
    print(json.dumps({"plan_id": plan["plan_id"], "items": len(plan["items"])}))


OWNER_KEYS = ("team", "owner")
METRIC_TYPES = ("metric alert", "query alert")


def cmd_inspect(args):
    """Definition checks that need no history and expose no monitor text."""
    mons = load_json(args.fetched)["monitors"]
    groups = {}
    for m in mons:
        groups.setdefault((m.get("type"), m.get("query")), []).append(m["id"])
    now = time.time()
    out = []
    for m in mons:
        opts = m.get("options") or {}
        thr = opts.get("thresholds") or {}
        tag_keys = {t.split(":", 1)[0] for t in (m.get("tags") or [])}
        flags = []
        if not tag_keys.intersection(OWNER_KEYS):
            flags.append("no_owner_tag")
        if m.get("priority") is None:
            flags.append("no_priority")
        if not re.search(r"https?://", m.get("message") or ""):
            flags.append("no_link_in_message")
        if m.get("type") in METRIC_TYPES:
            if thr.get("critical") is not None and thr.get("critical_recovery") is None:
                flags.append("no_recovery_threshold")
            if opts.get("evaluation_delay") is None:
                flags.append("no_evaluation_delay")
            if not opts.get("require_full_window"):
                flags.append("full_window_not_required")
        if opts.get("notify_no_data"):
            flags.append("notifies_on_no_data")
        silenced = opts.get("silenced") or {}
        if any(v is None for v in silenced.values()):
            flags.append("muted_with_no_end")
        if len(groups[(m.get("type"), m.get("query"))]) > 1:
            flags.append("duplicate_query")
        mod = m.get("overall_state_modified")
        if m.get("overall_state") in ("Alert", "No Data", "Warn") and isinstance(mod, str):
            try:
                age = (now - time.mktime(time.strptime(mod[:19], "%Y-%m-%dT%H:%M:%S"))) / 86400.0
                if age > args.stuck_days:
                    flags.append("stuck_in_%s" % m["overall_state"].lower().replace(" ", "_"))
            except ValueError:
                pass
        out.append({"monitor_id": m["id"], "monitor": label(m), "type": m.get("type"), "flags": flags,
                    "facts": {"renotify_interval": opts.get("renotify_interval"),
                              "evaluation_delay": opts.get("evaluation_delay"),
                              "thresholds": thr, "priority": m.get("priority"),
                              "overall_state": m.get("overall_state"),
                              "duplicates_of": [i for i in groups[(m.get("type"), m.get("query"))] if i != m["id"]]}})
    print(json.dumps({"monitors": out}, indent=1))


def cmd_summary(args):
    plan = load_json(args.changes)
    items = plan["items"]
    by = lambda key: {k: sum(1 for i in items if i.get(key) == k) for k in sorted({i.get(key) for i in items})}
    cats = {}
    for i in items:
        for c, n in (i.get("redactions") or {}).items():
            cats[c] = cats.get(c, 0) + n
    print(json.dumps({"plan_id": plan["plan_id"], "scope": plan.get("scope"), "modes": plan["modes"],
                      "items": len(items), "monitors": len({i["monitor_id"] for i in items}),
                      "by_mode": by("mode"), "by_field": by("field"), "by_risk": by("risk"),
                      "redaction_categories": cats,
                      "needs_review": sum(1 for i in items if i.get("needs_review")),
                      "review_notes": len(plan.get("review_notes", [])),
                      "alerts_removed": sum(i.get("alerts_removed") or 0 for i in items)}, indent=1))


def approved_ids(plan, approval):
    if approval.get("plan_id") != plan["plan_id"]:
        raise ToolError("approval is for plan %s, but this plan is %s; get approval of the current report"
                        % (approval.get("plan_id"), plan["plan_id"]))
    all_ids = [i["id"] for i in plan["items"]]
    if approval.get("approve_all"):
        chosen = [x for x in all_ids if x not in set(approval.get("exclude", []))]
    else:
        chosen = [x for x in approval.get("approved_ids", []) if x in all_ids]
    unknown = set(approval.get("approved_ids", [])) - set(all_ids)
    if unknown:
        raise ToolError("approval names unknown items: %s" % ", ".join(sorted(unknown)))
    return set(chosen)


def cmd_apply(args):
    plan = load_json(args.changes)
    if plan["plan_id"] != plan_id(plan["items"]):
        raise ToolError("the plan file was edited after it was built")
    chosen = approved_ids(plan, load_json(args.approved))
    api = Api(args.base_url, args.sleep)
    by_monitor = {}
    for it in plan["items"]:
        if it["id"] in chosen:
            if it["field"] not in ALLOWED_FIELDS:
                raise ToolError("item %s changes a field this tool may not change" % it["id"])
            by_monitor.setdefault(it["monitor_id"], []).append(it)
    results, rollback = [], {}
    for mid, group in by_monitor.items():
        try:
            live = api.call("GET", "/api/v1/monitor/%s" % mid)
        except ToolError as err:
            results += [{"item": g["id"], "monitor_id": mid, "status": "error", "detail": str(err)} for g in group]
            continue
        body, applicable = {}, []
        for it in group:
            if sha(get_path(live, it["field"])) != it["current_sha256"]:
                results.append({"item": it["id"], "monitor_id": mid, "status": "drifted",
                                "detail": "changed since the plan was made; skipped"})
                continue
            top = it["field"].split(".")[0]
            body.setdefault(top, json.loads(canon(live[top])) if top in live else None)
            if "." in it["field"]:
                set_path(body, it["field"], it["proposed"])
            else:
                body[top] = it["proposed"]
            applicable.append(it)
            if it["mode"] != "redact":  # restoring a removed credential is never wanted
                rollback.setdefault(str(mid), {})[it["field"]] = get_path(live, it["field"])
        if not applicable:
            continue
        if not args.apply:
            results += [{"item": a["id"], "monitor_id": mid, "status": "would_apply"} for a in applicable]
            continue
        try:
            updated = api.call("PUT", "/api/v1/monitor/%s" % mid, body=body)
        except ToolError as err:
            results += [{"item": a["id"], "monitor_id": mid, "status": "error", "detail": str(err)} for a in applicable]
            if "HTTP 429" in str(err):
                results.append({"item": "-", "monitor_id": mid, "status": "stopped",
                                "detail": "rate limited; remaining monitors not touched"})
                break
            continue
        for a in applicable:
            ok = canon(get_path(updated, a["field"])) == canon(a["proposed"])
            results.append({"item": a["id"], "monitor_id": mid,
                            "status": "applied" if ok else "verify_failed"})
        time.sleep(api.sleep)
    if args.apply and rollback:
        os.makedirs(args.rollback_dir, exist_ok=True)
        path = os.path.join(args.rollback_dir, "rollback-%s.json" % plan["plan_id"])
        write_private(path, json.dumps({"plan_id": plan["plan_id"], "previous": rollback}))
    tally = {}
    for r in results:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    print(json.dumps({"plan_id": plan["plan_id"], "dry_run": not args.apply, "tally": tally,
                      "results": results}, indent=1))
    return 0 if not any(r["status"] in ("error", "verify_failed") for r in results) else 4


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--base-url", help="API base URL (default https://api.<DD_SITE>)")
        p.add_argument("--sleep", type=float, default=1.0, help="seconds between calls (default 1)")

    f = sub.add_parser("fetch")
    f.add_argument("--tag", action="append", help="monitor tag; repeat to require all")
    f.add_argument("--name-contains")
    f.add_argument("--ids", help="comma-separated monitor ids")
    f.add_argument("--query", help="monitor search query")
    f.add_argument("--limit", type=int, default=500)
    f.add_argument("--out", required=True)
    common(f)
    f.set_defaults(fn=cmd_fetch)

    r = sub.add_parser("plan-redact")
    r.add_argument("--fetched", required=True)
    r.add_argument("--denylist", help="only its ! lines apply to a live monitor")
    r.add_argument("--scope", help="text describing the scope, shown in the report")
    r.add_argument("--out", required=True)
    r.set_defaults(fn=cmd_plan_redact)

    b = sub.add_parser("build")
    b.add_argument("--fetched", required=True)
    b.add_argument("--proposals", required=True)
    b.add_argument("--into", required=True)
    b.add_argument("--scope")
    b.set_defaults(fn=cmd_build)

    i = sub.add_parser("inspect")
    i.add_argument("--fetched", required=True)
    i.add_argument("--stuck-days", type=float, default=14.0)
    i.set_defaults(fn=cmd_inspect)

    s = sub.add_parser("summary")
    s.add_argument("--changes", required=True)
    s.set_defaults(fn=cmd_summary)

    a = sub.add_parser("apply")
    a.add_argument("--changes", required=True)
    a.add_argument("--approved", required=True,
                   help='JSON: {"plan_id": "...", "approve_all": true, "exclude": []} or {"plan_id": "...", "approved_ids": []}')
    a.add_argument("--apply", action="store_true", help="write the changes; without it nothing is written")
    a.add_argument("--rollback-dir", default=".")
    common(a)
    a.set_defaults(fn=cmd_apply)

    args = ap.parse_args(argv)
    try:
        return args.fn(args) or 0
    except ToolError as err:
        sys.stderr.write("error: %s\n" % err)
        return 2


if __name__ == "__main__":
    sys.exit(main())
