# synth80: the programming interface

**Purpose.** This document specifies how synth80 is played and programmed: every MIDI message it takes, what each does, every controller number it answers and the synth80 control each one moves, what a synth80 patch is, and how the instrument's preset tones, memories, banks and program changes fit together. It is the basis for implementing synth80's part of the synthesizer protocols.

**Scope.** synth80 only: the eight-voice instrument with two channels a voice and touch response that models the Yamaha CS-80 (`neoteletext-common/docs/audio/synthesizers.md` says once which instrument each synthesizer models). The transport (blocks, records, packets), the form of a block, how a bank of patches is stored and named, the restatement of a live sound, and the messages common to every synthesizer belong to the architecture document, `midi-architecture.md` in this folder, whose requirements are cited as MIDI-1 to MIDI-125; this document states what synth80 needs of them, refers to them, and lists where the adopted interface departs from them. The typed interface through which a program sends synth80's patches and music belongs to the Rust server's document (DEC-6462: the server is the one implementation, and the TypeScript and Python kits are thin clients of it); this document gives the server the tables it implements. The sound of the instrument (its oscillators, filters, envelopes and effects) is not specified here.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

**What the owner should read first.**
1. The adopted interface is real and nearly complete. The "MIDI Specifications" table of the Deckard's Dream manual (revision 1.3.0, PDF pages 71 to 74) gives a controller number, a range and, for switches and selectors, value bands, for all 26 controls of each of the two layers, for 23 master controls, and for bank select, the modulation wheel, volume and the sustain pedal: 79 rows. Every one of synth80's 52 tone controls and 21 of its 33 other controls has a row there (section 5).
2. Twelve of synth80's controls have no row, because Deckard's Dream has no such control: the ring modulator's five levers, the two sustain controls of the CS-80's SUSTAIN section, and the five controls of its tremolo and chorus. Their controller numbers are the one place NeoTeletext must invent; section 6 gives the rule, the numbers and the alternatives, and open question 2 puts the choice to the owner.
3. The adopted table assigns controller 120 to GLIDE MODE. MIDI 1.0 gives controller 120 to All Sound Off (MIDI 1.0, to be checked), which every NeoTeletext synthesizer takes (decision A1; `midi-architecture.md`, MIDI-9 and MIDI-86, which require synth80 to move GLIDE MODE). The two cannot share the number; this document keeps All Sound Off and moves GLIDE MODE to controller 3 (section 6). Open question 3 records the choice, which the architecture's requirements settle.
4. The table gives each controller's range but never says which end of a slider value 0 is, nor which band of a switch or selector is which position. Deckard's Dream's sliders, like the CS-80's, have their greatest effect at the top for some controls and at the bottom for others (manual, PDF page 23; CS-80 owner's manual, page 6). This document takes value 0 as the end of least effect, which is how synth80's patch already counts every lever, so that today's lever values carry over unchanged; open question 1 gives the alternative (value 0 at the bottom of the slider) and lists every control whose meaning would invert.
5. Because the adopted table already lists the CS-80's tone controls in the order of the CS-80's memory panel, which is the order of synth80's patch today, the synth80 patch stays 85 values in today's order. What changes is how switches and selectors are coded, a third position of the glide switch, and that every value from 0 to 127 is valid in every place (section 9 and section 17).
6. The filed manual has errors that the requirements resolve explicitly: a misnamed controller (107), a garbled name (8), a controller out of sequence (119), a heading that contradicts its own text (RESh), a contradiction about what the touch response's SPEED follows, and two paragraphs copied from the manual of another instrument ("Kijimi", PDF pages 12 and 68). Section 5.6 lists each.
7. Where the adopted interface departs from the one rule the architecture sets for a behaviour common to every MIDI instrument (`midi-architecture.md` section 11.1, MIDI-84 to MIDI-92), synth80 follows the architecture's rule and this document lists the departure (section 14.2). Two of those rules change what is built: pitch bend becomes a range in semitones set by registered parameter number 0, in place of the CS-80 ribbon's law (S80-7, open question 4), and controller 64 holds released keys as MIDI's sustain pedal does, in place of the CS-80's foot switch, with the SUSTAIN lever now always in effect (S80-26, open question 7).

---

## 1. Sources

| Short name here | File | What it is used for |
|---|---|---|
| **DD manual** | `~/devel/teletext-reference/synthesizers/cs-80/manuals/black-corporation-deckards-dream-manual-1.3.0.pdf` ("Deckard's Dream, Rev 1.3.0, User Manual - Sept. 2019", Black Corporation; 74 pages; SHA-256 c42c29d2305f3b65411c12004beac6ca540c2b23bc976b0025728166407623ef). Its pages carry no printed numbers; it is cited by PDF page. | The adopted interface. "MIDI SPECIFICATIONS", PDF pages 71 to 74: the controller table. "PANEL LAYOUT", PDF pages 4 to 10: the 55 numbered controls. "SETUP AND CONNECTIONS", PDF pages 10 to 12: MIDI and MPE. "BANKS & PRESET SELECTION", PDF pages 16 to 22: banks, bank select, program change, what a saved patch holds. "PROGRAMMING", PDF pages 22 to 43: each control's direction (Top=Max/Bottom=Min and its inverse) and meaning. "SETTINGS", PDF pages 43 to 69: the MIDI, voice, time, keyboard and other settings, global and per patch. All 74 pages were read. |
| **CS-80 owner's manual** | `~/devel/teletext-reference/synthesizers/cs-80/manuals/Yamaha_CS-80_Owners_Manual_archiveorg.pdf` ("CS-80 Polyphonic Synthesizer Instruction Manual", Yamaha; 56 PDF pages; its printed page n is PDF page n + 4; the photograph inside the front cover, PDF page 3, numbers the controls [1] to [46]) | The instrument modelled: its panel and the meaning of every control, the tone selectors, presets and memories, the sustain and portamento/glissando sections, the ribbon, the ring modulator, the tremolo/chorus, the touch response, the rear-panel connections and the specifications. Pages 1 to 16, 19 to 23, 28 to 30, 34 to 39 and 49 were read for this document. |
| **synth80's source** | `~/devel/neoteletext-renderer-teletext/crates/neoteletext-audio-instruments/src/synth80/patch.rs`, `mod.rs`, `voice.rs`, `law.rs` and `presets.rs`, as they stood on 18 November 2026 (engine commit `dd0421c6`) | What is built today: the 85-byte patch (two tones of 26 bytes and 33 other bytes), the messages taken, the touch routes, the laws of the levers, the 22 preset tones. Each constant there names its own source (the service manual KEC-4223, the adjustment procedure, the owner's manual). |
| **Wire format as built** | `~/devel/teletext-reference/synthesizers/synthesizer-wire-format.html` and `programming-the-synthesizers.html` (read from the code on 18 November 2026; they use the old name "CS-80" for synth80) | What exists today on the wire and in the kit, for section 17. |
| **The architecture document** | `midi-architecture.md` in this folder | The block, the bank, the restatement, the codec numbers, the common MIDI behaviours (section 11.1) and the bounds this document refers to, cited by requirement number (MIDI-n) or open question. |

**Documents that are not filed.** No copy of the MIDI 1.0 Detailed Specification, of the Standard MIDI Files 1.0 specification or of the MIDI Association's Recommended Practice RP-015 ("Response to Reset All Controllers") is filed in `~/devel/teletext-reference/`. They are listed as documents to obtain in `midi-architecture.md` section 1.5. This document uses MIDI 1.0 only for what is common to all MIDI: the status bytes; that a note on of velocity 0 is a note off; the 14-bit pitch bend and its centre; registered parameter number 0; the standard meanings of controllers 0, 1, 5, 6, 7, 8, 38, 64, 96, 97, 100, 101 and 120 to 127; and which controller numbers MIDI 1.0 leaves undefined (section 6). Every fact that rests on MIDI 1.0 or RP-015 is marked "(MIDI 1.0, to be checked)" or "(RP-015, to be checked)" and is to be checked against the filed copy before implementation.

Decisions this document follows: DEC-6453 (each instrument is programmed exactly as its most well-known existing interface does it; NeoTeletext invents nothing unless nothing exists, and records why), DEC-6458 (the provenance of synth80 and the choice of Deckard's Dream's interface), DEC-6461 (the names), DEC-6462 (the Rust server is the core of the interface: it validates, packs, builds blocks, splits and restates; the TypeScript and Python kits are thin and hold no instrument logic), DEC-6464 (every synthesizer answers Reset All Controllers identically, by RP-015, leaving volume unchanged; recorded as proposed, awaiting the owner's confirmation), DEC-6410 and DEC-6429 (instruments as codecs of the audio profile), DEC-6428 (the clean-room rules), and the architecture decisions A1 to A6 of the brief of 18 November 2026.

No web page was fetched and no reference program was opened for this document.

## 2. Terms

- **synth80.** NeoTeletext's eight-voice synthesizer of two complete lines a voice (one for each channel), with keys that sense how hard they are struck and how hard each is pressed.
- **The instrument modelled.** The Yamaha CS-80. It is named in this document only where a source is cited or its panel is described.
- **The adopted interface.** The MIDI implementation of Black Corporation's Deckard's Dream, an eight-voice instrument "inspired by the Yamaha CS-80" (DD manual, PDF page 13), as the DD manual revision 1.3.0 states it.
- **Channel I and channel II.** The two rows of the CS-80's panel, each a complete line in every voice (CS-80 owner's manual, page 7, items [3] and [4]). The DD manual calls them **layer I and layer II** (PDF page 22), and its controller table calls them **A** and **B**: "A" is layer I and "B" is layer II. The evidence is that the table's first controller, 40, is "PULSE WIDTH MODULATION SPEED A", and the DEBUG setting names "the first slider, PWM SPEED A" (PDF page 66), and the first slider of the panel is layer I's control 1 (PDF page 5); and the mod wheel destinations name "PWM SPEED 1 (CC 040)" and "PWM SPEED 2 (CC 067)" (PDF page 49).
- **Tone.** The 26 controls of one channel's row, in the order of the CS-80's memory panel (CS-80 owner's manual, page 36): what a tone selector button recalls and a memory holds.
- **Master control.** A control that is neither channel's: the DD manual's "MASTER SYNTHESIS PARAMETERS" (PDF page 34) and the CS-80's controls outside the programmable panels.
- **Lever.** A continuous control (the CS-80 calls them sliders and levers; the DD manual calls them sliders). Its value in synth80 is a position from 0 to 127.
- **Switch.** A control of two positions. **Selector.** A control of three or six positions.
- **Controller.** A MIDI control change's controller number, 0 to 127. **Value** is its data byte, 0 to 127.
- **Band.** The set of values of a controller that select one position of a switch or selector, as the DD manual's table writes them ("0-64/65-127").
- **Canonical value.** The one value a sender writes for a given position of a switch or selector, where a band holds several values.
- **End of least effect.** For a lever whose DD manual heading says "Top=Max/Bottom=Min" or "Top=Min/Bottom=Max", its Min end; for a pitch lever ("Top=Low/Bottom=High"), its Low end; for the other levers, as section 5.4 says lever by lever.
- **Patch.** The positions of all 85 of synth80's controls. On the wire it is the 85 values of section 9.
- **Preset tone.** One of the CS-80's 22 tones held in its circuits, eleven for each row (CS-80 owner's manual, page 7, item [3]; page 49, "Preset Patches").
- **Memory.** One of the CS-80's four small copies of a tone's panel (CS-80 owner's manual, page 23 and page 36, item [46]).
- **Bank.** The set of patches a synth80 sound plays from, chosen among by program change and bank select. How a bank is stored and named is the architecture document's (MIDI-55 to MIDI-57): a stored object of the bank codec, which a sound names among its 1 to 10 banks.
- **Block.** 20 milliseconds of a sound's input, 960 samples at 48,000 Hz (decision A2). Its content is a Standard MIDI File track-event list whose tick is 0.1 millisecond (decision A3), of at most 1,005 bytes and 256 events (MIDI-23 to MIDI-31).
- **Counted as ignored.** A message the instrument does not act on adds one to a count the instrument keeps (`ignored_events` today), and nothing else happens. Nothing is an error. It is what the architecture document calls "passed over and counted" (`midi-architecture.md` section 2); the server refuses such a message in what a program sends (MIDI-10).
- **Restatement.** The messages that bring synth80 from any state to the state it should be in, which the server writes into a live sound at least once a second and at the start of every stored sound (MIDI-93 to MIDI-99; S80-46).
- **Not stated in the source.** The filed document does not say. Nothing is supplied from memory in its place; where synth80 needs an answer, the answer is NeoTeletext's own and is listed in section 15.

## 3. What the two instruments are (facts, not requirements)

**The instrument modelled has no MIDI.** The CS-80 owner's manual lists every connection of the instrument: the LEFT, GENERAL and RIGHT outputs with their HIGH/LOW switch, the FOOT CONTROLLER and FOOT SWITCH jacks, the EXTERNAL INPUT jack with its LEVEL control (page 4, "Connections", and the photograph of the rear panel there), and the headphone jack under the keyboard (page 5). Its specifications (page 49) name the same connections and no other, and describe its circuitry as "All solid state; keyboard and note assigning circuitry is digital; all audio circuitry is analog". It predates MIDI and has no digital interface of any kind. Its sounds are stored as positions of levers: its 22 preset tones as resistors on circuit boards, and its four memories as miniature copies of a tone's levers, set by hand and "fine tuned" by ear (page 23, item [46]; page 36, item [46]). There is therefore no MIDI implementation and no patch format of the CS-80 to be compatible with.

**The adopted interface is a modern instrument made after the CS-80.** Deckard's Dream is "an 8-voice polyphonic analog synthesizer inspired by the Yamaha CS-80" (DD manual, PDF page 13), with two synthesis layers a voice whose controls are the CS-80's tone controls, a master section, 384 presets in three banks (PDF pages 13, 15 and 17), MIDI over a DIN socket and USB, and modes for channel pressure, polyphonic aftertouch and MPE (PDF pages 11, 12, 15 and 45). It has no ring modulator, no tremolo or chorus, no ribbon and no SUSTAIN section; it has coarse and fine pitch, which synth80 takes outside the patch (S80-47), voice modes, and many settings in menus (sections 12 and 14). Its manual publishes a controller table (PDF pages 71 to 74) and no system exclusive format: its presets are backed up as files (`dd_bank_1.p`, `dd_bank_2.p`) from a USB drive mode whose format is not stated (PDF page 21).

---

## 4. The channel messages

### 4.1 What the adopted interface says it recognises

The DD manual has no MIDI implementation chart. What it says Deckard's Dream recognises, gathered from every page that mentions a message:
- Notes from "standard hardware MIDI controllers", "a polyphonic aftertouch controller or MIDI Polyphonic Expression (MPE) controller", "external hardware sequencers, or via automation over USB" (PDF pages 11 and 12).
- Note-on velocity ("INITIAL: This term is used to describe Deckard's Dream's responsiveness to note-on velocity", PDF page 23).
- Aftertouch ("AFTER: ... responsiveness to aftertouch modulation", PDF page 23), as channel pressure or polyphonic aftertouch according to the global MIDI MODE setting (PDF pages 17 and 45).
- MPE, as a third MIDI MODE: the master channel is chosen from 1 to 8 and "Deckard's Dream assigns MIDI channels 9-16 to each of its 8 voices" (PDF page 46). "Polyphonic pitch-bend" is listed among its controls (PDF page 15), and controller 74 from an MPE controller may be sent to one of nine destinations by the global CC74 REPLACE setting (PDF page 47).
- Pitch bend, whose range is a global setting with no message, "The default setting is 3 semitones. The allowable range is 1 to 99 semitones" (PDF page 60).
- Control changes, when the global CC RECEIVE setting is ON (PDF page 46), of the 79 controllers of the table (PDF pages 71 to 74).
- Program change and bank change: "Deckard's Dream responds to standard Program Change and Bank Change MIDI messages. Make sure that CC Receive is turned ON in the MIDI menu. Bank change uses MIDI CC message 0, with the values 0 = User Bank 1, 1 = User Bank 2, and 2 = Factory Bank" (PDF page 18); program change allows "selection of the next, previous, or specific patch numbers from the current bank, or from a different bank entirely" (PDF pages 18 and 19).
- System exclusive is mentioned once, for uploading a tuning program in `.mts` form "using any sysex librarian software, which is also used to save presets on a computer" (PDF page 68). No byte of any system exclusive message is given, and the paragraph names "Kijimi", another instrument, in place of Deckard's Dream.

Not stated in the source: note off (MIDI 1.0 defines it, and a note could not otherwise end); release velocity; the range of note numbers; which note is middle C; any system common or system real-time message; any mode message other than the controller table's; registered or non-registered parameter numbers.

### 4.2 Requirements

**S80-1. The messages synth80 acts on.** synth80 MUST act on exactly these MIDI 1.0 channel messages, and on no other: note off (status `0x8n`); note on (status `0x9n`); polyphonic key pressure (status `0xAn`); control change (status `0xBn`) of the controllers that S80-7, S80-10, S80-11, S80-18, S80-20, S80-24 to S80-29, S80-36 and S80-47 name; program change (status `0xCn`); channel pressure (status `0xDn`); and pitch bend (status `0xEn`). Here `n` is the channel, 0 to 15. A control change of any controller not named, and every system exclusive message, MUST be counted as ignored and MUST change nothing in the instrument; the server MUST refuse each of them in what a program sends (MIDI-10). System common and system real-time messages are never carried in a block (MIDI-8).
- Reason: These are the messages the adopted interface recognises (section 4.1), with the controllers NeoTeletext adds for the CS-80 controls the adopted interface lacks (section 6), the messages of NeoTeletext's common layer (section 7; MIDI-9), and the adopted interface's coarse and fine pitch, taken as performance controllers (S80-47; DEC-6465).
- Source: DD manual, PDF pages 11, 12, 15, 17, 18, 23, 45 to 47, 60 and 71 to 74. MIDI 1.0 for note off (MIDI 1.0, to be checked). `midi-architecture.md`, MIDI-8, MIDI-9 and MIDI-10.
- Verification: A test sends one message of every status from `0x80` to `0xEF`, and a control change of every controller from 0 to 127, and checks which change the instrument's state, and that each of the others adds one to the count of ignored messages and leaves the rendered samples identical to a run without it; a server test checks each of the others is refused.

**S80-2. Channels.** synth80 MUST act on a channel message alike whatever its channel, 0 to 15: the sixteen channels are one keyboard and one panel.
- Reason: A synth80 sound holds one instrument. Deckard's Dream receives one channel, chosen by a global setting with no message ("any of the 16 MIDI channels may be selected ... by default, channel 1"), or, in MPE mode, a master channel and eight voice channels; decision A6 lets a global setting of the hardware be left out. It is what is built today (`mod.rs`: "The instrument is one part and hears every channel").
- Source: DD manual, PDF page 46. synth80's source, `mod.rs` (`Synth80::event`). `midi-architecture.md`, MIDI-67 and MIDI-68 (a one-part family hears every channel, and lists the adopted interface's single receive channel as a departure). The departure is listed in section 14.2.
- Verification: A test plays one score sixteen times, each on a different channel, and once with its messages spread over all sixteen, and checks every run's samples identical.

**S80-3. Note on and velocity.** On a note on whose velocity is 1 to 127, synth80 MUST take the key (data byte 1, 0 to 127) as struck with that velocity, and assign it a voice by S80-31. The velocity MUST be the strength of the stroke, `velocity ÷ 127` of the hardest stroke, and MUST act through exactly these routes, each scaled by its lever: each channel's INITIAL BRILLIANCE (bytes 22 and 48 of the patch) opens that channel's filters; each channel's INITIAL LEVEL (bytes 23 and 49) raises that channel's level; the touch response's PITCHBEND (byte 67) starts the note below its pitch, the farther the harder the stroke, and lets it slide up to the pitch. A note on whose velocity is 0 MUST be taken as a note off of that key.
- Reason: The CS-80's keys sense how fast they are struck: "INITIAL BRILLIANCE [42] makes the notes brighter the harder you hit the key, and INITIAL LEVEL [43] makes the notes louder"; PITCHBEND "causes the pitch to begin below the note you play and then to quickly slide up to the proper pitch. The faster and harder you strike the keys, the more the pitch bends". Deckard's Dream takes note-on velocity for the same three controls.
- Source: CS-80 owner's manual, page 10, item [12] A; page 23, items [42] to [45]; page 36, items [42] and [43]; page 38, item [12]; page 49 ("Velocity Sensitive Touch Response"). DD manual, PDF page 7, items 23 and 24; PDF page 9, item 40; PDF pages 23, 32, 33 and 38. How many volts a stroke gives and how fast a stroke's effect drains away are synth80's own readings of the service manual (`voice.rs`, `STROKE_HARDEST`, `TOUCH_HOLD`, `TOUCH_BEND`). MIDI 1.0 for velocity 0 (MIDI 1.0, to be checked); `midi-architecture.md`, MIDI-88 (a note on of velocity 0 is a note off in every synthesizer).
- Verification: A test with INITIAL BRILLIANCE at 127 and the others at 0 plays one key at velocities 1, 64 and 127 and checks the low-pass filter's measured cutoff rises with velocity; the same for INITIAL LEVEL and the level, and for PITCHBEND and the depth of the starting pitch; with all three at 0 the three velocities give identical samples; a note on of velocity 0 releases the note exactly as a note off does.

**S80-4. Note off.** On a note off, synth80 MUST take the key as released. The release velocity MUST NOT change the sound. The pressure on a released key MUST become 0 (S80-5).
- Reason: The adopted interface does not mention release velocity, and the instrument modelled has none. The after-touch answers "when you press down on a key after it hits bottom", which a released key is not.
- Source: CS-80 owner's manual, page 36, items [44] and [45]. MIDI 1.0 (to be checked). synth80's source, `voice.rs` (`release`).
- Verification: A test checks note offs of release velocities 0, 64 and 127 give identical samples.

**S80-5. Polyphonic key pressure.** On a polyphonic key pressure, synth80 MUST set the pressure of every voice whose key is data byte 1 and is held to `data byte 2 ÷ 127` of a firm pressure. The pressure MUST act through exactly these routes, each scaled by its lever: each channel's AFTER BRILLIANCE (bytes 24 and 50) opens that channel's filters; each channel's AFTER LEVEL (bytes 25 and 51) raises its level; the touch response's SPEED (byte 68) speeds the sub oscillator; its VCO (byte 69) lets the sub oscillator move the pitch; its VCF (byte 70) lets the sub oscillator move the filters. The sub oscillator is one for all voices, so its speed MUST follow the hardest pressure of any held key. A key newly struck has a pressure of 0 until a pressure message for it arrives.
- Reason: The CS-80's keys sense pressure, key by key: "AFTER BRILLIANCE [44] and AFTER LEVEL [45] are similar to INITIAL BRILLIANCE and LEVEL, but are sensitive to key pressure"; "SPEED, VCO and VCF do the same thing as their counterparts in the Sub Oscillator section [11] ... these levers make the keyboard pressure sensitive". Deckard's Dream takes polyphonic aftertouch for the same controls: "Polyphonic aftertouch destinations: LFO speed, LFO to VCO amount, LFO to VCF amount, filter brilliance, volume level".
- Source: CS-80 owner's manual, page 10, item [12] B to D; page 23; page 36, items [44] and [45]; page 38, item [12]; page 49 ("Pressure Sensitive Touch Response"). DD manual, PDF page 7, items 25 and 26; PDF page 9, items 41 to 43; PDF pages 15, 33, 38 and 39. The DD manual contradicts itself on the touch response's SPEED: PDF page 9 (item 41) and PDF page 15 say key pressure, PDF page 38 says "based on velocity". synth80 follows the CS-80 and the DD manual's two other pages: pressure. One sub oscillator serving every key: CS-80 owner's manual, page 37, item [11] ("Processes both channels I and II") and synth80's source, `mod.rs` (`control`).
- Verification: A test holds two keys, sends pressure 127 to one and 0 to the other with AFTER LEVEL at 127, and checks only the pressed key's line grows louder; the same for AFTER BRILLIANCE; a test with the touch response's SPEED at 127 checks the sub oscillator's rate rises with the hardest pressure; a pressure for a key not held changes nothing.

**S80-6. Channel pressure.** On a channel pressure, synth80 MUST set the pressure of every voice whose key is held to `data byte 1 ÷ 127` of a firm pressure, with the routes of S80-5.
- Reason: Deckard's Dream offers channel pressure for "basic MIDI controllers that are not capable of polyphonic aftertouch". It is what is built.
- Source: DD manual, PDF pages 17 and 45. synth80's source, `mod.rs` (`event`). That synth80 takes both kinds of pressure at once, where Deckard's Dream takes the one its MIDI MODE setting selects, is listed in section 14.2.
- Verification: A test holds three keys, sends one channel pressure with AFTER LEVEL at 127, and checks all three lines grow louder by the same amount as three polyphonic key pressures of the same value would make them.

**S80-7. Pitch bend and its range.** On a pitch bend, synth80 MUST form the 14-bit number `data byte 2 × 128 + data byte 1`, whose centre 8,192 bends nothing, and MUST move the pitch of both channels of every voice by `(number − 8,192) ÷ 8,192` of the bend range, in semitones, linear in pitch (number 16,383 gives 8,191 ÷ 8,192 of the range upward, number 0 the whole range downward), the filters following as they follow the keys (MIDI-91). The bend range MUST be set by registered parameter number 0, pitch bend sensitivity (controller 101 at 0 and controller 100 at 0 select it; data entry, controller 6, gives the semitones and controller 38 the cents; increment, controller 96, and decrement, controller 97, step it), as MIDI-76 and MIDI-90 say. The range MUST be at most 99 semitones, a larger value being set to 99, and before any message it MUST be 3 semitones. A program change and controller 121 MUST NOT change the range (MIDI-84, MIDI-90). Every other registered parameter number, and every non-registered parameter number (controllers 99 and 98), MUST select no parameter of synth80: a data entry, increment or decrement after it changes nothing and is counted as ignored. The bend MUST apply to every sounding voice in SUSTAIN I and in SUSTAIN II mode alike (S80-32).
- Reason: The architecture sets one rule for pitch bend in every synthesizer (`midi-architecture.md`, MIDI-90 and MIDI-91, its open questions 5 and 6, pending the owner): all 14 bits, a range in semitones either way, set by registered parameter number 0 beside any message the adopted interface has. Deckard's Dream recognises pitch bend with a range in semitones that is a global setting with no message, 1 to 99 semitones, default 3 (PDF page 60), so its default and its most are synth80's, and registered parameter number 0 takes the place of the menu. Today synth80 takes pitch bend as the CS-80's ribbon, which "tunes the entire keyboard up or down in pitch", "approximately one octave" up and down "to a sub-audio frequency" (CS-80 owner's manual, page 14, item [19]), linear in frequency; that law is not a range either way and contradicts MIDI-90 and MIDI-91, so it is replaced, and the change is listed in section 14.2 and section 17. Open question 4 keeps the family's facts for the owner's answer to the architecture's open questions 5 and 6.
- Source: `midi-architecture.md`, MIDI-76, MIDI-84, MIDI-90 and MIDI-91. DD manual, PDF pages 15 and 60. CS-80 owner's manual, page 14, item [19]. synth80's source, `mod.rs` ("Pitch bend is the ribbon", `RIBBON_FLOOR`) and `voice.rs` (`RIBBON_REST`), which this requirement replaces. MIDI 1.0 for the 14 bits, the centre and registered parameter number 0 (MIDI 1.0, to be checked). The CS-80's statement that in SUSTAIN I mode "the ribbon only changes the pitch while you are holding down a key" and in SUSTAIN II "will also change the pitch during the sustain" (page 14) is not built and is not required; open question 4 asks whether to build it.
- Verification: A test holds a note and sends pitch bends of 0, 4,096, 8,192, 8,193, 12,288 and 16,383 with the range at its default, and checks the measured pitch against −3, −1.5, 0, a rise of 3 ÷ 8,192 semitone, +1.5 and +3 × 8,191 ÷ 8,192 semitones, each within 0.1 cent; a test sets the range by registered parameter number 0 to 1, 12, 99 and 127 semitones and checks a full bend against 1, 12, 99 and 99; a test checks a program change and controller 121 leave the range; a test checks a data entry after a non-registered parameter number is counted and changes nothing.

**S80-8. MPE is not taken as a mode.** synth80 MUST NOT treat any channel as an MPE master or voice channel: under S80-2 a pitch bend, pressure or control change on any channel applies to the whole instrument as S80-5 to S80-7 say, whatever channel its note was played on. Controller 74 MUST be counted as ignored.
- Reason: Deckard's Dream's MPE is a global mode chosen at its panel, with no message to select it; the manual states only that the master channel is 1 to 8 and that channels 9 to 16 are its eight voices (PDF page 46), that pitch bend is then "polyphonic" (PDF page 15), and that controller 74 may be redirected by a global setting (PDF page 47). It does not state how a voice channel's pitch bend, pressure or controllers combine with the master channel's, which an implementation would need. Open question 6 asks the owner whether to define it.
- Source: DD manual, PDF pages 11, 12, 15, 17, 45, 46 and 47.
- Verification: A test plays the same notes on channels 9 to 16 with a pitch bend on channel 10 only, and checks every voice is bent; a control change of controller 74 is counted as ignored.

**S80-9. System exclusive, system common and system real time.** synth80 MUST NOT act on any system exclusive message, of any length or content: the receiver counts each as ignored (a content error, MIDI-34), and the server refuses each in what a program sends for a synth80 sound (MIDI-10). It MUST NOT act on any system common or system real-time message, which a block never carries (MIDI-8): the server refuses them and the receiver passes them over and counts them.
- Reason: The adopted interface documents no system exclusive message: the one mention is of a tuning file uploaded by "any sysex librarian software" (PDF page 68), with no byte given; the instrument modelled has no digital interface. Neither source mentions system common or system real-time messages.
- Source: DD manual, PDF page 68. CS-80 owner's manual, pages 4 and 49. `midi-architecture.md`, MIDI-8, MIDI-10, MIDI-23 and MIDI-34.
- Verification: A receiver test puts system exclusive events of 1, 100 and 256 bytes after `0xF0` (the most a block carries, MIDI-28), a song position pointer and a timing clock into blocks and checks the samples identical to the blocks without them and each counted; a server test checks a synth80 events message holding any of them is refused.

---

## 5. The adopted controller table

### 5.1 How the table is read

The DD manual's table (PDF pages 71 to 74) has three columns: "MIDI CC", "RANGE" and "FUNCTION". Its ranges take four forms: "0-127" for a lever; "0-64-127" for a lever with a centre detent, 64 being the centre; "0-64/65-127" for a switch of two positions; "0-21/22-42/43-63/64-84/85-105/106-127" for a selector of six positions; "0-42/43-84/85-126" for GLIDE MODE, a switch of three positions; "0-1-2" for bank selection; and nothing for the sustain pedal. The table names a function and a range; it does not say which end of a lever value 0 is, which band of a switch or selector is which position, nor how a value becomes a position of the control between its ends. Those are settled in sections 5.4 and 5.5, and listed in section 15.

The panel the table addresses is that of PDF pages 5 to 10, whose controls are numbered 1 to 55 ("The controls for layer II are identical to controls 1 – 26 of layer I", PDF page 5). In the tables below, "DD" is that number and "CS-80" the number in brackets of the CS-80 owner's manual's photograph (PDF page 3).

### 5.2 The tone controls of channel I and channel II

**S80-10. The 52 tone controllers.** synth80 MUST move each tone control of each channel by the control change of the controller the table below gives, and by no other message than that, a program change (S80-35) or a patch (S80-33). The "Byte" columns are the control's place in the patch (section 9).

| Tone control | DD | CS-80 | Ch. I byte | Ch. I controller | Ch. II byte | Ch. II controller | DD range | DD function (channel I's; channel II's ends "B") |
|---|---|---|---|---|---|---|---|---|
| PWM SPEED | 1 | [20] | 0 | 40 | 26 | 67 | 0-127 | PULSE WIDTH MODULATION SPEED A |
| PWM | 2 | [21] | 1 | 41 | 27 | 68 | 0-127 | PULSE WIDTH MODULATION AMOUNT A |
| PW | 3 | [22] | 2 | 42 | 28 | 69 | 0-127 | PULSE WIDTH A |
| Square wave switch | 4 | [23] | 3 | 43 | 29 | 70 | 0-64/65-127 | SQUARE A |
| Sawtooth wave switch | 5 | [24] | 4 | 44 | 30 | 71 | 0-64/65-127 | SAW A |
| NOISE | 6 | [25] | 5 | 45 | 31 | 72 | 0-127 | NOISE LEVEL A |
| HPF | 7 | [26] | 6 | 46 | 32 | 73 | 0-127 | HIGH PASS FILTER BRILLIANCE A |
| RESh | 8 | [27] | 7 | 47 | 33 | 119 | 0-127 | HIGH PASS FILTER RESONANCE A |
| LPF | 9 | [28] | 8 | 48 | 34 | 75 | 0-127 | LOW PASS FILTER BRILLIANCE A |
| RESl | 10 | [29] | 9 | 49 | 35 | 76 | 0-127 | LOW PASS FILTER RESONANCE A |
| IL (filter envelope's initial level) | 11 | [30] | 10 | 50 | 36 | 77 | 0-127 | FILTER EG INITIAL LEVEL A |
| AL (filter envelope's attack level) | 12 | [31] | 11 | 51 | 37 | 78 | 0-127 | FILTER EG AFTER LEVEL A |
| Filter envelope A | 13 | [32] | 12 | 52 | 38 | 79 | 0-127 | FILTER ATTACK A |
| Filter envelope D | 14 | [33] | 13 | 53 | 39 | 80 | 0-127 | FILTER DECAY A |
| Filter envelope R | 15 | [34] | 14 | 54 | 40 | 81 | 0-127 | FILTER RELEASE A |
| VCF LEVEL | 16 | [35] | 15 | 55 | 41 | 82 | 0-127 | VCF LEVEL A |
| SINE | 17 | [36] | 16 | 56 | 42 | 83 | 0-127 | SINE LEVEL A |
| Amplifier envelope A | 18 | [37] | 17 | 57 | 43 | 84 | 0-127 | ATTACK A |
| Amplifier envelope D | 19 | [38] | 18 | 58 | 44 | 85 | 0-127 | DECAY A |
| Amplifier envelope S | 20 | [39] | 19 | 59 | 45 | 86 | 0-127 | SUSTAIN A |
| Amplifier envelope R | 21 | [40] | 20 | 60 | 46 | 87 | 0-127 | RELEASE A |
| LEVEL | 22 | [41] | 21 | 61 | 47 | 88 | 0-127 | LEVEL A |
| INITIAL BRILLIANCE | 23 | [42] | 22 | 62 | 48 | 89 | 0-127 | INITIAL BRILLIANCE A |
| INITIAL LEVEL | 24 | [43] | 23 | 63 | 49 | 90 | 0-127 | INITIAL LEVEL A |
| AFTER BRILLIANCE | 25 | [44] | 24 | 65 | 50 | 91 | 0-127 | AFTER BRILLIANCE A |
| AFTER LEVEL | 26 | [45] | 25 | 66 | 51 | 92 | 0-127 | AFTER LEVEL A |

The table runs through channel I's controllers 40 to 63 and 65 to 66, leaving out 64 (the sustain pedal), and channel II's 67 to 73, 119 and 75 to 92, leaving out 74 (which MPE controllers send for the vertical movement of a finger, PDF page 47). The order of each channel's 26 controls is the order of the CS-80's memory panel and of synth80's `Control` enum.
- Reason: These are the adopted interface's controllers for the 26 controls of each layer, which are the CS-80's 26 tone controls one for one.
- Source: DD manual, PDF pages 71 to 73 (the numbers and ranges), PDF pages 5 to 7 (items 1 to 26) and PDF pages 26 to 33 (each control). CS-80 owner's manual, PDF page 3 (items [20] to [45]) and page 36 (the memory panel, whose legend gives a tone's controls in this order). synth80's source, `patch.rs` (`Control`).
- Verification: A test sends, for each of the 52 controllers, values 0 and 127, and checks that exactly the patch byte the table names changes and no other; an assertion in the code checks that no controller appears twice in the tables of S80-10, S80-11 and S80-20.

### 5.3 The master controls

**S80-11. The 21 master controllers of the adopted table.** synth80 MUST move each of these master controls by the control change of the controller the table below gives.

| Master control | DD | CS-80 | Byte | Controller | DD range | DD function |
|---|---|---|---|---|---|---|
| FEET I | 30 | [5] | 52 | 102 | 0-21/22-42/43-63/64-84/85-105/106-127 | FEET A |
| FEET II | 31 | [5] | 53 | 103 | as FEET I | FEET B |
| DETUNE CH II | 29 | [6] | 54 | 95 | 0-64-127 | DETUNE OSC B |
| MIX I-II | 37 | [4] | 55 | 8 | 0-64-127 | MIX 43102 (sic) |
| BRILLIANCE (overall) | 38 | [7] | 56 | 109 | 0-64-127 | MASTER BRILLIANCE |
| RESONANCE (overall) | 39 | [8] | 57 | 110 | 0-127 | MASTER RESONANCE |
| KEYBOARD CONTROL BRILLIANCE LOW | 44 | [9] | 58 | 115 | 0-64-127 | KEYBOARD CONTROL - BRILLIANCE LOW |
| KEYBOARD CONTROL BRILLIANCE HIGH | 45 | [9] | 59 | 116 | 0-64-127 | KEYBOARD CONTROL - BRILLIANCE HIGH |
| KEYBOARD CONTROL LEVEL LOW | 46 | [10] | 60 | 117 | 0-64-127 | KEYBOARD CONTROL - LEVEL LOW |
| KEYBOARD CONTROL LEVEL HIGH | 47 | [10] | 61 | 118 | 0-64-127 | KEYBOARD CONTROL - LEVEL HIGH |
| SUB OSCILLATOR FUNCTION | 32 | [11] A | 62 | 104 | 0-21/22-42/43-63/64-84/85-105/106-127 | SUB OSCILLATOR WAVEFORM |
| SUB OSCILLATOR SPEED | 33 | [11] B | 63 | 105 | 0-127 | SUB OSCILLATOR SPEED |
| SUB OSCILLATOR VCO | 34 | [11] C | 64 | 106 | 0-127 | SUB OSCILLATOR TO VCO AMOUNT |
| SUB OSCILLATOR VCF | 35 | [11] D | 65 | 107 | 0-127 | SUB OSCILLATOR TO VAMOUNT (sic: the VCF, PDF pages 47 and 49) |
| SUB OSCILLATOR VCA | 36 | [11] E | 66 | 108 | 0-127 | SUB OSCILLATOR TO VCA AMOUNT |
| TOUCH RESPONSE PITCHBEND | 40 | [12] A | 67 | 111 | 0-127 | INITIAL PITCHBEND |
| TOUCH RESPONSE SPEED | 41 | [12] B | 68 | 112 | 0-127 | AFTER TO SUB OSCILLATOR SPEED |
| TOUCH RESPONSE VCO | 42 | [12] C | 69 | 113 | 0-127 | AFTER TO VCO AMOUNT |
| TOUCH RESPONSE VCF | 43 | [12] D | 70 | 114 | 0-127 | AFTER TO VCF AMOUNT |
| PORTAMENTO/GLISSANDO speed | 48 | [14] A | 79 | 5 | 0-127 | GLIDE TIME |
| PORTAMENTO/GLISSANDO selector | 49 | [14] D | 78 | 3 (see S80-20; the adopted table's 120) | 0-42/43-84/85-126 | GLIDE MODE |

- Reason: These are the adopted interface's controllers for the master controls that the CS-80 and Deckard's Dream share. GLIDE MODE keeps the adopted interface's bands and positions but not its number, for the reason S80-20 gives.
- Source: DD manual, PDF pages 73 and 74 (numbers and ranges); PDF pages 8 to 10, items 29 to 49; PDF pages 34 to 42 (each control). CS-80 owner's manual, PDF page 3, and pages 7 to 14 and 37 to 39 (each control). synth80's source, `patch.rs` (`Global`).
- Verification: As S80-10, for these 21 controllers.

**S80-12. What the remaining rows of the adopted table do.** Of the adopted table's 79 rows, synth80 MUST treat the six that are not tone or master controls as follows: controller 0 (BANK SELECTION, 0-1-2) by S80-36; controller 1 (MODULATION WHEEL) by S80-24; controller 5 (GLIDE TIME) by S80-11; controller 7 (GLOBAL VOLUME) by S80-25; controller 64 (SUSTAIN PEDAL) by S80-26; controller 120 (GLIDE MODE in the adopted table) as all sound off by S80-29, GLIDE MODE being moved to controller 3 by S80-20 and S80-27. Controllers 93 (COARSE PITCH, 0-64-127) and 94 (FINE PITCH, 0-64-127) MUST be taken by S80-47, as performance controllers outside the patch.
- Reason: Coarse and fine pitch are master controls of Deckard's Dream that are not among synth80's 85 patch controls; DEC-6465's answer to open question 5 (awaiting the owner's confirmation) takes them as performance controllers, like controller 7, rather than leaving them out or adding them to the patch (S80-47).
- Source: DD manual, PDF pages 71 to 74; PDF page 8, items 27 and 28; PDF page 34. DEC-6465, answer 40.
- Verification: The test of S80-1.

### 5.4 What value 0 and value 127 mean

**S80-13. Value 0 is the end of least effect.** For every lever of S80-10 and S80-11, value 0 MUST be the end of the lever this table names in its "0" column and value 127 the other end, and the synth80 field MUST equal the value: synth80 holds each lever as a position from 0 to 127 (`law::LEVER_MAX`), and the controller sets that position directly, with no scaling. A lever with a centre detent ("0-64-127") is at its centre at value 64 (`law::LEVER_CENTRE`).

| Lever | Value 0 | Value 127 | DD manual's direction, and the printed scale at the two ends | Ends in units, where a source gives them |
|---|---|---|---|---|
| PWM SPEED | slow | fast | Top=Max/Bottom=Min (PDF page 26); SLOW, FAST | DD: the "PWM MIN" and "PWM MAX" per-patch settings, defaults 0.7 Hz and 70.0 Hz (PDF pages 55 and 56). CS-80: not stated in the owner's manual. synth80: `law::speed` with `FAST_OCTAVES_A_VOLT` (adjustment procedure, page 17). |
| PWM | none | most | Top=Max/Bottom=Min (PDF page 26); 0 to 10 | |
| PW | 50% | 90% | Top=Max/Bottom=Min (PDF page 27); 50%, 90% | DD and CS-80 alike: "from 50% (square wave) to 90%" (DD PDF page 5, item 3; CS-80 page 15, item [22]). |
| NOISE | none | most | Top=Max/Bottom=Min (PDF page 27); 0 to 10 | |
| HPF | LOW (filter open) | HIGH | "Top=Max/Low=Min" (PDF page 28); LOW, HIGH | |
| RESh | no resonance | most resonance | The heading says "Top=Min/Bottom=Max", but its text says "At the bottom of the slider, no resonance is present. At the top of the slider, the maximum amount of resonance is present" (PDF page 28); the CS-80 agrees with the text ("Move both these sliders up to HIGH for maximum resonance", page 16). The text is taken. | |
| LPF | LOW (filter closed) | HIGH (filter open) | "Top=Max/Low=Min" (PDF page 28); LOW, HIGH | |
| RESl | no resonance | most resonance | Top=Max/Bottom=Min (PDF page 28) | |
| IL | 0 | −5 | Top=Max/Bottom=Min (PDF page 29); 0 to −5 | |
| AL | 0 | +5 | Top=Max/Bottom=Min (PDF page 29); 0 to +5 | |
| Filter A, D, R | SHORT | LONG | Top=Max/Bottom=Min (PDF pages 29 and 30) | DD: the ATTACK TIME per-patch setting, default 1.0 s, 1.0 to 100.0 s, and DEC/REL TIME, default 15.0 s, 15.0 to 150.0 s, set the longest time (PDF pages 56 and 57). CS-80: attack 1 ms to 1 s; decay 10 ms to 10 s; release 10 ms to 10 s (page 49). synth80: `law::time` (adjustment procedure, pages 7 and 13). |
| VCF LEVEL | 0 | 10 | Top=Max/Bottom=Min (PDF page 30) | |
| SINE | 0 | 10 | Top=Max/Bottom=Min (PDF page 31) | |
| Amplifier A, D, R | SHORT | LONG | Top=Max/Bottom=Min (PDF pages 31 and 32) | As the filter's. |
| Amplifier S | 0 | 10 | Top=Max/Bottom=Min (PDF page 31) | |
| LEVEL | 0 | 10 | Top=Max/Bottom=Min (PDF page 32) | |
| INITIAL BRILLIANCE, INITIAL LEVEL, AFTER BRILLIANCE, AFTER LEVEL | 0 (no effect) | 10 | Top=Max/Bottom=Min (PDF pages 32 and 33) | |
| DETUNE CH II | flat | sharp | Top=Low/Bottom=High (PDF page 34), centre detent | DD: "approximately 1 semitone in either direction" (PDF page 35). CS-80: "approximately ±1 semi-tone" (page 49). synth80: ±100 cents (`voice.rs`, `DETUNE_RANGE`). |
| MIX I-II | channel I alone | channel II alone | No direction heading; "At the top, only layer I is audible, while at the bottom, only layer II is audible" (PDF page 37), centre detent | |
| BRILLIANCE | duller | brighter | No direction heading; "Moving the slider up from the center will remove harmonics ... moving the slider down from the center detent will increase harmonics" (PDF page 37), centre detent | |
| RESONANCE | no added resonance | most | Top=Min/Bottom=Max (PDF page 37) | |
| KEYBOARD CONTROL BRILLIANCE LOW and HIGH | the lower (or upper) keys duller | the lower (or upper) keys brighter | No direction heading; "Moving the slider up will decrease emphasis ... Moving the slider toward the bottom will increase emphasis" (PDF page 40), centre detent | |
| KEYBOARD CONTROL LEVEL LOW and HIGH | the lower (or upper) keys quieter | louder | No direction heading; up decreases volume, down increases it (PDF pages 40 and 41), centre detent | |
| SUB OSCILLATOR SPEED | slow | fast | Top=Min/Bottom=Max (PDF page 36) | DD: LFO MIN, default 0.7 Hz (0.1 to 5.0 Hz), and LFO MAX, default 25.0 Hz (10.0 to 45.0 Hz) (PDF pages 54 and 55). CS-80: "0.7Hz to 60Hz" (page 49). synth80: `law::speed_under` with `SUB_OCTAVES_A_VOLT` (adjustment procedure, page 17). |
| SUB OSCILLATOR VCO, VCF, VCA | none | most | Top=Min/Bottom=Max (PDF pages 36 and 37) | |
| TOUCH RESPONSE PITCHBEND, SPEED, VCO, VCF | none | most | Top=Min/Bottom=Max (PDF pages 38 and 39) | |
| PORTAMENTO/GLISSANDO speed | SHORT | LONG | Top=Max/Bottom=Min (PDF page 42) | DD: "With the slider at the top, it takes approximately 10 seconds to transition from the lowest note to the highest note" (PDF page 42). CS-80: "about 10 seconds for the pitch to change from the lowest to the highest note on the keyboard (about 2 seconds per octave)" (page 12, item [14] A). |

- Reason: The DD manual defines "Max" as "the end of the slider's travel that has the biggest effect on Deckard's Dream's sound" (PDF page 23), so value 0 at Min and 127 at Max reads every "Top=Max" and "Top=Min" heading alike; for the pitch levers the Low end is taken as least. It is how synth80's patch already counts every lever ("A lever is 0 to 127 from the end the panel marks low, slow, short or 0 to the other", `patch.rs`), so a patch written today keeps its meaning. The source does not state which end value 0 is (open question 1).
- Source: DD manual, PDF pages 23 and 26 to 42. CS-80 owner's manual, page 6, note C ("some controls are arranged so that maximum effect occurs nearest the player (lever down), and others give maximum effect away from the player (lever up)"). synth80's source, `patch.rs`, `law.rs`. The value-to-unit laws between the ends are synth80's own readings of the service manual and adjustment procedure, as each constant's `Source:` line says, and are not specified here.
- Verification: A test sets each lever to 0 and to 127 by its controller and checks the direction of the effect the table names (for example, SUB OSCILLATOR SPEED at 127 gives a faster measured rate than at 0; MIX at 0 gives channel I alone).

### 5.5 The bands of switches and selectors

**S80-14. Switches.** For each switch of S80-10 (the square and sawtooth switches of each channel), synth80 MUST take values 0 to 64 as off and values 65 to 127 as on. The canonical values are 0 (off) and 127 (on).
- Reason: The adopted table gives the bands "0-64/65-127" (PDF pages 71 and 72). That the lower band is off is not stated in the source; it follows S80-13 (off is the end of least effect). Note that the band is not MIDI 1.0's usual one for a switch (off below 64): the adopted table's is taken.
- Source: DD manual, PDF pages 71 and 72; PDF page 27 ("SQUARE waveform switch (Top=Off/Bottom=On)").
- Verification: A test checks all 128 values of each of the four switches, and values 64 and 65 by name.

**S80-15. Six-position selectors.** For FEET I, FEET II and SUB OSCILLATOR FUNCTION, synth80 MUST take the position from the value by these bands: 0 to 21 position 0; 22 to 42 position 1; 43 to 63 position 2; 64 to 84 position 3; 85 to 105 position 4; 106 to 127 position 5. The canonical value of a position is the lowest of its band: 0, 22, 43, 64, 85, 106. The positions are:

| Position | FEET I and FEET II | SUB OSCILLATOR FUNCTION |
|---|---|---|
| 0 | 16′ | sine |
| 1 | 8′ | sawtooth ("rapid beginning and slow decay") |
| 2 | 5 1/3′ | inverted sawtooth ("slow beginning and rapid decay") |
| 3 | 4′ | square |
| 4 | 2 2/3′ | NOISE (white noise) |
| 5 | 2′ | EXT (with nothing connected, "an 'off' mode for the whole sub oscillator section") |

- Reason: The bands are the adopted table's. Which band is which position is not stated in the source; the positions are taken in the order the manuals give them, from the top of the panel: "At the top (16'), the pitch will be lowest. At the bottom (2'), the pitch will be highest" (DD PDF page 35); "Available options, from top to bottom, include sine, saw, reverse saw, square, random (sample & hold), and external" (DD PDF page 36). This is the order of synth80's `Feet` and `Function` today.
- Source: DD manual, PDF page 73 (bands), pages 34 to 36. CS-80 owner's manual, page 8, item [5]; page 9, item [11] A; page 37. synth80's source, `patch.rs` (`Feet`, `Function`). Deckard's Dream's fifth waveform is "random ('sample&hold')" (PDF page 8, item 32), which the CS-80 does not have; synth80's fifth position is the CS-80's white NOISE (page 9). The difference is listed in section 14.2.
- Verification: A test checks all 128 values of each selector against the bands and each band's two edges by name; a test with FEET I at each position checks the pitch of middle C against the six intervals (an octave down, unison, a fifth up, an octave up, an octave and a fifth up, two octaves up).

**S80-16. Lever values are all valid.** Every value 0 to 127 of every controller of S80-10, S80-11 and S80-20 MUST select a position of its control; no value is an error.
- Reason: The ranges of the adopted table cover 0 to 127 for every lever, switch and selector; GLIDE MODE's bands stop at 126, and S80-27 gives 127 to its last band.
- Source: DD manual, PDF pages 71 to 74.
- Verification: The tests of S80-10, S80-14, S80-15 and S80-27.

### 5.6 Errors in the adopted table, and how they are read

**S80-17. Reading the table's errors.** An implementation MUST read the adopted table with these corrections, each of which this document's tables already make:
1. Controller 107, "SUB OSCILLATOR TO VAMOUNT", is the sub oscillator's VCF depth: the same manual names controller 107 "LFO TO VCF" (PDF page 47) and "LFO DEPTH - VCF" (PDF page 49).
2. Controller 8, "MIX 43102", is MIX I-II: the panel's item 37 "Mix I / II" (PDF page 9) and the calibration list's "MIX I/II" (PDF page 64), and the only master control the table otherwise lacks.
3. Controller 51, "FILTER EG AFTER LEVEL A", and controller 78, "FILTER EG AFTER LEVEL B", are the filter envelope's attack level, AL: the panel's item 12 is "Attack level" (PDF page 6) and its heading on PDF page 29 is "AL". It is not an after-touch control: those are controllers 65, 66, 91 and 92.
4. Controller 119 is channel II's RESh, out of the table's otherwise rising sequence, which would have put it at 74; 74 is the controller that MPE controllers send for vertical finger movement, which the manual redirects separately (PDF page 47).
5. RESh's heading "Top=Min/Bottom=Max" contradicts its own text; the text is taken (S80-13).
6. The touch response's SPEED follows pressure, not velocity (S80-5).
7. Controller 46 and 73 "HIGH PASS FILTER BRILLIANCE" and 48 and 75 "LOW PASS FILTER BRILLIANCE" are the HPF and LPF cutoff levers ("BRILLIANCE: This term is synonymous with voltage-controlled filter cutoff frequency", PDF page 22).
- Reason: Each is an error of the filed manual; an implementation must not guess at them differently.
- Source: As each item names. The manual also carries a heading "Deckard's Dream 1.3.1 release notes:" with nothing under it (PDF page 71), and two paragraphs that name "Kijimi" in place of Deckard's Dream (PDF pages 12 and 68); neither bears on the table.
- Verification: The tests of S80-10 and S80-11 assert each corrected meaning by name.

---

## 6. The controllers NeoTeletext defines for the CS-80 controls the adopted table lacks

### 6.1 What lacks a controller

Comparing every field of synth80's patch with the adopted table, twelve fields have no row, because Deckard's Dream has no such control (its panel, PDF pages 5 to 10, has no ring modulator, no SUSTAIN section and no tremolo/chorus):

| Byte | synth80 field | The CS-80's control |
|---|---|---|
| 71 | `RingAttack` | RING MODULATOR ATTACK TIME, [16] D |
| 72 | `RingDecay` | RING MODULATOR DECAY TIME, [16] D |
| 73 | `RingDepth` | RING MODULATOR DEPTH, [16] C |
| 74 | `RingSpeed` | RING MODULATOR SPEED, [16] B |
| 75 | `RingModulation` | RING MODULATOR MODULATION, [16] A |
| 76 | `SustainMode` | SUSTAIN I-II, [13] B |
| 77 | `Sustain` | SUSTAIN SLIDER, [13] A |
| 80 | `Effect` | TREMOLO/CHORUS ON/OFF, [15] A |
| 81 | `Chorus` | CHORUS switch, [15] B |
| 82 | `Tremolo` | TREMOLO switch, [15] C |
| 83 | `EffectSpeed` | TREMOLO/CHORUS SPEED knob, [15] D |
| 84 | `EffectDepth` | TREMOLO/CHORUS DEPTH knob, [15] E |

Deckard's Dream's PLAYBACK setting (SUSTAIN I or SUSTAIN II, per patch) is the same choice as the CS-80's SUSTAIN I-II switch, but it is a menu setting with no controller (PDF pages 53 and 54). The CS-80's ribbon has its place taken by pitch bend (S80-7), a bend in semitones, and needs no controller. The thirteenth field, GLIDE MODE, has a row, but its number cannot be used (S80-20).

### 6.2 The rule used to choose their numbers

A number for each is the one thing in this document that no source supplies, and DEC-6453 item 3 permits NeoTeletext to define it because no existing interface covers these controls. The numbers were chosen by these rules, in order:
1. No controller the adopted table uses (0, 1, 5, 7, 8, 40 to 63, 64, 65 to 73, 75 to 95, 102 to 120) is reused for another meaning.
2. No controller MIDI 1.0 gives a meaning is used: 0 to 2, 4 to 8, 10 to 13, 16 to 19, 32 to 63 (the fine parts of 0 to 31), 64 to 84, 91 to 101, and 120 to 127 (MIDI 1.0, to be checked). Controller 74 is also avoided, because Deckard's Dream reserves it for MPE controllers (PDF page 47).
3. What remains, and is free in both, is exactly: 3, 9, 14, 15, and 20 to 31. These are the controllers MIDI 1.0 leaves undefined among 0 to 31 (MIDI 1.0, to be checked).
4. The twelve controls of section 6.1 take the one run of twelve consecutive free numbers, 20 to 31, in the order of synth80's patch, so that a reader finds them together and a sender can write them as a block.
5. GLIDE MODE, displaced from 120, takes the lowest remaining free number, 3. Numbers 9, 14 and 15 are left free.

These rules are the architecture's rules for control maps NeoTeletext defines (`midi-architecture.md`, MIDI-78): rule 1 here is its rule 1; rule 2 here holds its rules 2 and 6 (controllers 120 to 127, bank select, data entry 6 and 38, and 96 to 101 are never taken; 6, 38, 96, 97, 100 and 101 keep their registered-parameter meanings, S80-7); its rule 3 (a parameter whose meaning MIDI 1.0 names takes that controller) is overridden for GLIDE MODE by its rule 1, since controller 65, portamento on and off, is the adopted table's AFTER BRILLIANCE A; its rule 4 does not apply, since the adopted interface uses no parameter numbers; and rules 3 to 5 here are its rule 5. None of the numbers 3 and 20 to 31 is used by the adopted table, which uses 0, 1, 5, 7, 8, 40 to 73, 75 to 95 and 102 to 120.

### 6.3 Requirements

**S80-18. The twelve controllers of NeoTeletext's own.** synth80 MUST move each of the twelve controls of section 6.1 by the control change of the controller the table below gives. These numbers are NeoTeletext's own (section 15, item 1) and MUST be marked as such wherever they are documented.

| Byte | Control | Controller | Kind | Value 0 | Value 127, or the bands |
|---|---|---|---|---|---|
| 71 | RING MODULATOR ATTACK TIME | 20 | lever | shortest | longest |
| 72 | RING MODULATOR DECAY TIME | 21 | lever | shortest | longest |
| 73 | RING MODULATOR DEPTH | 22 | lever | no change of speed by the envelope | most |
| 74 | RING MODULATOR SPEED | 23 | lever | slowest | fastest |
| 75 | RING MODULATOR MODULATION | 24 | lever | no effect | most |
| 76 | SUSTAIN I-II | 25 | switch | 0 to 64: SUSTAIN I | 65 to 127: SUSTAIN II |
| 77 | SUSTAIN | 26 | lever | SHORT (no sustain) | LONG (about 10 seconds) |
| 80 | TREMOLO/CHORUS ON/OFF | 27 | switch | 0 to 64: off | 65 to 127: on |
| 81 | CHORUS | 28 | switch | 0 to 64: up | 65 to 127: down |
| 82 | TREMOLO | 29 | switch | 0 to 64: up | 65 to 127: down |
| 83 | TREMOLO/CHORUS SPEED | 30 | lever | slowest | fastest ("Maximum speed is at full clockwise rotation") |
| 84 | TREMOLO/CHORUS DEPTH | 31 | lever | least | most ("Maximum effect is at full clockwise rotation") |

The canonical values of the switches are 0 and 127.
- Reason: synth80 has these controls because the instrument modelled has them, and a patch must be able to carry them (decision A4: a patch is the list of control-change values). The switches use the adopted table's own band for a switch (S80-14), so that every switch of synth80 is coded alike. Value 0 is the end of least effect, as S80-13. The levers set synth80's fields directly, as S80-13.
- Source: CS-80 owner's manual, page 11, item [13] A and B; page 13, items [15] A to E and [16]; page 14, item [16] A to D; page 37, item [16]; page 39, items [13] and [15]; page 49 ("Ring Modulator"). The numbers: section 6.2, NeoTeletext's own. The alternatives and the owner's choice: open question 2.
- Verification: As S80-10, for these twelve controllers; and a test checks that with SUSTAIN I-II at 127 a new key ends the sustain of the notes released before it (S80-32).

**S80-19. Interactions of the tremolo/chorus switches.** With TREMOLO/CHORUS ON/OFF on, synth80 MUST give the tremolo when the TREMOLO switch is down (whether or not CHORUS is down), the chorus when CHORUS alone is down, and no effect when neither is; with ON/OFF off, no effect. Switching the effect on or off MUST pass over in at most 22 milliseconds, not in one sample.
- Reason: It is the instrument's wiring as built and the CS-80 manual's description: "The ON/OFF switch activates whatever effect is preset with the two adjacent switches"; the manual's figure shows both down as "Tremolo", "Not Recommended (Level Drops)".
- Source: CS-80 owner's manual, page 13, item [15] A to C; page 39, item [15] and its figures. synth80's source, `mod.rs` (`apply_patch`: "The TREMOLO tab takes the speed voltage and the oscillators' outputs from the CHORUS tab's contacts when it is down", from the service manual, page 66; `EFFECT_SWITCH_STEP`).
- Verification: The existing effect tests (`tests/synth80_*`), driven through controllers 27 to 29.

**S80-20. GLIDE MODE moves to controller 3.** synth80 MUST take the PORTAMENTO/GLISSANDO selector (byte 78) by controller 3, with the adopted table's bands and positions (S80-27). Controller 120 MUST keep MIDI 1.0's meaning, all sound off (S80-29), and MUST NOT move the selector.
- Reason: The adopted table puts GLIDE MODE on controller 120 (PDF page 74). MIDI 1.0 makes controllers 120 to 127 channel mode messages, 120 being all sound off (MIDI 1.0, to be checked), and decision A1 makes MIDI 1.0 the one common layer: every NeoTeletext synthesizer takes controller 120 as all sound off, a receiver needs it to silence a sound at once, and synth80 does so today. The architecture requires it: "Where an adopted interface gives one of the controllers 120 to 127 another meaning, MIDI 1.0's meaning MUST win and the family document MUST move that parameter to another controller or NRPN" (MIDI-9), and "Deckard's Dream's use of controller 120 for glide mode MUST be moved by `synth80.md`" (MIDI-86). The two meanings cannot share one number: GLIDE MODE's first band (0 to 42, portamento) contains 0, the value all sound off is sent with. The move is listed as a departure in section 14.2; open question 3 records the choice.
- Source: DD manual, PDF page 74. MIDI 1.0 (to be checked). synth80's source, `mod.rs` (`CONTROL_ALL_SOUND_OFF`). `midi-architecture.md`, MIDI-9, MIDI-78 and MIDI-86. The number 3: section 6.2, rule 5.
- Verification: A test sends controller 3 with values 0, 43 and 85 and checks the selector's three positions; a test sends controller 120 with value 0 under held notes and checks the sound is taken out and the selector unchanged.

---

## 7. The messages of NeoTeletext's common layer, and the adopted performance controllers

**S80-21. Controllers that are performance, not patch.** Controllers 1 (modulation wheel), 7 (volume), 64 (sustain pedal), 93 (coarse pitch) and 94 (fine pitch) MUST NOT be part of a patch: a program change or a patch leaves them as they are, and they are not among the patch's 85 values.
- Reason: The CS-80's foot switch, volume and PITCH [18] are not part of its tones or memories, and the modulation wheel is not a control of the CS-80 at all. Deckard's Dream's saved patch holds "All front panel slider and switch positions" and "All non-global MIDI settings" (PDF page 19), which the wheel, volume and pedal are not. Its coarse and fine pitch sliders are among the panel's sliders it saves; DEC-6465's answer to open question 5 (awaiting the owner's confirmation) nevertheless takes them outside the patch, as tuning controls like the CS-80's PITCH (S80-47), a difference listed in section 14.2.
- Source: DD manual, PDF page 19. CS-80 owner's manual, page 14 and page 23, item [46]. DEC-6465, answer 40.
- Verification: A test sets controllers 1, 7, 64, 93 and 94, sends a program change, and checks they are unchanged.

**S80-22. No coarse and fine pairs.** synth80 MUST treat every controller of S80-10, S80-11, S80-18 and S80-47 as a whole value of seven bits by itself. It MUST NOT pair controllers 0 to 31 with controllers 32 to 63 as most and least significant parts, as MIDI 1.0 does for its pairs: in the adopted table controllers 40 to 63 are channel I's tone controls in their own right, not the fine parts of 8 to 31 (controller 40, for example, is PULSE WIDTH MODULATION SPEED A, not the fine part of controller 8, MIX). Controllers 32 to 37 and 39 MUST be counted as ignored; controller 38 is the fine part of data entry for registered parameter number 0 alone (S80-7).
- Reason: The adopted table gives every controller the range 0 to 127 alone and uses 40 to 63 for other controls; synth80's levers have 128 positions, which one controller carries exactly. The architecture leaves the pairing to the interface (`midi-architecture.md`, MIDI-74).
- Source: DD manual, PDF pages 71 to 74. MIDI 1.0 for the pairing it leaves aside (MIDI 1.0, to be checked). `midi-architecture.md`, MIDI-74 and MIDI-90.
- Verification: A test sends controller 8 with value 64 and then controller 40 with value 100 and checks MIX stays at its centre and channel I's PWM SPEED becomes 100; controllers 32 to 37 and 39 are counted as ignored.

**S80-23. The sixteen-channel pressure and controller state is one.** The modulation wheel, the volume, the pedal, the coarse and fine pitch (S80-47), the pitch bend and the pressure of every held key MUST be one state for the whole instrument, whatever channel set them (S80-2).
- Reason: As S80-2.
- Source: synth80's source, `mod.rs`.
- Verification: The test of S80-2.

**S80-24. The modulation wheel, controller 1.** On a control change of controller 1, synth80 MUST let the sub oscillator move the pitch of both channels by up to `value ÷ 127` of 50 cents either way, added to what the SUB OSCILLATOR VCO lever and the touch response's VCO lever already give.
- Reason: The adopted table names controller 1 "MODULATION WHEEL" (PDF page 71). What it moves is Deckard's Dream's per-patch MOD WHEEL DESTINATION setting, one of eleven controllers, with a per-patch MOD WHEEL POLARITY that "adds to the value of the CC destination" when positive (PDF pages 48 to 50); no message sets either, the default is not stated in the source, and how much the wheel adds is not stated. synth80 takes the first destination listed, "LFO DEPTH - VCO (CC 106)", with positive polarity, which is what is built: the wheel adds sub oscillator depth on the pitch. The 50 cents are NeoTeletext's own (section 15, item 6). The CS-80 has no modulation wheel.
- Source: DD manual, PDF pages 48 to 50 and 71. synth80's source, `mod.rs` (`WHEEL_CENTS`, "own choice: the instrument has no such wheel").
- Verification: A test with the sub oscillator at a sine and SUB OSCILLATOR VCO at 0 measures the depth of the pitch's swing at wheel values 0, 64 and 127 against 0, 25.2 and 50 cents.

**S80-25. Volume, controller 7.** On a control change of controller 7, synth80 MUST set a gain on its output from the value, 0 (silent) to 127 (full), by the volume law every NeoTeletext synthesizer shares (`midi-architecture.md`, MIDI-82 and MIDI-92: `(value × value) ÷ (127 × 127)` of full), and MUST move the gain to its new place by at most `1 ÷ 256` of full a sample, so over at most 256 output samples (5.3 milliseconds). Before any controller 7 arrives the value is 127.
- Reason: The adopted table names controller 7 "GLOBAL VOLUME" (PDF page 74); the panel's VOLUME knob "controls the final output volume of a patch, both of the headphone amplifier on the front panel, and the AUDIO OUTPUT jack" (PDF page 43). The CS-80's VOLUME [2] is likewise outside its tones (page 6). The architecture takes Deckard's Dream's GLOBAL VOLUME as this volume (MIDI-92). The law and slew are what is built.
- Source: DD manual, PDF pages 10, 43 and 74. CS-80 owner's manual, page 6, item [2]; page 38, item [2]. synth80's source, `mod.rs` (`CONTROL_VOLUME`, `VolumeGain`); the shared law is in `analog/volume.rs` and is stated once in `midi-architecture.md`, MIDI-82 and MIDI-92.
- Verification: A test checks the level of a held chord at values 0, 64 and 127 against the shared law, and that no two successive samples of the gain differ by more than the slew allows.

**S80-47. Coarse and fine pitch, controllers 93 and 94.** On a control change of controller 93 (COARSE PITCH) or controller 94 (FINE PITCH), synth80 MUST set the instrument's coarse pitch or fine pitch to the value, 0 to 127, and MUST move the pitch of both channels of every voice, sounding or newly struck, by the sum of the two controls' offsets in cents, linear in pitch, added to the pitch bend's offset (S80-7) and acting exactly as the pitch bend acts, the filters following as they follow the keys. Value 64 MUST be each control's centre, at which it moves nothing; value 0 MUST be its low end and value 127 its high end. For a value v the offset MUST be `(v − 64) × R ÷ 64` cents for v from 0 to 64 and `(v − 64) × R ÷ 63` cents for v from 64 to 127, where R is 500 cents for coarse pitch and 100 cents for fine pitch: value 0 gives R down, value 64 nothing, and value 127 R up, every value between on a straight line in cents from its end to the centre (the law of synth80's `law::centred`, by which DETUNE CH II is read today, S80-13). The two controls MUST NOT be part of a patch (S80-21): the patch stays 85 values (S80-33), and a program change (S80-35), a patch sent inline (S80-40), controller 121 (S80-28), controller 120 (S80-29) and a lost block (S80-39) leave both as they are. Before any control change of either arrives, each MUST stand at 64. Each controller MUST be taken as one value of seven bits by itself, never as the coarse or fine part of a MIDI 1.0 pair (S80-22). A change under a sounding note MUST pass from the old offset to the new one as a lever passes under S80-37, a step of one position at each tick of a sixth of a millisecond, so that no step in pitch is heard as a click (`midi-architecture.md`, MIDI-83). Like the volume, each is one state for the whole instrument, whatever channel set it (S80-23).
- Reason: The adopted table names controller 93 "COARSE PITCH" and controller 94 "FINE PITCH", each with the range "0-64-127" (DD manual, PDF page 73), the form section 5.1 reads as a lever with a centre detent at 64. The panel: "Coarse pitch: Controls overall coarse pitch (both layers I and II)" and "Fine pitch: Controls overall fine pitch (both layers I and II)" (PDF page 8, items 27 and 28). The pitch parameters: "Coarse pitch has a dramatic effect on the pitch of the oscillators in layers I and II. A center detent identifies center pitch. Pitch can be adjusted approximately 5 semitones in either direction, with lower pitch toward the top, and higher pitch toward the bottom", and fine pitch, with the same centre detent and directions, "can be adjusted approximately 1 semitone in either direction" (PDF page 34, headed "COARSE PITCH (Top=Low/Bottom=High)" and "FINE PITCH (Top=Low/Bottom=High)"). DEC-6465's answer to open question 5 (awaiting the owner's confirmation) takes them as performance controllers outside the patch, like controller 7: a stream written for Deckard's Dream keeps its tuning, and a tuning control does not become part of every sound. The CS-80's PITCH [18], a coarse ring and a fine knob, is likewise a tuning control outside its tones and memories (CS-80 owner's manual, pages 14 and 37). Deckard's Dream itself saves "All front panel slider and switch positions" in a patch (PDF page 19), which include these two sliders; taking them outside the patch is a difference, listed in section 14.2. What the manual does not state, and is therefore NeoTeletext's own (section 15, item 14): which end of the slider value 0 is (the manual gives the slider's direction, top low and bottom high, not the value's; value 0 is taken as the low end, as for every pitch lever under S80-13 and open question 1); that "approximately 5 semitones" and "approximately 1 semitone" are exactly 500 and 100 cents; the law between the ends and the centre, a straight line in cents; that the two offsets add to each other and to the pitch bend's and act as the pitch bend acts; that a program change, a patch, controller 121, controller 120 and a lost block leave them; their value of 64 before any arrives; and the slide of a change under a sounding note.
- Source: DD manual, PDF page 8, items 27 and 28; PDF page 19; PDF page 34; PDF page 73 (read for this requirement from the filed manual). CS-80 owner's manual, pages 14 and 37 (PITCH [18]) and page 49. synth80's source, `law.rs` (`centred`, `LEVER_CENTRE`) and `voice.rs` (`DETUNE_RANGE`, read with `law::centred`). `midi-architecture.md`, MIDI-83, MIDI-84 and MIDI-93. DEC-6465, answer 40.
- Verification: A test holds a note and sends controller 93 with values 0, 32, 64, 96 and 127, and checks the measured pitch against −500, −250, 0, +253.97 (32 × 500 ÷ 63) and +500 cents, each within 0.1 cent; the same test for controller 94 checks −100, −50, 0, +50.79 (32 × 100 ÷ 63) and +100 cents; a test with both at 127 and a full upward pitch bend at the default range checks the pitch against +600 cents plus the bend; a test sets both to values other than 64, then sends a program change, a patch inline, controller 121, controller 120 and a lost block, and checks after each that both are unchanged; a test checks that the patch is still 85 bytes and that neither controller is among its values; the control-sweep test, driven through controllers 93 and 94 under a sounding note, holds the same bounds on the largest step of the output as for the levers.

**S80-26. The sustain pedal, controller 64, and the SUSTAIN lever.** On a control change of controller 64, synth80 MUST take values 64 to 127 as the pedal down and 0 to 63 as up (MIDI-87). While the pedal is down, a key released MUST go on sounding as if it were held; when the pedal goes up, every note so held MUST be released, as a note off of its key would release it then (MIDI-87). Independently of the pedal, a released note (a key released with the pedal up, or a note the pedal lets go) MUST die away in the SUSTAIN lever's time (byte 77) instead of its amplifier's release time, where the SUSTAIN lever's time is the longer, as the CS-80 does with its SUSTAIN FOOT SWITCH assigner off; with the SUSTAIN lever at SHORT (value 0) a released note falls at its own release time.
- Reason: The architecture sets one sustain pedal for every synthesizer (`midi-architecture.md`, MIDI-87): down at 64 to 127, holding released keys as if held, releasing them when it goes up. The adopted table names controller 64 "SUSTAIN PEDAL" and gives no range and no behaviour (PDF page 74), so it does not contradict that rule. Today synth80 takes controller 64 as the CS-80's FOOT SWITCH PEDAL with its SUSTAIN assigner on, which "turns ON the sustain when the SUSTAIN FOOT SWITCH assigner is also ON. The amount of sustain is set with the SUSTAIN SLIDER. However, releasing the pedal will immediately end any sustain, short or long" (page 11, item [13] C): it does not hold notes, and it contradicts MIDI-87, so it is replaced. The CS-80 with its assigner off "bypasses the FOOT SWITCH PEDAL and introduces that amount of sustain already set with the SUSTAIN SLIDER" ("Long sustain regardless of foot switch position", page 11, item [13] D and its figures), which keeps the SUSTAIN lever and the SUSTAIN I-II switch meaningful without the foot switch. The change is listed in section 14.2 and section 17, and open question 7 records it for the owner.
- Source: `midi-architecture.md`, MIDI-87. DD manual, PDF page 74. CS-80 owner's manual, page 11, item [13] A to D and its figures; page 39, item [13]. synth80's source, `mod.rs` ("Controller 64 is the foot switch with its SUSTAIN assigner on"), `voice.rs` (`amp_sustained`), which this requirement changes. MIDI 1.0 for the bands (MIDI 1.0, to be checked). The CS-80's foot switch can serve the portamento/glissando instead or as well, through its P/G assigner (page 12, item [14] B and C); synth80 has no assigners (section 13).
- Verification: A test sends values 0, 1, 63, 64 and 127 and checks the pedal's state after each; a test with SUSTAIN at 0 holds a key, puts the pedal down, releases the key, checks the note sounds at its full sustained level after one second, lifts the pedal and checks the note then falls at its release time; a test with a short amplifier release and SUSTAIN at 127 releases a key with the pedal up and checks the note still sounds after one second.

**S80-27. GLIDE MODE's positions.** For the PORTAMENTO/GLISSANDO selector, synth80 MUST take values 0 to 42 as PORTAMENTO, 43 to 84 as off, and 85 to 127 as GLISSANDO. The canonical values are 0, 43 and 85. With PORTAMENTO, a voice's pitch MUST glide continuously from the pitch it last had to its new key's, at the rate the PORTAMENTO/GLISSANDO speed lever (byte 79) sets; with GLISSANDO, it MUST move in semitone steps at the same rate; with off, or with the speed lever at 0, it MUST go to the new key at once. At the lever's top the glide MUST take about 10 seconds from the lowest key of the CS-80's 61 to its highest (about 2 seconds an octave). A glissando MUST stop when its key is released, unless SUSTAIN II mode is on, in which case it goes on until the note dies away.
- Reason: The adopted table gives the bands "0-42/43-84/85-126" (PDF page 74) to a "3-setting switch": "Left (P or PORTAMENTO)", "Center: Pitch transitions immediately between notes with no glide or stepping", "Right (G or GLISSANDO)" (PDF pages 41 and 42). Which band is which position is not stated; the positions are taken left to right, as the manual lists them. Value 127, outside every band of the table, is given to the last band (NeoTeletext's own). The CS-80's selector has two positions, PORTAMENTO and GLISSANDO, and gives no glide when the slider is at SHORT (page 12, item [14] A and D); the centre position adds an off that synth80 does not have today (section 17, item 5). The times are both manuals'; the glissando's end is the CS-80's.
- Source: DD manual, PDF pages 10, 41, 42 and 74. CS-80 owner's manual, page 12, item [14]; page 39, item [14]; page 49 ("Glissando/Portamento Time Range"). synth80's source, `voice.rs` (`glide_step`, `glissando`; "Portamento is per voice, each from the pitch it last had", `mod.rs`).
- Verification: A test plays two notes two octaves apart with the speed at 127 and checks the glide under PORTAMENTO takes the time the law of `voice.rs` (`GLIDE_CLOCK`) gives, about 4 seconds; that GLISSANDO moves in steps of one semitone; that off changes the pitch within one block; and a test checks all 128 values against the bands.

**S80-28. All notes off, reset all controllers and the mode messages: controllers 123, 121 and 124 to 127.** On controller 123, whatever its value, synth80 MUST release every key that is held, as a note off of each would; a note the pedal holds stays held until the pedal goes up (S80-26), and a note in its release goes on with it (MIDI-85). On controllers 124 (omni off), 125 (omni on), 126 (mono on) and 127 (poly on), whatever the value, synth80 MUST do exactly what controller 123 does and nothing else: none changes the channels synth80 hears (S80-2) or its voice assignment (S80-31) (MIDI-71, MIDI-89). On controller 121, whatever its value, synth80 MUST do what `midi-architecture.md`, MIDI-84, says for every synthesizer, following the MIDI Association's Recommended Practice RP-015 as DEC-6464 understands it (DEC-6464 is recorded as proposed, awaiting the owner's confirmation; RP-015, to be checked): set the modulation wheel to 0, the pedal up (releasing the notes it held), the registered parameter selection to none, the pitch bend to its centre, 8,192, and the channel pressure and every key's pressure to 0; and leave unchanged the volume of controller 7, the coarse and fine pitch of controllers 93 and 94 (S80-47), the bank select value of controller 0, the current patch, every patch control however it was last set, and the bend range of registered parameter number 0. Controller 121 MUST NOT release a held key. synth80 has no expression controller (11) and no portamento, sostenuto or soft pedal (65 to 67): controller 65 is the adopted table's AFTER BRILLIANCE A, a patch control, which controller 121 leaves.
- Reason: These are messages of NeoTeletext's common layer (decision A1; MIDI-9), which the adopted table does not list. All notes off and reset all controllers are built today; the architecture sets one behaviour for each in every synthesizer (MIDI-84, MIDI-85, MIDI-89). Today synth80 counts controllers 124 to 127 as ignored, which contradicts MIDI-9 and MIDI-89, and its reset does not clear a registered parameter selection, which it had none of; both are changed. They are listed in section 15 as additions to the adopted interface.
- Source: `midi-architecture.md`, MIDI-9, MIDI-71, MIDI-84, MIDI-85 and MIDI-89; DEC-6464; RP-015 (to be checked); MIDI 1.0 (to be checked); synth80's source, `mod.rs` (`control_change`).
- Verification: The tests that exist today for controllers 121 and 123 continue to pass; a test holds three keys, sends each of 123, 124, 125, 126 and 127 in turn, and checks the notes release as note offs would and the channel map and voice assignment are unchanged; a test moves the wheel, the pedal, the pressures, the bend, the volume, the coarse and fine pitch, a patch control and the bend range, sends 121, and checks each against MIDI-84's two lists, the coarse and fine pitch being unchanged.

**S80-29. All sound off, controller 120.** On controller 120, whatever its value, synth80 MUST take the sound of every voice, held, sustained and releasing alike, out over at most 256 output samples (5.3 milliseconds), within the 1,024 samples MIDI-86 allows and by a fade that passes the click measure (MIDI-83), then silence every voice and let every key go; a message that arrives meanwhile MUST be taken, in order, once the sound has gone. The pedal, every controller and the patch are left where they are.
- Reason: A message of NeoTeletext's common layer (decision A1), built today; the architecture sets it for every synthesizer (MIDI-86). It displaces the adopted table's GLIDE MODE (S80-20).
- Source: MIDI 1.0 (to be checked); `midi-architecture.md`, MIDI-9 and MIDI-86; synth80's source, `mod.rs` (`CONTROL_ALL_SOUND_OFF`, `cut`, `deferred`).
- Verification: The existing test of all sound off for synth80 continues to pass; a test holds a chord with the pedal down and a long release, sends 120, and checks the output is 0 by sample 256 and the sweep measure holds.

---

## 8. The keyboard: voices, sustain, glide and touch

**S80-30. Eight voices of two lines.** synth80 MUST sound up to eight keys at once, each key sounding one line of channel I and one of channel II, mixed by MIX I-II.
- Reason: "The CS-80 is an eight note polyphonic synthesizer. However, there are really 16 main oscillators divided into two ranks"; Deckard's Dream is likewise eight voices of two layers.
- Source: CS-80 owner's manual, page 31; page 49 ("Simultaneous Notes", "Simultaneous Voices"). DD manual, PDF pages 13 and 50. synth80's source, `mod.rs` (`VOICES`).
- Verification: A test strikes nine keys and checks that eight sound.

**S80-31. Voice assignment.** synth80 MUST give each newly struck key the next voice in turn round the eight, taking the one it reaches whether or not that voice is still sounding a released note.
- Reason: It is what is built, read from the CS-80's adjustment procedure ("depressing a key repeatedly will allow you to select a desired master board"). Deckard's Dream calls SUSTAIN I "round-robin voice assignment" (PDF page 54). Its VOICE MODE, CARDS PER VOICE and NUMBER OF VOICES settings (PDF pages 50 to 52) have no message and are left out (section 14.1).
- Source: synth80's source, `mod.rs` (`Mode::Poly(Assign::Cyclic)`, citing the adjustment procedure, page 6). DD manual, PDF page 54.
- Verification: The existing allocator tests continue to pass.

**S80-32. SUSTAIN I and SUSTAIN II.** With SUSTAIN I-II (byte 76) at SUSTAIN I, each released note MUST die away by itself. With SUSTAIN II, when a key is struck while no key is held, every note that is still sounding after its release MUST be ended at once (in a few milliseconds, not one sample), so that "the last note or chord played carries the sustain".
- Reason: The CS-80: "With SUSTAIN I, each note struck dies independently of any others, and all have the same sustain time. In SUSTAIN II mode, the last note or chord played carries the sustain ... The next chord or note played ends any previous sustain." Deckard's Dream's PLAYBACK setting says the same (PDF page 54).
- Source: CS-80 owner's manual, page 11, item [13] B; page 39, item [13]. DD manual, PDF page 54. synth80's source, `mod.rs` (`key_down`, `damp`).
- Verification: A test with a long release plays a chord, releases it, plays a single note, and checks the chord is ended under SUSTAIN II and goes on under SUSTAIN I.

**S80-33 is in section 9.**

**S80-34. The keyboard control's curve.** The KEYBOARD CONTROL levers MUST do nothing at key 66 and MUST act more the farther a key is from it, BRILLIANCE LOW and LEVEL LOW below it and BRILLIANCE HIGH and LEVEL HIGH above it, on a smooth curve with no step between the two halves.
- Reason: The CS-80: "There is no abrupt change where one lever's effect ends and the other lever's effect begins, although a transition occurs somewhere near the middle of the keyboard. In fact, the LOW and HIGH levers operate on a smooth curve". Deckard's Dream's TRACKING WIDTH and MIDDLE OCTAVE, which change the range of the curve, are global settings with no message (PDF pages 60 and 61) and are left out. Key 66 is the middle of the CS-80's 61 keys taken as MIDI keys 36 to 96, as built.
- Source: CS-80 owner's manual, page 9, item [9]; page 38, items [9] and [10]. DD manual, PDF pages 39 to 41, 60 and 61. synth80's source, `voice.rs` (`KEYBOARD_CENTRE`, `KEYBOARD_TRIM_KEYS`, `KEYBOARD_BRILLIANCE`, `KEYBOARD_LEVEL`).
- Verification: The existing keyboard control tests continue to pass, driven through controllers 115 to 118.

---

## 9. What a synth80 patch is

**S80-33. The patch: 85 values in a fixed order.** A synth80 patch MUST be exactly 85 bytes, each a control change's value from 0 to 127, in the order of the table below: channel I's 26 tone values, channel II's 26, then the 33 master values. The patch carries no status byte, no controller number, no name and no length: byte k is always the value of the controller the table gives for byte k. A sender MUST write each lever as its position (S80-13) and each switch and selector as its canonical value (S80-14, S80-15, S80-18, S80-27). A receiver MUST accept every patch whose 85 bytes are each 0 to 127, whatever their values, and MUST set the panel from it exactly as the 85 controllers' control changes would, all at one instant (S80-37); a patch with a byte above 127, or of another length, is not a patch, and the instrument then stands at the default patch (S80-45) and the fault is counted.

| Byte | Control | Controller | Default value |
|---|---|---|---|
| 0 | I: PWM SPEED | 40 | 0 |
| 1 | I: PWM | 41 | 0 |
| 2 | I: PW | 42 | 0 |
| 3 | I: square switch | 43 | 0 |
| 4 | I: sawtooth switch | 44 | 127 |
| 5 | I: NOISE | 45 | 0 |
| 6 | I: HPF | 46 | 0 |
| 7 | I: RESh | 47 | 0 |
| 8 | I: LPF | 48 | 127 |
| 9 | I: RESl | 49 | 0 |
| 10 | I: IL | 50 | 0 |
| 11 | I: AL | 51 | 0 |
| 12 | I: filter A | 52 | 0 |
| 13 | I: filter D | 53 | 0 |
| 14 | I: filter R | 54 | 0 |
| 15 | I: VCF LEVEL | 55 | 127 |
| 16 | I: SINE | 56 | 0 |
| 17 | I: amplifier A | 57 | 0 |
| 18 | I: amplifier D | 58 | 0 |
| 19 | I: amplifier S | 59 | 127 |
| 20 | I: amplifier R | 60 | 0 |
| 21 | I: LEVEL | 61 | 127 |
| 22 | I: INITIAL BRILLIANCE | 62 | 0 |
| 23 | I: INITIAL LEVEL | 63 | 0 |
| 24 | I: AFTER BRILLIANCE | 65 | 0 |
| 25 | I: AFTER LEVEL | 66 | 0 |
| 26 | II: PWM SPEED | 67 | 0 |
| 27 | II: PWM | 68 | 0 |
| 28 | II: PW | 69 | 0 |
| 29 | II: square switch | 70 | 0 |
| 30 | II: sawtooth switch | 71 | 127 |
| 31 | II: NOISE | 72 | 0 |
| 32 | II: HPF | 73 | 0 |
| 33 | II: RESh | 119 | 0 |
| 34 | II: LPF | 75 | 127 |
| 35 | II: RESl | 76 | 0 |
| 36 | II: IL | 77 | 0 |
| 37 | II: AL | 78 | 0 |
| 38 | II: filter A | 79 | 0 |
| 39 | II: filter D | 80 | 0 |
| 40 | II: filter R | 81 | 0 |
| 41 | II: VCF LEVEL | 82 | 127 |
| 42 | II: SINE | 83 | 0 |
| 43 | II: amplifier A | 84 | 0 |
| 44 | II: amplifier D | 85 | 0 |
| 45 | II: amplifier S | 86 | 127 |
| 46 | II: amplifier R | 87 | 0 |
| 47 | II: LEVEL | 88 | 127 |
| 48 | II: INITIAL BRILLIANCE | 89 | 0 |
| 49 | II: INITIAL LEVEL | 90 | 0 |
| 50 | II: AFTER BRILLIANCE | 91 | 0 |
| 51 | II: AFTER LEVEL | 92 | 0 |
| 52 | FEET I | 102 | 22 (8′) |
| 53 | FEET II | 103 | 22 (8′) |
| 54 | DETUNE CH II | 95 | 64 |
| 55 | MIX I-II | 8 | 0 (channel I alone) |
| 56 | BRILLIANCE | 109 | 64 |
| 57 | RESONANCE | 110 | 0 |
| 58 | KEYBOARD CONTROL BRILLIANCE LOW | 115 | 64 |
| 59 | KEYBOARD CONTROL BRILLIANCE HIGH | 116 | 64 |
| 60 | KEYBOARD CONTROL LEVEL LOW | 117 | 64 |
| 61 | KEYBOARD CONTROL LEVEL HIGH | 118 | 64 |
| 62 | SUB OSCILLATOR FUNCTION | 104 | 0 (sine) |
| 63 | SUB OSCILLATOR SPEED | 105 | 0 |
| 64 | SUB OSCILLATOR VCO | 106 | 0 |
| 65 | SUB OSCILLATOR VCF | 107 | 0 |
| 66 | SUB OSCILLATOR VCA | 108 | 0 |
| 67 | TOUCH RESPONSE PITCHBEND | 111 | 0 |
| 68 | TOUCH RESPONSE SPEED | 112 | 0 |
| 69 | TOUCH RESPONSE VCO | 113 | 0 |
| 70 | TOUCH RESPONSE VCF | 114 | 0 |
| 71 | RING MODULATOR ATTACK TIME | 20 (NeoTeletext's own) | 0 |
| 72 | RING MODULATOR DECAY TIME | 21 (NeoTeletext's own) | 0 |
| 73 | RING MODULATOR DEPTH | 22 (NeoTeletext's own) | 0 |
| 74 | RING MODULATOR SPEED | 23 (NeoTeletext's own) | 0 |
| 75 | RING MODULATOR MODULATION | 24 (NeoTeletext's own) | 0 |
| 76 | SUSTAIN I-II | 25 (NeoTeletext's own) | 0 (SUSTAIN I) |
| 77 | SUSTAIN | 26 (NeoTeletext's own) | 0 |
| 78 | PORTAMENTO/GLISSANDO selector | 3 (NeoTeletext's own; the adopted table's 120) | 43 (off) |
| 79 | PORTAMENTO/GLISSANDO speed | 5 | 0 |
| 80 | TREMOLO/CHORUS ON/OFF | 27 (NeoTeletext's own) | 0 |
| 81 | CHORUS | 28 (NeoTeletext's own) | 0 |
| 82 | TREMOLO | 29 (NeoTeletext's own) | 0 |
| 83 | TREMOLO/CHORUS SPEED | 30 (NeoTeletext's own) | 0 |
| 84 | TREMOLO/CHORUS DEPTH | 31 (NeoTeletext's own) | 0 |

- Reason: Decision A4: synth80 has no patch format anywhere (neither the CS-80 nor Deckard's Dream publishes one; Deckard's Dream's bank files' format is not stated, PDF page 21), so a patch is the list of its interface's control-change values. The order is today's, which is the CS-80's memory panel for the tones (page 36) and the adopted table's own order for each layer, so that today's patches convert byte by byte and the two forms can be compared field by field. Values alone are carried because the order is fixed. Every value is a position of its control, so the receiver has no range to check beyond the top bit.
- Source: Decision A4 and DEC-6453 item 3. The order and form: NeoTeletext's own (section 15, item 3). The default values: S80-45.
- Verification: A test decodes the default patch and compares each field with S80-45; a test checks, for every byte position and every value 0 to 127, that the patch is accepted and that the field is what the control change of that controller and value gives; a test checks that patches of 84 and 86 bytes, and a patch with any one byte of 128 or more, are refused and the default patch plays; a test checks that a patch applied at an instant equals its 85 values sent as 85 control changes at that instant.

**S80-45. The default patch.** An instrument that has been given no patch, and an instrument whose patch is missing or refused, MUST stand at the patch whose values are the last column of S80-33's table: on both channels a sawtooth through the open low-pass filter, VCF LEVEL, sustain and LEVEL at their tops and everything else of the tone at its foot; both channels at 8′; DETUNE, BRILLIANCE and the four KEYBOARD CONTROL levers at their centres; MIX at channel I alone; RESONANCE at its least; the sub oscillator a sine at its foot; every touch response, ring modulator, sustain and effect control at its foot or off; the glide off.
- Reason: An instrument must sound something definite before a patch arrives. This is the default built today (`Patch::DEFAULT`), drawn from the owner's manual's diagram of the nominal settings, with the glide selector at the new off position (today's default is PORTAMENTO with the speed at 0, which also gives no glide).
- Source: synth80's source, `patch.rs` (`Tone::DEFAULT`, `Patch::DEFAULT`, citing the owner's manual, pages 8, 31 and 38). Deckard's Dream "cannot initialize patches to a default state" (PDF page 22), so it offers no default to adopt.
- Verification: A test checks a new instrument's panel equals the 85 values, decoded, field by field.

**S80-35. Program change.** On a program change, synth80 MUST take its data byte, 0 to 127, as the number of a patch in the sound's current bank (S80-36) and MUST set all 85 controls to that patch, as if its 85 values had arrived as control changes at that instant (S80-37). The modulation wheel, pitch bend, pedal, volume, coarse and fine pitch (S80-47), pressures and the keys held are left as they are. If the bank holds no patch of that number, synth80 MUST set the panel to the default patch and count the program change as ignored. Until a first program change arrives the panel is at patch 0 of the bank, or at the default patch if the bank lacks patch 0 or it was refused (MIDI-61; every sound names at least one bank, MIDI-57).
A program change that sets the patch the panel already holds MUST change nothing audible: no envelope, oscillator phase, sub oscillator or filter state restarts, as S80-37 makes true for every control set to the value it holds (MIDI-97).
- Reason: Deckard's Dream "will respond to Program Change messages, allowing for selection of the next, previous, or specific patch numbers from the current bank", 128 patches a bank. Its patch is the whole panel: "All front panel slider and switch positions". That program number 0 is the bank's first patch is not stated in the source (the panel numbers patches from 1, "patch preset 1", PDF page 18); it is MIDI's ordinary numbering. The architecture's rules for choosing a patch are MIDI-59, MIDI-61 and MIDI-63.
- Source: DD manual, PDF pages 17 to 19. synth80's source (patch 0 before a first program change). `midi-architecture.md`, MIDI-59, MIDI-61, MIDI-63 and MIDI-97.
- Verification: A test builds a bank of 128 different patches, sends program changes 0, 1, 64 and 127, and checks the panel after each equals the patch of that number; a program change beyond a bank of 4 patches gives the default patch and is counted; held notes, the wheel, pitch bend, pedal and pressures are unchanged by a program change.

**S80-36. Bank select, controller 0, and the mapping of a program change.** synth80 MUST keep the value of the last control change of controller 0 (0 before any arrives, MIDI-64), and a bank select alone MUST NOT change the patch. At each program change, synth80 MUST choose the patch by this mapping (MIDI-59): a controller 0 value of 0, 1 or 2 chooses bank index 0, 1 or 2 of the sound's banks (the first, second or third bank the sound names, MIDI-57), and the program number, 0 to 127, chooses the patch of that number in that bank. A controller 0 value of 3 to 127, a bank index past the sound's banks, or a program number the bank does not hold, MUST set the default patch (S80-45) and count the program change as ignored (MIDI-59). Controller 32 MUST be counted as ignored. A synth80 sound may name 1 to 10 banks (MIDI-57), but only bank indices 0, 1 and 2 can be reached, and a bank named after the third is never played.
- Reason: "Bank change uses MIDI CC message 0, with the values 0 = User Bank 1, 1 = User Bank 2, and 2 = Factory Bank" (PDF page 18); the adopted table gives controller 0 the range "0-1-2" (PDF page 71). Whether the bank changes at once or at the next program change is not stated in the source; the next program change is MIDI 1.0's rule (MIDI 1.0, to be checked) and the architecture's (MIDI-64). Deckard's Dream's factory bank is its own 128 sounds, which are not filed and are not the CS-80's; in NeoTeletext the three banks are whatever the sound names. The architecture lets a sound name up to 10 banks (MIDI-57, its open question 3).
- Source: DD manual, PDF pages 17, 18 and 71. MIDI 1.0 (to be checked). `midi-architecture.md`, MIDI-57, MIDI-59 and MIDI-64.
- Verification: With a sound naming two banks, a test sends controller 0 value 1 alone and checks the panel is unchanged, then a program change 5 and checks patch 5 of the second bank; sends value 2 and a program change and checks the default patch is set and the count of ignored messages rises; sends value 3 and a program change and checks the same.

**S80-37. A control change under a sounding note.** A control change of a lever MUST take effect on sounding notes as moving the lever does on the instrument: the lever MUST pass from its old position to its new one a step of one position at each tick of a sixth of a millisecond (its whole travel in about 21 milliseconds), not in one sample. A switch or selector takes its new position at once (the tremolo/chorus switches as S80-19 says). With no note sounding, every control is at its new place at once. A patch and a program change apply in the same way to every control at once.
- Reason: A lever under a hand passes through every place between two; a step in a level or a cutoff is heard as a click. It is what is built for a patch, and a control change is the same movement.
- Source: synth80's source, `mod.rs` (`set_patch`, `slide`, `levers`; own choice of the rate).
- Verification: The existing control-sweep test of synth80, driven through control changes, holds the same bounds on the largest step of the output.

**S80-38. Order and time.** Control changes MUST be applied in the order and at the times the block gives them (`midi-architecture.md`, MIDI-5: the tick of 0.1 millisecond; MIDI-35: the order of events at one tick). Two instruments given the same events at the same times MUST give the same samples, however the rendering is divided into calls.
- Reason: A stored sound must play identically for every viewer and at every loop.
- Source: Decisions A2 and A3; `midi-architecture.md`, MIDI-5 and MIDI-35.
- Verification: A test renders one score in calls of 1, 7, 960 and 4,800 samples and checks the samples identical.

**S80-39. After a lost block.** When the receiver tells synth80 that input was lost (`midi-architecture.md`, MIDI-102, says when), synth80 MUST release every key, lift the pedal (releasing the notes it held) and set the registered parameter selection to none (MIDI-76), and MUST leave every patch control, the wheel, the pitch bend, the bend range, the volume and the coarse and fine pitch (S80-47) where they stand.
- Reason: A lost block may have held a note off or a pedal release; it may equally have held control changes, which cannot be known, so the panel is left and the server's next restatement restores it (MIDI-96, S80-46). The architecture requires every family that plays notes to lift the pedal and clear the parameter selection (MIDI-102); today synth80 leaves the pedal down, which is changed.
- Source: DEC-6410 item 12; `midi-architecture.md`, MIDI-76 and MIDI-102; synth80's source, `mod.rs` (`release_all`).
- Verification: The existing test `a_live_sound_of_each_synthesizer_plays_and_a_lost_block_releases_its_notes` passes for synth80, extended to check the pedal is up after the loss and that a data entry after the loss changes nothing.

**S80-40. The same patch as control changes.** The sequence of 85 control changes a patch stands for MUST be, in the patch's byte order, `0xBn, controller, value` for each byte, with the controller S80-33's table gives for that byte. A program MAY send a patch inline, in its music, and the server MUST write it as that sequence at one tick of one block (`midi-architecture.md`, MIDI-37 and MIDI-60), to set the whole panel without a bank; after the last of them the panel equals the patch, and no bank changes.
- Reason: The patch and the live messages are one definition, so a panel can be set by either and the server can turn one into the other with the table alone (MIDI-79).
- Source: S80-10, S80-11, S80-18, S80-20, S80-33; `midi-architecture.md`, MIDI-60 and MIDI-79.
- Verification: The last test of S80-33.

**S80-41. What synth80 needs of the bank, the block and the server.** The architecture document specifies the bank and the block, and the Rust server's document the typed interface; synth80's needs are these. (a) A bank image is of the fixed-patches form (`midi-architecture.md`, MIDI-56 item 2): 1 to 128 patches of 85 bytes each back to back, patch k at byte `k × 85`, numbered from 0 in the bank's order: at most 10,880 bytes, within the bank codec's 16,384 (MIDI-55). (b) A sound may need up to three banks (S80-36). (c) No synth80 message is longer than three bytes, since synth80 takes no system exclusive (S80-9); a whole panel as control changes (S80-40) is 85 events of a one-byte delta time and three bytes, 340 bytes, within a block's 1,005 bytes and 256 events (MIDI-30, MIDI-31). (d) The server, not a program or a kit, restates synth80's state in a live sound and at the start of a stored sound, as S80-46 states (MIDI-93 to MIDI-99). (e) The server MUST accept a patch given as named fields (one name for each of the 85 controls, the names being the server document's) and as the 85 values (MIDI-14), MUST produce identical patch bytes from either, and MUST write the canonical values (S80-33) when it builds one from named fields; it MUST check every patch and bank with the receiver's own check and refuse one that would fail it (MIDI-21, MIDI-63). The TypeScript and Python kits hold none of this logic (MIDI-22). (f) synth80's sounds are of the codec the architecture gives synth80, code 18, and its banks of the bank codec, code 19, if the architecture's open question 1 is answered as recommended; otherwise of the codes synth80 and the analogue banks have today (`midi-architecture.md`, MIDI-107 to MIDI-109 and its open question 1). DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation), so synth80's sounds are of code 18 and its banks of code 19. synth80 has one variant and its OBJECT carries no variant tag (MIDI-48).
- Reason: The adopted interface has 128 patches a bank and three banks; the sizes are what the architecture document needs to size records. DEC-6462: the server builds a patch from named, typed fields, builds the blocks and restates; the kits are thin; synth80 has no system exclusive form, so its two forms are the named fields and the 85 values.
- Source: DD manual, PDF pages 17 to 19. Decision A4. DEC-6462 items 1 and 3. `midi-architecture.md`, MIDI-14, MIDI-21, MIDI-22, MIDI-30, MIDI-31, MIDI-48, MIDI-55, MIDI-56, MIDI-63 and MIDI-107 to MIDI-109.
- Verification: A test stores a bank of 128 patches, plays a program change to each, and checks the panel; the server's tests cover the named fields and check a patch from named fields and from its 85 values give identical bytes.

**S80-46. synth80's restatement.** synth80's restatement (`midi-architecture.md`, MIDI-93) MUST be, on channel 1 (synth80 hears every channel alike, S80-2), at one tick of one block (MIDI-37, MIDI-98), in this order (MIDI-95): (1) where the patch was last set by a program change, controller 0 with its last value and then that program change; where it was last set inline (S80-40), the 85 control changes of that patch in the patch's byte order; (2) then the latest value of every controller of S80-10, S80-11, S80-18 and S80-20 moved by a control change since that patch was set, in ascending order of controller number; (3) then, where the bend range differs from its default of 3 semitones, the whole registered parameter sequence that sets it (controllers 101 and 100 at 0, then 6 and 38); (4) then, each where it is not at its value after MIDI-84's reset, the pitch bend, the channel pressure, controller 7, controller 1 and controller 64; (5) then, each where it is not at 64, its value before any arrives, controller 93 and then controller 94 (S80-47). Held notes and the pressure of single keys MUST NOT be restated. The server MUST write it at least once in every 50 blocks of a live sound and at tick 0 of block 0 of every stored sound (MIDI-96, MIDI-99), and a synth80 that already holds the state it carries MUST render identical samples with and without it (MIDI-97: a program change to the patch already held, and a controller set to the value it holds, change nothing, S80-35 and S80-37).
- Reason: The architecture requires each family document to state its restatement exactly (MIDI-93), so that a viewer who joins a live sound late, or loses a block, is put right within one second. As built, the kit's program repeater repeated only the program change every 500 milliseconds; under DEC-6462 the server restates the whole state.
- Source: `midi-architecture.md`, MIDI-37, MIDI-84 and MIDI-93 to MIDI-99; DEC-6410 item 12; DEC-6462 item 1.
- Verification: A test drives synth80 through a program change, an inline patch, ten control changes, a bend range, a bend and a coarse and fine pitch, plays the restatement into a fresh synth80, and checks the two states equal; a test plays the audio demo's synth80 tune with and without a restatement at a seeded random tick of every block and checks the samples identical.

---

## 10. The CS-80's preset tones and memories

**S80-42. The 22 preset tones.** The server MUST be able to fill a channel's 26 tone values (bytes 0 to 25 or 26 to 51) from the name of any of the CS-80's 22 preset tones, with the values of synth80's `presets::PRESETS`: channel I's row STRING 1, STRING 3, BRASS 1, FLUTE, ELECTRIC PIANO, CLAVICHORD 1, HARPSICHORD 1, ORGAN 1, GUITAR 1, FUNKY 1, FUNKY 3; channel II's row STRING 2, STRING 4, BRASS 2, BRASS 3, BASS, CLAVICHORD 2, HARPSICHORD 2, ORGAN 2, GUITAR 2, FUNKY 2, FUNKY 4. A preset tone MUST be accepted for the channel of its own row and MAY be accepted for the other.
- Reason: The CS-80's tone selectors offer "two rows (ranks) of selectors, each offering 11 preset patches, two memory-programmed patches and one panel-programmed patch"; a preset is a tone, not a whole panel, and the CS-80 recalls it per row. Deckard's Dream has no preset tones of the CS-80, and a program change on synth80 selects a whole patch (S80-35); the preset tones are therefore data from which a patch is built, by name, through the server (DEC-6462), not a message of the instrument. The values are synth80's own reading of the preset boards (`presets.rs`). That a row's presets may be used in the other channel is NeoTeletext's own: on the CS-80 the preset is wired to its row's oscillators, and the owner's manual warns that a channel I preset compared with a channel II panel uses "a completely different set of oscillators" (page 28), but in synth80 the two channels' circuits are identical.
- Source: CS-80 owner's manual, page 7, item [3]; page 28; page 37, item [3]; page 49 ("Preset Patches", "Total Number of Voices"). synth80's source, `presets.rs` (each preset's board and column on the service manual's pages 31, 33, 35 and 37).
- Verification: A server test builds a patch from "BRASS 1" for channel I and "BRASS 3" for channel II and checks bytes 0 to 25 and 26 to 51 equal the two `PRESETS` tones.

**S80-43. The four memories.** synth80 MUST NOT keep memories of its own: the CS-80's four memories, "miniaturized versions of programmable panels I & II", each holding one tone, are served by the patches of a bank. The server SHOULD let a patch be built from two tones held by the program, as it builds one from preset tones (S80-42).
- Reason: A memory is a tone; synth80's patch holds two tones and a bank holds up to 128 patches, which does the memories' work and more. Deckard's Dream has no memories either; its patches are whole panels.
- Source: CS-80 owner's manual, page 23, item [46]; page 36, item [46]. synth80's source, `mod.rs` ("The four memories are not kept: a memory is a tone, and Patch holds two").
- Verification: Inspection.

**S80-44. Program change does not select a preset tone.** A program change MUST select a patch of the bank (S80-35) and nothing else; there MUST be no fixed numbering of the 22 preset tones as program numbers.
- Reason: Neither source defines one: the CS-80 has no program change, and Deckard's Dream's program change selects its own patches. A numbering would be an invention with nothing to be compatible with; a program that wants the presets builds a bank of patches from them (S80-42) and numbers it as it likes.
- Source: CS-80 owner's manual, page 49. DD manual, PDF pages 18 and 19.
- Verification: Inspection.

---

## 11. The two panels compared

Every control of Deckard's Dream's panel (PDF pages 5 to 10) against synth80:

| DD item | DD control | synth80 |
|---|---|---|
| 1 to 26, and the same of layer II | The tone controls | **Has them**, one for one (S80-10). |
| 27 | Coarse pitch, about ±5 semitones, controller 93 | **Has it**, as a performance controller outside the patch, ±500 cents (S80-47; DEC-6465's answer to open question 5). The CS-80's PITCH [18] has a coarse ring of about an octave (−500 to +700 cents, page 49) and a fine knob, a tuning control outside the tones and memories; the adopted interface's range is taken, not the CS-80's. |
| 28 | Fine pitch, about ±1 semitone, controller 94 | **Has it**, as item 27, ±100 cents (S80-47). |
| 29 | Detune layer II, controller 95 | **Has it** (byte 54). |
| 30, 31 | Feet I and II, controllers 102 and 103 | **Has them** (bytes 52 and 53). |
| 32 | Sub-oscillator waveform: sine, saw, ramp, square, random ("sample&hold"), external; controller 104 | **Has it differently:** the fifth position is the CS-80's white NOISE, not random; the sixth, with nothing connected, is off (S80-15). |
| 33 to 36 | Sub-oscillator speed, VCO, VCF, VCA; controllers 105 to 108 | **Has them** (bytes 63 to 66). |
| 37 | Mix I / II, controller 8 | **Has it** (byte 55). |
| 38 | Global brilliance, controller 109 | **Has it** (byte 56). |
| 39 | Global resonance, controller 110 | **Has it** (byte 57). |
| 40 | Initial touch pitch bend, controller 111 | **Has it** (byte 67). |
| 41 to 43 | Aftertouch sub-osc speed, VCO, VCF; controllers 112 to 114 | **Has them** (bytes 68 to 70), following pressure (S80-5). |
| 44 to 47 | Keyboard follow brilliance low and high, level low and high; controllers 115 to 118 | **Has them** (bytes 58 to 61). |
| 48 | Portamento / glissando speed, controller 5 | **Has it** (byte 79). |
| 49 | Portamento / glissando switch of three positions, controller 120 | **Has it**, on controller 3 (S80-20), with an off position that synth80 must gain (S80-27). |
| 50 to 54 | Menu and preset navigation buttons | **Lacks them**: operations of the hardware. |
| 55 | Volume knob, controller 7 | **Has it** as controller 7's gain (S80-25), outside the patch. |

**Controls synth80 has that Deckard's Dream's panel lacks**, so that even a complete Deckard's Dream map could not move them: the ring modulator's five levers ([16]); the SUSTAIN slider ([13] A) and the SUSTAIN I-II switch ([13] B), the latter being a menu setting on Deckard's Dream; the tremolo/chorus's ON/OFF, CHORUS and TREMOLO switches and its SPEED and DEPTH knobs ([15]); the ribbon ([19]), whose place pitch bend takes (S80-7). Section 6 gives each of the others its controller.

## 12. Deckard's Dream controls synth80 lacks, each left out

| Control | Where | Why left out |
|---|---|---|
| Coarse pitch, controller 93 | DD PDF pages 8 and 34; table, PDF page 73 | Not left out: taken as a performance controller outside the patch (S80-47), by DEC-6465's answer to open question 5, which replaced this document's earlier reading, under which it was counted as ignored. Listed so that the change is not silent. |
| Fine pitch, controller 94 | DD PDF pages 8 and 34; table, PDF page 73 | As coarse pitch. |
| The random ("sample & hold") sub-oscillator waveform | DD PDF pages 8, 14 and 36 | The CS-80 has white noise in that place (page 9); synth80 takes the CS-80's (S80-15). |
| The external sub-oscillator input and its rear LEVEL knob | DD PDF pages 12, 13, 36 and 62 | No outside signal reaches a NeoTeletext instrument; the EXT position is the off position, as on a CS-80 with nothing connected (page 9). |
| The off (centre) position of the portamento/glissando switch | DD PDF page 42 | Not left out: synth80 gains it (S80-27). Listed so that it is not silent. |
| The menu and preset navigation buttons, items 50 to 54 | DD PDF page 10 | Hardware. |

## 13. CS-80 controls synth80's panel does not have

These are on the instrument modelled and are not among synth80's 85 controls, so no controller moves them. They are as built today.

| Control of the CS-80 | Owner's manual | Why not |
|---|---|---|
| AC POWER switch [1] | Pages 6 and 39 | Hardware. |
| PITCH [18], coarse ring and fine knob | Pages 14 and 37 | A tuning control outside the tones. Its work is done by the adopted interface's coarse and fine pitch, controllers 93 and 94, likewise outside the patch (S80-47), with the adopted interface's ranges of about ±5 and ±1 semitones rather than the CS-80's coarse ring of −500 to +700 cents (page 49). |
| FOOT PEDAL SELECTOR [17], EXP and EXP/WAH, and the FOOT CONTROLLER pedal | Pages 14 and 39 | No expression pedal reaches a NeoTeletext instrument; controller 7 does the expression pedal's volume work. |
| SUSTAIN FOOT SWITCH assigner [13] D | Page 11 | synth80 is the CS-80 with this assigner off, its SUSTAIN lever always in effect, and controller 64 is MIDI's sustain pedal (S80-26; MIDI-87). Today synth80 is the CS-80 with the assigner on; section 17 lists the change. |
| P/G FOOT SWITCH assigner [14] B, and the foot switch acting on the portamento/glissando [14] C | Page 12 | synth80 has no assigners; its portamento/glissando follows its selector alone (S80-27). |
| EXTERNAL INPUT jack and EXTERNAL LEVEL control | Pages 4 and 37 | No outside signal reaches a NeoTeletext instrument. |
| HIGH/LOW output switch, the LEFT, RIGHT and GENERAL outputs, the headphone jack | Pages 4 and 5 | One mono output (DEC-6437 item 2); the tremolo/chorus is what the mono output has of it (`mod.rs`). |
| The tone selector buttons [3], as buttons | Pages 7 and 37 | Replaced by patches built from preset tones (S80-42) and program change (S80-35). |
| The memory panel [46], as levers | Pages 23 and 36 | Replaced by the bank (S80-43). |

## 14. What is left out of the adopted interface, and what departs from it

### 14.1 Left out

| Item of Deckard's Dream's interface | Where the manual has it | Why synth80 leaves it out |
|---|---|---|
| MIDI MODE (CHANNEL PRESSURE, POLY AFTERTOUCH, MPE), global | PDF pages 17 and 45 | A global setting with no message. synth80 takes both kinds of pressure at once (S80-5, S80-6) and no MPE (S80-8). |
| CHANNEL, the one receive channel or the MPE master channel, global | PDF page 46 | A global setting with no message; synth80 hears all channels (S80-2). |
| CC RECEIVE, global | PDF page 46 | synth80 always takes control changes, as Deckard's Dream with the setting ON. |
| CC74 REPLACE, global | PDF page 47 | Belongs to MPE (S80-8). |
| SLIDERS (PICK UP, MERGE), global | PDF page 48 | Concerns the hardware's physical sliders. |
| MOD WHEEL DESTINATION and MOD WHEEL POLARITY, per patch | PDF pages 48 to 50 | No message sets them; synth80 has one fixed destination (S80-24). |
| VOICE MODE (MONOPHONIC, POLYPHONIC, UNISON), per patch | PDF pages 50 and 51 | No message sets it; synth80 is the CS-80's eight-voice polyphony (S80-30). |
| CARDS PER VOICE and NUMBER OF VOICES, global | PDF pages 51 and 52 | Hardware and global. |
| DETUNE (random pitch drift, 0 to 3.0 Hz), per patch | PDF pages 52 and 53 | No message sets it. synth80's oscillators each stand a fixed amount off their pitch, as built (`voice.rs`). |
| HPF MOD (NORMAL, INVERTED), global | PDF page 53 | Global; synth80 has the CS-80's one envelope polarity. |
| PLAYBACK (SUSTAIN I, SUSTAIN II), per patch | PDF pages 53 and 54 | Not left out in effect: synth80 has the same choice as the CS-80's SUSTAIN I-II switch, on controller 25 (S80-18). The menu setting itself has no message. |
| TIME: LFO MAX, LFO MIN, PWM MAX, PWM MIN, ATTACK TIME, DEC/REL TIME, LFO DEPTH (CLASSIC, EXTENDED), all per patch; PWM MODE (SEPARATE, SYNC) and LFO MODE (POLY, MONO), global; RESET TO DEFAULTS | PDF pages 54 to 59 | No message sets them. synth80 has the CS-80's fixed ranges, read from its adjustment procedure (section 5.4); its pulse-width oscillators are separate for the two channels (as SEPARATE) and its sub oscillator is one for all keys (as MONO). |
| USB MODE, global | PDF page 59 | Hardware. |
| KEYBOARD: PITCHBEND RANGE, TRACKING WIDTH, MIDDLE OCTAVE, global | PDF pages 59 to 61 | No message sets them. The pitch bend range is not left out in effect: synth80 has the same range in semitones, 3 by default and at most 99, set by registered parameter number 0 in place of the menu (S80-7; MIDI-90). The keyboard control's curve is the CS-80's (S80-34). |
| PRESET VOLUME, −6 dB to +6 dB, per patch | PDF page 61 | No message sets it; the levels of a patch are its LEVEL levers. |
| EXTERNAL range, global | PDF page 62 | No external input. |
| EXPANSION: CHAIN and MODE, global, "Available in future revisions" | PDF pages 62 and 63 | Hardware. |
| CALIBRATION: SLIDERS, OSCILLATORS, MICROTUNING, DEBUG, EDIT FREQS, TUNING PROGRAM (the `.mts` file sent by system exclusive), global | PDF pages 63 to 68 | Hardware calibration; the tuning program's bytes are not stated in the source; synth80 is in equal temperament. |
| COOLING FAN, ABOUT, RESET SETTINGS, RETUNE | PDF pages 44, 68 and 69 | Hardware. |
| Firmware update, and the USB drive mode with its files `dd_bank_1.p` and `dd_bank_2.p` | PDF pages 21, 69 and 70 | Hardware, and the files' format is not stated in the source. |
| Panel mode, saving, the three banks' names FCTRY, BNK1, BNK2 | PDF pages 16 to 22 | Operations of the panel. The three banks are reached by controller 0 (S80-36). |
| The factory bank's 128 sounds | PDF page 17 | Not filed; Deckard's Dream's own sounds, not the CS-80's. |
| GLIDE MODE's number, 120 | PDF page 74 | It collides with MIDI 1.0's all sound off, which the architecture keeps in every synthesizer (S80-20; MIDI-9, MIDI-86); open question 3. |

### 14.2 Taken with a difference

| Item | Deckard's Dream | synth80 | Requirement |
|---|---|---|---|
| Channel | One channel, or MPE's master and eight voice channels | All channels alike | S80-2 |
| Pressure | Channel pressure or polyphonic aftertouch, by setting | Both at once | S80-5, S80-6 |
| Touch response SPEED | Said to follow velocity on PDF page 38, pressure on PDF pages 9 and 15 | Pressure, as the CS-80 | S80-5 |
| Pitch bend | ± a range of 1 to 99 semitones, by a global setting with no message, default 3 | ± a range in semitones, default 3, at most 99, set by registered parameter number 0; all 14 bits | S80-7; MIDI-90, MIDI-91 |
| Sub-oscillator fifth waveform | Random (sample and hold) | White noise | S80-15 |
| Modulation wheel | One of eleven destinations, either polarity, by setting | The sub oscillator's depth on the pitch, adding up to 50 cents | S80-24 |
| Sustain pedal | Named, with no range and no behaviour stated | MIDI's sustain pedal: down at 64 to 127, holding released keys; the SUSTAIN lever always in effect | S80-26; MIDI-87 |
| GLIDE MODE | Controller 120 | Controller 3; controller 120 is all sound off | S80-20; MIDI-9, MIDI-86 |
| Bands' and ends' assignment | Not stated | Value 0 at the end of least effect; bands in the panel's order | S80-13, S80-14, S80-15, S80-27 |
| Coarse and fine pitch, controllers 93 and 94 | Panel sliders saved in the patch ("All front panel slider and switch positions", PDF page 19); 0-64-127, "approximately 5 semitones" and "approximately 1 semitone in either direction" (PDF pages 34 and 73); which end is value 0 not stated | Performance controllers outside the patch, like controller 7, left by a program change, a patch and controller 121; exactly ±500 and ±100 cents, a straight line in cents, value 0 the low end (DEC-6465, answer 40) | S80-21, S80-47 |

**Departures of the adopted interface from the architecture's common rules.** The architecture sets one rule for each behaviour common to all MIDI instruments (`midi-architecture.md` section 11.1, MIDI-84 to MIDI-92), and synth80 follows each. Where Deckard's Dream departs from or is silent on one, synth80 follows the architecture's rule, as this table lists:

| Behaviour | Deckard's Dream | synth80, by the architecture's rule |
|---|---|---|
| Reset all controllers, 121 | Not listed (PDF pages 71 to 74) | RP-015's reset, volume unchanged (S80-28; MIDI-84; DEC-6464, awaiting the owner's confirmation) |
| All notes off, 123 | Not listed | Every held key released (S80-28; MIDI-85) |
| All sound off, 120 | Controller 120 is GLIDE MODE (PDF page 74) | All sound off; GLIDE MODE on controller 3 (S80-20, S80-29; MIDI-86) |
| Sustain pedal, 64 | Named, range blank, no behaviour (PDF page 74) | Down at 64 to 127, holding released keys (S80-26; MIDI-87) |
| Note on of velocity 0 | Not stated | A note off (S80-3; MIDI-88) |
| Mode messages, 124 to 127 | Not listed | Each as all notes off and nothing more (S80-28; MIDI-89) |
| Pitch bend range | A global setting with no message, 1 to 99 semitones, default 3 (PDF page 60) | Registered parameter number 0, default 3, at most 99 (S80-7; MIDI-90) |
| Pitch bend resolution | Not stated | All 14 bits (S80-7; MIDI-91) |
| Volume, 7 | "GLOBAL VOLUME", 0 to 127 (PDF page 74) | Taken as the shared volume, with the shared law (S80-25; MIDI-82, MIDI-92) |
| Channels | One receive channel, or MPE's master and voice channels, by a global setting (PDF page 46) | All 16 channels one keyboard (S80-2; MIDI-68) |

## 15. What NeoTeletext defines itself

Each item exists because the filed interface does not define it.
1. **The controller numbers of the twelve CS-80 controls Deckard's Dream lacks (S80-18), and controller 3 for GLIDE MODE (S80-20).** Chosen by the rules of section 6.2. Open questions 2 and 3.
2. **Which end of each lever value 0 is, and which band is which position (S80-13 to S80-15, S80-18, S80-27).** The source gives ranges only. Open question 1.
3. **The patch as 85 values in today's order (S80-33), its equivalence to 85 control changes (S80-40), and the default patch (S80-45).** No patch format exists for either instrument.
4. **Value 127 of GLIDE MODE** belongs to its last band (S80-27); the adopted bands stop at 126.
5. **Controllers 120, 121, 123 and 124 to 127 (S80-28, S80-29), and registered parameter number 0 for the bend range with controllers 6, 38, 96, 97, 100 and 101 (S80-7)**, as NeoTeletext's common layer and the architecture's common rules (`midi-architecture.md`, MIDI-9 and MIDI-84 to MIDI-92), which the adopted table does not list (and whose 120 it uses otherwise).
6. **The modulation wheel's destination and amount (S80-24):** the first listed destination, positive, adding up to 50 cents, as built.
7. **All sixteen channels as one (S80-2)**, and both kinds of pressure at once (S80-5, S80-6).
8. **That bank select takes effect at the next program change (S80-36)**, and that program number 0 is a bank's first patch (S80-35).
9. **The restatement (S80-46)**, by the architecture's rules (MIDI-93 to MIDI-99), which the adopted interface, made for a cable, does not need. (Until this revision item 9 was the ribbon's law for pitch bend and its floor of eight octaves down, as built; S80-7 now follows the architecture's MIDI-90 and MIDI-91, and Deckard's Dream's own default and largest range.)
10. **How a moved lever is heard (S80-37):** a step a tick, as built.
11. **That a preset tone may be used in the other channel's row (S80-42).**
12. **The laws from a lever's position to volts, hertz and seconds**, which neither the adopted interface nor this document specifies: they are synth80's own readings of the service manual and adjustment procedure, each with its `Source:` line in `law.rs`, `voice.rs` and `mod.rs`.
13. **The SUSTAIN lever always in effect, as the CS-80 with its SUSTAIN FOOT SWITCH assigner off (S80-26)**, with controller 64 as the architecture's sustain pedal (MIDI-87). Open question 7.
14. **What the DD manual leaves unstated of coarse and fine pitch (S80-47):** that value 0 is the low end; that the manual's "approximately 5 semitones" and "approximately 1 semitone" are exactly 500 and 100 cents; the straight line in cents between the ends and the centre at 64; that the two offsets add to each other and to the pitch bend's and act as it acts; that they are outside the patch, left by a program change, a patch, controller 121, controller 120 and a lost block (DEC-6465, answer 40); that each stands at 64 before any arrives; and that a change slides as a lever does (S80-37).

## 16. Open questions for the owner

**1. Which end of a lever is value 0?**
The adopted table gives "0-127" and "0-64-127" and never says which end of the slider is 0. Deckard's Dream's sliders have their greatest effect at the top for some controls and at the bottom for others (PDF page 23). The two readings agree for every control whose greatest effect is at the top of its slider: all 26 tone controls of each channel (with RESh read by its text, S80-13) and the PORTAMENTO/GLISSANDO speed. They differ, so that the control's meaning inverts, for every one of these: SUB OSCILLATOR SPEED, VCO, VCF and VCA; TOUCH RESPONSE PITCHBEND, SPEED, VCO and VCF; RESONANCE; DETUNE CH II; MIX I-II; BRILLIANCE; the four KEYBOARD CONTROL levers; FEET I and II (whose bands would run 2′ to 16′); SUB OSCILLATOR FUNCTION (whose bands would run EXT to sine); and GLIDE MODE, if its positions were read from right to left. The twelve controllers of section 6 are NeoTeletext's own and follow whichever reading is chosen.
- *Option A: value 0 is the end of least effect (this document).* Every lever reads the same way: more value, more effect. It is how synth80 counts every lever today, so today's patches keep their values. The DD manual's mod wheel destinations support it weakly: "LFO DEPTH - VCO (CC 106)" with "POSITIVE: adds to the value of the CC destination" (PDF pages 48 to 50) reads naturally only if a larger value is more depth.
- *Option B: value 0 is the bottom of the slider (nearest the player).* The DD manual's DEBUG readout counts a slider "approximately 0 at the bottom to approximately 255 the top" (PDF page 66), which suggests the firmware's count follows the slider's position; a value sent by Deckard's Dream's own panel, if it sends any (not stated in the source), might then be the physical position. Under B, the controls listed above invert, and today's patches must have those bytes inverted when converted.
- *Option C: find out.* A Deckard's Dream owner, or a later manual with a fuller table, could settle it in minutes.
- *Recommendation:* A now, as it is consistent, matches what is built and has the only textual support; C if the owner can reach either, and then the bands and directions of sections 5.4 and 5.5 are corrected in one change.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: value 0 is the end of least effect; sections 5.4 and 5.5 are corrected in one change if a Deckard's Dream owner or a fuller manual says otherwise.

**2. The controller numbers of the twelve CS-80 controls Deckard's Dream lacks.**
- *Option A: the block 20 to 31 (this document).* Twelve consecutive controllers MIDI 1.0 leaves undefined and the adopted table does not use, in patch order. Simple, one message a change, readable as a block.
- *Option B: the undefined controllers in ascending order* (3, 9, 14, 15, 20 to 27). The same set but scattered; no gain.
- *Option C: non-registered parameter numbers (controllers 99, 98, 6 and 38).* Keeps every free controller free, but four messages a change where one serves, and the adopted interface uses no parameter numbers at all.
- *Option D: system exclusive under a NeoTeletext identifier.* Nothing to be compatible with, long, and not a control change, so not part of a patch as decision A4 defines it.
- *Recommendation:* A.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: controllers 20 to 31 in patch order (S80-18).

**3. Controller 120: GLIDE MODE or all sound off?** *Answered by the architecture:* `midi-architecture.md`, MIDI-9 and MIDI-86, require controller 120 to be all sound off in every synthesizer and require this document to move GLIDE MODE, so option A is what this document specifies (S80-20); the owner confirms it in approving the architecture. The options are kept as the record of the choice.
- *Option A: keep all sound off on 120, and put GLIDE MODE on 3 (this document).* Every NeoTeletext synthesizer silences on 120, as MIDI 1.0 says; a stream written for Deckard's Dream that moves GLIDE MODE on 120 would instead silence synth80, which a sender must translate.
- *Option B: follow Deckard's Dream: 120 is GLIDE MODE on synth80, and synth80 has no all sound off by controller.* Exactly the adopted interface, but synth80 alone among NeoTeletext's synthesizers could not be silenced at once by the common message, and the architecture document's rule for all synthesizers would need an exception.
- *Option C: 120 is all sound off when its value is 0 and GLIDE MODE otherwise.* Breaks GLIDE MODE's first band (portamento, 0 to 42).
- *Recommendation:* A.

**4. Pitch bend: the ribbon, or a range in semitones?** *The same question as the architecture's open questions 5 and 6* (`midi-architecture.md` section 20: pitch bend range by registered parameter number 0, and all 14 bits, in every family), which this document now follows: S80-7 specifies option C, the architecture's recommendation. The family's facts for the owner's answer:
- *Option A: the ribbon's law (as built until this revision).* The CS-80's only pitch controller; up to an octave up, towards nothing down, linear in frequency. It contradicts MIDI-90 and MIDI-91 and is open only if the owner answers the architecture's open questions 5 and 6 with their option B.
- *Option B: Deckard's Dream's default, ±3 semitones, linear in pitch, fixed.* What a sender writing for Deckard's Dream expects; loses the ribbon's wide downward reach. It is the architecture's option B of its open question 5 for synth80.
- *Option C: B, with the range set by registered parameter number 0 (pitch bend sensitivity), at most 99 semitones as Deckard's Dream allows (this document, S80-7).* The adopted interface sets the range in a menu, not by the registered parameter; the architecture adds registered parameter number 0 to every family (MIDI-90; its section 19, item 6).
- Also to decide, a question of this family alone: whether pitch bend should follow the CS-80's sustain modes, bending released notes only in SUSTAIN II (owner's manual, page 14), which is not built.
- *Recommendation:* C, as the architecture recommends; and do not build the sustain-mode behaviour of page 14, which belongs to the ribbon's law and not to a bend in semitones.
- Answered by DEC-6465 (awaiting the owner's confirmation): the architecture's open questions 5 and 6 were answered with their option A, so this document's option C stands as written (S80-7), and the ribbon's law is not kept. The sustain-mode behaviour of page 14 is not built, as recommended (DEC-6465 takes every document's recommendation except on questions 29 and 40 of `open-questions.md`).

**5. Coarse and fine pitch (controllers 93 and 94).**
- *Option A: leave them out (this document until DEC-6465).* The patch stays 85 values; a Deckard's Dream stream's tuning moves are counted as ignored.
- *Option B: add them as two more patch values, centred at 64,* coarse about ±5 semitones and fine about ±1 semitone as the DD manual says (PDF page 34), making the patch 87 values. Deckard's Dream saves "All front panel slider and switch positions" (PDF page 19), which include them; the CS-80's PITCH is a tuning control outside its tones.
- *Option C: take them as performance controllers outside the patch*, like controller 7 (this document since DEC-6465, S80-47).
- *Recommendation:* C: it honours a Deckard's Dream stream's tuning without making a tuning knob part of every sound.
- Answered by DEC-6465 (awaiting the owner's confirmation): option C, as recommended. This document had been written for option A and is amended to option C: S80-47 takes controllers 93 and 94 as performance controllers outside the patch, with the ranges and directions of the DD manual (PDF pages 8, 34 and 73) and what it leaves unstated as NeoTeletext's own (section 15, item 14); the patch stays 85 values; S80-1, S80-12, S80-21 to S80-23, S80-28, S80-35, S80-39 and S80-46, and sections 3, 11 to 15 and 17, are amended to match.

**6. MPE.**
- *Option A: no MPE (this document).* Every channel is the one keyboard.
- *Option B: define MPE for synth80:* a master channel and voice channels, each voice channel's pitch bend, pressure and controller 74 applying to the note on that channel. The DD manual gives only the channel layout (PDF page 46); how the master and voice channels' messages combine would be NeoTeletext's own, or the MIDI Association's MPE specification's, which is not filed.
- *Recommendation:* A until the MPE specification is filed and the owner wants per-note bending; then B, by that specification.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: no MPE until its specification is filed and the owner wants per-note bending.

**7. Controller 64: MIDI's sustain pedal, or the CS-80's foot switch?**
The architecture sets one sustain pedal for every synthesizer: down at 64 to 127, holding released keys as if held, releasing them when it goes up (`midi-architecture.md`, MIDI-87). synth80 today takes controller 64 as the CS-80's FOOT SWITCH PEDAL with its SUSTAIN assigner on: while it is down, released notes die away in the SUSTAIN lever's time, and lifting it ends every sustain at once (CS-80 owner's manual, page 11, item [13] C). The two differ: the foot switch never holds a note at its full level.
- *Option A: MIDI's sustain pedal, with the SUSTAIN lever always in effect as on the CS-80 with its assigner off (this document, S80-26).* The same pedal on every synthesizer, as MIDI-87 requires; the SUSTAIN lever and the SUSTAIN I-II switch keep their meaning, now set in the patch rather than switched by the foot.
- *Option B: the CS-80's foot switch, as built.* The instrument's own behaviour, but a departure from the architecture's one rule, which would need MIDI-87 amended to let synth80 differ.
- *Recommendation:* A, under the owner's rule of one behaviour for every synthesizer.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written (S80-26): controller 64 is MIDI's sustain pedal, with the SUSTAIN lever always in effect.

## 17. Differences from what is built today

What exists is described in `synthesizer-wire-format.html` and in synth80's source. Implementing this document changes the following.

**The patch.**
1. The patch stays 85 bytes in today's order: channel I's tone, channel II's tone, then the 33 other controls (`PATCH_BYTES`, `TONE_BYTES`, `GLOBAL_BYTES` in `patch.rs`). The levers' values are unchanged: today's 0 to 127 is the controller's value (S80-13).
2. The switches change coding: today 0 or 1 (bytes 3, 4, 29, 30, 76, 80, 81 and 82), they become values in two bands, 0 to 64 off and 65 to 127 on, written as 0 and 127 (S80-14, S80-18).
3. The selectors change coding: today positions 0 to 5 (bytes 52, 53 and 62), they become values in six bands, written as 0, 22, 43, 64, 85 and 106 (S80-15). The default patch's FEET bytes become 22 where they are 1 today.
4. Byte 78 changes from today's PORTAMENTO or GLISSANDO switch (0 or 1, `Global::Glissando`) to the three-position selector of S80-27, written as 0, 43 and 85; the default patch's byte 78 becomes 43 (off) where it is 0 today.
5. synth80 gains the selector's off position: today the glide is off only when the speed lever is at 0 (`glide_step` in `voice.rs`).
6. Today a patch is refused for a byte above its control's largest value (`PatchError::Value`, `TONE_MAXIMA`, `GLOBAL_MAXIMA`). After the change every value from 0 to 127 is valid in every byte, and the only faults are the length and a byte above 127. `Tone::from_levers` and the setters' clamping follow.
7. The engine's `SYNTH80_PATCH_BYTES` (`neoteletext-audio/src/codec.rs`) stays 85. The server's patch check (`teletext-runtime/src/protocol/check/instrument/patch.rs`, `synth80`) and its refusal messages change to the new coding. The kit's `synth80-patch.ts` packer moves into the server, which builds patches from named fields and preset names (DEC-6462; S80-41, S80-42); the kit keeps types and calls.

**The messages.**
8. Today synth80 takes control changes of controllers 1, 7, 64, 120, 121 and 123 only, and counts every other as ignored (`control_change` in `mod.rs`). It gains the 52 tone controllers of S80-10, the 21 master controllers of S80-11 (controller 3 in place of the adopted 120), and the twelve of S80-18, each setting one field and sliding as S80-37 says; `Synth80` needs a way to set one field. It also gains controllers 93 and 94, coarse and fine pitch, as performance controllers outside the patch (S80-47): today synth80 has no tuning control and counts both as ignored.
9. Today the server and the kit refuse a control change of any controller but 1, 7, 64, 120, 121 and 123 ("a control change is of controller 1, 7, 64, 120, 121 or 123"). For synth80 the server must allow the controllers of S80-7, S80-10, S80-11, S80-18, S80-20, S80-28 and S80-47 and controller 0, and the kit's copy of the check is removed (DEC-6462; MIDI-22).
10. Today a program change chooses patch 0 to 31 and a bank holds 1 to 32 patches (`PATCH_BANK_PATCHES`). They become 0 to 127 and 1 to 128 (S80-35, S80-41); controller 0 selects among up to three of the 1 to 10 banks a sound may name (S80-36; MIDI-57). Today a program change must have a second data byte of 0 in its four-byte slot, and a channel pressure likewise; under decision A3 both are the ordinary two-byte MIDI messages.
11. Today a patch missing from the bank becomes the default with no message; after the change a program change to a missing patch is also counted as ignored (S80-35).
12. Pitch bend changes from the ribbon's law, linear in frequency, up to an octave up and towards nothing down (`RIBBON_FLOOR`, `RIBBON_REST`), to a range in semitones either way, 3 by default and at most 99, set by registered parameter number 0 through controllers 101, 100, 6, 38, 96 and 97, which synth80 gains (S80-7; MIDI-90, MIDI-91; open question 4). The ribbon's dependence on the sustain mode (CS-80 owner's manual, page 14), never built, is not required.
13. Controller 64 changes from the CS-80's foot switch with its SUSTAIN assigner on to MIDI's sustain pedal, which holds released keys, and the SUSTAIN lever acts whatever the pedal (S80-26; MIDI-87; open question 7).
14. Controllers 124 to 127, counted as ignored today, become all notes off (S80-28; MIDI-89). Reset all controllers also sets the registered parameter selection to none and leaves the bend range (S80-28; MIDI-84). After a lost block synth80 also lifts the pedal and clears the registered parameter selection (S80-39; MIDI-102).
15. Nothing else changes in note on, note off, the velocity and pressure routes, the modulation wheel, volume, all sound off or all notes off: S80-3 to S80-6 and S80-24, S80-25 and S80-29 describe what is built, save item 5 above. System exclusive, which today cannot be expressed in a four-byte slot, can be expressed under decision A3 and is counted as ignored by the receiver and refused by the server (S80-9).
16. The kit's program repeater, which repeats only the program change every 500 milliseconds, is replaced by the server's restatement of synth80's whole state (S80-46; MIDI-93 to MIDI-99; DEC-6462).

**The block.**
17. Today a synth80 block is 1 to 16 slots of four bytes (a time, a status byte, two data bytes). Under decision A3 it becomes a Standard MIDI File track-event list with a tick of 0.1 millisecond, of at most 1,005 bytes and 256 events (MIDI-23 to MIDI-31). That change is the architecture document's and is the same for every family; synth80's part of it is only that a whole panel as control changes (85 events, 340 bytes, S80-40) no longer has to fit in 16 slots. Its codec code changes only as the architecture's open question 1 is answered (S80-41); DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation), so it becomes 18.

**Tests, documents and records.**
18. The tests that build patches from bytes (`tests/synth80_patch.rs`, `tests/synth80_instrument.rs`, `tests/synth80_filter.rs`, the control-sweep test, the engine's `tests/synths.rs`, the server's `protocol/tests/sound.rs` and `channel/tests/instrument.rs`, and the kit's patch tests) change to the new coding of switches, selectors and byte 78. New tests are those each requirement's "Verification" names.
19. The module documentation of `patch.rs` ("The byte layout here is therefore this crate's own", "a switch is 0 or 1; a selector is its position from 0") and of `mod.rs` (the list of messages taken) are rewritten to cite this document's requirements once they are rdm requirements. The two HTML documents in `teletext-reference/synthesizers/` describe the old form and are regenerated.
20. DEC-6458 names the emulator's directory by its old name (`src/cs80/`) and says Deckard's Dream has no control change "for the ring modulator, tremolo or ribbon"; the ribbon needs none, being pitch bend, and DEC-6458 does not mention the sustain controls, which also have none, nor the collision of controller 120. `cs-80/documents.tsv`'s row for the DD manual says the same and is otherwise accurate. Both are to be corrected when these requirements are recorded.
