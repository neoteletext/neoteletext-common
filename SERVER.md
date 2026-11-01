# NeoTeletext Server

**Status:** recommended design, 25 October 2026. For the owner to decide (section 19); nothing here is built.

**Sources:**
- The owner's two drafts of 25 October 2026: "NeoTeletext Server", and "NeoTeletext Server — Proposed Architecture".
- The engine (`~/devel/neoteletext-engine`) and the browser (`~/devel/neoteletext-browser`) as they stand.
- The browser's decision 104, which rescinds decision 22: pages are fetched while they are visible or have focus.

Where the drafts disagreed, or the engine already decides a question, this document says what it chose and why.

Paths:
- `E/` is the engine's `crates/` folder.
- `B/` is the browser's `native/` folder.
- `C/` is this repository.

## 1. What the server is

A teletext application server. Applications publish teletext pages and streams. Clients receive them as 42-byte teletext packets and behave as teletext receivers. The server holds what is being viewed, runs nothing per viewer, and sends each client only what changed in the pages it shows.

Three models, none allowed to dominate:

- **Teletext broadcasting:** channels, magazines, pages, sub-pages, authentic packets. A recording of what a client receives plays in any decoder.
- **Unix terminals:** an application keeps a screen, receives input, and refreshes. The server is its terminal driver and sends only what changed.
- **The web:** pages are addressable resources, served over HTTPS and cached; applications may personalise for an authenticated viewer.

Two properties of teletext make the design work:

1. **A page update replaces what it covers.** A row packet replaces its row, and a header with the erase bit replaces the page, so an update can be resent or coalesced without corrupting anything. Over an ordered stream, sending is idempotent.
2. **A row packet belongs to the last header sent** (it carries only its magazine and row). An update is therefore coherent only as a group: header, then rows. The unit that can be delayed, dropped or resent is the **page update**, never a single packet (section 5.2).

Rules from the start, since retrofitting them is a rewrite:
- the teletext code does no I/O;
- the server's runtime never touches a socket or a clock directly;
- the server builds on the engine and never copies it.

## 2. Vocabulary

| Noun | Meaning | Analogue |
|---|---|---|
| **Channel** | A teletext service: a folder on a web origin (engine decision E.70). Where a client connects, whose cookies it holds, what sessions belong to. | Web origin and path |
| **Page and sub-page** | A teletext page, `100` to `8FF`, and its sub-codes. Addressable, cacheable, tunable. | Web resource |
| **Session** | A viewer's relationship with a channel's application across connections. | tmux session |
| **View** | One place in a client showing a page. Each browser tab of a live channel has its own connection (DEC-1527), so to the server a view is a connection: it knows only the one page and sub-page that connection has selected, its **selection** (SELECT, section 5.4), and whether that page is focused for input. **Selected**, **active** and **focused** are defined once, in `INPUT.md` section 5.4: the selected page is active, so it is updated whatever its focus (REQ-1553). Elsewhere in this document a page a view has selected is called **tuned**, the word used before 29 October 2026. | Terminal window |
| **Application** | A program behind live or interactive pages, outside the server, serving every viewer at once. | Terminal program |

Deliberately not concepts for application developers:
- the magazine, which is the page number's first digit;
- the connection, a disposable pipe;
- packets, except through the raw interface of section 7.4.

**Ownership decides sharing.** A page is either the channel's, one copy shared by every viewer, or a session's, private to that session's views. Two viewers' sessions may each have their own page 500 (a game) while the channel's page 100 is one shared copy. Ownership comes from where the application published it (section 7.3), never from a flag on the content, so a private page cannot be shared by a slip.

## 3. Code: shared, not rebuilt

### 3.1 What the engine already does

The server's teletext is almost all in the engine.

| The server needs | The engine has |
|---|---|
| A page model | `PageFile` (`E/neoteletext-formats/src/page.rs:49`): address, sub-code, status, 26 rows, X/26, raw packets, Fastext, link lines, cursor, input modes |
| TTI | `TtiReader` (`tti.rs:36`), `write_tti` (`write/tti.rs:333`) |
| T42 | `T42Reader`, `T42Writer` (`write.rs:24`) |
| A page to packets | `encode_page` (`encode/page.rs:120`): M/29, X/0 with parity and control bits, X/27/0 with the checksum, X/28/0, X/26, rows, in EN 300 706 Annex B.2's order; transmission order by Annex B.7 |
| Packet codes | Hamming 8/4, Hamming 24/18 and odd parity, both directions (`E/neoteletext-core/src/ecc.rs`); X/0, X/26, X/27, X/28 and M/29 builders (`packet/encode.rs`) |
| Level 2.5 and 3.5 authoring, MOT | `author` module of `neoteletext-formats` |
| The input protocol's channel side | `StreamDecoder` (`E/neoteletext-input/src/event/decode.rs:203`); WELCOME, PUSH_MODE, POP_MODE, PAGE_MODES and cursor records |
| Audio to packets | `neoteletext-audio`, feature `encode`: sounds, live records, IMA ADPCM, IDL packets on data channel 12 |
| The WebSocket handshake | `ws::accept_for` (`E/neoteletext-web/src/ws/handshake.rs:30`) |
| `channel.json` and `contents.txt` read | `Descriptor::parse`, `contents::read` (`neoteletext-web`) |
| Cookies | RFC 6265bis, client side (`neoteletext-web`) |
| WebAssembly | `neoteletext-core` and `neoteletext-formats` build for `wasm32-unknown-unknown` and `wasm32-wasip1` (`scripts/build-targets.sh`), untested there |

### 3.2 What the server adds

**The owner decided on 25 October 2026 (option B):** the engine's scope is unchanged. The server lives in its own repository, `~/devel/teletext-server` (private, `github.com/crowdwave/teletext-server`). It imports the engine's crates at a pinned revision, never copies them, and writes there, once, what the engine lacks:

1. **A row diff:** the changed rows between two versions of an engine `PageFile`, and whether its enhancements changed.
2. **A push protocol crate, both sides** (`teletext-push`, sans I/O):
   - page frames, stream frames and control records (section 5);
   - the SELECT event (section 5.4);
   - used by the server, and imported by the browser's fetcher, as `neoteletext-input` serves receivers and channels.
3. **The channel side of an INPUT.md session:** the counterpart of the receiver's `Session`, built on the engine's `StreamDecoder` and control records.
4. **Server WebSocket frames:** unmasked writes, masked reads, beside the engine's `ws::accept_for`.
5. **Writers for `channel.json` and `contents.txt`,** which tools now write by hand.
6. **`Set-Cookie` writing and signing.**
7. **The audio object cycler** that the engine's `docs/spec/design/audio.md` §6.1 asks of a transmitter, over the engine's audio encoder.
8. **Tests that the engine's crates give the same output natively and in WebAssembly**, where the server needs WebAssembly.

**The engine's scope stays as it is:** `requirements/out-of-scope.md` items 5 (packet 31 data services) and 11 (teletext generation as a product) are not amended.

**What B costs, and how to keep it from becoming duplication:**
- **The push protocol has two sides:** the browser's receiver, in the engine, and the server's sender, here. To keep one implementation, the protocol crate (item 2) lives here, both sides, and the browser imports it from this repository pinned at a revision, as it imports the engine. Whatever the browser's fetcher already reads in `neoteletext-web` stays there until it moves.
- **The browser's reference channel** (`B/site`) already holds hand-written versions of the server half of WebSocket, HTTP serving and TTI writing. Once the server has them, the site imports them from here, or becomes the server's applications (section 3.3), and its copies are deleted.

### 3.3 Where the server lives

| | **A server repository pinning the engine (chosen by the owner, 25 October 2026)** | Server crates in the engine's workspace | A third repository of shared crates |
|---|---|---|---|
| Sharing | The engine's crates at one revision, never copied (`C/DEVELOPMENT.md` §11) | The same | The engine's crates would move |
| A change spanning codec and server | Engine first, then the pin | One commit | Two or three steps |
| Process | The browser's, which exists | The engine's requirements would cover a product | New |
| Cost | Pin moves | A slower server under the engine's process | Most churn |

The server repository, `teletext-server`:

| Crate | Holds | No |
|---|---|---|
| `runtime` | One single-threaded actor per channel: page store, tune tables, sender, flush policy, sessions, application host. Written against a `Host` trait (send, timer, now, spawn, storage) | I/O, threads, clock |
| `native` | tokio, TLS, the listener, application processes over stdio | Teletext logic |
| `cli` | `serve`, `validate` (a channel against the engine's rules), `inspect` (what a client would receive) | — |

**The browser's reference channel stops being a second server.** `B/site` today has its own HTTP server, its own WebSocket server half, TTI built as strings and `channel.json` written with `format!`. It is ported to the server:
- its pages (index, typing, invaders, piano, links, phone, podcast) become applications;
- the browser's tests run the real server;
- the hand-written transport is deleted.

Until then it uses `write_tti` and `encode_page` rather than strings.

### 3.4 Software development kits

The protocol of section 7 is the interface; a kit is a convenience. One reference kit, in TypeScript, keeps the screen buffers of section 7.3; others are thin wrappers that add nothing the protocol lacks. Three kits maintained from the start would be a load for one person.

## 4. Channels and addressing

**This section is the one written URL map** (REQ-1693, decided by DEC-1694). Every other document points here. A channel has one map: it is complete, so nothing is reachable by an address it does not list; it is fixed, so it is the same for every channel, and a channel cannot rename, move or add to it; and it is defined, so each thing has one spelling, and every other spelling is normalised to it or refused. `<channel>` means an `http` or `https` origin and folder, ending in `/`, optionally followed by a query, such as `https://app.neottx.com/home/`. The conformance table, every address below with what it opens, why it is refused or what a server answers, is the engine's `crates/neoteletext-web/src/map/conformance.tsv`, which the engine, the server and the browser each run at their pin of the engine (`neoteletext_web::map::CONFORMANCE`).

### 4.1 What viewers see

A channel's identity is its address up to `#`. Everything after `#` is inside the channel, and is never sent to a server (RFC 9110 section 4.2.5 and RFC 3986 section 3.5).

| Address | Opens |
|---|---|
| `<channel>` | The channel, arriving at its initial page (section 4.3) |
| `<channel>#302` | Page 302 |
| `<channel>#302/0002` | Sub-page 0002 of page 302 |
| `<channel>#302?name=value` | Page 302, with page parameters for the channel's program |
| `<channel>#302/0002?name=value` | Sub-page 0002 of page 302, with page parameters |
| `<channel>#contents` | The channel's contents |
| `<channel>#wall` | The wall of pages, with no page selected |
| `<channel>?name=value#302` | Any of these, with channel parameters, which are part of the channel's address and reach its program when it connects |

### 4.2 What receivers use

These are fixed names in the channel's folder (decision E.70). Viewers never see them in the address field, and a viewer's address naming a live or static channel's own file is refused, as section 4.4 says, except that a command-line reader told to open `channel.json` opens its channel (DEC-1710).

| Name | Channel | Holds |
|---|---|---|
| `channel.json` | Live and static | The channel's settings |
| `push` | Live | The WebSocket. It is always `<channel>push`, and `channel.json` has no member naming another address (`push: {method, input}`) |
| `contents.txt` | Static | The contents |
| `index.t42` | Static | A bundle of pages, first sub-pages only |
| `NNN.tti`, `NNN.t42` | Static | A page, or its first sub-page when it has several |
| `NNN-SSSS.t42` | Static | A sub-page, SSSS being four hexadecimal digits (`STANDARD-LIMITS.md` section 4) |
| `NNN.sub` | Static | A page's list of sub-pages, with their validators and titles |

### 4.3 Normalising

Each of these is changed to its one spelling when it is typed, linked, redirected to or opened from outside, and the address field, history and bookmarks hold only that spelling.

- **Arriving at `<channel>`.** Once the channel has given its initial page, the address becomes `<channel>#NNN` for that page, replacing the entry and adding no Back entry: `https://app.neottx.com/home/` becomes `https://app.neottx.com/home/#100`.
- **Digits.** Hexadecimal digits are capitals: `#1fe` becomes `#1FE`, and `#302/3f7e` becomes `#302/3F7E`.
- **File names.** `<channel>302.tti` and `<channel>302.t42` become `<channel>#302`, and `<channel>302-0002.t42` becomes `<channel>#302/0002`.
- **Parameters are not normalised.** They stay in the order given, percent-encoded as they came.

### 4.4 Refused

Any other fragment is refused, never ignored or repaired: the address is not opened, and a link carrying it is not a link. That includes `#`, `#30`, `#3021`, `#G02`, `#902` and any page the standard does not define, `#302/2`, `#302/3F7F` (which means no particular sub-page, and so cannot name one), `#302:0002`, `#WALL`, `#contents/1`, `#wall?name=value` and `#?name=value`. A page's file name with a fragment, such as `<channel>302.tti#303`, says where to go twice and is refused too, as are the receivers' names of section 4.2 that are not pages.

### 4.5 Spellings

- **Page:** three hexadecimal digits, magazine first.
- **Sub-page:** four hexadecimal digits, `0000` to `3F7E`.
- **Parameters:** `name=value` pairs joined by `&`, percent-encoded as a query is, following `?` inside the fragment. A name may not be empty, and a value may. RFC 3986 section 3.5 allows `/` and `?` in a fragment, so neither is escaped.
- **Length:** the whole address obeys the general limit of 8,000 octets (REQ-1661).
- **The words `contents` and `wall`** are in small letters and are the only words a fragment holds.

### 4.6 Parameters

**Channel parameters,** the query of `<channel>`, are no part of the channel's folder. The receiver sends them, as written, on the upgrade request to `push`, and the program is given them in `connected` (DEC-1665, REQ-1674).

**Page parameters** go with the selection. The receiver sends them in SELECT (`INPUT.md` section 5.4, DEC-1715), and the program receives them with that selection, in `selected`. They belong to that one selection: choosing another page, by any path, leaves them behind. They stay in the address, so a copied address, a bookmark or Reload sends them again. A static channel has no program, so they are kept in the address and do nothing, as a static host ignores a query.

### 4.7 What each address answers on the server

A live channel on the NeoTeletext server, on the native server and on Cloudflare alike, answers exactly this, and nothing else (DEC-1467, as amended by DEC-1669). The server serves no static channel and no channel's files: a live channel's pages, its contents and its sub-pages travel on its connection (section 6.1).

| Request | Answer |
|---|---|
| `<channel>` | 200, a small page in an ordinary web browser, naming the channel and offering a `neoteletext://` link and a link to get NeoTeletext. One line of script carries the address's query and any fragment of section 4.1 into that link, and leaves out any other fragment. It changes nothing else: no timer, no automatic launch and no redirect, so the page cannot lead anyone elsewhere |
| The folder without its final `/` | 308, a redirect to `<channel>`, on the same origin, keeping its query. A fragment stays with the web browser (RFC 9110 section 10.2.2) |
| `<channel>channel.json` | 200, the settings, generated |
| `<channel>push` | The WebSocket; 426 without an upgrade |
| Anything else under the channel, and `/` | 404 |

Only a `GET` or a `HEAD` reaches the small page or the redirect. A static channel answers whatever its host answers, and a receiver asks it only for the names in section 4.2.

### 4.8 Redirects, local files and what is outside the map

- **Redirects.** An HTTP redirect follows RFC 9110 section 10.2.2: a `Location` with no fragment inherits the original one, so `<old>#302` redirected to `<new>` opens `<new>#302`. A program's redirect names an address of this map, or a page of its own channel.
- **Local files.** A file or folder of page files takes the fragments of section 4.1, on its `file:` address. Arriving normalises to its initial page, as in section 4.3. A `file:` address is never split by the file-name rule: each local file is its own channel (REQ-722).
- **Outside the map.** The browser's built-in page `neoteletext:home` is not in a channel. A `neoteletext://` link wraps a whole address of this map and adds nothing to it (REQ-1672).

**Why not paths** (`/news/200/3`): every channel and client that exists already works with the layout, and a static host needs nothing new.

## 5. The wire

### 5.1 Transport

- **One WebSocket per tab** (DEC-1527): each browser tab showing a live channel opens its own, with its own decoder and store, never shared with another tab, even one on the same channel. The server sees one connection as one view with one selection (section 6.1); the channel's cookies stay shared by its tabs (section 8.2).
- `TCP_NODELAY` on.
- **No `permessage-deflate`:** the payload is small and already dense, and a private overlay compressed in one context with attacker-influenced public rows makes a compression oracle (CRIME and BREACH).
- **QUIC and WebTransport** later, only where measurement on a lossy mobile link shows head-of-line blocking. Section 5.2's self-contained frames are what make such a binding possible.

### 5.2 Downstream: four kinds of binary frame

**Downstream is a T42 stream, and nothing else** (DEC-1459, 30 October 2026): the binary messages, joined in the order sent, are a valid plain T42 file (the engine's REQ-INP-002), with nothing between packets and nothing added to them, and no text message is ever sent. Each message is a whole number of 42-byte packets (the engine's receiver already checks `len % 42 == 0`), of four kinds:

| Frame | Contents | Delivery |
|---|---|---|
| **Page frame** | Exactly one sub-page (DEC-1500, REQ-1501): its X/0 header, in serial magazine mode (C11 set), then either the whole sub-page with the erase bit (C4) set, or, for a later version of the same sub-page, only its changed rows and, if any of them changed, the whole group of enhancements (X/26, X/27, X/28). It is followed straight after by that sub-page's LINKS record whenever the sub-page has Link Extension links (section 5.5) | Only to the connection whose selection that sub-page is (section 6.1); changed rows are taken against what that connection was last sent (section 6.3) |
| **Stream frame** | Packets of an ordered stream: a recording, a carousel, an application's raw packets (section 7.4) | In order, never coalesced, through a bounded queue |
| **Audio frame** | One audio record as packet 4/31 on data channel 12 (section 9) | In order, through a bounded queue |
| **Control frame** | One control record on data channel 12 (section 5.5) | In order |

**One sub-page per frame, never a page's sub-pages together** (the owner, 30 October 2026: "IT IS VERY IMPORTANT THAT SUBPAGES ARE NOT TRANSMITTED WITH THEIR PARENT PAGE - SUBPAGES MUST BEHAVE IN EXACTLY THE SAME WAY AS PAGES", DEC-1500). No event sends two sub-pages in one frame, of the same page or of different pages: not a connection, not a selection, not a change. A page with one sub-page is a page whose list has one entry, sent the same way. A frame is therefore at most one sub-page, 3,108 bytes, and a page of the standard's 8,190 sub-pages, about 15 MB, is never sent to anyone at once.

**Why a page frame begins with its header every time.** A row belongs to the last header sent. A frame that begins with its own header stands alone: it can be applied, dropped or resent by itself, in any binding, with no state carried between frames.

- The cost: one 42-byte header per update, where a second change to the sub-page just addressed could do without. At an update a second, that is 42 bytes a second per connection.
- Serial mode makes the stream valid teletext, and a `.t42` recording of it plays.

**The sender's rules:**
- **A whole sub-page sets the erase bit**, so a sub-page selected again keeps nothing of an older version the receiver's store may hold. The first sub-page sent on a connection, the first after its selection changes, and every sub-page whose page or sub-code differs from the one last sent to the connection, go whole (section 6.3).
- **Changed rows go only for the same sub-code.** A frame of changed rows is sent only for a later version of the very sub-page, same page number and same sub-code, that the connection was last sent. Its header does not set the erase bit; the receiver keeps every row the frame does not carry (DEC-1499, REQ-1504).
- **Enhancements go as a group** whenever any changed, so a sub-page is never inconsistent with them.
- **Links follow every frame** of a sub-page that has Link Extension links, whole or changed rows, whether or not the links changed. A frame not followed by a LINKS record means the sub-page has no Link Extension links, and the receiver drops any it held for it (DEC-1517, which awaits the owner's confirmation; REQ-1494).
- **The header's text is the sub-page's,** sent like any row. The server never rewrites it: no clock ticking per viewer. A client draws its own clock, as receivers commonly do, or the program sends header changes.
- **A sub-page is 25 rows plus enhancements:**
  - header row 0;
  - rows 1 to 23;
  - row 24, the Fastext prompts;
  - X/26 to X/28.

  A Level 1 sub-page with links is 26 packets, 1,092 bytes, one TCP segment.
- **Over WebSocket, frames need no sequence numbers:** TCP is ordered and the server knows what each connection was sent. The packets have no spare field for one: every header bit is defined (EN 300 706 clause 9.3.1). A transport that loses or reorders data, if one is ever built, carries its sequence number as a record on data channel 12, one per datagram, never outside the packets (DEC-1459, which withdrew the 16-bit sequence number per page planned here).

### 5.3 Receiver-compatible and authentic delivery

There are two delivery modes, kept apart:

| Mode | What the client receives | For |
|---|---|---|
| **Receiver-compatible** (the default) | Page frames for the pages it tunes; not the full broadcast | Every page a person reads |
| **Authentic stream** | Stream frames: packets in the original or generated order and timing, unchanged | Recordings, virtual broadcast stations, applications that need exact packet order |

A receiver-compatible stream is not the original broadcast, and the server never claims it is. An authentic stream is never given current-state semantics: nothing in it is coalesced.

### 5.4 Upstream: INPUT.md version 5

Upstream is the input protocol already built on both sides and fuzzed (`C/INPUT.md`). It is binary events framed by `0xFF`, at most 8,192 bytes a message, and has:
- HELLO and WELCOME;
- KEY, MOUSE, WHEEL, PASTE and COMPOSE;
- FOCUS_IN and FOCUS_OUT;
- RESIZE.

PAGE (`0x0A`) and its capability were withdrawn on 31 October 2026 (DEC-1538, REQ-1556): a PAGE from any receiver is a protocol error, never read as a selection, and input protocol version 3 stamped each input event with the page on screen (REQ-1555). Version 4 adds the REDIRECT record, and a cursor record no longer moves a viewer (DEC-1689).

**The receiver says what its connection has selected** (the owner's decision of 29 October 2026: "we send an event saying which page the user has selected and if there are subpages then the server transmits them at that time. also the same event should send if the user has selected a subpage"). One event, an extension, which a channel that does not know it skips (`INPUT.md` section 5.4, REQ-INT-140):

| Type | Name | Payload |
|---|---|---|
| `0x40` | SELECT | `page` uv (`0x100` to `0x8FF`, or 0 for none), `sub` uv (the sub-code chosen, or `0x3F7F`, "no particular page sub-code", when the page was chosen and none of its sub-pages), and nothing after |

It is sent whenever the page or sub-page the tab has selected changes, whether or not keys go to the channel, and at the start of each session. It carries no view number: a connection is one tab with one selection (DEC-1527, which withdrew the `view` field and `MAX_VIEWS` of 29 October 2026). Section 6.1 says what the server sends in answer.

*Withdrawn on 29 October 2026, never built:* TUNE (`0x40`, a list of sub-pages tuned, with a `preview` flag), UNTUNE (`0x41`) and TITLES (`0x42`, titles by range), designed on 26 October 2026 for a receiver to tune single sub-pages and their neighbours. SELECT takes `0x40`; `0x41` and `0x42` are reserved.

A receiver that does not set SELECT has no selection of its own: its connection is shown the program's answer to `connected` with no selection, the channel's initial page (REQ-1471).

- **Focus** is FOCUS_IN and FOCUS_OUT, for the keyboard, and the pointer being over the page: it decides only where input goes, never what is sent (REQ-1554). A selected page stays active, and is updated, without it (REQ-1553).
- **The stamp.** Each input event carries the page and sub-code on screen when it happened. The server compares it with the connection's selection: a match goes to the program, with the page and sub-code; a press that differs is dropped, counted as `stale_input` in `/stats.json` and logged at most once an interval; a release is never dropped (REQ-1555, REQ-1557).
- **Held input.** The server keeps what each connection holds, and on a change of selection, FOCUS_OUT, a pointer's gone or a lost connection gives the program the releases still owed, marked `lost: true` (REQ-207, `INPUT.md` section 8 rule 3).
- **Keys are never batched or queued** in either direction.
- **No JSON on this wire.** A second protocol on one socket would mean two parsers in the browser's trusted core, and INPUT.md's KEY already carries everything the draft's `key {key}` would have to grow:
  - code;
  - modifiers;
  - text;
  - base character;
  - repeat and release.

JSON belongs to the application protocol (section 7), which people read and write.

### 5.5 Control records

Control records are teletext packets, as WELCOME is today: data channel 12, packet 4/31, records of the audio profile's frame, which a decoder that knows none of them skips, as EN 300 708 says. WELCOME is a kind of the control record, type 5 (`C/INPUT.md` section 7.2). The index, LOG, SET_COOKIE, LINKS, SUBPAGES and REDIRECT records are record types of their own, 6, 7, 8, 9, 10 and 11. **Each record's byte layout is defined once, in `C/INPUT.md` section 7, and nowhere else**: this section says only what each record is for and when it is sent. They are written with the engine's encoders and read with its readers.

| Record | What it carries (layout) | When it is sent |
|---|---|---|
| WELCOME, PUSH_MODE, POP_MODE, PAGE_MODES (the control record, type 5) | As `C/INPUT.md` section 7.2 | As today |
| Index (type 6) | The channel's magazines with their names, and each page's number, title, section and sub-page count, split across as many records as it needs (`C/INPUT.md` section 7.5, with section 7.10 for records of several fragments). It is page-level: it never lists sub-pages (DEC-1500 item 5). It is built from the program's `reply` and `index` messages (DEC-1482), never from a `contents.txt`; a live channel has no `contents.txt` (DEC-1467) | At connection, from the program's `reply`, and whenever the program sends an `index` change (section 6.5) |
| LOG (type 7) | `level` (`E`, `W` or `I`), the page it concerns or none, and UTF-8 `text` of 1 to 200 bytes (`C/INPUT.md` section 7.6): a log line for the channel's author, as a TTI `LG` line holds one (the engine's REQ-INP-026 and decision E.109 as amended for DEC-1459) | When the program sends an `author_log` |
| SET_COOKIE (type 8) | One `Set-Cookie` header value, built by the server from the program's typed `cookie` message (`C/INPUT.md` section 7.7) | When the program sets or clears a cookie mid-connection (section 8.2). The browser stores it in the channel's one cookie jar, which every tab of the channel shares (DEC-1527 item 4) |
| LINKS (type 9) | One sub-page's TTI Link Extension links: key links, page-number links and text links, with their targets and labels (`C/INPUT.md` section 7.8), so a sub-page sent as packets keeps the links packets cannot carry (DEC-1495, REQ-1494) | Straight after **every** page frame of a sub-page that has such links, whole or changed rows, whether or not they changed. A page frame not followed by one means the sub-page has none (DEC-1517, awaiting the owner's confirmation) |
| SUBPAGES (type 10) | One page's list of sub-pages: the list's version, its count (1 to 8,190) and each sub-code with its title of at most 40 characters, in ascending sub-code order with 0000 first when the page has it (every sub-code is a peer, DEC-1526), split across as many records as it needs (`C/INPUT.md` section 7.9, with section 7.10) | When the connection selects the page or one of its sub-pages and does not already hold the list's current version, and whenever the program changes the list while the connection's selection is the page or one of its sub-pages (DEC-1500 item 3, REQ-1503). It is never sent with, or in place of, any sub-page's content |
| REDIRECT (type 11) | A page and sub-code of this channel, or another channel's address (`C/INPUT.md` section 7.11) | When the program sends `redirect` (REQ-1688). It is the only thing that moves a viewer |
| DENIED | `page`, `reason` code: not found, not allowed, unavailable, limit | A selection refused, or a program that did not answer in time ("unavailable", REQ-1481) |
| LIMITS | The standard's maxima and the budgets of section 11 | Advertised after WELCOME, revised at any time |
| CHANGED | Page numbers | The coalesced change digest (section 6.5) |

The browser's sub-page list, its count and the selection's place ("3/12") come from a page's SUBPAGES record, never from the sub-pages its store happens to hold (the browser's REQ-1505). A channel served as files lists a page's sub-pages in `NNN.sub` instead (section 4).

*Withdrawn on 29 October 2026, never built:* a SUBPAGES record of 26 October 2026 (a tuned page's catalogue) and TITLES (titles by range). Today's SUBPAGES record (type 10) is a different record, made on 30 October 2026 because sub-pages no longer travel with their page.

Reasons are codes; the words are the client's. A record that breaks its layout or a bound is discarded and its packets counted as invalid (REQ-1462, `C/INPUT.md` section 7.10). DENIED, LIMITS and CHANGED have no layout yet.

## 6. Tuning and delivery

### 6.1 What a connection selects, and what it is sent

**One connection per tab, one selection per connection** (the owner, 30 October 2026: "we should probably have a websocket connection per tab which is completely self contained and decoupled - and the server sees it that way too", DEC-1527). Each browser tab showing a live channel opens its own push WebSocket, with its own decoder and store; tabs never share one, even on the same channel. A connection therefore has exactly one **selection**, or none: one page and one sub-code. The receiver states it with SELECT (section 5.4), which carries `page` and `sub` and no view number; the server's events to the program carry no view number either, and there is no `MAX_VIEWS`. The channel's cookies stay shared by its tabs, so the server sees two tabs as two connections of one session, as a web server sees two tabs of one site.

**The words** are `INPUT.md` section 5.4's, defined once (DEC-1538). The **selection** is the page and sub-page a connection shows: what is selected, sent, kept and diffed. A selected page is **active**: the server sends it and every change to it, whatever the focus. **Focused** is for input only, the `focus` and `blur` events among it. Only a new selection ends a page's updates.

**Every sub-code is a peer** (DEC-1526). Every sub-code 0000 to 3F7E a page has is one of its sub-pages, with content of its own, and all are equal (EN 300 706 section 3.1: a page address is a page number plus a sub-code). A page may have 0000 beside other sub-codes, and 0000 is then the page's own content; Annex A.1's 0000 for a page with no sub-pages and 0001 onward for a page with sub-pages are recommendations, not rules. A page's order is ascending sub-code, 0000 first when present: the order sub-pages are listed in, counted in and stepped through.

**The two selections** (REQ-1502):

| SELECT's `sub` | What the connection has selected | What it is sent |
|---|---|---|
| **3F7F**, "no particular page sub-code" (EN 300 706 clause 9.6.1): a page number keyed alone, a link, Fastext key or bookmark naming no sub-page, the page chosen from a list | The page | The page's **first sub-page in ascending order**, 0000 when the page has it, otherwise its lowest sub-code, and the page's SUBPAGES record if the connection lacks its current version. That sub-page then **is** the connection's selection, exactly as if its sub-code had been chosen: the server records it when it forwards the program's answer, the receiver records it from the frame and sends no second SELECT, and stepping goes on from it |
| **A sub-code** 0000 to 3F7E: a step to the next or previous sub-page, a choice from the sub-page list, an address or link naming a sub-page | That sub-page | That sub-page alone, and the page's SUBPAGES record if the connection lacks its current version; then that sub-page's later versions, as changed rows (section 6.3) |

| When | What the connection is sent |
|---|---|
| At connection | Nothing until the program answers `connected`; then the channel's index records (page-level), the one sub-page the connection's selection shows (the program's initial page with 3F7F when it named none), its LINKS record when it has links, and its page's SUBPAGES record |
| The selection changes (SELECT, or the program's page redirect) | The one sub-page the new selection shows, whole, as the table above says, with its LINKS record and, if needed, its page's SUBPAGES record |
| The program sends a new version of the selected sub-page | That sub-page as changed rows, followed by its LINKS record when it has links |
| The program sends any other sub-page to the connection | Nothing: a sub-page reaches a connection only when it is that connection's selection |
| The program changes the selected page's sub-page list | The new SUBPAGES record |
| The selected page does not exist, is refused, or the program does not answer in time | DENIED (section 5.5) |

**No rotation on a live channel** (DEC-1526 item 4). The sub-page a connection shows never changes by itself. It changes only when the receiver selects another, or when the program moves the connection with a page redirect (the `redirect` message naming a page, `C/INPUT.md` section 7.11), which is itself a selection the server records exactly as it would a SELECT. A `redirect` naming another channel's address changes no selection: the receiver leaves (REQ-1688). Neither is an HTTP redirect from a web server (REQ-701). A program that sends another sub-page of the selected page does not change what is shown: it is not forwarded. A broadcast recording played back as a stream (section 5.3) keeps the broadcast's own rotation.

**The program is the only source of content** (DEC-1482). The server answers nothing from a store: every sub-page a connection is sent is one the program sent for that connection, in answer to `connected` or `selected` (REQ-1471, REQ-1472) or as a change. The program answers a 3F7F selection with the page's first sub-page in ascending order; the TypeScript kit makes that answer for the program.

- **Why one sub-page:** each selection, step and update costs one sub-page at most, about 1 to 3 KB, and the browser treats pages and sub-pages the same way. The cost is a round trip to the program for each step through a page's sub-pages (DEC-1500's cost accepted).
- **Bounded per connection:** what a connection is sent grows with what its viewer selects, one sub-page at a time, never with the pages or sub-pages in the channel.
- **What the channel learns:** which page and which sub-page each viewer reads, detail a channel already has of the page a viewer types into. **The consequence, accepted by the owner on 25 October 2026 for tuning, stands:** a compromised interface could signal what it saw on one channel through what it selects on another. The trusted core sends SELECT from what the tab shows and limits how fast it may change (section 11).
- **Level 2.5 and 3.5 pages:** how a selected sub-page's object pages, DRCS pages and MOT reach the receiver, now that the program is the only source, is not yet designed (section 20 item 7).
- *Withdrawn on 30 October 2026:* a page selection bringing every sub-page of the page (29 October, DEC-1089 as first written); each shared page's first sub-page sent to every connection; the receiver rotating sub-pages from what it holds; several views sharing one connection with a view number in SELECT and `MAX_VIEWS` (DEC-1527); a 3F7F selection showing "the page's current sub-page" with the program's later sub-pages of the page reaching it as rotation (DEC-1500 as first written, amended by DEC-1526).

### 6.2 The page store

*Withdrawn on 30 October 2026* (DEC-1482 item 2, REQ-1474): the server keeps no page store. It holds no page, sub-page, index or version between connections or across a restart. The program is the only source of a channel's content; a program that wants to share work between viewers does so itself. The one thing the server keeps of any page is each connection's last-sent sub-page, used only for changed rows (section 6.3).

### 6.3 The sender

- **Per connection, one kept sub-page** (DEC-1499, as amended by DEC-1526 and DEC-1527; REQ-1474, REQ-1504). For each open connection the server keeps, in memory only, the last sub-page it sent that connection: its page number, its sub-code and its packets as sent. Because the connection has one selection, and a 3F7F selection becomes the concrete sub-page that answers it, this is the sub-page the connection's selection shows. It is at most one sub-page, 3,108 bytes, a connection, whatever the size of the channel; two tabs on one channel are two connections, each with its own.
- **Changed rows only against the same sub-code.** When the program sends the connection a sub-page with the same page number and the same sub-code as the kept one, the server compares the two (25 row comparisons and the enhancement group) and sends a page frame of the header without the erase bit, the changed rows, the whole enhancement group if any of it changed, and then the LINKS record if the sub-page has links. Nothing is sent when nothing differs. It then keeps the new version.
- **Any other sub-page goes whole and becomes the kept one.** A sub-page with a different page number or a different sub-code is never compared with the kept one: it goes whole, with the erase bit, followed by its LINKS record if it has links, and replaces the kept one. With no rotation, a different sub-code reaching a connection is always a new selection, never a change to the one shown. The first sub-page on a new connection and the first after the selection changes go whole for the same reason: the receiver's store may hold an older version.
- **When it is dropped.** The kept sub-page is dropped when the connection's selection changes and when the connection closes. It is never written to storage, never kept across a restart, never shared between connections, and never served to anyone: it is only compared against. A reconnected receiver starts with a whole sub-page.
- **Encoded once.** A sub-page the program sends to several connections is encoded once; each connection's changed rows are taken against its own kept version.

**Why:** programs stay simple, sending whole sub-pages, while viewers receive only what changed: a clock or a score changes one row, about 84 bytes (a header and one row), instead of about 1,800. What is kept is exactly what that connection was last sent, so the diff is correct by construction, and there is nothing to invalidate.

**Flush policy, per page, overridable per publication:**
- `immediate`: every change becomes a frame;
- `batch`: a packet count or a delay, whichever comes first;
- `manual`: the application sends `flush`.

A client may ask to be slower, never faster.

*Not yet revisited for DEC-1482:* the program's closed set of messages (REQ-1476) has no publications and no `flush`, and the server sends each sub-page as the program sends it. Whether a flush policy, and with it the coalescing of a slow client's frames, is kept is open (section 20 item 10).

### 6.4 Queues for ordered data

Stream, audio and control frames pass through a bounded queue per client, with a policy per source:
- **drop the oldest whole record** for live audio;
- **latest wins** for audio commands;
- **close** for an authentic stream that must not lose data.

Nothing ever drops part of a page frame.

### 6.5 The channel's index (for the browser's overview)

The browser's overview shows every page's status: which exist, their titles, "updated 12 s". Without broadcast, that needs:

- **INDEX at connection:** page numbers and titles, from `contents.txt` or the MOT;
- **CHANGED, opt-in:** page numbers of pages that changed, coalesced, at most every few seconds.

It costs bytes in proportion to the audience, but only numbers, and only for clients that asked. **The owner chose this** (25 October 2026), over an overview showing only tuned pages.

## 7. Applications

### 7.1 Process and transport

- **Applications run outside the server, in any language.** They never see packets (except through section 7.4), connections, headers or cookies' raw form.
- **One instance serves every viewer,** multiplexed by session; never a process per viewer.
- **Bindings:** stdio first, the server spawning the process; a socket second; in-process WebAssembly later, for the lowest latency.
- **Messages:** newline-delimited JSON.

### 7.2 Messages

| Direction | Message | Meaning |
|---|---|---|
| Server → app | `open {session, page, identity, cookies}` | A viewer tuned a page the application personalises; `identity` is the verified one, if any (section 8.3) |
| Server → app | `input {session, page, sub, event}` | An INPUT.md event for the selected page, with the page and sub-code of its stamp, as the decoder gives it; a release the page lost carries `lost: true` |
| Server → app | `focus` / `blur {session, page}` | The page gained or lost the keyboard focus (FOCUS_IN, FOCUS_OUT) |
| Server → app | `first_viewer` / `last_viewer {page}` | A channel page gained its first or lost its last viewer, so the application may idle; it publishes at once on the next |
| Server → app | `close {session}` | The session ended; discard its state |
| Server → app | `tick {timer}` | A timer the application asked for (for WebAssembly applications, which have no clock) |
| App → server | `publish {page, sub?, owner, tti \| rows \| region}` | Content, at any granularity (section 7.3): a sub-page, several, or every one |
| App → server | `remove {page, subs, owner}` | Sub-pages that end; the others are kept |
| App → server | `packets {stream, owner, base64}` | Raw packets (section 7.4) |
| App → server | `audio {owner, play \| object \| record}` | Sound (section 9) |
| App → server | `cookie {session, set-cookie}` | Write a viewer's cookie (section 8.2) |
| App → server | `flush {page?}` | Send what is held, in `manual` mode |
| App → server | `timer {id, every_ms \| at}` | Ask for ticks |

`owner` is `channel` or a session id.

### 7.3 Content and ownership

- **Content is TTI**, the engine's format, which teletext editors and archives use:
  - `tti` is a whole page;
  - `rows` is `OL` lines;
  - `region` names a region the channel declares.

  The engine's `TtiReader` parses it, fuzzed, with its escapes, national option sets (the control bits C12 to C14 and X/28), Fastext and links. There is no second row-text format to define. One content format serves files, applications and tests, and a page moves between a file and an application unchanged.
- **A publication puts sub-pages, not a page:** it names each sub-page it carries by sub-code (TTI's `SC`, four hexadecimal digits) and leaves the page's others as they were, so a page of 8,190 sub-pages changes one sub-page at the cost of one. An application never states a limit of its own: the server tells it the standard's maxima and the server's budgets in `start` (`STANDARD-LIMITS.md` section 3).
- **Ownership is where the content was published:**
  - `owner: channel` is one shared copy, sent to every viewer tuned;
  - `owner: <session>` is that session's views only.
- **A page may be shared with a private overlay:** the channel's page plus rows the session owns (a logged-in header). The shared rows fan out once; the overlay costs its rows per viewer.
- **Cookies reach the application only in `open`, which is per session.** A channel-owned publication answers no session and carries none of its data. An application can still copy a viewer's data into a channel page on purpose, but not by answering a request, which is how the first draft's per-response flag could leak a page.
- **The kit keeps the screen buffers.** The reference kit holds each page's working copy in the application; `refresh()` sends the rows that changed, never a stream of drawing calls. The server validates what arrives:
  - well-formed TTI;
  - a page number within the channel;
  - the owner a session the application holds;
  - limits.
  It then commits the new version.

```ts
app.page(100, async (page) => {            // the channel's: one shared copy
  page.write(5, 2, `TEMP ${await weather()}`);
  page.refresh();
});

app.session.page(500, (session, screen) => { // each session's own
  session.onInput((event) => {
    if (event.key === "Left") moveLeft(session);
    drawPlayer(screen, session);
    screen.refresh();                         // the changed rows only
    if (event.key === " ") session.audio.play("laser");
  });
});
```

### 7.4 Raw packets

An application may publish packets directly, for:
- imported broadcasts;
- exact effects;
- a generated station.

As a page's content they are validated and then delivered as page frames. As a `stream` they are delivered as stream frames, in authentic mode (section 5.3). The server checks:
- Hamming and parity where the standard requires them;
- that each header addresses a page within the channel;
- that each packet is of a kind the stream may carry (REQ-1462): a page's X/0 to X/28, M/29, 8/30, or 4/31 on data channel 12. A packet that fails any check is refused when it is published, and never sent.

### 7.5 Isolation and failure

- **The network loop never waits for an application.** Each application has a bounded inbound queue; when it fills, the server drops `open` and coalesces `input` beyond the limit, and says so in the console.
- **A crashed application** is restarted with backoff:
  - its channel pages stay as last published, marked stale;
  - its sessions' pages end;
  - tunes of them get DENIED (unavailable) until it returns.
- **A stalled application** (no answer to `open` within a limit) is treated as crashed for that session.

## 8. Sessions, cookies and identity

### 8.1 Sessions

- **A session is a viewer's relationship with a channel's application.** It is not a connection: a connection lost leaves the session for a grace period of minutes, since phones close background sockets.
- **A session may be watched from several views,** and one viewer may hold several sessions.
- **A reconnection is a new input session** (INPUT.md). On reconnecting, the client re-tunes and receives each tuned page whole. The application's session outlives connections through the session cookie (section 8.2), so the protocol needs no resume message.
- **A session page starts at its first `open`,** lives while any of its views tunes it, and is released after a time untuned or at the session's end.

### 8.2 Cookies

- **HTTP cookies, as the engine implements them** (RFC 6265bis, stricter: host-only, scoped to the channel folder, sent on the WebSocket upgrade and on each GET; separate jars for the browser's private tabs). The browser's trusted core already holds them, with its cookies panel, Clear-Site-Data and history clearing (browser decision 62). There is no second cookie model.
- **Mid-connection,** an application's `cookie` reaches the client as a SET_COOKIE record (type 8, `C/INPUT.md` §7.7) holding one `Set-Cookie` value, which the server builds from the typed message with the engine's encoder. The client applies it with the same parser as an HTTP response's.
- **The session cookie** is `__Host-`-style and the server's alone. Names beginning `_` are reserved for the server.
- **Signed cookies:**
  - the server HMACs the name, value, channel and an expiry;
  - it keeps the current and previous key, for rotation;
  - a value that fails is dropped before the application sees it.

### 8.3 Identity

"Authenticated" means a signed cookie the server verified, carrying an identity. **How a viewer logs in is not designed** (section 20): teletext has no password field, and the browser's typing badge says where keys go, but a login flow is still needed, typed on a page or delegated to the web. Until then `identity` is empty and applications see sessions only.

### 8.4 Application state

The server is not a database. A session's state lives in its application: in memory, a database, or a service. A kit's `session.get` is the application's own store.

## 9. Audio

**Audio is the engine's profile, decided in engine decisions E.84 to E.86** (`docs/spec/design/audio.md`):
- PCM16 and IMA ADPCM;
- eight rates from 8 to 48 kHz;
- records of at most 1 KB with a CRC-32;
- carried as EN 300 708 packets 4/31 on data channel 12;
- one record a WebSocket message;
- the latest command wins;
- a page's sound plays while the page is open.

It must stay compatible with tellyboy's `audio-sd` on microcontrollers.

**The second draft's three cases map onto it:**

| Case | In the profile |
|---|---|
| A sound event ("laser") | A stored sound object, sent once, played by a command record |
| An audio asset | An object, sent once; or, for long material, a file fetched over HTTPS by the client |
| A continuous stream | Live records |

**Transport:** audio frames on the page connection, through the ordered queue of section 6.4. IMA ADPCM at 16 kHz mono is 64 kbit/s, about 240 packets a second, near 10 KB/s. A page frame of 1 KB delays it by under a millisecond on broadband, and the client keeps a jitter buffer near 200 ms.

**Not WebRTC.** It would add a very large stack to the browser's sandboxed processes and a second media model, for a stream the WebSocket carries. A separate connection is the fallback if measurement on a lossy mobile link shows audio stalling behind pages.

## 10. Latency

Low latency is a requirement from the start, not a later optimisation. The critical path is:

> key → the trusted core → the WebSocket → the server → the application → `refresh` → page frame → the client

- **No broadcast cycle on it:** input is dispatched at once, and a publication flushes at once under `immediate`.
- **Ticks:** a game ticks on its own clock and publishes when the tick completes.
- **Sound:** a sound can go before the next screen refresh.
- **The budget is the browser's existing one:** a pushed packet to the screen within 20 ms, and a key's round trip within 20 ms on a local network. The browser's latency test (`B/core/tests/latency.rs`) measures it, and runs against the server once section 3.3's port is done.

## 11. Limits

**Maxima are not limits here** (`STANDARD-LIMITS.md` section 2): every page and sub-page the standard allows may exist, 2,022 page numbers a channel (shared by display and data pages) and 8,190 sub-pages a page, defined once in the engine (`neoteletext_core::limits`), every numbering rule being a requirement of the engine's area NUM (its decision E.130). What follows are budgets, which bound what is held and sent at once, never what may exist.

About ten numbers, in the server's configuration, overridable per channel, advertised in LIMITS:
- SELECTs a second, as other inbound events;
- session pages per session;
- connections per address and per session;
- inbound events per second and bytes per message;
- queue depth per client (ordered data);
- `open` per session per second (to an application);
- an application's inbound queue.

Replaceable things degrade: a tune is refused, or a page resent. Abusive things close the connection with a reason. The values are measured on the reference applications (section 16), not guessed.

## 12. Memory and cost

Cost grows with pages viewed plus viewers, never with pages in the channel and never with pages × viewers. A thousand clients on page 100 of 800 cost:
- one encoded page;
- a thousand sockets;
- a thousand last-sent pointers;
- a thousand writes per change.

The other 799 pages are files until tuned.

| What | Grows with | Held as |
|---|---|---|
| Page store | Pages tuned | Rows and encoded bytes, shared |
| Connection | Clients | Socket, tuned set, one pointer per tuned page, the focused page |
| Session | Viewers of applications that personalise | Cookie, application handles, time to live |
| Application state | Its sessions | Inside the application: the expensive, unavoidable term |

A whole Level 1 page is 1,092 bytes. A channel at the standard's maximum, 2,022 pages × 8,190 sub-pages, would be about 18 GB held whole; it is held as its applications publish it and its files are read, and only tuned sub-pages are sent, so the cost follows what is read. Connections and sessions are the memory to watch, not pages.

## 13. Carousel: an authentic broadcast

An optional module, not the normal path:
- it walks the channel's shared pages into one continuous stream per channel, at broadcast rate or as fast as the link allows;
- priority pages repeat;
- changed pages come forward;
- private pages never appear.

It can go to the WebSocket as stream frames, UDP multicast on a local network, or a `.t42` file; never as chunked HTTP, since the server answers no HTTP but a channel's `channel.json` and its WebSocket (DEC-1467). A client in this mode is a decoder joining mid-cycle, as a television did. A `.t42` recording plays back as a carousel, or splits into pages for tuning.

## 14. Security

| Threat | Answer |
|---|---|
| A private page shown to others | Ownership decides sharing, by where content was published; cookies reach applications only per session (section 7.3) |
| A compromised client interface steering requests | Accepted by the owner: the interface decides tuning (section 6.1); the trusted core limits how fast the tuned set may change |
| A compression oracle on private rows | No `permessage-deflate` (section 5.1) |
| Forged or replayed cookies | Signed with expiry, two keys for rotation (section 8.2) |
| A hostile application | Validated output (section 7.3): its page numbers within its channel, its sessions its own, its packets well formed; bounded queues; no process per viewer to exhaust |
| A flooding client | Limits, rate on events and tunes (section 11) |
| A stolen session cookie | Works for the grace period; device-bound session credentials (the engine's `dbsc`) are the later answer |
| A channel learning what is read | Accepted by browser decision 104: the price of tuning |

## 14a. Lessons from Lightstreamer

Lightstreamer is a commercial real-time streaming server, used for live financial data. Its documented model, set beside this design, on the owner's question of 25 October 2026:

| Lightstreamer | Here | What to take |
|---|---|---|
| Items with fields; **MERGE** mode keeps only each field's latest value for a slow client | Page frames: a slow connection gets each page's latest version (section 6.3, decision 7 of `teletext-server`) | The same idea, already built |
| **DISTINCT** and **RAW** modes deliver every update in order | Stream, audio and control frames through an ordered queue (section 6.4) | The same |
| **COMMAND** mode: a keyed table of rows that clients add, update and delete | A list page whose rows change (guestbook, scores) | Nothing new: a page frame of the changed rows does it |
| A maximum update frequency per subscription, and bandwidth allocated per session, lowered when a client falls behind | Flush policies per page (section 6.3); no limit per session yet | **Take:** a bandwidth ceiling per connection, so one viewer of a fast game cannot use what many viewers of shared pages need |
| A snapshot sent on subscription | A tuned page sent whole first (section 6.1) | The same |
| Stream-Sense: WebSocket, falling back to HTTP streaming and then polling where proxies block WebSocket | WebSocket only | **Decided:** WebSocket only, with no HTTP streaming or polling fallback (DEC-1467, 30 October 2026); a network that refuses the upgrade cannot reach a live channel |
| Data adapters (sources) and metadata adapters (who may see what, limits) apart from the server | Applications (section 7) and the server's ownership and limits (sections 7.3 and 11) | The same split |
| Clustering behind a load balancer with sticky sessions | One actor per channel; fan-out over several servers deferred (section 20 item 3) | Sticky routing by channel, as noted |

## 15. What is not built

- Distributed actors or per-page services.
- Redis, Kafka or any required infrastructure.
- Server-side screen buffers per connected user.
- Packet replay logs per client.
- Sequence numbers or versions on the WebSocket.
- A general delta synchronisation framework.
- Subscription priority classes.
- Resource tokens or leases.
- A process per user.
- A broadcast scheduler for interactive pages.
- Server-side sub-page rotation.
- JSON on the client wire.
- A second cookie model.
- WebRTC, WebTransport and QUIC, until measured.
- Compression of the stream.
- A copy of the engine.

## 16. Proving it: three reference applications

| Application | Proves | Measured |
|---|---|---|
| A static T42 channel | Packet fidelity, addressing, the static layout, a plain HTTPS host | Bytes per page, the first page's time |
| A shared weather page | One copy, live row changes, fan-out to many | Publication work, bytes per change per viewer, thousands of clients |
| Space Invaders | Fast input, sparse rows, per-session state, frequent publication, sound | Keypress to display, queue delay, many players while other pages update |

The reference channel's invaders (page 300) and typing (page 200) already exist and port first.

## 17. Order of work

Each step is usable on its own.

1. **In `teletext-server`, the pieces of section 3.2:**
   - the row diff;
   - the push protocol crate, both sides, which the browser will import;
   - INPUT.md's SELECT;
   - the channel side of an input session;
   - server WebSocket frames;
   - the descriptor and contents writers;
   - `Set-Cookie` writing and signing.

   Each imports the engine's page model, encoder and codes.
2. **The server repository:** the static layout over HTTPS with `ETag`; the runtime actor with the page store, tune tables and last-sent pointers.
3. **The WebSocket:** HELLO, WELCOME, SELECT; page frames; flush policies; conflation.
4. **Applications over stdio:** TTI content, ownership, overlays, `open`, `input`, cookies, validation, isolation.
5. **`B/site` ported to applications;** the browser's tests and latency test against the server.
6. **The browser:** the trusted core's tuning (decision 104), INDEX and CHANGED, sub-pages, enhanced pages' references.
7. **Sessions, grace and limits;** the three reference applications measured; the limits set.
8. **The audio cycler;** then the carousel.
9. **As measurement asks:** QUIC or WebTransport, socket and WebAssembly applications, Cloudflare Workers, fan-out over several servers.

## 18. Pros and cons of the whole

**Pros:**
- **Little new teletext code:** the encoder, parser and codes exist.
- **One protocol per boundary,** each implemented once for both sides: INPUT.md on the client wire, JSON to applications.
- **Every existing channel and client works.**
- **Correct by construction** under slow clients and loss of a connection.
- **Private pages cannot be shared by a slip.**
- **Cost grows with what is watched.**
- **The stream is real teletext.**

**Cons:**
- **The channel's server learns what is on screen** (decision 104's price).
- **A protocol change touches two repositories:** the push crate in the server, then the browser's pin.
- **One header per update** costs 42 bytes a viewer.
- **One actor per channel needs sticky routing** behind a load balancer.
- **The overview needs INDEX and CHANGED,** which are traffic broadcast did not cost.

## 19. Decisions for the owner

1. **Decided 25 October 2026: B.** A repository of its own, `~/devel/teletext-server`, private on GitHub, importing the engine at a pinned revision; the engine's scope unchanged; what the engine lacks written in the server once (section 3.2).
2. Four frame kinds, a page frame always self-contained in serial mode (section 5.2).
3. INPUT.md upstream, with SELECT as an extension (29 October 2026; TUNE and UNTUNE withdrawn); no JSON on the client wire (section 5.4).
4. Control as teletext records, including SET_COOKIE, INDEX and CHANGED (section 5.5).
5. The engine's channel layout, not new paths (section 4).
6. Ownership by publication, not a per-response flag (section 7.3).
7. Applications send TTI (section 7.3).
8. HTTP cookies; sessions as cookies; no resume message (section 8).
9. Audio as the engine's profile, on the page connection; no WebRTC (section 9).
10. ~~What counts as visible in the browser, and the overview~~ **Decided 25 October 2026:** the open page, the wall's thumbnails as previews, and each background tab's open page fully live; the overview gets INDEX and CHANGED; the interface decides what is tuned (sections 6.1 and 6.5).
11. `B/site` becomes the server's applications (section 3.3).
12. One reference kit, in TypeScript (section 3.4).
13. **Decided 26 October 2026:** the engine, the server and the browser allow every page and sub-page the standard allows, 2,022 page numbers and 8,190 sub-pages a page, defined in one place, the engine's `neoteletext_core::limits`, and sub-pages pass the wire only when tuned (`STANDARD-LIMITS.md`; sections 4, 5.4, 5.5, 6, 7.3, 11 and 12). *28 October 2026:* every address the standard defines is accepted and every numbering rule of World System Teletext is a requirement, the engine's area NUM (its decision E.130, the browser's decision 119, the server's decision 14).
14. **Decided 29 October 2026:** the receiver sends SELECT, which page and which sub-page each view has selected, whether or not keys go to the channel; the server sends every connection each page's first sub-page, and a page's sub-pages only to the connections that select it, at that time and as they change (sections 5.4 and 6.1). It replaces item 13's tuning of single sub-pages, with its TUNE, UNTUNE, TITLES, SUBPAGES and TITLES records, which were never built, and item 10's previews: thumbnails show first sub-pages.
    *Amended 30 October 2026:* item 14 is replaced by DEC-1500, DEC-1526 and DEC-1527: one connection per tab with one selection and no view number; one sub-page a frame, never a page's sub-pages together; a page selected with 3F7F shows its first sub-page in ascending order, which becomes the selection; no rotation on a live channel; and no page store, so no connection is sent first sub-pages it did not select (sections 5.1, 5.2, 5.4, 6.1 and 6.3).

## 20. Unsolved

1. **Login:** how a viewer authenticates, with no password field, typed on a page or delegated to the web (section 8.3).
2. **Selection's rate limit in the browser:** with the tabs deciding what is selected (section 6.1), the value that narrows a compromised interface's signal without making stepping through sub-pages slow.
3. **Routing:** every connection to a channel reaching its one actor, behind load balancers; fan-out over several servers.
4. **A stalled application's sessions:** how long the server waits before DENIED, and what a viewer sees meanwhile.
5. **The delta cache with overlays:** its hit rate when most viewers have overlays; measured on the weather application with a logged-in header.
6. **Header text:** whether clients draw the clock, for every channel, or applications publish it.
7. **Enhanced pages' references:** how many object, DRCS and MOT pages a single tune may bring in. (The sub-page limit is settled: `STANDARD-LIMITS.md`.)
8. **Cloudflare:** WebSocket hibernation, and whether Workers can host the actor; not needed for version 1.
9. **Carousel bandwidth** at realistic rates, measured.
10. **Flush policy:** whether the server keeps a per-page flush policy (`immediate`, `batch`, `manual`) and the coalescing of a slow client's frames, now that the program's closed set of messages has no publications and no `flush` (section 6.3).
