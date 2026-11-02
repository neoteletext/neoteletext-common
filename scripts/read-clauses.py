#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf==5.9.0"]
# ///
"""Write a source document's clause file for `rdm import-clauses`, read from its PDF.

    uv run scripts/read-clauses.py "EN 300 706 V1.2.1" standard.pdf en706.clauses.json

A PDF's outline is not its list of headings: EN 300 706 V1.2.1's outline leaves out
clauses 11.2.2, 12.1 and 15.6.1 to 15.6.12, which its printed contents list and its
pages hold. So the clauses are the union of the two, and every entry is then found
on its page, whose word positions give the place a link should open at. An entry
that cannot be found stops the run: a wrong list must not reach the citations.

Needs poppler's pdftotext, for word positions (-bbox), and pypdf, for the outline.
"""

import hashlib
import html
import json
import re
import subprocess
import sys
from pypdf import PdfReader

# How far above a heading's line a link's top sits, in points. Measured from the
# ETSI files' own outlines: 842 - 73.7 (the heading's yMin on page 61) gives 768.3,
# and they point at 772 for a heading in the same place at the top of a page.
TOP_MARGIN = 4
# Words closer than this in yMin, in points, are one line. Half a line of the
# ETSI files' smallest text, which is 8 points.
SAME_LINE = 2
# Headings start at the left margin, about 56.7 points in the ETSI files; a table's
# cells and an indented list start well to the right of it.
HEADING_LEFT = 62
# An outline's destination and the heading it names agree to within a line of
# the largest heading, 16 points: more is a link that opens somewhere else.
OUTLINE_TOLERANCE = 18

NUMBER = r'\d+(?:\.\d+)*[a-z]?|[A-Z](?:\.\d+)+'
CLAUSE = re.compile(rf'^({NUMBER})\s+(.*)$')
ANNEX = re.compile(r'^Annex ([A-Z])\b[^:]*:?\s*(.*)$')
TABLE = re.compile(r'^Table ([A-Z]?\.?\d+)\s*:\s*(.+)$')
LEADER = re.compile(r'\s*(?:\.\s*){3,}\s*(\d+)\s*$')
CONTENTS_HEAD = re.compile(r'^Contents\s*$')


def page_lines(path):
    """Each page's height and its lines, top to bottom: (yMin, xMin, text)."""
    output = subprocess.run(['pdftotext', '-bbox', path, '-'], check=True, capture_output=True, text=True).stdout
    pages = []
    for chunk in re.split(r'(?=<page )', output)[1:]:
        height = float(re.search(r'height="([\d.]+)"', chunk)[1])
        words = [
            (float(m[2]), float(m[1]), html.unescape(m[3]))
            for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="[\d.]+" yMax="[\d.]+">(.*?)</word>', chunk)
        ]
        words.sort()
        lines = []
        for y, x, text in words:
            if lines and y - lines[-1][0] < SAME_LINE:
                lines[-1][1].append((x, text))
            else:
                lines.append((y, [(x, text)]))
        pages.append((height, [(y, min(row)[0], ' '.join(t for _, t in sorted(row))) for y, row in lines]))
    return pages


def split_title(title):
    """A heading's (kind, number, title), or None for one with no number."""
    if m := ANNEX.match(title):
        return 'annex', m[1], m[2]
    if m := CLAUSE.match(title):
        return 'clause', m[1], m[2]
    return None


def outline_entries(reader):
    entries = {}

    def walk(items):
        for item in items:
            if isinstance(item, list):
                walk(item)
                continue
            if heading := split_title(item.title.strip()):
                kind, number, title = heading
                entries[kind, number] = {'title': title, 'page': reader.get_destination_page_number(item) + 1, 'outline_top': item.top}

    walk(reader.outline)
    return entries


def contents_entries(pages):
    """The printed contents, which give a clause's title and its page. ETSI's
    printed page numbers are the file's page numbers: the positions prove it."""
    entries = {}
    start = next((n for n, (_, lines) in enumerate(pages) if any(CONTENTS_HEAD.match(t) for _, _, t in lines)), None)
    if start is None:
        return entries
    pending = ''
    for _, lines in pages[start:]:
        found = False
        for _, left, text in lines:
            if CONTENTS_HEAD.match(text):
                continue
            if m := LEADER.search(pending + ' ' + text):
                found = True
                if heading := split_title((pending + ' ' + text)[: m.start()].strip()):
                    kind, number, title = heading
                    entries[kind, number] = {'title': title, 'page': int(m[1])}
                pending = ''
            elif pending or (left < HEADING_LEFT and split_title(text)):
                pending = (pending + ' ' + text).strip()
        if not found:
            break
    return entries


def find_heading(lines, kind, number):
    """The heading's yMin on its page, or None."""
    for y, x, text in lines:
        words = text.split()
        if kind == 'annex' and words[0] == 'Annex' and len(words) > 1 and words[1].rstrip(':') == number:
            return y
        if kind == 'clause' and words[0] == number and x < HEADING_LEFT and len(words) > 1:
            return y
    return None


def main():
    short_name, path, output = sys.argv[1:4]
    reader = PdfReader(path)
    digest = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    pages = page_lines(path)
    if len(pages) != len(reader.pages):
        sys.exit(f'{path}: pdftotext reads {len(pages)} pages, pypdf {len(reader.pages)}')

    outline = outline_entries(reader)
    contents = contents_entries(pages)
    faults = []
    entries = []
    from_contents = []
    for key in list(outline) + [k for k in contents if k not in outline]:
        kind, number = key
        found_by = 'outline' if key in outline else 'text'
        place = outline.get(key) or contents[key]
        if key in outline and key in contents and contents[key]['page'] != place['page']:
            faults.append(f"{kind} {number}: the outline says page {place['page']}, the contents {contents[key]['page']}")
        height, lines = pages[place['page'] - 1]
        y = find_heading(lines, kind, number)
        if y is None:
            faults.append(f"{kind} {number}: no heading on page {place['page']}")
            continue
        top = round(height - y + TOP_MARGIN)
        outline_top = place.get('outline_top')
        if outline_top is not None and abs(float(outline_top) - top) > OUTLINE_TOLERANCE:
            faults.append(f'{kind} {number}: the outline opens at {outline_top}, the heading is at {top}')
        if key not in outline:
            from_contents.append(f'{kind} {number}')
        entries.append({'kind': kind, 'number': number, 'title': place['title'][:200], 'page': place['page'], 'top': top, 'found_by': found_by})

    seen = set()
    for number_of_page, (height, lines) in enumerate(pages, 1):
        for y, _, text in lines:
            if (m := TABLE.match(text)) and m[1] not in seen:
                seen.add(m[1])
                entries.append({'kind': 'table', 'number': m[1], 'title': m[2].strip()[:200], 'page': number_of_page, 'top': round(height - y + TOP_MARGIN), 'found_by': 'text'})

    if faults:
        sys.exit('\n'.join(faults))
    with open(output, 'w') as file:
        json.dump({'source': short_name, 'sha256': digest, 'entries': entries}, file, indent=1, ensure_ascii=False)
    counts = {}
    for entry in entries:
        counts[entry['kind']] = counts.get(entry['kind'], 0) + 1
    print(short_name, 'pages', len(pages), 'entries', len(entries), counts, 'not in the outline', from_contents, 'not in the contents', [f'{k} {n}' for k, n in outline if (k, n) not in contents])


if __name__ == '__main__':
    main()
