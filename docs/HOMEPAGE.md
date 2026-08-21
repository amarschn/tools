# Homepage data

The homepage reads `catalog.json` for tool names, descriptions, disciplines,
tags, review status, and links. It reads `data/homepage-tool-meta.json` for the
last directory change, directory commit count, and documented tool version.

Run this after committing a public-tool or catalog-version change, then amend
the task commit with the generated file:

```bash
python3 scripts/generate_homepage_metadata.py
```

The date and change count come from Git history for `tools/<slug>/`. They include
maintenance commits in that directory and do not include changes made only to
shared Python or frontend files. The count is labeled `repository changes`; it
is not a semantic version or verification count. A version appears only when
the catalog has an explicit `version` field.

`scripts/build_site.py` regenerates the sitemap and static homepage links, then
checks the committed metadata against Git history. JavaScript replaces the static links
after `catalog.json` loads. If JavaScript or the catalog request fails, those
links remain available. Missing metadata does not stop the tool index from
loading.

Opening a preview loads the real tool page in an iframe. The iframe URL carries
`homepage_preview=1`, and the homepage also records a `tool_preview` event, so
preview traffic can be separated from direct tool visits in analytics.
