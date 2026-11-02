# Release and submission instructions

## What is already a Python package

This source tree is installable through pyproject.toml. The distribution name is
splitmend, the import is `splitmend`, and the CLI is `splitmend`. A wheel and source
distribution are built and tested locally. No Python committee approval is required.
PyPI hosting, GitHub publication and journal acceptance are three separate processes.

The PyPI JSON lookup for splitmend returned HTTP 404 on 2026-11-02. This does not reserve
the name or guarantee availability: PyPI can reject reserved/conflicting names. A
pending publisher also does not reserve a name before the first successful upload.

## Publish the GitHub repository

1. Create a repository named SplitMend under your own GitHub account. The commands below
   use the previously supplied username ravishanker39; change it if you choose another
   account. No repository at that URL is claimed to exist yet.
2. From the unpacked SplitMend directory, review .gitignore. Raw archives and large derived
   manifests are intentionally excluded from Git history; retain the research bundle
   as a release asset or DOI-backed dataset archive.
3. Run the following after creating the empty remote repository:

```sh
git init -b main
git add .
git commit -m "Release SplitMend 0.1.0 with reproducible evaluation"
git remote add origin https://github.com/ravishanker39/SplitMend.git
git push -u origin main
git tag v0.1.0
git push origin v0.1.0
```

If using the already initialized working repository, skip `git init` and do not create
a second initial commit. Attach the complete research bundle and checksums to the
GitHub release. Do not upload credentials, virtual environments or private datasets.

## Register PyPI and TestPyPI accounts

Create separate accounts at https://pypi.org/account/register/ and
https://test.pypi.org/account/register/. Verify your email and configure the required
two-factor authentication. Keep recovery codes privately. Do not send passwords or API
tokens through chat. Account creation and authentication are owner actions; they have
not been performed on your behalf.

## Trusted publishing with the supplied workflow

1. In GitHub repository settings, create environments named `testpypi` and `pypi`.
2. In each index's account Publishing page, add a pending GitHub publisher:
   project `splitmend`; owner your actual GitHub username; repository `SplitMend`;
   workflow filename `publish.yml`; environment `testpypi` or `pypi` respectively.
3. In GitHub Actions, run **Publish Python distribution** with target `testpypi`.
4. Check the package from a fresh environment. Install dependencies from normal PyPI,
   then the test distribution without dependency resolution:

```sh
python -m venv test-install
# Activate test-install as appropriate for your operating system.
python -m pip install 'numpy>=1.26,<3' 'scipy>=1.11,<2'
python -m pip install --index-url https://test.pypi.org/simple/ --no-deps splitmend==0.1.0
splitmend --version
```

5. Once verified, run the workflow with target `pypi`. A successful initial upload
   creates the PyPI project. Then users can run `python -m pip install splitmend`.
6. Public releases cannot reuse the same uploaded filename. Fixes need a new version;
   update pyproject.toml, __init__.py and CITATION.cff consistently.

For a manual build, run `python -m build` and `python -m twine check dist/*`.
Trusted publishing avoids maintaining a long-lived upload token in the repository.

## SoftwareX submission

Use article type Original Software Publication. The manuscript follows the software
article structure: motivation, software description, illustrative example, impact and
conclusions, with a code metadata table. The final permanent release URL/DOI must be
inserted after publication; a local ZIP is not represented as a registered DOI.

Before submitting, the author must review and approve the methods, numerical results,
interpretation, authorship contributions and competing-interest declaration. No funding
was reported by the author. This does not waive a journal article publishing charge;
check the journal open-access page and any institutional agreement before submission.
No publication payment has been made. The package has no OpenAI API dependency or API requirement.
Separately, ChatGPT/Codex assisted software development, analysis and manuscript drafting;
Elsevier requires an accurate declaration for this substantive assistance. Removing the
declaration would not make the manuscript comply with that policy.

The manuscript does not claim independent-host reproduction, external adoption, new
dataset defects, or superiority where simpler methods tie the optimum. CI files are
prepared but remote GitHub Actions runs are not claimed until the repository is pushed.

Official sources checked 2026-11-02:

* https://packaging.python.org/en/latest/tutorials/packaging-projects/
* https://docs.pypi.org/your-account/two-factor-authentication/
* https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/
* https://docs.pypi.org/trusted-publishers/adding-a-publisher/
* https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals
* https://www.sciencedirect.com/journal/softwarex/publish/guide-for-authors
