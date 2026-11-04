# GitHub README clean-style update

This package restores the original waving header and footer, the live Gitanimals farm, and the Snake animation. It removes the large rectangular backgrounds introduced by the previous version of the local SVG GitHub stats.

## Files to replace in `qlsl1198/qlsl1198`

1. `README.md`
2. `scripts/generate_profile_stats.py`
3. `scripts/verify_profile.py`
4. `assets/stats.svg`, `assets/languages.svg`, `assets/contributions.svg`

Keep `.github/workflows/profile-stats.yml` and the existing Snake Animation workflow unchanged; both remain compatible.

Commit these files to the `main` branch. If the daily stats workflow has been running successfully it will later overwrite only the three stats SVG files with the same clean transparent layout. Use Actions → Update profile statistics → Run workflow for an immediate refresh.

The older `assets/header.svg`, `assets/footer.svg`, and `assets/gitanimals-link.svg` are no longer referenced. They may be deleted later, but leaving them in the repository will not display anything.

## Verify locally

```sh
python scripts/verify_profile.py
python -m py_compile scripts/generate_profile_stats.py
```

Because GitHub app permissions currently reject file writes (HTTP 403), this zip does not automatically modify the remote GitHub repository.
