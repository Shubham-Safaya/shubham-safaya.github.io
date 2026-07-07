#!/usr/bin/env python3
"""Portfolio stats strip — daily refresh (backbone 3a). Zero required keys.
GitHub API (unauthenticated ok from Actions GITHUB_TOKEN), pypistats public
API, Medium RSS, YouTube channel RSS."""
import json, os, datetime, urllib.request, xml.etree.ElementTree as ET

UA = {"User-Agent": "portfolio-refresh (github.com/Shubham-Safaya)"}
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def get(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=30).read()

def gh_json(path):
    h = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    return json.loads(get(f"https://api.github.com{path}", h))

out = {"fetched_at": datetime.datetime.utcnow().isoformat() + "Z", "stats": {}, "medium": [], "youtube": []}

# public repos + 90d commit activity (events API is lossy; use repo pushes)
try:
    repos = gh_json("/users/Shubham-Safaya/repos?per_page=100&type=owner")
    out["stats"]["public_repos"] = len(repos)
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=90)).isoformat()
    commits = 0
    for r in repos:
        if r.get("pushed_at", "") >= cutoff and not r.get("fork"):
            try:
                cs = gh_json(f"/repos/Shubham-Safaya/{r['name']}/commits?since={cutoff}&per_page=100&author=Shubham-Safaya")
                commits += len(cs)
            except Exception:
                pass
    out["stats"]["commits_90d"] = commits
except Exception as e:
    print("github:", e)

# PyPI downloads (last month)
try:
    d = json.loads(get("https://pypistats.org/api/packages/identity-resolver/recent"))
    out["stats"]["pypi_downloads_month"] = d["data"]["last_month"]
except Exception as e:
    print("pypi:", e)

# Medium RSS
try:
    root = ET.fromstring(get("https://medium.com/feed/@safayashubham"))
    items = root.findall(".//item")
    out["stats"]["medium_articles"] = len(items)
    for it in items[:8]:
        out["medium"].append({
            "title": it.findtext("title"), "link": (it.findtext("link") or "").split("?")[0],
            "date": it.findtext("pubDate", "")})
except Exception as e:
    print("medium:", e)

# YouTube channel RSS (no API key path)
try:
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    root = ET.fromstring(get("https://www.youtube.com/feeds/videos.xml?channel_id=UCOIelVdp5ciYxidzwhF46aA"))
    entries = root.findall("a:entry", ns)
    out["stats"]["youtube_videos"] = len(entries)  # RSS caps at 15; YOUTUBE_API_KEY (optional) gives the true count
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        d = json.loads(get(f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id=UCOIelVdp5ciYxidzwhF46aA&key={key}"))
        out["stats"]["youtube_videos"] = int(d["items"][0]["statistics"]["videoCount"])
    for e in entries[:6]:
        out["youtube"].append({"id": e.findtext("yt:videoId", "", ns), "title": e.findtext("a:title", "", ns)})
except Exception as e:
    print("youtube:", e)

os.makedirs("data/history", exist_ok=True)
json.dump(out, open("data/latest.json", "w"), indent=2)
json.dump(out, open(f"data/history/{datetime.date.today()}.json", "w"), indent=2)
print("stats:", out["stats"])
