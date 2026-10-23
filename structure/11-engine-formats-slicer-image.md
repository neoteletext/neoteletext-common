# `neoteletext-formats`, `neoteletext-slicer`, `neoteletext-image`

| | |
|---|---|
| **Rests on** | A full reading of every `.rs` file of the three crates at engine `fb2dd8a` (61 files, 20,929 lines with the crates' `tests/` directories), measured by a brace-matching script for function and `impl` lengths; `cargo xtask`'s `checks.rs`, `features.rs` and `size.rs`; the `fuzz/` and `firmware/test-image/` manifests; a `grep` of every importer in the engine and in `~/devel/neoteletext-browser/native`. |
| **Phase** | E2 of `01-method-and-order.md`: after the core, before `neoteletext-web`. The three crates depend on the core only and on each other not at all, so their steps may run in any order; the order below is the one that keeps every feature row building. |
| **Public paths** | None changes. Every path another crate, a fuzz target, the firmware image, `xtask` or the browser imports today is kept by a re-export from the module that owns it now. |

## 1. The crates as they are

### 1.1 `neoteletext-formats`

**Purpose.** Layer L0 Ingress (`ARCHITECTURE.md` section 3): every byte source to `Packet { bytes: [u8; 42] }` and `PacketMeta`, through streaming readers that share one trait (`item::Reader`, fed bytes in pieces of any size, reporting `Item`s through a callback). Page files are read into one fixed-size `page::PageFile` and encoded to packets by `encode::encode_page`, so that files take the broadcast path (REQ-ARCH-004). The crate also holds the writers (T42, TTI, BDF font), the authoring builder of Level 2.5/3.5 test streams, the TTI page checker, the BDF font reader and converter, format detection, and the receiver's link resolution. Dependency: `neoteletext-core` only (REQ-GEN-017); dev-dependency `proptest`.

**Features** (decision E.61) and what each gates, as `lib.rs` declares it:

| Feature | Default | Gates | Implies |
|---|---|---|---|
| none | | `consts`, `item`, `text`, `t42`, `sliced` (the `ByteOrder` type), `transport` (the types), `log`, `page`, `detect` (with `NotCompiledReader` stand-ins) | |
| `transport` | yes | `pes` (whole module), `transport::reader` (`TsReader`, `crc32`), the `AnyReader::Transport`/`Pes` variants | |
| `sliced` | yes | `sliced::{record_packet, SlicedReader}` and their tests, by ten per-item `#[cfg]`s | |
| `pages` | yes | `encode`, `links`; `AutoReader::pass`'s page encoding; `write::{write_pages, write_page, in_transmission_order}` | |
| `tti` | yes | `tti`, `write::tti` (`write_tti`, `write_log_line`), `write::tests`, `links::tests`, `author` (with `std`) | `pages` |
| `ep1`, `edittf`, `dump` | yes | the module of each name | `pages` |
| `check` | yes | `check`; the `any_tti_lines` property test | `tti` |
| `bdf` | yes | `bdf` (`read`, `convert`, `source`), `write::font` | |
| `std` | no | `extern crate std`; `write` (the T42 writer always, the others with their features); `author` (with `tti`); the `enhancement_lines` property tests; `tests/golden_level25.rs`, `tests/level25.rs` | |

Integration tests carry `required-features`: `corpus` needs `pages`; `golden` needs `tti`; `golden_level25` and `level25` need `std,tti`. `cargo xtask features` builds the crate with `""`, `transport`, `sliced`, `pages`, `tti`, `ep1,edittf,dump`, `check`, `bdf`, `std` and `std,tti`.

**Module tree with line counts** (`tests.rs` files are `#[cfg(test)]` children):

```
lib.rs                      110   lint list, feature-gated mod declarations, re-exports
consts.rs                   410   container and file-format constants, one section per standard
item.rs                     265   Item, Diagnostic, DiagnosticKind, Capacity, Reader trait, offset helpers
text.rs                     132   Text<N> inline byte string, copy_prefix
t42.rs                      316   T42Variant, T42Reader (+113 inline test lines)
sliced.rs                   186   ByteOrder (always); record_packet, SlicedReader (feature) (+57 inline)
transport.rs                112   TsPacketSize, TsConfig, TeletextType, TeletextEntry, MAX_PROGRAMS
  transport/reader.rs       670   TsReader: sync lock, PAT/PMT sections, continuity, PES hand-off, crc32
  transport/tests.rs        243   stream builders (pub(crate)) and 8 tests
pes.rs                      488   PesParser state machine, PesReader (+120 inline pub(crate) tests)
dump.rs                     117   parse, DumpReader (+40 inline)
ep1.rs                      155   parse, enhancements, Ep1Reader
  ep1/tests.rs               89   ep1_file builder (pub(crate)) and 3 tests
edittf.rs                   393   base64 packing, parse, field parsers, write, EditTfReader
  edittf/tests.rs            96   4 tests
log.rs                      159   LogLevel, LogLine, LogRefused, read, check (+39 inline)
page.rs                     930   PageFile and every record type of the TTI extensions (+31 inline)
tti.rs                      955   decode_text, Args, field parsers, link targets, TtiReader (635-line impl)
  tti/tests.rs              857   fixtures (pub(crate)) and 24 tests
check.rs                    253   Severity, Problem, Finding, CheckOptions, check_page
  check/tests.rs            122   9 tests
bdf.rs                      815   Font, FontError(Kind), the 12x10/12x20 reader (+202 inline)
  bdf/convert.rs            430   ConvertError, MapError, read_map, convert (+224 inline)
  bdf/source.rs             406   SourceGlyph, SourceFont, read_source
detect.rs                   542   Format, Detection, detect, AutoConfig, NotCompiledReader, AnyReader, AutoReader
  detect/tests.rs           237   10 tests
encode.rs                   646   link row, checksum, packed lines, row codings, encode_page, X/28/0 synthesis, TransmissionClass
  encode/tests.rs           281   11 tests
links.rs                    276   Destination, resolve, ReceiverLinks, receiver_links (+142 inline, cfg tti)
write.rs                    134   PacketFilter, T42Writer, in_transmission_order
  write/tti.rs              317   write_tti, write_log_line
  write/font.rs              93   FontText, write_font
  write/tests.rs            178   6 round trips
author.rs                   317   AuthorError, shared helpers, MagazinePackets, Stream
  author/triplets.rs        393   RowScope, FlashMode, FlashRate, ObjectRef, LocalObject, Element, Triplets
  author/display.rs         377   LinkFunction, link(), DisplayPage
  author/objects.rs         284   public_number, pointer_place, ObjectPage
  author/mot.rs             210   MotLevel, object_link, Mot
  author/streams.rs         912   the REQ-TST-024 stream, five magazines
  author/tests.rs           501   12 tests
testing.rs                   72   test-only: Owned, run, same_in_any_chunks, packets, pages, diagnostics
robustness.rs               236   test-only: proptest robustness, reader_sizes
tests/corpus.rs             294   real captures, checksum order, national option order
tests/golden.rs              99   test-card raster checksums
tests/golden_level25.rs     157   authored-stream rasters; the TTI source on disk
tests/level25.rs            364   the authored stream through the decoder's stores
```

**Public paths and who imports them.** Every path found by `grep` in the engine (`crates/`, `xtask/`, `fuzz/fuzz_targets/`, `firmware/test-image/`) and in the browser (`native/`):

| Path | Imported by |
|---|---|
| `Item`, `Reader` (root), `item::Reader` | app `convert`, `extras`, `input`, `live`; cli `commands`, `keyboard`; fuzz `formats`, `tti_enhancement`, `channel_log`; firmware `main.rs:193–194`; browser `decoder/src/lib.rs:86–88`; `tests/*.rs` |
| `detect::{AutoConfig, AutoReader, Format}` | app `convert`, `input`, `live`; cli `options`; fuzz `formats`; firmware; browser decoder |
| `t42::T42Variant` | app `live`; cli `options`; fuzz `formats`; browser decoder |
| `transport::{TsPacketSize, TsConfig}` | app `input`; cli `options`; fuzz `formats` |
| `sliced::ByteOrder` | cli `options`; fuzz `formats` |
| `tti::TtiReader` | app `extras`; cli `commands`, `keyboard`; fuzz `tti_enhancement`, `channel_log`; `tests/golden.rs` |
| `page::{PageFile, EnhancementPacket, FastextLink, PageFunction, LinkDestination, INPUT_MODE_BITS}` | app `convert`, `extras`; cli `keyboard` (a `const _: () = assert!` on `INPUT_MODE_BITS`); fuzz `tti_enhancement`; browser `decoder/src/{lib,links}.rs` |
| `encode::{encode_page, RowCoding, packed_line_of, row_codes, transmission_class, TransmissionClass, CHECKSUM_HEADER_BYTES, checksum_word, page_checksum}` | app `convert`; fuzz `tti_enhancement`; `tests/{corpus,golden,level25}.rs` |
| `links::{receiver_links, INDEX_KEY, KEYS_WITH_INDEX}` | app `extras`; browser decoder |
| `log::{MAX_LOG_TEXT_BYTES, MAX_LOG_LINES_PER_PAGE, read, LogLine, LogLevel}` | fuzz `channel_log`; browser `decoder/src/lib.rs:36` (a `const _: () = assert!` on `MAX_LOG_TEXT_BYTES`), `protocol/src/decoder.rs:72` (doc) |
| `check::{CheckOptions, Severity, check_page}` | cli `commands` |
| `bdf::{read, FontErrorKind}`, `bdf::convert::{convert, read_map, ConvertError}`, `bdf::source::{SourceGlyph, read_source}` | cli `font`, `tests/font.rs`; fuzz `bdf`, `bdf_convert` |
| `consts::{FONT_MAP_MAX_FILE_BYTES, SOURCE_FONT_MAX_CHARACTERS, SOURCE_FONT_MAX_FILE_BYTES}` | cli `font` |
| `write::{write_tti, write_font, FontText, T42Writer, PacketFilter}` | app `convert`, `slice`; cli `font`, `tests/font.rs`; fuzz `tti_enhancement`, `bdf_convert`; browser decoder |
| `author::{self, AuthorError, DisplayPage, Stream, neutral_fields, streams, pointer_place}` | app `write_text`, `convert`; cli `tests/enhancement_reporting.rs`; `xtask/src/level25.rs`; browser decoder (`DisplayPage`); `tests/{golden_level25,level25}.rs` |

The remaining public items (section 2 names them per file) have no importer outside the crate.

**Specification to module:**

| Specification | Requirement | Module | Constants |
|---|---|---|---|
| EN 300 706 clause 7; T42 and its 43/45-byte and bit-reversed forms | REQ-INP-002 to 004 | `t42` | core `PACKET_BYTES*`, `FRAMING_CODE`, `CLOCK_RUN_IN` |
| ISO/IEC 13818-1 (2.4.3 packets, 2.4.4 PSI, Annex A CRC, 2.4.3.6 PES, 2.4.3.7 PTS); EN 300 421 RS(204,188); M2TS | REQ-INP-006 to 009 | `transport`, `transport::reader`, `pes` | `consts` sections 1–3 |
| EN 300 468 6.2.43/47/48 descriptors | REQ-INP-007 | `transport::reader::stream_descriptors`, `TeletextType`, `TeletextEntry` | `consts` "Descriptors" |
| EN 300 472 clause 4, EN 301 775 data units | REQ-INP-008 | `pes::PesParser::data_unit` | `consts` "Teletext in DVB" |
| V4L2 `v4l2_sliced_vbi_data` | REQ-INP-010 | `sliced` | `consts` "Linux sliced VBI records" |
| MRG TTI with vbit2 extensions; Appendix C forms; Appendix E links; `CU`/`IM` (REQ-INT-006/114); `LG` (REQ-INP-026); `CK` (REQ-CLI-006); packed lines (REQ-INP-023) | REQ-INP-013, 014, 023, 026 | `tti` (reader), `write::tti`, `page` (records), `log`, `check` | `consts` "TTI page files", "Pages of Levels 2.5 and 3.5" |
| EP1 (Softel Flair; `research/notes-formats.md` 6.1) | REQ-INP-015 | `ep1` | `consts` "EP1 page files" |
| edit.tf and zxnet addresses; RFC 4648 base64url | REQ-INP-016 | `edittf` | `consts` "edit.tf and zxnet addresses" |
| Raw screen dumps | REQ-INP-017 | `dump` | `consts` "Raw screen dumps" |
| EN 300 706 Annex B.2/B.7, Table 3 codings, Tables 4/6 X/28/0, clause 9.6.1 checksum, REQ-NAV-011 row 24 | REQ-INP-019, 024, REQ-ECC-007 | `encode` | core and `consts` |
| Tables 28/29 triplets, clause 10.5 object pages, 10.6 MOT, Annex A.1 sub-codes | REQ-INP-025, REQ-TST-024 | `author::{triplets, display, objects, mot, streams}` | `consts` `TERMINATION_*`, `OBJECTS_PER_*`, `SUBCODE_*`, `MOT_*` |
| Format detection by signature, then by scoring of headerless layouts | REQ-INP-005 | `detect` | `DETECTION_*` in `detect` |
| BDF 2.1/2.2, the REQ-FNT-002 profile; the converter's source cells | REQ-FNT-002, 010 | `bdf`, `bdf::source`, `bdf::convert`, `write::font` | core `FONT_MAX_*`, `CELL_*`; `consts` "Source fonts" |
| T42 writer | REQ-INP-018 | `write::T42Writer` | |

### 1.2 `neoteletext-slicer`

**Purpose.** Layer L0: sampled television lines to packets (area SLC), as the line slicer machine of REQ-FSM-002; the raw sampled video reader (REQ-INP-011); the synthetic signal generator (REQ-TST-060); float helpers for `no_std`. Floating point is allowed here (REQ-GEN-016); the fixed-point form (REQ-SLC-015) is Phase 2 and would replace `math` and the measuring functions only.

**Features:** `error-trait` (not default) adds `Display` and `core::error::Error` to `GeometryError`. Nothing else is gated.

```
lib.rs          70   lint list, mod declarations, re-exports, error_trait
consts.rs      164   derived bit counts, re-exported signal values, BT.470/BT.601 values, tuning (+15 inline)
fsm.rs         375   SlicerState/Event/Action, slicer_transition (the table), names (+61 inline)
generator.rs   426   LineBytes, line_bytes, packet_of, Echo, SignalParams, Rng, Generator, pulse shaping, quantise_* (+58 inline)
math.rs        287   floor/round/convert, sin_cos, atan2, frexp, ln, exp, sqrt (+59 inline)
raw.rs         331   Preset, RawGeometry, GeometryError, RawReader
slicer.rs      982   SampleFormat, Line, Config, Counters, Rejection, Sliced, RateParameters, Work, Slicer (475-line impl), Histogram (+53 inline, ignored)
tests.rs      1025   the crate's unit tests: fixtures, FSM rows, rates, timing, black level, framing, rejections, raw files, reports
```

**Public paths and importers:** root re-exports `GeometryError`, `Preset`, `RawGeometry`, `RawReader`, `Config`, `Counters`, `Line`, `Rejection`, `SampleFormat`, `Sliced`, `Slicer`. Imported by app `slice.rs:6, 23` (`Counters`, `Preset`, `RawGeometry`, `RawReader`, `Config`) and fuzz `slicer.rs:6` (`Config`, `Preset`, `RawGeometry`, `RawReader`). The modules `consts`, `fsm`, `generator`, `math`, `raw`, `slicer` are `pub`; nothing outside the crate names them.

**Specification to module:** REQ-FSM-002 table → `fsm::slicer_transition` (one arm per row; tests `row_01` … `row_12`); REQ-SLC-003 → `Slicer::load`, `back_porch_black`, `Histogram`; REQ-SLC-004/005 → `search`, `find_run_in`, `bit3_centre`, `measure`, `gate`; REQ-SLC-006/007/009 → `collect`, `bit`, `at`; REQ-SLC-008 and decision E.24 → `find_framing_code`; REQ-SLC-010 → `check_address`; REQ-SLC-012 → `SliceQuality` in `perform`; REQ-INP-011 presets → `raw::RawGeometry::preset`; REQ-TST-060 → `generator`; ITU-R BT.470/601/653 → `consts`.

### 1.3 `neoteletext-image`

**Purpose.** Layer L5 output adapters: `Rgba` palettes for the renderer's indices (REQ-RND-005/023/030), pixel-format conversion (REQ-RND-018), nearest and 4:3 scaling (REQ-RND-024), a fixed-Huffman PNG writer and a P6 PPM writer (REQ-RND-007), writing through the crate's `Sink` trait. `no_std`; dependency `neoteletext-core` with `render`.

**Features:** `error-trait` (Display/Error for `ConvertError`, `Overflow`, `ScaleError`, `PngError<E>`); `std` (a blanket `impl<W: std::io::Write> Sink for W`).

```
lib.rs            125   lint list, Sink trait, SliceSink, Overflow, error_trait
convert.rs        214   PixelFormat, ByteOrder, Rotation, ConvertError, grey, put, convert (+49 inline)
palette.rs        137   Rgba, CLUT0, base_colours, palette, colour_map_palette, clut0_of (+40 inline)
png.rs            466   PngError, CRC and chunks, BitWriter, fixed-Huffman tables, emit_match, write (+115 inline)
ppm.rs             81   decimal, write (+14 inline)
scale.rs          126   ScaleError, scaled_size, scale_indices, scale_rgb_smoothed (+17 inline)
tests/level25.rs  491   five hand-built Level 2.5/3.5 grids, golden checksums, PNG/PPM with side panels
```

**Public paths and importers:** `Sink`, `SliceSink`, `Overflow`; `convert::{PixelFormat, ByteOrder, Rotation, ConvertError, convert}`; `palette::{Rgba, CLUT0, base_colours, palette, colour_map_palette, clut0_of}`; `png::{PngError, write}`; `ppm::write`; `scale::{ScaleError, scaled_size, scale_indices, scale_rgb_smoothed}`. Imported by app `present.rs:18–19` (`palette::{Rgba, clut0_of, colour_map_palette, palette}`, `scale::{scale_indices, scaled_size}`); cli `commands.rs:23`, `view.rs:32`, `output/image.rs:18, 72, 85, 94` (`palette::Rgba`, `png::write`, `png::PngError::Sink`, `ppm::write`), `terminal.rs:69` (`scale::scaled_size`); browser `decoder/src/lib.rs:90` (`palette::{Rgba, colour_map_palette}`); `tests/level25.rs` (`Sink`, `png`, `ppm`, `palette`, `scale`).

**Specification to module:** PNG specification 5.2, 5.5/Annex D, 11.2.2; RFC 1950; RFC 1951 3.2.5/3.2.6 → `png`; Netpbm P6 → `ppm`; BT.601 luma → `convert::grey`; REQ-RND-004 (16/13) → `scale::scaled_size` by the core's `ASPECT_*`; Table 30 CLUT 0 → `palette::CLUT0`.

### 1.4 The numbers before the work (`01-method-and-order.md` section 5)

| | formats | slicer | image |
|---|---|---|---|
| files | 46 | 8 | 7 |
| largest / median lines | 955 / 279 | 1,025 / 353 | 491 / 137 |
| files over 500 | 9 | 2 | 0 |
| functions over 80 lines | 2 (`build_subpage`, `write_page`) | 2 (`slicer_transition`, a table; `report_impairments`, a test) | 1 (`png::write`) |
| `impl` blocks over 300 | 2 (`TtiReader` 635, `TsReader` 424) | 1 (`Slicer` 475) | 0 |
| test lines inline / in `tests.rs` / test-only modules | 1,021 / 2,604 / 308 | 254 / 1,025 / 0 | 246 / 0 / 0 |
| `cfg(feature)` sites inside shared files | 106 (32 in `detect.rs`, 24 in `robustness.rs`, 12 in `lib.rs`, 10 each in `sliced.rs` and `write.rs`) | 1 | 3 |

## 2. Findings

### 2.1 `neoteletext-formats`, file by file

**`lib.rs` (110).** Docs listing every module and feature (1–43); the lint lists (44–57); `extern crate std` (59–60); mod declarations grouped by feature (62–102); the root re-export (107); `testing` and `robustness` under `cfg(test)`. One concept. `transport` and `sliced` are declared unconditionally and gate their readers inside, while `pes` is gated here: three idioms for one need (section 2.5).

**`consts.rs` (410).** Constants of the container and file formats, each cited, in twelve sections by standard (11–381); two tests of the derived values (383–410). One concept; the only file of the crate that REQ-GEN-014's "constants module" names.

**`item.rs` (265).** `Item` (11–62); `Diagnostic` and its constructors (64–87); `DiagnosticKind`, 30 variants (89–221); `Capacity` (223–242); `trait Reader` (244–253); `pub(crate) saturate_u32`, `offset_of` (255–265), used by every reader. Imports `detect::Format`, `page::{IssueKind, PageFile}`, `transport::TeletextEntry` and `log::LogLine`: those four must stay compiled with no feature.

**`text.rs` (132).** `Text<N>` (7–91); `pub(crate) copy_prefix` (93–104), the REQ-GEN-019 byte loop that stands in for `copy_from_slice`; tests (106–132, 26). Two small concepts.

**`t42.rs` (316).** `RUN_IN_PREFIX`, `FRAMING_PREFIX` (14–17); `T42Variant` with `ALL`, `unit_bytes`, `prefix`, `packet` (19–76); `T42Reader` with `new`, `with_skip`, `variant`, `report_skipped`, `prefix_matches`, `resynchronise`, `push` (78–179); `impl Reader` (181–200); inline tests with `pub(crate) sample_packets`, `serialise` and 5 tests (202–316, 113 lines). The two `pub(crate)` helpers have no user outside the file: `detect/tests.rs:21–50` re-implements both.

**`sliced.rs` (186).** Ten per-item `#[cfg(feature = "sliced")]` lines on imports and items (8–20, 48, 73, 84, 93, 128); `ByteOrder` and `word` (22–44, always compiled); `record_packet` (46–70); `SlicedReader` (72–126); inline tests (128–186, 57).

**`transport.rs` (112).** The gated `mod reader` and `pub use reader::{TsReader, crc32}` (12–15); `MAX_PROGRAMS`; `TsPacketSize`; `TsConfig`; `TeletextType`; `TeletextEntry` (16–109); `pub(crate) mod tests` under `cfg(all(test, feature = "transport"))`. Types only; the clean form of the type/reader split.

**`transport/reader.rs` (670).** Consts (22–34); `impl TsPacketSize { leading_bytes }` (36–44); `Section`, `Push` (46–107); `Program` (109–116); `Continuity`, `check_continuity` (118–141); `pub fn crc32` (143–155); `Header` (157–166); `TsReader` (168–188); **`impl TsReader`, 424 lines (190–613)**: construction and buffer operations (190–252), `confirmed`, `lock`, `process` (254–333), `header`, `packet`, `teletext_packet` (335–425), `section_packet`, `append_section`, `section`, `pat_section`, `pmt_section`, `stream_descriptors` (427–612, the last 51 lines); `read_length`, `vbi_data_lists_teletext` (615–634); `impl Reader` with the manual buffer shift and its REQ-GEN-019 comment (636–670). Four concepts in one impl: byte buffering and sync lock (REQ-INP-006), the packet header and continuity (13818-1 2.4.3), PSI section reassembly and PAT/PMT/descriptor walking (2.4.4, EN 300 468), and the PID selection policy with the hand-off to `PesParser`.

**`transport/tests.rs` (243).** `pub(crate)` consts and builders `packetise`, `section`, `pat`, `pmt`, `sample`, `stream`, `flatten`, `expected_packets` (23–133; `flatten` and `stream` used by `detect/tests.rs:116, 167, 180, 182`); 8 tests (135–243).

**`pes.rs` (488).** Consts (19–31); `State` (33–49); `PesParser` (51–72); `impl PesParser`, 256 lines (74–329): control (`new`, `begin`, `abort`, `feed`, `finish`, skipped-byte bookkeeping, `end_of_packet`, `step`, `count_byte`, 74–187), header (`hunt`, `header_byte` 52 lines, `finish_header`, 189–267), data units (`unit_byte`, `data_unit`, 269–328); `pts_microseconds` (331–339); `PesReader` and `impl Reader` (341–365); inline `pub(crate) mod tests` with `data_unit`, `pes_packet` and 4 tests (367–488, 120 lines), the builders used by `transport/tests.rs:17` and `detect/tests.rs:123, 184`.

**`dump.rs` (117).** `parse` (15–30); `DumpReader` (32–74, "hold the whole input, parse at `finish`"); inline tests (76–117, 40). One concept.

**`ep1.rs` (155).** `LEVEL1_BYTES`, `EP1_MAX_BYTES` (20–25); `pub(crate) apply_designation` (27–33, used only at line 46 of the same file, and the only reason `ep1` imports `encode::DESIGNATION_GROUP_SHIFT`, a core constant re-exported there); `parse` (35–78); `enhancements` (80–106); `Ep1Reader` (108–152), whose `feed` is `dump.rs:56–60` line for line. `ep1/tests.rs` (89): `pub(crate) StoredPacket`, `ep1_file` (14–43, used by `detect/tests.rs:126, 186`); 3 tests.

**`edittf.rs` (393).** Consts (21–37); base64url codec `base64_value`, `unpack_codes`, `pack_codes` and `hex_value` (39–97); `parse` (99–146); `field_value` (148–194); `fastext_field`, `enhancement_field` (196–239); `write_hex`, `pub fn write` (241–309, 59 lines); `EditTfReader` (311–390), whose `feed` and `finish` are `tti.rs:924–951` line for line. Four concepts: codec, parser, writer, line reader. `edittf/tests.rs` (96): `pub(crate) written` (no outside user); 4 tests.

**`log.rs` (159).** The `LG` record: constants, `LogLevel`, `LogLine`, `LogRefused`, `BIDI_CONTROLS`, `read`, `check` (12–117); inline tests (119–159, 39). One concept.

**`page.rs` (930).** 18 capacity constants (16–60); `EnhancementPacket`, `RawBody`, `RawPacket`, `FastextLink` (62–98); `LinkKey`, `LinkLine`, `LinkDestination`, `NumberLink`, `TextLink` (100–250); `CursorLine`, `INPUT_MODE_BITS`, `ModesLine` (252–284); `FieldKind`, `FormField`, `FormOption`, `FormMethod`, `Form` (286–507); `IssueKind`, `Warning`, `PageIssue` (509–624); `PageFunction` (626–633); `PageFile` and `pub(crate) DEFAULT_ADDRESS` (635–693, the constant used by `tti.rs`); `impl PageFile`, 164 lines (695–858); `PartialEq`, `Eq`, `Default` (860–896); inline tests (898–930, 31). Six record families: packet-level records, the Link Extension (Appendix E, decision E.88), the interaction lines (REQ-INT), the Form Extension (Appendix C), the checker's issues and warnings (REQ-CLI-006), and the page with its PS-word mapping (decision E.21).

**`tti.rs` (955).** Consts incl. `PAGE_COMMANDS` (22–46); `DecodedText`, `decode_text` (48–92); `Args` (94–121); `parse_number`, `hex`, `decimal`, `flag`, `page_address`, `result_page`, `subcode`, `service_name` (123–192); `link_address`, `link_destination`, `link_target` (194–239); `TtiReader` (241–269); **`impl TtiReader`, 635 lines (271–905)**: `new` and diagnostics (271–307), `end_line`, `command`, `page_command` (70 lines, with `IM`, `RE`, `PF`, `CK`, `FP`, `FT`, `FH`/`TF` inline) (309–427), `log_line` (429–444), `page_number`, `description`, `output_line` (446–508), `packed_line` 73 lines (510–582), `fastext_line` (584–603), `link_line`, `number_link_line`, `cursor_line`, `text_link_line` (605–699), `set_text`, `field_definition`, `field_parameters` 66 lines, `option_line`, `form_submission`, `finish_form` (701–897), `emit` (899–904); `mark_cells` (907–922); `impl Reader` (924–952). Twelve TTI record families in one impl.

**`tti/tests.rs` (857).** `pub(crate)` fixtures `packed_line`, `read`, `full_page` (24–76), `FORM_EXAMPLE` (235–253), `enhancement_pages`, `packet_line`, `packets_of` (400–475), used by `detect/tests.rs:218`, `check/tests.rs:5`, `write/tests.rs:9, 131, 141`; 24 tests grouped by command family (78–154 lines; 156–232 links; 255–351 forms; 353–393 encoding; 477–604 enhancement pages; 606–695 addresses and text links; 697–776 `TF`, `IM`, `CU`; 778–857 `LG`). Six `cfg(feature = "std")` islands for writer round trips inside the reader's tests.

**`check.rs` (253).** Constants (14–24); `Severity`, `Problem`, `Finding`, `CheckOptions` (26–87); text scans (89–144); `check_links`, `check_label`, `check_form` (146–217); `check_page` (219–250). One concept. `check/tests.rs` (122): 9 tests.

**`bdf.rs` (815).** `pub mod convert; pub mod source;` (22–23); consts (25–52); `Font`, `FontError`, `FontErrorKind` (54–142); `Section`, `Character`, `Header` (144–193); `read` (195–218); `Parser` and its 261-line impl (220–487); the BDF line grammar `split_keyword`, `numbers`, `integer`, `property_value`, `once`, `keep`, `check_properties`, `misplaced_or_unknown`, `insert` (489–610), four of which `source.rs` imports as private items of its parent (`source.rs:11, 222, 276, 310`); inline tests (612–815, 202 lines). **`bdf/convert.rs` (430):** `ConvertError`, `MapError` (23–53); `read_map` (55–90); `convert` (92–138); `tall_rows`, `cell_rows`, `doubled` (140–183); `decimal`, `hexadecimal` (185–203); inline tests (205–430, 224 lines, the last under `cfg(feature = "std")`). **`bdf/source.rs` (406):** `SOURCE_CELLS` and consts (17–31); `SourceGlyph`, `SourceFont` (33–69); `Section`, `Character`, `Header` (71–105); `read_source` (107–128); `Parser` and its 238-line impl (130–374); `size`, `place` (376–406). One concept, but a second copy of the `bdf.rs` parser's shape.

**`detect.rs` (542).** Twelve gated import lines (9–38); `DETECTION_*` and scoring consts (40–53); `Format` with `is_compiled` (55–91); `Detection` (93–107); the detector `without_bom`, `looks_like_edittf`, `looks_like_tti`, `transport_offset`, `address_quality`, `score_t42`, `score_sliced`, `detect_binary`, `detect` (109–284); `AutoConfig` (286–300); `NotCompiledReader` (302–333); `AnyReader` with one `cfg` per variant and per arm (335–443); `State`, `AutoReader` with `pass` (two `pages` cfgs), `decide` (445–539). 32 cfg sites, the densest file of the crate; most belong to `AnyReader`. **`detect/tests.rs` (237):** duplicates of `t42::tests::{sample_packets, serialise}` (20–50); `sliced_stream` (86–100); 10 tests, five under feature cfgs that test absent formats (decision E.61).

**`encode.rs` (646).** Re-exports and consts (35–57); `LinkRow`, `pub(crate) key_colour`, `pub(crate) Prompt`, `pub(crate) draw_link_row`, `link_row` (59–132, the row-24 drawing shared with `links.rs`); `page_checksum`, `checksum_word` (134–163); `raw_packet`, `packed_line_of`, `packed_character`, `pack_triplets`, `unpack_triplets` (165–231); `RowCoding`, `row_coding`, `is_enhancement_page`, `row_bytes`, `row_codes`, `packed_row`, `nibble_row` (233–358); `transmitted_rows`, `fastext_links`, `triplets_with_marks`, `encode_page`, `emit_rows`, `emit_enhancements`, `emit_raw` (360–535); `default_clut_2_and_3`, `page_enhancement_packet`, `second_g0_value` (537–606); `TransmissionClass`, `transmission_class` (608–643). Seven concepts. **`encode/tests.rs` (281):** 11 tests, one of which (`ep1_language_designations_name_their_languages`, 26–47) tests `consts::EP1_LANGUAGES`, not the encoder.

**`links.rs` (276).** `Destination`, `resolve`, `resolve_parts`, `key_place`, `ReceiverLinks`, `receiver_links` (17–131); inline tests under `cfg(all(test, feature = "tti"))` (133–276, 142 lines). One concept.

**`write.rs` (134).** `PacketFilter` (17–25); `T42Writer` with `passes`, `write_packet` and the `pages`-gated `write_pages`, `write_page` (27–111); `in_transmission_order` (`pages`) (113–121); the gated `tti`, `font` and `tests` declarations (123–134). Ten cfg sites over three features. **`write/tti.rs` (317):** text and triplet writers (18–45); `write_field` 63 lines (47–109); `write_destination`, `write_fastext` (111–164); **`write_page`, 92 lines (166–257)**: head, rows with fields, X/26, raw packets, `FL`, `LN`, `LK`, `LT`, `CU`, `IM`, form lines, `CK`; `write_form_lines`, `write_log_line`, `write_tti` (259–317). **`write/font.rs` (93):** one concept. **`write/tests.rs` (178):** 6 round trips.

**`author.rs` (317).** Mod declarations (20–24); `AuthorError`, `Result` (55–79); `colour`, `address`, `default_clut_0_and_1`, `neutral_fields`, `neutral_fields_level_35` (81–122); `new_page`, `enhancement_subcode`, `raw_line`, `push_raw` (124–160), private helpers that the child modules reach as descendants; `MagazinePackets` (162–208); `Stream` (210–314). **`author/triplets.rs` (393):** `RowScope`, `FlashMode`, `FlashRate`, `ObjectRef`, `LocalObject` (`pub(super)` fields), `pub(super) Element`, `row_address`, `Triplets` with 32 builder methods and `pub(super) resolved` (impl 212 lines). **`author/display.rs` (377):** `PAGE_TRIPLETS` (27–28, the same derivation as `encode.rs:51`), `LinkFunction`, `VALID_*`, `link`, `no_link`, `null_link`, `DisplayPage` with `lay_out` (52 lines) and `build` (43). **`author/objects.rs` (284):** `public_number`, `pointer_place`, `ObjectPage`; **`build_subpage`, 101 lines (178–278)**: definition sequence and markers, pointer tables, assembly by `triplet_location`, sub-code. **`author/mot.rs` (210):** one concept. **`author/streams.rs` (912):** consts (46–86); helpers (88–137); `stream`, `display_pages` (139–162); magazine 1 (164–730: objects, table, index, colour maps, screen and row colours, side panels, sizes, flash, G3/G1, G2, every mode, sizes by X/26, clause 13.9, Annex C.2, local/public/global objects); magazines 2/3 links (732–779); magazine 4 default objects (781–832); magazine 5 links (834–863); magazine 7 packets (865–912). One concept, sectioned by banner comments. **`author/tests.rs` (501):** `BOTH` (duplicate of `streams.rs:47`); worked-encoding tests (53–345); TTI round trips of the builders and the stream (347–501).

**`testing.rs` (72), `robustness.rs` (236).** Test-only modules at the crate root: the reader harness (`Owned`, `run`, `same_in_any_chunks`, filters); the proptest robustness checks with one `cfg` per reader (24 sites), the `tti_enhancement` fuzz target as a property test, `reader_sizes`.

**`tests/`.** `corpus.rs` (294): real captures from `$NEOTELETEXT_CORPUS`, passes with a note when absent. `golden.rs` (99): `FORMAT_VERSION = 3`, `tests/golden/raster.txt`. `golden_level25.rs` (157): `FORMAT_VERSION = 7`, `tests/golden/authored-level25.txt`, and `authored_tti_source_is_current` against `tests/pages/level25/` (46 files). `level25.rs` (364): the stream through the decoder's stores. Each defines its own `root()` and `fnv()`.

### 2.2 `neoteletext-slicer`, file by file

**`lib.rs` (70), `consts.rs` (164), `fsm.rs` (375), `math.rs` (287), `raw.rs` (331).** Each one concept. `fsm::slicer_transition` (97–253) is 157 lines by design and carries `allow(clippy::match_same_arms, clippy::too_many_lines)` with the reason (one arm per REQ-FSM-002 row). `raw.rs` holds the preset table (19–51, 104–197) and the frame/field/line splitter (199–331).

**`generator.rs` (426).** Consts (32–51); `LineBytes`, `line_bytes`, `packet_of` (53–76); `Echo`, `SignalParams` (78–147); `Rng` with its four constants (149–209); `Generator` (211–303); `bit_of`, `raised_cosine`, `sync_and_burst` (305–343); `quantise_u8`, `quantise_u16le` (345–359); inline tests (361–426, 58), one of which asserts `[0x55, 0x55, 0x27]` at line 388. Five small concepts; the PRNG is the separable one.

**`slicer.rs` (982).** Consts (55–94, incl. the `FRAMING_OFFSETS` const fn); `SampleFormat`, `Line`, `Config`, `Counters`, `Rejection`, `Sliced` (96–246); `RateParameters`, `complex_multiply` (248–294); `Candidate`, `Work` (296–341); `Slicer` (343–356); **`impl Slicer`, 475 lines (358–832)**: accessors (358–408), the machine driver `slice`, `slice_traced`, `perform` (410–507), black level `load`, `back_porch_black` (513–576), run-in `search`, `find_run_in` 72 lines, `bit3_centre` (582–689), `measure`, `gate` (695–741), `find_framing_code` (747–778), `collect`, `bit`, `at`, `run_in_position` (784–831); `check_address`, `renormalise` (834–847); `Histogram` (849–920); compile-time asserts (922–926); inline ignored throughput test (928–982, 53) using `std::time::Instant::now()` at 946.

**`tests.rs` (1,025).** `#![allow]` of twelve lints; fixtures with `pub(crate) RATES`, `samples_per_line`, `random_packet`, `render` (38–163; the last two used by `slicer.rs:936`); REQ-FSM-009 rows (165–390); rates and noise (392–432); timing and bit rate (434–513); black level and amplitude (515–608); framing (610–638); rejections and hostile input (640–768); raw files (770–906); two ignored reports (908–1025, `report_impairments` 92 lines). The only crate here with every unit test in one file.

### 2.3 `neoteletext-image`, file by file

**`lib.rs` (125), `convert.rs` (214), `palette.rs` (137), `ppm.rs` (81), `scale.rs` (126).** Each one concept with a small inline test module. `lib.rs` holds the `Sink` trait beside the crate root (34–86), small enough to stay.

**`png.rs` (466).** PNG consts (16–34); `PngError` (36–46); CRC table and `chunk` (48–84); `BitWriter` (86–137); fixed-Huffman `literal_code`, `LENGTH_BASE`, `DISTANCE_BASE`, `emit_match` (139–240); **`write`, 103 lines (242–348)**: validation, IHDR/PLTE/tRNS, zlib header, the per-row Adler and two-distance match search, end of block, IEND; inline tests with an independent `inflate_fixed` (350–466, 115). Three concepts: the PNG container, the deflate encoder, the image writer.

**`tests/level25.rs` (491).** Grid-building fixtures (49–285, five demonstration grids); harness (287–372, with two vector sinks at 336–344 and 442–450); four tests. Under the 500-line ceiling; left as it is.

### 2.4 Duplication, including constants defined twice

| Shape | Where | Note |
|---|---|---|
| Line-splitting `feed`/`finish` | `tti.rs:924–951` ≡ `edittf.rs:366–389` | identical: buffer, `overflow`, `line_offset` at the first byte, `end_line` on `\n` |
| Whole-input `feed` | `dump.rs:55–60` ≡ `ep1.rs:133–137` | identical; `finish` differs only in the size test |
| Whole-buffer line loop | `bdf.rs:205–216` ≡ `bdf/source.rs:115–126` | identical 12 lines |
| Skipped-byte run `Option<(u64, u32)>` with `report_skipped` | `t42.rs:95–96, 130–134, 143–154`; `pes.rs:70–72, 125–135`; `transport/reader.rs:179, 235–252` | three copies of one small state machine |
| Digit parsing | `tti.rs:123–144` (bounded to 8 bytes); `edittf.rs:92–97` (8); `bdf/convert.rs:185–203` (`decimal` 10, `hexadecimal` unbounded in length); `bdf.rs:511–528` (signed) | four parsers, three bounds; the `8` at `tti.rs:127` and `edittf.rs:93` is unnamed |
| BDF parser pair | `bdf.rs:146–161` / `source.rs:73–81` (`Section`); `bdf.rs:228–255` / `source.rs:138–173` (line checks); `bdf.rs:364–389` / `source.rs:256–278` (`between`, identical); `bdf.rs:457–461` / `source.rs:337–341` (hex rows) | two parsers of one grammar |
| Sorted insert by code point | `bdf.rs:597–610` (`insert`); `bdf/convert.rs:126–135` (inline) | same `binary_search_by_key` + `rotate_right(1)` |
| Triplet unpacking by `as_chunks::<3>()` + `hamming2418` | `encode.rs:190–192`, `encode.rs:329–332`, `tti/tests.rs:465–467`; raw bytes `ep1.rs:95–103` | |
| Test fixtures | `t42.rs:210–231` and `detect/tests.rs:21–50` (`sample_packets`, `serialise`); `sliced.rs:134–145` and `detect/tests.rs:86–100` (sliced records); `encode_all`/`packets_of`/`encoded` in `encode/tests.rs:14–18`, `tti/tests.rs:471–475`, `author/tests.rs:47–51`, `tests/level25.rs:49–53`; "read a TTI into pages" in `author/tests.rs:348–359`, `links.rs:140–151`, `tests/golden.rs:44–52`, `tti/tests.rs:779–792`; `fnv` and `root` in `tests/golden.rs:34–40`, `tests/golden_level25.rs:50–56`, `image/tests/level25.rs:41–47`; `VecSink` in `png.rs:457–465`, `image/tests/level25.rs:336–344` and `442–450`; decoder-feed loops in `tests/golden.rs:53–58`, `golden_level25.rs:69–79`, `level25.rs:33–47`, `links.rs:251–255` | |
| **Constants defined twice** | `PAGE_TRIPLETS` (`encode.rs:51` private; `author/display.rs:28` pub; same derivation `DESIGNATION_CODES * TRIPLETS_PER_PACKET`); `VERSIONS` (`bdf.rs:52`, `bdf/source.rs:27`); `NS_PER_SECOND` (`generator.rs:33`, `slicer.rs:56`); `ROW_DIGITS`/`ROW_PAD_BITS` (`bdf.rs:44–46` as `u32`, `write/font.rs:14–16` as `usize`); `BOTH: ObjectUsage(0b11)` (`streams.rs:47`, `author/tests.rs:25`); `LINE_US = 64` (`tests/level25.rs:30`, `golden_level25.rs:41`; inline `* 64` at `golden.rs:56`); the `TERMINATION` triplet (`encode.rs:57`; inline at `tti/tests.rs:41`, `edittf/tests.rs:77`, `ep1/tests.rs:61`); two unrelated `pub const LINE_BYTES` (`tti.rs:24` = 512, `edittf.rs:23` = 4096) beside `raw::MAX_LINE_BYTES` | against `00-conventions.md` section 8 and `DEVELOPMENT.md` section 6 |

### 2.5 The three `cfg` idioms

| Idiom | Where | Sites |
|---|---|---|
| The whole module gated in `lib.rs` | `pes`, `dump`, `ep1`, `edittf`, `tti`, `check`, `bdf`, `encode`, `links`, `write`, `author` | 12 in `lib.rs` |
| A gated submodule under an ungated parent of types | `transport.rs` (`mod reader`) | 3 |
| Per-item attributes inside a shared file | `sliced.rs` (10), `write.rs` (10: `pages` on three items, `tti`/`bdf` on submodules and re-exports), `detect.rs` (32: per-variant on `AnyReader`, per-arm in `new` and `reader`, gated imports, `pass`), `robustness.rs` (24, one per reader under test), `tti/tests.rs` (6 `std` islands), `detect/tests.rs` (5) | 87 |

Test gating takes two forms as well: `#[cfg(all(test, feature = "x"))] mod tests;` on the declaration (`transport.rs`, `write.rs`, `links.rs`, `sliced.rs`) and `#![cfg(feature = "std")]` inside an integration test that already has `required-features` in `Cargo.toml` (`golden_level25.rs`, `level25.rs`).

### 2.6 Where tests are

| Place | Files |
|---|---|
| Inline `mod tests` at the end of the file | formats: `t42` (113), `sliced` (57), `dump` (40), `log` (39), `text` (26), `consts` (27), `page` (31), `pes` (120, `pub(crate)`), `bdf` (202), `bdf/convert` (224), `links` (142); slicer: `consts` (15), `fsm` (61), `generator` (58), `math` (59), `slicer` (53), `lib` (8); image: `convert` (49), `palette` (40), `png` (115), `ppm` (14), `scale` (17), `lib` (11) |
| `tests.rs` beside the module | formats: `transport`, `tti`, `ep1`, `edittf`, `check`, `detect`, `encode`, `write`, `author` |
| Crate-level `src/tests.rs` | slicer (1,025) |
| Test-only modules in `src/` | formats `testing.rs`, `robustness.rs` |
| `crates/<crate>/tests/` | formats `corpus`, `golden`, `golden_level25`, `level25`; image `level25`; slicer none |

The placement is not by size: `bdf.rs` keeps 202 inline lines while `ep1` has 89 in a file. Against the convention's 60-line rule, `t42`, `pes`, `bdf`, `bdf/convert`, `links`, `png` and the slicer's `fsm` are inline test modules that belong in `tests.rs`.

### 2.7 Golden files and fixtures

| What | Where | Read by |
|---|---|---|
| `tests/golden/raster.txt` (format 3) | repository `tests/golden/` | formats `tests/golden.rs` |
| `tests/golden/authored-level25.txt` (format 7) | | formats `tests/golden_level25.rs` |
| `tests/golden/raster-level25.txt` (format 6) | | image `tests/level25.rs` |
| `tests/pages/testcard.tti` | repository `tests/pages/` | formats `tests/golden.rs` |
| `tests/pages/level25/*.tti` (46 files, written by `author::streams`) | | formats `tests/golden_level25.rs` (`authored_tti_source_is_current`) |
| `tests/corpus-manifest.txt`; captures from `$NEOTELETEXT_CORPUS` | repository `tests/`; outside the repository | formats `tests/corpus.rs` |
| `tests/oracles/` (zvbi scripts, `zvbi-known-differences.txt`) | repository | by hand |
| `fuzz/corpus`, `fuzz/regressions` | `fuzz/` | the fuzz targets, replayed first |
| In-code fixtures | `tti/tests.rs`, `transport/tests.rs`, `pes` tests, `ep1/tests.rs`, `bdf` tests, `bdf/convert` tests, slicer `tests.rs`, image `tests/level25.rs` | the tests beside them and, through `pub(crate)`, `detect`, `check` and `write` |
| `docs/traceability.md` | generated by `cargo xtask traceability` | names source files by path |

All regenerate with `NEOTELETEXT_UPDATE_GOLDEN=1`; none changes under this plan, since no renderer, encoder or stream code changes.

## 3. The target layout

### 3.1 The one `cfg` idiom

A feature's code lives in files of its own, declared with one `#[cfg(feature = "...")] mod` in the parent (`00-conventions.md` section 3). The crate already does this for eleven modules in `lib.rs` and for `transport::reader`; the plan brings `sliced` and `write` to it. Two places keep `cfg` on items inside a shared file, and each is the convention's own exception (one item with two forms): `detect/any.rs`, where `AnyReader` is the one enum whose variants exist per feature (decision E.61 says why a `match` with a wildcard cannot replace it), and `detect/auto.rs`, where `pass` wraps the callback only when `pages` is compiled. `robustness.rs` keeps one `cfg` per reader under test, which is the test's subject. The re-export that accompanies a gated `mod` (`#[cfg(feature = "pages")] pub use pages::in_transmission_order;`) is part of the idiom, not a departure.

### 3.2 `neoteletext-formats`

```
lib.rs                       110   unchanged
consts.rs                    410   unchanged (one constants module, sectioned by standard; under the ceiling)
item.rs                      265   unchanged
text.rs                      132   unchanged
lines.rs                     ~80   NEW (step 14 only): Lines<const N>, the bounded line splitter shared by tti and edittf
t42.rs                      ~205   T42Variant, T42Reader; #[cfg(test)] mod tests;
  t42/tests.rs              ~115   the inline module (202–316)
sliced.rs                    ~45   ByteOrder; #[cfg(feature = "sliced")] mod reader; the gated pub use
  sliced/reader.rs          ~160   record_packet, SlicedReader, impl Reader (46–126); inline tests (57 lines, under 60)
transport.rs                 112   unchanged
  transport/reader.rs       ~320   consts; leading_bytes; Header; TsReader; impl: new, selected_pid, buffer ops, confirmed, lock,
                                   process, header, packet, teletext_packet; impl Reader; mod section; mod tables
    transport/reader/section.rs  ~130   Section, Push, Continuity, check_continuity, crc32, SECTION_SYNTAX, SECTION_CURRENT, CRC_TOP_BIT
    transport/reader/tables.rs   ~220   Program; impl TsReader { section_packet, append_section, section, pat_section, pmt_section,
                                   stream_descriptors }; read_length; vbi_data_lists_teletext
  transport/tests.rs         243   unchanged
pes.rs                      ~160   consts; State; PesParser; impl: new, begin, abort, feed, finish, report_skipped, note_skipped,
                                   end_of_packet, step, count_byte; PesReader; impl Reader; mod header; mod units; mod tests
  pes/header.rs             ~100   impl PesParser { hunt, header_byte, finish_header }; pts_microseconds
  pes/units.rs               ~65   impl PesParser { unit_byte, data_unit }
  pes/tests.rs              ~125   the inline module (369–488), pub(crate) data_unit, pes_packet kept
dump.rs                      117   unchanged
ep1.rs                       155   unchanged (apply_designation made private, its import from encode replaced by the core's)
  ep1/tests.rs                89   unchanged
edittf.rs                   ~140   LINE_BYTES and the shared consts (21–37); EditTfReader; impl Reader; mod base64; mod parse; mod write;
                                   pub use parse::parse; pub use write::write; mod tests
  edittf/base64.rs           ~70   base64_value, unpack_codes, pack_codes, hex_value, write_hex          [pub(super)]
  edittf/parse.rs           ~150   parse, field_value, fastext_field, enhancement_field
  edittf/write.rs            ~65   write
  edittf/tests.rs             96   unchanged but for one use line
log.rs                       159   unchanged
page.rs                     ~370   the capacity consts that are the page's own; PageFunction; PageFile; DEFAULT_ADDRESS; impl PageFile;
                                   PartialEq, Eq, Default; mod packets; mod links; mod interaction; mod form; mod issues; pub use …; tests inline (31)
  page/packets.rs            ~55   EnhancementPacket, RawBody, RawPacket, FastextLink; RAW_PACKETS, FASTEXT_LINKS
  page/links.rs             ~170   LINK_* consts, WEB_MARK, NUMBER_LINKS, TEXT_LINKS; LinkKey, LinkLine, LinkDestination, NumberLink, TextLink
  page/interaction.rs        ~40   CursorLine, INPUT_MODE_BITS, ModesLine
  page/form.rs              ~240   FORM_* and FIELD_* consts; FieldKind, FormField, FormOption, FormMethod, Form
  page/issues.rs            ~125   PAGE_ISSUES; IssueKind, Warning, PageIssue
tti.rs                      ~150   LINE_BYTES, PACKED_LINE, REGION_LAST, CODING_LAST, PAGE_COMMANDS; TtiReader; new; impl Reader;
                                   mod row_text; mod fields; mod targets; mod commands; mod packed; mod links; mod form; pub use …; mod tests
  tti/row_text.rs            ~75   DecodedText, decode_text
  tti/fields.rs             ~110   Args; parse_number, hex, decimal, flag, page_address, result_page, subcode, service_name   [pub(super)]
  tti/targets.rs             ~70   ADDRESS_MARK, ADDRESS_SCHEMES; link_address, link_destination, link_target                 [pub(super)]
  tti/commands.rs           ~230   impl TtiReader { diagnostic, issue, issue_at, end_line, command, page_command, log_line, page_number,
                                   description, output_line, emit }
  tti/packed.rs              ~80   impl TtiReader { packed_line }
  tti/links.rs              ~130   TEXT_LINK_LAST_ROW; impl TtiReader { fastext_line, link_line, number_link_line, text_link_line, cursor_line }
  tti/form.rs               ~230   impl TtiReader { set_text, field_definition, field_parameters, option_line, form_submission, finish_form }; mark_cells
  tti/tests.rs              ~330   fixtures (pub(crate)); mod links; mod forms; mod enhancement; mod interaction; the command and encoding tests
    tti/tests/links.rs      ~170   the Link Extension and address tests
    tti/tests/forms.rs      ~110   the Form Extension tests
    tti/tests/enhancement.rs ~130  the REQ-INP-023 tests
    tti/tests/interaction.rs ~170  TF, IM, CU and LG tests
check.rs                     253   unchanged
  check/tests.rs             122   unchanged
bdf.rs                      ~240   Font, FontError, FontErrorKind; the BDF line grammar split_keyword, numbers, integer, property_value, once,
                                   keep, misplaced_or_unknown, insert (private, seen by the children); pub mod convert; pub mod source;
                                   mod reader; pub use reader::read; mod tests
  bdf/reader.rs             ~310   consts (25–52); Section, Character, Header; read; Parser and its impl; check_properties
  bdf/tests.rs              ~210   the inline module (612–815)
  bdf/convert.rs            ~210   code (1–203); mod tests
    bdf/convert/tests.rs    ~230   the inline module (205–430)
  bdf/source.rs              406   unchanged but for its four use lines (now super::…, the same names)
detect.rs                   ~160   DETECTION_*; Format, is_compiled; Detection; AutoConfig; mod scoring; mod any; mod auto; pub use …; mod tests
  detect/scoring.rs         ~190   TS_SYNCS, BYTE_ORDER_MARK, ACCEPT_*; without_bom … detect_binary; pub(super) detect
  detect/any.rs             ~150   the gated reader imports; NotCompiledReader; AnyReader (per-variant cfg kept)
  detect/auto.rs            ~110   State; AutoReader; pass (two pages cfgs kept); decide; impl Reader
  detect/tests.rs            237   unchanged
encode.rs                    ~90   re-exports; GUILLEMET_FALLBACK, PROMPT_COLUMNS, LABEL_CHARACTERS, OTHER_SERVICE_LABEL_CHARACTERS,
                                   CHECKSUM_HEADER_BYTES, PAGE_TRIPLETS, TERMINATION, LinkTargets (private, seen by the children);
                                   mod link_row; mod checksum; mod triplets; mod rows; mod page; mod page_data; mod transmission; pub use …; mod tests
  encode/link_row.rs         ~90   LinkRow, key_colour, Prompt, draw_link_row, link_row                     [pub(crate) kept, re-exported]
  encode/checksum.rs         ~35   page_checksum, checksum_word
  encode/triplets.rs         ~75   raw_packet, packed_line_of, packed_character, pack_triplets, unpack_triplets
  encode/rows.rs            ~130   RowCoding, row_coding, is_enhancement_page, row_bytes, row_codes, packed_row, nibble_row
  encode/page.rs            ~180   transmitted_rows, fastext_links, triplets_with_marks, encode_page, emit_rows, emit_enhancements, emit_raw
  encode/page_data.rs        ~75   default_clut_2_and_3; page_enhancement_packet [pub(super)]; second_g0_value
  encode/transmission.rs     ~40   TransmissionClass, transmission_class
  encode/tests.rs            281   unchanged
links.rs                    ~135   code (1–131); #[cfg(all(test, feature = "tti"))] mod tests;
  links/tests.rs            ~145   the inline module (135–276)
write.rs                    ~100   PacketFilter; T42Writer; new, with_filter, into_inner, passes, write_packet; pub(super) sink();
                                   #[cfg(feature = "pages")] mod pages and its pub use; #[cfg(feature = "tti")] mod tti; #[cfg(feature = "bdf")] mod font; mod tests
  write/pages.rs             ~45   impl<W: Write> T42Writer<W> { write_pages, write_page }; in_transmission_order
  write/tti.rs              ~325   unchanged but write_page split in place into five named steps
  write/font.rs               93   unchanged
  write/tests.rs             178   unchanged
author.rs                    317   unchanged
  author/triplets.rs         393   unchanged
  author/display.rs          377   unchanged (PAGE_TRIPLETS becomes pub use crate::encode::PAGE_TRIPLETS, see 4.6)
  author/objects.rs         ~290   build_subpage split in place into definition_sequence, pointer_tables, place_triplets
  author/mot.rs              210   unchanged
  author/streams.rs         ~170   docs table; consts; magazine, page, text_body, filler_position, words, swatches; stream; display_pages;
                                   mod magazine_1; mod presentation; mod object_examples; mod links; mod default_objects; mod magazine_packets
    author/streams/magazine_1.rs       ~250   Objects, magazine_1, magazine_1_objects, magazine_1_table, index, colour_map, colour_map_level_35,
                                              screen_and_row_colours, side_panels
    author/streams/presentation.rs     ~200   sizes_and_attributes, flash, g3_and_g1, g2_and_diacritics, every_mode, sizes_written_by_enhancement_data
    author/streams/object_examples.rs  ~130   clause_13_9, annex_c2, local_objects, public_objects, global_objects
    author/streams/links.rs             ~85   links_over_the_table, level_35_links
    author/streams/default_objects.rs   ~60   default_object, default_objects
    author/streams/magazine_packets.rs  ~55   magazine_packets
  author/tests.rs           ~350   fixtures; the worked-encoding tests (53–345); mod round_trip
    author/tests/round_trip.rs ~160  read_tti, assert_same_pages, small_stream, authored_page, the four stream tests
testing.rs                    72   unchanged
robustness.rs                236   unchanged
tests/                              unchanged
```

**Public paths kept by re-export.** Every path in the table of 1.1 resolves as before: `tti.rs` re-exports `row_text::{DecodedText, decode_text}`; `page.rs` re-exports every record type from its children and keeps `pub(crate) DEFAULT_ADDRESS` itself; `encode.rs` re-exports every public function and `pub(crate) use link_row::{Prompt, draw_link_row, key_colour}` for `links.rs`; `detect.rs` re-exports `scoring::detect`, `any::{AnyReader, NotCompiledReader}`, `auto::AutoReader`; `transport.rs` keeps `pub use reader::TsReader` and gains `pub use reader::section::crc32` through `reader.rs`'s own `pub(super) use section::crc32`; `bdf.rs` re-exports `reader::read`; `write.rs` re-exports `pages::in_transmission_order` under `pages`; `sliced.rs` re-exports `reader::{record_packet, SlicedReader}` under `sliced`; `edittf.rs` re-exports `parse::parse` and `write::write`. The child modules are private, so no new public path appears.

**The shared bounded line reader (step 14).** `tti.rs:924–951` and `edittf.rs:366–389` are one mechanism: a fixed buffer of `N` bytes, a length, an overflow flag, the line number, the byte offset of the line's first byte, and the stream position; `feed` copies bytes until `\n`, marking overflow past `N`; `finish` ends a last line without `\n`. The extraction is `lines.rs`: `pub(crate) struct Lines<const N: usize>` with `const fn new()`, `fn feed(&mut self, bytes: &[u8], line: &mut dyn FnMut(Line<'_>))` and `fn finish(&mut self, line: &mut dyn FnMut(Line<'_>))`, where `Line` carries `text: &[u8]`, `number: u32`, `offset: u64`, `overflow: bool`. `TtiReader` replaces its six fields `line`, `len`, `overflow`, `line_number`, `line_offset`, `position` with one `lines: Lines<LINE_BYTES>` and `end_line` takes the `Line`; `EditTfReader` the same with its own `LINE_BYTES`. `dump.rs:55–74` and `ep1.rs:132–152` are the whole-input shape (`Whole<const N: usize>` with `feed` and `taken(&self) -> (&[u8], u64)`); the same file can hold it, or it is left as it is since each copy is twenty lines. The outputs are byte-identical: the same `Item`s at the same offsets and line numbers, which `same_in_any_chunks` (REQ-INP-001), `reports_long_rows_and_lines_with_offsets` and `reports_bad_data` already pin. `reader_sizes` prints the readers' sizes; they do not change (the same fields, grouped). This is the one commit of the plan that is not a pure move, and it is last and optional.

### 3.3 `neoteletext-slicer`

```
lib.rs           70   unchanged
consts.rs       164   unchanged
fsm.rs         ~315   code (1–312); #[cfg(test)] mod tests;
  fsm/tests.rs  ~65   the table test (314–375)
generator.rs   ~365   consts; LineBytes, line_bytes, packet_of; Echo, SignalParams; Generator; bit_of, raised_cosine, sync_and_burst;
                      quantise_*; mod rng; pub use rng::Rng; inline tests kept (58 lines; one holds a watched literal, see 4.11)
  generator/rng.rs ~65 Rng and its four constants (149–209)
math.rs         287   unchanged (59 inline test lines, at the limit; left)
raw.rs          331   unchanged
slicer.rs      ~310   consts (55–94); RateParameters, complex_multiply, renormalise; Candidate, Work; Slicer; new, config, set_config, counters,
                      black_level, reset_counters; check_address; compile-time asserts; mod line; mod config; mod outcome; mod machine;
                      mod black; mod run_in; mod framing; mod bits; pub use …; the ignored throughput test inline (53 lines; see 4.11)
  slicer/line.rs      ~60   SampleFormat, Line (REQ-SLC-001)
  slicer/config.rs    ~55   Config, Default
  slicer/outcome.rs   ~45   Counters, Rejection, Sliced
  slicer/machine.rs  ~105   impl Slicer { slice, slice_traced, perform }
  slicer/black.rs    ~140   impl Slicer { load, back_porch_black }; Histogram
  slicer/run_in.rs   ~170   impl Slicer { search, find_run_in, bit3_centre, measure, gate }
  slicer/framing.rs   ~65   FRAMING_OFFSETS, framing_offsets; impl Slicer { find_framing_code }
  slicer/bits.rs      ~55   impl Slicer { collect, bit, at, run_in_position }
tests.rs       ~170   #![allow]; fixtures (38–163) with their pub(crate) items; mod fsm_rows; mod signal; mod levels; mod framing;
                      mod rejection; mod raw; mod reports
  tests/fsm_rows.rs  ~230   row_01 … row_12, trace_of_an_accepted_line
  tests/signal.rs    ~125   clean_lines_decode_at_every_rate … search_window_limits_the_search
  tests/levels.rs    ~100   check_black, offset_black_levels, drifting_black_levels, black_level_of_a_row_of_solid_mosaics, amplitude_working_range
  tests/framing.rs    ~35   every_single_bit_framing_error, corrected_framing_needs_a_valid_address
  tests/rejection.rs ~135   biphase, non_teletext_lines_are_rejected, biphase_false_packets, noise_lines_give_no_packets, hostile_lines_do_not_panic
  tests/raw.rs       ~140   bt8x8_file, raw_bt8x8_file_in_odd_chunks, raw_reader_other_presets, raw_geometry_presets_and_validation
  tests/reports.rs   ~120   report_noise, report_impairments
```

The root's `pub use slicer::{Config, Counters, Line, Rejection, SampleFormat, Sliced, Slicer}` is unchanged because `slicer.rs` re-exports `line::{Line, SampleFormat}`, `config::Config`, `outcome::{Counters, Rejection, Sliced}`; `raw.rs`'s `use crate::slicer::{Config, Line, SampleFormat, Slicer}` resolves as before. The `impl Slicer` blocks in the children read `Slicer`'s and `Work`'s private fields as descendants of the module that defines them; no field becomes `pub(super)`. `RateParameters` stays in the spine for the same reason (it is read by `run_in.rs`, `black.rs` and `bits.rs`).

### 3.4 `neoteletext-image`

```
lib.rs          125   unchanged
convert.rs      214   unchanged
palette.rs      137   unchanged
png.rs         ~150   SIGNATURE, BIT_DEPTH, COLOUR_TYPE_INDEXED, FILTER_NONE, ZLIB_HEADER, ADLER_MODULUS; PngError; crc_table, CRC_TABLE,
                      crc_update, chunk; write, split in place into write_header and compress_rows; mod deflate; mod tests
  png/deflate.rs ~165  CHUNK_BYTES, MIN_MATCH, MAX_MATCH, MAX_DISTANCE; BitWriter; literal_code; LENGTH_BASE; DISTANCE_BASE;
                      LENGTH_SYMBOL_BASE, END_OF_BLOCK, DISTANCE_CODE_BITS; emit_match      [pub(super)]
  png/tests.rs   ~120  the inline module (350–466)
ppm.rs           81   unchanged
scale.rs        126   unchanged
tests/level25.rs 491  unchanged (under the ceiling)
```

`png::{PngError, write}` keep their paths; `deflate` is private.

## 4. The moves

Each step is one commit. Before the commit, every row of `cargo xtask features` for the crate builds (`neoteletext-formats`: `""`, `transport`, `sliced`, `pages`, `tti`, `ep1,edittf,dump`, `check`, `bdf`, `std`, `std,tti`; the slicer and image with and without their features) and `scripts/check.sh fast` passes. The diff is a move (`git diff --color-moved=dimmed-zebra`); the message names the step. No importer in another crate, a fuzz target, the firmware image, `xtask` or the browser changes in any step, because no public path changes; each step names the importers that exercise its paths so that they are compiled as part of the check. Each new test file begins with the `#![allow(...)]` header its source module carried (section 5).

**Step 1. Tests out of `tti`, `author`, `bdf`, `pes`, `t42`, `links`, `png`, `fsm`, and the slicer's `tests.rs` split.** Nothing but `#[cfg(test)]` code moves, so no feature build changes.
- `tti/tests.rs` 156–232, 606–695, 714–723 → `tti/tests/links.rs`; 255–351 → `tti/tests/forms.rs`; 477–604 → `tti/tests/enhancement.rs`; 697–712, 725–857 → `tti/tests/interaction.rs`; `tti/tests.rs` keeps 1–154, 235–253, 353–475, declares the four `mod`s. The fixtures stay `pub(crate)` (used by `check/tests.rs`, `write/tests.rs`, `detect/tests.rs`); the children reach them by `use super::*`. `packet_line` and `packets_of` (462–475) become `pub(super)` for `enhancement.rs`.
- `author/tests.rs` 347–501 → `author/tests/round_trip.rs`; `packets_of` (47–51) becomes `pub(super)`.
- `bdf.rs` 612–815 → `bdf/tests.rs`; `bdf/convert.rs` 205–430 → `bdf/convert/tests.rs`, its `super::super::FontErrorKind`, `super::super::source::read_source`, `super::super::read` rewritten as `crate::bdf::…` (noted in the message as the one test change). `pes.rs` 367–488 → `pes/tests.rs` (`pub(crate)` kept). `t42.rs` 202–316 → `t42/tests.rs`. `links.rs` 133–276 → `links/tests.rs`, declared `#[cfg(all(test, feature = "tti"))] mod tests;`. image `png.rs` 350–466 → `png/tests.rs`. slicer `fsm.rs` 314–375 → `fsm/tests.rs`.
- slicer `tests.rs`: 165–390 → `tests/fsm_rows.rs`; 392–513 → `tests/signal.rs`; 515–608 → `tests/levels.rs`; 610–638 → `tests/framing.rs`; 640–768 → `tests/rejection.rs`; 770–906 → `tests/raw.rs`; 908–1025 → `tests/reports.rs`; the fixtures (38–163) stay, private, read by the children; `RATES`, `samples_per_line`, `random_packet`, `render` stay `pub(crate)` for `slicer.rs`.
- **Two tests stay inline because `check-constants` and `check-io` strip a file at its first `#[cfg(test)]` marker and scan a `tests.rs` whole:** slicer `generator.rs:385–390` (`line_bytes_round_trip`, asserting `[0x55, 0x55, 0x27]`, the watched framing and run-in values) and slicer `slicer.rs:961–981` (`throughput`, calling `std::time::Instant::now()`, which `check-io` forbids). Both modules keep their inline `mod tests`.
- Gate: `cargo test` of each crate; `cargo xtask check-constants`, `check-io`.

**Step 2. `page/`.** `page.rs` 62–98 and 626–633 with `RAW_PACKETS`, `FASTEXT_LINKS` → `page/packets.rs`; 100–250 with `LINK_LABEL_BYTES`, `SERVICE_NAME_BYTES`, `LINK_LINES`, `LINK_ADDRESS_BYTES`, `WEB_MARK`, `NUMBER_LINKS`, `TEXT_LINKS` → `page/links.rs`; 252–284 → `page/interaction.rs`; 286–507 with `FORM_FIELDS`, `FORM_OPTIONS`, `FIELD_*`, `FORM_ADDRESS_BYTES`, `FORM_TOKEN_BYTES` → `page/form.rs`; 509–624 with `PAGE_ISSUES` → `page/issues.rs`. `page.rs` keeps `DESCRIPTION_BYTES`, `PageFile`, `DEFAULT_ADDRESS` (`pub(crate)`, unchanged), its impl, the equality impls and the 31-line inline tests; declares the five `mod`s and `pub use`s every type back. No visibility change: every record type is `pub` already. No cfg: `page` is always compiled. Importers exercised: app `convert`, `extras`; cli `keyboard` (the `INPUT_MODE_BITS` assert); fuzz `tti_enhancement`; the browser decoder at the re-pin.

**Step 3. `encode/`.** `encode.rs` 59–132 → `encode/link_row.rs` (`pub(crate)` items kept, re-exported from `encode.rs` with `pub(crate) use`); 134–163 → `encode/checksum.rs`; 165–231 → `encode/triplets.rs`; 233–358 → `encode/rows.rs`; 360–535 → `encode/page.rs`; 537–606 → `encode/page_data.rs` (`page_enhancement_packet` becomes `pub(super)`, the one seam); 608–643 → `encode/transmission.rs`. `encode.rs` keeps 35–57 (`PAGE_TRIPLETS`, `TERMINATION`, `LinkTargets` stay private there; the children and `encode/tests.rs` see them as descendants). `pages`-gated once in `lib.rs`; no cfg on the children. Importers exercised: app `convert`; fuzz `tti_enhancement`; `tests/corpus.rs`, `golden.rs`, `level25.rs`.

**Step 4. `bdf/reader.rs`.** `bdf.rs` 25–52, 144–487 and `check_properties` (560–574) → `bdf/reader.rs`; the grammar helpers 489–558 and 576–610 stay in `bdf.rs` beside the types, private, seen by `reader.rs` and `source.rs` as children; `source.rs:11, 222, 276, 310` change from `super::{…}` to the same names (unchanged paths, since the items stay in `bdf`). `bdf.rs` declares `mod reader; pub use reader::read;`. Build `bdf` alone and `bdf` with `std` (the converter's round-trip test). Importers exercised: cli `font`, `tests/font.rs`; fuzz `bdf`, `bdf_convert`.

**Step 5. `tti/`.** `tti.rs` 48–92 with `PACKED_LINE` → `tti/row_text.rs` (`PACKED_LINE` `pub(super)`); 94–192 with `REGION_LAST`, `CODING_LAST` → `tti/fields.rs` (`pub(super)`: `Args`, `parse_number`, `hex`, `decimal`, `flag`, `page_address`, `result_page`, `subcode`, `service_name`); 39–44, 194–239 → `tti/targets.rs` (`pub(super)`: `link_address`, `link_destination`, `link_target`); 294–508 and 899–904 → `tti/commands.rs`; 510–582 → `tti/packed.rs`; 45–46, 584–699 → `tti/links.rs`; 701–897 and 907–922 → `tti/form.rs`. `tti.rs` keeps `LINE_BYTES`, `PAGE_COMMANDS`, the struct, `Default`, `new` and `impl Reader`; the `impl TtiReader` blocks in the children read the struct's private fields as descendants. `diagnostic`, `issue`, `issue_at` (in `commands.rs`) and `set_text` (in `form.rs`) are called from sibling impl files and become `pub(super)`. Departure, with its reason: the seam of `fields.rs` is nine items, which the convention reads as a sign of a wrong split; they are the TTI argument grammar, one concept used by every record family, and the alternative (a parser per family) would duplicate them. Build `tti`, `check`, `std,tti`. Importers exercised: app `extras`; cli `commands`, `keyboard`; fuzz `tti_enhancement`, `channel_log`.

**Step 6. `edittf/`.** `edittf.rs` 39–97 and 241–246 → `edittf/base64.rs` (`pub(super)`: `base64_value`, `unpack_codes`, `pack_codes`, `hex_value`, `write_hex`); 99–239 → `edittf/parse.rs`; 248–309 → `edittf/write.rs`. The constants 21–37 stay in `edittf.rs`, seen by both children. `edittf/tests.rs:45` uses `super::base64::pack_codes`. Build `ep1,edittf,dump`.

**Step 7. `pes/`, then `transport/reader/`.** `pes.rs` 189–267 and 331–339 → `pes/header.rs`; 269–328 → `pes/units.rs`; the struct and its control methods stay in `pes.rs`, so the children read its fields as descendants. Then `transport/reader.rs` 29–34, 46–107, 118–155 → `transport/reader/section.rs` (`pub(super)`: `Section`, `Push`, `Continuity`, `check_continuity`, `SECTION_SYNTAX`, `SECTION_CURRENT`; `crc32` stays `pub` and `reader.rs` adds `pub(super) use section::crc32`, which `transport.rs`'s existing `pub use reader::{TsReader, crc32}` resolves); 109–116 and 427–634 → `transport/reader/tables.rs` (`Program` `pub(super)`; the `impl TsReader` block reads the struct's fields as a descendant of `reader`). Departure, with its reason: `transport/reader/` is a third level under `src/`, allowed where the second level is a large concept; the reader is 670 lines today and cannot be flattened into `transport/` because `transport.rs` must stay ungated for `item.rs` and the one gated `mod` of the convention is `reader`. Build `transport` and `""`. Importers exercised: app `input`; cli `options`; fuzz `formats`.

**Step 8. `sliced/reader.rs`.** `sliced.rs` 46–126 and 128–186 → `sliced/reader.rs`, the inline tests kept (57 lines) with their `#[cfg(test)] mod tests` and `#[allow]`; the ten per-item cfgs become `#[cfg(feature = "sliced")] mod reader;` and `#[cfg(feature = "sliced")] pub use reader::{record_packet, SlicedReader};`. Build `sliced` and `""`. Importers: cli `options`; fuzz `formats`.

**Step 9. `write/pages.rs`.** `write.rs` 86–110 and 113–121 → `write/pages.rs` as `impl<W: Write> T42Writer<W> { write_pages, write_page }` and `in_transmission_order`; `write.rs` gains `pub(super) fn sink(&mut self) -> &mut W` (`write_page` writes through `self.inner`; a sibling gets a method, not a field), `#[cfg(feature = "pages")] mod pages;` and `#[cfg(feature = "pages")] pub use pages::in_transmission_order;`. In the same commit, `write/tti.rs::write_page` (166–257) is cut in place into `write_page_head` (167–187), `write_rows_and_fields` (188–200), `write_packed_lines` (201–217), `write_links` (218–239) and `write_interaction_lines` (240–247), `write_page` calling them in order; the message says so. Build `std`, `std,tti`, `std` with `bdf`, default with `std`. Importers: app `convert`, `slice`; cli `font`; fuzz `tti_enhancement`, `bdf_convert`; the browser decoder.

**Step 10. `author/streams/`.** `streams.rs` 164–406 → `author/streams/magazine_1.rs`; 408–605 → `presentation.rs`; 607–730 → `object_examples.rs`; 732–779 and 834–863 → `links.rs`; 781–832 → `default_objects.rs`; 865–912 → `magazine_packets.rs`. `streams.rs` keeps 1–162 and declares the six `mod`s; the helpers (88–137) stay private and are read by the children as descendants. `magazine_1` (180–210) calls the page builders of `presentation.rs` and `object_examples.rs` by name, so the fourteen builders it calls become `pub(super)` (listed in the message); `links_over_the_table`, `default_objects`, `level_35_links`, `magazine_packets`, `magazine_1` become `pub(super)` for `stream()`. Departure, with its reason: a seam of fourteen names, which are the table of contents of magazine 1 as the module docs list it; the push order in `magazine_1` is kept to the line, because `Stream::in_transmission_order` is a stable sort and the authored TTI on disk depends on insertion order. In the same commit, `author/objects.rs::build_subpage` is cut in place into `definition_sequence` (188–216), `pointer_tables` (221–239) and `place_triplets` (249–275). Gate: `cargo xtask level25-stream` and the `golden_level25` test (`authored_tti_source_is_current` proves the stream byte-identical). Build `std,tti`. Importers: app `write_text`, `convert`; cli `tests/enhancement_reporting.rs`; `xtask/src/level25.rs`.

**Step 11. `detect/`.** `detect.rs` 45–53 and 109–284 → `detect/scoring.rs` (`detect` `pub(super)`, re-exported `pub use scoring::detect`); 302–443 with the gated imports it needs → `detect/any.rs` (the per-variant cfgs stay, the convention's one-item exception); 445–539 → `detect/auto.rs` (the two `pages` cfgs of `pass` stay). `detect.rs` keeps `DETECTION_*`, `Format`, `Detection`, `AutoConfig`. Last among the formats steps, after every reader's path is settled. Build every row of the matrix; build `firmware/test-image` with `formats` and `formats-all` on the remote host (`cargo xtask size`) and record the two sizes against those taken before step 1. Importers: app `convert`, `input`, `live`; cli `options`; fuzz `formats`; firmware `main.rs:193–194`; the browser decoder.

**Step 12. `slicer/` and `generator/rng.rs`.** `slicer.rs` 96–151 → `slicer/line.rs`; 153–205 → `slicer/config.rs`; 207–246 → `slicer/outcome.rs`; 410–507 → `slicer/machine.rs`; 513–576 and 849–920 → `slicer/black.rs`; 582–741 → `slicer/run_in.rs`; 74–94 and 747–778 → `slicer/framing.rs`; 784–831 → `slicer/bits.rs`; `slicer.rs` keeps the consts, `RateParameters`, `complex_multiply`, `renormalise`, `Candidate`, `Work`, `Slicer`, its accessors, `check_address`, the asserts and the inline throughput test, and re-exports `line::{Line, SampleFormat}`, `config::Config`, `outcome::{Counters, Rejection, Sliced}`. `Config::nominal_amplitude` (193–198) is read by `run_in.rs` and `black.rs` and becomes `pub(super)`. `generator.rs` 149–209 → `generator/rng.rs` with `pub use rng::Rng`. Build with and without `error-trait`; run `cargo test -p neoteletext-slicer --release -- --ignored throughput` once before and once after and report both numbers (REQ-GEN-013). Importers: app `slice`; fuzz `slicer`.

**Step 13. `png/deflate.rs` and traceability.** `png.rs` 28–33, 86–240 → `png/deflate.rs` (`pub(super)`: `BitWriter` and its methods, `literal_code`, `emit_match`, `LENGTH_BASE`, `DISTANCE_BASE`, which `png/tests.rs` reads); `write` is cut in place into `write_header` (254–278) and `compress_rows` (280–346). Build `""`, `std`, `error-trait`; run `tests/level25.rs` (golden unchanged). Importers: app `present`; cli `output/image`, `view`, `terminal`, `commands`; the browser decoder. Then `cargo xtask traceability` regenerates `docs/traceability.md` for every file path the steps moved; it is committed with this step so that the full gate's "running it changed a committed file" rule holds. `IMPLEMENTATION-LOG.md:64, 66, 87` cite module paths (`bdf::read`, `bdf::source::read_source`, `links`), which are unchanged.

**Step 14 (optional, not a move). `lines.rs`.** The extraction of section 3.2: `Lines<const N>` in `src/lines.rs`, `TtiReader` and `EditTfReader` holding one; the four `Whole` copies left or extracted alike. Its own commit after the moves, named as a behaviour-neutral extraction; `same_in_any_chunks`, `reports_long_rows_and_lines_with_offsets`, `reports_bad_data` and `reader_sizes` are the proof, and the fuzz targets `formats` and `tti_enhancement` are run for a few minutes against their corpora.

Files left over 400 lines after the work, each under the 500 ceiling: `consts.rs` (410, the constants module, sectioned by standard), `bdf/source.rs` (406, one parser), `image/tests/level25.rs` (491, fixtures and four tests), `tests/level25.rs` (364). None over 500.

## 5. Risks particular to these crates

| Risk | What meets it |
|---|---|
| **`item.rs` names `detect::Format`, `page::{IssueKind, PageFile}`, `transport::TeletextEntry` and `log::LogLine`** (`item.rs:7–9, 56`), so those four modules must stay compiled in the `""` build; moving `Format` into a gated child of `detect`, or `TeletextEntry` into `transport::reader`, breaks it | Steps 7 and 11 keep the types in the ungated parents and move only the readers; the `""` row of `cargo xtask features` is built at every formats step. |
| **`TECH-DEBT.md` records `cargo xtask features` already failing for `neoteletext-formats [std,tti]`** (issue 221; `tests/write_text.rs` of the cli is one named cause) | The row is run once on the unchanged tree before step 1 and its failure recorded in the log entry that announces the phase, so that a step is neither blamed for it nor hides it; the steps are judged by every other row and by `scripts/check.sh fast`. |
| **The no-panic `#![deny]` list is a crate-root attribute**, so no new module needs it; but every test file carries an `#![allow(clippy::unwrap_used, …)]` inner attribute that a new child test file does not inherit | Every new `tests.rs` and `tests/*.rs` of steps 1, 7, 12 and 13 begins with the header its source module carried; `--all-targets` Clippy in the gate catches an omission. |
| **`check-constants` and `check-io` strip at the first `#[cfg(test)]` marker and scan `tests.rs` files whole** | The two tests named under step 1 stay inline; no other test module of the three crates holds a watched literal (`0x27`, `0xE4`, `0x55`, `6937500`) or a forbidden `std` item, checked by `grep` at the reading. |
| **The size images `formats` (T42 and detection) and `formats-all` (every reader)** are the bare-metal measure of this crate (`cargo xtask size`, REQ-GEN-009/019) | Both are measured on the remote host before step 1 and after step 11 and the numbers put in the commit message; the plan adds and removes no entry point (the image calls `AutoReader::new/feed/finish` only), so the symbol check and the sizes are expected unchanged, and a difference is reported, not reasoned away. |
| **The browser's compile-time asserts** `const _: () = assert!(protocol::decoder::MAX_CHANNEL_LOG == neoteletext_formats::log::MAX_LOG_TEXT_BYTES)` (`decoder/src/lib.rs:36`) and the cli's `assert!(neoteletext_formats::page::INPUT_MODE_BITS == neoteletext_input::modes::ALL_MODES)` (`keyboard.rs:28`) | Both paths are kept (`log` unchanged; `INPUT_MODE_BITS` re-exported by `page.rs` from `page/interaction.rs`); the cli assert is compiled at step 2's gate, the browser's at the E5 re-pin. |
| **`write/tests.rs` is `cfg(all(test, feature = "tti"))` while `std` alone compiles `write.rs` without `tti` or `pages`** | Step 9 keeps `write.rs` building with `std` alone (`T42Writer` without the page methods) and builds that row. |
| **`author` needs `std` and `tti`; `links::tests` needs `tti` while `links` needs `pages`** | Step 1 keeps the `cfg(all(test, feature = "tti"))` on `links`'s `mod tests`; step 10 builds `std,tti`. |
| **Downstream feature sets differ from the matrix**: the browser's `decoder` asks for `std` only and relies on unification for `tti`/`pages`; `neoteletext-app` names eight features without `check`; `xtask` `std,tti`; fuzz `default,std` | None of these combinations is new; the re-pin (E5) runs the browser's `cargo check`, which is the one build the engine's matrix does not cover. |
| **`fuzz/` and `firmware/test-image/` are separate workspaces with their own lockfiles** | Path dependencies; no lockfile change; the fuzz targets are built in the full gate. |
| **The commit gate refuses untracked files** | Each step stages the whole move (`git mv` where possible) before `scripts/check.sh fast`. |

## 6. Seen, not part of this plan

- **Constants defined twice** (section 2.4): `PAGE_TRIPLETS`, `VERSIONS`, `NS_PER_SECOND`, `ROW_DIGITS`/`ROW_PAD_BITS`, `BOTH`, `LINE_US`, the `TERMINATION` triplet, and the two unrelated `LINE_BYTES`. Step 3 could make `encode::PAGE_TRIPLETS` public and `author/display.rs` re-export it, removing one; the rest need a decision on where each lives.
- **The near-duplicate BDF parsers** (`bdf.rs`, `bdf/source.rs`): one grammar, two state machines differing in the cells and keywords accepted. A single parser parameterised by profile would halve the code; it is a behaviour-bearing change and needs the `bdf` and `bdf_convert` fuzz targets re-run.
- **Four digit parsers with three bounds** (`tti.rs:123–144`, `edittf.rs:92–97`, `bdf/convert.rs:185–203`, `bdf.rs:511–528`); the `8` in `tti.rs:127` and `edittf.rs:93` is an unnamed limit.
- **Unnamed literals**: `png.rs:261` (`[0u8; 13]`, the IHDR length), `ppm.rs:38` (`[0u8; 20]`, the digits of `usize::MAX`) and `:46` (`3 * 64`, the row chunk), `convert.rs:91` (the 5-6-5 shifts), `pes.rs:337` (the PTS bit layout, commented but not named).
- **`parse` means three things**: `dump::parse` returns `bool`, `ep1::parse` returns `bool` and emits diagnostics, `edittf::parse` returns `Result<(), DiagnosticKind>`; `bdf::read`, `log::read`, `read_source`, `read_map` and `decode_text` name the same role differently.
- **Three sink conventions for writers**: `std::io::Write` (`write::*`), `&mut dyn FnMut(&[u8])` (`edittf::write`, the only writer in a reader module), and `image::Sink`.
- **Test helpers with no user**: `t42::tests::{sample_packets, serialise}` and `edittf::tests::written` are `pub(crate)`; `detect/tests.rs:21–50` re-implements the first two. `ep1::apply_designation` is `pub(crate)` with no user outside its file.
- **`encode/tests.rs:26–47`** tests `consts::EP1_LANGUAGES`, which belongs beside `ep1`'s tests.
- **Repeated test scaffolding**: `fnv` and `root` three times, `VecSink` three times (twice in one file), `encode_all`/`packets_of`/`encoded` four times, the decoder-feed loop four times; `tests/common/mod.rs` is the convention's home for the integration-test copies.
- **`ep1` imports `encode::DESIGNATION_GROUP_SHIFT`** for one constant the core defines; `edittf` does the same job through `PageFile::set_national_index`.
- **`golden_level25.rs` and `level25.rs`** carry `#![cfg(feature = "std")]` on top of `required-features = ["std", "tti"]`; one of the two is enough.
- **`TECH-DEBT.md` owes** fuzzing of `bdf`/`bdf_convert` with 12 by 20 inputs and a `cargo xtask size` remeasurement; neither is absorbed by this plan, but step 11's measurement gives the size.
