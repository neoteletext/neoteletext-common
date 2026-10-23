# 20. The trusted core (`native/core`)

| | |
|---|---|
| **Rests on** | A reading of every file of `native/core` at browser commit `494aa91` (25 files under `src/`, three under `tests/`, `build.rs`; 14,219 lines), with item ranges measured by brace-matching; `docs/architecture.md` sections 6 and 14; `DEVELOPMENT.md` section 6; `scripts/check.sh`; `00-conventions.md`. |
| **Phase** | B3 (`01-method-and-order.md` section 2): after `protocol`, `interface-core`, `confine` and `update`. |
| **Measured before** | 25 source files; largest 2,645 lines, median 375; 9 files over 500; 9 functions over 80 lines; 7 `impl` blocks over 300; 3,094 test lines inline and 644 in files of their own (`links/tests.rs`, `hostile_tests.rs`); `cfg(feature)` sites 56 in `main.rs`, 5 in `session.rs`, 4 in `page_controls.rs`, 3 in `hostile_tests.rs`. No `too_many_lines` allow anywhere in the crate. |

## 1. The crate as it is

### 1.1 Purpose and the two roots

The package `neoteletext` is the broker (`neoteletext`) and the trusted core (`neoteletext --core`) in one program (decision 56), and the library the fuzz targets read. It has two crate roots, each carrying the no-panic `#![deny(...)]` list and each named in `scripts/check.sh` `NO_PANIC_ROOTS` (lines 39-43).

| Root | Lines | Holds |
|---|---|---|
| `src/lib.rs` | 37 | Fifteen `pub mod`s: every part of the core that is pure logic or a kept file's format (`address`, `bookmarks`, `calendar`, `console`, `cookies`, `frames`, `hearing`, `history`, `links`, `outbox`, `restore`, `settings`, `sleep`, `start_page`, `typing`). Nothing in it names `Core`, a process, a pipe or the broker. 7,127 lines. Its doc comment (1-5) is out of date: it lists seven of the fifteen modules. |
| `src/main.rs` | 2,645 | The `Core` struct and every `impl Core` that no sibling took, the helper processes, the event loop, start-up and shutdown, the settings rules, the broker's handlers and both entry points; and seven `mod`s: `cookie_control`, `hostile_tests` (test), `library`, `page_controls`, `session`, `source`, `updates`. 6,754 lines with its modules. Every binary module but `source.rs` is an `impl Core` block or a type `Core` owns. |
| `tests/` | 338 | `confined_core.rs` (46), `confined_keyboard.rs` (72; `phone-keyboard`; `#[ignore]`), `latency.rs` (220; `interaction`; dev-dependency `decoder`). |
| `build.rs` | 26 | Delay-loads `shell32.dll` on Windows; bakes `NEOTELETEXT_VERSION`. |

Lints are the workspace's (`unsafe_code = "forbid"`, `missing_docs`, `unused_qualifications`, Clippy `pedantic`, `allow_attributes_without_reason`, `dbg_macro`, `todo`, `unimplemented`; `native/Cargo.toml:121-133`), errors under the gate's `-D warnings`; `clippy.toml` allows unwrap, expect, panic and indexing in tests but not `arithmetic_side_effects`, which is why most test modules carry `#[allow(clippy::arithmetic_side_effects, ..., reason = "a test")]`. `rustfmt` at 160 columns. Toolchain Rust 1.99.0.

### 1.2 Features

| Feature | Default | What it gates in this crate |
|---|---|---|
| `links` | on | `protocol/links`, `interface-core/links`, `dep:web-opener`; `pub mod links` (`lib.rs:29-30`); `Core::links`, the hyperlinks `impl Core` (`main.rs:1903-2038`), `start_bookmark_reader`'s sibling `Follow` use in `page_controls.rs:95-104`, `Session::{follow, show_page}` and `ChannelState::has_page` (`session.rs:104-108, 462-471, 486-497`), the `open_web` handler in `broker()` (`main.rs:2422-2426`), and 20-odd arms and statements in `intent`, `decoded`, `fetched`, `send_all`, `put_to_sleep`, `went`, `send_controls` |
| `interaction` | on | `protocol/interaction`, `interface-core/interaction`, `dep:neoteletext-input`, `dep:unicode-normalization`; `pub mod typing` (`lib.rs:35-36`); `Core::{typing, opened}`, `focused` (with `links`), `input_intent`, `deliver_typing`, `typing_tick`'s body (`main.rs:400-470`), arms in `fetched`, `decoded`, `send_all`, `opened`, `put_to_sleep`, `loading_wanted`; `tests/latency.rs` |
| `phone-keyboard` | on; implies `interaction` | `protocol/phone-keyboard`, `interface-core/phone-keyboard`; `RELAY_VARIABLE`, `Event::{Phone, PhoneEnded}`, `Core::{phone, phone_view}`, the phone `impl Core` (`main.rs:1795-1899`), `flush`'s phone arm, two arms of `handle`; `tests/confined_keyboard.rs` |

`scripts/check.sh:76-85` runs Clippy with every feature, with none, and with `links`, `interaction` and `links interaction` alone; every step of this document builds in all five shapes.

### 1.3 Module tree with line counts

`T` is the inline `#[cfg(test)] mod tests` of the file.

```
src/
  lib.rs                   37   [lib root]  deny list, 15 pub mod
  main.rs                2645   [bin root]  deny list, 7 mod, Core, five impl Core, broker, main   T 112 + 80
  address.rs              308   [lib]  what the address field may open              T 99
  bookmarks.rs            800   [lib]  the bookmarks tree and bookmarks.txt         T 167
  calendar.rs             162   [lib]  civil-calendar arithmetic, days in words     T 38
  console.rs              290   [lib]  the console's kept entries                   T 106
  cookie_control.rs       606   [bin]  impl Core: fetchers' cookies, the file, the panel   T 208
  cookies.rs              725   [lib]  the cookie store and its sealed file         T 196
  frames.rs               121   [lib]  which frames are sent, encoded against the last   T 64
  hearing.rs              229   [lib]  which channel's sound is heard, the ledger   T 96
  history.rs              649   [lib]  history rows, history.txt, search; write_whole   T 173
  hostile_tests.rs        269   [bin, cfg(test)]  requirement 3.9's harness
  library.rs             1245   [bin]  impl Core: recording, history panel, bookmarks, star, bar   T 382
  links.rs                792   [lib]  targets, destinations, each image's links, the strip's question
  links/tests.rs          375   [lib]
  outbox.rs               245   [lib]  a pipe written by its own thread             T 88
  page_controls.rs        176   [bin]  impl Core: the open page's controls          T 24
  restore.rs              470   [lib]  session.txt                                  T 141
  session.rs             1460   [bin]  tabs, channels, windows, closed tabs, the kept session   T 495
  settings.rs             483   [lib]  settings.txt, Proxy, the local-address rule  T 127
  sleep.rs                162   [lib]  sleeping tabs and what their decoders had    T 48
  source.rs               147   [bin]  a channel's bytes from a file or folder      T 37
  start_page.rs           256   [lib]  neoteletext:home as TTI                      T 86
  typing.rs               679   [lib]  typing into a page                           T 242
  updates.rs              480   [bin]  the broker's three update handlers and the core's updater   T 85
tests/
  confined_core.rs         46
  confined_keyboard.rs     72
  latency.rs              220
```

The one directory module, `links.rs` + `links/tests.rs`, is already the 2018 layout `00-conventions.md` section 2 asks for; the workspace's other instance is `interface-core/src/browser.rs` + `browser/`. There is no `mod.rs` in the workspace.

### 1.4 Public paths and who imports them

The library's `pub` surface and every importer outside the crate (both repositories searched):

| Path | Importer |
|---|---|
| `neoteletext::address::parse` | `native/fuzz/fuzz_targets/address.rs` |
| `neoteletext::bookmarks::{Bookmarks, MAX_DEPTH, MAX_ITEMS}` | `fuzz_targets/bookmarks_file.rs` |
| `neoteletext::cookies::{Store, PER_CHANNEL, TOTAL}` | `fuzz_targets/cookie_file.rs` |
| `neoteletext::history::{History, MAX_FILE, MAX_ROWS}` | `fuzz_targets/history_file.rs` |
| `neoteletext::links::{Target, parse_target, web_address}` | `fuzz_targets/link_target.rs` |
| `neoteletext::restore::{Saved, MAX_ENTRIES, MAX_FILE, MAX_TABS, MAX_WINDOWS}` | `fuzz_targets/session_file.rs` |
| `neoteletext::settings::{Settings, MAX_LOCAL, MAX_VOLUME}` | `fuzz_targets/settings_file.rs` |
| `neoteletext::typing::{Send, Typing}` | `fuzz_targets/input_records.rs` |
| `neoteletext::frames::Frames` | `tests/latency.rs` |

No other workspace crate depends on the library. `native/fuzz` is a workspace of its own with its own lockfile (`fuzz/Cargo.toml:19`, `neoteletext = { path = "../core" }`), built by the full gate on nightly.

The binary's cross-file reaches are inside one crate and are the subject of section 2.2. The integration tests reach only `confine`, `protocol`, `neoteletext_input`, `decoder` and the one lib path above; `hostile_tests.rs` is a module of the binary, not an integration test, and reaches `crate::{Bookmarks, Core, Outbox, Settings}` (through `main.rs`'s private `use` lines, `main.rs:67, 74, 76`) and `crate::session::Session`.

## 2. Findings

### 2.1 File by file

**`main.rs` (2,645).** Eighteen responsibilities in one file. In order: the crate doc (1-16); `windows_subsystem` and the deny list (20-33); `mod`s (35-42); the `use` block (44-82) whose private imports sibling tests rely on; `RELAY_VARIABLE` (84-88, with the same `#[cfg]` written twice); seven constants (90-107), of which `PACKET_BYTES = 42` restates the engine's; `enum Event` (109-132); `Shown` (134-140); `Decoder`, `Fetcher` (142-157); `spawn`, `stop_decoder`, `start_decoder`, `start_bookmark_reader`, `start_fetcher`, `read_interface` (159-289), five of the six reader-thread loops; `Reach` (291-304); `struct Core` with 40 fields (306-392); `impl Core` (1) of 898 lines (394-1291) holding typing glue (402-470), sending (474-487), windows (491-639), the sound and decoder deliveries (642-660), the decoders' and fetchers' lifecycle (667-769), `certificate_refused` and `fetched` (774-869), `send_all`/`send_mutes`/`send_tabs` (873-925), `intent` (932-1037), `window_intent`/`keep_window`/`keep_session` (1041-1088), the tab and page intents, `opened`, `reload`, `went` (1092-1151), `load`, `decoder_ended`, `decoded` (1155-1290); `impl Core` (2) of 373 lines (1293-1667) titled "Settings, the strip's notice and the developer console" but holding also `flush`, `loading_wanted`, `next_wake`, `tick`, the updates glue, the sound helper and `broker()`; `checked_change` (1672-1758); `open_at_start`, `open_home` (1764-1789); the phone `impl Core` (1795-1899); the hyperlinks `impl Core` (1903-2038); `Core::new` (2040-2096); four `load_*` (2100-2167); `handle` (2170-2226); `run` (2228-2341); `ended` (2346-2349); the broker's constants and handlers (2353-2406); `broker` (2411-2438); `main` (2440-2449); `mod program_tests` (2452-2563, six tests of five concerns); `mod tests` (2565-2645, `cfg(all(test, unix))`, three tests). `log`'s doc comment (1382-1385) is `send_console`'s first sentence glued to `log`'s.

**`session.rs` (1,460).** Seven concerns: `ChannelState` (25-141: a channel's page table and contents); `Visit`, `Pending`, `ClosedTab`, `Window`, `Went`, `Tab` with its list rules and chapter stops (144-272); `Session` (285-310) and `impl Session` of 617 lines (348-964): constructors (352-380), the start page (385-405), tab navigation (411-579), closed tabs (586-627, 755-764), counts (634-642), windows (646-752), the kept session (770-879), mutes, moves, close and the views (882-963). `without` (314-328) and `kept_history` (332-346, with an `eprintln!`) are free functions. The doc comment at 895-897 describes `close` but sits above `move_tab`. Tests 966-1460 (20 tests).

**`library.rs` (1,245).** `Numbers<T>` (33-61), the row numbering every panel uses, including the cookies panel; `Manager` and `Library` (64-96); three helpers (100-116); `impl Core` of 745 lines (118-862): dispatch, `local_time`, recording and expiring (120-243); the history panel, suggestions, the tab list (248-482, under a `// ---- History ----` comment); the manager with two import paths, export, the star and the bar (488-861, `// ---- Bookmarks ----`). `import_bookmarks` (587-616) starts a decoder process. Tests 864-1245: a `Sink` and a `Test` harness (878-944) and twelve tests, three of which test `main.rs` concerns (section 2.7).

**`bookmarks.rs` (800).** The tree (`Item`, `Removed`, `Listed`, `Bookmarks`, 51-116), `name_of` and `bookmark_address` (119-136), and `impl Bookmarks` of 493 lines (138-630) in which the file's reading (`read`, `take`, 143-216) and writing (`text`, `load`, `save`, `export`, 571-629) bracket the tree's primitives and edits (218-567). Tests 632-800.

**`links.rs` (792) + `links/tests.rs` (375).** Six concerns: the target grammar (`Target`, `parse_target`, `web_address` and five helpers, 66-196; the one page-data parser in the core); classification (`Destination`, `Channel`, `Descriptor`, 200-305); per-image tables (`Link`, `Image`, `PageState`, 309-339); `Follow`, `Refusal`, `Asking`, `Links` (343-399); `impl Links` of 368 lines (401-768) covering bookkeeping, deciding, pointing, following and the strip's question (700-767); `overlap`, `carry_since` (771-789). The tests reach `Descriptor`, `Channel`, `page_links`, `INITIAL_PAGE` through `use super::*`.

**`cookies.rs` (725).** The store (`Jar`, `new_jar`, `Mode`, `Channel`, `Listed`, `Refused`, `Store`, 44-161; `impl Store` 163-440, with the file's text form in `export`/`import` 359-439) and, after it, the sealed file (`FILE_NAME` … `MAX_SEALED`, `cipher`, `seal`, `open`, `save`, `load`, `remove`, 443-524) with `is_tag` (526-528) after the sealing code though it belongs to `import`. Tests 530-725.

**`typing.rs` (679).** One concept, by design the one encoder of the input protocol: `Send` (42-47), `Channel` (51-102), three helpers (105-122), `Typing` and its impl of 299 lines (126-436). Tests 438-679, among them `no_input_code_logs` (646-667) with an `include_str!("typing.rs")` and four `include_str!("../../<crate>/src/<file>")` paths relative to this file. `PAGE_COLUMNS = 40` (36) restates `interface_core::canvas::COLUMNS`.

**`history.rs` (649).** Three concerns: rows and the file (`Row`, `Visit`, `Range`, `History`, 42-134; `impl History` 149-436 less the search); search, completion and suggestions (`query` 286-300, `completion` 342-357, `suggest` 362-378, `has_address` 323-325); and two generic file utilities, `private_options` and `write_whole` (454-475), used by `bookmarks.rs:10`, `restore.rs:13` and `cookies.rs:494`, which are not history. Tests 477-649.

**`cookie_control.rs` (606).** Four concerns in one `impl Core` of 315 lines (83-397): replies to fetchers (`fetcher_channel`, `answer`, `cookie_message`, `cookie_reply`, 85-149; `answer` 91-96 writes a fetcher's outbox and flushes it at once, the one flush outside `Core::flush`); the sealed file's life (153-247); `private_cookies_closed`, `clear_cookies_since` (251-264); the panel (`Row` 27-32; `cookies_request`, `send_cookies`, 267-396). Three protocol-to-lib mappings (`site`, `mode`, `mode_view`, 58-81). Tests 399-606 with a second copy of the `Sink`/`Test` harness.

**`restore.rs` (470).** One concept, the session file: types (47-92), `Tab::trimmed`, `Saved::tab_count` (94-111), line parsers (113-162), `impl Saved` (164-328) with `read` at 95 lines. Tests 330-470. Named for what is done with the file rather than for the file; every other kept file's format lives in the module named for its concept.

**`settings.rs` (483).** Four concerns: the file (`VERSION_LINE` … `TEMPORARY_NAME`, `Settings`, `read`, `take`, `text`, `load`, `save`), `Proxy` (50-96), the local-address rule `is_local` (169-174) and `checked_address` (179-184), and the platform folder `folder` (342-355). `save` (319-336) is a private copy of `history::write_whole` with its own `mode(0o600)` (329). Tests 357-483.

**`updates.rs` (480).** Two processes' code in one file, marked by `// ---- The broker's side ----` (39) and `// ---- The core's side ----` (86): the broker's `installation`, `tell_launcher_healthy`, `launcher_state`, `updater_grant` (42-84), called from `main.rs::broker` through `Handlers`; then `Health` (89-121), `Updates` (124-156) and `impl Updates` (158-394) which spawns the updater and reads its pipe (`start` 200-232, the sixth reader loop), writes it (`tell` 244-250), and holds the health and offer rules and the panel's `status` (361-393). Tests 396-480.

**`address.rs` (308), `calendar.rs` (162), `console.rs` (290), `frames.rs` (121), `hearing.rs` (229), `outbox.rs` (245), `page_controls.rs` (176), `sleep.rs` (162), `source.rs` (147), `start_page.rs` (256).** Each one concept at or under the size the conventions ask for. `console.rs` holds the entries' ring (28-146) and the text of a packet or exchange (150-183), two parts of one concept. `page_controls.rs` is the shape every binary-side concept should take: a state struct, one `impl Core`, tests of 24 lines; it carries two `#[cfg(feature = "links")]`/`#[cfg(not)]` pairs (95-104, 129-132) only because the links glue is in the same function. `start_page.rs:30` restates `COLUMNS = 40`; `hearing.rs:22` writes `48_000 * 2`. `source.rs` has no `Core` dependency and is in the binary only because the broker reads files for the core.

**`hostile_tests.rs` (269).** A whole-file test module of the binary with its own `Sink` (44-55), a deterministic `Random` (59-78), the frame makers (82-175) and one test (195-269) that builds a `Core` with `Core::new`, calls `core.cookie_reply` and `core.intent`, and reads `core.session.tabs`, `core.settings` and `core.to_interface`. Named by path in `docs/requirements.md:177`, `docs/architecture.md:702` and `docs/security-analysis.md:391`.

### 2.2 The private-field reach that constrains the split

Every field of `Core` (`main.rs:306-392`) is private, and so are most of its methods; `library.rs`, `cookie_control.rs`, `page_controls.rs` and `hostile_tests.rs` read them directly. That is legal only because those modules are children of the crate root where `Core` is defined: an item is visible in its defining module and that module's descendants. The counts, by file:

| File | `Core` fields read (count) | Private `Core` methods called |
|---|---|---|
| `library.rs` | `session` 109, `library` 105, `settings_folder` 4, `settings` 3, `broker` 3, `console` 2, `to_interface` 1, `events` 1 | `send`, `strip`, `send_history`, `log`, `send_bar`, `send_star`, `send_all`, `keep_session`, `broker`, `went`, `send_cookies`, `send_bookmarks`, `say`, `save_settings`, `others_stale`; in tests also `intent`, `fetched`, `keep_window`, `switch_window`, `next_wake` |
| `cookie_control.rs` | `cookies` 58, `session` 7, `settings` 6, `settings_folder` 4, `console` 2, `to_interface` 1, `fetchers` 1, `broker` 1 | `log`, `send_cookies`, `now`, `send`, `say`, `save_settings`, `active_channel`; in tests `history_request` |
| `page_controls.rs` | `controls` 20, `links` 2 | `tell`, `send`, `now`, `follow`, `active_channel` |
| `hostile_tests.rs` | `session` 7, `settings` 2, `to_interface` 1 | `new`, `intent`, `cookie_reply` |

`Session`'s fields are `pub` but `next_window`, `next_closed`, `next_channel`, `reader`; `ChannelState::new`, `Visit::new`, `Tab::push`, `Tab::next_chapter_stop`, `without` and `kept_history` are private and used across what will be separate files. `Links`'s fields and `Descriptor` are private and reached by `links/tests.rs`.

The consequence for section 3: an `impl Core` block can only live in a descendant of the module that defines `Core`; the same for `Session` and `Links`. The alternative, `pub(crate)` on fifteen fields and twenty methods, is the seam `00-conventions.md` section 6 warns against.

### 2.3 Oversized `impl` blocks and functions

| `impl` block | File:lines | Lines |
|---|---|---|
| `impl Core` (1) | `main.rs:394-1291` | 898 |
| `impl Core` | `library.rs:118-862` | 745 |
| `impl Session` | `session.rs:348-964` | 617 |
| `impl Bookmarks` | `bookmarks.rs:138-630` | 493 |
| `impl Core` (2) | `main.rs:1293-1667` | 373 |
| `impl Links` | `links.rs:401-768` | 368 |
| `impl Core` | `cookie_control.rs:83-397` | 315 |

| Function | File:lines | Lines | What it interleaves |
|---|---|---|---|
| `run` | `main.rs:2228-2341` | 114 | argument parsing; spawning the interface; loading four kept files; the first window message; building `Session` with the broker's reader; `Core::new`; start of cookies, sound, updater; opening every kept window; the event loop and its timeout; shutdown of every helper |
| `Core::intent` | `main.rs:932-1037` | 106 | the window short-circuit; 25 arms, eight handled inline; three post-steps |
| `Core::history_request` | `library.rs:248-348` | 101 | ten request kinds, including clearing the tabs' lists and cookies |
| `Saved::read` | `restore.rs:168-262` | 95 | four line kinds, a `finish` closure, bounds, two post-fixes |
| `Core::decoded` | `main.rs:1198-1290` | 93 | eleven message kinds; a frame's links, image, history record and controls in one arm |
| `checked_change` | `main.rs:1672-1758` | 87 | thirteen setting kinds, each a rule and a sentence |
| `Core::send_cookies` | `cookie_control.rs:310-396` | 87 | listing, the block list, filter, sort, grouping by origin, day words, numbering, paging |
| `Core::bookmark_request` | `library.rs:498-582` | 85 | fourteen request kinds |
| `Core::fetched` | `main.rs:788-869` | 82 | eleven message kinds; contents also clears the certificate screen and resends the channel |

All nine are under Clippy's `too_many_lines` (100 lines of code) today; none is split by this plan, which moves code. Each is one `match` over one message or request family, which the conventions allow as "one clause"; the plan places each in the file of its family so that a later split has its home.

### 2.4 Duplicated shapes

1. **The reader-thread loop** (read until `Ok(None)` or `Err`, send an `Event`, then send an `*Ended` event): `main.rs:183-197` (decoder), `252-266` (fetcher), `273-287` (interface), `1575-1589` (sound), `1838-1852` (phone), `updates.rs:215-229` (updater; differs in that `read_from_updater` returns `Result<M>` and ends on `UnexpectedEof`). Six copies differing in the read function and the two `Event` variants.
2. **Kill then wait**: `main.rs:174-175, 229-230, 766-767, 1191-1192, 1893-1894, 2320-2321, 2330-2331`; `updates.rs:238-239`. The fetcher's close (drop stdin, drop input, kill, wait) at `763-767` and again at `2318-2321`.
3. **Start a decoder and replay what was kept**: `main.rs:687-694` (`match_decoders`) and `749-757` (`grow_decoder`).
4. **Restore a parked window's `Shown`** (three assignments): `main.rs:500-503` and `582-585`.
5. **`load(folder)` of a kept file** (`metadata`; `NotFound` → the default; too long → a dropped line; `read`; `from_utf8_lossy`; `read`): `bookmarks.rs:591-603`, `history.rs:390-402`, `settings.rs:296-311`, `restore.rs:305-318`; `cookies.rs:503-513` the binary variant.
6. **Write whole through a temporary with mode 0600**: `history.rs:454-475` and `settings.rs:319-336`.
7. **`load_*` with logging**: `main.rs:2100-2120, 2124-2136, 2140-2152, 2156-2167`.
8. **Seconds since 1970**: `calendar.rs:12-14` (`utc_now`, `i64`), `cookie_control.rs:54-56` (`now_unix`, `u64`), `library.rs:145` (a closure, `i64`), `main.rs:2026` (inline, `u64`).
9. **`ToSound::Settings { sound, volume }`**: `main.rs:1592` and `1599`.
10. **A clear range to seconds**: `library.rs:300-307` and `322-329`.
11. **`FolderRow` from `bookmarks.folders()` with numbering**: `library.rs:686-696`, `700-708`, `799-809`.
12. **`ItemRow` builders**: `library.rs:653-674` (`item_row`) and `837-846` (`bar_row`).
13. **Cookie mode mapping**: `cookie_control.rs:66-72` (`mode`) and `main.rs:1744-1748` (inline in `checked_change`).
14. **The test harness** (`Sink` to an `mpsc` channel; `Test { core, written, folder }` built with `Core::new(Session::new(Bookmarks::default()), …, Outbox::new(Sink(sender)), None)`; draining with `recv_timeout(200 ms)` and `read_from_core`): `library.rs:878-944`, `cookie_control.rs:412-487`, `hostile_tests.rs:44-55, 200-203`; `main.rs:2587-2590` (`test_core`).
15. **Hexadecimal page digits**: `address.rs:67-69` and `links.rs:51-53` define `PAGE_DIGITS`, `SUBPAGE_DIGITS`, `HEXADECIMAL` twice; `address::fragment_page` (83-91) and `links::page` (120-126) implement the same rule.
16. **Scheme lists**: `address.rs:172-178`, `links.rs:55-57`, `history.rs:38`.
17. **`#[cfg(feature = "links")]`/`#[cfg(not)]` arm pairs** that exist only because links glue shares a function: `page_controls.rs:95-104, 129-132`; `main.rs:946-964, 1141-1147, 1247-1258`.
18. **Four `load` match shapes for files that are not there**: `bookmarks.rs:594`, `history.rs:393`, `settings.rs:301`, `restore.rs:308`, `cookies.rs:506, 521` (the `NotFound` arm), the same text five times.

### 2.5 Constants defined twice, and against the engine's and the interface core's

`00-conventions.md` section 8: each constant once; the browser uses engine constants by name.

| Constant | Where | Restates |
|---|---|---|
| `PACKET_BYTES = 42` | `main.rs:95` | `neoteletext_core::consts::PACKET_BYTES`, which `console.rs:11` imports |
| `COLUMNS = 40` | `start_page.rs:30` | `interface_core::canvas::COLUMNS`, which `links.rs:14` imports |
| `PAGE_COLUMNS = 40` | `typing.rs:36` | the same |
| `MAX_TABS` | `restore.rs:21` and `session.rs:279` | both `protocol::MAX_TABS` |
| `MAX_WINDOWS` | `restore.rs:23` | `interface_core::library::MAX_WINDOWS`, used directly in `session.rs:17` and `main.rs:610` |
| `PAGE_DIGITS`, `SUBPAGE_DIGITS`, `HEXADECIMAL` | `address.rs:67-69` and `links.rs:51-53` | each other |
| `STREAM_HELD_SAMPLES = 48_000 * 2` | `hearing.rs:22` | a sample rate written as a literal |

The plan moves these as they are (section 6 lists them for the owner); it does not add a restatement.

### 2.6 Naming

| What | Today | Why it misleads |
|---|---|---|
| The binary side of a library concept | `cookie_control.rs` for `cookies.rs`; `library.rs` for `history.rs` and `bookmarks.rs`; the sides of `links`, `typing`, `settings`, `console`, `hearing`, `sleep`, `frames` inside `main.rs` | three schemes for one relationship; `page_controls.rs` (plural) beside `cookie_control.rs` (singular) |
| The session's file | `restore.rs` (lib) beside `session.rs` (bin) | every other kept file's format is in the module of its concept; the fuzz target is already `session_file.rs` |
| `Channel` | `links::Channel<'a>`, `cookies::Channel`, `typing::Channel`, `session::ChannelState`, `interface_core::channel::Channel` | `main.rs:73` has to alias `LinkChannel` |
| `Send` | `hearing::Send`, `typing::Send` | `main.rs` imports one unqualified and spells the other by path |
| `Listed` | `bookmarks::Listed`, `cookies::Listed` | different things |
| `Visit` | `session::Visit`, `history::Visit` | different structs with the same name in files that import each other's module |
| `Tab`, `Window`, `Entry` | `restore.rs` | beside `session::{Tab, Window, Visit}`; `session.rs` writes `restore::Tab` by path throughout |
| `Row`, `State` | `history::Row` and `cookie_control::Row`; `page_controls::State` beside `update::state::State` and `neoteletext_input::session::State` | |
| Section comments standing for modules | `library.rs:245, 484`; `updates.rs:39, 86` | `// ---- History ----`, `// ---- The broker's side ----` mark what are separate concepts |

The plan renames nothing but the binary-side files it moves (`cookie_control.rs` → `trusted_core/cookies.rs`) and offers `restore` → `session_file` to the owner (section 3.3); the type names stay.

### 2.7 Where tests are

| Placement | Files |
|---|---|
| Inline `mod tests` over 60 lines | `main.rs` (two modules, 112 and 80), `address` 99, `bookmarks` 167, `console` 106, `cookie_control` 208, `cookies` 196, `frames` 64, `hearing` 96, `history` 173, `library` 382, `outbox` 88, `restore` 141, `session` 495, `settings` 127, `start_page` 86, `typing` 242, `updates` 85 |
| Inline, under 60 | `calendar` 38, `page_controls` 24, `sleep` 48 (an inner `#![allow]`, the only one), `source` 37 |
| A `tests.rs` under the concept's directory | `links/tests.rs` 375 (the convention's form) |
| A `*_tests.rs` file | `hostile_tests.rs` 269 |
| Integration | `tests/confined_core.rs`, `tests/confined_keyboard.rs`, `tests/latency.rs` |
| Tests of another file's concern | `library.rs:949-968` `a_refused_certificate_shows_until_the_contents_arrive` (what a fetcher said, `main.rs:774-786`); `library.rs:974-1006` `messages_and_intents_name_their_window` (windows, `main.rs:474-505, 1041-1062`); `library.rs:1012-1034` `the_session_is_kept_after_every_change` (`keep_session`, `keep_window`, `main.rs:1065-1088`). They are in `library.rs` because the `Test` harness is. `main.rs::program_tests` holds `the_tabs_at_start` (start-up), `each_setting_change_is_checked` (settings), `a_fetcher_is_given_the_proxy_and_the_local_addresses` (processes) and three broker tests. |

The `#[allow(…, reason = "a test")]` attribute is on thirteen test modules and absent from eight (`address`, `frames`, `hearing`, `links/tests`, `session`, `source`, `typing`, `main`); the moves keep each module's attribute as it is, since `arithmetic_side_effects` is not in `clippy.toml`'s test allowances and a module that lacks it compiles because it does no arithmetic.

## 3. The target layout

### 3.1 The shape, and three departures said up front

The library keeps its flat `src/*.rs` modules, each gaining a directory only for its tests and for the parts that are concepts of their own. The binary gains two modules at its root, `broker.rs` and `trusted_core.rs`, and `trusted_core/` holds one file per concern of the trusted core, each an `impl Core` block of its own, as `interface-core/src/browser/*_ui.rs` already does for `Browser`. `session.rs` becomes `session.rs` + `session/`.

| Departure | Reason |
|---|---|
| **The trusted core stays in the binary**, not in `lib.rs` as `00-conventions.md` section 2 asks for a binary's logic | The library is the fuzzed surface (`lib.rs:1-5`, `docs/hyperlinks-security.md:108`, requirement 3.2's spirit: parsers of outside input, no processes). Moving `Core` into it would make `Core`, `Event`, `Session`, the helper structs and the whole test harness `pub` across a crate boundary (every method documented for `missing_docs`, every private-field reach of section 2.2 turned into a method), for a test benefit the binary already has: its tests are in-crate (`library.rs`, `cookie_control.rs`, `hostile_tests.rs`). `main.rs` becomes the thin edge the convention wants (section 3.2); the logic sits one module down, in the same crate. |
| **The module is `trusted_core`, not `core`** | A module named `core` at the binary root would shadow the `core` crate in the root and make `core::mem::take` (`session.rs:601, 684-688, 705-709, 722, 860, 872`) and `core::array::from_fn` (`links.rs:470`) read as the local module wherever the root's scope reaches. The struct stays `Core`. |
| **The binary side of a library concept is named by the concept** (`trusted_core/cookies.rs` drives `neoteletext::cookies`), with `library.rs` the one two-concept parent | Siblings then agree: `cookies`, `links`, `typing`, `settings`, `console`, `updates` in `trusted_core/` mirror the library's modules, and inside each `use neoteletext::cookies::…` is an extern-crate path, never ambiguous with `crate::trusted_core::cookies`. History and bookmarks share one state struct, `Library` (`library.rs:73-96`), whose fields serve both panels; splitting the struct is a type change, not a move, so `library.rs` stays as the parent of `library/history.rs` and `library/bookmarks.rs`, named for the document that specifies both (`history-and-bookmarks.md`). |

### 3.2 The module tree after the work

Lines are estimates from the ranges in section 4; `T` is a `tests.rs` file.

```
src/
  lib.rs                      ~45   crate doc (rewritten to list every module), deny list, 16 pub mod + mod private_file
  main.rs                     ~70   deny list, windows_subsystem, mod broker/session/source/trusted_core, CORE_FLAG, fn core, fn main
  broker.rs                  ~175   the unconfined broker: VERSION_MARK, SECRET_FOLDERS, KEY_SERVICE, KEY_ACCOUNT, cookie_key,
                                    read_for_core, fn broker; installation, tell_launcher_healthy, launcher_state, updater_grant;
                                    three tests inline (31 lines)
  address.rs                 ~210   as today less its tests                                  address/tests.rs  ~100
  bookmarks.rs               ~465   types, name_of, bookmark_address, the tree, edits, import   bookmarks/file.rs ~160  T ~170
  calendar.rs                 162   unchanged
  console.rs                 ~185   the entries' ring and the texts                           console/tests.rs ~105
  cookies.rs                 ~435   the store, its text form, is_tag                         cookies/file.rs ~85   T ~200
  frames.rs                   121   unchanged (tests 64 lines, inline)
  hearing.rs                 ~135                                                            hearing/tests.rs ~95
  history.rs                 ~355   rows, the file, recording, expiry, removal               history/search.rs ~95  T ~175
  links.rs                   ~345   the per-image tables, Links, deciding, pointing, click/typed/fastext, overlap, carry_since
                                    links/target.rs ~140  links/destination.rs ~115  links/prompt.rs ~75  links/tests.rs 375
  outbox.rs                  ~160                                                            outbox/tests.rs ~90
  private_file.rs             ~30   private_options, write_whole (from history.rs)
  restore.rs                 ~330   (or session_file.rs, section 3.3)                        restore/tests.rs ~145
  settings.rs                ~310   the file, is_local, checked_address, folder             settings/proxy.rs ~50  T ~130
  sleep.rs                    162   unchanged
  source.rs                   147   unchanged
  start_page.rs              ~170                                                            start_page/tests.rs ~90
  typing.rs                  ~440                                                            typing/tests.rs ~245
  session.rs                 ~400   Session, constructors, the start page, tab navigation, closed tabs, mutes, move, close, views
  session/
    channel.rs               ~125   ChannelState and its impl
    tab.rs                   ~175   Visit, Pending, ClosedTab, Went, Tab and its list rules; without
    windows.rs               ~110   Window; the windows set aside
    saved.rs                 ~135   kept_history; saved, restore, remove_entries
    links.rs                  ~40   [links] Session::follow, Session::show_page, ChannelState::has_page
    tests.rs                 ~495
  trusted_core.rs            ~290   the constants; enum Event; struct Core; Core::new, now, send, send_untargeted,
                                    active_channel, broker, deliver; the mod tree below
  trusted_core/
    processes.rs             ~180   Decoder, Fetcher, Reach; spawn, stop_decoder, start_decoder, start_bookmark_reader,
                                    start_fetcher, read_interface; one test
    channels.rs              ~235   impl Core: tell, match_decoders, put_to_sleep, grow_decoder, stop_fetcher, decoder_ended,
                                    flush; one test and test_core
    timing.rs                ~110   impl Core: load, loading_wanted, next_wake, tick, typing_tick; one test
    windows.rs               ~290   Shown; impl Core: switch_window … tab_to_window, window_intent, keep_window, keep_session;
                                    two tests
    intents.rs               ~245   impl Core: intent, tab_intent, page_intent, opened, reload, went, send_all, send_mutes,
                                    send_tabs, open_start_page_bookmark, focused
    fetcher_messages.rs      ~150   impl Core: certificate_refused, fetched, console_fetched; one test
    decoder_messages.rs      ~100   impl Core: decoded
    strip.rs                  ~40   impl Core: strip, say, notice_tick
    console.rs                ~30   impl Core: log, note, send_console
    settings.rs              ~235   impl Core: settings_intent, send_settings, save_settings, change_setting; checked_change;
                                    one test
    sound.rs                  ~65   impl Core: tell_sound, sounding, start_sound
    updates.rs               ~350   Health, Updates and impl (the core's side); impl Core: send_update, update_intent,
                                    start_updater                                             updates/tests.rs ~85
    phone.rs                 ~120   [phone-keyboard] RELAY_VARIABLE; impl Core: send_phone, phone_panel, phone_said, phone_ended
    links.rs                 ~145   [links] impl Core: link, with_channel, links_of_image, redecide, redecide_channel, repoint,
                                    send_links_afresh, link_intent, follow, hand_off
    typing.rs                 ~70   [interaction] impl Core: input_intent, deliver_typing
    startup.rs               ~140   load_settings, load_bookmarks, load_history, load_session, open_at_start, open_home; one test
    run.rs                   ~200   handle, run, ended; one test
    numbers.rs                ~35   Numbers<T>
    library.rs               ~200   Manager, Library, shown_address, notice, depth_of; impl Core: library_intent, local_time,
                                    record_pending, record_drawn, record, expire_history, save_history, save_bookmarks, open_address
    library/history.rs       ~240   impl Core: history_request, send_history, suggest, open_suggestion, send_tab_list,
                                    remove_entries_of, go_to
    library/bookmarks.rs     ~380   impl Core: bookmarks_changed, bookmark_request, import_bookmarks, bookmarks_read,
                                    export_bookmarks, item_row, send_bookmarks, star, star_request, send_star, bar_request,
                                    bar_row, send_bar
    library/tests.rs         ~300   the nine library tests
    cookies.rs               ~275   Cookies; now_unix, site, mode, mode_view; impl Core: fetcher replies, the file, mode changes,
                                    private_cookies_closed, clear_cookies_since
    cookies/panel.rs         ~145   Row; impl Core: cookies_request, send_cookies
    cookies/tests.rs         ~210
    page_controls.rs          176   as today
    hostile_tests.rs          269   as today, imports changed
    test_support.rs           ~80   [test] Sink, Test and its helpers
tests/
  confined_core.rs, confined_keyboard.rs, latency.rs   unchanged
```

Two files are under 50 lines (`trusted_core/strip.rs`, `trusted_core/console.rs`); each is one concept and the alternative, folding `strip.rs` into `intents.rs` and `console.rs` into `fetcher_messages.rs`, would put the strip's notice and the console's feed where readers would not look. `session/links.rs` and `trusted_core/numbers.rs` are small for the same reason: a feature's code in a file of its own, a type in a file of its own. No file of code is over 500; the largest are `bookmarks.rs` (~465), `typing.rs` (~440) and `cookies.rs` (~435), each one concept, and the two test files `session/tests.rs` (~495) and `links/tests.rs` (375).

### 3.3 Public paths, all kept

Every path of section 1.4 is kept by a `pub use` in the parent file the item leaves, so no importer in `native/fuzz` or `tests/` changes:

| Parent | `pub use` |
|---|---|
| `links.rs` | `pub use target::{Target, parse_target, web_address}; pub use destination::{Channel, Destination};` |
| `cookies.rs` | `pub use file::{FILE_NAME, KEY_BYTES, load, open, remove, save, seal};` |
| `settings.rs` | `pub use proxy::Proxy;` |
| `session.rs` | `pub use channel::ChannelState; pub use tab::{ClosedTab, Pending, Tab, Visit, Went}; pub use windows::Window;` (crate-internal paths, kept for `trusted_core/*`) |
| `history.rs` | nothing moves out of it that was `pub` (`write_whole` and `private_options` are `pub(crate)` and move to `private_file.rs`; their three importers are updated in that step) |

One optional rename is offered to the owner and not assumed: `restore.rs` → `session_file.rs`, so that the session's file is named as the other kept files are and as the fuzz target already is. It changes `neoteletext::restore::` in `session.rs:20`, `main.rs:75` (after the moves, `trusted_core/startup.rs` and `trusted_core/windows.rs`), `library.rs:1014` (a test) and `fuzz/fuzz_targets/session_file.rs:7`; `lib.rs` would carry `pub mod session_file;` and no re-export, since a rename made for a name's sake with a compatibility alias would keep the misleading name alive.

### 3.4 Shared forms to extract, behaviour-neutrally

These are the only commits of the plan that are not pure moves. Each replaces copies with one function whose body is one of the copies, in a commit of its own after the moves (section 4, steps 48-51), so that the move diffs stay moves.

| Form | Where it lives | Signature (the body is today's code) | Callers replaced |
|---|---|---|---|
| The reader thread | `trusted_core/processes.rs` | `fn relay<M: Send + 'static>(output: ChildStdout, read: fn(&mut BufReader<ChildStdout>) -> io::Result<Option<M>>, events: Sender<Event>, said: impl Fn(M) -> Event + Send + 'static, ended: impl FnOnce(Option<String>) -> Event + Send + 'static)` | `start_decoder` (`main.rs:183-197`), `start_fetcher` (`252-266`), `read_interface` (`273-287`), `start_sound` (`1575-1589`), `phone_panel` (`1838-1852`). Not the updater's (`updates.rs:215-229`): `update::wire::read_from_updater` returns `Result<M>` and ends on `UnexpectedEof`, a different shape in another crate. |
| Kill then wait | `trusted_core/processes.rs` | `fn end(helper: &mut Helper)` | `stop_decoder` (`main.rs:174-175`), `start_bookmark_reader` (`229-230`), `stop_fetcher` (`766-767`), `decoder_ended` (`1191-1192`), `phone_ended` (`1893-1894`), `run`'s shutdown (`2320-2321`, `2330-2331`), `Updates::stop` (`updates.rs:238-239`). The fetcher's close (`763-767` and `2318-2321`) becomes `stop_fetcher` called from `run`. |
| A kept file's `load` | `private_file.rs` | `pub(crate) fn read_text(path: &Path, max: usize) -> io::Result<Read>` with `enum Read { Missing, TooLong, Text(String) }`: `metadata`, `NotFound` → `Missing`, over `max` → `TooLong`, else `read` and `from_utf8_lossy`. The callers keep their own sentences, since each turns a missing file into its default and an oversize one into a dropped line, never into an error | `Bookmarks::load` (`bookmarks.rs:591-603`), `History::load` (`history.rs:390-402`), `Settings::load` (`settings.rs:299-311`, after `update::profile::prepare`), `Saved::load` (`restore.rs:305-318`). `cookies::load` (`503-513`) reads bytes under a different bound and returns them whole; it stays. |
| Seconds since 1970 | `calendar.rs` (`utc_now`, `12-14`, exists) | callers use it; the two `u64` sites take `u64::try_from(utc_now()).unwrap_or(0)` | `library.rs:145` (identical closure), `cookie_control.rs:54-56` (`now_unix`), `main.rs:2026` (`hand_off`) |

The other duplicates of section 2.4 (3, 4, 7, 9-13, 15-18) are listed for the owner in section 6; they are either behaviour-bearing (the decoder replay, the cookie mode mapping) or small enough that a shared form would be longer than the copies.

## 4. The moves

Every step is one commit that passes `scripts/check.sh commit` (formatting, Clippy in all five feature shapes, the no-panic list, the tests), staged whole with `git add -A native/core` so that the gate's unstaged-sibling check does not refuse it. Steps 1 to 16 are in the library, 17 to 22 in `session.rs`, 23 to 47 in the trusted core, 48 to 51 the shared forms of section 3.4, 52 the documents. The order is leaves first: nothing moved in a later step is a parent of anything moved earlier. Where a step uses `git mv`, the diff is a rename plus the listed edits; where it splits a file, `git diff --color-moved=dimmed-zebra` shows the moved body. Each new file is assembled in the order of `00-conventions.md` section 7 (doc, `use`, constants, types, construction, behaviour, free functions, tests) and begins with a doc comment of a sentence naming the concept and the document section it follows.

### 4.1 The library

**Step 1. `private_file.rs`.** Move `private_options` and `write_whole` (`history.rs:453-475`, with their doc comments) to `src/private_file.rs`; `lib.rs` gains `mod private_file;` (not `pub`: the fuzz targets do not read it). Visibility stays `pub(crate)`. Imports: `bookmarks.rs:10`, `restore.rs:13`, `cookies.rs:494` change `crate::history::write_whole` to `crate::private_file::write_whole`; `history.rs` adds `use crate::private_file::{private_options, write_whole};` for `save` (409-413) and `append` (420-429). No public path changes.

**Steps 2 to 6. `tests.rs` for five small files.** One commit each, in this order: `address` (210-308 → `address/tests.rs`), `console` (185-290), `hearing` (134-229), `outbox` (158-245), `start_page` (171-256). Each parent ends with `#[cfg(test)] mod tests;`; the module's `#[allow(…, reason = "a test")]` attribute, where it has one, moves with it as an inner `#![allow]` on the first line of `tests.rs` (as `links/tests.rs` would carry one). `use super::*;` resolves as before: a child sees its parent's private items. `calendar` (38), `frames` (64), `page_controls` (24), `sleep` (48) and `source` (37) keep their tests inline; `frames` is four lines over the convention's "about 60" and is left, since the file is 121 lines in all.

**Step 7. `history/search.rs` and `history/tests.rs`.** From `history.rs` move `query` (283-300), `has_address` (321-325), `completion` (338-357) and `suggest` (359-378) into `history/search.rs` as an `impl History` block, with `HOST_SEARCH` (438-440) and `SCHEMES` (37-38) beside them; `Row::bare` (130-133) moves too, as it serves completion alone, and stays private, since only `search.rs` calls it. Visibility: nothing changes; `History::rows` and `index` are private fields read by `search.rs`, visible to a child. Tests 477-649 → `history/tests.rs`. `history.rs` declares `mod search; #[cfg(test)] mod tests;`. Public paths kept: `query`, `completion`, `suggest`, `has_address` are `pub` methods of `History`, reached as before.

**Step 8. `cookies/file.rs` and `cookies/tests.rs`.** Move `FILE_NAME`, `TEMPORARY_NAME`, `SEALED_MAGIC`, `KEY_BYTES`, `NONCE_BYTES`, `MAX_SEALED`, `cipher`, `seal`, `open`, `save`, `load`, `remove` (`cookies.rs:442-524`) to `cookies/file.rs`; `is_tag` (526-528) stays in `cookies.rs` beside `import`, which calls it. `cookies.rs` declares `mod file; #[cfg(test)] mod tests;` and `pub use file::{FILE_NAME, KEY_BYTES, load, open, remove, save, seal};` so `cookie_control.rs`'s `kept::{save, load, open, remove, KEY_BYTES}` and `fuzz_targets/cookie_file.rs` are unchanged. `file.rs` imports `super::Store` (its `export` is `pub`) and `crate::private_file::write_whole`. Tests 530-725 → `cookies/tests.rs`.

**Step 9. `bookmarks/file.rs` and `bookmarks/tests.rs`.** Move `read` and `take` (`bookmarks.rs:139-216`) and `text`, `load`, `save`, `export` (569-629) into `bookmarks/file.rs` as an `impl Bookmarks` block, with `VERSION_LINE`, `FILE_NAME`, `TEMPORARY_NAME`, `EXPORT_PREFIX`, `EXPORT_SUFFIX`, `MAX_EXPORTS_A_DAY`, `MAX_LINE`, `MAX_FILE` and its two `const _` asserts (14-21, 29-35). `take` calls `new_id`, `insert`, `depth`, `len`, `is_folder` and reads `items`: private items of the parent, visible to the child; `bookmark_address` is `pub`. `MAX_FILE` is `pub` and imported by `library.rs:595, 601` as `neoteletext::bookmarks::MAX_FILE`: `bookmarks.rs` re-exports it with `pub use file::MAX_FILE;` (the one re-export this step needs). Tests 632-800 → `bookmarks/tests.rs`; the test `the_file_is_read_strictly` names `VERSION_LINE` and `MAX_DEPTH` through `use super::*` and needs `use super::file::VERSION_LINE` after the move, or `file.rs` makes `VERSION_LINE` `pub(super)` — the latter, one line. `bookmarks.rs` declares `mod file; #[cfg(test)] mod tests;`.

**Step 10. `links/target.rs`.** Move `Target`, `parse_target`, `page`, `subpage`, `name`, `web_scheme`, `channel_address`, `uri_character`, `web_address` (`links.rs:62-196`) with `PAGE_DIGITS`, `SUBPAGE_DIGITS`, `HEXADECIMAL`, `HTTPS`, `HTTP`, `SCHEME_SEPARATOR`, `WEB`, `MAX_WEB` (43-58). Visibility: `page`, `name`, `channel_address` become `pub(super)` (called by `links.rs`'s `descriptor` 489-494 and by step 11's `destination.rs`); `HTTPS` → `pub(super)` (`follow`, 708). `links.rs` declares `mod target;` and `pub use target::{Target, parse_target, web_address};` so `fuzz_targets/link_target.rs` is unchanged. `links/tests.rs` keeps `use super::*` and sees the re-exports; it also names `MAX_TARGET` and `MAX_SERVICE_NAME`, which come from `protocol::links` in the parent's `use` and stay there.

**Step 11. `links/destination.rs`.** Move `Destination` and its impl, `Channel<'a>` and `own_page`, `Descriptor` and `resolve` (`links.rs:198-305`) with `INITIAL_PAGE` and `PAGE_FILES` (46-48, 59-60). Visibility: `Descriptor`, its fields `aliases`, `services`, `by_place`, and `resolve` → `pub(super)` (read by `decide`, `decide_fastext`, `typed`, `descriptor`, `aliases` in `links.rs` and by two tests); `INITIAL_PAGE` → `pub(super)` (`links/tests.rs:123`). `links.rs` adds `mod destination;` and `pub use destination::{Channel, Destination};`; `links/tests.rs` adds `use super::destination::{Descriptor, INITIAL_PAGE};` (the one test edit, noted in the message).

**Step 12. `links/prompt.rs`.** Move `Asking` (377-382) and `follow`, `prompt`, `confirm`, `cancel`, `forget_prompt` (697-767) as an `impl Links` block; `Links`'s fields `asking`, `next_prompt`, `last_handoff`, `unfocused` are private and visible to the child; `Asking` → `pub(super)` (a field type of `Links`). `PROMPT_DELAY_MILLISECONDS` and `HANDOFF_INTERVAL_MILLISECONDS` (29-34) are `pub` and move with their users, re-exported with `pub use prompt::{HANDOFF_INTERVAL_MILLISECONDS, PROMPT_DELAY_MILLISECONDS};` (the tests name them). After steps 10-12 `links.rs` is about 345 lines.

**Step 13. `typing/tests.rs`.** Move `typing.rs:438-679`. The five `include_str!` paths of `no_input_code_logs` (648-656) gain one `../`: `include_str!("../typing.rs")` and `include_str!("../../../interface-core/src/browser/terminal_ui.rs")` and so on; the message notes the five edited lines. The test's assertion that `typing.rs` contains no print call is unchanged in meaning and now scans a file that does not contain the test's own spelled-out strings.

**Step 14. `restore/tests.rs`.** Move `restore.rs:330-470`. `TEMPORARY_NAME`, `VERSION_LINE`, `FILE_NAME` are named by the tests through `use super::*` and are private constants of the parent, visible to the child. If the owner takes the rename of section 3.3, it is this step's commit, with the four importers listed there.

**Step 15. `settings/proxy.rs` and `settings/tests.rs`.** Move `Proxy` and its impl (`settings.rs:48-96`) to `settings/proxy.rs`; `Proxy::line` is private and called by `Settings::text` (272) → `pub(super)`. `settings.rs` declares `mod proxy; #[cfg(test)] mod tests;` and `pub use proxy::Proxy;`. Tests 357-483 → `settings/tests.rs`.

**Step 16. `lib.rs`'s doc comment** is rewritten to list every module (section 6 notes it is out of date); five lines, in the commit that ends the library's steps. No code moves.

### 4.2 The session

**Step 17. `session/tests.rs`.** Move `session.rs:966-1460`; `session.rs` declares `#[cfg(test)] mod tests;`. `Session::new` (cfg test) and `Visit::host_is` (cfg test) are seen by the child. No visibility change.

**Step 18. `session/channel.rs`.** Move `ChannelState` and its impl (`session.rs:23-141`) less `has_page` (104-108, step 22). `ChannelState::new` and `with` are private and called by `Session::channel_for` (379) → `new` becomes `pub(super)`. `session.rs` declares `mod channel;` and `pub use channel::ChannelState;` (the path `crate::session::ChannelState` is not used outside, but `Tab.channel`'s type must stay nameable from `trusted_core/*`).

**Step 19. `session/tab.rs`.** Move `Visit`, `Pending`, `ClosedTab`, `Went`, `Tab` and `impl Tab` (143-272) and `without` (312-328). `Visit::new`, `Tab::push`, `Tab::next_chapter_stop`, `without` → `pub(super)`. `session.rs` adds `mod tab;` and `pub use tab::{ClosedTab, Pending, Tab, Visit, Went};`, which keeps `crate::session::{Session, Went}` (`main.rs:81`) and `crate::session::Visit` (`library.rs:453`).

**Step 20. `session/windows.rs`.** Move `Window` (199-207) and `window_count`, `window_ids`, `window_of`, `all_tabs`, `all_tabs_mut`, `switch_to`, `new_window`, `close_window`, `take_tab`, `put_tab` (644-752) as an `impl Session` block; `Session::next_window` is a private field, visible to the child; `keep_closed` (755-764) is called by `close_window` and stays in `session.rs` as `pub(super)`. `session.rs` adds `mod windows;` and `pub use windows::Window;`.

**Step 21. `session/saved.rs`.** Move `kept_history` (330-346) and `saved`, `restore`, `remove_entries` (766-879). `restore` calls `channel_for`, `new_window`, `close_window`, `switch_to`, `tab_count`; `channel_for` (376-380) → `pub(super)`; `next_closed` is a private field, visible. `session.rs` adds `mod saved;`. Named `saved`, not `restore`, so that `crate::session::saved` and `neoteletext::restore` are never read as one thing.

**Step 22. `session/links.rs`.** Move `Session::follow` (462-471), `Session::show_page` (486-497) and `ChannelState::has_page` (104-108) into one file declared `#[cfg(feature = "links")] mod links;`, two `impl` blocks; `visit` (473-481) and `is_shown` are called by `follow` → `visit` becomes `pub(super)`. The three per-item `#[cfg(feature = "links")]` attributes go; the test `a_link_within_the_channel_keeps_it_open_and_is_recorded_as_the_pages` keeps its `#[cfg]` in `session/tests.rs`. After this step `session.rs` is about 400 lines and carries no `cfg`.

### 4.3 The trusted core

**Step 23. The hoist.** One commit, because the root cannot see private fields of a struct defined in a child: every `impl Core` leaves `main.rs` together.

- Create `src/trusted_core.rs` with `main.rs:44-2349` verbatim (the `use` block through `ended`), less the broker's items that stay for step 24: `CORE_FLAG` (2353), and the block 2355-2438 (`VERSION_MARK`, `SECRET_FOLDERS`, `KEY_SERVICE`, `KEY_ACCOUNT`, `cookie_key`, `read_for_core`, `broker`) which stays in `main.rs` for now. `fn core` (2365-2370) stays in `main.rs` and calls `trusted_core::run`, which becomes `pub(crate)`. Both test modules (2452-2645) move into `trusted_core.rs` for this step; their homes come with steps 25-41.
- `git mv src/cookie_control.rs src/trusted_core/cookies.rs`, `git mv src/library.rs src/trusted_core/library.rs`, `git mv src/page_controls.rs src/trusted_core/page_controls.rs`, `git mv src/updates.rs src/trusted_core/updates.rs`, `git mv src/hostile_tests.rs src/trusted_core/hostile_tests.rs`. Their `mod` lines leave `main.rs` for `trusted_core.rs`: `mod cookies; #[cfg(test)] mod hostile_tests; mod library; mod page_controls; mod updates;`. `main.rs` keeps `mod broker;` (step 24; until then nothing), `mod session; mod source; mod trusted_core;`.
- Import edits, each a one-line change: `library.rs:21` and `page_controls.rs:13` `use crate::Core` → `use super::Core`; `library.rs:596` `crate::start_bookmark_reader` → `super::start_bookmark_reader`; `library.rs:868` `crate::WINDOW_STILL` → `super::WINDOW_STILL` (the constant moves with the hoist into `trusted_core.rs`); `cookies.rs:17-18` `use crate::Core; use crate::library::Numbers;` → `use super::Core; use super::library::Numbers;`; `updates.rs:25` `use crate::Event` → `use super::Event`; `hostile_tests.rs:24-25` `use crate::session::Session; use crate::{Bookmarks, Core, Outbox, Settings};` → `use crate::session::Session; use super::Core; use neoteletext::bookmarks::Bookmarks; use neoteletext::outbox::Outbox; use neoteletext::settings::Settings;`. The `cookie_control::` and `page_controls::` and `updates::` and `library::` paths inside the hoisted text (for example `cookie_control::Cookies` in the `Core` struct, `updates::Updates::of_broker` in `run`) become `cookies::Cookies`, `updates::Updates`, and so on; `main.rs`'s `use` of `updates::{tell_launcher_healthy, launcher_state, updater_grant}` in `broker()` (2432-2434) becomes `trusted_core::updates::…` with those three functions `pub(crate)` until step 24.
- Visibility: `Core`'s fields unchanged (every `impl Core` is now in `trusted_core.rs` or a child of it). `pub(crate)` on `log`, `others_stale`, `start_bookmark_reader` and the methods of `library.rs`, `cookies.rs`, `page_controls.rs` may stay for this step.
- Documents: the three that name `hostile_tests.rs` are in step 52.

After this step `main.rs` is about 170 lines (the doc, the deny list, `mod`s, `CORE_FLAG`, `core`, the broker's block, `main`) and `trusted_core.rs` about 2,300; the five feature shapes build without a `cfg` change.

**Step 24. `broker.rs`.** Move from `main.rs` the block 2355-2438 and `CORE_FLAG` (2353) to `src/broker.rs` with `pub(crate) fn broker` and `pub(crate) const CORE_FLAG`; from `trusted_core/updates.rs` move `installation`, `tell_launcher_healthy`, `launcher_state`, `updater_grant` (39-84) into `broker.rs` as private functions (only `Handlers` names them); move the three broker tests (`the_broker_carries_its_version`, `a_helper_program_has_this_platforms_file_name`, `the_broker_reads_no_secret_for_the_core`, 2536-2562 in the hoisted text) to an inline `mod tests` at the end of `broker.rs` (31 lines, under the convention's 60). `main.rs` declares `mod broker;` and `main` calls `broker::broker()`. `updates.rs` loses the imports only the broker's side used (`update::layout`, `update::platform::Platform`, `update::files`, `update::state::MAX_STATE`, `release_identity::PORT`, `UpdaterGrant`, `std::io::Write` for `stdout`): the `--no-default-features` Clippy run shows any left behind. `main.rs` is now about 70 lines: the thin edge.

**Steps 25 to 41. Peeling `trusted_core.rs`**, one file per commit, each an `impl Core` block (or free items) moved verbatim with its `use` lines and its tests, each declared with one `mod` line in `trusted_core.rs`. Line numbers are those of `main.rs` today; in the hoisted file they are offset by a constant the commit message gives.

| Step | File | What moves (items; `main.rs` lines) | Visibility and `mod` | Tests |
|---|---|---|---|---|
| 25 | `processes.rs` | `Decoder`, `Fetcher` (142-157); `spawn`, `stop_decoder`, `start_decoder`, `start_bookmark_reader`, `start_fetcher`, `read_interface` (159-289); `Reach` and `Reach::of` (291-304) | all `pub(super)` (`Core`'s fields are of these types; `channels.rs`, `sound.rs`, `phone.rs`, `run.rs` call the functions); `start_bookmark_reader` drops `pub(crate)` for `pub(super)`; `mod processes;` | `a_fetcher_is_given_the_proxy_and_the_local_addresses` (2524-2534), inline |
| 26 | `channels.rs` | `impl Core`: `tell` (651-660), `match_decoders` (662-719), `put_to_sleep` (721-733), `grow_decoder` (735-759), `stop_fetcher` (761-769), `decoder_ended` (1175-1196), `flush` (1403-1434) | none beyond `mod channels;`; `put_to_sleep` and `flush` keep their `cfg(feature)` statements (they touch `links`, `typing`, `phone`: items used by two features stay in the ungated file) | `a_decoder_that_stops_reading_is_killed_and_forgotten` (2612-2644) with `test_core` (2585-2590), in a `#[cfg(all(test, unix))] mod tests` as today |
| 27 | `timing.rs` | `impl Core`: `load` (1153-1173), `loading_wanted` (1436-1446), `next_wake` (1448-1469), `tick` (1508-1532), `typing_tick` (441-451, with its `cfg_attr`) | `mod timing;`; `LOAD_INTERVAL`, `SLEEP_CHECK`, `CHUNK_BYTES` stay in `trusted_core.rs` (used by `Core::new` and here) | `the_core_wakes_only_for_work_it_has` (2592-2610) |
| 28 | `windows.rs` | `Shown` (134-140); `impl Core`: `switch_window`, `park_shown`, `in_window_of`, `others_stale`, `refresh_if_stale`, `open_window`, `send_window_whole`, `close_window`, `tab_to_window` (489-639), `window_intent` (1039-1062), `keep_window`, `keep_session` (1064-1088) | `Shown` → `pub(super)` (a field type); `others_stale` drops `pub(crate)`; `mod windows;`; `WINDOW_STILL` stays in `trusted_core.rs` | from `library.rs`'s tests (step 45 moves them): `messages_and_intents_name_their_window`, `the_session_is_kept_after_every_change` |
| 29 | `intents.rs` | `impl Core`: `send_all`, `send_mutes`, `send_tabs` (871-925), `intent` (931-1037), `tab_intent`, `page_intent`, `opened`, `reload`, `went` (1090-1151), `open_start_page_bookmark` (1328-1336), `focused` (400-413, with its `cfg(any(…))` and `cfg_attr`) | `mod intents;`; the cross-feature `cfg` sites inside `intent`, `send_all`, `opened`, `went` stay as they are (one item, two forms) | none |
| 30 | `fetcher_messages.rs` | `impl Core`: `certificate_refused` (771-786), `fetched` (788-869), `console_fetched` (1355-1380) | `mod fetcher_messages;` | `a_refused_certificate_shows_until_the_contents_arrive` (step 45) |
| 31 | `decoder_messages.rs` | `impl Core`: `decoded` (1198-1290) | `mod decoder_messages;` | none |
| 32 | `strip.rs` | `impl Core`: `strip` (1296-1305), `say` (1338-1344), `notice_tick` (1346-1353) | `mod strip;`; `NOTICE_TIME` moves with `say` as a private constant | none |
| 33 | `console.rs` | `impl Core`: `log` (1382-1389, its doc comment cut to its own sentence), `note` (1391-1394), `send_console` (1396-1401) | `log` drops `pub(crate)`; `mod console;` | none |
| 34 | `settings.rs` | `impl Core`: `settings_intent` (1307-1326), `send_settings` (1596-1617), `save_settings` (1619-1627), `change_setting` (1629-1666); `checked_change` (1669-1758) | `checked_change` private (only `change_setting` and its test call it); `mod settings;` | `each_setting_change_is_checked` (2484-2522), inline (39 lines) |
| 35 | `sound.rs` | `impl Core`: `tell_sound` (1534-1540), `sounding` (1542-1554), `start_sound` (1561-1594) | `mod sound;` | none |
| 36 | `updates.rs` (exists) and `updates/tests.rs` | `impl Core`: `send_update` (1471-1488), `update_intent` (1490-1499), `start_updater` (1501-1506) into `trusted_core/updates.rs` after `impl Updates`; tests 396-480 of `updates.rs` → `updates/tests.rs` | none | the four `Updates` tests |
| 37 | `phone.rs` | `RELAY_VARIABLE` (84-88, one `#[cfg]` instead of two); `impl Core` 1791-1899 | `#[cfg(feature = "phone-keyboard")] mod phone;`; the per-item `cfg` inside goes; `Event::{Phone, PhoneEnded}`, `Core::{phone, phone_view}` and `handle`'s two arms keep theirs | none |
| 38 | `links.rs` | `impl Core` 1901-2038; the `use protocol::links::{LinkKind, Message as LinkMessage, Pointing, Spot}` and `use neoteletext::links::{Channel as LinkChannel, Follow, Links, Refusal}` lines that only it needs | `#[cfg(feature = "links")] mod links;`; `follow` is called by `page_controls.rs:101` and `intents.rs` (`Cell`) → `pub(super)`; the `Spot` import stays in `intents.rs` for `Cell` | none |
| 39 | `typing.rs` | `impl Core`: `input_intent` (415-439), `deliver_typing` (453-470) | `#[cfg(feature = "interaction")] mod typing;`; `deliver_typing` is called from `intents.rs`, `fetcher_messages.rs`, `decoder_messages.rs`, `timing.rs`, `channels.rs` under their own `cfg(feature = "interaction")` → `pub(super)` | none |
| 40 | `startup.rs` | `load_settings`, `load_bookmarks`, `load_history`, `load_session` (2098-2167); `open_at_start`, `open_home` (1760-1789) | all `pub(super)` (`run` calls the first five; `open_home` is called by `windows.rs` and `intents.rs`); `mod startup;` | `the_tabs_at_start` (2455-2482), inline |
| 41 | `run.rs` | `handle` (2169-2226), `run` (2228-2341), `ended` (2343-2349) | `run` stays `pub(crate)`; `mod run;` | `a_crashed_or_failed_interface_fails_the_browser` (2575-2584), inline under `cfg(all(test, unix))` |

After step 41 `trusted_core.rs` holds the constants (90-107 less those that moved), `Event`, `Core`, `Core::new` (2040-2096), `now`, `send`, `send_untargeted`, `active_channel`, `broker`, `deliver` (396-398, 474-487, 642-649, 927-929, 1556-1559) and the `mod` tree: about 290 lines.

**Step 42. `trusted_core/numbers.rs`.** Move `Numbers<T>`, its `Default` and its impl (`library.rs:30-61`) to `numbers.rs`; `pub(super) struct Numbers`, methods `pub(super)` (they were `pub(crate)`; only `library/*` and `cookies/*` use them). `trusted_core.rs` declares `mod numbers;`; `library.rs` and `cookies.rs` import `super::numbers::Numbers`.

**Step 43. `trusted_core/library/history.rs`.** Move `history_request`, `send_history`, `suggest`, `open_suggestion`, `send_tab_list`, `remove_entries_of`, `go_to` (`library.rs:245-482`) as an `impl Core` block. `shown_address`, `notice` (100-112) → `pub(super)`; `open_address`, `expire_history`, `save_history` are private `Core` methods defined in `library.rs`'s own `impl Core`; a private inherent method is visible in the module of its `impl` and that module's descendants, so `library/history.rs` sees them without change. `library.rs` declares `mod history;`.

**Step 44. `trusted_core/library/bookmarks.rs`.** Move `bookmarks_changed` through `send_bar` (`library.rs:484-861`). `Manager` (64-70) → `pub(super)` (a field type of `Library`, constructed in `bookmark_request`); `depth_of` (114-116) → `pub(super)`; `PLACE_SEPARATOR` moves with `item_row`. `library.rs` declares `mod bookmarks;` and is about 200 lines.

**Step 45. `trusted_core/test_support.rs` and `library/tests.rs`.** Move `Sink` and `Test` with `new`, `sent`, `last_history`, `last_bookmarks`, `visit` (`library.rs:878-944`) to `test_support.rs`, `pub(super)` items, declared `#[cfg(test)] mod test_support;` in `trusted_core.rs`; add to `Test` the `last_view`, `tab`, `set`, `ask` helpers of `cookies.rs`'s tests (443-480) and delete that file's `Sink`/`Test` (412-441), its tests importing `super::super::test_support::Test`. Move the nine library tests (1036-1244) to `library/tests.rs`; move `a_refused_certificate_shows_until_the_contents_arrive` (946-968) to an inline `mod tests` in `fetcher_messages.rs` and `messages_and_intents_name_their_window`, `the_session_is_kept_after_every_change` (970-1034) to one in `windows.rs` (64 lines together; under the ceiling for an inline module by a few lines, left inline because `windows.rs` has no other tests). `hostile_tests.rs` keeps its own `Sink` (44-55): it needs a sink without the harness, and a test module is allowed its fixture.

**Step 46. `trusted_core/cookies/panel.rs` and `cookies/tests.rs`.** Move `Row` (27-32) and `cookies_request`, `send_cookies` (266-396) from `trusted_core/cookies.rs` to `cookies/panel.rs`; `Row` → `pub(super)`; `Cookies`'s private fields `numbers`, `panel_open`, `query`, `first`, `notice` are visible to the child. Tests (399-606, already using `test_support` from step 45) → `cookies/tests.rs`. `cookies.rs` declares `mod panel; #[cfg(test)] mod tests;`. `send_cookies` is called from `library/history.rs` (`ClearCookies`) and `intents.rs` → stays `pub(super)`.

**Step 47. `page_controls.rs`'s two `cfg` pairs.** Nothing moves; this step records that `page_controls.rs:95-104` and `129-132` stay as they are: `page_control`'s Fastext arm and `send_controls`'s `fastext` field are one item with two forms, which `00-conventions.md` section 3 allows. (Listed so that the step numbers of section 3.4 hold.)

### 4.4 The shared forms (section 3.4), after the moves

**Step 48.** `relay` in `processes.rs`; the five reader loops become calls. **Step 49.** `end` in `processes.rs`; eight kill-and-wait sites become calls; `run`'s fetcher shutdown calls `stop_fetcher`. **Step 50.** `private_file::read_text`; the four `load`s become calls that keep their own sentences. **Step 51.** `calendar::utc_now` at the three other clock sites. Each commit's message says it is behaviour-neutral and names the sites.

### 4.5 The documents (phase B5 for this crate)

**Step 52.** `docs/architecture.md` section 14's `core/` entry is rewritten from section 3.2; `docs/requirements.md:177`, `docs/architecture.md:702`, `docs/security-analysis.md:391` change `native/core/src/hostile_tests.rs` to `native/core/src/trusted_core/hostile_tests.rs`; `docs/architecture.md:130` and `docs/installation-and-updates.md:6` change `core/src/updates.rs` to `core/src/trusted_core/updates.rs` and `core/src/broker.rs`; `docs/hyperlinks.md:76` (`core/src/main.rs` "only logs" a click, already stale) names `trusted_core/links.rs`; `src/settings.rs:5`'s mention of `bookmarks.rs` and `lib.rs:5`'s of `main.rs` are checked. Paths that do not move and whose mentions stand: `outbox.rs` (`architecture.md:103, 285`; `security-analysis.md:160, 301`), `address.rs` (`architecture.md:508`; `hyperlinks.md:168`; `hyperlinks-security.md:108`), `source.rs` (`requirements.md:518`; `sandboxing.md:97`; `confine/src/broker.rs:39`), `settings.rs` (`history-and-bookmarks.md:446`), `console.rs` and `typing.rs` (`requirements.md:128`), `hearing.rs` (`security-analysis.md:167`).

## 5. Risks particular to this crate

| Risk | Where it bites | How the steps meet it |
|---|---|---|
| **The 56 `cfg` sites of `main.rs`** | Steps 23 and 25-41. Putting the links, typing and phone glue in gated modules removes the per-item `cfg` inside those blocks, but the cross-feature sites stay in `Core` (fields), `Core::new`, `intent`, `decoded`, `fetched`, `send_all`, `put_to_sleep`, `flush`, `loading_wanted`, `opened`, `went`, `focused` (`cfg(any(links, interaction))` with a `cfg_attr(allow(unnecessary_wraps))`), `typing_tick` (its `cfg_attr`), `page_control`, `send_controls`; `session.rs` has five and keeps one test's. A `use` left in a file whose only user was gated becomes `unused_imports` under `--no-default-features`, and the gate makes it an error | Every step builds the five shapes before its commit (`scripts/check.sh commit` runs all five Clippy passes); a step that moves a gated caller moves the imports only it needs, and `cargo clippy --no-default-features` on the crate alone (`scripts/try.sh neoteletext` does not; the commit gate does) is run after each peel |
| **Private `use` re-exports** | `hostile_tests.rs:25` imports `crate::{Bookmarks, Core, Outbox, Settings}` through `main.rs`'s private `use` lines (67, 74, 76); `library.rs:868-872` and `cookie_control.rs:403-406` tests import `crate::session::Session`, `crate::WINDOW_STILL`, and the lib's types by their own paths | Step 23 rewrites the three files' imports to the library's paths and `super::`; the commit message lists them |
| **Privacy of `Core`, `Session`, `Links`** | An `impl` block placed outside a descendant of the defining module cannot read private fields (section 2.2); the hoist must move every `impl Core` in one commit; `Core::new` is private and called by `hostile_tests` and `test_support` | Steps 23, 17-22 and 10-12 keep every `impl` in a child of the defining file; the `pub(super)` items are listed per step (none are fields) |
| **Fuzz paths** | `native/fuzz` builds the library on nightly in the full gate with the nine paths of section 1.4 | Steps 8, 10, 11, 15 add the `pub use` lines before the item leaves; no fuzz target changes unless the owner takes the `restore` → `session_file` rename (section 3.3), which changes `fuzz_targets/session_file.rs:7` in step 14's commit |
| **`include_str!` paths** | `typing.rs:648-656`: five paths relative to the file holding the macro | Step 13 adds one `../` to each and says so in its message; the test's meaning is unchanged |
| **Documents naming paths** | `hostile_tests.rs` (three documents), `updates.rs` (two), `main.rs` (`hyperlinks.md:76`), `architecture.md` section 14 | Step 52, one commit, from the final tree; the stale mention in `hyperlinks.md:76` is corrected in the same commit |
| **Pedantic lints** | `unused_qualifications` once a name is imported (`library.rs:453` writes `crate::session::Visit` in full); `missing_docs` for any item that becomes `pub` (only the re-exports, which carry their docs); `dead_code` if a copy of `Sink`/`test_core` is left unused after step 45; `too_many_lines` is not approached (no function gains lines); `module_name_repetitions` is no longer pedantic on 1.99 | The gate's Clippy run; each step's import edits are the only non-moved lines and are read for these |
| **`cargo fmt`** | New `use` blocks and `pub use` lists at 160 columns with `use_small_heuristics = "Max"` | `cargo fmt` before each commit; if it reorders moved code, the move's diff is read with `--color-moved` |
| **Commit-gate staging** | The gate refuses a staged set that has unstaged or untracked siblings under `native/`; a `git mv` plus edits must be staged whole; with nothing staged the gate runs nothing and reports success | `git add -A native/core` (and `docs/` in step 52) before `scripts/check.sh commit`, then `git status` shows nothing unstaged |
| **Git blame** | Whole-file moves keep blame (`git mv` in step 23); the peels of steps 25-46 lose it for the moved ranges whatever the method | The hoist is its own commit so that the largest move stays attributable; the peels' messages name the source ranges |
| **Behaviour that must not change while moving** | `cookies.rs`'s `answer` flushes a fetcher's pipe synchronously (a fetcher blocks on the answer); `keep_session` at the end of `intent` and `window_intent`; `flush`'s replacement of a stuck decoder; the order of `send_window_whole`'s sends; the first `ToInterface::Window` write before any other (`run`, 2249-2256) | Each moves verbatim; the behaviour-neutral steps 48-51 touch none of them, and steps 48 and 49 replace loops and kill-wait pairs whose bodies are the function's body |
| **Two test modules named `tests` in one file** | `main.rs` has `program_tests` and `tests` (cfg unix); after the peels each file has at most one | Steps 25-41 place each test with its concept |

## 6. Seen, not part of this plan

Defects and oddities noticed in the reading; none is a placement, and none is changed by the steps above (`30-cross-cutting.md` section 5 collects them across the repositories).

- **Constants restated against the engine's and the interface core's** (requirement 2.4; `00-conventions.md` section 8): `PACKET_BYTES = 42` at `main.rs:95` beside `neoteletext_core::consts::PACKET_BYTES`, which `console.rs:11` imports; `COLUMNS = 40` at `start_page.rs:30` and `PAGE_COLUMNS = 40` at `typing.rs:36` beside `interface_core::canvas::COLUMNS`, which `links.rs:14` imports; `STREAM_HELD_SAMPLES = 48_000 * 2` at `hearing.rs:22` with the sample rate as a literal; `MAX_TABS` at `restore.rs:21` and `session.rs:279`, both `protocol::MAX_TABS`; `MAX_WINDOWS` at `restore.rs:23` beside direct uses of `interface_core::library::MAX_WINDOWS`; `PAGE_DIGITS`, `SUBPAGE_DIGITS`, `HEXADECIMAL` at `address.rs:67-69` and `links.rs:51-53`, with `fragment_page` and `links::page` implementing the same rule.
- **A doc comment on the wrong item**: `session.rs:895-897` describes `close` and sits above `move_tab` (897-899); `main.rs:1382-1385` is `send_console`'s sentence glued to `log`'s.
- **`lib.rs:1-5`** lists seven of the fifteen modules; **`main.rs:84-88`** writes `#[cfg(feature = "phone-keyboard")]` twice on one constant.
- **`settings.rs:319-336`** is a private copy of `history::write_whole` with its own `mode(0o600)`; a one-line change makes it call `write_whole` (`private_file::write_whole` after step 1). Behaviour identical; left for the owner because it is not a move.
- **The duplicates of section 2.4 not taken up by steps 48-51**: the decoder started and given what was kept (`main.rs:687-694`, `749-757`); the parked window's three assignments (`500-503`, `582-585`); the four `load_*` (`2100-2167`); `ToSound::Settings` built twice (`1592`, `1599`); the clear range mapped twice (`library.rs:300-307`, `322-329`); three `FolderRow` builders (`686-696`, `700-708`, `799-809`); `item_row` and `bar_row` (`653-674`, `837-846`); the cookie mode mapped in `cookie_control.rs:66-72` and inline at `main.rs:1744-1748` (`change_setting` could pass `mode(new)`); the scheme lists (`address.rs:172-178`, `links.rs:55-57`, `history.rs:38`); the `NotFound` arm's sentence five times (section 2.4 item 18).
- **`cookie_control.rs:91-96` (`answer`)** flushes a fetcher's outbox outside `Core::flush`; by design, since the fetcher waits, but it is the one exception to decision 53's "once per event" and is undocumented at the site.
- **`session.rs:342`** writes to standard error from a library-shaped function (`kept_history`), the one `eprintln!` in `session.rs`; `updates.rs` has five and `library.rs:149` one; the console's Log tab does not see them (decision 70 routes logs through `Core::log`).
- **`hostile_tests.rs` is named by path in three documents**; any later rename of the harness file needs the same three edits as step 52.
- **`typing.rs`'s `no_input_code_logs`** scans five source files for print calls by `include_str!`; after step 13 the list of files is in `typing/tests.rs`, where a file added to the input path (`trusted_core/typing.rs`, which handles intents) is not scanned. Whether the test should cover the binary's typing glue is a question for the owner, not a placement.
