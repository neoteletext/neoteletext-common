# `neoteletext-core`: findings and the target layout

| | |
|---|---|
| **Rests on** | A full reading of the 48 `.rs` files of `crates/neoteletext-core` (28,900 lines) at engine `fb2dd8a`, the crate's `Cargo.toml`, `xtask/src/{checks,features,size,trace,glyphs}.rs`, `scripts/{check.sh,arabic-sets.py}`, `ARCHITECTURE.md` section 9, REQ-ARCH-011, REQ-GEN-006/009/014/016/019/020 and `DEVELOPMENT.md` section 6, and a `grep` of every `neoteletext_core::` path in the browser, the other engine crates, the fuzz targets, the firmware test image and `xtask`. Line numbers are those of the files at that commit. |
| **Measure** | [`00-conventions.md`](00-conventions.md). Phase E1 of [`01-method-and-order.md`](01-method-and-order.md). |
| **What it keeps** | Every public path (`neoteletext_core::<module>::<item>`), the sixteen features and their meaning, the `#![deny(...)]` list in `lib.rs` as the only root, the `xtask` layer table (keyed on the first path component under `src/`), `ARCHITECTURE.md` section 9 and REQ-ARCH-011, the generated `glyphs/bedstead.rs` and `glyphs/g3.rs`, and every behaviour. |

## 1. The crate as it is

### 1.1 Purpose

The `no_std`, no-allocation teletext core of EN 300 706 at Levels 1.0, 1.5, 2.5 and 3.5: error-protection codes, packet decoding, acquisition and the page store, service data, character sets, the Level 1 row machine, the Level 1.5 overwrite walk, the Colour Map, objects and the enhancement processor, the Arabic-script joining pass, glyph data and the row renderer, the viewer, navigation and the form model, the port traits, and the cross-cutting policy, configuration and trace modules. It depends on nothing (`[dependencies]` is empty, REQ-GEN-017, decision E.38); `proptest` is a dev-dependency no test uses.

### 1.2 The sixteen features

| Feature | Implies | What it gates today (file:line) |
|---|---|---|
| `extended-sets` | | `mod joining` (`lib.rs:62`); the `EXTENDED_TABLE_32` and `EXTENDED_SECOND` tables with their empty twins (`charset/tables.rs:114-168`); the joined-form check inside `conformance` (`glyphs/conformance.rs:245-258`); the joining call in `compose.rs:43,77`; tests in `level1.rs:1425`, `charset/mod.rs:548`, `charset/tables.rs:1971`. The own G0 and G2 tables are compiled in every build; only their Table 32 designations are reserved without the feature. |
| `level15` | | `mod level15` (`lib.rs:56`); the Level 1.5 arm of `compose.rs:29,64`; `PresentationLevel::available` (`config.rs:47`). |
| `level25` | | `mod enhance` (`lib.rs:53`); the Levels 2.5 and 3.5 arm of `compose.rs:34,69`; `config.rs:46`; `EnhancementReport::new` (`acq.rs:487-492`). `objects`, `colour` and `acq::enhancement` are compiled in every build. |
| `nonspacing-attributes` | `level25` | the constant `ATTRIBUTES` (`enhance.rs:112`) guarding four match arms of `column_triplet` (`enhance.rs:1090-1107`). |
| `objects` | `level25` | `enhance.rs:887` (no default objects) and `enhance.rs:1005` (an invocation is ignored). |
| `side-panels` | `level25` | `colour.rs:297` (no panel widths), `render.rs:595` (`panel_widths` is 0, 0); tests. |
| `level25-32colors` | `level25` | `colour.rs:254` (CLUTs 2 and 3 copied from 0 and 1), `colour.rs:271` (X/28/0 and M/29/0 never redefine). |
| `level35-32colors` | `level25-32colors` | `colour.rs:277` (X/28/4 and M/29/4 never redefine CLUTs 0 and 1). |
| `additional-flash-functions` | `nonspacing-attributes` | `flash_of` returns `None` (`enhance.rs:206`); tests. |
| `classic` | `level15`, `render`, `bedstead`, `viewer` | a profile; no code. |
| `modern-classic` | `level15`, `level25`, `nonspacing-attributes`, `render`, `bedstead`, `viewer`, `forms`, `objects` | a profile; no code. REQ-GEN-020's text says `original` where the manifest says `bedstead`. |
| `render` | | `mod glyphs`, `mod render` (`lib.rs:60,64`); `error_trait!` for `RenderError`. |
| `bedstead` | `render` | `mod bedstead` and `GlyphSet::bedstead()` (`glyphs/mod.rs:25,218`); the render test modules (`render.rs:1128-1134`, `glyphs/mod.rs:406`). |
| `viewer` | | `mod nav`, `mod viewer` (`lib.rs:69-72`). |
| `forms` | | `mod forms` (`lib.rs:67`); `error_trait!` for `FormError`. |
| `error-trait` | | `lib.rs:84-115`: `Display` and `core::error::Error` for the three error enums. |
| `debug-fmt` | | declared; nothing tests it. |

Default (decision E.105, pinned by `tests/capabilities.rs:28`): `level15, level25, nonspacing-attributes, level25-32colors, level35-32colors, render, bedstead, viewer, forms, extended-sets`. The gate (`xtask/src/features.rs`) lints and tests the core with `--no-default-features` and each of: `""`, `level15`, `level25`, `level15,level25`, `modern-classic`, `default`, `level15,level25,level25-32colors`, `classic`, `render`, `bedstead`, `viewer`, `forms`. `cargo xtask size` links `firmware/test-image` for `level1`, `level15` (budgeted at 64 KiB), `level35`, `modern-classic` and `core-all` on `thumbv6m-none-eabi` and fails on any floating-point, compare-and-swap or panic symbol.

### 1.3 The module tree with line counts

```
src/
  lib.rs                      115   root: deny list, mod tree, error_trait!
  consts.rs                  1026   Foundation: every constant (REQ-GEN-014)
  ecc.rs                      451   Foundation: parity, Hamming 8/4 and 24/18, bit reversal, checksum
  types.rs                    471   Foundation: addresses, X/28 field groups, FontGlyph, Instant, FixedVec
  packet.rs                  1365   L1: Packet, Decoded, decode(), header/row/X/26/X/27/0/8-30 decoders, encode, tests
  packet/function.rs          651   L1: TripletFunction (Tables 28, 29) and its field types
  packet/links.rs              84   L1: CompositionalLink (Table 15)
  packet/objects.rs           369   L1: object-page packets, Magazine Organization Table (+encode)
  packet/page_data.rs         223   L1: X/28 and M/29 field groups (+encode)
  acq.rs                     1849   L2: StoredPage, PageStore, events, statistics, Decoder, tests
  acq/enhancement.rs          464   L2: the enhancement-page store and its lookup
  fsm.rs                      579   L2: magazine and page lifecycle machines, tests
  service.rs                  195   L2: 8/30 interpretation
  charset/mod.rs              658   L3: set enums, CharRef, designation and Unicode facade, tests
  charset/tables.rs          2414   L3: Tables 32-48, own sets, Arabic shaping, Thai/Lao, marks, compositions, mosaics, tests
  colour.rs                   514   L3: ColourMap, Remapping, SidePanels, resolve(), tests
  compose.rs                   80   L3: compose_level(_traced)
  level1.rs                  1467   L3: Cell/Grid, DisplayOptions, designation resolution, Table 26 machine, build_grid, tests
  level15.rs                  519   L3: Level 1.5 walk (REQ-FSM-007), tests
  objects.rs                  643   L3: object links, bodies, definitions, prescan, tests
  enhance.rs                 2303   L3: the enhancement processor, tests
  joining.rs                  129   L3: Arabic-script joining, tests
  glyphs/mod.rs               487   L4: GlyphSet, LoadedFont, SPACING_MARKS, tests
  glyphs/bedstead.rs         2076   L4: generated Bedstead table (2066 glyphs)
  glyphs/g3.rs                394   L4: generated G3 table (96 glyphs)
  glyphs/conformance.rs       420   L4: FONT_SETS, conformance rules, tests
  render.rs                  1278   L4: flash, options, colours, cell raster, row renderer, palette, change tracking, tests
  render/level25_tests.rs     840   L4 tests
  render/font_tests.rs        345   L4 tests
  viewer.rs                   665   L6: Viewer, keys, status, compose, tests
  nav.rs                      328   L6: links, page stepping, entry, history, tests
  forms.rs                   1570   L6: form spec, editing, validation, pairs, drawing, tests
  port.rs                      45   L8: the port traits
  config.rs                   303   cross-cutting: PresentationLevel, Config, profiles, tests
  policy.rs                   172   cross-cutting: security decisions, tests
  trace.rs                     64   cross-cutting: TraceEntry, TraceSink
tests/
  common/mod.rs 561 · objects.rs 757 · level25.rs 429 · level25_attributes.rs 299 · reporting.rs 294
  behaviour.rs 269 · performance.rs 223 · flash_cost.rs 146 · capabilities.rs 145 · corpus.rs 70 · coverage.rs 64
examples/minimal_port.rs 87
```

Beside the code: `glyphs/g3.txt`, `required.txt`, `forms.txt` (written by `cargo xtask glyphs`); `charset/tables.rs:798-1196` is rewritten by `scripts/arabic-sets.py` between `BEGIN`/`END` marker lines.

### 1.4 The public paths and who imports them

Every importer names a top-level module path, so the layout below, which keeps every item re-exported from its module, breaks none of them.

| Importer | Paths |
|---|---|
| The browser (`native/`, 26 distinct paths) | `acq::{Decoder, EnhancementPacket, EnhancementStore, EnhancementSubPage, Event, StoredPage}`; `charset::{CharRef, CharSet, G2Set, to_unicode}`; `compose::compose_level`; `config::Config`; `consts::{COLUMNS, ROWS, DATA_BYTES, PACKET_BYTES, FLASH_CYCLE_US, FLASH_UNITS, G2_RIGHT_GUILLEMET, ENHANCEMENT_PACKETS_LEVEL_35, MAGAZINES, MOT_PACKETS, PAGE_COMPLETION_TIMEOUT_US}`; `ecc::{hamming84, hamming84_encode, with_odd_parity}`; `fsm::PageState`; `glyphs::GlyphSet`; `level1::{Cell, Glyph, Grid, Size, DisplayOptions, FlashRate, build_grid}`; `nav::{PageLinks, LinkTarget}`; `packet::{Packet, PacketMeta, Decoded, PageFormat, DisplayAttributes, decode, decode_address, encode}`; `policy::{ipv4_blocked, ipv6_blocked}`; `render::{ChangeTracker, FlashPhase, IndexBuffer, IndexFormat, RenderOptions, render_screen}`; `types::{ControlBits, DefaultColourFields, Designations, PageAddress, PresentationFields, Rgb12, SubCode, Instant}`; `viewer::MAX_LISTED_SUBPAGES` (asserted equal to `interface_core::controls::MAX_SUBPAGES`) |
| `neoteletext-formats` | `consts` (57 sites), `packet` (46: `Packet`, `PacketMeta`, `Triplet`, `decode_address`, `decode`, `encode::*`, `ColourData`, `CompositionalLink`, `ObjectKind`, `ObjectPacket`, `PageEnhancement`, `PageFormat`), `types` (35), `ecc` (16), `acq`, `config`, `charset`, `render`, `nav`, `level1`, `glyphs`, `level15`, `fsm`, `compose`, `colour` |
| `neoteletext-slicer`, `-web`, `-image`, `-audio`, `-input` | `consts`, `packet`, `types`, `ecc`, `trace`; web adds `policy`, `service`; image adds `colour::{colour_index, ColourMap, SidePanels}`, `render`, `level1`, `glyphs`, `config`, `charset` |
| `neoteletext-app`, `neoteletext-cli` | `consts`, `types`, `config`, `packet`, `level1`, `fsm::{PageState, PageKey}`, `charset`, `acq`, `policy`, `forms::FormModel`, `ecc`, `trace`, `service::{interpret, initial_page}`, `render`, `nav`, `glyphs::{GlyphSet, LoadedFont, conformance::*}`, `compose::{compose_level, compose_level_traced}`, `viewer::{Viewer, Key}`, `colour`, `objects::links`, `enhance::MAX_WALK_STEPS` |
| Fuzz targets (`fuzz/fuzz_targets/*.rs`) | `acq::{Decoder, EnhancementPacket, EnhancementStore, EnhancementSubPage, StoredPage}`, `compose::compose_level`, `config::{CellMode, Config, PresentationLevel}`, `consts::{…}`, `ecc::hamming84_encode`, `enhance::MAX_WALK_STEPS`, `fsm::PageState`, `glyphs::GlyphSet`, `level1::{DisplayOptions, Grid, build_grid}`, `level15`, `packet::{Packet, PacketMeta, Triplet, encode, decode}`, `render::{ALL_ROWS, ColourMode, FlashPhase, IndexBuffer, IndexFormat, RenderOptions, render_screen, row_width}`, `types::{ControlBits, Instant, Magazine, PageAddress, PageNumber, SubCode, FontGlyph}` |
| `firmware/test-image` | `acq::{Decoder, StoredPage, EnhancementPacket, EnhancementReport, EnhancementStore, EnhancementSubPage}`, `charset::G0`, `compose::compose_level`, `config::Config`, `forms::{FormKey, FormModel, FormSpec}`, `glyphs::GlyphSet`, `level1::{DisplayOptions, Grid, build_grid}`, `packet::{Packet, PacketMeta, ServicePacket}`, `render::{Field, IndexBuffer, RenderOptions, render_row}`, `service`, `types::{Instant, PageAddress, SubCode}`, `viewer::{ComposeContext, Key, KeyContext, Viewer, ViewerEvent}` |
| `xtask` | by API: `charset::{…}`, `glyphs::SPACING_MARKS`; by path: `src/glyphs/{bedstead.rs, g3.rs, g3.txt, required.txt, forms.txt}` (`xtask/src/glyphs.rs:30-35`), `DATA_FILES = ["charset/tables.rs", "glyphs/bedstead.rs", "consts.rs"]` (`xtask/src/checks.rs:212`), `crates/neoteletext-core/src` for the layer check (`checks.rs:73`) |
| Scripts and documents citing paths | `scripts/arabic-sets.py:6,23,35`; `docs/traceability.md` (244 core paths, regenerated by `cargo xtask trace`); `docs/spec/design/hmi.md:18-21,48` (`viewer.rs:20`, `forms.rs:250`, `forms.rs:34`, `port.rs`); `docs/spec/design/languages.md:172` (`glyphs/mod.rs:140`); `ARCHITECTURE.md:372` (`tables.rs`); `IMPLEMENTATION-LOG.md:17`, `TECH-DEBT.md:85,97`, `third_party/bedstead/PROVENANCE.md:14`; `docs/teletext-specification-audit.md:27-31,66` (untracked, not the project's); the browser's `docs/hyperlinks.md:67` (`level1.rs`) |

### 1.5 Where EN 300 706 lives today

| Clause or table | Module and lines |
|---|---|
| 5, 6, 7.1 signal, framing, packet form | `consts.rs:10-63`; `packet::Packet` |
| 7.1.2, Table 1 packet numbers and magazines | `consts.rs:65-98`, `types::Magazine/PageNumber`, `packet::decode_address` |
| 8.1, 8.2, 8.3 parity and Hamming codes | `ecc.rs`; `consts.rs:205-226` |
| 9.3.1 page header, C4-C14 | `packet.rs:126-155,409-458`; `consts.rs:174-203`; `types::ControlBits` |
| 9.4.1 X/26, 12.3.1 triplets (Tables 27-29) | `packet.rs:168-217,460-488`; `packet/function.rs`; `consts.rs:228-385` |
| 9.4.2-9.5 X/28, M/29 (Tables 3, 4, 9-13) | `packet/page_data.rs`; `packet.rs:361-387`; `acq::MagazineData`; `consts.rs:387-463` |
| 9.6.1 X/27/0 editorial links, checksum | `packet.rs:219-243,503-549`; `ecc::PageChecksum`; `nav::PageLinks` |
| 9.6.2 X/27/4,5 compositional links (Tables 15, 16) | `packet/links.rs`; roles in `objects.rs:103-154` |
| 9.8.1 8/30 broadcast service data | `packet.rs:267-284,551-587`; `service.rs`; `consts.rs:866-879` |
| 10.5.1 object pages (Figure 19) | `packet/objects.rs:25-113`; `objects.rs:439-478`; `consts.rs:487-522` |
| 10.6 Magazine Organization Table (Figure 20, Tables 20-23) | `packet/objects.rs:115-369`; `objects.rs:156-236`; `acq.rs:958-970`; `consts.rs:524-586` |
| 12.2 spacing attributes (Table 26) | `level1.rs:724-819`; again `enhance.rs:1417-1468,1659-1674`; `consts.rs:608-669` |
| 12.3.2-12.3.4 the active position | `level15.rs:55-112`; `enhance.rs:675-753,1081-1149`; `objects::row_of` |
| 12.4 Colour Map (Table 30) | `colour.rs`; `consts.rs:687-753` |
| 12.5 side panels | `colour.rs:132-181`; `enhance.rs:360-389,1851-1863`; `render.rs:592-631,798-822`; `consts.rs:755-768` |
| 13 objects, 13.2 display planes, Annex A.8 limits | `enhance.rs`; `objects.rs`; `consts.rs:896-946` |
| 15 character sets (Tables 32-48) | `charset/tables.rs`; resolution in `level1.rs:503-638` |
| Annex A.7.1, C.1, C.2, C.3, C.4 | `enhance.rs:117-198`; `render.rs:475-528`; `enhance.rs:187-198,1470-1486`; `enhance.rs:1717-1764`; `level1.rs:558-625` |
| Annex B.3, B.9 acquisition; Annex D.3 initial page; Annex H Fastext | `fsm.rs`, `acq.rs`; `service::initial_page`; `nav.rs:30-46`, `level1::row_24_shown` |
| EN 300 708 independent data lines | `consts.rs:100-129` |
| Appendix C of the specification (forms) | `forms.rs` |

## 2. Findings

### 2.1 File by file

| File | What it holds (line ranges) | Mixes |
|---|---|---|
| `lib.rs` 115 | deny list 26-35; `mod` tree 40-78; `error_trait!` 84-115 | one concept |
| `consts.rs` 1026 | signal 10-63; packet numbers 65-98; audio 100-129; pages and control bits 131-203; coding 205-226; triplets 228-385; X/28, M/29, X/27/4 387-485; object pages 487-522; MOT 524-586; designations 589-606; Table 26 608-669; mosaics 671-685; colours 687-706; Colour Map 708-753 (tables `COLOUR_MAP_DEFAULTS`, `REMAPPING_CLUTS`); side panels 755-768; geometry 770-828; timing 830-864; service 866-879; "Phase I2b" 881-894; "Phase I2a" 896-980; tests 982-1026 | one clause per banner, but 881-980 are grouped by implementation phase and scatter flash (350-355, 845-864, 948-968), objects (487-522, 908-933), link functions (464-485, 934-946), G3 (886-889, 970-972) and side panels (755-768, 900-902) over two places each |
| `ecc.rs` 451 | `Status` 9-26; parity 28-46; Hamming 8/4 48-131 (table built at compile time, narrow `#[allow]` at 105); Hamming 24/18 133-220; `reverse_bits` 222-227; `PageChecksum` 229-267; tests 269-451 | four sub-clauses, each self-contained; 268 lines of code |
| `types.rs` 471 | `Magazine` 8-43; `PageNumber` 45-74; `PageAddress` 76-108; `hex_digit`; `SubCode` 117-142; `ControlBits` 144-163; `Rgb12` 165-204; `ColourWords`, `Designations`, `SidePanelFields`, `DefaultColourFields`, `PresentationFields`, `FallbackFields` 206-277; `FontGlyph` 279-317; `Instant` 319-330; `FixedVec` 332-426; tests 428-471 | addressing, the Table 4/10/21 field groups, the loaded-font glyph, a collection |
| `packet.rs` 1365 | `Packet` 45-68; `PacketMeta`, `SliceQuality` 70-97; `PacketError`, `PacketAddress`, `decode_address` 99-124; `Header` 126-155; `Row` 157-166; `Triplet`, `Triplets`, `Enhancement` 168-217; `Link`, `Links` 219-243; `PagePacket`, `MagazinePacket` 245-265; `ServicePacket` 267-284; `Decoded` 286-337; `decode` 339-396; `designation_code`, `nibble` 398-407; header indices and `decode_header` 409-458; triplet helpers 460-488; `compositional_links` 490-501; `page_reference` 503-519; link indices and `decode_links` 521-549; service indices, `copy_bytes`, `decode_service` 551-587; `pub mod encode` 589-830; tests 832-1365 | six packet kinds (9.3.1, 9.4.1, 9.6.1, 9.6.2, 9.4.2/9.5, 9.8.1), every encoder, the boundary type |
| `packet/function.rs` 651 | `ColourData` 25-52; `ObjectSource` 54-86; `ObjectKind` 88-120; `ObjectNumber` 122-198; `ObjectUsage` 200-217; `DisplayAttributes` 219-263; `TripletFunction` 265-454; `Triplet::function`, `row_function`, `column_function` 456-525; `to_triplet` 527-580; `name`, `active_column` 582-645; `object_address` 647-651 | the Table 28 field types and the function enumeration with its two-way mapping; tested from `packet.rs` |
| `packet/links.rs` 84 | `CompositionalLink` with `from_values`/`to_values` | one concept |
| `packet/objects.rs` 369 | `ObjectPacket`, `TripletLocation`, `triplet_location` 21-113; `MotPosition` … `mot_totals` 115-302; `pub(super) mod encode` 304-369 | clause 10.5.1 and clause 10.6 |
| `packet/page_data.rs` 223 | `TripletValues`, `stream_bits` 23-47; `PageFormat` 49-73; `PageEnhancement` 75-86; `presentation_fields`, `colour_words`, `page_enhancement`, `page_function` 88-150; `encode::presentation_values` 152-208; `set_stream_bits` 210-223 | one concept |
| `acq.rs` 1849 | `StoredPage` 41-204 (`erase`, `merge` private); `PageStore` 206-316; `MagazineData` 318-326; `Discard`, `Event` 328-379; `Statistics` 381-410; `EnhancementFaults` 412-462; `EnhancementReport` 464-492 (`pub(crate) new` under `cfg(level25)`); `PageBuild` 494-514; `SearchStatus` 516-525; `Decoder` 527-559; `Route`, constants 561-579; `impl Decoder` 581-1304 (`push` 747-830, `enhancement_data` 834-894, enhancement-page routing 896-986, `tick` 991-1007, FSM driving 1018-1303); tests 1306-1849 | the stored page (E.8), the cache store, events and statistics, FSM driving (Annex B.3), the rolling header (E.11), enhancement-page routing (E.56) |
| `acq/enhancement.rs` 464 | constants 23-33; `EnhancementKey` 35-53; `EnhancementPacket` 55-66; `EnhancementSubPage` 68-95; `row_index`, `enhancement_index` 97-112; `EnhancementPage` 114-194; `Stored` 196-206 (`pub(super)`); `EnhancementStore` 208-422; `lookup`; `EnhancementLookup` 432-464 | the store and the lookup; tested from `acq.rs:1613-1750` |
| `fsm.rs` 579 | `PageKey` 10-17; magazine machine 19-180; page machine 182-302; tests 304-579 | two machines of one area; 303 lines of code |
| `service.rs` 195 | `DateTime`, `ServiceInfo` 9-45; `interpret` 47-69; `initial_page` 71-77; offset and digits 79-109; `date_time`, `civil_from_mjd` 111-163; tests 165-195 | one concept plus a calendar |
| `charset/mod.rs` 658 | `G0Set` 13-98; `JoiningType`, `JoinForm`, joining API 100-162; `G2Set` 164-187; `NationalOption` 189-254; `G0`, `CharSet`, `CharRef`, `Designation`, `Unicode` 256-318; designation lookups 320-372; Unicode conversion 374-402; mosaics 404-423; `compose`, `latin_text` 425-439; tests 441-658 | vocabulary, designation resolution, the Unicode facade; the joining API sits between the set enums |
| `charset/tables.rs` 2414 | header 12-39; Tables 32-34 41-245 (`cfg` twins 114-168); Latin and national options 247-355; standard G0 sets 357-467; own G0 sets 469-590; `g0_unicode` 592-630; G2 sets 632-741; G3 743-787; Arabic-script sets and shaping 789-1211 (generated block 798-1196); Thai and Lao 1213-1342; marks 1344-1373; mosaics 1375-1420; compositions 1422-1819; tests 1821-2414 | nine spec tables and decisions and one generated block; 1,800 lines of data |
| `colour.rs` 514 | `ColourIndex`, `colour_index` 21-27; `ColourMap` 30-94; `Remapping` 96-130; `SidePanels` 132-181; `PresentationSources`, `PagePresentation` 183-237; `resolve` 239-303 (four `cfg!` tests inside); `colour_words` 305-315; tests 317-514 | the Colour Map, the re-mapping, side panels (clause 12.5, not a colour), decision E.44 precedence |
| `compose.rs` 80 | `compose_level` 18-46; `compose_level_traced` 52-80 | one concept; the two functions differ only by the trace argument |
| `level1.rs` 1467 | `Glyph`, `Size`, `Width`, `FlashMode`, `FlashRate`, `CharSource`, `CellAttributes`, `Cell` 31-329; `Grid`, `DEFAULT_DESIGNATION`, `Zoom`, `DisplayOptions` 331-501; `DesignationSource`, `NationalSource`, `DesignationReport`, `designation_report`, `resolve_designation` 503-638; `RowState`, `RowContext`, `decode_row`, `set_at`, `cell_glyph`, `set_after` 640-819; `stored_row`, `build_grid`, receiver columns, `row_codes`, `row_24_shown`, `hide_header`, `fill_lower_row` 821-1015; tests 1017-1467 | the cell and grid model (E.42), Annex C.4 designations, the Table 26 row machine (REQ-FSM-006), page assembly (E.10, E.15, E.23) |
| `level15.rs` 519 | `WalkState`, `WalkAction`, `WalkContext` 18-51; `walk_transition` 53-112; names 114-145; `character` 147-165; `apply`, `apply_traced`, `walk`, `write` 167-282; tests 284-519 | one concept; 283 lines of code |
| `objects.rs` 643 | `PageLink`, `DefaultInvocation`, `EnhancementLinks` 42-101; roles and the table 103-259; `Body`, `Fetch` 261-346; `ObjectRef`, `Absent`, definitions, `find_local`, `find_public`, `row_of`, `prescan` 348-548; tests 550-643 | link resolution (REQ-OBJ-030..040), the triplet source, definition lookup (REQ-OBJ-003..006); compiled in every build though only `enhance` uses it |
| `enhance.rs` 2303 | bounds 61-72; attributes 74-242; characters 244-295; planes and areas 297-389; `Frame` 391-443; `Range`, `Slot`, `Collector` 445-547; `Inputs` 549-559; machine types 561-671; transitions 673-753; names and `traced_action` 755-835; `Walker` and impl 837-1302; `is_display`, `has_display_triplets` 1304-1331; `RowContext`, `RowState` 1333-1487; `Overlay`, `Resolved`, `cell_of` 1489-1536; `Segment`, `resolve_segment` 1538-1654; `level_1_glyph` 1656-1674; `RowCells` 1676-1765; `is_enhancement_page` 1767-1784; `Rows` 1786-1866; `apply`, `apply_traced`, `process`, `rebuild_rows` 1868-2058; tests 2060-2303 | Table 27 and 29 attributes (E.47, E.48), REQ-L25-010 characters, clause 13.2 planes, 12.5.3 areas, REQ-FSM-011, the walk's run-time with Annex A.8, REQ-FSM-012 with a second Table 26 machine, Annex C.3, REQ-OBJ-041 |
| `joining.rs` 129 | `letter`, `form`, `join_row`, `join`; tests 65-129 | one concept |
| `glyphs/mod.rs` 487 | `G3Glyph`, `CharClass`, `class` 40-72; `GlyphEntry`, `GlyphSet` 74-96; `FontTableError`, `LoadedFont`, `LoadedGlyph` 98-141; `impl LoadedFont` 143-211; `PLACEHOLDER`; `GlyphSet` construction and impl 217-375 (`glyph` is `#[inline(always)]`); `SPACING_MARKS` 377-403; tests 405-487 | the bundled set, and the run-time font with its shape checks (REQ-FNT-002/003/008) |
| `glyphs/bedstead.rs` 2076, `glyphs/g3.rs` 394 | generated tables | left as they are |
| `glyphs/conformance.rs` 420 | `FONT_SETS` 35-92 (56 rows); `font_set_of` 103-165 (a hand-kept mirror of the table); `assigned`, `Failure`, `SetConformance`, `conformance` (cfg block 245-258), `conformance_masks` 167-278; tests 280-420 | one concept plus the set registry |
| `render.rs` 1278 | `CellLine`, `Field` 38-67; `FlashPhase`, `flash_unit`, `flash_on` 69-156; `ColourMode`, `RenderOptions` 158-236; palette indices 238-271; raster helpers 273-466 (with `#[cold]`, `#[inline(never)]`, measured notes); `flash_shown`, `plane`, `resolved_colours` 468-528; `cell_line` 530-580 (`#[inline(always)]`); `palette_cell_allowed`, panel widths, `source_columns`, `row_columns`, `row_width`, `border_index`, mode checks, `source_cell` 582-662; `RenderError`, `IndexFormat`, `IndexBuffer` 664-699; `fill_cell`, `write_cell`, `write_line`, `write_panel`, `check_mode`, `render_row`, `render_line` 701-901; `fill_palette`, `palette_colour`, `flash_visible` 903-949; `ChangeTracker` 951-1095; `render_screen`, `ALL_ROWS`, `FIELD_LINES` 1097-1125; test declarations and tests 1127-1278 | E.12 and E.48 flash, options, REQ-RND-023 palette mode, REQ-RND-031/036 resolved mode with Annex C.1, the raster (E.13, E.14), row composition (E.49), buffer writing, change tracking |
| `render/level25_tests.rs` 840, `render/font_tests.rs` 345 | test-only modules; each begins with a `#[cfg(test)]`-marked line so the layer check strips it | the only place tests are in separate files |
| `viewer.rs` 665 | `Key` 16-53; `ViewerState`, `Action`, `ViewerEvent`, `SecurityIndicator` 55-117; `KeyContext`, `ComposeContext` 119-155; `Viewer` 160-175; `impl Viewer` 177-507 (`key` 287-383, `status` 424-472, `compose` 483-506); `Composed`, `MAX_LISTED_SUBPAGES`, helpers 509-537; tests 539-665 | the machine (REQ-FSM-005), keys with the link confirmation (REQ-NAV-012, REQ-SEC-024), the status area (REQ-SEC-005), composition |
| `nav.rs` 328 | `LinkTarget`, `PageLinks` 9-53; stepping 55-114; `PageEntry` 116-179; `History` 181-276; tests 280-328 | four small concepts of one area |
| `forms.rs` 1570 | limits and aliases 18-41; `FieldKind`, `FieldSpec`, `OptionSpec`, `Method`, `FormSpec`, `FormError` 43-227; `Invalid`, `FormKey`, `FormAction`, `EntryMode`, `KEYPAD`, `MARKER` 229-316; `FormModel` 318-330; `impl FormModel` 332-788 (`new` 335-366, editing 387-593, `validate` 596-637, `pairs` 648-684, drawing 689-787); `copy`, validation helpers 790-892; tests 894-1570 | Appendix C.2/C.3 spec, REQ-NAV-009 editing, C.5 validation, REQ-WEB-011 pairs, C.4 drawing |
| `port.rs` 45, `config.rs` 303, `policy.rs` 172, `trace.rs` 64 | one concept each; `config::available` has two `cfg!` lines (46-47) | left as they are |
| `tests/common/mod.rs` 561 | builders, `Receiver`, `feed`, grid builders, `worst_case_page` | Cargo's convention; stays |

### 2.2 Over the limits

Functions over 80 lines: `Decoder::push` (`acq.rs:747-830`, 84: decoding errors into statistics plus the per-kind dispatch); `resolve_segment` (`enhance.rs:1553-1654`, 102: REQ-FSM-012 steps 1 to 7 in one loop); `process` (`enhance.rs:1905-1995`, 91: level fallback, blanking, designations, sources, the page-level walk, colour defaults, grid write-back); `Viewer::key` (`viewer.rs:287-383`, 97: the confirmation sub-machine, toggles, Fastext, stepping, history); the test `every_transition_of_the_walk` (`enhance.rs:2168-2271`, 104, a 25-row table). Near the bar: `decode` 57, `designation_report` 57, `row_codes` 56, `build_grid` 51, `column_triplet` 69, `rebuild_rows` 60, `objects::table` 66, `colour::resolve` 52, `changed_rows` 53, `write_line` 51, `to_triplet` 49, `RowCells::place` 45.

`impl` blocks over 300 lines: `impl Decoder` 724 (`acq.rs:581-1304`), `impl FormModel` 457 (`forms.rs:332-788`), `impl Walker` 453 (`enhance.rs:850-1302`), `impl Viewer` 331 (`viewer.rs:177-507`).

Files over 800 lines: `charset/tables.rs` 2414, `enhance.rs` 2303, `glyphs/bedstead.rs` 2076 (generated), `acq.rs` 1849, `forms.rs` 1570, `level1.rs` 1467, `packet.rs` 1365, `render.rs` 1278, `consts.rs` 1026, `render/level25_tests.rs` 840. Inline tests in them: `forms.rs` 677, `charset/tables.rs` 594, `acq.rs` 544, `packet.rs` 534, `level1.rs` 451, `enhance.rs` 244, `render.rs` 145.

Files over 500 and under 800: `charset/mod.rs` 658, `objects.rs` 643, `packet/function.rs` 651, `viewer.rs` 665, `fsm.rs` 579, `level15.rs` 519, `colour.rs` 514 — all over by their test modules except `objects.rs` (549 of code) and `function.rs` (651, no tests).

### 2.3 The sixteen duplicated patterns

| # | Pattern | Where |
|---|---|---|
| 1 | **The Table 26 spacing-attribute machine, implemented twice**: set-at, set-after, the held-mosaic reset rules, box codes, ESC, hold and release | `level1.rs:728-747` (`set_at`), `771-819` (`set_after`), `749-769` (`cell_glyph`) and `enhance.rs:1451-1468` (`RowState::set_at`), `1417-1448` (`set_after`), `1659-1674` (`level_1_glyph`); the second adds re-mapping and the E.47 conceal split |
| 2 | Row-address arithmetic (40 is row 24, else address − 40) | `level15.rs:86-90`; `objects.rs:483-485` (`row_of`); `tests/common/mod.rs:107` |
| 3 | The G0-with-diacritic character and the "@" of 2/A | `level15.rs:150-165` (`character`); `enhance.rs:268-289` (`enhancement_glyph`) |
| 4 | Sub-code and control-bit packing from nibbles | `packet.rs:433-436`, `505-519`, `640-645`, `689-702` |
| 5 | Hamming nibble readers | `packet.rs:404-407` (`nibble`); `packet/objects.rs:164-175` (`nibble_at`, `nibbles`); `service.rs:92-99` (`nibbles`, another meaning) |
| 6 | The placeholder address `PageAddress { magazine: Magazine::from_bits(1), page: PageNumber(0) }` | `acq.rs:96`, `acq.rs:614`, `acq/enhancement.rs:86`, `nav.rs:203`, `service.rs:76` |
| 7 | The lower row of double height | `level1.rs:1004-1015` (`fill_lower_row`); `enhance.rs:2028-2031` (`fill`), `1726-1731` (claimed cells) |
| 8 | Page-visibility rules: `boxed_mode` from C5 or C6; `inhibit` from C10 or a non-text page; row 0 hidden by C7 | `level1.rs:861` and `enhance.rs:1980`; `level1.rs:865` and `enhance.rs:2007`; `level1.rs:991-1001` and `enhance.rs:2015` |
| 9 | Active, Adaptive, Passive to 0, 1, 2 | `enhance.rs:352-358` (`type_index`); `objects.rs:431-437` (`type_offset`); `tests/common/mod.rs:171-177` |
| 10 | Bit-doubling folds | `render.rs:275-282` (`widen`), `431-433` (`double_half`); `render/font_tests.rs:159-160`; `render/level25_tests.rs:552-554` |
| 11 | Side-panel width clamping to 16 | `colour.rs:160`; `render.rs:598` |
| 12 | Page-function classification | `acq.rs:122-126` (`is_text_page`); `acq.rs:900-903`; `enhance.rs:1772-1784` (`is_enhancement_page`); `level1.rs:575,579` |
| 13 | Walk machinery under the same names in two modules | `level15::{WalkState, WalkAction, walk_transition, walk_*_name}` and `enhance::{the same, plus WalkEvent}` |
| 14 | A function and its `_traced` twin | `compose.rs:18-46` and `52-80`; `level15.rs:177-198`; `enhance.rs:1877-1902` |
| 15 | Flash-rate lists | `render.rs:93-96,102`; `enhance.rs:234-235`; `render/level25_tests.rs:75-79,90,115` |
| 16 | Test fixtures (`mag`, `header`, `text`/`row`) | `packet.rs:843`; `acq.rs:1316-1332`; `tests/common/mod.rs:31-54`; `tests/behaviour.rs:22-36` |

### 2.4 Naming

| Name | Where | Why it misleads |
|---|---|---|
| "enhancement", six things | `acq/enhancement.rs` (the store of enhancement pages), `enhance.rs` (the processor), `packet::Enhancement` (packet X/26), `level15::EnhancementPackets`, `acq::{EnhancementReport, EnhancementFaults}` (fault counts), `acq::{EnhancementKey, EnhancementPage, EnhancementSubPage, EnhancementPacket, EnhancementStore, EnhancementLookup}` | the one word names a packet, a page, a store, a processor and a report |
| `objects.rs` and `packet/objects.rs` | L3 and L1 | the same file name in two layers; the L1 file is mostly the Magazine Organization Table |
| `packet/links.rs` beside `packet::Links` | L1 | the file holds X/27/4 and X/27/5 (compositional) links; `Links` is X/27/0 (editorial) |
| `RowState`, `RowContext` | `level1.rs:644,676` and `enhance.rs:1342,1360` | two different records under one name each |
| `WalkState`, `WalkAction`, `walk_transition` | `level15.rs` and `enhance.rs` | two machines (REQ-FSM-007 and REQ-FSM-011) under one vocabulary |
| `consts.rs` sections "Phase I2a", "Phase I2b" | `consts.rs:881-980` | grouped by when they were written, not by clause |
| `SidePanels` in `colour.rs` | `colour.rs:132-181` | clause 12.5 is layout, not colour |
| `mod.rs` in two places, file-plus-directory in three | `charset/`, `glyphs/` against `acq/`, `packet/`, `render/` | two module styles |
| `packet::encode` beside `packet::decode` and `ecc::hamming84_encode` | | a module and two functions share one verb |

### 2.5 Tests

Inline `mod tests` at the end of 24 of the 36 source files, from 12 lines (`lib.rs`) to 677 (`forms.rs`); two separate test files under `render/` only, named `*_tests.rs`; `packet/*.rs`, `acq/enhancement.rs` and the generated glyph files tested from their parents; a 594-line test module inside the data file `charset/tables.rs`. Every inline test module carries a slightly different `#[allow(clippy::…)]` list. Integration tests in `tests/` are one file per area with `required-features` in `Cargo.toml`.

### 2.6 `cfg` inside shared files

Every capability feature is switched by `cfg!()` inside a function rather than by a gated file: `colour.rs:254,271,277,297`; `enhance.rs:112,206,887,1005`; `render.rs:595`; `config.rs:46-47`. Only `joining.rs`, `enhance.rs` and `level15.rs` are feature files. The `objects` module is compiled in the Level 1-only build. The `extended-sets` tables sit in `charset/tables.rs:114-168` with empty twins.

## 3. The target layout

Every top-level module keeps its name and its public items; a module that grows children becomes `name.rs` beside `name/` (the 2018 layout, so `charset/mod.rs` and `glyphs/mod.rs` go), the parent holding the spine (the type, its construction, the `mod` lines and `pub use` of each child's public items). No `neoteletext_core::` path changes; the `xtask` layer table, `ARCHITECTURE.md` section 9 and REQ-ARCH-011 are untouched because the first path component under `src/` is still the module. Tests go to `tests.rs` under the concept's directory. Sizes are approximate.

```
src/
  lib.rs                              115  unchanged
  consts.rs                            60  REQ-GEN-014 docs; mod lines; pub use of every child
  consts/signal.rs                     60  clauses 5, 6, 7.1
  consts/packets.rs                    50  7.1.2 Table 1; 9.8.1 service-data fields
  consts/audio.rs                      35  EN 300 708 independent data lines
  consts/pages.rs                      80  9.3.1 page geometry, sub-codes, control bits, receiver columns
  consts/coding.rs                     25  clause 8
  consts/triplets.rs                  190  12.3.1 Tables 27-29 incl. flash codes and G1 columns
  consts/enhancement_packets.rs       120  X/28, M/29, X/27/4 fields; page functions; link roles; designation shifts
  consts/object_pages.rs              130  10.5.1, 10.6, Annex E.8 capacities, Annex A.8 limits
  consts/character_sets.rs             25  NATIONAL_POSITIONS, G2_RIGHT_GUILLEMET, G3 codes, undefined positions
  consts/spacing_attributes.rs         80  Table 26, TTI aliases, Table 47 mosaics
  consts/colour.rs                     90  Table 30, Colour Map, re-mapping, side-panel columns, ADJACENT_CLUT_FLIP, SCREEN_COLUMNS
  consts/geometry.rs                   70  cell and page geometry, fonts, aspect, palette indices, double-height rows
  consts/timing.rs                     40  E.12, E.19, REQ-NAV-007, E.48 units
  consts/tests.rs                      45
  ecc.rs                              270  unchanged code
  ecc/tests.rs                        185
  types.rs                             40  docs; Instant; mod lines; pub use          (see 4.4 on the name)
  types/address.rs                    160  Magazine, PageNumber, PageAddress, hex_digit, SubCode, ControlBits
  types/presentation_fields.rs        115  Rgb12, ColourWords, Designations, SidePanelFields, DefaultColourFields, PresentationFields, FallbackFields
  types/font_glyph.rs                  40  FontGlyph
  types/fixed_vec.rs                   95  FixedVec
  types/tests.rs                       45
  packet.rs                           330  Packet, PacketMeta, SliceQuality, PacketError, PacketAddress, decode_address, Row, PagePacket, MagazinePacket, Decoded, decode, designation_code, nibble; mod lines; pub use
  packet/header.rs                    100  9.3.1: Header, HEADER_* indices, decode_header, encode::header
  packet/triplets.rs                  110  9.4.1: Triplet, Triplets, Enhancement, values_of/triplets_of/…; encode::{triplet_packet, value_packet, pointer_triplet}
  packet/editorial_links.rs           110  9.6.1: Link, Links, LINK_* indices, page_reference, decode_links; encode::{page_reference, links}
  packet/compositional_links.rs       115  9.6.2: CompositionalLink (was links.rs), compositional_links; encode::compositional_links
  packet/service_data.rs               60  9.8.1: ServicePacket, SERVICE_* indices, copy_bytes, decode_service
  packet/page_data.rs                 280  unchanged, plus encode::{page_enhancement, magazine_enhancement, page_function, designation_triplets}
  packet/triplet_fields.rs            245  Table 28 fields: ColourData, ObjectSource, ObjectKind, ObjectNumber, ObjectUsage, DisplayAttributes
  packet/function.rs                  400  TripletFunction, row_function, column_function, to_triplet, name, active_column
  packet/object_pages.rs               95  10.5.1: ObjectPacket, TripletLocation, triplet_location
  packet/magazine_table.rs            260  10.6: MotPosition … mot_totals and their encode
  packet/encode.rs                     60  the public encode module: set, address, row, nibble_packet, raw; pub use of each child's encoders
  packet/tests.rs                     535
  acq.rs                              260  docs; Decoder (struct, constructors, accessors, record_enhancement, tick, count); Route; constants; mod lines; pub use
  acq/page.rs                         165  StoredPage (REQ-ACQ-007/008, E.8)
  acq/store.rs                        115  PageStore (REQ-ACQ-005)
  acq/events.rs                        65  MagazineData, Discard, Event
  acq/statistics.rs                   135  Statistics, EnhancementFaults, EnhancementReport, PageBuild
  acq/reception.rs                    330  impl Decoder: push, enhancement_data, header, roll, row_like, the machine drivers, start, end, page_event
  acq/enhancement_pages.rs            110  impl Decoder: page_format, switch_to_enhancement, start_enhancement, name, name_from_table, route, store_enhancement
  acq/enhancement.rs                  464  unchanged: the store and the lookup
  acq/tests.rs                        545
  fsm.rs                              305  unchanged code (two machines of area FSM)
  fsm/tests.rs                        276
  service.rs                          165  unchanged code
  service/tests.rs                     31
  charset.rs                          440  the former mod.rs without its tests; mod lines
  charset/code_table.rs               110  CodeTable, lookup, g0_unicode, g2_table, base_unicode
  charset/designation.rs              180  Tables 32, 33, 34 with the lookups; the empty cfg(not) twins
  charset/extended_designations.rs     55  [extended-sets] EXTENDED_TABLE_32, EXTENDED_SECOND
  charset/latin.rs                    110  Tables 35, 36 and the E.78 national options
  charset/g0_standard.rs              115  Tables 38, 39, 40, 42, 44, 46
  charset/g0_extended.rs              125  the twelve own G0 sets (E.78, E.81)
  charset/g2.rs                       100  Tables 37, 41, 43, 45; Vietnamese and Armenian G2
  charset/g3.rs                        40  Table 48
  charset/arabic_script.rs            425  group 1001: the generated sets, JOINING_TYPES, JOINED_FORMS, lookups
  charset/thai_lao.rs                 130  group 1100
  charset/diacritics.rs                30  G2 column 4 marks
  charset/mosaics.rs                   45  Table 47
  charset/composition.rs              400  COMPOSITIONS, EXTENDED_COMPOSITIONS, search, compose
  charset/tests.rs                    815  the former mod.rs and tables.rs tests
  colour.rs                           130  ColourIndex, colour_index, ColourMap, Remapping; mod lines; pub use
  colour/side_panels.rs                50  clause 12.5, E.49
  colour/presentation.rs              135  PresentationSources, PagePresentation, resolve, colour_words
  colour/tests.rs                     200
  compose.rs                           80  unchanged
  level1.rs                            50  docs; mod lines; pub use
  level1/cell.rs                      300  Glyph, Size, Width, FlashMode, FlashRate, CharSource, CellAttributes, Cell
  level1/grid.rs                      170  Grid, DEFAULT_DESIGNATION, Zoom, DisplayOptions
  level1/designation.rs               140  DesignationSource, NationalSource, DesignationReport, designation_report, resolve_designation
  level1/row.rs                       185  RowState, RowContext, decode_row, set_at, cell_glyph, set_after
  level1/row/tests.rs                 230  the Table 26 tests
  level1/page.rs                      200  stored_row, build_grid, receiver columns, row_codes, row_24_shown, hide_header, fill_lower_row
  level1/tests.rs                     225  grid, attributes, designation and build_grid tests
  level15.rs                          285  unchanged code
  level15/tests.rs                    236
  objects.rs                           70  docs; PageLink, DefaultInvocation, EnhancementLinks; mod lines; pub use
  objects/links.rs                    160  roles, the table, links (REQ-OBJ-030..040)
  objects/body.rs                      90  Body, Fetch, stored_triplet
  objects/definition.rs               205  ObjectRef, Absent, find_local, find_public, row_of, Extent, prescan
  objects/tests.rs                     95
  enhance.rs                          300  docs; bounds; Inputs, Rows, Frame, Range, Slot, Collector, Walker (structs); mod lines; pub use
  enhance/attributes.rs               150  Rate, Flash, ATTRIBUTES, LEVEL_1_FLASH, Attrs, AttrChange, flash_rate; the cfg(not) stub of flash_of
  enhance/additional_flash.rs          35  [additional-flash-functions] flash_of
  enhance/characters.rs                55  EnhChar, enhancement_glyph, is_text
  enhance/planes.rs                    95  Plane, type_index, Area, area_of, scan_index
  enhance/machine.rs                  280  WalkState, Ended, WalkEvent, WalkAction, transitions, names, traced_action
  enhance/walk.rs                     330  impl Frame, impl Collector, impl Walker (new, walk, run, next_triplet, act, act_on_frame), is_display, has_display_triplets
  enhance/walk/placement.rs           130  impl Walker: placeable, column_triplet, designation, character, attribute
  enhance/walk/invocation.rs          145  impl Walker: default_object, invoke, within_limits, accept
  enhance/row.rs                      430  RowContext, RowState, Overlay, Resolved, cell_of, Segment, resolve_segment, level_1_glyph, impl Rows (context, row)
  enhance/sizes.rs                    110  RowCells and place (Annex C.3) with three accessors
  enhance/page.rs                     215  is_enhancement_page, apply, apply_traced, process, rebuild_rows
  enhance/tests.rs                    245
  joining.rs                           65  unchanged code
  joining/tests.rs                     65
  glyphs.rs                           290  G3Glyph, CharClass, class, GlyphEntry, GlyphSet, PLACEHOLDER, SPACING_MARKS; mod lines
  glyphs/loaded_font.rs               120  FontTableError, LoadedFont, LoadedGlyph (REQ-FNT-002/003/008)
  glyphs/bedstead.rs                 2076  generated, unchanged
  glyphs/g3.rs                        394  generated, unchanged
  glyphs/conformance.rs               280  unchanged code
  glyphs/tests.rs                     225  the former glyphs and conformance tests
  render.rs                           120  docs; CellLine, Field, RenderError, IndexFormat, IndexBuffer, ALL_ROWS, FIELD_LINES; mod lines; pub use
  render/flash.rs                     110  FlashPhase, rate_bit, flash_unit, flash_on, flash_shown, flash_visible
  render/flash/tests.rs                90
  render/options.rs                    80  ColourMode, RenderOptions
  render/colours.rs                   200  palette and resolved indices, plane, palette_mode_allowed, border_index, fill_palette, palette_colour
  render/colours/tests.rs             320
  render/raster.rs                    260  glyph lines, mosaics, fonts, underline, double width, G3, cell_line
  render/raster/tests.rs              640  the raster and loaded-font tests
  render/row.rs                       290  panel widths, source columns, writers, render_row, render_line, render_screen
  render/row/tests.rs                 220
  render/changes.rs                   150  ChangeTracker
  render/changes/tests.rs              80
  render/test_grids.rs                110  [cfg(test)] the grid, cell and option builders the render tests share
  viewer.rs                           300  Key, ViewerState, Action, ViewerEvent, SecurityIndicator, KeyContext, ComposeContext, Viewer (struct, new, accessors, select, event), MAX_LISTED_SUBPAGES; mod lines
  viewer/keys.rs                      150  impl Viewer: key, digit, step_subpage; colour_index
  viewer/status.rs                     60  impl Viewer: status; two_digits
  viewer/screen.rs                     50  impl Viewer: compose; Composed
  viewer/tests.rs                     127
  nav.rs                              280  unchanged code
  nav/tests.rs                         49
  forms.rs                            160  docs; limits and aliases; FormModel (struct, new, spec, focus, mode, reset, field, value); mod lines; pub use
  forms/spec.rs                       190  FieldKind, FieldSpec, OptionSpec, Method, FormSpec, FormError
  forms/editing.rs                    300  FormKey, FormAction, EntryMode, KEYPAD, MARKER; impl FormModel: move_focus, code_for, insert, backspace, step_choice, toggle, press, submit, key, remote_digit
  forms/validation.rs                 150  Invalid; impl FormModel::validate; the rule functions
  forms/submission.rs                  50  impl FormModel: chosen_option, pairs
  forms/draw.rs                       120  impl FormModel: draw, draw_radio, paint, scroll, shown_codes; copy
  forms/tests.rs                      677
  port.rs 45 · config.rs 258 + config/tests.rs 47 · policy.rs 118 + policy/tests.rs 55 · trace.rs 64
tests/ and examples/ unchanged
```

Where capability features move to gated files and where they stay:

| Feature | Moves to a gated file | Stays in-line, because the two forms share one function |
|---|---|---|
| `additional-flash-functions` | `enhance/additional_flash.rs` holds `flash_of` (`enhance.rs:200-228` without its line 206), declared `#[cfg(feature = "additional-flash-functions")] mod additional_flash;`; `attributes.rs` keeps a three-line `#[cfg(not(…))] const fn flash_of(…) -> Option<Flash> { None }` — one item in two forms, behaviour unchanged | |
| `extended-sets` | `charset/extended_designations.rs` holds `EXTENDED_TABLE_32` and `EXTENDED_SECOND` (`tables.rs:114-163`), declared with one gated `mod`; the empty twins (`164-168`) stay in `designation.rs` under `#[cfg(not(…))]` | the joined-form block of `conformance` (`glyphs/conformance.rs:245-258`); the joining call in `compose.rs` (already item-form) |
| `nonspacing-attributes` | | `ATTRIBUTES` and the four guarded arms of `column_triplet` (`enhance/walk/placement.rs`): one `match` in two forms |
| `objects` | | `cfg!(feature = "objects")` in `Walker::run` and `Walker::act` (`enhance/walk.rs`): two arms of one loop and one `match`; `invocation.rs` itself is ungated because the finder module `objects` is ungated |
| `side-panels` | | `resolve` (`colour/presentation.rs`) and `panel_widths` (`render/row.rs`): one function, two forms; `SidePanels` is used ungated by `level1::Grid` |
| `level25-32colors`, `level35-32colors` | | `resolve` (`colour/presentation.rs`): three branches of one function |
| `level15`, `level25` | | `compose.rs` match arms and `config::available`: already on items |

Every item used by two features stays in an ungated file (`SidePanels`, `FlashMode`, `FlashRate`, `objects::*`, `acq::statistics`); nothing is duplicated.

## 4. The moves

Each step is one commit that passes `scripts/check.sh fast` and `cargo xtask features`; each moved test file begins with a `#[cfg(test)]`-marked line (`#[cfg(test)] use super::*;`, as `render/font_tests.rs:10-11` does today) so that `cargo xtask check-layers` strips it, and carries as inner attributes the `#![allow(clippy::…)]` list its former `mod tests` had. A `tests.rs` is declared from its parent with `#[cfg(test)] mod tests;` (or `#[cfg(all(test, feature = "bedstead"))]` where the parent's tests are so gated today). The commit message names the step number here and lists the visibility changes. `cargo fmt` runs on the untouched tree first, as its own commit if it changes anything.

Steps 1 and 2 touch tools only; 3 moves tests; 4 onward go module by module from the leaves.

### Step 1: widen `DATA_FILES` in `xtask/src/checks.rs`

`DATA_FILES` (`checks.rs:212`) exempts files from `check-constants` by suffix: `charset/tables.rs`, `glyphs/bedstead.rs`, `consts.rs`. Change the match to directory prefixes (`crates/neoteletext-core/src/consts/` and `consts.rs`, `charset/` table files, `glyphs/bedstead.rs`), with a test that a watched literal in `consts/signal.rs` is still exempt and one in `level1/cell.rs` is not. No source moves. The existing files still match.

### Step 2: make `scripts/arabic-sets.py` name its target once

`arabic-sets.py:6,23,35-36` name `charset/tables.rs`; the target becomes a single constant to be changed in step 15, and the docstring says the block it rewrites. Run it to confirm a byte-identical regeneration of `tables.rs:798-1196`.

### Step 3: tests out of the leaf files

Pure moves of inline test modules to `tests.rs`, each file becoming `name.rs` beside `name/`: `consts.rs:982-1026` → `consts/tests.rs`; `ecc.rs:269-451` → `ecc/tests.rs` (needs `pub(super)` on `build_hamming84_table`, `hamming84_decode_slow`, `hamming84_data`, `HAMMING84_TABLE`, `triplet_word`, `TRIPLET_DATA_MASK` is `consts`'); `types.rs:428-471` → `types/tests.rs`; `fsm.rs:304-579` → `fsm/tests.rs`; `service.rs:165-195` → `service/tests.rs` (`date_time`, `offset`, `OFFSET_NEGATIVE` → `pub(super)`); `level15.rs:284-519` → `level15/tests.rs` (`walk_transition` is public; `write`, `WalkContext` fields read by the tests are constructed as literals — `WalkContext` is `pub` with `pub` fields, fine; `write` → `pub(super)`); `nav.rs:280-328` → `nav/tests.rs`; `config.rs:257-303` → `config/tests.rs`; `policy.rs:118-172` → `policy/tests.rs`; `joining.rs:65-129` → `joining/tests.rs`. `lib.rs`'s 12-line test and `trace.rs`/`port.rs` (no tests) stay. Documents citing `port.rs` (`hmi.md:21,48`) are unaffected.

`fsm.rs` is left whole (303 lines, two machines of one area, REQ-FSM-003 and REQ-FSM-004, each a table-driven `match`): a split would leave a parent of a `PageKey` and two `pub use` lines, which the conventions call a sign to flatten.

### Step 4: `consts` by clause

`consts.rs` becomes the parent of fourteen children named in section 3, each taking its banner's lines verbatim with the doc comments (the mapping of lines to files is: signal 10-63; packets 65-98 and 866-879; audio 100-129; pages 131-203; coding 205-226; triplets 228-385, 948-968, 976-980; enhancement_packets 387-485, 934-946, 589-601; object_pages 487-586, 908-933; character_sets 602-606, 886-889, 970-975; spacing_attributes 608-685; colour 687-768, 890-892, 900-902; geometry 770-828, 893-894, 903-907; timing 830-864). Items that derive from another file's constant (`IDL_AUDIO_SERVICE_BYTE` from `DATA_START`, `OBJECT_TRIPLETS_IN_ROWS` from `PACKET_ROW_25` and `TRIPLETS_PER_PACKET`, `SCREEN_COLUMNS` from `COLUMNS`, `ENHANCEMENT_SUBPAGE_PACKETS`, `SIDE_PANEL_AREA_COLUMNS`, `PAGE_WIDTH`, `LOCAL_TRIPLETS`, `WALK_DEPTH`) take `use super::<child>::NAME;` lines. The parent's `pub use signal::*;` … lines keep `crate::consts::X` and `neoteletext_core::consts::X`. No visibility changes. Departure: the parent is a ~60-line file of docs and re-exports; it is kept because `consts` is the one home REQ-GEN-014 and `check-constants` name.

### Step 5: `types` by concept (optional)

`types/address.rs` (8-163), `types/presentation_fields.rs` (165-277, with `RED_SHIFT`/`GREEN_SHIFT` staying private there), `types/font_glyph.rs` (279-317), `types/fixed_vec.rs` (332-426); `Instant` (319-330) stays in the parent. No visibility changes. Departure from convention section 1 ("no `types` files"): the module name `types` is a public path used at some fifty sites across the engine crates, the browser (3), the fuzz targets and the firmware image, and is a row of the layer table; renaming it is a public-path change this plan does not make. The children are named by concept so that the parent is only the spine.

### Step 6: `packet`

Sub-steps, each a commit:

6a. `packet/function.rs` → `packet/triplet_fields.rs` (25-263) and `packet/function.rs` (265-651). The field constructors `ColourData::from_data/data`, `ObjectSource::from_bits/bits`, `ObjectNumber::from_fields/data/high`, `DisplayAttributes::from_data/data`, `flag` become `pub(super)` (nine items). `packet.rs`'s `pub use function::{ColourData, DisplayAttributes, ObjectKind, ObjectNumber, ObjectSource, ObjectUsage, TripletFunction}` becomes two lines.

6b. `packet/objects.rs` → `packet/object_pages.rs` (21-113) and `packet/magazine_table.rs` (115-369 with its `encode`); `DATA_FIRST_BYTE_NUMBER` → `pub(super)`; the `pub use objects::{…}` in `packet.rs` is rewritten over the two files.

6c. The decoders out of `packet.rs`: `packet/header.rs` (126-155, 409-458, and `encode::header` 625-654 as a child `pub(super) mod encode`), `packet/triplets.rs` (168-217, 460-488, `encode::{triplet_packet, value_packet, pointer_triplet}` 666-686, 749-753, 800-806), `packet/editorial_links.rs` (219-243, 503-549, `encode::{page_reference, links}` 688-738), `packet/compositional_links.rs` (`links.rs` renamed, plus 490-501 and `encode::compositional_links` 755-768), `packet/service_data.rs` (267-284, 551-587), `page_data.rs` gaining `encode::{designation_triplets, page_enhancement, magazine_enhancement, page_function}` (740-747, 770-798). `pub(super)`: `decode_header`, `HEADER_*`, `values_of`, `triplets_of`, `triplet_body`, `triplets`, `triplet_values`, `page_reference`, `decode_links`, `compositional_links`, `decode_service`, `nibble`, `designation_code`, `presentation_values`, and each child `encode` module.

6d. `packet/encode.rs`: the public `encode` module with `set` (`pub(super)`), `address`, `row`, `nibble_packet`, `raw` (609-623, 656-664, 808-829) and `pub use` of every child's encoders, so `packet::encode::{header, row, triplet_packet, links, compositional_links, page_enhancement, magazine_enhancement, page_function, designation_triplets, pointer_triplet, nibble_packet, raw, address, mot_page_entry, mot_object_link, mot_totals}` keep their paths (the formats crate, the browser and the fuzz targets use them).

6e. `packet.rs:832-1365` → `packet/tests.rs`, with `use super::header::HEADER_UNITS; use super::triplets::triplet_values;`.

After each sub-step: `cargo build -p neoteletext-formats --all-features` and `cargo check --manifest-path fuzz/Cargo.toml`.

### Step 7: `acq`

`Decoder` stays in `acq.rs` (the spine), so its private fields are visible to every child file; nothing on it widens. Sub-steps:

7a. `acq/page.rs` (41-204; `erase`, `merge` → `pub(super)`), `acq/store.rs` (206-316; `allocate`, `page_mut` → `pub(super)`), `acq/events.rs` (318-379), `acq/statistics.rs` (381-514, the `cfg(level25)` `impl` unchanged). `acq.rs` gains the `mod` and `pub use` lines.

7b. `acq/reception.rs`: a second `impl Decoder` with `push` 747-830, `enhancement_data` 834-894, `header` 1020-1047, `own_header_event` 1049-1061, `roll` 1065-1082, `row_like` 1089-1130, `magazine_event` 1149-1185, `discard` 1187-1190, `start` 1192-1219, `header_store` 1224-1233, `store_header` 1236-1251, `end` 1253-1270, `page_event` 1273-1303. `acq/enhancement_pages.rs`: a third `impl Decoder` with `page_format` 900-912, `switch_to_enhancement` 917-929, `start_enhancement` 934-945, `name` 948-956, `name_from_table` 961-970, `route` 979-986, `store_enhancement` 1134-1146; `route`, `start_enhancement`, `store_enhancement`, `page_format` → `pub(super)` (called from `reception.rs`). `page_event`, `magazine_event`, `end` → `pub(super)` (called from `enhancement_pages.rs` and `tick`). `acq.rs` keeps 585-744 and `tick` 991-1007, `count` 1009-1016.

7c. `acq.rs:1306-1849` → `acq/tests.rs` (its `EnhancementMemory`, `object_bytes`, `table_with_pop_link` helpers go with it).

### Step 8: `level1`

`level1/cell.rs` (31-329), `level1/grid.rs` (331-501), `level1/designation.rs` (503-638), `level1/row.rs` (640-819), `level1/page.rs` (821-1015). Visibility: `RowContext` stays private to `row.rs` and gains `pub(super) const fn new(config, default_g0, second_g0, double_allowed)` (four arguments) for `page.rs`'s `build_grid`; `decode_row` → `pub(super)`; `stored_row` stays private in `page.rs`; `RowState` stays `pub` as today. Tests: `level1.rs:1043-1270` (the Table 26 and Annex G tests, which build `RowContext` literals) → `level1/row/tests.rs`, a child of `row` so that it sees `RowContext`'s private fields and `set_at`/`set_after`; `level1.rs:1272-1466` → `level1/tests.rs`. Departure: `level1/row/` is a third level under `src/`; it exists for the tests of the row machine alone, so that `RowContext`'s fields stay private.

### Step 9: `colour` and `objects`

`colour/side_panels.rs` (132-181), `colour/presentation.rs` (183-315 with the four `cfg!` lines in `resolve`, which stay because they are branches of one function), `colour/tests.rs` (317-514 with its `cfg_attr`). `objects/links.rs` (103-259), `objects/body.rs` (261-346), `objects/definition.rs` (348-548), `objects/tests.rs` (550-643); `ROLES`, `usable`, `compositional`, `table_link`, `TableLinks`, `table` stay private to `links.rs`; `type_offset`, `usage_includes`, `check_definition` private to `definition.rs`. `SidePanels` stays in `colour` because a new top-level module would change the layer table.

### Step 10: `enhance`

The records every child reads — `Inputs` (549-559), `Rows` (1786-1799), `Frame` (391-418), `Range`, `RANGES`, `OPEN_RECORDS`, `Sets`, `Slot`, the `Collector` struct (445-493), the `Walker` struct (837-848) — move into `enhance.rs` beside the bounds (61-72), so that their fields stay private and are visible to every file under `enhance/`. Sub-steps:

10a. `enhance/attributes.rs` (74-199, 230-242; `pub(super)`), `enhance/additional_flash.rs` (`flash_of` 200-228 without line 206, gated; a `#[cfg(not(feature = "additional-flash-functions"))] pub(super) const fn flash_of(_: u8, _: u8, _: u8, _: u8) -> Option<Flash> { None }` stays in `attributes.rs`), `enhance/characters.rs` (244-295), `enhance/planes.rs` (297-389), `enhance/machine.rs` (561-835; the four `pub` items keep their paths through `pub use machine::*`).

10b. `enhance/walk.rs`: `impl Frame` (420-443), `impl Collector` (495-547), `Walker::new/walk/run/next_triplet/act/act_on_frame` (850-944, 969-1064), `is_display`, `has_display_triplets` (1304-1331); `enhance/walk/placement.rs`: `placeable`, `column_triplet`, `designation`, `character`, `attribute` (1066-1192); `enhance/walk/invocation.rs`: `default_object` (946-967), `invoke`, `within_limits`, `accept` (1194-1301). All `pub(super)` within `enhance`. The two `cfg!(feature = "objects")` lines stay in `walk.rs` (`run` and `act`), two forms of one loop and one `match`. Departure: a third level (`enhance/walk/`), allowed for a large concept; the walk is 900 lines.

10c. `enhance/row.rs` (1333-1674 and `impl Rows { context, row }` 1801-1866) and `enhance/sizes.rs` (`RowCells` 1676-1765). `RowCells` gains three `pub(super)` methods so that `rebuild_rows` reads no field: `placed(&self) -> &[Option<Cell>; SCREEN_COLUMNS]`, `fill(&self) -> [Cell; COLUMNS]` (the lower-row fill now built in `rebuild_rows:2028-2031`) and `remember(&mut self, grid, row)` (the `above` update of 2052-2055). These are the only new lines of code in the step and are named in the message. Departure: `row.rs` is about 430 lines, under the 500 ceiling; `RowContext` (nine fields) is built by `Rows::context` in the same file, which is why `Rows`'s methods live here.

10d. `enhance/page.rs` (1767-1784, 1868-2058) and `enhance/tests.rs` (2060-2303 with its `cfg_attr`).

### Step 11: `render`

11a. `render/flash.rs` (69-156, 468-473, 940-949), `render/options.rs` (158-236), `render/colours.rs` (238-271, 475-528, 582-590, 632-654, 903-938), `render/raster.rs` (273-466, 530-580, every `#[inline]`, `#[cold]` and measured comment moved with its item), `render/row.rs` (592-631, 656-662, 701-901, 1097-1119), `render/changes.rs` (951-1095). `pub(super)`: `displayed_colours`, `resolved_colours`, `palette_row_allowed`, `flash_shown`, `rate_bit`, `panel_widths`, `PANEL_AREA_END`, `glyph_line_20`, `widen`, `mosaic_block`, `mosaic_line`, `SEPARATED_COLUMNS`, `CELL_MASK`, `check_mode`, `write_line`; `font_line_20` keeps `pub(crate)`.

11b. The tests, redistributed by concept, moved function by function and never rewritten: `render/flash/tests.rs` (`level25_tests.rs:81-138`, `render.rs:1270-1277`); `render/colours/tests.rs` (`level25_tests.rs:140-384`, `render.rs:1183-1194,1236-1268`); `render/raster/tests.rs` (`level25_tests.rs:545-782`, `render.rs:1153-1181`, all of `font_tests.rs`); `render/row/tests.rs` (`level25_tests.rs:386-543`, `render.rs:1196-1219`); `render/changes/tests.rs` (`level25_tests.rs:784-840`, `render.rs:1221-1234`). The builders they share (`latin`, `text`, `g3`, `options`, `large`, `line_of`, `screen`, `level1_grid`, `labelled_grid`, `columns_shown`, `normal_mask`, `doubled`, the `PATTERN`/`OTHER` fonts and `fonts()`) become `render/test_grids.rs`, a `#[cfg(all(test, feature = "bedstead"))] mod test_grids;` named by what it holds. `level25_tests.rs` and `font_tests.rs` are deleted; the `*_tests.rs` form leaves the crate. Each new test file keeps the `#[cfg(test)] use super::*;` first line. If the owner prefers one move, a single `render/tests.rs` of the three modules (1,330 lines) is the fallback.

### Step 12: `viewer`

`Viewer` stays in `viewer.rs` with `new`, accessors, `select`, `event` (177-282) and `MAX_LISTED_SUBPAGES`; `viewer/keys.rs` (`key`, `digit`, `step_subpage` 284-420; `colour_index` 524-532), `viewer/status.rs` (`status` 422-472; `two_digits` 534-537), `viewer/screen.rs` (`compose` 474-507; `Composed` 509-517, re-exported), `viewer/tests.rs` (539-665). `select` → `pub(super)`. `docs/spec/design/hmi.md:18` cites `viewer.rs:20` (`Key`), which stays in the parent at a new line.

### Step 13: `forms`

`FormModel` stays in `forms.rs` with `new`, `spec`, `focus`, `mode`, `reset`, `field`, `value` (318-416) and the limits (18-41); `forms/spec.rs` (43-227; `FieldSpec::cells`, `cells_at` → `pub(super)`), `forms/editing.rs` (248-316 and 418-593), `forms/validation.rs` (229-246, 595-637, 799-892; `valid_email`, `valid_tel`, `valid_number`, `valid_date`, `valid_time` → `pub(super)` for the tests), `forms/submission.rs` (639-684; `chosen_option` → `pub(super)` for `draw.rs`), `forms/draw.rs` (686-797), `forms/tests.rs` (894-1570). `field` → `pub(super)`. `hmi.md:19-20` cite `forms.rs:250` (`FormKey`, now `forms/editing.rs`) and `forms.rs:34` (`MULTITAP_US`, still the parent).

### Step 14: `glyphs`

`glyphs/mod.rs` → `glyphs.rs`; `glyphs/loaded_font.rs` (98-211 with `PAIR_RIGHT_PIXELS`); `glyphs/tests.rs` (the former `mod.rs:405-487` and `conformance.rs:280-420`; `conformance::{FIRST_CODE, LAST_CODE}` → `pub(super)`). The generated `bedstead.rs` and `g3.rs` are not moved (`xtask/src/glyphs.rs:31,33`); their `pub(super)` items are read by `glyphs.rs` as before. `languages.md:172` cites `glyphs/mod.rs:140` (`LoadedGlyph`, now `glyphs/loaded_font.rs`).

### Step 15: `charset` tables by spec table

`charset/mod.rs` → `charset.rs`; `tables.rs` is replaced by the twelve files of section 3 (code_table 12-39, 592-630, 730-741, 781-787; designation 41-113, 164-245; extended_designations 114-163 gated; latin 247-355; g0_standard 357-467; g0_extended 469-590; g2 632-728; g3 743-779; arabic_script 789-1211 with the `BEGIN`/`END` markers; thai_lao 1213-1342; diacritics 1344-1373; mosaics 1375-1420; composition 1422-1819), each `#[rustfmt::skip]` on its `mod` line. The sixteen `pub(super)` functions keep that visibility; the tables they read (`LATIN_G2` for `latin_g2_with`, `COMBINING_MARKS` for the composition test, `FULL_BLOCK`, `MOSAIC_LEFT_COLUMN`, `MOSAIC_RIGHT_COLUMN`, `COMPOSITIONS`, `EXTENDED_COMPOSITIONS`, `search`, `GROUP_SHIFT`, `NATIONAL_BITS_MASK`, `ENGLISH_DESIGNATION`, `base_unicode`, `diacritic_combining`, `mosaic_unicode`, `modified_designation`, `default_second_g0`, `designation`, `second_g0`) become `pub(super)` where a sibling or `charset/tests.rs` reads them. `charset/tests.rs` takes `mod.rs:441-658` and `tables.rs:1821-2414`. The step changes `scripts/arabic-sets.py`'s target constant (step 2) to `charset/arabic_script.rs`, runs it, and updates `ARCHITECTURE.md:372`, `IMPLEMENTATION-LOG.md:17` and `TECH-DEBT.md:85` where they say `tables.rs`. Departures: `arabic_script.rs` (~425) and `composition.rs` (~400) are tables and generated data; `tests.rs` is 815 lines of tests; the own G0 tables stay ungated because `g0_unicode`'s `match` names every `G0Set` variant in every build.

### Step 16: the documents

Regenerate `docs/traceability.md` (`cargo xtask trace`); fix the line citations in `docs/spec/design/hmi.md:18-20` and `languages.md:172`; add the implementation-log row; `ARCHITECTURE.md` section 9 needs no change, its section 3 gains one sentence per module directory. Then `scripts/check.sh full` (which fails if running it changed a committed file), and the push to `implementation`.

## 5. Risks particular to this crate

| Risk | What meets it |
|---|---|
| `check-constants` exempts files by name suffix (`checks.rs:212`); after step 4 the literals `0x27`, `0xE4`, `0x55` and `6_937_500` are in `consts/signal.rs`, after step 15 the character tables are in twelve files | Step 1 widens `DATA_FILES` to directory prefixes before any file moves, with a test either way. |
| `check-layers` strips a file from its first `#[cfg(test)]` or `#[cfg(all(test,` marker (`checks.rs:51-60`); a moved test file without one is scanned as code, and `acq/tests.rs` would then fail on `crate::packet::encode`, `enhance/tests.rs` on nothing today but on any later `use` | Every moved test file begins with the marked `use super::*;` line; a gate run after each step. |
| Sibling files cannot see private fields; the convention keeps fields private | The structs whose `impl` spreads over children (`Decoder`, `Walker`, `Frame`, `Collector`, `Inputs`, `Rows`, `Viewer`, `FormModel`) are defined in the parent file, which every child is a descendant of; `RowContext` (level1) gets a four-argument constructor; `RowCells` gets three accessors; the Table 26 tests of `level1` sit under `level1/row/` for the same reason. Every `pub(super)` item is listed under its step. |
| The bare-metal size and symbol check (`cargo xtask size`), and the two ignored measurements that justify `#[inline(always)]` on `GlyphSet::glyph` and `cell_line`, `#[cold]` on `font_or_text_line` and `#[inline(never)]` on `styled_line`, `widen_mask`, `g3_line`, `resolved_colours` (`render.rs:353-357,379,417-418,537-538`) | One crate, LTO, `codegen-units = 1`: the image should be identical. `cargo xtask size` on the remote host before step 4 and after steps 10, 11 and 14; `cargo test -p neoteletext-core --release --test performance --test flash_cost -- --ignored --nocapture` before step 11 and after it, numbers in the commit message. |
| `docs/traceability.md` lists 244 core paths and the full gate fails if it is stale | Regenerated at step 16 (and may be regenerated at any step; it is generated from the tree, `xtask/src/trace.rs:10-21`). |
| Design documents cite lines: `hmi.md:18-20` (`viewer.rs:20`, `forms.rs:250`, `forms.rs:34`), `languages.md:172` (`glyphs/mod.rs:140`); `ARCHITECTURE.md:372`, `IMPLEMENTATION-LOG.md:17`, `TECH-DEBT.md:85` name `tables.rs`; the browser's `docs/hyperlinks.md:67` names `level1.rs` | Fixed in the step that moves the item (12, 13, 14, 15) or at step 16; the browser's line at its re-pin (phase E5). |
| `TECH-DEBT.md` records that the `modern-classic`, `classic`, `render` and `bedstead` feature builds were failing on 19 October 2026 (issue 221), before HEAD `fb2dd8a` "Build every feature set again" | Run `cargo xtask features` on `fb2dd8a` before step 1 and record which of the twelve builds pass; each step must keep every passing build passing, and must not be blamed for one already failing. |
| Clippy pedantic's `too_many_lines` (100) and `too_many_arguments` (7) under `-D warnings` | No function is merged or grown; the one new constructor has four arguments; `resolve_segment` (102 physical, fewer code lines) passes today and is moved whole. |
| `#[rustfmt::skip]` on the table modules | On each new `mod` line in `charset.rs` and on the generated glyph modules as today, else `cargo fmt --check` reflows the 96-entry rows. |
| `scripts/arabic-sets.py` writes a block of `tables.rs` | Step 2 makes the target one constant; step 15 changes it and proves a byte-identical regeneration. |
| The 2018-layout rename of `charset/mod.rs` and `glyphs/mod.rs` | Pure renames (`git mv`), no path change; `xtask/src/glyphs.rs` names only the generated children. |

## 6. Seen, not part of this plan

- The Table 26 spacing-attribute machine is implemented twice (`level1.rs:728-819` and `enhance.rs:1417-1468,1659-1674`); the second copy carries the re-mapping and the E.47 conceal rule. One machine with the Level 2.5 differences as parameters would remove the risk of the two drifting apart.
- Five copies of the placeholder address `Magazine::from_bits(1), PageNumber(0)` (`acq.rs:96,614`, `acq/enhancement.rs:86`, `nav.rs:203`, `service.rs:76`) with no name; a `PageAddress::PLACEHOLDER` or an `Option` would say what it is.
- `glyphs/conformance.rs:103-165` is a hand-kept mirror of `FONT_SETS` (35-92), checked by a test; the index could be derived from the table.
- `scripts/arabic-sets.py` writes two `// DUPLICATES {'#'}` comments at `charset/tables.rs:572,590` (Georgian and Tifinagh share `#` at 5/F and 2/3); a generator's note left in reviewed data.
- `consts.rs:325-328` `ROW_ADDRESS_RESERVED_DEFAULT` and `packet/function.rs:534` write Full Screen Colour with address 41 on encoding, while decoding ignores the address; the asymmetry is documented but worth a test.
- `objects` (643 lines) is compiled in every build including the Level 1-only image; gating `pub mod objects` on `level25` would remove a public path from builds that cannot use it, which this plan does not do.
- REQ-GEN-020's text names a feature `original`; the manifest has `bedstead`.
- `MULTITAP_US` and `KEYPAD` (`forms.rs:32-34,309-311`) cite "decision 12 of IMPLEMENTATION-LOG.md" rather than a decision in Part E.
- `proptest` is a dev-dependency of the core that no test uses.
- The `debug-fmt` feature is declared and tested by nothing.
- `docs/teletext-specification-audit.md` (untracked) still names `drcs.rs` and `render.rs:393`, both gone.
