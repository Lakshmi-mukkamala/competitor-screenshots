import json
from .config import CATEGORIES


def prepare_daily_report(run_dir, targets, started_at):
    manifest = run_dir / 'manifest.json'
    report = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else dict(startedAt=started_at, results=[])
    keys = {(r['id'], r['page']) for r in report['results']}
    keys.update((t['id'], t['page']) for t in targets)
    report['targetCount'] = len(keys)
    report['date'] = run_dir.name
    report['lastRun'] = dict(startedAt=started_at, targetCount=len(targets), completedCount=0)
    report.pop('completedAt', None)
    return report


def replace_result(report, result):
    report['results'] = [r for r in report['results'] if (r['id'], r['page']) != (result['id'], result['page'])]
    report['results'].append(result)


def write_report(run_dir, report):
    (run_dir / 'manifest.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    lines = ['# Competitor screenshots', '', f'Date: {report["date"]}', '',
             f'Daily results: {len(report["results"])} / {report["targetCount"]} pages.', '',
             f'Latest run: {report["lastRun"]["completedCount"]} / {report["lastRun"]["targetCount"]} pages processed.', '',
             'Captured images passed automated popup checks; visually review the full image before use.', '']
    for category in CATEGORIES:
        rows = [r for r in report['results'] if r['category'] == category]
        if not rows:
            continue
        lines += [f'## {category}', '', '| Competitor | Page | Status | Image | Notes |', '| --- | --- | --- | --- | --- |']
        for row in rows:
            image = row.get('screenshot') or row.get('diagnostic')
            note = ' '.join([row.get('error', ''), *row['warnings']]).replace('|', '\\|').replace('\n', ' ')
            link = f'[Open]({image})' if image else '—'
            lines.append(f'| {row["competitor"]} | {row["page"]} | {row["status"]} | {link} | {note} |')
        lines.append('')
    (run_dir / 'README.md').write_text('\n'.join(lines), encoding='utf-8')
