# Expanded research update — 7 November 2026

This update adds `research/` and links it from the main README. It preserves the
root software source, tests, original experiment files, MIT license, CITATION.cff
and the existing v0.1.1 tag. No Python package behavior or version changes.

The public repository previously described the original 180 comparisons. The
expanded evaluation additionally contains 800 single-group and 160 coupled
OULAD method outputs. They are repeated policy scenarios, not independent
datasets. Code, reference outcomes and independent assignment audits are
available under `research/`; all five tables can be regenerated without paid APIs.

The core source is checked against both the public repository and the released
wheel. Singleton stripping was already present in v0.1.1. The equivalence script
checks all 40 coupled models with and without explicit preprocessing; the
expanded study does not claim a new singleton-stripping implementation.

The five-dataset sweep includes ties and heuristic feasibility failures. PAMAP2
has 12 feasible policies, of which the greedy portfolio solves six, plus 28
infeasible policies. Coupled OULAD has 36 certified optimal cases and four
infeasible cases. Against the best valid per-case greedy portfolio, its weighted
objective reduction is 3.72%; faster heuristic runtimes and limited scalability
remain part of the interpretation. See `research/tables/interpretation.json`.

The GitHub subset omits large original source ZIPs, submission documents and
duplicate historical/rerun archives. The original experiment downloader retrieves
missing public archives and verifies their recorded hashes. The complete unified
archive is now published at
[10.5281/zenodo.24046268](https://doi.org/10.5281/zenodo.24046268).
The expanded repository snapshot has DOI
[10.5281/zenodo.24046217](https://doi.org/10.5281/zenodo.24046217).
The original software and dataset DOIs continue to identify their earlier
versions. The [reviewer guide](REPRODUCING.md) provides the current numbered
reproduction steps and expected reports.

Package users continue to install `splitmend==0.1.1`. Publishing this research
update does not require uploading another wheel to PyPI or moving the v0.1.1 tag.
Reproduction commands, attribution and limits are in `research/README.md`.
