# The neoteletext development process

One process for the two neoteletext repositories:

- **`neoteletext-engine`** (`~/devel/neoteletext-engine`, `crowdwave/neoteletext-engine`): the teletext engine, its libraries and the `neottx` program.
- **`neoteletext-browser`** (`~/devel/neoteletext-browser`, `crowdwave/neoteletext-browser`): NeoTeletext, built on the engine at a pinned commit.

Written on 21 October 2026 by merging the owner's global instructions (`~/.claude/CLAUDE.md`), the engine's `CLAUDE.md`, `README.md`, `IMPLEMENTATION-LOG.md`, `TECH-DEBT.md`, `LICENSING.md`, `docs/spec/` and gate scripts, and the browser's `docs/requirements.md`, `docs/architecture.md`, `docs/licensing.md` and gate scripts. Where they disagreed, the rule chosen and its reason are in appendix A; appendix B lists what each repository still has to change to follow this document.

---

## 1. Authority

1. **The owner's global instructions** (`~/.claude/CLAUDE.md`) apply to both repositories. This document adds to them; it departs from them only where it says so, with the owner's decision cited.
2. **This document** is the development process. A repository's `CLAUDE.md` says what is particular to that repository and points here for the rest; where a repository's own text and this document disagree, this document holds until appendix B's change is made there.
3. **The standard, datasheet or specification is the source of truth** for behaviour. Read it before writing code against it and cite the clause in comments (`// EN 300 706 clause 9.3.1: ...`). A datasheet wins over a web snippet. Read PDFs with page ranges, not through a text extractor that mangles tables. Standards and datasheets live in `~/devel/teletext-reference/`, never in either repository.
4. **Each repository's requirements are its only normative text.** The engine's are `docs/spec/requirements/`; the browser's are `docs/requirements.md`. Decisions record choices and their reasons; design documents explain; neither overrides a requirement.
5. **Security overrides every other requirement** in both repositories (the engine's area SEC and decision E.32; the browser's decision 4 and requirement 1.2). A conflict is recorded as a decision and the other requirement is amended. No option may switch security off.
6. **Each fact has one home.** Link rather than restate. Process lives here; behaviour lives in the requirements; choices in the decisions; explanation in design documents; where code lives in the engine's `ARCHITECTURE.md` and the browser's `docs/architecture.md`.

## 2. How work proceeds

### 2.1 Working rules

- **Stay on the task as given.** Do not change approach, introduce an architecture or add a library without asking; a library is an architectural choice. At a wall, give the options and their trade-offs and wait. Fixing, debugging and finishing the approach in hand needs no permission.
- **Do the obvious follow-ons** that are mechanical, inside the work in flight and cleanly reversible. Ask at real forks: schema, naming, scope, anything destructive.
- **A request with several parts becomes a numbered checklist**, shown, then closed item by item. Anything not done is listed as NOT DONE with the reason. Nothing is dropped silently.
- **Find root causes.** Test the cheap hypothesis first.
- **Measure, don't reason.** Performance claims carry before and after numbers from an instrument shown to exercise the changed code.
- **Don't overengineer.** No compatibility shims or feature flags unless asked; delete what is replaced in the same change.
- **No documents or files nobody asked for.** Offer them.
- **Long-running tests run whole.** Start them, wait for the result, don't poke at them meanwhile.

### 2.2 Two modes: rapid iteration, then integration

The owner shapes behaviour by asking for changes and looking at the result (the owner's instruction of 13 October 2026). Work runs in two modes, in both repositories.

**Rapid iteration** is the default while behaviour is being shaped.
- Make the change, rebuild with the fast profile and show the result: in the engine `cargo build --profile iterate -p neoteletext-cli`, then `target/iterate/neottx`; in the browser `scripts/try.sh` (Clippy on every save) or `scripts/try.sh <crate> [filter]`, and the program itself. Check the output, then tell the owner it is ready to look at.
- Do not write tests, user-guide text, requirement prose, log rows or traceability yet. Run the existing tests of the code touched when that is quick.
- Commit rarely, and never bypass a hook: batch the work instead.
- **Everything owed goes in the repository's `TECH-DEBT.md`** as it arises: tests, requirements and decisions to record, documents to update, verification to run, shortcuts taken, loose ends. Nothing deferred may exist only in a reply.

**Integration** starts when the owner says the feature works as they expect. Work through its `TECH-DEBT.md` items, in this order:
1. record the decision and the requirements (sections 4 and 5);
2. write the tests, each failing on the old code (section 8);
3. update the user guide, the architecture document and the other documents;
4. add the implementation log row, if the work met a question without the owner (section 3.3);
5. regenerate traceability in the engine; update the requirement State lines in the browser;
6. commit through the gates in small commits that reference their issues (section 10), and remove each item from `TECH-DEBT.md` as it is done.

Behaviour may be tried before it is recorded, but none is committed without its decision and requirements.

### 2.3 A feature's life

A feature large enough to need design goes through these steps; both repositories have done so (the browser's hyperlinks and interaction work, the engine's areas AUD and INT).
1. **A proposal document** and, for anything that reads outside input or adds an input or output, **its own security analysis**, whose findings are applied to the proposal.
2. **An adoption decision** by the owner, which adds the requirements.
3. **The build.**
4. **"What building changed"**: a section of the proposal listing every departure from it, and a decision recording the build that names the departures for the owner to confirm.
5. **A confirming decision**, recorded in every repository whose decisions the departures touched.

### 2.4 Decisions while the owner is away

When the owner asks for work to continue without questions, decisions are taken and recorded as usual, marked as taken while the owner was away, and listed for the owner's review. An implementation log row records each question met.

## 3. Tracking work

### 3.1 GitHub issues

Both repositories track work in GitHub issues on their own repository (`crowdwave/neoteletext-engine`, `crowdwave/neoteletext-browser`). An issue links to the requirement or decision it serves rather than restating it.
- **Work starts from an issue.** If none exists, open one. During rapid iteration one issue per feature is enough; small changes go in `TECH-DEBT.md`.
- **Commits reference it**: `Refs #123` for progress, `Closes #123` on the commit that finishes it (section 10.1).
- **Log what you find.** A bug, a gap or a decision for the owner gets an issue, not just a mention in a reply. Decisions for the owner carry the `decision` label.
- **Keep the milestones true.** Close finished work with the commit that did it; close work the design has overtaken as "not planned" with the reason. Delete an issue only with the owner's agreement.
- Work that concerns the other repository is moved there.

### 3.2 `TECH-DEBT.md`

Each repository keeps one. Each item says what is owed and why. An item is removed when done, and moved to an issue when it needs the owner.

### 3.3 The implementation log

`IMPLEMENTATION-LOG.md` records the questions met while implementing without the owner and the answer taken, as rows: number, question, decision, reason. A row is amended in place ("*Amended 11 October 2026:*") or superseded by a later row that says so. Behaviour the standard leaves open is a decision (section 5), not a log row. A round of unattended work ends with a status section: what was done and how it was verified, a NOT DONE table with reasons, and what is for the owner to review.

### 3.4 Reporting

Lead with the result. Report a failure as a failure, with its output; never claim a check passed that was not run. Name uncertainty as a fact about the evidence ("untested on hardware").

## 4. Requirements

Each repository keeps its numbering, since numbers are cited everywhere: the engine's `REQ-<AREA>-<NNN>` in `docs/spec/requirements/<area>.md`, the browser's "Requirement <section>.<n>" in `docs/requirements.md`.

- **Numbers are permanent.** They are never reused; gaps are deliberate. A new requirement takes the next free number in its area or section.
- **Modal verbs.** "Shall" or "must" is mandatory; "should" is expected unless a recorded reason says otherwise; "may" is an option.
- **Every requirement has a reason and a verification.** Verification is a test (automated), a check (automated, in the check script), an inspection or a review (recorded by a person), or a demonstration.
- **The browser's requirements also carry a Source** (the decision that made them) **and a State**: met, partly met or not met, with dated evidence ("measured by `<test>` on 21 October 2026, release build") and what is missing. The engine's state is its generated traceability table (`cargo xtask traceability`, `docs/traceability.md`), regenerated at integration.
- **Phases.** In the engine a Phase 2 requirement carries a `*Phase:*` line under its title and is listed in `requirements/README.md` section F.0.1; Phase 1 must not depend on Phase 2, and a Phase 2 feature's tests come with it.
- **Writing.** Full narrative sentences; terms spelled out (the engine's glossary is `docs/spec/glossary.md`, the browser's `docs/architecture.md` section 17); the standard cited by clause or table.
- **References resolve.** Every requirement identifier cited anywhere must name one that exists. The engine's check is in its `CLAUDE.md`; write its scratch files to the session scratchpad or `tmp/`, not `/tmp`.
- **The engine's state machine tables are normative** (area FSM): if a table and prose disagree, fix both.

### 4.1 Changing a requirement

One set of forms, in both repositories:
- **Amended:** a line at the end of the requirement, `*Amended 20 October 2026 (decision E.95):* what changed.`, the decision named whenever there is one.
- **Withdrawn:** the title becomes `Withdrawn: <old title>`, so the engine's traceability tool recognises it, and the body says `Withdrawn on <date> (decision <n>): <why>.` In the browser the old statement is kept under **Was:**. The number is kept.
- **Moved:** a requirement that moves to the other repository is withdrawn here with "Moved to <repository> on <date>", and its number is kept.

## 5. Decisions

Each repository keeps its own series, since both are cited across the code, the documents and the other repository: the engine's **E.n** in `docs/spec/decisions.md` (Part E), the browser's **Decision n** in the table of `docs/architecture.md` section 2. A decision of one repository cited in the other names its repository: "the engine's decision E.95", "NeoTeletext's decision 46". Feature documents may number their own decisions ("`hyperlinks.md` decision 7"); design documents may letter theirs ("decision D3 of `audio-platforms.md`"); implementation log rows are "rows", not decisions.

- **Record before committing behaviour.** Behaviour the standard or the design leaves open is recorded, or the decision amended, before the change is committed (the engine's REQ-DOC-004). During iteration it is noted in `TECH-DEBT.md` and recorded at integration.
- **A decision says who decided and when** ("Decided by the owner on 20 October 2026", "Decided on 21 October 2026, on the owner's instruction", "taken while the owner was away, as the owner had instructed"), what was chosen, in numbered items where there are several, and its reason.
- **A dependency of a microcontroller crate** of the engine needs a decision (section 7).
- **Decisions keep their history.** They are never deleted or renumbered.

### 5.1 Changing a decision

The engine records changes in the decision's text; the browser in its table's "Now" column, with the text unchanged. The forms:

| Change | In the engine's text | In the browser's "Now" column |
|---|---|---|
| Amended | `*Amended 18 October 2026 (decision E.76):* ...` | Amended by decision 37: ... |
| No longer applies in part | `*Note of 20 October 2026:* what this decision says of ... no longer applies (decision E.95).` | Amended by decision n |
| Superseded | `*Superseded on 12 October 2026 by decision E.72:* ...` | Superseded by decision 33 |
| Withdrawn | the entry shrinks to one line that keeps its number: `**E.54 — <title>.** Withdrawn on 20 October 2026: <why> (decision E.95).` | Retired by decision 33 |
| Moved to the other repository | one line: `Moved out of the engine on 16 October 2026 (decision E.76) ...` | Moved: ... |
| Confirmed by the owner | `*Confirmed by the owner on 21 October 2026,* with the browser's decision 45: ...` | Confirmed by decision 46 |
| Still unconfirmed | (named in the decision) | Owner to confirm ... |

## 6. Code

- **Strictest settings, warnings as errors.** Never silence a whole category. A suppression is narrow, at its site, with its reason written (`#[allow(..., reason = "...")]`); the gates make warnings errors. When strictness breaks the build, the warnings are the work.
- **Lints, in both workspaces** (the engine is to add the last four, appendix B): `unsafe_code = "forbid"`; `missing_docs`; `unused_qualifications`; Clippy `pedantic`, with each workspace-wide exception listed and justified in `Cargo.toml`; `allow_attributes_without_reason`, `dbg_macro`, `todo` and `unimplemented`.
- **No panics where input comes from outside.** Every crate root that reads input from outside its process denies `indexing_slicing`, `unwrap_used`, `expect_used`, `panic`, `arithmetic_side_effects`, `unreachable`, `todo` and `unimplemented`, with one list kept identical across those roots by the check script (the browser's checks it today; the engine's core has the list). Tests may use them.
- **Unsafe code** only where the platform offers no safe interface, in a crate of its own that denies it everywhere else, with each unsafe block saying why it is sound (`undocumented_unsafe_blocks`). Today that is the browser's `dock-menu` and `web-opener`; the engine has none (a future FFI crate would be the place).
- **No magic numbers.** Every literal is named, derived in the code, or cites its source or measurement. **Each constant is defined once**; where two places must agree, assert it. Every teletext constant lives in the engine core's `consts` (REQ-GEN-014, checked by `cargo xtask check-constants`); every limit the browser uses is an engine constant used by name (browser requirement 2.4).
- **Use the vendor's symbols** for registers and bitfields.
- **Descriptive names** over abbreviations, except loop indices and names that mirror a standard exactly.
- **All input is untrusted.** Bound every allocation and every length before using it.
- **Comments say why**, never what, and cite the clause they follow.
- **The engine's libraries have no operating-system access**: no files, network, processes, environment, threads or clock (checked by `cargo xtask check-io`), and stop at the row renderer.
- **The engine's `no_std` rules** (REQ-GEN-006, REQ-GEN-016): no floating point, no atomics, no division or 64-bit arithmetic on hot paths, no `core::fmt` on hot paths, no deep recursion or large stack buffers, explicit byte order.
- **Waiting.** A program waits on what it needs (a channel, a socket's reader, a timer's deadline), never by sleeping a fixed interval and looking again (the engine's decision E.97, the browser's decision 46). A serial or console read returns as soon as the expected data arrives; a timeout is a ceiling, not a wait.
- **Formatting:** `cargo fmt` with the workspace's `rustfmt.toml` (the engine 120 columns, the browser 160; appendix A item 15).
- **TypeScript**, in the browser's prototypes: TypeScript only, function components and hooks, no global state, events between components, native CSS, linted with zero warnings.

## 7. Dependencies and licences

- **Every library needs the owner's approval by name**, whatever its licence and whichever crate uses it, before it is added. Record the approval in a decision. A system library is recorded in the repository's licensing document before it is used.
- **The engine's microcontroller crates** take a dependency only by a decision in Part E, and only one that builds `no_std` without allocation for `thumbv6m`, `riscv32imc` and Xtensa, uses no compare-and-swap or floating point, has no build script or native code, has its flash cost measured and passes the symbol check (REQ-GEN-017). `cargo xtask check-deps` compares each crate's dependencies with its permitted list.
- **Licences.** The projects are MIT, and nothing linked may change that: MIT, Apache-2.0 (with or without the LLVM exception), BSD-2-Clause, BSD-3-Clause, Zlib, ISC and CC0 are accepted; OFL for fonts; LGPL only as a system library linked dynamically and not shipped. Never GPL or AGPL; MPL or EPL only by the owner's decision. An exception in `deny.toml` names one crate and one licence, with its reason. The engine's `LICENSING.md` is the full rule; the browser's `docs/licensing.md` applies it.
- **No GPL code**, ever: zvbi, vhs-teletext, vbit2 and QTeletextMaker may run as separate programs or test oracles only; never copy their code or test files.
- **Versions.** `Cargo.lock` is committed in every workspace, including fuzzing's, and its changes are reviewed. Application crates (the browser's, and the engine's `neoteletext-app`, `neoteletext-cli` and `neoteletext-qrkeyboard`) pin their own dependencies' exact versions (`=x.y.z`), each with a comment giving its licence and reason. The engine's library crates use ordinary version requirements, so that a program depending on them can resolve; their lockfile is the pin for the engine's own builds.
- **When a lockfile must change, change only what has to.** `cargo update` without arguments upgrades every dependency; to move one source, let Cargo re-resolve (`cargo metadata`) or name the package (`cargo update -p <name>`), then check that the lockfile's diff touches nothing else.
- **No unused dependencies** (`cargo machete`). Advisories are checked by `cargo deny`; an advisory is ignored only with its reason and the owner's decision.
- **Credits.** A solution taken from another project is credited in `CREDITS.md`, naming the project, licence, version and the problem it solved; outside reference projects are not named in source code. Bundled third-party material keeps its licence and provenance beside it.
- **No copyrighted standards, datasheets, broadcast recordings or captures** in either repository. The engine's corpus is downloaded at test time and pinned by checksum, local files read from `$NEOTELETEXT_CORPUS`; the browser's sites built from recordings stay in ignored folders.
- **Fonts.** The engine bundles one font, Bedstead; its Noto-derived fonts are loaded at run time; no other font or ROM glyph is added (the engine's decisions E.72 and E.77).

## 8. Tests

- **A regression test fails on the old code.** Confirm it by running it there, and say so in the commit message. A fault is fixed in its own commit, with its test.
- **Assertions say exactly what they claim**: check the expected set, not a count.
- **Golden files carry a format version.** A change to pixels raises it and regenerates the golden files in the same commit, with the reason; check that only the expected pages changed.
- **Timed tests hold a budget** and print their numbers (the browser's latency test; the engine's typing test, REQ-INT-008). A timed test builds the programs it times.
- **Fuzzing.** Every reader of outside input has a fuzz target. Every input that ever found a fault is kept as a regression and replayed first.
- **Oracles** (zvbi and others) run as separate programs; their known differences are listed and explained (`tests/oracles/`).
- **The engine** also keeps line coverage of its core at 90 % or more, size and symbol budgets for the microcontroller builds (`cargo xtask size`), and each crate's build with no optional area and with each area alone (`cargo xtask features`, decision E.61).
- **Platform behaviour** that cannot run unattended is an ignored test run by hand, and its result is recorded with the date.

## 9. Gates

There is no continuous integration; the gates are local (the owner's instruction). One check script per repository runs every gate, and git hooks in `.githooks/` run it, enabled once per clone with `git config core.hooksPath .githooks`. Never bypass a hook (`--no-verify`); if a gate is slow, batch the work.

| Gate | When | What it must do |
|---|---|---|
| **Commit gate** | `pre-commit`, every commit | Formatting, Clippy with warnings as errors in every feature set the repository builds, lockfiles current, the no-panic list identical, the tests of what the commit touches, and the architecture checks. It checks what is staged: it refuses while a part it checks has unstaged or untracked changes, so what passed is what is committed. |
| **Full gate** | before anything reaches `main` on GitHub, and before a release | Everything: release tests, documentation tests, tests with optional areas compiled out, every target, fuzzing, licences and advisories, unused dependencies, the Linux build host, and in the engine size, features and coverage. It runs on a clean tree at the commit being pushed, and fails if running it changed a committed file. |

- **Nothing is skipped.** A missing tool or an unreachable host fails the gate; nothing passes silently.
- **The commands.**
  - Engine: `scripts/check.sh fast` (commit), `NEOTELETEXT_REMOTE=foundintelquiet4060 scripts/check.sh full` (full; `cargo xtask features` and the remote stages included).
  - Browser: `scripts/check.sh commit`, `scripts/check.sh full` (`NEOTELETEXT_LINUX_HOST` names the Linux host, `foundintelquiet4060` by default).
- **Pushing.** The browser's `pre-push` runs the full gate on the commits being pushed. The engine pushes its work branch `implementation` after the commit gate, and runs the full gate before `main` moves (the owner's decision of 11 October 2026, the engine's log row 4: about 40 minutes then, about an hour now), so its `pre-push` runs the commit gate except on a push to `main`.
- **Measured costs.** The engine's commit gate takes over ten minutes on this computer; its full gate about an hour. A cleared build cache adds a full rebuild.

## 10. Commits, branches and pushing

### 10.1 Commits

- **Commit when asked**, or when the request clearly includes it.
- **One concept per commit.** A fix, a refactor and a document change are separate commits.
- **The subject** is an imperative sentence, sentence case, no full stop, naming the decision where there is one: "Stop drawing the Level 3.5 font styles; underline stays (E.96)".
- **The body** says why, then what changed, with measured numbers, the decision and requirement numbers, regenerated golden files and their raised format versions, and that the new test fails on the old code. It ends with the issue: `Refs #123` or `Closes #123`.
- **Never credit an AI** in a commit, a pull request, a comment or a document: no `Co-Authored-By` trailer, no "Generated with" line, no session link. Write as the human author.
- **Never commit secrets** (they live in `~/devel/credentials/*.env`), `.env` files, captures or scratch files.

### 10.2 Branches and pushing

- **The browser** works on `main`; its `pre-push` full gate guards what reaches GitHub.
- **The engine** works on `implementation` and merges to `main` after the full gate; feature branches (for example `audio`) merge into `implementation` once their work is committed. A backup branch is made before a destructive change (`backup-before-drcs-removal`).
- **Push when the owner says.**
- **Moving a branch:** `git branch <new> <sha>`, and `git reset --soft` if needed; never `reset --hard`, `clean -fd`, `checkout -- <path>` or `filter-repo` on a dirty tree. Run `git status` first and stash everything, including files that seem not to be yours.
- **Another session may be working in the same repository.** If HEAD or files change unexpectedly, stop and report; don't fight it.
- **A `--force` flag means a safety check refused.** Read why first.

## 11. The two repositories together

- **Where code belongs.** The engine is the teletext engine only (its decision E.76): no browser code there. All teletext recognition, decoding, rendering and web-protocol reading is the engine's; the browser does not implement a second one (browser requirement 2.1). A limit or policy the browser needs is added to the engine, not to the browser.
- **The pin.** The browser depends on every engine crate at one commit, through a `git` source on the engine's repository (`file:///Users/andrewstuart/devel/neoteletext-engine` while the commit is unpublished, then the GitHub address at the same commit), never a copy and never a local patch (browser requirement 2.5, decision 36). Every `neoteletext-*` dependency names the same `rev`.
- **Moving the pin** is a commit of its own in the browser:
  1. Change the `rev` in `native/Cargo.toml` and in `native/fuzz/Cargo.toml`.
  2. Re-resolve both workspaces without upgrading anything else (`cargo metadata --format-version 1`, and with `--manifest-path native/fuzz/Cargo.toml`), and check that both lockfiles' diffs touch only the engine's entries.
  3. Lint and test the whole workspace, then commit, naming what the new engine commit changes for the browser.
  4. Update `docs/architecture.md` section 5's pinned commit.
- **A change the engine needs** is made in the engine, by its process, and recorded in its decisions; the browser then moves its pin. A decision affecting both is recorded in both, each citing the other's number.
- **Moving or renaming a repository's directory:** update every `file://` source, `deny.toml`'s allowed git sources, the documents and the Claude memory folder (`~/.claude/projects/<path with dashes>`); repair worktrees (`git worktree repair`); then clear the build cache (`cargo clean`), since tests carry the old absolute paths compiled in (`CARGO_BIN_EXE_*`, `CARGO_TARGET_TMPDIR`) and Cargo does not rebuild them.
- **Toolchains agree.** Both pin the same Rust release in `rust-toolchain.toml`, so both are checked by the same compiler and Clippy.

## 12. Hosts and platforms

| Host | Use |
|---|---|
| This Mac (macOS, Apple silicon) | Development, both gates; the engine's `x86_64-apple-darwin` tests run under Rosetta. Never install qemu here. |
| `foundintelquiet4060` (Linux, x86_64) | Both full gates' Linux stage: the engine's tests, every target (`scripts/build-targets.sh`, qemu-user tests), size and symbols, coverage and fuzzing; the browser's Linux build and tests. Its disk `/mnt/usb` holds the Linux builds and the Windows virtual machine. |
| Windows 11 virtual machine on `foundintelquiet4060` | The browser's Windows build and tests, run by hand (no gate yet). See section 12.1. |
| `oldvga` (Linux) | The owner's Linux test box, on which anything may be done; qemu system emulation runs there. |

### 12.1 Running the browser on Windows

The virtual machine builds offline from a copy in its shared folder:
1. Export the commit: `git archive HEAD | tar -x -C <scratch>`.
2. Vendor its crates: in `<scratch>/native`, `cargo vendor --locked ../vendor`, and write `native/.cargo/config.toml` replacing crates.io and the engine's `git+file` source (with its `rev`) by `../vendor`. Check it resolves with `cargo metadata --offline --locked`.
3. Copy it: `rsync -a --delete --checksum <scratch>/ foundintelquiet4060:/mnt/usb/windows/shared/neoteletext-browser/`. With `--checksum`: `cargo vendor` stamps every file with one date, so a re-vendored crate of the same size looks unchanged to rsync's size-and-time check, and to `robocopy`'s in the virtual machine, whose `C:\build\neoteletext-browser\vendor` is removed before the copy (`confine-build.ps1` on the share does both).
4. Build and test: on `foundintelquiet4060`, `ssh -i ~/.ssh/winvm_ed25519 -p 2222 Docker@127.0.0.1 "powershell -NoProfile -ExecutionPolicy Bypass -File \\host.lan\Data\build-windows.ps1"`. The shared folder holds `build-windows.ps1` (build and release tests), `test-windows.ps1` (with optional areas compiled in and out) and `latency-windows.ps1`.
5. Record the result in the requirement's State line, with the date.
6. Anything with a window or sound runs in the logged-in desktop session, not the `ssh` session (session 0, which has no window station: a confined interface dies there at `CoInitialize`). `desktop-run.ps1` on the share runs a script there through a one-off interactive scheduled task (`schtasks /create /it /rl limited /sc once`, then `/run`) and prints its output; `confine-windows.ps1` runs the confined browser that way with its standard error captured.

### 12.2 Targets

The engine's targets are its REQ-GEN-015: Arm Cortex-M0 to M33 and Arm Linux; RISC-V bare metal and Linux; Xtensa (ESP32, ESP32-S3; Espressif's toolchain through `espup`, version 1.93, since 1.94 and 1.95 fail release builds); x86_64 Linux, Windows and macOS; WebAssembly. The browser's are macOS, Windows and Linux (its requirement 15.1); its interface core is `no_std`, for the microcontroller build of requirement 15.3, not yet made.

## 13. Toolchain and tools

- **Pinned.** `rust-toolchain.toml` pins the compiler release, components and targets in both repositories; the minimum supported Rust version is at most three stable releases old.
- **Tools are installed per repository, at exact versions,** into the ignored `tools/` folder by `scripts/tools.sh`, and the check script refuses other versions; the nightly compiler used for fuzzing is pinned by date. Nothing is installed for the whole machine.
- **Don't install reflexively.** Check what the machine already has; a "not found" is often a broken path, not a missing tool. Python tools run with `uvx`, never a permanent install.

## 14. Security process

- **Every input is untrusted** and every reader of one is bounded and fuzzed.
- **No executable content**, ever, unless the engine's REQ-SEC-004 is first changed by an explicit, recorded owner decision; no script engine, web engine or interpreter in the browser (its requirement 1.3).
- **A feature that adds an input or output** gets a security analysis before adoption (section 2.3); the engine's `THREAT-MODEL.md` and the browser's `docs/security-analysis.md` are updated, and the review is recorded with its date.
- **A security review** closes each engine milestone and is recorded (REQ-SEC-023); every security fault gets a regression test that fails on the faulty code.
- **Reporting.** The engine's `SECURITY.md` is the procedure for a reported vulnerability, for both repositories: acknowledge within seven days, reproduce with a failing test, release the fix and the test together, credit the reporter, update the threat model.
- **Release gate:** every security requirement passing, no open advisories, fuzzing clean for a stated time.

## 15. Safety, backups and secrets

- **Before anything destructive, name the way back.** If there is none, make one first: `cp -a <path> <path>.bak-$(date +%Y-%m-%d-%H%M%S)`, or a backup branch.
- **Production:** confirm the deploy took a backup, or record the version to roll back to, before deploying.
- **Servers you don't own are read-only** unless the owner has authorised them (`foundintelquiet4060` and its Windows virtual machine are). Beware commands that install things as a side effect.
- **Secrets** live in `~/devel/credentials/*.env`. Never print, echo or commit them.
- **Scratch files** go in the session's scratchpad or the repository's ignored `tmp/`, never `/tmp`.
- **Don't take the owner's desktop**: no stolen focus, no windows brought forward; a browser driven for tests uses its own debugging port and profile and is launched in the background.

## 16. Documents each repository keeps

| Document | Engine | Browser |
|---|---|---|
| Repository guidance, pointing here | `CLAUDE.md` | `CLAUDE.md` |
| Requirements | `docs/spec/requirements/` | `docs/requirements.md` |
| Decisions | `docs/spec/decisions.md` | `docs/architecture.md` section 2 |
| Where code lives | `ARCHITECTURE.md` | `docs/architecture.md` |
| Design and explanation | `docs/spec/design/` | feature documents in `docs/` |
| Traceability or state | `docs/traceability.md` (generated) | State lines in `docs/requirements.md` |
| Owed work | `TECH-DEBT.md` | `TECH-DEBT.md` (to be made, appendix B) |
| Questions met without the owner | `IMPLEMENTATION-LOG.md` | `IMPLEMENTATION-LOG.md` (to be made, appendix B) |
| Security | `SECURITY.md`, `THREAT-MODEL.md`, area SEC | `docs/security-analysis.md`, per-feature analyses |
| Licences and credits | `LICENSING.md`, `CREDITS.md` | `docs/licensing.md`, `CREDITS.md` |
| User guide | `docs/user-guide.md` | (none yet) |

Every public function, type and constant is documented (REQ-DOC-001; `missing_docs`).

---

## Appendix A. Choices made in merging

Where the sources disagreed, this document chose as follows. Each is open to the owner's change.

| # | Disagreement | Chosen | Why |
|---|---|---|---|
| 1 | Global rule: `pre-push` runs the full gate. Browser: it does. Engine: `pre-push` runs the fast gate, by the owner's decision of 11 October 2026 (log row 4). | The full gate runs before anything reaches `main` on GitHub. The browser, which works on `main`, runs it on every push; the engine runs it on a push to `main`, and the commit gate on pushes of `implementation`. | Keeps the owner's later, specific decision for the engine, and the global rule's purpose: nothing reaches `main` unchecked. |
| 2 | Engine's fast gate checks the whole tree; browser's commit gate checks what is staged and refuses unstaged changes. | The browser's. | Otherwise what passed is not what was committed. |
| 3 | Engine reports missing tools as SKIPPED, and its remote stages are left out silently when `NEOTELETEXT_REMOTE` is unset; browser fails. | Nothing is skipped. | A gate that can pass without running is not a gate (the engine's own log row 18 says "never silently passed"). |
| 4 | Engine records tool versions in prose and uses an unpinned nightly; browser installs exact versions into `tools/` and refuses others. | The browser's. | The global rule: pin tools. |
| 5 | Linux host: the global rules and engine documents say `oldvga`; the scripts and the engine's `TECH-DEBT.md` say `foundintelquiet4060`. | `foundintelquiet4060` for the gates; `oldvga` remains the owner's test box. | It is what the gates use, and `oldvga` was unreachable on 21 October 2026. |
| 6 | Decisions: E.n in text (engine) against Decision n in a table (browser). | Both kept; one set of forms for changes (section 5.1). | Renumbering would break every citation, in both repositories. |
| 7 | Requirements: `REQ-AREA-NNN` with traceability (engine) against numbered sections with State lines (browser). | Both kept; one set of forms for amendments and withdrawals (section 4.1); "Withdrawn:" titles everywhere. | The same reason; the forms are what differed without need. The engine's tool recognises only "Withdrawn" titles. |
| 8 | Issues: required in the engine, unused in the browser. Engine rule says `Closes #n`; its commits say `Refs #n`. | Issues in both; `Refs` for progress, `Closes` on completion. | Work found should not live only in replies; both forms were in use. |
| 9 | Deferred work: `TECH-DEBT.md` and the implementation log in the engine only. | Both repositories keep both. | The same rule: nothing deferred exists only in a reply. |
| 10 | CI: the global rules say none; the engine's requirements still say "continuous integration". | No CI; the engine's requirements are to be reworded to "the full gate". | The owner's instruction, which log row 4 already said overrides the wording. |
| 11 | Library approval: global and browser ask for every library; the engine's REQ-GEN-017 only for microcontroller crates. | Every library, by name. | The global rule, and the engine's own E.93 libraries were approved that way. |
| 12 | Exact version pins in the browser, ordinary requirements in the engine. | Exact in applications, ordinary in libraries, lockfiles everywhere. | Exact pins in a library would stop programs that use it from resolving. |
| 13 | Lints: the browser warns on allows without reasons, `dbg_macro`, `todo` and `unimplemented`; the engine does not. | Both do. | The global rule: a suppression carries its reason. |
| 14 | The engine says OS access is enforced by Clippy's disallowed lists; it is enforced by `cargo xtask check-io`. | `check-io`. | It is what runs. |
| 15 | Formatting width: engine 120, browser 160. | Each keeps its own. | Changing either reformats every file for no gain; it is not process. |
| 16 | Credits: the browser's entries name the problem solved; the engine's are an inventory. | Both: the inventory, and for each borrowed solution the problem it solved. | The global rule asks for the latter; the inventory serves licensing. |
| 17 | The engine's reference check writes `/tmp/refs` and `/tmp/defs`. | The scratchpad or `tmp/`. | The global rule. |
| 18 | Timings in the engine: "over ten minutes" (`CLAUDE.md`), "a minute or two" (`pre-push`), "about 40 minutes" (`README.md`). | Measured on 21 October 2026: the commit gate over ten minutes, the full gate about an hour. | Measure, don't reason. |

## Appendix B. Adopting this process

Not yet done in the repositories; each is a change of its own.

**Engine**
1. `scripts/check.sh`: refuse unstaged changes in what the commit gate checks; fail instead of SKIPPED; fail when `NEOTELETEXT_REMOTE` is unset in the full gate; check lockfiles with `--locked`; check that the gate changed nothing committed.
2. `.githooks/pre-push`: run the full gate on a push to `main`.
3. `scripts/tools.sh`: install cargo-deny, cargo-machete, cargo-fuzz, cargo-llvm-cov and the dated nightly at exact versions, as the browser's does.
4. Workspace lints: add `allow_attributes_without_reason`, `dbg_macro`, `todo` and `unimplemented`; give every crate root that reads outside input the core's no-panic list, checked identical by `scripts/check.sh`; pin the application crates' own dependencies exactly.
5. Requirements: reword "continuous integration" to "the full gate"; give withdrawn requirements "Withdrawn:" titles where they lack one (area TST, SEC); REQ-GEN-017 to require the owner's approval for every library; correct "clippy's disallowed lists" to `check-io`.
6. `CLAUDE.md`: keep what is particular to the engine and point here; close `TECH-DEBT.md`'s item asking for one development-process document.
7. Rename `oldvga` to `foundintelquiet4060` where the documents mean the build host.

**Browser**
1. `CLAUDE.md`, pointing here.
2. `TECH-DEBT.md` and `IMPLEMENTATION-LOG.md`.
3. GitHub issues on `crowdwave/neoteletext-browser`, and the engine's browser issues (#215, #216, and parts of #177 and #210) moved there.
4. `scripts/check.sh`: check that every `neoteletext-*` dependency names the same `rev` (requirement 2.5 asks for it; only the repository is checked today).
5. Requirement forms: one amendment form (section 4.1); "Withdrawn:" titles.
6. A Windows step in the full gate, or a recorded decision that Windows stays a by-hand check.
