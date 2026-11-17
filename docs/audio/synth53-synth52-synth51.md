# synth53, synth52 and synth51: the programming interface

**Purpose.** This document specifies how synth53, synth52 and synth51 are played and programmed: every MIDI message they take, what each does, every parameter number and controller number of their interface, the system exclusive messages that carry a program, the byte layout of a program, and how each parameter becomes a control of NeoTeletext's instrument. It is the basis for implementing this family's part of the synthesizer protocols.

**Scope.** The three synthesizers that model the Sequential Circuits Prophet-5: synth53 (revision 3, the Curtis chips), synth52 (revision 2) and synth51 (revision 1), the last two one model today (`neoteletext-common/docs/audio/synthesizers.md` says once which instrument each synthesizer models). The transport (blocks, records, packets), the form of a block, how a bank of programs is stored and named, how a system exclusive message longer than a block or a record travels, the restatement of a live sound, the codec numbers, and the behaviours common to every synthesizer belong to the architecture document, `midi-architecture.md` in this folder (cited below by its requirement numbers, MIDI-1 to MIDI-125); this document states what the family needs of them, refers to them, and lists this interface's departures from them. The typed programming interface of the Rust server is the server document's; this document states what that interface must express for this family (DEC-6462). The sound of the instrument (its oscillators, filter and envelopes) is not specified here.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

**What the owner should read first.**
1. **The adopted interface is complete enough to build from.** Sequential's "Prophet-5 MIDI Implementation" 1.4 (13 pages, all read) gives every parameter of a program a parameter number (NRPN) and almost all of them a control change, gives the program dump and the edit buffer dump byte by byte, and describes the packing of eight bits into seven. With the User's Guide 1.3 (all its pages on controls, programs and settings read) it gives the meaning and the panel range of each parameter. Section 4 onwards specifies all of it.
2. **The filed document contradicts itself in eight places** (section 3.3). Each is listed with the reading this document takes and why. None stops the build; open question 4 asks whether the readings may be confirmed against the factory program banks.
3. **Today's 24-byte patch is not NeoTeletext's own design.** It is the original instrument's own program record: "40 24-byte programs", each byte a knob in its low seven bits and a switch in its top bit, as the 1982 operation manual's section 6-7, "Status 3: Save to tape", sets it out for the instrument's serial interface (operation manual CM1000D, pages 6-5 and 6-6, read for this document). DEC-6453 item 4 lists it among the invented formats to be replaced; that description is wrong. It is nevertheless replaced, because the 2020 instrument's MIDI interface is the most widely used and is the one DEC-6456 records as adopted, and because the original's format has no MIDI form at all (it travels through a non-MIDI serial port). Section 16 lists the change.
4. **The 2020 instrument adds parameters that revisions 1 to 3 never had**: velocity, aftertouch, the Vintage knob, the filter revision select, a count and detuning of unison voices, four key priority modes, half keyboard tracking, a per-program pitch wheel range, an initial amount for the low-frequency oscillator, and a chord memory. Each is placed in section 10 as built today, to be built, or left out, under the recommendation of open question 2.
5. **The Prophet-10 is not described by any filed document.** The two filed documents mention the name only in "Prophet-5/10" as a port name (User's Guide, page 4). Anything about a second layer or a ten-voice instrument is not stated in the source and is left out.
6. **Where the architecture document sets one rule for every synthesizer, this family follows it, and the adopted interface's difference is a departure** (section 4.3): reset all controllers leaves the volume unchanged (DEC-6464, against the adopted interface's "MIDI volume to maximum"); controller 7 runs 0 to 127 with 127 full, not 0 to 120; the mode messages 124 to 127 and all sound off, 120, are acted on though the adopted interface does not receive them; registered parameter number 0 sets the pitch wheel range beside controller 70 and parameter 86, and a program change does not change the range (open question 5 asks whether a program's own range may); a program dump is carried only in a bank, never applied in the middle of a sound; and a program change to a program the sound lacks plays the default program.

---

## 1. Sources

All files are under `~/devel/teletext-reference/synthesizers/prophet-5/`. Page numbers are the printed page numbers of each document. In the MIDI Implementation they equal the PDF's page numbers; in the User's Guide the printed page n is the PDF's page n + 11.

| Short name here | File | What it is used for |
|---|---|---|
| **MIDI Implementation** | `manuals/Prophet-5-MIDI-Implementation-1.4.pdf` (13 pages; "Prophet-5 MIDI Implementation", Sequential LLC, version 1.4, March 2021; SHA-256 `5b86f304…dd219a`, 575,000 bytes, per `documents.tsv`) | The adopted interface, every page. Page 1: the global settings that govern reception. Page 2: the channel messages and controllers received. Page 3: those transmitted. Pages 4 and 5: the table of control changes. Pages 6 and 7: how a parameter number (NRPN) message is formed and received. Pages 8 and 9: the table of parameter numbers. Page 10: the device inquiry. Page 11: the request messages. Page 12: the program dump, the edit buffer dump and "Save Edit Buffer". Page 13: the global parameters dump, the order of a program's bytes, and the packed data format with its example. |
| **User's Guide** | `manuals/Prophet-5-Users-Guide-1.3_rev4.pdf` (80 PDF pages; "Prophet-5 User's Guide", version 1.3, February 2021, Sequential LLC) | The meaning and panel range of each parameter. Page 1 (the five voices and the three revisions' filters), page 4 (the USB port's name), pages 6 to 10 (groups, banks and programs; saving), pages 12 to 16 (the global settings), 17 to 20 (oscillators), 21 (mixer), 22 to 24 (filter and the REV switch), 25 to 27 (filter envelope and velocity), 28 to 30 (amplifier envelope), 31 to 33 (low-frequency oscillator and Wheel-Mod), 34 and 35 (Poly-Mod), 36 (Vintage), 37 to 39 (the wheels, aftertouch and glide), 40 and 41 (unison and chord memory), 42 (master tune), 43 (the release switch), 45 (key priority and voice assignment), 57 to 59 (troubleshooting), 61 to 63 (calibration; exporting and importing programs), 64 (alternative tunings). The pages of tutorials (46 to 51) and of control voltage connections (52 to 56), and the descriptions of the alternative tunings after page 64, were not read page by page: their headings show they hold nothing for the interface. |
| **Operation manual** | `manuals/Prophet-5_Owners_Manual_archiveorg.pdf` ("Prophet-5 Synthesizer Operation Manual", Sequential Circuits, CM1000D, February 1982) | Only pages 6-5 and 6-6: the original's 24-byte program record, for the finding above and for section 16. |
| **synth53's source** | `~/devel/neoteletext-renderer-teletext/crates/neoteletext-audio-instruments/src/synth53/patch.rs`, `mod.rs`, `law.rs` and `voice.rs`, as they stood on 18 November 2026 (engine commit `dd0421c6`) | What is built today: the 24 knobs and 22 switches of a patch, the messages taken, the models, the laws of the knobs. Each constant there names its own source. |
| **Wire format as built** | `~/devel/teletext-reference/synthesizers/synthesizer-wire-format.html` and `programming-the-synthesizers.html` | What exists today on the wire and in the kit, for section 16. |
| **`documents.tsv`** | `prophet-5/documents.tsv` | The size of the factory program files (31,800 bytes each), used once in section 3.3 as arithmetic, without opening them. |
| **Architecture** | `neoteletext-common/docs/audio/midi-architecture.md` (this folder), design document of 18 November 2026 | The block, its grammar and bounds, the bank codec and bank image, the restatement, the codec numbers, and the common behaviours of section 11.1 (MIDI-84 to MIDI-92), which this family follows. |

Decisions this document follows: DEC-6453 (each instrument is programmed exactly as its most well-known existing interface does it), DEC-6456 (the provenance of this family and the choice of the 2020 instrument's MIDI interface), DEC-6461 (the names; each name its own kind; no model field for a program to set), DEC-6462 (the Rust server is the one implementation of the programming interface; the kits are thin), DEC-6464 (every synthesizer answers reset all controllers identically, by RP-015, leaving the volume unchanged; recorded as proposed, awaiting the owner's confirmation), DEC-6410 and DEC-6429 (instruments as codecs of the audio profile), DEC-6428 (the clean-room rules), and the architecture decisions A1 to A6 of the brief of 18 November 2026.

**Documents not filed.** No copy of the MIDI 1.0 Detailed Specification, of the Standard MIDI Files 1.0 specification or of the MIDI Association's Recommended Practice RP-015 ("Response to Reset All Controllers") is filed in `~/devel/teletext-reference/`. They are listed as documents to obtain in the architecture document, section 1.5. This document uses them only for what is common to all MIDI (status bytes, that a note on of velocity 0 is a note off, the standard meanings of controllers 6, 38, 74, 96 to 101 and 120 to 127, the null parameter number, registered parameter number 0, the centre of pitch bend, and what reset all controllers resets), and every fact resting on them is marked "(MIDI 1.0, to be checked)" or "(RP-015, to be checked)", to be checked against the filed copy before implementation.

No web page was fetched, no reference program was opened, and the factory program files were not opened for this document.

## 2. Terms

- **synth53, synth52, synth51.** NeoTeletext's five-voice analogue synthesizers of two oscillators a voice. synth53 models revision 3 (Curtis CEM3340 oscillators, CEM3320 filter, CEM3310 envelopes); synth52 and synth51 model revisions 2 and 1 (SSM2030, SSM2040, SSM2050), and are one model today (DEC-6461 item 6). **synth5x** in this document means any of the three.
- **The instrument modelled.** The Sequential Circuits Prophet-5, revisions 1 to 3.
- **The 2020 instrument.** The Prophet-5 that Sequential LLC has made since 2020, which the User's Guide calls "Prophet-5 Rev4". Its MIDI interface is the adopted interface.
- **The adopted interface.** The MIDI Implementation, version 1.4, read with the User's Guide for meanings.
- **Parameter.** One entry of the MIDI Implementation's table of parameter numbers (pages 8 and 9): a name, a number and a range.
- **NRPN.** A non-registered parameter number message of MIDI 1.0, as page 6 describes it: control changes that select a parameter number and then set its value.
- **Program.** The 128 bytes that hold one sound's parameters, one byte a parameter, in the order of section 9. A program is what a program dump carries, packed into 152 bytes.
- **Edit buffer.** The program that is sounding, as changed by the parameter messages received since it was chosen. A program change copies a stored program into it; the edit buffer dump carries it.
- **Group, bank, program number.** The 2020 instrument's three-digit address of a stored program (User's Guide, page 6): a group 1 to 5, a bank 1 to 5 and a program 1 to 8, so 200 programs a set, and two sets (user and factory), 400 in all. A program dump numbers groups 0 to 9 and programs 0 to 39 within a group (section 7).
- **Bank of the sound.** One of the 1 to 10 banks a synth5x sound names (MIDI-57), each holding the program dumps of one group (S53-26), chosen among by bank select and program change. How a bank is stored and named is the architecture document's (MIDI-55 to MIDI-57).
- **Field.** A knob or a switch of synth5x's `Patch` (`patch.rs`): 24 knobs, each a number 0 to 127, and 22 switches.
- **Dial step.** One step of the instrument's converter: a twelfth of a volt. On revision 3 the dial's 10 is 120 steps (`patch.rs`, `dial`; `law.rs`, `SYNTH53.knob_top` 120, from technical manual TM3 adjustment 4-14); on revisions 1 and 2 the converter reaches 127 (`law.rs`, `SYNTH52.knob_top`).
- **Counted as ignored.** A message the instrument does not act on adds one to a count the instrument keeps (`ignored_events` today), and nothing else happens. Nothing is an error in the instrument. It is the architecture document's "passed over and counted" (MIDI-34).
- **Refused.** The Rust server answers a program's message with a typed refusal (the field's path, the rule, a detail) and sends nothing (DEC-6462 item 2).
- **Not stated in the source.** The filed documents do not say. Nothing is supplied from memory in its place; where synth5x needs an answer, the answer is NeoTeletext's own, marked as a reading or an own choice, and listed in section 14.

## 3. What the interface is (facts, not requirements)

### 3.1 The instrument modelled has no MIDI

Revisions 1 to 3 have no MIDI interface. Their program record is the 24 bytes of the operation manual's section 6-7, read and written through a serial "independent CASSETTE interface" by status codes (operation manual, pages 6-5 and 6-6), not by any MIDI message. The interface for programming them over MIDI that is published, maintained and used by tools today is the 2020 instrument's, which reproduces "the vintage sound and features of all three revisions of the original" (User's Guide, page 1) and names each of the original's controls with a parameter number.

### 3.2 How the 2020 instrument's interface is organised

- **Reception is governed by global settings** (MIDI Implementation, page 1; User's Guide, pages 13 and 14): the MIDI channel (ALL, or 1 to 16), how parameters are received (Off, CC, or NRPN), whether controllers are obeyed (MIDI Control), and which port carries system exclusive. The document recommends parameter numbers: "NRPNs are the preferred method of parameter transmission, since they cover the complete range of all parameters, while CCs are limited to a range of 128" (page 1).
- **Every parameter of a program has a parameter number**, 0 to 87, of which 65 to 85 are reserved (pages 8 and 9). The global settings have parameter numbers 4096 to 4109 (page 9).
- **Most parameters also have a control change** (pages 4 and 5): 64 controllers, two of which (7 and 74) have no parameter number.
- **A program travels whole in system exclusive**: the program dump and the edit buffer dump, each 128 bytes packed into 152 (page 12).

### 3.3 Where the filed document contradicts itself, and the reading taken

| # | The contradiction | Where | Reading taken here, and why |
|---|---|---|---|
| C1 | The control-change table names controller 87 "PRESSURE LFO"; the parameter table names parameter 39, its counterpart, "AFTERTOUCH > AMP". | Pages 5 and 8 | Aftertouch's destinations are the filter and the low-frequency oscillator's amount: "The AFTERTOUCH switch lets you choose to apply aftertouch to the Filter cutoff and/or the LFO amount" (User's Guide, page 38). Parameter 39 is "aftertouch to the LFO amount"; the name "AMP" is a slip. |
| C2 | The program-change row reads "0-39 for Programs 0-7 within Bank 1, 8-15 within Bank 2, 16-23 within Bank 4, and 24-31 within Bank 5". It skips bank 3 and stops at 31 though it opens with 0-39. | Page 2 | A group holds five banks of eight programs (User's Guide, page 6). Program change n chooses bank ⌊n ÷ 8⌋ + 1 and program (n mod 8) + 1 for n from 0 to 39: the row's "Bank 4" and "Bank 5" are banks 3 and 4, and 32 to 39 are bank 5. |
| C3 | "Request Program Dump" carries a bank 0 to 7 and a program 0 to 127; the program dump it answers with carries a group 0 to 9 and a program 0 to 39. | Pages 11 and 12 | The program dump's numbering matches the instrument's 10 groups of 40 programs (User's Guide, page 6: two sets of 200). The request's ranges are left out with the request (section 13). |
| C4 | "Save Edit Buffer" is printed with the bytes of "Request Program Transmit" (command `0000 0101`, a bank 0 to 7, a program 0 to 127), identical to the request on page 11. | Page 12 | The message cannot be implemented from the document: its command byte is not stated. It is left out (section 13). |
| C5 | The device inquiry reply gives the instrument's identifier as `0011 0011` (0x33, "Prophet-5 ID (Family LS)"); every other system exclusive message gives "Prophet-5 ID" as `0011 0001` (0x31). | Pages 10 to 13 | The program and edit buffer dumps use 0x31, on four pages; the inquiry is left out (section 13). synth5x's dumps use 0x31. |
| C6 | "The 128 'packed' parameter bytes in the program dump follow the order of the NRPN list" (page 13), but the parameter table is headed "It is received and transmitted but not saved as part of a program" (pages 8 and 9). | Pages 8, 9 and 13 | Page 13 states the dump's layout explicitly and in the dump's own section; the heading of pages 8 and 9 contradicts the existence of the dump and the User's Guide's saving of every panel setting (pages 9 and 10). The parameters of numbers 0 to 87 are saved in a program. |
| C7 | Page 6 says a parameter number's most significant seven bits are "in most cases … zero or one, and never more than two"; the global parameters are numbered 4096 to 4109, whose most significant seven bits are 32. | Pages 6 and 9 | The table is taken as it stands. The program parameters, 0 to 87, all have a most significant part of 0. |
| C8 | The global parameters dump carries "27 nibbles (LS then MS) for 32 Global parameters"; 27 nibbles cannot hold 32 parameters, and page 9 lists 14 global parameters. | Pages 9 and 13 | The dump is not received by the 2020 instrument (page 13) and is left out (section 13). |

Further differences between the two documents, each with the reading taken, are given at the parameters they concern: the resonance's internal range (section 10.2, parameter 18), the unison detune's range (parameter 54), the velocity response's curves (section 13), the alternative tunings' count (section 13), and polyphonic key pressure (requirement S53-7).

**A check from the file sizes.** `documents.tsv` records the two factory program files as 31,800 bytes each. A program dump as section 8 specifies it is 159 bytes, and 200 × 159 = 31,800: two sets of 200 programs (User's Guide, page 6), each program a dump of the length this document reads from page 12. Nothing else was taken from the files.

---

## 4. The channel messages

### 4.1 What the adopted interface receives

The MIDI Implementation, page 2, "Received Channel Messages", row by row:

| Status | Second byte | Third byte | The document's description |
|---|---|---|---|
| `1000 nnnn` (0x8n) | key 0 to 127 | velocity | "Note Off. Velocity is ignored" |
| `1001 nnnn` (0x9n) | key 0 to 127 | velocity | "Note On. Note off if vvvvvvv = 0" |
| `1010 nnnn` (0xAn) | key 0 to 127 | value | "Polyphonic Key Pressure" |
| `1011 nnnn` (0xBn) | controller | value | "Control Change; see 'Received Controller Messages'" |
| `1100 nnnn` (0xCn) | program | none | "Program change, 0-39 for Programs 0-7 within Bank 1, …" (contradiction C2) |
| `1101 nnnn` (0xDn) | value | none | "Channel Pressure" |
| `1110 nnnn` (0xEn) | value | value | "Pitch Bend LS Byte then MS Byte" |

"nnnn: Channel number 0 to 15 (MIDI channel 1-16). Ignored if MIDI channel set to ALL." (page 2).

And "Received Controller Messages", page 2:

| Controller | The document's description |
|---|---|
| 1 (`0000 0001`) | "Mod Wheel: directly assignable controller" |
| 4 (`0000 0100`) | "Foot Controller: directly assignable controller" |
| 74 (`0100 1010`) | "Brightness: Added to filter cutoff frequency" |
| 32 (`0010 0000`) | "Bank Select: 1 - 5 select user banks 1 - 5; 6 - 9 select factory banks 1 - 4" |
| 64 (`0100 0000`) | "Damper pedal: Holds envelopes in Sustain if 0100 0000 or higher" |
| 123 (`0111 1011`) | "All Notes Off: Clear all MIDI notes" |
| 121 (`0111 1001`) | "Reset All Controllers: Clears all MIDI controllers to 0, MIDI volume to maximum" |

"See subsequent sections for additional Continuous Controller (CC) and Non-Registered Parameter Number (NRPN) messages received" (page 2): those are sections 5 and 6 here.

What the 2020 instrument transmits (page 3) gives rise to no requirement: synth5x transmits nothing.

### 4.2 Requirements

**S53-1. The three kinds.** synth53, synth52 and synth51 MUST each be a kind of its own on the wire and in the program protocol (a sound, a live sound, an events message and a bank for each name; DEC-6461 item 3 calls the events message the "blocks message"), and MUST take exactly the same messages, parameters, programs and dumps; every requirement of this document applies to all three unless it names one. The kind alone MUST choose the model: synth53 plays revision 3's laws, synth52 and synth51 play revisions 1 and 2's. The three MUST share one codec, whose code is the architecture document's: code 16, with OBJECT extension tag 5 naming the variant (0 synth53, 1 synth52, 2 synth51), and their banks of the bank codec, code 19, with tag 6 naming the family (MIDI-48, MIDI-107), if the architecture document's open question 1 is answered as it recommends; otherwise the present code of this family. This document does not decide the codec number: the architecture document's open question 1 does. The server MUST write tag 5 from the kind (MIDI-48).
- Reason: Each name is its own kind, and no model or revision field remains for a program to set; variants of one family share their codec and their code.
- Source: DEC-6461 items 3 and 6; decision A5; the architecture document, MIDI-48, MIDI-107 and its open question 1.
- Verification: A test plays one score and one program on each of the three kinds and checks that synth52 and synth51 give identical samples, that synth53 gives samples that differ from them, and that the server takes the same messages for all three; a record test checks the codec code and tag 5's value written for each kind.

**S53-2. The messages synth5x acts on.** synth5x MUST act on exactly these: note off (`0x8n`); note on (`0x9n`); control change (`0xBn`) of the controllers that requirements S53-9 to S53-20 name (1, 7, 32, 64, 74, 120, 121, 123, and 124 to 127 as all notes off), the controllers of the table of section 5.1 (S53-21), and the parameter number controllers of section 6 (6, 38, 96 to 101, including registered parameter number 0, S53-22); program change (`0xCn`); pitch bend (`0xEn`); and the system exclusive edit buffer dump of section 8 (S53-29). Polyphonic key pressure (`0xAn`) and channel pressure (`0xDn`) MUST be counted as ignored (S53-7). A program dump in a block MUST be counted as ignored (S53-28): it travels only in a bank. Every other channel message, every control change of a controller not named, every other system exclusive message, and every system common and system real-time message MUST be counted as ignored and MUST change nothing.
- Reason: These are the messages the adopted interface receives, less those this document leaves out with a reason (section 13), with the messages the architecture document's common layer adds (MIDI-9: controller 120, and the mode messages 124 to 127; MIDI-90: registered parameter number 0).
- Source: MIDI Implementation, pages 2, 4 to 9 and 12; the architecture document, MIDI-9, MIDI-10, MIDI-58 and MIDI-90.
- Verification: A test sends one message of every status from `0x80` to `0xEF`, every controller from 0 to 127, and system exclusive messages of other makers and of other command bytes, and checks which change the instrument and that each other adds one to the count of ignored messages and leaves the samples identical to a run without it.

**S53-3. Channels.** synth5x MUST act on a channel message alike whatever its channel, 0 to 15: its channel map (MIDI-67, MIDI-68) maps all 16 channels to its one part.
- Reason: It is the adopted interface's setting "ALL", under which the channel is "Ignored" and the instrument "receives on all 16 channels". A synth5x sound holds one instrument, so a single channel would address nothing more; the channel setting is a global setting of the hardware, which no program message sets.
- Source: MIDI Implementation, pages 1 and 2; User's Guide, page 13. It is what is built (`mod.rs`: "The instrument is one part and hears every channel").
- Verification: A test plays the same score on each of the 16 channels and once spread over all 16, and checks the samples identical.

**S53-4. Note on.** On a note on whose velocity is 1 to 127, synth5x MUST take the key (0 to 127) as pressed, under the key assignment of S53-40 and S53-42. A note on of velocity 0 MUST be taken as a note off of that key. The velocity MUST NOT change the sound while open question 2 is answered as recommended (parameters 41 and 42 are then kept and not acted on).
- Reason: The adopted interface says "Note off if vvvvvvv = 0". Velocity reaches the sound on the 2020 instrument only through the program's VELOCITY > FILTER and VELOCITY > AMP switches, which the instrument modelled does not have.
- Source: MIDI Implementation, page 2; User's Guide, pages 26 and 30; the architecture document, MIDI-88, with which the adopted interface agrees.
- Verification: A test plays the same note at velocities 1, 64 and 127 with parameters 41 and 42 on and checks identical samples; and checks that a note on of velocity 0 ends a note exactly as a note off does.

**S53-5. Note off.** On a note off, synth5x MUST take the key as released. The release velocity MUST NOT change the sound.
- Reason: "Note Off. Velocity is ignored."
- Source: MIDI Implementation, page 2.
- Verification: The test of S53-4, with note offs of release velocity 0, 64 and 127.

**S53-6. The pitch of a key.** With an oscillator's frequency knob at 24 semitones above its lowest (the operation manual's "normal range"), its fine tuning at 0 and the pitch wheel at its centre, key 69 MUST sound 440 Hz, and every key MUST sound its equal-tempered MIDI pitch, a semitone a key, over all 128 keys. Key 36 is the lowest key of the instrument modelled's 61-key keyboard; keys outside 36 to 96 MUST go on at the same semitone a key.
- Reason: The adopted interface receives note numbers 0 to 127 and does not say which pitch each sounds; synth5x keeps what is built.
- Source: MIDI Implementation, page 2 (key 0 to 127). synth53's source, `mod.rs` (`LOWEST_KEY` 36, its own sources) and `Model::frequency_knob`. NeoTeletext's own reading (section 14 item 10).
- Verification: The existing pitch tests of `tests/synth53_instrument.rs` pass unchanged, driven through the parameters of S53-27 instead of patch bytes.

**S53-7. Polyphonic key pressure and channel pressure.** synth5x MUST count every polyphonic key pressure and every channel pressure as ignored while open question 2 is answered as recommended. If the owner chooses to build aftertouch, both messages MUST then act as the one pressure the 2020 instrument has (the largest pressure of the keys held, for polyphonic key pressure), applied to the destinations parameters 38 and 39 select.
- Reason: The 2020 instrument receives both messages (page 2), yet its User's Guide says it "provides monophonic (or 'channel') aftertouch", applied "to the Filter cutoff and/or the LFO amount" (page 38). The instrument modelled has no pressure. How much pressure moves the cutoff or the amount is not stated in the source (only "eight different aftertouch/pressure response settings", page 39).
- Source: MIDI Implementation, page 2; User's Guide, pages 38 and 39. How a polyphonic pressure becomes one pressure is not stated in the source: NeoTeletext's own (section 14 item 11).
- Verification: The test of S53-2.

**S53-8. Pitch bend and its range.** On a pitch bend, synth5x MUST form the 14-bit number `second byte + third byte × 128` (the least significant seven bits first, as the document says), whose centre is 8,192, and MUST move the pitch of every voice by `(number − 8,192) ÷ 8,192` of the pitch wheel range either way (MIDI-91). The range MUST be set, the last received of these holding, by: (a) parameter 86 received as controller 70 (S53-21) or as its parameter number message (S53-23), value v setting `v + 1` semitones (parameter 86 of S53-27 is 0 to 11, so 1 to 12 semitones); (b) registered parameter number 0, pitch bend sensitivity (S53-22), whose data entry gives semitones (controller 6) and cents (controller 38), setting `semitones + cents ÷ 100` semitones (MIDI 1.0, to be checked). The range MUST be held to at most 12 semitones, the most the adopted interface reaches; a larger value sets 12. Before any of these messages the range MUST be 7 semitones, the family's default. A program change and a received edit buffer dump MUST NOT change the range, whatever their parameter 86 holds, and reset all controllers MUST NOT change it (MIDI-84, MIDI-90); the parameter 86 a program carries is kept in the edit buffer and carried unchanged. Number 0 is the full range down and 16,383 is 8,191 ÷ 8,192 of it up.
- Reason: The adopted interface makes the pitch wheel's range a parameter of each program: "By default its range is set to a semitone … but you can change this on a per-program basis to up to an octave", chosen "from 1-12. A setting of 1 equals a semitone. A setting of 12 equals an octave". The parameter's range is 0 to 11: twelve values for the twelve settings. The instrument modelled has one range, "about a 5th" (`mod.rs`, `PITCH_BEND_SEMITONES` 7), the default here. The architecture document sets one rule for every synthesizer: the range is set by registered parameter number 0 beside the interface's own message, and a program change does not change it (MIDI-90). That the range does not follow the program chosen is therefore a departure from the adopted interface (section 13.2), which open question 5 puts to the owner; the adopted interface documents no registered parameter number but the null one (page 6), so number 0 collides with nothing.
- Source: MIDI Implementation, page 2 (byte order), pages 5, 6 and 9 (controller 70 and parameter 86, 0 to 11; the one RPN received); User's Guide, page 37; the architecture document, MIDI-90 and MIDI-91; MIDI 1.0 (to be checked) for registered parameter number 0 and its data. That parameter value v means v + 1 semitones is this document's reading of the two ranges (section 14 item 4); that the range is the same up and down is not stated in the source. The default of 7 semitones is NeoTeletext's own, as built (section 14 item 4).
- Verification: A test sets parameter 86 by controller 70 to 0, 6 and 11 and sends pitch bends of 0, 8,192 and 16,383, and checks −1, 0, +1 semitones; −7, 0, +7; −12, 0, +12, each within 1 cent (the upper ends to 8,191 ÷ 8,192 of the range); a test sets the range by registered parameter number 0 to 1, 7 and 24 semitones and checks 1, 7 and 12; a test checks that a program change to a program whose parameter 86 is 0, an edit buffer dump and controller 121 leave the range as it was; and a test with no range message checks 7 semitones.

**S53-9. The modulation wheel, controller 1.** On controller 1, synth5x MUST set the modulation wheel to `value ÷ 127` of its travel: the amount of the Wheel-Mod source (the mix of the low-frequency oscillator and noise that parameter 26 sets) sent to the destinations parameters 27 to 31 select, added to the low-frequency oscillator's initial amount (S53-43).
- Reason: "The Mod wheel controls the amount of modulation from the LFO and/or the Noise source as set in the wheel-mod section." The document calls controller 1 "directly assignable"; what it may be assigned to is not stated in the source, and the 2020 instrument's own wheel does what is specified here.
- Source: MIDI Implementation, page 2; User's Guide, pages 32 and 38. Built (`mod.rs`, `CONTROL_MODULATION_WHEEL`; the wheel's share is linear).
- Verification: The existing Wheel-Mod tests pass; a test checks the depth of vibrato at wheel values 0, 64 and 127 against 0, 64 ÷ 127 and 1 of the full depth.

**S53-10. Volume, controller 7.** On controller 7, synth5x MUST set a gain on its output by the volume law every NeoTeletext synthesizer shares (MIDI-82, MIDI-92): values 0 to 127, 127 full and 0 silence, the gain `(value × value) ÷ (127 × 127)` of full, moving to its new place by at most `1 ÷ 256` of full a sample. Before any controller 7 arrives the gain is full (value 127). The gain is not part of a program, and reset all controllers does not change it (S53-16).
- Reason: The architecture document sets one volume law for every synthesizer, on 0 to 127 with 127 full (MIDI-92). The adopted interface's controller 7 is "MASTER VOLUME", 0 to 120, and "Master volume is not programmable"; that its 120 is full there and is not full here is a departure (section 13.2), so that a program's fades sound alike on every synthesizer. This replaces an earlier choice of this document, which scaled 0 to 120 onto the shared law, because MIDI-92 rules it.
- Source: MIDI Implementation, page 4 (controller 7, 0 to 120); User's Guide, page 14; the architecture document, MIDI-82 and MIDI-92; synth53's source, `analog/volume.rs`.
- Verification: A test checks the level of a held note at values 0, 64, 120 and 127 against the law of MIDI-82, and that no two successive samples of the gain differ by more than the slew allows.

**S53-11. The foot controller, controller 4.** synth5x MUST count controller 4 as ignored.
- Reason: The document calls it "directly assignable" and does not say to what; the 2020 instrument's pedal jacks control volume and cutoff (User's Guide, page 2), but which of them, if either, controller 4 reaches is not stated in the source. The instrument modelled takes no foot controller over MIDI.
- Source: MIDI Implementation, page 2. Listed in section 13.
- Verification: The test of S53-2.

**S53-12. Brightness, controller 74.** On controller 74, synth5x MUST add `value` dial steps (0 to 127) to the cutoff that parameter 17 sets, for every voice, as if the cutoff knob stood that many steps higher, the sum held at the model's top (120 on synth53, 127 on synth52 and synth51). Value 0 adds nothing; before any controller 74 arrives the value is 0. Brightness is not part of a program.
- Reason: The adopted interface receives "Brightness: Added to filter cutoff frequency", 0 to 127. How far one step moves the cutoff is not stated in the source; the cutoff knob's own step is the one unit the instrument has, so a sender's brightness reads as a turn of the cutoff knob.
- Source: MIDI Implementation, pages 2 and 5. The scale is NeoTeletext's own (section 14 item 6).
- Verification: A test checks that a program with cutoff 40 and brightness 30 sounds as a program with cutoff 70 and brightness 0; that brightness 127 on cutoff 100 sounds as cutoff 120 on synth53; and that controller 121 leaves it as it was (S53-16).

**S53-13. Bank select, controller 32.** On controller 32, synth5x MUST choose the group that the next program change chooses within (MIDI-64): value v from 1 to 10 chooses group v − 1 of S53-25, and value 0 chooses group 0. Values 11 to 127 MUST be counted as ignored and leave the group as it is. Controller 0 MUST be counted as ignored. Bank select alone MUST NOT change the sound; until a bank select arrives the group is 0.
- Reason: The adopted interface: "Bank Select: 1 - 5 select user banks 1 - 5; 6 - 9 select factory banks 1 - 4". It names user groups 1 to 5 and factory groups 1 to 4 where the User's Guide has five of each (page 6); the reading carries the series on to 10 for the fifth factory group. What value 0 does is not stated in the source; it is taken as the first group so that every sender's first program is reachable. The 2020 instrument's "bank" here is the group of the User's Guide (the hundreds digit), since a program change already reaches 40 programs, five banks of eight.
- Source: MIDI Implementation, page 2; User's Guide, page 6. Values 0 and 10, and the mapping of values to the dump's group numbers, are NeoTeletext's own reading (section 14 item 2).
- Verification: A test builds a sound naming ten banks, one for each of groups 0 to 9, each with a distinct program 0, sends each controller 32 value from 0 to 12 followed by program change 0, and checks the program chosen; and checks that controller 32 alone changes nothing.

**S53-14. The damper pedal, controller 64.** On controller 64, synth5x MUST take the pedal as down at values 64 to 127 and up at 0 to 63. While it is down, a key that is released MUST keep its note in the envelopes' sustain, and the release of every envelope MUST be as its knob sets even when the release switch (parameter 51) is off; when it lifts, every note whose key is up is released.
- Reason: The adopted interface: "Damper pedal: Holds envelopes in Sustain if 0100 0000 or higher." The 2020 instrument's global "Release/Sustain" chooses between the original's release footswitch and a hold (User's Guide, pages 15 and 43); it is a global setting with no program message, and synth5x does both as built, which for a key released under the pedal is the hold.
- Source: MIDI Implementation, page 2; User's Guide, pages 15 and 43; synth53's source, `mod.rs` (`CONTROL_SUSTAIN`). The threshold is the architecture document's one rule for every synthesizer (MIDI-87), with which the adopted interface agrees.
- Verification: The existing pedal tests pass unchanged.

**S53-15. All notes off, controller 123, and the mode messages, controllers 124 to 127.** On controller 123, whatever its value, synth5x MUST release every key held, as a note off of each would; a pedal that is down still holds; a note in its release goes on with it (MIDI-85). Controllers 124, 125, 126 and 127 (omni off, omni on, mono on, poly on), whatever their value, MUST each act exactly as controller 123 and do nothing else: none changes the channels synth5x hears (S53-3), unison (parameter 52) or the key assignment (parameter 87) (MIDI-71, MIDI-89).
- Reason: "All Notes Off: Clear all MIDI notes." The adopted interface does not receive the mode messages; the architecture document makes each of them all notes off in every synthesizer (MIDI-89), which is a departure from the adopted interface listed in section 13.2.
- Source: MIDI Implementation, page 2; the architecture document, MIDI-71, MIDI-85 and MIDI-89. Built for 123 (`mod.rs`, `CONTROL_ALL_NOTES_OFF`).
- Verification: The existing test passes unchanged; a test holds three keys, sends each of 124 to 127 in turn, and checks the keys released, the pedal's hold kept, and unison, the key assignment and the channel map unchanged.

**S53-16. Reset all controllers, controller 121.** On controller 121, whatever its value, synth5x MUST answer exactly as every NeoTeletext synthesizer does (MIDI-84; DEC-6464, recorded as proposed and awaiting the owner's confirmation), by the MIDI Association's Recommended Practice RP-015 as DEC-6464 understands it (RP-015, to be checked): it MUST set the modulation wheel (controller 1) to 0, put the damper pedal (controller 64) up, releasing every note it alone was holding, make the selection of S53-22 none (no registered or non-registered parameter selected), and set the pitch wheel to its centre, 8,192; pressure, which synth5x does not act on (S53-7), is taken as 0. It MUST NOT change: the volume of controller 7 (S53-10); brightness, controller 74 (S53-12), which MIDI 1.0 names a sound controller (MIDI 1.0, to be checked), and sound controllers are left unchanged by RP-015; the group of S53-13; the edit buffer, including every parameter set by a control change or a parameter number message; the pitch wheel range (S53-8); or the keys held.
- Reason: The owner requires every synthesizer to answer reset all controllers the same way (DEC-6464: "we require ALL synths to behave the same way in this regard"), and the architecture document states the one rule (MIDI-84). The adopted interface says "Clears all MIDI controllers to 0, MIDI volume to maximum"; its volume to maximum, and its brightness and other controllers to 0, are departures listed in section 13.2, with DEC-6464 as their reason: keeping the volume avoids a reset making a quiet sound suddenly loud. This replaces an earlier choice of this document, which followed the adopted interface, because DEC-6464 and MIDI-84 rule it.
- Source: DEC-6464 items 1 to 4; the architecture document, MIDI-84; RP-015 (not filed; the architecture document, section 1.5 item 3; to be checked); MIDI Implementation, page 2.
- Verification: A test moves the modulation wheel, the pedal, the pitch wheel, brightness, the volume, the group, a program parameter by controller and by parameter number, a parameter selection and the pitch wheel range, sends controller 121, and checks the wheel at 0, the pedal up, nothing selected (a following data entry counted as ignored), the pitch wheel at its centre, and the volume, brightness, group, edit buffer and range unchanged.

**S53-17. Data entry, increment and decrement, and the parameter number controllers (6, 38, 96 to 101).** These controllers MUST act only as section 6 specifies. The adopted interface transmits its parameter number messages "in running status byte format" (page 6); a block carries no running status (MIDI-12), so the server MUST write each of these control changes with its status byte when it reads running status from a program's raw bytes or a Standard MIDI File, and MUST write a selection and the data entry that follows it in one block at one tick (MIDI-37).
- Reason: They form the parameter number messages of the adopted interface. The architecture document's block is read alone, so running status is expanded by the server.
- Source: MIDI Implementation, pages 6 and 7; the architecture document, MIDI-12 and MIDI-37.
- Verification: The tests of section 6; a server test reads a parameter number message in running status and checks every control change of the block is written with its status byte, the selection and data entry in one block.

**S53-18. Program change.** On a program change of data byte n from 0 to 39, synth5x MUST copy into the edit buffer the program numbered n held by the bank, among the sound's banks, whose program dumps carry the group last chosen by controller 32 (S53-13, S53-26), so that every parameter of section 9 takes that program's value at that instant, with the transitions of S53-34 (but not the pitch wheel range, S53-8). The modulation wheel, the pitch wheel, the pedal, brightness, the volume and the keys held are left as they are. A program change of 40 to 127, which the mapping does not reach, and a program change to a group no bank of the sound holds, or to a program number that group's bank does not hold, MUST set the default program of S53-30 and be counted as passed over (MIDI-59). Until a first program change arrives the edit buffer MUST hold the program numbered 0 of the sound's first bank (bank index 0, MIDI-61), or the default program of S53-30 if that bank lacks program 0 or it was refused (every sound names at least one bank, MIDI-57).
- Reason: The adopted interface receives program changes 0 to 39 within a group (contradiction C2 for the reading). The architecture document sets one rule for every synthesizer for a program the sound does not hold (MIDI-59) and for the part before any program change (MIDI-61); this replaces an earlier choice of this document, which left the edit buffer as it was on a missing program, because MIDI-59 rules it.
- Source: MIDI Implementation, page 2; User's Guide, pages 6 and 7; the architecture document, MIDI-59 and MIDI-61.
- Verification: A test builds a sound of ten banks of 40 distinct programs, one bank a group, sends every group and program change 0 to 39, and checks the edit buffer after each against the bank; sends 40 and 127, a program missing from a smaller bank and a group no bank holds, and checks the count and the default program; checks the program before any program change; and checks that held notes, the wheels and the pedal are unchanged.

**S53-19. A held note under a program change.** A program change and a received edit buffer dump MUST NOT release or retrigger a note that is sounding: the voices sounding go on with the new program's values, as the panel's controls move under a held note (S53-34). A change of parameter 52 (unison) or 87 (key assignment) MUST let go of every key, as switching unison does today, and leave the pedal as it is; whether either changed MUST be judged once all the events of one tick have been applied, by comparing its value then with its value before the tick, so that a restatement (a program change followed at the same tick by the parameters moved since, S53-46) that ends where it began lets go of nothing.
- Reason: It is what is built and what the instrument modelled does when its panel changes under a held key. The adopted interface does not say what happens to a sounding note. A restatement must be inaudible to a viewer who already has the state (MIDI-97), and it passes through the stored program's values within one tick.
- Source: Not stated in the source. synth53's source, `mod.rs` (`set_patch`); the architecture document, MIDI-97.
- Verification: A test holds a chord, sends a program change, and checks that the voices keep sounding and take the new cutoff within the transitions of S53-34; that switching unison lets go of the keys; and that a program change to a program whose unison is off, followed at the same tick by unison on, with unison on before, lets go of nothing and gives samples identical to a run without the two messages.

**S53-20. All sound off, controller 120.** synth5x MUST also act on controller 120, whatever its value, which the adopted interface does not receive: every voice, held, sustained and releasing alike, is taken out over at most 256 output samples by a fade that passes the click measure (MIDI-83), within the architecture document's bound of 1,024 samples (MIDI-86), and every voice then emptied; the pedal, every controller and the edit buffer are left where they are; messages that arrive meanwhile are taken in order when the sound has gone.
- Reason: Every NeoTeletext sound must be able to be silenced at once by the same message (the architecture document's common layer, MIDI-9 and MIDI-86); it is a standard MIDI 1.0 message (MIDI 1.0, to be checked) and is built.
- Source: MIDI 1.0 (to be checked); the architecture document, MIDI-9 and MIDI-86; synth53's source, `mod.rs` (`CONTROL_ALL_SOUND_OFF`). Listed in section 14 item 1.
- Verification: The existing test of all sound off passes unchanged.

### 4.3 The architecture's common behaviours, and this interface's departures

The architecture document sets one rule for every synthesizer where MIDI defines a behaviour common to all instruments (its section 11.1, MIDI-84 to MIDI-92), at the owner's requirement (DEC-6464). synth5x follows each rule; where the adopted interface differs, the difference is a departure, listed again in section 13.2.

| Behaviour | The architecture's rule | The adopted interface | synth5x | Requirement here |
|---|---|---|---|---|
| Reset all controllers, 121 | MIDI-84: RP-015 as DEC-6464 understands it; volume unchanged | "Clears all MIDI controllers to 0, MIDI volume to maximum" (page 2) | The rule: departure (volume and brightness kept; the selection cleared) | S53-16 |
| All notes off, 123 | MIDI-85 | "Clear all MIDI notes" (page 2) | Agrees | S53-15 |
| All sound off, 120 | MIDI-86: silence within 1,024 samples | Not received | Acted on, within 256 samples: departure (an addition) | S53-20 |
| Sustain, 64 | MIDI-87: down at 64 to 127 | "Holds envelopes in Sustain if 0100 0000 or higher" (page 2) | Agrees | S53-14 |
| Note on of velocity 0 | MIDI-88: a note off, release velocity 64 | "Note off if vvvvvvv = 0" (page 2) | Agrees; release velocity is not used (S53-5) | S53-4 |
| Mode messages, 124 to 127 | MIDI-89: all notes off only | Not received | All notes off: departure (an addition) | S53-15 |
| Pitch bend range | MIDI-90: registered parameter number 0 beside the interface's own message; a program change does not change it | Controller 70 and parameter 86, a parameter of each program (pages 5 and 9) | Both set it, held to 12 semitones; a program change does not change it: departure, open question 5 | S53-8, S53-22 |
| Pitch bend resolution | MIDI-91: all 14 bits | 14 bits, least significant byte first (page 2) | Agrees | S53-8 |
| Volume, 7 | MIDI-92: MIDI-82's law on 0 to 127, 127 full | "MASTER VOLUME", 0 to 120 (page 4) | The law on 0 to 127: departure (120 is not full) | S53-10 |

The rules rest on MIDI 1.0 and RP-015, neither filed (section 1); each is to be checked as the architecture document says.

---

## 5. The control changes of the program's parameters

### 5.1 The complete table

The MIDI Implementation, pages 4 and 5, "Additional Continuous Controllers Transmitted/Received": "The following table details how MIDI Continuous Controllers (CCs) are mapped to Prophet-5 controls. They are transmitted when Param Xmit is set to CC, and recognized/received when Param Rcv is set to CC." Every row, in the document's order, with the parameter number of the same control from pages 8 and 9:

| Controller | The document's name | Range | Parameter number |
|---|---|---|---|
| 3 | OSC A FREQUENCY | 0-120 | 0 |
| 7 | MASTER VOLUME | 0-120 | none (S53-10) |
| 9 | OSC B FREQUENCY | 0-120 | 1 |
| 14 | OSC B FINE TUNE | 0-127 | 2 |
| 15 | OSC A SAW ON/FF | 0-1 | 3 |
| 20 | OSC A SQUARE ON/OFF | 0-1 | 4 |
| 21 | OSC A PULSE WIDTH | 0-120 | 8 |
| 22 | OSC B PULSE WIDTH | 0-120 | 9 |
| 23 | OSC SYNC ON/OFF | 0-1 | 10 |
| 24 | OSC B LOW FREQ ON/OFF | 0-1 | 11 |
| 25 | OSC B KEYBOARD ON/OFF | 0-1 | 12 |
| 26 | GLIDE RATE | 0-120 | 13 |
| 27 | OSC A LEVEL | 0-120 | 14 |
| 28 | OSC B LEVEL | 0-120 | 15 |
| 29 | NOISE LEVEL | 0-120 | 16 |
| 30 | OSC B SAW ON/OFF | 0-1 | 5 |
| 31 | RESONANCE | 0-120 | 18 |
| 35 | FILTER KEYBOARD TRACK OFF/HALF/FULL | 0-2 | 19 |
| 41 | FILTER REV SELECT | 0-1 | 20 |
| 46 | LFO FREQUENCY | 0-120 | 21 |
| 47 | LFO INITIAL AMOUNT | 0-120 | 22 |
| 52 | OSC B TRI ON/OFF | 0-1 | 6 |
| 53 | LFO SOURCE MIX | 0-120 | 26 |
| 54 | LFO FREQ A ON/OFF | 0-1 | 27 |
| 55 | LFO FREQ B ON/OFF | 0-1 | 28 |
| 56 | LFO FREQ PW A ON/OFF | 0-1 | 29 |
| 57 | LFO FREQ PW B ON/OFF | 0-1 | 30 |
| 58 | LFO FILTER ON/OFF | 0-1 | 31 |
| 59 | POLY MOD FILT ENV AMOUNT | 0-127 | 32 |
| 60 | POLY MOD OSC B AMOUNT | 0-120 | 33 |
| 61 | POLY MOD FREQ A ON/OFF | 0-1 | 34 |
| 62 | POLY MOD PW ON/OFF | 0-1 | 35 |
| 63 | POLY MOD FILTER ON/OFF | 0-1 | 36 |
| 70 | PITCH WHEEL RANGE | 0-11 | 86 |
| 71 | RETRIGGER AND UNISON ASSIGN | 0-3 | 87 |
| 73 | CUTOFF | 0-120 | 17 |
| 74 | BRIGHTNESS | 0-127 | none (S53-12) |
| 85 | VINTAGE | 0-127 | 37 |
| 86 | PRESSURE FILTER | 0-1 | 38 |
| 87 | PRESSURE LFO | 0-1 | 39 (contradiction C1) |
| 89 | ENVELOPE FILTER AMOUNT | 0-120 | 40 |
| 90 | ENVELOPE FILTER VELOCITY ON/OFF | 0-1 | 41 |
| 102 | ENVELOPE VCA VELOCITY ON/OFF | 0-1 | 42 |
| 103 | ATTACK FILTER | 0-120 | 43 |
| 104 | ATTACK VCA | 0-120 | 44 |
| 105 | DECAY FILTER | 0-120 | 45 |
| 106 | DECAY VCA | 0-120 | 46 |
| 107 | SUSTAIN FILTER | 0-120 | 47 |
| 108 | SUSTAIN VCA | 0-120 | 48 |
| 109 | RELEASE FILTER | 0-120 | 49 |
| 110 | RELEASE VCA | 0-120 | 50 |
| 111 | RELEASE ON/OFF | 0-1 | 51 |
| 112 | UNISON ON/OFF | 0-1 | 52 |
| 113 | UNISON VOICE COUNT | 0-10 | 53 |
| 114 | UNISON DETUNE | 0-7 | 54 |
| 116 | OSC B SQUARE ON/OFF | 0-1 | 7 |
| 117 | LFO SAW ON/OFF | 0-1 | 23 |
| 118 | LFO TRI ON/OFF | 0-1 | 24 |
| 119 | LFO SQUARE ON/OFF | 0-1 | 25 |

That is 59 controllers, 57 of them with a parameter number. The program parameters that have **no controller** are UNISON NOTE, parameters 55 to 64 (ten parameters). The controllers with **no parameter number** are 7 and 74.

The table uses controllers 35, 41, 46, 47 and 52 to 63 as controls of their own, which MIDI 1.0 assigns as the least significant parts of controllers 3 to 31 (MIDI 1.0, to be checked); the adopted interface does not pair them, and synth5x follows it, as the architecture document requires (MIDI-74): controller 35, for example, is the filter's keyboard tracking, not a fine part of oscillator A's frequency.

### 5.2 Requirements

**S53-21. The controllers of the parameters.** On a control change of a controller of the table of section 5.1 other than 7 and 74, synth5x MUST set the parameter of the same row (the "Parameter number" column) in the edit buffer to `min(value, maximum)`, where the maximum is the row's range's upper end, exactly as the parameter number message of section 6 setting that parameter to that value would. A controller of the table MUST NOT be read as the least significant part of another.
- Reason: It is the adopted interface's table. The 2020 instrument receives either controllers or parameter numbers by its global "Param Rcv"; synth5x has no global settings and receives both, which cannot collide, since no controller of the table is one of the parameter number controllers (6, 38, 96 to 101). A value above a parameter's range is taken as its maximum so that a controller sent with MIDI's usual 0 or 127 for a switch is on, and so that nothing is an error.
- Source: MIDI Implementation, pages 1, 4 and 5. Receiving both is a departure (section 13, "Param Rcv"); the clamping is NeoTeletext's own (section 14 item 3).
- Verification: A test sends, for each of the 57 controllers with a parameter number, values 0, 1, the maximum and 127, and checks that exactly the row's parameter changes, to the expected value, and that nothing else changes; an assertion in the code checks that the controller-to-parameter table has 57 entries with no controller and no parameter twice.

---

## 6. Parameter number (NRPN) messages

### 6.1 How the adopted interface forms them

"The messages are handled in standard MIDI format using the NRPN CC commands in running status byte format. Below is the format used for transmitting a NRPN parameter" (MIDI Implementation, page 6):

| Byte | Meaning |
|---|---|
| `1011 nnnn` | Control change |
| `0110 0011` (99) | NRPN parameter number MSB CC |
| `0vvv vvvv` | Parameter number MSB |
| `0110 0010` (98) | NRPN parameter number LSB CC |
| `0vvv vvvv` | Parameter number LSB |
| `0000 0110` (6) | NRPN parameter value MSB CC |
| `0vvv vvvv` | Parameter value MSB |
| `0010 0110` (38) | NRPN parameter value LSB CC |
| `0vvv vvvv` | Parameter value LSB |

"The parameter numbers and the parameter values are broken into two 7-bit bytes for MIDI transmission; the LSB has the seven least-significant bits, and the MSB has the seven most-significant bits" (page 6). "When receiving an NRPN, all messages do not necessarily need to be transmitted, since the synth will track the most recent NRPN number, though it is usually good practice to send the entire message above. Once an NRPN is selected, the synth will also respond to NRPN Data Increment and Decrement commands … Finally, it responds to one RPN (Registered Parameter Number) command, the RPN/NRPN Reset command, which can be handy for resetting the currently selected parameter to a known state" (page 6).

"Received NRPN Messages" (page 7), every row:

| Status | Second | Third | Description |
|---|---|---|---|
| `1011 nnnn` | `0110 0011` (99) | `0vvvvvvv` | NRPN parameter number MSB CC |
| `1011 nnnn` | `0110 0010` (98) | `0vvvvvvv` | NRPN parameter number LSB CC |
| `1011 nnnn` | `0000 0110` (6) | `0vvvvvvv` | NRPN parameter value MSB CC |
| `1011 nnnn` | `0010 0110` (38) | `0vvvvvvv` | NRPN parameter value LSB CC |
| `1011 nnnn` | `0110 0000` (96) | `0xxxxxxx` | NRPN parameter value Increment |
| `1011 nnnn` | `0110 0001` (97) | `0xxxxxxx` | NRPN parameter value Decrement |
| `1011 nnnn` | `0010 0101` (101) | `0111111` (127) | RPN parameter number MSB CC – Reset NRPN parameter number (when both MSB and LSB received) |
| `1011 nnnn` | `0010 0100` (100) | `0111111` (127) | RPN parameter number LSB CC – Reset NRPN parameter number (when both MSB and LSB received) |

(The document prints the third byte of the last two rows as seven digits, `0111111`; read as the byte `0111 1111`, 127, the value MIDI 1.0 gives the null parameter number (MIDI 1.0, to be checked).)

The adopted interface receives no registered parameter number but this null one. The architecture document adds registered parameter number 0, pitch bend sensitivity, to every synthesizer (MIDI-90); it is selected by controller 101 at 0 and controller 100 at 0 (MIDI 1.0, to be checked), which the adopted interface gives no other meaning, so the addition collides with nothing.

### 6.2 Requirements

**S53-22. Selecting a parameter.** synth5x MUST keep a selection: a non-registered parameter number, 0 to 16,383, or registered parameter number 0, or none; at first it is none, and after reset all controllers (S53-16) and after lost input (S53-46) it is none (MIDI-76, MIDI-84, MIDI-102). Controller 99 MUST set the non-registered number's most significant seven bits to its value, and controller 98 its least significant seven bits; each MUST leave the other part as it is, and after either the number `MSB × 128 + LSB` is selected. Controllers 101 and 100 select a registered number in the same way, from parts kept apart from the non-registered number's: when the registered number they then form is 0 (both parts 0), registered parameter number 0, pitch bend sensitivity, is selected (S53-8); when it is 16,383 (both parts 127, the null number), the selection MUST be none; when it is any other number, the selection MUST be none and the controller counted as ignored. Both registered parts are 0 at first, and after a null selection both are 127.
- Reason: The adopted interface tracks "the most recent NRPN number" and resets it with the null RPN. The architecture document adds registered parameter number 0 for the pitch wheel range in every synthesizer (MIDI-90). An RPN other than these two selects a registered parameter that synth5x does not have; data entry that follows it is meant for that parameter and must not land on a program parameter.
- Source: MIDI Implementation, pages 6 and 7; the architecture document, MIDI-76 and MIDI-90; MIDI 1.0 (to be checked) for registered parameter number 0 and the null number. That either part alone selects with the other kept, and that another RPN deselects, are not stated in the source: NeoTeletext's own (section 14 item 3).
- Verification: A test sends 99 then 98 then 6 then 38 and checks the parameter set; sends 98 alone afterwards with another value and checks that the parameter of the new least significant part and the old most significant part is set by the next data entry; sends the null RPN and checks that the next data entry is counted as ignored; sends controllers 101 and 100 at 0 and a data entry and checks the pitch wheel range set; sends controller 101 of value 1 and checks the next data entry counted as ignored; and checks the selection none after controller 121 and after lost input.

**S53-23. Setting a parameter's value.** Controller 6 MUST set the value's most significant seven bits to its value and its least significant seven bits to 0; controller 38 MUST set the least significant seven bits and leave the most significant. After either, if a parameter of the table of S53-27 is selected, synth5x MUST set it in the edit buffer to `min(MSB × 128 + LSB, maximum)`, where the maximum is the parameter's stated range's upper end. Controller 96 MUST raise the selected parameter's value by one and controller 97 lower it by one, whatever their data byte, held to 0 and to the maximum. While registered parameter number 0 is selected, controller 6 MUST set the pitch wheel range's semitones and controller 38 its cents, as S53-8 says, and controllers 96 and 97 MUST be counted as ignored. A data entry, increment or decrement while nothing is selected, or while the number selected is a reserved number (65 to 85, 88 to 94), a global parameter's number (4096 to 4109) or any number not in the table, MUST be counted as ignored.
- Reason: These are the adopted interface's messages. Every program parameter's value fits in seven bits, so a sender sends a most significant part of 0; clearing the least significant part on controller 6 makes a sender that sends only controller 6, the coarse part, set an exact value, and a sender that sends both, as the document transmits them, end at the right value. The step of an increment or decrement is not stated in the source; one step is the smallest change.
- Source: MIDI Implementation, pages 6 and 7; the architecture document, MIDI-76 and MIDI-90. The clearing, the step, the clamping and ignoring an increment or decrement of registered parameter number 0 are NeoTeletext's own (section 14 item 3). The global parameters are left out (section 13).
- Verification: A test sets each of the 67 program parameters by the full four-controller sequence and by controller 38 alone (after a selection), and checks the value; sends values above the maximum and checks the maximum; sends increments and decrements at both ends and checks the clamping; sends data entry with nothing selected, with 70 and with 4096 selected and checks each counted.

**S53-24. A parameter's message changes the sound at once, as the panel.** A parameter set by a control change or a parameter number message MUST take effect as moving the same control of the instrument's panel does (S53-34): on the voices that are sounding and on later notes alike.
- Reason: "Changes to the values of front panel controls are transmitted via MIDI" (page 1): a received parameter is the turn of a knob or the press of a switch.
- Source: MIDI Implementation, page 1; User's Guide, page 13.
- Verification: The test of S53-34.

### 6.3 The complete table of parameter numbers

The MIDI Implementation, pages 8 and 9, "Control NRPN Data", every row in the document's order. "Name" and "Range" are the document's, word for word, including its spelling; numbers 0 to 87 are the program's parameters (contradiction C6) and 4096 to 4109 the global settings.

| Number | Name | Range | Number | Name | Range |
|---|---|---|---|---|---|
| 0 | OSC A FREQUENCY | 0-120 | 26 | LFO SOURCE MIX | 0-120 |
| 1 | OSC B FREQUENCY | 0-120 | 27 | LFO FREQ A ON/OFF | 0-1 |
| 2 | OSC B FINE TUNE | 0-127 | 28 | LFO FREQ B ON/OFF | 0-1 |
| 3 | OSC A SAW ON/FF | 0-1 | 29 | LFO FREQ PW A ON/OFF | 0-1 |
| 4 | OSC A SQUARE ON/OFF | 0-1 | 30 | LFO FREQ PW B ON/OFF | 0-1 |
| 5 | OSC B SAW ON/OFF | 0-1 | 31 | LFO FILTER ON/OFF | 0-1 |
| 6 | OSC B TRI ON/OFF | 0-1 | 32 | POLY MOD FILT ENV AMOUNT | 0-127 |
| 7 | OSC B SQUARE ON/OFF | 0-1 | 33 | POLY MOD OSC B AMOUNT | 0-120 |
| 8 | OSC A PULSE WIDTH | 0-120 | 34 | POLY MOD FREQ A ON/OFF | 0-1 |
| 9 | OSC B PULSE WIDTH | 0-120 | 35 | POLY MOD PW ON/OFF | 0-1 |
| 10 | OSC SYNC ON/OFF | 0-1 | 36 | POLY MOD FILTER ON/OFF | 0-1 |
| 11 | OSC B LOW FREQ ON/OFF | 0-1 | 37 | VINTAGE | 0-127 |
| 12 | OSC B KEYBOARD ON/OFF | 0-1 | 38 | AFTERTOUCH > FILTER | 0-1 |
| 13 | GLIDE RATE | 0-120 | 39 | AFTERTOUCH > AMP | 0-1 |
| 14 | OSC A LEVEL | 0-120 | 40 | ENV FILTER AMOUNT | 0-120 |
| 15 | OSC B LEVEL | 0-120 | 41 | VELOCTIY > FILTER | 0-1 |
| 16 | NOISE LEVEL | 0-120 | 42 | VELOCITY > AMP | 0-1 |
| 17 | CUTOFF | 0-120 | 43 | ATTACK FILTER | 0-120 |
| 18 | RESONANCE | 0–120 | 44 | ATTACK VCA | 0-120 |
| 19 | FILTER KEYBOARD TRACK OFF/HALF/FULL | 0-2 | 45 | DECAY FILTER | 0-120 |
| 20 | FILTER REV SELECT | 0-1 | 46 | DECAY VCA | 0-120 |
| 21 | LFO FREQUENCY | 0-120 | 47 | SUSTAIN FILTER | 0-120 |
| 22 | LFO INITIAL AMOUNT | 0-120 | 48 | SUSTAIN VCA | 0-120 |
| 23 | LFO SAW ON/OFF | 0-1 | 49 | RELEASE FILTER | 0-120 |
| 24 | LFO TRI ON/OFF | 0-1 | 50 | RELEASE VCA | 0-120 |
| 25 | LFO SQUARE ON/OFF | 0-1 | 51 | RELEASE SWITCH | 0-1 |
| | | | 52 | UNISON ON/OFF | 0-1 |
| | | | 53 | UNISON VOICE COUNT | 0-10 |

Continued (page 9):

| Number | Name | Range |
|---|---|---|
| 54 | UNISON DETUNE | 0-7 |
| 55-64 | UNISON NOTE | 1-10 |
| 65-85 | RESERVED | (none given) |
| 86 | PITCH WHEEL RANGE | 0-11 |
| 87 | RETRIGGER AND UNISON | 0-3 |
| 88-94 | RESERVED | (none given) |
| 4096 | TRANSPOSE | 0-24 |
| 4097 | MIDI CHANNEL | 0-16 |
| 4098 | PARAM XMIT | 0-2 |
| 4099 | PARAM RCV | 0-2 |
| 4100 | MIDI CONTROL | 0-1 |
| 4101 | MIDI SYSEX | 0-1 |
| 4102 | MIDI OUT | 0-3 |
| 4103 | LOCAL CONTROL | 0-2 |
| 4104 | POT MODE | 0-2 |
| 4105 | SUSTAIN MODE | 0-1 |
| 4106 | PEDAL MODE | 0-1 |
| 4107 | ALT TUNINGS | 0-15 |
| 4108 | VEL RESPONSE | 0-7 |
| 4109 | AFTERTOUCH RESPONSE | 0-7 |

Section 10 gives every program parameter's meaning and what synth5x does with it; section 13 gives every global parameter and why it is left out.

---

## 7. Programs, groups and banks

**The adopted interface's numbering.** "The Prophet-5 contains a total of 400 programs. 200 are permanent 'Factory' programs and 200 are 'User' programs" (User's Guide, page 6). A program is addressed by a group 1 to 5 ("the 'hundreds'"), a bank 1 to 5 ("the 'tens'") and a program 1 to 8 ("the 'ones' digit"), for example program 123 (pages 6 and 7). Over MIDI: bank select chooses user groups 1 to 5 and factory groups (S53-13); a program change chooses one of 40 programs within the group, "0-39" (page 2); a program dump carries "Group Number: 0 - 9" and "Program Number: 0 - 39" (page 12). The dump numbers ten groups where bank select's row names nine values (1 to 9); this document settles the difference by reading value 10 as the fifth factory group (S53-13).

**S53-25. The numbering of a synth5x bank.** A synth5x sound's bank MUST address its programs as the adopted interface does: by a group number 0 to 9 and a program number 0 to 39, so 400 places, and the place of the program at group g and program p MUST be `g × 40 + p`, 0 to 399. Program p within a group is the User's Guide's bank `⌊p ÷ 8⌋ + 1` and program `(p mod 8) + 1`; group g from 0 to 4 is the user set's groups 1 to 5 and group g from 5 to 9 the factory set's groups 1 to 5. A sound MAY hold any number of programs from 1 to 400 at any places, in 1 to 10 banks of one group each (S53-26); the sound names which banks.
- Reason: The program dump's group and program numbers are the place a program "will load back into" (User's Guide, page 63), and bank select and program change reach the same 400 places. Keeping the numbering means a bank made from the 2020 instrument's own dumps plays with its own program changes. The architecture document's ten banks a sound (MIDI-57) are the ten groups. That groups 0 to 4 are the user set and 5 to 9 the factory set is the order of controller 32's values; the document does not state it for the dump's numbers.
- Source: MIDI Implementation, pages 2 and 12; User's Guide, pages 6, 7 and 63; the architecture document, MIDI-57. The mapping of the user and factory sets to group numbers is this document's reading (section 14 item 2).
- Verification: The test of S53-18.

**S53-26. The family's banks and blocks.** synth5x's banks and blocks MUST be as the architecture document specifies (MIDI-23 to MIDI-31, MIDI-50 to MIDI-58), with these facts of this family. (a) A bank image (MIDI-56, the form of messages) MUST be 1 to 40 program dumps of S53-28, byte for byte, back to back, every one carrying the same group (0 to 9) and each a different program number (0 to 39): at most 40 × 159 = 6,360 bytes, within the architecture's 16,384. A sound MUST name 1 to 10 such banks (MIDI-57), no two of the same group, so that it reaches up to 400 programs; the bank of a group is the bank whose dumps carry that group number, wherever it stands among the sound's banks. The server MUST refuse a bank whose dumps carry two groups or one program number twice, and a sound naming two banks of one group. (b) A block MUST be able to carry a 157-byte edit buffer dump as one system exclusive event (156 bytes after `0xF0`, within MIDI-28's 256), at most 1,005 bytes and 256 events a block (MIDI-30, MIDI-31); a program dump never travels in a block (S53-28), and a block carries no running status (MIDI-12, S53-17). (c) A whole program sent as parameter number messages is 67 parameters of four control changes each: 268 messages, 804 bytes with every status byte written and a delta time of one byte each to be added (1,072 bytes in all), so it exceeds one block's 1,005 bytes and its 256 events; a program SHOULD send the edit buffer dump instead, and the server MUST refuse a block that would hold more (MIDI-31). (d) The server, not the program, restates each part (S53-46, MIDI-93 to MIDI-99).
- Reason: Decision A4: patches travel in the adopted interface's own form, its system exclusive dumps. The architecture document carries a bank as an object of its own, at most 16,384 bytes and ten a sound (MIDI-55 to MIDI-57); one bank a group is the form in which the 2020 instrument's own numbering and the architecture's bounds agree. This replaces an earlier choice of this document, one bank of up to 400 programs (63,600 bytes), which exceeded the architecture's bound.
- Source: MIDI Implementation, pages 6, 8, 9 and 12; decisions A3 and A4; the architecture document, MIDI-12, MIDI-28, MIDI-30, MIDI-31 and MIDI-55 to MIDI-57.
- Verification: A test stores ten banks of 40 programs, one a group, plays a bank select and program change to each, and checks the edit buffer; server tests refuse a bank of two groups, a bank with one program twice and a sound of two banks of one group; a test carries an edit buffer dump in a live block and checks it applied; the architecture document's tests cover the carriage.

---

## 8. The system exclusive messages

### 8.1 The two dumps synth5x takes

"Program Data Dump" (MIDI Implementation, page 12), byte by byte:

| Offset | Bits | Value | Meaning |
|---|---|---|---|
| 0 | `1111 0000` | 0xF0 | System Exclusive |
| 1 | `0000 0001` | 0x01 | "DSI ID" |
| 2 | `0011 0001` | 0x31 | "Prophet-5 ID" |
| 3 | `0000 0010` | 0x02 | "Program Data" |
| 4 | `0000 00vv` | 0 to 9 | "Group Number: 0 - 9" |
| 5 | `0vvv vvvv` | 0 to 39 | "Program Number: 0 - 39" |
| 6 to 157 | `0vvv vvvv` | 0 to 127 each | "128 bytes expanded to 152 MIDI bytes in 'packed MS bit' format" |
| 158 | `1111 0111` | 0xF7 | End of Exclusive |

159 bytes in all. (The group's bit pattern is printed `0000 00vv`, two bits, which cannot hold 9; the range "0 - 9" is taken as stated.)

"Program Edit Buffer Data Dump" (page 12), byte by byte:

| Offset | Bits | Value | Meaning |
|---|---|---|---|
| 0 | `1111 0000` | 0xF0 | System Exclusive |
| 1 | `0000 0001` | 0x01 | "DSI ID" |
| 2 | `0011 0001` | 0x31 | "Prophet-5 ID" |
| 3 | `0000 0011` | 0x03 | "Edit Buffer Data" |
| 4 to 155 | `0vvv vvvv` | 0 to 127 each | "128 bytes expanded to 152 MIDI bytes in 'packed MS bit' format" |
| 156 | `1111 0111` | 0xF7 | End of Exclusive |

157 bytes in all.

**S53-27. The parameters a program carries.** The parameters of a synth5x program, and their stated maxima, MUST be exactly the 67 of the table of section 6.3 numbered 0 to 64, 86 and 87; numbers 65 to 85 and 88 to 94 are reserved. In the rest of this document "the table of S53-27" means those 67 parameters with their ranges.
- Reason: They are the adopted interface's program parameters (contradiction C6 for why they are the program's).
- Source: MIDI Implementation, pages 8, 9 and 13.
- Verification: An assertion in the code checks that the parameter table holds 67 entries with those numbers and maxima; the tests of section 9.

**S53-28. A program dump.** A program dump is a message whose bytes 0 to 3 are `F0 01 31 02`, whose length is 159 bytes with byte 158 `F7`, whose group (byte 4) is 0 to 9 and whose program (byte 5) is 0 to 39. It MUST travel only in a bank image (S53-26): when the receiver reads a bank, synth5x MUST unpack each program dump's bytes 6 to 157 by S53-31 and MUST take the program as the bank's program at that group and program number; a dump in a bank with these first four bytes and any other length, group or program MUST be taken as a faulty patch (MIDI-63): its place, if its program number can be read, holds the default program of S53-30, and it is counted among the patches refused. A program dump delivered in a block MUST be counted as ignored and MUST change neither the edit buffer nor any bank (MIDI-34, MIDI-60, MIDI-65). The server MUST lift a program dump that stands in a program's music before the sound's first note on into a bank, and MUST refuse one after it (MIDI-58).
- Reason: "Dumped programs will load back into the same bank and program location in memory when received" (User's Guide, page 16, and page 63): it is the message that fills the instrument's memory, which is what the architecture document's bank image carries (MIDI-56). The architecture document keeps a sound's banks fixed for its life (MIDI-65) and lets no inline message change a bank (MIDI-60). This replaces an earlier choice of this document, under which a program dump in a block replaced a program in a working copy of the bank for the rest of the play, because MIDI-58, MIDI-60 and MIDI-65 rule it.
- Source: MIDI Implementation, page 12; User's Guide, pages 16 and 63; the architecture document, MIDI-56, MIDI-58, MIDI-60, MIDI-63 and MIDI-65.
- Verification: A test builds a bank from program dumps of group 3 and checks each program; a test sends a program dump in a live block and checks it counted and the edit buffer and the bank unchanged; a test puts dumps of 158 and 160 bytes, group 10 and program 40 in a bank and checks each refused and counted; server tests lift a dump before the first note on into a bank and refuse one after.

**S53-29. Receiving an edit buffer dump.** When a block delivers a system exclusive message whose bytes 0 to 3 are `F0 01 31 03`, whose length is 157 bytes with byte 156 `F7`, synth5x MUST unpack bytes 4 to 155 by S53-31 and MUST set the edit buffer to that program at that instant, as a program change would (S53-18, S53-19), without changing any of the sound's banks (MIDI-60). A message with these first four bytes and another length MUST be taken as a faulty patch: the edit buffer MUST be set to the default program of S53-30 and the message counted among the patches refused (MIDI-63).
- Reason: It is the adopted interface's whole-program message for the sound that is playing, and the way a program sets every parameter at once; the architecture document's inline patch (MIDI-60). The architecture document sets one rule for a faulty patch (MIDI-63); this replaces an earlier choice of this document, which counted the message as ignored and left the edit buffer, because MIDI-63 rules it.
- Source: MIDI Implementation, page 12; the architecture document, MIDI-60 and MIDI-63. That receiving it sets the edit buffer is not stated in so many words; it is what the edit buffer dump is for, and the 2020 instrument's request for it answers with "the current program edit buffer" (page 11).
- Verification: A test sends an edit buffer dump and checks every parameter of the edit buffer; checks a held note goes on (S53-19); and sends one of 156 bytes and checks the default program and the counter.

**S53-30. The default program.** An instrument whose first bank lacks program 0 (S53-18), and an instrument given a program change the sound does not hold or a faulty patch (S53-18, S53-28, S53-29), MUST stand at this program (by parameter number, the value; every number not given is 0): 0, 64; 1, 64; 3, 1; 8, 64; 9, 64; 12, 1; 14, 120; 17, 120; 19, 2; 20, 1 for synth53 and 0 for synth52 and synth51; 24, 1; 47, 120; 48, 120; 51, 1; 53, 4; 86, 6. That is: oscillator A's sawtooth alone, both frequency knobs at 64, both pulse widths at 64, oscillator B on the keyboard, the mixer's oscillator A full, the cutoff open with full keyboard tracking, the low-frequency oscillator's triangle chosen, both sustains full, the release switch on, unison off, the pitch wheel range seven semitones, and the key assignment of value 0.
- Reason: An instrument must sound something definite before a program arrives. This is the default built today (`Patch::DEFAULT`, own choice) in the adopted interface's form, with the parameters the original does not have set as the original behaves: the pitch wheel at the original's fifth, the filter tracking full as the original's switch is, unison at five voices under the reading of S53-42. The 2020 instrument's own "Basic Preset" (User's Guide, page 8) is not stated value by value in the source, beyond oscillator A alone on its sawtooth (page 19) and the revision 3 filter (page 23), both of which this program shares.
- Source: synth53's source, `patch.rs` (`Patch::DEFAULT`). NeoTeletext's own (section 14 item 9).
- Verification: A test checks a new instrument's edit buffer, parameter by parameter, and that it sounds identical to today's default patch on synth53 and synth52.

### 8.2 The packing of eight bits into seven

The MIDI Implementation, page 13, in full: "Data is packed in 8 byte 'packets', with the MS bit stripped from 7 parameter bytes, and packed into an eighth byte, which is sent at the start of the 8 byte packet." Its example:

| Input data (bits 7 to 0) | | Packed MIDI data (bits 7 to 0) |
|---|---|---|
| 1: A7 A6 A5 A4 A3 A2 A1 A0 | | 1: 0 G7 F7 E7 D7 C7 B7 A7 |
| 2: B7 B6 B5 B4 B3 B2 B1 B0 | | 2: 0 A6 A5 A4 A3 A2 A1 A0 |
| 3: C7 C6 C5 C4 C3 C2 C1 C0 | | 3: 0 B6 B5 B4 B3 B2 B1 B0 |
| 4: D7 D6 D5 D4 D3 D2 D1 D0 | | 4: 0 C6 C5 C4 C3 C2 C1 C0 |
| 5: E7 E6 E5 E4 E3 E2 E1 E0 | | 5: 0 D6 D5 D4 D3 D2 D1 D0 |
| 6: F7 F6 F5 F4 F3 F2 F1 F0 | | 6: 0 E6 E5 E4 E3 E2 E1 E0 |
| 7: G7 G6 G5 G4 G3 G2 G1 G0 | | 7: 0 F6 F5 F4 F3 F2 F1 F0 |
| | | 8: 0 G6 G5 G4 G3 G2 G1 G0 |

So the first byte of a packet holds the top bit of the packet's first data byte in its bit 0, of the second in bit 1, and so on to the seventh's in bit 6; its bit 7 is 0. The next seven bytes are the seven data bytes with their top bit cleared, in order.

**The length.** 128 bytes are 18 whole packets of seven (126 bytes, packed into 144) and two bytes over; "152 MIDI bytes" is 19 packets of 8. The nineteenth packet therefore carries data bytes 126 and 127 and five more positions, which the document does not describe: what a sender writes in them is not stated in the source.

**S53-31. Unpacking.** A receiver, and the server when it checks a dump (MIDI-21), MUST unpack 152 packed bytes into 133 bytes thus: for packet k from 0 to 18, with packed bytes `P[8k]` to `P[8k + 7]`, data byte `7k + i` for i from 0 to 6 is `P[8k + 1 + i] OR (((P[8k] >> i) AND 1) << 7)`. Bytes 0 to 127 are the program; bytes 128 to 132 MUST be ignored. A packed byte with its top bit set cannot occur inside a system exclusive message.
- Reason: It is the page 13 format, applied to the 152 bytes page 12 gives.
- Source: MIDI Implementation, pages 12 and 13. Ignoring the five extra positions is NeoTeletext's own (section 14 item 12).
- Verification: A test unpacks the worked examples of S53-32 and checks every bit; a test packs and unpacks 1,000 seeded random 128-byte programs and checks each returns identical.

**S53-32. Packing, and the worked examples.** A writer, which is the server alone (DEC-6462; MIDI-13, MIDI-22), MUST pack 128 program bytes into 152 by the inverse of S53-31, writing 0 in the five positions after byte 127 (data bytes 128 to 132 of the last packet). The following examples MUST hold, and are the verification vectors.
1. *The document's own description*, with seven bytes chosen so that every top bit differs: input `80 01 FF 00 7F 81 40`. Their top bits are A7 = 1, B7 = 0, C7 = 1, D7 = 0, E7 = 0, F7 = 1, G7 = 0, so the first packed byte is `0 0 1 0 0 1 0 1` in bits 7 to 0, 0x25. The packet is `25 00 01 7F 00 7F 01 40`.
2. *The first packet of the default program of S53-30* on synth53: parameters 0 to 6 are 64, 64, 0, 1, 0, 0, 0, none above 127, so the first byte is 0x00 and the packet is `00 40 40 00 01 00 00 00`.
3. *The last packet of any program*: data bytes 126 and 127 (reserved, written 0) and five zeros: `00 00 00 00 00 00 00 00`.
Every byte of a valid synth5x program is at most 127 (S53-27), so every first byte of a packet a synth5x writer makes is 0x00; a receiver MUST nevertheless unpack the top bits, since the format carries them.
- Reason: The format is the document's; the zeros in the five extra positions are the only choice that adds nothing.
- Source: MIDI Implementation, page 13. The examples' values are this document's; example 1 is the document's example with values.
- Verification: A test packs and unpacks each of the three examples and checks every byte.

---

## 9. The program: 128 bytes

"The 128 'packed' parameter bytes in the program dump follow the order of the NRPN list, one byte per parameter, and padded with zeros from the final parameter to the 128th byte" (MIDI Implementation, page 13). The parameter table lists the reserved numbers 65 to 85 and 88 to 94 in their places, which they can occupy only as positions; this document therefore reads "the order of the NRPN list" as **byte n holds parameter n**. The program has no name: neither document gives a program a name, and the 2020 instrument's display shows a three-digit number (User's Guide, pages 6 and 7).

**S53-33. The layout of a program.** Byte n of the 128 MUST hold parameter number n for n from 0 to 87, and bytes 88 to 127 MUST be written 0 and ignored when read. The bytes, every one in order:

| Byte | Parameter | Byte | Parameter |
|---|---|---|---|
| 0 | OSC A FREQUENCY | 44 | ATTACK VCA |
| 1 | OSC B FREQUENCY | 45 | DECAY FILTER |
| 2 | OSC B FINE TUNE | 46 | DECAY VCA |
| 3 | OSC A SAW ON/OFF | 47 | SUSTAIN FILTER |
| 4 | OSC A SQUARE ON/OFF | 48 | SUSTAIN VCA |
| 5 | OSC B SAW ON/OFF | 49 | RELEASE FILTER |
| 6 | OSC B TRI ON/OFF | 50 | RELEASE VCA |
| 7 | OSC B SQUARE ON/OFF | 51 | RELEASE SWITCH |
| 8 | OSC A PULSE WIDTH | 52 | UNISON ON/OFF |
| 9 | OSC B PULSE WIDTH | 53 | UNISON VOICE COUNT |
| 10 | OSC SYNC ON/OFF | 54 | UNISON DETUNE |
| 11 | OSC B LOW FREQ ON/OFF | 55 | UNISON NOTE (first) |
| 12 | OSC B KEYBOARD ON/OFF | 56 | UNISON NOTE (second) |
| 13 | GLIDE RATE | 57 | UNISON NOTE (third) |
| 14 | OSC A LEVEL | 58 | UNISON NOTE (fourth) |
| 15 | OSC B LEVEL | 59 | UNISON NOTE (fifth) |
| 16 | NOISE LEVEL | 60 | UNISON NOTE (sixth) |
| 17 | CUTOFF | 61 | UNISON NOTE (seventh) |
| 18 | RESONANCE | 62 | UNISON NOTE (eighth) |
| 19 | FILTER KEYBOARD TRACK | 63 | UNISON NOTE (ninth) |
| 20 | FILTER REV SELECT | 64 | UNISON NOTE (tenth) |
| 21 | LFO FREQUENCY | 65 | reserved |
| 22 | LFO INITIAL AMOUNT | 66 | reserved |
| 23 | LFO SAW ON/OFF | 67 | reserved |
| 24 | LFO TRI ON/OFF | 68 | reserved |
| 25 | LFO SQUARE ON/OFF | 69 | reserved |
| 26 | LFO SOURCE MIX | 70 | reserved |
| 27 | LFO FREQ A ON/OFF (Wheel-Mod to oscillator A's frequency) | 71 | reserved |
| 28 | LFO FREQ B ON/OFF (to oscillator B's frequency) | 72 | reserved |
| 29 | LFO FREQ PW A ON/OFF (to oscillator A's pulse width) | 73 | reserved |
| 30 | LFO FREQ PW B ON/OFF (to oscillator B's pulse width) | 74 | reserved |
| 31 | LFO FILTER ON/OFF (to the cutoff) | 75 | reserved |
| 32 | POLY MOD FILT ENV AMOUNT | 76 | reserved |
| 33 | POLY MOD OSC B AMOUNT | 77 | reserved |
| 34 | POLY MOD FREQ A ON/OFF | 78 | reserved |
| 35 | POLY MOD PW ON/OFF | 79 | reserved |
| 36 | POLY MOD FILTER ON/OFF | 80 | reserved |
| 37 | VINTAGE | 81 | reserved |
| 38 | AFTERTOUCH > FILTER | 82 | reserved |
| 39 | AFTERTOUCH > LFO (printed "AMP", contradiction C1) | 83 | reserved |
| 40 | ENV FILTER AMOUNT | 84 | reserved |
| 41 | VELOCITY > FILTER | 85 | reserved |
| 42 | VELOCITY > AMP | 86 | PITCH WHEEL RANGE |
| 43 | ATTACK FILTER | 87 | RETRIGGER AND UNISON |

Bytes 88 to 94 are reserved and bytes 95 to 127 are padding: all 0 when written.

A synth5x writer (the server) MUST write each of the 67 parameters within its range and 0 in every reserved and padding byte. A synth5x receiver MUST accept every program of the right length and header and MUST take a parameter byte above its parameter's maximum as the maximum (the family's choice under MIDI-81). The Rust server MUST refuse a program in which a parameter byte is above its parameter's stated maximum, naming the byte, the parameter and the maximum, and MUST NOT refuse a program for the content of a reserved or padding byte or of the five positions after byte 127, which it MUST carry unchanged.
- Reason: Byte for byte as the adopted interface (decision A4). The receiver never errors, as no instrument does. The server refuses what cannot be a program of the 2020 instrument so that a channel's mistake is shown to its author (as the server checks every patch today); it keeps reserved content unchanged, since a dump from the 2020 instrument may carry values there that this document cannot know, and A4 requires its dumps byte for byte.
- Source: MIDI Implementation, pages 8, 9 and 13. "Byte n holds parameter n" is this document's reading (section 14 item 2; open question 4 asks to confirm it). The minimum of parameters 55 to 64 is stated as 1; the server checks only maxima, so a 0 there is accepted.
- Verification: A test decodes the default program of S53-30 from its dump and checks every byte; a test checks, for every parameter byte and every value 0 to 255, the receiver's value and the server's acceptance or refusal; a test checks that a program with non-zero reserved bytes passes the server unchanged and plays as the same program with zeros.

---

## 10. What each parameter means, and what synth5x does with it

### 10.1 How a value becomes a control

**S53-34. A value moves a control as the panel does.** A parameter that maps to a knob of synth5x (column "Field" of S53-37) MUST move the knob as the instrument's computer follows a turned knob (one dial step every six milliseconds while a voice sounds; at once when none does); a parameter that maps to a switch MUST take effect at once.
- Reason: It is what is built: the instrument modelled scans each knob once a loop and moves its number one step towards it, which is what a received parameter is, the turn of a knob.
- Source: synth53's source, `mod.rs` (`LOOP_TICKS`, `set_patch`, `scan`; TM3 section 2-12, page 29).
- Verification: The existing control tests pass, driven through parameter messages instead of `set_patch`.

**S53-35. The scale of a knob on synth53.** On synth53 a knob parameter of range 0 to 120 MUST set the field to the parameter's value: one value is one dial step, and 120 is the dial's 10. OSC B FINE TUNE (0 to 127) and POLY MOD FILT ENV AMOUNT (0 to 127) MUST set the field to the value.
- Reason: The 2020 instrument's knobs run 0 to 120, its "10" on every dial (User's Guide, pages 18 to 35, each knob "0...10"); revision 3's converter puts the dial's 10 at 120 steps of a twelfth of a volt and plays nothing above it. The two are one scale.
- Source: MIDI Implementation, pages 8 and 9; synth53's source, `patch.rs` (`dial`) and `law.rs` (`SYNTH53.knob_top` 120, from TM3 adjustment 4-14 and section 2-12).
- Verification: A test sets each knob parameter to 0, 60 and 120 on synth53 and checks the field 0, 60, 120; and that a program from today's 24-byte form with every knob at most 120 sounds identical when carried as a program.

**S53-36. The scale of a knob on synth52 and synth51.** On synth52 and synth51 a knob parameter of range 0 to 120 MUST set the field to `floor((value × 127 + 60) ÷ 120)`, so that 0 is 0, 60 is 64 (63.5 rounded up) and 120 is 127. OSC B FINE TUNE and POLY MOD FILT ENV AMOUNT, 0 to 127, MUST set the field to the value. A writer that turns a synth52 field back into a parameter MUST write `floor((field × 120 + 63) ÷ 127)`, which the receiver's formula returns as the nearest field that a parameter can express.
- Reason: Open question 3, recommendation A: the parameter is the dial's position, and revisions 1 and 2 put the dial's 10 at the converter's 127 (`law.rs`, `SYNTH52.knob_top` 127), so the same program reaches the same dial positions on every model. Of the 128 field values, 121 are reachable.
- Source: NeoTeletext's own (section 14 item 13), pending open question 3. synth53's source, `law.rs` (`SYNTH52`, TM2 section 2-12).
- Verification: A test checks all 121 values against the formula, that the field never decreases as the value rises, and that 0, 60 and 120 give 0, 64 and 127.

### 10.2 Every parameter

The meanings are the User's Guide's (printed page in brackets). "Field" is synth5x's `Patch` field today (`patch.rs`: knob or switch, with its byte there). "Status": **built** (synth5x does it today), **to be built** (requirement here, recommended under open question 2), **kept** (stored, carried and returned unchanged, not acted on: left out of the sound, section 13).

| No. | Parameter | Range | Meaning in the adopted interface | Field of synth5x | Status |
|---|---|---|---|---|---|
| 0 | OSC A FREQUENCY | 0-120 | "Sets the base oscillator frequency over a 4-octave range. Adjustment is in semitones" [18] | Knob `OscAFrequency` (byte 21) | Built; on synth52 the knob spans five octaves, as revisions 1 and 2 do (`law.rs`) |
| 1 | OSC B FREQUENCY | 0-120 | As oscillator A's; with oscillator B's KEYBOARD off "the FREQUENCY knob has a 9 octave range" [19] | Knob `OscBFrequency` (22) | Built |
| 2 | OSC B FINE TUNE | 0-127 | "adjusts the tuning of Oscillator B upward (sharp) and has a range of nearly a semitone" [18] | Knob `OscBFine` (23) | Built |
| 3 | OSC A SAW ON/FF | 0-1 | Oscillator A's sawtooth; "You can turn on multiple waveshapes simultaneously" [18] | Switch `OscASawtooth` (1) | Built |
| 4 | OSC A SQUARE ON/OFF | 0-1 | Oscillator A's square/pulse [18] | Switch `OscAPulse` (0) | Built |
| 5 | OSC B SAW ON/OFF | 0-1 | Oscillator B's sawtooth [18] | Switch `OscBSawtooth` (3) | Built |
| 6 | OSC B TRI ON/OFF | 0-1 | Oscillator B's triangle [18] | Switch `OscBTriangle` (4) | Built |
| 7 | OSC B SQUARE ON/OFF | 0-1 | Oscillator B's square/pulse [18] | Switch `OscBPulse` (5) | Built |
| 8 | OSC A PULSE WIDTH | 0-120 | From a square at the knob's centre "to a very narrow pulse wave when the PULSE WIDTH knob is fully left or right" [18, 19] | Knob `OscAPulseWidth` (13) | Built (the instrument modelled's law, `law.rs`) |
| 9 | OSC B PULSE WIDTH | 0-120 | As oscillator A's [18] | Knob `OscBPulseWidth` (11) | Built |
| 10 | OSC SYNC ON/OFF | 0-1 | "Sync forces Oscillator A to restart its cycle every time Oscillator B starts a cycle" [18] | Switch `Sync` (2) | Built |
| 11 | OSC B LOW FREQ ON/OFF | 0-1 | "Turns Oscillator B into a low-frequency oscillator" [19] | Switch `OscBLowFrequency` (21) | Built |
| 12 | OSC B KEYBOARD ON/OFF | 0-1 | "When off, the Oscillator B ignores the keyboard and note data received via MIDI" [19] | Switch `OscBKeyboard` (6) | Built |
| 13 | GLIDE RATE | 0-120 | "Glide causes the pitch of a note to glide up or down from the pitch of the previously played note" [39] | Knob `Glide` (16) | Built, in unison only (S53-44) |
| 14 | OSC A LEVEL | 0-120 | "Sets the output level of Oscillator A" [21] | Knob `MixerOscA` (12) | Built |
| 15 | OSC B LEVEL | 0-120 | Oscillator B's level [21] | Knob `MixerOscB` (10) | Built |
| 16 | NOISE LEVEL | 0-120 | "the output level of the white noise generator" [21] | Knob `MixerNoise` (14) | Built |
| 17 | CUTOFF | 0-120 | "Sets the filter's cutoff frequency", 0...10 [24] | Knob `Cutoff` (8) | Built |
| 18 | RESONANCE | 0-120 | 0...10; "High levels of resonance can cause either filter to self-oscillate" [24]. The User's Guide gives "the RESONANCE parameter has an internal value range of 0 to 127" [14], against the MIDI Implementation's 0 to 120; the interface's range, 0 to 120, is taken. | Knob `Resonance` (15) | Built |
| 19 | FILTER KEYBOARD TRACK OFF/HALF/FULL | 0-2 | "Selecting HALF or FULL means that the higher the note played on the keyboard, the more the filter opens" [24]; values 0, 1, 2 read as off, half, full, the order of the name | Switch `FilterKeyboard` (14): off or full | 0 and 2 built; 1, half, to be built (S53-41) |
| 20 | FILTER REV SELECT | 0-1 | The REV switch: "1/2" (the SSI 2140, as the SSM 2040 of revisions 1 and 2) or "3" (the CEM 3320); it "not only changes filter type, but also the Filter Envelope's shape/response" [22, 24, 25]. Which value is which is not stated in the source; read as 0 = "1/2", 1 = "3", the panel's order | None: the kind chooses (S53-1) | Kept; open question 1 |
| 21 | LFO FREQUENCY | 0-120 | "from a slow .022Hz to a fast 500Hz" on the 2020 instrument [32] | Knob `LfoFrequency` (17) | Built, with the instrument modelled's range (`law.rs`), not the 2020 instrument's |
| 22 | LFO INITIAL AMOUNT | 0-120 | "Sets the amount of LFO modulation routed to a destination set in the WHEEL-MOD section … applies the selected modulation continuously" [32] | None | To be built (S53-43) |
| 23 | LFO SAW ON/OFF | 0-1 | The low-frequency oscillator's sawtooth; "Any of these waveshapes can be enabled simultaneously" [32] | Switch `LfoSawtooth` (11) | Built |
| 24 | LFO TRI ON/OFF | 0-1 | Its triangle [32] | Switch `LfoTriangle` (12) | Built |
| 25 | LFO SQUARE ON/OFF | 0-1 | Its square [32] | Switch `LfoSquare` (13) | Built |
| 26 | LFO SOURCE MIX | 0-120 | Wheel-Mod's "ratio between two modulation sources: LFO and Noise"; counter-clockwise all LFO, clockwise all noise [32] | Knob `SourceMix` (18) | Built |
| 27 | LFO FREQ A ON/OFF | 0-1 | Wheel-Mod "to Osc A frequency" [32] | Switch `WheelFrequencyA` (16) | Built |
| 28 | LFO FREQ B ON/OFF | 0-1 | Wheel-Mod "to Osc B frequency" [32] | Switch `WheelFrequencyB` (17) | Built |
| 29 | LFO FREQ PW A ON/OFF | 0-1 | Wheel-Mod "to Osc A square wave pulse width" [32] | Switch `WheelPulseWidthA` (18) | Built |
| 30 | LFO FREQ PW B ON/OFF | 0-1 | Wheel-Mod "to Osc B square wave pulse width" [32] | Switch `WheelPulseWidthB` (19) | Built |
| 31 | LFO FILTER ON/OFF | 0-1 | Wheel-Mod "to Filter cutoff frequency" [32] | Switch `WheelFilter` (20) | Built |
| 32 | POLY MOD FILT ENV AMOUNT | 0-127 | "the amount of modulation from the Filter Envelope that is applied to a selected destination" [35] | Knob `PolyModFilterEnvelope` (20) | Built |
| 33 | POLY MOD OSC B AMOUNT | 0-120 | "the amount of modulation from Oscillator B" [35] | Knob `PolyModOscB` (19) | Built |
| 34 | POLY MOD FREQ A ON/OFF | 0-1 | Poly-Mod to "Oscillator A frequency" [35] | Switch `PolyModFrequencyA` (8) | Built |
| 35 | POLY MOD PW ON/OFF | 0-1 | Poly-Mod to oscillator A's pulse width [35] | Switch `PolyModPulseWidthA` (9) | Built |
| 36 | POLY MOD FILTER ON/OFF | 0-1 | Poly-Mod to "the Filter cutoff frequency" [35] | Switch `PolyModFilter` (10) | Built |
| 37 | VINTAGE | 0-127 | "lets you dial in progressively more of this character as you go from a very stable 4 (as in Prophet-5 Rev4 …) all the way to 1 (as in Prophet-5 Rev1 …)": "progressively more randomness to the behavior of the individual VCOs, filters, envelopes, and amplifiers" [36]. Which end of 0 to 127 is "4" is not stated in the source | None (synth5x has fixed per-voice tolerances, `law.rs` `tolerance`) | Kept; open question 2 |
| 38 | AFTERTOUCH > FILTER | 0-1 | Pressure "will open the filter wider" [38, 39] | None | Kept; open question 2 |
| 39 | AFTERTOUCH > AMP (read: to the LFO) | 0-1 | Pressure "will apply modulation to the currently enabled destinations in the WHEEL-MOD section" [39] (contradiction C1) | None | Kept; open question 2 |
| 40 | ENV FILTER AMOUNT | 0-120 | "Sets the amount of modulation from the filter envelope to the filter's cutoff frequency" [24] | Knob `FilterEnvelopeAmount` (9) | Built |
| 41 | VELOCTIY > FILTER | 0-1 | "Allows key velocity to influence filter cutoff frequency" [26] | None | Kept; open question 2 |
| 42 | VELOCITY > AMP | 0-1 | "Allows key velocity to influence volume" [30] | None | Kept; open question 2 |
| 43 | ATTACK FILTER | 0-120 | The filter envelope's attack time [26] | Knob `FilterAttack` (0) | Built |
| 44 | ATTACK VCA | 0-120 | The amplifier envelope's attack time [29] | Knob `AmplifierAttack` (4) | Built |
| 45 | DECAY FILTER | 0-120 | The filter envelope's decay time [26] | Knob `FilterDecay` (1) | Built |
| 46 | DECAY VCA | 0-120 | The amplifier envelope's decay time [29] | Knob `AmplifierDecay` (5) | Built |
| 47 | SUSTAIN FILTER | 0-120 | The filter envelope's sustain level [26] | Knob `FilterSustain` (2) | Built |
| 48 | SUSTAIN VCA | 0-120 | The amplifier envelope's sustain level [29] | Knob `AmplifierSustain` (6) | Built |
| 49 | RELEASE FILTER | 0-120 | The filter envelope's release time [26] | Knob `FilterRelease` (3) | Built |
| 50 | RELEASE VCA | 0-120 | The amplifier envelope's release time [29] | Knob `AmplifierRelease` (7) | Built |
| 51 | RELEASE SWITCH | 0-1 | "If the RELEASE switch is on, the RELEASE knob setting on the Filter and Amplifier envelopes is used. If the RELEASE switch is off, the Release on both envelopes is fast" [43] | Switch `Release` (15) | Built |
| 52 | UNISON ON/OFF | 0-1 | "only 1 note can be played at a time … powered by as many as five voices" [40] | Switch `Unison` (7) | Built (all five voices) |
| 53 | UNISON VOICE COUNT | 0-10 | "how many voices to stack" [40, 41], and "CHD", the chord memory, as a choice among them [41] | None | To be built (S53-42) |
| 54 | UNISON DETUNE | 0-7 | "A setting of 0 is minimum detuning. A setting of 8 is maximum detuning" [40], against the range 0 to 7; the interface's range is taken | None | To be built (S53-42) |
| 55-64 | UNISON NOTE | 1-10 | Not stated in the source. They are the only program parameters that could hold the chord memory, which "is saved with the program" [41]; the stated range, 1 to 10, cannot hold MIDI note numbers | None | Kept (left out, section 13) |
| 86 | PITCH WHEEL RANGE | 0-11 | "change this on a per-program basis to up to an octave", settings 1 to 12 [37] | None (fixed seven semitones, `PITCH_BEND_SEMITONES`) | To be built (S53-8) |
| 87 | RETRIGGER AND UNISON | 0-3 | The key priority mode for unison: "Low note priority (LO)", "Low note retrigger (LOr)", "Last note priority (LAS)", "Last note priority retrigger (LAr)" [45]; values 0 to 3 read in that order | None (unison is low note, no retrigger, today) | To be built (S53-42) |

**S53-37. The mapping of parameters to fields.** synth5x MUST set each field of `Patch` from the parameter the table of section 10.2 names for it, by S53-35 and S53-36: the 24 knobs from parameters 0, 1, 2, 8, 9, 13, 14, 15, 16, 17, 18, 21, 26, 32, 33, 40 and 43 to 50; the 22 switches from parameters 3 to 7, 10, 11, 12, 23 to 25, 27 to 31, 34 to 36, 51 and 52, and from parameter 19 (off at 0, on at 1 and 2, with S53-41 for 1). Every field of `Patch` MUST be set by exactly one parameter, and no parameter MUST set two fields.
- Reason: Every control of the instrument modelled has its parameter in the adopted interface; nothing synth5x has today is lost.
- Source: The table of section 10.2; MIDI Implementation, pages 8 and 9; synth53's source, `patch.rs`.
- Verification: A test, for each of the 46 fields, sets its parameter and checks that exactly that field changes; an assertion in the code checks that the mapping covers all 24 knobs and 22 switches once.

### 10.3 The parameters of the instrument's revisions

**What the 2020 instrument has.** Two controls name the revisions: the REV switch (parameter 20, "FILTER REV SELECT"), which chooses the filter of revisions 1 and 2 or of revision 3 and the matching filter envelope shape, while the oscillators stay the 2020 instrument's Curtis oscillators (User's Guide, pages 1, 22 and 25); and the VINTAGE knob (parameter 37), whose positions 4 to 1 are named for the 2020 instrument and revision 1 but which adds randomness, not a revision's circuits (page 36).

**What NeoTeletext has.** Three kinds, each a whole instrument: synth53 is revision 3 throughout (oscillators, filter, envelopes, the processor's laws), synth52 and synth51 revisions 1 and 2 throughout (DEC-6461). No program field chooses the revision.

**S53-38. The revision parameter is kept, and the kind decides.** Under open question 1, recommendation A: synth5x MUST NOT act on parameter 20; the kind alone chooses the revision. The parameter MUST be carried unchanged in every program, dump and bank, and a synth5x writer that makes a program from fields MUST write 1 for synth53 and 0 for synth52 and synth51. The Rust server MUST NOT refuse a program whose parameter 20 differs from its kind.
- Reason: DEC-6461 item 3: no model or revision field remains for a program to set; the kind is the instrument. Writing the kind's value means that a program made by NeoTeletext and sent to the 2020 instrument chooses the same filter. Not refusing means that a program from the 2020 instrument plays on any kind.
- Source: DEC-6461; User's Guide, pages 22 to 25. The value-to-revision reading of parameter 20 is section 14 item 2.
- Verification: A test plays one program with parameter 20 at 0 and at 1 on each kind and checks the samples identical per kind; a test checks that the server writes 1 for synth53 and 0 for the others and passes either through.

**S53-39. Vintage is kept.** Under open question 2, recommendation: synth5x MUST NOT act on parameter 37; it MUST be carried unchanged. Each voice's fixed tolerance stays as built.
- Reason: The User's Guide gives no figure for any randomness, no scale and not even which end of 0 to 127 is "4"; the instrument modelled has no such knob, and synth5x's per-voice tolerances already place it inside the spread of real units (DEC-6429).
- Source: User's Guide, page 36; synth53's source, `law.rs` (`tolerance`). Listed in section 13.
- Verification: A test plays one program with parameter 37 at 0 and at 127 and checks identical samples.

## 11. Voices, unison, glide and the wheels

**What the adopted interface says.** The 2020 Prophet-5 has five voices (User's Guide, page 1). Played polyphonically it "is set to last note priority so that any newly played notes take priority and will 'steal' voices when necessary"; "when you hold more than five notes, it will steal one of the voices to play the next note, and it will retrigger. … if you repeatedly hit the same key, it will not cycle through voices; it will retrigger the same voice" (page 45). In unison "the original Prophet-5 would always play all five voices (now you can stack 1-5 voices), it would always be low-note priority, and it would always play legato" (page 45). Ten voices are not described by either filed document.

**S53-40. Polyphony and voice assignment.** With parameter 52 off, synth5x MUST play up to five notes at once, assigning keys as built: each new key takes the voice used longest ago, a repeated key its own voice again, and with five keys held the next key takes the voice keyed longest ago and retriggers it. Parameter 87 MUST NOT change polyphonic assignment.
- Reason: It is the instrument modelled's and the 2020 instrument's assignment ("These modes do not affect polyphonic playing", page 45). synth5x has five voices, the instrument modelled's number.
- Source: User's Guide, pages 1 and 45; synth53's source, `mod.rs` (`VOICES` 5, `Synth53::mode`, TM3 section 2-2).
- Verification: The existing voice assignment tests pass unchanged.

**S53-41. Half keyboard tracking.** With parameter 19 at 1, the cutoff MUST follow the key at half the rate it follows it at 2 (full); at 0 it does not follow the key.
- Reason: The 2020 instrument has "off, half, full" (User's Guide, page 24); the instrument modelled has a switch, which is full. Half is read as half the key's voltage, as the name says; the exact share is not stated in the source.
- Source: MIDI Implementation, page 8; User's Guide, page 24. The share is NeoTeletext's reading (section 14 item 4).
- Verification: A test measures the cutoff of a self-oscillating filter at keys 36 and 60 with parameter 19 at 0, 1 and 2 and checks a rise of 0, 12 and 24 semitones within 1 semitone.

**S53-42. Unison: voices, detune and key priority.** With parameter 52 on, synth5x MUST sound one note at a time on several voices, thus.
1. *The count.* Parameter 53's value v from 0 to 4 MUST stack v + 1 voices, and values 5 to 10 MUST stack all five. The voices stacked are voices 1 to the count; the others are silent while unison is on.
2. *The detune.* With parameter 54 at d (0 to 7) and n voices stacked, voice k (0 to n − 1) MUST be tuned `(2k − (n − 1)) × d × 3 ÷ (n − 1)` cents from the note (for n = 1, 0 cents): the voices spread evenly over `±3d` cents, 21 cents either way at d = 7.
3. *The key priority.* Parameter 87's value MUST choose: 0, the lowest key held, envelopes started only when a key goes down with none held (the instrument modelled's unison and today's); 1, the lowest key, envelopes restarted by every key that takes the note; 2, the last key held, started only from silence; 3, the last key, restarted by every key that takes the note.
- Reason: The adopted interface has the count ("how many voices to stack"), the detune and the four modes (User's Guide, pages 40, 41 and 45). Value 0 of each reproduces the instrument modelled's unison with the default count of S53-30. The count's values: 0 to 10 is eleven values for counts the User's Guide gives as 1 to 5 on a Prophet-5 and the "CHD" chord; v + 1 voices is this document's reading, and counts above five, which a ten-voice instrument would reach, play all five of synth5x's. The size of a detune step is not stated in the source. synth5x's allocator already has the lowest and last priorities and the single and multiple triggers (`analog/allocator.rs`).
- Source: MIDI Implementation, pages 5, 8 and 9; User's Guide, pages 40, 41 and 45. The count's reading, the detune's law and the mode order are NeoTeletext's own (section 14 item 4), pending open questions 2 and 4.
- Verification: A test with unison on checks, for counts 0 to 10, the number of voices sounding; for detune 0, 3 and 7 with five voices, each voice's pitch within 0.5 cent of the law; and for each mode the key that sounds and whether the loudness envelope restarts, on the sequence: hold 60, then 64, then 55, release 55.

**S53-43. The low-frequency oscillator's initial amount.** The amount of Wheel-Mod that reaches the destinations parameters 27 to 31 select MUST be `min(1, parameter 22 ÷ 120 + wheel ÷ 127)` of the full amount, where `wheel` is controller 1's value.
- Reason: The 2020 instrument: "Setting an amount here applies the selected modulation continuously. If you set this parameter to zero but still select a modulation destination in the WHEEL-MOD section, modulation is only applied when you use the Mod wheel" (User's Guide, page 32). How the two combine is not stated in the source; their sum, held to the whole, makes the wheel add to a set amount and leaves the instrument modelled's behaviour at an initial amount of 0.
- Source: MIDI Implementation, pages 4 and 8; User's Guide, pages 32 and 38. The sum is NeoTeletext's own (section 14 item 4).
- Verification: A test with the triangle to oscillator A's frequency checks the vibrato's depth at initial amounts 0, 60 and 120 and wheel 0 and 127 against 0, 0.5, 1, 1, 1 and 1 of the full depth.

**S53-44. Glide.** Parameter 13 MUST set the glide's rate as built: in unison the note's pitch slides from the last note's to the new one's at the knob's rate, and at 0 it changes at once. Polyphonically synth5x MUST NOT glide.
- Reason: The instrument modelled's glide circuit follows the unison voltage (`law.rs`, glide, from TM3 sheet SD334), and synth5x keeps the modelled revisions' behaviour. The 2020 instrument's User's Guide says its glide "functions when the Prophet-5 is in either polyphonic or Unison mode" (page 39); that departure is listed in section 13 and in open question 2.
- Source: synth53's source, `mod.rs` (`glide`) and `law.rs`; User's Guide, page 39.
- Verification: The existing glide tests pass unchanged.

**S53-45. Master tune.** synth5x's master tune (±100 cents, `set_master_tune`) MUST NOT be set by any message of this interface.
- Reason: The adopted interface has no message for the MASTER TUNE knob, which is not part of a program (User's Guide, page 42; MIDI Implementation, pages 4 to 9). The global TRANSPOSE (parameter 4096) is left out (section 13).
- Source: User's Guide, page 42; MIDI Implementation, pages 8 and 9.
- Verification: A test checks that no message of section 4 to 8 changes the tuning.

**S53-46. Order, time, restatement and lost input.** Messages MUST be applied in the order and at the times the block gives them (the tick of 0.1 millisecond, MIDI-5 and MIDI-35); two instruments given the same events at the same times MUST give the same samples however the rendering is divided into calls. A parameter number message spread over several control changes MUST be applied as its parts arrive, each at its own time. When the receiver tells synth5x that input was lost, synth5x MUST release every note, lift the pedal and make the selection of S53-22 none (MIDI-76, MIDI-102), and MUST leave the edit buffer, the group, the wheels, brightness, the volume and the pitch wheel range as they stand. The server MUST restate synth5x's one part as the architecture document requires (MIDI-93 to MIDI-99: in a live sound's first block and at least once in every 50 blocks after, and at tick 0 of block 0 of every stored sound), and the restatement MUST be, in this order, at one tick and in one block: controller 32 at the value that chooses the present group (S53-13); then, if the edit buffer equals the program the last program change chose and no edit buffer dump has come since, that program change, and otherwise an edit buffer dump (S53-29) of the present edit buffer, which stands for the program change and every parameter moved since (MIDI-93's "that patch's message"); then registered parameter number 0 with the pitch wheel range, if the range is not the default of S53-8; then pitch bend, controller 7, controller 1, controller 64 and controller 74, each where it is not at its value after reset all controllers or, for controllers 7 and 74, at its value at the start of a sound (127 and 0). Such a restatement is at most about 200 bytes, well within a block.
- Reason: A stored sound must play identically for every viewer and at every loop. A lost block may have held a note off; it may equally have held parameters, which cannot be known, so they are left and the server's restatement restores them; the selection is cleared because a data entry to the wrong parameter is worse than none, and the server selects again before every data entry (MIDI-37). Restating moved parameters one by one as parameter number messages could take 1,072 bytes, more than a block (S53-26 (c)), and would then never fit (MIDI-98); the edit buffer dump carries the same state in 157 bytes, and a dump equal to the edit buffer changes nothing (S53-19, MIDI-97).
- Source: Decisions A2 and A3; DEC-6410; DEC-6462 item 1; the architecture document, MIDI-5, MIDI-35, MIDI-37, MIDI-76 and MIDI-93 to MIDI-102; synth53's source, `mod.rs` (`release_all`). Restating with the edit buffer dump is this document's use of MIDI-93's rules (section 14 item 15).
- Verification: A test renders one score with parameter messages in calls of 1, 7, 960 and 4,800 samples and checks the samples identical; the existing lost-block test passes for the three kinds, extended with a data entry after the loss that changes nothing; a server test drives a part through a program change, ten parameter changes, a range and a bend, plays the restatement into a fresh instrument and checks the two edit buffers, groups and controller states equal; a test plays a tune with and without a restatement at a seeded random tick of every block and checks the samples identical (MIDI-97).

## 12. What the Rust server takes for this family

**S53-47. The forms of a program the server takes.** Under DEC-6462 and the architecture document's MIDI-14 and MIDI-15, the Rust server MUST take a synth5x program from a channel's program in either of two forms, and a bank as a list of 1 to 40 programs of one group or as the program dumps themselves, and MUST turn either into the 159-byte program dump (for a bank) or the 157-byte edit buffer dump (for a live sound) that it sends: (a) the dump itself, byte for byte, which it checks by S53-28, S53-29 and S53-33 and passes on unchanged; or (b) the 67 parameters as named, typed fields, each an integer within its parameter's range, from which the server writes the 128 bytes by S53-33 (with parameter 20 by S53-38) and packs them by S53-32. The field names MUST be the adopted interface's parameter names in lower case with words joined by underscores, with the document's misprints corrected (`osc_a_saw`, `velocity_to_filter`, `aftertouch_to_lfo`), and the ten UNISON NOTE parameters as one list of ten; the server document gives the exact schema. The server MUST check every program, bank and edit buffer dump with the receiver's own code (MIDI-21), and MUST do all the packing (S53-32), the building of blocks and records, the splitting, the restatement (S53-46) and the reading of Standard MIDI Files (MIDI-112). The kits MUST hold no packing, no program layout, no block building, no restatement and no range table beyond what the generated schema gives (MIDI-22).
- Reason: The server is the one implementation; the kits are thin and equal (DEC-6462 items 1 and 3). A dump is what other tools and the 2020 instrument produce; named fields are what a program written by hand needs.
- Source: DEC-6462; decision A4; MIDI Implementation, pages 8, 9, 12 and 13.
- Verification: A test sends the same program in both forms and checks the server emits identical dumps; a test sends each field out of range and checks the typed refusal names it; the kits' tests check that the TypeScript and Python kits send identical messages for the same program.

---

## 13. What is left out of the adopted interface, and what departs

### 13.1 Messages and settings left out

| Item | Where | Why synth5x leaves it out |
|---|---|---|
| Everything transmitted (page 3), including note, controller, pitch bend, pressure and program change transmission, and the "Param Xmit" setting | Pages 1 and 3 | synth5x transmits nothing: a NeoTeletext instrument only receives. |
| The global settings as a whole: MIDI Channel, Param Rcv, MIDI Control, MIDI SysEx, MIDI Out | Page 1; User's Guide, pages 13 and 14 | Settings of the hardware's ports, with no program message. synth5x acts as the 2020 instrument does with the channel at ALL (S53-3), parameters received both as controllers and as parameter numbers (S53-21; a departure: the 2020 instrument takes one or the other), and controllers obeyed. |
| Global parameter 4096, TRANSPOSE, 0 to 24 ("−12 … 12 … Master Transpose control, 0 is centered", User's Guide, page 13) | Page 9 | A global setting of the instrument, not of a program; a sender transposes its notes itself. |
| 4097 MIDI CHANNEL (0 to 16), 4098 PARAM XMIT (0 to 2), 4099 PARAM RCV (0 to 2), 4100 MIDI CONTROL (0 to 1), 4101 MIDI SYSEX (0 to 1), 4102 MIDI OUT (0 to 3) | Page 9; User's Guide, pages 13 and 14 | As the global settings above. (The User's Guide gives MIDI Out four choices, Off, MIDI, USB and ALL, and the table 0 to 3; MIDI Channel's value for ALL is not stated in the source.) |
| 4103 LOCAL CONTROL (0 to 2: "OFF, SOn, ALL", User's Guide, page 14) | Page 9 | A setting of the hardware's own keyboard and panel, which synth5x does not have. |
| 4104 POT MODE (0 to 2: relative, passthru, jump) | Page 9; User's Guide, pages 14 and 15 | How the hardware's knobs take over from a program; synth5x has no knobs. |
| 4105 SUSTAIN MODE (0 to 1: release or hold) | Page 9; User's Guide, pages 15 and 43 | A global setting; synth5x acts on controller 64 as S53-14 says. |
| 4106 PEDAL MODE (0 to 1: normal or reversed) | Page 9; User's Guide, pages 15 and 16 | The wiring of an expression pedal at a jack. |
| 4107 ALT TUNINGS (0 to 15) | Page 9; User's Guide, pages 16 and 64 to 68 | A global setting; the tunings themselves are loaded by a system exclusive message the filed documents do not describe. (The User's Guide gives "Normal, 1…16", seventeen values, against the table's sixteen.) |
| 4108 VEL RESPONSE (0 to 7) | Page 9; User's Guide, page 16 | A global curve for velocity, which synth5x does not act on (S53-4). (The User's Guide gives seven curves, "0-6", against the table's eight.) |
| 4109 AFTERTOUCH RESPONSE (0 to 7) | Page 9; User's Guide, pages 16 and 39 | As velocity, for pressure (S53-7). |
| The device inquiry and its reply (`F0 7E <channel> 06 01 F7`, answered by `F0 7E <channel> 06 02 01 33 01 00 00 <three version bytes> F7`) | Page 10 | It identifies the hardware and its software version to a computer; synth5x answers nothing (contradiction C5 concerns its identifier). |
| Request Program Dump (`F0 01 31 05 <bank 0 to 7> <program 0 to 127> F7`), Request Program Edit Buffer Dump (`F0 01 31 06 F7`), Request Global Parameter Dump (`F0 01 31 0E F7`) | Page 11 | Requests for the instrument to transmit; synth5x transmits nothing. |
| Save Edit Buffer | Page 12 | It writes the hardware's memory, and its command byte is not stated in the source (contradiction C4). A synth5x sound's banks are fixed for its life (MIDI-65) and are made only by the channel's program through the server. |
| Global Parameters Data Dump (`F0 01 31 0F <data> F7`) | Page 13 | "Not recognized when received" by the 2020 instrument itself, and inconsistent (contradiction C8). |
| Controller 4, the foot controller | Page 2 | Its assignment is not stated in the source (S53-11). |
| Controller 0, and the most significant part of bank select | Page 2 (absent) | The adopted interface uses controller 32 alone; controller 0 is counted as ignored (S53-13, MIDI-64). |
| A program dump received in the middle of a sound, loading a place in memory | Page 12; User's Guide, pages 16 and 63 | A sound's banks are fixed for its life (MIDI-65); a program dump travels only in a bank (S53-28, MIDI-58). |
| The chord memory, parameters 55 to 64 | Pages 8 and 9; User's Guide, page 41 | Their meaning is not stated in the source, their stated range cannot hold notes, and the instrument modelled has no chord memory. They are kept and carried unchanged. |
| Velocity, parameters 41 and 42, with the velocity of note on | Page 8; User's Guide, pages 26 and 30 | Under open question 2's recommendation: the instrument modelled has no velocity, and no law of how far velocity moves the cutoff or the level is stated in the source. Kept and carried. |
| Aftertouch, parameters 38 and 39, with polyphonic key pressure and channel pressure | Pages 2 and 8; User's Guide, pages 38 and 39 | As velocity. Kept and carried. |
| Vintage, parameter 37 | Page 8; User's Guide, page 36 | S53-39. Kept and carried. |
| The filter revision select, parameter 20, as a switch | Page 8 | S53-38: the kind decides. Kept and carried. |
| Polyphonic glide | User's Guide, page 39 | S53-44: synth5x keeps the modelled revisions' glide in unison. |
| The 2020 instrument's low-frequency oscillator range of 0.022 Hz to 500 Hz | User's Guide, page 32 | synth5x keeps the instrument modelled's range, which its laws give from the technical manuals (`law.rs`, `lfo`). |
| A ten-voice instrument and any second layer ("Prophet-10") | Not in either filed document beyond the port name "Prophet-5/10" (User's Guide, page 4) | Not stated in the source. synth5x has five voices; unison counts above five play five (S53-42). |
| The panel's own operations: record, compare, live panel, basic preset, calibration, the A440 tone, the master tune knob, the pedal and control voltage jacks | User's Guide, pages 2, 3, 8 to 10, 42, 44, 52 to 56, 61 | Operations of the hardware with no message. |

### 13.2 Taken with a difference

| Item | The 2020 instrument | synth5x | Requirement |
|---|---|---|---|
| Channel | A setting: ALL or one channel | All channels alike (the setting ALL; MIDI-68) | S53-3 |
| Parameters received | Controllers or parameter numbers, by a setting | Both | S53-21 |
| Bank select values 0 and 10 | Not stated | Group 0, and the fifth factory group | S53-13 |
| Program dump received | Loads the place in memory | Carried only in a bank; in a block counted as ignored | S53-28 (MIDI-58, MIDI-65) |
| Program change to a program the sound lacks, or of 40 to 127 | Not stated | The default program, counted | S53-18 (MIDI-59) |
| A faulty edit buffer dump | Not stated | The default program, counted among refused patches | S53-29 (MIDI-63) |
| Reset all controllers | "Clears all MIDI controllers to 0, MIDI volume to maximum" | RP-015 as DEC-6464 understands it: the modulation wheel to 0, the pedal up, the selection none, the pitch wheel to its centre; the volume, brightness, the group, the program and the pitch wheel range unchanged. DEC-6464 is the reason. | S53-16 (MIDI-84) |
| Controller 7 | "MASTER VOLUME", 0 to 120, 120 full | The shared law on 0 to 127, 127 full; 120 is not full | S53-10 (MIDI-92) |
| All sound off, 120 | Not received | Silence within 256 samples | S53-20 (MIDI-86) |
| Mode messages 124 to 127 | Not received | Each as all notes off | S53-15 (MIDI-89) |
| Pitch wheel range | A parameter of each program, set by controller 70 and parameter 86; follows the program chosen | Set by controller 70, parameter 86 and registered parameter number 0, held to 12 semitones; a program change and an edit buffer dump do not change it (open question 5) | S53-8, S53-22 (MIDI-90) |
| Lost input | Not applicable | Notes released, the pedal lifted, the selection none | S53-46 (MIDI-102) |
| Knob scale on synth52 and synth51 | 0 to 120 | Scaled to the converter's 0 to 127 | S53-36 |

## 14. What NeoTeletext defines itself

Each item exists because the filed documents do not define it.

1. **Controller 120, all sound off (S53-20), the mode messages 124 to 127 as all notes off (S53-15), and registered parameter number 0 (S53-8, S53-22).** Not received by the 2020 instrument; the architecture document's common layer (MIDI-9, MIDI-86, MIDI-89, MIDI-90).
2. **The readings of the program's numbering and layout**: that byte n of a program holds parameter n (S53-33); that groups 0 to 4 of a dump are the user set and 5 to 9 the factory set, and bank select's values 0 and 10 (S53-13, S53-25); that parameter 20's value 0 is "1/2" and 1 is "3" (S53-38). Open question 4 asks to confirm them against the factory banks.
3. **The handling of parameter number messages at their edges (S53-21 to S53-23)**: a value above a parameter's maximum is its maximum; controller 6 clears the least significant part; either part of the parameter number selects with the other kept; an RPN other than the null one and number 0 deselects; an increment or decrement is one step, and of registered parameter number 0 is counted as ignored.
4. **The laws of the additions of the 2020 instrument that are to be built**: the pitch wheel range as value + 1 semitones, held to 12, 7 before any message (S53-8); half keyboard tracking as half (S53-41); the unison count as value + 1, the detune as an even spread of `±3d` cents, and the order of the four key priority modes (S53-42); the initial amount added to the wheel (S53-43). Each is the simplest reading of the User's Guide's words; none is stated as a number in the source.
5. **Withdrawn: controller 7 is no longer scaled.** An earlier version of this document scaled 0 to 120 onto the shared volume law; S53-10 now applies the architecture document's law on 0 to 127 (MIDI-92), which is not this document's own definition.
6. **Brightness as dial steps of the cutoff (S53-12).**
7. **Withdrawn: what reset all controllers does is no longer this document's own (S53-16).** It is the architecture document's rule (MIDI-84, DEC-6464).
8. **What happens to the edit buffer and the banks**: the mapping of a group to the bank whose dumps carry it (S53-18, S53-26); one bank a group, no two of one group in a sound (S53-26). What a missing program, the first program and a program dump in a block do is now the architecture document's (MIDI-58, MIDI-59, MIDI-61).
9. **The default program (S53-30).** Today's default, in the adopted interface's form.
10. **The pitch of a MIDI key (S53-6).** As built.
11. **How polyphonic key pressure would become one pressure (S53-7)**, should aftertouch be built.
12. **The five positions after byte 127 in a packed program (S53-31, S53-32)**: written 0, ignored when read.
13. **The scale of a knob on synth52 and synth51 (S53-36)**, pending open question 3.
14. **The field names of the server's typed program (S53-47)**, derived from the adopted interface's parameter names.
15. **The restatement of this family's part (S53-46)**: the group by controller 32, then the program change or, where parameters have moved, the edit buffer dump of the present edit buffer, under the architecture document's rules (MIDI-93).

## 15. Open questions for the owner

**1. A program's FILTER REV SELECT, when the kind already names the revision.**
The 2020 instrument has one set of oscillators and a switch for the filter and its envelope; NeoTeletext has three whole instruments, and DEC-6461 removed every model field from the program.
- *Option A: the kind decides; the parameter is kept, carried unchanged, and written to match the kind* (S53-38). A program of the 2020 instrument plays on whichever kind the channel chooses; nothing a program sets can contradict the kind.
- *Option B: the parameter switches the filter and filter envelope only*, as on the 2020 instrument: synth53's oscillators with synth52's filter, and the reverse. The interface is then followed exactly, but synth5x gains two hybrid instruments that no revision ever was, the filter and envelope code must be separable by model, and the kind no longer says what plays: a program would carry a revision setting, which DEC-6461 item 3 ruled out.
- *Option C: the server refuses a program whose parameter disagrees with its kind.* It is strict, but every program of the 2020 instrument made with the other switch position is refused, and a bank of mixed programs cannot be used at all.
- *Recommendation:* A.

**2. The 2020 instrument's additions: which to build.**
The instrument modelled lacks all of these; the 2020 instrument has them as program parameters or messages: velocity to filter and to amplifier (41, 42), aftertouch to filter and to the LFO amount (38, 39), Vintage (37), the LFO initial amount (22), the unison count, detune and four key priority modes (53, 54, 87), half keyboard tracking (19 at 1), the per-program pitch wheel range (86), brightness (controller 74), polyphonic glide, and the chord memory (55 to 64).
- *Option A: build every one.* Programs made on the 2020 instrument sound as their makers intended where they use them. But velocity, aftertouch and Vintage have no stated law, so their depth would be invented; the chord memory's bytes have no stated meaning; and polyphonic glide departs from the modelled schematic.
- *Option B: build none; carry all.* synth5x stays the instrument modelled; every program is carried unchanged, and those parameters are silent.
- *Option C: build those whose meaning is stated and which reduce to the instrument modelled at their default* (initial amount, unison count, detune, key priority modes, half tracking, pitch wheel range, brightness), and carry the others unbuilt (velocity, aftertouch, Vintage, chord memory, polyphonic glide).
- *Recommendation:* C. It is what this document specifies. Each of the unbuilt five can be added later without changing the program format, since its bytes are already carried.

**3. The knob scale on synth52 and synth51.**
The 2020 instrument's knobs run 0 to 120; revision 3's converter reaches 120 at the dial's 10, revisions 1 and 2's reach 127 (`law.rs`).
- *Option A: scale 0 to 120 onto 0 to 127* (S53-36). The same program reaches the same dial positions on every model, and the full travel of revisions 1 and 2.
- *Option B: take the value as the converter's number on every model.* Simpler and identical to synth53's, but on synth52 the dial's last 7 steps, a little over half a division, are unreachable, and every knob stands about 5 per cent lower than the same program puts it on synth53.
- *Recommendation:* A.

**4. May the factory program banks be decoded in a test to confirm the readings?**
The readings of section 14 item 2, the unison count's reading (S53-42) and the order of parameter 87's modes could each be confirmed by unpacking the 400 factory programs (`patches/Prophet-510-Factory-Programs-ReadMe1.03.zip`) and checking every byte against its parameter's range, the reserved bytes for zeros, and the original programs (group 5, programs 511 to 558, per `documents.tsv`) against the original patch sheets.
- *Option A: yes, as a validation test whose data stays outside the repositories*, as DEC-6428 item 6 allows ("used only to set the same patch in our emulator and the reference, never shipped").
- *Option B: no; the readings stand on the documents alone.*
- *Recommendation:* A. It replaces five readings by evidence at the cost of one test, and the files are already filed for that purpose.

**5. A program's own pitch wheel range, against the architecture's rule that a program change does not change the range.**
The adopted interface makes the pitch wheel range a parameter of each program (parameter 86, "on a per-program basis", User's Guide, page 37), so choosing a program sets its range. The architecture document sets one rule for every synthesizer: the range is set by registered parameter number 0 beside the interface's own message, and a program change does not change it (MIDI-90; its open question 5). This document follows the architecture (S53-8).
- *Option A (written): the architecture's rule.* A program change and an edit buffer dump do not change the range; parameter 86 sets it only when it arrives as controller 70 or as its parameter number message; the parameter 86 a program carries is kept and returned unchanged but not acted on at a program change. The pitch wheel behaves alike on every synthesizer, but a program made on the 2020 instrument for a range of an octave plays with whatever range was last set.
- *Option B: the adopted interface's rule.* A program change and an edit buffer dump set the range from the program's parameter 86, and registered parameter number 0 and controller 70 change it until the next program change. Programs of the 2020 instrument play as their makers meant; the architecture's MIDI-90 would need an exception for a family whose adopted interface stores the range in its patch.
- *Recommendation:* B, with MIDI-90 amended to say that where an adopted interface stores the range in its patch, choosing a patch sets it: the range is part of this interface's program, as every other parameter is, and DEC-6453 asks that the interface be followed. Until the owner rules, the document is written for A, as the architecture requires.

## 16. Differences from what is built today

What exists is described in `synthesizer-wire-format.html`, `programming-the-synthesizers.html` and synth53's source. Implementing this document changes the following.

**The program.**
1. Today a patch is 24 bytes: the original instrument's own program record (operation manual, section 6-7; `patch.rs`), each byte a knob 0 to 127 in its low seven bits and a switch in its top bit, nothing refused. It becomes the 2020 instrument's 128-byte program (S53-33), carried as a 159-byte program dump in a bank and a 157-byte edit buffer dump live (S53-26 to S53-29), packed by S53-31. The 24 knobs and 22 switches, their meanings and their laws do not change; their coding does, and 21 parameters are added: 5 acted on under open question 2's recommendation (22, 53, 54, 86 and 87) and 16 kept (20, 37, 38, 39, 41, 42 and 55 to 64).
2. Today's knob values 121 to 127 are reachable on synth53 and play as 120; under the new form they cannot be written. On synth52 and synth51 today's 0 to 127 become 0 to 120 scaled (S53-36).
3. Today's filter keyboard switch (on or off) becomes off, half or full; half is new (S53-41).
4. Today the wire's tag 5 ("model: 0 = revision 3, 1 = revisions 1 and 2") and the kit's `model` field ("revision_3", "revisions_1_and_2") choose the model; under DEC-6461 the kinds synth53, synth52 and synth51 replace the field (another session is renaming the code now). The record's extension that names the variant stays (DEC-6461 item 3); a program's parameter 20 never chooses it (S53-38).
5. Today's `Patch::DEFAULT` becomes the default program of S53-30, sounding identical.

**The bank and program change.**
6. Today a bank holds 1 to 32 patches and a program change chooses 0 to 31, with a second data byte of 0 in its four-byte slot, and a sound names one bank. It becomes 1 to 10 banks a sound, each 1 to 40 program dumps of one group, so up to 400 programs at group and program places, chosen by controller 32 and program changes 0 to 39 (S53-13, S53-18, S53-25, S53-26), and the program change is the ordinary two-byte MIDI message under decision A3 (MIDI-26).
7. Today a program change to a missing patch plays the default patch; it still will, and it will also be counted (S53-18, MIDI-59).

**The messages.**
8. Today synth5x takes controllers 1, 7, 64, 120, 121 and 123 only. It gains controller 32, controller 74, the 57 controllers of section 5.1 with parameter numbers, and the parameter number controllers 6, 38, 96 to 101 (sections 5 and 6). `Synth53` needs a way to set one parameter and an edit buffer distinct from the stored program; `set_patch` remains as the way a program change and a dump set all of them.
9. Controller 7 stays on 0 to 127 with the shared law (S53-10, MIDI-92); the adopted interface's 0 to 120 is not followed.
10. Controller 121 today leaves the volume, and it still will: every synthesizer answers it as RP-015 does (S53-16; DEC-6464, awaiting the owner's confirmation; MIDI-84). It will also clear the parameter selection and leave brightness, which it does not do today because neither exists today.
11. Today the pitch wheel bends seven semitones on every patch; it will bend 7 semitones until controller 70, parameter 86 or registered parameter number 0 sets another range, of 1 to 12 semitones (S53-8), pending open question 5. Today's patches carried as programs take parameter 86 at 6.
12. Today unison is all five voices, lowest key, no retrigger, no detune; it gains the count, detune and four modes (S53-42), whose value 0 and the default count are today's behaviour.
13. Today there is no initial amount and no brightness; both are added (S53-43, S53-12).
14. Today system exclusive cannot be expressed in a four-byte slot. Under decision A3 it can: the edit buffer dump is taken in a block and the program dump in a bank (S53-28, S53-29), every other system exclusive message is counted as ignored.
15. Today the server and the kit refuse a control change of any controller but 1, 7, 64, 120, 121 and 123 ("a control change is of controller 1, 7, 64, 120, 121 or 123"); for this family the server must allow the controllers of S53-2, and the kit's copy of the rule goes (MIDI-22).

**The server and the kits.**
16. Today the kit's 24-byte patch builder and its dial helper build patches in the kit (under whatever names the renaming of DEC-6461 gives them). Under DEC-6462 they go: the server takes the program as a dump or as named fields and does the packing (S53-47); the kits carry the generated types. The kit's program repeater goes too: the server restates (S53-46, MIDI-93 to MIDI-99).
17. The engine's patch size constant for this family, the analogue bank's family sizes (codec 11, today "24 a patch"), the records' counts (42 of this family's patches a record today) and the server's patch check and refusal messages all follow. The codec of this family becomes code 16 and its banks the bank codec, code 19, if the architecture document's open question 1 is answered as it recommends (S53-1, MIDI-107); its tag 5 gains a third value, so that synth52 and synth51 are told apart (MIDI-48). The architecture document carries the 159-byte dumps in a bank object (MIDI-55, MIDI-56) and the 157-byte edit buffer dump as one event (MIDI-27, MIDI-28).

**Tests and documents.**
18. The tests that build patches from bytes (`tests/synth53_instrument.rs` and the others of synth53 in the engine, the engine's `tests/synths.rs`, the server's and the kit's patch tests) change to programs. New tests are those each requirement's "Verification" names.
19. The module documentation of `patch.rs` ("The layout, and why this one", which gives the reasons the 2020 dump was not chosen) and of `mod.rs` (the list of messages taken) are rewritten to cite this document's requirements once they are rdm requirements. The two HTML documents in `teletext-reference/synthesizers/` describe the old form and are regenerated.
20. DEC-6453 item 4 describes the 24 bytes as an invented format; it is the original instrument's. The record should be corrected to say so, and that it is replaced because the 2020 instrument's MIDI interface is the adopted one (DEC-6456).
21. Today the mode messages 124 to 127 and registered parameter number 0 are not taken by this family; they will be (S53-15, S53-22, MIDI-89, MIDI-90). After lost input the selection of a parameter number becomes none (S53-46, MIDI-102).
