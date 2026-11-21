"""The DPDP baseline: the parts of each rule set that come from the law and cannot be weakened.

NigraniAI is a DPDP compliance tool, so the legal requirements are fixed. A client configures its own
business on top (tables, purposes, notices, contact person, response steps) and may make any check
stricter, but never weaker:

* consent rules R1-R8 (DPDP Act s.5, s.6, s.8, s.12; Rules 2025 Rule 3) stay on, keep their legal
  reference, and their severity can only go up; grace periods have a ceiling;
* retention rules E1, L1-L3, I1 stay on; legal minimums can only grow; the inactivity period can only
  shrink and the warning before erasure is at least 48 hours (Rule 8(2));
* breach detectors D1-D7 stay on with their conditions fixed; thresholds can only go down (more
  sensitive) and severity only up; the response clocks have legal ceilings (Rule 7, CERT-In 6 h);
* the anomaly model stays on, at medium sensitivity or higher.

The baseline values of each locked item are taken from the shipped default documents, so the copy's
defaults and its legal floor are the same thing. `check()` reports every way a document is weaker than
the baseline (and returns a corrected copy); `describe()` tells the dashboard what is locked.
"""
import copy

SEV = ["low", "medium", "high", "critical"]
SENS = ["low", "medium", "high"]
UNIT_S = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400, "months": 2629800, "years": 31557600}

BASELINE_VERSION = "DPDP Act 2023 · DPDP Rules 2025 · CERT-In Directions 2022"

# ---------------------------------------------------------------- what is locked
POLICY_RULES = {          # id -> extra limits (grace ceilings in seconds)
    "R1": {}, "R2": {"grace_max": 600}, "R3": {}, "R4": {}, "R5": {},
    "R6": {"grace_max": 30 * 86400}, "R7": {}, "R8": {},
}
POLICY_FIXED = ("type", "name", "dpdp_ref")

RETENTION_RULES = {
    "E1": {"keep_max": {"n": 30, "unit": "days"},
           "why": "Erasure after a request (s.12(3)) must happen; NigraniAI allows at most 30 days to complete it."},
    "L1": {"keep_min": "default", "why": "Kept because another law requires it (DPDP Act s.8(7))."},
    "L2": {"keep_min": "default", "why": "Kept because another law requires it (DPDP Act s.8(7))."},
    "L3": {"keep_min": "default", "why": "Logs of processing must be kept for at least one year (Rule 8(3))."},
    "I1": {"keep_max": "default", "notice_min": 48,
           "why": "Erase after the inactivity period, warning the customer at least 48 hours before (Rule 8(1)-(2))."},
}
RETENTION_FIXED = ("type", "ref", "action")

DETECTOR_FIXED = ("source", "match", "measure", "sum_field", "group_by", "window", "category", "name", "why", "ref")

CLOCK_MAX = {
    "cert_in_hours": (6, "CERT-In must be told within 6 hours (CERT-In Directions, 28 April 2022)"),
    "board_report_hours": (72, "The detailed report to the Board is due within 72 hours (Rule 7(2)(b))"),
    "board_initial_hours": (72, "The Board must be told without delay (Rule 7(2)(a)); the target cannot exceed the 72-hour report"),
    "principals_hours": (72, "Affected customers must be told without delay (Rule 7(1)); the target cannot exceed 72 hours"),
}
ANOMALY_MIN_SENS = "medium"


def _secs(keep):
    try:
        return float(keep.get("n")) * UNIT_S[keep.get("unit")]
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def _fmt(keep):
    n = keep.get("n")
    n = int(n) if isinstance(n, float) and n.is_integer() else n
    unit = str(keep.get("unit") or "")
    return f"{n} {unit[:-1] if n == 1 and unit.endswith('s') else unit}"


def _by_id(items):
    return {x.get("id"): x for x in items or [] if isinstance(x, dict)}


# ---------------------------------------------------------------- checks
def _check_policy(doc, base, out):
    rules = doc.get("rules") if isinstance(doc.get("rules"), list) else []
    have, want = _by_id(rules), _by_id(base.get("rules"))
    for rid, lim in POLICY_RULES.items():
        b = want.get(rid)
        if not b:
            continue
        r = have.get(rid)
        if r is None:
            out.append(f"Consent rule {rid} ({b['name']}) is required by {b['dpdp_ref']} and cannot be removed.")
            rules.append(copy.deepcopy(b)); continue
        for k in POLICY_FIXED:
            if r.get(k) != b.get(k):
                out.append(f"Consent rule {rid}: '{k}' is fixed by the DPDP baseline ({b['dpdp_ref']}).")
                r[k] = b.get(k)
        if r.get("enabled") is not True:
            out.append(f"Consent rule {rid} ({b['name']}) is required by {b['dpdp_ref']} and cannot be switched off.")
            r["enabled"] = True
        if r.get("severity") not in SEV or SEV.index(r["severity"]) < SEV.index(b["severity"]):
            out.append(f"Consent rule {rid}: severity cannot be lower than {b['severity']}.")
            r["severity"] = b["severity"]
        gmax = lim.get("grace_max")
        if not isinstance(r.get("params"), dict):
            r["params"] = {}
        p = r["params"]
        if gmax is not None and isinstance(p.get("grace_seconds"), (int, float)) and p["grace_seconds"] > gmax:
            out.append(f"Consent rule {rid}: the grace period can be at most {gmax:,} seconds.")
            p["grace_seconds"] = gmax
    doc["rules"] = rules


def _check_retention(doc, base, out):
    rules = doc.get("rules") if isinstance(doc.get("rules"), list) else []
    have, want = _by_id(rules), _by_id(base.get("rules"))
    for rid, lim in RETENTION_RULES.items():
        b = want.get(rid)
        if not b:
            continue
        r = have.get(rid)
        if r is None:
            out.append(f"Retention rule {rid} ({b['name']}) is required ({b.get('ref')}) and cannot be removed.")
            rules.append(copy.deepcopy(b)); continue
        for k in RETENTION_FIXED:
            if r.get(k) != b.get(k):
                out.append(f"Retention rule {rid}: '{k}' is fixed by the DPDP baseline ({b.get('ref')}).")
                if b.get(k) is None:
                    r.pop(k, None)
                else:
                    r[k] = b.get(k)
        if r.get("enabled") is not True:
            out.append(f"Retention rule {rid} ({b['name']}) is required ({b.get('ref')}) and cannot be switched off.")
            r["enabled"] = True
        keep = r.get("keep") if isinstance(r.get("keep"), dict) else {}
        s = _secs(keep)
        kmin = b["keep"] if lim.get("keep_min") == "default" else lim.get("keep_min")
        kmax = b["keep"] if lim.get("keep_max") == "default" else lim.get("keep_max")
        if kmin and (s is None or s < _secs(kmin)):
            out.append(f"Retention rule {rid} ({b['name']}): must keep for at least {_fmt(kmin)} ({b.get('ref')}).")
            r["keep"] = dict(kmin)
        if kmax and (s is None or s > _secs(kmax)):
            out.append(f"Retention rule {rid} ({b['name']}): the period can be at most {_fmt(kmax)}.")
            r["keep"] = dict(kmax)
        nmin = lim.get("notice_min")
        if nmin and (not isinstance(r.get("notice_hours"), (int, float)) or r["notice_hours"] < nmin):
            out.append(f"Retention rule {rid}: customers must be warned at least {nmin} hours before erasure (Rule 8(2)).")
            r["notice_hours"] = nmin
    # Nothing may delete data that another law says must be kept.
    mins = [x for x in rules if x.get("type") == "legal_minimum" and x.get("enabled")]
    for r in rules:
        if r.get("type") != "age" or r.get("action") != "delete" or not r.get("enabled"):
            continue
        for m in mins:
            if (m.get("source", "shop"), m.get("table")) == (r.get("source", "shop"), r.get("table")):
                s, ms = _secs(r.get("keep") or {}), _secs(m.get("keep") or {})
                if s is not None and ms is not None and s < ms:
                    out.append(f"Retention rule {r.get('id')} deletes {r.get('table')} before the legal minimum in {m.get('id')} ({_fmt(m['keep'])}).")
                    r["keep"] = dict(m["keep"])
    doc["rules"] = rules


def _check_breach(doc, base, out):
    clocks = doc.get("clocks") if isinstance(doc.get("clocks"), dict) else {}
    for k, (mx, why) in CLOCK_MAX.items():
        v = clocks.get(k)
        if not isinstance(v, (int, float)) or v > mx:
            out.append(f"{why}; it cannot be set above {mx} hours.")
            clocks[k] = min(mx, base["clocks"].get(k, mx))
    w = clocks.get("warn_hours")
    if not isinstance(w, (int, float)) or w > clocks.get("board_report_hours", 72):
        out.append("The warning time cannot be longer than the Board report deadline.")
        clocks["warn_hours"] = min(base["clocks"].get("warn_hours", 12), clocks.get("board_report_hours", 72))
    doc["clocks"] = clocks

    an = doc.get("anomaly") if isinstance(doc.get("anomaly"), dict) else None
    if an is not None:
        if an.get("enabled") is not True:
            out.append("The anomaly model is part of breach detection (DPDP Act s.8(5)) and cannot be switched off.")
            an["enabled"] = True
        if an.get("sensitivity") not in SENS or SENS.index(an["sensitivity"]) < SENS.index(ANOMALY_MIN_SENS):
            out.append(f"Anomaly sensitivity cannot be lower than {ANOMALY_MIN_SENS}.")
            an["sensitivity"] = ANOMALY_MIN_SENS

    dets = doc.get("detectors") if isinstance(doc.get("detectors"), list) else []
    have = _by_id(dets)
    for b in base.get("detectors") or []:
        did = b["id"]
        d = have.get(did)
        if d is None:
            out.append(f"Breach detector {did} ({b['name']}) is part of the DPDP baseline and cannot be removed.")
            dets.append(copy.deepcopy(b)); continue
        for k in DETECTOR_FIXED:
            if d.get(k) != b.get(k):
                out.append(f"Breach detector {did}: '{k}' is fixed by the DPDP baseline.")
                if b.get(k) is None:
                    d.pop(k, None)
                else:
                    d[k] = copy.deepcopy(b.get(k))
        if d.get("enabled") is not True:
            out.append(f"Breach detector {did} ({b['name']}) cannot be switched off.")
            d["enabled"] = True
        if d.get("severity") not in SEV or SEV.index(d["severity"]) < SEV.index(b["severity"]):
            out.append(f"Breach detector {did}: severity cannot be lower than {b['severity']}.")
            d["severity"] = b["severity"]
        if not isinstance(d.get("threshold"), (int, float)) or d["threshold"] > b["threshold"]:
            out.append(f"Breach detector {did}: the threshold can only be lowered (at most {b['threshold']}).")
            d["threshold"] = b["threshold"]
        if b.get("auto_open") and not d.get("auto_open"):
            out.append(f"Breach detector {did}: it must open an incident automatically.")
            d["auto_open"] = True
    doc["detectors"] = dets


CHECKS = {"policy": _check_policy, "retention": _check_retention, "breach": _check_breach}


def check(kind, doc, base):
    """(corrected copy, list of violations). An empty list means the document meets the baseline."""
    fixed = copy.deepcopy(doc)
    out = []
    if kind in CHECKS and isinstance(fixed, dict):
        CHECKS[kind](fixed, base, out)
    return fixed, list(dict.fromkeys(out))


def describe(bases):
    """What the dashboard shows as locked, and the limits on each editable value."""
    pol, ret, br = bases["policy"], bases["retention"], bases["breach"]
    rp = {r["id"]: r for r in pol.get("rules", [])}
    rr = {r["id"]: r for r in ret.get("rules", [])}
    return {
        "version": BASELINE_VERSION,
        "policy": {rid: {"ref": rp[rid]["dpdp_ref"], "severity_min": rp[rid]["severity"],
                         **({"grace_max": lim["grace_max"]} if "grace_max" in lim else {})}
                   for rid, lim in POLICY_RULES.items() if rid in rp},
        "retention": {rid: {"ref": rr[rid].get("ref"), "why": lim["why"],
                            **({"keep_min": rr[rid]["keep"] if lim["keep_min"] == "default" else lim["keep_min"]} if lim.get("keep_min") else {}),
                            **({"keep_max": rr[rid]["keep"] if lim["keep_max"] == "default" else lim["keep_max"]} if lim.get("keep_max") else {}),
                            **({"notice_min": lim["notice_min"]} if lim.get("notice_min") else {})}
                      for rid, lim in RETENTION_RULES.items() if rid in rr},
        "breach": {
            "detectors": {d["id"]: {"ref": d.get("ref"), "severity_min": d["severity"], "threshold_max": d["threshold"], "auto_open": bool(d.get("auto_open"))}
                          for d in br.get("detectors", [])},
            "clocks_max": {k: {"max": mx, "why": why} for k, (mx, why) in CLOCK_MAX.items()},
            "anomaly": {"enabled": True, "sensitivity_min": ANOMALY_MIN_SENS},
        },
    }
