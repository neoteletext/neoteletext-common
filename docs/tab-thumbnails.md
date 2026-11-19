# Tab thumbnails: a picture for every tab, with nothing personal written

| | |
|---|---|
| **Status** | Specification and security analysis of 19 November 2026, revised the same day for DEC-6875 version 2, for building in the engine, the server, both program kits, the component library, the channels and the browser. |
| **The owner's decision** | DEC-6875 version 2 (19 November 2026): a tab's picture is the page as seen this run, held in memory only; else an anonymous snapshot kept on disk; else one fetched now for tabs shown in the filmstrip; else a stand-in card. A live channel's snapshot is drawn by the channel's program for an anonymous viewer marked a snapshot (no viewer identity, no stored state, no session, no input), which may decline; the server creates no viewer, counts no new-viewer limit, sends the page and its picture records and closes; the page's public description may answer when the program declines or the page is public. Only real pages drawn successfully are stored; concealed characters are blanked before storing; private windows fetch, read and store nothing; REQ-687 is amended; the limits are provisional until measured. The owner: "implement it, write up as requirements", then, of the program-drawn snapshot, "ok do that". |
| **This document's own choices** | DEC-6878 version 2, waiting for the owner's confirmation. |
| **Process** | DEVELOPMENT.md section 2.3 (a proposal with its security analysis, section 13 here) and section 14 (security). |
| **Repositories it changes** | neoteletext-renderer-teletext (the engine), neoteletext-app-server (the server, and program protocol 16), neoteletext-server-ts-protocol (the TypeScript kit), neoteletext-server-channels (the Python kit, and the channels' kit versions), neoteletext-server-ts-ui-components (the component library), neoteletext-browser, and this repository (the protocol's documentation items and the wire vectors). Static channels do not change. |

**A page, in this document, is one page number and one sub-code together** (DEC-6599). A snapshot is keyed by channel address, page and sub-code; sub-code `3F7F` means the page as a whole, as SELECT means it, never a page's sub-pages shared.

**What changed from the first version of this document.** The first version answered every snapshot from the page's public description (REQ-1728), so a page its program did not mark public had no picture. DEC-6875 version 2 has the channel's program draw the page for a stranger instead. This version adds the program protocol's snapshot messages (section 6) and the kits' and component library's part (section 7), holds snapshot connections apart from viewers' in the server, adds the program's rate and an answers' cache to the server's limits, sends a NAPLPS picture's objects with it, blanks concealed characters before a snapshot is stored (section 10), amends REQ-687 (done: version 7), and adds threats T16 to T20.

---

## 1. The problem and the shape of the answer

The tab filmstrip (REQ-6640) shows a still of each tab's page as the viewer last saw it. Stills are taken in the interface and kept in memory, so after a restart every tab shows a blank stand-in until the viewer visits it. Storing stills on disk would write the viewer's own pages, which may be personal, and would need an image reader in the trusted core.

The answer: what is written to disk is only what any stranger is shown, fetched without anything that identifies the viewer, drawn for a stranger by the channel's own program, kept as page content with concealed text blanked, and drawn by a confined decoder like any page. What the viewer actually saw stays in memory for the run.

## 2. The order of sources (REQ-6883)

For each tab of the window, the filmstrip's picture is the first of:

1. **The still as seen this run**, taken by the interface as REQ-6640 item 3 says. Memory only. It always replaces a still made from a snapshot.
2. **The stored snapshot of the tab's place**, for a tab of a window that is not private. The place is the tab's current address: its channel (`Address::channel_text`), its page or 000 for the channel's initial page when the address names none (a bare address, `wall`, `contents`), its sub-code or 3F7F when it names none.
3. **A snapshot fetched now**, only while the tab's picture is in view in the open filmstrip, for a non-private tab, with the setting on, when none is stored or the stored one is older than `SNAPSHOT_REFRESH` (one hour), and the place has not missed in the last `SNAPSHOT_MISS_RETRY` (15 minutes). An older snapshot shows meanwhile and is kept if the new fetch misses. A live channel's snapshot is the page its program draws for a stranger, or its public description (section 5.2); a static channel's is its page file.
4. **The stand-in card** (section 12), meanwhile and for good.

## 3. The push protocol: capability bit 25, SNAPSHOT (REQ-6879; DOC-1922, DOC-6888)

- `neoteletext_input::caps::SNAPSHOT_CAP = 1 << 25` (33,554,432), in `ALL_CAPS`. Bits 23 and 24 are REGIS and NAPLPS; 25 is the lowest free bit.
- `SNAPSHOT_OFFER = SNAPSHOT_CAP | SELECT_CAP | REGIS_CAP | NAPLPS_CAP`: never CURSOR, TOUCH, RESUME or AGENT, so HELLO carries no user agent text and nothing can be resumed.
- The request is one input message: HELLO (version 10, caps `SNAPSHOT_OFFER`, no agent), then SELECT of one display page, with its sub-code or without one for 3F7F, and no query. Written by `neoteletext_input::snapshot`.
- A receiver whose WELCOME does not agree SNAPSHOT closes at once with code 1000, before SELECT and before answering anything.

**Push protocol 10 does not change.** The bit is additive and compatible both ways:
- A server that does not know bit 25: its HELLO reader reads past unknown bits (the engine's `read_hello` refuses only bit 16), and it agrees only `caps & USED`, so its WELCOME does not agree bit 25. The receiver then closes at once. That server has sent WELCOME and its opening STATE_CHALLENGE, but no viewer exists until a proof is answered (VS-202, VS-304), and the program is told `connected` only after the first SELECT or `FIRST_SELECTION_WAIT_MS`, which never comes: nothing of a viewer is made.
- A receiver that does not know bit 25 never offers it, and WELCOME's caps are a subset of HELLO's, so it is never sent it.

Wire vectors `input hello_snapshot` and `record welcome_snapshot` join `wire-vectors.tsv`.

## 4. The engine's agent in snapshot mode (REQ-6880)

`neoteletext_web::agent::Config::snapshot: Option<SnapshotTarget { page, sub }>`. With it the agent:
1. fetches the descriptor under every existing rule (address rules, local network refused unless allowed, proxy, TLS as the address says, bounds and time limits);
2. for a live channel (the descriptor names a push address) opens the push connection once, sends the snapshot request itself and nothing else, closes on a WELCOME without SNAPSHOT (`SnapshotEnd::NotOffered`), passes pushed messages on, ends `Answered`, `Denied(status)` or `Failed(failure)`, never reconnects, and treats a STATE_CHALLENGE as a protocol error;
3. for a static channel fetches the one file once: the sub-page's own `NNN/SSSS.t42` when a sub-code is named and the channel gives sub-page files, else the page's file; no contents file, list, bundle or other page;
4. sends no conditional request, `Cookie`, `Referer`, `Authorization` or client certificate, and refuses every input message and viewer-state answer its caller gives it;
5. ends everything by `SNAPSHOT_TIME_LIMIT_US`, 15,000,000 microseconds: the connect and response limits, the server's 2,000 ms wait on its program and then 2,000 ms on the description, with room for a slow link, and above the server's 10-second life of a snapshot connection.

## 5. The server (REQ-6881, REQ-6882; DOC-6888, DOC-1950)

### 5.1 What a snapshot connection is and is not

A connection whose HELLO offers SNAPSHOT. WELCOME agrees SNAPSHOT, and SELECT, REGIS and NAPLPS as offered; never CURSOR, TOUCH or RESUME. SNAPSHOT without SELECT is a protocol error.

**Held apart.** When that HELLO is read, the connection leaves the channel's table of connections (`connections`, of `Connection`) and is held only in a table of snapshot connections (`crates/teletext-runtime/src/channel/snapshots.rs`): its address, when it opened, the caps agreed, and whether it awaits a SELECT, an answer for a place, or nothing. No path that reads the viewers' table can reach it, so by construction the server sends it no STATE_CHALLENGE, creates and counts no viewer (`Viewers::admit` is never called; `MOST_NEW_VIEWERS_PER_ADDRESS_PER_HOUR` untouched), never tells the program `connected`, `selected`, `input`, `left` or `gone` of it, never includes it in a message to `"all"` or to a page's viewers, runs no rule table, animation, timeline, sound or synthesizer for it, and counts it as a snapshot (`stats.snapshots`) in its own figures, never in the program's viewer figures. A flag on `Connection` was considered and not chosen: every viewer path would have to remember to check it.

After HELLO, one SELECT of a display page is the only thing allowed; anything else is a protocol error (`CLOSE_BROKE_PROTOCOL`). A query on that SELECT is ignored.

### 5.2 How the server answers

In this order:

| Step | When | What happens |
|---|---|---|
| 1 | No program running | DENIED 503, close |
| 2 | The description cache holds a fresh (`DESCRIPTION_CACHE_MS`) public description of the page whose `content` sub-page is the one selected, or the page was selected whole | That description answers at once; the program is asked nothing (DEC-6875 item 3: "or the page is public") |
| 3 | The snapshot cache holds a fresh (`SNAPSHOT_CACHE_MS`) answer for the same place | A cached page is sent; a cached decline goes to step 5 |
| 4 | Within `SNAPSHOTS_PER_SECOND` (burst `SNAPSHOTS_BURST`) and `MOST_SNAPSHOTS_AWAITED` | The program is sent `snapshot` (section 6) and has `SNAPSHOT_ANSWER_MS` to answer; connections selecting the same place meanwhile wait on the same question. A `snapshot_page` that passes every check is cached and sent to every connection waiting on it |
| 5 | The program declined, answered with something refused, did not answer in time, or was not asked because of its rate | The page's description is asked for through the web visitors' path (REQ-1728: cache, rate `DESCRIPTIONS_PER_SECOND` with its burst, wait `DESCRIPTION_WAIT_MS`), the program hearing the page number and nothing else; a public description that fits as in step 2 is sent |
| 6 | Otherwise | DENIED 404 naming the place, or DENIED 429 when the program was not asked because of its rate; close |

**What is sent for a page:** the sub-page whole as page packets, as a first selection's sub-page is sent (no changed rows, no index, LINKS, SUBPAGES, cursor, rule table, sound or animation record); then, when the answer carries a picture in a language the connection agreed, its REGIS (14) or NAPLPS (17) record (a kept picture as its kept stream stands), and for a NAPLPS picture with objects those objects as one NAPLPS_OBJECTS record (25) as they stand, with no animation, because the shown picture is composed of them (PAR-26; the first version of this document left them out, which would have drawn such a picture without its objects); never DRAWING_LINKS or REGIS_CURSOR; in a language not agreed, the mosaic fallback (REQ-6769). Then a close with code 1000.

| Also | Sent, then a close with code 1000 |
|---|---|
| A snapshot connection limit reached (section 5.3) | WELCOME agreeing SNAPSHOT, DENIED 429 with no place; the program is told nothing |
| `SNAPSHOT_CONNECTION_MS` after opening | DENIED 503 if a SELECT stands unanswered |

Closing a snapshot connection tells the program nothing. A snapshot asked of the program stays awaited until its answer or its time even when every connection waiting on it has gone, and its answer is cached.

### 5.3 Limits (`crates/teletext-runtime/src/snapshot.rs`)

All provisional and unmeasured (DEC-6875 item 7).

| Constant | Value | Bounds |
|---|---|---|
| `MOST_SNAPSHOTS_PER_ADDRESS_PER_MINUTE` | 120 | snapshot connections from one network address on one channel, in `SNAPSHOT_WINDOW_MS` |
| `SNAPSHOT_WINDOW_MS` | 60,000 | its window |
| `MOST_OPEN_SNAPSHOTS_PER_ADDRESS` | 8 | open at once from one address on one channel |
| `MOST_OPEN_SNAPSHOTS` | 1,024 | open at once on one channel |
| `MOST_COUNTED_SNAPSHOT_ADDRESSES` | 65,536 | addresses counted at once, the oldest forgotten |
| `SNAPSHOT_CONNECTION_MS` | 10,000 | a snapshot connection's life |
| `SNAPSHOT_ANSWER_MS` | 2,000 | the wait for `snapshot_page` or `snapshot_declined`; `start.budgets.snapshot_limit_ms` |
| `SNAPSHOTS_PER_SECOND` / `SNAPSHOTS_BURST` | 10 / 20 | `snapshot` messages to one program, a token bucket, half the description rate because drawing costs more than describing |
| `MOST_SNAPSHOTS_AWAITED` | 16 | `snapshot` messages unanswered at once on one channel |
| `SNAPSHOT_CACHE_MS` | 60,000 | how long an answer, a decline included, is kept for its place |
| `MOST_CACHED_SNAPSHOTS` / `MOST_CACHED_SNAPSHOT_BYTES` | 256 / 16 MiB | the cache's places and bytes, the oldest forgotten |

Connections are counted at HELLO, apart from viewer state's counters both ways. The address is taken as VS-304 takes it. However many snapshot connections arrive, from however many addresses, one program is asked to draw at most 10 a second (20 in a burst), 16 at a time, and each place at most once a minute.

## 6. The program protocol's addition (REQ-6900; DOC-6904, DOC-1968, DOC-1970)

### 6.1 Added to protocol 16, without raising it

Program protocol 16 (NAPLPS on the raster, DEC-6856) is new: it exists only on the `parity` branches of the server (head 69b3f67), the TypeScript kit (19.0.0 to 19.1.0), the Python kit (1.1.0) and the component library (27.x), and on the channels' parity builds. Every repository's `livedevelopment` and `main` is at protocol 15 or earlier. The version rule (DOC-1968: raised by one on every change to the shape or meaning of a message, with no compatibility path) protects programs built for a released version; no program was built for 16 except from those branches, which are integrated together, so 16 is still being defined and the snapshot messages are part of it. Raising to 17 would make every parity branch move its version twice for no program's sake.

What is not safe, and what follows: a kit build of 16 from before this addition (TypeScript kit 19.1.0, component library 27.1.0, Python kit 1.1.0) reads the server's messages against the schema strictly and would refuse `snapshot` as an unknown message. So the server built from this specification runs only with channels built on the kits that know it (TypeScript kit 19.2.0, component library 27.2.0, Python kit 1.2.0), and wherever parity builds run they are deployed together, as every parity change already is (TODO-6908). TODO-6874's review of protocol 16 before the parity branch merges includes these messages.

### 6.2 `snapshot` (server to program)

```json
{"type":"snapshot","snapshot":17,"page":"100","sub":"3F7F","path":"100"}
```

- `snapshot`: the snapshot's number, 1 to 2^53 − 1 (`SAFE_INTEGER_LIMIT`), rising, never reused while the server runs, counted apart from connection numbers.
- `page`, `sub` (3F7F for the page as a whole), `path` (`302` or `302/0002`, as `Selection::path` writes it).
- Nothing else: no connection, viewer, `remembered`, query or request number. `ServerMessage::connection()` gives none.
- Meaning: draw this page for no one in particular, as for a connection that has just arrived with no viewer and no query; the answer may go to any stranger for up to a minute.

### 6.3 `snapshot_page` (program to server)

```json
{"type":"snapshot_page","snapshot":17,"page":{"page":"100","sub":"0000","rows":["..."]},"picture":{"kept":"0000"}}
```

(The `page` object is abbreviated here; it has every field of a page message's sub-page.)

- `snapshot`: a number the server awaits.
- `page`: one sub-page in the form of every page message (`Page`, REQ-1478), checked by every rule a page message passes, text runs encoded by the engine's encoder. Its page MUST be the page asked for; its sub-code the one asked for, or any of the page's when 3F7F was asked (a kit gives the first in ascending order, DEC-1526).
- `picture`, optional: `{"kept": "<sub-code>"}`, the picture kept for that same sub-page (audience `"kept"`, PAR-16), which must be kept at the time; or `{"language": "regis" | "naplps", "data": ...}` or with `parts` in place of `data` (exactly one, PAR-21), NAPLPS with `objects` as `description.picture` carries them (PAR-26), at most 262,144 bytes decoded, checked as the `regis` and `naplps` messages are.
- The type has no field for a connection, an audience, rules, sound, links, a cursor, sprites, a timeline, a sub-page list or an index.

### 6.4 `snapshot_declined` (program to server)

```json
{"type":"snapshot_declined","snapshot":17}
```

The program will not draw this snapshot. The server may then answer from the description (section 5.2 step 5).

### 6.5 Refusals, and what cannot be named

- An answer naming a snapshot the server does not await (never sent, answered already, past `SNAPSHOT_ANSWER_MS`): `not_awaited`.
- A `snapshot_page` of another page or sub-code: `wrong_page`; a kept picture not kept: `not_kept`; a picture breaking a picture rule: that rule. Each is then taken as a decline. The refusal's `request` is null; its `detail` names the snapshot's number.
- A snapshot's number is not a `ConnectionId`. Every message that names connections names only connections announced with `connected`, and snapshot connections are not among them, so a snapshot's number used as a connection is refused `unknown_connection`. **This is the whole of what a program may send to a snapshot: the page and its picture, in one message, and nothing else.**
- `start.budgets.snapshot_limit_ms` is 2,000.

## 7. The kits and the component library (REQ-6901, REQ-6902, REQ-6903; DOC-6904)

### 7.1 What both kits do

Both kits answer `snapshot` themselves, so that applications need no new code to be pictured. They **run the page's own selection for a stranger**:

1. Make a snapshot connection of the kit's own, numbered `-snapshot` (below zero, so it can never equal a server connection number and is never written into a message to the server), with no viewer, `remembered` false and an empty query, held apart from the kit's connections so that no fan-out reaches it (a page published to the channel's shared copy, messages to everyone, to a page's viewers, or to a list).
2. Decline at once, calling no application, when no application serves the page or the page is marked never to be pictured (TypeScript `PageEntry.snapshots: false`; Python `App(..., no_snapshots=...)`).
3. Otherwise call the page's application as for a connection that has just arrived with that selection, in `connected`'s order: TypeScript `joined`, `request`, `opened`; Python `on_joined`, `on_request`, `on_opened` (awaited). While it runs, `context.isSnapshot(connection)` (Python `App.is_snapshot(connection)`) is true for it.
4. Answer `snapshot_page` with the sub-page that connection would be shown first, resolved exactly as the kit resolves a reply's (its own copy, else the channel's shared copy; the sub-page asked for, or the first for 3F7F), and its picture: the bytes or parts the application sent to that connection alone for that sub-page during the call (with `restart`, and a NAPLPS picture's latest objects), within 262,144 bytes decoded; else `{kept: sub}` when the kit has sent a kept picture of that sub-page and not forgotten it. Decline instead when the application denied the connection (`deny`, any status, is how an application declines), redirected it, has no copy or no such sub-page, sent a picture past its bound, or a handler threw.
5. Drop every other message the application addresses to the snapshot connection, alone or among others: page messages and lists beyond the answer, indexes, redirects, sound, every rule-table message (`rules`, `query_state`, `local_midi`, `variable`, `timer`, `report`, `run`, `sequence`), every animation message (`frame`, `animate`, `sprites`, `naplps_objects` beyond the answer's, `sprite_sheet`, `timeline`, `timeline_stop`, `object_page`), drawing links and cursors, author's log lines, and viewer state (`request_state`, `end_state`, `offer_remember`). `request_state` on it is answered to the application at once with `state_refused` `stateless`.
6. Then call `leftPage` and `gone` (`on_left_page`, `on_gone`) and forget the connection.

Why run the selection rather than answer from the shared copy: a page that refuses strangers in its request handler (DENIED 403) may still have a shared copy that holds members' content; running the selection declines it. A page drawn for each viewer shows a stranger's version. And no application has to write a second drawing of a page that could drift from the first.

### 7.2 The TypeScript kit, 19.2.0

`ServerEvents.snapshot(snapshot, selection, path)`; a snapshot registry beside `Connections`; `Context.isSnapshot`; `PageEntry.snapshots?: boolean` (default true); `Limits.snapshotLimitMs`; the sender's and the host's drops of section 7.1 item 5; kept pictures tracked per page and sub-code and forgotten on `forgetPicture`, a restart to another audience and `start`; types regenerated from the server's `schema-16.json`. The guide's advice: a snapshot is drawn for no one in particular and may be shown to any stranger for a minute, so draw it from nothing that belongs to one viewer; decline it with `deny` when the page is not one to show strangers; check `isSnapshot` before an effect beyond drawing (counting visitors, telling others someone arrived).

### 7.3 The Python kit, 1.2.0

The same, in the kit's own forms: `snapshot` in the dispatch table (not a handler applications override), `App.is_snapshot`, `App(..., no_snapshots=...)`, `protocol_types.py` regenerated, every message checked by `validate.py`.

### 7.4 The component library, 27.2.0, on the TypeScript kit 19.2.0

**Does the library draw a page for a snapshot connection without its per-viewer state?** Mostly it already does, and this specification makes it certain. At `start` every page is mounted once as the channel's copy, with no connection, no parameters and no kept viewer, and published as the shared copy: that copy is already a stranger's page, and a page that needs no copy of each viewer is answered from it. A page that needs one (`perViewer`, found by the probe, or a viewer's own language) gets a mount for the snapshot connection, because the kit runs its selection. For that mount the library MUST:

1. make it with no parameters, with `KeptComponents` whose viewer is none (`Services.viewer(connection)` returns null for a snapshot), so every kept component shows its default and no viewer's state is read from the store, in the channel's language;
2. do nothing for it on `wantState`, `offerRemember`, `setLanguage`, `play` and every stream call; add `Services.isSnapshot(connection)`; have its own components with effects beyond drawing (sound commands, live streams, timers that report to the channel, feedback that tells other viewers someone arrived) check it;
3. add `PageSpec.snapshots?: boolean`, passed to the kit's `PageEntry.snapshots`; a page whose render or mount calls `deny` for the connection is declined by the kit with no library change;
4. for a picture page, publish the snapshot mount's picture to that connection alone, which the kit carries; a page answered from the channel's copy is named by its kept picture (as the library's description already does);
5. unmount the snapshot connection's mounts and stop their timers when the kit says it left and is gone.

### 7.5 The channels

Every channel's parity build moves to the new kits before it runs under the new server; a channel whose pages are per viewer, closed to strangers, or count visitors is checked by hand and marked or adjusted, each choice recorded in that channel (TODO-6908).

## 8. Across the trusted-core gate, and pacing (REQ-6883)

- **Interface to trusted core:** `ToCore::Thumbnails(Vec<u32>)`, the channel numbers of the window's tabs whose pictures are at least partly in view and have no still, left to right, at most `MAX_TABS`; sent on opening, when a slide settles, when tabs change while open, and empty on closing. Untrusted: numbers not of the window's tabs are dropped; only the latest counts; the interface never names an address, page or file. REQ-687 version 7's fifth exception allows exactly this.
- **Trusted core to interface:** `ToInterface::Thumbnail { channel, page, sub, image }`, the image a teletext page image in the `frame` form the trusted core already checks and encodes, or a ReGIS picture in `ToInterface::Regis`'s form. The interface makes a still of `STILL_WIDTH` by `STILL_HEIGHT` within `MAX_STILLS`, captions it with its page number, and drops the image; one for a tab gone or moved is dropped.
- **`TabInfo`** gains `page: Option<u16>`, `subpage: Option<u16>` and `page_title: String` (at most `MAX_TITLE`, cleaned) for the card.

| Constant (`native/core/src/snapshots.rs`) | Value |
|---|---|
| `SNAPSHOT_FETCHES_AT_ONCE` | 2 in the browser, and 1 to any one host |
| `SNAPSHOT_DRAWS_AT_ONCE` | 2 |
| `SNAPSHOT_REFRESH` | 1 hour |
| `SNAPSHOT_MISS_RETRY` | 15 minutes, in memory only |
| `MAX_MISSES_REMEMBERED` | 256, the oldest forgotten |
| `SNAPSHOT_FETCH_LIMIT` | 20 seconds, then the fetcher is ended: a miss |
| `SNAPSHOT_DRAW_LIMIT` | 5 seconds, then the decoder is ended: a miss |

Nothing is fetched at start, for tabs out of view, or while the filmstrip is shut. A fetch already started finishes and is stored even if its tab leaves the view. All values provisional.

## 9. The anonymous fetcher (REQ-6884)

`neoteletext-fetcher <channel address> --snapshot <page> <sub-code> [--allow-local <ip>]... [--proxy <url>]`, one fresh process per snapshot, started through the broker with the Network role. It is given the address (checked again by the address rules), the page and sub-code, and the proxy and local addresses as a tab's fetcher has them; nothing else, and no state from any earlier process.

It speaks `protocol::snapshot` only. From the trusted core: `Close`. To it: `Confined`, `Piece(Vec<u8>)` (each within `MAX_PAYLOAD`), `Ended(SnapshotEnd)` (answered, denied with status, not offered, too large, failed: one byte of kind, no text from outside). No `protocol::fetcher` message is read or written; `fetcher/src/snapshot.rs` does not use the viewer-state code. It keeps at most `MAX_SNAPSHOT_BYTES` and the trusted core counts the same. It uses the engine's snapshot mode (section 4), names itself as every NeoTeletext request does, and follows the address's TLS and the browser's rule on plain `http`.

A separate program was considered: it adds a binary to the installer, updater and broker, for no more separation than a fresh process with its own message set gives.

## 10. The snapshot decoder (REQ-6885)

`neoteletext-decoder --snapshot`, one fresh process per snapshot drawn, Decoder role, so no two channels share a process (architecture section 6.3). It accepts only `ToDecoder::Whole` (the bytes, in pieces as a pictured page file goes), `ToDecoder::Snapshot { page, sub }` and `Close`.

It draws the one sub-page named (3F7F: the first in ascending order, DEC-1526) as a still: reveal off whatever any view says, no sound, rule table, animation (pictures drawn whole, NAPLPS objects as they stand), flashing (its visible phase), links or fetched fonts (DEC-6669), at the teletext raster or the ReGIS size, as the page area would.

It answers `SnapshotDrawn { page, sub, image }`, preceded by `SnapshotSource(Vec<u8>)` pieces, only when the bytes held a complete sub-page of that page, every reader accepted them, and any picture drew without a fault within its work allowance; else `SnapshotRefused { page, sub, reason }`. The source is the sub-page in a static channel's sub-page file form (`NNN/SSSS.t42`, DOC-2034): its packets as its store holds them (REQ-1558), then its picture's records as packets 4/31 (with a NAPLPS picture's NAPLPS_OBJECTS record), at most `MAX_SNAPSHOT_BYTES`, written by the engine's writer of that form. It sends nothing else of the page and ends.

**Concealed text is blanked in the source** (DEC-6875 item 7). The server sends concealed characters to any stranger, as teletext always has; only the stored copy must not hold them. Every character code that no cell of the page shows when it is drawn with reveal off is blanked in the source:
- a concealed cell's code on its display row (after the Conceal Display spacing attribute until the attribute ends, EN 300 706 clause 12.2; or a cell the enhancement data's display attributes conceal, clause 12.3) becomes a space, 0x20 with its odd parity, unless the same code is shown in another cell, as a held mosaic carried past the concealed run is;
- every X/26 triplet that writes a character into a concealed cell whose character no cell shows is removed;
- spacing attributes, every other packet and every picture record are kept, so the layout does not move.

The concealed cells are found from the decoder's own composed page, at every level, never by reading the bytes a second way. The properties the tests hold: the blanked source drawn with reveal off gives the same image as the original drawn with reveal off; drawn with reveal on, it shows no character that the original shows in no cell with reveal off. If the engine does not expose which cells are concealed and which code each shown cell comes from, that is an engine to-do of the browser's build.

## 11. The store (REQ-6886)

- **Where:** `snapshots/` in the trusted core's settings folder, mode 0700; files mode 0600, never through a link, written whole through a temporary and a rename (`private_file`).
- **Name:** lowercase hexadecimal SHA-256 of the key line, then `.snapshot`. No address in a file name. Tabs on one place share one file.
- **Format 1:**

```
neoteletext-snapshot 1\n
<page, 3 hex capitals>\t<sub-code asked, 4 hex capitals>\t<channel address>\n
<fetched, seconds since 1970 UTC, at most 19 digits>\t<sub-code drawn, 4 hex capitals>\t<body length, decimal>\n
<body: exactly that many bytes, whole 42-byte packets, concealed text blanked>
```

- **Bounds:** `MAX_SNAPSHOT_BYTES` 1,965,054 (asserted equal to the fetcher's `MAX_PICTURED_SUBPAGE_FILE`); `MAX_SNAPSHOT_FILE` that plus the three lines at their longest (the address at `MAX_ADDRESS`); `MAX_SNAPSHOTS` 64 (`MAX_TABS`); `MAX_SNAPSHOT_STORE_BYTES` 32 MiB. Past either of the last two, the snapshots fetched longest ago go first, never the one being stored.
- **Read back as untrusted:** within `MAX_SNAPSHOT_FILE`; every line checked strictly (the key equal to the one asked for and accepted by the address rules, sub-code drawn 0000 to 3F7E, length at most the bound, a whole number of packets, exactly the rest of the file); a failing file is refused whole and deleted. The body goes unread to a snapshot decoder. At start, anything in the folder not named as above, and every file no restored tab's place names, is deleted.
- **Written** only after `SnapshotDrawn`, with the blanked source; a miss leaves an older snapshot as it was.
- **Deleted:** when no tab of a non-private window shows the place (closed, navigated away, moved to a private window); when history is cleared, the snapshots fetched in that time and the remembered misses; all of them when the setting is turned off. A recently closed tab keeps none.
- **Private windows** read nothing from the store, fetch nothing and write nothing.
- **Setting** "Tab pictures", on by default, `tab-pictures on|off` in `settings.txt` (a missing line means on). Panel text: "Show pictures of tabs you have not looked at since NeoTeletext started. The pictures are fetched without saying who you are, only for tabs in view, and kept on this computer." Off: nothing fetched, read or kept; stills as seen this run still show.

## 12. The stand-in card (REQ-6887)

Drawn by the interface, at the still's size, with its own built-in teletext glyphs, from `TabInfo`, never stored:

| Row | Content |
|---|---|
| 1 | a band in the tab's colour (`TAB_COLOURS`), the channel's name in white, cut to 38 characters |
| 9 and 10 | the page number in double height, yellow: `P100`, `P100/0001`, or `Start page` |
| 13 to 14 | the page's title from the tab's history entry, white, cut to 38 characters a row |
| 23 | `No picture yet` in cyan |

Black ground, drawn at the filmstrip's dimmed strength, inside a dashed border in the panel's edge colour, so it is never taken for a picture of the page. It shows while a snapshot is fetched or drawn and for good when there is none (a page its program declines and whose description is not public, any miss, a private tab not seen this run, the setting off), and is replaced at once by a still. It replaces REQ-6640 item 3's blank stand-ins in the filmstrip.

---

## 13. Security analysis

DEVELOPMENT.md sections 2.3 and 14: every new input and output, the threats, and what stops each. The browser's boundaries are its `security-analysis.md` section 4.

### 13.1 New inputs and outputs

| # | Crosses | From, to | Treated as |
|---|---|---|---|
| I1 | The snapshot connection's bytes, a static page file | network, to the snapshot fetcher | untrusted, bounded by the agent's limits and `MAX_SNAPSHOT_BYTES` |
| I2 | `protocol::snapshot` pieces and end | snapshot fetcher, to trusted core | untrusted; counted against `MAX_SNAPSHOT_BYTES`; passed on unread |
| I3 | `SnapshotSource`, `SnapshotDrawn`, `SnapshotRefused` | snapshot decoder, to trusted core | untrusted; the image checked as every frame is; the source bounded and stored unread |
| I4 | A snapshot file | disk, to trusted core | untrusted; three lines parsed strictly, the body unread; fuzzed (`snapshot_file`) |
| I5 | `ToCore::Thumbnails` | interface, to trusted core | untrusted intent: only the window's tabs, latest only, bounded by `MAX_TABS` |
| I6 | HELLO with SNAPSHOT, one SELECT | network, to the server | untrusted; any other item a protocol error; limits of section 5.3 |
| I7 | `snapshot_page`, `snapshot_declined` | program, to the server | untrusted as every program message: schema-strict, every page and picture check, awaited numbers only, bounded |
| O1 | The snapshot request | snapshot fetcher, to the network | nothing of the viewer (threat T1) |
| O2 | `ToInterface::Thumbnail`, `TabInfo`'s new fields | trusted core, to interface | images the trusted core encoded; titles cleaned |
| O3 | Snapshot files | trusted core, to disk | a stranger's page with concealed text blanked, the user's alone |
| O4 | The page and its picture records, DENIED | server, to a snapshot connection | what the program drew for a stranger, or its public description |
| O5 | `snapshot` | server, to the program | a page number, a sub-code and a snapshot number: nothing of any receiver |

### 13.2 Threats and mitigations

| # | Threat | Mitigation | Residual |
|---|---|---|---|
| T1 | A snapshot carries the viewer's identity (key proof, cookie, session token, validator, login) and links the snapshot to the viewer | A fresh process given only an address, a page, the proxy and local addresses; a message set with no field for identity; the engine's snapshot mode refuses its caller's input and state answers, sends no conditional, `Cookie`, `Referer` or `Authorization`, and never answers a challenge; the server's `snapshot` to the program names no connection; tests hold each (REQ-6880, REQ-6884, REQ-6900) | The network address is visible to the server, as for any connection; a server can correlate a snapshot with the viewer's own connections by address and time. "Anonymous" means no application identity. A proxy, if set, applies |
| T2 | A channel makes a page look different in snapshots than to the viewer (a misleading thumbnail) | A channel controls its own pages anyway; a thumbnail is its stranger's page, captioned by its trusted page number and channel name; it opens nothing | Accepted; DEC-6875's reconsideration names it. A program now knows when it draws a snapshot, so it can do this more easily than with descriptions |
| T3 | Malformed or hostile content in a snapshot attacks the browser | It reaches only a confined decoder, one process per snapshot, Decoder role, killed after `SNAPSHOT_DRAW_LIMIT`; the trusted core reads none of it; fuzzed (`decoder_snapshot`) | As for any page: a decoder fault draws a picture of the channel's choosing in that one thumbnail |
| T4 | A local attacker plants or alters snapshot files | The folder and files are the user's alone; read strictly, bounded, refused whole and deleted when wrong; the body drawn only by a confined decoder; names checked; strays deleted at start | Someone who can write as the user can already do more; a planted valid file shows a chosen picture for a place, as a planted session file shows a chosen address |
| T5 | The store reveals what tabs show (privacy on disk) | It holds only strangers' pages of places the session file already names; deleted with its tab, with history and with the setting; never for private windows; not encrypted, like history and the session (`security-analysis.md` section 12) | Equal to the session file's exposure |
| T6 | Concealed text written to disk | Blanked in the decoder's source before it is stored (section 10), found from the composed page at every level; drawn with reveal off always; tests and the fuzz target hold the property | A held mosaic shown outside the concealed run is kept, because it is shown; concealed text is still sent over the network to anyone, as teletext always has |
| T7 | Disk exhaustion through many or large snapshots | `MAX_SNAPSHOT_BYTES`, `MAX_SNAPSHOTS`, `MAX_SNAPSHOT_STORE_BYTES`; oldest dropped | None |
| T8 | A compromised interface drives fetching | It can only name its window's tabs, whose places the trusted core already holds; pacing bounds the rate; REQ-687's fifth exception and its harness test | It can make the browser fetch its own tabs' pages anonymously while the filmstrip is open; it could already navigate those tabs |
| T9 | The snapshot path probes the local network or bypasses address rules | The same address rules, local refusal and allowed addresses as a tab's fetcher, checked again at start | None new |
| T10 | Servers are made to answer snapshots at high rates (amplification, denial of service of the server) | Per-address and per-channel connection limits, a 10-second life, one SELECT; the browser fetches two at a time, only for tabs in view, misses held 15 minutes | A botnet across many addresses meets the per-channel open limit |
| T11 | Snapshots lock real viewers out by spending viewer budgets | Snapshots are held and counted apart from viewers both ways | None |
| T12 | An older server treats a snapshot as a viewer | The receiver closes at once on a WELCOME without SNAPSHOT: no proof answered, no SELECT sent, so no viewer and no `connected` | The older server sees a connection open and close |
| T13 | A snapshot request crosses channels (one channel's content stored under another's place) | The key is the address the trusted core holds for the tab, not anything the content says; the file's key line is checked against the key asked for | None |
| T14 | Thumbnails leak a private tab | Private windows fetch, read and store nothing; their stills stay in memory as today | None |
| T15 | Timing: the browser tells servers when the filmstrip opens | Only for tabs in view, refreshed at most hourly, nothing at start | A channel learns that someone at an address with a tab on one of its pages opened the filmstrip, as decision 104 already lets it learn which pages are on screen |
| T16 | **Snapshots drive a program's rendering cost** (many addresses asking for many pages, each making the program run a page's selection) | The server asks one program at most `SNAPSHOTS_PER_SECOND` 10 a second (burst 20), at most 16 unanswered, each place at most once a minute (the answers' cache, declines included), shares one question among connections on one place, and answers from a cached public description without asking at all; beyond the rate the description path (with its own rate) or DENIED 429 answers. The kits run only the one page's selection; `snapshots: false` and `no_snapshots` let a channel opt a costly page out without running anything | A program pays up to 10 page drawings a second per channel, sustained, from a distributed attacker; the numbers are unmeasured (DEC-6875 item 7) |
| T17 | **A program wrongly shows personal state to an anonymous connection** | There is nothing personal to key on: `snapshot` carries no connection, viewer handle, `remembered`, query, cookie or session, and the kits' snapshot connection has viewer none, an empty query, and a number below zero that no stored state can be keyed by; `request_state` on it is refused at once, so no viewer can be attached to it; the component library gives its kept components no viewer, reads nothing from the state store for it and gives it no parameters; the kits' default answer is the copy the connection would be shown first, which for a new connection is the channel's shared copy unless the application makes it one; the kits' guides say a snapshot may go to any stranger for a minute | An application that shows state not keyed by a viewer (the last visitor's name, a global feed) shows it to snapshots as it shows it to every stranger who connects; that state is already public to anyone who connects. A cached answer may be shown to other strangers for a minute |
| T18 | **A page closed to strangers is pictured** (members' content in a shared copy, with access control in the request handler) | The kits run the page's request and open handlers for the snapshot connection, and a `deny` or `redirect` there declines; the component library's render-time `deny` declines the same way | A page that keeps members' content in its shared copy and denies nobody, relying on never sending it to a connection without state some other way, would be pictured: the kit cannot know. The kits' guides name this; DEC-6878's reconsideration covers it |
| T19 | **Snapshots trigger a program's side effects** (counting visitors, announcing arrivals, starting sounds, timers or streams) | `isSnapshot` in both kits and `Services.isSnapshot` in the library; the library's own effectful components skip them; the kits drop sound, rules, animation and author's log lines addressed to the snapshot connection and call `leftPage` and `gone` at once, so timers and mounts end | An application's own `joined` handler that counts visitors without checking `isSnapshot` over-counts |
| T20 | **A kit's snapshot connection leaks to the server or to viewers** | It is held apart from the kits' connections and never in any fan-out; its number is below zero, which the server's schema refuses for every connection field (minimum 1); a message naming only it is never sent | None |

### 13.3 Changes to existing documents

- The browser's `security-analysis.md`: boundary 2 gains the snapshot fetcher's messages; boundary 3 the snapshot decoder's; boundary 5 `Thumbnail` and `TabInfo`'s fields; boundary 6 `Thumbnails`; section 12 (privacy) the store, its deletion, the blanking and threat T1's residual; section 17 the new fuzz targets.
- The browser's `architecture.md` section 6.4: the new messages; section 6.1: the snapshot modes.
- The server's architecture: snapshot connections held apart, the program's snapshot messages, the limits, the rate and the cache.
- Both kits' guides and the component library's documentation: snapshots, `isSnapshot`, declining, and the advice of section 7.2.
- Documentation items: DOC-6888 (version 2), DOC-6904 (new), DOC-1922 (version 8), DOC-1968 (version 15), DOC-1970 (two rows, TODO-6892).
- REQ-687 amended (version 7, fifth exception: done); REQ-6640 item 3 amended for the card (the browser's to-do).

## 14. What the owner may want to decide

1. Whether a program should be told that a snapshot is a snapshot at all (as here, so that it can decline and skip side effects) or be shown an ordinary stranger's connection (it could not decline, and every visitor counter would count snapshots).
2. Whether the default for an application that does nothing should be to be pictured (as here) or to decline until it opts in; T18 is the residual of the default chosen.
3. Whether private windows may fetch snapshots kept in memory only (here they fetch nothing).
4. The numbers of sections 5.3, 8 and 11, all provisional and unmeasured.

## 15. Records

DEC-6875 version 2 (the owner's), DEC-6878 version 2 (this document's choices, needing confirmation). Engine: REQ-6879, REQ-6880. Server: REQ-6881, REQ-6882, REQ-6900 (the program protocol). TypeScript kit: REQ-6901. Python kit: REQ-6902. Component library: REQ-6903. Browser: REQ-6883 to REQ-6887, REQ-687 (version 7). Documentation items: DOC-6888, DOC-6904 (new), DOC-1922, DOC-1968, DOC-1970 and DOC-1950. To-dos, in build order: TODO-6891 (the engine), TODO-6892 (this repository's wire vectors, DOC-1970 and `PROTOCOL.html`), TODO-6893 (the server), TODO-6905 (the TypeScript kit), TODO-6906 (the Python kit), TODO-6907 (the component library), TODO-6908 (the channels), TODO-6894 (the browser).
