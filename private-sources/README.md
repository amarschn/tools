# Private source documents

Put manufacturer datasheets and other original source documents here. Nothing
in this directory is committed except this file, and nothing in it may ever be
served.

## Why it sits here and not under `tools/`

`netlify.toml` publishes the repository root, and the documented local server
(`python -m http.server`) serves every file on disk, not just tracked ones. A
datasheets folder under `tools/` would therefore be reachable at
`http://<your-ip>:8000/tools/...` while you develop, and would sit inside the
tree that every script, reviewer and agent treats as shippable. Keeping it at
the root, named for what it is, removes both problems.

Git-ignored files are never uploaded to Netlify, because Netlify deploys from
the repository. So production is safe either way; the exposure this guards
against is the local preview server.

When you run a local server, prefer binding it to your own machine:

```sh
python3 -m http.server --bind 127.0.0.1
```

## What may and may not ship

The Materials tool publishes textual citations only: publisher, document title,
revision, page or table locator, the source literal, and a snapshot hash. It
must not contain document URLs, embeds, download endpoints, or the documents
themselves. That rule is enforced by the builder at compile time and by
`materials-lookup/builder/verify_release.py`, not only in the interface.

`tests/test_source_documents_stay_private.py` enforces the repository half of
it: no document may be tracked by git, and no document URL may appear in the
published Materials data.

## Layout

Organise however suits review. One workable shape:

```
private-sources/
  README.md            <- the only tracked file
  uddeholm/            <- by publisher
  outokumpu/
  ensinger/
```

The materials project can populate a private review index for you, with each
file checked against the SHA-256 recorded when it was reviewed:

```sh
python3 materials-lookup/builder/prepare_source_review.py \
  --pdf-dir private-sources --output-dir /private/tmp/materials-source-documents
```

That script refuses to write inside a repository or a preview server root, so
its output must go somewhere outside this tree.

## Paid access later

Offering documents to customers is not a matter of moving files here. It needs
reviewed distribution rights per document, private object storage with public
access disabled, sign-in, and server-side entitlement checks that fail closed.
It must not be done by hiding links or bundling files into the static site.
