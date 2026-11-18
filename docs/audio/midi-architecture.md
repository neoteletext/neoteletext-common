# The MIDI architecture of NeoTeletext's synthesizers

**Purpose.** This document specifies the one MIDI architecture that all eleven of NeoTeletext's synthesizers share: what a channel's program expresses to the server when it plays or programs a synthesizer, what the server makes of it, and what travels in the audio profile's records to the receiver in the viewer's browser. It is the document every family document and the server, TypeScript, Python and integration documents of this set rest on. It is the basis for implementing the synthesizers' programming interface, its records and its receiver.

**Scope.** It covers: the model (synthesizer, variant, kind, family, part, patch, bank, stored sound, live sound, block, event); the MIDI 1.0 messages in general and which of them the architecture carries; the byte grammar of a block as a Standard MIDI File track-event list; how blocks of variable length are carried in the existing OBJECT and DATA records and kept by the receiver; system exclusive messages longer than a block; patches and banks; MIDI channels and parts; real-time parameter control; live and stored sounds; the codec numbers and versions; Standard MIDI Files as input; every bound the receiver and the server enforce; and a table of the eleven synthesizers. It does not specify any one synthesizer's messages, controllers or patch bytes: each family document does that, inside the frame this document sets. It does not name the JSON fields of the program protocol (the server document does) or the calls of the kits (the TypeScript and Python documents do).

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

Which instrument each synthesizer models is said once, in `synthesizers.md` in this folder, with the trademark statement. The makers' names appear below only where a source is cited.

**What this document decides, in brief** (each item is specified by the requirements cited):
1. Every synthesizer is played and programmed with standard MIDI 1.0 messages, those its adopted interface defines (MIDI-1 to MIDI-12). A program expresses them to the server as typed JSON at the level of the adopted interface (MIDI-13 to MIDI-22); the server validates them and makes the records (DEC-6462).
2. A block is 20 milliseconds and its content is a Standard MIDI File track-event list with a tick of 0.1 millisecond: no running status, no continuation packets, no meta events, at most 1,005 bytes and 256 events (MIDI-23 to MIDI-38).
3. Blocks become variable in length. A DATA record of a synthesizer's sound carries each block with a two-byte length before it and the byte offset of its first block; the OBJECT record states the sound's total bytes (MIDI-39 to MIDI-49).
4. A system exclusive message longer than one event in a block travels only as a stored bank object, never split across events or blocks (MIDI-50 to MIDI-53).
5. A bank is a stored object holding the adopted interface's own dump bytes, verbatim, or for a synthesizer whose interface has no dump, the list of its control values; a sound names 1 to 10 banks; a program change chooses a patch; a faulty patch is replaced by the family's default and counted, and the server refuses it before it is ever sent (MIDI-54 to MIDI-66).
6. Where the adopted interfaces differ on a behaviour common to all MIDI instruments (reset all controllers, all notes off, all sound off, the sustain pedal, mode messages, pitch bend range and resolution, volume), one rule holds for every synthesizer: reset all controllers follows the MIDI Association's RP-015 (DEC-6464), and the rest are set here (MIDI-84 to MIDI-92).
7. The server restates every part's state (bank, program or patch, and every parameter moved since) at least once a second in a live sound, and at the start of every stored sound, so that a viewer who joins late or loses a block is put right (MIDI-93 to MIDI-103).
8. The synthesizers move to new codec numbers, 12 to 19, and codecs 3 to 11 are retired; this is open question 1, because DEC-6461 item 3 said the codec numbers would not change (MIDI-107 to MIDI-111). DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation), amending DEC-6461 item 3.
9. Standard MIDI Files are read by the server, not the kits (MIDI-112 to MIDI-120).
10. Every bound the receiver and the server enforce is listed in section 16 (MIDI-121 to MIDI-124), and the eleven synthesizers are tabled in section 17 (MIDI-125).

---

## 1. Sources

### 1.1 The filed documents of the adopted interfaces

All under `~/devel/teletext-reference/synthesizers/`. Page numbers are the printed page numbers where a page has one, with the PDF page in brackets where they differ.

| Short name here | File | What it is used for here |
|---|---|---|
| **ASID** | `sid/protocols/thomasj-asid-protocol.md` and `sid/protocols/thomasj-asid-implementations.md` | Through the family document `synth6581-synth8580.md`, which reads them: that the interface of synth6581 and synth8580 is system exclusive only, the largest message (41 bytes in block form), and the count of messages in a block. |
| **DX7 manual** | `dx7/manuals/yamaha-dx7-owners-manual-DX7E1.pdf` (34 pages) | Specifications, printed page 27 (PDF 28): 16 notes in poly mode, 1 in mono mode, 32 voices of internal memory, 32 of cartridge memory. MIDI data format, printed pages 30 to 32 (PDF 31 to 33): the channel messages transmitted and received, the controllers received (1, 2, 4, 5, 6, 7, 64, 65, 96, 97, 125, 126, 127), program change 0 to 63, pitch bend whose least significant byte is ignored on reception, the single-voice bulk dump (155 data bytes), the 32-voice bulk dump (4,096 data bytes), the parameter change (group 0 voice parameters 0 to 155, group 2 function parameters 64 to 77), active sensing. Its parameter table's LFO wave 0 ~ 4 (page 31) is a misprint; the TX7 and DX7 II manuals give 0 to 5. |
| **TX7 manual** | `dx7/manuals/yamaha-tx7-owners-manual.pdf` (48 pages, a scan) | Through the family document `synth7.md`, which read it: the maker's statement of the DX7 voice format: the single-voice and 32-voice dumps (printed pages 35 and 36), the parameter change with sub-group bits (page 36), voice parameters 0 to 156 and their codings (pages 38 and 39), function parameters 64 to 77 (page 41), the order of the single-voice data (page 41, section 4-5), and the 128-byte packed voice (page 44, section 4-8). |
| **DX7 II manual** | `dx7/manuals/yamaha-dx7ii-fd-d-owners-manual.pdf` (111 pages, a scan) | Through `synth7.md`: the same voice format restated, the voice parameters with the maker's initial voice (printed page Add-8) and the packed voice (Add-11). |
| **Grey Matter text** | `dx7/manuals/dave-benson-dx7-E-midispec.txt` | The MIDI implementation of a third-party replacement firmware for the DX7 ("GREY MATTER RESPONSE E!"), not of the stock DX7's formats; it says of the Yamaha formats that they "are well documented by YAMAHA, and therefore will not be explained here". It is used for nothing in this document. |
| **Juno-106 manual** | `juno/manuals/roland-juno-106-owners-manual-roland-cdn.pdf` (36 pages) | Specifications, page 32: six voices. MIDI Implementation Chart (PDF 34) and MIDI Implementation (PDF 35, unnumbered): the three MIDI functions, the messages recognised, program change 0 to 127 (groups A and B), the patch message (function type 0x30, 24 bytes), the manual message (0x31, 24 bytes), the parameter change (0x32, 7 bytes), the parameter number table 0 to 17. |
| **JU-06A chart** | `juno/manuals/roland-ju-06a-midi-implementation-chart.pdf` (2 pages, dated 5 September 2019, version 1.00) | The control changes for the Juno panel, including the Juno-60's switches (controllers 15, 28 and 93), program change 0 to 63, the channel mode messages and the system messages recognised. |
| **Voyager manuals** | `minimoog/manuals/moog-minimoog-voyager-user-manual-combo-os3.4-2008.pdf`, `moog-minimoog-voyager-rack-mount-edition-user-manual-os2.6-2005.pdf` and `moog-minimoog-voyager-user-manual-2003.pdf` | Through the family document `synthd.md`: the operating system 3.4 manual's controller map (printed pages 76 to 78) and chart (printed page 89), with the 2.6 manual as its second witness, give every control of the Voyager's panel a controller or a pair, the Voyager receiving controllers 1 to 31, 33 to 63 and 65 to 88, note on, pitch bend, all notes off and program change 0 to 127; the 2003 manual, of software version 1.0, names controllers 1 and 7 only; none documents the bytes of the system exclusive presets. |
| **Prophet-5 MIDI** | `prophet-5/manuals/Prophet-5-MIDI-Implementation-1.4.pdf` (13 pages) | All 13 pages: the channel messages received and transmitted (page 2 and 3), the control changes (pages 4 and 5), the NRPN messages, sent "in running status byte format" (pages 6 to 9), the device inquiry, the program dump and the edit buffer dump of 152 packed bytes (pages 10 to 13), and bank select by controller 32 (page 2). |
| **Prophet-5 guide** | `prophet-5/manuals/Prophet-5-Users-Guide-1.3_rev4.pdf` (80 pages) | Page 1 (PDF 12): "a five-voice, polyphonic analog synthesizer". Pages 5 and 6 (PDF 17 and 18): 400 programs, 200 factory and 200 user, in groups, banks of eight and programs. |
| **JUPITER-08 chart and reference manual** | `jupiter-8/manuals/roland-jupiter-08-midi-implementation-chart-v1.01.txt` (dated 1 October 2026, version 1.01, headed "MIDI Implementation Chart (Part)") and `jupiter-8/manuals/roland-jupiter-08-reference-manual-v1.00-panel-and-midi-pages.txt` (fifteen pages of the reference manual of Roland's 2026 Boutique sound module) | The control changes for the panel and the messages recognised (the part chart); each parameter's range and positions, without controller value bands (the manual's panel pages); the System chart, whose program change selects a step-sequencer pattern and which has no system exclusive. Read through `synth8.md`. |
| **Deckard's Dream manual** | `cs-80/manuals/black-corporation-deckards-dream-manual-1.3.0.pdf` (74 pages; its pages carry no printed numbers and are cited by PDF page) | PDF pages 16 to 18: three banks of 128 patches, "standard Program Change and Bank Change MIDI messages", bank change by controller 0 with values 0, 1 and 2. PDF pages 45 to 51: MIDI mode (channel pressure, polyphonic aftertouch, MPE), channel, 8 voices. PDF pages 71 to 74, "MIDI SPECIFICATIONS": its whole control change table. |

### 1.2 What the family documents found

The seven family documents were written beside this one, on 18 November 2026, and reconciled with it the same day. Each states its family's interface in full; this table gives only what this document takes from each.

| Document | What this document takes from it |
|---|---|
| `synthesizers.md` (this folder) | The eleven names and which instrument each models. |
| `synth6581-synth8580.md` | These two synthesizers take ASID register data messages (command 0x4E) only, accepting start and stop playback (0x4C and 0x4D) with no effect and passing over every other command (S6581-9); at most 20 register data messages to a block and at most 874 bytes a block, a family bound within MIDI-30 and MIDI-31 (S6581-42, S6581-43); no message longer than 41 bytes in block form, 39 after `0xF0` (S6581-6); no bank and no program change (S6581-51); a patch is a full register update of 37 bytes (S6581-50); the restatement is a full register update, at the interval of MIDI-96 (S6581-46). The document is complete (sections 1 to 9). |
| `synth7.md` | synth7 takes the DX7's channel messages and system exclusive, with RPN 0 beside function parameter 65 (S7-9); the single-voice bulk dump of 163 bytes is its patch and the 32-voice bulk dump of 4,104 bytes its bank, travelling only as a bank (S7-42); programs 0 to 31 choose from bank index 0 and 32 to 63 from bank index 1, the cartridge (S7-50); the packed 128-byte voice is as the TX7 manual states it (section 10); synth7's volume law is MIDI-82's with a slower slew (S7-15); an edited voice is restated as one single-voice dump (S7-49). |
| `synth106-synth60.md` | The Juno-106's 18 values are the whole programmable panel; a synth106 patch is the 24-byte patch message, a synth60 patch that message followed by the JU-06A's controllers 15, 28 and 93, 33 bytes (S106-31); the JU-06A chart gives no ranges or bands, so its scalings are NeoTeletext's own (S106-23, S106-24, S106-26); there is no bank select, so only bank index 0 is reachable (S106-10); a moved panel is restated as one patch message (S106-40). |
| `synthd.md` | synthD's patch is 60 control values in a fixed order, 46 of the Voyager's controllers and 14 of NeoTeletext's own (89, 90 and 102 to 113) for the controls only synthD has; a bank holds 1 to 128 of them; synthD takes no system exclusive (SD-17, SD-22, SD-27); its bend range is set by RPN 0 (SD-6); its restatement is SD-28. |
| `synth53-synth52-synth51.md` | The edit buffer dump of 157 bytes is the patch and the program dump of 159 bytes the bank's unit; a bank is 1 to 40 program dumps of one group, and a sound names one bank a group, up to 10 (S53-26); bank select is controller 32 (S53-13); a part is restated with an edit buffer dump of its present state (S53-46); controller 7 follows MIDI-82's law on 0 to 127, the interface's 0 to 120 being a departure (S53-10). |
| `synth8.md` | synth8's patch is 42 control values, 40 of the chart's controllers and NeoTeletext's own 107 and 108 (S8-16, S8-23); one bank of 1 to 64 patches, program change 0 to 63 on channels 1 and 2 (S8-12, S8-29); the channel map (S8-2); the key mode and split key stay in tag 7 (S8-18); RPN 0 sets the bend depth beside controller 41, the JUPITER-08's Bend Pitch (S8-14, S8-31); controller 57 is VCO-2's NORMAL / LOW FREQ switch and 63 moves VCO-2 RANGE (S8-16). |
| `synth80.md` | synth80's patch is 85 control values, 73 of Deckard's Dream's controllers and 12 of NeoTeletext's own, 20 to 31 (S80-18, S80-33); three banks of 128 chosen by controller 0, values 0 to 2 (S80-36); Deckard's Dream's glide mode moves from controller 120 to controller 3 (S80-20); pitch bend's range is set by RPN 0, default 3 semitones, at most 99 (S80-7); synth80 takes no system exclusive. |

### 1.3 Decisions this document follows

DEC-6453 (every instrument is programmed exactly as its most well-known existing interface does it; nothing invented while one exists), DEC-6461 (NeoTeletext's own names; each name its own kind), DEC-6462 (the Rust server is the core of the synthesizers' programming interface; a program sends structured typed JSON at the level of the adopted interfaces; the server validates it and turns it into the audio profile's blocks and records; the kits are thin), DEC-6410 (instruments are codecs of the audio profile; a block is 20 milliseconds of the instrument's input; instrument sounds are kept as their blocks and rendered as played), DEC-6429 (the analogue synthesizers), DEC-6428 (the clean-room rules), DEC-611 (live sounds join at the newest block), DEC-6464 (recorded as proposed and awaiting the owner's confirmation: every synthesizer answers Reset All Controllers the same way, by the MIDI Association's RP-015; and, as the owner asked on 18 November 2026, where two adopted interfaces differ on a common MIDI behaviour, this document sets one rule for all), and the provenance records DEC-6454 to DEC-6460, each of which names its instrument's adopted interface and its filed document.

The architecture decisions of the owner's brief of 18 November 2026 are cited as "decision A1" to "decision A6":
- **A1.** MIDI 1.0 is the one common layer: every synthesizer is played and programmed with the standard MIDI messages its adopted interface defines.
- **A2.** Inside the audio profile an instrument sound stays a sequence of 20 millisecond blocks at 48,000 Hz (960 samples), stored or live, carried in the existing OBJECT, DATA and CONTROL records and teletext packets; no new transport.
- **A3.** A block's content becomes a Standard MIDI File track-event list: delta time as a variable-length quantity, then a MIDI event, system exclusive in the form `F0 <length> …`. The tick is 0.1 millisecond. The fixed four-byte slots are replaced.
- **A4.** Patches travel in the adopted interface's own form; how a bank is stored and named, and how a system exclusive message longer than one block or one record travels, are this document's to specify.
- **A5.** Each of the eleven names is its own kind; variants of one family share their codec and code underneath.
- **A6.** Nothing is invented where the adopted interface defines it; every departure, omission and addition is listed with its reason.

### 1.4 What is built today

| Source | What it is used for here |
|---|---|
| `~/devel/teletext-reference/synthesizers/synthesizer-wire-format.html` and `programming-the-synthesizers.html` (both read from the code on 18 November 2026) | The wire format, the program protocol and the kit as built: section 21 lists what implementation changes. |
| The engine (`~/devel/neoteletext-renderer-teletext`, commit `dd0421c6`): `crates/neoteletext-audio/src/codec.rs`, `record.rs`, `store.rs`, `store/arena.rs`, `store/live.rs`, `encode.rs`, `profile.rs`, `receiver/instruments.rs`; `crates/neoteletext-audio-instruments/src/analog/volume.rs`, `synth7/rack.rs`, the instruments' `VOICES` constants, and `tests/control_sweep_support.rs` | The record layout, the store's layout of fixed blocks, the live ring, the render budget, the volume law, the voice counts and the measure of a click. |
| The server (`~/devel/neoteletext-app-server`, commit `df662b9`): `crates/teletext-runtime/src/protocol.rs` | Program protocol 12, the line limit of 16 MiB, the bounds on instrument sounds. |
| The TypeScript kit (`~/devel/neoteletext-server-ts-protocol`): `src/sound/midi-file.ts`, `src/sound/program-repeater.ts` | The Standard MIDI File reader and the program-change repeater as built, which move into the server under DEC-6462. |

### 1.5 The filed MIDI standards

The MIDI standards this document rests on are filed in `~/devel/teletext-reference/midi/`, each with its SHA-256, size and source address in that folder's `documents.tsv`, and each recorded in rdm as a source (DEVELOPMENT.md section 3.7). They were filed on 18 November 2026, and on the same day every statement of this document and of the family documents that rests on them was read against them and either confirmed, with its citation, or corrected (TODO-6466). A citation gives the document, the section or table, the printed page and, in brackets, the PDF page of the filed file.

| Short name here | File | rdm source | What it is and what it is used for here |
|---|---|---|---|
| **MIDI 1.0 4.2** | `mma-complete-midi-1.0-detailed-specification-96-1-third-edition.pdf`, PDF pages 28 to 113 | SRC-6469 | The MIDI 1.0 Detailed Specification, Document Version 4.2, revised February 1996, as printed in the MIDI Manufacturers Association's bundle "The Complete MIDI 1.0 Detailed Specification", document version 96.1, third edition. In its main text printed page n is PDF page n + 32; its Additional Explanations and Application Notes, pages A-1 to A-8, are PDF pages 91 to 98, and its Tables, pages T-1 onward, begin at PDF page 100. Used for: the status and data bytes (printed pages 3 and 6, PDF 35 and 38), running status (printed page 5, PDF 37; A-1 to A-3, PDF 91 to 93), the channel modes and the basic channel (printed pages 6 and 7, PDF 38 and 39; printed pages 20 to 23, PDF 52 to 55), velocity and note off (printed page 10, PDF 42), the controllers and their classes (printed pages 11 to 16, PDF 43 to 48), registered and non-registered parameter numbers and pitch bend sensitivity (printed pages 17 and 18, PDF 49 and 50), pitch bend (printed page 19, PDF 51), the channel mode messages (printed page 20 and printed pages 24 to 26, PDF 52 and 56 to 58), the hold pedal and all notes off (A-5, PDF 95), and Tables I to VII (pages T-1 to T-8, PDF 100 to 107). |
| **Standard MIDI Files 1.0** | the same file, PDF pages 128 to 143 | SRC-6469 | Standard MIDI Files 1.0, RP-001, revised February 1996, in the same bundle. Its printed page n is PDF page n + 129. Used for: the variable-length quantity (printed page 2, PDF 131), chunks (printed page 3, PDF 132), the header chunk, the formats and the division (printed pages 4 and 5, PDF 133 and 134), the track chunk, the grammar of a track event, running status in a file and the `F0` and `F7` system exclusive events (printed pages 5 to 7, PDF 134 to 136), meta events, end of track and set tempo (printed pages 7 to 10, PDF 136 to 139), and the calculation of time from ticks (printed page 14, PDF 143). |
| **GM Developer Guidelines** | the same file, PDF pages 306 to 333 | SRC-6469 | General MIDI System Level 1 Developer Guidelines, second revision, in the same bundle. Used only for its page 6 (PDF 315), "RPN/NRPN Null Function Value": the null parameter number, `7F 7F`, which it calls "MIDI 1.0 Approved Protocol JMSC-0011" and after which "subsequent Data Entry and Data Increment/Decrement commands are ignored". MIDI 1.0 4.2's own text does not state the null parameter number. |
| **RP-015** | `mma-amei-rp-015-response-to-reset-all-controllers.pdf` (3 pages) | SRC-6468 | The MIDI Manufacturers Association's and AMEI's Recommended Practice RP-015, "Response to Reset All Controllers", revised letter of agreement issued on 6 November 1998. Its page 2, "DETAILS", lists what controller 121 sets and what it leaves unchanged, the rule for every other controller and the documentation a manufacturer owes; its page 1 quotes MIDI 1.0's reception rule. It is not in the 96.1 bundle, whose appendix lists it as a later addition. DEC-6464 version 2 quotes it. |
| **MPE** | `mma-amei-rp-053-midi-polyphonic-expression-1.0.pdf` and `mma-amei-ca-034-mpe-configuration-rpn.pdf` | SRC-6470 | MIDI Polyphonic Expression, version 1.0 (RP-053), and the MPE configuration message, registered parameter number 6 (CA-034). Filed beside the others; no requirement of this document rests on them. |

Where this document says "MIDI 1.0" it means MIDI 1.0 4.2 as filed. The filed implementation charts corroborate part of what MIDI 1.0 says: the status bytes of the channel messages (DX7 manual, pages 30 to 32; Juno-106 manual, PDF 35; Prophet-5 MIDI, pages 2, 3 and 7), the channel mode messages 120 to 127 (JU-06A chart; Juno-106 manual, PDF 35; DX7 manual, page 32), the system common and system real-time messages by name (JU-06A chart; Juno-106 chart, PDF 34), the NRPN and RPN controllers 98 to 101, 6, 38, 96 and 97 (Prophet-5 MIDI, pages 6 and 7), and the system exclusive frame `F0 … F7` (every system exclusive message in the DX7 manual, the Juno-106 manual and the Prophet-5 MIDI).

---

## 2. Terms

- **Synthesizer.** One of NeoTeletext's eleven instruments, by its NeoTeletext name: synth6581, synth8580, synth7, synth106, synth60, synthD (`synthd` in identifiers), synth53, synth52, synth51, synth8, synth80.
- **Family.** The synthesizers that share one module of the engine, one codec and one family document: the synth6581 family (synth6581, synth8580); synth7; the synth106 family (synth106, synth60); synthD; the synth53 family (synth53, synth52, synth51); synth8; synth80. There are seven families.
- **Variant.** One synthesizer of a family that has more than one: synth8580 is a variant of the synth6581 family.
- **Kind.** What a program names when it sends a sound: each of the eleven names is a kind of its own (DEC-6461), with its stored sound, its live sound, its events message and, where the family has banks, its bank.
- **Adopted interface.** The existing programming interface a family takes under DEC-6453, as its filed document states it: ASID; the DX7's MIDI and system exclusive; the Juno-106's MIDI and system exclusive with the JU-06A's control changes; the Voyager's MIDI; the Prophet-5/10's MIDI implementation 1.4; the JUPITER-08's chart; Deckard's Dream's MIDI specification.
- **Family document.** The document of this set for one family: `synth6581-synth8580.md`, `synth7.md`, `synth106-synth60.md`, `synthd.md`, `synth53-synth52-synth51.md`, `synth8.md`, `synth80.md`.
- **Message.** A MIDI 1.0 message: a status byte (top bit set) and its data bytes (top bit clear), or a system exclusive message `F0 … F7`.
- **Channel.** A MIDI channel, numbered 1 to 16 in prose and 0 to 15 in the low four bits of a channel message's status byte. In this document "channel" always means a MIDI channel; the audio profile's four channels, on which a CONTROL record plays a sound, are called **audio channels**.
- **Part.** What one MIDI channel addresses inside one sound: a set of voices playing one patch. How many parts a synthesizer has and which channels address them is its family document's (section 10).
- **Patch.** Everything that sets a part's sound, in the adopted interface's own form: a system exclusive dump, or for a family whose interface has none, the list of its control values in an order the family document fixes, or for the synth6581 family a full register update.
- **Bank.** An ordered set of patches that a program change chooses among, stored as an object of its own (section 9).
- **Bank image.** The bytes of a bank: the adopted interface's dump messages, verbatim, or the family's fixed-size patches back to back (MIDI-56).
- **Sound.** What a CONTROL record plays on an audio channel: an OBJECT record and its blocks. A **stored sound** is sent whole and played by commands; a **live sound** is announced once and fed with blocks as it plays.
- **Block.** 20 milliseconds of a sound's input: 960 samples at 48,000 Hz (decision A2). Its content is an event list.
- **Tick.** 0.1 millisecond, the unit of time inside a block (decision A3). A block is 200 ticks, numbered 0 to 199.
- **Event.** One entry of a block's event list: a delta time and one MIDI message. Its **time** is its tick within the block.
- **Delta time.** The ticks from the previous event of the block, or from the block's start for the first event, as a variable-length quantity.
- **Variable-length quantity.** Standard MIDI Files 1.0's coding of a number in bytes of seven bits, most significant first, every byte but the last with its top bit set (Standard MIDI Files 1.0, printed page 2, PDF 131: "These numbers are represented 7 bits per byte, most significant bits first. All bytes except the last have bit 7 set, and the last byte has bit 7 clear"). Here only its **minimal** form is allowed: no leading byte of `0x80`.
- **Event codec.** A codec of the audio profile whose blocks are event lists: the seven synthesizer codecs of MIDI-107.
- **Restatement.** The messages that bring a part (or, for the synth6581 family, the chip) from any state to the state it should be in: section 12.
- **Passed over and counted.** What the receiver does with something it does not act on: it changes nothing, skips it, and adds one to a counter the port can read. Nothing is an error that stops a sound.
- **Refused.** What the server does with a program's message that breaks a rule: it sends nothing of it and answers the program with a typed refusal naming the field's path, the rule and the detail (DEC-6462 item 2).
- **Framing error.** A fault in a block that leaves the receiver unable to find where the next event begins (MIDI-33).
- **Content error.** A fault in one event whose extent is known, so the receiver can skip exactly that event (MIDI-34).
- **The common layer.** The few MIDI 1.0 messages every family that plays notes acts on, whether or not its adopted interface names them (MIDI-9).
- **The server.** neoteletext-app-server, the one implementation of the programming interface (DEC-6462).
- **The receiver.** The engine's audio receiver, `neoteletext-audio`, running in the browser's confined decoder process.

Numbers written `0x…` are hexadecimal. Bits are numbered from 0, the least significant. "Byte" is eight bits.

---

## 3. The model

**MIDI-1. The eleven synthesizers and their seven families.** NeoTeletext MUST have exactly these synthesizers, in these families, each family with one codec, one module of the engine and one family document:

| Family | Synthesizers (kinds) | Engine module | Adopted interface |
|---|---|---|---|
| synth6581 | synth6581, synth8580 | `synth6581` | ASID (DEC-6460) |
| synth7 | synth7 | `synth7` | The DX7's MIDI and system exclusive (DEC-6460) |
| synth106 | synth106, synth60 | `synth106` | The Juno-106's MIDI and system exclusive, and the JU-06A's control changes (DEC-6454) |
| synthD | synthD | `synthd` | The Voyager's MIDI and controller map, version 3.4 of its operating system, with NeoTeletext's own controllers for the controls only synthD has (DEC-6455, DEC-6465 answers 23 and 24; `synthd.md`) |
| synth53 | synth53, synth52, synth51 | `synth53` | The Prophet-5/10's MIDI implementation 1.4 (DEC-6456) |
| synth8 | synth8 | `synth8` | The JUPITER-08's MIDI implementation chart 1.01 (DEC-6457) |
| synth80 | synth80 | `synth80` | Deckard's Dream's MIDI specification, manual 1.3.0 (DEC-6458) |

synth52 and synth51 are one model today; the kind still chooses which name the sound carries.
- Reason: The owner's names and their kinds (DEC-6461), and the interfaces researched and filed for each (DEC-6453 to DEC-6460).
- Source: DEC-6461 items 1, 3 and 5; DEC-6454 to DEC-6460; `synthesizers.md`.
- Verification: Inspection: the server's protocol schema has exactly these eleven names as sound kinds, and the engine has exactly these seven modules; a test lists the codecs the engine knows and checks one per family.

**MIDI-2. Every synthesizer is addressed with standard MIDI 1.0.** Every synthesizer MUST be played and programmed only with MIDI 1.0 messages: the channel messages, the control changes (including registered and non-registered parameter number sequences and bank select), program change, pitch bend, channel pressure, polyphonic key pressure and system exclusive, each as its adopted interface defines it. No synthesizer MUST be played or programmed by a message, record, field or format that is not a MIDI 1.0 message, except the audio profile's own records (OBJECT, DATA and CONTROL), which carry the messages and play the sounds, and the bank image of a family whose adopted interface has no patch dump (MIDI-56).
- Reason: Decision A1: one common layer, the one every existing tool, file and musician already uses; nothing invented while one exists (DEC-6453).
- Source: Decisions A1 and A6; DEC-6453 items 1 to 3.
- Verification: Inspection of the receiver: the only input to a synthesizer is a MIDI message given by the event-list reader, and a bank's patches. A test feeds each synthesizer every message its family document lists and checks each has its stated effect.

**MIDI-3. A synthesizer's state belongs to its sound.** Each sound that a receiver plays MUST have its own instance of its synthesizer, made new when the sound starts, holding every part's patch, every controller value, every held note and every voice. Nothing that one sound's messages do MUST reach another sound, even of the same kind on another audio channel.
- Reason: Sounds start, stop, loop and are joined independently; a shared instrument would make one sound's program change change another's timbre.
- Source: As built: `receiver/instruments.rs` keeps one instrument in each of four lanes, made ready for one sound (`Lane::prepare`).
- Verification: A test plays two sounds of one kind on two audio channels, sends a program change and a controller in one, and checks the other's samples are unchanged.

**MIDI-4. A sound is a sequence of blocks, rendered as it is played.** A sound of a synthesizer MUST be a sequence of blocks of 20 milliseconds, each 960 samples at 48,000 Hz, mono, whose content is an event list (section 6). The receiver MUST keep a sound as its blocks and render each block when it is played, never render a whole stored sound ahead of time.
- Reason: Decision A2; a two-minute sound kept as events is a few kilobytes where its samples would be 11.5 MB.
- Source: Decision A2; DEC-6410 items 2, 6 and 13.
- Verification: The engine's existing test that every block of an instrument renders exactly 960 samples, run on event blocks; a test that a two-minute stored sound's receiver memory is its blocks' bytes and the store's tables, not its samples.

**MIDI-5. An event is a time and one message.** An event MUST be one MIDI message at one tick of one block. The receiver MUST give an event's message to the synthesizer immediately before it renders the sample numbered `floor(time × 24 ÷ 5)` of the block's 960, after rendering every earlier sample of the block (24 ÷ 5 = 4.8 samples a tick at 48,000 Hz).
- Reason: Decision A3 sets the tick; the formula is the one the receiver already uses, so a message lands on the same sample in every receiver.
- Source: Decision A3; `receiver/instruments.rs`, `render_slots` ("Tenths of a millisecond to samples at 48,000 Hz: 4.8 each"); `synth6581-synth8580.md`, S6581-40.
- Verification: A test places a note on at each tick from 0 to 199 in turn and checks the first sample that changes is `floor(time × 24 ÷ 5)`.

**MIDI-6. A patch, a bank and a program change.** For every family but the synth6581 family, a part's sound MUST be set by a patch, and a patch MUST be chosen from one of the sound's banks by a program change, or sent inline in a block as the adopted interface's own message (MIDI-60). For the synth6581 family a patch is a full register update, sent only inline, and there is no bank and no program change (`synth6581-synth8580.md`, S6581-50 and S6581-51).
- Reason: Decision A4; it is how each adopted interface chooses and sends a sound.
- Source: Decision A4; the family documents.
- Verification: The tests of section 9.

---

## 4. The MIDI messages in general

### 4.1 The messages MIDI 1.0 defines

The table lists every status byte of MIDI 1.0, as MIDI 1.0 4.2's tables give them: the channel messages and their data bytes in Tables I and II (pages T-1 and T-2, PDF 100 and 101), the channel mode messages in Table IV (page T-5, PDF 104), the system common messages in Table V (page T-6, PDF 105), the system real-time messages in Table VI (page T-7, PDF 106) and system exclusive in Table VII (page T-8, PDF 107). Every row was checked against those tables. The column "Also shown by" names the filed implementation charts that show the message too; "none" means that only MIDI 1.0 shows it.

| Status | Message | Data bytes | Also shown by |
|---|---|---|---|
| `0x8n` | Note off | key, release velocity | DX7 manual p. 32; Juno-106 manual PDF 35; Prophet-5 MIDI p. 2 |
| `0x9n` | Note on (velocity 0 is a note off) | key, velocity | DX7 manual pp. 30 and 32 ("v=0; Key OFF"); Prophet-5 MIDI p. 2 ("Note off if vvvvvvv = 0") |
| `0xAn` | Polyphonic key pressure | key, pressure | Prophet-5 MIDI p. 2; JUPITER-08 chart ("Aftertouch Key's") |
| `0xBn` | Control change, controllers 0 to 119 | controller, value | DX7 manual pp. 30 and 32; Prophet-5 MIDI pp. 2, 4 to 7 |
| `0xBn` | Channel mode messages, controllers 120 to 127: 120 all sound off, 121 reset all controllers, 122 local control, 123 all notes off, 124 omni off, 125 omni on, 126 mono on, 127 poly on | controller, value | JU-06A chart (all eight by name); Juno-106 manual PDF 35 (123 to 127); DX7 manual p. 32 (125 to 127); Prophet-5 MIDI p. 2 (121 and 123) |
| `0xCn` | Program change | program | DX7 manual p. 32; Juno-106 manual PDF 35; Prophet-5 MIDI p. 2 |
| `0xDn` | Channel pressure | pressure | DX7 manual p. 30 (transmitted); Prophet-5 MIDI p. 2 |
| `0xEn` | Pitch bend | least significant 7 bits, most significant 7 bits | DX7 manual p. 30; Juno-106 manual PDF 35; Prophet-5 MIDI p. 2 |
| `0xF0` | System exclusive start; the message runs to `0xF7` | any number of data bytes | DX7 manual p. 30; Juno-106 manual PDF 35; Prophet-5 MIDI pp. 10 to 13 |
| `0xF1` | MIDI time code quarter frame | 1 | None (MIDI 1.0 4.2, Table V, PDF 105) |
| `0xF2` | Song position pointer | 2 | JU-06A chart; Juno-106 chart (PDF 34) |
| `0xF3` | Song select | 1 | JU-06A chart; Juno-106 chart |
| `0xF4`, `0xF5` | Undefined | — | None (MIDI 1.0 4.2, Table V, PDF 105: "Undefined") |
| `0xF6` | Tune request | 0 | JU-06A chart; Juno-106 chart |
| `0xF7` | End of exclusive | 0 | DX7 manual p. 30 ("EOX") |
| `0xF8` | Timing clock | 0 | JU-06A chart ("Clock") |
| `0xF9`, `0xFD` | Undefined | — | None (MIDI 1.0 4.2, Table VI, PDF 106: "Undefined") |
| `0xFA`, `0xFB`, `0xFC` | Start, continue, stop | 0 | JU-06A chart |
| `0xFE` | Active sensing | 0 | DX7 manual p. 30 ("11111110"); JU-06A chart |
| `0xFF` | System reset | 0 | JU-06A chart |

A control change may also form, by MIDI 1.0's conventions, a **14-bit pair** (a coarse controller 0 to 31 and a fine controller 32 higher), a **bank select** (controllers 0 and 32), a **registered parameter number** sequence (controllers 101 and 100 select, 6 and 38 set, 96 and 97 step) and a **non-registered parameter number** sequence (controllers 99 and 98 select, with the same data controllers). The NRPN and RPN controllers are shown in the Prophet-5 MIDI, pages 6 and 7, and in MIDI 1.0 4.2's Table III (page T-3, PDF 102) and printed page 17 (PDF 49); the pairing of 0 to 31 with 32 to 63 is MIDI 1.0's ("controller numbers 32 to 63 are used to define an LSB byte for corresponding controllers 0 through 31", printed page 11, PDF 43), and so is bank select by controllers 0 and 32 (printed page 13, PDF 45). Whether a given interface uses a controller in this conventional way is that interface's to say (MIDI-74).

### 4.2 What the architecture carries

**MIDI-7. The messages carried.** A block MUST be able to carry, as events, exactly these messages: note off, note on, polyphonic key pressure, control change (controllers 0 to 127, which includes the channel mode messages, bank select, 14-bit pairs and RPN and NRPN sequences, each control change being one event), program change, channel pressure, pitch bend, and system exclusive messages of at most 256 bytes after the `0xF0` (MIDI-28). Which of these a synthesizer acts on is its family document's (MIDI-10).
- Reason: These are the messages every adopted interface plays and programs its instrument with (decision A1).
- Source: Decision A1; section 4.1; the adopted interfaces' charts (section 17).
- Verification: A test builds one block holding one event of each status `0x80` to `0xEF` and one system exclusive message, passes it through the server's check and the receiver's reader, and checks each event reaches the synthesizer with its time and bytes unchanged.

**MIDI-8. The messages never carried, and why.** A block MUST NOT carry these messages; the server MUST refuse a program's message that holds one where it would go into a block (except as section 15 says for a Standard MIDI File, whose meta events the server resolves or drops), and the receiver MUST pass one over and count it (MIDI-34):

| Message | Why it is never carried |
|---|---|
| Timing clock `0xF8`, start `0xFA`, continue `0xFB`, stop `0xFC` | They drive a sequencer or arpeggiator to an outside tempo. No NeoTeletext synthesizer has a sequencer or an arpeggiator, and a sound's time is its blocks' ticks: each event already says when it happens. |
| Active sensing `0xFE` | It detects a broken cable. The audio profile already detects a stalled live sound (2,000 milliseconds with no block, MIDI-101) and a stored sound cannot be cut. The DX7 turns its sound off when active sensing stops for 666 milliseconds (DX7 manual, page 32); that behaviour belongs to a cable and is left out. |
| System reset `0xFF` | A sound is reset by being started; the audio profile's stop command ends it. In a Standard MIDI File `0xFF` begins a meta event, so it cannot be a message in an event list anyway. |
| MIDI time code quarter frame `0xF1`, song position pointer `0xF2`, song select `0xF3` | They position or choose a song in a sequencer's memory. A sound has no song memory and no position other than its block numbers. |
| Tune request `0xF6` | It asks an analogue instrument to calibrate its oscillators. NeoTeletext's synthesizers are in tune by construction. |
| Undefined `0xF4`, `0xF5`, `0xF9`, `0xFD` | MIDI 1.0 leaves them undefined (Table V, PDF 105; Table VI, PDF 106), and says a device that receives an undefined status byte should ignore it (printed page 6, PDF 38; A-2, PDF 92). |
| Local control, controller 122 | It disconnects an instrument's own keyboard from its sound. A NeoTeletext synthesizer has no keyboard of its own. |
| Standard MIDI Files meta events `0xFF type length …` | They are file-level information: tempo, time signature, key signature, names, markers, end of track. In a block, time is already in ticks, so tempo has no meaning; the rest describe a file, not a sound. The server resolves tempo when it reads a file (section 15). |
| Standard MIDI Files `0xF7 length …` events (continuation packets and escapes) | A continuation would split a system exclusive message across events, and so across blocks, where a lost block would leave half a message (section 8). An escape carries arbitrary bytes, which are either messages that MIDI-8 already excludes or not messages at all. |

- Reason: Decision A6 asks that every omission be listed with its reason. Each excluded message either serves only hardware or a sequencer, or is replaced by something the audio profile already does.
- Source: Decision A6; DEC-6453 item 2 (what serves only hardware may be left out); the reasons in the table.
- Verification: A server test for each row: a program's events message holding it is refused, naming the event. A receiver test for each row: a block holding it is played with the message counted and with samples identical to the same block without it.

**MIDI-9. The common layer.** Every synthesizer that plays notes (every family but the synth6581 family) MUST act on these messages, whether or not its adopted interface names them, each with the meaning MIDI 1.0 gives it (MIDI 1.0 4.2, Tables II and IV, PDF 101 and 104; printed pages 10, 12, 20 and 24 to 25, PDF 42, 44, 52 and 56 to 57): note off; note on, a velocity of 0 being a note off; pitch bend; controller 7, volume (MIDI-82); controller 64, the sustain pedal (down at 64 to 127, up at 0 to 63); controller 120, all sound off; controller 121, reset all controllers; controller 123, all notes off; and controllers 124, 125, 126 and 127 each as all notes off, changing neither which channels the synthesizer hears nor its voice assignment. Each of these behaviours MUST be the same in every family, as section 11.1 specifies (MIDI-84 to MIDI-101); where an adopted interface differs, section 11.1's rule holds and the family document lists the departure. Where an adopted interface gives one of the controllers 120 to 127 another meaning, MIDI 1.0's meaning MUST win and the family document MUST move that parameter to another controller or NRPN, listing it as a departure.
- Reason: A sound must be able to be silenced and every note released at any time, in every family, by the same message; a server that writes restatements and ends stored sounds needs them; and controllers 120 to 127 are reserved by MIDI 1.0 for these messages. Deckard's Dream's specification gives controller 120 to "GLIDE MODE" (Deckard's Dream manual, PDF 74), which would turn a standard all sound off into a change of glide mode.
- Source: MIDI 1.0 4.2, as cited in the statement; JU-06A chart (all sound off, reset all controllers, all notes off recognised; omni and mono and poly "Same process as All Notes Off"); Juno-106 manual PDF 35 ("Mode messages (123 - 127) are also recognized as ALL NOTES OFF"); as built (`receiver/instruments.rs`, `CONTROLLERS = [1, 7, 64, 120, 121, 123]`); `synthd.md`, SD-13.
- Verification: A test for each family that plays notes: hold three notes, send each of 120, 121, 123, 124, 125, 126 and 127 in turn, and check the stated effect; with the pedal down, check 123 leaves notes held as MIDI 1.0 says ("A Hold or Sustain pedal 'On' message takes priority over Note Off and All Notes Off until it is released", A-5, PDF 95) and 120 silences them.

**MIDI-10. Each family document restricts the set.** Each family document MUST give a complete table of the messages its synthesizers act on, within MIDI-7 and including the common layer of MIDI-9: every status, every controller number (with its range, value bands and resolution), every NRPN and RPN number, every system exclusive message (its exact bytes and length), and program change's range. Every message carried by MIDI-7 that the table does not list MUST be refused by the server and passed over and counted by the receiver.
- Reason: The architecture carries the union of what the interfaces need; each synthesizer acts on its own interface's part of it, and nothing else.
- Source: Decisions A1 and A6.
- Verification: For each family, a receiver test sends one message of every status `0x80` to `0xEF`, every controller 0 to 127 and one system exclusive message of a foreign manufacturer, and checks that exactly the listed ones change the synthesizer's state and every other is counted; a server test checks every other is refused.

**MIDI-11. A data byte with its top bit set is never a data byte.** Every data byte of every message (every byte after a channel message's status, and every byte between `0xF0` and `0xF7`) MUST be 0x00 to 0x7F. The server MUST refuse a program's message with such a byte; the receiver MUST treat it as a framing error in a channel message (MIDI-33) and as a content error in a system exclusive message (MIDI-34).
- Reason: MIDI data bytes carry seven bits (MIDI 1.0 4.2, printed page 6, PDF 38: "Data bytes are eight-bit binary numbers in which the Most Significant Bit (MSB) is always set to binary 0"; Table VII, note 2, PDF 107: "All bytes between the System Exclusive Status byte and EOX must have zeroes in the Most Significant Bit"; ASID's own words, "All MIDI data bytes are 7-bit values"); a byte with its top bit set is a status byte.
- Source: MIDI 1.0 4.2, printed page 6 (PDF 38) and Table VII (PDF 107); `thomasj-asid-protocol.md`, "Original ASID protocol"; `synth6581-synth8580.md`, S6581-5.
- Verification: A fuzz target and a test placing `0x80` in each data position of each message kind.

### 4.3 Running status

**MIDI-12. No running status in a block.** Every channel message in a block MUST be written with its status byte. A byte below `0x80` where an event's status is expected is a framing error (MIDI-33). The server MUST accept running status in what a program sends where a program sends raw MIDI bytes (a Standard MIDI File, or a sequence of MIDI bytes in an events message, MIDI-16) and MUST write each such message with its status byte in full. In expanding it the server MUST follow MIDI 1.0's rules: running status applies to channel voice and channel mode messages only ("For Voice and Mode messages only", printed page 5, PDF 37); it is cleared by a system exclusive or system common message and left as it was by a system real-time message (A-2, PDF 92, the running status buffer's rules 3 and 4); and in a Standard MIDI File system exclusive and meta events cancel it, and the first event of each track must give its status (Standard MIDI Files 1.0, printed pages 6 and 7, PDF 135 and 136). A data byte where a status is expected and no running status is in effect MUST be refused.
- Reason: Each block must be readable alone, because a live sound's blocks can be lost: a running status carried from one block into the next would give the next block's first message the wrong meaning after a loss. Within one block, allowing it would save at most one byte an event, and the receiver's reader is simpler and its faults fewer without it. Programs and files commonly use running status (the Prophet-5's own NRPN messages are transmitted "in running status byte format", Prophet-5 MIDI page 6), so the server, which reads them, expands it. A block so written is still valid Standard MIDI File track data, which permits but does not require running status ("status bytes of MIDI channel messages may be omitted if the preceding event is a MIDI channel message with the same status", Standard MIDI Files 1.0, printed page 6, PDF 135).
- Source: Decision A3; Prophet-5 MIDI, page 6; MIDI 1.0 4.2, printed page 5 (PDF 37) and A-1 to A-3 (PDF 91 to 93), for what running status is and what clears it; Standard MIDI Files 1.0, printed pages 6 and 7 (PDF 135 and 136), for running status in a file. Option considered and rejected: running status within a block but not across blocks, saving about a byte an event at the cost of a second state in the reader.
- Verification: A server test sends a Standard MIDI File and an events message using running status and checks every event of the resulting blocks begins with its status byte; a server test sends a channel message's data bytes straight after a system exclusive message, with no status of their own, and checks they are refused; a receiver test gives a block whose second channel message omits its status and checks the rest of the block is passed over and counted.

---

## 5. What a program expresses to the server

DEC-6462 makes the server the one implementation of the synthesizers' programming interface. This section states, at the level of the MIDI architecture, what a program says to the server; the server document names the JSON messages and fields, and generates their schema from the server's Rust types.

**MIDI-13. The server is where the MIDI architecture is implemented.** A program MUST express sounds to the server as structured, typed messages at the level of the adopted interfaces: a patch, a bank, music as timed MIDI events or as a Standard MIDI File, and the audio profile's play, stop and gain. The server MUST validate every such message completely, turn it into OBJECT, DATA and CONTROL records as this document specifies, split what is too long, and write the restatements a live sound needs. No program, and neither kit, MUST write a block, a record or a bank image itself.
- Reason: One implementation, tested once, which every language a channel may be written in reaches for the cost of a thin client (DEC-6462, "Why").
- Source: DEC-6462 items 1 to 4.
- Verification: Inspection: the program protocol's schema has no field that carries a block's or a record's bytes; the server test suite holds the tests of this document's server-side requirements.

**MIDI-14. A patch as named, typed fields, or as the interface's own bytes.** A program MUST be able to give a patch in either of two forms, and the server MUST accept both for every family that has patches:
1. **named fields:** an object with one typed field for each parameter of the patch, named and ranged as the family document's parameter table gives, which the server encodes into the patch form of MIDI-54;
2. **the interface's bytes:** for a family whose patch form is a system exclusive message, the exact bytes of that message from `0xF0` to `0xF7`, as the adopted interface defines it (for example a DX7 single-voice bulk dump); for a family whose patch form is a list of control values, the values in the family document's order; for the synth6581 family, a full register update.

The server MUST check either form against every rule of the family document and MUST produce identical patch bytes from a named-field patch and from the interface's bytes of the same patch.
- Reason: DEC-6462 item 1 ("a patch as named, typed fields or as its standard system exclusive"); named fields are what a program writes, and the interface's bytes are what every existing librarian and file holds.
- Source: DEC-6462 item 1; decision A4.
- Verification: For each family, a server test encodes the family's default patch and three others from named fields and from bytes and checks the records are byte for byte equal.

**MIDI-15. A bank as a list of patches.** A program MUST be able to give a bank as an ordered list of 1 to 128 patches, each in either form of MIDI-14, and, for a family whose adopted interface has a whole-bank dump, as that dump's exact bytes (for example a DX7 32-voice bulk dump). The server MUST build the bank image of MIDI-56 from it.
- Reason: DEC-6462 item 1 ("a bank as a list of patches"); a bank dump is how existing sounds come.
- Source: DEC-6462 item 1; DX7 manual, page 30 (the 32-voice dump).
- Verification: For each family with banks, a server test sends a bank as a list and, where the family has one, as a dump, and checks the bank image.

**MIDI-16. Music as timed MIDI events.** A program MUST be able to give music as an ordered list of timed events, each a time (MIDI-17) and one message, the message given either as a typed object (a note on with its channel, key and velocity; a note off; a control change with its controller and value; a program change; a pitch bend with its 14-bit value 0 to 16,383 and centre 8,192; channel pressure; key pressure; an NRPN or RPN with its 14-bit parameter number and value, which the server writes as the interface's control-change sequence; a bank select with its value or values; a patch, MIDI-60; a named parameter, MIDI-18; a system exclusive message as its bytes) or as raw MIDI bytes (one or more messages, running status allowed, MIDI-12). The server MUST write each event into the block and tick its time falls in, in the order MIDI-35 gives.
- Reason: DEC-6462 item 1 ("music as timed MIDI events or a Standard MIDI File"). Typed objects carry a program's meaning; raw bytes carry what existing tools produce.
- Source: DEC-6462 item 1; decision A3.
- Verification: A server test gives the same music as typed objects and as raw bytes and checks identical blocks.

**MIDI-17. Time in a program's message.** An event's time MUST be given in whole microseconds from the start of the sound, 0 to 119,999,999 for a stored sound (6,000 blocks of 20,000 microseconds) and 0 to 2^53 − 1 for a live sound (counting from the live sound's start; the largest integer every language's JSON reader holds exactly, `protocol.rs`, `SAFE_INTEGER_LIMIT`, so a live sound may run for centuries; its block numbers wrap at 65,536 as today). The server MUST place an event at the absolute tick `floor((time + 50) ÷ 100)`, that is to the nearest tick with a half rounded up, in block `floor(tick ÷ 200)` at time `tick mod 200` within it. The server MUST compute each event's tick from its own time, never from the previous event's tick, so that no rounding error passes from one event to another: every event is within 50 microseconds of its stated time.
- Reason: Microseconds are exact for every frame interval a program is likely to state and are integers in every language's JSON; rounding once from the absolute time means a long sound keeps its tempo.
- Source: Decision A3; `synth6581-synth8580.md`, S6581-41 (how a tune's frame times become microseconds, which this rule then rounds).
- Verification: A server test places 10 minutes of events at multiples of 16,667 microseconds and of 19,950 microseconds and checks every event's tick against `floor((time + 50) ÷ 100)` and that the last event's error is no larger than the first's.

**MIDI-18. A named parameter.** A program MAY give a real-time parameter change as a named parameter of the family document's parameter table and a value in that parameter's own units or range. The server MUST write it as the one message the family document names for that parameter's real-time change (a control change, a pair of control changes, an NRPN sequence or a system exclusive parameter change), at the event's tick.
- Reason: It gives a program the parameter by name with its type checked, and still sends only the adopted interface's own message (decision A6).
- Source: DEC-6462 item 1 ("structured, typed JSON at the level of the adopted interfaces").
- Verification: For each family, a server test sends every named parameter at its lowest and highest value and checks the message written against the family document's table.

**MIDI-19. A stored sound.** A program's stored sound MUST name its kind, its handle and generation, its banks (for a family with banks, 1 to 10 bank handles, MIDI-57), its variant setting where the family has one in its OBJECT (for example the synth6581 family's clock), its events (MIDI-16) or its Standard MIDI File (section 15), and its length: either a length in microseconds, or a tail in microseconds that the server adds after the last event. The sound's blocks MUST be `ceil(length ÷ 20,000)`, at least 1 and at most 6,000.
- Reason: The audio profile needs the block count in the OBJECT; a program states how long the sound rings after its last event, which no event says.
- Source: As built (`SynthScore.build(tailMs)` in the kit); `protocol.rs`, `MOST_INSTRUMENT_BLOCKS`.
- Verification: A server test checks the OBJECT's block count for a length, for a tail, and refuses a length of 0 or over 120,000,000 microseconds.

**MIDI-20. A live sound and its events messages.** A program's live sound MUST be announced once (its kind, handle, generation, banks and variant setting) and then fed by events messages, each giving the events of a span of the sound and the time `until` (in microseconds from the live sound's start) up to which the program has now given every event. The server MUST write and send every block that ends at or before `until` and not yet sent, holding back the block in which `until` falls. One events message MUST advance `until` by at most 2,000,000 microseconds (100 blocks). An event whose tick lies in a block already sent MUST be refused (it is late).
- Reason: The server, not the program, now numbers and fills blocks; it needs to know when a block is complete, which only the program knows. The bound of 100 blocks a message is the one built today (`MOST_LIVE_INSTRUMENT_BLOCKS`).
- Source: DEC-6462 item 1; `protocol.rs` (`MOST_LIVE_INSTRUMENT_BLOCKS` = 100); `programming-the-synthesizers.html`, section 07 (the audio demo sends 10 blocks every 200 milliseconds).
- Verification: A server test sends events in steps of 200 milliseconds and checks each step sends exactly the completed blocks; a test sends an event for a block already sent and checks the refusal names it; a test checks an advance of 2,000,001 microseconds is refused.

**MIDI-21. The server checks with the receiver's own code.** The server MUST check every block it writes, every bank image and every patch with the same engine functions the receiver uses to read them, and MUST refuse a program's message that would produce any block, bank or patch those functions would pass over, count or replace with a default. A refusal MUST name the path of the field at fault, the rule broken (citing the requirement) and the detail (for example the event's index and its time, or the patch's index, byte and value).
- Reason: Then nothing a program can send is played differently from what it said, and the server's refusal is what tells the author; the receiver's own checks remain what security rests on (MIDI-123).
- Source: DEC-6462 item 2; REQ-6413 ("each block checked with the engine's code before it is sent"); the known gaps of `synthesizer-wire-format.html` section 12, where the server checked less than the receiver.
- Verification: A property test generates programs' messages, and for every one the server accepts, checks that the receiver's reader reports no event passed over, no block malformed and no patch refused.

**MIDI-22. The kits are thin.** The TypeScript and Python kits MUST hold no instrument logic: no patch packing, no block or record building, no Standard MIDI File reading, no restatement, and no copy of a server rule beyond what the schema states. Their types MUST be generated from, or checked against, the server's schema.
- Reason: DEC-6462 item 3; the TypeScript kit today holds about 4,300 lines of sound logic that duplicate the server's or precede it, which the Python kit lacks.
- Source: DEC-6462 items 3 and 4.
- Verification: Inspection of both kits; their commit gates check their schema copies against the server's.

---

## 6. The event block

### 6.1 Grammar

**MIDI-23. The grammar of a block.** The content of a block of an event codec MUST be a sequence of zero or more events and nothing else, with this grammar, where `VLQ` is a minimal variable-length quantity (MIDI-24) and every byte named is one byte:

```
block          = { event }
event          = delta message
delta          = VLQ                                  ; 0 to 199, MIDI-25
message        = channel-message | sysex | skipped
channel-message= status2 data data                    ; status 0x80-0xBF, 0xE0-0xEF
               | status1 data                         ; status 0xC0-0xDF
sysex          = 0xF0 length sysex-bytes              ; length = VLQ, 1 to 256, MIDI-28
sysex-bytes    = { data } 0xF7                        ; exactly `length` bytes, the last 0xF7
skipped        = 0xF7 length { any }                  ; escape or continuation, `length` bytes
               | 0xFF type length { any }             ; meta event, type 0x00-0x7F, `length` bytes
               | 0xF1 data | 0xF2 data data | 0xF3 data | 0xF6
               | 0xF8 | 0xFA | 0xFB | 0xFC | 0xFE
data           = a byte 0x00 to 0x7F
```

A writer (the server) MUST write only `channel-message` and `sysex` events. A reader (the receiver) MUST read every alternative of the grammar; a `skipped` event is passed over by its stated length and counted (MIDI-34). The bytes `0xF4`, `0xF5`, `0xF9` and `0xFD` in a message's place, and a data byte in a message's place, are framing errors (MIDI-33). Every event the writer writes is exactly a Standard MIDI File track event, so that the blocks of a sound are a Standard MIDI File track (MIDI-38). The `skipped` alternatives that are system common or system real-time messages written bare (`0xF1` to `0xF3`, `0xF6`, `0xF8`, `0xFA` to `0xFC` and `0xFE`) are not Standard MIDI File events: a track event is a channel message, a system exclusive event or a meta event, and a file carries a system common or real-time message only inside an `0xF7` escape event (Standard MIDI Files 1.0, printed page 6, PDF 135). The reader passes each over by the data bytes MIDI 1.0 gives it (Tables V and VI, PDF 105 and 106), a tolerance of NeoTeletext's own listed in section 19, so that a block that is not the server's and holds one is not lost whole.
- Reason: Decision A3 makes a block a Standard MIDI File track-event list. A reader that can skip every form a track may hold by its length lets a later version of this architecture add events an earlier receiver passes over, and lets a receiver survive a block that is not the server's.
- Source: Decision A3; Standard MIDI Files 1.0, printed pages 6 and 7 (PDF 135 and 136), for the forms of a track event ("<event> = <MIDI event> | <sysex event> | <meta-event>", a MIDI event being "any MIDI channel message"), the `0xF0` and `0xF7` system exclusive events and the meta event, whose type byte "is always less than 128"; MIDI 1.0 4.2, Tables V and VI (PDF 105 and 106), for the data bytes of the system common and real-time messages; MIDI-8 for what is never written.
- Verification: A receiver test reads one block holding one event of every alternative and checks which reached the synthesizer and which were counted; a fuzz target of the block reader (MIDI-124).

**MIDI-24. Variable-length quantities are minimal and short.** A delta time MUST be a variable-length quantity of one byte (0 to 127) or two bytes (128 to 199: `0x81` then the value less 128). A system exclusive length MUST be one byte (1 to 127) or two bytes (128 to 256: `0x81` then the value less 128, or `0x82 0x00` for 256). A skipped event's length MUST be at most two bytes. A variable-length quantity whose first byte is `0x80`, or that has a third byte, is a framing error.
- Reason: The largest numbers a block holds need two bytes; one coding for each number leaves no second way to write the same block, which the store's comparison of a block sent twice relies on (MIDI-44), and a bound on the bytes of a number bounds the reader.
- Source: Standard MIDI Files 1.0, printed page 2 (PDF 131), for the coding, whose examples include `81 00` for 128; the minimal form and the bound of two bytes are this document's; `synth6581-synth8580.md`, S6581-6, which writes the same two-byte form.
- Verification: A test of the reader on every one- and two-byte value 0 to 16,383, on `0x80 0x05` and on a three-byte quantity.

### 6.2 Time

**MIDI-25. An event's time and the block's end.** An event's time MUST be the sum of its delta time and the delta times of every event before it in the block, and MUST be 0 to 199. An event whose time would be 200 or more is a framing error: the receiver MUST pass that event and every later event of the block over and count them, and the server MUST never write one (an event at absolute tick T is always written in block `floor(T ÷ 200)`).
- Reason: A block is 200 ticks; an event past its end belongs to the next block, and a reader that let it through would play it in the wrong block.
- Source: Decision A3; `synth6581-synth8580.md`, S6581-40 (the same rule).
- Verification: A test gives a block whose third event's time reaches 200 and checks the first two are played and the rest counted.

**MIDI-26. A channel message's length.** A channel message with status `0x80` to `0xBF` or `0xE0` to `0xEF` MUST be followed by exactly two data bytes, and one with status `0xC0` to `0xDF` by exactly one. A program change or channel pressure MUST NOT carry a second data byte.
- Reason: MIDI 1.0's lengths (Table I, PDF 100: two data bytes for `8n`, `9n`, `An`, `Bn` and `En`, one for `Cn` and `Dn`; the DX7 manual, pages 30 and 32, and the Prophet-5 MIDI, page 2, show them too). As built a program change carried a second data byte of 0 in its four-byte slot; that byte goes.
- Source: MIDI 1.0 4.2, Tables I and II (PDF 100 and 101); DX7 manual, pages 30 and 32; Prophet-5 MIDI, page 2.
- Verification: A test of the reader for each status kind.

### 6.3 System exclusive in a block

**MIDI-27. The system exclusive event.** A system exclusive message in a block MUST be one event: `0xF0`, then its length as a variable-length quantity, then exactly that many bytes, which are every byte of the message after `0xF0`, the last of them `0xF7` and every other a data byte. An `0xF0` event whose last byte is not `0xF7` (Standard MIDI Files' form of a message continued in later packets) MUST be treated as a content error.
- Reason: Decision A3 ("system exclusive as `F0 <length> …`, so events of any length are carried"); a message must be whole in one event so that a lost block never leaves part of one (section 8).
- Source: Decision A3; Standard MIDI Files 1.0, printed pages 6 and 7 (PDF 135 and 136): a complete message is stored as "F0 <length> <bytes to be transmitted after F0>", the length counting the bytes after it and "not including the F0 or the length itself", with "the F7 at the end"; a message broken into packets has its last `F7` in a later `F7` event; `synth6581-synth8580.md`, S6581-6.
- Verification: A reader test with a complete message, one without its `0xF7`, and one with `0xF7` before its stated end.

**MIDI-28. The longest system exclusive event.** The length of a system exclusive event MUST be 1 to 256 bytes. A longer one is a content error to the receiver and MUST be refused by the server unless MIDI-58 lifts it into a bank.
- Reason: A bound on a message lets every synthesizer read one into a fixed buffer, as a `no_std` receiver must. 256 holds every timed message of every adopted interface: the largest is the DX7's single-voice bulk dump, 163 bytes in all (`F0`, 5 header bytes, 155 data bytes, a checksum, `F7`: DX7 manual, page 30), so 162 after `0xF0`; the Prophet-5's program dump is 159 bytes in all (Prophet-5 MIDI, page 12: `F0`, the 3 header bytes `01 31 02`, a group and a program byte, 152 bytes, `F7`); the Juno-106's patch message is 24 bytes (Juno-106 manual, PDF 35); ASID's longest is 39 after `0xF0` (`synth6581-synth8580.md`, S6581-6). Only whole-bank dumps are longer (the DX7's 32-voice dump is 4,104 bytes), and those travel as banks (section 8).
- Source: The documents named in the reason.
- Verification: A reader test at 256 and 257; a server test refusing a 257-byte message in an events message.

### 6.4 Bounds of a block

**MIDI-29. Skipped events.** The receiver MUST pass over a `skipped` event (MIDI-23) by its length, count it, and go on with the next event of the block.
- Reason: Forward compatibility and robustness; MIDI-8 says why none is written.
- Source: MIDI-8, MIDI-23.
- Verification: The test of MIDI-23.

**MIDI-30. The largest block.** A block MUST be at most 1,005 bytes. The figure is derived, and an assertion in the engine MUST hold it to its derivation: a record is at most 1,024 bytes; less its 4-byte header and 4-byte CRC-32, a body is at most 1,016 bytes; less the 9 bytes of an event codec's DATA fields (MIDI-42), 1,007 bytes; less the block's 2-byte length, 1,005 bytes. A block therefore always fits one DATA record.
- Reason: A block that fits one record is lost or received whole, which the live sound's rules rely on; and the receiver keeps a live block in a fixed slot of the ring.
- Source: `profile.rs` (`MAX_RECORD` = 1,024, `RECORD_HEADER` = 4, `RECORD_CRC` = 4); MIDI-42.
- Verification: A compile-time assertion in `codec.rs` that the constant equals the derivation; a server test that a block of 1,005 bytes is written in one record and a 1,006th byte is refused.

**MIDI-31. The most events in a block.** A block MUST hold at most 256 events. The receiver MUST act on the first 256 and pass over and count every later one; the server MUST refuse a block that would hold more, naming the block and the count. A family document MAY set a lower bound for its family (the synth6581 family's is 20 register data messages, S6581-42).
- Reason: A bound on the events is a bound on the receiver's work for one block. At the smallest event (3 bytes: a delta and a program change), 1,005 bytes hold 335 events; 256 is 12,800 events a second, far above any performance.
- Source: DEVELOPMENT.md section 6 ("Bound every allocation and every length"); `synth6581-synth8580.md`, S6581-42.
- Verification: A receiver test with 257 events; a server test refusing 257.

**MIDI-32. An empty block.** A block of zero bytes MUST be valid: it holds no event, and the synthesizer renders its 20 milliseconds from the state it holds.
- Reason: Most blocks of most music hold no event; they cost only their length's two bytes (MIDI-42).
- Source: As built, an all-zero slot was empty; the empty block replaces it.
- Verification: A test renders a sound whose blocks 1 to 99 are empty and checks a held note sounds through them.

### 6.5 Faults in a block

**MIDI-33. A framing error.** On a framing error (a data byte or one of `0xF4`, `0xF5`, `0xF9`, `0xFD` where a message's status is expected; a channel message cut by the block's end; a data byte with its top bit set in a channel message; a variable-length quantity not minimal or over two bytes; a length that runs past the block's end; an event whose time reaches 200), the receiver MUST keep the effect of every event already applied, pass over the rest of the block, count the block once as malformed, and render the block's remaining samples from the state the synthesizer holds.
- Reason: After a framing error the reader cannot know where the next event begins; going on would read data as messages. Keeping what was applied and rendering on keeps the sound going.
- Source: DEVELOPMENT.md section 6 (all input untrusted).
- Verification: A fuzz target (MIDI-124) and a test for each kind of framing error.

**MIDI-34. A content error.** On a content error (an event whose extent is known but which the synthesizer does not act on: a message its family document does not list, a system exclusive message longer than 256 bytes, without its final `0xF7`, with a byte of `0x80` or above before it, or whose bytes break its family document's rules; a skipped event), the receiver MUST pass over exactly that event, count it, and go on with the next event of the block. A system exclusive message that is passed over MUST change nothing in the synthesizer: none of its bytes may have been applied.
- Reason: The event's extent is known, so the rest of the block can still be read; and a message applied in part would leave a state no sender meant.
- Source: `synth6581-synth8580.md`, S6581-8 (the same rule for ASID messages).
- Verification: A test for each kind of content error, checking the counter and that the samples equal those of the block without the event.

### 6.6 Order and timing

**MIDI-35. The order of events at one tick.** Events with the same time MUST be applied in the order they stand in the block. The server MUST write events of one tick in this order: first the restatement events it adds (section 12), then the program's events in the order the program gave them; and for a Standard MIDI File, events of one tick in the order of their tracks (track 0 first) and, within a track, in the file's order.
- Reason: Order at one tick carries meaning: a bank select before its program change, a coarse controller before its fine one, an NRPN's number before its value, a note off before a note on of the same key. A restatement carries the state as it stood before the tick, so it goes first.
- Source: As built (`render_slots`: "in slot order where times are equal"); `synth6581-synth8580.md`, S6581-40.
- Verification: A test gives a note off and a note on of one key at one tick in both orders and checks the two outcomes differ as their order says; a server test checks the order of a merged file's events.

**MIDI-36. Timing accuracy.** Every event MUST take effect at the sample `floor(tick × 24 ÷ 5)` of its block (MIDI-5), within 0.8 of a sample (16.7 microseconds) of its tick, and every tick MUST be within 50 microseconds of the time the program stated (MIDI-17). The total error of any event against the program's time is therefore at most 66.7 microseconds, and it does not grow along a sound.
- Reason: Musical timing needs errors well under a millisecond and no drift; the figures follow from the tick and the rounding.
- Source: Decision A3; MIDI-5, MIDI-17.
- Verification: The tests of MIDI-5 and MIDI-17.

**MIDI-37. What the server never splits.** The server MUST write these groups of messages into one block, at one tick, in this order, and never across a block boundary: (a) a bank select (controller 0, then 32 where both are used) and the program change it applies to; (b) the coarse and the fine controller of a 14-bit pair; (c) an NRPN or RPN's parameter number (controllers 99 and 98, or 101 and 100) and the data entry, increment or decrement that follows it (controllers 6 and 38, or 96, or 97); (d) a restatement of one part (MIDI-98). Every data entry, increment or decrement the server writes MUST be preceded in the same block by the parameter number it applies to.
- Reason: If a group were split and the block holding its first half lost, the second half would change the wrong patch or the wrong parameter: a data entry whose number was lost goes to whatever number was selected before. Keeping each group in one block makes a group lost or received whole.
- Source: Prophet-5 MIDI, pages 6 and 7 (the NRPN sequence; "the synth will track the most recent NRPN number"); MIDI 1.0 4.2 for bank select ("The transmitter must transmit the MSB and LSB as a pair, and the Program Change must be sent immediately after the Bank Select pair", printed page 13, PDF 45) and for pairs (the most significant byte first, Table II, note 4, PDF 101).
- Verification: A server test that sends each group at a tick 0.05 milliseconds before a block's end and checks it is written whole in one block at one tick.

**MIDI-38. A sound's blocks are a Standard MIDI File track.** The events of a sound's blocks, taken in order, with the first event of block k given the delta time `200 × k + its time − (the absolute tick of the previous event)`, MUST, with a set tempo meta event of 1,000,000 microseconds a quarter note (`FF 51 03 0F 42 40`) at time 0 before the first of them and an end-of-track meta event (`FF 2F 00`) after the last, form a valid Standard MIDI File format 0 track whose division is 10,000 ticks a quarter note (so that a tick is 0.1 millisecond). The server MAY write a sound so, for an author to inspect it in any MIDI tool.
- Reason: It states exactly what decision A3 promises, and gives a test of the grammar with existing tools. The two meta events are added because a block holds none (MIDI-8), while a track must end with end of track and its tempo must be stated for its ticks to be 0.1 millisecond.
- Source: Decision A3; Standard MIDI Files 1.0: printed page 4 (PDF 133) for the division (bit 15 clear, ticks a quarter note in bits 14 to 0, so at most 32,767); printed page 9 (PDF 138) for the set tempo meta event (`FF 51 03 tttttt`, microseconds a quarter note) and end of track (`FF 2F 00`); printed page 8 (PDF 137): "An end-of-track event must occur as the last event in the track"; printed page 6 (PDF 135): "The first event in each MTrk chunk must specify status".
- Verification: A test writes a sound's blocks as such a file, reads it with the server's file reader (section 15), and checks the same blocks come back.

---

## 7. Carrying blocks in records

### 7.1 Why blocks become variable in length, and how

As built, a codec's block size is fixed for each sound by the OBJECT record's block bytes field, and the store keeps a stored sound as `blocks × block bytes` bytes, finds block k at `k × block bytes`, and keeps a live sound in a ring of 32 slots of that size (`store.rs`, `store/arena.rs`, `store/live.rs`). A block of slots held 4 to 64 bytes. An event list varies: most blocks of music are empty or hold a few events; a block that sets a whole panel or carries a patch holds hundreds of bytes. The options considered:

| Option | What it is | Cost |
|---|---|---|
| **A. Fixed blocks, padded.** | Every block of a sound is as long as its longest, the rest padded (for example with zero bytes, which the reader takes as the list's end). No record changes. | A sound pays for its densest block in every block. A two-minute sound with one 1,005-byte block costs 6,030,000 bytes, more than a desktop receiver's whole 4 MiB store (`profile.rs`, `LEVEL_B_MINIMUM`). Rejected. |
| **B. Variable blocks: each block with its length, each DATA record with the byte offset of its first block, the OBJECT with the sound's total bytes.** | The store keeps exactly the bytes sent, finds each block by an offset table, admits a stored sound by its total. | Two bytes a block on the wire (100 bytes a second); four bytes a DATA record; in the receiver, four bytes a block of a stored sound for its offset (24,000 bytes for 6,000 blocks) and a live ring of 32 slots of the largest block. A new DATA layout for the event codecs. **Chosen.** |
| **C. One block a DATA record.** | Each DATA record holds one block; the record's length gives the block's. | Twelve bytes of record header and CRC and five of DATA fields for every block, 850 bytes a second for a sound of empty blocks; 6,000 records for a two-minute sound; the store still needs an offset table. Rejected. |
| **D. Offsets in the OBJECT.** | The OBJECT lists every block's length. | 6,000 blocks need 12,000 bytes; an OBJECT is at most 1,016 bytes of body. Impossible. |

Option B is specified by MIDI-39 to MIDI-49.

**MIDI-39. Blocks of an event codec vary in length.** A block of an event codec MUST be 0 to 1,005 bytes (MIDI-30), each block of a sound its own length. The OBJECT and DATA records of an event codec MUST be as MIDI-40 to MIDI-43 say; the records of every other codec (PCM, IMA ADPCM, Opus, and the bank codec of MIDI-55) MUST stay as they are.
- Reason: Section 7.1, option B.
- Source: Decisions A2 and A3; section 7.1.
- Verification: The tests of MIDI-40 to MIDI-46.

**MIDI-40. The OBJECT of an event codec.** An OBJECT record of an event codec MUST have its 17 fixed bytes as today, with these meanings: the codec (MIDI-107); the rate code 7, 48,000 Hz; the block bytes field, the length in bytes of the sound's longest block, 0 to 1,005 (for a live sound, the longest any block will be, MIDI-103); the samples field, the number of blocks times 960 for a stored sound and 0 for a live sound; the blocks field, the number of blocks, 1 to 6,000 for a stored sound and 0 for a live sound. A receiver MUST refuse the record if the block bytes field is above 1,005, if the samples field of a stored sound is not exactly the blocks field times 960, or if a stored sound has more than 6,000 blocks.
- Reason: The fields keep their meaning wherever they can; block bytes, which can no longer be every block's size, becomes the largest, which bounds a DATA record's blocks and a live ring's slots.
- Source: `record.rs` (`OBJECT_FIXED`, `object`); MIDI-30.
- Verification: Record tests for each refusal and for a valid stored and live OBJECT.

**MIDI-41. The total bytes of a stored sound: extension tag 8.** An OBJECT record of a stored sound of an event codec MUST carry extension tag 8, of length 4: the sum of the lengths of all its blocks, a big-endian number from 0 to 960,000. A live sound's OBJECT MUST NOT carry it. A receiver MUST refuse a stored event sound's OBJECT without the tag, with a value over 960,000, or with a value over the blocks field times the block bytes field; and MUST skip the tag on any other codec, as an unknown tag.
- Reason: The store admits a sound only if it fits once complete, and must know how much to set aside before any block arrives (`store.rs`: "An object is admitted only if it fits once complete"). 960,000 is the largest stored sound the profile admits today: 6,000 Opus blocks of the largest packet, 160 bytes (`codec.rs`, `OPUS_MAX_PACKET`), so no instrument sound costs the store more than a sound it already holds.
- Source: `store.rs`; `codec.rs` (`OPUS_MAX_PACKET` = 160); `record.rs` (tags 1 to 7 are in use, so 8 is the next).
- Verification: Record tests for each refusal; a store test admits a sound of 960,000 bytes in a store of exactly that much plus its tables, and refuses one byte more.

**MIDI-42. The DATA record of an event codec.** The body of a DATA record of an event codec MUST be: the handle (1 byte); the generation (2 bytes); the number of its first block (2 bytes); the byte offset of its first block within the sound (4 bytes, big-endian; 0 for a live sound); then one or more blocks, each a length of 2 bytes, big-endian, 0 to 1,005, and that many bytes of event list. A block MUST NOT be split across two DATA records.
- Reason: Section 7.1, option B. The offset lets a record be stored wherever it arrives, in any order and after any loss; the length tells the store where each block ends. A fixed two-byte length is read with the record reader's existing field reader, where a variable-length quantity would add a second number coding to the record layer.
- Source: Section 7.1; `record.rs` (`DATA_FIXED`, today 5 bytes).
- Verification: Record tests that write and read a DATA record of one empty block, of one 1,005-byte block, and of 503 empty blocks, the most that fit.

**MIDI-43. What makes a DATA record of an event codec faulty.** The receiver's store MUST discard a DATA record of an event codec whole, storing none of it, when: a block's length is over the OBJECT's block bytes field or runs past the record's end; the record holds no block; for a stored sound, a block's number is at or past the blocks field, or its offset plus its length passes the total of tag 8, or the offset stated for the first block, or computed for a later one by adding the lengths before it, disagrees with an offset the store already holds for that block number, or the first block is block 0 and its offset is not 0, or a block's end would overlap the start the store holds for the next block; for a live sound, the offset field is not 0.
- Reason: The record is judged whole before any of it is written, as the store does today (`store.rs`, `put`), so that a faulty record cannot leave the store's tables disagreeing with its bytes.
- Source: `store.rs` (`put`, `record_blocks`); DEVELOPMENT.md section 6.
- Verification: A store test for each fault, checking nothing is stored and the record is counted.

**MIDI-44. A block sent twice.** When a block arrives that the store already holds, the store MUST compare the two byte for byte, length included; if they differ, the sound MUST be put in conflict and not played until a newer generation replaces it, as today. Two encodings of the same events are different blocks: the server MUST write any block it sends more than once with identical bytes.
- Reason: The store's existing rule for a stored or live block that differs (`store.rs`, `put`; `store/live.rs`, `put_live`), which detects a sender that changed a sound without a new generation. MIDI-24's minimal coding makes one encoding of a list the only one.
- Source: `store.rs`; `store/live.rs`.
- Verification: The existing conflict tests, run on event blocks of different lengths.

### 7.2 What the receiver keeps

**MIDI-45. A stored event sound in the store.** For a stored sound of an event codec, the store MUST set aside exactly: the total bytes of tag 8 for the blocks' bytes; 4 bytes for each block, its offset; and one bit for each block, whether it has arrived (rounded up to whole bytes); and MUST admit the sound only if all of that fits once evicting what may be evicted, as today. A block's bytes MUST be found from its offset and the next block's offset (or the total, for the last block).
- Reason: It is option B's store: what was sent, plus the tables to find it.
- Source: Section 7.1; `store.rs` (`Entry::size`, the admission rule); DEC-2113 (nothing leaves for a sound refused).
- Verification: A store test checks the space a sound takes equals `total + 4 × blocks + ceil(blocks ÷ 8)`; the existing admission and eviction tests run on event sounds.

**MIDI-46. A live event sound in the store.** For a live sound of an event codec, the store MUST keep a ring of 32 slots, each of the OBJECT's block bytes plus 2 bytes for the block's length and 2 for its block number, filled by block number modulo 32, as today; the lookahead (3 blocks) and the stall (2,000 milliseconds, then a 100-millisecond fade) MUST be as today (MIDI-101).
- Reason: The live ring as built, with a slot that holds the largest block and a length to say how much of it is used.
- Source: `store/live.rs`; `profile.rs` (`LIVE_RING_BLOCKS` = 32, `LIVE_LOOKAHEAD_BLOCKS` = 3, `LIVE_STALL_MS` = 2,000, `LIVE_STALL_FADE_MS` = 100); DEC-611.
- Verification: The existing live-sound tests, run on event blocks of lengths 0, 1 and 1,005.

**MIDI-47. How the server packs DATA records.** The server MUST put into each DATA record of an event codec as many whole blocks, in order, as fit its body (at most 1,016 bytes), and MUST start a new record when the next block would not fit.
- Reason: Fewest records for the bytes; and MIDI-42 forbids splitting a block.
- Source: `encode.rs` (`data_records`: "as many whole blocks in each as fit a record").
- Verification: A server test checks no record could have held the next block.

**MIDI-48. The OBJECT extensions of the event codecs.** The extension tags of an OBJECT record of an event codec MUST be exactly these; every other tag MUST be skipped as unknown:

| Tag | Length | On codecs | Value |
|---|---|---|---|
| 1 | 0 to 64 | every codec | The sound's label, UTF-8, as today |
| 2 | 0 to 16 | every codec | A language tag, as today |
| 3 | 1 | 12 (the synth6581 family) | Bit 0: 0 synth6581, 1 synth8580; bit 1: 0 the PAL clock, 1 the NTSC clock; bits 2 to 7: 0. Without it: synth6581 on the PAL clock. As today, and as `synth6581-synth8580.md`, S6581-39, requires. |
| 4 | 1 to 10 | 13 to 18 (every family with banks) | The handles of the sound's banks, in order: bank index 0 first (MIDI-57). Required on those codecs. |
| 5 | 1 | 14 (the synth106 family) and 16 (the synth53 family) | The variant: for codec 14, 0 synth106 and 1 synth60; for codec 16, 0 synth53, 1 synth52, 2 synth51. Without it: 0. |
| 6 | 1 | 19 (the bank codec) | The family the bank is for: the code of that family's codec, 13 to 18. Required on that codec. |
| 7 | 2 | 17 (synth8) | synth8's key mode (one byte: 0 whole, 1 dual, 2 split) and split key (one byte), as today; the adopted interface has no message for either (`synth8.md`, S8-18). |
| 8 | 4 | 12 to 18, stored sounds | The total bytes of the blocks (MIDI-41). |

The server MUST write tags 3 and 5 from the sound's kind, never from a field a program sets for the chip or the variant.
- Reason: Each synthesizer's setting that never changes while it plays travels in the OBJECT, which a receiver that joins late already has; the kind sets the variant (DEC-6461 item 3). synth52 and synth51 are one model today but keep distinct values so that a later model can tell them apart without a new tag.
- Source: `record.rs` (tags 1 to 7); DEC-6461 item 3; `synth6581-synth8580.md`, S6581-1 and S6581-39.
- Verification: Record tests for each tag on each codec, on a codec it does not belong to, and with a wrong length.

**MIDI-49. What option B costs, measured.** The implementation MUST measure and record, for the audio demo's tunes of every family and for a two-minute sound of the densest blocks the server allows: the bytes on the wire against the bytes as built, the store's bytes, and the time the receiver spends finding and reading a block; and the figures MUST be in the commit that builds option B.
- Reason: Section 7.1 states the cost by reasoning; DEVELOPMENT.md section 2.1 requires measurement.
- Source: DEVELOPMENT.md section 2.1 ("Measure, don't reason").
- Verification: Review of the commit's figures.

---

## 8. System exclusive longer than an event

The adopted interfaces' timed messages are all short (MIDI-28). What is long is the whole-bank dump: the DX7's 32-voice dump of 4,104 bytes; a Juno-106 bank sent as 128 patch messages of 24 bytes, 3,072 bytes; a Prophet-5 group of 40 programs of 159 bytes, 6,360 bytes. A message of 4,104 bytes cannot be one event of a block (MIDI-30) nor one record. Two ways could carry it: Standard MIDI Files' continuation form, `F0 <length> <first part>` then `F7 <length> <next part>` … across events and so across blocks; or a stored object of its own.

**MIDI-50. A timed system exclusive message is whole in one event.** Every system exclusive message in a block MUST be whole in one event of one block (MIDI-27, MIDI-28). Standard MIDI Files' continuation form MUST NOT be used: the server MUST never write an `0xF7` event, and the receiver MUST pass one over as a skipped event (MIDI-29), so that no part of a message is ever applied.
- Reason: With continuation, a lost live block would leave a synthesizer holding the start of a message whose end never comes, or the end of one whose start it never saw; a receiver would need a buffer as large as the longest message for each part and rules for when a partial message is abandoned. No timed message of any adopted interface needs it (MIDI-28).
- Source: Section 8; decision A3; `synth6581-synth8580.md`, S6581-6 (which forbids it for ASID).
- Verification: A receiver test gives `F0` with a part of a message and then `F7` with the rest, in one block and across two, and checks that nothing reaches the synthesizer and both are counted.

**MIDI-51. A message longer than an event travels as a bank.** A system exclusive message longer than 256 bytes MUST travel only inside a bank image (MIDI-56), a stored object carried in DATA records of 1,011 bytes and kept whole by the store. The server MUST refuse one in a program's timed events, unless MIDI-58 lifts it into a bank.
- Reason: The stored object is the audio profile's existing way to carry bytes of any length, with loss recovery (a stored object's records are repeated until every one has arrived) and conflict detection; nothing new is needed.
- Source: Decision A4 (this document is to specify how such a message travels); `store.rs`.
- Verification: A server test sends a 4,104-byte DX7 dump as a bank and checks its records; a server test refuses the same bytes as a timed event after the first note.

**MIDI-52. A bank that has not wholly arrived.** The receiver MUST NOT read any patch from a bank image until every one of its DATA records has arrived and the store holds it complete. A sound that names a bank not complete MUST wait (MIDI-62).
- Reason: A bank image is parsed as a whole sequence of messages; a part of it holds parts of messages.
- Source: As built (`a_stored_sound_of_each_synthesizer_waits_for_its_bank_and_then_plays`).
- Verification: A test sends a bank's records with one held back, starts a sound, and checks it waits until the last arrives.

**MIDI-53. Reading a bank image is bounded.** The receiver MUST read a bank image in one pass, with work proportional to its bytes (at most 16,384, MIDI-55), and MUST take from it only whole messages (or whole fixed-size patches) that its family document's rules accept; any other message in it MUST be passed over and counted, and any patch it fails to set MUST be the default (MIDI-63).
- Reason: All input is untrusted; a bank is read when a sound starts, and its cost must not depend on anything but its length.
- Source: DEVELOPMENT.md sections 6 and 14.
- Verification: A fuzz target of the bank reader for each family (MIDI-124); a timed test of a 16,384-byte bank image.

---

## 9. Patches and banks

### 9.1 What a patch is, family by family

**MIDI-54. The patch form of each family.** Each family's patch MUST be in the form this table gives, and its family document MUST specify it byte for byte. A cell marked "family document" is that document's to settle within the rule of its row; the figures given are what the filed sources show.

| Family | Patch form | Size | Source |
|---|---|---|---|
| synth6581 | A full register update: one ASID register data message carrying ASID register IDs 0 to 24 | 37 bytes in MIDI form | `synth6581-synth8580.md`, S6581-50 |
| synth7 | The DX7's single-voice bulk dump: `F0 43 0n 00 01 1B`, 155 bytes of voice data, a checksum, `F7` | 163 bytes | DX7 manual, page 30 ("Bulk data of 1 voice", byte count 155); TX7 manual, printed pages 35, 36 and 44 |
| synth106 | The Juno-106's patch message: `F0 41 30 0n`, the program number, 18 values (16 sliders and 2 bytes of switches), `F7`; or its manual message, `F0 41 31 0n 00`, 18 values, `F7`; for synth60 the same patch message followed by the JU-06A's control changes of controllers 15, 28 and 93 at canonical values, 21 values (`synth106-synth60.md`, S106-31) | 24 bytes; 33 for synth60 | Juno-106 manual, PDF 35, sections 3.1, 3.2 and 3.4; `synth106-synth60.md`, S106-31 |
| synthD | The values of synthD's 60 panel controllers in `synthd.md`'s fixed order, the Voyager's 46 in ascending order of controller number and then NeoTeletext's own 14, without status bytes or controller numbers (the order is NeoTeletext's own: the Voyager's preset dump is undocumented) | 60 bytes | `synthd.md`, SD-22 |
| synth53 | The Prophet-5's program edit buffer data dump: `F0 01 31 03`, 152 bytes ("128 bytes expanded to 152 MIDI bytes in packed MS bit format"), `F7`; in a bank, its program data dump: `F0 01 31 02`, group, program, 152 bytes, `F7` | 157 bytes; 159 in a bank | Prophet-5 MIDI, pages 12 and 13 |
| synth8 | The values of synth8's 42 panel controllers in `synth8.md`'s fixed order, the order of the JUPITER-8/SYSTEM-8 correspondence table's parameter numbers: 40 of the chart's controllers and NeoTeletext's own 107 and 108 for the two bend switches (NeoTeletext's own: the chart lists no patch format and no system exclusive) | 42 bytes (`synth8.md`, S8-23) | JUPITER-08 chart; DEC-6457; `synth8.md`, S8-16 and S8-23 |
| synth80 | The values of synth80's 85 controllers in `synth80.md`'s fixed order (NeoTeletext's own: Deckard's Dream's manual gives control changes and no patch format) | 85 bytes: 73 values of the adopted table's controllers (its 75 panel controllers less coarse and fine pitch, 93 and 94, which synth80 lacks) and 12 of NeoTeletext's own for the CS-80 controls Deckard's Dream lacks (`synth80.md`, S80-33) | Deckard's Dream manual, PDF 71 to 74; DEC-6458; `synth80.md`, S80-33 |

- Reason: Decision A4: patches travel in the adopted interface's own form; where an interface has none, a patch is the list of that interface's control values.
- Source: The documents in the table; decision A4.
- Verification: Each family document's tests of its patch; a test in this document's suite checks each family's default patch has the size the family document states.

**MIDI-55. The bank codec.** A bank MUST be a stored object of the bank codec (code 19, MIDI-107), never played: rate code 7; its samples field the bank image's length in bytes, 1 to 16,384; its block bytes field 1,011 (the most a DATA record of the existing layout carries) or, for a bank image shorter than that, its length; its blocks field `ceil(samples ÷ block bytes)`; its blocks the bank image cut into pieces of the block bytes, the last piece shorter where the length is not a multiple, in DATA records of the existing layout (5 bytes of fields, then the bytes). It MUST carry extension tag 6, the family's codec (MIDI-48). A CONTROL record that plays a bank MUST be ignored and counted.
- Reason: A bank is bytes of a known length that must arrive whole; the audio profile's existing stored-object layout, with a shorter final block as PCM's has (`codec.rs`, `block_bytes_for`), carries exactly that.
- Source: `codec.rs` (`samples_per_block`, `block_bytes_for`); `record.rs` (`TAG_BANK_FAMILY`); DEC-6410 item 11 (a bank is stored as a sound and never played).
- Verification: Record and store tests for a bank of 1 byte, 1,011 bytes, 1,012 bytes and 16,384 bytes; a test plays a bank and checks it is ignored.

**MIDI-56. The bank image.** A bank image MUST be, for the family it is for, one of these two forms, as its family document specifies:
1. **messages:** a sequence of complete messages of the adopted interface, `F0 … F7` back to back, each byte for byte as the interface defines it, being what a librarian would send the instrument to fill its memory: for synth7, one 32-voice bulk dump (`F0 43 0n 09 20 00`, 4,096 bytes of 32 packed voices, a checksum, `F7`: 4,104 bytes; DX7 manual, page 30; TX7 manual, printed pages 35, 36 and 44); for synth106, 1 to 128 patch messages (function type 0x30), each carrying its own program number, 24 bytes each; for synth60, 1 to 128 patches of 33 bytes, each a function type 0x30 message followed by the three control changes `Bn 0F v`, `Bn 1C v`, `Bn 5D v` (`synth106-synth60.md`, S106-31 and S106-38; that document's open question 1), the only bank image that holds channel messages, because no interface defines a Juno-60 patch; for the synth53 family, 1 to 40 program data dumps of one group, each carrying its group and program number;
2. **fixed patches:** for a family whose patch form is a list of control values (synthD, synth8, synth80), 1 to 128 patches back to back, each of the family's patch size, patch k at byte `k × size` (synth8: 1 to 64 patches of 42 bytes, at most 2,688; `synth8.md`, S8-29).

Which patch of the image is which program MUST be as the messages say (a message that carries a program number sets that program) or, where they carry none, by position (the DX7's 32-voice dump holds programs 0 to 31 in order; a fixed patch is its position). A bank image MUST NOT carry a message that the adopted interface does not use to fill its memory (for example a device inquiry, a request, or a global parameter dump).
- Reason: Decision A4 asks for the interface's own form, byte for byte: a bank image of messages is exactly what the interface sends, so every existing bank file is a bank image as it stands. Where the interface has no dump, the patches are the family's lists of values, which decision A4 makes the patch.
- Source: Decision A4; DX7 manual, page 30; Juno-106 manual, PDF 35 (section 3.1, "When Group, Bank or Patch number is changed", carries the program number 0 to 127); Prophet-5 MIDI, page 12 (group 0 to 9, program 0 to 39); `synthd.md`, SD-27.
- Verification: For each family, a test builds a bank image from the family's filed example where one exists (the Juno-106 manual's example message, PDF 35) and checks each program's patch.

**MIDI-57. A sound names its banks.** A sound of a family with banks MUST name 1 to 10 banks, by their handles, in extension tag 4 of its OBJECT record (MIDI-48); the first is bank index 0, the next bank index 1, and so on. Every bank named MUST be for the sound's family (its tag 6). The server MUST send every bank a sound names before the sound's OBJECT record, and MUST refuse a sound naming a bank it does not hold for that program, for another family, or more than 10.
- Reason: The adopted interfaces reach more patches than one bank holds: the DX7's programs 32 to 63 are its cartridge's 32 voices (DX7 manual, page 32), the Prophet-5 selects groups by bank select (Prophet-5 MIDI, page 2: values 1 to 5 the user banks, 6 to 9 the factory banks; the program dump numbers groups 0 to 9, page 12), and Deckard's Dream has three banks chosen by controller 0 (manual, PDF 18). Ten covers the Prophet-5's ten groups, the most of any. The OBJECT reaches a receiver before any block, including one that joins late.
- Source: The documents in the reason; `record.rs` (`TAG_SYNTH7_BANK`, one handle today).
- Verification: A record test with 0, 1, 10 and 11 handles; a server test refusing a bank of another family.

**MIDI-58. Bank dumps in a program's music are lifted into banks.** When a program's timed events or Standard MIDI File hold a system exclusive message that the family document identifies as a bank dump (a message of the bank image's form, MIDI-56), and it stands before the sound's first note on, the server MUST take it out of the music, make a bank of it (as if the program had sent it as a bank, MIDI-15), give that bank a handle and generation of the program's choosing or, where the program gave none, refuse; and name it as the sound's next bank index. A bank dump after the first note on MUST be refused, naming its time.
- Reason: Many files of music for these instruments begin with the bank they play (a DX7 file commonly opens with a 32-voice dump); taking it into a bank keeps such a file playable with no change by its author, and the music then uses the bank as the instrument would. After the first note the dump would change patches mid-performance, which the architecture cannot carry in a block (MIDI-50); the author must split the sound.
- Source: DEC-6462 item 1 ("splits what is too long"); MIDI-50 and MIDI-51.
- Verification: A server test with a file that begins with a DX7 32-voice dump and plays program 5; and one with a dump after a note, refused.

### 9.2 Choosing a patch

**MIDI-59. A program change chooses a patch.** A program change MUST choose, for the part its channel addresses (section 10), the patch the family document's mapping gives from the program number (0 to 127) and the channel's bank select state (MIDI-64): a bank index of the sound's banks and a program within that bank's image. Where the adopted interface has no bank select and its program numbers fit one bank, the mapping MUST be bank index 0, program equal to the program number. The family document MUST give the mapping as a complete table or formula. A program number the mapping does not reach, a bank index past the sound's banks, or a program the bank image does not hold MUST set the family's default patch (MIDI-63) and count the program change as passed over.
- Reason: Each interface numbers its programs in its own way: the DX7 0 to 31 internal and 32 to 63 cartridge (DX7 manual, page 32); the Juno-106 0 to 63 group A and 64 to 127 group B (Juno-106 manual, PDF 35, section 2.2); the Prophet-5 0 to 39 within the group bank select chose (Prophet-5 MIDI, page 2); Deckard's Dream 128 within the bank controller 0 chose (manual, PDF 17 and 18); the Voyager 0 to 127 (`synthd.md`, SD-12).
- Source: The documents in the reason.
- Verification: For each family, a test sends every program number with every bank select state the mapping names and checks the patch.

**MIDI-60. A patch sent inline.** A patch MAY be sent inline, in a block, as the adopted interface's own message: for a family whose patch form is a system exclusive message (synth7, synth106, synth53, synth6581), that message as one event (MIDI-27), at most 256 bytes; for a family whose patch form is a list of control values (synthD, synth8, synth80), the sequence of control changes the family document says the patch stands for, in its order, at one tick. Its effect MUST be what the adopted interface says receiving that message does (for example the DX7's single-voice dump replaces the voice the part is playing, its edit buffer; the Prophet-5's edit buffer dump replaces the program being played), as the family document states, and it MUST NOT change any bank.
- Reason: It is how each interface sends a sound without storing it, and lets a program change a sound mid-performance with no bank.
- Source: Decision A4; DX7 manual, page 32 ("Bulk data of 1 voice"); Prophet-5 MIDI, page 12 ("Program Edit Buffer Data Dump"); `synthd.md`, SD-26.
- Verification: For each family, a test sends a patch inline and checks the part plays it and every bank is unchanged.

**MIDI-61. Before any patch arrives.** Until a part of a family with banks receives a program change or an inline patch, it MUST play program 0 of bank index 0 of its sound; and where that program is missing from the bank or refused, the family's default patch, which its family document MUST state value by value.
- Reason: A part must sound something definite from the first note; patch 0 is what is built and what a program that never sends a program change expects.
- Source: As built (`a_program_change_chooses_the_patch_and_patch_0_plays_until_one_comes`); `synthd.md`, SD-12 and SD-21.
- Verification: A test plays a note with no program change, with a bank, with a bank that lacks program 0, and with a bank whose program 0 is faulty.

**MIDI-62. A sound waits for its banks.** A sound that names banks MUST NOT start until the store holds every bank it names complete. A stored sound waits as today; a live sound's blocks are kept in its ring, and if no bank completes before the live sound stalls (MIDI-101), it stalls.
- Reason: A sound that started before its banks would play its first notes on default patches and then change timbre; as built a stored sound waits.
- Source: As built (`a_stored_sound_of_each_synthesizer_waits_for_its_bank_and_then_plays`).
- Verification: The existing test, extended to a sound naming three banks, the third held back.

**MIDI-63. A faulty patch.** When a patch in a bank image or sent inline breaks its family document's rules (a wrong length, a byte out of its range, a wrong header, a wrong checksum where the interface has one), the receiver MUST set the family's default patch in its place, MUST count it in a counter of refused patches the port can read, and MUST NOT stop the sound. The server MUST check every patch with the receiver's own check (MIDI-21) and MUST refuse any bank or inline patch that would fail it, naming the bank, the program, the byte and the rule, so that a sound the server sends never reaches this rule.
- Reason: As built, a faulty patch became the default "silently", which hid real faults (the server checked DX7 banks less than the receiver: `synthesizer-wire-format.html`, section 12). Keeping the default keeps the sound going, so one bad patch costs a timbre and nothing more; counting it lets the fault be seen; the server's refusal, with one check shared, means a program learns of the fault before anyone hears it.
- Source: `receiver/instruments.rs` (`bank`: "a faulty bank costs a sound its timbre and nothing else"); `synthesizer-wire-format.html`, section 12 ("DX7 bank checks"); DEC-6462 item 2.
- Verification: A receiver test with one faulty patch of each kind in a bank and inline, checking the default plays and the counter; a server test for each refusal.

**MIDI-64. Bank select.** Where an adopted interface selects banks with controller 0, controller 32, or both, the receiver MUST keep, for each channel, the values last received, and MUST apply them at the channel's next program change, through MIDI-59's mapping; a bank select alone MUST NOT change the patch. A family whose interface has no bank select MUST treat controllers 0 and 32 as content errors (MIDI-34), unless its family document assigns them otherwise. Bank select values MUST be 0 at the start of a sound.
- Reason: It is MIDI 1.0's rule for bank select ("When the Bank Select message is received, the receiving device must remember that bank number in readiness for the following Program Change. Bank Select alone must not change the program", printed page 13, PDF 45), and the Prophet-5 (controller 32, values 1 to 9) and Deckard's Dream (controller 0, values 0 to 2) use it so.
- Source: MIDI 1.0 4.2, printed page 13 (PDF 45); Prophet-5 MIDI, page 2; Deckard's Dream manual, PDF 18.
- Verification: A test sends a bank select alone and checks no change, then a program change and checks the bank's patch.

**MIDI-65. Banks are fixed for the life of a sound.** The banks a sound plays from MUST be as they stood when the sound started, until it ends: a bank a playing sound names MUST NOT be evicted from the store, and a newer generation of the bank's handle MUST take effect only for sounds started after it arrives.
- Reason: A sound's patches must not change under it because the store needed room or a program sent a new bank; as built a lane reads its bank once, when it is prepared.
- Source: `receiver/instruments.rs` (`Lane::prepare` reads the bank once); `store/arena.rs` (`busy` protects what the receiver needs).
- Verification: A test replaces a bank while a sound plays and checks the sound's patches are unchanged and a sound started afterwards has the new ones; a test fills the store while a sound plays and checks its banks stay.

**MIDI-66. Finding a patch is bounded.** The receiver's work to apply a program change MUST be bounded by the bytes of the bank image it reads (at most 16,384) and MUST NOT depend on anything else a sender controls; a receiver SHOULD index each bank once when its sound starts so that a program change costs only the patch's own check and application.
- Reason: Program changes can arrive as often as events (256 a block), so their cost must be small and bounded.
- Source: DEVELOPMENT.md sections 6 and 14.
- Verification: A timed test sends 256 program changes in one block against a 16,384-byte bank and holds the block's time to the render budget (MIDI-106), printing it.

---

## 10. Channels and parts

**MIDI-67. Channels and the family's channel map.** The channel of a channel message MUST be the low four bits of its status byte, 0 to 15 (channels 1 to 16). Each family document MUST give a channel map: for each of the 16 channels, which part it addresses or that it addresses none. A message on a channel that addresses no part MUST be passed over and counted. The synth6581 family has no channels: ASID messages carry none (`synth6581-synth8580.md`, S6581-4), and its channel messages are content errors.
- Reason: The adopted interfaces differ: one keyboard on one channel, sixteen parts, two parts. A map stated per family leaves nothing to guess.
- Source: MIDI 1.0 4.2, Table I and its note on `nnnn`, "N-1, where N = Channel #" (PDF 100); the family documents.
- Verification: For each family, a test sends a note on each of the 16 channels and checks which part sounds.

**MIDI-68. One-part families hear every channel.** synthD, the synth106 family, the synth53 family and synth80 each have one part, and their channel maps MUST map all 16 channels to it, unless their family document states otherwise with its reason. That the adopted interfaces each receive on one channel, chosen by a setting of the instrument (Juno-106 and JU-06A charts: basic channel 1 to 16; Prophet-5 MIDI, page 1: 1 to 16 or All; Deckard's Dream manual, PDF 45 and 46; the Voyager, `synthd.md`, SD-2), MUST be listed by each family document as a departure.
- Reason: A sound holds one instrument; a basic-channel setting serves an instrument on a shared cable, and no message sets it. Hearing every channel is what is built.
- Source: The documents in the statement; `synthesizer-wire-format.html`, section 08 ("The analogue instruments hear all channels as one keyboard").
- Verification: The test of MIDI-67 for each of these families.

**MIDI-69. synth7 has sixteen parts.** synth7's channel map MUST map channel n to part n, sixteen parts each with its own patch and controllers, sharing its 16 notes of polyphony as built (DEC-6410 item 10). `synth7.md` MUST list as a departure that the DX7 receives on one channel ("when the channel number of reception data accords with the channel number of the DX7", DX7 manual, page 32) and has 16 notes in poly mode (page 27).
- Reason: It is what is built and what lets one synth7 sound play a multi-part arrangement; the DX7 itself is one part.
- Source: DEC-6410 item 10; DX7 manual, pages 27 and 32.
- Verification: The existing rack tests (`tests/synth7_rack.rs`).

**MIDI-70. synth8 has two parts.** synth8's channel map MUST be as `synth8.md`, S8-2, states. Notes, pitch bend and the performance controllers (1, 5, 7, 8, 11, 41, 64, 118, the RPN controllers and the common layer) on every channel act on the whole instrument. Panel controllers and program changes on channel 1 address the upper half and on channel 2 the lower half; on channels 3 to 16 they are passed over and counted. The key mode and split key travel in the OBJECT (tag 7). The JUPITER-08 chart states no program change, no system exclusive and nothing of upper and lower parts; `synth8.md` section 13 lists what it defines itself.
- Reason: The instrument modelled has two patches at once; the filed interface does not say how they are addressed.
- Source: JUPITER-08 chart; `synthesizer-wire-format.html`, section 08 ("program change only on channel 0 (upper patch) or 1 (lower)").
- Verification: The existing test `a_synth8_has_two_patches_a_key_mode_and_a_split_point`.

**MIDI-71. Mode messages never change the channel map.** Omni off (124), omni on (125), mono on (126) and poly on (127) MUST NOT change which channels a synthesizer hears; each MUST act as all notes off (MIDI-9) and nothing more: none MUST switch a part between mono and poly assignment, in any family (MIDI-89). No message MUST set a basic channel.
- Reason: The channel map is fixed by the family (MIDI-67); a basic channel and omni are settings of hardware on a cable. The Juno-106 and the JU-06A treat all four as all notes off.
- Source: Juno-106 manual, PDF 35; JU-06A chart (notes "*2 Same process as All Notes Off"); DX7 manual, page 32 (125 "OMNI all key off", 126 "MONO all key off", 127 "POLY all key off", the values of 125 and 127 marked "ignored"; 124 not listed), whose difference MIDI-89 settles.
- Verification: A test sends each of 124 to 127 with notes held and checks notes released and the channel map unchanged.

---

## 11. Real-time parameter control

**MIDI-72. The three ways a parameter is changed.** A parameter of a patch MUST be changed while a sound plays only by the message its adopted interface defines for it, which is one of: a control change, or a coarse and fine pair of them; an NRPN or RPN sequence; a system exclusive parameter change (the DX7's `F0 43 1n` group and parameter, data, `F7`, 7 bytes, DX7 manual page 30; the Juno-106's `F0 41 32 0n` parameter, value, `F7`, 7 bytes, Juno-106 manual PDF 35). Each family document MUST give, for every parameter, its message, its range and how a value becomes the parameter's setting.

| Family | Ways the adopted interface defines | Source |
|---|---|---|
| synth6581 | ASID register data, a system exclusive message | `synth6581-synth8580.md` |
| synth7 | System exclusive parameter change; controllers 1, 2, 4, 5, 6, 7, 64, 65, 96, 97 for the performance controls | DX7 manual, pages 30 to 32 |
| synth106 | System exclusive parameter change (parameters 0 to 17); the JU-06A's control changes | Juno-106 manual, PDF 35; JU-06A chart |
| synthD | Control changes: the Voyager's map for the controls the two panels share, NeoTeletext's own for the rest | `synthd.md`, SD-9, SD-10, SD-17 |
| synth53 | Control changes and NRPN, both for every panel parameter ("NRPNs are the preferred method … since they cover the complete range of all parameters, while CCs are limited to a range of 128") | Prophet-5 MIDI, pages 1, 4 to 9 |
| synth8 | Control changes | JUPITER-08 chart |
| synth80 | Control changes | Deckard's Dream manual, PDF 71 to 74 |

- Reason: Decision A1; nothing invented where the interface defines it.
- Source: The documents in the table.
- Verification: Each family document's tests.

**MIDI-73. When a control takes effect.** A parameter change MUST take effect at its event's sample (MIDI-5), on notes that are sounding as well as on notes that start later, as moving the control does on the instrument modelled, smoothed as MIDI-83 requires.
- Reason: A performance moves controls under held notes.
- Source: Decision A1; `synthd.md`, SD-23.
- Verification: Each family's control-sweep test (MIDI-83).

**MIDI-74. Controller conventions are the interface's.** A family MUST treat controllers 32 to 63 as the fine part of controllers 0 to 31 only where its adopted interface (or, for a map NeoTeletext defines, its family document) pairs them; otherwise each is an ordinary controller of its own. The same holds for controllers 6, 38, 96 to 101 (data entry and parameter numbers): they mean NRPN and RPN only where the interface uses NRPN or RPN.
- Reason: The interfaces do not keep MIDI 1.0's conventions: the Prophet-5 uses controller 3 for oscillator A's frequency and controller 35 for the filter's keyboard tracking (Prophet-5 MIDI, page 4); the JUPITER-08 uses 3 for the cutoff and 35 for the LFO waveform; Deckard's Dream uses 40 to 63 each for a slider. Imposing the pairing would break each.
- Source: Prophet-5 MIDI, page 4; JUPITER-08 chart; Deckard's Dream manual, PDF 71 and 72.
- Verification: A test for synth53 sends controller 3 then 35 and checks two parameters change, not one.

**MIDI-75. A 14-bit pair.** Where a family pairs a coarse and a fine controller, a coarse value MUST set the parameter's seven high bits and clear its seven low bits, and a fine value MUST set the seven low bits and leave the high; the parameter MUST be set anew after either. The server MUST write a pair coarse first (MIDI-37).
- Reason: MIDI 1.0's rule: "When an MSB is received, the receiver should set its concept of the LSB to zero", and a later fine adjustment "only requires the sending of the LSB" (printed page 12, PDF 44; Table II, note 4, PDF 101); `synthd.md` relies on it.
- Source: MIDI 1.0 4.2, printed page 12 (PDF 44) and Table II, note 4 (PDF 101); `synthd.md`, SD-18.
- Verification: `synthd.md`'s tests of SD-18.

**MIDI-76. NRPN and RPN.** Where a family uses NRPN or RPN, the receiver MUST keep for each channel the parameter number last selected (by controllers 99 and 98, or 101 and 100; a parameter number is `MSB × 128 + LSB`), and MUST apply data entry (6, the value's high bits, and 38, its low bits), increment (96) and decrement (97) to it, as the adopted interface says. A selection of RPN 127, 127 or NRPN 127, 127, the null parameter number, MUST select no parameter, after which data entry, increment and decrement change nothing. After a lost block (MIDI-102), every channel's selection MUST become none.
- Reason: The Prophet-5's own rules (Prophet-5 MIDI, pages 6 and 7: "the synth will track the most recent NRPN number"; increment and decrement; "RPN/NRPN Reset … resetting the currently selected parameter"). After a loss the selection is unknown, and a data entry to the wrong parameter is worse than none; MIDI-37 makes the server re-select before every data entry, so nothing is lost by clearing it.
- Source: Prophet-5 MIDI, pages 6 and 7; MIDI 1.0 4.2, printed page 17 (PDF 49), the rules for parameter numbers, and Table III (PDF 102): controllers 98 and 99 the non-registered parameter number's least and most significant bytes, 100 and 101 the registered parameter number's, 6 and 38 data entry, 96 data increment and 97 data decrement; the GM Developer Guidelines, page 6 (PDF 315), for the null parameter number: "The 'Null function' value (7F for both the MSB and LSB) is used to lock in the value of the RPN or NRPN so that subsequent Data Entry and Data Increment/Decrement commands are ignored", MIDI 1.0 Approved Protocol JMSC-0011, which MIDI 1.0 4.2's text does not state.
- Verification: A test selects NRPN 18, sends data entry, checks resonance changes; sends RPN 127, 127 and a data entry and checks nothing changes; loses a block and checks a data entry alone changes nothing.

**MIDI-77. A system exclusive parameter change.** Where an interface defines a system exclusive parameter change, the receiver MUST apply it to the part the message's channel field addresses (the DX7's and the Juno-106's carry the channel in their third byte), as the interface defines, and MUST pass over and count one whose channel field addresses no part.
- Reason: The interface's own message, byte for byte.
- Source: DX7 manual, page 30 ("Sub status (s=1) & Channel number"); Juno-106 manual, PDF 35, section 3.3.
- Verification: The family documents' tests.

**MIDI-78. Control maps NeoTeletext defines.** Where an adopted interface gives no controller for a parameter the synthesizer has (as for synthD's panel, `synthd.md` section 6), the family document MUST define one, by these rules, in order, and MUST list each such number as NeoTeletext's own:
1. a number the adopted interface uses is never reused;
2. controllers 120 to 127 are never used (MIDI-9);
3. a parameter whose meaning MIDI 1.0 names takes that controller (for example 5, portamento time; 65, portamento on and off) (MIDI 1.0 4.2, Table III, PDF 102);
4. where the interface uses NRPN for its parameters, an added parameter takes an NRPN number the interface leaves unassigned, so that its controllers stay as the interface left them;
5. otherwise a parameter of more than 128 values takes a coarse controller among 0 to 31 that MIDI 1.0 leaves undefined, with its fine controller 32 higher, or, where the adopted interface uses every such controller, two consecutive single-byte controllers that MIDI 1.0 leaves undefined, the lower the coarse, which the family document pairs (MIDI-74); and every other parameter one controller that MIDI 1.0 leaves undefined. MIDI 1.0 4.2's Table III (PDF 102) leaves undefined controllers 3, 9, 14, 15 and 20 to 31 among the coarse controllers 0 to 31, whose fine controllers are 35, 41, 46, 47 and 52 to 63 ("LSB for values 0-31"), and controllers 85 to 90 and 102 to 119 among the single-byte controllers. Controllers 16 to 19 and 80 to 83, the general purpose controllers, which "may be used by a manufacturer for any added functions" (printed page 12, PDF 44), and controllers 75 to 79, sound controllers 6 to 10, which MIDI 1.0 defines as sound controllers with no default assignment (Table III; printed page 14, PDF 46), are not undefined and are not taken under this rule;
6. no controller MIDI 1.0 gives another meaning is taken (bank select 0 and 32, data entry 6 and 38, 96 to 101, and the others Table III names) (MIDI 1.0 4.2, Table III, PDF 102).

`synthd.md`'s map follows the Voyager's for the controls the two panels share, and rules 1, 2, 5 and 6 for the rest. Every number the family documents chose under rules 3, 5 and 6 was checked against MIDI 1.0 4.2's Table III on 18 November 2026: synthD's own (`synthd.md`, SD-17) are the pair 89 and 90, two consecutive single-byte controllers because the Voyager's map uses every controller from 1 to 31, and the single controllers 102 to 113, all undefined and none used by the Voyager's map; synth8's 107 and 108 (`synth8.md`, S8-16) and synth80's 3 and 20 to 31 (`synth80.md`, S80-18 and S80-20) are undefined controllers.
- Reason: DEC-6453 item 3 lets NeoTeletext define a message only where nothing exists; one rule for every family keeps such definitions from colliding with MIDI 1.0 or with the interface, and the same in every family.
- Source: DEC-6453 item 3; `synthd.md`, SD-17's reason (the same rules).
- Verification: Each family document's test that no controller number appears twice; a test in this suite checks every NeoTeletext-defined number against rules 1 and 2.

**MIDI-79. A patch of control values is its control changes.** For a family whose patch form is a list of control values, setting a patch (by program change or inline) MUST have exactly the effect of the control changes of its values, in its order, at one tick; and each byte of the patch MUST be a value 0 to 127, every one of which is valid.
- Reason: The patch and the live messages are one definition (`synthd.md`, SD-26), so a tool turns one into the other with the family's table alone.
- Source: Decision A4; `synthd.md`, SD-22 and SD-26.
- Verification: For each such family, a test sets a patch and the same values as control changes and checks identical samples.

**MIDI-80. One controller number, many meanings.** A controller number MUST mean in each family what that family's document says, and nothing across families except the common layer (MIDI-9). The server MUST check a control change against the family of the sound it is in.
- Reason: Controller 3 is oscillator A's frequency on synth53 and the cutoff on synth8; controller 7 is "MASTER VOLUME", 0 to 120, on the Prophet-5 (page 4), "PATTERN PART LEVEL" on the JUPITER-08 and "GLOBAL VOLUME" on Deckard's Dream (PDF 74). As built, every synthesizer took one shared set of six controllers.
- Source: The documents named.
- Verification: A server test sends controller 3 to a synth53 and a synth8 sound and checks each is accepted and means its family's parameter.

**MIDI-81. Resolution.** Each parameter MUST be carried at the resolution its interface gives it, and its family document MUST state which:

| Message | Resolution | Example |
|---|---|---|
| A control change | 7 bits, 0 to 127; or a narrower range the interface states | Prophet-5 controller 26, glide rate, 0 to 120 (page 4) |
| A coarse and fine pair | 14 bits, 0 to 16,383 | `synthd.md`, SD-18 |
| NRPN data entry | 14 bits (controller 6 the high seven, 38 the low seven), within the parameter's stated range | Prophet-5 NRPN 0, oscillator A frequency, 0 to 120 (page 8) |
| Pitch bend | 14 bits, centre 8,192; the DX7 ignores the low seven bits (page 32) and the Juno-106 the low six (PDF 35) | |
| A system exclusive parameter change | 7 bits a data byte | DX7 parameter data 0 to 99 (page 31) |

A value above a parameter's stated range (for example 121 to 127 to a Prophet-5 controller of range 0 to 120) MUST be treated as its family document says; where the interface does not say, the family document MUST choose (clamp or pass over) and list it as its own.
- Reason: Each interface's resolution, unchanged; and a rule where the interface leaves a value undefined.
- Source: The documents named.
- Verification: The family documents' tests at each parameter's edges and past them.

**MIDI-82. Volume, controller 7.** A family whose adopted interface names controller 7 as a volume, or that takes it from the common layer (MIDI-9), MUST apply it as a gain on the part's output, separate from any volume of the patch; its value MUST be 127 at the start of a sound; and, where neither the interface nor the family document states another law, the gain MUST be `(value × value) ÷ (127 × 127)` of full, moving to a new value by at most `1 ÷ 256` of full a sample (from nothing to full in 256 samples, 5.3 milliseconds). The law MUST be the same in every family (MIDI-92); a family MAY move the gain more slowly than the slew where its click measure needs it (synth7 moves by at most 1.5 dB in each 32 samples, as built). synth7's law today is this one, with that slower slew (`synth7.md`, S7-15).
- Reason: One law for every synthesizer that has no other, as built and shared, so a program's fades sound alike on each; `synthd.md` relies on this document to state it.
- Source: `analog/volume.rs` (`wanted`, `VOLUME_SLEW`, own choices); `synth7/rack.rs` (`VOLUME_STEP`); `synthd.md`, SD-10.
- Verification: The existing tests of `analog/volume.rs`; a test for each family checks the gain at values 0, 64 and 127.

**MIDI-83. No click from a control.** For every parameter of every family, a change under a sounding note MUST pass the engine's control-sweep measure: the largest sample-to-sample step in the 50 milliseconds after the change MUST be at most 1.5 times the larger of the sound's own largest step and the largest step of the sound the change goes to (`tests/control_sweep_support.rs`, `BOUND`, `AFTER`). Each family's control sweep MUST drive the change through the message the interface defines (MIDI-72), not through an internal call.
- Reason: A step in a level or a filter is heard as a click; the measure exists and each instrument passes it today through internal calls.
- Source: `tests/control_sweep_support.rs`; `tests/*_control_sweep.rs`; DEC-6460 item 2 (the DX7's volume moved by at most 1.5 dB a step for this reason).
- Verification: Each family's `<family>_control_sweep.rs`, driven by messages.

### 11.1 Common MIDI behaviours: one rule for every synthesizer

The owner requires every synthesizer to behave the same way where MIDI defines a behaviour common to all instruments (DEC-6464: "we require ALL synths to behave the same way in this regard"). The filed interfaces differ on several such behaviours. The table lists each difference found; MIDI-84 to MIDI-92 set the one rule, and each family document MUST list its interface's departure from the rule with the requirement as its reason. The synth6581 family takes no channel messages (`synth6581-synth8580.md`, S6581-26), so none of these rules applies to it.

| Behaviour | What the filed interfaces say | The rule |
|---|---|---|
| Reset all controllers (121) | Prophet-5: "Clears all MIDI controllers to 0, MIDI volume to maximum" (MIDI, page 2). JU-06A: recognised, effect not stated. DX7 (page 32), Juno-106 (PDF 35), Voyager (`synthd.md`), JUPITER-08, Deckard's Dream (PDF 71 to 74): not listed. | MIDI-84: RP-015, volume unchanged |
| All notes off (123) | Juno-106 (123 to 127), JU-06A, Prophet-5 ("Clear all MIDI notes"), Voyager: recognised. DX7, JUPITER-08, Deckard's Dream: not listed. | MIDI-85 |
| All sound off (120) | JU-06A: recognised. Deckard's Dream: controller 120 is "GLIDE MODE" (PDF 74). Every other: not listed. As built: synth7 fades it over 21 milliseconds (DEC-6460), synthD over at most 256 samples (`synthd.md`, SD-13). | MIDI-86 |
| Sustain or hold (64) | Prophet-5: on at 64 or higher (page 2). DX7: 0 off, 127 on, other values not stated (page 32). Juno-106: hold on at 1 to 127 (PDF 35). JU-06A, JUPITER-08: "HOLD", "Hold Pedal", values not stated. Deckard's Dream: "SUSTAIN PEDAL", range blank (PDF 74). Voyager: not recognised. | MIDI-87: down at 64 to 127 |
| Note on of velocity 0 | DX7 (pages 30 and 32) and Prophet-5 (page 2): a note off. Others: not stated. | MIDI-88: a note off, everywhere |
| Omni off, omni on, mono on, poly on (124 to 127) | Juno-106 (PDF 35) and JU-06A: each as all notes off. DX7: 125 "OMNI all key off", 126 "MONO all key off", 127 "POLY all key off", the values of 125 and 127 marked "ignored" (page 32); 124 not listed. Others: not listed. | MIDI-89: all notes off only |
| Pitch bend range | DX7: function parameter 65, 0 to 12, by system exclusive (page 31). Prophet-5: controller 70 and NRPN 86, 0 to 11 for 1 to 12 semitones, a parameter of each program (pages 5 and 9; User's Guide, page 37). JU-06A: controller 87, "BEND RANGE". JUPITER-08: controller 41, "BEND PITCH", the part's Bend Pitch, 0 to 1200 (`synth8.md`, S8-14). Juno-106: a panel knob, no message. Voyager: a setting of each preset, no message (`synthd.md`, section 12.1). Deckard's Dream: a global setting with no message, 1 to 99 semitones, default 3 (PDF 60). None documents RPN 0. | MIDI-90: RPN 0 everywhere, beside each interface's own |
| Pitch bend resolution | DX7: least significant byte ignored (page 32). Juno-106: low six bits ignored (PDF 35). Others: 14 bits or not stated. | MIDI-91: all 14 bits |
| Volume (7) | DX7: volume, 0 to 127, "LS 4 bit are ignored" (page 32). Prophet-5: "MASTER VOLUME", 0 to 120 (page 4). Voyager: "MASTER VOLUME", the pair 7 and 39 (`synthd.md`, section 6). JUPITER-08: "PATTERN PART LEVEL", the part volume 0 to 127 (`synth8.md`, S8-9). Deckard's Dream: "GLOBAL VOLUME", 0 to 127. Juno-106 and JU-06A: not listed. | MIDI-92: one law, MIDI-82 |

**MIDI-84. Reset all controllers, in every synthesizer: RP-015.** Every synthesizer that takes channel messages MUST answer controller 121 identically, as the MIDI Manufacturers Association's and AMEI's Recommended Practice RP-015 says (RP-015, page 2, "DETAILS"), for the part the message's channel addresses (RP-015: "the following actions are taken for the specified MIDI channel"):
1. **Reception.** MIDI 1.0 says "Reception follows the same rules as All Notes Off — Ignore if Omni is On" (printed page 25, PDF 57) and gives the message the value 0 (Table IV, PDF 104); RP-015 notes that "many implementations allow any value (don't care)" (page 1). Every synthesizer MUST accept any value, and the server MUST write the value 0. No NeoTeletext synthesizer has an Omni state that a message sets (MIDI-89), and a part is addressed only by the channels its family's channel map gives it (MIDI-67). A family whose map gives all 16 channels to its one part (MIDI-68) hears voice messages as an instrument in Omni On mode would, yet MUST answer controller 121, and controller 123 (MIDI-85), on every one of those channels: this departure from MIDI 1.0's reception rule is listed in section 19 with its reason.
2. **What is set** (RP-015, page 2): the modulation wheel, controller 1, to 0; expression, controller 11, to 127, where the family has it; the pedals, controllers 64, 65, 66 and 67 (the sustain pedal, the portamento switch, sostenuto and the soft pedal, MIDI 1.0 4.2, Table III, PDF 102), to 0, wherever the family responds to one with that meaning, even where its family document makes that meaning a parameter of its patch (synthD's GLIDE switch is controller 65, portamento on and off), since RP-015 names them among the controllers set and item 4's latitude does not reach them; where an adopted interface gives one of these numbers another meaning (Deckard's Dream makes 65, 66 and 67 tone controls of its patch, `synth80.md`), it is not one of RP-015's pedals there and falls under item 4; the registered and non-registered parameter number, controllers 98 to 101, to the null value 127 each, so that no parameter is selected (MIDI-76); pitch bend to its centre, 8,192 (RP-015: "Set pitch bender to center (64/0)"); channel pressure to 0; and every key's polyphonic pressure to 0.
3. **What is left unchanged** (RP-015, page 2): volume, controller 7; pan, controller 10; bank select, controllers 0 and 32; the current program and patch; the effect controllers 91 to 95; the sound controllers 70 to 79; the values of registered and non-registered parameters, as against their selection in item 2, so that the pitch bend range of MIDI-90 stays; and the channel mode messages ("Do NOT reset other channel mode messages (#120-#127)"), which in NeoTeletext's synthesizers hold no state to reset (MIDI-89).
4. **Every other controller.** RP-015 says that any other controller a device can respond to "should be set to 0, or the behavior should be specified and/or documented", and that a manufacturer may leave one unaffected "as long as the behavior is documented" (page 2). Each family document MUST list, for every other controller its synthesizers respond to (for example breath 2, foot 4, portamento time 5, balance 8, legato 68, hold 2 69, portamento control 84, and every controller that moves a parameter of the patch), whether controller 121 sets it to 0 or leaves it, with the reason. A controller that moves a parameter of the patch MUST be left unchanged, since it is the patch, not a performance control (DEC-6464 item 4). The list is NeoTeletext's documentation of its response, which RP-015 asks of a manufacturer ("Manufacturers should create a section in their documentation for response to the Reset All Controllers message", page 2).
5. **Notes.** Notes held MUST NOT be released by it, except as the sustain pedal's going to 0 releases the notes it held.
6. **Departures.** Where an adopted interface departs from RP-015 (the Prophet-5 sets volume to its maximum, Prophet-5 MIDI page 2), the synthesizer MUST follow this rule and its family document MUST list the departure with DEC-6464 as its reason: RP-015's permission to depart covers only item 4's controllers, not volume, which it names. Where an interface does not recognise controller 121 (the DX7, the Juno-106, the Voyager, the JUPITER-08, Deckard's Dream), the synthesizer MUST still act on it, as the common layer (MIDI-9).
- Reason: The owner requires all synthesizers to behave the same way; RP-015 is MIDI's one standard of the reset, and keeping volume avoids a reset making a quiet sound suddenly loud (DEC-6464). A pedal that a family makes a parameter of its patch (synthD's GLIDE switch is controller 65, the portamento switch MIDI 1.0 names, `synthd.md`, SD-13) is set to 0 like any pedal, because RP-015 names the pedals 64 to 67 among those set, without exception, and DEC-6464 item 6 makes RP-015's text hold over a family's own reading; a number an adopted interface gives a meaning other than the pedal's is not that pedal, and RP-015's "Set Pedals" does not reach it.
- Source: DEC-6464 version 2, items 1 to 7 (the owner required one behaviour for all; the choice of RP-015 was made under DEC-6453 and is recorded as proposed, awaiting the owner's confirmation); RP-015, pages 1 and 2; MIDI 1.0 4.2, printed page 25 (PDF 57) and Table IV (PDF 104); the GM Developer Guidelines, page 6 (PDF 315), for the null value; Prophet-5 MIDI, page 2.
- Verification: For each family, a test moves every performance controller, the volume, a patch parameter and the bend range, sends controller 121 with the value 0 and again with the value 127, and checks each against items 2 and 3 and the family document's list of item 4; a test sends it on each of the 16 channels and checks it acts on every channel that addresses a part; a test for synth53 checks volume is unchanged.

**MIDI-85. All notes off, in every synthesizer.** Controller 123 MUST release every key held on the part, exactly as a note off of each would, each voice going to the release stage of its envelope; a note held by the sustain pedal MUST stay held until the pedal goes up, and a note in its release MUST go on with it. Nothing else changes. MIDI 1.0 gives the message the value 0 (Table IV, PDF 104); every synthesizer MUST accept any value, and the server MUST write the value 0. It MUST be received as MIDI-84 item 1 says of controller 121, on every channel that addresses a part, although MIDI 1.0 says "Receivers should ignore an All Notes Off message while Omni is on" (printed page 25, PDF 57): the departure is listed in section 19.
- Reason: One behaviour where four interfaces recognise it and three do not list it; it is the message a sender uses to end every note it started. The release and the pedal's hold are MIDI 1.0's rules: "All Notes Off should force voices to go to the release stage of the envelope, and not terminate the sound of the notes abruptly", and "A Hold or Sustain pedal 'On' message takes priority over Note Off and All Notes Off until it is released" (A-5, PDF 95).
- Source: Juno-106 manual, PDF 35; JU-06A chart; Prophet-5 MIDI, page 2; `synthd.md`, SD-11; MIDI 1.0 4.2, printed pages 24 and 25 (PDF 56 and 57), A-5 (PDF 95) and Table IV (PDF 104).
- Verification: For each family, a test holds three keys, sends 123, and checks the notes release as note offs would; with the pedal down, checks they sound until the pedal goes up.

**MIDI-86. All sound off, in every synthesizer.** Controller 120, whatever its value, MUST bring every voice of the part to silence, held, sustained and releasing alike, within 1,024 samples (21.3 milliseconds), by a fade that passes the click measure (MIDI-83), and then empty every voice; it MUST NOT change the pedal, any controller or the patch. Deckard's Dream's use of controller 120 for glide mode is moved by `synth80.md` to controller 3 and listed as a departure (`synth80.md`, S80-20).
- Reason: A program must be able to silence any synthesizer at once with one message. 1,024 samples is the longest fade built today (synth7's 21 milliseconds), so both built behaviours already meet it; a step to silence would click.
- Source: JU-06A chart; DEC-6460 item 2 (synth7's 21-millisecond fade); `synthd.md`, SD-13 (256 samples); Deckard's Dream manual, PDF 74; MIDI-9; MIDI 1.0 4.2, printed page 25 (PDF 57): "Upon reception, all notes currently on are turned off and their volume envelopes are set to zero as soon as possible".
- Verification: For each family, a test holds a chord with the pedal down and a long release, sends 120, and checks the output is 0 by sample 1,024 and the sweep measure holds.

**MIDI-87. The sustain pedal, in every synthesizer.** Controller 64 MUST put the pedal down at values 64 to 127 and up at 0 to 63, in every family. While it is down, a key released MUST go on sounding as if held, and when it goes up every note so held MUST be released. The Juno-106's hold on at 1 to 127 (PDF 35) is a departure `synth106-synth60.md` lists.
- Reason: One threshold for every synthesizer, the one the Prophet-5 states and MIDI 1.0 gives ("If a receiver is expecting switch information it should recognize 0-63 (00H-3FH) as "OFF" and 64-127 (40H-7FH) as "ON"", printed page 12, PDF 44), so a performance's pedal means the same on each.
- Source: Prophet-5 MIDI, page 2; Juno-106 manual, PDF 35; DX7 manual, page 32; MIDI 1.0 4.2, printed page 12 (PDF 44) and Table III (PDF 102: 64, "Damper pedal (sustain)").
- Verification: For each family, a test sends values 0, 1, 63, 64 and 127 and checks the pedal's state after each.

**MIDI-88. A note on of velocity 0, in every synthesizer.** A note on whose velocity is 0 MUST be a note off of that key, with a release velocity of 64, in every family.
- Reason: MIDI's rule, stated by the DX7 and the Prophet-5, and relied on by files and running status.
- Source: DX7 manual, pages 30 and 32; Prophet-5 MIDI, page 2; MIDI 1.0 4.2, printed page 10 (PDF 42: "A receiver must be capable of recognizing either method of turning off a note, and should treat them identically") and Tables I and II (PDF 100 and 101: "a velocity of 0 = Note Off"). The release velocity of 64 is MIDI 1.0's ("vvvvvvv = 0: Note-Off (with velocity of 64)", printed page 10, PDF 42); it matters only to a family that uses release velocity.
- Verification: For each family, a test plays a note ended by a note on of velocity 0 and by a note off of velocity 64 and checks identical samples.

**MIDI-89. Mode messages, in every synthesizer.** Controllers 124, 125, 126 and 127 MUST each, whatever its value, act as all notes off (MIDI-85) and do nothing else in every family: none changes the channels heard (MIDI-71) or switches the part between mono and poly. The DX7's 126 ("MONO all key off", page 32) is a departure `synth7.md` lists; a family whose instrument has a mono and poly mode sets it by its patch or by the parameter message its interface defines, never by 126 or 127. That each of the four also acts as all notes off is MIDI 1.0's ("Messages 123 through 127 also function as All Notes Off messages", printed page 20, PDF 52; Table IV, PDF 104), and so is a receiver's leave to ignore a request for a mode it does not implement (printed page 7, PDF 39; printed page 23, PDF 55). MIDI 1.0 recognises mode messages "only when sent on the Basic Channel" (printed page 20, PDF 52); NeoTeletext's synthesizers have no basic channel (MIDI-71), so they MUST act on these messages on every channel that addresses a part, a departure listed in section 19. Their values (0, or for 126 the number of channels) MUST be accepted whatever they are.
- Reason: One behaviour; the Juno-106 and the JU-06A already treat all four as all notes off, and a mode change by a message that also ends notes is a cable-era setting a program does not expect.
- Source: Juno-106 manual, PDF 35; JU-06A chart; DX7 manual, page 32; MIDI 1.0 4.2, printed pages 7, 20 and 23 (PDF 39, 52 and 55) and Table IV (PDF 104).
- Verification: The test of MIDI-71, for each family.

**MIDI-90. Pitch bend range, in every synthesizer: RPN 0.** Every synthesizer that plays notes MUST act on registered parameter number 0, pitch bend sensitivity, selected by controller 101 (the registered parameter number's most significant byte) at 0 and controller 100 (its least significant byte) at 0, and set by data entry, controller 6 the semitones and controller 38 the cents, or stepped by data increment, controller 96, and data decrement, controller 97, setting the range of a full bend either way ("Pitch Bend Sensitivity is defined as Registered Parameter Number 00 00. The MSB of Data Entry represents the sensitivity in semitones and the LSB of Data Entry represents the sensitivity in cents", MIDI 1.0 4.2, printed page 18, PDF 50; Table IIIa, PDF 103; printed page 17, PDF 49; Table III, PDF 102). MIDI 1.0 4.2 states no size for a step of increment or decrement; each MUST move the range by one cent, whatever its value, and not below 0, NeoTeletext's own reading (section 19), which `synthd.md`, SD-6, states for synthD. Where the adopted interface has its own message for the range (the DX7's function parameter 65, the Prophet-5's controller 70 and NRPN 86, the JU-06A's controller 87, the JUPITER-08's controller 41), that message MUST set the same range, the last received of either holding. The range MUST be limited to the most the family document states for its instrument (for example 12 semitones on the DX7, 12 on the Prophet-5, whose parameter 86's values 0 to 11 are 1 to 12 semitones, `synth53-synth52-synth51.md`, S53-8), a larger value set to that most. Before any message the range MUST be the family's default, which its family document states. A program change MUST NOT change the range; reset all controllers MUST NOT change it (MIDI-84).
- Reason: The interfaces each set the range their own way and three have no message at all; RPN 0 is MIDI's one standard way, so a program can set a bend range the same way on every synthesizer. It is listed in section 19 as an addition to every adopted interface, none of which documents it.
- Source: DX7 manual, page 31; Prophet-5 MIDI, pages 5 and 9; JU-06A chart; JUPITER-08 chart; `synthd.md`, SD-6 (written for this rule, pending open question 5); MIDI 1.0 4.2, printed pages 17 and 18 (PDF 49 and 50), Table III (PDF 102) and Table IIIa (PDF 103), for registered parameter number 0's number, its selection and its data.
- Verification: For each family, a test sets the range by RPN 0 to 1, 7 and 24 semitones, steps it by increment and decrement and checks each step is one cent, and sets it by the interface's own message, bends fully, and checks the pitch against the range (24 limited to the family's most); a test checks a program change and controller 121 leave it.

**MIDI-91. Pitch bend resolution, in every synthesizer.** Every synthesizer MUST use all 14 bits of a pitch bend, `data byte 2 × 128 + data byte 1`, centre 8,192, moving the pitch by `(number − 8,192) ÷ 8,192` of the range (8,191 ÷ 8,192 at the top). The DX7's ignoring of the low byte (page 32) and the Juno-106's of the low six bits (PDF 35) are departures their family documents list.
- Reason: One behaviour; a program's bend then glides alike on every synthesizer instead of stepping on two of them.
- Source: DX7 manual, page 32; Juno-106 manual, PDF 35; `synthd.md`, SD-6 (the same formula); MIDI 1.0 4.2, printed page 19 (PDF 51: always "14 bit resolution (2 bytes)", the centre "00, 64", the extremes "00, 00" and "127, 127") and Table II (PDF 101: the least significant byte first).
- Verification: For each family, a test bends from 8,192 to 8,193 and checks the pitch moves.

**MIDI-92. Volume, in every synthesizer.** Controller 7 MUST be a volume with MIDI-82's law in every family that plays notes, values 0 to 127, 127 full. The Prophet-5's range of 0 to 120 (page 4) is a departure `synth53-synth52-synth51.md` lists (its 120 is not full); the JUPITER-08's "PATTERN PART LEVEL" and Deckard's Dream's "GLOBAL VOLUME" are taken as this volume; the Juno-106 and the JU-06A, which list no controller 7, take it from the common layer (MIDI-9).
- Reason: One law, so a program's mix and fades are alike on every synthesizer.
- Source: The documents named; MIDI-82.
- Verification: The test of MIDI-82, for each family.

---

## 12. Live sounds: joining, restatement and loss

A viewer may start hearing a live sound at any block (DEC-611: a play joins at the newest block), and a live block may be lost. Either leaves the viewer's synthesizer without the program changes, patches and controller values sent before. As built, the kit's program repeater rewrites each part's last program change into a free slot when 500 milliseconds pass without one (`program-repeater.ts`), and the synth6581 family's whole register image in every block makes it need nothing. A program change alone is not enough under the adopted interfaces: a patch sent inline, an NRPN, a system exclusive parameter change or a control change moves a part away from its bank patch, and a repeated program change would put it back. The server therefore restates the whole state.

**MIDI-93. What a restatement is.** A part's restatement MUST be the messages that bring a part in any state to the part's present state: its bank select values and its program change (or, where its last patch came inline, that patch's message, MIDI-60); then the latest value of every parameter moved since by a control change, a coarse and fine pair, an NRPN or RPN (as a whole sequence, MIDI-37) or a system exclusive parameter change; then pitch bend, channel pressure, controller 7, controller 1 and the sustain pedal, where they are not at the values a fresh synthesizer holds (pitch bend 8,192, channel pressure 0, controller 7 at 127, controller 1 at 0, the pedal up). Held notes MUST NOT be restated: a viewer who joins hears each note from its next note on. For the synth6581 family the restatement is a full register update of the registers' present values (`synth6581-synth8580.md`, S6581-46). Each family document MUST state its restatement exactly, using these rules. A family document MAY instead restate the part's program and the parameters moved since by one inline patch carrying the part's present state, where that is the interface's own message and is no longer than the messages it stands for (as `synth106-synth60.md`, S106-40, does with the Juno-106's patch message, `synth53-synth52-synth51.md`, S53-46, with the edit buffer dump, and `synth7.md`, S7-49, with the single-voice bulk dump).
- Reason: A joining viewer must end up with the sender's state, whatever moved it; restating notes would start notes mid-way through, which a listener hears as wrong.
- Source: DEC-6410 item 12 (a sender repeats each part's settings); `program-repeater.ts`; `synth6581-synth8580.md`, S6581-46; `synthd.md`, SD-28.
- Verification: For each family, a test drives a part through a program change, an inline patch, ten parameter changes and a bend, then plays the part's restatement into a fresh synthesizer, and checks the two synthesizers' states equal.

**MIDI-94. The server keeps each part's state.** For every live sound, and while it writes every stored sound, the server MUST track each part's state from the events it writes, as MIDI-93 needs, keeping for each parameter only its latest value. The state it keeps MUST be bounded by the family document's parameter table (each parameter once), the 16 channels and one inline patch a part.
- Reason: Only the server sees every event, so only it can restate (DEC-6462 item 1: the server "repeats what a viewer who joins late needs").
- Source: DEC-6462 item 1.
- Verification: A server test of the tracked state after a long sequence of every message of each family.

**MIDI-95. The order of a restatement.** A restatement MUST be written at a block's tick before the program's events of that tick (MIDI-35), in the order of MIDI-93, the parameters in ascending order of their message (controllers by number, coarse before fine; then NRPNs by number; then system exclusive parameter changes by parameter number), and MUST carry the state as it stands after every event of earlier ticks.
- Reason: A fixed order gives identical bytes every time (MIDI-44) and puts a pair's coarse before its fine part.
- Source: MIDI-35, MIDI-37, MIDI-44.
- Verification: A server test checks the bytes of a restatement for a known state.

**MIDI-96. How often a live sound is restated.** The server MUST write every part's restatement of a live sound in the first block it sends and at least once in every 50 blocks (1,000 milliseconds) after; it SHOULD write it every 25 blocks (500 milliseconds) where the blocks have room. A part that has received no message since the sound started MUST still be restated, so that a viewer's part that played a default meanwhile is put right.
- Reason: The worst a joining viewer then hears wrong is about one second, the bound of DEC-6410 item 12 and of `synth6581-synth8580.md`, S6581-46; 500 milliseconds is today's interval.
- Source: DEC-6410 item 12; `program-repeater.ts` (`PROGRAM_REPEAT_BLOCKS`, 500 milliseconds); S6581-46.
- Verification: A server test feeds an hour of live events and checks no 50 consecutive blocks lack any part's restatement.

**MIDI-97. A restatement is inaudible to a viewer who has the state.** A synthesizer that already holds the state a restatement carries MUST render identical samples with and without it: a program change to the program already chosen, or the same inline patch, MUST NOT restart envelopes, oscillator phases, LFOs or the filter's state, and a parameter set to the value it holds MUST change nothing. Each family document MUST make this true and test it.
- Reason: Restatements go to every viewer, most of whom lost nothing.
- Source: `synth6581-synth8580.md`, S6581-47 (the same rule).
- Verification: For each family, a test plays the audio demo's tunes with and without a restatement at a seeded random tick of every block and checks the samples identical.

**MIDI-98. Fitting restatements into blocks.** One part's restatement MUST be written whole in one block at one tick (MIDI-37). Different parts' restatements MAY be spread over different blocks within the interval of MIDI-96. Where a block lacks room (MIDI-30, MIDI-31) for a part's restatement, the server MUST put it in the next block with room; if 50 blocks pass without room for a part, the server MUST refuse the program's message that filled them, naming the blocks and saying they leave no room to restate.
- Reason: A part restated in two halves, one lost, would be left in neither state. Sixteen inline DX7 voices (16 × 167 bytes) do not fit one block, so parts must be spread. A stream so dense that a restatement never fits is refused rather than left without one.
- Source: MIDI-30, MIDI-31, MIDI-37.
- Verification: A server test with 16 synth7 parts each on an inline voice checks every part restated within 50 blocks; a test with 50 full blocks checks the refusal.

**MIDI-99. A stored sound begins with its restatement.** The server MUST write, at tick 0 of block 0 of every stored sound, the restatement of every part the sound uses, carrying the state before the sound's first event. A family document MAY instead require the program's own first events to be that restatement and refuse a stored sound that lacks it (as `synth6581-synth8580.md`, S6581-45, does).
- Reason: When a stored sound loops, its synthesizer is not reset (MIDI-105), so the start must set every part again; and a sound then plays the same from its first block in every receiver.
- Source: `synth6581-synth8580.md`, S6581-45 and S6581-49.
- Verification: A server test checks block 0 of a stored sound of each family begins with the restatements.

**MIDI-100. Joining a live sound.** A receiver that starts a live sound part-way MUST start at the newest block (DEC-611) with a new synthesizer whose parts stand as MIDI-61 says, and MUST play on as blocks come; the server's restatements (MIDI-96) put each part right within 1,000 milliseconds. The server MUST NOT send one connection blocks different from another's for the same block number.
- Reason: The audio profile is a broadcast format: a block number has one content for every receiver (MIDI-44), on teletext lines as on the network; a block made for one joining viewer would conflict with the same block another viewer holds. Open question 4 asks whether a later version should add a restatement for a joining connection.
- Source: DEC-611; `store/live.rs` (a differing block puts a sound in conflict).
- Verification: A test joins a live sound at every block of a 3-second sound and checks each receiver's synthesizer state equals the sender's within 50 blocks.

**MIDI-101. The live ring, the lookahead and the stall.** A live sound of an event codec MUST be kept and played as every live sound is: a ring of 32 blocks; a block still missing when the newest is 3 blocks past it is played through as lost (MIDI-102); with no new block for 2,000 milliseconds the sound stops with a 100-millisecond fade.
- Reason: The audio profile's live rules, unchanged (decision A2).
- Source: `profile.rs` (`LIVE_RING_BLOCKS`, `LIVE_LOOKAHEAD_BLOCKS`, `LIVE_STALL_MS`, `LIVE_STALL_FADE_MS`); DEC-611.
- Verification: The existing live-sound tests on event blocks.

**MIDI-102. A lost block.** When a live block is played through as lost, the receiver MUST, before rendering it, tell the synthesizer that input was lost; the synthesizer MUST then do what its family document states (for every family that plays notes: release every note and lift the sustain pedal on every part, and set every channel's RPN and NRPN selection to none, MIDI-76; for the synth6581 family: nothing, the registers sound on, S6581-48), and render the block's 20 milliseconds with no event. A lost block that arrives after it was played through MUST NOT be applied.
- Reason: The lost block may have held note offs, so notes are released rather than left hanging; its parameter changes cannot be known, so the panel is left and the next restatement repairs it. Applying a block late would play its events at the wrong time.
- Source: DEC-6410 item 12; `receiver/instruments.rs` (`conceal`, `send_live`); `synthd.md`, SD-25; S6581-48.
- Verification: The existing test `a_live_sound_of_each_synthesizer_plays_and_a_lost_block_releases_its_notes`, on event blocks, extended with an NRPN data entry after the loss.

**MIDI-103. The largest block of a live sound.** The server MUST write the block bytes field of a live sound's OBJECT as 1,005, the largest block allowed, so that any block it later writes fits the receiver's ring.
- Reason: A live sound's future blocks are not known when it is announced. The cost is a ring of 32 × 1,009 bytes, 32,288 bytes, for each live sound, which a desktop receiver's 4 MiB store holds many times.
- Source: MIDI-30, MIDI-46.
- Verification: A server test of a live OBJECT.

---

## 13. Stored sounds

**MIDI-104. The length of a stored sound.** A stored sound of an event codec MUST be 1 to 6,000 blocks (two minutes) and its blocks MUST total at most 960,000 bytes (MIDI-41). The server MUST refuse a longer or larger one, naming which bound.
- Reason: Two minutes is the profile's longest stored sound (`protocol.rs`, `MOST_INSTRUMENT_BLOCKS`); 960,000 bytes the most store any stored sound takes today (MIDI-41).
- Source: `protocol.rs`; MIDI-41.
- Verification: Server tests at each bound and one past it.

**MIDI-105. Looping.** When a stored sound loops, the receiver MUST go on from its last block to block 0 without resetting or replacing the synthesizer, so notes still sounding, envelopes, phases and filters carry across the join; block 0's restatement (MIDI-99) sets every part again.
- Reason: A reset at the join is heard as a click; as built a loop plays on across its join.
- Source: DEC-6410 item 13; `synth6581-synth8580.md`, S6581-49.
- Verification: A test loops a two-block sound and checks the join is no larger a step than any other block boundary.

**MIDI-106. Rendering as played, within a budget.** The receiver MUST render a stored sound's blocks in order, from block 0, as far as they have arrived without a gap, at most 50 blocks (one second of sound) a call, asking to be called again at once while more wait, as today. The work of one block MUST be bounded by its 1,005 bytes and 256 events, the family's bounded work per event, and 960 samples of rendering, whatever the block holds.
- Reason: A sound of any length never holds the port for longer than the budget's blocks cost (`receiver/instruments.rs`, `RENDER_BUDGET_BLOCKS`).
- Source: `receiver/instruments.rs`; DEC-6410 item 13.
- Verification: The existing render-budget test; a timed test of the costliest block each family allows, printing its time against a stated budget.

---

## 14. The codecs, their versions and the program protocol

**MIDI-107. The codec numbers.** The event codecs and the bank codec MUST have these codes in the OBJECT record's codec field (open question 1 gives the alternative of keeping 3 to 11; DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation)):

| Code | Codec | Blocks |
|---|---|---|
| 12 | synth6581 family (synth6581, synth8580; tag 3 chooses) | Event lists |
| 13 | synth7 | Event lists |
| 14 | synth106 family (synth106, synth60; tag 5 chooses) | Event lists |
| 15 | synthD | Event lists |
| 16 | synth53 family (synth53, synth52, synth51; tag 5 chooses) | Event lists |
| 17 | synth8 | Event lists |
| 18 | synth80 | Event lists |
| 19 | Bank, of any family (tag 6 names it) | Pieces of a bank image (MIDI-55) |

A receiver built without a family MUST read its code, and a bank for it, as unsupported and ignore the object, as today.
- Reason: The content of every synthesizer block changes (decision A3) and so does every patch form (decision A4). Under the same codes a receiver of today would read an event list as four-byte slots and play wrong notes; under new codes it ignores what it cannot play, the profile's existing rule for an unknown codec. One bank codec replaces two (5 and 11) because a bank image says its own form.
- Source: Decisions A3 and A4; `codec.rs` (`from_code`: "A receiver built without an instrument ignores its objects, as it would any reserved code").
- Verification: Record tests for each code, with and without its feature built.

**MIDI-108. Codes 3 to 11 are retired.** Codes 3 to 11 MUST be read as reserved by every receiver built after this change, and MUST NOT be given to any codec again.
- Reason: A code given a second meaning would be misread by every receiver that knew the first.
- Source: `codec.rs`.
- Verification: A record test that codes 3 to 11 are ignored as reserved.

**MIDI-109. An older receiver.** A receiver built before this change MUST be expected to ignore every sound of codes 12 to 19 and count it unsupported; the server MUST NOT send a synthesizer's sound under codes 3 to 11 once the change is built.
- Reason: That is the existing behaviour of every receiver for an unknown code, so old browsers fall silent rather than misplay; the browser and the server are rebuilt and deployed together (DEC-6461, "What it changes").
- Source: `codec.rs`; DEC-6461.
- Verification: A test runs the receiver of the engine's last commit before the change on records of codes 12 to 19 and checks the counter and that nothing plays.

**MIDI-110. How the architecture changes later.** A later change that every receiver of these codecs can ignore safely MUST be made by a new OBJECT extension tag (unknown tags are skipped) or by an event a receiver passes over by its length (MIDI-29); any other change to what a block or a bank image means MUST take a new codec code.
- Reason: The OBJECT has no version field for a codec; the code is the version, and the skip rules are what make additions safe.
- Source: `record.rs` (unknown tags skipped); MIDI-23, MIDI-29.
- Verification: Review of each later change against this rule.

**MIDI-111. The program protocol's version.** The program protocol MUST be raised from version 12 (made on 18 November 2026 for the synthesizers' new names, DEC-6461; the server's `PROTOCOL` constant, commit `df662b9`) to version 13 when the interface this document specifies is built, since the messages change shape; a program of version 12 then stops at `start`, naming both versions.
- Reason: The protocol's rule: one number, raised on every change of shape (REQ-2215); as version 12 did for the names.
- Source: `protocol.rs` (`PROTOCOL` = 12, and its history); REQ-2215.
- Verification: The server's protocol test of the version; a kit test that a version-12 program stops.

---

## 15. Standard MIDI Files as input

**MIDI-112. The server reads Standard MIDI Files.** A program MAY give a stored sound's music as the bytes of a Standard MIDI File; the server MUST read it as this section says and turn it into the sound's events. The kits MUST NOT read Standard MIDI Files (MIDI-22); the kit's reader of today (`midi-file.ts`) is removed when this is built.
- Reason: DEC-6462 item 1 ("music as … a Standard MIDI File"); item 3 (no file parsing in the kits).
- Source: DEC-6462; `midi-file.ts`.
- Verification: The server tests of this section; inspection of the kits.

**MIDI-113. Formats and division.** The server MUST read files of format 0 and format 1, and MUST refuse format 2, a file whose header is not `MThd`, a header shorter than 6 bytes, a format 0 file with other than one track, and a division whose top bit is set (time in SMPTE frames) or that is 0. A header longer than 6 bytes MUST be read by its stated length, the bytes past the first 6 skipped. Chunks of other types than `MTrk` MUST be skipped by their length.
- Reason: Formats 0 and 1 are the forms of one piece of music; format 2 holds independent patterns, which is not one sound. SMPTE division is rare in music for these instruments and is refused as built; it can be added later without a change of shape to blocks.
- Source: `midi-file.ts` (formats 0 and 1; SMPTE refused); Standard MIDI Files 1.0, printed pages 3 to 5 (PDF 132 to 134): every chunk's four-character type and 32-bit length, most significant byte first, and "Your programs should expect alien chunks and treat them as if they weren't there"; the header's length 6, its format, its track count, which "will always be 1 for a format 0 file", and its division, whose bit 15 set means time-code-based time; and "it is important to read and honor the length, even if it is longer than 6".
- Verification: A server test for each refusal and for an unknown chunk skipped.

**MIDI-114. Tempo and time.** The server MUST merge every track's tempo meta events (`FF 51 03` and three bytes of microseconds a quarter note, 1 to 16,777,215; a tempo of 0 refused) into one tempo map, a tempo taking effect from its own tick, 500,000 microseconds a quarter note before any; and MUST compute each event's time in microseconds exactly, as a rational number, from the sum over tempo segments of ticks × tempo ÷ division, rounding only once, when MIDI-17 turns the time into a tick: `tick = floor((numerator + 50 × denominator) ÷ (100 × denominator))`, in integers wide enough that no step overflows.
- Reason: Every tempo change is applied, as built; computing from exact sums keeps a long file in time with no drift.
- Source: `midi-file.ts` (`DEFAULT_TEMPO`, every tempo change applied); MIDI-17; Standard MIDI Files 1.0, printed page 9 (PDF 138), the set tempo meta event `FF 51 03 tttttt`, "in microseconds per MIDI quarter-note", a 24-bit value; printed page 5 (PDF 134), "If they don't, the time signature is assumed to be 4/4, and the tempo 120 beats per minute" (500,000 microseconds a quarter note); printed page 14 (PDF 143), time from ticks, tempo and division. Standard MIDI Files 1.0 asks that a format 1 file keep its tempo map in its first track (printed page 5, PDF 134); merging every track's tempo events reads that file the same and is NeoTeletext's own tolerance of a file that does not.
- Verification: A server test of a file with 500 tempo changes, checking the last event's tick against the exact sum.

**MIDI-115. Meta events.** The server MUST use tempo meta events (MIDI-114) and end-of-track (`FF 2F 00`, whose time is the track's end, MIDI-120) and MUST drop every other meta event without error; none is carried into a block (MIDI-8).
- Reason: Time signature, key signature, names, markers and the rest describe a file; a sound has its own label.
- Source: MIDI-8; `midi-file.ts`; Standard MIDI Files 1.0, printed pages 7 to 10 (PDF 136 to 139): a meta event is `FF <type> <length> <bytes>`, its type "always less than 128", its length a variable-length quantity, and "programs must properly ignore meta-events which they do not recognize"; end of track is `FF 2F 00`.
- Verification: A server test with one meta event of each type 0x00 to 0x7F.

**MIDI-116. Channels.** The server MUST keep each message's channel as the file gives it, unless the program gives a channel map: for each of the 16 channels of the file, a channel of the sound or none (the channel's messages dropped). For synth7 a file's channel is then a part.
- Reason: Most files already use channels as parts; a map lets a program fold a file's channels onto a synthesizer that has fewer parts.
- Source: MIDI-67.
- Verification: A server test of a map that moves channel 10 to channel 1 and drops channel 2.

**MIDI-117. System exclusive in a file.** The server MUST join a system exclusive message split across a track's `F0` event and later `F7` continuation events into one message (Standard MIDI Files 1.0, printed pages 6 and 7, PDF 135 and 136: an `F0` event whose last byte is not `F7` begins a message continued in `F7` events until one ends with `F7`, and "an F7 sysex event ... encountered without a preceding F0 sysex event" is an escape), at the time of its first part, bounded at 16,384 bytes; MUST drop `F7` escape events that are not continuations; and MUST then treat the message as a timed event (MIDI-28), lift it into a bank (MIDI-58), or refuse it.
- Reason: Files carry long dumps in continuation packets; blocks never do (MIDI-50).
- Source: `midi-file.ts` (`SYSEX_CONTINUED`); MIDI-50, MIDI-58.
- Verification: A server test of a DX7 32-voice dump split into five packets at a file's start, lifted into a bank.

**MIDI-118. What a file holds that the synthesizer does not take.** The server MUST drop every message of a file that the family document does not list (MIDI-10), and every system common and real-time message (which a file can hold only inside an `F7` escape event, Standard MIDI Files 1.0, printed page 6, PDF 135), and MUST report to the program, in its answer, how many of each kind it dropped; it MUST NOT refuse a file for them.
- Reason: Files are made for many instruments; refusing every file with one foreign controller would refuse nearly all. The report tells the author what was not played, as the kit reports today.
- Source: `midi-file.ts` (`MidiDropped`).
- Verification: A server test with one message of each kind a synthD sound does not take, checking the report.

**MIDI-119. A file's bounds.** The server MUST refuse a file of more than 1,048,576 bytes, of more than 1,024 tracks, of more than 100,000 events (meta events and dropped messages counted), with a chunk or event whose stated length passes the file's end, with a variable-length quantity of more than four bytes, or with a data byte that follows no status; and MUST believe no length past the bytes it has.
- Reason: A file is untrusted; these are the kit's bounds as built, with a bound on tracks added.
- Source: `midi-file.ts` (`MOST_MIDI_FILE_BYTES`, `MOST_MIDI_EVENTS`); DEVELOPMENT.md section 14.
- Verification: A server test for each bound; a fuzz target of the reader (MIDI-124).

**MIDI-120. A file's length.** The sound's length MUST be the later of the last event's time and the last end-of-track's time, plus the tail the program gives (MIDI-19), and MUST then meet MIDI-104.
- Reason: A file's end-of-track marks where it ends, which may be after its last note; the tail lets notes ring.
- Source: Standard MIDI Files 1.0, printed page 8 (PDF 137: "An end-of-track event must occur as the last event in the track") and printed page 9 (PDF 138: end of track "is included so that an exact ending point may be specified for the track"); MIDI-19.
- Verification: A server test of a file whose end-of-track is 2 seconds after its last note.

---

## 16. Limits and security

Everything a receiver reads and everything the server reads from a program is untrusted (DEVELOPMENT.md sections 6 and 14). Every bound below is a named constant, defined once, in the engine (the receiver's) or the server (the program's), with an assertion where two must agree.

**MIDI-121. The receiver's bounds.** The receiver MUST enforce every bound of this table on every record, block and bank image, whoever sent it:

| Bound | Value | Requirement |
|---|---|---|
| Bytes of a record | 1,024 | `profile.rs` |
| Bytes of a block | 0 to 1,005 | MIDI-30 |
| Events a block | 256 (a family may set fewer) | MIDI-31 |
| Ticks of a block; an event's time | 200; 0 to 199 | MIDI-25 |
| Bytes of a variable-length quantity in a block | 2 | MIDI-24 |
| Bytes of a system exclusive event after `0xF0` | 1 to 256 | MIDI-28 |
| Blocks of a stored sound | 1 to 6,000 | MIDI-40 |
| Total bytes of a stored sound's blocks | 960,000 | MIDI-41 |
| Blocks of a live ring; lookahead; stall | 32; 3; 2,000 ms | MIDI-101 |
| Bytes of a bank image | 1 to 16,384 | MIDI-55 |
| Patches a bank | 1 to 128 | MIDI-56 |
| Banks a sound names | 1 to 10 | MIDI-57 |
| Blocks rendered a call | 50 | MIDI-106 |

- Reason: Bounded memory and bounded work per call, whatever arrives.
- Source: The requirements named.
- Verification: A test for each bound at its value and one past it.

**MIDI-122. The server's bounds on a program's input.** The server MUST enforce, besides MIDI-121 on everything it writes: the longest line, 16 MiB (`protocol.rs`, `LONGEST_LINE`); at most 100,000 timed events in one stored sound's message; at most 25,600 timed events (100 blocks of 256) and an advance of at most 100 blocks in one live events message (MIDI-20); at most 128 patches a bank; at most 16,384 bytes of a patch or bank given as bytes; and section 15's bounds on a file. Its work on one message MUST be proportional to the message's bytes.
- Reason: DEC-6462 ("What it changes"): the server's new work on a program's input "must be limited and fuzzed as all input from outside is".
- Source: DEC-6462; `protocol.rs`.
- Verification: A server test at each bound; a timed test of the largest message.

**MIDI-123. The receiver trusts no sender.** The receiver MUST make every check of this document and of the family documents itself, whatever the server checked, and MUST NOT panic, allocate or loop without bound on any input; each fault it meets MUST be counted where the port can read it (blocks malformed, events passed over, patches refused, unsupported objects).
- Reason: A receiver may meet records from any sender: a server of another version, a recording, an attacker on a network path.
- Source: DEVELOPMENT.md section 14; the engine's crate root's denied lints (`lib.rs`).
- Verification: The fuzz targets of MIDI-124; inspection of the crate's lints.

**MIDI-124. Fuzz targets.** There MUST be fuzz targets, each with its corpus of every input that ever found a fault, for: the receiver's block reader with each family's synthesizer behind it; the store's DATA reader for event codecs; each family's bank reader; the server's events-message reader; and the server's Standard MIDI File reader.
- Reason: DEVELOPMENT.md section 8: every reader of outside input has a fuzz target.
- Source: DEVELOPMENT.md sections 8 and 14.
- Verification: The full gate runs them.

---

## 17. The eleven synthesizers

**MIDI-125. The synthesizers' table.** Each family document MUST confirm or correct its rows of this table, and the table MUST be kept true as they are approved. Every cell gives its source; a cell marked **unverified** could not be confirmed from a filed document or the engine's code, and says why. The family documents confirmed or corrected their rows on 18 November 2026, and no cell is now unverified.

| Synthesizer | Adopted interface | Playing messages the interface recognises | Parameter control | Patch form | Patch size | Bank | Polyphony | MIDI channel use |
|---|---|---|---|---|---|---|---|---|
| synth6581 | ASID (`thomasj-asid-protocol.md`) | None: system exclusive only (S6581-26) | ASID register data, `F0 2D 4E … F7` (S6581-10) | Full register update (S6581-50) | 37 bytes (S6581-50) | None (S6581-51) | 3 voices (`synthesizers.md`) | None: ASID carries no channel (S6581-4) |
| synth8580 | As synth6581 | As synth6581 | As synth6581 | As synth6581 | 37 bytes | None | 3 voices | None |
| synth7 | DX7 MIDI and system exclusive (DX7 manual pp. 30 to 32) | Note off, note on (velocity used), pitch bend (low byte ignored), program change 0 to 63, controllers 1, 2, 4, 5, 6, 7, 64, 65, 96, 97, 125, 126, 127 ("all key off"; the values of 125 and 127 ignored) (p. 32). Channel pressure: transmitted (p. 30), not in the DX7's reception list (p. 32); the TX7, of the same voice format, receives it (TX7 manual, printed pages 32 and 34); synth7 takes it (`synth7.md`, S7-22, its open question 5) | System exclusive parameter change, 7 bytes, group 0 voice parameters 0 to 155, group 2 function parameters 64 to 77 (pp. 30 and 31) | Single-voice bulk dump | 163 bytes (155 data bytes, p. 30) | One 32-voice bulk dump, 32 patches, 4,104 bytes (p. 30); two banks reach programs 0 to 63 (p. 32; `synth7.md`, S7-50) | 16 notes poly, 1 mono (p. 27); 16 shared by 16 parts as built (`rack.rs`, `NOTES`) | The DX7 receives on one channel (p. 32); synth7 has 16 parts, one a channel, as built (DEC-6410 item 10) |
| synth106 | Juno-106 MIDI and system exclusive (Juno-106 manual PDF 34 and 35); JU-06A control changes | Note on and off (velocity ignored), controller 1 (LFO modulation, "0 or 127" in the chart), 64 (hold), 123 to 127 (all notes off), program change 0 to 127, pitch bend (low six bits ignored) (PDF 34 and 35) | System exclusive parameter change `F0 41 32 0n pp vv F7`, parameters 0 to 17 (PDF 35); of the JU-06A's 39 recognised controllers (1, 3, 5, 9, 11 to 30, 64, 65, 71 to 75, 82, 83, 86 to 89, 91, 93), the 25 that move a patch field and 1, 64 and 87 (`synth106-synth60.md`, S106-25); controller 7 and RPN 0 from the common layer (MIDI-9, MIDI-90) | Patch message `F0 41 30 0n`, program, 18 values, `F7` | 24 bytes (PDF 35) | 1 to 128 patch messages, 3,072 bytes at most; groups A and B, programs 0 to 127 (PDF 35) | 6 voices (p. 32; `synth106/mod.rs`, `VOICES`) | One basic channel, 1 to 16 (PDF 34); synth106 hears all 16 as one keyboard, as built |
| synth60 | As synth106; the JU-06A's controllers 15 (DCO LFO, MAN, ENV), 28 (sub on and off) and 93 (chorus off, I, II, I+II) for the Juno-60's own switches (DEC-6454) | As synth106 | As synth106 | The Juno-106's patch message followed by the JU-06A's controllers 15, 28 and 93 at canonical values (`synth106-synth60.md`, S106-31) | 33 bytes (21 values; S106-31) | 1 to 128 patches of 33 bytes, 4,224 bytes at most (S106-38, S106-39) | 6 voices (`synth106-synth60.md`, S106-34; Juno-60 service notes) | As synth106 |
| synthD | Voyager MIDI, version 3.4 (`synthd.md`, sections 4 and 6) | Note on and off (velocity ignored), pitch bend, the modulation wheel (1 and 33), volume (7), all notes off, program change 0 to 127 (`synthd.md`, SD-1); controllers 64, 120, 121 and 123 to 127 of the common layer (`synthd.md`, SD-13) | Control changes: 46 of the Voyager's map for the controls the two panels share, its controllers for controls synthD lacks ignored; 14 of NeoTeletext's own (`synthd.md`, SD-17); pitch bend range by RPN 0 (`synthd.md`, SD-6, MIDI-90) | 60 control values (`synthd.md`, SD-22) | 60 bytes | 1 to 128 patches, 7,680 bytes at most (`synthd.md`, SD-27) | 1 voice, lowest key (`synthd.md`, SD-14) | All 16 channels one keyboard (`synthd.md`, SD-2) |
| synth53 | Prophet-5/10 MIDI implementation 1.4 | Note off, note on, polyphonic key pressure, channel pressure, pitch bend, program change 0 to 39, controllers 1, 4, 32 (bank select), 64, 74 (brightness), 121, 123 (pp. 2 and 3) | Control changes (pp. 4 and 5) and NRPN 0 to 94 and 4,096 to 4,109 (pp. 8 and 9) (the program's parameters are 0 to 64, 86 and 87; 4,096 to 4,109 are global settings left out, S53-27), by controllers 99, 98, 6, 38, 96, 97; RPN 127, 127 resets the selection (p. 7) | Program edit buffer dump, 152 packed bytes (p. 12) | 157 bytes; 159 as a program dump (p. 12) | 40 programs a group, 6,360 bytes as program dumps; groups 0 to 9 (p. 12); one bank a group, 1 to 10 banks a sound (`synth53-synth52-synth51.md`, S53-26); bank select values 1 to 9 (p. 2), read as values 1 to 10 choosing groups 0 to 9 and value 0 choosing group 0 (S53-13) | 5 voices (guide p. 1; `synth53/mod.rs`, `VOICES`) | One channel 1 to 16, or All (p. 1); synth53 hears all 16, as built |
| synth52 | As synth53 | As synth53 | As synth53 | As synth53 | As synth53 | As synth53 | 5 voices | As synth53 |
| synth51 | As synth53 | As synth53 | As synth53 | As synth53 | As synth53 | As synth53 | 5 voices | As synth53 |
| synth8 | JUPITER-08 MIDI implementation chart 1.01 | Note on (velocity recognised; synth8 ignores it) and off, polyphonic key pressure (synth8 ignores it), pitch bend, 50 control changes, nine of them recognised only (1, 7, 10, 11, 41, 64, 91, 92, 118); mode 3; **no system exclusive, and program change selects a step-sequencer pattern** (the System chart) | Control changes: all 41 the chart marks transmitted, 40 of them patch bytes and 63 moving VCO-2 RANGE as 62 does, plus NeoTeletext's own 107 and 108 (`synth8.md`, S8-16) | 42 control values in `synth8.md`'s order (NeoTeletext's own) | 42 bytes (`synth8.md`, S8-23) | NeoTeletext's own: one bank of 1 to 64 patches, 2,688 bytes at most; program change 0 to 63 on channels 1 and 2 (`synth8.md`, S8-12, S8-29); the JUPITER-08's program change chooses a pattern, not a patch, and its charts state no bank | 8 voices, whole; 4 a half in dual and split (owner's manual, printed pages 3 and 11; `synth8/assign.rs`, `VOICES`) | Basic channel 1 to 16 (chart); synth8: notes on all 16, upper half on channel 1 and lower on channel 2 (`synth8.md`, S8-2) |
| synth80 | Deckard's Dream MIDI specifications, manual 1.3.0 | Note on and off; channel pressure, polyphonic aftertouch or MPE by a global setting (PDF 45 and 46); program change and bank select by controller 0, values 0 to 2 (PDF 18); controllers 1, 5, 7, 64; pitch bend, its range a global setting of 1 to 99 semitones, default 3 (PDF 60), polyphonic pitch bend in MPE (PDF 15) | Control changes: 75 panel controllers (PDF 71 to 74), of which 93 and 94, coarse and fine pitch, are taken as performance controllers outside the patch (`synth80.md`, S80-47; DEC-6465, awaiting the owner's confirmation); controller 120 is glide mode there, moved to controller 3 (`synth80.md`, S80-20; MIDI-86); 12 controllers of NeoTeletext's own, 20 to 31 (S80-18); pitch bend range by RPN 0 (S80-7, MIDI-90) | Control values in `synth80.md`'s order (NeoTeletext's own) | 85 bytes (S80-33) | 128 patches a bank, three banks (PDF 16 to 18); a bank image of 1 to 128 patches, 10,880 bytes at most (S80-41) | 8 voices, or 4 with two cards a voice (PDF 50 and 51; `synth80/mod.rs`, `VOICES` = 8) | One channel 1 to 16; in MPE mode a master channel 1 to 8 and the voices on 9 to 16 (PDF 46); synth80 hears all 16 as one keyboard, as built |

- Reason: The brief asks for one table of the eleven, filled from the filed documents and the code, with every unverified cell marked.
- Source: The cells' sources.
- Verification: Review against each family document on its approval.

---

## 18. What is left out

Of MIDI 1.0 and the Standard MIDI Files format, as a whole (each family document lists what it leaves out of its own interface):

| Left out | Reason | Requirement |
|---|---|---|
| Timing clock, start, continue, stop | No sequencer or arpeggiator; time is the blocks' ticks | MIDI-8 |
| Active sensing, and the DX7's sound turned off when it stops | The profile's stall rule does the job | MIDI-8 |
| System reset | A sound is reset by starting; stop ends it | MIDI-8 |
| Time code, song position, song select, tune request | No song memory; in tune by construction | MIDI-8 |
| Local control (122) | No keyboard of the synthesizer's own | MIDI-8 |
| Basic channel, omni and mono or poly switching by mode messages | The channel map is the family's; mode messages are all notes off | MIDI-71, MIDI-89 |
| Meta events in blocks; tempo in blocks | A block's time is in ticks | MIDI-8, MIDI-115 |
| Running status in blocks | Each block must be read alone | MIDI-12 |
| Standard MIDI Files continuation and escape events in blocks | A lost block would leave part of a message | MIDI-50 |
| Standard MIDI Files format 2 and SMPTE division | Not one piece of music; rare; as built | MIDI-113 |
| System exclusive longer than 256 bytes in a block | Only bank dumps are longer; they travel as banks | MIDI-28, MIDI-51 |
| Device inquiry, dump requests, global parameter dumps, firmware transfer | Hardware; a synthesizer transmits nothing | Each family document |
| Everything an instrument transmits | NeoTeletext's synthesizers only receive | Each family document |

---

## 19. What NeoTeletext defines itself

Each item exists because neither MIDI 1.0, Standard MIDI Files 1.0 nor an adopted interface defines it.

1. **The block as 200 ticks of 0.1 millisecond in an event list, with its bounds** (MIDI-23 to MIDI-31): decision A3 sets the form; the bounds (1,005 bytes, 256 events, 256-byte system exclusive, two-byte quantities) are this document's, for a receiver of fixed memory.
2. **The DATA layout of the event codecs and extension tag 8** (MIDI-41, MIDI-42): the audio profile's own records, extended for blocks of varying length.
3. **The bank codec, the bank image and a sound's list of up to 10 banks** (MIDI-55 to MIDI-57): the interfaces define dumps, not how a broadcast carries them.
4. **Lifting bank dumps out of music** (MIDI-58).
5. **The restatement and its interval** (MIDI-93 to MIDI-99): a broadcast's need, which no cable-era interface has.
6. **The common layer's additions to interfaces that lack them**: controllers 7, 64, 120, 121 and 123 and the mode messages wherever an interface does not list them (MIDI-9); RPN 0 for pitch bend range in every family (MIDI-90), which no filed interface documents.
7. **One rule for each common behaviour where interfaces differ** (MIDI-84 to MIDI-92), at the owner's requirement (DEC-6464).
8. **The volume law** (MIDI-82), as built.
9. **The rules for control maps NeoTeletext defines** (MIDI-78), for families whose interface has none.
10. **The default patch before any program change** (MIDI-61) and **the default for a faulty patch** (MIDI-63), as built.
11. **The program's interface to the server**: time in microseconds, named parameters, `until` for live sounds (MIDI-16 to MIDI-20), under DEC-6462.
12. **The new codec numbers** (MIDI-107), if open question 1 is answered as recommended, as DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation).
13. **Bare system common and real-time messages passed over in a block** (MIDI-23): Standard MIDI Files 1.0 has no such track event and carries these messages only inside an `F7` escape (printed page 6, PDF 135); the reader passes them over by MIDI 1.0's lengths so that a block that is not the server's is not lost whole. The server never writes one.
14. **Reception without a basic channel or an Omni state** (MIDI-84, MIDI-85, MIDI-89): MIDI 1.0 recognises the mode messages only on the basic channel (printed page 20, PDF 52) and has a receiver in Omni On ignore all notes off and reset all controllers (printed page 25, PDF 57). NeoTeletext's synthesizers have no basic channel and no Omni state that a message sets; a one-part family hears all 16 channels as an instrument in Omni On would (MIDI-68), yet acts on controllers 121, 123 and 124 to 127 on every channel that addresses a part. MIDI 1.0's reason for ignoring them in Omni On, that an all notes off sent with one sequencer track would cut the sustained notes of another track on another channel (printed page 25, PDF 57), does not arise in the same way: the server builds every block itself (MIDI-13) and merges a file's tracks (section 15), so it knows which parts every such message reaches before it writes one; and a program must be able to reset and silence every synthesizer by the same message, which is the purpose of the common layer (MIDI-9).
15. **The step of increment and decrement for pitch bend sensitivity** (MIDI-90): one cent, since MIDI 1.0 4.2 states none.

---

## 20. Open questions for the owner

**1. Codec numbers: new codes 12 to 19, or keep 3 to 11?**
DEC-6461 item 3 says "the codec numbers and the bytes of the records do not change" for the rename; decisions A3 and A4, taken after it, change every synthesizer's block and patch.
- *Option A: new codes 12 to 19, 3 to 11 retired* (MIDI-107 to MIDI-109). A browser of today ignores the new sounds and stays silent; nothing old is misread. Amends DEC-6461 item 3.
- *Option B: keep 3 to 11 with the new contents.* No new numbers; a browser of today reads event lists as four-byte slots and plays wrong notes or noise until it is updated.
- *Recommendation:* A. The requirements are written for it; under B only MIDI-107 to MIDI-109's numbers change.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, new codes 12 to 19, codes 3 to 11 retired; it amends DEC-6461 item 3's statement that the codec numbers do not change. MIDI-107 to MIDI-109 stand as written.

**2. How often to restate, and whether a stored sound's start restatement is the server's or the program's.**
- *Option A* (written): the server restates within every 50 blocks, aiming at 25, and writes block 0's restatement itself, while a family document may require the program to (as synth6581's does).
- *Option B:* 25 blocks as a hard bound: half a second of wrong timbre at most for a joiner, twice the bytes.
- *Recommendation:* A, matching DEC-6410 item 12 and the synth6581 document.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written.

**3. Several banks for one sound.**
- *Option A* (written): 1 to 10 banks a sound, chosen by bank select or by program range as each interface does.
- *Option B:* one bank a sound, at most 128 patches: simpler, but DX7 programs 32 to 63, the Prophet-5's groups and Deckard's Dream's banks cannot all be reached as the interfaces reach them.
- *Recommendation:* A.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written; for synth7, a second 32-voice dump as its cartridge bank reached by program changes 32 to 63 (`synth7.md`, S7-50).

**4. A restatement made for a viewer who joins.**
The server could send a connection that joins a live sound one extra event list at once with every part's restatement, instead of waiting up to a second; but a block number has one content for every receiver (MIDI-44), so this needs a new record or a block numbered apart.
- *Option A* (written): no; the periodic restatement alone, which also serves teletext lines where nothing is per-viewer.
- *Option B:* design a join restatement in a later version.
- *Recommendation:* A now; B only if the second is heard as a fault.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written; reconsidered only if the second of wrong timbre is heard as a fault.

**5. Pitch bend range by RPN 0 in every family** (MIDI-90).
The owner asked for one rule for common behaviours. No filed interface documents RPN 0; three have no range message at all, and synthD's document is written for option A, stating option B's fixed range of 797 cents.
- *Option A* (written): RPN 0 in every family beside each interface's own message.
- *Option B:* each family's own message only; synthD, the Juno-106 and Deckard's Dream keep fixed ranges.
- *Recommendation:* A: it is MIDI's standard way and the only one that can be the same everywhere. A related question for the synth53 family, whose interface stores the range in each program while MIDI-90 says a program change does not change it, is `synth53-synth52-synth51.md`'s open question 5. `synthd.md`, SD-6, follows option A pending the answer.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written. The related question of the synth53 family (`synth53-synth52-synth51.md`, open question 5) was answered with its option A, the rule of MIDI-90, against that document's recommendation, because the owner requires one behaviour for all synthesizers in what MIDI defines in common; MIDI-90 therefore gains no exception.

**6. Pitch bend at full resolution everywhere** (MIDI-91).
- *Option A* (written): all 14 bits in every family, the DX7's and Juno-106's coarser bends listed as departures.
- *Option B:* each instrument's own resolution, as its interface states.
- *Recommendation:* A, under the owner's rule of one behaviour.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written.

**7. The documents to obtain.**
MIDI 1.0, Standard MIDI Files 1.0 and RP-015 were not filed when this document was written; every statement resting on them was marked "to be checked". *Recommendation:* the owner or the main session fetches and files them before any requirement marked so is built.
- Not answered by DEC-6465: left with the owner (TODO-6466).
- Answered by the filing of 18 November 2026 (TODO-6466, done): the MIDI 1.0 Detailed Specification 4.2, Standard MIDI Files 1.0 and the General MIDI Level 1 Developer Guidelines, in the 96.1 bundle (SRC-6469); RP-015 (SRC-6468); and MIDI Polyphonic Expression 1.0 with its configuration message (SRC-6470), all in `~/devel/teletext-reference/midi/` (section 1.5). DEC-6464 version 2 quotes RP-015. Every statement of this document and of the family documents that was marked "to be checked" was read against them and confirmed with its citation or corrected; the corrections to this document are in MIDI-12 (MIDI 1.0's rules for expanding running status), MIDI-23 (the bare system common and real-time messages are not Standard MIDI File events), MIDI-38 (the set tempo and end-of-track meta events a track needs), MIDI-76 (the null parameter number for non-registered parameters too, and for increment and decrement), MIDI-84 (RP-015's lists as written, the reception rule and the list each family document owes), MIDI-85 and MIDI-89 (their reception), MIDI-90 (increment and decrement of registered parameter 0) and MIDI-113 (a header longer than 6 bytes).

---

## 21. Differences from what is built today

What exists is described in `synthesizer-wire-format.html`, `programming-the-synthesizers.html` and the code named in section 1.4.

**Blocks and records.**
1. A synthesizer block is today 1 to 16 four-byte slots (time, status, two data bytes; all zeros empty), a fixed number for every block of a sound, or for the synth6581 family 1, 2 or 4 register images of 25 bytes. It becomes an event list of 0 to 1,005 bytes (MIDI-23 to MIDI-31). `SYNTH7_SLOT_BYTES`, `SYNTH7_MAX_SLOTS`, `SYNTH7_SLOT_LAST_TIME`, `SYNTH6581_IMAGE_BYTES` as a block unit, and `render_slots`, `slot` and `render_synth6581` in `receiver/instruments.rs` are replaced by one event-list reader.
2. The OBJECT's block bytes field becomes the longest block; tag 8 is added (MIDI-40, MIDI-41).
3. DATA records of the event codecs gain a 4-byte byte offset and a 2-byte length before each block (MIDI-42). `record.rs`, `store.rs` (`Entry`, `put`, `record_blocks`, `block`, `block_length`), `store/arena.rs` (`size`) and `store/live.rs` change; the store gains an offset table for stored event sounds (MIDI-45) and a length in each ring slot (MIDI-46). `encode.rs` (`instrument`, `of_blocks`, `packet_records`, `data_records`) changes to write them.
4. A DATA record today holds `floor(1,011 ÷ block bytes)` blocks; it will hold as many varying blocks as fit (MIDI-47).

**Codecs.**
5. Codes 3 to 11 are retired and 12 to 19 take their place (MIDI-107, open question 1); `Codec` in `codec.rs`, `from_code`, `code`, `is_slots`, `allows_block`, `samples_per_block`, `patch_bytes`, `models`, `bank_codec`, `is_family_code` and the per-family patch sizes all change.
6. The two bank codecs (5, a DX7 bank of 128-byte packed voices; 11, an analogue bank of NeoTeletext's own patch layouts of 18, 36, 24, 43 or 85 bytes) become one bank codec of bank images (MIDI-55, MIDI-56). The 18-, 36-, 24-, 43- and 85-byte layouts are replaced by each interface's own form (MIDI-54).
7. Tag 4 carries 1 to 10 handles where it carries one (MIDI-57); tag 5's values for the synth53 family become three (MIDI-48).

**Messages.**
8. Today every slot codec takes one shared set: note off and on, pitch bend, controllers 1, 7, 64, 120, 121 and 123, program change 0 to 31 with a second data byte of 0; the Juno also 124 to 127, the Jupiter-8 also 5, 8 and 65, the CS-80 also key and channel pressure. Each family will take its interface's set (MIDI-10) plus the common layer (MIDI-9), with one behaviour for each common message (MIDI-84 to MIDI-92). Program changes reach 0 to 127 and banks hold up to 128 patches.
9. Today system exclusive cannot be expressed; it becomes an event (MIDI-27).
10. Reset all controllers today resets what each instrument chose; it becomes RP-015's list in every family (MIDI-84). The sustain threshold, the mode messages, all sound off's fade, pitch bend's resolution and range by RPN 0, and controller 7's law become one rule each (MIDI-85 to MIDI-92).
11. A faulty patch today becomes the default silently; it will be counted, and the server will refuse it with the receiver's own check (MIDI-63). The known gap "DX7 bank checks" (`synthesizer-wire-format.html`, section 12) closes.
12. After a lost block today the instruments release their notes; they will also clear every NRPN selection (MIDI-102).

**The server and the kits.**
13. Today a program sends blocks and banks as base64 bytes it has built with the kit, with `slots`, `images_per_block` and `first` fields. It will send patches, banks, timed events or a Standard MIDI File as typed JSON, and the server builds everything (MIDI-13 to MIDI-22); the program protocol becomes version 13 (MIDI-111).
14. The kit's sound logic (about 4,300 lines: `synth-score.ts`, `synth7-score.ts`, `slot-score.ts`, `program-repeater.ts`, `midi-file.ts`, `midi-bytes.ts`, the `*-patch.ts` packers, `synth-patch-rules.ts`, `synth7-sysex.ts` and others) moves into the server or is removed; the program repeater becomes the server's restatement (MIDI-93 to MIDI-99), restating every parameter and not only program changes.
15. The server today checks blocks with the engine's code but checks some things less than the receiver; it will check everything with the receiver's functions (MIDI-21).

**Documents and tests.**
16. The tests that build slots or patches (`tests/synths.rs`, the instruments' tests, the server's and the kit's) change to event lists and the interfaces' patch forms; each requirement's verification names the new tests.
17. `synthesizer-wire-format.html` and `programming-the-synthesizers.html` describe the old format and are regenerated; the protocol's documentation items for the codecs (TODO-6450) are written from this document.
