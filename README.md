# chatgpt-plugins

Plugins for the ChatGPT / Codex plugin directory.

| Plugin | What it does | Status |
| --- | --- | --- |
| [Billsmith Invoice Generator](plugins/billsmith) | Invoices, quotes, estimates and receipts as PDF files with exact totals | 1.0.0, not yet submitted |

## Layout

```
plugins/<name>/            the package that gets zipped and uploaded
  .codex-plugin/plugin.json  manifest and directory listing text
  assets/                    listing icons
  skills/<skill>/            SKILL.md plus scripts, references, assets
docs/                      public website (GitHub Pages): overview, support, privacy, terms
tools/build.py             sync shared files, validate, write dist/<name>-<version>.zip
tools/make_icons.py        redraw the icons (needs Pillow)
tools/make_site.py         regenerate docs/billsmith
tests/                     unit tests for the document engine
.agents/plugins/marketplace.json   local marketplace for testing in Codex / ChatGPT desktop
```

## Build and test

```bash
python3 -m unittest discover -s tests      # engine tests (pypdf and Pillow are optional extras)
python3 tools/build.py billsmith           # sync shared files, validate, write dist/billsmith-1.0.0.zip
python3 tools/build.py billsmith --check   # validate only
```

`skills/create-invoice` owns the shared files (`scripts/billdoc.py`,
`references/spec.md`, `assets/icon.png`). Edit them there; `tools/build.py`
copies them into the other skills, because every skill folder has to be
self-contained.

## Try it locally

```bash
codex plugin marketplace add /path/to/chatgpt-plugins
codex plugin add billsmith@williiam-plugins
codex exec "Invoice Acme for 10 hours of consulting at \$150/hour, from Northwind Studio"
```

After changing the plugin, run `codex plugin add billsmith@williiam-plugins`
again so the installed copy is refreshed.

## Publish

1. Verify your developer identity at <https://platform.openai.com/settings/organization/general>.
2. Make sure the four listing URLs in `plugin.json` are live (GitHub Pages serves `docs/`).
3. `python3 tools/build.py billsmith`, then upload `dist/billsmith-<version>.zip` at
   <https://platform.openai.com/plugins> (Upload new or existing plugin).
4. Resolve automated findings, submit for review, and publish once approved.

Updates: bump `version` in `plugin.json`, rebuild, and upload the new ZIP to the same plugin.

## Licence

MIT. See [LICENSE](LICENSE).
