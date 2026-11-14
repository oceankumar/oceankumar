"""Refresh public profile SVGs using GitHub APIs; no third-party credentials."""
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

USER = 'oceankumar'
OUT = Path('dist')
TOKEN = os.environ['GITHUB_TOKEN']


def api(path, data=None):
    body = json.dumps(data).encode() if data else None
    request = Request('https://api.github.com/' + path, data=body, headers={
        'Authorization': 'Bearer ' + TOKEN,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'OceanKumar-profile-assets',
        'X-GitHub-Api-Version': '2022-11-28',
    })
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def svg(theme, height, title, content, width=840):
    dark = theme == 'dark'
    colors = {'BG': '#0d1117' if dark else '#f6f8fa',
              'FG': '#f0f6fc' if dark else '#1f2328',
              'MUTED': '#919bab' if dark else '#59636e',
              'BORDER': '#30363d' if dark else '#d1d9e0',
              'ACCENT': '#b89aff' if dark else '#7546d8',
              'CYAN': '#67e8f9' if dark else '#096f83'}
    result = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">
<title id="title">{escape(title)}</title>
<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="12" fill="BG" stroke="BORDER"/>
<g font-family="system-ui,-apple-system,Segoe UI,sans-serif">{content}</g></svg>'''
    for key, value in colors.items():
        result = result.replace('"' + key + '"', '"' + value + '"')
    return result


def main():
    repos = []
    page = 1
    while True:
        batch = api(f'users/{USER}/repos?per_page=100&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    public = [r for r in repos if not r['private']]
    owned = [r for r in public if not r['fork']]
    languages = Counter()
    for repo in owned:
        languages.update(api(f"repos/{USER}/{repo['name']}/languages"))
    total = sum(languages.values())
    lang = '<text x="26" y="31" font-size="12" fill="ACCENT" letter-spacing="2">PUBLIC CODE / LANGUAGE MIX</text>'
    palette = ['#9575de', '#55b6c8', '#438cba', '#c084b6', '#ab985e', '#6f9d77']
    top = languages.most_common(5)
    other = total - sum(value for _, value in top)
    if other:
        top.append(('Other', other))
    if total:
        x = 26.0
        for (name, value), color in zip(top, palette):
            width = 368 * value / total
            lang += f'<rect x="{x:.2f}" y="49" width="{width:.2f}" height="9" fill="{color}"/>'
            x += width
        for i, ((name, value), color) in enumerate(zip(top, palette)):
            x = 26 + (i % 2) * 190
            y = 83 + (i // 2) * 26
            lang += f'<circle cx="{x+4}" cy="{y-4}" r="4" fill="{color}"/><text x="{x+16}" y="{y}" font-size="14" fill="FG">{escape(name)} <tspan fill="MUTED">{value/total:.1%}</tspan></text>'
    else:
        lang += '<text x="26" y="83" font-size="12" fill="MUTED">No public language data available.</text>'
    OUT.mkdir(exist_ok=True)
    for theme in ['dark', 'light']:
        (OUT / f'languages-{theme}.svg').write_text(
            svg(theme, 154, 'Language share by bytes in public non-fork repositories', lang, 420))
    counts = api(f'users/{USER}/events/public?per_page=100')
    event_types = Counter(event['type'] for event in counts)
    cards = {
        'base': ('GitHub activity', [
            ('Public repositories', len(owned)),
            ('Recent public events', len(counts)),
            ('Recent push events', event_types['PushEvent']),
            ('Recent pull request events', event_types['PullRequestEvent']),
        ]),
        'followup': ('Issues and pull requests', [
            ('Recent pull request events', event_types['PullRequestEvent']),
            ('Recent issue events', event_types['IssuesEvent']),
            ('Recent issue comment events', event_types['IssueCommentEvent']),
        ]),
    }
    for key, (title, rows) in cards.items():
        content = f'<text x="26" y="32" font-size="16" fill="ACCENT">{escape(title)}</text>'
        for i, (label, value) in enumerate(rows):
            content += f'<text x="26" y="{67 + i * 27}" font-size="14" fill="FG">{escape(label)}: {value}</text>'
        for theme in ['dark', 'light']:
            (OUT / f'metrics.{key}-{theme}.svg').write_text(svg(theme, 80 + len(rows) * 27, title, content, 420))
    days = Counter(event['created_at'][:10] for event in counts)
    today = datetime.now(timezone.utc).date()
    content = '<text x="26" y="30" font-size="16" fill="ACCENT">Recent public activity</text>'
    for i in range(84):
        day = today - timedelta(days=83-i)
        count = days[day.isoformat()]
        color = '#7546d8' if count >= 3 else '#b89aff' if count else '#30363d'
        x = 26 + (i // 7) * 31
        y = 48 + (i % 7) * 22
        content += f'<rect x="{x}" y="{y}" width="17" height="17" rx="3" fill="{color}"/>'
    content += '<text x="26" y="220" font-size="11" fill="MUTED">Last 84 days · public events returned by GitHub</text>'
    for theme in ['dark', 'light']:
        (OUT / f'metrics.isocalendar-{theme}.svg').write_text(svg(theme, 235, 'Recent public activity calendar', content, 420))
    stars = api(f'users/{USER}/starred?per_page=4')
    content = '<text x="26" y="32" font-size="16" fill="ACCENT">Recently starred</text>'
    for i, repo in enumerate(stars):
        content += f'<text x="26" y="{65 + i * 27}" font-size="14" fill="FG">{escape(repo["full_name"])}</text>'
    if not stars:
        content += '<text x="26" y="65" font-size="14" fill="MUTED">No public stars yet.</text>'
    for theme in ['dark', 'light']:
        (OUT / f'metrics.stars-{theme}.svg').write_text(svg(theme, 90 + len(stars) * 27, 'Recently starred', content, 420))
    print('Generated public profile metrics and language SVGs.')


if __name__ == '__main__':
    main()
