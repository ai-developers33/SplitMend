# Release maintenance

## Published software

* Source repository: https://github.com/ai-developers33/SplitMend
* Python package: https://pypi.org/project/splitmend/0.1.1/
* Current runtime version: 0.1.1
* Software license: MIT
* Maintainer: Ravi Shanker Thadishetti

The public wheel has been installed successfully in a fresh macOS environment using
Python 3.11.3, NumPy 2.4.6 and SciPy 1.17.1. Dependency checks passed and the command-line
interface reported version 0.1.1. This installation check is distinct from rerunning the
full experiment suite.

## Research materials

The repository contains the runtime library, tests, protocols, source-data attribution,
dependency lock files, comparison scripts, reference run records and summary tables.
The reproduction entry point is:

```sh
python scripts/reproduce.py --bootstrap
```

Use Python 3.12 on Linux with the supplied reference lock files. The harness downloads
the original public data archives, constructs the evaluation cases, runs 180 method
comparisons across 30 configurations, checks the saved assignments and writes the
completion record to `results/reproduction.json`.

Raw archives, derived manifests, assignment files and solver logs are excluded from Git
because of their size. Keep them with their source attribution and SHA-256 checksums in
the research archive. A complete archival deposit should include those files, the exact
source snapshot, environment records, protocol versions and reproduction instructions.
Dataset licenses remain separate from the MIT software license.

The recorded full experiment rerun was performed on the development host. Successful
package installation or continuous-integration tests do not establish independent
reproduction of the complete benchmark.

## Preparing a future version

1. Update the version consistently in `pyproject.toml`, `src/splitmend/__init__.py` and
   `CITATION.cff`, and record changes in `CHANGELOG.md`.
2. Run the source tests, build both distributions and check their metadata:

```sh
python -m pip install '.[test]' build twine
python -m pytest -q
python -m build
python -m twine check --strict dist/*
```

3. Test the wheel in a separate environment and check the source distribution's contents.
4. Push the reviewed commit and its version tag. Confirm that the GitHub tests pass.
5. Create the corresponding GitHub release and attach checksums and research artifacts.
6. Publish the new version using the configured publishing workflow or an upload token.

Version 0.1.1 is already published on PyPI. Its distribution filenames cannot be reused;
changes to the files distributed through PyPI require a new version. Updating GitHub
files does not replace an existing PyPI distribution.

## Documentation scope

Journal manuscripts, cover letters and author declarations are maintained separately.
This repository documents the software interface, experiments, measured results and
release process.
