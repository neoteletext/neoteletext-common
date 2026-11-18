# The synthesizers in the Rust server

**Purpose.** This document is the main specification of the synthesizers' programming interface (DEC-6462 item 4). It specifies, as Rust types with their exact names, fields, field types, bounds and serde tags, every message of program protocol 13 by which a channel's program sends a sound to one of NeoTeletext's eleven synthesizers; and it specifies, as numbered requirements, everything the server (neoteletext-app-server) does with those messages: validation with typed refusals, the packing of patches into the adopted interfaces' forms, the building of event blocks and bank images, the restatement a late joiner needs, the timing of live sounds, the reading of Standard MIDI Files, the engine crates the server calls so that the encoder and the receiver's own checks are one implementation, the bounds on every input and on the work per message, the fuzz targets, the tests and their shared golden vectors, the generated schema and how the kits copy it, the removal of program protocol 12's synthesizer kinds and of the kit-side logic they needed, and the order in which all of it is built.

**Scope.** It covers the `sound` message's synthesizer kinds and the server's handling of them. It does not restate the MIDI architecture (`midi-architecture.md`, requirements MIDI-1 to MIDI-125), whose block grammar, records, codecs, bank codec, restatement rules and limits it implements, nor any family's messages, controllers or patch bytes, which the family documents of this folder specify; it names their requirements where the server rests on them. It does not specify how the records reach the browser or how the browser plays them (the integration document of this set, `integration.md`), nor the calls of the two kits (the TypeScript and Python documents of this set), which are thin clients of the types below. The messages of program protocol 13 that are not about sound are `../viewer-state.md`'s (VS-351 to VS-354) and the protocol's existing messages; this document and that one together define protocol 13 (SRV-2).

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

Which instrument each synthesizer models is said once, in `synthesizers.md` in this folder, with the trademark statement. Makers' names appear below only where a source is cited.

**What this document decides, in brief** (each item is specified by the requirements cited):
1. Program protocol 13 has, for each of the eleven names, a stored sound, a live sound and an events message, and for each name of a family with banks a bank message: 42 kinds in all, from `synth6581`, `synth6581_live` and `synth6581_events` to `synth80`, `synth80_live`, `synth80_events` and `synth80_bank`, every one listed in SRV-3. The third kind is renamed from `_blocks` to `_events`, because a program no longer sends blocks (SRV-4).
2. Music is given as timed events, each a time in whole microseconds and one MIDI message given as a typed object (a note, a control change, a program change with its bank select, a registered or non-registered parameter number, a pitch bend, a pressure, a system exclusive message, an inline patch, a named parameter) or as raw MIDI bytes; or, for a stored sound, as the bytes of a Standard MIDI File (SRV-10 to SRV-24).
3. A patch is given as named, typed fields or as the adopted interface's own bytes, for every family; a bank as a list of patches or as the bank image's bytes (SRV-25 to SRV-45).
4. The server validates every message completely with the engine's own functions, refuses a faulty one whole with a typed refusal (path, rule, detail citing the requirement, and the sound it concerns), and lists every rule (SRV-48 to SRV-54).
5. The server packs patches, builds bank images, places events into event blocks, lifts bank dumps out of music, holds the program's banks and sends each before a sound that names it, restates every part, times live sounds by `until_us` and paces their blocks to the receiver's ring of 32 (DEC-6477), reads Standard MIDI Files, and writes the records, all through the engine's crates at one pinned commit (SRV-55 to SRV-89).
6. Every bound is a named constant (SRV-90), every reader of a program's input has a fuzz target (SRV-92), and the server and the engine share golden vectors in neoteletext-common (SRV-94).
7. The schema is `protocol/schema-13.json`, generated from the types; the kits copy it byte for byte, pinned to a server commit, and hold no sound logic (SRV-96 to SRV-98).
8. Program protocol 12's synthesizer kinds and every piece of kit code that built slots, images, patches or banks are removed in the same change (SRV-99, SRV-100), in the order of SRV-102.

---

## 1. Sources

### 1.1 Decisions

| Record | What this document takes from it |
|---|---|
| DEC-6462 | The governing decision: the server is the one implementation of the synthesizers' programming interface; a program sends structured, typed JSON at the level of the adopted interfaces (a patch as named typed fields or as its standard system exclusive, music as timed MIDI events or a Standard MIDI File, a bank as a list of patches, play, stop, gain); the server validates, builds blocks and records, splits what is too long and restates for late joiners; the interface is defined as the existing protocol is (Rust types first, a generated JSON Schema, typed refusals, shared fixtures and vectors); the kits are thin and equal; this document is the main specification. |
| DEC-6453 | Every instrument is programmed exactly as its most well-known existing interface does it; nothing of NeoTeletext's own unless nothing exists. |
| DEC-6461 | The eleven names, each its own kind; a sound, a live sound, a blocks message and a bank for each name; no `model`, `chip` or revision field for a program to set. |
| DEC-6464 version 2 | Reset all controllers is answered by every synthesizer as the MIDI Association's RP-015 says (the server writes it with value 0). |
| DEC-6465 | The answers to the architecture's and the family documents' open questions, among them: new codec numbers 12 to 19 (answer 1); restatement within every 50 blocks, aiming at 25, and the server writing block 0's restatement (answer 2); 1 to 10 banks a sound (answer 3); no restatement made for a single joining viewer (answer 4); RPN 0 for bend range everywhere (answer 5); a synth7 bank of fewer than 32 voices filled with the default voice by the server, more than 32 refused (answer 18); no note layer for synth6581 and synth8580 (answer 8). |
| DEC-6473 | Three readings of RP-015 and MIDI 1.0 (synthD's GLIDE switch off on reset; reset and all notes off answered on every channel; pedals reset only where they are pedals), which the engine's trackers follow (SRV-68). |
| DEC-6471 | The viewer-state proposal, accepted by the owner on 18 November 2026, which makes program protocol 13 and push protocol 8 (the engine's next version after 7); its program messages are `../viewer-state.md` VS-351 to VS-354. |
| DEC-6477 | The answers to this document's open questions and those of the TypeScript, Python and integration documents, at the owner's delegation, and the settlement of the conflicts between the documents; it governs where this document first said otherwise: the server paces live blocks to the receiver's ring (SRV-77), every bytes field is marked `contentEncoding: "base64"` (SRV-6), every refusal of a sound and every `sound_built` names the sound (SRV-47, SRV-48), names follow this document in every document of the set. |
| DEC-6474 | The Python kit validates every message at run time with `jsonschema`, is kept fully equal to the TypeScript kit, and generates its types from the schema (SRV-98). |
| REQ-1475, REQ-1476, REQ-1479 | Every message has one exact typed shape and a faulty one is refused whole; the messages and the schema come from one set of types; one JSON Schema generated from the server's Rust types. |
| REQ-2215 | The protocol's version is one number, raised on every change of shape. |
| REQ-6413 | Each instrument block is checked with the engine's code before it is sent. |

### 1.2 Documents of this set

| Document | What this document takes from it |
|---|---|
| `midi-architecture.md` | The whole frame: what a program expresses (MIDI-13 to MIDI-22), the block grammar and bounds (MIDI-23 to MIDI-38), the records (MIDI-39 to MIDI-49), system exclusive longer than an event (MIDI-50 to MIDI-53), patches and banks (MIDI-54 to MIDI-66), channels (MIDI-67 to MIDI-71), parameter control (MIDI-72 to MIDI-92), restatement and live sounds (MIDI-93 to MIDI-103), stored sounds (MIDI-104 to MIDI-106), codecs and the protocol's version (MIDI-107 to MIDI-111), Standard MIDI Files (MIDI-112 to MIDI-120), limits and fuzzing (MIDI-121 to MIDI-124). |
| `synth6581-synth8580.md` | ASID's message and register data (S6581-4 to S6581-17), the 28 register IDs and their names (S6581-11, S6581-27), the clock (S6581-39), times (S6581-41), the family's block bounds (S6581-42, S6581-43), the opening update and the restatement (S6581-45, S6581-46), the patch (S6581-50), no bank (S6581-51), no note layer (S6581-52), and what the protocol and the server must give these two (S6581-53, S6581-54). |
| `synth7.md` | The 156 voice parameters with their ranges and packed places (S7-28), the fourteen function parameters (S7-33, S7-35), the single-voice dump (S7-38), the checksum (S7-39), the 32-voice dump (S7-41, S7-42), the parameter change (S7-43), the packed voice (S7-46 to S7-48), sizes and restatement (S7-49), the program mapping and the refusal of a third bank (S7-50), the default voice (S7-51). |
| `synth106-synth60.md` | The patch message and manual message (S106-13, S106-14), the parameter change (S106-17), the switch bytes (S106-18), the mapping of the 18 values and three synth60 settings to fields (S106-22), the switch bands and canonical values (S106-24), the synth60 patch (S106-31, S106-32), what the server takes (S106-36 to S106-40). |
| `synthd.md` | The 39 panel controls and their controllers on the Voyager's map (SD-17), the 60-byte patch (SD-22), the patch as control changes (SD-26), the bank (SD-27), the restatement (SD-28). |
| `synth53-synth52-synth51.md` | The NRPN table (section 6.3), bank select by controller 32 (S53-13), the numbering of programs (S53-25), banks and blocks (S53-26), the 67 program parameters (S53-27), the dumps (S53-28, S53-29), packing (S53-31, S53-32), the program layout (S53-33), the revision parameter (S53-38), restatement (S53-46), what the server takes (S53-47). |
| `synth8.md` | The channel map (S8-2), the 42 panel controls (S8-16), the key mode and split key (S8-18), the 42-byte patch (S8-23, S8-27), the bank, program numbers and restatement (S8-28, S8-29). |
| `synth80.md` | The tone and master controllers (S80-10, S80-11), the twelve of NeoTeletext's own (S80-18), GLIDE MODE on controller 3 (S80-20), the 85-byte patch (S80-33), program change and bank select by controller 0 (S80-35, S80-36), the patch as control changes (S80-40), what the server must do (S80-41), the 22 preset tones (S80-42, S80-43), the restatement (S80-46). |
| `../viewer-state.md` | Program protocol 13's other changes (VS-351 to VS-354), the order of the cut-over (its section 9, VS-601 and VS-602), the removal of the server session. |

### 1.3 What is built today

| Source | What it is used for here |
|---|---|
| `~/devel/neoteletext-app-server` at commit `df662b9`: `crates/teletext-runtime/src/protocol.rs` | Program protocol 12: `PROTOCOL` = 12; `LONGEST_LINE` 16 MiB; `SAFE_INTEGER_LIMIT`; `Connections`, `Base64`; `Sound` with its 51 variants; the instrument constants (`MOST_INSTRUMENT_BLOCKS`, `MOST_LIVE_INSTRUMENT_BLOCKS`, `SYNTH6581_IMAGE_BYTES` and the rest); `Refused` and the closed list `Rule`; `schema()`. The example every type below follows. |
| The same, `protocol/check.rs` and `protocol/check/instrument.rs` | The rules a schema cannot state, checked over a message once read, the first fault refusing it whole with its path (`Path`, `fault`, `Refusal`). The instrument rules of protocol 12, which this document replaces. |
| The same, `protocol/read.rs` | The strict reader that follows `type` and then `kind` to the message's own type and reports the path of the first fault serde finds. |
| The same, `sound.rs`, `sound/instrument.rs`, `channel.rs` (`ProgramMessage::Sound`, `records`) | How a `sound` becomes records today: the server writes codecs 3 to 11's bodies itself, because the engine it pins (`4ddd34be`) predates them, and sends each record to each connection named as teletext packets numbered on that connection. |
| The same, `protocol/schema-12.json`, `protocol/tests/schema.rs` | The published schema and its test (`TELETEXT_BLESS_SCHEMA=1` writes it). |
| The same, `fuzz/fuzz_targets/instrument_sound.rs` | The fuzz target of protocol 12's instrument sounds, which SRV-92 replaces. |
| `~/devel/neoteletext-server-ts-protocol`: `schema/protocol-12.json`, `scripts/check.sh` (`SCHEMA_FROM`), `src/wire/generated/`, `src/wire/instrument-rules.ts`, `src/wire/instrument-wire.ts`, `src/sound/` (4,279 lines), `test/server-rules.test.ts` | The schema copy rule, the generated validators, and the sound logic that moves into the server under DEC-6462. |
| `~/devel/neoteletext-server-channels`: `kits/python/src/neoteletext_app/protocol-12.json`, `scripts/check.sh` (`SCHEMA_FROM`, `SCHEMA_COPY`) | The Python kit's schema copy and its rule. The Python kit has no synthesizer code. |
| `~/devel/neoteletext-common/wire-vectors.tsv` | The form of shared vectors: the engine keeps an exact copy, which its commit gate compares, and the server reads that copy through its pinned engine. |

---

## 2. Terms

The terms of `midi-architecture.md` section 2 hold here (synthesizer, family, variant, kind, adopted interface, part, patch, bank, bank image, sound, stored sound, live sound, block, tick, event, delta time, restatement, refused, passed over and counted). In addition:

- **Program protocol 13.** The version of the protocol between the server and a channel's program that this document and `../viewer-state.md` define together, replacing version 12.
- **Message.** In this document, unless it says "MIDI message", one JSON object on one line of program protocol 13.
- **The sound message.** A message whose `type` is `sound`; its `kind` names which of the `Sound` enum's variants it is.
- **Synthesizer kind.** One of the 42 values of `kind` this document defines (SRV-3).
- **Timed event.** One element of a list of events in a program's message: a time in microseconds and one MIDI message given in one of the forms of SRV-12.
- **Named fields form.** A patch given as an object with one typed field for each parameter of the family's patch.
- **Bytes form.** A patch or a bank given as the exact bytes the adopted interface defines, in base64.
- **Canonical value.** The value the server writes for a field whose interface accepts several values with one meaning: for a switch or selector carried by a controller, the lowest value of its position's band, as the family document defines it.
- **The bank table.** What the server holds, for one channel program, of the banks the program has sent (SRV-59).
- **The live table.** What the server holds, for one channel program, of each live synthesizer sound it is building (SRV-72).
- **Tracker.** The engine's record of one sound's parts as its events are written, from which a restatement is written (MIDI-94; SRV-68).
- **Interface module.** The engine's code of one family that holds the family's tables and checks without its synthesis: which messages it takes, how a patch is packed and checked, how a bank image is read, and its tracker (SRV-88).
- **Golden vector.** One row of the shared file `synth-vectors.tsv` (SRV-94).

Numbers written `0x…` are hexadecimal. "µs" is not used; times are written "microseconds", and their fields end in `_us`.

---

## 3. Program protocol 13 for sounds

### 3.1 The version

**SRV-1. Program protocol 13.** The server's `PROTOCOL` constant MUST become 13 in the commit that builds this document's messages, and the published schema MUST be `protocol/schema-13.json`; `protocol/schema-12.json` MUST be deleted in the same commit. A program whose `start` names version 12 MUST stop at `start`, naming both versions, as the protocol does today for an older version. The doc comment of `PROTOCOL` MUST gain a sentence for version 13 naming both its changes: the synthesizers' typed interface (this document) and the viewer state mechanism (`../viewer-state.md`).
- Reason: The sound messages change shape (MIDI-111); the protocol's rule is one number, raised on every change of shape (REQ-2215).
- Source: MIDI-111; REQ-2215; `protocol.rs` (`PROTOCOL` and its history).
- Verification: The existing schema test (`protocol/tests/schema.rs`), its file name now `schema-13.json`; a test that a version-12 program stops at `start`.

**SRV-2. One protocol 13 with the viewer state mechanism.** Program protocol 13 MUST hold both this document's sound messages and `../viewer-state.md`'s messages (VS-351 to VS-354). The two MUST NOT give a field, a message type, a `kind`, a server message or a `Rule` value the same name with two meanings. The names this document adds to `ServerMessage` (`sound_built`, SRV-47), to `Refused` (`sound`, SRV-48) and to `Rule` (SRV-51) MUST NOT be among those `../viewer-state.md` adds (the server messages `viewer_began`, `viewer_left`, `state_refused`, `viewers_reset` and `gone`; the program messages `request_state`, `end_state` and `offer_remember`; the `Rule` values `has_viewer`, `no_gesture` and `unknown_viewer` of VS-353), and none is. `SAFE_INTEGER_LIMIT`, which today is `session_cookie::SESSION_LIMIT − 1` and which VS-354's removal of the session module would orphan, MUST be defined in `protocol.rs` as `2^53 − 1` (9,007,199,254,740,991) with its reason (the largest integer every language's JSON reader holds exactly, IEEE 754 binary64), because this document's live times rest on it (SRV-8). The two MUST be released in one schema and one deployment; whichever is ready first waits for the other (DEC-6477 answer 3).
- Reason: The brief of this set asks that the documents agree on one protocol 13; the deployment of protocol 13 is one cut-over (`../viewer-state.md`, its requirement on one planned cut-over), and a second version for whichever part comes second would be a second breaking change for every channel.
- Source: `../viewer-state.md` VS-351 to VS-354, its section 5.3 and section 9; `protocol.rs` (`SAFE_INTEGER_LIMIT`); DEC-6477 answer 3.
- Verification: A test lists every message type, kind, server message and rule name in `schema-13.json` and checks no name appears twice; the schema test.

### 3.2 The kinds

**SRV-3. The synthesizer kinds.** The `Sound` enum (`#[serde(tag = "kind", rename_all = "snake_case")]`) MUST have exactly these synthesizer variants, besides the six of Opus and PCM and the three commands, which stay as they are (SRV-46). Each row's four kinds are the name's stored sound, live sound, events message and bank; the Rust variant names are the kind in upper camel case (`Synth106Live`, `SynthDBank`), with `#[serde(rename = "…")]` where serde's snake case would not give the kind (`synthd`, `synthd_live`, `synthd_events`, `synthd_bank`).

| Name | Stored sound | Live sound | Events message | Bank | Their Rust types |
|---|---|---|---|---|---|
| synth6581 | `synth6581` | `synth6581_live` | `synth6581_events` | none (S6581-51) | `Synth6581Sound`, `Synth6581LiveSound`, `Synth6581EventsSound` |
| synth8580 | `synth8580` | `synth8580_live` | `synth8580_events` | none | the same three types |
| synth7 | `synth7` | `synth7_live` | `synth7_events` | `synth7_bank` | `Synth7Sound`, `Synth7LiveSound`, `Synth7EventsSound`, `Synth7BankSound` |
| synth106 | `synth106` | `synth106_live` | `synth106_events` | `synth106_bank` | `Synth106Sound`, `Synth106LiveSound`, `Synth106EventsSound`, `Synth106BankSound` |
| synth60 | `synth60` | `synth60_live` | `synth60_events` | `synth60_bank` | `Synth60Sound`, `Synth60LiveSound`, `Synth60EventsSound`, `Synth60BankSound` |
| synthD | `synthd` | `synthd_live` | `synthd_events` | `synthd_bank` | `SynthDSound`, `SynthDLiveSound`, `SynthDEventsSound`, `SynthDBankSound` |
| synth53 | `synth53` | `synth53_live` | `synth53_events` | `synth53_bank` | `Synth53Sound`, `Synth53LiveSound`, `Synth53EventsSound`, `Synth53BankSound` |
| synth52 | `synth52` | `synth52_live` | `synth52_events` | `synth52_bank` | the four synth53 types |
| synth51 | `synth51` | `synth51_live` | `synth51_events` | `synth51_bank` | the four synth53 types |
| synth8 | `synth8` | `synth8_live` | `synth8_events` | `synth8_bank` | `Synth8Sound`, `Synth8LiveSound`, `Synth8EventsSound`, `Synth8BankSound` |
| synth80 | `synth80` | `synth80_live` | `synth80_events` | `synth80_bank` | `Synth80Sound`, `Synth80LiveSound`, `Synth80EventsSound`, `Synth80BankSound` |

That is 42 synthesizer kinds: eleven stored sounds, eleven live sounds, eleven events messages and nine banks (`synth7_bank`, `synth106_bank`, `synth60_bank`, `synthd_bank`, `synth53_bank`, `synth52_bank`, `synth51_bank`, `synth8_bank`, `synth80_bank`); the synth6581 family has no bank kind, because DEC-6461 item 3 gives a bank only to a name whose family has banks. No variant MUST carry a `model`, `chip`, `variant`, `slots`, `images_per_block`, `first` or `patch_bytes` field. synth6581 and synth8580 share one set of types and synth53, synth52 and synth51 another, as today; the kind alone says which synthesizer plays (MIDI-48: the server writes tags 3 and 5 from the kind).

The types MAY be written by a macro in the source, but each MUST be a named, concrete type, so that the schema's `$defs` carry the names this table gives and no generic instance name.
- Reason: DEC-6461 items 1 and 3: each name its own kind, with a sound, a live sound, a third message and, where the family has banks, a bank. The synth6581 family has no bank (S6581-51). Concrete names keep the generated TypeScript and Python types readable.
- Source: DEC-6461; S6581-51, S6581-53; MIDI-1; `protocol.rs` (the `Sound` enum, `#[serde(rename = "synthd")]`).
- Verification: A schema test lists the synthesizer kinds of `$defs/Sound` and checks the 42 values, each once; a test sends each kind with a field of protocol 12 (`slots`, `images_per_block`, `first`, `model`, `chip`) and checks the refusal `unknown_field`.

**SRV-4. The third kind is the events message.** The kind that adds to a live sound MUST be named `<name>_events`, not `<name>_blocks`. `<name>_blocks` MUST NOT be a kind of protocol 13; a message of that kind MUST be refused with the rule `not_listed` on the path `kind`.
- Reason: A program no longer sends blocks; it sends events and the time up to which it has sent them (MIDI-20), and the server makes the blocks. Keeping the old name for a new shape would mislead every author who knew version 12. `synth6581-synth8580.md`, S6581-53, leaves the name to this document; DEC-6461 item 3 named the third kind by its content as it then was.
- Source: S6581-53; MIDI-20; DEC-6461 item 3.
- Verification: A test sends `synth7_blocks` and checks the refusal.

### 3.3 The common fields

**SRV-5. Who, which handle, which generation.** Every synthesizer kind MUST carry these three fields first, with the types and meanings they have in every `sound` of protocol 12:
- `connections`: `Connections`, either `"all"` or a list of 1 to `MOST_NAMED_CONNECTIONS` (4,096) connection numbers, each 1 to `SAFE_INTEGER_LIMIT`;
- `handle`: `u8`, 0 to 255, the audio profile's handle of the object (the sound, or the bank);
- `generation`: `u16`, 0 to 65,535, the object's generation.
- Reason: These are the audio profile's object identity and the protocol's addressing, unchanged.
- Source: `protocol.rs` (`Connections`, every `*Sound` struct).
- Verification: The existing tests of `Connections`, run on every synthesizer kind.

**SRV-6. Exact base64, marked as bytes.** Every field that carries bytes MUST be of type `Base64` (a string of exact base64 as RFC 4648 section 4 defines it, padded, with no whitespace), checked as the protocol checks it today (`check_base64`), and refused with `not_base64` when it is not, and with `too_long` when its decoded length is above the field's bound, which each field's requirement states. The schema of `Base64` MUST carry `"contentEncoding": "base64"` (JSON Schema 2020-12 Validation, section 8.3), written by a `schemars` attribute on the type, so that every field of the type, in this document and in every other message of protocol 13 that carries bytes, is marked; and no field that does not carry base64 bytes MUST be so marked.
- Reason: The protocol's one coding of bytes. The mark is what lets the TypeScript and Python kits' generators type every bytes field as bytes (`Uint8Array`, `bytes`) by one rule, with no knowledge of which field is which (`typescript.md` TS-21, `python.md` PY-13; DEC-6477 typescript answer 1).
- Source: `protocol.rs` (`Base64`); `protocol/check.rs` (`check_base64`); DEC-6477.
- Verification: The existing base64 tests, run on every bytes field of this document; a schema test that every property whose type is `Base64` carries `contentEncoding: "base64"` and no other property does.

**SRV-7. A MIDI channel is 1 to 16.** Every field named `channel` in this document's types MUST be a `u8` from 1 to 16, the MIDI channel as MIDI 1.0's prose numbers it; the server MUST write channel `c` as `c − 1` in the low four bits of a status byte, and in the channel field of a system exclusive message it builds (the DX7's sub-status byte, the Juno-106's byte d). The audio profile's audio channel, 0 to 3, keeps its field name `channel` only in `play`, `stop` and `gain` (SRV-46), whose meaning is unchanged.
- Reason: Channel numbers in a program's music should read as musicians, MIDI 1.0's prose and the family documents write them ("program changes on channels 1 and 2", S8-12); the server, which writes every byte, does the subtraction once.
- Source: MIDI-67 (channels 1 to 16 in prose, 0 to 15 in the status byte); MIDI 1.0 4.2, Table I, note on `nnnn` ("N-1, where N = Channel #", PDF 100).
- Verification: A test sends a note on channel 1 and channel 16 and checks status bytes `0x90` and `0x9F`; channel 0 and 17 are refused `out_of_range`.

**SRV-8. Time is whole microseconds from the sound's start.** Every timed event MUST carry `time_us`: `u64`, whole microseconds from the start of the sound, where 0 is the first sample of block 0. For a stored sound `time_us` MUST be 0 to `MOST_STORED_TIME_US` − 1 (119,999,999); for a live sound 0 to `SAFE_INTEGER_LIMIT`. The server MUST place an event at the absolute tick `floor((time_us + 50) ÷ 100)`, in block `floor(tick ÷ 200)` at tick `tick mod 200` within it, computing each event's tick from its own time and never from another event's (MIDI-17). For a stored sound an event whose tick falls in a block at or past the sound's block count MUST be refused with `beyond_length` (SRV-14), which also refuses the times 119,999,950 to 119,999,999 that round into block 6,000.
- Reason: MIDI-17's rule, stated with its field name. The range of MIDI-17 for a stored sound admits 50 microseconds of times that round past the last block, so the check is made on the tick.
- Source: MIDI-17, MIDI-36; S6581-41, S6581-53 item 2.
- Verification: The tests of MIDI-17; the test of S6581-53 (times 0, 19,900, 20,000 and 1,234,500 microseconds land in blocks 0, 0, 1 and 61 at ticks 0, 199, 0 and 145; times 1,234,549 and 1,234,550 at absolute ticks 12,345 and 12,346); a test refuses a stored event at 119,999,950.

**SRV-9. A stored sound's length.** Every stored synthesizer sound MUST carry `length`: `SoundLength`, an externally tagged enum (`#[serde(rename_all = "snake_case")]`) of exactly one of:
- `{"length_us": n}`: the sound's length, `n` a `u64` from 1 to `MOST_STORED_TIME_US` (120,000,000); its blocks are `ceil(n ÷ 20,000)`;
- `{"tail_us": n}`: how long the sound rings after its last event, `n` a `u64` from 0 to `MOST_STORED_TIME_US`; its blocks are the larger of `ceil((T + n) ÷ 20,000)` and `floor(K ÷ 200) + 1`, where K is the absolute tick of the last event (or, for a Standard MIDI File, the later of the last event's tick and the last end-of-track's tick, MIDI-120) and T is `K × 100`, and at least 1; with no event at all, `ceil(n ÷ 20,000)`, at least 1.
The blocks MUST be 1 to `MOST_INSTRUMENT_BLOCKS` (6,000); a sound whose blocks would be more MUST be refused with `beyond_length` on the path `length`, naming the blocks it would need.
- Reason: The OBJECT needs the block count (MIDI-19, MIDI-40); a program states how long the sound rings after its last event, which no event says. The second term of the tail's formula makes the last event's own block always part of the sound, so that a tail of 0 never cuts it off.
- Source: MIDI-19, MIDI-104, MIDI-120; `protocol.rs` (`MOST_INSTRUMENT_BLOCKS`).
- Verification: A server test checks the OBJECT's block count for `length_us` of 1, 20,000, 20,001 and 120,000,000; for `tail_us` 0 after an event at tick 199 (1 block) and at tick 200 (2 blocks); refuses `length_us` 0 and 120,000,001.

### 3.4 Timed events

**SRV-10. The events of a note-playing family.** For each of the six families that play notes (synth7, synth106, synthD, synth53, synth8, synth80), the events of a stored sound and of an events message MUST be a list of that family's event type: `Synth7Event`, `Synth106Event`, `Synth60Event`, `SynthDEvent`, `Synth53Event`, `Synth8Event`, `Synth80Event`. Each is an internally tagged enum, `#[serde(tag = "event", rename_all = "snake_case", deny_unknown_fields)]`, with exactly these variants, whose structs are shared by every family except the last two, which are the family's own:

| `event` | Rust variant and struct | Fields besides `time_us` | The MIDI message the server writes |
|---|---|---|---|
| `note_off` | `NoteOff(NoteOff)` | `channel` 1 to 16; `key` `u8` 0 to 127; `velocity` `u8` 0 to 127, the release velocity | `8n key velocity` |
| `note_on` | `NoteOn(NoteOn)` | `channel`; `key` 0 to 127; `velocity` `u8` 0 to 127 (0 is a note off, MIDI-88) | `9n key velocity` |
| `key_pressure` | `KeyPressure(KeyPressure)` | `channel`; `key` 0 to 127; `pressure` `u8` 0 to 127 | `An key pressure` |
| `control_change` | `ControlChange(ControlChange)` | `channel`; `controller` `u8` 0 to 127; `value` `u8` 0 to 127 | `Bn controller value` |
| `program_change` | `ProgramChange(ProgramChange)` | `channel`; `program` `u8` 0 to 127; `bank_msb` `Option<u8>` 0 to 127, default none; `bank_lsb` `Option<u8>` 0 to 127, default none | `Bn 00 msb` where given, `Bn 20 lsb` where given, then `Cn program`, at one tick in one block (MIDI-37 (a)) |
| `channel_pressure` | `ChannelPressure(ChannelPressure)` | `channel`; `pressure` `u8` 0 to 127 | `Dn pressure` |
| `pitch_bend` | `PitchBend(PitchBend)` | `channel`; `value` `u16` 0 to 16,383, centre 8,192 | `En lsb msb`, `lsb = value mod 128`, `msb = floor(value ÷ 128)` |
| `rpn` | `Rpn(ParameterNumber)` | `channel`; `parameter` `u16` 0 to 16,383; `value` `u16` 0 to 16,383 | `Bn 65 p_msb`, `Bn 64 p_lsb`, `Bn 06 v_msb`, `Bn 26 v_lsb` (controllers 101, 100, 6, 38), at one tick in one block (MIDI-37 (c)) |
| `nrpn` | `Nrpn(ParameterNumber)` | as `rpn` | `Bn 63 p_msb`, `Bn 62 p_lsb`, `Bn 06 v_msb`, `Bn 26 v_lsb` (controllers 99, 98, 6, 38) |
| `rpn_step` | `RpnStep(ParameterStep)` | `channel`; `parameter` 0 to 16,383; `direction`: `ParameterDirection`, `increment` or `decrement` | `Bn 65 p_msb`, `Bn 64 p_lsb`, then `Bn 60 00` (increment, controller 96) or `Bn 61 00` (decrement, controller 97) |
| `nrpn_step` | `NrpnStep(ParameterStep)` | as `rpn_step` | `Bn 63 p_msb`, `Bn 62 p_lsb`, then `Bn 60 00` or `Bn 61 00` |
| `system_exclusive` | `SystemExclusive(SystemExclusive)` | `bytes`: `Base64`, one whole message from `0xF0` to `0xF7`, 3 to `MOST_EVENT_BYTES` (16,384) bytes decoded | the message as one event `F0 <length> …` (MIDI-27) |
| `raw` | `Raw(RawMidi)` | `bytes`: `Base64`, one or more whole MIDI messages back to back, running status allowed within the event (SRV-13), 1 to `MOST_EVENT_BYTES` bytes decoded | each message as its own event at this event's tick, in order, with its status byte written in full (MIDI-12) |
| `patch` | `Patch(<Family>PatchEvent)` | `channel`; `patch`: the family's patch type (SRV-25 onward) | the patch's inline form (MIDI-60), at one tick in one block |
| `parameter` | `Parameter(<Family>ParameterEvent)` | `channel`; `set`: the family's parameter type, an externally tagged enum of one named parameter and its typed value (SRV-25 onward) | the one message the family document names for that parameter's real-time change (MIDI-18) |

The family's two own structs are named `<Family>PatchEvent` and `<Family>ParameterEvent`: `Synth7PatchEvent`, `Synth7ParameterEvent`, `Synth106PatchEvent`, `Synth106ParameterEvent`, `Synth60PatchEvent`, `Synth60ParameterEvent`, `SynthDPatchEvent`, `SynthDParameterEvent`, `Synth53PatchEvent`, `Synth53ParameterEvent`, `Synth8PatchEvent`, `Synth8ParameterEvent`, `Synth80PatchEvent`, `Synth80ParameterEvent`. Every struct of this table MUST carry `time_us` (SRV-8) as its first field and MUST be `deny_unknown_fields`.

The variants are the same in every family, whether or not the family acts on the message: whether a family takes a message is the engine's table of that family (SRV-88), and the server refuses one it does not take with `not_taken` (SRV-51), naming the family document's requirement.
- Reason: MIDI-16 lists exactly these forms: typed objects for each channel message, an NRPN or RPN with its 14-bit number and value, a bank select with its program change, a patch, a named parameter, a system exclusive message as its bytes, and raw bytes. Writing a bank select only together with its program change, and a parameter number only together with its data, enforces MIDI-37's groups by the shape of the message. One set of variants for every family keeps the six event types alike for authors and kits; which messages a family takes is decided once, in the engine, not twice in the schema and the engine.
- Source: MIDI-16, MIDI-18, MIDI-37, MIDI-60, MIDI-76, MIDI-88, MIDI-90; MIDI 1.0 4.2, Table III (PDF 102: controllers 6, 38, 96 to 101) and printed page 13 (PDF 45: "the Program Change must be sent immediately after the Bank Select pair").
- Verification: For each family, a server test sends one event of every variant and checks the bytes written against the table, or the refusal `not_taken` naming the requirement; a test checks every struct refuses an unknown field.

**SRV-11. The value written for a parameter step.** The server MUST write the value byte of controller 96 or 97 as 0.
- Reason: MIDI-90 makes each step move the range by one cent "whatever its value", MIDI-84 has every synthesizer accept any value, and the server must write one value so that a block written twice has one form (MIDI-44). MIDI 1.0 4.2's text does not fix the value the sender writes; 0 is NeoTeletext's choice (section 6).
- Source: MIDI-44, MIDI-90.
- Verification: The test of SRV-10's `rpn_step` row.

**SRV-12. The events of synth6581 and synth8580.** The events of a `synth6581` or `synth8580` stored sound and of a `synth6581_events` or `synth8580_events` message MUST be a list of `Synth6581Event`, `#[serde(tag = "event", rename_all = "snake_case", deny_unknown_fields)]`, with exactly two variants:
- `register_update`: `RegisterUpdate { time_us, registers: Synth6581Registers }`, an ASID register data message (command 0x4E) given by named fields;
- `asid`: `AsidMessage { time_us, bytes: Base64 }`, one ASID message in its MIDI form, `F0 2D`, the command, the payload, `F7` (S6581-4), 4 to 257 bytes decoded (the longest system exclusive message MIDI-28 allows, so that a command the family does not take is refused as `not_taken` rather than by its length; a register data message is at most 40, S6581-10).

`Synth6581Registers` MUST be a struct of exactly these 28 fields, each `Option<u8>` from 0 to 255 with default none (S6581-17: every value 0x00 to 0xFF is valid), named for the ASID register IDs of S6581-11 in ID order; a field given is a register present in the message's mask:

| ASID register ID | Field | Register (S6581-11, S6581-27) |
|---|---|---|
| 0 | `voice1_frequency_low` | Voice 1 frequency, low byte (address 0x00) |
| 1 | `voice1_frequency_high` | Voice 1 frequency, high byte (0x01) |
| 2 | `voice1_pulse_width_low` | Voice 1 pulse width, low byte (0x02) |
| 3 | `voice1_pulse_width_high` | Voice 1 pulse width, high bits (0x03) |
| 4 | `voice1_attack_decay` | Voice 1 attack and decay (0x05) |
| 5 | `voice1_sustain_release` | Voice 1 sustain and release (0x06) |
| 6 | `voice2_frequency_low` | Voice 2 frequency, low byte (0x07) |
| 7 | `voice2_frequency_high` | Voice 2 frequency, high byte (0x08) |
| 8 | `voice2_pulse_width_low` | Voice 2 pulse width, low byte (0x09) |
| 9 | `voice2_pulse_width_high` | Voice 2 pulse width, high bits (0x0A) |
| 10 | `voice2_attack_decay` | Voice 2 attack and decay (0x0C) |
| 11 | `voice2_sustain_release` | Voice 2 sustain and release (0x0D) |
| 12 | `voice3_frequency_low` | Voice 3 frequency, low byte (0x0E) |
| 13 | `voice3_frequency_high` | Voice 3 frequency, high byte (0x0F) |
| 14 | `voice3_pulse_width_low` | Voice 3 pulse width, low byte (0x10) |
| 15 | `voice3_pulse_width_high` | Voice 3 pulse width, high bits (0x11) |
| 16 | `voice3_attack_decay` | Voice 3 attack and decay (0x13) |
| 17 | `voice3_sustain_release` | Voice 3 sustain and release (0x14) |
| 18 | `filter_cutoff_low` | Filter cutoff, low bits (0x15) |
| 19 | `filter_cutoff_high` | Filter cutoff, high byte (0x16) |
| 20 | `filter_resonance_routing` | Filter resonance and routing (0x17) |
| 21 | `filter_mode_volume` | Filter mode and volume (0x18) |
| 22 | `voice1_control` | Voice 1 control (0x04) |
| 23 | `voice2_control` | Voice 2 control (0x0B) |
| 24 | `voice3_control` | Voice 3 control (0x12) |
| 25 | `voice1_control_second` | Voice 1 control, second write (0x04) |
| 26 | `voice2_control_second` | Voice 2 control, second write (0x0B) |
| 27 | `voice3_control_second` | Voice 3 control, second write (0x12) |

From a `register_update` the server MUST write the register data message of S6581-10 to S6581-13: the mask bits of the fields given, the most-significant-bit bytes from bit 7 of each value, and the data bytes in ascending ID order; the same update given as `asid` bytes MUST produce identical bytes (S6581-53 item 3). A `register_update` with no field given MUST be refused with `too_short` on the path `registers` (the message would be the empty update S6581-16 says a sender SHOULD NOT send). A full register update is a `register_update` with the 25 fields of IDs 0 to 24 given and none of IDs 25 to 27 (S6581-50).

There MUST be no note, controller, program, patch or bank event for these two kinds (S6581-52).
- Reason: S6581-53 item 3: ASID register data accepted as its bytes, so that any existing ASID stream is carried unchanged, and as named, typed fields, whose names and types are this document's. The names are the source's register names (S6581-11's column "the source's name") written out in full in lower case.
- Source: S6581-4, S6581-10 to S6581-17, S6581-50, S6581-52, S6581-53.
- Verification: The test of S6581-53 (the two forms give identical records); a test for each of the 28 fields alone checks the mask bit and data byte written; a test with a value of 0x80 checks the most-significant-bit byte.

**SRV-13. Raw MIDI bytes.** In a `raw` event the server MUST read one or more whole MIDI messages, expanding running status as MIDI-12 says (channel voice and mode messages only; cleared by a system exclusive or system common message; a system real-time message leaves it). Running status MUST NOT carry from one `raw` event into another, nor into or out of any other event: the first message of each `raw` event MUST begin with a status byte. A data byte where a status is expected and no running status is in effect MUST be refused with `running_status`, naming the byte's offset. A message cut short by the end of the bytes MUST be refused with `malformed_midi`. Every message read MUST then be checked as if it had been given as its own typed event.
- Reason: MIDI-12 asks the server to accept running status where a program sends raw bytes and to write every message with its status. Bounding running status to one event keeps each event readable alone, as each block is.
- Source: MIDI-12, MIDI-16; MIDI 1.0 4.2, printed page 5 (PDF 37) and A-2 (PDF 92).
- Verification: The tests of MIDI-12; a test sends two `raw` events, the second beginning with a data byte, and checks the refusal.

### 3.5 Music

**SRV-14. The music of a stored sound.** Every stored synthesizer sound MUST carry `music`, an internally tagged enum `#[serde(tag = "form", rename_all = "snake_case", deny_unknown_fields)]` with exactly two variants:
- `events`: `{ "form": "events", "events": [ … ] }`, a list of 0 to `MOST_STORED_EVENTS` (100,000) of the family's events (SRV-10, SRV-12), in non-decreasing order of `time_us`;
- `midi_file`: `{ "form": "midi_file", "bytes": …, "channel_map": … }`, a Standard MIDI File as `Base64`, 14 to `MOST_MIDI_FILE_BYTES` (1,048,576) bytes decoded, and for the six note-playing families an optional `channel_map` (SRV-23). The synth6581 family's file variant has no `channel_map` field.

The Rust types are `Synth6581Music`, `Synth7Music`, `Synth106Music`, `Synth60Music`, `SynthDMusic`, `Synth53Music`, `Synth8Music`, `Synth80Music`; their file variants are `Synth6581MidiFile { bytes }` and, for the others, `MidiFile { bytes, channel_map }`. Two events with the same `time_us` MUST keep their order in the list (MIDI-35). An event with a smaller `time_us` than the one before it MUST be refused with `not_ascending`, naming both indexes. An event whose tick lies in a block at or past the sound's block count MUST be refused with `beyond_length`.
- Reason: DEC-6462 item 1 ("music as timed MIDI events or a Standard MIDI File"); one field with a tagged choice states in the schema that exactly one form is given. 14 bytes is the smallest file that holds a header chunk (`MThd`, its 4-byte length and 6 bytes); a shorter one cannot be read at all.
- Source: MIDI-16, MIDI-19, MIDI-35, MIDI-112, MIDI-119; S6581-53 item 2; Standard MIDI Files 1.0, printed pages 3 and 4 (PDF 132 and 133: the header chunk is `MThd`, a 4-byte length of 6, and 6 bytes).
- Verification: A test of each form for each family; a test of two events at one time in both orders; the refusals `not_ascending` and `beyond_length`.

**SRV-15. Bank dumps lifted out of music.** Every stored sound of a family with banks MUST carry `lift_banks`: a list of 0 to 10 `BankName { handle: u8, generation: u16 }`, default empty. The server MUST give the k-th bank it lifts from the music (SRV-63) the k-th name of the list. A sound whose music holds more bank dumps to lift than `lift_banks` names MUST be refused with `bank_not_named`, naming the first dump not named; a sound that names more than it lifts MUST be refused with `too_long` on the path `lift_banks`.
- Reason: MIDI-58: a lifted bank is given "a handle and generation of the program's choosing or, where the program gave none, refuse". A name the program did not use would be a handle reserved for nothing.
- Source: MIDI-58.
- Verification: The tests of SRV-63.

**SRV-16. The fields of a stored sound.** Each stored synthesizer sound MUST have exactly these fields, in this order:

| Type | Fields |
|---|---|
| `Synth6581Sound` (kinds `synth6581`, `synth8580`) | `connections`, `handle`, `generation`, `clock`: `Synth6581Clock` (`pal` or `ntsc`, required, S6581-39), `length`: `SoundLength`, `music`: `Synth6581Music` |
| `Synth7Sound`, `Synth106Sound`, `Synth60Sound`, `SynthDSound`, `Synth53Sound` (kinds `synth53`, `synth52`, `synth51`), `Synth80Sound` | `connections`, `handle`, `generation`, `banks`: a list of 0 to the family's most banks (SRV-58) of `u8` handles, `lift_banks`: `Vec<BankName>` (SRV-15), `length`: `SoundLength`, `music`: the family's music type |
| `Synth8Sound` | as the row above, with `key_mode`: `Synth8KeyMode` (`whole`, `dual` or `split`) and `split_key`: `u8` 0 to 127 after `generation` (S8-18; MIDI-48 tag 7) |

`banks` lists the sound's banks in order: bank index 0 first (MIDI-57). Banks lifted from the music follow them as the next bank indexes, in the order lifted (MIDI-58); the total MUST be at least 1 and within the family's most banks (SRV-58). `banks` MAY therefore be empty when `lift_banks` names at least one bank: MIDI-57's "1 to 10 banks" are the banks the sound's OBJECT names in its extension tag 4, which are `banks` followed by the lifted banks (SRV-79), and a sound whose only bank is lifted from its music names that one bank there as bank index 0. A stored sound whose `banks` and `lift_banks` together name no bank MUST be refused with `too_short` on the path `banks` (SRV-58).
- Reason: MIDI-19: a stored sound names its kind, its handle and generation, its banks, its variant setting where its family has one in its OBJECT (the clock; synth8's key mode and split key), its music, and its length.
- Source: MIDI-19, MIDI-48, MIDI-57, MIDI-58; S6581-39, S6581-53 item 1; S8-18; DEC-6477 (the question of an empty `banks`, raised by `typescript.md`, settled here).
- Verification: A schema test of each type's fields; a test of each refusal of a missing field; a test of a synth7 sound with `banks` empty and one name in `lift_banks` whose music begins with a 32-voice dump, accepted, its OBJECT's tag 4 naming the lifted bank as bank index 0; the same sound with `lift_banks` empty refused `too_short` on `banks`.

**SRV-17. The fields of a live sound.** Each live synthesizer sound MUST have exactly these fields: `Synth6581LiveSound`: `connections`, `handle`, `generation`, `clock`; `Synth8LiveSound`: `connections`, `handle`, `generation`, `key_mode`, `split_key`, `banks`; every other live type (`Synth7LiveSound`, `Synth106LiveSound`, `Synth60LiveSound`, `SynthDLiveSound`, `Synth53LiveSound`, `Synth80LiveSound`): `connections`, `handle`, `generation`, `banks`. A live sound's `banks` MUST name 1 to the family's most banks (SRV-58), since it lifts none. A live sound has no length, no music and no `lift_banks`: its events come in events messages, and a bank dump in them is refused as MIDI-51 says (SRV-63).
- Reason: MIDI-20: a live sound is announced once, with its kind, handle, generation, banks and variant setting.
- Source: MIDI-20; S6581-53 item 1.
- Verification: A schema test of each type's fields.

**SRV-18. The fields of an events message.** Each events message MUST have exactly these fields: `connections`, `handle`, `generation`, `until_us`: `u64` from 1 to `SAFE_INTEGER_LIMIT`, and `events`: a list of 0 to `MOST_LIVE_EVENTS` (25,600) of the family's events, in non-decreasing order of `time_us`. The types are `Synth6581EventsSound` (kinds `synth6581_events`, `synth8580_events`), `Synth7EventsSound`, `Synth106EventsSound`, `Synth60EventsSound`, `SynthDEventsSound`, `Synth53EventsSound` (kinds `synth53_events`, `synth52_events`, `synth51_events`), `Synth8EventsSound`, `Synth80EventsSound`. What the server does with one is SRV-74 to SRV-77.
- Reason: MIDI-20: each events message gives the events of a span and the time `until` up to which the program has given every event. 25,600 is MIDI-122's bound: 100 blocks of 256 events.
- Source: MIDI-20, MIDI-122; S6581-53 item 2.
- Verification: A schema test; a test at 25,600 events and one past it (`too_long`).

**SRV-19. The fields of a bank message.** Each bank message MUST have exactly these fields: `connections`, `handle`, `generation`, `bank`: the family's bank type (SRV-27, SRV-32, SRV-35, SRV-38, SRV-41, SRV-44). The types are `Synth7BankSound`, `Synth106BankSound`, `Synth60BankSound`, `SynthDBankSound`, `Synth53BankSound` (kinds `synth53_bank`, `synth52_bank`, `synth51_bank`), `Synth8BankSound`, `Synth80BankSound`. What the server does with one is SRV-59 to SRV-62.
- Reason: MIDI-15: a bank as a list of patches, or as the interface's whole-bank bytes.
- Source: MIDI-15, MIDI-55, MIDI-56.
- Verification: A schema test of each type.

**SRV-20. Every bank type has two forms.** Each family's bank type MUST be an internally tagged enum `#[serde(tag = "form", rename_all = "snake_case", deny_unknown_fields)]` with exactly two variants: `patches`, a list of the family's patches, each in either form of its patch type, patch k of the list being program k of the bank (with the synth53 family's `group`, SRV-38); and `bytes`, `{ "form": "bytes", "bytes": … }`, the bank image of MIDI-56 exactly as the family document defines it, 1 to `MOST_BANK_IMAGE_BYTES` (16,384) bytes decoded.
- Reason: MIDI-15: a bank as a list of 1 to 128 patches in either form of MIDI-14, and as the bank image's bytes, which is what every existing bank file holds where the interface has a bank dump, and for the other families exactly what the bank object carries.
- Source: MIDI-14, MIDI-15, MIDI-55, MIDI-56.
- Verification: For each family, a test sends a bank in both forms, built to hold the same patches, and checks identical bank records.

**SRV-21. Every patch type has two forms.** Each note-playing family's patch type MUST be an internally tagged enum `#[serde(tag = "form", rename_all = "snake_case", deny_unknown_fields)]` with exactly two variants: `fields`, the named fields of the family's patch (the family's section below), and `bytes`, `{ "form": "bytes", "bytes": … }`, the patch in the adopted interface's own form, 1 to `MOST_PATCH_BYTES` (16,384) bytes decoded, whose exact length and content the family's section states. The types are `Synth7Patch`, `Synth106Patch`, `Synth60Patch`, `SynthDPatch`, `Synth53Patch`, `Synth8Patch`, `Synth80Patch`. From the `fields` form the server MUST write canonical values; a `bytes` form MUST, once checked, be carried byte for byte. A patch given in both forms that set the same parameters to the same values, with the bytes form at canonical values, MUST produce identical bytes (MIDI-14).
- Reason: MIDI-14: two forms, both accepted, the same patch giving the same bytes. Carrying a checked bytes form unchanged is DEC-6453's byte-for-byte compatibility: a patch from any existing source plays as it came.
- Source: MIDI-14; DEC-6453 item 2; DEC-6462 item 1; S106-36, S106-37, S53-47, S80-41 (e).
- Verification: For each family, a server test encodes the family's default patch and three others from named fields and from bytes and checks the records byte for byte equal (MIDI-14's test).

**SRV-22. The fields of a patch event and a parameter event.** Each `<Family>PatchEvent` MUST have exactly `time_us`, `channel` and `patch` (the family's patch type); each `<Family>ParameterEvent` exactly `time_us`, `channel` and `set` (the family's parameter type). Each family's parameter type MUST be an externally tagged enum (`#[serde(rename_all = "snake_case")]`) with one variant for each named parameter the family's section lists, each variant holding its value with the type and range the section gives, so that the schema states every parameter's name and the range of its value: `"set": {"op3_output_level": 80}`.
- Reason: MIDI-18: a named parameter of the family's parameter table and a value in that parameter's own units or range. An externally tagged enum carries the range with the name, which a name field and a value field could not.
- Source: MIDI-18, MIDI-60.
- Verification: A schema test checks every parameter variant's range against the family document's table, as data.

**SRV-23. A Standard MIDI File's channel map.** The `channel_map` of a `MidiFile` MUST be `Option<[Option<u8>; 16]>`, default none: a list of exactly 16 entries, entry n for the file's channel n + 1, each null (that channel's messages are dropped) or a channel 1 to 16 of the sound. Without a map, each message keeps its channel (MIDI-116).
- Reason: MIDI-116.
- Source: MIDI-116.
- Verification: The test of MIDI-116.

**SRV-24. Events are checked against the family, the kind and the part.** Every timed event MUST be checked against the family document of the sound's kind, with the engine's own table of what that family takes (SRV-88): its status, its controller (MIDI-80), its range, its channel's part (MIDI-67; for synth8, panel controllers and program changes on channels 1 and 2 only, S8-2), and for a system exclusive message its exact bytes. A message the family does not act on MUST be refused with `not_taken`; a message that MIDI-8 lists as never carried MUST be refused with `never_carried`, naming the event. Both refusals' detail MUST name the family document's requirement or MIDI-8's row.
- Reason: MIDI-10 and MIDI-8: every message a family's table does not list is refused by the server; MIDI-21: the server checks with the receiver's own code.
- Source: MIDI-8, MIDI-10, MIDI-21, MIDI-80; S7-5, S106-1, SD-1, S53-2, S8-1, S80-1, S6581-26.
- Verification: For each family, a server test sends one message of every status `0x80` to `0xEF`, every controller 0 to 127, every message of MIDI-8 and one system exclusive message of a foreign manufacturer, and checks exactly the family's listed ones accepted (MIDI-10's server test).

### 3.6 synth6581 and synth8580: the patch

**SRV-25. A synth6581 or synth8580 patch is a full register update.** These two kinds MUST have no patch type, no bank kind, no `banks` field, no program change and no named parameter beyond the register fields of SRV-12: a patch is a full register update (S6581-50), given as a `register_update` with the 25 fields of IDs 0 to 24, or as `asid` bytes of the 37-byte message. The server MUST refuse a stored sound whose first event is not a full register update at tick 0 of block 0, with the rule `no_opening_update` on the path `music.events[0]` (or `music` when there is no event, or the file's first event for a Standard MIDI File), and the same of a live sound's first events message (S6581-45, S6581-54 item 8).
- Reason: S6581-50 to S6581-52: no patch standard exists for the chip; ASID's register update is the patch; the family's stored sound opens with the program's own full update, which this family requires in place of a server-written restatement (MIDI-99 allows it).
- Source: S6581-45, S6581-50, S6581-51, S6581-52, S6581-54 item 8; MIDI-99.
- Verification: The tests of S6581-54 item 8; a schema test that the two kinds have no `banks`, `patch` or `parameter`.

### 3.7 synth7

**SRV-26. A synth7 voice as named fields.** `Synth7Patch::Fields` MUST hold `Synth7Voice`, with exactly these fields, each the voice parameter of `synth7.md`, S7-28, whose number is given, as an integer in the parameter's own range (the interface's values, unchanged: `algorithm` 0 is the algorithm the instrument shows as 1):

| Field | Type and range | Voice parameter (S7-28) |
|---|---|---|
| `operators` | `[Synth7Operator; 6]`, exactly six, **operator 1 first**, operator 6 last | operator n's fields are parameters `(6 − n) × 21` to `(6 − n) × 21 + 20` |
| `pitch_eg_rates` | `[u8; 4]`, each 0 to 99 | 126 to 129, PITCH EG RATE 1 to 4 |
| `pitch_eg_levels` | `[u8; 4]`, each 0 to 99 | 130 to 133, PITCH EG LEVEL 1 to 4 |
| `algorithm` | `u8` 0 to 31 | 134, ALGORITHM SELECT |
| `feedback` | `u8` 0 to 7 | 135, FEED BACK |
| `oscillator_sync` | `u8` 0 to 1 | 136, OSCILLATOR SYNC |
| `lfo_speed` | `u8` 0 to 99 | 137, LFO SPEED |
| `lfo_delay` | `u8` 0 to 99 | 138, LFO DELAY |
| `lfo_pitch_depth` | `u8` 0 to 99 | 139, LFO PMD |
| `lfo_amplitude_depth` | `u8` 0 to 99 | 140, LFO AMD |
| `lfo_sync` | `u8` 0 to 1 | 141, LFO SYNC |
| `lfo_wave` | `u8` 0 to 5 | 142, LFO WAVE (0 triangle, 1 sawtooth down, 2 sawtooth up, 3 square, 4 sine, 5 sample and hold) |
| `pitch_sensitivity` | `u8` 0 to 7 | 143, MOD SENSITIVITY PITCH |
| `transpose` | `u8` 0 to 48 | 144, TRANSPOSE (24 none) |
| `name` | `String` of 0 to 10 characters, each U+0020 to U+007E | 145 to 154, VOICE NAME 1 to 10, padded with spaces (0x20) to ten |

`Synth7Operator` MUST have exactly these fields, in each operator's order of parameter offsets 0 to 20:

| Field | Type and range | Offset within the operator; S7-28's name |
|---|---|---|
| `eg_rates` | `[u8; 4]`, each 0 to 99 | 0 to 3, EG RATE 1 to 4 |
| `eg_levels` | `[u8; 4]`, each 0 to 99 | 4 to 7, EG LEVEL 1 to 4 |
| `break_point` | `u8` 0 to 99 | 8, KEYBOARD LEVEL SCALE BREAK POINT |
| `left_depth` | `u8` 0 to 99 | 9, KEYBOARD LEVEL SCALE LEFT DEPTH |
| `right_depth` | `u8` 0 to 99 | 10, KEYBOARD LEVEL SCALE RIGHT DEPTH |
| `left_curve` | `u8` 0 to 3 | 11, KEYBOARD LEVEL SCALE LEFT CURVE (0 −LIN, 1 −EXP, 2 +EXP, 3 +LIN) |
| `right_curve` | `u8` 0 to 3 | 12, KEYBOARD LEVEL SCALE RIGHT CURVE |
| `rate_scaling` | `u8` 0 to 7 | 13, KEYBOARD RATE SCALING |
| `amplitude_sensitivity` | `u8` 0 to 3 | 14, MOD SENSITIVITY AMPLITUDE |
| `velocity_sensitivity` | `u8` 0 to 7 | 15, OPERATOR KEY VELOCITY SENSITIVITY |
| `output_level` | `u8` 0 to 99 | 16, OPERATOR OUTPUT LEVEL |
| `oscillator_mode` | `u8` 0 to 1 | 17, OSCILLATOR MODE (0 ratio, 1 fixed) |
| `frequency_coarse` | `u8` 0 to 31 | 18, OSCILLATOR FREQUENCY COARSE |
| `frequency_fine` | `u8` 0 to 99 | 19, OSCILLATOR FREQUENCY FINE |
| `detune` | `u8` 0 to 14 | 20, DETUNE (7 none) |

The operator switch (voice parameter 155) is not a field of a voice, since no stored voice holds it (S7-30); it is the named parameter `operator_switch` (SRV-28). A name character outside U+0020 to U+007E MUST be refused with `forbidden_character` on the path `name`; a voice given as bytes may carry any name bytes 0 to 127 (S7-32), and they are carried unchanged.
- Reason: These are the adopted interface's voice parameters, every one, with S7-28's ranges, grouped as a program writes a voice. Operator 1 is first because the algorithms are drawn and numbered from operator 1, and a program indexes `operators[0]` as operator 1; the server writes the interface's order (operator 6's parameters first). A name typed in JSON is printable text; any byte of a dump is still carried.
- Source: S7-28, S7-30, S7-31, S7-32; DEC-6462 item 1.
- Verification: A test builds the default voice of S7-51 from fields and checks the 163 bytes of its single-voice dump against S7-38 and the DX7 II manual's values; a test sets each field to its lowest and highest value and checks the parameter number it lands on; each field one above its range is refused `out_of_range` with its path (`patch.operators[2].detune`).

**SRV-27. A synth7 voice as bytes, and a synth7 bank.** `Synth7Patch::Bytes` MUST be exactly the 163 bytes of a single-voice dump (S7-38: `F0 43 0n 00 01 1B`, 155 voice bytes, the checksum, `F7`), any channel `n`, checked by S7-29, S7-38, S7-39 and S7-45 with the engine's own check; any other length, a wrong header, a wrong checksum or a parameter above its range MUST be refused with `invalid_patch`, naming the byte. `Synth7Bank` MUST be either `patches`, a list of 1 to 32 `Synth7Patch`, voice k of the list being program k of the bank (voice k of the 32-voice dump); or `bytes`, exactly the 4,104 bytes of one 32-voice dump (S7-41), any channel, checked by S7-39, S7-41, S7-42 and S7-45 and S7-46 to S7-48 with the engine's check, and refused with `invalid_bank`, naming the voice and the byte, when it fails. A list of more than 32 MUST be refused with `too_long` (DEC-6465 answer 18).
- Reason: S7-37 to S7-42; MIDI-15 (a bank as a list, or as the whole-bank dump); DEC-6465 answer 18.
- Source: S7-29, S7-38, S7-39, S7-41, S7-42, S7-45 to S7-48, S7-55; DEC-6465 answer 18.
- Verification: The tests of S7-41 (each header byte, the length, the checksum and EOX made wrong in turn), run through the server and checking each refusal; a bank of 1 voice and of 32; 33 refused.

**SRV-28. synth7's named parameters.** `Synth7Parameter` MUST have exactly these variants, each holding a `u8` in the range given:
1. for each operator n from 1 to 6 and each of the 21 operator fields of SRV-26, a variant named `op<n>_<field>`, where the field is written `eg_rate_1` to `eg_rate_4` and `eg_level_1` to `eg_level_4` for the two arrays and as SRV-26 names it otherwise (`op1_eg_rate_1`, …, `op6_detune`): 126 variants, voice parameters 0 to 125, operator n's offset f being parameter `(6 − n) × 21 + f`, each with S7-28's range;
2. `pitch_eg_rate_1` to `pitch_eg_rate_4` (126 to 129), `pitch_eg_level_1` to `pitch_eg_level_4` (130 to 133), `algorithm` (134), `feedback` (135), `oscillator_sync` (136), `lfo_speed` (137), `lfo_delay` (138), `lfo_pitch_depth` (139), `lfo_amplitude_depth` (140), `lfo_sync` (141), `lfo_wave` (142), `pitch_sensitivity` (143), `transpose` (144), each with S7-28's range;
3. `name_1` to `name_10` (145 to 154), each 0 to 127;
4. `operator_switch` (155), 0 to 63;
5. the fourteen function parameters of S7-33, each with its range: `mono_poly` (64, 0 to 1), `pitch_bend_range` (65, 0 to 12), `pitch_bend_step` (66, 0 to 12), `portamento_mode` (67, 0 to 1), `glissando` (68, 0 to 1), `portamento_time` (69, 0 to 99), `modulation_wheel_range` (70, 0 to 99), `modulation_wheel_assign` (71, 0 to 7), `foot_controller_range` (72, 0 to 99), `foot_controller_assign` (73, 0 to 7), `breath_controller_range` (74, 0 to 99), `breath_controller_assign` (75, 0 to 7), `after_touch_range` (76, 0 to 99), `after_touch_assign` (77, 0 to 7).
That is 126 + 19 + 10 + 1 + 14 = 170 variants.
- Reason: MIDI-18: every parameter the family's interface changes in real time, by name, its value's range in the schema. The DX7's real-time parameter message covers group 0's voice parameters 0 to 155 and group 2's function parameters 64 to 77 (S7-43), so all of them are named.
- Source: S7-28, S7-33, S7-43; MIDI-18.
- Verification: A test sends every variant at its lowest and highest value and checks the parameter change written (SRV-29); a schema test checks the 170 names and ranges against S7-28 and S7-33 as data.

**SRV-29. What the server writes for synth7.** For an inline `patch` event on channel c the server MUST write one single-voice dump (S7-38) with sub-status byte `0x00 | (c − 1)`, at the event's tick, as one system exclusive event. For a `parameter` event on channel c the server MUST write one parameter change (S7-43): byte 2 `0x10 | (c − 1)`; byte 3 the group (0 for the voice parameters of items 1 to 4 of SRV-28, 2 for the function parameters of item 5) in bits 2 to 6 and the parameter number's two high bits in bits 0 and 1; byte 4 the number's low seven bits; byte 5 the value. When the server builds a single-voice dump or a 32-voice dump it MUST write channel 0 in the dump's sub-status byte and the checksum of S7-39.
- Reason: The adopted interface's own messages for a voice and for one parameter (MIDI-18, MIDI-60); a 32-voice dump's channel addresses nothing on synth7 (S7-42), so the server writes one value for byte-identical banks (MIDI-44).
- Source: S7-38, S7-39, S7-40, S7-42, S7-43, S7-44; MIDI-18, MIDI-44, MIDI-60.
- Verification: A test of one patch event and of one parameter event of each group, checking every byte.

### 3.8 synth106 and synth60

**SRV-30. A synth106 patch as named fields.** `Synth106Patch::Fields` MUST hold `Synth106Panel`, with exactly these fields, each setting the field of S106-22 named in the last column:

| Field | Type and values | Juno-106 parameter (S106-13, S106-18, S106-22) |
|---|---|---|
| `lfo_rate` | `u8` 0 to 127 | 0, LFO rate |
| `lfo_delay` | `u8` 0 to 127 | 1, LFO delay |
| `dco_lfo` | `u8` 0 to 127 | 2, DCO LFO |
| `dco_pwm` | `u8` 0 to 127 | 3, DCO PWM |
| `noise_level` | `u8` 0 to 127 | 4, noise level |
| `vcf_frequency` | `u8` 0 to 127 | 5, VCF cutoff |
| `vcf_resonance` | `u8` 0 to 127 | 6, resonance |
| `vcf_envelope` | `u8` 0 to 127 | 7, VCF ENV |
| `vcf_lfo` | `u8` 0 to 127 | 8, VCF LFO |
| `vcf_keyboard` | `u8` 0 to 127 | 9, VCF KYBD |
| `vca_level` | `u8` 0 to 127 | 10, VCA level |
| `attack` | `u8` 0 to 127 | 11, attack |
| `decay` | `u8` 0 to 127 | 12, decay |
| `sustain` | `u8` 0 to 127 | 13, sustain |
| `release` | `u8` 0 to 127 | 14, release |
| `sub_level` | `u8` 0 to 127 | 15, sub level |
| `range` | `Synth106Range`: `feet_16`, `feet_8`, `feet_4` | 16, bits 2 to 0: `001`, `010`, `100` |
| `pulse` | `bool` | 16, bit 3 |
| `sawtooth` | `bool` | 16, bit 4 |
| `chorus` | `Synth106Chorus`: `off`, `one`, `two` | 16, bits 6 and 5: `x1` off (the server writes `01`), `10` I, `00` II |
| `pwm` | `Synth106Pwm`: `lfo`, `manual` | 17, bit 0: 0 LFO, 1 MAN |
| `envelope_polarity` | `Synth106Polarity`: `positive`, `negative` | 17, bit 1: 0 +, 1 − |
| `vca` | `Synth106Vca`: `envelope`, `gate` | 17, bit 2: 0 ENV, 1 gate |
| `hpf` | `u8` 0 to 3, the panel switch's position | 17, bits 4 and 3: `3 − position` |

The server MUST write chorus off as bits 6 and 5 equal to `01`, and every bit S106-18 says is 0 as 0.
- Reason: S106-36: "the sixteen sliders, each an integer 0 to 127; range, one of 16′, 8′ and 4′; pulse and sawtooth, each on or off; chorus, one of off, I and II; PWM source, LFO or manual; envelope polarity, positive or negative; VCA control, envelope or gate; high-pass filter, an integer 0 to 3", whose spellings are this document's. The names are the patch fields of S106-22 in snake case, with `noise_level` and `sub_level` named for their sliders so that `sub_switch` (SRV-31) is distinct. Writing `01` for chorus off chooses one of the manual's two codings (`x1`) so that a patch has one form.
- Source: S106-13, S106-18, S106-22, S106-36.
- Verification: A test checks the switch bytes for each of the 3 ranges, the 4 combinations of pulse and sawtooth, the 3 chorus values, and the 2 × 2 × 2 × 4 values of byte 17; the decodings of S106-15 as round trips.

**SRV-31. A synth60 patch as named fields.** `Synth60Patch::Fields` MUST hold `Synth60Panel`, with exactly `Synth106Panel`'s fields except that `pwm` is `Synth60Pwm` (`lfo`, `manual`, `envelope`) and `chorus` is `Synth60Chorus` (`off`, `one`, `two`, `both`), and one more field, `sub_switch`: `bool`. From it the server MUST write the 33 bytes of S106-31: the function type `30` message, then `Bn 0F v` (controller 15: 0 for `lfo`, 43 for `manual`, 86 for `envelope`), `Bn 1C v` (controller 28: 0 off, 64 on), `Bn 5D v` (controller 93: 0 `off`, 32 `one`, 64 `two`, 96 `both`), with the 18 values agreeing with the three settings as S106-31 says (the PWM bit 1 for `manual` and `envelope`; chorus bits of II for `both`). On synth60 `range` is the octave transpose switch (S106-22: `feet_16` DOWN, `feet_8` NORMAL, `feet_4` UP).
- Reason: S106-36 (synth60 takes the same fields, with PWM source also envelope, chorus also I+II and a sub-oscillator switch) and S106-31 (the 33-byte form and its canonical values).
- Source: S106-22, S106-24, S106-31, S106-36.
- Verification: The 24 combinations of S106-31's test, built from fields, checked byte for byte.

**SRV-32. synth106 and synth60 patches as bytes, and their banks.** `Synth106Patch::Bytes` MUST be exactly 24 bytes, a function type `30` or `31` message (S106-13, S106-14); `Synth60Patch::Bytes` exactly 33, a function type `30` or `31` message followed by the 9 bytes of S106-31 at canonical values in agreement. Either MUST be refused with `invalid_patch`, naming the byte, when S106-19 would have the instrument ignore it, or (synth60) when the three controller values are not canonical or the 18 values disagree with them (S106-37). `Synth106Bank` and `Synth60Bank` MUST be either `patches`, a list of 1 to 128 patches of that kind, patch k being program k; or `bytes`, 1 to 128 patches' messages back to back (24 bytes each for synth106, 33 for synth60), each a function type `30` message whose byte e is its position k (S106-38); a bank given as bytes whose byte e disagrees with its position, or holding a function type `31` message, MUST be refused with `invalid_bank`, naming the patch. When it builds a bank from `patches`, the server MUST write each patch as a function type `30` message with byte e set to k, whichever function type it was given as.
- Reason: S106-37 and S106-38.
- Source: S106-13, S106-14, S106-16, S106-19, S106-31, S106-37, S106-38.
- Verification: The tests of S106-37 and S106-38, through the server.

**SRV-33. synth106's and synth60's named parameters.** `Synth106Parameter` MUST have one variant for each field of `Synth106Panel`, named as the field and holding the field's type; `Synth60Parameter` one for each field of `Synth60Panel`. The server MUST write:
1. on synth106, for every variant, one function type `32` message (S106-17), byte d the channel less one, byte e the parameter number (0 to 15 for the sliders; 16 for `range`, `pulse`, `sawtooth` and `chorus`; 17 for `pwm`, `envelope_polarity`, `vca` and `hpf`), byte f the value: the slider's value, or the whole switch byte made from the tracked state of the part (SRV-68) with the one field changed;
2. on synth60, for the sliders, the same function type `32` message; for `range`, `pulse`, `sawtooth`, `chorus`, `pwm`, `envelope_polarity`, `vca`, `hpf` and `sub_switch`, the control change of the JU-06A controller S106-22 gives for the field (12, 16, 17, 93, 15, 21, 25, 20 and 28), at the canonical value of the position (S106-24), because a function type `32` message for parameter 16 or 17 on synth60 also resets the synth60 settings it overlaps (S106-32).
- Reason: MIDI-18: the one message the family document names for a parameter's real-time change. The Juno-106's own parameter change is its interface's message for every value; on synth60 it would undo a setting it did not mean to change, so the JU-06A's controllers, which set exactly one field, are used for the switches.
- Source: S106-17, S106-18, S106-22, S106-24, S106-25, S106-32; MIDI-18.
- Verification: For each variant of each kind, a test sends it after a patch with every other field set and checks that exactly that field changed in the receiver's panel and every other is as it was.

### 3.9 synthD

**SRV-34. A synthD patch as named fields.** `SynthDPatch::Fields` MUST hold `SynthDPanel`, with exactly these 42 fields, one for each controller or coarse and fine pair of `synthd.md`, SD-22, which together set the 39 panel controls of SD-17 (each RANGE selector being two fields, its octave controller and its LO/HI controller, as table C of SD-17 carries it). Each field holds the value of its controller or pair as the adopted interface carries it: a pair is a `u16` from 0 to 16,383 (`coarse × 128 + fine`, SD-18); every other field a `u8` from 0 to 127. The meaning of a value is SD-18, SD-19 and SD-20's law. The table is in the order of the patch's bytes:

| Patch bytes (SD-22) | Field | Type | SD-17 control (number) | Controller or pair |
|---|---|---|---|---|
| 0, 1 | `glide` | `u16` 0 to 16,383 | GLIDE (2) | 5 and 37 |
| 2, 3 | `oscillator_2_frequency` | `u16` 0 to 16,383 | Oscillator 2 FREQUENCY (7) | 10 and 42 |
| 4, 5 | `oscillator_3_frequency` | `u16` 0 to 16,383 | Oscillator 3 FREQUENCY (10) | 12 and 44 |
| 6, 7 | `external_input_volume` | `u16` 0 to 16,383 | EXTERNAL INPUT VOLUME (15) | 14 and 46 |
| 8, 9 | `oscillator_1_volume` | `u16` 0 to 16,383 | Mixer VOLUME of oscillator 1 (12) | 15 and 47 |
| 10, 11 | `oscillator_2_volume` | `u16` 0 to 16,383 | Mixer VOLUME of oscillator 2 (13) | 16 and 48 |
| 12, 13 | `oscillator_3_volume` | `u16` 0 to 16,383 | Mixer VOLUME of oscillator 3 (14) | 17 and 49 |
| 14, 15 | `noise_volume` | `u16` 0 to 16,383 | NOISE VOLUME (16) | 18 and 50 |
| 16, 17 | `cutoff_frequency` | `u16` 0 to 16,383 | CUTOFF FREQUENCY (17) | 19 and 51 |
| 18, 19 | `emphasis` | `u16` 0 to 16,383 | EMPHASIS (18) | 21 and 53 |
| 20, 21 | `filter_attack_time` | `u16` 0 to 16,383 | Filter contour ATTACK TIME (20) | 23 and 55 |
| 22, 23 | `filter_decay_time` | `u16` 0 to 16,383 | Filter contour DECAY TIME (21) | 24 and 56 |
| 24, 25 | `filter_sustain_level` | `u16` 0 to 16,383 | Filter contour SUSTAIN LEVEL (22) | 25 and 57 |
| 26, 27 | `amount_of_contour` | `u16` 0 to 16,383 | AMOUNT OF CONTOUR (19) | 27 and 59 |
| 28, 29 | `loudness_attack_time` | `u16` 0 to 16,383 | Loudness contour ATTACK TIME (23) | 28 and 60 |
| 30, 31 | `loudness_decay_time` | `u16` 0 to 16,383 | Loudness contour DECAY TIME (24) | 29 and 61 |
| 32, 33 | `loudness_sustain_level` | `u16` 0 to 16,383 | Loudness contour SUSTAIN LEVEL (25) | 30 and 62 |
| 34 | `glide_switch` | `u8` 0 to 127 | GLIDE switch (38) | 65 |
| 35 | `oscillator_1_range_octave` | `u8` 0 to 127 | Oscillator 1 RANGE (4), its octave | 74 |
| 36 | `oscillator_2_range_octave` | `u8` 0 to 127 | Oscillator 2 RANGE (6), its octave | 75 |
| 37 | `oscillator_3_range_octave` | `u8` 0 to 127 | Oscillator 3 RANGE (9), its octave | 76 |
| 38 | `oscillator_3_control` | `u8` 0 to 127 | OSC. 3 CONTROL (28) | 79 |
| 39 | `oscillator_3_range_lo_hi` | `u8` 0 to 127 | Oscillator 3 RANGE (9), LO or HI | 80 |
| 40 | `external_input_switch` | `u8` 0 to 127 | Mixer switch of the external input (32) | 81 |
| 41 | `oscillator_1_switch` | `u8` 0 to 127 | Mixer switch of oscillator 1 (29) | 82 |
| 42 | `oscillator_2_switch` | `u8` 0 to 127 | Mixer switch of oscillator 2 (30) | 83 |
| 43 | `oscillator_3_switch` | `u8` 0 to 127 | Mixer switch of oscillator 3 (31) | 84 |
| 44 | `noise_switch` | `u8` 0 to 127 | Mixer switch of the noise (33) | 85 |
| 45 | `decay_switch` | `u8` 0 to 127 | DECAY switch (39) | 88 |
| 46, 47 | `tune` | `u16` 0 to 16,383 | TUNE (1) | 89 and 90 |
| 48 | `modulation_mix` | `u8` 0 to 127 | MODULATION MIX (3) | 102 |
| 49 | `oscillator_1_range_lo_hi` | `u8` 0 to 127 | Oscillator 1 RANGE (4), LO or HI | 103 |
| 50 | `oscillator_1_waveform` | `u8` 0 to 127 | Oscillator 1 WAVEFORM (5) | 104 |
| 51 | `oscillator_2_range_lo_hi` | `u8` 0 to 127 | Oscillator 2 RANGE (6), LO or HI | 105 |
| 52 | `oscillator_2_waveform` | `u8` 0 to 127 | Oscillator 2 WAVEFORM (8) | 106 |
| 53 | `oscillator_3_waveform` | `u8` 0 to 127 | Oscillator 3 WAVEFORM (11) | 107 |
| 54 | `main_output_volume` | `u8` 0 to 127 | Main output VOLUME (26) | 108 |
| 55 | `oscillator_modulation` | `u8` 0 to 127 | OSCILLATOR MODULATION (27) | 109 |
| 56 | `noise_colour` | `u8` 0 to 127 | Noise WHITE / PINK (34) | 110 |
| 57 | `filter_modulation` | `u8` 0 to 127 | FILTER MODULATION (35) | 111 |
| 58 | `keyboard_control_1` | `u8` 0 to 127 | KEYBOARD CONTROL 1 (36) | 112 |
| 59 | `keyboard_control_2` | `u8` 0 to 127 | KEYBOARD CONTROL 2 (37) | 113 |

The server MUST write a pair's coarse byte as `floor(value ÷ 128)` and its fine byte as `value mod 128`, and MUST write the 60 bytes in the order of SD-22.
- Reason: synthD has no patch format anywhere; its patch is its interface's control values (decision A4, SD-22), so the named fields are those values by name, which round-trip exactly with the 60 bytes. A RANGE selector is two controllers on the Voyager's map (its octave and its LO/HI), and a field for each keeps the fields one for one with the controllers. DEC-6477 (server answer 1) keeps the fields raw controller values rather than typed positions.
- Source: SD-17, SD-18, SD-21, SD-22, SD-26; DEC-6476 (the Voyager's map adopted); DEC-6477.
- Verification: A test decodes SD-21's default patch from its 60 bytes into fields and back; for every field, its lowest and highest value land on the bytes the table names.

**SRV-35. A synthD patch as bytes, and a synthD bank.** `SynthDPatch::Bytes` MUST be exactly 60 bytes, each 0 to 127 (SD-22), carried unchanged; a byte of 128 or more, or another length, MUST be refused with `invalid_patch`. `SynthDBank` MUST be either `patches`, a list of 1 to 128 `SynthDPatch`; or `bytes`, 1 to 128 patches of 60 bytes back to back (a length that is a multiple of 60, at most 7,680), patch k at byte `k × 60` (SD-27, MIDI-56 item 2), refused with `invalid_bank` when its length is not a multiple of 60 or a byte is 128 or more.
- Reason: SD-22, SD-27, MIDI-56.
- Source: SD-22, SD-27; MIDI-56.
- Verification: A test of a bank of 1 and of 128 patches in both forms; 129 refused; 61 bytes refused.

**SRV-36. synthD's named parameters.** `SynthDParameter` MUST have one variant for each field of `SynthDPanel`, named as the field and holding its type. The server MUST write a `u8` field as the control change of its controller, and a `u16` field as the two control changes of its pair, coarse then fine, at one tick (MIDI-37 (b), MIDI-75).
- Reason: SD-17: each control is moved by its controller or pair and no other message; MIDI-18.
- Source: SD-17, SD-18; MIDI-18, MIDI-37, MIDI-75.
- Verification: A test sends every variant and checks the control changes written.

### 3.10 synth53, synth52 and synth51

**SRV-37. A synth53 program as named fields.** `Synth53Patch::Fields` MUST hold `Synth53Program`, with exactly these 57 fields, which carry the 66 program parameters other than parameter 20 (the ten UNISON NOTE parameters in one list), each an integer in its parameter's stated range (S53-27; `synth53-synth52-synth51.md` section 6.3), named as S53-47 says (the interface's parameter names in lower case, words joined by underscores, "ON/OFF" left out, ">" written `to`, the document's misprints corrected, the ten UNISON NOTE parameters one list):

| Field | Type and range | Parameter |
|---|---|---|
| `osc_a_frequency` | `u8` 0 to 120 | 0 |
| `osc_b_frequency` | `u8` 0 to 120 | 1 |
| `osc_b_fine_tune` | `u8` 0 to 127 | 2 |
| `osc_a_saw` | `u8` 0 to 1 | 3 |
| `osc_a_square` | `u8` 0 to 1 | 4 |
| `osc_b_saw` | `u8` 0 to 1 | 5 |
| `osc_b_tri` | `u8` 0 to 1 | 6 |
| `osc_b_square` | `u8` 0 to 1 | 7 |
| `osc_a_pulse_width` | `u8` 0 to 120 | 8 |
| `osc_b_pulse_width` | `u8` 0 to 120 | 9 |
| `osc_sync` | `u8` 0 to 1 | 10 |
| `osc_b_low_freq` | `u8` 0 to 1 | 11 |
| `osc_b_keyboard` | `u8` 0 to 1 | 12 |
| `glide_rate` | `u8` 0 to 120 | 13 |
| `osc_a_level` | `u8` 0 to 120 | 14 |
| `osc_b_level` | `u8` 0 to 120 | 15 |
| `noise_level` | `u8` 0 to 120 | 16 |
| `cutoff` | `u8` 0 to 120 | 17 |
| `resonance` | `u8` 0 to 120 | 18 |
| `filter_keyboard_track` | `u8` 0 to 2 | 19 |
| `lfo_frequency` | `u8` 0 to 120 | 21 |
| `lfo_initial_amount` | `u8` 0 to 120 | 22 |
| `lfo_saw` | `u8` 0 to 1 | 23 |
| `lfo_tri` | `u8` 0 to 1 | 24 |
| `lfo_square` | `u8` 0 to 1 | 25 |
| `lfo_source_mix` | `u8` 0 to 120 | 26 |
| `lfo_freq_a` | `u8` 0 to 1 | 27 |
| `lfo_freq_b` | `u8` 0 to 1 | 28 |
| `lfo_freq_pw_a` | `u8` 0 to 1 | 29 |
| `lfo_freq_pw_b` | `u8` 0 to 1 | 30 |
| `lfo_filter` | `u8` 0 to 1 | 31 |
| `poly_mod_filt_env_amount` | `u8` 0 to 127 | 32 |
| `poly_mod_osc_b_amount` | `u8` 0 to 120 | 33 |
| `poly_mod_freq_a` | `u8` 0 to 1 | 34 |
| `poly_mod_pw` | `u8` 0 to 1 | 35 |
| `poly_mod_filter` | `u8` 0 to 1 | 36 |
| `vintage` | `u8` 0 to 127 | 37 |
| `aftertouch_to_filter` | `u8` 0 to 1 | 38 |
| `aftertouch_to_lfo` | `u8` 0 to 1 | 39 (printed "AMP", S53's contradiction C1) |
| `env_filter_amount` | `u8` 0 to 120 | 40 |
| `velocity_to_filter` | `u8` 0 to 1 | 41 (printed "VELOCTIY") |
| `velocity_to_amp` | `u8` 0 to 1 | 42 |
| `attack_filter` | `u8` 0 to 120 | 43 |
| `attack_vca` | `u8` 0 to 120 | 44 |
| `decay_filter` | `u8` 0 to 120 | 45 |
| `decay_vca` | `u8` 0 to 120 | 46 |
| `sustain_filter` | `u8` 0 to 120 | 47 |
| `sustain_vca` | `u8` 0 to 120 | 48 |
| `release_filter` | `u8` 0 to 120 | 49 |
| `release_vca` | `u8` 0 to 120 | 50 |
| `release_switch` | `u8` 0 to 1 | 51 |
| `unison` | `u8` 0 to 1 | 52 |
| `unison_voice_count` | `u8` 0 to 10 | 53 |
| `unison_detune` | `u8` 0 to 7 | 54 |
| `unison_notes` | `[u8; 10]`, each 0 to 10 | 55 to 64, in order |
| `pitch_wheel_range` | `u8` 0 to 11 | 86 |
| `retrigger_and_unison` | `u8` 0 to 3 | 87 |

Parameter 20, FILTER REV SELECT, MUST NOT be a field: from fields the server MUST write it as 1 for a patch of a `synth53` kind and 0 for one of a `synth52` or `synth51` kind (S53-38). The server MUST write bytes 65 to 85 and 88 to 127 of the 128-byte program as 0 (S53-33). `unison_notes`' entries are checked against their maximum only, as S53-33 says the server does (a 0 is accepted).
- Reason: S53-47 asks for named fields under these naming rules; the server document gives the exact schema. Parameter 20 is left out of the fields because DEC-6461 item 3 leaves no revision field for a program to set and S53-38 has the writer write it from the kind, so a field would be one the server overwrites.
- Source: S53-27, S53-33, S53-38, S53-47; section 6.3 of the family document.
- Verification: A test builds S53-30's default program from fields for each kind and checks the 128 bytes (parameter 20 per kind); each field one above its maximum refused `out_of_range` with its path.

**SRV-38. A synth53 program as bytes, and a synth53 bank.** `Synth53Patch::Bytes` MUST be exactly the 157 bytes of an edit buffer dump (`F0 01 31 03`, 152 packed bytes, `F7`; S53-29), unpacked and checked by S53-31 and S53-33 with the engine's check (every parameter within its maximum, every reserved and padding byte 0; parameter 20 either value, S53-38), and refused with `invalid_patch`, naming the parameter, when it fails. `Synth53Bank` MUST be either `patches`, `{ "form": "patches", "group": g, "patches": [ … ] }`, `group` a `u8` 0 to 9 and 1 to 40 `Synth53Patch`, patch k being program k of group g; or `bytes`, 1 to 40 program dumps of 159 bytes back to back (`F0 01 31 02`, group, program, 152 packed bytes, `F7`; S53-28), every one of the same group and each of a different program number, refused with `invalid_bank`, naming the dump, when two groups or a repeated program appear or a dump fails S53-28 or S53-33. When it builds a bank from `patches` the server MUST write each program as a program dump carrying `g` and its position k, packed by S53-32.
- Reason: S53-26 (a), S53-28, S53-29, S53-47.
- Source: S53-25, S53-26, S53-28, S53-29, S53-31, S53-32, S53-33, S53-38, S53-47.
- Verification: The tests of S53-28 and S53-29 through the server; a bank of 40 programs of group 3 in both forms gives identical records; a bank given as bytes with two groups is refused.

**SRV-39. synth53's named parameters.** `Synth53Parameter` MUST have one variant for each field of `Synth53Program` except `unison_notes`, named as the field and holding its type and range, and ten variants `unison_note_1` to `unison_note_10` (parameters 55 to 64, each 0 to 10): 56 + 10 = 66 variants, one for each program parameter but parameter 20. The server MUST write each as the parameter's NRPN sequence: controllers 99 and 98 the parameter number's high and low seven bits, then 6 and 38 the value's high and low seven bits, at one tick (MIDI-37 (c)).
- Reason: The adopted interface prefers NRPN for every program parameter ("NRPNs are the preferred method … since they cover the complete range of all parameters", Prophet-5 MIDI, page 1; MIDI-72); MIDI-18.
- Source: S53-22, S53-23; MIDI-18, MIDI-37, MIDI-72.
- Verification: A test sends every variant and checks the four control changes written.

### 3.11 synth8

**SRV-40. A synth8 patch as named fields.** `Synth8Patch::Fields` MUST hold `Synth8Panel`, with exactly these 42 fields, each a `u8` 0 to 127, the value of the controller `synth8.md`, S8-23, gives, its meaning the law of S8-21 and S8-30:

| Byte | Field | Panel control, controller |
|---|---|---|
| 0 | `lfo_rate` | LFO RATE, 29 |
| 1 | `lfo_delay_time` | LFO DELAY TIME, 27 |
| 2 | `lfo_waveform` | LFO WAVE FORM, 35 |
| 3 | `vco_lfo_mod` | VCO LFO MOD, 26 |
| 4 | `vco_env_mod` | VCO ENV MOD, 25 |
| 5 | `vco_modulator` | VCO MODULATOR switch, 60 |
| 6 | `pulse_width_mod` | PULSE WIDTH MOD, 18 |
| 7 | `pulse_width_mod_source` | PULSE WIDTH MOD source, 19 |
| 8 | `cross_mod` | CROSS MOD, 59 |
| 9 | `vco1_range` | VCO-1 RANGE, 20 |
| 10 | `vco1_waveform` | VCO-1 WAVEFORM, 46 |
| 11 | `vco2_sync` | VCO-2 SYNC, 87 |
| 12 | `vco2_low_freq` | VCO-2 NORMAL / LOW FREQ switch, 57 |
| 13 | `vco2_range` | VCO-2 RANGE, 62 (controller 63 also moves it, S8-16) |
| 14 | `vco2_fine_tune` | VCO-2 FINE TUNE, 56 |
| 15 | `vco2_waveform` | VCO-2 WAVEFORM, 61 |
| 16 | `vco1_level` | VCO-1 LEVEL, 16 |
| 17 | `vco2_level` | VCO-2 LEVEL, 17 |
| 18 | `hpf_cutoff` | HPF CUTOFF, 79 |
| 19 | `vcf_cutoff` | VCF CUTOFF, 3 |
| 20 | `vcf_resonance` | VCF RESONANCE, 9 |
| 21 | `vcf_slope` | VCF SLOPE, 13 |
| 22 | `vcf_env_mod` | VCF ENV MOD, 81 |
| 23 | `vcf_envelope_select` | VCF ENVELOPE SEL, 84 |
| 24 | `vcf_lfo_mod` | VCF LFO MOD, 28 |
| 25 | `vcf_key_follow` | VCF KEY FOLLOW, 82 |
| 26 | `vca_level` | VCA LEVEL, 110 |
| 27 | `vca_lfo_mod` | VCA LFO MOD, 109 |
| 28 | `env1_attack` | ENV-1 ATTACK, 83 |
| 29 | `env1_decay` | ENV-1 DECAY, 80 |
| 30 | `env1_sustain` | ENV-1 SUSTAIN, 85 |
| 31 | `env1_release` | ENV-1 RELEASE, 86 |
| 32 | `env1_polarity` | ENV-1 POLARITY, 106 |
| 33 | `env2_attack` | ENV-2 ATTACK, 89 |
| 34 | `env2_decay` | ENV-2 DECAY, 90 |
| 35 | `env2_sustain` | ENV-2 SUSTAIN, 102 |
| 36 | `env2_release` | ENV-2 RELEASE, 103 |
| 37 | `assign_mode` | ASSIGN MODE, 119 |
| 38 | `env1_key_follow` | ENV-1 KEY FOLLOW, 104 |
| 39 | `env2_key_follow` | ENV-2 KEY FOLLOW, 105 |
| 40 | `vco1_bend` | VCO-1 BEND, 107 (NeoTeletext's own) |
| 41 | `vco2_bend` | VCO-2 BEND, 108 (NeoTeletext's own) |

- Reason: synth8 has no patch format anywhere; its patch is the list of its controllers' values (decision A4, S8-23), so the named fields are those values by name.
- Source: S8-16, S8-21, S8-23, S8-30; DEC-6476 (controller 57 is the VCO-2 NORMAL / LOW FREQ switch, controller 63 a second controller of the RANGE knob).
- Verification: A test decodes S8-22's default patch from its 42 bytes into fields and back.

**SRV-41. A synth8 patch as bytes, and a synth8 bank.** `Synth8Patch::Bytes` MUST be exactly 42 bytes, each 0 to 127, carried unchanged, else refused with `invalid_patch`. `Synth8Bank` MUST be either `patches`, 1 to 64 `Synth8Patch`; or `bytes`, 1 to 64 patches of 42 bytes back to back (a multiple of 42, at most 2,688), refused with `invalid_bank` otherwise (S8-29 (a)).
- Reason: S8-23, S8-29.
- Source: S8-23, S8-29; MIDI-56.
- Verification: A bank of 1 and of 64 patches in both forms; 65 refused.

**SRV-42. synth8's named parameters.** `Synth8Parameter` MUST have one variant for each field of `Synth8Panel`, named as the field, each a `u8` 0 to 127. The server MUST write each as the control change of its controller on the event's channel, which MUST be 1 (the upper half) or 2 (the lower half); a `patch` or `parameter` event on channels 3 to 16 MUST be refused with `not_taken` (S8-2). An inline `patch` event MUST be written as the 42 control changes of S8-27, in byte order, on its channel, at one tick.
- Reason: S8-2, S8-16, S8-27; MIDI-18, MIDI-60, MIDI-70.
- Source: S8-2, S8-16, S8-27; MIDI-70.
- Verification: A test sends every variant on channels 1 and 2 and checks the control change; on channel 3 checks the refusal.

### 3.12 synth80

**SRV-43. A synth80 patch as named fields, and the preset tones.** `Synth80Patch::Fields` MUST hold `Synth80Panel`, with exactly these fields: `channel_1` and `channel_2`, each a `Synth80Tone`; and the 33 master fields below, each a `u8` 0 to 127, the value of the controller `synth80.md`, S80-33, gives. `Synth80Tone` MUST be an internally tagged enum (`tag = "form"`) of two variants: `fields`, a `Synth80ToneFields` of the 26 fields below; and `preset`, `{ "form": "preset", "name": … }`, `name` a `Synth80Preset`, one of the 22 preset tones of S80-42, whose 26 values the server takes from the engine's `presets::PRESETS` (S80-42). A preset MUST be accepted for either channel (S80-42: "MAY be accepted for the other").

`Synth80ToneFields`, each `u8` 0 to 127 (bytes 0 to 25 for channel I, 26 to 51 for channel II; controllers of S80-10 for channel I and channel II):

| Field | Control | Ch. I byte, controller | Ch. II byte, controller |
|---|---|---|---|
| `pwm_speed` | PWM SPEED | 0, 40 | 26, 67 |
| `pwm` | PWM | 1, 41 | 27, 68 |
| `pw` | PW | 2, 42 | 28, 69 |
| `square` | Square wave switch | 3, 43 | 29, 70 |
| `sawtooth` | Sawtooth wave switch | 4, 44 | 30, 71 |
| `noise` | NOISE | 5, 45 | 31, 72 |
| `hpf` | HPF | 6, 46 | 32, 73 |
| `hpf_resonance` | RESh | 7, 47 | 33, 119 |
| `lpf` | LPF | 8, 48 | 34, 75 |
| `lpf_resonance` | RESl | 9, 49 | 35, 76 |
| `filter_initial_level` | IL (filter envelope's initial level) | 10, 50 | 36, 77 |
| `filter_attack_level` | AL (filter envelope's attack level) | 11, 51 | 37, 78 |
| `filter_attack` | Filter envelope A | 12, 52 | 38, 79 |
| `filter_decay` | Filter envelope D | 13, 53 | 39, 80 |
| `filter_release` | Filter envelope R | 14, 54 | 40, 81 |
| `vcf_level` | VCF LEVEL | 15, 55 | 41, 82 |
| `sine` | SINE | 16, 56 | 42, 83 |
| `amplifier_attack` | Amplifier envelope A | 17, 57 | 43, 84 |
| `amplifier_decay` | Amplifier envelope D | 18, 58 | 44, 85 |
| `amplifier_sustain` | Amplifier envelope S | 19, 59 | 45, 86 |
| `amplifier_release` | Amplifier envelope R | 20, 60 | 46, 87 |
| `level` | LEVEL | 21, 61 | 47, 88 |
| `initial_brilliance` | INITIAL BRILLIANCE | 22, 62 | 48, 89 |
| `initial_level` | INITIAL LEVEL | 23, 63 | 49, 90 |
| `after_brilliance` | AFTER BRILLIANCE | 24, 65 | 50, 91 |
| `after_level` | AFTER LEVEL | 25, 66 | 51, 92 |

The master fields of `Synth80Panel`, each `u8` 0 to 127:

| Byte | Field | Control, controller |
|---|---|---|
| 52 | `feet_1` | FEET I, 102 |
| 53 | `feet_2` | FEET II, 103 |
| 54 | `detune_channel_2` | DETUNE CH II, 95 |
| 55 | `mix` | MIX I-II, 8 |
| 56 | `brilliance` | BRILLIANCE, 109 |
| 57 | `resonance` | RESONANCE, 110 |
| 58 | `keyboard_brilliance_low` | KEYBOARD CONTROL BRILLIANCE LOW, 115 |
| 59 | `keyboard_brilliance_high` | KEYBOARD CONTROL BRILLIANCE HIGH, 116 |
| 60 | `keyboard_level_low` | KEYBOARD CONTROL LEVEL LOW, 117 |
| 61 | `keyboard_level_high` | KEYBOARD CONTROL LEVEL HIGH, 118 |
| 62 | `sub_oscillator_function` | SUB OSCILLATOR FUNCTION, 104 |
| 63 | `sub_oscillator_speed` | SUB OSCILLATOR SPEED, 105 |
| 64 | `sub_oscillator_vco` | SUB OSCILLATOR VCO, 106 |
| 65 | `sub_oscillator_vcf` | SUB OSCILLATOR VCF, 107 |
| 66 | `sub_oscillator_vca` | SUB OSCILLATOR VCA, 108 |
| 67 | `touch_pitch_bend` | TOUCH RESPONSE PITCHBEND, 111 |
| 68 | `touch_speed` | TOUCH RESPONSE SPEED, 112 |
| 69 | `touch_vco` | TOUCH RESPONSE VCO, 113 |
| 70 | `touch_vcf` | TOUCH RESPONSE VCF, 114 |
| 71 | `ring_modulator_attack_time` | RING MODULATOR ATTACK TIME, 20 (NeoTeletext's own) |
| 72 | `ring_modulator_decay_time` | RING MODULATOR DECAY TIME, 21 (NeoTeletext's own) |
| 73 | `ring_modulator_depth` | RING MODULATOR DEPTH, 22 (NeoTeletext's own) |
| 74 | `ring_modulator_speed` | RING MODULATOR SPEED, 23 (NeoTeletext's own) |
| 75 | `ring_modulator_modulation` | RING MODULATOR MODULATION, 24 (NeoTeletext's own) |
| 76 | `sustain_mode` | SUSTAIN I-II, 25 (NeoTeletext's own) |
| 77 | `sustain` | SUSTAIN, 26 (NeoTeletext's own) |
| 78 | `glide_mode` | PORTAMENTO/GLISSANDO selector, 3 (NeoTeletext's own; the adopted table's 120, S80-20) |
| 79 | `glide_speed` | PORTAMENTO/GLISSANDO speed, 5 |
| 80 | `tremolo_chorus` | TREMOLO/CHORUS ON/OFF, 27 (NeoTeletext's own) |
| 81 | `chorus` | CHORUS, 28 (NeoTeletext's own) |
| 82 | `tremolo` | TREMOLO, 29 (NeoTeletext's own) |
| 83 | `tremolo_chorus_speed` | TREMOLO/CHORUS SPEED, 30 (NeoTeletext's own) |
| 84 | `tremolo_chorus_depth` | TREMOLO/CHORUS DEPTH, 31 (NeoTeletext's own) |

`Synth80Preset` MUST be exactly these 22 values, from S80-42's lists: channel I's row `string_1`, `string_3`, `brass_1`, `flute`, `electric_piano`, `clavichord_1`, `harpsichord_1`, `organ_1`, `guitar_1`, `funky_1`, `funky_3`; channel II's row `string_2`, `string_4`, `brass_2`, `brass_3`, `bass`, `clavichord_2`, `harpsichord_2`, `organ_2`, `guitar_2`, `funky_2`, `funky_4`.
- Reason: S80-41 (e): one name for each of the 85 controls, the names being this document's; S80-42: a channel's 26 tone values from the name of any preset tone, through the server; S80-43: a patch built from two tones. A tone is an object of its own so that a preset can stand in its place. The fields are the controllers' values, as for synthD and synth8.
- Source: S80-10, S80-11, S80-18, S80-20, S80-33, S80-41, S80-42, S80-43.
- Verification: The test of S80-42 ("BRASS 1" for channel I and "BRASS 3" for channel II, bytes 0 to 25 and 26 to 51 equal to the two `PRESETS` tones); S80-45's default patch from fields equals its 85 bytes.

**SRV-44. A synth80 patch as bytes, and a synth80 bank.** `Synth80Patch::Bytes` MUST be exactly 85 bytes, each 0 to 127, carried unchanged, else refused with `invalid_patch`. `Synth80Bank` MUST be either `patches`, 1 to 128 `Synth80Patch`; or `bytes`, 1 to 128 patches of 85 bytes back to back (at most 10,880), refused with `invalid_bank` otherwise (S80-41 (a)).
- Reason: S80-33, S80-41.
- Source: S80-33, S80-41; MIDI-56.
- Verification: A bank of 1 and of 128 patches in both forms; 129 refused.

**SRV-45. synth80's named parameters.** `Synth80Parameter` MUST have one variant for each master field of `Synth80Panel`, named as the field, and one for each tone field of each channel, named `channel_1_<field>` and `channel_2_<field>`: 33 + 52 = 85 variants, each a `u8` 0 to 127. The server MUST write each as the control change of its controller. An inline `patch` event MUST be written as the 85 control changes of S80-40, in byte order, at one tick.
- Reason: S80-10, S80-11, S80-18, S80-20, S80-40; MIDI-18, MIDI-60.
- Source: The same.
- Verification: A test sends every variant and checks the control change.

### 3.13 Play, stop and gain

**SRV-46. The commands are unchanged.** `play` (`PlaySound`), `stop` (`StopSound`) and `gain` (`GainSound`) MUST keep in protocol 13 exactly the fields, types, bounds and meanings they have in protocol 12: `connections`; `channel`, the audio channel, 0 to 3; for `play`, `handle`, `generation`, `gain` 0 to 100, `fade_ms` `u16`, `loop` `bool`, `after` `bool`, `duck` 0 to 6, `page` `Option<PageNumber>`; for `stop`, `fade_ms`; for `gain`, `gain` and `fade_ms`. A `play` of a handle that holds a bank in the server's bank table MUST be refused with `not_listed` on the path `handle`, detail "MIDI-55: a bank is never played".
- Reason: DEC-6462 item 1 ("the audio profile's play, stop and gain") and the brief: as today. A bank played would be ignored and counted by the receiver (MIDI-55); the server knows it is a bank and says so.
- Source: `protocol.rs` (`PlaySound`, `StopSound`, `GainSound`); MIDI-55.
- Verification: The existing tests of the three commands; a test plays a bank's handle and checks the refusal.

### 3.14 What the server tells the program

**SRV-47. `sound_built`.** `ServerMessage` MUST gain one variant, `SoundBuilt(SoundBuilt)`, `type` `sound_built`, sent to the program once for every stored synthesizer sound the server has accepted and sent, after its records have been given to every connection named, naming the sound it concerns by its kind, handle and generation (DEC-6477 typescript answer 3), with exactly these fields:
- `kind`: the stored sound's kind, as a string of the 11 stored kinds;
- `handle`: `u8`; `generation`: `u16`;
- `blocks`: `u16`, 1 to 6,000, the blocks of the sound;
- `bytes`: `u32`, 0 to 960,000, the total bytes of its blocks (MIDI-41's tag 8);
- `longest_block`: `u16`, 0 to 1,005, the OBJECT's block bytes field (MIDI-40);
- `banks_lifted`: a list of the `BankName`s of the banks lifted from its music (SRV-15), in order;
- `dropped`: `DroppedCounts`, the counts of what a Standard MIDI File held that the server dropped (MIDI-118), each a `u32`: `not_taken` (messages the family document does not list), `unmapped_channel` (messages of a channel the channel map maps to none), `system_messages` (system common and real-time messages inside `F7` escape events), `escapes` (other `F7` escape events), `meta_events` (meta events other than set tempo and end of track); every count 0 for a sound given as events.
It MUST NOT be sent for a live sound, an events message or a bank.
- Reason: MIDI-118 requires the server to report to the program how many of each kind it dropped from a file; a stored sound's blocks and bytes are what the server computed and the program cannot know, and a program measuring its sounds against a receiver's store needs them. One answer for every stored sound gives a program a uniform acknowledgement.
- Source: MIDI-41, MIDI-58, MIDI-118; the kit's `MidiDropped` as built; DEC-6477.
- Verification: A test of a sound given as events (counts 0, blocks and bytes checked) and of a file with one message of each dropped kind (the counts checked).

**SRV-48. `refused` names the sound it refuses.** `Refused` MUST keep its fields (`message`, `path`, `rule`, `detail`, `request`) and MUST gain one more, `sound`: `Option<RefusedSound>`, default none, where `RefusedSound` is a struct of exactly `kind`: `SoundKind`, the closed list of every `kind` of the `Sound` enum (the 42 synthesizer kinds of SRV-3 and the nine of SRV-46's Opus, PCM and commands); `handle`: `Option<u8>`; and `generation`: `Option<u16>`. For a refused `sound` message the server MUST set `sound` whenever the line is a JSON object whose `kind` is one of the closed list, with `handle` and `generation` given where the line holds them as integers within their types, whatever the fault and wherever it lies; it MUST leave `sound` none when the line is not a JSON object or its `kind` is missing or not listed, and for every message that is not a `sound`. A refused sound message carries `message` `sound` and `request` none. No sound message carries a request number, and the server MUST NOT answer an accepted sound message other than by `sound_built` (SRV-47).
- Reason: The existing typed refusal (REQ-1475), which DEC-6462 item 2 takes as the example. A program writes several sound messages together, and without a name it cannot tell which of them a refusal concerns; DEC-6477 (typescript answer 3) keeps sound calls unanswered and has every refusal and every `sound_built` name the sound, so that a program matches them by kind, handle and generation.
- Source: `protocol.rs` (`Refused`); DEC-6477; `typescript.md` TS-24; `python.md` PY-34.
- Verification: The existing refusal tests; a test refuses a synth7 stored sound at its last event and checks `sound` is `{"kind": "synth7", "handle": 8, "generation": 0}`; a test refuses a `stop` (no handle) and checks `sound` names the kind alone; a test of a line whose `kind` is not listed checks `sound` is none.

---

## 4. The server's work

### 4.1 Validation and typed refusals

**SRV-49. The order of reading and checking.** The server MUST handle a sound message of a synthesizer kind in this order, and MUST stop at the first fault, refusing the message whole: (1) read it serde-strict through `protocol/read.rs`, following `type`, then `kind`, then each `event`, `form` and externally tagged parameter to its own type, so that an unknown field, a missing field, a wrong type and a value outside a schema range are refused with the path serde gives (`unknown_field`, `missing_field`, `wrong_type`, `not_listed`, `out_of_range`); (2) check every rule a schema cannot state, in `protocol/check.rs` and its sound module, field by field in the order of the message; (3) build: pack patches, build bank images, read a Standard MIDI File, place events and write blocks, restatements and records, through the engine's functions (SRV-87); (4) check everything built with the engine's receiver-side checks (SRV-54); (5) only then change the bank table or the live table and send records.
- Reason: REQ-1475: a faulty message is refused whole, with the path of its first fault; a message the server refuses must leave nothing sent and nothing changed (MIDI-13, MIDI-21).
- Source: `protocol/read.rs`, `protocol/check.rs`; REQ-1475; MIDI-21.
- Verification: A test sends a stored sound whose last event is faulty and checks that no record was sent and the bank table is unchanged; a test of a live events message refused at its last event checks the live table unchanged and the next message accepted as if the refused one had not come.

**SRV-50. A refusal names the path, the rule and the detail.** Every refusal of this document MUST carry: `path`, the path from the message's root to the field at fault, in the protocol's form (`music.events[1204].velocity`, `bank.patches[3].operators[0].detune`, `music.bytes`, `until_us`, `banks[2]`), or the message's root (empty) when the fault is the message as a whole; `rule`, one value of `Rule` (SRV-51); `detail`, which MUST begin with the requirement broken (`MIDI-28:`, `S7-39:`, `SRV-74:`) and then say the fault in words with the values that locate it: for an event its index and its `time_us`, and once placed, its block and tick; for a patch its byte offset and value, or its parameter's name; for a bank the patch's index and byte; for a Standard MIDI File the track's index, the event's index within the track and the byte offset in the file.
- Reason: MIDI-21: a refusal names the path of the field at fault, the rule broken (citing the requirement) and the detail. Naming the requirement lets an author find the rule in these documents without a copy of it in any kit.
- Source: MIDI-21; DEC-6462 item 2; S6581-54.
- Verification: Each refusal test of this document asserts the path, the rule and the requirement at the start of the detail.

**SRV-51. The rules this document adds.** `Rule` MUST gain exactly these values, each with the doc comment the table gives, and the server MUST use each for exactly the faults its row names. The existing values keep their meanings and are used here as the table's last rows say.

| `Rule` value | The fault | Requirements |
|---|---|---|
| `not_taken` | A MIDI message the family of the sound's kind does not act on: a status, controller, parameter number, program number, channel or system exclusive message the family document does not list for its part; an ASID command other than 0x4C, 0x4D and 0x4E | MIDI-10, MIDI-67, MIDI-80; S6581-54 item 3; each family's list of messages |
| `never_carried` | A message MIDI-8 lists as never carried in a block, given as an event: timing clock, start, continue, stop, active sensing, system reset, time code, song position, song select, tune request, an undefined status, local control (controller 122) | MIDI-8 |
| `malformed_midi` | Bytes that are not whole MIDI messages: a data byte of 0x80 or above inside a message, a channel message cut short, a system exclusive message not ending with `0xF7` or holding a byte of 0x80 or above before it, an ASID payload breaking S6581-10 to S6581-14 or S6581-18 | MIDI-11, MIDI-26, MIDI-27; S6581-5, S6581-54 items 1, 2, 4 and 5 |
| `running_status` | A data byte where a status byte is expected and no running status is in effect | MIDI-12; SRV-13 |
| `system_exclusive_too_long` | A system exclusive message of more than 256 bytes after `0xF0` in the music, that is not a bank dump the server lifts | MIDI-28, MIDI-51 |
| `block_full` | A block that would hold more than 1,005 bytes or 256 events, or for the synth6581 family more than 20 register data messages or more than one start or one stop message | MIDI-30, MIDI-31; S6581-42, S6581-54 item 7 |
| `no_room_to_restate` | Fifty blocks pass without room for a part's restatement | MIDI-98 |
| `beyond_length` | An event in a block at or past the stored sound's block count; a sound needing more than 6,000 blocks or 960,000 bytes | MIDI-17, MIDI-19, MIDI-104; SRV-8, SRV-9 |
| `late_event` | An event of an events message whose block the server has already sent | MIDI-20 |
| `not_before_until` | An event of an events message whose `time_us` is not less than the message's `until_us` | SRV-74 |
| `until_moved_back` | An events message whose `until_us` is less than the live sound's last `until_us` | SRV-74 |
| `advance_too_far` | An events message that advances `until_us` by more than 2,000,000 microseconds | MIDI-20 |
| `unknown_live_sound` | An events message for a handle and generation the live table does not hold as a live sound of the message's kind | SRV-72 |
| `live_sound_changed` | A live sound announced again with the handle and generation of the live sound the server holds, but a different kind, clock, key mode, split key or list of banks | SRV-73 |
| `no_opening_update` | A synth6581 or synth8580 sound whose first event is not a full register update at tick 0 | S6581-45, S6581-54 item 8; SRV-25 |
| `invalid_patch` | A patch, given in a bank list, as a patch event, as bytes, or met as an inline patch message in the music, that the family's check refuses: a wrong length, header, checksum, byte or parameter out of its range, a synth60 controller value not canonical or not agreeing | MIDI-21, MIDI-63; each family's patch rules |
| `invalid_bank` | A bank image that the family's bank check refuses, or that holds a message not of its form, or numbers its patches other than by position where the family requires it | MIDI-53, MIDI-56; S7-41, S106-38, S53-26, S8-29, S80-41, SD-27 |
| `unknown_bank` | A sound naming a handle the bank table does not hold as a bank | MIDI-57; SRV-59 |
| `wrong_family` | A sound naming a bank of another family | MIDI-57 |
| `too_many_banks` | A sound naming, with the banks lifted from its music, more banks than its family's most | MIDI-57; S7-50; SRV-58 |
| `bank_dump_after_note` | A bank dump in a stored sound's music after its first note on, or anywhere in a live sound's events | MIDI-58, MIDI-51 |
| `bank_not_named` | A bank dump to lift with no name left in `lift_banks` | MIDI-58; SRV-15 |
| `midi_file_unsupported` | A Standard MIDI File of format 2, of SMPTE division or a division of 0, of format 0 with other than one track, or whose first chunk is not `MThd` or is shorter than 6 bytes | MIDI-113 |
| `midi_file_malformed` | A Standard MIDI File with a chunk or event whose stated length passes the file's end, a variable-length quantity of more than four bytes, a data byte with no status, a tempo of 0, a meta event's type of 128 or more, or a system exclusive message whose continuation never ends | MIDI-113, MIDI-114, MIDI-117, MIDI-119 |
| `midi_file_too_large` | A Standard MIDI File of more than 1,048,576 bytes, 1,024 tracks or 100,000 events, or a joined system exclusive message of more than 16,384 bytes | MIDI-117, MIDI-119 |
| Existing: `not_ascending` | Events out of time order | SRV-14, SRV-18, SRV-75 |
| Existing: `out_of_range`, `too_long`, `too_short`, `not_listed`, `wrong_type`, `unknown_field`, `missing_field`, `duplicate_field`, `not_base64`, `wrong_length`, `forbidden_character`, `duplicate` | As today; `duplicate` also for a synth53 sound naming two banks of one group (S53-26 (a)) | REQ-1475 |
| Existing: `unknown_connection` | As today | REQ-1473 |

`Rule::OutsideProfile` MUST no longer be used for any synthesizer kind; it stays for the Opus and PCM sounds.
- Reason: DEC-6462 item 2 and MIDI-21: every rule a schema cannot state is checked by the server with a typed refusal, and the closed list `Rule` names each. One value for each kind of fault lets a program react by rule, and the detail carries the specifics.
- Source: MIDI-8, MIDI-10 to MIDI-12, MIDI-17, MIDI-19 to MIDI-21, MIDI-26 to MIDI-31, MIDI-51, MIDI-53, MIDI-56 to MIDI-58, MIDI-63, MIDI-98, MIDI-104, MIDI-113, MIDI-114, MIDI-117, MIDI-119; S6581-54; `protocol.rs` (`Rule`).
- Verification: A test for every row, each asserting the rule, the path and the requirement in the detail; a schema test that `Rule` holds exactly the old values and these.

**SRV-52. No kit holds a copy of these rules.** Neither kit MUST contain any check of this document's rules beyond what `schema-13.json` states; a program MUST learn of every other fault from the server's `refused`.
- Reason: DEC-6462 item 3; MIDI-22; S6581-54 ("A kit MUST NOT hold its own copy of these rules beyond what the server's generated schema states").
- Source: DEC-6462 item 3; MIDI-22.
- Verification: Inspection of both kits; each kit's test that a message breaking a non-schema rule reaches the server and its refusal is returned unchanged (SRV-94's refusal vectors).

**SRV-53. Checks are made once, where they live.** A rule that the engine's interface module checks (a family's messages, patches, bank images, the block grammar and bounds) MUST be checked by calling the engine, never by a second copy in the server; the server's own checks MUST be only those of its program-facing shape (times, `until_us`, the bank and live tables, `lift_banks`, the Standard MIDI File, the bounds of SRV-90).
- Reason: MIDI-21: "The server MUST check every block it writes, every bank image and every patch with the same engine functions the receiver uses to read them"; one implementation of each rule (DEC-6462 "Why").
- Source: MIDI-21; DEC-6462.
- Verification: Inspection of the server's sound module: no table of controllers, patch layout, checksum or parameter range exists in the server.

**SRV-54. Everything written is read back by the receiver's code.** Before it sends anything, the server MUST read every block it wrote with the engine's block reader and the sound's family's synthesizer-side acceptance, every bank image with the family's bank reader, and every inline patch with the family's patch check, and MUST refuse the program's message if any of them would pass anything over, count it, call a block malformed or replace a patch with the default; the refusal's rule MUST be the one of SRV-51 the engine's reason maps to, and its detail MUST name the engine's reason.
- Reason: MIDI-21 and MIDI-63: nothing a program can send is played differently from what it said; the server refuses what the receiver would not take, so that a sound the server sends never reaches the receiver's fault rules.
- Source: MIDI-21, MIDI-63; REQ-6413.
- Verification: The property test of SRV-95.

### 4.2 Packing patches

**SRV-55. The server packs every patch through the engine.** From a patch in the `fields` form the server MUST build the engine's value of that family's patch and call the engine's packer, which MUST write the adopted interface's form: synth7, the single-voice dump of S7-38 (and the packed voice of S7-46 to S7-48 inside a 32-voice dump); synth106 and synth60, the messages of S106-13 and S106-31; synthD, the 60 values of SD-22; synth53, the 128-byte program of S53-33 packed into 152 bytes by S53-32, inside an edit buffer dump (S53-29) or a program dump (S53-28); synth8, the 42 values of S8-23; synth80, the 85 values of S80-33; synth6581 and synth8580, the register data message of S6581-10 to S6581-13. No packing code MUST exist in the server or in either kit.
- Reason: DEC-6462 items 1 and 3: the server packs; MIDI-21: the engine's functions are the one implementation.
- Source: MIDI-14, MIDI-54; S7-38, S7-46 to S7-48, S106-13, S106-31, SD-22, S53-29, S53-32, S53-33, S8-23, S80-33, S6581-10 to S6581-13.
- Verification: The round-trip tests of each family's section; inspection.

**SRV-56. A synth7 bank of fewer than 32 voices.** When it builds a synth7 bank from a list of n voices, n from 1 to 31, the server MUST fill voices n to 31 of the 32-voice dump with the default voice of S7-51, packed.
- Reason: DEC-6465 answer 18; a 32-voice dump always holds 32 voices (S7-41).
- Source: DEC-6465 answer 18; S7-41, S7-51.
- Verification: A test of a bank of 1 voice checks voices 1 to 31 equal the packed default voice.

**SRV-57. A Standard MIDI File's or an event's inline patch is checked as a patch.** A system exclusive message in the music that the family takes as an inline patch (synth7's single-voice dump, the synth106 family's function type `30` and `31` messages, synth53's edit buffer dump) MUST be checked by the family's patch check like a `patch` event, and refused with `invalid_patch` when it fails.
- Reason: MIDI-63: the server refuses any inline patch that would fail the receiver's check, however it was given.
- Source: MIDI-60, MIDI-63.
- Verification: A test of a single-voice dump with a wrong checksum given as a `system_exclusive` event, as `raw` bytes and in a file, each refused.

### 4.3 Banks

**SRV-58. The most banks a sound may name.** A sound MUST name, in `banks` and through `lift_banks` together, at least 1 bank and at most its family's most, and the server MUST refuse more with `too_many_banks`:

| Family | Most banks | Why no program change reaches a further one |
|---|---|---|
| synth7 | 2 | Programs 0 to 31 reach bank index 0 and 32 to 63 bank index 1 (S7-50, which itself requires this refusal) |
| synth106, synth60 | 1 | There is no bank select; programs 0 to 127 reach bank index 0 only (S106-10) |
| synthD | 1 | There is no bank select; programs 0 to 127 reach the bank (SD-12) |
| synth53, synth52, synth51 | 10 | One bank a group, groups 0 to 9, chosen by controller 32 (S53-13, S53-26); no two of one group (`duplicate`) |
| synth8 | 1 | One bank of up to 64 patches (S8-29) |
| synth80 | 3 | Controller 0 values 0 to 2 choose among three banks (S80-36) |

A sound of these families naming no bank at all MUST be refused with `too_short` on the path `banks`.
- Reason: MIDI-57 requires a sound of a family with banks to name 1 to 10 banks; a bank that no program change can reach is store spent for nothing, as S7-50 says of synth7's third. The family documents other than `synth7.md` state the reach but not the refusal; it is NeoTeletext's own, by the same reason (section 6).
- Source: MIDI-57, MIDI-59; S7-50, S106-10, SD-12, S53-13, S53-26, S8-29, S80-36.
- Verification: For each family, a test names its most and is accepted, and one more and is refused.

**SRV-59. The bank table.** The server MUST keep, for each channel program, a bank table: for each handle 0 to 255 at most one bank, its generation, the family it is for and its bank image, as last accepted from a bank message of that handle or lifted from a stored sound's music. A bank message or a lifted bank MUST replace the entry of its handle. A stored or live synthesizer sound, an Opus sound, a PCM sound or a live sound of any codec sent with that handle MUST remove the handle's bank entry, because the audio profile's handle then names the new object. The table's bytes are at most 256 × 16,384 = 4,194,304 a channel program, and the server MUST count them against the channel's memory as it counts every other held object.
- Reason: MIDI-57: the server sends every bank a sound names before the sound's OBJECT, and refuses a sound naming a bank it does not hold for that program; it must therefore hold them.
- Source: MIDI-57; the audio profile's one-byte handle (`record.rs`).
- Verification: A test sends a bank, then a PCM sound on its handle, then a synth sound naming the handle, and checks `unknown_bank`.

**SRV-60. Building and checking a bank.** From a bank message the server MUST build the bank image (MIDI-56) through the engine (SRV-55), check it with the engine's bank reader (MIDI-53) so that every patch it holds would be taken, and refuse it with `invalid_bank` or `invalid_patch` otherwise; the image MUST be 1 to 16,384 bytes (MIDI-55). It MUST then write the bank as a stored object of the bank codec, code 19, with extension tag 6 naming the family's codec (MIDI-55, MIDI-48), send it to the connections the message names, and enter it in the bank table.
- Reason: MIDI-15, MIDI-55, MIDI-56, MIDI-63.
- Source: The same.
- Verification: For each family, record tests of a bank of the smallest and the largest image; the tests of each family's bank section.

**SRV-61. A bank goes before the sound that names it.** The server MUST keep, for each connection, the handle and generation of every bank it has sent to it. When it sends a synthesizer sound (stored or live) to a connection, it MUST first send that connection, in the order of the sound's bank indexes, every bank the sound names whose handle and generation the connection has not been sent, and only then the sound's OBJECT record (MIDI-57). A sound naming a handle the bank table does not hold as a bank MUST be refused with `unknown_bank`; one naming a bank of another family with `wrong_family`.
- Reason: MIDI-57; a viewer who connects after a bank was sent to "all" gets it with the first sound that needs it, without the program tracking who has what.
- Source: MIDI-57, MIDI-62.
- Verification: A test sends a bank to connection 1, then a sound naming it to connections 1 and 2, and checks connection 2 received the bank's records before the sound's OBJECT and connection 1 did not receive them twice.

**SRV-62. A new generation of a bank.** A bank message for a handle the table holds at an older generation MUST replace it, and the server MUST send the new generation to the connections the message names only; the banks of a sound already playing are not changed by it (MIDI-65), and a later sound naming the handle is preceded by the new generation on each connection that has not been sent it (SRV-61).
- Reason: MIDI-65: a newer generation takes effect only for sounds started after it arrives.
- Source: MIDI-65.
- Verification: A test replaces a bank and sends a second sound, checking which connections received the new bank.

**SRV-63. Bank dumps lifted out of a stored sound's music.** The server MUST take out of a stored sound's music, before placing its events, each system exclusive message that is one of the family's bank-image messages and stands before the sound's first note on, and make a bank of each as if a bank message had sent it, with the name `lift_banks` gives it (SRV-15), naming it as the sound's next bank index. The messages lifted MUST be, per family:
- synth7: a 32-voice dump (S7-41), each one a bank of its own;
- the synth53 family: program dumps (S53-28), all those of one group making one bank, in the order their groups first appear;
- the synth106 family, synthD, synth8 and synth80: none (the synth106 family's function type `30` message is its inline patch, MIDI-60, and the others take no system exclusive).
A bank dump after the first note on, or any bank dump in a live sound's events, MUST be refused with `bank_dump_after_note`, naming its time. A lifted bank MUST be checked as SRV-60 says.
- Reason: MIDI-58, which leaves to the family document which messages are bank dumps. A Juno-106 patch message is both a bank image's unit and the interface's inline patch; taken as the inline patch it means what the instrument does with it, so it is not lifted.
- Source: MIDI-58; S7-41, S7-42, S53-28, S106-13, S106-38.
- Verification: The test of MIDI-58 (a file that begins with a DX7 32-voice dump and plays program 5); a test with three Prophet-5 program dumps of groups 2, 2 and 4 before the first note makes two banks; a dump after a note is refused.

### 4.4 Blocks

**SRV-64. Events become blocks through the engine's writer.** The server MUST place each event, after expanding typed objects and raw bytes into MIDI messages (SRV-10, SRV-13), at its tick (SRV-8), and MUST write each block with the engine's event-list writer, which writes the grammar of MIDI-23 with minimal variable-length quantities (MIDI-24), every channel message with its status byte (MIDI-12), and each system exclusive message as one `F0 <length> …` event (MIDI-27); it MUST never write an `F7` event, a meta event or a bare system common or real-time message (MIDI-23, MIDI-50).
- Reason: MIDI-23 to MIDI-27, MIDI-50: the writer writes only channel messages and system exclusive events; one writer, the engine's.
- Source: MIDI-12, MIDI-23 to MIDI-27, MIDI-44, MIDI-50.
- Verification: The tests of MIDI-23 and MIDI-24; a test writes the same events twice and checks identical bytes (MIDI-44).

**SRV-65. The order of events at a tick.** Within a tick the server MUST write first the restatement it adds (SRV-69), then the program's events in the order the program gave them (for a Standard MIDI File, by track, track 0 first, and in each track in the file's order), each event's messages in the order SRV-10's table gives them (MIDI-35).
- Reason: MIDI-35.
- Source: MIDI-35, MIDI-95.
- Verification: The tests of MIDI-35.

**SRV-66. Groups are never split.** The messages that one typed event writes (a bank select and its program change; a parameter number and its data; a coarse and fine pair; an inline patch of control changes; a named parameter's messages) MUST be written in one block at one tick, which SRV-8's placement guarantees, since every message of one event takes the event's tick. A `raw` event or a Standard MIDI File that gives such a group in separate events at different ticks that fall in different blocks MUST be written as given, at their own ticks, and the server MUST NOT move them.
- Reason: MIDI-37 asks the server never to split the groups it writes. A program that gives the halves of a group at different times has chosen their times, and moving them would change its music; the receiver's rules (MIDI-76: a lost block clears the selection) bound the harm.
- Source: MIDI-37, MIDI-76.
- Verification: The test of MIDI-37 (each group at a tick 0.05 milliseconds before a block's end is written whole in one block).

**SRV-67. A block's bounds.** A block the server writes MUST be at most 1,005 bytes and 256 events (MIDI-30, MIDI-31), and for the synth6581 family at most 20 register data messages and at most one start and one stop message (S6581-42, S6581-54 item 7); the server MUST refuse the program's message that would make a larger one with `block_full`, naming the block number and its bytes and events counted.
- Reason: MIDI-30, MIDI-31, S6581-42.
- Source: The same.
- Verification: A test at 1,005 bytes and one past it; at 256 events and one past it; at 20 and 21 register updates in one synth6581 block.

### 4.5 Restatement

**SRV-68. Each sound's parts are tracked by the engine.** For every stored sound while it is written and for every live sound while it lives, the server MUST keep the engine's tracker of the sound's family (MIDI-94) and give it, in order, every message it writes, so that the tracker holds each part's state exactly as the restatement needs it: the bank select values and the last program change or inline patch, the latest value of every parameter moved since, and the performance state (pitch bend, channel pressure, controllers 7 and 1, the sustain pedal and each family's further items); synth106's tracked state also gives the switch bytes of SRV-33. The tracker MUST be bounded as MIDI-94 says: each parameter of the family's table once, 16 channels, one inline patch a part.
- Reason: MIDI-94: only the server sees every event; the tracker belongs with the family's message tables in the engine, where its restatement can be played into the real synthesizer in the engine's tests (MIDI-93's verification). DEC-6477 (answer 5) places this logic in the engine, beside the receiver's own code.
- Source: MIDI-93, MIDI-94; S6581-46, S7-49 item 4, S106-40, SD-28, S53-46, S8-29 (e), S80-46.
- Verification: A server test of the tracked state after a long sequence of every message of each family (MIDI-94's test); the engine's tests of each family's restatement.

**SRV-69. What a restatement is and where it goes.** A restatement MUST be the one each family document states exactly, written by the engine from the tracker: S6581-46 (a full register update of the registers' present values), S7-49 item 4, S106-40, SD-28, S53-46, S8-29 (e), S80-46. It MUST be written whole in one block, at one tick, before the program's events of that tick (MIDI-95, MIDI-98), and MUST carry the state after every event of earlier ticks. In a live sound the server MUST write every part's restatement in the first block it sends and then at least once in every `RESTATE_EVERY_BLOCKS` (50) blocks, and SHOULD write it every `RESTATE_AIM_BLOCKS` (25) blocks where blocks have room (MIDI-96), at tick 0 of the block chosen; a part that has received no message since the sound began MUST still be restated (MIDI-96). The server MUST NOT write a restatement for one connection only (MIDI-100; DEC-6465 answer 4).
- Reason: MIDI-93 to MIDI-100. Tick 0 is chosen so that the restatement precedes everything in its block.
- Source: MIDI-93, MIDI-95, MIDI-96, MIDI-98, MIDI-100; DEC-6465 answers 2 and 4; the family documents' restatement requirements.
- Verification: The test of MIDI-96 (an hour of live events, no 50 consecutive blocks without a part's restatement); the family documents' restatement tests through the server.

**SRV-70. A stored sound begins with its restatement.** At tick 0 of block 0 of every stored sound the server MUST write the restatement of every part the sound uses, carrying the state before the sound's first event (each part at program 0 of bank index 0, MIDI-61, and every controller at its starting value), except for synth6581 and synth8580, whose program's own first event is that restatement (SRV-25; S6581-45). A part is used when any event of the sound addresses its channel.
- Reason: MIDI-99: when a stored sound loops its synthesizer is not reset, so its start must set every part again.
- Source: MIDI-99, MIDI-105; S6581-45.
- Verification: The test of MIDI-99, for each family.

**SRV-71. Fitting restatements.** Where a block lacks room for a part's restatement (its bytes or events would pass MIDI-30 or MIDI-31 with it), the server MUST put that part's restatement in the next block with room, and different parts' restatements MAY go in different blocks within the interval; if `RESTATE_EVERY_BLOCKS` blocks pass with no room for a part, the server MUST refuse the program's message whose events filled them with `no_room_to_restate`, naming the blocks and the part.
- Reason: MIDI-98.
- Source: MIDI-98.
- Verification: The tests of MIDI-98 (sixteen synth7 parts each on an inline voice are all restated within 50 blocks; fifty full blocks are refused).

### 4.6 Live sounds

**SRV-72. The live table.** The server MUST keep, for each channel program, a live table: for each handle at most one live synthesizer sound, with its kind, generation, settings (clock; key mode and split key; banks), the connections it was announced to, its `until_us`, the number of the next block to write and of the next to send, the live sound's clock (SRV-77), the time of its latest event, the events placed in the block not yet written (at most one block's worth, MIDI-31, plus what one message carries), the blocks written and held for pacing with the connections each goes to (SRV-77), the tracker (SRV-68) and the block count since each part's last restatement. An events message whose handle and generation the table does not hold as a live sound of the message's kind MUST be refused with `unknown_live_sound`. A stored sound, a bank, an Opus sound, a PCM sound or a live sound of any other kind sent with the handle MUST remove the handle's live entry.
- Reason: MIDI-20: the server, not the program, now numbers and fills blocks, so it must hold each live sound's state between messages.
- Source: MIDI-20, MIDI-94, MIDI-96.
- Verification: A test sends events for a handle never announced, and for one replaced by a PCM sound, and checks `unknown_live_sound`.

**SRV-73. Announcing a live sound.** A live sound message MUST make the server write the OBJECT record of MIDI-40 (block bytes 1,005, MIDI-103; samples 0; blocks 0; tags 3, 4, 5 and 7 as MIDI-48 gives them from the kind and the settings), send the banks it names before it (SRV-61), and enter the sound in the live table with block 0 next. A live sound message whose handle and generation the table already holds as a live sound with the same kind and the same settings MUST change nothing in the table, and MUST send to the connections it names that have not been sent it only the OBJECT, preceded by any bank SRV-61 requires, so that a program can bring a newly connected viewer into a live sound already playing (DEC-6477 typescript answer 6); the connections then receive the sound's blocks from the next one sent (SRV-74). One with the same handle and generation but another kind or other settings MUST be refused with `live_sound_changed`. One with a new generation MUST replace the entry, starting again at block 0.
- Reason: MIDI-20 (a live sound announced once), MIDI-100 (a receiver that joins starts at the newest block and is put right by the restatements), MIDI-103.
- Source: MIDI-20, MIDI-40, MIDI-48, MIDI-100, MIDI-103; DEC-6477.
- Verification: A test announces a live sound to connection 1, sends events, announces it again to connection 2 and checks connection 2 receives the OBJECT and the next blocks and the block numbering does not restart.

**SRV-74. An events message and `until_us`.** For an events message the server MUST: (1) refuse it with `advance_too_far` when `until_us` exceeds the sound's last `until_us` (0 before the first message) by more than `MOST_LIVE_ADVANCE_US` (2,000,000); (2) refuse it with `until_moved_back` when `until_us` is less than the last; (3) refuse with `not_before_until` any event whose `time_us` is not less than `until_us`; (4) place every event (SRV-8, SRV-64); (5) write, in block order, every block k not yet written with `(k + 1) × 20,000 ≤ until_us`, each with its restatements (SRV-69), as DATA records of the live layout (MIDI-42, offset 0), and send each as SRV-77's pacing allows to the connections the message names, first sending the sound's banks and OBJECT (SRV-61, SRV-73) to a named connection that has not been sent them; (6) keep the block in which `until_us` falls, unwritten, for the next message. An events message with no event that advances `until_us` MUST write the blocks it completes, empty but for restatements. A program ends a live sound for a connection by naming that connection in no later events message.
- Reason: MIDI-20: the server writes every block that ends at or before `until`, holding back the one in which `until` falls; `until` is the time up to which the program has given every event, so an event at or after it belongs to a later message. The blocks are sent as the receiver's ring allows (SRV-77; DEC-6477 answer 2).
- Source: MIDI-20, MIDI-42, MIDI-122.
- Verification: The tests of MIDI-20 (events in steps of 200 milliseconds send exactly the completed blocks; an advance of 2,000,001 is refused); a test of each refusal.

**SRV-75. Late and out-of-order events.** An event whose tick falls in a block already sent MUST be refused with `late_event`, naming the event and the block. Events MUST be in non-decreasing `time_us` within a message and MUST NOT be earlier than the latest event of the sound's earlier messages; one that is MUST be refused with `not_ascending`.
- Reason: MIDI-20 ("An event whose tick lies in a block already sent MUST be refused (it is late)"); one order across messages keeps a live sound's blocks the same as the stored sound of the same events.
- Source: MIDI-20, MIDI-35.
- Verification: A test sends an event for a block already sent and checks the refusal names it; a test sends an event earlier than the previous message's last.

**SRV-76. Block numbers wrap.** A live sound's block k MUST be sent with the block number `k mod 65,536` in its DATA record, as today; the server's own count k MUST be a `u64`, so that the times of SRV-8 up to `SAFE_INTEGER_LIMIT` map to block numbers without overflow.
- Reason: MIDI-17 ("its block numbers wrap at 65,536 as today"); the record's block number is two bytes (MIDI-42).
- Source: MIDI-17, MIDI-42.
- Verification: A test starts a live sound with `until_us` near 65,536 × 20,000 and checks the wrap.

**SRV-77. The server paces live blocks to the receiver's ring.** The server MUST NOT send a live sound's block more than `LIVE_SEND_LEAD_BLOCKS`, 25 blocks (500 milliseconds), before the moment that block is due by the live sound's clock, which starts when the server sends the sound's first block and advances 20 milliseconds a block, so that no viewer's receiver is sent more than its ring of 32 blocks can hold ahead of play (`integration.md` INT-18). Blocks an events message completes earlier, which MIDI-20 allows (up to 100 blocks in one message), MUST be held by the server, in order, and sent as the lead allows, each to the connections the events message that completed it names; a held block MUST NOT be sent to a connection announced after it was written. The held blocks of one live sound are at most `MOST_LIVE_INSTRUMENT_BLOCKS` (100) plus the lead, and the server MUST count them against the channel's memory. `LIVE_SEND_LEAD_BLOCKS` MUST be defined once in the server (SRV-90), and a compile-time assertion MUST hold it below `LIVE_RING_BLOCKS − LIVE_LOOKAHEAD_BLOCKS` (29), the engine's constants used by name. The schema's documentation of `until_us` MUST say that the server sends the blocks a message completes at most 500 milliseconds ahead of their time, and that a live sound with no new block for 2,000 milliseconds stops at the receiver, so that a program SHOULD advance `until_us` at least every 2,000 milliseconds.
- Reason: A receiver keeps only the newest 32 blocks of a live sound (MIDI-46, MIDI-101), so a burst of 100 blocks would overwrite blocks not yet played. DEC-6477 (answer 2) puts the pacing in the server, because DEC-6462 puts the work in the server and a thin kit cannot know a receiver's ring; MIDI-20's advance of 100 blocks in one message stays allowed, and the server holds the excess. The figure of 25 blocks is `integration.md`'s (its INT-18 and section 16 item 1): the lead the audio demonstration channel's live page uses today (10 blocks every 200 milliseconds) with room to spare, short enough that a joining viewer hears the present.
- Source: MIDI-20, MIDI-46, MIDI-101; `integration.md` INT-18; DEC-6477 answer 2; `profile.rs` (`LIVE_RING_BLOCKS` 32, `LIVE_LOOKAHEAD_BLOCKS` 3, `LIVE_STALL_MS` 2,000).
- Verification: A server test sends one events message advancing 100 blocks and checks, against a test clock, that no block leaves the server more than 25 blocks before it is due and that every block is sent in order; the compile-time assertion; inspection of the schema's description of `until_us`.

**SRV-78. A live sound ends.** A live sound's entry MUST stay in the live table until a message replaces its handle (SRV-72, SRV-73) or the program ends; `stop` of an audio channel MUST NOT remove it. The block holding the last `until_us` is never sent unless a later message completes it.
- Reason: `stop` acts on an audio channel, not on a handle, and a program may play the same live sound again; the table's size is bounded by the 256 handles.
- Source: MIDI-20; `protocol.rs` (`StopSound`).
- Verification: A test stops an audio channel playing a live sound, sends more events, and checks they are accepted.

### 4.7 Records of a stored sound

**SRV-79. The records of a stored sound.** For a stored synthesizer sound the server MUST write, through the engine's encoder: the OBJECT record of MIDI-40 and MIDI-41 (codec of MIDI-107 for the kind's family; rate code 7; block bytes the longest block; samples the blocks times 960; blocks 1 to 6,000; tags 3, 4, 5, 7 and 8 as MIDI-48 gives them from the kind and its fields, tag 4 holding `banks` then the lifted banks); then its DATA records, each holding as many whole blocks as fit (MIDI-42, MIDI-47), with the byte offset of its first block. It MUST refuse a sound whose blocks total more than 960,000 bytes with `beyond_length`. It MUST send, to each connection named, the banks of SRV-61, then the OBJECT, then the DATA records in block order; then it MUST send `sound_built` (SRV-47).
- Reason: MIDI-40 to MIDI-48, MIDI-104, MIDI-107.
- Source: The same.
- Verification: The record tests of MIDI-40 to MIDI-47 through the server; MIDI-47's test (no record could have held the next block).

**SRV-80. What the server emits.** The records of SRV-60, SRV-73, SRV-74 and SRV-79, and the CONTROL records of `play`, `stop` and `gain`, MUST be all the server sends a receiver for synthesizer sounds, each record carried to each connection as the server carries every audio record today (teletext packets of the audio service, numbered on the connection). How they travel to the browser and are played there is `integration.md`'s, which this document does not restate.
- Reason: The architecture keeps the audio profile's records and carriage (decision A2); the integration document of this set specifies what the browser does with them.
- Source: MIDI-13; decision A2; `channel.rs` (`records`).
- Verification: The integration document's tests; a server test that a stored sound's packets decode to exactly SRV-79's records.

### 4.8 Standard MIDI Files

**SRV-81. Formats and chunks.** The server MUST read a Standard MIDI File as MIDI-113 says, through its own reader in `crates/teletext-runtime/src/sound/midi_file.rs`: the first chunk MUST be `MThd` with a length of at least 6, read by its stated length; format 0 (exactly one track) and format 1 MUST be read; format 2, a division with its top bit set and a division of 0 MUST be refused with `midi_file_unsupported`; chunks of other types than `MTrk` MUST be skipped by their length; a header's track count MUST be at most `MOST_MIDI_FILE_TRACKS` (1,024), and the tracks read are the `MTrk` chunks found, which MUST number as the header says, or the file is refused with `midi_file_malformed`.
- Reason: MIDI-113, MIDI-119. The reader is the server's because it holds a whole file and merges tracks, which needs allocation the `no_std`, allocation-free engine does not have.
- Source: MIDI-113, MIDI-119; Standard MIDI Files 1.0, printed pages 3 to 5 (PDF 132 to 134).
- Verification: The tests of MIDI-113.

**SRV-82. Tempo and time.** The server MUST build one tempo map from every track's set tempo meta events, take 500,000 microseconds a quarter note before any, and compute each event's time exactly, as a rational number, rounding once to a tick by `tick = floor((numerator + 50 × denominator) ÷ (100 × denominator))`, in integers of 128 bits (MIDI-114). A tempo of 0 MUST be refused with `midi_file_malformed`.
- Reason: MIDI-114. With at most 100,000 events, ticks of at most 2^28 per delta (a four-byte variable-length quantity), a division of at most 32,767 and a tempo of at most 2^24 − 1, the numerator of a sum is below 2^128.
- Source: MIDI-114.
- Verification: The test of MIDI-114 (500 tempo changes, the last event's tick against the exact sum).

**SRV-83. Meta events, escapes and system exclusive in a file.** The server MUST use set tempo and end of track, drop every other meta event, join a system exclusive message split across `F0` and `F7` continuation events into one message at the time of its first part (at most `MOST_JOINED_SYSEX_BYTES`, 16,384), drop `F7` escape events that are not continuations, and then treat each message as a timed event (SRV-24), lift it into a bank (SRV-63) or refuse it (MIDI-115, MIDI-117).
- Reason: MIDI-115, MIDI-117.
- Source: The same.
- Verification: The tests of MIDI-115 and MIDI-117 (a DX7 32-voice dump split into five packets at a file's start, lifted into a bank).

**SRV-84. What a file holds that the synthesizer does not take.** The server MUST drop, and count by kind in `sound_built`'s `dropped` (SRV-47), every message of a file the family does not take, every message of a channel the channel map maps to none, every system common and real-time message inside an escape, every other escape, and every meta event other than set tempo and end of track; it MUST NOT refuse a file for them (MIDI-118). A message the family takes but whose content is faulty (an inline patch failing its check, a value outside its range) MUST still be refused.
- Reason: MIDI-118: files are made for many instruments; but a message the synthesizer would act on and play wrongly is a fault of the file, which the author must learn of.
- Source: MIDI-118, MIDI-63.
- Verification: The test of MIDI-118 (one message of each kind a synthD sound does not take; the report checked); a file holding a DX7 voice with a wrong checksum is refused.

**SRV-85. A file's bounds and its length.** The server MUST refuse a file of more than `MOST_MIDI_FILE_BYTES` (1,048,576) bytes, more than `MOST_MIDI_FILE_TRACKS` (1,024) tracks or more than `MOST_MIDI_FILE_EVENTS` (100,000) events, meta events and dropped messages counted, with `midi_file_too_large`; a chunk or event whose stated length passes the file's end, a variable-length quantity of more than `MOST_FILE_VLQ_BYTES` (4) bytes, or a data byte with no status, with `midi_file_malformed`; and it MUST believe no length past the bytes it has. The sound's length MUST be the later of the last event's tick and the last end-of-track's tick, plus the tail, as SRV-9 says; a file given with `length_us` MUST have every event and every end of track within it, or be refused with `beyond_length`.
- Reason: MIDI-119, MIDI-120.
- Source: The same.
- Verification: The tests of MIDI-119 and MIDI-120.

**SRV-86. The channel map.** The server MUST apply a `MidiFile`'s `channel_map` (SRV-23) to every channel message of the file before checking it against the family (MIDI-116); for synth7 a mapped channel is a part.
- Reason: MIDI-116.
- Source: MIDI-116.
- Verification: The test of MIDI-116 (channel 10 moved to channel 1; channel 2 dropped).

### 4.9 The engine's crates

**SRV-87. The engine the server pins.** The server MUST depend on the engine's crates at one commit, through the `git` source of the engine's repository and one `rev` for every `neoteletext-*` dependency (DEVELOPMENT.md section 11), that commit being the first that builds `midi-architecture.md`'s event codecs and every family's interface module; it MUST depend on `neoteletext-audio` with the feature `encode` and on `neoteletext-audio-instruments` with the feature `interface` and no family's synthesis feature. The pin MUST be moved in a commit of its own, naming what the new engine commit changes for the server, before any commit of protocol 13's sound messages.
- Reason: MIDI-21: the server checks with the receiver's own functions, which are the engine's; the server needs the tables, packers, checks and trackers but not the synthesis, which it never runs. One pin for every crate keeps the encoder and the receiver's checks one implementation at one commit.
- Source: MIDI-21; DEVELOPMENT.md section 11; the server's `Cargo.toml` (one `rev` for every engine crate, today `4ddd34be`).
- Verification: The server's commit gate's check that every `neoteletext-*` dependency names the same `rev`; inspection of the features.

**SRV-88. What the server calls in the engine.** The engine commit of SRV-87 MUST provide, and the server MUST call, these, under these names (the engine's process may refine a name, and this requirement is revised with it):

| Engine item | Crate and feature | What the server uses it for |
|---|---|---|
| `neoteletext_audio::event::{Message, read_block}` | `neoteletext-audio` | Reading back every block written (SRV-54); the block grammar's reader, the receiver's own |
| `neoteletext_audio::encode::event::BlockWriter` | `neoteletext-audio`, `encode` | Writing each block's event list (SRV-64) |
| `neoteletext_audio::encode::instrument::{object, data_records, live_object, live_data_record, bank_records}` | `neoteletext-audio`, `encode` | The OBJECT and DATA records of event codecs and of the bank codec (SRV-60, SRV-73, SRV-74, SRV-79) |
| `neoteletext_audio::Codec` and its codes 12 to 19 | `neoteletext-audio` | The codec of each kind (MIDI-107) |
| `neoteletext_audio_instruments::interface::{Family, Kind}` | `neoteletext-audio-instruments`, `interface` | The family and variant of each kind, and the OBJECT tags they set |
| For each family, `neoteletext_audio_instruments::<family>::interface::{accepts, Patch, pack_patch, check_patch, build_bank, check_bank, Tracker}` (`<family>` one of `synth6581`, `synth7`, `synth106`, `synthd`, `synth53`, `synth8`, `synth80`) | `neoteletext-audio-instruments`, `interface` | Which messages the family takes (SRV-24); the patch's value type, packer and check (SRV-55); the bank image's builder and reader (SRV-60); the tracker and its restatement writer (SRV-68, SRV-69) |
| `neoteletext_audio_instruments::synth80::presets::PRESETS` | `neoteletext-audio-instruments`, `interface` | The 22 preset tones (SRV-43) |
| `neoteletext_audio::synth_vectors::TABLE` | `neoteletext-audio` | The shared golden vectors (SRV-94) |

The `interface` feature MUST compile without allocation, without floating point and without any family's synthesis code, as the engine's `no_std` rules require of its libraries.
- Reason: MIDI-21 and DEC-6462: one implementation of the tables and checks, called by both the receiver and the server.
- Source: MIDI-21, MIDI-94; DEC-6462; DEVELOPMENT.md section 6 (the engine's `no_std` rules).
- Verification: The server's build against the pinned engine; the engine's build of `neoteletext-audio-instruments` with `interface` alone.

**SRV-89. What stays in the server.** The server MUST hold, in `crates/teletext-runtime`, only: the protocol 13 types and their schema (`protocol.rs`), the checks of SRV-53's program-facing shape (`protocol/check.rs` and a sound module under it), the conversion of a typed patch to the engine's patch value, the placing of events at ticks, the Standard MIDI File reader (SRV-81), the bank table and the live table, and the sending of records and `sound_built`. The server's `sound/instrument.rs`, which writes codecs 3 to 11's record bodies itself because the engine it pinned predated them, MUST be deleted.
- Reason: DEC-6462: the server is the core of the interface, and the engine is the core of the instruments; everything the receiver also needs lives in the engine once.
- Source: DEC-6462; `sound/instrument.rs`'s own comment ("The engine this server is pinned to predates those codecs, so the records' bodies are written here").
- Verification: Inspection.

### 4.10 Bounds

**SRV-90. Every bound is a named constant.** The server MUST define each bound of this table once, as a named constant with a doc comment giving its source, in `protocol.rs` where the schema uses it and in the sound module otherwise, and MUST assert at compile time each relation the table states. A bound that is the engine's MUST be the engine's constant used by name.

| Constant | Value | Source or derivation |
|---|---|---|
| `PROTOCOL` | 13 | SRV-1 |
| `LONGEST_LINE` | 16,777,216 bytes | As today |
| `SAFE_INTEGER_LIMIT` | 2^53 − 1 | SRV-2 |
| `TICK_US` | 100 | MIDI-17: a tick is 0.1 millisecond |
| `BLOCK_TICKS` | 200 | The engine's constant (MIDI-25) |
| `BLOCK_US` | 20,000 | `TICK_US × BLOCK_TICKS`, asserted |
| `MOST_INSTRUMENT_BLOCKS` | 6,000 | As today (MIDI-104) |
| `MOST_STORED_TIME_US` | 120,000,000 | `MOST_INSTRUMENT_BLOCKS × BLOCK_US`, asserted |
| `MOST_LIVE_INSTRUMENT_BLOCKS` | 100 | As today (MIDI-20) |
| `MOST_LIVE_ADVANCE_US` | 2,000,000 | `MOST_LIVE_INSTRUMENT_BLOCKS × BLOCK_US`, asserted |
| `LIVE_SEND_LEAD_BLOCKS` | 25 | `integration.md` INT-18; asserted below the engine's `LIVE_RING_BLOCKS − LIVE_LOOKAHEAD_BLOCKS` (29) (SRV-77) |
| `MOST_BLOCK_BYTES` | 1,005 | The engine's (MIDI-30) |
| `MOST_BLOCK_EVENTS` | 256 | The engine's (MIDI-31) |
| `MOST_STORED_SOUND_BYTES` | 960,000 | The engine's (MIDI-41) |
| `MOST_STORED_EVENTS` | 100,000 | MIDI-122 |
| `MOST_LIVE_EVENTS` | 25,600 | `MOST_LIVE_INSTRUMENT_BLOCKS × MOST_BLOCK_EVENTS`, asserted (MIDI-122) |
| `MOST_EVENT_BYTES` | 16,384 | Equal to `MOST_BANK_IMAGE_BYTES`, asserted: the longest message an event may give is a bank dump to lift |
| `MOST_PATCH_BYTES` | 16,384 | MIDI-122 |
| `MOST_BANK_IMAGE_BYTES` | 16,384 | The engine's (MIDI-55) |
| `MOST_BANK_PATCHES` | 128 | MIDI-56; each family's own lower most (32, 40, 64) is the engine's |
| `MOST_SOUND_BANKS` | 10 | The engine's (MIDI-57); each family's most of SRV-58 is the engine's |
| `RESTATE_EVERY_BLOCKS` | 50 | MIDI-96 |
| `RESTATE_AIM_BLOCKS` | 25 | MIDI-96 |
| `MOST_MIDI_FILE_BYTES` | 1,048,576 | MIDI-119 |
| `MOST_MIDI_FILE_TRACKS` | 1,024 | MIDI-119 |
| `MOST_MIDI_FILE_EVENTS` | 100,000 | MIDI-119 |
| `MOST_FILE_VLQ_BYTES` | 4 | MIDI-119; Standard MIDI Files 1.0, printed page 2 (PDF 131) |
| `MOST_JOINED_SYSEX_BYTES` | 16,384 | MIDI-117 |
| `DEFAULT_TEMPO_US` | 500,000 | MIDI-114 |
| `MOST_TEMPO_US` | 16,777,215 | MIDI-114: three bytes |

The protocol 12 constants of SRV-99 MUST be deleted with the types that used them.
- Reason: DEVELOPMENT.md section 6: every literal is named, each constant defined once, and where two places must agree it is asserted; MIDI-122.
- Source: MIDI-121, MIDI-122; DEVELOPMENT.md section 6.
- Verification: A server test at each bound and one past it; the compile-time assertions.

**SRV-91. The work per message is bounded by its bytes.** The server's work on one sound message MUST be at most a constant times the message's bytes plus a constant times the blocks it writes, the constants named and measured: reading and checking are linear in the message; placing events is linear (events arrive in time order, SRV-14, SRV-18; a file's tracks are merged by a heap of at most 1,024 tracks, so at most 10 comparisons an event); writing a block is linear in its events; restatements are bounded by the tracker's fixed size (SRV-68) per part per block; a bank is built and checked in one pass over at most 16,384 bytes. A timed test MUST send the largest message of each kind the bounds allow (a stored sound of 100,000 events over 6,000 blocks; a 1,048,576-byte file of 1,024 tracks; an events message of 25,600 events; a bank of 128 patches as fields) and MUST print its time against a budget stated in the test.
- Reason: MIDI-122: "Its work on one message MUST be proportional to the message's bytes"; DEC-6462's "When to reconsider" asks for the server's work per message to be watched; DEVELOPMENT.md section 2.1: measure.
- Source: MIDI-122; DEC-6462; DEVELOPMENT.md section 8 (timed tests hold a budget and print their numbers).
- Verification: The timed test.

### 4.11 Fuzz targets

**SRV-92. Fuzz targets.** The server's `fuzz/` workspace MUST have these targets, each with a corpus that keeps every input that ever found a fault and replays it first, run by the full gate:
1. `synth_sound`: arbitrary bytes read as one protocol 13 `sound` line of any synthesizer kind and handled to the end (checks, building, records), asserting that every accepted message's blocks, banks and patches pass the engine's receiver-side reading with nothing counted;
2. `synth_live`: a sequence of live sound and events messages for one handle, asserting the same of every block sent and that block numbers rise by one;
3. `synth_patch`: arbitrary bytes as each family's patch bytes form and bank bytes form;
4. `midi_file`: arbitrary bytes as a Standard MIDI File for each family;
5. `protocol_reader`, as today, its corpus extended with lines of every kind of this document.
The target `instrument_sound` MUST be deleted with protocol 12's kinds, its corpus inputs that are valid lines kept as inputs of `synth_sound` where they still parse.
- Reason: MIDI-124 and DEVELOPMENT.md sections 8 and 14: every reader of outside input has a fuzz target.
- Source: MIDI-124; DEVELOPMENT.md sections 8 and 14; `fuzz/fuzz_targets/` (`instrument_sound.rs`, `protocol_reader.rs`).
- Verification: The full gate runs them for its stated time.

### 4.12 Tests and golden vectors

**SRV-93. Every requirement has its tests.** Each requirement of this document MUST be verified by the test its Verification line names, in `crates/teletext-runtime/src/protocol/tests/` (a module `synth.rs` for the types and refusals, as `sound.rs` is today) and `crates/teletext-runtime/src/sound/tests/` for the building; each test MUST name the requirement it verifies, and each regression test MUST be shown to fail on the code before its fix (DEVELOPMENT.md section 8).
- Reason: DEVELOPMENT.md section 8.
- Source: DEVELOPMENT.md section 8.
- Verification: Review: every requirement number appears in a test's name or comment.

**SRV-94. Golden vectors shared with the engine.** neoteletext-common MUST hold `synth-vectors.tsv`, beside `wire-vectors.tsv` and in its form (a comment header, then rows of tab-separated columns), with these columns: `name`; `kind`; `message`, one protocol 13 `sound` line as JSON; `blocks`, the hexadecimal of each block's event list, separated by `/`, or `-`; `records`, the hexadecimal of each record, separated by `/`, or the expected refusal as `refused rule path`. It MUST hold at least: for each of the eleven kinds, its default patch from fields and from bytes, a stored sound of every event variant, a live sound of three events messages with a restatement, and a bank of each form; one row for every `Rule` value of SRV-51; and the worked examples the family documents name as test vectors (S106-15; S53-32's worked examples; S6581-53's times). The engine MUST keep an exact copy of it, compared by its commit gate, as `neoteletext_audio::synth_vectors::TABLE`, and MUST check every row's `blocks` against its encoder's `records` and its receiver's reading; the server MUST read the engine's copy through its pinned engine and check every row's `message` against `blocks`, `records` or the refusal; each kit MUST check that, for every refusal row, it passes the server's `refused` through unchanged.
- Reason: DEC-6462 item 2 ("shared fixtures and vectors"); the existing form, by which the engine and the server already share `wire-vectors.tsv`.
- Source: DEC-6462 item 2; `wire-vectors.tsv`'s header.
- Verification: The three repositories' tests of the file; the engine's commit gate's comparison of its copy.

**SRV-95. One property, tested.** A property test MUST generate sound messages of every kind (valid and faulty), and for every one the server accepts MUST check that the receiver's reader reports no event passed over, no block malformed and no patch refused, and that the same message sent twice gives byte-identical records.
- Reason: MIDI-21's verification; MIDI-44.
- Source: MIDI-21, MIDI-44.
- Verification: The property test itself, with its seed printed.

### 4.13 The schema and the kits' copies

**SRV-96. The schema is generated.** `protocol/schema-13.json` MUST be generated by `protocol::schema()` from the types of this document and the protocol's others, as today, every bound of this document that a JSON Schema can state carried by a `schemars` attribute (`range`, `length`, the externally tagged parameter enums with their ranges), every doc comment of every type and field carried into the schema's descriptions; the schema test MUST fail when the file differs from what the types generate.
- Reason: REQ-1476, REQ-1479; DEC-6462 item 2.
- Source: `protocol.rs` (`schema`); `protocol/tests/schema.rs`.
- Verification: The schema test.

**SRV-97. The TypeScript kit's copy.** neoteletext-server-ts-protocol MUST hold `schema/protocol-13.json`, byte for byte the server's `protocol/schema-13.json` at the server commit its `scripts/check.sh` names in `SCHEMA_FROM`, and its commit gate MUST fail otherwise, as today for version 12; its validators and types MUST be generated from that file (`src/wire/generated/`); `schema/protocol-12.json` MUST be deleted.
- Reason: DEC-6462 items 2 and 3: the schema is the contract, taken by copy pinned to a server commit.
- Source: The kit's `scripts/check.sh` (`SCHEMA_FROM`, the step "schema/protocol-12.json is the server's").
- Verification: The kit's commit gate.

**SRV-98. The Python kit's copy.** neoteletext-server-channels MUST hold `kits/python/src/neoteletext_app/protocol-13.json`, byte for byte the server's `protocol/schema-13.json` at the commit its `scripts/check.sh` names in `SCHEMA_FROM`, with `SCHEMA_COPY` naming the file, and its commit gate MUST fail otherwise; `protocol-12.json` MUST be deleted; the Python kit's types for these messages MUST be generated from, or checked against, that file, equal in what they can express to the TypeScript kit's.
- Reason: DEC-6462 item 3: the kits are equals.
- Source: neoteletext-server-channels `scripts/check.sh` (`SCHEMA_FROM`, `SCHEMA_COPY`).
- Verification: That repository's commit gate.

### 4.14 What is removed

**SRV-99. Protocol 12's synthesizer kinds are removed from the server.** In the commit that makes protocol 13's sound messages, the server MUST delete: the `Sound` variants `Synth6581Blocks`, `Synth8580Blocks`, `Synth7Blocks`, `Synth106Blocks`, `Synth60Blocks`, `SynthDBlocks`, `Synth53Blocks`, `Synth52Blocks`, `Synth51Blocks`, `Synth8Blocks`, `Synth80Blocks`; the types `Synth6581BlocksSound`, `Synth7BlocksSound`, `SynthSound`, `SynthLiveSound`, `SynthBlocksSound`, `SynthBankSound` and the enum `Synth` with its `codec`, `model` and `patch_bytes`; the protocol 12 shapes of `Synth6581Sound`, `Synth6581LiveSound`, `Synth7Sound`, `Synth7LiveSound`, `Synth7BankSound`, `Synth8Sound` and `Synth8LiveSound` (their names are reused for protocol 13's types); the constants `SYNTH6581_IMAGE_BYTES`, `SYNTH6581_IMAGES_PER_BLOCK`, `SYNTH7_SLOT_BYTES`, `SYNTH7_MOST_SLOTS`, `SYNTH7_PATCH_BYTES`, `SYNTH7_MOST_PATCHES`, `SYNTH106_PATCH_BYTES`, `SYNTHD_PATCH_BYTES`, `SYNTH53_PATCH_BYTES`, `SYNTH8_PATCH_BYTES`, `SYNTH80_PATCH_BYTES`, `SYNTH_MOST_PATCHES`; `protocol/check/instrument.rs` and `protocol/check/instrument/patch.rs`; `sound/instrument.rs`; the fuzz target `instrument_sound`; and every test of those. No alias, no compatibility path and no second reader of version 12 MUST remain.
- Reason: DEVELOPMENT.md section 2.1 ("No compatibility shims … delete what is replaced in the same change"); MIDI-111.
- Source: `protocol.rs`, `protocol/check/instrument.rs`, `sound/instrument.rs`, `fuzz/fuzz_targets/instrument_sound.rs` at `df662b9`.
- Verification: A search of the server for each name finds only protocol 13's types of the reused names.

**SRV-100. The kits' sound logic is removed.** In the release that speaks protocol 13, the TypeScript kit MUST delete every piece of instrument logic, which today is in `src/sound/`: `synth-score.ts`, `synth7-score.ts`, `slot-score.ts`, `program-repeater.ts`, `midi-file.ts`, `midi-bytes.ts`, `synth-patch-rules.ts`, `synth-patch-tables.ts`, `synth106-patch.ts`, `synth53-patch.ts`, `synthd-patch.ts`, `synth8-patch.ts`, `synth80-patch.ts`, `synth7-patch.ts`, `synth7-sysex.ts`, `synth7-slot.ts`, `synth7-live.ts`, `synth-live.ts`, `synth6581-image.ts`, `synth6581-note.ts`, `synth6581-track.ts`, `synth6581-clock.ts`, `instrument-profile.ts`, `patch-field.ts` and whatever of `instrument-fields.ts`, `instrument-members.ts`, `synth-fields.ts` and `members.ts` builds or checks a synthesizer's bytes; in `src/wire/`, `instrument-rules.ts` and `instrument-wire.ts`; and their tests (`synth-patch.test.ts`, `synth-score.test.ts`, `synth-sounds.test.ts`, `synth6581.test.ts`, `synth7-bank.test.ts`, `synth7-score.test.ts`, `midi-file.test.ts`, `instrument-sounds.test.ts`, and the sound cases of `server-rules.test.ts`). What replaces them (the generated types and the send calls) is the TypeScript document's. The Python kit has no such code today and MUST gain none (S6581-52, MIDI-22).
- Reason: DEC-6462 items 3 and "What it changes" ("the kit's sound code shrinks to types and calls: a breaking change to the kit"); MIDI-22; MIDI-112 (`midi-file.ts` is removed); S6581-52 (the note helpers are withdrawn). Which of the listed files hold only types or send calls is for the TypeScript document to settle; none of their logic remains.
- Source: The kit's `src/sound/` and `src/wire/` (4,279 lines in `src/sound/` on 18 November 2026); MIDI-22, MIDI-112; S6581-52; `midi-architecture.md` section 21 item 14.
- Verification: Inspection of both kits; the TypeScript kit's line count of `src/sound/` before and after, in the release's notes.

**SRV-101. The channels that use the old kinds.** Every channel program that sends a protocol 12 synthesizer kind (the audio demo channel, and any other found by a search of the channel repositories for the old kinds) MUST be changed, in the same deployment, to send protocol 13's typed messages, its patches and banks carried over by converting each to the new forms with a one-time script that is not kept.
- Reason: A program speaking protocol 12 cannot run under a server speaking 13 (MIDI-111); the deployment is one cut-over (`../viewer-state.md`).
- Source: MIDI-111; `../viewer-state.md` section 9 (VS-601, VS-602).
- Verification: A search of every channel repository for `_blocks`, `slots`, `images_per_block` in sound messages finds none; the audio demo's sounds play after the deployment.

### 4.15 Order of implementation

**SRV-102. The order.** The work MUST be done in this order, each step through its repository's own process and gates, and each step's commits naming the rdm records they serve:
1. **neoteletext-common:** this document and its set approved and recorded in rdm; `synth-vectors.tsv` written (SRV-94).
2. **The engine:** the event-list reader and writer and the records of option B (MIDI-23 to MIDI-49), the bank codec (MIDI-55, MIDI-56), codes 12 to 19 (MIDI-107), each family's `interface` module (tables, patch packer and check, bank builder and reader, tracker and restatement) and its receiver; the copy of `synth-vectors.tsv`; committed and published at the commit SRV-87 names.
3. **The server, first commit:** the engine pin moved alone (SRV-87).
4. **The server, protocol 13:** the types of section 3, together with `../viewer-state.md`'s (SRV-2); the checks and rules (SRV-49 to SRV-54); packing, banks, blocks, restatement, live sounds, Standard MIDI Files, records and `sound_built` (SRV-47, SRV-55 to SRV-86); the bounds (SRV-90); the removals (SRV-99); `schema-13.json`; the tests, the vectors and the fuzz targets (SRV-92 to SRV-95); the timed test (SRV-91), its figures in the commit.
5. **The browser:** its engine pin moved to step 2's commit (the integration document says what else).
6. **The TypeScript kit:** `protocol-13.json`, the generated types, the removals of SRV-100; a major release.
7. **The Python kit:** `protocol-13.json` and its types (SRV-98).
8. **The channels:** SRV-101.
9. **One deployment** of the server, the browser and every channel together, after confirming the deployment pipeline's backup.
- Reason: Each step needs the one before it: the server calls the engine at a pinned commit; the kits copy the server's schema at a server commit; the channels use the kits; and protocol 13 is one cut-over. It matches `../viewer-state.md`'s order (engine, server, browser, kits, library, channels, one deployment), so the two can share steps 2 to 9.
- Source: DEVELOPMENT.md sections 2.2, 10 and 11; `../viewer-state.md` section 9 (VS-602); MIDI-111.
- Verification: The to-dos of the integration, each closed with its commit in this order.

---

## 5. What is left out

Of the program-facing interface the architecture and the family documents describe, these are not in program protocol 13, each with its reason:

| Left out | Reason | Requirement |
|---|---|---|
| A field carrying a block's, a record's or a bank image's bytes as built by the program | The server builds every block, record and bank (MIDI-13); a program gives events, patches and the interface's own dumps | SRV-10, SRV-20, SRV-21 |
| `slots`, `images_per_block`, `first`, `model`, `chip` | Meaningless when each event carries its own time and each kind names its synthesizer (DEC-6461 item 3; S6581-53 item 5) | SRV-3 |
| A bank, a program change and a note layer for synth6581 and synth8580 | S6581-51, S6581-52; DEC-6465 answer 8 | SRV-25 |
| A Standard MIDI File as the music of a live sound | MIDI-112 gives files to stored sounds; a live sound is fed as it plays, which a file cannot be | SRV-14, SRV-17 |
| Running status carried from one `raw` event into another | Each event is read alone, as each block is (MIDI-12) | SRV-13 |
| A restatement made for one joining connection | DEC-6465 answer 4; MIDI-100 | SRV-69 |
| A request number on a sound message, and an answer to each accepted sound but `sound_built` | DEC-6477 typescript answer 3: sound calls stay unanswered; a refusal and `sound_built` name the sound instead | SRV-47, SRV-48 |
| Global settings of the adopted interfaces (the DX7's function mode settings beyond parameters 64 to 77, the Prophet-5's NRPN 4,096 to 4,109, Deckard's Dream's global bend range) | Each family document leaves them out with its reason; no event variant or parameter names them | S7-33, S53-27, S80-7 |
| A `sound_built` answer for live sounds and banks | Their sizes are what the program sent or does not end; the refusal is the only answer a program needs | SRV-47 |
| Any check in a kit beyond the schema | DEC-6462 item 3 | SRV-52 |

---

## 6. What NeoTeletext defines itself

Each item exists because neither MIDI 1.0, Standard MIDI Files 1.0, the architecture nor a family document defines it; the architecture leaves the program-facing names to this document (its scope: "It does not name the JSON fields of the program protocol (the server document does)").

1. **Every name of section 3**: the kinds' Rust types, every field, every variant, every `event`, `form` and parameter name, and the `Rule` values of SRV-51. The family documents fixed the rules for some names (S53-47's naming rule; S106-36's fields; S80-41's "one name for each of the 85 controls"); the rest are this document's, written as the family documents' own names for each parameter in lower case with words joined by underscores.
2. **`_events` in place of `_blocks`** for the third kind (SRV-4), which S6581-53 left to this document.
3. **MIDI channels written 1 to 16** in typed events (SRV-7).
4. **`time_us`, `length_us`, `tail_us` and `until_us`** as the names of MIDI-17, MIDI-19 and MIDI-20's times, and the block count of a tail (SRV-9), whose second term keeps the last event's block in the sound.
5. **A bank select only as fields of a program change, and a parameter number only with its data or step** (SRV-10), so that MIDI-37's groups cannot be split by the shape of a typed event.
6. **The value 0 written for controllers 96 and 97** (SRV-11).
7. **Running status bounded to one `raw` event** (SRV-13).
8. **The named fields of the control-value families as controller values** (SRV-34, SRV-40, SRV-43): synthD's, synth8's and synth80's fields carry the value of their controller (or pair) by name, not a decoded position, so that fields and bytes round-trip exactly (DEC-6477 answer 1).
9. **synth7's operators listed operator 1 first** (SRV-26), and the voice name as printable text in the fields form.
10. **synth53's parameter 20 left out of the named fields** and written from the kind (SRV-37), because a field the server overwrites would be the revision field DEC-6461 item 3 removed; S53-47 spoke of 67 named parameters.
11. **synth80's tone as fields or a preset name** (SRV-43), the form S80-42 and S80-43 ask the server to support.
12. **synth60's switch parameters written as JU-06A controllers** (SRV-33), so that a real-time change of one switch does not reset another (S106-32).
13. **The most banks of each family** (SRV-58), stated by `synth7.md` for synth7 and here for the rest, by the same reason.
14. **The bank table, the live table and sending a bank on demand** (SRV-59, SRV-61, SRV-72), which MIDI-57 and MIDI-20 imply but do not specify.
15. **Which system exclusive messages are lifted as bank dumps** (SRV-63): synth7's 32-voice dump and the synth53 family's program dumps, and not the synth106 family's patch message.
16. **A live sound announced again to bring in a new connection** (SRV-73).
17. **`not_before_until`, `until_moved_back`** and the order of events across messages (SRV-74, SRV-75).
18. **`sound_built`** (SRV-47), the answer MIDI-118 asks for, given for every stored sound.
19. **`synth-vectors.tsv`** and its columns (SRV-94).
20. **The engine's `interface` feature and the trackers in the engine** (SRV-87, SRV-88, SRV-68; DEC-6477 answer 5).
21. **Restatement at tick 0** of the block chosen (SRV-69).
22. **`Refused`'s `sound` field** (SRV-48), which names the sound a refusal concerns (DEC-6477).
23. **A stored sound's `banks` empty when `lift_banks` names its banks** (SRV-16), MIDI-57's count being read on the OBJECT's tag 4.
24. **The pacing of live blocks, held at most 25 blocks ahead of the live sound's clock** (SRV-77), the figure `integration.md` INT-18 defines.

---

## 7. Open questions for the owner

Every question of this section was answered by DEC-6477 (18 November 2026, at the owner's delegation, awaiting the owner's review); each answer is recorded under its question, and the requirements cited follow it.

**1. Named fields of synthD, synth8 and synth80: controller values, or typed positions?** *Answered by DEC-6477 (answer 1): option A, raw controller values, as written (SRV-34, SRV-40, SRV-43).*
- *Option A* (written): every field is its controller's value, 0 to 127 (synthD's pairs 0 to 16,383); a switch is "off" at 0 to 63 and a selector's position follows the family document's bands. Exact round trip with the bytes form; the interface's own units (DEC-6453); nothing for the server to scale.
- *Option B:* switches as `bool` and selectors as enums of their positions (for example synthD's oscillator ranges as `lo`, `feet_32`, `feet_16`, `feet_8`, `feet_4`, `feet_2`), the server writing canonical values. Friendlier to write; the bands of S8-21, S8-30, S80-15 and SD-20 move into the schema, and a value read back from bytes that is not canonical cannot be shown exactly.
- *Recommendation:* A now. B can be added later as a third `form` of the patch without breaking A, at the cost of a protocol version.

**2. Should the server keep a live sound within the receiver's ring?** *Answered by DEC-6477 (answer 2): option B, as `integration.md` INT-18 has it, against this document's first recommendation: the server holds completed blocks and sends each at most 25 blocks ahead of the live sound's clock, because DEC-6462 puts the work in the server and a thin kit cannot know a receiver's ring. SRV-74, SRV-77 and SRV-90 are amended accordingly.*
A receiver keeps 32 blocks; MIDI-20 lets one message advance 100. A program that runs more than 32 blocks ahead loses audio at every receiver.
- *Option A* (first written): the server sends blocks as they complete; the schema's documentation tells programs to keep within 29 blocks.
- *Option B:* the server holds completed blocks and releases them on its own clock, at most 29 ahead of the live sound's start time as it measures it.
- *Option C:* the server refuses an events message that would put `until_us` more than 29 blocks ahead of its own clock.
- *Recommendation first written:* A. B and C need the runtime to read a clock it is given by its host and would make the server's output depend on its timing; the demo channel already paces correctly. DEC-6477 chose B.

**3. If the viewer state mechanism and the synthesizers' interface are not ready together.** *Answered by DEC-6477 (answer 3): option A, one protocol 13 and one push protocol version (the engine's 8), in one deployment; whichever is ready first waits (SRV-2).*
- *Option A* (written): one protocol 13 holding both (SRV-2); whichever is ready first waits.
- *Option B:* whichever is ready first is protocol 13, and the other protocol 14, each document renamed.
- *Recommendation:* A, as `../viewer-state.md` plans one cut-over of every repository; B if one of the two is held back by an unanswered question for more than a few weeks.

**4. Sending banks on demand.** *Answered by DEC-6477 (answer 4): option A, as written (SRV-59, SRV-61).*
- *Option A* (written): the server keeps the program's banks and sends each to a connection before the first sound that needs it (SRV-59, SRV-61).
- *Option B:* the program sends each bank to each connection itself and the server only checks it was sent.
- *Recommendation:* A: it is the only way MIDI-57's "the server MUST send every bank a sound names before the sound's OBJECT record" holds for a viewer who arrives later, without every program tracking who has what. Its cost is up to 4 MiB a channel program (SRV-59).

**5. The trackers and restatements in the engine.** *Answered by DEC-6477 (answer 5): option A, as written (SRV-68, SRV-88).*
- *Option A* (written): each family's tracker and restatement writer are the engine's, in the `interface` module (SRV-68, SRV-88).
- *Option B:* they are the server's, written from the family documents.
- *Recommendation:* A: the restatement must put a fresh synthesizer into the sender's state (MIDI-93), which the engine's tests can check against the real synthesizer; the tracker reads the same message tables the receiver uses; and the server stays free of family tables (SRV-53). This places new code in the engine, which is an architectural choice for the owner.

---

## 8. Differences from what is built today

What exists is the server at `df662b9`, the TypeScript kit at `6d54c3d` and the Python kit as of 18 November 2026 (section 1.3).

**The protocol.**
1. `PROTOCOL` 12 becomes 13, `schema-12.json` becomes `schema-13.json` (SRV-1), with `../viewer-state.md`'s changes in the same version (SRV-2). `SAFE_INTEGER_LIMIT` is defined in `protocol.rs` (SRV-2).
2. The 51 `Sound` variants become 9 (Opus, PCM, commands) plus 42 synthesizer kinds; `_blocks` becomes `_events`; the synth6581 family keeps no bank kind, as today (SRV-3, SRV-4).
3. A synthesizer sound today carries base64 of 4-byte slots or 25-byte register images and a `bank` handle; it will carry `banks`, `lift_banks`, `length` and `music` (SRV-16); a live sound and an events message change the same way (SRV-17, SRV-18).
4. A bank today is base64 of NeoTeletext's own 128-, 18-, 36-, 24-, 43- or 85-byte layouts, 1 to 32 patches; it will be a list of patches as fields or bytes, or the interface's bank image, up to each family's most (SRV-19 to SRV-21 and section 3).
5. Program changes reach 0 to 127; every MIDI message is typed; system exclusive can be expressed (SRV-10).
6. `ServerMessage` gains `sound_built` (SRV-47); `Refused` gains `sound` (SRV-48); `Rule` gains 25 values (SRV-51); `Base64` is marked `contentEncoding: "base64"` in the schema (SRV-6).

**The server.**
7. The server today checks slots and patches with its own copy of rules (`protocol/check/instrument.rs`, `instrument/patch.rs`) and writes codecs 3 to 11's records itself (`sound/instrument.rs`); it will call the engine for every check and every record (SRV-53, SRV-87 to SRV-89), and those files are deleted (SRV-99).
8. The server gains the bank table, the live table, the trackers, restatement, a Standard MIDI File reader, and `sound_built` (sections 4.3 to 4.8). Live blocks, which the server today forwards as the program sends them, are paced to at most 25 blocks ahead of the live sound's clock (SRV-77).
9. The engine pin moves from `4ddd34be` to the commit of SRV-87, and the server depends on `neoteletext-audio-instruments` for the first time (SRV-87).
10. The fuzz target `instrument_sound` is replaced by four (SRV-92).

**The kits and the channels.**
11. The TypeScript kit's sound logic (about 4,300 lines) is removed (SRV-100); the Python kit gains only the copied schema and types (SRV-98).
12. The audio demo channel and any other program of the old kinds is rewritten (SRV-101).
