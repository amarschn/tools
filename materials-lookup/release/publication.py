"""Keep source-document access out of the public static artifact."""
from pathlib import PurePosixPath
import re

SOURCE_FIELDS = ('id', 'title', 'organization', 'source_type', 'publication_date',
                 'revision', 'retrieved_date', 'license', 'notes', 'sha256')
DOCUMENT_SUFFIXES = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                     '.odt', '.ods', '.odp', '.rtf'}


def public_source(source):
    # An allowlist also excludes future private storage/download fields.
    return {key: source[key] for key in SOURCE_FIELDS if key in source}


def document_file(path, content):
    return (PurePosixPath(path).suffix.lower() in DOCUMENT_SUFFIXES or
            re.search(rb'(?m)^\s*%PDF-\d\.\d', content[:1024]) is not None or
            content.startswith(b'{\\rtf'))


def verify_public_outputs(outputs, sources):
    urls = [s['url'].encode() for s in sources]
    for path, content in outputs.items():
        if PurePosixPath(path).suffix not in {'.html', '.mjs', '.css', '.json', '.csv', '.txt'} and path not in {'_headers', 'README.md'}:
            raise ValueError(f'Unsupported public asset: {path}')
        if document_file(path, content):
            raise ValueError(f'Source document in public output: {path}')
        if any(url in content or url.replace(b'/', b'\\/') in content for url in urls):
            raise ValueError(f'Source document URL in public output: {path}')
        if re.search(rb'https?://[^\s<>"\x27]*\.(?:pdf|docx?|xlsx?|pptx?|ashx)(?:[?#\s<>"\x27]|$)', content, re.I):
            raise ValueError(f'Document link in public output: {path}')
