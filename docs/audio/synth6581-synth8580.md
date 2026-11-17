# synth6581 and synth8580: the programming interface

**Purpose.** This document specifies how a channel programs NeoTeletext's two sound-chip synthesizers, synth6581 and synth8580: the messages that set the chip's registers, the registers themselves, the time at which each message takes effect, and what a sender and a receiver must check. It is the basis for implementing the interface in the engine and the server, and the types the kits generate from the server's schema.

**Scope.** It covers the adopted interface (ASID, a protocol that carries register writes in MIDI system exclusive messages), every ASID command and what NeoTeletext does with it, the chip's 25 writable registers, the differences between the two synthesizers, the chip clock, time within a block, the bounds on a block, what a patch is for these synthesizers, loss and joining, and what a converter from existing music must produce. It does not specify how blocks are carried in records and packets, how a block's events are framed in general, or how the server and the kits name their calls: the architecture document (`midi-architecture.md`, which governs this document) and the server, TypeScript and Python documents of this set do that, and this document states only what these two synthesizers need from them. Where this document and `midi-architecture.md` speak of the same thing, they say the same; the requirements below cite the architecture's requirements (MIDI-n) they rest on.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

Which instruments synth6581 and synth8580 model is said once, in `synthesizers.md` in this folder, with the trademark statement.

---

## 1. Sources

Every fact about ASID in this document comes from the two filed files below. Where they do not say something, this document says "not stated in the source" and does not fill the gap from memory.

| Filed document | What it is | What it is used for here |
|---|---|---|
| `~/devel/teletext-reference/synthesizers/sid/protocols/thomasj-asid-protocol.md` (8,165 bytes, SHA-256 `3d358814313a61d23ffcd9f921a30da1c0b4a2f7ce2f30a7dc4e72bd526fe3b3`, from the GitHub repository thomasj/asid-protocol, fetched 18 November 2026; the repository states no licence) | The community specification of ASID: the original protocol (commands 0x4C, 0x4D, 0x4E and 0x4F) and the extended protocol (commands 0x50 to 0x5F, 0x60, 0x30, 0x31 and 0x32). It has no page numbers; it is cited here by its section headings. | The message framing, every command, every payload byte, the register mapping. |
| `~/devel/teletext-reference/synthesizers/sid/protocols/thomasj-asid-implementations.md` (3,342 bytes, SHA-256 `1d102a384226edcb04584611c8a691b0c303ea839b16151adc56c22e752da6de`, same repository and date) | The list of known receivers and senders of ASID, with the commands each supports. | Section 5, how widely each command is used, which is the evidence for which commands NeoTeletext takes. |
| `~/devel/teletext-reference/synthesizers/sid/documents.tsv` | The provenance row of each of the two files. | The sizes and checksums above. |

The chip's registers are described from NeoTeletext's own synthesizer, which is the thing a channel programs:

| Source | What it is used for here |
|---|---|
| The engine's module `crates/neoteletext-audio-instruments/src/synth6581/` in `neoteletext-renderer-teletext` (`mod.rs`, `oscillator.rs`, `envelope.rs`, `analogue.rs`, `decimator.rs`), read on 18 November 2026 | The 25 registers, their bit fields, what each does in our synthesizer, the two clocks, and how synth6581 and synth8580 differ. |
| The public documents that module cites where each constant is defined (the chip's data sheet as printed in appendix O of the "Commodore 64 Programmer's Reference Guide"; Andreas Varga's interview with the chip's designer; US patent 4,677,890; Asger Alstrup's examinations of the noise and triangle waveforms; Kevin Horton's and Plogue's envelope tables; "The C64 Digi" in C=Hacking 20; codebase64's articles; the oxyron.de register reference; the Commodore 64 schematic for assembly 250469; and the measurements of real chips the module names) | Cited here only through the module, as "module, citing …". These documents are not filed in `~/devel/teletext-reference/synthesizers/sid/`; the module carries their addresses. Section 9.3 lists filing them as work owed. |

Decisions this document follows (rdm): DEC-6453 (every instrument is programmed exactly as its most well-known existing interface does it), DEC-6460 (ASID is that interface for these two synthesizers), DEC-6461 (the names; each name its own kind), DEC-6410 (instruments are codecs of the audio profile; a block is 20 milliseconds of the instrument's input), DEC-6428 (clean-room rules; no GPL code), DEC-6462 (the Rust server is the one implementation of the synthesizers' programming interface: a program sends typed messages at the level of the adopted interface, and the server checks them, builds the blocks and repeats what a late joiner needs; the TypeScript and Python kits are thin clients with no instrument logic), and the architecture decisions A1 to A6 of the owner's brief of 18 November 2026, cited below as "decision A1" to "decision A6":

- **A1.** MIDI 1.0 is the one common layer.
- **A2.** An instrument sound stays a sequence of 20 millisecond blocks at 48,000 Hz (960 samples), carried in the existing OBJECT, DATA and CONTROL records.
- **A3.** A block's content is a Standard MIDI File track-event list: a delta time as a variable-length quantity, then an event, with system exclusive in the Standard MIDI File's `F0 <length> …` form. The tick is 0.1 millisecond.
- **A4.** Patches travel in the adopted interface's own form; for synth6581 and synth8580 that is an ASID register update.
- **A5.** Each of the eleven names is its own kind.
- **A6.** Nothing is invented where the adopted interface defines it; every omission and every item NeoTeletext defines itself is listed with its reason.

**The filed MIDI standards.** The MIDI 1.0 Detailed Specification 4.2 and Standard MIDI Files 1.0, in the MIDI Manufacturers Association's bundle of document version 96.1 (rdm SRC-6469), and the Recommended Practice RP-015, "Response to Reset All Controllers" (rdm SRC-6468), are filed in `~/devel/teletext-reference/midi/`; `midi-architecture.md`, section 1.5, describes them and the form of their citations, "MIDI 1.0 4.2, printed page n (PDF m)", the PDF page being that of the filed file. Every fact here that rests on one of them was read against the filed copy on 18 November 2026 and cites the place it rests on. RP-015 governs no requirement of this document, since these synthesizers take no channel messages (section 3.3, "Everything else"; S6581-26).

The architecture document this document follows is `midi-architecture.md` in this folder: the block's grammar and bounds (MIDI-23 to MIDI-38), the carrying of blocks in records (MIDI-39 to MIDI-49), the restatement of a live sound (MIDI-93 to MIDI-103), the codec numbers (MIDI-107 to MIDI-111, and its open question 1) and the program's interface to the server (MIDI-13 to MIDI-22).

"As built today" refers to `~/devel/teletext-reference/synthesizers/synthesizer-wire-format.html` and `programming-the-synthesizers.html` (both of 18 November 2026) and to the code they were read from.

---

## 2. Terms

- **The chip.** The thing synth6581 and synth8580 emulate: three voices, one filter, one volume control, set through 25 writable registers.
- **Register address.** A register's number on the chip, 0x00 to 0x18 for the writable ones.
- **ASID.** The protocol this document adopts: register writes carried in MIDI system exclusive messages whose first data byte is 0x2D.
- **ASID register ID.** ASID's own number for a register write, 0 to 27. It is not the register address: IDs 0 to 21 are the non-control registers in address order, IDs 22 to 24 are the three control registers, and IDs 25 to 27 are a second write to the same three control registers. Requirement S6581-11 has the whole table.
- **Register data message.** The ASID message with command 0x4E.
- **Register update.** The set of register writes one register data message carries.
- **Full register update.** A register data message that carries ASID register IDs 0 to 24, each once, and no other: all 25 registers.
- **Host** and **client.** The source's words for the sender of ASID messages (a player) and the receiver that makes the sound. In NeoTeletext the host is the channel's program, through the server; the client is the receiver in the viewer's browser.
- **Program**, **server** and **kit.** A channel's program writes typed messages to the server (neoteletext-app-server); the server checks them, builds the audio profile's blocks and records, and sends them to viewers. The TypeScript and Python kits are thin clients of the server: types generated from, or checked against, the server's schema, and the calls that send them, with no instrument logic (DEC-6462).
- **Frame.** The source's word for the interval at which a tune's player routine runs and sends one set of register writes, "for example the 50 Hz vertical blank".
- **Block.** 20 milliseconds of a sound: 960 samples at 48,000 Hz (decision A2).
- **Tick.** 0.1 millisecond, the unit of a delta time in a block (decision A3). A block is 200 ticks.
- **Event.** One entry of a block's track-event list: a delta time and a MIDI event.
- **MIDI form** and **block form.** An ASID message as it would travel on a MIDI cable (`F0 2D … F7`), and the same message as an event in a block (`F0 <length> 2D … F7`, after a delta time).
- **Passed over and counted.** What a receiver does with something it does not act on: it skips it, changes nothing, and adds one to a counter the port can read. This is the term the audio profile already uses.
- **PAL clock** and **NTSC clock.** The two frequencies the chip can run at, 985,248 Hz and 1,022,727 Hz (requirement S6581-39).
- **The family's codec.** The one codec of the audio profile that carries both synthesizers. Its code is 12 under `midi-architecture.md`, MIDI-107, if that document's open question 1 is answered as it recommends (new codes 12 to 19 for the synthesizers, codes 3 to 11 retired, MIDI-108); otherwise it is the present code, 3. DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation), so the code is 12; this document calls the code "the family's codec" throughout, and "codec 3" only when describing what is built today.
- **Stored sound** and **live sound.** A sound sent whole and played by a command, and a sound announced once and fed with blocks as it plays (the audio profile's terms).

Numbers written `0x…` are hexadecimal. Bits are numbered from 0, the least significant.

---

## 3. Requirements

### 3.1 Identity

**S6581-1.** synth6581 and synth8580 MUST be two kinds of sound a channel program can send, each with its stored sound, its live sound and its blocks message, and both MUST be carried by one codec of the audio profile, the family's codec (section 2: code 12 if `midi-architecture.md`'s open question 1 is answered as recommended, otherwise the present code 3; DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation), so it is 12). The kind alone MUST choose which of the two chips plays: a `synth6581` sound plays synth6581 and a `synth8580` sound plays synth8580, and no field of a program's message, and no message inside a block, may choose the other.
Reason: the owner ruled that each name is its own kind and that no `chip` or `model` field remains for a program to set; variants share their codec and code underneath. DEC-6461 item 3 also said the codec numbers would not change; the architecture document, because decisions A3 and A4 change every synthesizer's block and patch, recommends new codes instead and puts the choice to the owner as its open question 1, which this document follows and does not decide. DEC-6465 answered the architecture's open question 1 with new codes 12 to 19, codes 3 to 11 retired (awaiting the owner's confirmation).
Source: DEC-6461 items 3 and 5; decision A5; `midi-architecture.md`, MIDI-1, MIDI-48 (tag 3), MIDI-107 to MIDI-109 and open question 1.
Verification: a server test sends a sound of each kind and reads the OBJECT record's chip extension (requirement S6581-39): bit 0 is 0 for `synth6581` and 1 for `synth8580`. A test confirms that no message of the program protocol for these kinds accepts a `chip` or `model` field.

**S6581-2.** The registers of synth6581 and synth8580 MUST be set only by ASID register data messages (command 0x4E), as requirements S6581-10 to S6581-17 specify. NeoTeletext MUST NOT define any other message, record or field that writes a register.
Reason: ASID is the most widely used way to drive this chip remotely, and the owner's rule is that nothing is invented while an existing interface covers the need.
Source: DEC-6453 items 1 to 3; DEC-6460 ("The most standard way to drive a SID remotely is ASID"); decision A6.
Verification: inspection of the engine's receiver: the only caller of the chip's register write is the handler of command 0x4E. A receiver test feeds a block of every other event this document lists and asserts all 25 registers unchanged.

**S6581-3.** A sound of either kind MUST be a sequence of blocks of 20 milliseconds, rendered at 48,000 samples a second (960 samples a block), in one channel (mono). Each block's content MUST be a track-event list as the architecture document specifies under decision A3 (`midi-architecture.md`, MIDI-23 to MIDI-38: at most 1,005 bytes and at most 256 events a block, every system exclusive event 1 to 256 bytes after its 0xF0), holding only the events this document allows, within the lower bounds this document sets for this family (requirements S6581-42 and S6581-43).
Reason: the audio profile's carriage, storage, loss handling and control already work on 20 millisecond blocks; the chip has one audio output.
Source: decisions A2 and A3; DEC-6410 items 2 and 6; `midi-architecture.md`, MIDI-4, MIDI-23, MIDI-30 and MIDI-31.
Verification: the engine's existing test that a block of each instrument renders exactly 960 samples, extended to the new block content.

### 3.2 The ASID message

**S6581-4.** An ASID message in MIDI form MUST be exactly these bytes, in this order:

| Position | Byte | Meaning |
|---|---|---|
| 0 | 0xF0 | System exclusive start |
| 1 | 0x2D | The ASID identifier (decimal 45), a one-byte identifier in the place of a manufacturer identifier |
| 2 | command | The ASID command, one byte, 0x00 to 0x7F |
| 3 to 2 + n | payload | The command's payload, n bytes, where n is 0 or more and is fixed or bounded by the command |
| 3 + n | 0xF7 | System exclusive end |

There is no device number, no channel, no checksum and no length field in an ASID message: the end byte is the only terminator.
Reason: this is the adopted interface's framing, taken byte for byte.
Source: `thomasj-asid-protocol.md`, section "Original ASID protocol", the format table and the paragraph before it ("a one-byte identifier was used and the number chosen was 45").
Verification: an encoder test compares the bytes produced for each command against this table; a decoder test accepts exactly these and refuses a message with any byte between 0xF0 and 0x2D.

**S6581-5.** Every byte of an ASID message between the start byte 0xF0 and the end byte 0xF7 (the identifier, the command and every payload byte) MUST be in the range 0x00 to 0x7F. A receiver MUST treat a message that has a byte of 0x80 or above in those positions as malformed (requirement S6581-8).
Reason: MIDI data bytes carry seven bits; this is why ASID packs each register value's eighth bit separately.
Source: `thomasj-asid-protocol.md`, section "Original ASID protocol": "All MIDI data bytes are 7-bit values."; `midi-architecture.md`, MIDI-11 (the same rule for every message, a content error in a system exclusive message).
Verification: a decoder test with a byte of 0x80 in each position in turn; each message is passed over, counted as malformed, and writes no register.

**S6581-6.** In a block, an ASID message MUST be one event in block form:

| Bytes | Content |
|---|---|
| 1 or 2 | The delta time in ticks since the previous event of the block (or since the start of the block for the first event), as a variable-length quantity. A value of 0 to 127 is one byte; 128 to 199 is two bytes, 0x81 followed by the value less 128. |
| 1 | 0xF0 |
| 1 | The length, as a variable-length quantity: the count of bytes that follow it, which is 3 + n (the identifier 0x2D, the command, the n payload bytes, and the end byte 0xF7). This is the architecture's system exclusive length (`midi-architecture.md`, MIDI-27: every byte of the message after 0xF0, the last of them 0xF7), and it is within the architecture's bound of 1 to 256 (MIDI-28). For every message this document takes, the length is at most 39 and so is one byte. |
| 1 | 0x2D |
| 1 | The command |
| n | The payload |
| 1 | 0xF7 |

The whole message MUST be in one event of one block. A sender MUST NOT split an ASID message across two events (the Standard MIDI File's continuation form, an `0xF0` event not ending in 0xF7 followed by `0xF7` events (Standard MIDI Files 1.0, printed pages 6 and 7, PDF 135 and 136: "The F0 and F7 sysex events may be used together to break up syntactically complete system exclusive messages into timed packets"), which the architecture never writes, MIDI-50) or across two blocks, and a receiver MUST treat an ASID message that does not end with 0xF7 inside its event's stated length as malformed.
Reason: decision A3 gives the block's form; the longest ASID message NeoTeletext takes is 41 bytes in block form before its delta time (0xF0, a length of 39, and the 39 bytes it counts), far below a block's 1,005 bytes, so splitting is never needed, and forbidding it means a lost block can never leave half a message behind.
Source: decision A3; `midi-architecture.md`, MIDI-23 (the grammar), MIDI-24 (the variable-length quantities, one or two bytes, minimal), MIDI-27, MIDI-28 and MIDI-50; `thomasj-asid-protocol.md` for the message.
Verification: an encoder test checks the length byte against 3 + n for every command; a decoder test gives a message whose length runs past the end of the block, one whose last byte is not 0xF7, and one split into a continuation event, and each is passed over and counted as malformed.

**S6581-7.** A system exclusive event in a block of these synthesizers whose first byte after the length is not 0x2D is not an ASID message. A receiver MUST pass it over and count it, and MUST NOT write any register. The server MUST refuse a program's message that holds one.
Reason: the chip has no other system exclusive interface; refusing at the sender tells the author at once, and passing over at the receiver keeps an unexpected byte from stopping a sound.
Source: decision A6; the audio profile's existing rule for messages a codec does not take.
Verification: a server test that the message is refused with a message naming the event; a receiver test that the event is counted and the registers are unchanged.

**S6581-8.** A receiver MUST drop a malformed ASID message whole: it writes none of the message's registers, changes no state, counts the message as malformed, and goes on with the next event of the block. A message is malformed when it breaks requirement S6581-5, S6581-6 or S6581-14. A malformed ASID message whose event's extent is known is a content error in the architecture's terms (`midi-architecture.md`, MIDI-34) and is handled as this requirement says; a fault that leaves the receiver unable to find where the next event begins (a length that runs past the block's end, a variable-length quantity that is not minimal or is longer than two bytes, an event whose time reaches 200) is a framing error (MIDI-33): the receiver keeps every register write already applied, passes over the rest of the block, counts the block once as malformed, and renders the block's remaining samples from the registers as they stand.
Reason: all input is untrusted. A message applied in part would leave the chip in a state no sender intended; a message that stopped the block would let one bad byte silence a sound.
Source: DEVELOPMENT.md section 6 ("All input is untrusted"); the source does not state what a client does with a malformed message; `midi-architecture.md`, MIDI-33 and MIDI-34.
Verification: a fuzz target feeds arbitrary bytes as a block; the receiver never panics, never writes a register from a malformed message, and renders 960 samples for every block.

### 3.3 The commands

**S6581-9.** The ASID commands, and what NeoTeletext does with each, MUST be exactly as this table says. "Taken" means the receiver acts on it. "Accepted, no effect" means a sender may send it and the receiver passes it over without counting it as a fault. "Not taken" means the server refuses a program's message that holds it, and a receiver that meets it passes it over and counts it.

| Command | Name in the source | Payload | NeoTeletext | Requirement |
|---|---|---|---|---|
| 0x4C | Start playback | none | Accepted, no effect | S6581-18 |
| 0x4D | Stop playback | none | Accepted, no effect | S6581-18 |
| 0x4E | SID register data | 4 mask bytes, 4 most-significant-bit bytes, 0 to 28 data bytes | Taken | S6581-10 to S6581-17 |
| 0x4F | Display characters | 0 or more ASCII characters | Not taken | S6581-19 |
| 0x50 to 0x5F | Multi-SID register data, for the second to the seventeenth chip | as 0x4E | Not taken | S6581-20 |
| 0x60 | OPL-FM register data | a count, packed most significant bits, register and data pairs | Not taken | S6581-21 |
| 0x30 | SID write order and timing | 28 pairs of 2 bytes | Not taken | S6581-22 |
| 0x31 | Speed settings | 4 bytes | Not taken | S6581-23 |
| 0x32 | SID type information | 2 bytes | Not taken | S6581-24 |
| every other value, 0x00 to 0x7F | not defined by the source | not defined | Not taken | S6581-25 |

Reason: decision A6 requires every command of the adopted interface to be either taken or listed as left out with its reason. The reasons are in each command's requirement and in section 6.
Source: `thomasj-asid-protocol.md`, every section; `thomasj-asid-implementations.md` for which commands are widely used (section 5).
Verification: a receiver test sends one message of every command value from 0x00 to 0x7F: only 0x4E changes a register; 0x4C and 0x4D are not counted; every other value is counted once.

#### Command 0x4E: register data

**S6581-10.** The payload of command 0x4E MUST be, in this order:

| Payload bytes | Field | Content |
|---|---|---|
| 0 to 3 | mask bytes 1 to 4 | Which ASID register IDs are present in the message, one bit for each ID (requirement S6581-11). |
| 4 to 7 | most-significant-bit bytes 1 to 4 | Bit 7 of the value of each ID that is present, at the same bit positions as the mask (requirement S6581-12). |
| 8 to 7 + k | data bytes | Bits 6 to 0 of the value of each ID that is present, one byte for each, k bytes in all, where k is the number of bits set in the four mask bytes, from 0 to 28 (requirement S6581-13). |

In MIDI form the whole message is therefore 12 + k bytes (0xF0, 0x2D, 0x4E, 8 bytes, k bytes, 0xF7): 12 bytes with no register, 37 bytes for a full register update, 40 bytes at most. In block form the length byte is 11 + k, and the event is 13 + k bytes after its delta time.
Reason: the adopted interface's layout, taken byte for byte. The mask lets a message carry some or all registers, which is how the source says the protocol was "optimized for MIDI bandwidth limits".
Source: `thomasj-asid-protocol.md`, section "0x4E - SID register data", "Payload".
Verification: an encoder and decoder round-trip test over every one of the 2²⁸ masks is too many; the test covers the empty mask, each single ID, the full register update, all 28 IDs, and 10,000 masks drawn from a seeded generator, and compares each against a table-driven reference written from this requirement.

**S6581-11.** The mask's bits, the ASID register IDs and the chip's register addresses MUST correspond exactly as in this table. Bit b (0 to 6) of mask byte m (1 to 4) stands for ASID register ID 7 × (m − 1) + b. Bit 7 of every mask byte is 0 (requirement S6581-5).

| ASID register ID | Mask byte | Bit | Register address | Register (the source's name) | Voice or part |
|---|---|---|---|---|---|
| 0 | 1 | 0 | 0x00 | Voice 1 Freq Lo | voice 1 |
| 1 | 1 | 1 | 0x01 | Voice 1 Freq Hi | voice 1 |
| 2 | 1 | 2 | 0x02 | Voice 1 PW Lo | voice 1 |
| 3 | 1 | 3 | 0x03 | Voice 1 PW Hi | voice 1 |
| 4 | 1 | 4 | 0x05 | Voice 1 Env AD | voice 1 |
| 5 | 1 | 5 | 0x06 | Voice 1 Env SR | voice 1 |
| 6 | 1 | 6 | 0x07 | Voice 2 Freq Lo | voice 2 |
| 7 | 2 | 0 | 0x08 | Voice 2 Freq Hi | voice 2 |
| 8 | 2 | 1 | 0x09 | Voice 2 PW Lo | voice 2 |
| 9 | 2 | 2 | 0x0A | Voice 2 PW Hi | voice 2 |
| 10 | 2 | 3 | 0x0C | Voice 2 Env AD | voice 2 |
| 11 | 2 | 4 | 0x0D | Voice 2 Env SR | voice 2 |
| 12 | 2 | 5 | 0x0E | Voice 3 Freq Lo | voice 3 |
| 13 | 2 | 6 | 0x0F | Voice 3 Freq Hi | voice 3 |
| 14 | 3 | 0 | 0x10 | Voice 3 PW Lo | voice 3 |
| 15 | 3 | 1 | 0x11 | Voice 3 PW Hi | voice 3 |
| 16 | 3 | 2 | 0x13 | Voice 3 Env AD | voice 3 |
| 17 | 3 | 3 | 0x14 | Voice 3 Env SR | voice 3 |
| 18 | 3 | 4 | 0x15 | Filter Cutoff Lo | filter |
| 19 | 3 | 5 | 0x16 | Filter Cutoff Hi | filter |
| 20 | 3 | 6 | 0x17 | Filter Reso & Enable | filter |
| 21 | 4 | 0 | 0x18 | Filter Mode / Volume | filter and volume |
| 22 | 4 | 1 | 0x04 | Voice 1 Control | voice 1 |
| 23 | 4 | 2 | 0x0B | Voice 2 Control | voice 2 |
| 24 | 4 | 3 | 0x12 | Voice 3 Control | voice 3 |
| 25 | 4 | 4 | 0x04 | Voice 1 Control (second write) | voice 1 |
| 26 | 4 | 5 | 0x0B | Voice 2 Control (second write) | voice 2 |
| 27 | 4 | 6 | 0x12 | Voice 3 Control (second write) | voice 3 |

All 28 IDs are valid; there is no reserved bit among the 28. The mask bytes of a full register update are 0x7F, 0x7F, 0x7F, 0x0F.

The source states which IDs each mask byte covers ("The first mask byte (bits 6-0) covers registers 0-6, the second covers 7-13, and so on") and that there is "one bit per ID". It does not state in so many words that, within a byte, bit 0 is the lowest ID of the byte. That reading (bit 0 the lowest ID, rising) is the one this requirement takes, and it MUST be confirmed against a message captured from an existing ASID host before the requirement is marked implemented.
Reason: the adopted interface's mapping, taken exactly, so that an ASID stream made by any existing host sets the same registers in NeoTeletext.
Source: `thomasj-asid-protocol.md`, section "0x4E - SID register data", "Payload" (the mask_bytes row) and "ASID to SID register mapping" (all 28 rows).
Verification: a table-driven test with one message for each of the 28 IDs asserts the register address written. A recorded test vector: one frame of an ASID stream captured as MIDI bytes from an existing host program run as a separate program (DEC-6428 step 4), whose register values are known from the tune, decoded and compared.

**S6581-12.** The four most-significant-bit bytes MUST use the same positions as the mask bytes: bit b of most-significant-bit byte m is bit 7 of the value of ASID register ID 7 × (m − 1) + b. The value written to the register is that bit times 128, plus the ID's data byte. A sender MUST write 0 in the bit of every ID that is not present in the mask, and in bit 7 of each of the four bytes. A receiver MUST ignore the bit of an ID that is not present, without counting a fault.
Reason: a register holds eight bits and a MIDI data byte seven; the source packs the eighth bits "similar to" the mask. What a set bit means for an absent ID is not stated in the source, so a sender writes 0 and a receiver does not depend on it.
Source: `thomasj-asid-protocol.md`, section "0x4E - SID register data", "Payload" (the msb_bytes row). The handling of the bit of an absent ID is NeoTeletext's (section 7).
Verification: a test writes 0x00, 0x7F, 0x80 and 0xFF to each of the 28 IDs in turn and reads back the register's effect; a test with a most-significant bit set for an absent ID asserts no register changes and no fault is counted.

**S6581-13.** The data bytes MUST follow the eight mask and most-significant-bit bytes in ascending order of ASID register ID: the first data byte belongs to the lowest ID whose mask bit is set, the next to the next lowest, to the highest. Each data byte is bits 6 to 0 of its register's value. There is no data byte for an ID whose mask bit is clear.
Reason: the source says the data is the "lowest 7 bits of the data for each register, as indicated by mask_bytes", and names 0, 1, 2, 3 to 27 as "the regular ASID write order".
Source: `thomasj-asid-protocol.md`, section "0x4E - SID register data", "Payload" (the register_data row), and section "0x30 — SID Write Order & Timing", "Notes" ("Example order: 0, 1, 2, 3 ... 27 corresponds to the regular ASID write order").
Verification: the tests of requirements S6581-10 and S6581-11.

**S6581-14.** The count of data bytes in a register data message MUST equal the count of bits set in its four mask bytes. A receiver MUST treat a message with fewer or more data bytes as malformed (requirement S6581-8), and a message whose payload is shorter than the 8 mask and most-significant-bit bytes as malformed. The server MUST refuse a program's message that holds one.
Reason: the count is the only check a register data message offers; without it a truncated message would write the wrong values to the wrong registers.
Source: follows from `thomasj-asid-protocol.md`, section "0x4E - SID register data"; the source does not state what a client does on a mismatch, and dropping the message whole is NeoTeletext's (section 7).
Verification: decoder tests with one data byte missing and one extra for each of five masks, and with payloads of 0 to 7 bytes; each is counted as malformed and no register changes.

**S6581-15.** A receiver MUST apply the writes of one register data message in ascending order of ASID register ID, all at the instant of the message's event (requirement S6581-40), with no chip time passing between one write and the next. It follows that:

1. the non-control registers of all three voices and the filter (IDs 0 to 21) are written before any control register;
2. the three control registers (IDs 22, 23 and 24: addresses 0x04, 0x0B and 0x12) are written next;
3. the second writes to the control registers (IDs 25, 26 and 27: the same three addresses) are written last.

When a message carries both writes to a control register, the receiver MUST perform both, the first and then the second, each as a real write to the chip: a gate bit that differs between the two starts or releases the envelope, and a test bit set in either resets the oscillator, exactly as two writes made one after the other by a program on the original machine would. A second write MAY be present without the first.
Reason: the order is the source's "regular ASID write order". The second write exists so that one frame can, for example, clear a voice's gate or set its test bit and then start the note. The source does not state how much time a client leaves between writes; NeoTeletext leaves none, and a sender that needs time between two writes puts them in two messages at different ticks (section 7, item 3).
Source: `thomasj-asid-protocol.md`, section "0x4E - SID register data", "Purpose" ("There is also room for an extra write for the control registers") and the mapping table; section "0x30", "Notes", for the order. The module's `Synth6581::write` for what a control write does (`oscillator.rs` `write_control`, `envelope.rs` `set_gate`).
Verification: a test sends one message with ID 22 holding a control value with the gate clear and ID 25 holding one with the gate set, to a voice whose envelope is sustaining, and asserts the envelope begins a new attack; a test with the two values exchanged asserts a release; a test that IDs 0 and 1 (frequency) take effect before ID 22's gate in the same message.

**S6581-16.** A register data message whose four mask bytes are all zero is valid. A receiver MUST accept it, write nothing, and not count a fault. A sender SHOULD NOT send one.
Reason: the layout allows it, and refusing it would make a receiver stricter than the adopted interface.
Source: follows from `thomasj-asid-protocol.md`, section "0x4E - SID register data" ("it can be chosen to update some or all of the available registers"); the empty case is not mentioned in the source.
Verification: a decoder test.

**S6581-17.** Any value from 0x00 to 0xFF MUST be valid for every one of the 28 ASID register IDs. Neither the server, a kit nor the receiver may refuse a register data message because of a register's value.
Reason: the chip accepts any byte in any register, and tunes use bits and combinations the data sheet calls unused or warns against (several waveforms at once, the test bit).
Source: the module's documentation, `mod.rs` ("Any byte in any register is valid, nothing here panics or allocates"); `synthesizer-wire-format.html`, section 08, "A SID image" ("Every byte value is valid").
Verification: the engine's existing test that every byte in every register renders without a panic, run through the ASID decoder.

Two worked examples, in MIDI form and in block form at tick 0:

- Voice 1's frequency set to 0x1D45 and its control register to 0x41 (IDs 0, 1 and 22; mask byte 1 is 0x03, mask byte 4 is 0x02; no value has bit 7 set). MIDI form, 15 bytes: `F0 2D 4E 03 00 00 02 00 00 00 00 45 1D 41 F7`. Block form, 17 bytes: `00 F0 0E 2D 4E 03 00 00 02 00 00 00 00 45 1D 41 F7`.
- Voice 1's sustain and release register set to 0xA4 (ID 5; mask byte 1 is 0x20; the value's bit 7 is set, so most-significant-bit byte 1 is 0x20 and the data byte is 0x24). MIDI form, 13 bytes: `F0 2D 4E 20 00 00 00 20 00 00 00 24 F7`. Block form, 15 bytes: `00 F0 0C 2D 4E 20 00 00 00 20 00 00 00 24 F7`.

#### Commands 0x4C and 0x4D: start and stop playback

**S6581-18.** Command 0x4C (start playback) and command 0x4D (stop playback) each have an empty payload: the message is `F0 2D 4C F7` or `F0 2D 4D F7` in MIDI form, 4 bytes, and `F0 03 2D 4C F7` or `F0 03 2D 4D F7` after its delta time in block form. A sender MAY put either in a block. A receiver MUST accept either, MUST NOT change any register or any other state because of it, and MUST NOT count it as a fault. A message of either command with a payload of one byte or more is malformed.
Reason: the source says only that each "signal[s] that playback is starting" or "stopping" and that the message "is not mandatory"; it defines no effect on the chip, so giving one would be an invention. In NeoTeletext a sound starts and stops by the audio profile's CONTROL record, and the chip is reset when a sound starts (requirement S6581-36). They are accepted so that a stream captured from an existing host can be carried unchanged. A sender that wants silence writes the registers that make it.
Source: `thomasj-asid-protocol.md`, sections "0x4C — Start playback" and "0x4D — Stop playback". `thomasj-asid-implementations.md`: four of the six listed receivers act on them, and one of the seven listed senders sends them in full.
Verification: a receiver test that a sounding chip's output is sample-for-sample the same with and without each message in the block.

#### Command 0x4F: display characters

**S6581-19.** Command 0x4F has a payload of zero or more ASCII characters, ended only by the message's end byte. The source's notes say the end byte serves as the terminator and that, for compatibility with the original receiver, an implementation may assume a display of two rows of sixteen characters that clears when the command is received. NeoTeletext does not take it: the server MUST refuse a program's message that holds it, and a receiver MUST pass it over and count it.
Reason: a NeoTeletext sound has no display; the teletext page is the display, and a channel writes text there. A sound that could put text on the screen would be a second, unchecked path to the page.
Source: `thomasj-asid-protocol.md`, section "0x4F - Display characters".
Verification: the test of requirement S6581-9.

#### Commands 0x50 to 0x5F: register data for further chips

**S6581-20.** Commands 0x50 to 0x5F each carry register data for one further chip, with a payload in exactly the form of command 0x4E (requirements S6581-10 to S6581-14). The source names 0x50 as the second chip's register data, 0x51 as the third's, 0x52 as the fourth's, and 0x5F as the seventeenth's; the commands between follow in order, so command 0x50 + i is the register data of chip i + 2, for i from 0 to 15. Command 0x4E is the first chip's. NeoTeletext does not take commands 0x50 to 0x5F: a sound of these kinds has exactly one chip. The server MUST refuse a program's message that holds one (a kit holds no copy of this rule, DEC-6462 item 3), and a receiver MUST pass each over and count it.
Reason: one sound is one chip today (DEC-6410 item 10 counts a tab's four audio channels as "at most … 12 SID voices", one chip of three voices to a sound), a tab's four audio channels already allow four chips as four sounds, and a second chip inside one sound raises a question the kinds cannot answer (a tune for one chip of each kind would belong to neither). The source notes that these commands typically need more bandwidth than a MIDI cable gives; three of the six listed receivers and one of the seven listed senders support them. Whether to add them is open question 2.
Source: `thomasj-asid-protocol.md`, section "Multi-SID Register Data"; `thomasj-asid-implementations.md`.
Verification: the test of requirement S6581-9.

#### Command 0x60: OPL-FM register data

**S6581-21.** Command 0x60 carries register writes to a frequency-modulation chip of another family. Its payload, as the source gives it:

| Field | Size | Content |
|---|---|---|
| num_pairs | 1 byte | The number of address and data pairs, at most 16 |
| msb_bytes | "variable"; the exact count is not stated in the source | The packed most significant bits of the pairs' bytes, "see command 0x4E for reference" |
| pairs | num_pairs × 2 bytes | For each pair, the register and then the data |

NeoTeletext does not take it: the server MUST refuse a program's message that holds it, and a receiver MUST pass it over and count it, skipping it by its event's length without reading its payload.
Reason: NeoTeletext has no synthesizer of that chip; the message is not for the chip these kinds play.
Source: `thomasj-asid-protocol.md`, section "0x60 — OPL-FM Register Data".
Verification: the test of requirement S6581-9.

#### Command 0x30: write order and timing

**S6581-22.** Command 0x30 tells a client the order in which to write the registers of each later register data message, and how long to wait after each write. Its payload is 28 pairs of two bytes, 56 bytes, "one pair per ASID register":

| Byte of a pair | Bits | Meaning |
|---|---|---|
| data0 | 0 to 5 | A register index: an ASID register ID, 0 to 27 ("Indices refer to ASID register IDs, not SID registers") |
| data0 | 6 | Bit 7 of wait_cycles |
| data0 | 7 | 0, as in every MIDI data byte (requirement S6581-5); the source's table does not list this bit |
| data1 | 0 to 6 | Bits 0 to 6 of wait_cycles |
| data1 | 7 | 0, as in every MIDI data byte; not listed in the source's table |

wait_cycles, 0 to 255, is the "delay before next register write", in cycles of the original machine's processor, about one microsecond each. The source gives the order 0, 1, 2, 3 to 27 as the one that "corresponds to the regular ASID write order". The source does not state whether the pair at position p names the register written p-th, or gives the place in the order of ASID register ID p; for the regular order the two readings give the same bytes.

NeoTeletext does not take it: the server MUST refuse a program's message that holds it, and a receiver MUST pass it over and count it. A sender that needs registers written in another order, or with time between writes, MUST send several register data messages, each at its own tick (requirement S6581-40).
Reason: a block's delta times already place every message in time, to 0.1 millisecond, without any state in the receiver. Command 0x30 is a setting that every later message depends on: a viewer who joins a live sound after it was sent, or who loses the block that carried it, would play every later frame differently from the sender's intent, which the audio profile's rules for loss and joining exist to prevent. Two of the six listed receivers and one of the seven listed senders support it. What is given up is resolution: 0.1 millisecond is about 98.5 chip cycles on the PAL clock and 102.3 on the NTSC clock, where the command counts single cycles. Whether to take it is open question 3.
Source: `thomasj-asid-protocol.md`, section "0x30 — SID Write Order & Timing"; `thomasj-asid-implementations.md`.
Verification: the test of requirement S6581-9; a test that two register data messages at the same tick are applied in the order they stand in the block.

#### Command 0x31: speed settings

**S6581-23.** Command 0x31 tells a client the playback timing of the tune. Its payload is 4 bytes:

| Byte | Bits | Meaning |
|---|---|---|
| data0 | 0 | The system: 0 is PAL, 1 is NTSC |
| data0 | 1 to 4 | The speed multiplier, "1× – 16×". How the sixteen values of the four bits stand for 1 to 16 is not stated in the source. |
| data0 | 5 | Reserved, 0 |
| data0 | 6 | Buffering requested |
| data0 | 7 | Reserved (and 0 in any MIDI data byte) |
| data1 | 0 to 6 | Frame delta, bits 0 to 6 |
| data2 | 0 to 6 | Frame delta, bits 7 to 13 |
| data3 | 0 to 1 | Frame delta, bits 14 to 15 |
| data3 | 2 to 6 | Reserved |

The frame delta is a 16-bit value in microseconds, at most 65,535 microseconds (about 15 frames a second). The source says to use the speed multiplier when "no advanced timing system exists" and when the frame delta is 0.

NeoTeletext does not take it: the server MUST refuse a program's message that holds it, and a receiver MUST pass it over and count it. The clock of a sound is chosen as requirement S6581-39 says, and the time of every register update is given by its event's delta time.
Reason: everything the command says is already said elsewhere, in a place a late joiner always has: the system (PAL or NTSC) in the sound's OBJECT record, and the frame interval and speed in the delta times themselves, which a receiver follows exactly and need not be told in advance. The command exists so that a client receiving messages with no times "can adapt its playback, for instance to implement a buffered output"; NeoTeletext's receiver always buffers whole blocks. Two of the six listed receivers and one of the seven listed senders support it. Whether the clock should instead come from this message is open question 4.
Source: `thomasj-asid-protocol.md`, section "0x31 — Speed Settings"; `thomasj-asid-implementations.md`.
Verification: the test of requirement S6581-9.

#### Command 0x32: chip type information

**S6581-24.** Command 0x32 tells a client which chip a tune is written for. Its payload is 2 bytes:

| Byte | Bits | Meaning |
|---|---|---|
| data0 | all | The chip index: 0 is the first chip, 1 the second. The source's table gives these two rows and then an ellipsis; the highest index is not stated in the source. |
| data1 | 0 | The chip type: 0 is the 6581, 1 is the 8580 |
| data1 | 1 to 6 | Reserved for variants; when they are zero, bit 0 alone defines the type |
| data1 | 7 | Reserved |

NeoTeletext does not take it: the server MUST refuse a program's message that holds it, and a receiver MUST pass it over and count it. The chip is chosen by the sound's kind (requirement S6581-1).
Reason: the owner ruled that each name is its own kind and that nothing inside a sound chooses the variant (DEC-6461 item 3). A message that could change the chip in the middle of a sound would also be a setting a late joiner lacks. Two of the six listed receivers and one of the seven listed senders support it. A converter uses the information this message carries to choose the kind (requirement S6581-58).
Source: `thomasj-asid-protocol.md`, section "0x32 — SID Type Information"; `thomasj-asid-implementations.md`; DEC-6461.
Verification: the test of requirement S6581-9; a test that a `synth6581` sound containing the message with bit 0 set still plays synth6581.

#### Everything else

**S6581-25.** An ASID message whose command is none of 0x30, 0x31, 0x32, 0x4C, 0x4D, 0x4E, 0x4F, 0x50 to 0x5F and 0x60 is not defined by the source. The server MUST refuse a program's message that holds it, and a receiver MUST pass it over and count it, skipping it by its event's length.
Reason: the source says future expansion may add chip types; a receiver that skips what it does not know keeps playing a stream made for a later version.
Source: `thomasj-asid-protocol.md`, section "0x32", "Notes" ("Future expansion may include FM or additional chip types").
Verification: the test of requirement S6581-9.

**S6581-26.** A block of these synthesizers MUST hold only system exclusive events that are ASID messages. Every other MIDI event (note off, note on, polyphonic key pressure, control change, program change, channel pressure, pitch bend, and every system common and system real-time message) and every Standard MIDI File meta event has no meaning for these synthesizers: the server MUST refuse a program's message that holds one, and a receiver MUST pass it over and count it.

It follows that the architecture's common layer (`midi-architecture.md`, MIDI-9) and its common MIDI behaviours (section 11.1, MIDI-84 to MIDI-92: reset all controllers by RP-015 under DEC-6464, which is recorded as proposed and awaits the owner's confirmation; all notes off, controller 123; all sound off, controller 120; the sustain pedal's threshold of 64; a note on of velocity 0 as a note off; the mode messages 124 to 127 as all notes off only; pitch bend range by registered parameter number 0; 14-bit pitch bend; one volume law for controller 7) do not apply to synth6581 and synth8580, as the architecture itself says (section 11.1, and MIDI-9, "every family but the synth6581 family"): every one of those behaviours is carried by a channel message, and these synthesizers take none. This is not a departure from section 11.1: there is no channel message here for the rule to govern. A program silences these synthesizers by writing the registers that make silence (requirement S6581-34), and a lost block is handled as requirement S6581-48 says, not as MIDI-102 says for the families that play notes.
Reason: ASID defines no note, controller or program message, and the chip has no notion of a note: a tune plays it by writing registers. Decision A1 gives each synthesizer "the standard MIDI messages its adopted interface defines", and ASID defines only system exclusive. Whether NeoTeletext should add a note-playing layer of its own is open question 1, with the recommendation that it should not (requirement S6581-52).
Source: `thomasj-asid-protocol.md` (the whole document defines only system exclusive messages); decision A1; DEC-6453 item 3; `midi-architecture.md`, MIDI-9, MIDI-10, MIDI-67 and section 11.1; DEC-6464.
Verification: a server test that each of the listed events is refused, naming the block and the event; a receiver test that each is counted and no register changes.

### 3.4 The registers

The registers are described as our synthesizer's: what a value written through ASID does in synth6581 and synth8580. Everything in this section is the same for the two unless requirement S6581-38 says otherwise.

**S6581-27.** The chip MUST have exactly 25 writable registers, at addresses 0x00 to 0x18: seven for each of three voices, then four for the filter and volume. Their addresses, the ASID register IDs that write them, and their contents:

| Address | Decimal | ASID register ID | Register | Bits used | Requirement |
|---|---|---|---|---|---|
| 0x00 | 0 | 0 | Voice 1 frequency, low byte | 7 to 0 | S6581-28 |
| 0x01 | 1 | 1 | Voice 1 frequency, high byte | 7 to 0 | S6581-28 |
| 0x02 | 2 | 2 | Voice 1 pulse width, low byte | 7 to 0 | S6581-29 |
| 0x03 | 3 | 3 | Voice 1 pulse width, high bits | 3 to 0 | S6581-29 |
| 0x04 | 4 | 22, and 25 for a second write | Voice 1 control | 7 to 0 | S6581-30 |
| 0x05 | 5 | 4 | Voice 1 attack and decay | 7 to 0 | S6581-31 |
| 0x06 | 6 | 5 | Voice 1 sustain and release | 7 to 0 | S6581-31 |
| 0x07 | 7 | 6 | Voice 2 frequency, low byte | 7 to 0 | S6581-28 |
| 0x08 | 8 | 7 | Voice 2 frequency, high byte | 7 to 0 | S6581-28 |
| 0x09 | 9 | 8 | Voice 2 pulse width, low byte | 7 to 0 | S6581-29 |
| 0x0A | 10 | 9 | Voice 2 pulse width, high bits | 3 to 0 | S6581-29 |
| 0x0B | 11 | 23, and 26 for a second write | Voice 2 control | 7 to 0 | S6581-30 |
| 0x0C | 12 | 10 | Voice 2 attack and decay | 7 to 0 | S6581-31 |
| 0x0D | 13 | 11 | Voice 2 sustain and release | 7 to 0 | S6581-31 |
| 0x0E | 14 | 12 | Voice 3 frequency, low byte | 7 to 0 | S6581-28 |
| 0x0F | 15 | 13 | Voice 3 frequency, high byte | 7 to 0 | S6581-28 |
| 0x10 | 16 | 14 | Voice 3 pulse width, low byte | 7 to 0 | S6581-29 |
| 0x11 | 17 | 15 | Voice 3 pulse width, high bits | 3 to 0 | S6581-29 |
| 0x12 | 18 | 24, and 27 for a second write | Voice 3 control | 7 to 0 | S6581-30 |
| 0x13 | 19 | 16 | Voice 3 attack and decay | 7 to 0 | S6581-31 |
| 0x14 | 20 | 17 | Voice 3 sustain and release | 7 to 0 | S6581-31 |
| 0x15 | 21 | 18 | Filter cutoff, low bits | 2 to 0 | S6581-32 |
| 0x16 | 22 | 19 | Filter cutoff, high byte | 7 to 0 | S6581-32 |
| 0x17 | 23 | 20 | Filter resonance and routing | 7 to 0 (bit 3 has no effect) | S6581-33 |
| 0x18 | 24 | 21 | Filter mode and volume | 7 to 0 | S6581-34 |

Reason: these are the registers the synthesizer has, and the ASID mapping reaches each of them and no other.
Source: the module, `mod.rs` (`REGISTERS`, `VOICE_REGISTERS`, `FILTER_REGISTERS`, `Synth6581::write`), citing the data sheet's Table 1; `thomasj-asid-protocol.md`, "ASID to SID register mapping".
Verification: a test asserts that the 28 ASID register IDs map onto exactly the addresses 0x00 to 0x18, each address reached by at least one ID, the three control addresses by two, and no ID reaching an address above 0x18. It is held as a compile-time or test-time assertion between the decoder's table and the module's `REGISTERS`.

**S6581-28.** The two frequency registers of a voice MUST form one 16-bit number F, the high byte's eight bits above the low byte's. The voice's oscillator is a 24-bit accumulator to which F is added on every cycle of the chip clock, so the voice's pitch in hertz is F × clock ÷ 16,777,216. On the PAL clock (985,248 Hz) one step of F is 0.058725 Hz and the highest pitch, F = 65,535, is 3,848.6 Hz; on the NTSC clock (1,022,727 Hz) one step is 0.060959 Hz and the highest pitch is 3,995.0 Hz. The same value of F therefore sounds higher on the NTSC clock than on the PAL clock, by the ratio of the clocks. A value of 0 stops the oscillator where it is. Writing either byte takes effect at once and does not reset the oscillator.
Reason: this is what the chip does, and it is why a sound must name its clock (requirement S6581-39).
Source: the module, `oscillator.rs` (`ACCUMULATOR_BITS`, `write_frequency_low`, `write_frequency_high`, `advance`), citing the data sheet, registers 0 and 1 ("Fout = (Fn * Fclk / 16777216) Hz"), and the designer's interview.
Verification: the engine's existing pitch test, run through ASID: for F = 7,493 on the PAL clock and F = 7,218 on the NTSC clock (each the nearest value to 440 Hz) the rendered sawtooth's measured frequency is within 0.1 Hz of F × clock ÷ 16,777,216.

**S6581-29.** The two pulse width registers of a voice MUST form one 12-bit number W, 0 to 4,095: the low byte's eight bits, and above them bits 3 to 0 of the high register. Bits 7 to 4 of the high register have no effect and any value in them is valid. W sets the share of each period for which the pulse waveform is at one of its two levels: the pulse waveform is at its high value while the upper twelve bits of the oscillator's accumulator are at or above W, so the output's duty is W ÷ 40.95 per cent in the data sheet's terms, W = 2,048 is a square wave, and W = 0 is a constant level. W has no effect on a voice whose control register does not select the pulse waveform.
Reason: this is what the chip does.
Source: the module, `oscillator.rs` (`write_pulse_low`, `write_pulse_high`, `pulse`), citing the data sheet, registers 2 and 3 ("PWout = (PWn/40.95) %"), and the recordings of two real chips it names for which share of the period is high.
Verification: a test renders the pulse waveform at W = 1,024, 2,048 and 3,072 and measures the duty of the output; a test that the upper four bits of the high register change nothing.

**S6581-30.** The control register of a voice MUST have these eight bits:

| Bit | Value | Name | What it does |
|---|---|---|---|
| 0 | 0x01 | Gate | When it changes from 0 to 1, the voice's envelope begins its attack from the level it has reached. When it changes from 1 to 0, the envelope begins its release. Writing the same value again does nothing. |
| 1 | 0x02 | Synchronise | While it is 1, the voice's oscillator is set back to zero each time the top bit of another voice's oscillator rises: voice 1 follows voice 3, voice 2 follows voice 1, voice 3 follows voice 2. |
| 2 | 0x04 | Ring modulation | While it is 1 and the triangle waveform is selected, the triangle is inverted by the top bit of the same other voice's oscillator (voice 1 by voice 3, voice 2 by voice 1, voice 3 by voice 2), which gives the ring-modulated combination of the two. It has no effect on the other waveforms. |
| 3 | 0x08 | Test | While it is 1, the oscillator is held at zero and the pulse waveform is held at its high value. If it is held for 32,768 chip cycles (about 33 milliseconds) the noise generator is reset to its starting value. Clearing it lets the oscillator run again from zero. |
| 4 | 0x10 | Triangle | Selects the triangle waveform. |
| 5 | 0x20 | Sawtooth | Selects the sawtooth waveform. |
| 6 | 0x40 | Pulse | Selects the pulse waveform, whose width is requirement S6581-29's W. |
| 7 | 0x80 | Noise | Selects the noise waveform, a 23-bit pseudo-random generator stepped by the oscillator, so that the frequency registers set its colour. |

With no waveform bit set, the voice's waveform output keeps its last value and falls slowly to zero (one unit of 4,095 every 512 chip cycles, about 2.1 seconds from the top). With more than one of the triangle, sawtooth and pulse bits set, the waveforms are combined bit by bit (a logical AND on synth8580; on synth6581 the AND with further bits pulled low, requirement S6581-38). With the noise bit set together with any other waveform bit, the combination is the AND and the zeros it produces are written back into the noise generator, which drains to zero and stays silent until the test bit resets it.

Any of the 256 values is valid.
Reason: this is what the chip does; tunes rely on every one of these behaviours, including the ones the data sheet warns against.
Source: the module, `oscillator.rs` (the `control` constants, `write_control`, `advance`, `synchronise`, `triangle`, `pulse`, `waveform`, `floating`, `combined`, `NOISE_RESET_CYCLES`, `FLOATING_FALL_CYCLES`) and `mod.rs` (`cycle`, for which voice follows which), citing the data sheet's register 4, the designer's interview, Alstrup's examination of the noise waveform and codebase64.
Verification: the engine's existing tests of each bit (`tests/synth6581_voices.rs`, `tests/synth6581_chip.rs`), each run through an ASID message that sets the bit by ID 22, 23 or 24.

**S6581-31.** The attack and decay register and the sustain and release register of a voice MUST hold four 4-bit numbers:

| Register | Bits | Field | Range | Meaning |
|---|---|---|---|---|
| Attack and decay | 7 to 4 | Attack | 0 to 15 | The rate at which the envelope rises from its present level to the peak, 255, after the gate is set |
| Attack and decay | 3 to 0 | Decay | 0 to 15 | The rate at which it then falls from the peak to the sustain level |
| Sustain and release | 7 to 4 | Sustain | 0 to 15 | The level held while the gate stays set: the field times 17, so 0 is silence and 15 is the peak, 255 |
| Sustain and release | 3 to 0 | Release | 0 to 15 | The rate at which the envelope falls to zero after the gate is cleared |

The envelope is an 8-bit counter, 0 to 255, that multiplies the voice's waveform. A rate field selects the number of chip cycles between steps of the counter:

| Field value | Chip cycles a step | Attack, 0 to 255, on the PAL clock | Attack, 0 to 255, on the NTSC clock |
|---|---|---|---|
| 0 | 9 | 2.3 ms | 2.2 ms |
| 1 | 32 | 8.3 ms | 8.0 ms |
| 2 | 63 | 16.3 ms | 15.7 ms |
| 3 | 95 | 24.6 ms | 23.7 ms |
| 4 | 149 | 38.6 ms | 37.2 ms |
| 5 | 220 | 56.9 ms | 54.9 ms |
| 6 | 267 | 69.1 ms | 66.6 ms |
| 7 | 313 | 81.0 ms | 78.0 ms |
| 8 | 392 | 101.5 ms | 97.7 ms |
| 9 | 977 | 252.9 ms | 243.6 ms |
| 10 | 1,954 | 505.7 ms | 487.2 ms |
| 11 | 3,126 | 809.1 ms | 779.4 ms |
| 12 | 3,907 | 1,011.2 ms | 974.1 ms |
| 13 | 11,720 | 3,033.3 ms | 2,922.2 ms |
| 14 | 19,532 | 5,055.2 ms | 4,870.0 ms |
| 15 | 31,251 | 8,088.3 ms | 7,791.9 ms |

The attack rises one unit a step. Decay and release fall one unit after 1 step while the level is above 93, after 2 steps from 93, after 4 from 54, after 8 from 26, after 16 from 14 and after 30 from 6, which makes the fall close to exponential and about three times as long as the attack at the same field value. The envelope stops at zero until the next gate. Because the step timer is a counter that is compared with the selected value, a rate written while the timer is already past the new value takes effect only after the timer has run all the way round, a delay of up to 32,767 chip cycles (about 33 milliseconds); this is the behaviour players work around with a "hard restart", and the synthesizer reproduces it.

Any of the 256 values is valid in either register.
Reason: this is what the chip does. The delay matters to anyone writing or converting a tune: a note started in the frame after its envelope registers were changed may start late on the real chip and equally in ours.
Source: the module, `envelope.rs` (`RATE_PERIODS`, `RATE_STATES`, `EXPONENTIAL_STEPS`, `SUSTAIN_STEP`, `write_attack_decay`, `write_sustain_release`, `set_gate`), citing Kevin Horton's reading of the chip's die, Plogue's recording of a chip's release, US patent 4,677,890, codebase64 and the data sheet's register 6 and Table 2. The times in the table are 255 steps times the cycles a step, divided by the clock.
Verification: the engine's existing test `periods_are_the_die_table`, and a test through ASID that measures the attack time of each of the 16 field values on both clocks against the table to within one block.

**S6581-32.** The two cutoff registers MUST form one 11-bit number C, 0 to 2,047: bits 2 to 0 of the low register, and above them the high register's eight bits. Bits 7 to 3 of the low register have no effect and any value in them is valid. C sets the filter's cutoff frequency, by a curve that differs between synth6581 and synth8580 (requirement S6581-38). The cutoff has an effect only on voices routed through the filter (requirement S6581-33).
Reason: this is what the chip does.
Source: the module, `analogue.rs` (`CUTOFF_MAX`, `write_cutoff_low`, `write_cutoff_high`), citing the data sheet, registers 0x15 and 0x16 ("an 11-bit number").
Verification: the engine's existing filter tests (`tests/synth6581_filter.rs`), run through ASID IDs 18 and 19; a test that bits 7 to 3 of the low register change nothing.

**S6581-33.** The resonance and routing register MUST have these fields:

| Bits | Field | Meaning |
|---|---|---|
| 7 to 4 | Resonance | 0 to 15: how strongly the filter emphasises frequencies at its cutoff, from none (0) to the most (15) |
| 3 | External input routing | No effect: the chip's external audio input is not modelled. Any value is valid. |
| 2 | Filter voice 3 | 1 sends voice 3 through the filter; 0 sends it past the filter, straight to the mixer |
| 1 | Filter voice 2 | The same for voice 2 |
| 0 | Filter voice 1 | The same for voice 1 |

Reason: this is what the chip does; the external input is left out because nothing in NeoTeletext could feed it.
Source: the module, `analogue.rs` (`write_resonance_routing`, `filters`) and `mod.rs` (`route`, and "The external audio input … [is] not modelled"), citing the data sheet, register 0x17.
Verification: the module's test `voices_are_routed_by_the_filter_registers`, run through ASID ID 20; a test that bit 3 changes nothing.

**S6581-34.** The mode and volume register MUST have these fields:

| Bits | Value | Field | Meaning |
|---|---|---|---|
| 7 | 0x80 | Voice 3 off | 1 removes voice 3 from the output when voice 3 is not routed through the filter. A voice 3 that is routed through the filter is not removed. Voice 3's oscillator still runs, so it can still synchronise and ring-modulate voice 1. |
| 6 | 0x40 | High-pass | 1 adds the filter's high-pass output to the mix |
| 5 | 0x20 | Band-pass | 1 adds the filter's band-pass output to the mix |
| 4 | 0x10 | Low-pass | 1 adds the filter's low-pass output to the mix |
| 3 to 0 | 0x0F | Volume | 0 to 15: the output level of the whole chip, in sixteen equal steps; 0 is silence |

Any combination of the three filter outputs may be selected; with none selected, voices routed through the filter are not heard. Because each voice adds a constant level to the mixer even when silent (much more on synth6581 than on synth8580), changing the volume makes a step in the output, and tunes play sampled sound by writing this register quickly; requirement S6581-38 gives the size of that step for each synthesizer.

A chip in which every register is zero, as at the start of a sound, is silent: nothing is heard until the volume and a voice have been written.
Reason: this is what the chip does.
Source: the module, `analogue.rs` (the `mode` constants, `write_mode_volume`, `voice_3_off`, `process`) and `mod.rs` (`route`, `Synth6581::new`), citing the data sheet, register 0x18, and "The C64 Digi".
Verification: the module's routing test; a test that each of the 16 volumes scales a steady voice in equal steps; a test that a chip with all registers zero renders silence.

**S6581-35.** A receiver MUST ignore the bits this document says have no effect (bits 7 to 4 of each pulse width high register, bits 7 to 3 of the cutoff low register, bit 3 of the resonance and routing register) without counting a fault, and a sender MAY write any value in them.
Reason: streams made by existing hosts carry whatever the tune wrote; a value is not a fault because part of it is unused.
Source: requirement S6581-17 and the module's write functions, which mask these bits.
Verification: the tests of requirements S6581-29, S6581-32 and S6581-33.

**S6581-36.** When a sound of either kind starts to play, the receiver MUST make a new chip in its reset state: all 25 registers zero, every oscillator at zero, every envelope at zero and released, the noise generators at their starting value, the filter at rest. No register value carries over from any earlier sound.
Reason: a sound must play the same every time it is played and for every viewer, whatever was heard before it.
Source: DEC-6410 item 7 ("the chip is reset when a sound starts"); the module, `Synth6581::new` and `reset`.
Verification: a receiver test plays sound A and then sound B on one audio channel, and sound B alone on another receiver, and asserts the samples of B are identical.

**S6581-37.** The chip's four read-only addresses (0x19 and 0x1A, the two potentiometer inputs; 0x1B, the upper eight bits of voice 3's waveform; 0x1C, voice 3's envelope) are not writable, have no ASID register ID, and MUST NOT be reachable by any message. NeoTeletext has no message that reads a register, and a receiver sends nothing back to a sender.
Reason: ASID is one-way, from host to client, and defines no read; a tune that depends on reading voice 3 does that reading inside its own player, on the machine that makes the ASID stream, not in the receiver. The potentiometer inputs are not modelled.
Source: `thomasj-asid-protocol.md` (the mapping table has no row for these addresses, and no command returns data); the module, `mod.rs` (`OSCILLATOR_3`, `ENVELOPE_3`, `read`, and "the two potentiometer registers … are not modelled").
Verification: the test of requirement S6581-27, which asserts no ID reaches an address above 0x18.

### 3.5 The two synthesizers and the clock

**S6581-38.** synth6581 and synth8580 MUST take exactly the same messages, have exactly the same 25 registers with the same bit fields, and have the same oscillators, sawtooth, triangle, pulse and noise waveforms, ring modulation, synchronisation, test bit and envelopes. They MUST differ only in these ways, which a channel hears and cannot set:

| What | synth6581 | synth8580 |
|---|---|---|
| Filter cutoff against the 11-bit number C | A bent curve: a floor of 400 Hz at the bottom of the register; a bend upwards between C = 320 and C = 904; a straight rise of 23 Hz a step above the bend; a slacker rise of 16 Hz a step above C = 1,056; a top of 16,000 Hz. It is the middle of seven measured chips, which differ widely. | A straight line: 30 Hz at C = 0, rising 7.25 Hz a step, to about 14.9 kHz at C = 2,047. |
| Resonance | Little. At the highest setting the peak is about 1.6 dB (a Q of 1.2) while C is at or below 0x100, rising to about 8 dB (a Q of 2.5) when C is at or above 0x500. Between settings 0 and 15 the damping falls in equal steps. | More at low cutoffs. At the highest setting the peak is about 8 dB (a Q of 2.5) at every cutoff. Between settings 0 and 15 the damping falls in equal ratios. |
| Distortion in the filter | The filter's input saturates: one voice at full level passes unchanged, and three together are bent. | None: the filter is clean. |
| High-pass output | Mixed 3 dB below the low-pass and band-pass outputs. | Mixed at the same level as the others. |
| Combined waveforms (more than one of triangle, sawtooth and pulse selected) | The bit-by-bit AND, with further bits pulled low by their low neighbours, so the combinations are quieter and the top bit of sawtooth with triangle never rises. | The plain bit-by-bit AND. |
| The constant level each voice adds | Large: a quarter of a voice's full swing for each voice, and a further 0.08 of a swing from the mixer; the waveform swings about a point 0.61 of the way up its range. Changing the volume from 0 to 15 with the chip silent makes a step 0.82 times the span of a triangle at full volume, so sampled sound played through the volume register is loud. | Small: a twentieth of a voice's full swing for each voice, and nothing from the mixer; the waveform swings about its middle. The same step is 0.15 times the span of a triangle, so sampled sound played through the volume register is quiet. |
| Loudness | The reference: one sawtooth at full volume, past the filter, at the level every NeoTeletext instrument is set to. | 2.3 dB quieter for the same registers. |

Reason: these are the differences between the two chips the synthesizers model that a listener hears. They are properties of the synthesizer, not of the interface, and so nothing in a message sets them.
Source: the module, `analogue.rs` (`curve_6581`, `CUTOFF_FLOOR_8580_HZ`, `CUTOFF_SLOPE_8580`, `DAMPING_HIGHEST_6581`, `RESONANCE_RISE_6581`, `DAMPING_RATIO_8580`, `HIGH_PASS_GAIN_6581`, `SATURATION_START`, `WAVEFORM_ZERO_6581`, `VOICE_OFFSET_6581`, `MIXER_OFFSET_6581_MILLIVOLTS`, `WAVEFORM_ZERO_8580`, `VOICE_OFFSET_8580`, `output_gain`), `oscillator.rs` (`combined`, `pull_reach_6581`) and `mod.rs` (`Variant`), each citing its own measurement or document where it is defined.
Verification: the engine's existing tests of each figure (`the_6581_curve_is_the_middle_chips`, `the_highest_resonance_is_the_one_fitted`, `tests/synth6581_filter.rs`, `tests/levels.rs`); a test that the same block played as each kind gives different samples when it uses the filter or a combined waveform, and that a block of one plain sawtooth past the filter differs only in level.

**S6581-39.** A sound of either kind MUST name the clock its chip runs at, one of two:

| Clock | Frequency | How it is derived |
|---|---|---|
| PAL | 985,248 Hz | A crystal of 17,734,475 Hz divided by 18 |
| NTSC | 1,022,727 Hz | A crystal of 14,318,182 Hz divided by 14 |

The clock sets the pitch a frequency register gives (requirement S6581-28), the length of every envelope stage (requirement S6581-31) and every other time inside the chip. It MUST be carried where it is carried today, in the sound's OBJECT record, extension tag 3, one byte: bit 0 is the chip (0 for synth6581, 1 for synth8580, written by the server from the kind and never by a program), bit 1 is the clock (0 for PAL, 1 for NTSC), and bits 2 to 7 are 0. A sound without the tag plays synth6581 on the PAL clock. A program states the clock as a required field of a stored sound and of a live sound, `clock`, whose values are `pal` and `ntsc`; the server refuses a message without it, as it does today, and no kit supplies a default (DEC-6462 item 3). The clock MUST NOT change while a sound plays, and nothing inside a block may change it.

The clock does not change the time of a block or of a tick: a block is 20 milliseconds and a tick 0.1 millisecond on either clock. The receiver runs the chip for exactly the clock's number of cycles for each second it renders: 19,704.96 cycles a block on the PAL clock and 20,454.54 on the NTSC clock, with the fraction carried from block to block so that no time is gained or lost.
Reason: the same registers play at a different pitch and speed on the two clocks, so a tune must be played on the clock it was written for. The OBJECT record reaches every receiver before any block of the sound, including one that joins a live sound late, which a message inside a block would not.
Source: the module, `mod.rs` (`PAL_CRYSTAL`, `NTSC_CRYSTAL`, `ChipClock::hz`, `Synth6581::cycles`), citing the oxyron.de register reference and the Commodore 64 schematic; the engine's `crates/neoteletext-audio/src/record.rs` (`TAG_SYNTH6581_CHIP`, `SYNTH6581_CHIP_8580`, `SYNTH6581_CLOCK_NTSC`); DEC-6410 item 8; DEC-6461 item 3.
Verification: the module's test `the_clocks_are_the_crystals_divided`; a receiver test that the same block gives a pitch higher by the ratio 1,022,727 ÷ 985,248 on the NTSC clock; a record test that a tag with any of bits 2 to 7 set is refused.

### 3.6 Time

ASID itself carries no time: in the source, a host sends "a set of SID register write requests" at each frame and the client applies each message when it arrives. In NeoTeletext every message stands in a block with a delta time, so the time ASID leaves to the moment of arrival is stated exactly.

**S6581-40.** Each event of a block has a time within the block, in ticks of 0.1 millisecond: the sum of its own delta time and the delta times of the events before it in the block. The time MUST be from 0 to 199. A receiver MUST apply a register data message immediately before it renders the sample numbered ⌊time × 24 ÷ 5⌋ of the block's 960 (24 ÷ 5 being 4.8 samples a tick), after rendering every earlier sample of the block. Events with the same time MUST be applied in the order they stand in the block. An event whose time would be 200 or more is malformed: the server MUST NOT write one (it places each event in the block its time falls in, requirement S6581-53), and a receiver MUST pass it and every later event of that block over and count them. These are the architecture's rules for every event codec, stated here for this family (`midi-architecture.md`, MIDI-5, MIDI-25 and MIDI-35).
Reason: decision A3 sets the tick; the sample formula is the one the engine already uses for timed events, so that a register update lands on the same sample in every receiver. The chip is rendered a sample at a time, so a write takes effect at a sample boundary: about 20.5 chip cycles apart on the PAL clock and 21.3 on the NTSC clock.
Source: decision A3; `midi-architecture.md`, MIDI-5, MIDI-25 and MIDI-35; `synthesizer-wire-format.html`, section 08 ("sample = time × 24 ÷ 5"); the module, `Synth6581::render`.
Verification: a receiver test places one register data message that sets the volume at each tick from 0 to 199 in turn and asserts the first changed sample is ⌊time × 24 ÷ 5⌋; a test of two messages at one tick writing the same register asserts the later one in the block wins.

**S6581-41.** Whatever computes the times of a tune's register updates (a channel's program, or a converter, section 3.11) MUST, for a tune with a frame interval of P microseconds and N register updates a frame, give update number k (counted from 0 at the start of the sound) the time k × P ÷ N microseconds from the start of the sound, stated in whole microseconds as the architecture requires (`midi-architecture.md`, MIDI-17): the whole number nearest to k × P ÷ N, a value exactly half way rounded up, which in integers is ⌊(2 × k × P + N) ÷ (2 × N)⌋. The server then places the update at the absolute tick ⌊(time + 50) ÷ 100⌋, the nearest tick with a half rounded up, in block ⌊tick ÷ 200⌋ at the time tick mod 200 within it (MIDI-17; requirement S6581-53). Each update's time MUST be computed from k, never by adding a rounded interval to the previous update's time, so that the error of any update against k × P ÷ N is at most half a microsecond before the server's rounding and at most 50.5 microseconds after it, and never accumulates. It follows that:

- a tune with a 20,000 microsecond frame (50 frames a second, the source's example) and one update a frame has exactly one update in every block, at the same time in each;
- the same tune at speed 2 has two updates a block, at ticks 0 and 100; at speed 4, four, at ticks 0, 50, 100 and 150; at speed 16, sixteen, 12.5 ticks apart before rounding, at ticks 0, 13, 25, 38, 50, 63, 75, 88, 100, 113, 125, 138, 150, 163, 175 and 188;
- a tune whose frame is not a whole number of ticks, or not a divisor of 20 milliseconds, has a number of updates that varies from block to block (for a frame a little shorter than 20 milliseconds, usually one and now and then two), and a block with no update is valid;
- the longest frame command 0x31 can state, 65,535 microseconds, is one update in about every 3.28 blocks.

This is how ASID's frame rate, speed multiplier and frame delta (command 0x31) relate to NeoTeletext's blocks and ticks: the sender uses them to compute times, and the times, not the settings, are what travels.
Reason: a tune keeps its tempo only if the time between its player's calls is kept on average exactly; rounding each interval separately would make a tune drift against the page and against other sounds.
Source: `thomasj-asid-protocol.md`, section "Original ASID protocol" ("At each frame (for example the 50 Hz vertical blank), a set of SID register write requests is transmitted") and section "0x31 — Speed Settings" (frame delta in microseconds, speed multiplier 1 to 16); decision A3; `midi-architecture.md`, MIDI-17 (time in whole microseconds, rounded once to the tick by the server) and MIDI-36.
Verification: a test of the converter (and of any example program that computes times this way) builds 10 minutes of updates for frame intervals of 20,000, 16,667 and 19,950 microseconds at speeds 1, 2, 4 and 16, sends them through the server, and asserts that every update's absolute tick is within 50.5 microseconds of k × P ÷ N and that the last update's error is no larger than the first's; the server's own test of MIDI-17 covers its rounding.

**S6581-42.** A block of these synthesizers MUST hold at most 20 register data messages (this family's lower bound on a block's events, which the architecture's MIDI-31 allows a family to set beneath its 256), at most one start message (command 0x4C) and at most one stop message (command 0x4D). The server MUST refuse a program's message that would place more than these in one block (more than 20 register updates whose times fall within the same block's 200 ticks, or a second start or stop message there), naming the block and the count; a receiver MUST apply the first 20 register data messages of a block and pass over and count the rest, and pass over and count every start or stop message after the first of its command in a block.
Reason: a bound on a block's messages is a bound on the receiver's work and on the block's size (requirement S6581-43); start and stop messages have no effect (requirement S6581-18), so one of each is all a stream captured from an existing host needs. Twenty is one update a millisecond: it carries the highest speed command 0x31 names, 16 updates a frame, at the 50-frames-a-second example of the source (16 a block), with room for a frame up to a quarter faster. As built today a block holds at most 4 register images (200 a second); the source says a MIDI cable limits ASID to "approximately 75 Hz", so every stream made for a cable fits many times over. The figure is open question 5.
Source: `thomasj-asid-protocol.md`, section "0x31 — Speed Settings" (the multiplier's range) and section "Extended ASID protocol", "Notes" (the 75 Hz limit); DEVELOPMENT.md section 6 ("Bound every allocation and every length"); `midi-architecture.md`, MIDI-31.
Verification: a server test with 21 register updates in one block's ticks, and one with two start messages there; a receiver test that the 21st register data message changes no register and is counted, and that a second start message is counted.

**S6581-43.** A block of these synthesizers needs at most 874 bytes: 20 register data messages of all 28 ASID register IDs (each 2 bytes of delta time at most, and 41 bytes of event: 0xF0, the length, 0x2D, 0x4E, 8 mask and most-significant-bit bytes, 28 data bytes, 0xF7), which is 860 bytes, and one start and one stop message (each 2 bytes of delta time at most and 5 bytes of event), which is 14 bytes. This is this family's bound on a block's bytes, within the architecture's bound of 1,005 bytes for every event codec (`midi-architecture.md`, MIDI-30), so a block of these synthesizers always fits one DATA record of the architecture's layout for the event codecs (MIDI-42), with its two-byte length before it. The server MUST refuse a program's message that would make a block of more than 874 bytes, and a receiver needs no check of its own on this figure: a block of this family's codec longer than 874 bytes necessarily holds more messages than S6581-42 allows or events this family does not take (since the 20 largest register data messages and one start and one stop message, each with the longest delta time, are 874 bytes), and those are passed over and counted as requirements S6581-7, S6581-26 and S6581-42 say, within the architecture's bound of 1,005 bytes, which the receiver enforces on every block (MIDI-30, MIDI-121). No ASID message NeoTeletext takes is longer than 40 bytes in MIDI form, 39 bytes after its 0xF0 in block form (within the architecture's 1 to 256, MIDI-28), so these synthesizers have no need for the architecture's means of carrying a system exclusive message longer than an event, which exists only for bank dumps travelling as banks (MIDI-50 and MIDI-51); this family has no bank (requirement S6581-51).
Reason: decision A4 asks each family document to state what its instrument needs in sizes and counts.
Source: requirements S6581-6, S6581-10, S6581-18 and S6581-42; `midi-architecture.md`, MIDI-28, MIDI-30, MIDI-31, MIDI-42, MIDI-50 and MIDI-51.
Verification: an encoder test builds the largest block this requirement describes and asserts its length is 874 bytes and that it is accepted and written in one DATA record.

**S6581-44.** The work a receiver does for one block MUST be bounded whatever the block holds: at most 20 register data messages, each at most 28 register writes, so at most 560 register writes a block, each a fixed amount of work; and the rendering of 960 samples, whose cost for each sample is fixed whatever the registers hold. Passing an event over MUST cost no more than reading its length.
Reason: every input is untrusted; a sound must not be able to make a viewer's browser stall.
Source: the module's documentation, `mod.rs` ("a sample costs the same bounded work whatever the registers hold"); DEVELOPMENT.md sections 6 and 14.
Verification: a timed test renders the worst block of requirement S6581-43, with register values chosen by the fuzzing corpus's slowest input, and holds its time to a stated budget, printing the number.

### 3.7 State, loss and joining

A register data message may carry only some registers, so a sound's blocks depend on the blocks before them. As built today every block restates all 25 registers, so no block depends on another; the requirements of this section restore what that gave.

**S6581-45.** The first event of the first block of a stored sound of either kind MUST be a full register update at tick 0. The server MUST refuse a stored sound whose program's message does not begin with one; it MUST NOT supply one itself, because only the author knows the registers the sound begins with. This is the choice the architecture leaves to a family document (`midi-architecture.md`, MIDI-99: the program's own first events are the stored sound's restatement, in place of one the server writes), and the full register update is this family's restatement (MIDI-93).
Reason: a stored sound then says everything about the chip's registers itself; and when a sound loops, the full register update at its start sets every register again at the join.
Source: DEC-6410 item 7 ("Every image is complete, so a receiver needs no earlier block"), kept for the first block; `midi-architecture.md`, MIDI-93 and MIDI-99.
Verification: a server test that a stored sound whose first event is a partial update, or a full register update at tick 1, is refused with a message saying why.

**S6581-46.** The blocks of a live sound of either kind MUST carry this family's restatement, a full register update holding the value each of the 25 registers has at that instant (`midi-architecture.md`, MIDI-93), at the interval the architecture sets for every live sound (MIDI-96): in the first block of the sound, at least once in every 50 blocks (1,000 milliseconds) after, and, where the blocks have room, every 25 blocks (500 milliseconds). The server MUST do this itself: it keeps the value of each of the 25 registers as it places a live sound's register updates in blocks (MIDI-94), and writes a full register update of those values at a block's tick ahead of any update of the program's at that tick (MIDI-35 and MIDI-95), carrying the registers as they stand after every update of earlier ticks. The full register update counts as one of the block's 20 register data messages (requirement S6581-42); where a block already holds 20 of the program's register data messages, the server MUST put the restatement in the next block with room, and if 50 blocks pass without room the server MUST refuse the program's message that filled them, naming the blocks and saying they leave no room to restate (MIDI-98). A program need not restate, and the first register update a program sends for a live sound MUST be a full register update (the server refuses a live sound whose first update is partial, since it would not know the registers the update leaves out).
Reason: a viewer may join a live sound part-way, and a block may be lost; with partial updates either would leave a register wrong for as long as the tune did not write it again. The interval is the architecture's, one for every synthesizer, and its bound of one second is the interval the audio profile already uses for restating a live instrument's settings. The server does it because it is the one implementation of the interface and the place that "repeats what a viewer who joins late needs" (DEC-6462 item 1); a kit holds no such logic (DEC-6462 item 3). Earlier drafts of this document placed the restatement at tick 0 whenever 50 blocks would otherwise pass without one; it now follows MIDI-96 and MIDI-98, which govern.
Source: `midi-architecture.md`, MIDI-93 to MIDI-98 and its open question 2; DEC-6410 item 12 (for synth7, "A sender of a live DX7 sound repeats each part's program change at least once a second"); DEC-6462 items 1 and 3; `programming-the-synthesizers.html`, section 07 (joining a live sound part-way).
Verification: a server test feeds a live sound an hour of partial updates and asserts no 50 consecutive blocks lack a full register update and that, where blocks have room, one comes every 25 blocks; a server test fills 50 consecutive blocks with 20 register data messages each and asserts the refusal; a receiver test that joins at each block of a 3 second live sound and asserts its registers equal the sender's within 50 blocks.

**S6581-47.** A full register update that writes to every register the value it already holds MUST make no change to the synthesizer's output: the samples rendered MUST be identical with and without it.
Reason: requirement S6581-46 inserts such updates into a tune; they must be inaudible when nothing was lost. It is this family's case of the architecture's MIDI-97.
Source: the module's write functions: a gate written with the value it has makes no envelope transition (`envelope.rs`, `set_gate`), a test bit written set while already set leaves the oscillator held and does not restart the noise reset's count (`oscillator.rs`, `write_control`), and every other register write stores a value.
Verification: a test plays each tune of the engine's test set twice, once with a full register update of the current values inserted at a seeded random tick of every block, and asserts the two outputs are identical sample for sample.

**S6581-48.** When a block of a sound is missing (a live sound's block that has not arrived by the time it is due, as the audio profile defines), the receiver MUST render that block's 20 milliseconds with the chip's registers as they stand and no writes: voices that were sounding go on sounding. It MUST NOT reset the chip, clear a gate or change the volume. This is what the architecture's MIDI-102 requires of this family ("for the synth6581 family: nothing, the registers sound on"); the release of notes MIDI-102 requires of the other families does not apply, since these synthesizers have no notes.
Reason: this is the behaviour as built, and for this chip it is the least audible: a held note for one block, where a reset would be a click and a silence.
Source: DEC-6410 item 7 ("a lost block holds the registers as they were"); `synthesizer-wire-format.html`, section 11 ("the SID keeps its registers").
Verification: the engine's existing test of a lost block, run on the new block content.

**S6581-49.** When a stored sound of either kind loops, the receiver MUST go on from the last block to the first without resetting the chip, so that envelopes, oscillator phases and the filter's state carry across the join.
Reason: this is the behaviour as built; a reset at the join would be heard as a click. The full register update that begins the sound (requirement S6581-45) sets the registers.
Source: DEC-6410 item 13 ("A loop plays on across its join"); `midi-architecture.md`, MIDI-105.
Verification: a receiver test loops a two-block sound and asserts the chip's cycle count runs on across the join and the samples show no discontinuity larger than between any two other blocks.

### 3.8 Patches

**S6581-50.** For synth6581 and synth8580 a patch is one full register update: a register data message in which exactly ASID register IDs 0 to 24 are present. In MIDI form it is 37 bytes: `F0 2D 4E 7F 7F 7F 0F`, the four most-significant-bit bytes, the 25 data bytes in the order of ASID register IDs 0 to 24 (so the 22 non-control registers in address order and then the control registers of voices 1, 2 and 3), and `F7`. It is the same for the two synthesizers; the same patch sounds different on each (requirement S6581-38). No patch format, patch name or patch number is defined beyond this.
Reason: no patch standard exists for this chip anywhere: tunes carry their own player code and sound data, and each player has its own instrument tables. The one thing every tool agrees on is the registers, and ASID's register update is their adopted form.
Source: decision A4 ("for synth6581/8580 an ASID register update"); DEC-6460 ("No patch format for the SID exists anywhere"); requirement S6581-10; `midi-architecture.md`, MIDI-54 (its row for this family) and MIDI-60 (a patch of this family is sent only inline, as one event).
Verification: an encoder test that a patch is 37 bytes with the stated first seven bytes and decodes to the 25 values given.

**S6581-51.** These synthesizers MUST have no patch bank on the wire: no bank sound, no bank handle in a sound's OBJECT record, and no program change. A patch reaches the chip only as a register data message in a block. A channel's program or an authoring tool MAY keep patches as named values and send them as register updates; a kit holds none (DEC-6462 item 3). Extension tag 4, the banks of a sound, is defined only on the codecs of families with banks (`midi-architecture.md`, MIDI-48), so on this family's codec it is an unknown tag, skipped.
Reason: a bank serves an instrument that plays notes on a chosen patch. Nothing in ASID chooses a patch, a patch here holds the notes' own pitch and gate bits, and without a note-playing layer (requirement S6581-52) a bank would have no reader. As built today these synthesizers have no bank either.
Source: decision A4 (family documents state what the instrument needs); `midi-architecture.md`, MIDI-6, MIDI-48 and MIDI-57; `synthesizer-wire-format.html`, section 04 (the bank tag is not used on codec 3 today).
Verification: a server test that no bank kind exists for either name; a record test that the bank tag on an object of the family's codec is skipped, as it is today on codec 3.

### 3.9 Notes

**S6581-52.** NeoTeletext MUST NOT define a note-playing layer for synth6581 and synth8580: no note on, note off, pitch bend, controller or program change is taken by the receiver for these kinds (requirement S6581-26), and the program protocol MUST NOT have a note message for them. No kit may carry functions that turn notes into register updates (as the TypeScript kit's `synth6581Note`, `synth6581Gate` and `synth6581HardRestart` do today): a kit holds no instrument logic. A program that wants notes computes the registers itself, and what it sends are ordinary register updates.
Reason: ASID has no notes, and the owner's rule is that nothing is invented where the adopted interface is silent unless it has to be (DEC-6453 item 3). A note layer would be a whole instrument design of NeoTeletext's own: which of three voices takes a note, what waveform, envelope and filter a note uses, how pulse width, vibrato and arpeggios, which tunes make by rewriting registers every frame, are driven, and when to make the "hard restart" that the envelope's delay (requirement S6581-31) calls for. Every existing tune and tool does this in its player, before the registers, and ASID carries the result. The kits are thin clients of the server with no instrument logic and must be equals (DEC-6462 item 3), so the helpers that exist today in the TypeScript kit, and not in the Python kit, cannot stay there. This withdraws the kit's hard-restart note helper that DEC-6419 item 3 added and REQ-6414 item 1 states (section 9.3). Whether the server should offer such a layer instead is open question 1, with the recommendation that it should not.
Source: `thomasj-asid-protocol.md` (no note message is defined); DEC-6453 item 3; DEC-6462 item 3; decision A1.
Verification: the receiver test of requirement S6581-26; a server protocol test that no note message exists for either kind; inspection of each kit for code that writes registers from a note.

### 3.10 What the program protocol and the kits must give these synthesizers

The server document and the TypeScript and Python documents of this set specify the messages and calls. This section states only what these two synthesizers need of them.

**S6581-53.** The program protocol MUST have, for each of the two names, a stored sound, a live sound and a message that adds to a live sound: `synth6581`, `synth6581_live`, `synth6581_blocks`, `synth8580`, `synth8580_live` and `synth8580_blocks` (the third kind keeps today's name; whether it is renamed is the server document's). What these synthesizers need of them:

1. A stored sound and a live sound carry the sound's handle, its generation and its clock (`pal` or `ntsc`, required, requirement S6581-39). A stored sound also carries its length, as the architecture requires of every stored sound (`midi-architecture.md`, MIDI-19): a length in microseconds, or a tail in microseconds that the server adds after the last update, its blocks being ⌈length ÷ 20,000⌉, 1 to 6,000.
2. A stored sound, and each message that adds to a live sound, carry a list of register updates in time order. Each update is a time and an ASID message. The time is the architecture's (MIDI-17): whole microseconds from the start of the sound (0 is the first sample of the first block), 0 to 119,999,999 for a stored sound and 0 to 2⁵³ − 1 for a live sound, as requirement S6581-41 computes it. Two updates MAY have the same time; they keep their order in the list. Each message that adds to a live sound also carries the time `until` up to which the program has now given every update, advancing by at most 2,000,000 microseconds a message (MIDI-20).
3. The ASID message of an update MUST be accepted in its MIDI form, as bytes (`F0 2D`, the command, the payload, `F7`), so that a stream made by any existing ASID host is carried unchanged. A register data message (command 0x4E) MUST also be accepted as named, typed fields: the registers it writes, each by name with its value, and optionally the second writes of the three control registers. The server builds the ASID message from the fields, and the two forms of the same update produce the same bytes. The field names and types are the server document's.
4. The server, not the program and not a kit, MUST build the blocks: it turns each update's time into its absolute tick, ⌊(time + 50) ÷ 100⌋ (MIDI-17), places the update in the block its tick falls in (the tick divided by 200, rounded down) at the time in the block (the remainder), writes the delta times and the block form of requirement S6581-6, numbers the blocks, sends for a live sound every block that ends at or before `until` (MIDI-20), and for a live sound inserts the full register updates of requirement S6581-46. A message that adds to a live sound MUST NOT hold an update whose block the server has already sent; the server refuses it, naming the update.
5. There MUST be no field for the chip, for a number of register images in a block, or for a bank.

Reason: each name is its own kind; the clock is the one setting of a sound. The owner's decision makes the server the one implementation of the interface: a program sends typed messages at the level of the adopted interface, and the server checks them, turns them into the audio profile's blocks and records, and repeats what a late joiner needs; named fields and the interface's own bytes are the two forms that decision names for a patch. The count of register images in a block, a field of the format as built, has no meaning when each update carries its own time.
Source: DEC-6461 item 3; DEC-6462 items 1 to 3; requirements S6581-6, S6581-39, S6581-40, S6581-41, S6581-46 and S6581-51; `midi-architecture.md`, MIDI-13, MIDI-14, MIDI-16, MIDI-17, MIDI-19, MIDI-20 and MIDI-22.
Verification: a server protocol test that each of the six kinds is accepted with these fields and refused with `chip`, `model`, `images_per_block` or `bank`; a test that the same updates given as bytes and as named fields produce identical records; a test that updates at times of 0, 19,900, 20,000 and 1,234,500 microseconds land in blocks 0, 0, 1 and 61 at times 0, 199, 0 and 145; a test that times of 1,234,549 and 1,234,550 microseconds land at absolute ticks 12,345 and 12,346.

**S6581-54.** The server, when it reads a program's message of these kinds, MUST check every update and refuse the whole message, naming the update (its position in the list and its tick) and the fault, when:

1. an update's ASID message is not a system exclusive message whose first data byte is 0x2D (requirements S6581-7 and S6581-26);
2. an ASID message has a byte of 0x80 or above between its start byte and its end byte, or does not end with 0xF7 (requirement S6581-5);
3. the command is not 0x4C, 0x4D or 0x4E (requirements S6581-9 and S6581-19 to S6581-25);
4. a start or stop message has a payload (requirement S6581-18);
5. a register data message has fewer than 8 payload bytes, or a count of data bytes different from the count of mask bits, or bit 7 set in a mask or most-significant-bit byte, or a most-significant bit set for an ID that is not present (requirements S6581-10, S6581-12 and S6581-14);
6. the updates are not in time order; or, for a stored sound, an update's time lies at or beyond the end of the longest stored sound (6,000 blocks, 120,000,000 microseconds, MIDI-17 and MIDI-104), or at or beyond the sound's stated length (MIDI-19); or, for a live sound, an update falls in a block already sent, or a message advances `until` by more than 2,000,000 microseconds (requirement S6581-53; MIDI-20);
7. more than 20 register updates, or more than one start or one stop message, fall in one block (requirement S6581-42);
8. a stored sound, or a live sound's first update, is not a full register update at tick 0 (requirements S6581-45 and S6581-46).

A kit MUST NOT hold its own copy of these rules beyond what the server's generated schema states (DEC-6462 item 3); a program learns of a fault from the server's typed refusal. The receiver MUST make the checks of the block form again (requirements S6581-5 to S6581-8, S6581-14, S6581-40 and S6581-42) and pass over and count as each requirement says: it never trusts that the server checked. The server MUST make these checks with the engine's own functions that the receiver uses (`midi-architecture.md`, MIDI-21), and each refusal names the path of the field at fault, the rule broken (citing the requirement) and the detail.
Reason: a refusal by the server tells the author what is wrong and where; one implementation of the rules means one wording and no second copy to keep in step; the receiver's own checks are what security rests on.
Source: DEVELOPMENT.md sections 6 and 14; DEC-6462 items 2 and 3 (every rule a schema cannot state is checked by the server with a typed refusal; kits hold no copies of the server's rules); `midi-architecture.md`, MIDI-21, MIDI-22 and MIDI-123.
Verification: one server test for each of the eight faults, asserting the refusal's field path, rule and detail; a kit test that a message with each fault reaches the server and the server's refusal is returned unchanged; the receiver's fuzz target of requirement S6581-8.

### 3.11 Converting existing music

A large body of music exists for this chip as files that hold a tune's own player program and data for the original machine's processor. Such a file is not a list of register writes: the writes exist only when the player program is run. These requirements say what a converter from such files must produce. They do not design the converter. The format of those files is not described in any filed source; filing its description is work owed (section 9.3).

**S6581-55.** A converter from existing music MUST be an authoring-time program, separate from the server, the kits' runtime and the receiver. Its output is a sound a channel then sends as any other; nothing that runs a tune's player program may be part of the server or the browser.
Reason: a tune's player is executable content for a processor, and NeoTeletext carries no executable content and has no interpreter in the browser. Conversion once, by the author, keeps it out of every viewer's machine.
Source: DEVELOPMENT.md section 14 ("No executable content"); DEC-6410 item 13 (instrument sounds are kept as their blocks).
Verification: inspection: no crate of the engine, the browser or the server depends on the converter or contains a processor emulator; `cargo xtask check-deps` or the repository's equivalent holds it.

**S6581-56.** A converter's output MUST be a stored sound of the kind `synth6581` or `synth8580` that meets every requirement of this document: blocks of 20 milliseconds whose events are register data messages only (and, if it wishes, one start message in the first block and one stop message in the last), the first event a full register update at tick 0 holding the registers as the tune's first frame leaves them, every later frame's writes as one or more register data messages, at most 20 in a block. Within one message it MUST rely only on the order of requirement S6581-15; where a frame of the tune writes a register more than twice, writes a non-control register more than once, or needs an order that requirement S6581-15 does not give, it MUST use further messages at the same or a later tick so that the order of the tune's writes is kept.
Reason: the output must play in every receiver with no knowledge of the converter.
Source: requirements S6581-10 to S6581-17, S6581-40, S6581-42 and S6581-45.
Verification: the converter's output for a set of test tunes is passed through the server's checks of requirement S6581-54 and accepted; for each tune, the sequence of register writes the receiver makes equals the sequence the converter observed, in order.

**S6581-57.** A converter MUST place each frame's register update at the time requirement S6581-41 gives, from the tune's own frame interval and speed, and MUST NOT assume a frame is 20 milliseconds. Where it knows the offset of each write within the frame, it SHOULD place writes that are more than half a tick apart in separate messages at their own ticks.
Reason: a tune converted at the wrong frame interval plays at the wrong tempo; writes spread through a frame are part of how some tunes sound.
Source: requirement S6581-41; `thomasj-asid-protocol.md`, section "0x30 — SID Write Order & Timing", for the fact that order and timing within a frame matter to faithful playback.
Verification: for a test tune with a known frame interval that is not 20 milliseconds, the converted sound's length equals the tune's frame count times the interval, to within one tick.

**S6581-58.** A converter MUST choose the kind from the chip the tune states it was written for (`synth6581` for the earlier chip, `synth8580` for the later one), and the clock from the system the tune states (`pal` or `ntsc`). Where the tune states neither, or says either will do, the converter MUST take the author's choice and MUST NOT guess silently: it reports that it defaulted, to `synth6581` and `pal`. The information is the same that ASID's commands 0x32 and 0x31 carry.
Reason: a tune written for one chip's filter, or one clock's pitch, sounds wrong on the other; the kind and the clock are fixed for the whole sound (requirements S6581-1 and S6581-39).
Source: `thomasj-asid-protocol.md`, sections "0x31 — Speed Settings" (bit 0: PAL or NTSC) and "0x32 — SID Type Information" (bit 0: 6581 or 8580); DEC-6410 item 8.
Verification: converter tests with tunes flagged for each chip and each clock assert the kind and the `clock` field of the output.

**S6581-59.** A converter MUST report, and not silently mis-convert, a tune that these synthesizers cannot play as written:

1. a tune for more than one chip (ASID's commands 0x50 to 0x5F): it is refused, or converted for its first chip only with a report saying so;
2. a tune that plays sampled sound or depends on writes timed more finely than a tick: the source says ASID "remains unsuitable for digi-sample playback or highly arbitrary timing requirements". The converter reports any frame with more than 20 updates, or with writes it had to move by more than half a tick;
3. a tune longer than the audio profile's longest stored sound: it is cut at that length with a report, or refused;
4. a tune whose player reads a register of the chip (voice 3's waveform or envelope) or the potentiometers: the converter's own model of the chip supplies those reads, and it reports that the tune depends on them.

Reason: an author must know when a conversion is not faithful.
Source: `thomasj-asid-protocol.md`, section "Extended ASID protocol", "Notes"; requirements S6581-20, S6581-37, S6581-40 and S6581-42.
Verification: converter tests with one tune of each of the four sorts assert the report.

**S6581-60.** A converter MUST contain no code under the GNU General Public License or any other licence DEVELOPMENT.md section 7 excludes, and no code read from such a program. The programs that play these files, and the processor emulators inside them, are for the most part under that licence: none may be linked, copied, translated or read. Three ways remain that meet this requirement; the second needs the owner's decision before it is used (open question 6):

1. a converter of NeoTeletext's own, with a processor emulator written from the processor's public documents under the clean-room procedure, or one under an accepted licence that the owner approves by name;
2. an existing player run as a separate program, in the sandbox the clean-room procedure describes, whose ASID output is captured as MIDI bytes and given times by a small program of NeoTeletext's own. Only the program's output is used. The procedure as written allows a reference program only "to compare output" when building an emulator (DEC-6428 step 4); using one to make the content a channel sends is a use it does not cover. The implementations list names seven senders of ASID;
3. the author's own register updates, computed by the channel's program and sent to the server, with no conversion at all.

The music in such files belongs to its composers. A converter does not change that: a channel may send a converted tune only with the right to do so, and no such file or converted sound is committed to a repository unless its terms allow.
Reason: NeoTeletext is MIT-licensed and never uses GPL code; a program's output is not its code.
Source: DEVELOPMENT.md section 7 ("No GPL code, ever"; "No copyrighted … recordings or captures"); DEC-6428 steps 2, 4 and 6; `thomasj-asid-implementations.md`, "Hosts (Players / Senders)".
Verification: the converter's dependency list is checked by `cargo deny` against the accepted licences; its provenance is recorded in a decision as DEC-6428 step 7 requires.

---

## 4. What is built today

This is what exists on 18 November 2026, read from the code and from the two documents of the format as built. Section 9 lists how it differs from section 3.

- **The synthesizer.** One module, `synth6581`, in the engine's crate `neoteletext-audio-instruments`, emulates both chips (`Variant::Synth6581` and `Variant::Synth8580`) on either clock (`ChipClock::Pal`, `ChipClock::Ntsc`). Its interface is `write(address, value)` for one register, `write_image(&[u8; 25])` for all 25 in address order, `render(&mut [i16])`, `reset()`, and `read(address)` for the two readable registers of voice 3. It is integer-only, allocates nothing and cannot panic. It renders every chip cycle and brings the result to 48,000 Hz through two decimating filters.
- **The block.** Codec 3 of the audio profile. A block is 1, 2 or 4 register images of 25 bytes (25, 50 or 100 bytes): the registers at addresses 0 to 24, in address order, raw 8-bit values. Image k of n in a block is written at sample k × 960 ÷ n, so images are 20, 10 or 5 milliseconds apart, and the chip renders between them. All of a sound's blocks have the same number of images. Every byte value is valid. There is no time field, no mask and no partial update: every image restates every register.
- **The object.** An OBJECT record with codec 3, rate code 7, block bytes of 25, 50 or 100, and extension tag 3 of one byte (bit 0 the chip, bit 1 the clock).
- **The receiver.** One chip for each of four instrument lanes. The chip is made new, from the tag's chip and clock, when a lane is prepared for a sound. A missing block is rendered with the registers as they stand. A DATA record carries 40, 20 or 10 blocks.
- **The program protocol.** The server's types are in `crates/teletext-runtime/src/protocol.rs` of neoteletext-app-server (`Synth6581Sound`, `Synth6581LiveSound`, `Synth6581BlocksSound`, `Synth6581Clock`, `SYNTH6581_IMAGE_BYTES` = 25, `SYNTH6581_IMAGES_PER_BLOCK` = 1, 2 or 4). The kinds are `synth6581`, `synth6581_live`, `synth6581_blocks` and the same three for `synth8580`, the two names sharing one type of each. A stored sound has the fields `connections`, `handle`, `generation`, `images_per_block` (1, 2 or 4), `clock` (`pal` or `ntsc`, required) and `images` (its blocks back to back, base64, 1 to 6,000 blocks). A live sound has the same fields without `images`. A blocks message has `connections`, `handle`, `generation`, `images_per_block`, `first` (the first block's number, counting modulo 65,536) and `images` (1 to 100 blocks), and no clock. Unknown fields are refused. The server's check (`protocol/check/instrument.rs`, `synth6581`) tests only `images_per_block` and that `images` is whole blocks within those counts; every byte value is accepted. The server writes the OBJECT record (`sound/instrument.rs`, `synth6581_object`) with codec 3, block bytes of 25 times `images_per_block`, and extension tag 3 with bit 0 from the kind and bit 1 from `clock`.
- **The kits.** The TypeScript kit (neoteletext-server-ts-protocol) has `Synth6581Image` (setters for every register: pitch, control, gate, envelope, pulse width, cutoff, resonance, routing, mode and volume), `Synth6581Track` (collects images into blocks, filling a part block at the end by holding the last image), `synth6581Frequency` and `synth6581ClockHz` (hertz to a frequency register on either clock), and `synth6581Note`, `synth6581HardRestart` and `synth6581Gate` (a note with the two-frame, 40 millisecond hard restart). Its sound members make `clock` optional and write `pal` when it is absent (`sound/instrument-fields.ts`). The Python kit has none of this: it carries a copy of the server's schema only.
- **Nothing of ASID** is in any code: no system exclusive, no mask, no ASID register ID.

---

## 5. How widely ASID is used

The implementations list names six receivers ("clients") and seven senders ("hosts"): thirteen entries, twelve products, since one product is listed as both. Every one of the thirteen supports command 0x4E. The table counts, for each command, the entries marked as supporting it; "partial" and "unknown" are the list's own marks.

| Command | Receivers, of 6 | Senders, of 7 |
|---|---|---|
| 0x4E, register data | 6 | 7 |
| 0x4C and 0x4D, start and stop | 4 (the Elektron SidStation, MIDIbox SID, TeensyROM, USBSID-Pico) | 1 (Elektron ASID-XP), with 1 partial (Plogue chipsynth C64) and 1 unknown (Station 64) |
| 0x4F, display characters | 2 (the Elektron SidStation, TeensyROM) | 2 (Elektron ASID-XP, Plogue chipsynth C64), with 1 unknown (Station 64) |
| 0x50 to 0x5F, further chips | 3 (Twisted Electrons TherapSID, TeensyROM, USBSID-Pico) | 1 (DeepSID) |
| 0x30, write order and timing | 2 (TeensyROM, USBSID-Pico) | 1 (SIDFactory II) |
| 0x31, speed settings | 2 (TeensyROM, USBSID-Pico) | 1 (SIDFactory II) |
| 0x32, chip type | 2 (TeensyROM, USBSID-Pico) | 1 (SIDFactory II) |
| 0x60, OPL-FM | 2 (Twisted Electrons TherapSID, USBSID-Pico) | 1 (DeepSID) |

The receivers are five hardware devices (the Elektron SidStation, for which the protocol was designed; MIDIbox SID, of which the list says several variants exist; Twisted Electrons TherapSID, which the list says "Needs Turbo MIDI interface for Multi-SID and OPL-FM"; TeensyROM; USBSID-Pico) and one software instrument (Plogue chipsynth C64, for Windows, macOS and Linux). The senders are a browser player (DeepSID), a tracker (SIDFactory II, for Windows, macOS and Linux), two players by the protocol's designer that are no longer developed (Elektron ASID-XP for Windows and ASID-X for macOS), a program for the original machine (Station 64), a macOS player (Sidplay 5) and Plogue chipsynth C64.

What this shows:

1. Command 0x4E alone is the protocol every implementation shares. A stream of 0x4E messages, which is what NeoTeletext takes, is what all seven senders produce and all six receivers play.
2. The start and stop commands are sent in full by one sender, so a receiver cannot rely on them; NeoTeletext accepts them and gives them no effect.
3. The extensions (further chips, write order and timing, speed, chip type, OPL-FM) are each supported by at most three receivers and one sender. Leaving them out leaves out nothing that most ASID software uses.

The list's Station 64 row marks start and stop and display characters as not yet verified. DEC-6460 describes ASID as "used by about 25 players, trackers and devices"; the filed list names twelve products, and the difference is reported in section 9.3.

---

## 6. What is left out, and what is taken with a difference

### 6.1 Of the adopted interface: left out

Every command and feature of ASID that NeoTeletext does not take, with its reason. "Refused and counted" means the server refuses a program's message that holds it, and a receiver that meets it passes it over and counts it.

| Item of ASID | Where the source has it | What NeoTeletext does | Why |
|---|---|---|---|
| Command 0x4F, display characters, and the note that a receiver may assume a display of two rows of sixteen characters that clears when the command arrives | `thomasj-asid-protocol.md`, "0x4F - Display characters" | Refused and counted (S6581-19) | A sound has no display. The teletext page is the display, and text reaches it only through the page; a sound that could write text would be a second, unchecked path to the screen. Two of the six listed receivers and two of the seven listed senders support it. |
| Commands 0x50 to 0x5F, register data for the second to the seventeenth chip | "Multi-SID Register Data" | Refused and counted (S6581-20) | A sound of these kinds is one chip; four chips are four sounds on a tab's four audio channels. A sound of several chips would raise a question the kinds cannot answer, a tune for chips of both kinds. Open question 2. |
| Command 0x60, register data for a frequency-modulation chip of another family (the source names the YM3526 and YM3812) | "0x60 — OPL-FM Register Data" | Refused and counted, skipped by its length (S6581-21) | NeoTeletext has no synthesizer of that chip. |
| Command 0x30, the write order of the 28 register IDs and the wait in processor cycles after each write | "0x30 — SID Write Order & Timing" | Refused and counted (S6581-22) | A setting that every later message depends on, which a late joiner or a lost block would miss. Every message already has its own time to 0.1 millisecond, and a sender that needs another order or time between writes sends several messages. What is given up is single-cycle resolution. Open question 3. |
| Command 0x31, the system (PAL or NTSC), the speed multiplier, buffering requested, and the frame delta | "0x31 — Speed Settings" | Refused and counted (S6581-23) | The clock is in the sound's OBJECT record, which every receiver has before the first block (S6581-39). The frame interval and speed are carried by the updates' own times (S6581-41); a receiver needs no advance notice of them and always buffers whole blocks. Open question 4. |
| Command 0x32, the chip type of each chip | "0x32 — SID Type Information" | Refused and counted (S6581-24) | The kind chooses the chip, and nothing in a sound may choose it (DEC-6461 item 3). A converter uses the same information to choose the kind (S6581-58). |
| Command values the source does not define | "0x32 — SID Type Information", "Notes" (future expansion) | Refused and counted, skipped by length (S6581-25) | Nothing to act on; skipping keeps a stream made for a later version playing. |
| Transport over a MIDI cable or USB, at the frame rate a host chooses, and the bandwidth limits the source discusses ("approximately 75 Hz" on a MIDI cable) | "Original ASID protocol"; "Extended ASID protocol", "Notes" | Not used | NeoTeletext carries ASID messages inside the audio profile's blocks, records and teletext packets (decision A2). No MIDI cable exists between a channel and a viewer. |
| Reading the chip's registers (voice 3's waveform and envelope, the two potentiometer inputs) | Not part of ASID: the mapping table has no row for them and no command returns data | No message reads a register; the receiver sends nothing back (S6581-37) | ASID is one-way; a tune that reads voice 3 does so in its player, before the ASID stream is made. |

### 6.2 Of the adopted interface: taken with a difference

| Item | ASID as the source gives it | NeoTeletext | Requirement |
|---|---|---|---|
| When a message takes effect | When it arrives; the source says a set of writes is sent at each frame | At the event's time in its block, in ticks of 0.1 millisecond, on a stated sample | S6581-40, S6581-41 |
| Start and stop playback | "Signal that playback is starting" or "stopping"; "not mandatory" | Accepted, with no effect on the chip or anything else; a sound starts and stops by the audio profile's CONTROL record | S6581-18 |
| Time between the writes of one register data message | Not stated in the source | None: all writes at one instant, in ascending order of ASID register ID | S6581-15 |
| A malformed message (a count of data bytes that does not match the mask, a byte of 0x80 or above, no end byte) | Not stated in the source | Dropped whole and counted | S6581-8, S6581-14 |
| The most-significant bit of an ID absent from the mask | Not stated in the source | Written 0 by a sender; ignored by a receiver | S6581-12 |
| Number of messages in a time | Unbounded; limited only by the transport | At most 20 register data messages, one start and one stop message in a block | S6581-42 |

### 6.3 Of the chip modelled

These are parts of the chip that no ASID message reaches and that the synthesizer does not model. They are as built today.

| Part of the chip | Why |
|---|---|
| The external audio input, and bit 3 of the resonance and routing register that routes it through the filter | Nothing in NeoTeletext could feed it (S6581-33). |
| The two potentiometer inputs, read at addresses 0x19 and 0x1A | Hardware inputs for paddles; nothing in NeoTeletext could turn them, and ASID cannot read them (S6581-37). |
| What the chip returns when a write-only register is read | ASID cannot read; the module leaves it out (`mod.rs`, `read`). |

---

## 7. What NeoTeletext defines itself

Each item exists because the filed ASID documents do not define it, or because NeoTeletext's carriage needs it. Items 1 to 3 are the ones requirements S6581-12, S6581-14 and S6581-15 refer to by number.

1. **The most-significant bit of an absent ID (S6581-12).** The source does not say what a set bit means for an ID whose mask bit is clear. A sender writes 0 and a receiver ignores it, so that no behaviour depends on it, and the server refuses a program's message that sets one, so that an author's mistake is seen.
2. **Dropping a malformed message whole (S6581-8, S6581-14).** The source does not say what a client does with a message whose count of data bytes does not match its mask, or that breaks the 7-bit rule. Applying part of it would set registers no sender meant; dropping it and counting it keeps every other message and tells the port something was wrong.
3. **No chip time between the writes of one message (S6581-15).** The source gives the order of the writes ("the regular ASID write order") but not the time between them; on the original machine a program takes some cycles between writes, and command 0x30 exists to state them. NeoTeletext applies a message's writes at one instant, in that order, so that every receiver gives the same result; a sender that needs time between two writes puts them in two messages at different ticks.
4. **The order of the bits within a mask byte (S6581-11).** The source says each mask byte covers seven IDs, "one bit per ID", without saying in words that bit 0 is the lowest. NeoTeletext reads it so, and the reading is to be confirmed against a captured stream before the requirement is marked implemented (section 9.3).
5. **The time of each message (S6581-6, S6581-40, S6581-41).** ASID has no time; the source's messages take effect on arrival. Decision A3 gives the block's event form and the tick; this document adds the sample a register update lands on, the order of updates at one tick, and how a tune's frame interval and speed become ticks without drift.
6. **The bounds on a block (S6581-42, S6581-43, S6581-44).** Twenty register data messages, one start and one stop message, 874 bytes at most: this family's lower bounds within the architecture's 256 events and 1,005 bytes (`midi-architecture.md`, MIDI-30 and MIDI-31). ASID has no bound but its transport; a receiver of untrusted input needs one.
7. **Full register updates for joining and loss (S6581-45, S6581-46, S6581-47).** A stored sound begins with one; the server inserts one into a live sound in its first block, at least once every 50 blocks and, where there is room, every 25 blocks, as the architecture's restatement rule says for every synthesizer (`midi-architecture.md`, MIDI-93 to MIDI-99). ASID streams over a cable assume an unbroken stream from the start; the audio profile has viewers who join late and blocks that are lost.
8. **The chip from the kind, the clock from the OBJECT record (S6581-1, S6581-39).** As built. ASID's command 0x32 and bit 0 of command 0x31 carry the same facts inside the stream, where a late joiner may miss them.
9. **Start and stop with no effect (S6581-18).** The source gives them no effect on the chip; NeoTeletext accepts them so that captured streams travel unchanged, and gives them none.
10. **A patch is a full register update, and there is no bank (S6581-50, S6581-51).** No patch format exists for this chip (DEC-6460); decision A4 names the register update as the patch.
11. **The register update in the program protocol (S6581-53).** Its time in whole microseconds, which the server rounds once to a tick (`midi-architecture.md`, MIDI-17), and the ASID message either as its bytes or as named, typed register fields from which the server builds the same bytes (DEC-6462 item 1).
12. **The receiver's behaviour at the start of a sound, on a lost block and at a loop's join (S6581-36, S6581-48, S6581-49).** The chip is reset when a sound starts, a lost block holds the registers, and a loop runs on without a reset. As built; ASID has no sounds, loss or loops.
13. **What a converter must produce and report (S6581-55 to S6581-60).** ASID's hosts are players; NeoTeletext needs a tune turned once into a stored sound, which no filed document describes.

---

## 8. Open questions for the owner

**1. Should NeoTeletext define a note-playing layer for synth6581 and synth8580?**
ASID has none: a tune plays the chip by writing registers, and every existing player decides in its own code which voice plays a note, with which waveform, envelope, pulse width, filter, vibrato and arpeggio, and when to make the hard restart. Today the TypeScript kit has helpers (`synth6581Note`, `synth6581Gate`, `synth6581HardRestart`) that turn a note into register images; under DEC-6462 they cannot stay in a kit.
- *Option A: no note layer anywhere in NeoTeletext* (S6581-26, S6581-52). A program computes its own registers, or a converter makes a sound from existing music. Nothing is invented; the interface is ASID alone. A program that wants notes has more to write, as an author of music for this chip always has.
- *Option B: note messages in the server's program protocol for these kinds*, which the server turns into register updates (MIDI note on and note off, perhaps with a voice and a patch of 25 registers). The receiver and the block form stay ASID. It is a whole instrument design of NeoTeletext's own (voice allocation, which registers a note sets, the hard restart's timing), which DEC-6453 forbids unless it has to be, and every choice in it is one that existing tunes make differently.
- *Option C: note messages in the block, played by the receiver.* All of option B's design, and the receiver's work and state grow with it; the block is then no longer ASID.
- *Recommendation:* A. If channel authors need notes, the help belongs in an example program of a channel (as the audio demo channel already has its own player code), not in the protocol, the server or a kit.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: no note-playing layer for synth6581 and synth8580 anywhere in NeoTeletext; note help belongs in an example channel program.

**2. Should a sound carry several chips (ASID commands 0x50 to 0x5F)?**
- *Option A: no* (S6581-20). One sound is one chip; a tune for two chips is two sounds started together on two audio channels. Simple and as built, but two sounds started by two CONTROL records are not guaranteed to start on the same sample.
- *Option B: yes, up to a stated number of chips in one sound*, with commands 0x50 and above taken. It needs an answer to which kind a sound of a 6581 and an 8580 is, more work for each block, and a larger block bound. Three of the six listed receivers and one of the seven listed senders support these commands.
- *Recommendation:* A, until a channel needs a tune for more than one chip; then B with the chips' kinds stated in the OBJECT record.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: one chip per sound, until a channel needs a tune for more than one chip.

**3. Should command 0x30, write order and timing, be taken?**
- *Option A: no* (S6581-22). Order and time between writes are given by separate messages at their own ticks, to 0.1 millisecond (about 98 chip cycles on the PAL clock).
- *Option B: yes, as a setting of the sound in its OBJECT record*, so that a late joiner has it: 56 bytes in an extension, applied to every register data message. Writes could then be spaced to single cycles inside one message, which the receiver can honour only to the nearest sample (about 20.5 chip cycles).
- *Recommendation:* A. The receiver renders a sample at a time, so most of the resolution command 0x30 offers could not be honoured; revisit if a converted tune is shown to sound wrong for want of it.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: command 0x30 is not taken.

**4. Should the clock come from ASID's command 0x31 instead of from the sound's `clock` field and OBJECT record?**
- *Option A: the OBJECT record and the `clock` field* (S6581-39, as built). Every receiver has the clock before the first block.
- *Option B: command 0x31's bit 0, in the first block.* It is ASID's own place for it, but a viewer who joins late, or loses the first block, plays at the wrong pitch, and a message in a block could change the clock in the middle of a sound.
- *Recommendation:* A.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: the clock stays in the OBJECT record and the `clock` field.

**5. Is twenty register data messages a block the right bound?**
- *Option A: 20* (S6581-42): the highest speed command 0x31 names, 16 updates a frame at 50 frames a second, with a quarter more for faster frames; 874 bytes a block at most.
- *Option B: 16*, exactly that highest speed at 50 frames a second: 702 bytes a block at most (16 messages of 43 bytes, and the start and stop messages' 14). A tune at speed 16 with a frame shorter than 20 milliseconds would not fit.
- *Option C: more, for example 50*, one update every 0.4 millisecond: 2,164 bytes a block at most (50 messages of 43 bytes, and 14), more than the architecture's largest block of 1,005 bytes (`midi-architecture.md`, MIDI-30), so this option would also need that bound changed, and two and a half times the receiver's worst-case work.
- *Recommendation:* A.
- Answered by DEC-6465 (awaiting the owner's confirmation): option A, as written: at most 20 register data messages a block.

**6. How is existing music for this chip to be converted, if at all?**
The files hold a player program for the original machine's processor (section 3.11). DEC-6428 allows a GPL or proprietary program to be run only in a sandbox "to compare output" when building an emulator (step 4); it does not cover using a program's output as the content a channel sends.
- *Option A: a converter of NeoTeletext's own*, with a processor emulator written under the clean-room procedure from the processor's public documents, and the file format filed first (section 9.3). Clean and lasting, and the most work.
- *Option B: capture an existing player's ASID output* in the sandbox and give it times (S6581-60, way 2). Quick, but it needs the owner's decision extending DEC-6428 step 4 to this use, and the player's licence must allow its output to be used so.
- *Option C: no converter for now.* Authors write registers in their programs, as the audio demo channel does today.
- *Recommendation:* C now, and A if the owner wants existing music on channels; B only by an explicit decision that names the program and its licence. Whichever is chosen, a converted tune is sent only with the right to send it (S6581-60).
- Answered by DEC-6465 (awaiting the owner's confirmation): option C, as recommended: no converter of existing chip music for now; a clean-room converter of NeoTeletext's own only if the owner later wants existing music on channels; capturing another player's output only by an explicit owner decision naming the program and its licence.

---

## 9. Differences from what is built today

What exists is described in section 4. Implementing this document changes the following. Every change to the wire is a breaking change to the program protocol, the server, the kits and the browser, made together.

### 9.1 The engine (neoteletext-renderer-teletext)

1. **The block.** Today a codec 3 block is 1, 2 or 4 register images of 25 bytes, so 25, 50 or 100 bytes, every block of a sound the same size (`Codec::allows_block` in `crates/neoteletext-audio/src/codec.rs`, `SYNTH6581_IMAGE_BYTES`). It becomes a Standard MIDI File track-event list of ASID messages (S6581-6), of varying length up to 874 bytes (S6581-43). The OBJECT record's block-bytes field, extension tag 8 and the DATA record of the event codecs carry blocks of varying length as the architecture specifies (`midi-architecture.md`, MIDI-39 to MIDI-47); today a DATA record holds 40, 20 or 10 fixed blocks. The codec's code is today 3. It becomes code 12 if `midi-architecture.md`'s open question 1 is answered as that document recommends (MIDI-107 to MIDI-109, codes 3 to 11 retired), and otherwise stays 3 with the new block content; this document does not decide it (S6581-1).
2. **The receiver.** Today `render_synth6581` in `crates/neoteletext-audio/src/receiver/instruments.rs` cuts a block into images and calls `Synth6581::write_image` for image k of n at sample k × 960 ÷ n. It becomes a decoder of the block's events: a delta time, a system exclusive event, the ASID identifier and command; for command 0x4E, the mask, the most-significant bits and the data bytes, written by `Synth6581::write(address, value)` in ascending order of ASID register ID (S6581-15) at sample ⌊time × 24 ÷ 5⌋ (S6581-40), with the chip rendered between. Every other event is passed over and counted (S6581-7, S6581-9, S6581-26), a malformed message is dropped whole (S6581-8), and a block's register data messages beyond 20 and its start and stop messages beyond one each are passed over (S6581-42). `write_image` then has no caller outside the module's tests and is removed if none remains.
3. **Counters.** The receiver's statistics (`crates/neoteletext-audio/src/receiver.rs`, which today count slots passed over, `slots_passed_over`) gain counts of the events of the family's codec passed over and of malformed ASID messages, as the architecture's counters (`midi-architecture.md`, MIDI-123).
4. **The ASID table.** A table from ASID register ID to register address (S6581-11), asserted against the module's `REGISTERS` so that the 28 IDs reach exactly the 25 addresses (S6581-27).
5. **The synthesizer module** (`crates/neoteletext-audio-instruments/src/synth6581/`) does not change: `write` already performs any register write, including both writes of a control register in one message, and every byte is valid.
6. **The encoder.** `crates/neoteletext-audio/src/encode.rs`, which the server uses to write records, gains the building of a block of the family's codec from timed ASID messages.
7. **Fuzzing and tests.** A fuzz target for the family's block decoder (S6581-8; `midi-architecture.md`, MIDI-124). The tests that build images (`crates/neoteletext-audio/tests/instruments.rs`: `image`, `synth6581_sound`, the stored and live tests) change to the new block; the module's own tests do not change; the new tests are those each requirement's "Verification" names.
8. **The tag.** Extension tag 3 and its handling (`record.rs`: `TAG_SYNTH6581_CHIP`, `SYNTH6581_CHIP_8580`, `SYNTH6581_CLOCK_NTSC`, the refusal of bits 2 to 7) do not change (S6581-39), except that the tag is read on the family's codec, whatever its code (`midi-architecture.md`, MIDI-48).

### 9.2 The server (neoteletext-app-server) and the kits

9. **The program protocol.** In `crates/teletext-runtime/src/protocol.rs`, `Synth6581Sound`, `Synth6581LiveSound` and `Synth6581BlocksSound` lose `images_per_block` and `images`, and the message that adds to a live sound loses `first`; they gain a list of register updates, each a time in whole microseconds and an ASID message given as bytes or as named, typed register fields, a stored sound's length or tail, and on each message that adds to a live sound the time `until` (S6581-53; `midi-architecture.md`, MIDI-17, MIDI-19 and MIDI-20). An earlier draft of this document had a program state each update's absolute tick; it now states whole microseconds and the server rounds, because the architecture gives every synthesizer's events that one form (MIDI-17), which governs. `clock` stays required on a stored and a live sound. The constants `SYNTH6581_IMAGE_BYTES` and `SYNTH6581_IMAGES_PER_BLOCK` go. The JSON Schema is regenerated (today `protocol/schema-12.json`), with a new version, and copied into both kits.
10. **The checks.** Today `protocol/check/instrument.rs`, `synth6581`, checks only `images_per_block` and that `images` is whole blocks in count. It gains the eight checks of S6581-54, each with a typed refusal.
11. **Building the records.** Today `sound/instrument.rs` (`synth6581`, `synth6581_live`, `synth6581_blocks`, `synth6581_object`) copies a program's images into blocks unchanged. It becomes the builder of blocks from register updates (S6581-53 item 4): placing each update by its tick, writing delta times, numbering blocks, and, for a live sound, keeping each register's current value from message to message so as to insert a full register update in the first block, at least every 50 blocks and, where there is room, every 25 blocks (S6581-46; `midi-architecture.md`, MIDI-96 and MIDI-98). That per-sound state is new in the server, held for each live sound's handle and generation and dropped when the sound is replaced.
12. **The server's tests and fixtures.** The fixture `synth6581()` in `protocol/tests/sound.rs`, the shared fixture of real messages (`hello.jsonl`) and neoteletext-common's `wire-vectors.tsv` change to the new form.
13. **The TypeScript kit** (neoteletext-server-ts-protocol). `Synth6581Track`, `synth6581Note`, `synth6581Gate`, `synth6581HardRestart`, `SYNTH6581_HARD_RESTART_FRAMES`, `SYNTH6581_HARD_RESTART_MS`, `synth6581Frequency`, `synth6581ClockHz` and the clock constants are instrument logic and are removed (S6581-52, DEC-6462 item 3); `Synth6581Image` is replaced by the types generated for the named register fields; the default of `clock` to `pal` (`sound/instrument-fields.ts`) is removed; the kit's own checks of these kinds (`wire/instrument-rules.ts`) shrink to what the schema states. A major release of the kit.
14. **The Python kit** (`neoteletext-server-channels/kits/python`) gains the same generated types and calls, and nothing else.
15. **The audio demo channel** (neoteletext-server-channel-audiodemo), whose `src/synth6581/` files (`player.ts`, `tune.ts`, `song.ts`, `duet.ts`, `effects.ts`, `live.ts`) use the kit's images, tracks and note helpers, must compute its own register updates and send them in the new form.

### 9.3 Records, documents and sources owed

These are not changes to code; each is work for a session permitted to write rdm records or to file sources, and none was done in writing this document.

16. **DEC-6460's count of ASID implementations.** DEC-6460 says ASID is "used by about 25 players, trackers and devices". The filed list (`thomasj-asid-implementations.md`) names six receivers and seven senders: thirteen entries and twelve products, Plogue chipsynth C64 being listed both as a receiver and as a sender. Counting the two variants of MIDIbox SID that the list's notes name (sammichSID and MB6582) as products of their own gives fourteen. No filed document gives a figure of about 25, and DEC-6460 does not say where its figure came from. The choice of ASID does not depend on the figure, since section 5's conclusion rests on every listed implementation sharing command 0x4E, but a decision must not state what its evidence does not hold. DEC-6460 is to be revised to say "twelve products named in the filed implementations list (six receivers and seven senders, one product listed as both)", or the source of the larger figure filed and cited. `sid/documents.tsv` describes the list correctly and needs no change.
17. **DEC-6410 and its requirements.** DEC-6410 item 7 (a block is whole register images; "Every image is complete, so a receiver needs no earlier block") is replaced for this family's codec by this document and decision A3. DEC-6410 is to be amended or superseded on the owner's approval of this document, and the requirements it decides that describe the block as images revised: REQ-6411 item 2 for the codec, and REQ-6414 item 1, which asks the TypeScript kit for a builder of register images, a frequency helper, calls that send images, and the hard-restart note helper of DEC-6419 item 3. Under DEC-6462 and S6581-52 none of those stays in a kit, so REQ-6414 item 1 and DEC-6419 item 3 are to be revised to match, and the protocol's documentation item for the codecs (DOC-1860) with them.
18. **The chip's public documents.** The documents the module cites (section 1) are not filed in `~/devel/teletext-reference/synthesizers/sid/`. They are to be filed there with rows in `documents.tsv` (DEC-6428 step 1), and those that requirements S6581-27 to S6581-39 rest on recorded as rdm sources, so that this document's register descriptions can cite them directly rather than through the module.
19. **A captured ASID stream.** S6581-11 asks for one frame of an ASID stream captured from an existing host program, run as a separate program in the sandbox of DEC-6428 step 4, to confirm the order of the bits within a mask byte before the requirement is marked implemented.
20. **The format of the tune files.** If open question 6 is answered A or B, a description of the files' format is to be filed before a converter is written (section 3.11).
21. **The two documents of the format as built.** `synthesizer-wire-format.html` and `programming-the-synthesizers.html` in `~/devel/teletext-reference/synthesizers/` describe the images and are regenerated when the new form is built.
