# Method, order and shared risks

## 1. How the analysis was made

- **Every source file of both repositories was read in full**, by crate group, with the questions of `00-conventions.md` in hand: what does this file hold, which concepts does it mix, how large are its functions and `impl` blocks, where are its tests, what does it reach in its siblings, and what would the file look like if it held one concept. The readings are recorded as the "Findings" section of each per-crate document, file by file, with line ranges, so that each proposed move can be checked against the code without re-reading it.
- **Three rounds.** The first round produced the per-crate findings. The second read across them for the shapes that repeat in both repositories (`30-cross-cutting.md`) and sent back to the per-crate documents the splits that must agree between siblings (the browser's panels, the engine's format readers, the protocol's message families). The third checked each target layout against the conventions, against the build's feature matrix, and against every importer of a path that moves, and fixed the order of the steps.
- **A finding is structural.** The plan records where code is and what shape it has, not whether it is right. A defect noticed in passing goes in `30-cross-cutting.md` section 5, for the owner to take up on its own.
- **The measure** is `00-conventions.md`. A file that meets it is left alone even if it is large (a table, one clause); a small file that mixes two concepts is still split.

## 2. The order of the work

The engine comes first, because the browser imports its paths at a pinned commit (`DEVELOPMENT.md` section 11): the engine's moves are pushed to `implementation` step by step; when they are done and the full gate has passed, `main` moves, and the browser re-pins once, updating every import in that one commit. Then the browser's own moves. Inside each repository the order is from the leaves to the roots, so that a step never has to be redone when a later one moves its parent.

| Phase | Repository | Crates | Why in this order |
|---|---|---|---|
| E1 | engine | `neoteletext-core` | Everything else imports it; its public paths are the ones the other crates and the browser name, so its re-exports are fixed first. |
| E2 | engine | `neoteletext-formats`, `neoteletext-slicer`, `neoteletext-image` | Depend on the core only. |
| E3 | engine | `neoteletext-web`, `neoteletext-input`, `neoteletext-qrkeyboard`, `neoteletext-audio`, `neoteletext-audio-mix` | Depend on the core; independent of each other, so they can be done in any order or in parallel branches merged to `implementation`. |
| E4 | engine | `neoteletext-app`, `neoteletext-cli`, `xtask`, fuzz targets, the firmware test image | Import everything above; their imports are fixed last. |
| E5 | engine | full gate, `main`, the browser's re-pin | One browser commit: the pin in all three workspaces, the lockfiles, the import paths that changed, nothing else. |
| B1 | browser | `protocol` | Every process imports it. |
| B2 | browser | `interface-core`, `confine`, `update` | Depend on `protocol` (or on nothing); independent of each other. |
| B3 | browser | `core`, `decoder`, `fetcher`, `interface`, `sound`, `keyboard`, `dock-menu`, `draw-*`, `web-opener` | The processes. |
| B4 | browser | `launcher`, `os-install`, `installer`, `stub`, `release-identity`, `tuf`, `site`, fuzz targets | The outer ring. |
| B5 | browser | `docs/architecture.md` section 14, the engine's `ARCHITECTURE.md`, `TECH-DEBT.md` | The documents say where code lives once it lives there. |

Each phase is one or more commits, each passing the gate; a phase is not begun until the one before is pushed (the engine) or committed (the browser), so that two phases never move the same file.

## 3. The gates each step passes

| Repository | At each commit | Before the branch moves |
|---|---|---|
| engine | `scripts/check.sh fast` (fmt, Clippy, tests, `check-constants`, `check-io`) | `scripts/check.sh full` before `main`: every feature set alone (`cargo xtask features`), the bare-metal images and their symbol check (`cargo xtask size`), the Linux host's stage |
| browser | `scripts/check.sh commit` (fmt, Clippy in every feature shape, tests, the tuf workspace, the engine pin) | `scripts/check.sh full` before a push: fuzz builds, the Linux stage, Windows by hand where a process's platform code moved |

A move that touches a platform module (`confine`, `dock-menu`, `os-install`, `web-opener`, the sound helper) is also run by hand on that platform before its commit, as `DEVELOPMENT.md` section 12 asks for anything platform-specific.

## 4. Risks shared by every step

| Risk | How each step meets it |
|---|---|
| **A feature combination stops building** because an item moved into a file gated on one feature is used by code gated on another | The target layouts put every item used by two features in an ungated parent; the engine's `cargo xtask features` and the browser's per-area Clippy runs are in the gates. |
| **A public path changes** and an importer in the other repository or a fuzz target breaks | Each per-crate document lists the crate's public paths and every importer (both repositories' `grep` results); a re-export in `lib.rs` keeps the path wherever it can; where it cannot, the importers are updated in the same commit or, across repositories, in the re-pin commit. |
| **The no-panic list is missing from a new root** | New crate roots are not expected; a split makes modules, not crates. If one is made, `NO_PANIC_ROOTS` and the list are updated in the same commit. |
| **`unsafe` moves outside its permitted module** | The permitted modules are directories after the split (`confine/src/{linux,unix,windows}/`), each child file carrying the same `#![expect(unsafe_code, reason)]` as the parent had; requirement 10.12's text is updated to name the directories. |
| **A test helper shared by two modules is stranded** | Helpers become named `#[cfg(test)]` modules at the crate level in the step that first needs them. |
| **Formatting churn hides the move** | `cargo fmt` runs before the move commit on the unchanged tree, as a commit of its own if it changes anything, so that the move's diff is only the move. |
| **Two sessions in one repository** | Each phase is announced in the implementation log before it starts, and a session that finds HEAD moved under it stops and reports (`DEVELOPMENT.md` section 10.2). |
| **The documents fall behind** | Phase B5 and each engine phase's `ARCHITECTURE.md` line are part of the plan, not an afterthought; `docs/architecture.md` section 14 is rewritten once at B5 from the final tree. |

## 5. What is measured before and after

So that the plan can be judged by numbers, the per-crate documents record, and the carrying-out re-records:

- files per crate; lines per file (largest, median); files over 500 lines;
- functions over 80 lines and `impl` blocks over 300;
- test lines inline versus in `tests.rs`;
- `cfg` sites inside shared files;
- build and test time of each gate (a reorganisation should not slow the gate; many small files compile no slower than few large ones in one crate).
