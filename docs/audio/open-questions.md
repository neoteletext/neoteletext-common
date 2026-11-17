# The synthesizers' interface documents: open questions for the owner

**Purpose.** This file collects, in one numbered list, every question for the owner that the eight synthesizer interface documents of this folder leave open: `midi-architecture.md` and the seven family documents `synth6581-synth8580.md`, `synth7.md`, `synth106-synth60.md`, `synthd.md`, `synth53-synth52-synth51.md`, `synth8.md` and `synth80.md`. Each question gives its options and the recommendation, and cites the document and section where it is argued, which remains the place of the full argument. A question raised in two documents appears once, citing both. Questions the documents raised and have since answered are listed at the end, with what answered them.

**Status.** Collected on 18 November 2026, after the eight documents were reconciled with each other and with DEC-6453, DEC-6461, DEC-6462 and DEC-6464, for the owner's review. The questions were answered on 18 November 2026 by DEC-6465, taken at the owner's delegation ("i want you to answer as many as you can unless you think its a critical decision for some reason - make sensible decisions") and recorded in rdm as proposed, awaiting the owner's confirmation; each answer is given under its question's recommendation, as "*Answered (DEC-6465):*", in DEC-6465's own words. Question 7, the documents to obtain, is not answered: it waits on the owner, because the documents need the owner's own sign-in, and the owner's to-do for it is TODO-6466. Each document is written for DEC-6465's answers until the owner rules otherwise. The answers take each question's recommendation except question 29, which departs from its document's recommendation for the owner's rule of one behaviour, the document having already been written for the option chosen. Two documents were amended to the answers: `synth80.md` for question 40, whose answer is its recommendation but not the option it had been written for, and `synth7.md` for question 16, whose answer is its recommendation but not the voice it had specified.

**A decision awaiting the owner, not a question of the documents.** DEC-6464 records that every synthesizer answers Reset All Controllers (controller 121) identically, by the MIDI Association's Recommended Practice RP-015, which leaves volume unchanged. The owner required one behaviour for all; the choice of RP-015 was made under DEC-6453 and is recorded in rdm as proposed, awaiting the owner's confirmation. Every document is written for it (`midi-architecture.md`, MIDI-84).

---

## The MIDI architecture (`midi-architecture.md`)

**1. Codec numbers: new codes 12 to 19, or keep 3 to 11?**
DEC-6461 item 3 said that "the codec numbers and the bytes of the records do not change" for the rename; decisions A3 and A4 of the owner's brief, taken after it, change every synthesizer's block and patch. Every family document refers to this question rather than deciding it: synth6581 and synth8580 code 12 or the present 3; synth7 code 13 or the present 4, its banks 19 or the present 5; synth106 and synth60 code 14 or the present 6; synthD code 15 or the present 7; synth53, synth52 and synth51 code 16 or their present code; synth8 code 17 or the present 9; synth80 code 18 or its present code; the banks of the analogue families 19 or the present 11.
- *Option A: new codes 12 to 19, codes 3 to 11 retired* (MIDI-107 to MIDI-109). A browser of today ignores the new sounds and stays silent; nothing old is misread. It amends DEC-6461 item 3.
- *Option B: keep codes 3 to 11 with the new contents.* No new numbers; but a browser of today reads event lists as four-byte slots and plays wrong notes or noise until it is updated.
- *Recommendation:* A. The requirements are written for it; under B only the numbers of MIDI-107 to MIDI-109 change.
- *Answered (DEC-6465):* Codec numbers: new codes 12 to 19, codes 3 to 11 retired (option A). Nothing deployed misreads a new sound; a browser of today stays silent instead of playing noise. This amends DEC-6461 item 3's statement that codec numbers do not change.
- *Argued in:* `midi-architecture.md`, section 14 and section 20 question 1; referred to by every family document (`synth6581-synth8580.md` S6581-1 and section 9.1; `synth7.md` S7-49; `synth106-synth60.md` section 17 and section 18 item 1; `synthd.md` scope and section 14; `synth53-synth52-synth51.md` S53-1; `synth8.md` S8-29; `synth80.md` S80-41).

**2. How often the server restates a part, and whether a stored sound's opening restatement is the server's or the program's.**
- *Option A (written):* the server restates every part within every 50 blocks (one second), aiming at every 25, and writes block 0's restatement of a stored sound itself, while a family document may require the program's own first events to be that restatement (as `synth6581-synth8580.md`, S6581-45, does).
- *Option B:* 25 blocks as a hard bound: at most half a second of wrong timbre for a viewer who joins, at twice the bytes.
- *Recommendation:* A, matching DEC-6410 item 12 and the synth6581 family's document, whose S6581-46 now follows MIDI-96.
- *Answered (DEC-6465):* Restatement: the server restates every part within every 50 blocks, aiming at 25, and writes a stored sound's block-0 restatement itself (option A).
- *Argued in:* `midi-architecture.md`, section 12 (MIDI-96, MIDI-99) and section 20 question 2.

**3. Several banks for one sound.**
The adopted interfaces reach more patches than one bank holds. For synth7 in particular, the DX7 maps program changes 32 to 63 to the 32 voices of a cartridge (DX7 manual, pages 30 and 32), which synth7 ignores today.
- *Option A (written):* 1 to 10 banks a sound, chosen by bank select or by program range as each interface does. For synth7, a sound may name a second 32-voice dump as its cartridge bank, and program change `32 + p` chooses its voice `p`, so a sound may hold 64 voices; a synth7 sound naming more than two banks is refused (`synth7.md`, S7-50).
- *Option B:* one bank a sound, at most 128 patches: simpler, but the DX7's programs 32 to 63, the Prophet-5's groups and Deckard's Dream's three banks cannot all be reached as the interfaces reach them. Under B, synth7's program changes 32 to 63 set the default voice and are counted, as 64 to 127 do.
- *Recommendation:* A.
- *Answered (DEC-6465):* One sound may name 1 to 10 banks (option A); for synth7, a second 32-voice dump as its cartridge bank reached by program changes 32 to 63.
- *Argued in:* `midi-architecture.md`, MIDI-57 and section 20 question 3; `synth7.md`, section 16 question 3 and S7-50.

**4. A restatement made for a viewer who joins a live sound.**
The server could send a connection that joins a live sound one extra event list at once with every part's restatement, instead of letting it wait up to a second; but a block number has one content for every receiver (MIDI-44), so this needs a new record or a block numbered apart.
- *Option A (written):* no; the periodic restatement alone, which also serves teletext lines, where nothing is sent to one viewer.
- *Option B:* design a restatement for joining in a later version.
- *Recommendation:* A now; B only if the second of wrong timbre is heard as a fault.
- *Answered (DEC-6465):* No restatement made for a single joining viewer now (option A); reconsider only if the second of wrong timbre is heard as a fault.
- *Argued in:* `midi-architecture.md`, MIDI-100 and section 20 question 4.

**5. Pitch bend range by registered parameter number 0 in every family.**
The owner asked for one rule for behaviours common to all MIDI instruments. No filed interface documents registered parameter number 0; three (the Juno-106, the Voyager and Deckard's Dream) have no message for the range at all. Every family document is written for option A: synth7 beside function parameter 65 (S7-9); synth106 and synth60 beside the JU-06A's controller 87 (S106-26); synthD, which states option B's fixed range of 797 cents (SD-6); synth53, synth52 and synth51 beside controller 70 and parameter number 86 (S53-8); synth8 beside controller 41 (S8-14, S8-31); synth80, whose range Deckard's Dream sets in a menu, 1 to 99 semitones, default 3 (S80-7).
- *Option A (written):* registered parameter number 0 in every family, beside each interface's own message, the last received of either holding, limited to the family's most.
- *Option B:* each family's own message only; synthD, synth106 (the Juno-106 has only a panel knob) and synth80 keep fixed ranges (synthD 797 cents; synth80 Deckard's Dream's ±3 semitones).
- *Recommendation:* A: it is MIDI's standard way and the only one that can be the same everywhere.
- *Answered (DEC-6465):* Pitch-bend range by registered parameter number 0 in every family, beside each interface's own message (option A).
- *For synth80 alone:* the CS-80's ribbon law (up to an octave up, towards nothing down, linear in frequency), as built until now, is open only if this question and question 6 are answered B; and whether pitch bend should follow the CS-80's sustain modes (owner's manual, page 14) is recommended not to be built.
- *Argued in:* `midi-architecture.md`, MIDI-90 and section 20 question 5; `synthd.md`, SD-6; `synth80.md`, section 16 question 4 and S80-7; related to question 29 below.

**6. Pitch bend at full resolution in every family.**
- *Option A (written):* all 14 bits in every family; the DX7's ignoring of the low seven bits and the Juno-106's of the low six bits are listed as departures (`synth7.md` section 14.2; `synth106-synth60.md` S106-7 and section 15.4).
- *Option B:* each instrument's own resolution, as its interface states.
- *Recommendation:* A, under the owner's rule of one behaviour.
- *Answered (DEC-6465):* Pitch bend at full 14-bit resolution in every family (option A).
- *Argued in:* `midi-architecture.md`, MIDI-91 and section 20 question 6; `synth80.md`, section 16 question 4.

**7. The documents to obtain.**
The MIDI 1.0 Detailed Specification, the Standard MIDI Files 1.0 specification and the Recommended Practice RP-015 are not filed (`midi-architecture.md`, section 1.5); every statement marked "(MIDI 1.0, to be checked)", "(Standard MIDI Files 1.0, to be checked)" or "(RP-015, to be checked)" in any of the eight documents waits on them. The MIDI Association's MPE specification is also not filed; `synth80.md` needs it only if question 41 is answered B.
- *Recommendation:* the owner or the main session fetches and files them, with their rows in `documents.tsv` and their rdm sources, before any requirement marked so is built.
- *Not answered (DEC-6465):* NOT DECIDED; left with the owner. The MIDI 1.0 Detailed Specification, the Standard MIDI Files 1.0 specification, the Recommended Practice RP-015 and the MPE specification are published by the MIDI Association, whose downloads are understood to need a signed-in account; the owner's rules forbid scripting logins. A to-do for the owner records it. Every requirement marked "to be checked" waits on it. The to-do for the owner is TODO-6466.
- *Argued in:* `midi-architecture.md`, section 1.5 and section 20 question 7; the "Documents not filed" paragraph of each family document's sources.

---

## synth6581 and synth8580 (`synth6581-synth8580.md`)

**8. Should NeoTeletext define a note-playing layer for synth6581 and synth8580?**
ASID has none: a tune plays the chip by writing registers. Today the TypeScript kit has helpers (`synth6581Note`, `synth6581Gate`, `synth6581HardRestart`) that turn a note into register images; under DEC-6462 they cannot stay in a kit.
- *Option A: no note layer anywhere in NeoTeletext* (S6581-26, S6581-52). A program computes its own registers, or a converter makes a sound from existing music. Nothing is invented.
- *Option B: note messages in the server's program protocol*, which the server turns into register updates. The receiver and the block stay ASID, but it is a whole instrument design of NeoTeletext's own (voice allocation, which registers a note sets, the hard restart's timing), which DEC-6453 forbids unless it has to be.
- *Option C: note messages in the block, played by the receiver.* All of option B's design, with the receiver's work and state growing; the block is then no longer ASID.
- *Recommendation:* A. Help with notes belongs in an example program of a channel, not in the protocol, the server or a kit.
- *Answered (DEC-6465):* No note-playing layer for synth6581 and synth8580 anywhere in NeoTeletext (option A); note help belongs in an example channel program.
- *Argued in:* section 8 question 1 and section 3.9.

**9. Should a sound carry several chips (ASID commands 0x50 to 0x5F)?**
- *Option A: no* (S6581-20). One sound is one chip; a tune for two chips is two sounds started together on two audio channels, whose starts are not guaranteed to fall on the same sample.
- *Option B: yes, up to a stated number of chips in one sound*, with commands 0x50 and above taken. It needs a rule for which kind a sound of a 6581 and an 8580 is, more work for each block, and a larger block bound.
- *Recommendation:* A, until a channel needs a tune for more than one chip; then B with the chips' kinds stated in the OBJECT record.
- *Answered (DEC-6465):* One chip per sound (option A), until a channel needs a tune for more than one chip.
- *Argued in:* section 8 question 2, section 3.3 and S6581-20.

**10. Should command 0x30, write order and timing, be taken?**
- *Option A: no* (S6581-22). Order and time between writes are given by separate messages at their own ticks, to 0.1 millisecond.
- *Option B: yes, as a setting of the sound in its OBJECT record* (56 bytes in an extension, applied to every register data message), which the receiver could honour only to the nearest sample, about 20.5 chip cycles.
- *Recommendation:* A; revisit if a converted tune is shown to sound wrong for want of it.
- *Answered (DEC-6465):* ASID command 0x30 not taken (option A).
- *Argued in:* section 8 question 3 and S6581-22.

**11. Should the clock come from ASID's command 0x31 instead of the sound's `clock` field and OBJECT record?**
- *Option A: the OBJECT record and the `clock` field* (S6581-39, as built). Every receiver has the clock before the first block.
- *Option B: command 0x31's bit 0, in the first block.* ASID's own place for it, but a viewer who joins late, or loses the first block, plays at the wrong pitch, and a message could change the clock in the middle of a sound.
- *Recommendation:* A.
- *Answered (DEC-6465):* The clock stays in the OBJECT record and the `clock` field (option A).
- *Argued in:* section 8 question 4, S6581-23 and S6581-39.

**12. Is twenty register data messages a block the right bound?**
This is the family's own lower bound within the architecture's 256 events and 1,005 bytes (MIDI-30, MIDI-31).
- *Option A: 20* (S6581-42): the highest speed command 0x31 names, with a quarter more for faster frames; at most 874 bytes a block.
- *Option B: 16*: at most 702 bytes a block; a tune at speed 16 with a frame shorter than 20 milliseconds would not fit.
- *Option C: more, for example 50*: up to 2,164 bytes a block, more than the architecture's largest block of 1,005 bytes, so that bound would also have to change, and two and a half times the receiver's worst-case work.
- *Recommendation:* A.
- *Answered (DEC-6465):* At most 20 register data messages per block (option A).
- *Argued in:* section 8 question 5, S6581-42 and S6581-43.

**13. How is existing music for this chip to be converted, if at all?**
The files hold a player program for the original machine's processor. DEC-6428 allows such a program to be run only in a sandbox to compare output when building an emulator (step 4); it does not cover using its output as a channel's content.
- *Option A: a converter of NeoTeletext's own*, with a processor emulator written under the clean-room procedure and the file format filed first.
- *Option B: capture an existing player's ASID output* in the sandbox. Quick, but it needs the owner's decision extending DEC-6428 step 4, and the player's licence must allow its output to be used so.
- *Option C: no converter for now.*
- *Recommendation:* C now; A if the owner wants existing music on channels; B only by an explicit decision naming the program and its licence.
- *Answered (DEC-6465):* No converter of existing chip music for now (option C); a clean-room converter of NeoTeletext's own only if the owner later wants existing music on channels; capturing another player's output only by an explicit owner decision naming the program and its licence.
- *Argued in:* section 8 question 6, section 3.11 and S6581-60.

---

## synth7 (`synth7.md`)

**14. Controllers 6, 96 and 97 (data entry) outside registered parameter number 0.**
Under MIDI-90 they act on registered parameter number 0 while it is selected (S7-9); the question is what they do otherwise. The DX7 receives controller 6 for master tune only (page 32); the TX7 uses all three on the parameter last named by a parameter change (TX7 manual, printed page 34).
- *Option A: leave all three out otherwise* (S7-18). A program changes a parameter with a parameter change, which names it.
- *Option B: controller 6 as master tune of the part*, value 64 the centre, ±75 cents scaled linearly (NeoTeletext's own scale); 96 and 97 left out.
- *Option C: as the TX7 does*: 6, 96 and 97 alter the voice or function parameter last named by a parameter change on the part's channel.
- *Recommendation:* A. Master tune serves tuning an instrument to a band, which a NeoTeletext sound never needs, and its scale would be invented; C is another instrument's behaviour, which a parameter change already gives exactly.
- *Answered (DEC-6465):* synth7's controllers 6, 96 and 97 do nothing outside registered parameter number 0 (option A).
- *Argued in:* section 16 question 4 and S7-18.

**15. Channel pressure: take it, though the DX7's reception list does not name it?**
The DX7 transmits channel pressure and has after-touch parameters (76 and 77), but its reception list on page 32 does not name the message. The TX7, of the same voice format, receives it (TX7 manual, printed pages 32 and 34).
- *Option A: take it* (S7-22), as the one message that plays the after-touch parameters.
- *Option B: ignore it*; the after-touch parameters are then settable but have no effect.
- *Recommendation:* A, now corroborated by the TX7.
- *Answered (DEC-6465):* synth7 takes channel pressure (option A), as the TX7 manual confirms for the same voice format.
- *Argued in:* section 16 question 5 and S7-22.

**16. The default voice: synth7's own, or the maker's initial voice?**
synth7's default voice (S7-51) was, until DEC-6465, a plain sine at algorithm value 15, named "PLAIN SINE", as built. The DX7 II manual gives the maker's initial voice (printed page Add-8): the same in every parameter but algorithm value 0 and the name "INIT VOICE".
- *Option A: take the maker's initial voice.*
- *Option B: keep synth7's*, as built.
- *Recommendation:* A, under DEC-6453; it changes no sound.
- *Answered (DEC-6465):* synth7's default voice becomes the maker's initial voice from the DX7 II manual (option A), under DEC-6453; it changes no sound.
- *Argued in:* section 16 question 6 and S7-51.

**17. The portamento switch: on at a sound's start, but off after reset all controllers?**
S7-17 starts the switch on, so that a portamento time is heard without a pedal (NeoTeletext's own); MIDI-84 puts the portamento pedal off on reset all controllers in every synthesizer. A part therefore glides before controller 121 and not after it. (synthD meets the same clause of MIDI-84 differently: question 25.)
- *Option A (written):* on at the start, off after controller 121.
- *Option B: off at the start too*, so that a part glides only after controller 65 at 64 or more.
- *Option C: on after controller 121 too*, a departure from MIDI-84 against the owner's rule of one behaviour (DEC-6464).
- *Recommendation:* A until RP-015 is filed and read; then B if RP-015 sets the portamento pedal off, so that start and reset agree.
- *Answered (DEC-6465):* synth7's portamento switch: on at a sound's start, off after Reset All Controllers (option A), revisited when RP-015 is filed.
- *Argued in:* section 16 question 7 and S7-17.

**18. A bank given as a list of fewer than 32 voices.**
MIDI-15 lets a program give a bank as a list of 1 to 128 patches, but a synth7 bank image is exactly one 32-voice dump.
- *Option A: the server fills the missing voices with the default voice* (S7-51) and builds the 32-voice dump; a list of more than 32 voices is refused.
- *Option B: the server refuses a list of other than exactly 32 voices.*
- *Recommendation:* A: it keeps today's banks of fewer than 32 voices working, and the default voice is what a missing program already plays (MIDI-59).
- *Answered (DEC-6465):* A synth7 bank given as fewer than 32 voices is filled with the default voice by the server; more than 32 is refused (option A).
- *Argued in:* section 16 question 8 and S7-49.

---

## synth106 and synth60 (`synth106-synth60.md`)

**19. How is a synth60 patch carried?**
The Juno-60's sub-oscillator switch, envelope pulse-width modulation and I+II chorus have no place in the Juno-106's 18 values.
- *Option A: the 18 values and the three JU-06A controller values* (S106-31), 33 bytes as messages. Every byte is an adopted interface's, and the 18 values alone are the nearest Juno-106 patch, readable by any Juno-106 tool. It makes the synth60 bank image the only one holding channel messages (`midi-architecture.md`, MIDI-56).
- *Option B: the three settings in bits of the 18 values the manual says are 0* (24 bytes). It invents bits, and a Juno-106 tool would refuse or misread the patch, which DEC-6453 forbids.
- *Option C: the JU-06A's controller values alone*, all 24 that move a synth60 field: 72 bytes as messages, no longer a Juno-106 patch at all.
- *Option D: no synth60 patch of its own*; the three settings reachable only by live controllers, so a stored synth60 sound could not keep them.
- *Recommendation:* A.
- *Answered (DEC-6465):* A synth60 patch is the Juno-106's 18 values plus the three JU-06A controller values (option A).
- *Argued in:* section 12, S106-31 and section 17 question 1.

**20. The JU-06A's value bands are not in the filed chart.**
- *Option A:* look for a JU-06A owner's manual or parameter guide from Roland, file it, and replace S106-23, S106-24 and S106-26 with its figures.
- *Option B:* approve S106-23, S106-24 and S106-26 as NeoTeletext's own.
- *Recommendation:* A as a short search by the owner or the main session, then B if nothing is found. Only the bands and scalings would change; the controller numbers and their fields stand.
- *Answered (DEC-6465):* Search for and file a Roland JU-06A owner's manual or parameter guide that states its value bands (option A), begun at once; if none is found, the document's bands are approved as NeoTeletext's own (option B).
- *Argued in:* section 10 and section 17 question 2.

**21. Which performance controls should the instruments gain?**
The JU-06A recognises controls synth106 and synth60 lack: portamento time and switch (5, 65), expression (11), LFO wave (29), LFO trigger (30) and assignment mode (86).
- *Option A:* none now; they stay counted as ignored.
- *Option B:* add those the instruments modelled have: portamento on synth106; Poly 2 and solo unison on both through controller 86 (POLY as Poly 1, "(POLY)" as Poly 2, UNISON and SOLO as solo unison until SOLO's meaning is found); and the Juno-60's LFO trigger mode on synth60.
- *Option C:* B, and also expression as a second gain.
- *Recommendation:* A for this interface's first build, since each item of B is new instrument work; then B, recorded as its own to-do.
- *Answered (DEC-6465):* No new performance controls for synth106 and synth60 in the interface's first build (option A); the additions of option B become a to-do.
- *Argued in:* sections 9, 10 and 13 and section 17 question 3.

**22. Does a seventh key held steal a voice?**
The Juno-106 manual says "If 6 keys are simultaneously pressed, no more key will sound" (page 22); what is built gives a seventh key the voice of the first.
- *Option A:* the manual's rule, for both instruments (S106-34).
- *Option B:* keep what is built.
- *Recommendation:* A; it is the only statement in the source.
- *Answered (DEC-6465):* A seventh key held on synth106 or synth60 does not sound, as the Juno-106 manual states (option A).
- *Argued in:* section 13, S106-34 and section 17 question 4.

---

## synthD (`synthd.md`)

**23. The panel's controller numbers: look for a later edition of the Voyager manual, or approve NeoTeletext's own?**
The filed manual (software version 1.0, 2003) names controllers 1 and 7 only. DEC-6455 and `documents.tsv` describe it as holding a full map, which it does not.
- *Option A: look for a later edition and file it.* If it documents control changes for the panel, section 7's numbers, curves and bands, and the patch of SD-22, are replaced by it for every control the two panels share.
- *Option B: approve section 7 as NeoTeletext's own.* Complete and buildable now, but compatible with nothing outside NeoTeletext.
- *Option C: adopt another instrument's interface for the same panel* (the maker's reissues, which take MIDI for notes, pitch bend and modulation only); nothing of it is filed.
- *Recommendation:* A first, as a short search by the owner or the main session; B if no edition with a panel map can be filed.
- *Answered (DEC-6465):* Search for and file a later edition of the Voyager manual with a panel controller map (option A), begun at once; if none is found, synthd.md section 7 is approved as NeoTeletext's own (option B).
- *Argued in:* sections 6 and 7 and section 14 question 1.

**24. If a Voyager map is adopted, how are the controls only synthD has controlled?**
They are MODULATION MIX, the two modulation switches, WHITE / PINK, the two KEYBOARD CONTROL switches, the DECAY switch, LO on oscillators 1 and 2, and the six fixed waveforms. The question arises only if question 23 is answered A.
- *Option A: controllers of NeoTeletext's own*, from those the adopted map and MIDI 1.0 both leave unused, by the rules of SD-17.
- *Option B: non-registered parameter numbers*, four messages a change.
- *Option C: fold each onto the nearest Voyager control*, where meanings then differ, and MODULATION MIX and WHITE / PINK have nothing to fold onto.
- *Recommendation:* A for the controls with no counterpart (MODULATION MIX, the two modulation switches, WHITE / PINK); C only where the Voyager's control has the same purpose and the bands can be stated exactly, decided control by control once the map is in hand.
- *Answered (DEC-6465):* Only if question 23 finds a map: controllers of NeoTeletext's own for the controls only synthD has (option A), folding onto a Voyager control only where its purpose and bands are the same.
- *Argued in:* section 10 and section 14 question 2.

**25. Should reset all controllers turn synthD's GLIDE switch off?**
synthD's GLIDE switch is a parameter of its patch carried by controller 65, the controller MIDI 1.0 names the portamento switch (SD-17). MIDI-84 both resets the pedals on controllers 64 to 67 and leaves unchanged every parameter of the patch moved by a control change; for synthD's controller 65 the two disagree, and `midi-architecture.md` MIDI-84 now says so and points here. (synth7 meets the same clause differently: question 17.)
- *Option A (written, SD-13 item 3):* the GLIDE switch is a parameter of the patch and is left as it is.
- *Option B:* the GLIDE switch is turned off, as RP-015's portamento switch; the restatement (SD-28) then restates controller 65 after it.
- *Option C:* move the GLIDE switch to an undefined controller under MIDI-78 rule 5, breaking SD-17's rule of using the controller MIDI 1.0 names.
- *Recommendation:* A until RP-015 is filed and read; if its text resets controller 65 whatever it carries, B. The answer settles MIDI-84 for every family whose patch parameter sits on controllers 64 to 67.
- *Answered (DEC-6465):* Reset All Controllers leaves synthD's GLIDE switch (controller 65) as the patch set it (option A), revisited when RP-015 is filed.
- *Argued in:* SD-13 item 3 and section 14 question 4; `midi-architecture.md`, MIDI-84.

---

## synth53, synth52 and synth51 (`synth53-synth52-synth51.md`)

**26. A program's FILTER REV SELECT (parameter 20), when the kind already names the revision.**
The 2020 instrument has one set of oscillators and a switch for the filter and its envelope; NeoTeletext has three whole instruments, and DEC-6461 removed every model field.
- *Option A: the kind decides*; the parameter is kept, carried unchanged, and written to match the kind (S53-38).
- *Option B: the parameter switches the filter and filter envelope only*, as on the 2020 instrument, making two hybrid instruments no revision ever was, and letting a program carry a revision setting, which DEC-6461 item 3 ruled out.
- *Option C: the server refuses a program whose parameter disagrees with its kind*, so that a bank of mixed programs cannot be used at all.
- *Recommendation:* A.
- *Answered (DEC-6465):* A Prophet-5 program's filter revision parameter: the kind decides, the byte is carried and written to match the kind (option A).
- *Argued in:* section 15 question 1 and S53-38.

**27. The 2020 instrument's additions: which to build.**
Velocity to filter and amplifier (41, 42), aftertouch to filter and LFO amount (38, 39), Vintage (37), the LFO initial amount (22), the unison count, detune and key priority modes (53, 54, 87), half keyboard tracking, the per-program pitch wheel range (86), brightness (controller 74), polyphonic glide, and the chord memory (55 to 64).
- *Option A: build every one*; velocity, aftertouch and Vintage would need invented laws, and the chord memory has no stated meaning.
- *Option B: build none; carry all*, unchanged and silent.
- *Option C: build those whose meaning is stated and which reduce to the instrument modelled at their default* (initial amount, unison count, detune, key priority modes, half tracking, pitch wheel range, brightness), and carry the others unbuilt.
- *Recommendation:* C, which is what the document specifies.
- *Answered (DEC-6465):* Of the 2020 instrument's additions, build those whose meaning is stated and which reduce to the modelled instrument at their default (LFO initial amount, unison count, detune, key priority modes, half keyboard tracking, pitch wheel range, brightness), and carry the rest unbuilt (option C).
- *Argued in:* section 15 question 2 and section 10.

**28. The knob scale on synth52 and synth51.**
The 2020 instrument's knobs run 0 to 120; revision 3's converter reaches 120 at the dial's 10, revisions 1 and 2's reach 127.
- *Option A: scale 0 to 120 onto 0 to 127* (S53-36), so the same program reaches the same dial positions on every model.
- *Option B: take the value as the converter's number on every model*; the last 7 steps are unreachable on synth52 and synth51 and every knob stands about 5 per cent lower than on synth53.
- *Recommendation:* A.
- *Answered (DEC-6465):* On synth52 and synth51 the interface's knob range 0 to 120 is scaled onto 0 to 127 (option A).
- *Argued in:* section 15 question 3 and S53-36.

**29. A program's own pitch wheel range, against the rule that a program change does not change the range.**
The adopted interface makes the pitch wheel range a parameter of each program (parameter 86, User's Guide, page 37); MIDI-90 says a program change does not change the range. Related to question 5.
- *Option A (written): the architecture's rule.* A program change and an edit buffer dump leave the range; parameter 86 acts only when it arrives as controller 70 or as its parameter number message.
- *Option B: the adopted interface's rule.* Choosing a program sets its range, and registered parameter number 0 and controller 70 change it until the next program change; MIDI-90 gains an exception for an interface that stores the range in its patch.
- *Recommendation:* B, with MIDI-90 amended accordingly, since DEC-6453 asks that the interface be followed; until the owner rules, the document is written for A, as the architecture requires.
- *Answered (DEC-6465):* A program change does not change the pitch-bend range in any family, including synth53, synth52 and synth51, whose interface stores the range in each program (option A, the architecture's rule, which the document is written for). Chosen against the document's own recommendation (option B) because the owner requires one behaviour for all synthesizers in what MIDI defines in common, and bend range is one of those behaviours; parameter 86 still acts when it arrives as controller 70 or its parameter-number message.
- *Argued in:* section 15 question 5 and S53-8; `midi-architecture.md`, MIDI-90 and section 20 question 5.

**30. May the factory program banks be decoded in a test to confirm the readings?**
The readings of byte n as parameter n, the group sets, parameter 20's values, the unison count (S53-42) and the order of parameter 87's modes could be confirmed by unpacking the 400 factory programs.
- *Option A: yes, as a validation test whose data stays outside the repositories*, as DEC-6428 item 6 allows.
- *Option B: no*; the readings stand on the documents alone.
- *Recommendation:* A.
- *Answered (DEC-6465):* The Prophet-5 factory banks may be decoded in a validation test whose data stays outside the repositories (option A), as DEC-6428 item 6 allows.
- *Argued in:* section 15 question 4 and section 14.

---

## synth8 (`synth8.md`)

**31. Which product is "JUPITER-08", and do its controller numbers equal the JP-08 Boutique's?**
The filed chart says only "Model: JUPITER-08", "Date: October 1st, 2026", "Version: 1.01". Settling it means filing the rest of the reference manual the chart belongs to and Roland's chart and parameter list for the JP-08 Boutique (2015).
- *Option A:* file both and revise sections 7 and 9 to them before the interface is built.
- *Option B:* build to this document now, and revise if the filed documents later differ.
- *Recommendation:* A: the bands of six selectors and the meanings of controllers 41 and 57 depend on it, and changing bands after patches exist breaks them.
- *Answered (DEC-6465):* Search for and file the rest of the JUPITER-08 reference manual and Roland's JP-08 Boutique chart and parameter list, and revise synth8.md sections 7 and 9 to them before the interface is built (option A), begun at once.
- *What follows if nothing is found:* DEC-6465 does not say; its answers 32 and 33 keep `synth8.md`'s readings until question 31's documents say otherwise.
- *Argued in:* section 14 question 1.

**32. What do controllers 41 "BEND PITCH" and 57 "VCO-2 MODE" do?**
- *Option A (written):* 41 is the VCO bend depth (S8-14) and 57 is counted as ignored, until question 31's documents say.
- *Option B:* 41 is a pitch-bend range in semitones and 57 is VCO-2's NORMAL / LOW FREQ switch.
- *Recommendation:* A. Option B's 57 would give one switch two controllers (63 is "VCO-2 LO FREQ"), and the semitone reading of 41 is in no filed document; under either option registered parameter number 0 also sets the range (S8-31; question 5).
- *Answered (DEC-6465):* synth8's controller 41 is the VCO bend depth and controller 57 is ignored (option A), until question 31's documents say otherwise.
- *Argued in:* section 14 question 2 and S8-14.

**33. Should the five modulation sliders and VCA LFO MOD keep their inverted half?**
- *Option A (written):* each modulation slider is 0 (none) to 127 (most) in the instrument's direction; VCA LFO MOD is four bands; the inverted half is dropped.
- *Option B:* each is centred at 64, 0 to 63 being the inverted half, as the correspondence table's range suggests.
- *Recommendation:* A, or B if question 31's documents show the controllers are centred.
- *Answered (DEC-6465):* synth8's modulation sliders and VCA LFO MOD drop the inverted half (option A), unless question 31's documents show the controllers are centred.
- *Argued in:* section 14 question 3 and S8-21.

**34. Should the bender panel's other three depths (VCF bend, LFO VCO, LFO VCF) have controllers?**
- *Option A (written):* no controllers; the depths stay at their defaults (0, 50 cents and 0).
- *Option B:* three NeoTeletext controllers (for example 111, 112 and 113), listed as additions.
- *Recommendation:* A for now.
- *Answered (DEC-6465):* No controllers for synth8's other three bender depths now (option A).
- *Argued in:* section 14 question 4 and S8-14.

**35. Should a program change recall a patch preset?**
- *Option A (written):* no; a sender sends a program change on each channel, and the key mode stays in the OBJECT (tag 7).
- *Option B:* program changes 64 to 71 on channel 1 recall presets A to H, each two patch numbers and a key mode, changing the key mode mid-sound and needing it restated for a viewer who joins.
- *Recommendation:* A: a preset is "pairs of numbers referring to patches" (owner's manual, printed page 24), which two program changes already express.
- *Answered (DEC-6465):* A program change does not recall a synth8 patch preset (option A).
- *Argued in:* section 14 question 5 and section 11.

**36. Is 128 steps enough for a slider?**
- *Option A (written):* 128 steps, the chart's own form.
- *Option B:* NeoTeletext's own pairs or non-registered parameter numbers for 256 steps, which the chart does not have and DEC-6453 discourages.
- *Recommendation:* A.
- *Answered (DEC-6465):* 128 steps per synth8 slider (option A).
- *Argued in:* section 14 question 6 and S8-21.

**37. Should the hold hold only the lower half in the split key mode, as the instrument modelled does?**
The owner's manual says the hold pedal acts "on the Lower end of the keyboard only" in split (printed page 13); MIDI-87 holds every key in every synthesizer. (synth80 raises the same kind of choice between MIDI-87 and an instrument's pedal: question 42.)
- *Option A (written, S8-11):* the architecture's rule; the hold holds the whole keyboard in every key mode.
- *Option B:* the instrument's behaviour, as a departure the architecture would have to allow.
- *Recommendation:* A, under the owner's requirement of one behaviour (DEC-6464); B only if the owner counts the split hold as part of the instrument rather than of MIDI.
- *Answered (DEC-6465):* synth8's hold holds the whole keyboard in every key mode (option A), under the one-behaviour rule.
- *Argued in:* section 14 question 7 and S8-11.

---

## synth80 (`synth80.md`)

**38. Which end of a lever is value 0?**
The adopted table gives "0-127" and "0-64-127" and never says which end of a slider is 0. The two readings differ for the sub oscillator and touch response levers, resonance, detune, mix, brilliance, the four keyboard control levers, the feet and sub oscillator function selectors, and possibly glide mode.
- *Option A (written): value 0 is the end of least effect.* Every lever reads the same way, today's patches keep their values, and the manual's mod wheel destinations weakly support it.
- *Option B: value 0 is the bottom of the slider*, as the manual's DEBUG readout suggests; the controls listed invert and converted patches must have those bytes inverted.
- *Option C: find out*, from a Deckard's Dream owner or a fuller manual.
- *Recommendation:* A now; C if the owner can reach either, then sections 5.4 and 5.5 corrected in one change.
- *Answered (DEC-6465):* synth80: value 0 of a lever is its end of least effect (option A); corrected in one change if a Deckard's Dream owner or a fuller manual says otherwise.
- *Argued in:* sections 5.4 and 5.5 and section 16 question 1.

**39. The controller numbers of the twelve CS-80 controls Deckard's Dream lacks.**
- *Option A (written): controllers 20 to 31*, in patch order (S80-18).
- *Option B: the undefined controllers in ascending order* (3, 9, 14, 15, 20 to 27); controller 3 is now glide mode (S80-20), so this option would need another set.
- *Option C: non-registered parameter numbers*, four messages a change.
- *Option D: system exclusive under a NeoTeletext identifier*, which is not a control change and so not part of a patch.
- *Recommendation:* A.
- *Answered (DEC-6465):* synth80's twelve controls that Deckard's Dream lacks take controllers 20 to 31 in patch order (option A).
- *Argued in:* section 6.2 and section 16 question 2.

**40. Coarse and fine pitch (Deckard's Dream's controllers 93 and 94).**
- *Option A (written): leave them out*; the patch stays 85 values, and a Deckard's Dream stream's tuning moves are counted as ignored.
- *Option B: add them as two more patch values*, making the patch 87 values.
- *Option C: take them as performance controllers outside the patch*, like controller 7.
- *Recommendation:* C: it honours a stream's tuning without making a tuning knob part of every sound. The document was written for A until DEC-6465.
- *Answered (DEC-6465):* Deckard's Dream's coarse and fine pitch (controllers 93 and 94) are taken as performance controllers outside the patch (option C, the document's recommendation; the document was written for option A and is amended to option C); the patch stays 85 values.
- *Argued in:* section 12 and section 16 question 5.

**41. MPE.**
- *Option A (written): no MPE*; every channel is the one keyboard.
- *Option B: define MPE for synth80* by the MIDI Association's MPE specification, which is not filed (question 7).
- *Recommendation:* A until the specification is filed and the owner wants per-note bending; then B.
- *Answered (DEC-6465):* No MPE for synth80 (option A) until its specification is filed and the owner wants per-note bending.
- *Argued in:* S80-8 and section 16 question 6.

**42. Controller 64: MIDI's sustain pedal, or the CS-80's foot switch?**
MIDI-87 sets one sustain pedal for every synthesizer; synth80 today takes controller 64 as the CS-80's foot switch with its sustain assigner on, which never holds a note at full level. (synth8 raises the same kind of choice: question 37.)
- *Option A (written, S80-26): MIDI's sustain pedal*, with the SUSTAIN lever always in effect, as on the CS-80 with its assigner off.
- *Option B: the CS-80's foot switch, as built*, a departure needing MIDI-87 amended.
- *Recommendation:* A, under the owner's rule of one behaviour.
- *Answered (DEC-6465):* Controller 64 is MIDI's sustain pedal on synth80, with the SUSTAIN lever always in effect (option A), under the one-behaviour rule.
- *Argued in:* S80-26 and section 16 question 7.

---

## Questions answered during the reconciliation of 18 November 2026

These were raised as questions and are now answered; each document keeps the question with its answer as the record of the choice.

1. **File the maker's data-format document for the DX7's packed voice** (`synth7.md`, section 16 question 1). Answered by the filed TX7 manual (printed pages 35 to 44; the packed voice on page 44, section 4-8) and the DX7 II manual (Add-11); `synth7.md` section 10 was checked against them byte for byte and agrees.
2. **Take the DX7's 32-voice dump in a block as well as a bank** (`synth7.md`, section 16 question 2). Answered by `midi-architecture.md`, MIDI-28, MIDI-50, MIDI-51 and MIDI-58: it travels only as a bank.
3. **Controller 7 as synthD's panel VOLUME knob, or beside it** (`synthd.md`, section 14 question 3). Answered by `midi-architecture.md`, MIDI-82 and MIDI-92: a gain on the part's output, separate from the patch's volume, by one law, subject to the owner's approval of the architecture.
4. **Controller 120: Deckard's Dream's glide mode, or all sound off** (`synth80.md`, section 16 question 3). Answered by `midi-architecture.md`, MIDI-9 and MIDI-86: controller 120 is all sound off in every synthesizer, and synth80 takes glide mode on controller 3 (S80-20), subject to the owner's approval of the architecture.
