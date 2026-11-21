# synthD: the programming interface

**Purpose.** This document specifies how synthD is played and programmed: every MIDI message it takes, what each does, what a synthD patch is, and how each value becomes a position of a control of synthD's panel. It is the basis for implementing synthD's part of the synthesizer protocols.

**Scope.** synthD only: the instrument that models the Moog Minimoog Model D (`neoteletext-common/docs/audio/synthesizers.md` says once which instrument each synthesizer models). The transport (blocks, records, packets), the form of a block, how a bank of patches is stored and named, the restatement of a live sound, and the behaviours common to every synthesizer belong to the architecture document, `midi-architecture.md` in this folder; this document states what synthD needs of them and refers to it by requirement number (MIDI-n). Under DEC-6462 the server (neoteletext-app-server) is the one implementation of the programming interface: it encodes patches, builds blocks and records, checks everything with the receiver's own code, splits what is too long and writes the restatements; the TypeScript and Python kits are thin clients that hold none of that logic (MIDI-13, MIDI-22). The sound of the instrument (its oscillators, filter and contours) is not specified here.

**synthD's codec.** synthD's sounds are of the event codec the architecture numbers 15, and its banks of the bank codec 19, if the architecture's open question 1 (`midi-architecture.md`, section 20) is answered as it recommends (MIDI-107 to MIDI-109); otherwise synthD keeps its present code, 7, with the new content. DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired, so synthD's code is 15 and its banks' 19.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

**The adopted map.** The Voyager's user's manual of 2003 describes version 1.0 of the Voyager's software, which recognises two control changes only: controller 1, the modulation wheel, and controller 7, volume (its pages 46 and 51). Later versions of the software give every knob and switch of the Voyager's panel a controller, and two later manuals that print the map are now filed: the combined user's manual for operating system version 3.4 (2008; the map on printed pages 76 to 78, the MIDI implementation chart on printed page 89) and the Rack Mount Edition's manual for software version 2.6 (2005; the map on printed pages 53 and 54, the chart on printed page 58). They were found by the search that DEC-6465 answer 23 asked for (option A), and this document follows them as DEC-6465 answers 23 and 24 direct:
1. For every control that synthD's panel and the Voyager's share, synthD takes the Voyager's controller, or its pair of controllers, with the Voyager's printed value bands, as version 3.4 prints them (sections 6 and 7). Where version 2.6 prints otherwise, or a row is misprinted, the reading taken is stated (section 6).
2. The controls only synthD has take controllers of NeoTeletext's own, from the numbers that both MIDI 1.0's Table III and the Voyager's map leave unused, by a rule stated in SD-17; a synthD control is folded onto a Voyager control only where the purpose and the bands are the same.
3. Every controller of the Voyager's map that moves a control synthD lacks is counted as ignored (SD-17, table F).

The patch (section 9) is the list of those controllers' values: the Voyager's in ascending order of controller number, then NeoTeletext's own. The scaling of the Voyager's continuous controls onto synthD's units, which the map does not state, and the controllers of the synthD-only controls are NeoTeletext's own, and are listed in section 13.

---

## 1. Sources

All files are under `~/devel/synthesizer-reference/minimoog/`. Page numbers are the printed page numbers of each document.

| Short name here | File | What it is used for |
|---|---|---|
| **Voyager 3.4 manual** | `manuals/moog-minimoog-voyager-user-manual-combo-os3.4-2008.pdf` (116 pages; Moog's combined "Voyager User's Manual" for operating system version 3.4, © Moog Music 2008; its printed page n is the PDF's page n − 2) | The adopted interface's controller map. "How the Voyager handles MIDI", printed pages 76 to 78 (PDF 74 to 76): the table "The Voyager's MIDI CC data assignments", every front-panel control with its controller or pair and its value bands. Appendix E, "MIDI Implementation Chart", "Version 3.4", dated 6/23/08, printed page 89 (PDF 87). The MASTER mode's system exclusive utilities, printed pages 74 and 75 (PDF 72 and 73). Where it and the 2.6 manual differ, it is taken, being the later (section 6). |
| **Voyager 2.6 manual** | `manuals/moog-minimoog-voyager-rack-mount-edition-user-manual-os2.6-2005.pdf` (60 pages; "User's Manual for the Minimoog Voyager Rack Mount Edition", SKU MAN-MIN-05, software version 2.6, © 2002 and 2005; its printed page numbers equal the PDF's) | The second witness to the map: section 5, "MIDI", printed pages 53 and 54, the same assignments with the switch bands printed as 0 to 64 and 65 to 127, and the pedal destination and oscillator 3 frequency rows printed correctly; appendix D, the chart, "Version 2.5/030404", printed page 58; system exclusive of single presets, banks and the operating system, printed page 54. |
| **Voyager manual** | `manuals/moog-minimoog-voyager-user-manual-2003.pdf` (62 pages; "Minimoog Voyager User's Manual SKU#MAN-MIN-01", © Moog Music Inc. 2002, 2003; its printed page numbers equal the PDF's page numbers) | The Voyager's panel described control by control, and the MIDI of version 1.0 of its software. Section K.5 "MIDI" (page 46): the messages transmitted and recognised. Appendix D, "MIDI Implementation Chart", "Version 1.0/020503", dated 2/05/03 (page 51): the chart. Section K.2 "MASTER Mode" (pages 39 and 40): the MIDI channel settings and the system exclusive utilities. Section K.3 "EDIT Mode" (pages 41 to 44): pitch bend amount, keyboard modes, trigger modes, what a preset stores. Section K.4 "PANEL Mode" (page 45): presets and their numbers. Sections III and IV (pages 13 to 37) and the figure "Default Program for Minimoog Voyager" (page 44): the Voyager's panel, control by control. Appendix C (pages 48 to 50): the count of presets. |
| **Model D manual** | `manuals/moogminimoogownersmanual_archiveorg.pdf` (24 pages; "the minimoog synthesizer operation manual", "A Guide to the Operation of the Mini Moog Model D", Moog Music Inc.; its printed page n is the PDF's page n + 2; the loose sheets after page 14 are dated July 1971 and 4/12/72 and are cited by PDF page) | The panel of the instrument modelled: every control and switch, by the numbers (1 to 29) and letters (A to S) its figures give them; the keyboard's priority; the wheels; the DECAY switch. |
| **synthD's source** | `~/devel/neoteletext-renderer-teletext/crates/neoteletext-audio-instruments/src/synthd/patch.rs`, `mod.rs` and `law.rs`, as they stood on 18 November 2026 | What is built today: the patch fields and their units, the messages taken, the laws of the knobs. Each constant there names its own source (the service manual, the schematics, the sound charts). |
| **Wire format as built** | `~/devel/synthesizer-reference/synthesizer-wire-format.html` and `programming-the-synthesizers.html` (read from the code on 18 November 2026) | What exists today on the wire and in the kit, for section 15. |
| **Architecture** | `midi-architecture.md` in this folder (18 November 2026) | The block, the records, the bank, the restatement, the common behaviours of every synthesizer (its section 11.1, MIDI-84 to MIDI-92) and every bound; this document cites its requirements as MIDI-n. Where the two documents differ, it governs. |

**The filed MIDI standards.** The MIDI 1.0 Detailed Specification 4.2 and Standard MIDI Files 1.0, in the MIDI Manufacturers Association's bundle of document version 96.1 (rdm SRC-6469), and the Recommended Practice RP-015, "Response to Reset All Controllers" (rdm SRC-6468), are filed in `~/devel/teletext-reference/midi/`; `midi-architecture.md`, section 1.5, describes them and the form of their citations, "MIDI 1.0 4.2, printed page n (PDF m)", the PDF page being that of the filed file. This document uses MIDI 1.0 only for what is common to all MIDI: the status bytes, that a note on of velocity 0 is a note off, the pairing of controllers 0 to 31 with 32 to 63 as most and least significant bytes, the standard meanings of controllers 5, 64, 65, 120, 121 and 123 to 127, the controllers it leaves undefined, registered parameter number 0, and the centre of pitch bend; the null parameter number from the General MIDI Level 1 Developer Guidelines in the same bundle (page 6, PDF 315); and RP-015 through DEC-6464 version 2 and MIDI-84. Every statement below that rests on one of them was read against the filed copy on 18 November 2026 and cites the place it rests on.

Decisions this document follows: DEC-6453 (each instrument is programmed as its most well-known existing interface does it; NeoTeletext defines something only where nothing exists, and records why), DEC-6455 (the provenance of synthD and the choice of the Voyager's interface), DEC-6461 (the names), DEC-6462 (the Rust server is the core of the programming interface; the kits are thin), DEC-6464 (every synthesizer answers Reset All Controllers identically, by RP-015, volume unchanged; recorded as proposed, awaiting the owner's confirmation), DEC-6465 (the answers to this document's open questions; its answers 23 and 24 are what sections 6 and 7 carry out), DEC-6473 (synthD's GLIDE switch turned off by Reset All Controllers; the one-part families answer controllers 121 and 123 on every channel), DEC-6410 and DEC-6429 (instruments as codecs of the audio profile), DEC-6428 (the clean-room rules), and the architecture decisions A1 to A6 of the brief of 18 November 2026.

No web page was fetched and no reference program was opened for this document.

## 2. Terms

- **synthD.** NeoTeletext's monophonic synthesizer of three oscillators and a ladder filter. In identifiers it is written `synthd`.
- **The instrument modelled.** The Moog Minimoog Model D. It is named in this document only where a source is cited or the panel is described.
- **The adopted interface.** The MIDI implementation of the Moog Minimoog Voyager at version 3.4 of its operating system: the messages its chart recognises (Voyager 3.4 manual, printed page 89) and its controller map (printed pages 76 to 78).
- **The Voyager's map.** The table "The Voyager's MIDI CC data assignments" of the Voyager 3.4 manual, printed pages 76 to 78, reproduced in full in section 6.
- **Shared control.** A control of synthD's panel that has a control of the same purpose on the Voyager's panel, which synthD therefore moves by the Voyager's controller (SD-17). **synthD-only control.** A control of synthD's panel with no such counterpart, or whose counterpart's values have no stated bands that could be folded onto it; it takes a controller of NeoTeletext's own (SD-17).
- **Panel control.** One knob or one switch of synthD's panel. synthD has 39: the 26 knobs and selector switches and the 13 on-off switches that the patch of `patch.rs` holds. They are the panel of the instrument modelled, less the controls that serve only its hardware (section 12.3). Each oscillator's RANGE switch is one panel control carried by two controllers (SD-20).
- **Field.** The value of one panel control as synthD holds it, in the panel's own units (for example a contour's attack time in milliseconds, 0 to 10,000). The fields are those of `Patch` in `patch.rs`.
- **Controller.** A MIDI control change's controller number, 0 to 127. **Value** is its data byte, 0 to 127.
- **Coarse and fine pair.** Two controllers that together carry one 14-bit number: the coarse controller, numbered 0 to 31, carries the most significant seven bits, and the fine controller, numbered 32 higher, carries the least significant seven. The 14-bit number is `coarse × 128 + fine`, 0 to 16,383.
- **Canonical value.** The one value a sender writes for a given position of a control, where several values select the same position.
- **Patch.** The positions of all 39 panel controls. On the wire it is the 60 values of section 9.
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

The adopted interface is the Voyager's chart for version 3.4 (Voyager 3.4 manual, Appendix E, printed page 89, "Moog Music, Inc., Voyager Analog Synthesizer", "Date: 6/23/08", "Version 3.4"). The chart, row by row, in its "Recognized" column, with the same rows of the two earlier charts filed beside it: version 2.5 (Voyager 2.6 manual, printed page 58, "Version 2.5/030404") and version 1.0 (Voyager manual, page 51, "Version 1.0/020503").

| Chart row | Recognised, version 3.4 | Remarks in the 3.4 chart | Version 2.5 | Version 1.0 |
|---|---|---|---|---|
| Basic channel, default | 1 to 16 | Memorized | 1 to 16 | 1 to 16 |
| Basic channel, changed | 1 to 16 | Memorized | 1 to 16 | 1 to 16 |
| Mode, default | 4 (Omni Off, Mono) | "Note priority is user selectable" | 4 | 4 |
| Mode, messages | Yes | "All Notes Off" | Yes, "All Notes Off" | Yes, "All Notes Off" |
| Mode, altered | No | | No | No |
| Note number | 0 to 127 | | 0 to 127 | 0 to 127 |
| Note number, true voice | 0 to 127 | | 0 to 127 | 0 to 127 |
| Velocity, note on | No | "Note ON and Note OFF data is transmitted from the Voyager keyboard version only" | Yes | No |
| Velocity, note off | No | As above | Yes | No |
| After touch | No | "Aftertouch data is transmitted from the Voyager keyboard version only" | Yes | No |
| Pitch bend | Yes | "Pitch Bend data is transmitted from the Voyager keyboard version only" | Yes | Yes |
| Control change | Yes | "Receive: CC1-31 MSB. 33-63 LSB, 65-88" | Yes, "Receives CC 1-31 MSB, 33-63 LSB; 65-88" | Yes, "CC 1 (Mod Wheel), CC 7 (Volume)" |
| Program change | Yes, true number 0 to 127 | | Yes, 0 to 127 | Yes, 0 to 127 |
| System exclusive | Yes | "Must be enabled" | Yes, "Must be enabled" | Yes, "Must be enabled" |
| System common | No | | No | No |
| System real time | Clock: yes | "MIDI Clock" | Yes, "MIDI Clock" | No |
| Aux messages | No | | No | No |

For completeness, the 3.4 chart's "Transmitted" column: basic channel 1 to 16; mode 3; note numbers 0 to 127; velocity of note on and of note off, no; after touch, no; pitch bend, yes; control change, yes, "CC1 (Voyager Keyboard only), 5-31 MSB,35, 37-63 LSB; CC 65-127"; program change, yes, 0 to 127; system exclusive, yes; system common, system real time and aux messages, no. synthD transmits nothing, so that column gives rise to no requirement.

The Voyager's MIDI Clock serves its LFO SYNC switch's MIDI position ("When the LFO SYNC switch is set to 'MIDI', a MIDI clock signal retriggers the start of the LFO cycle", Voyager 2.6 manual, printed page 54); synthD has no dedicated low-frequency oscillator to retrigger, and a block carries no system real-time message (MIDI-8), so it is left out (section 12.1). The version 2.5 chart's recognition of velocity and after touch was withdrawn in version 3.4, which is taken; synthD acts on neither in any case (SD-3, SD-7).

### 4.2 Requirements

**SD-1. The messages synthD acts on.** synthD MUST act on exactly these MIDI 1.0 channel messages, and on no other: note off (status `0x8n`); note on (status `0x9n`); control change (status `0xBn`) of the controllers that requirements SD-6 (the registered parameter number controllers 6, 38, 96, 97, 98, 99, 100 and 101), SD-9 to SD-13 and tables A to E of SD-17 name; program change (status `0xCn`); and pitch bend (status `0xEn`). Here `n` is the channel, 0 to 15. Every other channel message (polyphonic key pressure `0xAn`, channel pressure `0xDn`, a control change of any controller not named) and every system exclusive, system common and system real-time message MUST be counted as ignored and MUST change nothing in the instrument. The server MUST refuse a program's message holding one of those others where it would go into a synthD block (MIDI-10), and MUST drop it, with a count in its answer, from a Standard MIDI File (MIDI-118).
- Reason: These are the messages the adopted interface recognises that synthD's panel can act on: the Voyager's controllers for the controls the two panels share, with NeoTeletext's own controllers for the controls only synthD has (section 7), and those of the common layer every synthesizer takes (MIDI-9, MIDI-84 to MIDI-92). The Voyager's controllers for controls synthD lacks are counted as ignored (SD-17, table F).
- Source: Voyager 3.4 manual, printed pages 76 to 78 (the map) and 89 (the chart). Voyager manual, page 46 (section K.5). That note off is recognised is not stated in the 1.0 manual's sentence, which names "Note On messages" only; MIDI 1.0 defines note off (MIDI 1.0 4.2, Table II, PDF 101; printed page 10, PDF 42), and a note could not otherwise end. MIDI-9, MIDI-10.
- Verification: A test sends one message of every status from `0x80` to `0xEF` and every controller 0 to 127, and checks which change the instrument's state and that each of the others adds one to the count of ignored messages and leaves the rendered samples identical to a run without it; a server test checks each of the others is refused, naming the event.

**SD-2. Channels.** synthD MUST act on a channel message alike whatever its channel (0 to 15): the sixteen channels are one keyboard and one panel.
- Reason: A synthD sound holds one monophonic instrument, so there is nothing a second channel could address. The Voyager "only responds to one channel at a time", chosen from 1 to 16 by a setting of its MASTER mode; that setting is a global setting of the hardware, which decision A6 lets be left out, and no message sets it.
- Source: Voyager manual, page 39 ("MIDI IN CHANNEL") and page 51 (basic channel 1 to 16, mode 4); Voyager 3.4 manual, printed page 89 (the same rows). MIDI-67 and MIDI-68 (the channel map of a one-part family). The departure (all channels, where the Voyager takes one) is listed in sections 12.1 and 12.2, as MIDI-68 requires. It is what is built today (`mod.rs`: "The instrument is one part and hears every channel").
- Verification: A test plays the same score sixteen times, each on a different channel, and once with its messages spread over all sixteen, and checks that every run's samples are identical.

**SD-3. Note on.** On a note on whose velocity is 1 to 127, synthD MUST take the key (data byte 1, 0 to 127) as pressed, under the rules of section 5. The velocity MUST NOT change the sound in any way. A note on whose velocity is 0 MUST be taken as a note off of that key, as in every synthesizer (MIDI-88).
- Reason: The adopted interface does not recognise velocity, and the instrument modelled has none. The meaning of velocity 0 is the common rule of MIDI-88, which the Voyager manual does not state.
- Source: Voyager 3.4 manual, printed page 89, and Voyager manual, page 51 (velocity, note on: not recognised; note numbers 0 to 127 recognised; the version 2.5 chart's recognition of velocity, Voyager 2.6 manual, printed page 58, is not taken, section 4.1). Model D manual, page 8, step 13 (the keyboard produces a control signal by "the position of the key struck" and a timing signal, and nothing else). MIDI-88; MIDI 1.0 4.2, printed page 10 (PDF 42) and Table II (PDF 101), for velocity 0.
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

This second paragraph follows the architecture's open question 5 (`midi-architecture.md`, section 20), answered by DEC-6465 answer 5 with its option A. Under that question's option B, synthD would instead keep the one range of 797 cents either way, no message would set it, and controllers 6, 38, 96, 97, 98, 99, 100 and 101 would be counted as ignored.

The Voyager's map gives controllers 6 and 38 to the modulation wheel bus's AMOUNT (Voyager 3.4 manual, printed page 76: "MW AMOUNT … 6 MSB, 38 LSB"), a control synthD lacks (section 10). synthD MUST keep 6 and 38 as the data entry of item 2 and MUST NOT take them as an amount: a Voyager sender selects no parameter number, and with none selected a data entry changes nothing and is counted as ignored (item 3), so a Voyager's MW AMOUNT moves nothing on synthD, as table F of SD-17 lists.
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

**SD-9. The modulation wheel, controllers 1 and 33.** synthD MUST take controller 1 as the coarse part and controller 33 as the fine part of the modulation wheel's 14-bit number, `number = coarse × 128 + fine`, by the rule of MIDI-75 (a coarse value sets the seven high bits and clears the seven low; a fine value sets the seven low bits and leaves the high), and MUST set the wheel to `number ÷ 16,383` of its travel. The wheel is the level control of the modulation mix on its way to the destinations that the OSCILLATOR MODULATION and FILTER MODULATION switches select: at number 0 no modulation passes, and at number 16,383 all of it passes. The share of the modulation that passes MUST be the square of the wheel's travel, `(number × number) ÷ (16,383 × 16,383)`. A sender that sends controller 1 alone reaches at most `16,256 ÷ 16,383` of the travel, as every coarse controller alone does on MIDI's 14-bit scale; the server writes the wheel as controller 1 then controller 33 (MIDI-37).
- Reason: The adopted interface recognises the "MOD WHEEL" as a pair, "1 MSB, 33 LSB", the pairing MIDI 1.0 gives controllers 1 and 33 (MIDI 1.0 4.2, printed page 11, PDF 43; Table III, PDF 102), which MIDI-74 then requires synthD to keep. The wheel does on synthD what it does on the instrument modelled.
- Source: Voyager 3.4 manual, printed page 77 ("MOD WHEEL … Modulation … 1 MSB, 33 LSB") and printed page 89 (controllers 1 to 31 and 33 to 63 received); Voyager 2.6 manual, printed page 53 ("Mod Wheel 1 MSB 33 LSB (receive only)"); Voyager manual, page 35 ("MOD WHEEL"). Model D manual, page 6, step 5 ("The MODULATION wheel is in effect a level control for the Modulation Mix"). MIDI-74, MIDI-75. The curve between the ends is not stated in the source; the square is what is built (`mod.rs`, from the service manual's "50K AUDIO") and is NeoTeletext's own (section 13 item 9).
- Verification: A test sets oscillator 3 to LO as the modulation, turns OSCILLATOR MODULATION on, and measures the depth of the pitch's swing at controller 1 values 0, 32, 64, 96 and 127 sent alone (numbers 0, 4,096, 8,192, 12,288 and 16,256) against 0, 0.0625, 0.2500, 0.5626 and 0.9846 of the full depth, and at controller 1 value 127 followed by controller 33 value 127 against the full depth; and a test sends controller 33 alone after controller 1 and checks the fine part moves the depth and the coarse part is kept.

**SD-10. Volume, controller 7.** On a control change of controller 7, synthD MUST set a gain on its output from the value, 0 (silent) to 127 (full), by the volume law that every NeoTeletext synthesizer shares (MIDI-82 and MIDI-92: `(value × value) ÷ (127 × 127)` of full), and MUST move the gain to its new place by at most `1 ÷ 256` of full a sample, so over at most 256 output samples (5.3 milliseconds). This gain is separate from the panel's VOLUME knob (control 26 of SD-17, carried by controller 108) and multiplies with it. Before any controller 7 arrives the value is 127. Controller 39 MUST be counted as ignored.
- Reason: The adopted interface's map makes controllers 7 and 39 the pair of its MASTER VOLUME knob ("MASTER VOLUME … Adjusts the master volume level … 7 MSB, 39 LSB"), so that on the Voyager controller 7 moves the panel's volume. The architecture requires instead that controller 7 be, in every synthesizer, a gain on the part's output separate from any volume of the patch, by one law of seven bits (MIDI-82, MIDI-92), so that a patch's own volume and a performance's fades do not overwrite one another; where the two documents differ the architecture governs. synthD therefore keeps what is built: controller 7 is the performance volume, the panel's VOLUME knob is a parameter of the patch on a controller of its own (SD-17), and controller 39, which the Voyager pairs with 7 as its fine part, is counted as ignored because the shared law reads seven bits. Both are departures from the Voyager's map, listed in section 12.2.
- Source: Voyager 3.4 manual, printed page 78 (MASTER VOLUME, 7 and 39); Voyager 2.6 manual, printed page 54 ("Master Volume 7 MSB 39 LSB"); Voyager manual, pages 46 and 51 ("Volume Controller (CC7)"). The law and its slew: synthD's source, `analog/volume.rs` (own choices), shared by all the synthesizers; MIDI-82 and MIDI-92 state the law once for every synthesizer, as a gain separate from any volume of the patch. NeoTeletext's own definition, section 13 item 10.
- Verification: A test checks the level of a held note at values 0, 64 and 127 against the shared law, checks that no two successive samples of the gain differ by more than the slew allows, and checks that the product with the panel's VOLUME is what is heard.

**SD-11. All notes off, controller 123.** On a control change of controller 123, whatever its value, synthD MUST release every key that is held, as a note off of each would, and change nothing else, as MIDI-85 requires of every synthesizer. A sustain pedal that is down (SD-13) still holds the note until it goes up, and a note in its release goes on with it.
- Reason: It is the one mode message the adopted interface recognises, and its behaviour is the common one of MIDI-85.
- Source: Voyager manual, page 46 ("All Notes Off") and page 51 (mode messages: "All Notes Off"). MIDI-85. That the pedal still holds is MIDI 1.0's rule ("A Hold or Sustain pedal 'On' message takes priority over Note Off and All Notes Off until it is released", A-5, PDF 95) and what is built.
- Verification: A test holds three keys, sends controller 123, and checks the note is released; and repeats with the pedal down and checks it is held until the pedal lifts.

**SD-12. Program change.** On a program change, synthD MUST take its data byte, 0 to 127, as the number of a patch in the sound's bank and MUST set all 39 panel controls to that patch, as if the control changes of the patch's 60 values had arrived at that instant (SD-22). The modulation wheel, the pitch wheel, the sustain pedal, controller 7's volume and the keys held are left as they are. If the bank holds no patch of that number, synthD MUST set the panel to the default patch (SD-21) and count the program change as ignored. Until a first program change arrives the panel is at patch 0 of the bank, or at the default patch if the bank lacks patch 0 or it was refused (MIDI-61; every sound names at least one bank, MIDI-57).
- Reason: The adopted interface recognises program change with true numbers 0 to 127 and keeps 128 presets, numbered 1 to 128. A program change on the Voyager recalls a preset, which is "all of the settings of the front panel controls except FINE TUNE, plus the parameters in EDIT mode"; synthD's patch is all of its panel (it includes TUNE: section 12.1).
- Source: Voyager 3.4 manual, printed page 89, and Voyager manual, page 51 (program change, 0 to 127); Voyager manual, page 45 ("The 128 presets are numbered 1 to 128. A preset consists of all of the settings of the front panel controls except FINE TUNE, plus the parameters in EDIT mode") and page 46. That program number 0 is preset 1 is not stated in the source; it is MIDI's ordinary numbering (MIDI 1.0 4.2, printed page 14, PDF 46: "As with program numbers, banks begin counting from 1. Thus the actual bank number will be (MIDI value + 1)"). That patch 0 plays before a first program change is what is built, and is MIDI-61's rule; that a missing patch sets the default and is counted is MIDI-59's. synthD has no bank select: controllers 0 and 32 are counted as ignored (MIDI-64), and the mapping of MIDI-59 is bank index 0, program equal to the program number, so a synthD sound names one bank (MIDI-57 allows 1 to 10; only the first is reached).
- Verification: A test builds a bank of 128 different patches, sends program changes 0, 1, 31, 32 and 127, and checks the panel after each equals the patch of that number; sends a program change beyond a bank of 4 patches and checks the default patch and the count; and checks that a held note, the wheels and the pedal are unchanged by a program change.

**SD-13. The messages of NeoTeletext's common layer.** synthD MUST also act on the control changes that the architecture defines for every synthesizer (MIDI-9) and that the adopted interface does not recognise, each with the one behaviour section 11.1 of `midi-architecture.md` sets for every synthesizer:
1. controller 64, the sustain pedal (MIDI-87): down at values 64 to 127, up at 0 to 63; while it is down a released key's note is held as a held key's is, and when it goes up every note so held is released;
2. controller 120, all sound off (MIDI-86): the sound is taken out over at most 256 output samples, within the 1,024 that MIDI-86 allows, by a fade that passes the click measure (MIDI-83), and the voice then emptied; the pedal, every controller and the panel are left where they are;
3. controller 121, reset all controllers (MIDI-84, after DEC-6464 version 2, which is recorded as proposed and awaits the owner's confirmation), on every channel and whatever its value: it sets the modulation wheel, controller 1, to 0, the pitch wheel to its centre (8,192), the sustain pedal, controller 64, up, the GLIDE switch, controller 65, off, and the parameter number selection of SD-6 to none (the null value 127 in each of controllers 98 to 101); it leaves controller 7's volume, the program, the pitch bend range of SD-6 and every other panel control of SD-17 as they are. Held keys are not released by it, except as the pedal's going up releases the notes it held. synthD has no expression, sostenuto or soft pedal, no channel pressure, no key pressure, and no pan, bank select, effect or sound controller, so RP-015's settings of those have nothing to act on (RP-015, page 2); controller 11, which RP-015 sets to 127 as expression, is the Voyager's oscillator 2 WAVE and controller 67, which it sets to 0 as the soft pedal, the Voyager's LFO SYNC, and synthD takes neither (SD-17, table F), so neither is a pedal or an expression on synthD and neither holds state to set (MIDI-84 item 2, DEC-6473 item 3). The modulation wheel's reset to 0 sets both its controllers, 1 and 33, to 0 (SD-9). The GLIDE switch is a panel control of the patch (SD-17), but controller 65 is one of the pedals RP-015 sets to 0 by name ("Set Pedals (#64, #65, #66, #67) to 0", RP-015, page 2), and synthD's GLIDE switch carries that pedal's own meaning, portamento on and off, which MIDI-84 item 2 resets even where a family makes it a parameter of its patch; open question 4 records the change. Every other controller synthD responds to, as MIDI-84 item 4 requires this document to list:

| Controllers | What they move | On controller 121 | Reason |
|---|---|---|---|
| The Voyager's pairs 5 and 37 (the GLIDE knob; MIDI 1.0's portamento time), 10 and 42, 12 and 44, 14 and 46, 15 and 47, 16 and 48, 17 and 49, 18 and 50, 19 and 51, 21 and 53, 23 and 55, 24 and 56, 25 and 57, 27 and 59, 28 and 60, 29 and 61, 30 and 62; the Voyager's single controllers 74, 75, 76, 79, 80, 81, 82, 83, 84, 85 and 88; and NeoTeletext's own 89 and 90 and 102 to 113: every panel controller of SD-17 but the GLIDE switch, controller 65 | Parameters of the patch | Left as they are | A controller that moves a parameter of the patch is the patch, not a performance control (DEC-6464 item 4, MIDI-84 item 4) |
| 6, 38, 96 and 97: data entry, increment and decrement | The value of the registered parameter selected, the pitch bend range | They hold no value of their own; the range they set is left as it is | RP-015: "Do NOT reset registered or non-registered parameters" (page 2) |

Every controller not named in SD-1 is counted as ignored (SD-1) and has no state to reset;
4. controllers 124 (omni off), 125 (omni on), 126 (mono on) and 127 (poly on), the mode messages (MIDI-89): whatever its value, each acts as all notes off (SD-11) and does nothing else; none changes the channels synthD hears (SD-2) or its one-note assignment (SD-14).
- Reason: They are needed by every NeoTeletext sound (a receiver releases every note after a lost block; a sound must be silenced at once), they are standard MIDI 1.0 messages (decision A1), and the owner requires every synthesizer to behave the same way for them (DEC-6464; section 11.1 of the architecture). Controllers 64, 120 and 121 are built today; the mode messages and the parameter number selection are new. Each is listed in section 12.2 as a departure from, or in section 13 as an addition to, the adopted interface.
- Source: MIDI-9, MIDI-83, MIDI-84, MIDI-86, MIDI-87, MIDI-89; DEC-6464 version 2; DEC-6473 items 1 to 3; MIDI 1.0 4.2, Tables III and IV (PDF 102 and 104) and printed pages 12, 20, 24 and 25 (PDF 44, 52, 56 and 57), for the controllers; RP-015, page 2, for the reset; synthD's source, `mod.rs` (`control_change`). The Voyager's 3.4 chart (printed page 89) receives controllers 1 to 31, 33 to 63 and 65 to 88 only, so not 64 or 120 to 127, and its mode messages are "All Notes Off" only.
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

## 6. The Voyager's controller map

From version 2 of its software the Voyager gives every knob and switch of its front panel a controller: "When you adjust any one of the Voyager's front panel controls, MIDI Continuous Controller (CC) messages are transmitted on the MIDI Out jack. … For example, when the FILTER CUTOFF control is rotated, MIDI CC data corresponding to the Filter Cutoff parameter (CC#19 & CC#51) is transmitted" (Voyager 3.4 manual, printed page 76); "All the front panel knobs and switches are assigned a CC number" (Voyager 2.6 manual, printed page 53). The chart says which it receives: "Receive: CC1-31 MSB. 33-63 LSB, 65-88" (Voyager 3.4 manual, printed page 89). The 1.0 manual's MIDI, with controllers 1 and 7 only ("The current (as of 02/05/03) MIDI implementation of Version 1.0 of the software", Voyager manual, page 46), is superseded by it.

### 6.1 The map, every row

Every row of "The Voyager's MIDI CC data assignments" (Voyager 3.4 manual, printed pages 76 to 78), in the manual's order, with its section, control, function, controller and "VALUE/RANGE" as printed; where the Voyager 2.6 manual (printed pages 53 and 54) prints a row differently, the difference; and what synthD does with the row (the control numbers are those of SD-17).

| Section | Control | Function as printed | Controller | Value or range as printed | The 2.6 manual | synthD |
|---|---|---|---|---|---|---|
| Modulation busses | MW SOURCE | Selects the Mod Wheel bus source modulation | 68 | 0-15 Tri; 16-31 Square; 32-47 Osc 3; 48-63 S&H; 64-79 ON/Mod2; 80-127 Noise/PGM | The same | Counted as ignored (table F) |
| Modulation busses | MW DESTINATION | Selects the Mod Wheel bus destination | 69 | 0-15 Pitch; 16-31 Osc 2; 32-47 Osc 3; 48-63 Filt; 64-79 Wave; 80-127 LFO Rate/PGM | The same | Counted as ignored |
| Modulation busses | MW SHAPING | Selects the Mod Wheel bus modulation shaping | 70 | 0-31 Filt; 32-63 Velocity; 64-95 Aftertouch; 96-127 ON/PGM | The same ("Filt. Env.") | Counted as ignored |
| Modulation busses | MW AMOUNT | Adjusts the Mod Wheel bus modulation amount | 6 MSB, 38 LSB | - | The same | Not an amount: 6 and 38 are data entry (SD-6) |
| Modulation busses | PEDAL SOURCE | Selects the Pedal/ON bus source modulation | 71 | As MW SOURCE | The same | Counted as ignored |
| Modulation busses | PEDAL DEST. | Selects the Pedal/ON bus destination | 72 | Printed with the source list: 0-15 Tri; 16-31 Square; 32-47 Osc 3; 48-63 S&H; 64-79 ON/Mod2; 80-127 Noise/PGM | 0-15 Pitch; 16-31 Osc.2; 32-47 Osc. 3; 48-63 Filt; 64-79 Wave; 80-127 LFO Rate/PGM | Counted as ignored; the misprint is read in section 6.2 |
| Modulation busses | PEDAL SHAPING | Selects the Pedal/ON bus modulation shaping | 73 | As MW SHAPING | The same | Counted as ignored |
| Modulation busses | PEDAL AMOUNT | Adjusts the Pedal/ON bus modulation amount | 8 MSB, 40 LSB | - | The same | Counted as ignored |
| Performance controls | MOD WHEEL | Modulation | 1 MSB, 33 LSB | - | "(receive only)" | The modulation wheel (SD-9) |
| Performance controls | GLIDE SWITCH | Turns Glide ON/OFF | 65 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On; "(receive only)" | Control 38, the GLIDE switch |
| Performance controls | RELEASE SWITCH | Turns Release ON/OFF | 88 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On; "(receive only)" | Control 39, the DECAY switch |
| Performance controls | MOD 1 | Mod 1 Input | 2 MSB, 34 LSB | - | "(receive only)" | Counted as ignored |
| Performance controls | MOD 2 | Mod 2 Input | 4 MSB, 36 LSB | - | "(receive only)" | Counted as ignored |
| LFO | LFO RATE | Adjusts the LFO frequency | 3 MSB, 35 LSB | 0 – 127 | The same | Counted as ignored |
| LFO | LFO SYNC | Selects the LFO Sync mode | 67 | 0-31 OFF; 32-63 MIDI; 64-95 KB; 96-127 Env Gate | The same | Counted as ignored |
| Oscillators | OSC 1 OCTAVE | Sets the octave of oscillator 1 | 74 | 0-15 32′; 16-31 16′; 32-47 8′; 48-63 4′; 64-79 2′; 80-127 1′ | The same | Control 4, oscillator 1 RANGE, with controller 103 |
| Oscillators | OSC 1 WAVE | Sets the waveform of oscillator 1 | 9 MSB, 41 LSB | - | The same | Counted as ignored |
| Oscillators | OSC 2 FREQ | Adjusts the frequency of oscillator 2 | 10 MSB, 42 LSB | - | The same | Control 7, oscillator 2 FREQUENCY |
| Oscillators | OSC 2 OCTAVE | Sets the octave of oscillator 2 | 75 | As OSC 1 OCTAVE | The same | Control 6, oscillator 2 RANGE, with controller 105 |
| Oscillators | OSC 2 WAVE | Sets the waveform of oscillator 2 | 11 MSB, 43 LSB | - | The same | Counted as ignored |
| Oscillators | OSC 3 FREQ | Adjusts the frequency of oscillator 3 | Printed "12 MSB, 45 LSB" | - | 12 MSB, 44 LSB | Control 10, oscillator 3 FREQUENCY, on 12 and 44 (section 6.2) |
| Oscillators | OSC 3 OCTAVE | Sets the octave of oscillator 3 | 76 | As OSC 1 OCTAVE | The same | Control 9, oscillator 3 RANGE, with controller 80 |
| Oscillators | OSC 3 WAVE | Sets the waveform of oscillator 3 | 13 MSB, 45 LSB | - | The same | Counted as ignored |
| Oscillators | 1-2 SYNC | Turns oscillator sync ON/OFF | 77 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Counted as ignored |
| Oscillators | 3-1 FM | Turns oscillator frequency modulation ON/OFF | 78 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Counted as ignored |
| Oscillators | 3 KB CONT | Turns keyboard control of oscillator 3 ON/OFF | 79 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Control 28, OSC. 3 CONTROL |
| Oscillators | 3 FREQ | Sets the HI/LO frequency range of oscillator 3 | 80 | 0-63 OFF, 64-127 ON | "3 Frequency Lo/Hi … Value 0-64=LO; 65-127=HI" | Control 9, oscillator 3 RANGE: its LO position (SD-20) |
| Oscillators | GLIDE RATE | Adjusts the rate of glide | 5 MSB, 37 LSB | - | The same | Control 2, the GLIDE knob |
| Mixer | EXTERNAL | Adjusts the level of the external audio signal | 14 MSB, 46 LSB | - | The same | Control 15, EXTERNAL INPUT VOLUME |
| Mixer | EXTERNAL SWITCH | Toggles the external audio ON/OFF | 81 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Control 32 |
| Mixer | OSCILLATOR 1 | Adjusts the level of oscillator 1 | 15 MSB, 47 LSB | - | The same | Control 12 |
| Mixer | OSCILLATOR 1 SW | Toggles oscillator 1 ON/OFF | 82 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Control 29 |
| Mixer | OSCILLATOR 2 | Adjusts the level of oscillator 2 | 16 MSB, 48 LSB | - | The same | Control 13 |
| Mixer | OSCILLATOR 2 SW | Toggles oscillator 2 ON/OFF | 83 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Control 30 |
| Mixer | OSCILLATOR 3 | Adjusts the level of oscillator 3 | 17 MSB, 49 LSB | - | The same | Control 14 |
| Mixer | OSCILLATOR 3 SW | Toggles oscillator 3 ON/OFF | 84 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Control 31 |
| Mixer | NOISE | Adjusts the level of noise | 18 MSB, 50 LSB | - | The same | Control 16, NOISE VOLUME |
| Mixer | NOISE SWITCH | Toggles noise ON/OFF | 85 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Control 33 |
| Filter | CUTOFF | Adjusts the filter cutoff frequency | 19 MSB, 51 LSB | - | The same | Control 17, CUTOFF FREQUENCY |
| Filter | SPACING | Adjusts the filter spacing parameter | 20 MSB, 52 LSB | - | The same | Counted as ignored |
| Filter | RESONANCE | Adjusts the filter resonance parameter | 21 MSB, 53 LSB | - | The same | Control 18, EMPHASIS |
| Filter | KB AMOUNT | Adjusts the amount of pitch CV affecting the cutoff | 22 MSB, 54 LSB | - | The same ("Filter KB Control Amount") | Counted as ignored (SD-17, rule c) |
| Filter | MODE | Toggles the filter mode between LP/LP and HP/LP | 86 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Counted as ignored |
| Envelope generator | FILTER ENV ATTACK | Adjusts the filter envelope attack time | 23 MSB, 55 LSB | - | The same | Control 20 |
| Envelope generator | FILTER ENV DECAY | Adjusts the filter envelope decay time | 24 MSB, 56 LSB | - | The same | Control 21 |
| Envelope generator | FILTER ENV SUSTAIN | Sets the filter envelope sustain level | 25 MSB, 57 LSB | - | The same | Control 22 |
| Envelope generator | FILTER ENV RELEASE | Adjusts the filter envelope release time | 26 MSB, 58 LSB | - | The same | Counted as ignored |
| Envelope generator | AMOUNT TO FILTER | Adjusts the amount of filter envelope affecting the cutoff | 27 MSB, 59 LSB | - | The same | Control 19, AMOUNT OF CONTOUR, its positive half (SD-18 item 2) |
| Envelope generator | VOLUME ENV ATTACK | Adjusts the volume envelope attack time | 28 MSB, 60 LSB | - | The same | Control 23 |
| Envelope generator | VOLUME ENV DECAY | Adjusts the volume envelope decay time | 29 MSB, 61 LSB | - | The same | Control 24 |
| Envelope generator | VOL ENV SUSTAIN | Sets the volume envelope sustain level | 30 MSB, 62 LSB | - | The same | Control 25 |
| Envelope generator | VOL ENV RELEASE | Adjusts the volume envelope release time | 31 MSB, 63 LSB | - | The same | Counted as ignored |
| Envelope generator | ENV GATE SWITCH | Toggles the envelope gate between Keyboard and ON/EXT | 87 | 0-63 OFF, 64-127 ON | 0-64 Off; 65-127 On | Counted as ignored |
| Vol | MASTER VOLUME | Adjusts the master volume level | 7 MSB, 39 LSB | - | The same | Controller 7 is the common layer's volume gain (SD-10); 39 is counted as ignored |

Beneath the table the 3.4 manual adds: "When the EXTERNAL SWITCH is set to OFF, the EXTERNAL control does not transmit MIDI CC's" (printed page 78). It concerns what the Voyager transmits, not what it receives, and gives synthD no requirement.

### 6.2 What the map does not state, and the readings taken

1. **The scale of every pair.** The "VALUE/RANGE" column is "-" for every pair but LFO RATE, "0 – 127". The map does not state what a pair's number means in the control's own units (hertz, seconds, octaves), whether its scale is linear, or whether a receiver takes a fine controller alone. synthD's scaling (SD-18) is NeoTeletext's own: linear in synthD's own units, exact both ways, with MIDI-75's rule that a coarse value clears the fine.
2. **The switch bands differ between editions.** Version 3.4 prints every switch as "0-63 OFF, 64-127 ON"; version 2.6 prints "0-64=Off; 65-127=On" (and "0-64=LO; 65-127=HI" for the 3 FREQ switch). They differ only at value 64. synthD takes the later edition, 3.4, which is also MIDI 1.0's rule for a switch controller ("0-63 (00H-3FH) as 'OFF' and 64-127 (40H-7FH) as 'ON'", MIDI 1.0 4.2, printed page 12, PDF 44) and what every NeoTeletext synthesizer's sustain pedal follows (MIDI-87): value 64 is on. A sender writes 0 and 127 (SD-20), which both editions read alike.
3. **The selector bands are taken as printed**: LFO SYNC four bands of 32 values; the six octave bands of 16 values with the last, 1′, from 80 to 127; the bus sources and destinations six bands, the last from 80 to 127; the shapings four bands of 32. The two editions print them alike.
4. **The pedal destination, controller 72, is misprinted in version 3.4** with the list of the pedal source (Tri, Square, Osc 3, S&H, ON/Mod2, Noise/PGM). The reading taken is version 2.6's list, "0-15=Pitch; 16-31= Osc.2; 32-47= Osc. 3; 48-63=Filt; 64-79 = Wave; 80-127=LFO Rate/PGM", which is the list the 3.4 manual itself gives the modulation wheel's destination (controller 69) and the only one that names destinations. synthD lacks the busses and counts controller 72 as ignored under either reading.
5. **Oscillator 3's FREQ pair is misprinted in version 3.4** as "12 MSB, 45 LSB", while OSC 3 WAVE is printed "13 MSB, 45 LSB": one controller, 45, cannot be the fine part of both. The reading taken is 12 and 44, as version 2.6 prints it ("Osc. 3 Frequency 12 MSB 44 LSB"), as the pairing of every other row of the map gives (each fine controller is its coarse controller plus 32, MIDI 1.0 4.2, printed page 11, PDF 43; Table III, PDF 102), and as the chart's "33-63 LSB" admits. Controller 45 is the fine part of OSC 3 WAVE, which synthD counts as ignored.
6. **Which end of the 3 FREQ switch is LO.** Version 3.4 prints only "0-63 OFF, 64-127 ON" against "Sets the HI/LO frequency range of oscillator 3"; version 2.6 says "Value 0-64=LO; 65-127=HI". The reading taken is the 3.4 bands with version 2.6's names: 0 to 63 LO, 64 to 127 HI.
7. **Which end of the RELEASE switch releases.** The map says "Turns Release ON/OFF"; the 1.0 manual says the switch "is used to shorten the Release time of both the filter and Volume envelopes" (Voyager manual, page 35). The reading taken is that ON is the release at the envelopes' own release times and OFF the shortened release, which is the sense of "Turns Release ON/OFF" and of synthD's DECAY switch (SD-17, control 39).
8. **Controllers 6 and 38, and 8 and 40.** The map gives 6 and 38 to MW AMOUNT and 8 and 40 to PEDAL AMOUNT, where MIDI 1.0 gives 6 and 38 to data entry and 8 to balance (MIDI 1.0 4.2, Table III, PDF 102). synthD lacks both amounts; 6 and 38 stay data entry (SD-6), and 8 and 40 are counted as ignored.

## 7. The panel control map

**SD-17. The 39 panel controls and their controllers.** synthD MUST have exactly the 39 panel controls of tables A to E below, each moved by the control change of the controller, pair of controllers or two controllers that the tables give, and by no other message than those and a program change (SD-12). For a shared control the controller is the Voyager's, as the Voyager 3.4 manual prints it with the readings of section 6.2; for a synthD-only control it is NeoTeletext's own, marked in bold, by the rules below. Every controller of table F, the Voyager's controllers for controls synthD lacks, MUST be counted as ignored and MUST change nothing. The "Model D" column gives the number or letter the Model D manual's figures give the control; the "Voyager control" column the row of the Voyager's map (section 6.1) that the control follows.

*Table A. Knobs carried as a coarse and fine pair, scaled by SD-18:*

| No. | Control | Model D | Voyager control | Coarse | Fine | Field and its unit | Range of the field |
|---|---|---|---|---|---|---|---|
| 1 | TUNE | 1 | None: the Voyager's FINE TUNE has no controller | **89** | **90** | The pitch of all three oscillators, in cents | −242 to +242 |
| 2 | GLIDE | 2 | GLIDE RATE | 5 | 37 | The dial's 0 to 10, in tenths of a division | 0 to 100 |
| 7 | Oscillator 2 FREQUENCY | 7 | OSC 2 FREQ | 10 | 42 | Oscillator 2's pitch against oscillator 1, in cents | −700 to +700 |
| 10 | Oscillator 3 FREQUENCY | 10 | OSC 3 FREQ | 12 | 44 | Oscillator 3's pitch, in cents; with OSC. 3 CONTROL off the same travel is 2.75 octaves either way | −700 to +700 |
| 12 | Mixer VOLUME of oscillator 1 | 12 | OSCILLATOR 1 | 15 | 47 | Tenths of a division | 0 to 100 |
| 13 | Mixer VOLUME of oscillator 2 | 13 | OSCILLATOR 2 | 16 | 48 | Tenths of a division | 0 to 100 |
| 14 | Mixer VOLUME of oscillator 3 | 14 | OSCILLATOR 3 | 17 | 49 | Tenths of a division | 0 to 100 |
| 15 | EXTERNAL INPUT VOLUME | 15 | EXTERNAL | 14 | 46 | Tenths of a division: how much of the instrument's own output returns to the mixer | 0 to 100 |
| 16 | NOISE VOLUME | 16 | NOISE | 18 | 50 | Tenths of a division | 0 to 100 |
| 17 | CUTOFF FREQUENCY | 17 | CUTOFF | 19 | 51 | The dial's −5 to +5, in hundredths of a division; a division is an octave | −500 to +500 |
| 18 | EMPHASIS | 18 | RESONANCE | 21 | 53 | Tenths of a division | 0 to 100 |
| 19 | AMOUNT OF CONTOUR | 19 | AMOUNT TO FILTER | 27 | 59 | Tenths of a division, from the pair's middle up (SD-18 item 2) | 0 to 100 |
| 20 | Filter contour ATTACK TIME | 20 | FILTER ENV ATTACK | 23 | 55 | Milliseconds | 0 to 10,000 |
| 21 | Filter contour DECAY TIME | 21 | FILTER ENV DECAY | 24 | 56 | Milliseconds | 0 to 10,000 |
| 22 | Filter contour SUSTAIN LEVEL | 22 | FILTER ENV SUSTAIN | 25 | 57 | Tenths of a division | 0 to 100 |
| 23 | Loudness contour ATTACK TIME | 23 | VOLUME ENV ATTACK | 28 | 60 | Milliseconds | 0 to 10,000 |
| 24 | Loudness contour DECAY TIME | 24 | VOLUME ENV DECAY | 29 | 61 | Milliseconds | 0 to 10,000 |
| 25 | Loudness contour SUSTAIN LEVEL | 25 | VOL ENV SUSTAIN | 30 | 62 | Tenths of a division | 0 to 100 |

*Table B. Knobs carried in one controller, scaled by SD-19:*

| No. | Control | Model D | Voyager control | Controller | Field and its unit | Range of the field |
|---|---|---|---|---|---|---|
| 3 | MODULATION MIX | 3 | None: the Voyager chooses one source with a selector (MW SOURCE) | **102** | Tenths of a division: 0 is all oscillator 3, 100 is all noise | 0 to 100 |
| 26 | Main output VOLUME | 26 | MASTER VOLUME, whose controller 7 is the common layer's gain (SD-10) | **108** | Tenths of a division | 0 to 100 |

*Table C. The RANGE selectors, each carried by two controllers, by the bands of SD-20 items 1 to 3:*

| No. | Control | Model D | Octave controller (the Voyager's) | LO/HI controller | Positions |
|---|---|---|---|---|---|
| 4 | Oscillator 1 RANGE | 4 | 74, OSC 1 OCTAVE | **103** (none on the Voyager) | LO, 32′, 16′, 8′, 4′, 2′ |
| 6 | Oscillator 2 RANGE | 6 | 75, OSC 2 OCTAVE | **105** (none on the Voyager) | LO, 32′, 16′, 8′, 4′, 2′ |
| 9 | Oscillator 3 RANGE | 9 | 76, OSC 3 OCTAVE | 80, the Voyager's 3 FREQ | LO, 32′, 16′, 8′, 4′, 2′ |

*Table D. Waveform selectors of six positions, carried in one controller, by the bands of SD-20 item 5:*

| No. | Control | Model D | Voyager control | Controller | Positions, 0 to 5 |
|---|---|---|---|---|---|
| 5 | Oscillator 1 WAVEFORM | 5 | None of the same bands: OSC 1 WAVE is a pair without bands | **104** | Triangular, sawtooth-triangular, sawtooth, square, wide rectangular, narrow rectangular |
| 8 | Oscillator 2 WAVEFORM | 8 | As above (OSC 2 WAVE) | **106** | As oscillator 1's |
| 11 | Oscillator 3 WAVEFORM | 11 | As above (OSC 3 WAVE) | **107** | Triangular, reverse sawtooth, sawtooth, square, wide rectangular, narrow rectangular |

*Table E. On-off switches, carried in one controller: off at values 0 to 63, on at values 64 to 127 (SD-20 item 4):*

| No. | Control | Model D | Voyager control | Controller | Off | On |
|---|---|---|---|---|---|---|
| 27 | OSCILLATOR MODULATION | A | None: the Voyager chooses one destination with a selector (MW DESTINATION) | **109** | The modulation does not reach the oscillators | It moves the oscillators' pitch |
| 28 | OSC. 3 CONTROL | B | 3 KB CONT | 79 | Oscillator 3 does not follow the keyboard | It follows the keyboard |
| 29 | Mixer switch of oscillator 1 | C | OSCILLATOR 1 SW | 82 | Out of the mixer | In the mixer |
| 30 | Mixer switch of oscillator 2 | E | OSCILLATOR 2 SW | 83 | Out of the mixer | In the mixer |
| 31 | Mixer switch of oscillator 3 | G | OSCILLATOR 3 SW | 84 | Out of the mixer (it still modulates) | In the mixer |
| 32 | Mixer switch of the external input | D | EXTERNAL SWITCH | 81 | Out of the mixer | In the mixer |
| 33 | Mixer switch of the noise | F | NOISE SWITCH | 85 | Out of the mixer (it still modulates) | In the mixer |
| 34 | Noise WHITE / PINK | H | None: the Voyager's noise is one "white/pink hybrid" | **110** | White | Pink |
| 35 | FILTER MODULATION | J | None, as control 27 | **111** | The modulation does not reach the filter | It moves the cutoff |
| 36 | KEYBOARD CONTROL 1 | K | None of the same bands: KB AMOUNT is a pair without bands | **112** | No share | A third of the keyboard's voltage moves the cutoff |
| 37 | KEYBOARD CONTROL 2 | L | As control 36 | **113** | No share | Two thirds of the keyboard's voltage moves the cutoff |
| 38 | GLIDE | R | GLIDE SWITCH | 65 | No glide | Glide at the GLIDE knob's rate (SD-16) |
| 39 | DECAY | S | RELEASE SWITCH | 88 | A released note is cut in a few milliseconds | A released note falls at each contour's DECAY TIME |

Controls 36 and 37 both on give all of the keyboard's voltage. The numbers 1 to 39 in the first column are this document's, in the order of today's patch.

*Table F. The Voyager's controllers for controls synthD lacks, each counted as ignored:*

| Controller | The Voyager's control (section 6.1) |
|---|---|
| 2 and 34 | MOD 1, an input of the modulation busses |
| 3 and 35 | LFO RATE |
| 4 and 36 | MOD 2, an input of the modulation busses |
| 8 and 40 | PEDAL AMOUNT |
| 9 and 41 | OSC 1 WAVE |
| 11 and 43 | OSC 2 WAVE |
| 13 and 45 | OSC 3 WAVE |
| 20 and 52 | Filter SPACING |
| 22 and 54 | Filter KB AMOUNT |
| 26 and 58 | FILTER ENV RELEASE |
| 31 and 63 | VOL ENV RELEASE |
| 39 | The fine part of MASTER VOLUME (SD-10) |
| 67 | LFO SYNC |
| 68, 69 and 70 | MW SOURCE, MW DESTINATION and MW SHAPING |
| 71, 72 and 73 | PEDAL SOURCE, PEDAL DEST. and PEDAL SHAPING |
| 77 | 1-2 SYNC |
| 78 | 3-1 FM |
| 86 | Filter MODE |
| 87 | ENV GATE SWITCH |

The Voyager's MW AMOUNT, controllers 6 and 38, is not counted here: those controllers are data entry on synthD (SD-6), which with no parameter selected changes nothing and is counted as ignored.

- Reason: The panel is the instrument modelled's; the fields and units are those built and are the units its dials and sound charts are written in. DEC-6453 requires synthD to be programmed as its adopted interface does it, and DEC-6465 answers 23 and 24 direct that the Voyager's map be followed for every control the two panels share, with NeoTeletext's own controllers for the controls only synthD has. The controllers were chosen by these rules, in order:
  - (a) A shared control takes the Voyager's controller or pair, as the Voyager 3.4 manual prints it, read as section 6.2 says. A control is shared where the Voyager's control has the same purpose; where the two differ in positions or range, SD-18 to SD-20 state how the Voyager's values fall onto synthD's, which DEC-6465 answer 24 allows only where the purpose and the bands are the same. This gives the seventeen pairs of table A from GLIDE to the loudness SUSTAIN LEVEL; the octave controllers 74, 75 and 76 and the 3 FREQ switch 80 of table C; and the switches 79, 81 to 85, 65 and 88 of table E. The DECAY switch (39) folds onto the RELEASE SWITCH (88): both turn the release on and off with the same two bands, synthD's release taking the DECAY TIME because the instrument modelled has no release knob (section 6.2 item 7).
  - (b) A synthD control whose Voyager counterpart has a purpose of its own (the bus's source and destination selectors against MODULATION MIX and the two modulation switches), or has no counterpart (TUNE, whose Voyager FINE TUNE has no controller and is left out of the Voyager's presets; WHITE / PINK; the LO position of oscillators 1 and 2), or whose counterpart has no value bands to fold onto (the three WAVE pairs against the six-position WAVEFORM switches; KB AMOUNT against the two KEYBOARD CONTROL switches), is synthD-only and takes a controller of NeoTeletext's own. The main output VOLUME is also given one of NeoTeletext's own, because the Voyager's MASTER VOLUME controller, 7, is the common layer's gain in every synthesizer (SD-10, MIDI-82).
  - (c) NeoTeletext's own controllers are taken from the numbers that MIDI 1.0 4.2's Table III leaves undefined (3, 9, 14, 15, 20 to 31, 85 to 90 and 102 to 119) less those the Voyager's map uses (3, 9, 14, 15, 20 to 31 and 85 to 88): that is, from 89, 90 and 102 to 119, in that order. The synthD-only controls take them in the order of today's patch (the numbers 1 to 39), each the lowest still free. A control of more than 128 values takes two consecutive numbers, the lower its coarse part and the higher its fine part, which this document pairs as MIDI-74 lets a family document pair the controllers of a map NeoTeletext defines; MIDI-78 rule 5's coarse controller among 0 to 31 cannot be had, because the Voyager's map uses every controller from 1 to 31. So TUNE takes 89 and 90; MODULATION MIX 102; oscillator 1's LO/HI 103; oscillator 1 WAVEFORM 104; oscillator 2's LO/HI 105; oscillator 2 WAVEFORM 106; oscillator 3 WAVEFORM 107; the main output VOLUME 108; OSCILLATOR MODULATION 109; WHITE / PINK 110; FILTER MODULATION 111; KEYBOARD CONTROL 1 112 and KEYBOARD CONTROL 2 113. Controllers 114 to 119 stay free.
  - (d) The common layer's controllers keep their meanings: 1 and 33 the modulation wheel, 7 the volume gain, 64, 120, 121 and 123 to 127 (SD-9 to SD-13), and 6, 38 and 96 to 101 registered parameter number 0 (SD-6). None of NeoTeletext's own numbers is one that MIDI 1.0 gives another meaning (MIDI-78 rule 6).
- Source: The controls: Model D manual, pages 3 to 14 and its figures 2 to 6 (each control's number or letter), and synthD's source, `patch.rs` (each field, unit and range, with its own sources). The Voyager's controllers and bands: Voyager 3.4 manual, printed pages 76 to 78, with the Voyager 2.6 manual, printed pages 53 and 54, for the readings of section 6.2; the chart's received controllers, Voyager 3.4 manual, printed page 89. NeoTeletext's own controllers and their rule: section 13 item 1. The undefined controllers: MIDI 1.0 4.2, Table III (PDF 102), against which 89, 90 and 102 to 113 were checked on 18 November 2026 as undefined. DEC-6453; DEC-6465 answers 23 and 24; MIDI-74, MIDI-78.
- Verification: A test sends, for each of the 39 controls, a control change of each of its controllers and checks that exactly that field changes and no other; a test sends each controller of table F, each of 0, 64 and 127, and checks it is counted as ignored and the samples are identical to a run without it; a test sends every controller from 0 to 127 that tables A to F and SD-6 and SD-9 to SD-13 do not name and checks each is counted as ignored. An assertion in the code checks that no controller number appears twice among tables A to E and the common layer's, and that every number of rule (c) is one Table III leaves undefined and the Voyager's map does not use.

**SD-18. Scaling of a coarse and fine pair.** For each control of table A, synthD MUST keep a 14-bit number, `number = coarse × 128 + fine`. A control change of the coarse controller MUST set the coarse seven bits to its value and the fine seven bits to 0; a control change of the fine controller MUST set the fine seven bits and leave the coarse. The field is set anew after either. All arithmetic is in integers.
1. For every control of table A but AMOUNT OF CONTOUR, synthD MUST set the field to `field = lowest + floor((number × span + 8,191) ÷ 16,383)`, where `lowest` is the lowest value of the field's range and `span` is the highest less the lowest: 484 for TUNE; 1,400 for a FREQUENCY; 1,000 for CUTOFF FREQUENCY; 10,000 for an ATTACK or DECAY TIME; 100 for GLIDE, the five mixer volumes, EMPHASIS and the two SUSTAIN LEVELs. The canonical number for a field's value, which a sender writes, is `number = floor(((field − lowest) × 16,383 + floor(span ÷ 2)) ÷ span)`, and the receiver's formula returns exactly that field for it. Number 0 is the lowest value and number 16,383 the highest; for TUNE, the FREQUENCY knobs and CUTOFF FREQUENCY number 8,192 (coarse 64, fine 0) is the middle, 0.
2. For AMOUNT OF CONTOUR (controllers 27 and 59), synthD MUST set the field to 0 for a number below 8,192, and to `floor(((number − 8,192) × 100 + 4,095) ÷ 8,191)` for a number from 8,192: number 8,192 (coarse 64, fine 0) is 0 and number 16,383 is 100. The canonical number is `8,192 + floor((field × 8,191 + 50) ÷ 100)`, which the formula returns exactly.
- Reason: The scale is linear in the panel's own units, so that a value reads as the dial reads, and it is exact both ways: every value of every field (each has fewer than 16,384) has a number, and the number gives that value back, so that a patch written in cents, milliseconds and tenths is carried without change. A coarse controller alone gives 128 steps over the whole travel, and its value 64 is the middle of a knob that has one; alone it reaches `16,256 ÷ 16,383` of the travel, which is MIDI's 14-bit scale (a knob of 0 to 100 then reads 99, AMOUNT OF CONTOUR 98), and the fine controller reaches the top. That a coarse controller clears the fine part is MIDI 1.0's rule for such pairs ("When an MSB is received, the receiver should set its concept of the LSB to zero", MIDI 1.0 4.2, printed page 12, PDF 44), as MIDI-75 states for every family. The Voyager's AMOUNT TO FILTER runs from −5 to +5, its middle no amount (Voyager manual, page 27); synthD's AMOUNT OF CONTOUR, like the instrument modelled's, only adds (0 to 10), so the Voyager's positive half carries synthD's whole range, with the Voyager's zero at synthD's zero, and the negative half, which synthD cannot make, is no amount.
- Source: The pairs: Voyager 3.4 manual, printed pages 76 to 78. Their scale: not stated in the source (section 6.2 item 1); NeoTeletext's own (section 13 item 2). The fields' ranges: SD-17, table A. MIDI-75; MIDI 1.0 4.2, printed pages 11 and 12 (PDF 43 and 44), for the pairing and the clearing of the fine part. AMOUNT TO FILTER's range: Voyager manual, page 27.
- Verification: A test checks, for each of the eighteen controls of table A and every value of its field, that the canonical number sent as coarse then fine gives that value; that numbers 0, 8,192 and 16,383 give the lowest, middle and highest (for AMOUNT OF CONTOUR, 0, 0 and 100, and number 8,191 gives 0); that the field never decreases as the number rises through all 16,384; and that a coarse controller alone sets the fine part to 0.

**SD-19. Scaling of a knob in one controller.** For each knob of table B (controllers 102 and 108), synthD MUST set the field to `floor((value × 100 + 63) ÷ 127)`: value 0 is 0, value 64 is 50 and value 127 is 100. The canonical value for a field is `floor((field × 127 + 50) ÷ 100)`, and the receiver's formula returns exactly that field for it. Neither controller has a fine part.
- Reason: These fields are tenths of a dial's division, 101 values, which one controller's 128 values carry exactly; they are NeoTeletext's own controllers, outside MIDI's paired range, and a fine controller would add nothing the instrument holds. The scale is linear in the dial's divisions.
- Source: Not stated in the Voyager's map (it has no such control): NeoTeletext's own (section 13 item 2). The fields: `patch.rs` and `law.rs` (`KNOB_MAX`).
- Verification: A test checks, for both knobs, all 128 values against the formula, all 101 canonical values for an exact return, and that the field never decreases as the value rises.

**SD-20. Value bands of the selectors and switches.**
1. **The octave controllers 74, 75 and 76** MUST be read by the Voyager's bands: values 0 to 15 32′; 16 to 31 16′; 32 to 47 8′; 48 to 63 4′; 64 to 79 2′; 80 to 127 1′. synthD has no 1′: values 80 to 127 MUST select 2′, the shortest footage synthD has. The canonical values are 0 (32′), 16 (16′), 32 (8′), 48 (4′) and 64 (2′).
2. **The LO/HI controllers** 103 (oscillator 1), 105 (oscillator 2) and 80 (oscillator 3, the Voyager's 3 FREQ) MUST be read as LO at values 0 to 63 and HI at values 64 to 127. The canonical values are 0 (LO) and 127 (HI).
3. **The RANGE field** of each oscillator is LO while its LO/HI controller is LO, whatever its octave controller holds; while it is HI, it is the footage its octave controller selects. synthD MUST keep the value of both controllers, so that a change to HI restores the footage last set. The canonical values for a RANGE of LO are LO/HI 0 with the octave controller at 32 (8′); for a footage, LO/HI 127 with the octave controller at that footage's canonical value.
4. **The on-off switches** of table E (controllers 65, 79, 81 to 85, 88 and 109 to 113) MUST be read as off at values 0 to 63 and on at values 64 to 127. The canonical values are 0 and 127.
5. **The waveform selectors** 104, 106 and 107 MUST be read as position `floor(value × 6 ÷ 128)`, which gives these bands: values 0 to 21 position 0; 22 to 42 position 1; 43 to 63 position 2; 64 to 85 position 3; 86 to 106 position 4; 107 to 127 position 5. The canonical value of a position is the lowest of its band: 0, 22, 43, 64, 86, 107.
- Reason: Every value from 0 to 127 then selects a position, so that no value is an error. Items 1 and 4 are the Voyager's own bands for the controllers it has, as version 3.4 prints them (section 6.2 items 2 and 3); the 1′ band falls on 2′ because synthD's RANGE switches, as the instrument modelled's, end at 2′, the nearest footage. Items 2 and 3 follow the Voyager's way of making a LO range, a separate switch beside the octave (its 3 FREQ, controller 80, for oscillator 3 only); synthD's RANGE switch has LO as one of its positions on all three oscillators, so oscillators 1 and 2 take LO/HI controllers of NeoTeletext's own in the same form as the Voyager's 80, and the six positions of synthD's switch are carried by the two controllers without loss. Item 5 is NeoTeletext's own, the six bands as nearly equal as six positions in 128 values allow, because the Voyager's WAVE controls are continuous and its map gives them no bands. The canonical octave for a RANGE of LO is 8′, the footage of the default patch's other oscillators, so that a change of that oscillator to HI lands on the middle of the panel.
- Source: Items 1, 2 (for controller 80) and 4: Voyager 3.4 manual, printed page 77 and 78; Voyager 2.6 manual, printed pages 53 and 54; the readings of section 6.2 items 2, 3 and 6; MIDI 1.0 4.2, printed page 12 (PDF 44), for the on-off rule. The fold of 1′ onto 2′, items 2 and 3 for controllers 103 and 105, and item 5: NeoTeletext's own (section 13 item 3). synthD's positions: `patch.rs` (RANGE 0 to 5, LO first).
- Verification: A test checks all 128 values of each of the three octave controllers, the three LO/HI controllers, the three waveform selectors and the thirteen switches against the bands, and each band's two edges by name; a test sets oscillator 1 to 4′, sends controller 103 at 0 and checks LO, then at 127 and checks 4′; and a test sends controller 74 at 100 and checks 2′.

**SD-21. The default patch.** An instrument that has been given no patch, and an instrument whose patch is missing or refused, MUST stand at this patch: TUNE 0; GLIDE 0; MODULATION MIX 0; oscillator 1 RANGE 8′, WAVEFORM sawtooth, mixer VOLUME 100, mixer switch on; oscillator 2 RANGE 8′, FREQUENCY 0, WAVEFORM sawtooth, VOLUME 100, switch off; oscillator 3 RANGE LO, FREQUENCY 0, WAVEFORM triangular, VOLUME 100, switch off; EXTERNAL INPUT VOLUME 0, switch off; NOISE VOLUME 0, switch off, white; CUTOFF FREQUENCY +500; EMPHASIS 0; AMOUNT OF CONTOUR 0; both contours ATTACK TIME 0, DECAY TIME 0, SUSTAIN LEVEL 100; main output VOLUME 100; OSCILLATOR MODULATION off; OSC. 3 CONTROL on; FILTER MODULATION off; KEYBOARD CONTROL 1 and 2 off; GLIDE off; DECAY off. Its 60 values are in the last column of the table of SD-22.
- Reason: An instrument must sound something definite before a patch arrives. This is the default built today: one sawtooth at 8′ through the open filter, shaped as an organ's note.
- Source: synthD's source, `patch.rs`, `Patch::DEFAULT` (own choice). The Voyager has a "Default Init. Parameters" sound of its own, given only as a drawing of its panel (Voyager manual, page 44), which is of a different panel and is not used.
- Verification: A test checks that a new instrument's panel equals the 60 values of SD-22's last column, decoded, field by field.

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

**SD-22. The patch: 60 values in a fixed order.** A synthD patch MUST be exactly 60 bytes, each a control change's value from 0 to 127, in the order of the table below: first the values of the Voyager's controllers that synthD takes (tables A, C and E of SD-17), in ascending order of controller number, each fine controller immediately after its coarse controller; then the values of NeoTeletext's own controllers, in ascending order of controller number. The patch carries no status byte, no controller number, no name and no length: byte k is always the value of the controller the table gives for byte k. A sender MUST write the canonical value of each field (SD-18, SD-19, SD-20). A receiver MUST accept every patch whose 60 bytes are each 0 to 127, whatever their values, and MUST set the panel from it exactly as the control changes of its 60 values would, all at one instant; a patch with a byte above 127, or of another length, is not a patch, and the instrument then stands at the default patch (SD-21) and the fault is counted in the counter of refused patches (MIDI-63). The server MUST encode a patch given as named fields into these 60 bytes, writing the canonical values, and MUST accept a patch given as the 60 values (MIDI-14); it MUST check every patch with the receiver's own check and refuse one of another length or with a byte above 127, naming the bank, the program, the byte and the rule (MIDI-21, MIDI-63).

| Byte | Control (number in SD-17) | Controller | Origin | Value in the default patch |
|---|---|---|---|---|
| 0 | GLIDE (2), coarse | 5 | The Voyager's | 0 |
| 1 | GLIDE (2), fine | 37 | The Voyager's | 0 |
| 2 | Oscillator 2 FREQUENCY (7), coarse | 10 | The Voyager's | 64 |
| 3 | Oscillator 2 FREQUENCY (7), fine | 42 | The Voyager's | 0 |
| 4 | Oscillator 3 FREQUENCY (10), coarse | 12 | The Voyager's | 64 |
| 5 | Oscillator 3 FREQUENCY (10), fine | 44 | The Voyager's | 0 |
| 6 | EXTERNAL INPUT VOLUME (15), coarse | 14 | The Voyager's | 0 |
| 7 | EXTERNAL INPUT VOLUME (15), fine | 46 | The Voyager's | 0 |
| 8 | Mixer VOLUME of oscillator 1 (12), coarse | 15 | The Voyager's | 127 |
| 9 | Mixer VOLUME of oscillator 1 (12), fine | 47 | The Voyager's | 127 |
| 10 | Mixer VOLUME of oscillator 2 (13), coarse | 16 | The Voyager's | 127 |
| 11 | Mixer VOLUME of oscillator 2 (13), fine | 48 | The Voyager's | 127 |
| 12 | Mixer VOLUME of oscillator 3 (14), coarse | 17 | The Voyager's | 127 |
| 13 | Mixer VOLUME of oscillator 3 (14), fine | 49 | The Voyager's | 127 |
| 14 | NOISE VOLUME (16), coarse | 18 | The Voyager's | 0 |
| 15 | NOISE VOLUME (16), fine | 50 | The Voyager's | 0 |
| 16 | CUTOFF FREQUENCY (17), coarse | 19 | The Voyager's | 127 |
| 17 | CUTOFF FREQUENCY (17), fine | 51 | The Voyager's | 127 |
| 18 | EMPHASIS (18), coarse | 21 | The Voyager's | 0 |
| 19 | EMPHASIS (18), fine | 53 | The Voyager's | 0 |
| 20 | Filter ATTACK TIME (20), coarse | 23 | The Voyager's | 0 |
| 21 | Filter ATTACK TIME (20), fine | 55 | The Voyager's | 0 |
| 22 | Filter DECAY TIME (21), coarse | 24 | The Voyager's | 0 |
| 23 | Filter DECAY TIME (21), fine | 56 | The Voyager's | 0 |
| 24 | Filter SUSTAIN LEVEL (22), coarse | 25 | The Voyager's | 127 |
| 25 | Filter SUSTAIN LEVEL (22), fine | 57 | The Voyager's | 127 |
| 26 | AMOUNT OF CONTOUR (19), coarse | 27 | The Voyager's | 64 |
| 27 | AMOUNT OF CONTOUR (19), fine | 59 | The Voyager's | 0 |
| 28 | Loudness ATTACK TIME (23), coarse | 28 | The Voyager's | 0 |
| 29 | Loudness ATTACK TIME (23), fine | 60 | The Voyager's | 0 |
| 30 | Loudness DECAY TIME (24), coarse | 29 | The Voyager's | 0 |
| 31 | Loudness DECAY TIME (24), fine | 61 | The Voyager's | 0 |
| 32 | Loudness SUSTAIN LEVEL (25), coarse | 30 | The Voyager's | 127 |
| 33 | Loudness SUSTAIN LEVEL (25), fine | 62 | The Voyager's | 127 |
| 34 | GLIDE switch (38) | 65 | The Voyager's | 0 (off) |
| 35 | Oscillator 1 RANGE (4), octave | 74 | The Voyager's | 32 (8′) |
| 36 | Oscillator 2 RANGE (6), octave | 75 | The Voyager's | 32 (8′) |
| 37 | Oscillator 3 RANGE (9), octave | 76 | The Voyager's | 32 (8′; not heard while LO) |
| 38 | OSC. 3 CONTROL (28) | 79 | The Voyager's | 127 (on) |
| 39 | Oscillator 3 RANGE (9), LO/HI | 80 | The Voyager's | 0 (LO) |
| 40 | Mixer switch of the external input (32) | 81 | The Voyager's | 0 (off) |
| 41 | Mixer switch of oscillator 1 (29) | 82 | The Voyager's | 127 (on) |
| 42 | Mixer switch of oscillator 2 (30) | 83 | The Voyager's | 0 (off) |
| 43 | Mixer switch of oscillator 3 (31) | 84 | The Voyager's | 0 (off) |
| 44 | Mixer switch of the noise (33) | 85 | The Voyager's | 0 (off) |
| 45 | DECAY switch (39) | 88 | The Voyager's | 0 (off) |
| 46 | TUNE (1), coarse | 89 | NeoTeletext's own | 64 |
| 47 | TUNE (1), fine | 90 | NeoTeletext's own | 0 |
| 48 | MODULATION MIX (3) | 102 | NeoTeletext's own | 0 |
| 49 | Oscillator 1 RANGE (4), LO/HI | 103 | NeoTeletext's own | 127 (HI) |
| 50 | Oscillator 1 WAVEFORM (5) | 104 | NeoTeletext's own | 43 (sawtooth) |
| 51 | Oscillator 2 RANGE (6), LO/HI | 105 | NeoTeletext's own | 127 (HI) |
| 52 | Oscillator 2 WAVEFORM (8) | 106 | NeoTeletext's own | 43 (sawtooth) |
| 53 | Oscillator 3 WAVEFORM (11) | 107 | NeoTeletext's own | 0 (triangular) |
| 54 | Main output VOLUME (26) | 108 | NeoTeletext's own | 127 |
| 55 | OSCILLATOR MODULATION (27) | 109 | NeoTeletext's own | 0 (off) |
| 56 | Noise WHITE / PINK (34) | 110 | NeoTeletext's own | 0 (white) |
| 57 | FILTER MODULATION (35) | 111 | NeoTeletext's own | 0 (off) |
| 58 | KEYBOARD CONTROL 1 (36) | 112 | NeoTeletext's own | 0 (off) |
| 59 | KEYBOARD CONTROL 2 (37) | 113 | NeoTeletext's own | 0 (off) |

The 60 bytes are the 39 controls: eighteen pairs (36 bytes), the two knobs of table B, the three RANGE selectors as six bytes, the three waveform selectors and the thirteen switches. Bytes 0 to 45 are the Voyager's 46 controllers, bytes 46 to 59 NeoTeletext's 14.
- Reason: Decision A4: synthD has no patch format anywhere, so a patch is the list of its interface's control-change values; the Voyager's own preset dump is undocumented (section 11). The Voyager's values come first and in the order of its controller numbers, so that a Voyager's settings are the patch's first 46 bytes as its map numbers them, and NeoTeletext's own follow, as the controls the Voyager lacks. Values alone are carried because the order is fixed: the controller numbers would repeat the same 60 bytes in every patch. Every byte value from 0 to 127 is a position of its control (SD-18 to SD-20), so the receiver has no range to check beyond the top bit, and a patch cannot hold a value the instrument cannot take. A coarse controller precedes its fine controller, as SD-18 needs.
- Source: Decision A4 and DEC-6453 item 3; DEC-6465 answers 23 and 24. The controllers: SD-17. The order and the form: NeoTeletext's own (section 13 item 4). Whether the Voyager's own preset dump could be used instead: section 11.
- Verification: A test decodes the default patch's 60 bytes and compares each field with SD-21; a test checks, for every byte position and every value 0 to 127, that the patch is accepted and that the field is what the control change of that controller and value gives; a test checks that a patch of 59 or 61 bytes, and a patch with any one byte of 128 or more, is refused and the default patch plays; and a test checks that a patch applied at an instant equals the same 60 values sent as 60 control changes at that instant.

**SD-26. The same patch as control changes.** The sequence of 60 control changes that a patch stands for MUST be, in the patch's byte order, `0xBn, controller, value` for each byte, where `controller` is the table's for that byte. A program that wishes to set the whole panel in a stream without a bank MAY send that sequence; synthD takes it by SD-17, and after the last of them the panel equals the patch. In that sequence a coarse controller always comes before its fine controller, as SD-18 needs.
- Reason: The patch and the live messages are one definition, so that a panel can be set by either and a tool can turn one into the other with the table alone.
- Source: SD-17, SD-18, SD-22.
- Verification: The last test of SD-22.

**SD-27. What synthD needs of the bank and of a block.** The architecture specifies the bank (MIDI-55 to MIDI-57) and the block (MIDI-23 to MIDI-38); synthD's needs are these. (a) A bank image is of the fixed-patch form of MIDI-56: 1 to 128 patches of 60 bytes each, back to back, patch k at byte `k × 60`, numbered from 0 in the bank's order: at most 7,680 bytes, within the 16,384 of MIDI-55, carried by the bank codec in pieces of 1,011 bytes (eight DATA records for a bank of 128). (b) A program change's data byte, 0 to 127, is the patch's number in bank index 0 (SD-12). (c) No synthD message is longer than three bytes, since synthD takes no system exclusive (SD-8); a whole panel as control changes (SD-26) is 60 events, 240 bytes with every status byte and a one-byte delta time written, well within a block's 1,005 bytes and 256 events (MIDI-30, MIDI-31); synthD sets no lower bound of its own. (d) The server restates each live synthD sound, and begins each stored one with a restatement, as SD-28 states.
- Reason: The adopted interface has 128 presets and program numbers 0 to 127; the bank must reach them. The sizes are what the architecture needs to size records.
- Source: Voyager manual, pages 45 and 51 (128 presets; program change 0 to 127). Decision A4; MIDI-30, MIDI-31, MIDI-55, MIDI-56, MIDI-57.
- Verification: A test stores a bank of 128 patches, plays a program change to each, and checks the panel; the architecture's tests cover the carriage.

**SD-28. synthD's restatement.** The server MUST write synthD's restatement as MIDI-93 to MIDI-99 require, and it MUST be exactly these events, at one tick, in this order (MIDI-95): (1) the program change of the patch last chosen, or, where the last patch came inline as the 60 control changes of SD-26, those 60 control changes; (2) then, in ascending order of controller number, the latest value of every panel controller of SD-17 moved by a control change since (a reset all controllers that turned the GLIDE switch off counts as moving controller 65, SD-13 item 3), each coarse controller before its fine one, and both controllers of a pair where either moved; (3) then, where the pitch bend range is not the default of SD-6, the registered parameter 0 sequence that sets it (controller 101 at 0, controller 100 at 0, controller 6 the semitones, controller 38 the cents), followed by controller 101 at 127 and controller 100 at 127 so that no parameter is left selected; (4) then pitch bend, controller 7, the modulation wheel as controller 1 then controller 33 (SD-9), and controller 64, each only where it is not at the value a fresh synthD holds (pitch bend 8,192, controller 7 at 127, the wheel at 0, the pedal up). Held notes MUST NOT be restated. The server MUST write it in the first block of a live sound and at least once in every 50 blocks after (MIDI-96), and at tick 0 of block 0 of a stored sound (MIDI-99). synthD MUST render identical samples with and without a restatement that carries the state it already holds (MIDI-97): a program change to the patch already set, and a control change to the value a control already holds, MUST NOT restart the contours, reset the oscillators' phases or move the filter's state.
- Reason: A viewer who joins a live sound late, or loses a block, has none of the program changes and control changes sent before; the server, which sees every event, restates the whole state (DEC-6462 item 1). A restatement goes to every viewer, most of whom lost nothing, so it must be inaudible to them. Clearing the selection at the end keeps a later data entry from changing the range unasked. Volume is compared with a fresh synthD's 127 rather than with its value after a reset, since a reset leaves volume unchanged (MIDI-84) and a joining viewer's synthD starts at 127 (MIDI-82).
- Source: MIDI-82, MIDI-84, MIDI-93 to MIDI-99; DEC-6410 item 12; DEC-6462 item 1.
- Verification: A test drives synthD through a program change, an inline patch, ten panel control changes, a bend range and a bend, then plays the server's restatement into a fresh synthD and checks the two panels, ranges and wheels equal; a test plays the audio demo's synthD tune with and without a restatement at a seeded random tick of every block and checks the samples identical; a server test checks the bytes of the restatement for a known state.

---

## 10. The Voyager's panel against synthD's, control by control

The comparison is of the two panels, from the Voyager manual's sections and its figure of page 44, the Voyager's map (section 6.1) and the Model D manual. The "Controller" column is the Voyager's, from its map; the last column says what synthD does with it, by SD-17.

"Has it" means synthD's panel has a control of the same kind and range, moved by the Voyager's controller. "Has it differently" means synthD has a control for the same purpose whose positions or range differ: where the Voyager's bands fold onto synthD's, the Voyager's controller moves it (SD-18, SD-20); where they do not, synthD's control has a controller of NeoTeletext's own and the Voyager's is counted as ignored. "Lacks it" means the instrument modelled has no such control, and synthD has none; the Voyager's controller is counted as ignored (SD-17, table F).

| Voyager control | What the Voyager manual says of it (page) | Controller | synthD |
|---|---|---|---|
| LFO RATE | The dedicated low-frequency oscillator's rate, 0.2 Hz to 50 Hz (33, 34) | 3 and 35 | **Lacks it.** The modelled instrument has no dedicated low-frequency oscillator; oscillator 3 at LO serves (Model D manual, page 6). Ignored. |
| LFO SYNC | Four positions: OFF/SYNC, MIDI, KB, ENV. GATE (34) | 67 | **Lacks it.** Ignored. |
| Mod wheel bus SOURCE | Six positions: LFO triangle, LFO square, oscillator 3, sample and hold, ON/MOD2, NOISE/PGM (31) | 68 | **Has it differently:** the MODULATION MIX knob (control 3) blends oscillator 3 and noise; there is no low-frequency oscillator, sample and hold or fixed level to choose, and a blend is not a choice of one. MODULATION MIX takes NeoTeletext's controller 102; 68 is ignored. |
| Mod wheel bus DESTINATION | Six positions: PITCH (all oscillators), OSC. 2, OSC. 3, FILTER, WAVE, LFO/PGM (31, 32) | 69 | **Has it differently:** the OSCILLATOR MODULATION switch (27) and the FILTER MODULATION switch (35), which may both be on; no destination of one oscillator, of the waveform or of a rate. The switches take NeoTeletext's controllers 109 and 111; 69 is ignored. |
| Mod wheel bus SHAPING | Four positions: FILT. ENV., VELOCITY, PRESSURE, ON/PGM (31) | 70 | **Lacks it.** Ignored. |
| Mod wheel bus AMOUNT | 0 to 10: the most modulation the wheel lets through (32) | 6 and 38 | **Lacks it.** The wheel alone sets the amount. Controllers 6 and 38 are data entry on synthD (SD-6). |
| Pedal/On bus SOURCE | As the mod wheel bus's (30, 31) | 71 | **Lacks it.** The modelled instrument has one modulation path. Ignored. |
| Pedal/On bus DESTINATION | As the mod wheel bus's | 72 | **Lacks it.** Ignored. |
| Pedal/On bus SHAPING | As the mod wheel bus's | 73 | **Lacks it.** Ignored. |
| Pedal/On bus AMOUNT | 0 to 10 | 8 and 40 | **Lacks it.** Ignored. |
| MOD 1 and MOD 2 inputs | Inputs of the modulation busses, received only (Voyager 2.6 manual, printed page 53) | 2 and 34; 4 and 36 | **Lacks them.** Ignored. |
| FINE TUNE | Tunes the oscillators "+ or − 2 semitones"; not stored in a preset (20, 45) | None in the map | **Has it:** TUNE (control 1), ±242 cents, part of the patch, on NeoTeletext's controllers 89 and 90 because the map has none. |
| GLIDE RATE | "The glide can vary from a very fast to a very slow glide" (21) | 5 and 37 | **Has it:** GLIDE (control 2). |
| Oscillator 1 OCTAVE | Six positions, 32′, 16′, 8′, 4′, 2′, 1′ (19) | 74 | **Has it differently:** RANGE (control 4) is LO, 32′, 16′, 8′, 4′, 2′: it has LO and has no 1′. The octave is controller 74, with 1′ read as 2′ (SD-20 item 1); LO is NeoTeletext's controller 103. |
| Oscillator 1 WAVE | Continuously variable through triangle, sawtooth, square and rectangular (20) | 9 and 41 | **Has it differently:** WAVEFORM (control 5) is a switch of six fixed waveforms; the map gives the pair no bands to fold onto. NeoTeletext's controller 104; 9 and 41 are ignored. |
| Oscillator 2 FREQUENCY | "+ or − 7 semitones relative to Osc. 1" (19, 20) | 10 and 42 | **Has it:** control 7, ±700 cents. |
| Oscillator 2 OCTAVE | As oscillator 1's | 75 | **Has it differently:** control 6, as control 4, with NeoTeletext's controller 105 for LO. |
| Oscillator 2 WAVE | As oscillator 1's | 11 and 43 | **Has it differently:** control 8, NeoTeletext's controller 106; 11 and 43 are ignored. |
| Oscillator 3 FREQUENCY | As oscillator 2's; a greater range with 3 KB CONT off (20) | 12 and 44 (printed 45, section 6.2 item 5) | **Has it:** control 10, and 2.75 octaves either way with OSC. 3 CONTROL off. |
| Oscillator 3 OCTAVE | As oscillator 1's | 76 | **Has it differently:** control 9, with the Voyager's 3 FREQ (80) for LO. |
| Oscillator 3 WAVE | As oscillator 1's | 13 and 45 | **Has it differently:** control 11, whose second position is the reverse sawtooth; NeoTeletext's controller 107; 13 and 45 are ignored. |
| 1–2 SYNC | Oscillator 2 synchronised to oscillator 1 (20) | 77 | **Lacks it.** Ignored. |
| 3–1 FM | Linear frequency modulation of oscillator 1 by oscillator 3 (21) | 78 | **Lacks it.** Ignored. |
| 3 KB CONT | Oscillator 3's keyboard control on or off (20) | 79 | **Has it:** OSC. 3 CONTROL (control 28). |
| 3 FREQ | Oscillator 3's range, LO or HI (20) | 80 | **Has it differently:** LO is a position of each oscillator's RANGE switch; for oscillator 3, controller 80 selects it (SD-20 items 2 and 3). |
| Mixer EXTERNAL level and switch | The external audio input's level, 0 to 10, and on or off (17) | 14 and 46; 81 | **Has it differently:** controls 15 and 32; synthD's external input is fed from its own output. |
| Mixer OSCILLATOR 1, 2, 3 levels and switches | Level 0 to 10 and on or off, each (17) | 15 and 47, 16 and 48, 17 and 49; 82, 83, 84 | **Has them:** controls 12, 13, 14 and 29, 30, 31. |
| Mixer NOISE level and switch | Level 0 to 10 and on or off; the noise "is a white/pink hybrid" (17) | 18 and 50; 85 | **Has them:** controls 16 and 33. synthD also has the WHITE / PINK switch (34), which the Voyager lacks, on NeoTeletext's controller 110. |
| Filter CUTOFF | The cutoff of both filters; the dial is marked in hertz from 20 to 12K (22, 24) | 19 and 51 | **Has it differently:** CUTOFF FREQUENCY (control 17), one filter, a dial of −5 to +5, moved by the Voyager's pair over its whole range (SD-18). |
| Filter SPACING | The difference between the two filters' cutoffs, −3 to +3 octaves (25) | 20 and 52 | **Lacks it.** One filter. Ignored. |
| Filter RESONANCE | 0 to 10; self-oscillation from 8 (23, 25) | 21 and 53 | **Has it:** EMPHASIS (control 18), oscillation from 7.5 as built. |
| KB. CONT. AMOUNT | A knob, 0 to 10: how far the cutoff follows the keyboard (25) | 22 and 54 | **Has it differently:** two switches, KEYBOARD CONTROL 1 and 2 (controls 36 and 37): none, a third, two thirds or all. The map gives the pair no bands, so the switches take NeoTeletext's controllers 112 and 113, and 22 and 54 are ignored. |
| Filter MODE | Dual lowpass, or highpass and lowpass (23, 24) | 86 | **Lacks it.** Ignored. |
| Filter envelope ATTACK | 1 millisecond to 10 seconds (26) | 23 and 55 | **Has it:** control 20, 0 to 10,000 milliseconds (the Model D manual, page 11, says 10 milliseconds to 10 seconds). |
| Filter envelope DECAY | 1 millisecond to 10 seconds (26) | 24 and 56 | **Has it:** control 21. |
| Filter envelope SUSTAIN | A level (26) | 25 and 57 | **Has it:** control 22. |
| Filter envelope RELEASE | 1 millisecond to 10 seconds (27) | 26 and 58 | **Lacks it.** The DECAY switch (control 39) makes the DECAY TIME the release. Ignored. |
| AMOUNT TO FILTER | −5 to +5: the envelope adds to the cutoff or subtracts from it (27) | 27 and 59 | **Has it differently:** AMOUNT OF CONTOUR (control 19), 0 to 10, which only adds; the pair's upper half carries it and its lower half is no amount (SD-18 item 2). |
| Volume envelope ATTACK, DECAY, SUSTAIN | As the filter envelope's (26) | 28 and 60, 29 and 61, 30 and 62 | **Has them:** controls 23, 24, 25. |
| Volume envelope RELEASE | As the filter envelope's (27) | 31 and 63 | **Lacks it,** as above. Ignored. |
| ENV. GATE | The envelopes are triggered from the keyboard, or held on, or triggered from outside (27) | 87 | **Lacks it.** The modelled instrument has a shorting plug for its trigger input (Model D manual, page 14), which is not a panel control; synthD has no external trigger. Ignored. |
| MASTER VOLUME | "Full-clockwise is maximum output, full-counterclockwise silences" (29) | 7 and 39 | **Has it:** main output VOLUME (control 26), a parameter of the patch on NeoTeletext's controller 108, because controller 7 is the common layer's volume gain (SD-10); 39 is ignored. |
| HEADPHONE VOLUME | The headphone jack's volume (29) | None in the map | **Lacks it.** synthD has one output. |
| PITCH BEND wheel | "Affects the pitch of all three oscillators" (35) | Pitch bend | **Has it:** pitch bend (SD-6). |
| MOD WHEEL | The amount of the mod wheel bus's modulation (35) | 1 and 33 | **Has it:** SD-9. |
| GLIDE switch | "Turns on and off the GLIDE circuit" (35) | 65 | **Has it:** control 38. |
| RELEASE switch | "Used to shorten the Release time of both the filter and Volume envelopes" (35) | 88 | **Has it differently:** the DECAY switch (control 39): off, a released note is cut; on, it falls at the DECAY TIME. The two have the same purpose and bands, so 88 moves it (SD-17 rule a; section 6.2 item 7). |
| Touch surface X, Y and A | Filter cutoff, filter spacing and filter resonance, while touched (36) | None in the map | **Lacks it.** |

The settings the Voyager keeps in its EDIT mode, none of which has a message in the source, are in section 12.1.

**Controls synthD has that the Voyager's panel lacks, and what was done for each** (DEC-6465 answer 24):
1. MODULATION MIX (control 3): a continuous blend of oscillator 3 and noise; the Voyager chooses one source with a selector. NeoTeletext's controller 102.
2. OSCILLATOR MODULATION (27) and FILTER MODULATION (35) as two switches that may both be on; the Voyager chooses one destination with a selector. NeoTeletext's controllers 109 and 111.
3. Noise WHITE / PINK (34); the Voyager's noise is one "white/pink hybrid". NeoTeletext's controller 110.
4. KEYBOARD CONTROL 1 and 2 (36, 37) as two switches; the Voyager has a knob whose controllers have no bands. NeoTeletext's controllers 112 and 113.
5. The DECAY switch (39) as the choice between a cut and a fall at the decay time; the Voyager's RELEASE switch has the same purpose and the same two bands, and is folded onto: controller 88.
6. The LO position of the RANGE switches of oscillators 1 and 2 (controls 4 and 6); the Voyager has LO for oscillator 3 only, by its 3 FREQ switch, which oscillator 3's LO folds onto (controller 80). Oscillators 1 and 2 take NeoTeletext's controllers 103 and 105 in the same form.
7. The six fixed positions of each WAVEFORM switch (5, 8, 11), among them the sawtooth-triangular and oscillator 3's reverse sawtooth; the Voyager's wave control is continuous and its map gives it no bands. NeoTeletext's controllers 104, 106 and 107.
8. TUNE (1), which the Voyager has as FINE TUNE without a controller. NeoTeletext's controllers 89 and 90.
9. The main output VOLUME (26), whose Voyager controller is the common layer's gain. NeoTeletext's controller 108.

## 11. Could the Voyager's own preset system exclusive be the patch?

**The facts in the Voyager manual.**
1. The Voyager transmits and receives "System Exclusive Data (software and preset banks)" (page 46); the chart marks system exclusive as transmitted and recognised, "Must be enabled" (page 51).
2. SEND PRESETS "is a utility to send Sysex (System Exclusive) data for archiving the bank of presets in the Voyager's memory", to "another Voyager, or a computer with a MIDI interface and a program that can accept a manual Sysex dump" (page 39).
3. RECEIVE PRESETS "is a utility to import Sysex data for a bank of Voyager presets"; the Voyager "must be enabled to receive the presets", it shows "Sysex enabled", and the transfer "will replace any presets that are in memory" (page 39).
4. SEND SYSTEM ROM, SEND BOOT SYSTEM and RECEIVE UPDATE carry the Voyager's own software (page 40).
5. A bank is 128 presets (pages 45 and 48). A preset stores "all the Voyager's current front panel settings, Pitch Bend Amount, Programmable Mod Sources and Destinations, Keyboard Mode, Trigger Mode, and Preset Name" (page 44), with a name of "up to 24 characters" (page 44), and not FINE TUNE (page 45).
6. Later versions add single presets: "SysEx messages transmitted and received include Single Presets, Preset Banks, Operating System (System ROM) and Boot System" (Voyager 2.6 manual, printed page 54). The 3.4 manual's MASTER mode describes the same utilities for the operating system and boot software (printed pages 74 and 75), and says that such transfers need "MIDI Software capable of sending a generic Sysex bank file (.syx) or Standard MIDI file (.mid)" (printed page 75).
7. Not stated in any filed source: the manufacturer's identifier, the header, the length of the message or of a preset, the order and coding of the parameters, any checksum, and whether the bank is one message or many. None of the three manuals gives a byte of the message.

**Recommendation: it cannot be used, and should not be.** First, it cannot be implemented from the filed documents: the format is not documented in them, and filling it in from anywhere but a filed document is forbidden. Second, even with the format in hand it would be a poor fit: a Voyager preset holds a different panel (section 10), so most of its content would be discarded and nine kinds of synthD's controls (section 10's closing list) would have nowhere to go. Third, in the version 1.0 manual it exists only as a whole bank of 128, received only when a person enables it, and in every version only when "enabled". A synthD patch is therefore the list of control-change values of SD-22, as decision A4 already rules.

## 12. What is left out, and what departs

### 12.1 Of the adopted interface: left out

| Item of the Voyager's interface | Where the manual has it | Why synthD leaves it out |
|---|---|---|
| The MIDI IN CHANNEL setting, 1 to 16, and Omni Off | Pages 39 and 51 | A global setting of the hardware with no message; synthD hears all channels (SD-2). |
| The MIDI OUT CHANNEL setting and everything transmitted (notes, pitch bend, the controllers of the map, program change, system exclusive) | Pages 39, 46 and 51; Voyager 3.4 manual, printed pages 76 and 89 | synthD transmits nothing: a NeoTeletext instrument only receives. |
| SEND PRESETS and RECEIVE PRESETS, the system exclusive bank of presets, and the single presets of later versions | Page 39; Voyager 2.6 manual, printed page 54 | Undocumented in the source, a different panel, a whole bank only (section 11). |
| SEND SYSTEM ROM, SEND BOOT SYSTEM, RECEIVE UPDATE | Page 40; Voyager 3.4 manual, printed pages 74 and 75 | They carry the Voyager's own software; they serve only its hardware. |
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
| Every Voyager panel control that section 10 marks "lacks it", with its controllers: LFO RATE (3 and 35), LFO SYNC (67), the MOD 1 and MOD 2 inputs (2 and 34, 4 and 36), both busses' SOURCE (68, 71), DESTINATION (69, 72), SHAPING (70, 73) and AMOUNT (6 and 38, 8 and 40), 1–2 SYNC (77), 3–1 FM (78), filter SPACING (20 and 52), filter MODE (86), both RELEASE knobs (26 and 58, 31 and 63), ENV. GATE (87), HEADPHONE VOLUME and the touch surface's X, Y and A (no controller) | Section 10; Voyager 3.4 manual, printed pages 76 to 78 | The instrument modelled has none of them. Each controller is counted as ignored (SD-17, table F), but 6 and 38, which are data entry (SD-6). |
| The three oscillators' WAVE pairs (9 and 41, 11 and 43, 13 and 45) and the filter's KB AMOUNT pair (22 and 54) | Voyager 3.4 manual, printed pages 77 and 78 | Continuous controls whose map gives no bands; synthD's WAVEFORM selectors and KEYBOARD CONTROL switches cannot take a continuous value without bands of NeoTeletext's own, which DEC-6465 answer 24 does not allow for a fold, so they have controllers of their own and these are counted as ignored (SD-17, table F). |
| The 1′ footage of the octave controllers 74 to 76 | Voyager 3.4 manual, printed page 77 | synthD has no 1′; the band selects 2′ (SD-20 item 1). |
| The negative half of AMOUNT TO FILTER (27 and 59) | Voyager manual, page 27 | synthD's contour only adds; the lower half is no amount (SD-18 item 2). |
| MIDI Clock, recognised for the LFO SYNC switch's MIDI position | Voyager 3.4 manual, printed page 89; Voyager 2.6 manual, printed page 54 | synthD has no dedicated low-frequency oscillator, and a block carries no system real-time message (MIDI-8). |
| The touch surface's assignable "MIDI CNTL No." | Voyager 3.4 manual, printed page 79 | synthD has no touch surface. |
| The back panel's control and gate inputs (pitch, wave, filter, envelope rate, volume, pan, MOD1, MOD2, LFO rate, sample and hold, envelope gate, release, LFO sync, sample and hold gate), the mix-out loop and the accessory port | Pages 14, 18, 21, 25, 27 to 29, 32, 34, 37 | Voltages at jacks, not messages. |

### 12.2 Of the adopted interface: taken with a difference

| Item | The Voyager | synthD | Requirement |
|---|---|---|---|
| Channel | One channel, Omni Off | All channels alike | SD-2 |
| Pitch bend range | Ten choices a preset, default ±fourth, no message | Set by registered parameter 0, as in every synthesizer; default 797 cents either way, at most 3,100 (the architecture's open question 5, answered by DEC-6465 answer 5) | SD-6, MIDI-90 |
| Pitch bend resolution | Not stated in the source | All 14 bits, as in every synthesizer | SD-6, MIDI-91 |
| Reset all controllers, controller 121 | Not recognised (the 3.4 chart receives controllers 1 to 31, 33 to 63 and 65 to 88 only, printed page 89) | Acted on, RP-015's reset with volume unchanged and the GLIDE switch, controller 65, off, as in every synthesizer | SD-13, MIDI-84 |
| All sound off, controller 120 | Not recognised | Acted on, a fade within 256 samples, as in every synthesizer | SD-13, MIDI-86 |
| Sustain pedal, controller 64 | Not recognised | Acted on, down at 64 to 127, as in every synthesizer | SD-13, MIDI-87 |
| Note on of velocity 0 | Not stated in the source | A note off, as in every synthesizer | SD-3, MIDI-88 |
| Mode messages, controllers 124 to 127 | Not listed (the chart's mode messages are "All Notes Off") | Each acted on as all notes off and nothing more, as in every synthesizer | SD-13, MIDI-89 |
| Note priority | Four modes a preset | Lowest key | SD-14 |
| Trigger | Two modes a preset | Single | SD-15 |
| Program change | Recalls a preset without FINE TUNE | Sets the whole panel, TUNE included | SD-12 |
| Controllers 7 and 39 | The MASTER VOLUME knob's pair (Voyager 3.4 manual, printed page 78) | Controller 7 a gain beside the panel's VOLUME, by the seven-bit law every synthesizer shares; 39 counted as ignored; the panel's VOLUME on NeoTeletext's controller 108 | SD-10, SD-17, MIDI-82, MIDI-92 |
| Controllers 6 and 38 | The modulation wheel bus's AMOUNT | Data entry of registered parameter 0, as in every synthesizer; with no parameter selected, ignored | SD-6, MIDI-90 |
| Switch bands | 0 to 63 off, 64 to 127 on (version 3.4); 0 to 64 off, 65 to 127 on (version 2.6) | Version 3.4's: value 64 is on | SD-20, section 6.2 item 2 |
| Oscillator 3 FREQ's fine controller | Printed 45 in version 3.4, 44 in version 2.6 | 44 | SD-17, section 6.2 item 5 |
| The RELEASE switch, controller 88 | Turns the envelopes' release on and off | synthD's DECAY switch: on, a released note falls at the DECAY TIME; off, it is cut | SD-17, section 6.2 item 7 |

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

Each item exists because the filed interface does not define it.

1. **The controllers of the synthD-only controls (SD-17, rules b and c).** The Voyager's map has no control of the same purpose and bands for TUNE, MODULATION MIX, the LO/HI of oscillators 1 and 2, the three WAVEFORM switches, OSCILLATOR MODULATION, WHITE / PINK, FILTER MODULATION and the two KEYBOARD CONTROL switches, and its controller for the master volume is the common layer's gain, so these take controllers 89 and 90 (TUNE's pair) and 102 to 113, the lowest of those that MIDI 1.0's Table III leaves undefined and the Voyager's map does not use, in the order of today's patch (DEC-6465 answer 24). TUNE's pair of two consecutive single-byte controllers is this document's own pairing, since the Voyager's map leaves no controller from 1 to 31 free for MIDI-78 rule 5's pair.
2. **The scaling of a value to a field (SD-18, SD-19).** The Voyager's map gives no scale for any pair (its "VALUE/RANGE" is "-", section 6.2 item 1). Linear in the panel's own units, in integers, exact both ways; the Voyager's pairs at their 14 bits, NeoTeletext's own knobs in one controller; AMOUNT OF CONTOUR on the upper half of the Voyager's bipolar AMOUNT TO FILTER.
3. **The value bands that the map does not give (SD-20).** The fold of the octave controllers' 1′ band onto 2′; the LO/HI controllers 103 and 105 in the form of the Voyager's 80, and the derivation of the RANGE field from the octave and LO/HI controllers with the canonical octave 8′ for LO; the six near-equal bands of the WAVEFORM selectors. The Voyager's own bands are taken where it prints them, with the readings of section 6.2.
4. **The patch as 60 values, the Voyager's controllers in ascending order then NeoTeletext's (SD-22), and its equivalence to 60 control changes (SD-26).** No patch format exists for the instrument modelled, and the Voyager's is undocumented and of another panel (section 11).
5. **The default patch (SD-21).** As built.
6. **Controllers 64, 120 and 121 and the mode messages 124 to 127 (SD-13).** Standard MIDI 1.0 messages that the Voyager's chart does not recognise (version 3.4 receives controllers 1 to 31, 33 to 63 and 65 to 88 only), taken as part of NeoTeletext's common layer (MIDI-9) with the one behaviour each of `midi-architecture.md`, section 11.1; 64, 120 and 121 as built.
7. **All sixteen channels as one (SD-2).** As built.
8. **The pitch of a MIDI key (SD-5).** The manual does not state it; the modelled instrument's tuning, as built.
9. **The modulation wheel's curve (SD-9).** The manual does not state it; the square, as built.
10. **Controller 7 as a gain beside the panel's VOLUME, its law and its slew, and controller 39 ignored (SD-10).** The Voyager's map makes 7 and 39 its MASTER VOLUME's pair; the architecture makes controller 7 in every synthesizer a seven-bit gain separate from the patch's volume (MIDI-82), which governs; as built.
11. **The pitch wheel's default range and its most, and registered parameter 0 to set it (SD-6); the lowest-key priority and single trigger (SD-14, SD-15).** The Voyager makes each a setting of a preset with no message. synthD takes the modelled instrument's priority, trigger and default range; its range is set by registered parameter 0, which MIDI-90 adds to every adopted interface, up to the Voyager's largest choice, 31 semitones, a limit of NeoTeletext's choosing; and increment and decrement step it by one cent, NeoTeletext's own reading.
12. **How a moved control is heard (SD-23): the slews.** As built and measured.
13. **The drift of the oscillators.** Each oscillator's pitch wanders by up to 2 cents by default; the instrument can be set from 0 to 50 cents (`set_drift` in `mod.rs`). It is not a control of the panel, it is not in the patch, and nothing on the wire sets it today. This document adds no message for it: it stays at its default. If the owner wants it set by a channel, it needs a controller of its own, which would be a 40th control and a 61st byte, on one of the free controllers 114 to 119 (SD-17 rule c).
14. **synthD's restatement, event by event (SD-28).** The architecture sets the rule (MIDI-93 to MIDI-99); the exact events for synthD's panel, and the closing null parameter number, are this document's within it.

## 14. Open questions for the owner

**1. The panel's controller numbers: look for a later edition of the Voyager manual, or approve NeoTeletext's own?**
The filed manual (version 1.0 of the software, 2003) names two controllers and no others. DEC-6455 and `documents.tsv` describe it as holding a full map with coarse and fine pairs, so whoever researched it believed such a map exists; this file does not contain it, and its own words ("current as of 02/05/03 … Version 1.0") allow that a later version differs.
- *Option A: look for a later edition and file it.* If one documents control changes for the panel, the controllers and pairs of section 7 are replaced by its numbers for every control the two panels share (section 10's "has it" rows), its curves and bands are taken where it states them, and the patch of SD-22 is rebuilt in the same way. The seven kinds of control that only synthD has (section 10) still need numbers of NeoTeletext's own (question 2). This is what DEC-6453 asks for, if the document exists.
- *Option B: approve section 7 as NeoTeletext's own.* It is complete and can be built now. It is compatible with nothing outside NeoTeletext, which DEC-6453 permits only "where no existing interface covers the instrument".
- *Option C: adopt another instrument's interface for the same panel.* DEC-6455 records that the maker's reissues of the instrument modelled take MIDI "for notes, pitch bend and modulation only"; no document of theirs is filed, so nothing can be said of them here.
- *Recommendation:* A first, as a short search by the owner or the main session (this document's author was not permitted to fetch anything); if no edition with a panel map can be filed, B. Sections 4, 5, 8 and 10 to 12 stand under either answer; only the numbers, pairs and bands of sections 7 and 9 change.
- Answered by DEC-6465 (since accepted by the owner): option A, a search for a later edition of the Voyager manual with a panel controller map, begun at once; if none is found, section 7 is approved as NeoTeletext's own (option B).
- *Closed on 18 November 2026.* The search found and filed two later manuals that print the map: the combined user's manual for operating system 3.4 (2008; printed pages 76 to 78, chart on printed page 89) and the Rack Mount Edition's manual for software 2.6 (2005; printed pages 53, 54 and 58), both in `minimoog/manuals/` and described in `minimoog/documents.tsv`. Option A was carried out: section 6 reproduces the map with its readings, and section 7, the patch of section 9, the reset table of SD-13, the restatement of SD-28 and sections 10 to 15 were rewritten so that synthD follows the Voyager's controller, pair and bands for every control the two panels share. The earlier map of NeoTeletext's own (coarse controllers 3, 9, 14, 15 and 20 to 23, single controllers 24 to 31, 85 to 90 and 102 to 116, a patch of 47 bytes) is withdrawn.

**2. If a Voyager map is adopted (option A), how are the controls that only synthD has controlled?**
They are MODULATION MIX, the two modulation switches, WHITE / PINK, the two KEYBOARD CONTROL switches, the DECAY switch, LO on oscillators 1 and 2, and the six fixed waveforms.
- *Option A: controllers of NeoTeletext's own,* from those the adopted map and MIDI 1.0 both leave unused, by the rules of SD-17. Exact, and clearly marked as additions.
- *Option B: non-registered parameter numbers,* keeping every ordinary controller for the Voyager's map. Four messages a change where a controller needs one.
- *Option C: fold each onto the nearest Voyager control* (for example the two KEYBOARD CONTROL switches as four bands of the Voyager's keyboard amount knob; the six waveforms as six bands of the continuous wave control; the DECAY switch as the RELEASE switch). A Voyager-style controller then moves something on synthD, but the meanings differ, MODULATION MIX and WHITE / PINK have nothing to fold onto, and a value written for a Voyager would not sound the same.
- *Recommendation:* A for the controls with no counterpart (MODULATION MIX, the two modulation switches, WHITE / PINK), and C only where the Voyager's control has the same purpose and the bands can be stated exactly (the keyboard amount, the octave and wave selectors, the release switch), decided control by control once the map is in hand.
- Answered by DEC-6465 (since accepted by the owner): option A, and only if question 1's search finds a map: controllers of NeoTeletext's own for the controls only synthD has, folding onto a Voyager control only where its purpose and bands are the same.
- *Closed on 18 November 2026.* The map was found (question 1), and each of the controls named above was examined against it (section 10's closing list). Two fold onto a Voyager control of the same purpose and the same printed bands: the DECAY switch onto the RELEASE SWITCH, controller 88, and oscillator 3's LO onto the 3 FREQ switch, controller 80. The rest take controllers of NeoTeletext's own from those MIDI 1.0's Table III and the Voyager's map both leave unused, by SD-17's rule (c): TUNE 89 and 90, MODULATION MIX 102, oscillator 1's LO/HI 103, oscillator 1 WAVEFORM 104, oscillator 2's LO/HI 105, oscillator 2 WAVEFORM 106, oscillator 3 WAVEFORM 107, the main output VOLUME 108, OSCILLATOR MODULATION 109, WHITE / PINK 110, FILTER MODULATION 111, KEYBOARD CONTROL 1 112 and KEYBOARD CONTROL 2 113. The WAVEFORM switches and the KEYBOARD CONTROL switches are not folded onto the Voyager's WAVE and KB AMOUNT pairs because those pairs have no printed bands; MODULATION MIX, the modulation switches and WHITE / PINK have no counterpart of the same purpose.

**3. Should controller 7 be the panel's VOLUME knob, or stay beside it?**
The source does not say what the Voyager's controller 7 moves. SD-10 keeps what is built: two gains, the patch's VOLUME (controller 87) and a performance volume (controller 7).
- *Option A: keep both* (SD-10). A patch's level and a score's fades are independent; controller 7 behaves the same on every NeoTeletext synthesizer.
- *Option B: one knob.* Controller 7 moves the panel's VOLUME, controller 87 is not used and the patch is 47 bytes with byte 33 carried by controller 7. Simpler, and nearer to "the Voyager's volume is in its preset", but a program change then overwrites a fade, and the shared volume law would replace the knob's linear law, which changes the level of every existing patch whose VOLUME is not 100.
- *Recommendation:* A. The architecture document should rule the same way for every family.
- *Status:* answered by the architecture, subject to the owner's approval of it: MIDI-82 and MIDI-92 make controller 7 in every synthesizer a gain on the part's output, separate from any volume of the patch, by one law. That is option A, which SD-10 states.
- *Updated on 18 November 2026:* the Voyager's map, now filed, answers what the source had left unstated: on the Voyager, controllers 7 and 39 are the MASTER VOLUME knob's pair (Voyager 3.4 manual, printed page 78), which is option B's reading. The architecture's rule still governs, so option A stands: the panel's VOLUME moves from controller 87, which is now the Voyager's ENV GATE SWITCH, to NeoTeletext's controller 108 (SD-17, table B), and the departure from the Voyager's map is listed in section 12.2.

**4. Should reset all controllers turn synthD's GLIDE switch off?**
synthD's GLIDE switch is a panel control of the patch, carried by controller 65, which is both the Voyager's GLIDE SWITCH (SD-17, rule (a)) and the controller MIDI 1.0 names the portamento switch. MIDI-84, following DEC-6464's reading of RP-015, both resets "the sustain, portamento, sostenuto and soft pedals, controllers 64 to 67, off where the family has them" and leaves unchanged "every parameter of the patch moved by a control change"; for synthD's controller 65 the two clauses disagree.
- *Option A* (written, SD-13 item 3): the GLIDE switch is a parameter of the patch and is left as it is; a reset changes no part of the sound's patch.
- *Option B:* the GLIDE switch is turned off, as RP-015's portamento switch; a reset then changes the patch's glide, and a restatement (SD-28) must restate controller 65 after it.
- *Option C:* move the GLIDE switch off controller 65 to an undefined controller under MIDI-78 rule 5, so that controller 65 is not the patch's; breaks SD-17's rule (a), which uses the Voyager's own controller, and leaves the controller MIDI 1.0 names unused.
- *Recommendation:* A, until RP-015 is filed and read (`midi-architecture.md`, section 1.5); if its text resets controller 65 whatever it carries, B. The architecture's MIDI-84 should say which clause holds where a family's patch parameter sits on controllers 64 to 67.
- Answered by DEC-6465 (since accepted by the owner): option A, as written (SD-13 item 3): controller 121 leaves the GLIDE switch as the patch set it; revisited when RP-015 is filed.
- Revisited on 18 November 2026, when RP-015 was filed (rdm SRC-6468): its text sets controller 65 whatever it carries ("Set Pedals (#64, #65, #66, #67) to 0", page 2), DEC-6464 version 2 limits a manufacturer's latitude to the other controllers (item 4) and makes RP-015 hold where a family would depart from it (item 6), and MIDI-84 item 2 now says that the pedals 64 to 67 are set to 0 wherever a family responds to one with its pedal meaning, even as a parameter of its patch. Option B is therefore written (SD-13 item 3, SD-28), as this question's recommendation said it would be if RP-015 read so; it replaces DEC-6465's answer A and awaits the owner's confirmation with DEC-6464.

**Questions of the architecture that change this document.** Two of `midi-architecture.md`'s open questions (section 20) decide parts of this document and are not repeated here: open question 1, the codec numbers (synthD's code 15 or its present code 7; the scope above; answered by DEC-6465 with new codes 12 to 19), and open question 5, the pitch bend range by registered parameter 0 in every family, which SD-6 is written for under option A, the answer DEC-6465 gave, with what SD-6 would be under option B stated there.

## 15. Differences from what is built today

What exists is described in `synthesizer-wire-format.html` and in synthD's source. Implementing this document changes the following.

**The patch.**
1. Today a patch is 36 bytes of NeoTeletext's own design (`PATCH_BYTES`, `Patch::from_bytes`, `Patch::to_bytes` in `patch.rs`): fields in the panel's units, two-byte fields with the low byte first, and thirteen switches packed as bits into bytes 34 and 35. It becomes 60 bytes, each a control change's value from 0 to 127, in the order of the Voyager's controller numbers and then NeoTeletext's (SD-22). The 39 fields, their units and their ranges do not change; only their coding does.
2. Today's two-byte signed fields (TUNE, both FREQUENCY knobs, CUTOFF FREQUENCY) and two-byte times become coarse and fine pairs scaled by SD-18, and so do today's one-byte knobs of 0 to 100 that the Voyager carries as pairs (GLIDE, the five mixer volumes, EMPHASIS, AMOUNT OF CONTOUR, the two SUSTAIN LEVELs); MODULATION MIX and the main output VOLUME become one value of 0 to 127 scaled by SD-19. Today's range bytes, 0 to 5, become two values each, the Voyager's octave bands and a LO/HI switch (SD-20 items 1 to 3); today's waveform bytes, 0 to 5, become values in six bands (SD-20 item 5). Today's two switch bytes become thirteen bytes, one a switch.
3. Today a patch is refused for a field out of range (`PatchError`: a knob above 100, a position above 5, a time above 10,000, an unused switch bit). After the change every value from 0 to 127 is valid in every byte, and the only faults are the length and a byte above 127. `PatchError`'s seven kinds reduce to those two.
4. The engine's `SYNTHD_PATCH_BYTES` (`neoteletext-audio/src/codec.rs`), the server's patch check and its refusal messages, and the documents' "36 B" all follow. The kit's `packSynthdPatch` (today's 36-byte builder under its new name) and its initial patch are removed from the kit (DEC-6462 item 3, MIDI-22): the server takes a patch as named fields in the panel's units and writes canonical values (MIDI-14, SD-22), and the kit keeps only the generated types and the call that sends them.
5. A DATA record of a synthD bank holds 28 patches of 36 bytes today. Under MIDI-55 a bank image is instead cut into pieces of 1,011 bytes whatever its patches' boundaries, so a bank of 128 patches of 60 bytes, 7,680 bytes, travels in eight DATA records.

**The messages.**
6. Today synthD takes control changes of controllers 1, 7, 64, 120, 121 and 123 only, and counts every other as ignored (`control_change` in `mod.rs`). It gains the 60 controllers of SD-17 (39 controls: eighteen pairs, three RANGE selectors of two controllers each, and fifteen single controllers), and controller 33 as the modulation wheel's fine part (SD-9). `SynthD` needs a way to set one field and keep the 14-bit numbers of the eighteen pairs and the wheel, and the octave and LO/HI values of each RANGE; `set_patch` remains as the way a patch and a program change set all 39.
7. Today the server and the kit refuse a control change of any controller but 1, 7, 64, 120, 121 and 123 ("a control change is of controller 1, 7, 64, 120, 121 or 123"). For synthD the server must allow the controllers of SD-17's tables A to E, controller 33, the registered parameter controllers of SD-6 and the mode messages 124 to 127 as well, and must refuse the controllers of table F, which a receiver counts as ignored (MIDI-10); the kit's copy of the rule is removed (MIDI-22).
8. Today a program change chooses patch 0 to 31 and a bank holds 1 to 32 patches. They become 0 to 127 and 1 to 128 (SD-12, SD-27). Today a program change must have a second data byte of 0 in its four-byte slot; under decision A3 a program change is the ordinary two-byte MIDI message.
9. Today a patch missing from the bank or out of range becomes the default with no message. After the change a program change to a missing patch is also counted as ignored (SD-12).
10. Nothing changes in note on, note off, the pitch bend's 14-bit reading, controller 7, the sustain pedal, all sound off or all notes off: SD-3 to SD-5, SD-10, SD-11 and SD-13 items 1 and 2 describe what is built. The modulation wheel gains its fine part, controller 33, and its travel becomes the 14-bit number over 16,383, so that controller 1 at 127 alone gives 0.9846 of the full depth instead of all of it (SD-9). Three things change in the common layer: synthD gains registered parameter 0 for its bend range, with the parameter number selection, increment and decrement (SD-6), which today it counts as ignored; it gains the mode messages 124 to 127 as all notes off (SD-13 item 4), which today it counts as ignored; and reset all controllers and a lost block also clear the parameter number selection (SD-13 item 3, SD-25). The lowest-key priority, the single trigger and the glide (SD-14 to SD-16) are as built.
11. Today key pressure, channel pressure and every other status are counted as ignored; that stays. System exclusive, which today cannot be expressed in a four-byte slot, can be expressed under decision A3 and is counted as ignored (SD-8).

**The block.**
12. Today a synthD block is 1 to 16 slots of four bytes (a time, a status byte, two data bytes), under codec 7. Under decision A3 it becomes a Standard MIDI File track-event list with a tick of 0.1 millisecond, of at most 1,005 bytes and 256 events (MIDI-23 to MIDI-38), under codec 15 if the architecture's open question 1 is answered as recommended, or still under codec 7 if not; DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired, so it is codec 15. That change is the architecture's and is the same for every family; synthD's part of it is only that a whole panel as control changes (60 events, SD-26) no longer has to fit in 16 slots.

**The restatement.**
13. Today the kit's program repeater rewrites each part's last program change every 500 milliseconds (`program-repeater.ts`), and nothing restates synthD's panel control changes. Under SD-28 the server restates synthD's whole state (program or inline patch, every panel controller moved since, the bend range, the wheels, the volume and the pedal), and the kit's repeater is removed (MIDI-22, MIDI-93 to MIDI-99).

**Tests and documents.**
14. The tests that build patches from bytes (`tests/synthd_instrument.rs`, `tests/synthd_control_sweep.rs`, `tests/synthd_support.rs`, the engine's `tests/synths.rs`, the server's and the kit's patch tests, and the validation script `minimoog/validation/patch_hex.py`) change to the 60-byte form. New tests are those each requirement's "Verification" names.
15. The module documentation of `patch.rs` ("its byte form is this crate's own", the byte layout table) and of `mod.rs` (the list of messages taken) are rewritten to cite this document's requirements once they are rdm requirements. The two HTML documents in `synthesizer-reference/` describe the old form and are regenerated.
16. `minimoog/documents.tsv`'s row for the 2003 Voyager manual now says what the file holds (controllers 1 and 7 only) and names the two later manuals that hold the map. DEC-6455's paragraph on the programming interface, which said the 2003 manual holds the map, is to be corrected to name the Voyager 3.4 manual (printed pages 76 to 78) and the Voyager 2.6 manual (printed pages 53 and 54).
