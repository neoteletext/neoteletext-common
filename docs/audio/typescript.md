# Programming the synthesizers from TypeScript

**Purpose.** This document specifies how a channel's program written in TypeScript plays and programs NeoTeletext's eleven synthesizers through the TypeScript kit, `neoteletext-server-ts-protocol`: how the kit takes the server's generated schema of program protocol 13, how its TypeScript types come from that schema, the thin calls a program makes, what the kit checks and what it leaves to the server, the test harness a channel's tests use, what becomes of every module of the kit's sound code today, the release that makes the change, how the audio demo channel moves to it, and worked examples of a program playing each family. It is the basis for implementing the kit's side of the synthesizers' programming interface.

**Scope.** It covers the TypeScript kit and the audio demo channel that uses it. It does not define any message, field, type, bound or refusal of program protocol 13: the server document of this set, `server.md` in this folder (prefix SRV-), is the main specification of the program-protocol-13 sound messages and defines every one of them, generated from the server's Rust types as `protocol/schema-13.json`. Where this document names a message, a kind, a field or a refusal, it names the server document's, and where the two disagree the server document holds and this document is corrected (TS-4). It does not specify any synthesizer's messages, patches or banks (the family documents do), nor the architecture's blocks and records (`midi-architecture.md`, prefix MIDI-, does), nor the Python kit (`python.md`, prefix PY-, does; this document and it are written to give the two kits the same calls, TS-2), nor the viewer's state (`../viewer-state.md`, prefix VS-, does; TS-28 only places its calls beside the sound calls, for completeness).

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement of the repository it names: the TypeScript kit (`neoteletext-server-ts-protocol`) for TS-1 to TS-37 and TS-43, the audio demo channel (`neoteletext-server-channel-audiodemo`) for TS-38 to TS-42.

Which instrument each synthesizer models is said once, in `synthesizers.md` in this folder, with the trademark statement.

**What this document decides, in brief** (each item is specified by the requirements cited):
1. The kit holds no instrument logic: no patch packing, no block or record building, no Standard MIDI File reading, no restatement, no copy of a server rule beyond what the schema states (TS-1, TS-3, TS-4).
2. The kit's calls and harness are the Python kit's, name for name, held to one shared list (`docs/audio/kit-calls.tsv`) and one shared fixture of the worked examples' lines (`docs/audio/examples.jsonl`), both in neoteletext-common (TS-2).
3. The kit takes the server's `protocol/schema-13.json` as a byte-for-byte copy, `schema/protocol-13.json`, pinned to the server commit `SCHEMA_FROM` names, checked by the commit gate as today (TS-5 to TS-7).
4. **The kit's TypeScript types for the protocol are generated from the schema**, by a generator of the kit's own (`scripts/types.ts`, no new library), into `src/wire/generated/protocol.d.ts`, never edited, never committed, rebuilt by the commit gate's new step "the types, from the server's schema"; hand-written types checked against the schema were considered and rejected (TS-8 to TS-15).
5. The kit validates a program's message with the validators precompiled from the schema, and nothing else; every other rule is the server's, learned from its typed refusal (TS-16 to TS-18).
6. A program sends every sound message, of every kind, with one call, `context.sound(to, member)`, whose member is a value of a generated member type; it hears the server's refusals and its reports of sounds through application handlers, each naming the sound it concerns; bytes are `Uint8Array`, as the schema marks every bytes field base64 (TS-19 to TS-28).
7. The test harness records every sound message as its generated member type and lets a test answer one with a refusal or a report the schema allows; one test runs the examples against the real server (TS-29 to TS-33).
8. The change is kit release 15.0.0, a breaking release made together with protocol 13's other changes (TS-34, TS-35).
9. Every module of today's `src/sound/`, and the wire, testing and test files that touch the synthesizers, is listed with its fate (TS-36), and the kit's guide says only what the kit does (TS-37); every sound file of the audio demo is listed with what it becomes (TS-38 to TS-42).
10. Seven worked examples, the same seven `python.md` gives, are compiled and run as the kit's tests on shared inputs and scenarios (TS-43, section 4).
11. Every open question of this document was answered by DEC-6477 (section 7), and the documents' conflicts were settled by it: names follow `server.md` everywhere (section 8).

---

## 1. Sources

### 1.1 Decisions

| Decision | What this document takes from it |
|---|---|
| DEC-6462 | The Rust server is the core of the synthesizers' programming interface. Item 1: a program sends structured, typed JSON at the level of the adopted interfaces (a patch as named, typed fields or as its standard system exclusive; music as timed MIDI events or a Standard MIDI File; a bank as a list of patches; a play, stop or gain), and the server validates it, builds blocks and records, splits what is too long and restates for late joiners. Item 2: Rust types first, the JSON Schema generated from them, every rule a schema cannot state checked by the server with a typed refusal, shared fixtures and vectors. Item 3: the kits are thin, "types generated from, or checked against, the server's schema, and the calls that send them", with "no packing, no block building, no file parsing, no copies of the server's rules beyond what the schema gives"; "The TypeScript and Python kits are equals; neither can do what the other cannot". Item 4: this document is short beside the server's and describes the generated types and how to call them. "What it changes": the kit's sound code shrinks to types and calls, a breaking change to the kit. |
| DEC-6461 | The eleven names, each its own kind. |
| DEC-6453 | Each instrument is programmed as its adopted interface does it; nothing invented while something exists. |
| DEC-6464 version 2 and DEC-6473 (awaiting the owner's confirmation) | One behaviour for every synthesizer where MIDI defines a common one, and three readings of RP-015 and MIDI 1.0; server and receiver work, which leaves the kit untouched. |
| DEC-6465 (awaiting the owner's confirmation) | The answers to the synthesizer documents' open questions; answer 8: no note-playing layer for synth6581 and synth8580 anywhere in NeoTeletext, and "note help belongs in an example channel program". |
| DEC-6471 (accepted 18 November 2026) and `../viewer-state.md` | Program protocol 13's other changes (cookies and the server session removed, a viewer handle, `gone`), and the kit's release 15.0.0 that speaks it (VS-351 to VS-354, VS-401 to VS-404; section 14.4: "protocol 13 types generated from the schema … A major release (15.0.0)"). |
| DEC-1482 item 7, and DEC-2766 and DEC-2768 (split from REQ-1479) | Messages are JSON lines; the schema generated from the server's Rust types is the contract; the kit validates with validators precompiled by Ajv's standalone mode. |
| DEC-6443 | Every browser tab is a connection of its own to applications (kit 13.0.0). |
| DEC-6477 (awaiting the owner's review) | The answers to this document's six open questions and to those of `server.md`, `python.md` and `integration.md`, at the owner's delegation, and the settlement of the documents' conflicts: names follow `server.md`; every bytes field is marked `contentEncoding: "base64"`; no library generates types; sound calls stay unanswered, every refusal and `sound_built` naming the sound; every hand-written protocol type goes in 15.0.0; the kit's Opus and sample checks go; a repeated live announcement sends the OBJECT only. It governs where this document first said otherwise. |
| DEC-6474 | The Python kit validates at run time with `jsonschema`, is kept fully equal to this kit, and generates its types. |

### 1.2 The documents of this set

| Document | What this document takes from it |
|---|---|
| `server.md` (this folder), complete | SRV-1 (protocol 13, `protocol/schema-13.json`); SRV-2 (one protocol 13 with `viewer-state.md`'s messages); SRV-3 (the 42 synthesizer kinds: `<name>`, `<name>_live`, `<name>_events`, `<name>_bank`, and the Rust type names, each a named type of `$defs`); SRV-4 (`<name>_blocks` is no kind of protocol 13); SRV-5 (`connections`, `handle`, `generation`); SRV-6 (bytes as `Base64`); SRV-7 (`channel` 1 to 16); SRV-8 (`time_us`); SRV-9 (`length`, `{"length_us": n}` or `{"tail_us": n}`); SRV-10 (the events, tagged by `event`); SRV-12 (synth6581's `register_update` and `asid` events and the 28 register fields); SRV-14 (`music`, tagged by `form`: `events` or `midi_file`); SRV-15 (`lift_banks`); SRV-16 to SRV-19 (the fields of a stored sound, a live sound, an events message with `until_us`, and a bank message with `bank`); SRV-20 and SRV-21 (a bank and a patch, each tagged by `form`: `patches` or `bytes`, `fields` or `bytes`); SRV-22 (a parameter event's `set`); SRV-23 (`channel_map`, 16 entries); SRV-26 to SRV-45 (each family's patch fields, bytes, banks and named parameters, which the examples spell); SRV-46 (`play`, `stop`, `gain` unchanged); SRV-47 (the report `sound_built`, naming the sound); SRV-48 (`refused` naming the sound in its `sound` field); SRV-51 (the refusal rules); SRV-52 (no kit holds a copy of them); SRV-73 (a repeated live announcement); SRV-74 and SRV-77 (`until_us` and the server's pacing); SRV-97 (the kit's schema copy); SRV-100 (the kit's sound logic removed). |
| `python.md` (this folder) | PY-10 (the generated types' names, word for word TS-10's); PY-12 (member types); PY-13 (bytes as bytes where the schema marks `contentEncoding: "base64"`); PY-18 and PY-19 (the kits' calls equal, held to `docs/audio/kit-calls.tsv`); PY-20 (`sound`, one call for every sound, writing one line a chunk of connections); PY-21 (the hearers, without sessions); PY-24 and PY-25 (refusals and the server's reports of sounds reach handlers); PY-34 (no sound call waits on the server); PY-44 and PY-45 (the harness's `sounds` and its kin, `refuse`, `report`); PY-47 (a test against the real server); PY-48 (`docs/audio/examples.jsonl`); section 5 (the seven worked examples). |
| `midi-architecture.md` (this folder) | MIDI-13 (no program and no kit writes a block, a record or a bank image), MIDI-14 (a patch as named fields or the interface's bytes), MIDI-15 (a bank as a list or a dump), MIDI-16 (music as timed events), MIDI-17 (time in whole microseconds), MIDI-18 (a named parameter), MIDI-19 (a stored sound's length or tail), MIDI-20 (a live sound's events messages and `until`), MIDI-21 (the server's refusal names the field's path, the rule and the detail), MIDI-22 (the kits are thin; their types generated from, or checked against, the schema), MIDI-58 (bank dumps lifted out of music), MIDI-111 (protocol 13), MIDI-112 (the kits never read Standard MIDI Files; `midi-file.ts` is removed), MIDI-118 (the server reports what it dropped from a file "in its answer"). |
| `synth6581-synth8580.md` | S6581-51 (no bank; a kit holds no patches), S6581-52 (no note layer; `synth6581Note`, `synth6581Gate` and `synth6581HardRestart` leave the kit), S6581-53 (what the protocol gives these synthesizers), S6581-54 (a kit holds no copy of the server's rules), section 9.2 items 13 to 15 (what leaves the kit; what the audio demo must do). |
| `synth7.md`, `synth106-synth60.md`, `synthd.md`, `synth53-synth52-synth51.md`, `synth8.md`, `synth80.md` | Each family's patch and bank forms as a program gives them, and the kit code each says moves into the server (`synth7.md` section 17 items 12 and 17; `synth106-synth60.md` section 18 item 14; `synthd.md` section 15 items 4, 7 and 13; `synth53-synth52-synth51.md` S53-47 and section 16 items 15 and 16, whose verification asks that "the TypeScript and Python kits send identical messages for the same program"; `synth8.md` section 15 items 4, 8 and 15; `synth80.md` S80-41 and section 17 items 7, 9 and 16). |

### 1.3 What is built today, read on 18 November 2026

| Source | Commit | What it is used for here |
|---|---|---|
| The TypeScript kit, `~/devel/neoteletext-server-ts-protocol` | `6d54c3d` (release 14.0.0, protocol 12) | `src/sound/` (36 modules), `src/wire/` (`protocol.ts`, `validate.ts`, `instrument-wire.ts`, `instrument-rules.ts`, `sound-rules.ts`, `server-rules.ts`, `limits.ts`), `src/channel/` (`context.ts`, `application.ts`, `channel.ts`, `sender.ts`, `connections.ts`, `measures.ts`), `src/testing/` (`harness.ts`, `sent.ts`), `scripts/check.sh` (`SCHEMA_FROM`, the `schema` step), `scripts/validators.ts`, `scripts/release.sh`, `knip.jsonc`, and the tests. Section 3.8 lists every file this document touches. |
| The server, `~/devel/neoteletext-app-server` | `df662b9` | `crates/teletext-runtime/src/protocol.rs` (the `Sound` enum, `Refused`, `Rule`, `MessageType`; `PROTOCOL` = 12) and `protocol/schema-12.json`, whose keywords and shape section 3.3 rests on. |
| The audio demo channel, `~/devel/neoteletext-server-channel-audiodemo` | `3dc1d68` (kit 14.0.0) | Every source and test file, for section 3.9. |
| The Python kit, `~/devel/neoteletext-server-channels/kits/python` | as checked out | Its schema copy (`protocol-12.json`), for the equality of the two kits. |
| `~/devel/neoteletext-common/wire-vectors.tsv` | as checked out | The shared table of wire values both repositories run, the model for TS-2's shared files. |

---

## 2. Terms

- **The kit.** `neoteletext-server-ts-protocol`, the TypeScript kit with which a channel's program speaks the program protocol to the server.
- **The server.** `neoteletext-app-server`, the one implementation of the synthesizers' programming interface (DEC-6462).
- **The server document.** `server.md` in this folder.
- **The schema.** The JSON Schema the server generates from its Rust types with the `schemars` derive: `protocol/schema-13.json` in the server's repository. **The schema's copy** is the kit's `schema/protocol-13.json`.
- **Generated types.** The TypeScript types the kit's generator (TS-9) writes from the schema's copy.
- **Wire type.** The generated type of a message, or of one kind of the `sound` message, exactly as the line carries it with its tag (for example `SoundSynth7Bank`, with `kind`, `connections`, `handle`, `generation` and `bank`, named by TS-10 rule 2 from the `Sound` union and the kind; the server's `Synth7BankSound`, the same fields without the tag, is its definition in `$defs`).
- **Member type.** A wire type without the fields the kit fills, `type` and `connections`, named the wire type's name followed by `Member` (`SoundSynth7BankMember`); `SoundMember` is the union of every kind's member type (TS-11, as PY-12).
- **Validators.** The validation functions Ajv's standalone mode compiles from the schema's copy (`scripts/validators.ts`, as built), one for each program message and each server message by its `type`.
- **Instrument logic.** Anything that knows what a synthesizer, a MIDI message, a patch, a bank, a block, a tick or a Standard MIDI File means beyond what the schema states: packing or unpacking a patch, building or reading a block, placing an event in time, restating, reading a file, checking a range the schema does not state.
- **A synthesizer message.** A program's `sound` message of one of the 42 synthesizer kinds of SRV-3.
- **A refusal.** The server's `refused` message: the message type refused, the path of the first fault, the rule broken from the closed list `Rule`, the detail in words, for the messages that carry one a request number, and for a refused sound the sound it concerns, its kind, handle and generation (REQ-1475; SRV-48).
- **A report of a sound.** A message the server document defines that the server sends a program about a sound it has taken: `sound_built` (SRV-47), which names the sound and carries MIDI-118's counts of what a file's reading dropped and MIDI-58's lifted banks.
- **Audience.** The kit's statement of who hears a message, which the kit turns into the message's `connections` (TS-20).
- **The audio demo.** The channel `neoteletext-server-channel-audiodemo`, the test channel of the instrument sounds.
- **The harness.** The kit's `Harness` (`neoteletext-server-ts-protocol/testing`), which drives a channel as the server drives it, for tests.

Numbers written `0x…` are hexadecimal. A "commit gate", "push gate" and "full gate" are DEVELOPMENT.md section 9.2's tiers.

---

## 3. Requirements

### 3.1 The kit's place

**TS-1. The kit holds no instrument logic.** The kit MUST NOT contain, for any synthesizer: patch packing or unpacking in any form (named fields to bytes, bytes to fields, system exclusive checksums, packed and unpacked voices); building, splitting or reading blocks, slots, register images, event lists, records or bank images; placing events in blocks or ticks, or rounding times; restating a live sound's state, repeating program changes, or tracking a part's state; reading or writing Standard MIDI Files or system exclusive files; converting notes to registers, frequencies to register values, or panel units to controller values; tables of patch fields, controllers, ranges or defaults; a default patch; a clock of a sound, or a block number; or any check of a synthesizer message beyond what the schema's validators make (TS-16, TS-17). What it holds for the synthesizers is exactly: the schema's copy, the generated types and validators, the calls and handlers of section 3.5, the harness of section 3.6, and their tests.
- Reason: DEC-6462 item 3; one implementation, in the server, tested once. A second copy drifts, as today's did: the kit's `synth-patch-rules.ts` is a port of the server's `patch.rs` at `e2f5e1b`, and the server checked DX7 banks less than the receiver while the kit checked them differently again (`synthesizer-wire-format.html` section 12).
- Source: DEC-6462 items 1 and 3; `midi-architecture.md`, MIDI-13 and MIDI-22; `synth6581-synth8580.md`, S6581-52 and S6581-54; `python.md`, PY-28 (the same list for the Python kit).
- Verification: Inspection of the release's source against every item of the list; `test/thin.test.ts`, which lists the files of `src/sound/` and `src/wire/` and checks the list equals the files TS-36 keeps, so that a new module there needs this requirement changed; Knip's check that nothing exported is unused.

**TS-2. The kit is the Python kit's equal.** For every synthesizer message, every other protocol-13 message and every harness scenario, the kit MUST offer exactly the calls, handlers and harness calls the Python kit offers, each named as `python.md` PY-18 maps names (the TypeScript kit's `lowerCamelCase`, the Python kit's `snake_case`, its handlers prefixed `on_`), with the same arguments in the same order and the same meaning; neither kit MAY have one the other lacks. Two files in neoteletext-common hold the kits to this:
1. `docs/audio/kit-calls.tsv` (PY-19): after its comment lines (each beginning `#`), a header row and one row a call, handler, audience or harness call, of five tab-separated columns: `what` (`call`, `handler`, `audience` or `harness`), `typescript` (the TypeScript kit's name), `python` (the Python kit's name), `message` (the protocol message it writes or reads, or `-`) and `arguments` (its arguments in order, by meaning, separated by commas). The kit MUST keep a byte-for-byte copy, `kit-calls.tsv` at the kit's root, of the file at the neoteletext-common commit named by `COMMON_FROM` in `scripts/check.sh`, and the commit gate MUST check the copy against that commit as TS-6 checks the schema's. `test/kit-calls.test.ts` MUST compare the kit's public interface with the copy: the methods of `Context` (by its prototype), the optional handlers of `Application` (by `src/channel/handlers.ts`, a list of their names declared `satisfies readonly (keyof Application)[]` and held by a type-level assertion to name every optional method of `Application` and nothing else), and the methods of `Harness`; a call or handler missing from the file, in the file and missing from the kit, or with other arguments, MUST fail the test.
2. `docs/audio/examples.jsonl` (PY-48): one line a `sound` message, as the program of each worked example of section 4 writes it on the inputs and in the scenario of section 4.0, each line a JSON object of exactly `example` (the example's name of section 4.0) and `message` (the message with its `type` and `connections`). The kit MUST keep a byte-for-byte copy, `test/fixtures/examples.jsonl`, of the file at `COMMON_FROM`, checked by the same gate step, and each example's test (TS-43) MUST check that the `sound` lines it writes equal, in order, the `message` of the file's lines for that example, as parsed JSON values.
- Reason: DEC-6462 item 3 ("The TypeScript and Python kits are equals; neither can do what the other cannot"); `synth53-synth52-synth51.md`, S53-47's verification ("the kits' tests check that the TypeScript and Python kits send identical messages for the same program"); equality that is not checked drifts. Shared files are how the repositories already hold each other to shared values (`wire-vectors.tsv`).
- Source: DEC-6462 items 2 and 3; S53-47; `python.md`, PY-18, PY-19 and PY-48; `wire-vectors.tsv`'s practice.
- Verification: `test/kit-calls.test.ts`, run with one method added to `Context` (fails naming it) and with one row removed from the copy (fails naming the call); the examples' tests. neoteletext-common's commit that adds the two files checks that every line of `examples.jsonl` holds the field names and required fields `server.md` gives its kind (a script of the session, not kept, run on 18 November 2026).

**TS-3. The kit speaks protocol 13 only.** Release 15.0.0 and later MUST say protocol 13 and nothing else, MUST stop at a `start` of another version as today, naming both versions, and MUST hold no type, call or path of protocol 12. `PROTOCOL` in `src/wire/limits.ts` MUST equal the `const` of the `protocol` field of the schema's `start` message (13).
- Reason: The protocol's rule of one number, raised on every change of shape (REQ-2215; MIDI-111; SRV-1); no compatibility shims (DEVELOPMENT.md section 2.1).
- Source: MIDI-111; SRV-1; REQ-2215; `viewer-state.md`, VS-351, VS-352; `python.md`, PY-4.
- Verification: `test/schema-facts.test.ts` reads the schema's copy and compares; the existing version test.

**TS-4. The server document defines; this document follows.** Every message, kind, field, type, bound, closed list and refusal rule the kit's calls send or receive MUST be the server document's, as the schema states it. The kit MUST NOT add a field, rename one, give one a default, or narrow or widen a bound. Where this document's text or examples differ from the server document, the server document MUST hold and this document MUST be corrected before the requirement concerned is built.
- Reason: DEC-6462 item 4: the server document is the main specification; this document describes the generated types and how to call them.
- Source: DEC-6462 item 4.
- Verification: Generation (TS-8) makes the types the schema's; the compiled examples (TS-43) fail to compile when a field differs.

### 3.2 The schema's copy

**TS-5. The copy.** The kit MUST hold `schema/protocol-13.json`, a byte-for-byte copy of the server's `protocol/schema-13.json` at the server commit named by `SCHEMA_FROM` in `scripts/check.sh`, and MUST hold no other schema: `schema/protocol-12.json` MUST be deleted in the commit that adds it. `SCHEMA_FROM` MUST name the same server commit as the Python kit's release of the same protocol change (PY-3).
- Reason: The schema is the contract (DEC-6462 item 2); a copy pinned to a commit lets the kit's build be reproduced and its changes reviewed, as today; one commit for both kits means one contract.
- Source: As built (`scripts/check.sh`, `SCHEMA_FROM`, `schema()`); DEC-6462, "What exists today", item 3; `python.md`, PY-3.
- Verification: The commit gate's step of TS-6; a review of each schema commit against the Python kit's.

**TS-6. The commit gate's `schema` step.** The commit gate MUST run, before every other step that reads the schema, a step named "schema/protocol-13.json is the server's protocol/schema-13.json at <the first seven characters of SCHEMA_FROM>" that: fails, saying the server's repository is needed at `$NEOTELETEXT_SERVER` (default `~/devel/neoteletext-app-server`), when that repository cannot be read; fails, naming the commit, when the server has no `protocol/schema-13.json` at `SCHEMA_FROM`; and fails, saying "copy that file, or name in scripts/check.sh the commit the copy is from", when the two differ in any byte (compared with `cmp`). It is today's `schema()` function with the file names changed, and it MUST go on reading the server's repository with `GIT_DIR`, `GIT_INDEX_FILE` and `GIT_WORK_TREE` unset (`server_git`). A second step, "kit-calls.tsv and examples.jsonl are neoteletext-common's at <the first seven characters of COMMON_FROM>", MUST check TS-2's two copies the same way against `$NEOTELETEXT_COMMON` (default `~/devel/neoteletext-common`).
- Reason: As built; the step is what makes a copy a copy.
- Source: `scripts/check.sh` (`schema`, `server_git`).
- Verification: A run of each step with the copy altered by one byte, with the commit naming one without the file, and with the repository's variable naming a missing directory, each failing with its message, recorded in the commit that changes the steps.

**TS-7. Taking a new schema.** A new schema MUST be taken in one commit that copies the server's file, sets `SCHEMA_FROM` to the server commit it is from, and changes whatever the regenerated types make fail to compile; the generated types and validators MUST NOT be committed (they are built by every gate and every build, TS-12); the commit message MUST name the server commit and what the new schema changes for programs.
- Reason: One concept a commit (DEVELOPMENT.md section 10.1); the build is reproduced from the copy alone.
- Source: As built (`scripts/validators.ts`: "built here, never edited, never committed").
- Verification: `.gitignore` names `src/wire/generated/`; a review of each schema commit.

### 3.3 TypeScript types from the schema

**TS-8. The kit's protocol types are generated from the schema.** The TypeScript types of every program message and every server message of protocol 13, and of every type they use, MUST be generated from the schema's copy by the kit's generator (TS-9), and the kit's calls and handlers MUST take and give values of those types. No protocol message's type MAY be written by hand.

This document chose generation over the alternative DEC-6462 item 3 also allows, hand-written types checked against the schema in the commit gate:

| | Generated types (chosen) | Hand-written types, checked (rejected) |
|---|---|---|
| How a type is made | The generator writes it from the schema at every gate and build. | A person writes it, as `protocol.ts` and `instrument-wire.ts` are written today. |
| What the check can prove | That the type is the schema's, by construction: the generator is its only author. | Only that sample values pass both the type and the schema (`test/protocol.test.ts` today "holds a valid value of each type to the schema"); a field the schema has and the hand-written type lacks, or a bound the type states wrongly, passes unless a sample happens to exercise it. A full structural comparison of a hand-written type with the schema needs the TypeScript compiler's type checker driven from a script, which is a second generator in all but name. |
| Size | The synthesizers' patches and parameters alone are hundreds of fields in two forms each: synth7's 155 voice parameters and 14 function parameters, synth80's 85 values, synthD's 39 controls, synth53's 66 program parameters, synth6581's 28 registers, each with its range. | The same hundreds of fields, written and kept in step by hand at every schema change. |
| What it costs | A generator of a few hundred lines for the few keywords `schemars` writes (TS-9), written and tested once. | Every schema change edited twice. |
| What the other documents said | `viewer-state.md` section 14.4: "protocol 13 types generated from the schema"; `python.md`, PY-7: the Python kit's types are generated, by a generator of its own. | DEC-6462 allows it. |

A library that generates types from JSON Schema (for example `json-schema-to-typescript`) was considered and not chosen, because every library needs the owner's approval by name (DEVELOPMENT.md section 7) and the schema uses so few keywords that the kit's own generator is small; DEC-6477 (answer 2) confirmed the kit's own generator.
- Reason: The table. A type that cannot differ from the schema is the strongest form of "types generated from, or checked against, the server's schema".
- Source: DEC-6462 item 3; `midi-architecture.md`, MIDI-22; `viewer-state.md` section 14.4; `python.md`, PY-7; DEVELOPMENT.md section 7.
- Verification: Inspection: `src/wire/` holds no hand-written type of a protocol message; TS-12's gate step; the compiled examples (TS-43).

**TS-9. The generator.** The generator MUST be `scripts/types.ts`, run with Node as `node scripts/types.ts`, written in TypeScript with no dependency but Node's own modules, and MUST read the schema's copy and write `src/wire/generated/protocol.d.ts`. It MUST map each keyword exactly as this table says, and MUST fail, naming the keyword and its path in the schema, on any keyword or combination the table does not list, so that a schema that says more than the generator understands is never turned into a type that says less:

| Keyword (where it appears) | What the generator writes |
|---|---|
| `$defs` (the root) | One exported type for each definition, named as TS-10 says. |
| `$ref` | The referenced definition's type by its name. |
| `$schema`, `title` (the root) | Nothing; `title` elsewhere is written into the type's documentation comment. |
| `description` | The type's or property's documentation comment, verbatim. |
| `type: "object"` with `properties`, `required`, `additionalProperties: false` | An interface whose properties are `readonly`, each required property plain and each other property optional (`?`). An object without `additionalProperties: false` MUST fail generation, since every message of the protocol refuses unknown fields (REQ-1475). |
| `type: "string"` | `string`; with `const`, the string literal; with `enum`, the union of its literals; `pattern`, `minLength` and `maxLength` are written into the documentation comment. |
| `type: "string"` with `contentEncoding: "base64"` | `Uint8Array` (TS-21); the bounds of the decoded bytes, where the description states them, stay in the comment. |
| `type: "integer"` or `"number"` | `number`; `minimum`, `maximum` and `format` are written into the documentation comment. With `const`, the number literal. |
| `type: "boolean"` | `boolean`. |
| `type: "null"`, or a `type` array holding `"null"` | `null` in the union. |
| `type: "array"` with `items`, `minItems`, `maxItems` | `readonly T[]`; with `minItems` equal to `maxItems` and at most 16, a `readonly` tuple of that length (as SRV-23's 16-entry channel map); the bounds in the documentation comment otherwise. |
| `oneOf`, `anyOf` | The union of the branches' types. |
| `allOf` | The intersection of the branches' types (`A & B`), which `schemars` may write for a tagged enum whose variant is a named type. |
| `enum` without `type` | The union of its literals. |
| `const` without `type` | The literal. |
| `default` | The documentation comment ("absent: …"); the property stays optional. |
| `format` | The documentation comment. |

The bounds the generator writes into comments are documentation only: the validators enforce them (TS-16).
- Reason: The schema of protocol 12 uses exactly these keywords but `contentEncoding` and `allOf` (read from `schema/protocol-12.json` on 18 November 2026: `$defs`, `$ref`, `$schema`, `additionalProperties`, `anyOf`, `const`, `default`, `description`, `enum`, `format`, `items`, `maxItems`, `maxLength`, `maximum`, `minItems`, `minLength`, `minimum`, `oneOf`, `pattern`, `properties`, `required`, `title`, `type`). `contentEncoding` is what the server document now writes on every bytes field (SRV-6; DEC-6477), and `allOf` is what `schemars` writes when SRV-3's named types sit under an internally tagged enum. Failing on anything else keeps the generator honest when the server's types grow.
- Source: `schema/protocol-12.json`; `scripts/validators.ts` (its strict Ajv options and integer formats); SRV-3, SRV-6; `python.md`, PY-9 and PY-13; DEVELOPMENT.md section 2.1.
- Verification: `test/types-generator.test.ts`: one case for each row, a small schema and the exact text expected; a case for each keyword the table does not list, checking generation fails naming it; a case of an object without `additionalProperties: false`, failing.

**TS-10. The generated types' names.** The generated types MUST be named by these rules, which are word for word the same in `typescript.md` TS-10 and `python.md` PY-10, so that a type has one name in both kits:
1. Each definition of the schema's `$defs` MUST be one type under its own name, which is the server's Rust type's name (`Refused`, `Rule`, `Sound`, `Synth7BankSound`, `Synth106Panel`, `Synth106Event`).
2. Each branch of a tagged union, that is of a `oneOf` or `anyOf` whose branches each hold a string `const` in a property named `type`, `kind`, `event` or `form`, MUST be one type, the branch whole with its tag, named the union's name followed by the tag's value in upper camel case: the value's parts between underscores, each with its first letter a capital and the rest as written (`Sound` and `synth7_bank` give `SoundSynth7Bank`; `Sound` and `synthd` give `SoundSynthd`; `ProgramMessage` and `sound` give `ProgramMessageSound`; `Synth106Event` and `note_on` give `Synth106EventNoteOn`; `Synth106Patch` and `fields` give `Synth106PatchFields`).
3. Any other object or union the schema writes inline MUST be named its enclosing type's name followed by its property's name in upper camel case (a union written inline as the property `bank` of `Synth7BankSound` is `Synth7BankSoundBank`).
4. A member type (TS-11, PY-12) MUST be named its branch's name followed by `Member` (`SoundSynth7BankMember`, `SoundPlayMember`, `ProgramMessagePageMember`), and the union of every sound kind's member type MUST be named `SoundMember`.
5. Two types MUST NOT receive one name, and no type's name MAY be a reserved word of TypeScript or of Python: the generator MUST fail, naming both paths or the word, rather than number, rename or drop a type.
- Reason: The server names its types (SRV-3 asks that each be a named type of `$defs` so that "the generated TypeScript and Python types" are readable); names derived from the schema's own structure are stable under regeneration, so a channel's code does not break when an unrelated type is added; numbering clashes would make a name depend on order. One rule in both kits gives every type one name in both, so that `kit-calls.tsv`, the guides and the examples read the same (DEC-6462 item 3; DEC-6477).
- Source: SRV-3; `python.md`, PY-10; DEC-6477.
- Verification: `test/types-generator.test.ts`: the names written for a schema of each shape of rules 1 to 4, and a clash and a reserved word failing (rule 5); the same cases as `python.md` PY-10's generator tests, from one table of schemas and names.

**TS-11. Member types.** For every branch of `ProgramMessage` that has a `connections` field, and for every kind of the `sound` message, the generator MUST also write a member type: the wire type without `type` and `connections`, made with TypeScript's own operators from the wire type (never restated), named by TS-10 rule 4 (`SoundSynth7BankMember`, `SoundPlayMember`); and a union `SoundMember` of every sound kind's member type. A program MUST build only member types; the kit adds `type` and `connections` (TS-20).
- Reason: Who a message is for is the kit's to fill from an audience, chunked by `start`'s `budgets.named_connections` as today; the program says what, not to which connection numbers. It is `python.md`'s PY-12, so that both kits' member types have one name.
- Source: `python.md`, PY-12; as built (`src/channel/sender.ts`, `toAudience`).
- Verification: A type test (`test/types/members.test-d.ts`, checked by the type check) that a member built with `connections` or `type` is an error; `test/sound-calls.test.ts` that `sound` fills both.

**TS-12. The gate steps.** The commit gate's `stage` MUST run, in this order: "Node 22.18.0 or later"; "the locked tools (npm ci)" when the lockfile changed; **"the types, from the server's schema"**, which runs `node scripts/types.ts` and then `node scripts/types.ts --check`, the second run regenerating into memory and failing, naming the first differing line, if its text differs from the file the first run wrote (so that generation is deterministic: one schema gives one text); "the validators, from the server's schema (Ajv's standalone mode)", as today; "type check, every strict option, errors fail", as today, which compiles every use of the generated types; then formatting, lint, Knip and the tests, as today. The build (`scripts/check.sh build`) MUST run the generator before `tsc -p tsconfig.build.json` and MUST copy `src/wire/generated/protocol.d.ts` into `dist/wire/generated/` beside the validators. `knip.jsonc` MUST list `scripts/types.ts` as an entry. Prettier and oxlint MUST NOT check `src/wire/generated/`, which a program writes and no person edits; their configurations MUST name it with that reason.
- Reason: The gate rebuilds what is never committed before anything uses it; a determinism check means the generated text changes only when the schema does; the type check is what holds every call to the schema. The Python kit commits its generated module and checks it (PY-14) because it has no build; the TypeScript kit has a build and already leaves its validators uncommitted.
- Source: `scripts/check.sh` (`stage`, `build`); DEVELOPMENT.md section 9.2; `python.md`, PY-14.
- Verification: A run of the commit gate on a clean checkout (no `src/wire/generated/`), passing; a run with the schema's copy changed to rename one sound field, failing at the type check with the example that uses it named.

**TS-13. Generated types carry their documentation.** Every generated type and property MUST carry the schema's description and the bounds of TS-9 in a documentation comment, so that an editor shows a program's author the server's words for every field.
- Reason: The server document's text reaches the author where they write, with no second copy in the kit.
- Source: TS-9; DEVELOPMENT.md section 6 (`missing_docs`).
- Verification: `test/types-generator.test.ts` checks a description and a bound reach the comment.

**TS-14. Generated types are used as they are.** The kit MUST NOT wrap a generated type in a hand-written one that repeats its fields. Where the kit derives a type (a member type, TS-11), it MUST use TypeScript's own operators (`Omit` distributed over a union, `Extract` by a discriminating field), never restate a field.
- Reason: A restated type is a hand-written type (TS-8).
- Source: TS-8.
- Verification: Inspection; the type check.

**TS-15. The hand-written protocol types go.** `src/wire/instrument-wire.ts`, `src/wire/protocol.ts`'s hand-written message types, `src/wire/server-wire.ts`'s and `src/wire/server-message.ts`'s hand-written server message types, and every type of `src/sound/` that describes a protocol message MUST be deleted in release 15.0.0, each use moving to the generated type, for every message of protocol 13 (the pages, input, ReGIS, NAPLPS and every other message as well as the sound messages and the server messages a sound call or handler meets), each in a commit of its own.
- Reason: TS-8; `viewer-state.md` section 14.4 already says "protocol 13 types generated from the schema"; DEC-6477 (typescript answer 4) replaces every hand-written protocol type in 15.0.0, since that release already breaks every sound and session call, so that the protocol is typed one way.
- Source: TS-8; `viewer-state.md` section 14.4; DEC-6477.
- Verification: Inspection of the release.

### 3.4 Validation in the kit

**TS-16. Every message is held to the schema before it is written.** Before writing any program message, after adding `type` and `connections` and after encoding bytes (TS-21), the kit MUST validate it with the validator compiled from the schema for its `type`, as `src/wire/validate.ts` does today; a message that fails MUST NOT be written, in whole or in part, to any connection, and the call MUST throw a `ProtocolError` whose `fault` holds the path of the first fault, the rule in the server's words from the schema's closed list `Rule` (Ajv's `additionalProperties` as `unknown_field`, `required` as `missing_field`, `type`, `pattern` and `format` as `wrong_type`, `const`, `enum`, `oneOf` and `anyOf` as `not_listed`, `minimum` and `maximum` as `out_of_range`, `maxLength` and `maxItems` as `too_long`, `minLength` and `minItems` as `too_short`, the mapping `validate.ts` holds today), and the detail. A call made before `start` MUST throw an `Error` saying so, as today.
- Reason: A program's mistake that the schema can state is reported where it is made, in the words the server would use; this is what the schema gives and nothing more (DEC-6462 item 3). It is `python.md`'s PY-32 and PY-37.
- Source: `src/wire/validate.ts`; DEC-1482 item 7; REQ-1475; `python.md`, PY-32, PY-35, PY-37.
- Verification: `test/sound-validation.test.ts`: for each synthesizer kind, a member with an unknown field, a missing field, a value of the wrong type, a value outside a schema bound and a list longer than a schema bound, each throwing with the expected rule and path and writing nothing.

**TS-17. Nothing else is checked.** The kit MUST NOT check a synthesizer message for anything the schema does not state. In particular it MUST NOT check, and MUST leave to the server's refusal: whether events are in time order, fall in a block already sent, or lie within the sound's length; the advance of `until_us`; whether a bank is held, of the sound's family, or sent before the sound naming it; whether `lift_banks` names as many banks as the music lifts; a patch's or a bank's bytes, header, checksum or length beyond the schema's bounds; whether a family takes a message (SRV-24's `not_taken`); how many events fall in one block or how many bytes a block takes; whether a stored sound begins with the restatement its family requires; a Standard MIDI File's contents; raw MIDI bytes' running status; and, for the sampled sounds, an Opus packet's or a sample's content beyond the schema (DEC-6477 typescript answer 5: the server's refusal reports an Opus packet the receivers would refuse). `src/wire/server-rules.ts` MUST lose its call to `soundFault` for every sound kind, and `src/wire/instrument-rules.ts`, `src/wire/sound-rules.ts`, `src/sound/opus-fields.ts` and `src/sound/opus-packet.ts` MUST be deleted (TS-36).
- Reason: DEC-6462 item 3 ("no copies of the server's rules beyond what the schema gives"); `synth6581-synth8580.md`, S6581-54 ("A kit MUST NOT hold its own copy of these rules beyond what the server's generated schema states … a program learns of a fault from the server's typed refusal"); `python.md`, PY-38.
- Source: DEC-6462 item 3; MIDI-22; S6581-54; PY-38; DEC-6477.
- Verification: `test/sound-validation.test.ts`: for one rule of each item of the list, a member that breaks it and passes the schema is written unchanged, as the harness reads it back.

**TS-18. The server's messages are held to the schema when read.** The kit MUST validate every line the server sends with the validator for its `type`, as today, before acting on it, including refusals and reports of sounds, and MUST give a handler only a validated value of the generated type.
- Reason: As built; nothing acts on a line that is not valid. It is `python.md`'s PY-6 and PY-17.
- Source: `src/wire/validate.ts`; PY-6, PY-17.
- Verification: The existing test that a server line failing the schema is not acted on, extended to a malformed `refused` of a sound and a malformed report.

### 3.5 The calls a program makes

#### 3.5.1 One call for every sound

**TS-19. `context.sound`.** A program MUST send every `sound` message of protocol 13, of every kind the schema gives (each synthesizer's stored sound, live sound, events message and bank; the sampled sounds of Opus and samples; and play, stop and gain), with one call:

```ts
context.sound(to: Audience, member: SoundMember): void
```

It MUST write one `sound` message for each chunk of the audience's connections, at most `start`'s `budgets.named_connections` each, as the kit's `Sender.toAudience` does today, each line the member with `"type": "sound"` and that chunk's `connections` added, after validating every line (TS-16) before writing the first; it MUST write nothing for an audience with no connection. It MUST NOT change, add to, reorder or remove anything of the member but those two fields, except to encode bytes (TS-21). It MUST write before it returns, and lines MUST be written in the order of the calls. It MUST NOT wait for, or give back, anything of the server's. The kit's guide MUST say, where it describes sending a page's sounds, that a program sends a connection a page's play once, when the connection opens the page, and never again while it stays on the page, since a new play starts its sound again (`integration.md` INT-28).
- Reason: The thinnest call there is (DEC-6462 item 3): the program builds the typed member, the kit addresses and writes it. Every kind through one call means a kind the server adds needs a new schema copy and nothing more in the kit. A live sound's events messages must reach the server in order (MIDI-20). It is `python.md`'s PY-20, PY-33 and PY-34.
- Source: DEC-6462 items 1 and 3; as built (`Context.sound`, `Sender.toAudience`); `python.md`, PY-20, PY-33, PY-34.
- Verification: `test/sound-calls.test.ts`: one valid member of every sound kind of the schema's copy (each the example the schema's copy gives for it, or one built in the test) is written as the member with `type` and `connections` added and nothing else; with `named_connections` of 2 and five connections, three lines; two calls' lines in the order of the calls.

**TS-20. Audiences.** An `Audience` MUST be one of: `{ connection: number }` (one connection); `{ page: number }` (every connection whose selection is on the page when the call is made); `{ connections: readonly number[] }` (the connections named); and `{ connections: "all" }` (every connection open, written `"connections": "all"`). Protocol 12's `{ session: number }` MUST be removed, with the server session (VS-354). The set MUST be the Python kit's hearers (`connection_hears`, `page_hears`, `connections_hear`, `everyone_hears`, PY-21), one for one.
- Reason: Under protocol 13 there is no server session (VS-354) and each tab is a connection of its own (DEC-6443, VS-403); a viewer's tabs together are found through the viewer handle, which the program keeps (VS-401). `viewer-state.md` does not name the audience's forms; this requirement does, as `python.md` does for its hearers.
- Source: VS-354, VS-401, VS-403; as built (`src/sound/members.ts`, `Audience`; `src/channel/connections.ts`, `audience`); `python.md`, PY-21.
- Verification: Tests of each audience's connections; `test/kit-calls.test.ts`.

**TS-21. Bytes are bytes.** Every field the schema marks `"contentEncoding": "base64"` MUST be a `Uint8Array` in the generated types (TS-9), and the kit MUST write each such value as its exact base64 text (RFC 4648 section 4, padded, with no line breaks) when it writes the line, and MUST NOT encode any other value. The harness MUST give such fields back as `Uint8Array` (TS-29). The server document marks every bytes field so (SRV-6; DEC-6477 typescript answer 1); the kit MUST NOT guess bytes from a description, and a field the schema does not mark is typed as its schema type says.
- Reason: A patch's system exclusive bytes, raw MIDI bytes and a Standard MIDI File's bytes (MIDI-14, MIDI-16, MIDI-112) are bytes to a program; one rule, applied to every bytes field at the one place the kit writes a line, needs no knowledge of which field is which and is not instrument logic. It is `python.md`'s PY-13.
- Source: SRV-6; DEC-6477; MIDI-14, MIDI-16, MIDI-112; JSON Schema 2020-12 Validation, section 8.3 (`contentEncoding`); RFC 4648 section 4; `python.md`, PY-13.
- Verification: `test/sound-calls.test.ts`: a synth7 patch given as bytes is written as the exact base64 of the bytes; RFC 4648 section 10's test vectors written as the standard gives them; a type test that a `string` given for a bytes field fails to compile.

#### 3.5.2 What the server says back

**TS-22. Refusals reach a handler.** `Application` MUST gain the optional handler `refused?(refusal: Refused, context: Context): void`. When the server sends `refused` that answers no `measure` waiting in the kit (a refusal of a `measure` still rejects that measure's promise, as today, and reaches no handler), the kit MUST call `refused` of every application that has it, in the order the applications were given, with the validated `Refused` unchanged; where no application has it, the kit MUST report it as it does today (`Channel.refused`: "the server refused <message>: <path>: <rule> (<detail>)").
- Reason: Under DEC-6462 the server's typed refusal is how a program learns of every fault the schema cannot state (MIDI-21; S6581-54), so a program must be able to act on it; today it is only logged. A refusal names no application, so every application that wants refusals hears them. It is `python.md`'s PY-24.
- Source: MIDI-21; S6581-54; as built (`Channel.refused`, `Measures.refused`); `python.md`, PY-24.
- Verification: `test/sound-calls.test.ts` with the harness: a refusal of a sound reaches each application's `refused`, typed and unchanged; a refusal of a measurement rejects its promise and reaches no handler; with no handler, the refusal is reported as today.

**TS-23. Reports of sounds reach a handler.** For every message the server document defines that the server sends a program about a sound (today one, `sound_built`, SRV-47, which carries MIDI-118's counts of what a Standard MIDI File's reading dropped and MIDI-58's lifted banks), `Application` MUST gain one optional handler named the message's `type` in lower camel case (`soundBuilt?(report: SoundBuilt, context: Context): void`), and the kit MUST call it of every application that has it, in order, with the validated message unchanged; it MUST NOT interpret, total or keep a report. A report no application handles MUST be passed over without a word.
- Reason: The report is the server's (MIDI-118: the server "MUST report to the program, in its answer, how many of each kind it dropped"); the kit passes it on. It is `python.md`'s PY-25 and PY-26.
- Source: MIDI-58, MIDI-118; SRV-47; `python.md`, PY-25, PY-26.
- Verification: For each report message the schema's copy defines, a test that feeds it to the kit and checks it reaches its handler unchanged.

**TS-24. No sound call waits on the server.** No sound call MUST return a promise, wait for an answer, or match a refusal or a report to the call that caused it; a program that needs to know what became of a sound reads the refusals and reports of TS-22 and TS-23, and matches them by the sound they name: a refusal's `sound` (its kind, handle and generation, SRV-48) and `sound_built`'s `kind`, `handle` and `generation` (SRV-47).
- Reason: The server answers a sound only with a refusal or a report; a call that waited would stall a live sound's feeding. DEC-6477 (typescript answer 3) keeps sound calls unanswered in 15.0.0 and has the server name the sound in every refusal and report, so that handlers can match. It is `python.md`'s PY-34, so the two kits behave alike.
- Source: `python.md`, PY-34; MIDI-20; SRV-47, SRV-48; DEC-6477.
- Verification: The type check: `context.sound` returns `void`; `test/kit-calls.test.ts`.

**TS-25. A refusal is not swallowed.** The kit's guide MUST say that a program that sends sounds has a `refused` handler that does something a person will see (a log line with the path, the rule and the detail at least), and that a `ProtocolError` thrown by `context.sound` is a fault of the program, not to be caught and ignored.
- Reason: A fault reported nowhere is the "silently" this design removes (MIDI-63's reason).
- Source: MIDI-63; DEVELOPMENT.md section 3.4.
- Verification: A review of the guide.

#### 3.5.3 What a program gives

**TS-26. Live sounds, banks, patches and music are members.** A program MUST announce a live synthesizer sound, feed it, send a bank, give a patch and give music only as members of the generated types sent with `context.sound`: a live sound's announcement as its `<name>_live` member and each feeding as its `<name>_events` member, with the events and `until_us` the program computes (SRV-17, SRV-18; MIDI-20); a bank as its `<name>_bank` member, in either form of SRV-20; a patch, inline in an event or in a bank, in either form of SRV-21; a named parameter as SRV-22's `parameter` event; music as SRV-14's `events` or `midi_file` form; a stored sound's length as SRV-9's `length`. The kit MUST offer no object, builder, helper or constant for any of them: no live-sound object holding a handle, no clock, no time conversion, no default patch, no initial voice, no event builder.
- Reason: DEC-6462 items 1 and 3; MIDI-112 ("The kits MUST NOT read Standard MIDI Files"); MIDI-17 (the server rounds, once); `python.md`, PY-28 and PY-30. A helper the Python kit lacks would break TS-2.
- Source: SRV-9, SRV-14, SRV-17 to SRV-22; MIDI-14 to MIDI-20, MIDI-112; DEC-6462 items 1 and 3; PY-28, PY-30.
- Verification: The examples (section 4); `test/thin.test.ts`; `test/kit-calls.test.ts`.

**TS-27. What the kit exports for sound.** The kit's entry point MUST export, for sound, exactly: `Context.sound`; the handlers `refused` and those of TS-23 on `Application`; `Audience`; `ProtocolError`; and the generated wire types, member types, `SoundMember`, `Refused`, `Rule` and the reports' types, from a sub-path `neoteletext-server-ts-protocol/protocol` holding every generated type under its generated name. The kit's Opus encoder (`ffmpegOpus`, `OpusEncoder` and their types) and the audio profile's constants the encoder uses stay, as encoding a program's samples is the program's side (the server's decision 21). Every other sound export of release 14.0.0 MUST be removed (TS-36).
- Reason: The public interface stated whole, so that the release notes, `kit-calls.tsv` and Knip can be held to it.
- Source: `src/index.ts` as built; TS-36.
- Verification: `test/exports.test.ts` lists the entry point's exports and compares with this list.

#### 3.5.4 The viewer handle, for completeness

**TS-28. Viewers beside sounds.** The kit's calls of `viewer-state.md` VS-401 (`viewer` and `remembered` of a connection; `requestState`, `endState`, `offerRemember`; the handlers `viewerBegan`, `viewerLeft`, `stateRefused`, `viewersReset`; and `gone`) MUST be as that document says; this document changes none of them. A sound is addressed to connections or a page (TS-20), never to a viewer handle. A program that keeps a viewer's sound settings (as the audio demo's keyboard page keeps each player's patch) MUST key them on the connection, ending them at `gone` (VS-403), or, where the viewer has state, on the viewer handle under VS-409's rule.
- Reason: The two designs of protocol 13 meet only here; saying so keeps a sound audience by viewer from being invented in the kit.
- Source: `viewer-state.md`, VS-401, VS-403, VS-409.
- Verification: A review of the guide.

### 3.6 The test harness

**TS-29. The harness gives back sounds as members.** The harness MUST keep every line a channel writes, validated against the schema as today, a fault failing the test at once, and MUST offer: `harness.sounds(connection: number): readonly SoundMember[]`, every sound member written to that connection, in order, each without `type` and `connections`, as the program built it, with bytes fields given back as `Uint8Array` (TS-21); `harness.soundsOfKind(connection, kind)`, those of one kind, typed by the kind; and `harness.soundsToEveryone()`, the members written with `"connections": "all"`. `soundBytes` (`src/testing/sent.ts`) MUST be removed.
- Reason: A channel's tests compare what was sent; members typed by the generated types let them do so without parsing by hand, and a test that reads a field the schema lacks fails to compile. It is `python.md`'s PY-44.
- Source: As built (`Harness.sent`, `soundBytes`); `python.md`, PY-44.
- Verification: `test/harness-sounds.test.ts`.

**TS-30. The harness answers only as a test tells it.** The harness MUST offer `harness.refuse(message: SoundMember, path: string, rule: Rule, detail: string)`, which builds the `refused` message the server would send for a sound (`type` `"refused"`, `message` `"sound"`, `sound` naming the member's kind and, where it has them, its handle and generation as SRV-48 says, and the given fields, with whatever else the schema's `Refused` requires), validates it against the schema, fails the test if it is not valid or if `message` was not written by the channel, and gives it to the channel as the server would; and, for each report message the schema defines (TS-23), `harness.report(message: SoundMember, report)`, which validates the report against the schema and gives it to the channel the same way. The harness MUST NOT refuse, report, answer or build anything of its own accord.
- Reason: A channel's tests of its handling of refusals and reports need them in the server's exact shapes; the harness cannot know when the server would refuse without holding the server's rules, which no kit may (TS-1). The closed list `Rule` is the generated type, so a test cannot give a rule the server has not got. It is `python.md`'s PY-45.
- Source: `Refused` and `Rule` (REQ-1475); TS-1, TS-17; `python.md`, PY-45.
- Verification: `test/harness-sounds.test.ts`: a refusal reaches the channel's `refused` with exactly its fields; a refusal with a rule outside the closed list does not compile, and one built by casting fails the test at validation; a refusal naming a member never written fails the test.

**TS-31. The harness restarts.** `harness.restart()` MUST give the channel the server's `start` again, as a server restart does: connection numbers start again; viewer handles do not change (VS-404). A channel's live sounds are then unknown to the server (MIDI-94: the server holds each live sound's state), and a channel's tests can check that it announces them again.
- Reason: A live sound's state is the server's and is lost with it.
- Source: `viewer-state.md`, VS-404 (the harness's server restart); MIDI-94.
- Verification: `test/harness-sounds.test.ts`.

**TS-32. The harness's fake viewers.** The harness MUST offer the fake viewers of `viewer-state.md` VS-404 with the names that requirement gives; this document adds nothing to them.
- Reason: VS-404; `python.md`, PY-49.
- Source: VS-404.
- Verification: As VS-404 says.

**TS-33. One test against the real server.** The kit's tests MUST include `test/server-oracle.test.ts`, which runs a program on the kit under the server's own program runner, on real pipes, with the server built at `SCHEMA_FROM` from `$NEOTELETEXT_SERVER`, sends every worked example's messages of section 4, and checks that the server accepts each (no `refused`) and refuses one deliberately faulty message of each example with the path and rule the server document gives. The test MUST be marked ignored, with the reason "needs neoteletext-app-server built at $NEOTELETEXT_SERVER", when the server is not built, and MUST fail when asked for without it (DEVELOPMENT.md section 8); the push gate MUST print it among the ignored tests when it is.
- Reason: The harness's refusals and reports are the test's word, not the server's (TS-30); only the server can say that an example is right. It is `python.md`'s PY-47.
- Source: DEVELOPMENT.md sections 8 and 9.2; DEC-6462 item 2; `python.md`, PY-47.
- Verification: The test, run by the push gate with the server built.

### 3.7 The release

**TS-34. Release 15.0.0.** The change MUST be released as kit version 15.0.0, a major release, made by `scripts/release.sh` from a commit whose gates pass, and MUST be the same release as `viewer-state.md`'s protocol-13 changes to the kit (its section 14.4 also names 15.0.0), because a program speaking protocol 12 cannot run under a server speaking 13 and protocol 13 is one version (SRV-2). The release notes (the release commit's message, or a `CHANGELOG.md` entry if the kit keeps one) MUST list every export removed (TS-36) by name, each with what replaces it or "removed: the server does this (DEC-6462)", and MUST name the server commit of its schema. No deprecated alias of a removed export MAY be kept.
- Reason: The change removes most of the kit's sound interface and changes every sound call's shape; DEVELOPMENT.md section 2.1 forbids compatibility shims; one protocol version is one release.
- Source: DEC-6462 ("a breaking change to the kit"); SRV-2; `viewer-state.md`, sections 9.1 and 14.4; DEVELOPMENT.md sections 2.1 and 10.
- Verification: The release commit; the tag `v15.0.0`; a review of the notes against TS-36.

**TS-35. Who takes the release.** Every channel and library that depends on the kit MUST move to 15.0.0 in the order `viewer-state.md` section 9.1 gives, and be deployed with the server of protocol 13 in one deployment. The audio demo's move is specified in section 3.9.
- Reason: `viewer-state.md` section 9.1, step 9: "one deployment of the server and every channel together".
- Source: `viewer-state.md`, section 9.1.
- Verification: The deployment record.

### 3.8 What becomes of the kit's sound code

**TS-36. Every module's fate.** Release 15.0.0 MUST do to each file of the kit as these tables say. "Deleted" means the file and every export of it go; "replaced by" names where the work now lives.

*`src/sound/`, the synthesizers (28 modules, 3,413 lines):*

| File (lines) | What it does today | Fate | Replaced by |
|---|---|---|---|
| `instrument-fields.ts` (85) | Writes a synthesizer member as protocol 12's fields, base64, and checks each as the server does | Deleted | Members written as given (TS-19); the server's checks |
| `instrument-members.ts` (106) | Hand-written member types of every synthesizer kind (`Synth6581Sound`, `SynthSound`, `SynthBank`, `Synth8Sound` and their live and blocks forms) | Deleted | Generated wire and member types (TS-8, TS-11) |
| `instrument-profile.ts` (97) | The instrument codecs' constants (`INSTRUMENT_BLOCK_MS`, `MOST_INSTRUMENT_BLOCKS`, `MOST_LIVE_INSTRUMENT_BLOCKS`, `SYNTH6581_IMAGE_BYTES`, `SLOT_BYTES`, `MOST_SLOTS`, `SYNTH7_PATCH_BYTES`, `SYNTH_PATCH_BYTES`, `SYNTHS`, `SYNTH_FAMILY` and others) | Deleted | The schema's bounds, in the generated types' comments (TS-13); the server's and the engine's constants |
| `member-pieces.ts` (58) | Range, handle, base64 and slot-block checks of instrument members | Deleted | The validators (TS-16); the server's checks |
| `midi-bytes.ts` (82) | A bounded reader of a Standard MIDI File's bytes | Deleted | The server's file reader (MIDI-112 to MIDI-119) |
| `midi-file.ts` (229) | Reads a Standard MIDI File into a score of slots | Deleted | The server's file reader; the program sends the file's bytes (TS-26) |
| `patch-field.ts` (28) | Range checks an analogue packer makes | Deleted | The server's encoding of named fields (MIDI-14, SRV-21) |
| `program-repeater.ts` (81) | Repeats each live part's last program change every 500 ms | Deleted | The server's restatement (MIDI-93 to MIDI-99) |
| `slot-score.ts` (168) | Places timed events into blocks of four-byte slots | Deleted | The server's block building (MIDI-13, MIDI-17, SRV-8) |
| `synth-fields.ts` (105) | Writes the slot synthesizers' members as fields | Deleted | Generated member types |
| `synth-live.ts` (16) | The analogue synthesizers' program repeater | Deleted | The server's restatement |
| `synth-patch-rules.ts` (86) | A port of the server's `patch.rs` patch checks | Deleted | The server's checks, with the receiver's own code (MIDI-21) |
| `synth-patch-tables.ts` (288) | The analogue synthesizers' patch field tables | Deleted | The server's parameter tables (the family documents) |
| `synth-score.ts` (47) | The analogue synthesizers' score of slots | Deleted | The server's block building |
| `synth106-patch.ts` (139) | Packs a synth106 or synth60 patch from its panel; `synth106InitPatch`, `synth60InitPatch` | Deleted | The server's encoding (`synth106-synth60.md`, S106-36, S106-37) |
| `synth53-patch.ts` (178) | Packs a synth53, synth52 or synth51 program; `synth53Dial` and the init patches | Deleted | The server's encoding (`synth53-synth52-synth51.md`, S53-47) |
| `synth6581-clock.ts` (33) | The chip's clocks and a frequency register's value for a pitch | Deleted | Nothing in the protocol, the server or the kits: a program computes its registers (S6581-52; DEC-6465 answer 8); the audio demo keeps its own (TS-39) |
| `synth6581-image.ts` (239) | Builds a 25-register image by name | Deleted | The generated `register_update` event's `registers` (SRV-12) |
| `synth6581-note.ts` (67) | The hard-restart note helpers | Deleted | Nothing in the kit (S6581-52); the audio demo keeps its own (TS-39) |
| `synth6581-track.ts` (93) | Gathers images step by step into a sound's bytes | Deleted | The program's list of timed register updates; the server builds the blocks (S6581-53 item 4) |
| `synth7-live.ts` (13) | synth7's program repeater | Deleted | The server's restatement |
| `synth7-patch.ts` (241) | Packs a synth7 voice into 128 bytes; `synth7InitVoice` | Deleted | The server's encoding (`synth7.md`) |
| `synth7-score.ts` (14) | synth7's score of slots | Deleted | The server's block building |
| `synth7-slot.ts` (212) | The slot format, its MIDI messages and the server's `slot_fault` rule | Deleted | The architecture's event list, written by the server (MIDI-23) |
| `synth7-sysex.ts` (86) | Reads a 32-voice dump into a bank | Deleted | The program sends the dump's bytes as a bank in the `bytes` form (SRV-20); the server reads it (`synth7.md`) |
| `synth8-patch.ts` (198) | Packs a synth8 patch | Deleted | The server's encoding (`synth8.md`) |
| `synth80-patch.ts` (211) | Packs a synth80 patch | Deleted | The server's encoding (`synth80.md`, S80-41, S80-42) |
| `synthd-patch.ts` (213) | Packs a synthD patch | Deleted | The server's encoding (`synthd.md`) |

*`src/sound/`, the sampled sounds and the profile:*

| File (lines) | What it does today | Fate |
|---|---|---|
| `members.ts` (100) | `Audience`, the sampled sounds' and commands' hand-written member types, `SoundMember` | `Audience` stays, as TS-20 reshapes it; every member type goes, replaced by the generated member types (TS-11, TS-15) |
| `sound-fields.ts` (126) | Writes a member as its fields, translating names and dispatching instruments to `instrument-fields.ts` | Deleted: a member is written as given (TS-19) |
| `profile.ts` (64) | The audio profile's rates, channels and bounds | Keeps only what the Opus encoder uses; the rest goes, as Knip will find |
| `ffmpeg-opus.ts` (172), `ogg-opus.ts` (201), `opus-encoder.ts` (37), `pcm.ts` (13) | Encode samples as Opus or PCM bytes | Stay: encoding a program's samples is the program's side (the server's decision 21) |
| `opus-fields.ts` (56), `opus-packet.ts` (97) | Write and check Opus members, porting the engine's packet check | Deleted: members are written as given (TS-19) and the server checks the packets (TS-17; DEC-6477 typescript answer 5) |

*`src/wire/`, `src/channel/`, `src/testing/`, `scripts/` and the entry point:*

| File | Fate |
|---|---|
| `src/wire/instrument-wire.ts` (73) | Deleted (TS-15) |
| `src/wire/instrument-rules.ts` (96) | Deleted (TS-17) |
| `src/wire/sound-rules.ts` (42) | Deleted: its instrument branch (`isInstrumentKind`, `instrumentFault`) and its Opus and sample checks are the server's (TS-17; DEC-6477 typescript answer 5) |
| `src/wire/server-rules.ts` | Calls `soundFault` for no synthesizer kind (TS-17) |
| `src/wire/protocol.ts`, `server-wire.ts`, `server-message.ts` | Their hand-written types go (TS-15); what is left is the kit's own plumbing |
| `src/wire/validate.ts` | Stays; validates after bytes are encoded (TS-16) |
| `src/wire/limits.ts` | `PROTOCOL` becomes 13 (TS-3) |
| `src/wire/server-events.ts` | Routes `refused` and the reports of sounds to the handlers (TS-22, TS-23) |
| `src/channel/context.ts` | `sound` takes `SoundMember` (TS-19) |
| `src/channel/application.ts` | Gains `refused` and the report handlers (TS-22, TS-23) |
| (new) `src/channel/handlers.ts` | The list of `Application`'s optional handlers (TS-2) |
| `src/channel/channel.ts`, `run-channel.ts` | Call the handlers; report an unhandled refusal as today |
| `src/channel/sender.ts`, `connections.ts` | Encode bytes before validation (TS-21); `{ connection }` in place of `{ session }` (TS-20) |
| `src/testing/harness.ts` | Gains `sounds`, `soundsOfKind`, `soundsToEveryone`, `refuse`, `report`, `restart` (TS-29 to TS-31) |
| `src/testing/sent.ts` | `soundBytes` and `BYTE_FIELDS` deleted (TS-29) |
| `src/testing/index.ts`, `src/index.ts` | Export exactly what TS-27 and section 3.6 list |
| `scripts/validators.ts` | Reads `schema/protocol-13.json` |
| (new) `scripts/types.ts` | The generator (TS-9) |
| `scripts/check.sh` | The `schema` step's names and the step of TS-2's copies (TS-6); `COMMON_FROM`; the types step (TS-12); the build copies `protocol.d.ts` |
| `knip.jsonc`, `.prettierignore`, `.oxlintrc.json` | As TS-12 says |
| `schema/protocol-12.json` | Deleted; `schema/protocol-13.json` added (TS-5) |
| (new) `kit-calls.tsv`, `test/fixtures/examples.jsonl` | The copies of TS-2 |

*The tests:*

| Test file | Fate |
|---|---|
| `test/instrument-sounds.test.ts`, `test/synth-sounds.test.ts`, `test/synth-patch.test.ts`, `test/synth-score.test.ts`, `test/synth6581.test.ts`, `test/synth7-bank.test.ts`, `test/synth7-score.test.ts`, `test/midi-file.test.ts` | Deleted with the code they test; what they checked is the server's to test (each family document's verifications) |
| `test/no-limits.test.ts` | Loses its instrument cases |
| `test/server-rules.test.ts` | Loses every synthesizer case (TS-17) |
| `test/protocol.test.ts` | Its samples of hand-written types go (TS-15) |
| `test/sound.test.ts`, `test/opus.test.ts`, `test/opus-profile.test.ts` | Use generated member types; their cases of the kit's Opus and sample rules are deleted with the rules (TS-17), the encoder's cases kept |
| `test/fixtures/hello.jsonl`, `hello.ts` | Gain one line of each synthesizer kind, as the server document's fixture has it (DEC-6462 item 2) |
| (new) `test/thin.test.ts`, `test/kit-calls.test.ts`, `test/types-generator.test.ts`, `test/types/members.test-d.ts`, `test/schema-facts.test.ts`, `test/sound-validation.test.ts`, `test/sound-calls.test.ts`, `test/harness-sounds.test.ts`, `test/exports.test.ts`, `test/server-oracle.test.ts`, `test/examples/*.test.ts` | The verifications of this document |

- Reason: DEC-6462 item 3 and the brief's request that every module be listed with its fate. The 28 synthesizer modules of `src/sound/` are 3,413 lines and the wire's two instrument modules 169 (DEC-6462 counts "about 4,300" lines of sound code, which includes the shared sound modules and the tests).
- Source: The kit at `6d54c3d`; DEC-6462; the family documents' differences sections.
- Verification: `test/thin.test.ts` (TS-1); `test/exports.test.ts` (TS-27); Knip.

**TS-37. The kit's guide.** The kit's guide (its `README.md` and the protocol's documentation item for the kit, DOC-1974) MUST describe the synthesizers only by: the one call and the audiences (TS-19, TS-20), with the rule of TS-19 that a page's play is sent once to a connection on the page (`integration.md` INT-28); bytes (TS-21); the handlers (TS-22, TS-23); the harness (section 3.6); and the worked examples (section 4), with every message, field and rule cited to the server document and its documentation items, not restated.
- Reason: Each fact has one home (DEVELOPMENT.md section 1 item 6); the guide teaches and points.
- Source: DEVELOPMENT.md sections 1 and 3.7; DEC-6462 item 4.
- Verification: A review of the guide.

### 3.9 The audio demo channel

The audio demo (`neoteletext-server-channel-audiodemo`, at `3dc1d68`, kit 14.0.0) plays every family. Its pages and their behaviour do not change; what it sends does. These requirements are the audio demo's.

**TS-38. The audio demo takes kit 15.0.0 and keeps its pages.** The audio demo MUST move to kit 15.0.0 in one change, keeping its nineteen pages, their numbers, their words (except where a figure quoted from the sounds changes, `src/text/`), their keys and the sounds each plays, by the same handles (`src/handles.ts`) and gains (until TS-41 measures them again). Each of its sound messages MUST be a generated member sent with `context.sound`. Its application MUST have a `refused` handler that logs the server's path, rule and detail, and a page whose sound is refused MUST go on showing its text.
- Reason: The demo is the test channel of the instrument sounds; its behaviour is the check that the new interface plays what the old one did.
- Source: The demo's README and `src/audio-demo.ts`; TS-22, TS-25.
- Verification: The demo's tests (TS-42) and a listening check in the browser on the deployed demo, recorded with its date (DEVELOPMENT.md section 8, platform behaviour).

**TS-39. What each sound file becomes.** Each file of the audio demo that makes or sends sound MUST change as this table says:

| File | What it does with kit 14.0.0 | What it becomes |
|---|---|---|
| `src/handles.ts` | The one table of handles, generations, audio channels and gains | Unchanged but for the gains (TS-41); `BANK` and `FIRST_SYNTH_BANK` are the handles of `<name>_bank` members |
| `src/library.ts` | Builds every stored sound once; checks the duet's halves are of equal blocks by dividing bytes by `SYNTH6581_IMAGE_BYTES` and `SLOT_BYTES` | Builds the same sounds as generated members; the duet's check compares the two halves' `length_us` (equal, so their loops stay together), not bytes |
| `src/openings.ts`, `src/audio-demo.ts` | Sends a page's sounds, a bank before any sound naming it, then the play commands, to `{ session }` | The same order, to `{ connection }` (TS-20); each play a `SoundPlayMember` with every field the schema requires, sent once to a connection on the page (`integration.md` INT-28) |
| `src/live-page.ts` | Announces `synth6581Live` to each viewer; every 200 ms sends `synth6581Blocks` of 25-register images, numbering blocks itself (`first`) | Announces a `synth6581_live` member (handle `LIVE_SYNTH6581`, `clock: "pal"`) to each connection that opens the page, which for a live sound already playing sends that connection its OBJECT only (SRV-73; DEC-6477 typescript answer 6), and every 200 ms sends a `synth6581_events` member to the page's connections with the register updates of the batch, each at its time in microseconds from the run's start, and `until_us` the run's time plus one batch, in microseconds, which the server sends at most 25 blocks ahead of their time (SRV-77); no block numbers. The first update of the run is a full register update (S6581-46) |
| `src/keyboard-page.ts` | Sends a player's eight notes as stored synth7 sounds of slots, a new generation when they choose another patch | The same eight stored sounds and generations, each a `synth7` member whose `music` is `events` (a `program_change`, a `note_on`, a `note_off`) and whose `length` is `{ "tail_us": … }`, naming the bank; the player's patch keyed on the connection (TS-28) |
| `src/synth6581/player.ts`, `song.ts`, `tune.ts`, `duet.ts`, `effects.ts`, `instruments.ts`, `live.ts` | Build `Synth6581Image`s with the kit's `Synth6581Track`, `synth6581Frequency`, `synth6581Note`, `synth6581Gate`, `synth6581HardRestart` | Compute their own registers and send `register_update` events (SRV-12): a full register update at time 0 (S6581-45), then, at each 20 ms step, the registers that step changes; the frequency formula and the hard restart move into a new `src/synth6581/registers.ts` of the demo's own, citing the datasheet as the kit's modules did, since note help belongs in an example program (DEC-6465 answer 8); a step's time is the step's number times 20,000 microseconds |
| `src/synth7/patches.ts`, `operators.ts` | Write six voices with `synth7InitVoice` and the kit's `Synth7Patch` | Write six voices as generated synth7 patches in the `fields` form, from a starting voice of the demo's own written from the DX7's initial voice as `synth7.md` states it |
| `src/synth7/bank.ts` | Packs the six voices with `packSynth7Patch` into 128-byte patches back to back | A `synth7_bank` member whose `bank` is `{ "form": "patches", … }` of the six voices (what a bank of fewer than 32 voices means is `synth7.md`'s, its open question 18 as answered by DEC-6465) |
| `src/synth7/tune.ts`, `duet.ts`, `phrase.ts`, `keyboard-notes.ts`, `parts.ts` | Add timed notes to `Synth7Score` in milliseconds, and build blocks of slots | Build lists of generated events (SRV-10): each `time_us` the row's start in microseconds (the row's milliseconds times 1,000), each event typed (`note_on`, `note_off`, `program_change`, `pitch_bend`, `control_change`); the sound's `length` is its bars' length as `length_us` |
| `src/synth/synth106.ts`, `synthd.ts`, `synth53.ts`, `synth8.ts`, `synth80.ts` | Pack two patches each with the kit's `pack…Patch` and `…InitPatch` | Write two patches each in the `fields` form of that synthesizer's generated patch type, in the units the family document gives; their starting points are the demo's own (TS-40) |
| `src/synth/voice.ts` | Maps a synthesizer name to the kit's member (`{ synth106: … }`), and a synth8's keyboard | Maps a synthesizer name to its `<name>` and `<name>_bank` kinds (SRV-3); a synth8's `key_mode` and `split_key` (SRV-16) |
| `src/synth/sounds.ts`, `piece.ts`, `library.ts`, `rows.ts`, `pieces.ts` | Build each synthesizer's bank, phrases and tune with `SynthScore` | Build them as generated members: a bank of the two patches, phrases and tunes as `events` music naming the bank |
| `src/tools/sizes.ts` | Prints each stored sound's bytes for the README | Prints each sound's events and length; the bytes on the wire are the server's to measure (MIDI-49), so the README's size table is replaced by the server's figures or removed |
| `src/text/*-pages.ts` | Quote figures computed from the sounds' bytes | Quote figures computed from the sounds' events and lengths |

- Reason: The brief asks what each sound file becomes. The changes are mechanical except where the kit's instrument logic leaves: the synth6581 register helpers become the demo's own, where DEC-6465 answer 8 places them.
- Source: The audio demo at `3dc1d68`; `synth6581-synth8580.md` section 9.2 item 15; DEC-6465 answer 8; TS-1; SRV-3, SRV-9, SRV-10, SRV-12, SRV-14, SRV-16, SRV-17, SRV-18, SRV-20, SRV-21.
- Verification: TS-42's tests.

**TS-40. The demo's patches are written in the adopted interfaces' terms.** Every patch the demo writes MUST be written in the `fields` form of the server document's patch type for its synthesizer, in the units the family document gives each field, and MUST NOT be computed from the kit 14.0.0 patch bytes the demo used before; where a family's fields differ from the panel the demo's patch was designed on (synthD's 60 values against the old 36 bytes; synth8's 42 against 43; synth53's program against the old 24 bytes), the patch MUST be written again from the family document's table, and listened to.
- Reason: The old byte layouts are NeoTeletext's own inventions that the family documents replace with each interface's form (`midi-architecture.md` section 21 item 6); a translation of old bytes would carry the old layout's meaning into the new fields.
- Source: `midi-architecture.md`, MIDI-54 and section 21 item 6; the family documents' differences sections.
- Verification: A review of each patch against its family document's table; the listening check of TS-38.

**TS-41. The demo's gains are measured again.** The demo's gains (`src/handles.ts`, measured in the browser on 18 November 2026 as EBU R128 integrated loudness of 30 seconds of each tune) MUST be measured again after the move, by the same method, and set so that each tune is at −25 LUFS as today, the measurements written into the file's comment with their date.
- Reason: The patches are written again (TS-40) and the families' volume law is now one (MIDI-82, MIDI-92); the levels will move. Measure, don't reason (DEVELOPMENT.md section 2.1).
- Source: `src/handles.ts`; DEVELOPMENT.md section 2.1.
- Verification: The figures in the commit.

**TS-42. The demo's tests.** The demo's tests MUST check, with the harness of section 3.6: on opening each page, exactly the sound members the page needs, in order, banks first (`test/opening.test.ts`, `test/synth-pages.test.ts`); the keyboard's eight notes and their regeneration on a change of patch (`test/keys.test.ts`); the live page's announcement to each connection that opens it, an events member every 200 ms of the harness's clock while anyone is on the page, each `until_us` 200,000 microseconds after the last and later than every event it carries, and nothing once the page is empty (`test/live.test.ts`); the tracker's register updates for known rows, including the hard restart's two steps before a note (`test/tracker.test.ts`, now testing the demo's own `registers.ts`); and that a refusal the harness gives a page's sound is logged and leaves the page's text shown. `test/synth7-messages.ts`, `test/synth7-parts.test.ts`, `test/synth7.test.ts` and `test/synth-sounds.test.ts` MUST read events and patches as generated members instead of slots and packed bytes. `test/helpers.ts` MUST use `harness.sounds` in place of `soundBytes`.
- Reason: The demo's tests today read bytes the kit built; they must read the members the demo now sends.
- Source: The demo's tests at `3dc1d68`; TS-29 to TS-31.
- Verification: The demo's push gate.

### 3.10 Protocol 14: the page rule table and animation

Program protocol 14 (`../page-rules.md` RULE-34, `../animation.md` ANIM-21; DEC-6522, DEC-6524) adds the page rule table and the animation messages. The TypeScript kit takes it as it took protocol 13, and the requirements above hold for it with 14 read for 13: the schema's copy is `schema/protocol-14.json`, the server's `protocol/schema-14.json` at the commit `SCHEMA_FROM` names (TS-5 to TS-7), `PROTOCOL` is 14, and a `start` of any other version stops the program (TS-3). The requirements below say what protocol 14 adds to this document; rdm requirement REQ-6537 carries them. They are `python.md`'s PY-74 to PY-82 for this kit, requirement for requirement, so that the kits stay equal (TS-2).

**TS-44. The constructs protocol 14 adds to the generator.** Beside TS-9's table, the generator MUST map `patternProperties` of exactly one pattern, in an object with `"additionalProperties": false` and no `properties` (the `variables` and `timers` of `page_state`, keyed by name), as `Readonly<Record<string, T>>`, the pattern held by the validators; any other use of `patternProperties` MUST fail generation, naming its path. The validators (`scripts/validators.ts`) MUST know the integer format `int8`, which checks nothing beyond the `minimum` and `maximum` beside it.
- Reason: These are what `schemars` emits for the rule table's types; TS-9's rule stands that the generator knows exactly what the schema holds and fails on anything else.
- Source: `schema-14.json`; page-rules.md RULE-35, RULE-38; `python.md` PY-74.
- Verification: `test/types-generator.test.ts`: the record written for one pattern; `patternProperties` beside `properties`, with `additionalProperties` not false, and of two patterns each failing.

**TS-45. The names protocol 14 adds.** TS-10 rule 2's tag properties are `type`, `kind`, `event`, `form`, `packet`, `action` and `of`: `action` tags `RuleAction` and `AnimationOp` (`RuleActionMidi`, `AnimationOpReset`) and `of` tags `RuleValue` (`RuleValueSynth`). A branch of an untagged union that is an object MUST be named the union's name followed, in upper camel case, by the first property it requires, in the schema's order, that no other object branch of the union has (`RuleCondition`'s branches of `read`, `op` and `value`, of `read` and `in_range`, and of `read` and `in_set` are `RuleConditionOp`, `RuleConditionInRange` and `RuleConditionInSet`; a branch of one property is named by it, as before); a branch with no such property MUST fail generation. The types RULE-55 and ANIM-19 name (`RuleTable`, `PageRule`, `RuleTrigger`, `RuleCondition`, `RuleValue`, `RuleAction`, `RuleTarget`, `AnimationOp`, `Sprite`, `NaplpsObject`) are the schema's definitions under their own names (TS-10 rule 1). `PageState` is the kit's name for the answer to a state query, an alias of the generated `ServerMessagePageState` and never a restatement of it (TS-14), exported from the kit's main entry.
- Reason: One rule gives each type its one name in both kits (TS-10; `python.md` PY-75).
- Source: page-rules.md RULE-35, RULE-55; `schema-14.json`.
- Verification: `test/types-generator.test.ts`: the two tags, the untagged branch's name, and two branches of the same properties failing.

**TS-46. The rule table's calls.** `Context` MUST offer `rules(to: Audience, page: number, table: RuleTable | null): void`, which writes one `rules` message for each chunk of the audience's connections, the table exactly as built (no default filled in, no name checked), `null` written as `null`; and `queryState(connection: number, page: number): Promise<PageState>`, which writes `query_state` with a request number of the kit's own count (1 to 4,294,967,295, then 1 again) and resolves with the server's `page_state` of that number, or rejects with a `QueryRefusedError` carrying the server's `refused` of that number (`too_frequent`, `wrong_page`, `not_answered` and the others of RULE-39). A `refused` that answers a state query reaches no `refused` handler, as one that answers a measure reaches none (TS-22). A `start` rejects every query not yet answered. The kit MUST hold `rules` and `query_state` to the schema and to nothing else (TS-17 extended): every fault the schema cannot state is the server's to refuse.
- Reason: RULE-55; DEC-6462: the kit builds and sends, and the server checks.
- Source: page-rules.md RULE-35, RULE-38, RULE-39, RULE-55.
- Verification: `test/rules/examples.test.ts`: the six examples of page-rules.md section 7.5 and the music player's table of RULE-93, written as typed tables, are written as exactly the documents' JSON text (TS-50). `test/rules/calls.test.ts`: chunking, `null`, a query answered, refused and ended by a restart. `test/rules/server-rules.test.ts`: what the schema states of a table refused at the server's path and rule, and what it cannot state sent.

**TS-47. What a rule's firing gives a program.** The kit's `Input` MUST gain three optional fields, `rule` (the name of the rule that sent it), `tick` (the page tick it fired at) and `target` (the target the pointer was inside, or `null`), as RULE-37 defines them, set on every input read from the server; they are optional in the type only so that a program's test may write an input without them. `readInput` takes them as its third argument. `Application` MUST gain the optional handlers `ruleEvent?(event: ServerMessageRuleEvent, context: Context): void` and `rulesFault?(fault: ServerMessageRulesFault, context: Context): void`, each given the validated message whole, called on the application that serves the message's page, with `context.connection()` answering the message's connection. `ServerEvents` MUST gain `ruleEvent`, `pageState` and `rulesFault`.
- Reason: RULE-55; TS-14 and TS-18 (handlers receive the generated wire types). Optional fields keep every `Input` a program's tests already write compiling.
- Source: page-rules.md RULE-37, RULE-48, RULE-55.
- Verification: `test/events.test.ts` and `test/rules/calls.test.ts`.

**TS-48. The animation calls.** `Context` MUST offer, with ANIM-19's signatures, each writing one message of ANIM-21 for each chunk of the audience's connections and checking nothing beyond the schema: `frame(to, page, sub, body)`, which writes `frame` with `"mark": "begin"`, runs `body`, and writes `frame` with `"mark": "end"`, also when `body` throws, whose error is then the caller's; `animate`; `sprites`; `naplpsObjects`; `spriteSheet(to, page, kind, data, restart?)`, text written a byte a character as `regis` writes it, and all bytes as base64 (TS-21); `playTimeline(to, page, sub, timeline, id?)`, which writes `timeline` with the timeline's `steps` and `loop_ticks` (`null` when it has none) and returns the identifier, the kit's own count (1 to 65,535, then 1 again) when none is given, an identifier given not being counted; and `stopTimeline(to, page, id)`. The local sound kinds of RULE-61 (`synth7_local` to `synth80_local`) are members of `SoundMember` and are sent with `sound` (TS-19).
- Reason: ANIM-19; DEC-6462: the server plays a timeline, so the kit holds no scheduler and keeps no list of the timelines playing.
- Source: animation.md ANIM-19, ANIM-21; page-rules.md RULE-61.
- Verification: `test/animation/calls.test.ts`: each call writes ANIM-21's example, text for text; a frame is ended when its body throws; the identifiers counted. `test/sound-calls.test.ts`: RULE-61's example.

**TS-49. The timeline builder.** The kit's main entry MUST export the class `Timeline` and the interface `TimelineStep` with ANIM-19's signatures, and `TICKS_PER_SECOND` (60). `new Timeline({ loopTicks })`; `at(tick)` answers a new step at that tick; `then(ticks)` a new step that many ticks after the step made last (after tick 0 when none was made); each of a step's methods (`move`, `show`, `hide`, `look`, `order`, `frame`, `cycle`, `stopCycle`, `reset`) adds one operation on `{ object: n }` and answers the step, writing `relative` and `once` always (`false` when not given) and `layer` as given (`null` to keep it). `steps` is the `timeline` message's `steps`: in ascending tick, the steps of one tick joined in the order they were made, and a step given no operation left out, though `then` still counts from it. `loopTicks` is the message's `loop_ticks`, or `null`. The builder checks nothing and holds no clock. Because `then` is also the name by which JavaScript takes an object for a promise, a `then` called with anything but a number (as `await` and an async function's return call it) MUST throw a `TypeError` saying a timeline is no promise, so that the mistake rejects where it is made and is never an await that does not settle.
- Reason: ANIM-19 ("`Timeline` only gathers steps ... sorts them by tick, joins steps of one tick, and holds no clock").
- Source: animation.md ANIM-19; ECMA-262, "Promise Resolve Functions" (a resolution value with a callable `then` is called as a thenable).
- Verification: `test/animation/timeline.test.ts`: the shared fixture of TS-50; a timeline awaited rejects.

**TS-50. The fixtures of protocol 14.** The kit MUST keep byte-for-byte copies of neoteletext-common's `docs/rules-examples.jsonl` and `docs/timelines.jsonl` as `test/fixtures/rules-examples.jsonl` and `test/fixtures/timelines.jsonl`, pinned by `COMMON_FROM` and checked by the commit gate's `shared` step as `kit-calls.tsv` is (TS-6); `python.md` PY-80 defines both files. The kit's tests MUST build every example's table and every timeline in TypeScript, typed by the generated types, and write exactly the fixture's message: the same JSON text, every field in the document's order.
- Reason: ANIM-19's verification; the rule examples are held the same way so that the documents' JSON is what both kits send.
- Source: animation.md ANIM-19; page-rules.md section 7.5 and RULE-93; `python.md` PY-80.
- Verification: `test/rules/examples.test.ts`, `test/animation/timeline.test.ts`; `scripts/check.sh shared`.

**TS-51. The harness for rules and animation.** Under protocol 14 every `input` names the rule that sent it, so the harness's `send`, and every input call made of it, MUST give an input that names no rule the rule of the server's default table (RULE-53) that sends that event (`keys`, `keys_up`, `text`, `press`, `release`, `move`, `hover_in`, `hover_out`, `drawing_in`, `drawing_out`, `focus`, `blur`, `wheel`), with the harness's clock in ticks as its tick and no target, and MUST keep the `rule`, `tick` and `target` of an input that carries them. The harness MUST also offer: `fire(connection, rule, event?, tick?, target?)`, which gives the channel what that rule's firing sends (with no event a `rule_event` of kind `fired`; with a `rule_event`'s body that `rule_event`; with an input event as the server writes one, the `input` naming the rule and target), held to the schema first; `answerState(query, state?)`, which answers a `query_state` the channel wrote with a `page_state` of its request, the fields `state` gives over those of a page with no table; and `timelineSends(connection)`, the `animate` messages the server would send the connection as it plays each timeline written, once through, each with its timeline's identifier and its step's tick. The harness does not stop, replace or loop a timeline and does not evaluate a table: those are the server's and the receiver's.
- Reason: RULE-55 ("each kit's test harness gains `press`, `fire` and `answerState`"; `press` is the harness's existing call, whose input now names a rule); ANIM-19 ("each kit's test harness records the messages a timeline would send").
- Source: page-rules.md RULE-53, RULE-55; animation.md ANIM-19; `python.md` PY-81.
- Verification: `test/rules/harness.test.ts`, `test/rules/calls.test.ts`, `test/animation/calls.test.ts`; the call list (TS-2).

**TS-52. Release 16.0.0.** The change MUST be released as kit version 16.0.0, a major release, made as TS-34 says from a commit whose gates pass. Every channel and library that depends on the kit moves to it together with the server and the browser, because a program of protocol 13 cannot run under a server of 14 and the push protocol changes with it (page-rules.md RULE-49); a channel that changes nothing but the kit's version keeps hearing its input where the server's configuration gives it `default_rules: send_all` (RULE-53).
- Reason: A change to what `exports` names, and to the protocol spoken, is a major version.
- Source: TS-34, TS-35; page-rules.md RULE-34, RULE-49, RULE-53.
- Verification: The release's tarball and its SHA-256, vendored by each consumer.

---

## 4. Worked examples

**TS-43. The examples are tests.** Each example of this section MUST be a test of the kit, `test/examples/<name>.test.ts`, compiled by the commit gate's type check against the generated types, run with the harness on the inputs and scenario of section 4.0, and checked line for line against `test/fixtures/examples.jsonl` (TS-2); and MUST be replayed against the server by TS-33. Every kind, field and value an example spells MUST be the server document's as `schema-13.json` publishes it; an example the schema's copy does not validate MUST fail its test, and the examples MUST be corrected to the schema before release 15.0.0.
- Reason: An example in a document that is not compiled drifts from the interface; compiled against the generated types it fails the gate the day a field changes; checked against the shared fixture, it is the evidence that the two kits send the same lines. It is `python.md`'s PY-48 and PY-73.
- Source: TS-2, TS-4, TS-8; `python.md`, PY-48, PY-73.
- Verification: The examples' tests.

**About the spellings.** The examples are the seven scenarios of `python.md` section 5, with the same pages, handles and values, so that both kits' versions write the same lines, which `docs/audio/examples.jsonl` holds. Every kind, field, event shape and patch field is the server document's (SRV-3 to SRV-48), as DEC-6477 settles for every document of this set: kinds `<name>`, `<name>_live`, `<name>_events`, `<name>_bank`; `time_us`; events tagged by `event`; `length` as `{ "tail_us": … }` or `{ "length_us": … }`; `music` tagged by `form`; `until_us`, always later than every event's `time_us` (SRV-74); `banks` as a list of bank handles, naming at least one bank in every sound of a family with banks (MIDI-57; SRV-16, SRV-17); `lift_banks`; banks and patches tagged by `form`, a patch's fields beside its `form`; a parameter event's `set` as `{ name: value }`; a bank select as a program change's `bank_msb` or `bank_lsb`; synth6581's `register_update` with the register fields of SRV-12; synth106's panel fields of SRV-30; synth8's panel fields of SRV-40. The members of `play` and `stop` carry every field the schema requires of them (`gain`, `fade_ms`, `loop`, `after` and `duck` for `play`; `fade_ms` for `stop`), which SRV-46 keeps unchanged. The generated type names follow TS-10 (a sound kind's member type is `Sound` followed by the kind in upper camel case and `Member`).

In every example the application is an `Application` of the kit; `opened`, `input`, `leftPage` and `wake` take a connection where protocol 12 took a session (VS-403); `context.now()` is milliseconds since the program started on the kit's clock, which the harness owns in a test, and `context.wakeIn(ms)` asks for one call of `wake` that long after.

### 4.0 The examples' inputs and scenarios

Both kits' tests run each example on these inputs and in these scenarios, on the harness, with one connection, number 1, and the clock starting at 0 milliseconds; the lines the program writes are, in order, the lines of `docs/audio/examples.jsonl` whose `example` is the example's name. Each line of that file is one JSON object of exactly two fields: `example`, the name below, and `message`, the message exactly as the program writes it, with its `type` and `connections`. Only `sound` messages are in the file; a `log` line an example writes is not.

| Example | Name in the file | Inputs | Scenario |
|---|---|---|---|
| 4.1 A stored tune (synth6581) | `stored-tune` | None | Connection 1 opens page 0x300. |
| 4.2 A live keyboard (synth106) | `live-keyboard` | None | Connection 1 opens page 0x310 at 0 ms; the key `a` is pressed at 30 ms and released at 250 ms; the connection leaves the page at 350 ms; the clock is run to 500 ms. The wakes at 100, 200 and 300 ms write the three events messages; the wake at 400 ms finds no player and writes nothing. |
| 4.3 A patch by fields (synth106) | `patch-by-fields` | None | The test sends `brassBank()` and then `brassPhrase()` to connection 1. |
| 4.4 A patch by system exclusive (synth7) | `patch-by-system-exclusive` | The voice file: the 163-byte single-voice dump of synth7's default voice (`synth7.md` S7-51) on channel 1 (sub-status byte `0x00`), its checksum by S7-39 | The test sends `voiceBank(file)` and then `electricPiano(file)` to connection 1. |
| 4.5 A bank (synth53) | `bank-synth53` | The dumps file: two program dumps (`synth53-synth52-synth51.md` S53-28) of group 0, programs 0 and 1, each the default program of S53-30 for synth53 (parameter 20 at 1), packed by S53-32: 318 bytes | Connection 1 opens page 0x320. |
| 4.5 A bank (synth80) | `bank-synth80` | One patch: synth80's default patch, the 85 values of the last column of `synth80.md` S80-33 (S80-45) | The test sends `stringsBank([patch])` to connection 1. |
| 4.6 A Standard MIDI File (synth7) | `midi-file` | `tune.mid`: a Standard MIDI File of format 0, one track, a division of 480 ticks a quarter note and no tempo event (so 500,000 microseconds a quarter note), whose track holds, at delta time 0, a 32-voice dump (`synth7.md` S7-41) of 32 copies of the default voice, written as an `F0` event; program change 0 on channels 1 and 2; note ons of keys 60, 64 and 67 at velocity 100 on channels 1, 2 and 3; at delta time 480 the three note offs at velocity 64; then end of track: 4,164 bytes | Connection 1 opens page 0x330. The note on and off of channel 3, which the channel map drops, are counted in `sound_built`'s `dropped.unmapped_channel` (SRV-47). |
| 4.7 A named parameter (synth8) | `named-parameter` | None | The live sound's start is set to 0 ms (its announcement is left out of the example); the wheel turns with `dy` −10 on connection 1 at 500 ms. |
| 4.7 A patch of control values (synthD) | `patch-of-control-values` | The 60 values: synthD's default patch, the last column of `synthd.md` SD-22 (SD-21) | The test sends `bassBank(values)` and then `bass(values)` to connection 1. |

neoteletext-common builds the fixture's bytes from the family documents' tables with one script that is not kept; a change to any input is a change to this table and to the fixture in one commit.

### 4.1 A stored tune (synth6581)

A short tune for synth6581, sent once to each connection that opens page 300 and played on audio channel 0. Every event is a register update by named fields (SRV-12); the first is a full register update at time 0, as S6581-54 item 8 requires (the server checks that, not the kit). The frequencies are the chip's 16-bit register values on a PAL clock, worked out once by the author from the chip's formula (S6581-35): C, E, G, C, 4,291, 5,407, 6,430 and 8,583, written as their low and high bytes.

```ts
import type { Application, Context } from "neoteletext-server-ts-protocol";
import type { SoundPlayMember, SoundSynth6581Member, Synth6581Event } from "neoteletext-server-ts-protocol/protocol";

const TUNE_PAGE = 0x300;
const TUNE_HANDLE = 4;
/** One frame of a 50 Hz tune, in microseconds (MIDI-17's unit). */
const FRAME_US = 20_000;
/** C, E, G, C as frequency register values, low byte and high byte (4,291; 5,407; 6,430; 8,583). */
const NOTES = [[0xc3, 0x10], [0x1f, 0x15], [0x1e, 0x19], [0x87, 0x21]] as const;
/** Voice 1's control register: pulse waveform (bit 6), gate (bit 0) open or closed. */
const PULSE_GATE_ON = 0x41;
const PULSE_GATE_OFF = 0x40;

function tune(): SoundSynth6581Member {
  const events: Synth6581Event[] = [
    {
      event: "register_update",
      time_us: 0,
      registers: {
        voice1_frequency_low: NOTES[0][0], voice1_frequency_high: NOTES[0][1],
        voice1_pulse_width_low: 0x00, voice1_pulse_width_high: 0x08,
        voice1_attack_decay: 0x09, voice1_sustain_release: 0xa0,
        voice2_frequency_low: 0, voice2_frequency_high: 0, voice2_pulse_width_low: 0, voice2_pulse_width_high: 0,
        voice2_attack_decay: 0, voice2_sustain_release: 0,
        voice3_frequency_low: 0, voice3_frequency_high: 0, voice3_pulse_width_low: 0, voice3_pulse_width_high: 0,
        voice3_attack_decay: 0, voice3_sustain_release: 0,
        filter_cutoff_low: 0x00, filter_cutoff_high: 0x80, filter_resonance_routing: 0x01, filter_mode_volume: 0x1f,
        voice1_control: PULSE_GATE_OFF, voice2_control: 0, voice3_control: 0,
      },
    },
  ];
  NOTES.forEach(([low, high], index) => {
    const start = index * 12 * FRAME_US;
    events.push({ event: "register_update", time_us: start, registers: { voice1_frequency_low: low, voice1_frequency_high: high, voice1_control: PULSE_GATE_ON } });
    events.push({ event: "register_update", time_us: start + 9 * FRAME_US, registers: { voice1_control: PULSE_GATE_OFF } });
  });
  return { kind: "synth6581", handle: TUNE_HANDLE, generation: 0, clock: "pal", length: { tail_us: 500_000 }, music: { form: "events", events } };
}

export const tunePage: Application = {
  pages: () => [/* the channel's page entries, page 300 among them */],
  start: () => {},
  opened(connection: number, page: number, context: Context): void {
    if (page !== TUNE_PAGE) {
      return;
    }
    const play: SoundPlayMember = { kind: "play", channel: 0, handle: TUNE_HANDLE, generation: 0, gain: 80, fade_ms: 0, loop: false, after: false, duck: 0, page: "300" };
    context.sound({ connection }, tune());
    context.sound({ connection }, play);
  },
};
```

What happens: the kit validates each member and writes two `sound` lines. The server places each update at the tick `floor((time_us + 50) ÷ 100)` (SRV-8), builds the blocks and records, and plays the sound on the `play`. Had the first update not been a full register update, the server would have refused the stored sound and the application's `refused` handler would have heard it, the refusal's `sound` naming kind `synth6581`, handle 4 and generation 0 (TS-22, SRV-48); the kit would not have. The two updates at one time keep their order (SRV-14). The note arithmetic is the program's: the kit has none (S6581-52). The play is sent once, when the page is opened, and not again while the connection stays on it (`integration.md` INT-28).

### 4.2 A live keyboard (synth106)

The viewer plays synth106 from the keyboard on page 310: the keys `a` to `k` are a white-key octave from middle C. The program sends the bank of example 4.3 and announces a live sound when the connection opens the page, turns each key press and release into a note on or note off at the program's own time, and every 100 milliseconds sends what it has with `until_us` one microsecond past now, so that every event given so far lies before it (SRV-74 refuses an event at or after `until_us`) and the server writes every block that has ended (MIDI-20).

```ts
import type { Application, Context, Input } from "neoteletext-server-ts-protocol";
import type { SoundPlayMember, SoundStopMember, SoundSynth106EventsMember, SoundSynth106LiveMember, Synth106Event } from "neoteletext-server-ts-protocol/protocol";

import { BRASS_BANK, brassBank } from "./patch-by-fields.ts";

const KEYBOARD_PAGE = 0x310;
const LIVE_HANDLE = 6;
/** Middle C, MIDI note 60, then the white keys up to the next C. */
const KEY_NOTES: Readonly<Record<string, number>> = { a: 60, s: 62, d: 64, f: 65, g: 67, h: 69, j: 71, k: 72 };
/** How often the program says how far it has given every event: well inside MIDI-20's 2,000,000 microseconds a message. */
const FEED_MS = 100;
const MICROSECONDS_A_MILLISECOND = 1_000;
/** `until_us` is one microsecond past now, so that an event stamped now is before it (SRV-74). */
const PAST_NOW_US = 1;

/** One connection's live sound: its start on the program's clock and the events not yet sent. */
interface Player {
  readonly startMs: number;
  pending: Synth106Event[];
}
const players = new Map<number, Player>();
const nowUs = (player: Player, context: Context): number => (context.now() - player.startMs) * MICROSECONDS_A_MILLISECOND;

export const keyboard: Application = {
  pages: () => [/* page 310 among them */],
  start: () => players.clear(),
  opened(connection: number, page: number, context: Context): void {
    if (page !== KEYBOARD_PAGE) {
      return;
    }
    const live: SoundSynth106LiveMember = { kind: "synth106_live", handle: LIVE_HANDLE, generation: 0, banks: [BRASS_BANK] };
    const play: SoundPlayMember = { kind: "play", channel: 1, handle: LIVE_HANDLE, generation: 0, gain: 100, fade_ms: 0, loop: false, after: false, duck: 0, page: "310" };
    context.sound({ connection }, brassBank());
    context.sound({ connection }, live);
    context.sound({ connection }, play);
    players.set(connection, { startMs: context.now(), pending: [] });
    context.wakeIn(FEED_MS);
  },
  input(connection: number, _page: number, input: Input, context: Context): boolean {
    const player = players.get(connection);
    const key = input.kind === "key" && input.action !== "repeat" ? KEY_NOTES[input.text ?? input.key] : undefined;
    if (player === undefined || key === undefined || input.kind !== "key") {
      return false;
    }
    const time_us = nowUs(player, context);
    player.pending.push(input.action === "press" ? { event: "note_on", time_us, channel: 1, key, velocity: 100 } : { event: "note_off", time_us, channel: 1, key, velocity: 64 });
    return true;
  },
  wake(context: Context): void {
    for (const [connection, player] of players) {
      const events: SoundSynth106EventsMember = { kind: "synth106_events", handle: LIVE_HANDLE, generation: 0, until_us: nowUs(player, context) + PAST_NOW_US, events: player.pending };
      context.sound({ connection }, events);
      player.pending = [];
    }
    if (players.size > 0) {
      context.wakeIn(FEED_MS);
    }
  },
  leftPage(connection: number, _page: number, context: Context): void {
    if (players.delete(connection)) {
      const stop: SoundStopMember = { kind: "stop", channel: 1, fade_ms: 20 };
      context.sound({ connection }, stop);
    }
  },
};
```

What happens: each events message is validated and written. The server writes the events into the blocks their times fall in, sends the blocks that have ended by `until_us` no more than 25 blocks ahead of the live sound's clock (SRV-77), restates the part at least once in every 50 blocks for a viewer who joins late (MIDI-96), and refuses an event whose block it has already written (MIDI-20): a key pressed just after a wake is placed at its own time, which lies after the last block written, so it is never late. The kit numbers no block and keeps no clock but the one it already has for wakes (TS-26). The live sound names the bank of example 4.3, sent first, as every sound of a family with banks names 1 to 10 banks (MIDI-57); with no program change the part plays program 0 of bank index 0 (MIDI-61). `FEED_MS` and `KEY_NOTES` are the program's; a wake is the kit's existing `wakeIn`.

### 4.3 A patch by fields (synth106)

A synth106 patch in the `fields` form (MIDI-14 form 1; SRV-30: the sixteen sliders 0 to 127, range, pulse, sawtooth, chorus, PWM source, envelope polarity, VCA control and the high-pass filter), used twice: as the one patch of a bank (SRV-20's `patches` form), which a sound of the family must name (MIDI-57), and inline as the first event of a stored phrase (MIDI-60; SRV-22). The file is `patch-by-fields.ts`, which example 4.2 imports.

```ts
import type { SoundSynth106BankMember, SoundSynth106Member, Synth106Panel } from "neoteletext-server-ts-protocol/protocol";

export const BRASS_BANK = 5;

export const BRASS: Synth106Panel = {
  lfo_rate: 40, lfo_delay: 0, dco_lfo: 0, dco_pwm: 0, noise_level: 0,
  vcf_frequency: 52, vcf_resonance: 18, vcf_envelope: 70, vcf_lfo: 0, vcf_keyboard: 64,
  vca_level: 90, attack: 22, decay: 60, sustain: 80, release: 30, sub_level: 40,
  range: "feet_8", pulse: false, sawtooth: true, chorus: "one",
  pwm: "manual", envelope_polarity: "positive", vca: "envelope", hpf: 0,
};

export function brassBank(): SoundSynth106BankMember {
  return { kind: "synth106_bank", handle: BRASS_BANK, generation: 0, bank: { form: "patches", patches: [{ form: "fields", ...BRASS }] } };
}

export function brassPhrase(): SoundSynth106Member {
  return {
    kind: "synth106",
    handle: 7,
    generation: 0,
    banks: [BRASS_BANK],
    lift_banks: [],
    length: { tail_us: 800_000 },
    music: {
      form: "events",
      events: [
        { event: "patch", time_us: 0, channel: 1, patch: { form: "fields", ...BRASS } },
        { event: "note_on", time_us: 0, channel: 1, key: 60, velocity: 96 },
        { event: "note_off", time_us: 400_000, channel: 1, key: 60, velocity: 64 },
      ],
    },
  };
}
```

What happens: a program sends `brassBank()` before `brassPhrase()`. The server encodes the fields into the Juno-106's 24-byte patch message (S106-37), once for the bank image and once as one system exclusive event at tick 0 of the phrase, before the note on (MIDI-35); the two are identical bytes (MIDI-14). A missing field or a field outside its range is thrown by the kit's validator before anything is written (TS-16); a value the schema cannot state as wrong is the server's refusal (TS-17). The kit holds no default synth106 patch: the program writes every field (TS-26). `Synth106Panel` is the generated type of the server's `Synth106Panel` (SRV-30), and the patch's `fields` form is that type's fields beside `form`, as SRV-21's internally tagged enum writes it.

### 4.4 A patch by system exclusive (synth7)

A DX7 voice as the 163 bytes of a single-voice bulk dump, as any librarian saves it, sent inline at the start of a stored sound (MIDI-14 form 2; MIDI-54; MIDI-60). The sound names a bank, as every sound of a family with banks must (MIDI-57): here a bank of that one voice in the `patches` form, each patch given as its bytes, which the server fills to 32 voices with the default voice (SRV-56).

```ts
import { readFileSync } from "node:fs";
import type { SoundSynth7BankMember, SoundSynth7Member } from "neoteletext-server-ts-protocol/protocol";

/** A DX7 single-voice bulk dump is 163 bytes (MIDI-54): a program should not send what it knows is not one. The server checks the bytes. */
const VOICE_DUMP_BYTES = 163;
const VOICES = 9;

function readVoice(voiceFile: string): Uint8Array {
  const dump = new Uint8Array(readFileSync(voiceFile));
  if (dump.length !== VOICE_DUMP_BYTES) {
    throw new RangeError(`${voiceFile}: ${dump.length} bytes, not a single-voice dump`);
  }
  return dump;
}

export function voiceBank(voiceFile: string): SoundSynth7BankMember {
  return { kind: "synth7_bank", handle: VOICES, generation: 0, bank: { form: "patches", patches: [{ form: "bytes", bytes: readVoice(voiceFile) }] } };
}

export function electricPiano(voiceFile: string): SoundSynth7Member {
  return {
    kind: "synth7",
    handle: 8,
    generation: 0,
    banks: [VOICES],
    lift_banks: [],
    length: { tail_us: 1_500_000 },
    music: {
      form: "events",
      events: [
        { event: "patch", time_us: 0, channel: 1, patch: { form: "bytes", bytes: readVoice(voiceFile) } },
        { event: "note_on", time_us: 0, channel: 1, key: 64, velocity: 90 },
        { event: "note_off", time_us: 1_000_000, channel: 1, key: 64, velocity: 64 },
      ],
    },
  };
}
```

The length check is the program's own choice about its own file, not a kit rule. The kit writes each dump as base64 (TS-21). The server checks the dump with the receiver's own code (header, byte ranges, checksum; MIDI-21, MIDI-63) and refuses a faulty one, naming the byte, which the application's `refused` handler hears; it writes it as one system exclusive event of 163 bytes, within MIDI-28's 256.

### 4.5 A bank (synth53 and synth80)

**synth53.** A bank of 1 to 40 program dumps of one group (S53-47; MIDI-56), given as the dumps' bytes from a file a librarian saved, and a stored sound that names it and plays programs 0 and 1, the group chosen by bank select on controller 32 (MIDI-64; S53-13: value 1 chooses group 0, the group of the file's dumps), written as the program change's `bank_lsb` so that the select and the change are one event (SRV-10).

```ts
import { readFileSync } from "node:fs";
import type { Application, Context } from "neoteletext-server-ts-protocol";
import type { SoundSynth53BankMember, SoundSynth53Member, SoundSynth80BankMember } from "neoteletext-server-ts-protocol/protocol";

const BANK_HANDLE = 20;
/** Controller 32's value 1 chooses group 0 (S53-13), the group of the bank's dumps. */
const GROUP_0 = 1;

export function groupBank(dumpsFile: string): SoundSynth53BankMember {
  return { kind: "synth53_bank", handle: BANK_HANDLE, generation: 0, bank: { form: "bytes", bytes: new Uint8Array(readFileSync(dumpsFile)) } };
}

export function twoPrograms(): SoundSynth53Member {
  return {
    kind: "synth53",
    handle: 21,
    generation: 0,
    banks: [BANK_HANDLE],
    lift_banks: [],
    length: { tail_us: 1_000_000 },
    music: {
      form: "events",
      events: [
        { event: "program_change", time_us: 0, channel: 1, program: 0, bank_lsb: GROUP_0 },
        { event: "note_on", time_us: 0, channel: 1, key: 57, velocity: 100 },
        { event: "note_off", time_us: 1_000_000, channel: 1, key: 57, velocity: 64 },
        { event: "program_change", time_us: 1_000_000, channel: 1, program: 1, bank_lsb: GROUP_0 },
        { event: "note_on", time_us: 1_000_000, channel: 1, key: 57, velocity: 100 },
        { event: "note_off", time_us: 2_000_000, channel: 1, key: 57, velocity: 64 },
      ],
    },
  };
}

export const banked: Application = {
  pages: () => [/* page 320 among them */],
  start: () => {},
  opened(_connection: number, page: number, context: Context): void {
    if (page === 0x320) {
      context.sound({ page }, groupBank("group-0.syx"));
      context.sound({ page }, twoPrograms());
    }
  },
};
```

The kit neither splits the bank's dumps nor checks that the bank arrives before the sound: the server splits them into the bank codec's records (MIDI-55), checks each dump (MIDI-63), sends the bank before the sound's OBJECT (MIDI-57), and refuses a sound that names a bank it does not hold for this program.

**synth80.** A bank given as a list of patches, each in the `bytes` form: for synth80 a patch is 85 control values in `synth80.md`'s fixed order (MIDI-54; S80-33). Three such banks are what Deckard's Dream's controller 0 chooses among (values 0 to 2; S80-36).

```ts
export function stringsBank(patches: readonly Uint8Array[]): SoundSynth80BankMember {
  return { kind: "synth80_bank", handle: 30, generation: 0, bank: { form: "patches", patches: patches.map((bytes) => ({ form: "bytes", bytes })) } };
}
```

A sound naming banks 30, 31 and 32 as bank indexes 0, 1 and 2 then plays bank 2's program 5 with `{ event: "program_change", time_us, channel: 1, program: 5, bank_msb: 2 }` (MIDI-59, MIDI-64; SRV-10 writes `Bn 00 02` then `Cn 05` at one tick).

### 4.6 A Standard MIDI File (synth7)

A Standard MIDI File made for a DX7, played on synth7, its channels 1 and 2 mapped to parts 1 and 2 and every other channel dropped (MIDI-116; SRV-23). The file opens with a 32-voice bulk dump, which the server lifts into a bank with the handle the program names (MIDI-58; SRV-15); that lifted bank is the sound's only bank, so `banks` is empty and the lifted bank is bank index 0, as SRV-16 allows (DEC-6477). The program hears the server's report of the sound, `sound_built` (SRV-47), by the handler TS-23 names for it.

```ts
import { readFileSync } from "node:fs";
import type { Application, Context } from "neoteletext-server-ts-protocol";
import type { SoundBuilt, SoundSynth7Member } from "neoteletext-server-ts-protocol/protocol";

const FILE_PAGE = 0x330;
const LIFTED_BANK = 40;

export function fromFile(midiFile: string): SoundSynth7Member {
  return {
    kind: "synth7",
    handle: 41,
    generation: 0,
    banks: [],
    lift_banks: [{ handle: LIFTED_BANK, generation: 0 }],
    length: { tail_us: 2_000_000 },
    music: {
      form: "midi_file",
      bytes: new Uint8Array(readFileSync(midiFile)),
      channel_map: [1, 2, null, null, null, null, null, null, null, null, null, null, null, null, null, null],
    },
  };
}

export const filePlayer: Application = {
  pages: () => [/* page 330 among them */],
  start: () => {},
  opened(_connection: number, page: number, context: Context): void {
    if (page === FILE_PAGE) {
      context.sound({ page }, fromFile("tune.mid"));
    }
  },
  soundBuilt(report: SoundBuilt, context: Context): void {
    context.log(`${report.kind} ${report.handle}: ${report.blocks} blocks, dropped ${JSON.stringify(report.dropped)}`);
  },
};
```

The kit sends the file's bytes as they are; it parses nothing (MIDI-112). The server reads the file within MIDI-119's bounds (at most 1,048,576 bytes, 1,024 tracks, 100,000 events), merges tempo (MIDI-114), joins split system exclusive (MIDI-117), lifts the leading dump into bank 40 as the sound's bank index 0, refuses a dump after the first note (MIDI-58), builds the blocks, and reports what it dropped (MIDI-118; SRV-47).

### 4.7 A named parameter in a live sound, and a patch of control values (synth8 and synthD)

**synth8.** In a live synth8 sound the viewer's mouse wheel moves the filter's cutoff by name (MIDI-18; SRV-22). The program names the parameter as SRV-42 names synth8's parameters, the field names of `Synth8Panel` (SRV-40), and gives its value; the server writes the controller the family document names for it (controller 3, S8-16). Announcing the live sound, keeping its start time and advancing `until_us` by wakes between turns of the wheel are as in example 4.2 and left out here.

```ts
import type { Context, Input } from "neoteletext-server-ts-protocol";
import type { SoundSynth8EventsMember } from "neoteletext-server-ts-protocol/protocol";

const LIVE8 = 50;
/** The cutoff's lowest and highest values, the program's own choice of how far the wheel moves it. */
const LOWEST_CUTOFF = 0;
const HIGHEST_CUTOFF = 127;
const MIDDLE_CUTOFF = 64;
const MICROSECONDS_A_MILLISECOND = 1_000;
/** `until_us` is one microsecond past the event, so that the event is before it (SRV-74). */
const PAST_NOW_US = 1;
const cutoffs = new Map<number, number>();
/** Each connection's live sound's start on the program's clock, set where the sound is announced. */
const startsMs = new Map<number, number>();

export function wheel(connection: number, input: Input, context: Context): boolean {
  const startMs = startsMs.get(connection);
  if (input.kind !== "wheel" || startMs === undefined) {
    return false;
  }
  const cutoff = Math.min(HIGHEST_CUTOFF, Math.max(LOWEST_CUTOFF, (cutoffs.get(connection) ?? MIDDLE_CUTOFF) - input.dy));
  cutoffs.set(connection, cutoff);
  const time_us = (context.now() - startMs) * MICROSECONDS_A_MILLISECOND;
  const events: SoundSynth8EventsMember = {
    kind: "synth8_events",
    handle: LIVE8,
    generation: 0,
    until_us: time_us + PAST_NOW_US,
    events: [{ event: "parameter", time_us, channel: 1, set: { vcf_cutoff: cutoff } }],
  };
  context.sound({ connection }, events);
  return true;
}
```

The clamp is the program's own choice of how the wheel moves; the kit checks the value only against the schema's range for `vcf_cutoff`.

**synthD.** A stored synthD sound whose patch is the 60 control values in `synthd.md`'s fixed order (SD-22), given in the `bytes` form, sent inline (MIDI-60): the server writes them as the 60 control changes they stand for, at one tick (SD-26, MIDI-79). The same values are the one patch of the bank the sound names (MIDI-57).

```ts
import type { SoundSynthdBankMember, SoundSynthdMember } from "neoteletext-server-ts-protocol/protocol";

const BASS_BANK = 61;

export function bassBank(values: Uint8Array): SoundSynthdBankMember {
  return { kind: "synthd_bank", handle: BASS_BANK, generation: 0, bank: { form: "patches", patches: [{ form: "bytes", bytes: values }] } };
}

export function bass(values: Uint8Array): SoundSynthdMember {
  return {
    kind: "synthd",
    handle: 60,
    generation: 0,
    banks: [BASS_BANK],
    lift_banks: [],
    length: { tail_us: 500_000 },
    music: {
      form: "events",
      events: [
        { event: "patch", time_us: 0, channel: 1, patch: { form: "bytes", bytes: values } },
        { event: "note_on", time_us: 0, channel: 1, key: 36, velocity: 110 },
        { event: "note_off", time_us: 250_000, channel: 1, key: 36, velocity: 64 },
      ],
    },
  };
}
```

---

## 5. What is left out

| Left out of the kit | Reason | Requirement |
|---|---|---|
| Patch packers, default patches, initial voices and patch tables, for every family | Instrument logic; the server encodes named fields (MIDI-14, SRV-21) | TS-1, TS-26, TS-36 |
| Block, slot, register-image and score builders | The server builds blocks (MIDI-13) | TS-1, TS-36 |
| The program-change repeater | The server restates the whole state (MIDI-93 to MIDI-99) | TS-36 |
| The Standard MIDI File reader and its byte reader | The server reads files (MIDI-112) | TS-26, TS-36 |
| The 32-voice dump reader | The server reads dumps (SRV-20) | TS-36 |
| synth6581 note, gate, hard-restart and frequency helpers, and the clock constants | No note layer anywhere in NeoTeletext (S6581-52; DEC-6465 answer 8); note help belongs in an example program | TS-36, TS-39 |
| Copies of the server's rules for synthesizer messages (`instrument-rules.ts`, `synth-patch-rules.ts`, `synth7-slot.ts`'s `slot_fault`) and for Opus packets and samples (`opus-packet.ts`, `opus-fields.ts`, `sound-rules.ts`) | DEC-6462 item 3; DEC-6477; the server's refusal is the one report | TS-17 |
| Translation of field names between camel case and the wire's | A hand-written copy of every field name; members are the wire's | TS-11, TS-19 |
| Synthesizer constants (block length, slot bytes, patch sizes, the family table) | The schema's bounds and the server's constants | TS-36 |
| A live-sound object, a clock, and any time conversion | The program keeps its own time (MIDI-17, MIDI-20); the Python kit has none (TS-2) | TS-26 |
| A promise answering each sound | The server answers sounds by refusals and reports, each naming the sound; the two kits behave alike (DEC-6477) | TS-24 |
| A sound audience by viewer handle | Sounds go to connections or pages; viewers are `viewer-state.md`'s | TS-28 |

---

## 6. What this document defines itself

Each item is a choice on the TypeScript side that neither DEC-6462, the architecture nor the server document makes.

1. **Generated types over hand-written ones, by a generator of the kit's own** (TS-8, TS-9): DEC-6462 allows either; generation makes the types the schema's by construction; the kit's own generator avoids a library the owner has not approved. The Python document chose the same for its kit (PY-7).
2. **The generator's keyword table and its refusal of anything else** (TS-9), including `contentEncoding` and `allOf`.
3. **The generated types' names** (TS-10, word for word PY-10) and **the member types** (TS-11, as PY-12).
4. **The gate step "the types, from the server's schema", with its determinism check, and the generated file uncommitted** (TS-12), where the Python kit commits its module (PY-14) because it has no build.
5. **The audiences** (TS-20): `{ connection }`, `{ page }`, `{ connections: [...] }`, `{ connections: "all" }`, the Python kit's hearers one for one; `viewer-state.md` names none.
6. **Bytes as `Uint8Array` where the schema marks them base64** (TS-21, as PY-13), which the server document marks (SRV-6).
7. **The handlers `refused` and one a report of a sound, called on every application that has them** (TS-22, TS-23): the TypeScript kit has several applications to a channel where the Python kit has one `App`.
8. **The harness's `sounds`, `soundsOfKind`, `soundsToEveryone`, `refuse`, `report` and `restart`** (TS-29 to TS-31), as PY-44 and PY-45 name them.
9. **`COMMON_FROM` and the kit's copies of `kit-calls.tsv` and `examples.jsonl`** (TS-2, TS-6), and the list of `Application`'s handlers that lets a test check them (`src/channel/handlers.ts`).
10. **The examples as compiled tests checked against the shared fixture** (TS-43), **and their inputs and scenarios** (section 4.0), on which the fixture's lines depend.
11. **The audio demo's own synth6581 register helpers in `src/synth6581/registers.ts`** (TS-39), where DEC-6465 answer 8 places note help.

---

## 7. Open questions for the owner

Every question of this section was answered by DEC-6477 (18 November 2026, at the owner's delegation, awaiting the owner's review), each answer the recommendation; the answer is recorded under each question, and the requirements cited follow it.

**1. Bytes in the schema.** *Answered by DEC-6477 (typescript answer 1): option A; the server's schema marks every bytes field `contentEncoding: "base64"` (SRV-6), and TS-21 types them `Uint8Array`.*
TS-21 and PY-13 type a bytes field as bytes (`Uint8Array`, `bytes`) only where the schema marks it `"contentEncoding": "base64"`; SRV-6 gives such fields the type `Base64`, and protocol 12's schema marks none (it says "exact base64" only in descriptions).
- *Option A:* the server document requires `Base64`'s schema to carry `"contentEncoding": "base64"` (a `schemars` attribute on the type), so that both kits take bytes.
- *Option B:* no mark; programs in both languages give base64 text themselves.
- *Recommendation:* A; it is one attribute in the server, and it removes a step of the wire from every program.

**2. A library for generating types.** *Answered by DEC-6477 (typescript answer 2): option A, no library; the kit's own generator (TS-9).*
- *Option A* (written): the kit's own generator, `scripts/types.ts`, for the keywords `schemars` writes (TS-9).
- *Option B:* a library such as `json-schema-to-typescript` (MIT), approved by name under DEVELOPMENT.md section 7, as a development dependency only. Less code of the kit's own; its output for `schemars`' shapes (inline tagged unions, `type` arrays with `"null"`, `allOf`) would need checking, and its names for inline types are its own, which would differ from the Python kit's (TS-10).
- *Recommendation:* A.

**3. Should a sound call be answered?** *Answered by DEC-6477 (typescript answer 3): option A; sound calls stay unanswered in 15.0.0, and every refusal (its `sound` field, SRV-48) and every `sound_built` (SRV-47) names the sound it concerns (TS-24).*
As written (TS-24, as PY-34), a sound call returns nothing; refusals and reports reach handlers, and a program matches them to its sounds by what they carry. A refusal of a sound carries the path and the rule but nothing that names which `sound` line it refuses; with several sounds written together, the program cannot always tell.
- *Option A* (written): no answer to the call; the server document makes each report carry the sound's kind, handle and generation, and a refusal of a sound the same, so that handlers can match.
- *Option B:* the server document gives every `sound` message a request number, echoed by `refused` and by its report, as `measure` has (REQ-2216); `context.sound` then returns a promise settled by the report or rejected by the refusal, and the Python kit's `sound` becomes awaitable the same way. A program feeding a live sound need not await it.
- *Recommendation:* A for 15.0.0, with the server document asked to make reports and refusals of sounds name the sound; B if programs prove unable to match them. Either way both kits change together (TS-2).

**4. Do all the hand-written protocol types go in the same release?** *Answered by DEC-6477 (typescript answer 4): option A; every hand-written protocol type is replaced by generated types in 15.0.0, not only the sound ones (TS-15).*
TS-15 requires generated types for every sound message and every server message a sound call or handler meets. The pages, input, ReGIS, NAPLPS and other messages of `src/wire/protocol.ts` are hand-written today and checked by samples.
- *Option A:* replace them all with generated types in 15.0.0, each in its own commit; one way of typing the protocol, as `viewer-state.md` section 14.4 says.
- *Option B:* only those TS-15 requires in 15.0.0; the rest in a later release.
- *Recommendation:* A, since 15.0.0 already breaks every sound and session call; it is wider than this document's subject, so it is the owner's to choose.

**5. The kit's copies of the server's Opus and sample rules.** *Answered by DEC-6477 (typescript answer 5): option A; the kit's copies are removed (TS-17, TS-36).*
`opus-packet.ts` ports the engine's Opus packet check, and `opus-fields.ts`, `sound-fields.ts` and `sound-rules.ts` check sampled sounds as the server does. They are not synthesizer code, but DEC-6462 item 3's principle ("no copies of the server's rules beyond what the schema gives") reads on them, and the Python kit will hold none (PY-16).
- *Option A:* remove them in 15.0.0; the server's refusal reports an Opus packet the receivers would refuse (`outside_profile`).
- *Option B:* keep them; a program learns of a bad packet before sending two minutes of sound.
- *Recommendation:* A, for one rule in one place and two equal kits; the Opus encoder that makes the packets stays.

**6. A second announcement of a live sound.** *Answered by DEC-6477 (typescript answer 6): a second announcement of a live sound to more connections sends those connections the OBJECT only (SRV-73), as recommended.*
The audio demo sends a live sound's announcement to each connection that opens the page while it plays, and feeds it to the page. Under protocol 13 the server builds the blocks and holds each live sound's state (MIDI-94). Whether a second announcement of a handle and generation the server already holds, to more connections, continues the live sound or starts it again is the server document's.
- *Recommendation:* that the server document say a repeated announcement of a held handle and generation sends its OBJECT to the connections named and changes nothing else; TS-39's live page is written for that.

---

## 8. Differences from what is built today, and conflicts found

**The kit (neoteletext-server-ts-protocol, release 14.0.0 at `6d54c3d`).**
1. Today the kit speaks protocol 12, with `schema/protocol-12.json` pinned by `SCHEMA_FROM = df662b9`. It will speak 13, with `schema/protocol-13.json` (TS-3, TS-5, TS-6).
2. Today the protocol's TypeScript types are hand-written (`src/wire/protocol.ts`: "hand-written to match the server's published schema"; `instrument-wire.ts`) and held to the schema by sample values in `test/protocol.test.ts`. They will be generated (TS-8 to TS-15); the gate gains the step "the types, from the server's schema" (TS-12).
3. Today a program sends members of the kit's own camel-case shapes (`{ synth7: { handle, generation, slots, bank, blocks } }`), which the kit translates into protocol 12's fields, with blocks and banks the kit built, as base64. It will send generated members with the wire's names, which the kit writes as given, bytes as `Uint8Array` (TS-11, TS-19, TS-21).
4. Today `{ session }` is an audience; it becomes `{ connection }` (TS-20).
5. Today a refusal is only logged by `Channel.refused`. It reaches an application's `refused` handler, and the server's reports of sounds reach handlers of their own (TS-22, TS-23).
6. Today the kit checks every synthesizer message with ports of the server's rules (`instrument-rules.ts`, `synth-patch-rules.ts`, `synth7-slot.ts`, `member-pieces.ts`), throwing `RangeError`. It will check only what the schema states, throwing `ProtocolError` (TS-16, TS-17).
7. Today the kit packs patches for every family, builds blocks of slots and register images, reads Standard MIDI Files and 32-voice dumps, repeats program changes on live sounds, and offers synth6581 note helpers: 3,413 lines in 28 modules of `src/sound/` and 169 in 2 of `src/wire/`. All of it is deleted (TS-36).
8. Today the harness offers `soundBytes` to read a sound line's bytes. It will offer typed members, refusals and reports a test gives, a restart, and a test against the real server (TS-29 to TS-33).
9. Today nothing holds the TypeScript and Python kits to the same calls or lines. `docs/audio/kit-calls.tsv` and `docs/audio/examples.jsonl` in neoteletext-common will (TS-2).
10. Release 15.0.0, breaking, together with `viewer-state.md`'s changes (TS-34).

**The audio demo (neoteletext-server-channel-audiodemo at `3dc1d68`).**
11. Today it builds every synthesizer sound's bytes with the kit's packers, scores, tracks and images, and numbers its live blocks. It will send generated members: patches by fields, music as timed events in microseconds, register updates by named fields, a live sound's events with `until_us` (TS-38, TS-39).
12. Its synth6581 helpers (frequency, hard restart) move from the kit into the demo (TS-39).
13. Its patches are written again in the family documents' fields, and its gains measured again (TS-40, TS-41).
14. Its tests read typed members from the harness (TS-42).

**Conflicts found with the other documents of this set, as read on 18 November 2026, each settled by DEC-6477 and carried into the documents.**
15. *Settled: names follow `server.md` in both kits' examples, which write identical lines (`docs/audio/examples.jsonl`).* **`python.md` section 5 and `server.md` spelled the sound messages differently**, and both kits must send the server document's lines into one `examples.jsonl`. `python.md`'s examples write `time` where SRV-8 has `time_us`; events as `{ "time", "message": { "type": "note_on", … } }` where SRV-10 has `{ "event": "note_on", "time_us", … }`; a top-level `tail_us` where SRV-9 has `length: { "tail_us" }`; `events` or `updates` or `midi_file` at the top where SRV-14 has `music: { "form": … }`; `until` where SRV-18 has `until_us`; `banks` as objects with handle and generation where SRV-16 has a list of `u8` handles; `lifted_banks` where SRV-15 has `lift_banks`; synth6581 register fields `voice1_frequency` of 16 bits where SRV-12 has `voice1_frequency_low` and `voice1_frequency_high`, and its updates without `event: "register_update"`; a parameter as `{ "name", "value" }` where SRV-22 has `set: { name: value }`; `play` without the fields protocol 12 requires (`fade_ms`, `loop`, `after`, `duck`); bank select as a separate `control_change` event where SRV-10 carries it in the program change's `bank_msb` and `bank_lsb` (examples 4.5 and 5.5); and sounds of families with banks that name no bank (`"banks": []` in `python.md` sections 5.2, 5.3, 5.4 and 5.7), which MIDI-57 refuses ("A sound of a family with banks MUST name 1 to 10 banks"; SRV-16: `banks`, "a list of 1 to the family's most banks"). This document's examples follow `server.md` and MIDI-57, and `python.md`'s were corrected to them, as its own PY-73 requires, so that one `examples.jsonl` holds both kits' lines. The examples also corrected two faults of their own: `until_us` set equal to an event's `time_us`, which SRV-74 refuses (`not_before_until`), is now one microsecond later; and the synth106 patch fields and synth8's parameter are now SRV-30's and SRV-42's names.
16. *Settled: `banks` may be empty when `lift_banks` names the sound's only bank (SRV-16, SRV-58), MIDI-57's count being of the banks the OBJECT's tag 4 names.* **A sound whose only bank is lifted from its file.** Example 4.6 (and `python.md` 5.6) gives `banks: []` with one name in `lift_banks`. SRV-16 says `banks` is "a list of 1 to the family's most banks" and also that lifted banks follow them with "the total" within the most; the server document must say whether `banks` may be empty when `lift_banks` is not. If not, example 4.6 must name a bank sent beforehand, and the lifted bank becomes bank index 1, which programs 0 to 31 do not reach (`synth7.md`, S7-50).
17. *Settled: `server.md` is complete, and every reference here is to its final numbers (`sound_built` SRV-47, `Refused`'s `sound` SRV-48, the refusal rules SRV-51); the examples' synth106 fields are SRV-30's and synth8's `vcf_cutoff` is SRV-40's field.* **`server.md` was incomplete when this document was first written.**
18. *Settled: TS-10's and PY-10's rules are one rule, word for word.* **Inline type names.** SRV-3 asks that every synthesizer type be a named type of `$defs`; protocol 12's schema writes the sound kinds inline. The one rule names a kind's branch `Sound` followed by the kind whether its fields are inline or a named definition.

**rdm records the main session will need to revise on approval (no rdm record was changed in writing this document).**
19. REQ-6414 (the kit's instrument sounds: register image builders, the hard-restart helper, note-block builders, bank readers, a MIDI file reader, program-change repetition) is contradicted item by item by TS-1 and TS-36, as `synth6581-synth8580.md` section 9.3 item 17 also says; it is to be superseded by this document's requirements.
20. DEC-6419 item 3 (the kit's hard-restart helper) is to be revised: the helper moves into the audio demo (TS-39).
