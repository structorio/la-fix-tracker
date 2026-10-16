#!/usr/bin/env python3
"""Pull last 90 days of public service-request data and write aggregate JSON (no addresses)."""
import json, subprocess, statistics, datetime as dt, re, time, os, sys
DAYS = 90
NOW = dt.datetime.now(dt.timezone.utc)
SINCE = NOW - dt.timedelta(days=DAYS)
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
CATS = ["Potholes & pavement", "Streetlights", "Illegal dumping", "Graffiti", "Sidewalks & curbs"]

def get(url, params=None, tries=5):
    cmd = ["curl", "-s", "-m", "180", "-G", "-A", "la-fix-tracker (fix.kordaris.com)", url]
    for k, v in (params or {}).items(): cmd += ["--data-urlencode", f"{k}={v}"]
    for i in range(tries):
        r = subprocess.run(cmd, capture_output=True, text=True).stdout
        try: return json.loads(r)
        except Exception: time.sleep(10 * (i + 1))
    raise RuntimeError("fetch failed: " + url)

def parse(s):
    if not s: return None
    s = s.replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:  # LA Socrata timestamps are local Pacific time
        d = d.replace(tzinfo=dt.timezone(dt.timedelta(hours=-7)))
    return d

def stats(rows):
    """rows: list of (created, closed|None). Medians over closed cases; %-within uses only cases old enough."""
    n = len(rows); closed = [(c, x) for c, x in rows if x and x >= c]
    days = [(x - c).total_seconds() / 86400 for c, x in closed]
    def within(k):
        elig = [(c, x) for c, x in rows if (NOW - c).days >= k]
        if not elig: return None
        ok = sum(1 for c, x in elig if x and (x - c).total_seconds() / 86400 <= k)
        return round(100 * ok / len(elig), 1)
    return {"requests": n, "closed": len(closed), "open": n - len(closed),
            "median_days": round(statistics.median(days), 1) if days else None,
            "same_day_pct": round(100 * sum(d < 1 for d in days) / len(days), 1) if days else None,
            "pct_7d": within(7), "pct_30d": within(30)}

# ---------------- City of Los Angeles (MyLA311 Cases 2026, data.lacity.org) ----------------
LA_TYPES = {"Street Pavement Issues": CATS[0], "Streetlight Repair Services": CATS[1],
            "Illegal Dumping Item Pickup": CATS[2], "Graffiti Removal": CATS[3],
            "Report a Sidewalk Problem": CATS[4], "Curb Issues": CATS[4]}
def la():
    rows, off = [], 0
    where = "createddate > '%s' AND type in(%s)" % (SINCE.astimezone(dt.timezone(dt.timedelta(hours=-7))).strftime("%Y-%m-%dT%H:%M:%S"),
                                                   ",".join("'%s'" % t for t in LA_TYPES))
    while True:
        b = get("https://data.lacity.org/resource/2cy6-i7zn.json", {"$select": "type,createddate,closeddate,locator_council_district,locator_sr_neigborhood_council_1",
               "$where": where, "$order": "casenumber", "$limit": 50000, "$offset": off})
        rows += b; off += 50000
        print("LA", len(rows), file=sys.stderr)
        if len(b) < 50000: break
    return [(LA_TYPES[r["type"]], parse(r["createddate"]), parse(r.get("closeddate")),
             r.get("locator_council_district"), (r.get("locator_sr_neigborhood_council_1") or "").title()) for r in rows]

# ---------------- SeeClickFix public API (cities where residents/cities use SCF) ----------------
SCF_KW = [(CATS[0], r"pothole|pavement|asphalt|road (damage|repair)|street repair|crack(ed)? (street|road)"),
          (CATS[1], r"street ?light|light out|lamp"),
          (CATS[2], r"dump|bulky|abandoned (item|furniture|trash)|trash|debris"),
          (CATS[3], r"graffiti|tag(ging)?\b|vandal"),
          (CATS[4], r"sidewalk|curb|trip hazard")]
def scf_cat(txt):
    t = (txt or "").lower()
    for c, rx in SCF_KW:
        if re.search(rx, t): return c
    return None
def scf(cities):
    out, seen = [], set()
    lat0, lat1, lng0, lng1, N = 33.33, 34.83, -118.95, -117.41, 4  # tile the region; API caps at 25 pages per query
    for a in range(N):
        for b in range(N):
            box = {"min_lat": lat0 + a * (lat1 - lat0) / N, "max_lat": lat0 + (a + 1) * (lat1 - lat0) / N,
                   "min_lng": lng0 + b * (lng1 - lng0) / N, "max_lng": lng0 + (b + 1) * (lng1 - lng0) / N}
            p, fails = 1, 0
            while p <= 25:
                d = get("https://seeclickfix.com/api/v2/issues", dict(box, after=SINCE.isoformat(), per_page=100, page=p,
                        status="open,acknowledged,closed,archived"))
                if "issues" not in d:
                    fails += 1
                    if fails > 4: break
                    time.sleep(30); continue
                for i in d["issues"]:
                    if i["id"] in seen: continue
                    seen.add(i["id"])
                    addr = i.get("address") or ""
                    city = next((c for c in cities if re.search(r"\b%s,?\s+(CA|California)\b" % re.escape(c), addr, re.I)), None)
                    if not city or city == "Los Angeles": continue  # LA uses MyLA311, not SCF
                    cat = scf_cat(((i.get("request_type") or {}).get("title") or "") + " " + (i.get("summary") or ""))
                    if not cat: continue
                    out.append((city, cat, parse(i["created_at"]), parse(i.get("closed_at")) if i["status"] in ("Closed", "Archived") else None))
                print("SCF tile", a, b, "page", p, len(out), file=sys.stderr)
                if not d["metadata"]["pagination"]["next_page"]: break
                p += 1; time.sleep(2)
    return out

def main():
    meta = json.load(open(os.path.join(OUT, "cities_meta.json")))
    pop = {c["name"]: c.get("population") for c in meta["cities"]}
    cities = sorted(pop, key=len, reverse=True)
    result = {"generated": NOW.isoformat(timespec="minutes"), "window_days": DAYS, "since": SINCE.date().isoformat(), "categories": CATS, "cities": []}
    def add(name, county, source, rows_by_cat, min_n=30):
        allrows = [r for v in rows_by_cat.values() for r in v]
        s = stats(allrows); s.update(name=name, county=county, source=source, population=pop.get(name),
               by_category={c: stats(v) for c, v in rows_by_cat.items() if v})
        s["per_1k"] = round(1000 * s["requests"] / pop[name], 2) if pop.get(name) else None
        s["ranked"] = s["requests"] >= min_n and s["closed"] >= 10
        result["cities"].append(s)
    L = la(); by = {c: [] for c in CATS}
    for c, cr, cl, *_ in L: by[c].append((cr, cl))
    add("Los Angeles", "Los Angeles", "MyLA311 (data.lacity.org, dataset 2cy6-i7zn)", by)
    # LA breakdowns
    def group(idx, label):
        g = {}
        for r in L:
            k = r[idx]
            if not k: continue
            g.setdefault(k, {c: [] for c in CATS})[r[0]].append((r[1], r[2]))
        res = []
        for k, v in g.items():
            allr = [x for vv in v.values() for x in vv]
            st = stats(allr); st["name"] = (f"District {k}" if label == "cd" else k); st["by_category"] = {c: stats(x) for c, x in v.items() if x}
            res.append(st)
        return sorted(res, key=lambda s: (s["median_days"] is None, s["median_days"] or 0))
    json.dump({"generated": result["generated"], "council_districts": group(3, "cd"), "neighborhood_councils": group(4, "nc")},
              open(os.path.join(OUT, "la_breakdown.json"), "w"), separators=(",", ":"))
    S = scf(cities); g = {}
    for city, cat, cr, cl in S: g.setdefault(city, {c: [] for c in CATS})[cat].append((cr, cl))
    county = {c["name"]: c["county"] for c in meta["cities"]}
    for city, v in g.items():
        add(city, county[city], "SeeClickFix public API (resident reports)", v)
    result["cities"].sort(key=lambda s: (not s["ranked"], s["median_days"] if s["median_days"] is not None else 1e9))
    json.dump(result, open(os.path.join(OUT, "leaderboard.json"), "w"), separators=(",", ":"))
    for f in ("leaderboard", "la_breakdown", "cities_meta"):
        d = open(os.path.join(OUT, f + ".json")).read()
        open(os.path.join(OUT, f + ".js"), "w").write("window.%s=%s;" % (f.upper(), d))
main()
