import json
import os
import re
import urllib.request
from xml.sax.saxutils import escape

EXCLUDE_LANGS = set()
TOP_N = 6

# ---- SVG style -------------------------------------------------------------
GRAD_START = "#8b5cf6"  # purple
GRAD_END = "#ec4899"    # pink

WIDTH = 470
ROW_H = 32
PAD_Y = 12
LABEL_X = 16
TRACK_X = 140
TRACK_W = 250
BAR_H = 12
PCT_X = TRACK_X + TRACK_W + 14

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
THEMES = {
    "light": {"text": "#1f2328", "track": "#d8dee4"},
    "dark": {"text": "#e6edf3", "track": "#30363d"},
}


def api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def fetch_top_languages():
    repos, page = [], 1
    while True:
        data = api(f"https://api.github.com/user/repos?affiliation=owner&per_page=100&page={page}")
        if not data:
            break
        repos += [r for r in data if not r["fork"]]
        page += 1

    totals = {}
    for r in repos:
        for lang, size in api(r["languages_url"]).items():
            if lang not in EXCLUDE_LANGS:
                totals[lang] = totals.get(lang, 0) + size

    total_bytes = sum(totals.values()) or 1
    print(f"repos found: {len(repos)}, languages found: {len(totals)}")
    top = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:TOP_N]
    return top, total_bytes


def build_svg(top, total_bytes, theme):
    colors = THEMES[theme]
    height = PAD_Y * 2 + ROW_H * len(top)
    max_size = top[0][1] if top else 1
    radius = BAR_H / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="Top languages">',
        f'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" '
        f'x1="{TRACK_X}" y1="0" x2="{TRACK_X + TRACK_W}" y2="0">'
        f'<stop offset="0" stop-color="{GRAD_START}"/>'
        f'<stop offset="1" stop-color="{GRAD_END}"/></linearGradient></defs>',
        f'<g font-family="{FONT}" font-size="14" fill="{colors["text"]}">',
    ]

    for i, (lang, size) in enumerate(top):
        pct = size / total_bytes * 100
        mid = PAD_Y + i * ROW_H + ROW_H / 2
        bar_y = mid - BAR_H / 2
        # bars are scaled to the top language; the printed % is the true share
        bar_w = max(size / max_size * TRACK_W, BAR_H)
        parts += [
            f'<text x="{LABEL_X}" y="{mid}" dy=".35em">{escape(lang)}</text>',
            f'<rect x="{TRACK_X}" y="{bar_y}" width="{TRACK_W}" height="{BAR_H}" '
            f'rx="{radius}" fill="{colors["track"]}"/>',
            f'<rect x="{TRACK_X}" y="{bar_y}" width="{bar_w:.1f}" height="{BAR_H}" '
            f'rx="{radius}" fill="url(#g)"/>',
            f'<text x="{PCT_X}" y="{mid}" dy=".35em" font-weight="600">{pct:.1f}%</text>',
        ]

    parts.append("</g></svg>")
    return "\n".join(parts) + "\n"


def build_readme_block(top, total_bytes):
    summary = ", ".join(f"{lang} {size / total_bytes * 100:.1f}%" for lang, size in top)
    alt = escape(f"Top languages: {summary}", {'"': "&quot;"})
    return (
        "<picture>\n"
        '  <source media="(prefers-color-scheme: dark)" srcset="langs-dark.svg">\n'
        '  <source media="(prefers-color-scheme: light)" srcset="langs-light.svg">\n'
        f'  <img alt="{alt}" src="langs-light.svg">\n'
        "</picture>"
    )


def main():
    top, total_bytes = fetch_top_languages()

    with open("README.md", encoding="utf-8") as f:
        content = f.read()

    pattern = r"<!--LANGS_START-->.*?<!--LANGS_END-->"
    if not re.search(pattern, content, flags=re.DOTALL):
        raise SystemExit("README.md is missing the <!--LANGS_START--> / <!--LANGS_END--> markers")

    for theme in THEMES:
        with open(f"langs-{theme}.svg", "w", encoding="utf-8") as f:
            f.write(build_svg(top, total_bytes, theme))

    block = build_readme_block(top, total_bytes)
    new = re.sub(
        pattern,
        lambda m: f"<!--LANGS_START-->\n{block}\n<!--LANGS_END-->",
        content,
        flags=re.DOTALL,
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new)


if __name__ == "__main__":
    main()
