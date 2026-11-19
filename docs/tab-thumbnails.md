# Tab thumbnails: a picture for every tab, with nothing personal written

| | |
|---|---|
| **Status** | Specification and security analysis of 19 November 2026, for building in the engine, the server and the browser. |
| **The owner's decision** | DEC-6875 (19 November 2026): a tab's picture is the page as seen this run, held in memory only; else an anonymous snapshot kept on disk; else one fetched now for tabs shown in the filmstrip; else a stand-in card. Only real pages drawn successfully are stored; a snapshot is page content drawn by the confined decoder; a snapshot connection makes no viewer. The owner: "implement it, write up as requirements". |
| **This document's own choices** | DEC-6878, waiting for the owner's confirmation. |
| **Process** | DEVELOPMENT.md section 2.3 (a proposal with its security analysis, section 11 here) and section 14 (security). |
| **Repositories it changes** | neoteletext-renderer-teletext (the engine), neoteletext-app-server (the server), neoteletext-browser, and this repository (the protocol's documentation items and the wire vectors). Static channels and the program kits do not change. |

**A page, in this document, is one page number and one sub-code together** (DEC-6599). A snapshot is keyed by channel address, page and sub-code; sub-code `3F7F` means the page as a whole, as SELECT means it, never a page's sub-pages shared.

---

## 1. The problem and the shape of the answer

The tab filmstrip (REQ-6640) shows a still of each tab's page as the viewer last saw it. Stills are taken in the interface and kept in memory, so after a restart every tab shows a blank stand-in until the viewer visits it. Storing stills on disk would write the viewer's own pages, which may be personal, and would need an image reader in the trusted core.

The answer: what is written to disk is only what any stranger is shown, fetched without anything that identifies the viewer, kept as page content and drawn by a confined decoder like any page. What the viewer actually saw stays in memory for the run.

## 2. The order of sources (REQ-6883)

For each tab of the window, the filmstrip's picture is the first of:

1. **The still as seen this run**, taken by the interface as REQ-6640 item 3 says. Memory only. It always replaces a still made from a snapshot.
2. **The stored snapshot of the tab's place**, for a tab of a window that is not private. The place is the tab's current address: its channel (`Address::channel_text`), its page or 000 for the channel's initial page when the address names none (a bare address, `wall`, `contents`), its sub-code or 3F7F when it names none.
3. **A snapshot fetched now**, only while the tab's picture is in view in the open filmstrip, for a non-private tab, with the setting on, when none is stored or the stored one is older than `SNAPSHOT_REFRESH` (one hour), and the place has not missed in the last `SNAPSHOT_MISS_RETRY` (15 minutes). An older snapshot shows meanwhile and is kept if the new fetch misses.
4. **The stand-in card** (section 10), meanwhile and for good.

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
5. ends everything by `SNAPSHOT_TIME_LIMIT_US`, 15,000,000 microseconds.

## 5. The server (REQ-6881, REQ-6882; DOC-6888, DOC-1950)

### 5.1 What a snapshot connection is and is not

A connection whose HELLO offers SNAPSHOT. WELCOME agrees SNAPSHOT, and SELECT, REGIS and NAPLPS as offered; never CURSOR, TOUCH or RESUME. SNAPSHOT without SELECT is a protocol error. The server sends no STATE_CHALLENGE, creates and counts no viewer (`MOST_NEW_VIEWERS_PER_ADDRESS_PER_HOUR` untouched), tells the program nothing (`connected`, `selected`, `input`, `left`, `gone`), runs no rule table, animation, timeline, sound or synthesizer, and counts the connection as a snapshot, not a viewer. After HELLO, one SELECT of a display page is the only thing allowed; anything else is a protocol error (`CLOSE_BROKE_PROTOCOL`). A query on that SELECT is ignored.

### 5.2 The answer is the page's public description

The server answers from the page's description for the web (REQ-1728), through the same path, cache (`DESCRIPTION_CACHE_MS`), rate (`DESCRIPTIONS_PER_SECOND` and its burst) and wait (`DESCRIPTION_WAIT_MS`) as a web visitor's, the program hearing the page number and nothing else. This is the one way to answer without running a session: the server keeps no page of its own (REQ-1474).

| When | Sent, then a close with code 1000 |
|---|---|
| Public, and the description's sub-page is the one selected or the page was selected whole | that sub-page whole as page packets (no index, LINKS, SUBPAGES, cursor, rule table, sound or animation record); then, if the description carries a picture (REQ-6768) in an agreed language, its REGIS (14) or NAPLPS (17) record, with no NAPLPS_OBJECTS, DRAWING_LINKS or REGIS_CURSOR; in a language not agreed, the mosaic fallback (REQ-6769) |
| Reserved, not public, not described within 2,000 ms, or another sub-code | DENIED 404 |
| No program running | DENIED 503 |
| A snapshot limit reached | WELCOME agreeing SNAPSHOT, DENIED 429 with no place |
| `SNAPSHOT_CONNECTION_MS` after opening | DENIED 503 if a SELECT stands unanswered |

The consequence the owner should know: **a page its program does not mark public has no snapshot** and shows the card. The TypeScript kit marks a page public only when the application says so in so many words (`description.ts`).

### 5.3 Limits (`crates/teletext-runtime/src/snapshot.rs`)

| Constant | Value | Bounds |
|---|---|---|
| `MOST_SNAPSHOTS_PER_ADDRESS_PER_MINUTE` | 120 | snapshot connections from one network address on one channel, in `SNAPSHOT_WINDOW_MS` |
| `SNAPSHOT_WINDOW_MS` | 60,000 | its window |
| `MOST_OPEN_SNAPSHOTS_PER_ADDRESS` | 8 | open at once from one address on one channel |
| `MOST_OPEN_SNAPSHOTS` | 1,024 | open at once on one channel |
| `MOST_COUNTED_SNAPSHOT_ADDRESSES` | 65,536 | addresses counted at once, the oldest forgotten |
| `SNAPSHOT_CONNECTION_MS` | 10,000 | a snapshot connection's life |

Counted at HELLO, apart from viewer state's counters both ways. The address is taken as VS-304 takes it.

## 6. Across the trusted-core gate, and pacing (REQ-6883)

- **Interface to trusted core:** `ToCore::Thumbnails(Vec<u32>)`, the channel numbers of the window's tabs whose pictures are at least partly in view and have no still, left to right, at most `MAX_TABS`; sent on opening, when a slide settles, when tabs change while open, and empty on closing. Untrusted: numbers not of the window's tabs are dropped; only the latest counts; the interface never names an address, page or file. REQ-687, which lets interface reports drive only the active tab's fetching, is amended for this one report.
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

Nothing is fetched at start, for tabs out of view, or while the filmstrip is shut. A fetch already started finishes and is stored even if its tab leaves the view.

## 7. The anonymous fetcher (REQ-6884)

`neoteletext-fetcher <channel address> --snapshot <page> <sub-code> [--allow-local <ip>]... [--proxy <url>]`, one fresh process per snapshot, started through the broker with the Network role. It is given the address (checked again by the address rules), the page and sub-code, and the proxy and local addresses as a tab's fetcher has them; nothing else, and no state from any earlier process.

It speaks `protocol::snapshot` only. From the trusted core: `Close`. To it: `Confined`, `Piece(Vec<u8>)` (each within `MAX_PAYLOAD`), `Ended(SnapshotEnd)` (answered, denied with status, not offered, too large, failed: one byte of kind, no text from outside). No `protocol::fetcher` message is read or written; `fetcher/src/snapshot.rs` does not use the viewer-state code. It keeps at most `MAX_SNAPSHOT_BYTES` and the trusted core counts the same. It uses the engine's snapshot mode (section 4), names itself as every NeoTeletext request does, and follows the address's TLS and the browser's rule on plain `http`.

A separate program was considered: it adds a binary to the installer, updater and broker, for no more separation than a fresh process with its own message set gives.

## 8. The snapshot decoder (REQ-6885)

`neoteletext-decoder --snapshot`, one fresh process per snapshot drawn, Decoder role, so no two channels share a process (architecture section 6.3). It accepts only `ToDecoder::Whole` (the bytes, in pieces as a pictured page file goes), `ToDecoder::Snapshot { page, sub }` and `Close`.

It draws the one sub-page named (3F7F: the first in ascending order, DEC-1526) as a still: reveal off whatever any view says, no sound, rule table, animation (pictures drawn whole), flashing (its visible phase), links or fetched fonts (DEC-6669), at the teletext raster or the ReGIS size, as the page area would.

It answers `SnapshotDrawn { page, sub, image }`, preceded by `SnapshotSource(Vec<u8>)` pieces, only when the bytes held a complete sub-page of that page, every reader accepted them, and any picture drew without a fault within its work allowance; else `SnapshotRefused { page, sub, reason }`. The source is the sub-page in a static channel's sub-page file form (`NNN/SSSS.t42`, DOC-2034): its packets as its store holds them (REQ-1558), then its picture's records as packets 4/31, at most `MAX_SNAPSHOT_BYTES`, written by the engine's writer of that form. It sends nothing else of the page and ends.

## 9. The store (REQ-6886)

- **Where:** `snapshots/` in the trusted core's settings folder, mode 0700; files mode 0600, never through a link, written whole through a temporary and a rename (`private_file`).
- **Name:** lowercase hexadecimal SHA-256 of the key line, then `.snapshot`. No address in a file name. Tabs on one place share one file.
- **Format 1:**

```
neoteletext-snapshot 1\n
<page, 3 hex capitals>\t<sub-code asked, 4 hex capitals>\t<channel address>\n
<fetched, seconds since 1970 UTC, at most 19 digits>\t<sub-code drawn, 4 hex capitals>\t<body length, decimal>\n
<body: exactly that many bytes, whole 42-byte packets>
```

- **Bounds:** `MAX_SNAPSHOT_BYTES` 1,965,054 (asserted equal to the fetcher's `MAX_PICTURED_SUBPAGE_FILE`); `MAX_SNAPSHOT_FILE` that plus the three lines at their longest (the address at `MAX_ADDRESS`); `MAX_SNAPSHOTS` 64 (`MAX_TABS`); `MAX_SNAPSHOT_STORE_BYTES` 32 MiB. Past either of the last two, the snapshots fetched longest ago go first, never the one being stored.
- **Read back as untrusted:** within `MAX_SNAPSHOT_FILE`; every line checked strictly (the key equal to the one asked for and accepted by the address rules, sub-code drawn 0000 to 3F7E, length at most the bound, a whole number of packets, exactly the rest of the file); a failing file is refused whole and deleted. The body goes unread to a snapshot decoder. At start, anything in the folder not named as above, and every file no restored tab's place names, is deleted.
- **Written** only after `SnapshotDrawn`; a miss leaves an older snapshot as it was.
- **Deleted:** when no tab of a non-private window shows the place (closed, navigated away, moved to a private window); when history is cleared, the snapshots fetched in that time and the remembered misses; all of them when the setting is turned off. A recently closed tab keeps none.
- **Private windows** read nothing from the store, fetch nothing and write nothing.
- **Setting** "Tab pictures", on by default, `tab-pictures on|off` in `settings.txt` (a missing line means on). Panel text: "Show pictures of tabs you have not looked at since NeoTeletext started. The pictures are fetched without saying who you are, only for tabs in view, and kept on this computer." Off: nothing fetched, read or kept; stills as seen this run still show.
- **Concealed text** is stored as the page carries it, conceal attributes and all, and a snapshot is always drawn with reveal off. The characters are in the file, as they are in what the server sends any stranger.

## 10. The stand-in card (REQ-6887)

Drawn by the interface, at the still's size, with its own built-in teletext glyphs, from `TabInfo`, never stored:

| Row | Content |
|---|---|
| 1 | a band in the tab's colour (`TAB_COLOURS`), the channel's name in white, cut to 38 characters |
| 9 and 10 | the page number in double height, yellow: `P100`, `P100/0001`, or `Start page` |
| 13 to 14 | the page's title from the tab's history entry, white, cut to 38 characters a row |
| 23 | `No picture yet` in cyan |

Black ground, drawn at the filmstrip's dimmed strength, inside a dashed border in the panel's edge colour, so it is never taken for a picture of the page. It shows while a snapshot is fetched or drawn and for good when there is none, and is replaced at once by a still. It replaces REQ-6640 item 3's blank stand-ins in the filmstrip.

---

## 11. Security analysis

DEVELOPMENT.md sections 2.3 and 14: every new input and output, the threats, and what stops each. The boundaries are the browser's (`security-analysis.md` section 4).

### 11.1 New inputs and outputs

| # | Crosses | From, to | Treated as |
|---|---|---|---|
| I1 | The snapshot connection's bytes, a static page file | network, to the snapshot fetcher | untrusted, bounded by the agent's limits and `MAX_SNAPSHOT_BYTES` |
| I2 | `protocol::snapshot` pieces and end | snapshot fetcher, to trusted core | untrusted; counted against `MAX_SNAPSHOT_BYTES`; passed on unread |
| I3 | `SnapshotSource`, `SnapshotDrawn`, `SnapshotRefused` | snapshot decoder, to trusted core | untrusted; the image checked as every frame is; the source bounded and stored unread |
| I4 | A snapshot file | disk, to trusted core | untrusted; three lines parsed strictly, the body unread; fuzzed (`snapshot_file`) |
| I5 | `ToCore::Thumbnails` | interface, to trusted core | untrusted intent: only the window's tabs, latest only, bounded by `MAX_TABS` |
| I6 | HELLO with SNAPSHOT, one SELECT | network, to the server | untrusted; any other item a protocol error; limits of section 5.3 |
| O1 | The snapshot request | snapshot fetcher, to the network | nothing of the viewer (section 11.2, threat T1) |
| O2 | `ToInterface::Thumbnail`, `TabInfo`'s new fields | trusted core, to interface | images the trusted core encoded; titles cleaned |
| O3 | Snapshot files | trusted core, to disk | public content, the user's alone |
| O4 | The page and its picture record, DENIED | server, to a snapshot connection | the program's public description |

### 11.2 Threats and mitigations

| # | Threat | Mitigation | Residual |
|---|---|---|---|
| T1 | A snapshot carries the viewer's identity (key proof, cookie, session token, validator, login) and links the snapshot to the viewer | A fresh process given only an address, a page, the proxy and local addresses; a message set with no field for identity; the engine's snapshot mode refuses its caller's input and state answers, sends no conditional, `Cookie`, `Referer` or `Authorization`, and never answers a challenge; tests hold each (REQ-6880, REQ-6884) | The network address is visible to the server, as for any connection; a server can correlate a snapshot with the viewer's own connections by address and time. "Anonymous" here means no application identity. A proxy, if set, applies |
| T2 | A channel makes a page look different in snapshots than to the viewer (a misleading thumbnail) | A channel controls its own pages anyway; a thumbnail is its public page, captioned by its trusted page number and channel name; it opens nothing | Accepted; DEC-6875's reconsideration names it |
| T3 | Malformed or hostile content in a snapshot attacks the browser | It reaches only a confined decoder, one process per snapshot, Decoder role, killed after `SNAPSHOT_DRAW_LIMIT`; the trusted core reads none of it; fuzzed (`decoder_snapshot`) | As for any page: a decoder fault draws a picture of the channel's choosing in that one thumbnail |
| T4 | A local attacker plants or alters snapshot files | The folder and files are the user's alone; read strictly, bounded, refused whole and deleted when wrong; the body drawn only by a confined decoder; names checked; strays deleted at start | Someone who can write as the user can already do more; a planted valid file shows a chosen picture for a place, as a planted session file shows a chosen address |
| T5 | The store reveals what tabs show (privacy on disk) | It holds only public pages of places the session file already names; deleted with its tab, with history and with the setting; never for private windows; not encrypted, like history and the session (`security-analysis.md` section 12) | Equal to the session file's exposure |
| T6 | Concealed text written to disk | Stored as served to any stranger, drawn with reveal off always | The characters are in the file; they are public content |
| T7 | Disk exhaustion through many or large snapshots | `MAX_SNAPSHOT_BYTES`, `MAX_SNAPSHOTS`, `MAX_SNAPSHOT_STORE_BYTES`; oldest dropped | None |
| T8 | A compromised interface drives fetching | It can only name its window's tabs, whose places the trusted core already holds; pacing bounds the rate | It can make the browser fetch its own tabs' public pages anonymously while the filmstrip is open; it could already navigate those tabs |
| T9 | The snapshot path probes the local network or bypasses address rules | The same address rules, local refusal and allowed addresses as a tab's fetcher, checked again at start | None new |
| T10 | Servers are made to render pages at high rates (amplification, denial of service) | Per-address and per-channel limits, a 10-second life, one SELECT; the program is asked only through the description cache and rate, shared with web visitors; the browser fetches two at a time, only for tabs in view, with misses held 15 minutes | A botnet across many addresses meets the per-channel open limit and the description rate, as web crawlers do today |
| T11 | Snapshots lock real viewers out by spending viewer budgets | Snapshots count apart from viewers both ways | None |
| T12 | An older server treats a snapshot as a viewer | The receiver closes at once on a WELCOME without SNAPSHOT: no proof answered, no SELECT sent, so no viewer and no `connected` | The older server sees a connection open and close |
| T13 | A snapshot request crosses channels (one channel's content stored under another's place) | The key is the address the trusted core holds for the tab, not anything the content says; the file's key line is checked against the key asked for | None |
| T14 | Thumbnails leak a private tab | Private windows fetch, read and store nothing; their stills stay in memory as today | None |
| T15 | Timing: the browser tells servers when the filmstrip opens | Only for tabs in view, refreshed at most hourly, nothing at start | A channel learns that someone at an address with a tab on one of its public pages opened the filmstrip, as decision 104 already lets it learn which pages are on screen |

### 11.3 Changes to existing documents

- The browser's `security-analysis.md`: boundary 2 gains the snapshot fetcher's messages; boundary 3 the snapshot decoder's; boundary 5 `Thumbnail` and `TabInfo`'s fields; boundary 6 `Thumbnails`; section 12 (privacy) the store, its deletion and threat T1's residual; section 17 the new fuzz targets.
- The browser's `architecture.md` section 6.4: the new messages; section 6.1: the snapshot modes.
- The server's architecture: snapshot connections and their limits.
- REQ-687 amended (section 6); REQ-6640 item 3 amended for the card (section 10).

## 12. What the owner may want to decide

1. Whether "public on the web" should also mean "may be thumbnailed", as chosen here, or whether programs get a separate mark. With this design, a live page its program does not mark public never has a snapshot.
2. Whether private windows may fetch snapshots kept in memory only (here they fetch nothing).
3. Whether concealed characters should be blanked in what is stored, rather than kept with their conceal attributes.
4. The numbers of sections 5.3, 6 and 9, all provisional and unmeasured.

## 13. Records

DEC-6875 (the owner's), DEC-6878 (this document's choices). Engine: REQ-6879, REQ-6880. Server: REQ-6881, REQ-6882. Browser: REQ-6883 to REQ-6887. Documentation items: DOC-6888 (new), DOC-1922 and DOC-1950 (revised). To-dos, one per repository, in build order: TODO-6891 (the engine), TODO-6892 (this repository's wire vectors and `PROTOCOL.html`), TODO-6893 (the server), TODO-6894 (the browser).
