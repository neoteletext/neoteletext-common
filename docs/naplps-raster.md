# NAPLPS on the teletext raster: one resolution for every coordinate NeoTeletext defines

| | |
|---|---|
| **Status** | Specification of 19 November 2026, for building at once by implementation agents in each repository working apart. It specifies the owner's decision DEC-6853 ("naplps must be the same resolution as teletext, not 640x480"). What it decides beyond DEC-6853 is listed in section 12 and recorded in rdm for the owner's confirmation. |
| **Companions** | `animation.md` (ANIM-6, ANIM-11, ANIM-13, ANIM-16), `page-rules.md` (RULE-12, RULE-13) and `renderer-parity.md` (PAR-1, PAR-10, PAR-24, PAR-40 to PAR-42), whose statements of a 640 by 480 picture this document replaces (section 10). |
| **Repositories it changes** | neoteletext-renderer-naplps, neoteletext-renderer-teletext (the engine), neoteletext-app-server, neoteletext-browser, neoteletext-server-ts-protocol (the TypeScript kit), neoteletext-server-channels (the Python kit), neoteletext-server-ts-ui-components, neoteletext-server-channel-naplpsdemo, neoteletext-server-channel-uicomponentsdemo, and this repository. |

Requirements are numbered `RAS-n`. The code read is: the NAPLPS renderer at `parity-2` c65f589, the engine at `parity` 62af44b5, the server at `parity` 432ed07, the browser at `parity` 9732d46, the TypeScript kit at `parity` e93260d (release 18.4.0), the Python kit at `parity` eb08906, the component library at `parity` fc5ba36 (release 26.3.0), the naplpsdemo channel at `livedevelopment` b0086ed, the uicomponentsdemo channel at `livedevelopment` f8273e4.

---

## 1. Inventory: where the 640 by 480 picture lives today

Each line is one place that defines the 640 by 480 "design picture", converts to or from it, or assumes it. Paths are from the repository's root.

**NAPLPS renderer (19 places).**
1. `crates/naplps/src/limits.rs`: `OBJECT_PICTURE_WIDTH` 640 and `OBJECT_PICTURE_HEIGHT` 480.
2. `crates/naplps/src/limits.rs`: `MAX_ANIMATION_PIXELS_PER_TICK` 153,600, "half of 640 by 480".
3. `crates/naplps/src/limits.rs`: `RECEIVER_CANVAS_WIDTH` and `RECEIVER_CANVAS_HEIGHT` (480, 462), raster figures written as their own literals.
4. `crates/naplps/src/surface.rs`: `Rect::on_canvas`, a design rectangle to canvas pixels.
5. `crates/naplps/src/surface.rs`: `design_pixel`, a canvas pixel to its design pixel (public, re-exported by `lib.rs`).
6. `crates/naplps/src/surface.rs`: `design_shift`, a design displacement in a canvas's sub-pixels.
7. `crates/naplps/src/terminal/objects.rs`: `Object`'s field documentation (width 1 to 640, height 1 to 480, positions "in the picture's pixels").
8. `crates/naplps/src/terminal/objects.rs`: the definition check (width and height against `OBJECT_PICTURE_*`).
9. `crates/naplps/src/terminal/objects.rs`: `bounds` and `placed`, a rectangle cut to 640 by 480.
10. `crates/naplps/src/terminal/objects.rs`: `objects_at`, picking at a design pixel.
11. `crates/naplps/src/terminal/objects.rs`: `objects_on_canvas`, picking at a canvas pixel through `design_pixel`.
12. `crates/naplps/src/terminal/objects.rs`: `pending` and `compose`, which turn design rectangles and moves into canvas ones.
13. `crates/naplps-render/src/main.rs`: `DEFAULT_WIDTH` 640 and `DEFAULT_HEIGHT` 480, the default canvas; `--neoteletext` and `--double`, and its own `RASTER_WIDTH`, `RASTER_HEIGHT`, `DISPLAY_LINES_ON_RASTER` and `RASTER_BORDER_LINES`.
14. `crates/naplps-render/src/play.rs`: the `--objects` file's form and its test (`region 2 1 -1 0 440 640 40 9 hidden`).
15. `fuzz/fuzz_targets/naplps_objects.rs`: objects placed on the design canvas and on the raster's, checked through `design_pixel`.
16. `fuzz/fuzz_targets/naplps_validator.rs`: "the design picture's canvas" as the second canvas.
17. `crates/naplps/src/lib.rs`: the crate example's `Canvas::new(640, 480)`.
18. Tests that place objects: `crates/naplps/tests/animation.rs`, `tests/parity.rs`, `crates/naplps-render/tests/neoteletext_raster.rs`; `README.md`'s usage line.
19. `crates/naplps-render/src/check.rs` (REQ-6646): `naplps-render check` draws on a 640 by 480 picture.

Not in scope (DEC-6853 item 4): `naplps-oracle`'s `NAPLPS_SCREEN` (640, 480), PP3's own screen, and the oracle and golden tests drawn at it; tests of a stream's drawing alone on a canvas of 640 by 480 (`terminal.rs`'s unit tests, `fixed.rs`), which use no coordinate NeoTeletext defines.

**Engine (11 places).**
1. `crates/neoteletext-web/src/records/naplps_objects.rs`: the record's layout comment (bytes 6 to 13 "in the picture's pixels", "1 to 640, 1 to 480"), `PICTURE_WIDTH` 640, `PICTURE_HEIGHT` 480, the field documentation, the reader's check.
2. `crates/neoteletext-web/src/records/naplps_objects/tests.rs`: objects 640 wide and "640 by 480".
3. `crates/neoteletext-web/src/wire_vectors.tsv`: the descriptions of `naplps_objects`, `naplps_objects_labelled` and `naplps_objects_one` (bytes unchanged).
4. `crates/neoteletext-rules/src/evaluator.rs`: `World::picture`'s documentation ("640 by 480 for NAPLPS").
5. `crates/neoteletext-cli/src/commands/rules_run.rs`: `Picture::Naplps`, size (640, 480).
6. `crates/neoteletext-cli/src/picture.rs`: `naplps_page` (PAR-10) writes its own three-byte operands (`nine_bits`, `operand`), the field 6 steps of 1/256 wide; computed (section 11), its characters are 11.25 dots apart, not 12.
7. `crates/neoteletext-picture/src/languages.rs`: its own unit-screen conversion (`fraction`, the centre of a pixel of the 480 by 462 canvas).
8. `crates/neoteletext-formats/src/picture_text/tests.rs`: a picture-text test drawn on `Canvas::new(640, 480)`.
9. `crates/neoteletext-input/src/event.rs`: `Pick`'s `picture_x` and `picture_y` documentation ("in its pixels"), which for NAPLPS are already raster dots (no change of value).
10. `crates/neoteletext-input/src/caps.rs` (PAR-1): `NAPLPS_CAP`'s meaning, which this document widens (RAS-9).
11. `fuzz/fuzz_targets/rules_world.rs`: the world's picture size for a NAPLPS page.

**Server (8 places).**
1. `crates/teletext-runtime/src/protocol/animation.rs`: `NaplpsObject`'s `x` ("in the picture's 640 by 480 pixels"), `width: U16In<1, 640>`, `height: U16In<1, 480>`, `origin_x`, `origin_y`.
2. `crates/teletext-runtime/src/protocol/rules.rs`: `RectDeclaration` ("a NAPLPS picture 640 by 480").
3. `protocol/schema-15.json` (generated): the same two descriptions and the bounds 640 and 480.
4. `crates/teletext-runtime/src/protocol.rs`: `PROTOCOL` 15.
5. `crates/teletext-runtime/src/fallback.rs`: `NAPLPS_DISPLAY_LINES` 462, its own literal of the renderer's figure.
6. `crates/teletext-runtime/src/channel/tests/rules.rs`: an object `"width":640`.
7. The tests of `fallback`, `descriptions` and `kept` that give NAPLPS objects.
8. `docs/architecture.md`'s account of NAPLPS objects.

**Browser (9 places).**
1. `native/decoder/src/naplps.rs`: the module's account of the design picture; `DESIGN_WIDTH`, `DESIGN_HEIGHT` and their assertion; `design_point` and `design_x`; `Page`'s objects "in the 640 by 480 picture"; `pick` (rectangles through `on_canvas`, then moved down by `TOP`); `target_state`'s bounds; `NaplpsPages::objects_at`; and the tests of all of these.
2. `native/decoder/src/engine/rules.rs`: `naplps_input`, which maps a pointer's dot to the design picture.
3. `native/decoder/src/animation/picture.rs`: `NAPLPS_SIZE` from the engine's `PICTURE_WIDTH`, `PICTURE_HEIGHT`.
4. `native/decoder/src/engine/animation_tests.rs`: places of the 640 by 480 picture (330, 110 and others).
5. `native/interface-core/src/canvas.rs`: `NAPLPS_DISPLAY_LINES` 462 and `NAPLPS_TOP_LINE`, literals of the renderer's figures (already raster).
6. `native/protocol/src/regis.rs` and `native/core/src/regis_pointer.rs`: the NAPLPS pick record is already 480 by 500 raster dots (no change of value).
7. `native/core/src/typing.rs`: `NAPLPS_CAP` offered (meaning widened, RAS-9).
8. The decoder's reading of records 17 and 25 when `NAPLPS_CAP` was not agreed (RAS-9 adds a rule).
9. `docs/architecture.md`, its NAPLPS paragraphs.

**TypeScript kit (6 places).**
1. `src/picture/naplps.ts`: the module comment; `DesignPoint` (exported by `src/index.ts`); `NaplpsObjectSpec`; `inPicture`; `unitSteps`; the `LARGEST_STEP` assertion against `OBJECT_PICTURE_WIDTH`; `rect`'s far corner at `x + width`; `object()`.
2. `src/picture/naplps-limits.ts` (generated): `OBJECT_PICTURE_WIDTH`, `OBJECT_PICTURE_HEIGHT`.
3. `scripts/picture-limits.ts`: the names it copies; `scripts/check.sh`'s `NAPLPS_FROM`.
4. `src/wire/limits.ts`: `PROTOCOL` 15, and the types generated from `schema-15.json`.
5. Tests: `test/naplps.test.ts`, `test/naplps-domain.test.ts`, `test/picture-builders.test.ts`, `test/animation/naplps-objects.test.ts`, `test/fixtures/picture-examples.jsonl`.
6. `package.json`: release 18.4.0.

**Python kit, in neoteletext-server-channels (6 places).**
1. `kits/python/src/neoteletext_app/naplps.py`: as the TypeScript kit's item 1.
2. `kits/python/src/neoteletext_app/naplps_limits.py` (generated) and `kits/python/scripts/generate_picture_limits.py`.
3. `kits/python/src/neoteletext_app/protocol_types.py`: `PROTOCOL` 15.
4. `kits/python/tests/test_builders.py` (`line(640, 480)`, `rect(639, 0, 1, 480)`, the 5/16 step, the error names).
5. `kits/python/tests/test_animation.py` (objects 640 wide) and `kits/python/tests/picture-examples.jsonl`.
6. The kit's version.

**Component library (6 places).**
1. `src/picture/grid.ts`: `NAPLPS_COLUMN` (16 design pixels), `naplpsX`, `naplpsY`, `naplpsLine`, `naplpsDotCentre`, `naplpsLineCentre`, `DISPLAY_FIRST_LINE` 19 and `DISPLAY_LINES` 462 as its own literals.
2. `src/picture/naplps-painter.ts`: `DesignBox`, `cellsBox`, the runs of raster pixels written as design points, the text field.
3. `src/picture/naplps-objects.ts`: `boundsOf`, an object's rectangle in the design picture.
4. `src/picture/naplps-macros.ts`: the caret and looks, through the grid's design mapping.
5. The golden pictures and tests of the NAPLPS renderer.
6. `package.json`: release 26.3.0, on kit 18.4.0.

**naplpsdemo channel (7 places).**
1. `src/naplps-bytes.ts`: `CANVAS_WIDTH` 640, `CANVAS_HEIGHT` 480, `canvasPoint` (a dot to the design canvas), `coordinate`, `filledRectangle` in design pixels.
2. `src/naplps-demo.ts`: the pointer page, which maps a pick's dot with `canvasPoint`.
3. `src/animation.ts`: the animation pages' objects in design pixels (`x: 400`, `width: 200`, buttons).
4. `scripts/make_pictures.py`: the 76 pictures authored on a 640 by 480 design canvas (`UNIT_HEIGHT`).
5. `scripts/charsets.py`: `CELL_W`, `CELL_H` in design units.
6. Tests: `test/naplps-demo.test.ts` (`canvasPoint`, operands of 640 and 614.4), `test/animation.test.ts` (`PICTURE` 640 by 480).
7. Its kit dependency (protocol 15).

**uicomponentsdemo channel (0 places of its own).** It moves to the new kit and component library (protocol 16, RAS-10).

**This repository (6 places).**
1. `docs/animation.md`: ANIM-6's position row; ANIM-11's table (bytes 6 to 13); ANIM-13's cut "to the picture of 640 by 480"; ANIM-16's table (153,600, "half of 640 by 480"); the example `"width":640`.
2. `docs/page-rules.md`: RULE-13 ("a NAPLPS picture 640 by 480").
3. `docs/renderer-parity.md`: section 1.4 (program protocol stays 15), PAR-1's `NAPLPS_CAP` text, PAR-10 (`naplps::design_point`'s inverse, three-byte precision), PAR-40 (the 640 by 480 design picture), PAR-42 (the grid's design mapping).
4. `docs/picture-examples.jsonl`: the NAPLPS builder examples.
5. `wire-vectors.tsv`: the descriptions of the NAPLPS_OBJECTS vectors.
6. `PROTOCOL.html`, generated from the rdm items DOC-6597, DOC-6595 and DOC-6585.

**rdm (17 records).** REQ-6531, REQ-6646, REQ-6772, REQ-6773, REQ-6774, DEC-6407, DEC-6746, DEC-6797, DEC-6812, DEC-6829, DEC-6849, DOC-6585, DOC-6595, DOC-6597, and in passing TODO-6547, TODO-6576 and TODO-6679 (history, not revised). Section 13 lists what was revised.

---

## 2. The raster and its display area (the renderer's constants)

**RAS-1 [NAPLPS renderer]. One set of named constants.**
- **Statement.** `naplps::limits` MUST define, and every other place MUST take from it by name (Rust) or by the kits' generated copies (TypeScript, Python):
  - `RASTER_WIDTH: u32 = 480` and `RASTER_HEIGHT: u32 = 500`: NeoTeletext's teletext raster, 40 columns of 12 dots by 25 rows of 20 lines (the engine's `PAGE_WIDTH` and `PAGE_HEIGHT`);
  - `DISPLAY_FIRST_LINE: u32 = 19` and `DISPLAY_LINES: u32 = 462`: the raster lines NAPLPS's display area is drawn on, lines 19 to 480 (REQ-5819, DEC-6667), with `const _: () = assert!(2 * DISPLAY_FIRST_LINE + DISPLAY_LINES == RASTER_HEIGHT)`;
  - `RECEIVER_CANVAS_WIDTH = RASTER_WIDTH` and `RECEIVER_CANVAS_HEIGHT = DISPLAY_LINES` (no literal of their own);
  - `MAX_ANIMATION_PIXELS_PER_TICK = RASTER_WIDTH as u64 * RASTER_HEIGHT as u64 / 2` (120,000, half the raster, the same as a teletext page's; ANIM-16 revised).
  - `OBJECT_PICTURE_WIDTH` and `OBJECT_PICTURE_HEIGHT` MUST be deleted.
- Every formula below is written in `DISPLAY_FIRST_LINE` (F) and `DISPLAY_LINES` (D), so that the owner's proposed 480 by 460 from line 20 (section 11) is a change of these two figures and nothing else. `naplps-render`'s own copies (`RASTER_WIDTH`, `RASTER_HEIGHT`, `DISPLAY_LINES_ON_RASTER`, `RASTER_BORDER_LINES`) MUST be deleted for these.
- **Verification.** The assertions compile; a test that the kits' generated copies name these figures.

**A coordinate.** Every place NeoTeletext defines on a NAPLPS page is a dot of the raster: x from 0 to 479 across, y from 0 to 499 down, origin at the top left of the 480 by 500 page, the same dots a teletext page and a pointer on it use (DEC-6853 item 1). Lines 0 to F − 1 and F + D to 499 are part of the raster and lie outside the NAPLPS display area: a coordinate there is valid, and nothing of the stream is drawn there (DEC-6853 item 3).

---

## 3. The mapping, which the renderer owns

The NAPLPS unit screen maps onto a canvas of W by H pixels as it does today (DEC-5766): the unit screen's width spans W, the displayed 25/32 of its height spans H, a point is rounded to the pixel whose centre is nearest, unit-screen (0, 0) at the centre of the bottom-left pixel. A canvas **shows the display area**: its width is the raster's 480 dots and its height the D lines from line F. The receiver's canvas is W = 480 k and H = D k with k = 1 (the browser, the server's fallback and description pictures, the engine's `neottx`) or k = 2 (`naplps-render --double`); a canvas of any other size (PP3's 640 by 480 in the oracle's tests, `naplps-render --width --height`) shows the same display area scaled, by the same formulas.

**RAS-2 [NAPLPS renderer]. A raster dot to a unit-screen point, and back.**
- **Statement.** In exact arithmetic, the point of dot (X, Y), the centre of that dot, is

  `across = X / 480`, `up = (F + D − 1 − Y) × 25 / (32 × D)`

  (for 19 and 462: `up = (480 − Y) × 25 / 14784`), and a unit-screen point lands on the receiver's canvas (k = 1) at

  `X = floor(sx / 256 + 1/2)` with `sx = floor(across × 480 × 256)`, and `Y = F + floor(sy / 256 + 1/2)` with `sy = (D − 1) × 256 − floor(up × D × 32/25 × 256)`,

  which are the renderer's `subpixel_of` and `pixel_of` on a 480 by D canvas, moved down F lines. X and Y need not be whole on the way in: a place between dots maps linearly by the same formula.
- The renderer MUST give, in `naplps` (re-exported at the crate root):
  - `pub fn dot_steps(x: i64, y: i64, denominator: i64, bytes: u8) -> (i64, i64)`: the place (x / denominator, y / denominator) of the raster as the two-dimensional multi-value operand's axis values for operands of `bytes` bytes (section 5.3.2.2.3, Table 5: 3 × `bytes` bits an axis, the first the sign), that is across × 2^(3 bytes − 1) and up × 2^(3 bytes − 1) each rounded to the nearest integer, a tie rounded up (towards plus infinity), then held to −2^(3 bytes − 1) to 2^(3 bytes − 1) − 1; `bytes` from 1 to 8, any other giving (0, 0).
  - `pub fn multi_value_operand(across: i64, up: i64, bytes: u8, out: &mut Vec<u8>)`: those values as operand bytes, three bits of x and three of y to a byte, most significant first, each with bit 7 set (Figure 11).
  - `pub fn dot_of_point(across: Unit, up: Unit) -> (i32, i32)`: the dot a point lands on, by the formula above.
- **Rounding, measured on every dot.** At four-byte operands every one of the raster's 240,000 dots, written by `dot_steps` and decoded by the renderer, lands on exactly that dot (a dot on a line outside the display area lands on a canvas row above row 0 or below row D − 1, off the canvas, where it belongs); at three-byte operands 184,448 of them do not. Computed for both 19/462 and 20/460 by a script mirroring `subpixel_of` and `pixel_of` (section 11). No whole dot is a tie at four or five bytes (480 and 14,784, or 14,720, have odd factors that no power of two cancels), so the tie rule matters only for places between dots.
- **Verification.** A renderer test: for every dot of the raster, `dot_of_point` of `dot_steps(X, Y, 1, 4)` (as `Unit`) is (X, Y), and a POINT SET ABSOLUTE written with those bytes on a 480 by D canvas lights pixel (X, Y − F) when Y is in the display area.

**RAS-3 [NAPLPS renderer]. A raster rectangle on any canvas, and a canvas pixel back to its dot.**
- **Statement.**
  - `naplps::raster_dot(x: u32, y: u32, width: u32, height: u32) -> (u32, u32)` replaces `design_pixel`: the dot the centre of pixel (x, y) of a canvas of `width` by `height` lies in, rounded half up as the drawing rounds a point to a pixel:

    `across = floor((2 x × 480 + W) / (2 W))`, `down = F + floor((2 D (y + 1) − H) / (2 H))`.

    On the receiver's canvas (k = 1) it is (x, y + F). On k = 2 it is (floor((x + 1) / 2), F + floor(y / 2)).
  - `Rect::on_canvas(&self, width, height) -> Option<Rect>` takes a rectangle **in raster dots** and gives exactly the canvas pixels whose `raster_dot` lies in it, cut to the canvas; `None` when there is none. In the current formula the design width 640 becomes 480, the design height 480 becomes D, and the rectangle's top and bottom are first taken F lines up (`edge − F`). On k = 1 it is the rectangle moved up F lines and cut to the canvas; a rectangle wholly on lines outside the display area is `None`.
  - `raster_shift(across: i64, down: i64, width: u32, height: u32) -> (i64, i64)` replaces `design_shift`: a move of (across, down) dots in sub-pixels of the canvas, `floor(across × W × 256 / 480)` and `floor(down × H × 256 / D)`, so that a moved macro's points land where they would were the macro drawn at the place moved to. On k = 1 it is (256 across, 256 down), exact.
  - `design_pixel`, `design_shift` and every mention of a design picture MUST be deleted.
- **Verification.** The existing property tests of `on_canvas` and `design_pixel`, rewritten for raster dots: picking at any canvas pixel equals picking at its `raster_dot`, on 480 by D, 960 by 2D and 640 by 480 canvases; on 480 by D `on_canvas` of every rectangle is that rectangle moved up F lines and cut.

---

## 4. Objects, moves, picking and bounds

**RAS-4 [NAPLPS renderer, engine, server, kits]. An object's fields are raster dots.**
- **Statement.** An object's fields (ANIM-11; the `NAPLPS_OBJECTS` record, the program message `naplps_objects`, `naplps::Object`, the kits' `object()`), keep their names and their places in the record, and mean:

  | Field | Range | Meaning |
  |---|---|---|
  | `x`, `y` | signed 16-bit, −32,768 to 32,767 | the raster dot of the rectangle's top left |
  | `width` | 1 to 480 (`RASTER_WIDTH`) | dots across, the rectangle being dots x to x + width − 1 |
  | `height` | 1 to 500 (`RASTER_HEIGHT`) | lines down, the rectangle being lines y to y + height − 1 |
  | `origin_x`, `origin_y` | signed 16-bit | the raster dot at which the object's macro, drawn where the stream would draw it, puts what is to be the rectangle's top left; 0 for a region |

  A reader refuses a width outside 1 to 480 or a height outside 1 to 500 (the engine's `RecordFault::BadValue`, the server's schema bound). The record's bytes and wire vectors are unchanged.
- **A move** (ANIM-6's position, `place` and `move` of an `ANIMATE` operation on a NAPLPS object, the rule table's bindings of them) is in raster dots. Drawing a macro object moves every point of its macro by (x − origin_x, y − origin_y) dots, `raster_shift` on the canvas drawn.
- **Bounds** (ANIM-13; `Terminal::bounds`): the object's rectangle as its state stands, cut to the raster, 0 to 479 by 0 to 499, or none while it does not exist, is not shown, or lies wholly outside the raster. A teletext sprite's rectangle is cut to the same raster.
- **Picking** (ANIM-11, RULE-12): an object is inside the pointer's dot when it is shown, detectable and the dot is in its bounds. `Terminal::objects_at(x, y)` takes a raster dot; `Terminal::objects_on_canvas(x, y, width, height)` is `objects_at(raster_dot(x, y, width, height))` for a pixel of a canvas showing the display area. A dot on the lines outside the display area picks an object whose bounds reach it (section 12, choice 2).
- **Drawing** is cut to `on_canvas` of the bounds, so a region's cover and a macro object's drawing never reach a canvas pixel whose dot is outside the object's rectangle, and nothing is drawn on lines outside the display area, which no canvas shows.
- **The pick record** the browser sends the trusted core (480 by 500 dots) holds each object's bounds dot for dot: no conversion, no `on_canvas`, no offset.
- **Verification.** Renderer: an object at two positions gives the same pixels moved by the same dots on the 480 by D canvas; on 960 by 2D by twice that; a hidden region of (0, 0, 480, 500) covers the whole canvas and its bounds are (0, 0, 480, 500); `objects_at(0, 0)` picks it. Engine and server: a width of 481 or a height of 501 is refused, 480 and 500 accepted.

**RAS-5 [engine, server, browser]. A rule table on a NAPLPS page uses the raster.**
- **Statement.** RULE-13's NAPLPS picture is the raster, 480 by 500, as a teletext page's is: a table's rectangles, the pointer's place, a wheel's place, a target's `x`, `y` and bounds (RULE-26), and `World::picture()` (480, 500) are raster dots. The unit of an object's position is one dot (the engine's `rules_run` `Picture::Naplps`: size (480, 500), unit (1, 1)). The browser passes the pointer's dot to the evaluator unchanged: `naplps_input` and `design_point` MUST be deleted.
- **Pointer, hover, PICK.** A pointer event's `px`, `py` on a NAPLPS page, a rule event's place and PICK's `picture_x`, `picture_y` are raster dots already and keep their values; PICK's `x`, `y` within an object are dots from its rectangle's top left. Hover (enter and leave of an object, carried as the MOUSE move with the target named, page-rules.md) is decided on the bounds of RAS-4.
- **Verification.** Browser: a press at dot (130, 110) on an object of (120, 100, 24, 20) fires the object's rule; at (100, 18), a dot above the display area, it fires an object whose bounds reach line 18 and no other; the evaluator's world says (480, 500).

---

## 5. Writing NAPLPS at raster dots: the kits, the component library, the channels and the engine's writers

**RAS-6 [TypeScript kit, Python kit]. The builders take raster dots.**
- **Statement.** `Naplps`'s coordinates (PAR-40) MUST be raster dots: a point, a line's end and a polygon's vertices take any number from 0 to 479 across and 0 to 499 down, and are written by RAS-2's formula at four-byte precision, as today after the DOMAIN of DEC-6849 (4/12, the logical pel (0, 0) in four bytes). A coordinate between dots maps linearly. `rect(x, y, width, height, { filled })` covers exactly the dots x to x + width − 1 and y to y + height − 1, width and height at least 1, x + width − 1 at most 479, y + height − 1 at most 499: it writes POINT SET ABSOLUTE at the dot (x, y + height − 1), its bottom left, and the RECTANGLE's displacement as the difference of the axis values of the dot (x + width − 1, y) and of that corner, so that the far corner lands where an absolute point would (a filled RECTANGLE covers from the pixel its near corner rounds to through the pixel its far corner rounds to, ANSI X3.110-1983 sections 5.3.3.4.1 and 5.3.2.2.6). Cells of 12 by 20 dots drawn by `rect` meet exactly, with no adjustment by the caller.
- `DesignPoint` becomes `RasterPoint` (TypeScript; `raster_point` where the Python kit names one). The bound errors name `RASTER_WIDTH` and `RASTER_HEIGHT`. The assertion that a step is under half a pixel becomes: 2 × 480 < 2^11 and 2 × D × 32/25 < 2^11 (a step is 0.234 dots and 0.289 lines at D = 462).
- The generated limits (`naplps-limits.ts`, `naplps_limits.py`) MUST copy `RASTER_WIDTH`, `RASTER_HEIGHT`, `DISPLAY_FIRST_LINE` and `DISPLAY_LINES` from `crates/naplps/src/limits.rs`, and no longer `OBJECT_PICTURE_WIDTH` or `OBJECT_PICTURE_HEIGHT`; `NAPLPS_FROM` names the renderer commit that has them.
- `object({...})` takes RAS-4's fields and bounds.
- **Releases.** The TypeScript kit 19.0.0 (a major release: every builder coordinate changes meaning) with `PROTOCOL = 16`; the Python kit's next major version with `PROTOCOL: Final = 16`.
- **Verification.** `picture-examples.jsonl` (this repository's, copied by both kits) rewritten in raster dots with new expected bytes, read by both kits' tests; tests: `rect(0, 0, 12, 20, { filled: true })` and `rect(12, 0, 12, 20, ...)` drawn by the NAPLPS renderer on 480 by D cover dots 0 to 11 and 12 to 23 of lines 0 to 19 with no dot shared (lines outside the display area drawn nowhere); `point(479, 480)` lights canvas pixel (479, 480 − F); `point(480, 0)` and `line(0, 500)` throw naming `RASTER_WIDTH` and `RASTER_HEIGHT`.

**RAS-7 [component library]. The grid is the raster.**
- **Statement.** A NAPLPS cell of row r, column c is the dots 12c to 12c + 11 of lines 20r to 20r + 19, written as those dots: `grid.ts`'s design mapping (`NAPLPS_COLUMN`, `naplpsX`, `naplpsY`, `naplpsLine`, `naplpsDotCentre`, `naplpsLineCentre`, `DesignBox`, `cellsBox`) MUST be deleted for the raster cell (`rasterDot`, `rasterLine` and the kit's `rect`), its `DISPLAY_FIRST_LINE` and `DISPLAY_LINES` taken from the kit's generated limits. An object's rectangle is its component's cells in dots (`boundsOf`); a mosaic cell's sixels are rectangles of 6 dots by 7, 7 and 6 lines; the caret the cell's last three lines; text is written from the dot (12c, 20r + 19), the foot of its row (PAR-10). Release 27.0.0, on kit 19.0.0.
- **Verification.** The golden pictures regenerated with their format version raised; a test that every cell's filled rectangle covers exactly its 12 by 20 dots on the 480 by D canvas.

**RAS-8 [naplpsdemo channel; engine `neottx`].**
- **naplpsdemo.** `naplps-bytes.ts` MUST write coordinates by RAS-2 from raster dots (the 640 by 480 canvas, `canvasPoint` and its scaling deleted); the pointer page uses the pick's dot as it comes; the animation pages' objects are laid out in raster dots, on whole cells where they were laid out on a grid; `scripts/make_pictures.py` and `scripts/charsets.py` author on the raster (a cell 12 by 20 dots) and the pictures are regenerated; the channel moves to kit 19.0.0 (protocol 16).
- **Engine.** `neottx write-text --picture naplps` (`picture.rs`'s `naplps_page`) and the picture converter (`neoteletext-picture`'s `languages.rs`) MUST write their coordinates with `naplps::dot_steps` and `naplps::multi_value_operand` at four-byte precision after DOMAIN 4/12 (as the kits do), deleting `nine_bits`, `operand` and `languages.rs`'s own `fraction` of a pixel's centre. The text field is section 11's.
- **Verification.** naplpsdemo: a pick at dot (240, 211) names the square drawn there; every page passes the server's check. Engine: `neottx write-text --picture naplps` of a 40-character line draws its characters on dots 12c to 12c + 11 of its row (the test `naplps_text_pages_draw_each_row_on_its_own_lines` extended to every column).

---

## 6. The protocols: what changes meaning, and the versions

**RAS-9 [engine, server, browser]. Push protocol 10 stays 10; `NAPLPS_CAP` carries the raster's meaning.**
- **What changes meaning on the wire.** `NAPLPS_OBJECTS` (type 25): bytes 6 to 17. `ANIMATE` (type 21) operations' positions on NAPLPS objects. A `RULES` record's rectangles, pointer comparisons and bound reads on a NAPLPS page. Nothing else: `DRAWING_LINKS`, `REGIS_CURSOR`, `NAPLPS` (17), MOUSE and PICK keep their meaning.
- **Why no version is raised.** Each of them means something only on a sub-page drawn in NAPLPS, and a server built to renderer parity sends the NAPLPS stream and `NAPLPS_OBJECTS` only to a receiver that agreed `NAPLPS_CAP` (bit 24) in WELCOME (PAR-24). Bit 24 is new in renderer parity's own unmerged branches. So `NAPLPS_CAP`'s meaning in PAR-1 MUST read: "the receiver draws a sub-page's NAPLPS from the NAPLPS record, type 17, with `NAPLPS_OBJECTS`, `DRAWING_LINKS` and `REGIS_CURSOR` for its objects, on the teletext raster of REQ-5819, every NeoTeletext coordinate of the page being a dot of that raster (DEC-6853)". What each peer sees:
  - **A receiver built before renderer parity** (the deployed browser) offers no bit 24, is never sent a type-17 or type-25 record, and shows the mosaic fallback (PAR-25), a teletext page of the same 480 by 500 dots: a rule table's rectangles in raster dots fall on the dots of that page they were written for; `ANIMATE` operations name objects it does not have, which ANIM-6 ignores.
  - **A receiver built to this document talking to a server that did not agree bit 24** (one built before renderer parity, which sends NAPLPS to everyone) MUST NOT draw what it is sent: the trusted core MUST drop records of types 17 and 25 on a connection whose WELCOME did not agree `NAPLPS_CAP`, before the decoder sees them, counting each in the console as dropped, so that a 640 by 480 rectangle is never read as raster dots. The sub-page is then its teletext page.
  - **A server and a receiver both built to this document** agree bit 24 and speak raster dots.
- **The one condition.** This holds only while no server that agrees bit 24 with 640 by 480 meaning has been deployed. Before merging, the coordinator MUST check that no build of renderer parity's server is deployed (app.neottx.com, the Cloudflare host). If one is, `NAPLPS_CAP` moves to bit 25, bit 24 is retired as the retired page bit is (refused in HELLO by `read_hello`), and the rest of this section holds with bit 25.
- **Verification.** Engine: `NAPLPS_CAP`'s documentation; the existing HELLO and WELCOME round trips. Browser: a connection whose WELCOME agreed no bit 24 drops a type-25 and a type-17 record and draws the teletext page; one that agreed draws the object at its dots. Server: unchanged tests of PAR-24.

**RAS-10 [server, both kits, every channel]. Program protocol 15 becomes 16.**
- **Why.** REQ-4769: the program protocol's version is one integer raised on every change of shape or meaning, so that a program and a server that disagree stop at once rather than misread each other. `naplps_objects`' `x`, `y`, `width`, `height`, `origin_x` and `origin_y` (and the same object in a rule table's group and in `description.picture.objects`), an `animate` operation's position and move on a NAPLPS object, and a rule table's rectangles and pointer places on a NAPLPS page change meaning; a program built for 15 would put every object in the wrong place without an error.
- **Exactly.** The server's `PROTOCOL` becomes 16; `protocol/schema-16.json` is generated and `schema-15.json` deleted (formats are defined as the target, with no compatibility path; DEC-2242's precedent); `NaplpsObject`'s `width` is `U16In<1, 480>` and `height` `U16In<1, 500>`, the descriptions name raster dots; `RectDeclaration`'s description reads "a teletext page and a NAPLPS picture are 480 by 500 dots, a ReGIS picture 800 by 480 pixels". Renderer parity's additions to 15 (PAR-16 to PAR-26) are in 16 as they were specified. Field names are unchanged.
- **What an old peer sees.** A program built on kit 18 or the Python kit at protocol 15 receives `start` with protocol 16 and stops, naming both versions (REQ-4767); a program built for 16 against a server at 15 stops the same way. Every channel (naplpsdemo, uicomponentsdemo, demosite, hackaday, home, the Python channels) MUST move to kit 19.0.0 or the Python kit at 16 before or with the server's deployment.
- **Verification.** The server's schema tests; each kit's test that it stops on a `start` of 15; `naplps_objects` with `width` 481 refused (`out_of_range`) and 480 accepted.

---

## 7. `naplps-render` and the oracle

**RAS-11 [NAPLPS renderer].**
- **Statement.** `naplps-render`'s default MUST be NeoTeletext's raster: the 480 by 500 picture, the display area on lines F to F + D − 1, the lines above and below in `Terminal::screen_colour` (what `--neoteletext` draws today); `--neoteletext` is deleted, `--double` draws the raster at twice its size, and `--width N --height N` (with `--border N`) draws a bare canvas of that size showing the display area, which is how the oracle's comparisons and golden tests ask for PP3's 640 by 480 (DEC-6853 item 4). `--objects FILE` takes raster dots on every size. `naplps-render check` (REQ-6646) draws on the receiver's 480 by D canvas. `DEFAULT_WIDTH` and `DEFAULT_HEIGHT` are deleted; `DEFAULT_PALETTE_BITS` stays.
- **Verification.** `tests/neoteletext_raster.rs` without the flag; `tests/golden.rs` and the oracle's tests pass `--width 640 --height 480` and keep their pictures; an objects file of raster dots composes on the default and on `--double`.

---

## 8. Order of building

1. **The NAPLPS renderer** (RAS-1 to RAS-4, RAS-11): its new API is what every Rust caller and both kits' generated limits name. Branch from `parity-2`.
2. **This repository**: animation.md, page-rules.md, renderer-parity.md and the examples (section 10), so the kits' examples exist.
3. **The engine**, pinning the renderer at step 1's commit (RAS-4, RAS-5, RAS-8, RAS-9).
4. **The server**, pinning the engine and the renderer (RAS-4, RAS-9, RAS-10), and **the TypeScript kit** from its `schema-16.json` and the renderer's limits (RAS-6, RAS-10); **the Python kit** after the TypeScript kit's examples.
5. **The component library** on kit 19.0.0 (RAS-7); **the browser**, pinning the engine and the renderer (RAS-4, RAS-5, RAS-9).
6. **The channels**: naplpsdemo (RAS-8), uicomponentsdemo and every other channel's kit version (RAS-10).

A pin round in progress in the engine, server and browser is finished first; this change is built on the commits it leaves.

---

## 9. Security

Nothing new is read from outside. The bounds change in place: a record's width is held to 480 and height to 500 in place of 640 and 480, a smaller rectangle, so no allocation grows (the browser's pick record and the renderer's composing were already the raster's and the canvas's size). `raster_dot`, `on_canvas` and `raster_shift` keep the saturating integer arithmetic of the functions they replace; a coordinate of −32,768 or 32,767 is cut, as today. The fuzz target `naplps_objects` checks the same properties on raster dots. Dropping types 17 and 25 without `NAPLPS_CAP` (RAS-9) removes a path by which a receiver drew what its server never agreed to.

---

## 10. What this replaces in the specifications

- **animation.md.** ANIM-6's position: "pixels for a NAPLPS object (the top left of its rectangle on the 640 by 480 picture)" becomes "dots of the teletext raster for a NAPLPS object (the top left of its rectangle, 480 by 500, DEC-6853)". ANIM-11's table: bytes 6 to 9 "the top left of the object's rectangle, a dot of the teletext raster (480 by 500, the origin at the top left, y down)", bytes 10 to 13 "1 to 480, 1 to 500"; the origin "in the same dots". ANIM-13: "A NAPLPS object's is cut to the raster of 480 by 500". ANIM-16's table: NAPLPS's `MAX_ANIMATION_PIXELS_PER_TICK` 120,000 (half the raster). The example's `"width":640` becomes `"width":480` (its `"y":440` stays a dot).
- **page-rules.md RULE-13.** "a NAPLPS picture 640 by 480" becomes "a NAPLPS picture the same 480 by 500 dots (DEC-6853)".
- **renderer-parity.md.** Section 1.4: the program protocol becomes 16 (RAS-10). PAR-1: `NAPLPS_CAP`'s meaning as RAS-9. PAR-10: the text written at the dot (0, 20r + 19) by `naplps::dot_steps` at four-byte precision after DOMAIN, the field as section 11 settles. PAR-40: coordinates are raster dots, `rect` as RAS-6. PAR-42's NAPLPS grid: as RAS-7.
- **picture-examples.jsonl, wire-vectors.tsv**: as RAS-6 and RAS-4.
- **rdm**: section 13.

---

## 11. If the owner confirms the display area of 480 by 460 from line 20

The owner has been asked whether NAPLPS's display area should become the 460 lines from line 20, exactly teletext rows 1 to 23 (40 by 23 cells of 12 by 20), its shape 480 × 16/13 / 460 = 1.2843 against NAPLPS's 1.28 (0.33 per cent off; 462 lines give 1.2788, 0.09 per cent), with NeoTeletext's text parts setting the NAPLPS text field so that a character is exactly one 12 by 20 Noto cell. It is not confirmed, and REQ-5819 is not revised here. If it is:

1. **REQ-5819** is revised: a NAPLPS page is drawn on 480 by 460 dots of the 480 by 500 raster, lines 20 to 479, with 20 lines above and below; `DISPLAY_FIRST_LINE` becomes 20 and `DISPLAY_LINES` 460 (RAS-1). Nothing else of sections 2 to 7 changes: every formula is written in F and D, and the point of dot (X, Y) becomes `up = (479 − Y) × 25 / 14720`. Every dot still lands exactly at four-byte precision (computed, section 3). The browser's, the server's and the component library's copies of 462 and 19 follow, being the renderer's names.
2. **Rows 0 and 24 lie wholly outside the picture**: row 0 is lines 0 to 19 and row 24 lines 480 to 499, so the header and the status row (PAR-30) are drawn over border lines only, where today the picture's first line (19) and last (480) lie under them.
3. **The text field.** In unit-screen terms a cell is 1/40 of the unit screen across and 20/460 × 25/32 = 25/736 up. Neither is a binary fraction, so no operand gives it exactly, and what the renderer draws depends on how the field and the text's origin are rounded. A character covers the canvas pixels whose centres lie in [origin, origin + field) along each axis (`text.rs`'s `draw`), and the cursor advances by the field's width in exact unit-screen arithmetic, so a field just under a cell, with the origin rounded down, covers exactly one cell as long as the run's accumulated shortfall stays under one dot. Computed for all 920 cells of rows 1 to 23, by a script mirroring `subpixel_of` and `text.rs` (not run on the renderer; the renderer test that confirms it is in the plan):

   | Operand bytes | Field across × up, in steps | On the raster | Cells exact, each row one run from its first column |
   |---|---|---|---|
   | 4 (1/2048) | 51 × 69 | 11.953 dots × 19.84 lines | columns 0 to 20 only: 437 of 920 cells wrong (the run drifts a dot by column 21) |
   | 4 | 51 × 70 (nearest) | 11.953 × 20.125 | 878 wrong: 70 steps covers 21 lines |
   | 4, each character placed by its own POINT SET at its cell, rounded down | 51 × 69 | as above | all 920 |
   | 5 (1/16384), field and origin rounded down | 409 × 556 | 11.982 × 19.98 | all 920 |

   So at four-byte precision the field's height rounds to exactly 20 lines with 69 steps (not 70, the nearest), but its width cannot keep a run of more than 21 characters on its cells. Two ways give every character its cell: a five-byte DOMAIN for the TEXT field and the text's origin (409 × 556 steps of 1/16384, both rounded down; also exact at 19/462 with 409 × 554), or four-byte operands with a POINT SET before each character (seven bytes more a character, SO, the point, SI). The same holds today at 19/462: PAR-10's field at three-byte precision (6 steps of 1/256 across, 11.25 dots) puts 917 of 920 cells wrong, and at four bytes a run drifts from column 21. Which way, and DEC-6849's revision if five bytes are taken, is for the owner with this proposal; until then the engine's and the component library's writers keep the four-byte field of 51 by 69 steps (rounded down) and place text one run per row, exact to column 20 (recorded as a to-do of each).

---

## 12. What this document decided without the owner

Recorded in rdm as one decision with `needs_confirmation`, linked to DEC-6853:
1. Push protocol 10 is not raised; `NAPLPS_CAP` carries the raster's meaning, and a receiver drops types 17 and 25 without it (RAS-9), on the condition stated there.
2. Bounds and picking use the rectangle cut to the raster, so a dot on the lines outside the display area can pick an object whose rectangle reaches it, as a teletext sprite on row 0 can be picked (RAS-4). The alternative, cutting to the display area, would make a coordinate valid by DEC-6853 item 3 pick nothing.
3. A builder's `rect` covers exactly its width and height in dots, its far corner written at the last dot (RAS-6), so that cells meet without the caller subtracting a dot.
4. `MAX_ANIMATION_PIXELS_PER_TICK` for NAPLPS becomes half the raster, 120,000, the teletext figure (RAS-1).
5. `naplps-render` draws the raster by default (RAS-11).
6. The renderer gives `dot_steps`, `multi_value_operand` and `dot_of_point` so that every Rust writer of NAPLPS coordinates calls one mapping (RAS-2).

---

## 13. The rdm records

Revised to state the raster (each a complete new version naming DEC-6853): REQ-6531, REQ-6646, REQ-6772, REQ-6773, REQ-6774, DEC-6407, DEC-6746, DEC-6797, DEC-6812, DEC-6829, DEC-6849, DOC-6585, DOC-6595, DOC-6597. The decision of section 12 and one to-do for each repository of the header, in the order of section 8, are created and linked to DEC-6853; their identifiers are in the build plan.
