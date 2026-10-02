Quartz AMBIGUOUS_LINK hotfix v2

The previous launcher used LF-only line endings, which Windows cmd.exe misparsed.
This package uses CRLF line endings and an ASCII launcher filename.

1. Extract this ZIP.
2. Run APPLY_HOTFIX.bat.
3. Confirm [OK] and SHA256 509c4bfa9972c34b6efe6444b27aef70a3ade65fb8c6528ae06eff9cb0ae53fd.
4. Run your Quartz publish BAT again.

The target script is backed up as quartz-prepare.cjs.before-link-hotfix.bak before replacement.
