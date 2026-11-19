# NAPLPS on the teletext raster: one resolution for every coordinate NeoTeletext defines

| | |
|---|---|
| **Status** | Specification of 19 November 2026, for building at once by implementation agents in each repository working apart. It specifies the owner's decisions DEC-6853 ("naplps must be the same resolution as teletext, not 640x480") and DEC-6857 (the display area is 480 by 460 dots from raster line 20, teletext rows 1 to 23, one Noto cell to a character; REQ-5819 version 2), and settles TODO-6859 (the text field's precision). What it decides beyond them is listed in section 12 and recorded in rdm (DEC-6856) for the owner's confirmation. |
| **Companions** | `animation.md` (ANIM-6, ANIM-11, ANIM-13, ANIM-16), `page-rules.md` (RULE-12, RULE-13) and `renderer-parity.md` (PAR-1, PAR-7, PAR-9, PAR-10, PAR-24, PAR-25, PAR-31, PAR-40 to PAR-42), whose statements of a 640 by 480 picture, of 462 lines from line 19 and of the text field this document replaces (section 10). |
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

**Places stating the display area of 462 lines from line 19 (DEC-6857 makes it 460 from line 20).** The renderer: `limits.rs` (`RECEIVER_CANVAS_HEIGHT` 462 and the `WORK_CAP` and `MAX_COMPOSE_WORK` figures and measurements derived from it), `naplps-render`'s `main.rs` (`DISPLAY_LINES_ON_RASTER`, `RASTER_BORDER_LINES` asserted to be 19) and `tests/neoteletext_raster.rs` (19 and 38 border lines), `tests/validator.rs`, `tests/animation.rs`, `tests/held.rs`, both fuzz targets, `README.md`, `docs/verification.md` and the samples' gallery and generators that say 462. The engine: `neoteletext-cli`'s `picture.rs` (`NAPLPS_LINES`, `NAPLPS_FIRST_LINE`, the test of line 480), `neoteletext-picture`'s `languages.rs` (`NAPLPS_WIDTH` by 462) and its tests, `docs/user-guide.md`. The server: `fallback.rs` (`NAPLPS_DISPLAY_LINES` 462 and its tests), `kept.rs`, `animation.rs`. The browser: `interface-core/src/canvas.rs` (`NAPLPS_DISPLAY_LINES` 462, `NAPLPS_TOP_LINE` asserted 19), `decoder/src/naplps.rs`, `engine/animation_tests.rs`, the console panel's tests, `docs/architecture.md`. The TypeScript kit: `src/picture/naplps.ts`, `DEPLOYMENT.md`. The Python kit: `naplps.py`. The component library: `grid.ts` (`DISPLAY_FIRST_LINE` 19, `DISPLAY_LINES` 462), `test/naplps-painter.test.ts`. naplpsdemo: `naplps-bytes.ts`, `scripts/charsets.py`, its test. This repository: `renderer-parity.md` (PAR-7, PAR-9, PAR-10, PAR-25, PAR-31, PAR-40, PAR-42), and `structure/10`, `11`, `20` and `23`.

**rdm (17 records).** REQ-6531, REQ-6646, REQ-6772, REQ-6773, REQ-6774, DEC-6407, DEC-6746, DEC-6797, DEC-6812, DEC-6829, DEC-6849, DOC-6585, DOC-6595, DOC-6597, and in passing TODO-6547, TODO-6576 and TODO-6679 (history, not revised). Section 13 lists what was revised.

---

## 2. The raster and its display area (the renderer's constants)

**RAS-1 [NAPLPS renderer]. One set of named constants.**
- **Statement.** `naplps::limits` MUST define, and every other place MUST take from it by name (Rust) or by the kits' generated copies (TypeScript, Python):
  - `RASTER_WIDTH: u32 = 480` and `RASTER_HEIGHT: u32 = 500`: NeoTeletext's teletext raster, 40 columns of 12 dots by 25 rows of 20 lines (the engine's `PAGE_WIDTH` and `PAGE_HEIGHT`);
  - `DISPLAY_FIRST_LINE: u32 = 20` and `DISPLAY_LINES: u32 = 460`: the raster lines NAPLPS's display area is drawn on, lines 20 to 479, exactly teletext rows 1 to 23 (DEC-6857, REQ-5819 version 2), with `const _: () = assert!(DISPLAY_FIRST_LINE + DISPLAY_LINES <= RASTER_HEIGHT)` and an assertion that both are whole rows of 20 lines;
  - `RECEIVER_CANVAS_WIDTH = RASTER_WIDTH` and `RECEIVER_CANVAS_HEIGHT = DISPLAY_LINES` (no literal of their own), so `RECEIVER_CANVAS_PIXELS` is 220,800;
  - the work bounds re-derived from that canvas (TODO-6844, DEC-6851): `WORK_CAP = 128 * RECEIVER_CANVAS_PIXELS` = 28,262,400 units (was 28,385,280) and `MAX_COMPOSE_WORK = 16 * RECEIVER_CANVAS_PIXELS` = 3,532,800 (was 3,548,160). Their documentation's measured figures MUST be measured again on the 480 by 460 canvas, not scaled: the ignored test `the_corpus_draws_within_the_work_allowance` of `tests/work.rs` over the same 680 pages gives the heaviest page's allowance (it was 8,672,322 units for `girl.nap` on 480 by 462; scaled by 460/462 it would be about 8,634,800, a margin of about 3.27, which is an estimate until measured), and `tests/work.rs`'s timings of whole-screen fills; the double canvas `naplps-render --double` draws on becomes 960 by 920 of a 960 by 1,000 picture;
  - `MAX_ANIMATION_PIXELS_PER_TICK = RASTER_WIDTH as u64 * RASTER_HEIGHT as u64 / 2` (120,000, half the raster, the same as a teletext page's; ANIM-16 revised);
  - `OBJECT_PICTURE_WIDTH` and `OBJECT_PICTURE_HEIGHT` MUST be deleted, and `naplps-render`'s own copies (`RASTER_WIDTH`, `RASTER_HEIGHT`, `DISPLAY_LINES_ON_RASTER`, `RASTER_BORDER_LINES`) MUST be deleted for these.
- Every formula below is written in `DISPLAY_FIRST_LINE` (F) and `DISPLAY_LINES` (D), so that a change of the display area is a change of these two figures and nothing else.
- **Verification.** The assertions compile; a test that the kits' generated copies name these figures; the re-measured figures written into `limits.rs` with the date.

**A coordinate.** Every place NeoTeletext defines on a NAPLPS page is a dot of the raster: x from 0 to 479 across, y from 0 to 499 down, origin at the top left of the 480 by 500 page, the same dots a teletext page and a pointer on it use (DEC-6853 item 1). Rows 0 and 24 (lines 0 to 19 and 480 to 499) are teletext's own and lie wholly outside the picture (DEC-6857 item 2): nothing of the stream is drawn there and nothing of them covers the picture; a coordinate there is valid and lies outside the display area (DEC-6853 item 3).

---

## 3. The mapping, which the renderer owns

The NAPLPS unit screen maps onto a canvas of W by H pixels as it does today (DEC-5766): the unit screen's width spans W, the displayed 25/32 of its height spans H, a point is rounded to the pixel whose centre is nearest, unit-screen (0, 0) at the centre of the bottom-left pixel. A canvas **shows the display area**: its width is the raster's 480 dots and its height the D lines from line F. The receiver's canvas is W = 480 k and H = 460 k with k = 1 (the browser, the server's fallback and description pictures, `neottx`, `naplps-render check`) or any whole multiple k (`naplps-render --double` draws k = 2). On a whole multiple the renderer draws the receiver's picture on its 480 by 460 geometry and writes each raster dot as its k by k pixels, as a teletext page is shown at a whole multiple (RAS-3, `naplps::dot_scale`). A canvas of any other size (PP3's 640 by 480 in the oracle's tests, `naplps-render --width --height`) shows the same display area scaled, by the same formulas as k = 1.

**RAS-2 [NAPLPS renderer]. A raster dot to a unit-screen point, and back.**
- **Statement.** In exact arithmetic, the point of dot (X, Y), the centre of that dot, is

  `across = X / 480`, `up = (F + D − 1 − Y) × 25 / (32 × D)`, for 20 and 460: `up = (479 − Y) × 25 / 14720`,

  and a unit-screen point lands on the receiver's canvas (k = 1) at

  `X = floor(sx / 256 + 1/2)` with `sx = floor(across × 480 × 256)`, and `Y = F + floor(sy / 256 + 1/2)` with `sy = (D − 1) × 256 − floor(up × D × 32/25 × 256)`,

  which are the renderer's `subpixel_of` and `pixel_of` on a 480 by D canvas, moved down F lines. X and Y need not be whole on the way in: a place between dots maps linearly.
- The renderer MUST give, in `naplps` (re-exported at the crate root):
  - `pub fn dot_steps(x: i64, y: i64, denominator: i64, bytes: u8, rounding: Rounding) -> (i64, i64)`: the place (x / denominator, y / denominator) of the raster as the two-dimensional multi-value operand's axis values for operands of `bytes` bytes (section 5.3.2.2.3, Table 5: 3 × `bytes` bits an axis, the first the sign), that is across × 2^(3 bytes − 1) and up × 2^(3 bytes − 1), each rounded by `Rounding::Nearest` (a tie rounded up, towards plus infinity) or `Rounding::Down` (towards minus infinity), then held to −2^(3 bytes − 1) to 2^(3 bytes − 1) − 1; `bytes` from 1 to 8, any other giving (0, 0).
  - `pub fn unit_steps(numerator: i64, denominator: i64, bytes: u8, rounding: Rounding) -> i64`: a unit-screen fraction as one axis's value, the same way (for sizes, such as the text field of RAS-8).
  - `pub fn multi_value_operand(across: i64, up: i64, bytes: u8, out: &mut Vec<u8>)`: those values as operand bytes, three bits of x and three of y to a byte, most significant first, each with bit 7 set (Figure 11).
  - `pub fn dot_of_point(across: Unit, up: Unit) -> (i32, i32)`: the dot a point lands on, by the formula above.
- **Rounding, computed on every dot.** At four-byte and at six-byte operands every one of the raster's 240,000 dots, written by `dot_steps` with `Rounding::Nearest` and decoded as the renderer decodes it, lands on exactly that dot on the 480 by 460 canvas (a dot of rows 0 and 24 lands on a canvas row above row 0 or below row 459, off the canvas, where it belongs), and on a canvas k times it lights the dot's whole k by k block of pixels from (k X, k (Y − 20)) (RAS-3). Run on the renderer: `crates/naplps/tests/raster_dots.rs`, for k = 1, 2 and 3. No whole dot is a tie at these precisions (480 and 14,720 have odd factors no power of two cancels), so the tie rule matters only for places between dots.
- **Verification.** A renderer test: for every dot of the raster, `dot_of_point` of `dot_steps(X, Y, 1, 6, Nearest)` (as `Unit`) is (X, Y), and a POINT SET ABSOLUTE written with those bytes after a six-byte DOMAIN on a 480 by 460 canvas lights pixel (X, Y − 20) when Y is from 20 to 479.

**RAS-3 [NAPLPS renderer]. A raster rectangle on any canvas, and a canvas pixel back to its dot.**
- **Statement.**
  - `naplps::dot_scale(width: u32, height: u32) -> u32`: k when the canvas is k times the receiver's 480 by 460 each way (W = 480 k and H = 460 k, k a whole number from 1), and 1 for any other size. **On a whole multiple (k ≥ 2) the renderer draws on the receiver's own geometry, 480 by 460, and writes each of its pixels, a raster dot, as the k by k canvas pixels from (k x, k y)**: every drawing primitive, fill, character, object and cover is drawn as at k = 1 and magnified. ANSI X3.110-1983 section 5.3.2.2.6 leaves the display's resolution to the implementation and maps the logical pel to "at least one" physical picture element; NeoTeletext's picture element is the raster dot (DEC-6853), which a display k times the raster shows as k by k pixels, as it shows a teletext page's dots. The pixel work a drawing spends (DEC-6851) is the receiver's on every whole multiple.
  - `naplps::raster_dot(x: u32, y: u32, width: u32, height: u32) -> (u32, u32)` replaces `design_pixel`: the raster dot canvas pixel (x, y) belongs to. On a whole multiple k it is (floor(x / k), F + floor(y / k)): on the receiver's canvas (x, y + 20), on k = 2 (floor(x / 2), 20 + floor(y / 2)), so pixels 2X and 2X + 1 are dot X and every pixel, the last column and line included, belongs to exactly one dot. On any other canvas it is the dot the pixel's centre lies in, rounded half up as the drawing rounds a point to a pixel:

    `across = floor((2 x × 480 + W) / (2 W))`, `down = F + floor((2 D (y + 1) − H) / (2 H))`.

  - `Rect::on_canvas(&self, width, height) -> Option<Rect>` takes a rectangle **in raster dots** and gives exactly the canvas pixels whose `raster_dot` lies in it, cut to the canvas; `None` when there is none. On a whole multiple k it is the rectangle's top and bottom taken F lines up and every edge times k, cut to the canvas: on k = 1 the rectangle moved up 20 lines and cut; a rectangle wholly on rows 0 or 24 is `None`. On any other canvas, the centre rule: the design width 640 of the former formula becomes 480, the design height 480 becomes D, and the rectangle's top and bottom are first taken F lines up (`edge − F`).
  - `raster_shift(across: i64, down: i64, width: u32, height: u32) -> (i64, i64)` replaces `design_shift`: a move of (across, down) dots in sub-pixels of the surface the renderer draws on for that canvas, `floor(across × W' × 256 / 480)` and `floor(down × H' × 256 / D)`, where W' and H' are the canvas's sides divided by `dot_scale`. On every whole multiple it is (256 across, 256 down), exact.
  - `design_pixel`, `design_shift` and every mention of a design picture MUST be deleted.
- **Why whole multiples are drawn magnified (TODO-6873).** As first written, every canvas used the centre rule, with the unit screen's origin at the centre of the bottom-left canvas pixel (DEC-5766). On 960 by 920 a dot's centre then falls on the boundary between two pixels, so the odd columns' centres lay on dot boundaries: column 0 alone was dot 0, column 959 belonged to no dot, and a fill from a dot's centre left the pixels of its first column and line undrawn, so neither every pixel belonged to one dot nor did whatever covered a dot cover all its pixels. Drawing a whole multiple as the magnified receiver picture makes both exact on every multiple and leaves k = 1 and every other size, PP3's 640 by 480 among them, unchanged.
- **Verification.** Property tests: picking at any canvas pixel equals picking at its `raster_dot`, on 480 by 460, 960 by 920 and 640 by 480 canvases; on 480 by 460 `on_canvas` of every rectangle is that rectangle moved up 20 lines and cut; on 960 by 920 and 1,440 by 1,380 every column and line belongs to exactly one dot; an object whose macro fills its rectangle, a hidden region over the whole raster, cells written by RAS-6's `rect` and a point at every dot each cover every canvas pixel of their dots and no other on 480 by 460 and its whole multiples (`crates/naplps/tests/animation.rs` and `raster_dots.rs`); PP3's oracle comparisons at 640 by 480 unchanged.

---

## 4. Objects, moves, picking and bounds

**RAS-4 [NAPLPS renderer, engine, server, kits]. An object's fields are raster dots.**
- **Statement.** An object's fields (ANIM-11; the `NAPLPS_OBJECTS` record, the program message `naplps_objects`, `naplps::Object`, the kits' `object()`) keep their names and their places in the record, and mean:

  | Field | Range | Meaning |
  |---|---|---|
  | `x`, `y` | signed 16-bit, −32,768 to 32,767 | the raster dot of the rectangle's top left |
  | `width` | 1 to 480 (`RASTER_WIDTH`) | dots across, the rectangle being dots x to x + width − 1 |
  | `height` | 1 to 500 (`RASTER_HEIGHT`) | lines down, the rectangle being lines y to y + height − 1 |
  | `origin_x`, `origin_y` | signed 16-bit | the raster dot at which the object's macro, drawn where the stream would draw it, puts what is to be the rectangle's top left; 0 for a region |

  A reader refuses a width outside 1 to 480 or a height outside 1 to 500 (the engine's `RecordFault::BadValue`, the server's schema bound). The record's bytes and wire vectors are unchanged.
- **A move** (ANIM-6's position, `move` of an `ANIMATE` operation on a NAPLPS object, the rule table's bindings of them) is in raster dots. Drawing a macro object moves every point of its macro by (x − origin_x, y − origin_y) dots, `raster_shift` on the canvas drawn.
- **Bounds** (ANIM-13; `Terminal::bounds`): the object's rectangle as its state stands, cut to the raster, 0 to 479 by 0 to 499, or none while it does not exist, is not shown, or lies wholly outside the raster.
- **Picking** (ANIM-11, RULE-12): an object is inside the pointer's dot when it is shown, detectable and the dot is in its bounds. `Terminal::objects_at(x, y)` takes a raster dot; `Terminal::objects_on_canvas(x, y, width, height)` is `objects_at(raster_dot(x, y, width, height))`. A dot of rows 0 and 24 picks an object whose bounds reach it (section 12, choice 3).
- **Drawing** is cut to `on_canvas` of the bounds, so nothing is drawn on rows 0 and 24, which no canvas shows.
- **The pick record** the browser sends the trusted core (480 by 500 dots) holds each object's bounds dot for dot: no conversion, no `on_canvas`, no offset.
- **Verification.** Renderer: an object at two positions gives the same pixels moved by the same dots on 480 by 460, by twice that on 960 by 920; a hidden region of (0, 0, 480, 500) covers the whole canvas, its bounds are (0, 0, 480, 500) and `objects_at(0, 0)` picks it. Engine and server: a width of 481 or a height of 501 is refused, 480 and 500 accepted.

**RAS-5 [engine, server, browser]. A rule table on a NAPLPS page uses the raster.**
- **Statement.** RULE-13's NAPLPS picture is the raster, 480 by 500, as a teletext page's is: a table's rectangles, the pointer's place, a wheel's place, a target's `x`, `y` and bounds (RULE-26), and `World::picture()` (480, 500) are raster dots. The unit of an object's position is one dot (the engine's `rules_run` `Picture::Naplps`: size (480, 500), unit (1, 1)). The browser passes the pointer's dot to the evaluator unchanged: `naplps_input` and `design_point` MUST be deleted.
- **Pointer, hover, PICK.** A pointer event's `px`, `py` on a NAPLPS page, a rule event's place and PICK's `picture_x`, `picture_y` are raster dots already and keep their values; PICK's `x`, `y` within an object are dots from its rectangle's top left. Hover (enter and leave of an object, carried as the MOUSE move with the target named) is decided on the bounds of RAS-4.
- **Verification.** Browser: a press at dot (130, 110) on an object of (120, 100, 24, 20) fires the object's rule; at (100, 10), a dot of row 0, it fires an object whose bounds reach line 10 and no other; the evaluator's world says (480, 500).

---

## 5. Writing NAPLPS at raster dots

**RAS-6 [every NeoTeletext writer of NAPLPS: both kits, the component library, the engine's `neottx write-text` and picture converter, naplpsdemo]. Six-byte operands, raster dots, exact rectangles.**
- **Precision (settles TODO-6859; DEC-6856 item 8).** Every NeoTeletext writer MUST select six-byte multi-value operands, for every coordinate, size, text field and colour it writes: DOMAIN (section 5.3.2.2, Figure 14) with the fixed-format byte 5/4 (single-value operands of one byte, Table 4; multi-value operands of six bytes, Table 5, b5 b4 b3 = 101; two dimensions, section 5.3.2.2.4) and the logical pel (0, 0) in six bytes (4/0 six times, section 5.3.2.2.6): 2/1 5/4 then six 4/0, nine bytes with its SO. It is written where DEC-6849 item 2 writes the four-byte DOMAIN today (before the first PDI or bytes of the program's own, after the writer's own RESET, inside each macro's contents). A coordinate is then eighteen bits an axis, a step of 1/131072 of the unit screen, 0.0037 dots and 0.0045 lines on the 480 by 460 canvas. Section 11 shows why four and five bytes do not give one Noto cell a character. DEC-6849's four bytes are replaced by six.
- **Colours at six bytes.** SET COLOR's operand (section 5.3.2.5.1) is a multi-value operand of six bytes, twelve bits a primary, two to a byte, G R B G R B from b6 to b1: each primary is its eight bits followed by four zero bits. The renderer keeps a primary's most significant eight bits (`to_eight_bits`), so every intensity 0 to 255 is read back exactly, 255 included.
- **Coordinates** are raster dots: a point, a line's end and a polygon's vertices take any number from 0 to 479 across and 0 to 499 down, written by RAS-2 with `Rounding::Nearest`. `rect(x, y, width, height, { filled })` covers exactly the dots x to x + width − 1 and lines y to y + height − 1, width and height at least 1, x + width − 1 at most 479, y + height − 1 at most 499: it writes POINT SET ABSOLUTE at the dot (x, y + height − 1), its bottom left, and the RECTANGLE's displacement as the difference of the axis values of the dot (x + width − 1, y) and of that corner (a filled RECTANGLE covers from the pixel its near corner rounds to through the pixel its far corner rounds to, ANSI X3.110-1983 sections 5.3.3.4.1 and 5.3.2.2.6). Cells of 12 by 20 dots drawn by `rect` meet exactly.
- **The kits' API.** `DesignPoint` becomes `RasterPoint`; the bound errors name `RASTER_WIDTH` and `RASTER_HEIGHT`; the generated limits copy `RASTER_WIDTH`, `RASTER_HEIGHT`, `DISPLAY_FIRST_LINE` and `DISPLAY_LINES` and no longer `OBJECT_PICTURE_*`; `object({...})` takes RAS-4's fields. The Python kit rounds a tie up by `floor(value + 1/2)`, never `round`, which rounds a tie to even. Releases: the TypeScript kit 19.0.0 with `PROTOCOL = 16`; the Python kit's next major version with `PROTOCOL: Final = 16`.
- **Verification.** `picture-examples.jsonl` (this repository's, copied by both kits) rewritten in raster dots and six-byte operands with new expected bytes; tests: `rect(0, 20, 12, 20, { filled: true })` and `rect(12, 20, 12, 20, ...)` drawn by the renderer on 480 by 460 cover dots 0 to 11 and 12 to 23 of canvas lines 0 to 19 with no dot shared; `point(479, 479)` lights canvas pixel (479, 459); `point(480, 0)` and `line(0, 500)` throw naming `RASTER_WIDTH` and `RASTER_HEIGHT`; `colour(1, 255, 128, 1)` reads back as (255, 128, 1).

**RAS-7 [component library]. The grid is the raster.**
- **Statement.** A NAPLPS cell of row r (1 to 23), column c is the dots 12c to 12c + 11 of lines 20r to 20r + 19, written as those dots: `grid.ts`'s design mapping (`NAPLPS_COLUMN`, `naplpsX`, `naplpsY`, `naplpsLine`, `naplpsDotCentre`, `naplpsLineCentre`, `DesignBox`, `cellsBox`) MUST be deleted for the raster cell (`rasterDot`, `rasterLine` and the kit's `rect`), its `DISPLAY_FIRST_LINE` and `DISPLAY_LINES` taken from the kit's generated limits. An object's rectangle is its component's cells in dots (`boundsOf`); a mosaic cell's sixels are rectangles of 6 dots by 7, 7 and 6 lines; the caret the cell's last three lines; text as RAS-8. Rows 0 and 24 are the teletext page's, never drawn in the picture. Release 27.0.0, on kit 19.0.0.
- **Verification.** The golden pictures regenerated with their format version raised; a test that every cell's filled rectangle covers exactly its 12 by 20 dots on the 480 by 460 canvas; RAS-8's test.

**RAS-8 [every NeoTeletext writer of NAPLPS text: the engine's `neottx write-text` and `picture_text` callers, the server's text parts, both kits, the component library]. One Noto cell a character, text row r on teletext row r (DEC-6857 item 3).**
- **Statement.** A writer of text into a NAPLPS picture MUST, in the six-byte domain of RAS-6:
  1. set the TEXT command's character field (section 5.3.2.3.4) to `unit_steps(1, 40, 6, Down)` across and `unit_steps(20 × 25, 32 × 460, 6, Down)` up: **3,276 by 4,452 steps of 1/131072**, 11.9971 dots by 19.9992 lines, a hair under one cell each way;
  2. write row r's text (r from 1 to 23) from the point of the dot (12c, 20r + 19), the lower left of its first cell c (a character field's origin is its lower left corner and the field lies up and to the right, section 5.3.2.3.2, Figure 17), by `dot_steps` with **`Rounding::Down`** on both axes (towards the bottom left, so the origin is at or just short of the dot's centre);
  3. write a row as one run from its first cell; nothing else between its characters.
  The renderer covers with a character the canvas pixels whose centres lie in [origin, origin + field) along each axis and samples a Noto glyph's 12 by 20 dots at each pixel's share of the field (`text.rs`'s `draw`, `Shape::Glyph`), and the cursor advances by the field's width in exact unit-screen arithmetic, so a field just under a cell with its origin rounded down puts every character exactly on its cell: computed for all 920 cells of rows 1 to 23, by a script mirroring `subpixel_of` and `draw` for `Shape::Glyph`, every pixel of every cell is the glyph's own dot, glyph column k on dot 12c + k and glyph row j on line 20r + j, for a whole 40-cell run. Rounding the field to nearest (3,277 steps, 12.0007 dots) covers 13 dots and fails every cell; four and five bytes fail as section 11 shows.
  4. The server's text parts (PAR-5, PAR-21) are bytes of characters only: a program that places a text part sets the field and point as items 1 and 2 before it (the kits' `text()` does, taking the cell `(row, column)` it is written at), and the server MUST NOT write a field or point of its own.
  5. **Double height** (teletext's, EN 300 706 Table 26, code 0/D: a character 12 dots by two rows, drawn from the upper of the two; DEC-6889, TODO-6890): the field `unit_steps(1, 40, 6, Down)` across and `unit_steps(2 × 20 × 25, 32 × 460, 6, Down)` up, **3,276 by 8,904 steps** (11.9971 dots by 39.9984 lines, a hair under two cells), and the point of the dot (12c, 20(r + 1) + 19), the lower left of the cell below, rounded down as item 2, for an upper row r from 1 to 22. Drawn by the NAPLPS renderer with the engine's Noto Teletext glyphs, a row of 40 such characters puts every glyph on its 12 by 40 dots, glyph row j on lines 20r + 2j and 20r + 2j + 1, the same pixels as the engine's own teletext double height of the same character (checked for eleven rows of 40, all 94 codes of G0 Latin English, on 19 November 2026 against the renderer at 21f439b and `neottx render`). The kits' `text()` take it as `rows: 2`; the shared example `naplps-double-height-text` gives its bytes.
- Pages authored elsewhere keep their own text size (DEC-6857 item 3).
- **The test every writer MUST pass.** Each writer's repository keeps a test that writes, by that writer, a page of the 23 rows 1 to 23 of 40 characters each (row r, column c the character of code 0x21 + ((r + c) mod 94) of the G0 Latin English set), draws it with the NAPLPS renderer at the pinned commit on a 480 by 460 canvas given the engine's Noto Teletext glyphs, and asserts, for every cell, that its 12 by 20 dots on raster lines 20r to 20r + 19 (canvas lines 20r − 20 to 20r − 1) and dots 12c to 12c + 11 are exactly the glyph's bitmap in the drawing colour on the field's background (colour mode 2), and that no pixel outside the 920 cells is written. The engine's test `naplps_text_pages_keep_each_character_in_its_column` becomes this test with no drift allowed. Where a repository cannot run the renderer (the TypeScript and Python kits, the component library), its test compares its bytes with the shared example `naplps-text-page` of `picture-examples.jsonl`, whose bytes the renderer's own repository draws in this test.

---

## 6. The protocols: what changes meaning, and the versions

**RAS-9 [engine, server, browser]. Push protocol 10 stays 10; `NAPLPS_CAP` carries the raster's meaning.**
- **What changes meaning on the wire.** `NAPLPS_OBJECTS` (type 25): bytes 6 to 17. `ANIMATE` (type 23) operations' positions on NAPLPS objects. A `RULES` record's rectangles, pointer comparisons and bound reads on a NAPLPS page. Where a NAPLPS sub-page's picture is drawn (lines 20 to 479). Nothing else: `DRAWING_LINKS`, `REGIS_CURSOR`, `NAPLPS` (17), MOUSE and PICK keep their meaning.
- **Why no version is raised.** Each of them means something only on a sub-page drawn in NAPLPS, and a server built to renderer parity sends the NAPLPS stream and `NAPLPS_OBJECTS` only to a receiver that agreed `NAPLPS_CAP` (bit 24) in WELCOME (PAR-24). Bit 24 is new in renderer parity's own unmerged branches. So `NAPLPS_CAP`'s meaning in PAR-1 MUST read: "the receiver draws a sub-page's NAPLPS from the NAPLPS record, type 17, with `NAPLPS_OBJECTS`, `DRAWING_LINKS` and `REGIS_CURSOR` for its objects, on the 480 by 460 dots from line 20 of the teletext raster (REQ-5819, DEC-6857), every NeoTeletext coordinate of the page being a dot of that raster (DEC-6853)". What each peer sees:
  - **A receiver built before renderer parity** (the deployed browser) offers no bit 24, is never sent a type-17 or type-25 record, and shows the mosaic fallback (PAR-25), a teletext page of the same 480 by 500 dots: a rule table's rectangles in raster dots fall on the dots they were written for; `ANIMATE` operations name objects it does not have, which ANIM-6 ignores.
  - **A receiver built to this document talking to a server that did not agree bit 24** (one built before renderer parity, which sends NAPLPS to everyone) MUST NOT draw what it is sent: the trusted core MUST drop records of types 17 and 25 on a connection whose WELCOME did not agree `NAPLPS_CAP`, before the decoder sees them, counting each in the console as dropped. The sub-page is then its teletext page.
  - **A server and a receiver both built to this document** agree bit 24 and speak raster dots.
- **The one condition.** This holds only while no server that agrees bit 24 with the earlier meaning has been deployed. Before merging, the coordinator MUST check that no build of renderer parity's server is deployed (app.neottx.com, the Cloudflare host). If one is, `NAPLPS_CAP` moves to bit 25, bit 24 is retired as the retired page bit is (refused in HELLO by `read_hello`), and the rest of this section holds with bit 25.
- **Verification.** Engine: `NAPLPS_CAP`'s documentation; the existing HELLO and WELCOME round trips. Browser: a connection whose WELCOME agreed no bit 24 drops a type-25 and a type-17 record and draws the teletext page; one that agreed draws the object at its dots. Server: unchanged tests of PAR-24.

**RAS-10 [server, both kits, every channel]. Program protocol 15 becomes 16.**
- **Why.** REQ-4769: the program protocol's version is one integer raised on every change of shape or meaning. `naplps_objects`' `x`, `y`, `width`, `height`, `origin_x` and `origin_y` (and the same object in a rule table's group and in `description.picture.objects`), an `animate` operation's position and move on a NAPLPS object, a rule table's rectangles and pointer places on a NAPLPS page, and where a `naplps` picture is drawn change meaning; a program built for 15 would put every object in the wrong place without an error.
- **Exactly.** The server's `PROTOCOL` becomes 16; `protocol/schema-16.json` is generated and `schema-15.json` deleted (formats are defined as the target, with no compatibility path; DEC-2242's precedent); `NaplpsObject`'s `width` is `U16In<1, 480>` and `height` `U16In<1, 500>`, the descriptions name raster dots; `RectDeclaration`'s description reads "a teletext page and a NAPLPS picture are 480 by 500 dots, a ReGIS picture 800 by 480 pixels". Renderer parity's additions to 15 (PAR-16 to PAR-26) are in 16 as they were specified. Field names are unchanged.
- **What an old peer sees.** A program built on kit 18 or the Python kit at protocol 15 receives `start` with protocol 16 and stops, naming both versions (REQ-4767); a program built for 16 against a server at 15 stops the same way. Every channel (naplpsdemo, uicomponentsdemo, demosite, hackaday, home, the Python channels) MUST move to kit 19.0.0 or the Python kit at 16 before or with the server's deployment.
- **Verification.** The server's schema tests; each kit's test that it stops on a `start` of 15; `naplps_objects` with `width` 481 refused (`out_of_range`) and 480 accepted.

---

## 7. Where the picture is drawn, `naplps-render` and the oracle

**RAS-11 [NAPLPS renderer, engine, server, browser]. The canvas is 480 by 460, placed at line 20.**
- **Statement.** Every receiver of NeoTeletext draws a NAPLPS sub-page on a canvas of 480 by 460 (`RECEIVER_CANVAS_*`), placed at raster line 20 of the 480 by 500 picture it carries or composes: the browser's decoder (`decoder/src/naplps.rs` `HEIGHT` and `TOP` from the renderer's constants, `interface-core/src/canvas.rs`'s `NAPLPS_DISPLAY_LINES` and `NAPLPS_TOP_LINE` asserted equal to them), the server's mosaic fallback and public pictures (`fallback.rs`'s `NAPLPS_DISPLAY_LINES` deleted for the renderer's; the fallback's 80 by 69 sixels of rows 1 to 23 now come from exactly those rows), and the engine's `neottx render`, `view`, `show` and `html` (`picture.rs`'s `NAPLPS_LINES` and `NAPLPS_FIRST_LINE` from the renderer's). Lines 0 to 19 and 480 to 499 of the carried picture are rows 0 and 24 of the teletext page beneath, drawn by the receiver as on any teletext page (the header and status row, the coloured-key row, PAR-31), never covered by the picture and never covering it; they are filled in `Terminal::screen_colour` only where the teletext page draws nothing (DEC-6512). The picture converter (PAR-9) fits pictures to 480 by 460 dots.
- **`naplps-render`.** Its default MUST be NeoTeletext's raster: the 480 by 500 picture, the display area on lines 20 to 479, rows 0 and 24 in `Terminal::screen_colour` (what `--neoteletext` draws today); `--neoteletext` is deleted, `--double` draws the raster at twice its size (960 by 1,000, the canvas 960 by 920 at line 40), and `--width N --height N` (with `--border N`) draws a bare canvas of that size showing the display area, which is how the oracle's comparisons and golden tests ask for PP3's 640 by 480 (DEC-6853 item 4). `--objects FILE` takes raster dots on every size. `naplps-render check` (REQ-6646) draws on the receiver's 480 by 460 canvas. `DEFAULT_WIDTH` and `DEFAULT_HEIGHT` are deleted; `DEFAULT_PALETTE_BITS` stays.
- **Verification.** `tests/neoteletext_raster.rs` without the flag: 20 and 40 border lines, the canvas at lines 20 and 40; `tests/golden.rs` and the oracle's tests pass `--width 640 --height 480` and keep their pictures; the browser's and server's tests that a NAPLPS picture's first drawn line is 20 and its last 479; the engine's test of line 480 now finds row 24's own line.

---

## 8. Order of building

1. **The NAPLPS renderer** (RAS-1 to RAS-4, RAS-11; RAS-8's renderer-side test page): its new API is what every Rust caller and both kits' generated limits name. Branch from `parity-2` at its newest commit (DEC-6858's work included).
2. **This repository**: animation.md, page-rules.md, renderer-parity.md and the shared examples (section 10), so the kits' examples exist.
3. **The engine**, pinning the renderer at step 1's commit (RAS-4, RAS-5, RAS-6, RAS-8, RAS-9, RAS-11).
4. **The server**, pinning the engine and the renderer (RAS-4, RAS-8 item 4, RAS-9 to RAS-11), and **the TypeScript kit** from its `schema-16.json` and the renderer's limits (RAS-6, RAS-8, RAS-10); **the Python kit** after the TypeScript kit's examples.
5. **The component library** on kit 19.0.0 (RAS-7, RAS-8); **the browser**, pinning the engine and the renderer (RAS-4, RAS-5, RAS-9, RAS-11).
6. **The channels**: naplpsdemo (RAS-6, RAS-8), uicomponentsdemo and every other channel's kit version (RAS-10).

A pin round in progress in the engine, server and browser is finished first; this change is built on the commits it leaves.

---

## 9. Security

Nothing new is read from outside. The bounds change in place: a record's width is held to 480 and height to 500 in place of 640 and 480, a smaller rectangle, so no allocation grows; the receiver canvas shrinks by 960 pixels, and `WORK_CAP` and `MAX_COMPOSE_WORK` shrink with it (RAS-1), so the time a stream can cost does not grow. Six-byte operands make each coordinate two bytes longer: a stream of a given length holds fewer coordinates, so no bound on work per byte grows (`WORK_PER_BYTE` is unchanged). `raster_dot`, `on_canvas`, `raster_shift`, `dot_steps` and `unit_steps` keep saturating integer arithmetic; a coordinate of −32,768 or 32,767 is cut, as today. The fuzz target `naplps_objects` checks the same properties on raster dots. Dropping types 17 and 25 without `NAPLPS_CAP` (RAS-9) removes a path by which a receiver drew what its server never agreed to.

---

## 10. What this replaces in the specifications

- **animation.md.** ANIM-6's position: "pixels for a NAPLPS object (the top left of its rectangle on the 640 by 480 picture)" becomes "dots of the teletext raster for a NAPLPS object (the top left of its rectangle, 480 by 500, DEC-6853)". ANIM-11's table: bytes 6 to 9 "the raster dot of the top left of the object's rectangle (480 by 500, the origin at the top left, y down)", bytes 10 to 13 "1 to 480, 1 to 500"; the origin "in the same dots". ANIM-13: "A NAPLPS object's is cut to the raster of 480 by 500". ANIM-16's table: NAPLPS's `MAX_ANIMATION_PIXELS_PER_TICK` 120,000 (half the raster). The example's `"width":640` becomes `"width":480`.
- **page-rules.md RULE-13.** "a NAPLPS picture 640 by 480" becomes "a NAPLPS picture the same 480 by 500 dots, drawn on rows 1 to 23 (DEC-6853, DEC-6857)".
- **renderer-parity.md.** Section 1.4: the program protocol becomes 16 (RAS-10). PAR-1: `NAPLPS_CAP`'s meaning as RAS-9. PAR-7, PAR-25, PAR-26, PAR-31: 480 by 460 from line 20; rows 0 and 24 are the teletext page's and lie wholly outside the picture (RAS-11). PAR-9: fitted to 480 by 460. PAR-10: RAS-8 (the field 3,276 by 4,452 steps of 1/131072 after a six-byte DOMAIN; row r's text from the dot (0, 20r + 19) rounded down). PAR-40: coordinates are raster dots at six-byte precision, `rect` and colours as RAS-6. PAR-42's NAPLPS grid: RAS-7.
- **picture-examples.jsonl, wire-vectors.tsv**: as RAS-6, RAS-8 and RAS-4.
- **rdm**: section 13.

---

## 11. Why six bytes: the text field computed for every cell

A cell is 1/40 of the unit screen across and 20/460 × 25/32 = 25/736 up. Neither is a binary fraction, so no operand gives it exactly; what the renderer draws depends on how the field and the text's origin are rounded. A character covers the canvas pixels whose centres lie in [origin, origin + field) along each axis and samples its glyph at each pixel's share of the field (`text.rs`'s `draw`, `Shape::Glyph`, which adds half a pixel's share before sampling), and the cursor advances by the field's width in exact unit-screen arithmetic. So the field must be just under a cell (just over covers a thirteenth dot or a twenty-first line) with the origin rounded down, and the run's accumulated shortfall must stay small enough that every pixel still samples its own glyph column. Computed on the 480 by 460 canvas for all 920 cells of rows 1 to 23 (23 rows of 40 characters, each row one run from column 0 unless stated), by a script mirroring `subpixel_of` and `draw`; a cell is right only when each of its 240 pixels is written with its own glyph dot and no pixel outside it is written:

| Operand bytes | Field across × up, in steps | On the raster | Origin | Cells wrong |
|---|---|---|---|---|
| 4 (1/2048) | 51 × 69 (down) | 11.953 dots × 19.84 lines | down | 690 (from column 10) |
| 4 | 51 × 69 | as above | down, a POINT SET before every character | 0 |
| 4 | 51 × 70 (nearest) | 11.953 × 20.125 | down | 790 (21 lines) |
| 5 (1/16384) | 409 × 556 (down) | 11.982 × 19.98 | down | 276 (from column 28) |
| 5 | 409 × 556 | as above | down, a run at most 27 cells | 0 |
| 5 | 410 × 557 (nearest) | 12.012 × 20.017 | down | 920 (13 dots a cell) |
| 6 (1/131072) | 3,276 × 4,452 (down) | 11.997 × 19.999 | down | **0** |
| 6 | 3,276 × 4,452 | as above | nearest | 0 (rounding down is still required, as the margin a writer may rely on) |
| 7 and 8 | the same rounding | | down | 0 |

Five bytes with 410/16384 (12.012 dots), as TODO-6859 proposed, covers 13 dots with each character, since the pixel 12 dots on has its centre inside a field 12.012 dots wide; a character's thirteenth pixel repeats its last glyph column and every cell after is shifted. Five bytes with 409 works only for runs of up to 27 cells, and four bytes only with a point before every character. Six bytes is the shortest precision at which a whole 40-cell row written from one point, as one run, keeps every character on its cell, so every writer selects it for everything (RAS-6), which also keeps one DOMAIN for a whole stream. Not run on the renderer yet; RAS-8's test is that run.

---

## 12. What this document decided without the owner

Recorded in rdm as DEC-6856 (`needs_confirmation`), linked to DEC-6853 and DEC-6857:
1. Push protocol 10 is not raised; `NAPLPS_CAP` carries the raster's meaning, and a receiver drops types 17 and 25 without it (RAS-9), on the condition stated there.
2. Program protocol 15 becomes 16 (RAS-10, as REQ-4769 requires).
3. Bounds and picking use the rectangle cut to the raster, so a dot of rows 0 and 24 can pick an object whose rectangle reaches it (RAS-4); nothing is drawn there.
4. A builder's `rect` covers exactly its width and height in dots, its far corner written at the last dot (RAS-6).
5. `MAX_ANIMATION_PIXELS_PER_TICK` for NAPLPS becomes half the raster, 120,000 (RAS-1).
6. `naplps-render` draws the raster by default (RAS-11).
7. The renderer gives `dot_steps`, `unit_steps`, `multi_value_operand` and `dot_of_point` so that every Rust writer calls one mapping (RAS-2).
8. Every NeoTeletext writer uses six-byte operands for everything; the text field is 3,276 by 4,452 steps of 1/131072 with the origin rounded down; the server writes no field or point of its own (RAS-6, RAS-8). This settles TODO-6859 and replaces DEC-6849's four bytes.
9. A canvas that is a whole multiple k of the receiver's 480 by 460 is drawn as the receiver's picture with each raster dot k by k pixels, `raster_dot` there being (floor(x / k), 20 + floor(y / k)); other sizes keep the centre rule (RAS-3, TODO-6873).

---

## 13. The rdm records

Revised (each a complete new version naming DEC-6853 or DEC-6857): REQ-5923, REQ-6531, REQ-6772, REQ-6773, REQ-6774, DEC-6407, DEC-6746, DEC-6797, DEC-6812, DEC-6829, DEC-6849, DEC-6856, DOC-6585, DOC-6595, DOC-6597. TODO-6859 is closed by DEC-6856 item 8. Still to be revised, by the to-do of the repository that owns each: REQ-6646, REQ-5789, DEC-6851 (with re-measured figures), DEC-6829 and DEC-6407 (480 by 460) by TODO-6861; REQ-6761 and REQ-6763 by TODO-6863; REQ-6532, REQ-6533 and REQ-6766 to REQ-6769 by TODO-6864; DEC-6797 item 7 by TODO-6865; DEC-6812 item 8 by TODO-6867; DEC-6746, REQ-6771 and REQ-6408 by TODO-6868. The to-dos, in the order of section 8: TODO-6861 (NAPLPS renderer), TODO-6862 (this repository), TODO-6863 (engine), TODO-6864 (server), TODO-6865 (TypeScript kit), TODO-6866 (Python kit), TODO-6867 (component library), TODO-6868 (browser), TODO-6870 (naplpsdemo, recorded in the NAPLPS renderer's repository since rdm does not list the channel's), TODO-6869 (uicomponentsdemo).
