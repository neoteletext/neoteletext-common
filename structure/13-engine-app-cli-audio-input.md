# 13. The engine's application, command-line, audio and input crates, `xtask`, the fuzz targets and the firmware image

| | |
|---|---|
| **Covers** | `neoteletext-app`, `neoteletext-cli`, `neoteletext-audio`, `neoteletext-audio-mix`, `neoteletext-input`, `neoteletext-qrkeyboard`, `xtask`, `fuzz/`, `firmware/test-image/`, and the repository-level `tests/` folder. |
| **Rests on** | A whole reading of every `.rs` file in those parts of the engine at `fb2dd8a` (about 21,800 lines), the crates' `Cargo.toml` files, `ARCHITECTURE.md`, `scripts/check.sh`, the hooks, and the browser's imports at `494aa91`. Function, `impl` and test-module lengths were measured by matching each closing brace at its opening indentation, not estimated. |
| **Rules** | `00-conventions.md`. Where a target file is left over 500 lines or a step departs from a convention, the step says why. |

---

## 1. The crates as they are

### 1.1 `neoteletext-app` (14 files, 4,742 lines)

Layer L9 for `neottx` and any viewer program: the decoding session, reading inputs, both processes of live mode, the operating-system sandbox, format conversion, slicing, writing pages from text, and the presentation pieces every viewer shares. A library only.

Features: `default = ["live", "slice", "write-text"]`. `live` brings `neoteletext-web` (default and `std`), `embedded-io`, `rustls`, `webpki-roots`; `slice` brings `neoteletext-slicer`; `write-text` brings `neoteletext-core/extended-sets` and `unicode-bidi`. On Linux, `landlock`, `seccompiler` and `libc` are unconditional.

| File | Lines | Gate |
|---|---|---|
| `src/lib.rs` | 52 | |
| `src/convert.rs` | 366 | |
| `src/extras.rs` | 290 | |
| `src/fetch.rs` | 1,071 | `live` |
| `src/input.rs` | 279 | (two `live` stubs inside) |
| `src/interact.rs` | 79 | |
| `src/live.rs` | 501 | `live` |
| `src/pipe.rs` | 497 | |
| `src/present.rs` | 207 | |
| `src/sandbox.rs` | 174 | (`target_os` inside) |
| `src/session.rs` | 238 | |
| `src/slice.rs` | 48 | `slice` |
| `src/source.rs` | 66 | |
| `src/write_text.rs` | 874 | `write-text` |

Public paths and importers. Everything in every module is `pub`; the only narrower items are the two `pub(super) fn apply` of `sandbox::platform`. The crate's one consumer is `neoteletext-cli`; the browser does not depend on it (its only mention is a doc comment at `native/protocol/src/decoder.rs:105`). The CLI's imports: `main.rs:22, 54, 463` (`exit`, `sandbox`, `session::DEFAULT_PAGES`, `not_in_build`); `commands.rs:8-12, 449, 464, 476` (`Failure`, `input::{self, Options}`, `sandbox::{self, Policy}`, `session::Session`, `convert`, `exit`, `slice::slice`, `fetch::run`, `live::descriptor_service_names`); `contents.rs:10-13`, `font.rs:6-7`, `sound.rs:9-13`, `write_text.rs:6-10` (`input`, `sandbox`, `session`, `Failure`, `exit`, `write_text::write_text`); `keyboard.rs:9, 24` (`exit`, `pipe::MAX_INPUT_MESSAGE`); `options.rs:6` (`input::Options`); `output/image.rs:10-11` (`present`, `present::{Raster, Scale}`); `output/text.rs:9-10` (`present::{MosaicStyle, plain, cell_text, row_cells}`); `view.rs:14-18` (`extras::{self, PageExtras}`, `interact::{ActiveForm, message_row, origin_of, submission}`, `pipe::Notice`, `session::Session`, `source::Source`); `tests/typing.rs:17` (`pipe::{self, Frame, Notice, Origin}`). No fuzz target imports it.

### 1.2 `neoteletext-cli` (24 files, 4,950 lines: 15 source files of 3,850 lines, 9 integration tests of 1,100)

The `neottx` program: arguments, terminal output, the terminal viewer, and the authoring commands. A binary only (`[[bin]] neottx = src/main.rs`): nothing imports it, and its public surface is the command line, pinned by the integration tests.

Features: `default = ["view", "live", "slice", "write-text", "sound", "keyboard"]`. `view` brings `crossterm` and `unicode-normalization`; `live`, `slice`, `write-text` forward to `neoteletext-app`; `sound` brings `neoteletext-audio` with `encode`; `keyboard` brings `neoteletext-qrkeyboard` and `unicode-normalization`; `objects`, `side-panels`, `additional-flash-functions` forward to the core.

| File | Lines | Gate |
|---|---|---|
| `src/main.rs` | 549 | |
| `src/commands.rs` | 540 | (stubs for `view`, `slice`, `live` inside) |
| `src/contents.rs` | 226 | |
| `src/font.rs` | 148 | |
| `src/keyboard.rs` | 335 | `keyboard` |
| `src/nfc.rs` | 51 | `any(view, keyboard)` |
| `src/options.rs` | 97 | |
| `src/output/mod.rs` | 5 | |
| `src/output/cells.rs` | 112 | |
| `src/output/image.rs` | 207 | (`view` inside) |
| `src/output/text.rs` | 266 | |
| `src/sound.rs` | 309 | (`sound` on 17 items inside) |
| `src/terminal.rs` | 90 | (`view` inside) |
| `src/view.rs` | 866 | `view` |
| `src/write_text.rs` | 49 | (`write-text` on 8 items inside) |
| `tests/typing.rs` | 248 | `live` |
| `tests/sound.rs` | 212 | `sound` |
| `tests/font.rs` | 130 | |
| `tests/web.rs` | 120 | `live` (two tests `view`) |
| `tests/write_text.rs` | 87 | `write-text` |
| `tests/level25_corpus.rs` | 86 | |
| `tests/not_in_build.rs` | 76 | per test, `not(feature)` |
| `tests/enhancement_reporting.rs` | 76 | |
| `tests/contents.rs` | 65 | |

### 1.3 `neoteletext-audio` (11 files, 3,395 lines: 10 source files of 2,905, one integration test of 490)

The audio profile (area AUD): record frames and bodies, carriage on EN 300 708 data lines, the compressed sound store, per-channel command state, IMA ADPCM, and the receiver that turns records into `VoiceSink` operations. `#![no_std]`, no allocation except under `encode`. The crate root carries the eight-lint panic deny list (`lib.rs:18-27`). Its only dependency is `neoteletext-core`.

Features: `default = ["idl", "ima"]`; `idl` is the carriage, `ima` the decoder, `encode = ["ima", "idl"]` the publishing side with `alloc`.

| File | Lines | Gate |
|---|---|---|
| `src/lib.rs` | 187 | |
| `src/control.rs` | 106 | |
| `src/crc.rs` | 86 | |
| `src/encode.rs` | 281 | `encode` |
| `src/idl.rs` | 374 | `idl` |
| `src/ima.rs` | 211 | `ima` (`encode` fn inside) |
| `src/port.rs` | 82 | |
| `src/receiver.rs` | 469 | (nine `cfg` inside for `idl` and `ima`) |
| `src/record.rs` | 491 | |
| `src/store.rs` | 618 | |
| `tests/receiver.rs` | 490 | `encode` |

Public paths and importers:

| Importer | Paths |
|---|---|
| `neoteletext-input` (`idl` feature) | `idl::{fragment, packet, FRAGMENT_DATA}` (`control.rs:9-10`, `cursor.rs:23`, `lib.rs:85`); `record::{RecordError, framed_length, record_length, split, write, TYPE_CURSOR, TYPE_INPUT_CONTROL, is_input_type}` (`control.rs:11-12`, `cursor.rs:24-25`, `lib.rs:88`) |
| `neoteletext-cli` (`sound`) | `Codec`, `encode::{Command, Sound, packets}`, `record::FLAG_LOOP`, `CHANNELS`, `MAX_GAIN`, `IMA_BLOCK_LARGE`, `IMA_BLOCK_SMALL`, `MAX_PCM_BLOCK`, `SAMPLE_RATES` (`sound.rs:15-17, 77-78, 90-91, 96, 114`); `tests/sound.rs:11-12` `port::{SoundFormat, SoundId, Start, VoiceSink}`, `receiver::Receiver` |
| fuzz `audio_packets` | `port::*`, `receiver::Receiver`, `crc::crc16_idl` |
| fuzz `audio_records` | `port::*`, `receiver::Receiver`, `crc::crc32`, `PROFILE_VERSION`, `MAX_BLOCK_SAMPLES`, `SAMPLE_RATES`, `CHANNELS`, `MIN_FADE_MS` |
| browser `decoder/src/lib.rs:70-71, 1266-1316` | `port::*`, `receiver::Receiver`, `encode::*`, `Codec::Pcm16`, `LIVE_STALL_FADE_MS` |
| browser `protocol/src/audio.rs:8` | `CHANNELS`, `DUCK_PERCENT`, `MAX_FADE_MS`, `MAX_GAIN`, `MIN_FADE_MS`, `SAMPLE_RATES` |
| browser `site/src/terminal.rs:32-33, 1390-1457` | `Codec`, `encode::*`, `receiver::Receiver`, `port::{VoiceSink, SoundFormat, SoundId, Start}` |
| browser `site/src/podcast.rs:13, 275-276` | `encode::*`, `port::*`, `receiver::Receiver` |

The browser pins the crate with features `["idl", "ima"]` (`native/Cargo.toml:59`); `decoder` (dev) and `site` add `encode`.

### 1.4 `neoteletext-audio-mix` (2 files, 839 lines)

The software mixer for ports with an operating-system audio output (REQ-AUD-019): four voices, fixed-point ramps, ducking in Table 19's steps, windowed-sinc resampling, and live-stream buffering with rate trim. `#![no_std]` with `alloc`; `render` never allocates. The crate root carries the panic deny list (`lib.rs:15-24`). No dependencies; a dev-dependency on `neoteletext-audio` that no test uses. No features.

| File | Lines |
|---|---|
| `src/lib.rs` | 757 |
| `src/sinc.rs` | 82 (generated table) |

Importers: the browser only, `native/sound/src/audio.rs:34` `neoteletext_audio_mix::{Mixer, SoundKey, Start}`. Nothing in the engine, no fuzz target.

### 1.5 `neoteletext-input` (11 files, 3,245 lines, no integration tests)

The input system of `INPUT.md` version 2: the receiver-to-channel stream over varint primitives, the functional key codes and the frozen W3C name table, capabilities and the mode stack, the receiver's session (handshake, filtering by mode, rate limit, input count and acknowledgement), the channel's cursor and control records, held-key release at the channel, and decimal digits of any script. `#![no_std]`, no allocation, no features. The crate root carries the panic deny list (`lib.rs:20-29`). Dependencies: core and audio (`idl`).

| File | Lines |
|---|---|
| `src/lib.rs` | 97 |
| `src/control.rs` | 272 |
| `src/cursor.rs` | 260 |
| `src/digits.rs` | 55 |
| `src/event.rs` | 792 |
| `src/held.rs` | 150 |
| `src/keys.rs` | 313 |
| `src/modes.rs` | 155 |
| `src/names.rs` | 191 |
| `src/session.rs` | 680 |
| `src/wire.rs` | 280 |

Public paths and importers:

| Importer | Paths |
|---|---|
| `neoteletext-cli` `view.rs` | `modes::{PAGE_CAP, ALL_KEYS, KEY_RELEASE}`, `event::{Item, Event, Key, KeyCode, Action, SHIFT, CONTROL, ALT, printable, write}`, `keys::code`, `session::{Session, State}`, `control::{FRAGMENT_DATA, from_packet}`, `cursor::from_packet`, `MAX_MESSAGE`, `MAX_ROWS`, `MAX_PASTE`, `is_input_packet` |
| `neoteletext-cli` `keyboard.rs` | `event::{Action, Event, Item, Key, KeyCode, printable, write}`, `modes::{ALL_KEYS, KEY_RELEASE, ALL_MODES}`, `session::{SendError, Session, State}`, `MAX_MESSAGE`, `MAX_ROWS`, `WELCOME_TIMEOUT_MS`, `control`, `keys` |
| `neoteletext-cli` `nfc.rs`, `tests/typing.rs` | `event::{Event, Item, Key}`; `MAX_MESSAGE`, `event::{Item, write}` |
| fuzz `control_records` | `control::{FRAGMENT_DATA, MAX_BODY, from_packet, packet_of, read_body, write_body}` |
| fuzz `cursor_records` | `cursor::{BODY, from_body, from_packet}` |
| fuzz `input_stream` | `MAX_MESSAGE`, `event::{MAX_STREAM_ITEM, StreamDecoder, read_message, write}` |
| browser `core/src/typing.rs` | `control::{..., PAGE_MODES, MAX_BODY, write_body}`, `cursor::`, `event::`, `modes::`, `session::{..., REMEMBERED}`, `MAX_PER_SECOND` |
| browser `core/tests/latency.rs` | `control::`, `event::{..., write}`, `modes::PAGE_CAP`, `session::Session`, `MAX_MESSAGE` |
| browser `decoder/src/lib.rs` | `cursor::{BODY, from_packet}`, `is_input_packet`, `control::{Control, MAX_BODY, write_body}`, `modes::MOUSE_BUTTONS` |
| browser `interface-core/src/input.rs`, `browser.rs`, `browser/terminal_ui.rs` | `event::`, `event::MouseAction`, `cursor::`, `modes::`, `MAX_KEY_TEXT` |
| browser `interface/src/keys.rs`, `main.rs` | `event::`, `keys`, `event::Action` |
| browser `keyboard/src/keyboard.rs` | `session::Limiter` |
| browser `protocol/src/decoder.rs`, `interaction.rs` | `cursor::BODY`, `control::MAX_BODY`, `cursor`, `event::`, `modes::{ALL_MODES, MOUSE_BUTTONS}` |
| browser `site/src/terminal.rs`, `websocket.rs` | `control::`, `cursor::`, `digits::decimal_digit`, `event::`, `keys`, `modes::`, `VERSION`, `MAX_MESSAGE` |
| browser fuzz `input_records`, `fetcher_commands` | `control::MAX_BODY`, `cursor::BODY`, `modes::ALL_MODES`; `MAX_MESSAGE`, `event::read_message` |

### 1.6 `neoteletext-qrkeyboard` (13 files, 3,209 lines: 10 source files of 2,873, three integration tests of 336)

The screen's side of qrkeyboard protocol 3: configuration and its hash, AES-256-GCM sealed frames and SPAKE2 for a PIN, one pairing run, the application messages, HTTP and WebSocket connections with TLS, the screen's state machine, a phone for tests, and the QR as mosaics. A `std` crate (decision E.94); the crate root carries the panic deny list (`lib.rs:23-32`). Dependencies: `neoteletext-web` (`std`), `rustls`, `webpki-roots`, `aes-gcm`, `hkdf`, `hmac`, `sha2`, `p256`, `getrandom`, `qrcodegen`. No features.

| File | Lines |
|---|---|
| `src/lib.rs` | 101 |
| `src/config.rs` | 189 |
| `src/crypto.rs` | 369 |
| `src/json.rs` | 244 |
| `src/message.rs` | 242 |
| `src/net.rs` | 613 |
| `src/pairing.rs` | 199 |
| `src/phone.rs` | 178 |
| `src/qr.rs` | 152 |
| `src/screen.rs` | 586 |
| `tests/wake.rs` | 141 |
| `tests/relay.rs` | 99 (needs `QRKEYBOARD_RELAY`) |
| `tests/socket.rs` | 96 |

Importers: `neoteletext-cli` `keyboard.rs:16-19` (`config::{Layout, ScreenConfig}`, `net::{self, Incoming, WebSocket}` and `net::parse`, `qr::{Correction, Matrix}`, `screen::{Event, Screen}`); browser `keyboard/src/keyboard.rs:9-11, 139, 183` (`config::`, `qr::`, `screen::`, `RELAY`), `site/src/terminal.rs:1059-1061` (`config::`, `qr::`, `screen::`), browser fuzz `relay_messages.rs:8-11` (`json::Value::parse`, `message::read`, `message::from_base64url`). No engine fuzz target.

### 1.7 `xtask` (10 files, 1,969 lines)

| Task | Module | Lines | What it does |
|---|---|---|---|
| `glyphs` | `glyphs.rs` | 367 | Regenerates the core's Bedstead table, the G3 text and source, `required.txt`, `forms.txt` |
| `check-bedstead` | `glyphs.rs` | | Bedstead export against its recorded SHA-256 |
| `corpus` | `corpus.rs` | 72 | Fetches and pins the broadcast corpus with `curl` and `shasum` |
| `traceability` | `trace.rs` | 181 | Writes `docs/traceability.md` |
| `check-layers` | `checks.rs` | 316 | Core module dependency table (REQ-ARCH-011) |
| `check-deps` | `checks.rs` | | Permitted dependencies per crate; application crates use only crates below them |
| `check-constants` | `checks.rs` | | Teletext literals outside `consts` |
| `check-io` | `checks.rs` | | Operating-system access in library crates; every crate classed |
| `level25-stream` | `level25.rs` | 44 | Writes the authored Level 2.5/3.5 stream |
| `check-noto` | `noto.rs` | 61 | Noto-derived fonts against their record |
| `features` | `features.rs` | 89 | Lints and tests the 42 fixed feature builds |
| `size` | `size.rs` | 289 | Links the firmware image per build; flash, static RAM and forbidden symbols |
| `g3` geometry | `g3.rs` | 474 | The G3 shapes `glyphs` draws from |
| dispatch | `main.rs` | 76 | |

`scripts/check.sh` orchestrates: fmt, clippy, tests, the four checks and the two font checks in `fast`; in `full`, the bare-metal build of the eight `no_std` crates, `features`, `size`, release tests, Rosetta tests, machete, deny and the remote stages. No logic is in both.

### 1.8 The fuzz targets (21, 847 lines; outside the workspace, nightly only)

`fuzz/Cargo.toml` depends on core, formats (`default`, `std`), slicer, web (`default`, `dbsc`), audio and input. None imports `app`, `cli`, `qrkeyboard` or `audio-mix`.

| Target | Imports |
|---|---|
| `address` | `neoteletext_web::url::Url` |
| `audio_packets` | `neoteletext_audio::{port::{SoundFormat, SoundId, Start, VoiceSink}, receiver::Receiver, crc::crc16_idl}`; core `consts`, `ecc::hamming84_encode`, `packet::Packet` |
| `audio_records` | `neoteletext_audio::{port::*, receiver::Receiver, crc::crc32, PROFILE_VERSION, MAX_BLOCK_SAMPLES, SAMPLE_RATES, CHANNELS, MIN_FADE_MS}` |
| `bdf` | `neoteletext_formats::bdf::read`; core `consts`, `types::FontGlyph` |
| `bdf_convert` | `neoteletext_formats::bdf::{read, convert, source}`, `write::{FontText, write_font}` |
| `channel_log` | `neoteletext_formats::{log, tti::TtiReader, Item, Reader}` |
| `control_records` | `neoteletext_input::control::{FRAGMENT_DATA, MAX_BODY, from_packet, packet_of, read_body, write_body}` |
| `cookie` | `neoteletext_web::cookie::{CookieJar, parse_cookie_date}` |
| `cursor_records` | `neoteletext_input::cursor::{BODY, from_body, from_packet}`; core `packet::Packet` |
| `dbsc` | `neoteletext_web::dbsc::*` |
| `descriptor` | `neoteletext_web::{descriptor::Descriptor, url::Url}` |
| `enhancement` | core `acq`, `config`, `consts`, `enhance::MAX_WALK_STEPS`, `glyphs`, `level1`, `packet`, `render`, `types`, `compose` |
| `formats` | `neoteletext_formats::{Item, detect, item::Reader, sliced, t42, transport}` |
| `http` | `neoteletext_web::http::{BodyDecoder, Framing, HeadCollector, parse_head}` |
| `input_stream` | `neoteletext_input::{MAX_MESSAGE, event::{MAX_STREAM_ITEM, StreamDecoder, read_message, write}}` |
| `packets` | core `acq`, `config`, `consts`, `fsm`, `glyphs`, `level1`, `level15`, `packet`, `render`, `types` |
| `proxy` | `neoteletext_web::{http::HeadCollector, proxy::*}` |
| `slicer` | `neoteletext_slicer::{Config, Preset, RawGeometry, RawReader}` |
| `sse` | `neoteletext_web::sse::SseParser` |
| `tti_enhancement` | core `packet::decode`; `neoteletext_formats::{Item, encode::encode_page, item::Reader, page::PageFile, tti::TtiReader, write::write_tti}` |
| `websocket` | `neoteletext_web::ws::FrameReader` |

### 1.9 The firmware image and `tests/`

| Item | What it is |
|---|---|
| `firmware/test-image/src/main.rs` (253) | The linked microcontroller image `cargo xtask size` measures: `no_std`, `no_main`, its own panic handler, one `#[used]` function pointer per entry point, feature-gated modules per area. Depends on core, formats and web with default features off; nothing in this document is linked into it. |
| `tests/corpus-manifest.txt` | REQ-TST-022 pins read by `xtask corpus`. |
| `tests/golden/` | `authored-level25.txt`, `raster-level25.txt`, `raster.txt`. |
| `tests/oracles/` | zvbi comparison programs and scripts run against `neottx text --cells`. |
| `tests/pages/` | `level25/`, `testcard.tti`. |
| `tests/web-server/` | `server.py`, `drive_viewer.py`, `drive_offline.py`, driven by `neoteletext-cli/tests/web.rs`. |

---
## 2. Findings

### 2.1 File by file

Line ranges are those of the files at `fb2dd8a`. "Mixes" lists the distinct responsibilities a file holds.

**`neoteletext-app`**

| File | Contents (line ranges) | Mixes | Tests |
|---|---|---|---|
| `lib.rs` | `mod` lines 14-30; `exit` consts 32-42; `Failure` 44-45; `not_in_build` 47-52 | one | — |
| `source.rs` | `Wake` 10-12; `trait Source` 14-57; `Finished` 59-66 | one | — |
| `slice.rs` | `slice` 14-48: preset-name strings 15-22, slicer loop and T42 writer | preset names belong with arguments; the loop is the command | — |
| `interact.rs` | `ActiveForm` 10-22; `message_row` 24-33; `origin_of` 35-42; `submission` 44-65 | one | 12 inline |
| `sandbox.rs` | `Policy` 11-21; `apply` 23-30; Linux `mod platform` 32-139 (`landlock` 47-69, `seccomp` 91-131); other `mod platform` 141-158; `self_test` 160-174 | policy and dispatch; the Linux mechanism; the self-test | — |
| `present.rs` | `MosaicStyle` 21-28; `visible`, `cell_text`, `row_cells`, `plain` 30-95; `Raster`, `Scale`, `raster` 97-153; `receiver_grid` 155-188 | text output; raster output; a receiver-drawn page built through acquisition types | 18 inline |
| `session.rs` | consts 18-51; `Session` 30-42; `impl` 53-238 (`new`, `keep`/`take_kept`/`maybe_keep` 74-92, `push` 111-126, `push_at` 128-140, `tick` 142-153, `finish` 155-165, `pages`, `service`, `page`, `grid` 188-218, `print_trace` 220-226, `rolling_header`) | the session; the kept-packet sidecar; trace printing | — |
| `input.rs` | `Options` 18-57; `config` 62-83; `is_live` 85-92; `live_source` ×2 94-104; `load_live` 106-143; `open` 145-156; `pump` 158-170; `reader` 172-182; `load`, `load_for` 184-251; `region_for_language` 253-268; `open_live` 270-279 | options; configuration; file reading and pumping; live collection; the language table | — |
| `extras.rs` | `PageExtras` 15-37; consts 39-42; `Destination`, `TextLinkExtras` 44-64; `impl` 66-84; `destination` 86-97; `from_page` 99-158; `draw_marks` 160-167; `fixed`, `number`, `form_spec` 169-254; `key` 256-260 | link extras; drawing marks on a grid; form specification conversion | 27 inline |
| `convert.rs` | consts 28-32; `page_file` 34-74; `push_line`, `page_packets`, `enhancement_function` 76-134; `enhancement_page_file` 136-164; `magazine_page_file` 166-182; `session_page_files` 184-209; `Target` 211-218; `convert` 220-256 | pure page-file export; the command with its file I/O | 108 inline |
| `pipe.rs` | consts 8-14; `Origin`, `PageData`, `Submission`, `Frame`, `Notice` 16-127; kind bytes 129-157; `put*` 159-180; `Cursor` 182-224; `page_payload`, `page_data` 226-253; `write` 255-323; `read` 325-403; `notice_frame` 405-426 | the message model; the wire codec | 69 inline |
| `live.rs` | `Live` 23-55; `Fill` 57-79; consts 81-92; `open` 94-122; `read_frames` 124-140; `routed` (test) 142-147; `impl Live` ×3 149-170, 172-226, 362-384; `impl Source` 228-360; `Drop` 386-393; `descriptor_service_names` 395-404 | process spawning and the pipe reader; the fill policy; the `Source`; a descriptor reader for `neottx check` | 95 inline |
| `fetch.rs` | consts 19-30; `Wake` 32-43; `Connection`, `StdTransport` 45-68; `slot`, `web_address`, `blocked` 70-90; `impl StdTransport` 92-185; `read_socket` 187-207; `Refill`, `refill` 209-229; `write_records` 231-238; `impl Connection` 240-275; `Transport` impls 277-332; `SystemRandom` 334-342; `send` 344-347; `requests` 349-366; `Wakes` 368-439; `page_request` 441-443; `CHANNEL_PREFIX` 445-447; `run` 449-477; `neottx` 479-489; `clock` 491-493; `run_zxnet` 495-505; `live_loop` 507-591; `run_web` 593-797 | the std socket, TLS and proxy transport; the random source; the pipe to the decoder; wake plumbing; entry and sandbox; the zxnet loop; the web-agent loop | 272 inline, two unrelated groups |
| `write_text.rs` | `SETS` 38-87; Thai/Lao consts 89-111; Arabic consts 113-121; row consts 123-132; `WriteError` 134-173; `set_names`, `Written` 175-190; `Cell` 192-199; `Sets` 201-245; `stand_in`, `switch`, `encode` 247-311; `break_line` 313-347; `visual`, `break_line_rtl` 349-406; `MarkedLine`, `mark_cell`, `clusters`, `marked_lines`, `mark_row`, `marked_rows` 408-550; `page_sets` 552-565; `write_text` 567-650 | the set table; cell encoding; Latin breaking; right-to-left ordering and breaking; Thai and Lao layout; page building | 221 inline |

**`neoteletext-cli`**

| File | Contents | Mixes | Tests |
|---|---|---|---|
| `main.rs` | `mod` lines 6-19; `Cli` 26-32; `Common` 34-86; `ParityChoice`, `LevelChoice`, `GraphicsChoice` 88-125; `RasterArgs` 127-143; `Command` 145-396 (20 variants); `main` 398-477; `FontCommand` 479-513 | the argument schema; dispatch; building `SoundOptions`/`KeyboardOptions` inline (451, 458-459) while `Common`'s conversion lives in `options.rs` | 34 inline |
| `options.rs` | `FormatChoice` 13-65; `impl Common { options }` 67-97 | one, but the three value enums are split across two files | — |
| `commands.rs` | `ImageFormat`, `ConvertTarget`, `Selection` 29-65; `parse_selection` 67-87; `selected`, `grid_of`, `sandbox` 89-116; `list` 118-179; `mosaic_style`, `text`, `display`, `scale_for` 181-220; `show` 222-268; `view` + stub 270-304; `page_file_name` 306-310; `render` 312-363; `service_info` 365-400; `services` 402-428; `convert` 430-444; `slice` + stub 446-458; `fetch` + stub 460-471; `descriptor_service_names` + stub 473-484; `check` 486-522 | eleven commands and their shared helpers, while five other commands have files of their own | 16 inline |
| `view.rs` | `Wakened`, `next_event` 39-54; `TICK`, `TICKER_STEP_US` 56-60; `map_key` 62-85; `map_form_key` 87-108; `LEAVE_TYPING`, `OFFERED` 110-118; `input_of` 120-177; `Typing` 179-201; `host_page` 203-208; `impl Typing` 210-303; `RawGuard` 305-320; `Pending` 322-326; `origin_ticker` 328-357; `run` 359-746; `draw` 748-770 | terminal wait plumbing; three key mappers; the typing-back session; the raw-mode guard; the status ticker; the loop with seven sub-concerns; drawing | 94 inline |
| `keyboard.rs` | two `const _` assertions 21-28; `OFFERED` 30-32; consts 34-40; `type Failure` 42; `page_number` 44-49; `qr_page` 51-80; `qr` 82-86; `KeyboardOptions` 88-102; `Channel` 104-232; `terminal_qr` 234-245; `keyboard` 247-308 | `neottx qr`; the input-session channel bridge; terminal QR drawing; `neottx keyboard`; two crate-wide invariants compiled only with this feature | 25 inline |
| `sound.rs` | 17 `cfg` attributes; consts 24-38; `SoundOptions` 40-63; `sound` 65-160; `live_packets` 162-208; stub 210-214; `Wave`, `read_wave` 216-268 | option validation and command I/O; the live pacing algorithm; the WAVE reader; the stub | 39 under `cfg(all(test, feature))` |
| `output/text.rs` | re-exports 9; `ColourDepth` 17-24; `nearest_of_eight`, `colour_of` 26-40; `Style` 42-104; `ansi` 106-128 | one (ANSI) | 136 inline, four of them testing `app::present::plain` |
| `contents.rs` | consts 22-25; `Found`, `Loaded` 27-41; `civil_date`, `date` 43-67; `title_text`, `first_line`, `description` 69-91; `load` 93-128; `contents` 130-206 | civil-date arithmetic; title extraction; the command | 18 inline |
| `output/image.rs` | `BEDSTEAD` 20-21; `Frame` 23-52 (`at` under `view`); `raster`, `raster_in` 54-65; `png`, `ppm` 67-96; `base64` 98-120; `iterm2_inline` 122-134 | the frame timing type; the encoders; base64 and the iTerm2 escape | 71 inline |
| `font.rs` | `read_bounded` 22-32 (`pub(crate)`, also used by `sound.rs` and `write_text.rs`); `convert_font` 34-73; `read_table` 75-87; `font_sets` 89-124; `source_fault`, `conversion_fault` 126-148 | a shared bounded file read; two font subcommands; error wording | — |
| `output/cells.rs` | `character`, `size`, `flags`, `cells` 25-93 | one | 17 inline |
| `terminal.rs` | `Display` 4-11; `detect` 13-28; `TextArea` 30-40; `text_area` + stub 42-58; `fit_scale` 60-73 | one | 15 inline |
| `nfc.rs` | `nfc`, `with_nfc` 12-27 | one | 22 inline |
| `write_text.rs` | 8 `cfg` attributes; `TEXT_MAX_FILE_BYTES` 16-21; `write_text` 23-43; stub 45-49 | one | — |
| `output/mod.rs` | three `pub mod` lines | the one `mod.rs` in this scope | — |

**`neoteletext-audio`**

| File | Contents | Mixes | Tests |
|---|---|---|---|
| `lib.rs` | attributes 14-27; `mod` lines 34-45; fifteen profile consts 47-85; `Codec` 87-146; IMA size consts 148-158; `SAMPLE_RATES`, `sample_rate`, `rate_code` 160-173; `DUCK_PERCENT` 175-178; `serial_newer` 180-187 | the profile's constants; the codec type and rate tables; serial arithmetic, all in the root | — |
| `store.rs` | `Entry` 10-94; `Defined`, `Stored` 96-135; `Store` 137-142; `impl` 144-467 (`define` 211-295, `find_space` 297-317, `set_live_cursor`, `live_block`, `slot_index` 319-349, `put_live` 353-407, `put` 410-466) | the entry model; arena allocation and eviction; static block storage; the live ring | 148 inline |
| `record.rs` | type consts 12-33; field and flag consts 35-63; `RecordError` 65-82; `Object`, `Data`, `Operation`, `Control`, `Record` 84-168; `framed_length`, `record_length`, `split`, `write` 170-238; `parse`, `object`, `control` 240-343; `Fields` 345-383 | the frame shared with the input profile; the three audio bodies | 105 inline |
| `receiver.rs` | `Statistics` 19-38; `Receiver` 40-52; `impl` 54-435 (`tick` 74-96, `push_packet` 161-185 under `idl`, `push_record` 188-228, `open_page` 231-250, `set_page_sounds` 252-271, `command` 273-307, `try_start` 310-355, `start_waiting`, `start_armed`, `buffered_ms` 357-381, `send_sound`, `send_live`, `send_block` 383-434); `decode` 437-454; `bump`, `needs`, `duration_ms` 456-469 | carriage intake; record dispatch; command and page-sound policy; starting plays; sending samples with codec dispatch | — (integration) |
| `idl.rs` | consts 23-35; `Fragment`, `IdlError` 37-67; `is_audio`, `fragment`, `packet`, `read` 69-163; `Slot`, `Reassembler` 165-263 | the fragment codec; reassembly | 108 inline |
| `encode.rs` | `Sound`, `EncodeError` 13-47; `impl Sound` 49-185; `ima_blocks` 187-210; `Command` 212-254; `frame`, `packets` 256-281 | one (publishing) | — |
| `ima.rs` | tables and consts 12-34; `ImaError`, `State` 36-78; `decode_block` 80-111; `encode` 113-135 under `encode` | one | 73 inline |
| `control.rs`, `crc.rs`, `port.rs` | one concept each | | 26, 24, — inline |

**`neoteletext-audio-mix`**: `lib.rs` holds the attributes 12-28, the consts 36-61, `Ramp` 63-97, `Sound` 99-137, `Playing` 139-161, `Start` 163-178, `Voice` 180-188, `Mixer` 190-198, `impl Mixer` 200-508 (`stream_samples` 257-275, `start` 304-320, `render` 358-370, `voice_sample` 374-440, `update_ducks` 444-469, `trim_streams` 475-495, `collect` 498-507), `begin` 510-536, `set_step`, `advance`, `interpolate`, `level`, `scale` 538-573, tests 575-757. Mixes the fixed-point ramp; sound storage, static and live ring; voice state and stepping; the mixer API; rendering with resampling, ducking and stream trim. The tests read private fields (`mixer.voices`, `mixer.sounds` at 691-692, 745).

**`neoteletext-input`**

| File | Contents | Mixes | Tests |
|---|---|---|---|
| `lib.rs` | attributes 16-29; `mod` lines 34-43; consts 45-65; two `const _` 67-71; `LAST_ADDRESSABLE_PAGE` 73-76; `is_input_packet` 78-90; `is_page` 92-97 | one | — |
| `event.rs` | type, flag and modifier consts 14-76; `Action`, `KeyCode`, `Key`, `MouseAction`, `Point`, `Mouse`, `Wheel`, `Event`, `Item`, `InputError` 78-248; `printable`, `check_text`, `units` 250-269; `read`, `read_text`, `read_point`, `read_event`, `read_key` 271-433; `write`, `write_point`, `point_flags`, `write_event` 435-564; `read_message` 566-585; `StreamDecoder`, `MAX_STREAM_ITEM` 587-640 | the event model; the decoder; the encoder; message and stream framing | 149 inline |
| `session.rs` | consts 16-22; `State`, `WelcomeError`, `SendError` 24-65; `serial_after` 67-72; `Session` 74-92; `impl` 94-390 (`open` 135-141, `welcome` 153-168, `control` 175-192, `send` 226-255, `filter` 259-318, `allow` 324-334, `sent` 338-351, `acknowledged` 368-383); `Limiter` 392-431 | handshake; mode filtering; the rate limiter; the count and acknowledgement ring | 246 inline |
| `keys.rs` | `FIRST_NAMED` 15-16; `ONE_BYTE` table 18-149; `code`, `name`, `is_code`, `unidentified` 151-185; modifier sets, `is_modifier`, `is_dead` 187-209; `remaining` 211-214; `us_base` 216-246 | the code table and its lookups; the United States layout map | 64 inline |
| `control.rs` | re-exports 9, 11; consts 20-31; `Control`, `ControlError` 33-82; `read_body` 84-136; `write_body` 138-179; `packet_of`, `read`, `from_packet` 181-223 | the body codec; the record and packet wrappers | 46 inline |
| `cursor.rs` | consts 31-47; `Place`, `Cursor` 49-117; `read`, `from_body`, `from_packet` 119-186 | one, with the same wrappers as `control.rs` | 71 inline |
| `wire.rs`, `modes.rs`, `held.rs`, `digits.rs`, `names.rs` | one concept each | | 59, 48, 53, 19, 12 inline |

**`neoteletext-qrkeyboard`**

| File | Contents | Mixes | Tests |
|---|---|---|---|
| `lib.rs` | attributes 23-32; `mod` lines 34-42; consts 44-56; `Error` 58-93; `random` 95-101 | one | — |
| `net.rs` | consts 23-37; `OsRandom` 39-47; `tls_config` 49-57; `Stream` 59-191 (`connect` 73-119); `parse` 193-199; `request` 201-276; `host_header` 278-282; `Incoming` 284-293; `Wake`, `Waker`, `later` 295-336; `read_socket` 342-367; `Reading` 369-436; `write_records` 438-445; `WebSocket` 447-616 (`connect` 463-521, `receive` 556-597) | the TCP/TLS stream; the HTTP client; wake plumbing; the reader thread and TLS pump; the WebSocket client | — (integration) |
| `screen.rs` | consts 19-43; `Join`, `Event` 45-88; `Screen` 90-115; `is_code` 117-119; `impl` 121-573 (`create` 128-202, `wait` 245-277, `next_deadline` 281-289, `turn` 293-331, `control` 351-374, `peer_up` 376-395, `binary` 419-481, `has_key` 494-534 with five inline key tables, `finish` 548-563) | instance creation; the wait scheduler; relay control text; pairing drive; application messages and acknowledgements; layout key tables | 11 inline |
| `crypto.rs` | consts 25-48; `Role` 50-57; `hkdf`, `directional_keys`, `nonce` 59-85; `Sealer`, `Opener` 87-146; `constant_time_equal` 148-153; point helpers, `password_scalar`, `random_scalar`, `length_prefixed` 155-209; `Spake2`, `Spake2Result` 211-281 | sealed frames; SPAKE2 | 85 inline |
| `message.rs` | consts 10-33; `FromPhone`, `Message` 35-66; `is_id`, `read`, `pack`, `ack`, `new_id` 68-138; `base64url`, `from_base64url` 140-182 | the message model; base64url | 57 inline |
| `config.rs`, `json.rs`, `pairing.rs`, `phone.rs`, `qr.rs` | one concept each | | 44, 23, 56, 12, 33 inline |

**`xtask`**: `checks.rs` holds four checks with their tables (`LAYER_TABLE` 12-38, `PERMITTED` 118-127, `APPLICATION_CRATES` 186-208, `DATA_FILES`/`WATCHED_LITERALS` 212-215, `LIBRARY_CRATES`/`FORBIDDEN` 256-267) and the shared `rust_files` 40-50, `non_test_source` 52-62, `report` 306-316. `g3.rs` holds the geometry engine 27-233, the Table 48 shape list `shape` 236-343 and `text` 378-399. `glyphs.rs` holds the Bedstead table 45-94, `g3_source` 98-147, `sets`/`required`/`forms_text` 150-268, `check_bedstead` 270-295, `generate` 298-317. `size.rs` holds the size gate and an ELF reader `read_elf` 197-264. `trace.rs` has one 93-line function. The rest are one concept each.

### 2.2 Size outliers

Functions over 80 lines: `cli/src/view.rs:361-746 run` (386, `#[allow(clippy::too_many_lines)]`); `app/src/fetch.rs:595-797 run_web` (203, allowed); `xtask/src/g3.rs:236-343 shape` (108, allowed, one arm per Table 48 position); `cli/src/sound.rs:67-160 sound` (94); `xtask/src/trace.rs:89-181 generate` (93); `input/src/event.rs:478-564 write_event` (87); `audio/src/store.rs:211-295 define` (85); `app/src/fetch.rs:509-591 live_loop` (83). Just under: `main.rs main` (80), `pipe.rs read` (78, its tail cut off into `notice_frame` to stay under clippy's 100), `write_text.rs write_text` (78), `live.rs poll` (77), `contents.rs contents` (76), `screen.rs create` (75).

`impl` blocks over 300 lines: `screen.rs:121-573 impl Screen` (453); `receiver.rs:54-435 impl Receiver` (382); `store.rs:144-467 impl Store` (324); `audio-mix lib.rs:200-508 impl Mixer` (309). Near: `session.rs:94-390 impl Session` (297).

Files over 500 lines: `fetch.rs` 1,071; `write_text.rs` 874; `view.rs` 866; `event.rs` 792; `audio-mix lib.rs` 757; `session.rs` 680; `store.rs` 618; `net.rs` 613; `screen.rs` 586; `main.rs` 549; `commands.rs` 540; `live.rs` 501.

### 2.3 Mixed responsibilities

| File | Responsibilities |
|---|---|
| `app/src/fetch.rs` | 7: transport; random source; pipe to the decoder; wake plumbing; entry and sandbox; zxnet loop; web-agent loop |
| `cli/src/view.rs` | 8: wait plumbing; three key mappers; typing-back session; raw-mode guard; ticker; the loop; drawing |
| `app/src/write_text.rs` | 6: set table; cell encoding; Latin breaking; right-to-left; Thai and Lao; page building |
| `qrkeyboard/src/screen.rs` | 6: creation; wait scheduler; relay control; pairing drive; messages; layout tables |
| `app/src/input.rs` | 5: options; configuration; reading and pumping; live collection; language table |
| `audio/src/receiver.rs` | 5: carriage; record dispatch; command policy; starting; sending |
| `audio-mix/src/lib.rs` | 5: ramp; sound storage; voice state; mixer API; rendering |
| `qrkeyboard/src/net.rs` | 5: stream; HTTP; wakes; reader thread; WebSocket |
| `cli/src/commands.rs` | 11 commands plus shared helpers |
| `cli/src/keyboard.rs` | 4: `qr`; the channel bridge; terminal QR; `keyboard`; plus two misplaced invariants |
| `cli/src/sound.rs` | 4: command; pacing; WAVE reader; stub |
| `app/src/live.rs` | 4: spawning; fill policy; the source; a descriptor reader |
| `audio/src/store.rs` | 4: entry model; arena; static blocks; live ring |
| `input/src/event.rs` | 4: model; decoder; encoder; framing |
| `input/src/session.rs` | 4: handshake; filtering; limiter; count ring |
| `app/src/present.rs`, `session.rs`, `extras.rs`, `sandbox.rs`; `cli/src/main.rs`, `contents.rs`, `output/image.rs`, `font.rs`; `audio/src/lib.rs`, `record.rs`, `idl.rs`; `input/src/keys.rs`, `control.rs`; `qrkeyboard/src/crypto.rs`, `message.rs`; `xtask/src/checks.rs`, `g3.rs`, `glyphs.rs`, `size.rs` | 2 or 3 each, as listed in 2.1 |

### 2.4 Duplicated shapes (24 pairs)

The two std network clients first. `neoteletext-app/src/fetch.rs` and `neoteletext-qrkeyboard/src/net.rs` each carry a socket-plus-TLS client:

1. The socket reader thread: `fetch.rs:189-207 read_socket` and `net.rs:345-367 read_socket` are the same loop (`Interrupted` retry, `SyncSender<Vec<u8>>`, a wake per chunk and at the end).
2. `write_records`: `fetch.rs:233-238` is byte for byte `net.rs:440-445`.
3. The TLS record pump (`read_tls` until nothing is taken, `process_new_packets`, answer alerts): `fetch.rs:161-168` and `:259-271` against `net.rs:424-433`.
4. Proxy-or-direct connect with the two timeouts: `fetch.rs:115-139` against `net.rs:78-106`; the handshake loop `fetch.rs:169-171` equals `net.rs:115-117`.
5. The rustls root store and client configuration: `fetch.rs:97-98` against `net.rs:52-55`.
6. Constants restated: `CONNECT_TIMEOUT` (`fetch.rs:21`, `net.rs:24`), `READS_AHEAD` (`fetch.rs:30`, `net.rs:340`), `READ_CHUNK` (`fetch.rs:26` 16 KiB, `net.rs:33` 4 KiB).
7. A random source over the operating system: `fetch.rs:335-342 SystemRandom` (ring) against `net.rs:40-47 OsRandom` (getrandom).

Within the CLI:

8. Page-number parsing "100 to 8FF": `keyboard.rs:44-49`, `sound.rs:68-71`, `write_text.rs:26-29`; `commands.rs:67-87 parse_selection` is the fuller form.
9. `sandbox::apply(Policy { writable_directory: None, network: false, readable: &[] }, …)` with the same `map_err`: a helper exists at `commands.rs:113-116` but the literal recurs at `commands.rs:287-288`, `contents.rs:158-159`, `font.rs:41-42, 92-93`, `sound.rs:86-87`, `write_text.rs:34-35`, and `app/sandbox.rs:163`.
10. `.map_err(|error| (exit::INPUT, format!("{}: {error}", path.display())))` at about 25 sites: `font.rs:24, 27, 29, 38, 70`; `sound.rs:84, 121, 123, 145, 150`; `write_text.rs:32, 40`; `commands.rs:330, 360, 497`; `keyboard.rs:85`; `contents.rs:133`; `app/convert.rs:223`; `app/slice.rs:28`; `app/live.rs:398, 402`.
11. The "stub when the feature is off" pair written eight times: `app/input.rs:94-104`; `commands.rs:270-304, 446-458, 460-471, 473-484`; `sound.rs:65-67/210-214`; `cli/write_text.rs:23-25/45-49`; `terminal.rs:42-58`.
12. Hand-built TTI text with its own control-code escaping, `keyboard.rs:65-78 qr_page`, against `neoteletext_formats`' writer and `author::DisplayPage` as `app/write_text.rs:607-648` uses them; the CLI tests build TTI by string too (`tests/typing.rs:56`, `tests/contents.rs:21-25`).
13. A milliseconds clock from `start.elapsed().as_millis()` at `view.rs:467, 509, 617` and `keyboard.rs:114`; a microseconds clock at `fetch.rs:491-493`, `input.rs:119`, `view.rs:421`.
14. base64: `output/image.rs:98-120` (standard alphabet) against `qrkeyboard/src/message.rs:140-182` (URL alphabet); `neoteletext_web::ws` carries a third for the handshake.
15. Integration-test helpers `fn neottx(arguments)` at `tests/sound.rs:16-18`, `tests/font.rs:12-14`, `tests/write_text.rs:10-12`, `tests/contents.rs:8-10`, with variants at `tests/web.rs:38-45` and `tests/not_in_build.rs:14-17`; `fn folder(name)` at `tests/sound.rs:20-25`, `tests/font.rs:17-22`, `tests/write_text.rs:15-20`; the WAVE builder at `src/sound.rs:274-288` and `tests/sound.rs:28-38`.
16. The command skeleton (parse selection, load, sandbox, lock stdout, `grid_of` per page) written out in `commands.rs` `list` 119-123, `text` 187-192, `show` 231-247, `render` 320-344, `service_info` 367-368.

Within `neoteletext-app`:

17. The trace-collecting closure, seven lines, at `session.rs:119-125, 133-139, 146-152, 158-164`.
18. `origin_of` (`interact.rs:35-42`) derives an origin by string splitting while `neoteletext_web::url::Url::origin` exists.

Within the microcontroller crates:

19. RFC 1982 serial arithmetic: `audio/src/lib.rs:184-187 serial_newer` and `input/src/session.rs:69-72 serial_after` are the same function, and `input` already depends on `audio`.
20. Body-to-record-to-packet wrappers: `input/src/control.rs:181-223` and `cursor.rs:101-131, 173-186` are the same three-level shape over `record::{write, split}` and `idl::{packet, fragment}`; `lib.rs:78-90 is_input_packet` tests the same "one fragment of an input type" condition a third time.
21. `VoiceSink` fakes: `audio/tests/receiver.rs:29-92 Recorder`, `cli/tests/sound.rs:41-69 Keeper`, `fuzz/audio_packets.rs:16-27 Quiet`, `fuzz/audio_records.rs:13-39 Checker`.

Test servers:

22. Hand-written WebSocket servers with RFC 6455 literals restated although `neoteletext_web::consts::OPCODE_*` exist: `cli/tests/typing.rs:36-45, 97-141`; `qrkeyboard/tests/socket.rs:16-25, 31-71`; `qrkeyboard/tests/wake.rs:17, 43-87`; `app/src/fetch.rs:814, 843-901`.

In `xtask` and `qrkeyboard`:

23. Directory walkers `checks.rs:40-50 rust_files` and `trace.rs:10-21 files`; SHA-256 by `shasum` (`corpus.rs:20-24`) against `neoteletext_web::sha256` (`glyphs.rs:276`, `noto.rs:47`).
24. The four colour-key names: `config.rs:34 COLOUR_KEYS` and `screen.rs:496 COLOURS`.

### 2.5 `cfg` scatter

| File | `cfg` attributes | What they gate |
|---|---|---|
| `cli/src/sound.rs` | 17 | every `use`, const, fn and the test module, for `sound` |
| `cli/src/commands.rs` | 9 | four stub pairs (`view`, `slice`, `live` ×2) |
| `audio/src/receiver.rs` | 9 | `idl` on imports 6, 10, 13, the field 43, the initialiser 60, `reset` 143, `push_packet` 161; `ima` on both arms of `decode` 449, 451 |
| `cli/src/write_text.rs` | 8 | every `use`, the const, the fn pair, for `write-text` |
| `cli/src/main.rs` | 7 | module lines and two match arms |
| `cli/src/output/image.rs` | 7 | one method (`Frame::at`) and its tests, for `view` |
| `audio/src/ima.rs` | 4 | `encode` inside an `ima` file |
| `cli/src/terminal.rs` | 3 | one stub pair |
| `app/src/input.rs` | 2 | one stub pair |

Clean, with the gate on the `mod` line: `app/lib.rs:16-30`, `cli/main.rs:9-18`, `audio/lib.rs:36-41`. `view.rs` is the model the others should follow; `sound.rs` and `cli/write_text.rs` gate item by item because `SoundOptions` (`main.rs:451`) and `PLAYER_PACKETS_PER_SECOND` (`main.rs:337`) must exist in every build.

### 2.6 Where tests are

- Unit tests sit at the end of their file everywhere (consistent), named `tests` except `present.rs:191 receiver_tests`. Inline modules over the 60-line mark of `00-conventions.md`: `fetch.rs` 272, `session.rs` (input) 246, `write_text.rs` 221, `audio-mix lib.rs` 181, `event.rs` 149, `store.rs` 148, `output/text.rs` 136, `convert.rs` 108, `idl.rs` 108, `record.rs` 105, `live.rs` 95, `view.rs` 94, `crypto.rs` 85, `ima.rs` 73, `image.rs` 71, `cursor.rs` 71, `pipe.rs` 69, `keys.rs` 64.
- A test in the wrong crate: `cli/src/output/text.rs:148-163, 182-217` tests `neoteletext_app::present::plain` (136 lines of tests, four of them for the other crate's function).
- Test-only code in production positions: `app/src/fetch.rs:378-379` (`Wakes::waits` field), `:389-390`, `:425-426`; `app/src/live.rs:144-147 routed`. Because `xtask`'s `non_test_source` (`checks.rs:52-62`) and `trace.rs:144` cut a file at the first `#[cfg(test)]`, `check-constants` and `check-io` never read `fetch.rs:380-1071` or `live.rs:148-501` today, and the traceability table attributes those lines to tests.
- Allow attributes on test modules vary in form: with `reason` (`extras.rs:263`, `event.rs:643`, `session.rs:434`, `keys.rs:249`, `wire.rs:221`, `control.rs:226`, `held.rs:97`), without (`write_text.rs:653`, `cursor.rs:189`, `qr.rs:119`, `crypto.rs:284`, `json.rs:221`, `message.rs:185`, `pairing.rs:143`, `config.rs:145`, the four-lint lists in every `audio` and the `audio-mix` file), and as inner attributes (`fetch.rs:803`, `view.rs:774`).
- Integration tests: CLI nine files, audio one, qrkeyboard three; app none (its process behaviour is exercised by `cli/tests/typing.rs` and `web.rs`); input and audio-mix none.

### 2.7 Gaps in the gates (findings for `30-cross-cutting.md`, not steps here)

- There is no check that the panic deny lists are identical: `scripts/check.sh` has no `NO_PANIC_ROOTS` equivalent, and `xtask` does not read the lists. The four lists (`audio/lib.rs:18-27`, `audio-mix/lib.rs:15-24`, `input/lib.rs:20-29`, `qrkeyboard/lib.rs:23-32`) agree by inspection today.
- `neoteletext-app` and `neoteletext-cli` have no deny list at all, although `pipe.rs` (frames from the other process), `fetch.rs` and `live.rs` (network and pipe), `sound.rs::read_wave` (a WAVE file), `contents.rs` (a folder of files) and `font.rs` read outside input; `pipe.rs:333, 342, 363, 390-392` and `sound.rs:233-256` index slices behind length guards that the list would refuse.
- `cli/src/keyboard.rs:21-28` holds two cross-crate constant assertions that compile only with the `keyboard` feature; `cargo xtask features` row `neoteletext-cli ""` never checks them.
- `features.rs:22-68` has no row for `neoteletext-app` or `neoteletext-cli` with `write-text` alone, nor any for `neoteletext-audio-mix` or `neoteletext-qrkeyboard` (both have no features; the workspace clippy covers them).

---
## 3. The target layout

Every tree below follows `00-conventions.md`: the 2018 layout (`foo.rs` beside `foo/`, no `mod.rs`), one concept per file, a feature's code in files of its own behind one gated `mod`, tests in `tests.rs` under the concept's directory when they pass about 60 lines, the narrowest visibility, and no change to any public path of the four crates the browser pins. Line counts are approximate and exclude tests unless the file is a `tests.rs`.

### 3.1 `neoteletext-app`

```
src/
  lib.rs                 ~55   crate docs; mod tree; exit; Failure; not_in_build (as today)
  source.rs               66   Source, Wake, Finished (unchanged)
  session.rs             238   Session (unchanged; see the shared form below)
  interact.rs             79   ActiveForm, message_row, origin_of, submission (unchanged)
  slice.rs                48   [slice] (unchanged)
  sandbox.rs             ~60   Policy, apply, self_test; mod linux / mod unsupported
  sandbox/linux.rs      ~110   Landlock and seccomp (today's Linux mod platform)
  sandbox/unsupported.rs ~20   the note-and-continue platform (today's other mod platform)
  present.rs             ~95   MosaicStyle, visible, cell_text, row_cells, plain; mod raster; mod receiver_page
  present/raster.rs      ~60   Raster, Scale, raster
  present/receiver_page.rs ~40 ALL_COLUMNS_GOOD, ALL_ROWS_RECEIVED, receiver_grid
  present/tests.rs       ~75   the receiver test, and the four tests of plain now in the CLI
  input.rs              ~210   Options, CHUNK, config, open, pump, reader, load, load_for, region_for_language; mod feed
  input/feed.rs          ~75   is_live, live_source (both forms), load_live, open_live
  extras.rs             ~200   PageExtras, Destination, TextLinkExtras, destination, from_page, draw_marks, key; mod forms
  extras/forms.rs        ~90   fixed, number, form_spec
  convert.rs             ~55   Target, convert; mod pages
  convert/pages.rs      ~185   page_file, push_line, page_packets, enhancement_function, enhancement_page_file, magazine_page_file, session_page_files
  convert/tests.rs       108
  pipe.rs               ~135   MAX_INPUT_MESSAGE, MAX_FRAME, Origin, PageData, Submission, Frame, Notice; mod codec
  pipe/codec.rs         ~300   kind bytes, put*, Cursor, page_payload, page_data, write, read, notice_frame
  pipe/tests.rs           69
  descriptor.rs          ~15   [live] descriptor_service_names
  live.rs               ~330   [live] Live, Fill's consts, one impl Live, impl Source, Drop; mod spawn; mod fill; mod tests
  live/spawn.rs          ~45   open, read_frames
  live/fill.rs           ~30   Fill, DECIMAL_DIGIT_LAST
  live/tests.rs          ~95   routed, Kept, the three tests
  fetch.rs               ~75   [live] RESOLVER_PATHS, CHANNEL_PREFIX, run, neottx, clock; mod lines; pub use transport::StdTransport, wakes::Wake
  fetch/transport.rs    ~320   CONNECT_TIMEOUT, READ_CHUNK, READS_AHEAD, Connection, StdTransport, slot, web_address, blocked, read_socket, Refill, refill, write_records, Transport impls, SystemRandom
  fetch/decoder_link.rs  ~35   send, requests, page_request
  fetch/wakes.rs         ~85   Wake, Wakes
  fetch/zxnet.rs        ~100   run_zxnet, live_loop
  fetch/web.rs          ~210   run_web
  fetch/tests.rs        ~270   the played feed (Script, Server, Fake, start, closed) and its three tests; played_proxy, through and the three proxy tests
  write_text.rs         ~190   [write-text] FIRST_ROW, LAST_ROW, WriteError, set_names, Written, write_text; mod sets; mod rtl; mod thai_lao; mod tests
  write_text/sets.rs    ~210   SETS, LAST_CODE, LAST_MARK, Sets, stand_in, page_sets, Cell, switch, encode, break_line
  write_text/rtl.rs      ~70   LAM, ALEF, LAM_ALEF, MIRRORED, visual, break_line_rtl
  write_text/thai_lao.rs ~150  the mark consts, is_mark, MarkedLine, mark_cell, clusters, marked_lines, mark_row, marked_rows
  write_text/tests.rs    221
```

Paths. The crate's only consumer is the CLI, so paths may change, and two do: `live::descriptor_service_names` becomes `descriptor::descriptor_service_names` (one CLI site), and nothing else — `present::{MosaicStyle, plain, cell_text, row_cells, Raster, Scale, raster}`, `pipe::{read, write, …}`, `convert::{Target, convert}`, `input::{Options, is_live, open_live, …}` are kept by `pub use` in each parent, as `00-conventions.md` section 2 asks. `StdTransport` and `Wake` stay `pub` through re-exports although nothing outside uses them; narrowing them is a separate decision.

Shared forms extracted within the crate, behaviour-neutral: `Session::trace_sink(&mut self) -> impl FnMut(Event)` replacing the four seven-line closures (pair 17). Not extracted: `origin_of` (pair 18) would change the parsing path and is a correctness question for `30-cross-cutting.md`.

### 3.2 `neoteletext-cli`

The binary becomes the thin edge the convention asks for: `main.rs` calls `neoteletext_cli::run()`, and a `src/lib.rs` holds the module tree. This adds a library target to the existing package, not a crate; the library exposes one public function, so `missing_docs` touches nothing else. `output/mod.rs` goes, and the output files flatten to the crate root because the parent would hold nothing but three `mod` lines.

```
src/
  main.rs                 ~5   fn main() -> ExitCode { neoteletext_cli::run() }
  lib.rs                 ~70   crate docs; mod tree; the two const _ invariants from keyboard.rs; pub use run::run
  run.rs                 ~95   pub(crate) fn run: parse, one match arm per command, the exit status
  args.rs               ~420   Cli, Common, FormatChoice, ParityChoice, LevelChoice, GraphicsChoice, RasterArgs, Command, FontCommand (clap only); mod tests
  args/tests.rs          ~35   the level-option test
  options.rs             ~70   impl Common { options }, impl FormatChoice { format }
  bounded_file.rs        ~15   read_bounded
  clock.rs               ~20   milliseconds since a start, as the input session counts them
  nfc.rs                  51   [any(view, keyboard)] (unchanged)
  terminal.rs             90   (unchanged)
  cells.rs               112   (today output/cells.rs)
  image.rs              ~140   BEDSTEAD, raster, raster_in, png, ppm, base64, iterm2_inline; tests inline (base64, inline sequence, rasters)
  frame.rs               ~35   Frame (still; at under view)
  ansi.rs               ~130   ColourDepth, nearest_of_eight, colour_of, Style, ansi; re-export of present::{MosaicStyle, plain}; tests inline (~60, the plain tests gone to app)
  commands.rs           ~150   ImageFormat, ConvertTarget, Selection, parse_selection, selected, grid_of, sandbox_closed, mosaic_style, display, scale_for, page_file_name, page_number, io_failure; mod lines
  commands/list.rs       ~65
  commands/text.rs       ~25
  commands/show.rs       ~55
  commands/view.rs       ~40   the view fn and its stub
  commands/render.rs     ~60
  commands/service_info.rs ~40
  commands/services.rs   ~30
  commands/convert.rs    ~20
  commands/slice.rs      ~15   the slice fn and its stub
  commands/fetch.rs      ~15   the fetch fn and its stub
  commands/check.rs      ~55   check; descriptor_service_names and its stub
  commands/contents.rs   226   (today contents.rs, tests inline)
  commands/font.rs      ~120   convert_font, read_table, font_sets, source_fault, conversion_fault
  commands/sound.rs      ~45   SoundOptions, PLAYER_PACKETS_PER_SECOND, the stub; [sound] mod run; [sound] mod wave
  commands/sound/run.rs ~150   [sound] WAV_MAX_FILE_BYTES, WAVE_PCM, PLAY, LOOP, sound, live_packets
  commands/sound/wave.rs ~95   [sound] Wave, read_wave; tests inline (39)
  commands/write_text.rs ~25   TEXT_MAX_FILE_BYTES, the stub; [write-text] mod run
  commands/write_text/run.rs ~30 [write-text] write_text
  commands/qr.rs         ~75   [keyboard] ESCAPE, ESCAPE_OFFSET, LAST_ROW, qr_page, qr; test inline
  commands/keyboard.rs  ~230   [keyboard] OFFERED, REJOIN_SECONDS, KeyboardOptions, Channel, terminal_qr, keyboard
  view.rs               ~420   [view] Pending, run, draw; mod keys; mod typing; mod terminal; mod ticker; mod tests
  view/keys.rs           ~55   map_key, map_form_key, LEAVE_TYPING
  view/typing.rs        ~190   OFFERED, input_of, Typing, host_page
  view/terminal.rs       ~60   Wakened, next_event, TICK, RawGuard
  view/ticker.rs         ~35   TICKER_STEP_US, origin_ticker
  view/tests.rs          ~94
tests/
  common/mod.rs          ~40   neottx, folder, wave (today repeated in four tests)
  (the nine test files as today)
```

Two files stay over 400 lines: `args.rs` is one `Command` enum with clap attributes on every field — the command line's one specification, split only by inventing a seam inside the enum; `view.rs` keeps `run` whole (386 lines) because dividing it is a refactor of the loop's state, proposed as a later stage (section 4, step C9). Both are under the 500-line ceiling. `commands/sound/run.rs` and `write_text/run.rs` are small because what they hold is exactly the gated code; the ungated parent keeps what `run.rs` and `args.rs` need in every build.

Paths: none are public (a binary); the integration tests pin the command line, which does not change.

Shared forms extracted within the crate: `commands::io_failure(path, error) -> Failure` for the twenty-five `map_err` sites (pair 10); `commands::page_number` as the one home of "100 to 8FF" (pair 8); `commands::sandbox_closed(no_sandbox)` for the seven closed-sandbox calls (pair 9); `clock::now_ms(start)` for the four milliseconds clocks (pair 13); `tests/common/mod.rs` for `neottx`, `folder` and the WAVE builder (pair 15). The stub pairs (pair 11) stay as they are: a macro would be a new mechanism, and each pair is the convention's "one item with two forms". `qr_page`'s hand-written TTI (pair 12) is left for `30-cross-cutting.md`: replacing it with the formats crate's writer changes the bytes written.

### 3.3 `neoteletext-audio` (`no_std`; one crate root, one deny list)

```
src/
  lib.rs                 ~60   docs; the lint lists; mod tree; pub use profile::*, codec::*, serial::serial_newer
  profile.rs             ~55   the fifteen profile constants (PROFILE_VERSION … PROGRESSIVE_BUFFER_MS)
  codec.rs               ~95   Codec, IMA_HEADER, IMA_BLOCK_SMALL, IMA_BLOCK_LARGE, MAX_PCM_BLOCK, MAX_BLOCK_SAMPLES, SAMPLE_RATES, sample_rate, rate_code, DUCK_PERCENT
  serial.rs              ~15   serial_newer
  control.rs             106   (unchanged)
  crc.rs                  86   (unchanged)
  port.rs                 82   (unchanged)
  encode.rs              281   [encode] (unchanged)
  ima.rs                ~140   [ima] (tests out)
  ima/tests.rs            73
  idl.rs                ~170   [idl] FRAGMENT_DATA, MAX_FRAGMENTS, CONTROL_*, Fragment, IdlError, is_audio, fragment, packet, read; mod reassembler; pub use reassembler::Reassembler
  idl/reassembler.rs    ~100   SLOT_BYTES, Slot, Reassembler
  idl/tests.rs           108
  record.rs             ~270   TYPE_*, is_input_type, OBJECT_FIXED, DATA_FIXED, CONTROL_BYTES, MAX_LABEL, MAX_LANGUAGE, TAG_*, FLAG_*, Object, Data, Operation, Control, Record, parse, object, control; mod frame; pub use frame::{RecordError, framed_length, record_length, split, write}
  record/frame.rs       ~130   RecordError, framed_length, record_length, split, write, Fields
  record/tests.rs        105
  receiver.rs           ~300   Statistics, Receiver, new, tick, next_tick_ms, statistics, store, follow_service, reset, sink_lost, push_record, open_page, set_page_sounds, command, bump, needs, duration_ms; [idl] mod carriage; mod play; mod send
  receiver/carriage.rs   ~40   [idl] impl Receiver { push_packet }
  receiver/play.rs       ~85   impl Receiver { try_start, start_waiting, start_armed, buffered_ms }
  receiver/send.rs       ~90   impl Receiver { send_sound, send_live, send_block }; decode (its two ima arms)
  store.rs              ~260   Entry, Defined, Stored, Store, new … received, put; mod arena; mod live; mod tests
  store/arena.rs        ~115   impl Store { define, find_space }
  store/live.rs          ~95   impl Store { set_live_cursor, live_block, slot_index, put_live }
  store/tests.rs         148
tests/
  receiver.rs            490   (unchanged)
```

`serial.rs` is fifteen lines: a file that small is tolerated because its one function is used by `control.rs` and `store.rs` and is the crate's one piece of RFC 1982 arithmetic; the alternative, leaving it in `lib.rs`, breaks the rule that the root holds no logic.

Paths: every root path (`Codec`, `SAMPLE_RATES`, `IMA_BLOCK_*`, `MAX_BLOCK_SAMPLES`, `CHANNELS`, `MIN_FADE_MS`, `MAX_FADE_MS`, `MAX_GAIN`, `DUCK_PERCENT`, `PROFILE_VERSION`, `LIVE_STALL_FADE_MS`, `serial_newer`, …) and every module path (`record::{split, write, framed_length, record_length, RecordError, TYPE_*, is_input_type, FLAG_LOOP, MAX_LABEL}`, `idl::{fragment, packet, FRAGMENT_DATA, Reassembler}`, `receiver::Receiver`, `port::*`, `encode::*`, `crc::*`) is kept by `pub use`. Nothing the browser, `neoteletext-input`, the CLI or the fuzz targets name moves.

No shared form is extracted here; the one duplicate (pair 19) crosses into `neoteletext-input`, and is listed in section 6.

### 3.4 `neoteletext-audio-mix` (`no_std` with `alloc`; one crate root)

```
src/
  lib.rs                 ~45   docs; the lint lists; mod tree; pub use mixer::{Mixer, Start, VOICES}, sound::{SoundKey, STREAM_TARGET_MS, STREAM_RING_MS, STREAM_TRIM_PPM}
  sinc.rs                 82   (unchanged, generated)
  ramp.rs                ~60   UNITY, MIN_RAMP_MS, Ramp, level, scale
  sound.rs               ~75   SoundKey, STREAM_TARGET_MS, STREAM_RING_MS, STREAM_TRIM_PPM, PPM, Sound
  voice.rs              ~110   FRACTION_BITS, PHASE_SHIFT, Playing, Voice, begin, set_step, advance, interpolate
  mixer.rs              ~330   VOICES, Start, Mixer, new, rate, define, samples, forget, clear, start, stop, gain, set_master, active, render, voice_sample, update_ducks, collect; mod stream; mod tests
  mixer/stream.rs        ~75   impl Mixer { stream, stream_samples, trim_streams }
  mixer/tests.rs         181
```

Paths: `neoteletext_audio_mix::{Mixer, SoundKey, Start}` (the browser's three) are kept by `pub use`. The private fields of `Mixer` stay private; `mixer/tests.rs` and `mixer/stream.rs` are descendants of `mixer` and reach them.

### 3.5 `neoteletext-input` (`no_std`; one crate root)

```
src/
  lib.rs                 ~45   docs; the lint lists; mod tree; pub use limits::*, carriage::is_input_packet
  limits.rs              ~45   VERSION, MAX_MESSAGE, MAX_PASTE, MAX_COMPOSE, MAX_KEY_TEXT, MAX_AGENT, MAX_COLUMNS, MAX_ROWS, MAX_PER_SECOND, WELCOME_TIMEOUT_MS, LAST_ADDRESSABLE_PAGE, is_page, the two const _ assertions
  carriage.rs            ~50   input_record(packet, kind) -> Option<fragment>, is_input_packet
  wire.rs                280   (unchanged, tests inline 59)
  names.rs               191   (unchanged)
  digits.rs               55   (unchanged)
  modes.rs               155   (unchanged)
  held.rs                150   (unchanged)
  keys.rs               ~110   FIRST_NAMED, code, name, is_code, unidentified, MODIFIER_NAMES, LOCKS, LOCATED_MODIFIERS, is_modifier, is_dead, remaining; mod one_byte; mod us_layout; mod tests
  keys/one_byte.rs      ~135   the ONE_BYTE table
  keys/us_layout.rs      ~35   us_base
  keys/tests.rs           64
  event.rs              ~330   the type, flag and modifier constants; Action, KeyCode, Key, MouseAction, Point, Mouse, Wheel, Event, Item, InputError; printable, check_text, units; mod decode; mod encode; pub use decode::{read, read_message, StreamDecoder, MAX_STREAM_ITEM}, encode::write; mod tests
  event/decode.rs       ~250   read, read_text, read_point, read_event, read_key, read_message, MAX_STREAM_ITEM, StreamDecoder
  event/encode.rs       ~135   write, write_point, point_flags, write_event
  event/tests.rs         149
  session.rs            ~230   State, WelcomeError, SendError, Session, new, state, welcomed, caps, open, close, welcome, control, tick, welcome_due, modes_on, send, count, acked; mod filter; mod count; mod limiter; pub use count::REMEMBERED, limiter::Limiter; mod tests
  session/filter.rs      ~65   impl Session { filter }
  session/count.rs       ~70   REMEMBERED, SERIAL_HALF, serial_after, impl Session { sent, drop_oldest, acknowledged }
  session/limiter.rs     ~60   SECOND_MS, impl Session { allow }, Limiter
  session/tests.rs       246
  control.rs            ~230   (packet_of, read, from_packet now through carriage; tests inline 46)
  cursor.rs             ~190   (from_packet through carriage; tests out)
  cursor/tests.rs         71
```

Paths: every path the browser, the CLI and the three fuzz targets name (`event::{…}`, `session::{Session, State, Limiter, REMEMBERED, SendError, WelcomeError}`, `control::{Control, ControlError, MAX_BODY, FRAGMENT_DATA, PAGE_MODES, …, from_packet, packet_of, read_body, write_body}`, `cursor::{BODY, Cursor, from_body, from_packet, …}`, `modes::*`, `keys::{code, name, is_code, unidentified, is_modifier, is_dead, us_base, FIRST_NAMED}`, `digits::decimal_digit`, `is_input_packet`, `MAX_MESSAGE`, `MAX_KEY_TEXT`, `MAX_PER_SECOND`, `MAX_ROWS`, `MAX_PASTE`, `VERSION`, `WELCOME_TIMEOUT_MS`) is kept by `pub use`.

Shared form extracted within the crate: `carriage::input_record`, the "one fragment carrying a record of this input type" test that `control::from_packet`, `cursor::from_packet` and `is_input_packet` each write today (pair 20). The record and packet wrappers themselves stay in `control.rs` and `cursor.rs`: their bodies differ in type and size.

### 3.6 `neoteletext-qrkeyboard` (std; one crate root)

```
src/
  lib.rs                 ~40   docs; the lint lists; mod tree; pub use error::Error, protocol::*, crypto::random
  error.rs               ~40   Error, Display, std::error::Error
  protocol.rs            ~20   PROTOCOL_VERSION, MAX_FRAME_BYTES, KEEPALIVE, LEAVE, KEEPALIVE_INTERVAL_MS, RELAY
  config.rs             ~230   Layout (with has_key and has_text, today's screen.rs tables), ScreenConfig, hash; tests inline 44
  crypto.rs              ~90   Role, SECRET_BYTES, SALT_BYTES, SHARE_BYTES, CONFIRM_BYTES, hkdf, directional_keys, constant_time_equal, random; mod sealed; mod spake2; pub use sealed::{Sealer, Opener, NONCE_BYTES, TAG_BYTES, TAG_SEALED, SEALED_OVERHEAD}, spake2::{Spake2, Spake2Result, password_scalar, random_scalar}; mod tests
  crypto/sealed.rs       ~80   nonce, Sealer, Opener
  crypto/spake2.rs      ~140   SPAKE2_M, SPAKE2_N, SCALAR_BYTES, point, decode_point, encode, reduce, password_scalar, random_scalar, length_prefixed, Spake2, Spake2Result
  crypto/tests.rs         85
  json.rs                244   (unchanged)
  message.rs             242   (unchanged)
  pairing.rs             199   (unchanged)
  phone.rs               178   (unchanged)
  qr.rs                  152   (unchanged)
  net.rs                ~110   CONNECT_TIMEOUT, RESPONSE_TIMEOUT, READ_CHUNK, OsRandom, tls_config, parse, Incoming, Wake, Waker, LONGEST_WAIT, later; mod stream; mod http; mod websocket; pub use stream::Stream, http::{request, MAX_BODY}, websocket::WebSocket
  net/stream.rs         ~140   Stream
  net/http.rs            ~95   MAX_HEAD, MAX_BODY, request, host_header
  net/websocket.rs      ~280   FRAME_HEADER, CLOSE_CODE_BYTES, READS_AHEAD, read_socket, Reading, write_records, WebSocket, Drop
  screen.rs             ~270   the consts, Join, Event, Screen, is_code, create, connect, join, connected, waker, send_text, send_binary, finish, close; mod wait; mod relay; mod messages; test inline 11
  screen/wait.rs        ~115   impl Screen { wait, next_deadline, turn, release_stale }
  screen/relay.rs        ~75   impl Screen { control, peer_up, pin_failed, lock, clear_channel }
  screen/messages.rs     ~75   impl Screen { binary, acknowledge }
tests/
  wake.rs, relay.rs, socket.rs   (unchanged)
```

Paths: `neoteletext_qrkeyboard::{Error, RELAY, PROTOCOL_VERSION, …, random}` and `config::*`, `qr::*`, `screen::*`, `message::{read, from_base64url}`, `json::Value`, `net::{parse, request, Incoming, WebSocket, Waker}`, `crypto::*` are kept by `pub use`.

Shared form extracted within the crate: the five layout key tables of `screen.rs:495-526` become `config::Layout::has_key` and `has_text` (pair 24), a move of static data behind a one-line forwarding call. `base64url` stays in `message.rs` (pair 14 crosses into the CLI; section 6).

### 3.7 The two network clients

Pairs 1 to 7 are the one duplication this plan does not remove. `fetch/transport.rs` and `net/{stream,websocket}.rs` need the same socket reader, TLS pump, proxy connect and `write_records`, but no crate may hold them without a decision the owner has not taken: `neoteletext-qrkeyboard` may depend only on `neoteletext-web` (`xtask/src/checks.rs:186-208`); `neoteletext-app` may not be used by `qrkeyboard` without inverting that table and dragging `landlock`, `seccompiler` and the slicer into the keyboard; and `neoteletext-web` is a library crate that `cargo xtask check-io` forbids sockets and threads. The three ways out — a new `std` transport crate, a `std`-gated transport module in `neoteletext-web` with an exemption in `check-io`, or `qrkeyboard` depending on `app` — each add a crate, a dependency or a rule, which the plan does not do. The two files are kept in step by a cross-reference comment at the head of each, and the pair is listed for the owner in `30-cross-cutting.md`.

### 3.8 `xtask`

```
src/
  main.rs                 76   (unchanged: dispatch is the binary's whole entry, and xtask has no library)
  checks.rs              ~70   rust_files, non_test_source, report, WORKSPACE_PREFIX, LIBRARY_CRATES, APPLICATION_CRATES; mod layers; mod deps; mod constants; mod io; pub use
  checks/layers.rs       ~95   FOUNDATION, CROSS_CUTTING, LAYER_TABLE, module_of, layers, uses
  checks/deps.rs         ~70   PERMITTED, dependencies
  checks/constants.rs    ~50   DATA_FILES, WATCHED_LITERALS, constants, contains_literal
  checks/io.rs           ~45   FORBIDDEN, io, forbid
  features.rs             89   (unchanged)
  corpus.rs               72   (unchanged)
  noto.rs                 61   (unchanged)
  level25.rs              44   (unchanged)
  trace.rs               181   (unchanged; the 93-line function is a later refactor)
  size.rs               ~200   DEFAULT_TARGET, FLASH_BUDGET, Build, BUILDS, the marker tables, run, link, forbidden, is_float, is_panic; mod elf; tests inline 23
  size/elf.rs            ~75   Image, read_elf
  g3.rs                  ~45   CELL_WIDTH, HEIGHTS, FIRST_CODE, CODES, text; mod geometry; mod table; mod tests
  g3/geometry.rs        ~215   signed, X, Y, Part, Shape, inside_polygon, covers, rasterise, polygon, rect, union, the stroke constants and helpers, mirror, complement
  g3/table.rs           ~115   shape
  g3/tests.rs             73
  glyphs.rs              ~60   the path constants, generate; mod bedstead; mod g3_table; mod required; mod tests
  glyphs/bedstead.rs     ~80   Entry, parse, bedstead_source, check_bedstead, recorded_checksum
  glyphs/g3_table.rs     ~55   g3_source
  glyphs/required.rs    ~120   Set, sets, required, required_text, forms_text
  glyphs/tests.rs         48
```

Shared form: `trace.rs` uses `checks::rust_files` (`pub(crate)`) in place of its own `files` once the latter's extra extensions are passed as a parameter — a small code change, listed under step X3 as optional (pair 23's first half; the `shasum` half is in section 6).

### 3.9 The fuzz targets and the firmware image

Unchanged. Every path they import (section 1.8) is kept by the re-exports above; each step that touches `neoteletext-audio` or `neoteletext-input` runs `cargo +nightly check --manifest-path fuzz/Cargo.toml` before its commit. The firmware image links core, formats and web only, so `cargo xtask size` is unaffected by anything here; the `full` gate's bare-metal build of the three `no_std` crates (`check.sh:39-41`) is the check that no new file added `std`.

---
## 4. The moves

Each step is one commit. Unless a step says otherwise it passes `scripts/check.sh fast` and the touched crate's rows of `cargo xtask features` (`xtask/src/features.rs:22-68`), its diff reads as moved lines under `git diff --color-moved=dimmed-zebra`, its message names the concept and the step number, and every test module keeps the allow attribute it has today, carried as the first line of the new `tests.rs` (an inner `#![allow(...)]`). Tests go last in every file. "Importers" names the other engine files whose `use` lines change. The browser is not touched by any step here: no path it imports changes.

The order across crates is the one `01-method-and-order.md` sets: `neoteletext-app` (no consumer but the CLI), then the CLI, then the three `no_std` crates and `qrkeyboard` under the rule that no public path moves, then `xtask`.

### 4.1 `neoteletext-app` (steps A1 to A10)

Gate for every A step: `scripts/check.sh fast`; `cargo xtask features` rows `neoteletext-app ""`, `"live"`, `"slice"`; and, because `features.rs` has no row for it, `cargo clippy -p neoteletext-app --no-default-features --features write-text --all-targets -- -D warnings` by hand.

**A1. `sandbox` by platform.** `git mv` nothing; create `sandbox/linux.rs` from the Linux `mod platform` body (`sandbox.rs:34-138`: the `use` lines, `LANDLOCK_ABI`, `landlock`, `target_arch`, `number` with its allow, `seccomp`, `apply`) and `sandbox/unsupported.rs` from the other (`143-157`, with its `#[allow(clippy::unnecessary_wraps)]`). In `sandbox.rs`: `#[cfg(target_os = "linux")] mod linux; #[cfg(target_os = "linux")] use linux as platform; #[cfg(not(target_os = "linux"))] mod unsupported; #[cfg(not(target_os = "linux"))] use unsupported as platform;`. Visibility: the two `pub(super) fn apply` stay as they are. No tests move. Importers: none.

**A2. `present` into text, raster and the receiver's page.** `present/raster.rs` takes `Raster` 97-108, `Scale` 110-119, `raster` 121-153; `present/receiver_page.rs` takes `ALL_COLUMNS_GOOD`, `ALL_ROWS_RECEIVED` 155-158 and `receiver_grid` 160-188 (its five inline `use` lines become file-level `use`s); `present/tests.rs` takes `receiver_tests` 190-207 (no allow attribute) **and** the four tests of `plain` from `neoteletext-cli/src/output/text.rs:148-163, 182-196, 200-217` with their `grid_with` helper 139-146 (their `#[cfg(feature = "side-panels")]` on `plain_text_composes_side_panels` travels; `neoteletext-app` has no such feature, so that test needs the core's: add `#[cfg(feature = "side-panels")]` as it is and note that the app crate does not forward the feature — the test compiles out in every app build until the CLI's `side-panels` pass-through reaches the app; alternatively keep that one test in the CLI. The plan keeps it in the CLI and moves the other three.) `present.rs` keeps `MosaicStyle`, `visible`, `cell_text`, `row_cells`, `plain` and adds `mod raster; mod receiver_page; pub use raster::{Raster, Scale, raster}; pub use receiver_page::receiver_grid; #[cfg(test)] mod tests;`. Visibility: none change (`visible` stays private to `present.rs`). Importers: none (`cli/output/text.rs:9-10` and `output/image.rs:10-11` keep their paths).

**A3. `input` and its live feed.** `input/feed.rs` takes `is_live` 85-92, both `live_source` forms 94-104 with their `cfg` lines, `load_live` 106-143, `open_live` 270-279. `input.rs` adds `mod feed; pub use feed::{is_live, open_live};`. Visibility: `load_live` becomes `pub(super)` (called by `load_for` 192-194). Importers: none.

**A4. `extras` and its form conversion.** `extras/forms.rs` takes `fixed` 169-177, `number` 179-181, `form_spec` 183-254. `extras.rs` adds `mod forms; pub use forms::form_spec;`. The 27-line test module stays inline in `extras.rs` with its `#[allow(clippy::unwrap_used, clippy::indexing_slicing, reason = "a test")]`. Visibility: `fixed` and `number` stay private, now to `forms.rs`. Importers: none.

**A5. `convert` and the page-file export.** `convert/pages.rs` takes `LINKS`, `CODING_TRIPLETS` 28-32 and the seven functions 34-209; `convert/tests.rs` takes 258-366 (no allow attribute). `convert.rs` keeps `Target`, `convert` and adds `mod pages; pub use pages::{page_file, enhancement_page_file, magazine_page_file, session_page_files}; #[cfg(test)] mod tests;`. Visibility: `CODING_TRIPLETS` becomes `pub(super)` (the test at 364 reads it); `push_line`, `page_packets`, `enhancement_function` stay private to `pages.rs`. Importers: none (`cli/commands.rs:12` uses `convert as conversion` and `Target`, `convert`).

**A6. `pipe` and its codec.** `pipe/codec.rs` takes the kind bytes and `MAX_STRINGS` 129-157, `put`, `put_string`, `put_option` 159-180, `Cursor` 182-224, `page_payload`, `page_data` 226-253, `write` 255-323, `read` 325-403, `notice_frame` 405-426; `pipe/tests.rs` takes 428-497 (no allow attribute). `pipe.rs` keeps the types and adds `mod codec; pub use codec::{read, write}; #[cfg(test)] mod tests;`. Visibility: none change. Importers: none (`cli/tests/typing.rs`, `cli/keyboard.rs:24`, `live.rs`, `fetch.rs` keep `pipe::…`).

**A7. `live` into the source, its spawning and its fill policy; the descriptor reader out.** `live/spawn.rs` takes `open` 94-122 and `read_frames` 124-140; `live/fill.rs` takes `Fill` 57-79 and `DECIMAL_DIGIT_LAST` 81-82; `live/tests.rs` takes `routed` 142-147 and 406-501 (no allow attribute); `src/descriptor.rs` takes `descriptor_service_names` 395-404 with `#[cfg(feature = "live")] pub mod descriptor;` in `lib.rs`. The three `impl Live` blocks (149, 172, 362) become one. `live.rs` adds `mod spawn; mod fill; pub use spawn::open; #[cfg(test)] mod tests;`. Visibility: `Live::new` → `pub(super)` (spawn and tests call it); `read_frames` → `pub(super)` (tests); `Fill` and `Fill::allows` → `pub(super)`; `Live::request` is a trait method, unchanged. Importers: `neoteletext-cli/src/commands.rs:476` → `neoteletext_app::descriptor::descriptor_service_names`.

**A8. `fetch` into its seven parts.** `git mv src/fetch.rs src/fetch.rs` is a no-op; create the directory. `fetch/transport.rs` takes `CONNECT_TIMEOUT`, `READ_CHUNK`, `READS_AHEAD` 19-30 (not `RESOLVER_PATHS`), `Connection` 45-55, `StdTransport` 57-68, `slot`, `web_address`, `blocked` 70-90, `impl StdTransport` 92-185, `read_socket` 187-207, `Refill`, `refill` 209-229, `write_records` 231-238, `impl Connection` 240-275, the two `Transport` impls 277-332, `SystemRandom` 334-342; `fetch/decoder_link.rs` takes `send` 344-347, `requests` 349-366, `page_request` 441-443; `fetch/wakes.rs` takes `Wake` 32-43 and `Wakes` 368-439 with its `#[cfg(test)]` field and two sites unchanged; `fetch/zxnet.rs` takes `run_zxnet` 495-505, `live_loop` 507-591; `fetch/web.rs` takes `run_web` 593-797 with its allow, which gains `reason = "one event loop; splitting it would scatter the agent's sink and state"` from the comment at 593. `fetch.rs` keeps the doc, `RESOLVER_PATHS`, `CHANNEL_PREFIX`, `run`, `neottx`, `clock` and adds the five `mod` lines, `pub use transport::StdTransport; pub use wakes::Wake;`. Tests: `fetch/transport/tests.rs` (a third level, allowed because `transport.rs` is itself a 320-line concept and its tests reach `reach`, `open` and `Connection::receive`, which stay private) takes `played_proxy`, `through` and the three proxy tests 975-1070; `fetch/tests.rs` takes `LIMIT`, `PEER`, `TEXT_FRAME` 809-814, `Script`, `Server`, `Fake`, `start`, `closed` 816-928 and the three loop tests 930-973. Both carry `#![allow(clippy::unwrap_used, clippy::expect_used, reason = "a test")]`. Visibility: `READ_CHUNK`, `web_address`, `SystemRandom` → `pub(super)`; `send`, `requests`, `page_request` → `pub(super)`; `Wakes`, `Wakes::new`, `turn`, `next_request`, `wait` → `pub(super)`, and `Wakes::ended` (read at 566, 701) gets `pub(super) fn ended(&self) -> bool` — the one method added, since fields stay private; `run_zxnet`, `live_loop`, `run_web`, `clock`, `neottx` → `pub(super)`. Importers: none (`cli/commands.rs:464` keeps `fetch::run`). After this step `xtask check-constants` and `check-io` read the whole of what was `fetch.rs` for the first time.

**A9. `write_text` by script.** `write_text/sets.rs` takes `SETS` 38-87, `LAST_CODE`, `LAST_MARK` 129-132, `Cell` 192-199, `Sets` 201-245, `stand_in` 247-262, `switch` 264-271, `encode` 273-311, `break_line` 313-347, `page_sets` 552-565; `write_text/rtl.rs` takes 113-121, `visual` 349-370, `break_line_rtl` 372-406; `write_text/thai_lao.rs` takes 89-111, `MarkedLine` 408-414, `mark_cell` 416-438, `clusters` 440-464, `marked_lines` 466-515, `mark_row` 517-526, `marked_rows` 528-550; `write_text/tests.rs` takes 652-874 with `#![allow(clippy::unwrap_used, clippy::indexing_slicing)]`. `write_text.rs` keeps 1-27, 123-127, 134-190, 567-650 and adds `mod sets; mod rtl; mod thai_lao; pub use sets::{SETS, set_names}; #[cfg(test)] mod tests;`. Visibility: `Sets`, `Cell`, `encode`, `break_line`, `page_sets`, `LAST_CODE`, `break_line_rtl`, `marked_lines`, `marked_rows` → `pub(super)`; `Sets`'s four fields (`default`, `second`, `base`, `g2`) → `pub(super)`, read by `thai_lao.rs:420-433` and `write_text.rs:576-577, 612`. This is a departure from "fields stay private": four accessors would be the convention's answer, and are a code change for the later stage; the seam is listed so the reviewer sees it. Importers: none (`cli/write_text.rs:36` keeps `write_text::write_text`). `write_text.rs` ends at about 190 lines; `sets.rs` at about 210.

**A10. The one shared form.** Add `Session::trace_sink` and call it from `push`, `push_at`, `tick`, `finish` (`session.rs:119-125, 133-139, 146-152, 158-164`). A code change, not a move; the four bodies become one; the message says so.

### 4.2 `neoteletext-cli` (steps C1 to C14)

Gate for every C step: `scripts/check.sh fast`; `cargo xtask features` rows `neoteletext-cli ""`, `"view"`, `"live"`, `"slice"`, `"sound"`, `"keyboard"`; and by hand `--no-default-features --features write-text`. The integration tests run in `check.sh`'s `cargo test`; `tests/not_in_build.rs` runs its refusal tests only in the feature-less row.

**C1. The library edge.** Create `src/lib.rs` with the crate doc (`main.rs:1-4`), the `mod` lines (`main.rs:6-19`, with `mod args; mod run;` added), the two `const _` assertions from `keyboard.rs:21-28`, and `pub use run::run;`. `src/args.rs` takes `Cli` 26-32, `Common` 34-86 with its `#[allow(clippy::struct_excessive_bools)]`, `ParityChoice`, `LevelChoice`, `GraphicsChoice` 88-125, `RasterArgs` 127-143, `Command` 145-396, `FontCommand` 479-513, and `FormatChoice` from `options.rs:13-44`; `src/args/tests.rs` takes `main.rs:515-549` (no allow attribute). `src/run.rs` takes `main` 398-477 as `pub(crate) fn run() -> ExitCode`. `src/main.rs` becomes `fn main() -> std::process::ExitCode { neoteletext_cli::run() }`. `options.rs` keeps `impl FormatChoice { format }` and `impl Common { options }`, now `use crate::args::{Common, FormatChoice, LevelChoice, ParityChoice}`. Visibility: everything that was `pub` in `main.rs` stays as it is (inside private modules of the library it is not exported, so `missing_docs` sees only `run`); `run` is `pub`, documented. Importers: `commands.rs:6` (`crate::{GraphicsChoice, RasterArgs}` → `crate::args::{…}`), `options.rs:4`. Departure: `args.rs` is about 420 lines, over the 400 aim and under the 500 ceiling, because it is one `Command` enum with clap attributes on every field — the command line's one specification. The firmware and fuzz are untouched; `cargo xtask check-deps` and `check-io` work by crate name and need no change.

**C2. The output files to the root.** Delete `output/mod.rs`; `git mv output/cells.rs cells.rs`, `output/image.rs image.rs`, `output/text.rs ansi.rs` (a rename where the name misleads: the file holds ANSI output and re-exports `plain`). `lib.rs`: `mod cells; mod image; mod ansi;` in place of `mod output;`. Importers: `commands.rs:3-4` (`crate::output::image::…` → `crate::image::…`, `crate::output::text::…` → `crate::ansi::…`), `commands.rs:197` (`crate::output::cells::cells` → `crate::cells::cells`), `contents.rs:9`, `view.rs:6-7`.

**C3. `Frame` out of `image`.** `src/frame.rs` takes `Frame` 23-52 (with the `view` gate on `at` and the `ColourMode` import 15-16) and the test `frames_follow_the_flash_timing` 163-191 with its `#[cfg(feature = "view")]` and the `PresentationLevel` import, inline (29 lines). `image.rs` keeps `BEDSTEAD`, the encoders, `base64`, `iterm2_inline` and its other tests inline (~40 lines). Importers: `commands.rs:3`, `view.rs:6` (`crate::image::Frame` → `crate::frame::Frame`).

**C4. `commands` into one file per command.** `commands/list.rs` takes `list` 118-179; `commands/text.rs` `text` 185-201; `commands/show.rs` `show` 222-268; `commands/view.rs` `view` and its stub 270-304; `commands/render.rs` `render` 312-363; `commands/service_info.rs` 365-400; `commands/services.rs` 402-428; `commands/convert.rs` 430-444; `commands/slice.rs` 446-458; `commands/fetch.rs` 460-471; `commands/check.rs` `descriptor_service_names` with its stub 473-484 and `check` 486-522. `commands.rs` keeps 1-116, 181-183, 203-220, 306-310 and the 16-line test inline, adds the eleven `mod` lines and a `pub use` of each command function so `run.rs` is unchanged. Visibility: `selected`, `grid_of`, `sandbox`, `mosaic_style`, `display`, `scale_for`, `page_file_name` → `pub(super)`; `descriptor_service_names` stays private, now to `check.rs`. Importers: `run.rs` none. The directory's third level is not needed: no child has children.

**C5. `contents`, `font` and the bounded read into place.** `git mv src/contents.rs src/commands/contents.rs`, `git mv src/font.rs src/commands/font.rs`; `src/bounded_file.rs` takes `read_bounded` `font.rs:22-32` as `pub(crate)`. `commands.rs` adds `mod contents; mod font; pub use contents::contents; pub use font::{convert_font, font_sets};`; `lib.rs` drops `mod contents; mod font;` and adds `mod bounded_file;`. Visibility: `read_table` → `pub(super)` (called by `render.rs`, today `commands.rs:324`). Importers: `run.rs` (`contents::contents` → `commands::contents`, `font::…` → `commands::…`), `render.rs` (`crate::font::read_table` → `super::font::read_table`), `sound.rs:8`, `write_text.rs:5` (`crate::font::read_bounded` → `crate::bounded_file::read_bounded`).

**C6. `sound` as an ungated parent and a gated child.** `git mv src/sound.rs src/commands/sound.rs`; `commands/sound/run.rs` takes the `use` lines (now without `cfg`), `WAV_MAX_FILE_BYTES`, `WAVE_PCM`, `PLAY`, `LOOP` 24-35, `sound` 65-160, `live_packets` 162-208; `commands/sound/wave.rs` takes `Wave` 216-222, `read_wave` 224-268 and the tests 270-309 inline under a plain `#[cfg(test)]` (39 lines, no allow attribute). `commands/sound.rs` keeps `SoundOptions` 40-63 with its `cfg_attr`, `PLAYER_PACKETS_PER_SECOND` 37-38, the stub 210-214, and adds `#[cfg(feature = "sound")] mod run; #[cfg(feature = "sound")] mod wave; #[cfg(feature = "sound")] pub use run::sound;`. Seventeen `cfg` attributes become five. Visibility: `Wave`, `read_wave` → `pub(super)`; `live_packets` private to `run.rs`. Importers: `run.rs` (`sound::…` → `commands::…`), `commands.rs` adds `mod sound; pub use sound::{SoundOptions, PLAYER_PACKETS_PER_SECOND, sound};`, `args.rs:337` (`sound::PLAYER_PACKETS_PER_SECOND` → `crate::commands::PLAYER_PACKETS_PER_SECOND`).

**C7. `qr` and `keyboard` apart.** `commands/qr.rs` takes `ESCAPE`, `ESCAPE_OFFSET`, `LAST_ROW` 34-38, `qr_page` 51-80, `qr` 82-86 and the test 310-335 inline (25 lines, no allow); `commands/keyboard.rs` takes `OFFERED` 30-32, `REJOIN_SECONDS` 39-40, `KeyboardOptions` 88-102, `Channel` 104-232, `terminal_qr` 234-245, `keyboard` 247-308; `page_number` 44-49 moves to `commands.rs` as `pub(super)` (the one home of "100 to 8FF"; `sound.rs` and `write_text.rs` adopt it in C12); `type Failure` 42 is deleted in favour of `neoteletext_app::Failure`. `commands.rs` adds `#[cfg(feature = "keyboard")] mod qr; #[cfg(feature = "keyboard")] mod keyboard;` and the gated `pub use`. Visibility: `qr` → `pub(super)` (called by `keyboard.rs`, today 274). Importers: `run.rs:455, 459` (`keyboard::…` → `commands::…`). `nfc.rs` stays at the root with its `any(view, keyboard)` gate.

**C8. `write_text` the same way.** `git mv src/write_text.rs src/commands/write_text.rs`; `commands/write_text/run.rs` takes the `use` lines and `write_text` 23-43; the parent keeps `TEXT_MAX_FILE_BYTES` 16-21, the stub 45-49, `#[cfg(feature = "write-text")] mod run;` and the gated `pub use`. Eight `cfg` attributes become three. `run.rs` is small (about 30 lines); it is exactly the gated code, and siblings agree with `sound/run.rs`. Importers: `run.rs`.

**C9. `view` into its parts.** `view/keys.rs` takes `map_key` 62-85, `map_form_key` 87-108, `LEAVE_TYPING` 110-112; `view/typing.rs` takes `OFFERED` 114-118, `input_of` 120-177, `Typing` 179-201, `host_page` 203-208, `impl Typing` 210-303; `view/terminal.rs` takes `Wakened` 39-45, `next_event` 47-54, `TICK` 56-58, `RawGuard` 305-320; `view/ticker.rs` takes `TICKER_STEP_US` 59-60, `origin_ticker` 328-357; `view/tests.rs` takes 772-866 with `#![allow(clippy::unwrap_used, reason = "a test")]`. `view.rs` keeps the doc, `Pending`, `run`, `draw` and adds the four `mod` lines and `#[cfg(test)] mod tests;`. Visibility: `map_key`, `map_form_key`, `LEAVE_TYPING`, `input_of`, `Typing`, `Typing::new`, `tell_focus`, `on`, `connection`, `records`, `send`, `host_page`, `Wakened`, `next_event`, `TICK`, `RawGuard`, `origin_ticker` → `pub(super)`; `Typing`'s fields `open`, `left`, `unfocused`, `input`, `told`, `go_to` → `pub(super)`, read and written by `run` at 517, 526-527, 553, 634, 641-651. That is a seam of six fields, the convention's sign that `run` and `Typing` are one concept; it is accepted here because the alternative is the loop refactor below, and it is listed for the reviewer. Departure: `view.rs` stays about 420 lines because `run` (386) is moved whole. The later stage, not in this plan's steps, lifts `run`'s seven blocks (notices 425-484, actions 486-507, typing 508-530, viewer state 531-548, form activation 556-585, compose and draw 586-615, keys 639-739) into methods of a loop type holding the sixteen locals of 381-398, after which the six fields become methods and `view.rs` falls under 150.

**C10 to C14. The shared forms (code changes, one commit each).** C10 `commands::io_failure(path: &Path, error: impl Display) -> Failure` replacing the twenty-five `map_err` closures of pair 10. C11 `commands::sandbox_closed(no_sandbox: bool) -> Result<(), Failure>` replacing the seven literal `sandbox::apply(Policy { … }, …)` calls of pair 9 (the existing `commands.rs:113-116 sandbox` becomes it). C12 `sound/run.rs:68-71` and `write_text/run.rs:26-29` call `commands::page_number`. C13 `src/clock.rs` with `now_ms(start: Instant) -> u32` replacing `view.rs:467, 509, 617` and `keyboard.rs:114`; ungated, since both features use it. C14 `tests/common/mod.rs` with `neottx`, `folder` and the WAVE builder, used by `tests/sound.rs`, `font.rs`, `write_text.rs`, `contents.rs`. Each message says which sites changed; the gate's integration tests prove the wording of the messages did not.

### 4.3 `neoteletext-audio` (steps U1 to U6)

Gate for every U step: `scripts/check.sh fast`; rows `neoteletext-audio ""`, `"idl"`, `"ima"`, `"encode"`; `cargo build --target x86_64-unknown-none -p neoteletext-audio`; `cargo +nightly check --manifest-path fuzz/Cargo.toml`. The firmware image does not link this crate; `cargo xtask size` needs no run.

**U1. The root to its three files.** `src/profile.rs` takes `lib.rs:47-85`; `src/codec.rs` takes `Codec` 87-146, 148-158, 160-173, 175-178; `src/serial.rs` takes `serial_newer` 180-187. `lib.rs` keeps the doc, the lint lists, `extern crate`, the `mod` lines and adds `pub use profile::*; pub use codec::*; pub use serial::serial_newer;`. Visibility: none change (all were `pub` at the root; they stay `pub` and re-exported). Importers: none (`crate::Codec`, `crate::MAX_RECORD`, `crate::serial_newer` resolve through the re-exports; `input/src/lib.rs`, `cli/sound.rs`, the browser and the fuzz targets keep their root paths). Departure: `serial.rs` is fifteen lines; see section 3.3.

**U2. `record` and its frame.** `record/frame.rs` takes `RecordError` 65-82, `framed_length` 170-184, `record_length` 186-190, `split` 192-220, `write` 222-238, `Fields` 345-383; `record/tests.rs` takes 385-491 with `#![allow(clippy::indexing_slicing, clippy::unwrap_used, clippy::arithmetic_side_effects, clippy::panic)]`. `record.rs` keeps the rest and adds `mod frame; pub use frame::{RecordError, framed_length, record_length, split, write}; #[cfg(test)] mod tests;`. Visibility: `Fields` and its methods → `pub(super)` (used by `parse`, `object`, `control`). Importers: none (`input/control.rs:12`, `cursor.rs:25` keep `record::{…}`).

**U3. `idl` and its reassembler.** `idl/reassembler.rs` takes `SLOT_BYTES` 34-35, `Slot` 165-176, `Reassembler` with `Default` and `impl` 178-263; `idl/tests.rs` takes 265-374 with the four-lint allow. `idl.rs` adds `mod reassembler; pub use reassembler::Reassembler; #[cfg(test)] mod tests;`. Visibility: none change (`Fragment`, `FRAGMENT_DATA`, `MAX_FRAGMENTS` are `pub`). Importers: `receiver.rs:11` keeps `crate::idl::{Reassembler, fragment}`.

**U4. `ima`'s tests out.** `ima/tests.rs` takes 137-211 with the four-lint allow and the two inner `cfg(feature = "encode")` lines as they are. `ima.rs` adds `#[cfg(test)] mod tests;`.

**U5. `receiver` into intake, play and send.** `receiver/carriage.rs` takes `push_packet` 159-185 as `impl Receiver { … }` with its `use` lines 6-7, 10-11, 13-14 now without `cfg`; `receiver/play.rs` takes `try_start` 309-355, `start_waiting` 357-363, `start_armed` 365-374, `buffered_ms` 376-381; `receiver/send.rs` takes `send_sound` 383-390, `send_live` 392-419, `send_block` 421-434, `decode` 436-454 with its two `ima` arms. `receiver.rs` keeps the rest, the `cfg(feature = "idl")` on the `reassembler` field 43, the initialiser 60 and `reset` 143, and adds `#[cfg(feature = "idl")] mod carriage; mod play; mod send;`. Nine `cfg` attributes become four. Visibility: `bump`, `needs`, `duration_ms` → `pub(super)`; `try_start`, `start_waiting`, `start_armed`, `send_sound`, `send_live`, `send_block` → `pub(super)` (called across the three files); fields stay private, reached by the children. Importers: none (`receiver::Receiver` and `push_packet` keep their paths).

**U6. `store` into the entry model, the arena and the live ring.** `store/arena.rs` takes `define` 209-295, `find_space` 297-317; `store/live.rs` takes `set_live_cursor` 319-326, `live_block` 328-338, `slot_index` 340-349, `put_live` 351-407; `store/tests.rs` takes 469-618 with the four-lint allow. `store.rs` keeps `Entry`, `Defined`, `Stored`, `Store` and the remaining methods, adds `mod arena; mod live; #[cfg(test)] mod tests;`. Visibility: `put_live` → `pub(super)` (called by `put` 421); `find_space`, `slot_index` stay private to their files; `Entry::size`, `data_bytes`, `bitmap_bytes`, `index_table_bytes` and `Store::received` are private methods of the parent, reached by the children as descendants. Importers: none.

### 4.4 `neoteletext-audio-mix` (step M1)

Gate: `scripts/check.sh fast`; `cargo build --target x86_64-unknown-none -p neoteletext-audio-mix`; nothing in `features.rs` or the fuzz set names it.

**M1. The one file into five.** `src/ramp.rs` takes `UNITY`, `MIN_RAMP_MS` 38-41, `Ramp` 63-97, `level`, `scale` 565-573; `src/sound.rs` takes `SoundKey` 42-43, `STREAM_TARGET_MS`, `STREAM_RING_MS`, `STREAM_TRIM_PPM`, `PPM` 48-61, `Sound` 99-137; `src/voice.rs` takes `FRACTION_BITS`, `PHASE_SHIFT` 44-47, `Playing` 139-161, `Voice` 180-188, `begin` 510-536, `set_step`, `advance` 538-548, `interpolate` 550-563; `src/mixer.rs` takes `VOICES` 36-37, `Start` 163-178, `Mixer` 190-198, the `impl` 200-508 less the three stream methods, and adds `mod stream; #[cfg(test)] mod tests;`; `src/mixer/stream.rs` takes `stream` 239-252, `stream_samples` 254-275, `trim_streams` 471-495 as a second `impl Mixer`; `src/mixer/tests.rs` takes 575-757 with `#![allow(clippy::indexing_slicing, clippy::unwrap_used, clippy::arithmetic_side_effects, clippy::panic)]`. `lib.rs` keeps the doc, the lint lists, `extern crate alloc`, the `cfg(test) extern crate std`, `pub mod sinc`, the five `mod` lines and `pub use mixer::{Mixer, Start, VOICES}; pub use sound::{SoundKey, STREAM_TARGET_MS, STREAM_RING_MS, STREAM_TRIM_PPM};`. Visibility: `Ramp` and its methods, `level`, `scale`, `Sound` and its methods, `Playing`, `Voice`, `begin`, `set_step`, `advance`, `interpolate`, `FRACTION_BITS`, `PHASE_SHIFT`, `UNITY`, `MIN_RAMP_MS`, `PPM` → `pub(crate)`; `trim_streams` → `pub(super)` (called by `render` 359). The fields of `Sound` (`key`, `rate_hz`, `samples`, `forgotten`, `stream`, `written`) and of `Playing` (`key`, `whole`, `fraction`, `nominal`, `primed`, `looped`, `gain`, `duck_percent`, `fade_ms`, `stopping`, `step_whole`, `step_fraction`) and `Voice` (`playing`, `outgoing`, `pending`, `duck`) → `pub(crate)`: `mixer.rs` reads and writes them in `voice_sample` and `update_ducks`. This is the plan's widest seam and a departure from "fields stay private"; the alternative, keeping `Playing` and `Voice` in `mixer.rs`, leaves a 500-line file, and accessors for twenty fields would be a refactor. The seam is listed so the owner can choose the 500-line file instead. Importers: the browser's three paths are unchanged.

### 4.5 `neoteletext-input` (steps I1 to I6)

Gate for every I step: `scripts/check.sh fast`; row `neoteletext-input ""`; `cargo build --target x86_64-unknown-none -p neoteletext-input`; `cargo +nightly check --manifest-path fuzz/Cargo.toml` (targets `control_records`, `cursor_records`, `input_stream`).

**I1. The root to its two files.** `src/limits.rs` takes `lib.rs:45-76` (the ten limits, the two `const _` assertions, `LAST_ADDRESSABLE_PAGE`, `is_page`); `src/carriage.rs` takes `is_input_packet` 78-90. `lib.rs` keeps the doc, the lint lists, `cfg(test) extern crate std`, the `mod` lines and adds `pub use limits::*; pub use carriage::is_input_packet;`. Visibility: none change. Importers: none (`crate::is_page`, `crate::MAX_MESSAGE` and the external root paths resolve through the re-exports).

**I2. The one shared form.** Add `carriage::input_record(packet: &Packet, kind: u8) -> Option<Fragment>` (one fragment, first and last, whose byte 1 is `kind`) and call it from `control::from_packet` 216-219, `cursor::from_packet` 181-184 and `is_input_packet`. A code change, one commit, no path moves; the fuzz targets `control_records` and `cursor_records` exercise both callers.

**I3. `keys` and its tables.** `keys/one_byte.rs` takes `ONE_BYTE` 18-149; `keys/us_layout.rs` takes `us_base` 216-246; `keys/tests.rs` takes 248-313 with `#![allow(clippy::unwrap_used, reason = "a test")]`. `keys.rs` adds `mod one_byte; mod us_layout; pub use us_layout::us_base; #[cfg(test)] mod tests;`. Visibility: `ONE_BYTE` → `pub(super)` (read by `code`, `name`, `remaining`, and the tests through `super`). Importers: none (the browser's `keys` paths are root-level functions).

**I4. `event` into the model, the decoder and the encoder.** `event/decode.rs` takes `read` 271-285, `read_text` 287-308, `read_point` 310-319, `read_event` 321-393, `read_key` 395-433, `read_message` 566-585, `StreamDecoder`, `MAX_STREAM_ITEM`, `Default`, `impl` 587-640; `event/encode.rs` takes `write` 435-459, `write_point` 461-472, `point_flags` 474-476, `write_event` 478-564; `event/tests.rs` takes 642-792 with `#![allow(clippy::unwrap_used, clippy::indexing_slicing, clippy::panic, reason = "a test")]`. `event.rs` keeps 14-269 and adds `mod decode; mod encode; pub use decode::{read, read_message, StreamDecoder, MAX_STREAM_ITEM}; pub use encode::write; #[cfg(test)] mod tests;`. Visibility: the private constants `LAST_CORE`, `CORE_LAST_TYPE`, `ACTION`, `FUNCTIONAL`, `HAS_MODS`, `HAS_TEXT`, `HAS_BASE`, `KEY_RESERVED`, `HAS_PIXELS`, `POINTER_RESERVED`, `NEVER_UTF8`, `NEVER_UTF8_FROM` and `check_text` → `pub(super)`. `encode.rs` imports `super::decode::read` (the write-then-read-back check at 454). Importers: none; the browser's, the CLI's and `input_stream`'s `event::…` paths are kept.

**I5. `session` into the handshake, the filter, the count and the limiter.** `session/filter.rs` takes `filter` 257-318 as `impl Session`; `session/count.rs` takes `REMEMBERED`, `SERIAL_HALF` 16-20, `serial_after` 67-72, `sent` 336-351, `drop_oldest` 353-356, `acknowledged` 364-383; `session/limiter.rs` takes `SECOND_MS` 21-22, `allow` 320-334 as `impl Session`, `Limiter` with `Default` and `impl` 392-431; `session/tests.rs` takes 433-680 with `#![allow(clippy::unwrap_used, clippy::arithmetic_side_effects, reason = "a test")]`. `session.rs` keeps the rest and adds `mod filter; mod count; mod limiter; pub use count::REMEMBERED; pub use limiter::Limiter; #[cfg(test)] mod tests;`. Visibility: `filter` → `pub(super)` (called by `send` 236); `drop_oldest`, `serial_after`, `SERIAL_HALF` stay private to `count.rs`; `REMEMBERED` stays `pub` (the browser's `session::REMEMBERED`), as does `Limiter`; fields stay private, reached by the children. Importers: none.

**I6. `cursor`'s tests out.** `cursor/tests.rs` takes 188-260 with `#![allow(clippy::indexing_slicing, clippy::unwrap_used)]`; `cursor.rs` adds `#[cfg(test)] mod tests;`. `control.rs`'s 46-line module, `wire.rs`'s 59, `held.rs`'s 53, `modes.rs`'s 48 stay inline.

### 4.6 `neoteletext-qrkeyboard` (steps Q1 to Q5)

Gate for every Q step: `scripts/check.sh fast` (its `cargo test` runs `tests/wake.rs` and `tests/socket.rs`; `tests/relay.rs` only with `QRKEYBOARD_RELAY`). No feature rows, no bare-metal build, no fuzz target in the engine.

**Q1. The root to its parts.** `src/error.rs` takes `Error` with its two impls 58-93; `src/protocol.rs` takes the six constants 44-56; `random` 95-101 moves to `crypto.rs`. `lib.rs` keeps the doc, the lint list, the `mod` lines and adds `pub use error::Error; pub use protocol::*; pub use crypto::random;`. Importers: none (`crate::Error`, `crate::random`, `crate::MAX_FRAME_BYTES`, the CLI's and the browser's `RELAY` resolve through the re-exports).

**Q2. `crypto` into sealed frames and SPAKE2.** `crypto/sealed.rs` takes `NONCE_BYTES`, `TAG_BYTES`, `COUNTER_OFFSET`, `TAG_SEALED`, `SEALED_OVERHEAD` 29-38, `nonce` 79-85, `Sealer` 87-110, `Opener` 112-146; `crypto/spake2.rs` takes `SCALAR_BYTES`, `SPAKE2_M`, `SPAKE2_N` 43-48, `point`, `decode_point`, `encode`, `reduce` 155-177, `password_scalar` 179-186, `random_scalar` 188-202, `length_prefixed` 204-209, `Spake2`, `Spake2Result`, `impl` 211-281; `crypto/tests.rs` takes 283-369 with `#![allow(clippy::unwrap_used, clippy::indexing_slicing, clippy::arithmetic_side_effects)]`. `crypto.rs` keeps `SECRET_BYTES`, `SALT_BYTES`, `SHARE_BYTES`, `CONFIRM_BYTES`, `Role`, `hkdf`, `directional_keys`, `constant_time_equal`, `random` and adds `mod sealed; mod spake2; pub use sealed::{Sealer, Opener, NONCE_BYTES, TAG_BYTES, TAG_SEALED, SEALED_OVERHEAD}; pub use spake2::{Spake2, Spake2Result, password_scalar, random_scalar}; #[cfg(test)] mod tests;`. Visibility: `hkdf` → `pub(super)` (used by `finish` 270-271); `Sealer::new`, `Opener::new` → `pub(super)` (called by `directional_keys` 76); `reduce` → `pub(super)` (the tests' `scalar` helper). Importers: `message.rs:6`, `pairing.rs:8-11`, `phone.rs:9`, `screen.rs:12` keep `crate::crypto::{…}`.

**Q3. `net` into the stream, the HTTP client and the WebSocket.** `net/stream.rs` takes `Stream` 59-191; `net/http.rs` takes `MAX_BODY` 29-31, `request` 201-276, `host_header` 278-282; `net/websocket.rs` takes `FRAME_HEADER`, `CLOSE_CODE_BYTES` 34-37, `READS_AHEAD` 338-340, `read_socket` 342-367, `Reading` 369-436, `write_records` 438-445, `WebSocket` 447-606, `Drop` 608-616. `net.rs` keeps `CONNECT_TIMEOUT`, `RESPONSE_TIMEOUT`, `MAX_HEAD`, `READ_CHUNK`, `OsRandom`, `tls_config`, `parse`, `Incoming`, `Wake`, `Waker`, `LONGEST_WAIT`, `later` and adds `mod stream; mod http; mod websocket; pub use stream::Stream; pub use http::{request, MAX_BODY}; pub use websocket::WebSocket;`. Visibility: `tls_config`, `MAX_HEAD`, `READ_CHUNK`, `RESPONSE_TIMEOUT` → `pub(super)` (`MAX_HEAD` is read by `websocket.rs` 467, 478 and `http.rs` 231); `Wake`, `Waker::new`, `later` keep `pub(crate)`. Importers: `screen.rs:15`, `phone.rs:12`, the CLI's `net::{self, Incoming, WebSocket}` and `net::parse` — unchanged.

**Q4. `screen` into creation, waiting, relay control and messages.** `screen/wait.rs` takes `wait` 234-277, `next_deadline` 279-289, `turn` 291-331, `release_stale` 536-542; `screen/relay.rs` takes `control` 349-374, `peer_up` 376-395, `pin_failed` 397-402, `lock` 404-409, `clear_channel` 411-417; `screen/messages.rs` takes `binary` 419-481, `acknowledge` 483-487, `has_text` 489-491, `has_key` 494-534. `screen.rs` keeps the rest, the 11-line test inline, and adds `mod wait; mod relay; mod messages;`. Visibility: `connect`, `send_text`, `send_binary` (parent) → `pub(super)` (called by `turn` and the children); `control`, `binary` → `pub(super)` (called by `turn`); `clear_channel`, `pin_failed`, `lock` → `pub(super)` (called by `binary` and `turn`); `has_text`, `has_key` private to `messages.rs` until Q5; fields stay private.

**Q5. The layout tables to `config::Layout`.** The five tables `DPAD`, `COLOURS`, `TELETEXT`, `REMOTE`, `GAMEPAD` of `has_key` (`screen.rs:495-526`) and the `match` 527-533 move to `config.rs` as `impl Layout { pub(crate) fn has_key(&self, key: &str) -> bool; pub(crate) fn has_text(&self) -> bool }`, with `COLOURS` replaced by the existing `COLOUR_KEYS` 34 (the same four names); `screen/messages.rs` keeps two one-line forwarders or calls `self.config.layout.has_key(&key)` directly. A move of static data with a one-line call; the message says it is the one step in this crate that is not a pure move.

### 4.7 `xtask` (steps X1 to X4)

Gate: `scripts/check.sh fast` (which runs `xtask` itself for the four checks and the two font checks) and `cargo test -p xtask`.

**X1. `checks` into its four checks.** `checks/layers.rs` takes `FOUNDATION`, `CROSS_CUTTING`, `LAYER_TABLE` 8-38, `module_of` 64-69, `layers` 71-100, `uses` 102-114; `checks/deps.rs` takes `PERMITTED` 116-127, `dependencies` 129-177; `checks/constants.rs` takes `DATA_FILES`, `WATCHED_LITERALS` 210-215, `constants` 217-238, `contains_literal` 240-253; `checks/io.rs` takes `FORBIDDEN` 266-267, `io` 269-287, `forbid` 289-304. `checks.rs` keeps `rust_files` 40-50, `non_test_source` 52-62, `WORKSPACE_PREFIX`, `APPLICATION_CRATES` 179-208, `LIBRARY_CRATES` 256-265, `report` 306-316 and adds the four `mod` lines and `pub use layers::layers; pub use deps::dependencies; pub use constants::constants; pub use io::io;`. Visibility: `rust_files`, `non_test_source`, `report`, `APPLICATION_CRATES`, `LIBRARY_CRATES`, `WORKSPACE_PREFIX` → `pub(super)`. Importers: `main.rs:55-58` unchanged. Optional, as its own commit: `trace.rs:10-21 files` replaced by `checks::rust_files` made `pub(crate)` with an extensions parameter (pair 23).

**X2. `g3` into the geometry, the table and the text.** `g3/geometry.rs` takes `DESIGN_ROWS` 34-35, `signed` 39-41, `X`, `Y`, `Part`, `Shape` 45-82, the two impls 84-110, `inside_polygon` 115-133, `covers` 135-156, `rasterise` 159-169, `polygon`, `rect`, `union` 171-187, the stroke constants and helpers 193-231, `mirror` 346-367, `complement` 370-373; `g3/table.rs` takes `shape` 236-343 with its allow, which gains `reason = "one arm per position of Table 48"` from the comment at 235; `g3/tests.rs` takes 401-474 (no allow attribute). `g3.rs` keeps `CELL_WIDTH`, `HEIGHTS`, `FIRST_CODE`, `CODES` 27-33 and `text` 378-399, adds `mod geometry; mod table; #[cfg(test)] mod tests;`. Visibility: everything `table.rs` builds with — `X`, `Y`, `Part`, `Shape`, `polygon`, `rect`, `union`, the stroke constants, `light_vertical`, `light_horizontal`, `heavy_horizontal`, `stroke`, `mirror`, `complement` — and `rasterise`, `shape` → `pub(super)`. A wide seam (about fifteen items), accepted because `geometry.rs` is a small drawing language and `table.rs` its one user; the alternative is one 330-line file, which is also acceptable, and the owner may prefer it. Importers: `glyphs.rs:20` keeps `crate::g3::{CODES, FIRST_CODE, HEIGHTS, CELL_WIDTH, text}`.

**X3. `glyphs` into the Bedstead table, the G3 source and the required lists.** `glyphs/bedstead.rs` takes `SOURCE`, `TARGET`, `PROVENANCE`, `CHECKSUM_PREFIX`, `GLYPH_LINES` 30-43 as they apply, `Entry`, `parse` 45-68, `bedstead_source` 71-94, `check_bedstead` 270-285, `recorded_checksum` 288-295; `glyphs/g3_table.rs` takes `G3_TEXT`, `G3_TARGET`, `g3_source` 98-147; `glyphs/required.rs` takes `REQUIRED`, `FORMS`, `FIRST_CODE`, `LAST_CODE`, `Set`, `sets` 150-219, `required`, `required_text`, `forms_text` 222-268; `glyphs/tests.rs` takes 319-367 (no allow attribute). `glyphs.rs` keeps `generate` 298-317 and adds the three `mod` lines, `pub use bedstead::check_bedstead; #[cfg(test)] mod tests;`. Visibility: `bedstead_source`, `g3_source`, `required_text`, `forms_text`, `recorded_checksum` and the path constants → `pub(super)`. Importers: `main.rs:60` keeps `glyphs::check_bedstead`.

**X4. The ELF reader out of `size`.** `size/elf.rs` takes `Image` 96-104 and `read_elf` 197-264; `size.rs` adds `mod elf;` and uses `elf::{Image, read_elf}`. Visibility: both → `pub(super)`. The 23-line test stays inline in `size.rs`.

### 4.8 The fuzz targets and the firmware image

No step changes a file under `fuzz/` or `firmware/`. Steps U1 to U6 and I1 to I6 each run `cargo +nightly check --manifest-path fuzz/Cargo.toml` before committing, which resolves every path of section 1.8 against the re-exports; a failure there is a missing `pub use`, fixed in the same step. The firmware image links none of these crates; `cargo xtask size` is run once at the end of the engine's work as the full gate requires, not per step.

---

## 5. Risks particular to these crates

- **Items `run.rs` (today `main.rs`) needs in every build.** `commands::SoundOptions`, `commands::PLAYER_PACKETS_PER_SECOND` (a clap default at `args.rs`), `commands::sound`, `commands::write_text`, `commands::{view, slice, fetch}`, `terminal::text_area`, `commands::{convert_font, font_sets, contents}` must be defined without any feature. Steps C6 and C8 keep them in the ungated parent; a layout that gates `commands/sound.rs` whole fails `cargo xtask features` row `neoteletext-cli ""`. `commands::{qr, keyboard, KeyboardOptions}` may stay gated because the `run` arms that name them are (`main.rs:454-464` today).
- **`tests/not_in_build.rs` wording.** Its six tests assert `"not in this build"` and the back-quoted feature name (`not_in_build.rs:20-25`); every stub keeps its `not_in_build("…", "feature")` call unchanged through C4, C6, C7, C8.
- **No new roots; the allow attributes travel.** No step adds a crate root, so the four deny lists apply unchanged to every new file beneath them. Every `tests.rs` created in U2-U6, M1, I3-I6, Q2 carries, as its first line, the attribute its module has today (listed per step); a `tests.rs` without it fails the root's `deny` at the first `unwrap`. `neoteletext-app` and `neoteletext-cli` have no list, so their new test files need none; if a later decision adds the list to those roots, `pipe/codec.rs:333, 342, 363, 390-392` and `commands/sound/wave.rs` need `get` forms first.
- **The browser's pinned paths.** The browser pins `fb2dd8a` and imports the paths of sections 1.3, 1.5, 1.6 and 1.4; steps U1-U6, M1, I1-I6 and Q1-Q5 keep every one by `pub use`. A path that did move would need a pin move in the browser (`DEVELOPMENT.md` section 11: `native/Cargo.toml`, `native/fuzz/Cargo.toml`, both lockfiles, one commit), so the rule for these four crates is "no public path changes", and the re-export lines are part of each step's diff, not an afterthought. `neoteletext-app`'s one changed path (A7) has one importer, the CLI, fixed in the same commit.
- **Fuzz is built only on the remote, with nightly.** A broken path in `control_records`, `cursor_records`, `input_stream`, `audio_packets` or `audio_records` surfaces in the full gate's last stage (`check.sh:103-113`), an hour in; the per-step `cargo +nightly check --manifest-path fuzz/Cargo.toml` is what catches it on this machine, and needs the nightly toolchain installed here (it is not in `rust-toolchain.toml`).
- **Never a new file named `consts.rs`.** `cargo xtask check-constants` skips any file whose path ends `consts.rs` (`checks.rs:212`); the engine core's module is the only one meant. This plan names the constant files `profile.rs`, `codec.rs`, `limits.rs`, `protocol.rs`.
- **Tests last, because the checks cut at `#[cfg(test)]`.** `check-constants`, `check-io` (`checks.rs:57`) and `traceability` (`trace.rs:144`) stop reading a file at its first `#[cfg(test)]`. Every new file keeps its `tests` module, or `#[cfg(test)] mod tests;` line, last; a `#[cfg(test)]` helper placed above production code would hide that code from the checks, as `fetch.rs:378` does today until A8.
- **`missing_docs` and intra-doc links.** Every `pub` item in a new file needs its doc comment (they move with the item); items narrowed to `pub(super)` or `pub(crate)` need none. The CLI's new library exports one function. Intra-doc links name items by path (`event.rs:6-7`, `cursor.rs:64-67`, each `lib.rs` doc): after I4, I5, Q3 and A8 run `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`, which `check.sh` does not, since a broken link is a rustdoc warning only.
- **`unused_qualifications`.** A `use` line added for a moved item can make an existing fully qualified path redundant (`view.rs:341-352`, `present.rs:166-167`); the lint is `warn`, which the gate makes an error — drop the qualification in the same step.
- **The `allow(clippy::too_many_lines)` lines.** They travel with `run_web` (A8), `run` (C9) and `shape` (X2); A8 and X2 add the `reason` the comment beside each already gives, so that a later `allow_attributes_without_reason` lint finds nothing.
- **`cargo xtask features` has no rows for `write-text` alone, `audio-mix` or `qrkeyboard`.** The A and C gates above add the `write-text` build by hand; `audio-mix` and `qrkeyboard` have no features, so the workspace clippy and tests are their whole check. Adding the two rows to `features.rs` is a one-line change for `30-cross-cutting.md` to decide.
- **The third-level test directory in A8.** `fetch/transport/tests.rs` is the one place the plan goes three levels down, so that `reach`, `open` and `Connection::receive` stay private; `00-conventions.md` allows a third level where the second is itself a large concept, which a 320-line transport is.
- **Seams the owner may reject.** A9 (four fields of `Sets`), C9 (six fields of `Typing`), M1 (the fields of `Sound`, `Playing` and `Voice`) and X2 (fifteen geometry items) each widen visibility instead of adding methods; every one is listed under its step with the alternative, and choosing the alternative (a single larger file) is a one-step change to this plan, not a rewrite.

---

## 6. Seen, not part of this plan

For the owner, and for `30-cross-cutting.md`; none of these is a structure move.

- `neoteletext-app/src/input.rs:139`: `load_live` polls `source.poll` every 20 ms with `std::thread::sleep`, against the waiting rule of `DEVELOPMENT.md` section 6; the `Source::set_wake` hook (`source.rs:19`) exists for the viewer but this loop does not use it.
- Library code prints with the program's prefix: `session.rs:224` (`print_trace`), `sandbox.rs:26, 93, 153`, `input.rs:129, 212, 216, 221, 229, 240` write `neottx: …` to standard error from `neoteletext-app`, which another viewer embedding the crate would inherit.
- `neoteletext-audio-mix/Cargo.toml:16`: the dev-dependency on `neoteletext-audio` is unused by the crate's tests; `cargo machete` in the full gate reports or ignores it today.
- `firmware/test-image/target/` holds build products under the earlier name `tellytxt` (`tellytxt-test-image`, `libtellytxt_core-*.rlib`); whether that directory is ignored or committed is worth checking.
- RFC 1982 serial arithmetic is written twice: `neoteletext-audio/src/lib.rs:184-187 serial_newer` and `neoteletext-input/src/session.rs:69-72 serial_after`; `input` depends on `audio`, so the second could call the first (one public path would then be used across the crates).
- base64 is written three times: `neoteletext-cli/src/output/image.rs:98-120` (standard alphabet, for iTerm2), `neoteletext-qrkeyboard/src/message.rs:140-182` (URL alphabet), and `neoteletext-web::ws` for the handshake key; one home needs a crate both the CLI and `qrkeyboard` may use, which only `neoteletext-web` is.
- The two std network clients (section 2.4, pairs 1-7, and section 3.7) wait for a dependency decision.
- `neoteletext-cli/src/keyboard.rs:65-78 qr_page` writes TTI text by hand with its own control-code escaping, beside the formats crate's writer; replacing it changes the bytes written and is a behaviour question.
- `interact.rs:35-42 origin_of` derives an origin by splitting strings while `neoteletext_web::url::Url::origin` exists; whether the two agree on every input is a correctness question.
- `xtask/src/corpus.rs:20-24` computes SHA-256 by running `shasum`, while `glyphs.rs:276` and `noto.rs:47` use `neoteletext_web::sha256`.
- The test servers in `cli/tests/typing.rs`, `qrkeyboard/tests/socket.rs` and `tests/wake.rs` restate RFC 6455's opcode and length literals that `neoteletext_web::consts` already names.
- `scripts/check.sh` has no identical-panic-list check and `neoteletext-app` and `neoteletext-cli` have no list (section 2.7); `cargo xtask features` lacks the rows named in section 5.
