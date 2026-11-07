# Publishing Patchsmith

The local repository uses `main` and retains the implementation history and green phase tags. No remote is configured yet. The source directory can keep its current name; the repository name on GitHub should be `patchsmith`.

## Create the remote

Create an empty GitHub repository named `patchsmith`. Leave the remote README, license and ignore options unchecked because these files already exist locally.

From the local source directory in PowerShell, replace `YOUR_ACCOUNT` below:

```powershell
git remote add origin https://github.com/YOUR_ACCOUNT/patchsmith.git
git remote -v
git push -u origin main
```

Optional: publish the green phase checkpoints too:

```powershell
git push origin --tags
```

If `origin` is already configured, inspect it first and use `git remote set-url origin ...` to correct it. Normal pushes preserve history; no force push is needed.

## Pin the catalog entry

After the source commit is pushed, obtain its full identifier:

```powershell
git rev-parse HEAD
```

In `catalog-entry.yaml`, replace the `<USER>` repository/docs placeholders and the all-zero SHA with that pushed source commit. The SHA identifies the source revision that Hermes should install. Commit the catalog changes separately; retain that source SHA rather than repeatedly replacing it with the catalog-edit commit.

Submit the completed entry through the Hermes plugin catalog contribution process. Repository creation, pushes and catalog submission are the owner's steps.

## Local verification

The latest implementation gate recorded 99 passed and 1 skipped; see `eval/hardware-tests.txt` and `docs/IMPLEMENTATION.md` for the measured environment and limits. To rerun the offline suite with Python and pytest available:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -B -m pytest tests -q -p no:cacheprovider --tb=short
```

The intentionally failing fixtures are collected only by the benchmark runner. Contributor benchmark instructions are in `benchmarks/README.md`.

Private implementation plans, local environment files, generated run state, Python caches and the local video workspace are ignored. Committed synthetic benchmark evidence remains part of the public source. Remote credentials belong in the Git credential manager or SSH agent, never in tracked files or remote URLs.
