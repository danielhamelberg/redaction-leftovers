# Problem search and selection

Done on 2026-10-27, before any code was written. The goal was a small open-source tool for a real,
evidenced, currently unmet problem, chosen on merit across domains. Star counts and dates were read
from the GitHub API on that day.

## Constraints applied before scoring

Candidates were excluded or penalised if they needed: paid APIs, scraping against a site's terms,
trading or financial advice, healthcare data, PII detection or de-identification, or numbers that
users would act on but that the tool could not verify (for example tax rates).

## Shortlist

| # | Problem | Demand evidence | Existing tools and why they fall short (or don't) |
|---|---|---|---|
| 1 | Fabricated or wrong references in papers (often from AI writing tools) | Several new tools built for it in 2026 | Well served: [citegate](https://github.com/chrisyangsong/citegate) (102★), [bibtex-verifier](https://github.com/Altman-conquer/bibtex-verifier) (143★), [citecheck](https://github.com/tobiasosDev/citecheck), [hallubib](https://pypi.org/project/hallubib/) |
| 2 | Low-quality and AI-generated pull requests swamping maintainers | [GitHub community discussion #185387](https://github.com/orgs/community/discussions/185387), GitHub's own statement of the problem | Well served: [anti-slop](https://github.com/peakoss/anti-slop) (849★), [slopguard](https://github.com/Blue-B/slopguard), [gatekeep](https://github.com/farrellh1/gatekeep) |
| 3 | GitHub Actions removing the Node 20 runtime | [GitHub changelog, 2025-09-19](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/) | Served and time-limited: [node24-ready](https://github.com/cosmichackerx/node24-ready), a jactionlint rule, Dependabot |
| 4 | EU Accessibility Act checks for sites and PDFs | [Accessibility statement study, Sept 2026](https://accessibility.build/research/accessibility-statements-2026) | Served: axe-core, veraPDF, [ariada](https://github.com/ariada-org/ariada), [OpenADA](https://github.com/techcto/openada); a small new tool adds little |
| 5 | Caption and subtitle quality (reading speed, line length) | Accessibility requirements for video | Served: [caption-checker](https://github.com/markksantos/caption-checker), timedtext-lint, vttlint, Subtitle Edit |
| 6 | Netherlands: end of net metering on 1 Jan 2027, effect on a household from its own meter data | [Rijksoverheid: salderingsregeling](https://www.rijksoverheid.nl/onderwerpen/energie-thuis/salderingsregeling) | Partly served: [jeroen.nl stroomanalyse](https://jeroen.nl/energie/stroomanalyse) (account, one free analysis), [duurzaamthuislab calculator](https://duurzaamthuislab.nl/posts/nieuwe-rekentool-saldering-eigen-meterdata-2026/), [thuisbatterij-simulatie](https://github.com/mark-vis/thuisbatterij-simulatie). Results depend on tariffs a tool cannot verify |
| 7 | Certificate expiry after Let's Encrypt stopped expiry emails, and shorter maximum lifetimes (200 days from March 2026) | [CA/B Forum Baseline Requirements](https://cabforum.org/working-groups/server/baseline-requirements/requirements/) | Served: [tlswatch](https://tlswatch.nl/), [cert-watch](https://github.com/hraedon/cert-watch/), [certinspect](https://github.com/mangrisano/certinspect), Uptime Kuma |
| 8 | Gene symbols turned into dates by spreadsheets | [Ziemann et al., Genome Biology 2016](https://link.springer.com/article/10.1186/s13059-016-1044-7) | Served: [gfix](https://github.com/sbooeshaghi/gfix/), Truke, uncorrupt, oct4th; Excel can now turn the conversion off |
| 9 | EU deforestation regulation: geolocation files rejected by the EU system | [EUDR GeoJSON file description](https://eudr.webcloud.ec.europa.eu/tracesnt/help/eudr-documentation/operator/geojson-description.html) | Served by [GeoRoots](https://georoots.eu/) (open source, offline browser editor and checker) |
| 10 | Dutch plain-language (B1) checks for public-sector text | Government plain-language policy | Served: [alletaal-lint](https://github.com/Amsterdam/alletaal-lint) (City of Amsterdam), [LiNT-II](https://github.com/vanboefer/lint_ii), [T-Scan](https://github.com/CentreForDigitalHumanities/tscan) |
| 11 | PDFs published after "redaction" that still contain the removed content | X-Ray issues open for years: [earlier revisions (#1, 2020)](https://github.com/freelawproject/x-ray/issues/1), [bookmarks (#2, 2020)](https://github.com/freelawproject/x-ray/issues/2), [highlighter redactions (#185, 2025)](https://github.com/freelawproject/x-ray/issues/185), [cross-hatched (#169, 2025)](https://github.com/freelawproject/x-ray/issues/169); [write-up of recovery from incremental updates](https://obscuraos.com/recover-redacted-pdf) | Partly served: [X-Ray](https://github.com/freelawproject/x-ray) (832★, maintained) finds text under rectangles and highlights only. [before-you-send](https://github.com/Waiga/before-you-send) (Python, Sept 2026, 0★) is broad: covered, invisible, background-coloured, clipped and off-page text, unapplied marks, attachments, metadata, and a count of retained earlier revisions; its README states that it does not tell structural history apart from replaced page content. [scrubzero](https://github.com/over-punch/scrubzero) (TypeScript, 0★) flags incremental saves inside a larger redaction toolkit whose audit also returns the recovered text. [PDFRecon](https://github.com/Rasmus-Riis/PDFRecon) is a forensic tool with no clear license |

## Scoring

Each criterion is scored 1 (weak) to 5 (strong). The gap counts double, because a new tool is only
worth publishing where existing ones fall short.

| # | Impact | Evidence | Gap (×2) | Can build well now | Total | Note |
|---|---|---|---|---|---|---|
| 1 | 4 | 4 | 1 | 4 | 14 | |
| 2 | 4 | 5 | 1 | 3 | 14 | |
| 3 | 3 | 5 | 1 | 5 | 15 | Problem ends once migrations finish |
| 4 | 4 | 4 | 1 | 2 | 12 | |
| 5 | 3 | 3 | 1 | 5 | 13 | |
| 6 | 3 | 4 | 2 | 3 | 14 | Penalised: users would act on cost figures the tool cannot verify |
| 7 | 3 | 4 | 1 | 5 | 14 | |
| 8 | 3 | 4 | 1 | 5 | 14 | |
| 9 | 4 | 3 | 2 | 3 | 14 | |
| 10 | 3 | 3 | 1 | 3 | 11 | |
| **11** | **4** | **4** | **2** | **5** | **17** | **Selected** (gap corrected from 3, see below) |

## Why #11

- **Impact.** A failed redaction cannot be undone once a file is public. It affects court filings,
  freedom-of-information releases and journalism, where the removed text is often the sensitive part.
- **Gap.** The best-known open tool has had "earlier versions" open since 2020. before-you-send
  reports that earlier revisions exist but, by its own README, does not tell harmless structural
  history from revisions whose page text was replaced; scrubzero's audit returns recovered text. No
  checker compared the words of each earlier revision with the final version and reported only
  what was removed, without printing it.
- **Feasible to do properly.** Each leftover can be built into a test PDF in code, so every claim is
  backed by a test.
- **Rule check.** The tool reads PDF structure only. It does not look for personal data, classify
  content, or de-identify anything, and it never prints the text it finds.

## How this tool relates to the others

It complements X-Ray rather than replacing it: run X-Ray for text under boxes in the current
version, and this tool for what the file keeps elsewhere. It overlaps with before-you-send on
several checks and covers more cases overall (see its README). The main difference is that this
tool compares the text of each earlier revision with the final version instead of only counting
revisions. Like before-you-send, it reports locations and sizes, not document content.

## Correction, 2026-10-29

The first version of this document, written on 2026-10-27, said that before-you-send "does not list
earlier revisions" and scored the gap for #11 as 3. That was wrong: before-you-send has an
`earlier_versions_retained` check that counts retained revisions. It does not compare their text
with the final version. The gap is rescored as 2, which brings #11 to 17; it is still the highest
total, so the selection stands. The descriptions above were corrected on the same date.
