# 22. The browser's protocol and its processes

| | |
|---|---|
| **Crates** | `protocol`, `decoder`, `fetcher`, `interface`, `draw-vello`, `draw-embedded`, `dock-menu`, `keyboard`, `sound` (all under `native/`) |
| **Rests on** | Every file of the nine crates read in full at browser `494aa91` (23 October 2026); `docs/architecture.md` sections 6 and 14; `DEVELOPMENT.md` section 6; `scripts/check.sh`; `native/clippy.toml`; the fuzz targets and `core`'s tests that import these crates. |
| **Phases** | `protocol` is B1; the processes and the drawing back ends are B3 (`01-method-and-order.md` section 2). |
| **Measure** | `00-conventions.md`. Where a step departs from it, the step says so and why. |

## 1. The crates as they are

### 1.1 `protocol` (library, 6,955 lines in 14 files)

Every message between the browser's processes: the engine's framing (kind byte, 32-bit big-endian length, payload, at most `MAX_PAYLOAD` of 256 KB), the bounds, the kinds, the strict readers and `clean()` for untrusted text (`architecture.md` section 6.4). Root `src/lib.rs` is in `NO_PANIC_ROOTS`.

| Feature | Turns on |
|---|---|
| `links` (default) | `interface-core/links`; the link messages |
| `interaction` (default) | `neoteletext-input`, `interface-core/interaction`; typing |
| `phone-keyboard` (default) | `interaction`, `interface-core/phone-keyboard`; the phone keyboard |

| File | Lines | Gate | Pipe |
|---|---|---|---|
| `lib.rs` | 1622 | — | root; core ↔ interface: `ToInterface`, `ToCore`, framing, `Fields`, `clean` |
| `library.rs` | 792 | — | history, bookmarks, star, bar, suggestions, tab list, window geometry |
| `decoder.rs` | 757 | — | core ↔ decoder; the frame writer; bookmark import |
| `links.rs` | 669 | `links` | link messages on three pipes |
| `fetcher.rs` | 645 | — | core ↔ fetcher; cookie questions |
| `interaction.rs` | 506 | `interaction` | intents, `Typing`, `check_message` |
| `keyboard.rs` | 387 | `phone-keyboard` | core ↔ keyboard process; `PhoneView`, `PhoneKey` |
| `audio.rs` | 387 | — | one voice-operation payload on two pipes |
| `frame.rs` | 330 | — | page image: raw, runs, changes |
| `settings.rs` | 320 | — | settings view, change, update, remote |
| `sound.rs` | 180 | — | core ↔ sound helper |
| `cookies.rs` | 154 | — | cookies panel |
| `controls.rs` | 114 | — (private) | page controls |
| `console.rs` | 92 | — | console update |

Every file but `lib.rs` is a leaf reaching the root's private helpers through `use super::{Fields, ProtocolError, push_text, …}`.

Public paths and their importers (from `grep` over `native/`; `core` is the trusted core, `fuzz` the fuzz workspace):

| Path | Importers |
|---|---|
| `protocol::{clean, MAX_ADDRESS, MAX_TITLE, MAX_TABS, MAX_PAGE_TITLE, MAX_STRIP_NOTICE, FIRST_WINDOW, NEW_WINDOW, ProtocolError, ToInterface, ToCore}` | `core/src/*` (22 files), `interface/src/main.rs`, `decoder/src/{main,netscape}.rs` |
| `protocol::{read_from_core, read_from_interface, write_to_core, write_to_interface}` | `core/src/{main,hostile_tests}.rs`, `interface/src/main.rs`, `fuzz/fuzz_targets/{core_messages,interface_messages}.rs` |
| `protocol::{problem_code, problem_of}` | crate-internal (`fetcher.rs`), `core` |
| `protocol::decoder::{ToDecoder, FromDecoder, View, BookmarkEntry, read_from_core, read_from_decoder, write_to_decoder, write_to_core, write_frame_to_core, is_netscape_bookmarks, FIRST_STORE_PAGES, MAX_STORE_PAGES, MAX_CHANNEL_LOG, MAX_BOOKMARK_FILE, MAX_BOOKMARK_ENTRIES, MAX_BOOKMARK_NAME, MAX_COLOURS}` | `core`, `decoder/src/{lib,main,netscape}.rs`, `decoder/tests/confined_bookmarks.rs`, `fuzz/{decoder_messages,decoder_requests,netscape_file}.rs` |
| `protocol::fetcher::{FromFetcher, ToFetcher, Entry, Origin, CookieSite, CertificateProblem, read_from_fetcher, read_to_fetcher, write_to_core, write_to_fetcher, MAX_NOTICE, MAX_SET_COOKIE, MAX_COOKIE_HEADER, MAX_EXCHANGE_URL}` | `core`, `core/tests/latency.rs`, `core/src/hostile_tests.rs`, `fetcher/src/{main,cookies,transport}.rs`, `fuzz/{fetcher_messages,fetcher_commands}.rs` |
| `protocol::frame::{decode, encode, base, PAGE_DOTS, FrameError, Image, MAX_IMAGE, MAX_COLOURS}` | `core/src/frames.rs`, `core/tests/latency.rs`, `interface/src/main.rs`, `fuzz/page_image.rs` |
| `protocol::keyboard::{FromKeyboard, ToKeyboard, PhoneState, PhoneView, PhoneKey, Qr, read_from_keyboard, read_to_keyboard, write_to_core, write_to_keyboard, MAX_KEY_NAME, MAX_PHONE_TEXT, MAX_QR_SIZE}` | `core`, `core/tests/confined_keyboard.rs`, `keyboard/src/keyboard.rs`, `interface/src/main.rs`, `fuzz/phone_keys.rs` |
| `protocol::sound::{ToSound, FromSound, read_to_sound, read_from_sound, write_to_sound, write_from_sound}` | `core`, `sound/src/main.rs`, `sound/tests/confined.rs`, `fuzz/{sound_messages,sound_requests}.rs` |
| `protocol::audio::{Audio, Sound, MAX_MESSAGE_SAMPLES}` | `core`, `decoder/src/lib.rs`, `sound/src/{audio,main}.rs`, `sound/tests/confined.rs` |
| `protocol::links::{Message, Spot, Candidate, Found, NumberLink, Alias, Service, Fastext, FastextTarget, LinkKind, Pointing, MAX_*}` | `core`, `decoder/src/{lib,links}.rs`, `fetcher/src/main.rs`, `interface/src/main.rs` |
| `protocol::interaction::{Intent, InputIntent, CursorState, Typing}` | `core`, `interface/src/main.rs` |
| `protocol::{library, settings, cookies, console}::*` | `core`, `interface/src/main.rs` (`console::Level` also `decoder/src/lib.rs`) |

### 1.2 `decoder` (package `neoteletext-decoder`: library `decoder` and binary; 2,530 lines)

The engine as the decoder process uses it: one channel's pages, rendering, the audio receiver, link finding, the Netscape bookmark reader. Roots `src/lib.rs` (1572) and `src/main.rs` (283), both in `NO_PANIC_ROOTS`. Features `links` and `interaction` (default), each forwarding to `protocol` and `interface-core`; `interaction` adds `neoteletext-input`.

| File | Lines | Holds |
|---|---|---|
| `lib.rs` | 1572 | `Engine`, `Rendered`, `Flashing`, the audio sink, input records, page-file lines, titles, `sample`, 502 lines of tests |
| `netscape.rs` | 421 | the bookmark file reader |
| `links.rs` | 254 (`links`) | link finding in a page |
| `main.rs` | 283 | the process: arguments, the loop, the frame cache |
| `tests/confined_bookmarks.rs` | 59 | the binary under `confine` |

Public paths: `decoder::{Engine, Rendered, Exported, Found, Changed, Flashing, FlashRates, InputRecords, ChannelLog}`, `decoder::netscape::{read, Found, NotRead}`, `decoder::sample::tti`, `decoder::links::{Lines, LinkLines, find}`. Importers: `decoder/src/main.rs` (`Engine`, `Flashing`, `Rendered`, `netscape::read`), `draw-vello/src/lib.rs` and `examples/write_window.rs` (`Engine`, `sample::tti`), `draw-embedded/examples/write_screen.rs` and `tests/memory_display.rs` (same), `core` (`Engine`, `sample::tti` in tests), `fuzz/{engine,netscape_file}.rs`.

### 1.3 `fetcher` (package `neoteletext-fetcher`: binary only; 1,294 lines)

The engine's user agent over real sockets; one channel's network. Root `src/main.rs` (515) in `NO_PANIC_ROOTS`; private modules `transport.rs` (642) and `cookies.rs` (137). Features `links` (adds `interface-core`) and `interaction`. No library target, so nothing is importable; no fuzz target reaches its code.

### 1.4 `interface` (package `neoteletext-interface`: library and binary; 1,778 lines)

The window: winit and softbuffer, the interface core drawn by `draw-vello`, the translation of input, the reader thread. Roots `src/lib.rs` (20) and `src/main.rs` (1544), both in `NO_PANIC_ROOTS`. The library holds only `keys.rs` (214, `interaction`), imported by the binary as `neoteletext_interface::keys`. Features `links`, `interaction`, `phone-keyboard` (default), forwarded to `protocol` and `interface-core`.

### 1.5 `draw-vello` (library; 1,123 lines, example 106)

The `Canvas` back end on the processor: `vello_cpu` and Parley, damage-limited redraw. `lib.rs` (890) and `damage.rs` (233). Not a no-panic root. Dev-dependency on `decoder` for its tests and example. Public: `draw_vello::{Painter, Family, PageError, Damage, DeviceBox, MAX_BOXES}`; importers `interface/src/main.rs`, its own example.

### 1.6 `draw-embedded` (library, `no_std`; 233 lines, example 87, test 105)

`Canvas` over `embedded-graphics`. One file; `Screen<D>`, `PageError`. Importers: its example and test.

### 1.7 `dock-menu` (library; 647 lines)

The macOS Dock menu and menu bar (decisions 39, 84). `lib.rs` (354: platform-neutral types, the `MENU_BAR` table, no-op fallbacks) and `mac.rs` (293: every `unsafe` block, under `#![expect(unsafe_code, reason)]`). Lints are the workspace's with `unsafe_code = "deny"` and `undocumented_unsafe_blocks`. Importer: `interface/src/main.rs`.

### 1.8 `keyboard` (package `neoteletext-keyboard`: binary; 233 lines)

`main.rs` (41, root) and `keyboard.rs` (192, `phone-keyboard`). No library.

### 1.9 `sound` (package `neoteletext-sound`: library `sound` and binary; 672 lines, test 63)

`lib.rs` (15, root) with `audio.rs` (529); `main.rs` (128, root); `tests/confined.rs` (ignored, needs a device). Public: `sound::audio::{Mixers, Shared, Speaker, OutputSample, apply, watch, set_sound, render}`; importer `sound/src/main.rs`.

### 1.10 Dependencies between the nine

```
protocol ─► interface-core
decoder ─► protocol, interface-core          (dev: engine's encoders)
fetcher ─► protocol, [interface-core with links]
interface ─► protocol, interface-core, draw-vello, dock-menu
draw-vello ─► interface-core                  (dev: decoder)
draw-embedded ─► interface-core               (dev: decoder)
keyboard ─► protocol
sound ─► protocol
dock-menu ─► nothing in the workspace
```

### 1.11 The numbers before the work

| | files | largest | over 500 | functions over 80 lines | `impl` over 300 | test lines inline |
|---|---|---|---|---|---|---|
| `protocol` | 14 | 1622 | 5 (1622, 792, 757, 669, 645) | 4 (182, 172, 136, 99) | 0 | 1,497 |
| `decoder` | 5 | 1572 | 1 | 1 (`run`, 102) | 1 (`impl Engine`, 452) | 641 |
| `fetcher` | 3 | 642 | 2 (642, 515) | 1 (`run`, 120) | 0 | 352 |
| `interface` | 3 | 1544 | 1 | 3 (118, 106, 93) | 2 (667, 316) | 93 |
| `draw-vello` | 3 | 890 | 1 | 0 | 0 | 236 |
| `draw-embedded`, `dock-menu`, `keyboard`, `sound` | 9 | 529 | 1 (`sound/audio.rs`) | 1 (`keyboard::run`, 85) | 0 | 273 |

## 2. Findings

### 2.1 `protocol/src/lib.rs` (1622)

The crate root and the whole core↔interface pipe in one file.

| Lines | Item |
|---|---|
| 8–20 | `#![deny(...)]` no-panic list |
| 22–37 | the fourteen `mod` declarations, three behind `cfg(feature)` |
| 49–76 | `pub const` bounds: `MAX_PAYLOAD`, `MAX_PAGES`, `FIRST_PAGE`, `LAST_PAGE`, `MAX_TITLE`, `MAX_IDENTITY`, `MAX_STRIP_NOTICE`, `MAX_ADDRESS`, `MAX_PAGE_TITLE`, `MAX_BANK_NAME`, `MAX_TAB_TITLE`, `MAX_TABS` |
| 78–98 | `KIND_*` core→interface: 2–6, 8–10, 40–44, 46, 47, 49 (40–42 gated) |
| 99–121 | `KIND_*` intents 16–30 (24–30 gated) |
| 122–134 | `KIND_*` strip input 32–39, 45 (36, 37 gated) |
| 135–165 | `KIND_*` views and requests 50–77 |
| 166–170 | `pub const NEW_WINDOW`, `FIRST_WINDOW` |
| 171–175 | `KIND_UPDATE_VIEW` 120, `KIND_DRAWN` 121, `KIND_INSTALL_UPDATE` 122 |
| 177–189 | strip flag bits and tab flag bits |
| 191–194 | `HEADER_BYTES`, `KEY_BYTES`, `FRAME_FIXED_BYTES`, `CELL_BYTES` |
| 196–296 | `pub enum ToInterface` (35 variants, 7 gated) |
| 298–455 | `pub enum ToCore` (50 variants, 10 gated) |
| 457–495 | `ProtocolError` and its `Display`, `Error`, `From<io::Error>` |
| 497–522 | `pub fn clean`, `pub(crate) fn push_raw_text`, `fn is_clean` |
| 524–567 | `write_frame`, `read_frame`, `pub(crate) tail` |
| 569–594 | `push_key`, `push_text`, `push_keys` |
| 596–619 | `update_intent`, `window_intent` |
| 621–633 | `pub fn problem_code`, `problem_of` |
| 635–648 | `window_number`, `flag_byte` |
| 650–717 | `struct Fields<'a>` and its reader methods |
| 719–726 | `read_flag` — the same body as `flag_byte` |
| 728–905 | `write_to_interface`, 172 lines, `#[allow(clippy::too_many_lines)]` |
| 907–1048 | `read_from_core`, 136 lines, allowed |
| 1050–1236 | `write_to_core`, 182 lines, allowed |
| 1238–1341 | `read_from_interface`, 99 lines |
| 1343–1622 | `mod tests`, 279 lines, nine tests, one `cfg(not(feature = "links"))` that also probes decoder kind 68 and fetcher kind 83 |

Two generations of encoding coexist. The older families (Tabs, Strip, Channel, Page, Updated, Frame, Sounding, Visible, Cell, the tab intents, the window intents, and every gated single-byte intent) are written out inside the four big `match` expressions; the newer (links, interaction, keyboard, settings, console, library, cookies, controls) delegate to `push_x`/`read_x` in their own file and the arm is one line. The split in section 3 finishes the second pattern.

Private items reached by the child modules through `super::`: `Fields` and its methods, `push_key`, `push_text`, `is_clean`, `read_frame`, `write_frame`, `read_flag`; and the field `Fields::bytes` read directly at `decoder.rs:366, 565`, `fetcher.rs:279, 461, 508`, `links.rs:121`, `keyboard.rs:193, 209, 214`, `lib.rs:1294`.

### 2.2 `protocol/src/library.rs` (792)

| Lines | Item |
|---|---|
| 10–14 | `pub use interface_core::library::{… 27 names …}` |
| 16–52 | request tags `HISTORY_*` (5 retired), `BOOKMARKS_*`, `STAR_*`, `BAR_*`; `NO_PAGE` |
| 54–195 | row helpers: `push_flag`/`read_flag`, `push_count`/`read_count`, `push_page`/`read_page`, `push_numbers`/`read_numbers`, folders, items, `push_optional`/`read_optional`, `push_range`/`read_range` |
| 197–297 | history view and request |
| 299–361 | suggestions, tab list, `pub(crate) read_steps` (also used by `lib.rs:1333`) |
| 363–469 | bookmarks view and request |
| 471–559 | star view and request, bar view and request |
| 561–577 | `push_window`/`read_window` (also used by `lib.rs` for `Window` and `OpenWindow`) |
| 579–792 | `mod tests`, 212 lines, three tests, a generic `round_trip(value, push, read)` helper |

Five panels' tags and encoders in one file.

### 2.3 `protocol/src/decoder.rs` (757)

| Lines | Item |
|---|---|
| 14–41 | `MAX_CHUNK`, `MAX_WHOLE`, `MAX_COLOURS` (a second definition; `frame.rs:26` has the first), `PAGE_DOTS`, `RGB_BYTES`, `FRAME_HEADER_BYTES`, `WHOLE_FLAGS_BYTES`; the bookmark-import bounds and `NETSCAPE_DOCTYPE` |
| 43–70 | `KIND_*`: core→decoder 48–55 (51 retired); decoder→core 64–77 (68, 69, 71 gated) |
| 71–82 | `MAX_CHANNEL_LOG`, `NO_PAGE`, `VIEW_*` flag bits |
| 84–106 | `pub struct View`; `FIRST_STORE_PAGES`, `MAX_STORE_PAGES` |
| 108–239 | `ToDecoder` (7 variants), `FromDecoder` (14, 3 gated) |
| 241–266 | `BookmarkEntry`, `is_netscape_bookmarks` |
| 268–272 | `display_page` |
| 274–393 | `write_to_decoder`, `read_from_core` |
| 395–414 | `write_frame_to_core` |
| 416–592 | `write_to_core` (78), `read_from_decoder` (90) |
| 594–609 | `raw_text(fields, limit, too_long)`; `_text`, dead, `#[allow(dead_code)]` |
| 611–757 | `mod tests`, 146 lines, six tests |

### 2.4 `protocol/src/links.rs` (669, `links`)

| Lines | Item |
|---|---|
| 14–40 | ten `pub const` bounds |
| 42–56 | `KIND_PAGE_LINKS` 11 … `KIND_ALIASES` 15; run flags; `FOUND_*`; `SECURE` |
| 58–133 | `Message` (core→interface); `push_message` (returns the kind), `is_message`, `read_message` |
| 135–201 | decoder→core and fetcher→core types `Found`, `Candidate`, `NumberLink`, `Alias`, `Service`; the interface's `Spot` |
| 203–266 | `push_whole` (refuses, never cuts), `raw_text`, `count`, `read_count`, `place`, `flags`, `read_flags`, `display_page` |
| 268 | `pub use interface_core::controls::ANY_SUBCODE`, mid-file |
| 270–352 | `FastextTarget`, `Fastext`, `FASTEXT_*`, `push_fastext`/`read_fastext` |
| 354–420 | `push_found`/`read_found`, `push_channel_links`/`read_channel_links` |
| 422–519 | page links, page numbers, pointing, prompt, spot |
| 521–669 | `mod tests`, 148 lines, five tests, reaching `crate::decoder` and `crate::fetcher`; kind 68 at 646, kind 25 at 666 |

Three pipes' link payloads in one file, with its own copies of the text, page and count readers.

### 2.5 `protocol/src/fetcher.rs` (645)

| Lines | Item |
|---|---|
| 16–36 | bounds; `STATUS_CODES` |
| 38–56 | `KIND_*` 80–92 (83, 84 gated), 96 (gated), 97, 98 |
| 58–113 | `CookieSite`, `SITE_*`; `ENTRY_*`; `Origin`, `ORIGIN_*`; `Entry` |
| 115–237 | `FromFetcher` (14 variants, 2 gated), `ToFetcher` (3, 1 gated) |
| 239–298 | `write_to_fetcher`, `read_to_fetcher` |
| 300–306 | `raw_text` (the same body as `links.rs:214`) |
| 308–386 | `write_to_core` (77) |
| 388–470 | `push_cookie_message` (returns the kind), `read_cookie_message` |
| 472–550 | `read_from_fetcher` (74) |
| 552–645 | `mod tests`, 93 lines, three tests; kind 65 at 642 |

### 2.6 `protocol/src/interaction.rs` (506, `interaction`)

`check` (17–36); `InputIntent`, `CursorState`, `Typing` (38–90); `FLAG_*`, `TAG_*`, `KEY_*`, `ABSENT`/`PRESENT`, `NO_CHARACTER` (92–114); action and mouse bytes, `push_string`/`read_string`, `push_point`/`read_point` (116–194); `push_intent`/`read_intent`, `push_input`/`read_input` (196–302); `push_typing`, `check_cursor`, `read_typing` (304–382); `check_message` (384–392); `mod tests` 112 lines (394–506). Intent encoding, typing-state encoding and the fetcher's message check in one file.

### 2.7 The remaining `protocol` files

| File | Shape | Finding |
|---|---|---|
| `keyboard.rs` (387) | bounds, kinds 112–115 and 120, `PhoneState`, `Qr`, the pipe's four functions, then `PhoneView` and `PhoneKey` for the interface; tests 50 | the keyboard pipe and the interface's views in one file; the phone-key tag bytes 0/1/2 are literals (319, 327, 332); `MAX_JOIN` (15) is unused |
| `audio.rs` (387) | `OP_*`, `Sound`, `Audio`, `Sender`, `push` (checks by reading itself back), `read` (64 lines), five field readers; tests 94 | one concept; tests over the inline limit |
| `frame.rs` (330) | the image forms, `encode`, `base`, `decode` (69); tests 83 | one concept; does not use `Fields`; tests over the limit |
| `settings.rs` (320) | bounds at 9–19 and 211–214; `push_remote`/`read_remote` at 41–68 between constant groups; `CHANGE_CHECK_UPDATES` at 71 after functions; tests 65 | one concept, scrambled order |
| `sound.rs` (180), `cookies.rs` (154), `controls.rs` (114), `console.rs` (92) | one concept each | `cookies.rs:16` is a fourth copy of the flag reader; `controls.rs` has no tests of its own |

### 2.8 `decoder/src/lib.rs` (1572)

| Lines | Item |
|---|---|
| 25–26, 68–93 | two import blocks with items between them |
| 28–30 | `pub mod links` (gated), `pub mod netscape` |
| 32–61 | `MAX_LOGS_HELD`, an engine-bound assertion, `ChannelLog`, `keep_log` |
| 63–66 | a second engine-bound assertion |
| 95–126 | consts, `static GLYPHS`, `AUDIO_*` |
| 128–174 | `Exported`, `Rendered`, `Found` (gated) |
| 176–237 | `Engine`, 22 fields, one `#[cfg(test)]` |
| 239–250 | `InputRecords` (gated) |
| 258–709 | `impl Engine`, 452 lines: construction (`new`, `with_store`), views (`set_view`, `stored`, `subcodes`), sounds (`take_sounds`, `open_page`, `tick_audio`), input (`take_input`), feeding (`push_all`, `feed`, `feed_whole`, `drop_pushed`, `complete`, `finish`), reporting (`take_changed`, `take_logs`, `take_store_full`, `take_updated`, `arrivals`), the clock (`now_us`, `next_audio_tick_ms`), export, composition and rendering (`grid`, `render`, `render_at`, `render_into`, `render_over`) |
| 711–728 | `fastext` (gated) |
| 730–768 | `Changes`, `Changed` |
| 770–853 | `RATES`, `FlashRates`, `Flashing` (used by `main.rs` alone) |
| 855–913 | `header_page`, `ReceiverRow` (its doc comment is two run together, 863–866), `PageLines` |
| 915–969 | `Outbox` and its `VoiceSink` |
| 971–1012 | `digest`, `title` |
| 1014–1516 | `mod tests`, 502 lines, 24 tests, reaching private `engine.grid()`, `engine.views`, `engine.digests` |
| 1518–1545 | `pub mod sample` |
| 1547–1572 | `impl InputRecords` (gated), after the tests |

### 2.9 `decoder/src/main.rs` (283)

`Mode` and `mode()` (39–58, untested); `read_bookmarks` (60–90); `run` (92–193: reader thread, deadline wait, dispatch, reporting); `draw` (198–238: the sent-frame cache, links before image, sub-pages); `send_sounds` (242–257); `main` (259–283). Logic that the convention places in the library.

### 2.10 `decoder/src/netscape.rs` (421) and `links.rs` (254)

One concept each. `netscape.rs` tests are 105 lines (316–421); `links.rs` tests 34.

### 2.11 `fetcher/src/main.rs` (515)

`COOKIE_SLOTS`/`COOKIE_BYTES` and two `const _` assertions (59–68); `wait_for_wake` (70–84); `Wake` (86–96); `Random` and its `RandomSource` (98–117); `Action` (119–143); `collect`, the agent's `Output` to `Action` (145–192); `contents_entries` (194–209); `product` (211–221); `descriptor_links` (223–242, gated); `run` (244–363, 120 lines); `read_commands` (365–381); `Arguments`, `arguments` (383–403); `main`; tests 85 lines (430–515). Agent translation, the loop, randomness, arguments and product naming in one binary root.

### 2.12 `fetcher/src/transport.rs` (642)

`CONNECT_TIMEOUT`, `SOCKET_READ`, `READS_AHEAD`, `Wake` (32–43); `address` (46–51); `Connection`, `Failure` (53–71); `certificate_problem` (73–88); `Link`, `Tcp` and its impl (90–161); `reach`, `open` (163–230); `read_socket` (232–252); `Refill`, `refill`, `Connection::receive` (254–311); `write_records` (313–320); `impl Transport` (322–383); `mod tests` 256 lines with an in-process HTTP and SOCKS proxy (385–642). `cookies.rs` (137) is one concept.

### 2.13 `interface/src/main.rs` (1544)

| Lines | Item |
|---|---|
| 50–74 | window and frame-pacing constants; `FRAME` in two `cfg(target_os)` forms |
| 76–149 | `Library` (9 views), `Incoming` (30 variants, 4 gated) |
| 151–178 | `InputMethod`, `Graphics`, `Heard` |
| 180–233 | `View` (14 fields), `View::new` |
| 236–271 | `App` (18 fields) |
| 273–333 | `clipboard_key`, `attributes`, `on_a_display`, `geometry` |
| 335–1001 | `impl App`, 667 lines: `now`, `scale`, `show_tabs`, `request_redraw`, `modifiers`, `send`, `switch_view`, `window_ids`, `open_another`, `close_view`, `tab_out`, `redraw` (63), `update_cursor`, `act` (93, `Output` to `ToCore`), `window_action`, `resize_from_edge`, `sync_ime`, `wheel`, `is_paste`, `paste`, `clipboard`, `clipboard_text`, `copy_text`, `edit_field`, `menu_chosen`, `tab_to_new_window`, `browser_modifier`, `terminal_key`, `show_phone`, `show_typing`, `phone_key`, `key` |
| 1003–1077 | `impl ApplicationHandler<Incoming>`: `resumed`, `user_event`, `window_event`, `device_event`, `about_to_wait` |
| 1079–1114 | `impl App`: `pace` |
| 1116–1431 | `impl App`, 316 lines: `show_frame`, `open_window`, `create_window`, `middle_pressed`, `report_window`, `incoming` (106), `window_input` (118) |
| 1433–1480 | `read_core`: a thirty-arm map of `ToInterface` to `Incoming` |
| 1482–1544 | `main` (63): confine, the event loop, the Dock and menu-bar installs, the reader thread, the `App` literal |

Eight concerns in one root: the event loop; multi-window management; frame presentation; input translation; the input method; the clipboard and menus; outputs to messages; incoming to the browser; the reader thread; tracing. No tests. `keys.rs` (214) is one concept with 93 lines of tests.

### 2.14 `draw-vello/src/lib.rs` (890)

Constants (31–49); `StyleKey`, `Family`, `small_capitals`, conversions (51–117); `Command`, `Recorded`, `Frame` (119–196); `PageImage`, `Painter` (16 fields), `PageError` (198–254); `impl Painter` 273 lines: construction, `begin`, `render`, `copy_to`, `finish`, `damage`, `narrowed`, `draw_box`, `record`, `set_page`, `retain_pages`, `base`, `layout`, `make_layout` (256–528); `changed_dots`, `around` (530–552); the raster calls `draw_*` (554–637); `impl Canvas` (639–715); `mod tests` 173 lines (717–890). Recording, damage, page images, text layout and rasterisation in one file. `damage.rs` is one concept with 63 lines of tests.

### 2.15 `sound/src/audio.rs` (529)

`Mixers` and its impl (52–125); `watch`, `set_sound`, `apply` (127–203); `Speaker` (205–257); `build`, `render`, `OutputSample` and three impls (259–327); `mod tests` 200 lines (329–529). Two concepts: the mixers (pure) and the output device. `main.rs` (128) holds `Wake` and `run` (62 lines).

### 2.16 `dock-menu`, `draw-embedded`, `keyboard`

Each meets the conventions already: `dock-menu/lib.rs` is the Dock types, the `MENU_BAR` table and the fallbacks (354, tests 52 inline); `mac.rs` is the one `unsafe` file; `draw-embedded/lib.rs` is one type; `keyboard/keyboard.rs` is the process (192, tests 21) under a thin `main.rs`.

### 2.17 Functions and `impl` blocks past the limits

| File | Item | Lines | Length |
|---|---|---|---|
| `protocol/lib.rs` | `write_to_core` | 1055–1236 | 182 |
| `protocol/lib.rs` | `write_to_interface` | 734–905 | 172 |
| `protocol/lib.rs` | `read_from_core` | 913–1048 | 136 |
| `protocol/lib.rs` | `read_from_interface` | 1243–1341 | 99 |
| `protocol/decoder.rs` | `read_from_decoder` | 503–592 | 90 |
| `fetcher/main.rs` | `run` | 244–363 | 120 |
| `interface/main.rs` | `window_input` | 1313–1430 | 118 |
| `interface/main.rs` | `incoming` | 1206–1311 | 106 |
| `decoder/main.rs` | `run` | 92–193 | 102 |
| `interface/main.rs` | `act` | 553–645 | 93 |
| `keyboard/keyboard.rs` | `run` | 43–127 | 85 |
| `interface/main.rs` | `impl App` | 335–1001 | 667 |
| `decoder/lib.rs` | `impl Engine` | 258–709 | 452 |
| `interface/main.rs` | `impl App` | 1116–1431 | 316 |

### 2.18 Duplicated shapes

| Shape | Copies (file:lines) |
|---|---|
| a 0 or 1 flag byte, `match fields.u8()? { 0 => false, 1 => true, _ => Err(BadValue(…)) }` | `lib.rs:641–648` (`flag_byte`), `lib.rs:719–726` (`read_flag`, identical), `library.rs:58–64`, `settings.rs:115–121`, `cookies.rs:16–22`; inline at `lib.rs:1272, 1300, 1308, 1314`, `decoder.rs:536`, `fetcher.rs:287, 436, 524`, `keyboard.rs:204`, `links.rs:324`, `console.rs:49`, `sound.rs:82`, `audio.rs:246` — fifteen, with twelve reason strings, one asserted by a test (`lib.rs:1566`, `"mute"`) |
| pushing a flag, `payload.push(u8::from(x))` | `library.rs:54`, `settings.rs:111`, and inline throughout |
| lossy raw text with a bound | `decoder.rs:596–602` (takes the reason), `links.rs:214–222`, `fetcher.rs:300–306` (the last two identical); tests assert `"title too long"` (`decoder.rs:755`) and `"text too long"` (`links.rs:649`, `fetcher.rs:638`) |
| cut-and-length-prefix of untrusted text on send | `lib.rs:513–518` (`push_raw_text`, cuts) against `links.rs:205–212` (`push_whole`, refuses: a target cut short can name another place) — different on purpose |
| a display page number, `page_index(n).ok_or(BadValue("page number"))` | `decoder.rs:268–272`, `links.rs:262–266` (identical `display_page`); inline `lib.rs:987, 993, 1149, 1293`, `interaction.rs:326, 347, 365`, `controls.rs:62, 83`, `fetcher.rs:490`, `decoder.rs:301, 316, 584`; `library.rs:79–94` with a `NO_PAGE` sentinel |
| a counted list prefix | `library.rs:66–77` (u16), `links.rs:224–237` (u8, takes the reason), `lib.rs:584–594` and `694–700`; inline u16 at `console.rs:33, 54`, `cookies.rs:25, 49`, `decoder.rs:289, 353`, `fetcher.rs:314, 482`; inline u8 at `settings.rs:136, 157`, `decoder.rs:452, 547` |
| flag-bit sets with an all-bits mask | `lib.rs:177–189`, `decoder.rs:77–82`, `links.rs:48–51` and `294–297`, `interaction.rs:92–98`, `controls.rs:18–24`, `audio.rs:30–32`, `keyboard.rs:257–258`; unmasked `flags > 3` at `decoder.rs:363`, `fetcher.rs:457, 519`, `cookies.rs:57`; the `flag(set, bit)` closure twice (`lib.rs:752`, `interaction.rs:305`) |
| an optional trailing field read as "payload empty" | `lib.rs:1039, 1270, 1289, 1294`, `library.rs:294, 555`, `keyboard.rs:193`, `links.rs:121, 470, 489`; against flag-prefixed optionals at `library.rs:165–172`, `settings.rs:142, 164, 219, 233` |
| `MAX_COLOURS`, `PAGE_DOTS`, `RGB_BYTES` | `protocol/decoder.rs:22–24` and `protocol/frame.rs:26–29`; `PAGE_DOTS` again in `decoder/lib.rs:108`, `draw-vello/lib.rs:35`, `draw-embedded/lib.rs:28` |
| "cut on a character boundary" | `protocol/lib.rs:514`, `decoder/netscape.rs:307`, `keyboard/keyboard.rs:98` (three crates; left alone) |
| the `Memory` draw target and `channel_with_pages` | `draw-embedded/examples/write_screen.rs:20–62` and `tests/memory_display.rs:21–70` |

### 2.19 Naming

| What | As it is | Note |
|---|---|---|
| a helper's reader of the core's messages | `decoder::read_from_core`, `fetcher::read_to_fetcher`, `keyboard::read_to_keyboard`, `sound::read_to_sound` | three schemes; `protocol::read_from_core` is the *interface's* reader, so two pipes share the name |
| a helper's writer to the core | `decoder::write_to_core`, `fetcher::write_to_core`, `keyboard::write_to_core`, `sound::write_from_sound`; the root's `write_to_core` is the interface's | |
| the flag reader | `flag_byte`, `read_flag` (both in `lib.rs`), `flag` (`cookies.rs`), `push_flag` | |
| the count reader | `push_count`/`read_count` (`library.rs`), `count`/`read_count` (`links.rs`) | |
| sub-kind tags | `HISTORY_*`, `BOOKMARKS_*`, `CHANGE_*`, `PANEL`/`QUERY`/…, `CONTROL_*`, `OP_*`, and literal 0/1/2 in `keyboard.rs` | `KIND_*` is the pipe level; the sub-kind names vary by file |
| `View` | `protocol::decoder::View` (how a page is drawn), `interface/main.rs::View` (a window) | |
| `Found` | `protocol::links::Found` (a link target), `decoder::Found` (a page's links), `decoder::netscape::Found` (a file's bookmarks) | two in one crate |
| `Output` | `interface_core::browser::Output`, `neoteletext_web::agent::Output`, `fetcher::cookies::Output` (a shared writer), `decoder/main.rs::Output` (a writer type) | |

None of these is renamed by this plan (the paths are imported by `core`, the fuzz targets and the hostile tests); the pipe readers are the one case where a rename would remove a real ambiguity, and `30-cross-cutting.md` holds it.

## 3. The target layout

### 3.1 `protocol`

```
protocol/src/
  lib.rs             ~110  doc; the deny list; the mod tree; `pub use` of the API (every path of section 1.1 unchanged);
                           `pub(crate) use` of the seams (Fields, push_text, …) so that every family's `use super::…` holds
  bounds.rs           ~55  the twelve pub bounds (lib.rs 49–76), NEW_WINDOW, FIRST_WINDOW (166–170)
  error.rs            ~45  ProtocolError and its three impls (457–495)
  framing.rs          ~60  HEADER_BYTES; write_frame, read_frame, tail (524–567)
  fields.rs          ~190  KEY_BYTES; Fields and its readers (650–717) with `remaining`, `flag(reason)`, `count_u8(max, reason)`,
                           `count_u16(max, reason)`, `display_page` added; push_key, push_text, push_keys (569–594),
                           push_flag, push_count (one copy each)
  text.rs             ~70  clean, is_clean (497–509, 520–522); push_raw_text (511–518); raw_text(fields, limit, too_long)
                           (decoder.rs 594–602)
  interface.rs       ~310  the core ↔ interface pipe's spine: ToInterface (196–296), ToCore (298–455), the mod declarations,
                           `pub(crate) use` of its children's four functions and problem_code/problem_of
  interface/kinds.rs  ~80  every ungated KIND_* of this pipe (78–175), the strip and tab flag bits (177–189), with the
                           retired numbers and the gated ones listed in a comment table
  interface/to_interface.rs ~150  write_to_interface, read_from_core, one line per kind
  interface/to_core.rs      ~180  write_to_core, read_from_interface, update_intent (596–600)
  interface/strip.rs   ~90  push_strip/read_strip (from 751–767 / 939–961); problem_code, problem_of (621–633)
  interface/tabs.rs    ~80  push_tabs/read_tabs (737–750 / 917–938); push_sounding/read_sounding (806–814 / 1005–1014)
  interface/pages.rs   ~90  FRAME_FIXED_BYTES, CELL_BYTES; channel, page, updated, frame, visible, cell (768–805 / 962–1004;
                            1058–1067 / 1247–1259)
  interface/windows.rs ~90  window_number, window_intent (602–619, 635–639); Target, OpenWindow, CloseWindow, From,
                            NewWindow, TabToWindow, CloseWindow (884–901 / 1036–1042; 1111–1131)
  interface/tests.rs  ~280  the nine tests of lib.rs 1343–1622, moved, with strip() and channel()
  decoder.rs         ~300  ToDecoder, FromDecoder (108–239); write_to_decoder, read_from_core, write_to_core, read_from_decoder,
                           the arms calling the children; the bounds that are the pipe's (MAX_CHUNK, MAX_WHOLE, FIRST_STORE_PAGES,
                           MAX_STORE_PAGES, MAX_CHANNEL_LOG); `pub use` of the children's public names
  decoder/kinds.rs    ~45  KIND_* 48–55, 64–77 with the three gated ones kept here under their cfg (one constant each)
  decoder/frame.rs    ~60  FRAME_HEADER_BYTES; `use crate::frame::{MAX_COLOURS, PAGE_DOTS}` in place of the second definition;
                           write_frame_to_core (395–414); read_frame (from 511–530)
  decoder/view.rs     ~75  View (84–98), VIEW_* (77–82), push_view/read_view (from 315–330 / 372–388)
  decoder/bookmarks.rs ~90 MAX_BOOKMARK_FILE, MAX_BOOKMARK_ENTRIES, MAX_BOOKMARK_NAME, NETSCAPE_DOCTYPE (30–41); BookmarkEntry,
                           is_netscape_bookmarks (241–266); the three bookmark kinds' push and read (473–486 / 572–579)
  decoder/tests.rs   ~150  the six tests (611–757)
  fetcher.rs         ~300  bounds, Origin, Entry, FromFetcher, ToFetcher (16–36, 74–237); the four pipe functions with the
                           cookie arms delegated
  fetcher/kinds.rs    ~35  KIND_* 80–98, the three gated ones under their cfg
  fetcher/cookies.rs ~130  CookieSite, SITE_* (58–72); MAX_SET_COOKIE, MAX_COOKIE_HEADER; push_cookie_message,
                           read_cookie_message (388–470); the CookieAnswer and ReachedAnswer arms (248–260 / 277–293)
  fetcher/tests.rs   ~100  the three tests (552–645)
  links.rs           ~170  the ten bounds (14–40), KIND_* 11–15 and the gated intent kinds KIND_POINT, KIND_TYPED,
                           KIND_CONFIRM, KIND_CANCEL (moved here from lib.rs 108–111, 128–131: a feature's kinds in the
                           feature's file); `pub use` of interface_core::links and ANY_SUBCODE; Message (58–85);
                           push_message, is_message, read_message (87–133); Spot, push_spot, read_spot (189–201, 502–519)
  links/found.rs     ~150  Found, Candidate, NumberLink, Alias, Service (135–187); push_whole (203–212); place, flags,
                           read_flags (239–260); push_found/read_found, push_channel_links/read_channel_links (354–420)
  links/fastext.rs    ~90  FastextTarget, Fastext, FASTEXT_* (270–297); push_fastext/read_fastext (299–352)
  links/interface.rs ~110  what the interface is told: push_page_links/read_page_links, push_numbers/read_numbers,
                           push_pointing/read_pointing, push_prompt/read_prompt (422–500)
  links/tests.rs     ~150  the five tests (521–669)
  library.rs         ~160  `pub use interface_core::library::{…}`; the row helpers (109–172: folders, items, optional, range,
                           numbers, page) as pub(super); push_window/read_window (561–577); the mod declarations
  library/history.rs ~110  HISTORY_* (16–25); the history view and request (197–297)
  library/bookmarks.rs ~160 BOOKMARKS_*, STAR_*, BAR_* (27–49); the bookmarks view and request (363–469); star (471–512); bar (514–559)
  library/lists.rs    ~70  suggestions (299–322); tab list and read_steps (324–361)
  library/tests.rs   ~215  the three tests (579–792)
  interaction.rs     ~120  `pub use Intent`; InputIntent, CursorState, Typing (38–90); check (17–36); check_message (384–392);
                           the gated intent kinds KIND_TYPING, KIND_INPUT, KIND_EDITING and KIND_FOCUSED (from lib.rs 87–88,
                           112–115, 120–121; KIND_FOCUSED keeps its cfg(any(links, interaction)))
  interaction/intent.rs ~200 TAG_*, KEY_*, ABSENT, PRESENT, NO_CHARACTER (100–114); action and mouse bytes (116–148);
                           push_string/read_string, push_point/read_point (150–194); push_intent/read_intent, push_input/read_input (196–302)
  interaction/typing.rs ~90  FLAG_* (92–98); push_typing, check_cursor, read_typing (304–382)
  interaction/tests.rs ~115  the five tests (394–506)
  keyboard.rs        ~340  as today, with the gated kinds KIND_PHONE, KIND_PHONE_KEY, KIND_PHONE_PANEL, KIND_PHONE_FINISH
                           (lib.rs 89–92, 116–119) and the tests left inline (50 lines)
  frame.rs           ~250  as today less its tests
  frame/tests.rs      ~85
  audio.rs           ~295  as today less its tests
  audio/tests.rs      ~95
  settings.rs        ~255  as today, reordered: bounds together (9–19 with 211–214), CHANGE_* together (26–36 with 71),
                           push_remote/read_remote after read_change
  settings/tests.rs   ~65
  sound.rs, cookies.rs, controls.rs, console.rs   unchanged
```

Where `KIND_FOCUSED` ends up (`interaction.rs`, under `cfg(any(feature = "links", feature = "interaction"))`) is the one gated kind that two features share; the convention's "an item used by two features goes in the parent" would put it in `interface/kinds.rs` under its cfg, and that is where it goes if the reviewer prefers; either place keeps the value 26.

Public paths kept by `pub use` in `lib.rs`: all of section 1.1. Public paths that change: none.

Seams (items that become `pub(super)` or `pub(crate)` because a split crosses them): `Fields`, its methods and `bytes` (replaced by `remaining()`), `push_key`, `push_text`, `push_keys`, `push_flag`, `push_count`, `is_clean`, `raw_text`, `read_frame`, `write_frame`, `tail` — `pub(crate)`; `interface/{strip,tabs,pages,windows}.rs` push and read functions, `window_number`, `update_intent` — `pub(super)`; `links::{push_found, read_found, push_fastext, read_fastext, push_channel_links, read_channel_links, push_spot, read_spot}` — `pub(crate)` (reached from `decoder.rs`, `fetcher.rs`, `interface/to_core.rs`); `library::{push_*, read_*}` — `pub(crate)` as today; the row helpers in `library.rs` — `pub(super)`; `decoder/{frame,view,bookmarks}.rs` push and read — `pub(super)`; `fetcher/cookies.rs` push and read — `pub(super)`; the gated `KIND_*` moved into `links.rs`, `interaction.rs`, `keyboard.rs` — `pub(crate)`.

### 3.2 `decoder`

```
decoder/src/
  lib.rs              ~70  doc; the deny list; the two engine-bound assertions (36, 66); the mod tree;
                           `pub use engine::{ChannelLog, Engine, Exported, Found, Rendered}; pub use changes::Changed;
                            pub use flash::{FlashRates, Flashing}; pub use input_records::InputRecords;`
  engine.rs          ~270  the engine's spine: the consts (95–126 less the title consts), static GLYPHS, Exported, Rendered,
                           Found, ChannelLog, the Engine struct (176–237), Default, `impl Engine { new, with_store, take_sounds,
                           open_page, tick_audio, take_input, take_changed, take_logs, take_store_full, now_us,
                           next_audio_tick_ms, take_updated }`; the mod declarations
  engine/feed.rs     ~220  `impl Engine { push_all, feed, feed_whole, drop_pushed, complete, finish, arrivals }`;
                           MAX_LOGS_HELD, keep_log (32–61); header_page (855–861); digest (971–978); ReceiverRow, PageLines (863–913)
  engine/render.rs   ~220  `impl Engine { set_view, stored, subcodes, grid, render, render_at, render_into, render_over, export }`;
                           fastext (711–728, gated: one function, kept here under its cfg)
  engine/tests.rs    ~510  the 24 tests (1014–1516): a child of `engine`, so engine.views, engine.digests and engine.grid()
                           stay private
  title.rs            ~50  TITLE_MINIMUM, MOSAIC_SHARE, FIRST_TEXT_ROW, LAST_TEXT_ROW; title (980–1012); pub(crate)
  changes.rs          ~45  Changes, note (730–759, pub(crate)); Changed (761–768)
  flash.rs            ~90  RATES, FlashRates, Flashing (770–853)
  voice_sink.rs       ~60  AUDIO_* (122–126 stay in engine.rs: the receiver's store is the engine's); Outbox, sound,
                           impl VoiceSink (915–969); pub(crate)
  input_records.rs    ~50  InputRecords (239–250) and its impl (1547–1572); the whole file `#[cfg(feature = "interaction")]`
  sample.rs           ~30  the sample module (1518–1545); `pub mod sample;`
  links.rs           ~220  as today less its tests
  links/tests.rs      ~35  (or left inline: 34 lines is under the limit; the move is optional)
  netscape.rs        ~315  as today less its tests
  netscape/tests.rs  ~105
  process.rs         ~230  from main.rs: Mode, mode (39–58), read_bookmarks (60–90), run (92–193), draw (198–238),
                           send_sounds (242–257), MICROSECONDS_PER_MILLISECOND, the Output alias
  main.rs             ~40  windows_subsystem; the deny list; main (259–283) calling decoder::process
```

Public paths kept: every one of section 1.2, by the `pub use` lines in `lib.rs` and `pub mod {links, netscape, sample}`. New public path: `decoder::process::{run, read_bookmarks, mode, Mode}`, used by `main.rs` only. Public paths that change: none.

Seams: `Engine`'s fields stay private to `engine` (its children are `impl Engine` blocks); `Outbox` and `Changes` become `pub(crate)` with `pub(crate)` fields; `title` `pub(crate)`; `FlashRates` is already `pub`.

### 3.3 `fetcher`

```
fetcher/src/
  lib.rs              ~40  NEW ROOT: the deny list (byte-identical), the mod tree, `pub use process::run; pub use arguments::{Arguments, arguments};`
  process.rs         ~200  Wake, wait_for_wake (70–96); Action, collect (119–192); contents_entries (194–209); run (244–363);
                           read_commands (365–381); COOKIE_SLOTS, COOKIE_BYTES, READ_CHUNK and the three assertions (59–68)
  agent.rs            ~60  Random (98–117); product (211–221); descriptor_links (223–242, gated: one function)
  arguments.rs        ~60  Arguments, arguments (383–403) and their test (496–515, 20 lines, inline)
  cookies.rs         ~137  as today
  transport.rs       ~390  as today less its tests
  transport/tests.rs ~260  the nine tests and the test proxy (385–642)
  main.rs             ~40  windows_subsystem; the deny list; main (405–428) calling fetcher::run
```

`Cargo.toml` gains `[lib] name = "fetcher" path = "src/lib.rs"`, as `decoder` and `sound` have. `native/fetcher/src/lib.rs` is added to `NO_PANIC_ROOTS` in `scripts/check.sh` in the same commit (`00-conventions.md` section 8). No lockfile changes: a target is not a package. New public paths: the library's, used by `main.rs` alone. Departure, section 4 step 28 says why the library is made rather than the logic left in `main.rs`.

### 3.4 `interface`

```
interface/src/
  lib.rs              ~45  the deny list; `pub mod keys` (gated); `mod app; mod incoming; mod reader; mod window;`
                           `pub use app::App; pub use reader::read_core; pub use incoming::Incoming;`
  keys.rs            ~120  as today less its tests
  keys/tests.rs       ~95
  incoming.rs         ~90  Library (76–87), Incoming (89–149)
  reader.rs           ~55  read_core (1433–1480)
  window.rs          ~120  WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, MINIMUM_*, TORN_OFFSET, RESIZE_MARGIN, FRAME (50–60, 68–74);
                           attributes (284–303), on_a_display (305–316), geometry (318–333)
  app.rs             ~280  App (236–271), View (180–233), Graphics, Heard, InputMethod (151–178), `App::new(trace_frames)`
                           (the literal of main.rs 1514–1533), now, scale, send (381–391), window_ids;
                           impl ApplicationHandler<Incoming> (1003–1077); the mod declarations
  app/windows.rs     ~220  switch_view, open_another, close_view, open_window, create_window, report_window, show_tabs,
                           window_action, resize_from_edge, tab_out, tab_to_new_window
  app/frame.rs       ~140  CHANGE_FRAME_MILLISECONDS, TYPING_FRAME_MILLISECONDS; redraw (471–533), show_frame (1120–1142),
                           request_redraw, update_cursor, pace (1079–1114); the frame-trace eprintln!s
  app/input.rs       ~200  modifiers (374–377), key (952–1000), wheel (708–729), middle_pressed, window_input (1313–1430)
  app/typing.rs      ~110  `#[cfg(feature = "interaction")]`: browser_modifier, terminal_key, is_paste, paste, show_typing
  app/phone.rs        ~90  `#[cfg(feature = "phone-keyboard")]`: show_phone (872–885), phone_key (915–950)
  app/ime.rs          ~30  sync_ime (692–703)
  app/clipboard.rs   ~110  clipboard_key (273–282), clipboard, clipboard_text, copy_text (749–764), edit_field (770–793),
                           menu_chosen (798–825), the Dock Choice handling (from incoming 1227–1237)
  app/outputs.rs     ~110  act (553–645)
  app/incoming.rs    ~120  incoming (1206–1311) less the Dock arm
  main.rs             ~50  windows_subsystem; the deny list; main (1482–1544) building `App::new` and the event loop
```

`View`, `Graphics`, `Heard` and `InputMethod` live in `app.rs` rather than `window.rs` because every child of `app/` reads and writes their fields (`self.view.dirty`, `self.view.held`, `self.view.graphics`); a method for each would be a seam of thirty accessors, which section 6 of the conventions says means the two are one concept. `window.rs` keeps only the free functions and the constants of the system window.

Public paths kept: `neoteletext_interface::keys::{KeyParts, modifiers, parts, phone_parts}`. New public paths: `neoteletext_interface::{App, Incoming, read_core}`, used by `main.rs` alone. Changed: none.

### 3.5 `draw-vello`

```
draw-vello/src/
  lib.rs             ~230  TOLERANCE, OPAQUE, RGBA_BYTES, PAGE_DOTS, ROBOTO, OPEN_SANS; Family (58–74); colour, rect, point (96–106);
                           Painter and PageError (208–254); `impl Painter { new, begin, redraw_whole, surface, render, copy_to, finish }`;
                           the mod declarations; `pub use damage::{Damage, DeviceBox, MAX_BOXES}`
  record.rs          ~170  Command, Recorded, Frame (119–196); record (443–447); around (545–552); impl Canvas for Painter (639–715)
  damage.rs          ~300  as today, with `impl Painter { damage, narrowed }` (357–402) and changed_dots (530–543) moved in
  damage/tests.rs     ~65
  pages.rs            ~80  PageImage (198–206); image, pixmap (108–117); set_page, retain_pages (449–487); draw_page (599–607)
  text.rs            ~130  SMALL_CAPITAL, INK_OVERHANG, LAYOUT_CACHE_LIMIT, StyleKey, style_key, small_capitals (36–94);
                           layout, make_layout (494–527); draw_text (609–636)
  raster.rs           ~80  draw_box (404–440); base (490–492); draw_fill, draw_polygon, draw_dim, draw_push_clip, draw_gradient (556–597)
  tests.rs           ~175  the seven tests (717–890)
```

`Painter`'s fields stay private to the crate root; every child is an `impl Painter` block. Public paths kept: all. Changed: none.

### 3.6 `sound`

```
sound/src/
  lib.rs              ~20  the deny list; `pub mod audio; pub mod process;`
  audio.rs           ~220  SCRATCH_FRAMES, Shared, key, MAX_VOLUME and its assertion; Mixers and its impl (52–125); watch, set_sound,
                           apply (127–203); `pub use device::{Speaker, OutputSample, render}`; `mod device;`
  audio/device.rs    ~130  Speaker (205–257); build, render, OutputSample and its impls (259–327)
  audio/tests.rs     ~200
  process.rs          ~90  Wake, TRACE_EVERY, run (36–110) from main.rs
  main.rs             ~35  windows_subsystem; the deny list; main (112–128) calling sound::process::run
```

Public paths kept by the `pub use` in `audio.rs`: `sound::audio::{Mixers, Shared, Speaker, OutputSample, apply, watch, set_sound, render}`. New: `sound::process::run`. Changed: none.

### 3.7 Left as they are

`draw-embedded` (one type, 233 lines; its example and test each under the limit), `dock-menu` (the `unsafe` file is named by requirement 10.12 and the plain file is a table with its readers), `keyboard` (see step 32 for why its 192-line module stays in the binary).

### 3.8 The numbers after the work (estimated)

| | files | largest | over 500 | functions over 80 | `impl` over 300 | test lines inline |
|---|---|---|---|---|---|---|
| `protocol` | 48 | ~340 (`keyboard.rs`) | 0 | 0 | 0 | ~250 (the small files) |
| `decoder` | 15 | ~315 (`netscape.rs`) | 0 | 1 (`process::run`, 102; step 24) | 0 | ~55 |
| `fetcher` | 8 | ~390 (`transport.rs`) | 0 | 1 (`process::run`, 120; step 28) | 0 | ~30 |
| `interface` | 16 | ~280 (`app.rs`) | 0 | 2 (`window_input` 118, `incoming` 106; step 36) | 0 | 0 |
| `draw-vello` | 8 | ~300 (`damage.rs`) | 0 | 0 | 0 | 0 |
| `sound` | 6 | ~220 | 0 | 0 | 0 | 0 |

## 4. The moves

Each step is one commit on the browser's `main` that compiles in every feature shape and passes `scripts/check.sh commit`. "Moves" names items by their current file and lines; "visibility" lists the seams; "declarations" the `mod` and `use` lines added; "importers" what changes outside the crate. Steps 1–23 are phase B1 (`protocol`); 24–41 are phase B3.

### `protocol`

1. **`bounds.rs` and `error.rs`.** Moves: `lib.rs` 49–76 and 166–170 to `bounds.rs`; 457–495 to `error.rs`. Declarations: `mod bounds; mod error; pub use bounds::*; pub use error::ProtocolError;`. Visibility: none. Importers: none (paths unchanged).

2. **`framing.rs`.** Moves: `HEADER_BYTES` (191), `write_frame`, `read_frame`, `tail` (524–567). Visibility: `write_frame`, `read_frame` → `pub(crate)`; `tail` stays `pub(crate)`. Declarations: `mod framing; pub(crate) use framing::{read_frame, tail, write_frame};` — the families' `use super::{read_frame, write_frame}` resolve through the re-export. Importers: none.

3. **`fields.rs`.** Moves: `KEY_BYTES` (192), `Fields` and its impl (650–717), `push_key`, `push_text`, `push_keys` (569–594), `flag_byte` (641–648) renamed `read_flag`; delete the duplicate `read_flag` (719–726) and point `lib.rs` 606, 1287, 1328, 1330, 1332 at the one. Adds `Fields::remaining(&self) -> usize` and changes the ten direct `fields.bytes` reads of section 2.1 to it (the one change that is not a move; listed in the message). Visibility: `Fields`, its methods, `push_key`, `push_text`, `push_keys`, `read_flag` → `pub(crate)`. Declarations: `mod fields; pub(crate) use fields::{Fields, push_key, push_keys, push_text, read_flag};`. Importers: none.

4. **`text.rs`.** Moves: `clean`, `is_clean` (497–509, 520–522), `push_raw_text` (511–518), and `decoder.rs` `raw_text` (594–602) as the one copy. `links.rs:214–222` and `fetcher.rs:300–306` are deleted and their callers pass `"text too long"` (sixteen call sites: `links.rs` 385, 392, 414, 417; `fetcher.rs` 434, 435, 451, 454, 455, 460, 467, 488, 492, 510, 530, 534). Visibility: `is_clean`, `raw_text` → `pub(crate)`. Declarations: `mod text; pub use text::clean; pub(crate) use text::{is_clean, push_raw_text, raw_text};`. Importers: none. The test strings asserted at `links.rs:649` and `fetcher.rs:638` are unchanged.

5. **The field readers unified.** Adds to `fields.rs`: `Fields::flag(&mut self, reason: &'static str)`, `count_u8`, `count_u16`, `display_page`; `push_flag`, `push_count`. Replaces the copies of section 2.18 row by row, each call passing the reason string it has today, so every `BadValue(…)` text is the same as before. Deletes `library.rs:54–77`, `settings.rs:111–121`, `cookies.rs:16–22`, `links.rs:224–237, 262–266`, `decoder.rs:268–272`. This is the one step whose diff is not purely a move; it is kept to one commit, with the list of sites in the message, so the reviewer can check each reason string. Importers: none.

6. **`interface/kinds.rs`.** Makes `interface/` and moves `lib.rs` 78–175 (less the two `pub` consts) and 177–189 to it, the gated kinds included for now. Declarations in `lib.rs`: `mod interface;` with `interface.rs` holding `mod kinds; pub(crate) use kinds::*;` and for this step nothing else; `lib.rs` keeps `use interface::*` so the four big functions compile. Visibility: every kind → `pub(crate)`. Importers: none.

7. **`interface/strip.rs`.** Moves: the Strip arm bodies (751–767, 939–961) as `push_strip`/`read_strip`; `problem_code`, `problem_of` (621–633). Visibility: push and read → `pub(super)`; the problem functions stay `pub`, re-exported from `lib.rs` (`pub use interface::strip::{problem_code, problem_of};`). Importers: none (`fetcher.rs` calls `crate::problem_code`).

8. **`interface/tabs.rs`.** Moves: Tabs (737–750, 917–938) and Sounding (806–814, 1005–1014) arm bodies. `sound.rs` 105–114 and 127–136 are the same list reader and writer; they call `tabs::push_channels`/`read_channels` (`pub(crate)`). Importers: none.

9. **`interface/pages.rs`.** Moves: `FRAME_FIXED_BYTES`, `CELL_BYTES` (193–194); Channel, Page, Updated, Frame (768–805, 962–1004), Visible, Cell (1058–1067, 1247–1259). The Frame read keeps its early `return` in the dispatch and calls `pages::read_frame_head(&mut fields)` for the key and version. Visibility: `pub(super)`.

10. **`interface/windows.rs`.** Moves: `window_number` (635–639), `window_intent` (602–619), the Target, OpenWindow, CloseWindow arms (884–901, 1036–1042), the From, NewWindow, TabToWindow, CloseWindow arms (1111–1131). Visibility: `pub(super)`.

11. **`interface/to_interface.rs` and `interface/to_core.rs`.** Moves: `ToInterface` and `ToCore` (196–455) into `interface.rs`; `write_to_interface`, `read_from_core` (728–1048) into `to_interface.rs`; `write_to_core`, `read_from_interface`, `update_intent` (1050–1341, 596–600) into `to_core.rs`. Each arm that still carries a body is now a call into steps 7–10 or into a family module. The three `#[allow(clippy::too_many_lines, reason = …)]` come off: the functions are under 100 lines and the reason would be false. Declarations: `lib.rs` has `pub use interface::{ToCore, ToInterface, read_from_core, read_from_interface, write_to_core, write_to_interface};`. Importers: none; `core/src/{main,hostile_tests}.rs`, `interface/src/main.rs`, `fuzz/{core_messages,interface_messages}.rs` compile unchanged.

12. **`interface/tests.rs`.** Moves: `lib.rs` 1343–1622. The tests use `KIND_*` through `use super::kinds::*` and the root functions through `use crate::…`. `strip()` and `channel()` stay with them. Importers: none.

13. **Gated kinds to their feature files.** Moves: `KIND_POINT`, `KIND_TYPED`, `KIND_CONFIRM`, `KIND_CANCEL` to `links.rs`; `KIND_TYPING`, `KIND_INPUT`, `KIND_EDITING`, `KIND_FOCUSED` to `interaction.rs`; `KIND_PHONE`, `KIND_PHONE_KEY`, `KIND_PHONE_PANEL`, `KIND_PHONE_FINISH` to `keyboard.rs`; each `pub(crate)`, each keeping its cfg; `interface/kinds.rs` keeps a comment table naming them so the numbering is readable in one place. `to_interface.rs` and `to_core.rs` import them under the same cfg. Checked by the five Clippy shapes in `check.sh`. Importers: none.

14. **`library/`.** Makes `library/{history,bookmarks,lists,tests}.rs`; `library.rs` keeps the re-exports, the row helpers (as `pub(super)`) and `push_window`/`read_window`. Moves as section 3.1. Declarations in `library.rs`: `mod bookmarks; mod history; mod lists; #[cfg(test)] mod tests; pub(crate) use …` of the fourteen push and read functions. Importers: none.

15. **`decoder/`.** Makes `decoder/{kinds,frame,view,bookmarks,tests}.rs`; `decoder.rs` keeps the enums, the pipe bounds and the four functions. `decoder/frame.rs` imports `crate::frame::{MAX_COLOURS, PAGE_DOTS}` and `decoder.rs` re-exports `pub use crate::frame::MAX_COLOURS;` so `protocol::decoder::MAX_COLOURS` holds; `RGB_BYTES` is `pub(crate)` in `frame.rs`. `pub use bookmarks::{BookmarkEntry, MAX_BOOKMARK_ENTRIES, MAX_BOOKMARK_FILE, MAX_BOOKMARK_NAME, NETSCAPE_DOCTYPE, is_netscape_bookmarks}; pub use view::View;`. Delete `_text` (604–609). Importers: none (`core`, `decoder/src/{lib,main,netscape}.rs`, `decoder/tests/confined_bookmarks.rs`, `fuzz/{decoder_messages,decoder_requests,netscape_file}.rs` unchanged).

16. **`fetcher/`.** Makes `fetcher/{kinds,cookies,tests}.rs`; `fetcher.rs` re-exports `pub use cookies::{CookieSite, MAX_COOKIE_HEADER, MAX_SET_COOKIE};`. Importers: none (`fetcher/src/cookies.rs`, `core`, `fuzz/fetcher_commands.rs` unchanged).

17. **`links/`.** Makes `links/{found,fastext,interface,tests}.rs`; `links.rs` keeps the bounds, the kinds, `Message`, its three functions, `Spot` and its two. Re-exports `pub use found::{Alias, Candidate, Found, NumberLink, Service}; pub use fastext::{Fastext, FastextTarget}; pub(crate) use found::{push_channel_links, push_found, read_channel_links, read_found}; pub(crate) use fastext::{push_fastext, read_fastext};`. Importers: none (`core`, `decoder/src/{lib,links}.rs`, `fetcher/src/main.rs`, `interface/src/main.rs` unchanged).

18. **`interaction/`.** Makes `interaction/{intent,typing,tests}.rs`. `interaction.rs` re-exports `pub(crate) use intent::{push_input, read_input}; pub(crate) use typing::{push_typing, read_typing};`. Importers: none.

19. **`settings.rs` reordered.** No item moves between files; the bounds, the `CHANGE_*` tags and the remote functions are put in the order of `00-conventions.md` section 7, and the tests go to `settings/tests.rs`. Importers: none.

20. **`frame/tests.rs`, `audio/tests.rs`.** The test modules of `frame.rs` (246–330) and `audio.rs` (293–387) moved out. Importers: none.

21. **`keyboard.rs` tag names.** The phone-key tags 0, 1, 2 at 319, 327, 332 named `PHONE_KEY_UP`, `PHONE_KEY_DOWN`, `PHONE_TEXT` (`00-conventions.md` section 8: every constant defined once). Values unchanged. Importers: none.

22. **`lib.rs` tidied.** With everything moved, `lib.rs` is the doc, the deny list, the mod tree and the re-exports (~110 lines). The module doc of each new file is written in this commit if it was not in the step that made it.

23. **Fuzz and `core` check.** `cd native/fuzz && cargo check --all-targets` and `scripts/check.sh full` once at the end of B1 (the fuzz workspace is built only by the full gate). No fuzz target changes are expected; this step records that.

### `decoder`

24. **`decoder::process`.** Moves: `main.rs` 34–257 (`MICROSECONDS_PER_MILLISECOND`, `Output`, `Mode`, `mode`, `read_bookmarks`, `run`, `draw`, `send_sounds`) to `src/process.rs`; `main.rs` keeps its attributes, the deny list and `main`. Visibility: `run`, `read_bookmarks`, `mode`, `Mode` → `pub`. Declarations: `pub mod process;` in `lib.rs`. `run` stays 102 lines: it is the process's one loop, and cutting it at the dispatch would make two functions that share seven locals; the departure is accepted and `#[allow(clippy::too_many_lines, reason = "the decoder's one loop")]` is added, as the trusted core's loop has. Importers: none.

25. **`flash.rs`, `changes.rs`, `voice_sink.rs`, `input_records.rs`, `sample.rs`, `title.rs`.** Six files, one commit each (one concept per commit): `lib.rs` 770–853; 730–768; 915–969; 239–250 with 1547–1572; 1518–1545; 980–1012 with its four consts. Visibility: `Outbox` and `Changes` → `pub(crate)` with `pub(crate)` fields; `title` → `pub(crate)`. Declarations: the six `mod` lines and `pub use` of `Changed`, `FlashRates`, `Flashing`, `InputRecords` in `lib.rs`; `pub mod sample;`. Importers: none (`decoder::Flashing`, `decoder::sample::tti` hold).

26. **`engine.rs` and `engine/tests.rs`.** Moves: everything left of `lib.rs` between the imports and the tests (95–709, 855–913, 971–978) to `engine.rs`, the two import blocks merged at its top; the tests (1014–1516) to `engine/tests.rs` as `#[cfg(test)] mod tests;` at the end of `engine.rs`. `lib.rs` keeps the doc, the deny list, the two assertions and the mod tree. Declarations: `mod engine; pub use engine::{ChannelLog, Engine, Exported, Found, Rendered};`. Importers: none.

27. **`engine/feed.rs` and `engine/render.rs`.** Moves: the methods of section 3.2 out of `engine.rs` into two `impl Engine` blocks, with `keep_log`, `header_page`, `digest`, `ReceiverRow`, `PageLines` to `feed.rs` and `fastext` to `render.rs`. Visibility: none (children of `engine`). Then `netscape/tests.rs` (and `links/tests.rs` if wanted) in the same way, each its own commit. Importers: none.

### `fetcher`

28. **The library target.** Adds `[lib] name = "fetcher"` to `Cargo.toml` and `src/lib.rs` with the byte-identical deny list; adds `native/fetcher/src/lib.rs` to `NO_PANIC_ROOTS` in `scripts/check.sh`. Moves: `cookies.rs` and `transport.rs` declarations from `main.rs` to `lib.rs`; `main.rs` 59–403 to `process.rs`, `agent.rs`, `arguments.rs` as section 3.3 (three commits after this one, one per file). `main.rs` keeps `main` calling `fetcher::run`. This is the one new root the plan makes in these crates; it is made because `00-conventions.md` section 2 asks for the binary to be the thin edge, and because `collect` (the agent's output to actions) and `arguments` are the fetcher's testable logic, today testable only inside the binary. `run` stays 120 lines with the same allow and reason as step 24. Importers: none outside the package.

29. **`transport/tests.rs`.** Moves `transport.rs` 385–642. Importers: none.

### `interface`

30. **`incoming.rs` and `reader.rs`.** Moves: `main.rs` 76–149 to `src/incoming.rs`; 1433–1480 to `src/reader.rs`. Both into the library: `lib.rs` gains `mod incoming; mod reader; pub use incoming::Incoming; pub use reader::read_core;`. `main.rs` uses `neoteletext_interface::{Incoming, read_core}`. Visibility: `Incoming`, `Library`, `read_core` → `pub` (documented). Importers: none.

31. **`window.rs`.** Moves: the constants 50–60 and 68–74, `attributes`, `on_a_display`, `geometry` (284–333) to `src/window.rs` in the library; `pub(crate)`. Importers: none.

32. **`app.rs`.** Moves: `App`, `View`, `Graphics`, `Heard`, `InputMethod` (151–271), the whole `impl App` and `impl ApplicationHandler` (335–1431) to `src/app.rs` in the library, verbatim; the `App { … }` literal of `main.rs` 1514–1533 becomes `App::new(trace_frames: bool)` in `app.rs`; `main.rs` is `main` alone. Visibility: `App` and `App::new` → `pub`. This commit makes a 1,300-line `app.rs` for one step; steps 33–38 cut it. Importers: none. (Departure noted for `keyboard`: the same move is not made there, because `keyboard` has no library and its one module is 192 lines with its argument test already in place; a new root for it would be a cost without a gain.)

33. **`app/outputs.rs`.** Moves `act` (553–645) as an `impl App` block. Declarations: `mod outputs;` in `app.rs`.

34. **`app/incoming.rs` and `app/clipboard.rs`.** Moves `incoming` (1206–1311) less its Dock arm, `show_phone`'s and `show_typing`'s callers unchanged; `clipboard_key`, `clipboard`, `clipboard_text`, `copy_text`, `edit_field`, `menu_chosen`, and the Dock `Choice` handling (1227–1237) as `fn dock_chosen`. The one non-move: `incoming`'s `Incoming::Dock` arm becomes a call to `dock_chosen`.

35. **`app/typing.rs` and `app/phone.rs`.** Moves the `cfg(feature = "interaction")` methods `browser_modifier`, `terminal_key`, `is_paste`, `paste`, `show_typing` into a file declared `#[cfg(feature = "interaction")] mod typing;`, and the `phone-keyboard` methods `show_phone`, `phone_key` into `#[cfg(feature = "phone-keyboard")] mod phone;`. The item-level cfgs come off inside the files. The cfg arms inside `window_input`, `incoming`, `pace`, `wheel` and `sync_ime` stay as arms (a `match` arm cannot live in another file); each calls the gated file.

36. **`app/input.rs` and `app/ime.rs`.** Moves `modifiers`, `key`, `wheel`, `middle_pressed`, `window_input`; `sync_ime`. `window_input` (118) and `incoming` (106) keep their length: each is one `match` over one event enum with one arm per variant, which section 1 of the conventions allows for "a long `match` that is one spec clause"; they take `#[allow(clippy::too_many_lines, reason = "one arm for each event")]` and the plan records it.

37. **`app/frame.rs` and `app/windows.rs`.** Moves the frame methods and the two pacing constants; then the window-management methods of section 3.4.

38. **`keys/tests.rs`.** Moves `keys.rs` 121–214.

### `draw-vello` and `sound`

39. **`draw-vello`.** Five commits: `tests.rs` (717–890); `record.rs`; `pages.rs`; `text.rs`; `raster.rs`; then `damage` gains `damage`, `narrowed`, `changed_dots` and its tests move to `damage/tests.rs`. Visibility: none (`Painter`'s fields are the crate root's; every child is `impl Painter`). Importers: none (`interface/src/main.rs` and the example use `draw_vello::{Family, Painter}` as before).

40. **`sound::audio::device` and `audio/tests.rs`.** Moves `audio.rs` 205–327 to `audio/device.rs` and 329–529 to `audio/tests.rs`; `audio.rs` re-exports `pub use device::{OutputSample, Speaker, render};`. Importers: none (`main.rs` and `tests/confined.rs` unchanged).

41. **`sound::process`.** Moves `main.rs` 36–110 to `src/process.rs`; `main.rs` keeps `main`. Declarations: `pub mod process;`. Importers: none.

## 5. Risks particular to these crates

| Risk | Where | How the steps meet it |
|---|---|---|
| A gated kind moved into a feature file is named by an arm compiled under another feature | `KIND_FOCUSED` (`any(links, interaction)`); `links::is_message`'s range 11–15 used as a guard in `read_from_core` | Step 13 keeps `KIND_FOCUSED`'s cfg wherever it lives and imports it under the same cfg; `is_message` stays beside the links kinds; `check.sh` builds all five feature shapes at every commit |
| `Fields::bytes` read directly by ten sites breaks when `Fields` leaves `lib.rs` | section 2.1 | step 3 adds `remaining()` first |
| Test reason strings change | the fifteen flag readers, three `raw_text`s, the count readers | steps 4 and 5 pass each site's string through; the asserted ones (`"mute"`, `"title too long"`, `"text too long"`, `"too many links"`, `"too many rows"`) are listed in the commit message and checked by the moved tests |
| Kind bytes written as literals in tests | `lib.rs:1574–1589` (11–15, 24–27, 36, 37, 68, 83), `links.rs:646, 666`, `audio.rs:350, 379–381`, `fetcher.rs:642`, `keyboard.rs:377` | they pin the wire contract and are moved, not edited |
| The three `too_many_lines` allows become false | `lib.rs:733, 912, 1054` | removed in step 11 |
| `decoder`'s tests reach private fields | `engine.views`, `engine.digests` (`#[cfg(test)]`), `engine.grid()` | the tests are a child of `engine` (step 26), never a sibling |
| A new no-panic root | `fetcher/src/lib.rs` | step 28 adds the list and the `NO_PANIC_ROOTS` entry in the same commit; `check_no_panic_lists` compares the text from `#![deny(` to `)]` byte for byte |
| `missing_docs` on new `pub` items | `decoder::process`, `fetcher::{run, Arguments}`, `neoteletext_interface::{App, Incoming, read_core}`, `sound::process` | each is documented in the step that makes it; `pub(crate)` and `pub(super)` items need none |
| `cfg` inside shared files after the split | `interface`'s enum variants, `window_input`'s arms, `PageLines`'s fields, `Rendered.links` | unavoidable for variants, arms and fields; counted in section 3.8's measure and noted in `30-cross-cutting.md` |
| The `unsafe` location | `dock-menu/src/mac.rs` | not touched |
| Platform code | `interface`'s `FRAME` and `attributes` (`cfg(target_os = "macos")`), `sound`'s device | one-line forms stay inline; the sound helper's split is run by hand on each desktop before its commit (`01-method-and-order.md` section 3) |
| The fuzz workspace's lockfile | `native/fuzz/Cargo.lock` | no package changes; `cargo metadata --locked` in the commit gate proves it |
| `core`'s imports | 22 files and three tests (section 1.1) | every path is a re-export; `core` is built by every gate |

## 6. Seen, not part of this plan

- `sound/src/audio.rs:254` and `273` print `neoteletext-interface: audio output: …` from the process named `neoteletext-sound` (a leftover of decision 55).
- `protocol/src/decoder.rs:604–609`: `_text` is dead code under `#[allow(dead_code)]`; step 15 deletes it as part of the move, since deleting an unused private function changes no behaviour.
- `MAX_COLOURS`, `PAGE_DOTS` and `RGB_BYTES` are defined in both `protocol/src/decoder.rs` and `protocol/src/frame.rs`; step 15 keeps one. `PAGE_DOTS` is also restated in `decoder`, `draw-vello` and `draw-embedded` from the two engine constants; a `pub const` in `interface_core::canvas` would be the one definition (a change for `21-browser-interface-core.md`).
- `protocol/src/keyboard.rs:15` `MAX_JOIN` is unused.
- `decoder/src/lib.rs:863–866`: two doc comments run together above `ReceiverRow`.
- `draw-embedded`'s example and test each define a `Memory` draw target and `channel_with_pages`; a `tests/common/mod.rs` would hold one copy if a third user appears.
- The pipe readers' names (`read_from_core` on two pipes; `read_to_fetcher`, `read_to_keyboard`, `read_to_sound`) are the one naming inconsistency a rename would improve; the importers are `core`, the fuzz targets and the three processes. Recorded for `30-cross-cutting.md`.
- `interface/src/main.rs:1437–1480` re-wraps every `ToInterface` variant into `Incoming` one for one; whether `Incoming` could carry `ToInterface` itself (plus `Dock`, `Menu`, `End`) is a design question, not a move.
