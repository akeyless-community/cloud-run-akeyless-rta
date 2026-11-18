# Releasing

Releases are automated: pushing a tag `vX.Y.Z` runs [`.github/workflows/publish.yml`](../.github/workflows/publish.yml), which

1. checks the tag is on `main` and matches `__version__` in `src/akeyless_cloudrun_rta/__init__.py`
2. runs the tests and builds the wheel and sdist
3. publishes to [PyPI](https://pypi.org/project/akeyless-cloudrun-rta/) with trusted publishing (no API token), after approval of the `pypi` environment
4. creates the GitHub Release with generated notes and the built files attached

The version lives only in `__init__.py`; `pyproject.toml` reads it from there.

## One-time setup

1. **Make the repo public**, so the PyPI project links work.
2. **PyPI trusted publisher.** On [pypi.org](https://pypi.org): Account settings, Publishing, Add a new pending publisher:

   | Field | Value |
   |-------|-------|
   | PyPI Project Name | `akeyless-cloudrun-rta` |
   | Owner | `akeyless-community` |
   | Repository name | `cloud-run-akeyless-rta` |
   | Workflow name | `publish.yml` |
   | Environment name | `pypi` |

3. **GitHub environment.** Settings, Environments, New environment `pypi`. Add required reviewers (for example `@akeyless-community/cs-admin`) and limit deployment to tags matching `v*`.

## Cutting a release

From an up-to-date, clean `main`:

```bash
scripts/release.sh 0.2.0
```

The script sets `__version__`, commits `chore: release v0.2.0`, tags `v0.2.0` and pushes both. Then approve the `pypi` deployment in the Actions run.

If `main` is protected against direct pushes, bump `__version__` in a pull request instead. After it merges, run `scripts/release.sh 0.2.0` on `main`: the version already matches, so it only creates and pushes the tag.

## Versioning

[Semantic versioning](https://semver.org): patch for fixes, minor for new features or options, major for breaking changes to the client API, env vars or tool contract. A version can never be re-uploaded to PyPI; if a release is broken, ship the next patch.

## If something fails

- **Tag/version mismatch or tag not on main:** nothing was published. Delete the tag (`git push origin :refs/tags/vX.Y.Z && git tag -d vX.Y.Z`), fix, and release again.
- **PyPI step failed:** usually the trusted publisher fields do not match the table above. Fix them on PyPI and re-run the failed job.
- **Release step failed after PyPI succeeded:** re-run only the `github-release` job.
