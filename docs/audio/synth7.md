# synth7: the programming interface

**Purpose.** This document specifies how synth7 is played and programmed: every MIDI message it takes and what each does, what a synth7 voice is, byte by byte and parameter by parameter, the three system exclusive messages that carry voices and parameters, the function parameters, and how sixteen MIDI channels become sixteen parts. It is the basis for implementing synth7's part of the synthesizer protocols.

**Scope.** synth7 only: the six-operator FM synthesizer that models the Yamaha DX7 (`neoteletext-common/docs/audio/synthesizers.md` says once which instrument each synthesizer models). This document says what the interface is. How a program sends it to the server, and the server's typed form of it, belong to the Rust server's document (DEC-6462); the transport (blocks, records, packets), the form of a block, how a bank of voices is stored and named by a sound, how a system exclusive message longer than one block travels, the restatement a live sound carries, and the behaviours common to every synthesizer belong to the MIDI architecture document (`midi-architecture.md`), which governs this one. This document states what synth7 needs of them and refers to them by requirement. The sound of the instrument (its operators, envelopes and tables) is not specified here.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

**What the owner must read first.** Five facts about the filed sources shape this document.

1. **The maker's full data format is filed, in two manuals of the same voice format.** Besides the DX7's own manual, two manuals of the instrument maker are filed: the TX7's (the DX7's tone-generator module, which uses the DX7's voice format) and the DX7 II FD/D's (whose voice format keeps the DX7's). The TX7 manual's "System Exclusive Data Format" (printed pages 35 to 44) gives the single-voice and 32-voice dumps, the parameter change, the voice parameters 0 to 156 with notes that state how each coded value is read, the function parameters 64 to 77, that the single-voice dump's 155 bytes are parameters 0 to 154 in order (printed page 41, section 4-5), and every byte and bit field of the 128-byte packed voice (printed page 44, section 4-8). The DX7 II manual draws the same packed voice (printed page Add-11, section 5-4) and lists the same voice parameters with the maker's initial values (printed page Add-8, section 5-1). Section 10's layout was checked byte by byte and bit by bit against the TX7 manual's page 44 and agrees with it in every field.
2. **The file `dave-benson-dx7-E-midispec.txt` is not a source for the adopted interface.** It is the MIDI implementation of "GREY MATTER RESPONSE E! FOR THE DX7", a third-party replacement firmware for the DX7, posted on 13 January 1998. It describes that firmware's own messages and system exclusive formats and says of the maker's formats only that they "are well documented by YAMAHA, and therefore will not be explained here". Nothing in this document rests on it. `dx7/documents.tsv` now describes it so.
3. **Every fact this document had to infer from the DX7 manual alone is now stated by a maker's document**: the order of the single-voice dump's data (S7-38), the meaning of the parameter change's two high bits (S7-43), the coding of the scaling curves, the break point, the oscillator mode, the fixed-frequency steps, the detune and the transpose (S7-31), and the bit order of the assign parameters (S7-34). What remains NeoTeletext's own is listed in section 15.
4. **The three pages of the DX7 manual's data format are a re-set copy with additions.** Printed pages 30, 31 and 32 of the filed DX7 manual are not a scan like the rest of the manual: they are set again in another type, and several phrases on them are printed in blue, for example "(add 155th byte and make the 2's complement)", "(transmited when it is unavailable)", "(LS 4 bit are ignored.)", "(v : ignored)", "ignored" against controllers 125 and 127, the explanations of active sensing, and the whole of the paragraphs under "2-2-2" to "2-2-5". Who added them is not stated in the source. They are the only filed statement of some of those facts, so this document cites them, saying "blue text" wherever a fact rests on one.
5. **The DX7 manual contradicts itself in one place, and the other manuals settle it; its operator switch is held reversed in today's code.** The DX7 manual's parameter table gives "LFO WAVE 0 ~ 4" (printed page 31), while its printed pages 13 and 27 list six waveforms; the TX7 manual (printed pages 38 and 39) and the DX7 II manual (printed page Add-8) give 0 to 5, so 0 to 4 is a misprint (S7-31). All three manuals put operator 1 in bit 5 and operator 6 in bit 0 of parameter 155, where today's code holds the operators the other way round (S7-30).

**The behaviours common to every synthesizer.** Where MIDI defines a behaviour common to all instruments (reset all controllers, all notes off, all sound off, the sustain pedal, a note on of velocity 0, the mode messages, the pitch bend range and resolution, and volume), synth7 follows the one rule of `midi-architecture.md` section 11.1 (MIDI-84 to MIDI-92), and this document lists each place where the adopted interface departs from that rule as a departure (section 14.2).

---

## 1. Sources

All files are under `~/devel/synthesizer-reference/dx7/`. Page numbers are printed page numbers. In the DX7 manual ("the manual"), printed page n is PDF page n + 1 (the cover is PDF page 1); in the TX7 manual, printed page n is PDF page n + 1 (printed page 44 is PDF page 45); the DX7 II manual's appendix pages are numbered Add-1 onwards (Add-8 is PDF page 102, Add-11 is PDF page 105). Where this document says "the manual" without a name, it means the DX7 manual.

| Short name here | File | What it is used for |
|---|---|---|
| **The manual** | `manuals/yamaha-dx7-owners-manual-DX7E1.pdf` (34 PDF pages; "DX7 Digital Programmable Algorithm Synthesizer Operating Manual", Yamaha, Nippon Gakki Co., Ltd., back cover "OMD-71 86100.5"; SHA-256 a3bb18bafbb6d2ec03268b814ac495bb5dfdabbda53b52a46f510ebbc2ed9a42) | The adopted interface. "MIDI" (pages 21 and 22): what MIDI carries, the receiving channel, system information and memory protect. "MIDI DATA FORMAT" (pages 30 to 32): every message transmitted and received, the voice parameters 0 to 155 and the function parameters 64 to 77. "FUNCTION MODE" (pages 6 to 8): the meaning of every function parameter. "EDIT MODE" (pages 12 to 17): the meaning and range of every voice parameter. "KEY TRANSPOSE" (page 18). "STORE/SAVE/LOAD" (pages 19 and 20): memory protect. "LFO BLOCKDIAGRAM" (page 26): how the controllers reach the modulation. "SPECIFICATIONS" (page 27): ranges and polyphony. "VOICE DATA LIST" (pages 28 and 29): the parameters as the maker groups them. All 34 pages were read. |
| **The TX7 manual** | `manuals/yamaha-tx7-owners-manual.pdf` (48 PDF pages; "TX7 FM Tone Generator" owner's manual, Yamaha; a scan without a text layer; SHA-256 63011cff4b5150aeb0e27716173922408149c4de33791df7d45196aa73952a3e) | The maker's statement of the voice format the DX7 uses. "MIDI DATA FORMAT" (printed pages 32 to 44): reception conditions and data (pages 32 to 34; it receives after touch, page 32 and section 2-2-5 on page 34), the single-voice dump and the 32-voice dump with their headers and byte counts (pages 35 and 36, section 2-5-1; "The 155 bytes of voice data go into the Edit buffer, replacing any existing data there", page 35), the parameter change with its sub-group bits (page 36, section 2-5-2), the voice parameters 0 to 156 (page 38, section 4-1) and their notes *1 to *8 (page 39: the break point's keys, the scaling curves, the oscillator mode, the frequency coarse and fine, the detune, the LFO waves 0 to 5, the operator on/off bits, the operator select), the effect assign bits (page 40, section 4-2, note *2), the function parameters 64 to 77 (page 41, section 4-3), the order of the single-voice dump's data (page 41, section 4-5), and the 128-byte packed voice (page 44, section 4-8). Pages 32 to 41 and 44 were read. |
| **The DX7 II manual** | `manuals/yamaha-dx7ii-fd-d-owners-manual.pdf` (111 PDF pages; DX7 II FD/D owner's manual, Yamaha; a scan without a text layer; SHA-256 7ea6771f0a3c984173390561de5b86375181ae9cb1df6c7a175bdf8a24eb5ca6) | A second statement of the same voice format, for checking the TX7 manual. Printed page Add-8 (PDF 102), section 5-1: the voice parameters 0 to 156 with their ranges, LFO wave 0 to 5, "OPERATOR ENABLE B5:OP1,..,B0:OP6", and the maker's initial voice ("INIT VOICE") value by value. Printed page Add-11 (PDF 105), section 5-4: the 128-byte packed voice ("VMEM format"), the same layout as the TX7 manual's page 44 (its "OSC.PHASE INIT" is the DX7's oscillator sync). Those two pages were read. |
| **The Grey Matter text** | `manuals/dave-benson-dx7-E-midispec.txt` (553 lines; SHA-256 0cd8ccd34cc82be72f3888a20b397b2699ee1295ab8d81d673796f682090669d) | What it is: the MIDI implementation of a third-party replacement firmware for the DX7 ("GREY MATTER RESPONSE E! FOR THE DX7"), not the maker's data format. Nothing in this document rests on it (section 14.3). |
| **synth7's source** | `~/devel/neoteletext-renderer-teletext/crates/neoteletext-audio-instruments/src/synth7/` (`mod.rs`, `patch.rs`, `rack.rs`, `note.rs`) and `crates/neoteletext-audio/src/receiver/instruments.rs`, as they stood on 18 November 2026 (engine commit dd0421c6) | What is built today: the voice and its checks, the packed layout as read, the rack of sixteen parts, the messages taken, the receiver's slots. |
| **The kit's reader** | `~/devel/neoteletext-server-ts-protocol/src/sound/synth7-sysex.ts` (`synth7BankFromSysex`) | What the TypeScript kit accepts today: the 4,104-byte 32-voice dump. |
| **Wire format as built** | `~/devel/synthesizer-reference/synthesizer-wire-format.html` and `programming-the-synthesizers.html` | What exists today on the wire and in the kit, under the old names, for section 17. |
| **The architecture** | `midi-architecture.md` in this folder | The block and its bounds, the records, banks and their carriage, program change mapping, the restatement, the codec numbers, and the behaviours common to every synthesizer (section 11.1, MIDI-84 to MIDI-92). Where this document and it disagreed, it was followed. |

**The filed MIDI standards.** The MIDI 1.0 Detailed Specification 4.2 and Standard MIDI Files 1.0, in the MIDI Manufacturers Association's bundle of document version 96.1 (rdm SRC-6469), and the Recommended Practice RP-015, "Response to Reset All Controllers" (rdm SRC-6468), are filed in `~/devel/teletext-reference/midi/`; `midi-architecture.md`, section 1.5, describes them and the form of their citations, "MIDI 1.0 4.2, printed page n (PDF m)", the PDF page being that of the filed file. Every statement of this document that rests on one of them, and not on a filed Yamaha manual, was read against the filed copy on 18 November 2026 and cites the place it rests on. This document uses MIDI 1.0 only for what is common to all MIDI: the status bytes, that a note on of velocity 0 is a note off, the centre of pitch bend, the meaning of controllers 120, 121 and 123, registered parameter number 0, and that a switch controller is on from 64; and RP-015 through DEC-6464 version 2 and MIDI-84.

Decisions this document follows: DEC-6453 (each instrument is programmed as its most well-known existing interface does it; NeoTeletext defines something only where nothing exists, and records why), DEC-6460 (the provenance of synth7, and the choice of the maker's system exclusive as its interface), DEC-6461 (the names), DEC-6462 (the Rust server is the core: it validates, packs, builds blocks, splits, restates and reads files; the kits are thin), DEC-6464 (every synthesizer answers reset all controllers identically, as RP-015 says, volume unchanged; recorded as proposed, awaiting the owner's confirmation), DEC-6410 (instruments as codecs of the audio profile; the rack of sixteen parts and sixteen notes, item 10), DEC-6429, DEC-6428 (the clean-room rules) and DEC-6420 (the parameter layer translated from an Apache-2.0 program), and the architecture decisions A1 to A6 of the brief of 18 November 2026.

No web page was fetched and no reference program was opened for this document.

## 2. Terms

- **synth7.** NeoTeletext's six-operator FM synthesizer: sixteen parts sharing sixteen notes.
- **The instrument modelled.** The Yamaha DX7, named in this document only where a source is cited.
- **The adopted interface.** The MIDI implementation and system exclusive messages of the instrument modelled, as the manual states them on printed pages 21, 22 and 30 to 32.
- **Operator.** One of the six oscillators of a voice, each with its own envelope, level and frequency, numbered 1 to 6 as the manual numbers them.
- **Voice.** One sound of the instrument: the 155 voice parameters 0 to 154 of S7-28. The manual's word; a "patch" in the other family documents.
- **Voice parameter.** One of the 156 parameters of the parameter change message's group 0, numbered 0 to 155 (S7-28). Parameters 0 to 154 are a voice; parameter 155 is the operator switch, which is not part of a stored voice.
- **Function parameter.** One of the parameters of the parameter change message's group 2, numbered 64 to 77 (S7-33): how the wheels, pedals and controllers act, and whether the instrument is polyphonic. They are not part of a voice: "function parameters cannot be saved in internal or external memory" (page 6).
- **Packed voice.** The 128-byte form of one voice inside the 32-voice dump (section 10).
- **Part.** One of synth7's sixteen instruments within one sound, each answering one MIDI channel (S7-1). The instrument modelled is one part.
- **Current voice.** The voice a part plays notes with: chosen by a program change, replaced by a single-voice dump, edited by a parameter change. The instrument modelled calls the voice being played and edited its edit buffer (page 12, "EDIT/COMPARE"); this document says "current voice".
- **Bank.** The 32 voices of one 32-voice dump, which a sound names by handle (`midi-architecture.md`, MIDI-56 and MIDI-57). The first bank a sound names (bank index 0) is what program changes 0 to 31 choose among: the "internal memory" of the instrument modelled (page 1: "a 32-voice internal memory").
- **Cartridge bank.** The second bank a sound names (bank index 1), chosen by program changes 32 to 63, as the instrument's cartridge is (page 30). Whether a sound may name more than one bank is the architecture's open question 3 (`midi-architecture.md` section 20); its requirements are written for its recommended answer, under which a synth7 sound may name a cartridge bank (S7-50).
- **Note.** One of the sixteen sounding notes synth7 shares among its parts (S7-3).
- **Block.** 20 milliseconds of a sound's input, 960 samples at 48,000 Hz (decision A2). Its content is a Standard MIDI File track-event list whose tick is 0.1 millisecond (decision A3), in which a system exclusive message is written `F0 <length> <bytes after F0>`.
- **Channel `n`.** The low four bits of a status byte, 0 to 15, which the manual calls channels 1 to 16 ("n=0 ; ch1 ~ n=15 ; ch16", page 32).
- **Counted as ignored.** The message changes nothing, and a count the instrument keeps (`ignored_events` today) rises by one. Nothing is an error.
- **Not stated in the source.** None of the filed Yamaha manuals (the DX7, TX7 and DX7 II manuals) says. Nothing is supplied from memory in its place; where synth7 needs an answer, the answer is NeoTeletext's own and is listed in section 15.

## 3. What the instrument modelled is (facts, not requirements)

The instrument modelled is a 61-key keyboard, "C1 ~ C6 (Initial & After touch sensitive)", with an FM tone generator of "6 operators, 32 algorithms", and "POLY mode: 16 notes, MONO mode: 1 note" (page 27). It keeps 32 voices in its internal memory and reaches 32 more on a cartridge (pages 1, 3, 5 and 27). It answers one MIDI receiving channel, 1 to 16, set at its panel (page 21; page 27, "MIDI CHANNEL 1 ~ 16"). It exchanges three kinds of system information with others of its maker: "Data for one voice or for all voices", "The data for a single parameter within a certain voice", "The data for a single parameter within the FUNCTIONS" (page 21). It receives system information only when its panel's "SYS INFO" is set "AVAIL" and, for anything that writes memory, when its memory protect is off (pages 21, 22 and 32).

Its function parameters, the settings of the pitch bend wheel, portamento, polyphony and the four modulation controllers, are kept apart from its voices: "Function parameters are memorized and maintained even when power to the DX is cut off. Unlike voice data, however, function parameters cannot be saved in internal or external memory" (page 6).

---

## 4. Parts, channels and reception

**S7-1. Sixteen parts, one for each channel.** A synth7 sound MUST hold sixteen parts, numbered 0 to 15. A channel message, and a system exclusive message whose sub-status byte carries a channel, on channel `n` MUST act on part `n` and on no other. Each part MUST behave towards its own channel as the instrument modelled behaves towards the one channel it receives on, by every requirement of this document.
- Reason: The instrument modelled is one part on one channel. A NeoTeletext sound that is a small ensemble (a bass, a piano and a pad) must not need three sounds and three audio channels. Mapping each channel to its own instrument keeps every message of the adopted interface meaning exactly what it means on one instrument, so a score or a stream written for the instrument modelled on one channel plays unchanged on part 0, and a score written for several such instruments on several channels plays as it would on that many. The sixteen-part rack is NeoTeletext's own (DEC-6410 item 10), listed in section 15, and is the channel map `midi-architecture.md` requires of synth7 (MIDI-67, MIDI-69); that the instrument modelled receives on one channel is listed as a departure in section 14.2.
- Source: The manual, page 21 ("Selecting the Receiving Channel") and page 32 ("This message can be received when the channel number of reception data accords with the channel number of the DX7"). DEC-6410 item 10. `midi-architecture.md`, MIDI-67 and MIDI-69. synth7's source, `rack.rs` (`PARTS`, "one for each MIDI channel").
- Verification: A test plays the same score on channel 0 and on each other channel and checks identical samples; a test gives parts 0 and 5 different voices, plays one note on each channel, and checks that each note sounds its part's voice and that a pitch bend, a control change or a program change on channel 5 changes nothing on part 0.

**S7-2. What a part holds and what the parts share.** Each part MUST hold, separately from every other part: its current voice (the 155 voice parameters 0 to 154), its operator switch (voice parameter 155), its program number, its fourteen function parameters (S7-33), its pitch bend, its modulation wheel, breath controller, foot controller and channel pressure values, its volume, its sustain pedal and portamento switch, its low-frequency oscillator, and the keys held on it. The sixteen parts MUST share the sound's bank of 32 voices and its cartridge bank, where it names one (S7-50), and one pool of sixteen notes (S7-3).
- Reason: Each part is one instrument modelled, and each of these is what one such instrument holds for itself (its edit buffer, its function settings, its controllers). The banks are shared because the sound names them (`midi-architecture.md`, MIDI-57), as today; the notes are shared because sixteen is the polyphony of one instrument modelled and the bound on synth7's work (DEC-6410 item 10).
- Source: The manual, page 6 (function parameters are the instrument's own and are not in a voice), page 12 (the voice being edited), page 27 (16 notes). synth7's source, `rack.rs` (`Part`, `Rack`).
- Verification: A test sets different function parameters, volumes, wheels and current voices on two parts and checks that each part's notes follow its own; a test sends a 32-voice dump and checks that a program change on every part reaches the new voices.

**S7-3. Sixteen notes, shared.** At most sixteen notes MUST sound at once across all sixteen parts. A note on that needs a note when all sixteen are taken MUST take, in this order of preference: the note already sounding on the same key of the same part; a note that is not sounding; the note released longest ago; the note held (by its key or the sustain pedal) longest. A note taken from another sounding note MUST carry on from that note's sound without a gap, as the instrument modelled does: "If a 17th key is pressed the first note makes a smooth transition to the 17th note."
- Reason: Sixteen is the instrument's polyphony, and its own rule takes the oldest note. Preferring a released note over a held one, and the same key over another, is what is built and keeps held notes sounding longest.
- Source: The manual, page 14 ("In the polyphonic mode, for example, maximum simultaneous output is 16 notes. If a 17th key is pressed the first note makes a smooth transition to the 17th note") and page 27 ("POLY mode: 16 notes"). The order among released and held notes: synth7's source, `rack.rs` (`note_on`), own choice, listed in section 15.
- Verification: The existing rack tests that hold seventeen keys continue to pass; a test holds sixteen keys on four parts, releases one, presses another and checks that the released note is the one taken.

**S7-4. Reception conditions.** synth7 MUST take every message of this document as the instrument modelled takes it with its receiving channel equal to the message's channel, its system information set "AVAIL", and its internal memory protect off. synth7 has no setting of the receiving channel, of system information or of memory protect, and no message sets them.
- Reason: The instrument modelled refuses system exclusive data unless system information is available and memory protect is off (page 32: "This message requests reception with the same format as transmission when MIDI channel numbers are corresponded, system information is available, and Memory protect is off"). Those are switches of its panel that protect its battery-backed memory from a cable; a synth7 sound has no memory that outlives the sound, and the sender of the sound is the only source of its input, so the switches have nothing to protect. Every part receives its own channel (S7-1).
- Source: The manual, pages 21, 22 and 32 (blue text under "2-2-2", "2-2-3" and "2-2-4"); page 19 (memory protect). The omission of the switches is listed in section 14.
- Verification: The tests of S7-40, S7-42 and S7-44 send each system exclusive message with no preceding setting and check that it takes effect.

## 5. Channel messages

**S7-5. The messages synth7 acts on.** synth7 MUST act on exactly these MIDI 1.0 messages, and count every other as ignored: note off (`8n`); note on (`9n`); control change (`Bn`) of the controllers the table of S7-10 marks "acted on"; program change (`Cn`); channel pressure (`Dn`, S7-22); pitch bend (`En`); and the two system exclusive messages a block carries for synth7, the single-voice dump (S7-38) and the parameter change (S7-43) (`F0 43 ...`). The 32-voice dump (S7-41) reaches synth7 only as a bank (S7-42). Polyphonic key pressure (`An`), every control change the table of S7-10 does not mark "acted on", every other system exclusive message, and every system common and system real-time message MUST change nothing and be counted as ignored. This is synth7's complete table of the messages it acts on, as `midi-architecture.md` MIDI-10 requires.
- Reason: These are the messages the adopted interface receives (page 32), with channel pressure taken as S7-22 explains, and the messages of NeoTeletext's common layer and common behaviours (`midi-architecture.md`, MIDI-9 and MIDI-84 to MIDI-92; S7-19, S7-20 and S7-9).
- Source: The manual, pages 30 to 32. Channel pressure: S7-22. The common layer: `midi-architecture.md`, MIDI-9, MIDI-10 and section 11.1.
- Verification: A test sends one message of every status `80` to `EF`, every controller 0 to 127, and system messages `F1` to `FF`, and checks which change the instrument's state and that each of the others adds one to the count and leaves the samples identical to a run without it.

**S7-6. Note on.** On a note on whose velocity is 1 to 127, the part MUST start a note of the key (data byte 1, 0 to 127) with its current voice, the velocity scaling each operator's level by that operator's KEY VELOCITY SENSITIVITY (voice parameter 15 of the operator's 21, S7-28): 0 none, 7 the most, velocity 1 the softest ("ppp") and 127 the hardest ("fff"). A note on of velocity 0 MUST be taken as a note off of that key.
- Reason: The adopted interface: "Key velocity (v=0 ; Key OFF, v=1 ; ppp ~ v=127 ; fff)" (page 32), and each operator's sensitivity "Permits adjustment of key touch response … No touch response will be produced with a 0 setting, while a setting of 7 produces maximum response" (page 16). How much a velocity changes a level at each sensitivity is not stated in the source; synth7 keeps what is built (the parameter layer translated under DEC-6420).
- Source: The manual, pages 16, 30 and 32. synth7's source, `note.rs` (`start`).
- Verification: The existing velocity tests continue to pass; a test plays one note at velocities 1, 64 and 127 with all sensitivities 0 and checks identical samples, and with sensitivity 7 checks that the level rises with the velocity; a test checks that a note on of velocity 0 releases the note as a note off does.

**S7-7. Note off.** On a note off, the part MUST release its note of that key, or, if its sustain pedal is down, mark it held by the pedal until the pedal lifts. The release velocity MUST NOT change the sound.
- Reason: "Key velocity (v : ignored)" for a key off (page 32, blue text).
- Source: The manual, page 32.
- Verification: A test releases the same note with note offs of velocity 0, 64 and 127 and checks identical samples.

**S7-8. Keys and their pitch.** synth7 MUST take every key 0 to 127. Key 60 is the manual's C3, the key at which KEY TRANSPOSE (voice parameter 144) at its middle value 24 changes nothing; each step of transpose MUST move every key by one semitone, from 24 semitones down (0) to 24 up (48), and the moved key MUST be what level scaling, rate scaling and pitch follow. Every key MUST sound one equal-tempered semitone above the key below it. Which frequency key 60 sounds with every operator at a ratio of 1.00 is not stated in the source; synth7 keeps what is built (key 69 at 440 Hz).
- Reason: The adopted interface receives "Key number (k=0, 1 ; C#−2 ~ k=127 ; G8)" (page 32) and sends "k=36 ; C1 ~ k=96 ; C6" (page 30), so its key numbers name C3 as key 60. KEY TRANSPOSE "Transposes pitch over a ±2 octave range in semitone steps with C3 as standard" (page 17). That transpose moves the key itself for scaling is not stated in the source and is what is built (`note.rs`, "Own choice: transpose moves the key itself, so keyboard scaling follows the transposed key as pitch does").
- Source: The manual, pages 17, 18, 30 and 32. The page 32 text gives the lowest key as "C#−2"; from page 30's numbering key 0 would be C−2, and the difference is the source's own. NeoTeletext's own, section 15 item 5.
- Verification: A test measures the pitch of one operator at ratio 1.00 for keys 0, 36, 60, 69, 96 and 127 and checks each against its semitone within 1 cent; a test sets transpose to 0, 24 and 48 and checks a shift of −24, 0 and +24 semitones.

**S7-9. Pitch bend.** On a pitch bend, the part MUST form the 14-bit number `data byte 2 × 128 + data byte 1`, whose centre is 8,192, and MUST bend the pitch of every operator of the part's notes by `(number − 8,192) ÷ 8,192` of the part's PITCH BEND RANGE (function parameter 65, 0 to 12 semitones; 0 bends nothing). The range MUST be set both by a parameter change of function parameter 65 (S7-43) and by registered parameter number 0, pitch bend sensitivity (`midi-architecture.md`, MIDI-90): controller 101 at 0 and controller 100 at 0 select it, controller 6 then sets the range in semitones, and controllers 96 and 97 raise and lower it by one semitone (MIDI-76); a value above 12 MUST set 12, the most the instrument modelled has; controller 38's cents MUST change nothing, since the range is held in whole semitones as function parameter 65 holds it; and whichever of the two messages came last MUST hold. Controllers 101 and 100 at 127 and 127 MUST select no parameter, after which controllers 6, 38, 96 and 97 change nothing (MIDI-76). Neither a program change nor controller 121 MUST change the range (MIDI-90, MIDI-84). When the part's PITCH BEND STEP (function parameter 66, 0 to 12) is above 0, the bend MUST move in steps of that many semitones: the bend in semitones is rounded towards the centre to a whole multiple of the step.
- Reason: The adopted interface's pitch bend wheel bends "throughout the set range" (page 3); RANGE "can be set from 0 to 12. 0 range is equivalent to no pitch bend. A setting of 12 permits pitch bend over a ±1200 cent (2 octave) range" (page 6); STEP "A setting of 0 corresponds to 0-cent steps, and a setting of 12 corresponds to 1200-cent (1 octave) steps … If STEP is set to 1, the pitch will bend in 100-cent (semitone) steps" (page 6). The instrument modelled reads only the most significant byte ("Pitch bender value LS byte (ignored)", page 32, blue text); synth7 reads all fourteen bits, as `midi-architecture.md` MIDI-91 requires of every synthesizer, so a bend is never coarser than on the instrument and a stream written for it bends the same to within 1/128 of the range. The instrument sets its range only by function parameter 65; registered parameter number 0 is added because MIDI-90 requires it of every synthesizer, which is the architecture's open question 5, pending the owner. Both departures are listed in section 14.2. That the step rounds towards the centre is not stated in the source and is NeoTeletext's own (section 15 item 6).
- Source: The manual, pages 3, 6, 27 and 32. `midi-architecture.md`, MIDI-76, MIDI-90 and MIDI-91. MIDI 1.0 for the 14 bits and the centre (MIDI 1.0 4.2, printed page 19, PDF 51) and for registered parameter number 0 (printed pages 17 and 18, PDF 49 and 50; Tables III and IIIa, PDF 102 and 103). Today synth7 bends a fixed 2 semitones (`rack.rs`, `PITCH_BEND_SEMITONES`) and has no step.
- Verification: A test holds a note with range 2, 7 and 12 and sends bends of 0, 4,096, 8,192, 12,288 and 16,383, checking the pitch against the formula within 1 cent; a test with range 12 and step 1 sweeps the bend and checks that only whole semitones sound; a test with range 0 checks that no bend moves the pitch; a test sets the range by registered parameter number 0 to 1, 7 and 24 semitones and by function parameter 65, bends fully and checks the range (24 set to 12), that the later message holds, that controller 96 after the selection raises the range by one, and that a program change and controller 121 leave it.

**S7-10. The controllers.** synth7 MUST act on each controller as this table says, and count every other controller as ignored. The second column is the manual's reception list (page 32); "today" is what synth7 does on 18 November 2026 (`rack.rs`, `control_change`).

| Controller | The manual (page 32) | Value range in the manual | What synth7 does today | What synth7 MUST do | Requirement |
|---|---|---|---|---|---|
| 1 | Modulation wheel | 0 to 127 | Adds pitch modulation depth up to that of a voice's depth of 99, scaled by the voice's pitch sensitivity | Acted on: the part's modulation wheel, applied through function parameters 70 and 71 | S7-11 |
| 2 | Breath controller | 0 to 127 | Ignored and counted | Acted on: the part's breath controller, through function parameters 74 and 75 | S7-12 |
| 4 | Foot controller | 0 to 127 | Ignored and counted | Acted on: the part's foot controller, through function parameters 72 and 73 | S7-13 |
| 5 | Portamento time | 0 to 127 | Ignored and counted | Acted on: sets the part's PORTAMENTO TIME (function parameter 69) | S7-14 |
| 6 | Data entry knob ("MASTER TUNE only") | 0 to 127 | Ignored and counted | Acted on only as the data entry of registered parameter number 0 while it is selected (S7-9); otherwise counted as ignored, pending open question 4 | S7-9, S7-18 |
| 7 | Volume ("LS 4 bit are ignored", blue text) | 0 to 127 | The part's volume, 128 steps, moving by at most 1.5 dB a 32-sample step | Acted on: the part's volume | S7-15 |
| 38 | Not in the manual | | Ignored and counted | Acted on only as the fine data entry of registered parameter number 0 while it is selected, where it changes nothing (S7-9); otherwise counted as ignored | S7-9 |
| 64 | Sustain foot switch | 0 off, 127 on | The part's sustain pedal, down from 64 | Acted on: the part's sustain pedal, down from 64 | S7-16 |
| 65 | Portamento foot switch | 0 off, 127 on | Ignored and counted | Acted on: the part's portamento switch, on from 64 | S7-17 |
| 96 | Data entry +1 | 127, "ON only" | Ignored and counted | Acted on only as the increment of registered parameter number 0 while it is selected (S7-9); otherwise counted as ignored, pending open question 4 | S7-9, S7-18 |
| 97 | Data entry −1 | 127, "ON only" | Ignored and counted | Acted on only as the decrement of registered parameter number 0 while it is selected (S7-9); otherwise counted as ignored, pending open question 4 | S7-9, S7-18 |
| 100 | Not in the manual | | Ignored and counted | Acted on: the low seven bits of the registered parameter number selected (S7-9; `midi-architecture.md`, MIDI-76 and MIDI-90) | S7-9 |
| 101 | Not in the manual | | Ignored and counted | Acted on: the high seven bits of the registered parameter number selected (S7-9; MIDI-76, MIDI-90) | S7-9 |
| 120 | Not in the manual | | All sound off: the part's notes cut over 21 ms | Acted on, as every synthesizer does (MIDI-86) | S7-20 |
| 121 | Not in the manual | | Reset all controllers: wheel 0, bend centre, pedal up; volume left | Acted on, as every synthesizer does, by the list of S7-20 item 2 (MIDI-84, RP-015) | S7-20 |
| 123 | Not in the manual | | All notes off: as a note off of every held key; the pedal still holds | Acted on, as every synthesizer does (MIDI-85) | S7-20 |
| 124 | Not in the manual | | Ignored and counted | Acted on: all notes off of the part, and nothing else (MIDI-89) | S7-19 |
| 125 | "OMNI all key off" | "ignored" (blue text) | Ignored and counted | Acted on: all notes off of the part, and nothing else (MIDI-89) | S7-19 |
| 126 | "MONO all key off" | 1 | Ignored and counted | Acted on: all notes off of the part, and nothing else (MIDI-89) | S7-19 |
| 127 | "POLY all key off" | "ignored" (blue text) | Ignored and counted | Acted on: all notes off of the part, and nothing else (MIDI-89) | S7-19 |

Every controller not in the table (0, 3, 8 to 37, 39 to 63, 66 to 95, 98, 99, 102 to 119 and 122) MUST be counted as ignored. Controllers 0 and 32, bank select, are among them: the adopted interface has no bank select (`midi-architecture.md`, MIDI-64). Controllers 98 and 99, which select non-registered parameter numbers, are among them: synth7 has no non-registered parameter.
- Reason: The table is the adopted interface's reception list, entry by entry, with the controllers `midi-architecture.md` requires of every synthesizer (the common layer of MIDI-9, the common behaviours of MIDI-84 to MIDI-92, and registered parameter number 0 of MIDI-90), and says for each what is built and what is owed.
- Source: The manual, page 32 (the list), page 30 (the transmitted list: controllers 1, 2, 4, 6, 64, 65, 96 and 97). `midi-architecture.md`, MIDI-9, MIDI-64, MIDI-76 and MIDI-84 to MIDI-92. synth7's source, `rack.rs`.
- Verification: The test of S7-5; and each row's requirement's test.

**S7-11. The modulation wheel, controller 1.** On controller 1, the part MUST set its modulation wheel to the value, 0 to 127. The wheel MUST act through the part's MODULATION WHEEL RANGE (function parameter 70, 0 to 99) and MODULATION WHEEL ASSIGN (function parameter 71) as S7-36 specifies: with PITCH on it deepens the low-frequency oscillator's pitch modulation, with AMPLITUDE on its amplitude modulation, and with EG BIAS on it raises the level of each operator by that operator's MOD SENSITIVITY AMPLITUDE. At range 0, or with all three off, the wheel MUST change nothing.
- Reason: "The modulation wheel, foot controller, breath controller or keyboard after touch can be used to control LFO modulation depth applied to pitch, amplitude or envelope" (page 7); RANGE "No effect is produced with a 0 setting, and a setting of 99 produces maximum effect" (page 8). Today the wheel always adds pitch depth as if the range were 99 and PITCH alone were on; S7-35 makes that today's behaviour the default.
- Source: The manual, pages 3, 7, 8, 26, 31 and 32. synth7's source, `note.rs` (`control`, "Own choice: the wheel adds vibrato depth").
- Verification: The tests of S7-36 for the wheel.

**S7-12. The breath controller, controller 2.** On controller 2, the part MUST set its breath controller to the value, 0 to 127, acting through BREATH CONTROLLER RANGE and ASSIGN (function parameters 74 and 75) as S7-36 specifies.
- Reason: The adopted interface receives "Breath controller 0 ~ 127" (page 32); "The effect will not be audible unless breath is applied to the controller" (page 8).
- Source: The manual, pages 8, 31 and 32.
- Verification: The tests of S7-36 for the breath controller.

**S7-13. The foot controller, controller 4.** On controller 4, the part MUST set its foot controller to the value, 0 to 127, acting through FOOT CONTROLLER RANGE and ASSIGN (function parameters 72 and 73) as S7-36 specifies.
- Reason: The adopted interface receives "Foot controller 0 ~ 127" (page 32); "Maximum effect is produced by pressing the foot controller all the way down, while raising the controller fully eliminates the effect" (page 8). The foot controller that the instrument's VOLUME jack takes (page 5) is a pedal wired to its volume, not a MIDI message, and is not this controller.
- Source: The manual, pages 5, 8, 31 and 32.
- Verification: The tests of S7-36 for the foot controller.

**S7-14. Portamento time, controller 5.** On controller 5, the part MUST set its PORTAMENTO TIME (function parameter 69) to `floor((value × 99 + 63) ÷ 127)`: value 0 is time 0 and value 127 is time 99. A later parameter change of function parameter 69 MUST overwrite it, and it MUST overwrite that parameter in turn.
- Reason: The adopted interface receives "Portamento time 0 ~ 127" (page 32) for a parameter whose range is 0 to 99 (page 31). How the 128 values become the 100 times is not stated in the source; the linear scale is NeoTeletext's own (section 15 item 7).
- Source: The manual, pages 6, 31 and 32.
- Verification: A test sends values 0, 64 and 127 and reads back times 0, 50 and 99; a test checks that the controller and the parameter change set the same one parameter.

**S7-15. Volume, controller 7.** On controller 7, the part MUST set its volume to the value, 0 (silent) to 127 (no attenuation), by the volume law that every NeoTeletext synthesizer shares (`midi-architecture.md`, MIDI-82 and MIDI-92): a gain of `(value × value) ÷ (127 × 127)` of full, separate from every level of the voice. synth7 MAY move the gain to its new place more slowly than MIDI-82's slew, as MIDI-82 permits it, and MUST move it by at most 1.5 decibels (a quarter of a doubling) in each 32 samples. Before any controller 7 arrives the volume is 127; neither controller 121 nor a program change changes it (MIDI-84). synth7 MUST use all seven bits of the value.
- Reason: The adopted interface receives "Volume 0 ~ 127" and adds "(LS 4 bit are ignored.)" (page 32, blue text): the instrument modelled has eight steps of volume. synth7 keeps 128 steps, as built and as MIDI-92 requires of every synthesizer, so that a fade is smooth; a stream written for the instrument modelled sounds at the same eight levels and between them. Which attenuation each step gives on the instrument modelled is not stated in the source. This departure is listed in section 14.2. synth7's law today is MIDI-82's law: `tables.rs` holds, for each value `v`, the attenuation `round(2 × log2(127 ÷ v) × 1024)` in units of 1/1024 of a doubling (an amplitude of `(v ÷ 127)²`, applied as a logarithm so that the kernel needs no multiplication), with value 0 silent. Only its slew differs: a quarter of a doubling each 32-sample block (`rack.rs`, `VOLUME_STEP`), chosen and measured so that a fade passes the click measure (`midi-architecture.md`, MIDI-83), which MIDI-82 allows by name.
- Source: The manual, page 32. synth7's source, `rack.rs` (`VOLUME_STEP`, `Part::volume`) and `tables.rs` (`VOLUME_ATTENUATION`). `midi-architecture.md`, MIDI-82, MIDI-83 and MIDI-92.
- Verification: The existing volume tests (`tests/synth7_rack.rs`, `tests/synth7_control_sweep.rs`) continue to pass.

**S7-16. The sustain pedal, controller 64.** On controller 64, the part's sustain pedal MUST go down at values 64 to 127 and up at 0 to 63. While it is down, a key released on the part MUST go on sounding as if held. When it lifts, every note it holds MUST be released. In mono mode (S7-26), "a key pressed while another key is held will take priority, and the sustain effect will apply to the new key".
- Reason: The adopted interface receives "Sustain foot switch 0 ; OFF, 127 ; ON" (page 32). What values 1 to 126 do is not stated in the source; the threshold of 64 is the one rule `midi-architecture.md` MIDI-87 sets for every synthesizer, MIDI 1.0's switch rule (MIDI 1.0 4.2, printed page 12, PDF 44: "it should recognize 0-63 (00H-3FH) as "OFF" and 64-127 (40H-7FH) as "ON""), and what is built. That the instrument modelled names only the values 0 and 127 is listed in section 14.2.
- Source: The manual, pages 7 and 32. `midi-architecture.md`, MIDI-87. synth7's source, `rack.rs` (`PEDAL_DOWN`).
- Verification: The existing sustain tests continue to pass; a test checks values 63 and 64 at the edge.

**S7-17. The portamento switch, controller 65.** On controller 65, the part's portamento switch MUST go on at values 64 to 127 and off at 0 to 63. While it is off the part MUST play no portamento or glissando, whatever its function parameters; while it is on, the part MUST glide as S7-27 specifies. Before any controller 65 arrives the switch is on. Controller 121 MUST put the switch off, as `midi-architecture.md` MIDI-84 puts the portamento pedal off in every synthesizer that has one; that the switch therefore starts on but resets to off is open question 7.
- Reason: "The portamento/glissando effect can also be turned ON or OFF using an optional FC-4 or FC-5 foot pedal once the portamento/glissando function has been turned on using the front-panel controls. Pressing the foot pedal turns the effect ON. The effect is OFF when the foot pedal is released" (page 7); the adopted interface receives "Portamento foot switch 0 ; OFF, 127 ; ON" (page 32). The switch's state before any message is not stated in the source; on is NeoTeletext's own (section 15 item 8), so that a portamento time sent by a parameter change is heard without a pedal, as on the instrument with no pedal plugged in.
- Source: The manual, pages 4, 7 and 32. `midi-architecture.md`, MIDI-84; DEC-6464 (proposed, awaiting the owner's confirmation).
- Verification: A test sets portamento time 50, plays two notes with the switch at 0 and checks no glide, then at 127 and checks a glide; a test checks a glide with no controller 65 ever sent; a test sends controller 121 and checks no glide until controller 65 at 127.

**S7-18. The data entry controllers 6, 96 and 97.** Except while registered parameter number 0 is selected, when they set the pitch bend range (S7-9), synth7 MUST count controllers 6, 96 and 97 as ignored, until open question 4 is answered.
- Reason: On the instrument modelled these move the panel's data entry slider and its +1 and −1 keys, which act on whichever parameter the panel last selected ("When data entry is initiated while in the PLAY mode, the parameter selected at the end of the FUNCTION mode can be controlled", page 5); controller 6 on reception acts on "MASTER TUNE only" (page 32). A synth7 part has no panel and no selected parameter, so controllers 96 and 97 have nothing to act on; master tune is a tuning of the whole instrument to others, ±75 cents (pages 6 and 27), which a NeoTeletext sound does not need, since it is in tune by construction. How controller 6's 128 values would map to the 151 cents of master tune is not stated in the source.
- Source: The manual, pages 5, 6, 27, 30 and 32.
- Verification: The test of S7-5.

**S7-19. The mode messages, controllers 124, 125, 126 and 127.** On controller 124, 125, 126 or 127, whatever the value, the part MUST act as on all notes off (`midi-architecture.md`, MIDI-85): it MUST release every note held by a key, as a note off of each would, and a note held by the sustain pedal stays held. They MUST do nothing else: they MUST NOT change the part between poly and mono mode, nor its channel (MIDI-71, MIDI-89).
- Reason: `midi-architecture.md` MIDI-89 sets one rule for every synthesizer: each mode message is all notes off and nothing more. The adopted interface receives 125, 126 and 127 each as an "all key off": "OMNI all key off", "MONO all key off", "POLY all key off" (page 32), and does not list 124. Whether they also change the instrument's mode is not stated in the DX7 manual; its mode is a function parameter (64) that a parameter change sets, and its channel a panel setting. (The TX7 manual says its mode messages change its mode, "accompanied by a compulsory voice dump and cleaning of the Key Assigner", printed page 34; that is another instrument's behaviour and is not taken.) The blue text "ignored" against controllers 125 and 127 stands in the column of values, and is taken to mean that the value is ignored, as the value 1 against controller 126 is the one value that message carries; that reading is NeoTeletext's own (section 15 item 9). That the instrument modelled names 126 "MONO all key off", and lists neither 124 nor any effect beyond releasing keys, is listed as a departure in section 14.2.
- Source: The manual, page 32. The TX7 manual, printed page 34. `midi-architecture.md`, MIDI-71, MIDI-85 and MIDI-89.
- Verification: A test holds three keys and sends each of the four controllers in turn, checking every key's note released; with the pedal down, checking the notes held until it lifts; and checking that the mode (S7-25, S7-26) and the channel map are unchanged.

**S7-20. All sound off, reset all controllers and all notes off: controllers 120, 121 and 123.** The part MUST act on these three control changes, whatever their value, exactly as `midi-architecture.md` requires of every synthesizer, although the adopted interface does not receive them:
1. Controller 120, all sound off (MIDI-86): every voice of the part, held, sustained and releasing alike, MUST be faded to silence over 21 milliseconds (1,008 samples, within MIDI-86's 1,024) and freed; the pedal, every controller and the voice MUST be left as they are.
2. Controller 121, reset all controllers, on the part its channel addresses (MIDI-84, which follows the Recommended Practice RP-015 under DEC-6464 version 2, recorded as proposed and awaiting the owner's confirmation; RP-015, page 2): the modulation wheel (controller 1) and channel pressure MUST go to 0, the pitch bend to its centre (8,192), the sustain pedal (controller 64) up, releasing the notes it held, and the portamento switch (controller 65) off (S7-17), and the registered parameter number selection to none, the null value 127 in controllers 100 and 101 (S7-9). The volume (controller 7), the current voice and every parameter of it, the operator switch, the program number, every function parameter (so the pitch bend range of S7-9 stays), and the held keys MUST be left as they are. synth7 takes no expression, pan, bank select, effect or sound controller and no polyphonic key pressure, so RP-015's settings of those have nothing to act on. Every other controller synth7 responds to, as MIDI-84 item 4 requires this document to list:

| Controllers | What they move | On controller 121 | Reason |
|---|---|---|---|
| 2, breath controller (S7-12), and 4, foot controller (S7-13) | Performance controllers, applied through function parameters 72 to 75 | Set to 0 | RP-015: "Any other controllers that a device can respond to should be set to 0" (page 2); they are performance controllers, and 0 is their rest |
| 5, portamento time (S7-14) | PORTAMENTO TIME, function parameter 69 | Left as it is | It sets a function parameter, which is a setting of the instrument kept like the voice, not a performance control (DEC-6464 item 4); RP-015 lets a manufacturer leave a controller unaffected "as long as the behavior is documented" (page 2) |
| 6, 38, 96 and 97, data entry, increment and decrement of registered parameter number 0 (S7-9) | The pitch bend range, function parameter 65 | Left as it is | RP-015: "Do NOT reset registered or non-registered parameters" (page 2) |
3. Controller 123, all notes off (MIDI-85): as S7-19.
- Reason: Every NeoTeletext sound needs them (a sound must be silenced at once; a sender resets a part between pieces), they are standard MIDI 1.0 messages (decision A1), the owner requires every synthesizer to answer them identically (DEC-6464), and 120, 121 and 123 are built today. The 21-millisecond fade is synth7's as built (DEC-6460 item 2), which MIDI-86 takes as its bound. That reset all controllers also returns breath and foot to 0 is RP-015's rule for every controller it does not name ("should be set to 0", page 2), and was checked against it on 18 November 2026. That the adopted interface receives none of the three is listed as a departure in section 14.2.
- Source: `midi-architecture.md`, MIDI-9, MIDI-84, MIDI-85 and MIDI-86; DEC-6464 version 2; RP-015, page 2; MIDI 1.0 for the three controllers (MIDI 1.0 4.2, printed pages 20, 24 and 25, PDF 52, 56 and 57; Table IV, PDF 104); synth7's source, `rack.rs` (`control_change`). The manual's reception list (page 32) has none of them.
- Verification: The existing tests for the three controllers continue to pass; a test moves the modulation wheel, the breath controller, the foot controller, channel pressure, the pitch bend, the sustain pedal, the portamento switch, the volume, a voice parameter, a function parameter and the pitch bend range, sends controller 121, with the values 0 and 127, and checks each against item 2 and its table; a test holds a chord with the pedal down, sends controller 120, and checks the output 0 by sample 1,024 and the sweep measure (MIDI-83) held.

**S7-21. Program change.** On a program change, the part MUST copy into its current voice, setting voice parameters 0 to 154, the voice S7-50's mapping gives for the program number, and MUST set its operator switch (parameter 155) to all six on. Notes already sounding MUST keep the voice they started with; notes started afterwards use the new current voice. The part's function parameters, controllers and held keys MUST NOT change. Where the mapping reaches no voice (a program number of 64 to 127, a cartridge program when the sound names no second bank, or a voice the bank holds as refused), the part MUST take the default voice (S7-51) and count the program change as passed over (`midi-architecture.md`, MIDI-59). Until a first program change arrives, every part's current voice is voice 0 of bank index 0, or the default voice if that voice is missing or was refused (MIDI-61; every sound names at least one bank, MIDI-57). A program change to the program a part already plays, whose current voice and operator switch are unchanged since, MUST change nothing that is heard (MIDI-97).
- Reason: The adopted interface: "Program number (p=0:INT1 ~ p=31:INT32, p=32:CRT1 ~ p=63:CRT32)" (page 32). The internal voices are the bank. On the instrument modelled the operator switch "operates only in the EDIT mode and OPERATOR ON-OFF data is not stored in memory" (page 16), so a recalled voice has every operator on. That sounding notes keep their voice, and that part 0's first voice is voice 0, are what is built. A program number the mapping does not reach sets the default voice, as `midi-architecture.md` MIDI-59 requires of every family; this document formerly left the part unchanged for program changes 64 to 127, and was changed to follow MIDI-59.
- Source: The manual, pages 16, 30 and 32. `midi-architecture.md`, MIDI-59, MIDI-61 and MIDI-97. synth7's source, `rack.rs` (`program_change`, `note_on`).
- Verification: A test builds a bank of 32 different voices, sends program changes 0, 1, 17 and 31 and checks the current voice after each against the bank; a test holds a note across a program change and checks it keeps its timbre; a test checks that program changes 64 and 127 set the default voice and are counted; a test repeats a program change while a note is held and checks identical samples.

**S7-22. Channel pressure.** On a channel pressure message (`Dn`), the part MUST set its pressure to the data byte, 0 to 127, acting through AFTER TOUCH RANGE and ASSIGN (function parameters 76 and 77) as S7-36 specifies.
- Reason: The instrument modelled has key pressure ("Initial/After Touch response provided", page 3; "The amount of pressure applied determines the depth of the effect", page 8), sends it as "After touch & Channel number … Touch value (0 ~ 127)" (page 30), and has two function parameters for it (76 and 77, page 31) that a parameter change sets. Its reception list (page 32) does not name the message; the list's page ends at pitch bend and nothing follows. A part whose after-touch parameters can be set but whose after touch cannot be played would be half an interface, so synth7 takes the message the instrument sends. The maker's tone-generator module of the same voice format, the TX7, receives it ("$D0 AFTER TOUCH", TX7 manual, printed page 32; section 2-2-5, printed page 34), which corroborates the choice but is not the DX7's own reception list. This is listed in section 15 item 10 and is open question 5.
- Source: The manual, pages 3, 8, 26, 30, 31 and 32. The TX7 manual, printed pages 32 and 34.
- Verification: The tests of S7-36 for after touch.

**S7-23. Polyphonic key pressure.** synth7 MUST count polyphonic key pressure (`An`) as ignored.
- Reason: The adopted interface neither sends nor receives it (pages 30 and 32): the instrument's after touch is one value for the keyboard.
- Source: The manual, pages 30 and 32.
- Verification: The test of S7-5.

**S7-24. System common and system real-time messages.** synth7 MUST count every system common and system real-time message as ignored, active sensing (`FE`) among them.
- Reason: The instrument modelled sends active sensing about every 80 milliseconds and, receiving it, turns its sound off when it stops for more than 666 milliseconds (pages 30 and 32, blue text). That guards a cable that may be pulled; a NeoTeletext sound's input is blocks whose loss the receiver detects and handles itself (S7-53; `midi-architecture.md`, MIDI-8, MIDI-101 and MIDI-102). The instrument receives no other system common or real-time message (page 32). A block never carries any of them (MIDI-8); one that arrives in a block is passed over and counted.
- Source: The manual, pages 30 and 32. `midi-architecture.md`, MIDI-8.
- Verification: The test of S7-5, with active sensing sent and then stopped for a second, checking that a held note keeps sounding.

## 6. Poly and mono, portamento and glissando

**S7-25. Poly mode.** While a part's MONO/POLY MODE (function parameter 64) is 0, the part MUST be polyphonic: each key held is its own note, within the sixteen notes of S7-3.
- Reason: The instrument's polyphonic mode (page 6, "Press the DATA ENTRY −1 key for polyphonic operation"); that 0 is poly follows from the −1 key and is listed in S7-33.
- Source: The manual, pages 6, 27 and 31.
- Verification: The existing rack tests, which play chords, continue to pass with function parameter 64 at 0.

**S7-26. Mono mode.** While a part's MONO/POLY MODE is 1, the part MUST sound at most one note. A key pressed while another key of the part is held MUST take the note ("a key pressed while another key is held will take priority"). When the key sounding is released while other keys of the part are held, the note MUST pass to the key pressed most recently among those still held. The part MUST remember 16 held keys; a seventeenth held at once displaces the key held longest. Whether a note passing to a new key while another is held restarts the envelopes is not stated in the source; it MUST NOT restart them (legato), and a key pressed when no key of the part is held MUST start them.
- Reason: "MONO mode: 1 note" (page 27); "In the monophonic mode, a key pressed while another key is held will take priority" (page 7); "FINGERED PORTA … portamento is applied only to legato notes" (page 6) implies that the instrument knows legato notes in mono mode. Return to a still-held key, the sixteen remembered keys and legato without retrigger are not stated in the source and are NeoTeletext's own (section 15 item 11), chosen as the behaviour the fingered portamento's description presumes. Today synth7 has no mono mode.
- Source: The manual, pages 6, 7 and 27.
- Verification: A test in mono mode holds 60, then 64 (the note moves to 64 without the envelope restarting), releases 64 (the note returns to 60), releases 60 (the note is released); a test holds seventeen keys and checks which is forgotten.

**S7-27. Portamento and glissando.** While a part's portamento switch (S7-17) is on and its PORTAMENTO TIME (function parameter 69) is above 0, a note's pitch MUST move from the pitch of the previous note of the part to its own over a time that rises with the parameter, 0 being no glide and 99 the slowest. With PORTAMENTO GLISSANDO (function parameter 68) at 1 the move MUST be in semitone steps; at 0 it is smooth. Which notes glide MUST follow PORTAMENTO MODE (function parameter 67): in poly mode, 0 is "SUS-KEY P RETAIN" ("the pitch of keys released while the sustain pedal is on … does not change. However, portamento is effected between two subsequently pressed keys") and 1 is "SUS-KEY P FOLLOW" ("the pitch of a key released while the sustain pedal is held slides (portamento) to a previously pressed key"); in mono mode, 0 is "FINGERED PORTA" ("portamento is applied only to legato notes") and 1 is "FULL TIME PORTA" ("portamento is always applied"). The time law (the seconds for an octave at each of 0 to 99) is not stated in the source and is NeoTeletext's own, to be set and recorded when it is built.
- Reason: The adopted interface's portamento, quoted from page 6. In poly mode 0 is retain and 1 is follow, as the TX7 manual states ("“0” ... sustain-key pitch retain, “1” ... sustain-key pitch follow", printed page 40, section 4-2, note *1). That in mono mode 0 is fingered and 1 full time is not stated in the source; it follows from the DX7 manual's page 6, where the −1 key makes RETAIN and FINGERED and the +1 key makes FOLLOW and FULL TIME, and is listed in S7-33. Today synth7 has no portamento.
- Source: The manual, pages 6, 7, 27 and 31. The TX7 manual, printed page 40.
- Verification: A test in poly mode with time 50 plays two keys an octave apart and checks the glide's start and end pitch and that its duration rises from time 25 to time 75; with glissando on checks that only semitones sound; a test of each of the four modes checks which notes glide by the quoted rules.

## 7. The voice parameters

**S7-28. The 156 voice parameters.** A synth7 voice MUST be exactly the voice parameters 0 to 154 of this table, each with the range given; parameter 155, the operator switch, is a parameter of the part's current voice that no stored voice holds (S7-30). The numbers are the parameter numbers of the parameter change message, group 0 (S7-43). The last column is where the parameter lies in the packed voice (section 10): its byte, 0 to 127, and its bits.

The manual's table lists parameters 0 to 20 for operator 6 and writes the rest of the operators as "21 ~ OP5 ~ OP1 ~ 125" (page 31). The TX7 manual states the blocks: "21 ~ 41 OP5", "42 ~ 62 OP4", "63 ~ 83 OP3", "84 ~ 104 OP2", "105 ~ 125 OP1" (printed page 38, section 4-1), each operator's 21 in the same order as operator 6's; the DX7 II manual numbers them the same (printed page Add-8). The table below writes every one of them out.

*Operators (parameters 0 to 125):*

| No. | Operator | Parameter (the manual's name) | Range | Meaning | Packed byte, bits |
|---|---|---|---|---|---|
| 0 | Operator 6 | EG RATE 1 | 0 to 99 | Rate of the envelope's first segment, from LEVEL 4 to LEVEL 1; 0 slowest, 99 fastest (printed page 15) | 0, bits 0–6 |
| 1 | Operator 6 | EG RATE 2 | 0 to 99 | Rate of the second segment, LEVEL 1 to LEVEL 2 | 1, bits 0–6 |
| 2 | Operator 6 | EG RATE 3 | 0 to 99 | Rate of the third segment, LEVEL 2 to LEVEL 3 | 2, bits 0–6 |
| 3 | Operator 6 | EG RATE 4 | 0 to 99 | Rate of the fourth segment, after key off, LEVEL 3 to LEVEL 4 | 3, bits 0–6 |
| 4 | Operator 6 | EG LEVEL 1 | 0 to 99 | Level reached by the first segment; 0 no output, 99 most (printed page 15) | 4, bits 0–6 |
| 5 | Operator 6 | EG LEVEL 2 | 0 to 99 | Level reached by the second segment | 5, bits 0–6 |
| 6 | Operator 6 | EG LEVEL 3 | 0 to 99 | Level of the third segment, held while the key is down | 6, bits 0–6 |
| 7 | Operator 6 | EG LEVEL 4 | 0 to 99 | Level after key off, and the level the envelope starts from | 7, bits 0–6 |
| 8 | Operator 6 | KEYBOARD LEVEL SCALE BREAK POINT | 0 to 99 | The key about which level scaling turns, A−1 to C8 (printed page 16); 39 is C3, key 60 (TX7 manual, printed page 39, note *1; S7-31) | 8, bits 0–6 |
| 9 | Operator 6 | KEYBOARD LEVEL SCALE LEFT DEPTH | 0 to 99 | Depth of the scaling below the break point; 0 flat (printed page 16) | 9, bits 0–6 |
| 10 | Operator 6 | KEYBOARD LEVEL SCALE RIGHT DEPTH | 0 to 99 | Depth of the scaling above the break point | 10, bits 0–6 |
| 11 | Operator 6 | KEYBOARD LEVEL SCALE LEFT CURVE | 0 to 3 | Curve below the break point: one of −LIN, −EXP, +EXP, +LIN (printed page 16); 0 to 3 in that order (TX7 manual, printed page 39, note *2; S7-31) | 11, bits 0–1 |
| 12 | Operator 6 | KEYBOARD LEVEL SCALE RIGHT CURVE | 0 to 3 | Curve above the break point, coded as the left curve | 11, bits 2–3 |
| 13 | Operator 6 | KEYBOARD RATE SCALING | 0 to 7 | How much higher keys shorten the envelope (printed page 16) | 12, bits 0–2 |
| 14 | Operator 6 | MOD SENSITIVITY AMPLITUDE | 0 to 3 | This operator's sensitivity to amplitude modulation and to EG bias (printed pages 8 and 14) | 13, bits 0–1 |
| 15 | Operator 6 | OPERATOR KEY VELOCITY SENSITIVITY | 0 to 7 | How much velocity changes this operator's level; 0 none, 7 most (printed page 16) | 13, bits 2–4 |
| 16 | Operator 6 | OPERATOR OUTPUT LEVEL | 0 to 99 | The operator's overall level; 0 silent (printed page 16) | 14, bits 0–6 |
| 17 | Operator 6 | OSCILLATOR MODE | 0 to 1 | 0 frequency ratio, 1 fixed frequency in hertz (printed page 14; TX7 manual, printed page 39, note *3; S7-31) | 15, bit 0 |
| 18 | Operator 6 | OSCILLATOR FREQUENCY COARSE | 0 to 31 | In ratio mode 0.5 (value 0) and 1 to 31; in fixed mode 1, 10, 100 and 1,000 Hz for values 0, 1, 2 and 3, repeating every four values (printed pages 15 and 27; TX7 manual, printed page 39, note *4; S7-31) | 15, bits 1–5 |
| 19 | Operator 6 | OSCILLATOR FREQUENCY FINE | 0 to 99 | In ratio mode the coarse ratio times 1.00 to 1.99; in fixed mode times 1.000 to 9.772 (printed pages 15 and 27; TX7 manual, printed page 39, note *4) | 16, bits 0–6 |
| 20 | Operator 6 | DETUNE | 0 to 14 | Detune of −7 to +7; 7 is none (printed page 15; TX7 manual, printed page 39, note *5; S7-31) | 12, bits 3–6 |
| 21 | Operator 5 | EG RATE 1 | 0 to 99 | Rate of the envelope's first segment, from LEVEL 4 to LEVEL 1; 0 slowest, 99 fastest (printed page 15) | 17, bits 0–6 |
| 22 | Operator 5 | EG RATE 2 | 0 to 99 | Rate of the second segment, LEVEL 1 to LEVEL 2 | 18, bits 0–6 |
| 23 | Operator 5 | EG RATE 3 | 0 to 99 | Rate of the third segment, LEVEL 2 to LEVEL 3 | 19, bits 0–6 |
| 24 | Operator 5 | EG RATE 4 | 0 to 99 | Rate of the fourth segment, after key off, LEVEL 3 to LEVEL 4 | 20, bits 0–6 |
| 25 | Operator 5 | EG LEVEL 1 | 0 to 99 | Level reached by the first segment; 0 no output, 99 most (printed page 15) | 21, bits 0–6 |
| 26 | Operator 5 | EG LEVEL 2 | 0 to 99 | Level reached by the second segment | 22, bits 0–6 |
| 27 | Operator 5 | EG LEVEL 3 | 0 to 99 | Level of the third segment, held while the key is down | 23, bits 0–6 |
| 28 | Operator 5 | EG LEVEL 4 | 0 to 99 | Level after key off, and the level the envelope starts from | 24, bits 0–6 |
| 29 | Operator 5 | KEYBOARD LEVEL SCALE BREAK POINT | 0 to 99 | The key about which level scaling turns, A−1 to C8 (printed page 16); 39 is C3, key 60 (TX7 manual, printed page 39, note *1; S7-31) | 25, bits 0–6 |
| 30 | Operator 5 | KEYBOARD LEVEL SCALE LEFT DEPTH | 0 to 99 | Depth of the scaling below the break point; 0 flat (printed page 16) | 26, bits 0–6 |
| 31 | Operator 5 | KEYBOARD LEVEL SCALE RIGHT DEPTH | 0 to 99 | Depth of the scaling above the break point | 27, bits 0–6 |
| 32 | Operator 5 | KEYBOARD LEVEL SCALE LEFT CURVE | 0 to 3 | Curve below the break point: one of −LIN, −EXP, +EXP, +LIN (printed page 16); 0 to 3 in that order (TX7 manual, printed page 39, note *2; S7-31) | 28, bits 0–1 |
| 33 | Operator 5 | KEYBOARD LEVEL SCALE RIGHT CURVE | 0 to 3 | Curve above the break point, coded as the left curve | 28, bits 2–3 |
| 34 | Operator 5 | KEYBOARD RATE SCALING | 0 to 7 | How much higher keys shorten the envelope (printed page 16) | 29, bits 0–2 |
| 35 | Operator 5 | MOD SENSITIVITY AMPLITUDE | 0 to 3 | This operator's sensitivity to amplitude modulation and to EG bias (printed pages 8 and 14) | 30, bits 0–1 |
| 36 | Operator 5 | OPERATOR KEY VELOCITY SENSITIVITY | 0 to 7 | How much velocity changes this operator's level; 0 none, 7 most (printed page 16) | 30, bits 2–4 |
| 37 | Operator 5 | OPERATOR OUTPUT LEVEL | 0 to 99 | The operator's overall level; 0 silent (printed page 16) | 31, bits 0–6 |
| 38 | Operator 5 | OSCILLATOR MODE | 0 to 1 | 0 frequency ratio, 1 fixed frequency in hertz (printed page 14; TX7 manual, printed page 39, note *3; S7-31) | 32, bit 0 |
| 39 | Operator 5 | OSCILLATOR FREQUENCY COARSE | 0 to 31 | In ratio mode 0.5 (value 0) and 1 to 31; in fixed mode 1, 10, 100 and 1,000 Hz for values 0, 1, 2 and 3, repeating every four values (printed pages 15 and 27; TX7 manual, printed page 39, note *4; S7-31) | 32, bits 1–5 |
| 40 | Operator 5 | OSCILLATOR FREQUENCY FINE | 0 to 99 | In ratio mode the coarse ratio times 1.00 to 1.99; in fixed mode times 1.000 to 9.772 (printed pages 15 and 27; TX7 manual, printed page 39, note *4) | 33, bits 0–6 |
| 41 | Operator 5 | DETUNE | 0 to 14 | Detune of −7 to +7; 7 is none (printed page 15; TX7 manual, printed page 39, note *5; S7-31) | 29, bits 3–6 |
| 42 | Operator 4 | EG RATE 1 | 0 to 99 | Rate of the envelope's first segment, from LEVEL 4 to LEVEL 1; 0 slowest, 99 fastest (printed page 15) | 34, bits 0–6 |
| 43 | Operator 4 | EG RATE 2 | 0 to 99 | Rate of the second segment, LEVEL 1 to LEVEL 2 | 35, bits 0–6 |
| 44 | Operator 4 | EG RATE 3 | 0 to 99 | Rate of the third segment, LEVEL 2 to LEVEL 3 | 36, bits 0–6 |
| 45 | Operator 4 | EG RATE 4 | 0 to 99 | Rate of the fourth segment, after key off, LEVEL 3 to LEVEL 4 | 37, bits 0–6 |
| 46 | Operator 4 | EG LEVEL 1 | 0 to 99 | Level reached by the first segment; 0 no output, 99 most (printed page 15) | 38, bits 0–6 |
| 47 | Operator 4 | EG LEVEL 2 | 0 to 99 | Level reached by the second segment | 39, bits 0–6 |
| 48 | Operator 4 | EG LEVEL 3 | 0 to 99 | Level of the third segment, held while the key is down | 40, bits 0–6 |
| 49 | Operator 4 | EG LEVEL 4 | 0 to 99 | Level after key off, and the level the envelope starts from | 41, bits 0–6 |
| 50 | Operator 4 | KEYBOARD LEVEL SCALE BREAK POINT | 0 to 99 | The key about which level scaling turns, A−1 to C8 (printed page 16); 39 is C3, key 60 (TX7 manual, printed page 39, note *1; S7-31) | 42, bits 0–6 |
| 51 | Operator 4 | KEYBOARD LEVEL SCALE LEFT DEPTH | 0 to 99 | Depth of the scaling below the break point; 0 flat (printed page 16) | 43, bits 0–6 |
| 52 | Operator 4 | KEYBOARD LEVEL SCALE RIGHT DEPTH | 0 to 99 | Depth of the scaling above the break point | 44, bits 0–6 |
| 53 | Operator 4 | KEYBOARD LEVEL SCALE LEFT CURVE | 0 to 3 | Curve below the break point: one of −LIN, −EXP, +EXP, +LIN (printed page 16); 0 to 3 in that order (TX7 manual, printed page 39, note *2; S7-31) | 45, bits 0–1 |
| 54 | Operator 4 | KEYBOARD LEVEL SCALE RIGHT CURVE | 0 to 3 | Curve above the break point, coded as the left curve | 45, bits 2–3 |
| 55 | Operator 4 | KEYBOARD RATE SCALING | 0 to 7 | How much higher keys shorten the envelope (printed page 16) | 46, bits 0–2 |
| 56 | Operator 4 | MOD SENSITIVITY AMPLITUDE | 0 to 3 | This operator's sensitivity to amplitude modulation and to EG bias (printed pages 8 and 14) | 47, bits 0–1 |
| 57 | Operator 4 | OPERATOR KEY VELOCITY SENSITIVITY | 0 to 7 | How much velocity changes this operator's level; 0 none, 7 most (printed page 16) | 47, bits 2–4 |
| 58 | Operator 4 | OPERATOR OUTPUT LEVEL | 0 to 99 | The operator's overall level; 0 silent (printed page 16) | 48, bits 0–6 |
| 59 | Operator 4 | OSCILLATOR MODE | 0 to 1 | 0 frequency ratio, 1 fixed frequency in hertz (printed page 14; TX7 manual, printed page 39, note *3; S7-31) | 49, bit 0 |
| 60 | Operator 4 | OSCILLATOR FREQUENCY COARSE | 0 to 31 | In ratio mode 0.5 (value 0) and 1 to 31; in fixed mode 1, 10, 100 and 1,000 Hz for values 0, 1, 2 and 3, repeating every four values (printed pages 15 and 27; TX7 manual, printed page 39, note *4; S7-31) | 49, bits 1–5 |
| 61 | Operator 4 | OSCILLATOR FREQUENCY FINE | 0 to 99 | In ratio mode the coarse ratio times 1.00 to 1.99; in fixed mode times 1.000 to 9.772 (printed pages 15 and 27; TX7 manual, printed page 39, note *4) | 50, bits 0–6 |
| 62 | Operator 4 | DETUNE | 0 to 14 | Detune of −7 to +7; 7 is none (printed page 15; TX7 manual, printed page 39, note *5; S7-31) | 46, bits 3–6 |
| 63 | Operator 3 | EG RATE 1 | 0 to 99 | Rate of the envelope's first segment, from LEVEL 4 to LEVEL 1; 0 slowest, 99 fastest (printed page 15) | 51, bits 0–6 |
| 64 | Operator 3 | EG RATE 2 | 0 to 99 | Rate of the second segment, LEVEL 1 to LEVEL 2 | 52, bits 0–6 |
| 65 | Operator 3 | EG RATE 3 | 0 to 99 | Rate of the third segment, LEVEL 2 to LEVEL 3 | 53, bits 0–6 |
| 66 | Operator 3 | EG RATE 4 | 0 to 99 | Rate of the fourth segment, after key off, LEVEL 3 to LEVEL 4 | 54, bits 0–6 |
| 67 | Operator 3 | EG LEVEL 1 | 0 to 99 | Level reached by the first segment; 0 no output, 99 most (printed page 15) | 55, bits 0–6 |
| 68 | Operator 3 | EG LEVEL 2 | 0 to 99 | Level reached by the second segment | 56, bits 0–6 |
| 69 | Operator 3 | EG LEVEL 3 | 0 to 99 | Level of the third segment, held while the key is down | 57, bits 0–6 |
| 70 | Operator 3 | EG LEVEL 4 | 0 to 99 | Level after key off, and the level the envelope starts from | 58, bits 0–6 |
| 71 | Operator 3 | KEYBOARD LEVEL SCALE BREAK POINT | 0 to 99 | The key about which level scaling turns, A−1 to C8 (printed page 16); 39 is C3, key 60 (TX7 manual, printed page 39, note *1; S7-31) | 59, bits 0–6 |
| 72 | Operator 3 | KEYBOARD LEVEL SCALE LEFT DEPTH | 0 to 99 | Depth of the scaling below the break point; 0 flat (printed page 16) | 60, bits 0–6 |
| 73 | Operator 3 | KEYBOARD LEVEL SCALE RIGHT DEPTH | 0 to 99 | Depth of the scaling above the break point | 61, bits 0–6 |
| 74 | Operator 3 | KEYBOARD LEVEL SCALE LEFT CURVE | 0 to 3 | Curve below the break point: one of −LIN, −EXP, +EXP, +LIN (printed page 16); 0 to 3 in that order (TX7 manual, printed page 39, note *2; S7-31) | 62, bits 0–1 |
| 75 | Operator 3 | KEYBOARD LEVEL SCALE RIGHT CURVE | 0 to 3 | Curve above the break point, coded as the left curve | 62, bits 2–3 |
| 76 | Operator 3 | KEYBOARD RATE SCALING | 0 to 7 | How much higher keys shorten the envelope (printed page 16) | 63, bits 0–2 |
| 77 | Operator 3 | MOD SENSITIVITY AMPLITUDE | 0 to 3 | This operator's sensitivity to amplitude modulation and to EG bias (printed pages 8 and 14) | 64, bits 0–1 |
| 78 | Operator 3 | OPERATOR KEY VELOCITY SENSITIVITY | 0 to 7 | How much velocity changes this operator's level; 0 none, 7 most (printed page 16) | 64, bits 2–4 |
| 79 | Operator 3 | OPERATOR OUTPUT LEVEL | 0 to 99 | The operator's overall level; 0 silent (printed page 16) | 65, bits 0–6 |
| 80 | Operator 3 | OSCILLATOR MODE | 0 to 1 | 0 frequency ratio, 1 fixed frequency in hertz (printed page 14; TX7 manual, printed page 39, note *3; S7-31) | 66, bit 0 |
| 81 | Operator 3 | OSCILLATOR FREQUENCY COARSE | 0 to 31 | In ratio mode 0.5 (value 0) and 1 to 31; in fixed mode 1, 10, 100 and 1,000 Hz for values 0, 1, 2 and 3, repeating every four values (printed pages 15 and 27; TX7 manual, printed page 39, note *4; S7-31) | 66, bits 1–5 |
| 82 | Operator 3 | OSCILLATOR FREQUENCY FINE | 0 to 99 | In ratio mode the coarse ratio times 1.00 to 1.99; in fixed mode times 1.000 to 9.772 (printed pages 15 and 27; TX7 manual, printed page 39, note *4) | 67, bits 0–6 |
| 83 | Operator 3 | DETUNE | 0 to 14 | Detune of −7 to +7; 7 is none (printed page 15; TX7 manual, printed page 39, note *5; S7-31) | 63, bits 3–6 |
| 84 | Operator 2 | EG RATE 1 | 0 to 99 | Rate of the envelope's first segment, from LEVEL 4 to LEVEL 1; 0 slowest, 99 fastest (printed page 15) | 68, bits 0–6 |
| 85 | Operator 2 | EG RATE 2 | 0 to 99 | Rate of the second segment, LEVEL 1 to LEVEL 2 | 69, bits 0–6 |
| 86 | Operator 2 | EG RATE 3 | 0 to 99 | Rate of the third segment, LEVEL 2 to LEVEL 3 | 70, bits 0–6 |
| 87 | Operator 2 | EG RATE 4 | 0 to 99 | Rate of the fourth segment, after key off, LEVEL 3 to LEVEL 4 | 71, bits 0–6 |
| 88 | Operator 2 | EG LEVEL 1 | 0 to 99 | Level reached by the first segment; 0 no output, 99 most (printed page 15) | 72, bits 0–6 |
| 89 | Operator 2 | EG LEVEL 2 | 0 to 99 | Level reached by the second segment | 73, bits 0–6 |
| 90 | Operator 2 | EG LEVEL 3 | 0 to 99 | Level of the third segment, held while the key is down | 74, bits 0–6 |
| 91 | Operator 2 | EG LEVEL 4 | 0 to 99 | Level after key off, and the level the envelope starts from | 75, bits 0–6 |
| 92 | Operator 2 | KEYBOARD LEVEL SCALE BREAK POINT | 0 to 99 | The key about which level scaling turns, A−1 to C8 (printed page 16); 39 is C3, key 60 (TX7 manual, printed page 39, note *1; S7-31) | 76, bits 0–6 |
| 93 | Operator 2 | KEYBOARD LEVEL SCALE LEFT DEPTH | 0 to 99 | Depth of the scaling below the break point; 0 flat (printed page 16) | 77, bits 0–6 |
| 94 | Operator 2 | KEYBOARD LEVEL SCALE RIGHT DEPTH | 0 to 99 | Depth of the scaling above the break point | 78, bits 0–6 |
| 95 | Operator 2 | KEYBOARD LEVEL SCALE LEFT CURVE | 0 to 3 | Curve below the break point: one of −LIN, −EXP, +EXP, +LIN (printed page 16); 0 to 3 in that order (TX7 manual, printed page 39, note *2; S7-31) | 79, bits 0–1 |
| 96 | Operator 2 | KEYBOARD LEVEL SCALE RIGHT CURVE | 0 to 3 | Curve above the break point, coded as the left curve | 79, bits 2–3 |
| 97 | Operator 2 | KEYBOARD RATE SCALING | 0 to 7 | How much higher keys shorten the envelope (printed page 16) | 80, bits 0–2 |
| 98 | Operator 2 | MOD SENSITIVITY AMPLITUDE | 0 to 3 | This operator's sensitivity to amplitude modulation and to EG bias (printed pages 8 and 14) | 81, bits 0–1 |
| 99 | Operator 2 | OPERATOR KEY VELOCITY SENSITIVITY | 0 to 7 | How much velocity changes this operator's level; 0 none, 7 most (printed page 16) | 81, bits 2–4 |
| 100 | Operator 2 | OPERATOR OUTPUT LEVEL | 0 to 99 | The operator's overall level; 0 silent (printed page 16) | 82, bits 0–6 |
| 101 | Operator 2 | OSCILLATOR MODE | 0 to 1 | 0 frequency ratio, 1 fixed frequency in hertz (printed page 14; TX7 manual, printed page 39, note *3; S7-31) | 83, bit 0 |
| 102 | Operator 2 | OSCILLATOR FREQUENCY COARSE | 0 to 31 | In ratio mode 0.5 (value 0) and 1 to 31; in fixed mode 1, 10, 100 and 1,000 Hz for values 0, 1, 2 and 3, repeating every four values (printed pages 15 and 27; TX7 manual, printed page 39, note *4; S7-31) | 83, bits 1–5 |
| 103 | Operator 2 | OSCILLATOR FREQUENCY FINE | 0 to 99 | In ratio mode the coarse ratio times 1.00 to 1.99; in fixed mode times 1.000 to 9.772 (printed pages 15 and 27; TX7 manual, printed page 39, note *4) | 84, bits 0–6 |
| 104 | Operator 2 | DETUNE | 0 to 14 | Detune of −7 to +7; 7 is none (printed page 15; TX7 manual, printed page 39, note *5; S7-31) | 80, bits 3–6 |
| 105 | Operator 1 | EG RATE 1 | 0 to 99 | Rate of the envelope's first segment, from LEVEL 4 to LEVEL 1; 0 slowest, 99 fastest (printed page 15) | 85, bits 0–6 |
| 106 | Operator 1 | EG RATE 2 | 0 to 99 | Rate of the second segment, LEVEL 1 to LEVEL 2 | 86, bits 0–6 |
| 107 | Operator 1 | EG RATE 3 | 0 to 99 | Rate of the third segment, LEVEL 2 to LEVEL 3 | 87, bits 0–6 |
| 108 | Operator 1 | EG RATE 4 | 0 to 99 | Rate of the fourth segment, after key off, LEVEL 3 to LEVEL 4 | 88, bits 0–6 |
| 109 | Operator 1 | EG LEVEL 1 | 0 to 99 | Level reached by the first segment; 0 no output, 99 most (printed page 15) | 89, bits 0–6 |
| 110 | Operator 1 | EG LEVEL 2 | 0 to 99 | Level reached by the second segment | 90, bits 0–6 |
| 111 | Operator 1 | EG LEVEL 3 | 0 to 99 | Level of the third segment, held while the key is down | 91, bits 0–6 |
| 112 | Operator 1 | EG LEVEL 4 | 0 to 99 | Level after key off, and the level the envelope starts from | 92, bits 0–6 |
| 113 | Operator 1 | KEYBOARD LEVEL SCALE BREAK POINT | 0 to 99 | The key about which level scaling turns, A−1 to C8 (printed page 16); 39 is C3, key 60 (TX7 manual, printed page 39, note *1; S7-31) | 93, bits 0–6 |
| 114 | Operator 1 | KEYBOARD LEVEL SCALE LEFT DEPTH | 0 to 99 | Depth of the scaling below the break point; 0 flat (printed page 16) | 94, bits 0–6 |
| 115 | Operator 1 | KEYBOARD LEVEL SCALE RIGHT DEPTH | 0 to 99 | Depth of the scaling above the break point | 95, bits 0–6 |
| 116 | Operator 1 | KEYBOARD LEVEL SCALE LEFT CURVE | 0 to 3 | Curve below the break point: one of −LIN, −EXP, +EXP, +LIN (printed page 16); 0 to 3 in that order (TX7 manual, printed page 39, note *2; S7-31) | 96, bits 0–1 |
| 117 | Operator 1 | KEYBOARD LEVEL SCALE RIGHT CURVE | 0 to 3 | Curve above the break point, coded as the left curve | 96, bits 2–3 |
| 118 | Operator 1 | KEYBOARD RATE SCALING | 0 to 7 | How much higher keys shorten the envelope (printed page 16) | 97, bits 0–2 |
| 119 | Operator 1 | MOD SENSITIVITY AMPLITUDE | 0 to 3 | This operator's sensitivity to amplitude modulation and to EG bias (printed pages 8 and 14) | 98, bits 0–1 |
| 120 | Operator 1 | OPERATOR KEY VELOCITY SENSITIVITY | 0 to 7 | How much velocity changes this operator's level; 0 none, 7 most (printed page 16) | 98, bits 2–4 |
| 121 | Operator 1 | OPERATOR OUTPUT LEVEL | 0 to 99 | The operator's overall level; 0 silent (printed page 16) | 99, bits 0–6 |
| 122 | Operator 1 | OSCILLATOR MODE | 0 to 1 | 0 frequency ratio, 1 fixed frequency in hertz (printed page 14; TX7 manual, printed page 39, note *3; S7-31) | 100, bit 0 |
| 123 | Operator 1 | OSCILLATOR FREQUENCY COARSE | 0 to 31 | In ratio mode 0.5 (value 0) and 1 to 31; in fixed mode 1, 10, 100 and 1,000 Hz for values 0, 1, 2 and 3, repeating every four values (printed pages 15 and 27; TX7 manual, printed page 39, note *4; S7-31) | 100, bits 1–5 |
| 124 | Operator 1 | OSCILLATOR FREQUENCY FINE | 0 to 99 | In ratio mode the coarse ratio times 1.00 to 1.99; in fixed mode times 1.000 to 9.772 (printed pages 15 and 27; TX7 manual, printed page 39, note *4) | 101, bits 0–6 |
| 125 | Operator 1 | DETUNE | 0 to 14 | Detune of −7 to +7; 7 is none (printed page 15; TX7 manual, printed page 39, note *5; S7-31) | 97, bits 3–6 |

*The voice (parameters 126 to 155):*

| No. | Parameter (the manual's name) | Range | Meaning | Packed byte, bits |
|---|---|---|---|---|
| 126 | PITCH EG RATE 1 | 0 to 99 | Rate of the pitch envelope's first segment; 0 slowest, 99 fastest (page 17) | 102, bits 0–6 |
| 127 | PITCH EG RATE 2 | 0 to 99 | Rate of its second segment | 103, bits 0–6 |
| 128 | PITCH EG RATE 3 | 0 to 99 | Rate of its third segment | 104, bits 0–6 |
| 129 | PITCH EG RATE 4 | 0 to 99 | Rate of its fourth segment, after key off | 105, bits 0–6 |
| 130 | PITCH EG LEVEL 1 | 0 to 99 | Pitch reached by the first segment: 50 the key's own pitch, 99 four octaves up, 0 four octaves down (page 17) | 106, bits 0–6 |
| 131 | PITCH EG LEVEL 2 | 0 to 99 | Pitch reached by the second segment | 107, bits 0–6 |
| 132 | PITCH EG LEVEL 3 | 0 to 99 | Pitch held while the key is down | 108, bits 0–6 |
| 133 | PITCH EG LEVEL 4 | 0 to 99 | Pitch after key off, and the pitch the envelope starts from | 109, bits 0–6 |
| 134 | ALGORITHM SELECT | 0 to 31 | Which of the 32 algorithms joins the operators; value 0 is the algorithm the instrument shows as 1 (derived; S7-31) | 110, bits 0–4 |
| 135 | FEED BACK | 0 to 7 | Feedback of the algorithm's feedback operator; 0 none (page 13) | 111, bits 0–2 |
| 136 | OSCILLATOR SYNC | 0 to 1 | 1: every operator starts from phase 0 when a key goes down; 0: its phase carries on from the note before (page 14) | 111, bit 3 |
| 137 | LFO SPEED | 0 to 99 | Speed of the low-frequency oscillator; 0 slowest (page 13) | 112, bits 0–6 |
| 138 | LFO DELAY | 0 to 99 | Delay from key down to the oscillator's modulation; 0 none (page 13) | 113, bits 0–6 |
| 139 | LFO PMD | 0 to 99 | Pitch modulation depth, independent of the controllers (page 13) | 114, bits 0–6 |
| 140 | LFO AMD | 0 to 99 | Amplitude modulation depth, independent of the controllers (page 13) | 115, bits 0–6 |
| 141 | LFO SYNC | 0 to 1 | 1: the oscillator's waveform starts at the same point when a key is pressed; 0: it runs free (page 13) | 116, bit 0 |
| 142 | LFO WAVE | 0 to 5 (TX7 manual, printed page 38; DX7 II manual, printed page Add-8; the DX7 manual's table says 0 to 4, a misprint; S7-31) | 0 triangle, 1 sawtooth down, 2 sawtooth up, 3 square, 4 sine, 5 sample and hold (pages 13 and 27; TX7 manual, printed page 39, note *6; S7-31) | 116, bits 1–3 |
| 143 | MOD SENSITIVITY PITCH | 0 to 7 | Sensitivity of every operator's pitch to pitch modulation; 0 none (page 14) | 116, bits 4–6 |
| 144 | TRANSPOSE | 0 to 48 | The keys moved −24 to +24 semitones; 24 none (page 17; TX7 manual, printed page 38, "Concert pitch at 24"; S7-8) | 117, bits 0–6 |
| 145 | VOICE NAME 1 | ASCII | First character of the name (S7-32) | 118, bits 0–6 |
| 146 | VOICE NAME 2 | ASCII | Second character | 119, bits 0–6 |
| 147 | VOICE NAME 3 | ASCII | Third character | 120, bits 0–6 |
| 148 | VOICE NAME 4 | ASCII | Fourth character | 121, bits 0–6 |
| 149 | VOICE NAME 5 | ASCII | Fifth character | 122, bits 0–6 |
| 150 | VOICE NAME 6 | ASCII | Sixth character | 123, bits 0–6 |
| 151 | VOICE NAME 7 | ASCII | Seventh character | 124, bits 0–6 |
| 152 | VOICE NAME 8 | ASCII | Eighth character | 125, bits 0–6 |
| 153 | VOICE NAME 9 | ASCII | Ninth character | 126, bits 0–6 |
| 154 | VOICE NAME 10 | ASCII | Tenth character | 127, bits 0–6 |
| 155 | OPERATOR ON/OFF | 0 to 63 | Which operators sound: bit 5 operator 1, bit 4 operator 2, bit 3 operator 3, bit 2 operator 4, bit 1 operator 5, bit 0 operator 6; 1 on, 0 off; bit 6 is 0 (page 31; TX7 manual, printed page 39, note *7; DX7 II manual, printed page Add-8; S7-30) | Not in the packed voice |

- Reason: These are the adopted interface's voice parameters, every one, with the manual's names, numbers and ranges, and the meaning the manual's edit-mode pages give each. The TX7 manual lists the same parameters with the same numbers and ranges (and a parameter 156, OPERATOR SELECT, 0 to 5, which chooses the operator a panel edits; the DX7 manual's table ends at 155, and synth7 counts 156 as ignored, S7-43).
- Source: The manual, page 31 (the table "g=0 : DX 共通 Voice parameter", whose numbers and ranges are these), pages 12 to 17 (the meanings), page 27 (the specifications), page 28 (the voice data list). The TX7 manual, printed pages 38 and 39 (section 4-1 and its notes *1 to *8). The DX7 II manual, printed page Add-8 (section 5-1). The packed column: section 10, from the TX7 manual, printed page 44.
- Verification: A test holds the table as data and checks, for every parameter 0 to 155, that a parameter change sets exactly that parameter of the part's current voice; that the single-voice dump of S7-38 carries parameters 0 to 154 at bytes 6 to 160; and that packing and unpacking (S7-48) give each back.

**S7-29. Ranges and refusal.** A voice MUST be refused whole when any of its parameters 0 to 154 is above the top of its range in S7-28, except the name's (S7-32). A refused voice MUST NOT reach the sound engine; what takes its place is said where the voice arrives (S7-40, S7-42, S7-45). A parameter change whose data is above the parameter's range MUST be counted as ignored and change nothing.
- Reason: Every value the engine meets must be one the instrument gives its parameter, so that no value from outside indexes a table out of its bounds (DEVELOPMENT.md sections 6 and 14). The range check is built today for the packed voice (`Patch::new`).
- Source: The manual, page 31 (each range). synth7's source, `patch.rs` (`Patch::new`, `PatchError`).
- Verification: A test sets each parameter in turn to its top value and to one above it, checking acceptance and refusal, for a single-voice dump, a 32-voice dump and a parameter change.

**S7-30. The operator switch, voice parameter 155.** A parameter change of voice parameter 155 MUST set which operators of the part's current voice sound, bit 5 of the data being operator 1, bit 4 operator 2, bit 3 operator 3, bit 2 operator 4, bit 1 operator 5 and bit 0 operator 6, a 1 being on. An operator switched off MUST contribute nothing to the sound and MUST modulate nothing. The switch MUST NOT be stored in any bank or dump, and a program change or a single-voice dump MUST set it to all six on (data 63).
- Reason: The adopted interface, as all three of the maker's manuals state it: the DX7 manual, "155 OPERATOR ON/OFF 0=OFF, 1=ON", with the bits drawn "D6 D5 D4 D3 D2 D1 D0 / 0 OP1 OP2 OP3 OP4 OP5 OP6" (page 31); the TX7 manual, "OPERATOR ON OFF", bit b5 OP1, b4 OP2, b3 OP3, b2 OP4, b1 OP5, b0 OP6, "Bit Map "0"...OFF "1"...ON" (printed page 39, note *7); the DX7 II manual, "OPERATOR ENABLE B5:OP1,..,B0:OP6" (printed page Add-8). "OPERATOR ON-OFF data is not stored in memory" (DX7 manual, page 16). Today synth7 holds the switch with bit 0 as operator 1 (`patch.rs`, `operators_on`), the other way round from the manuals; no message sets it today, so nothing on the wire changes, but the code's order must follow the manuals' when the parameter change is built (section 17).
- Source: The manual, pages 12, 16 and 31. The TX7 manual, printed pages 38 and 39. The DX7 II manual, printed page Add-8.
- Verification: A test sends parameter 155 with data 32 (operator 1 alone) and data 1 (operator 6 alone) on a voice whose operators are distinguishable and checks which sounds; a test checks that a program change after it sounds all six.

**S7-31. Coded values.** Where a parameter's number codes a choice, synth7 MUST read it as follows. Each row says which manual states the coding, or that it is derived.

| Parameter | Values | Meaning | Where it comes from |
|---|---|---|---|
| KEYBOARD LEVEL SCALE LEFT CURVE and RIGHT CURVE (11 and 12 of each operator) | 0, 1, 2, 3 | 0 −LIN, 1 −EXP, 2 +EXP, 3 +LIN | The four curves are the DX7 manual's (page 16, figure); which number is which is stated by the TX7 manual ("KEYBOARD LEVEL SCALING CURVE": 0 −LIN, 1 −EXP, 2 +EXP, 3 +LIN, printed page 39, note *2). It is what is built (`patch.rs`: "0 linear fall, 1 exponential fall, 2 exponential rise, 3 linear rise"). |
| KEYBOARD LEVEL SCALE BREAK POINT (8 of each operator) | 0 to 99 | One key a step: value `v` is MIDI key `v + 21`, from A−1 (0, key 21) to C8 (99, key 120); 39 is C3, key 60 | The range of keys is the DX7 manual's ("anywhere between A−1 and C8", page 16; "A−1 ~ C8", page 27). The TX7 manual tables the values against MIDI note numbers: 0 is 21, 1 is 22, 2 is 23, 3 is 24, 4 is 25, 5 is 26, 15 is 36, 27 is 48, 39 is 60, 51 is 72, 63 is 84, 75 is 96, 87 is 108, 99 is 120 (printed page 39, note *1). |
| OSCILLATOR MODE (17 of each operator) | 0, 1 | 0 ratio, 1 fixed frequency | "“0” ............ frequency ratio, “1” ............ fixed frequency" (TX7 manual, printed page 39, note *3). The DX7 manual's −1 key "sets the operators to the FREQUENCY (RATIO) mode", its +1 key "sets the FIXED FREQ (HZ) mode" (page 14), which agrees. |
| OSCILLATOR FREQUENCY COARSE (18 of each operator) | 0 to 31 | In ratio mode: 0 a ratio of 0.5, `n` from 1 to 31 a ratio of `n`. In fixed mode: 1, 10, 100 and 1,000 Hz for values 0, 1, 2 and 3, the four repeating every four values (4 is 1 Hz, 7 is 1,000 Hz, 31 is 1,000 Hz) | The TX7 manual's tables "FREQUENCY COARSE FINE": for frequency ratio with FINE 0, coarse 0 is 0.5, 1 is 1, 2 is 2, 3 is 3, 10 is 10, 30 is 30, 31 is 31; for fixed frequency with FINE 0, coarse 0 is 1 Hz, 1 is 10, 2 is 100, 3 is 1000, 4 is 1, 5 is 10, 6 is 100, 7 is 1000, 31 is 1000 (printed page 39, note *4). The DX7 manual: "COARSE adjustment is possible in four steps—1, 10, 100 and 1000" (page 15). Whether what is built (the parameter layer translated under DEC-6420) repeats the four steps so is to be checked against this table when synth7 is built to this document (section 17). |
| OSCILLATOR FREQUENCY FINE (19 of each operator) | 0 to 99 | In ratio mode the coarse ratio times `1 + v ÷ 100` (with coarse 1: 1.00 to 1.99). In fixed mode the coarse frequency times 1.000 (0) to 9.772 (99) | The TX7 manual: with coarse 1, fine 0 is 1.00, 1 is 1.01, 2 is 1.02, 3 is 1.03, 10 is 1.10, 50 is 1.50, 99 is 1.99; with coarse 0 in fixed mode, fine 0 is 1.000 Hz, 1 is 1.023, 2 is 1.047, 3 is 1.072, 4 is 1.096, 5 is 1.122, 10 is 1.259, 20 is 1.585, 50 is 3.162, 99 is 9.772 (printed page 39, note *4). The fixed-mode values are `10^(v ÷ 100)` to the four places the table prints; that law is derived from the table. |
| DETUNE (20 of each operator) | 0 to 14 | −7 to +7; 7 none | The TX7 manual: 0 is −7, 1 is −6, and so on by one to 14, which is +7 (printed page 39, note *5). The DX7 manual: range "0 ~ 14" (page 31), meaning "−7 to +7" (page 15). |
| ALGORITHM SELECT (134) | 0 to 31 | The algorithms the panel numbers 1 to 32 | Range "0 ~ 31" (DX7 manual, page 31; TX7 manual, printed page 38); the panel shows "ALG 4" and algorithms 1 to 32 (pages 11 and 12). That value 0 is algorithm 1 is derived; no filed manual states it. |
| LFO WAVE (142) | 0 to 5 | 0 triangle, 1 sawtooth down, 2 sawtooth up, 3 square, 4 sine, 5 sample and hold | The TX7 manual: range "0 ~ 5" (printed page 38) and the six waves in this order, 0 "TRIANGLE" to 5 "SAMPLE/HOLD" (printed page 39, note *6). The DX7 II manual: "LFW 0 - 5" (printed page Add-8). The DX7 manual's own pages 13 and 27 list the same six in the same order ("Any of the six waveforms shown below can be selected", page 13); its table's "0 ~ 4" (page 31) is a misprint. As built. |
| TRANSPOSE (144) | 0 to 48 | −24 to +24 semitones; 24 none | Range "0 ~ 48" (page 31), "±2 octaves", "C3 as standard" (pages 17 and 27); "Concert pitch at 24" (TX7 manual, printed page 38). |
| OSCILLATOR SYNC (136), LFO SYNC (141) | 0, 1 | Off, on | "ON/OFF" (page 27), "0 ~ 1" (page 31; TX7 manual, printed page 38, "OSCILLATOR KEY SYNC" and "LFO KEY SYNC"). That 1 is on is derived; no filed manual states it. The maker's initial voice has both at 1 (DX7 II manual, printed page Add-8). |

- Reason: A voice's numbers mean nothing until each coding is fixed, and each must be fixed once.
- Source: As each row says.
- Verification: A test for each row plays a voice that differs only in that parameter and checks the stated meaning (the curve's direction and shape, the break point's key, the ratio and the fixed frequency for every coarse value 0 to 31 and the fine values the TX7 manual tables, the detune's sign, the algorithm's carriers, the waveform's shape, the transpose's semitones, the sync's phase).

**S7-32. The voice name.** Parameters 145 to 154 MUST be taken as ten bytes of a name, each 0 to 127, and MUST NOT change the sound. A receiver MUST NOT refuse a voice for its name. A sender SHOULD write only the characters the instrument modelled can enter: the digits 1 to 0, the capital letters A to Z, the hyphen, the full stop and the space.
- Reason: The name is a label: "Name for original voices can be specified using up to ten characters … The available characters are 1 through 0, A through Z, −, a period and a space" (page 17); the table says "ASCII" (page 31). Voices made by other tools carry other characters, and refusing them would refuse their sound for a label.
- Source: The manual, pages 17, 25, 27 and 31. synth7's source, `patch.rs` ("The name is not checked").
- Verification: A test sends a voice whose name holds bytes 0 to 9 and 127 and checks it accepted and sounding identical to the same voice named with spaces.

## 8. The function parameters

**S7-33. The function parameters.** Each part MUST hold these fourteen function parameters, set by the parameter change message's group 2 (S7-43) on the part's channel, and MUST act on each as the column "What synth7 must do" says. "Today" is synth7 on 18 November 2026.

| No. | The manual's name (page 31) | Range | Meaning (the manual, pages 6 to 8) | Today | What synth7 must do |
|---|---|---|---|---|---|
| 64 | MONO/POLY MODE CHANGE | 0 to 1 | 0 poly, 1 mono ("Press the DATA ENTRY −1 key for polyphonic operation, and the +1 key for monophonic operation", page 6; the coding is derived from the keys) | Always poly | S7-25, S7-26 |
| 65 | PITCH BEND RANGE | 0 to 12 | The bend at either end of the wheel, in semitones; 0 none, 12 ±1,200 cents | Fixed at 2 | S7-9 |
| 66 | PITCH BEND STEP | 0 to 12 | 0 smooth; `s` bends in steps of `s` semitones | Smooth | S7-9 |
| 67 | PORTAMENTO MODE | 0 to 1 | Poly: 0 retain, 1 follow (TX7 manual, printed page 40, note *1); mono: 0 fingered, 1 full time (derived from the −1 and +1 keys, page 6) | None | S7-27 |
| 68 | PORTAMENTO GLISSANDO | 0 to 1 | 0 portamento, 1 glissando ("When it is OFF a normal portamento effect is produced") | None | S7-27 |
| 69 | PORTAMENTO TIME | 0 to 99 | 0 no effect, 99 the slowest | None | S7-27; also set by controller 5 (S7-14) |
| 70 | MODULATION WHEEL RANGE | 0 to 99 | 0 no effect, 99 the most | As if 99 | S7-36 |
| 71 | MODULATION WHEEL ASSIGN | 0 to 7 | Which of PITCH, AMPLITUDE and EG BIAS the wheel acts on: bit 0 PITCH, bit 1 AMPLITUDE, bit 2 EG BIAS (S7-34) | As if PITCH alone | S7-36 |
| 72 | FOOT CONTROLLER RANGE | 0 to 99 | As 70, for the foot controller | None | S7-36 |
| 73 | FOOT CONTROLLER ASSIGN | 0 to 7 | As 71 | None | S7-36 |
| 74 | BREATH CONTROLLER RANGE | 0 to 99 | As 70, for the breath controller | None | S7-36 |
| 75 | BREATH CONTROLLER ASSIGN | 0 to 7 | As 71 | None | S7-36 |
| 76 | AFTER TOUCH RANGE | 0 to 99 | As 70, for after touch | None | S7-36 |
| 77 | AFTER TOUCH ASSIGN | 0 to 7 | As 71 | None | S7-36 |

The instrument modelled has other settings in its function mode that are not in this table and that no parameter change reaches (page 6 and 7, page 27): MASTER TUNE ADJ, EDIT RECALL, VOICE INIT, CARTRIDGE FORMATTING, BATTERY CHECK, CARTRIDGE SAVE and LOAD, MIDI CHANNEL, SYSTEM INFORMATION and MIDI TRANSMIT. They are listed in section 14.

A function parameter MUST apply to the part's notes from the next block onwards, including the notes already sounding (a range or an assign changed under a held note changes its modulation; a mode changed from poly to mono releases the part's notes but the one most recently pressed).
- Reason: These are the function parameters of the adopted interface, every one, and each is a setting of one instrument, so each is a setting of one part (S7-2). The TX7 manual lists the same fourteen with the same numbers and ranges in its function parameter change (printed page 41, section 4-3), and adds that it keeps the four RANGE parameters (70, 72, 74, 76, which it calls SENSITIVITY) "on a scale of 0 ~ 15" though it receives 0 to 99 (note *1); that is the TX7's memory, not the DX7's interface, and synth7 holds the 0 to 99 the DX7 manual gives. That a change applies to sounding notes is how a performer changes them on the instrument, and is not stated otherwise in the source; what a change of mode does to held notes is not stated in the source and is NeoTeletext's own (section 15 item 12).
- Source: The manual, pages 6 to 8, 26, 27 and 31. The TX7 manual, printed pages 40 and 41.
- Verification: A test sends every function parameter at its lowest and highest value on part 3 and checks that part 3's behaviour changes as its requirement says and part 4's does not; a test sends each one value above its range and checks it counted as ignored.

**S7-34. The assign bits.** In the data of function parameters 71, 73, 75 and 77, bit 0 MUST be PITCH, bit 1 AMPLITUDE and bit 2 EG BIAS, a 1 being on.
- Reason: Each assign is three switches, "PITCH ON/OFF, AMPLITUDE ON/OFF, EG BIAS ON/OFF" (DX7 manual, page 27), and the range 0 to 7 (page 31) is three bits. The DX7 manual does not say which bit is which; the TX7 manual does, for the same four assigns in its performance parameter change: "EFFECT ASSIGN", bit b2 EG BIAS, b1 AMPLITUDE, b0 PITCH (printed page 40, section 4-2, note *2). Its function parameter change lists the same assigns at 71, 73, 75 and 77, 0 to 7, without repeating the note (printed page 41, section 4-3); that the one coding serves both lists is taken (section 15 item 13).
- Source: The manual, pages 7, 8, 27 and 31. The TX7 manual, printed pages 40 and 41.
- Verification: A test sets each assign to 1, 2 and 4 and checks that the controller acts on pitch alone, on amplitude alone and on bias alone.

**S7-35. The function parameters a part starts with.** Before any parameter change reaches it, a part's function parameters MUST be: 64 MONO/POLY 0 (poly); 65 PITCH BEND RANGE 2; 66 PITCH BEND STEP 0; 67 PORTAMENTO MODE 0; 68 GLISSANDO 0; 69 PORTAMENTO TIME 0; 70 MODULATION WHEEL RANGE 99; 71 MODULATION WHEEL ASSIGN 1 (PITCH); 72 FOOT CONTROLLER RANGE 0; 73 FOOT CONTROLLER ASSIGN 0; 74 BREATH CONTROLLER RANGE 0; 75 BREATH CONTROLLER ASSIGN 0; 76 AFTER TOUCH RANGE 0; 77 AFTER TOUCH ASSIGN 0. A sound that starts again, and controller 121, MUST NOT change them; a new sound's parts start from these.
- Reason: A part must behave definitely before any parameter change. The instrument modelled keeps whatever was last set and has no stated factory value (page 6, "memorized and maintained even when power to the DX is cut off"); its own voice data list shows one example with the wheel at range 60 and PITCH on and the others' ranges at 99 or 60 with everything off (page 28), which is one owner's sheet, not a default. These values keep what synth7 does today (a bend of 2 semitones, a wheel that adds vibrato as a depth of 99, no other controller), so no existing sound changes. They are NeoTeletext's own (section 15 item 14).
- Source: Not stated in the source. synth7's source, `rack.rs` (`PITCH_BEND_SEMITONES`) and `note.rs` (the wheel).
- Verification: A test checks a new part's fourteen values; the existing tests of the bend and the wheel continue to pass with no parameter change sent.

**S7-36. How the four controllers act.** For each of the four controllers (the modulation wheel, controller 1; the foot controller, controller 4; the breath controller, controller 2; after touch, channel pressure), let `c` be its value divided by 127 and `r` its RANGE divided by 99. Then, for the part's notes:
1. With PITCH on, the controller MUST add `c × r` of the full pitch modulation depth to the voice's LFO PMD (parameter 139), the sum not exceeding the full depth, before the voice's MOD SENSITIVITY PITCH (parameter 143) scales it; the controller's share MUST NOT wait for the LFO DELAY.
2. With AMPLITUDE on, the controller MUST add `c × r` of the full amplitude modulation depth to the voice's LFO AMD (parameter 140) in the same way, before each operator's MOD SENSITIVITY AMPLITUDE scales it.
3. With EG BIAS on, the controller MUST attenuate each operator by `(1 − c) × r` of the attenuation that the full amplitude modulation depth gives that operator at the deepest point of the oscillator's swing, at that operator's MOD SENSITIVITY AMPLITUDE: at the controller's top no attenuation, at its bottom the most. An operator whose sensitivity is 0 is not attenuated.
4. Several controllers acting on the same destination MUST add, the sum of their shares not exceeding the full depth.
- Reason: The adopted interface's block diagram (page 26) draws each controller's RANGE feeding PITCH, AMPLITUDE and EG BIAS switches, the first two joining the oscillator's PMD and AMD paths before the voice's MOD SENSITIVITY, and EG BIAS joining the amplitude path without the oscillator. "When EG BIAS is ON, volume or brilliance (wow) variation effects can be added with the controllers by varying the level of each operator's envelope generator. MOD. SENSITIVITY (AMPLITUDE) is used to set the sensitivity … In some cases, if the carrier sensitivity is maximum and the controller is set to its minimum, no sound will be produced" (page 8): the bias attenuates most at the controller's minimum. "These parameters will have no effect if the PITCH MODULATION SENSITIVITY or the AMPLITUDE MODULATION SENSITIVITY of the voice used are zero" (page 8). The exact laws (that shares are linear in `c` and `r`, that they add, the full depths) are not stated in the source; the linear law is NeoTeletext's own, the full pitch depth is what is built for the wheel today, and the full amplitude depth is today's amplitude modulation (`note.rs`, `AMP_MOD_SHIFTS`, own choice) (section 15 item 15).
- Source: The manual, pages 7, 8 and 26. synth7's source, `note.rs`.
- Verification: For each controller and each assign bit, a test holds a note on a voice with the relevant sensitivity at its top and PMD and AMD 0, and checks: no modulation at `c` 0 or `r` 0 (pitch and amplitude); the depth at `c` and `r` both 1 equal to that of PMD or AMD 99 alone; for EG bias, silence of a carrier with sensitivity 3 at `c` 0 and `r` 1 and its full level at `c` 1; and that with sensitivity 0 nothing changes.

## 9. System exclusive

**S7-37. Which system exclusive messages synth7 takes.** synth7 MUST take exactly three system exclusive messages, all with the identification number 67 (`43` hexadecimal) in their second byte: the single-voice dump (S7-38) and the parameter change (S7-43), which a block carries as events and synth7 acts on where they stand, and the 32-voice dump (S7-41), which travels only as a bank (S7-42). The third byte's high nibble is the sub-status (`0sss`, bits 4 to 6), its low nibble the channel. Every other system exclusive message, including one of identification 67 with another sub-status, format or group, MUST be counted as ignored and change nothing, whatever its length; a 32-voice dump found in a block is longer than a block's system exclusive event may be (`midi-architecture.md`, MIDI-28) and is passed over and counted as a content error (MIDI-34).
- Reason: These three are the adopted interface's "System Information" (page 21) and are the messages DEC-6460 adopts. A single-voice dump is 162 bytes after `F0` and a parameter change 6, both within the 256 bytes a block's system exclusive event may hold (MIDI-28); the 32-voice dump is 4,103 bytes after `F0`, which no block can hold, and `midi-architecture.md` carries a message so long only in a bank (MIDI-50, MIDI-51). The instrument modelled also defines a request for "the performance data of the DX1 A-side" (page 32, "2-2-5"), which belongs to another instrument, and transmits active sensing (S7-24).
- Source: The manual, pages 21, 22 and 30 to 32. DEC-6460. `midi-architecture.md`, MIDI-28, MIDI-34, MIDI-50 and MIDI-51.
- Verification: A test sends messages of identification 67 with every sub-status 0 to 7 and every format 0 to 127, and messages of other identifications, and checks that only the three act and every other is counted.

**S7-38. The single-voice dump: 163 bytes.** A single-voice dump MUST be exactly these 163 bytes:

| Byte | Bits | Value | Meaning (the manual, page 30, "1-2-2. Bulk data of 1 voice") |
|---|---|---|---|
| 0 | `11110000` | `F0` | Status byte: system exclusive |
| 1 | `0iiiiiii` | `43` | Identification number, i = 67, the maker (the TX7 manual draws it `01000011`, printed page 35) |
| 2 | `0sssnnnn` | `00` to `0F` | Sub-status s = 0; channel n, 0 to 15 (channels 1 to 16) |
| 3 | `0fffffff` | `00` | Format number f = 0: one voice |
| 4 | `0bbbbbbb` | `01` | Byte count, most significant seven bits |
| 5 | `0bbbbbbb` | `1B` | Byte count, least significant seven bits: 1 × 128 + 27 = 155 |
| 6 to 160 | `0ddddddd` each | `00` to `7F` | Data bytes 1 to 155: data byte k + 1, at byte 6 + k, is voice parameter k, k from 0 to 154 (S7-28) |
| 161 | `0eeeeeee` | `00` to `7F` | Checksum of the 155 data bytes (S7-39) |
| 162 | `11110111` | `F7` | EOX: end of system exclusive |

- Reason: The adopted interface's message, byte by byte. The two bytes of the count are each a MIDI data byte of seven bits, as their drawing `0bbbbbbb` shows; 155 written in two seven-bit bytes is `01 1B`, which the TX7 manual draws as `00000001` and `00011011` (printed page 35). That data byte k + 1 is parameter k is stated by the TX7 manual: "155 bytes of data. The arrangement of this data is the same as in diagram 4-1, parameters 0 thru 154" (printed page 41, section 4-5). The DX7 manual gives the count ("b=155 ; 1 voice", "Data 1st byte ~ Data 155th byte", page 30) and the parameters (page 31), and says parameter 155 "is not stored in memory" (page 16), which agrees.
- Source: The manual, page 30 (the message), page 31 (the parameters), page 16 (parameter 155 not stored). The TX7 manual, printed page 35 (section 2-5-1, the message) and printed page 41 (section 4-5, the order of the data).
- Verification: A test builds the dump of a known voice, checks its length, header and checksum against this table, and checks that synth7 sets each of the 155 parameters from its byte; a test changes byte 6 + k for each k and checks that parameter k alone changes.

**S7-39. The checksum.** The checksum byte of a single-voice dump and of a 32-voice dump MUST be the two's complement of the sum of its data bytes, taken in seven bits: `checksum = (128 − (sum of the data bytes mod 128)) mod 128`. Equivalently, the data bytes and the checksum MUST sum to a multiple of 128. The header bytes (0 to 5) and EOX are not in the sum.
- Reason: The adopted interface: "Check Sum (add 155th byte and make the 2's complement)" and "(add 4096th byte and make the 2's complement)" (page 30, blue text): the data bytes added, then complemented; the checksum byte is drawn `0eeeeeee`, seven bits, so the complement is taken in seven bits. Both readers built today compute it so (`patch.rs`, `Bank::from_sysex`; the kit's `checksum`).
- Source: The manual, page 30 (blue text). The TX7 manual, printed pages 35 and 36, draws the checksum `0eeeeeee` after the data of each dump and does not state its rule.
- Verification: A test computes the checksum of known data by the formula and checks that a dump with it is accepted and that a dump with any other checksum is refused (S7-45).

**S7-40. What a single-voice dump does.** A single-voice dump on channel `n` that is whole and correct (S7-45) and whose parameters are all in range (S7-29) MUST replace part `n`'s current voice with its 155 parameters, and MUST set the part's operator switch to all six on. Notes already sounding keep the voice they started with. It MUST NOT change the bank, the part's program number, or any other part.
- Reason: The instrument modelled, receiving one voice, shows "INTERNAL VOICE" and the received voice's name with its first character flashing (page 22): the voice arrives in the voice being played and edited, ready to be stored, and is not stored in a memory place until a person stores it. The TX7 manual states where it lands: "The 155 bytes of voice data go into the Edit buffer, replacing any existing data there" (printed page 35). This is the effect `midi-architecture.md` MIDI-60 gives an inline patch of this family. The part is the channel's (S7-1, S7-4).
- Source: The manual, pages 22 and 32 ("2-2-2", blue text). The TX7 manual, printed page 35. `midi-architecture.md`, MIDI-60.
- Verification: A test sends a dump on channel 2, plays a note on part 2 and checks the new voice; checks part 3 unchanged; sends program change 0 on part 2 and checks the bank's voice 0 back.

**S7-41. The 32-voice dump: 4,104 bytes.** A 32-voice dump MUST be exactly these 4,104 bytes:

| Byte | Bits | Value | Meaning (the manual, page 30, "1-2-3. Bulk data of 32 voices") |
|---|---|---|---|
| 0 | `11110000` | `F0` | Status byte: system exclusive |
| 1 | `0iiiiiii` | `43` | Identification number, i = 67 |
| 2 | `0sssnnnn` | `00` to `0F` | Sub-status s = 0; channel n |
| 3 | `0fffffff` | `09` | Format number f = 9: 32 voices (the TX7 manual draws it `00001001`, printed page 36) |
| 4 | `0bbbbbbb` | `20` | Byte count, most significant seven bits |
| 5 | `0bbbbbbb` | `00` | Byte count, least significant seven bits: 32 × 128 + 0 = 4,096 |
| 6 to 4,101 | `0ddddddd` each | `00` to `7F` | Data bytes 1 to 4,096: voice v (0 to 31) is the packed voice of section 10 at bytes 6 + 128 × v to 133 + 128 × v |
| 4,102 | `0eeeeeee` | `00` to `7F` | Checksum of the 4,096 data bytes (S7-39) |
| 4,103 | `11110111` | `F7` | EOX |

- Reason: The adopted interface's message, byte by byte. That the 4,096 bytes are 32 voices of 128 bytes each, in voice order, is stated by the TX7 manual: "Data are listed in order for the 32 programs in units of 128 bytes" (printed page 44, section 4-8); the DX7 manual gives the count and "f=9 ; 32 voices" (page 30). The layout of each 128 is section 10's. Both readers built today accept exactly this message.
- Source: The manual, page 30. The TX7 manual, printed page 36 (section 2-5-1 (iv), the message) and printed page 44 (section 4-8). synth7's source, `patch.rs` (`Bank::from_sysex`, `SYSEX_BYTES`). The kit's `synth7BankFromSysex`, which moves into the server (DEC-6462).
- Verification: The existing bank tests continue to pass; a test checks the length, every header byte, the checksum and EOX one at a time by making each wrong.

**S7-42. What a 32-voice dump does.** A 32-voice dump MUST reach synth7 only as a bank: the bank image of a bank object of the bank codec, which is exactly one 32-voice dump (`midi-architecture.md`, MIDI-55 and MIDI-56), named by a sound in its list of banks (MIDI-57). A program may give it to the server as a bank (MIDI-15) or at the start of its music, where the server lifts it into a bank (MIDI-58); the server MUST refuse one that stands after the music's first note on (MIDI-58). When a sound starts, the bank's 32 voices MUST be read from its dump, whatever the dump's channel; a dump that is not whole and correct (S7-45) MUST set none of its voices, so that each of its 32 programs is the default voice (S7-51); a voice of a correct dump with a parameter out of range MUST leave the default voice in its place, and the others MUST be taken. Every such fault MUST be counted (MIDI-63). The banks a sound plays from are fixed for its life (MIDI-65): no part's current voice, program number or function parameters change when a bank arrives, and a part takes a bank's voices at its next program change.
- Reason: The instrument modelled, receiving all 32 voices, memorizes them "into the internal memory" (page 22); its voice being played is not said to change. The bank is shared by every part (S7-2), so the channel addresses nothing. A voice out of range costs only that voice, as built for a stored bank today (`instruments.rs`, `bank`). A message of 4,104 bytes cannot be one event of a block (MIDI-28, MIDI-30), and `midi-architecture.md` forbids splitting one across events or blocks (MIDI-50), so the dump travels as a bank; this document's open question 2, which asked whether the dump should also be taken in a stream, is answered by those requirements.
- Source: The manual, pages 22 and 32 ("2-2-3", blue text). synth7's source, `instruments.rs` (`bank`). `midi-architecture.md`, MIDI-15, MIDI-28, MIDI-30, MIDI-50, MIDI-51, MIDI-55 to MIDI-58, MIDI-63 and MIDI-65.
- Verification: A test plays a sound naming a bank, sends program change 5 and checks voice 5 of the dump; a test makes a bank whose dump has voice 7 out of range and checks voice 7 the default, the other 31 taken and the fault counted; a test makes a bank whose dump has a wrong checksum and checks every program the default and the fault counted; a server test gives music that begins with a 32-voice dump and checks it lifted into a bank, and one with the dump after a note on and checks the refusal.

**S7-43. The parameter change: 7 bytes.** A parameter change MUST be exactly these 7 bytes:

| Byte | Bits | Value | Meaning (the manual, page 30, "1-2-4. Parameter change") |
|---|---|---|---|
| 0 | `11110000` | `F0` | Status byte |
| 1 | `0iiiiiii` | `43` | Identification number, i = 67 |
| 2 | `0sssnnnn` | `10` to `1F` | Sub-status s = 1; channel n |
| 3 | `0gggggpp` | see below | Parameter group g, in bits 2 to 6; the two highest bits of the parameter number, in bits 0 and 1 |
| 4 | `0ppppppp` | `00` to `7F` | The parameter number's lowest seven bits |
| 5 | `0ddddddd` | `00` to `7F` | Data: the parameter's new value |
| 6 | `11110111` | `F7` | EOX |

The groups are: g = 0, the voice parameters 0 to 155 (S7-28); g = 2, the function parameters 64 to 77 (S7-33). The parameter number is `pp × 128 + ppppppp`: the TX7 manual calls the two low bits of byte 3 the sub-group `h` ("0ggggghh", h = 0, 1, printed page 36) and numbers voice parameters 128 to 156 as sub-group 1, parameter 0 to 28 ("0 (128)" to "28 (156)", printed page 38). So a voice parameter 0 to 127 is written byte 3 `00`, byte 4 the number; a voice parameter 128 to 155 is written byte 3 `01`, byte 4 the number less 128 (`00` to `1B`); a function parameter 64 to 77 is written byte 3 `08` (g = 2, pp = 0), byte 4 `40` to `4D`. Every other group (1 and 3 to 31), every voice parameter number above 155 (among them the TX7's 156, OPERATOR SELECT, a choice of the operator a panel edits) and every function parameter number below 64 or above 77 MUST be counted as ignored. The full list of numbers, with the bytes 3 and 4 of each, is S7-28's table (group 0) and S7-33's (group 2).
- Reason: The adopted interface's message, byte by byte. The manual names group 0 "DX common Voice parameter" ("DX 共通" in its table's heading) and group 2 "DX7 Function parameter" (pages 30 and 31). It draws the two lowest bits of byte 3 as `pp`, part of the parameter number, which the voice parameters need since their numbers reach 155, beyond seven bits; the TX7 manual states that those bits are the sub-group, sub-group 1 holding parameters 128 and above (printed pages 36 and 38). The TX7 manual's drawing of the message omits the data byte between the parameter number and EOX (printed page 36); the DX7 manual draws it (page 30), and synth7 follows the DX7 manual.
- Source: The manual, pages 30 and 31. The TX7 manual, printed pages 36 (section 2-5-2) and 38 (section 4-1).
- Verification: A test sends a parameter change for every voice parameter 0 to 155 and every function parameter 64 to 77 and checks that exactly that parameter of that part changes; a test sends groups 1 and 3, voice number 156, and function numbers 63 and 78, and checks each counted.

**S7-44. What a parameter change does.** A parameter change of group 0 on channel `n` whose data is within the parameter's range MUST set that parameter of part `n`'s current voice; a change to the voice's sound (any parameter but the name) MUST take effect on notes started afterwards, and on notes already sounding from the next block for the parameters that the instrument's sound engine reads continuously (output levels, the low-frequency oscillator, the pitch modulation sensitivity, the operator switch) and from their next note for the others. It MUST NOT change the bank. A parameter change of group 2 on channel `n` within range MUST set that function parameter of part `n` (S7-33).
- Reason: The adopted interface: "When receiving this information, the unit will vary the data for that particular parameter" (page 22); "Voice or function data in the Edit Buffer will be changed" (TX7 manual, printed page 36); "Voice parameter and function parameter request reception with the same format as transmission" (page 32, blue text). The voice changed is the one being played, which a panel edits (page 12); the stored bank changes only when a person stores. Which parameters reach a sounding note on the instrument is not stated in the source; the split above is NeoTeletext's own (section 15 item 16), and the list is to be confirmed against the engine when it is built.
- Source: The manual, pages 12, 22 and 32. The TX7 manual, printed page 36.
- Verification: A test holds a note and sends a change of OUTPUT LEVEL of its carrier and checks the level changes within one block; sends a change of ALGORITHM SELECT, checks the held note unchanged and the next note changed; sends program change 0 and checks the bank's voice back.

**S7-45. A faulty system exclusive message.** A message of identification 67 that begins as a single-voice dump or a 32-voice dump (bytes 0 to 3 as S7-38 or S7-41) but has another length, another byte count, a byte with bit 7 set before its last, a checksum that fails S7-39, or a last byte that is not `F7`, MUST be refused whole: nothing it carries is taken, and the fault MUST be counted. A parameter change of another length, or with a byte with bit 7 set before its last, MUST likewise be refused and counted.
- Reason: The instrument modelled stores a dump as it arrives; NeoTeletext receives its input from outside, so every byte is untrusted and nothing is taken until all of it is checked (DEVELOPMENT.md sections 6 and 14). Both readers built today refuse on these grounds for the 32-voice dump.
- Source: DEVELOPMENT.md sections 6 and 14. synth7's source, `patch.rs` (`BankError`). The kit's `synth7BankFromSysex`.
- Verification: A test takes a correct dump of each kind and, for each byte position, sets bit 7, changes the value, removes the byte and adds a byte, checking each refusal and its count; a fuzz target feeds arbitrary system exclusive messages to synth7 and checks that it never panics and that only well-formed messages act.

## 10. The packed voice: 128 bytes

The DX7 manual does not lay out these 128 bytes; the TX7 manual does, every byte and bit field ("4-8. 32 Voice Bulk Data (f = 9)", printed page 44), and the DX7 II manual draws the same layout ("5-4. Voice Data (VMEM format)", printed page Add-11). The table below is that layout. It was checked on 18 November 2026 against the TX7 manual's page 44, byte by byte and bit by bit, and against the DX7 II manual's page Add-11, and agrees with both in every field; it is also the layout synth7 reads and writes today (`Patch::from_packed` and `Patch::to_packed` in `patch.rs`, whose comments cite an unfiled document of 1993 and the Apache-2.0 program of DEC-6420, and which are to cite the TX7 manual instead). Every field's range is S7-28's. "Unused" bits, which the TX7 manual draws hatched, are written 0 by a sender.

**S7-46. The layout of a packed voice.** A packed voice MUST be exactly 128 bytes, each a MIDI data byte (bit 7 clear), laid out as this table says. Bytes 0 to 101 are six blocks of 17 bytes, one for each operator, operator 6 first (bytes 0 to 16), then operators 5 (17 to 33), 4 (34 to 50), 3 (51 to 67), 2 (68 to 84) and 1 (85 to 101); bytes 102 to 127 are the voice's own. Each field names the voice parameter of S7-28 it carries.

| Byte | Of | Bits and the parameter each carries |
|---|---|---|
| 0 | Operator 6 | bits 0–6: EG RATE 1 (parameter 0) |
| 1 | Operator 6 | bits 0–6: EG RATE 2 (parameter 1) |
| 2 | Operator 6 | bits 0–6: EG RATE 3 (parameter 2) |
| 3 | Operator 6 | bits 0–6: EG RATE 4 (parameter 3) |
| 4 | Operator 6 | bits 0–6: EG LEVEL 1 (parameter 4) |
| 5 | Operator 6 | bits 0–6: EG LEVEL 2 (parameter 5) |
| 6 | Operator 6 | bits 0–6: EG LEVEL 3 (parameter 6) |
| 7 | Operator 6 | bits 0–6: EG LEVEL 4 (parameter 7) |
| 8 | Operator 6 | bits 0–6: BREAK POINT (parameter 8) |
| 9 | Operator 6 | bits 0–6: LEFT DEPTH (parameter 9) |
| 10 | Operator 6 | bits 0–6: RIGHT DEPTH (parameter 10) |
| 11 | Operator 6 | bits 0–1: LEFT CURVE (parameter 11); bits 2–3: RIGHT CURVE (parameter 12); bits 4–6 unused |
| 12 | Operator 6 | bits 0–2: KEYBOARD RATE SCALING (parameter 13); bits 3–6: DETUNE (parameter 20) |
| 13 | Operator 6 | bits 0–1: MOD SENSITIVITY AMPLITUDE (parameter 14); bits 2–4: KEY VELOCITY SENSITIVITY (parameter 15); bits 5–6 unused |
| 14 | Operator 6 | bits 0–6: OUTPUT LEVEL (parameter 16) |
| 15 | Operator 6 | bit 0: OSCILLATOR MODE (parameter 17); bits 1–5: FREQUENCY COARSE (parameter 18); bit 6 unused |
| 16 | Operator 6 | bits 0–6: FREQUENCY FINE (parameter 19) |
| 17 | Operator 5 | bits 0–6: EG RATE 1 (parameter 21) |
| 18 | Operator 5 | bits 0–6: EG RATE 2 (parameter 22) |
| 19 | Operator 5 | bits 0–6: EG RATE 3 (parameter 23) |
| 20 | Operator 5 | bits 0–6: EG RATE 4 (parameter 24) |
| 21 | Operator 5 | bits 0–6: EG LEVEL 1 (parameter 25) |
| 22 | Operator 5 | bits 0–6: EG LEVEL 2 (parameter 26) |
| 23 | Operator 5 | bits 0–6: EG LEVEL 3 (parameter 27) |
| 24 | Operator 5 | bits 0–6: EG LEVEL 4 (parameter 28) |
| 25 | Operator 5 | bits 0–6: BREAK POINT (parameter 29) |
| 26 | Operator 5 | bits 0–6: LEFT DEPTH (parameter 30) |
| 27 | Operator 5 | bits 0–6: RIGHT DEPTH (parameter 31) |
| 28 | Operator 5 | bits 0–1: LEFT CURVE (parameter 32); bits 2–3: RIGHT CURVE (parameter 33); bits 4–6 unused |
| 29 | Operator 5 | bits 0–2: KEYBOARD RATE SCALING (parameter 34); bits 3–6: DETUNE (parameter 41) |
| 30 | Operator 5 | bits 0–1: MOD SENSITIVITY AMPLITUDE (parameter 35); bits 2–4: KEY VELOCITY SENSITIVITY (parameter 36); bits 5–6 unused |
| 31 | Operator 5 | bits 0–6: OUTPUT LEVEL (parameter 37) |
| 32 | Operator 5 | bit 0: OSCILLATOR MODE (parameter 38); bits 1–5: FREQUENCY COARSE (parameter 39); bit 6 unused |
| 33 | Operator 5 | bits 0–6: FREQUENCY FINE (parameter 40) |
| 34 | Operator 4 | bits 0–6: EG RATE 1 (parameter 42) |
| 35 | Operator 4 | bits 0–6: EG RATE 2 (parameter 43) |
| 36 | Operator 4 | bits 0–6: EG RATE 3 (parameter 44) |
| 37 | Operator 4 | bits 0–6: EG RATE 4 (parameter 45) |
| 38 | Operator 4 | bits 0–6: EG LEVEL 1 (parameter 46) |
| 39 | Operator 4 | bits 0–6: EG LEVEL 2 (parameter 47) |
| 40 | Operator 4 | bits 0–6: EG LEVEL 3 (parameter 48) |
| 41 | Operator 4 | bits 0–6: EG LEVEL 4 (parameter 49) |
| 42 | Operator 4 | bits 0–6: BREAK POINT (parameter 50) |
| 43 | Operator 4 | bits 0–6: LEFT DEPTH (parameter 51) |
| 44 | Operator 4 | bits 0–6: RIGHT DEPTH (parameter 52) |
| 45 | Operator 4 | bits 0–1: LEFT CURVE (parameter 53); bits 2–3: RIGHT CURVE (parameter 54); bits 4–6 unused |
| 46 | Operator 4 | bits 0–2: KEYBOARD RATE SCALING (parameter 55); bits 3–6: DETUNE (parameter 62) |
| 47 | Operator 4 | bits 0–1: MOD SENSITIVITY AMPLITUDE (parameter 56); bits 2–4: KEY VELOCITY SENSITIVITY (parameter 57); bits 5–6 unused |
| 48 | Operator 4 | bits 0–6: OUTPUT LEVEL (parameter 58) |
| 49 | Operator 4 | bit 0: OSCILLATOR MODE (parameter 59); bits 1–5: FREQUENCY COARSE (parameter 60); bit 6 unused |
| 50 | Operator 4 | bits 0–6: FREQUENCY FINE (parameter 61) |
| 51 | Operator 3 | bits 0–6: EG RATE 1 (parameter 63) |
| 52 | Operator 3 | bits 0–6: EG RATE 2 (parameter 64) |
| 53 | Operator 3 | bits 0–6: EG RATE 3 (parameter 65) |
| 54 | Operator 3 | bits 0–6: EG RATE 4 (parameter 66) |
| 55 | Operator 3 | bits 0–6: EG LEVEL 1 (parameter 67) |
| 56 | Operator 3 | bits 0–6: EG LEVEL 2 (parameter 68) |
| 57 | Operator 3 | bits 0–6: EG LEVEL 3 (parameter 69) |
| 58 | Operator 3 | bits 0–6: EG LEVEL 4 (parameter 70) |
| 59 | Operator 3 | bits 0–6: BREAK POINT (parameter 71) |
| 60 | Operator 3 | bits 0–6: LEFT DEPTH (parameter 72) |
| 61 | Operator 3 | bits 0–6: RIGHT DEPTH (parameter 73) |
| 62 | Operator 3 | bits 0–1: LEFT CURVE (parameter 74); bits 2–3: RIGHT CURVE (parameter 75); bits 4–6 unused |
| 63 | Operator 3 | bits 0–2: KEYBOARD RATE SCALING (parameter 76); bits 3–6: DETUNE (parameter 83) |
| 64 | Operator 3 | bits 0–1: MOD SENSITIVITY AMPLITUDE (parameter 77); bits 2–4: KEY VELOCITY SENSITIVITY (parameter 78); bits 5–6 unused |
| 65 | Operator 3 | bits 0–6: OUTPUT LEVEL (parameter 79) |
| 66 | Operator 3 | bit 0: OSCILLATOR MODE (parameter 80); bits 1–5: FREQUENCY COARSE (parameter 81); bit 6 unused |
| 67 | Operator 3 | bits 0–6: FREQUENCY FINE (parameter 82) |
| 68 | Operator 2 | bits 0–6: EG RATE 1 (parameter 84) |
| 69 | Operator 2 | bits 0–6: EG RATE 2 (parameter 85) |
| 70 | Operator 2 | bits 0–6: EG RATE 3 (parameter 86) |
| 71 | Operator 2 | bits 0–6: EG RATE 4 (parameter 87) |
| 72 | Operator 2 | bits 0–6: EG LEVEL 1 (parameter 88) |
| 73 | Operator 2 | bits 0–6: EG LEVEL 2 (parameter 89) |
| 74 | Operator 2 | bits 0–6: EG LEVEL 3 (parameter 90) |
| 75 | Operator 2 | bits 0–6: EG LEVEL 4 (parameter 91) |
| 76 | Operator 2 | bits 0–6: BREAK POINT (parameter 92) |
| 77 | Operator 2 | bits 0–6: LEFT DEPTH (parameter 93) |
| 78 | Operator 2 | bits 0–6: RIGHT DEPTH (parameter 94) |
| 79 | Operator 2 | bits 0–1: LEFT CURVE (parameter 95); bits 2–3: RIGHT CURVE (parameter 96); bits 4–6 unused |
| 80 | Operator 2 | bits 0–2: KEYBOARD RATE SCALING (parameter 97); bits 3–6: DETUNE (parameter 104) |
| 81 | Operator 2 | bits 0–1: MOD SENSITIVITY AMPLITUDE (parameter 98); bits 2–4: KEY VELOCITY SENSITIVITY (parameter 99); bits 5–6 unused |
| 82 | Operator 2 | bits 0–6: OUTPUT LEVEL (parameter 100) |
| 83 | Operator 2 | bit 0: OSCILLATOR MODE (parameter 101); bits 1–5: FREQUENCY COARSE (parameter 102); bit 6 unused |
| 84 | Operator 2 | bits 0–6: FREQUENCY FINE (parameter 103) |
| 85 | Operator 1 | bits 0–6: EG RATE 1 (parameter 105) |
| 86 | Operator 1 | bits 0–6: EG RATE 2 (parameter 106) |
| 87 | Operator 1 | bits 0–6: EG RATE 3 (parameter 107) |
| 88 | Operator 1 | bits 0–6: EG RATE 4 (parameter 108) |
| 89 | Operator 1 | bits 0–6: EG LEVEL 1 (parameter 109) |
| 90 | Operator 1 | bits 0–6: EG LEVEL 2 (parameter 110) |
| 91 | Operator 1 | bits 0–6: EG LEVEL 3 (parameter 111) |
| 92 | Operator 1 | bits 0–6: EG LEVEL 4 (parameter 112) |
| 93 | Operator 1 | bits 0–6: BREAK POINT (parameter 113) |
| 94 | Operator 1 | bits 0–6: LEFT DEPTH (parameter 114) |
| 95 | Operator 1 | bits 0–6: RIGHT DEPTH (parameter 115) |
| 96 | Operator 1 | bits 0–1: LEFT CURVE (parameter 116); bits 2–3: RIGHT CURVE (parameter 117); bits 4–6 unused |
| 97 | Operator 1 | bits 0–2: KEYBOARD RATE SCALING (parameter 118); bits 3–6: DETUNE (parameter 125) |
| 98 | Operator 1 | bits 0–1: MOD SENSITIVITY AMPLITUDE (parameter 119); bits 2–4: KEY VELOCITY SENSITIVITY (parameter 120); bits 5–6 unused |
| 99 | Operator 1 | bits 0–6: OUTPUT LEVEL (parameter 121) |
| 100 | Operator 1 | bit 0: OSCILLATOR MODE (parameter 122); bits 1–5: FREQUENCY COARSE (parameter 123); bit 6 unused |
| 101 | Operator 1 | bits 0–6: FREQUENCY FINE (parameter 124) |
| 102 | Voice | bits 0–6: PITCH EG RATE 1 (parameter 126) |
| 103 | Voice | bits 0–6: PITCH EG RATE 2 (parameter 127) |
| 104 | Voice | bits 0–6: PITCH EG RATE 3 (parameter 128) |
| 105 | Voice | bits 0–6: PITCH EG RATE 4 (parameter 129) |
| 106 | Voice | bits 0–6: PITCH EG LEVEL 1 (parameter 130) |
| 107 | Voice | bits 0–6: PITCH EG LEVEL 2 (parameter 131) |
| 108 | Voice | bits 0–6: PITCH EG LEVEL 3 (parameter 132) |
| 109 | Voice | bits 0–6: PITCH EG LEVEL 4 (parameter 133) |
| 110 | Voice | bits 0–4: ALGORITHM SELECT (parameter 134); bits 5–6 unused |
| 111 | Voice | bits 0–2: FEEDBACK (parameter 135); bit 3: OSCILLATOR SYNC (parameter 136); bits 4–6 unused |
| 112 | Voice | bits 0–6: LFO SPEED (parameter 137) |
| 113 | Voice | bits 0–6: LFO DELAY (parameter 138) |
| 114 | Voice | bits 0–6: LFO PMD (parameter 139) |
| 115 | Voice | bits 0–6: LFO AMD (parameter 140) |
| 116 | Voice | bit 0: LFO SYNC (parameter 141); bits 1–3: LFO WAVE (parameter 142); bits 4–6: MOD SENSITIVITY PITCH (parameter 143) |
| 117 | Voice | bits 0–6: TRANSPOSE (parameter 144) |
| 118 | Voice | bits 0–6: VOICE NAME 1 (parameter 145) |
| 119 | Voice | bits 0–6: VOICE NAME 2 (parameter 146) |
| 120 | Voice | bits 0–6: VOICE NAME 3 (parameter 147) |
| 121 | Voice | bits 0–6: VOICE NAME 4 (parameter 148) |
| 122 | Voice | bits 0–6: VOICE NAME 5 (parameter 149) |
| 123 | Voice | bits 0–6: VOICE NAME 6 (parameter 150) |
| 124 | Voice | bits 0–6: VOICE NAME 7 (parameter 151) |
| 125 | Voice | bits 0–6: VOICE NAME 8 (parameter 152) |
| 126 | Voice | bits 0–6: VOICE NAME 9 (parameter 153) |
| 127 | Voice | bits 0–6: VOICE NAME 10 (parameter 154) |

- Reason: This is the form in which a 32-voice dump carries each voice (S7-41), and the form every existing bank file holds; it is what synth7 reads today.
- Source: The TX7 manual, printed page 44 (PDF page 45), section 4-8: the 17 bytes of operator 6 drawn field by field at addresses 0 to 16, operators 5 to 1 at 17 to 33, 34 to 50, 51 to 67, 68 to 84 and 85 to 101 "in the same" form, and bytes 102 to 127 drawn field by field. The DX7 II manual, printed page Add-11 (PDF page 105), section 5-4, the same layout (its byte 111 field "OPI", oscillator phase init, is the DX7's oscillator sync). As built: synth7's source, `patch.rs`.
- Verification: The existing packing tests continue to pass; a test packs a voice whose every parameter is distinct and checks every byte against this table; a test unpacks every byte position with every bit set alone and checks which parameter changes.

**S7-47. Unused bits and bit 7.** A receiver MUST ignore the unused bits of S7-46 (bits 4 to 6 of each operator's byte 11; bits 5 and 6 of its byte 13; bit 6 of its byte 15; bits 5 and 6 of byte 110; bits 4 to 6 of byte 111) and MUST then check every field against its range (S7-29). A sender MUST write every unused bit as 0.
- Reason: Bank files made by other tools may hold anything in bits the layout does not use; ignoring them takes every such file whose fields are in range, as today. Bit 7 cannot occur in a system exclusive message's data (S7-45).
- Source: The TX7 manual, printed page 44 (the unused bits are drawn hatched: bits 4 to 6 of byte 11, bits 5 and 6 of byte 13, bit 6 of byte 15, bits 5 and 6 of byte 110, bits 4 to 6 of byte 111). synth7's source, `patch.rs` (`from_packed`: "the bits the format leaves unused … are ignored, as the instrument's own masks ignore them").
- Verification: A test sets every unused bit of a correct voice and checks the voice accepted and identical to the voice without them.

**S7-48. From 155 parameters to 128 bytes and back.** Packing a voice MUST place each of parameters 0 to 154 in the byte and bits S7-28's last column and S7-46 give it, and nothing else; unpacking MUST read each from there. For every voice whose parameters are all in range, unpacking the packed voice MUST give back exactly the same 155 parameters, and packing the parameters of a single-voice dump (S7-38) MUST give the packed voice of the same voice. Parameter 155 is in neither form.
- Reason: A voice arrives in either form (a single-voice dump or a parameter change gives the 155; a 32-voice dump gives the 128), and the server, which packs and checks (DEC-6462), and the engine, which reads, must agree on one mapping; the kits hold none of it (`midi-architecture.md`, MIDI-22). Every field of the 128-byte form is a whole parameter at a fixed place, with no scaling, so the mapping loses nothing within range.
- Source: S7-28 and S7-46; the TX7 manual, printed pages 38, 41 and 44. synth7's source, `patch.rs` (`to_packed`, `from_packed`).
- Verification: A property test packs and unpacks random voices of in-range parameters and checks equality both ways; a test converts a single-voice dump to a packed voice and back for each of a 32-voice bank's voices.

## 11. Banks, voices and their sizes

**S7-49. Sizes, carriage, codec and restatement.** `midi-architecture.md` specifies how a bank is stored, named and carried, how a block carries system exclusive, the codec numbers, and the restatement every live sound carries; synth7 takes them as follows.
1. **Patch and bank sizes.** A single voice travels as the single-voice dump of S7-38: 163 bytes, 162 after `F0`, so one event of a block (MIDI-27, MIDI-28, MIDI-54, MIDI-60). A bank image is exactly one 32-voice dump of S7-41, byte for byte: 4,104 bytes, 32 voices (MIDI-56); it travels only as a bank object of the bank codec, never in a block (MIDI-50, MIDI-51, MIDI-55). A parameter change is 7 bytes, 6 after `F0`; all fourteen function parameters of one part are 98 bytes of messages, of all sixteen parts 1,568.
2. **Wholeness.** Each message MUST be whole before synth7 acts on it (S7-45): a single-voice dump or a parameter change is whole in one event of one block (MIDI-27, MIDI-50), and a bank is read only when every one of its records has arrived (MIDI-52).
3. **Codec.** A synth7 sound MUST be of the codec `midi-architecture.md` MIDI-107 gives synth7, code 13, and its banks of the bank codec, code 19, with extension tag 6 naming code 13 (MIDI-48), if the architecture's open question 1 is answered as it recommends; otherwise synth7 keeps its present codes, 4 for its sounds and 5 for its banks, with their contents changed as this document and the architecture say. DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation), so synth7's sounds are of code 13 and its banks of code 19.
4. **Restatement.** The server MUST restate every part of a live synth7 sound as MIDI-93 to MIDI-98 require (in the first block, and at least once in every 50 blocks), and MUST begin every stored synth7 sound with the restatement of every part it uses (MIDI-99). A synth7 part's restatement MUST be, in this order, at one tick and whole in one block (MIDI-37, MIDI-98): (a) the part's program change, or, where the part's current voice differs in any of parameters 0 to 154 from the voice its program chose (because a single-voice dump or a parameter change of group 0 changed it), one single-voice dump (S7-38) of the current voice in place of the program change and those parameter changes; (b) a parameter change of voice parameter 155 where the operator switch is not all six on; (c) a parameter change of group 2 for every function parameter that differs from S7-35, in ascending order of parameter number; (d) the performance state, where it is not at its value after reset all controllers (S7-20) or at the start of a sound (S7-54): pitch bend, channel pressure, then controllers 1, 2, 4, 7, 64 and 65 in ascending order. Controller 5 is never restated, since its value lives in function parameter 69, which (c) restates. A part's restatement is therefore at most 332 bytes (a single-voice dump of 166 bytes as an event; 9 bytes for parameter 155; 14 function parameters of 9 bytes each, 126; a pitch bend of 4 bytes and channel pressure of 3; six controllers of 4 bytes each, 24), which fits one block (MIDI-30).
- Reason: Decision A4: synth7's patches travel in the adopted interface's own form, byte for byte. The sizes are what `midi-architecture.md` needs to size records and restatements. Function parameters belong to no voice and no bank (page 6), so a late viewer has them only if they are restated. Restating an edited voice as one dump rather than as every parameter change since keeps a part's restatement within one block whatever was edited (155 parameter changes would be 1,395 bytes), and is the inline patch MIDI-93 names; the dump also sets the operator switch to all on (S7-40), so (b) follows it. The codec number is the architecture's open question 1, which a family document does not decide. This requirement formerly said that a message longer than one block or record "must be joined by the transport" and that a sender repeats "every single-voice dump or parameter change"; both were changed to follow `midi-architecture.md` (MIDI-50, MIDI-51, MIDI-93 to MIDI-99), and the restatement is the server's, not a program's or a kit's (DEC-6462).
- Source: The manual, pages 6 and 30. Decision A4. DEC-6462. `midi-architecture.md`, MIDI-27, MIDI-28, MIDI-30, MIDI-37, MIDI-48, MIDI-50 to MIDI-52, MIDI-54 to MIDI-56, MIDI-60, MIDI-93 to MIDI-99 and MIDI-107 to MIDI-109, and its open question 1.
- Verification: The architecture document's tests cover the carriage; a server test drives a part through a program change, a single-voice dump, parameter changes of groups 0 and 2, every controller of (d) and a bend, then checks the restatement's bytes against this order and its length against 332; a test of synth7 joins a live sound after function parameters and a voice edit were sent, receives the restatement, and checks its state equals that of a viewer who heard from the start; a test plays a restatement into a synth7 that already holds its state and checks identical samples (MIDI-97).

**S7-50. Program numbers and voices.** A synth7 program change MUST be mapped to a voice by this table, which is synth7's mapping under `midi-architecture.md` MIDI-59 (synth7 has no bank select, so controllers 0 and 32 do not enter it, MIDI-64):

| Program number `p` | Bank index | Voice of that bank's 32-voice dump | What the instrument modelled shows |
|---|---|---|---|
| 0 to 31 | 0 (the sound's first bank) | `p`: the voice at data bytes `128 × p` to `128 × p + 127` | "INT" `p + 1` |
| 32 to 63 | 1 (the sound's second bank, the cartridge bank) | `p − 32`: the voice at data bytes `128 × (p − 32)` to `128 × (p − 32) + 127` | "CRT" `p − 31` |
| 64 to 127 | None | None: the default voice, counted (S7-21) | Not defined by the adopted interface |

A synth7 sound MAY name one or two banks (MIDI-57); since no program change reaches a third, the server MUST refuse a synth7 sound that names more than two, naming the count.
- Reason: "p=0:INT1 ~ p=31:INT32, p=32:CRT1 ~ p=63:CRT32" (pages 30 and 32). The cartridge's voices are a second bank, as `midi-architecture.md` MIDI-57 gives the DX7's programs 32 to 63 as its example of a sound naming more than one bank. Whether a sound may name more than one bank is the architecture's open question 3; this document's open question 3, which asked the same for synth7, now refers to it. The refusal of a third bank is NeoTeletext's own (section 15), because a bank no program change can reach is store spent for nothing.
- Source: The manual, pages 30 and 32. `midi-architecture.md`, MIDI-57, MIDI-59 and MIDI-64, and its open question 3.
- Verification: The test of S7-21; a test sends program changes 32, 45 and 63 to a sound naming two banks and checks voices 0, 13 and 31 of the second, and to a sound naming one bank and checks the default voice and the count; a server test refuses a synth7 sound naming three banks.

**S7-51. The default voice.** A part whose bank holds no voice at the number chosen, or whose voice was refused, MUST play this voice, the maker's initial voice as the DX7 II manual gives it value by value in the "INIT" column of its voice parameter table (printed page Add-8): algorithm 1 (value 0); operator 1 at output level 99, ratio 1.00 (coarse 1, fine 0, detune 7), envelope rates 99, 99, 99, 99 and levels 99, 99, 99, 0; operators 2 to 6 the same but at output level 0; break point 39, depths 0, curves 0, rate scaling 0, amplitude sensitivity 0, velocity sensitivity 0, oscillator mode 0 for every operator; pitch envelope rates 99 and levels 50; feedback 0; oscillator sync 1; LFO speed 35, delay 0, PMD 0, AMD 0, sync 1, wave 0; pitch sensitivity 3; transpose 24; name "INIT VOICE" (voice name parameters 145 to 154: "I", "N", "I", "T", a space, "V", "O", "I", "C", "E"). The manual's "INIT" column gives no value for the operator switch (parameter 155); a part's switch is all six on, as S7-21 and S7-54 set it. It is the family's default patch of `midi-architecture.md` MIDI-61 and MIDI-63.
- Reason: A part must sound something definite, and under DEC-6453 nothing of NeoTeletext's own is used where the maker's exists. The DX7 manual's "basic voice data" set by VOICE INIT (page 7) is not given value by value there; the DX7 II manual gives the maker's initial voice value by value ("INIT" column, printed page Add-8), for the same voice parameters 0 to 154, and that voice is taken (open question 6, answered by DEC-6465, awaiting the owner's confirmation). What is built today (`Patch::DEFAULT`, NeoTeletext's own choice) is the same voice in every parameter but two: algorithm value 15 (algorithm 16) in place of 0, and the name "PLAIN SINE" in place of "INIT VOICE". With every operator but operator 1 at output level 0 both algorithms sound one plain sine, carrier operator 1 alone, so the change alters no sound; it changes the voice's bytes, and so what a voice parameter dump of the default voice holds (section 17, item 19).
- Source: The DX7 II manual, printed page Add-8 (the "INIT" column of the voice parameter table, section 5-1, read for this requirement from the filed scan). synth7's source, `patch.rs` (`Patch::DEFAULT`), which this requirement changes. DEC-6453; DEC-6465 answer 16. `midi-architecture.md`, MIDI-61 and MIDI-63.
- Verification: A test checks a new part's current voice, with an empty bank, against these values parameter by parameter.

## 12. How a message takes effect

**S7-52. Order and time.** synth7 MUST act on messages in the order and at the times the block gives them: each event's message MUST take effect at the sample `floor(tick × 24 ÷ 5)` of its block, after every earlier sample of the block has been rendered (`midi-architecture.md`, MIDI-5 and MIDI-36), and events of one tick in the order they stand (MIDI-35). A change of a level or a parameter MAY then be smoothed as the engine smooths it, provided it passes the click measure (MIDI-73, MIDI-83). Two racks given the same messages at the same times MUST give the same samples, however the rendering is divided into calls.
- Reason: A stored sound must play identically for every viewer and at every loop, and every synthesizer places an event on the same sample (MIDI-5, MIDI-36). As built, synth7 renders in steps of 32 samples and a message takes effect at the start of the next step, up to 0.67 milliseconds late (`rack.rs`); MIDI-36 allows 0.8 of a sample, so the engine must start a step at an event's sample (section 17). This requirement formerly allowed the 32-sample delay, and was changed to follow the architecture.
- Source: Decisions A2 and A3. `midi-architecture.md`, MIDI-5, MIDI-35, MIDI-36, MIDI-73 and MIDI-83. synth7's source, `rack.rs` ("A message takes effect at the next block: at most 0.67 milliseconds later").
- Verification: A test places a note on at each tick from 0 to 199 in turn and checks the first sample that changes is `floor(tick × 24 ÷ 5)`; a test renders one score in calls of 1, 7, 960 and 4,800 samples and checks the samples identical; the existing determinism tests continue to pass.

**S7-53. After a lost block.** When the receiver tells synth7 that input was lost (the architecture document says when), synth7 MUST release every note of every part, held by a key or by the pedal, lift every sustain pedal, and set every part's registered parameter number selection to none (`midi-architecture.md`, MIDI-102), and MUST leave every part's current voice, function parameters, program number, wheels, controllers and volume as they stand.
- Reason: A lost block may have held a note off; it may equally have held voice or function changes, which cannot be known, so they are left and the server's restatement (S7-49 item 4) restores them; it may have held a registered parameter number selection, and a data entry to the wrong parameter is worse than none (MIDI-76).
- Source: DEC-6410 item 12. `midi-architecture.md`, MIDI-76 and MIDI-102. synth7's source, `rack.rs` (`release_all`) and `instruments.rs` (`conceal`).
- Verification: The existing test `a_live_sound_of_each_synthesizer_plays_and_a_lost_block_releases_its_notes` passes for synth7; a test changes a function parameter, loses a block, and checks the parameter kept; a test selects registered parameter number 0, loses a block, sends controller 6 and checks the pitch bend range unchanged.

**S7-54. A sound's start.** When a synth7 sound starts, every part MUST stand at program 0 of the sound's first bank (or the default voice), its operator switch all on, its function parameters as S7-35, its pitch bend at the centre, its wheel, breath, foot and pressure at 0, its volume at 127, its sustain pedal up, its portamento switch on (S7-17) and its registered parameter number selection none, with no note sounding (`midi-architecture.md`, MIDI-61).
- Reason: A stored sound is rendered from its first block for every viewer and must start from one state; when it loops, synth7 is not reset (MIDI-105), and block 0's restatement sets every part again (MIDI-99).
- Source: synth7's source, `rack.rs` (`reset`), with the function parameters, controllers and switches this document adds. `midi-architecture.md`, MIDI-61, MIDI-99 and MIDI-105.
- Verification: A test checks each of these on a new sound before its first block.

## 13. Existing files and tools

**S7-55. What works unchanged.** synth7 MUST accept, byte for byte and with no conversion: (a) as a bank (S7-42), any 32-voice dump of exactly 4,104 bytes as S7-41 gives it, on any channel, whose voices are in range, which is the content of a 32-voice bank file of the instrument modelled; (b) any single-voice dump of exactly 163 bytes as S7-38 gives it; (c) any parameter change of 7 bytes as S7-43 gives it, of a voice or function parameter. A stream of these, with the channel messages of section 5, written by a sequencer or an editor for the instrument modelled on one channel, MUST play on part `n` of a synth7 sound as on one instrument receiving channel `n`, a 32-voice dump at its start being lifted into a bank by the server (`midi-architecture.md`, MIDI-58).
- Reason: Decision DEC-6453: NeoTeletext is to be exactly compatible with the most well-known interface, so that existing sounds, tools and skills work. DEC-6460 records that the maker's system exclusive is "read by Dexed, FM8, Yamaha's later FM instruments and librarians"; that record, not this document's author, is the source for those names, and which file layouts each of those programs writes is not stated in any filed source. A file holding anything other than the exact messages (several messages one after another, a file of 4,096 bytes with no header, a dump of another format number) is not accepted as it is; the server refuses it, naming the fault, and a program splits or wraps it before sending. A Standard MIDI File holding such messages is read by the server (`midi-architecture.md`, section 15).
- Source: DEC-6453, DEC-6460. The manual, page 30. The TX7 manual, printed pages 35 and 36.
- Verification: A test feeds a set of bank and voice files kept in the test corpus (each with its provenance and licence recorded, DEVELOPMENT.md section 7) and checks each accepted and each voice playing; a test plays one recorded stream for the instrument modelled on each of channels 0 and 9 and checks parts 0 and 9.

---

## 14. What is left out of the adopted interface

### 14.1 Left out

| Item of the adopted interface | Where the manual has it | Why synth7 leaves it out |
|---|---|---|
| The receiving channel setting, 1 to 16, and the transmitting channel | Pages 21, 22 and 27 | Every part receives its own channel (S7-1); synth7 transmits nothing. |
| SYS INFO AVAIL and UNAVAIL | Pages 21 and 22 | A panel switch guarding the instrument's memory; synth7 takes system information always (S7-4). |
| Internal and cartridge MEMORY PROTECT | Pages 3, 19, 20, 22 and 32 | As above; a synth7 sound has no lasting memory (S7-4). |
| Everything transmitted: key on and off, controllers 1, 2, 4, 6, 64, 65, 96 and 97, program change, after touch, pitch bend, the dumps, the parameter change, active sensing | Pages 22 and 30 | A NeoTeletext instrument only receives. |
| "MIDI TRANSMIT ?" (sending all 32 voices from the panel) | Page 22 | A panel operation. |
| Active sensing, received (sound off after 666 ms without it) | Page 32 | The receiver's own loss handling replaces it (S7-24, S7-53). |
| The request for the DX1's performance data, format 2, 94 bytes | Page 32, "2-2-5" | It belongs to another instrument. |
| Controllers 6, 96 and 97, data entry | Pages 5, 30 and 32 | They act on a panel's selected parameter; open question 4 (S7-18). |
| MASTER TUNE ADJ, ±75 cents | Pages 6 and 27 | A tuning of the whole instrument to others; a synth7 sound is in tune by construction. Reached only by controller 6 (open question 4). |
| EDIT RECALL, VOICE INIT, CARTRIDGE FORMATTING, BATTERY CHECK, CARTRIDGE SAVE and LOAD, STORE, EG COPY, EDIT/COMPARE | Pages 3, 6, 7, 12, 19 and 20 | Operations of the instrument's panel and memory, with no message. A program does each by sending voices. |
| The cartridge and its 64 ROM voices, A1 to A32 and B1 to B32 | Pages 3 and 5 | Hardware and the maker's voices, which are not shipped (DEC-6428 item 6). Program changes 32 to 63: open question 3. |
| Program changes transmitted "when it is unavailable" | Page 30 (blue text) | Transmission. |
| The 32-voice dump as a message in a stream | Page 30; TX7 manual, printed page 36 | It is 4,104 bytes; `midi-architecture.md` carries a message longer than 256 bytes only as a bank (MIDI-28, MIDI-50, MIDI-51). It is taken as a bank (S7-42), and lifted into one by the server at the start of a program's music (MIDI-58). |
| The TX7 manual's voice parameter 156, OPERATOR SELECT | TX7 manual, printed pages 38 and 39 | It chooses which operator a panel edits; the DX7 manual's table ends at 155, and synth7 has no panel (S7-43). |

### 14.2 Taken with a difference

Each row is a departure from the adopted interface; where a requirement of `midi-architecture.md` section 11.1 sets the rule every synthesizer follows, that requirement is the departure's reason.

| Item | The instrument modelled | synth7 | Requirement |
|---|---|---|---|
| Channels | One receiving channel (page 32) | Sixteen parts, one a channel | S7-1; MIDI-69 |
| Pitch bend resolution | Most significant byte only (page 32) | All fourteen bits | S7-9; MIDI-91 |
| Pitch bend range | Function parameter 65 only (page 31) | Function parameter 65 and registered parameter number 0, the later holding (the architecture's open question 5, pending the owner) | S7-9; MIDI-90 |
| Volume, controller 7 | Lowest four bits ignored: eight steps (page 32) | All seven bits: 128 steps, by the one volume law of every synthesizer | S7-15; MIDI-82, MIDI-92 |
| Sustain and portamento switches | Values 0 (off) and 127 (on) (page 32) | Off below 64, on from 64 | S7-16, S7-17; MIDI-87 |
| Mode messages | 125 and 127 "all key off" with their value ignored, 126 "MONO all key off", 124 not listed (page 32) | Each of 124 to 127, whatever its value, is all notes off and nothing else | S7-19; MIDI-89 |
| All sound off, controller 120 | Not received (page 32) | Received: every voice of the part faded to silence over 21 milliseconds | S7-20; MIDI-86 |
| Reset all controllers, controller 121 | Not received (page 32) | Received, as RP-015 says and DEC-6464 requires of every synthesizer (DEC-6464 recorded as proposed, awaiting the owner's confirmation); volume unchanged | S7-20; MIDI-84 |
| All notes off, controller 123 | Not received (page 32) | Received | S7-20; MIDI-85 |
| Program changes 64 to 127 | Not defined (page 32) | The default voice, counted | S7-21; MIDI-59 |
| LFO WAVE | DX7 manual's table: 0 to 4, a misprint (page 31) | 0 to 5, six waveforms, as the TX7 and DX7 II manuals and the DX7 manual's own pages 13 and 27 give | S7-31 |
| A received dump | Stored as it arrives; protected by switches | Checked whole first; refused whole if faulty | S7-45 |
| Function parameters | One set, kept through power-off | One set a part, starting from S7-35 with every sound | S7-33, S7-35 |

### 14.3 The Grey Matter text

The file `dave-benson-dx7-E-midispec.txt` is the MIDI implementation of a third-party replacement firmware for the DX7 (section 1). Its modes, controllers, system real-time and common messages and system exclusive formats are that firmware's; none is part of the adopted interface and none is taken.

## 15. What NeoTeletext defines itself

Each item exists because no filed Yamaha manual defines it. (The order of the single-voice dump's data, the meaning of the parameter change's two high bits, the packed layout, and the codings of the scaling curves, the break point, the oscillator mode, the fixed-frequency steps and the detune, which an earlier version of this list held, are now stated by the TX7 manual and are no longer NeoTeletext's own.)

1. **The sixteen parts (S7-1, S7-2).** The instrument modelled is one part on one channel. Each channel is its own instrument so that every message keeps its meaning. DEC-6410 item 10; `midi-architecture.md`, MIDI-69.
2. **The order of note stealing beyond "the first note" (S7-3).** As built.
3. **Taking every message as received with system information available and memory protect off (S7-4).**
4. **The messages and behaviours common to every synthesizer that the adopted interface lacks (S7-19, S7-20, S7-9).** Controllers 120, 121, 123 and 124, and registered parameter number 0 with controllers 100, 101, 6, 38, 96 and 97 for it, as `midi-architecture.md` MIDI-9, MIDI-84 to MIDI-86, MIDI-89 and MIDI-90 require of every synthesizer; that reset all controllers also returns breath and foot to 0 (S7-20 item 2) is RP-015's own rule for a controller it does not name (page 2), and is listed here because the adopted interface does not receive controller 121.
5. **The frequency of a key, and that transpose moves the key that scaling follows (S7-8).** As built.
6. **That a stepped pitch bend rounds towards the centre (S7-9).**
7. **The scale from controller 5's 128 values to portamento time's 100 (S7-14).**
8. **That the portamento switch is on before any controller 65 (S7-17).** Open question 7.
9. **That controllers 125 and 127 take any value (S7-19).**
10. **Taking channel pressure as after touch (S7-22).** The instrument sends it and has parameters for it; its reception list does not name it; the TX7 receives it. Open question 5.
11. **Mono mode's return to a held key, its sixteen remembered keys and its legato (S7-26).**
12. **What a change of mode does to sounding notes, and that function parameter changes reach sounding notes (S7-33).**
13. **That the TX7 manual's assign bit order, stated for its performance parameters, serves the function parameters 71, 73, 75 and 77 (S7-34).**
14. **The function parameters a part starts with (S7-35).** Chosen to keep today's sound.
15. **The laws by which the four controllers act (S7-36)**, and the portamento time law (S7-27).
16. **Which voice parameters reach a sounding note (S7-44).**
17. **The default voice (S7-51).** *No longer NeoTeletext's own:* by DEC-6465's answer to open question 6 (awaiting the owner's confirmation) the default voice is the maker's initial voice of the DX7 II manual, printed page Add-8. The item is kept, so that the numbers of the items after it do not change. What remains NeoTeletext's own is only that the operator switch, for which the manual's "INIT" column gives no value, is all six on (S7-21).
18. **A whole-message check before anything is taken (S7-45).** Security.
19. **The derived codings no manual states (S7-31):** that algorithm value 0 is algorithm 1, that 1 is on for the two sync parameters, and that the mono-mode portamento modes are 0 fingered and 1 full time (S7-27, S7-33).
20. **synth7's restatement (S7-49 item 4)**: an edited voice restated as one single-voice dump, in the order given, under `midi-architecture.md` MIDI-93 to MIDI-99.
21. **The refusal of a synth7 sound naming more than two banks (S7-50).**
22. **The reading of the 32-voice dump as a bank only (S7-42)**, under `midi-architecture.md` MIDI-50, MIDI-51 and MIDI-58.

## 16. Open questions for the owner

**1. File the maker's data format sheet, or a document that holds it?** *Answered.*
The DX7 manual gives every message's header, count and checksum, and every parameter's number and range, but not the 128-byte packed layout, not the order of the single-voice dump's data in words, not the coding of the scaling curves, the fixed-frequency steps or the assign bits, and it contradicts itself on the LFO waveforms. The question asked for a document that holds the maker's full data format. It is answered by the TX7 manual (`manuals/yamaha-tx7-owners-manual.pdf`, printed pages 35 to 44), filed with the DX7 II manual as a second statement of the same format, and recorded in `dx7/documents.tsv`, whose row for the Grey Matter text was corrected at the same time. Section 10 was checked against it and agrees; S7-31, S7-34, S7-38 and S7-43 now cite it. What no filed manual states is listed in section 15.

**2. Should synth7 also accept the 32-voice dump in a block, as a message, or only as the sound's named bank?** *Answered by `midi-architecture.md`.*
A system exclusive message in a block is at most 256 bytes after `F0` (MIDI-28), a message is never split across events or blocks (MIDI-50), a longer one travels only as a bank (MIDI-51), and a dump at the start of a program's music is lifted into a bank by the server while one after the first note on is refused (MIDI-58). The 32-voice dump is therefore taken only as a bank (S7-42). A recorded stream that changes the bank after its first note must be split into two sounds by its author.

**3. Program changes 32 to 63: a cartridge bank?** *The same question as `midi-architecture.md`'s open question 3 (several banks for one sound), which it recommends answering yes.*
The adopted interface uses program changes 32 to 63 for the 32 voices of a cartridge (pages 30 and 32). Today synth7 ignores them. S7-50 is written for the architecture's recommended answer: a synth7 sound may name a second 32-voice dump as its cartridge bank, and program change `32 + p` chooses its voice `p`, so the adopted interface's whole program range works and a sound may hold 64 voices; a synth7 sound naming more than two banks is refused. If the architecture's question is answered no (one bank a sound), program changes 32 to 63 set the default voice and are counted, as 64 to 127 do.
- Answered by DEC-6465 (awaiting the owner's confirmation): the architecture's open question 3 was answered with its option A, 1 to 10 banks a sound, so S7-50 stands as written: a synth7 sound may name a second 32-voice dump as its cartridge bank, reached by program changes 32 to 63.

**4. Controllers 6, 96 and 97, the data entry controls: leave out, or give them a meaning beyond registered parameter number 0?**
On the instrument they move the panel's slider and keys, which act on whichever parameter the panel last selected; controller 6 on reception acts on master tune only (page 32). The TX7 uses them to alter "voice or function parameters selected with Parameter Change" when its data entry receive switch is on (TX7 manual, printed page 34). Under `midi-architecture.md` MIDI-90 they now act on registered parameter number 0 while it is selected (S7-9); the question is what they do otherwise.
- *Option A: leave all three out otherwise* (S7-18). A program changes a parameter with a parameter change, which names it.
- *Option B: controller 6 as master tune of the part,* value 64 the centre, the range ±75 cents scaled linearly (NeoTeletext's own scale); 96 and 97 left out.
- *Option C: as the TX7 does,* 6, 96 and 97 alter the voice or function parameter last named by a parameter change on the part's channel.
- *Recommendation:* A. Master tune serves tuning an instrument to a band, which a NeoTeletext sound never needs, and the scale would be invented; C is another instrument's behaviour, which a parameter change already gives exactly.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: controllers 6, 96 and 97 do nothing outside registered parameter number 0 (S7-18).

**5. Channel pressure (after touch): take it, though the DX7's reception list does not name it?**
The instrument sends channel pressure and has after-touch range and assign parameters that a parameter change sets, but its reception list on page 32 does not name the message. The TX7, the maker's tone-generator module of the same voice format, receives it (TX7 manual, printed pages 32 and 34).
- *Option A: take it* (S7-22), as the one message that plays the after-touch parameters.
- *Option B: ignore it,* as the DX7's reception list strictly reads; the after-touch parameters are then settable but have no effect.
- *Recommendation:* A, now corroborated by the TX7's reception of the same message.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: synth7 takes channel pressure (S7-22), as the TX7 manual confirms for the same voice format.

**6. The default voice: keep synth7's, or take the maker's initial voice?**
synth7's default voice (S7-51) was, as built, a plain sine at algorithm value 15, named "PLAIN SINE". The DX7 II manual gives the maker's initial voice value by value (printed page Add-8): the same in every parameter but algorithm value 0 and the name "INIT VOICE". Both sound one plain sine.
- *Option A: take the maker's initial voice:* algorithm value 0 and the name "INIT VOICE", every other value as S7-51.
- *Option B: keep synth7's,* as built.
- *Recommendation:* A, under DEC-6453 (nothing of our own where the maker's exists); it changes no sound.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A. S7-51 now specifies the maker's initial voice, algorithm value 0 and the name "INIT VOICE", checked against the DX7 II manual's printed page Add-8.

**7. The portamento switch: on at a sound's start but off after reset all controllers?**
S7-17 starts the switch on, so that a portamento time sent by a parameter change is heard without a pedal (NeoTeletext's own); `midi-architecture.md` MIDI-84 puts the portamento pedal off on reset all controllers, in every synthesizer. A part therefore glides before controller 121 and not after it.
- *Option A: as written:* on at the start, off after controller 121.
- *Option B: off at the start too,* so that a part glides only after controller 65 at 64 or more, as on an instrument whose pedal is plugged in and up.
- *Option C: on after controller 121 too,* a departure from MIDI-84 for synth7, against the owner's rule of one behaviour (DEC-6464).
- *Recommendation:* A until RP-015 is filed and read (MIDI-84 rests on it); then B if RP-015 sets the portamento pedal off, so that start and reset agree.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: on at a sound's start, off after controller 121; revisited when RP-015 is filed.
- Revisited on 18 November 2026, when RP-015 was filed (rdm SRC-6468): it sets the portamento pedal off ("Set Pedals (#64, #65, #66, #67) to 0", page 2), so option A, as written, complies with RP-015 and MIDI-84. The recommendation's condition for option B is met; B changes only the switch's state at a sound's start (S7-17), which RP-015 does not govern, so the written answer A stands and the choice of B is left with the owner.

**8. A bank given as a list of fewer than 32 voices.**
`midi-architecture.md` MIDI-15 lets a program give a bank as a list of 1 to 128 patches, but a synth7 bank image is exactly one 32-voice dump (MIDI-56, S7-49), which holds 32.
- *Option A: the server fills the dump's missing voices with the default voice (S7-51)* and builds the 32-voice dump; a list of more than 32 voices is refused.
- *Option B: the server refuses a list of other than exactly 32 voices.*
- *Recommendation:* A: it keeps today's banks of fewer than 32 voices working, and the default voice is what a missing program already plays (MIDI-59).
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: the server fills a bank given as fewer than 32 voices with the default voice (S7-51) and refuses more than 32.

## 17. Differences from what is built today

What exists is described in `synthesizer-wire-format.html` and in synth7's source. Implementing this document changes the following.

**Voices and banks.**
1. Today a bank is a sound of codec 5 whose blocks are 128-byte packed voices, 1 to 32 of them, read once when the sound starts (`instruments.rs`, `bank`); the server checks only that each byte is at most 127 and the receiver range-checks each field. Under decision A4 a bank is the 32-voice dump itself, 4,104 bytes byte for byte (S7-41, S7-49), stored as a bank object of the bank codec and named by a sound among its one or two banks (`midi-architecture.md`, MIDI-55 to MIDI-57; S7-50). Its code is 19, and a synth7 sound's 13, if the architecture's open question 1 is answered as it recommends; otherwise codes 5 and 4 stay, with their contents changed (S7-49 item 3). DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation). A bank of fewer than 32 voices no longer exists: a dump always holds 32 (open question 8).
2. Today the rack has one bank and no current voice: a part plays `bank.get(program)` at each note on (`rack.rs`, `note_on`). Each part gains a current voice (S7-2), set by program change (S7-21), single-voice dump (S7-40) and parameter change (S7-44). `Rack` needs a voice of 155 parameters a part.
3. Today a voice can be made only by unpacking 128 bytes (`Patch::from_packed`) or from fields (`Patch::new`). It gains the 155-byte form of the single-voice dump (S7-38) and single-parameter edits (S7-43, S7-44), each range-checked (S7-29).
4. Today `operators_on` holds operator 1 in bit 0 (`patch.rs`). Parameter 155, as all three of the maker's manuals give it, holds operator 1 in bit 5 and operator 6 in bit 0 (S7-30); the code's order, or the conversion at the message, must follow the manuals.
5. Today the voice is checked with LFO wave up to 5 (`MAX_LFO_WAVE`), as S7-31 keeps, citing the TX7 and DX7 II manuals. The comments of `patch.rs` that cite an unfiled document of 1993 for the packed layout are to cite the TX7 manual, printed page 44, instead (section 10). Whether the parameter layer reads a fixed-frequency coarse value as the TX7 manual tables it (1, 10, 100 and 1,000 Hz repeating every four values) is to be checked and, if not, changed (S7-31).
6. Today a program change chooses 0 to 31 and ignores the rest (`program_change`). Under S7-50, 32 to 63 choose from a cartridge bank (the architecture's open question 3), and a program change that reaches no voice sets the default voice and is counted (S7-21). Today the receiver's slot check also refuses a program change whose (absent) second data byte is not 0 (`instruments.rs`, `common`); under decision A3 a program change is the ordinary two-byte message.

**Channel messages.**
7. Today synth7 acts on controllers 1, 7, 64, 120, 121 and 123 only, and the receiver passes over any other controller before synth7 sees it (`instruments.rs`, `CONTROLLERS`; the server and the kit refuse it). It gains controllers 2, 4, 5, 65, 124, 125, 126 and 127, and controllers 6, 38, 96, 97, 100 and 101 for registered parameter number 0 (S7-10, S7-9), and the server and the receiver must allow them for synth7; the kit holds no such rule (DEC-6462).
8. Today channel pressure is passed over by the receiver for synth7 (only synth80 takes it). It is taken (S7-22, open question 5).
9. Today controller 121 resets the wheel, bend and pedal. It also resets breath, foot and pressure, puts the portamento switch off and clears the registered parameter number selection, as `midi-architecture.md` MIDI-84 requires (S7-20). Controller 120's fade of 21 milliseconds is kept (MIDI-86).
10. Today the modulation wheel always adds pitch depth (`note.rs`). It acts through function parameters 70 and 71 (S7-11, S7-36), whose defaults keep today's effect (S7-35).

**Function parameters.**
11. Today synth7 has no function parameters: the bend range is fixed at 2 semitones (`PITCH_BEND_SEMITONES`), there is no bend step, no mono mode, no portamento or glissando, and no foot, breath or after-touch control. Each part gains the fourteen of S7-33, the mono mode of S7-26, the portamento and glissando of S7-27, and the controller laws of S7-36, with EG bias, which needs an attenuation per operator from the controllers that the engine does not have today.

**System exclusive.**
12. Today system exclusive cannot be expressed in a block (fixed 4-byte slots); the 32-voice dump is read only by the kit (`synth7BankFromSysex`) and by `Bank::from_sysex`, before a bank is sent. Under decision A3 a block can carry system exclusive of up to 256 bytes, and synth7 takes the single-voice dump and the parameter change in a stream, and the 32-voice dump as a bank (S7-37 to S7-45), refusing a faulty one whole and counting it. The server takes over the reading of dumps, the packing of voices, the building of banks and the restatement from the kit (DEC-6462; `midi-architecture.md`, MIDI-13 and MIDI-22); the kit's reader becomes types and a call, and the kit's program repeater becomes the server's restatement (S7-49 item 4).
13. A fuzz target for synth7's system exclusive reader is added (S7-45).

**The block.**
14. Today a synth7 block is 1 to 16 slots of four bytes (a time, a status byte, two data bytes) and the format cannot hold more than 800 events a second or any system exclusive (DEC-6410 item 9). Under decision A3 it becomes a Standard MIDI File track-event list with a tick of 0.1 millisecond, at most 1,005 bytes and 256 events (`midi-architecture.md`, MIDI-23 to MIDI-31). That change is the architecture document's and is the same for every family; synth7's part of it is the system exclusive of section 9.
15. Today a message takes effect at the start of synth7's next 32-sample step, up to 0.67 milliseconds late (`rack.rs`). It must take effect at its own sample (S7-52; MIDI-5, MIDI-36), so the rack must begin a step at each event's sample.
16. Today a lost block releases notes and lifts pedals; it will also clear every part's registered parameter number selection (S7-53).

**Tests and documents.**
17. The tests that build banks from 128-byte blocks (`tests/synth7_rack.rs`, the engine's `tests/synths.rs`, the server's and the kit's bank tests) change to the 4,104-byte dump; new tests are those each requirement's "Verification" names. The module documentation of `patch.rs` and `rack.rs` is rewritten to cite this document's requirements once they are rdm requirements. The two HTML documents in `synthesizer-reference/` describe the old form and are regenerated.
18. `dx7/documents.tsv`'s row for `dave-benson-dx7-E-midispec.txt` has been corrected to what the file holds (the MIDI implementation of a third-party replacement firmware, with none of the maker's byte layouts), and the TX7 and DX7 II manuals have rows of their own. DEC-6460's sentence that calls the file "Dave Benson's transcription of the data-format sheet … for checking offsets" still describes it as the maker's data format and is to be revised to name the TX7 manual as the source of the packed layout.

**The default voice.**
19. Today the default voice (`Patch::DEFAULT` in `patch.rs`, NeoTeletext's own choice) has algorithm value 15 (algorithm 16) and the name "PLAIN SINE". Under S7-51, by DEC-6465's answer to open question 6, it becomes the maker's initial voice of the DX7 II manual (printed page Add-8): algorithm value 0 (algorithm 1) and the name "INIT VOICE", every other parameter as today. The sound does not change, since with only operator 1 at a level above 0 both algorithms sound that operator alone; the tests that compare a voice with the default voice byte for byte, and any comment that names "PLAIN SINE", change with it.
