# Publishing Patchsmith

The public source is [icporcincula/patchsmith](https://github.com/icporcincula/patchsmith). Users can install it directly with `hermes plugins install icporcincula/patchsmith --enable`.

## Merge source changes

Open a pull request to `main`. The offline checks run on Windows and Linux. The maintainer reviews the change and merges manually after both checks pass. GitHub auto-merge is disabled.

## Pin the Hermes catalog entry

Update `catalog-entry.yaml` to the full SHA of the verified source commit. Keep the catalog-only update in a separate commit so the source SHA is immutable. If both commits travel in one pull request, use a merge commit so the pinned source revision remains in `main` history.

Check that the pin is reachable from the published branch before submitting the entry upstream:

```sh
git fetch origin main
git merge-base --is-ancestor <source-sha> origin/main
```

Submit the entry through the Hermes plugin catalog contribution process. The catalog revision changes when a new source revision is selected for review.
