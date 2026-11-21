# synth106 and synth60: the programming interface

**Purpose.** This document specifies how synth106 and synth60 are played and programmed: every MIDI message they take, what each does, what a patch of each is, byte by byte, and how every value of the adopted interfaces becomes a field of the instruments' patch. It is the basis for implementing the two instruments' part of the synthesizer protocols.

**Scope.** synth106 and synth60 only: the two instruments that model the Roland Juno-106 and the Roland Juno-60 (`neoteletext-common/docs/audio/synthesizers.md` says once which instrument each synthesizer models). They are two kinds for a channel program (DEC-6461 item 3) that share one codec and one implementation underneath. The transport (blocks, records, packets), the form of a block, how a bank of patches is stored and named, how a system exclusive message longer than one block or one record travels, the restatement of a live sound's state, and the behaviours common to every synthesizer belong to the architecture document, `midi-architecture.md` in this folder (cited below by its requirement numbers, MIDI-1 to MIDI-125, and its open questions); the form of the typed requests a channel's program sends belongs to the Rust server's document (DEC-6462). This document states what these two instruments need of them and refers to them. The sound of the instruments (oscillator, filters, envelope, chorus) is not specified here.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

**The findings the owner should read first.**
1. **The Juno-106's own interface is complete for synth106's patch and is adopted whole.** Its owner's manual gives, byte by byte, the three system exclusive messages (a patch of 18 values sent when a patch is chosen, the same 18 values when the Manual button is pressed, and one parameter changed), the parameter numbers 0 to 17, and both switch bytes bit by bit (owner's manual, page 35). Every one of the 18 values maps to exactly one field of the patch built today, and every field built today for synth106 is one of them (section 9).
2. **The JU-06A chart names its controllers but gives no ranges and no value bands.** Roland's chart (both pages read) lists, for each controller number, only a parameter name, whether it is transmitted and whether it is recognised. It does not say how a controller's value 0 to 127 maps to a slider, nor which values select which position of a switch, nor in which order a switch's positions run. Every scaling and every value band in section 10 is therefore NeoTeletext's own, chosen by one rule and listed in section 16. Open question 2 asks whether to look for a Roland document that states them.
3. **synth60's patch needs something the Juno-106 message cannot carry.** The Juno-60 has no MIDI (its owner's manual: its digital port is the DCB, "Please do not connect the Juno-60 to any other device but the OP-8", page 21). Its sub-oscillator switch, its envelope as a source of pulse-width modulation and its chorus with both buttons down have no bit in the Juno-106's 18 values; the JU-06A has a controller for each (controllers 28, 15 and 93). Section 12 specifies a synth60 patch as the Juno-106's 18 values followed by those three controller values: 21 values in all. It is NeoTeletext's own composition of two adopted interfaces, listed with its alternatives in section 16 and open question 1.
4. **The JU-06A's sound-module map is a superset aimed at a newer instrument.** Of its 39 controllers, 28 move something synth106 or synth60 has (25 a patch field, and modulation, hold and bend range), and 11 move things neither has (a delay effect, tempo sync, an LFO waveform choice, an LFO trigger, expression, portamento, assignment modes). Section 10 marks each. Open question 3 asks which of the performance controls the instruments should gain.
5. **Where the Juno-106's interface differs from the behaviours common to every NeoTeletext synthesizer, the common rule holds** (`midi-architecture.md` section 11.1, MIDI-84 to MIDI-92). Four departures follow: hold is down at 64 to 127, not 1 to 127 (MIDI-87); pitch bend uses all 14 bits, not the top eight (MIDI-91); reset all controllers, which the Juno-106 does not recognise, follows the Recommended Practice RP-015 and leaves the bend range and the volume as they are (MIDI-84, DEC-6464); and the bend range is also set by registered parameter number 0 (MIDI-90), beside the JU-06A's controller 87. Section 15.4 lists them.

---

## 1. Sources

All files are under `~/devel/synthesizer-reference/juno/manuals/`. Page numbers are printed page numbers. In the Juno-106 owner's manual the printed page n is the PDF's page n (the fold-out of the panel, printed "3-4", is PDF page 3). In the Juno-60 owner's manual the printed page n is the PDF's page n + 2.

| Short name here | File | What it is used for |
|---|---|---|
| **Juno-106 manual** | `roland-juno-106-owners-manual-roland-cdn.pdf` (36 PDF pages; Roland's "JUNO-106 Owner's Manual", part RUS10003; a scan, read as page images) | The adopted interface. Page 35, "MODEL JUNO-106 MIDI Implementation": sections 1.1 to 1.3 (transmitted data), 2.1 to 2.3 (recognised data), 3.1 to 3.3 (the three exclusive messages) and 3.4 (the parameter number table). Page 34, "MODEL JUNO-106 MIDI Implementation Chart". Pages 25 to 28: MIDI channel, the MIDI function switch I, II and III, the program-change numbering of groups A and B, the application of system exclusive. Page 29: the receivable range of notes. Pages 6 to 11: memory, editing, writing, tape. Pages 16 to 24: every panel control, the assignment modes Poly 1 and Poly 2, the controllers beside the keyboard. Pages 32 and 33: the specifications. |
| **JU-06A chart** | `roland-ju-06a-midi-implementation-chart.pdf` (2 pages; Roland's "MIDI Implementation Chart", "Model: JU-06A", "Date: Sep. 5, 2019", "Version 1.00"; a text PDF) | The adopted interface for control changes. Page 1, headed "SOUND MODULE", "Model: JU-06A": the sound-module mode, specified here. Page 2, headed "Model: JU-06A (Control Surface Mode)": the control-surface mode, left out (section 15.2). |
| **Correspondence table** | `roland-juno-106-system-8-parameter-correspondence-table.pdf` (1 page; Roland's "JUNO-106/SYSTEM-8 Parameter Correspondence Table", © 2016, edition 01) | A second statement by Roland of which controls make up a Juno-106 sound: its "Controller Map" numbers 25 of the Juno-106's panel controls, 1 to 23, 28 and 29 (the sixteen sliders, the switches and the two chorus buttons; 14 and 15 mark the VCF envelope slider and its polarity switch together) and gives the SYSTEM-8 parameter of each. Used to confirm that the 18 values of the system exclusive patch are the whole programmable panel, and nothing else. Its SYSTEM-8 value ranges (0 to 255, −128 to +127) are the SYSTEM-8's and are not used. |
| **Juno-60 manual** | `roland-juno-60-owners-manual-roland-cdn.pdf` (38 PDF pages; Roland's "JUNO-60 Owner's Manual", "'83 APR"; a scan) | What synth60's panel is and what its memory holds: page 6 (56 patches, banks 1 to 7 of patches 1 to 8, numbered 11 to 78), page 7 (what a patch memorises, including the OCTAVE TRANSPOSE switch), pages 12 and 13 (the DCO, the PWM mode switch ENV, MANUAL, LFO, the sub-oscillator switch), page 14 (HPF and VCF), page 16 (VCA and envelope), page 17 (the LFO and its TRIGGER MODE switch), page 18 (the controllers), page 21 (the DCB), page 22 (the chorus), pages 32 and 33 (the specifications). |
| **Juno-60 service notes** | `roland-juno-60-service-notes.pdf` (26 PDF pages; Roland's "JUNO-60 Service Notes", "April 10, 1983"); PDF page 16, printed page 22, "Adjustment summary", Table 6 "Panel Control Settings by Test Program" and the "Test Modes" | That a Juno-60 patch also holds the LFO's trigger mode (the column "MODE", A or M) and the octave transpose (column "TRANS", N or D), and the chorus as one of four settings (column "CHORUS", 0 to 3); the Juno-60's key-assignment test modes. |
| **synth106's source** | `~/devel/neoteletext-renderer-teletext/crates/neoteletext-audio-instruments/src/synth106/patch.rs`, `mod.rs` and `voice.rs`, as they stood on 18 November 2026 (engine commit `dd0421c6`) | What is built today: the patch's fields, the 18-byte reader and writer, the messages taken, how synth60's extra settings are held and played. |
| **Wire format as built** | `~/devel/synthesizer-reference/synthesizer-wire-format.html` and `programming-the-synthesizers.html` (read from the code on 18 November 2026, under the old names) | What exists today on the wire and in the kit, for section 18. |
| **The architecture document** | `neoteletext-common/docs/audio/midi-architecture.md` (this folder) | The frame this document works in: the block's grammar and bounds (MIDI-23 to MIDI-38), the bank codec and the bank image (MIDI-54 to MIDI-58), choosing a patch (MIDI-59 to MIDI-66), the channel map (MIDI-67, MIDI-68), the behaviours common to every synthesizer (MIDI-84 to MIDI-92), the restatement of a live sound and the loss of a block (MIDI-93 to MIDI-103), the codec numbers (MIDI-107 to MIDI-109, with its open question 1). Where this document and it differed, this document has been brought into line with it. |

**The filed MIDI standards.** The MIDI 1.0 Detailed Specification 4.2 and Standard MIDI Files 1.0, in the MIDI Manufacturers Association's bundle of document version 96.1 (rdm SRC-6469), and the Recommended Practice RP-015, "Response to Reset All Controllers" (rdm SRC-6468), are filed in `~/devel/teletext-reference/midi/`; `midi-architecture.md`, section 1.5, describes them and the form of their citations, "MIDI 1.0 4.2, printed page n (PDF m)", the PDF page being that of the filed file. This document uses MIDI 1.0 only for what is common to all MIDI (the status bytes, that a note on of velocity 0 is a note off, the standard meanings of controllers 7, 64, 120, 121 and 123 to 127, registered parameter number 0, the form of a system exclusive message: `F0`, a manufacturer's identifier, data bytes below 128, `F7`), Standard MIDI Files 1.0 only for the form of a system exclusive event in a block, and RP-015 through DEC-6464 version 2 and the architecture's MIDI-84. Every statement below that rests on one of them was read against the filed copy on 18 November 2026 and cites the place it rests on.

Decisions this document follows: DEC-6453 (each instrument is programmed exactly as its most well-known existing interface does it; NeoTeletext defines something only where nothing exists, and records why), DEC-6454 (the provenance of synth106 and synth60 and the choice of the Juno-106's system exclusive with the JU-06A's controllers as their interface), DEC-6461 (the names; each name its own kind), DEC-6462 (the Rust server is the one implementation of the programming interface: it validates, packs, builds blocks and records, splits and restates; the kits are thin and hold no instrument logic), DEC-6464 (every synthesizer answers reset all controllers identically, by RP-015, volume unchanged; recorded as proposed and awaiting the owner's confirmation), DEC-6410 and DEC-6429 (instruments as codecs of the audio profile), DEC-6428 (the clean-room rules), and the architecture decisions A1 to A6 of the brief of 18 November 2026.

No web page was fetched and no reference program was opened for this document.

## 2. Terms

- **synth106.** NeoTeletext's six-voice synthesizer that models the Juno-106 (Scope).
- **synth60.** NeoTeletext's six-voice synthesizer that models the Juno-60 (Scope). It shares synth106's code and codec (DEC-6461 item 5) and differs in its oscillator's clock, its envelope, its high-pass filter's positions and the extra settings of section 12.
- **The adopted interfaces.** (a) The Juno-106's MIDI implementation and system exclusive, as the Juno-106 manual states them; (b) the JU-06A's control changes in its sound-module mode, as the JU-06A chart states them.
- **Slider.** One of the sixteen continuous controls of the panel that a patch holds, numbered 0 to 15 by the Juno-106 manual's parameter number table. Its value is 0 to 127.
- **Switch byte.** One of the two bytes after the sliders, parameter numbers 16 and 17, whose bits hold the panel's switches.
- **The 18 values.** The sixteen slider values and the two switch bytes, in parameter-number order: the content of the Juno-106's patch messages.
- **The three synth60 settings.** The pulse-width modulation source with its third position ENV, the sub-oscillator switch, and the chorus with its fourth setting I+II. The Juno-106 has none of the three positions or switches.
- **Patch.** The positions of all of an instrument's programmable controls. A synth106 patch is the 18 values; a synth60 patch is the 18 values and the three synth60 settings (section 12).
- **Bank.** The set of patches a sound plays from, chosen among by program change. How a bank is stored and named is the architecture document's (MIDI-55 to MIDI-57): a stored object of the bank codec whose bank image is the patches' messages back to back (MIDI-56).
- **The panel.** The patch an instrument is playing now, which control changes and system exclusive messages move. On the Juno-106 it is called the edit state: "If you move a desired control even slightly, its setting position of that patch program will be deleted and ready to be manually controlled" (Juno-106 manual, page 7). Changing the panel never changes the bank.
- **Block.** 20 milliseconds of a sound's input, 960 samples at 48,000 Hz (decision A2). Its content is a Standard MIDI File track-event list whose tick is 0.1 millisecond, in which a system exclusive message is written `F0`, its length as a variable-length quantity, then its bytes after `F0` up to and including `F7` (decision A3; its grammar and bounds are the architecture's, MIDI-23 to MIDI-38: at most 1,005 bytes and 256 events a block, a system exclusive event 1 to 256 bytes after `F0`).
- **Counted as ignored.** A message the instrument does not act on adds one to a count the instrument keeps (`ignored_events` today), and nothing else happens. Nothing is an error. It is what the architecture calls "passed over and counted" (MIDI-34).
- **Value band.** The range of controller values that selects one position of a switch.
- **Canonical value.** The one value a sender writes for a given position or setting where several values select it.
- **Not stated in the source.** The filed document does not say. Nothing is supplied from memory in its place; where an instrument needs an answer, the answer is NeoTeletext's own and is listed in section 16.

---

## 3. Channels and the MIDI function switch

The Juno-106 manual describes a three-position MIDI FUNCTION switch on the rear panel (page 27): "I. Select this position for communication of only Keyboard and Hold information"; "II. … the Keyboard, Hold, Bender on/off control, and Patch Selection information"; "III. … the information of II plus tone color parameter information by means of System Exclusive message. Regarding Patch Selection information, it can be received by the Juno-106, but is not transmitted from it." Page 35 states the same per position: section 2.1 (function 1: note events, hold, channel mode messages), 2.2 (function 2: those, and program change, pitch bender and LFO modulation), 2.3 (function 3: those of function 2 and exclusive messages).

**S106-1. Every message as in function III.** synth106 and synth60 MUST act on every message that the Juno-106 recognises with its MIDI function switch at III: the messages of sections 2.1, 2.2 and 2.3 of the Juno-106 manual's page 35. No message, setting or field selects function I or II.
- Reason: A NeoTeletext sound is played from a program's messages, and every one of them should be heard; functions I and II exist on the hardware to stop a second instrument on the same cable from acting on what it should not. The switch is a setting of the hardware with no message, which decision A6 lets be left out.
- Source: Juno-106 manual, pages 27 and 35 (sections 2.1 to 2.3), page 34 (the chart's three columns of "Recognized"). Listed as left out in section 15.1.
- Verification: A test sends one message of each kind that section 2.3 recognises (note on, note off, hold, all notes off, a mode message, program change, pitch bender, controller 1, and each of the three exclusive messages) and checks that each changes the instrument's state as its requirement says.

**S106-2. All channels are one instrument.** synth106 and synth60 MUST act on a channel message alike whatever its channel, 0 to 15, and MUST act on a system exclusive message of section 7 whatever its channel byte (byte `d`, `0000 nnnn`). The sixteen channels are one keyboard and one panel.
- Reason: A sound holds one instrument. The Juno-106 is in OMNI ON mode when switched on ("When power is first applied, receiver's mode is OMNI ON, POLY mode", page 35, section 2.1), and in OMNI ON mode it takes voice messages on "all channels"; it takes mode messages and, by its chart's "Tx = Rx", everything else on its one MIDI channel, which is a setting of the hardware (page 25) with no message. synth60 has no MIDI of its own and is given the same rule. What is built does this ("The instrument is one part and hears every channel", `mod.rs`).
- Source: Juno-106 manual, page 25 ("Changing MIDI Channels"; "If the receiving MIDI Channel is different from the transmit Channel number, MIDI information is not received (except the unit is set to Omni mode)"), page 34 (basic channel 1 to 16, "Tx = Rx"), page 35 (section 2.1, "Recognized channels are as follows: … OMNI ON mode: all channels" for voice messages, "basic channel only" for mode messages). That mode messages and system exclusive are also taken on every channel is a departure, listed in section 15.1. The channel map is the architecture's rule for a one-part family (MIDI-67, MIDI-68): all 16 channels map to the one part.
- Verification: A test plays one score sixteen times, each on a different channel, and once with its messages spread over all sixteen, and checks that every run's samples are identical; a second test sends the same exclusive patch message with channel bytes `00` and `0F` and checks the panel is the same after each.

## 4. Notes and keys

**S106-3. Note on.** On a note on (status `0x9n`) whose velocity (data byte 2) is 1 to 127, the instrument MUST take the key (data byte 1, 0 to 127) as pressed, under the rules of S106-5 and section 13. The velocity MUST NOT change the sound in any way.
- Reason: The Juno-106 recognises "Note ON, kkkkkkk = 0 – 127 (24 – 108), vvvvvvv = 1 – 127, velocity ignored". The Juno-60's keyboard has no velocity.
- Source: Juno-106 manual, page 35, section 2.1; page 34 (velocity, note on: not recognised). The JU-06A recognises velocity (JU-06A chart, page 1, "Velocity Note On: o"), but what it does with it is not stated in the source; synth106 and synth60 follow the instruments modelled (section 15.3).
- Verification: A test plays the same note at velocities 1, 64 and 127 and checks that the samples are identical.

**S106-4. Note off.** On a note off (status `0x8n`, any release velocity), and on a note on whose velocity is 0, the instrument MUST take the key as released. The release velocity MUST NOT change the sound.
- Reason: The Juno-106 recognises "1000 nnnn 0kkk kkkk 0vvv vvvv Note OFF, velocity ignored" and "1001 nnnn 0kkk kkkk 0000 0000 Note OFF".
- Source: Juno-106 manual, page 35, section 2.1; page 34 (velocity, note off: not recognised). The same rule holds in every synthesizer (`midi-architecture.md`, MIDI-88).
- Verification: A test checks that a note on of velocity 0, a note off of release velocity 0 and a note off of release velocity 127 each release a held note at the same sample, giving identical output.

**S106-5. Keys outside the instrument's range.** A key below 24 MUST sound as the key raised by the fewest whole octaves that bring it to 24 or above; a key above 108 MUST sound as the key lowered by the fewest whole octaves that bring it to 108 or below. Keys 24 to 108 sound as themselves. The key's identity for note off and for voice assignment is the key received, not the key sounded: a note off of key 12 releases the voice that key 12 started.
- Reason: The Juno-106 receives note numbers 0 to 127, but its true voice is 24 to 108, and "If the data sent exceeds this range, it will be automatically transposed up or down to fit in the range". By how much it transposes is not stated in the source; by whole octaves keeps the note's name, which is the only transposition that fits the word "transposed" as the same manual uses it for its Key Transpose ("shifted one octave up or down", page 29). synth60 has no MIDI; the Juno-60's keyboard also sounds seven octaves (Juno-60 manual, page 18), and it is given the same rule.
- Source: Juno-106 manual, page 34 (note number recognised 0 to 127, "True voice 24-108"), page 29 ("Sound Range", paragraph 2). The octave rule is NeoTeletext's reading (section 16 item 5).
- Verification: A test plays keys 0, 11, 12, 23, 24, 108, 109, 120 and 127 with range 8′ and checks that they sound as keys 24, 35, 24, 35, 24, 108, 97, 108 and 103 respectively, each within 1 cent; and checks that a note off of key 12 releases the voice key 12 started while a held key 24 keeps sounding.

**S106-6. Short notes.** A note whose note off arrives less than 5 milliseconds after its note on MUST be played, as any other note is: its note on starts a voice and its note off releases it.
- Reason: The Juno-106 chart remarks that "The Note Number message that gives less than 5 ms from Note ON to Note OFF cannot be received". That is a limit of the hardware's processor, not a behaviour a sound needs; a score that relies on it is not foreseeable, and dropping notes would make a stored sound depend on its timing to a tenth of a millisecond.
- Source: Juno-106 manual, page 34 (remark on note number). Listed as left out in section 15.1.
- Verification: A test plays a note on and its note off 1 millisecond apart and checks that a voice sounded.

## 5. Bender, modulation and hold

**S106-7. Pitch bender.** On a pitch bend (status `0xEn`, data byte 1 the least significant byte, data byte 2 the most significant), the instrument MUST form the 14-bit number `bend = data byte 2 × 128 + data byte 1`, 0 to 16,383, whose centre is 8,192, using all 14 bits. It MUST move the pitch of every voice by `(bend − 8,192) ÷ 8,192` of the bend range, where the bend range is the setting of S106-26 (two semitones until that setting is moved). Data byte 2 = 64 with data byte 1 = 0 is no bend; 0 and 0 is the full range down; 127 and 127 is 8,191 ÷ 8,192 of the range up. The bender MUST NOT move the filter's cutoff.
- Reason: The architecture's common rule for every synthesizer (`midi-architecture.md`, MIDI-91): a program's bend then glides alike on every synthesizer. The Juno-106 recognises "1110 nnnn 0b00 0000 0bbb bbbb Pitch Bender, LS 6 bits are ignored": seven bits of the most significant byte and the top bit of the least significant byte, an 8-bit bend. That reading is a departure under MIDI-91, listed in section 15.4. The Juno-106 transmits "MAX (high) MSB 127 LSB 96; CENTER 64, 0; MIN (low) 0, 0"; such a bend is read here as its 14 bits say. How far the bender bends is the receiver's: "Sensitivity of the pitch bender and modulation can be adjusted by receiver", by the DCO and VCF bend sensitivity knobs beside the keyboard (page 23), which are not part of a patch. synth106 and synth60 have no bender on the filter today (`mod.rs`), and nothing in the adopted interfaces asks for one in a message.
- Source: `midi-architecture.md`, MIDI-91 (MIDI 1.0 4.2, printed page 19, PDF 51, and Table II, PDF 101, for the 14-bit form). Juno-106 manual, page 35, sections 1.2 and 2.2 and the note under 2.2; page 23 ("DCO Bend Sens Knob … (Max. ±1 octave)", "VCF Bend Sens Knob"). The bend range: S106-26.
- Verification: A test holds a note and sends pitch bends (data byte 1, data byte 2) of (0, 0), (0, 64), (1, 64), (0, 96), (127, 127), and checks the pitch against −200, 0, +0.0244, +100 and +199.9756 cents (the first, second, fourth and fifth within 0.01 cent, and the third as a pitch above the second's), with the range at two semitones.

**S106-8. Modulation, controller 1.** On a control change of controller 1, the instrument MUST set the depth of the low-frequency oscillator's vibrato to `value ÷ 127` of the vibrato's full depth, linearly: value 0 adds no vibrato, value 127 the full depth. The full depth is ±50 cents. This vibrato is separate from the patch's DCO LFO slider (parameter 2) and adds to it.
- Reason: The Juno-106 recognises "1011 nnnn 0000 0001 0vvv vvvv LFO Modulation, v = 0 (min) --> 127 (max)", and its manual describes the lever: "While this lever is being pushed back, vibrato effect by LFO is obtained", at a depth set by the LFO knob beside the keyboard ("This knob controls the depth of the vibrato effect"), which is not part of a patch. The JU-06A recognises controller 1 as "MODULATION". The full depth is the receiver's; synth106 and synth60 keep what is built.
- Source: Juno-106 manual, page 35, section 2.2; page 21 (③ "Bender Lever", ④ "LFO Modulation Depth Knob"); page 23 (⑦). JU-06A chart, page 1, controller 1. The depth: synth106's source, `mod.rs`, `WHEEL_CENTS` (own choice). The linear curve is NeoTeletext's (section 16 item 6).
- Verification: A test sets the DCO LFO slider to 0, holds a note, and measures the pitch's swing at values 0, 32, 64, 96 and 127 against 0, 12.6, 25.2, 37.8 and 50 cents either way, each within 0.5 cent.

**S106-9. Hold, controller 64.** On a control change of controller 64, synth106 and synth60 MUST each take values 0 to 63 as hold off and 64 to 127 as hold on. While hold is on, a key that is released keeps its voice sounding as a held key's does; when hold goes off, every voice whose key is up is released.
- Reason: The architecture's common rule for every synthesizer (`midi-architecture.md`, MIDI-87): one threshold, so a performance's pedal means the same on each. The Juno-106 recognises "1011 nnnn 0100 0000 0000 0000 hold OFF" and "0vvv vvvv hold ON vvvvvvv = 1 – 127"; its hold on at 1 to 127 is a departure under MIDI-87, listed in section 15.4. synth60's hold is a switch at a jack (Juno-60 manual, page 21, "PEDAL HOLD"), and no Roland document says how it would read controller 64; the JU-06A recognises controller 64 as "HOLD" but gives no band. What is built takes the common rule for synth60 and the Juno-106's for synth106 (`mod.rs`, `PEDAL_DOWN_106`, `PEDAL_DOWN_60`); synth106 changes (section 18).
- Source: `midi-architecture.md`, MIDI-87 (MIDI 1.0 4.2, printed page 12, PDF 44: a switch is "OFF" at 0 to 63 and "ON" at 64 to 127). Juno-106 manual, page 35, section 2.1. JU-06A chart, page 1, controller 64.
- Verification: A test sends values 0, 1, 63, 64 and 127 to each instrument and checks the hold's state after each (off, off, off, on, on); a test holds a key, sends controller 64 at value 64, releases the key, and checks the voice still sounds on both; then sends value 0 and checks it is released on both.

## 6. Program change and patch memory

The Juno-106 holds 128 patches in two groups, A and B, each of eight banks of eight patches, named by group, bank and patch number: A-11 to A-88 and B-11 to B-88 (Juno-106 manual, pages 6 and 27). The Juno-60 holds 56 patches in banks 1 to 7 of patches 1 to 8, numbered 11 to 78 (Juno-60 manual, page 6). The JU-06A recognises program changes 0 to 63 (JU-06A chart, page 1).

**S106-10. Program change.** On a program change (status `0xCn`, one data byte p, 0 to 127), the instrument MUST set its panel to patch p of the sound's bank, as if that patch's exclusive message (section 7, and for synth60 its three controller values, section 12) had arrived at that instant. The bender, the modulation, hold, controller 7's volume, the bend range, and the keys held are left as they are. If the bank holds no patch p, the instrument MUST set its panel to its default patch (S106-21) and count the program change as ignored. Until a first program change arrives the panel is patch 0 of the bank, or the default patch if the bank lacks patch 0 or it was refused (MIDI-61; every sound names at least one bank, MIDI-57).
- Reason: The Juno-106 recognises "1100 nnnn 0ppp pppp Program Change, 0 – 63 : Group-A 11 – 88, 64-127 : Group-B 11 – 88". A program change recalls a whole patch and leaves the bender, the lever and the hold, which are not part of a patch.
- Source: Juno-106 manual, page 35, section 2.2; page 34 (program change recognised, true number 0 to 127); page 27 (the tables of groups A and B). That patch 0 plays before a first program change is what is built, and is the architecture's rule (MIDI-61). The architecture's mapping (MIDI-59): the Juno-106 has no bank select, so a program change p always chooses program p of bank index 0, the first bank the sound names; controllers 0 and 32 are counted as ignored (MIDI-64, S106-25), and a sound of this family that names further banks cannot reach them. A missing or refused patch is the default and is counted (MIDI-59, MIDI-63). A program change to the program already chosen, with the panel unmoved since, MUST change nothing audible (MIDI-97).
- Verification: A test builds a bank of 128 different patches, sends program changes 0, 7, 8, 63, 64 and 127, and checks the panel after each equals the patch of that number; sends a program change beyond a bank of 4 patches and checks the default patch and the count; and checks that a held note, the bender, controller 1 and hold are unchanged by a program change.

**S106-11. Program numbers as the Juno-106 names them.** A program number p MUST correspond to the Juno-106's patch name thus: group A if p is 0 to 63 and group B if p is 64 to 127; bank `((p mod 64) ÷ 8, rounded down) + 1`; patch `(p mod 8) + 1`. So 0 is A-11, 7 is A-18, 8 is A-21, 63 is A-88, 64 is B-11 and 127 is B-88. A tool that shows a synth106 or synth60 patch number to a person SHOULD show it in this form.
- Reason: It is the Juno-106's own numbering, and every published Juno-106 patch is named by it. One numbering serves both instruments; the Juno-60's own numbers 11 to 78 are the first 56 of group A's, A-11 to A-78, and a bank of synth60 patches taken from a Juno-60 places its patch "23" at program 10.
- Source: Juno-106 manual, page 27, the "GROUP A" and "GROUP B" tables and the note "MIDI Format "0" to "127" are assigned to the Patch programs of Group A-11 to Group B-88". Juno-60 manual, page 6. That the Juno-60's numbers are placed as group A's is NeoTeletext's (section 16 item 8).
- Verification: A test checks the formula against all 128 cells of the two tables of page 27.

**S106-12. The bank holds up to 128 patches.** A bank of synth106 or synth60 patches MUST hold 1 to 128 patches, numbered from 0 in the bank's order, and a program change MUST reach every one of them. The bank's storage is the architecture document's (MIDI-55, MIDI-56); what it needs from this document is in S106-38 and S106-39.
- Reason: The Juno-106 holds 128 patches and recognises program changes 0 to 127. synth60 is given the same so that one bank form and one rule serve both, though the Juno-60 holds 56 and the JU-06A recognises 0 to 63.
- Source: Juno-106 manual, pages 6, 27 and 34. Today a bank holds 1 to 32 (section 18).
- Verification: The test of S106-10, with a bank of 128.

## 7. The system exclusive messages

The Juno-106 manual (page 35, section 3) gives three exclusive messages. The letters a to g name the bytes as the manual does. All three begin with `F0` (exclusive), `41` (Roland's identifier), a function type, and `0n` (the MIDI channel less one), and end with `F7` (EOX). They are recognised only with the MIDI function switch at III (section 2.3), which S106-1 makes always so.

**S106-13. Patch change, function type `30`.** The instrument MUST recognise this message of exactly 24 bytes:

| Byte | Bits | Hexadecimal | The manual's description | What the instrument does with it |
|---|---|---|---|---|
| a | `1111 0000` | `F0` | Exclusive | Start of the message. |
| b | `0100 0001` | `41` | Roland ID # | Must be `41`. |
| c | `0011 0000` | `30` | function type | Must be `30`. |
| d | `0000 nnnn` | `0N` | N+1 = MIDI channel, N = 0 – 15 | Must have its top four bits 0; the channel is otherwise not used (S106-2). |
| e | `0xxx xxxx` | 0 to 127 | Program number 0 – 127 | Not used by the receiver (S106-16). A sender writes the patch's number (S106-11). |
| f, 1st | `0zzz zzzz` | 0 to 127 | value: parameter 0 | LFO rate |
| f, 2nd | `0zzz zzzz` | 0 to 127 | value: parameter 1 | LFO delay |
| f, 3rd | `0zzz zzzz` | 0 to 127 | value: parameter 2 | DCO LFO |
| f, 4th | `0zzz zzzz` | 0 to 127 | value: parameter 3 | DCO PWM |
| f, 5th | `0zzz zzzz` | 0 to 127 | value: parameter 4 | noise level |
| f, 6th | `0zzz zzzz` | 0 to 127 | value: parameter 5 | VCF cutoff |
| f, 7th | `0zzz zzzz` | 0 to 127 | value: parameter 6 | resonance |
| f, 8th | `0zzz zzzz` | 0 to 127 | value: parameter 7 | VCF ENV |
| f, 9th | `0zzz zzzz` | 0 to 127 | value: parameter 8 | VCF LFO |
| f, 10th | `0zzz zzzz` | 0 to 127 | value: parameter 9 | VCF KYBD |
| f, 11th | `0zzz zzzz` | 0 to 127 | value: parameter 10 | VCA level |
| f, 12th | `0zzz zzzz` | 0 to 127 | value: parameter 11 | attack |
| f, 13th | `0zzz zzzz` | 0 to 127 | value: parameter 12 | decay |
| f, 14th | `0zzz zzzz` | 0 to 127 | value: parameter 13 | sustain |
| f, 15th | `0zzz zzzz` | 0 to 127 | value: parameter 14 | release |
| f, 16th | `0zzz zzzz` | 0 to 127 | value: parameter 15 | sub level |
| f, 17th | `0zzz zzzz` | see S106-18 | value: parameter 16 | the first switch byte |
| f, 18th | `0zzz zzzz` | see S106-18 | value: parameter 17 | the second switch byte |
| g | `1111 0111` | `F7` | EOX | End of the message. |

On receiving it, the instrument MUST set its panel to the 18 values at that instant, as one change. On synth60 it MUST also set the three synth60 settings as S106-32 says. It MUST NOT change the bank, and MUST NOT change which program number a later program change is counted from.
- Reason: It is the message a Juno-106 sends "When Group, Bank or Patch number is changed", and the manual's note 5 says what a receiving Juno-106 does with it: "the master Juno can perfectly control the slave one. That is, Information of each parameter of the patch selected in the master Juno will be sent to the slave Juno by means of Exclussive Message. The Information here includes the setting of each control and switch. Here, the Patch Program number Information is not transmitted to the slave Juno, but its tone color will turn out exactly the same as the master Juno's" and "Changing patches in the master Juno does not alter the Program Number currently shown in the Display on the slave Juno, only dots will light indicating that Exclusive Message has been received."
- Source: Juno-106 manual, page 35, section 3.1 ("(18 bytes total for values)"); page 28 (note 5). The meaning of each value: section 3.4 (S106-17, S106-18).
- Verification: A test sends the manual's example of section 3.2 rewritten with function type `30` (S106-15's vector) and checks every field of the panel; checks the program number byte 0 and 127 give the same panel; and checks that a program change sent afterwards still recalls the bank's patch, unchanged.

**S106-14. Manual mode, function type `31`.** The instrument MUST recognise this message of exactly 24 bytes, byte for byte as S106-13's table except: byte c is `31`, and byte e is `00`, which the manual describes as "Number indicates "Manual"". On receiving it, the instrument MUST do exactly what S106-13 says.
- Reason: It is the message a Juno-106 sends "When Manual Button is pressed": the panel's controls as they physically stand, "(18 bytes total for values)". To a receiver it is the same panel in the same form. Pressing Manual on a Juno-106 makes the sound follow the panel (page 8, "Depress the Manual Button, then synthesize your own sound"); a receiver has no physical panel, so the 18 values are its panel.
- Source: Juno-106 manual, page 35, section 3.2.
- Verification: A test sends the manual's own example of section 3.2 and checks the panel against S106-15's decoding; a test sends it with byte e other than `00` and checks it is ignored and counted (S106-19).

**S106-15. The manual's examples are test vectors.** The examples printed under sections 3.1, 3.2 and 3.3 MUST be decoded by the instrument as follows, and these decodings MUST be among its tests.
1. Section 3.2's example, `F0 41 31 00 00 03 00 00 00 00 3F 3C 00 00 7F 45 00 00 7F 00 00 2A 19 F7`: LFO rate 3, LFO delay 0, DCO LFO 0, DCO PWM 0, noise 0, VCF cutoff 63, resonance 60, VCF ENV 0, VCF LFO 0, VCF KYBD 127, VCA level 69, attack 0, decay 0, sustain 127, release 0, sub level 0; first switch byte `2A` (`010 1010`): range 8′, pulse on, sawtooth off, chorus off; second switch byte `19` (`001 1001`): pulse width manual, envelope positive, amplifier by envelope, high-pass filter at position 0.
2. Section 3.1's example, `F0 41 30 00 00 39 2D 00 37 00 55 00 00 00 19 34 3B 2D 56 28 00 1A 18 F7`, as read from the scan: LFO rate 57, LFO delay 45, DCO LFO 0, DCO PWM 55, noise 0, VCF cutoff 85, resonance 0, VCF ENV 0, VCF LFO 0, VCF KYBD 25, VCA level 52, attack 59, decay 45, sustain 86, release 40, sub level 0; first switch byte `1A` (`001 1010`): range 8′, pulse on, sawtooth on, chorus on, chorus II; second switch byte `18` (`001 1000`): pulse width by LFO, envelope positive, amplifier by envelope, high-pass filter at position 0. The scan is of a dot-matrix print; the digits read as `19`, `3B` and `2D` in the second line could be `1B`, `38` and `20`. The test MUST use the bytes as printed here and say so; it checks the decoding, not the patch's provenance.
3. Section 3.3's example, `F0 41 32 00 03 04 F7`: DCO PWM (parameter 3) set to 4, every other field unchanged.
- Reason: They are the only byte sequences Roland printed, and they fix the order of the bytes and the sense of the bits.
- Source: Juno-106 manual, page 35, the three "Example" blocks, read at 600 dots an inch.
- Verification: The three decodings are the test.

**S106-16. The program number byte.** In a received function type `30` message the instrument MUST NOT act on byte e. A sender (the server, which writes every message a block or a bank carries, DEC-6462) MUST write in it the number, 0 to 127, of the patch the message holds in its bank, or 0 when the patch is in no bank.
- Reason: A receiving Juno-106 does not change its program number (S106-13's reason). A sender writes the number so that a message taken out of a bank still says where it came from, as a Juno-106's own messages do.
- Source: Juno-106 manual, page 35, section 3.1 ("Program number 0 – 127"); page 28 (note 5). What a sender writes when the patch is in no bank is NeoTeletext's (section 16 item 9).
- Verification: The test of S106-13 (byte e 0 and 127 give the same panel); a server test checks that a bank's patch k is emitted with byte e = k.

**S106-17. Control change of one parameter, function type `32`.** The instrument MUST recognise this message of exactly 7 bytes:

| Byte | Bits | Hexadecimal | The manual's description | What the instrument does with it |
|---|---|---|---|---|
| a | `1111 0000` | `F0` | Exclusive | Start of the message. |
| b | `0100 0001` | `41` | Roland ID | Must be `41`. |
| c | `0011 0010` | `32` | function type | Must be `32`. |
| d | `0000 nnnn` | `0N` | N+1 = MIDI channel, N = 0 – 15 | Must have its top four bits 0; the channel is otherwise not used (S106-2). |
| e | `0yyy yyyy` | 0 to 17 | parameter number 0 – 17 | Which value to set: the table below. |
| f | `0zzz zzzz` | 0 to 127 | value 0 – 127 | The new value. |
| g | `1111 0111` | `F7` | EOX | End of the message. |

On receiving it, the instrument MUST set the one value that byte e names to byte f, at that instant, and leave every other value as it is. On synth60, a message for parameter 16 or 17 also sets the three synth60 settings as S106-32 says. The parameter numbers are the manual's section 3.4:

| Parameter number | The manual's name ("for potentiometers") | The panel control (Juno-106 manual) |
|---|---|---|
| 0 | LFO rate | LFO RATE knob (page 21, ①) |
| 1 | LFO delay | LFO DELAY TIME knob (page 21, ②) |
| 2 | DCO LFO | DCO LFO modulation knob (page 16, ⑤) |
| 3 | DCO PWM | DCO pulse width modulation knob (page 16, ③) |
| 4 | noise level | DCO NOISE level knob (page 16, ⑥) |
| 5 | VCF cutoff | VCF FREQ, cutoff frequency knob (page 18, ②) |
| 6 | resonance | VCF RES, resonance knob (page 18, ③) |
| 7 | VCF ENV | VCF ENV, envelope modulation knob (page 18, ④) |
| 8 | VCF LFO | VCF LFO modulation knob (page 18, ⑥) |
| 9 | VCF KYBD | VCF KYBD, key follow knob (page 18, ⑦) |
| 10 | VCA level | VCA LEVEL knob (page 20, ②) |
| 11 | attack | ENV A, attack time knob (page 20, ③) |
| 12 | decay | ENV D, decay time knob (page 20, ④) |
| 13 | sustain | ENV S, sustain level knob (page 20, ⑤) |
| 14 | release | ENV R, release time knob (page 20, ⑥) |
| 15 | sub level | DCO SUB, sub oscillator level knob (page 16, ④) |
| 16 | (switches) | The first switch byte: S106-18 |
| 17 | (switches) | The second switch byte: S106-18 |

- Reason: It is the message a Juno-106 sends "When volume controllers or switches are changed", and "if any of the controls or switches under a red belt of the master Juno is moved even slightly, corresponding parameter Information is transmitted to the slave Juno, by means of Exclusive Message, therefore the slave Juno is perfectly controlled by it, regardless of its own panel setting" (page 28). It is the Juno-106's own way of moving one control.
- Source: Juno-106 manual, page 35, sections 3.3 and 3.4; page 28 (note 5). The panel controls: pages 16, 18, 20 and 21. The correspondence table numbers the same sixteen sliders 1, 2, 4, 5, 10, 12, 13, 14 or 15, 16, 17, 19, 20, 21, 22, 23 and 9 in its "Controller Map".
- Verification: A test sends, for each parameter number 0 to 15, the message with value 0, 64 and 127, and checks that exactly that slider changes and no other value; and for 16 and 17 checks each bit of S106-18.

**S106-18. The two switch bytes, bit by bit.** The first switch byte (parameter 16) and the second (parameter 17) MUST be read as follows. Bit 0 is the least significant bit.

*Parameter 16, the first switch byte:*

| Bit | Function | Value 1 | Value 0 |
|---|---|---|---|
| 6 | chorus | I | II (the manual prints "2") |
| 5 | chorus | off | on |
| 4 | saw | on | off |
| 3 | pulse | on | off |
| 2, 1, 0 | range | `100` 4′; `010` 8′; `001` 16′ | (see below) |

Bits 6 and 5 together: `x1` (bit 5 set, whatever bit 6) is chorus off; `10` is chorus I; `00` is chorus II. Bits 2 to 0 MUST be exactly one of `001`, `010` and `100`. Bit 7 is 0, as in every data byte.

*Parameter 17, the second switch byte:*

| Bit | Function | Value 1 | Value 0 |
|---|---|---|---|
| 6 | (none) | — | always 0 |
| 5 | (none) | — | always 0 |
| 4, 3 | HP filter | `11` the manual's "off"; `10` 1; `01` 2; `00` 3 | (see the first column) |
| 2 | VCA | gate | ENV |
| 1 | ENV | − (envelope inverted) | + |
| 0 | PWM | MAN | LFO |

The high-pass filter's two bits are three less the panel switch's position, 0 to 3: `11` is position 0, `10` position 1, `01` position 2, `00` position 3. Bits 6 and 5 MUST be 0.
- Reason: It is the manual's table "for switches". The manual calls the high-pass filter's `11` "off"; on the Juno-106's panel that position is the lowest, 0, at which "lower frequencies are boosted", and position 1 is the one at which "the DCO output passes the filter unprocessed" (page 18). What is built reads `11` as position 0, the panel's lowest, from the module board schematic's table of the high-pass switch against modes 0 to 3 (`patch.rs`, `HPF_SHIFT`).
- Source: Juno-106 manual, page 35, section 3.4, "for switches"; page 18 (the high-pass filter's positions). That a range other than exactly one bit, or a set bit 5 or 6 of parameter 17, is refused is S106-19.
- Verification: A test sends parameter 16 with each of the 3 ranges and each of the 8 combinations of bits 3 to 5 with bit 6 at 0 and 1, and parameter 17 with each of its 32 values with bits 5 and 6 at 0, and checks each field; the decodings of S106-15 also cover these bits.

**S106-19. Messages that are not these three, and malformed ones.** A system exclusive message MUST be counted as ignored, and MUST change nothing, if any of these holds: its byte b is not `41`; its byte c is not `30`, `31` or `32`; it is not exactly 24 bytes long (function types `30` and `31`) or exactly 7 bytes long (`32`), counting `F0` and `F7`; its byte d has a bit set above bit 3; in a function type `31` message byte e is not `00`; in a function type `32` message byte e is above 17; in a message of function type `30` or `31` the first switch byte's bits 2 to 0 are not exactly one of `001`, `010` and `100`, or the second switch byte has bit 5 or bit 6 set; in a function type `32` message for parameter 16 or 17 the same holds of byte f. A message that is refused is refused whole: no value of it is applied.
- Reason: Roland's identifier `41` is shared by every Roland instrument, and other Roland instruments use other function types and lengths; only a message that is exactly one of the three is a Juno-106 message. A switch byte that names no range, or two, has no meaning in the manual, and what a Juno-106 did with one is not stated in the source; refusing it whole is what is built (`Patch::from_bytes`, `PatchError::Range`, `PatchError::Switches`) and keeps the panel definite.
- Source: Juno-106 manual, page 35, sections 3.1 to 3.4. The refusal rules are NeoTeletext's (section 16 item 10).
- Verification: A test sends each of the malformed forms named (a wrong identifier, function type `33`, lengths 23, 25, 6 and 8, channel byte `10`, a `31` with byte e `01`, a `32` with byte e 18, range bits `000`, `011` and `111`, the second switch byte `20` and `40`) and checks the panel is unchanged and each is counted.

**S106-20. Exclusive messages in a block.** Each of the three messages MUST be carried in a block as one system exclusive event of Standard MIDI File form (decision A3): the byte `F0`, the length of the rest as a variable-length quantity (23 for function types `30` and `31`, 6 for `32`), then the bytes from b to g. A message takes effect at the event's time, in order with the block's other events.
- Reason: Decision A3 and the architecture's system exclusive event (MIDI-27). These messages are short, 24 and 7 bytes, well within the architecture's 256 bytes after `F0` (MIDI-28): none needs to travel in a bank object as a message longer than an event does (MIDI-50, MIDI-51).
- Source: Decision A3; `midi-architecture.md`, MIDI-27, MIDI-28 (Standard MIDI Files 1.0, printed pages 6 and 7, PDF 135 and 136, for the event's form, `F0`, the length as a variable-length quantity, and the bytes after `F0` ending with `F7`); Juno-106 manual, page 35 (the lengths).
- Verification: A test puts a function type `30` message and a note on at the same tick, in that order, and checks the note sounds with the new patch; and in the other order, with the old.

## 8. The default patch

**S106-21. The default patch.** An instrument that has been given no patch, and an instrument whose patch is missing (S106-10) or refused, MUST stand at this patch. synth106: the 18 values `00 00 00 00 00 7F 00 00 00 00 40 00 00 7F 00 00 32 11`, that is every slider 0 but VCF cutoff 127, VCA level 64 and sustain 127; range 8′, sawtooth on, pulse off, chorus off; pulse width manual, envelope positive, amplifier by envelope, high-pass filter at position 1. synth60: the 18 values `00 00 00 00 00 7F 00 00 00 00 40 00 00 7F 00 00 32 19` (the same, but the high-pass filter at position 0), with the three synth60 settings pulse width manual, sub-oscillator on and chorus off (controller values 43, 64 and 0 by section 10).
- Reason: An instrument must sound something definite before a patch arrives. This is the default built today: one sawtooth at 8′ through an open filter. The high-pass position differs because the two instruments' positions differ: on synth106 position 1 is flat, and on synth60 position 0 is flat (`Patch::default_for`; Juno-60 manual, page 14: "In its lowest position, the DCO output passes the filter unchanged").
- Source: synth106's source, `patch.rs`, `Patch::DEFAULT` and `Patch::default_for` (own choice). It is the family's default patch that the architecture asks each family document to state value by value (MIDI-61, MIDI-63).
- Verification: A test checks that a new synth106 and a new synth60 each have the panel above, field by field, and that the bytes above decode to it.

## 9. The interface parameters and the patch fields

This section is the complete mapping between the adopted interfaces' parameters and the fields of `Patch` in `patch.rs`. The JU-06A controller of each is given here for reference; section 10 specifies the controllers.

**S106-22. The mapping.** Every value of the 18 and every one of the three synth60 settings MUST set exactly the field of the patch that this table names, and no other.

| Parameter | The Juno-106 manual's name | Patch field (`patch.rs`) | Values | JU-06A controller |
|---|---|---|---|---|
| 0 | LFO rate | `Slider::LfoRate` | 0 to 127 | 3, LFO RATE |
| 1 | LFO delay | `Slider::LfoDelay` | 0 to 127 | 9, LFO DELAY |
| 2 | DCO LFO | `Slider::DcoLfo` | 0 to 127 | 13, DCO LFO |
| 3 | DCO PWM | `Slider::DcoPwm` | 0 to 127 | 14, DCO PWM |
| 4 | noise level | `Slider::Noise` | 0 to 127 | 19, DCO NOISE |
| 5 | VCF cutoff | `Slider::VcfFrequency` | 0 to 127 | 74, VCF FREQ |
| 6 | resonance | `Slider::VcfResonance` | 0 to 127 | 71, VCF RES |
| 7 | VCF ENV | `Slider::VcfEnvelope` | 0 to 127 | 22, VCF ENV |
| 8 | VCF LFO | `Slider::VcfLfo` | 0 to 127 | 23, VCF LFO |
| 9 | VCF KYBD | `Slider::VcfKeyboard` | 0 to 127 | 24, VCF KYBD |
| 10 | VCA level | `Slider::VcaLevel` | 0 to 127 | 26, VCA LEVEL |
| 11 | attack | `Slider::Attack` | 0 to 127 | 73, ENV A |
| 12 | decay | `Slider::Decay` | 0 to 127 | 75, ENV D |
| 13 | sustain | `Slider::Sustain` | 0 to 127 | 27, ENV S |
| 14 | release | `Slider::Release` | 0 to 127 | 72, ENV R |
| 15 | sub level | `Slider::Sub` | 0 to 127 | 18, DCO SUB |
| 16, bits 2 to 0 | range | `range`: `Range::Sixteen`, `Eight`, `Four` | 16′, 8′, 4′ | 12, DCO RANGE |
| 16, bit 3 | pulse | `pulse` | off, on | 16, DCO SQR SW |
| 16, bit 4 | saw | `sawtooth` | off, on | 17, DCO SAW SW |
| 16, bits 5 and 6 | chorus | `chorus`: `ChorusMode::Off`, `One`, `Two` | off, I, II | 93, CHORUS OFF / I / II / I+II |
| 17, bit 0 | PWM | `pwm`: `PwmSource::Lfo`, `Manual` | LFO, MAN | 15, DCO LFO/MAN/ENV |
| 17, bit 1 | ENV (polarity) | `envelope_inverted` | + is false, − is true | 21, VCF ENV Polarity |
| 17, bit 2 | VCA | `vca_gate` | ENV is false, gate is true | 25, VCA ENV / GATE |
| 17, bits 4 and 3 | HP filter | `hpf` | 0 to 3 | 20, HPF FREQ |
| synth60 setting | PWM source ENV | `pwm`: `PwmSource::Envelope` | — | 15, DCO LFO/MAN/ENV |
| synth60 setting | sub-oscillator switch | `sub` | off, on | 28, DCO SUB SW |
| synth60 setting | chorus I+II | `chorus`: `ChorusMode::Both` | — | 93, CHORUS OFF / I / II / I+II |

On synth60 the range field is the Juno-60's OCTAVE TRANSPOSE switch, which a Juno-60 patch memorises (Juno-60 manual, page 7: "The settings of the knobs (covered red) and the position of the OCTAVE TRANSPOSE switch are memorized as a patch program"): 16′ is DOWN, 8′ is NORMAL and 4′ is UP. The Juno-60 has no range buttons (its specifications, page 32, list none under DCO).
- Reason: Each field built today is one of these controls, so the mapping is one to one and loses nothing for synth106. The correspondence table confirms that these are the whole of a Juno-106 sound: its 25 numbered controls are the sixteen sliders, the switches of the two bytes and the chorus buttons, and nothing else.
- Source: Juno-106 manual, page 35, section 3.4. JU-06A chart, page 1. Correspondence table, "Controller Map". synth106's source, `patch.rs`. Juno-60 manual, pages 7, 18 and 32. That range carries the octave transpose on synth60 is what is built (`voice.rs`, `divisor_60` and `range_octaves`) and is NeoTeletext's (section 16 item 4).
- Verification: The tests of S106-17 and S106-18 for the 18 values; the tests of S106-23 and section 10 for the three settings.

**What the adopted interfaces have that the patch lacks.** The following are controls of the instruments modelled, or of the JU-06A, that no field of `Patch` holds. Each is listed with what the instruments do instead; section 15 lists them as left out and open question 3 asks about the performance controls.
1. On the Juno-106, outside the patch (Juno-106 manual, pages 22 to 25 and 33): the VOLUME knob, the PORTAMENTO time knob and switch, the DCO and VCF bend sensitivity knobs, the LFO modulation depth knob beside the bender, the assign mode buttons Poly 1 and Poly 2, KEY TRANSPOSE, the rear TUNE knob (±50 cents). synth106 has a bend range set by controller 87 and registered parameter number 0 (S106-26) in place of the knob, no bend of the filter, a fixed vibrato depth (S106-8), Poly 1 only (section 13), no portamento and no transpose; controller 7 stands for the volume knob (S106-28).
2. On the Juno-60, in its patch (Juno-60 service notes, Table 6, column "MODE"; Juno-60 manual, page 17): the LFO TRIGGER MODE switch, AUTO or MANUAL. synth60's LFO behaves as AUTO always ("The oscillator's delay starts when a key goes down with no other held", `mod.rs`, citing the Juno-60 service notes, adjustment 7-4, "TRIG MODE to AUTO"); its LFO TRIGGER button, which MANUAL needs, is not modelled. Whether the JU-06A's controller 30, "LFO TRIG", is this switch is not stated in the source.
3. On the Juno-60, outside the patch: the arpeggio (MODE, RANGE, RATE, ON/OFF), HOLD, KEY TRANSPOSE, the bend sensitivity knobs, VOLUME (Juno-60 manual, pages 18 to 20, 32). None is modelled.
4. On the JU-06A, with no counterpart on either instrument modelled: LFO WAVE (controller 29), EXPRESSION PEDAL (11), the delay effect (82, 83, 89, 91), TEMPO SYNC (88), the clock and transport messages (section 10).

**What the patch has that the Juno-106's interface lacks.** The three synth60 settings (the `sub` switch, `PwmSource::Envelope`, `ChorusMode::Both`), which section 12 carries by the JU-06A's controllers. Every other field is one of the 18 values. The patch's `hpf` field is a `u8` that today accepts values above 3 and holds them to 3; by S106-18 and section 10 no message can set such a value, and S106-36 makes the server refuse one in a typed patch.

## 10. The JU-06A's controllers, sound-module mode

The JU-06A chart's first page, "SOUND MODULE", lists 39 controllers with a parameter name each and "o" (yes) or "x" (no) for transmitted and recognised. All 39 are recognised. The chart gives, for no controller, a range, a scaling or a value band, and for no switch the order of its positions beyond the order in which its name lists them.

**S106-23. Scaling of a slider's controller.** For each controller that the table of S106-25 marks "slider", the instrument MUST set the slider to the controller's value unchanged: value v, 0 to 127, sets the slider to v. The canonical value of a slider's setting is the setting itself.
- Reason: The slider's own values are 0 to 127 (Juno-106 manual, page 35), the same as a controller's, so the identity is the one mapping that loses nothing and lets a controller and the exclusive message of parameter n set the same value from the same number. The chart does not state a scaling.
- Source: Not stated in the JU-06A chart; NeoTeletext's own (section 16 item 1).
- Verification: A test checks, for each of the sixteen slider controllers, values 0, 1, 64, 126 and 127 against the slider, and that each sets the same slider as the exclusive message of S106-22's table.

**S106-24. Value bands of the switches.** For each controller that the table of S106-25 marks as a switch of n positions, the instrument MUST take the position `floor(value × n ÷ 128)`, numbered from 0 in the order the table gives. This gives these bands: for 2 positions, 0 to 63 and 64 to 127; for 3 positions, 0 to 42, 43 to 85 and 86 to 127; for 4 positions, 0 to 31, 32 to 63, 64 to 95 and 96 to 127. The canonical value of position p is the lowest of its band, `ceil(p × 128 ÷ n)`: for 2 positions 0 and 64; for 3 positions 0, 43 and 86; for 4 positions 0, 32, 64 and 96.
- Reason: Every value then selects a position, so no value is an error, the bands are as nearly equal as n positions in 128 values allow, and a switch of two positions is off below 64 and on from 64 as MIDI 1.0's switch controllers are (MIDI 1.0 4.2, printed page 12, PDF 44). The chart states none of this.
- Source: Not stated in the JU-06A chart; NeoTeletext's own (section 16 item 2). Open question 2.
- Verification: A test checks all 128 values of each switch controller against its bands, each band's two edges by name, and that each canonical value gives its position.

**S106-25. The controllers.** synth106 and synth60 MUST act on the control changes of the controllers in the table below as its "Effect" column says, on the instrument its "Applies to" column names. A controller marked "both" acts on both instruments. A controller marked "neither" is recognised by the JU-06A but moves nothing either instrument has, and MUST be counted as ignored by both, unless the owner's answer to open question 3 adds it. The "Patch field" column names the field each sets; a controller that sets a field moves the panel exactly as the exclusive message of the same parameter would.

| Controller | The chart's name | Applies to | Kind | Positions, in order (S106-24) | Effect: patch field, or what it does |
|---|---|---|---|---|---|
| 1 | MODULATION | both | performance | — | Vibrato depth: S106-8. |
| 3 | LFO RATE | both | slider | — | `Slider::LfoRate` (parameter 0) |
| 5 | PORTAMENTO TIME | neither | — | — | Counted as ignored. The Juno-106 has a portamento time knob outside its patch (Juno-106 manual, page 23); the Juno-60 has none ("A DCO does not, however, provide portament function", Juno-60 manual, page 12). Neither instrument has portamento today. Open question 3. |
| 9 | LFO DELAY | both | slider | — | `Slider::LfoDelay` (parameter 1) |
| 11 | EXPRESSION PEDAL | neither | — | — | Counted as ignored. Neither instrument modelled recognises it. Open question 3. |
| 12 | DCO RANGE | both | switch of 3 | 16′, 8′, 4′ | `range`. On synth60: DOWN, NORMAL, UP of OCTAVE TRANSPOSE. The order is the panel's, left to right (Juno-106 manual, page 16); the chart names no positions. |
| 13 | DCO LFO | both | slider | — | `Slider::DcoLfo` (parameter 2) |
| 14 | DCO PWM | both | slider | — | `Slider::DcoPwm` (parameter 3) |
| 15 | DCO LFO/MAN/ENV | both; ENV synth60 only | switch of 3 | LFO, MAN, ENV | `pwm`: `Lfo`, `Manual`, `Envelope`. On synth106, ENV is taken as MAN (S106-27). One of the three synth60 settings. |
| 16 | DCO SQR SW | both | switch of 2 | off, on | `pulse` (parameter 16, bit 3). The chart's "SQR" is the Juno-106's pulse wave, whose width is set by DCO PWM (Juno-106 manual, page 17). |
| 17 | DCO SAW SW | both | switch of 2 | off, on | `sawtooth` (parameter 16, bit 4) |
| 18 | DCO SUB | both | slider | — | `Slider::Sub` (parameter 15) |
| 19 | DCO NOISE | both | slider | — | `Slider::Noise` (parameter 4) |
| 20 | HPF FREQ | both | switch of 4 | 0, 1, 2, 3 | `hpf` (parameter 17, bits 4 and 3). The panel is marked 0 to 3 (Juno-106 manual, page 18). |
| 21 | VCF ENV Polarity | both | switch of 2 | +, − | `envelope_inverted` (parameter 17, bit 1). The order follows the exclusive bit, 0 for + and 1 for −. |
| 22 | VCF ENV | both | slider | — | `Slider::VcfEnvelope` (parameter 7) |
| 23 | VCF LFO | both | slider | — | `Slider::VcfLfo` (parameter 8) |
| 24 | VCF KYBD | both | slider | — | `Slider::VcfKeyboard` (parameter 9) |
| 25 | VCA ENV / GATE | both | switch of 2 | ENV, GATE | `vca_gate` (parameter 17, bit 2) |
| 26 | VCA LEVEL | both | slider | — | `Slider::VcaLevel` (parameter 10) |
| 27 | ENV S | both | slider | — | `Slider::Sustain` (parameter 13) |
| 28 | DCO SUB SW | synth60 | switch of 2 | off, on | `sub`. On synth106, counted as ignored (S106-27). One of the three synth60 settings. |
| 29 | LFO WAVE | neither | — | — | Counted as ignored. Neither instrument modelled has a choice of LFO waveform; how many positions the chart's control has is not stated. Open question 3. |
| 30 | LFO TRIG | neither | — | — | Counted as ignored. What it is (the Juno-60's TRIGGER MODE switch, or its TRIGGER button, or something else) is not stated in the source, and neither instrument has either today. Open question 3. |
| 64 | HOLD | both | performance | — | Hold: S106-9. |
| 65 | PORTAMENTO SW | neither | — | — | Counted as ignored, as controller 5. |
| 71 | VCF RES | both | slider | — | `Slider::VcfResonance` (parameter 6) |
| 72 | ENV R | both | slider | — | `Slider::Release` (parameter 14) |
| 73 | ENV A | both | slider | — | `Slider::Attack` (parameter 11) |
| 74 | VCF FREQ | both | slider | — | `Slider::VcfFrequency` (parameter 5) |
| 75 | ENV D | both | slider | — | `Slider::Decay` (parameter 12) |
| 82 | DELAY TIME | neither | — | — | Counted as ignored. A delay effect neither instrument modelled has. |
| 83 | DELAY FEEDBACK | neither | — | — | Counted as ignored, as 82. |
| 86 | POLY / (POLY) / SOLO / UNISON | neither today | — | — | Counted as ignored today. The assignment mode: section 13 and open question 3. |
| 87 | BEND RANGE | both | performance | — | The bend range: S106-26. |
| 88 | TEMPO SYNC | neither | — | — | Counted as ignored. It belongs to the delay effect. |
| 89 | DELAY SW | neither | — | — | Counted as ignored, as 82. |
| 91 | DELAY LEVEL | neither | — | — | Counted as ignored, as 82. |
| 93 | CHORUS OFF / I / II / I+II | both; I+II synth60 only | switch of 4 | OFF, I, II, I+II | `chorus`: `Off`, `One`, `Two`, `Both`. On synth106, I+II is taken as II (S106-27). One of the three synth60 settings. |

Every controller from 0 to 127 that this table, S106-26 (controllers 6, 38, 96, 97, 100 and 101 of the registered parameter number sequence), S106-28 and S106-29 do not name MUST be counted as ignored. Among them are bank select, controllers 0 and 32 (MIDI-64: the Juno-106 has no bank select), and the non-registered parameter number controllers 98 and 99 (neither adopted interface uses NRPN, MIDI-74).
- Reason: The JU-06A's map is Roland's own for knob-by-knob control of both instruments (DEC-6454), and the only one that covers the Juno-60's switches. Its controllers for the sixteen sliders and the switches of the two bytes move exactly the fields the exclusive messages move. Its controllers for things neither instrument has are named so that a score written for the JU-06A is understood, and so that the choice to add any of them is the owner's (open question 3).
- Source: JU-06A chart, page 1, every row of "Control Change". The positions' order: the chart's names, and for controller 12 the Juno-106 panel. The scalings and bands: S106-23 and S106-24 (NeoTeletext's own).
- Verification: A test sends, for each controller of the table, the canonical value of each position or the values 0, 64 and 127, and checks that exactly the named field changes and no other; and a test sends every controller from 0 to 127 not named and checks each is counted as ignored and changes nothing.

**S106-26. Bend range, controller 87 and registered parameter number 0.** The pitch bender's range MUST be set by either of two messages, the last received of either holding:
1. **Controller 87**, the JU-06A's: the range becomes `floor(value × 13 ÷ 128)` semitones either way: values 0 to 9 give 0 semitones, 10 to 19 one, 20 to 29 two, 30 to 39 three, 40 to 49 four, 50 to 59 five, 60 to 68 six, 69 to 78 seven, 79 to 88 eight, 89 to 98 nine, 99 to 108 ten, 109 to 118 eleven, and 119 to 127 twelve. The canonical value for n semitones is the lowest of its band, `ceil(n × 128 ÷ 13)`.
2. **Registered parameter number 0, pitch bend sensitivity** (`midi-architecture.md`, MIDI-90; MIDI 1.0 4.2, printed pages 17 and 18, PDF 49 and 50, and Tables III and IIIa, PDF 102 and 103): with the registered parameter selected by controller 101 at 0 and controller 100 at 0, data entry controller 6 sets the semitones and controller 38 the cents (0 to 99; a value of 100 to 127 is taken as 99), the range becoming the semitones plus the cents ÷ 100; increment (controller 96) and decrement (controller 97) move the range by one cent, as the architecture's MIDI-90 says for every synthesizer, MIDI 1.0 4.2 stating no step. A range above twelve semitones MUST be set to twelve semitones, the most this family's instruments have. Controllers 101 and 100 at 127 and 127 select no parameter (MIDI-76); with no parameter or with any registered parameter other than 0 selected, data entry, increment and decrement MUST be counted as ignored. After a lost block the selection MUST be none (MIDI-76, MIDI-102).

Until either message arrives the range is two semitones. The range is not part of a patch: a program change and the exclusive messages leave it as it is, and reset all controllers leaves it as it is (MIDI-84, S106-29).
- Reason: The JU-06A recognises "BEND RANGE". The Juno-106's range is a knob beside the keyboard of up to "±1 octave" (page 23), outside its patch, with no message; twelve semitones is that octave. Two semitones is what is built (`PITCH_BEND_SEMITONES`). The chart gives no scaling; thirteen near-equal bands give every whole semitone from none to an octave. Registered parameter number 0 is the architecture's rule for every synthesizer (MIDI-90), so that a program sets a bend range the same way on each; neither adopted interface documents it, so it is an addition, listed in section 16 item 3. The architecture's open question 5 asks the owner whether RPN 0 is to be added in every family; this item is pending the owner's answer to it.
- Source: JU-06A chart, page 1, controller 87. Juno-106 manual, page 23. `midi-architecture.md`, MIDI-76, MIDI-84 and MIDI-90, and its open question 5 (MIDI 1.0 4.2, printed pages 17 and 18, PDF 49 and 50, and Tables III and IIIa, PDF 102 and 103, for registered parameter number 0's number and data; the GM Developer Guidelines, page 6, PDF 315, for the null parameter number 127, 127). The scaling of controller 87: NeoTeletext's own (section 16 item 3).
- Verification: A test sends controller 87 at each band's two edges and checks the bend at full range; sets the range by RPN 0 to 1, 7 and 24 semitones and checks the bend at full range against 1, 7 and 12 semitones; sets 7 semitones by RPN 0 and then 87 at its canonical value for 3, and checks 3; checks the default of two semitones; and checks a program change and controller 121 leave the range.

**S106-27. synth60 settings sent to synth106.** On synth106, controller 15 in its ENV band MUST set `pwm` to `Manual`; controller 93 in its I+II band MUST set `chorus` to `Two`; controller 28 MUST be counted as ignored and leave `sub` on.
- Reason: The Juno-106 has none of the three; what is built takes ENV as manual and I+II as II ("A setting the model has not is taken as the nearest it has", `Synth106::set_patch`). The sub-oscillator switch has no nearest setting on the Juno-106, whose sub-oscillator is turned off by its level (parameter 15) alone; ignoring the controller keeps synth106's panel what a Juno-106's could be.
- Source: synth106's source, `mod.rs` (`chorus_mode`), `voice.rs` (`PwmSource::Envelope` on synth106 is manual). Juno-106 manual, pages 16 and 32 (no sub-oscillator switch). That controller 28 is ignored on synth106 is NeoTeletext's (section 16 item 11).
- Verification: A test sends the three controllers to synth106 at the synth60 positions and checks the fields, and that the output is identical to a run with ENV replaced by MAN, I+II by II and controller 28 left out.

## 11. Messages of NeoTeletext's common layer, and the mode messages

The architecture sets one rule for every synthesizer where MIDI defines a behaviour common to all instruments (`midi-architecture.md` section 11.1: reset all controllers, MIDI-84; all notes off, MIDI-85; all sound off, MIDI-86; the sustain pedal, MIDI-87; a note on of velocity 0, MIDI-88; the mode messages, MIDI-89; pitch bend range by registered parameter number 0, MIDI-90; pitch bend's 14 bits, MIDI-91; one volume law, MIDI-92). synth106 and synth60 follow every one of them: S106-4 (MIDI-88), S106-7 (MIDI-91), S106-9 (MIDI-87), S106-26 (MIDI-90), S106-28 (MIDI-82 and MIDI-92) and S106-29 (MIDI-84, MIDI-85, MIDI-86, MIDI-89). Where the Juno-106's or the JU-06A's interface differs, the common rule holds, and section 15.4 lists the departure with the requirement as its reason. Reset all controllers follows DEC-6464, which is recorded as proposed and awaits the owner's confirmation.

**S106-28. Volume, controller 7.** On a control change of controller 7, the instrument MUST set a gain on its output from the value, 0 (silent) to 127 (full), by the volume law that every NeoTeletext synthesizer shares (`midi-architecture.md`, MIDI-82 and MIDI-92: `(value × value) ÷ (127 × 127)` of full), moving to its new place by at most `1 ÷ 256` of full a sample, so over at most 256 output samples. Before any controller 7 arrives the value is 127. The gain is not part of a patch, and multiplies with the VCA level slider.
- Reason: Neither the Juno-106 nor the JU-06A recognises controller 7, but every NeoTeletext synthesizer takes it from the common layer (MIDI-9, MIDI-92), it stands for the Juno-106's VOLUME knob (page 23), which is outside its patch, and it is built today.
- Source: MIDI 1.0 for controller 7 (MIDI 1.0 4.2, Table III, PDF 102: "Channel Volume (formerly Main Volume)"); `midi-architecture.md`, MIDI-9, MIDI-82 and MIDI-92, for the shared law; synth106's source, `mod.rs` (`CONTROL_VOLUME`, `VolumeGain`). Juno-106 manual, page 34 (controllers recognised: 1 and 64 only). An addition, listed in section 16 item 12.
- Verification: The tests of controller 7 that exist today continue to pass.

**S106-29. All sound off, reset all controllers, all notes off and the mode messages.** The instrument MUST act on these control changes:
1. Controller 120, all sound off, whatever its value: every voice, held, holding and releasing alike, is brought to silence within 1,024 samples (21.3 milliseconds) by a fade that passes the engine's click measure (MIDI-83), and then comes to rest; hold, every controller and the panel stay where they are (MIDI-86).
2. Controller 121, reset all controllers, on every channel and whatever its value, as the architecture's MIDI-84 says (the Recommended Practice RP-015, page 2, as DEC-6464 version 2 quotes it; DEC-6464, proposed and awaiting the owner's confirmation): modulation (controller 1) to 0, the bender to its centre (8,192), hold (controller 64) off, and the registered parameter number selection (S106-26) to none, the null value 127 in controllers 100 and 101. The panel, controller 7's volume and the bend range (S106-26) are left as they are, and notes held are not released except as hold's going off releases them. Neither instrument acts on expression, the portamento switch (controller 65, counted as ignored, S106-25), sostenuto, the soft pedal, pan, bank select, an effect controller or a pressure, so RP-015's settings of those have nothing to act on. Every other controller the instrument responds to, as MIDI-84 item 4 requires this document to list:

| Controllers | What they move | On controller 121 | Reason |
|---|---|---|---|
| 3, 9, 12 to 27, 28 (synth60 only), 71 to 75 and 93: every panel controller of S106-25, among them 71 to 75, which MIDI 1.0 makes sound controllers and RP-015 leaves in any case | Parameters of the patch | Left as they are | A controller that moves a parameter of the patch is the patch, not a performance control (DEC-6464 item 4, MIDI-84 item 4) |
| 87, the JU-06A's BEND RANGE, and 6, 38, 96 and 97, data entry, increment and decrement of registered parameter number 0 (S106-26) | The bend range | Left as it is | It is the value of registered parameter number 0 (MIDI-90), and RP-015 says "Do NOT reset registered or non-registered parameters" (page 2) |

The patch and manual messages and the parameter change by system exclusive (S106-13, S106-14, S106-17) move the same panel and are left likewise.
3. Controller 123, all notes off, and controllers 124 (omni off), 125 (omni on), 126 (mono on) and 127 (poly on), whatever their value: every key held is released as a note off of it would release it; hold still holds, and a voice in its release goes on with it (MIDI-85, MIDI-89). Controllers 124 to 127 MUST do nothing else: they MUST NOT change which channels are heard (S106-2, MIDI-71) and MUST NOT change how voices are assigned.
- Reason: The Juno-106 recognises all notes off and "Mode messages (123 - 127) are also recognized as ALL NOTES OFF", and "The JUNO-106 does not respond to MONO ON message". The JU-06A recognises all sound off, reset all controllers, all notes off and the four mode messages, and says of the four "Same procecss as All Notes Off". Taking the mode messages as all notes off and nothing more is therefore exactly the JU-06A's behaviour and the Juno-106's for MONO ON and POLY ON; for OMNI OFF and OMNI ON the Juno-106 also changes its omni state (its table under section 2.1), which is left out (section 15.1). All sound off and reset all controllers are recognised by the JU-06A and not by the Juno-106; they are built today and are part of NeoTeletext's common layer (MIDI-9). What the JU-06A does on reset all controllers is not stated in the source; the architecture's rule (MIDI-84) holds for both instruments. As built, controller 121 restored the bend range; under MIDI-84 and MIDI-90 it leaves it, and section 18 lists the change.
- Source: Juno-106 manual, page 35, section 2.1 and its notes; page 34 (aux messages: all notes off, "(123-127)"). JU-06A chart, page 1, "Aux Message" rows and note "*2 Same procecss as All Notes Off". synth106's source, `mod.rs` (`control_change`). `midi-architecture.md`, MIDI-84, MIDI-85, MIDI-86 and MIDI-89; DEC-6464 version 2; RP-015, page 2; MIDI 1.0 4.2, printed pages 20, 24 and 25 (PDF 52, 56 and 57), A-5 (PDF 95) and Table IV (PDF 104).
- Verification: The architecture's tests of MIDI-84 to MIDI-86 and MIDI-89 for this family: a test holds three notes with a long release and hold on, sends 120, and checks the output is 0 by sample 1,024 and the click measure holds; a test moves controller 1, the bender, hold, controller 7, a panel slider and the bend range, sends 121, and checks controller 1 at 0, the bender at its centre and hold off, and controller 7, the slider and the bend range unchanged; a test sends controller 124 then a note on channel 5 and checks it sounds; the existing tests of controllers 123 to 127 continue to pass.

**S106-30. Other messages.** The instrument MUST count as ignored, and change nothing for, polyphonic key pressure (`0xAn`), channel pressure (`0xDn`), every system common message, and every system real-time message, including the timing clock, start, continue, stop and active sensing that the JU-06A recognises.
- Reason: The Juno-106 recognises none of them (its chart: after touch, system common, system real time, active sense: no). The JU-06A recognises clock, start, continue, stop and active sensing, which serve its delay's tempo sync and its link to other hardware; neither instrument has anything they could drive, and a lost connection is the architecture document's to detect (MIDI-101). The system common and real-time messages are never carried in a block at all (MIDI-8); the server refuses them, and a receiver that meets one passes it over and counts it.
- Source: Juno-106 manual, page 34. JU-06A chart, page 1, "System Real Time" and "Active Sensing". `midi-architecture.md`, MIDI-8 and MIDI-101. Listed in section 15.
- Verification: A test puts one of each into a score and checks the samples are identical to the score without them and that each is counted.

## 12. The synth60 patch

The Juno-60 has no MIDI, so no adopted interface defines a synth60 patch as a whole. Its panel is the Juno-106's sixteen sliders and switches, with three settings more (section 2), and the JU-06A, which models both instruments, has a controller for each of the three.

**S106-31. A synth60 patch is the 18 values and three controller values.** A synth60 patch MUST be the Juno-106's function type `30` message of S106-13, followed at the same instant by three control changes, in this order: controller 15 (DCO LFO/MAN/ENV), controller 28 (DCO SUB SW) and controller 93 (CHORUS OFF / I / II / I+II), each with the canonical value of its position (S106-24): controller 15 at 0 (LFO), 43 (MAN) or 86 (ENV); controller 28 at 0 (off) or 64 (on); controller 93 at 0 (OFF), 32 (I), 64 (II) or 96 (I+II). Its content is 21 values: the 18 of the message, then the three controller values. The three control changes MUST be written with their status byte (`0xBn`, n the channel of the message's byte d), as 9 bytes: `Bn 0F v`, `Bn 1C v`, `Bn 5D v`. The whole patch as messages is 33 bytes. A sender (the server, DEC-6462, which writes every patch from a program's typed fields or checks a program's bytes, S106-36 and S106-37) MUST make the 18 values agree with the three settings where they overlap: the PWM bit of parameter 17 is 1 when controller 15 is MAN or ENV and 0 when it is LFO; the chorus bits of parameter 16 are those of OFF, I or II, and those of II when controller 93 is I+II.
- Reason: Decision A4 carries a patch in its adopted interface's own form, and a synth60 patch has no single form; this composes the two adopted interfaces without inventing a byte. The 18 values alone are a valid Juno-106 patch and a valid synth60 panel (S106-32), so a tool that knows only the Juno-106's message reads a synth60 patch as the nearest Juno-106 sound, and the three controllers are Roland's own for exactly the three settings. The agreement rule makes the 18 values the nearest Juno-106 patch.
- Source: Juno-106 manual, page 35 (the message). JU-06A chart, page 1 (controllers 15, 28 and 93). Juno-60 manual, pages 12 and 32 (the PWM mode switch ENV/MANUAL/LFO; the sub-oscillator ON/OFF switch). Juno-60 service notes, Table 6, column "CHORUS" (0 to 3: four settings). The composition is NeoTeletext's own (section 16 item 4); alternatives are in open question 1.
- Verification: A test builds a synth60 patch for each combination of the three settings (3 × 2 × 4 = 24), sends it, and checks every field; a test checks that a sender's patch with ENV writes the PWM bit 1 and with I+II writes chorus II; a test checks that the 33 bytes of a patch equal the server's emitted bytes for the same typed patch.

**S106-32. An 18-value message alone on synth60.** On synth60, a function type `30` or `31` message MUST set, besides the 18 values, the three synth60 settings to those the 18 values imply: controller 15's setting to LFO or MAN by the PWM bit, the sub-oscillator switch on, and the chorus to OFF, I or II by its bits. A function type `32` message for parameter 16 or 17 MUST set the setting it overlaps in the same way (parameter 16: the chorus; parameter 17: the PWM source), and leave the sub-oscillator switch as it is. Controllers 15, 28 and 93 that follow then set the settings as section 10 says.
- Reason: The 18 values must give a definite synth60 panel by themselves, whatever came before, so that a Juno-106 patch played on synth60 always sounds the same, and the panel never keeps a synth60 setting from an earlier patch that the new one did not mention. The Juno-106's sub-oscillator is always switched in, its level alone setting how much is heard (Juno-106 manual, pages 16 and 32), so "on" is the setting that reproduces a Juno-106 patch.
- Source: Juno-106 manual, page 35; pages 16 and 32. synth106's source, `patch.rs` (`Patch::from_bytes` sets `sub` on). NeoTeletext's own (section 16 item 4).
- Verification: A test sets synth60 to ENV, sub off and I+II by controllers, then sends an 18-value message with PWM bit 0 and chorus off, and checks LFO, sub on and chorus off; a test sends parameter 17 alone and checks the sub switch unchanged.

**S106-33. Which message wins where they overlap.** Where a system exclusive message and a JU-06A controller set the same field, the instrument MUST apply them in the order of their times in the block, and at one tick in the order the block lists them (`midi-architecture.md`, MIDI-35): the later sets the field, and neither kind of message takes precedence over the other.
- Reason: On the Juno-106 the exclusive messages are themselves the panel's moves, sent one after another as a control moves (page 28); a later move of the same control replaces an earlier. Giving either kind precedence would make a score's result depend on the kind of message and not on what was played. S106-31 relies on this order: the three controllers follow the 18 values and refine them.
- Source: Juno-106 manual, page 28 (note 5); `midi-architecture.md`, MIDI-35. NeoTeletext's own rule (section 16 item 13).
- Verification: A test sends, at one tick, controller 74 at 10 then parameter 5 at 100 by exclusive message, and checks the cutoff is 100; and the other order, and checks 10.

## 13. Polyphony and assignment

The Juno-106 has two assignment modes, chosen by two buttons outside its patch (Juno-106 manual, page 22): "Poly 1. This mode turns the Juno-106 to a 6 voice polyphonic synthesizer assigning one synthesizer voice to each key pressed. This is suitable for the sound whose envelope curve is similar to piano or guitar, therefore chosen for usual performance." "Poly 2. This mode is very similar to Poly 1 assigning only one synthesizer voice to each key pressed. The primary advantage of Poly 2 is that only the last note or notes played together receive natural release length. This mode is suitable for the performance with portamento effect." Beneath, with no heading of its own: "If 6 keys are simultaneously pressed, no more key will sound." and "Pressing the Poly 1 and Poly 2 at the same time will turn the Juno-106 to the Solo unison mode, therefore it can be played as a monophonic synthesizer that assign 6 voices to each key pressed." The Juno-60's service notes describe three key-assignment modes of its test mode (Juno-60 service notes, page 22, "Key Assign"): UNISON, UP & DOWN (ROTARY), and DOWN (NON-ROTARY). The JU-06A's controller 86 is "POLY / (POLY) / SOLO / UNISON", with no further description. The Juno-106's interface has no message for the assignment mode; it is a setting of the panel outside the patch.

**S106-34. Six voices, Poly 1.** synth106 and synth60 MUST each have six voices and MUST assign one voice to each key pressed, a key taking the next voice at rest after the one last taken, round the six. A key pressed while six keys are held MUST NOT sound. When six voices sound and fewer than six keys are held, a new key MUST take a voice that is releasing: the one whose release began first.
- Reason: Six voices: for synth106, the Juno-106 manual, page 32 ("6 Voice programmable Polyphonic Synthesizer"); for synth60, the Juno-60's service notes. The order round the six is what is built, from the Juno-60's service notes ("The CPU assigns channels (voices) in a cyclic order", the ROTARY mode) and the Juno-106's test mode "ROTARY" (`mod.rs`, `Assign::Cyclic`). That a seventh key held does not sound is the Juno-106 manual's sentence on page 22. Which releasing voice a new key takes is not stated in the source; the one whose release began first is the one most nearly silent.
- Source: Juno-106 manual, pages 22 and 32. Juno-60 service notes, page 22, "Key Assign". synth106's source, `mod.rs` (`VOICES`, `Allocator::new(Mode::Poly(Assign::Cyclic))`). The seventh-key rule is a difference from what is built (section 18); open question 4.
- Verification: A test holds keys one by one and checks which voice each takes; holds six keys, presses a seventh, and checks it does not sound and the six continue; releases one and checks the next key takes the voice whose release began first.

**S106-35. Poly 2, solo unison and the JU-06A's assignment controller.** synth106 and synth60 MUST NOT implement Poly 2, solo unison, or any other assignment mode, and MUST count controller 86 as ignored, until the owner answers open question 3.
- Reason: None is built today (`mod.rs`: "No portamento, no arpeggiator, no unison or Poly 2"), the Juno-106's interface has no message for them, and what the JU-06A's four positions mean, in particular "(POLY)" and "SOLO", is not stated in the source.
- Source: Juno-106 manual, page 22. JU-06A chart, page 1, controller 86.
- Verification: A test sends controller 86 at every value and checks it is counted and changes nothing.

## 14. What the Rust server takes and gives for these instruments

DEC-6462 makes the Rust server the one implementation of the programming interface: a program sends typed requests at the level of the adopted interfaces, and the server validates them, packs patches into their messages, builds the blocks, bank images and records, splits what is too long and writes the restatements a live sound needs (`midi-architecture.md`, MIDI-13 to MIDI-22). The TypeScript and Python kits hold none of this logic: they carry the server's generated types and the calls that send them (MIDI-22). The form of the requests is the Rust server's document; these are what synth106 and synth60 need of it.

**S106-36. A patch as typed fields.** The server MUST accept a synth106 patch as named, typed fields: the sixteen sliders, each an integer 0 to 127; range, one of 16′, 8′ and 4′; pulse and sawtooth, each on or off; chorus, one of off, I and II; PWM source, LFO or manual; envelope polarity, positive or negative; VCA control, envelope or gate; high-pass filter, an integer 0 to 3. A synth60 patch MUST take the same fields, with PWM source also envelope, chorus also I+II, and a sub-oscillator switch, on or off. The server MUST refuse a field out of its range, an unknown field, a synth60-only value in a synth106 patch, and a missing field, each with a typed refusal naming the field. The spelling of each field's name is the Rust server document's.
- Reason: DEC-6462 item 1: "a patch as named, typed fields or as its standard system exclusive". The fields are exactly S106-22's.
- Source: DEC-6462. S106-22.
- Verification: The server's tests: one valid patch of each kind, and one refusal for each field's every way of being wrong.

**S106-37. A patch as its system exclusive.** The server MUST also accept a synth106 patch as the 24 bytes of a function type `30` or `31` message, and a synth60 patch as those 24 bytes followed by the 9 bytes of S106-31, and MUST refuse, with a typed refusal naming the byte, any that S106-19 would have the instrument ignore, and a synth60 patch whose three controller values are not canonical or whose 18 values do not agree with them (S106-31). From a typed patch the server MUST emit exactly these bytes, with canonical values.
- Reason: DEC-6462 item 1; DEC-6453's exact compatibility: a Juno-106 patch from any source is taken byte for byte. Refusing what the instrument would ignore keeps a program from sending something that silently does nothing.
- Source: DEC-6462. S106-13, S106-19, S106-31.
- Verification: The server's tests: the decodings of S106-15 as input; each malformation of S106-19 refused; a typed patch and its bytes round-trip exactly.

**S106-38. A bank of 1 to 128 patches.** The server MUST accept a bank of 1 to 128 patches of one kind, each in either form of S106-36 and S106-37 (MIDI-15), and MUST write it as a bank of the bank codec (MIDI-55) whose bank image is its patches' messages back to back, in the bank's order (MIDI-56): for synth106, 1 to 128 function type `30` messages of 24 bytes; for synth60, 1 to 128 patches of 33 bytes, each a function type `30` message followed by its three control changes (S106-31). Patch k's function type `30` message MUST carry k in byte e (S106-16), so that the program a message names and its position in the image agree; the server MUST refuse a bank given as bytes in which they disagree, naming the patch.
- Reason: S106-12; the architecture's bank image of messages (MIDI-56), which for this family is exactly what a Juno-106 librarian would send, one patch message for each patch.
- Source: S106-12, S106-16, S106-31; `midi-architecture.md`, MIDI-15, MIDI-55 and MIDI-56.
- Verification: A server test sends banks of 1 and 128 patches of each kind and checks the bank image byte for byte; a bank of 0 or 129 is refused.

**S106-39. What a record needs.** The architecture document sizes a bank and a block from these figures: a synth106 patch is 18 values, 24 bytes as its message; a synth60 patch is 21 values, 33 bytes as its messages; a bank of 128 is therefore at most 2,304 values (synth106) or 2,688 (synth60), and a bank image of 3,072 or 4,224 bytes, within the architecture's 16,384 (MIDI-55). The longest message either instrument takes is the 24-byte exclusive message, within the 256 bytes of a system exclusive event (MIDI-28); none travels as a message longer than an event (MIDI-50, MIDI-51). An inline synth60 patch (MIDI-60) is the 24-byte system exclusive event and the three control-change events at one tick, in one block, never split (MIDI-37).
- Reason: Decision A4 leaves storage to the architecture document and asks the family document for sizes.
- Source: S106-13, S106-31. Decision A4. `midi-architecture.md`, MIDI-28, MIDI-37, MIDI-50, MIDI-51, MIDI-55 and MIDI-60.
- Verification: The architecture document's tests of carriage; a server test checks the bank image's length for 128 patches of each kind.

**S106-40. Restatement, joining and a lost block.** The server MUST restate the state of synth106 and synth60 as the architecture says (`midi-architecture.md`, MIDI-93 to MIDI-99): in the first block of a live sound and at least once in every 50 blocks after, aiming at every 25 (MIDI-96), and at tick 0 of block 0 of every stored sound (MIDI-99). This family's restatement, written whole in one block at one tick before the program's events of that tick (MIDI-95, MIDI-98), MUST be, in this order:
1. the program change of the last program chosen (program 0 if none has been), with no bank select (the Juno-106 has none, MIDI-64);
2. where the panel has moved since that program change, or its last patch came inline, the whole panel as one function type `30` message (byte e the program number of item 1), and on synth60 the three control changes of S106-31, carrying every one of the 18 values and the three synth60 settings as they stand. This one message stands for the architecture's "latest value of every parameter moved since" (MIDI-93): it sets every field a JU-06A controller or a function type `32` message could have moved, in 24 or 33 bytes, where a message for each field moved could take up to 25 controllers or 18 exclusive messages of 7 bytes;
3. the bend range, where it is not two semitones, by the message that last set it: controller 87 at the canonical value of its semitones, or the registered parameter number 0 sequence whole (controllers 101 and 100 at 0, then 6 and 38, MIDI-37);
4. pitch bend, controller 7, controller 1 and hold (controller 64), each where it is not at its value after reset all controllers (MIDI-84) and, for controller 7, not at 127.

Held notes MUST NOT be restated. A restatement to an instrument that already holds the state it carries MUST change nothing audible: a program change to the program already chosen, or a patch message equal to the panel, MUST NOT restart an envelope, the oscillator's phase, the LFO or the filter's state (MIDI-97). A receiver that joins a live sound starts at the newest block with the panel of S106-10 and is put right by the next restatement (MIDI-100). When a live block is played through as lost, both instruments MUST release every note, take hold off, set the registered parameter number selection to none and render the block with no event, leaving the panel as it stands (MIDI-102).
- Reason: A viewer who joins late or loses a block must end up with the sender's panel, whatever moved it: the Juno-106's program change alone would put a moved panel back to its bank patch. The architecture requires each family document to state its restatement exactly (MIDI-93). The whole-panel message is the Juno-106's own way of carrying a whole panel ("Information of each parameter of the patch selected in the master Juno will be sent to the slave Juno", Juno-106 manual, page 28).
- Source: `midi-architecture.md`, MIDI-93 to MIDI-102; Juno-106 manual, page 28 (note 5), page 35 (section 3.1). DEC-6462 item 1 (the server "repeats what a viewer who joins late needs").
- Verification: The architecture's tests of MIDI-93 and MIDI-97 for this family: a server test drives a live synth106 and a live synth60 sound through a program change, controller 74 moving the cutoff, controller 93 setting I+II on synth60, controller 87 and a bend, checks the restatement's bytes, plays it into a fresh instrument and checks the two instruments' states equal; a test plays the audio demo's tune with and without a restatement at every block and checks identical samples; the existing lost-block test runs on this family with a registered parameter data entry after the loss and checks it changes nothing.

---

## 15. What is left out

### 15.1 Of the Juno-106's interface

| Item | Where the manual has it | Why it is left out |
|---|---|---|
| Everything transmitted (sections 1.1 to 1.3: notes with velocity 64, hold from the rear jack, all notes off, omni off and poly on at power-up, program change, bender, LFO modulation, the exclusive messages) | Page 35, page 34 ("Transmitted") | synth106 and synth60 only receive; nothing in NeoTeletext listens to an instrument. |
| The MIDI FUNCTION switch I, II, III | Pages 27 and 33 | A setting of the hardware; both instruments act as at III (S106-1). |
| The MIDI channel setting, 1 to 16, its button, and the button's "special function" of clearing what came through MIDI | Page 25 | A setting of the hardware; all channels are heard (S106-2). Clearing is all sound off (S106-29). |
| OMNI OFF and OMNI ON changing which channels are heard | Page 35, the table under section 2.1 | There is no basic channel to fall back to; the JU-06A's processing (all notes off only) is followed (S106-29). |
| Mode messages and exclusive messages heard on the basic channel only | Page 35, section 2.1 | As above (S106-2). |
| The 5-millisecond minimum between a note on and its note off | Page 34 | A limit of the hardware's processor (S106-6). |
| Memory write, copy, the Memory Protect switch | Pages 7 to 10, 33 | Operations of the hardware's memory; a bank is written by its sender. |
| Tape save, verify and load of a whole bank group | Pages 11 to 15 | Hardware; and not documented byte by byte in the manual. |
| Patch shift by pedal | Page 24 | Hardware; program change does the same. |
| Key transpose | Page 24 | Not modelled. A sender transposes its notes. |
| The rear TUNE knob, ±50 cents | Pages 5 and 33 | Not modelled; the instrument is in tune by construction. |
| The VOLUME knob | Page 23 | Outside the patch; controller 7 stands for it (S106-28). |
| The PORTAMENTO time knob and switch | Page 23 | Outside the patch and not modelled; open question 3. |
| The DCO and VCF bend sensitivity knobs | Page 23 | Outside the patch; the DCO's range is S106-26, the VCF's is not modelled. |
| The LFO modulation depth knob beside the bender | Pages 21, 23 | Outside the patch; fixed at ±50 cents (S106-8). |
| Poly 2 and solo unison | Page 22 | Not modelled (S106-35); open question 3. |

### 15.2 Of the JU-06A's interface

| Item | Where the chart has it | Why it is left out |
|---|---|---|
| The control-surface mode, its whole second page | JU-06A chart, page 2 | In that mode the JU-06A recognises nothing ("Recognized: x" in every row) and transmits 24 controllers on channel 1 whose numbers contradict the sound-module mode's (for example controller 3 is VCF FREQ there and LFO RATE in sound-module mode; 9 is VCF RES there and LFO DELAY here). It is a map for the JU-06A acting as a controller of a computer program, not a map an instrument receives. An instrument can follow only one numbering, and the sound-module mode is the one in which the JU-06A is itself the instrument. For the record, its controllers are: 3 VCF FREQ, 9 VCF RES, 12 CHORUS OFF / ON, 16 DCO SQR SW, 17 DCO SAW SW, 18 DCO SUB, 19 DCO NOISE, 26 DCO LFO, 27 LFO DELAY, 28 VCF LFO, 29 LFO RATE, 47 DCO RANGE, 50 DCO PWM, 60 DCO LFO / MAN / ENV, 70 CHORUS I / II, 79 HPF FREQ, 81 VCF ENV, 82 VCF KYBD, 83 ENV A, 84 ENV D, 85 ENV S, 86 ENV R, 88 VCA ENV / GATE, 110 VCA LEVEL; notes 60 to 71 (with its BANK/MEMORY buttons) and 48 to 72 (with a K-25m keyboard) transmitted. |
| Transmission of anything | Page 1, "Transmitted" | As 15.1. |
| Controllers 5 and 65 (portamento), 11 (expression), 29 (LFO wave), 30 (LFO trig), 86 (assignment mode) | Page 1 | Nothing in either instrument to move; counted as ignored (S106-25); open question 3. |
| Controllers 82, 83, 88, 89, 91 (the delay effect and its tempo sync) | Page 1 | Neither instrument modelled has a delay. |
| Velocity | Page 1, "Velocity Note On: o" | What the JU-06A does with it is not stated; neither instrument modelled has velocity (S106-3). |
| Timing clock, start, continue, stop, active sensing | Page 1 | Nothing to drive (S106-30). |
| Program change limited to 0 to 63 | Page 1 | The Juno-106's 0 to 127 is taken for both (S106-12). |

### 15.3 Of the instruments modelled, outside any interface

| Item | Source | Why it is left out |
|---|---|---|
| The Juno-60's LFO TRIGGER MODE switch (stored in its patch) and LFO TRIGGER button | Juno-60 manual, pages 17, 18; service notes, Table 6 | Not modelled; synth60's LFO is as at AUTO. A fourth synth60 setting would need it (open question 3). |
| The Juno-60's arpeggio, HOLD button, KEY TRANSPOSE, ARPEGGIO CLOCK input, VCF CONTROL pedal jack, PATCH SHIFT jack | Juno-60 manual, pages 19 to 21, 33 | Not modelled. |
| The Juno-60's DCB port | Juno-60 manual, page 21 | Roland's own pre-MIDI bus, for the OP-8 only, with no filed description; not a programming interface. |
| The Juno-60's tape interface | Juno-60 manual, pages 8 to 11 | Hardware, and its data format is not described. |

### 15.4 Taken with a difference: the behaviours common to every synthesizer

Where the Juno-106's or the JU-06A's interface differs from the one rule the architecture sets for every synthesizer (`midi-architecture.md` section 11.1), the common rule holds, and these are the departures.

| Behaviour | What the adopted interface says | What synth106 and synth60 do | Requirement |
|---|---|---|---|
| Hold, controller 64 | The Juno-106: hold on at 1 to 127, off at 0 (Juno-106 manual, page 35, section 2.1). The JU-06A: "HOLD", no band stated. | Down at 64 to 127, up at 0 to 63, on both instruments. | MIDI-87; S106-9 |
| Pitch bend resolution | The Juno-106: "LS 6 bits are ignored", an 8-bit bend (page 35, note under section 2.2). | All 14 bits, centre 8,192. | MIDI-91; S106-7 |
| Reset all controllers, controller 121 | The Juno-106: not recognised (page 34). The JU-06A: recognised, effect not stated. | Acted on, as the Recommended Practice RP-015 says (page 2): the performance controllers to rest; the panel, the volume and the bend range unchanged, as S106-29 item 2 lists. DEC-6464, proposed and awaiting the owner's confirmation. | MIDI-84; S106-29 |
| All sound off, controller 120 | The Juno-106: not recognised. The JU-06A: recognised, effect not stated. | Every voice silent within 1,024 samples by a fade that does not click. | MIDI-86; S106-29 |
| Volume, controller 7 | Neither the Juno-106 nor the JU-06A recognises it. | The common layer's volume, with the shared law. | MIDI-9, MIDI-82, MIDI-92; S106-28 |
| Bend range | The Juno-106: a knob beside the keyboard, no message (page 23). The JU-06A: controller 87, "BEND RANGE", no scaling stated. | Controller 87 and registered parameter number 0, the last received holding, at most twelve semitones; pending the owner's answer to the architecture's open question 5. | MIDI-90; S106-26 |
| Mode messages 124 to 127 | The Juno-106: all notes off, and omni off and omni on also change its omni state (page 35). The JU-06A: "Same process as All Notes Off". | All notes off and nothing more. This is the JU-06A's behaviour; only the Juno-106's omni change departs. | MIDI-71, MIDI-89; S106-29 |

## 16. What NeoTeletext defines itself

Each item exists because no filed document defines it.

1. **The scaling of a slider's controller (S106-23).** The chart gives none. The identity, because the slider's own values are 0 to 127.
2. **The value bands of every switch controller, and the order of positions where the chart's name does not settle it (S106-24, S106-25).** The chart gives none. `floor(value × n ÷ 128)`, canonical value the lowest of a band; controller 12's order from the Juno-106 panel; controller 21's from the exclusive bit.
3. **The scaling of controller 87 and its default (S106-26); registered parameter number 0 as a second way to set the range (S106-26).** The chart gives no scaling; thirteen bands for 0 to 12 semitones; two semitones as built. Registered parameter number 0 is the architecture's addition to every adopted interface (MIDI-90), none of which documents it; pending the owner's answer to the architecture's open question 5. That reset all controllers leaves the range is the architecture's rule (MIDI-84), not this document's.
4. **The synth60 patch as 18 values and three controller values, the agreement rule, and what an 18-value message alone does on synth60 (S106-31, S106-32); range as the octave transpose on synth60 (S106-22).** No interface defines a Juno-60 patch.
5. **That a key outside 24 to 108 is moved by whole octaves (S106-5).** The manual says it is "transposed" to fit, not by how much.
6. **The linear curve of controller 1 and its ±50-cent depth (S106-8).** The depth is the receiver's knob on the Juno-106; as built.
7. **The hold band, on from 64, on both instruments (S106-9).** The Juno-60 has no MIDI, and the Juno-106's own band (on from 1) departs from the architecture's one rule for every synthesizer (MIDI-87), which this document follows.
8. **That the Juno-60's patch numbers 11 to 78 are placed as group A's (S106-11).** No document joins the two numberings.
9. **What a sender writes in byte e for a patch in no bank (S106-16).**
10. **The refusal of malformed exclusive messages, whole (S106-19).** What a Juno-106 did with one is not stated.
11. **That controller 28 is ignored on synth106 (S106-27).**
12. **Controller 7 and its law (S106-28); controllers 120 and 121 on synth106, which the Juno-106 does not recognise (S106-29).** NeoTeletext's common layer (MIDI-9, MIDI-82, MIDI-84, MIDI-86, MIDI-92), as built.
13. **The order rule where exclusive messages and controllers overlap (S106-33).**
14. **Which releasing voice a new key takes (S106-34).**
15. **All channels as one instrument for mode messages and exclusive messages too (S106-2).**
16. **The restatement of this family's state for a live or stored sound, with the whole panel as one patch message (S106-40).** A broadcast's need, which the architecture defines (MIDI-93 to MIDI-99) and asks each family document to state exactly.

## 17. Open questions for the owner

Three questions of the architecture document bear on this family and are not repeated here: its open question 1 (new codec numbers, 14 for this family and 19 for its banks, or the present code 6 and bank code 11; answered by DEC-6465 with new codes 12 to 19, awaiting the owner's confirmation, so 14 and 19), its open question 5 (pitch bend range by registered parameter number 0 in every family, which S106-26 follows), and its open question 6 (pitch bend at full resolution in every family, which S106-7 follows in place of the Juno-106's eight bits).

**1. How is a synth60 patch carried?**
- *Option A (recommended): the 18 values and three JU-06A controller values* (S106-31). Every byte is an adopted interface's; the 18 values alone are the nearest Juno-106 patch, readable by any Juno-106 tool. 33 bytes as messages.
- *Option B: the 18 values with the three settings in byte 17's bits 5 and 6 and in unused combinations of byte 16.* Smaller (24 bytes), but it invents bits the manual says are 0, and a Juno-106 tool would refuse or misread the patch: what DEC-6453 forbids.
- *Option C: the JU-06A's controller values alone, all 24 that move a synth60 field.* Wholly the JU-06A's, but 72 bytes as messages, and no longer a Juno-106 patch at all.
- *Option D: no synth60 patch of its own;* synth60 plays Juno-106 patches only, and the three settings are reachable only by live controllers. Simplest, but a stored synth60 sound could not keep its sub-oscillator off, its envelope PWM or its I+II chorus.
- *Recommendation:* A.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: a synth60 patch is the Juno-106's 18 values and the three JU-06A controller values (S106-31).

**2. The JU-06A's value bands are not in the filed chart.**
Roland's chart names controllers and nothing more. A JU-06A owner's manual or parameter guide may state how each controller's value maps to a slider and which values select which switch position.
- *Option A:* look for such a document from Roland, file it, and replace S106-23, S106-24 and S106-26 with its figures.
- *Option B:* approve S106-23, S106-24 and S106-26 as NeoTeletext's own.
- *Recommendation:* A as a short search by the owner or the main session (this document's author was not permitted to fetch anything), then B if nothing is found. Only the bands and scalings change; the controller numbers and their fields stand.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, a search for a Roland JU-06A owner's manual or parameter guide that states its value bands, begun at once; if none is found, S106-23, S106-24 and S106-26 are approved as NeoTeletext's own (option B). The document stands as written meanwhile.

**3. Which performance controls should the instruments gain?**
The JU-06A recognises, and the instruments modelled have outside their patch, controls synth106 and synth60 lack. For each: portamento time and switch (5, 65; the Juno-106 has them, the Juno-60 cannot); expression (11; a second gain, as controller 7); LFO wave (29; neither instrument modelled has it); LFO trig (30; possibly the Juno-60's stored TRIGGER MODE, which would be a fourth synth60 setting); assignment mode (86; Poly 2 and solo unison from the Juno-106's manual, and the meaning of "(POLY)" and "SOLO" not stated).
- *Option A:* none now; they stay counted as ignored (as specified).
- *Option B:* add those that the instruments modelled have: portamento on synth106, Poly 2 and solo unison on both via controller 86 (mapping POLY to Poly 1, "(POLY)" to Poly 2, UNISON to solo unison, and SOLO to solo unison too until its meaning is found), and the Juno-60's LFO TRIGGER MODE on synth60.
- *Option C:* B and also expression as a second gain.
- *Recommendation:* A for this interface's first build, since each of B's items is new instrument work, not interface work; then B, recorded as its own to-do, because DEC-6453 asks for what a performance needs.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: no new performance controls in the interface's first build; the additions of option B become a to-do.

**4. Does a seventh key held steal a voice?**
The Juno-106 manual says "If 6 keys are simultaneously pressed, no more key will sound" (page 22), printed beneath the Poly 2 paragraph but reading as general. What is built gives a seventh key the voice of the first.
- *Option A (recommended):* the manual's rule for both modes (S106-34).
- *Option B:* keep what is built.
- *Recommendation:* A; it is the only statement in the source.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: a seventh key held does not sound, as the Juno-106 manual states (S106-34).

## 18. Differences from what is built today

What exists is described in `synthesizer-wire-format.html`, `programming-the-synthesizers.html` and synth106's source. Implementing this document changes the following.

**Names and kinds.**
1. Today the kit and the program protocol have one kind, `juno` (with `juno_live`, `juno_blocks`, `juno_bank`), and a `model` field of `"106"` or `"60"`. They become two kinds, `synth106` and `synth60`, each with its live, blocks and bank forms, and the `model` field goes (DEC-6461 item 3). The record's extension tag 5 (0 for synth106, 1 for synth60) stays as it is (MIDI-48). The family's codec becomes code 14, and its banks the bank codec 19, if the architecture's open question 1 is answered as recommended (MIDI-107 to MIDI-109, retiring codes 3 to 11); otherwise the present code, 6, is kept with the new block contents, and banks keep the present analogue bank code, 11. DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation), so the codes are 14 and 19. This document does not decide it.

**The patch.**
2. Today a bank holds 18 raw bytes per patch (`PATCH_BYTES`, `Patch::from_bytes`, `Patch::to_bytes`), the 18 values. A synth106 patch's content stays those 18 values; a bank becomes a bank image of the 24-byte function type `30` messages (MIDI-56, S106-38), and a synth60 bank one of 33-byte patches.
3. Today a synth60 patch is the same 18 bytes, and `from_bytes` always sets `sub` on and cannot express ENV or I+II (the wire format's "Known gaps"). It becomes 21 values (S106-31): the engine's reader gains the three controller values, and `to_bytes` for synth60 gains them too.
4. The checks of `Patch::from_bytes` stay (S106-19), and gain the length and header checks of a whole message.

**The messages.**
5. Today the instruments take control changes of controllers 1, 7, 64, 120, 121 and 123 to 127 only. They gain the 25 JU-06A controllers of S106-25 that move a patch field, and controller 87 (S106-26); `Synth106` needs a way to set one field without a whole patch.
6. Today no system exclusive message reaches the instruments (a four-byte slot cannot hold one). They gain function types `30`, `31` and `32` (section 7), carried as Standard MIDI File system exclusive events (decision A3).
7. Today a pitch bend uses all 14 bits. It stays so (S106-7, MIDI-91); the Juno-106's reading of eight bits is a departure (section 15.4).
8. Today the bend range is a constant, two semitones (`PITCH_BEND_SEMITONES`). It becomes the setting of controller 87 and of registered parameter number 0, two semitones by default, at most twelve, left unchanged by controller 121 (S106-26, MIDI-84, MIDI-90).
9. Today every key 0 to 127 sounds at its own pitch. Keys below 24 and above 108 become folded by octaves (S106-5).
10. Today a seventh key held takes the first key's voice. Under S106-34 it does not sound (open question 4).
11. Today a program change chooses patch 0 to 31, must carry a second data byte of 0 in its slot, and a bank holds 1 to 32 patches. They become 0 to 127, the ordinary two-byte message, and 1 to 128 (S106-10, S106-12). A program change to a missing patch becomes counted as ignored.
12. Controller 121 follows the architecture's MIDI-84 (S106-29): it leaves the bend range and the panel, and clears the registered parameter number selection. synth106's hold moves from on at 1 to on at 64 (`PEDAL_DOWN_106`, S106-9, MIDI-87). Controller 120's fade is held to at most 1,024 samples and the click measure (MIDI-86). After a lost block the registered parameter number selection is also cleared (S106-40, MIDI-102). The mode messages, controllers 1, 7 and 123, note on and note off are as built.
13. Today each block is a fixed number of four-byte slots; it becomes the architecture's event list (MIDI-23 to MIDI-38), carried in the event codec's DATA records (MIDI-39 to MIDI-47).

**The server and the kits (DEC-6462).**
14. Today the TypeScript kit packs a patch (`packJunoPatch`, `junoInitPatch`), builds blocks (`SynthScore("juno")`), repeats program changes (`SynthProgramRepeater`), and checks fields itself. The server takes the typed patch, the exclusive bytes and banks of up to 128 (S106-36 to S106-38), emits the bytes, builds the blocks, restates the whole state for live and stored sounds (S106-40, replacing the kit's program repeater), and refuses with typed refusals; the kit's sound code for these instruments shrinks to generated types and calls, and the Python kit gains the same.
15. Today the server checks each patch byte against the receiver's range; it gains the checks of S106-19 and S106-31.

**Tests and documents.**
16. The engine's tests that build patches from 18 bytes keep working for synth106; synth60's tests gain the three settings. New tests are those each requirement's "Verification" names, among them the manual's examples (S106-15).
17. The module documentation of `patch.rs` ("synth60 itself has no MIDI, so there is no byte form of its own") and of `mod.rs` (the list of messages taken) are rewritten to cite this document's requirements once they are rdm requirements. The two HTML documents in `synthesizer-reference/` describe the old form and are regenerated.
