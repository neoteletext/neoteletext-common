# Renderer parity: what is still to be built for teletext, ReGIS and NAPLPS to be equals

| | |
|---|---|
| **Status** | Specification of 19 November 2026, written while the owner was away, for building at once by implementation agents in each repository working apart. The owner's decision is DEC-6638 (version 2) with the owner's later rulings DEC-6667 (the NAPLPS picture on the teletext raster) and DEC-6669 (only the provided character sets for text). What this document decides beyond them is listed in section 21 and recorded in rdm as one decision for the owner's confirmation. |
| **Asked for by** | The owner, 18 November 2026: every renderer has the same enhancements as the others except where that makes no sense, after the comparison of that day (`~/devel/teletext-reference/renderer-enhancements-comparison.html`). |
| **Process** | DEVELOPMENT.md section 2.3 (a proposal with its own security analysis, section 19 here), section 3.5 (every record in full) and section 14 (security). |
| **Companions** | `page-rules.md` (RULE-n) and `animation.md` (ANIM-n): the rule table, the objects, the records 21 to 33 and push protocol 10, on which this work builds and which it does not change. |
| **Repositories it changes** | neoteletext-renderer-teletext (the engine), neoteletext-renderer-regis, neoteletext-renderer-naplps, neoteletext-app-server, neoteletext-browser, neoteletext-server-ts-protocol (the TypeScript kit), neoteletext-server-channels (the Python kit), neoteletext-server-ts-ui-components (the component library), and this repository. |

Requirements are numbered `PAR-n` and grouped in sections, **one section to one implementing repository**, so that each section is one rdm requirement in that repository (section 22). Each requirement names the row of DEC-6638 (and of the comparison, whose row numbers DEC-6638 uses) that it serves, and the clause of a standard where behaviour comes from one. Every bound is a named constant of the crate or module that owns it, stated once here with its value and used by name everywhere else.

**A page, in this document, is one page number and one sub-code together** (DEC-6599). A picture belongs to exactly one such page; nothing is addressed by a page number alone, and sub-code `3F7F` never names a picture.

---

## 1. What is already built and what this document covers

### 1.1 Built before this document (checked against the code on 19 November 2026)

The code read: the engine at `livedevelopment` 3e5ddb03; the ReGIS renderer at `livedevelopment` f6d14d8 (its branch `parity`, with labels and titles, merged); the NAPLPS renderer at `livedevelopment` b435b7d; the server at `livedevelopment` 68b3b42 (program protocol 15, `protocol/schema-15.json`); the browser at `livedevelopment` c3d541c (branches `rules-2` and `naplps-raster` merged); the TypeScript kit at f237228 (release 18.1.0); the Python kit at 505c6a1; the component library at b040c6f (release 26.0.1).

| DEC-6638 row | What | Where it is built |
|---|---|---|
| 1.3, 1.5 | NAPLPS objects detectable, in the pick record, with hover and pressed looks | `NAPLPS_OBJECTS` record type 25 (ANIM-11); the browser's decoder makes the pick record from objects (`decoder/src/naplps.rs`) and draws looks (commit cdf069a, TODO-6747) |
| 1.4 | The hand pointer over a NAPLPS object | the trusted core's pointer path reads the pick record whatever its language (`core/src/regis_pointer.rs`) |
| 1.6 | Hover events to the channel for NAPLPS objects | under push protocol 10 every input reaches a channel only inside `RULE_EVENT` (RULE-46); an `enter` or `leave` on a NAPLPS object is carried as the MOUSE move that caused it with the object named as the target. No `DRAWING_HOVER` for objects is needed (section 21 item 1) |
| 2.8 | A title the picture carries | ReGIS `D(T'…')` (REQ-6653); NAPLPS `NAPLPS_OBJECTS` flag `TITLED` (REQ-6644, TODO-6657 done). Using them in page lists and the screen reader is TODO-6658, not repeated here |
| 3.2 | A NAPLPS object redefined by a record | `NAPLPS_OBJECTS` flag `ONE` (REQ-6645) |
| 4.3 | Sound tied to a page's own objects | a rule on `press` or `enter` running a group with a local sound command (RULE-21); nothing separate |
| 5.1 | NAPLPS supplementary-set glyphs | the NAPLPS stroke font (TODO-5791's remaining work is a layout comparison) |
| 5.1 | Other scripts for NAPLPS | the 55 provided sets by ISO 2022 private designations (REQ-6668), passed by the browser (TODO-6679) |
| 6.1 | Labels on drawings and objects | REQ-6652 and REQ-6643; the screen-reader tree is TODO-6658 with REQ-761 |
| 7.4 | The NAPLPS picture's place | the teletext raster, 480 by 462 from line 19 (DEC-6667, REQ-5819, TODO-6679) |
| 7.7 | NAPLPS WAIT and BLINK | on the tick clock (DEC-6524) |
| 8.4 | Random-input testing of both languages | property tests in each renderer |
| 9.3 | An authoring check for NAPLPS | `naplps-render check` (REQ-6646) |

### 1.2 Not applicable (DEC-6638 as recorded)

Local echo (1.12, withdrawn everywhere); TOP navigation (2.9, not built for teletext either); the 4:3 aspect option (7.3, the fit setting serves pictures); reveal, mix and zoom for vector pictures (7.8, hold alone applies); sitemap (11.3, undecided for teletext too).

### 1.3 What this document specifies

Everything else of DEC-6638 items 2 to 7: the NAPLPS cursor and links on NAPLPS objects (1.2, 2.1, 2.2), touch looks checked (1.9), small-target picking (1.10), the component library for pictures (1.11), keyboard reach and link marks (2.3, 6.3), the server keeping picture streams (3.3, 3.4), static channels with pictures (3.5), picture pages kept (3.6), capability bits and the mosaic fallback (3.7), Unicode text runs, right-to-left order, Arabic joining and the provided sets for ReGIS (5.1 to 5.3, DEC-6669 item 4), text measurement (5.4), user-loadable fonts (5.5), reduced motion (6.2), the header row above pictures (7.6), hold (7.8), the embedded back end (7.10), the server checking NAPLPS (8.3, 10.4), the security analysis (8.5), `neottx` for pictures (9.1), the picture converter (9.2), writing pages from text (9.4), the kits (10.2, 10.3), and public pages and static HTML with pictures (11.1, 11.2).

### 1.4 The numbers this document takes

| What | Number or value | Free because |
|---|---|---|
| Capability `REGIS_CAP` | bit 23 (`1 << 23`) | `neoteletext_input::caps` defines bits 17 to 22; 23 and up are unused |
| Capability `NAPLPS_CAP` | bit 24 (`1 << 24`) | as above |
| Record types | **none new** | `DRAWING_LINKS` (15) and `REGIS_CURSOR` (16) are widened to name NAPLPS objects (PAR-2) |
| Input events | **none new** | NAPLPS object hover and picking are carried by `RULE_EVENT`'s target (RULE-46) |
| Push protocol version | stays **10** | every change is a capability bit (HELLO reads past unknown bits) or a widened meaning of an existing record (PAR-1, PAR-2) |
| Program protocol version | stays **15** | every change is a new message or optional field a program sends, or an answer only to a new request (section 8 introduction) |
| ReGIS alphabets of the provided sets | 100 to 154 | the VT340 has alphabets 0 to 3 (manual chapter 7, "Select Character Set"); the renderer ignores any other today |
| New program messages | `naplps_links`, `naplps_cursor`, `forget_picture`, `measure_picture_text` | `MessageType` lists none of these names |
| New server message | `measured_picture_text` | `ServerMessage` lists no such type |
| New refusal rules | `kept_over_limit`, `wrong_picture_language`, `not_kept`, `invalid_naplps`, `invalid_naplps_links`, `invalid_picture_parts` | `Rule` lists none of these names |

---

## 2. The engine: capability bits and the picture records (neoteletext-renderer-teletext)

**PAR-1 [engine: neoteletext-input]. Two capability bits for the picture languages.** (DEC-6638 row 3.7.)
- **Statement.** `neoteletext_input::caps` MUST define `REGIS_CAP: u32 = 1 << 23` ("the receiver draws a sub-page's ReGIS from the REGIS record, type 14, with `DRAWING_LINKS` and `REGIS_CURSOR`, as REQ-6341 and regis-v2.md say") and `NAPLPS_CAP: u32 = 1 << 24` ("the receiver draws a sub-page's NAPLPS from the NAPLPS record, type 17, with `NAPLPS_OBJECTS`, `DRAWING_LINKS` and `REGIS_CURSOR` for its objects, on the teletext raster of REQ-5819"), and `ALL_CAPS` MUST include both. A receiver MUST offer a bit in HELLO only when it draws that language; a server MUST agree in WELCOME only bits it was offered and knows (the existing rule of `session.rs`: offered `& ALL_CAPS`).
- **Compatibility, exactly.** HELLO's reader refuses only the retired page bit (`event/decode.rs`, `read_hello`), so a server built before these bits reads a HELLO that offers them and agrees neither. WELCOME's reader refuses bits outside `ALL_CAPS` (`control.rs`), but a server agrees only what was offered, so a receiver built before these bits, which offers neither, is never sent one. No version is raised. The one change of behaviour is the server's (PAR-24): a receiver that does not offer a bit is given the mosaic fallback for that language, so a browser built before this work shows mosaics in place of pictures until it is updated; it shows something, which is better than a version change that would refuse it whole.
- **Verification.** Tests: HELLO with each bit round-trips; WELCOME agreeing each round-trips; a WELCOME agreeing bit 25 is refused; `ALL_CAPS` holds both and no retired bit (the existing assertion). The wire vectors (PAR-44).

**PAR-2 [engine: neoteletext-web, neoteletext-audio]. `DRAWING_LINKS` and `REGIS_CURSOR` name a NAPLPS object as well as a ReGIS drawing.** (DEC-6638 rows 1.2, 2.1, 2.2.)
- **Statement.** The meaning of the two records is widened, their bytes unchanged: `DRAWING_LINKS` (type 15; page, sub-code, part, parts, count, then each number `u16` and target, as `records/drawing_links.rs` documents) names the numbered drawings **or objects** of a sub-page's picture that are links, a number being a ReGIS numbered drawing when the sub-page's picture is ReGIS and a NAPLPS object (ANIM-11) when it is NAPLPS; `REGIS_CURSOR` (type 16; page, sub-code, number, 0 for none) names the drawing **or object** that is the sub-page's cursor. The documentation of both in `neoteletext-audio/src/record.rs`, `records/drawing_links.rs` and `records/regis_cursor.rs` MUST say so; the constants and the readers keep their names and their checks, so no code that reads them changes.
- **Compatibility, exactly.** The bytes are those of push protocol 10. A browser built before this work files both records by page and sub-code (`decoder/src/regis.rs`, `core/src/links/drawings.rs`): a cursor record for a NAPLPS sub-page finds no ReGIS picture and is dropped, and drawing links for a NAPLPS sub-page are matched against the NAPLPS pick record, whose numbers are object numbers, so they may already be followed. Neither does harm.
- **Verification.** Codec tests unchanged; a decoder test in the browser (PAR-27) that the same bytes reach the NAPLPS picture.

---

## 3. The engine: text in pictures (neoteletext-renderer-teletext)

The server writes a program's Unicode text into a picture (PAR-21), `neottx write-text` writes pages of it (PAR-10), and both measure it (PAR-22), with one encoder, which lives in the engine beside the teletext encoder it shares its tables with.

**PAR-3 [engine: neoteletext-formats, neoteletext-core]. The picture text encoder: Unicode to stretches of provided sets.** (DEC-6638 rows 5.2, 5.3; DEC-6669 items 1 and 5.)
- **Statement.** `neoteletext-formats` MUST gain a module `picture_text`, behind a feature `picture-text` (off by default), with `pub fn stretches(text: &str, language: Option<&str>, outside: bool) -> Result<Vec<Stretch>, PictureTextError>`. It takes a run's text in Unicode normalisation form C with no control or bidirectional formatting character, and its language (a BCP 47 tag of `neoteletext_core::charset::language::LANGUAGES`, none for Latin English), and returns the run in **visual order** as stretches, each `Stretch { set: u8, codes: Vec<u8>, marks: Vec<(usize, u8, u8)> }`: `set` is the set's number, 0 to 54, its place in the engine's `FONT_SETS` (`crates/neoteletext-core/src/glyphs/conformance.rs`, `FONT_SET_COUNT` 55); `codes` are its code positions 0x20 to 0x7F; `marks` lists, for a letter written with a diacritical mark the set has no precomposed glyph for, the index in `codes` of the letter, the G2 set's number and the mark's code in it. The choices are exactly those the teletext encoder makes for a run at Level `NeoTeletext` (`write_text::runs`, REQ-2214 item 5, TODO-2343, DEC-2473): the language's own set, and Latin English for what it cannot show; right-to-left runs reversed into visual order (`write_text::rtl`); the letters of Table 44 (EN 300 706 Table 44, the Arabic G0 set, set 18) in their joined forms (`write_text::table44`); the letters of the plain Arabic-script sets (group 1001, sets 44 to 51) in their base forms, which the picture renderers join (PAR-13, PAR-14), as the teletext renderer joins them (REQ-CHR-015). A character no set of the language or Latin English shows is refused (`PictureTextError::Unshown { index }`) unless `outside` is true, when it becomes the language's stand-in, as `TextRun::outside` does for teletext (DEC-2326). The function shares the tables of the teletext encoder by calling into them, never by copying them.
- **The joining data.** `neoteletext-core` MUST expose, for each code of a group 1001 set, its joining type (none, right-joining, dual-joining, transparent: Unicode's `ArabicShaping.txt` classes as REQ-CHR-015 uses them) and the glyphs of its isolated, final, initial and medial forms from the compiled Noto Teletext glyph table, as `neoteletext_core::glyphs::joining(set: u8, code: u8) -> Option<Joining>`. The browser, the server and `neottx` pass these to the picture renderers (PAR-13, PAR-14); the renderers link no engine crate.
- **Limits** (in `picture_text`): `MAX_PART_CHARACTERS = 1_000`, the characters of one run; `MAX_STRETCHES = MAX_PART_CHARACTERS`, asserted, since a stretch holds at least one character; `MAX_PICTURE_STREAM_BYTES = 1_048_576`, the most bytes of one picture's stream that a static channel file carries (PAR-8) or the server keeps (PAR-17), defined here because both the engine's tools and the server link this crate.
- **Verification.** Tests: a German run with `@` gives a German stretch and a Latin English one; a Hebrew run is reversed; an Arabic run of Table 44 gives the joined codes the teletext encoder gives on the same text; a Persian run gives base codes in set 44; a letter with a mark the set lacks yields the mark entry with G2-Latin (set 20); an unshown character is refused, and with `outside` becomes the stand-in; a run of `MAX_PART_CHARACTERS + 1` characters is refused.

**PAR-4 [engine: neoteletext-formats]. Stretches written as ReGIS.** (DEC-6638 rows 5.2, 5.3; DEC-6669 item 4.)
- **Statement.** `picture_text::regis(stretches: &[Stretch], out: &mut Vec<u8>)` MUST append, for each stretch in order: `T(A` the decimal alphabet `FIRST_PROVIDED_ALPHABET + set` (PAR-12; 100 to 154) `)`; then the codes as one or more quoted strings `"…"` of at most `regis::limits::MAX_STRING_BYTES` (1,024) bytes each, a `"` among the codes written twice (`""`, the manual's chapter 1 rule for a quote inside a quoted string); and, for each mark, after its letter, the string is closed, `T(A` the G2 set's alphabet `)` and `T(W(V))"` BS (0x08) and the mark's code `"` are written (BS moves back one character cell, the manual's chapter 7 "text control characters"; the temporary overlay write control `W(V)`, the manual's chapter 5, "Temporary Write Controls", with overlay writing as chapter 3 defines it, keeps the letter beneath the mark whatever writing mode is in force), and the stretch's alphabet is selected again before the next code. After the last stretch it MUST append `T(A0)`. A text part therefore leaves alphabet 0 selected and the text position after its last character; it changes no other text control, writing control or position. The bytes MUST be checked by the ReGIS renderer in the encoder's tests: drawn, they give the provided glyphs at the cells expected.
- **The code 0x7F** of a set (the block of the Latin sets) is never written: a stretch holding one is refused (`PictureTextError::Unwritable { index }`), since ReGIS strings carry 0x20 to 0x7E.
- **Limits.** `MAX_REGIS_BYTES_PER_CHARACTER = 32`, the most bytes one character's writing takes (`T(A154)` and a quoted character, 10 bytes; a mark, at most 19 more; asserted from those parts), and `MAX_REGIS_PART_BYTES = MAX_PART_CHARACTERS * MAX_REGIS_BYTES_PER_CHARACTER` (32,000), asserted.
- **Verification.** Byte-exact tests of a one-set run, a two-set run, a quote, a mark and a 1,500-byte stretch cut into two strings; the drawing test above for every one of the 55 sets.

**PAR-5 [engine: neoteletext-formats]. Stretches written as NAPLPS.** (DEC-6638 rows 5.2, 5.3; REQ-6668.)
- **Statement.** `picture_text::naplps(stretches: &[Stretch], out: &mut Vec<u8>)` MUST append, for each stretch: the 94-character designation of its set into G0 (ESC 2/8, then the supplement 2/1, 2/2 or 2/3 for set numbers 16 and up, then the final 3/(n mod 16), exactly REQ-6668's table; `naplps::teletext::designation_of`), then SI (0/15) to invoke G0 into the in-use table, then the codes. A code 7/15, unreachable in the 94-character form, is written by designating the set's 96-character form into G2 (ESC 2/14, the supplement, the final), SS2 (1/9) and the code, then designating the supplementary set back into G2 (ESC 2/10 7/12, ANSI X3.110-1983 section 4.3.2 Table 1). A mark is written after its letter as APB (0/8, ACTIVE POSITION BACKWARD, of NAPLPS's C0 set, ANSI X3.110-1983 section 6.1.2.1), the G2 set's 96-character designation into G2, SS2 and the mark's code, then the supplementary set back into G2. After the last stretch it MUST append the designation of the primary set into G0 (ESC 2/8 4/2, Table 1). A text part therefore leaves G0 invoked in the in-use table holding the primary set, and G2 holding the supplementary set; a page that draws with PDIs after it sends SO again. In colour mode 2, where a character's field is filled with the background colour (SELECT COLOR's colour mode 2, ANSI X3.110-1983 section 5.3.2.6.3), a mark erases its letter: the kits' builders (PAR-39, PAR-40) never write text parts in colour mode 2, and the server's check (PAR-23) logs a mark written in it.
- **Limits.** `MAX_NAPLPS_BYTES_PER_CHARACTER = 32` (a designation of 4 bytes, SI and the code; a mark, at most 13 more; asserted), and `MAX_NAPLPS_PART_BYTES` = 32,000, asserted from its product.
- **Verification.** Byte-exact tests as PAR-4's; drawn by the NAPLPS renderer with the engine's sets, every set's codes give the provided glyphs.

**PAR-6 [engine: neoteletext-formats]. Measuring picture text.** (DEC-6638 row 5.4.)
- **Statement.** `picture_text::measure(stretches: &[Stretch]) -> Measured { cells: u32, regis_bytes: u32, naplps_bytes: u32, sets: Vec<u8>, stand_ins: u32 }` MUST give the character cells the run advances (a mark takes none: it is written over its letter), the bytes each encoding takes, the sets used in order of first use, and the characters that became stand-ins. Both picture languages space text by whole cells (ReGIS by the character display cell, the manual's chapter 7; NAPLPS by the character field of the TEXT instruction, ANSI X3.110-1983 sections 5.3.2.3.4 and 5.3.2.3.9, as REQ-6668 reads it), so the width of a run is `cells` times the cell width the program set, and the program needs nothing else to place it.
- **Verification.** Tests that `cells` and the byte counts equal the lengths `regis` and `naplps` produce and the advance the renderers draw.

---

## 4. The engine: `neottx` and the picture tools (neoteletext-renderer-teletext)

The engine's application crates link the two renderer crates, the project's own, pure Rust and without dependencies, approved by DEC-6579 (section 21 item 17). `neoteletext-formats` links them only under the feature `picture-text`, for their constants; the microcontroller builds never turn that feature on (REQ-GEN-017).

**PAR-7 [engine: neoteletext-cli, neoteletext-app]. `neottx` views, renders and checks pictures.** (DEC-6638 row 9.1.)
- **Statement.** `neottx render`, `view` and `show` MUST accept a ReGIS file (`.regis`, ReGIS commands with or without the device control string), a NAPLPS file (`.naplps` or `.nap`), and a `.t42` file or static channel page that carries `REGIS` or `NAPLPS` records (with `NAPLPS_OBJECTS`, `DRAWING_LINKS` and `REGIS_CURSOR` records) beside a sub-page. A picture is drawn as the browser draws it: ReGIS at 800 by 480 in its colour map; NAPLPS on the 480 by 500 teletext raster from line 19 (REQ-5819, DEC-6667), border lines in `Terminal::screen_colour`; NAPLPS objects composed (`compose`); text in the provided sets (the engine's compiled Noto Teletext glyphs, PAR-12, REQ-6668) with joining data (PAR-3); the ReGIS alphabet 0 font from `--regis-font FILE` or, by default, the VT340 font file the ReGIS renderer's repository ships (`fonts/vt340.regisfont`), compiled into `neottx`; the NAPLPS stroke font from `--naplps-font FILE` or the one `naplps-fonts` compiles. `neottx render` writes PNG, PPM or sixels as for teletext pages; `neottx view` shows the picture in the terminal or window it shows pages in, with the row 0 header and row 24 of the page beneath above and below it (PAR-31's layout). `neottx check` on a picture reports what the server's checks report (PAR-23; for ReGIS a failed commit with its code and drawing, for NAPLPS the renderer's `Diagnostics`), and exits non-zero on a refusal. `neottx` as a live receiver (`neoteletext-app`, the push connection) MUST offer `REGIS_CAP` and `NAPLPS_CAP` and draw the pictures it is sent.
- **Verification.** CLI tests rendering one file of each language and a `.t42` with each record kind against golden PNGs (a format version for them, DEVELOPMENT.md section 8); `check` exiting non-zero on a failing ReGIS commit and on a NAPLPS stream past `MAX_PROCESSED_BYTES`; a session test that HELLO offers both bits.

**PAR-8 [engine: neoteletext-cli]. Static channels carry pictures; static HTML shows them.** (DEC-6638 rows 3.5, 11.2.)
- **Statement.** `neottx convert --to channel` MUST take, for a page and sub-code, `--regis FILE` or `--naplps FILE`, and `--objects FILE` (the JSON of the program protocol's `naplps_objects` without `type`, `connections`, `page` and `sub`), `--links FILE` (the JSON array of `regis_links`'s or `naplps_links`'s `links`), `--cursor N`, and write into that sub-page's file (`NNN.t42`, or `NNN/SSSS.t42` in a sub-page folder, DOC-1868) the sub-page's packets followed by its records as packets 4/31 on data channel 12 (DOC-1951): the stream as `REGIS` or `NAPLPS` records of generation 1 from offset 0 (cut as `records::regis` cuts a live stream), then `NAPLPS_OBJECTS`, `DRAWING_LINKS` and `REGIS_CURSOR`, each written by its encoder and checked by its reader. A picture file larger than `neoteletext_formats::picture_text::MAX_PICTURE_STREAM_BYTES` (1,048,576, PAR-3) is refused: the same constant bounds a stream the server keeps (PAR-17), so that a static picture is never larger than a live one may be. `neottx html` (REQ-1725) MUST draw a sub-page that carries a picture as PAR-7 draws it, as a PNG beside the page's HTML, with the picture's title (REQ-6644, REQ-6653) or the page's as its `alt` text, in place of the teletext page's picture.
- **Verification.** A round trip: convert a ReGIS and a NAPLPS picture into a channel folder, read the folder back with the engine's reader, and find the same bytes and records; `neottx html` on that folder writes the two PNGs equal to `neottx render`'s.

**PAR-9 [engine: neoteletext-picture, neoteletext-picture-cli]. The picture converter makes ReGIS and NAPLPS.** (DEC-6638 row 9.2.)
- **Statement.** `neoteletext-picture` MUST gain `convert_raster(raster: Raster, options: &Options) -> Result<Page, Error>` (the existing path after `decode`, for a picture already in pixels; PAR-25 uses it), and `to_regis(bytes: &[u8], options: &PictureOptions) -> Result<Vec<u8>, Error>` and `to_naplps(bytes: &[u8], options: &PictureOptions) -> Result<Vec<u8>, Error>`. Each decodes within the existing bounds (`MAX_INPUT_BYTES`, `MAX_SIDE`, `MAX_DECODE_BYTES`), fits the picture to the language's canvas (ReGIS 800 by 480 square pixels; NAPLPS 480 by 462 dots of the raster, whose pixel is 16/13 as wide as it is high, DEC-2049) with the existing `Fit` choices, reduces it to the language's colours (ReGIS: 16 colour-map entries, set by `S(M…)` in the RGB form of the manual's chapter 2, "RGB System"; NAPLPS: 16 entries of colour mode 1, set by the SET COLOR instruction of ANSI X3.110-1983 section 5.3.2.5) by the existing quantiser, then writes regions: each row's runs of one colour, merged downwards with the run beneath of the same colour and extent into rectangles, each rectangle one filled shape (ReGIS a polygon fill, `F(V…)`, the manual's chapter 11; NAPLPS the RECTANGLE (FILLED) picture description instruction of ANSI X3.110-1983 section 5.3.3.4). The ReGIS output is then shortened by the ReGIS renderer repository's minifier library (`regis-minify`, which checks its result by rendering), the NAPLPS output is checked by drawing it with the NAPLPS renderer; each output MUST draw, within the colour reduction, the picture fitted. `PictureOptions` adds `colours` (2 to 16) to the existing options. Output over `MAX_PICTURE_OUTPUT_BYTES = 262_144` is an `Error::TooLarge`. `neottx-picture` (the CLI) MUST take `--to regis` and `--to naplps`; the browser's Tools menu (`decoder/src/picture.rs`) offers the same two outputs (PAR-36).
- **Verification.** Tests: a picture of four coloured quarters gives exactly four rectangles in each language and draws back to the same pixels; a photograph's output is within `MAX_PICTURE_OUTPUT_BYTES` and draws with a mean squared error recorded as a measured baseline; `convert_raster` on a raster equals `convert` on its PNG.

**PAR-10 [engine: neoteletext-cli]. Writing pages from text makes ReGIS and NAPLPS pages.** (DEC-6638 row 9.4.)
- **Statement.** `neottx write-text` (REQ-95, E.82) MUST take `--picture regis` or `--picture naplps` and write a picture file (and, with `--to channel`, a static channel sub-page as PAR-8) that lays the text out on the cell grid of PAR-42: 40 columns and the 23 rows 1 to 23, each line wrapped as the teletext writer wraps it, each line written as a text part (PAR-4, PAR-5) at its row's place, with `--language` as for teletext. ReGIS: the screen erased, character display cell 20 by 20 pixels and unit cell 16 by 20 (`T(S[20,20])` and `T(U[16,20])`; the teletext cell's 12 dots at their 16/13 shape on a 20-pixel row are 15 wide (DEC-2049), and a unit cell's width is a multiple of 8, a width between two being drawn at "the next smaller size" (VT330/VT340 Programmer Reference Manual, volume 2, chapter 7, "Unit Cell Size"), so 16 is the multiple nearest to 15 and no narrower, DEC-6818), row `r` at `P[0,10+20×(r−1)]`. NAPLPS: clear screen, the field 1/40 of the unit screen wide and 20 raster lines high (20/462 of the display's 25/32 unit height, at a three-byte multi-value operand's precision), row `r`'s text written from the unit-screen point on the row's last raster line, 20 × `r` + 19 (`naplps::design_point`'s inverse): a character field's origin is its lower left corner and the field lies up and to the right of the drawing point (ANSI X3.110-1983 section 5.3.2.3.2, Figure 17), so the field covers raster lines 20 × `r` to 20 × `r` + 19; written from line 20 × `r`, it would land on the row above. A character the language cannot show is the stand-in, as `outside` text (PAR-3).
- **Verification.** Tests: a German, a Russian, a Hebrew and an Arabic text each render to the cells expected in both languages; a line longer than 40 cells wraps.

**PAR-11 [engine: neoteletext-image or neoteletext-picture]. The raster a server converts.** (DEC-6638 row 3.7.)
- **Statement.** The server's fallback (PAR-25) MUST be able to turn a picture's indexed pixels and colour map into a teletext page of Level 1 mosaics without decoding a file: `convert_raster` of PAR-9 with `Level::One`, `Fit::Contain`, the picture placed in rows 1 to 23 (80 by 69 sixels), and nothing on rows 0 and 24. `neoteletext-picture`'s image decoders MUST be behind a default feature `decode`, so that the server links the converter without them (they are pure Rust, but the server's build for the Cloudflare host is size-bounded).
- **Verification.** A build of `neoteletext-picture` with `default-features = false` succeeds and passes `convert_raster`'s tests.

---

## 5. The ReGIS renderer: the provided character sets (neoteletext-renderer-regis)

**PAR-12 [neoteletext-renderer-regis]. A ReGIS page selects a provided set as an alphabet.** (DEC-6638 row 5.1; DEC-6669 item 4.)
- **Statement.** ReGIS's own means of selecting a character set is the text command's alphabet option, `T(A<n>)` (the manual's chapter 7, "Select Character Set"), which the VT340 defines for alphabets 0 (built in) to 3 (loadable, chapter 8). NeoTeletext's ReGIS v2 MUST give the 55 provided sets (DEC-6669 item 1) as alphabets `FIRST_PROVIDED_ALPHABET` (100) to 154, alphabet `100 + n` being set `n` of the engine's `FONT_SETS`, in the order REQ-6668's table gives. In a provided alphabet a string's byte 0x20 to 0x7E draws the set's position `byte − 0x20`; any other byte that is not a text control character draws the empty character cell and advances. The glyphs are data the caller passes (the renderer compiles no font, DEC-6346): `regis::ProvidedSet`, one glyph for each of the 96 positions, each at most `MAX_PROVIDED_GLYPH_WIDTH` (16) by `MAX_PROVIDED_GLYPH_HEIGHT` (32) pixels, given with `Terminal::set_provided_set(number: u8, set: ProvidedSet) -> Result<(), Error>` for a number below `PROVIDED_SETS` (55). A glyph is scaled into the character's unit cell by the rule the renderer uses for its built-in strikes, each unit pixel taking the glyph pixel nearest the middle of its share of the cell, under every text option (size, direction, italic, the writing mode), exactly as a built-in character. An alphabet from 4 to 99 or past 154 is ignored, as today. The load command (`L`) MUST refuse to load into a provided alphabet; DEC-6295's exception is not widened (DEC-6669 item 4). A provided set whose glyphs the caller did not give draws empty cells. regis-v2.md MUST state this, with the alphabet table, and `regis-minify` MUST keep every alphabet selection it finds.
- **Constants** (`regis::limits`): `FIRST_PROVIDED_ALPHABET = 100`, `PROVIDED_SETS = 55`, `PROVIDED_SET_POSITIONS = 96`, `MAX_PROVIDED_GLYPH_WIDTH = 16`, `MAX_PROVIDED_GLYPH_HEIGHT = 32`. A test in each linking caller (the server, the browser, `neottx`) asserts `PROVIDED_SETS == neoteletext_core::...::FONT_SET_COUNT`.
- **Compatibility.** A page that selects alphabet 100 and is drawn by a renderer built before this work keeps its alphabet in force (an unknown alphabet is ignored, `machine/text.rs`), and draws its codes in that alphabet: wrong letters, nothing worse. The server's fallback and the capability bit cover receivers that are not the browser.
- **Verification.** Tests: for each of the 55 alphabets, every code draws the given glyph scaled into the default cell; `L(A100)` is refused; alphabet 155 is ignored; a quoted `""` draws one quote; `regis-render --teletext DIR` (as `naplps-render --teletext`, REQ-6668) draws them from the engine's checkout, ignored with its reason when the checkout is absent.

**PAR-13 [neoteletext-renderer-regis]. Joined Arabic letters in the plain Arabic-script sets.** (DEC-6638 row 5.3; REQ-CHR-015.)
- **Statement.** For a provided alphabet whose set the caller marks as joined (sets 44 to 51, group 1001), the renderer MUST draw each letter of a string in the form its neighbours in that string give it, by the rule the teletext renderer applies (REQ-CHR-015), stated here for text in visual order, where the letter that follows a letter in reading is the one on its left: a letter **joins leftwards** when it is dual-joining and the nearest non-transparent code on its left is dual-joining or right-joining; it **joins rightwards** when the nearest non-transparent code on its right is dual-joining (and itself is dual- or right-joining); a letter that joins both ways takes its medial form, leftwards only its initial form, rightwards only its final form, and neither its isolated form (the set's own glyph); a transparent code (a mark) takes no part and keeps its own glyph. The forms are the caller's glyphs. The caller passes, with the set, `ProvidedSet::joining`: for each position its joining type and its final, initial and medial glyphs (PAR-3's `joining` data). Joining stops at the end of a string, at a change of alphabet and at a text control character.
- **Verification.** Tests: a Persian word in set 44 draws the same glyph sequence the teletext renderer draws for the same codes; a string cut by an alphabet change does not join across it.

---

## 6. The NAPLPS renderer: joining and a check without a canvas (neoteletext-renderer-naplps)

**PAR-14 [neoteletext-renderer-naplps]. Joined Arabic letters in the plain Arabic-script sets.** (DEC-6638 row 5.3; TODO-6680; REQ-CHR-015.)
- **Statement.** As PAR-13, for NAPLPS: `BitmapSet` gains the joining data (each position's joining type and three further glyphs), given by the caller for sets 44 to 51, and the renderer draws each letter of a run of characters of that set in its joined form, deciding by the characters on either side in visual order as REQ-CHR-015 does, a run ending at a control code, a change of the in-use table's set, or a PDI. This closes TODO-6680.
- **Verification.** As PAR-13's tests, in NAPLPS.

**PAR-15 [neoteletext-renderer-naplps]. `naplps::Validator`: the receiver's reading of a stream without drawing it.** (DEC-6638 rows 8.3, 10.4.)
- **Statement.** The library MUST provide `Validator::new()`, `feed(&mut self, bytes: &[u8]) -> Vec<Event>`, `diagnostics(&self) -> &Diagnostics` and `defined_macros(&self) -> [bool; 96]`, which read a stream exactly as `Terminal::feed` reads it (the same parser, the same definitions of macros, DRCS and textures, the same processed-byte count and refusals, `MAX_PROCESSED_BYTES`) but keep no canvas and draw nothing, so that a server can check many streams at a memory cost independent of the picture's size. Its memory MUST be bounded by the definitions' own limits (`MAX_ALL_MACRO_BYTES` and the DRCS and texture bounds) and a fixed state, stated as a measured figure in its documentation. A test MUST show that for any input the `Diagnostics` of `Validator` and of `Terminal` are equal.
- **Verification.** The equality test as a property test over random input (the crate's existing random-input generator); a stream past `MAX_PROCESSED_BYTES` reports `Refusal::ProcessingLimit` in both.

---

## 7. The server: picture streams kept per page (neoteletext-app-server)

**Why the program protocol stays at version 15.** The server reads a program's messages and refuses what it does not know (each message is `additionalProperties: false`, an unknown type is refused). Every change of sections 7 to 10 is a new message a program sends, a new value of a field a program sends, or an optional field a program sends; and the one new server message, `measured_picture_text`, and the new refusal rules and `MessageType` values in `refused`, are sent only in answer to those new messages. A program built for protocol 15 before this work never sends any of them, so it never receives anything new, and its kit's readers meet nothing they do not know. A program that uses them needs a server built after this work; the kits' releases that add the calls name that server commit, as they do today. `start.protocol` stays 15.

**PAR-16 [server]. The audience `"kept"`.** (DEC-6638 rows 3.3, 3.4.)
- **Statement.** The messages `regis`, `regis_links`, `regis_cursor`, `naplps`, `naplps_objects`, `naplps_links` and `naplps_cursor` MUST take, in `connections`, the schema's `PictureAudience`: what `Connections` takes, or the string `"kept"`. `"kept"` means: the server keeps this for the page and sub-code named, sends it now to every open connection whose selection is that page and sub-code, and sends it to every connection that selects it later, for as long as it is kept. Every other message refuses `"kept"` by the schema. `sub` `3F7F` is refused (`out_of_range`), as today.
- **What is kept, for one page and sub-code** (a "kept picture"): its language (ReGIS or NAPLPS); its stream, every byte since its last `restart`, in order; for NAPLPS its objects (the last whole set, with each later `one` redefinition applied to it, and its title); its links (the last `regis_links` or `naplps_links`); its cursor (the last `regis_cursor` or `naplps_cursor`). A kept `regis` or `naplps` without `restart` appends to the kept stream; one with `restart` replaces it (a new kept generation) and keeps nothing else of before; a kept stream of one language given a message of the other without `restart` is refused (`wrong_picture_language`), and with `restart` replaces it.
- **Checks.** A kept ReGIS stream is checked by one `regis::Validator` held with it, as a connection's is today (REQ-6332); a kept NAPLPS stream by one `naplps::Validator` (PAR-15, PAR-23). A message whose bytes the check refuses is refused whole and nothing of it is kept or sent.
- **Verification.** Schema tests: `"kept"` accepted by the seven and refused by `page`; tests of each refusal.

**PAR-17 [server]. The bounds of what is kept.** (DEC-6638 rows 3.3, 3.4.)
- **Statement.** The server MUST hold kept pictures to these constants of `teletext-runtime` (a new module `kept.rs`), and refuse whole, with the rule `kept_over_limit` and a `detail` naming the constant and its value, a message that would pass one:

| Constant | Value | Limit |
|---|---|---|
| `MOST_KEPT_STREAM_BYTES` | `neoteletext_formats::picture_text::MAX_PICTURE_STREAM_BYTES` (1,048,576), by name | The bytes of one kept stream since its restart |
| `MOST_KEPT_PICTURES` | 512 | Pages and sub-codes with a kept picture, for one channel |
| `MOST_KEPT_COST` | 33,554,432 | The cost of all of a channel's kept pictures: each stream's bytes counted twice (the bytes and its validator's copy of what it holds, which is at most the bytes), plus each companion's message bytes as received |

A kept picture is never dropped to make room: a program that needs room sends `forget_picture` (PAR-19). The kept pictures are dropped when the program ends or restarts (the server tells the program `start` again and keeps nothing across it), and when the channel's host drops its state (the Cloudflare host's hibernation, as for every other thing the server holds).
- **Reason.** Refusal names the limit to the program; silent eviction would leave late viewers without a picture and no one told. One megabyte a sub-page covers every demonstration picture measured (the largest regisdemo page is under 64 KB); 32 MB is a quarter of the Cloudflare host's 128 MB of memory for one channel.
- **Verification.** For each constant, a message reaching it exactly is kept and one byte or one picture more is refused naming it; a test that the cost counts twice the stream.

**PAR-18 [server]. Late and reconnected viewers, and page content against local state.** (DEC-6638 rows 3.3, 3.4; DEC-6587 item 3; DEC-6599.)
- **Statement.** When a connection's selection becomes a page and sub-code that has a kept picture, the server MUST send it, right after the frame of the `page` message that answers that selection, in this order: the stream as records of a new generation of that connection's stream of the language (its next `regis_generation` or `naplps_generation`) from offset 0; for NAPLPS the objects with their title as one `NAPLPS_OBJECTS` of that generation; the links as `DRAWING_LINKS`; the cursor as `REGIS_CURSOR`. Each later kept message reaches every connection showing it as the records of that same generation, appended. A connection whose stream of that page and sub-code was begun by a message naming connections (not `"kept"`) does not take kept appends until it selects the page again. A connection that does not have the language's capability bit is given the fallback instead (PAR-24).
- **Reconnection.** A connection that ends loses everything at the receiver (RULE-111, DEC-6587 item 3), and a reconnection is a new connection with a selection: it receives the kept picture from its beginning, as any late viewer does. Nothing of the old connection is replayed.
- **Squared with DEC-6587 item 3.** That decision drops a page's **local state** at a disconnect: its rule table's state, groups, sequences, variables, timers, animation state and local sounds, which exist only at the receiver. A kept picture is **page content**, what the program gave the page to show, of the same kind as the teletext rows the kit keeps for `publish` and sends at every selection. Keeping it is keeping what the page is, not what a viewer did to it: animation commands (`animate`, timelines, `frame`), the pointer's looks and the rule table's state are not kept and are never sent to a late viewer; a kept NAPLPS object is sent as its definition says (shown or hidden, its frame 0), and whatever the page's rule table or the program then does to it starts afresh, as the page's `open` trigger does.
- **Verification.** Tests with two connections: one selects before the picture is kept and receives it as it is sent; one selects after and receives the whole stream, objects, links and cursor in that order, then the appends; a connection that closes and opens again receives the stream from offset 0 of a new generation; a connection given a per-connection `regis` restart takes no kept appends; nothing of `animate` is sent to a late viewer.

**PAR-19 [server]. `forget_picture`.** (DEC-6638 rows 3.3, 3.4.)
- **Statement.** A program MUST be able to send `{"type":"forget_picture","page":"200","sub":"0001"}`: the kept picture of that page and sub-code is dropped, and every connection that was taking it is sent a restart of its stream with no bytes (an empty picture, the records of a new generation with no bytes), its objects, links and cursor gone with it. A `forget_picture` of a page and sub-code with nothing kept is refused (`not_kept`).
- **Verification.** Tests of both.

---

## 8. The server: NAPLPS links and cursor, text in pictures, measuring (neoteletext-app-server)

**PAR-20 [server]. `naplps_links` and `naplps_cursor`.** (DEC-6638 rows 1.2, 2.1, 2.2.)
- **Statement.** The program protocol MUST gain `{"type":"naplps_links","connections":…,"page":…,"sub":…,"links":[{"object":7,"target":"200"},…]}` (0 to 64 links, the existing `MAX_REGIS_LINKS`, each object 1 to 65,535 named once, each target as `DrawingLink.target`) and `{"type":"naplps_cursor","connections":…,"page":…,"sub":…,"object":7}` (0 for none). The server MUST write them as `DRAWING_LINKS` and `REGIS_CURSOR` records (PAR-2), exactly as `regis_links` and `regis_cursor` are written, and refuse a target the TTI reader's parser refuses (`invalid_naplps_links`). A link or a cursor may name an object not yet defined; the receiver uses it once the object exists. The same messages, without `connections`, are commands a rule table's group may hold (RULE-35's list gains them), since a group's command is the message a program would send (DEC-6587).
- **Verification.** Encoding tests against the engine's readers; refusal tests; a group holding `naplps_cursor` accepted.

**PAR-21 [server]. Text parts in `regis` and `naplps`.** (DEC-6638 rows 5.2, 5.3; DEC-6669.)
- **Statement.** `regis` and `naplps` MUST take, in place of `data`, `parts`: an array of 1 to `MOST_PICTURE_PARTS` (64) objects, each either `{"data": Base64}` (bytes as `data` takes them) or `{"text": "…", "language": LanguageTag | null, "outside": false}` (1 to `MAX_PART_CHARACTERS` characters in Unicode normalisation form C, no control or bidirectional formatting character; `language` a tag of `start.languages`, none for Latin English; `outside` as `TextRun.outside`). Exactly one of `data` and `parts` is given (`missing_field`, `duplicate_field`). The server encodes each text part with the engine's encoder (PAR-3 with PAR-4 or PAR-5), joins the parts in order into the message's bytes, and then treats them exactly as `data`: checked, kept when the audience is `"kept"`, sent as records. A character the language cannot show refuses the message with `text_unshown` and the part's path (`parts[3].text`), unless `outside`, when it is the stand-in and the author's log says so, as for teletext text runs (DEC-2326). Faults of a part's text use the existing rules (`not_nfc`, `forbidden_character`, `unknown_language`, `too_long`); a parts array outside its bounds is `invalid_picture_parts`.
- **Verification.** Tests: a part in each of the 55 sets' languages encodes to the bytes PAR-4 and PAR-5 give; Arabic and Hebrew; a mark; `outside`; each refusal with its path.

**PAR-22 [server]. `measure_picture_text`.** (DEC-6638 row 5.4.)
- **Statement.** A program MUST be able to send `{"type":"measure_picture_text","request":17,"text":"…","language":"ar","outside":false}`, and the server MUST answer `{"type":"measured_picture_text","request":17,"cells":12,"regis_bytes":96,"naplps_bytes":40,"sets":["G0-Arabic"],"stand_ins":0}` from PAR-6, `sets` naming each set used by its `FONT_SETS` name in order of first use. A text the language cannot show without `outside` is refused (`text_unshown`) with `request` carried, as `measure`'s refusals are (REQ-2216 item 3). It sends nothing to any viewer.
- **Verification.** Tests of an answer and a refusal; the figures equal the encoder's.

**PAR-23 [server]. The server checks NAPLPS with the receiver's renderer and tells the author.** (DEC-6638 rows 8.3, 10.4.)
- **Statement.** The server MUST read every `naplps` message's bytes, per connection or kept, with a `naplps::Validator` (PAR-15) of that stream, as it reads ReGIS with `regis::Validator` (REQ-6332): a message whose bytes make the validator record any `Refusal` (the processed-byte limit, a macro too long, the macros full, a PDI too long) is refused whole (`invalid_naplps`), with `detail` naming the refusal by `Refusal::name` and the stream offset of the first. Bytes passed over (`Diagnostics::passed_over`) are not refused: the server writes one `author_log` line for the message naming how many and the first offset. A `naplps_objects` whose frames or looks name a macro the stream has not defined is not refused (the macro may come later) and is logged once a generation. A text part's mark written while colour mode 2 is in force is logged (PAR-5). A per-connection stream's validator lives while the connection's stream does; its memory is PAR-15's.
- **Verification.** Tests: a stream past `MAX_PROCESSED_BYTES` refused naming the limit; a null-set byte logged and sent; an undefined macro in an object logged once.

---

## 9. The server: capability and the mosaic fallback (neoteletext-app-server)

**PAR-24 [server]. Pictures go only to connections that agreed their language.** (DEC-6638 row 3.7.)
- **Statement.** The server MUST agree `REGIS_CAP` and `NAPLPS_CAP` in WELCOME when offered (PAR-1). To a connection that has not agreed a language's bit, the server MUST send none of that language's records (its stream records; for NAPLPS `NAPLPS_OBJECTS`; `DRAWING_LINKS` and `REGIS_CURSOR` of its sub-pages), and MUST give it the fallback of PAR-25 for every sub-page it shows that has a picture of that language, kept or sent to it. Rule tables, sounds and every other record go as today.
- **Verification.** Tests with a connection offering neither bit, ReGIS only and NAPLPS only, against kept and per-connection pictures of each language.

**PAR-25 [server]. The mosaic fallback.** (DEC-6638 row 3.7.)
- **Statement.** For a connection without a picture's capability, the server MUST draw the picture with the same renderer the browser uses and the same fonts (ReGIS: `regis::Terminal` on an 800 by 480 `Screen`, the VT340 alphabet 0 font from the ReGIS repository, the provided sets from the engine's compiled Noto Teletext glyphs; NAPLPS: `naplps::Terminal` on the 480 by 462 canvas, the stroke font of `naplps-fonts`, the 55 sets as `animation.rs`'s `naplps_receiver` gives them, its objects composed), turn it into RGB by its colour map, and convert it with `neoteletext_picture::convert_raster` (PAR-11) into Level 1 mosaics on rows 1 to 23. The connection is sent the sub-page as the program gave it with rows 1 to 23 replaced by the fallback's rows; rows 0 and 24 and everything else of the page are the program's. When the picture changes, the fallback is drawn again from the whole stream, at most once in `FALLBACK_INTERVAL_MS` (500) for one picture, the last change always drawn within that interval; a kept picture's fallback is drawn once and shared by every connection showing it. Fallback drawing for a channel is held to `MOST_FALLBACK_RENDERS_PER_SECOND` (20), sustained, over all its pictures: a fallback over the budget is drawn late, never wrong and never skipped. For a per-connection stream to such a connection the server keeps the stream's bytes (they are not sent), at most `MOST_KEPT_STREAM_BYTES` for one connection and `MOST_FALLBACK_POOL_BYTES` (16,777,216) for all of a channel's connections together; a stream past either is dropped for that connection, its fallback shows what it had, and the author's log says which bound was passed.
- **Verification.** Tests: a ReGIS picture of a red rectangle on black gives red mosaics where it lies on rows 1 to 23 and the program's rows 0 and 24 unchanged; a NAPLPS picture likewise; twenty changes within 500 ms draw at most two fallbacks and the last state; a kept picture with 100 connections without the bit is drawn once; the pool bound.

---

## 10. The server: public pages with pictures (neoteletext-app-server)

**PAR-26 [server]. `description.picture`.** (DEC-6638 rows 11.1, 11.2.)
- **Statement.** `description` MUST take an optional `picture`, either `{"kept":"0001"}` (draw the kept picture of the described page with that sub-code) or `{"language":"regis"|"naplps","data":Base64,"objects":[NaplpsObject]|null}` (draw these bytes, at most `MOST_DESCRIPTION_PICTURE_BYTES` (262,144) decoded, with these NAPLPS objects for NAPLPS). When given, the server MUST draw the picture as PAR-25 draws it (the shown objects composed, no animation, no pointer look) and give it, as a PNG, as the page's picture in place of `content`'s drawing; `content` may still be given for the page beneath (its text for `text`). The PNG is at the language's own size, as the browser shows it: ReGIS 800 by 480; NAPLPS the 480 by 500 teletext raster with its border lines, the same raster and pixel shape as a teletext page's public picture, so the landing page shows it at the size it shows a teletext page. A PNG over the existing `MOST_PICTURE_BYTES` (64 KiB) is left out, as today. A `kept` naming nothing kept, or a picture whose check fails (PAR-16, PAR-23), refuses the description (`not_kept`, `invalid_regis`, `invalid_naplps`).
- **Verification.** Tests: a described ReGIS picture gives the PNG the server's renderer draws; a kept NAPLPS picture likewise; each refusal; the landing page's HTML for a picture page names the picture's title as `alt` when the program gives none.

---

## 11. The browser: interactivity on pictures (neoteletext-browser)

**PAR-27 [browser]. The NAPLPS cursor.** (DEC-6638 row 1.2.)
- **Statement.** A `REGIS_CURSOR` record (PAR-2) for a sub-page drawn in NAPLPS MUST make the named object that sub-page's cursor: the receiver shows and hides it in turn at the rate it blinks a ReGIS cursor (the decoder's existing period), through the object's animation state (`set_animation`), while the page's keys go to the channel, and shows it steadily when reduced motion is set (PAR-33). Number 0, or an object that does not exist, is no cursor. The decoder's NAPLPS page store (`decoder/src/naplps.rs`) holds it as the ReGIS store holds its own.
- **Verification.** Decoder tests: the object alternates at the period; 0 stops it; a later `NAPLPS_OBJECTS` without that object stops it.

**PAR-28 [browser]. Links on NAPLPS objects, and touch looks checked.** (DEC-6638 rows 2.1, 2.2, 1.9.)
- **Statement.** `DRAWING_LINKS` for a sub-page drawn in NAPLPS MUST make the named objects links, followed by the rules of every link (REQ-6376): the destination shown in the strip while the pointer is on the object, the dwell time, the question before leaving the channel. The decoder MUST read the record for NAPLPS sub-pages as for ReGIS ones (`read_links` keyed by page and sub-code whatever the language) and the trusted core MUST match it against the NAPLPS pick record. The hand pointer, hover and pressed looks and the touch rule (a finger presses and does not hover, DEC-2385) apply to NAPLPS objects exactly as to ReGIS drawings; their being seen on a real touch screen is a test run by hand, recorded with its date (DEVELOPMENT.md section 8).
- **Verification.** Trusted-core tests: a click on a linked object follows its link after the dwell time; the strip shows its destination; the hand over it. An ignored test naming the touch screen it needs, run by hand for ReGIS and NAPLPS.

**PAR-29 [browser]. Pointing at small targets when a picture is scaled down.** (DEC-6638 row 1.10.)
- **Statement.** When a picture is shown smaller than its own size, so that one screen pixel covers more than one picture pixel, the trusted core MUST decide what is under the pointer by looking at every picture pixel the screen pixel covers, up to `MAX_PICK_SPAN` (8) across and down (a picture shown at an eighth of its size or more; below that, the 8 by 8 block centred on the mapped pixel): the targets are every detectable drawing or object the pick record names at any of those pixels, and the one chosen is the one at the pixel nearest the block's centre, ties broken by the higher drawing order (the pick record's own order). At its own size or larger the block is one pixel and nothing changes. The PICK and the rule table's pointer pixel report the chosen pixel. `MAX_PICK_SPAN` is a constant of the trusted core's pointer module.
- **Verification.** Tests: a one-pixel-wide detectable drawing is hit with the picture shown at a third of its size; two drawings in one block resolve to the nearer the centre; at actual size the result is the existing one.

**PAR-30 [browser]. Keyboard reach and link marks on pictures.** (DEC-6638 rows 2.3, 6.3.)
- **Statement.** Tab and Shift-Tab MUST move the focus ring (`interface-core/src/browser/hyperlinks.rs`) through a picture's drawing or object links and its detectable drawings or objects, after the page's teletext links, in reading order of their bounds (top edge, then left edge, then number), each target once. The ring is drawn around the target's bounding rectangle (`Terminal::bounds`, carried with the pick record), in the picture's pixels scaled as the picture is. A focused link shows its destination in the strip at once and is followed by Enter under the same dwell rule as a pointer. A focused detectable drawing or object that is not a link is activated by Enter or Space as a press and a release at the centre of its rectangle, given to the page's rule table (RULE-12's targets) exactly as a pointer's would be, with no modifier. Links on pictures MUST be marked: a line two picture pixels high beneath each linked target's rectangle, in the colour teletext link underlines use, drawn by the receiver over the picture and following the setting that shows or hides teletext link marks.
- **Verification.** Interface tests: Tab order on a picture with three links and two detectable objects; Enter follows; Space on a non-link object fires the page's `press` rule with the centre pixel; the underline drawn under linked targets only.

---

## 12. The browser: presentation, fonts, kept pictures, static channels and the embedded back end (neoteletext-browser)

**PAR-31 [browser]. The header row and status area above a picture.** (DEC-6638 row 7.6; REQ-6626.)
- **Statement.** A picture MUST be shown with row 0 of the sub-page's teletext page above it, as row 24 is shown beneath it (REQ-6379): the receiver-owned status area (page number, the sub-page's place, the stale mark, the security indicators; DEC-1003, E.10, REQ-SEC-005) in its columns and the channel's header text and clock in the rest, at the scale row 24 is drawn at. For ReGIS the layout becomes row 0, the 800 by 480 picture, row 24. For NAPLPS, whose picture is the teletext raster (DEC-6667), row 0 is drawn on raster lines 0 to 19 and row 24 on lines 480 to 499, over the border lines and over the picture's first line (19) and last line (480), which they cover. The cost line drawn above a picture today (`interface-core/src/browser/regis_status.rs`) MUST move to the developer console's Stats tab (REQ-6626) if it has not already, so that nothing of the browser's own lies over the page's rows. The wall tile and the filmstrip show the same layout.
- **Verification.** Interface tests of both layouts' rectangles; a screenshot on a private display of a ReGIS and a NAPLPS page showing the header's clock and status area.

**PAR-32 [browser]. Hold applies to pictures.** (DEC-6638 row 7.8.)
- **Statement.** Hold (browser decision 67) MUST freeze a picture as it freezes a teletext page: while held, the picture shown is not replaced, though the decoder goes on reading the picture's records into its terminal so that its state stays the stream's; at release the latest picture is shown at once. Animation and the cursor do not move while held. Reveal, mix and zoom do not apply to pictures (DEC-6638 item 6) and their keys do nothing on a picture page.
- **Verification.** Tests: records arriving while held do not change the shown picture; release shows the latest.

**PAR-33 [browser]. Reduced motion stops receiver-side animation in every renderer.** (DEC-6638 row 6.2; REQ-754, DEC-2424.)
- **Statement.** With the reduced-motion setting on (REQ-754), the receiver MUST NOT move what only the receiver moves, while every state change the channel or the page's own rules make still applies: teletext flash shows its characters steadily in the on phase; a teletext, ReGIS or NAPLPS cursor shows steadily; NAPLPS BLINK shows its first colour steadily; NAPLPS WAIT is not waited for (the bytes after it are applied at once); a frame cycle (ANIM-14) shows its first frame and does not advance; the ReGIS paint rate (ANIM-15) draws at once. Rule tables, sequences, timers, the server's timelines and animation commands are state changes and apply as usual.
- **Verification.** Decoder tests for each item with the setting on and off.

**PAR-34 [browser]. Picture pages are kept like teletext pages.** (DEC-6638 row 3.6.)
- **Statement.** The decoder's page cache (`decoder/src/page_cache.rs`, `MAX_CACHED_PAGES` 128 entries, `CACHED_PAGE_LIFETIME_US` 24 hours) MUST keep picture sub-pages under the same rule as teletext ones, by keeping each picture's source (its stream's bytes and its objects, links and cursor records, as received) rather than a renderer, held to `MAX_KEPT_PICTURE_SOURCE_BYTES` (33,554,432) for a tab, the entry drawn longest ago dropped first. A kept picture shown again is drawn from its source into a new terminal at once, and replaced when the channel sends the picture again. The live terminals stay bounded by `MAX_REGIS_PAGES` and `MAX_NAPLPS_PAGES` (4), which now bound only what is open at once; the fixed four no longer bound what back and forward can show.
- **Verification.** Tests: twenty picture sub-pages visited are shown again from the cache without a fetch; a source over the budget drops the oldest; the cache's lifetime applies.

**PAR-35 [browser]. User-loadable fonts for pictures.** (DEC-6638 row 5.5.)
- **Statement.** The browser's settings MUST let the user choose a ReGIS font file (the text form `regis::Font::parse` reads, at most `regis::limits::MAX_FONT_BYTES`) for alphabet 0, and a NAPLPS stroke font file (the form `naplps::StrokeFont` reads, at most the NAPLPS renderer's bound for it, `MAX_STROKE_FONT_BYTES`, which the renderer adds as 1,048,576 if it has none), each replacing the font compiled in for every picture of that language, or going back to it. The trusted core reads the file and passes its bytes; the confined decoder parses it; a file that does not parse is refused with the parser's message and the font in force is kept. The provided sets are not replaceable (DEC-6669).
- **Verification.** Tests: a valid ReGIS font file changes the glyphs drawn; a malformed one is refused and changes nothing; one over the bound is refused before it is read whole.

**PAR-36 [browser]. Pictures from static channels; the picture converter's outputs; the capability bits; the provided sets and joining data.** (DEC-6638 rows 3.5, 3.7, 9.2, 5.1, 5.3.)
- **Statement.** (1) A static channel's fetched files that carry picture records (PAR-8) MUST be read and drawn as a live channel's: the fetcher passes the record packets to the decoder, which reads them by the same reader. (2) The Tools menu's picture converter (`decoder/src/picture.rs`) MUST offer ReGIS and NAPLPS outputs (PAR-9). (3) HELLO MUST offer `REGIS_CAP` and `NAPLPS_CAP` (PAR-1). (4) Every ReGIS terminal MUST be given the 55 provided sets (PAR-12) from the engine's compiled glyph table, and every ReGIS and NAPLPS terminal the joining data of sets 44 to 51 (PAR-13, PAR-14), as every NAPLPS terminal is given the sets today (TODO-6679).
- **Verification.** A fetcher test with a static folder holding a ReGIS and a NAPLPS sub-page; a decoder test that alphabet 117 (Greek) draws the engine's Greek glyphs; a session test of HELLO's bits.

**PAR-37 [browser: draw-embedded]. The embedded back end draws pictures.** (DEC-6638 row 7.10.)
- **Statement.** `draw-embedded` MUST draw a picture as it draws a page: `set_page` (or a new `set_picture`) takes the picture's language and so its size (`PictureLanguage::width` and `height`: 800 by 480, or the 480 by 500 raster), its colour map and its indices, and `page` draws it scaled into the rectangle given with the layout of PAR-31 (row 0 and row 24 being pages the core gives it). The second size is the one it lacks today.
- **Verification.** A test drawing a ReGIS and a NAPLPS picture onto an `embedded-graphics` mock display and comparing pixels.

---

## 13. The TypeScript kit (neoteletext-server-ts-protocol)

**PAR-38 [TypeScript kit]. The calls of sections 7 to 10.** (DEC-6638 rows 10.2, 3.3, 5.2 to 5.4, 11.1.)
- **Statement.** The kit MUST take the server's schema of the commit that builds sections 7 to 10 and give: `Audience` a fourth form `{ kept: true }`, accepted by `regis`, `regisLinks`, `regisCursor`, `naplps`, `naplpsObjects`, `naplpsLinks` and `naplpsCursor` only (a type error elsewhere); `naplpsLinks(to, page, sub, links: readonly { object: number; target: string }[])`; `naplpsCursor(to, page, sub, object: number)`; `forgetPicture(page, sub)`; `regis` and `naplps` taking `data: string | Uint8Array | readonly PicturePart[]`, a `PicturePart` being `Uint8Array | string` (bytes) or `{ text: string; language?: string; outside?: boolean }`; `measurePictureText(text, { language?, outside? }): Promise<{ cells, regisBytes, naplpsBytes, sets, standIns }>`; the description's `picture` (`{ kept: sub }` or `{ language, data, objects? }`); and the group commands `naplps_links` and `naplps_cursor`. The kit's `kit-calls.tsv` and documents list them.
- **Verification.** Tests of each call's message against the schema; `measurePictureText` against a fake server's answer.

**PAR-39 [TypeScript kit]. A ReGIS builder.** (DEC-6638 row 10.2.)
- **Statement.** The kit MUST give `class Regis`, whose methods append ReGIS commands and return the builder, and whose `parts()` returns the `PicturePart[]` for `regis`: `erase(background?)`, `colour(index, r, g, b)` (`S(M index(R…G…B…))`, its values 0 to 100 as the manual's chapter 2, "RGB System", gives them), `pen(index)` (`W(I index)`), `at(x, y)`, `line(x, y)`, `box(x, y, width, height, { fill?, pen? })`, `circle(x, y, radius, { fill? })`, `text(text, { language?, outside?, size? })` (a text part; `size` sets `T(S[w,h])` before it), `bytes(raw)`, `drawing(number, { detectable?, layer?, hover?, pressed?, label? }, build: (r: Regis) => void)` (regis-v2.md's numbered drawing with its attributes `H`, `A`, `U`, built by `build`), `commit()`, `title(text)` (`D(T'…')`). Every number is checked against the ReGIS renderer's limits by name (the kit's generated limits table) and a call outside one throws naming it.
- **Verification.** Tests that each method's bytes are the commands named; a builder's output passes the server's check in an end-to-end test.

**PAR-40 [TypeScript kit]. A NAPLPS builder.** (DEC-6638 row 10.2.)
- **Statement.** The kit MUST give `class Naplps` with `parts()` for `naplps`: `reset()`, `clear()`, `colour(index, r, g, b)` (SET COLOR in colour mode 1), `pen(index)`, `point(x, y)`, `line(x, y)`, `rect(x, y, width, height, { filled? })`, `polygon(points, { filled? })`, `text(text, { language?, outside? })` (a text part; the builder never leaves colour mode 2 in force before one, PAR-5), `bytes(raw)`, `defineMacro(code, build)` (DEF MACRO … END, the C1 macro controls of ANSI X3.110-1983 section 6.2.2.1, the 96 macro names of section 6.2), each coordinate given in the 640 by 480 design picture of ANIM-11 and written as the unit-screen operands at a fixed three-byte precision; and `object({...})` producing a `NaplpsObject` for `naplpsObjects`. Its documentation names the sections of ANSI X3.110-1983 each method writes.
- **Verification.** As PAR-39's, with the NAPLPS renderer.

---

## 14. The Python kit (neoteletext-server-channels)

**PAR-41 [Python kit]. The Python kit's picture calls.** (DEC-6638 row 10.3.)
- **Statement.** `neoteletext_app` MUST take the same schema and give: the hearer `kept_hears()` for the seven picture calls; `naplps_links`, `naplps_cursor`, `forget_picture`; `regis` and `naplps` taking parts (`bytes`, `str` for ReGIS bytes as today, or `PictureText(text, language=None, outside=False)`); `measure_picture_text`; `description` with `picture`; typed input events for `pick` and `drawing_hover`, and the rule event's `target` (`{"kind": "object", "number": n}`) on every `input`, so a program can tell which drawing or object a pointer event concerned; and the builders `Regis` and `Naplps` with the methods of PAR-39 and PAR-40 in Python's naming (`define_macro`). The existing `regis`, `regis_links`, `regis_cursor`, `naplps` and `naplps_objects` stay.
- **Verification.** The kit's tests for each call against the schema (`test_protocol15.py`), and the builders' bytes equal the TypeScript kit's for the same calls (a shared examples file, `picture-examples.jsonl`, read by both kits' tests).

---

## 15. The component library renders to pictures (neoteletext-server-ts-ui-components)

**PAR-42 [component library]. A page's renderer, and pictures drawn from the same components.** (DEC-6638 row 1.11; supersedes DEC-6366's exclusion.)
- **Statement.** A page spec MUST be able to name its renderer, `"teletext"` (the default, as today), `"regis"` or `"naplps"`, and every component MUST render to all three from the same element tree, with the same props, state, events and focus. The library MUST give a picture canvas for each language implementing the library's `Canvas` (`core/canvas.ts`) on the cell grid of the page's rows 1 to 23 and 40 columns, so that layout is unchanged:
  - **ReGIS** (PAR-42's grid): a cell is 20 by 20 picture pixels; row `r` is at `y = 10 + 20 × (r − 1)`, column `c` at `x = 20 × c`; the picture's top and bottom 10 pixels are the page's background. A component's cells are drawn as filled rectangles and text parts (PAR-21) with `T(S[20,20])` and `T(U[16,20])` (PAR-10's unit cell, a width the VT340 can make; DEC-6818); mosaic cells (`core/mosaics.ts`) as filled rectangles of their sixels (10 by 6⅔ pixels, drawn as 10 by 7, 7 and 6 rows from the top).
  - **NAPLPS** (PAR-42's grid): a cell is 12 by 20 dots of the raster; row `r` lies on raster lines `20r` to `20r + 19`, column `c` on dots `12c` to `12c + 11`; written in the design picture's coordinates by `naplps::design_point`'s mapping (across times 640/480, down from line 19 times 480/462), text in fields of PAR-10's size.
  - **Interactive components** become numbered drawings (ReGIS) or objects (NAPLPS: a macro object whose frame draws the component and whose hover and pressed looks draw its looks, ANIM-11) with the component's hover and pressed looks (`core/look.ts`), detectable when the component takes the pointer; links become `regis_links` or `naplps_links`; the focused text field's caret becomes the cursor (`regis_cursor` or `naplps_cursor`); the page's rule table (`core/page-rules.ts`) names drawings and objects by number (RULE-12 kind 2) in place of controls; every number is given by the library, stable across renders of the same element.
  - **Repainting.** A change of state repaints only the drawings or objects of the components that changed (a ReGIS drawing redefined and committed; a NAPLPS object redefined with `one`, REQ-6645), never the whole stream, so that the library's renders are deltas, as its teletext renders are rows that changed.
  - **Publishing** uses the audience `"kept"` (PAR-16) for the copy every viewer shares, and the existing per-connection audiences for a viewer's own mount.
- **Verification.** For each component of the library's catalogue, a test rendering it in each of the three renderers and checking the drawn picture against golden PNGs (the server's renderers drawn in the test, a format version for the goldens); tests that a click and a key on a picture page reach the same handlers as on the teletext page; a test that a state change sends only the changed drawings or objects. The component library's demonstration channel shows its catalogue in all three.

---

## 16. This repository: documentation items, wire vectors, the security analysis and the end-to-end check (neoteletext-common)

**PAR-43 [neoteletext-common]. The protocol's documentation items.** (DEC-2022.)
- **Statement.** rdm's documentation items MUST state, and `PROTOCOL.html` be generated with: the two capability bits (the capabilities item, DOC-1922); `DRAWING_LINKS` and `REGIS_CURSOR` naming NAPLPS objects (PAR-2); ReGIS's provided alphabets (PAR-12); the program messages and fields of sections 7 to 10, with the reason the program protocol stays 15; the fallback (PAR-25). Each item documents its PAR requirement's rdm record.
- **Verification.** Review at generation: every PAR requirement that defines a wire form or message has an item that documents it.

**PAR-44 [neoteletext-common]. Wire vectors.** 
- **Statement.** `wire-vectors.tsv` MUST gain: a HELLO offering `REGIS_CAP` and `NAPLPS_CAP`; a WELCOME agreeing them; a `DRAWING_LINKS` and a `REGIS_CURSOR` for a NAPLPS sub-page (the same bytes as for ReGIS, recorded so); a text part's ReGIS bytes and NAPLPS bytes for one Greek and one Arabic run (PAR-4, PAR-5). The engine's, the server's and the browser's wire vector tests read them.
- **Verification.** Each repository's wire-vector test passes with the new rows.

**PAR-45 [neoteletext-common]. The security analysis applied.** (DEC-6638 row 8.5; DEVELOPMENT.md sections 2.3 and 14.)
- **Statement.** The findings of section 19 MUST be applied in the requirements they name, and each repository's threat document updated (the engine's `THREAT-MODEL.md`, the browser's `docs/security-analysis.md`), the review recorded with its date.
- **Verification.** Review: each finding's mitigation is a requirement's text and a test.

**PAR-46 [neoteletext-common]. The end-to-end check and the comparison regenerated.** (TODO-6639 "How it is checked".)
- **Statement.** When every other PAR requirement is built, a run on a private display (the browser and a local server, as TODO-6679's check) MUST show: a NAPLPS page's cursor blinking, an object link followed by click and by keyboard; Tab through a ReGIS page's drawings; Arabic and Greek text parts in both languages; the header row above both; a kept picture reaching a second tab opened later; `neottx` (not offering the bits) showing the mosaic fallback; a public page's address answering with a picture; a component library page in each renderer. The comparison of 18 November 2026 MUST then be regenerated, every row reading built or not applicable.
- **Verification.** Screenshots kept in the browser's ignored `tmp/` and named in the to-do that closes this work; the regenerated comparison.

---

## 17. Limits stated in this document

Every limit below is defined once, in the crate named, and used by name everywhere else. None is a limit of the page rule table, so REQ-6608 is not changed: the rule table's own limits bound a group's `naplps_links` and `naplps_cursor` commands as they bound every command (`MAX_COMMAND_BYTES`).

| Constant | Value | Crate | PAR |
|---|---|---|---|
| `REGIS_CAP` | `1 << 23` | `neoteletext_input::caps` | PAR-1 |
| `NAPLPS_CAP` | `1 << 24` | `neoteletext_input::caps` | PAR-1 |
| `MAX_PART_CHARACTERS` | 1,000 | `neoteletext_formats::picture_text` | PAR-3 |
| `MAX_STRETCHES` | = `MAX_PART_CHARACTERS` | `neoteletext_formats::picture_text` | PAR-3 |
| `MAX_PICTURE_STREAM_BYTES` | 1,048,576 | `neoteletext_formats::picture_text` | PAR-3, PAR-8, PAR-17 |
| `MAX_REGIS_BYTES_PER_CHARACTER` | 32 | `neoteletext_formats::picture_text` | PAR-4 |
| `MAX_REGIS_PART_BYTES` | 32,000 (derived) | `neoteletext_formats::picture_text` | PAR-4 |
| `MAX_NAPLPS_BYTES_PER_CHARACTER` | 32 | `neoteletext_formats::picture_text` | PAR-5 |
| `MAX_NAPLPS_PART_BYTES` | 32,000 (derived) | `neoteletext_formats::picture_text` | PAR-5 |
| `MAX_PICTURE_OUTPUT_BYTES` | 262,144 | `neoteletext_picture` | PAR-9 |
| `FIRST_PROVIDED_ALPHABET` | 100 | `regis::limits` | PAR-12 |
| `PROVIDED_SETS` | 55 | `regis::limits` | PAR-12 |
| `PROVIDED_SET_POSITIONS` | 96 | `regis::limits` | PAR-12 |
| `MAX_PROVIDED_GLYPH_WIDTH` | 16 | `regis::limits` | PAR-12 |
| `MAX_PROVIDED_GLYPH_HEIGHT` | 32 | `regis::limits` | PAR-12 |
| `MOST_KEPT_STREAM_BYTES` | = `MAX_PICTURE_STREAM_BYTES` | `teletext_runtime::kept` | PAR-17 |
| `MOST_KEPT_PICTURES` | 512 | `teletext_runtime::kept` | PAR-17 |
| `MOST_KEPT_COST` | 33,554,432 | `teletext_runtime::kept` | PAR-17 |
| `MOST_PICTURE_PARTS` | 64 | `teletext_runtime::protocol` | PAR-21 |
| `FALLBACK_INTERVAL_MS` | 500 | `teletext_runtime::kept` | PAR-25 |
| `MOST_FALLBACK_RENDERS_PER_SECOND` | 20 | `teletext_runtime::kept` | PAR-25 |
| `MOST_FALLBACK_POOL_BYTES` | 16,777,216 | `teletext_runtime::kept` | PAR-25 |
| `MOST_DESCRIPTION_PICTURE_BYTES` | 262,144 | `teletext_runtime::descriptions` | PAR-26 |
| `MAX_PICK_SPAN` | 8 | the browser's trusted core, pointer module | PAR-29 |
| `MAX_KEPT_PICTURE_SOURCE_BYTES` | 33,554,432 | the browser's decoder, `page_cache.rs` | PAR-34 |
| `MAX_STROKE_FONT_BYTES` | 1,048,576 (if the crate has no bound) | `naplps::limits` | PAR-35 |

Existing constants used by name: `MAX_REGIS_LINKS` (64), `MAX_LABEL_BYTES` and `MAX_TITLE_BYTES` (64), `MAX_PROCESSED_BYTES` (4,000,000), `MAX_STRING_BYTES` (1,024), `MAX_FONT_BYTES` (1,048,576), `MOST_PICTURE_BYTES` (65,536), `MAX_CACHED_PAGES` (128), `MAX_REGIS_PAGES` and `MAX_NAPLPS_PAGES` (4).

---

## 18. Order of building

1. The renderers (sections 5 and 6) and the engine's PAR-1, PAR-2 and PAR-3 to PAR-6 may start at once; the engine's encoder tests need the renderers' branches for the drawing checks.
2. The engine's tools (section 4) after its encoder and the renderers are pinned.
3. The server (sections 7 to 10) after the engine's commit with PAR-1 to PAR-6 and PAR-11, and the renderers' commits, are pinned.
4. The browser (sections 11 and 12) after the engine's PAR-1 and PAR-3's joining data and the renderers' commits are pinned; its PAR-36 (1) after PAR-8.
5. The kits (sections 13 and 14) after the server's schema is committed.
6. The component library (section 15) after the TypeScript kit's release.
7. This repository (section 16) alongside, finishing with PAR-46.

---

## 19. Security analysis

What this work adds that reads outside input or holds memory for it, and what bounds it.

| # | Threat | Where | Mitigation (requirement) |
|---|---|---|---|
| 1 | A program fills the server's memory with kept pictures | server | Refused at `MOST_KEPT_STREAM_BYTES`, `MOST_KEPT_PICTURES` and `MOST_KEPT_COST`, never evicted silently (PAR-17) |
| 2 | A program makes the server render without end for fallbacks | server | One render a picture in `FALLBACK_INTERVAL_MS`, `MOST_FALLBACK_RENDERS_PER_SECOND` a channel, shared for kept pictures, each render bounded by the renderers' work caps (`WORK_CAP`, `MAX_PROCESSED_BYTES`) (PAR-25) |
| 3 | A program floods per-connection streams to connections without the capability, which the server must now keep | server | `MOST_KEPT_STREAM_BYTES` a connection and `MOST_FALLBACK_POOL_BYTES` a channel; past either the stream is dropped and logged (PAR-25) |
| 4 | Text parts expand into many bytes | server, engine | `MAX_PART_CHARACTERS`, `MOST_PICTURE_PARTS`, and the derived byte bounds asserted (PAR-3 to PAR-5, PAR-21) |
| 5 | A page carries its own letters for text | renderers | Only provided alphabets 100 to 154 and NAPLPS private designations of REQ-6668; `L` refuses a provided alphabet (PAR-12, DEC-6669) |
| 6 | A malicious ReGIS or NAPLPS stream crashes or stalls the server's check | server, renderers | The receiver's own bounded readers; `naplps::Validator` equal to `Terminal` by property test (PAR-15, PAR-23) |
| 7 | A user font file attacks the confined decoder | browser | Read by the trusted core within its byte bound, parsed in the confined decoder by the renderers' bounded parsers (PAR-35) |
| 8 | A picture's links mislead a viewer | browser | The same destination display, dwell time and question before leaving as teletext links (PAR-28, PAR-30) |
| 9 | Keyboard activation acts where the viewer did not point | browser | Only on the focused target, which the ring shows, and only a press and release a pointer could have made (PAR-30) |
| 10 | Public pictures cost the server rendering for crawlers | server | The existing description bounds (`DESCRIPTIONS_PER_SECOND`, the cache) apply to the picture's render; `MOST_DESCRIPTION_PICTURE_BYTES` bounds explicit bytes (PAR-26) |
| 11 | Static channel files carry oversized pictures | engine, browser | `MAX_PICTURE_STREAM_BYTES` when written; the browser's existing record and renderer bounds when read (PAR-8, PAR-36) |
| 12 | Kept content reaches a viewer who should not see it | server | A kept picture is content a program publishes to everyone who selects that page, as `publish` is; a program that wants a viewer's own picture names connections, as today (PAR-16) |

When this section was written no finding was left open. The review of the code as built, below, found three mitigations that do not hold in full; they are open security issues, each an rdm to-do in the repository that must fix it.

### 19.1 Review of the code as built, 19 November 2026 (PAR-45; DEVELOPMENT.md section 14)

Read against: the server's branch `parity` at ec189ce, the engine's branch `parity` at 42297736 (with its pins moved to 6efa8fef), the ReGIS renderer's branch `parity-2` at 9c1a162, the NAPLPS renderer's branch `parity-2` at 016a83c, and the browser's branch `parity` at 9732d46. The engine's `THREAT-MODEL.md` ("Renderer parity's threats", threats 4, 5 and 11) and the browser's `docs/security-analysis.md` (threats 7, 8, 9 and 11) record their own parts; both were read against the code and need no correction.

| # | Mitigation as built | Result |
|---|---|---|
| 1 | `teletext_runtime::kept` refuses at `MOST_KEPT_STREAM_BYTES`, `MOST_KEPT_PICTURES` and `MOST_KEPT_COST` with `kept_over_limit`, never evicting; tested at each bound | **Open (TODO-6836).** The cost counts a stream's reader as at most the stream's bytes, which is false for NAPLPS: `naplps::Validator` holds up to about 1.85 MB (its own documentation, measured at 1,761,280 bytes), most of it from DRCS and texture definitions of seven bytes each, so 512 kept NAPLPS pictures of about 700 bytes can hold some 820 MB against a counted cost under 1 MB. The list of appended message lengths (8 bytes a message) and the ReGIS reader's fixed state are not counted either, and nothing bounds the sum of per-connection readers (PAR-23) across a channel. |
| 2 | `channel/fallback.rs`: one drawing a picture in `FALLBACK_INTERVAL_MS`, `MOST_FALLBACK_RENDERS_PER_SECOND` a channel, one shared drawing for a kept picture; each drawing bounded by `WORK_CAP` and `MAX_PROCESSED_BYTES`; tested | Holds as stated. The worst time of one drawing of a 1 MiB stream is not measured, so what twenty a second cost a processor is not known (TODO-6839, a measurement owed). |
| 3 | `MOST_KEPT_STREAM_BYTES` a connection and `MOST_FALLBACK_POOL_BYTES` a channel for streams kept for the fallback, dropped with the author's log; tested | Holds. |
| 4 | `MAX_PART_CHARACTERS`, `MOST_PICTURE_PARTS` and the asserted `MAX_REGIS_PART_BYTES` and `MAX_NAPLPS_PART_BYTES` (engine and server); tested | Holds. |
| 5 | The encoder writes only the 55 provided sets; the ReGIS renderer's `L` refuses alphabets past 3 (test `the_load_command_refuses_a_provided_alphabet`); provided glyphs are bounded to 16 by 32 and set numbers below 55; random-input tests draw through the provided alphabets | Holds for ReGIS and for text parts. The row's wording is too strong for NAPLPS: a NAPLPS page MAY define its own characters with DEF DRCS, which the owner allows (the DRCS ban is the teletext renderer's, REQ-2196), bounded by the NAPLPS renderer's DRCS limits; that bound is part of finding 1. |
| 6 | The server reads every stream with the receiver's reader (`regis::Validator`, `naplps::Validator`) before sending or keeping it | **Open in part (TODO-6837, TODO-6838).** A refused append to a kept picture makes the server read the whole kept stream again (`KeptPicture::reread`), up to 1 MiB for a line of a few dozen bytes, with no rate bound. The NAPLPS validator's equality with `Terminal` is tested on fixed streams only; PAR-15's random-input property test does not exist. |
| 7 | The browser's broker reads a chosen font only within `MAX_REGIS_FONT_BYTES` or `MAX_NAPLPS_FONT_BYTES` (checked before reading), asserted equal to the renderers' bounds; a decoder started for it alone parses it | Holds. |
| 8 | NAPLPS object links go through the trusted core's `Links` with the destination shown, the dwell time and the question before leaving; tested | Holds. |
| 9 | The trusted core sends the interface only rectangles from its own pick record; Enter follows only the focused link by the click's checks; Enter or Space on a non-link is a press and release at its centre | Holds. |
| 10 | A description's picture is drawn only for an awaited `describe` (after the `not_awaited` check), within the description bounds; explicit bytes at most `MOST_DESCRIPTION_PICTURE_BYTES` | Holds. |
| 11 | `neottx convert` refuses a picture over `MAX_PICTURE_STREAM_BYTES`; the browser's fetcher takes a page file up to `MAX_PICTURED_PAGE_FILE` and passes it in pieces of one message (DEC-6817), no message bound raised | Holds. |
| 12 | `"kept"` is accepted only by the seven picture messages and `naplps_objects` (the schema's `PictureAudience`) | Holds. |

None of the open findings is in the ReGIS renderer, so none is written in that repository's `UNSOLVEDSECURITYISSUES/`.

---

## 20. Departures from earlier records

- **DEC-6638 row 1.6** asked for `DRAWING_HOVER` for objects; push protocol 10 carries every input inside `RULE_EVENT` with its target (RULE-46), which already names a NAPLPS object, so nothing new is sent (section 21 item 1).
- **REQ-6668** says a mark's composition with a letter "is not offered" for NAPLPS pages; the server's text parts compose a mark by writing it over its letter with APB (PAR-5), which is a way of writing a page, not a renderer feature, and leaves REQ-6668 true for what a renderer does.
- **TODO-6680** (NAPLPS joining) is closed by PAR-14.
- **DEC-6366's exclusion** of the component library is superseded, as DEC-6638 item 2 already says (PAR-42).
- **REQ-1473** says a connection that opens after a message was sent receives none of it unless the program sends it again, and **REQ-6533** that nothing of animation is kept for a later viewer. The audience `"kept"` (PAR-16) is the exception to the first, and a NAPLPS object's definition sent to it is page content kept as the stream is, while animation operations are still never kept. Both requirements are to be revised to say so, by the server's build (TODO-6777 step 9).

---

## 21. What this document decided without the owner

Recorded in rdm as one decision, for the owner's confirmation.

1. **No new record types or input events; push protocol stays 10.** `DRAWING_LINKS` and `REGIS_CURSOR` are widened to NAPLPS objects; NAPLPS hover and picking reach a channel through `RULE_EVENT`'s target.
2. **Capability bits 23 and 24**, and their absence means the mosaic fallback; browsers built before this work see mosaics until updated, rather than being refused by a version change.
3. **Program protocol stays 15**: every change is something a program sends, or an answer only to it.
4. **Kept pictures by an audience `"kept"`**, not by a separate publish message; refused, never evicted, at their bounds; a kept picture is page content, local state is never kept.
5. **The fallback** is drawn by the server at Level 1 into rows 1 to 23, rate-bounded, shared for kept pictures; per-connection streams to receivers without the bit are kept for it within a pool.
6. **ReGIS provided sets are alphabets 100 to 154**, selected by `T(A n)`, the VT340's own option, with glyphs from the caller.
7. **Text parts' encodings** as PAR-4 and PAR-5, each leaving a stated state; marks written over their letters (BS in ReGIS with a temporary overlay write control, APB in NAPLPS); Table 44 joined by the server, group 1001 joined by the renderers from data the caller passes.
8. **Measurement in cells and bytes**, since both picture languages space text by whole cells.
9. **Public pictures** by `{kept}` or explicit bytes, drawn at the language's own size.
10. **Keyboard reach**: Tab in reading order of bounds after teletext links; Enter or Space on a non-link as a press and release at the centre; link marks as a two-pixel underline following the teletext setting.
11. **Small targets**: every picture pixel under the screen pixel, up to 8 by 8, nearest the centre wins.
12. **The header row on the NAPLPS raster** covers the picture's first line, and row 24 its last.
13. **Hold freezes presentation, not reading**; **reduced motion** stops flash, blinks, WAIT, frame cycling and the paint rate while state changes apply.
14. **Picture pages kept as sources** within a byte budget, re-rendered on showing.
15. **The component library's grids**: ReGIS 20 by 20 cells with 10-pixel margins; NAPLPS the raster's own 12 by 20 cells.
16. **The converter's form**: colour-reduced rectangles, minified (ReGIS) or checked by drawing (NAPLPS).
17. **The engine's application crates and `neoteletext-formats` (feature `picture-text`) link the renderer crates** under DEC-6579; `neoteletext-picture`'s decoders go behind a default feature.
18. **REQ-6608 is unchanged**: no limit here is a rule table's.

## 22. The rdm records

| Record | Repository | What |
|---|---|---|
| DEC-6760 | neoteletext-common | Section 21's choices, for the owner's confirmation; decides every requirement below, as DEC-6638 does |
| REQ-6761 | neoteletext-renderer-teletext | Section 2: PAR-1, PAR-2 |
| REQ-6762 | neoteletext-renderer-teletext | Section 3: PAR-3 to PAR-6 |
| REQ-6763 | neoteletext-renderer-teletext | Section 4: PAR-7 to PAR-11 |
| REQ-6764 | neoteletext-renderer-regis | Section 5: PAR-12, PAR-13 |
| REQ-6765 | neoteletext-renderer-naplps | Section 6: PAR-14, PAR-15 |
| REQ-6766 | neoteletext-app-server | Section 7: PAR-16 to PAR-19 |
| REQ-6767 | neoteletext-app-server | Section 8: PAR-20 to PAR-23 |
| REQ-6769 | neoteletext-app-server | Section 9: PAR-24, PAR-25 |
| REQ-6768 | neoteletext-app-server | Section 10: PAR-26 |
| REQ-6770 | neoteletext-browser | Section 11: PAR-27 to PAR-30 |
| REQ-6771 | neoteletext-browser | Section 12: PAR-31 to PAR-37 |
| REQ-6772 | neoteletext-server-ts-protocol | Section 13: PAR-38 to PAR-40 |
| REQ-6773 | neoteletext-server-channels | Section 14: PAR-41 |
| REQ-6774 | neoteletext-server-ts-ui-components | Section 15: PAR-42 |
| REQ-6775 | neoteletext-common | Section 16: PAR-43 to PAR-46 |
| TODO-6776 | neoteletext-renderer-teletext | The engine's build |
| TODO-6777 | neoteletext-app-server | The server's build, with the revisions of REQ-1473 and REQ-6533 |
| TODO-6778 | neoteletext-browser | The browser's build |
| TODO-6779 | neoteletext-renderer-regis | The ReGIS renderer's build |
| TODO-6780 | neoteletext-renderer-naplps | The NAPLPS renderer's build, closing TODO-6680 |
| TODO-6781 | neoteletext-server-ts-protocol | The TypeScript kit's build |
| TODO-6782 | neoteletext-server-channels | The Python kit's build |
| TODO-6783 | neoteletext-server-ts-ui-components | The component library's build |
| TODO-6784 | neoteletext-common | Documentation items, wire vectors, the security review, the end-to-end check, and the close of TODO-6639 |
