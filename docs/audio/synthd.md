# synthD: the programming interface

**Purpose.** This document specifies how synthD is played and programmed: every MIDI message it takes, what each does, what a synthD patch is, and how each value becomes a position of a control of synthD's panel. It is the basis for implementing synthD's part of the synthesizer protocols.

**Scope.** synthD only: the instrument that models the Moog Minimoog Model D (`neoteletext-common/docs/audio/synthesizers.md` says once which instrument each synthesizer models). The transport (blocks, records, packets), the form of a block, how a bank of patches is stored and named, the restatement of a live sound, and the behaviours common to every synthesizer belong to the architecture document, `midi-architecture.md` in this folder; this document states what synthD needs of them and refers to it by requirement number (MIDI-n). Under DEC-6462 the server (neoteletext-app-server) is the one implementation of the programming interface: it encodes patches, builds blocks and records, checks everything with the receiver's own code, splits what is too long and writes the restatements; the TypeScript and Python kits are thin clients that hold none of that logic (MIDI-13, MIDI-22). The sound of the instrument (its oscillators, filter and contours) is not specified here.

**synthD's codec.** synthD's sounds are of the event codec the architecture numbers 15, and its banks of the bank codec 19, if the architecture's open question 1 (`midi-architecture.md`, section 20) is answered as it recommends (MIDI-107 to MIDI-109); otherwise synthD keeps its present code, 7, with the new content. DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation), so synthD's code is 15 and its banks' 19.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

**The finding the owner must read first.** The decision to adopt the Minimoog Voyager's MIDI implementation (DEC-6453, DEC-6455) rests on the belief that the filed Voyager user's manual holds a complete control-change table for the panel, with coarse and fine pairs. It does not. All 62 pages were read. The manual describes version 1.0 of the Voyager's software, and in that version the Voyager recognises exactly two control changes: controller 1, the modulation wheel, and controller 7, volume (manual pages 46 and 51). It has no appendix of continuous controllers, no table of controller numbers for the panel's knobs and switches, and no description of the bytes of its system exclusive preset dump. The row for this file in `minimoog/documents.tsv`, which says its "MIDI appendix gives the control-change map (coarse and fine pairs) for its panel", is wrong about this file.

This document therefore does three things:
1. It specifies completely, as requirements, everything the filed manual does define (sections 4 to 6).
2. It specifies a complete control map and patch form of NeoTeletext's own for synthD's 39 panel controls (sections 7 to 9), so that the instrument can be implemented. Every controller number, value band and scaling in those sections is NeoTeletext's own definition, marked as such, and is listed in section 13.
3. It puts the choice to the owner as open question 1 (section 14): look for a later edition of the Voyager manual that documents control changes for the panel, file it and replace the numbers of section 7 with its numbers; or approve section 7 as NeoTeletext's own.

---

## 1. Sources

All files are under `~/devel/teletext-reference/synthesizers/minimoog/`. Page numbers are the printed page numbers of each document.

| Short name here | File | What it is used for |
|---|---|---|
| **Voyager manual** | `manuals/moog-minimoog-voyager-user-manual-2003.pdf` (62 pages; "Minimoog Voyager User's Manual SKU#MAN-MIN-01", © Moog Music Inc. 2002, 2003; its printed page numbers equal the PDF's page numbers) | The adopted interface. Section K.5 "MIDI" (page 46): the messages transmitted and recognised. Appendix D, "MIDI Implementation Chart", "Version 1.0/020503", dated 2/05/03 (page 51): the chart. Section K.2 "MASTER Mode" (pages 39 and 40): the MIDI channel settings and the system exclusive utilities. Section K.3 "EDIT Mode" (pages 41 to 44): pitch bend amount, keyboard modes, trigger modes, what a preset stores. Section K.4 "PANEL Mode" (page 45): presets and their numbers. Sections III and IV (pages 13 to 37) and the figure "Default Program for Minimoog Voyager" (page 44): the Voyager's panel, control by control. Appendix C (pages 48 to 50): the count of presets. |
| **Model D manual** | `manuals/moogminimoogownersmanual_archiveorg.pdf` (24 pages; "the minimoog synthesizer operation manual", "A Guide to the Operation of the Mini Moog Model D", Moog Music Inc.; its printed page n is the PDF's page n + 2; the loose sheets after page 14 are dated July 1971 and 4/12/72 and are cited by PDF page) | The panel of the instrument modelled: every control and switch, by the numbers (1 to 29) and letters (A to S) its figures give them; the keyboard's priority; the wheels; the DECAY switch. |
| **synthD's source** | `~/devel/neoteletext-renderer-teletext/crates/neoteletext-audio-instruments/src/synthd/patch.rs`, `mod.rs` and `law.rs`, as they stood on 18 November 2026 | What is built today: the patch fields and their units, the messages taken, the laws of the knobs. Each constant there names its own source (the service manual, the schematics, the sound charts). |
| **Wire format as built** | `~/devel/teletext-reference/synthesizers/synthesizer-wire-format.html` and `programming-the-synthesizers.html` (read from the code on 18 November 2026) | What exists today on the wire and in the kit, for section 15. |
| **Architecture** | `midi-architecture.md` in this folder (18 November 2026) | The block, the records, the bank, the restatement, the common behaviours of every synthesizer (its section 11.1, MIDI-84 to MIDI-92) and every bound; this document cites its requirements as MIDI-n. Where the two documents differ, it governs. |

**The filed MIDI standards.** The MIDI 1.0 Detailed Specification 4.2 and Standard MIDI Files 1.0, in the MIDI Manufacturers Association's bundle of document version 96.1 (rdm SRC-6469), and the Recommended Practice RP-015, "Response to Reset All Controllers" (rdm SRC-6468), are filed in `~/devel/teletext-reference/midi/`; `midi-architecture.md`, section 1.5, describes them and the form of their citations, "MIDI 1.0 4.2, printed page n (PDF m)", the PDF page being that of the filed file. This document uses MIDI 1.0 only for what is common to all MIDI: the status bytes, that a note on of velocity 0 is a note off, the pairing of controllers 0 to 31 with 32 to 63 as most and least significant bytes, the standard meanings of controllers 5, 64, 65, 120, 121 and 123 to 127, the controllers it leaves undefined, registered parameter number 0, and the centre of pitch bend; the null parameter number from the General MIDI Level 1 Developer Guidelines in the same bundle (page 6, PDF 315); and RP-015 through DEC-6464 version 2 and MIDI-84. Every statement below that rests on one of them was read against the filed copy on 18 November 2026 and cites the place it rests on.

Decisions this document follows: DEC-6453 (each instrument is programmed as its most well-known existing interface does it; NeoTeletext defines something only where nothing exists, and records why), DEC-6455 (the provenance of synthD and the choice of the Voyager's interface), DEC-6461 (the names), DEC-6462 (the Rust server is the core of the programming interface; the kits are thin), DEC-6464 (every synthesizer answers Reset All Controllers identically, by RP-015, volume unchanged; recorded as proposed, awaiting the owner's confirmation), DEC-6410 and DEC-6429 (instruments as codecs of the audio profile), DEC-6428 (the clean-room rules), and the architecture decisions A1 to A6 of the brief of 18 November 2026.

No web page was fetched and no reference program was opened for this document.

## 2. Terms

- **synthD.** NeoTeletext's monophonic synthesizer of three oscillators and a ladder filter. In identifiers it is written `synthd`.
- **The instrument modelled.** The Moog Minimoog Model D. It is named in this document only where a source is cited or the panel is described.
- **The adopted interface.** The MIDI implementation of the Moog Minimoog Voyager, version 1.0 of its software, as the Voyager manual states it.
- **Panel control.** One knob or one switch of synthD's panel. synthD has 39: the 26 knobs and selector switches and the 13 on-off switches that the patch of `patch.rs` holds. They are the panel of the instrument modelled, less the controls that serve only its hardware (section 12.3).
- **Field.** The value of one panel control as synthD holds it, in the panel's own units (for example a contour's attack time in milliseconds, 0 to 10,000). The fields are those of `Patch` in `patch.rs`.
- **Controller.** A MIDI control change's controller number, 0 to 127. **Value** is its data byte, 0 to 127.
- **Coarse and fine pair.** Two controllers that together carry one 14-bit number: the coarse controller, numbered 0 to 31, carries the most significant seven bits, and the fine controller, numbered 32 higher, carries the least significant seven. The 14-bit number is `coarse × 128 + fine`, 0 to 16,383.
- **Canonical value.** The one value a sender writes for a given position of a control, where several values select the same position.
- **Patch.** The positions of all 39 panel controls. On the wire it is the 47 values of section 9.
- **Bank.** The set of patches a synthD sound plays from, chosen among by program change. How a bank is stored and named is the architecture document's.
- **Block.** 20 milliseconds of a sound's input, 960 samples at 48,000 Hz (decision A2). Its content is a Standard MIDI File track-event list whose tick is 0.1 millisecond (decision A3).
- **Counted as ignored.** A message the instrument does not act on adds one to a count the instrument keeps (`ignored_events` today), and nothing else happens. Nothing is an error. It is what the architecture calls "passed over and counted".
- **Not stated in the source.** The filed document does not say. Nothing is supplied from memory in its place; where synthD needs an answer, the answer is NeoTeletext's own and is listed in section 13.

## 3. What the two instruments are (facts, not requirements)

**The instrument modelled has no MIDI and no patch memory.** Its maker says so: the Voyager manual, page 2, says of analogue synthesizers thirty years old, and of the minimoog "introduced in 1970", that Moog has "done away with the things that made 30-year-old analog synthesizers difficult – the tuning instability, the lack of patch memory, and the lack of compatibility with MIDI gear". The Model D manual describes no memory and no digital interface of any kind: what it offers for outside control is "provision … at the rear of the instrument for connecting external controlling devices such as sequencers, foot pedals, and two-dimensional (joystick) controllers", which "may be used to control volume, pitch, and filter characteristic", and timing signals "to trigger the contour generators" (Model D manual, page 1). A sound is written down as the positions of the knobs and switches (the Voyager manual, page 52: sounds on the minimoog "are easier to document with patch templates").

**The Voyager is a different instrument with a larger panel.** It is "a descendant of the classic minimoog" (Voyager manual, page 13): monophonic, three oscillators, a noise source, an external input, a mixer, two filters, two envelope generators, a dedicated low-frequency oscillator, two modulation busses, a touch surface and 128 presets. Section 10 compares the two panels control by control.

---

## 4. The channel messages

### 4.1 What the adopted interface recognises

The Voyager manual's whole statement of what the Voyager recognises is this sentence (page 46): "The Voyager responds to Note On messages, Program Change messages, All Notes Off, Pitch Bend, Mod Wheel (CC1), and Volume Controller (CC7) messages", and the chart of page 51. The chart, row by row, in the "Recognized" column:

| Chart row | Recognised | Remarks in the chart |
|---|---|---|
| Basic channel, default | 1 to 16 | Memorized |
| Basic channel, changed | 1 to 16 | Memorized |
| Mode, default | 4 (Omni Off, Mono) | "Note Priority is user selectable" |
| Mode, messages | Yes | "All Notes Off" |
| Mode, altered | No | |
| Note number | 0 to 127 | |
| Note number, true voice | 0 to 127 | |
| Velocity, note on | No | |
| Velocity, note off | No | |
| After touch | No | |
| Pitch bend | Yes | |
| Control change | Yes | "CC 1 (Mod Wheel), CC 7 (Volume)" |
| Program change | Yes, true number 0 to 127 | |
| System exclusive | Yes | "Must be enabled" |
| System common | No | |
| System real time | No | |
| Aux messages | No | |

For completeness, the "Transmitted" column: basic channel 1 to 16; mode 3; note numbers 53 to 96; velocity of note on and of note off, yes; after touch, no; pitch bend, no; control change, no; program change, yes, 0 to 127; system exclusive, yes; system common, system real time and aux messages, no. synthD transmits nothing, so that column gives rise to no requirement.

### 4.2 Requirements

**SD-1. The messages synthD acts on.** synthD MUST act on exactly these MIDI 1.0 channel messages, and on no other: note off (status `0x8n`); note on (status `0x9n`); control change (status `0xBn`) of the controllers that requirements SD-6 (the registered parameter number controllers 6, 38, 96, 97, 98, 99, 100 and 101), SD-9 to SD-13 and the table of SD-17 name; program change (status `0xCn`); and pitch bend (status `0xEn`). Here `n` is the channel, 0 to 15. Every other channel message (polyphonic key pressure `0xAn`, channel pressure `0xDn`, a control change of any controller not named) and every system exclusive, system common and system real-time message MUST be counted as ignored and MUST change nothing in the instrument. The server MUST refuse a program's message holding one of those others where it would go into a synthD block (MIDI-10), and MUST drop it, with a count in its answer, from a Standard MIDI File (MIDI-118).
- Reason: These are the messages the adopted interface recognises, with the control changes NeoTeletext adds for the panel because the adopted interface has none (section 7), and those of the common layer every synthesizer takes (MIDI-9, MIDI-84 to MIDI-92).
- Source: Voyager manual, page 46 (section K.5) and page 51 (the chart). That note off is recognised is not stated in the manual's sentence, which names "Note On messages" only; MIDI 1.0 defines note off (MIDI 1.0 4.2, Table II, PDF 101; printed page 10, PDF 42), and a note could not otherwise end. MIDI-9, MIDI-10.
- Verification: A test sends one message of every status from `0x80` to `0xEF` and every controller 0 to 127, and checks which change the instrument's state and that each of the others adds one to the count of ignored messages and leaves the rendered samples identical to a run without it; a server test checks each of the others is refused, naming the event.

**SD-2. Channels.** synthD MUST act on a channel message alike whatever its channel (0 to 15): the sixteen channels are one keyboard and one panel.
- Reason: A synthD sound holds one monophonic instrument, so there is nothing a second channel could address. The Voyager "only responds to one channel at a time", chosen from 1 to 16 by a setting of its MASTER mode; that setting is a global setting of the hardware, which decision A6 lets be left out, and no message sets it.
- Source: Voyager manual, page 39 ("MIDI IN CHANNEL") and page 51 (basic channel 1 to 16, mode 4). MIDI-67 and MIDI-68 (the channel map of a one-part family). The departure (all channels, where the Voyager takes one) is listed in sections 12.1 and 12.2, as MIDI-68 requires. It is what is built today (`mod.rs`: "The instrument is one part and hears every channel").
- Verification: A test plays the same score sixteen times, each on a different channel, and once with its messages spread over all sixteen, and checks that every run's samples are identical.

**SD-3. Note on.** On a note on whose velocity is 1 to 127, synthD MUST take the key (data byte 1, 0 to 127) as pressed, under the rules of section 5. The velocity MUST NOT change the sound in any way. A note on whose velocity is 0 MUST be taken as a note off of that key, as in every synthesizer (MIDI-88).
- Reason: The adopted interface does not recognise velocity, and the instrument modelled has none. The meaning of velocity 0 is the common rule of MIDI-88, which the Voyager manual does not state.
- Source: Voyager manual, page 51 (velocity, note on: not recognised; note numbers 0 to 127 recognised). Model D manual, page 8, step 13 (the keyboard produces a control signal by "the position of the key struck" and a timing signal, and nothing else). MIDI-88; MIDI 1.0 4.2, printed page 10 (PDF 42) and Table II (PDF 101), for velocity 0.
- Verification: A test plays the same note at velocities 1, 64 and 127 and checks identical samples; and checks that a note on of velocity 0 releases the note exactly as a note off does.

**SD-4. Note off.** On a note off, synthD MUST take the key as released, under the rules of section 5. The release velocity MUST NOT change the sound.
- Reason: As SD-3.
- Source: Voyager manual, page 51 (velocity, note off: not recognised). MIDI 1.0 4.2, Table II (PDF 101: `8n`, the key and the note off velocity).
- Verification: The test of SD-3, with note offs of velocities 0, 64 and 127.

**SD-5. The pitch of a key.** With an oscillator's RANGE at 8′, its FREQUENCY at the middle, TUNE at the middle and the pitch wheel at its centre, key 69 MUST sound 440 Hz and every other key MUST sound its equal-tempered MIDI pitch, a semitone a key, over all 128 keys. The keys below 41 and above 84, which the modelled instrument's 44-note keyboard does not have, MUST go on at the same semitone a key.
- Reason: The adopted interface recognises note numbers 0 to 127. Which pitch a MIDI note number sounds on the Voyager is not stated in the source (page 61 says only that the keyboard's pitch voltage "will be different when MIDI note-on messages are received"); synthD keeps what is built, which is the modelled instrument's tuning.
- Source: Voyager manual, page 51 (note numbers 0 to 127). synthD's source, `law.rs` (`PITCH_KEY` 69, `PITCH` 440 Hz, `KEYBOARD` 41 to 84, each with its own source in the service manual). Model D manual, page 1 ("a 44-note keyboard"). NeoTeletext's own definition, section 13 item 8.
- Verification: A test measures the frequency of keys 0, 21, 41, 69, 84, 108 and 127 with one oscillator at 8′ and drift at zero and checks each within 1 cent of its MIDI pitch (keys whose pitch lies above half the sample rate are checked to be silent, not folded).

**SD-6. Pitch bend and its range.** On a pitch bend, synthD MUST form the 14-bit number `data byte 2 × 128 + data byte 1`, whose centre is 8,192, using all 14 bits (MIDI-91), and MUST move the pitch of all three oscillators by `(number − 8,192) ÷ 8,192` of the wheel's range either way. Number 0 is then the full range down, and number 16,383 is 8,191 ÷ 8,192 of the range up. An oscillator 3 whose OSC. 3 CONTROL switch is off MUST be moved as the others are, as it is today.

The wheel's range MUST be set as MIDI-90 requires of every synthesizer, by registered parameter number 0, pitch bend sensitivity (MIDI 1.0 4.2, printed page 18, PDF 50; Table IIIa, PDF 103):
1. synthD MUST keep, as MIDI-76 says, the parameter number last selected: controller 101 sets its most significant seven bits and controller 100 its least significant seven, for a registered parameter; controller 99 and controller 98 do the same for a non-registered parameter. A parameter number is `MSB × 128 + LSB`. Before any selection, after RPN 127, 127 (the null parameter number), after a reset all controllers (MIDI-84, SD-13) and after a lost block (SD-25), no parameter is selected.
2. While registered parameter 0 is selected, data entry controller 6 MUST set the range's semitones to its value (0 to 127) and its cents to 0, and data entry controller 38 MUST set the range's cents to its value and leave its semitones; increment (controller 96) and decrement (controller 97), whatever their value, MUST raise or lower the range by one cent, not below 0. The range in cents is `100 × semitones + cents`, limited to synthD's most, 3,100 cents (31 semitones, two octaves and a fifth): a larger value MUST be set to 3,100.
3. Data entry, increment and decrement while no parameter, a non-registered parameter or a registered parameter other than 0 is selected MUST change nothing and MUST be counted as ignored: synthD has no non-registered parameters and no other registered parameter.
4. Before any registered parameter 0 message the range MUST be synthD's default, 200 ÷ 301 of an octave (797 cents) either way, the range of the instrument modelled. A program change MUST NOT change the range, and neither MUST a reset all controllers (MIDI-84, MIDI-90).

This second paragraph follows the recommendation of the architecture's open question 5 (`midi-architecture.md`, section 20), which is pending the owner's answer. Under that question's option B, synthD would instead keep the one range of 797 cents either way, no message would set it, and controllers 6, 38, 96, 97, 98, 99, 100 and 101 would be counted as ignored.
- Reason: The adopted interface recognises pitch bend, and its wheel "affects the pitch of all three oscillators". The Voyager's range is a setting of each preset with ten choices, from off to two octaves and a fifth (section 12.1), and no message of the Voyager sets it; MIDI-90 makes registered parameter 0 the one way every synthesizer's range is set, so that a program sets a bend range alike everywhere. The default is the instrument modelled's one range, as built. The most, 31 semitones, is the largest of the Voyager's ten choices, so that every range the adopted interface offers can be set and nothing beyond it; it is NeoTeletext's own choice of limit within MIDI-90 (section 13 item 11). One cent a step for increment and decrement is NeoTeletext's own reading, since neither the Voyager manual nor a filed MIDI document says what a step of registered parameter 0 is: MIDI 1.0 4.2 names data increment and decrement (printed page 17, PDF 49; Table III, PDF 102) but states no step, and MIDI-90 makes one cent the step in every synthesizer.
- Source: Voyager manual, page 51 (pitch bend recognised), page 35 ("PITCH BEND WHEEL"), pages 41 and 42 (PITCH BEND AMOUNT, ±2 octaves and a fifth the largest). The default range: synthD's source, `law.rs`, `BEND`, from the service manual's figure 9-2; the Model D manual, page 8, step 10, says "as much as half an octave up or down". MIDI-76, MIDI-90, MIDI-91; MIDI 1.0 4.2, printed page 19 (PDF 51), for the 14 bits and the centre, and printed pages 17 and 18 (PDF 49 and 50) with Tables III and IIIa (PDF 102 and 103), for registered parameter number 0, its selection and its data; the GM Developer Guidelines, page 6 (PDF 315), for the null parameter number.
- Verification: A test holds a note and sends pitch bends of 0, 4,096, 8,192, 12,288 and 16,383 at the default range, and checks the measured pitch against −797, −398.5, 0, +398.5 and +796.9 cents, each within 1 cent; a test bends from 8,192 to 8,193 and checks the pitch moves; a test sets the range by registered parameter 0 to 1, 7 and 24 semitones and to 40 semitones (limited to 31), bends fully and checks the pitch against each range within 1 cent; a test checks increment and decrement each move the range by one cent; a test checks data entry after RPN 127, 127, after a non-registered parameter selection and with no selection changes nothing and is counted; and a test checks a program change and controller 121 leave the range.

**SD-7. Key pressure and channel pressure.** synthD MUST NOT act on polyphonic key pressure or on channel pressure: each such message is counted as ignored.
- Reason: The adopted interface does not recognise after touch, and the instrument modelled has no pressure.
- Source: Voyager manual, page 51 (after touch: not recognised).
- Verification: The test of SD-1.

**SD-8. System exclusive, system common and system real time.** synthD MUST NOT act on any system exclusive message: one that reaches it is counted as ignored, whatever its length and content. It MUST NOT act on any system common or system real-time message.
The server MUST refuse a system exclusive message in a program's events for a synthD sound (MIDI-10), and a block never carries the system common and real-time messages of MIDI-8.
- Reason: The Voyager recognises system exclusive only for a whole bank of presets and for its own software, only when a person has enabled it at the panel, and the manual gives not one byte of either message (section 11). There is therefore no documented system exclusive message for synthD to be compatible with. The chart marks system common and system real time as not recognised.
- Source: Voyager manual, pages 39 and 40 (the utilities), page 46 and page 51 ("Must be enabled"). MIDI-8, MIDI-10, MIDI-28, MIDI-34.
- Verification: A receiver test gives blocks holding system exclusive events of 1, 100 and 256 bytes after `0xF0`, one of 257 bytes (a content error, MIDI-28), and skipped events in the places of a song position pointer and a timing clock (MIDI-23), and checks that the samples are identical to the blocks without them and that each is counted; a server test checks a system exclusive message in a synthD sound's events is refused.

**SD-9. The modulation wheel, controller 1.** On a control change of controller 1, synthD MUST set the modulation wheel to `value ÷ 127` of its travel. The wheel is the level control of the modulation mix on its way to the destinations that the OSCILLATOR MODULATION and FILTER MODULATION switches select: at value 0 no modulation passes, and at value 127 all of it passes. The share of the modulation that passes MUST be the square of the wheel's travel, `(value × value) ÷ (127 × 127)`. Controller 33, which MIDI 1.0 pairs with controller 1 as its fine part (MIDI 1.0 4.2, printed page 11, PDF 43; Table III, PDF 102), MUST be counted as ignored, as MIDI-74 allows where the interface does not pair them.
- Reason: The adopted interface recognises "Mod Wheel (CC1)", one controller. The wheel does on synthD what it does on the instrument modelled.
- Source: Voyager manual, pages 46 and 51 (controller 1) and page 35 ("MOD WHEEL"). Model D manual, page 6, step 5 ("The MODULATION wheel is in effect a level control for the Modulation Mix"). The curve between the ends is not stated in the source; the square is what is built (`mod.rs`, from the service manual's "50K AUDIO") and is NeoTeletext's own (section 13 item 9).
- Verification: A test sets oscillator 3 to LO as the modulation, turns OSCILLATOR MODULATION on, and measures the depth of the pitch's swing at values 0, 32, 64, 96 and 127 against 0, 0.0635, 0.254, 0.571 and 1 of the full depth.

**SD-10. Volume, controller 7.** On a control change of controller 7, synthD MUST set a gain on its output from the value, 0 (silent) to 127 (full), by the volume law that every NeoTeletext synthesizer shares (MIDI-82 and MIDI-92: `(value × value) ÷ (127 × 127)` of full), and MUST move the gain to its new place by at most `1 ÷ 256` of full a sample, so over at most 256 output samples (5.3 milliseconds). This gain is separate from the panel's VOLUME knob (control 26 of SD-17) and multiplies with it. Before any controller 7 arrives the value is 127. Controller 39 MUST be counted as ignored.
- Reason: The adopted interface recognises "Volume Controller (CC7)", one controller. Whether on the Voyager it moves the MASTER VOLUME knob or acts beside it is not stated in the source; synthD keeps what is built, a volume beside the panel's, so that a patch's own volume and a performance's fades do not overwrite one another.
- Source: Voyager manual, pages 46 and 51. The law and its slew: synthD's source, `analog/volume.rs` (own choices), shared by all the synthesizers; MIDI-82 and MIDI-92 state the law once for every synthesizer, as a gain separate from any volume of the patch. NeoTeletext's own definition, section 13 item 10.
- Verification: A test checks the level of a held note at values 0, 64 and 127 against the shared law, checks that no two successive samples of the gain differ by more than the slew allows, and checks that the product with the panel's VOLUME is what is heard.

**SD-11. All notes off, controller 123.** On a control change of controller 123, whatever its value, synthD MUST release every key that is held, as a note off of each would, and change nothing else, as MIDI-85 requires of every synthesizer. A sustain pedal that is down (SD-13) still holds the note until it goes up, and a note in its release goes on with it.
- Reason: It is the one mode message the adopted interface recognises, and its behaviour is the common one of MIDI-85.
- Source: Voyager manual, page 46 ("All Notes Off") and page 51 (mode messages: "All Notes Off"). MIDI-85. That the pedal still holds is MIDI 1.0's rule ("A Hold or Sustain pedal 'On' message takes priority over Note Off and All Notes Off until it is released", A-5, PDF 95) and what is built.
- Verification: A test holds three keys, sends controller 123, and checks the note is released; and repeats with the pedal down and checks it is held until the pedal lifts.

**SD-12. Program change.** On a program change, synthD MUST take its data byte, 0 to 127, as the number of a patch in the sound's bank and MUST set all 39 panel controls to that patch, as if the control changes of the patch's 47 values had arrived at that instant (SD-22). The modulation wheel, the pitch wheel, the sustain pedal, controller 7's volume and the keys held are left as they are. If the bank holds no patch of that number, synthD MUST set the panel to the default patch (SD-21) and count the program change as ignored. Until a first program change arrives the panel is at patch 0 of the bank, or at the default patch if the bank lacks patch 0 or it was refused (MIDI-61; every sound names at least one bank, MIDI-57).
- Reason: The adopted interface recognises program change with true numbers 0 to 127 and keeps 128 presets, numbered 1 to 128. A program change on the Voyager recalls a preset, which is "all of the settings of the front panel controls except FINE TUNE, plus the parameters in EDIT mode"; synthD's patch is all of its panel (it includes TUNE: section 12.1).
- Source: Voyager manual, page 51 (program change, 0 to 127), page 45 ("The 128 presets are numbered 1 to 128. A preset consists of all of the settings of the front panel controls except FINE TUNE, plus the parameters in EDIT mode") and page 46. That program number 0 is preset 1 is not stated in the source; it is MIDI's ordinary numbering (MIDI 1.0 4.2, printed page 14, PDF 46: "As with program numbers, banks begin counting from 1. Thus the actual bank number will be (MIDI value + 1)"). That patch 0 plays before a first program change is what is built, and is MIDI-61's rule; that a missing patch sets the default and is counted is MIDI-59's. synthD has no bank select: controllers 0 and 32 are counted as ignored (MIDI-64), and the mapping of MIDI-59 is bank index 0, program equal to the program number, so a synthD sound names one bank (MIDI-57 allows 1 to 10; only the first is reached).
- Verification: A test builds a bank of 128 different patches, sends program changes 0, 1, 31, 32 and 127, and checks the panel after each equals the patch of that number; sends a program change beyond a bank of 4 patches and checks the default patch and the count; and checks that a held note, the wheels and the pedal are unchanged by a program change.

**SD-13. The messages of NeoTeletext's common layer.** synthD MUST also act on the control changes that the architecture defines for every synthesizer (MIDI-9) and that the adopted interface does not recognise, each with the one behaviour section 11.1 of `midi-architecture.md` sets for every synthesizer:
1. controller 64, the sustain pedal (MIDI-87): down at values 64 to 127, up at 0 to 63; while it is down a released key's note is held as a held key's is, and when it goes up every note so held is released;
2. controller 120, all sound off (MIDI-86): the sound is taken out over at most 256 output samples, within the 1,024 that MIDI-86 allows, by a fade that passes the click measure (MIDI-83), and the voice then emptied; the pedal, every controller and the panel are left where they are;
3. controller 121, reset all controllers (MIDI-84, after DEC-6464 version 2, which is recorded as proposed and awaits the owner's confirmation), on every channel and whatever its value: it sets the modulation wheel, controller 1, to 0, the pitch wheel to its centre (8,192), the sustain pedal, controller 64, up, the GLIDE switch, controller 65, off, and the parameter number selection of SD-6 to none (the null value 127 in each of controllers 98 to 101); it leaves controller 7's volume, the program, the pitch bend range of SD-6 and every other panel control of SD-17 as they are. Held keys are not released by it, except as the pedal's going up releases the notes it held. synthD has no expression, sostenuto or soft pedal, no channel pressure, no key pressure, and no pan, bank select, effect or sound controller, so RP-015's settings of those have nothing to act on (RP-015, page 2). The GLIDE switch is a panel control of the patch (SD-17), but controller 65 is one of the pedals RP-015 sets to 0 by name ("Set Pedals (#64, #65, #66, #67) to 0", RP-015, page 2), and synthD's GLIDE switch carries that pedal's own meaning, portamento on and off, which MIDI-84 item 2 resets even where a family makes it a parameter of its patch; open question 4 records the change. Every other controller synthD responds to, as MIDI-84 item 4 requires this document to list:

| Controllers | What they move | On controller 121 | Reason |
|---|---|---|---|
| 5 (the GLIDE knob, portamento time), 3, 9, 14, 15 and 20 to 23 with their fine controllers 35, 41, 46, 47 and 52 to 55, 24 to 31, 85 to 90 and 102 to 116: every panel controller of SD-17 but the GLIDE switch | Parameters of the patch | Left as they are | A controller that moves a parameter of the patch is the patch, not a performance control (DEC-6464 item 4, MIDI-84 item 4) |
| 6, 38, 96 and 97: data entry, increment and decrement | The value of the registered parameter selected, the pitch bend range | They hold no value of their own; the range they set is left as it is | RP-015: "Do NOT reset registered or non-registered parameters" (page 2) |

Every controller not named in SD-1 is counted as ignored (SD-1) and has no state to reset;
4. controllers 124 (omni off), 125 (omni on), 126 (mono on) and 127 (poly on), the mode messages (MIDI-89): whatever its value, each acts as all notes off (SD-11) and does nothing else; none changes the channels synthD hears (SD-2) or its one-note assignment (SD-14).
- Reason: They are needed by every NeoTeletext sound (a receiver releases every note after a lost block; a sound must be silenced at once), they are standard MIDI 1.0 messages (decision A1), and the owner requires every synthesizer to behave the same way for them (DEC-6464; section 11.1 of the architecture). Controllers 64, 120 and 121 are built today; the mode messages and the parameter number selection are new. Each is listed in section 12.2 as a departure from, or in section 13 as an addition to, the adopted interface.
- Source: MIDI-9, MIDI-83, MIDI-84, MIDI-86, MIDI-87, MIDI-89; DEC-6464 version 2; MIDI 1.0 4.2, Tables III and IV (PDF 102 and 104) and printed pages 12, 20, 24 and 25 (PDF 44, 52, 56 and 57), for the controllers; RP-015, page 2, for the reset; synthD's source, `mod.rs` (`control_change`). The Voyager manual's chart (page 51) names only controllers 1 and 7, and its mode messages "All Notes Off" only.
- Verification: The tests that exist today for controllers 64, 120 and 121 (`tests/synthd_instrument.rs`) continue to pass; a test sends values 0, 1, 63, 64 and 127 of controller 64 and checks the pedal after each; a test holds a note with the pedal down, sends 120 and checks the output is 0 by sample 256 and the sweep measure holds; a test moves the wheels, the pedal, the volume, a panel control and the bend range and selects registered parameter 0, sends 121, and checks each against item 3 and its table, the GLIDE switch off and every other panel control unchanged; and a test holds three keys and sends each of 124 to 127 in turn, checking the note released and nothing else changed.

## 5. The keyboard: one note, lowest key, no retrigger

**SD-14. Note priority.** synthD MUST sound one note at a time. While more than one key is held, the note MUST be the lowest key held. When the lowest key is released while others are held, the note MUST pass to the lowest key still held. When the last key is released (and the pedal is up) the note is released and the pitch stays where it was. synthD MUST remember 16 held keys; a seventeenth held at once displaces the key held longest.
- Reason: It is the instrument modelled: "If more than one key is held down, only the lowest one has effect." The Voyager offers four keyboard modes as a setting of each preset ("Lower Key", "Higher Key", "Last Key", "1 Key Only"); no message sets it, which mode is its default is not stated in the source, and the first of them, "the lowest key pressed sounds", is the modelled instrument's.
- Source: Model D manual, page 8, step 13. Voyager manual, page 43 ("KEYBOARD MODES") and page 51 ("Note Priority is user selectable"). The 16 keys: synthD's source, `analog/allocator.rs`, `HELD_KEYS` (own choice).
- Verification: A test holds key 60, then 64 (the pitch stays at 60), then 55 (the pitch goes to 55), releases 55 (the pitch goes to 60), releases 60 (the pitch goes to 64), releases 64 (the note is released); and a test holds 17 keys and checks which is forgotten.

**SD-15. Triggering and legato.** The filter contour and the loudness contour MUST start (their attacks begin) only when a key goes down while no key is held and no pedal holds the note. A key pressed while another is held MUST NOT restart the contours, whether or not it takes the note; nor does the passing of the note back to a held key when another is released. The contours MUST be released when the last key is released and the pedal is up.
- Reason: It is the instrument modelled: "A timing signal begins whenever a key on the keyboard is depressed, and stops when all keys are released." It is also the first of the Voyager's two trigger modes, "Single Trigger (legato, envelopes aren't retriggered until keys are fully released)"; the other, "Multi Trigger", is a setting of a preset that no message sets, and the instrument modelled has no such mode.
- Source: Model D manual, page 2 (section C). Voyager manual, page 43 ("TRIGGER MODES").
- Verification: A test with a slow attack plays two overlapping notes and checks that the loudness contour's level does not fall back to its start at the second; and plays two notes with a gap and checks that it does.

**SD-16. Glide.** When the GLIDE switch (control 38 of SD-17) is on and the GLIDE knob (control 2) is above 0, a change of the note's pitch MUST slide from the old pitch to the new at the rate the knob sets; otherwise the pitch MUST change at once. The slide happens on every change of the note's key, including a legato change (SD-14) and the first note after silence, from the pitch last sounded.
- Reason: It is the instrument modelled: the GLIDE control "regulates the amount of portamento, or glide, heard between pitches as first one key and then another is depressed", "activated by turning on the GLIDE switch". The Voyager has the same pair: a GLIDE RATE knob and a GLIDE switch.
- Source: Model D manual, page 8, step 12, and PDF page 20 ("With no external switch connected and the GLIDE switch turned 'off' there will be no portamento"). Voyager manual, page 21 ("GLIDE") and page 35. The knob's law: synthD's source, `law.rs` (`glide`, `GLIDE_TIME`; the cube is an own choice).
- Verification: A test plays two notes an octave apart with the switch on and the knob at 50 and checks the time the pitch takes to cover 63 per cent of the octave against the law; and with the switch off, or the knob at 0, checks the pitch changes within one block.

---

## 6. What the adopted interface says of the panel's controllers

The Voyager manual assigns a controller number to nothing on the panel. It names two controllers, 1 and 7 (pages 46 and 51), and says nothing of any other: no number, no coarse and fine pair, no range, no value band for any switch. For every knob and switch of the Voyager's panel the controller number is therefore **not stated in the source**, and so is the curve from a controller's value to the control's position. Section 10 lists every control of the Voyager's panel with this fact against it.

The manual's own words date its MIDI section: "The current (as of 02/05/03) MIDI implementation of Version 1.0 of the software" (page 46). Whether a later version of the software recognises more, and whether a later edition of the manual documents it, is not established by any filed document. DEC-6455 and the row of `documents.tsv` say that this file holds a control-change map; it does not.

Under DEC-6453 item 3, NeoTeletext defines a format or message of its own only where no existing interface covers the instrument, and records why. Sections 7 to 9 are that definition for synthD's panel, made because the filed interface covers two controllers and synthD has 39 panel controls. Open question 1 asks the owner whether to keep it or to look for a later edition.

## 7. The panel control map (NeoTeletext's own definition)

**SD-17. The 39 panel controls and their controllers.** synthD MUST have exactly the 39 panel controls of the table below, each moved by the control change of the controller, or coarse and fine pair, that the table gives, and by no other message than that and a program change (SD-12). The "Model D" column gives the number or letter the Model D manual's figures give the control.

*Knobs carried as a coarse and fine pair (fields of more than 128 values), scaled by SD-18:*

| No. | Control | Model D | Coarse | Fine | Field and its unit | Range of the field |
|---|---|---|---|---|---|---|
| 1 | TUNE | 1 | 3 | 35 | The pitch of all three oscillators, in cents | −242 to +242 |
| 7 | Oscillator 2 FREQUENCY | 7 | 9 | 41 | Oscillator 2's pitch against oscillator 1, in cents | −700 to +700 |
| 10 | Oscillator 3 FREQUENCY | 10 | 14 | 46 | Oscillator 3's pitch, in cents; with OSC. 3 CONTROL off the same travel is 2.75 octaves either way | −700 to +700 |
| 17 | CUTOFF FREQUENCY | 17 | 15 | 47 | The dial's −5 to +5, in hundredths of a division; a division is an octave | −500 to +500 |
| 20 | Filter contour ATTACK TIME | 20 | 20 | 52 | Milliseconds | 0 to 10,000 |
| 21 | Filter contour DECAY TIME | 21 | 21 | 53 | Milliseconds | 0 to 10,000 |
| 23 | Loudness contour ATTACK TIME | 23 | 22 | 54 | Milliseconds | 0 to 10,000 |
| 24 | Loudness contour DECAY TIME | 24 | 23 | 55 | Milliseconds | 0 to 10,000 |

*Knobs carried in one controller (fields of 101 values), scaled by SD-19:*

| No. | Control | Model D | Controller | Field and its unit | Range of the field |
|---|---|---|---|---|---|
| 2 | GLIDE | 2 | 5 | The dial's 0 to 10, in tenths of a division | 0 to 100 |
| 3 | MODULATION MIX | 3 | 24 | Tenths of a division: 0 is all oscillator 3, 100 is all noise | 0 to 100 |
| 12 | Mixer VOLUME of oscillator 1 | 12 | 25 | Tenths of a division | 0 to 100 |
| 13 | Mixer VOLUME of oscillator 2 | 13 | 26 | Tenths of a division | 0 to 100 |
| 14 | Mixer VOLUME of oscillator 3 | 14 | 27 | Tenths of a division | 0 to 100 |
| 15 | EXTERNAL INPUT VOLUME | 15 | 28 | Tenths of a division: how much of the instrument's own output returns to the mixer | 0 to 100 |
| 16 | NOISE VOLUME | 16 | 29 | Tenths of a division | 0 to 100 |
| 18 | EMPHASIS | 18 | 30 | Tenths of a division | 0 to 100 |
| 19 | AMOUNT OF CONTOUR | 19 | 31 | Tenths of a division | 0 to 100 |
| 22 | Filter contour SUSTAIN LEVEL | 22 | 85 | Tenths of a division | 0 to 100 |
| 25 | Loudness contour SUSTAIN LEVEL | 25 | 86 | Tenths of a division | 0 to 100 |
| 26 | Main output VOLUME | 26 | 87 | Tenths of a division | 0 to 100 |

*Selector switches of six positions, carried in one controller, by the value bands of SD-20:*

| No. | Control | Model D | Controller | Positions, 0 to 5 |
|---|---|---|---|---|
| 4 | Oscillator 1 RANGE | 4 | 88 | LO, 32′, 16′, 8′, 4′, 2′ |
| 5 | Oscillator 1 WAVEFORM | 5 | 89 | Triangular, sawtooth-triangular, sawtooth, square, wide rectangular, narrow rectangular |
| 6 | Oscillator 2 RANGE | 6 | 90 | LO, 32′, 16′, 8′, 4′, 2′ |
| 8 | Oscillator 2 WAVEFORM | 8 | 102 | As oscillator 1's |
| 9 | Oscillator 3 RANGE | 9 | 103 | LO, 32′, 16′, 8′, 4′, 2′ |
| 11 | Oscillator 3 WAVEFORM | 11 | 104 | Triangular, reverse sawtooth, sawtooth, square, wide rectangular, narrow rectangular |

*On-off switches, carried in one controller: off at values 0 to 63, on at values 64 to 127 (SD-20):*

| No. | Control | Model D | Controller | Off | On |
|---|---|---|---|---|---|
| 27 | OSCILLATOR MODULATION | A | 105 | The modulation does not reach the oscillators | It moves the oscillators' pitch |
| 28 | OSC. 3 CONTROL | B | 106 | Oscillator 3 does not follow the keyboard | It follows the keyboard |
| 29 | Mixer switch of oscillator 1 | C | 107 | Out of the mixer | In the mixer |
| 30 | Mixer switch of oscillator 2 | E | 108 | Out of the mixer | In the mixer |
| 31 | Mixer switch of oscillator 3 | G | 109 | Out of the mixer (it still modulates) | In the mixer |
| 32 | Mixer switch of the external input | D | 110 | Out of the mixer | In the mixer |
| 33 | Mixer switch of the noise | F | 111 | Out of the mixer (it still modulates) | In the mixer |
| 34 | Noise WHITE / PINK | H | 112 | White | Pink |
| 35 | FILTER MODULATION | J | 113 | The modulation does not reach the filter | It moves the cutoff |
| 36 | KEYBOARD CONTROL 1 | K | 114 | No share | A third of the keyboard's voltage moves the cutoff |
| 37 | KEYBOARD CONTROL 2 | L | 115 | No share | Two thirds of the keyboard's voltage moves the cutoff |
| 38 | GLIDE | R | 65 | No glide | Glide at the GLIDE knob's rate (SD-16) |
| 39 | DECAY | S | 116 | A released note is cut in a few milliseconds | A released note falls at each contour's DECAY TIME |

Controls 36 and 37 both on give all of the keyboard's voltage. The numbers 1 to 39 in the first column are this document's, in the order of today's patch.
- Reason: The panel is the instrument's; the fields and units are those built and are the units the modelled instrument's dials and sound charts are written in. The controller numbers are NeoTeletext's own because the adopted interface gives none. They were chosen by these rules, in order: (a) controllers 1 and 7 are the adopted interface's and are not reused; (b) a control whose meaning MIDI 1.0 already names takes that controller (5, portamento time, for the GLIDE knob; 65, portamento on and off, for the GLIDE switch); (c) a field of more than 128 values takes a coarse controller that MIDI 1.0 leaves undefined among 0 to 31 (3, 9, 14, 15, 20 to 23), with its fine controller 32 higher; (d) every other control takes one controller that MIDI 1.0 leaves undefined (24 to 31, 85 to 90, 102 to 116), in the panel's order; (e) no controller that MIDI 1.0 gives another meaning is taken (0 and 32 bank select, 2, 4, 6 and 38, 8, 10 to 13, 16 to 19, 64, 66 to 84, 91 to 101, 120 to 127).
- Source: The controls: Model D manual, pages 3 to 14 and its figures 2 to 6 (each control's number or letter), and synthD's source, `patch.rs` (each field, unit and range, with its own sources). The controller numbers: not stated in the Voyager manual; NeoTeletext's own (section 13 item 1). The standard meanings and the undefined controllers: MIDI 1.0 4.2, Table III (PDF 102), against which every number was checked on 18 November 2026: 5 and 65 are portamento time and portamento on and off; 3, 9, 14, 15, 20 to 31, 85 to 90 and 102 to 119 are undefined; 35, 41, 46, 47 and 52 to 55 are the least significant bytes of 3, 9, 14, 15 and 20 to 23; and the controllers of rule (e) are those Table III gives another meaning.
- Verification: A test sends, for each of the 39 controls, a control change of its controller (and of its fine controller where it has one) and checks that exactly that field changes and no other; and a test sends every controller from 0 to 127 that the table and SD-9 to SD-13 do not name and checks each is counted as ignored. An assertion in the code checks that no controller number appears twice.

**SD-18. Scaling of a coarse and fine pair.** For each control carried as a pair, synthD MUST keep a 14-bit number, `number = coarse × 128 + fine`, and MUST set the field to

`field = lowest + floor((number × span + 8,191) ÷ 16,383)`

where `lowest` is the lowest value of the field's range and `span` is the highest less the lowest (484 for TUNE, 1,400 for a FREQUENCY, 1,000 for CUTOFF FREQUENCY, 10,000 for a time). All arithmetic is in integers. A control change of the coarse controller MUST set the coarse seven bits to its value and the fine seven bits to 0; a control change of the fine controller MUST set the fine seven bits and leave the coarse. The field is set anew after either. The canonical number for a field's value, which a sender writes, is

`number = floor(((field − lowest) × 16,383 + floor(span ÷ 2)) ÷ span)`

and the receiver's formula returns exactly that field for it. Number 0 is the lowest value, number 16,383 is the highest, and for TUNE, the FREQUENCY knobs and CUTOFF FREQUENCY number 8,192 (coarse 64, fine 0) is the middle, 0.
- Reason: The scale is linear in the panel's own units, so that a value reads as the dial reads, and it is exact both ways: every value of every field (each has fewer than 16,384) has a number, and the number gives that value back, so that a patch written today in cents and milliseconds is carried without change. The coarse controller alone gives 128 steps over the whole travel, and its value 64 is the middle of a knob that has one. That a coarse controller clears the fine part is MIDI 1.0's rule for such pairs ("When an MSB is received, the receiver should set its concept of the LSB to zero", MIDI 1.0 4.2, printed page 12, PDF 44), as MIDI-75 states for every family.
- Source: Not stated in the Voyager manual (it has no pair and no curve): NeoTeletext's own (section 13 item 2). The fields' ranges: SD-17. MIDI-75; MIDI 1.0 4.2, printed pages 11 and 12 (PDF 43 and 44), for the pairing and the clearing of the fine part.
- Verification: A test checks, for each of the eight controls and every value of its field, that the canonical number sent as coarse then fine gives that value; that numbers 0, 8,192 and 16,383 give the lowest, middle and highest; that the field never decreases as the number rises through all 16,384; and that a coarse controller alone sets the fine part to 0.

**SD-19. Scaling of a knob in one controller.** For each knob carried in one controller, synthD MUST set the field to `floor((value × 100 + 63) ÷ 127)`: value 0 is 0, value 64 is 50 and value 127 is 100. The canonical value for a field is `floor((field × 127 + 50) ÷ 100)`, and the receiver's formula returns exactly that field for it. The controller 32 higher than a knob's controller, where that number is below 64 (37 for GLIDE, 56 to 63 for controllers 24 to 31), MUST be counted as ignored.
- Reason: These fields are tenths of a dial's division, 101 values, which one controller's 128 values carry exactly; a fine controller would add nothing the instrument holds. The scale is linear in the dial's divisions.
- Source: Not stated in the Voyager manual: NeoTeletext's own (section 13 item 2). The fields: `patch.rs` and `law.rs` (`KNOB_MAX`).
- Verification: A test checks, for each of the twelve knobs, all 128 values against the formula, all 101 canonical values for an exact return, and that the field never decreases as the value rises.

**SD-20. Value bands of the switches.** For a selector switch of six positions synthD MUST set the position to `floor(value × 6 ÷ 128)`, which gives these bands: values 0 to 21 position 0; 22 to 42 position 1; 43 to 63 position 2; 64 to 85 position 3; 86 to 106 position 4; 107 to 127 position 5. The canonical value of a position is the lowest of its band: 0, 22, 43, 64, 86, 107. For an on-off switch synthD MUST take values 0 to 63 as off and 64 to 127 as on; the canonical values are 0 and 127.
- Reason: Every value from 0 to 127 then selects a position, so that no value is an error, and the bands are as nearly equal as six positions in 128 values allow. Off below 64 and on from 64 is MIDI 1.0's rule for a switch controller ("it should recognize 0-63 (00H-3FH) as "OFF" and 64-127 (40H-7FH) as "ON"", MIDI 1.0 4.2, printed page 12, PDF 44) and what the sustain pedal follows in every synthesizer (MIDI-87).
- Source: Not stated in the Voyager manual (it gives no value band for any switch): NeoTeletext's own (section 13 item 3). MIDI 1.0 4.2, printed page 12 (PDF 44), for the on-off rule.
- Verification: A test checks all 128 values of each of the six selectors and each of the thirteen switches against the bands, and each band's two edges by name.

**SD-21. The default patch.** An instrument that has been given no patch, and an instrument whose patch is missing or refused, MUST stand at this patch: TUNE 0; GLIDE 0; MODULATION MIX 0; oscillator 1 RANGE 8′, WAVEFORM sawtooth, mixer VOLUME 100, mixer switch on; oscillator 2 RANGE 8′, FREQUENCY 0, WAVEFORM sawtooth, VOLUME 100, switch off; oscillator 3 RANGE LO, FREQUENCY 0, WAVEFORM triangular, VOLUME 100, switch off; EXTERNAL INPUT VOLUME 0, switch off; NOISE VOLUME 0, switch off, white; CUTOFF FREQUENCY +500; EMPHASIS 0; AMOUNT OF CONTOUR 0; both contours ATTACK TIME 0, DECAY TIME 0, SUSTAIN LEVEL 100; main output VOLUME 100; OSCILLATOR MODULATION off; OSC. 3 CONTROL on; FILTER MODULATION off; KEYBOARD CONTROL 1 and 2 off; GLIDE off; DECAY off. Its 47 values are in the last column of the table of SD-22.
- Reason: An instrument must sound something definite before a patch arrives. This is the default built today: one sawtooth at 8′ through the open filter, shaped as an organ's note.
- Source: synthD's source, `patch.rs`, `Patch::DEFAULT` (own choice). The Voyager has a "Default Init. Parameters" sound of its own, given only as a drawing of its panel (Voyager manual, page 44), which is of a different panel and is not used.
- Verification: A test checks that a new instrument's panel equals the 47 values of SD-22's last column, decoded, field by field.

## 8. How a control change takes effect

**SD-22 is in section 9.** The requirements here say when and how a moved control is heard.

**SD-23. A control moves under a sounding note.** A control change of a panel control MUST take effect on a note that is sounding, as moving the control does on the instrument: a switch or a selector at once; a knob that sets a level in the signal's path (the mixer's five volumes, MODULATION MIX, AMOUNT OF CONTOUR, both SUSTAIN LEVELs, the main VOLUME) by moving to its new place over at most 1,024 samples of the voice (5.3 milliseconds); CUTOFF FREQUENCY and EMPHASIS over at most 4,096 samples of the voice (21 milliseconds). TUNE, the FREQUENCY knobs, GLIDE and the contours' times take their new value at once. While no note is sounding every control is at its new place at once.
- Reason: A knob under a hand passes through every place between two; a step in a level or in the cutoff is heard as a click. These are the slews built and measured today.
- Source: synthD's source, `mod.rs` (`POT_SLEW_SHIFT`, `FILTER_SLEW_SHIFT`, `set_patch`; own choices, measured in `tests/synthd_control_sweep.rs`).
- Verification: The existing control-sweep test, driven through control changes instead of `set_patch`, holds the same bounds on the largest step of the output.

**SD-24. Order and time.** Control changes MUST be applied in the order and at the times the block gives them: each event's message immediately before the sample `floor(time × 24 ÷ 5)` of its block (MIDI-5), and events of one tick in the order they stand in the block (MIDI-35). Two instruments given the same events at the same times MUST give the same samples, however the rendering is divided into calls.
- Reason: A stored sound must play identically for every viewer and at every loop.
- Source: Decisions A2 and A3; MIDI-5, MIDI-35; synthD's source, `mod.rs` (the documentation of `SynthD`: "rendered in calls of any lengths give the same samples").
- Verification: A test renders one score in calls of 1, 7, 960 and 4,800 samples and checks the samples identical.

**SD-25. After a lost block.** When the receiver tells synthD that input was lost (MIDI-102 says when), synthD MUST release the note, lift the sustain pedal and set the parameter number selection of SD-6 to none, and MUST leave every panel control, the wheels, the pitch bend range and controller 7's volume where they stand.
- Reason: A lost block may have held a note off; it may equally have held control changes, which cannot be known, so the panel is left and the server's next restatement (SD-28, MIDI-96) restores it. A data entry after a lost selection would go to the wrong parameter, so the selection is cleared, as MIDI-76 and MIDI-102 require.
- Source: DEC-6410 item 12; MIDI-76, MIDI-102; synthD's source, `mod.rs` (`release_all`).
- Verification: The existing test `a_live_sound_of_each_synthesizer_plays_and_a_lost_block_releases_its_notes` passes for synthD on event blocks; a test selects registered parameter 0, loses a block, sends a data entry alone and checks the range is unchanged.

## 9. What a synthD patch is

**SD-22. The patch: 47 values in a fixed order.** A synthD patch MUST be exactly 47 bytes, each a control change's value from 0 to 127, in the order of the table below. A control carried as a coarse and fine pair contributes two bytes, the coarse value then the fine. The patch carries no status byte, no controller number, no name and no length: byte k is always the value of the controller the table gives for byte k. A sender MUST write the canonical value of each field (SD-18, SD-19, SD-20). A receiver MUST accept every patch whose 47 bytes are each 0 to 127, whatever their values, and MUST set the panel from it exactly as the 39 controls' control changes would, all at one instant; a patch with a byte above 127, or of another length, is not a patch, and the instrument then stands at the default patch (SD-21) and the fault is counted in the counter of refused patches (MIDI-63). The server MUST encode a patch given as named fields into these 47 bytes, writing the canonical values, and MUST accept a patch given as the 47 values (MIDI-14); it MUST check every patch with the receiver's own check and refuse one of another length or with a byte above 127, naming the bank, the program, the byte and the rule (MIDI-21, MIDI-63).

| Byte | Control (number in SD-17) | Controller | Value in the default patch |
|---|---|---|---|
| 0 | TUNE (1), coarse | 3 | 64 |
| 1 | TUNE (1), fine | 35 | 0 |
| 2 | GLIDE (2) | 5 | 0 |
| 3 | MODULATION MIX (3) | 24 | 0 |
| 4 | Oscillator 1 RANGE (4) | 88 | 64 |
| 5 | Oscillator 1 WAVEFORM (5) | 89 | 43 |
| 6 | Oscillator 2 RANGE (6) | 90 | 64 |
| 7 | Oscillator 2 FREQUENCY (7), coarse | 9 | 64 |
| 8 | Oscillator 2 FREQUENCY (7), fine | 41 | 0 |
| 9 | Oscillator 2 WAVEFORM (8) | 102 | 43 |
| 10 | Oscillator 3 RANGE (9) | 103 | 0 |
| 11 | Oscillator 3 FREQUENCY (10), coarse | 14 | 64 |
| 12 | Oscillator 3 FREQUENCY (10), fine | 46 | 0 |
| 13 | Oscillator 3 WAVEFORM (11) | 104 | 0 |
| 14 | Mixer VOLUME of oscillator 1 (12) | 25 | 127 |
| 15 | Mixer VOLUME of oscillator 2 (13) | 26 | 127 |
| 16 | Mixer VOLUME of oscillator 3 (14) | 27 | 127 |
| 17 | EXTERNAL INPUT VOLUME (15) | 28 | 0 |
| 18 | NOISE VOLUME (16) | 29 | 0 |
| 19 | CUTOFF FREQUENCY (17), coarse | 15 | 127 |
| 20 | CUTOFF FREQUENCY (17), fine | 47 | 127 |
| 21 | EMPHASIS (18) | 30 | 0 |
| 22 | AMOUNT OF CONTOUR (19) | 31 | 0 |
| 23 | Filter ATTACK TIME (20), coarse | 20 | 0 |
| 24 | Filter ATTACK TIME (20), fine | 52 | 0 |
| 25 | Filter DECAY TIME (21), coarse | 21 | 0 |
| 26 | Filter DECAY TIME (21), fine | 53 | 0 |
| 27 | Filter SUSTAIN LEVEL (22) | 85 | 127 |
| 28 | Loudness ATTACK TIME (23), coarse | 22 | 0 |
| 29 | Loudness ATTACK TIME (23), fine | 54 | 0 |
| 30 | Loudness DECAY TIME (24), coarse | 23 | 0 |
| 31 | Loudness DECAY TIME (24), fine | 55 | 0 |
| 32 | Loudness SUSTAIN LEVEL (25) | 86 | 127 |
| 33 | Main output VOLUME (26) | 87 | 127 |
| 34 | OSCILLATOR MODULATION (27) | 105 | 0 |
| 35 | OSC. 3 CONTROL (28) | 106 | 127 |
| 36 | Mixer switch of oscillator 1 (29) | 107 | 127 |
| 37 | Mixer switch of oscillator 2 (30) | 108 | 0 |
| 38 | Mixer switch of oscillator 3 (31) | 109 | 0 |
| 39 | Mixer switch of the external input (32) | 110 | 0 |
| 40 | Mixer switch of the noise (33) | 111 | 0 |
| 41 | Noise WHITE / PINK (34) | 112 | 0 |
| 42 | FILTER MODULATION (35) | 113 | 0 |
| 43 | KEYBOARD CONTROL 1 (36) | 114 | 0 |
| 44 | KEYBOARD CONTROL 2 (37) | 115 | 0 |
| 45 | GLIDE switch (38) | 65 | 0 |
| 46 | DECAY switch (39) | 116 | 0 |

- Reason: Decision A4: synthD has no patch format anywhere, so a patch is the list of its interface's control-change values. The order is the panel's, left to right, and is the order of the fields of today's patch, so that the two can be compared field by field. Values alone are carried because the order is fixed: the controller numbers would repeat the same 47 bytes in every patch. Every byte value from 0 to 127 is a position of its control (SD-18 to SD-20), so the receiver has no range to check beyond the top bit, and a patch cannot hold a value the instrument cannot take.
- Source: Decision A4 and DEC-6453 item 3. The order and the form: NeoTeletext's own (section 13 item 4). Whether the Voyager's own preset dump could be used instead: section 11.
- Verification: A test decodes the default patch's 47 bytes and compares each field with SD-21; a test checks, for every byte position and every value 0 to 127, that the patch is accepted and that the field is what the control change of that controller and value gives; a test checks that a patch of 46 or 48 bytes, and a patch with any one byte of 128 or more, is refused and the default patch plays; and a test checks that a patch applied at an instant equals the same 47 values sent as 47 control changes at that instant.

**SD-26. The same patch as control changes.** The sequence of 47 control changes that a patch stands for MUST be, in the patch's byte order, `0xBn, controller, value` for each byte, where `controller` is the table's for that byte. A program that wishes to set the whole panel in a stream without a bank MAY send that sequence; synthD takes it by SD-17, and after the last of them the panel equals the patch. In that sequence a coarse controller always comes before its fine controller, as SD-18 needs.
- Reason: The patch and the live messages are one definition, so that a panel can be set by either and a tool can turn one into the other with the table alone.
- Source: SD-17, SD-18, SD-22.
- Verification: The last test of SD-22.

**SD-27. What synthD needs of the bank and of a block.** The architecture specifies the bank (MIDI-55 to MIDI-57) and the block (MIDI-23 to MIDI-38); synthD's needs are these. (a) A bank image is of the fixed-patch form of MIDI-56: 1 to 128 patches of 47 bytes each, back to back, patch k at byte `k × 47`, numbered from 0 in the bank's order: at most 6,016 bytes, within the 16,384 of MIDI-55, carried by the bank codec in pieces of 1,011 bytes (six DATA records for a bank of 128). (b) A program change's data byte, 0 to 127, is the patch's number in bank index 0 (SD-12). (c) No synthD message is longer than three bytes, since synthD takes no system exclusive (SD-8); a whole panel as control changes (SD-26) is 47 events, 188 bytes with every status byte and a one-byte delta time written, well within a block's 1,005 bytes and 256 events (MIDI-30, MIDI-31); synthD sets no lower bound of its own. (d) The server restates each live synthD sound, and begins each stored one with a restatement, as SD-28 states.
- Reason: The adopted interface has 128 presets and program numbers 0 to 127; the bank must reach them. The sizes are what the architecture needs to size records.
- Source: Voyager manual, pages 45 and 51 (128 presets; program change 0 to 127). Decision A4; MIDI-30, MIDI-31, MIDI-55, MIDI-56, MIDI-57.
- Verification: A test stores a bank of 128 patches, plays a program change to each, and checks the panel; the architecture's tests cover the carriage.

**SD-28. synthD's restatement.** The server MUST write synthD's restatement as MIDI-93 to MIDI-99 require, and it MUST be exactly these events, at one tick, in this order (MIDI-95): (1) the program change of the patch last chosen, or, where the last patch came inline as the 47 control changes of SD-26, those 47 control changes; (2) then, in ascending order of controller number, the latest value of every panel controller of SD-17 moved by a control change since (a reset all controllers that turned the GLIDE switch off counts as moving controller 65, SD-13 item 3), each coarse controller before its fine one; (3) then, where the pitch bend range is not the default of SD-6, the registered parameter 0 sequence that sets it (controller 101 at 0, controller 100 at 0, controller 6 the semitones, controller 38 the cents), followed by controller 101 at 127 and controller 100 at 127 so that no parameter is left selected; (4) then pitch bend, controller 7, controller 1 and controller 64, each only where it is not at the value a fresh synthD holds (pitch bend 8,192, controller 7 at 127, controller 1 at 0, the pedal up). Held notes MUST NOT be restated. The server MUST write it in the first block of a live sound and at least once in every 50 blocks after (MIDI-96), and at tick 0 of block 0 of a stored sound (MIDI-99). synthD MUST render identical samples with and without a restatement that carries the state it already holds (MIDI-97): a program change to the patch already set, and a control change to the value a control already holds, MUST NOT restart the contours, reset the oscillators' phases or move the filter's state.
- Reason: A viewer who joins a live sound late, or loses a block, has none of the program changes and control changes sent before; the server, which sees every event, restates the whole state (DEC-6462 item 1). A restatement goes to every viewer, most of whom lost nothing, so it must be inaudible to them. Clearing the selection at the end keeps a later data entry from changing the range unasked. Volume is compared with a fresh synthD's 127 rather than with its value after a reset, since a reset leaves volume unchanged (MIDI-84) and a joining viewer's synthD starts at 127 (MIDI-82).
- Source: MIDI-82, MIDI-84, MIDI-93 to MIDI-99; DEC-6410 item 12; DEC-6462 item 1.
- Verification: A test drives synthD through a program change, an inline patch, ten panel control changes, a bend range and a bend, then plays the server's restatement into a fresh synthD and checks the two panels, ranges and wheels equal; a test plays the audio demo's synthD tune with and without a restatement at a seeded random tick of every block and checks the samples identical; a server test checks the bytes of the restatement for a known state.

---

## 10. The Voyager's panel against synthD's, control by control

The Voyager manual gives no controller number for any control below except the modulation wheel (1). For every other row, "controller number: not stated in the source" applies, and so do "coarse and fine pair", "range of values" and "value bands". The comparison is of the two panels, from the Voyager manual's sections and its figure of page 44, and from the Model D manual.

"Has it" means synthD's panel has a control of the same kind and range. "Has it differently" means synthD has a control for the same purpose whose positions or range differ. "Lacks it" means the instrument modelled has no such control, and synthD has none.

| Voyager control | What the Voyager manual says of it (page) | synthD |
|---|---|---|
| LFO RATE | The dedicated low-frequency oscillator's rate, 0.2 Hz to 50 Hz (33, 34) | **Lacks it.** The modelled instrument has no dedicated low-frequency oscillator; oscillator 3 at LO serves (Model D manual, page 6). |
| LFO SYNC | Four positions: OFF/SYNC, MIDI, KB, ENV. GATE (34) | **Lacks it.** |
| Mod wheel bus SOURCE | Six positions: LFO triangle, LFO square, oscillator 3, sample and hold, ON/MOD2, NOISE/PGM (31) | **Has it differently:** the MODULATION MIX knob (control 3) blends oscillator 3 and noise; there is no low-frequency oscillator, sample and hold or fixed level to choose. |
| Mod wheel bus DESTINATION | Six positions: PITCH (all oscillators), OSC. 2, OSC. 3, FILTER, WAVE, LFO/PGM (31, 32) | **Has it differently:** the OSCILLATOR MODULATION switch (27) and the FILTER MODULATION switch (35), which may both be on; no destination of one oscillator, of the waveform or of a rate. |
| Mod wheel bus SHAPING | Four positions: FILT. ENV., VELOCITY, PRESSURE, ON/PGM (31) | **Lacks it.** |
| Mod wheel bus AMOUNT | 0 to 10: the most modulation the wheel lets through (32) | **Lacks it.** The wheel alone sets the amount. |
| Pedal/On bus SOURCE | As the mod wheel bus's (30, 31) | **Lacks it.** The modelled instrument has one modulation path. |
| Pedal/On bus DESTINATION | As the mod wheel bus's | **Lacks it.** |
| Pedal/On bus SHAPING | As the mod wheel bus's | **Lacks it.** |
| Pedal/On bus AMOUNT | 0 to 10 | **Lacks it.** |
| FINE TUNE | Tunes the oscillators "+ or − 2 semitones"; not stored in a preset (20, 45) | **Has it:** TUNE (control 1), ±242 cents, and it is part of the patch. |
| GLIDE RATE | "The glide can vary from a very fast to a very slow glide" (21) | **Has it:** GLIDE (control 2). |
| Oscillator 1 OCTAVE | Six positions, 32′, 16′, 8′, 4′, 2′, 1′ (19) | **Has it differently:** RANGE (control 4) is LO, 32′, 16′, 8′, 4′, 2′: it has LO and has no 1′. |
| Oscillator 1 WAVE | Continuously variable through triangle, sawtooth, square and rectangular (20) | **Has it differently:** WAVEFORM (control 5) is a switch of six fixed waveforms. |
| Oscillator 2 FREQUENCY | "+ or − 7 semitones relative to Osc. 1" (19, 20) | **Has it:** control 7, ±700 cents. |
| Oscillator 2 OCTAVE | As oscillator 1's | **Has it differently:** control 6, as control 4. |
| Oscillator 2 WAVE | As oscillator 1's | **Has it differently:** control 8. |
| Oscillator 3 FREQUENCY | As oscillator 2's; a greater range with 3 KB CONT off (20) | **Has it:** control 10, and 2.75 octaves either way with OSC. 3 CONTROL off. |
| Oscillator 3 OCTAVE | As oscillator 1's | **Has it differently:** control 9. |
| Oscillator 3 WAVE | As oscillator 1's | **Has it differently:** control 11; its second position is the reverse sawtooth. |
| 1–2 SYNC | Oscillator 2 synchronised to oscillator 1 (20) | **Lacks it.** |
| 3–1 FM | Linear frequency modulation of oscillator 1 by oscillator 3 (21) | **Lacks it.** |
| 3 KB CONT | Oscillator 3's keyboard control on or off (20) | **Has it:** OSC. 3 CONTROL (control 28). |
| 3 FREQ | Oscillator 3's range, LO or HI (20) | **Has it differently:** LO is a position of each oscillator's RANGE switch. |
| Mixer EXTERNAL level and switch | The external audio input's level, 0 to 10, and on or off (17) | **Has it differently:** controls 15 and 32; synthD's external input is fed from its own output. |
| Mixer OSCILLATOR 1, 2, 3 levels and switches | Level 0 to 10 and on or off, each (17) | **Has them:** controls 12, 13, 14 and 29, 30, 31. |
| Mixer NOISE level and switch | Level 0 to 10 and on or off; the noise "is a white/pink hybrid" (17) | **Has them:** controls 16 and 33. synthD also has the WHITE / PINK switch (34), which the Voyager lacks. |
| Filter CUTOFF | The cutoff of both filters; the dial is marked in hertz from 20 to 12K (22, 24) | **Has it differently:** CUTOFF FREQUENCY (control 17), one filter, a dial of −5 to +5. |
| Filter SPACING | The difference between the two filters' cutoffs, −3 to +3 octaves (25) | **Lacks it.** One filter. |
| Filter RESONANCE | 0 to 10; self-oscillation from 8 (23, 25) | **Has it:** EMPHASIS (control 18), oscillation from 7.5 as built. |
| KB. CONT. AMOUNT | A knob, 0 to 10: how far the cutoff follows the keyboard (25) | **Has it differently:** two switches, KEYBOARD CONTROL 1 and 2 (controls 36 and 37): none, a third, two thirds or all. |
| Filter MODE | Dual lowpass, or highpass and lowpass (23, 24) | **Lacks it.** |
| Filter envelope ATTACK | 1 millisecond to 10 seconds (26) | **Has it:** control 20, 0 to 10,000 milliseconds (the Model D manual, page 11, says 10 milliseconds to 10 seconds). |
| Filter envelope DECAY | 1 millisecond to 10 seconds (26) | **Has it:** control 21. |
| Filter envelope SUSTAIN | A level (26) | **Has it:** control 22. |
| Filter envelope RELEASE | 1 millisecond to 10 seconds (27) | **Lacks it.** The DECAY switch (control 39) makes the DECAY TIME the release. |
| AMOUNT TO FILTER | −5 to +5: the envelope adds to the cutoff or subtracts from it (27) | **Has it differently:** AMOUNT OF CONTOUR (control 19), 0 to 10, which only adds. |
| Volume envelope ATTACK, DECAY, SUSTAIN | As the filter envelope's (26) | **Has them:** controls 23, 24, 25. |
| Volume envelope RELEASE | As the filter envelope's (27) | **Lacks it,** as above. |
| ENV. GATE | The envelopes are triggered from the keyboard, or held on, or triggered from outside (27) | **Lacks it.** The modelled instrument has a shorting plug for its trigger input (Model D manual, page 14), which is not a panel control; synthD has no external trigger. |
| MASTER VOLUME | "Full-clockwise is maximum output, full-counterclockwise silences" (29) | **Has it:** main output VOLUME (control 26). |
| HEADPHONE VOLUME | The headphone jack's volume (29) | **Lacks it.** synthD has one output. |
| PITCH BEND wheel | "Affects the pitch of all three oscillators" (35) | **Has it:** pitch bend (SD-6). |
| MOD WHEEL (controller 1) | The amount of the mod wheel bus's modulation (35) | **Has it:** SD-9. |
| GLIDE switch | "Turns on and off the GLIDE circuit" (35) | **Has it:** control 38. |
| RELEASE switch | "Used to shorten the Release time of both the filter and Volume envelopes" (35) | **Has it differently:** the DECAY switch (control 39): off, a released note is cut; on, it falls at the DECAY TIME. |
| Touch surface X, Y and A | Filter cutoff, filter spacing and filter resonance, while touched (36) | **Lacks it.** |
| Volume (controller 7) | "Volume Controller (CC7)" (46, 51); which control it moves is not stated | **Has it:** SD-10. |

The settings the Voyager keeps in its EDIT mode, none of which has a message in the source, are in section 12.1.

**Controls synthD has that the Voyager's panel lacks.** These exist on the instrument modelled and have no counterpart of the same kind on the Voyager's panel, so even a complete Voyager control-change map could not move them as they are:
1. MODULATION MIX (control 3): a continuous blend of oscillator 3 and noise. The Voyager chooses one source with a switch.
2. OSCILLATOR MODULATION (27) and FILTER MODULATION (35) as two switches that may both be on. The Voyager chooses one destination with a switch.
3. Noise WHITE / PINK (34). The Voyager's noise is one "white/pink hybrid".
4. KEYBOARD CONTROL 1 and 2 (36, 37) as two switches. The Voyager has a knob.
5. The DECAY switch (39) as the choice between a cut and a fall at the decay time. The Voyager has RELEASE knobs and a RELEASE switch that shortens them.
6. The LO position of the RANGE switches of oscillators 1 and 2 (controls 4 and 6). The Voyager has LO for oscillator 3 only, by a separate switch.
7. The six fixed positions of each WAVEFORM switch (5, 8, 11), among them the sawtooth-triangular and oscillator 3's reverse sawtooth. The Voyager's wave control is continuous and its manual names four shapes.

How these are controlled is settled by section 7 if the owner approves it; if a later Voyager map is adopted instead, it is open question 2.

## 11. Could the Voyager's own preset system exclusive be the patch?

**The facts in the Voyager manual.**
1. The Voyager transmits and receives "System Exclusive Data (software and preset banks)" (page 46); the chart marks system exclusive as transmitted and recognised, "Must be enabled" (page 51).
2. SEND PRESETS "is a utility to send Sysex (System Exclusive) data for archiving the bank of presets in the Voyager's memory", to "another Voyager, or a computer with a MIDI interface and a program that can accept a manual Sysex dump" (page 39).
3. RECEIVE PRESETS "is a utility to import Sysex data for a bank of Voyager presets"; the Voyager "must be enabled to receive the presets", it shows "Sysex enabled", and the transfer "will replace any presets that are in memory" (page 39).
4. SEND SYSTEM ROM, SEND BOOT SYSTEM and RECEIVE UPDATE carry the Voyager's own software (page 40).
5. A bank is 128 presets (pages 45 and 48). A preset stores "all the Voyager's current front panel settings, Pitch Bend Amount, Programmable Mod Sources and Destinations, Keyboard Mode, Trigger Mode, and Preset Name" (page 44), with a name of "up to 24 characters" (page 44), and not FINE TUNE (page 45).
6. Not stated in the source: the manufacturer's identifier, the header, the length of the message or of a preset, the order and coding of the parameters, any checksum, whether the bank is one message or many, and whether a single preset can be sent. The manual gives no byte of the message.

**Recommendation: it cannot be used, and should not be.** First, it cannot be implemented from the filed documents: the format is not documented in them, and filling it in from anywhere but a filed document is forbidden. Second, even with the format in hand it would be a poor fit: a Voyager preset holds a different panel (section 10), so most of its content would be discarded and seven kinds of synthD's controls would have nowhere to go. Third, it exists only as a whole bank of 128, received only when a person enables it. A synthD patch is therefore the list of control-change values of SD-22, as decision A4 already rules.

## 12. What is left out, and what departs

### 12.1 Of the adopted interface: left out

| Item of the Voyager's interface | Where the manual has it | Why synthD leaves it out |
|---|---|---|
| The MIDI IN CHANNEL setting, 1 to 16, and Omni Off | Pages 39 and 51 | A global setting of the hardware with no message; synthD hears all channels (SD-2). |
| The MIDI OUT CHANNEL setting and everything transmitted (notes 53 to 96 with velocity, program change, system exclusive) | Pages 39, 46 and 51 | synthD transmits nothing: a NeoTeletext instrument only receives. |
| SEND PRESETS and RECEIVE PRESETS, the system exclusive bank of presets | Page 39 | Undocumented in the source, a different panel, a whole bank only (section 11). |
| SEND SYSTEM ROM, SEND BOOT SYSTEM, RECEIVE UPDATE | Page 40 | They carry the Voyager's own software; they serve only its hardware. |
| LCD CONTRAST | Page 39 | Hardware only. |
| PITCH BEND AMOUNT, a setting of each preset: Off, ±2 semitones, ±minor third, ±major third, ±fourth (the default), ±fifth, ±1 octave, ±1 octave and a fifth, ±2 octaves, ±2 octaves and a fifth | Pages 41 and 42 | No message sets it in the source, and synthD's patch has no place for it. synthD's range is set instead by registered parameter 0 (SD-6, MIDI-90), from a default of the instrument modelled's one range, 797 cents, up to the largest of these ten choices. |
| KEYBOARD MODES, a setting of each preset: Lower Key, Higher Key, Last Key, 1 Key Only | Page 43 | No message sets it. synthD has the modelled instrument's lowest key (SD-14), which is the first of the four. |
| TRIGGER MODES, a setting of each preset: Single Trigger, Multi Trigger | Page 43 | No message sets it. synthD has the modelled instrument's single trigger (SD-15). |
| PROGRAMMABLE MOD WHEEL SOURCE and PEDAL/ON SOURCE, each one of Noise, Filter ENV, Amplitude ENV, Smoothed Sample and Hold, Oscillator 1, Oscillator 2, Touch Surface X, Touch Surface Y | Page 42 | synthD has no modulation busses. |
| PROGRAMMABLE MOD WHEEL DESTINATION and PEDAL/ON DESTINATION, each one of LFO Rate, Filter Resonance, Filter Spacing, Panorama, Osc. 1 Level, Osc. 2 Level, Osc. 3 Level, Noise Level | Pages 42 and 43 | As above. |
| TOUCH SURFACE MEMORY | Page 43 | synthD has no touch surface. |
| PRESET NAME, up to 24 characters | Page 44 | A synthD patch has no name; a sound's label is the audio profile's (the architecture document). |
| RECALL, REAL PANEL CONTROL, INITIALIZE PARAMETERS, SAVE PRESET, QUICK MODE, PARAMETER DISPLAY, and the HEADPHONE VOLUME and MASTER VOLUME options of PANEL mode | Pages 41 to 45 | Operations of the Voyager's own panel and memory, with no message. |
| That a preset leaves FINE TUNE out | Page 45 | synthD's patch includes TUNE, as today's does: a sound is then complete in one patch. This is a departure, listed here so that it is not silent. |
| Every Voyager panel control that section 10 marks "lacks it": LFO RATE, LFO SYNC, both busses' SOURCE, DESTINATION, SHAPING and AMOUNT, 1–2 SYNC, 3–1 FM, filter SPACING, filter MODE, both RELEASE knobs, ENV. GATE, HEADPHONE VOLUME, the touch surface's X, Y and A | Section 10 | The instrument modelled has none of them. |
| The back panel's control and gate inputs (pitch, wave, filter, envelope rate, volume, pan, MOD1, MOD2, LFO rate, sample and hold, envelope gate, release, LFO sync, sample and hold gate), the mix-out loop and the accessory port | Pages 14, 18, 21, 25, 27 to 29, 32, 34, 37 | Voltages at jacks, not messages. |

### 12.2 Of the adopted interface: taken with a difference

| Item | The Voyager | synthD | Requirement |
|---|---|---|---|
| Channel | One channel, Omni Off | All channels alike | SD-2 |
| Pitch bend range | Ten choices a preset, default ±fourth, no message | Set by registered parameter 0, as in every synthesizer; default 797 cents either way, at most 3,100 (pending the architecture's open question 5) | SD-6, MIDI-90 |
| Pitch bend resolution | Not stated in the source | All 14 bits, as in every synthesizer | SD-6, MIDI-91 |
| Reset all controllers, controller 121 | Not recognised (page 51 names controllers 1 and 7 only) | Acted on, RP-015's reset with volume unchanged and the GLIDE switch, controller 65, off, as in every synthesizer | SD-13, MIDI-84 |
| All sound off, controller 120 | Not recognised | Acted on, a fade within 256 samples, as in every synthesizer | SD-13, MIDI-86 |
| Sustain pedal, controller 64 | Not recognised | Acted on, down at 64 to 127, as in every synthesizer | SD-13, MIDI-87 |
| Note on of velocity 0 | Not stated in the source | A note off, as in every synthesizer | SD-3, MIDI-88 |
| Mode messages, controllers 124 to 127 | Not listed (the chart's mode messages are "All Notes Off") | Each acted on as all notes off and nothing more, as in every synthesizer | SD-13, MIDI-89 |
| Note priority | Four modes a preset | Lowest key | SD-14 |
| Trigger | Two modes a preset | Single | SD-15 |
| Program change | Recalls a preset without FINE TUNE | Sets the whole panel, TUNE included | SD-12 |
| Controller 7 | "Volume Controller"; what it moves is not stated | A gain beside the panel's VOLUME, by the law every synthesizer shares | SD-10, MIDI-82, MIDI-92 |

The rows from pitch bend resolution to the mode messages are the common behaviours of `midi-architecture.md`, section 11.1, which the owner requires to be the same in every synthesizer (DEC-6464); each is a departure from the Voyager's interface, which does not state or does not recognise it, made for that reason.

### 12.3 Of the instrument modelled: controls synthD's panel does not have

These are on the Model D's panel or rear and are not among synthD's 39 controls, so no controller moves them. They are as built today.

| Control of the instrument modelled | Model D manual | Why not |
|---|---|---|
| POWER switch (P) | Page 4 | Hardware. |
| MAIN OUTPUT switch (M) | Pages 3 and 4 | A sound is started and stopped by the audio profile's play and stop. |
| A-440 switch (Q) and its tone | Page 4 | A tuning aid for a drifting instrument; synthD is in tune by construction. |
| HEADPHONE VOLUME (27) and the PHONES jack (N) | Page 4 | One output. |
| The OVERLOAD lamp | Page 9 | Nothing to show it on. |
| The EXT. SIGNAL INPUT jack | Page 9 | No outside signal reaches a NeoTeletext instrument; the input is fed from the instrument's own output, and EXTERNAL INPUT VOLUME (control 15) sets how much returns. |
| The rear panel's control inputs (volume, pitch, filter), the trigger input and its shorting plug, and the GLIDE and DECAY foot switch jacks | Pages 1 and 14, PDF pages 18 to 21 | No outside voltage reaches a NeoTeletext instrument. |
| The rear panel's trimmers | PDF pages 22 and 23 | Service adjustments. |

## 13. What NeoTeletext defines itself

Each item exists because the filed interface does not define it. Each is replaced if open question 1 is answered by filing a document that does.

1. **The controller numbers of the 39 panel controls (SD-17).** The Voyager manual gives none. The numbers follow five stated rules (SD-17's reason) so that nothing collides with a controller MIDI 1.0 defines and the two that MIDI 1.0 already names for glide are used as named.
2. **The scaling of a value to a field (SD-18, SD-19).** The manual gives no curve. Linear in the panel's own units, in integers, exact both ways, with a coarse and fine pair only where a field has more than 128 values.
3. **The value bands of the selectors and switches (SD-20).** The manual gives none. Six near-equal bands; on from 64.
4. **The patch as 47 values in panel order (SD-22), and its equivalence to 47 control changes (SD-26).** No patch format exists for the instrument modelled, and the Voyager's is undocumented and of another panel (section 11).
5. **The default patch (SD-21).** As built.
6. **Controllers 64, 120 and 121 and the mode messages 124 to 127 (SD-13).** Standard MIDI 1.0 messages that the Voyager's chart does not recognise, taken as part of NeoTeletext's common layer (MIDI-9) with the one behaviour each of `midi-architecture.md`, section 11.1; 64, 120 and 121 as built.
7. **All sixteen channels as one (SD-2).** As built.
8. **The pitch of a MIDI key (SD-5).** The manual does not state it; the modelled instrument's tuning, as built.
9. **The modulation wheel's curve (SD-9).** The manual does not state it; the square, as built.
10. **Controller 7 as a gain beside the panel's VOLUME, its law and its slew (SD-10).** The manual does not say what controller 7 moves; as built.
11. **The pitch wheel's default range and its most, and registered parameter 0 to set it (SD-6); the lowest-key priority and single trigger (SD-14, SD-15).** The Voyager makes each a setting of a preset with no message. synthD takes the modelled instrument's priority, trigger and default range; its range is set by registered parameter 0, which MIDI-90 adds to every adopted interface, up to the Voyager's largest choice, 31 semitones, a limit of NeoTeletext's choosing; and increment and decrement step it by one cent, NeoTeletext's own reading.
12. **How a moved control is heard (SD-23): the slews.** As built and measured.
13. **The drift of the oscillators.** Each oscillator's pitch wanders by up to 2 cents by default; the instrument can be set from 0 to 50 cents (`set_drift` in `mod.rs`). It is not a control of the panel, it is not in the patch, and nothing on the wire sets it today. This document adds no message for it: it stays at its default. If the owner wants it set by a channel, it needs a controller of its own, which would be a 40th control and a 48th byte.
14. **synthD's restatement, event by event (SD-28).** The architecture sets the rule (MIDI-93 to MIDI-99); the exact events for synthD's panel, and the closing null parameter number, are this document's within it.

## 14. Open questions for the owner

**1. The panel's controller numbers: look for a later edition of the Voyager manual, or approve NeoTeletext's own?**
The filed manual (version 1.0 of the software, 2003) names two controllers and no others. DEC-6455 and `documents.tsv` describe it as holding a full map with coarse and fine pairs, so whoever researched it believed such a map exists; this file does not contain it, and its own words ("current as of 02/05/03 … Version 1.0") allow that a later version differs.
- *Option A: look for a later edition and file it.* If one documents control changes for the panel, the controllers and pairs of section 7 are replaced by its numbers for every control the two panels share (section 10's "has it" rows), its curves and bands are taken where it states them, and the patch of SD-22 is rebuilt in the same way. The seven kinds of control that only synthD has (section 10) still need numbers of NeoTeletext's own (question 2). This is what DEC-6453 asks for, if the document exists.
- *Option B: approve section 7 as NeoTeletext's own.* It is complete and can be built now. It is compatible with nothing outside NeoTeletext, which DEC-6453 permits only "where no existing interface covers the instrument".
- *Option C: adopt another instrument's interface for the same panel.* DEC-6455 records that the maker's reissues of the instrument modelled take MIDI "for notes, pitch bend and modulation only"; no document of theirs is filed, so nothing can be said of them here.
- *Recommendation:* A first, as a short search by the owner or the main session (this document's author was not permitted to fetch anything); if no edition with a panel map can be filed, B. Sections 4, 5, 8 and 10 to 12 stand under either answer; only the numbers, pairs and bands of sections 7 and 9 change.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, a search for a later edition of the Voyager manual with a panel controller map, begun at once; if none is found, section 7 is approved as NeoTeletext's own (option B). The document stands as written meanwhile.

**2. If a Voyager map is adopted (option A), how are the controls that only synthD has controlled?**
They are MODULATION MIX, the two modulation switches, WHITE / PINK, the two KEYBOARD CONTROL switches, the DECAY switch, LO on oscillators 1 and 2, and the six fixed waveforms.
- *Option A: controllers of NeoTeletext's own,* from those the adopted map and MIDI 1.0 both leave unused, by the rules of SD-17. Exact, and clearly marked as additions.
- *Option B: non-registered parameter numbers,* keeping every ordinary controller for the Voyager's map. Four messages a change where a controller needs one.
- *Option C: fold each onto the nearest Voyager control* (for example the two KEYBOARD CONTROL switches as four bands of the Voyager's keyboard amount knob; the six waveforms as six bands of the continuous wave control; the DECAY switch as the RELEASE switch). A Voyager-style controller then moves something on synthD, but the meanings differ, MODULATION MIX and WHITE / PINK have nothing to fold onto, and a value written for a Voyager would not sound the same.
- *Recommendation:* A for the controls with no counterpart (MODULATION MIX, the two modulation switches, WHITE / PINK), and C only where the Voyager's control has the same purpose and the bands can be stated exactly (the keyboard amount, the octave and wave selectors, the release switch), decided control by control once the map is in hand.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, and only if question 1's search finds a map: controllers of NeoTeletext's own for the controls only synthD has, folding onto a Voyager control only where its purpose and bands are the same.

**3. Should controller 7 be the panel's VOLUME knob, or stay beside it?**
The source does not say what the Voyager's controller 7 moves. SD-10 keeps what is built: two gains, the patch's VOLUME (controller 87) and a performance volume (controller 7).
- *Option A: keep both* (SD-10). A patch's level and a score's fades are independent; controller 7 behaves the same on every NeoTeletext synthesizer.
- *Option B: one knob.* Controller 7 moves the panel's VOLUME, controller 87 is not used and the patch is 47 bytes with byte 33 carried by controller 7. Simpler, and nearer to "the Voyager's volume is in its preset", but a program change then overwrites a fade, and the shared volume law would replace the knob's linear law, which changes the level of every existing patch whose VOLUME is not 100.
- *Recommendation:* A. The architecture document should rule the same way for every family.
- *Status:* answered by the architecture, subject to the owner's approval of it: MIDI-82 and MIDI-92 make controller 7 in every synthesizer a gain on the part's output, separate from any volume of the patch, by one law. That is option A, which SD-10 states.

**4. Should reset all controllers turn synthD's GLIDE switch off?**
synthD's GLIDE switch is a panel control of the patch, carried by controller 65 because MIDI 1.0 names 65 the portamento switch (SD-17, rule (b)). MIDI-84, following DEC-6464's reading of RP-015, both resets "the sustain, portamento, sostenuto and soft pedals, controllers 64 to 67, off where the family has them" and leaves unchanged "every parameter of the patch moved by a control change"; for synthD's controller 65 the two clauses disagree.
- *Option A* (written, SD-13 item 3): the GLIDE switch is a parameter of the patch and is left as it is; a reset changes no part of the sound's patch.
- *Option B:* the GLIDE switch is turned off, as RP-015's portamento switch; a reset then changes the patch's glide, and a restatement (SD-28) must restate controller 65 after it.
- *Option C:* move the GLIDE switch off controller 65 to an undefined controller under MIDI-78 rule 5, so that controller 65 is not the patch's; breaks SD-17's rule (b), which uses the controller MIDI 1.0 names.
- *Recommendation:* A, until RP-015 is filed and read (`midi-architecture.md`, section 1.5); if its text resets controller 65 whatever it carries, B. The architecture's MIDI-84 should say which clause holds where a family's patch parameter sits on controllers 64 to 67.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written (SD-13 item 3): controller 121 leaves the GLIDE switch as the patch set it; revisited when RP-015 is filed.
- Revisited on 18 November 2026, when RP-015 was filed (rdm SRC-6468): its text sets controller 65 whatever it carries ("Set Pedals (#64, #65, #66, #67) to 0", page 2), DEC-6464 version 2 limits a manufacturer's latitude to the other controllers (item 4) and makes RP-015 hold where a family would depart from it (item 6), and MIDI-84 item 2 now says that the pedals 64 to 67 are set to 0 wherever a family responds to one with its pedal meaning, even as a parameter of its patch. Option B is therefore written (SD-13 item 3, SD-28), as this question's recommendation said it would be if RP-015 read so; it replaces DEC-6465's answer A and awaits the owner's confirmation with DEC-6464.

**Questions of the architecture that change this document.** Two of `midi-architecture.md`'s open questions (section 20) decide parts of this document and are not repeated here: open question 1, the codec numbers (synthD's code 15 or its present code 7; the scope above; answered by DEC-6465 with new codes 12 to 19, awaiting the owner's confirmation), and open question 5, the pitch bend range by registered parameter 0 in every family, which SD-6 is written for under its recommended option A, with what SD-6 would be under option B stated there.

## 15. Differences from what is built today

What exists is described in `synthesizer-wire-format.html` and in synthD's source. Implementing this document changes the following.

**The patch.**
1. Today a patch is 36 bytes of NeoTeletext's own design (`PATCH_BYTES`, `Patch::from_bytes`, `Patch::to_bytes` in `patch.rs`): fields in the panel's units, two-byte fields with the low byte first, and thirteen switches packed as bits into bytes 34 and 35. It becomes 47 bytes, each a control change's value from 0 to 127 (SD-22). The 39 fields, their units and their ranges do not change; only their coding does.
2. Today's two-byte signed fields (TUNE, both FREQUENCY knobs, CUTOFF FREQUENCY) and two-byte times become coarse and fine pairs scaled by SD-18. Today's one-byte knobs, 0 to 100, become values 0 to 127 scaled by SD-19. Today's range and waveform bytes, 0 to 5, become values in six bands (SD-20). Today's two switch bytes become thirteen bytes, one a switch.
3. Today a patch is refused for a field out of range (`PatchError`: a knob above 100, a position above 5, a time above 10,000, an unused switch bit). After the change every value from 0 to 127 is valid in every byte, and the only faults are the length and a byte above 127. `PatchError`'s seven kinds reduce to those two.
4. The engine's `SYNTHD_PATCH_BYTES` (`neoteletext-audio/src/codec.rs`), the server's patch check and its refusal messages, and the documents' "36 B" all follow. The kit's `packSynthdPatch` (today's 36-byte builder under its new name) and its initial patch are removed from the kit (DEC-6462 item 3, MIDI-22): the server takes a patch as named fields in the panel's units and writes canonical values (MIDI-14, SD-22), and the kit keeps only the generated types and the call that sends them.
5. A DATA record of a synthD bank holds 28 patches of 36 bytes today. Under MIDI-55 a bank image is instead cut into pieces of 1,011 bytes whatever its patches' boundaries, so a bank of 128 patches of 47 bytes, 6,016 bytes, travels in six DATA records.

**The messages.**
6. Today synthD takes control changes of controllers 1, 7, 64, 120, 121 and 123 only, and counts every other as ignored (`control_change` in `mod.rs`). It gains the 47 controllers of SD-17 (39 controls, eight of them with a fine controller), each setting one field. `SynthD` needs a way to set one field and keep the 14-bit numbers of the eight pairs; `set_patch` remains as the way a patch and a program change set all 39.
7. Today the server and the kit refuse a control change of any controller but 1, 7, 64, 120, 121 and 123 ("a control change is of controller 1, 7, 64, 120, 121 or 123"). For synthD the server must allow the controllers of SD-17, the registered parameter controllers of SD-6 and the mode messages 124 to 127 as well (MIDI-10); the kit's copy of the rule is removed (MIDI-22).
8. Today a program change chooses patch 0 to 31 and a bank holds 1 to 32 patches. They become 0 to 127 and 1 to 128 (SD-12, SD-27). Today a program change must have a second data byte of 0 in its four-byte slot; under decision A3 a program change is the ordinary two-byte MIDI message.
9. Today a patch missing from the bank or out of range becomes the default with no message. After the change a program change to a missing patch is also counted as ignored (SD-12).
10. Nothing changes in note on, note off, the pitch bend's 14-bit reading, the modulation wheel, controller 7, the sustain pedal, all sound off or all notes off: SD-3 to SD-5, SD-9 to SD-11 and SD-13 items 1 and 2 describe what is built. Three things change in the common layer: synthD gains registered parameter 0 for its bend range, with the parameter number selection, increment and decrement (SD-6), which today it counts as ignored; it gains the mode messages 124 to 127 as all notes off (SD-13 item 4), which today it counts as ignored; and reset all controllers and a lost block also clear the parameter number selection (SD-13 item 3, SD-25). The lowest-key priority, the single trigger and the glide (SD-14 to SD-16) are as built.
11. Today key pressure, channel pressure and every other status are counted as ignored; that stays. System exclusive, which today cannot be expressed in a four-byte slot, can be expressed under decision A3 and is counted as ignored (SD-8).

**The block.**
12. Today a synthD block is 1 to 16 slots of four bytes (a time, a status byte, two data bytes), under codec 7. Under decision A3 it becomes a Standard MIDI File track-event list with a tick of 0.1 millisecond, of at most 1,005 bytes and 256 events (MIDI-23 to MIDI-38), under codec 15 if the architecture's open question 1 is answered as recommended, or still under codec 7 if not; DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation), so it is codec 15. That change is the architecture's and is the same for every family; synthD's part of it is only that a whole panel as control changes (47 events, SD-26) no longer has to fit in 16 slots.

**The restatement.**
13. Today the kit's program repeater rewrites each part's last program change every 500 milliseconds (`program-repeater.ts`), and nothing restates synthD's panel control changes. Under SD-28 the server restates synthD's whole state (program or inline patch, every panel controller moved since, the bend range, the wheels, the volume and the pedal), and the kit's repeater is removed (MIDI-22, MIDI-93 to MIDI-99).

**Tests and documents.**
14. The tests that build patches from bytes (`tests/synthd_instrument.rs`, `tests/synthd_control_sweep.rs`, `tests/synthd_support.rs`, the engine's `tests/synths.rs`, the server's and the kit's patch tests, and the validation script `minimoog/validation/patch_hex.py`) change to the 47-byte form. New tests are those each requirement's "Verification" names.
15. The module documentation of `patch.rs` ("its byte form is this crate's own", the byte layout table) and of `mod.rs` (the list of messages taken) are rewritten to cite this document's requirements once they are rdm requirements. The two HTML documents in `teletext-reference/synthesizers/` describe the old form and are regenerated.
16. `minimoog/documents.tsv`'s row for the Voyager manual and DEC-6455's paragraph on the programming interface say the manual holds a control-change map with coarse and fine pairs. Both are to be corrected to what the file holds: controllers 1 and 7 only, and an undocumented system exclusive bank dump.
