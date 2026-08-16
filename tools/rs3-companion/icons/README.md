# Custom ability icons (optional)

Everything else in this repo is original — including the generated
placeholder badges the app draws by default. Real RS3 ability icons are
Jagex's copyrighted game art, so they're not bundled here and never
will be; this folder exists so *you* can drop in your own instead, for
your own local use.

## How

Save a PNG per ability, named to match exactly (case-sensitive),
sourced from your own game client — a screenshot of the ability icon
cropped square works fine:

```
icons/
  Touch of Death.png
  Living Death.png
  Fury.png
  ...
```

Any ability without a matching file falls back to the generated badge
automatically — you don't need to cover every ability, just the ones
you care about.

Have a folder of icons already named with underscores instead of
spaces (e.g. from a batch download) sitting somewhere else on your PC?
`../import-icons.ps1` copies and renames them into here in one go —
see that script's header comment for usage.

This whole folder (except this README) is gitignored: your icons stay
local to your machine and are never pushed to the repo or included in
release zips.
