# Conventions: the rules every file and every move follows

These rules are the measure the per-crate documents use. They come from the two repositories' own rules (`DEVELOPMENT.md` section 6, the engine's REQ-GEN requirements, each workspace's `Cargo.toml` lint tables and `clippy.toml`), from what the code already does where it is at its best, and from current Rust practice. Where a rule is new to the repositories it says so.

## 1. One concept per file

A file holds one concept: one type and its behaviour, one mechanism, one spec clause, one table, or one panel of the window. A reader opening it by name should find only what the name promises.

- **Size.** Aim at 150 to 400 lines; 500 is the ceiling for a file of code, and a file over it is split unless its document says why not (a table, a long `match` that is one spec clause). A test module counts separately (section 5).
- **Functions.** A function is one step of one concept. Past about 80 lines it is split, and the parts named by what they do, not `part_one`. Clippy's `too_many_lines` (100) stays as the hard limit.
- **`impl` blocks.** An `impl` block over about 300 lines means the type does several things; its methods go into concept files as `impl Type` blocks of their own (the browser's `impl Browser` in `browser/*_ui.rs` is the model), or the type is two types.
- **Tables** (character sets, colour maps, key codes, kind bytes, menus) live in files of their own, named by the table, with the code that reads them beside them, not inside them.
- **No `utils`, `helpers`, `misc`, `common` or `types` files.** A file is named by the concept it holds. (`tests/common/mod.rs` is Cargo's own convention for integration-test helpers and stays.)

## 2. Directories and modules

- **The 2018 layout**: a module `foo` with children is `foo.rs` beside a directory `foo/`, never `foo/mod.rs`. Both repositories use this already; the engine's three `mod.rs` files (`neoteletext-core/src/charset/mod.rs`, `glyphs/mod.rs`, `neoteletext-cli/src/output/mod.rs`) are brought to it.
- **The parent file holds the concept's spine**: the type, its construction, and the `mod` declarations; the children hold its parts. A parent of under 50 lines that only re-exports is a sign the directory should be flattened.
- **Depth.** Two levels below `src/` is the norm; a third is allowed only where the second level is itself a large concept (the interface core's `browser/`, the engine's `render/`).
- **`lib.rs` and `main.rs`** hold the crate's documentation, the lint lists, the `mod` tree, the re-exports and, for a binary, the entry function alone. Logic in a `main.rs` goes into the crate's library (`lib.rs`) so that it can be tested and so that the binary is the thin edge; several browser `main.rs` files are the opposite today.
- **Re-exports** are deliberate and few: a crate's public API is named in `lib.rs` so that moving a file never moves a public path. Where a public path must change, the document and the commit say so, and every importer (the other repository included) is listed.

## 3. Where `cfg` goes

- **A feature's code lives in files of its own**, declared with one `#[cfg(feature = "...")] mod` in the parent; `cfg` on individual items inside a shared file is for the places where one item has two forms, not for whole areas.
- **A platform's code lives in a file or directory of its own** (`mac.rs`, `linux.rs`, `windows.rs`, `unix.rs`), with the shared API in the parent; `#[cfg(target_os)]` on items inside a shared file is for a one-line difference, not a mechanism.
- **An item used by two features** goes in the parent or in a file gated on neither; it is never duplicated.
- The engine's rule that each crate builds with each optional area alone (`cargo xtask features`) is what the layout must satisfy; the browser's `check.sh` builds each area alone the same way.

## 4. Naming

- **Files are nouns naming the concept**: `session.rs`, `strip.rs`, `cookie_jar.rs`; a file that holds the drawing of a thing is `draw.rs` inside that thing's directory, not `thing_draw.rs` beside it.
- **Siblings agree.** Inside one directory, files follow one scheme. The interface core's `browser/*_ui.rs` suffix is dropped once each panel is a directory (`browser/history/{state,draw,input}.rs`), because the directory already says it is the window's.
- **Tests** are `tests.rs` inside the concept's directory, or a `tests` module at the end of a small file; never `foo_tests.rs` beside `foo.rs` and `foo/tests.rs` in the same crate (the engine's `render/` has both forms today).
- **Types are named by what they are**, in the words the standards use (`DEVELOPMENT.md` section 6; EN 300 706 for teletext, the RFCs for the web). No abbreviation but a standard's own.

## 5. Where tests go

- **Unit tests** that need private items sit in `tests.rs` under the concept's directory (`#[cfg(test)] mod tests;`), so a 300-line file of code does not carry 400 lines of tests. A test module under about 60 lines may stay inline at the end of its file.
- **Shared test helpers** (a recorder canvas, a played server, fixture builders) are a `#[cfg(test)]` module in the crate (`test_canvas.rs`, `tests/common/mod.rs`), named by what they are, not by the first test that used them.
- **Integration tests** stay in each crate's `tests/`, one file per area, named by the area.
- **Fuzz targets** stay one file each; a reorganisation lists every path a target imports and updates it in the same commit.
- Tests are moved, never rewritten, in a structure commit; a test that must change to compile is noted in the commit.

## 6. Visibility

- **The narrowest that works.** An item reached only by siblings is `pub(super)`; by the crate, `pub(crate)`; `pub` is the crate's API and is listed in `lib.rs`.
- Splitting a file turns private items that cross the new boundary into `pub(super)`; the per-crate document lists each such item so that the reviewer can see the seams. A seam with many items is a sign the split is in the wrong place.
- Fields stay private; a sibling that needs a field gets a method, or the two files are one concept after all.

## 7. The order of items in a file

A fixed order makes a file readable from the top without searching: the file's documentation; `use` lines (standard, external, crate); constants with their derivations; types; the type's construction (`new`, `Default`); its behaviour, public before private; free functions; the `tests` module last. The engine's lint and panic lists stay in the crate root only.

## 8. The rules the repositories already have, which every move keeps

- `unsafe_code = "forbid"` everywhere but `dock-menu/src/mac.rs`, `web-opener/src/windows.rs` and `confine`'s platform modules (browser requirement 10.12); a split never moves an `unsafe` block outside those modules, and each keeps its `#![expect(unsafe_code, reason)]`.
- The no-panic `#![deny(...)]` list is identical in every crate root that reads outside input, and `scripts/check.sh` (`NO_PANIC_ROOTS`) names those roots: a move that makes a new root adds it to the list and the script in the same commit.
- Every constant is defined once, in the engine's `consts` for teletext constants (REQ-GEN-014, `cargo xtask check-constants`); the browser uses engine constants by name (browser requirement 2.4).
- `no_std` crates stay `no_std`; no `core::fmt` on hot paths, no floating point or atomics in the bare-metal image (`cargo xtask size`).
- Formatting: the engine at 120 columns, the browser at 160, by `cargo fmt`.
- Every public item documented (`missing_docs`); comments say why and cite the clause.

## 9. What a move commit is

- **One concept per commit**: one file split, or one directory made, or one rename, with its `mod` and visibility changes and its import updates in the other crates and the other repository. No behaviour change rides with it.
- **The gate passes at every commit**: the engine's `scripts/check.sh fast` at each, `full` before `main` moves; the browser's `commit` at each, `full` before a push.
- **The diff is a move.** `git diff --color-moved=dimmed-zebra` shows the body of the change as moved lines; what is not moved (new `mod` lines, visibility, `use` lines, a doc comment on a new file) is small and listed in the message.
- **The message** names the concept and the document's step number, and says which public paths changed, if any.
- **Across the repositories**: the engine is reorganised first, each step pushed to `implementation`; the browser re-pins once at the end of the engine's work and updates its imports in that one commit (`DEVELOPMENT.md` section 11), then does its own steps.
