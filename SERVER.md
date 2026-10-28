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
| **View** | One place in a client showing a page: a tab, a window, a thumbnail. A client has many; the server knows only which pages are tuned and which one has focus. | Terminal window |
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
   - the TUNE and UNTUNE events (section 5.4);
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

**The engine's channel layout, unchanged** (decision E.70, `requirements/web.md`):
- a channel is a folder on an `https` origin;
- `channel.json` describes it, including `push: {address, method, input}`;
- pages are `NNN.tti` or `NNN.t42`;
- `index.t42` is a bundle;
- `contents.txt` lists and orders the pages.

The server serves exactly this, with `ETag` and conditional requests, which the engine's agent already makes, plus the WebSocket that `push` names. A static channel is that folder on any web server, with no NeoTeletext server.

**Why not new paths** (`/news/200/3`): every channel and client that exists already works with the layout, and a static host needs nothing new.

**Sub-pages have files of their own** (decided 26 October 2026, `STANDARD-LIMITS.md` section 4), since a page may have 8,190 and a page response is bounded (the engine's REQ-WEB-008):
- `NNN.t42` holds the page, or its first sub-page when it has several;
- `NNN-SSSS.t42` holds sub-page SSSS, four hexadecimal digits;
- `NNN.sub` lists the page's sub-codes with their validators and titles;
- `index.t42` carries first sub-pages only.

## 5. The wire

### 5.1 Transport

- **One WebSocket per channel per client**, shared by every view of that channel in that client.
- `TCP_NODELAY` on.
- **No `permessage-deflate`:** the payload is small and already dense, and a private overlay compressed in one context with attacker-influenced public rows makes a compression oracle (CRIME and BREACH).
- **SSE:** the engine's client keeps it for channels made elsewhere; this server needs only the WebSocket, since input needs the upgrade anyway.
- **QUIC and WebTransport** later, only where measurement on a lossy mobile link shows head-of-line blocking. Section 5.2's self-contained frames are what make such a binding possible.

### 5.2 Downstream: four kinds of binary frame

Downstream is binary WebSocket messages, each a whole number of 42-byte packets (the engine's receiver already checks `len % 42 == 0`), of four kinds:

| Frame | Contents | Delivery |
|---|---|---|
| **Page frame** | One sub-page's update: its X/0 header, in serial magazine mode (C11 set), then either the changed rows and, if any changed, the whole group of enhancements (X/26, X/27, X/28); or the whole page with the erase bit (C4) set | Coalesced: a slow client gets the difference from what it last received (section 6.3) |
| **Stream frame** | Packets of an ordered stream: a recording, a carousel, an application's raw packets (section 7.4) | In order, never coalesced, through a bounded queue |
| **Audio frame** | One audio record as packet 4/31 on data channel 12 (section 9) | In order, through a bounded queue |
| **Control frame** | One control record on data channel 12 (section 5.5) | In order |

**Why a page frame begins with its header every time.** A row belongs to the last header sent. A frame that begins with its own header stands alone: it can be applied, dropped or resent by itself, in any binding, with no state carried between frames.

- The cost: one 42-byte header per update, where a second change to the page just addressed could do without. At an update a second per viewed page, that is 42 bytes a second per viewer.
- Serial mode makes the stream valid teletext, and a `.t42` recording of it plays.

**The sender's rules:**
- A **whole page sets the erase bit**, so a page tuned again keeps nothing of its previous version.
- **Enhancements go as a group** whenever any changed, so a page is never inconsistent with them.
- **The header's text is the page's,** published like any row. The server never rewrites it: no clock ticking per viewer. A client draws its own clock, as receivers commonly do, or an application publishes header changes.
- **A page is 25 rows plus enhancements:**
  - header row 0;
  - rows 1 to 23;
  - row 24, the Fastext prompts;
  - X/26 to X/28.

  A Level 1 page with links is 26 packets, 1,092 bytes, one TCP segment.
- **Over WebSocket, frames need no sequence numbers:** TCP is ordered and the server knows what each client was sent. A datagram binding adds a 16-bit sequence number per page, the one place versions would return.

### 5.3 Receiver-compatible and authentic delivery

There are two delivery modes, kept apart:

| Mode | What the client receives | For |
|---|---|---|
| **Receiver-compatible** (the default) | Page frames for the pages it tunes; not the full broadcast | Every page a person reads |
| **Authentic stream** | Stream frames: packets in the original or generated order and timing, unchanged | Recordings, virtual broadcast stations, applications that need exact packet order |

A receiver-compatible stream is not the original broadcast, and the server never claims it is. An authentic stream is never given current-state semantics: nothing in it is coalesced.

### 5.4 Upstream: INPUT.md version 3

Upstream is the input protocol already built on both sides and fuzzed (`C/INPUT.md`). It is binary events framed by `0xFF`, at most 4,096 bytes a message, and has:
- HELLO and WELCOME;
- KEY, MOUSE, WHEEL, PASTE and COMPOSE;
- FOCUS_IN and FOCUS_OUT;
- RESIZE;
- **PAGE**, which says which page has the keys.

Version 3 adds two events, as extensions (`0x40`–`0x7F`, length-prefixed), which a channel that does not know them skips, where an unknown core type would be a protocol error (`C/INPUT.md` §5.4):

| Type | Name | Payload |
|---|---|---|
| `0x40` | TUNE | `count` uv, then `count` × (`page` uv, `sub` uv), `flags` u8: bit 0 `preview` |
| `0x41` | UNTUNE | `count` uv, then `count` × (`page` uv, `sub` uv) |
| `0x42` | TITLES | `page` uv, `first` uv (a place, 1 to 8,190), `count` uv: the titles of those sub-pages, at most the budget a record carries |

**A tune names a sub-page** (decided 26 October 2026, `STANDARD-LIMITS.md` section 4): `sub` is a sub-code, and only tuned sub-pages pass the wire. Tuning any sub-page of a page brings the page's catalogue (SUBPAGES, section 5.5) and its changes; `sub` 0 tunes a page that has no sub-pages, or, on a page that has, its catalogue alone. A sub-code outside the mask or 3F7F is refused.

A channel that does not tune keeps sending what it sends today.

- **Focus** is the existing PAGE event, with FOCUS_IN and FOCUS_OUT: one page per connection has the keys.
- **Keys are never batched or queued** in either direction.
- **No JSON on this wire.** A second protocol on one socket would mean two parsers in the browser's trusted core, and INPUT.md's KEY already carries everything the draft's `key {key}` would have to grow:
  - code;
  - modifiers;
  - text;
  - base character;
  - repeat and release.

JSON belongs to the application protocol (section 7), which people read and write.

### 5.5 Control records

Control records are teletext packets, as WELCOME is today: data channel 12, packet 4/31, the control record type 5 (`C/INPUT.md` §7.2). The kinds are:

| Kind | Fields | Meaning |
|---|---|---|
| WELCOME, PUSH_MODE, POP_MODE, PAGE_MODES | As INPUT.md | As today |
| DENIED | `page`, `reason` code: not found, not allowed, unavailable, limit | A tune refused |
| LIMITS | The standard's maxima and the budgets of section 11 | Advertised after WELCOME, revised at any time |
| SUBPAGES | A page, then its sub-codes, each with its version; or the change since the last | Sent for each page a client tunes, then as its sub-pages are added, removed or changed |
| TITLES | A page, the first place, then titles | The answer to a TITLES request (section 5.4) |
| SET_COOKIE | One `Set-Cookie` header line | A cookie set mid-connection (section 8.2) |
| INDEX | Page numbers and titles | The channel's index (section 6.5) |
| CHANGED | Page numbers | The coalesced change digest (section 6.5) |

Reasons are codes; the words are the client's. A decoder that knows none of this skips the records, as EN 300 708 says.

## 6. Tuning and delivery

### 6.1 What a client tunes

The client says which pages its views show. **The owner decided (25 October 2026):**
- **Tuned:** the open page; the wall's visible thumbnails, as `preview` tunes; and **each background tab's open page, fully live**.
- **Not tuned:** every other page.
- **The interface decides what is tuned**, from what it shows; the trusted core passes its tunes on.

**The consequence, accepted by the owner:** a compromised interface could signal what it saw on one channel through the pattern of tunes it makes on another. Browser requirement 4.7 and decision 20 had kept the interface from steering requests. A limit on how fast a channel's tuned set may change, enforced by the trusted core, narrows that signal without closing it (section 11).

| Tuned | What arrives |
|---|---|
| A sub-page | Its page frame, then its changes; and its page's catalogue (SUBPAGES), then the catalogue's changes |
| A page's other sub-pages | Nothing but their entries in the catalogue, until they are tuned |
| A Level 2.5 or 3.5 page | The pages it references as well: its POP and GPOP object pages, DRCS and GDRCS pages, and the MOT, which the server reads to find them |
| A `preview` tune (a wall of thumbnails) | The page's shared copy only, at a slow rate, with nothing personalised and no `view` sent to its application |
| A page that does not exist or is refused | DENIED |

**Sub-pages:** the server does not rotate them, since that traffic would scale with the audience. The client rotates or steps them (browser decision 67), tuning the sub-page it shows and, within a budget, those either side of it, so stepping is instant; to show the latest as it arrives, it tunes the one whose version in the catalogue changed last. A page may have every sub-page the standard allows, 8,190 (`STANDARD-LIMITS.md` section 1); none passes the wire until tuned.

### 6.2 The page store

- **Each published sub-page is held once:** its rows as shared pointers, its encoded packets, its version and its title, made by the engine's title function when it is published. A row update replaces one pointer and never copies the sub-page. A page is its catalogue: its sub-codes and their versions.
- **Static pages** are read and encoded at their first tune, and held while tuned.
- **A session's pages** are held while the session's views tune them.

### 6.3 The sender

- **Per connection, per tuned sub-page, one pointer:** the version this client was last sent. A change marks the tuned entries dirty; a change to a sub-page the client does not tune marks only its page's catalogue.
- **At a flush,** the sender compares last-sent with current (25 pointer comparisons) and sends a page frame of the changed rows, or the whole page if the client holds nothing.
- **The encoded delta is cached by (previous version, current version)**, so the usual case, every client one version behind, is encoded once. A session's page has one viewer and gains nothing from the cache; its shared base rows do.
- **Slow clients:** they need no queue. A client behind gets, at its next flush, the difference from what it actually received. This is better than a fresh snapshot, never more bytes, and as correct.

**Flush policy, per page, overridable per publication:**
- `immediate`: every change becomes a frame;
- `batch`: a packet count or a delay, whichever comes first;
- `manual`: the application sends `flush`.

A client may ask to be slower, never faster.

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
| Server → app | `input {session, page, event}` | An INPUT.md event for the page with focus, as the decoder gives it |
| Server → app | `focus` / `blur {session, page}` | Keys moved to or from the page |
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
- that each header addresses a page within the channel.

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
- **Mid-connection,** an application's `cookie` reaches the client as a SET_COOKIE control record holding one `Set-Cookie` line. The client applies it with the same parser as an HTTP response's.
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
- tuned pages per connection;
- sub-pages tuned either side of the one shown;
- titles a TITLES record carries;
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

It can go to the WebSocket as stream frames, chunked HTTP, UDP multicast on a local network, or a `.t42` file. A client in this mode is a decoder joining mid-cycle, as a television did. A `.t42` recording plays back as a carousel, or splits into pages for tuning.

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
| Stream-Sense: WebSocket, falling back to HTTP streaming and then polling where proxies block WebSocket | WebSocket only | **Consider:** an HTTP streaming fallback for networks that refuse the upgrade (hotels, some corporate proxies); the engine's client already reads server-sent events |
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
   - INPUT.md version 3's TUNE and UNTUNE;
   - the channel side of an input session;
   - server WebSocket frames;
   - the descriptor and contents writers;
   - `Set-Cookie` writing and signing.

   Each imports the engine's page model, encoder and codes.
2. **The server repository:** the static layout over HTTPS with `ETag`; the runtime actor with the page store, tune tables and last-sent pointers.
3. **The WebSocket:** HELLO, WELCOME, TUNE, PAGE; page frames; flush policies; conflation.
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
3. INPUT.md version 3 upstream, with TUNE and UNTUNE as extensions; no JSON on the client wire (section 5.4).
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

## 20. Unsolved

1. **Login:** how a viewer authenticates, with no password field, typed on a page or delegated to the web (section 8.3).
2. **Tuning's rate limit in the browser:** with the interface deciding what is tuned (section 6.1), the value that narrows a compromised interface's signal without making a wall of pages slow.
3. **Routing:** every connection to a channel reaching its one actor, behind load balancers; fan-out over several servers.
4. **A stalled application's sessions:** how long the server waits before DENIED, and what a viewer sees meanwhile.
5. **The delta cache with overlays:** its hit rate when most viewers have overlays; measured on the weather application with a logged-in header.
6. **Header text:** whether clients draw the clock, for every channel, or applications publish it.
7. **Enhanced pages' references:** how many object, DRCS and MOT pages a single tune may bring in. (The sub-page limit is settled: `STANDARD-LIMITS.md`.)
8. **Cloudflare:** WebSocket hibernation, and whether Workers can host the actor; not needed for version 1.
9. **Carousel bandwidth** at realistic rates, measured.
