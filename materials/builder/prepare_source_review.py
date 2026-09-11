#!/usr/bin/env python3
"""Copy pinned source PDFs and a review index into a private local directory."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def prepare(pdf_dir, output_dir):
    output_dir = output_dir.resolve()
    if output_dir == ROOT or ROOT in output_dir.parents:
        raise ValueError('Private source review must be outside the repository and preview server root')
    documents = json.loads((ROOT / 'curated/reference-manifest.json').read_text())['documents']
    sources = {s['id']: s for s in json.loads((ROOT / 'curated/sources.json').read_text())['sources']}
    # Verify the entire batch before copying anything.
    verified = []
    for document in documents:
        name = document['filename']
        if Path(name).name != name:
            raise ValueError('Source filename must not contain a directory')
        source = pdf_dir / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != document['sha256']:
            raise ValueError(f'{name}: source differs from the reviewed snapshot')
        verified.append((document, source))
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_dir.chmod(0o700)
    rows = []
    for document, source in verified:
        target = output_dir / source.name
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        target.chmod(0o600)
        citation = sources[document['id']]
        rows.append('<li><a href="' + quote(source.name) + '">' +
                    html.escape(citation['organization'] + ' — ' + citation['title']) +
                    '</a> · ' + html.escape(citation['revision'] or 'Undated') + '</li>')
    (output_dir / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<title>Source documents — local review</title><h1>Source documents</h1><ul>' +
        ''.join(rows) + '</ul></html>')
    (output_dir / 'index.html').chmod(0o600)
    return len(verified)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    count = prepare(args.pdf_dir, args.output_dir)
    print(f'{count} verified source documents: {args.output_dir.resolve() / "index.html"}')
