# Security review, approach 2: tool-driven

Engine `~/devel/neoteletext-engine` at `implementation` e7d8927; browser `~/devel/neoteletext-browser` at `main` 494aa91 (which pins the engine at fb2dd8a, an ancestor of e7d8927 differing by one commit). Both were reviewed in throwaway clones under `scratchpad/security/A2/` (`engine`, `browser`), with sources rsynced to `foundintelquiet4060:~/security-a2/` for fuzzing, Miri and Linux ASan. No tracked file of either repository was changed. The proposed fixes below were tried only in a non-git copy on the host (`~/security-a2/patched-check/`).

Scratch paths named below are relative to `/private/tmp/claude-501/-Users-andrewstuart-devel-neoteletext-browser/0baeb9ff-23b7-4dc4-8727-0fa7d5218d0d/scratchpad/security/A2/`.

## Findings, ranked

| # | Severity | Where (item) | Tool | Summary |
|---|---|---|---|---|
| 1 | Medium (gate/process) | `browser/native/Cargo.lock`: `ctutils` 0.4.3, `clipboard-win` 5.4.1 | cargo-deny | RUSTSEC-2026-0385 and a yanked crate. The browser's full gate (`cargo deny check`, pre-push) fails today. The vulnerable code cannot be reached. |
| 2 | Low | engine `neoteletext-formats/src/tti.rs`, `TtiReader::packed_line` | fuzz `tti_enhancement` | A packed X/28 line that the page has no room to store still sets the page function and coding. Writing the page and reading it back gives a different function. |
| 3 | Low | engine `neoteletext-formats/src/tti.rs`, `TtiReader::description`, the `FT` arm of `TtiReader::command`, `TtiReader::set_text` | fuzz `tti_enhancement` (after fix 2) | A value cut to its capacity can end in a CR. The writer writes it out, and the reader drops it as part of the line ending. |
| 4 | Low | browser `core/src/bookmarks.rs`, `Bookmarks::text` (with `Bookmarks::read`) | fuzz `bookmarks_file` | The file numbers items by tree walk, but reading assigns ids in file order. The text is not a fixed point. The fuzz target fails within seconds, so it can turn the pre-push gate red. |
| 5 | Info / hardening | browser `interface-core`, `draw-vello`, `draw-embedded`, `site`; engine `neoteletext-app`, `neoteletext-cli` | clippy (strict) | These crates have no no-panic deny list. No hit can be reached from untrusted input today. Adding the list would keep it that way. |
| 6 | Info | browser `dock-menu/src/mac.rs`; `os-install/src/macos.rs` | ASan | The unsafe modules have no tests, so ASan exercised none of their unsafe code. |
| 7 | Info | `CLAUDE.md` (browser) | grep | The file says unsafe code is only in `dock-menu` and `web-opener`. Requirement 10.12, as amended by decisions 52, 56 and 75, also allows `confine` and `os-install`. The document is out of date; the code is not at fault. |

No memory-safety fault, undefined behaviour, sanitizer report, out-of-memory, timeout or reachable panic was found.

---

### Finding 1: RUSTSEC-2026-0385 (`ctutils`) and a yanked `clipboard-win`. The browser's full gate fails.

**Severity:** Medium, for the process: `scripts/check.sh full` runs `cd native && cargo deny check`, which exits 1 today, so the next push is blocked. As a vulnerability it is negligible: the code cannot be reached (see below).

**Tool output** (`cargo-deny 0.20.2`, from the browser's `tools/bin`, run from `browser/native`):

```
error[vulnerability]: Non-constant-time mask generation and `u128` comparisons
   ├ ID: RUSTSEC-2026-0385
   ├ Solution: Upgrade to >=0.4.4 (try `cargo update -p ctutils`)
   ├ ctutils v0.4.3
     └── digest v0.11.3
         ├── hmac v0.13.0
         │   └── hkdf v0.13.0
         │       └── secret-service v5.2.0
         │           └── zbus-secret-service-keyring-store v1.0.1
         │               └── keyring v4.2.0
         │                   └── neoteletext v0.1.0   (native/core)
         └── sha2 v0.11.1
             └── secret-service v5.2.0 (*)
error[yanked]: detected yanked crate (try `cargo update -p clipboard-win`)
   ├ clipboard-win v5.4.1
     └── arboard v3.6.1
         └── neoteletext-interface v0.1.0
advisories FAILED, bans ok, licenses ok, sources ok
```

`cargo deny check advisories` in `native/fuzz` reports the same advisory, since that workspace pulls in `neoteletext` (core).

**Reachability:** `ctutils` is used by `digest` 0.11 only for `CtEq` in `Mac::verify*` and `CtOutput` equality (`digest-0.11.3/src/mac.rs:144-229`). `secret-service` 5.2.0 uses `hkdf`/`sha2` only to derive the D-Bus session key (`session.rs:89-115`) and never verifies a MAC. The crates are compiled only for Linux, through `keyring`'s Secret Service store, which keeps the cookie-file key. So the branchy mask code is never run on secret data. The constant-time property it lacks is not one the browser relies on.

**Fix:** In `native` run `cargo update -p ctutils` (0.4.3 to 0.4.5) and `cargo update -p clipboard-win` (5.4.1 to 5.4.3), both shown by `--dry-run` as available. Do the same in `native/fuzz`. Commit the lockfiles. Nothing else changes.

**Still ignored, and still present** (`native/deny.toml`): RUSTSEC-2026-0192 (`ttf-parser` 0.25.1 unmaintained, through winit's `sctk-adwaita` on Wayland) and RUSTSEC-2026-0370/0371/0372 (`zvariant`, `zbus_names`, `zvariant_derive` 5.x unmaintained, through `zbus` 5.19.0 in the Secret Service client). All four are `informational = "unmaintained"` with no patched version, and their ignore reasons still hold. The engine (`cargo deny check` in `engine`, `engine/fuzz`, `engine/xtask`) and `native/tuf` and `native/tuf/fuzz` are clean: `advisories ok, bans ok, licenses ok, sources ok`. Only duplicate-version warnings remain: 27 in the browser, 2 in the engine, 6 in tuf.

---

### Finding 2: the TTI reader takes the page function from an X/28 packet it then drops

**Severity:** Low. This is page integrity, with no memory or security effect. A page read from a TTI file can claim a page function and coding that no packet it holds carries. Writing it and reading it back changes the function (here MOT `F,2` instead of `0,0`), which changes how decoders treat the page.

**Where:** `crates/neoteletext-formats/src/tti.rs`, `TtiReader::packed_line`, lines 555-581 at e7d8927. The block commented "REQ-INP-023: X/28/0, X/28/3 and X/28/4 also set the page function" sets `self.page.function` and `self.function_designation` before the packet is stored. When `self.page.raw_packets.push(raw)` then fails (`RAW_PACKETS` = 16, `page.rs:41`), the function stays but the packet is lost.

**Reproducer:** `crashes/tti_enhancement/function-from-dropped-packet.tti` (hand-reduced from the fuzz input `crashes/tti_enhancement/min.bin`, 50 bytes):

```
PN,1FE00
OL,28,Co
OL,27,A   … OL,27,O     (15 distinct X/27 lines: 16 packets in all)
OL,28,                  (X/28/0, function 0 coding 0: the 17th packet)
```

The first write gives `PF,0,0` and the X/28/3 line, but no X/28/0. Reading that back, X/28/3 wins and the second write gives `PF,F,2`. Reproduced locally with `cargo +nightly-2026-10-01 fuzz run -O tti_enhancement crashes/tti_enhancement/min.bin`, which panics at `fuzz_targets/tti_enhancement.rs:65:5` ("writing what was read back changes nothing"). It also reproduces with the scratch program `repro/` (`repro/target/debug/repro --tti <file>`).

**Fix:** store first, and return before touching the function when the page is full:

```rust
let packets = self.page.raw_packets.as_mut_slice();
if let Some(existing) = packets.iter_mut().find(|p| p.number == number && p.designation == designation) {
    *existing = raw;
} else if !self.page.raw_packets.push(raw) {
    // A packet the page cannot hold sets nothing: its function would
    // be written without the packet that carried it.
    self.diagnostic(DiagnosticKind::CapacityExceeded { what: Capacity::RawPackets }, out);
    return;
}
// … then the existing REQ-INP-023 block that sets the function.
```

The full diff is `patched/tti.diff` (its first hunk). Validated on the host copy: all 25 saved `tti_enhancement` failures replay clean, `cargo test -p neoteletext-formats` passes (107 tests), and the fuzzer then found only finding 3. Add `crashes/tti_enhancement/min.bin` to `fuzz/regressions/tti_enhancement/`.

---

### Finding 3: TTI values cut to capacity can end in a carriage return

**Severity:** Low. This is round-trip integrity. A page's description, source, form token or field text read from a file is written back with a trailing CR, and reading that back drops it. The text changes on every cycle. Any digest or comparison over pages written and re-read can be affected. There is no security effect.

**Where:** `crates/neoteletext-formats/src/tti.rs`. The line reader strips every trailing CR before the line feed (lines 316-321, REQ-INP-013). After that, `Text::set` (`text.rs:52`, `copy_prefix`) cuts the value to its capacity, and the cut can land just after a CR in the middle of the value. Three sites are affected:

- `TtiReader::description` (`DE`/`DS`, line 481)
- the `FT` arm of `TtiReader::command` (line 418, `form.token`, `FORM_TOKEN_BYTES`)
- `TtiReader::set_text` (line 702, used by `TtiReader::field_definition`)

The writer (`write/tti.rs`, for example `out.write_all(page.description.as_bytes())` at line 172) writes the bytes verbatim.

**Reproducers:**

- `crashes/tti_enhancement2/description-ends-in-cr.tti`: `DE,` followed by 63 × `a`, then `\rxyz`, then `PN,10000`. Gives `stable: false`.
- `crashes/tti_enhancement2/form-token-ends-in-cr.tti`: `PN,10000`, then `FT,` followed by 63 × `a`, then `\rxyz`. Gives `stable: false`. Lengths 31, 127 and 255 are stable.
- The fuzzer's minimised input is `crashes/tti_enhancement2/min.bin`. It is found within 30 s once finding 2 is fixed. On the unfixed code, finding 2 hides it.

**Fix:** give the reader one helper that every one of the three sites uses. It cuts the value to the capacity and then drops trailing CRs, for example `Text::set_line_value(&mut self, bytes) -> bool` returning whether the whole value was kept. Or slice `args` to `N` bytes and `trim` trailing `\r` before `set`. An ad-hoc version of this for `description` alone is in `patched/tti.diff` (second hunk). It made the description case pass, and the fuzzer then found the `FT` case, which shows the fix belongs in the shared helper. Alternatively the writer could refuse or escape a trailing CR, but the reader is the better place, because REQ-INP-013 already defines CRs before the line feed as line ending.

---

### Finding 4: the bookmarks file is not a fixed point under read then write

**Severity:** Low. Ids are internal and renumbered on every read, so no wrong bookmark is touched within a run. Two effects remain. The file rewrites itself on the first save after any load where a later-numbered folder sits under the bar. And the fuzz target `bookmarks_file` fails within seconds (1.67 M runs on the host). Because `scripts/check.sh full` fuzzes every target for 20 s after its regressions, the pre-push gate can fail by chance.

**Where:** `native/core/src/bookmarks.rs`. `Bookmarks::read` (line 143, through `Bookmarks::take` and `new_id`) gives each item a new id in file order. `Bookmarks::text` (line 571) writes the items in `walk()` order (the bar's subtree before Other's) using their in-memory ids. A folder read later but placed under the bar is written before one read earlier under Other, with the larger number.

**Reproducer:** `crashes/bookmarks_file/min.txt` (52 bytes, from `cargo fuzz tmin`):

```
neoteletext-bookmarks 1
folder	22	2	.
folder	222	1	t
```

Reproduced locally with `cargo +nightly-2026-10-01 fuzz run -O bookmarks_file crashes/bookmarks_file/min.txt`. It panics at `fuzz_targets/bookmarks_file.rs:17:5`: `folder 3 1 t … folder 4 2 .` on the first write versus `folder 4 1 t … folder 3 2 .` on the second.

**Fix:** number the lines in the order `text()` writes them, as `read` numbers them. The diff is `patched/bookmarks.diff`:

```rust
let order = self.walk();
let mut numbers: BTreeMap<u32, u32> = BTreeMap::from([(ROOT, ROOT), (BAR, BAR), (OTHER, OTHER)]);
let mut next = OTHER.saturating_add(1);
for &id in &order {
    numbers.entry(id).or_insert_with(|| { let n = next; next = next.saturating_add(1); n });
}
// each line then writes numbers[&id] and numbers[&item.parent]
```

Validated on the host copy: the saved failures replay clean, a further 300 s of fuzzing (2.34 M runs) found nothing, and `cargo test -p neoteletext bookmarks` passes. Add `min.txt` to `native/fuzz/regressions/bookmarks_file/`.

---

### Finding 5: crates without the no-panic list (strict Clippy triage)

**Command** (`scripts/strict-clippy.sh`):

```
cargo clippy -p <crate> --lib --bins --message-format=short -- \
  -W clippy::arithmetic_side_effects -W clippy::indexing_slicing -W clippy::unwrap_used \
  -W clippy::expect_used -W clippy::panic -W clippy::cast_possible_truncation \
  -W clippy::cast_sign_loss -W clippy::cast_possible_wrap -W clippy::integer_division \
  -W clippy::string_slice -W clippy::as_conversions
```

These are the crate roots without `#![deny(clippy::indexing_slicing, …)]`:

- browser: `interface-core`, `draw-vello`, `draw-embedded`, `dock-menu`, `site`, `stub`, `release-identity`
- engine: `neoteletext-app`, `neoteletext-cli`, `xtask`

The deny list in the listed crates covers `indexing_slicing`, `unwrap_used`, `expect_used`, `panic`, `arithmetic_side_effects`, `unreachable`, `todo` and `unimplemented`. It does not cover the cast lints, `integer_division` or `string_slice`.

| Crate | Hits | Of which can panic (index, slice, str slice, unwrap, expect, panic) |
|---|---|---|
| interface-core | 199 (102 `as`, 67 arith, 17 div, 9 str slice, 4 index) | 13 |
| draw-vello (own) | 22 (6 slices) | 6 |
| draw-embedded (own) | 25 (5 index or slice) | 5 |
| dock-menu | 1 arith | 0 |
| site | 299 (119 `as`, 117 arith, 27 index, 24 div, 10 str, 2 slice) | 39 |
| stub | 0 | 0 |
| release-identity | 9 (build script) | 6, build time only |
| neoteletext-app | 440 (243 `as`, 117 truncation, 51 div, 18 index, 6 arith, 5 slice). Many hits are in path-dependency engine crates, through the cast lints, which no list covers. | 23 |
| neoteletext-cli | 570 (275 `as`, 129 truncation, 72 div, 44 arith, 37 index, 11 slice, 2 str) | 50 |
| xtask | 375 | build tooling, not triaged |

**Triage of every hit that can panic, in the crates that read outside input:**

- `interface-core/src/browser.rs:1516, 1756, 1767-1768, 1782` (`Browser::offset_at`, `Browser::draw_address`) and `editor.rs:103, 107` (`Editor::previous`, `Editor::next`): **not reachable**. Offsets come from `char_indices`, `str::find` plus a match length, or the `Editor` caret and anchor. `Editor::insert` advances by `len_utf8`, `Editor::place` rounds down to `is_char_boundary`, and `Editor::set` resets to 0. All are char boundaries.
- `interface-core/src/browser/console_ui.rs:350`, `settings_ui.rs:280`, `tabs_ui.rs:135`, `wall.rs:716`: **not reachable**. The indexes are `% len`, a fixed-size array indexed by a fixed enum, or a `position()` result.
- `draw-embedded/src/lib.rs:159-160` (`polygon`, after a `first()` check) and `206-207` (`page`, whose `indices` and `palette` are validated in `set_page`, lines 110-114): **not reachable**.
- `draw-vello/src/lib.rs:338-364` (`copy_to`, `damage`): **not reachable**. Damage boxes are clamped to the surface (`damage.rs:29-61`), lengths are compared first, and the `common_ends` bounds are by construction.
- `site/src/websocket.rs:79, 105, 115-118` (`Reader::read`, `parse`): **not reachable**. `at` ≤ 8 and `length` ≤ `MAX_MESSAGE`, and `get(..)` is used before indexing. `site/src/main.rs:32-42` indexes `arguments` (operator input). `terminal.rs` and `serve.rs` index by `% len` or a fixed enum. `site` is the reference channel, not part of the shipped browser.
- `neoteletext-app/src/pipe.rs:174, 196-206, 363-392` (`put_string`, `Cursor`): **not reachable**. `Cursor::bytes` checks the count first, and the payload lengths are compared to 1.
- `neoteletext-app/src/fetch.rs:292-330` (`StdTransport`): index from `slot()`, which is 0 to 2 into 3-element arrays. `session.rs:234-235` copies into an exactly sized buffer.
- `neoteletext-cli/src/commands.rs:245` (`show`: `selected(...)?[0]`): **not reachable**. `Selection::All` is refused at line 232, and `Selection::Page` returns one key or an error.
- `neoteletext-cli/src/keyboard.rs:227` and `view.rs:628`: **not reachable**. The ends are lowered to `is_char_boundary`. `view.rs:339` is guarded by `text.is_empty()`. `terminal.rs:67` (`fit_scale`) divides by `area.rows`, but `text_area` returns `None` when rows is 0 (line 49). `sound.rs:233-262` (`read_wave`) uses `get`, `saturating_add` and `chunks_exact`.
- **Arithmetic:** release builds of both workspaces do not set `overflow-checks`, so an overflow wraps and does not panic. The only additions in `interface-core` on values from another process are `cookies_ui.rs:242` and `history_ui.rs:512`, where `view.first + 1` is a `u32` from the trusted core that echoes the interface's own request. A debug build would panic on `first == u32::MAX`, a release build would show "rows 0 to …". This is cosmetic.
- **Casts:** all the `as` and truncation hits examined are masks, bounded indices or float-to-pixel conversions. In the input-reading crates, `confine/src/broker.rs:460` (`header`, a `u32` to `usize` length) is checked against `max` before the allocation at lines 485 and 617. `confine/src/unix.rs:44, 70, 114` (`send`, `receive`) are `CMSG_*` sizes bounded by `CONTROL_BYTES`. `string_slice` across the whole browser workspace finds only `release-identity/build.rs:44` (build time). Across the engine it finds only the two guarded CLI sites and `xtask`.

**Proposed fix (hardening):** add the shared `#![deny(...)]` list to `interface-core/src/lib.rs`, `draw-vello/src/lib.rs` and `draw-embedded/src/lib.rs`, and put those roots in `NO_PANIC_ROOTS` in `scripts/check.sh`. Today the interface's list (`interface/src/lib.rs`) does not reach the `interface-core` library that does the parsing and drawing. About 25 sites would need `get` or `checked_*`. In the engine, do the same for `neoteletext-app` (it reads the pipe and the network for the CLI). Consider adding `clippy::string_slice` to every list. It costs nothing now, since the only hits are already guarded.

---

### Finding 6: ASan did not exercise the unsafe code of `dock-menu` or `os-install`

`dock-menu`'s 4 tests (`lib.rs`) pass under ASan on macOS, but `src/mac.rs`, where the AppKit FFI is, has no tests. `os-install` has 0 tests on macOS. The Windows modules (`confine/src/windows.rs`, `web-opener/src/windows.rs`, `os-install/src/windows.rs`) cannot be built on either platform used. **Proposed fix:** a test of `dock-menu::mac` that builds and tears down the menu on a headless `NSApplication`. That gives ASan, and a future Miri-free UB check, something to run. A Windows build with `-Zsanitizer=address` (MSVC supports ASan) in the VM would cover the Win32 FFI.

---

## What ran, with commands and results

### (1) Dependency audit

- `cargo-deny 0.20.2` (`~/devel/neoteletext-browser/tools/bin/cargo-deny`), `cargo deny check` with each repository's `deny.toml`:
  - engine: **ok** (exit 0).
  - browser `native`: **FAILED** (finding 1).
  - `native/tuf`: **ok**.
- `cargo deny check advisories`: `engine/fuzz` ok, `engine/xtask` ok, `native/fuzz` FAILED (same RUSTSEC-2026-0385), `native/tuf/fuzz` ok.
- cargo-audit is not installed. cargo-deny's advisories check uses the same RustSec database, fetched on this run (`~/.cargo/advisory-dbs/advisory-db-3157b0e258782691`).
- Outputs: `out/deny-engine.txt`, `out/deny-browser.txt`, `out/deny-tuf.txt`.

### (2) Strict lints

Finding 5 has the results. Outputs are in `out/clippy-*.txt`. A workspace-wide `-W clippy::string_slice` run is in `out/clippy-browser-string_slice.txt` and `out/clippy-engine-string_slice.txt`. Cast lints on protocol, fetcher, decoder, confine and update are in `out/clippy-browser-casts.txt`.

### (3) Fuzzing (foundintelquiet4060, `nightly` 1.101.0 2026-10-11, `cargo fuzz run -O <t> corpus/<t> regressions/<t> -- -max_total_time=<s> -timeout=10 -rss_limit_mb=2048`, 8 at a time; script `scripts/fuzz-host.sh`)

Each target ran for 900 s if it parses network input or another process's messages, and 300 s otherwise. The repositories ship no corpora, only `regressions/` (engine `control_records`, browser `cookie_file`), and those were replayed. Runs are executions.

Engine (21 targets):

| Target | Time (s) | Runs | Result |
|---|---|---|---|
| address | 900 | 178.4 M | clean |
| cookie | 900 | 15.4 M | clean |
| dbsc | 900 | 146.3 M | clean |
| descriptor | 900 | 78.4 M | clean |
| http | 900 | 122.6 M | clean |
| proxy | 900 | 35.8 M | clean |
| sse | 900 | 50.5 M | clean |
| websocket | 900 | 232.7 M | clean |
| audio_packets | 300 | 29.6 M | clean |
| audio_records | 300 | 9.9 M | clean |
| bdf | 300 | 48.5 M | clean |
| bdf_convert | 300 | 3.5 M | clean |
| channel_log | 300 | 6.9 M | clean |
| control_records | 300 | 200.5 M | clean |
| cursor_records | 300 | 219.6 M | clean |
| enhancement | 300 | 60.8 k | clean (slow: about 200 runs/s; slowest unit under 1 s) |
| formats | 300 | 5.7 M | clean |
| input_stream | 300 | 2.2 M | clean |
| packets | 300 | 100.6 k | clean (slow, as above) |
| slicer | 300 | 92.4 M | clean |
| tti_enhancement | 300 | 761 k | **FAILED**: findings 2 and 3 |

Browser `native/fuzz` (28 targets):

| Target | Time (s) | Runs | Result |
|---|---|---|---|
| core_messages | 900 | 56.2 M | clean |
| decoder_messages | 900 | 48.8 M | clean |
| decoder_requests | 900 | 86.3 M | clean |
| fetcher_commands | 900 | 26.0 M | clean |
| fetcher_messages | 900 | 36.5 M | clean |
| interface_messages | 900 | 23.8 M | clean |
| engine | 900 | 70.8 M | clean |
| relay_messages | 900 | 66.5 M | clean |
| broker_requests | 900 | 284.0 M | clean |
| broker_replies | 900 | 335.5 M | clean |
| sound_messages | 900 | 64.5 M | clean |
| sound_requests | 900 | 97.6 M | clean |
| updater_messages | 900 | 259.9 M | clean |
| address | 300 | 57.3 M | clean |
| cookie_file | 300 | 41 k | clean (slow: key work on each input) |
| gzip_member | 300 | 1.5 M | clean |
| history_file | 300 | 7.4 M | clean |
| input_records | 300 | 6.5 M | clean |
| launcher_state | 300 | 131.4 M | clean |
| link_target | 300 | 85.7 M | clean |
| netscape_file | 300 | 171.4 M | clean |
| page_image | 300 | 960 k | clean |
| phone_keys | 300 | 24.3 M | clean |
| release_manifest | 300 | 104.6 M | clean |
| session_file | 300 | 5.6 M | clean |
| settings_file | 300 | 5.6 M | clean |
| version_mark | 300 | 73.7 M | clean |
| bookmarks_file | 300 | 1.67 M | **FAILED**: finding 4 |

Browser `native/tuf/fuzz` (2 targets):

| Target | Time (s) | Runs | Result |
|---|---|---|---|
| http_response | 900 | 30.4 M | clean |
| tuf_metadata | 900 | 21.8 M | clean |

Peak RSS stayed between 135 MB and 653 MB on every target. There were no OOMs, no timeouts and no ASan reports from libFuzzer's instrumented builds.

Follow-up on copies carrying the proposed fixes (`scripts/patched-host.sh`):

- `bookmarks_file`: 300 s, 2.34 M runs, clean.
- `tti_enhancement`: found finding 3 within 30 s. With a description-only patch it then found the `FT` case of finding 3, which shows the shared fix is needed.

Crashes and minimised inputs are in `crashes/`. All reproduce locally against the clones' source; the commands are in each finding.

### (4) Miri

On the host, `cargo +nightly miri test -p <crate> --lib`. All four crates `#![forbid(unsafe_code)]`, so Miri can only find UB in their dependencies (none: they are `no_std` with path dependencies only) or in `core`/`alloc` as used.

- First pass, whole crates under a 90-minute ceiling: `neoteletext-input` **45/45 passed** (1428 s). `neoteletext-core` 68/240 passed before it reached `ecc::tests::hamming2418_exhaustive` (2^24 cases, not feasible under Miri). `neoteletext-formats` 23/107 passed before `detect::tests::auto_reader_detects_then_reads_in_any_chunks`. `neoteletext-audio-mix` 1/11 passed before `tests::a_live_sound_follows_a_sender_whose_clock_runs_one_per_cent_fast`. These runs were stopped after 70 minutes.
- Second pass, one Miri process per test with a 120 s ceiling over all 403 unit tests of the four crates, 8 workers (`scripts/miri-per-test.sh`, `timeout 120 cargo +nightly miri test -q -p <crate> --lib -- --exact <test>`):

  | Crate | Tests | Passed | Hit the 120 s ceiling | Other |
  |---|---|---|---|---|
  | neoteletext-core | 240 | 235 | 5 | 0 |
  | neoteletext-formats | 107 | 99 | 6 | 2 |
  | neoteletext-audio-mix | 11 | 10 | 1 | 0 |
  | neoteletext-input | 45 | 44 | 1 | 0 |

  - The tests that hit the ceiling are exhaustive or long loops: core `ecc::tests::hamming2418_exhaustive`, `ecc::tests::page_checksum_shift_register`, `render::level25_tests::resolved_mode_matches_palette_mode_on_level1_pages`, `render::level25_tests::change_tracking_in_the_resolved_mode` and `render::tests::rows_render_identically_in_any_order`; formats `detect::tests::{detection_finds_every_format, detects_each_t42_layout_even_with_a_corrupted_start, auto_reader_reports_unknown_input, auto_reader_detects_then_reads_in_any_chunks, detects_signatures}` and `bdf::tests::limits`; audio-mix `tests::a_live_sound_follows_a_sender_whose_clock_runs_one_per_cent_fast`; input `keys::tests::every_code_round_trips_and_unused_codes_name_nothing`, which passed in the first pass.
  - The two "Other" results are formats `robustness::any_tti_lines` and `robustness::any_input_in_any_split`. Both stopped with `unsupported operation: getcwd not available when isolation is enabled`, from proptest's failure persistence: the instrument, not the code. Rerun with `MIRIFLAGS=-Zmiri-disable-isolation PROPTEST_CASES=8`, `any_input_in_any_split` **passed** (376 s) and `any_tti_lines` hit a 900 s ceiling.
- **Result:** no undefined behaviour reported in any of the 389 tests that completed under Miri: 388 in the second pass plus `any_input_in_any_split`, with `neoteletext-input` complete in the first pass. 14 tests are too slow for Miri.

### (5) Sanitizers

- **macOS** (`nightly-2026-10-01`, `RUSTFLAGS=-Zsanitizer=address`, `--target aarch64-apple-darwin`, separate target directory):
  - `dock-menu`: 4/4 passed.
  - `web-opener`: 1 passed, 1 ignored (it opens a browser).
  - `os-install`: 0 tests.
  - `confine`: 9/10 passed. `tests::a_helper_gets_only_the_environment_it_is_given` failed because the confined helper's macOS sandbox profile blocks loading `librustc-nightly_rt.asan.dylib` from `~/.rustup` (`dyld: … (blocked by sandbox)`). This is the instrument failing, not a fault: the same test passes without ASan and under ASan on Linux.
- **Linux host** (`RUSTFLAGS=-Zsanitizer=address`, `ASAN_OPTIONS=detect_leaks=1:abort_on_error=1`):
  - `confine`: all tests passed (lib 8, including `unix::tests::descriptors_travel_with_their_message` over the `sendmsg`/`recvmsg` SCM_RIGHTS code; `tests/probe.rs` 5, covering the Landlock, network-namespace and seccomp probes; and the environment probe).
  - `web-opener`: 1 passed, 1 ignored.
  - `os-install`: 0 tests.
- No sanitizer report anywhere.

### (6) Tests with `--release`

`cargo test --workspace --release --no-fail-fast` on macOS:

- engine: 52 test binaries, **884 passed, 0 failed**, 9 ignored. The 9 ignored measurement tests were then run with `-- --ignored` in release: all passed.
- browser `native`: 50 binaries, **449 passed, 0 failed**, 5 ignored (they need the internet, an audio device or a web browser).
- `native/tuf`: 7 binaries, **9 passed, 0 failed**.

No difference between debug and release behaviour showed up.

## Ran clean

Every fuzz target except `tti_enhancement` and `bookmarks_file`. That includes all network parsers (engine http, websocket, sse, proxy, cookie, dbsc, descriptor, address; tuf http_response, tuf_metadata; relay_messages) and all inter-process message decoders (core, decoder, fetcher, interface, sound, broker, updater). Also clean:

- cargo-deny for the engine and tuf.
- Every release test suite.
- ASan for `confine` (Linux), `dock-menu`, `web-opener` and `os-install`.
- Miri for `neoteletext-input`, plus the Miri results at the end.
- `string_slice` across both workspaces.
- Strict Clippy: no hit that untrusted input can reach.
