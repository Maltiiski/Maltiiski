import json
import os
import re
import urllib.request

TOKEN = os.environ["GH_TOKEN"]
EXCLUDE_LANGS = set()
TOP_N = 6

BAR_WIDTH = 50 
PARTIALS = " ▏▎▍▌▋▊▉" 

def make_bar(pct):
    eighths = round(pct / 100 * BAR_WIDTH * 8)
    full, part = divmod(eighths, 8)
    return ("█" * full + PARTIALS[part]).strip() or "▏"

def api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)

repos, page = [], 1
while True:
    data = api(f"https://api.github.com/user/repos?affiliation=owner&per_page=100&page={page}")
    if not data:
        break
    repos += [r for r in data if not r["fork"]]
    page += 1

totals = {}
for r in repos:
    langs = api(r["languages_url"])
    for lang, size in langs.items():
        if lang not in EXCLUDE_LANGS:
            totals[lang] = totals.get(lang, 0) + size

total_bytes = sum(totals.values()) or 1
print(f"repos found: {len(repos)}, languages found: {len(totals)}")
top = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:TOP_N]

rows = ["| Language | Share | |", "|---|---|---|"]
for lang, size in top:
    pct = size / total_bytes * 100
    bar = make_bar(pct)
    rows.append(f"| {lang} | {pct:.1f}% | {bar} |")
table = "\n".join(rows)

with open("README.md", encoding="utf-8") as f:
    content = f.read()

new = re.sub(
    r"<!--LANGS_START-->.*?<!--LANGS_END-->",
    lambda m: f"<!--LANGS_START-->\n{table}\n<!--LANGS_END-->",
    content,
    flags=re.DOTALL,
)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new)
