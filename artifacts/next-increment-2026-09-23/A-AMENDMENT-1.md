# A setup amendment 1

The first owned attempt exited before a reference HTTP request because the new runner omitted the repository root from `sys.path`, so `reference.seed` was unavailable. No action outcome was observed. The failed receipt remains at `A-RAW.json` with SHA-256 `bc52cfdafdd12da989a0a19903da4003e1244255a13a408fc7e1573701704511`. Commit `81f148a8ffd1272797dd870a4b92d5aa8cae8fba` adds the path. The case inventory and request cap are unchanged. The next run uses `A-FROZEN-A1.json` and a new output path.
