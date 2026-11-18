# Programming the synthesizers from Python

**Purpose.** This document specifies how a channel's program written in Python plays and programs NeoTeletext's eleven synthesizers: how the Python kit takes the server's generated schema of program protocol 13, how its Python types are made from that schema, the thin calls a program makes, how a message is validated before it is written, the test harness a channel's tests drive, which of the Python kit's gaps of today this work closes, how the old Python Hackaday channel moves to protocol 13, and worked examples of a program playing each family. It is the basis for implementing the Python half of the synthesizers' programming interface, in the repository neoteletext-server-channels (`kits/python` and `hackaday`).

**Scope.** The Python kit (`neoteletext_app`, in `neoteletext-server-channels/kits/python`) and the old Python Hackaday channel (`neoteletext-server-channels/hackaday`). It does not define any message, field, kind, bound or refusal of the program protocol: the server document of this set, `server.md` (prefix SRV-), is the main specification of protocol 13's sound messages, and `midi-architecture.md` (prefix MIDI-) and the seven family documents say what the messages mean. Where this document needs something of the server, it says so and names it as a need, not as a definition. It does not specify the TypeScript kit, which `typescript.md` (prefix TS-) does; it requires that the Python kit be the TypeScript kit's equal (DEC-6462 item 3) and says how that equality is checked. It does not specify the viewer-state messages of protocol 13 (`viewer-state.md`, VS-351 to VS-354 and VS-401 to VS-404), which it takes as they are.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

Which instrument each synthesizer models is said once, in `synthesizers.md` in this folder, with the trademark statement.

**What this document decides, in brief** (each item is specified by the requirements cited):
1. The kit carries `protocol-13.json`, the server's `protocol/schema-13.json` byte for byte, pinned by the commit `SCHEMA_FROM` names in `scripts/check.sh`, exactly as it carries `protocol-12.json` today; the kit speaks protocol 13 only and stops at a `start` of any other version (PY-1 to PY-6).
2. The kit's Python types are **generated from the schema** as `TypedDict` classes and `Literal` unions by a generator of the kit's own, written with Python's standard library only, so that no library is added; the generated module is committed and the commit gate fails when it differs from what the generator makes of the schema copy (PY-7 to PY-17).
3. A program sends every sound with one call, `sound(to, member)`, whose `member` is any member of the generated `SoundMember` union; it sends the other picture and viewer messages with one call each; it hears the server's refusals and sound reports through handlers, each naming the sound it concerns. The calls are the TypeScript kit's calls with their names in `snake_case`, checked against one shared list in neoteletext-common, `docs/audio/kit-calls.tsv` (PY-18 to PY-34).
4. Every message is validated against the schema, and only the schema, before it is written, with the `jsonschema` validator the kit's tests already use, a run-time dependency of the kit with the packages it requires, approved by the owner by name (DEC-6474). Nothing beyond the schema is checked: the server's typed refusal is how a program learns of every other fault (PY-35 to PY-42).
5. The kit's test module gains a harness equal to the TypeScript kit's, which records every sound a program sends, validated, and can answer with a refusal or a report (PY-43 to PY-50).
6. This work closes every sound gap of the Python kit, its picture gaps (ReGIS, NAPLPS, measuring), its session coupling (TODO-6445) and its missing harness; it leaves Opus encoding, which is not part of the synthesizers' interface, as a recorded inequality (PY-51 to PY-58).
7. The old Hackaday channel moves to protocol 13 with exactly the changes needed to keep running (PY-59 to PY-65).
8. Seven worked examples, one for each family, cover a stored tune, a live keyboard, a patch by fields, a patch by system exclusive, a bank and a Standard MIDI File; each is also a test of the kit, writing exactly the TypeScript kit's lines, which `docs/audio/examples.jsonl` holds (PY-66 to PY-73, section 5).
9. Every open question of this document was answered by DEC-6474, and DEC-6477 settled its conflicts with the other documents: names follow `server.md` everywhere (section 8).

---

## 1. Sources

### 1.1 Decisions

| Decision | What this document takes from it |
|---|---|
| DEC-6462 | The Rust server is the core of the synthesizers' programming interface; a program sends structured, typed JSON (a patch as named, typed fields or as its standard system exclusive; music as timed MIDI events or a Standard MIDI File; a bank as a list of patches or its dump; play, stop, gain); the server validates it, builds blocks and records, splits long system exclusive into bank objects and restates for late joiners; the kits are thin: types generated from, or checked against, the server's schema, and the calls that send them; no instrument logic; **the TypeScript and Python kits are equals, neither can do what the other cannot**; the Python and TypeScript documents describe the generated types and how to call them. |
| DEC-6461 | The eleven names, each a kind of its own: synth6581, synth8580, synth7, synth106, synth60, synthD (`synthd` in identifiers), synth53, synth52, synth51, synth8, synth80. |
| DEC-6453 | Every synthesizer is programmed exactly as its adopted interface does it; a Python program therefore sends the adopted interface's own messages and patch forms, never a form of the kit's. |
| DEC-6464 version 2, DEC-6465, DEC-6473 | The common MIDI behaviours and the answers to the family documents' open questions; nothing here depends on them except that the worked examples obey them. |
| DEC-6471 | Program protocol 13 also removes cookies and the server session (`viewer-state.md`); the Python kit takes those changes in the same release (PY-55). |
| DEC-6443 | Every browser tab is a session of its own to applications; the TypeScript kit does it since its release 13.0.0; TODO-6445 records that the Python kit does not. |
| DEC-1082 (the server's decision 16), item 5 | The old Hackaday channel and the Python kit get exactly the changes needed to keep running when the protocol changes, and no other work. This document's work goes beyond that, as DEC-6462 requires: section 8 and open question 2. |
| DEC-1482 item 7, REQ-2769, REQ-2771, REQ-2772 | One schema, generated by `schemars` from the server's Rust types and published as `protocol/schema-<version>.json`; the TypeScript kit refuses a message the server would refuse before writing it, with the server's path and rule; the TypeScript kit's types are tested against the schema. |
| DEC-1543 item 5 | Today the Python kit checks its messages by hand and, in its tests, against the schema; it does not validate at run time. PY-35 changes that. |
| REQ-5207 | A kit exposes the limits `start` carries and holds no limit of its own. |
| DEVELOPMENT.md sections 7 and 13 | Every library needs the owner's approval by name; Python tools run with `uv` and `uvx`, never a permanent install; tools are pinned. |
| DEC-6474 | The owner's approval of run-time validation with `jsonschema` 4.25.1 and the packages it requires (`attrs`, `jsonschema-specifications`, `referencing`, `rpds-py`), each to be pinned with its licence and reason; the kit kept fully equal to the TypeScript kit, amending DEC-1082 item 5 for the kit; types generated by the kit's own standard-library script. It answers this document's three open questions (section 8). |
| DEC-6477 (awaiting the owner's review) | The settlement of the conflicts between this document and `server.md`, `typescript.md` and `integration.md`: names follow `server.md`; every bytes field is marked `contentEncoding: "base64"` (SRV-6); every refusal and `sound_built` names the sound; one naming rule for both kits' generated types. |

### 1.2 Documents of this set

| Document | What this document takes from it |
|---|---|
| `server.md` (SRV-) | The main specification of protocol 13's sound messages: every message type, `kind`, field, bound and typed refusal, and the server's reports to a program. Every name a worked example of section 5 uses is `server.md`'s. |
| `typescript.md` (TS-) | The TypeScript kit's calls, which the Python kit's calls equal (PY-18). |
| `midi-architecture.md` | What a program expresses (MIDI-13 to MIDI-22): patches in two forms (MIDI-14), banks (MIDI-15), timed events (MIDI-16), times in whole microseconds (MIDI-17), named parameters (MIDI-18), stored and live sounds (MIDI-19, MIDI-20), the server checking with the receiver's code (MIDI-21), the kits thin (MIDI-22); banks lifted from music (MIDI-58); program change and banks (MIDI-57, MIDI-59); Standard MIDI Files read by the server (MIDI-112 to MIDI-120); the server's bounds on a program's input (MIDI-122); protocol 13 (MIDI-111). |
| `synth6581-synth8580.md`, `synth7.md`, `synth106-synth60.md`, `synthd.md`, `synth53-synth52-synth51.md`, `synth8.md`, `synth80.md` | What each family's patch, bank and messages are; the sections each has on what it needs of the server and the kits (for example S6581-53, S6581-54, S106-36 to S106-40, S53-47). |
| `../viewer-state.md` | Protocol 13's viewer messages (VS-351 to VS-354), the kits' viewer calls and harness (VS-401 to VS-404), the order of the cut-over (VS-601, VS-602) and what changes in this repository (section 14.5). |

### 1.3 What is built today, read on 18 November 2026

| Source | What it is used for here |
|---|---|
| neoteletext-server-channels, commit `a802d56` ("Take program protocol 12 in the Python kit, so the old Hackaday channel keeps running"): `kits/python/src/neoteletext_app/app.py` (1,080 lines), `sound.py`, `testing.py`, `textrules.py`, `protocol-12.json`; `kits/python/tests/test_kit.py`; `scripts/check.sh`; `pyproject.toml`; `hackaday/src/hackaday/channel.py` | The kit and the channel as built: section 3. |
| neoteletext-app-server, commit `df662b9`: `crates/teletext-runtime/src/protocol.rs` (`PROTOCOL` = 12, the `Sound` enum, `schema()`), `protocol/check.rs` (`Refusal`, `Rule`), `protocol/schema-12.json` (204,002 bytes, SHA-256 `4a69ef281eada4f9911954b61035b778ea69a6e83cdd8e019d8005dad545c14b`) | The typed protocol as built and the JSON Schema constructs `schemars` emits (PY-9). |
| neoteletext-server-ts-protocol, commit `6d54c3d` (release 14.0.0, protocol 12): `src/channel/context.ts`, `src/sound/members.ts`, `src/wire/validate.ts`, `src/wire/protocol.ts`, `src/testing/harness.ts`, `scripts/check.sh`, `scripts/validators.ts` | The TypeScript kit's calls, validation and harness, which the Python kit is to equal. |

---

## 2. Terms

- **The kit.** The Python kit, the package `neoteletext_app` in `neoteletext-server-channels/kits/python`. "The TypeScript kit" is neoteletext-server-ts-protocol.
- **The server.** neoteletext-app-server, the one implementation of the synthesizers' programming interface (DEC-6462).
- **Program.** A channel's program: here, a Python program built on the kit, a subclass of `App`.
- **Protocol 13.** Program protocol version 13, the one version that carries both the synthesizers' messages (`midi-architecture.md`, MIDI-111; `server.md`) and the viewer-state messages (`viewer-state.md`, VS-351 to VS-354).
- **The schema.** The server's `protocol/schema-13.json`, a JSON Schema of draft 2020-12 generated by `schemars` from the server's Rust types; **the schema copy** is the kit's `protocol-13.json`.
- **Generated module.** The Python module the kit's type generator writes from the schema copy: `neoteletext_app/protocol_types.py` (PY-8).
- **Wire type.** A generated `TypedDict` that is one JSON object of the protocol exactly, every field with the wire's own name.
- **Member type.** A generated `TypedDict` that is a wire type without its `connections` field, which the kit fills from a hearer (PY-12).
- **Sound member.** Any member type of the protocol's `sound` message: a stored sound, a live sound, a live sound's next events, a bank, a play, a stop or a gain, of any kind the schema lists.
- **Hearer.** Who a message is for: one connection, the connections showing a page, a list of connections, or every connection (PY-21).
- **Handler.** A method of `App` the kit calls when something happens, named `on_…`, which a program overrides.
- **Fault.** What validation finds wrong with a message: a path in the server's form (`music.events[3].time_us`), a rule from the schema's `Rule` list, and a detail (PY-37).
- **Refusal.** The server's typed answer to a message it will not act on (`refused`: the message's type, the field's path, the rule, the detail and, for a sound, the sound it concerns; `midi-architecture.md`, terms; SRV-48).
- **Report.** An answer the server gives a program about a sound it accepted: `sound_built` (SRV-47), which names the sound and carries the counts of messages of a Standard MIDI File it dropped (MIDI-118).
- **Call list.** The shared file of every public call and handler of both kits, in both spellings (PY-19).

---

## 3. The Python kit today (facts, not requirements)

### 3.1 What it sends and hears

The kit's `App` (`app.py`) is a base class: a program overrides its handlers (`on_start`, `on_join`, `on_request`, `on_open`, `on_leave`, `on_input`, `on_close`, `on_stats`, `describe`) and calls its methods (`publish`, `redirect`, `release`, `title`, `log`, `author_log`, `cookie`, `cookies_of`, `sound_object`, `play`, `stop`, `packets`, `connections_of`, `current_connection`, `showing`, `shown`, `kept`, `index`, `initial_page`, `send`, `run`). Its handlers name **sessions**, which "outlive connections and are shared by a viewer's tabs" (the module's own text, lines 18 to 20).

It writes these program messages of protocol 12: `reply`, `page`, `subpages`, `index`, `redirect`, `sound`, `cookie`, `author_log`, `log`, `packets`, `denied`, `description`. Of the schema's eighteen program messages it never writes `measure`, `regis`, `regis_links`, `regis_cursor` or `naplps`.

Of the `sound` message's 51 kinds in protocol 12 it writes three: `object` (16-bit samples, which the server encodes as IMA ADPCM; `sound_object`), `play` and `stop`. It has no call for `gain`, for Opus (`opus`, `opus_live`, `opus_packets`), for a live sound of samples (`live`, `blocks`), or for any of the 42 synthesizer kinds (`synth6581`, `synth6581_live`, `synth6581_blocks`, the same three for `synth8580`, and for each of `synth7`, `synth106`, `synth60`, `synthd`, `synth53`, `synth52`, `synth51`, `synth8` and `synth80` its stored sound, live sound, live blocks and bank). It has `sound.py`, which makes 16-bit samples of tones, noise and chimes for `object`.

It hears `start`, `connected`, `selected`, `input`, `left`, `closed`, `stats`, `describe` and `refused`. A `refused` is written to standard error and nothing else happens: no handler is called. It does not hear `measured`.

### 3.2 Types and validation

The kit has no types of the protocol's messages: every message is a `dict[str, Any]` built by hand in the method that sends it. Each method checks its own arguments with literals of its own (`SAMPLE_RATES`, `AUDIO_CHANNELS`, `LAST_HANDLE`, `LAST_GENERATION`, `FULL_GAIN`, `LONGEST_FADE_MS`, `DEEPEST_DUCK`, `MOST_SAMPLES`, through `whole`), which are copies of the schema's bounds. `send` holds every message to `textrules.py`'s `message_fault` (the text rules the schema cannot state: no control or bidirectional formatting character, normalisation form C, a cookie's fields in bytes, an author's log line in bytes) and writes it with `json.dumps(message, ensure_ascii=False, separators=(",", ":"))`. Nothing validates a message against the schema at run time (DEC-1543 item 5).

The schema copy is `protocol-12.json`, byte for byte the server's `protocol/schema-12.json` at commit `df662b9`, which `scripts/check.sh` names as `SCHEMA_FROM` and checks in the commit gate (`check_schema_copy`). The kit's tests (`test_kit.py`) collect every message their channels sent and, at the end, check them against the schema with `jsonschema==4.25.1`, run by `uvx` in a process of its own (`testing.py`, `schema_faults`), so the kit itself has no dependency (`pyproject.toml`, `dependencies = []`).

### 3.3 Protocol version

`PROTOCOL = 12`. On a `start` of another version, `_start` writes a line to standard error and goes on (`report(f"protocol {…}, this kit speaks {PROTOCOL}")`): it does not stop. The TypeScript kit stops.

### 3.4 Sessions and tabs

The kit presents the server's session to the program: `_open` and `_leave` skip `on_open` and `on_leave` when another connection of the same session is on the page (`_other_on`); `session_hears` and `Hearer(session=…)` send a session's sound to every one of its tabs; `publish(owner=session)` sends a session's own copy to every tab of the session. This is TODO-6445.

### 3.5 Testing

`testing.py` offers `schema_faults` and `start_message` only. The helpers that drive the kit in its tests (`Recorder`, `run`, `connected`, `selected`, `event`, `key`, `started`) live in `tests/test_kit.py`, not in the kit, so a channel's tests cannot use them. The TypeScript kit's `testing` module has a `Harness` (join, open, close, press, type, click, the wheel, a clock, and `sounds(session)` among what it reads back).

### 3.6 Gaps against the TypeScript kit

| # | Gap | Closed by this work |
|---|---|---|
| 1 | 48 of the `sound` message's 51 kinds of protocol 12, and every sound kind protocol 13 adds or reshapes | Yes (PY-51) |
| 2 | `measure` and `measured` | Yes (PY-52) |
| 3 | `regis`, `regis_links`, `regis_cursor`, `naplps` | Yes (PY-53) |
| 4 | A `refused` reaches no handler | Yes (PY-24) |
| 5 | No types of the messages | Yes (PY-7 to PY-17) |
| 6 | No validation against the schema at run time | Yes (PY-35; DEC-6474) |
| 7 | A `start` of another version does not stop the program | Yes (PY-5) |
| 8 | Tabs of one session coupled (TODO-6445) | Yes (PY-55) |
| 9 | No harness a channel's tests can use | Yes (PY-43) |
| 10 | No Opus encoder (the TypeScript kit encodes with `ffmpeg`, `ffmpeg-opus.ts`) | No: section 6 item 1 and PY-58 |

---

## 4. Requirements

### 4.1 Taking the server's schema

**PY-1. The schema copy.** The kit MUST carry exactly one copy of the protocol's schema, `kits/python/src/neoteletext_app/protocol-13.json`, byte for byte the server's `protocol/schema-13.json` at one commit of neoteletext-app-server. `protocol-12.json` MUST be deleted in the same change.
- Reason: The schema is the contract (DEC-6462 item 2, DEC-1482 item 7); a kit that holds one exact copy checks what the server checks. One copy, because two versions in one kit would be a compatibility shim (DEVELOPMENT.md section 2.1).
- Source: DEC-6462 items 2 and 3; REQ-2771; `scripts/check.sh` as built (`SCHEMA_COPY`).
- Verification: The commit gate's check of PY-2; inspection that no other schema file is in the kit.

**PY-2. The copy is pinned and checked.** `scripts/check.sh` MUST name, as `SCHEMA_FROM`, the full 40-character commit of neoteletext-app-server the copy was taken from, and as `SCHEMA_COPY` the copy's path; its commit gate step MUST fail, naming both, when the server's repository is not at `$NEOTELETEXT_SERVER` (default `~/devel/neoteletext-app-server`), when that commit has no `protocol/schema-13.json`, or when the copy differs from it by one byte. The step MUST read the server's file with `git show SCHEMA_FROM:protocol/schema-13.json` and compare with `cmp`, as `check_schema_copy` does today, with only the version in the file name changed. A new schema MUST be taken by copying the file and changing `SCHEMA_FROM` in the same commit, and by nothing else.
- Reason: The way the copy is checked today works and is the TypeScript kit's too (`schema()` in its `scripts/check.sh`); the brief asks that protocol 13 be taken exactly as protocol 12 is.
- Source: `scripts/check.sh` (`SCHEMA_FROM`, `check_schema_copy`); DEVELOPMENT.md section 9.2 (nothing skipped silently: a missing server repository fails the step).
- Verification: The gate run with the copy changed by one byte fails naming the file; run with `SCHEMA_FROM` naming a commit without `schema-13.json` fails naming it; run with the server's repository absent fails naming `NEOTELETEXT_SERVER`.

**PY-3. The TypeScript kit names the same commit.** Each release of the kit that changes `SCHEMA_FROM` MUST name the same server commit as the TypeScript kit's release of the same protocol change, and the commit message MUST name that TypeScript release.
- Reason: The kits are equals (DEC-6462 item 3): two kits on two schema commits of one protocol version could accept different messages.
- Source: DEC-6462 item 3.
- Verification: Review of each commit that changes `SCHEMA_FROM` against the TypeScript kit's `scripts/check.sh` at the release named.

**PY-4. The protocol constant.** The kit's `PROTOCOL` MUST be 13, and MUST equal the `const` of the schema copy's `start.protocol` field; the generated module (PY-8) MUST carry that `const`, and `app.py` MUST take `PROTOCOL` from the generated module, never as a literal of its own.
- Reason: One constant, defined once (DEVELOPMENT.md section 6); the schema states the version (`#[schemars(extend("const" = PROTOCOL))]` in `protocol.rs`).
- Source: `protocol.rs` (`PROTOCOL`, the `start` message's `protocol` field); MIDI-111.
- Verification: A kit test checks `PROTOCOL == 13` and that it is the schema copy's `const`; a search of `app.py` finds no literal 13.

**PY-5. A program of another version stops.** On a `start` whose `protocol` is not `PROTOCOL`, the kit MUST write one line to standard error naming both versions (`protocol 12 from the server; this kit speaks 13`) and MUST end the program with exit status 1, calling no handler and writing no message.
- Reason: MIDI-111: "a program of version 12 then stops at `start`, naming both versions"; the TypeScript kit stops; a program that goes on would have every message refused.
- Source: MIDI-111; `app.py` (`_start`, which today only reports); the TypeScript kit's `streams.ts`.
- Verification: A kit test feeds `start` with `protocol` 12 and with 14 and checks the exit status, the line and that nothing was written; it fails on the kit of today, which goes on.

**PY-6. Every message read is checked.** The kit MUST validate every line it reads from the server against the schema's `ServerMessage` (PY-35's validator) before acting on it, and MUST report a line that fails and act on nothing in it, as the TypeScript kit does ("A line from the server that is not valid is reported and never acted on", DOC-2317).
- Reason: A message from the server is input; the kits are equal.
- Source: DOC-2317; DEC-6462 item 3.
- Verification: A kit test feeds a `connected` with an unknown field and checks it is reported and no handler is called.

### 4.2 The Python types, generated from the schema

The choice and its reasons are in PY-7; open question 3 records the alternatives, and DEC-6474 item 3 chose generation.

**PY-7. Types are generated, not written by hand.** The kit's types of every protocol message MUST be generated from the schema copy by a generator of the kit's own, `kits/python/scripts/generate_types.py`, written with Python's standard library only (`json`, `keyword`, `re`, `sys`, `pathlib`), checked by the repository's `ruff` and `mypy` like the kit's own source, and run with `uv run --frozen python kits/python/scripts/generate_types.py`. No library and no tool outside the repository's `uv.lock` MUST be used to generate them.
- Reason: Protocol 13's sound messages are large: eleven kinds, each with stored, live and events messages, banks, two patch forms per family, and named patch fields counted in hundreds (synth7's 155 voice parameters alone, `synth7.md` section 7). Hand-written types of that size drift from the schema, and the brief requires generated types or hand-written ones checked against the schema. A generator of the kit's own adds no library, which DEVELOPMENT.md section 7 would require the owner to approve by name, and is small because `schemars` emits a small, fixed set of JSON Schema constructs (PY-9). A third-party generator run by `uvx` (for example `datamodel-code-generator`) would be a tool to approve and pin, emits code whose shape the kit does not control, and is designed around run-time model libraries the kit does not use.
- Source: DEC-6462 items 2 and 3 ("types generated from, or checked against, the server's schema"); MIDI-22; DEVELOPMENT.md sections 7 and 13.
- Verification: Inspection of the generator's imports; the commit gate of PY-14.

**PY-8. TypedDicts, not dataclasses.** The generated module, `kits/python/src/neoteletext_app/protocol_types.py`, MUST describe each JSON object of the schema as a `typing.TypedDict` whose keys are the wire's field names exactly, each closed set of strings as `typing.Literal`, and each union as a type alias of the union of its members. It MUST contain no function, no class other than `TypedDict` classes, and no value other than the constants of PY-11; it MUST begin with a comment naming the schema copy and its SHA-256 and saying it is generated and never edited.
- Reason: A `TypedDict` is a `dict` when the program runs, so a message the program builds is the JSON object the server reads: the kit writes it with `json.dumps` and validates it with `jsonschema` with no conversion, no renaming layer and no code that could disagree with the schema. The wire's names are already Python's style (`snake_case`), so the wire's names are the Pythonic names. A dataclass would need conversion code both ways, which is logic in a thin kit.
- Source: DEC-6462 item 3 (the kits hold types and calls only); the schema's field names (`fade_ms`, `packet_bytes`, `named_connections`).
- Verification: A kit test imports the generated module and checks that every `ProgramMessage` and `ServerMessage` member of the schema has one class; inspection of the module.

**PY-9. How each schema construct becomes a Python type.** The generator MUST translate exactly these constructs, which are every construct `schemars` emits in the protocol's schema (counted in `schema-12.json`: `description`, `type`, `format`, `minimum`, `maximum`, `const`, `$ref`, `properties`, `required`, `additionalProperties`, `maxLength`, `minLength`, `items`, `maxItems`, `minItems`, `anyOf`, `oneOf`, `enum`, `pattern`, `default`, `$defs`, `$schema`, `title`) and the two `schema-13.json` adds (`contentEncoding`, SRV-6, and `allOf`, for SRV-3's named types under a tagged enum), exactly the keywords `typescript.md` TS-9 maps, as this table says; and MUST stop with an error naming the construct and its JSON pointer when the schema holds any other, writing nothing:

| Schema construct | Python type |
|---|---|
| `"type": "object"` with `properties` | A `TypedDict` class; each property one key |
| A property in `required` | `Key: T` |
| A property not in `required` | `Key: NotRequired[T]` |
| `"type": "string"` | `str` |
| `"type": "string"` with `"contentEncoding": "base64"` | `bytes` (PY-13), which `server.md` writes on every bytes field (SRV-6) |
| `"type": "integer"`, with any `format` (`uint8`, `uint16`, `uint32`, `uint64`, `int16`, `int32`) | `int` |
| `"type": "boolean"` | `bool` |
| `"type": "array"` with `items` | `list[T]` |
| `"type": [T, "null"]` | `T \| None` |
| `"const": "x"` | `Literal["x"]` |
| `"const"` of an integer | `Literal[n]` |
| `"enum": [...]` of strings or integers | `Literal[...]` of the values, in the schema's order |
| `"$ref": "#/$defs/Name"` | The class or alias `Name` |
| `"anyOf": [A, {"type": "null"}]` | `A \| None` |
| `"anyOf"` or `"oneOf"` of other members | A type alias of the union of the members' types |
| A `oneOf` or `anyOf` member that is an object with a string `const` in a property named `type`, `kind`, `event` or `form` (the tag of a tagged union) | A class named by PY-10 rule 2 (`Sound` and `synth7_bank` give `SoundSynth7Bank`) |
| `allOf` of a `$ref` and an object (what `schemars` writes for a tagged enum's variant that is a named type) | One `TypedDict` class holding the referenced class's keys and the object's, by inheritance from the referenced class |
| `minimum`, `maximum`, `minLength`, `maxLength`, `minItems`, `maxItems`, `pattern` | Not a type: written in the key's comment (`# 0 to 255`, `# at most 64 items`, `# pattern ^[0-9A-F]{3}$`); held at run time by validation (PY-35) |
| `description` | The class's docstring, or the key's comment, as the schema words it |
| `default` | Written in the key's comment (`# default 100`); never filled in by the kit |
| `additionalProperties: false` | Nothing more: a `TypedDict` built by a literal is already closed to `mypy` (an extra key is an error), and validation refuses it at run time |
| `$defs`, `$schema`, `title`, the root `anyOf` | Not types: read to find the definitions |

- Reason: A generator that fails on what it does not know cannot silently lose a rule when the server's schema grows; one that knows exactly what `schemars` emits is small. Bounds are not Python types (Python has no ranged integer), so they are shown to the author and enforced by the one validator.
- Source: `schema-12.json` as counted on 18 November 2026; `protocol.rs` (`schema()`, `SchemaSettings`); PEP 589 (`TypedDict`), PEP 655 (`NotRequired`), PEP 586 (`Literal`).
- Verification: A generator test for each row, on a schema of that one construct; a test that a schema with `patternProperties` (one construct `schemars` does not emit here) stops the generator naming it; the generated module type-checks under `mypy --strict`.

**PY-10. Names.** The generated types MUST be named by these rules, which are word for word the same in `typescript.md` TS-10 and `python.md` PY-10, so that a type has one name in both kits:
1. Each definition of the schema's `$defs` MUST be one type under its own name, which is the server's Rust type's name (`Refused`, `Rule`, `Sound`, `Synth7BankSound`, `Synth106Panel`, `Synth106Event`).
2. Each branch of a tagged union, that is of a `oneOf` or `anyOf` whose branches each hold a string `const` in a property named `type`, `kind`, `event` or `form`, MUST be one type, the branch whole with its tag, named the union's name followed by the tag's value in upper camel case: the value's parts between underscores, each with its first letter a capital and the rest as written (`Sound` and `synth7_bank` give `SoundSynth7Bank`; `Sound` and `synthd` give `SoundSynthd`; `ProgramMessage` and `sound` give `ProgramMessageSound`; `Synth106Event` and `note_on` give `Synth106EventNoteOn`; `Synth106Patch` and `fields` give `Synth106PatchFields`).
3. Any other object or union the schema writes inline MUST be named its enclosing type's name followed by its property's name in upper camel case (a union written inline as the property `bank` of `Synth7BankSound` is `Synth7BankSoundBank`).
4. A member type (TS-11, PY-12) MUST be named its branch's name followed by `Member` (`SoundSynth7BankMember`, `SoundPlayMember`, `ProgramMessagePageMember`), and the union of every sound kind's member type MUST be named `SoundMember`.
5. Two types MUST NOT receive one name, and no type's name MAY be a reserved word of TypeScript or of Python: the generator MUST fail, naming both paths or the word, rather than number, rename or drop a type.

A key of a `TypedDict` that is a Python keyword (none is today) MUST use the functional form `TypedDict("Name", {...})`, which allows it; it is not a renaming, and the wire's key is unchanged.
- Reason: The names are the schema's, so the server document's names are the program's names; a silent rename would make a Python program differ from the documentation. One rule in both kits gives every type one name in both (DEC-6462 item 3; DEC-6477).
- Source: PEP 589 (the functional form for keys that are not identifiers); SRV-3; `typescript.md` TS-10; DEC-6477.
- Verification: Generator tests for each rule, from the same table of schemas and names as `typescript.md` TS-10's tests; tests for a clash, for a reserved word and for a keyword key.

**PY-11. The constants the schema states.** The generated module MUST carry, as `Final` constants, the protocol version (`PROTOCOL: Final = 13`, from `start.protocol`'s `const`) and nothing else; every other bound stays in the schema and in what `start` gives (REQ-5207).
- Reason: A kit holds no limit of its own (REQ-5207); the version is the one figure the kit itself acts on (PY-5).
- Source: REQ-5207; PY-4.
- Verification: Inspection of the generated module; the kit test of PY-4.

**PY-12. Member types.** For every program message that has a `connections` field (`page`, `subpages`, `index`, `sound`, `author_log`, `packets`, `regis`, `regis_links`, `regis_cursor`, `naplps`, and any `server.md` adds), the generator MUST also emit a member type: the same `TypedDict` without `connections` and, for a `sound` message, without `type`, named by PY-10 rule 4 (`SoundSynth7BankMember`, `SoundPlayMember`), and a union alias `SoundMember` of every sound member type. A program MUST build only member types; the kit adds `type` and `connections` (PY-20).
- Reason: Who a message is for is the kit's to fill from a hearer, chunked by `start`'s `named_connections` as today (`_chunks`); the program says what, not to which connection numbers. The TypeScript kit's `sound(to, member)` takes the same split (`members.ts`, `Audience` and `SoundMember`).
- Source: `app.py` (`_audience`, `_chunks`, `_sound`); `members.ts`.
- Verification: A kit test that a member type built with `connections` is a `mypy` error (a test file checked by `mypy` with an expected error); a test that `sound` fills `connections`.

**PY-13. Bytes are bytes.** Every field the schema marks `"contentEncoding": "base64"` MUST be `bytes` in the generated types; the kit MUST write every `bytes` value of a message as its exact base64 text (RFC 4648 section 4, with padding, no line breaks) when it writes the line, by `json.dumps`'s `default`, and MUST NOT encode any other value. The server's schema marks every such field (SRV-6; DEC-6477), where protocol 12's said "exact base64" only in a field's description (`OpusSound.packets`, `ObjectSound.pcm`); `bytes` MUST NOT be guessed from a description, and a field the schema does not mark is typed as its schema type says.
- Reason: A patch's system exclusive bytes, raw MIDI bytes and a Standard MIDI File's bytes (MIDI-14, MIDI-16, MIDI-112) are bytes to a Python program; a program that had to write base64 itself would carry a step of the wire in every program. One rule, applied to every `bytes` value at the one place the kit writes a line, is not instrument logic and needs no knowledge of which field is which.
- Source: MIDI-14, MIDI-16, MIDI-112; SRV-6; DEC-6477; JSON Schema 2020-12 Validation, section 8.3 (`contentEncoding`); RFC 4648 section 4.
- Verification: A kit test sends a synth7 patch given as `bytes` and checks the line carries the exact base64 of the bytes; a `mypy` test file checks that `bytes` given for a field the generated types make `str` is a type error.

**PY-14. The generated module is committed and checked.** The generated module MUST be committed. The commit gate MUST run the generator into the session's temporary folder and fail, naming the module, when its output differs from the committed module by one byte; the step MUST run after PY-2's schema check.
- Reason: Committed, the module is read by `mypy` in every channel and by a reader with no build step (the uv workspace installs the kit from its source); checked, it can never be other than what the schema gives. The TypeScript kit's validators are built and not committed because its release is a build; the Python kit has none.
- Source: DEVELOPMENT.md section 9.2; `scripts/check.sh` (`commit_steps`).
- Verification: The gate run with the committed module edited by one character fails naming it; run after a schema change without regeneration fails.

**PY-15. Programs are type-checked.** The kit and every Python channel in the repository MUST pass `mypy --strict` (the repository's `[tool.mypy] strict = true`) with the generated types, so that a misspelt key, a missing required key, an extra key in a literal, a string outside a `Literal` and a member of the wrong union are each errors before the program runs.
- Reason: Static types are what the generated module is for; the repository already runs `mypy` strictly in the commit gate (`check_python`).
- Source: `pyproject.toml` (`[tool.mypy]`); `scripts/check.sh` (`check_python`).
- Verification: A kit test file of deliberate mistakes, one for each kind named, checked by `mypy` with each expected error asserted (`# type: ignore[typeddict-unknown-key]` and its kin, with `warn_unused_ignores`, so a mistake that stops being an error fails).

**PY-16. No hand-written message type.** The kit MUST NOT define any type, constant or check of a protocol message other than the generated ones; every hand-written `dict[str, Any]` message builder of today (`_sound`, `play`, `stop`, `sound_object`, `packets`, `_page`, `_list`, `_redirect`, and the rest of section 3.1) MUST build a generated type, and the literals of section 3.2 that copy the schema's bounds (`SAMPLE_RATES`, `AUDIO_CHANNELS`, `LAST_HANDLE`, `LAST_GENERATION`, `FULL_GAIN`, `LONGEST_FADE_MS`, `DEEPEST_DUCK`, `MOST_SAMPLES`, `PACKET_BYTES` and `whole` where it checks them) MUST be removed.
- Reason: Copies of the schema's bounds are copies of server rules (MIDI-22), and REQ-5207 forbids a kit's own limits.
- Source: MIDI-22; REQ-5207; DEC-6462 item 3.
- Verification: A kit test, like the TypeScript kit's `no-limits.test.ts`, searches the kit's source for the removed names and for integer literals equal to a schema bound outside the generated module, and fails on each.

**PY-17. Types of what the server sends.** The handlers of PY-23 to PY-26 MUST receive the generated wire types of the server's messages (`Refused`, `Measured` and every report `server.md` defines), validated by PY-6, never a `dict[str, Any]`.
- Reason: The program reads the server's answers by the same contract it writes its messages by.
- Source: DEC-6462 item 2.
- Verification: `mypy` over the kit's handlers; a test that a handler receives the validated message.

### 4.3 The calls a program makes

**PY-18. The Python kit's calls are the TypeScript kit's.** The kit's public calls and handlers for every protocol-13 message MUST be exactly the TypeScript kit's, each named as the TypeScript kit names it with `lowerCamelCase` turned into `snake_case` and, for a handler, `on_` before it (`regisLinks` is `regis_links`, the handler `stateRefused` is `on_state_refused`, `opened` is `on_opened`, `leftPage` is `on_left_page`), the TypeScript handlers' trailing `context` argument having no Python counterpart (the Python handler is a method of the `App`), taking the same arguments in the same order (Python keyword-only arguments for the TypeScript kit's options objects), with the same meaning; neither kit MUST have a call the other lacks. Where the two kits differ in structure (an `App` subclass with handlers in Python, applications and a context in TypeScript), the calls MUST still correspond one to one. Every call, handler, audience and harness call of both kits is a row of `docs/audio/kit-calls.tsv` (PY-19), and the names this document gives in PY-20 to PY-50 are that file's.
- Reason: DEC-6462 item 3: "The TypeScript and Python kits are equals; neither can do what the other cannot"; VS-401 asks the same for the viewer calls. Equal names make every guide and example read the same in either language.
- Source: DEC-6462 item 3; VS-401.
- Verification: PY-19's check.

**PY-19. One call list, checked by both kits.** neoteletext-common MUST keep `docs/audio/kit-calls.tsv`: after its comment lines (each beginning `#`), a header row and one row a call, handler, audience or harness call, of five tab-separated columns, `what` (`call`, `handler`, `audience` or `harness`), `typescript` (the TypeScript kit's name), `python` (the Python kit's name), `message` (the protocol message it writes or reads, or `-`) and `arguments` (its arguments in order, by meaning, separated by commas), as `typescript.md` TS-2 describes it. Each kit's commit gate MUST check its own public interface against the file: the Python kit's by importing `neoteletext_app` and listing `App`'s public methods and the `testing` module's public names (with `inspect`), the TypeScript kit's as `typescript.md` says; a call or handler missing from the file, in the file and missing from the kit, or with other arguments, MUST fail the gate. Each kit MUST copy the file byte for byte and pin it by the neoteletext-common commit, `COMMON_FROM` in its `scripts/check.sh`, checked by its commit gate as it checks the schema (PY-2).
- Reason: Equality that is not checked drifts; the file is how neoteletext-common already holds values both sides must share (`wire-vectors.tsv`).
- Source: DEC-6462 item 3; `wire-vectors.tsv` as the example.
- Verification: The gate run with one method added to `App` fails naming it; run with one row removed from the copy fails naming the call.

**PY-20. `sound`: the one call for every sound.** `App.sound(to: Hearer, member: SoundMember) -> None` MUST write one `sound` message for each chunk of the hearer's connections (at most `start`'s `budgets.named_connections` each, as `_chunks` does today), each the member with `"type": "sound"` and `connections` added, validated (PY-35) before the first is written; it MUST write nothing for a hearer with no connection. It MUST take every sound member the schema has, of every kind: stored sounds, live sounds and their events, banks, play, stop and gain, of the eleven synthesizers and of samples and Opus, so that a program can send every message `server.md` defines for sounds through it. It MUST NOT change, add to, reorder or remove anything of the member but `type` and `connections`, except to encode `bytes` (PY-13). The kit's guide MUST say, where it describes sending a page's sounds, that a program sends a connection a page's play once, when the connection opens the page, and never again while it stays on the page, since a new play starts its sound again (`integration.md` INT-28).
- Reason: The thinnest call there is (DEC-6462 item 3): the program builds the typed message, the kit addresses and writes it. It is the TypeScript kit's `sound(to, member)` (`context.ts`). Every kind through one call means a kind `server.md` adds needs a new schema copy and nothing more in the kit.
- Source: DEC-6462 items 1 and 3; `context.ts` (`sound`); `app.py` (`_sound`, `_audience`, `_chunks`).
- Verification: A kit test sends one valid member of every sound kind of the schema copy (generated from the schema's own examples where `server.md` gives them, PY-48) and checks each line is the member with `type` and `connections` added and nothing else; a test with `named_connections` of 2 and five connections checks three lines.

**PY-21. Hearers.** A hearer MUST be one of: `connection_hears(connection)` (one connection), `page_hears(page)` (every connection whose selection is on the page now), `connections_hear(connections)` (a list of connection numbers) and `everyone_hears()` (`"connections": "all"`). `session_hears` and `Hearer(session=…)` MUST be removed (PY-55). The set MUST be the TypeScript kit's `Audience` in protocol 13, by PY-18.
- Reason: Under protocol 13 there is no server session (VS-354), and each tab is a connection of its own (DEC-6443, VS-403); a viewer's tabs together are found through the viewer handle, which the program keeps (VS-401).
- Source: VS-354; VS-403; `members.ts` (`Audience`).
- Verification: Kit tests of each hearer's connections; the call list check (PY-19).

**PY-22. Viewer calls.** The kit MUST offer the viewer calls and handlers `viewer-state.md` specifies for the Python kit (VS-401: `request_state`, `end_state`, `offer_remember`, `on_viewer_began`, `on_viewer_left`, `on_state_refused`, `on_viewers_reset`, and the connection's `viewer` and whether it is remembered), as that document specifies them, and MUST remove every cookie call (VS-402).
- Reason: Protocol 13 is one protocol; a kit that took the sound messages and not the viewer messages could not speak it.
- Source: VS-401, VS-402, VS-403.
- Verification: As VS-401 to VS-403 say; the call list check.

**PY-23. Handlers of a connection's life.** The kit MUST call `on_opened(connection, page)` for every connection whose selection comes to a page and `on_left_page(connection, page)` for every connection that leaves one, whatever other connections of the same viewer do, and `on_gone(connection)` when the server says `gone` (VS-351 item 6), in place of `on_close(session)`; `on_join` MUST become `on_joined(connection)`, called once for each `connected`; `on_open` and `on_leave` are renamed to `on_opened` and `on_left_page`. The names are the TypeScript kit's (`joined`, `opened`, `leftPage`, `gone`) by PY-18, as `docs/audio/kit-calls.tsv` lists them.
- Reason: TODO-6445 item 1 and VS-403: each connection is its own unit to applications, and its state ends at `gone`.
- Source: TODO-6445; VS-351 item 6; VS-403; `app.py` (`_open`, `_leave`, `_other_on`, `_closed`).
- Verification: TODO-6445's tests: two connections of one viewer on one page are each opened, and each closes at its own `gone`; a sound sent to one connection reaches it alone; each fails on the kit of today.

**PY-24. `on_refused`.** When the server sends `refused`, the kit MUST call `on_refused(refusal: Refused)` with the validated message, whose fields (the message's type, the path, the rule, the detail, and, for a refused sound, `sound`, naming its kind, handle and generation, SRV-48) are the schema's; the default handler MUST write one line to standard error, as the kit does today, and nothing else. A refusal that answers a `measure` MUST instead fail that measure's awaitable (PY-29) and MUST NOT reach `on_refused`.
- Reason: Under DEC-6462 the server's typed refusal is how a program learns of every fault the schema cannot state (MIDI-21; S6581-54: "a program learns of a fault from the server's typed refusal"), so a program must be able to act on it; today it is only printed.
- Source: MIDI-21; S6581-54; `app.py` (`_about_no_viewer`); `measures.ts` in the TypeScript kit (a refusal that answers a measurement rejects it).
- Verification: A kit test feeds a `refused` of a sound and checks `on_refused` receives it typed; a test that a refusal of a measurement fails its awaitable and does not reach `on_refused`; the first fails on the kit of today.

**PY-25. Reports of sounds.** For every message `server.md` defines that the server sends a program about a sound (today one, `sound_built`, SRV-47, which names the sound and carries the counts of a Standard MIDI File's dropped messages, MIDI-118), the kit MUST call one handler `on_<message type>` (`on_sound_built`, the TypeScript kit's `soundBuilt`) with the validated message, whose default does nothing; it MUST NOT interpret the report.
- Reason: The report is the server's (MIDI-118: the server "MUST report to the program, in its answer, how many of each kind it dropped"); the kit passes it on.
- Source: MIDI-118; SRV-47; DEC-6462 item 3; `typescript.md` TS-23.
- Verification: A kit test for each such message `server.md` defines: fed to the kit, it reaches its handler unchanged.

**PY-26. Every server message reaches a handler or the kit's own work.** Every member of the schema's `ServerMessage` MUST be either acted on by the kit itself (`start`, `connected`, `selected`, `input`, `left`, `gone`, `describe`, `measured`) or passed to a handler; the kit MUST NOT write "passed over a message of type" for any type the schema lists.
- Reason: A message the kit drops is a capability the program lacks; the TypeScript kit acts on every message it reads.
- Source: `app.py` (`_about_no_viewer`'s last branch); DEC-6462 item 3.
- Verification: A kit test feeds one valid message of every `ServerMessage` type of the schema copy and checks none is passed over.

**PY-27. `regis`, `regis_links`, `regis_cursor`, `naplps`.** The kit MUST offer `regis(to, page, sub, data: str | bytes, *, restart: bool = False)`, `regis_links(to, page, sub, links: list[DrawingLink])`, `regis_cursor(to, page, sub, drawing: int)` and `naplps(to, page, sub, data: bytes, *, restart: bool = False)`, each writing its one message for each chunk of the hearer's connections, with the page and sub-code written as the schema writes them (three and four hexadecimal digits, as `page_text` and `sub_text` write them today), and nothing else. They are the TypeScript kit's `regis`, `regisLinks`, `regisCursor` and `naplps` (`context.ts`).
- Reason: The kits are equals (DEC-6462 item 3); each is one thin call.
- Source: `context.ts`; the schema's `regis`, `regis_links`, `regis_cursor` and `naplps` messages.
- Verification: A kit test for each call checks the line; the call list check.

**PY-28. No instrument logic.** The kit MUST NOT contain any of: a patch packer or unpacker, a table of any family's parameters or controllers, a block, record or bank builder, a reader of Standard MIDI Files or of system exclusive, a converter of times to ticks or blocks, a restatement, a program-change repeater, a check of a synthesizer message beyond the schema, or a default patch. A program that wants a family's default patch, its parameter names or its controller numbers MUST read them from the schema's types and descriptions or from the family document.
- Reason: DEC-6462 item 3 and MIDI-22 name exactly these; the TypeScript kit's 4,300 lines of them are what DEC-6462 removes, and the Python kit must not gain them.
- Source: DEC-6462 item 3; MIDI-22; MIDI-112.
- Verification: Review of every change to the kit against this list; PY-16's search.

**PY-29. `measure`.** The kit MUST offer `async def measure(page: int, screen: Screen) -> Measured`, which writes a `measure` message with a request number of the kit's own (1 upwards, bounded as the schema bounds it) and returns when the server answers with the `measured` of that number, or raises `MeasureRefused` carrying the `Refused` when the server refuses it. It is the TypeScript kit's `measure` (`context.ts`).
- Reason: The kits are equals; a Python channel's tests can then measure every page against a running server, as DOC-2317 says of the TypeScript kit.
- Source: DOC-2317; `context.ts`, `measures.ts`; REQ-2216.
- Verification: Kit tests with the harness answering a measurement and refusing one.

**PY-30. Time is the program's.** The kit MUST NOT keep a sound's clock, number a block, or turn a time into anything: every time in a sound member is whole microseconds as MIDI-17 states, and the program computes it (for a live sound, from its own clock, for example `time.monotonic_ns() // 1_000` less the live sound's start).
- Reason: MIDI-17 and MIDI-20 put times in microseconds in the program's message and blocks in the server; the kit is thin.
- Source: MIDI-17, MIDI-20; DEC-6462 item 3.
- Verification: Review; PY-28.

**PY-31. The calls of today that go.** `sound_object`, `play` and `stop` MUST be removed: a program sends those messages with `sound` (PY-20) and the generated member types `SoundObjectMember`, `SoundPlayMember` and `SoundStopMember`. `sound.py` (tones, noise and chimes as 16-bit samples) MUST stay: it makes samples, not messages, and is not instrument logic of a synthesizer.
- Reason: Three hand-written builders with their own copies of the schema's bounds (PY-16) for three of the sound kinds would leave the kit unequal to itself; one call for all is what the TypeScript kit has (`sound(to, member)`). No alias is kept (DEVELOPMENT.md section 2.1).
- Source: PY-16; PY-20; `app.py` (`sound_object`, `play`, `stop`).
- Verification: The call list check; the Hackaday channel's tests after PY-62.

**PY-32. Errors a call raises.** A call MUST raise `ProtocolError` (a subclass of `ValueError`) carrying the fault of PY-37 when validation fails, and MUST write nothing of the message to any connection; it MUST raise `RuntimeError` when called before `start`. It MUST NOT raise for anything the server would refuse that the schema does not state: that comes back as a refusal (PY-24).
- Reason: The TypeScript kit's `ProtocolError` (`validate.ts`); a mistake the schema can see is caught where it is made, and every other one is the server's to say.
- Source: `validate.ts`; DEC-6462 item 2.
- Verification: Kit tests: a member with a value past its schema bound raises with the server's path and rule and nothing is written; a member the schema accepts and the server would refuse (for example a synth7 bank whose checksum is wrong) is written.

**PY-33. Synchronous writing, asynchronous reading.** `sound` and the other writing calls MUST be ordinary methods that write their lines before they return, callable from any handler or from a task the program starts (as `publish` is today), and MUST write lines in the order the calls were made.
- Reason: A live sound's events messages must reach the server in order (MIDI-20); the kit's writing is synchronous today.
- Source: `app.py` (`send`, `write`).
- Verification: A kit test with a live sound's events sent from two tasks checks the lines' order.

**PY-34. No call makes a program wait on the server for a sound.** No sound call MUST wait for the server's answer; a program that needs to know a sound was accepted reads the reports and refusals of PY-24 and PY-25, and matches them by the sound they name: a refusal's `sound` (SRV-48) and `sound_built`'s `kind`, `handle` and `generation` (SRV-47).
- Reason: The server answers a sound only with a refusal or a report; a call that waited would stall a live sound's feeding. DEC-6477 keeps sound calls unanswered and has every refusal and report name the sound, in both kits (`typescript.md` TS-24).
- Source: MIDI-20; SRV-47, SRV-48; DEC-6477; `typescript.md` TS-24.
- Verification: Review; the live keyboard example (section 5.2) runs in the harness with no answer given.

### 4.4 Validation

**PY-35. Every message is validated against the schema before it is written.** The kit MUST validate every message it is about to write, after adding `type` and `connections` and after encoding `bytes` (PY-13), against the schema copy's definition of that message (the `ProgramMessage` member whose `type` it has, as the TypeScript kit validates against each member separately, `scripts/validators.ts`), with `jsonschema`'s `Draft202012Validator`, version 4.25.1, built once per message type when `start` is read. A message with any fault MUST NOT be written. This makes `jsonschema` 4.25.1 (MIT) and the packages it requires, `attrs`, `jsonschema-specifications`, `referencing` and `rpds-py` (each MIT; `rpds-py` holds compiled Rust code), run-time dependencies of the kit, approved by the owner by name (DEC-6474; DEVELOPMENT.md section 7); each MUST be pinned to an exact version in `pyproject.toml` and `uv.lock` with its licence and reason, and any further package they turn out to require MUST NOT be added before the owner approves it by name.
- Reason: The brief: "validation (the schema only, via the jsonschema the kit's tests already use)". A program's mistake is then refused where it is made, with the server's path and rule, as the TypeScript kit does with Ajv (REQ-2769), and the kits are equal. `jsonschema` is the validator the kit's tests already run (`testing.py`, `JSONSCHEMA = "jsonschema==4.25.1"`), so the kit and its tests check with one validator; a validator written in the kit (compiling the schema as Ajv's standalone mode does) would be a second implementation of JSON Schema to keep correct.
- Source: The brief; REQ-2769; `testing.py`; `validate.ts`; DEVELOPMENT.md section 7; DEC-6474 item 1.
- Verification: Kit tests: one invalid form of every program message type is refused before writing; `uv.lock` pins `jsonschema` 4.25.1 and its dependencies; the licences of all five are recorded in the kit's project file.

**PY-36. Validation in the kit's tests stays.** The kit's tests MUST still check every message their channels sent against the schema with `jsonschema` 4.25.1 at the end of the run (`schema_faults`), and the harness (PY-43) MUST check every line a program writes as it is written. Both MUST use the same validator, the kit's run-time dependency of PY-35, in place of today's run through `uvx`.
- Reason: Validation in tests is what holds the kit to the schema whatever the run-time choice.
- Source: `testing.py`; `test_kit.py` (`test_every_message_sent_is_one_the_server_takes`).
- Verification: The test exists and finds a fault in a deliberately invalid message, as today.

**PY-37. A fault as the server says it.** A validation fault MUST be reported as the server reports a refusal: the path of the first fault in the server's form (`music.events[3].time_us`, from JSON Pointer `/music/events/3/time_us`, as the TypeScript kit's `pathOf` writes it), a rule from the schema's `Rule` list mapped from the failing JSON Schema keyword exactly as the TypeScript kit maps it (`additionalProperties` to `unknown_field`, `required` to `missing_field`, `type`, `pattern` and `format` to `wrong_type`, `const`, `enum`, `oneOf` and `anyOf` to `not_listed`, `minimum` and `maximum` to `out_of_range`, `maxLength` and `maxItems` to `too_long`, `minLength` and `minItems` to `too_short`), the deepest fault chosen where several are found and a keyword that says only that no member of a union fitted put after a more telling one at the same depth, and a detail in words.
- Reason: One wording of a fault in both kits and the server (REQ-2769: "the same path and the same rule that the server would report"); the mapping is the TypeScript kit's (`validate.ts`, `RULES`, `first`), which is the schema's own `Rule` list.
- Source: `validate.ts`; the schema's `$defs/Rule`; REQ-2769.
- Verification: A shared test table, the same rows run in both kits, of invalid messages and the path and rule each must give; each row also sent to the server in the server's tests, which must give the same path and rule.

**PY-38. The schema only.** For the sound messages of protocol 13, the kit MUST hold no rule beyond the schema: no range, length, checksum, order, count or cross-field rule of a synthesizer message, whatever `server.md` or a family document says the server checks.
- Reason: DEC-6462 item 3 ("no copies of the server's rules beyond what the schema gives"); MIDI-22; S6581-54 ("A kit MUST NOT hold its own copy of these rules beyond what the server's generated schema states").
- Source: DEC-6462 item 3; MIDI-22; S6581-54; S53-47.
- Verification: Review; a kit test sends a synth6581 stored sound whose first update is not a full register update (S6581-54 item 8, a rule the schema cannot state) and checks it is written, and that the harness's refusal of it reaches `on_refused`.

**PY-39. The line's length.** After validation the kit MUST measure the line's length in bytes of UTF-8 and, when it is over `start`'s `budgets.line_bytes`, raise `ProtocolError` with the rule `line_too_long` and write nothing, as the TypeScript kit does (`app.ts`, `send`).
- Reason: The schema cannot state a line's length; the TypeScript kit checks it, and it is a limit `start` gives (REQ-5207), not a copy of a rule; a Standard MIDI File of 1,048,576 bytes (MIDI-119) is about 1.4 MB as base64 and fits 16 MiB, but a program can build a longer line.
- Source: `app.ts` (`send`); MIDI-122 (the longest line, 16 MiB); REQ-5207.
- Verification: A kit test with `line_bytes` lowered in `start` refuses a line one byte over it.

**PY-40. Text rules stay as they are.** `textrules.py`'s rules for text (control and bidirectional formatting characters, normalisation form C, the author's log line in bytes) MUST stay and MUST apply to the text fields of every message as today; its cookie rules MUST go with the cookie (VS-402). No text rule MUST be added for sound messages.
- Reason: These rules are older than DEC-6462, apply to text, and are the subject of TODO-1550, which this document does not change; the sound messages carry no free text the schema leaves unbounded.
- Source: `textrules.py`; TODO-1550; VS-402.
- Verification: The kit's existing text-rule tests; inspection.

**PY-41. Validation work is bounded.** Validating one message MUST take work proportional to its bytes; the kit MUST build each validator once, never per message.
- Reason: A live sound's events messages are sent many times a second (section 5.2); a validator rebuilt for each would cost more than the message.
- Source: DEVELOPMENT.md section 6.
- Verification: A timed kit test validates 1,000 live events messages of 100 events each and prints the time per message, held under a budget the test states (measured when it is written).

**PY-42. The kit trusts the server's refusal over its own check.** Where the kit's validation passes a message the server then refuses, the kit MUST pass the refusal to the program (PY-24) and MUST NOT retry, alter or resend the message.
- Reason: The server is the authority (DEC-6462 item 2); a kit that second-guessed it would be a second implementation.
- Source: DEC-6462 item 2.
- Verification: Review.

### 4.5 The test harness

**PY-43. A harness in the kit.** The kit's `testing` module MUST offer `Harness`, which drives a program (an `App` subclass) as the server does: it says `start` (protocol 13, with the server's budgets, from `start_message`), connects connections and viewers, selects pages, sends input, says `gone`, moves a clock the test controls, and records every line the program writes, each validated against the schema copy as it is written (PY-36), a fault failing the test at once. Its calls MUST be the TypeScript kit's `Harness` calls in `snake_case` (PY-18), including VS-404's viewers (`viewer`, `join`, `private_viewer`, `forget`), and are listed in the call list (PY-19).
- Reason: A channel's tests must be able to drive their channel without a server, as the TypeScript kit's harness lets them (DOC-2317, "Testing a channel"); today the helpers are private to the kit's own tests (section 3.5). VS-404 requires the same scenarios in the Python harness.
- Source: DOC-2317; VS-404; `harness.ts`; `test_kit.py` (`Recorder`, `run`, `connected`, `selected`, `event`, `key`, `started`).
- Verification: The kit's own tests are rewritten on the harness; the call list check.

**PY-44. What the harness gives back of sounds.** The harness MUST offer `sounds(connection)`, every sound member written to a connection in order (each without `type` and `connections`, as the program built it, with `bytes` fields given back as `bytes`); `sounds_of_kind(connection, kind)`; and `sounds_to_everyone()`. They are the TypeScript harness's `sounds` and its kin.
- Reason: A channel's test checks what a viewer was sent; the TypeScript harness has `sounds(session)`.
- Source: `harness.ts` (`sounds`).
- Verification: Harness tests.

**PY-45. The harness answers as the server would, when told to.** The harness MUST let a test answer a written sound message with a refusal (`refuse(message, path, rule, detail)`, whose fields must pass the schema's `Refused`) or with any report `server.md` defines (`report(message, …)`), delivered to the program as the server would deliver it; it MUST NOT refuse, report or build anything by itself.
- Reason: The harness stands in for the server's transport, not for its rules: a harness that refused by rules of its own would be a second copy of the server (PY-38). A program's handling of refusals and reports is still testable.
- Source: DEC-6462 item 3; PY-24; PY-25.
- Verification: A harness test refuses a sound and checks `on_refused` is called.

**PY-46. Wakes and the clock.** The kit MUST offer `now()`, the kit's clock in milliseconds since the program started, as the TypeScript kit's `now` (`context.ts`), and `wake_at(at_ms)` and `wake_in(delay_ms)`, which ask for one call of the handler `on_wake()` at that time on that clock, the earliest asked for winning, as the TypeScript kit's `wakeAt`, `wakeIn` and `wake` do; the Python kit has none of them today. A program MUST take every time it puts in a sound member from `now()`, so that the harness's clock drives it. The harness MUST own that clock in a test: `advance(milliseconds)` runs every wake due up to the new time, in order. A program that feeds a live sound MUST schedule its feeding through `wake_at` or `wake_in`, not `asyncio.sleep`, so that the harness can drive it.
- Reason: A live sound's test must run without waiting in real time; the TypeScript harness has `advance` and `runUntil`.
- Source: `harness.ts` (`advance`, `runUntil`); `context.ts` (`wakeAt`, `wakeIn`).
- Verification: The live keyboard example's test (PY-67) runs 10 seconds of a live sound in under a second.

**PY-47. Against the real server.** The kit's tests MUST include one test that runs a program on the kit under the server's own program runner, on real pipes, sends every worked example's messages of section 5, and checks that the server accepts each (no `refused`) and refuses one deliberately faulty message of each example with the path and rule `server.md` gives. The test MUST be ignored with its reason ("needs neoteletext-app-server built at `$NEOTELETEXT_SERVER`") when the server is not built, and MUST fail when asked for without it (DEVELOPMENT.md section 8).
- Reason: The harness answers nothing by itself (PY-45); one test against the server is what shows the kit's messages are the ones the server takes. The kit already runs a program on real pipes (`tests/pipe_program.py`).
- Source: DEVELOPMENT.md section 8; `pipe_program.py`.
- Verification: The test, run in the full gate (`full_steps`) where the server is built.

**PY-48. The examples are shared fixtures.** The `sound` messages of every worked example of section 5 MUST be kept in neoteletext-common as one fixture of JSON lines, `docs/audio/examples.jsonl`, one line a message, each a JSON object of exactly `example` (the example's name, as `typescript.md` section 4.0 names it) and `message` (the message as the program wrote it, with its `type` and `connections`), on the inputs and in the scenarios of `typescript.md` section 4.0; both kits' tests MUST produce exactly those messages, in order (equal as JSON values), from their own versions of the examples, and the server's tests MUST accept every line. The kit MUST keep a byte-for-byte copy of the file, pinned by `COMMON_FROM` and checked by its commit gate as PY-19's copy is. The fixture is the evidence that the two kits are equal for sounds.
- Reason: DEC-6462 item 3; S53-47's verification asks "that the TypeScript and Python kits send identical messages for the same program"; a fixture both read is how `hello.jsonl` already ties the TypeScript kit and the server together.
- Source: DEC-6462 item 3; S53-47; the TypeScript kit's `test/fixtures/hello.jsonl`.
- Verification: The kits' tests and the server's test of the fixture.

**PY-49. Viewer scenarios.** The harness MUST provide the viewer scenarios of VS-404 with the same names in `snake_case`.
- Reason: VS-404.
- Source: VS-404.
- Verification: As VS-404 says.

**PY-50. The kit's own tests move to the harness.** The helpers of `tests/test_kit.py` (`Recorder`, `run`, `connected`, `selected`, `event`, `key`, `started`) MUST be replaced by the harness, so that the kit tests what channels use.
- Reason: Two ways of driving the kit would test different things.
- Source: `test_kit.py`.
- Verification: Inspection.

### 4.6 The gaps this work closes

**PY-51. Every sound kind.** The release of the kit that speaks protocol 13 MUST be able to send every sound member of the schema copy (PY-20) and MUST be released only when the worked examples of section 5 pass (PY-66 to PY-73).
- Reason: Gap 1 of section 3.6; DEC-6462 item 3.
- Source: Section 3.6; DEC-6462.
- Verification: PY-20's test of every kind.

**PY-52. Measuring.** The same release MUST have `measure` (PY-29).
- Reason: Gap 2; the kits are equals.
- Source: Section 3.6.
- Verification: PY-29's tests.

**PY-53. Pictures.** The same release MUST have `regis`, `regis_links`, `regis_cursor` and `naplps` (PY-27).
- Reason: Gap 3; the kits are equals. They are part of the protocol both kits speak, and each is one thin call.
- Source: Section 3.6; DEC-6462 item 3.
- Verification: PY-27's tests.

**PY-54. Refusals.** The same release MUST have `on_refused` and the report handlers (PY-24, PY-25).
- Reason: Gap 4.
- Source: Section 3.6.
- Verification: PY-24's and PY-25's tests.

**PY-55. Tabs are independent (TODO-6445).** The same release MUST close TODO-6445's item 1 (each connection presented as its own unit, numbered as the connection, its state ended at `gone`) and item 2 (its tests), as VS-403 restates them for protocol 13, and item 4 (moving the Python channel to the release); item 3 (the Hackaday poll) is PY-63.
- Reason: Protocol 13 has no server session (VS-354): the kit cannot speak protocol 13 and keep presenting sessions; DEC-6462 item 3 requires equality with the TypeScript kit, which did this in its release 13.0.0 (DEC-6443).
- Source: TODO-6445; VS-354; VS-403; DEC-6443.
- Verification: TODO-6445's tests (PY-23).

**PY-56. Types and validation.** The same release MUST have the generated types (PY-7 to PY-17) and the run-time validation of PY-35 (DEC-6474).
- Reason: Gaps 5 and 6.
- Source: Section 3.6.
- Verification: As PY-14 and PY-35.

**PY-57. The version and the harness.** The same release MUST stop on another protocol version (PY-5) and offer the harness (PY-43).
- Reason: Gaps 7 and 9.
- Source: Section 3.6.
- Verification: As PY-5 and PY-43.

**PY-58. Opus encoding is recorded, not built.** The kit MUST NOT gain an Opus encoder in this work. The inequality (the TypeScript kit encodes samples as Opus through `ffmpeg`, `ffmpeg-opus.ts` and `opus-encoder.ts`; the Python kit sends Opus packets a program has encoded, through `sound`, and encodes none) MUST be recorded as an rdm to-do in neoteletext-server-channels, linked to DEC-6462 and REQ-1061, for the owner to decide.
- Reason: Opus encoding is not part of the synthesizers' programming interface, which is this document's subject; it runs another program (`ffmpeg`) and is logic, which DEC-6462 moves out of kits for synthesizers but does not address for Opus; with `sound` a Python program can already send every Opus kind. Equality says it must not stay silently unequal.
- Source: DEC-6462 item 3; REQ-1061 (its State says the Python kit does not encode Opus because of DEC-1082); `ffmpeg-opus.ts`.
- Verification: The to-do exists and is linked.

### 4.7 Protocol 13 for the old Python Hackaday channel

The old Hackaday channel is kept running and kept current with the protocol, nothing more (DEC-1082 item 5). It plays samples (`object`, `play`) and no synthesizer. These are exactly the changes protocol 13 forces on it.

**PY-59. The channel takes the kit's protocol-13 release.** The old Hackaday channel MUST move to the kit release that speaks protocol 13 in one commit with the kit's, since both are in one uv workspace and one gate, and MUST be deployed with the server and every other channel at once (VS-602 step 9).
- Reason: A program of protocol 12 cannot run under a server of protocol 13 (PY-5; VS-602).
- Source: VS-602; `pyproject.toml` (`[tool.uv.workspace]`).
- Verification: The repository's gates; the deployment's check that every channel's program reports protocol 13.

**PY-60. Its handlers name connections.** `Channel`'s handlers (`on_join`, `on_open`, `on_leave`, `on_input`, `on_close` and the rest in `hackaday/src/hackaday/channel.py`) MUST take connections in place of sessions and take the kit's names of PY-23 (`on_joined`, `on_opened`, `on_left_page`, `on_gone` in place of `on_join`, `on_open`, `on_leave`, `on_close`), and its `Viewer` state (scroll positions, the chosen item, the wheel and the grip per page) MUST be kept per connection, ended at `on_gone`.
- Reason: TODO-6445: two tabs on one scrolling page share one scroll position today, and one tab's scroll redraws the other's; under protocol 13 there is no session to key on (VS-354).
- Source: TODO-6445 (lines 428, 599 and 656 of `channel.py`); VS-403.
- Verification: A Hackaday test: two connections of one viewer on one scrolling page scroll independently; by hand, two tabs on a Hackaday scrolling page scroll independently.

**PY-61. Its sounds are sent per connection.** `hear` and `play_clip` MUST send a sound's `object` the first time on each connection (not each session) before its `play`, so that a connection is never told to play a sound it was never given.
- Reason: TODO-6445: "`hear` … sends a sound's definition only the first time per session, so a later tab is told to play a sound it was never given".
- Source: TODO-6445; `channel.py` (`hear`, lines 439 to 445; `play_clip`, lines 830 to 864).
- Verification: A Hackaday test: two connections of one viewer each hear a sound, and each receives its `object` before its `play`; it fails on the channel of today.

**PY-62. Its sound calls become `sound`.** Each call of `sound_object`, `play` and `stop` in `channel.py` (the five at lines 443, 445, 840, 843 and 848 as read on 18 November 2026, and any other) MUST become a call of `sound` with the generated member types, hearing `connection_hears(connection)`, with the same handles, gains, channels and pages.
- Reason: PY-31 removes the three calls.
- Source: PY-31; `channel.py`.
- Verification: Hackaday's tests, which check what each connection was sent, pass unchanged in their expectations.

**PY-63. Its poll keys on the viewer.** The poll's "one vote per viewer" (lines 883 to 898 and 432 to 437 of `channel.py`) MUST key a ballot on the viewer handle (VS-401), asking for state with `request_state` on the vote's input when the connection has no viewer, and keeping a vote for the connection's life only when state is refused, as VS-407 specifies for the component library's `Tally`; it MUST NOT use a cookie (VS-402). This replaces TODO-6445 item 3's cookie, which protocol 13 removes.
- Reason: Under per-connection presentation a session-keyed vote becomes one vote a tab; cookies are gone (DEC-6471).
- Source: TODO-6445 item 3; VS-401, VS-402, VS-407; DEC-6471.
- Verification: Hackaday tests with the harness's viewers: alice in two tabs votes once; with state refused, a vote counts for its connection's life.

**PY-64. Nothing else in the channel changes.** The old Hackaday channel MUST NOT gain a synthesizer sound, a picture, measuring or any other feature in this work.
- Reason: DEC-1082 item 5.
- Source: DEC-1082.
- Verification: Review of the commit.

**PY-65. Cookies leave the channel.** Every use of cookies in the old Hackaday channel and its tests (none is in `channel.py` as read on 18 November 2026; the tests' `connected` carries `cookies`) MUST be removed with the kit's (VS-402).
- Reason: VS-402.
- Source: VS-402; `test_kit.py` (`connected`).
- Verification: A search of the channel and its tests for "cookie" finds nothing.

### 4.8 The worked examples

Each example is a complete program of section 5, kept in the kit's guide and run as a kit test on the harness (PY-43), its messages kept in the shared fixture (PY-48) and sent to the server in PY-47's test.

**PY-66. A stored tune (synth6581).** The kit MUST carry the example of section 5.1: a stored synth6581 sound of ASID register updates given as named fields, played on audio channel 0 to the connections on a page.
- Reason: The brief's "a stored tune"; it shows a stored sound, times in microseconds, and the synth6581 family's register updates as fields (S6581-53 item 3).
- Source: S6581-53; MIDI-17; MIDI-19.
- Verification: Its test checks the members written and that they equal the fixture.

**PY-67. A live keyboard (synth106).** The kit MUST carry the example of section 5.2: a live synth106 sound fed by note on and note off events from a viewer's keys, with `until_us` advanced every 100 milliseconds by a wake.
- Reason: The brief's "a live keyboard"; it shows a live sound (MIDI-20), the program's own clock (PY-30) and feeding by wakes (PY-46).
- Source: MIDI-20; S106 family.
- Verification: Its test runs `typescript.md` section 4.0's scenario and checks the lines against the fixture; a second test presses keys through the harness, advances the clock 10 seconds and checks every events message's `until_us` advances by at most 2,000,000 microseconds, is later than each of its events, and that its events are those of the keys.

**PY-68. A patch by fields (synth106).** The kit MUST carry the example of section 5.3: a synth106 patch given as named, typed fields (S106-36), sent inline in a stored sound's events.
- Reason: The brief's "a patch by fields"; MIDI-14 form 1.
- Source: MIDI-14; MIDI-60; S106-36.
- Verification: Its test checks the member and the fixture.

**PY-69. A patch by system exclusive (synth7).** The kit MUST carry the example of section 5.4: a synth7 single-voice bulk dump read from a file of 163 bytes and sent inline as the interface's own bytes.
- Reason: The brief's "a patch by system exclusive"; MIDI-14 form 2.
- Source: MIDI-14; MIDI-54 (synth7's 163 bytes); `synth7.md`.
- Verification: Its test checks the member carries the file's bytes exactly.

**PY-70. A bank (synth53 and synth80).** The kit MUST carry the examples of section 5.5: a synth53 bank given as a list of program dumps of one group, and a synth80 bank given as a list of patches in the interface's bytes (85 control values each), each named by a stored sound that chooses its patches by program change and, for synth80, bank select by controller 0.
- Reason: The brief's "a bank"; MIDI-15, MIDI-57, MIDI-59, MIDI-64.
- Source: MIDI-15; MIDI-56; S53-47; `synth80.md` S80-36.
- Verification: Their tests check the members and the fixture.

**PY-71. A Standard MIDI File (synth7).** The kit MUST carry the example of section 5.6: a stored synth7 sound given as a Standard MIDI File's bytes, read from a file by the program and passed whole, with a channel map, a handle for a bank dump at the file's start that the server lifts (MIDI-58), and the program's handling of the server's report of dropped messages (MIDI-118).
- Reason: The brief's "a MIDI file"; the server reads the file, never the kit (MIDI-112).
- Source: MIDI-58; MIDI-112 to MIDI-120.
- Verification: Its test checks the member carries the file's bytes exactly and that a report given by the harness reaches the handler.

**PY-72. A named parameter in a live sound (synth8 and synthD).** The kit MUST carry the example of section 5.7: a live synth8 sound in which the program moves a parameter by name (MIDI-18) as the viewer turns the wheel, and a stored synthD sound given its patch as the 60 values in the family's order.
- Reason: The two remaining families, synth8 and synthD, and the named-parameter form of MIDI-18, which no other example shows.
- Source: MIDI-18; `synth8.md`; `synthd.md` SD-22.
- Verification: Their tests check the members and the fixture.

**PY-73. The examples are corrected to `server.md`.** Every kind, field and value an example spells MUST be `server.md`'s as published in `schema-13.json`; an example that the schema copy does not validate MUST fail its test, and the examples MUST be corrected to the schema before the kit's protocol-13 release.
- Reason: This document was written beside `server.md`; the spellings in section 5 are this document's reading of the architecture and the family documents and are not definitions (scope).
- Source: Scope; PY-35; PY-36.
- Verification: The examples' tests validate every member against the schema copy.

### 4.9 Protocol 14: the page rule table and animation

Program protocol 14 (`../page-rules.md` RULE-34, `../animation.md` ANIM-21; DEC-6522, DEC-6524) adds the page rule table and the animation messages. The Python kit takes it as it took protocol 13, and the requirements above hold for it with 14 read for 13: the schema copy is `protocol-14.json`, the server's `protocol/schema-14.json` (PY-1, PY-2), `PROTOCOL` is 14 (PY-4, PY-11), and a `start` of any other version stops the program (PY-5). The requirements below say what protocol 14 adds to this document; rdm requirement REQ-6538 carries them.

**PY-74. The constructs protocol 14 adds to the generator.** Beside PY-9's table, the generator MUST translate: `patternProperties` of exactly one pattern in an object with `"additionalProperties": false` and no `properties` (the `variables` and `timers` of `page_state`, keyed by name) as `dict[str, T]`, the pattern held by validation; a union of objects and other members (`RuleTarget`: the word `"page"` beside `{"control": n}`, `{"object": n}` and `{"rect": name}`) as an alias of the named object types and the other members' types, in the schema's order; and an object with a key that is a Python keyword (`and`, `or` and `not` of `RuleCondition`) in `TypedDict`'s functional form, each key's type written as a string, as PY-10 already requires. Any other use of `patternProperties` MUST stop the generator.
- Reason: These are the constructs `schemars` emits for the rule table's types; PY-9's rule stands that the generator knows exactly what the schema holds and stops on anything else.
- Source: `schema-14.json`; page-rules.md RULE-35, RULE-38; PEP 589.
- Verification: A generator test for each; a test that `patternProperties` beside `properties` stops the generator, and that a construct the schema never holds (`if`) stops it.

**PY-75. The names protocol 14 adds.** PY-10 rule 2's tag properties are `type`, `kind`, `event`, `form`, `packet`, `action` and `of`: `action` tags `RuleAction` and `AnimationOp` (`RuleActionMidi`, `AnimationOpReset`) and `of` tags `RuleValue` (`RuleValueSynth`). A branch of an untagged union that has several properties MUST be named the union's name followed, in upper camel case, by the first property it requires that no other branch of the union has (`RuleCondition`'s branches of `read`, `op` and `value`, of `read` and `in_range`, and of `read` and `in_set` are `RuleConditionOp`, `RuleConditionInRange` and `RuleConditionInSet`); a branch with no such property MUST stop the generator. The types RULE-55 and ANIM-19 name (`RuleTable`, `PageRule`, `RuleTrigger`, `RuleCondition`, `RuleValue`, `RuleAction`, `RuleTarget`, `AnimationOp`, `Sprite`, `NaplpsObject`) are the schema's definitions under their own names (PY-10 rule 1); the answer to a state query is `ServerMessagePageState` (PY-10 rule 2).
- Reason: One rule gives each type its one name; the rule table's unions are tagged by what their documents tag them with.
- Source: page-rules.md RULE-35, RULE-55; `schema-14.json`.
- Verification: Generator tests of the two tags and of the untagged branch's name; the kit test that every message of the schema has its generated type.

**PY-76. The rule table's calls.** The kit MUST offer `App.rules(to: Hearer, page: int, table: RuleTable | None) -> None`, which writes one `rules` message for each chunk of the hearers' connections, the table exactly as built (no default filled in, no name checked), `None` written as `null`; and `async def query_state(connection: int, page: int) -> ServerMessagePageState`, which writes `query_state` with a request number of the kit's own count (1 to 4,294,967,295, then 1 again) and answers with the server's `page_state` of that number, or raises `QueryRefused` carrying the server's `refused` of that number (`too_frequent`, `wrong_page`, `not_answered` and the others of RULE-39). A `refused` that answers a state query reaches no handler, as one that answers a measurement reaches none (PY-29).
- Reason: RULE-55; DEC-6462: the kit builds and sends, and the server checks.
- Source: page-rules.md RULE-35, RULE-38, RULE-39, RULE-55.
- Verification: Kit tests that the six examples of page-rules.md section 7.5 and the music player's table of RULE-93, built as Python values, are written as exactly the documents' JSON (PY-80); that a state query is answered and refused; the call list (PY-19).

**PY-77. What a rule's firing gives a program.** The kit MUST give `on_input` each `input` message's event with three more fields of `Event`: `rule` (the name of the rule that sent it), `tick` (the page tick it fired at) and `target` (the target the pointer was inside, or `None`), as RULE-37 defines them. It MUST call `on_rule_event(event: ServerMessageRuleEvent)` for each `rule_event` and `on_rules_fault(fault: ServerMessageRulesFault)` for each `rules_fault`, each with the validated message whole, and with `connection()` answering the message's connection while the handler runs.
- Reason: RULE-55; PY-17 (handlers receive the generated wire types).
- Source: page-rules.md RULE-37, RULE-48, RULE-55.
- Verification: Kit tests of the three.

**PY-78. The animation calls.** The kit MUST offer, each writing one message of ANIM-21 for each chunk of the hearers' connections and checking nothing beyond the schema: `frame(to, page, sub)`, a context manager that writes `frame` with `"mark": "begin"` on entry and with `"mark": "end"` on exit, also when its block raises, to the hearers named on entry; `animate(to, page, sub, ops: list[AnimationOp])`; `sprites(to, page, sub, sprites: list[Sprite])`; `naplps_objects(to, page, sub, objects: list[NaplpsObject])`; `sprite_sheet(to, page, kind, data: str | bytes, restart: bool = False)`, text written a byte a character (Latin-1), as `regis` writes ReGIS text and as the TypeScript kit writes a sheet's (animation.md ANIM-19), and all bytes as base64 (PY-13); `play_timeline(to, page, sub, timeline: Timeline, id: int | None = None) -> int`, which writes `timeline` with the timeline's `steps` and `loop_ticks` (`null` when it has none) and answers the identifier, the kit's own count (1 to 65,535, then 1 again) when none is given; and `stop_timeline(to, page, id)`. The local sound kinds of RULE-61 (`synth7_local` to `synth80_local`) are members of `SoundMember` and are sent with `sound` (PY-20).
- Reason: ANIM-19; DEC-6462: the server plays a timeline, so the kit holds no scheduler.
- Source: animation.md ANIM-19, ANIM-21; page-rules.md RULE-61.
- Verification: Kit tests that each call writes the message of ANIM-21's example; that a frame is ended when its block raises; the call list.

**PY-79. The timeline builder.** The kit's module `neoteletext_app.timeline` MUST offer `Timeline` and `TimelineStep` with ANIM-19's Python signatures. `Timeline(*, loop_ticks=None)`; `at(tick)` answers a new step at that tick; `then(ticks)` a new step that many ticks after the last step made (after tick 0 when none was made); each of a step's methods (`move`, `show`, `hide`, `look`, `order`, `frame`, `cycle`, `stop_cycle`, `reset`) adds one operation on `{"object": n}` and answers the step, writing `relative` and `once` always (`false` when not given) and `layer` as given (`null` to keep it). `steps` is the `timeline` message's `steps`: in ascending tick, the steps of one tick joined in the order they were made, and a step given no operation left out (it would send nothing, and the schema takes no step without an operation), though `then` still counts from it. The builder checks nothing and holds no clock.
- Reason: ANIM-19 ("`Timeline` only gathers steps ... sorts them by tick, joins steps of one tick, and holds no clock").
- Source: animation.md ANIM-19.
- Verification: The shared fixture of PY-80.

**PY-80. The fixtures of protocol 14.** neoteletext-common MUST keep two fixtures of JSON lines beside the documents they come from, and each kit a byte-for-byte copy of each, pinned by `COMMON_FROM` and checked by its commit gate as PY-19's copy is: `docs/rules-examples.jsonl`, one line for each of the six worked examples of page-rules.md section 7.5 (`example-1` to `example-6`) and one for the music player's table of RULE-93 (`music-player`), each an object of `example` and `message`, the `rules` message exactly as the document writes it; and `docs/timelines.jsonl`, one line a timeline, each an object of `timeline` (its name), `loop_ticks`, `calls` (the builder's calls in order, each a list of the call's protocol name in snake_case and its arguments: `at` and `then` begin a step and each other call adds to the step last begun), `page`, `sub`, `id` and `message` (the `timeline` message `play_timeline` must write to every connection). Each kit's tests MUST build every example's table and every timeline in its own language and write exactly the fixture's message (equal as JSON values).
- Reason: ANIM-19's verification ("a shared fixture of timelines and the `timeline` messages they must produce, checked by both kits"); the rule examples are held the same way so that the documents' JSON is what both kits send.
- Source: animation.md ANIM-19; page-rules.md section 7.5 and RULE-93; PY-48 as the pattern.
- Verification: The kits' tests of the two fixtures; the commit gate's check of the copies.

**PY-81. The harness for rules and animation.** Under protocol 14 every `input` names the rule that sent it, so the harness's input calls (`send`, `key`, `press`, `click`, `wheel` and the others) MUST name the rule of the server's default table (RULE-53) that sends that event (`keys`, `keys_up`, `text`, `press`, `release`, `move`, `hover_in`, `hover_out`, `drawing_in`, `drawing_out`, `focus`, `blur`, `wheel`), as a program of a channel with `default_rules: send_all` hears it, with the harness's clock in ticks as the event's tick. The harness MUST also offer: `fire(connection, rule, event=None, tick=None, target=None)`, which gives the program what that rule's firing sends (with no event a `rule_event` of kind `fired`; with a `rule_event`'s body that `rule_event`; with an input event the `input` naming the rule and target); `answer_state(message, state=None)`, which answers a `query_state` the program wrote with a `page_state` of its request, the fields `state` gives over those of a page with no table; and `timeline_sends(connection)`, the `animate` messages the server would send the connection as it plays each timeline written, once through, each with its timeline's identifier and its step's tick. The harness does not stop, replace or loop a timeline and does not evaluate a table: those are the server's and the receiver's (PY-45).
- Reason: RULE-55 ("each kit's test harness gains `press`, `fire` and `answerState`"; `press` is the harness's existing call, which now names a rule); ANIM-19 ("each kit's test harness records the messages a timeline would send").
- Source: page-rules.md RULE-53, RULE-55; animation.md ANIM-19.
- Verification: Kit tests of each call; the call list.

**PY-82. The old Hackaday channel under protocol 14.** The old Hackaday channel MUST NOT change: the server gives each of its pages the default table (`default_rules: send_all`, RULE-53), so it hears the input it heard under protocol 13, each event now naming its rule. Only its tests' helper that writes an `input` as the server sends it gains the `rule` and `tick` the schema requires.
- Reason: DEC-1082 item 5; RULE-53.
- Source: page-rules.md RULE-53; build plan of 18 November 2026, section 9.
- Verification: The channel's tests pass on the protocol-14 kit with no change to `hackaday/src`.

---

## 5. Worked examples

**About the spellings.** These programs are complete in what they do, and they show the calls of section 4.3 exactly. Every sound member they build is a generated type of `server.md`'s schema, and every kind, field, event shape and patch field they spell is `server.md`'s (SRV-3 to SRV-48), as DEC-6477 settles for every document of this set: `time_us`; events tagged by `event`; `length` as `{"tail_us": …}` or `{"length_us": …}`; `music` tagged by `form`; `until_us`, always later than every event's `time_us` (SRV-74); `banks` as a list of bank handles, naming at least one bank in every sound of a family with banks (MIDI-57; SRV-16, SRV-17); `lift_banks`; a patch's fields beside its `form`; a parameter event's `set` as `{name: value}`; a bank select as a program change's `bank_msb` or `bank_lsb`; `play` with every field the schema requires. The generated type names follow PY-10 (a sound kind's member type is `Sound` followed by the kind in upper camel case and `Member`). They are the seven examples of `typescript.md` section 4, with the same pages, handles and values, and on the inputs and in the scenarios of `typescript.md` section 4.0, which both kits' tests use, each writes exactly the lines of `docs/audio/examples.jsonl` that bear its name (PY-48). Nothing in them defines a message.

Each example's program is a subclass of `App`; its `async` handlers are the kit's (PY-23 to PY-26), named as the TypeScript kit's are with `on_` before them (PY-18), and its `now`, `wake_in` and `on_wake` are PY-46's.

### 5.1 A stored tune: synth6581

A program sends a short tune for synth6581 once to each connection that opens page 300 and plays it on audio channel 0. Every update is a time in microseconds and an ASID register data message given as named fields (SRV-12; S6581-53 item 3); the first is a full register update at time 0, as S6581-54 item 8 requires (the server checks that, not the kit).

```python
from neoteletext_app.app import App, connection_hears
from neoteletext_app.protocol_types import SoundPlayMember, SoundSynth6581Member, Synth6581Event

TUNE_PAGE = 0x300
TUNE_HANDLE = 4
#: One frame of a 50 Hz tune, in microseconds (MIDI-17's unit).
FRAME_US = 20_000
#: C, E, G, C as the chip's frequency register values on a PAL clock, low byte and high byte
#: (4,291; 5,407; 6,430; 8,583), worked out once by the author from the chip's formula (S6581-35).
NOTES = ((0xC3, 0x10), (0x1F, 0x15), (0x1E, 0x19), (0x87, 0x21))
#: Voice 1's control register: pulse waveform (bit 6), gate (bit 0) open or closed.
PULSE_GATE_ON = 0x41
PULSE_GATE_OFF = 0x40


def tune() -> SoundSynth6581Member:
    events: list[Synth6581Event] = [
        # A full register update at time 0: every register of IDs 0 to 24 written (SRV-25).
        {"event": "register_update", "time_us": 0, "registers": {
            "voice1_frequency_low": NOTES[0][0], "voice1_frequency_high": NOTES[0][1],
            "voice1_pulse_width_low": 0x00, "voice1_pulse_width_high": 0x08,
            "voice1_attack_decay": 0x09, "voice1_sustain_release": 0xA0,
            "voice2_frequency_low": 0, "voice2_frequency_high": 0, "voice2_pulse_width_low": 0, "voice2_pulse_width_high": 0,
            "voice2_attack_decay": 0, "voice2_sustain_release": 0,
            "voice3_frequency_low": 0, "voice3_frequency_high": 0, "voice3_pulse_width_low": 0, "voice3_pulse_width_high": 0,
            "voice3_attack_decay": 0, "voice3_sustain_release": 0,
            "filter_cutoff_low": 0x00, "filter_cutoff_high": 0x80, "filter_resonance_routing": 0x01, "filter_mode_volume": 0x1F,
            "voice1_control": PULSE_GATE_OFF, "voice2_control": 0, "voice3_control": 0,
        }},
    ]
    for index, (low, high) in enumerate(NOTES):
        start = index * 12 * FRAME_US
        events.append({"event": "register_update", "time_us": start, "registers": {"voice1_frequency_low": low, "voice1_frequency_high": high, "voice1_control": PULSE_GATE_ON}})
        events.append({"event": "register_update", "time_us": start + 9 * FRAME_US, "registers": {"voice1_control": PULSE_GATE_OFF}})
    return {
        "kind": "synth6581",
        "handle": TUNE_HANDLE,
        "generation": 0,
        "clock": "pal",
        "length": {"tail_us": 500_000},
        "music": {"form": "events", "events": events},
    }


class Tune(App):
    async def on_opened(self, connection: int, page: int) -> None:
        if page != TUNE_PAGE:
            return
        to = connection_hears(connection)
        self.sound(to, tune())
        play: SoundPlayMember = {"kind": "play", "channel": 0, "handle": TUNE_HANDLE, "generation": 0, "gain": 80, "fade_ms": 0, "loop": False, "after": False, "duck": 0, "page": "300"}
        self.sound(to, play)
```

What happens: the kit validates each member against the schema and writes two `sound` lines. The server places each update at the tick `floor((time_us + 50) / 100)` (SRV-8), builds the blocks, writes the OBJECT and DATA records and plays the sound on the `play`. If the first update were not a full register update, the server would refuse the stored sound and the program's `on_refused` would hear it, the refusal's `sound` naming kind `synth6581`, handle 4 and generation 0 (PY-24, SRV-48); the kit would not. The play is sent once, when the page is opened, and not again while the connection stays on it (`integration.md` INT-28).

### 5.2 A live keyboard: synth106

The viewer plays synth106 from the keyboard on page 310: the keys `a` to `k` are a white-key octave from middle C. The program sends the bank of section 5.3 and announces a live sound when the connection opens the page, turns each key press and release into a note on or note off at the program's own time on the kit's clock, and every 100 milliseconds sends what it has with `until_us` one microsecond past now, so that every event given so far lies before it (SRV-74) and the server writes every block that has ended (MIDI-20).

```python
from neoteletext_app.app import App, connection_hears
from neoteletext_app.event import Event
from neoteletext_app.protocol_types import (
    SoundPlayMember,
    SoundStopMember,
    SoundSynth106EventsMember,
    SoundSynth106LiveMember,
    Synth106Event,
)

from .patch_by_fields import BRASS_BANK, brass_bank

KEYBOARD_PAGE = 0x310
LIVE_HANDLE = 6
#: Middle C, MIDI note 60, then the white keys up to the next C.
KEY_NOTES = {"a": 60, "s": 62, "d": 64, "f": 65, "g": 67, "h": 69, "j": 71, "k": 72}
#: How often the program says how far it has given every event: well inside MIDI-20's
#: 2,000,000 microseconds a message, and short enough that a key sounds within a block or five.
FEED_MS = 100
MICROSECONDS_PER_MILLISECOND = 1_000
#: `until_us` is one microsecond past now, so that an event stamped now is before it (SRV-74).
PAST_NOW_US = 1


class Player:
    """One connection's live sound: its start on the kit's clock and the events not yet sent."""

    def __init__(self, start_ms: int) -> None:
        self.start_ms = start_ms
        self.pending: list[Synth106Event] = []


class Keyboard(App):
    def __init__(self, pages: dict[int, str]) -> None:
        super().__init__(pages)
        self.players: dict[int, Player] = {}

    def now_us(self, player: Player) -> int:
        return (self.now() - player.start_ms) * MICROSECONDS_PER_MILLISECOND

    async def on_opened(self, connection: int, page: int) -> None:
        if page != KEYBOARD_PAGE:
            return
        to = connection_hears(connection)
        live: SoundSynth106LiveMember = {"kind": "synth106_live", "handle": LIVE_HANDLE, "generation": 0, "banks": [BRASS_BANK]}
        play: SoundPlayMember = {"kind": "play", "channel": 1, "handle": LIVE_HANDLE, "generation": 0, "gain": 100, "fade_ms": 0, "loop": False, "after": False, "duck": 0, "page": "310"}
        self.sound(to, brass_bank())
        self.sound(to, live)
        self.sound(to, play)
        self.players[connection] = Player(self.now())
        self.wake_in(FEED_MS)

    async def on_input(self, connection: int, page: int, event: Event, sub: int) -> bool:
        player = self.players.get(connection)
        key = KEY_NOTES.get(event.text or event.key or "") if event.kind == "key" and event.action != "repeat" else None
        if player is None or key is None:
            return False
        time_us = self.now_us(player)
        if event.action == "press":
            player.pending.append({"event": "note_on", "time_us": time_us, "channel": 1, "key": key, "velocity": 100})
        else:
            player.pending.append({"event": "note_off", "time_us": time_us, "channel": 1, "key": key, "velocity": 64})
        return True

    async def on_wake(self) -> None:
        for connection, player in self.players.items():
            events: SoundSynth106EventsMember = {
                "kind": "synth106_events",
                "handle": LIVE_HANDLE,
                "generation": 0,
                "until_us": self.now_us(player) + PAST_NOW_US,
                "events": player.pending,
            }
            self.sound(connection_hears(connection), events)
            player.pending = []
        if self.players:
            self.wake_in(FEED_MS)

    async def on_left_page(self, connection: int, page: int) -> None:
        if self.players.pop(connection, None) is not None:
            stop: SoundStopMember = {"kind": "stop", "channel": 1, "fade_ms": 20}
            self.sound(connection_hears(connection), stop)
```

What happens: each events message is validated and written. The server writes the events into the blocks their times fall in, sends the blocks that have ended by `until_us` no more than 25 blocks ahead of the live sound's clock (SRV-77), restates the part's state at least once in every 50 blocks for a viewer who joins late (MIDI-96), and refuses an event whose block it has already written (MIDI-20). The kit numbers no block and keeps no clock but the one it keeps for wakes (PY-30, PY-46). The live sound names the bank of section 5.3, sent first (MIDI-57); with no program change the part plays program 0 of bank index 0 (MIDI-61).

### 5.3 A patch by fields: synth106

The same family: a patch given as named, typed fields (MIDI-14 form 1; SRV-30: the sixteen sliders 0 to 127, range, pulse, sawtooth, chorus, PWM source, envelope polarity, VCA control and high-pass filter), used as the one patch of a bank, which a sound of the family must name (MIDI-57), and inline as the first event of a stored phrase (MIDI-60). The module is `patch_by_fields.py`, which section 5.2 imports.

```python
from neoteletext_app.protocol_types import SoundSynth106BankMember, SoundSynth106Member, Synth106Panel

BRASS_BANK = 5

BRASS: Synth106Panel = {
    "lfo_rate": 40, "lfo_delay": 0, "dco_lfo": 0, "dco_pwm": 0, "noise_level": 0,
    "vcf_frequency": 52, "vcf_resonance": 18, "vcf_envelope": 70, "vcf_lfo": 0, "vcf_keyboard": 64,
    "vca_level": 90, "attack": 22, "decay": 60, "sustain": 80, "release": 30, "sub_level": 40,
    "range": "feet_8", "pulse": False, "sawtooth": True, "chorus": "one",
    "pwm": "manual", "envelope_polarity": "positive", "vca": "envelope", "hpf": 0,
}


def brass_bank() -> SoundSynth106BankMember:
    return {"kind": "synth106_bank", "handle": BRASS_BANK, "generation": 0, "bank": {"form": "patches", "patches": [{"form": "fields", **BRASS}]}}


def brass_phrase() -> SoundSynth106Member:
    return {
        "kind": "synth106",
        "handle": 7,
        "generation": 0,
        "banks": [BRASS_BANK],
        "lift_banks": [],
        "length": {"tail_us": 800_000},
        "music": {"form": "events", "events": [
            {"event": "patch", "time_us": 0, "channel": 1, "patch": {"form": "fields", **BRASS}},
            {"event": "note_on", "time_us": 0, "channel": 1, "key": 60, "velocity": 96},
            {"event": "note_off", "time_us": 400_000, "channel": 1, "key": 60, "velocity": 64},
        ]},
    }
```

What happens: a program sends `brass_bank()` before `brass_phrase()`. The server encodes the fields into the Juno-106's 24-byte patch message (S106-37), once for the bank image and once as one system exclusive event at tick 0, before the note on (MIDI-35); the two are identical bytes (MIDI-14). A missing field or a field out of its range is refused by the kit's schema validation before writing (PY-35); what the schema cannot state is the server's refusal (PY-38). `Synth106Panel` is the generated type of the server's `Synth106Panel` (SRV-30), and the patch's `fields` form is that type's keys beside `form`, as SRV-21's internally tagged enum writes it.

### 5.4 A patch by system exclusive: synth7

A program has a DX7 voice as the 163 bytes of a single-voice bulk dump, as any librarian saves it, and sends it inline at the start of a stored sound (MIDI-14 form 2; MIDI-54, synth7's patch form; MIDI-60). The sound names a bank, as every sound of a family with banks must (MIDI-57): a bank of that one voice in the `patches` form, which the server fills to 32 voices with the default voice (SRV-56).

```python
from pathlib import Path

from neoteletext_app.protocol_types import SoundSynth7BankMember, SoundSynth7Member

#: A DX7 single-voice bulk dump is 163 bytes (MIDI-54); a file of another length is not one,
#: and a program should not send what it knows is wrong. The server checks the bytes.
VOICE_DUMP_BYTES = 163
VOICES = 9


def read_voice(voice_file: Path) -> bytes:
    dump = voice_file.read_bytes()
    if len(dump) != VOICE_DUMP_BYTES:
        message = f"{voice_file}: {len(dump)} bytes, not a single-voice dump"
        raise ValueError(message)
    return dump


def voice_bank(voice_file: Path) -> SoundSynth7BankMember:
    return {"kind": "synth7_bank", "handle": VOICES, "generation": 0, "bank": {"form": "patches", "patches": [{"form": "bytes", "bytes": read_voice(voice_file)}]}}


def electric_piano(voice_file: Path) -> SoundSynth7Member:
    return {
        "kind": "synth7",
        "handle": 8,
        "generation": 0,
        "banks": [VOICES],
        "lift_banks": [],
        "length": {"tail_us": 1_500_000},
        "music": {"form": "events", "events": [
            {"event": "patch", "time_us": 0, "channel": 1, "patch": {"form": "bytes", "bytes": read_voice(voice_file)}},
            {"event": "note_on", "time_us": 0, "channel": 1, "key": 64, "velocity": 90},
            {"event": "note_off", "time_us": 1_000_000, "channel": 1, "key": 64, "velocity": 64},
        ]},
    }
```

The length check is the program's own choice about its own file, not a kit rule. The kit writes each dump as base64 (PY-13). The server checks the dump with the receiver's own code (header, byte ranges, checksum; MIDI-21, MIDI-63) and refuses a faulty one, naming the byte; it writes it as one system exclusive event of 163 bytes, within MIDI-28's 256.

### 5.5 A bank: synth53 and synth80

**synth53.** A bank is 1 to 40 program dumps of one group (S53-47; MIDI-56), given here as the dumps' bytes from a file a librarian saved, and a stored sound names it and chooses programs 0 and 1 by program change, the group chosen by bank select on controller 32 written as the program change's `bank_lsb` (MIDI-64; S53-13: value 1 chooses group 0, the group of the file's dumps; SRV-10).

```python
from pathlib import Path

from neoteletext_app.app import App, page_hears
from neoteletext_app.protocol_types import SoundSynth53BankMember, SoundSynth53Member

BANK_HANDLE = 20
#: Controller 32's value 1 chooses group 0 (S53-13), the group of the bank's dumps.
GROUP_0 = 1


def group_bank(dumps_file: Path) -> SoundSynth53BankMember:
    return {"kind": "synth53_bank", "handle": BANK_HANDLE, "generation": 0, "bank": {"form": "bytes", "bytes": dumps_file.read_bytes()}}


def two_programs() -> SoundSynth53Member:
    return {
        "kind": "synth53",
        "handle": 21,
        "generation": 0,
        "banks": [BANK_HANDLE],
        "lift_banks": [],
        "length": {"tail_us": 1_000_000},
        "music": {"form": "events", "events": [
            {"event": "program_change", "time_us": 0, "channel": 1, "program": 0, "bank_lsb": GROUP_0},
            {"event": "note_on", "time_us": 0, "channel": 1, "key": 57, "velocity": 100},
            {"event": "note_off", "time_us": 1_000_000, "channel": 1, "key": 57, "velocity": 64},
            {"event": "program_change", "time_us": 1_000_000, "channel": 1, "program": 1, "bank_lsb": GROUP_0},
            {"event": "note_on", "time_us": 1_000_000, "channel": 1, "key": 57, "velocity": 100},
            {"event": "note_off", "time_us": 2_000_000, "channel": 1, "key": 57, "velocity": 64},
        ]},
    }


class Banked(App):
    async def on_opened(self, connection: int, page: int) -> None:
        if page == 0x320:
            to = page_hears(page)
            self.sound(to, group_bank(Path("group-0.syx")))
            self.sound(to, two_programs())
```

The server splits the bank's dumps into the bank codec's records (MIDI-55), checks each dump (MIDI-63), sends the bank before the sound's OBJECT (MIDI-57) and refuses a sound that names a bank it does not hold for this program.

**synth80.** A bank given as a list of patches, each in the interface's bytes: for synth80 a patch is 85 control values in `synth80.md`'s fixed order (MIDI-54; S80-33). Three such banks are what Deckard's Dream's controller 0 chooses among (values 0 to 2; S80-36).

```python
from neoteletext_app.protocol_types import SoundSynth80BankMember


def strings_bank(patches: list[bytes]) -> SoundSynth80BankMember:
    return {
        "kind": "synth80_bank",
        "handle": 30,
        "generation": 0,
        "bank": {"form": "patches", "patches": [{"form": "bytes", "bytes": patch} for patch in patches]},
    }
```

A sound naming banks 30, 31 and 32 as bank indexes 0, 1 and 2 then chooses bank 2's program 5 with `{"event": "program_change", "time_us": time_us, "channel": 1, "program": 5, "bank_msb": 2}` (MIDI-59, MIDI-64; SRV-10 writes `Bn 00 02` then `Cn 05` at one tick).

### 5.6 A Standard MIDI File: synth7

A program plays a Standard MIDI File made for a DX7 on synth7, its channels 1 and 2 mapped to parts 1 and 2 and every other channel dropped (MIDI-116; SRV-23). The file opens with a 32-voice bulk dump, which the server lifts into a bank with the handle the program names (MIDI-58; SRV-15); that lifted bank is the sound's only bank, so `banks` is empty and the lifted bank is bank index 0, as SRV-16 allows (DEC-6477). The program hears the server's report, `sound_built` (SRV-47), by `on_sound_built` (PY-25).

```python
from pathlib import Path

from neoteletext_app.app import App, page_hears
from neoteletext_app.protocol_types import SoundBuilt, SoundSynth7Member

FILE_PAGE = 0x330
LIFTED_BANK = 40


def from_file(midi_file: Path) -> SoundSynth7Member:
    return {
        "kind": "synth7",
        "handle": 41,
        "generation": 0,
        "banks": [],
        "lift_banks": [{"handle": LIFTED_BANK, "generation": 0}],
        "length": {"tail_us": 2_000_000},
        "music": {
            "form": "midi_file",
            "bytes": midi_file.read_bytes(),
            "channel_map": [1, 2, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
        },
    }


class FilePlayer(App):
    async def on_opened(self, connection: int, page: int) -> None:
        if page == FILE_PAGE:
            self.sound(page_hears(page), from_file(Path("tune.mid")))

    async def on_sound_built(self, report: SoundBuilt) -> None:
        self.log(f"{report['kind']} {report['handle']}: {report['blocks']} blocks, dropped {report['dropped']}")
```

The kit sends the file's bytes as they are; it parses nothing (MIDI-112). The server reads the file within MIDI-119's bounds (at most 1,048,576 bytes, 1,024 tracks, 100,000 events), merges tempo (MIDI-114), joins split system exclusive (MIDI-117), lifts the leading dump into bank 40 as the sound's bank index 0, refuses a dump after the first note (MIDI-58), builds the blocks, and reports what it dropped (MIDI-118; SRV-47).

### 5.7 A named parameter in a live sound, and a patch of control values: synth8 and synthD

**synth8.** In a live synth8 sound the viewer's mouse wheel moves the filter's cutoff by name (MIDI-18; SRV-22). The program names the parameter as SRV-42 names synth8's parameters, the field names of `Synth8Panel` (SRV-40), and gives its value; the server writes the controller the family document names for it (controller 3, S8-16). Announcing the live sound, setting `start_ms`, and advancing `until_us` by wakes between turns of the wheel are as in section 5.2, left out here.

```python
from neoteletext_app.app import App, connection_hears
from neoteletext_app.event import Event
from neoteletext_app.protocol_types import SoundSynth8EventsMember

LIVE8 = 50
#: The cutoff's lowest and highest values, the program's own choice of how far the wheel moves it.
LOWEST_CUTOFF = 0
HIGHEST_CUTOFF = 127
MIDDLE_CUTOFF = 64
MICROSECONDS_PER_MILLISECOND = 1_000
#: `until_us` is one microsecond past the event, so that the event is before it (SRV-74).
PAST_NOW_US = 1


class Sweep(App):
    def __init__(self, pages: dict[int, str]) -> None:
        super().__init__(pages)
        self.cutoff: dict[int, int] = {}
        #: Each connection's live sound's start on the kit's clock, set where the sound is announced.
        self.start_ms: dict[int, int] = {}

    async def on_input(self, connection: int, page: int, event: Event, sub: int) -> bool:
        if event.kind != "wheel" or connection not in self.start_ms:
            return False
        cutoff = min(HIGHEST_CUTOFF, max(LOWEST_CUTOFF, self.cutoff.get(connection, MIDDLE_CUTOFF) - event.dy))
        self.cutoff[connection] = cutoff
        time_us = (self.now() - self.start_ms[connection]) * MICROSECONDS_PER_MILLISECOND
        events: SoundSynth8EventsMember = {
            "kind": "synth8_events",
            "handle": LIVE8,
            "generation": 0,
            "until_us": time_us + PAST_NOW_US,
            "events": [{"event": "parameter", "time_us": time_us, "channel": 1, "set": {"vcf_cutoff": cutoff}}],
        }
        self.sound(connection_hears(connection), events)
        return True
```

The clamp is the program's own choice of how the wheel moves; the kit checks the value only against the schema's range for `vcf_cutoff`.

**synthD.** A stored synthD sound whose patch is the 60 control values in `synthd.md`'s fixed order (SD-22), given as the interface's bytes, sent inline (MIDI-60): the server writes them as the 60 control changes they stand for, at one tick (SD-26, MIDI-79). The same values are the one patch of the bank the sound names (MIDI-57).

```python
from neoteletext_app.protocol_types import SoundSynthdBankMember, SoundSynthdMember

BASS_BANK = 61


def bass_bank(values: bytes) -> SoundSynthdBankMember:
    return {"kind": "synthd_bank", "handle": BASS_BANK, "generation": 0, "bank": {"form": "patches", "patches": [{"form": "bytes", "bytes": values}]}}


def bass(values: bytes) -> SoundSynthdMember:
    return {
        "kind": "synthd",
        "handle": 60,
        "generation": 0,
        "banks": [BASS_BANK],
        "lift_banks": [],
        "length": {"tail_us": 500_000},
        "music": {"form": "events", "events": [
            {"event": "patch", "time_us": 0, "channel": 1, "patch": {"form": "bytes", "bytes": values}},
            {"event": "note_on", "time_us": 0, "channel": 1, "key": 36, "velocity": 110},
            {"event": "note_off", "time_us": 250_000, "channel": 1, "key": 36, "velocity": 64},
        ]},
    }
```

---

## 6. What is left out

1. **An Opus encoder in the Python kit** (PY-58): not part of the synthesizers' interface; recorded as a to-do for the owner, since it leaves the kits unequal.
2. **Helpers that build sounds** (a note layer, a scale, a tempo, a score object, a default patch, a parameter table): every one is instrument logic or a copy of the server's or a family document's data (DEC-6462 item 3, MIDI-22). A channel that wants one writes it in the channel. The TypeScript kit's `SynthScore`, `Synth6581Image`, `Synth6581Track`, the `*-patch.ts` packers and their kin are removed by `typescript.md` for the same reason and have no Python counterpart.
3. **Reading a Standard MIDI File or a system exclusive file in the kit**: the server reads them (MIDI-112). A program reads a file's bytes with `Path.read_bytes` and passes them.
4. **Checking a synthesizer message beyond the schema** in the kit (PY-38).
5. **Dataclasses, `pydantic` models or any run-time model library** for the types (PY-8; open question 3, answered by DEC-6474 item 3).
6. **The server's rules of TODO-1550 for the Python kit** (link targets, label bounds, packet checks and the rest): TODO-1550 is about text and pages, predates DEC-6462, and is blocked on the owner's word; this document neither does it nor withdraws it (section 9 item 3).
7. **A WebSocket transport** (DOC-2317, "Not built"): unchanged by this work.

## 7. What this document defines itself

1. **What the kit needs of the server's schema**, now `server.md`'s own requirement (SRV-6; DEC-6477): that every field carrying bytes as base64 is marked `"contentEncoding": "base64"`, so that the generator can type it `bytes` (PY-13). Reason: a description in words is not a contract a generator should read.
2. **The generator and the generated module**, their names (`scripts/generate_types.py`, `protocol_types.py`) and the construct table (PY-7 to PY-10). Reason: the brief leaves the method to this document; no existing tool is used because none can be added without approval and the constructs are few.
3. **Member types and their naming** (`…Member`, `SoundMember`; PY-10, PY-12), one rule with `typescript.md` TS-10. Reason: the split of what from to whom, as the TypeScript kit's `sound(to, member)` has it.
4. **`bytes` written as base64 by one rule** (PY-13). Reason: a program's bytes stay bytes; one rule, not per-field logic.
5. **The shared call list `docs/audio/kit-calls.tsv`** in neoteletext-common (PY-19). Reason: makes DEC-6462's equality checkable.
6. **The shared examples fixture `docs/audio/examples.jsonl`** (PY-48). Reason: the evidence that both kits send the same messages for the same program.
7. **The hearer names `connection_hears`, `page_hears`, `connections_hear`, `everyone_hears`** (PY-21), the Python spellings of the TypeScript kit's audiences, and the handler names, the TypeScript kit's with `on_` before them (`on_joined`, `on_opened`, `on_left_page`, `on_gone`, `on_refused`, `on_sound_built`; PY-18, PY-23 to PY-25), as `docs/audio/kit-calls.tsv` lists them.
8. **The kit's request numbers for `measure`** (PY-29), which the TypeScript kit already keeps for itself.

## 8. Open questions for the owner

Every question of this section was answered by DEC-6474 (18 November 2026): the first by the owner's own word, the second and third by the session under DEC-6462 and the owner's delegation; DEC-6477 records that answer for this document. The answer is recorded under each question, and the requirements cited follow it.

**1. May `jsonschema` become a run-time dependency of the Python kit?** *Answered by DEC-6474 item 1: option A; the owner approved `jsonschema` 4.25.1 and the four packages it requires by name (PY-35).* PY-35 validates every message before it is written with `jsonschema` 4.25.1, the validator the kit's tests already run through `uvx`. As a run-time dependency it brings `attrs`, `jsonschema-specifications`, `referencing` and `rpds-py` (the last with compiled Rust code, installed as a prebuilt wheel), each to be approved by name (DEVELOPMENT.md section 7) and pinned in `uv.lock`.
- Option A: approve the five; the kit validates at run time as the TypeScript kit does with Ajv. A mistake is caught where it is made, with the server's path and rule; the kits are equal in this too.
- Option B: no run-time dependency; the kit validates in its tests and its harness only (as today, DEC-1543 item 5), and at run time a program learns of a schema fault from the server's refusal (PY-24). The kits are equal in what they can send but not in where a mistake is caught.
- Option C: a validator written in the kit, generated from the schema like the types. No library, but a second implementation of JSON Schema's keywords to keep correct.
- **Recommendation: A.** It is the brief's choice, keeps one validator for the kit and its tests, and meets REQ-2769's intent for both kits; the dependencies are small and widely used.

**2. Does DEC-6462 amend DEC-1082 item 5 for the Python kit?** *Answered by DEC-6474 item 2: option A; the kit is kept fully equal to the TypeScript kit, which amends DEC-1082 item 5 for the kit; the old Hackaday channel gets only what protocol 13 forces (PY-64).* DEC-1082 item 5 (the owner, 28 October 2026) keeps the Python kit and the old Hackaday channel to the changes needed to keep running; TODO-1545 was cancelled and TODO-1550 blocked under it. DEC-6462 (the owner, 18 November 2026) makes the TypeScript and Python kits equals for the synthesizers. This document follows DEC-6462 for the kit (sections 4.2 to 4.6) and DEC-1082 for the channel (section 4.7, PY-64), and goes further than the synthesizers in closing the picture and measuring gaps (PY-52, PY-53) because "neither can do what the other cannot" is stated without limit.
- Option A: DEC-6462 amends DEC-1082 item 5 for the kit: the kit is kept equal to the TypeScript kit in everything; the channel stays "running, nothing more".
- Option B: the kit gains only the synthesizers' calls and protocol 13's forced changes; ReGIS, NAPLPS and measuring stay TypeScript-only, recorded as inequalities.
- **Recommendation: A**, recorded as a decision amending DEC-1082 item 5, with TODO-1550 then unblocked or cancelled by the owner.

**3. Generated types, or hand-written types checked against the schema?** *Answered by DEC-6474 item 3: option A, generated by the kit's own standard-library script, run with `uv run --frozen` (PY-7, PY-14).* PY-7 chooses generated `TypedDict`s from a generator of the kit's own.
- Option A (chosen): generated, stdlib-only generator, committed output, gate-checked.
- Option B: a third-party generator run by `uvx` (for example `datamodel-code-generator`), pinned; needs approval by name, and its output shape is not the kit's to choose.
- Option C: hand-written `TypedDict`s with a gate check comparing them to the schema; hundreds of hand-written fields for the synthesizers' patches, each a chance to drift until the check catches it.
- **Recommendation: A.**

## 9. Differences from what is built today

**The kit (`neoteletext-server-channels/kits/python`).**
1. `protocol-12.json` is replaced by `protocol-13.json`; `scripts/check.sh`'s `SCHEMA_FROM`, `SCHEMA_COPY` and `check_schema_copy` name `schema-13.json` (PY-1, PY-2).
2. `PROTOCOL` becomes 13, taken from the generated module; a `start` of another version ends the program (PY-4, PY-5).
3. New: `scripts/generate_types.py`, `src/neoteletext_app/protocol_types.py` and a commit-gate step comparing them (PY-7 to PY-14).
4. Every message builder in `app.py` builds a generated type; the bound literals `SAMPLE_RATES`, `AUDIO_CHANNELS`, `LAST_HANDLE`, `LAST_GENERATION`, `FULL_GAIN`, `LONGEST_FADE_MS`, `DEEPEST_DUCK`, `MOST_SAMPLES`, `PACKET_BYTES` and the bound checks through `whole` go (PY-16).
5. `sound_object`, `play` and `stop` are replaced by `sound(to, member)` (PY-20, PY-31); `regis`, `regis_links`, `regis_cursor`, `naplps` and `measure` are added (PY-27, PY-29); `now`, `wake_at` and `wake_in` are added (PY-46).
6. `Hearer(session=…)` and `session_hears` go; `connection_hears`, `connections_hear` and `everyone_hears` come (PY-21); handlers take connections, `on_close(session)` becomes `on_gone(connection)`, `on_join` becomes `on_joined`, `on_open` becomes `on_opened` and `on_leave` becomes `on_left_page` (PY-23); `_other_on` and the session bookkeeping go (PY-55, TODO-6445).
7. `refused` reaches `on_refused`; every server message type reaches a handler or the kit's own work; `sound_built` reaches `on_sound_built` (PY-24 to PY-26).
8. `send` validates against the schema with `jsonschema` (PY-35; DEC-6474), maps faults to the server's path and rule (PY-37), checks the line's length (PY-39), and writes `bytes` as base64 (PY-13); `textrules.py` loses its cookie rules (PY-40).
9. Every cookie call goes and the viewer calls come (PY-22; VS-401, VS-402).
10. `testing.py` gains `Harness` (PY-43 to PY-49); `tests/test_kit.py` moves onto it (PY-50); a test runs the examples against the server (PY-47).
11. `pyproject.toml`: `dependencies` gains `jsonschema==4.25.1` (PY-35; DEC-6474); `uv.lock` pins it and its four dependencies.

**The old Hackaday channel (`neoteletext-server-channels/hackaday`).**
12. Handlers and `Viewer` state per connection (PY-60); sounds sent per connection (PY-61); sound calls through `sound` (PY-62); the poll keyed on the viewer handle (PY-63); cookies gone from its tests (PY-65); nothing else (PY-64).

**neoteletext-common.**
13. New: `docs/audio/kit-calls.tsv` (PY-19) and `docs/audio/examples.jsonl` (PY-48).

**Records and conflicts found while writing this document.**
1. **DEC-1082 item 5 and DEC-6462 item 3 disagreed** about how far the Python kit may change; settled by DEC-6474 item 2 (open question 2).
2. **REQ-2769 and REQ-2772 name only the TypeScript kit**, and DEC-1543 item 5 records that the Python kit does not validate at run time; PY-35 makes the Python kit meet REQ-2769's rule too, and DEC-6474 says both requirements are to name both kits.
3. **TODO-1550** asks the Python kit to copy every rule of the server's `check.rs`, including Opus and packet checks; DEC-6462 item 3 and MIDI-22 forbid copies of the server's rules for the synthesizers, and REQ-2769 asks a kit to refuse what the server would refuse. For sound messages this document follows DEC-6462 (PY-38). Whether TODO-1550 stands for the text and page rules is the owner's (section 6 item 6).
4. **REQ-1061** says the Python kit does not encode Opus because of DEC-1082; under DEC-6462 that inequality needs the owner's decision (PY-58).
5. **The schema of protocol 12 does not mark base64 fields** (`contentEncoding`), which PY-13 needs; settled: `server.md` SRV-6 marks every bytes field of protocol 13 (DEC-6477).
6. **`server.md` and `typescript.md` were being written at the same time as this document**; settled by DEC-6477: every name in section 5 and every call name of section 4.3 was checked against them, and section 5's examples were corrected to `server.md`'s names (`time_us`, `until_us`, `length` holding `length_us` or `tail_us`, `music` tagged by `form`, `lift_banks`, `<name>_events`, events tagged by `event`, a parameter's `set`, bank select by `bank_msb` and `bank_lsb`, `play`'s required fields, synth6581's register fields of SRV-12, synth106's panel fields of SRV-30, a bank named by every sound of a family with banks) and to the TypeScript kit's handler names, so that both kits write the same lines (`docs/audio/examples.jsonl`).
