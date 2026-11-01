# The structure of a channel

| | |
|---|---|
| **Status** | Decided by the owner on 30 October 2026, and to be built: the engine, the server, the browser, the kits and the channels already published change to meet it, with no earlier layout kept beside it ("we are in development so we must go directly to what we want it to be and then update the server and the client and the sites that we have built to comply"). |
| **Replaces** | The channel layout of the engine's REQ-WEB-018, REQ-WEB-019, REQ-WEB-023, REQ-WEB-024, REQ-WEB-026, REQ-WEB-027 and REQ-WEB-034 (decisions E.70, E.122 and E.132), which now point here for every name, format and rule below. |
| **Words** | MUST, SHOULD and MAY as in RFC 2119. A *channel* is a teletext service on the web: a folder of files, and optionally a live connection. A *reader* is anything that opens one: NeoTeletext, `neottx`, a microcontroller receiver. A *generator* is anything that writes one: the server, the build tool, a site generator. |

---

## 1. What it is for

A channel is the web's form of a teletext service. A broadcast sends every page round and round and a receiver captures the few it wants; a channel holds every page at a fixed address and a reader asks for the few it wants. This document defines the whole of a channel: every file, its name, its format and its limit; how an address maps to them; how a reader opens any address it is given; and what a channel may and may not change about how it is shown.

**In scope:** the folder and its files, the URL map, the lists that let a reader navigate without fetching everything, opening any address, the smallest channel, and presentation.

**Out of scope:** what travels on the live connection (`SERVER.md`, `INPUT.md`), what a page's packets mean (EN 300 706, the engine's areas), and how a reader draws.

## 2. Principles

1. **One structure, always the same.** A channel's files have fixed names. The same structure is used, unchanged, by files on disk, an SD card, a `file://` folder, any static host and the server. Nothing in a channel renames, moves or remaps a file, so the URL map is a rule, not a file (REQ-CHN-002).
2. **The page number is the address.** Every file a reader asks for is named from a page number, a sub-code or a part number, and nothing else.
3. **Bounded at every size.** Every file has a maximum a microcontroller can hold. No file grows with the size of the channel but the magazine lists, and they are bounded by the standard's page count (section 7).
4. **What can be derived is generated, never written by hand.** A list says what its files hold; the file is the truth and the list a hint (REQ-CHN-014).
5. **Written by hand stays simple.** A folder of `100.tti`, `101.tti` is a channel. Everything else is optional (section 4).
6. **A channel changes how it is shown, never what proves where the viewer is** (section 11).

## 3. The folder and its files

### 3.1 The channel is a folder

A channel is a folder on a web server, a folder on a computer, or a folder on any storage a reader can read. Its address is an `http` or `https` address whose path ends in `/`, in the canonical form of the engine's REQ-WEB-023; the root folder `/` is a channel like any other. A channel is identified by its origin and its folder path, compared exactly (REQ-WEB-018), and that identity is the boundary for cookies, redirects and links (REQ-WEB-026).

**Page folders belong to the channel.** Inside a channel's folder, a folder named by a page number, three hexadecimal digits with the magazine 1 to 8 first and `A` to `F` in capitals, is that page's folder. Any other folder inside a channel's folder is a channel of its own and inherits nothing (REQ-CHN-003).

### 3.2 Every file

`NNN` is a page number as three hexadecimal digits in capitals, magazine first (`100`, `1FE`); `SSSS` is a sub-code as four hexadecimal digits in capitals, S4 first (`0001`, `3F7E`); `P` is a part number in decimal, 0 to 127, with no leading zeros; `M` is a magazine, 1 to 8.

| Name | Holds | Format | Largest | Tier |
|---|---|---|---|---|
| `channel.json` | The channel's settings | Section 6 | 16,384 bytes | Optional |
| `contents.txt` | The channel's table of contents: sections, pages and titles, in the order shown | The engine's REQ-WEB-025 | 65,536 bytes, 1,000 lines | Optional |
| `index.t42` | The first sub-page of any number of pages, so a channel opens with one request | T42 packets | 262,144 bytes (REQ-CHN-011) | Built |
| `M.pag` | Magazine `M`'s pages: each one's sub-page count, version and title | Section 7 | 17,204 bytes | Built |
| `NNN.tti` | Page `NNN`, with all its sub-pages | TTI (REQ-INP-013) | 262,144 bytes | Hand-written |
| `NNN.t42` | Page `NNN`: all its sub-pages, or only the first when the page has a folder | T42 packets (REQ-INP-002) | 262,144 bytes | Either |
| `NNN.ep1` | Page `NNN`, one sub-page | EP1 (REQ-INP-015) | 1,648 bytes | Hand-written |
| `NNN/SSSS.t42` | Sub-page `SSSS` of page `NNN` | T42 packets | 3,108 bytes (section 5.1) | Built |
| `NNN/P.sub` | Part `P` of page `NNN`'s list of sub-pages | Section 5.2 | 4,119 bytes | Built |
| `push` | The live connection: pages as they change, sounds, and the viewer's keys back | `SERVER.md`, `INPUT.md` | One message 65,536 bytes (REQ-WEB-008) | Optional |

A reader asks for these names and no others (REQ-CHN-002). Every name fits the 8.3 form a minimal FAT library reads, but `channel.json` and `contents.txt`'s place in it is `channel.json`, which needs long names: the owner kept the name (section 13 item 9).

The largest EP1 file is the 6-byte header, sixteen 40-byte enhancement packets, 25 rows of 40 bytes and the 2-byte terminator: 6 + 640 + 1,000 + 2 = 1,648 bytes (REQ-INP-015).

### 3.3 Finding a page

A reader looks for page `NNN` (REQ-CHN-004):
1. in its store, when the page is there and confirmed current (REQ-WEB-004);
2. otherwise in `NNN.tti`, then `NNN.t42`, then `NNN.ep1`, stopping at the first that answers 200 and passes its format's check (REQ-WEB-027). Within a channel, the extension that last answered 200 is tried first and the others after it in this order, which changes only how many requests are made, never which file is used;
3. otherwise the page is not found.

A page not found costs at most three requests. A file that answers 200 but fails its check is a failure of that page, and the other extensions are not tried.

**What each file may fill.** A page's file fills only the pages asked for in this channel, and enhancement pages, whose numbers are not decimal (REQ-WEB-019). `index.t42` fills every page it holds. A sub-page's file fills only that sub-page and enhancement pages. Lists fill no page.

## 4. Two tiers

**Hand-written.** A folder with page files, `NNN.tti`, `NNN.t42` or `NNN.ep1`, each holding the whole page, and optionally `channel.json` and `contents.txt`. Nothing else is needed, and a reader MUST open such a folder fully: it learns a page's sub-pages from the page's file as it decodes it. EP1 and edit.tf files carry no trusted page number; in a channel the file's name gives it.

**Built.** What a generator writes, from a hand-written folder or from a program's pages: every page as `NNN.t42`, and a page of more than one sub-page with its folder `NNN/` holding every sub-page's file and the parts of its list; the magazine lists `M.pag`; and `index.t42`. A built channel MAY also carry the hand-written files. Nobody writes a validator, a part or a magazine list by hand: they are derived from the page data (REQ-CHN-014), and a generator writes them again from the pages every time.

**The build tool.** `neottx` turns any folder into a built channel: a vbit2 service folder, captures, editor exports, files of any name with the page number read from each TTI's `PN` line or each EP1's name. It reads every format the engine reads; a reader of channels need not.

## 5. A page's sub-pages

### 5.1 Sub-page files

When page `NNN` has more than one sub-page, a built channel holds each of them, the first included, as `NNN/SSSS.t42`, one sub-page's packets and nothing else (REQ-CHN-005). `NNN.t42` then holds the first sub-page only, so a reader that knows only pages still shows the page.

A sub-page's file is at most 74 packets of 42 bytes, 3,108 bytes: the header and rows 1 to 25 (26 packets), and packets X/26, X/27 and X/28 with each of their 16 designation codes (48 packets; EN 300 706 clauses 9.4.2, 9.6 and 9.4.7). A Level 1 sub-page with links is 26 packets, 1,092 bytes.

### 5.2 The list of sub-pages, in parts

Page `NNN`'s list is in parts of `ROWS_PER_PART` = 64 rows. Part `P`, `NNN/P.sub`, holds the rows at places 64 × `P` to 64 × `P` + 63, counting from 0; a page of 8,190 sub-pages has parts 0 to 127 (⌈8,190 ÷ 64⌉ = 128). A reader finds the part of place `k` as ⌊`k` ÷ 64⌋, so it reaches any row with one request and never needs the whole list (REQ-CHN-006).

**Format.** Text: lines end with LF or CR LF; fields are separated by one horizontal tab; a byte outside printable ASCII other than the tab and the line ends makes its line invalid.

- **Line 1, the header:** `total`, the page's number of sub-pages in decimal, 1 to 8,190; then `version`, the page's version (section 5.3). Every part of one version of a page has the same header, so whichever part arrives first sizes the reader's scrollbar.
- **Every further line, one row:**

  | Field | Holds |
  |---|---|
  | sub-code | `SSSS`: four hexadecimal digits in capitals, any of `0000` to `3F7E` with no bit outside the thirteen a sub-code has (EN 300 706 clause 9.3.1.2; `3F7F` names no sub-page, clause 9.6.1) |
  | validator | The sub-page file's validator (section 5.3): 1 to 16 letters, digits, `-` and `_` |
  | title | Optional: 1 to 40 characters, the sub-page's title (section 5.5) |

- **Rows** are in ascending sub-code order (section 5.4). A part other than the last holds exactly 64 rows; the last holds the rest.

**Size.** The header is at most 4 + 1 + 16 + 2 = 23 bytes; a row is at most 4 + 1 + 16 + 1 + 40 + 2 = 64 bytes; a part is at most 23 + 64 × 64 = 4,119 bytes. A larger file is refused whole.

**Faults.** A header that is missing or invalid makes the part invalid. A row with fewer than two fields or more than three, an invalid sub-code or validator, an empty title field, a sub-code not above the row before it, or a 65th row is ignored and counted. A part whose `version` differs from the other parts the reader holds is fetched again; a reader holding parts of two versions shows neither as current.

**What a reader does with it.**
- **Stepping** to the next or previous sub-page takes the next or previous row of the part it holds, and the part beside it at a part's edge.
- **Keying a sub-code** asks for `NNN/SSSS.t42`. A 404 or 410 means that sub-page does not exist; the page's own file is not tried, since it holds the first sub-page only.
- **The list of sub-pages,** scrolled, asks for the parts its rows fall in, and the scrollbar is `total`.
- **No part:** when `NNN/0.sub` answers 404 or 410, the page has no folder, and its sub-pages are those its page file holds.

### 5.3 Validators and versions

- **A file's validator** is the first 16 lowercase hexadecimal digits of the SHA-256 of the file's bytes, as the engine's `Validator::of` writes it (REQ-CHN-007).
- **A page's version** is the validator of the page's sub-pages' packets end to end, in the page's order: what `NNN.t42` would hold if it held them all. It changes when any sub-page changes, is added or is removed.
- **A built file's `ETag`** MUST be its validator in double quotes, so that a sub-page's validator in its list and the `ETag` of its file are one value: a reader that holds a sub-page compares the list's validator with the `ETag` it holds and fetches only what differs, with no conditional request for the rest. A generator that cannot set headers (a static host) gives up only that saving, not correctness: the host's own `ETag` still serves conditional requests.

### 5.4 The page's order

A page's sub-pages are in ascending sub-code order, in the page's file, in its folder's lists, and as a reader steps through them (REQ-CHN-008). Order is then no separate fact, and a list cannot contradict its files about it. A generator given sub-pages in another order sorts them.

### 5.5 Titles

A sub-page's title is, in this order (REQ-CHN-009):
1. the title its publisher gave it (a program's sub-page title, a TTI page's `DE` line for its first sub-page);
2. otherwise the text of its row 1: each character shown in an alphanumeric mode (EN 300 706 clause 12.2) whose code is `0x20` to `0x7E` is kept as that ASCII character, and everything else, spacing attributes and mosaic characters included, becomes a space; runs of spaces become one, the ends are trimmed, and the result is cut to 40 characters;
3. otherwise, when that leaves nothing, it has none, and the list shows its sub-code and place alone.

Row 0 is never used: its text is the service's header, the same on every sub-page. A page's title, in `M.pag`, is its first sub-page's.

## 6. `channel.json`

The channel's settings, read by the engine's strict, bounded reader of at most 16,384 bytes (REQ-WEB-024). Every member is optional; an absent member takes its default; a duplicate member is refused; **an unknown member is refused**, and the channel does not open (REQ-CHN-012).

| Member | Holds | Default |
|---|---|---|
| `name` | The channel's own name for itself, at most 120 characters. A reader may show it outside the page, never in row 0. | The channel's address |
| `initial_page` | The page a channel opens at: three decimal digits, the magazine 1 to 8 first | `"100"` |
| `push` | An object, whose presence makes the channel live. Its one member is `input`, `true` when the channel takes the viewer's keys back. The connection is always a WebSocket at the channel's `push` (section 8). | No live connection |
| `region` | The default character set region (decision E.4) | The reader's configured region |
| `services` | Linked channels: each a `name` (short, for `name:mpp` links), a `display_name`, and `channel`, the linked channel's folder address in canonical form | None |
| `aliases` | At most 16 members, each mapping one page number to a target, `name:mpp` or a channel address (REQ-WEB-020) | None |
| `refresh` | Seconds, 5 to 86,400: how often the page on screen is asked for again when the channel has no live connection | Never |
| `presentation` | `"teletext"` or `"site"` (section 11) | `"teletext"` |

**Withdrawn on 30 October 2026:** `page_template`, and with it descriptor services, a descriptor at any other address with a template mapping page numbers to URLs (REQ-WEB-002), because a template maps a channel's files to names of its own and the structure is fixed; `push.address`, because the live connection's address is fixed (section 8); `services`' `descriptor`, for the same reason. Each is an unknown member, and refused.

**Withdrawn on 1 November 2026:** `push.method`, because a WebSocket is the only live connection (DEC-1738), so the member could say nothing. It is an unknown member, and refused, whatever its value.

## 7. Magazine lists

`M.pag` lists magazine `M`'s pages, so a reader knows which pages exist, how many sub-pages each has, whether it changed and what it is called, without asking for any page (REQ-CHN-010). It is what the standard's Magazine Inventory Page (page `MFD`, EN 300 706 clause 11.3) says, with the exact counts the inventory gives only as ranges above 79 (Table 24), and titles.

**Format.** Text, as section 5.2's. No header: the number of lines is the number of pages. Every line, one page, in ascending page number:

| Field | Holds |
|---|---|
| page | `NNN`, a page of magazine `M`: any page number but the reserved ones (`MFD`, `MFE`, `MFF` in every magazine, and `1BE` and `1F0`; the engine's `RESERVED_IN_EVERY_MAGAZINE` and `RESERVED_PAGES`) |
| sub-pages | Its number of sub-pages, decimal, 1 to 8,190 |
| version | The page's version (section 5.3) |
| title | Optional: 1 to 40 characters, its first sub-page's title (section 5.5) |

**Size.** A magazine has at most 253 pages; a line is at most 3 + 1 + 4 + 1 + 16 + 1 + 40 + 2 = 68 bytes; a magazine list is at most 253 × 68 = 17,204 bytes. All eight are at most 137,632 bytes, and a reader needs only the magazine being browsed.

**Faults.** A line of another magazine's page, a reserved page, a page not above the line before it, or an invalid field is ignored and counted. A magazine list that answers 404 or 410 means the channel does not list that magazine, not that it is empty: the reader then finds its pages by asking for them.

**With `contents.txt`.** `contents.txt` is the channel's own table of contents, in the order and sections it chooses, of at most 800 keyable pages (REQ-WEB-025); the magazine lists are the inventory of every page, hexadecimal ones included. A reader shows the first and navigates by the second.

## 8. The live connection

A channel's live connection is always at its folder's `push`: `wss://` for a channel at `https://`, `ws://` for one at `http://` (REQ-CHN-013). Server-sent events were withdrawn by DEC-1738. A reader opens it only when `channel.json` has `push`, and never asks for `push` otherwise. Its cookies are the channel's (REQ-WEB-026). What travels on it is `SERVER.md`'s and `INPUT.md`'s.

A static host serves the files and cannot serve `push`; a channel that takes the viewer's keys needs a server on the channel's own origin (`INPUT.md` section 4).

## 9. The URL map

**The written URL map is `SERVER.md` section 4** (REQ-1693, DEC-1694 version 3), which replaces what this section said of a viewer's addresses. The file names below that differ from section 4.2 there, `NNN/SSSS.t42` for `NNN-SSSS.t42`, `NNN/P.sub` for `NNN.sub`, and `M.pag`, are this document's own proposal, not built.

Every address of a channel, for a channel at `https://example.org/news/`:

| What | Address | Asked for by a reader |
|---|---|---|
| The channel | `https://example.org/news/` | Never itself |
| A page, as a viewer bookmarks or shares it | `https://example.org/news/602` | Never: a reader goes to the page's file, or selects it on a live channel |
| A sub-page, as a viewer bookmarks or shares it | `https://example.org/news/602/0101` | Never |
| Its settings | `…/news/channel.json` | When it opens |
| Its contents | `…/news/contents.txt` | When the contents are shown |
| Its bundle | `…/news/index.t42` | When it opens |
| Magazine 6's pages | `…/news/6.pag` | When the reader needs magazine 6's inventory |
| Page 602 | `…/news/602.tti`, `…/news/602.t42`, `…/news/602.ep1` | Section 3.3 |
| Sub-page 0101 of page 602 | `…/news/602/0101.t42` | When it is shown, or beside the one shown |
| Rows 64 to 127 of page 602's list | `…/news/602/1.sub` | When those rows are needed |
| The live connection | `wss://example.org/news/push` | When `channel.json` has `push` |

**Rules** (REQ-CHN-002, REQ-CHN-015):
1. **Each address is the folder followed by a fixed name,** worked out from the page number, sub-code or part number. There is no map file and no setting that changes the map.
2. **One spelling.** Hexadecimal digits are capitals; a page is three digits, a sub-code four, a part decimal without leading zeros. A reader writes only these forms, and an address in another form names no file of the channel.
3. **A viewer's address names a page, not a file.** `NNN` and `NNN/SSSS` after the channel's address, with the same digits as the file's path, so the two convert by rule: `602/0101` is the file `602/0101.t42`, and `602` is whichever of `602.tti`, `602.t42` or `602.ep1` holds the page. A reader never requests the viewer's address.
4. **Links resolve through the map,** never through anything a page says about files: a page link (X/27/0) is `NNN` in the same channel; `name:mpp` goes through `services`; an alias through `aliases`; a `contents.txt` `x` entry names a channel or a file of one, which opens as section 10 says.

## 10. Opening any address

A reader opens any address it is given (REQ-CHN-016). It decides what the address is in this order, and stops at the first that fits:

| # | The address | Opens as |
|---|---|---|
| 1 | Its fragment is a page in the edit.tf or zxnet editors' form, a hexadecimal digit, a colon and the base64url page (REQ-INP-016) | That page alone, decoded from the address, with nothing fetched |
| 2 | A folder: its path ends in `/` | A channel |
| 3 | A channel's folder followed by one of the fixed names of section 3.2 | That channel, at the page or sub-page the name gives, or at its initial page for any other name |
| 4 | Any other address that answers 200 with teletext | A single resource (section 10.1) |
| 5 | Any other address that answers 200 with a web page | Discovery: its `Link` headers and `<link>` elements lead to a channel (the browser's requirements 5.5 and 5.6) |
| 6 | A live feed in the zxnet viewer's WebSocket form (REQ-INP-022) | That live stream |
| 7 | Anything else | Refused, saying why |

The rules of the engine's area SEC apply to every case, whatever it opens as: the plain-HTTP marker (REQ-SEC-005), no downgrade (REQ-SEC-007), the local-network checks (REQ-SEC-006), strict HTTP (REQ-SEC-011), and redirects (REQ-WEB-021).

### 10.1 A single resource

A file that is not part of a channel, with any name, anywhere (REQ-CHN-017):
- **Its format is decided by its content,** by the engine's detection (REQ-INP-005), never by its name or extension: a T42 recording, a transport stream, sliced VBI data, a TTI file or an EP1 file. It holds whatever pages, sub-pages and enhancements it holds.
- **Its identity is its own address,** not a folder. It has no settings, no lists, no live connection and no cookies. Its links lead only to pages it holds; any other link is a navigation away from it, shown as one.
- **It is read whole,** at most `MAX_SINGLE_RESOURCE` = 64 MiB (the browser's `MAX_SOURCE_BYTES`: far above a day's recording of a service, which is a few megabytes), in the process that reads network data, and played to the decoder as a local file is.
- **It is never interactive.** Taking the viewer's keys needs a channel (section 12).

### 10.2 Folders and files on this computer

A folder on this computer is a channel by the same structure, with the same names and the same rules; a folder that holds no file of the structure opens as an empty channel at its initial page, which is not found. A file on this computer is a single resource, whatever its name (REQ-CHN-018).

## 11. Presentation

`channel.json`'s `presentation` says how a reader shows the channel; it changes nothing about the structure (REQ-CHN-019).

- **`"teletext"`, the default:** the reader's whole interface: the overview of the channel's pages, the contents, the list and count of a page's sub-pages, and keying page numbers.
- **`"site"`:** the channel is shown as a site of linked pages. By default the reader hides the overview, the contents, and the list and count of sub-pages, and keying digits does not select a page (they go to the channel when it takes keys, and do nothing otherwise). The viewer moves only by what the pages offer: their links, their Fastext keys, the prompts they make clickable, and back and forward through the pages they have seen. Every page keeps its address (`NNN`), and can be bookmarked and shared.

**One switch, not a member a panel,** so that no channel can make a half of one and half of the other.

**What presentation never changes** (REQ-CHN-020): the reader's trusted indicators and controls. These are the trusted strip and the address it shows (the browser's requirement 11.4), row 0 columns 0 to 7, which belong to the receiver alone (the engine's area SEC), the badge saying keys go to the channel (`INPUT.md` REQ-INT-131), and the keys the reader keeps for itself. And the viewer stays in charge: the reader's own menu still opens the overview and the sub-page list of a `"site"` channel.

**Presentation is not secrecy.** Every file is still at its fixed address, and `index.t42` and the lists name every page to anyone who asks. A page only some viewers may see is published by a program for those viewers, over the live connection (`SERVER.md` section 8).

## 12. The smallest channel

**A page a viewer can read:** a folder holding `100.tti`.

**A page a viewer can use:** a folder at your site's root, `https://example.org/`, holding

```json
{ "name": "Example", "push": { "input": true } }
```

as `channel.json`, and a server answering `wss://example.org/push` with a program that publishes page 100 and reads the viewer's keys: a game, a menu, a form, each viewer's page its own. `100.t42` beside it, MAY be given, so the page shows before the connection opens and while it is down. With `"presentation": "site"`, it shows as a site with no channel interface.

A file alone is never interactive (section 10.1): taking keys needs the live connection, and the live connection belongs to a channel.

## 13. Decisions

| # | Choice | Why |
|---|---|---|
| 1 | Fixed names, and the URL map the same as the files, always | One layout to learn, build and check; a descriptor is untrusted and cannot point a reader anywhere; a microcontroller needs no templates; a copied folder is a channel |
| 2 | A page's sub-pages in a folder named by the page | At most 8,190 + 128 files in a folder, within FAT32's 65,536 entries; the owner chose it on 30 October 2026 |
| 3 | The list in parts of 64 rows, the header in every part | A part is at most 4 KB, a screen of 23 rows spans at most two, and the total comes with any part, so no manifest is needed |
| 4 | Text lists, not JSON | One kind of strict, bounded reader for every list, as `contents.txt` has; no JSON parser to navigate |
| 5 | A validator is the file's `ETag` | One version everywhere: a list tells a reader which files it already holds |
| 6 | Ascending sub-code order | Order is derived, not a separate fact a list could get wrong |
| 7 | Titles given, else row 1 | Row 0 is the service's header; row 1 is commonly the page's heading |
| 8 | Magazine lists `M.pag` | Navigation by page number on a microcontroller, at most 17 KB a magazine |
| 9 | The new names in 8.3 form, and `channel.json` kept | A minimal FAT library reads every list and page; `channel.json` needs long names, and the owner kept it |
| 10 | Descriptor services, `page_template` and `push.address` withdrawn | They map a channel to names of its own; the map is fixed |
| 11 | EP1 among the page files | What the zxnet and edit.tf editors export, and a fixed name gives it the page number it lacks |
| 12 | Any address opens | A recording or a page anywhere on the web is teletext too; only a channel is navigated, kept current and interactive |
| 13 | Presentation as one switch, never touching what proves where the viewer is | A site can be shown as a site; the viewer's protection does not depend on the site |
| 14 | No version member in `channel.json` | In development: what is built changes to meet this document, with nothing kept for an earlier layout |

## 14. Requirements

**REQ-CHN-001 — A channel is a folder.** A channel shall be a folder, its address an `http` or `https` address whose path ends in `/` in the canonical form of the engine's REQ-WEB-023, identified by its origin and folder path, which shall be the boundary for cookies, redirects and links (REQ-WEB-018, REQ-WEB-026). *Reason:* section 3.1. *Verification:* the engine's tests of REQ-WEB-018, REQ-WEB-023 and REQ-WEB-026.

**REQ-CHN-002 — Fixed names, one map.** A channel's files shall have the names of section 3.2 and no others, in the one spelling of section 9 rule 2, and a reader shall ask a channel for those names alone. No setting, file or page shall change the name of a channel's file. *Reason:* section 13 item 1. *Verification:* a reader's tests that opening, browsing and stepping through a channel of every file kind asks for nothing else, and that a `channel.json` with `page_template` is refused.

**REQ-CHN-003 — Page folders.** Inside a channel's folder, a folder named by a page number in the form of section 3.2 shall belong to the channel as that page's folder, and any other folder shall be a channel of its own. *Reason:* section 13 item 2. *Verification:* tests that `602/0101.t42` is a file of the channel at `…/` and `other/100.tti` a file of the channel at `…/other/`, with cookies kept apart.

**REQ-CHN-004 — Finding a page.** A reader shall look for a page as section 3.3 says: the store, then `NNN.tti`, `NNN.t42` and `NNN.ep1`, the extension that last answered first; a file that fails its format's check shall be a failure of the page, and the others not tried. *Reason:* section 13 item 11. *Verification:* tests that a page is found in each of the three, not at all in three requests, and that the order changes after a success but the result does not.

**REQ-CHN-005 — Sub-page files.** A built page of more than one sub-page shall hold each sub-page as `NNN/SSSS.t42`, and `NNN.t42` its first sub-page alone; a reader asking for a sub-page shall ask for its file alone, and a 404 or 410 shall mean it does not exist. *Reason:* section 5.1. *Verification:* a generator's test that a page of 8,190 sub-pages is written as 8,190 files and 128 parts and read back; a reader's test that keying a sub-code asks for one file.

**REQ-CHN-006 — The list in parts.** A page's list of sub-pages shall be `NNN/P.sub`, in the format, order, size and faults of section 5.2, and a reader shall ask only for the parts holding the rows it needs. *Reason:* section 13 item 3. *Verification:* a reader's test with the 128 parts of 8,190 sub-pages that showing rows 4,000 to 4,022 asks for parts 62 and 63 alone; tests of every bound and fault, and fuzzing of the reader.

**REQ-CHN-007 — Validators and versions.** A validator and a page's version shall be as section 5.3 defines them, and a generator that sets headers shall send a built file's validator as its `ETag`. *Reason:* section 13 item 5. *Verification:* a generator's test that every row's validator equals its sub-page file's `ETag`, and that a page's version changes when one sub-page changes and when one is added or removed.

**REQ-CHN-008 — Ascending order.** A page's sub-pages shall be in ascending sub-code order in its file, its lists and its stepping. *Reason:* section 13 item 6. *Verification:* a generator's test given sub-pages out of order.

**REQ-CHN-009 — Titles.** A sub-page's title shall be as section 5.5 says. *Reason:* section 13 item 7. *Verification:* tests of a given title, row 1 with attributes, mosaics and runs of spaces, an empty row 1, and a row 1 longer than 40 characters.

**REQ-CHN-010 — Magazine lists.** A built channel shall hold `M.pag` for each magazine it has pages in, in the format, size and faults of section 7. *Reason:* section 13 item 8. *Verification:* a generator's test that every page and only the pages it holds are listed with their counts, versions and titles; a reader's tests of every bound and fault, and fuzzing.

**REQ-CHN-011 — The bundle's bound.** `index.t42` shall be at most 262,144 bytes. A generator shall put first sub-pages in it in ascending page order and stop before the page that would pass the bound. *Reason:* a channel larger than the bundle still opens with one request for its first pages; Hackaday's bundle was measured at 261,954 bytes on 30 October 2026. *Verification:* a generator's test with more first sub-pages than fit.

**REQ-CHN-012 — `channel.json`.** `channel.json` shall have the members of section 6 and no others, read strictly at most 16,384 bytes, with an unknown, duplicate or invalid member refusing the file. *Reason:* section 6. *Verification:* tests of each member, each withdrawn member, an unknown member and a duplicate.

**REQ-CHN-013 — The live connection's address.** A channel's live connection shall be at its folder's `push`, with the scheme section 8 says, and a reader shall open it only when `channel.json` has `push`. *Reason:* section 13 item 10. *Verification:* tests that the address is derived for `http` and `https`, and that no `push` member means no request to `push`.

**REQ-CHN-014 — Derived files.** A generator shall derive every part, magazine list, validator, version and title from the page data each time it writes them; a reader shall treat a sub-page's file as the truth when it disagrees with a list. *Reason:* section 2 principle 4. *Verification:* a reader's test that a listed sub-page whose file answers 404 is not found, and that a sub-page's file whose `ETag` differs from its list's validator is used.

**REQ-CHN-015 — Viewer addresses.** A page's address for a viewer shall be the channel's address followed by `NNN`, and a sub-page's by `NNN/SSSS`, in the spelling of `SERVER.md` section 4. *Reason:* section 9 rule 3. *Verification:* tests that opening `…/602/0101` asks for `602/0101.t42` and never for `…/602/0101` itself.

**REQ-CHN-016 — Opening any address.** A reader shall open any address in the order of section 10, and refuse what fits none, saying why. *Reason:* section 13 item 12. *Verification:* a test of each of the seven cases, and of an address that could be two of them, which opens as the earlier.

**REQ-CHN-017 — A single resource.** A file opened as section 10 case 4 shall be read as section 10.1 says: format by content, identity its own address, no settings, lists, live connection or cookies, at most `MAX_SINGLE_RESOURCE`, never interactive. *Reason:* section 10.1. *Verification:* tests with a T42 recording, a transport stream, a TTI file and an EP1 file under unrelated names, one of 64 MiB and one byte more, and one serving a cookie.

**REQ-CHN-018 — This computer.** A folder on this computer shall open as a channel by this structure, and a file as a single resource. *Reason:* section 10.2. *Verification:* the same tests as REQ-CHN-002 to REQ-CHN-006 on a folder, and a test that a folder of files with other names opens no page.

**REQ-CHN-019 — Presentation.** A reader shall show a channel as section 11 says for its `presentation`. *Reason:* section 13 item 13. *Verification:* tests that a `"site"` channel opens with the overview, contents and sub-page list hidden and digits not selecting a page, that its links, Fastext keys, back and forward work, and that the menu still opens the overview.

**REQ-CHN-020 — What presentation never changes.** No member, file or page of a channel shall hide, move or change the reader's trusted indicators and controls listed in section 11. *Reason:* the viewer's protection does not depend on the channel. *Verification:* tests of a `"site"` channel that the strip, the address, row 0 columns 0 to 7, the keys badge and the reader's own keys are as for a `"teletext"` channel.

**REQ-CHN-021 — Media types.** A channel's files shall be accepted with the media types of the engine's REQ-WEB-027, and its new files with these: `M.pag` and `NNN/P.sub`, `text/plain` or `application/octet-stream`; `NNN.ep1`, `application/octet-stream`; `NNN/SSSS.t42` as `NNN.t42`. *Reason:* no teletext media type is registered, and hosts send generic ones. *Verification:* the tests of REQ-WEB-027 for each new file.

**REQ-CHN-022 — Bounded readers.** Every reader of a file of section 3.2 shall refuse whole a file larger than its largest there, allocate no more than that bound, and be fuzzed (REQ-GEN-008, REQ-TST-040). *Reason:* every file is untrusted input, and a microcontroller must be able to hold any one of them. *Verification:* a test at each bound and one byte past it, and a fuzz target for each reader.

## 15. What changes, and where

| Repository | Work |
|---|---|
| Engine `neoteletext-web` | The names: `NNN/SSSS.t42`, `NNN/P.sub`, `M.pag`, `NNN.ep1`, `push`; the parted list's reader and writer, replacing `NNN.sub`'s; the magazine list's reader and writer; finding a page in three files; finding sub-pages by part; `channel.json`'s `presentation`, `push` without `address`, `services` without `descriptor`; descriptor services and `page_template` withdrawn; the bundle's bound in the writer; page folders in the address rules; requirements REQ-WEB-002, 008, 018, 019, 023, 024, 026, 027 and 034 amended to point here |
| Engine `neoteletext-formats` | The title of a sub-page (section 5.5) |
| Engine `neottx` | The build tool (section 4) |
| Server | Serve the structure from the engine's names; `channel.json` with `push` alone and `presentation`; `M.pag`; titles; the validator as every built file's `ETag`; the bundle's bound; ascending order |
| Browser | The engine's new pin; sub-page lists by part; `presentation`; opening any address (section 10); this computer's folders by the structure; the live connection's derived address; EP1 among page files |
| TypeScript kit and UI library | A channel's `presentation` and a sub-page's title declared to the server |
| Channels | demosite, uicomponentsdemo and Hackaday published again by the server in the structure; `presentation` declared where wanted |
