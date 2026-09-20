r"""Copy docs/manual into the application so Help works offline.

docs/manual is the source of truth. This copies each chapter into
apps/client/assets/manual/, writes contents.json (order, titles and summaries)
and leaves links that only exist in the repository as plain text, because the
example files are not shipped with the application.

Run after editing a chapter, then rebuild:

    .\.venv\Scripts\python.exe scripts\sync_manual_assets.py

--check reports whether the shipped copy is stale instead of writing, for the
release checklist.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/manual'
TARGET = ROOT / 'apps/client/assets/manual'
# Links to files the application does not carry: keep the words, drop the link.
UNSHIPPED = re.compile(r'\[([^\]]+)\]\((?:examples/|\.\./)[^)]+\)')
CHAPTER_LINK = re.compile(r'\]\((\d[\w.-]*)\.md\)')


def convert(text):
    text = UNSHIPPED.sub(r'\1', text)
    return CHAPTER_LINK.sub(r'](chapter:\1)', text)


def summarize(text):
    """The chapter title and its first sentence of prose."""
    title = next((line[2:].strip() for line in text.splitlines() if line.startswith('# ')), '')
    summary = ''
    for block in text.split('\n\n'):
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if not lines or lines[0].startswith(('#', '|', '-', '>', '```', '*', '1.')):
            continue  # Heading, list, table or code, not a description.
        paragraph = ' '.join(lines)
        if paragraph.endswith(':'):
            continue  # An introduction to a list rather than a statement.
        summary = paragraph
        break
    summary = re.sub(r'\*\*|`|\[([^\]]+)\]\([^)]*\)', lambda m: m.group(1) or '', summary)
    return title, summary


def index_summaries():
    """The 'Covers' column of the contents table in README.md, per chapter file."""
    rows = re.findall(r'^\|\s*\d+\s*\|\s*\[[^\]]+\]\(([\w.-]+)\)\s*\|([^|]+)\|', (SOURCE / 'README.md').read_text(encoding='utf-8'), re.M)
    return {name: summary.strip() for name, summary in rows}


def build():
    chapters = []
    files = {}
    covers = index_summaries()
    for path in sorted(SOURCE.glob('*.md')):
        if path.name == 'README.md':
            continue
        text = convert(path.read_text(encoding='utf-8'))
        title, summary = summarize(text)
        chapters.append({'file': path.name, 'title': title, 'summary': covers.get(path.name, summary)})
        files[path.name] = text
    files['contents.json'] = json.dumps({'chapters': chapters}, indent=2, ensure_ascii=False) + '\n'
    return files


def main():
    files = build()
    check = '--check' in sys.argv
    stale = []
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        path = TARGET / name
        current = path.read_text(encoding='utf-8') if path.is_file() else None
        if current == text:
            continue
        stale.append(name)
        if not check:
            path.write_text(text, encoding='utf-8')
    for path in TARGET.iterdir():
        if path.name not in files:
            stale.append(f'{path.name} (removed)')
            if not check:
                path.unlink()
    if check:
        print('Stale in the application:', ', '.join(stale) if stale else 'nothing — the shipped manual matches docs/manual')
        return 1 if stale else 0
    print(f'{len(files) - 1} chapters synced to {TARGET}' + (f'; updated {", ".join(stale)}' if stale else '; already current'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
