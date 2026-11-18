# Animation and moving objects in the teletext, ReGIS and NAPLPS renderers

| | |
|---|---|
| **Status** | Specification of 18 November 2026, written while the owner was away, for building at once. The owner's decision is DEC-6524; what this document decides beyond it is listed in section 12 and recorded in rdm as items 17 to 27 of DEC-6525, for the owner's confirmation. |
| **Second form** | Revised on 18 November 2026 with page-rules.md for the owner's decisions DEC-6587 (a rule runs a group of protocol commands; everything local dropped at a disconnect) and DEC-6599 (a sub-page is exactly a page). Section 15 lists every change this document took from them. |
| **Asked for by** | The owner, 18 November 2026, of twenty ideas for animation: "drop 8 11 12 14 18 and DO ALL THE REST OF THE 20 IDEAS CREATE REQUIREMENTS". |
| **Companion** | `page-rules.md` (requirements RULE-n): the rule table, whose actions and collision conditions act on the objects this document defines, and which shares this document's clock. |
| **Repositories it changes** | neoteletext-renderer-teletext (the engine), neoteletext-renderer-regis, neoteletext-renderer-naplps, neoteletext-browser, neoteletext-app-server, neoteletext-server-ts-protocol and neoteletext-server-channels (the kits), and the test channels. |

Requirements are numbered `ANIM-n`, each naming in brackets the repository that implements it. DEC-6524's fifteen items are met as follows:

| DEC-6524 item | Requirement |
|---|---|
| 1 One presentation clock | ANIM-1 |
| 2 Atomic frames | ANIM-2 |
| 3 Double-buffered pages | ANIM-3 |
| 4 Damage-only repaint in every renderer | ANIM-4, ANIM-5 |
| 5 Teletext objects as sprites | ANIM-7, ANIM-8 |
| 6 ReGIS numbered drawings as sprites | ANIM-9, ANIM-10 |
| 7 NAPLPS numbered objects | ANIM-11 |
| 8 Layers and z-order | ANIM-12 |
| 9 Collision and region tests | ANIM-13 (and RULE-19) |
| 10 Frame cycling | ANIM-14 |
| 11 The ReGIS paint rate | ANIM-15 |
| 12 NAPLPS WAIT and BLINK | ANIM-20 |
| 13 An animation budget | ANIM-16 |
| 14 Sprite sheets as page assets | ANIM-17 |
| 15 A timeline in the kits, and image sequences | ANIM-19, ANIM-18 |

Every integer in a record is big-endian. The record frame, the data channel and the page and sub-code fields are those of page-rules.md section 8. Push protocol version 10 (RULE-49) carries everything here; the record types are 23 to 27. **A page, in this document as in page-rules.md, is one page number and one sub-code together** (DEC-6599, RULE-112): every record, message and call here carries both, and nothing belongs to a page number alone.

| Type | Name | Carries | Requirement |
|---|---|---|---|
| 23 | `ANIMATE` | operations on a sub-page's objects | ANIM-6 |
| 24 | `SPRITES` | a teletext sub-page's sprites | ANIM-7 |
| 25 | `NAPLPS_OBJECTS` | a NAPLPS sub-page's objects | ANIM-11 |
| 26 | `SHEET` | bytes of a page's sprite sheet | ANIM-17 |
| 27 | `FRAME` | the beginning or the end of an atomic frame | ANIM-2 |

---

## 1. The clock

**ANIM-1 [engine; neoteletext-renderer-regis; neoteletext-renderer-naplps; neoteletext-browser]. One presentation clock of 60 ticks a second.**
- **Statement.** Every time-driven thing a receiver shows MUST be timed in ticks of one sixtieth of a second on one clock per decoder, the **presentation clock**, whose tick `n` is due `n × 50,000 ÷ 3` microseconds after the decoder started it (RULE-4): teletext flash, the cursor blink, NAPLPS WAIT and BLINK, frame cycling, the ReGIS paint rate, the end of an atomic frame, and the page rule table. The renderers stay without a clock: each is told the tick, or how many ticks have passed. The figures, each a named constant in the crate that uses it:

| What | Today | On the clock | Constant |
|---|---|---|---|
| Ticks a second | — | 60 | `PRESENTATION_TICKS_PER_SECOND`, in `neoteletext_core::consts::timing`; `neoteletext_rules::limits::TICKS_PER_SECOND` is asserted equal where both are linked |
| Teletext Level 1 flash (EN 300 706 clause 12.2, Table 26, the Flash spacing attribute; the engine's decision E.12 and REQ-412: the SAA5050's 960 ms shown and 320 ms hidden, three to one) | 48 fields shown, 16 hidden, of 20 ms | 57 ticks shown (950 ms), 19 hidden (317 ms), which keeps the ratio of three to one exactly: a cycle of 76 ticks, 1.267 seconds | `FLASH_SHOWN_TICKS`, `FLASH_HIDDEN_TICKS` |
| The Additional Flash Functions (EN 300 706 Table 29, column address mode 00111; decision E.48) | 12 units of one twelfth of a second | a unit is 5 ticks; a cycle 60 ticks | `FLASH_UNIT_TICKS` |
| The text cursor's blink and the ReGIS cursor drawing's (REQ-6378) | half period 530 ms | half period 32 ticks, 533 ms | `BLINK_HALF_TICKS`, in the browser's `interface-core` |
| NAPLPS WAIT and BLINK intervals (ANSI X3.110-1983 sections 5.3.2.8 and 5.3.2.7: tenths of a second) | not played | a tenth is 6 ticks | `TENTH_TICKS`, in `naplps::limits` |
| The ReGIS paint rate (DEC-6382: `rate × 100` work units a second) | not built | after `n` ticks, `n × rate × 100 ÷ 60` units, rounded down | `PAINT_RATE_UNIT`, in `regis::limits` |

- A phase is a function of the presentation tick alone, so every page of a channel flashes in step and a page's rule tick 0 falls on a clock tick. The engine's `FIELD_PERIOD_US` remains for acquisition and timeouts and no longer times anything shown. The decoder MUST wake only for ticks at which something is due — the next flash phase a shown page uses, a cycle's next frame, a drawing still painting, a WAIT ending, a held frame's limit, or every tick while the open page has a rule table — and otherwise sleep until it is written to (the browser's decision 47). The trusted core's least interval between a page's frames (`frames::MIN_FRAME_INTERVAL`, 20 ms today) MUST become one tick.
- **Reason and source.** DEC-6524 item 1: animation that is deterministic, synchronised across renderers and replays exactly.
- **Verification.** Engine tests of each flash phase by tick; a decoder test that a page with one slow-flashing cell wakes twice a cycle and not sixty times a second; the image sequences of ANIM-18, which are the same on every run.

## 2. Frames, page swap and damage

**ANIM-2 [engine: neoteletext-web; neoteletext-browser; neoteletext-app-server]. Atomic frames: the FRAME record, type 27.**
- **Statement.** Record type 27, `FRAME`, has a body of 8 bytes: the page (2 bytes); the sub-code (2 bytes); a mark (1 byte: 1 begin, 2 end); a reserved byte, 0; and an identifier (2 bytes, which an end repeats from its begin). Between a begin and its end for a page, the receiver MUST hold, unapplied and in arrival order, everything that changes what that page shows — the page's teletext packets, and its `REGIS`, `NAPLPS`, `DRAWING_LINKS`, `REGIS_CURSOR`, `LINKS`, `RULES`, `ANIMATE`, `SPRITES`, `NAPLPS_OBJECTS` and `SHEET` records — and at the end apply them all, in order, and show the result on one tick: no picture between is ever presented. What is held is the bytes, at most `MAX_FRAME_BYTES` (262,144), never a second raster. Sound records and other pages' packets pass as they arrive. A frame ends, and what it held is applied at once, also when: the limit of bytes is reached; `MAX_FRAME_TICKS` (120, two seconds) pass with no end; a second begin arrives for the page; the page stops being shown; the connection ends. So a fault delays a picture and never loses or hides one. At most `MAX_OPEN_FRAMES` (4) pages have a frame open at once in a decoder; a fifth begin is treated as having no frame.
- In the streams themselves: a ReGIS v2 stream already has its marker, the commit `D(C)`, which ends a frame that began at the first staged operation after the last commit (regis-v2.md, "Commit and repaint"); nothing is added to it. NAPLPS (ANSI X3.110-1983) has no such marker and gets no new opcode: the FRAME record brackets its records. Teletext packets are bracketed the same way.
- The engine's `neoteletext_web::records::frame::OpenFrames` follows which pages have a frame open and ends each by the five early endings above; it holds no bytes itself, and the receiver that holds them asks it.
- **Reason and source.** DEC-6524 item 2.
- **Verification.** Decoder tests: a page's rows and a ReGIS commit inside one frame appear in one presented frame; each of the five early endings applies what was held; fuzz target `frame_records`.

**ANIM-3 [neoteletext-browser; neoteletext-app-server]. Double-buffered pages: a whole page swapped in on one tick.**
- **Statement.** A frame MAY hold a whole new page: a teletext page with the erase bit (C4), a new generation of a ReGIS or NAPLPS stream from offset 0, new sprites, objects, sheet and table. The receiver MUST keep presenting the page as it was until everything held has been applied and the new picture is complete — for a ReGIS or NAPLPS stream, until the new renderer has painted its first whole picture — and then present the new page on one tick. No blank, erased or half-drawn page is presented between. It is the atomic frame applied to a page's model: bytes are held and one picture is replaced by another; no raster is doubled beyond the picture being replaced and the one replacing it. A page larger than `MAX_FRAME_BYTES` cannot be swapped whole and falls back to appearing as it arrives (ANIM-2); the server refuses a `frame` whose content exceeds the limit (ANIM-21), so a program learns of it.
- **Reason and source.** DEC-6524 item 3.
- **Verification.** A decoder test: a new ReGIS generation inside a frame never presents the cleared picture; the image sequence of a swap shows the old page then the new with nothing between.

**ANIM-4 [engine; neoteletext-renderer-naplps]. Damage-only repaint for teletext and NAPLPS.**
- **Statement.** The teletext engine's renderer MUST be able to render only the rectangle of a page that changed since it last rendered that page, and say which rectangle that is: the union, in whole cells, of the cells whose character, attributes, enhancement or flash phase changed and of the cells any sprite covered before or covers now (ANIM-8). The result MUST be, dot for dot, what rendering the whole page gives. The NAPLPS renderer's `Terminal` MUST track the rectangle of pixels written since its caller last took it (`take_damage`), for the stream's own drawing and for its objects (ANIM-11), with the same property. ReGIS has this already (REQ-6329).
- **Reason and source.** DEC-6524 item 4.
- **Verification.** Property tests in each renderer: for random sequences of changes, the damaged rendering equals the whole rendering, and no dot outside the reported rectangle differs. Measured before and after: one flashing cell, and one moved sprite, against a whole page.

**ANIM-5 [neoteletext-browser]. The browser handles only the rectangle that changed, for every renderer.**
- **Statement.** The decoder MUST send, the trusted core check, encode and pass on, and the interface draw and present, only the damaged rectangle of a teletext page and of a NAPLPS picture, as REQ-6399 already requires for a ReGIS picture, on the picture path the three share. The trusted core's frame check holds for a rectangle as for a whole frame: a known page, a rectangle inside the raster, every index inside the palette.
- **Reason and source.** DEC-6524 item 4; DEC-6398 item 4, extended.
- **Verification.** The timed test of RULE-66; a test that a one-cell change sends a frame of one cell's rectangle.

## 3. Objects and their animation state

**ANIM-6 [engine: neoteletext-rules, neoteletext-web; neoteletext-browser]. The animation state, its operations and the ANIMATE record, type 23.**
- **Statement.** For each sub-page shown the receiver MUST keep, for at most `MAX_ANIMATED_OBJECTS` of its objects and controls — 32 on a teletext sub-page, 64 on a ReGIS picture (`MAX_ANIMATED_DRAWINGS`) and 64 on a NAPLPS picture, the figures of ANIM-16's table — an **animation state**, which is the receiver's own and which nothing in a page's stream can read:

| Part | Values | Without it |
|---|---|---|
| shown | shown or hidden | the object's own visibility |
| position | x, y (signed 16-bit), in the renderer's units: cells for a teletext sprite (x the column, y the row), pixels for a ReGIS drawing (as its `X` and `Y` attributes, relative to its parent) and for a NAPLPS object (the top left of its rectangle on the 640 by 480 picture) | the object's own position |
| layer and order | layer 0 to 3 and order −128 to 127 (ANIM-12) | the object's own |
| frame | 0 to 15 (ANIM-14) | frame 0 |
| cycle | first, last, period, once, and the tick it started (ANIM-14) | not cycling |
| forced look | 0 none, 1 hover, 2 pressed, 3 alternative | the pointer decides the look |

- It is changed by **operations**, which are carried by the `ANIMATE` record alone: the server sends one directly, and a group of a page's rule table holds one as a command (RULE-119), the same bytes either way, applied by the same code, and are read by one function of `neoteletext-rules`. Each is a code byte, a target (a kind byte, 1 control or 2 object, and a 16-bit number, not 0) and a body:

| Code | Operation | Body | Applies to |
|---|---|---|---|
| 5 | `show` | none | controls and objects |
| 6 | `hide` | none | controls and objects |
| 7 | `look` | look, 0 to 3 | controls and objects |
| 15 | `move` | flags (bit 0 relative); x; y (signed 16-bit) | objects |
| 16 | `order` | layer (0 to 3, or 255 to keep it); order (signed 8-bit) | objects |
| 17 | `frame` | frame, 0 to 15; also stops a cycle | objects |
| 18 | `cycle` | first; last (`first ≤ last ≤ 15`); period (16-bit, 1 to 3,600 ticks); flags (bit 0 once) | objects |
| 19 | `stop_cycle` | none | objects |
| 20 | `reset` | none: forgets the object's whole animation state. In an `ANIMATE` record only | controls and objects |

- **Why a teletext sub-page holds 32 and the others 64.** A teletext sub-page has at most 32 sprites (`MAX_SPRITES`, ANIM-7), and the engine's core, which is built without allocation for microcontrollers, keeps the states in a fixed array of that many, which the sub-page's sprites and controls share. ReGIS and NAPLPS pictures have up to 64 objects that can move. An operation that would give one object more than the maximum a state does nothing and is counted, as an operation on a target that does not exist is; an object whose state sets nothing (every part back at its own) holds no state and frees its place.
- A relative `move` adds to the position in force, saturating at the signed 16-bit bounds. A hidden control is drawn as spaces whose background is its row's full row colour, and takes no pointer event; a cell a sprite has changed is left as the sprite drew it when a control beneath it is hidden or given a look, because sprites lie over the page. A forced look on a teletext control draws the hover look for 1 and the pressed look for 2 and 3 (the control's two looks, the engine's decision E.127); on a ReGIS drawing, its `H`, `A` and `N` looks (ANIM-10); on a NAPLPS object, its hover, pressed and alternative macros (ANIM-11).
- **The ANIMATE record's body** is: the page (2 bytes); the sub-code (2 bytes, `0x0000` to `0x3F7E`; the first form's `0x3F7F`, "whichever sub-page is shown", is withdrawn by DEC-6599 and refused); a count (1 byte, 1 to 64); a reserved byte, 0; then that many operations. The whole record is applied together, at the tick after it arrives (or at its frame's end), and its effects are seen by rules from the next snapshot (RULE-7).
- **In a group.** An `ANIMATE` record in a group may hold any operation, `reset` among them, and its fields may take amounts (RULE-106): an operation's target number from a row parameter or the firing's target, and the x and y of `move`, the frame, the look, the order and a cycle's period from a constant plus a variable, a row parameter or a value of the firing.
- **Dropped with the page.** The animation state is part of a page's local state (RULE-111): it is dropped when the page is closed or its connection ends, kept while the page is paused, and never replayed by the server.
- **One state, last writer wins.** An `ANIMATE` record, whether the server sent it or a group ran it, and the stream's own change of the same thing all write the same state: a ReGIS commit that sets a drawing's `X` or `Y` forgets that drawing's position in the animation state, `V` its shown part, `L` or `G` its layer and order; a ReGIS deletion, a new stream generation, and a `SPRITES` or `NAPLPS_OBJECTS` record (which replace all of a sub-page's sprites or objects) forget the state of what they remove or replace. An operation on a target that does not exist does nothing and is counted.
- **Reason and source.** DEC-6524 items 5, 6 and 7 (move, show and hide by number without anything sent again); DEC-6522 item 7 (`show`, `hide`, `look`); one state so that the channel and the page's rules never hold two answers.
- **Verification.** Tests in `neoteletext-rules` of each operation and of folding a list of them; decoder tests of last-writer-wins for each renderer; fuzz target `animate_record`.

**ANIM-7 [engine: neoteletext-web, neoteletext-core]. Teletext sprites: the SPRITES record, type 24.**
- **Statement.** A teletext sprite is a numbered placement of teletext objects (EN 300 706 clause 13, "Objects") on a sub-page, which the receiver draws over the page and can move, show, hide, order and cycle. Record type 24, `SPRITES`, gives a sub-page all its sprites, replacing any it had. Its body: the page (2 bytes); the sub-code (2 bytes); a count (1 byte, 0 to `MAX_SPRITES`, 32); a reserved byte, 0; then for each sprite:

| Bytes | Field | Values |
|---|---|---|
| 0–1 | number | 1 to 65,535, distinct within the record |
| 2 | flags | bit 0 shown; bit 1 detectable (pointer triggers see it); other bits 0 |
| 3 | layer | 1 to 3 (layer 0 is the page itself) |
| 4 | order | signed, −128 to 127 |
| 5 | column | signed, −39 to 39: the column of the sprite's origin |
| 6 | row | signed, −24 to 24: its row |
| 7 | width | 1 to 40 cells |
| 8 | height | 1 to 25 cells |
| 9 | frames `F` | 1 to 16 |
| 10– | `F` object references, 2 bytes each | bits 15 to 13 zero; bits 12 and 11 the source (1 a local object of the page's own packets X/26, 2 an object of its Public Object Page, 3 of its Global Public Object Page); bits 10 and 9 the type (1 active, 2 adaptive, 3 passive); bits 8 to 0 the object number N8 to N0 — the fields of an Object Invocation triplet (EN 300 706 Table 28) |

- A sprite moves in whole character cells and is never placed between cells (the owner dropped sub-cell positioning). Its frames are built of what teletext objects hold: characters, mosaics and attributes. A DRCS character an object invokes is not drawn, in a sprite as anywhere (REQ-2196).
- **Reason and source.** DEC-6524 items 5, 10 and 14. Using the standard's own objects means a sprite's shapes are made with what a channel already uses for Level 2.5 pages, and a sprite sheet is an object page.
- **Verification.** Codec tests at each bound; the record's reader refuses a repeated number, a reserved bit and a source of 0.

**ANIM-8 [engine: neoteletext-core]. How a sprite is drawn.**
- **Statement.** After a page's own enhancement data has been processed, at Presentation Level 2.5 or above, the engine MUST draw each shown sprite of the sub-page, in order of layer, then order, then number, by invoking the object of its frame in force exactly as the enhancement processor invokes an object from an Object Invocation triplet whose active position is the sprite's origin (its row and column in the animation state, else the record's); cells the object addresses outside the sprite's width and height from its origin, outside columns 0 to 39, or outside rows 1 to 23 are not written. An object that is absent (its page not received, or its definition not found) draws nothing. Below Level 2.5 sprites are not drawn. The sprite's bounding rectangle is its width and height in cells at its origin, cut to the page, in dots (12 by 20 a cell). The engine keeps the page's own rendering apart from the sprites', so that moving a sprite repaints only the cells it left and the cells it reaches (ANIM-4, ANIM-12). The work is bounded as an object's is today: at most 507 triplets an object, 32 sprites a sub-page.
- **The display planes still rank what is drawn.** Each shown sprite is one more invocation given to the enhancement walk after the page's own data, so the planes of EN 300 706 clause 13.2 hold: a Passive object's cells lie over an Adaptive object's, and those over an Active object's and the page's own, whatever the sprites' layers; layer, order and number decide among objects of the same type, the later invoked on top. A sprite whose frames are Passive objects, the ordinary case, always lies over the page.
- **A sprite's objects count toward the standard's limits with the page's own** (EN 300 706 Annex A.8): at most 127 invocations of each type for a grid, the page's and the sprites' together, so the bound on a grid's work is what it was before sprites. The two limits on nesting at one position start afresh for each sprite.
- **A sprite changes nothing outside its own cells.** Its objects set no Full Screen Colour and no Full Row Colour; an Active object's attributes stop at the sprite's right edge; an enlarged character does not reach past the sprite. Where two sprites lie side by side on one row, the left one's Active attributes can run on into the right one's rectangle, and never outside the union of the sprites' rectangles.
- **The bounding rectangle is cut to the whole page, rows 0 to 24**, though a sprite writes only rows 1 to 23: a sprite placed on row 24 has a rectangle for collision tests and draws nothing.
- **What is rebuilt.** When sprites change, the grid of cells is composed again whole from the page's own grid, which is kept apart and not built again; only the pixels are repainted by damage (ANIM-4).
- **Reason and source.** DEC-6524 item 5.
- **Verification.** Golden images: a sprite of each object type over text and mosaics; clipped at each edge; two overlapping in each order. The damage property test of ANIM-4.

**ANIM-9 [neoteletext-renderer-regis]. ReGIS numbered drawings as sprites.**
- **Statement.** The ReGIS renderer's `Terminal` MUST take, beside the viewer state (regis-v2.md, "Viewer state"), the animation state of ANIM-6 for at most `MAX_ANIMATED_DRAWINGS` (64) numbered drawings: `set_animation(number, state)` and `clear_animation(number)`. Where a part is set it is used in place of the drawing's committed attribute: the position for `X` and `Y`, shown for `V`, the layer for `G` and the order for `L`, the frame for which entry of the frame list is drawn (ANIM-10), the forced look for which look is drawn whatever the pointer does. The picture is, pixel for pixel, the picture of a scene whose committed attributes had those values, and it is made by damage repaint (REQ-6329) under the repaint budget (REQ-6368): no byte of the stream is sent again, and no drawing outside the damaged rectangle is replayed. Like the viewer state, the animation state is the receiver's alone: nothing in the stream can read or set it, and a commit's checks of work and nesting count the dearest of every look and every frame of each drawing, so that no animation state can make a repaint cost more than the commit allowed. `Terminal::bounds(number)` gives a drawing's bounding rectangle on the screen for the state in force (ANIM-13).
- `set_animation` on a drawing that does not exist, and a state for a 65th drawing, are refused and keep nothing. A state that sets nothing is the same as no state and frees its place among the 64. A layer above 3 is taken as 3 and a frame above 15 as 15. Two calls stand beside those named: `Terminal::animation(number)`, which a receiver reads after a commit to learn which parts the stream wrote over (last writer wins), and `Terminal::drawing_position(number)`, the position in force, to which a relative `move` adds.
- **Showing a drawing the stream hid can be refused.** A commit's checks do not count hidden drawings, so the shown part of an animation state could make a repaint cost more than the commit allowed. `set_animation` therefore keeps the rest of the state and drops the shown part, answering false, when the scene would then cost more than `MAX_REBUILD_WORK` (100,000,000 work units); after every commit, shown parts are dropped, highest drawing number first, until the scene fits. A receiver treats a false answer as the operation not having taken effect, and counts it.
- The retained contents of the moved drawing itself are replayed inside the damage; a cache of its pixels is not kept, because a drawing's pixels depend on what lies beneath it (complement and erase writing, regis-v2.md rule 2). Section 12, item 4, records this reading of "without its vectors being ... interpreted again".
- **Reason and source.** DEC-6524 item 6.
- **Verification.** Property test: for random scenes and random animation states, the picture and the pick record equal those of the same scene committed with those attribute values. Measured: moving a 20-pixel drawing, before and after, in work units and time.

**ANIM-10 [neoteletext-renderer-regis]. Four attributes more in the ReGIS v2 stream.**
- **Statement.** `D(S<n>(…))` MUST accept, beside the ten attributes regis-v2.md defines (`X`, `Y`, `L`, `V`, `P`, `R`, `I`, `H`, `A`, `C`), these four, in the same grammar (decimal values, commas between attributes, letters in either case):

| Letter | Attribute | Value | Default |
|---|---|---|---|
| `G` | Layer (group) | 0 to 3 (ANIM-12). It takes effect on a top-level drawing; a child is in its top-level ancestor's layer | 1 |
| `N` | Alternative look | a drawing number, or 0 for none: the drawing drawn in this one's place while the alternative look is forced (ANIM-6), as `H` and `A` are for hover and pressed | 0 |
| `F` | Frame list | `F(<n>,<n>,…)`: 1 to 16 drawing numbers, or `F0` for none. While a drawing has a frame list, the entry numbered by its frame in force (0 without animation state; an entry beyond the list draws the last) is drawn in its place, as a source is | none |
| `T` | Paint rate | 0 to 32,767 (ANIM-15) | 0 |

- The order of precedence for what is drawn in a drawing's place: a forced look; else the pressed look, then the hover look, by the viewer state; else the frame in force; else the source; else its own contents. Looks, frames and sources are all references between drawings: none may form a cycle, in any mixture, and chains of them count toward the nesting cap of 16 (failed-commit codes 3 and 4). A drawing drawn in another's place, as a source, a look or a frame, uses its own frame list and its own source, and does not use its own looks or its own paint rate: the paint rate follows the drawing that placed it. Giving a master a frame by its animation state therefore changes every drawing that names the master. A malformed attribute fails the batch with code 7. `docs/regis-v2.md` gains these in its Attributes and Grammar sections and in "What building changed".
- Examples: `D(S40(G2,F(41,42,43,44)),S41(V0),S42(V0),S43(V0),S44(V0),C)` makes drawing 40 a four-frame sprite on the sprites layer whose frames are the hidden drawings 41 to 44; `D(S10(I1,H11,A12,N13))` gives drawing 10 its three looks; `D(S7(T50))` paints drawing 7 at 5,000 work units a second.
- **Reason and source.** DEC-6524 items 6, 8, 10 and 11; consistent with the letters already taken in `D` (regis-v2.md, "Attributes").
- **Verification.** Lexer and commit tests for each attribute at its bounds; the validator refuses a frame cycle; golden images of each example.

**ANIM-11 [neoteletext-renderer-naplps; engine: neoteletext-web]. The NAPLPS object layer: the NAPLPS_OBJECTS record, type 25.**
- **Statement.** NAPLPS (ANSI X3.110-1983) keeps no scene: a stream draws on the picture and is forgotten. NeoTeletext adds a layer of numbered objects over it, defined by a record and not by any new NAPLPS opcode, so that every stream stays a conforming one. Record type 25, `NAPLPS_OBJECTS`, gives a sub-page all its objects, replacing any it had. Its body: the page (2 bytes); the sub-code (2 bytes); the generation of the NAPLPS stream the objects belong to (2 bytes; objects for another generation than the one shown are kept until that generation is, and dropped when a later one arrives); a count (1 byte, 0 to `MAX_OBJECTS`, 64); a reserved byte, 0; then for each object:

| Bytes | Field | Values |
|---|---|---|
| 0–1 | number | 1 to 65,535, distinct within the record |
| 2 | kind | 1 a macro object, 2 a region |
| 3 | flags | bit 0 shown; bit 1 detectable; other bits 0 |
| 4 | layer | 1 to 3 |
| 5 | order | signed, −128 to 127 |
| 6–7, 8–9 | x, y | signed 16-bit: the top left of the object's rectangle, in the picture's pixels (640 by 480, the origin at the top left, y down) |
| 10–11, 12–13 | width, height | 1 to 640, 1 to 480 |
| 14–15, 16–17 | origin x, origin y | signed 16-bit: where that top left corner lies in the macro's own drawing, in the same pixels; 0 for a region |
| 18 | frames `F` | a macro object: 1 to 16; a region: 0 |
| 19 | cover | a region: the colour-map entry that fills it while it is hidden; a macro object: 0 |
| 20, 21, 22 | hover, pressed and alternative look | each a macro's code, `0x20` to `0x7F`, or 0 for none |
| 23 | reserved | 0 |
| 24– | `F` frame bytes | each a macro's code, `0x20` to `0x7F` (the 96 macro names of ANSI X3.110-1983 section 6.2, codes 2/0 to 7/15) |

- **A macro object** is drawn by executing its frame's macro (or a look's) as the stream last defined it, in a fresh presentation state — the state after a reset of every attribute to its default (as RESET gives, ANSI X3.110-1983 section 5.3.2.9, but touching nothing of the stream's own state) — with every pixel it would write moved by (`x − origin x`, `y − origin y`) and written only inside the object's rectangle. So a macro that draws a figure around the unit screen's point that maps to pixel (origin x, origin y) appears with that point at (x, y). Inside an object's macro these have no effect: SET COLOR's redefinition of the colour map, BLINK, WAIT, RESET, and DEF MACRO, DEFP MACRO, DEFT MACRO, DEF DRCS and DEF TEXTURE; calling another macro, and text in any set including DRCS characters (which the ban of REQ-2196 does not cover), work as in the stream. A macro that is not defined draws nothing.
- **A region** is a rectangle of the stream's own picture. Shown, it changes nothing; hidden, its rectangle is filled with its cover entry on its layer. It exists so that part of an ordinary NAPLPS page can be clicked and covered (DEC-6522 item 11).
- **Picking.** An object is inside a pointer's pixel when it is shown, detectable and the pixel is in its rectangle; where several are, each is (RULE-12). Nothing else of a NAPLPS picture can be picked.
- **The renderer** (`naplps::Terminal`) MUST take the objects (`set_objects`), the animation state (`set_animation`, `clear_animation`) and a second picture the caller owns, into which it composes the stream's picture and the shown objects in order of layer, order and number (`compose`), repainting only damage (ANIM-4); it reports each object's rectangle (`bounds`). Each object's drawing is bounded by `MAX_OBJECT_BYTES` (16,384 bytes processed, macro expansion counted) and by the limits a stream already has (`MAX_MACRO_DEPTH`, `MAX_VERTICES`); past the bound the object's drawing stops.
- **As built.** `compose(background, presented)` takes two pictures of one size, the stream's and the one composed into, since the caller owns both. The fresh presentation state is the power-up state: default attributes, colour mode 0 drawing in white, and the power-up code sets, so a macro that draws in the 7-bit form begins with SO. A definition inside an object's macro is read as a definition and dropped: nothing is stored. Inside an object's macro, SET COLOR in colour mode 0 draws with the nearest existing colour-map entry and allocates none, BLINK START and BLINK STOP are ignored as BLINK is, and BEL and the limit report no event. An object's macro cannot read the picture: a scroll inside it brings in blanks, which is what makes the damage property of ANIM-4 exact.
- **A region may have looks.** A shown region whose look in force has a macro draws that macro, moved to the region's top left corner and clipped to it; otherwise a shown region draws nothing.
- **Layer 0 in the animation state.** An object the animation state puts in layer 0 is still composed over the stream's picture, before every object of layers 1 to 3; it is never drawn into the stream's own picture.
- **The pointer's look** is given by the caller with `Terminal::set_pointer_look(number, look)`, kept apart from the animation state: `clear_animation` and the `reset` operation do not forget it, and `set_objects` does. A look the object has no macro for leaves the frame in force.
- **Checks.** `set_objects` refuses a whole set in which any field is outside this table's ranges; a region has origin 0 and no frames, and a macro object cover 0. The renderer keeps no cycle and holds no pixel budget: the caller sets the frame each tick and reads how much is waiting to be composed before it composes.
- **Reason and source.** DEC-6524 item 7; DEC-6522 item 11. A record keeps the stream conforming; a search of the standard found no command that names and retains a drawing other than the macro, which is why the macro is the object's content.
- **Verification.** Codec tests; renderer tests: an object at two positions gives the same pixels moved; a hidden region is its cover; the ignored commands change nothing of the stream's state; the damage property; fuzz target `naplps_objects`.

## 4. Layers, rectangles and frames

**ANIM-12 [engine; neoteletext-renderer-regis; neoteletext-renderer-naplps]. Four layers and an order within each.**
- **Statement.** Every page has exactly `LAYERS` (4) layers, drawn in this order, each renderer naming the constant in its `limits`:

| Layer | Name | What is in it |
|---|---|---|
| 0 | background | the page's own picture: the teletext page with its enhancements; the ReGIS base and every top-level drawing with `G0`; the NAPLPS stream's picture |
| 1 | scene | objects that seldom move |
| 2 | sprites | objects that move |
| 3 | overlay | what must lie over everything: a cursor, a pointer's mark, a caption |

- Within a layer, objects are drawn by order, lowest first, then by number. For a ReGIS drawing the order is its depth `L` among top-level drawings of its layer (children keep the rule of regis-v2.md within their parent), and the `order` operation sets it. Each renderer MUST keep the background as a raster of its own, repainted only when the background's own content changes, and compose layers 1 to 3 over a copy of it into the presented picture, so that a moving object never causes the background to be drawn again: the damaged rectangle is filled by copying the background's pixels, and only the objects of layers 1 to 3 that reach into it are replayed. That is one background raster and one presented picture a page (the ReGIS renderer keeps its v1 base beside them).
- In the teletext engine this holds for pixels: the page's own grid of cells is kept and not built again, the composed grid is built again whole when sprites change, and only the cells that differ are drawn.
- **Reason and source.** DEC-6524 item 8: a small fixed number of layers, composited separately.
- **Verification.** Golden images of the same objects in each layer and order; a counter test that moving a layer-2 object over a costly `G0` drawing replays none of that drawing's contents.

**ANIM-13 [engine; neoteletext-renderer-regis; neoteletext-renderer-naplps; neoteletext-browser]. Bounding rectangles, for collision and region tests.**
- **Statement.** Each renderer MUST report, for an object as its state stands, one bounding rectangle in the picture's pixels, or none while the object does not exist or is not shown: a teletext sprite's cells (ANIM-8); a ReGIS drawing's reach as measured at its commit (regis-v2.md, "Commit and repaint": the rectangle of every position its contents write) with that of its shown children, of the look or frame in force, moved to its screen position and cut by its clip rectangles and the screen; a NAPLPS object's rectangle. The decoder gives these to the rule evaluator for `overlaps`, `inside` and pointer triggers (RULE-12, RULE-19) through the evaluator's `World`. The tests are on these rectangles and never on pixels.
- A teletext sprite's rectangle is cut to the page's rows 0 to 24 (ANIM-8). A NAPLPS object's is cut to the picture of 640 by 480, and is none when the object lies wholly outside. A ReGIS drawing that is still being painted gradually (ANIM-15) has the rectangle it will have when finished, so that collisions do not change as it appears.
- **Reason and source.** DEC-6524 item 9.
- **Verification.** Renderer tests of each rectangle against the pixels actually written (every written pixel lies inside); the rule tests of RULE-19.

**ANIM-14 [engine: neoteletext-rules; all three renderers]. Frame cycling.**
- **Statement.** An object with more than one frame — a teletext sprite's object references, a ReGIS drawing's frame list, a NAPLPS object's macros — shows the frame in force. A `cycle` operation (ANIM-6) makes the receiver change it by itself: with `s` the tick the cycle started (the tick after the operation ran), `p` its period and `c = last − first + 1`, the frame at tick `t` is `first + ((t − s) ÷ p) mod c`; with `once`, it is `min(first + (t − s) ÷ p, last)` and the cycle ends when `last` is reached. At most `MAX_CYCLING_OBJECTS` (16) objects of a page cycle at once, and a 17th `cycle` does nothing and is counted. An object has at most `MAX_OBJECT_FRAMES` (16) frames; a frame number beyond an object's frames shows its last. Cycles run on the presentation clock whether or not the page has a rule table. In teletext the frames are objects of characters and mosaics, never DRCS (REQ-2196); in NAPLPS a frame's macro may draw DRCS characters; in ReGIS a frame is a drawing.
- **Reason and source.** DEC-6524 item 10.
- **Verification.** Evaluator tests of both formulas at their edges; an image sequence of a four-frame cycle for each renderer.

**ANIM-15 [neoteletext-renderer-regis; neoteletext-browser]. The ReGIS paint rate.**
- **Statement.** DEC-6382's design is built as written: the attribute `T<rate>` (ANIM-10), 0 for at once, else the drawing's own contents (or the source, look or frame drawn in its place) are painted gradually at `rate × 100` work units a second; painting starts at the commit in which the drawing's contents are defined or redefined, in which it is given a rate, or in which it becomes visible, and not at a commit that only moves, re-parents, clips or reorders it; a child of a drawing still painting waits for it; the finished picture is exactly the picture painted at once; the pick record follows the pixels painted so far; filled areas and characters are paid for whole and appear at once when their cost has been earned. The time comes from the receiver on the presentation clock: `Terminal::advance_ticks(n)` adds the allowance of ANIM-1 (`n × rate × 100 ÷ 60`, computed from the total of ticks so that nothing is lost to rounding) and answers whether anything is still painting. Each step is a damage repaint under the repaint budget and the animation budget. The browser MUST have a setting, "Paint drawings gradually", on by default, which when off makes every drawing appear at once and every NAPLPS WAIT pass without delay (ANIM-20). A showing or hiding of a drawing by the animation state starts its painting as a commit that made it visible does.
- **What the rate pays for.** Everything the contents cost except the 64 work units a repaint counts for each byte of contents replayed: the pixels of lines and curves, the areas of fills and characters, 4 units a degree of arc, and 64 units for each byte a macrograph call expands to. So `T1` is a pen moving 100 pixels a second, as DEC-6382 says, and a short line does not wait for its own bytes.
- **"Given a rate" means the rate changes.** A commit that sets the rate a drawing already has does not start its painting again; one that changes it, from 0 too, does. To play a painting again an author defines the contents again, or hides and shows the drawing.
- **Children start with their parent.** When a drawing's painting starts, the painting of every drawing with a paint rate below it starts too, whether or not it had finished before.
- **Reason and source.** DEC-6382, accepted by DEC-6524 item 11.
- **Verification.** Renderer tests: the picture after `k` ticks holds exactly the pixels the allowance buys; the final picture equals the picture at once; the pick record at each step. An image sequence of a drawing with two children.

**ANIM-16 [engine; neoteletext-renderer-regis; neoteletext-renderer-naplps; neoteletext-browser]. The animation budget.**
- **Statement.** Beside the repaint budget (REQ-6368), each renderer's `limits` MUST define these maximums, and the decoder MUST hold a page to them:

| Constant | Teletext (`neoteletext_core::limits`) | ReGIS (`regis::limits`) | NAPLPS (`naplps::limits`) |
|---|---|---|---|
| `LAYERS` | 4 | 4 | 4 |
| Objects a sub-page | `MAX_SPRITES` 32 | the existing drawing limits | `MAX_OBJECTS` 64 |
| `MAX_ANIMATED_OBJECTS` (`MAX_ANIMATED_DRAWINGS` in ReGIS): objects holding animation state at once | 32 | 64 | 64 |
| `MAX_CYCLING_OBJECTS` | 16 | 16 | 16 |
| `MAX_OBJECT_FRAMES` | 16 | 16 | 16 |
| `MAX_ANIMATION_PIXELS_PER_TICK`: pixels repainted for animation in one tick | 120,000 dots (half a page of 480 by 500) | 192,000 (half a picture of 800 by 480) | 153,600 (half of 640 by 480) |
| Work for animation in one tick | — | `ANIMATION_WORK_PER_TICK`: 3,333,333 work units, a sixtieth of `REPAINT_WORK_PER_SECOND`, taken from the same budget | `MAX_OBJECT_BYTES` 16,384 an object's drawing |

- and `neoteletext-web` defines `MAX_FRAME_BYTES` 262,144, `MAX_FRAME_TICKS` 120, `MAX_OPEN_FRAMES` 4 and `MAX_SHEET_BYTES` 65,536. When a tick's animation would pass a budget, the receiver MUST slow the animation and nothing else: every operation still changes the state at once (so rules and the state query see it), but the painting waits, damage merging into one rectangle that is painted in the next tick with budget; a cycle's frames whose turn passes unpainted are skipped; a painting drawing paints later. The viewer's input, the evaluation of rules, sound and the reports to the channel are never delayed by it. The receiver reports fault 8 (RULE-48). A record that defines more than a maximum is refused whole by its reader, and by the server before it is sent.
- **Reason and source.** DEC-6524 item 13: over the budget the receiver slows the animation, never the viewer's input.
- **Verification.** Decoder tests: 64 objects moving each tick paint within the budget each tick and reach their final places; a key pressed during the overload fires its rule in the next tick; each constant's refusal test.

**ANIM-17 [engine: neoteletext-web; neoteletext-browser; neoteletext-app-server]. Sprite sheets as page assets: the SHEET record, type 26.**
- **Statement.** A page's sprite frames are sent once for that page — that page number and sub-code — and named by number afterwards. A sheet belongs to one page and is never shared with another sub-code of the same page number (DEC-6599): a program that wants the same sheet on several sends it to each.
  - **Teletext.** The sheet is the page's objects: its own local objects, and the object pages it links (EN 300 706 clause 13 and clause 10.5: the Public and Global Public Object Pages named by the page's packets X/27/4 or its magazine's Magazine Organization Table). They are ordinary pages of the channel. The server MUST send a connection the object pages a selected page links, once for the connection, before the page.
  - **ReGIS and NAPLPS.** Record type 26, `SHEET`, carries bytes of a page's sheet, in the REGIS record's form: the page (2 bytes); the sub-code (2 bytes); a kind (1 byte: 1 ReGIS, 2 NAPLPS); a reserved byte, 0; a generation (2 bytes); an offset (4 bytes); and data, at most 8,172 bytes. A sheet is one stream of at most `MAX_SHEET_BYTES` (65,536) for a page and kind; a new generation starts it again. The receiver MUST keep the page's sheet while that page is selected, feed it to the renderer it makes for that page before the page's own stream, and drop it with the rest of the page's local state (RULE-111). A ReGIS sheet defines hidden drawings (masters) and ends with a commit; the page's stream names them as sources, looks and frames. A NAPLPS sheet defines macros, DRCS characters and textures; the page's stream and objects call them. A new generation of a sheet makes the receiver start the page's renderer again from the new sheet. A sheet draws nothing itself: a ReGIS sheet's drawings that are left visible, and anything a NAPLPS sheet draws on the picture, are a fault the server refuses (`invalid_sheet`).
- **When the server sends a sheet.** The server sends a connection a page's ReGIS and NAPLPS sheets at each selection of the page, as a new stream from their start, since it cannot know that a receiver kept the sheet of a page it left. A sheet is one stream for each connection and kind; the renderer reads the whole sheet so far at every `sprite_sheet` message, and a ReGIS commit that fails, or NAPLPS that changes a pixel, is `invalid_sheet`. A page's ReGIS stream is checked after that page's ReGIS sheet. A new ReGIS sheet makes the server forget the connection's ReGIS stream of that page, so the program begins that stream again.
- **Reason and source.** DEC-6524 item 14.
- **Verification.** Decoder tests: a sheet sent for one sub-code is not fed to another sub-code of the same page number; a new stream generation keeps the sheet; a page left drops its sheet; the server's refusals.

## 5. NAPLPS WAIT and BLINK

**ANIM-20 [neoteletext-browser; neoteletext-renderer-naplps]. WAIT and BLINK are played on the clock, under a time budget.**
- **Statement.** **WAIT** (ANSI X3.110-1983 section 5.3.2.8: pause for an interval in tenths of a second before what follows is executed). The renderer already returns it as an event and keeps no clock. The decoder MUST play it: on a WAIT of `w` tenths it stops feeding that stream's bytes to the renderer for `6 × w` ticks, presents the picture as it stands, and then goes on. Bytes that arrive meanwhile are held, at most `MAX_WAIT_HELD_BYTES` (262,144); when more arrive the wait ends at once. A stream's waits together are played for at most `WAIT_BUDGET_TICKS` (3,600, one minute) in a generation; after that each WAIT passes without delay. A WAIT does not hold the page's other records, its sound or its rule table. With the viewer's setting "Paint drawings gradually" off (ANIM-15), no WAIT delays anything.
- **BLINK** (section 5.3.2.7: a colour-map entry takes another's colour for an ON interval and its own for an OFF interval, in tenths of a second, with a start delay; at most `MAX_BLINKS`, 32, processes). The decoder MUST play it by the colour map alone: at each tick at which some process changes phase, it takes the renderer's colour map for that time (`Palette::at`, given tenths as ticks ÷ 6 from the tick the first process was defined) and presents the picture's palette changed, with no pixel repainted. The intervals fall on tick boundaries. Blinking continues while the page is shown.
- Both constants are defined once, in `naplps::limits`, with `TENTH_TICKS`.
- The playing itself is written once, as `naplps::Player` in the renderer's library, without a clock or any input or output of its own and told the ticks, because `naplps-render` needs the same logic for its image sequences (ANIM-18); the decoder uses it.
- **Reason and source.** DEC-6524 item 12; TODO-6409 item 2 (a decoder clock for NAPLPS animation), which this settles.
- **Verification.** Decoder tests with a scripted clock: a WAIT of 5 tenths shows the earlier picture for 30 ticks; the budget; the overflow; a BLINK of 5 on, 5 off changes the palette every 30 ticks and sends no pixels. An image sequence of a historical animated page.

## 6. The program protocol's messages (version 15)

**ANIM-21 [neoteletext-app-server]. The messages.**
- **Statement.** Program protocol 14 (RULE-34) MUST gain these program messages, each with `connections`, a `page` and, where stated, a `sub`, in the conventions of page-rules.md section 7:

```json
{"type":"frame","connections":"all","page":"150","sub":"0001","mark":"begin"}
{"type":"frame","connections":"all","page":"150","sub":"0001","mark":"end"}

{"type":"animate","connections":"all","page":"150","sub":"0001","ops":[
  {"action":"move","target":{"object":10},"x":120,"y":80,"relative":false},
  {"action":"cycle","target":{"object":10},"first":0,"last":3,"period":6,"once":false},
  {"action":"hide","target":{"object":20}},
  {"action":"reset","target":{"object":21}}]}

{"type":"sprites","connections":"all","page":"160","sub":"0001","sprites":[
  {"number":1,"shown":true,"detectable":false,"layer":2,"order":0,"column":10,"row":5,"width":4,"height":3,
   "frames":[{"source":"local","kind":"passive","number":0},{"source":"local","kind":"passive","number":1}]}]}

{"type":"naplps_objects","connections":"all","page":"170","sub":"0001","objects":[
  {"number":1,"kind":"macro","shown":true,"detectable":true,"layer":2,"order":0,
   "x":300,"y":200,"width":64,"height":64,"origin_x":0,"origin_y":416,
   "frames":[32,33],"cover":null,"hover":34,"pressed":null,"alternative":null},
  {"number":2,"kind":"region","shown":true,"detectable":true,"layer":1,"order":0,
   "x":0,"y":440,"width":640,"height":40,"origin_x":0,"origin_y":0,
   "frames":[],"cover":0,"hover":null,"pressed":null,"alternative":null}]}

{"type":"sprite_sheet","connections":"all","page":"150","sub":"0001","kind":"regis","data":"RChCNDEp…","restart":true}

{"type":"timeline","connections":"all","page":"150","sub":"0001","id":1,"loop_ticks":null,"steps":[
  {"tick":0,"ops":[{"action":"show","target":{"object":10}}]},
  {"tick":30,"ops":[{"action":"move","target":{"object":10},"x":8,"y":0,"relative":true}]}]}
{"type":"timeline_stop","connections":"all","page":"150","sub":"0001","id":1}
```

- `ops` holds 1 to 64 operations `show`, `hide`, `look`, `move`, `order`, `frame`, `cycle`, `stop_cycle` and `reset`, each an object tagged by `action` with a `target` (`{"control":n}` or `{"object":n}`) and the operation's fields of ANIM-6 (`look`: `normal`, `hover`, `pressed` or `alternative`; `x`, `y`, `relative`; `layer`, `order`; `frame`; `first`, `last`, `period`, `once`); the same `animate` message, without its `connections`, `page` and `sub`, is a command of a rule table's group (RULE-35). `sprites` holds 0 to 32 sprites and `naplps_objects` 0 to 64 objects, with the fields and ranges of ANIM-7 and ANIM-11 (`source` is `local`, `public` or `global`; a sprite's `kind` is `active`, `adaptive` or `passive`; an object's is `macro` or `region`). `sprite_sheet`'s `data` is Base64 of the next bytes of the sheet, and `restart` starts a new generation. A `timeline` holds 1 to `MAX_TIMELINE_STEPS` (1,024) steps in ascending `tick` (0 to 216,000); the **server** plays it, sending each step's `ANIMATE` record when its tick is due on the server's clock, counted from the message's arrival at `1,000 ÷ 60` milliseconds a tick, and again from the start every `loop_ticks` when that is given; `id` (1 to 65,535) names it for `timeline_stop`, and a new timeline with a playing one's `id` replaces it. A program has at most 16 timelines playing for a page.
- **Audiences.** As for `rules` (RULE-40), an audience is the connections open when the message arrives: `sprites`, `naplps_objects`, `sprite_sheet`, `animate` and `timeline` sent to `"all"` reach no connection that opens afterwards.
- **Frames are held by the server.** From a `frame` begin to its end the server holds, for each connection, everything it would send that changes what the frame's page shows, and at the end sends the begin's FRAME record, what it held and the end's FRAME record in one message; sound records and other pages' packets pass as they arrive. The server ends a frame that is not ended within `MAX_FRAME_TICKS` (two seconds) and one that is open when its program ends; a selection of another page drops it. A begin goes to the connections named that show the sub-page.
- **Timelines are played for each connection** of the audience, counted from the message's arrival: `id` names a timeline within one connection and page, so a program may play the same `id` for two viewers at different times. At most 16 play for one connection and page, and at most 64 for one connection over all its pages. A step's tick `n` is due at the first millisecond at or after `n × 50,000 ÷ 3` microseconds. Steps are in strictly ascending order of `tick`, and with `loop_ticks` every step's tick is below it. A host that slept through several turns of a looping timeline sends one turn's steps and goes on at the next turn, in step with its start. A timeline keeps playing, into the state kept for a later viewer, while its connection shows another page.
- **NAPLPS objects and their stream's generation.** A `naplps_objects` message is written for the generation of the NAPLPS stream the connection has for the sub-page, or, when it has none, for the generation its next `naplps` message with `restart` will begin; so a program sends `naplps` with `restart` before the objects of that stream when the connection already has a stream of the sub-page.
- **The server keeps nothing for a late viewer.** Withdrawn: the first form's keeping, for each connection and page, of the newest `sprites`, `naplps_objects`, sheet and folded animation state, and its sending of them at each selection. By DEC-6587 items 3 and 9 and RULE-40 and RULE-111 of page-rules.md, the server holds no animation state, sprites, objects or sheet for a viewer who selects the page later, returns to it or reconnects: a program is told of every selection (`selected`, with `page` and `sub`) and sends the page's sheet, definitions and opening operations then, and a page's opening state is what its program sends. A timeline is played for the connections that have the page selected when it is sent; it ends for a connection that leaves the page or whose connection ends, and for every connection when the program's connection ends.
- **Refusals.** Beside the existing rules: `frame_order` (an end with no begin, a begin inside a frame, a program that ends with a frame open — the server then sends the end itself); `frame_too_large` (the frame's records pass `MAX_FRAME_BYTES`; the server sends what it holds as an unframed page); `invalid_animation` (an operation outside its range, or on "any"); `invalid_sprites`; `invalid_naplps_objects`; `invalid_sheet`; `sheet_too_large`; `too_many_timelines`; `not_ascending` (a timeline's steps not in strictly ascending order of `tick`). Each record is checked with the engine's own reader before it is sent, and a ReGIS sheet and stream with the ReGIS renderer's validator, as ReGIS is today.
- **Reason and source.** DEC-6524 "new messages in the program protocol"; DEC-6462 (the server plays the timeline, so the kits hold no scheduler).
- **Verification.** Server tests: the record built from each example; each refusal; a viewer who selects the page later is sent nothing that was kept; a timeline ends for a connection that leaves the page; a timeline's records at their times against a scripted clock.

## 7. The kits

**ANIM-19 [neoteletext-server-ts-protocol; neoteletext-server-channels]. The calls and the timeline.**
- **Statement.** Both kits MUST offer these, as thin calls that build and send ANIM-21's messages, the Python names the snake_case of the TypeScript, and list them in `kit-calls.tsv`:

```ts
// TypeScript
context.frame(to: Audience, page: number, sub: number, body: () => void): void;   // begin, body's sends, end
context.animate(to: Audience, page: number, sub: number, ops: readonly AnimationOp[]): void;
context.sprites(to: Audience, page: number, sub: number, sprites: readonly Sprite[]): void;
context.naplpsObjects(to: Audience, page: number, sub: number, objects: readonly NaplpsObject[]): void;
context.spriteSheet(to: Audience, page: number, sub: number, kind: "regis" | "naplps", data: string | Uint8Array, restart?: boolean): void;
context.playTimeline(to: Audience, page: number, sub: number, timeline: Timeline, id?: number): number;  // returns the id
context.stopTimeline(to: Audience, page: number, sub: number, id: number): void;

class Timeline {
  constructor(options?: { loopTicks?: number });
  at(tick: number): TimelineStep;        // a step at an absolute tick
  then(ticks: number): TimelineStep;     // a step that many ticks after the last step made
  readonly steps: readonly { tick: number; ops: readonly AnimationOp[] }[];
}
interface TimelineStep {
  move(object: number, x: number, y: number, relative?: boolean): TimelineStep;
  show(object: number): TimelineStep;
  hide(object: number): TimelineStep;
  look(object: number, look: "normal" | "hover" | "pressed" | "alternative"): TimelineStep;
  order(object: number, layer: number | null, order: number): TimelineStep;
  frame(object: number, frame: number): TimelineStep;
  cycle(object: number, first: number, last: number, period: number, once?: boolean): TimelineStep;
  stopCycle(object: number): TimelineStep;
  reset(object: number): TimelineStep;
}
```

```python
# Python
app.frame(to, page, sub)                      # a context manager: with app.frame(to, page, sub): ...
app.animate(to, page, sub, ops)
app.sprites(to, page, sub, sprites)
app.naplps_objects(to, page, sub, objects)
app.sprite_sheet(to, page, sub, kind, data, restart=False)
app.play_timeline(to, page, sub, timeline, id=None) -> int
app.stop_timeline(to, page, sub, id)

class Timeline:
    def __init__(self, *, loop_ticks: int | None = None) -> None: ...
    def at(self, tick: int) -> "TimelineStep": ...
    def then(self, ticks: int) -> "TimelineStep": ...
    steps: list[dict]
class TimelineStep:   # each method returns the step
    def move(self, object: int, x: int, y: int, relative: bool = False) -> "TimelineStep": ...
    def show(self, object: int) -> "TimelineStep": ...
    def hide(self, object: int) -> "TimelineStep": ...
    def look(self, object: int, look: str) -> "TimelineStep": ...
    def order(self, object: int, layer: int | None, order: int) -> "TimelineStep": ...
    def frame(self, object: int, frame: int) -> "TimelineStep": ...
    def cycle(self, object: int, first: int, last: int, period: int, once: bool = False) -> "TimelineStep": ...
    def stop_cycle(self, object: int) -> "TimelineStep": ...
    def reset(self, object: int) -> "TimelineStep": ...
```

- `Timeline` only gathers steps into the `timeline` message's `steps`; it sorts them by tick, joins steps of one tick, and holds no clock: the server plays it (ANIM-21). The types `AnimationOp`, `Sprite` and `NaplpsObject` are generated from the schema. For animation that must be exact to the tick and answer the viewer at once, an author writes rules with `after` and `every` triggers and animation actions (page-rules.md), which the receiver runs; the timeline is for motion the channel directs. Each kit's test harness records the messages a timeline would send.
- **A sheet's text is written a byte a character.** `spriteSheet` (`sprite_sheet`) takes text or bytes. Text is written as Latin-1 (ISO 8859-1): each character is the one byte of its code point, 0 to 255, exactly as each kit's `regis` call writes ReGIS text, because ReGIS is ASCII with eight-bit characters in its strings and that is what a renderer reads. It is never written as UTF-8, which would send two bytes for every character above 127. Bytes given as bytes are sent as they are. Both kits MUST send the same bytes for the same text.
- **The builder, as built.** `Timeline.steps` leaves out a step that was given no operation, since the schema takes no step without one, though `then` still counts from it. The TypeScript `Timeline` has a public read-only `loopTicks`, and its `then` throws a `TypeError` when it is called with anything but a number, because JavaScript takes an object with a callable `then` for a promise and would otherwise call it when a timeline is awaited. `playTimeline` without an `id` takes the next of a count the kit keeps for the whole channel, 1 to 65,535 and then 1 again; an `id` the program gives is used and not counted, and the kit keeps no list of the timelines playing.
- **Reason and source.** DEC-6524 item 15; DEC-6462.
- **Verification.** Each kit's interface test against `kit-calls.tsv`; a shared fixture of timelines and the `timeline` messages they must produce, checked by both kits; a test in each kit that a sheet's text with a character above 127 is written a byte a character.

## 8. Image sequences

**ANIM-18 [engine: neoteletext-cli; neoteletext-renderer-regis; neoteletext-renderer-naplps]. A mode that plays a page's animation into a sequence of images.**
- **Statement.** `neottx` (for a teletext page), `regis-render` and `naplps-render` MUST each gain a mode that plays a page for a stated number of ticks and writes images, for tests and golden files. The options are the same in all three:

| Option | Meaning |
|---|---|
| `--frames <ticks>` | play this many ticks, 1 to 36,000, from tick 0: ticks 0 to `<ticks>` less one, the last of which is always written |
| `--frame-step <k>` | write an image every `k` ticks (default 1), and always the last |
| `--script <file>` | a text file of timed operations, one a line: `<tick> <operation>`, in ascending tick. The operations are ANIM-6's, written `move <n> <x> <y> [relative]`, `show <n>`, `hide <n>`, `look <n> <0-3>`, `order <n> <layer|keep> <order>`, `frame <n> <f>`, `cycle <n> <first> <last> <period> [once]`, `stop_cycle <n>`, `reset <n>`; and `record <type> <hexadecimal body>` for a record applied at that tick (`neottx` only: `ANIMATE`, `SPRITES`, `FRAME`). `-` reads standard input. An empty line and a line that begins with `#` are skipped. A target `<n>` is an object; `neottx` also reads `control:<n>`, since a teletext page numbers its controls apart from its objects. A cycle's operation at tick `t` first changes the frame at tick `t + 1 + period` (ANIM-14, with `s = t + 1`) |
| the output path | each image is written with `-NNNNN`, the tick in five digits, before its extension |

- In `neottx` a `record` is named `ANIMATE`, `SPRITES` or `FRAME`, or by its type number; one for another page or sub-page is ignored; a FRAME record holds the `record` lines after it, and the script's own operations are the receiver's and are never held. `naplps-render` takes `--objects <file>`, a text file of one object a line, because a NAPLPS page's objects come in a record the engine reads and `record` lines are `neottx`'s alone; it refuses a `record` line.
- `neottx` also gains `neottx rules-run <table> <inputs>`: it evaluates a page rule table (the RULES record's body, in bytes or as hexadecimal text; the `rules` message's JSON is not read, because turning its names into numbers is the server's work, RULE-36) with `neoteletext-rules` against a file of timed inputs (`<tick> key down|up char|name|physical <key>`, `<tick> pointer <x> <y> <buttons>`, `<tick> level <audio channel> <0-255>`, `<tick> rectangle <n> <x> <y> <width> <height>` for an object's bounds), and writes the operations each tick's actions produce in the `--script` form, and its reports and MIDI messages as comment lines. Its output is the script for any of the three programs, so a rule-driven page of any renderer can be played into images without the browser. The renderers' programs keep no dependency: they read operations, never tables. `rules-run` takes two options more: `--frames`, how many ticks to evaluate (by default to the tick after the last input), and `--picture teletext|regis|naplps`, which sets the picture's size and how far one unit of a `move` carries a rectangle (a cell of 12 by 20 dots, or a pixel). With no renderer present, every control and object a table names is taken to exist, an object has the rectangle the inputs last gave it, moved with it, and every audio channel answers as holding a local sound, so that MIDI messages are written and not skipped.
- The images of a run are the same on every machine and every run. Golden sequences carry a format version (DEVELOPMENT.md section 8).
- **Reason and source.** DEC-6524 item 15.
- **Verification.** Each program's test plays a fixture twice and compares; the golden sequences named in ANIM-8, ANIM-10, ANIM-14, ANIM-15 and ANIM-20, and the music player's (RULE-92).

## 9. The browser

**ANIM-22 [neoteletext-browser]. The decoder is the compositor; the rest of the browser passes rectangles.**
- **Statement.** The decoder MUST: keep the presentation clock (ANIM-1); read the five records and hold frames (ANIM-2, ANIM-3); keep each shown sub-page's animation state and give it to the renderer of that sub-page (the engine's sprite list, `regis::Terminal::set_animation`, `naplps::Terminal::set_animation`); advance cycles, the paint rate, WAIT and BLINK on the clock; hold the animation budget (ANIM-16); and send only damaged rectangles (ANIM-5). The trusted core and the interface gain no knowledge of objects: they check, pass and draw rectangles of pictures as they do today, at most one frame a tick for each of the three clocks of a page (content, look, answer). Receiver-side animation is thereby allowed on every kind of page, as DEC-6398 is amended to say; what DEC-6398 still forbids — drawing a guess of what a key will do before the page or its rules say — stays forbidden: every pixel the browser draws is the page's stream, the page's objects or the page's rule table.
- **Reason and source.** DEC-6524, "the browser's compositor" and "the conflict resolved".
- **Verification.** The decoder tests named above; the existing hostile-interface and frame-check tests, extended to rectangles of teletext and NAPLPS frames.

## 10. Verification and fuzzing

**ANIM-23 [every repository named]. Tests and fuzz targets.**
- **Statement.** Each requirement above lists its tests, and each test names its `ANIM-n` and the rdm requirement that carries it. These fuzz targets MUST exist, each replaying first every input that found a fault: `animate_record`, `sprites_record`, `naplps_objects_record`, `sheet_record` and `frame_records` in the engine (each reader accepts only what its writer can write, and a decoder model given any sequence of them and of ticks never holds more than its limits or presents inside a frame); `regis_animation` in the ReGIS renderer (any stream with any sequence of animation states and ticks: the picture equals the whole rebuild, work stays under the caps); `naplps_objects` in the NAPLPS renderer (any stream, objects and states: no panic, damage holds, object drawing bounded); `animation_json` in the server (any JSON line as one of ANIM-21's messages is refused or encodes to records the engine accepts). neoteletext-common's `wire-vectors.tsv` gains one vector of each of the five records.
- **Verification.** The full gates.

## 11. Which repository implements what

| Repository | Implements |
|---|---|
| neoteletext-renderer-teletext (the engine) | ANIM-1 (constants, flash by tick), ANIM-2 and ANIM-17 (record codecs), ANIM-4 (teletext damage), ANIM-6 (operations in `neoteletext-rules`; the `ANIMATE` codec), ANIM-7, ANIM-8, ANIM-12 to ANIM-14 and ANIM-16 for teletext, ANIM-18 (`neottx`), ANIM-23 |
| neoteletext-renderer-regis | ANIM-1 (ticks), ANIM-9, ANIM-10, ANIM-12 to ANIM-16 for ReGIS, ANIM-17 (a sheet is ordinary stream bytes), ANIM-18 (`regis-render`), `docs/regis-v2.md` |
| neoteletext-renderer-naplps | ANIM-1 (ticks), ANIM-4, ANIM-11, ANIM-12 to ANIM-14 and ANIM-16 for NAPLPS, ANIM-18 (`naplps-render`), ANIM-20's constants |
| neoteletext-browser | ANIM-1 (the clock, the wakes, the frame interval), ANIM-2, ANIM-3, ANIM-5, ANIM-15's setting, ANIM-16, ANIM-17, ANIM-20, ANIM-22 |
| neoteletext-app-server | ANIM-2, ANIM-3 and ANIM-17 (sending), ANIM-21 |
| neoteletext-server-ts-protocol, neoteletext-server-channels (Python kit) | ANIM-19 |
| the test channels (`regisdemo`, `naplpsdemo`, `demosite`) | a page showing each mechanism, as REQ-6381 asked for each ReGIS feature |

## 12. What this document decided without the owner

Recorded in rdm as items 17 to 27 of DEC-6525, the one decision awaiting the owner.

17. **Teletext flash on the 60-tick clock**: Level 1 flash 57 ticks shown and 19 hidden (the three-to-one ratio of decision E.12 kept exactly, 950 and 317 milliseconds against the SAA5050's 960 and 320; the cycle 1.267 seconds, not 1.28; 58 and 19 would be nearer in milliseconds and lose the ratio); the Additional Flash Functions' unit 5 ticks, exactly one twelfth of a second; the cursor's half period 32 ticks. The engine's and the browser's flash requirements (REQ-412, REQ-3676, REQ-5713, REQ-736) are to be restated in ticks when this is built.
18. **Frames are a record**, type 27, for teletext and NAPLPS; ReGIS's commit is its frame marker and nothing is added to its stream. A frame that is not ended is applied, never dropped.
19. **Teletext sprites are placements of the standard's own objects**, and a teletext sprite sheet is an object page.
20. **ReGIS sprites replay the moved drawing inside the damage** and keep no pixel cache, because a drawing's pixels depend on what is beneath it; DEC-6524 item 6's "without its vectors being sent or interpreted again" is met for everything but the moved drawing itself.
21. **ReGIS gains the attributes `G`, `N`, `F` and `T`**, and a layer applies to top-level drawings.
22. **NAPLPS objects are macros placed by a record**, with regions for clickable and coverable parts of an ordinary page; no NAPLPS opcode is added.
23. **Four layers**, with the background kept as a raster of its own in each renderer.
24. **One animation state, last writer wins** between the stream, the channel's `ANIMATE` records and the page's rules.
25. **The timeline is played by the server**, so the kits hold only a builder (DEC-6462); tick-exact local animation is written as rules.
26. **The budgets' figures** (half a picture a tick; 64 animated objects; 16 cycling; 16 frames; frames of 262,144 bytes and two seconds; sheets of 65,536 bytes; one minute of WAIT) are starting values to be confirmed by measurement.
27. **One viewer's setting**, "Paint drawings gradually", turns off both the ReGIS paint rate and NAPLPS WAIT.

## 13. The rdm records

| Record | Repository | Carries |
|---|---|---|
| DEC-6524 | neoteletext-common | The owner's decision: fifteen animation mechanisms to build |
| DEC-6382 | neoteletext-renderer-regis | The ReGIS paint rate's design, accepted by DEC-6524 |
| DEC-6525 | neoteletext-common | Items 17 to 27: what this document decided without the owner (awaiting confirmation) |
| REQ-6529 | neoteletext-renderer-teletext | The engine: ANIM-1, ANIM-2, ANIM-4, ANIM-6 to ANIM-8, ANIM-12 to ANIM-14, ANIM-16 to ANIM-18, ANIM-23 |
| REQ-6530 | neoteletext-renderer-regis | The ReGIS renderer: ANIM-1, ANIM-9, ANIM-10, ANIM-12 to ANIM-16, ANIM-18 |
| REQ-6531 | neoteletext-renderer-naplps | The NAPLPS renderer: ANIM-1, ANIM-4, ANIM-11 to ANIM-14, ANIM-16, ANIM-18, ANIM-20 |
| REQ-6533 | neoteletext-app-server | The server: ANIM-2, ANIM-3, ANIM-17, ANIM-21 |
| REQ-6536 | neoteletext-browser | The browser: ANIM-1 to ANIM-3, ANIM-5, ANIM-15 to ANIM-17, ANIM-20, ANIM-22 |
| REQ-6537, REQ-6538 | the TypeScript and Python kits | ANIM-19 |
| REQ-6540 | neoteletext-common | Fuzz targets and wire vectors: ANIM-23 |
| DEC-6398 | neoteletext-browser | Amended on 18 November 2026: receiver-side animation allowed |
| TODO-6543 | neoteletext-renderer-teletext | Restate the flash timing requirements in ticks |

## 14. What building changed

The fifteen mechanisms were built on 18 November 2026 in each repository at once, from this document at commit 85904b0. This section lists every place where what was built departs from that text or settles what it left open (DEVELOPMENT.md section 2.3, step 4). Each reading was taken without the owner and is recorded in rdm, in the record named, for the owner to confirm; where a reading is stated here as built, the requirement it concerns was corrected in place in the same change. Section 14.2 lists the places where the text was left as it is because what was built falls short of it or goes against it: those are faults to correct in code.

**Since written into this text.** The owner's decisions DEC-6587 and DEC-6599, made after the build, are now in the requirements above (section 15 lists the changes), so where this section cites ANIM-6, ANIM-17 or ANIM-21 as built, the citation is to the first form's text at commit 595f58c. DEC-6580's three changes are in page-rules.md (RULE-96 to RULE-98).

### 14.1 Departures and readings, now stated in the requirements

**The number of animation states (ANIM-6 against ANIM-16).**

1. ANIM-6 said 64 for every renderer and ANIM-16's table said 32 for teletext. The engine built 32 (`neoteletext_core::limits::MAX_ANIMATED_OBJECTS`), shared by a sub-page's sprites and controls; the ReGIS and NAPLPS renderers built 64. ANIM-6 now gives each renderer its figure and the reason, and says what an operation beyond the maximum does. ANIM-21's folded state for a later viewer is held to the same figure.

**The teletext engine (DEC-6554; TODO-6558 part A item 15).**

2. **ANIM-8.** A sprite is one more invocation in the enhancement walk, so the standard's display planes still rank what is drawn: a sprite whose frame is an Active object can be covered by a Passive object the page itself invokes.
3. **ANIM-8.** A sprite's objects count toward the standard's limits of invocations with the page's own; a page that itself uses 127 Passive invocations draws no Passive sprite.
4. **ANIM-8.** A sprite changes nothing outside its own cells, with the one case of two sprites side by side on a row.
5. **ANIM-8, ANIM-13.** The bounding rectangle is cut to rows 0 to 24, though a sprite writes only rows 1 to 23.
6. **ANIM-8, ANIM-12.** The grid of cells is composed again whole when sprites change; only the pixels are repainted by damage. "A moving object never causes the background to be drawn again" is met for pixels.
7. **ANIM-6.** A hidden control's spaces take its row's full row colour; forced look 3 is drawn as the pressed look; a cell a sprite changed is left alone when a control beneath is hidden or given a look.
8. **ANIM-6.** The engine's core holds the animation state and its operations as its own plain types, since it takes no dependency; a caller that links the core and `neoteletext-rules` converts between them.
9. **ANIM-1.** `FLASH_CYCLE_US` stays in the core's timing constants although nothing shown is timed by it; the configuration's flash times are given in ticks, with no shim for the earlier microseconds.
10. **ANIM-18.** The script's comments and empty lines, `control:<n>`, the records `neottx` reads, and `rules-run`'s two options and its world without a renderer are stated. `rules-run` reads the RULES record's body and not the `rules` message's JSON.
11. **ANIM-2.** The follower of open frames, `OpenFrames`, is named.

**The ReGIS renderer (TODO-6549; `docs/regis-v2.md` of that repository, "What building changed", item 12).**

12. **ANIM-15.** The paint rate does not charge the 64 work units a byte of a drawing's contents.
13. **ANIM-15.** "Given a rate" means the rate changes.
14. **ANIM-15.** When a drawing's painting starts, so does that of every drawing with a paint rate below it.
15. **ANIM-10.** A drawing drawn in another's place uses its own frame list and source, and not its own looks or paint rate.
16. **ANIM-9.** Showing a drawing the stream hid can be refused, when the scene would then cost more than a rebuild may.
17. **ANIM-13.** A drawing still being painted has the rectangle it will have when finished.
18. **ANIM-9.** What `set_animation` refuses and clamps, and the two calls added, `animation` and `drawing_position`.

**The NAPLPS renderer (TODO-6547).**

19. **ANIM-11.** `compose` takes two pictures; the fresh presentation state is the power-up state; definitions inside an object's macro are read and dropped; SET COLOR, BLINK START, BLINK STOP, BEL and the limit inside an object's macro; an object's macro cannot read the picture.
20. **ANIM-11.** A region may have looks.
21. **ANIM-11.** An object put in layer 0 by its animation state is still composed over the stream's picture.
22. **ANIM-11.** The pointer's look is given by the caller and kept apart from the animation state.
23. **ANIM-13.** An object's rectangle is cut to the picture.
24. **ANIM-11, ANIM-16.** The renderer keeps no cycle and holds no pixel budget; its caller does. Damage is the pixels whose value changed, not every pixel written.
25. **ANIM-20.** The playing of WAIT and BLINK is `naplps::Player`, in the renderer's library.
26. **ANIM-18.** `naplps-render --objects <file>`.

**The server (DEC-6568).**

27. **ANIM-21.** An audience is the connections open when the message arrives.
28. **ANIM-21.** Frames are held by the server and sent as one message; the server ends a frame after two seconds and when its program ends.
29. **ANIM-21.** Timelines are played for each connection; 16 for a connection and page and 64 for a connection; a step's due time; strictly ascending steps, refused with `not_ascending`; a looping timeline after a sleep.
30. **ANIM-21, ANIM-17.** A later viewer is sent the sheets from their start at each selection, not once for the connection's life; the state may take two ANIMATE records; a relative `move` is kept as a sum.
31. **ANIM-21.** A `naplps_objects` message is written for the generation of the connection's NAPLPS stream.
32. **ANIM-17.** The whole sheet is read at every message; a new ReGIS sheet makes the server forget the connection's ReGIS stream of that page.

**The kits (TODO-6559, TODO-6561).**

33. **ANIM-19.** A sheet's text is written a byte a character (Latin-1), as each kit's `regis` call writes ReGIS text. The TypeScript kit was built so; the Python kit was built writing UTF-8 and is changed to match.
34. **ANIM-19.** `Timeline.steps` leaves out a step given no operation; the TypeScript `then` refuses anything but a number; `loopTicks` is public; how `playTimeline` chooses an identifier. The Python `frame` is a context manager, as this document already wrote it, and `kit-calls.tsv` marks the `body` argument as TypeScript's alone.

### 14.2 Where the text stands and the code is to change

Each is recorded in the rdm record named, and none is a reading to confirm: the requirement is right and what was built does not meet it. The state given is that of the audit of 18 November 2026, when the browser's two branches were still being merged.

| # | Requirement | What was built | Record |
|---|---|---|---|
| 1 | ANIM-18: the options are the same in all three programs; `--frames <ticks>` plays that many ticks from tick 0 | `neottx` and `naplps-render` write ticks 0 to `<ticks>` less one; `regis-render` writes ticks 0 to `<ticks>` inclusive, one image more | TODO-6549 item 9, TODO-6605 |
| 2 | ANIM-21, ANIM-6: a later viewer is sent no more states than its renderer holds | The server folds up to 64 objects for every kind of sub-page, so a teletext sub-page's later viewer can be sent states the engine turns away | TODO-6605 |
| 3 | ANIM-17: the server sends a selected page's teletext object pages before the page | Not sent | TODO-6569 |
| 4 | ANIM-17: a ReGIS sheet that leaves a drawing visible is refused | Not refused; the ReGIS renderer offers no query for it | TODO-6570 |
| 5 | ANIM-1: the cursor's half period is 32 ticks, and the least interval between a page's frames is one tick | The browser's cursor blinks at 530 milliseconds and its least interval is 20 milliseconds | REQ-6536 |
| 6 | ANIM-2: a frame holds LINKS, DRAWING_LINKS and RULES records | The browser applies them as they arrive | TODO-6563 item 6 |
| 7 | ANIM-5: a teletext page and a NAPLPS picture are sent as their damaged rectangle | A teletext page is sent whole | REQ-6536 |
| 8 | ANIM-20: a BLINK changes the palette and repaints no pixel | The browser sends a whole picture at each change | TODO-6563 item 3 |
| 9 | ANIM-16: the decoder holds every renderer to its pixel maximum and reports fault 8 | Only NAPLPS is held; fault 8 is never sent | TODO-6563 item 8 |
| 10 | ANIM-17: a new generation of a sheet starts the shown sub-page's renderer again | It does not | TODO-6563 item 7 |
| 11 | ANIM-15: the viewer's setting "Paint drawings gradually" | Nothing sets it | REQ-6536 |
| 12 | ANIM-19: both kits send the same bytes for a sheet's text | The Python kit writes UTF-8 | TODO-6561 item 2 |
| 13 | Section 11: a page showing each mechanism in `regisdemo`, `naplpsdemo` and `demosite` | None | TODO-6605 |
| 14 | The owner's decision DEC-6599: a sub-page's sheet, animation state and timelines are its own | ANIM-17 as written and built gives a page one sheet that is fed before each of its sub-pages' streams; ANIM-6's ANIMATE record and ANIM-21's messages accept the sub-code `0x3F7F` for whichever sub-page is shown; the server keeps sheets by page and late-viewer state under a page; the browser's decoder keeps a sheet across sub-pages | DEC-6599 |

## 15. What changed in the second form

The changes this document took on 18 November 2026 from the second form of the page rule table (page-rules.md section 18), against its text at commit 595f58c. The renderers' requirements (ANIM-4, ANIM-7 to ANIM-16, ANIM-18, ANIM-20) are unchanged.

| # | Before | Now | By |
|---|---|---|---|
| 1 | Animation operations are held by a rule's actions and by the `ANIMATE` record | By the `ANIMATE` record alone, which a rule table's group holds as a command; `reset` and amounts are allowed in a group (ANIM-6) | DEC-6587 item 1 |
| 2 | An `ANIMATE` record may name the sub-code `0x3F7F`, "whichever sub-page is shown" | Withdrawn and refused: a record names one page number and one sub-code (ANIM-6) | DEC-6599 |
| 3 | A sheet belongs to a page number and is fed before each of its sub-pages' streams; the `SHEET` record and `sprite_sheet` name a page number | A sheet belongs to one page (number and sub-code); the `SHEET` record, `sprite_sheet`, `spriteSheet` and `sprite_sheet` gain the sub-code (ANIM-17, ANIM-19, ANIM-21) | DEC-6599 |
| 4 | `timeline_stop` and `stopTimeline` name a page number | They gain the sub-code (ANIM-19, ANIM-21) | DEC-6599 |
| 5 | The server keeps sprites, objects, sheets and the folded animation state for 64 pages a connection and sends them to a late viewer | The server keeps nothing; the program sends the page afresh at every selection; a timeline ends when its viewer leaves the page (ANIM-21) | DEC-6587 items 3 and 9 |
| 6 | Animation state outlives a connection's break where the receiver keeps the page | It is local state, dropped at a close and at a disconnect and kept while paused (ANIM-6; RULE-111) | DEC-6587 item 3 |
| 7 | Program protocol 14, push protocol 9 | 15 and 10 | DEC-6587 |
