# synth8: the programming interface

**Purpose.** This document specifies how synth8 is played and programmed: every MIDI message it takes, what each does, which of its two patches each addresses, what a synth8 patch is, and how each value becomes a position of a control of synth8's panel. It is the basis for implementing synth8's part of the synthesizer protocols.

**Scope.** synth8 only: the instrument that models the Roland Jupiter-8 (`neoteletext-common/docs/audio/synthesizers.md` says once which instrument each synthesizer models). The transport (blocks, records, packets), the form of a block, how a bank of patches is stored and named, how a system exclusive message longer than a block travels, and the messages common to every synthesizer belong to the architecture document, `midi-architecture.md` in this folder; this document states what synth8 needs of them and refers to it. Under DEC-6462 the Rust server is the one implementation of this interface: a program sends a synth8 patch as named, typed fields or as its control-change values, and the server validates it and builds the records; the kits only carry the types. This document defines the values and their meaning that the server's types carry. The sound of the instrument (its oscillators, filters and envelopes) is not specified here.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

**What the owner must read first.**

1. **The instrument modelled has no MIDI.** Its owner's manual describes no MIDI and no digital interface for notes, controls or patches: its outside connections are the Hold, Portamento, VCF and VCA control jacks, the arpeggio clock input and DIN connection, the highest-note control voltage and gate outputs, and the tape memory's Save and Load jacks (owner's manual, printed pages 5 to 7, 29 and 30). DEC-6457 records that it has "only Roland's DCB"; no filed document describes that interface, and this document does not use it.

2. **The adopted interface is a chart, and only a chart.** DEC-6453 and DEC-6457 adopt Roland's "MIDI Implementation Chart (Part)" for a model named "JUPITER-08", version 1.01, dated 1 October 2026. The filed file holds the chart's rows from "Basic Channel" to control change 119 and the legend of the four MIDI modes; it holds no row for program change, system exclusive, system common, system real time or auxiliary messages, it gives no value range and no value band for any controller, and it describes no controller beyond its name. It is all read; this document takes every fact it states and marks every gap as "not stated in the source".

3. **Which product "JUPITER-08" is, is not established** (open question 1, section 14). Nothing in the filed documents says what Roland product the chart belongs to, and nothing says whether its controller numbers equal those of Roland's 2015 JP-08 Boutique module. The chart's name for controller 7, "PATTERN PART LEVEL", suggests a part of a multi-part instrument with patterns, which the Jupiter-8 is not; that is an inference, recorded as one. Every controller number in section 7 is taken from the chart as filed and stands whatever the answer; what the answer could change is the value bands and the meaning of two controllers the chart names but does not explain (41 "BEND PITCH" and 57 "VCO-2 MODE").

4. **Where the chart is silent, NeoTeletext defines the gap.** The value bands of every selector and switch, the scaling of every slider, the order of the patch, the MIDI channels of the two patches, the program change and the controller numbers of the two bender switches that a patch holds are NeoTeletext's own, each marked as such and listed in section 13.

---

## 1. Sources

All files are under `~/devel/teletext-reference/synthesizers/jupiter-8/`. No web page was fetched and no reference program was opened for this document.

| Short name here | File | What it is used for |
|---|---|---|
| **The chart** | `manuals/roland-jupiter-08-midi-implementation-chart-v1.01.txt` (2,817 bytes; "Model: JUPITER-08", "Date: October 1st, 2026", "Version: 1.01"; the text of Roland's web page `jupiter-08_reference_v100/en-US/581830795601006731.html`, saved on 18 November 2026; SHA-256 `3c7d7270…786d91` per `documents.tsv`) | The adopted interface. It has no page numbers; it is cited by its rows ("the chart, row Velocity, Note On"). Every row it holds is reproduced in section 4.1 and section 7. |
| **The table** | `manuals/roland-jupiter-8-system-8-parameter-correspondence-table.pdf` (one page; "JUPITER-8/SYSTEM-8 Parameter Correspondence Table", © 2016 Roland Corporation, "01") | Its "Parameter List" numbers 44 parameters of the original's panel, 1 to 44, with the SYSTEM-8's value range of each; its "Controller Map" draws where each sits on the original's panel. Used for the order of the patch, for which panel controls a patch holds, and for what the SYSTEM-8 adds. |
| **The owner's manual** | `manuals/roland-jupiter-8-owners-manual.pdf` (26 PDF pages; "JP-8 Operation Manual"). Its printed page numbers run 3 to 25 on PDF pages 2 to 24, then 29 and 30 on PDF pages 25 and 26; printed pages 1, 2 and 26 to 28 are not in the scan. | The panel of the instrument modelled: every control, its positions and its range; key modes, assign modes, the hold, the arpeggio, portamento and the bender panel (printed pages 3, 11 to 21); patch memory, patch presets and tape memory (printed pages 3, 9 to 11, 21 to 24); the specifications (printed pages 29 and 30). Cited by printed page. |
| **synth8's source** | `~/devel/neoteletext-renderer-teletext/crates/neoteletext-audio-instruments/src/synth8/patch.rs`, `mod.rs`, `law.rs` and `voice.rs`, and `crates/neoteletext-audio/src/receiver/instruments/analogue.rs`, `instruments.rs`, `record.rs` and `codec.rs`, as they stood on 18 November 2026 (engine commit `dd0421c6`) | What is built today: the 43-byte patch, the messages taken, the two patches and their channels, the key mode, the bender panel. Each constant there names its own source. |
| **Wire format as built** | `~/devel/teletext-reference/synthesizers/synthesizer-wire-format.html` and `programming-the-synthesizers.html` | What exists today on the wire and in the kit, for section 15. |
| **The architecture** | `midi-architecture.md` in this folder | The frame this document works inside: the block and its bounds (MIDI-23 to MIDI-38), the bank and the patch (MIDI-54 to MIDI-66), the channel map (MIDI-67 and MIDI-70), the common behaviours of every synthesizer (MIDI-84 to MIDI-92, its section 11.1), the restatement (MIDI-93 to MIDI-99), the lost block (MIDI-102) and the codec numbers (MIDI-107 to MIDI-109, and its open question 1). Requirements cited "MIDI-n" are that document's. |

**Documents that are not filed.** No copy of the MIDI 1.0 Detailed Specification, of the Standard MIDI Files 1.0 specification or of the MIDI Association's Recommended Practice RP-015 ("Response to Reset All Controllers") is filed in `~/devel/teletext-reference/`; all three are listed as documents to obtain in `midi-architecture.md` section 1.5. This document uses MIDI 1.0 only for what is common to all MIDI: the status bytes, that a note on of velocity 0 is a note off, the 14 bits and centre of pitch bend, the convention that a switch controller is on from 64, the standard meanings of controllers 5, 8, 64, 65 and 120 to 127, registered parameter number 0 (pitch bend sensitivity), the pairing of controllers 0 to 31 with 32 to 63, and the four modes the chart's legend names; and RP-015 only through MIDI-84. Every such fact is marked "(MIDI 1.0, to be checked)" or "(RP-015, to be checked)" and is to be checked against the filed copy before implementation.

Decisions this document follows: DEC-6453 (each instrument is programmed as its most well-known existing interface does it; NeoTeletext defines something only where nothing exists, and records why), DEC-6457 (the provenance of synth8 and the choice of the chart), DEC-6461 (the names), DEC-6462 (the Rust server is the core; the kits are thin), DEC-6464 (every synthesizer answers Reset All Controllers identically, by RP-015, volume unchanged; recorded as proposed, awaiting the owner's confirmation), DEC-6410 and DEC-6429 (instruments as codecs of the audio profile), DEC-6428 (the clean-room rules), and the architecture decisions A1 to A6 of the brief of 18 November 2026.

## 2. Terms

- **synth8.** NeoTeletext's eight-voice synthesizer of two oscillators a voice, playable as one instrument of eight voices or as two of four.
- **The instrument modelled.** The Roland Jupiter-8. It is named in this document only where a source is cited or its panel is described.
- **The adopted interface.** The chart: the control changes and channel messages that Roland's chart for "JUPITER-08", version 1.01, marks as recognised.
- **Half.** One of synth8's two parts, each with its own patch: the **upper** and the **lower**. In the whole key mode the upper patch plays on all eight voices; in dual and split each half has four voices (owner's manual, printed pages 3 and 11).
- **Key mode.** How the keyboard is shared between the halves: **whole**, **dual** or **split** (section 6).
- **Panel control.** One slider, knob, selector or switch that a synth8 patch holds. synth8 has 42 (section 7). The controls that are not part of a patch (volume, balance, the bender panel, portamento, the hold) are **performance controls**.
- **Slider.** A panel control that passes through every place between its ends: the instrument's sliders and its rotary SOURCE MIX and FINE TUNE knobs.
- **Selector.** A panel control of three or more fixed positions. **Switch.** A panel control of two.
- **Controller.** A MIDI control change's controller number, 0 to 127. **Value** is its data byte, 0 to 127.
- **Canonical value.** The one value a sender writes for a given position of a control, where several values select the same position.
- **Patch.** The positions of all 42 panel controls of one half. On the wire it is the 42 values of section 9.
- **Bank.** The set of patches a synth8 sound plays from, chosen among by program change. How a bank is stored and named is the architecture's (MIDI-55 to MIDI-57).
- **Block.** 20 milliseconds of a sound's input, 960 samples at 48,000 Hz (decision A2). Its content is a Standard MIDI File track-event list whose tick is 0.1 millisecond (decision A3).
- **Counted as ignored.** A message the instrument does not act on adds one to a count the instrument keeps (`ignored_events` today), and nothing else happens. Nothing is an error. It is what the architecture calls "passed over and counted".
- **Not stated in the source.** The filed document does not say. Nothing is supplied from memory in its place; where synth8 needs an answer, the answer is NeoTeletext's own and is listed in section 13.

## 3. What the two instruments are (facts, not requirements)

**The instrument modelled.** An eight-voice polyphonic synthesizer of 61 keys, C to C (owner's manual, printed pages 11 and 29). Each voice has two oscillators (VCO-1 and VCO-2), a source mixer, a high-pass filter, a low-pass filter of −24 or −12 dB an octave, an amplifier and two four-stage envelopes; one low-frequency oscillator serves each half (printed pages 3, 15 to 21). It has 64 patch memories numbered 11 to 88 and 8 patch presets A to H, each preset a pair of patch numbers with a key mode (printed pages 3, 9, 11, 22 and 24). Its keyboard can be one instrument of eight voices (whole) or two of four (dual, split), each with its own patch and assign mode (printed pages 3, 11 and 12). It has an arpeggiator, polyphonic portamento, a bender lever with sensitivity sliders and switches, an LFO modulation touch pad, two hold selectors and a tape memory (printed pages 12 to 14, 23 and 24). It has no MIDI (point 1 above).

**The JUPITER-08 of the chart.** All that the filed documents say of it is what the chart says: it takes notes on one basic channel of 1 to 16 in mode 3 (omni off, poly), recognises note-on velocity, polyphonic key pressure and pitch bend, recognises 50 control changes and transmits 41 of them. The 41 it transmits are named after controls of the Jupiter-8's panel, all but one (57, "VCO-2 MODE") after a control the owner's manual names. The nine it only recognises are 1, 7, 10, 11, 41, 64, 91, 92 and 118; of those, 118 "PORTAMENTO SW" is a control of the Jupiter-8's panel, 1 and 64 stand for its touch pad and hold pedal, 41 "BEND PITCH" is not explained, and five (7 "PATTERN PART LEVEL", 10 "Pan", 11 "Expression", 91 "Reverb Send Level", 92 "Delay Send Level") name nothing the Jupiter-8 has.

---

## 4. The channel messages

### 4.1 What the adopted interface says

The chart, every row the filed file holds, other than the control-change rows (which are in section 7.1). "o" is the chart's "Yes", "x" its "No", "-" as the chart prints it.

| Chart row | Transmitted | Recognised | Remarks |
|---|---|---|---|
| Basic Channel, Default | 1–16 | 1–16 | |
| Basic Channel, Changed | 1–16 | 1–16 | |
| Mode, Default | Mode 3 | Mode 3 | The legend: "Mode 3: OMNI OFF, POLY" |
| Mode, Messages | x | x | |
| Mode, Altered | - | x | |
| Note Number | 0–127 | 0–127 | |
| Note Number, True Voice | - | 0–127 | |
| Velocity, Note On | o | o | |
| Velocity, Note Off | x | x | |
| Aftertouch, Key's | x | o | |
| Aftertouch, Channel's | x | x | |
| Pitch Bend | x | o | |
| Control Change | (section 7.1) | (section 7.1) | 50 controllers |
| Program Change | not in the filed file | not in the filed file | Not stated in the source |
| System Exclusive | not in the filed file | not in the filed file | Not stated in the source |
| System Common | not in the filed file | not in the filed file | Not stated in the source |
| System Real Time | not in the filed file | not in the filed file | Not stated in the source |
| Aux Messages | not in the filed file | not in the filed file | Not stated in the source |

The file's heading is "MIDI Implementation Chart (Part)": it is a part of a chart, and its last row is controller 119.

### 4.2 Requirements

**S8-1. The messages synth8 acts on.** synth8 MUST act on exactly these MIDI 1.0 channel messages, and on no other: note off (status `0x8n`); note on (status `0x9n`); control change (status `0xBn`) of the controllers that requirements S8-8 to S8-15, S8-31 and the table of S8-16 name, on the channels S8-2 gives; program change (status `0xCn`) on the channels S8-2 gives; and pitch bend (status `0xEn`). Here `n` is the channel, 0 to 15 (MIDI channels 1 to 16). Every other channel message (polyphonic key pressure `0xAn`, channel pressure `0xDn`, a control change of any controller not named or on a channel S8-2 does not give it, a program change on another channel), every system exclusive message and every system common and system real-time message MUST be counted as ignored and MUST change nothing in the instrument.
- Reason: These are the messages the chart recognises that the instrument modelled can act on, with the additions of section 13.
- Source: The chart, all rows. The departures (velocity, key pressure, the controllers synth8 does not take) are S8-3, S8-6 and section 7.2; the additions are listed in section 13.
- Verification: A test sends one message of every status from `0x80` to `0xEF`, on every channel, and checks which change the instrument's state, and that each of the others adds one to the count of ignored messages and leaves the rendered samples identical to a run without it.

**S8-2. Channels.** synth8 MUST treat MIDI channels as follows.
1. Note on and note off, on any channel 1 to 16, MUST play the one keyboard; the key mode (S8-18) decides which half or halves sound a key.
2. Pitch bend and the control changes of performance controls (controllers 1, 5, 7, 8, 11, 41, 64 and 118; the registered parameter controllers 6, 38, 96, 97, 98, 99, 100 and 101 of S8-31; and the common layer's 120, 121 and 123 to 127 of S8-13), on any channel, MUST act on the whole instrument. The registered parameter number selection of S8-31 MUST be kept for each channel, as MIDI-76 requires, and the range it sets is the whole instrument's.
3. This is synth8's channel map under MIDI-67: for notes and performance controls, every channel 1 to 16 addresses the whole instrument; for panel controls and program changes, channel 1 addresses the upper half, channel 2 the lower half, and channels 3 to 16 address no half.
4. A control change of a panel control (the 42 controllers of S8-16) on MIDI channel 1 (`n` = 0) MUST move that control of the upper patch; on MIDI channel 2 (`n` = 1) it MUST move that control of the lower patch; on channels 3 to 16 it MUST be counted as ignored.
5. A program change on MIDI channel 1 MUST choose the upper patch and on MIDI channel 2 the lower patch (S8-12); on channels 3 to 16 it MUST be counted as ignored.
- Reason: The chart has one basic channel (1 to 16, set at the instrument and "memorized" in a JUPITER-08 that has a menu for it), mode 3, and says nothing of two patches. The instrument modelled has two patches and a keyboard, and edits one patch at a time through its "Panel Mode" Lower and Upper buttons (owner's manual, printed pages 11 and 30). Channels 1 and 2 stand in for the panel mode: the upper patch on channel 1, so that a sender that knows nothing of halves programs the patch the whole key mode plays. Program changes on channels 1 and 2 are what is built.
- Source: The chart, rows "Basic Channel" and "Mode". Owner's manual, printed pages 11 ("press the dark blue Lower Panel Mode button") and 30 ("Panel mode: Lower, Upper"). synth8's source: `analogue.rs` (`SYNTH8_UPPER_CHANNEL`, `PROGRAM_CHANNELS` = 2) and `mod.rs` ("The instrument is one part and hears every channel"). Items 1 to 5 are NeoTeletext's own (section 13 items 1 and 2). The architecture: MIDI-67 (each family states its channel map) and MIDI-70 (synth8's two parts, as `synth8.md` states).
- Verification: A test plays one score on each channel and checks identical samples; sends a control change of controller 3 on channels 1, 2 and 3 in the dual key mode and checks that only the upper cutoff, then only the lower cutoff, change, and that the third is counted; and sends program changes on channels 1, 2 and 16 and checks the upper patch, the lower patch and a count.

**S8-3. Note on.** On a note on whose velocity is 1 to 127, synth8 MUST take the key (data byte 1, 0 to 127) as pressed, and give it voices under the key mode (S8-18) and each half's assign mode (S8-19). The velocity MUST NOT change the sound in any way. A note on whose velocity is 0 MUST be taken as a note off of that key.
- Reason: The chart recognises note-on velocity, but the instrument modelled has none; synth8 models the instrument, and the chart does not say what velocity does on the JUPITER-08. This is a departure from the chart, listed in section 12.2.
- Source: The chart, rows "Note Number" (0–127 recognised) and "Velocity, Note On" (recognised). Owner's manual, printed page 29 (the keyboard is "61 Key (5 octave)", with no touch response among the specifications). synth8's source, `mod.rs` ("Velocity is ignored, as the instrument's keyboard has none"). Velocity 0 as a note off: MIDI-88, the rule every synthesizer shares (MIDI 1.0, to be checked).
- Verification: A test plays the same chord at velocities 1, 64 and 127 and checks identical samples; and checks that a note on of velocity 0 releases its key exactly as a note off does.

**S8-4. Note off.** On a note off, synth8 MUST take the key as released, in both halves (a half that holds no voice on the key ignores it). The release velocity MUST NOT change the sound.
- Reason: The chart does not recognise note-off velocity. Both halves are released because the key mode or split point may have changed since the key went down.
- Source: The chart, row "Velocity, Note Off". synth8's source, `mod.rs` (`key_up`).
- Verification: The test of S8-3, with note offs of velocities 0, 64 and 127; and a test that holds a key in split, changes nothing else, and releases it.

**S8-5. The pitch of a key.** With VCO-1's RANGE at 8′, the master tuning at its centre and the bender at its centre, key 69 MUST sound 440 Hz and every other key MUST sound its equal-tempered MIDI pitch, a semitone a key. The instrument's keyboard is MIDI keys 36 to 96 (its C0 to C5); keys outside it MUST go on at a semitone a key.
- Reason: The chart recognises note numbers 0 to 127 and does not say which pitch each sounds. synth8 keeps what is built, which is the instrument's tuning and the instrument's own keyboard placed on MIDI keys.
- Source: The chart, row "Note Number". Owner's manual, printed page 9 ("reference very near to A-440 if the Master Tune knob … is in the 12 o'clock position"). synth8's source, `law.rs` (`A4` = 440 Hz on key 69; `LOWEST_KEY` = 36, each with its source in the service notes). NeoTeletext's own (section 13 item 9).
- Verification: A test measures keys 24, 36, 60, 69, 96 and 108 with VCO-1 alone at 8′ and each voice's tolerance at zero, and checks each within 1 cent of its MIDI pitch.

**S8-6. Key pressure and channel pressure.** synth8 MUST NOT act on polyphonic key pressure or on channel pressure: each such message is counted as ignored.
- Reason: The chart recognises polyphonic key pressure ("Aftertouch, Key's"), but does not say what it does on the JUPITER-08, and the instrument modelled has no pressure. Channel pressure is not recognised by the chart. The first is a departure, listed in section 12.2.
- Source: The chart, rows "Aftertouch, Key's" and "Aftertouch, Channel's". Owner's manual, printed page 29.
- Verification: The test of S8-1.

**S8-7. Pitch bend: the bender.** On a pitch bend, synth8 MUST form the 14-bit number `data byte 2 × 128 + data byte 1`, whose centre is 8,192, and MUST move the bender lever to `(number − 8,192) ÷ 8,192` of its travel either way. The bender MUST move the pitch of each oscillator whose bend switch in its half's patch is on (S8-16, bytes 40 and 41) by that share of the VCO bend depth, and the low-pass filter's cutoff by that share of the VCF bend depth (S8-14). The lever MUST go to its new place at no more than an end's travel in 21 milliseconds (128 ticks of the instrument's control rate), as it does today.
- Reason: The chart recognises pitch bend. On the instrument modelled the bender is a centre-sprung lever whose effect "is determined by the VCO and VCF selectors and Bend sensitivity slider controls", "VCO-1 (the pitch of VCO-1 alone), VCO-2 (the pitch of VCO-2 alone), and VCF (Tone Color)", the extremes achieving "the same amount of bend in opposite directions" (owner's manual, printed page 14). The slew is what is built, because a message places a lever that a hand moves through every place.
- Source: The chart, row "Pitch Bend". Owner's manual, printed pages 14 and 30 ("Bender lever, VCO bend sensitivity, VCO-1 bend SW, VCO-2 bend SW, VCF bend sensitivity, VCF bend SW"). synth8's source, `mod.rs` (`BEND_SLEW`, `control`). The architecture, MIDI-91 (every synthesizer uses all 14 bits; the chart states no resolution). MIDI 1.0 (to be checked) for the 14 bits and the centre.
- Verification: A test holds a note with both bend switches on and the VCO bend depth at 200 cents, sends pitch bends of 0, 4,096, 8,192, 12,288 and 16,383, and checks the measured pitch against −200, −100, 0, +100 and +199.98 cents, each within 1 cent once the lever has arrived; and checks that with VCO-2's bend switch off, VCO-2 alone with VCO-1 out of the mix does not move.

**S8-8. The modulation wheel, controller 1: the LFO modulation.** On a control change of controller 1, synth8 MUST set the bender panel's LFO modulation to `value ÷ 127` of its depth: at value 0 none, and at value 127 the low-frequency oscillator of each half moves the pitch of every oscillator by the LFO VCO depth and the cutoff by the LFO VCF depth (S8-14), either way. Controller 33 MUST be counted as ignored.
- Reason: The chart recognises controller 1, "Modulation Wheel". The instrument modelled has no wheel; its "Auxiliary LFO controls" apply the low-frequency oscillator to the VCO, the VCF or both, at a depth each slider sets, through an on-off touch pad (owner's manual, printed page 14). The wheel stands in for the pad and its rise time: what is built.
- Source: The chart, controller 1. Owner's manual, printed pages 14 and 30 ("LFO Mod: On/Off button, Rise time, VCO Mod sensitivity, VCO Mod SW, VCF Mod sensitivity, VCF Mod SW"). synth8's source, `mod.rs` (`CONTROL_MODULATION_WHEEL`, `Performance::lfo_vco`, `lfo_vcf`). The linear law is what is built and NeoTeletext's own (section 13 item 10).
- Verification: A test sets the LFO VCO depth to 100 cents with a square low-frequency wave and measures the pitch's swing at values 0, 64 and 127 against 0, 50.4 and 100 cents either way.

**S8-9. Volume, controller 7, and expression, controller 11.** On a control change of controller 7, synth8 MUST set its volume gain from the value, 0 (silent) to 127 (full), and on a control change of controller 11 its expression gain likewise, each by the volume law every NeoTeletext synthesizer shares (MIDI-82 and MIDI-92: a gain of `(value × value) ÷ (127 × 127)` of full); the output MUST be multiplied by both, and each MUST move to its new place over at most 256 output samples (5.3 milliseconds). Before either arrives its value is 127. Reset all controllers sets expression to 127 and leaves the volume unchanged (S8-13, MIDI-84). Neither is part of a patch. Controllers 39 and 43 MUST be counted as ignored.
- Reason: The chart recognises controller 7, which it names "PATTERN PART LEVEL", and controller 11, "Expression". Neither is a control of the Jupiter-8's panel; controller 7 stands in for the instrument's VOLUME knob, which is no part of a patch ("All programs … can be programmed to a suitable volume level, making further adjustment of the master Volume during performance usually unnecessary", owner's manual, printed page 9). Expression is a performance volume the chart defines; taking it costs one multiplication and lets a score shape a phrase without disturbing a fade.
- Source: The chart, controllers 7 and 11. Owner's manual, printed pages 9 and 29 ("Volume"). synth8's source, `mod.rs` (`CONTROL_VOLUME`) and the shared `analog/volume.rs`; the architecture states the law once (MIDI-82) and takes the chart's "PATTERN PART LEVEL" as this volume (MIDI-92). What either controller does on the JUPITER-08 beyond its name is not stated in the source. Controller 11 is new to synth8 (section 15).
- Verification: A test checks the level of a held chord at controller 7 values 0, 64 and 127 with controller 11 at 127, and the same for controller 11 with controller 7 at 127, against the shared law, and checks that the product is what is heard and that no step of either gain exceeds the slew.

**S8-10. Balance, controller 8.** On a control change of controller 8, synth8 MUST set the balance of the two halves: at value 0 the lower half alone, at 64 both at their full level, at 127 the upper half alone, each half falling in a straight line from the centre to nothing at the other end; the shares MUST move to their new places over at most 256 output samples. In the whole key mode the balance MUST have no effect. Before controller 8 arrives the value is 64. Controller 40 MUST be counted as ignored.
- Reason: The instrument modelled has a BALANCE knob between its Upper and Lower sections, which is no part of a patch; "While in the Whole Mode, the Balance control is inoperative" (owner's manual, printed page 11). The chart has no controller for it; controller 8 is MIDI 1.0's balance, and it is what is built.
- Source: Owner's manual, printed pages 11 and 29 ("Volume, Balance (Upper, Lower)"). synth8's source, `mod.rs` (`CONTROL_BALANCE`, `shares`, `BALANCE_SLEW`). MIDI 1.0 (to be checked) for controller 8. NeoTeletext's own (section 13 item 3). That the balance does nothing in whole is a change from what is built (section 15 item 9).
- Verification: A test in dual plays a key at balances 0, 32, 64, 96 and 127 and checks each half's share; and in whole checks that every balance gives identical samples.

**S8-11. The hold, controller 64.** On a control change of controller 64, synth8 MUST put the hold on at values 64 to 127 and off at values 0 to 63. While the hold is on, a released key's voices MUST keep sounding at their sustain level, as long as no new key needs their voice; when the hold goes off, every note so held MUST be released. In every key mode, whole, dual and split alike, the hold MUST hold the whole keyboard, as MIDI-87 requires of every synthesizer.
- Reason: The chart recognises controller 64, "Hold Pedal", and states no values; the threshold is the one MIDI-87 sets for every synthesizer. The instrument modelled's pedal "will activate the Hold function for the entire keyboard" in whole and dual and "on the Lower end of the keyboard only" in split, and held notes sound "indefinitely at their programmed Sustain levels" "until that Hold function is removed or until more notes are played than there are voices available". Holding only the lower half in split is a departure from MIDI-87's one behaviour; under the owner's rule that every synthesizer behaves the same way on common MIDI behaviours, the architecture's rule holds, and the instrument's split behaviour is listed in section 12.3 and is open question 7. This changes what this document first said, and what is built (section 15 item 13).
- Source: The chart, controller 64. Owner's manual, printed page 13 ("Hold Selectors"). synth8's source, `mod.rs` (`hold`). The architecture, MIDI-87. MIDI 1.0 (to be checked) for the switch's threshold.
- Verification: A test holds a chord, puts the hold on, releases the keys and checks the chord still sounds; repeats in split and checks that the notes of both halves are held; sends values 0, 1, 63, 64 and 127 and checks the hold's state after each (MIDI-87); and plays more keys than voices under the hold and checks the oldest held voice is taken.

**S8-12. Program change.** On a program change on MIDI channel 1 or 2, synth8 MUST take its data byte, 0 to 127, as the number of a patch in the sound's bank, and MUST set the upper patch (channel 1) or the lower patch (channel 2) to it, as if the control changes of the patch's 42 values had arrived on that channel at that instant (S8-23). The performance controls (the wheel, the bender, the volume, expression, balance, portamento, the hold) and the keys held are left as they are. synth8 has no bank select (MIDI-64: controllers 0 and 32 are counted as ignored), so every program change chooses from bank index 0, the first bank the sound names, with the program equal to the data byte (MIDI-59). If that bank holds no patch of that number (a data byte of 64 to 127, or a number past the bank's last patch), synth8 MUST set the half to the default patch (S8-22) and count the program change as ignored, as MIDI-59 requires of every family. Until a first program change arrives on a channel, its half plays patch 0 of the bank, or the default patch (S8-22) if patch 0 is missing or refused (MIDI-61; every sound names at least one bank, MIDI-57). A program change to the patch the half already plays, with no control moved since, MUST change nothing that is heard: it MUST NOT restart an envelope, an oscillator's phase or a low-frequency oscillator (MIDI-97).
- Reason: The chart has no program change row, and the instrument modelled has no MIDI, so the message and its numbering are NeoTeletext's own. Program change is MIDI's message for choosing a stored sound and is what is built. A missing patch sets the default, as the architecture's MIDI-59 requires of every family; this changes what is built, where a missing patch leaves the half alone (section 15 item 11). A program change that repeats the present patch is what the server's restatement sends to every viewer (MIDI-93, MIDI-97), so it must be silent to a viewer who lost nothing.
- Source: Not stated in the source (the filed chart has no program change row). synth8's source, `analogue.rs` (`Played::new`, `Player::event`). NeoTeletext's own (section 13 item 4). The architecture: MIDI-59, MIDI-61, MIDI-64 and MIDI-97. The numbering against the instrument's patch numbers is S8-28.
- Verification: A test builds a bank of 64 different patches and sends program changes 0, 7, 8, 63 on channel 1 and checks the upper patch after each; the same on channel 2 for the lower; sends program change 64 and a program change beyond a bank of 4 and checks the half stands at the default patch and the count rises; sends a program change to the patch already playing under a held chord and checks the samples identical to a run without it; and checks that held notes, the bender, the volume and the hold are unchanged by a program change.

**S8-13. The messages of NeoTeletext's common layer.** synth8 MUST also act on these control changes, which the chart does not recognise ("Mode, Messages: x"), each exactly as the architecture's common behaviours (its section 11.1) state for every synthesizer:
1. Controller 120, all sound off, whatever its value: every voice of both halves, held, sustained and releasing alike, MUST be brought to silence by a fade that passes the click measure, within 1,024 output samples (MIDI-86); synth8 takes the sound out over at most 256 output samples, as built, which is within that bound. Every voice is then emptied and every key let go; the hold is left as the pedal has it, and no controller and neither patch changes. Messages that arrive in the meantime, up to 16, are taken in order once the sound has gone, as built.
2. Controller 121, reset all controllers, whatever its value: as MIDI-84 states, which is the MIDI Association's RP-015 as DEC-6464 understands it (DEC-6464 is recorded as proposed, awaiting the owner's confirmation; RP-015, to be checked). For synth8 that is: the modulation wheel (controller 1) to 0; expression (controller 11) to 127, its maximum; the hold (controller 64) off, which releases the notes it held; the bender to its centre, 8,192; the registered parameter number selection of every channel to none (S8-31). These are left as they are: the volume (controller 7), the balance (controller 8), the portamento time (controller 5) and switch (controller 118), the VCO bend depth set by controller 41 or by registered parameter number 0 (S8-14, S8-31), every panel control of both patches, both patches themselves, the key mode and the split point. Notes held by keys are not released.
3. Controller 123, all notes off, whatever its value: every key held is released as a note off of each would; a note held by the hold stays held until the hold goes off, and a note in its release goes on with it (MIDI-85).
4. Controllers 124 (omni off), 125 (omni on), 126 (mono on) and 127 (poly on), whatever their values: each MUST act as all notes off (item 3) and do nothing else; none changes the channels synth8 hears (S8-2) or any half's assign mode (MIDI-71, MIDI-89). The chart's mode 3 ("OMNI OFF, POLY") is not changed by them, because no message changes it.
- Reason: The owner requires every synthesizer to behave the same way where MIDI defines a behaviour common to all instruments (DEC-6464, "we require ALL synths to behave the same way in this regard"); the architecture states the one rule for each (MIDI-84 to MIDI-89), and synth8's departures from the chart are listed in section 12.4. A receiver must be able to silence a sound at once and release every note, and the server's restatements and the end of a stored sound rely on these messages.
- Source: The architecture, MIDI-9, MIDI-71 and MIDI-84 to MIDI-89; DEC-6464 items 1 to 4; MIDI 1.0 (to be checked) for the controllers; RP-015 (to be checked) for reset all controllers; synth8's source, `mod.rs` (`control_change`, `DEFERRED`). The chart, rows "Mode, Messages" and "Mode, Default".
- Verification: The existing tests of controllers 120, 121 and 123 (`tests/synth8_instrument.rs`), changed so that controller 121 sets expression to 127 and leaves the volume, the balance, controller 118, the portamento time and the VCO bend depth unchanged; and the architecture's tests of MIDI-84 to MIDI-89 for synth8: hold three notes and send each of 120, 121, 123, 124, 125, 126 and 127 in turn and check the stated effect, and with the hold on check that 123 leaves the notes held and 120 silences them by sample 1,024.

**S8-14. The bender panel's depths and controller 41.** synth8 MUST hold four depths of the bender panel, none of them part of a patch: the VCO bend depth (0 to 1,200 cents, default 200), the VCF bend depth (0 to 4,800 cents, default 0), the LFO VCO depth (0 to 1,200 cents, default 50) and the LFO VCF depth (0 to 4,800 cents, default 0). On a control change of controller 41, synth8 MUST set the VCO bend depth to `floor((value × 1,200 + 63) ÷ 127)` cents: value 0 is none, value 127 an octave. Registered parameter number 0, pitch bend sensitivity, MUST set the same VCO bend depth (S8-31); whichever of controller 41 and registered parameter number 0 arrived last holds (MIDI-90). The VCO bend depth is the bend range of MIDI-90: the pitch moved by a full bend either way, at most 1,200 cents (12 semitones), default 200 cents (2 semitones). Neither a program change nor reset all controllers changes it (MIDI-84, MIDI-90). No message sets the other three depths; they stay at their defaults.
- Reason: The instrument modelled has, on its bender panel, a VCO bend sensitivity slider, a VCF bend sensitivity slider and two LFO modulation sensitivity sliders, with switches (owner's manual, printed pages 14 and 30). The chart recognises controller 41, "BEND PITCH", and says nothing more of it; of the bender panel's controls the VCO bend sensitivity is the one that name fits. Whether the JUPITER-08's controller 41 is a sensitivity, a range in semitones or something else is not stated in the source (open question 2). The other depths have no message in the chart and none today; section 13 item 11 and open question 4 say why none is added.
- Source: The chart, controller 41. Owner's manual, printed page 14. synth8's source, `mod.rs` (`Performance`, `BEND_MAX` from the service notes' adjustment 25-1, `CUTOFF_MAX` and `DEFAULT` own choices). The scaling is NeoTeletext's own (section 13 item 5).
- Verification: A test sends controller 41 at 0, 64 and 127 and measures the pitch at full bend against 0, 605 and 1,200 cents; a test sends controller 41 at 64, then registered parameter number 0 of 3 semitones, and checks a full bend moves 300 cents, then controller 41 at 127 and checks 1,200 cents; a test checks a program change and controller 121 leave the depth unchanged.

**S8-31. Pitch bend range by registered parameter number 0.** synth8 MUST act on registered parameter number 0, pitch bend sensitivity, as MIDI-90 requires of every synthesizer that plays notes, and on the registered and non-registered parameter number messages that carry it, as MIDI-76 states, on any channel:
1. Controllers 101 and 100 select a registered parameter number, `controller 101's value × 128 + controller 100's value`; controllers 99 and 98 select a non-registered parameter number in the same way. The selection is kept for each channel, and is none at the start of a sound, after reset all controllers (S8-13), and after a lost block (S8-26).
2. When the selection is registered parameter number 0: controller 6 (data entry, coarse) MUST set the VCO bend depth (S8-14) to `value × 100` cents, its semitones, with no cents; controller 38 (data entry, fine) MUST set the cents above the semitones last set, a value above 99 taken as 99; controller 96 (increment) MUST raise the depth by one cent and controller 97 (decrement) lower it by one cent, whatever their values. Each result MUST be limited to 0 to 1,200 cents, a larger value set to 1,200 (12 semitones, the most `mod.rs` builds, `BEND_MAX`).
3. When the selection is none, registered parameter number 127, 127 (which selects none), any other registered parameter number, or any non-registered parameter number (synth8 has none), controllers 6, 38, 96 and 97 MUST change nothing and be counted as ignored.
- Reason: MIDI-90 makes registered parameter number 0 the one way every synthesizer's bend range is set, beside each interface's own message; the chart's own is controller 41 (S8-14), which sets the same depth. None of these controllers is used by the chart, so the map of S8-16 is unchanged (MIDI-78 rule 6). That the coarse value clears the cents, and that increment and decrement move by one cent, follow MIDI 1.0's conventions as the architecture reads them (MIDI-75), to be checked; the treatment of cents above 99 is NeoTeletext's own (section 13 item 16, MIDI-81).
- Source: The architecture, MIDI-76 and MIDI-90 (open question 5 of that document asks the owner to confirm registered parameter number 0 in every family; this requirement is pending that answer); MIDI 1.0 (to be checked) for the parameter number, its data and the null number 127, 127; synth8's source, `mod.rs` (`BEND_MAX`). The chart has no row for any of these controllers.
- Verification: A test selects registered parameter number 0 and sends data entry 1, 7 and 24 semitones in turn, bending fully after each, and checks 100, 700 and 1,200 cents (24 limited to 12 semitones); a test sends controller 38 of 50 after 2 semitones and checks 250 cents; a test sends registered parameter number 127, 127 then data entry and checks nothing changes and the message is counted; a test selects a non-registered parameter number and checks data entry changes nothing.

**S8-15. Portamento: controllers 118 and 5.** On a control change of controller 118, synth8 MUST switch portamento on for both halves at values 64 to 127 and off at values 0 to 63. On a control change of controller 5, synth8 MUST set the portamento time from the value: at 0 a change of pitch is at once, and the glide's time constant rises with the value to 1 second at 127, by the law built today. With portamento on and a time above 0, each voice MUST glide from the pitch it last sounded to its new key's pitch. Neither controller is part of a patch. Controller 65 and controller 37 MUST be counted as ignored.
- Reason: The chart recognises controller 118, "PORTAMENTO SW", and has no controller for the portamento's time. The instrument modelled has "polyphonic portamento that may be assigned to the entire keyboard, to the Upper end of a split keyboard, or switched 'Off' entirely using the associated three position switch", and a rotary time control: "Pitch changes are instantaneous with the Portamento control set at '0'". Controller 5 is MIDI 1.0's portamento time and what is built. The switch's third position, upper only, has no message (section 12.3). Controller 65, MIDI 1.0's portamento switch, is what synth8 takes today; the chart's 118 replaces it, so that one switch has one controller.
- Source: The chart, controller 118. Owner's manual, printed pages 14 and 30 ("Portamento: Time, Mode (Upper only/Off/On)"). synth8's source, `mod.rs` (`Portamento`, `PORTAMENTO_LONGEST`, own choice). Controller 5 and the time law: NeoTeletext's own (section 13 item 3).
- Verification: A test plays two notes an octave apart with controller 118 at 127 and controller 5 at 0, 64 and 127, and checks the time to cover 63 per cent of the octave against the law; and with controller 118 at 0 checks the pitch changes within one tick; and checks that controller 65 is counted.

---

## 5. Where the controllers sit in MIDI 1.0's map

**S8-16 is in section 7.** The requirement here concerns the pairing of controllers.

**S8-17. No coarse and fine pairs.** synth8 MUST take every controller of the chart as one controller carrying one 7-bit value, and MUST NOT pair any controller from 0 to 31 with the controller 32 higher as its least significant bits. In particular controllers 35, 41, 46, 56, 57, 59, 60, 61, 62 and 63, which MIDI 1.0 reserves as the fine parts of controllers 3, 9, 14, 24, 25, 27, 28, 29, 30 and 31, MUST mean what the chart names them and nothing else.
- Reason: The chart assigns ten controllers of the range 32 to 63 to panel controls of their own (for example 35 "LFO WAVEFORM", which MIDI 1.0 would pair with 3 "VCF CUTOFF"). An implementation that followed MIDI 1.0's pairing would turn the cutoff when the LFO's waveform changed.
- Source: The chart, the control-change rows. MIDI 1.0 (to be checked) for the reserved range.
- Verification: A test sets the cutoff with controller 3, then sends controller 35, and checks that the cutoff is unchanged and the LFO waveform is changed.

---

## 6. Key modes, assign modes and the two halves

**S8-18. Key mode and split point.** A synth8 sound MUST have one key mode, whole, dual or split, and one split point, a MIDI key of 0 to 127, both set by the sound's OBJECT record, in extension tag 7 as today (MIDI-48): one byte of mode, 0 whole, 1 dual, 2 split, and one byte of split key. The server writes the tag from the program's typed fields for the sound. In whole, every key MUST play the upper patch on all eight voices. In dual, every key MUST play both patches, four voices each. In split, keys below the split point MUST play the lower patch on four voices and keys from the split point up the upper patch on four voices. Without the tag the key mode is whole and the split point key 60. No MIDI message changes the key mode or the split point.
- Reason: The instrument modelled: "The Whole Mode operates as one eight voice polyphonic instrument, while Dual and Split modes divide the JP-8 into two four-voice instruments that may even be assigned different patches. Split Mode divides the keyboard into Lower and Upper sections while Dual Mode layers two patches from each keypress", and "The keyboard is split into two octaves for the Lower section and three octaves for the Upper, marked by an arrow", which on its keyboard of MIDI keys 36 to 96 (S8-5) is a split at key 60. The chart has no message for a key mode. A key mode in the OBJECT is what is built, chosen so that a receiver that joins a live sound late has it.
- Source: Owner's manual, printed pages 3 and 11. The chart (no row). synth8's source, `record.rs` (`TAG_SYNTH8_KEYS`), `mod.rs` (`KeyMode`, `SPLIT_DEFAULT`). The default split point 60, which the source calls an own choice, rests on printed page 11; a variable split point is the service notes' later instruments (cited in `mod.rs`) and is NeoTeletext's own here (section 13 item 6).
- Verification: The existing test `a_synth8_has_two_patches_a_key_mode_and_a_split_point` passes; a test in split with the default checks key 59 plays the lower patch and key 60 the upper.

**S8-19. Assign modes.** Each half MUST give its keys voices by the assign mode of its own patch (S8-16, byte 37): **Poly-1**, a voice for each key, which rings to the end of its release, new keys taking voices in the order first played once all are busy; **Poly-2**, the same, except that a new key cuts the release of every voice already released; **Solo**, one voice, the lowest key held; **Unison**, every voice of the half on the keys held, shared among them. A change of a half's assign mode MUST release that half's voices, those the hold kept too.
- Reason: The instrument modelled: printed page 12, "Assign Modes": Poly-1 "each key pressed is assigned one voice … and will reach it's full natural release length"; Poly-2 "only the last note or notes played together receive their natural Release length. Any notes played previously will have instantaneous Releases"; Solo "one voice in Whole Mode or one voice for each section of the Split or Dual Modes", "Low Note priority"; Unison "All 8 synthesizers will be assigned to any one key pressed, dividing to four each for two keys, and so on". "All four Assign Modes may be used in any three of the available Key Modes."
- Source: Owner's manual, printed page 12. The chart, controller 119 "SOLO/POLY/UNISON". synth8's source, `assign.rs`.
- Verification: The existing random-playing test of `mod.rs` passes, driven through control changes of controller 119 on channels 1 and 2 instead of `set_patch`.

**S8-20. Each half's low-frequency oscillator.** Each half MUST have its own low-frequency oscillator, run from its own patch's LFO controls; in whole, the upper half's runs every voice. Its delay MUST start when a key of its half goes down while no other key of that half is held.
- Reason: The instrument modelled: "The two LED's will flash independently to indicate the LFO speed of the Lower and Upper sections whenever the Jupiter-8 is in Dual or Split Key Mode", and "When the Delay Time slider is raised, pressing a key on the keyboard will delay the introduction of the LFO output".
- Source: Owner's manual, printed page 18. synth8's source, `mod.rs` (`lfos`, `key_down`).
- Verification: The existing tests of the low-frequency oscillator in `tests/synth8_instrument.rs` pass when the patches are set by control changes.

---

## 7. The panel control map

### 7.1 Every controller of the chart

The chart's control-change rows, all 50, in its order. "Tx" and "Rx" are its Transmitted and Recognised columns. The "Jupiter-8" column says whether the name is a control of the instrument modelled's panel and which (the table's parameter number in brackets); the last column says what synth8 does.

| Controller | Tx | Rx | The chart's name | Jupiter-8 | synth8 |
|---|---|---|---|---|---|
| 1 | x | o | Modulation Wheel | Not a panel control; stands in for the LFO modulation touch pad | Takes it: S8-8 |
| 3 | o | o | VCF CUTOFF | VCF CUTOFF FREQ (20) | Patch byte 19 |
| 7 | x | o | PATTERN PART LEVEL | Not a panel control (a part's level); stands in for the VOLUME knob | Takes it: S8-9 |
| 9 | o | o | VCF RESONANCE | VCF RES (21) | Patch byte 20 |
| 10 | x | o | Pan | Not a panel control | Counted as ignored: synth8 is mono (section 12.2) |
| 11 | x | o | Expression | Not a panel control | Takes it: S8-9 |
| 13 | o | o | VCF SLOPE | VCF SLOPE (22) | Patch byte 21 |
| 16 | o | o | VCO-1 LEVEL | SOURCE MIX, VCO-1 side (18) | Patch byte 16 |
| 17 | o | o | VCO-2 LEVEL | SOURCE MIX, VCO-2 side (18) | Patch byte 17 |
| 18 | o | o | PWM | PULSE WIDTH MOD slider (8) | Patch byte 6 |
| 19 | o | o | PWM SOURCE SEL | PULSE WIDTH MOD selector LFO, MANUAL, ENV-1 (9) | Patch byte 7 |
| 20 | o | o | VCO-1 RANGE | VCO-1 RANGE (11) | Patch byte 9 |
| 25 | o | o | VCO ENV MOD | VCO MODULATOR, ENV MOD (5) | Patch byte 4 |
| 26 | o | o | VCO LFO MOD | VCO MODULATOR, LFO MOD (4) | Patch byte 3 |
| 27 | o | o | LFO DELAY TIME | LFO DELAY TIME (2) | Patch byte 1 |
| 28 | o | o | VCF LFO DEPTH | VCF LFO MOD (25) | Patch byte 24 |
| 29 | o | o | LFO RATE | LFO RATE (1) | Patch byte 0 |
| 35 | o | o | LFO WAVEFORM | LFO WAVE FORM (3) | Patch byte 2 |
| 41 | x | o | BEND PITCH | Not stated in the source; taken as the bender panel's VCO bend sensitivity | Takes it: S8-14 (open question 2) |
| 46 | o | o | VCO-1 WAVEFORM | VCO-1 WAVEFORM (12) | Patch byte 10 |
| 56 | o | o | VCO-2 FINE TUNE | VCO-2 FINE TUNE (16) | Patch byte 14 |
| 57 | o | o | VCO-2 MODE | Not stated in the source; no control of the panel bears the name | Counted as ignored (open question 2) |
| 59 | o | o | CROSS MOD | VCO-1 CROSS MOD (10) | Patch byte 8 |
| 60 | o | o | FREQ MOD SELECT | VCO MODULATOR switch VCO-1, BOTH, VCO-2 (6 and 7) | Patch byte 5 |
| 61 | o | o | VCO-2 WAVEFORM | VCO-2 WAVEFORM (17) | Patch byte 15 |
| 62 | o | o | VCO-2 RANGE | VCO-2 RANGE (15) | Patch byte 13 |
| 63 | o | o | VCO-2 LO FREQ | VCO-2 LOW FREQ / NORMAL (14) | Patch byte 12 |
| 64 | x | o | Hold Pedal | Not a panel control; the DP-2 pedal at the HOLD jack | Takes it: S8-11 |
| 79 | o | o | FILTER HPF | HPF CUTOFF FREQ (19) | Patch byte 18 |
| 80 | o | o | ENV1 DECAY | ENV-1 D (30) | Patch byte 29 |
| 81 | o | o | VCF ENV | VCF ENV MOD (23) | Patch byte 22 |
| 82 | o | o | VCF KEY FOLLOW | VCF KEY FOLLOW (26) | Patch byte 25 |
| 83 | o | o | ENVELOPE1 ATTACK | ENV-1 A (29) | Patch byte 28 |
| 84 | o | o | VCF ENVELOPE SEL | VCF ENV-1 / ENV-2 switch (24) | Patch byte 23 |
| 85 | o | o | ENVELOPE1 SUSTAIN | ENV-1 S (31) | Patch byte 30 |
| 86 | o | o | ENVELOPE1 RELEASE | ENV-1 R (32) | Patch byte 31 |
| 87 | o | o | VCO SYNC | VCO-2 SYNC (13) | Patch byte 11 |
| 89 | o | o | ENVELOPE2 ATTACK | ENV-2 A (34) | Patch byte 33 |
| 90 | o | o | ENVELOPE2 DECAY | ENV-2 D (35) | Patch byte 34 |
| 91 | x | o | Reverb Send Level | Not a panel control | Counted as ignored: synth8 has no reverb (section 12.2) |
| 92 | x | o | Delay Send Level | Not a panel control | Counted as ignored: synth8 has no delay (section 12.2) |
| 102 | o | o | ENVELOPE2 SUSTAIN | ENV-2 S (36) | Patch byte 35 |
| 103 | o | o | ENVELOPE2 RELEASE | ENV-2 R (37) | Patch byte 36 |
| 104 | o | o | ENVELOPE1 KEY FOLLOW | ENV-1 KEY FOLLOW (41) | Patch byte 38 |
| 105 | o | o | ENVELOPE2 KEY FOLLOW | ENV-2 KEY FOLLOW (42) | Patch byte 39 |
| 106 | o | o | ENVELOPE1 POLARITY | ENV-1 POLARITY (33) | Patch byte 32 |
| 109 | o | o | VCA LFO MOD | VCA LFO MOD, a switch of four positions (28) | Patch byte 27 |
| 110 | o | o | AMP LEVEL | VCA LEVEL (27) | Patch byte 26 |
| 118 | x | o | PORTAMENTO SW | The PORTAMENTO mode switch, Upper only, Off, On | Takes it: S8-15 |
| 119 | o | o | SOLO/POLY/UNISON | ASSIGN MODE (40) | Patch byte 37 |

The chart gives, for every one of these controllers, no range other than MIDI's 0 to 127 and no value band: the scaling and bands below are **not stated in the source** and are NeoTeletext's own.

### 7.2 The requirements

**S8-16. The 42 panel controls and their controllers.** synth8 MUST have exactly the 42 panel controls of the table below in each half, each moved by a control change of the controller the table gives, on the channel of its half (S8-2), and by a program change (S8-12), and by no other message. Forty controllers are the chart's; controllers 107 and 108 are NeoTeletext's own. The "Table" column is the parameter number in the table; the "Panel" column is the control on the instrument modelled, as the owner's manual names it. The "Kind" column names the law of S8-21 that turns the value into the control's position.

| Byte | Table | Panel control (owner's manual page) | Controller | Kind | Positions or range |
|---|---|---|---|---|---|
| 0 | 1 | LFO RATE slider (17, 18) | 29 | Slider | 0 to 10; 0.05 Hz to 40 Hz (29) |
| 1 | 2 | LFO DELAY TIME slider (17, 18) | 27 | Slider | 0 to 10; 0 to 4 seconds (29) |
| 2 | 3 | LFO WAVE FORM selector (17) | 35 | Selector of 4 | Sine, falling sawtooth, square, random |
| 3 | 4 | VCO MODULATOR LFO MOD slider (17) | 26 | Modulation slider | 0 (none) to 10 |
| 4 | 5 | VCO MODULATOR ENV MOD slider (17) | 25 | Modulation slider | 0 (none) to 10 |
| 5 | 6 and 7 | VCO MODULATOR switch (17) | 60 | Selector of 3 | VCO-1, BOTH, VCO-2 |
| 6 | 8 | PULSE WIDTH MOD slider (17) | 18 | Slider | 0 to 10 |
| 7 | 9 | PULSE WIDTH MOD selector (17) | 19 | Selector of 3 | LFO, MANUAL, ENV-1 |
| 8 | 10 | VCO-1 CROSS MOD slider (15) | 59 | Slider | 0 to 10 |
| 9 | 11 | VCO-1 RANGE selector (15) | 20 | Selector of 4 | 16′, 8′, 4′, 2′ |
| 10 | 12 | VCO-1 WAVEFORM selector (15, 16) | 46 | Selector of 4 | Triangle, sawtooth, pulse, square |
| 11 | 13 | VCO-2 SYNC switch (16) | 87 | Switch | Off, on |
| 12 | 14 | VCO-2 NORMAL / LOW FREQ switch (16) | 63 | Switch | Normal, low frequency |
| 13 | 15 | VCO-2 RANGE knob, in half steps (16) | 62 | Selector of 37 | 16′ and the 36 semitones above it to 2′ |
| 14 | 16 | VCO-2 FINE TUNE knob (16) | 56 | Centred knob | −50 to +50 cents (16, 29) |
| 15 | 17 | VCO-2 WAVEFORM selector (16) | 61 | Selector of 4 | Sine, sawtooth, pulse, noise |
| 16 | 18 | SOURCE MIX, VCO-1's level (18) | 16 | Slider | 0 to 10 |
| 17 | 18 | SOURCE MIX, VCO-2's level (18) | 17 | Slider | 0 to 10 |
| 18 | 19 | HPF CUTOFF FREQ slider (18) | 79 | Slider | 0 (low) to 10 (high) |
| 19 | 20 | VCF CUTOFF FREQ slider (19) | 3 | Slider | 0 to 10 |
| 20 | 21 | VCF RES slider (19) | 9 | Slider | 0 to 10 |
| 21 | 22 | VCF SLOPE switch (19) | 13 | Switch | −24 dB an octave, −12 dB an octave |
| 22 | 23 | VCF ENV MOD slider (19) | 81 | Modulation slider | 0 (none) to 10 |
| 23 | 24 | VCF ENV-1 / ENV-2 switch (19) | 84 | Switch | Envelope 1, envelope 2 |
| 24 | 25 | VCF LFO MOD slider (19) | 28 | Modulation slider | 0 (none) to 10 |
| 25 | 26 | VCF KEY FOLLOW slider (19) | 82 | Modulation slider | 0 (none) to 10; 0 to 120 per cent (29) |
| 26 | 27 | VCA LEVEL slider (20) | 110 | Slider | 0 (silent) to 10 |
| 27 | 28 | VCA LFO MOD switch (20) | 109 | Selector of 4 | 0, 1, 2, 3 |
| 28 | 29 | ENV-1 A slider (20, 21) | 83 | Slider | 1 ms to 5 s (29) |
| 29 | 30 | ENV-1 D slider (20, 21) | 80 | Slider | 1 ms to 10 s (29) |
| 30 | 31 | ENV-1 S slider (20, 21) | 85 | Slider | 0 to 100 per cent (29) |
| 31 | 32 | ENV-1 R slider (20, 21) | 86 | Slider | 1 ms to 10 s (29) |
| 32 | 33 | ENV-1 POLARITY switch (21) | 106 | Switch | Normal, inverted |
| 33 | 34 | ENV-2 A slider (20, 21) | 89 | Slider | 1 ms to 5 s (29) |
| 34 | 35 | ENV-2 D slider (20, 21) | 90 | Slider | 1 ms to 10 s (29) |
| 35 | 36 | ENV-2 S slider (20, 21) | 102 | Slider | 0 to 100 per cent (29) |
| 36 | 37 | ENV-2 R slider (20, 21) | 103 | Slider | 1 ms to 10 s (29) |
| 37 | 40 | ASSIGN MODE buttons (12) | 119 | Selector of 4 | Poly-1, Solo, Unison, Poly-2 |
| 38 | 41 | ENV-1 KEY FOLLOW switch (21) | 104 | Switch | Off, on |
| 39 | 42 | ENV-2 KEY FOLLOW switch (21) | 105 | Switch | Off, on |
| 40 | 43 | VCO-1 BEND switch of the bender panel (14, 30) | **107** (NeoTeletext's own) | Switch | Off, on |
| 41 | 44 | VCO-2 BEND switch of the bender panel (14, 30) | **108** (NeoTeletext's own) | Switch | Off, on |

- Reason: The panel is the instrument's, and the patch holds what the table numbers as the original's patch parameters, less the arpeggio's two (table 38 and 39), which synth8 does not build (section 12.3). Forty controller numbers are the chart's, as DEC-6453 requires. The table numbers the two bend switches among the original's parameters (43 and 44) and today's patch holds them, but the chart has no controller for them, so they take two controllers that MIDI 1.0 leaves undefined and the chart does not use; 107 and 108 are the first two such after the chart's 106. The table's parameters 6 and 7, two enable flags on the SYSTEM-8, are on the original one switch of three positions, which the chart's controller 60 names; one controller sets both.
- Source: The chart, controller rows. The table, "Parameter List" and "Controller Map". Owner's manual, printed pages 12 to 21, 29 and 30, as cited in each row. synth8's source, `patch.rs` (today's 43 bytes, whose order this keeps). Controllers 107 and 108: NeoTeletext's own (section 13 item 7); MIDI 1.0 (to be checked) for their being undefined.
- Verification: A test sends, for each of the 42 controllers on channel 1, a control change and checks that exactly that control of the upper patch changes and no other, and the same on channel 2 for the lower; a test sends every controller from 0 to 127 that this table and S8-8 to S8-15 do not name and checks each is counted as ignored; an assertion in the code checks that no controller appears twice among the 42 and the performance controllers.

**S8-21. The laws of the values.** synth8 MUST turn a value v (0 to 127) into a control's position by the law of its kind:
1. **Slider.** The position is `v ÷ 127` of the slider's travel: 0 at its bottom, 127 at its top. Where the instrument keeps a slider as a byte of 0 to 255, as today, the byte MUST be `floor((v × 255 + 63) ÷ 127)` (0 gives 0, 64 gives 129, 127 gives 255).
2. **Modulation slider** (bytes 3, 4, 22, 24 and 25). The position is `v ÷ 127` of the slider's travel from no modulation at 0 to the most at 127, in the direction the instrument modelled has. Where the instrument keeps such a control as today's signed byte (128 meaning none), the byte MUST be `128 + v`. Values cannot express the inverted half that today's patch allows (open question 3).
3. **Centred knob** (byte 14, VCO-2 FINE TUNE). Value 64 is the centre, 0 cents. Below it the position is `−(64 − v) ÷ 64` of the knob's travel to its left end, −50 cents at value 0; above it `(v − 64) ÷ 63` to its right end, +50 cents at value 127. As today's signed byte, the byte MUST be `128 − 2 × (64 − v)` for v below 64 and `128 + floor(((v − 64) × 127 + 31) ÷ 63)` for v from 64.
4. **Selector of n positions.** The position, counted from 0 in the order the table of S8-16 lists them, is `floor(v × n ÷ 128)`; the canonical value of position p is `ceil(p × 128 ÷ n)`, the lowest value of its band. The bands are:
   - n = 3 (bytes 5 and 7): values 0 to 42 position 0; 43 to 85 position 1; 86 to 127 position 2. Canonical values 0, 43, 86.
   - n = 4 (bytes 2, 9, 10, 15, 27 and 37): values 0 to 31 position 0; 32 to 63 position 1; 64 to 95 position 2; 96 to 127 position 3. Canonical values 0, 32, 64, 96.
   - n = 37 (byte 13, VCO-2 RANGE, position p being p semitones above 16′): the table of S8-30.
5. **Switch.** Values 0 to 63 are the first position the table of S8-16 lists, and 64 to 127 the second. Canonical values 0 and 127.
- Reason: The chart gives no range or band for any controller. These laws make every value 0 to 127 a position of its control, so that no value is an error; divide a selector's values into bands as nearly equal as its positions allow; follow MIDI 1.0's rule that a switch controller is on from 64; and keep the units the instrument is built in, so that the laws of `law.rs` stand unchanged behind them. A slider's 128 values are 12.7 steps for each of the ten divisions its scale is printed with (owner's manual, printed page 7: "most control references will be made to a scale of Zero to Ten"). The orders of the selectors are the owner's manual's, left to right or top to bottom as it draws and lists them, except the assign mode, which follows the order of the table's parameter 40 ("POLY1, MONO, UNISON, POLY2"), the one Roland document that orders the four.
- Source: Not stated in the chart: NeoTeletext's own (section 13 item 5). The positions: owner's manual, printed pages 12 and 15 to 21. The fine tune's range: owner's manual, printed pages 16 ("variable Range of ±50 cent from 12 o'clock position") and 29. MIDI 1.0 (to be checked) for the switch rule.
- Verification: A test checks all 128 values of each selector and switch against its bands, and each band's edges by name; checks each slider's byte at values 0, 1, 63, 64, 126 and 127; checks the fine tune's measured detune at 0, 32, 64, 96 and 127 against −50, −25, 0, +25.4 and +50 cents within 0.5 cent; and checks that every canonical value returns its own position.

**S8-30. The bands of VCO-2 RANGE (controller 62).** Position p is p semitones above 16′: 0 is 16′, 12 is 8′, 24 is 4′, 36 is 2′.

| Position | Values | Position | Values | Position | Values |
|---|---|---|---|---|---|
| 0 (16′) | 0–3 | 13 | 45–48 | 26 | 90–93 |
| 1 | 4–6 | 14 | 49–51 | 27 | 94–96 |
| 2 | 7–10 | 15 | 52–55 | 28 | 97–100 |
| 3 | 11–13 | 16 | 56–58 | 29 | 101–103 |
| 4 | 14–17 | 17 | 59–62 | 30 | 104–107 |
| 5 | 18–20 | 18 | 63–65 | 31 | 108–110 |
| 6 | 21–24 | 19 | 66–69 | 32 | 111–114 |
| 7 | 25–27 | 20 | 70–72 | 33 | 115–117 |
| 8 | 28–31 | 21 | 73–76 | 34 | 118–121 |
| 9 | 32–34 | 22 | 77–79 | 35 | 122–124 |
| 10 | 35–38 | 23 | 80–83 | 36 (2′) | 125–127 |
| 11 | 39–41 | 24 (4′) | 84–86 | | |
| 12 (8′) | 42–44 | 25 | 87–89 | | |

The canonical value of each position is the first of its band.
- Reason: VCO-2's range "covers the same pitch range as VCO-1, from 16′ to 2′. This Range control, however, is quantized so that the pitch will change in half steps": 37 positions, which S8-21 item 4 bands.
- Source: Owner's manual, printed page 16. synth8's source, `patch.rs` (`VCO2_RANGE_MAX` = 36). The bands: NeoTeletext's own (section 13 item 5).
- Verification: The test of S8-21, for this selector's 37 bands.

**S8-22. The default patch.** A half that has been given no patch, and a half whose patch is missing or refused, MUST stand at this patch: LFO RATE 0, DELAY TIME 0, WAVE FORM sine; VCO MODULATOR LFO MOD 0, ENV MOD 0, switch BOTH; PULSE WIDTH MOD 0, source MANUAL; CROSS MOD 0; VCO-1 RANGE 8′, WAVEFORM sawtooth; SYNC off; VCO-2 NORMAL, RANGE 8′, FINE TUNE centre, WAVEFORM sawtooth; VCO-1 level full, VCO-2 level 0; HPF 0; VCF CUTOFF full, RES 0, SLOPE −24 dB, ENV MOD 0, envelope 1, LFO MOD 0, KEY FOLLOW 0; VCA LEVEL at value 96, LFO MOD 0; both envelopes ATTACK 0, DECAY 0, SUSTAIN full, RELEASE 0; ENV-1 POLARITY normal; ASSIGN MODE Poly-1; both KEY FOLLOW off; VCO-1 BEND and VCO-2 BEND on. Its 42 values are in the last column of the table of S8-23.
- Reason: A half must sound something definite before a patch arrives. This is today's default (`Patch::DEFAULT`, VCO-1's sawtooth alone at 8′ through an open filter, after the owner's manual's "basic tuning patch"), carried into values; VCA LEVEL, 192 of 255 today, is the nearest value, 96 (byte 193).
- Source: synth8's source, `patch.rs` (`Patch::DEFAULT`, citing owner's manual, printed page 8, figure 1, and own choice where the drawing cannot be read).
- Verification: A test checks that a new instrument's two patches equal the 42 values of S8-23's last column, decoded, control by control.

## 8. How a control change takes effect

**S8-24. A control moves under a sounding note.** A control change of a panel control MUST take effect on the voices of its half that are sounding, as moving the control does on the instrument: a switch or a selector at once; a slider by moving towards its new place by one 256th of its travel at each tick of the instrument's control rate (its whole travel in 43 milliseconds), as `slide` does today. While no voice of the half is sounding every control is at its new place at once. A change of the assign mode releases the half's voices (S8-19).
- Reason: The instrument modelled: "Any program in memory can be edited even during live performance by moving the desired control" (owner's manual, printed page 3). A slider under a hand passes through every place between two; a step in a level or a cutoff is heard as a click. These are the slews built and measured today.
- Source: Owner's manual, printed pages 3 and 22. synth8's source, `mod.rs` (`set_patch`, `slide`, own choice of the rate) and `tests/synth8_control_sweep.rs`.
- Verification: The existing control-sweep test, driven through control changes instead of `set_patch`, holds the same bounds on the largest step of the output.

**S8-25. Order and time.** Messages MUST be applied in the order and at the times the block gives them: each at the sample `floor(time × 24 ÷ 5)` of its block (MIDI-5), and events of one tick in the order they stand in the block (MIDI-35). Two instruments given the same events at the same times MUST give the same samples, however the rendering is divided into calls.
- Reason: A stored sound must play identically for every viewer and at every loop.
- Source: Decisions A2 and A3; the architecture, MIDI-5 and MIDI-35; synth8's source, `mod.rs` (the documentation of `Synth8`: "rendered in calls of any lengths give the same samples").
- Verification: A test renders one score with panel control changes on both channels in calls of 1, 7, 960 and 4,800 samples and checks the samples identical.

**S8-26. After a lost block.** When the receiver tells synth8 that input was lost (MIDI-102 says when), synth8 MUST release every voice, those the hold kept too, put the hold off, and set every channel's registered and non-registered parameter number selection to none (MIDI-76, S8-31), and MUST leave both patches, the VCO bend depth, every panel control, the key mode, the wheel, the bender, the volume, expression, balance and portamento where they stand.
- Reason: A lost block may have held a note off; it may equally have held control changes, which cannot be known, so the panel is left and the server's next restatement (S8-29 item e; MIDI-93 to MIDI-96) restores it. A data entry whose parameter number was lost would go to the wrong parameter, so the selection is cleared; the server selects again before every data entry (MIDI-37).
- Source: DEC-6410 item 12; the architecture, MIDI-76 and MIDI-102; synth8's source, `mod.rs` (`release_all`) and `analogue.rs` (`conceal`).
- Verification: The existing test `a_live_sound_of_each_synthesizer_plays_and_a_lost_block_releases_its_notes` passes for synth8, extended with a data entry after the loss that must change nothing (MIDI-102).

## 9. What a synth8 patch is

**S8-23. The patch: 42 values in a fixed order.** A synth8 patch MUST be exactly 42 bytes, each a control change's value from 0 to 127, in the order of the table below, which is the order of the table's parameter numbers. The patch carries no status byte, no channel, no controller number, no name and no length: byte k is always the value of the controller the table gives for byte k. One patch is one half's panel; which half it plays is chosen by the channel of the program change that selects it (S8-12). A sender MUST write the canonical value of each control (S8-21). A receiver MUST accept every patch whose 42 bytes are each 0 to 127, whatever their values, and MUST set the half's panel from it exactly as the 42 control changes would, all at one instant; a patch with a byte above 127, or of another length, is not a patch, and the half then stands at the default patch (S8-22) and the fault is counted.

| Byte | Panel control | Controller | Value in the default patch |
|---|---|---|---|
| 0 | LFO RATE | 29 | 0 |
| 1 | LFO DELAY TIME | 27 | 0 |
| 2 | LFO WAVE FORM | 35 | 0 (sine) |
| 3 | VCO LFO MOD | 26 | 0 |
| 4 | VCO ENV MOD | 25 | 0 |
| 5 | VCO MODULATOR switch | 60 | 43 (BOTH) |
| 6 | PULSE WIDTH MOD | 18 | 0 |
| 7 | PULSE WIDTH MOD source | 19 | 43 (MANUAL) |
| 8 | CROSS MOD | 59 | 0 |
| 9 | VCO-1 RANGE | 20 | 32 (8′) |
| 10 | VCO-1 WAVEFORM | 46 | 32 (sawtooth) |
| 11 | VCO-2 SYNC | 87 | 0 (off) |
| 12 | VCO-2 LOW FREQ | 63 | 0 (normal) |
| 13 | VCO-2 RANGE | 62 | 42 (8′) |
| 14 | VCO-2 FINE TUNE | 56 | 64 (centre) |
| 15 | VCO-2 WAVEFORM | 61 | 32 (sawtooth) |
| 16 | VCO-1 LEVEL | 16 | 127 |
| 17 | VCO-2 LEVEL | 17 | 0 |
| 18 | HPF CUTOFF | 79 | 0 |
| 19 | VCF CUTOFF | 3 | 127 |
| 20 | VCF RESONANCE | 9 | 0 |
| 21 | VCF SLOPE | 13 | 0 (−24 dB) |
| 22 | VCF ENV MOD | 81 | 0 |
| 23 | VCF ENVELOPE SEL | 84 | 0 (envelope 1) |
| 24 | VCF LFO MOD | 28 | 0 |
| 25 | VCF KEY FOLLOW | 82 | 0 |
| 26 | VCA LEVEL | 110 | 96 |
| 27 | VCA LFO MOD | 109 | 0 (position 0) |
| 28 | ENV-1 ATTACK | 83 | 0 |
| 29 | ENV-1 DECAY | 80 | 0 |
| 30 | ENV-1 SUSTAIN | 85 | 127 |
| 31 | ENV-1 RELEASE | 86 | 0 |
| 32 | ENV-1 POLARITY | 106 | 0 (normal) |
| 33 | ENV-2 ATTACK | 89 | 0 |
| 34 | ENV-2 DECAY | 90 | 0 |
| 35 | ENV-2 SUSTAIN | 102 | 127 |
| 36 | ENV-2 RELEASE | 103 | 0 |
| 37 | ASSIGN MODE | 119 | 0 (Poly-1) |
| 38 | ENV-1 KEY FOLLOW | 104 | 0 (off) |
| 39 | ENV-2 KEY FOLLOW | 105 | 0 (off) |
| 40 | VCO-1 BEND | 107 | 127 (on) |
| 41 | VCO-2 BEND | 108 | 127 (on) |

- Reason: Decision A4: the instrument modelled has no patch format that any filed document describes (its memories go to tape as "a complex series of pitched pulses", owner's manual, printed page 23, with no format given), and the chart lists no system exclusive, so a patch is the list of its interface's control-change values. The order is the table's, which is today's patch's, so that the two can be compared byte by byte. Values alone are carried because the order is fixed. Every byte from 0 to 127 is a position of its control (S8-21), so a receiver has no range to check beyond the top bit, and a patch cannot hold a value the instrument cannot take.
- Source: Decision A4 and DEC-6453 item 3. The order and the form: NeoTeletext's own (section 13 item 8). The table, "Parameter List".
- Verification: A test decodes the default patch's 42 bytes and compares each control with S8-22; a test checks, for every byte position and every value 0 to 127, that the patch is accepted and that the control is what the control change of that controller and value gives; a test checks that a patch of 41 or 43 bytes, and one with any byte of 128 or more, is refused and the default patch plays; a test checks that a patch applied at an instant equals the same 42 values sent as 42 control changes on the half's channel at that instant.

**S8-27. The same patch as control changes.** The sequence of 42 control changes that a patch stands for, for the upper half, MUST be, in the patch's byte order, `0xB0, controller, value` for each byte, where `controller` is the table's for that byte; for the lower half the status byte is `0xB1`. A program that wishes to set a whole panel in a stream without a bank MAY send that sequence; synth8 takes it by S8-16, and after the last of them the half's panel equals the patch.
- Reason: The patch and the live messages are one definition, so that a panel can be set by either and the server can turn one into the other with the table alone.
- Source: S8-16, S8-2, S8-23.
- Verification: The last test of S8-23.

**S8-28. The instrument's patch memory and the program numbers.** The program number of a patch MUST correspond to the instrument modelled's patch number as `program = (tens − 1) × 8 + (units − 1)`, where the patch number's tens and units are each 1 to 8: patch 11 is program 0, patch 18 program 7, patch 21 program 8, patch 88 program 63. A tool that shows patch numbers to a person SHOULD show them in the instrument's form, 11 to 88; the server's typed interface (DEC-6462) MAY accept a patch number in that form beside the program number, converting it by this formula.
- Reason: The instrument modelled has 64 patch memories selected by two digits, each 1 to 8: "patch positions numbering 11-18, 21-28, 31-38, 41-48, 51-58, 61-68, 71-78 and 81-88. These may be thought of as positions 1 to 8 in banks of the 'teens, twenties, and so on". Taking them in that order onto programs 0 to 63 keeps a factory sheet's patch number findable.
- Source: Owner's manual, printed pages 9 and 10 (figure 2, the grid of 11 to 88) and 30 ("Patch number button (64 memory)"). The correspondence to program numbers: NeoTeletext's own (section 13 item 4).
- Verification: A test converts every patch number 11 to 88 to its program and back and checks the 64 pairs, and that the numbers 19, 20, 29, 90 and 10 are refused.

**S8-29. What synth8 needs of the bank, the block, the codec and the restatement.** The architecture specifies the bank, the block, the codec and the restatement; synth8's needs of them, and its part of each, are these.
- (a) **The bank.** A synth8 bank image is of the fixed-patches form (MIDI-56 item 2): 1 to 64 patches of 42 bytes each (S8-23) back to back, patch k at byte `k × 42`, numbered from 0: at most 2,688 bytes, within the bank codec's 16,384 (MIDI-55). Both halves choose from bank index 0, the first bank the sound names (S8-12); synth8 has no bank select (MIDI-64), so a sound naming more than one bank (MIDI-57 allows 1 to 10) reaches only the first.
- (b) **Program change.** A program change's data byte, 0 to 63, is the patch's number in bank index 0; 64 to 127 name no patch and set the default (S8-12, MIDI-59).
- (c) **The block.** synth8's blocks are the architecture's event lists (MIDI-23 to MIDI-38): at most 1,005 bytes and 256 events a block. No synth8 message is longer than three bytes, since synth8 takes no system exclusive; a system exclusive event in a synth8 block is counted as ignored (MIDI-34). A whole panel as control changes (S8-27) is 42 messages, 126 bytes with every status byte written, and both panels 84 messages, 252 bytes, which fit one block. The server writes every control change with its status byte (MIDI-12).
- (d) **The OBJECT.** A synth8 sound's OBJECT carries its key mode and split point in extension tag 7, as today (S8-18, MIDI-48); no MIDI message replaces it, because the chart has none for a key mode.
- (e) **The restatement.** The server, not the program and not a kit, restates synth8's state, as MIDI-93 to MIDI-99 require of every synthesizer: in the first block of a live sound and at least once in every 50 blocks after (MIDI-96), and at tick 0 of block 0 of every stored sound (MIDI-99). synth8's restatement is, for each half, written whole at one tick of one block (MIDI-98): on channel 1 for the upper half, the program change of its patch, then the latest value of every panel controller moved since by a control change, in ascending order of controller number (MIDI-95); then the same on channel 2 for the lower half. The performance controls, which are the whole instrument's, are restated with the upper half on channel 1, each only where it is not at its value after reset all controllers (MIDI-84) or at its start value: pitch bend, controller 1, controller 5, controller 7, controller 8, controller 11, controller 64, controller 118, and the VCO bend depth (as controller 41 where it was last set by controller 41, or as registered parameter number 0, controllers 101, 100, 6 and 38, followed by 101 and 100 at 127 to select none, where it was last set so). Held notes are not restated (MIDI-93). The restatement of one half is at most 42 control changes and a program change, 128 bytes, and the performance controls at most 15 messages more, so a whole restatement is well within one block. By S8-12 and S8-24, a restatement that carries the state the receiver already holds changes nothing that is heard (MIDI-97).
- (f) **The codec.** synth8's sounds are of codec 17 and its banks of the bank codec 19, if the architecture's open question 1 is answered as it recommends (MIDI-107 to MIDI-109); otherwise synth8's sounds keep their present code, 9, and its banks the present analogue bank code, 11 (`codec.rs`, `Codec::Synth8`, `Codec::PatchBank`). This document does not decide it.
- Reason: The instrument modelled holds 64 patches; the program numbers reach them all (S8-28). The sizes are what the architecture needs to size records. The restatement is the server's under DEC-6462 item 1 ("repeats what a viewer who joins late needs").
- Source: Owner's manual, printed pages 3, 9 and 30. Decision A4. DEC-6462 items 1 and 3. The architecture, MIDI-23 to MIDI-38, MIDI-48, MIDI-55, MIDI-56, MIDI-59, MIDI-93 to MIDI-99 and MIDI-107 to MIDI-109.
- Verification: A test stores a bank of 64 patches, plays program changes to each on both channels, and checks both panels; a server test drives both halves through a program change, ten panel control changes, a bend, the hold and a bend depth, plays the restatement into a fresh synth8, and checks the two states equal (MIDI-93); a server test checks block 0 of a stored synth8 sound begins with both halves' restatements; the architecture's tests cover the carriage.

---

## 10. The panel against the chart, the other way round

### 10.1 Controls synth8 has that the chart lacks

1. **VCO-1 BEND and VCO-2 BEND switches** (patch bytes 40 and 41). The table numbers them among the original's parameters (43 and 44); the chart has no controller. NeoTeletext's controllers 107 and 108 (S8-16).
2. **The portamento time** (controller 5, S8-15). The instrument's rotary PORTAMENTO knob (owner's manual, printed page 14). The chart has the switch (118) and no time.
3. **The balance** (controller 8, S8-10). The instrument's BALANCE knob (printed pages 11 and 29).
4. **The upper-only position of the portamento switch** (printed page 14). synth8 holds it (`Portamento::UpperOnly`) but no message reaches it (section 12.3).
5. **The bender panel's VCF bend depth, LFO VCO depth and LFO VCF depth** (S8-14). synth8 holds them; no message sets them (section 13 item 11, open question 4).
6. **The key mode and the split point** (S8-18), set by the OBJECT record.
7. **Two patches** addressed by channel (S8-2). The chart has one basic channel.

### 10.2 Messages and controls the chart has that synth8 lacks or does not take

1. **Note-on velocity** (recognised by the chart): ignored, S8-3.
2. **Polyphonic key pressure** (recognised by the chart): ignored, S8-6.
3. **Controller 10, Pan; controller 91, Reverb Send Level; controller 92, Delay Send Level**: counted as ignored. synth8 is mono (DEC-6410 item 2) and has no effects.
4. **Controller 57, VCO-2 MODE**: counted as ignored; its meaning is not stated in the source and no control of the instrument modelled bears the name (open question 2).
5. **The table's SYSTEM-8 positions that the instrument modelled lacks**, which the JUPITER-08's controllers may have (open question 1): LFO waves TRI and a second random (RND2); VCO ranges 64′ and 32′; VCO-1 waves PWM, SIN and NOISE as separate choices; VCO-2 waves TRI and SQR; VCO-2's ±36 semitone "Sub Range" beside its six footages; PWM sources ENV1−, ENV2+ and ENV2−; the −18 dB slope. synth8 has none of them, as the instrument modelled has none.
6. **The table's bipolar ranges** (−128 to +127) for VCO LFO MOD, VCO ENV MOD, VCF ENV MOD, VCF LFO MOD, VCF KEY FOLLOW and VCA LFO MOD: the instrument modelled's sliders run one way only (printed pages 17, 19 and 20), and its VCA LFO MOD is a switch of four positions (printed pages 20 and 29). Open question 3.

### 10.3 Controls of the instrument modelled that neither the chart nor synth8 has

Listed with their reasons in section 12.3: the arpeggio section; the LFO MOD touch pad's ON/OFF and its RISE TIME knob; MASTER TUNE and the TUNE button; the HOLD LOWER and UPPER selectors; the PANEL MODE buttons (the channel stands in, S8-2); the patch number, MANUAL, WRITE and PATCH PRESET buttons and memory protect; the tape memory; the outputs, their level switch and the phones; the external control jacks; the highest-note outputs.

## 11. Patch memory and patch presets of the instrument modelled

**The facts in the owner's manual.**
1. The instrument "has the capacity to store and recall the exact synthesizer settings for up to sixty-four different patch programs" (printed page 3), numbered 11 to 88 by two digits of 1 to 8 (printed page 9).
2. "Every one of the synthesizer controls just described can be written into the Jupiter-8's Patch memories" (printed page 22): the synthesizer section, "all controls to the right of the Arpeggio rate controls and above the row of switches" (printed page 15).
3. Eight patch presets, A to H, each recall "two patches and key mode at one" (printed page 11): "these memories are pairs of numbers referring to patches within the 64 available Patch memories, not a separate set of patches" (printed page 24).
4. A MANUAL button gives the panel's own settings; an edit moves a control off its stored value without rewriting the memory, and WRITE stores it, unless MEMORY PROTECT is on (printed pages 7, 21 and 22).
5. The tape memory saves, verifies and loads the 64 patches and 8 presets as audio, with a file number (printed page 23); its format is not given.

**What synth8 takes of it.** The 64 patches become the bank of up to 64 and program numbers 0 to 63 (S8-28, S8-29). The two halves each choose from it (S8-12), as Upper and Lower each take a patch number on the instrument. The patch presets are not taken (section 12.3, open question 5): a preset is two patch numbers and a key mode, which a sender expresses as two program changes, and the key mode is the OBJECT's. Writing, protection and tape serve only the hardware.

## 12. What is left out, and what departs

### 12.1 Of the chart: left out

| Item of the chart | Why synth8 leaves it out |
|---|---|
| The Basic Channel setting, 1 to 16, "Changed" | A setting of the hardware with no message; synth8 uses channels as S8-2 says. |
| Everything transmitted (notes, velocity, 41 controllers) | synth8 transmits nothing: a NeoTeletext instrument only receives. |
| Controller 10, Pan | synth8 is mono (DEC-6410 item 2). |
| Controllers 91 and 92, reverb and delay sends | synth8 has no reverb and no delay; the instrument modelled has neither. |
| Controller 57, VCO-2 MODE | Its meaning is not stated in the source (open question 2). |

### 12.2 Of the chart: taken with a difference

| Item | The chart | synth8 | Requirement |
|---|---|---|---|
| Channel | One basic channel, mode 3 | Notes on every channel; panel controls on 1 (upper) and 2 (lower) | S8-2 |
| Note-on velocity | Recognised | Ignored, as the instrument modelled has none | S8-3 |
| Polyphonic key pressure | Recognised | Ignored, as the instrument modelled has none | S8-6 |
| Controller 7 | "PATTERN PART LEVEL" | The instrument's VOLUME, a gain beside the patch | S8-9 |
| Controller 41 | "BEND PITCH" | The VCO bend depth | S8-14 |
| Mode messages 120, 121, 123 to 127 | Not recognised ("Mode, Messages: x") | Taken, as NeoTeletext's common layer, by the architecture's one rule for each (section 12.4) | S8-13 |
| Controller 64, Hold Pedal | Recognised, values not stated | On at 64 to 127, holding the whole keyboard in every key mode | S8-11 |
| Registered parameter number 0 | No row | Sets the VCO bend depth beside controller 41 | S8-31 |
| Every panel controller | No range, no bands | NeoTeletext's laws and bands | S8-21 |

### 12.3 Of the instrument modelled: what synth8 does not have

| Control or function | Owner's manual | Why not |
|---|---|---|
| The arpeggio: RATE (1 Hz to 20 Hz), RANGE 1 to 4, MODE up, down, up and down, random, the internal or external clock and its 3-position beat switch, the clock jack and DIN connection; and the table's parameters 38 and 39 | Printed pages 6, 12, 13, 29 and 30 | Not built. The chart has no controller for any of it. Adding it is a new feature for the owner to ask for. |
| The LFO MOD touch pad (ON/OFF) and its RISE TIME knob | Printed pages 14 and 30 | The modulation wheel stands in for the pad (S8-8); the rise is the sender's to shape with the wheel. As built. |
| The VCO MOD and VCF MOD switches of the LFO modulation, and the VCF BEND switch | Printed pages 14 and 30 | The depths of S8-14 at 0 stand for a switch off. As built. |
| The portamento switch's UPPER ONLY position | Printed page 14 | The chart's controller 118 is a switch of two positions; synth8 holds the position but no message reaches it. |
| MASTER TUNE (±50 cents) and the TUNE button (computer tune) | Printed pages 9 and 29 | synth8 is in tune by construction; a sound's pitch is the sender's. |
| The HOLD LOWER and UPPER selectors | Printed page 13 | The hold is the pedal alone (S8-11). As built. |
| The hold pedal holding only the lower half in the split key mode | Printed page 13 | The architecture's one rule for the sustain pedal (MIDI-87) holds every key in every synthesizer; open question 7. |
| The PANEL MODE Lower and Upper buttons | Printed pages 11 and 30 | The channel of a control change stands in for them (S8-2). |
| The patch number buttons, MANUAL, WRITE, MEMORY PROTECT and the patch presets A to H | Printed pages 9, 11, 21 and 22 | Operations of the hardware's memory; a patch is chosen by program change; presets: section 11. |
| The tape memory: SAVE, VERIFY, LOAD, DATA CHECK, file numbers | Printed pages 7, 23 and 24 | Hardware only; its format is not given. |
| The outputs (Upper, Lower, Mix; balanced and unbalanced), the output level switch, the phones and their level | Printed pages 4, 5 and 30 | synth8 has one mono output, the Mix (DEC-6437 item 2, as cited in `mod.rs`). |
| The external control jacks (Hold, Portamento, VCF, VCA) | Printed pages 5, 6 and 30 | No outside voltage reaches a NeoTeletext instrument; the hold is controller 64 and portamento controller 118. |
| The highest-note CV and gate outputs | Printed pages 6 and 30 | synth8 transmits nothing. |

### 12.4 The common MIDI behaviours: the chart's departures

The architecture sets one rule for every synthesizer where MIDI defines a behaviour common to all instruments (its section 11.1, MIDI-84 to MIDI-92), at the owner's requirement (DEC-6464). synth8 follows each rule; this table lists where the chart departs from it or is silent, and the requirement that gives synth8's behaviour.

| Behaviour | The chart | synth8, by the architecture's rule | Requirement |
|---|---|---|---|
| Reset all controllers (121) | Not recognised ("Mode, Messages: x"; no row for 121) | RP-015 as DEC-6464 understands it (DEC-6464 proposed, awaiting the owner's confirmation): wheel 0, expression 127, hold off, bender centred, parameter number selection none; volume and everything else unchanged | MIDI-84; S8-13 item 2 |
| All notes off (123) | Not recognised | Every key released as note offs; the hold still holds | MIDI-85; S8-13 item 3 |
| All sound off (120) | Not recognised | Silence within 1,024 samples by a fade (synth8: 256) | MIDI-86; S8-13 item 1 |
| Sustain, controller 64 | "Hold Pedal", recognised, values not stated | Down at 64 to 127, up at 0 to 63; holds the whole keyboard in every key mode | MIDI-87; S8-11 |
| Note on of velocity 0 | Not stated | A note off | MIDI-88; S8-3 |
| Omni off, omni on, mono on, poly on (124 to 127) | Mode 3 by default; "Mode, Messages: x", "Mode, Altered: x" | Each acts as all notes off and nothing else | MIDI-89; S8-13 item 4 |
| Pitch bend range | Controller 41, "BEND PITCH", not explained | Controller 41 and registered parameter number 0 set the same VCO bend depth, the last received holding, at most 12 semitones, default 2 | MIDI-90; S8-14, S8-31 |
| Pitch bend resolution | Recognised, resolution not stated | All 14 bits | MIDI-91; S8-7 |
| Volume, controller 7 | "PATTERN PART LEVEL", recognised | The volume, by MIDI-82's law, 127 full | MIDI-92; S8-9 |

## 13. What NeoTeletext defines itself

Each item exists because the filed chart does not define it.

1. **All sixteen channels as one keyboard (S8-2 items 1 to 3).** The chart has one basic channel; synth8 hears notes and performance controls on every channel, as built.
2. **Channels 1 and 2 for the upper and lower panels and program changes (S8-2 items 3 to 5).** The chart has one part; the instrument has two patches and a panel mode.
3. **Controller 8 (balance) and controller 5 (portamento time), with their laws (S8-10, S8-15).** The instrument has both controls; the chart has no controller for either. MIDI 1.0's own controllers for those purposes, as built.
4. **Program change and its numbering against patches 11 to 88 (S8-12, S8-28).** The filed chart has no program change row; the instrument has no MIDI.
5. **The laws and value bands of every controller (S8-21, S8-30), and the scaling of controller 41 (S8-14).** The chart gives none.
6. **The split point as a key of the OBJECT (S8-18).** The owner's manual's instrument splits at one fixed key; a variable point is built and kept.
7. **Controllers 107 and 108 for the two bend switches (S8-16).** The table makes them part of the original's patch; the chart has no controller.
8. **The patch as 42 values in the table's order (S8-23), and its equivalence to 42 control changes (S8-27).** No patch format exists in any filed document.
9. **The pitch of a MIDI key (S8-5).** As built.
10. **The modulation wheel as the LFO modulation, and its linear law (S8-8).** As built.
11. **The bender panel's depths without messages, but for controller 41 (S8-14).** As built: today no message sets any depth. Adding controllers for the other three is open question 4.
12. **Controllers 120, 121 and 123 to 127 (S8-13).** Standard MIDI 1.0 messages the chart does not recognise, taken as NeoTeletext's common layer with the architecture's one rule for each (MIDI-84 to MIDI-89); 120, 121 and 123 as built, 124 to 127 new.
13. **Ignoring velocity and key pressure (S8-3, S8-6).** The chart recognises both; the instrument modelled has neither.
14. **The slews (S8-7, S8-9, S8-10, S8-24).** As built and measured.
15. **The default patch (S8-22).** As built.
16. **Registered parameter number 0 for the bend range, and its treatment of cents (S8-31).** The chart has no row for it; the architecture requires it in every family (MIDI-90, pending the owner's answer to its open question 5). A cents value above 99 taken as 99, and increment and decrement by one cent, are this document's (MIDI-81).
17. **The restatement of the two halves and of the performance controls (S8-29 item e).** The architecture's rule (MIDI-93 to MIDI-99) applied to synth8's two halves.

## 14. Open questions for the owner

**1. Which product is "JUPITER-08", and do its controller numbers equal the JP-08 Boutique's? (Not established by the filed documents.)**
The filed chart says "Model: JUPITER-08", "Date: October 1st, 2026", "Version: 1.01", and nothing more about the product. The filed documents do not say whether it is Roland's 2015 JP-08 Boutique module, a later hardware or software product, or a part ("PATTERN PART LEVEL") of a larger instrument; nor whether the JP-08's controller numbers equal these. If they are a different product's, the Boutique's chart, which more tools and players will have met, could be the better-known interface under DEC-6453.
- *What would settle it:* filing, under DEC-6428 step 1, (a) the rest of the reference manual the chart belongs to (the page's own address is `jupiter-08_reference_v100/…`: its title page, its product description, its parameter list with each controller's range and value bands, and the rows of the chart that the filed part leaves out, among them program change and system exclusive); and (b) Roland's MIDI implementation chart and parameter list for the JP-08 Boutique (2015). Comparing the two charts row by row answers the second question; the reference manual's parameter list replaces S8-21's bands with Roland's wherever it states them, and may say what controllers 41 and 57 do.
- *Option A:* file both and revise sections 7 and 9 to them before the interface is built.
- *Option B:* build to this document now, and revise if the filed documents later differ.
- *Recommendation:* A. The controller numbers here would very likely stand, but the bands of six selectors (whose SYSTEM-8 lists in the table have six entries where the instrument has three or four) and two controllers' meanings depend on it, and changing bands after patches exist breaks them.

**2. What do controllers 41 "BEND PITCH" and 57 "VCO-2 MODE" do?**
The chart names them and says nothing more. This document takes 41 as the VCO bend depth (S8-14) and counts 57 as ignored.
- *Option A:* as this document, until open question 1's documents say.
- *Option B:* take 41 as a pitch-bend range in semitones (a common meaning on other instruments), and 57 as VCO-2's NORMAL / LOW FREQ switch.
- *Recommendation:* A. Option B's 57 would give one switch two controllers (63 is "VCO-2 LO FREQ"), and the semitone reading of 41 is not in any filed document. Under either option the bend range is also set by registered parameter number 0 (S8-31, MIDI-90), so a sender that wants a range in semitones has the standard message for it.

**3. Should the five modulation sliders and VCA LFO MOD keep their inverted half?**
Today's patch keeps VCO LFO MOD, VCO ENV MOD, VCF ENV MOD, VCF LFO MOD, VCF KEY FOLLOW and VCA LFO MOD as signed bytes, after the table's −128 to +127, though the instrument's sliders run one way and its VCA LFO MOD is a four-position switch.
- *Option A (this document):* each modulation slider is 0 (none) to 127 (most) in the instrument's direction; VCA LFO MOD is four bands. The inverted half is dropped.
- *Option B:* each is centred at 64, 0 to 63 being the inverted half, as the table's range suggests; a sender who moves a controller from its bottom then starts at the inverted most, not at none.
- *Recommendation:* A. It is the instrument's panel, value 0 is none as for every other slider, and ENV-1 POLARITY already inverts the envelope's modulation. If open question 1's documents show the JUPITER-08's controllers are centred, B follows them.

**4. Should the bender panel's other three depths have controllers?**
The VCF bend depth, LFO VCO depth and LFO VCF depth have no message today and none in the chart; they stay at 0, 50 cents and 0.
- *Option A (this document):* no controllers; the depths stay at their defaults.
- *Option B:* three NeoTeletext controllers (for example 111, 112 and 113, undefined in MIDI 1.0 and unused by the chart), with the VCF and LFO switches as depth 0.
- *Recommendation:* A for now. A sound cannot reach the filter from the bender or the wheel, which the instrument can; if the owner wants those, B, as additions listed in section 13.

**5. Should a program change recall a patch preset?**
- *Option A (this document):* no; a sender sends a program change on each channel, and the key mode stays in the OBJECT.
- *Option B:* program changes 64 to 71 on channel 1 recall presets A to H stored with the bank, each two patch numbers and a key mode; the key mode would then change mid-sound, which today only the OBJECT can do, and a viewer joining late would need it repeated.
- *Recommendation:* A. A preset is "pairs of numbers referring to patches" (printed page 24), which two program changes already express.

**6. Is 128 steps enough for a slider?**
Today a slider is a byte of 256 steps; a control change carries 128. The table's ranges are 0 to 255.
- *Option A (this document):* 128 steps, the chart's own form, 12.7 steps for each printed division of the slider.
- *Option B:* NeoTeletext's own pairs or non-registered parameter numbers for 256 steps, which the chart does not have and DEC-6453 discourages.
- *Recommendation:* A.

**7. Should the hold hold only the lower half in the split key mode, as the instrument modelled does?**
The owner's manual says the hold pedal acts "on the Lower end of the keyboard only" in split (printed page 13), and what is built does so; the architecture's one rule for the sustain pedal (MIDI-87) holds every key in every synthesizer, and this document now follows it (S8-11).
- *Option A (this document):* the architecture's rule: in every key mode the hold holds the whole keyboard, so a performance's pedal means the same on every synthesizer.
- *Option B:* the instrument's behaviour, listed as a departure from MIDI-87, which the architecture would then have to allow.
- *Recommendation:* A, under the owner's requirement that every synthesizer behave the same way on behaviours common to all MIDI instruments (DEC-6464); B only if the owner counts the split hold as part of the instrument rather than of MIDI.

## 15. Differences from what is built today

What exists is described in `synthesizer-wire-format.html`, `programming-the-synthesizers.html` and synth8's source. Implementing this document changes the following.

**The patch.**
1. Today a patch is 43 bytes of NeoTeletext's own design (`PATCH_BYTES`, `Patch::from_bytes`, `Patch::to_bytes` in `patch.rs`): each byte 0 to 255 or 0 to its selector's maximum, signed fields offset by 128, the VCO modulator as two bytes (5 and 6), the source mixer's two levels as bytes 17 and 18. It becomes 42 bytes, each a control change's value 0 to 127 (S8-23): bytes 5 and 6 become one value of three bands (S8-16 byte 5), so the state "neither oscillator", which the instrument cannot take, is no longer expressible; sliders lose half their steps (S8-21 item 1); the six signed controls lose their inverted half (open question 3); VCA LFO MOD, a signed slider today interpolated between four positions in `voice.rs` (`LEVEL_LFO_LAW`), becomes the instrument's four positions.
2. Selectors move from 0 to their maximum (0 to 3, 0 to 2, 0 to 36, 0 or 1) to value bands (S8-21, S8-30). The assign mode's positions keep today's order (Poly-1, Solo, Unison, Poly-2).
3. Today a patch is refused for a byte above its control's maximum (`PatchError::Value`). After the change every value 0 to 127 is valid in every byte, and the only faults are the length and a byte above 127.
4. `SYNTH8_PATCH_BYTES` (`neoteletext-audio/src/codec.rs`, 43) becomes 42; the server's patch check and its refusal messages ("patch 0 byte 14 (VCO-2 RANGE) is 37: at most 36"), the kit's synth8 patch builder (`packJupiter8Patch` before the renaming), its initial patch, and the documents' "43 B" all follow. Under DEC-6462 the patch builder moves into the server, which takes named, typed fields or the 42 values.
5. A DATA record that holds 23 patches of 43 bytes today holds 24 of 42 bytes; the architecture document sizes it.
6. `Patch::set_source_mix`, which sets both levels as the instrument's one knob does, stays as a helper of the server's typed fields; on the wire the two levels are controllers 16 and 17.

**The messages.**
7. Today synth8 takes control changes of controllers 1, 5, 7, 8, 64, 65, 120, 121 and 123 only (`control_change` in `mod.rs`; `SYNTH8_CONTROLLERS` in `analogue.rs`). It gains the 42 panel controllers of S8-16 on channels 1 and 2, controller 11 (expression), controller 41 (the VCO bend depth) and controller 118 (portamento switch); controller 65 is dropped and counted as ignored. `Synth8` needs a way to set one control of one half; `set_patch` and `set_lower_patch` remain as the way a program change sets all 42.
8. Today the server and the kit refuse a control change of any controller but 1, 5, 7, 8, 64, 65, 120, 121 and 123 for synth8. The server must allow the controllers of S8-16, S8-8 to S8-15, S8-31 and S8-13, and refuse 65 (MIDI-10); the kit's copy of the rule is removed, since the kits hold no copy of a server rule beyond what the schema states (MIDI-22).
9. Today the balance acts in the whole key mode between the first four voices and the last four (`set_balance`'s documentation: "as they are in the instrument"). The owner's manual says "While in the Whole Mode, the Balance control is inoperative" (printed page 11), and in whole the Upper and Lower outputs "present the same output" (printed page 4). S8-10 follows the manual: in whole the balance does nothing.
10. Today a program change chooses patch 0 to 31 and a bank holds 1 to 32 patches. They become 0 to 63 and 1 to 64 (S8-12, S8-29). Under decision A3 a program change is the ordinary two-byte MIDI message, not a four-byte slot with a second data byte of 0.
11. Today a program change to a patch the bank lacks changes nothing, silently; after the change it sets the half to the default patch and is counted as ignored (S8-12, MIDI-59).
12. `SPLIT_DEFAULT` (key 60) says "own choice: middle C … neither page says where the fixed one lay". The owner's manual, printed page 11, places the fixed split two octaves above the lowest C of the keyboard, which is key 60 on the keyboard `law.rs` places at keys 36 to 96; its source line can cite that page.
13. Nothing changes in note on, note off, pitch bend, the modulation wheel, volume, all sound off or all notes off; the key modes, assign modes and the low-frequency oscillators (S8-18 to S8-20) are as built. These change, to follow the architecture's common behaviours: reset all controllers sets expression (controller 11) to 127, clears the parameter number selection, and leaves controller 118 and the VCO bend depth alone (S8-13, MIDI-84); controllers 124 to 127, counted as ignored today, act as all notes off (S8-13, MIDI-89); the hold holds both halves in split, where today it holds the lower half only (S8-11, MIDI-87); registered parameter number 0 and controllers 6, 38, 96 to 101 are new (S8-31, MIDI-90); a lost block also clears the parameter number selection (S8-26, MIDI-102).

**The block.**
14. Today a synth8 block is 1 to 16 slots of four bytes. Under decision A3 it becomes a Standard MIDI File track-event list with a tick of 0.1 millisecond; that change is the architecture document's and is the same for every family. synth8's part of it is only that two whole panels as control changes (84 messages, S8-27) no longer have to fit in 16 slots. The codec code changes only if the architecture's open question 1 is answered as it recommends (S8-29 item f).

**The server and the kits.**
15. Under DEC-6462 the server writes synth8's blocks, its bank images, its OBJECT's tag 7 and its restatements (S8-29); today the kit builds the patches and blocks and repeats program changes (`program-repeater.ts`), and the kit's synth8 code is reduced to the generated types and the calls that send them (MIDI-22).

**Tests and documents.**
16. The tests that build patches from bytes (`tests/synth8_patch.rs`, `tests/synth8_instrument.rs`, `tests/synth8_control_sweep.rs`, `tests/synth8_factory.rs`, `tests/synth8_support.rs` and the other `synth8_*` tests, the engine's `tests/synths.rs`, the server's and the kit's patch tests) change to the 42-value form. The factory patches that `synth8_factory.rs` sets from Roland's factory patch sheets are rewritten as values. New tests are those each requirement's "Verification" names.
17. The module documentation of `patch.rs` (the byte table) and of `mod.rs` ("# MIDI: The instrument has none: its keys, bender and pedals are mapped onto MIDI as `Synth8::event` says") are rewritten to cite this document's requirements once they are rdm requirements. The two HTML documents in `teletext-reference/synthesizers/` describe the old form and are regenerated.
18. `jupiter-8/documents.tsv`'s row for the chart and DEC-6457 say the chart gives "a control change for each panel control". It gives one for 40 of the 42 controls a patch holds (not the two bend switches), none for the arpeggio, the portamento time, the balance or the bender panel's depths, and adds nine that are not panel controls. Both are to be corrected to what the file holds.
