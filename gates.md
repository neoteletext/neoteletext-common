# Gates and the work branch

Every neoteletext repository works this way (the owner's instruction of 29 October 2026: every process "as fast as possible", and "I need to know when I am committing to a long integration step"). `DEVELOPMENT.md` section 9 holds the rest of the rules for gates.

## Day to day, nothing long starts

1. Work on `livedevelopment`.
2. Build and run as often as you like: building or running a program runs no gate.
3. Commit whenever a step compiles: the commit gate checks only that.
4. Push `livedevelopment` whenever the work should be on GitHub: the push gate runs the tests, and nothing already passed on the same code.
5. Push to `main` only to integrate, when the owner says: that is the one long step. It prints its last measured time before it starts, so Ctrl-C stops it if now is not the time.

## The tiers

`scripts/check.sh commit | push | full`; the git hooks (`git config core.hooksPath .githooks`) run them. Never bypass a hook (`--no-verify`).

| Tier | Hook | What it adds |
|---|---|---|
| `commit` | `pre-commit`, every commit | The code compiles clean: formatting, Clippy or the type check, the cheap text checks. It checks what is staged and refuses while a part it reads has unstaged or untracked changes. |
| `push` | `pre-push` of any branch but `main` | The remaining feature shapes and the tests, on a clean tree at the commit pushed. |
| `full` | `pre-push` to `main` | Everything else: release and feature-off tests, fuzzing, licences, unused dependencies, the Linux host's steps running alongside. It fails if running it changed a committed file. |

- **Each gate says its cost first:** its last pass's time and its three slowest steps, then each step's time as it ends.
- **Nothing runs twice on the same code:** a pass records what it passed on, keyed on the paths the gates read, and a higher tier skips a lower one already passed there; a change to a document alone runs no gate again.
- **Nothing is skipped silently:** a missing tool or an unreachable host fails the gate.

## Where the gates live

- **One copy of the machinery,** in neoteletext-common's `gates/`: `gate.sh` (timing, records, tiers, the Linux host alongside) and the three hooks. Change it there, commit, and run `gates/sync`, which writes `scripts/gate.sh` and `.githooks/` into every repository `gates/repositories` names. Each repository's commit gate fails if its copy differs from neoteletext-common's at the commit the copy names.
- **Each repository's own steps,** in its `scripts/check.sh`: `CHECKED_PATHS`, `commit_steps`, `push_steps`, `full_steps` and `linux_steps`, then `gate_main`.
- **The copy to the Linux host compares content** (`rsync --no-times --checksum`): with this machine's times kept, a file edited here before the host's last build looks older than that build, and Cargo reuses the stale crate.
