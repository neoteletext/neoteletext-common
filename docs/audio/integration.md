# How the synthesizers integrate into NeoTeletext

**Purpose.** This document specifies everything that happens to a synthesizer's sound between the moment the server has made it and the moment a viewer hears it: the audio profile's records that carry it, the teletext packets and the push connection that carry the records, how a page names its sounds and when they play, the engine's receiver that keeps and renders them, the browser's processes that turn them into sound, what happens when a viewer switches tabs, opens several tabs or turns the mouse wheel, the documentation items of `PROTOCOL.html` that must be written, the security analysis of the new input, the deployment, the measurements still owed, and the order in which the repositories change. It is the basis for implementing the receiving half of the synthesizers' interface and for integrating it across the repositories.

**Scope.** It covers the path from the server's output to the viewer's ears. It does not repeat the byte grammar of a block, the bank image, the restatement or any family's messages: `midi-architecture.md` (requirements MIDI-1 to MIDI-125) and the seven family documents specify those, and this document refers to them by requirement. It does not specify what a program sends the server, the JSON members of program protocol 13 or the server's internal work: `server.md` (requirements SRV-n, written beside this one) does that, and the TypeScript and Python documents describe the kits. Where this document needs something of the server, it states it as a property of the server's output, so that `server.md` and this document meet at the records.

**Status.** Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement.

Which instrument each synthesizer models is said once, in `synthesizers.md` in this folder, with the trademark statement.

**What this document decides, in brief** (each item is specified by the requirements cited):
1. One path, end to end: program, server, records, packets, carriage, the browser's decoder process (where alone a block is read and rendered), the trusted core, the sound helper, the device. Nothing is synthesised anywhere else, and nothing but the server writes a synthesizer's records on a channel's push connection (INT-1 to INT-4).
2. The records keep the audio profile's frame, record types and CONTROL record unchanged; the synthesizers use codecs 12 to 19, OBJECT extension tags 3 to 8 and the event codecs' DATA layout with its 4-byte byte offset, all as `midi-architecture.md` defines them; the server sends a connection a sound's banks, then its OBJECT, then its DATA, and every connection the same bytes (INT-5 to INT-13).
3. The three carriages (broadcast independent data lines, the push WebSocket, recordings) carry the same packets; the server sends a record's fragments together and paces a live sound's blocks to at most 500 milliseconds ahead of its clock (INT-14 to INT-19).
4. A sound belongs to a page through the CONTROL record's page field, as every sound of the audio profile does; a stored synthesizer sound starts from its first block, with a new synthesizer, each time its page is opened, and a live one joins at its newest block; a sub-page change does not touch a page's sounds (INT-20 to INT-29).
5. The receiver renders a synthesizer's sound as it plays, into a stream, a short lead ahead of what is heard, never into a sound held whole; this replaces the build of 16 November 2026, which rendered a stored sound whole at its first play (INT-30 to INT-40).
6. The browser moves its engine pin, names the seven family features, changes no sandbox and no process but the decoder, keeps a tab's sounds going untouched through a tab switch, keeps every tab independent, and keeps the wheel's sub-page steps from touching a page's sounds (INT-41 to INT-56).
7. The server checks with the receiver's own code, which needs its engine pin moved from `4ddd34b`, a commit older than every synthesizer (INT-57 to INT-62).
8. One program protocol 13 and one push protocol change (version 7 to 8), shared with `viewer-state.md`; the synthesizers themselves need no push protocol change and leave the record frame at version 2 (INT-63 to INT-69).
9. Every new reader has a fuzz target, listed with the reader (INT-70 to INT-78).
10. The server, the channels and the browser are deployed together; an old browser hears silence where a synthesizer plays, and a new browser hears silence in an old recording's synthesizer sounds (INT-79 to INT-83).
11. Render cost is measured for every family on the browser's three hosts and on the microcontroller targets, with a budget (INT-84 to INT-89).
12. The repositories change in one stated order (INT-90 and INT-91).
13. Every open question of this document was answered by DEC-6477 (section 17), and its disagreements with the other documents were settled by it (section 19): names follow `server.md`.

---

## 1. Sources

### 1.1 The documents of this set

| Document | What this document takes from it |
|---|---|
| `midi-architecture.md` (this folder) | The model, the block grammar (MIDI-23 to MIDI-38), the records of the event codecs (MIDI-39 to MIDI-49, tag 8 in MIDI-41, the DATA layout in MIDI-42, the tags in MIDI-48), long system exclusive and banks (MIDI-50 to MIDI-66), restatement, joining and loss (MIDI-93 to MIDI-103), stored sounds and the render budget (MIDI-104 to MIDI-106), the codec numbers (MIDI-107 to MIDI-110), protocol 13 (MIDI-111), the bounds and fuzz targets (MIDI-121 to MIDI-124). |
| The family documents: `synth6581-synth8580.md`, `synth7.md`, `synth106-synth60.md`, `synthd.md`, `synth53-synth52-synth51.md`, `synth8.md`, `synth80.md` | Each family's voices (for render cost), its bank sizes and its variant settings. |
| `server.md` (this folder) | What a program sends and the names of program protocol 13's members, which this document uses as `server.md` spells them where it names one (INT-66); the server's pacing of live blocks (SRV-77), its sending of banks and live sounds to connections (SRV-61, SRV-73, SRV-74) and its handles (SRV-59, SRV-72), which this document's requirements on the server's output agree with. |
| `viewer-state.md` (`~/devel/neoteletext-common/docs/`) | Program protocol 13's other changes (VS-351 to VS-354), the push protocol change from version 7 to 8 (VS-201), the state records 18 to 20 (VS-204), the one cut-over (VS-601) and its order of change (VS-602). |
| `synthesizers.md` (this folder) | The eleven names and the trademark statement. |
| `~/devel/neoteletext-common/DEVELOPMENT.md` | Sections 2.3 (a feature that adds an input has its own security analysis), 7 (licences), 8 (tests and fuzzing), 9 (gates), 11 (the engine pin), 12 (hosts and targets) and 14 (security process). |

### 1.2 Decisions

DEC-6410 (instruments are codecs of the audio profile; a block is 20 milliseconds of the instrument's input; instrument sounds are kept as their blocks and rendered as played, item 13; rendered in the browser's decoder process, item 15), DEC-6421 (what building the instruments changed on 16 November 2026: they play inside the audio receiver, item 1; a stored sound rendered whole at its first play, item 2, "Rendering as played remains the intended design and is owed"; the render budget, item 3), DEC-6429 (the analogue synthesizers), DEC-6453 (each instrument programmed by its adopted interface), DEC-6461 (NeoTeletext's own names, each a kind), DEC-6462 (the Rust server is the core; the kits are thin), DEC-6464 and DEC-6473 (one behaviour for common MIDI messages), DEC-6465 (answers to the open questions, among them new codes 12 to 19 and codes 3 to 11 retired), DEC-6471 (viewer state), DEC-6477 (the answers to this document's open questions and the settlement of the documents' disagreements, at the owner's delegation: the voice sink's stream operations carry the audio channel; one protocol 13 and one deployment; background and muted tabs keep rendering; names follow `server.md`; the server paces live blocks as INT-18 says), the kit's DEC-6443 (every browser tab is a session of its own to applications), neoteletext-common's DEC-1538 (tabs are isolated: nothing one tab does affects another), DEC-1527 (a connection's one selection), the browser's DEC-6447 (the wheel over a page steps its sub-pages unless its channel uses the wheel), DEC-611 (a live sound joins at its newest block), DEC-6398 (no local behaviour in the receiver: a note in answer to a key waits for the round trip), DEC-2022 (the protocol is defined by rdm's documentation items, from which `PROTOCOL.html` is generated), DEC-1447 (the push protocol's version agreed in HELLO and WELCOME), the engine's decision E.92 (a push WebSocket message is whole packets, never a bare record).

### 1.3 Requirements and documentation items as they stand

| Record | What it says today, and what this document does with it |
|---|---|
| REQ-36 (engine) | The record frame: profile version 2, a type, a 16-bit body length, the body, a CRC-32; an audio record at most 1,024 bytes. Unchanged (INT-5). |
| REQ-40 (engine), DOC-1857 | Broadcast carriage on data channel 12, packet 4/31, the Service Byte, the Control Byte, 34 record bytes a fragment, the 16-bit check. Unchanged (INT-15). |
| REQ-45 and REQ-3000 (engine), REQ-791 and REQ-795 (browser), DOC-1862 | A play naming a page is armed for that page, starts whenever the page is opened, fades out when it is left, and plays only while page sounds are on; the latest command wins; a play whose sound is not ready waits; progressive start; live sounds. Applied to synthesizer sounds (INT-20 to INT-29). |
| DOC-1859 | OBJECT, DATA and CONTROL as built, before the event codecs. To be revised (INT-66). |
| DOC-1860 | The codecs and rates, 0 to 2, with 3 to 255 reserved. To be revised (INT-66). |
| DOC-1951 | The record types 1 to 12. Not changed by this document (INT-5); the table already lacks types 13 to 17, which the engine uses (section 18 item 1). |
| DOC-1972 | The program protocol's `sound` message as it stood on 2 November 2026 (Opus and sampled kinds, `play`, `stop`, `gain`). To be revised for protocol 13 (INT-66). |
| DOC-2295 | Sound in the browser: where sound is read, every tab heard, live sounds, output, controls, and the voice operations' bounds. To be revised (INT-66, INT-69). |
| REQ-6411 (engine) | Codecs 3, 4 and 5 as built on 16 November 2026. Superseded by `midi-architecture.md` and this document (section 18). |
| REQ-6413 (server), REQ-6414 (TypeScript kit) | The program's instrument sound kinds and the kit's sound helpers as built. Superseded by `server.md` and the TypeScript document. |
| REQ-6415 (browser) | The browser renders instrument sounds in each channel's decoder process, with no change to the trusted core, the sound helper or the messages between them; the start delay to be measured. Revised by INT-33, INT-37 and INT-44. |
| TODO-6416 (engine) | Everything owed from the build of 16 November 2026, among it rendering as played and the fuzz targets. Carried by INT-33 and INT-71. |
| TODO-6446 (browser) | The trusted core's sound ledger drops a third tab's sounds silently once two tabs fill the shared total. Touched by INT-49. |
| TODO-6448 (browser) | The regression test owed for the tab-switch fix of 18 November 2026. Required by INT-48. |
| TODO-6450 (neoteletext-common) | The documentation items owed for the synthesizers, written for codes 3 to 11. To be revised to codes 12 to 19 and this document's list (INT-68). |

### 1.4 The code read

| Repository and commit | Files read, and what for |
|---|---|
| Engine, `neoteletext-renderer-teletext`, `livedevelopment` at `dd0421c6` | `crates/neoteletext-audio/src/record.rs` (record types 1 to 17, the OBJECT tags 1 to 7, `OBJECT_FIXED`, `DATA_FIXED`, `CONTROL_BYTES`, `is_channel_type`), `profile.rs` (`PROFILE_VERSION` = 2, `MAX_RECORD` = 1,024, `CHANNELS` = 4, `LIVE_RING_BLOCKS` = 32, `LIVE_LOOKAHEAD_BLOCKS` = 3, `LIVE_STALL_MS` = 2,000, `PROGRESSIVE_BUFFER_MS` = 40, `INSTRUMENT_LANES` = 4, `LEVEL_A_MINIMUM`, `LEVEL_B_MINIMUM`), `receiver/carriage.rs` (`push_message`: a WebSocket message of whole 42-byte packets; `push_packet`), `receiver/instruments.rs` (four lanes, `RENDER_BUDGET_BLOCKS` = 50, `prepare`, `conceal`), `port.rs` (the `VoiceSink` trait: `define`, `samples`, `forget`, `stream`, `stream_samples`, `start`, `stop`, `gain`, `concealed`), `ttau.rs` (the `.ttau` file of records back to back), `Cargo.toml` (the features `synth6581`, `synth7`, `analog`, `synth106`, `synthd`, `synth53`, `synth8`, `synth80`, none a default); `crates/neoteletext-audio-mix/src/mixer.rs` (a clamp after the sum); `crates/neoteletext-input/src/limits.rs` (`VERSION` = 7, the push protocol's version); `fuzz/Cargo.toml` and `fuzz/fuzz_targets/` (the audio targets build `neoteletext-audio` with its default features and `encode`, so with no synthesizer). |
| Browser, `neoteletext-browser`, `livedevelopment` at `7809799` | `native/Cargo.toml` (the engine pinned at `dd0421c6` through `file://`), `native/decoder/Cargo.toml` (the seven synthesizer features), `native/decoder/src/engine.rs` (`AUDIO_ARENA` = 4,194,304 bytes, `AUDIO_OBJECTS` = 256, `AUDIO_RECORDS` = 8, the receiver boxed at about 270 KB, `next_tick_ms`), `native/decoder/src/voice_sink.rs` (each voice operation a message for the trusted core, samples cut at `MAX_MESSAGE_SAMPLES`), `native/core/src/hearing.rs` (`MAX_HELD_SAMPLES` = 16 Mi samples, `MAX_TOTAL_HELD_SAMPLES` = twice that, `STREAM_HELD_SAMPLES` = 96,000), `native/sound/src/audio.rs` (one engine mixer per channel, the settings' sound and volume as each mixer's master, the device running only while a channel sounds), commit `9442e09` (a tab's page sounds go on when the viewer switches back to it), commit `42104b6` (the wheel over a page with sub-pages steps them unless its channel uses the wheel), `docs/architecture.md` sections 5, 6.1 to 6.5 and the sandbox table. |
| Server, `neoteletext-app-server`, `livedevelopment` at `df662b9` | `Cargo.toml` (the engine pinned at `4ddd34b`, from GitHub), `crates/teletext-runtime/src/protocol.rs` (`PROTOCOL` = 12, the `packets` message), `protocol/check.rs` (`check_packets`, which refuses the first fragment of a ReGIS or NAPLPS record but not of an audio record), `sound.rs` and `sound/instrument.rs` (the instruments' records written in the server because its pinned engine predates them), `channel.rs` (`targets`, `send_records`: a program's sound goes to the connections it names, once), `fuzz/fuzz_targets/` (`instrument_sound`, `opus_sound`, `protocol_reader`, `channel_input`, `session_cookie`, `websocket_reader`). |
| TypeScript kit, `neoteletext-server-ts-protocol`, at `6d54c3d` (release 14.0.0, protocol 12) | `src/channel/page-calls.ts` (`opened` and `leftPage` per tab-session since DEC-6443). |
| Audio demonstration channel, `neoteletext-server-channel-audiodemo`, at `28259da` | `src/openings.ts` and `src/audio-demo.ts` (at `opened` a page's bank, sounds and plays naming the page are sent to the tab that opened it). |

### 1.5 Standards

EN 300 708 (rdm source SRC-1775) clauses 6.4.1, 6.4.2, 6.5.8.1, 6.7.1, 6.7.1.1 and 6.7.3 to 6.7.3.3 and Tables 16, 19 and 21, as DOC-1857 and DOC-1862 cite them: the independent data lines, data channel 12, the user-defined service, the check word, the fade of a stalled sound and the duck table. The MIDI standards are cited only through `midi-architecture.md`, which read them (its section 1.5).

---

## 2. Terms

The terms of `midi-architecture.md` section 2 hold here (synthesizer, family, variant, kind, adopted interface, block, tick, event, event codec, bank, bank image, sound, stored sound, live sound, restatement, passed over and counted, refused, the receiver, the server). In addition:

- **Audio channel.** One of the audio profile's four channels, 0 to 3, on which a CONTROL record plays a sound. Never a MIDI channel.
- **Carriage.** A way records reach a receiver: the **broadcast carriage** (EN 300 708 independent data lines on data channel 12, packet 4/31, DOC-1857), the **push carriage** (the channel's push WebSocket, whose binary messages are whole 42-byte packets, the same packets), and **recordings** (a T42 file or a browser's `.ntrec` record of pushed packets, holding the same packets; and the engine's `.ttau` file of records back to back).
- **Push connection.** The channel's WebSocket on which pages and records come down and input goes up. Each browser tab has its own (DEC-1527, DEC-6443).
- **Push protocol.** The binary protocol of the push connection, agreed in HELLO and WELCOME (DEC-1447); its version is `neoteletext_input::limits::VERSION`, 7 at the engine's `dd0421c6`, and the WebSocket subprotocol `neottx.7`; `viewer-state.md` makes it 8 (`neottx.8`, VS-201).
- **Program protocol.** The JSON-lines protocol between the server and a channel's program, version 12 today (`PROTOCOL` in the server's `protocol.rs`).
- **Decoder process.** The browser's confined process, one per tab, that reads the channel's bytes, holds the audio receiver and renders pages and sound (the browser's architecture, section 6.1).
- **Trusted core.** The browser's process that owns the tabs, passes bytes to each decoder unread, checks every voice operation a decoder sends and passes it to the sound helper.
- **Sound helper.** The browser's confined process that holds samples, mixes each tab's sounds with the engine's mixer and plays them through the operating system's output device.
- **Voice operation.** One message from a decoder's voice sink (`neoteletext_audio::port::VoiceSink`): define a sound, give its samples, forget it, announce a stream, give a stream's next samples, start, stop or ramp an audio channel.
- **Stream.** A sound given to the sink as samples in order as they are made, held by the sound helper only a bounded time ahead (two seconds at 48,000 Hz, `STREAM_HELD_SAMPLES`), as a live Opus sound is today.
- **Lane.** One of the receiver's four synthesizer slots, one for each audio channel (`INSTRUMENT_LANES`), each holding the synthesizer instance of the sound playing on that channel.
- **Lead.** How far ahead of the sample being heard the receiver has rendered a synthesizer's stream.
- **Open page.** The page whose sounds play in a tab: the page zoomed on the wall, or else the page chosen by number or in the list (REQ-795). A tab has at most one.
- **Armed play.** A CONTROL play naming a page, held by the receiver for that page and started whenever the page is opened (REQ-45).
- **Event sound.** A sound of an event codec, 12 to 18.
- **Old browser, old receiver.** A browser, or an engine receiver, built before codes 12 to 19.

Numbers written `0x…` are hexadecimal. "Byte" is eight bits.

---

## 3. The path from the server to the viewer

```
channel's program ──JSON lines, program protocol 13──▶ server (neoteletext-app-server)
                                                         │ checks with the receiver's code, builds blocks, banks,
                                                         │ restatements; writes OBJECT, DATA, CONTROL records
                                                         ▼
                              records (record frame, version 2) cut into 34-byte fragments,
                              each in a 42-byte packet 4/31 of data channel 12, audio service 0
                                │                         │                          │
                     push WebSocket (whole packets)   broadcast lines          recordings (T42, .ntrec)
                                └─────────────┬───────────┴──────────────────────────┘
                                              ▼
browser: fetcher ──bytes, unread──▶ trusted core ──bytes, unread──▶ decoder process (one per tab)
                                                                     │ audio receiver: reassembly, store,
                                                                     │ commands, page arming, lanes;
                                                                     │ each lane a synthesizer rendering
                                                                     │ 960 samples a block, as it plays
                                                                     ▼
                                       voice operations (a stream's 16-bit samples, start, stop, ramp)
                                                                     │ checked again, bounded
                                                                     ▼
                                trusted core ──▶ sound helper: one engine mixer per tab, master volume,
                                                 tab mute, clamp after the sum ──▶ output device
```

**INT-1. One path.** A synthesizer's sound MUST reach a viewer only by the path above: the server writes the audio profile's records; packets 4/31 of data channel 12 carry them on every carriage; in the browser the decoder process of the tab alone reassembles, stores, reads and renders them; the decoder gives 16-bit samples at 48,000 Hz to the trusted core as voice operations; the trusted core checks each and passes it on; the sound helper mixes and plays. No process other than a tab's decoder process MUST read a record, a block, a bank image or a patch, or run a synthesizer.
- Reason: It is the path every sound of the audio profile already takes (DOC-2295), and it keeps outside input and the code that interprets it in the process built and confined for that (DEC-6410 item 15; REQ-6415).
- Source: DEC-6410 items 6, 13 and 15; DEC-6421 item 1; DOC-2295; the browser's architecture, sections 6.1 to 6.4.
- Verification: Inspection: only the decoder crate of the browser depends on `neoteletext-audio` with a synthesizer feature, and only the sound helper on `neoteletext-audio-mix`; a test in the decoder feeds a sound of each family as packets and checks samples reach the test's sink.

**INT-2. Nothing is synthesised before the browser.** The server and the channel's program MUST NOT send rendered samples of a synthesizer in place of its events; a synthesizer's sound on the wire MUST be its event blocks and banks, rendered only in the receiver.
- Reason: The events are a few kilobytes where the samples of two minutes are 11.5 MB (MIDI-4); the receiver's rendering is the point of the design (DEC-6410 item 13). A program that wants samples sends Opus, as it may for any sound.
- Source: DEC-6410 items 6 and 13; MIDI-4.
- Verification: Inspection of the server's sound path; the server's schema has no member that carries a synthesizer's samples.

**INT-3. The server is the one writer of a synthesizer's records on a push connection.** On the push carriage, every OBJECT, DATA and CONTROL record of an event sound or a bank, and every CONTROL record that plays one, MUST be written by the server from a program's typed message, checked as `server.md` and MIDI-21 require; a program MUST NOT be able to place such a record on a connection any other way.
- Reason: DEC-6462 makes the server the one implementation; a record that bypassed the server's checks would reach the receiver unchecked by anything but the receiver itself, and the program would learn of its fault from nobody.
- Source: DEC-6462 items 1 and 2; MIDI-13, MIDI-21.
- Verification: The test of INT-4; inspection of the server's message handlers.

**INT-4. The raw packets message carries no audio record.** The server's check of a program's `packets` message (raw 42-byte packets, DOC-1970) MUST refuse a packet that is the first fragment (fragment index 0) of a record of type 1, 2 or 3 (OBJECT, DATA or CONTROL), naming the packet's index and saying that sounds go in the sound messages, exactly as `check_packets` in `protocol/check.rs` already refuses the first fragment of a REGIS, DRAWING_LINKS, REGIS_CURSOR or NAPLPS record.
- Reason: Today a program can send a synthesizer's records, or any audio record, as raw packets, and the server forwards them unchecked (`check_packets` lists only types 14 to 17). That is the one way around INT-3. A record cannot begin without its first fragment, which carries the type byte, so refusing the first fragment refuses the record.
- Source: `protocol/check.rs`, `check_packets` and its comment ("no record of a sub-page's ReGIS, its drawing links or its cursor can begin here, so none passes unchecked", DEC-6335, REQ-6372); DOC-1951 (the type byte is the record's second byte, in its first fragment).
- Verification: A server test sends a `packets` message whose third packet is the first fragment of an OBJECT record and checks the refusal names `packets[2]` and nothing is sent; the test fails on the server's `df662b9`.

---

## 4. The records on the wire

The audio profile's records are unchanged in their frame, their types, their carriage and the CONTROL record. What the synthesizers add is defined in `midi-architecture.md`: the codecs 12 to 19 (MIDI-107), the OBJECT of an event codec (MIDI-40) and its extension tags 3 to 8 (MIDI-48, with tag 8 in MIDI-41), the DATA record of an event codec (MIDI-42, MIDI-43), the bank codec (MIDI-55) and the bank image (MIDI-56). This section states what the server writes for each kind, the order in which a connection receives the records, and what stays the same.

**INT-5. The record frame and the record types do not change.** Every record of a synthesizer's sound or bank MUST be framed as REQ-36 says (the profile version byte 2, the record type, a 16-bit big-endian body length, the body, a CRC-32 over header and body) and MUST be of type 1 (OBJECT), 2 (DATA) or 3 (CONTROL), at most 1,024 bytes (`MAX_RECORD`) with a body of at most 1,016 bytes (`MAX_BODY`). No new record type MUST be added for the synthesizers, and the profile version MUST stay 2.
- Reason: Decision A2 of the architecture: "no new transport". New codecs are what a receiver of today ignores safely (MIDI-109); a new record type or profile version would be refused or skipped as a whole, and would make the synthesizers' records unlike every other sound's.
- Source: Decision A2; REQ-36; REQ-4205; `profile.rs` (`PROFILE_VERSION` = 2); MIDI-39, MIDI-110.
- Verification: A test reads every record the server writes for one sound of each kind and each bank, and checks its version byte, type and length.

**INT-6. What the server writes in each OBJECT.** For each kind a program names, the server MUST write the OBJECT record's codec and extension tags exactly as this table says, with the rate code 7 (48,000 Hz) in every one, and the fields block bytes, samples and blocks as MIDI-40 (an event sound) or MIDI-55 (a bank) say:

| Kind | Codec | Tag 3 (1 byte) | Tag 4 (1 to 10 bytes) | Tag 5 (1 byte) | Tag 6 (1 byte) | Tag 7 (2 bytes) | Tag 8 (4 bytes) |
|---|---|---|---|---|---|---|---|
| synth6581, stored | 12 | bit 0 = 0; bit 1 the clock (0 PAL, 1 NTSC) | none | none | none | none | the total bytes of the blocks |
| synth8580, stored | 12 | bit 0 = 1; bit 1 the clock | none | none | none | none | the total |
| synth6581 or synth8580, live | 12 | as for stored | none | none | none | none | none |
| synth7, stored | 13 | none | the sound's banks, bank index 0 first | none | none | none | the total |
| synth106, stored | 14 | none | the banks | 0 | none | none | the total |
| synth60, stored | 14 | none | the banks | 1 | none | none | the total |
| synthD, stored | 15 | none | the banks | none | none | none | the total |
| synth53, stored | 16 | none | the banks | 0 | none | none | the total |
| synth52, stored | 16 | none | the banks | 1 | none | none | the total |
| synth51, stored | 16 | none | the banks | 2 | none | none | the total |
| synth8, stored | 17 | none | the banks | none | none | the key mode and the split key | the total |
| synth80, stored | 18 | none | the banks | none | none | none | the total |
| Any of codecs 13 to 18, live | as stored | none | the banks | as stored | none | as stored | none |
| A bank for codec 13 to 18 | 19 | none | none | none | the family's codec, 13 to 18 | none | none |

The label (tag 1) and the language tag (tag 2) MAY be written on any of them, as for every codec. The server MUST write tags 3 and 5 from the kind alone (MIDI-48), and MUST write tag 4 only with handles of banks it has sent the same connection (INT-11).
- Reason: The table is MIDI-48's applied to each of the eleven kinds, so that the server's encoder, the receiver's reader and the documentation item agree on one table; a kind sets its variant (DEC-6461 item 3).
- Source: MIDI-40, MIDI-41, MIDI-48, MIDI-55, MIDI-57, MIDI-107; DEC-6461 item 3; `record.rs` (tags 1 to 7 as built).
- Verification: A server test writes one sound of each of the eleven kinds, stored and live, and one bank of each family with banks, and checks every OBJECT byte for byte against this table; a receiver test reads each and checks the variant it plays.

**INT-7. What the server writes in each DATA record.** For an event sound the server MUST write DATA records as MIDI-42 says (the handle, the generation, the first block's number, the 4-byte big-endian byte offset of the first block within the sound, 0 for a live sound, then whole blocks each with its 2-byte length) and pack them as MIDI-47 says; for a bank, DATA records of the existing layout (the handle, the generation, the first block's number, then the bank image's bytes), as MIDI-55 says. A stored event sound's records MUST cover every block from 0 to the blocks field less one exactly once, in ascending order of block number, and a bank's every piece of its image.
- Reason: The receiver's store admits a stored sound by its total and finds each block by its offset (MIDI-41, MIDI-45); a record that left a gap or covered a block twice with different bytes would leave a sound incomplete or in conflict (MIDI-43, MIDI-44).
- Source: MIDI-42, MIDI-43, MIDI-47, MIDI-55.
- Verification: A server test of one stored sound of each family with blocks of lengths 0, 1, 1,005 and a mixture, reading the records back with the engine's store and checking every block's bytes; the record tests of MIDI-42.

**INT-8. The CONTROL record does not change.** A play, stop or set-gain of a synthesizer's sound MUST be the existing CONTROL record of 14 bytes of body (the audio channel 0 to 3, the 16-bit sequence number, the operation 1 play, 2 stop or 3 set gain, the handle, the generation, the gain 0 to 100, the fade in milliseconds at most 10,000, the flags 1 progressive, 2 loop and 4 after current, the duck code 0 to 6, and the page, 0x100 to 0x8FF or 0xFFFF for the whole service), with the meaning DOC-1859 and DOC-1862 give it. A play naming a bank (codec 19) MUST be refused by the server and ignored and counted by the receiver (MIDI-55).
- Reason: Playing, stopping, fading, ducking, looping and page arming are the audio profile's and apply to every codec unchanged (DEC-6410 item 6).
- Source: DOC-1859; DOC-1862; `record.rs` (`CONTROL_BYTES` = 14); DEC-6410 item 6; MIDI-55.
- Verification: The existing CONTROL tests, run with a synthesizer's sound; a server test refuses a play of a bank; a receiver test checks a play of a bank is counted and nothing sounds.

**INT-9. A sound's handle and generation.** A synthesizer's sound and a bank MUST each be an object of the audio profile with a handle (0 to 255) and a 16-bit generation, in the one space of handles the receiver keeps for its channel, shared with every other sound; a bank's handle MUST NOT at the same time be another sound's. Any change to a sound's records, or to a bank's image, MUST take a newer generation (MIDI-44).
- Reason: The store's admission, replacement and conflict rules work by handle and generation (DOC-1862); a bank is stored as a sound is (DEC-6410 item 11).
- Source: DOC-1862; MIDI-44, MIDI-55, MIDI-65.
- Verification: A receiver test replaces a bank by a newer generation while a sound plays and checks MIDI-65; a server test sends a bank and then a sound with the bank's handle and checks the sound replaces the bank in the server's bank table (`server.md` SRV-59), so that a later sound naming the handle is refused `unknown_bank` and the handle never names a bank and a sound at once.

**INT-10. The same bytes to every connection.** For a given handle and generation, the server MUST send every connection, and every carriage it writes, records whose bodies are identical byte for byte: the same OBJECT, the same DATA records and, for a live sound, the same block under each block number (MIDI-100). Only the record id of the packets (DOC-1857, byte 8), which counts records on each connection, MAY differ.
- Reason: A sound is one thing whoever receives it: a recording replays the same; a block number has one content (MIDI-44, MIDI-100); and each tab of one viewer is its own connection (DEC-6443), so two tabs of one viewer receive the same sound separately.
- Source: MIDI-44, MIDI-100; DOC-1951 (the record id counts per connection).
- Verification: A server test sends a live sound to three connections, two of them added later, and checks the records each received are identical but for record ids.

**INT-11. The order in which a connection receives a sound.** The server MUST send a connection: every bank a sound names, all of its records, before the sound's OBJECT (MIDI-57); a sound's OBJECT before any of its DATA records; and a CONTROL record that plays a sound only after that sound's OBJECT. A connection that is added to a live sound already running (a tab that opens its page later) MUST be sent the sound's banks, then its OBJECT, then its blocks from the next block the server writes; the server MUST NOT send it blocks already sent to others.
- Reason: A receiver that holds the OBJECT first can admit the sound and place each block as it comes (MIDI-45); banks before the sound mean a play never waits on a bank that was going to come anyway (MIDI-62); a play before its OBJECT would wait, which is allowed, but writing the OBJECT first makes the wait no longer than the sound's own records. Blocks already sent would arrive late and be played through as lost (MIDI-102); the restatement puts the new connection right instead (MIDI-96, MIDI-100).
- Source: MIDI-45, MIDI-57, MIDI-62, MIDI-96, MIDI-100; DOC-1862 ("A play whose sound is not ready waits").
- Verification: A server test checks the order of records sent for a stored sound with three banks and its play; a test adds a connection to a live sound at block 400 and checks it receives the banks, the OBJECT and blocks from 401 on, and that its receiver's synthesizer state equals the sender's within 50 blocks.

**INT-12. What a connection already holds.** The server MAY leave out of what it sends a connection a bank or a stored sound whose handle and generation it has sent that connection already, in full, since the connection opened. It MUST NOT leave out anything else.
- Reason: A program sends a page's banks and sounds each time a tab opens the page (section 6), and a receiver that holds them changes nothing on a repeat (DOC-1862: "A repeated OBJECT changes nothing"); leaving out a repeat saves its bytes. Whether to do so is the server's to choose (`server.md`); this document requires only that a sound reach a receiver complete.
- Source: DOC-1862; `openings.ts` of the audio demonstration channel (a page's members sent at every `opened`).
- Verification: A server test opens one page twice on one connection and checks the receiver's sound plays either way.

**INT-13. A record's fragments travel together.** On the push carriage and in every file the server writes, the server MUST send all the packets of one record consecutively, with no packet of another record between them.
- Reason: A receiver holds a bounded number of records in reassembly, at least 2 at audio Level A and 8 at Level B (`LEVEL_A_MINIMUM`, `LEVEL_B_MINIMUM`), and a new record evicts the oldest incomplete one (DOC-1857); interleaving the fragments of many records would make a small receiver lose records it could otherwise have read.
- Source: DOC-1857; `profile.rs`; `idl.rs` (`Reassembler`).
- Verification: A server test of a stored sound of 50 DATA records sent to two connections checks each connection's packets hold each record's fragments consecutively.

---

## 5. Carriage

**INT-14. Three carriages, one set of packets.** The records of a synthesizer's sound MUST travel on every carriage as the same 42-byte packets 4/31 of data channel 12, audio service 0 (DOC-1857, DOC-1951): on the push carriage as binary WebSocket messages of whole packets (the engine's decision E.92: never a bare record; `Receiver::push_message` refuses a message that is not whole packets); on the broadcast carriage as EN 300 708 independent data lines; in a recording as those packets in order. The engine's `.ttau` file of records back to back MAY carry them too, for tools.
- Reason: Decision A2: no new transport. A receiver then reads a synthesizer's sound from a broadcast, a recording or a push connection with one reader.
- Source: Decision A2; DOC-1857; REQ-40; `receiver/carriage.rs`; `ttau.rs`.
- Verification: A receiver test feeds the same sound as a push message, as packets one by one and as a `.ttau` file, and checks identical samples.

**INT-15. The packet.** Each packet MUST be as DOC-1857 says: data channel 12 and designation code 15 Hamming 8/4 coded; the Service Byte with bit 4 set (a user-defined service) and service 0; the Control Byte marking a record's first and last fragments; the record id (counting records on the connection modulo 256); the fragment index 0 to 240; 34 bytes of the record, the last fragment padded with zeros; and the 16-bit check over the 36 bytes before it, by the polynomial of EN 300 708 clause 6.5.8.1. A record of 1,024 bytes is 31 packets (30 of 34 bytes and one of 4 bytes and 30 bytes of padding).
- Reason: The existing carriage, unchanged (decision A2).
- Source: DOC-1857; REQ-40; EN 300 708 clauses 6.5.8.1 and 6.7.3, Tables 16 and 21.
- Verification: The existing carriage tests and wire vectors, and a vector of an event DATA record (INT-67).

**INT-16. Stored sounds on each carriage.** On the push carriage a stored sound's and a bank's records MUST be sent once to each connection that is to have them (INT-12), since the connection delivers them in order and whole. On the broadcast carriage, where a receiver may tune in at any time and lose any packet, a stored sound's and a bank's records MUST be repeated in a cycle for as long as a play may name them, and the receiver's store MUST take repeats as it does today: a block or record that arrives again with the same bytes changes nothing, and one with different bytes puts the sound in conflict (MIDI-44).
- Reason: The push connection is a reliable stream; a broadcast has no return path, and the audio profile already relies on repetition there (DOC-1862; the engine's `neottx sound --repeat`, REQ-96, REQ-4623).
- Source: DOC-1862; REQ-96; REQ-4623; MIDI-44.
- Verification: A receiver test feeds a stored synth7 sound's records twice in reverse order with every fifth packet lost the first time and checks the sound plays complete after the second.

**INT-17. Live sounds on each carriage.** A live sound's blocks MUST be sent once, in order of block number, each as soon as the server has written it and no sooner than INT-18 allows; they MUST NOT be repeated on any carriage. A receiver MUST keep them in its ring of 32 (MIDI-46) and play them as MIDI-101 and MIDI-102 say.
- Reason: A live block is due at one moment and is of no use after it (MIDI-102: a lost block that arrives later is not applied); the restatement, not repetition, repairs a loss or a late join (MIDI-96).
- Source: MIDI-46, MIDI-96, MIDI-101, MIDI-102; DOC-1862 ("Live sounds").
- Verification: The live-sound tests of MIDI-101 and MIDI-102.

**INT-18. A live sound is paced.** The server MUST NOT send a live sound's block more than `LIVE_SEND_LEAD_BLOCKS`, 25 blocks (500 milliseconds), before the moment that block is due by the live sound's clock, which starts when the server sends its first block and advances 20 milliseconds a block. Blocks a program's events message completes earlier (MIDI-20 allows an advance of up to 100 blocks in one message) MUST be held by the server and sent as the lead allows. `LIVE_SEND_LEAD_BLOCKS` MUST be defined once in the server, and an assertion MUST hold it below `LIVE_RING_BLOCKS − LIVE_LOOKAHEAD_BLOCKS` (29).
- Reason: The receiver keeps only the newest 32 blocks of a live sound (`LIVE_RING_BLOCKS`); a burst of 100 blocks would overwrite blocks not yet played. 500 milliseconds is the lead the audio demonstration channel's live page uses today (10 blocks every 200 milliseconds, ahead of play) with room to spare, and is short enough that a joining viewer hears the present.
- Source: MIDI-20, MIDI-46, MIDI-101; `profile.rs` (`LIVE_RING_BLOCKS` = 32, `LIVE_LOOKAHEAD_BLOCKS` = 3); `programming-the-synthesizers.html`, section 07 (the audio demo's 10 blocks every 200 milliseconds); DEC-6477 answer 2, which adopts this pacing for the server, as `server.md` SRV-77 builds it. The figure of 25 is NeoTeletext's own (section 16).
- Verification: A server test sends one events message advancing 100 blocks and checks no block leaves the server more than 25 blocks before it is due by a test clock; the compile-time assertion.

**INT-19. Broadcast capacity.** A channel that carries a synthesizer's live sound on the broadcast carriage MUST be given enough of data channel 12's lines for the sound's records, and the server, or the tool that writes the broadcast, MUST report a live sound whose records need more packets a second than the broadcast gives it rather than send it late. The packets a second a live sound needs MUST be measured (INT-89).
- Reason: A live sound of empty blocks costs few packets (a DATA record holds 503 empty blocks), but one of dense blocks can need a 31-packet record every 20 milliseconds, 1,550 packets a second, more than the lines of a broadcast field can carry; the push carriage has no such bound.
- Source: MIDI-30, MIDI-42; DOC-1857.
- Verification: The measurement of INT-89; a test of the report with a broadcast budget set below a sound's need.

---

## 6. How a page names its sounds, and when they play

A synthesizer's sound belongs to a page exactly as every sound of the audio profile does: by the page field of the CONTROL record that plays it (REQ-45, DOC-1862). This section applies those rules to synthesizer sounds and states the few that are new.

**INT-20. A page names its sounds by its plays.** A synthesizer's sound MUST belong to a page only through a CONTROL play whose page field names that page (0x100 to 0x8FF, EN 300 706 page numbers 100 to 8FF), which the receiver arms for that page (REQ-45); a play whose page field is 0xFFFF plays for the whole service, once, when accepted. Nothing in a page's own packets, in a sound's OBJECT or in a bank MUST bind a sound to a page.
- Reason: One rule for every codec; a sound may be armed for several pages by several plays, and a bank belongs to no page.
- Source: REQ-45; REQ-4516; DOC-1859 (the page field); DOC-1862 ("Pages").
- Verification: A receiver test arms one synth7 sound for pages 106 and 107 on two audio channels and checks it starts on each page's opening.

**INT-21. Sub-pages share their page's sounds.** A play's page field names a page, not a sub-page; a page's armed sounds MUST play whichever of its sub-pages is shown, and a change of sub-page (by the wheel, by the sub-page list, by a key, or by the channel's own rotation) MUST NOT stop, restart or re-arm them. The browser MUST NOT tell a decoder that its open page changed when only the sub-page changed.
- Reason: The CONTROL record has no sub-page field (DOC-1859), and a viewer stepping through a page's sub-pages is still on that page; restarting its music at each step would be heard as a fault.
- Source: DOC-1859; REQ-795 (the open page is a page); the browser's DEC-6447 and REQ-6349 (the wheel steps sub-pages).
- Verification: A browser test opens a page with ten sub-pages and an armed synth8 sound, steps through every sub-page with the wheel, and checks the decoder receives no `Opened` message and the sound's stream continues without a gap.

**INT-22. A stored synthesizer sound starts at its first block, every time.** When a page is opened, each sound armed for it MUST start as REQ-45 says; a stored event sound MUST start at block 0, with a new synthesizer instance in the lane of its audio channel (MIDI-3), playing from its banks as they stand at that moment (MIDI-65). When the page is left, the sound MUST fade out as REQ-45 says and its lane MUST be freed.
- Reason: The audio profile's rule ("it starts whenever that page is opened"); a new instance makes the sound the same on every opening, with no state carried from the last.
- Source: REQ-45; REQ-3000; MIDI-3, MIDI-65.
- Verification: A receiver test opens, leaves and opens again a page with an armed stored synthD sound and checks the samples of the two openings are identical from their first sample.

**INT-23. A live synthesizer sound joins at its newest block.** When a page with an armed live event sound is opened, the receiver MUST start it at the newest block it holds (DEC-611), with a new synthesizer instance whose parts stand as MIDI-61 says, and the server's restatements MUST put it right within 1,000 milliseconds (MIDI-96, MIDI-100).
- Reason: DEC-611, unchanged for synthesizers.
- Source: DEC-611; MIDI-61, MIDI-96, MIDI-100.
- Verification: The test of MIDI-100, run through the page arming of a receiver.

**INT-24. A play waits for what its sound needs.** A play of an event sound MUST wait, as a play whose sound is not ready waits today (DOC-1862), until the receiver holds: the sound's OBJECT; every bank its tag 4 names, complete (MIDI-62); and, unless the play is progressive, every block of a stored sound. A play of a live sound MUST wait for its OBJECT and its banks, then join as INT-23 says.
- Reason: A sound that started before its banks would play its first notes on default patches and then change timbre (MIDI-62); a stored sound that started before its blocks would stall.
- Source: DOC-1862; MIDI-52, MIDI-62.
- Verification: The test of MIDI-62, with a play sent before the sound's records.

**INT-25. A progressive play of a stored synthesizer sound.** A play with the progressive flag of a stored event sound MUST start once its banks are complete and its blocks have arrived contiguously from block 0 for at least `PROGRESSIVE_BUFFER_MS` (40 milliseconds, two blocks). A block that has not arrived when it falls due MUST be played through as a lost block (MIDI-102: notes released, the sustain pedal lifted, every parameter-number selection cleared, the block's 20 milliseconds rendered with no event) and counted as concealed; when it arrives later it MUST be stored for the next playing but not applied to this one.
- Reason: DOC-1862's progressive rule ("Samples of blocks not yet arrived are silence, and timing is never shifted"), applied to a sound whose blocks are events rather than samples: a missing event block cannot be silence, because the synthesizer goes on sounding, so it is treated as a live sound's lost block, which is the one rule for a block not there when due.
- Source: DOC-1862 ("Starting and loss"); `profile.rs` (`PROGRESSIVE_BUFFER_MS` = 40); MIDI-102. The treatment of a missing stored block is NeoTeletext's own (section 16).
- Verification: A receiver test plays a stored synth53 sound progressively with block 30 held back until block 60 has played, and checks notes are released at block 30, the counter, and that a second playing is complete.

**INT-26. The latest command wins, on four audio channels.** For each of a tab's four audio channels the receiver MUST keep only the newest command (DOC-1862), so at most four synthesizer sounds, each with its own instance, play at once in one tab, each on its own lane. A play that replaces a playing synthesizer sound on its audio channel MUST ramp the old one out as any play does, and MUST free its lane when the ramp ends.
- Reason: The audio profile's rule; the lanes are one per audio channel (`INSTRUMENT_LANES` = `CHANNELS`).
- Source: DOC-1862; `profile.rs`.
- Verification: A receiver test plays four synthesizer sounds of four families on the four audio channels, then a fifth on channel 2, and checks four play, the third's replacement ramps, and no lane is left held.

**INT-27. A program sends a page's sounds when a tab opens it.** A program that gives a page sounds MUST send them to a connection when it is told that the connection opened the page (the kits' `opened`, per tab-session since DEC-6443): first the banks, then the sounds, then the plays naming the page, as INT-11 orders them. The server and the kits MUST tell a program that a connection opened a page only when the connection's page number changes, never for a change of sub-page alone (INT-21).
- Reason: Each tab is its own connection and its own receiver (DEC-1527, DEC-6443), so each tab that opens a page must be sent its sounds; before DEC-6443 a second tab of one session was never told, and was silent (TODO-6442). A sub-page change is not an opening.
- Source: DEC-6443 item 1; `page-calls.ts` (`tellOpened`); `openings.ts` of the audio demonstration channel.
- Verification: A kit test with two tab-sessions on one page checks each is told `opened` once; a kit test steps one tab through three sub-pages and checks no further `opened`.

**INT-28. A play is not sent again to a tab on the page.** A program MUST NOT send a connection a second play of the same sound for the same page and audio channel while that connection stays on the page, since a new play, being a newer command, starts its sound again from the beginning (DOC-1862: "A play starts its sound on the channel, ramping out what played"). The TypeScript and Python documents MUST say so where they describe sending a page's plays.
- Reason: A play repeated at a moment the program did not intend (for example on a selection that did not change the page) restarts the music, which the viewer hears as the fault the owner found on 18 November 2026 for tab switches.
- Source: DOC-1862; TODO-6448.
- Verification: A channel test of the audio demonstration channel opens a page, sends a selection of another sub-page of it, and checks no second play is sent.

**INT-29. Page sounds off.** While the viewer's page sounds setting is off, no armed play MUST start, and a synthesizer sound armed for a page MUST NOT be rendered; a play for the whole service MUST be treated as REQ-45 treats it for every codec, the synthesizers adding no rule of their own. When the setting is turned on, the open page's armed sounds MUST start as on an opening.
- Reason: REQ-45 ("A page sound shall play only while the user's page sounds setting is on"), and nothing rendered that cannot be heard costs the decoder nothing. The engine's TODO-1146 item 5 records a fault where a waiting page play starts with the setting off; it applies to synthesizer sounds too and is fixed there.
- Source: REQ-45; REQ-795; TODO-1146 item 5.
- Verification: A receiver test with page sounds off opens a page with an armed synth80 sound and checks no stream is announced, then turns the setting on and checks it starts at block 0.

---

## 7. The receiver in the engine

**INT-30. One feature for each family.** The engine's `neoteletext-audio` MUST have exactly one Cargo feature for each family, named as its engine module: `synth6581`, `synth7`, `synth106`, `synthd`, `synth53`, `synth8` and `synth80`. Each MUST build the shared event-list reader (MIDI-23) and its family's synthesizer from `neoteletext-audio-instruments`; every feature but `synth6581` MUST also build the bank codec (codec 19) and the bank reader of its family. The feature `analog`, which exists today only so that the analogue synthesizers share synth7's slot block, MUST be removed, since every family now shares the event-list reader. None of the seven MUST be among the crate's default features, so that a microcontroller build that names none is unchanged.
- Reason: A family is a codec and a module (MIDI-1); a port chooses which it can afford (DEC-6421 item 12: "Neither feature is in the audio crate's default, so a microcontroller build is unchanged"). The variants of a family need no feature of their own (decision A5).
- Source: MIDI-1; decision A5; DEC-6421 item 12; `crates/neoteletext-audio/Cargo.toml` as built.
- Verification: `cargo xtask features` builds the crate with each feature alone and with none (the engine's decision E.61), and a test for each lists the codecs the build knows.

**INT-31. A build without a family.** A receiver built without a family's feature MUST read an OBJECT of that family's codec, and a bank naming that family in its tag 6, as an object of a reserved codec: ignored, counted in `Statistics::unsupported`, never a fault; its DATA records MUST be dropped as records of an unknown sound, and a play of it MUST wait as a play of a sound not held waits (DOC-1862), so the audio channel stays silent. Codes 3 to 11 MUST be read so by every build (MIDI-108).
- Reason: The profile's rule for an unknown codec, which is what makes the new codes safe for old receivers too (MIDI-109).
- Source: MIDI-107 to MIDI-109; DOC-1859 ("An object of a reserved codec, or one the build leaves out, is ignored and counted, never a fault"); `codec.rs` (`from_code`).
- Verification: For each family, a test built without it feeds one stored sound and a bank of that family and a play of the sound, and checks the counter, that nothing is stored for it and that nothing sounds; the test of MIDI-108.

**INT-32. Four lanes, each a new instance for each playing.** The receiver MUST keep `INSTRUMENT_LANES` lanes, one for each audio channel, and MUST give each playing of an event sound a synthesizer instance new at its start (MIDI-3), of the family its codec names and the variant its tags name. A lane MUST hold the state of one family at a time; the memory of the lanes MUST be bounded at build time by the largest family built and MUST be measured and stated (INT-40).
- Reason: Sounds start, stop, loop and join independently (MIDI-3); one lane per audio channel bounds the work and memory of a receiver whatever arrives (`profile.rs`, `INSTRUMENT_LANES` = `CHANNELS`). Today each lane holds one instance of every family built side by side, about 270 KB for seven families (the browser's commit `f8b0ea0`); holding one family at a time is allowed but not required.
- Source: MIDI-3; `receiver/instruments.rs` (`Lane`, `Lanes`); `profile.rs`.
- Verification: The test of MIDI-3; a test plays a synth7 sound and then a synth80 sound on one audio channel and checks the second starts from its default state.

**INT-33. A synthesizer's sound is rendered as it plays, into a stream.** The receiver MUST render each playing of an event sound block by block as it plays, in order from its starting block, and MUST give the samples to the port's voice sink as a stream (`VoiceSink::stream`, then `VoiceSink::stream_samples` for each block's 960 samples), for a stored sound exactly as for a live one. It MUST NOT render a stored event sound whole, nor define it to the sink as a sound of held samples (`VoiceSink::define` and `VoiceSink::samples`). This supersedes the build of 16 November 2026 (DEC-6421 item 2), which rendered a stored sound whole at its first play and defined it to the sink.
- Reason: DEC-6410 item 13 and MIDI-4: a sound is kept as its blocks and rendered as played, the ReGIS model the owner asked for ("can we use the same model used for regis to prevent memory issues"); DEC-6421 item 2 called this "the intended design" and recorded it as owed (TODO-6416). Rendering whole held a two-minute sound as about 11.5 MB of samples in the sound helper, applied the two-minute bound on held sounds to music, and repeated a loop's samples instead of playing on across the join (MIDI-105). A stream holds two seconds in the sound helper however long the sound (DOC-2295).
- Source: DEC-6410 item 13; DEC-6421 item 2; MIDI-4, MIDI-105, MIDI-106; TODO-6416; DOC-2295 ("a live sound counting as two seconds at 48 kilohertz").
- Verification: A receiver test plays a two-minute stored synth7 sound with a recording sink and checks only stream operations are given, that the receiver's memory does not grow with the sound's length, and that the samples equal those of rendering its blocks in order; the loop test of MIDI-105, through the sink.

**INT-34. The lead.** The receiver MUST keep each playing event sound's stream rendered ahead of its play position by at least `INSTRUMENT_LEAD_MIN_BLOCKS`, 2 blocks (40 milliseconds), and at most `INSTRUMENT_LEAD_MAX_BLOCKS`, 5 blocks (100 milliseconds), rendering further blocks only as the play position advances; and MUST say, through `Receiver::next_tick_ms`, the latest moment it must next be called to keep the lead. Both figures MUST be named constants of `profile.rs`, and an assertion MUST hold the larger below the samples a sink holds for a stream (two seconds).
- Reason: Rendering too far ahead delays every change the viewer should hear (a stop, a gain, a new play) and wastes work on a page about to be left; too little ahead risks an underrun on a busy host. 40 milliseconds is the progressive start's buffer (`PROGRESSIVE_BUFFER_MS`); 100 milliseconds bounds the added delay of a stop below what is heard as lag in answer to a key. Both are NeoTeletext's own and are to be confirmed by measurement (INT-88).
- Source: `profile.rs` (`PROGRESSIVE_BUFFER_MS` = 40); DOC-2295 (a stream holds two seconds); REQ-6415 item 5 ("it does not render ahead of what the sound helper will hold"). The two figures are NeoTeletext's own (section 16).
- Verification: A receiver test drives the clock in steps of 1 millisecond to 50 milliseconds and checks the rendered lead stays between the two bounds and the next tick asked for keeps it; the measurement of INT-88.

**INT-35. The render budget.** One call of the receiver MUST render at most `RENDER_BUDGET_BLOCKS` (50) blocks of all its lanes together, and MUST ask to be called again at once while blocks are owed (MIDI-106); in steady play a call renders only the blocks the lead needs, and the budget bounds the catch-up after the port has been slow.
- Reason: A sound of any length never holds the port for longer than the budget's blocks cost (DEC-6421 item 3), whatever a sender put in its blocks.
- Source: MIDI-106; DEC-6421 item 3; `receiver/instruments.rs` (`RENDER_BUDGET_BLOCKS` = 50).
- Verification: The existing render-budget test, run on event sounds of each family; a timed test of a call of 50 of the costliest blocks of each family, printing its time (INT-84).

**INT-36. Playing on across a loop, and ending.** A looped stored event sound MUST go on from its last block to block 0 in the same stream, without a new instance (MIDI-105). An unlooped stored event sound's stream MUST end after its last block's samples, and a play waiting with `after current` behind it MUST start when the sink reports those samples played, as it does for every sound. A stopped sound's stream MUST end at the end of its stop's fade, and its lane MUST be freed then.
- Reason: The architecture's loop rule; the audio profile's `after current` and stop rules, unchanged.
- Source: MIDI-105; DOC-1862 ("Operations").
- Verification: The loop test of MIDI-105; a test queues a sound with `after current` behind a stored synth106 sound and checks it starts within one block of the first's end.

**INT-37. Each playing is its own stream.** Two audio channels playing the same event sound (one handle and generation) at once MUST each be heard as its own playing, from its own instance and its own start. The engine's `VoiceSink` stream operations, and the browser's voice-operation message that carries them (DOC-2295, `protocol::audio::Audio::Stream` and its samples), MUST therefore name the audio channel with the sound, so that two streams of one sound are told apart, one sound playing on two audio channels at once (DEC-6477 integration answer 1); REQ-6415 MUST be revised to say so.
- Reason: Today a stream is named by its sound alone (`SoundId`, its handle and generation), which was enough when a live Opus sound was the only stream and two plays of it carry the same samples; two playings of one stored synthesizer sound started at different moments carry different samples, so one name would mix them. MIDI-3 requires each playing its own instance.
- Source: MIDI-3; `port.rs` (`stream`, `stream_samples` take a `SoundId`); `voice_sink.rs`; DEC-6477.
- Verification: A receiver test plays one stored synth7 sound on audio channels 0 and 1, the second 300 milliseconds after the first, and checks two streams whose samples are each the sound's from its own start.

**INT-38. What the receiver counts.** The receiver's `Statistics` MUST count, each in a field of its own that a port can read: objects of an unsupported or retired codec (`unsupported`, as today); blocks malformed (MIDI-33); events passed over (MIDI-34; this replaces `slots_passed_over`); patches refused and replaced by the default (MIDI-63); plays of a bank ignored (MIDI-55); and blocks concealed (`concealed`, as today, which counts a live block played through as lost and a missing block of a progressive play, INT-25). Every counter MUST saturate rather than wrap.
- Reason: MIDI-123 ("each fault it meets MUST be counted where the port can read it"); a count is how an author, or a test, sees why a sound was silent or wrong.
- Source: MIDI-33, MIDI-34, MIDI-55, MIDI-63, MIDI-123; `receiver.rs` (`Statistics`).
- Verification: The tests of each requirement named, each checking its counter.

**INT-39. The receiver stays sans-IO, `no_std` and integer-only.** The event-list reader, the bank readers, the lanes and every synthesizer MUST keep the engine's rules for its libraries (DEVELOPMENT.md section 6): no operating-system access, no floating point, no allocation in the receiver, no panic on any input (the crate root's denied lints), every bound a named constant.
- Reason: The same receiver runs in the browser's decoder and on microcontrollers (REQ-GEN-006, REQ-GEN-016), and it reads untrusted input (MIDI-123).
- Source: DEVELOPMENT.md section 6; MIDI-123; DEC-6410 item 14.
- Verification: The engine's `cargo xtask check-io`, its lints, and the build for `thumbv6m-none-eabi` with every family feature.

**INT-40. The receiver's memory, stated and asserted.** The bytes of a receiver built with every family (its store's arena, its tables, its ring slots for live event sounds at 32 × 1,009 bytes each, and its lanes) MUST be measured on each build and written in the engine's architecture document; the browser's decoder MUST keep the receiver on the heap as it does today; and a compile-time assertion in the engine MUST hold the size of a lane to the figure stated, so that a change that grows it is seen.
- Reason: With seven families the receiver grew from about 185 KB to about 270 KB and overflowed a test thread's stack (the browser's commit `f8b0ea0`); event lists, banks of up to 16,384 bytes read in place and live rings of the largest block change it again.
- Source: The browser's commit `f8b0ea0`; MIDI-45, MIDI-46, MIDI-103; DEVELOPMENT.md section 2.1 ("Measure, don't reason").
- Verification: The assertion; the figure in the engine's architecture document and in the commit that builds this.

---

## 8. The browser

**INT-41. The engine pin moves.** The browser MUST take the engine at the commit that builds the codecs 12 to 19 and this document's receiver, by a commit of its own, in every workspace that pins the engine (`native/Cargo.toml`, `native/fuzz/Cargo.toml`, `native/tuf/Cargo.toml` and `native/tuf/fuzz/Cargo.toml`), every `neoteletext-*` dependency naming the same `rev`, with each lockfile's diff touching only the engine's entries, and `docs/architecture.md` section 5 naming the new commit with what it changes for the browser.
- Reason: DEVELOPMENT.md section 11 ("Moving the pin"); the browser's requirement 2.5.
- Source: DEVELOPMENT.md section 11; `native/Cargo.toml` (pinned at `dd0421c6`).
- Verification: The browser's check that every `neoteletext-*` dependency names one `rev`; review of the lockfiles' diffs.

**INT-42. The decoder names every family.** The browser's decoder (`native/decoder/Cargo.toml`) MUST build `neoteletext-audio` with the seven family features of INT-30, and no process of the browser but the decoder MUST name any of them. The browser's fuzz workspace MUST build the decoder with the same features (INT-73).
- Reason: The decoder is the one process that renders (REQ-6415 item 1); every tab should hear every synthesizer a channel sends.
- Source: REQ-6415 item 1; `native/decoder/Cargo.toml` (the seven features of `dd0421c6`'s names).
- Verification: Inspection of every `Cargo.toml` of the browser; a decoder test plays one sound of each family.

**INT-43. No process gains a capability.** Adding the synthesizers MUST NOT widen any process's sandbox on any platform (the browser's architecture, the sandbox table: the decoder confined on macOS to its pipes, on Windows in a less privileged AppContainer with no capabilities, on Linux in an empty network namespace with nothing readable under Landlock and no sockets under seccomp), MUST NOT add a parser of outside input to the trusted core, the interface process or the sound helper, and MUST NOT add a message kind between processes, except the audio channel added to the stream operations by INT-37 and the receiver's counters that INT-53 adds to what a decoder tells the trusted core.
- Reason: The synthesizers need no file, socket, clock or device: the receiver is sans-IO (INT-39), and the decoder's clock is the one it already keeps for live sounds (REQ-6415 item 5). The sound helper keeps receiving only checked samples and voice operations (DOC-2295).
- Source: The browser's architecture, sections 6.1 and 6.5 and the sandbox table; DOC-2295; REQ-6415 item 2.
- Verification: The browser's sandbox tests unchanged and passing; inspection of the `protocol` crate's diff.

**INT-44. What the trusted core and the sound helper hold for a synthesizer.** The trusted core MUST check a synthesizer's stream as it checks every live sound's (DOC-2295: a stream takes only its next samples, every field bounded), and its ledger MUST count each stream as a live sound, `STREAM_HELD_SAMPLES` (96,000 samples, two seconds at 48,000 Hz), against the channel's bound of 32 MB and the total of 64 MB (`MAX_HELD_SAMPLES`, `MAX_TOTAL_HELD_SAMPLES`). The two-minute bound on a defined sound MUST NOT apply to a synthesizer's sound, which is never defined (INT-33). REQ-6415 item 2 MUST be revised to say so, and to name codes 12 to 19.
- Reason: Under INT-33 a tab plays at most four streams, 384,000 samples (768,000 bytes), however long its music, where the build of 16 November 2026 held up to 11.5 MB for each two-minute sound; the coupling between tabs that TODO-6446 found (a third tab's sounds dropped once two others fill the total) then cannot arise from synthesizer music.
- Source: DOC-2295; `hearing.rs`; REQ-6415 item 2; TODO-6446.
- Verification: A trusted-core test plays four synthesizer streams in each of three tabs and checks none is refused and the ledger's total is twelve streams' worth.

**INT-45. The gain a viewer hears.** The level of a synthesizer's sound MUST be, in this order and nowhere else: the synthesizer's output, including its controller 7 under MIDI-82's law and every level of its patch; then the CONTROL record's gain (0 to 100 per cent, ramped over its fade, at least 5 milliseconds) and the ducking of other audio channels by a play's duck code (DOC-1862, Table 19), applied in the sound helper's mixer as for every sound; then the tab's mixer master (the settings' volume 0 to 100, silent when sound is off or the tab is muted); then the sum of every tab's mixer, clamped to 16 bits after the sum (`neoteletext-audio-mix`, "a clamp after the sum"); then the device. No level MUST change faster than over 5 milliseconds (DOC-1862, "Levels"), except where the family's own click measure requires a slower one (MIDI-82, MIDI-83).
- Reason: One chain for every sound, so a synthesizer's music fades, ducks and mutes as speech and Opus music do; the program's two levers (controller 7 within the music, CONTROL gain for the whole sound) stay distinct.
- Source: MIDI-82, MIDI-83; DOC-1862 ("Levels"); DOC-2295 ("Controls"); `native/sound/src/audio.rs` (`master`); `crates/neoteletext-audio-mix/src/mixer.rs`.
- Verification: A test plays one synth53 sound at controller 7 = 64 and CONTROL gain 50 with a settings volume of 80 and checks the output level against the product of the three laws; the existing mixer tests.

**INT-46. A family's loudest sound does not clip alone.** Each family's output MUST stay below full scale for its loudest patch with every voice sounding at the highest velocity and controller 7 at 127, so that clipping happens only in the mixer's sum of several sounds, never inside one synthesizer; each family's peak level in that case MUST be measured and written in its family document.
- Reason: A synthesizer that clipped alone would distort before any gain could lower it; the mixer clamps the sum, which is the only place several sounds meet. synth7's mix today puts one full note 24 dB below full scale so that sixteen in unison do not clip (DEC-6421 item 8).
- Source: DEC-6421 item 8; `neoteletext-audio-mix` (the clamp after the sum).
- Verification: For each family, a test renders the loudest case and checks no sample reaches −32,768 or 32,767, printing the peak.

**INT-47. The decoder keeps the clock.** The decoder MUST call its receiver's tick when the receiver last asked to be called (`Receiver::next_tick_ms`), as it does for live sounds today, so that the lead of INT-34 is kept, and MUST otherwise sleep until written to; it MUST NOT poll on a fixed interval.
- Reason: REQ-6415 item 5; a program waits on what it needs, never by looking again on a timer (the browser's decision 46, DEVELOPMENT.md section 6, "Waiting").
- Source: REQ-6415 item 5; the browser's architecture, section 10 item 6 ("The decoder also wakes when its audio receiver next needs the time"); DEVELOPMENT.md section 6.
- Verification: A decoder test with a fake clock checks the wake-ups asked for while a synthesizer plays and that none is asked for while nothing plays.

**INT-48. A tab switch changes nothing a tab hears.** Choosing another tab, and choosing a tab again, MUST NOT change any tab's open page as its decoder knows it, MUST NOT send any decoder an `Opened` message, and MUST NOT stop, restart, pause or skip any sound in any tab: a background tab's synthesizer sounds MUST go on playing from where they are, rendered by its decoder, heard through its mixer, as DOC-2295 says ("a background tab keeps playing, as in a web browser"); and returning to a tab MUST find its music where it would have been had the tab stayed in front. The trusted core MUST pass a report of no open page to a tab's decoder only when the page open is that tab's own (the viewer choosing the wall), as the browser's commit `9442e09` does; and the regression test that TODO-6448 owes MUST exist and fail on the browser's `7058cfc`.
- Reason: The owner found on 18 November 2026 that clicking back on a tab restarted its music from the beginning: just after a tab is chosen the interface reports no page open until the tab's page is drawn, and the trusted core passed that on, so the receiver stopped the page's plays and started them again a moment later. Tabs are independent (DEC-1538 item 1); choosing one must not change another's sound, nor restart its own. With rendering as played (INT-33), a restart would also start the synthesizer anew, which is worse than replaying samples.
- Source: TODO-6448; the browser's commit `9442e09`; DEC-1538 item 1; DEC-6443; DOC-2295.
- Verification: The test of TODO-6448 (two tabs, switch away and back with `Opened(None)` then `Opened(Some(page))` from the interface, no `ToDecoder::Opened` sent; and the wall chosen on the active tab does send it); a decoder test checks a stream's samples are continuous across a switch; by hand, the audio demonstration channel's synth7 tune keeps playing across a switch away and back.

**INT-49. Several tabs are wholly independent.** Each tab MUST have its own push connection, decoder, receiver, store (4,194,304 bytes), four audio channels and four lanes (DEC-1527, DEC-6443, the browser's architecture section 6.3); nothing a sound does in one tab MUST reach another; two tabs on one page of one channel MUST each be sent the page's sounds and each hear them from their own start; and the sound helper MUST mix every tab through its own mixer, muted or heard as the viewer chose. The only resource tabs share MUST be the sound helper's total of held samples (`MAX_TOTAL_HELD_SAMPLES`), and a refusal under it MUST be reported as TODO-6446 asks, not silent.
- Reason: The owner's decision that tabs are completely independent (DEC-6443: "tabs should be completely independent"); DEC-1538 item 1. Under INT-44 synthesizer music cannot fill the shared total, but sampled sounds can.
- Source: DEC-6443; DEC-1538; DEC-1527; DOC-2295; TODO-6446.
- Verification: A test opens the audio demonstration channel's synth7 tune page in two tabs 2 seconds apart and checks each stream starts at its own block 0 and that a play sent to one tab's connection is heard only in that tab; the test of TODO-6446.

**INT-50. A tab that closes or leaves the channel.** When a tab closes, or navigates to another channel, its decoder MUST be stopped and the sound helper told to forget that tab's sounds, ending its synthesizer streams with the fade a stop uses, as for every sound today (DOC-2295, "When a channel's decoder is gone"). Nothing of it MUST outlive the tab.
- Reason: The existing rule, which covers synthesizer streams once they are streams (INT-33).
- Source: DOC-2295; the browser's architecture, section 6.3 ("A decoder and its fetcher are stopped when no tab uses their channel any more").
- Verification: A test closes a tab mid-tune and checks the sound helper's channel is forgotten and no stream operation follows.

**INT-51. The wheel and the pages.** The mouse wheel MUST affect a tab's synthesizer sounds only by what it does to the open page: over a page with sub-pages, a channel that does not use the wheel (no `push.wheel`, DEC-6447) steps the sub-pages, which leaves the page's sounds playing (INT-21); where the wheel steps pages (beside the page, or a page without sub-pages, REQ-6349), each step leaves one page, fading its armed sounds, and opens the next, starting its own (INT-22, INT-23). Over a channel that uses the wheel, the wheel MUST be sent to the channel as input, and any change to a synthesizer's sound in answer MUST come from the server as events of a live sound, after the round trip; the browser MUST NOT change a sound locally in answer to the wheel or a key.
- Reason: The wheel's meaning is the browser's DEC-6447 and REQ-6349, unchanged; there is no local behaviour in the receiver (DEC-6398): a note or a bend in answer to input waits for the round trip.
- Source: DEC-6447; REQ-6349; DEC-6398; the browser's commit `42104b6`.
- Verification: The browser's test `the_wheel_over_a_page_with_sub_pages_steps_them_unless_its_channel_uses_the_wheel`, extended to check no `Opened` message for a sub-page step; a test steps three pages with the wheel and checks each page's armed sound starts and the last's fades.

**INT-52. Silence where there is no device.** Where the system has no output device or no sound library, the browser MUST run silent as it does today (DOC-2295), and the decoder MUST go on rendering and giving streams as on any host, so that a sound is where its clock says when a device appears.
- Reason: The existing rule; a decoder that stopped rendering would need a new message from the sound helper to every decoder, which INT-43 does not allow, and the cost is bounded by the four lanes a tab has (INT-84 measures it).
- Source: DOC-2295 ("With no output device, or no sound library on the system, the browser runs silent").
- Verification: A test with the sound helper reporting no device checks the browser runs and the decoder's streams continue.

**INT-53. A tab's counters reach the channel's Log tab.** The decoder SHOULD send the trusted core the receiver's counters of INT-38 when they change, at most once a second, as bounded integers, and the browser SHOULD show them in the channel's Log tab beside the receiver's figures it shows today (the `AudioReceiver` message, the engine's REQ-AUD-017).
- Reason: When a sound is silent or wrong, the author needs to see that a block was malformed, a patch refused or a codec unsupported; the server refuses faults before they are sent (MIDI-21), so these counters mostly show a sender that is not the NeoTeletext server, or an old browser.
- Source: MIDI-123; the browser's architecture, section 6.4 (`AudioReceiver`).
- Verification: A test feeds a malformed block and checks the Log tab's figure.

**INT-54. The start delay is measured.** The time from a play's arrival in the decoder to the first sample of a synthesizer's stream given to the sound helper, and from there to the device, MUST be measured for each family on each of the browser's hosts and recorded in REQ-6415 item 6 with the date.
- Reason: REQ-6415 item 6 asks for it; with rendering as played the delay is the lead (INT-34) plus the sound helper's buffering, and it bounds how promptly a page's music starts and a key's note sounds.
- Source: REQ-6415 item 6; INT-34.
- Verification: A timed test printing the delays (INT-88).

**INT-55. Licences and credits.** The synthesizers MUST bring the browser no library from outside NeoTeletext; `deny.toml` MUST gain no entry for them; the licence texts and notices the browser ships for code translated into `neoteletext-audio-instruments` (today the Apache-2.0 licence and the notice of music-synthesizer-for-android, DEC-6420) MUST stay true for the engine commit pinned, and `CREDITS.md` MUST carry the engine's credits for that code (REQ-6415 item 4).
- Reason: DEVELOPMENT.md section 7; REQ-6415 item 4. If a family's rewrite to its adopted interface removes or adds translated code, the shipped notices must follow.
- Source: DEVELOPMENT.md section 7; REQ-6415 item 4; DEC-6420.
- Verification: The browser's licence check; review of `docs/licensing.md` and `CREDITS.md` against the engine's at the pinned commit.

**INT-56. The decoder's engine test.** The decoder's tests MUST include, for each family, a sound fed as packets through `Engine::feed` that reaches the test's sink as a stream of samples in order at 48,000 Hz, a play that waits for its bank, a page sound that stops when its page is left, and the four-tab case of INT-44.
- Reason: REQ-6415's verification, carried to the seven families and to streams; today only a synth6581 sound is tested there (`a_synth6581_sound_is_rendered_into_samples_for_the_sound_helper`).
- Source: REQ-6415, "Verification"; `native/decoder/src/engine/tests.rs`.
- Verification: The tests named.

---

## 9. The server's output

`server.md` specifies the server. This section states only the properties of its output that the receiving side relies on.

**INT-57. The server checks with the receiver's own code.** The server MUST take the engine at the commit that builds the codecs 12 to 19 (and at least the receiver's event-list reader, bank readers, record reader and store), MUST write every synthesizer's record with the engine's encoder and check every block, bank image and patch with the engine's reader, as MIDI-21 requires, and MUST delete its own writer of instrument records (`sound/instrument.rs`) and its own checks (`protocol/check/instrument.rs`) in the same change.
- Reason: Today the server pins the engine at `4ddd34b`, a commit older than every synthesizer, and so writes the instrument records itself and checks them with code of its own ("The engine this server is pinned to predates those codecs, so the records' bodies are written here", `sound/instrument.rs`); two implementations of one format disagree in time, which is the gap `synthesizer-wire-format.html` section 12 recorded ("DX7 bank checks"). MIDI-21 requires one.
- Source: MIDI-21; DEC-6462 items 1 and 2; the server's `Cargo.toml` (`rev = "4ddd34b…"`); `sound/instrument.rs`.
- Verification: Inspection: the server's diff deletes both modules; the property test of MIDI-21.

**INT-58. The server's engine comes from the published repository.** The server's engine pin MUST name a commit pushed to the engine's GitHub repository, since the server takes the engine from there; the engine's change MUST therefore be pushed before the server's pin moves.
- Reason: The server's `Cargo.toml` names `https://github.com/neoteletext/neoteletext-renderer-teletext`; Cargo reads a commit, never a working tree (the browser's architecture, section 5). It sets the order of section 14.
- Source: The server's `Cargo.toml`; DEVELOPMENT.md section 11.
- Verification: The server's build.

**INT-59. A refused message sends nothing.** When the server refuses a program's message about a synthesizer's sound, it MUST send no record of it to any connection, and a message it accepts MUST have every record checked before the first is sent, as the server does for every message today (`send_records`: "checked before any is sent").
- Reason: A receiver must never hold half of what a program meant; MIDI-21.
- Source: MIDI-21; `channel.rs` (`send_records`).
- Verification: A server test sends a stored sound whose last block is faulty and checks no packet reaches any connection.

**INT-60. Restatement is in the blocks.** Every restatement the server writes (MIDI-93 to MIDI-99) MUST be inside the sound's blocks, as events, and the server MUST NOT send any record, or any connection anything, to put a joining receiver right other than those blocks.
- Reason: A block number has one content for every receiver (MIDI-100, INT-10); MIDI-100 and DEC-6465 answer 4 rule out a restatement made for one joining viewer.
- Source: MIDI-96, MIDI-100; DEC-6465 answer 4.
- Verification: The test of MIDI-100, run through the server.

**INT-61. A live sound's audience.** A live sound's blocks MUST go to the open connections that each events message names (`server.md` SRV-74), each of which has been sent the sound's banks and OBJECT before its first block (SRV-61, SRV-73), and to no other; a program adds a connection by announcing the live sound to it again or by naming it in an events message (INT-11), and ends the sound for a connection by naming that connection in no later events message, after which that connection receives none of its blocks and its receiver stalls and fades it as MIDI-101 says, unless a stop is sent first.
- Reason: Each tab is its own connection (DEC-6443); a live sound shared by many tabs must still be one sound (INT-10), and a tab that left the page should not keep receiving it.
- Source: DEC-6443; MIDI-100, MIDI-101; `channel.rs` (`targets`); `server.md` SRV-73, SRV-74.
- Verification: A server test with three connections joining and leaving one live sound checks which receive each block.

**INT-62. The server counts what it sends.** The server MUST count, for each channel, the records and packets it sends for synthesizer sounds and banks, by codec, beside the existing count of sound records (`stats.sound_records`), on its administration listener.
- Reason: The cost on the wire is owed as a measurement (MIDI-49, INT-87) and must be visible in operation.
- Source: MIDI-49; `channel.rs` (`stats.sound_records`); DOC-2030 (the administration listener).
- Verification: A server test checks the counters after one sound of each family.

---

## 10. Protocol versions and the documentation items

**INT-63. One program protocol 13.** The synthesizers' program-facing messages (`server.md`) and the viewer-state messages of `viewer-state.md` (VS-351 to VS-354) MUST be one program protocol, version 13, with one generated schema (`protocol/schema-13.json`), one kit release of each language speaking it, and one moment of deployment; a program of version 12 MUST stop at `start`, naming both versions (MIDI-111). Neither change MUST be released as version 13 without the other; whichever is ready first waits (DEC-6477 integration answer 2, open question 2).
- Reason: The protocol has one number, raised on every change of shape (REQ-2215), and its two ends are released together (DOC-1927: "the program protocol is exact, as its two ends are released together"); two changes in flight at once must not take two numbers or one number with two meanings.
- Source: MIDI-111; VS-351 to VS-354, VS-601; REQ-2215; DOC-1927; `server.md` SRV-2; DEC-6477.
- Verification: The server's protocol test of the version; each kit's test that a version-12 program stops; the deployment check of INT-83.

**INT-64. The synthesizers need no push protocol change.** The synthesizers' records MUST travel in the push protocol as it stands, since they are records of the audio profile in packets 4/31 (INT-5, INT-14), which every version of the push protocol carries and which a receiver that does not know a codec ignores. The push protocol's version MUST be raised only by `viewer-state.md` (VS-201), once, from 7 to 8 (DEC-6477), and the browser release that speaks version 8 MUST be built with the seven family features (INT-42), so that every browser the new server admits plays every synthesizer.
- Reason: The audio profile is below the push protocol and versions itself by codec (MIDI-110); raising the push protocol for codecs would refuse old browsers for a change they already survive in silence. Tying the features to the release that the push protocol change forces on every viewer means no admitted browser is silent for a synthesizer.
- Source: MIDI-109, MIDI-110; VS-201; DEC-1447.
- Verification: Inspection of the push protocol's documentation items: none mentions a codec; the browser release's `Cargo.toml`.

**INT-65. The record frame stays at version 2, and a codec is its own version.** The record frame's profile version MUST stay 2 (INT-5), and any later change to what an event block or a bank image means MUST be made as MIDI-110 says: a new OBJECT extension tag or a skippable event where every receiver can ignore it, a new codec code otherwise.
- Reason: MIDI-110; a new frame version would make every receiver of today refuse every record, sound or not.
- Source: MIDI-110; REQ-36.
- Verification: Review of each later change.

**INT-66. The documentation items to write.** Before the deployment of INT-79, the documentation items of `PROTOCOL.html` (DEC-2022) MUST state the synthesizers in full, as rdm items with `documents` links to the requirements each states and citations of the sources each rests on, as this table lists:

| Item | Change | What it MUST state | Documents |
|---|---|---|---|
| DOC-1860, "Codecs and rates" | Revised | Codes 12 to 19 and what a block of each is (an event list of 0 to 1,005 bytes; a piece of a bank image); codes 3 to 11 retired and never reused; a receiver built without a family ignores its code. | MIDI-107 to MIDI-110; INT-30, INT-31 |
| DOC-1859, "OBJECT, DATA and CONTROL" | Revised | The OBJECT fields' meaning for event codecs (block bytes the longest block, samples and blocks); the extension tags 3 to 8 with their codecs and values (the table of INT-6); the DATA layout of event codecs (the 4-byte offset, the 2-byte length of each block) and its faults; the bank's DATA layout; that CONTROL is unchanged and a play of a bank is ignored. | MIDI-39 to MIDI-48, MIDI-55; INT-5 to INT-9 |
| New: "Event blocks" | New, normative | The grammar of a block, the minimal variable-length quantity, the tick and an event's sample, the system exclusive event, the messages never carried, the bounds of a block, framing and content errors, the order of events at one tick, and that a sound's blocks are a Standard MIDI File track. | MIDI-5, MIDI-7, MIDI-8, MIDI-11, MIDI-12, MIDI-23 to MIDI-38 |
| New: "Banks" | New, normative | The bank codec, the two forms of a bank image, which patch is which program, a sound's 1 to 10 banks, waiting for a bank, reading a bank's bounds, the default for a faulty patch, bank select, banks fixed for a sound's life, a dump lifted out of music. | MIDI-50 to MIDI-66 |
| New: "Synthesizer sounds in a receiver" | New, normative | A new instance for each playing; rendering as played into a stream with its lead; the render budget; looping; a progressive play's missing block; joining a live sound and the restatement it relies on; a lost block; the counters. | MIDI-3, MIDI-4, MIDI-93 to MIDI-106; INT-22 to INT-26, INT-32 to INT-38 |
| New: "The common MIDI behaviours" | New, normative | The common layer and the one rule for reset all controllers, all notes off, all sound off, the sustain pedal, velocity 0, the mode messages, pitch bend range by RPN 0, pitch bend resolution and volume. | MIDI-9, MIDI-71, MIDI-82, MIDI-84 to MIDI-92 |
| New: one item for each family: "synth6581 and synth8580", "synth7", "synth106 and synth60", "synthD", "synth53, synth52 and synth51", "synth8", "synth80" | Seven new, normative | The family's codec and variant tag; its channel map; the complete table of the messages it acts on (every status, controller, NRPN, RPN and system exclusive message, with ranges); its patch form byte for byte; its bank image; its program mapping; its default patch; its restatement; its response to reset all controllers for every controller it takes; what a lost block does. | Each family document's requirements (S6581-n, S7-n, S106-n, SD-n, S53-n, S8-n, S80-n) |
| DOC-1862, "What a receiver does with sound" | Revised | That a play of an event sound waits for its banks; the progressive rule for a missing event block; that a play of a bank is ignored. | INT-24, INT-25, INT-8 |
| DOC-2295, "Sound in the browser" | Revised | That synthesizers are rendered in each tab's decoder as streams, the stream's bound in the sound helper, the stream named with its audio channel, that a tab switch changes no tab's sound, and the features the browser builds. | INT-33, INT-37, INT-42 to INT-50 |
| DOC-1972, "Sounds" (the program protocol's `sound` message) | Revised for protocol 13 | Every member of program protocol 13 for synthesizers, with every field, range and refusal rule, as `server.md` names them: the kinds `<name>`, `<name>_live`, `<name>_events` and `<name>_bank`; a patch in named fields or as the interface's bytes (`form` `fields` or `bytes`); a bank as a list of patches or as a dump (`form` `patches` or `bytes`); a stored sound with its `music` (`form` `events` or `midi_file`), its `length` (`length_us` or `tail_us`), its `banks` and its `lift_banks`; events tagged by `event`, timed by `time_us`; a live sound's announcement; the events message with `until_us`; the report `sound_built`, with the messages dropped from a file; `refused`'s `sound`; and `play`, `stop` and `gain`, unchanged. Where `server.md` makes several members, one item for each group, beside this one. | `server.md`'s SRV requirements; MIDI-13 to MIDI-22, MIDI-112 to MIDI-122 |
| DOC-1968 and DOC-1970 (from the server to a program; from a program to the server) | Revised | Protocol 13's lists of messages, with the synthesizers' members and the refusals they add. | `server.md`; VS-351, VS-352 |
| DOC-1963, "The wire vectors" | Revised | The rows of INT-67. | INT-67 |

DOC-1857 (data channel 12) and DOC-1951 (the records) MUST NOT change for the synthesizers.
- Reason: The protocol is defined only by rdm's documentation items (DEC-2022); the owner noticed on 18 November 2026 that `PROTOCOL.html` does not mention the synthesizers (TODO-6450). The items state the rules; their reasons stay in the requirements and decisions they document (rdm's rule for items).
- Source: DEC-2022; TODO-6450; DEVELOPMENT.md section 3.7.
- Verification: `PROTOCOL.html` generated from the items lists codes 12 to 19, every tag, the event block's grammar and each family's messages; a review checks each item's byte layouts against the engine's encoder and reader and the server's schema; every item has its `documents` links.

**INT-67. The wire vectors.** `wire-vectors.tsv` in neoteletext-common, and the engine's copy of it, MUST gain rows of kind `record`, each a 42-byte packet 4/31 with its record id, for: the OBJECT of a stored sound of each codec 12 to 18 with its tags, and of a bank of codec 19; the DATA record of a stored synth7 sound holding blocks of 0, 3 and 165 bytes, with its offset; the DATA record of a live synth80 sound, offset 0; the first DATA record of a bank; and a CONTROL play of a synth7 sound armed for page 0x106. A record longer than one packet MUST be given as its packets in order, one row each. The engine and the server MUST read and write every row, as they do every row today.
- Reason: The wire vectors are the protocol's byte-level examples that every implementation runs (DOC-1963; DEC-1759 lesson 3).
- Source: DOC-1963; `wire-vectors.tsv`.
- Verification: The engine's and the server's existing tests over every row, passing with the new rows; the engine's commit gate comparing its copy.

**INT-68. TODO-6450 is revised.** TODO-6450 MUST be revised, as a complete new version, to name codes 12 to 19 and the items of INT-66 in place of codes 3 to 11 and the members of protocol 12, and linked to this document's requirements.
- Reason: It was written on 18 November 2026 before codes 12 to 19 and DEC-6462; documenting codes 3 to 11 now would document what is retired.
- Source: TODO-6450; DEC-6465 answer 1; DEC-6462.
- Verification: Review of the revised record.

**INT-69. The reference pages are replaced.** `synthesizer-wire-format.html` and `programming-the-synthesizers.html` in `~/devel/synthesizer-reference/` describe the format and the kit as built before this change; they MUST be regenerated from the new code, or replaced by links to `PROTOCOL.html` and the TypeScript and Python documents, in the same step as the deployment, and the kit's published page "Programming the NeoTeletext synthesizers" MUST link to the items of INT-66 for the wire.
- Reason: A reference that describes retired codecs misleads; `midi-architecture.md` section 21 item 17 already says so.
- Source: `midi-architecture.md`, section 21 item 17; TODO-6450 ("How it will be checked").
- Verification: Review after deployment.

---

## 11. Security analysis

DEVELOPMENT.md sections 2.3 and 14 require a feature that reads outside input to have its own security analysis, applied before adoption, and every reader of outside input to be bounded and fuzzed. The synthesizers add readers in two places: the engine's receiver, which every browser tab runs on bytes from any channel, any broadcast and any recording; and the server, which reads what a channel's program sends. This section is the analysis of the receiving side and of the server's new readers as the receiving side depends on them; `server.md` bounds the server's work.

**INT-70. The analysis is recorded and kept.** On adoption, this section's analysis MUST be carried into the engine's `THREAT-MODEL.md`, the browser's `docs/security-analysis.md` and the server's security document, each with the date, and a security review MUST be recorded when the receiver of this document is built (the engine's REQ-SEC-023: a review closes each milestone); every fault it or the fuzzing finds MUST get a regression test that fails on the faulty code.
- Reason: DEVELOPMENT.md section 14; the build of 16 November 2026 owed its analysis and fuzz targets (DEC-6421, "What was not done"; TODO-6416).
- Source: DEVELOPMENT.md sections 2.3 and 14; DEC-6421; TODO-6416.
- Verification: The documents' diffs and the review record.

**INT-71. Every reader and its fuzz target.** Each reader in this table MUST have the fuzz target named, with a corpus holding every input that ever found a fault, replayed first (DEVELOPMENT.md section 8), run by its repository's full gate:

| Reader | Repository and code | Its input, and who can send it | Fuzz target | Today |
|---|---|---|---|---|
| The packets and the reassembly of records | Engine, `idl.rs`, `receiver/carriage.rs` | Packets 4/31 from any carriage | `audio_packets`, `audio_messages` (existing) | Exists; unchanged |
| The record reader, the store and the commands, with OBJECT tags 3 to 8, the event codecs' DATA layout and the bank codec | Engine, `record.rs`, `store.rs`, `store/live.rs`, `receiver/play.rs` | Records from any carriage | `audio_records` (existing), built with all seven family features | Exists, but built without any synthesizer |
| The event-list reader, with each family's synthesizer behind it, including every system exclusive message a family reads inline | Engine, the event-list reader and each family's message handling in `neoteletext-audio-instruments` | The bytes of a block | `audio_event_blocks` (new): the first byte chooses the family and its variant, the rest is blocks rendered in turn | None |
| Each family's bank reader and patch check | Engine, each family's bank reader | A bank image of up to 16,384 bytes | `audio_banks` (new): the first byte chooses the family, the rest is the image, then 256 program changes | None |
| The browser's decoder engine with its receiver | Browser, `native/decoder` | A channel's bytes | `engine` (existing), with the decoder built with the seven features and a seed corpus holding one sound of each family | Exists; seeds owed |
| The voice operations between the decoder, the trusted core and the sound helper | Browser, `protocol` crate | A decoder's messages | `decoder_messages`, `sound_messages`, `sound_requests` (existing), extended for INT-37's audio channel and INT-53's counters | Exists; to be extended |
| The program's JSON lines | Server, `protocol/read.rs` | A channel's program | `protocol_reader` (existing), with protocol 13's synthesizer members | Exists; to be extended |
| The checks and encoders of synthesizer messages: patches in named fields and as bytes, banks as lists and as dumps, events, their packing into blocks and records | Server, the modules `server.md` names, using the engine's encoder and reader | A channel's program | `synth_sound` (new), replacing `instrument_sound` | `instrument_sound` exists for the old kinds |
| The Standard MIDI File reader | Server | A channel's program | `midi_file` (new) | None |
| A live sound's events messages over time, with its restatement | Server | A channel's program | `synth_live` (new): a sequence of events messages for one live sound, checking that every block written passes the receiver's reader and that a fresh synthesizer fed the latest restatement holds the sender's state | None |

The kits read no outside input of their own for synthesizers (MIDI-22) and have no target.
- Reason: DEVELOPMENT.md section 8: "Every reader of outside input has a fuzz target"; MIDI-124 names the engine's and the server's; the browser's and the live sound's complete the list.
- Source: DEVELOPMENT.md sections 8 and 14; MIDI-124; `fuzz/fuzz_targets/` of the engine, the browser and the server.
- Verification: Each repository's full gate runs every target named for its stated time; inspection of each target's code against this table.

**INT-72. The engine's fuzz workspace builds every family.** The engine's `fuzz/Cargo.toml` MUST build `neoteletext-audio` with the seven family features as well as its default features and `encode`, so that `audio_records`, `audio_packets` and `audio_messages` reach the synthesizers' code.
- Reason: Today it names `["default", "encode"]`, so no fuzz target reaches any synthesizer, though the browser builds all seven.
- Source: The engine's `fuzz/Cargo.toml`.
- Verification: Inspection; a fuzz run whose coverage report shows the event-list reader reached.

**INT-73. The browser fuzzes what it ships.** The browser's fuzz workspace MUST build the decoder with exactly the features the shipped decoder has, and its `engine` target's seed corpus MUST hold, for each family, a recording of one stored and one live sound with its banks and plays, as packets.
- Reason: A fuzz target that does not build what ships tests something else; seeds of real sounds let the fuzzer reach the synthesizers past the record checks.
- Source: DEVELOPMENT.md section 8; `native/fuzz/Cargo.toml` (the decoder by path, so its features).
- Verification: Inspection; the full gate's fuzz run.

**INT-74. Work is bounded per block, and measured against a budget.** The work of one block MUST be bounded whatever it holds (MIDI-106), and each family's costliest block that the server and the receiver allow (256 events of the family's costliest kind, every voice sounding, its longest system exclusive message, a program change against its largest bank) MUST render in at most `BLOCK_RENDER_BUDGET_MS`, 5 milliseconds, on each of the browser's hosts in a release build; a family that cannot MUST lower its own bound on events a block, as MIDI-31 allows, until it does.
- Reason: A tab has four lanes; four of the costliest blocks must render within the block's 20 milliseconds, and DEC-6410 asks for the instruments to be reconsidered if they "cost more than a decoder process can give four times over". A hostile channel can then make one tab's decoder busy for at most the real time of its own sound, never more; other tabs are other processes.
- Source: DEC-6410 ("When to reconsider"); MIDI-31, MIDI-106; DEVELOPMENT.md section 14. The figure of 5 milliseconds is NeoTeletext's own, a quarter of a block (section 16).
- Verification: The timed tests of INT-84, each holding its family to the budget and printing its time.

**INT-75. Memory is bounded.** Everything a receiver holds for synthesizers MUST be within bounds fixed at build time: the store's arena (4,194,304 bytes in the browser) for stored sounds and banks, a stored event sound at most 960,000 bytes of blocks plus its tables (MIDI-45), a live event sound's ring of 32 × 1,009 bytes (MIDI-103), a bank image at most 16,384 bytes read in place, at most 10 banks a sound, and four lanes; and the sound helper at most two seconds of samples a stream (INT-44). Nothing a sender does MUST make a receiver allocate.
- Reason: All input is untrusted (DEVELOPMENT.md section 6); a receiver must survive any sender with its memory fixed.
- Source: MIDI-41, MIDI-45, MIDI-46, MIDI-55, MIDI-57, MIDI-103, MIDI-121; DOC-2295; the browser's `engine.rs`.
- Verification: The bound tests of MIDI-121; the measurement of INT-40.

**INT-76. The threats.** The analysis MUST address each threat in this table, with the defence named and the requirement that holds it, and MUST be revised when any of them changes:

| Threat | Who | Defence | Requirements | What remains |
|---|---|---|---|---|
| A malformed record, block, bank or patch that crashes, hangs or corrupts the receiver | Any sender: a hostile channel, a broadcast, a recording, a network attacker on an unencrypted connection | Every reader bounded, no panic, no allocation, framing and content errors passed over and counted, fuzzing | MIDI-23 to MIDI-34, MIDI-53, MIDI-121, MIDI-123; INT-39, INT-71 | A fault the fuzzing misses stops one tab's decoder, which the trusted core replaces (the browser's architecture, section 6.4); its sandbox holds it |
| Processor exhaustion by dense blocks, many events, long system exclusive or program changes against large banks | A hostile channel | 256 events a block, family bounds, four lanes, the render budget of 50 blocks a call, the per-block budget | MIDI-31, MIDI-66, MIDI-106; INT-35, INT-74 | One tab's decoder busy for the real time of its own sound |
| Memory exhaustion | A hostile channel | The fixed arena and its admission rule; the ring; banks and their count bounded; streams of two seconds | INT-44, INT-75 | None beyond what any sound can already take |
| A sound louder than a viewer chose, or a sudden step of level | A hostile channel | No synthesizer clips alone; every level ramps over at least 5 milliseconds; the settings' volume, the tab's mute and mute-all apply | INT-45, INT-46; MIDI-82, MIDI-83 | A channel can play at full scale, as it can with Opus today |
| A sound altered by a second sender, or a store put in conflict | A broadcast sender other than the channel's; on a push connection only the channel's own server sends | Generations, the conflict rule (a different block under one generation stops the sound until replaced) | MIDI-44; INT-9, INT-16 | On a broadcast, a sender with the channel's service can replace its sounds, as with every sound today |
| A program's records that bypass the server's checks | A channel's program | The raw packets message refuses audio records; the server is the one writer | INT-3, INT-4 | None |
| One tab's sound affecting another | A hostile channel in one tab | A decoder, receiver and store per tab; the ledger's shared total not reachable by streams; refusals reported | INT-44, INT-49; TODO-6446 | The shared total of held samples, for sampled sounds |
| A receiver of another version misreading a sound | Any sender, any old browser | New codec codes; unknown codes ignored; the frame unchanged | MIDI-107 to MIDI-110; INT-31, INT-65 | Old browsers silent |
| A compromised decoder | An attacker who found a fault in the receiver | The sandbox, unchanged; the trusted core's checks of every voice operation | INT-43, INT-44; DOC-2295 | Sound of its choosing in its own tab, within the voice operations' bounds, as today |
| Work on the server by a hostile program | A channel's program | `server.md`'s bounds (MIDI-122) and fuzz targets | MIDI-122; INT-71 | `server.md`'s analysis |

- Reason: DEVELOPMENT.md section 14; section 2.3 (the analysis's findings are applied to the proposal: INT-4, INT-13, INT-18, INT-44 and INT-74 are such findings).
- Source: DEVELOPMENT.md sections 2.3 and 14.
- Verification: Review on adoption, recorded with its date.

**INT-77. No synthesizer setting switches security off.** No option, feature, setting or protocol field MUST turn off a bound or a check of this document or of `midi-architecture.md` section 16.
- Reason: DEVELOPMENT.md section 1 item 5 ("No option may switch security off").
- Source: DEVELOPMENT.md section 1 item 5.
- Verification: Review.

**INT-78. The analysis covers what is new only.** Nothing in this section MUST be taken to change the security of anything other than the synthesizers: the carriage, the store's admission, the commands, the sound helper and the sandboxes keep their existing analyses, which INT-70 extends.
- Reason: DEVELOPMENT.md section 1 item 6 (each fact has one home).
- Source: DEVELOPMENT.md section 1 item 6.
- Verification: Review.

---

## 12. Deployment

**INT-79. Everything moves together.** The engine's change MUST be pushed; then the server, every channel and the browser release MUST be deployed at one moment: the server speaking program protocol 13, every channel's program speaking 13 (a program of 12 cannot run under a server of 13, MIDI-111), the browser release with the new engine published through its updater; and the viewer-state change of `viewer-state.md` MUST be the same deployment (VS-602 step 9).
- Reason: The codecs, the program protocol and the push protocol change at once (INT-63, INT-64), and each side of each refuses or ignores the other's old form; a deployment in parts would leave channels down or silent between the steps.
- Source: VS-601, VS-602; MIDI-109, MIDI-111; DEC-6461 ("What it changes": the browser and the server are rebuilt and deployed together).
- Verification: The deployment's checks of INT-83.

**INT-80. What an old browser does.** An old browser MUST be expected to behave so after the deployment, and the release notes MUST say so: under the push protocol change of VS-201 it cannot connect to the new server at all (its HELLO is refused, close code 4001, `wrong_version`), and its updater offers the new release; were the synthesizers deployed without that change, it would show every page and play every sampled sound, and be silent wherever a synthesizer plays, its receiver ignoring codes 12 to 19 as reserved and counting each object as unsupported, and its plays of them waiting forever (MIDI-109). An old browser MUST NOT play anything wrong in either case.
- Reason: Silence, not noise, was the purpose of new codes (DEC-6465 answer 1); the push protocol change makes it moot on the push carriage but not in recordings.
- Source: MIDI-109; DEC-6465 answer 1; VS-201; the wire vectors (`close wrong_version 4001`).
- Verification: The test of MIDI-109 (the engine's last receiver before the change, fed records of codes 12 to 19); a by-hand check with the previous browser release against the deployed server, recorded with its date.

**INT-81. What a new browser does with an old recording.** A recording made before the change (a T42 file, a `.ntrec`) whose synthesizer sounds are of codes 3 to 11 MUST play its pages and its sampled sounds and be silent for those synthesizer sounds, counting each as unsupported; no converter of old recordings MUST be built unless the owner asks for one.
- Reason: Codes 3 to 11 are retired (MIDI-108); the recordings of before 18 November 2026 are test recordings of the audio demonstration channel, not a body of work to keep audible.
- Source: MIDI-108; DEC-6465 answer 1.
- Verification: A test feeds a recording of codec 4 to the new receiver and checks the counter and silence.

**INT-82. The way back.** Before the deployment, the versions of the server, of every channel and of the browser release in service MUST be recorded as the versions to roll back to, and the deployment pipeline's backup confirmed (DEVELOPMENT.md section 15); a rollback MUST put all of them back together, for the same reason they move together.
- Reason: DEVELOPMENT.md section 15 ("Production: confirm the deploy took a backup, or record the version to roll back to"); a partial rollback is a partial deployment.
- Source: DEVELOPMENT.md section 15; INT-79.
- Verification: The rdm deployment record names the versions.

**INT-83. The checks after deployment.** After the deployment it MUST be checked and recorded: that every channel's program reports protocol 13; that the audio demonstration channel's pages play a stored and a live sound of each of the eleven kinds in the new browser on each of its three hosts, by ear, with the hearer and the date; that a tab switch away and back leaves each playing (INT-48); that two tabs on one page each hear the page from their own start (INT-49); and that the previous browser release behaves as INT-80 says.
- Reason: Nothing of the synthesizers has been listened to by a person since they were built (DEC-6421: "nothing has been listened to"); a deployment is where the whole path first runs.
- Source: DEC-6421; DEVELOPMENT.md section 3.4 (report a check as run or not run).
- Verification: The rdm deployment record and its notes.

---

## 13. Measurements owed

Each measurement below MUST be made on the build that implements this document, recorded in the commit that adds it (or in the requirement named), with its instrument shown to exercise the changed code (DEVELOPMENT.md section 2.1, "Measure, don't reason").

**INT-84. Render cost on the browser's hosts.** For each family, the time to render one block MUST be measured in a release build, for its costliest block (INT-74) and for a typical block of the audio demonstration channel's tune, on each of the browser's hosts: the Mac (macOS, Apple silicon), the Linux host (`foundintelquiet4060`, x86_64) and the Windows 11 virtual machine; each result MUST be written in a table of family against host in the engine's architecture document, and each MUST meet INT-74's budget.

| Family | Voices | Costliest block, macOS | Costliest block, Linux | Costliest block, Windows | Typical block, each host |
|---|---|---|---|---|---|
| synth6581 (and synth8580) | 3 (one chip) | to be measured | to be measured | to be measured | to be measured |
| synth7 | 16 notes over 16 parts | to be measured | to be measured | to be measured | to be measured |
| synth106 (and synth60) | 6 | to be measured | to be measured | to be measured | to be measured |
| synthD | 1 | to be measured | to be measured | to be measured | to be measured |
| synth53 (and synth52, synth51) | 5 | to be measured | to be measured | to be measured | to be measured |
| synth8 | 8 | to be measured | to be measured | to be measured | to be measured |
| synth80 | 8 | to be measured | to be measured | to be measured | to be measured |

- Reason: DEC-6410's condition for reconsidering; the instruments were measured only as a whole on 16 November 2026 ("54 to 63 times faster than real time, measured in release on the development machine", DEC-6421 item 3), before event lists and the interfaces' messages.
- Source: DEC-6410; DEC-6421 item 3; the voices: `midi-architecture.md`, MIDI-125; DEVELOPMENT.md section 12 (the hosts).
- Verification: The timed tests, printing their numbers; the table filled.

**INT-85. Render cost and size on the microcontroller targets.** For each family, on each microcontroller target of the engine's REQ-GEN-015 (Arm Cortex-M0 to M33, `thumbv6m-none-eabi` and the Cortex-M targets above it; RISC-V `riscv32imc-unknown-none-elf`; Xtensa ESP32 and ESP32-S3), there MUST be measured: the flash and static memory the family's feature adds to the engine's microcontroller build (`cargo xtask size`), the receiver's memory with that family alone, and the cycles one costliest and one typical block take; a family MUST be listed as fit for a target when one lane's costliest block renders in at most 10 milliseconds at the target's usual clock, and the list MUST be written in the engine's architecture document for the owner to choose which families each port builds.
- Reason: The receiver is meant to run on microcontrollers (REQ-GEN-006, REQ-GEN-015); no synthesizer has been built for one. Ten milliseconds, half a block, leaves the other half for the teletext decoding the same processor does.
- Source: The engine's REQ-GEN-015, REQ-GEN-017 (flash cost measured); DEVELOPMENT.md section 12.2. The criterion of 10 milliseconds is NeoTeletext's own (section 16).
- Verification: The size and cycle reports in the commit, and the list.

**INT-86. Processor time with many tabs.** The browser's processor time MUST be measured with 1, 4 and 16 tabs, each playing four synthesizer sounds of the costliest family, in front and in the background, with and without the tabs muted, on each host.
- Reason: Every tab renders its own sounds (INT-48, INT-49), muted or not (DEC-6477 integration answer 3); the cost grows with tabs, and the owner should see it, and DEC-6477 is to be reconsidered if the cost matters.
- Source: INT-48, INT-49; DEC-6443.
- Verification: The figures in the browser's commit, set beside DEC-6477's answer 3.

**INT-87. Bytes on the wire.** The bytes and packets each family's demonstration tune and live sound cost on the push carriage MUST be measured against the same music as built before this change (slots of 4 bytes), with the store's bytes and the time to find and read a block, as MIDI-49 requires.
- Reason: MIDI-49.
- Source: MIDI-49.
- Verification: Review of the figures.

**INT-88. Delays and underruns.** On each host there MUST be measured: the start delay of INT-54; the lead actually kept against INT-34's bounds over ten minutes of play; the number of underruns of a synthesizer stream in the sound helper over those ten minutes with the host idle and with it busy compiling the workspace; and the delay from a key pressed on the audio demonstration channel's keyboard page to the first sample of its note heard.
- Reason: INT-34's lead is chosen by reasoning and must be confirmed; REQ-6415 item 6 asks for the start delay; the keyboard's round trip (DEC-6398) is what a player feels.
- Source: INT-34, INT-54; REQ-6415 item 6; DEC-6398.
- Verification: The figures recorded in REQ-6415 and in the commit; INT-34's bounds revised if they fail.

**INT-89. Packets a second of a live sound.** For each family's live demonstration sound, the packets a second its records need MUST be measured, and compared with what a broadcast's data lines give (INT-19).
- Reason: INT-19.
- Source: INT-19; DOC-1857.
- Verification: The figures in the commit.

---

## 14. The order of integration

**INT-90. The order of change.** The repositories MUST change in this order, each step by its own process (DEVELOPMENT.md section 2.2: decisions and requirements recorded, tests that fail on the old code, documents, commits naming their records, through the gates), and this order MUST be merged with `viewer-state.md`'s (VS-602) into one plan of one release train, each repository making both changes in its step:
1. **neoteletext-common and rdm.** On the owner's approval of the documents of this folder: their requirements and decisions recorded in rdm with their links; TODO-6450 revised (INT-68); the documentation items of INT-66 drafted from the documents (VS-602 step 1 asks for the items first); to-dos for each step below.
2. **The engine.** Codes 12 to 19, the event-list reader, the store's offsets and lengths, tag 8, the bank codec and readers, each family's adopted interface, the common layer, the receiver rendering as played into streams named with their audio channel (INT-33, INT-37), the counters, the features (INT-30), the fuzz targets (INT-71, INT-72), the wire vectors' engine copy (INT-67), the measurements of INT-84, INT-85 and INT-87; then pushed to GitHub (INT-58).
3. **The server.** The engine pin moved (INT-57, INT-58), program protocol 13 and `schema-13.json`, the synthesizer messages of `server.md`, the server's own instrument code deleted, the raw packets check (INT-4), consecutive fragments (INT-13), live pacing (INT-18), the counters (INT-62), its fuzz targets; and the Cloudflare host's equivalents where it carries sound.
4. **The kits.** The TypeScript kit and the Python kit, each with types from `schema-13.json` and its calls, the TypeScript kit's sound logic removed (MIDI-22), each a release speaking 13; their documents say INT-28.
5. **The component library** (neoteletext-server-ts-ui-components): the release that depends on the kit speaking 13. It holds no synthesizer code (its `sound.ts` makes sampled tones), so its change is the protocol's and `viewer-state.md`'s.
6. **The channels.** The audio demonstration channel (neoteletext-server-channel-audiodemo) rewritten to protocol 13's synthesizer messages: patches and banks in the adopted interfaces' forms, music as events or Standard MIDI Files, no blocks or packing of its own; every other channel taking the kit and library releases.
7. **The browser.** The engine pin moved (INT-41), the features (INT-42), the stream's audio channel in the `protocol` crate (INT-37), the ledger (INT-44, TODO-6446), the tab-switch test (INT-48, TODO-6448), the decoder tests (INT-56), the counters (INT-53), licences (INT-55), the measurements of INT-84, INT-86 and INT-88. The browser depends only on the engine, so this step MAY run beside steps 3 to 6.
8. **`PROTOCOL.html`.** The documentation items finalised against the built bytes (INT-66), `wire-vectors.tsv` (INT-67), `PROTOCOL.html` generated and committed in neoteletext-common.
9. **The deployment** of INT-79, with its checks (INT-83).
- Reason: Each step needs the one before: the server checks with the engine's code and takes it from GitHub; the kits copy the server's schema; the library depends on a kit; the channels on both; the items are finalised from what was built; the deployment needs all. VS-602 puts the browser before the kits; for the synthesizers the browser needs only the engine, so either position holds.
- Source: VS-602; DEVELOPMENT.md sections 2.2, 9 and 11; the user's order of 18 November 2026 (engine, server, kits, library, channels, browser, `PROTOCOL.html`, deployment).
- Verification: The to-dos of each step, each closed with its commit.

**INT-91. Integration happens on `livedevelopment`, and `main` moves by the owner.** Every step MUST be committed on each repository's `livedevelopment` through its commit and push gates, and no repository's `main` MUST move until the owner says to integrate (DEVELOPMENT.md section 9.1), when every repository's full gate runs.
- Reason: DEVELOPMENT.md sections 9 and 10.
- Source: DEVELOPMENT.md sections 9.1 and 10.2.
- Verification: The gates.

---

## 15. What is left out

| Left out | Reason | Reconsider when |
|---|---|---|
| Writing synthesizer sounds into broadcast files with the engine's `neottx sound` (DEC-6421 item 11: it refuses an instrument codec today) | DEC-6462 makes the server the one builder of synthesizer records; a broadcast or a file of them is made by recording the server's output, packets 4/31 as they are. A second builder in `neottx` would be a second implementation. | A broadcast needs synthesizer sounds without a server. |
| A restatement made for one joining viewer | A block number has one content for every receiver (MIDI-100); DEC-6465 answer 4. | A second of wrong timbre is heard as a fault. |
| Rendering a stored synthesizer sound whole ahead of play (DEC-6421 item 2) | INT-33; DEC-6410 item 13. | Never, unless streams prove unworkable on a host (INT-88). |
| Any sound made by the receiver in answer to a key or the wheel without the server | DEC-6398. | The owner decides on local behaviour. |
| Sounds bound to a sub-page | The CONTROL record names a page (INT-21). | A channel needs different music for each sub-page of one page; today it can use separate pages. |
| A converter of recordings made with codes 3 to 11 | INT-81. | The owner asks. |
| Skipping the rendering of a muted or background tab | DEC-6477 integration answer 3 (open question 3): every tab keeps rendering. | INT-86's figures, or the owner. |
| Synthesizers in the Android port and in the microcontroller ports' programs | Neither port plays synthesizers today; this document measures the targets (INT-85) and leaves the choice to the owner. | The owner chooses families for a port. |

---

## 16. What NeoTeletext defines itself

1. **`LIVE_SEND_LEAD_BLOCKS`, 25 blocks (500 milliseconds)** (INT-18): no standard paces a live sound's records; the figure fits the receiver's ring of 32 with its lookahead of 3.
2. **The lead of 2 to 5 blocks (40 to 100 milliseconds)** (INT-34): rendering as played needs a lead, which the audio profile never stated because it never rendered.
3. **A missing block of a progressive stored event sound is played as a lost block** (INT-25): the audio profile's progressive rule was written for samples, where a missing block is silence.
4. **A stream named with its audio channel** (INT-37): needed so that one sound can play on two audio channels from two starts.
5. **The raw packets message refuses audio records** (INT-4): a gap in today's server, closed as it was for ReGIS and NAPLPS records.
6. **A record's fragments sent consecutively** (INT-13): the carriage allows interleaving; the server chooses not to.
7. **The receiver's counters in the channel's Log tab** (INT-53).
8. **No synthesizer clips alone** (INT-46).
9. **The per-block budget of 5 milliseconds on the browser's hosts and the criterion of 10 milliseconds on a microcontroller** (INT-74, INT-85).
10. **One feature per family and the end of the `analog` feature** (INT-30).
11. **The order of records to a connection: banks, then the OBJECT, then the DATA; a joining connection given blocks from the next only** (INT-11): the profile allows any order and waits; the server makes the wait shortest.

---

## 17. Open questions for the owner

Every question of this section was answered by DEC-6477 (18 November 2026, at the owner's delegation, awaiting the owner's review), each answer the recommendation; the answer is recorded under each question, and the requirements cited follow it.

**1. Two playings of one synthesizer sound at once** (INT-37). *Answered by DEC-6477 (integration answer 1): option A; the engine's voice-sink stream calls and the browser's voice-operation message carry the audio channel, so one sound can play on two audio channels at once; REQ-6415 is to be revised accordingly (INT-37).*
Today a stream is named by its sound alone, so one stored synthesizer sound playing on two audio channels from two different moments cannot be told apart in the stream operations.
- *Option A* (written): name each stream with its audio channel too: a change to the engine's `VoiceSink` stream operations and to the browser's voice-operation message, one byte more, so each playing is its own stream.
- *Option B:* allow one playing of a stored synthesizer sound at a time in a tab: a second play of it on another audio channel stops the first. No message changes, but a program that plays one phrase on two channels (an echo, a round) cannot.
- *Recommendation:* A. MIDI-3 already requires each playing its own instance; the message change is small and inside one release.

**2. If the synthesizers and viewer state are not ready together** (INT-63, INT-79). *Answered by DEC-6477 (integration answer 2): option A; one protocol 13 and one deployment (`server.md` SRV-2).*
Both need program protocol 13 and one deployment.
- *Option A* (written): one protocol 13 and one deployment; whichever is ready first waits.
- *Option B:* whichever is ready first is released as protocol 13 and deployed; the other becomes protocol 14 with its own deployment.
- *Recommendation:* A, as asked; B only if one waits on the other for more than a few weeks.

**3. Muted and background tabs** (INT-48, INT-86). *Answered by DEC-6477 (integration answer 3): option A; background and muted tabs keep rendering until the measurements of INT-86 show the cost matters.*
Every tab's decoder renders its sounds whether the tab is in front, behind or muted, as a background tab in a web browser keeps playing.
- *Option A* (written): keep rendering everywhere; unmuting or returning hears the music exactly where it is, and nothing between processes changes.
- *Option B:* the trusted core tells a muted tab's decoder it is muted, and the decoder keeps each playing's position by its clock without rendering; unmuting restarts rendering at the right block, with a new synthesizer instance and the music's state restated only at the next restatement (up to a second of wrong timbre).
- *Recommendation:* A, until INT-86 shows the cost matters.

---

## 18. Differences from what is built today

**Records and the receiver.**
1. Codes 3 to 11 are retired and 12 to 19 take their place; the receiver reads event lists, variable blocks and banks of bank images (`midi-architecture.md` section 21 items 1 to 7). DOC-1951's table of record types lacks types 13 to 17, which the engine already uses (`record.rs`: 13 kept for the CHANNEL record, REQ-3581; 14 REGIS; 15 DRAWING_LINKS; 16 REGIS_CURSOR; 17 NAPLPS); this document adds none, and the table's correction is separate work.
2. The receiver renders a stored synthesizer sound whole at its first play and defines it to the sink (DEC-6421 item 2); it will render as played into a stream (INT-33), with a lead (INT-34), and a loop plays on across its join (INT-36). `receiver/instruments.rs` changes, and its lanes become one family at a time or stay all families, as measured (INT-32, INT-40).
3. A stream is named by its sound alone; it will be named with its audio channel too (INT-37): the engine's `port.rs` and the browser's `protocol::audio` and `voice_sink.rs` change.
4. `Statistics::slots_passed_over` becomes events passed over, and blocks malformed, patches refused and plays of banks ignored are added (INT-38).
5. The `analog` feature goes; the seven family features stay, with new meanings (INT-30).
6. The engine's fuzz workspace builds no synthesizer; it will build all seven, with two new targets (INT-71, INT-72).

**The browser.**
7. The engine pin moves from `dd0421c6` (INT-41).
8. The sound helper holds a stored synthesizer sound's samples whole, under the two-minute bound; it will hold two seconds of each stream (INT-44). REQ-6415 items 2 and 6 are revised.
9. The tab-switch fix of `9442e09` has no regression test; TODO-6448's is added (INT-48).
10. The trusted core's ledger drops a third tab's sounds silently (TODO-6446); it will report the refusal (INT-49).
11. The decoder's engine tests cover synth6581 alone; they will cover every family (INT-56).

**The server.**
12. The server pins the engine at `4ddd34b` and writes and checks the instrument records with its own code; it will use the engine's (INT-57).
13. The raw packets message forwards audio records unchecked; it will refuse them (INT-4).
14. Live blocks are forwarded as the program sends them; they will be paced (INT-18).

**Protocols and documents.**
15. Program protocol 12 becomes 13, one version with viewer state (INT-63); the push protocol's change is viewer state's alone (INT-64).
16. `PROTOCOL.html` does not mention the synthesizers; the items of INT-66 are written and TODO-6450 revised (INT-68).
17. `synthesizer-wire-format.html` and `programming-the-synthesizers.html` describe the retired format; they are regenerated or replaced (INT-69).

**Records in rdm superseded or revised on adoption.** REQ-6411 (codecs 3 to 5) superseded by `midi-architecture.md`'s requirements and INT-30 to INT-40; REQ-6413 and REQ-6414 superseded by `server.md` and the kits' documents; REQ-6415 revised (INT-33, INT-37, INT-44); DEC-6421 item 2 superseded by INT-33; DOC-1859, DOC-1860, DOC-1862, DOC-1963, DOC-1968, DOC-1970, DOC-1972 and DOC-2295 revised (INT-66); TODO-6416's items on rendering as played and fuzz targets carried by INT-33 and INT-71.

---

## 19. Agreement with the other documents

This document was checked against `midi-architecture.md` and `viewer-state.md` on 18 November 2026. What was found, for the owner and for the authors of those documents:

1. **The push protocol's number.** *Settled by DEC-6477, and `viewer-state.md` corrected:* `viewer-state.md` said the push protocol was "today … input protocol version 2" and made it version 3 (VS-201, VS-203 item 2). The engine's push protocol version is 7 (`neoteletext_input::limits::VERSION` = 7; `wire-vectors.tsv`: `version input 7`, subprotocol `neottx.7`), so the next is 8, as VS-201 and VS-203 now say and the engine's branch `viewer-state` builds; INT-64 names it.
2. **Record types 13 to 15.** *Settled by DEC-6477, and `viewer-state.md` corrected:* `viewer-state.md` VS-204 allocated record types 13 (STATE_CHALLENGE), 14 (STATE_END) and 15 (STATE_KEEP_OFFER). The engine already uses 14 (REGIS, REQ-6336) and 15 (DRAWING_LINKS, REQ-6370), and keeps 13 for the CHANNEL record (REQ-3581); 16 and 17 are REGIS_CURSOR and NAPLPS (`record.rs`). The state records now take 18, 19 and 20, as VS-204 says and the engine's branch `viewer-state` builds. This document allocates no record type.
3. **The order of change.** VS-602 puts the browser fourth, before the kits; INT-90 puts it seventh, after the channels, as the order of 18 November 2026 asks. For the synthesizers the browser depends only on the engine, so INT-90 allows it beside steps 3 to 6; the two orders are to be merged into one plan (INT-90).
4. **A live sound's advance and the ring.** *Settled by DEC-6477 (answer 2), and `server.md` corrected:* MIDI-20 lets one events message advance a live sound by 100 blocks, more than the receiver's ring of 32 holds. INT-18 resolves it on the server's side, by pacing, and `server.md` SRV-77 now builds that pacing (the 100 blocks are what the server accepts, not what it sends at once); `midi-architecture.md` MIDI-20 is to say the same when next revised.
5. **Repetition of stored objects.** MIDI-51 says a stored object's records "are repeated until every one has arrived"; that holds on the broadcast carriage; on the push carriage they are sent once, over a reliable connection (INT-16).
6. **The `packets` message.** Neither `midi-architecture.md` nor the server's checks close the raw packets path for audio records; INT-4 does.
7. **A live sound's audience and a handle's two objects.** *Settled by DEC-6477 (names and behaviour follow `server.md`):* INT-61 first sent a live sound's blocks to every connection sent its OBJECT, and INT-9 refused one handle for a bank and a sound at once; `server.md` sends blocks to the connections each events message names (SRV-74) and lets a newer object replace a bank on its handle (SRV-59). INT-9's verification and INT-61 now follow `server.md`.
