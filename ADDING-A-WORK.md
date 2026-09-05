# Adding a work to the corpus

This file is a stub. The full recipe for adding a play to the drama corpus
(manifest shape, `play-line` citation scheme, Greek export via Diogenes,
English ingestion, speaker rosters, translation bench) is written at P1 of
the build plan, once the first real work (Agamemnon) has gone through the
pipeline end to end and the scheme freeze is done.

Until then, see `docs/plan.md`:

- "Architecture decisions" §2–5 for the citation scheme, speaker handling,
  English ingestion, and registry/data-model shape a manifest will need.
- The P1 phase entry for the exact acceptance criteria and file list for
  the first work.
- "Critical files to reuse" for which sibling-repo pipeline modules a new
  builder is ported from.

Do not write a new-work manifest against this stub — it predates the
`play-line` scheme and will be wrong. Wait for `docs/plan.md`'s P1 recipe,
or ask John.
