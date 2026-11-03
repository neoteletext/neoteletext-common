# How NeoTeletext is developed

**The one document of how we work**, for every NeoTeletext repository (the owner's instruction of 3 November 2026: "we need a SINGLE document that unifies how we work, and rdm is the baseline"). **rdm is the baseline:** every requirement, decision, checklist, term, source, documentation item and piece of work owed is an rdm record, and nothing else tracks work (section 3). Each repository's `CLAUDE.md` imports this document and adds only what is particular to that repository.

The repositories, each in `~/devel/`:
- **`neoteletext-engine`**: the teletext engine, its libraries and the `neottx` program;
- **`neoteletext-browser`**: NeoTeletext, the browser, built on the engine at a pinned commit;
- **`neoteletext-app-server`**: the NeoTeletext server;
- **`neoteletext-server-ts-protocol`** and **`neoteletext-server-ts-ui-components`**: the TypeScript protocol kit and component library channels are written with;
- **`neoteletext-server-channels`**, **`neoteletext-server-channel-demosite`**, **`neoteletext-server-channel-hackaday`**, **`neoteletext-server-channel-home-www.neoteletext.com`** and **`neoteletext-server-channel-uicomponentsdemo`**: the channels;
- **`neoteletext-common`**: this document, the gate machinery every repository shares (section 9), the protocol document generated from rdm, and the guides.

It replaces the two shorter documents on the gates and on working with rdm, folded in here on 3 November 2026 (sections 3 and 9). This document was first written on 21 October 2026 by merging the owner's global instructions (`~/.claude/CLAUDE.md`), the engine's `CLAUDE.md`, `README.md`, `IMPLEMENTATION-LOG.md`, `TECH-DEBT.md`, `LICENSING.md`, `docs/spec/` and gate scripts, and the browser's `docs/requirements.md`, `docs/architecture.md`, `docs/licensing.md` and gate scripts. Where they disagreed, the rule chosen and its reason are in appendix A; appendix B lists what each repository still has to change to follow this document.

---

## 1. Authority

1. **The owner's global instructions** (`~/.claude/CLAUDE.md`) apply to every repository. This document adds to them; it departs from them only where it says so, with the owner's decision cited.
2. **This document** is the development process, and the only one: no other file describes how we work. A repository's `CLAUDE.md` imports it (`@~/devel/neoteletext-common/DEVELOPMENT.md`) and says only what is particular to that repository; where a repository's own text and this document disagree, this document holds until the repository's text is corrected.
3. **The standard, datasheet or specification is the source of truth** for behaviour. Read it before writing code against it and cite the clause in comments (`// EN 300 706 clause 9.3.1: ...`). A datasheet wins over a web snippet. Read PDFs with page ranges, not through a text extractor that mangles tables. Standards and datasheets live in `~/devel/teletext-reference/`, never in either repository.
4. **rdm is the baseline.** Each repository's requirements are its only normative text, and they are kept in rdm (since 30 October 2026, rdm decision DEC-1389), with the decisions, the checklists, the terms, the sources, the protocol's documentation items and the work owed. rdm is reached through its MCP tools; no repository keeps a file of requirements, decisions, design or to-dos, and a hook refuses edits to the files that used to. Decisions record choices, their reasons and their evidence; neither a decision nor a document overrides a requirement. Every record is fully detailed (section 3.5), and every interaction with rdm puts the relevant links in place (section 3.6).
5. **Security overrides every other requirement** in every repository (the engine's area SEC and decision E.32; the browser's decision 4 and requirement 1.2). A conflict is recorded as a decision and the other requirement is amended. No option may switch security off.
6. **Each fact has one home.** Link rather than restate. Process lives here; behaviour lives in the requirements; choices, their reasons and their evidence in the decisions; the protocol in its documentation items (DEC-2022); where code lives in the engine's `ARCHITECTURE.md` and the browser's `docs/architecture.md`. A design that grows in a document while it is being shaped is carried into rdm and the document deleted, as the engine's language design was on 3 November 2026.

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

The owner shapes behaviour by asking for changes and looking at the result (the owner's instruction of 13 October 2026). Work runs in two modes, in every repository.

**Rapid iteration** is the default while behaviour is being shaped.
- Make the change, rebuild with the fast profile and show the result: in the engine `cargo build --profile iterate -p neoteletext-cli`, then `target/iterate/neottx`; in the browser `scripts/try.sh` (Clippy on every save) or `scripts/try.sh <crate> [filter]`, and the program itself. Check the output, then tell the owner it is ready to look at.
- Do not write tests, user-guide text, requirement prose or log rows yet. Run the existing tests of the code touched when that is quick.
- Commit whenever a step compiles: the commit gate checks only that (section 9.1). Never bypass a hook.
- **Everything owed is an rdm to-do** as it arises (`create_record`, type `todo`, linked to the requirement or decision it concerns): tests, requirements and decisions to record, documents to update, verification to run, shortcuts taken, loose ends. Nothing deferred may exist only in a reply.

**Integration** starts when the owner says the feature works as they expect. Work through its open to-dos, in this order:
1. record the decision and the requirements in rdm (sections 4 and 5);
2. write the tests, each failing on the old code and naming the requirement it verifies (section 8);
3. update the user guide, the architecture document and the other documents;
4. add the implementation log row, if the work met a question without the owner (section 3.3);
5. set each requirement's implementation status in rdm, on the commit that meets it;
6. commit through the gates in small commits that name the rdm records they serve (section 10), and mark each to-do done in rdm, naming the commit, as it is done.

Behaviour may be tried before it is recorded, but none is committed without its decision and requirements.

### 2.3 A feature's life

A feature large enough to need design goes through these steps; the engine and the browser have done so (the browser's hyperlinks and interaction work, the engine's areas AUD and INT).
1. **A proposal** (in rdm, as a decision waiting for the owner, or a document while it is shaped) and, for anything that reads outside input or adds an input or output, **its own security analysis**, whose findings are applied to the proposal.
2. **An adoption decision** by the owner, which adds the requirements.
3. **The build.**
4. **"What building changed"**: a section of the proposal listing every departure from it, and a decision recording the build that names the departures for the owner to confirm.
5. **A confirming decision**, recorded in every repository whose decisions the departures touched.

### 2.4 Decisions while the owner is away

When the owner asks for work to continue without questions, decisions are taken and recorded in rdm as usual, created with `needs_confirmation`, which lists them for the owner's review; only the owner's own words confirm one. An implementation log row records each question met.

## 3. Tracking work: rdm

### 3.1 rdm is the one record of work

Work is tracked in rdm and nowhere else (the owner, 3 November 2026: "rdm is the baseline"). GitHub issues are not used: no new issue is opened, and a commit does not reference one.
- **Work starts from a record.** Before substantive work, `search` rdm for the requirements and decisions that apply, and follow them. Work that has no record gets a to-do first.
- **Log what you find.** A bug, a gap, a loose end or a decision for the owner becomes an rdm record (a to-do, or a decision with `needs_confirmation`), never just a mention in a reply.
- **What waits on the owner** is listed by rdm: decisions with `needs_confirmation`, and to-dos created with `for_user` (`waiting_on_user`, and the summary at the start of each session). A task only the owner can do says so in its title.
- **Commits name their records** (`REQ-n`, `DEC-n`, `TODO-n`) in the subject or body, and rdm links each commit to the records it names (section 10.1).
- **Work that concerns another repository** is recorded in that repository, with a link from the record that found it.
- **Keep the record true.** A to-do is marked done with the commit that did it, or cancelled with the reason, never deleted; rdm lists to-dos whose requirement was implemented since, to be checked and closed.

### 3.2 Work owed

Each item is an rdm to-do. A to-do names the decision and requirements it serves; says what exists today and where (files, functions, behaviour); explains each step to be done in sentences, with the file or component it changes and why; gives the order and what it depends on or blocks; says how the work will be checked; and says what "done" means. Nothing deferred may exist only in a reply.

### 3.3 The implementation log

`IMPLEMENTATION-LOG.md` records the questions met while implementing without the owner and the answer taken, as rows: number, question, decision, reason. A row is amended in place ("*Amended 11 October 2026:*") or superseded by a later row that says so. Behaviour the standard leaves open is a decision (section 5), not a log row. A round of unattended work ends with a status section: what was done and how it was verified, a NOT DONE table with reasons, and what is for the owner to review.

### 3.4 Reporting

Lead with the result. Report a failure as a failure, with its output; never claim a check passed that was not run. Name uncertainty as a fact about the evidence ("untested on hardware").

### 3.5 Every record is fully detailed

The owner, 30 October 2026: "ensure todos and REQUIREMENTS are DETAILED NEVER ABBREVIATED NEVER TOO CONCISE, must FULLY EXPLAIN WHAT NEEDS TO BE DONE". A record is read later by someone, or by a session, that never saw the conversation it came from, so it must stand alone:
- **Full narrative sentences**, every term spelled out the first time it is used. No terse fragments, no abbreviations, no "as above", no "see the chat", and no pointer to a file for what the record itself should say.
- **A requirement** states the behaviour in full (what must happen, in which part, under which conditions, with every bound named and its source cited), why it is required (the owner's words where they are the reason), where it comes from (the decision that made it), how it will be verified, and its state (section 4).
- **A to-do** is as section 3.2 says.
- **A decision** says who decided and when, what was chosen in numbered items, why, the alternatives considered, what it withdraws or changes, and when to reconsider (section 5).
- **A revision** is a complete new version, never a patch that only makes sense beside the old one, with its reason.
- **A record that comes from the owner's words** quotes them (`origin_quote`).

### 3.6 rdm is a graph: every change is followed by its links

The owner, 30 October 2026: "always treat every interaction with RDM as a GRAPH database, be careful to put in place RELEVANT LINKS with EVERY interaction", and "AFTER CLAUDE HAS MADE ONE CHANGE OR A GROUP OF CHANGES, IT MUST - THIS IS REQUIRED - THEN DO A SECOND PHASE WHICH IS TO ESTABLISH LINKS OF THE CHANGED AND NEW INFORMATION … WE DO NOT EVER WANT LINKS THAT DO NOT ADD MEANINGFUL RELATIONSHIPS".
1. **The change:** create, revise or change the status of the records.
2. **The linking phase, always:** for every record just created or changed, establish its links, then report them. Making no link is the right choice when none would add meaning; say so rather than add a link for its own sake.

In the linking phase:
- **Search first** for the records the new one concerns, in its repository and in every other (`search` with `repository: "all"`), and link them.
- **The right kind of link:** `decides` from a decision to each requirement it makes or amends; `depends_on` from a record to what must exist or be done first, and from a requirement to the source it rests on (with the clause, table and page in the link's reason); `supersedes` from a new record to the one it replaces, whose status is set to superseded; `documents` from a documentation item to the requirement it states; `related` for everything else a reader of one should know about the other.
- **Every to-do links** to the decision and requirements it implements, and to the to-dos that must come before it. **Every requirement** is linked from the decision that made it and to what it builds on. **Every decision** links to the decisions it amends, supersedes or relies on, and decides its requirements.
- **A revision checks its links:** what the new version cites is linked, and links the change makes wrong are removed or replaced. Records a revision marks as needing a recheck are reviewed: revised to match, or reported as still holding.
- **Across repositories:** a record that concerns another repository's record is linked to it.
- **Tags:** a record created or revised is given the tags of its subjects, and a revision checks they still fit (section 3.8).

A `PostToolUse` hook in `~/.claude/settings.json` (`~/.claude/hooks/rdm-link-reminder.sh`) reminds the session of the linking phase after every rdm write.

### 3.7 Sources and the protocol's documentation items

- **A standard or other document that records rest on** is an rdm source (`create_record` type `source`): its publisher's address, its SHA-256, size and pages, pinned so the exact file can be fetched and checked. rdm holds its facts, clause numbers and positions only; the file itself stays in `~/devel/teletext-reference/`, never in a repository.
- **The protocol is defined only by rdm's documentation items** (DEC-2022), from which `PROTOCOL.html` is generated (`README.md`); guides teach and point to the items. `DOC-n` anywhere names the item at `PROTOCOL.html#DOC-n`.

### 3.8 Tags

The owner, 3 November 2026: "I also now want RDM entries to have tags wherever it makes sense" (DEC-2168). A tag is a short subject label, written like a hashtag, that gathers every record about one subject across repositories and record types. It complements the rest of a record: its type, lifecycle and repository are fields, and its relationships to other records are links.
- **One set of tags for the whole project.** In rdm a project, or topic, is all the repositories in one access scope; NeoTeletext's is every repository rdm lists for it, from the engine to the channels. A tag belongs to the project and is unique within it, so `#charactersets` is one tag whether it marks an engine requirement, a browser decision or a kit's to-do. Tags are a table and a relation in rdm, separated by project under the same Postgres row-level security as records, so NeoTeletext's tags are never seen from another project. Building them is rdm's own work, in rdm's project; a NeoTeletext session uses them and does not change rdm.
- **Simple hashtags, made freely, kept high level.** A tag is a lower-case hashtag of 1 to 50 letters, digits and hyphens, such as `#charactersets` or `#fonts` (rdm drops a leading `#` and lowers capitals); it has no description and no definition step, and a session may create one whenever a record needs it (the owner's answers of 3 November 2026, to rdm's maintainers). The owner wants tags high level: broad subjects, not fine detail. A tag names a subject: never a status, a type, a repository or a date, which rdm already holds.
- **Query before tagging.** `find_tags` returns the identical and similar tags with their record counts; ask it first, and use an existing tag where one fits, so that one subject keeps one tag. `tag_record` adds, removes or replaces a record's tags and names similar tags when it creates one; `edit_tag` creates, renames or deletes one. Broad subjects that recur include `#languages` and `#charactersets` for every record on languages and character sets (with a language or script tag such as `#thai`, `#lao`, `#arabic` or `#vietnamese` where a record deals with that one specifically, and `#noto` for the font pipeline), `#fonts`, `#protocol`, `#security`, `#gates`, `#development-process` and `#documentation`.
- **Where they go.** On records only, never commits. A record carries a few tags, its broad subjects (rdm allows up to 30). Every requirement, decision and to-do is tagged; terms, sources and documentation items where a reader would look for them by subject. Tagging is part of the linking phase (section 3.6). A tag change is logged by rdm but makes no new version of the record.
- **The engine's area codes become tags:** a record whose title starts with one (`[CHR]`, `[FNT]`, `[SEC]` …) is given that area's tag, and new titles stop carrying the code.
- **rdm has tags since 3 November 2026** (rdm commit `382ca43`): `get_record` shows a record's tags, and `list_records` and `search` filter by one. TODO-2169 tags the existing records. Nothing imitates tags in titles or bodies.

## 4. Requirements

Requirements are rdm records (section 3). Each repository's numbering stays valid, since numbers are cited everywhere: the engine's `REQ-<AREA>-<NNN>`, the browser's and the server's "Requirement <section>.<n>" resolve in rdm as the records' original IDs. A new requirement takes rdm's ID (`REQ-n`); in the engine its title starts with its area code (`[INP] …`), in the browser and the server with its section.

- **Numbers are permanent.** They are never reused; a requirement is never deleted.
- **Modal verbs.** "Shall" or "must" is mandatory; "should" is expected unless a recorded reason says otherwise; "may" is an option.
- **Every requirement is written in full** (section 3.5) and **has a reason and a verification.** Verification is a test (automated), a check (automated, in the check script), an inspection or a review (recorded by a person), or a demonstration.
- **Source and state.** A requirement links to the decision that made it (`decides`). Whether it is met is rdm's implementation status, per branch, set on the commit that meets it; tests that name the requirement are linked to it, with their results (the engine's REQ-DOC-003).
- **Phases.** In the engine a Phase 2 requirement says so in its body and is listed in decision F.0.1; Phase 1 must not depend on Phase 2, and a Phase 2 feature's tests come with it.
- **Writing.** Full narrative sentences; terms spelled out (the engine's glossary is `docs/spec/glossary.md`, the browser's `docs/architecture.md` section 17); the standard cited by clause or table.
- **References resolve.** Every requirement identifier cited anywhere must name one that exists in rdm.
- **The engine's state machine tables are normative** (area FSM): if a table and prose disagree, revise both.

### 4.1 Changing a requirement

- **Amended:** `revise_record` writes the complete new version, with the reason (naming the decision whenever there is one); rdm keeps every earlier version.
- **Withdrawn:** `set_status` lifecycle `cancelled`, with the date's reason; or `superseded`, naming the requirement that replaces it.
- **Moved:** a requirement that moves to another repository is created there and the old one superseded by it.

## 5. Decisions

Decisions are rdm records (section 3). Each repository's series stays valid as original IDs, since both are cited across the code and the documents: the engine's **E.n**, the browser's and the server's **Decision n**. A decision of one repository cited in another names its repository: "the engine's decision E.95", "NeoTeletext's decision 46". A new decision takes rdm's ID (`DEC-n`). Feature documents may number their own decisions ("`hyperlinks.md` decision 7"); implementation log rows are "rows", not decisions.

- **Record before committing behaviour.** Behaviour the standard or the design leaves open is recorded in rdm, or the decision revised, before the change is committed (the engine's REQ-DOC-004). During iteration it is an rdm to-do, decided at integration.
- **A decision says who decided and when**, what was chosen, in numbered items where there are several, its reason, the alternatives considered, what it withdraws or changes, and when to reconsider (section 3.5). rdm records who made each version and the conversation it came from.
- **A decision taken without the owner needs the owner's confirmation:** it is created with `needs_confirmation`, and only the owner's words confirm it (`set_status` confirmation `confirmed`, quoting them).
- **A dependency of a microcontroller crate** of the engine needs a decision (section 7).
- **Decisions keep their history.** They are never deleted or renumbered.

### 5.1 Changing a decision

| Change | In rdm |
|---|---|
| Amended | `revise_record`: a complete new version, with the reason |
| Superseded | `set_status` lifecycle `superseded`, naming the decision that replaces it |
| Withdrawn | `set_status` lifecycle `cancelled`, with the reason |
| Moved to another repository | created there; the old one superseded by it |
| Confirmed by the owner | `set_status` confirmation `confirmed`, quoting the owner's words |
| Still unconfirmed | confirmation `needs_confirmation` |

## 6. Code

- **Strictest settings, warnings as errors.** Never silence a whole category. A suppression is narrow, at its site, with its reason written (`#[allow(..., reason = "...")]`); the gates make warnings errors. When strictness breaks the build, the warnings are the work.
- **Lints, in both workspaces** (the engine is to add the last four, appendix B): `unsafe_code = "forbid"`; `missing_docs`; `unused_qualifications`; Clippy `pedantic`, with each workspace-wide exception listed and justified in `Cargo.toml`; `allow_attributes_without_reason`, `dbg_macro`, `todo` and `unimplemented`.
- **No panics where input comes from outside.** Every crate root that reads input from outside its process denies `indexing_slicing`, `string_slice`, `unwrap_used`, `expect_used`, `panic`, `arithmetic_side_effects`, `unreachable`, `todo` and `unimplemented`, with one list kept identical across those roots by each repository's check script. Tests may use them.
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
- **The engine's microcontroller crates** take a dependency only by a decision in rdm, and only one that builds `no_std` without allocation for `thumbv6m`, `riscv32imc` and Xtensa, uses no compare-and-swap or floating point, has no build script or native code, has its flash cost measured and passes the symbol check (REQ-GEN-017). `cargo xtask check-deps` compares each crate's dependencies with its permitted list.
- **Licences.** The projects are MIT, and nothing linked may change that: MIT, Apache-2.0 (with or without the LLVM exception), BSD-2-Clause, BSD-3-Clause, Zlib, ISC and CC0 are accepted; OFL for fonts; LGPL only as a system library linked dynamically and not shipped. Never GPL or AGPL; MPL or EPL only by the owner's decision. An exception in `deny.toml` names one crate and one licence, with its reason. The engine's `LICENSING.md` is the full rule; the browser's `docs/licensing.md` applies it.
- **No GPL code**, ever: vbit2 and QTeletextMaker may run as separate programs or test oracles only; never copy their code or test files.
- **Versions.** `Cargo.lock` is committed in every workspace, including fuzzing's, and its changes are reviewed. Application crates (the browser's, and the engine's `neoteletext-app`, `neoteletext-cli` and `neoteletext-qrkeyboard`) pin their own dependencies' exact versions (`=x.y.z`), each with a comment giving its licence and reason. The engine's library crates use ordinary version requirements, so that a program depending on them can resolve; their lockfile is the pin for the engine's own builds.
- **When a lockfile must change, change only what has to.** `cargo update` without arguments upgrades every dependency; to move one source, let Cargo re-resolve (`cargo metadata`) or name the package (`cargo update -p <name>`), then check that the lockfile's diff touches nothing else.
- **No unused dependencies** (`cargo machete`). Advisories are checked by `cargo deny`; an advisory is ignored only with its reason and the owner's decision.
- **Credits.** A solution taken from another project is credited in `CREDITS.md`, naming the project, licence, version and the problem it solved; outside reference projects are not named in source code. Bundled third-party material keeps its licence and provenance beside it.
- **No copyrighted standards, datasheets, broadcast recordings or captures** in either repository. The engine's corpus is downloaded at test time and pinned by checksum, local files read from `$NEOTELETEXT_CORPUS`; the browser's sites built from recordings stay in ignored folders.
- **Fonts.** The engine compiles in one font, Noto Teletext, converted from Noto; a user may load another at run time; no other font or ROM glyph is added (the engine's DEC-1761).

## 8. Tests

- **A regression test fails on the old code.** Confirm it by running it there, and say so in the commit message. A fault is fixed in its own commit, with its test.
- **Assertions say exactly what they claim**: check the expected set, not a count.
- **Golden files carry a format version.** A change to pixels raises it and regenerates the golden files in the same commit, with the reason; check that only the expected pages changed.
- **Timed tests hold a budget** and print their numbers (the browser's latency test; the engine's typing test, REQ-INT-008). A timed test builds the programs it times.
- **Fuzzing.** Every reader of outside input has a fuzz target. Every input that ever found a fault is kept as a regression and replayed first.
- **Oracles** run as separate programs (`tests/oracles/`).
- **The engine** also keeps line coverage of its core at 90 % or more, size and symbol budgets for the microcontroller builds (`cargo xtask size`), and each crate's build with no optional area and with each area alone (`cargo xtask features`, decision E.61).
- **Platform behaviour** that cannot run unattended is an ignored test run by hand, and its result is recorded with the date.
- **A test that cannot run says so** (section 9.2). What it needs and does not have, such as the corpus or a running relay, makes it an ignored test whose reason names what would make it run, never an early return that reports `ok`; asked for without it, it fails.

## 9. Gates and the work branch

There is no continuous integration; the gates are local (the owner's instruction). Every repository works this way (the owner's instruction of 29 October 2026: every process "as fast as possible", and "I need to know when I am committing to a long integration step").

### 9.1 Day to day, nothing long starts

1. Work on `livedevelopment`.
2. Build and run as often as you like: building or running a program runs no gate.
3. Commit whenever a step compiles: the commit gate checks only that.
4. Push `livedevelopment` whenever the work should be on GitHub: the push gate runs the tests, and nothing already passed on the same code.
5. Push to `main` only to integrate, when the owner says: that is the one long step. It prints its last measured time before it starts, so Ctrl-C stops it if now is not the time.

### 9.2 The tiers

`scripts/check.sh commit | push | full`; the git hooks (`git config core.hooksPath .githooks`) run them. Never bypass a hook (`--no-verify`).

| Tier | Hook | What it adds |
|---|---|---|
| `commit` | `pre-commit`, every commit | The code compiles clean: formatting, Clippy or the type check, the cheap text checks. It checks what is staged and refuses while a part it reads has unstaged or untracked changes. |
| `push` | `pre-push` of any branch but `main` | The remaining feature shapes and the tests, on a clean tree at the commit pushed. |
| `full` | `pre-push` to `main` | Everything else: release and feature-off tests, fuzzing, licences, unused dependencies, the Linux host's steps running alongside. It fails if running it changed a committed file. |

- **Each gate says its cost first:** its last pass's time and its three slowest steps, then each step's time as it ends.
- **Nothing runs twice on the same code:** a pass records what it passed on, keyed on the paths the gates read, and a higher tier skips a lower one already passed there; a change to a document alone runs no gate again.
- **Nothing is skipped silently:** a step that cannot run fails the gate and says what it lacks and how to get it, through `need_tool`, `need_host` and `need_host_tool` in `gate.sh`; a step never asks whether its tool is there and goes on without it. A tool a repository pins is installed by its `scripts/tools.sh` into its ignored `tools/`, and the full gate refuses a missing one, or another version, before anything long starts. The commit gate fails a check script that can report a step skipped.
- **A test that cannot run says so:** it is marked ignored with a reason naming what it needs, so that a run counts it as ignored and not as passed, and asked for without what it needs it fails. It never returns early and reports `ok`. A gate prints the ignored tests with their reasons, because a pass says nothing of them.
- **Measured costs.** The engine's commit gate: 3 seconds warm (29 October 2026; over ten minutes before the tiers), 9 seconds on 3 November 2026. The full gates: about an hour each before the tiers; each gate prints its own last measured time.

### 9.3 Where the gates live

- **One copy of the machinery,** in neoteletext-common's `gates/`: `gate.sh` (timing, records, tiers, the Linux host alongside) and the three hooks. Change it there, commit, and run `gates/sync`, which writes `scripts/gate.sh` and `.githooks/` into every repository `gates/repositories` names. Each repository's commit gate fails if its copy differs from neoteletext-common's at the commit the copy names.
- **No file names a deleted document.** The commit and push gates of every repository fail when a tracked file names a document that was deleted because rdm now holds it: the protocol documents DEC-2022 deleted, and the gate and rdm documents folded into this document on 3 November 2026. Such a mention cites the rdm record, the `DOC-n` item of `PROTOCOL.html`, or a section of this document instead. A file that must keep one as history, such as a dated review, is named alone in `DELETED_DOCUMENT_HISTORY` in that repository's `scripts/check.sh`.
- **neoteletext-common has a gate too:** its `scripts/check.sh` runs the original machinery and `gates/test`, with `git config core.hooksPath gates`. Run `gates/test` after any change to the machinery.
- **Each repository's own steps,** in its `scripts/check.sh`: `CHECKED_PATHS`, `commit_steps`, `push_steps`, `full_steps` and `linux_steps`, then `gate_main`.
- **The copy to the Linux host compares content** (`rsync --no-times --checksum`): with this machine's times kept, a file edited here before the host's last build looks older than that build, and Cargo reuses the stale crate.

## 10. Commits, branches and pushing

### 10.1 Commits

- **Commit when asked**, or when the request clearly includes it.
- **One concept per commit.** A fix, a refactor and a document change are separate commits.
- **The subject** is an imperative sentence, sentence case, no full stop, naming the decision where there is one: "Stop drawing the Level 3.5 font styles; underline stays (E.96)".
- **The body** says why, then what changed, with measured numbers, the rdm records it serves (`REQ-n`, `DEC-n`, `TODO-n`, or a record's original ID), regenerated golden files and their raised format versions, and that the new test fails on the old code. rdm links the commit to every record it names. It references no GitHub issue (section 3.1).
- **Never credit an AI** in a commit, a pull request, a comment or a document: no `Co-Authored-By` trailer, no "Generated with" line, no session link. Write as the human author.
- **Never commit secrets** (they live in `~/devel/credentials/*.env`), `.env` files, captures or scratch files.

### 10.2 Branches and pushing

- **Every repository works on `livedevelopment`** (the owner's name, 29 October 2026; the engine's was `implementation`), pushed through the push gate. `main` moves only by the full gate, when the owner says to merge. Feature branches merge into `livedevelopment` once their work is committed. A backup branch is made before a destructive change (`backup-before-drcs-removal`).
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
3. Copy it: `rsync -a --delete --checksum <scratch>/ foundintelquiet4060:/mnt/usb/windows/shared/neoteletext-browser/`. With `--checksum`: `cargo vendor` stamps every file with one date, so a re-vendored crate of the same size looks unchanged to rsync's size-and-time check, and to `robocopy`'s in the virtual machine, whose `C:\build\neoteletext-browser\vendor` is removed before the copy (`confine-build.ps1` on the share does both). That script also grants `ALL APPLICATION PACKAGES` read on the build's `target` folder, as an installed browser's folder grants it, because tests start confined processes from there.
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
| Repository guidance, importing this document | `CLAUDE.md` | `CLAUDE.md` |
| Requirements, decisions, checklists, owed work, sources, state and traceability | rdm | rdm |
| Where code lives | `ARCHITECTURE.md` | `docs/architecture.md` |
| Design and explanation | rdm's decisions; `docs/spec/design/` for what is not yet carried in | rdm's decisions; feature documents in `docs/` |
| Questions met without the owner | `IMPLEMENTATION-LOG.md` | `IMPLEMENTATION-LOG.md` (to be made, appendix B) |
| Security | `SECURITY.md`, `THREAT-MODEL.md`, area SEC | `docs/security-analysis.md`, per-feature analyses |
| Licences and credits | `LICENSING.md`, `CREDITS.md` | `docs/licensing.md`, `CREDITS.md` |
| User guide | `docs/user-guide.md` | (none yet) |

Every other repository keeps a `CLAUDE.md` importing this document, rdm for its records, and the `README.md`, `BUILD.md` and `DEPLOYMENT.md` its users need. Every public function, type and constant is documented (REQ-DOC-001; `missing_docs`).

---

## Appendix A. Choices made in merging

*Note of 3 November 2026:* item 8's GitHub issues are withdrawn: rdm is the one record of work (section 3.1), and appendix B's issue steps no longer apply.

*Note of 30 October 2026:* appendices A and B are the record of 21 October 2026. Where they name `TECH-DEBT.md`, requirement or decision files, or traceability, those are now rdm (section 1, rdm decision DEC-1389).

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
1. `scripts/check.sh`: refuse unstaged changes in what the commit gate checks; fail when `NEOTELETEXT_REMOTE` is unset in the full gate; check lockfiles with `--locked`; check that the gate changed nothing committed.
2. `.githooks/pre-push`: run the full gate on a push to `main`.
4. Workspace lints: add `allow_attributes_without_reason`, `dbg_macro`, `todo` and `unimplemented`; give every crate root that reads outside input the core's no-panic list, checked identical by `scripts/check.sh`; pin the application crates' own dependencies exactly.
5. Requirements: reword "continuous integration" to "the full gate"; give withdrawn requirements "Withdrawn:" titles where they lack one (area TST, SEC); REQ-GEN-017 to require the owner's approval for every library; correct "clippy's disallowed lists" to `check-io`.
6. `CLAUDE.md`: keep what is particular to the engine and point here; close `TECH-DEBT.md`'s item asking for one development-process document.
7. Rename `oldvga` to `foundintelquiet4060` where the documents mean the build host.

**Browser**
1. `CLAUDE.md`, pointing here.
2. `TECH-DEBT.md` and `IMPLEMENTATION-LOG.md`.
3. *Withdrawn 3 November 2026:* GitHub issues are not used; rdm is the one record of work (section 3.1).
4. `scripts/check.sh`: check that every `neoteletext-*` dependency names the same `rev` (requirement 2.5 asks for it; only the repository is checked today).
5. Requirement forms: one amendment form (section 4.1); "Withdrawn:" titles.
6. A Windows step in the full gate, or a recorded decision that Windows stays a by-hand check.
