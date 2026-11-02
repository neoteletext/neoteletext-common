# NeoTeletext teletext reference

This is a programmer's reference for writing pages. Part 1 lists the teletext features of EN 300 706 that NeoTeletext supports, level by level, with the bytes that switch each one on. Part 2 lists everything NeoTeletext adds beyond the standard, and how to program it.

To build a channel step by step, read [`creating-a-channel.md`](creating-a-channel.md). To run a server and program it, read [`servers.md`](servers.md). To implement a receiver or a server, read [the protocol document](../PROTOCOL.html), the one definition of the protocol. This guide says what a page author can do, and points at those documents for the wire.

The guide was checked against engine commit `3de0047`, browser commit `e87a652` (which pins engine `97f8fd2`), program protocol 6 and input protocol 7, on 1 November 2026. Every TTI block below was rendered with `neottx`. The **Browser** columns come from the browser's build and its code, not from running it.

## Contents

- [How to read this guide](#how-to-read-this-guide)
- [Part 1: the teletext of EN 300 706](#part-1-the-teletext-of-en-300-706)
  - [1. The levels](#1-the-levels)
  - [2. What each build shows](#2-what-each-build-shows)
  - [3. Level 1.0](#3-level-10)
  - [4. Level 1.5](#4-level-15)
  - [5. Level 2.5](#5-level-25)
  - [6. Level 3.5](#6-level-35)
  - [7. The character sets of the standard](#7-the-character-sets-of-the-standard)
  - [8. What is not supported](#8-what-is-not-supported)
- [Part 2: what NeoTeletext adds](#part-2-what-neoteletext-adds)
  - [9. Character sets beyond the standard](#9-character-sets-beyond-the-standard)
  - [10. Noto Teletext](#10-noto-teletext)
  - [11. Channels and channel.ttx](#11-channels-and-channelttx)
  - [12. Web addresses and the URL map](#12-web-addresses-and-the-url-map)
  - [13. neottx:// links](#13-neottx-links)
  - [14. Links beyond Fastext](#14-links-beyond-fastext)
  - [15. Live channels](#15-live-channels)
  - [16. The push WebSocket and the input protocol](#16-the-push-websocket-and-the-input-protocol)
  - [17. Typing and forms](#17-typing-and-forms)
  - [18. Controls: cells a page answers itself](#18-controls-cells-a-page-answers-itself)
  - [19. Audio](#19-audio)
  - [20. Pictures](#20-pictures)
  - [21. The phone keyboard and QR codes](#21-the-phone-keyboard-and-qr-codes)
  - [22. Other additions](#22-other-additions)
- [Appendix: where the documents and the code differ](#appendix-where-the-documents-and-the-code-differ)

---

## How to read this guide

### Notation

- A code is written in hexadecimal, `0x1D`, or as column and row of the standard's code tables, 1/D. They mean the same thing.
- A page number is `mpp`: three hexadecimal digits, magazine first. `100`, `2FA`.
- A sub-code is `ssss`: four hexadecimal digits, `0000` to `3F7E`. `3F7F` means no particular sub-page.
- A row is 0 to 24, and a column 0 to 39. A page is always 40 columns by 25 rows.
- X/26 means packet 26 of any magazine. X/26/3 means packet 26 with designation code 3. M/29 is a packet that belongs to a magazine rather than a page.
- Clause and table numbers are EN 300 706's, unless another document is named.

In TTI blocks, `␛` stands for the byte `0x1B` and `␡` for the byte `0x7F`. A real file holds those bytes.

### Four ways to write a page

| Way | Use it for | Reaches |
|---|---|---|
| TTI text | Hand-written and generated page files, and anything the kits have no call for | Everything in Part 1 |
| TypeScript kit, `neoteletext-server-ts-protocol` | Live channels | `Screen` reaches rows, links and the cursor. Everything else goes through TTI with `context.publishTti` |
| Python kit, `neoteletext_app` | Live channels | `Screen` reaches rows, links and the cursor. `Screen.load_tti` and the `enhancements` and `packets` lists reach the packets |
| Rust authoring builder, `neoteletext_formats::author` | Generated pages with enhancement data and object pages | Every function of Tables 28 and 29 by name |

The TypeScript UI library, `neoteletext-server-ts-ui-components`, sits on the TypeScript kit and draws pages from components. Its documents are in that repository's `docs/`.

### TTI in one screen

A TTI file is lines of text. Each line is a two-letter command, a comma, and its arguments. A page starts at `PN` and runs to the next `PN`. These lines are read:

| Line | Meaning |
|---|---|
| `PN,mppss` | Starts a page. `ss` is decimal, and only numbers the sub-pages in the file. The sub-code comes from `SC`, not from `ss` |
| `SC,ssss` | The sub-code, hexadecimal. Without it the sub-code is 0000 |
| `PS,xxxx` | Page status: the control bits and the national option ([section 3.2](#32-the-header-and-row-0)) |
| `RE,x` | The group of the character set designation, 0 to F ([section 3.11](#311-national-options)) |
| `PF,f,c` | Page function and page coding, hexadecimal |
| `OL,n,text` | Row `n`, 0 to 24, in the escape form below. `OL,26` to `OL,29` are packed lines ([section 4.1](#41-how-enhancement-data-is-written)) |
| `FL,r,g,y,c,5,i` | The six links of X/27/0, in hexadecimal ([section 3.10](#310-fastext-and-row-24)) |
| `LN`, `LK`, `LT` | The TTI Link Extension ([section 14](#14-links-beyond-fastext)) |
| `CU,row,col,0,flags` | The input cursor ([section 17](#17-typing-and-forms)) |
| `DE,text`, `DS,text` | Description and source. `DE` gives the first sub-page its title |
| `LG,level,text` | A log line for the channel's author ([section 22](#22-other-additions)) |
| `CK,considered,name` | Marks a `neottx check` warning as considered |
| `CT,...` | Read and ignored |

`TF` and `IM` are withdrawn and `neottx check` reports each as an error. The lines of the withdrawn Form Extension (`FD`, `OPTION`, `FS`, `FP`, `FT`, `FH`) are unknown commands, reported as diagnostics and ignored, as every unknown command is.

**Row text.** An `OL` line holds up to 40 codes. A control code `0x00` to `0x1F` is written as `␛` and the code plus `0x40`: alpha red, `0x01`, is `␛A`. The byte plus `0x80` also works, because each byte is masked to seven bits. Trailing spaces may be left out. A raw `0x10` in a row means Double Height, because MRG's format says so; write Mosaic Black as `␛P` to get `0x10` itself.

**The first eight columns of `OL,0` are never shown.** Row 0's columns 0 to 7 belong to the receiver, so `OL,0,HEADER` loses its first eight characters. Start header text at column 8.

```tti
PN,10000
SC,0000
PS,8000
OL,0,        HELLO
OL,1,␛CYellow text, then ␛Ared
```

### Checking a page

```sh
neottx text page.tti 100              # the page as UTF-8
neottx render page.tti 100 -o p.png   # the page as an image, 480 by 500
neottx check page.tti                 # authoring problems; exit status 4 on an error
neottx render page.tti 100 --level 1.5 -o p.png    # as a Level 1.5 set shows it
```

`-v` on any command prints a page's diagnostics. `neottx text` and `neottx render` take `100/0002` for one sub-page. To draw objects or Additional Flash Functions in `neottx`, build it with `--features objects,additional-flash-functions` ([section 2](#2-what-each-build-shows)).

---

# Part 1: the teletext of EN 300 706

## 1. The levels

A level is a setting of the receiver, and changing it re-acquires nothing. Each level holds everything below it (clause 12).

| Level | What runs | What it adds for an author |
|---|---|---|
| 1.0 | The page's Level 1 bytes. X/26 is stored and not applied | Spacing attributes, eight colours, mosaics, double height, flash, conceal, boxes, sub-pages, Fastext, national options |
| 1.5 | The Level 1 page, then a pass over X/26 | Characters placed by triplets: the G2 and G3 sets and diacritical marks |
| 2.5 | The Level 1 page, then the enhancement processor in place of the 1.5 pass | Non-spacing attributes, the Colour Map, screen and row colours, double width and size, Modified designation, objects |
| 3.5 | As 2.5, and X/27/5, X/28/4 and M/29/4 | CLUTs 0 and 1 redefined, and no limit on Modified designations |

`Config::default()` is the `en300706` profile, which presents at Level 3.5. Both `neottx` and the browser use it. `neottx --level 1|1.5|2.5|3.5` overrides it, and `neottx --profile saa5050` and `--profile saa5246a` present at Level 1 and 1.5 with those chips' behaviour. The browser has no setting for the level.

A page written for a higher level still shows on a lower one. The lower receiver ignores what it does not understand.

### Every feature at a glance

"Objects build" means a `neottx` built with `--features objects`. Everything else shows in the default `neottx`.

| Feature | Level | Browser | `neottx` | Section |
|---|---|---|---|---|
| Header and row 0 | 1.0 | Yes | Yes | [3.2](#32-the-header-and-row-0) |
| Spacing attributes | 1.0 | Yes | Yes | [3.3](#33-spacing-attributes) |
| Eight colours, backgrounds | 1.0 | Yes | Yes | [3.4](#34-colours-and-backgrounds) |
| Mosaics, contiguous and separated | 1.0 | Yes | Yes | [3.5](#35-mosaics-contiguous-and-separated) |
| Hold Mosaics | 1.0 | Yes | Yes | [3.6](#36-hold-mosaics) |
| Double height | 1.0 | Yes | Yes | [3.7](#37-double-height) |
| Flash, conceal | 1.0 | Yes | Yes | [3.8](#38-flash-and-conceal) |
| Boxes, newsflash and subtitle pages | 1.0 | Yes | Yes | [3.9](#39-boxes) |
| Sub-pages | 1.0 | Yes | Yes | [3.1](#31-pages-rows-and-sub-pages) |
| Fastext and row 24 | 1.0 | Yes | Yes | [3.10](#310-fastext-and-row-24) |
| National options | 1.0 | Yes | Yes | [3.11](#311-national-options) |
| Second G0 set, ESC | 1.0 | Yes | Yes | [3.12](#312-esc-and-the-second-g0-set) |
| Diacritical marks by triplet | 1.5 | Yes | Yes | [4.3](#43-g0-characters-and-diacritical-marks) |
| G2 and G3 by triplet | 1.5 | Yes | Yes | [4.4](#44-g2-and-g3-characters) |
| Non-spacing colours | 2.5 | Yes | Yes | [5.3](#53-non-spacing-attributes-and-size) |
| Double width and double size | 2.5 | Yes | Yes | [5.3](#53-non-spacing-attributes-and-size) |
| Underline, separated by attribute | 2.5 | Separated yes, underline no | Yes | [5.3](#53-non-spacing-attributes-and-size) |
| Invert, window | 2.5 | Yes | Yes | [5.3](#53-non-spacing-attributes-and-size) |
| Additional Flash Functions | 2.5 | **No** | Named feature | [5.4](#54-additional-flash-functions) |
| Colour Map, CLUTs 2 and 3 | 2.5 | Yes | Yes | [5.5](#55-the-colour-map-and-page-level-data) |
| Screen and row colours | 2.5 | Yes, with a border | Yes, no border | [5.5](#55-the-colour-map-and-page-level-data) |
| Substitution, Re-mapping | 2.5 | Yes | Yes | [5.5](#55-the-colour-map-and-page-level-data) |
| M/29 magazine data | 2.5 | Yes | Yes | [5.5](#55-the-colour-map-and-page-level-data) |
| Modified designation | 2.5 | Yes | Yes | [5.6](#56-modified-designation) |
| G1 mosaics by triplet | 2.5 | Yes | Yes | [5.2](#52-the-column-triplets) |
| Objects, default objects, MOT | 2.5 | Yes | Objects build | [5.7](#57-objects) |
| CLUTs 0 and 1 | 3.5 | Yes | Yes | [6](#6-level-35) |
| X/27/5 and the Level 3.5 MOT links | 3.5 | Yes | Objects build | [6](#6-level-35) |
| Side panels, DRCS, font styles | | No | No | [8](#8-what-is-not-supported) |

## 2. What each build shows

The capabilities of Levels 2.5 and 3.5 are Cargo features of `neoteletext-core`. A build without one shows a page as a receiver without it would, and this is never an error.

| Capability | Feature | Engine default | `modern-classic` | Browser | `neottx` default | `neottx` with the two features |
|---|---|---|---|---|---|---|
| Levels 1.0 and 1.5 | `level15` | Yes | Yes | Yes | Yes | Yes |
| The enhancement processor | `level25` | Yes | Yes | Yes | Yes | Yes |
| Non-spacing attributes | `nonspacing-attributes` | Yes | Yes | Yes | Yes | Yes |
| Objects | `objects` | No | Yes | Yes | **No** | Yes |
| Colour Map of Level 2.5 | `level25-32colors` | Yes | No | Yes | Yes | Yes |
| Colour Map of Level 3.5 | `level35-32colors` | Yes | No | Yes | Yes | Yes |
| NeoTeletext's own sets | `extended-sets` | Yes | No | Yes | Yes | Yes |
| Additional Flash Functions | `additional-flash-functions` | No | No | **No** | **No** | Yes |

The browser's decoder builds `modern-classic`, `level35-32colors` and `extended-sets`. `cargo tree` resolves that to `extended-sets`, `level15`, `level25`, `level25-32colors`, `level35-32colors`, `modern-classic`, `nonspacing-attributes`, `objects`, `render` and `viewer`. **Additional Flash Functions are not in the browser**: a page that uses them shows steady text there, except Level 1 flash, which still flashes.

`neottx` takes the engine's default features, so it draws no objects unless built with them. This is the commonest surprise when checking a page:

```sh
cargo build --profile iterate -p neoteletext-cli --features objects,additional-flash-functions
```

Two things draw differently in the browser whatever the features:

- **Underline.** The browser never draws the page's own underline (Display Attributes D5). In NeoTeletext an underline means a link, and the browser draws links itself. `neottx` draws it.
- **Screen colour.** The browser paints the screen colour around the page. `neottx render` writes the 480 by 500 page with no border.

The browser opens T42 and TTI files only, and its live and static channels use those two formats (DEC-1762). `neottx` also reads EP1, edit.tf addresses, transport streams, sliced VBI and screen dumps.

## 3. Level 1.0

### 3.1 Pages, rows and sub-pages

A page has a three-digit number and up to 8,190 sub-pages. Rows 1 to 23 are the page's text, row 0 is the header, and row 24 is the Fastext row.

| Page numbers | Rule |
|---|---|
| `100` to `899` | What a viewer can key |
| Any with a hexadecimal digit, such as `2FA` | Reached by links and addresses, not by keying. The code of practice puts enhancement data on such pages (TR 100 287 clause 10.1) |
| `mFD`, `mFE`, `mFF` in every magazine, `1BE`, `1F0` | Reserved: the Magazine Inventory Page, the Magazine Organization Table, time filling, Automatic Channel Installation and the Basic TOP Table |

A sub-page has its own `PN` and `SC` lines:

```tti
PN,20000
SC,0001
PS,8000
OL,1,First sub-page
PN,20001
SC,0002
PS,8000
OL,1,Second sub-page
```

`neottx list` shows `200 sub-pages 2 [0001 0002]`, and `neottx text page.tti 200/0002` shows the second. `neottx text page.tti 200` shows the last one stored.

Sub-code 0000 means a page with no sub-pages. A set of up to 79 uses 0001 to 0079. A larger set uses only sub-codes above 0079, at most 8,069 of them (TR 100 287 clause 10.1). The kits number sub-pages this way when given a whole page: `publishSubpages` in TypeScript, `publish` with a list in Python. To name sub-codes yourself, use `put` in TypeScript or `subcodes=` in Python.

| | Call |
|---|---|
| TTI | `PN` and `SC` lines |
| TypeScript | `context.publishSubpages("channel", 0x200, [{ screen: a }, { screen: b, title: "Two" }])` |
| Python | `app.publish(0x200, [a, b])` |

How a viewer sees sub-pages on a live channel is in [section 15](#15-live-channels). Nothing rotates there.

### 3.2 The header and row 0

Row 0 is built by the receiver, not the page (clause 9.3.1.3):

| Columns | Shown |
|---|---|
| 0 to 6 | The status area: `P100`, or the sub-page place such as `P100/12`. No page can write here |
| 7 | A colour attribute the receiver generates: white when the page is found, green while searching |
| 8 to 39 | Header bytes 14 to 45: the page's `OL,0` columns 8 to 39 |

Columns 32 to 39 are the clock: a receiver shows those of the latest header it has received. Nothing a page transmits reaches columns 0 to 7: a triplet, an object, a row colour or a screen colour aimed there is discarded and the rest of the data still runs.

The control bits are set by `PS`. The value is hexadecimal:

| `PS` bit | Value | Bit | Meaning |
|---|---|---|---|
| 15 | `8000` | | "Transmit page", kept for vbit2. No meaning to a decoder |
| 14 | `4000` | C4 | Erase page |
| 0 | `0001` | C5 | Newsflash: a boxed page |
| 1 | `0002` | C6 | Subtitle: a boxed page |
| 2 | `0004` | C7 | Suppress header: row 0 is not shown, apart from the status area when configured and any security indicator |
| 3 | `0008` | C8 | Update indicator |
| 4 | `0010` | C9 | Interrupted sequence |
| 5 | `0020` | C10 | Inhibit display: rows 1 to 24 are not shown. Row 0 is |
| 6 | `0040` | C11 | Magazine serial |
| 7, 8, 9 | `0080`, `0100`, `0200` | C12, C13, C14 | The national option, 4 × C12 + 2 × C13 + C14 |

Add the values. A subtitle page in German is `8000 + 0002 + 0200 = 8202`.

| | Call |
|---|---|
| TTI | `OL,0,` and eight spaces, then the text. `PS,...` for the bits |
| TypeScript | `screen.header("HELLO")`. The control bits are the typed page's `control` field. `Screen` sets none of them, so use TTI through `publishTti` |
| Python | `screen.header("HELLO")`. `Screen.content()` writes every control bit false |

On a live channel the server sets C4 and C11 itself.

### 3.3 Spacing attributes

A spacing attribute takes one cell, shown as a space in the state in force. A row starts as alphanumeric white on black, steady, normal size, unboxed, not concealed, contiguous, hold off, default G0 set. Nothing carries from one row to the next.

Set-at attributes act in their own cell, and set-after attributes from the next cell (Table 26).

| Code | TTI | Name | Timing | Effect |
|---|---|---|---|---|
| `0x00` | `␛@` | Alpha Black | After | Black text. Default profile only (below) |
| `0x01` | `␛A` | Alpha Red | After | Red text, alphanumeric mode, ends conceal |
| `0x02` | `␛B` | Alpha Green | After | |
| `0x03` | `␛C` | Alpha Yellow | After | |
| `0x04` | `␛D` | Alpha Blue | After | |
| `0x05` | `␛E` | Alpha Magenta | After | |
| `0x06` | `␛F` | Alpha Cyan | After | |
| `0x07` | `␛G` | Alpha White | After | |
| `0x08` | `␛H` | Flash | After | Flash until Steady or the row's end |
| `0x09` | `␛I` | Steady | At | Ends flash |
| `0x0A` | `␛J` | End Box | After | |
| `0x0B` | `␛K` | Start Box | After | Needs two in a row |
| `0x0C` | `␛L` | Normal Size | At | |
| `0x0D` | `␛M` | Double Height | After | |
| `0x0E` | `␛N` | Double Width | After | Level 2.5 and above; a space below that |
| `0x0F` | `␛O` | Double Size | After | Level 2.5 and above; a space below that |
| `0x10` | `␛P` | Mosaic Black | After | Default profile only |
| `0x11` | `␛Q` | Mosaic Red | After | Red mosaics, mosaic mode, ends conceal |
| `0x12` | `␛R` | Mosaic Green | After | |
| `0x13` | `␛S` | Mosaic Yellow | After | |
| `0x14` | `␛T` | Mosaic Blue | After | |
| `0x15` | `␛U` | Mosaic Magenta | After | |
| `0x16` | `␛V` | Mosaic Cyan | After | |
| `0x17` | `␛W` | Mosaic White | After | |
| `0x18` | `␛X` | Conceal | At | Hidden until a colour attribute or the row's end |
| `0x19` | `␛Y` | Contiguous Mosaics | At | |
| `0x1A` | `␛Z` | Separated Mosaics | At | |
| `0x1B` | `␛[` | ESC | After | Toggles the second G0 set |
| `0x1C` | `␛\` | Black Background | At | |
| `0x1D` | `␛]` | New Background | At | The foreground colour becomes the background |
| `0x1E` | `␛^` | Hold Mosaics | At | |
| `0x1F` | `␛_` | Release Mosaics | After | |

The standard gives 0/0 and 1/0 no Level 1 function. The default profile treats them as black, because services send them. The `saa5050` profile shows them as spaces. Both browser and `neottx` use the default.

The kits have the common codes by name, and any code goes through `code`:

| | Colour | Other attributes |
|---|---|---|
| TypeScript | `Colour.Red`, `textColour(colour)`, `mosaicColour(colour)`, `screen.coloured(row, column, colour, text)` | `Attribute.Flash`, `Steady`, `NormalHeight`, `DoubleHeight`, `Conceal`, `Contiguous`, `Separated`, `BlackBackground`, `NewBackground`, `HoldMosaics`, `ReleaseMosaics`. Others by value: `screen.code(row, column, 0x0B)` |
| Python | `Colour.RED.text`, `Colour.RED.mosaic`, `screen.coloured(row, column, colour, text)` | `Attribute.FLASH`, `STEADY`, `END_BOX`, `START_BOX`, `NORMAL_HEIGHT`, `DOUBLE_HEIGHT`, `DOUBLE_WIDTH`, `CONCEAL`, `CONTIGUOUS`, `SEPARATED`, `BLACK_BACKGROUND`, `NEW_BACKGROUND`, `HOLD_MOSAICS`, `RELEASE_MOSAICS` |

### 3.4 Colours and backgrounds

The eight colours are colour numbers 0 to 7. Bit 0 is red, bit 1 green and bit 2 blue.

| Number | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Colour | Black | Red | Green | Yellow | Blue | Magenta | Cyan | White |

A background takes two cells: a colour, then New Background. Black Background ends it.

```tti
PN,10100
PS,8000
OL,1,␛D␛]␛CYellow on blue␛\Black again
```

Browser: yes. `neottx`: yes.

| | Call |
|---|---|
| TypeScript | `screen.background(row, column, Colour.Blue)`, then `screen.coloured(...)` |
| Python | `screen.background(row, column, Colour.BLUE)` |

### 3.5 Mosaics, contiguous and separated

After a mosaic colour code, codes with bit 5 set are block mosaics, and codes 4/0 to 5/F show as ordinary characters ("blast-through"). A cell holds six sixels, two across and three down:

| | Left | Right |
|---|---|---|
| Top | `0x01` | `0x02` |
| Middle | `0x04` | `0x08` |
| Bottom | `0x10` | `0x40` |

The code is `0x20` plus the bits of the sixels that are set. All six is `0x7F`, the left column is `0x35`, and the right column is `0x6A`. Bit 5 is always set. The pattern number, used when converting to Unicode, is `n = (code & 0x1F) | ((code & 0x40) >> 1)`.

Separated Mosaics draws each sixel with a gap: the leftmost dot column and bottom line of each block become background. The form in force is kept with each cell.

```tti
PN,10200
PS,8000
OL,1,␛W␡5j␛Z␡5j␛Y␡ABC
```

That row is white mosaics: a full block, the left column and the right column; then the same three separated; then a contiguous block and the letters ABC blasting through.

Browser: yes. `neottx`: yes.

| | Call |
|---|---|
| TypeScript | `const canvas = new Sixels(width, height); canvas.set(x, y, true); canvas.draw(screen, row, column, Colour.White);` |
| Python | `canvas = Sixels(width, height); canvas.set(x, y); canvas.draw(screen, row, column, Colour.WHITE)` |

`draw` puts the mosaic colour in the cell before `column`. `Sixels` draws contiguous mosaics. For separated, write `0x1A` with `screen.code` first.

### 3.6 Hold Mosaics

Normally a spacing attribute inside a mosaic run leaves a blank cell. Under Hold Mosaics, each attribute cell shows the last mosaic instead, so a colour can change with no gap.

The held mosaic is the latest mosaic of the row with bit 5 set, in the form it had. It resets at the start of a row, on a change between alphanumeric and mosaic mode, and on a change of size. Blast-through characters are never held. When a set-after attribute changes the mode or size, its own cell can still show the held mosaic and the reset follows it. A set-at Normal Size resets before its own cell.

```tti
PN,10300
PS,8000
OL,1,␛W␡␛^␛R␡␛S␡␛_␛T␡
```

A white block, then under hold a green and a yellow block with no gap, then Release Mosaics and a blue block after a gap.

Browser: yes. `neottx`: yes. Kits: `Attribute.HoldMosaics`, `Attribute.HOLD_MOSAICS`.

### 3.7 Double height

Characters after Double Height have their top half in the row and their bottom half in the row below, with the attributes of the top half. When any cell of a row is double height, the transmitted content of the next row is ignored: it shows bottom halves below double-height cells and background below the others.

Double height in rows 0, 23 and 24 is treated as normal height. Annex C.3 leaves that to the decoder, and this is NeoTeletext's choice.

```tti
PN,10400
PS,8000
OL,1,␛MDouble height␛Lnormal
OL,2,This row is not shown
```

Browser: yes. `neottx`: yes.

| | Call |
|---|---|
| TypeScript | `screen.doubleHeight(row, column, Colour.Yellow, "Text")` |
| Python | `screen.double_height(row, column, Colour.YELLOW, "Text")` |

### 3.8 Flash and conceal

**Flash.** Cells after Flash flash until Steady or the row's end. The standard gives the code no rate, so NeoTeletext takes the SAA5050's at every level: shown for 960 ms and hidden for 320 ms. In the hidden phase the foreground is drawn in the background colour.

```tti
PN,10500
PS,8000
OL,1,␛HFlashing␛I steady
```

**Conceal.** Cells after Conceal show as spaces in their background colour until the next colour attribute or the row's end, unless the viewer reveals them. Reveal lasts until another page is selected.

```tti
PN,10600
PS,8000
OL,1,Answer:␛Xhidden␛Gseen
```

`neottx render --reveal` shows the concealed text. In `neottx view` and the browser the key is `?`.

Browser: yes for both. `neottx`: yes for both, though `render` writes one still image and so shows only one flash phase. Kits: `Attribute.Flash` and `Attribute.Conceal`, `Attribute.FLASH` and `Attribute.CONCEAL`.

### 3.9 Boxes

A box starts at the second of two consecutive Start Box codes, and ends after End Box. `neottx --single-start-box` accepts one code.

Box membership shows only on a page with C5 or C6, or in a viewer mode that uses it. On such a page only boxed cells are drawn and the rest is the picture: transparent pixels, since there is no video behind.

```tti
PN,10700
PS,8001
OL,0,        Hidden in boxed mode
OL,5,hidden␛K␛KShown in the box␛J␛Jhidden
```

Browser: the same grid is drawn. `neottx`: yes. Kits: TypeScript has no name for these codes, so use `screen.code(row, column, 0x0B)`; Python has `Attribute.START_BOX` and `Attribute.END_BOX`. Neither `Screen` sets C5 or C6, so a boxed page goes through TTI.

### 3.10 Fastext and row 24

X/27/0 carries six links: red, green, yellow, cyan, a fifth that is not used, and Index. In TTI they are the `FL` line, in hexadecimal; `0` and `8FF` mean no link.

```tti
PN,10800
PS,8000
OL,1,Sport 140
OL,24,␛ANews 200  ␛BSport 300 ␛CTV 400    ␛FMore
FL,200,300,400,500,8FF,100
```

Row 24 shows only when the page carries X/27/0 with its "display row 24" flag (Annex H), and an `FL` line sets the flag. Without it the row stays blank and the receiver may use it. On the `saa5246a` profile row 24 shows whenever X/24 is present. `FL` cannot name a sub-page, and with one the writer uses a packed `OL,27` line.

The Index key follows the sixth link, and on a page with no links requests the initial page. A key works only while row 24 is drawn and the page is not boxed away (REQ-SEC-024), so a page cannot make a key act while the prompt is hidden. Fastext targets may be any page, hexadecimal included, which is how a viewer reaches pages they cannot key.

| | Call |
|---|---|
| TTI | `FL,...` |
| TypeScript | `screen.fastext([0x200, 0x300, 0x400, 0x500])`, `screen.indexLink(0x100)`, `screen.showFastextRow()`. `null` for no link. For a link that names a sub-page, `packedLinksLine` |
| Python | `screen.fastext([0x200, 0x300, 0x400, 0x500])`, `screen.index_link(0x100)`, `screen.show_fastext_row()` |

Browser: yes. `neottx`: yes. For prompts the receiver draws itself, use the Link Extension ([section 14](#14-links-beyond-fastext)).

### 3.11 National options

The Latin G0 set has 13 positions that change with the national option: 2/3, 2/4, 4/0, 5/B, 5/C, 5/D, 5/E, 5/F, 6/0, 7/B, 7/C, 7/D and 7/E (Table 36).

The option is three bits, C12 to C14, and the group is four more. Together they are the seven-bit designation of Table 32: `group × 8 + option`. The group comes from the page's X/28/0, then the magazine's M/29/0, then the receiver's configured region, which is 0 by default. At Levels 1.0 and 1.5 the option always comes from the header. At Levels 2.5 and 3.5 it comes from the same designation when there is one, in the order of Annex C.4 rule 1, and from the header otherwise.

In TTI, `RE` sets the group, and the writer turns it into an X/28/0 packet. `PS` sets the option:

| Option | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| `PS` value | `8000` | `8200` | `8100` | `8300` | `8080` | `8280` | `8180` | `8380` |

Note the order: option 1 is C14, which is `PS` bit 9.

| `RE` | Option | Set | G2 | Designation |
|---|---|---|---|---|
| 0 | 0 | Latin English | Latin | `0x00` |
| 0 | 1 | Latin German | Latin | `0x01` |
| 0 | 2 | Latin Swedish, Finnish, Hungarian | Latin | `0x02` |
| 0 | 3 | Latin Italian | Latin | `0x03` |
| 0 | 4 | Latin French | Latin | `0x04` |
| 0 | 5 | Latin Portuguese, Spanish | Latin | `0x05` |
| 0 | 6 | Latin Czech, Slovak | Latin | `0x06` |
| 1 | 0 | Latin Polish | Latin | `0x08` |
| 1 | 1 to 4, 6 | As group 0's German, Swedish, Italian, French, Czech | Latin | `0x09` to `0x0C`, `0x0E` |
| 2 | 0 to 5 | As group 0 | Latin | `0x10` to `0x15` |
| 2 | 6 | Latin Turkish | Latin | `0x16` |
| 3 | 5 | Latin Serbian, Croatian, Slovenian | Latin | `0x1D` |
| 3 | 7 | Latin Rumanian | Latin | `0x1F` |
| 4 | 0 | Cyrillic option 1, Serbian and Croatian | Cyrillic | `0x20` |
| 4 | 1 | Latin German | Latin | `0x21` |
| 4 | 2 | Latin Estonian | Latin | `0x22` |
| 4 | 3 | Latin Lettish, Lithuanian | Latin | `0x23` |
| 4 | 4 | Cyrillic option 2, Russian and Bulgarian | Cyrillic | `0x24` |
| 4 | 5 | Cyrillic option 3, Ukrainian | Cyrillic | `0x25` |
| 4 | 6 | Latin Czech, Slovak | Latin | `0x26` |
| 6 | 6 | Latin Turkish | Latin | `0x36` |
| 6 | 7 | Greek | Greek | `0x37` |
| 8 | 0 | Latin English | Arabic | `0x40` |
| 8 | 4 | Latin French | Arabic | `0x44` |
| 8 | 7 | Arabic | Arabic | `0x47` |
| A | 5 | Hebrew | Arabic | `0x55` |
| A | 7 | Arabic | Arabic | `0x57` |

A reserved value falls back: first the same option in group 0, then English. The fallback is counted as a diagnostic.

```tti
PN,10900
PS,8200
OL,1,[\]{|}~ shows the German letters
```

```tti
PN,11000
PS,8380
RE,6
OL,1,abcdefg shows Greek
```

`channel.ttx` has a `region` member ([section 11.3](#113-channelttx)), the group of a page that names none. It stands above the receiver's configured region and below `neottx --region`. A page's own `RE` or `OL,28` stands above it.

| | Call |
|---|---|
| TTI | `PS` and `RE`, or `OL,28` ([section 5.5](#55-the-colour-map-and-page-level-data)) |
| Program protocol | The typed page's `character_set`: `{ "region": 6, "national_option": 7 }` |
| TypeScript | `Screen` writes `region: null` and option 0. `context.publishTti` keeps `RE` and `PS` |
| Python | `Screen` writes the same. `Screen.load_tti` reads the `OL,28` line but not `RE` or `PS`, so give it an `OL,28` line |

`Screen.text` in both kits writes the English option only: it folds other characters to the nearest English one.

### 3.12 ESC and the second G0 set

ESC, `0x1B`, toggles between the default G0 set and a second one, from the next cell (clause 15.3). The second set is named by X/28/0 or M/29/0 with a Table 33 value. With no second set, or with `0x7F`, ESC only takes up its cell.

```tti
PN,11100
PS,8000
OL,1,Latin ␛[abcdef␛[ Latin
OL,28,@@@\CpCu_@|w␡KpZA`UB_wLs_w}w␡w]␡_␡}_wM@@
```

That `OL,28` line is X/28/0 with default designation `0x00` and second designation `0x37`, Greek, built with the helper in [section 5.5](#55-the-colour-map-and-page-level-data). Row 1 shows `αβγδεζ` between the Latin words.

Browser: yes. `neottx`: yes. Kits: write `0x1B` with `screen.code`, and carry the `OL,28` line as [section 9.5](#95-programs) does.

## 4. Level 1.5

### 4.1 How enhancement data is written

Packets X/26 hold 13 triplets each, and a page has up to 16 of them, designation codes 0 to 15, so 208 triplets. A triplet is 18 bits (clause 12.3.1):

| Field | Bits | Meaning |
|---|---|---|
| Address | D1 to D6 | 0 to 39 is a column, and 40 to 63 is a row: 41 to 63 are rows 1 to 23 and 40 is row 24 |
| Mode | D7 to D11 | What the triplet does |
| Data | D12 to D18 | Its data |

`value = address | mode << 6 | data << 11`.

**The packed TTI line.** `OL,26,` then one character for the designation code, `0x40 | code`, then 39 characters, three a triplet. Each character is `0x40` plus six bits of the value, the least significant first. Such a line needs exactly 40 characters. The Hamming 24/18 coding is the encoder's work: a TTI file holds the 18 bits.

| Triplet | Value | Packed | On air |
|---|---|---|---|
| Set Active Position, row 1, column 5 | `0x02929` | `idB` | `CE 92 85` |
| G0 `e` with acute, column 5 | `0x32C85` | `Err` | |
| Termination Marker, type 7 | `0x03FFF` | `␡␡C` | |

Fill a packet's unused triplets with Termination Markers. This Python writes a line:

```python
def triplet(address, mode, data):
    return address | mode << 6 | data << 11

def packed(value):
    return bytes(0x40 | (value >> shift) & 0x3F for shift in (0, 6, 12))

END = triplet(63, 0b11111, 0b111)   # Termination Marker: no more local data

def ol26(designation, triplets):
    """One OL,26 line; a short list is filled with Termination Markers."""
    triplets = (list(triplets) + [END] * 13)[:13]
    return b"OL,26," + bytes([0x40 | designation]) + b"".join(map(packed, triplets)) + b"\n"
```

**The kits.** A program's typed page carries triplets as fields, `{ "address": 41, "mode": 4, "data": 5 }`, in `enhancements`, and the other packed lines in `packets`.

| | Call |
|---|---|
| TypeScript | `context.publishTti("channel", 0x100, text)`, where `text` holds `OL,26` lines. `Screen` has no call for triplets |
| Python | `screen.load_tti(text)` takes `OL,26` to `OL,29` lines. Or `screen.enhancements.append({"designation": 0, "triplets": [...]})` with all 13 |
| Rust | `DisplayPage::local()` gives a `Triplets` with a method for every function, and lays out the packets |

### 4.2 Positions

The pass starts at row 0, column 0, walks the packets in ascending designation code and stops at a Termination Marker.

| Mode | Address | Data | Function |
|---|---|---|---|
| `00100`, Set Active Position | 40 to 63 | Column | The row. At Level 1.5 the column goes to 0, and each character triplet gives its own. At Levels 2.5 and 3.5 the data sets the column when it is below 40 |
| `00111`, Address Display Row 0 | 63 | | Row 0, column 0 |
| `00001`, Full Row Colour | 40 to 63 | | The row, column 0. Its colour acts at Level 2.5 |
| `11111`, Termination Marker | 63 | Type | Ends the data |

A column triplet sets the column in the active row, with these exceptions, which do not move it: modes `00100`, `00101` and `01010` (reserved) and `00110` (Programme Delivery Control).

At Level 1.5 NeoTeletext follows Annex A.3 by default: every row triplet except the Termination Marker sets the row from its address.

### 4.3 G0 characters and diacritical marks

Modes `10000` to `11111` write a G0 character with a mark. The low four mode bits number the mark, and the data is the character code (Table 29).

| Mode | Mark | | Mode | Mark |
|---|---|---|---|---|
| `10000` | None | | `11000` | Diaeresis |
| `10001` | Grave | | `11001` | Dot below |
| `10010` | Acute | | `11010` | Ring above |
| `10011` | Circumflex | | `11011` | Cedilla |
| `10100` | Tilde | | `11100` | Low line |
| `10101` | Macron | | `11101` | Double acute |
| `10110` | Breve | | `11110` | Ogonek |
| `10111` | Dot above | | `11111` | Caron |

The rules at every level above 1:

- The character comes from the page's default G0 set with **no national option** and no effect from ESC. On an English page, code `0x23` in a triplet is `#`, not `£`.
- In mode `10000`, data `0x2A` writes `@`.
- A value below `0x20` writes nothing and still sets the column.
- In pixels, a precomposed glyph is used when the font has one, and otherwise the mark is laid over the letter.

An overwrite replaces only the glyph. The character keeps the cell's colours, flash, conceal, box and size, draws as text even in mosaic mode, and shows on the top half of double height as double height. Addressed to the lower row of a double-height row, it is not shown. The later of two overwrites wins.

```tti
PN,11200
PS,8000
OL,1,e a c n u
OL,26,@iD@@rrBqpD{qFTwHxz␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C
```

Row 1 shows `é à ç ñ ü` at Level 1.5 and above, and `e a c n u` at Level 1.

Browser: yes. `neottx`: yes. A kit writes these only as triplets ([section 4.1](#41-how-enhancement-data-is-written)). Rust: `triplets.diacritic(column, code, mark)` and `triplets.character(column, code)`.

### 4.4 G2 and G3 characters

| Mode | Writes | Levels |
|---|---|---|
| `01111` | A G2 character of the page's G2 set | 1.5 and above |
| `00010` | A G3 character | 1.5 and above |
| `01011` | A G3 character | 2.5 and above. Ignored at 1.5, apart from moving the column |

G2 is the supplementary set: currency, fractions, arrows, the spacing marks of column 4, and letters such as `Æ`, `Ø`, `ß` (Table 37). G3 is the smooth mosaic and line-drawing set (Table 48). Its characters are drawn from geometry at every level, never from the font.

Positions the standard leaves undefined show a space: Latin G2 5/9, 5/A, 5/B and 6/5, and G3 6/E, 6/F, 7/E and 7/F. G3's 5/F shows the background colour.

```tti
PN,11300
PS,8000
OL,1,0123456789
OL,26,@iD@@ORAoQBBPCKPDPUEOh␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C
```

Row 1 shows `$£`, two G3 characters, `@`, `―` and the digits `6` to `9`. At Level 1.5 column 3's triplet is ignored and the digit `3` stays.

| Triplet | Fields | Effect |
|---|---|---|
| 1 | Address 41, mode `00100`, data 0 | Row 1, column 0 |
| 2 | Column 0, mode `01111`, data `0x24` | G2 `$` |
| 3 | Column 1, mode `01111`, data `0x23` | G2 `£` |
| 4 | Column 2, mode `00010`, data `0x20` | G3 2/0 |
| 5 | Column 3, mode `01011`, data `0x20` | G3 2/0, Level 2.5 form |
| 6 | Column 4, mode `10000`, data `0x2A` | `@` |
| 7 | Column 5, mode `01111`, data `0x50` | G2 `―` |

Browser: yes. `neottx`: yes. Rust: `triplets.g2(column, code)`, `triplets.g3(column, code)`, `triplets.g3_level_15(column, code)`.

Row 0 can be written too, from column 8 on, after Address Display Row 0: `triplet(63, 0b00111, 0)`. It applies when the page is displayed, not to headers rolling during a search.

## 5. Level 2.5

### 5.1 The row triplets

Addresses 40 to 63 (Table 28). "Local" means the page's own X/26 and "Active" an Active object. Adaptive and Passive objects ignore the three colour functions.

| Mode | Function | Address | Data |
|---|---|---|---|
| `00000` | Full Screen Colour | Reserved; write 41 | D4 to D0 a Colour Map index, D6 D5 zero |
| `00001` | Full Row Colour | The row | D4 to D0 the index, D6 D5 the scope |
| `00100` | Set Active Position | The row | The column |
| `00111` | Address Display Row 0 | 63 | As Full Row Colour, for row 0 |
| `01000` to `01101` | Programme Delivery Control | | Ignored |
| `10000` | Origin Modifier | 40 + row offset | Column offset 0 to 71 |
| `10001`, `10010`, `10011` | Object Invocation: Active, Adaptive, Passive | [Section 5.7](#57-objects) | |
| `10101`, `10110`, `10111` | Object Definition: Active, Adaptive, Passive | [Section 5.7](#57-objects) | |
| `11000` | DRCS Mode | | Not implemented: a reserved row triplet |
| `11111` | Termination Marker | 63 | D2 to D0, the type (below) |

The scope of Full Row Colour: `00` this row only; `11` this row and every row below. `01` and `10` set the position and no colour.

| Termination type | Meaning | Rust constant |
|---|---|---|
| `000` | Intermediate object page, more objects | `TERMINATION_INTERMEDIATE_MORE` |
| `001` | Intermediate object page, last object | `TERMINATION_INTERMEDIATE_LAST` |
| `010` | Final object page, more objects | `TERMINATION_FINAL_MORE` |
| `011` | Final object page, last object | `TERMINATION_FINAL_LAST` |
| `100` | Local object, more follow | `TERMINATION_LOCAL_OBJECT_MORE` |
| `101` | Local object, the last | `TERMINATION_LOCAL_OBJECT_LAST` |
| `110` | Local data ends, Local Objects follow | `TERMINATION_LOCAL_DATA_OBJECTS_FOLLOW` |
| `111` | Local data ends | `TERMINATION_LOCAL_DATA_END` |

### 5.2 The column triplets

Addresses 0 to 39 (Table 29):

| Mode | Function | Data | Level |
|---|---|---|---|
| `00000` | Foreground Colour | D4 to D0 a Colour Map index | 2.5 |
| `00001` | G1 mosaic character | The code | 2.5 |
| `00010` | G3 character | The code | 1.5 |
| `00011` | Background Colour | D4 to D0 a Colour Map index | 2.5 |
| `00100` | Reserved | | Does not move the column |
| `00101` | Reserved. NeoTeletext's control ([section 18](#18-controls-cells-a-page-answers-itself)) | | Does not move the column |
| `00110` | Programme Delivery Control | | Does not move the column |
| `00111` | Additional Flash Functions | [Section 5.4](#54-additional-flash-functions) | 2.5, not in the browser |
| `01000` | Modified G0 and G2 Designation | A Table 34 value | 2.5 |
| `01001` | G0 character | The code | 2.5 |
| `01010` | Reserved | | Does not move the column |
| `01011` | G3 character | The code | 2.5 |
| `01100` | Display Attributes | [Section 5.3](#53-non-spacing-attributes-and-size) | 2.5 |
| `01101` | DRCS Character Invocation | | Not implemented: moves the column only |
| `01110` | Font Style | | Not implemented: moves the column only |
| `01111` | G2 character | The code | 1.5 |
| `10000` to `11111` | G0 character with a mark | The code | 1.5 |

A G1 character in columns 2, 3, 6 or 7 is a block mosaic, separated only by the non-spacing Underline or Separated attribute, never by Level 1 codes `0x19` and `0x1A`. In columns 4 and 5 it is the current G0 character.

Hold never replaces a character written by a triplet, and a G3 character does not change the held mosaic. National options and ESC never apply to a triplet's character.

### 5.3 Non-spacing attributes and size

A non-spacing attribute changes the display without using a cell. It takes effect at its own cell and lasts to the end of the row or a later attribute of its type.

**Foreground Colour and Background Colour** set the colour in D4 to D0 and do not change alphanumeric or mosaic mode. Data with D6 or D5 set only moves the column.

**Display Attributes** (mode `01100`) sets all six at once from its data bits, at its cell. A 0 bit also turns off what a Level 1 attribute turned on.

| Bit | Value | Attribute |
|---|---|---|
| D0 | `0x01` | Double height |
| D1 | `0x02` | Boxing or window |
| D2 | `0x04` | Conceal. A Level 1 colour code does not end it |
| D3 | `0x08` | Ignored |
| D4 | `0x10` | Invert: swaps the displayed colours. While it is in force, a Level 1 change of foreground alters the displayed background |
| D5 | `0x20` | Underline, or separated mosaics for G1. Level 1 code `0x19` does not cancel it |
| D6 | `0x40` | Double width. D0 and D6 together, `0x41`, are double size |

**Size.** Double height, width and size exist as spacing attributes `0x0D`, `0x0E`, `0x0F` and as Display Attributes. Sizes resolve by Annex C.3:

- Double height and double size do not take effect in rows 0, 23 and 24, and double width and double size not in column 39. The character is drawn without the doubling that cannot be shown.
- Earlier size attributes in scan order win. A later character drops the doubling that conflicts.
- All the attributes of the origin apply to every part of an enlarged character.
- A spacing double height or double size suppresses the row below. A non-spacing one does not: only the cells covered by lower halves are hidden, and the rest of the row below shows.

A wide character takes the cell after it, so put letters in every other cell. Python's `screen.double_width(row, column, colour, text)` does that with a spacing attribute.

```tti
PN,11400
PS,8000
OL,1,Plain foreground and background
OL,2,Underline Invert Hidden Normal
OL,3,W i d e
OL,5,S i z e
OL,26,@iD@@`@F@BVCAjD@@LPJLHQLBXL@kD@@L`mD@@l`
OL,26,A␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C
```

Row 1 is red, then blue from column 6, on a green background from column 22. Row 2 underlines its first word, inverts its second, conceals its third and turns them all off at column 24. Row 3 is double width. Row 5 is double size, and because that is non-spacing, row 6 is not suppressed. A second, empty packet follows because the thirteen triplets fill X/26/0 and the Termination Marker needs a place.

Browser: yes, without the underline. `neottx`: yes.

Rust: `triplets.foreground(column, colour)`, `triplets.background(column, colour)`, `triplets.attributes(column, DisplayAttributes { .. })`.

### 5.4 Additional Flash Functions

Column mode `00111`. **In `neottx` built with the feature, and not in the browser or the default `neottx`.** Without the feature the triplet only sets the column.

| Data | Value | Meaning |
|---|---|---|
| D1 D0 | `00` | Steady |
| | `01` | Normal flash to the background colour |
| | `10` | Invert phase of flash to background colour |
| | `11` | Flash to the same entry of the adjacent CLUT: the foreground index exclusive-OR 8 |
| D4 to D2 | `000` | Slow, 1 hertz |
| | `001`, `010`, `011` | Fast, 2 hertz, phases 1, 2, 3 |
| | `100` | Incremental: successive characters from the triplet's column take phases 1, 2, 3, 1 and so on, for movement to the right |
| | `101` | Decremental: phases 1, 3, 2, 1, for movement to the left |
| | `110`, `111` | Reserved: only sets the column |

The standard gives no duty cycle, so NeoTeletext divides a second into twelve units. Slow flash is on in units 0 to 8. Fast flash, in each half-second of six units, is off in two units given by its phase. The attribute lasts to the row's end or the next flash attribute, acts on the foreground only, and never changes Level 1 Flash.

A still `neottx render` cannot show the phases. They are held by the engine's test `crates/neoteletext-core/tests/level25_attributes.rs`, which passes with the feature on.

Rust: `triplets.flash(column, FlashMode::Normal, FlashRate::Fast(1))`.

### 5.5 The Colour Map and page-level data

Every colour at Levels 2.5 and 3.5 is an index 0 to 31, `8 × CLUT + entry`. The default map is Table 30 (each `0xRGB`, four bits a primary):

| Entry | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| CLUT 0, index 0 to 7 | `000` | `F00` | `0F0` | `FF0` | `00F` | `F0F` | `0FF` | `FFF` |
| CLUT 1, index 8 to 15 | Transparent | `700` | `070` | `770` | `007` | `707` | `077` | `777` |
| CLUT 2, index 16 to 23 | `F05` | `F70` | `0F7` | `FFB` | `0CA` | `500` | `652` | `C77` |
| CLUT 3, index 24 to 31 | `333` | `F77` | `7F7` | `FF7` | `77F` | `F7F` | `7FF` | `DDD` |

Index 8 is always transparent, and no packet changes it. A 4-bit primary times 17 gives its 8-bit value.

**Packet X/28/0 Format 1** carries a page's data (Table 4). Its 13 triplets read as one stream of 234 bits, stream position `18 × t + b - 1` being bit `b` of triplet `t + 1`:

| Stream bits | Field |
|---|---|
| 0 to 3 | Page function: 0 for a basic Level 1 page |
| 4 to 6 | Page coding: 0 |
| 7 to 13 | Default G0 and G2 designation, Table 32 |
| 14 to 20 | Second G0 designation, Table 33. `0x7F` for none |
| 21 to 27 | Side-panel fields. Read past; leave them 0 |
| 28 to 219 | Sixteen colour words of 12 bits: CLUT 2 entries 0 to 7, then CLUT 3. Each is red, green, blue, four bits each, low bit first |
| 220 to 224 | Default screen colour |
| 225 to 229 | Default row colour |
| 230 | Black Background Colour Substitution |
| 231 to 233 | Colour Table Re-mapping |

Because a packet holds every field, a page that wants one field writes the others at their defaults. This Python uses `packed` from [section 4.1](#41-how-enhancement-data-is-written):

```python
TABLE_30_CLUTS_2_3 = [0xF05, 0xF70, 0x0F7, 0xFFB, 0x0CA, 0x500, 0x652, 0xC77,
                      0x333, 0xF77, 0x7F7, 0xFF7, 0x77F, 0xF7F, 0x7FF, 0xDDD]

def ol28(designation=0, default=0, second=0x7F, words=TABLE_30_CLUTS_2_3,
         screen=0, row=0, substitute=0, remap=0, packet=28):
    """X/28/0 (designation 0) or X/28/4 (designation 4), as an OL line.

    packet=29 makes the same line M/29/0 or M/29/4. Each word is 0xRGB.
    """
    bits = [0] * 234
    def put(start, count, value):
        for index in range(count):
            bits[start + index] = value >> index & 1
    put(7, 7, default)
    put(14, 7, second)
    for index, word in enumerate(words):
        red, green, blue = word >> 8 & 15, word >> 4 & 15, word & 15
        put(28 + index * 12, 12, red | green << 4 | blue << 8)
    put(220, 5, screen)
    put(225, 5, row)
    put(230, 1, substitute)
    put(231, 3, remap)
    values = [sum(bits[18 * t + b] << b for b in range(18)) for t in range(13)]
    return b"OL,%d," % packet + bytes([0x40 | designation]) + b"".join(map(packed, values)) + b"\n"
```

**CLUTs 2 and 3.** Redefined by X/28/0, or when that is absent by the magazine's M/29/0. This page changes CLUT 2 entry 0 to `804`, and draws with index 16:

```tti
PN,11500
PS,8000
OL,1,Index 16 is now 804
OL,26,@iD@@@H␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C
OL,28,@@@|G@Bt_@|w␡KpZA`UB_wLs_w}w␡w]␡_␡}_wM@@
```

**Screen and row colours.** The screen colour fills the area around the page. A row's colour shows wherever a cell's background is transparent, index 8, and in the row's cells under substitution. The row colour does **not** replace Level 1's black background by itself: that is what substitution is for.

| Value | Highest first |
|---|---|
| Screen colour | Full Screen Colour triplet; the page's default; the magazine's; index 0 |
| A row's colour | Full Row Colour triplets in order; the screen colour, only when a Full Screen Colour triplet set it; the page's default row colour; the magazine's; index 0 |

No row colour is drawn in row 0, columns 0 to 7.

**Black Background Colour Substitution.** Stream bit 230. The start-of-row black background, and `0x1C`, take the row colour instead. A black set by `0x00` then `0x1D` is not substituted, and neither is a colour set by a triplet.

**Colour Table Re-mapping.** Stream bits 231 to 233. Level 1 colour codes, and the start-of-row white and black, read their CLUTs from here:

| Value | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Foreground CLUT | 0 | 0 | 0 | 1 | 1 | 2 | 2 | 2 |
| Background CLUT | 0 | 1 | 2 | 1 | 2 | 1 | 2 | 3 |

With value 2, for example, a page's Level 1 background black becomes CLUT 2 entry 0, and Level 1 colours keep CLUT 0.

**The magazine's packets.** M/29/0 and M/29/4 carry the same fields for a magazine, and any page without its own packet takes them. In TTI they go on the magazine's page `mFF`:

```tti
PN,1FF00
PS,0000
OL,29,@@@}G@Bt_@|w␡KpZA`UB_wLs_w}w␡w]␡_␡}_wM@@
PN,10000
PS,8000
OL,1,Index 16 from M/29/0
OL,26,@iD@@@H␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C
```

That `OL,29` line designates group 4, so the text shows in Cyrillic. Precedence is the page before the magazine, in the order X/28/0, X/28/4, M/29/0, M/29/4. A group of fields decoded with a damaged triplet counts as absent for that group alone.

Browser: yes for all of this. `neottx`: yes. A program can carry `x28` and `m29` lines in a sub-page's `packets`, which the schema allows. `x28` lines were tried on a live server on 2 November 2026, and reach a receiver: for all 72 language pages of the two demo sites, behind `teletext-server` at neoteletext-app-server `c6c692b` with kits 6.0.0 and 12.0.0, the packets received on the push WebSocket held one X/28/0 with the page's designation, and the same X/28/0 and X/26 packets as `neottx convert` makes of the page's TTI, byte for byte, and rendering them with `neottx` at engine `fecedf4` gave rows 1 to 23 identical to a render of the file. The route was TTI through the library's `RawSubPage` and the kit's TTI reader. `m29` lines, and a page of `packets` built by hand, were not tried. A ready-made page from `neottx write-text` has no `FL` line, so it shows no row 24 when rendered from the file, and shows one only once its links are given, as `RawSubPage` does when it is passed `fastext`. Rust: `DisplayPage::page_data(fields)`, `neutral_fields(national)`, `MagazinePackets`.

### 5.6 Modified designation

Column mode `01000` selects a G0 and G2 pair from Table 34 for characters placed by triplets. The value is a Table 32 value. It never affects the Level 1 page. It lasts to the row's end in local data and Active objects, and to the last character cell of the object in Adaptive and Passive objects, or to the next such triplet. At Level 2.5 a designation that would make more than two pairs on a page, counting the default, is ignored and counted. Level 3.5 has no limit.

```tti
PN,11600
PS,8000
OL,1,abcd
OL,26,@iD@@h[@ppAPqBpq␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C
```

Column 0's designation is `0x37`, Greek, so the row shows `αβγd`. The `d` at column 3 is the page's own.

Browser: yes. `neottx`: yes. Rust: `triplets.designation(column, value)`.

### 5.7 Objects

An object is a list of triplets defined once and placed anywhere. Objects need the `objects` feature: **the browser has it, and the default `neottx` does not.**

| Type | Attributes |
|---|---|
| Active | Acts as local data: its attributes run to the end of the row on every character |
| Adaptive | Starts with the underlying attributes. On each row its changes affect the cells between the first and the rightmost it addresses; right of that the underlying attributes return |
| Passive | Starts each invocation white on black, normal size, steady, unboxed, not concealed, contiguous. Its attributes persist across rows and apply only to cells it writes |

Where several sources write a cell, Passive wins, then Adaptive, then local data, then Active, then the Level 1 page. Between two of one type the later invoked wins.

| Invoker | May invoke |
|---|---|
| Local data | Active, Adaptive and Passive, from local, POP or GPOP |
| Active object | Adaptive and Passive |
| Adaptive object | Passive |
| Passive object | Nothing |

An invocation's fields (Table 28):

| Field | Bits | Meaning |
|---|---|---|
| Address | `1 S1 S0 X N8 N7` | S1 S0: `01` local, `10` POP, `11` GPOP |
| Mode | | `10001` Active, `10010` Adaptive, `10011` Passive |
| Data | `N6` to `N0` | The object number's low bits |

An **Origin Modifier** immediately before the invocation moves the object's origin: `triplet(40 + rows, 0b10000, columns)`. Inside the object every coordinate is relative to its origin. When the object ends, the active position returns to its value at the invocation.

An **Object Definition** has the same address form, with the usage in place of the source: `01` Level 2.5, `10` Level 3.5, `11` both. Its body runs to the next definition or Termination Marker, at most 507 triplets. Limits: 127 invocations of each type a page, 15 objects open at once, and 15 opened in succession with nothing displayable between. Further invocations are ignored and counted.

**A Local Object** is defined in the page's own X/26, after the local data. N7 to N4 are the designation code of the packet holding its definition, and N3 to N0 the triplet within it, from 0.

```tti
PN,11700
PS,8000
OL,2,Active
OL,26,@jdChQH␡_C␡_C␡_C␡_C␡_C␡_C␡_C␡_C␡_C␡_C␡_C
OL,26,AxUH@`@Ap`BPa␡␡B␡␡B␡␡B␡␡B␡␡B␡␡B␡␡B␡␡B␡␡B
```

The local data sets row 2, column 7, invokes the Active object defined at X/26/1 triplet 0, and ends with type `110`, filling its packet with the same marker. The object turns red at its column 0 and writes `AB` at its columns 1 and 2, relative to its origin, so the row shows `Active  AB`. Run it in a build with objects: the default `neottx` shows only `Active`.

**A public object** lives on a Public Object Page (POP) or Global Public Object Page (GPOP), a page of function 3 or 2 with coding 2 (`PF,3,2`). It holds up to 16 sub-pages, by S1. Its rows are packed like X/26: packets 1 to 4 hold pointers, and definitions start at packet 3 (clause 10.5.1). A page finds its POP and GPOP through its own X/27/4, and at Level 3.5 also X/27/5, or otherwise the magazine's Magazine Organization Table on `mFE`.

Build these with the Rust builder, which computes the pointers. This example was compiled and rendered:

```rust
use neoteletext_core::packet::{ObjectKind, ObjectUsage};
use neoteletext_core::types::SubCode;
use neoteletext_formats::author::{self, DisplayPage, LinkFunction, ObjectPage, Stream, Triplets, address};

/// A POP on 1A0 with one Active object, and page 100 that links and invokes it.
fn build() -> author::Result<Stream> {
    let mut body = Triplets::new();
    body.foreground(0, 1).text(1, b"FROM THE POP");
    let mut pop = ObjectPage::new(address(0x1A0)?, false);
    let object = pop.define(0, ObjectKind::Active, ObjectUsage(0b11), body)?;

    let mut page = DisplayPage::new(address(0x100)?, SubCode::new(0));
    page.header(b"POP EXAMPLE").text(3, 0, b"Level 1 text")?;
    page.link_level_25(LinkFunction::Pop, pop.address(), 1)?;
    page.local().position(3, 15)?.invoke(object);

    let mut stream = Stream::new();
    stream.extend(pop.build()?);
    stream.push(page.build()?);
    Ok(stream)
}
```

`stream.tti()` and `stream.write_t42(...)` write it. A complete example of every object type and of the MOT is `cargo xtask level25-stream FILE.t42 --tti FOLDER`, whose page 100 is an index of its pages.

**Default objects.** A page with no X/26 that carries a display triplet takes the default objects of the MOT: up to two through its magazine's GPOP link and up to two through its POP link, each with its origin at row 0, column 0.

**Where object pages must be.** A reader only ever holds what it was sent:

| Channel | Objects that work |
|---|---|
| A file | All of them, when the object page is in the file |
| A static channel | Local Objects. Public objects when the object page is in the page's own file or in `index.t42`, since a reader asks for no other file for them |
| A live channel | **Local Objects only.** How a selected sub-page's object pages and MOT reach the receiver is not designed (TODO-2023 item 7) |

## 6. Level 3.5

Level 3.5 is everything of Level 2.5, and:

| Feature | How | Browser | `neottx` |
|---|---|---|---|
| CLUTs 0 and 1 redefined | X/28/4 or M/29/4. Same layout as X/28/0, with the sixteen words CLUT 0 then CLUT 1 | Yes | Yes |
| More compositional links | X/27/4 links 4 and 5 and X/27/5 links 0 and 1 take their role from their function bits. MOT packets X/22 to X/24 | Yes | With objects |
| Modified designations with no limit | [Section 5.6](#56-modified-designation) | Yes | Yes |

With the `ol28` helper, `ol28(designation=4, words=...)` writes X/28/4. Word 8, CLUT 1 entry 0, is ignored: index 8 stays transparent. A page that redefines CLUT 0 should usually keep entries 0 and 7 black and white, for the header.

```tti
PN,11800
PS,8000
OL,1,␛AOrange, not red, at Level 3.5
OL,28,D@@|G@@pc@|p␡@@␡CO|␡␡O@pA@\p]@@wAG\w]G@@
```

Bold, italic and proportional spacing, the other Level 3.5 features, are not drawn ([section 8](#8-what-is-not-supported)).

## 7. The character sets of the standard

Inside the decoder a character is a set and a seven-bit code, never Unicode. Conversion to Unicode happens at output.

The standard's 24 sets are all present in every build:

| Kind | Sets | Table |
|---|---|---|
| G0 | Latin and its 13 national options | 35, 36 |
| G0 | Cyrillic options 1, 2 and 3 | 38, 39, 40 |
| G0 | Greek, Arabic, Hebrew | 42, 44, 46 |
| G2 | Latin, Cyrillic, Greek, Arabic | 37, 41, 43, 45 |

G1 (Table 47) and G3 (Table 48) are drawn by rule. Thirteen plus one Latin, three Cyrillic, three others and four G2 make the 24 of `neottx font sets`, which reports a loaded font against them.

| Reached by | Set used |
|---|---|
| A row of a page | The default G0, with national option, or after ESC the second G0 |
| A row in mosaic mode, columns 4 and 5 | The G0 set, with national option |
| A triplet, modes `10000` to `11111` and `01001` | The current G0 set, no national option |
| A triplet, mode `01111` | The current G2 set |
| A triplet, modes `00010` and `01011` | G3 |

Four national glyphs are too small in the standard to read, and are mapped so: Polish 5/B to U+01B5, Polish 7/D to U+0142, English 6/0 to U+2014 and English 7/C to U+2016. The Turkish currency sign at 2/3 is U+20BA.

## 8. What is not supported

A page that uses any of these still shows, as a receiver without the feature shows it. None is an error.

| Feature | State | Reason |
|---|---|---|
| Side panels (clause 12.5) | **Never** (DEC-1636) | The owner wants a predictable screen size. A page is always 40 by 25. The fields are read past, and an object placed past column 39 places nothing |
| DRCS (clause 14) | **Never** (DEC-619) | NeoTeletext wants no form of bitmap graphics. A DRCS Character Invocation places nothing, so the Level 1 character beneath shows. X/28/1 and M/29/1 are ignored, and the DRCS links unused. A DRCS page is never shown as text |
| Level 3.5 font styles: bold, italic, proportional spacing | **Not drawn** (DEC-620) | Removed on the owner's instruction. The Font Style triplet only moves the column. Underline stays |
| TOP navigation (clause 11.2) | Not implemented | TOP pages are stored as data pages and not used to navigate |
| Data broadcasting (EN 300 708 clause 4), packet 31 services | Out of scope (DEC-1116) | Pages are recognised and not decoded. NeoTeletext's own records use data channel 12 |
| Programme Delivery Control | Ignored in display | Triplets of modes `01000` to `01101` and `00110` do nothing |
| Teletext generation as a product | Out of scope (DEC-1122) | The page encoder exists for testing and conversion. There is no broadcast inserter |
| Additional Flash Functions in the browser | Implemented in the engine, not built into the browser | The `modern-classic` profile leaves them out (DEC-595) |
| Packet X/25 display | Out of scope (DEC-1118) | Stored, not displayed |
| The Magazine Inventory Page | Out of scope (DEC-1123) | Stored and not read: the MOT and X/27/4 find every object page |
| A layout for proportional spacing | Out of scope (DEC-1112) | The standard defines none |
| 525-line teletext, Viewdata | Out of scope (DEC-1115, DEC-1120) | Different systems |
| Languages needing more than one byte a character, Indic scripts, Burmese, Khmer, Sinhala, Inuktitut syllabics | Out of scope (DEC-1125, DEC-1126, DEC-1127) | They do not fit the single-byte sets of [section 9](#9-character-sets-beyond-the-standard) |

---

# Part 2: what NeoTeletext adds

## 9. Character sets beyond the standard

The feature `extended-sets`, in the default build and the browser's, adds 32 sets to the standard's 24: six national options of Latin G0, 22 whole G0 sets and four G2 sets. They are one byte a cell, read as EN 300 706 defines, and they serve about 55 languages. They use designation values that Tables 32 to 34 reserve, 29 of them, so another decoder takes the fallback of [section 3.11](#311-national-options), as does a build without the feature.

### 9.1 The groups and options

In TTI, `RE` is the group and `PS` the option, as in [section 3.11](#311-national-options). `neottx write-text --set NAME` takes the name in the last column, and handles marks, right-to-left order and rows for you.

| Group, `RE` | Option | `PS` | Value | Language or set | G2 | `write-text` |
|---|---|---|---|---|---|---|
| 0101, `5` | 0 | `8000` | `0x28` | Hausa and Fula (Latin option) | Latin | `hausa-fula` |
| | 1 | `8200` | `0x29` | Akan, Lingala, Bambara and other West African (Latin option) | Latin | `west-african` |
| | 2 | `8100` | `0x2A` | Ewe (Latin option) | Latin | `ewe` |
| | 3 | `8300` | `0x2B` | Kabyle and Tamazight (Latin option) | Latin | `kabyle-tamazight` |
| | 4 | `8080` | `0x2C` | Azerbaijani (Latin option) | Latin | `azerbaijani` |
| | 5 | `8280` | `0x2D` | Kanuri and Mossi (Latin option) | Latin | `kanuri-mossi` |
| | 6 | `8180` | `0x2E` | Yoruba and Igbo | Latin | `yoruba-igbo` |
| | 7 | `8380` | `0x2F` | Vietnamese | Vietnamese | `vietnamese` |
| 0111, `7` | 0 | `8000` | `0x38` | Ukrainian | Cyrillic | `ukrainian` |
| | 1 | `8200` | `0x39` | Belarusian | Cyrillic | `belarusian` |
| | 2 | `8100` | `0x3A` | Macedonian | Cyrillic | `macedonian` |
| | 3 | `8300` | `0x3B` | Serbian | Cyrillic | `serbian` |
| | 5 | `8280` | `0x3D` | Kyrgyz and Mongolian | Cyrillic | `kyrgyz-mongolian` |
| | 6 | `8180` | `0x3E` | Tatar | Cyrillic | `tatar` |
| | 7 | `8380` | `0x3F` | Tajik | Cyrillic | `tajik` |
| 1001, `9` | 0 | `8000` | `0x48` | Persian and Dari | Arabic | `persian` |
| | 1 | `8200` | `0x49` | Urdu | Arabic | `urdu` |
| | 2 | `8100` | `0x4A` | Pashto | Arabic | `pashto` |
| | 3 | `8300` | `0x4B` | Sindhi | Arabic | `sindhi` |
| | 4 | `8080` | `0x4C` | Sorani Kurdish | Arabic | `sorani` |
| | 5 | `8280` | `0x4D` | Uyghur | Arabic | `uyghur` |
| | 6 | `8180` | `0x4E` | Balochi | Arabic | `balochi` |
| | 7 | `8380` | `0x4F` | Arabic in plain letters | Arabic | `arabic` |
| 1011, `B` | 0 | `8000` | `0x58` | Georgian (Mkhedruli) | Latin | `georgian` |
| | 1 | `8200` | `0x59` | Armenian | Armenian | `armenian` |
| | 2 | `8100` | `0x5A` | Tifinagh | Latin | `tifinagh` |
| 1100, `C` | 0 | `8000` | `0x60` | Latin English, with Thai second | Thai | None |
| | 2 | `8100` | `0x62` | Thai | Thai | `thai` |
| | 4 | `8080` | `0x64` | Lao | Lao | `lao` |

Counting them: the 29 values are the six options, the 22 whole G0 sets, and `0x60`, which adds no G0 set of its own. The 32 sets are those 28 new G0 tables and the Vietnamese, Armenian, Thai and Lao G2 sets. Every G0 set has the space at 2/0 and the block at 7/F. Each of the 29 values was rendered with a page like the one below, showing its codes 2/0 to 7/F. Browser: yes for all of them. `neottx`: yes. A build without `extended-sets` falls back as a reserved value does.

```tti
PN,21000
PS,8000
RE,7
OL,1,abcdefghijklmnopqrstuvwxyz
```

Row 1 shows the Ukrainian set's lowercase letters.

The code tables are in `crates/neoteletext-core/src/charset/`: `g0_extended.rs`, `arabic_script.rs`, `thai_lao.rs`, `latin.rs` and `g2.rs`. The designations are `extended_designations.rs`.

**The second set.** Every new set has Latin English as its second G0 set, reached by ESC, so a page can mix a language with English. Value `0x60` differs: its second set is Thai, with no X/28 at all and on a TTI page with `RE,C`, whose X/28/0 from the writer names `0x62`.

**Marks.** A diacritical-mark triplet numbers its mark as [section 4.3](#43-g0-characters-and-diacritical-marks) does. On a page whose G2 set is Vietnamese, mark 12, `11100`, is the hook above in place of the low line. Vietnamese and Yoruba-Igbo are whole sets rather than Latin options so that a triplet's mark finds its base letter, since a triplet never reads a national option.

### 9.2 Writing text in these sets

```sh
neottx write-text --set vietnamese --page 300 input.txt page.tti
```

Each character is written as, in order of preference: a code of the current G0 set; after an ESC, a code of Latin English; a G0 letter with an X/26 mark; a G2 character by X/26 over a stand-in. Anything else is refused, naming the character and its line. Text fills rows 1 to 23.

The command takes 46 names: the 28 of the table and 18 of the standard's sets, `english` to `hebrew`. Its `--help` lists only 18 of them.

### 9.3 Arabic-script joining

Group 1001 holds each letter once, and the receiver chooses its joined form. Table 44's Arabic sets, by contrast, send each form as its own code, and stay as they are.

- **Rows are in visual order,** as Table 44's are. The first letter of a word in reading order has the highest column. A programmer writing rows by hand writes the word backwards. `write-text` does this with the Unicode Bidirectional Algorithm, and runs of digits and Latin stay left to right.
- **After a page is composed,** each row is passed once from right to left. A letter's previous letter is the cell to its right and its next the cell to its left, when each holds a letter of the same set with no mark.
- **A letter joins its previous letter** when it can join backwards and that letter can join forwards. It joins its next when it can join forwards and that letter can join backwards. Joining types are Unicode's `ArabicShaping.txt`: dual-joining, right-joining, none, and the tatweel, which joins both sides.
- **Its form** is isolated, final (joins previous only), initial (joins next only) or medial (both). The code points are Arabic Presentation Forms, or private-use ones where Unicode has none.
- **Lam-alef** is one code, in each set just before the tatweel. `write-text` writes `لا` as that code.
- **Digits** keep codes 3/0 to 3/9, drawn in the language's shapes.

A join needs both cells to hold letters of the same set with no mark, so a space, an attribute or a character of another set breaks it. `neottx text` writes base letters. `neottx render` and the browser draw joined forms.

```sh
printf 'سلام دنیا\n' > fa.txt
neottx write-text --set persian --page 400 fa.txt fa.tti
```

### 9.4 Thai and Lao

The Thai sets are those of the Philips SAA5246AP/S, and Lao's codes come from the 1990 World System Teletext specification. A mark is an ordinary character in its own cell. The receiver neither overlays nor reorders.

Each line of text takes three kinds of row: the letters, their upper marks on the row before and their lower vowels on the row after, each in its letter's column. A line's lower vowels share a row with the next line's upper marks unless a column needs both. A vowel with a tone is one G2 glyph, placed by X/26 over the vowel alone. In `write-text`, `ำ` is written as `ํ` over the consonant and `า` beside it. The G2 sets' columns 5 and 6 hold these pairs, which `neottx text` writes as two combining marks.

```sh
printf 'สวัสดี\n' > th.txt
neottx write-text --set thai --page 401 th.txt th.tti
```

Partly settled: the code tables mark Thai 4/0, 7/9, 7/A and 7/C as readings still to be confirmed. Thai G2 6/D to 6/F and several Lao positions are not yet identified and show a space.

### 9.5 Programs

The kits' `Screen.text` writes the English option. For any other set, a program writes codes from its own table and adds the designation as an `OL,28` line:

```ts
screen.codes(1, 0, codesInTheSet);                                  // seven-bit codes
context.publishTti("channel", 0x300, screen.toTti(0x300) + ol28Line);   // the X/28/0 goes with the page
```

```python
screen.codes(1, 0, codes_in_the_set)
screen.load_tti(ol28_line)              # the X/28/0 goes in screen.packets
```

The simplest path for fixed text is `neottx write-text`, then `publishTti` or `Screen.load_tti` on the file it wrote. It writes an X/28/0 line, so both kits carry the set. Thai and Lao mix rows and triplets, which is another reason to let it do the work.

## 10. Noto Teletext

The font's rules are in [the one compiled font](../PROTOCOL.html#DOC-1851).

Noto Teletext is the one compiled font, in every build that draws (DEC-1761, DEC-1766). It is Google's Noto fonts converted to the 12 by 20 cell, licensed under the SIL Open Font License 1.1, and it replaces Bedstead, which is gone.

- There is no font choice. No feature selects it, the browser has no font setting, and **no channel or page can name a font**: `channel.ttx` refuses a `font` member and a `TF` line is an error. An author cannot change the look of text except through colour, size and the enhancement attributes.
- It holds every character of the standard's 24 sets and of the 32 of [section 9](#9-character-sets-beyond-the-standard), with their joined forms and marks.
- Each glyph is 12 pixels by 20 lines. Capitals stand on lines 2 to 15, with the baseline on line 16. It is drawn line for line and never rounded.
- Row 0's status area is always drawn in it.
- A character the font lacks is drawn as a hollow box, never as a wrong character. In a supported set that is a defect in the font.
- Mosaics and G3 are drawn by rule, not from the font.

`neottx render --font FILE` draws in a loaded BDF font, 12 by 10 or 12 by 20, for a person's own use. `neottx font sets FONT` reports a font against the 24 sets. This is a choice of the viewer's tool and no page reaches it. Its form and limits are REQ-FNT-002.

## 11. Channels and channel.ttx

### 11.1 A channel is a folder

A channel is a folder on the web, or on any storage, with fixed file names. The smallest one is a folder holding `100.tti`. A hand-written folder of `.tti` files needs nothing else, and any static host serves it.

For the walkthrough, read [`creating-a-channel.md`](creating-a-channel.md).

### 11.2 The files, as built

| Name | Holds |
|---|---|
| `channel.ttx` | The channel's settings, JSON, at most 16,384 bytes |
| `contents.txt` | The channel's table of contents |
| `index.t42` | A bundle of first sub-pages, so a channel opens with one request |
| `NNN.tti`, `NNN.t42` | Page `NNN`, or its first sub-page when it has several |
| `NNN/SSSS.t42`, `NNN/SSSS.tti` | One sub-page, in a folder named for its page, at the path of its address |
| `NNN/P.sub` | Part `P` of a page's list of sub-pages, 64 rows, with validators and titles |
| `push` | The live connection, a WebSocket |

[DOC-2034](../PROTOCOL.html#DOC-2034) and [DOC-2039](../PROTOCOL.html#DOC-2039) propose `M.pag` and `NNN.ep1`. **Those names are not built**; the code and [DOC-1909](../PROTOCOL.html#DOC-1909) use the table above.

Digits are capitals, with no other spelling. A reader tries `NNN.tti`, then `NNN.t42`.

### 11.3 channel.ttx

Every member is optional. An unknown or duplicate member refuses the file and the channel does not open.

```json
{
  "name": "Example",
  "initial_page": "100",
  "push": { "input": true },
  "services": [
    { "name": "weather", "display_name": "Weather", "channel": "https://weather.example/" }
  ],
  "aliases": { "300": "weather:100" },
  "refresh": 60
}
```

| Member | Holds | Default |
|---|---|---|
| `name` | The channel's name, at most 120 characters. Shown outside the page, never in row 0 | The address |
| `initial_page` | Three decimal digits | `"100"` |
| `push` | An object, whose presence makes the channel live. Its one member is `input`, true when it takes keys | None |
| `region` | The default character set group, 0 to 15, for a page that names none | The reader's |
| `services` | Linked channels, for `name:mpp` links | None |
| `aliases` | Up to 16: a page number and a target, `name:mpp` or a channel address | None |
| `refresh` | Seconds, 5 to 86,400, between asking for the page on screen again | Never |

Tried and confirmed: `{"presentation": "site"}` and `{"push": {"address": "..."}}` are both refused. [DOC-2037](../PROTOCOL.html#DOC-2037) describes `presentation`, but **it is not built**. `push.address`, `push.method`, `page_template` and `font` are withdrawn.

`neottx probe <address>` opens a channel as a receiver does and reports each step, and `--allow-local 127.0.0.1` lets it reach a local server.

### 11.4 contents.txt

Lines of tab-separated fields. Empty lines and lines starting `#` are ignored.

```text
# a comment
s	News
p	101	Headlines	2026-10-12
x	weather:100	Weather
```

`s` starts a section. `p` is a page, a title and an optional date. `x` is a linked channel: `name:mpp`, or a channel's or page file's address. A title is cut at 120 characters. The file is at most 65,536 bytes and 1,000 lines, printable ASCII and tabs. `neottx contents FOLDER` writes it from a folder of page files.

A live channel has no `contents.txt`: its program gives an index instead ([section 15](#15-live-channels)).

## 12. Web addresses and the URL map

[DOC-1779](../PROTOCOL.html#DOC-1779) is the one written URL map, and `crates/neoteletext-web/src/map/conformance.tsv` is its test table. Every channel has the same map. `<channel>` is an origin and folder ending in `/`.

| Address | Opens |
|---|---|
| `<channel>` | The channel, arriving at its initial page |
| `<channel>302` | Page 302 |
| `<channel>302/0002` | Sub-page 0002 of page 302 |
| `<channel>302?name=value` | Page 302, with a query for the channel's program |
| `<channel>302/0002?name=value` | The sub-page, with a query |
| `<channel>contents` | The channel's contents |
| `<channel>wall` | The wall of pages, with nothing selected |

Rules a programmer needs:

- **Spelling.** Page digits become capitals, a final slash after a place goes, and `302.tti` becomes `302`, `302/0002.t42` becomes `302/0002`. Queries are not changed.
- **Refused:** a fragment on an `http` or `https` address, a place the map does not list (`30`, `G02`, `902`, `302/2`, `302/3F7F`), and a query after `contents` or `wall`.
- **A last segment** that is a page number, `contents` or `wall` belongs to the channel above it, so no channel can be a folder of those names.
- **The whole address** is at most 8,000 octets.
- **Local files** take a place after `#`: `file:///tmp/news.tti#200`. This is the one use of `#`.

**The query** goes with one selection. A program receives it in `selected`. A static channel ignores it.

## 13. neottx:// links

`neottx://` lets another program or a web page open a channel in the browser. It wraps a whole `http` or `https` address and adds nothing to it:

```text
neottx://https://app.neottx.com/demosite/
neottx://https://app.neottx.com/demosite/302/0002?a=1
```

The browser registers the scheme with the operating system, and opens such a link at once with no confirmation (DEC-1667). `neottx` registers nothing, but takes the same link as an input; a fragment on it is refused. The name is defined once, `neoteletext_core::consts::LINK_SCHEME`, and the owner expects it to change (DEC-1726). It is not a page's link: inside a page, use a plain address.

A channel's address asked for by a web browser answers a small page offering a `neottx://` link and a link to get NeoTeletext ([section 22](#22-other-additions)).

## 14. Links beyond Fastext

The TTI Link Extension declares links packets cannot carry. The lines are defined in [the TTI Link Extension](../PROTOCOL.html#DOC-1879), and this section teaches their use.

| Line | Meaning | Limit |
|---|---|---|
| `LN,key,target,label` | A coloured key or Index. `key` is `R`, `G`, `Y`, `C` or `I` | Four coloured, one Index. A fifth, or a repeat, makes the page's links invalid |
| `LK,mpp,target` | A page number the page shows. Typing it follows the link | 8 a page. Never to `web:` |
| `LT,row,column,length,target` | A run of text. Rows 1 to 23, within the row | 8 a page |

A target is one of:

| Form | Leads to |
|---|---|
| `mpp`, `mpp:ssss` | A page or sub-page of this channel |
| `name:mpp`, `name:mpp:ssss` | A page of a channel named in `services` |
| `https://...`, `http://...` | Another channel, or a page file of one |
| `web:https://...` | A web page, opened outside teletext after a confirmation |

Targets are printable ASCII with no spaces or commas, an address at most 8,000 bytes and 8,004 with `web:`. A label is at most 9 characters, 8 for a link leaving the service, and ignored for `I`.

```tti
PN,22000
PS,8000
OL,1,Headlines 101 Sport 140 TV 190
OL,2,Read the story
LN,R,101,Headlines
LN,G,140,Sport
LN,Y,weather:400,Weather
LN,C,190,TV guide
LN,I,100,
LK,190,tv:100
LT,2,0,14,300:0002
```

On a page with `LN` lines **the receiver draws row 24 itself**, and ignores any row 24 the page sends: four prompts of 10 columns, each a colour attribute and a label. `neottx check` warns about that as `hidden-content`, and warns when a linked number is not on the page (`page-number-not-shown`) or a page's only route to another service is its link (`no-other-route`). A `CK,considered,no-other-route` line marks one as considered.

When a page is turned into packets, X/27/0 carries the same-service links, and a row 24 is written, with links leaving the service in white with `»`. So a Level 1 television shows the prompts and follows what it can. `neottx text` shows that row.

In the browser:

- A link is drawn by the browser: a blue hairline under the run, over the page image. The page's own underline is not drawn, so an underline there always means a link.
- The trusted strip shows where a link leads. A click follows the link the viewer saw.
- A page of the channel opens at once, and another channel opens at once in the same tab (REQ-1670).
- A `web:` target goes to the system's web browser after a confirmation in the strip.
- A web link is followed by a click and not by a coloured key. The browser's own row 24 leaves such a key's prompt, and one naming a `services` channel, blank, since its decoder passes no service list (`native/decoder/src/engine/feed.rs`).
- **Only what a page declares is a link.** The browser used to find page numbers in text and no longer does, so a number you want clickable needs an `LT` line. A click on a declared link is the browser's and never reaches the channel.
- A hover over a link takes the look of [section 18](#18-controls-cells-a-page-answers-itself).

`LN` wins over `FL` when both are present. On a live channel these links travel as a LINKS record, type 9, straight after the sub-page's page frame, and a sub-page sent without one has none.

| | Key | Number | Text |
|---|---|---|---|
| TTI | `LN` | `LK` | `LT` |
| TypeScript | `screen.keyLink("red", "101", "Headlines")` | `screen.numberLink(0x190, "tv:100")` | `screen.textLink(2, 0, 14, "300:0002")` |
| Python | `screen.key_link("red", "101", "Headlines")` | `screen.number_link(0x190, "tv:100")` | `screen.text_link(2, 0, 14, "300:0002")` |

## 15. Live channels

A live channel is one whose `channel.ttx` has `push`. A program writes its pages, one instance serving every viewer. The server starts the program, or the program connects to a socket, and they talk in lines of JSON. [`servers.md`](servers.md) covers running it. A channel is listed in the server's channels file:

```json
{"channels":[
  {"folder":"home","name":"NeoTeletext","command":["node","src/main.ts"],"directory":"../my-channel"}
]}
```

The protocol is `neoteletext-app-server/docs/applications.md`, version 6, with the schema `protocol/schema-6.json`. Every line is checked against it and refused whole if wrong.

**A viewer's connection is one browser tab with one selection.** Selecting a page (sub-code 3F7F) brings its first sub-page in ascending sub-code order, which then is the selection. Selecting a sub-page brings that one. **Nothing rotates**: a sub-page changes only when the viewer selects another, or the program redirects them, or the program sends a change. Pages go one sub-page at a time, whole the first time and then as changed rows. The kits do all of this.

```ts
import { type Application, Colour, runChannel, Screen } from "neoteletext-server-ts-protocol";

const hello: Application = {
  pages: () => [{ page: 0x100, title: "Hello" }],
  start(context) {
    const screen = new Screen();
    screen.header("HELLO");
    screen.doubleHeight(2, 0, Colour.Yellow, "Hello, teletext");
    screen.fastext([0x101, null, null, null]);
    context.publish("channel", 0x100, screen);
  },
};

await runChannel([hello]);
```

```python
from neoteletext_app.app import App
from neoteletext_app.screen import Colour, Screen

class Hello(App):
    async def on_start(self):
        screen = Screen()
        screen.header("HELLO")
        screen.double_height(2, 0, Colour.YELLOW, "Hello, teletext")
        self.publish(0x100, screen)

Hello({0x100: "Hello"}).run()
```

| To | TypeScript | Python |
|---|---|---|
| Publish for everyone | `context.publish("channel", page, screen)` | `self.publish(page, screen)` |
| Publish for one viewer | `context.publish(session, page, screen)` | `self.publish(page, screen, owner=session)` |
| Publish TTI | `context.publishTti(owner, page, text)` | `screen.load_tti(text)`, then `publish` |
| Change one sub-page | `context.put(owner, page, [{ screen, subcode }])` | No call: publish the whole page, with `subcodes=[...]` to keep its sub-codes |
| Remove sub-pages | `context.remove(owner, page, [subcode])` | Publish the page without them |
| Move a viewer | `context.redirect(session, page, sub)`, or an address | `self.redirect(session, page, sub)` |
| Title a page | `context.title(page, title)` | `self.title(page, title)` |
| Set a cookie | `context.cookie(connection, name, value, options)` | `self.cookie(...)` |
| Send raw packets | `context.packets(audience, bytes)` | `self.packets(hearer, bytes)` |
| Log to the viewer's console | `context.authorLog(audience, "I", text)` | `self.author_log(hearer, "I", text)` |

An audience is `{ session }`, `{ page }` or `{ connections }`, and a hearer is `session_hears(session)` or `page_hears(page)`.

A page owned by a session is that viewer's alone. The channel's copy is shared, and `release` drops a viewer's own copy.

A selection ends in one of these ways. The kits answer a selection for a page they hold.

| Answer | Meaning |
|---|---|
| A page | One sub-page goes to the viewer |
| The message `denied`, status 403, 404, 429 or 503 | The selection ends at once with no page, and the connection stays. The receiver says so in its own words |
| The message `redirect` | The viewer moves, to a page, or to another channel after a one-second notice |
| Nothing for 5 seconds | The server sends DENIED 503 itself |

Every selection has an ending. A viewer's query reaches `request`, as `{ path, query, queryText, cookies }`, all untrusted. In Python that is `on_request`.

**What is not on a live channel:** public object pages and the MOT ([section 5.7](#57-objects)).

A live channel's index, given by the program, fills the receiver's list of pages, and each page's `subpages` list gives its sub-pages and their titles. `Application.pages()` declares what the index lists, and `Subpage.title` titles a sub-page, at most 40 characters.

## 16. The push WebSocket and the input protocol

[DOC-1781](../PROTOCOL.html#DOC-1781) is the whole upstream protocol. This section is what a page author should know. A kit does all of it.

**The connection.** A channel's WebSocket is always `<channel>push`: `wss` for `https`, `ws` for `http`. A receiver offers `Sec-WebSocket-Protocol: neottx.7`, sends no `Origin`, and a server refuses anything else (426 and 403). It is one socket a tab, with no compression. Close codes 4000 and 4001 mean stop; 4100 means try again.

**Downstream is teletext.** Binary messages are 42-byte packets. Everything beyond pages travels as records on data channel 12, carried in 4/31 packets (EN 300 708 clause 6.7.3.2):

| Type | Record | Carries |
|---|---|---|
| 1, 2, 3 | OBJECT, DATA, CONTROL | Sound |
| 4 | Cursor | The input cursor, and how much input was acted on |
| 5 | WELCOME | The answer to HELLO |
| 6 | Index | The channel's magazines and pages |
| 7 | LOG | A line for the developer console |
| 8 | SET_COOKIE | One `Set-Cookie` value |
| 9 | LINKS | A sub-page's Link Extension links |
| 10 | SUBPAGES | A page's list of sub-pages |
| 11 | REDIRECT | Moves a viewer |
| 12 | DENIED | A selection refused |

**Upstream is events.** Any byte but `0xFF` begins raw UTF-8 text. An event is `0xFF`, a type byte, and fields. Every key, click and move goes to the channel; **there are no modes to ask for** ([DOC-1922](../PROTOCOL.html#DOC-1922)), and the channel ignores what it does not use.

| Type | Event | When |
|---|---|---|
| `0x01` | KEY | Every press, repeat and release |
| `0x02` | MOUSE | Press, release, move at most 60 a second, and gone |
| `0x03` | WHEEL | Over the page, in 1/120ths of a line |
| `0x04` | PASTE | The whole paste as one event, at most 4,000 bytes |
| `0x05`, `0x06` | FOCUS_IN, FOCUS_OUT | Keys start and stop going |
| `0x07` | RESIZE | Always 40 by 25 cells; the drawn size or 0 |
| `0x08` | COMPOSE | An input method's preedit |
| `0x09` | HELLO | First, once: version 7 and capabilities |
| `0x40` | SELECT | The tab's selection: `302`, `302/0002`, a query, or empty |
| `0x43` | HOVER | The pointer enters or leaves a control |
| `0x44` | TOUCH | Contacts after the first |
| `0x45` | RESUME | Continues a lost session |

Each event but the focus events, HELLO, RESIZE, SELECT and RESUME carries a stamp: the page and sub-code on screen when it happened. An event stamped with anything but the selection is dropped, except a release.

| Input | Bytes |
|---|---|
| `a` pressed on page 100 | `FF 01 80 02 00 10 61 01 61` |
| Enter pressed | `FF 01 80 02 00 04 02` |
| Red (Fastext) pressed | `FF 01 80 02 00 04 5C` |
| Click at column 10, row 5 | `FF 02 80 02 00 00 00 0A 05` |
| `é` from an input method | `C3 A9` |
| Page 302 selected | `FF 40 03 33 30 32` |

**What a program hears.** The server turns these into typed `input` messages.

| Event | TypeScript `Input` | Python `Event` |
|---|---|---|
| Key | `kind: "key"`, `action`, `key`, `text`, `base`, `lost`. `pressed(input, Key.Enter)` | `event.pressed_key("Enter")` |
| Typing | `typed(input)`, `character(input)` | `event.typed`, `event.character` |
| Click | `clicked(input)`, and `kind: "mouse"` with `column`, `row` | `event.clicked` |
| Move | `kind: "mouse"`, `action: "move"`, `buttons` | |
| Wheel | `kind: "wheel"`, `dx`, `dy` | |
| Hover | `kind: "hover"`, `action`, `column`, `row` | `event.entered` |
| Paste | `kind: "paste"`, `text`. Data, never keystrokes | |
| Focus | `kind: "focus"`, `kind: "blur"` | |

Key names are W3C `KeyboardEvent.key` names. Text is Unicode after the viewer's layout, in logical order and Normalization Form C. **A receiver never translates text into a teletext set**: the channel maps it onto the page's sets and decides what to show for a character they lack. `key` follows the layout and `base` the physical position, so a game's movement keys use `base`.

A key held when the viewer leaves is released by the server and marked `lost`, so a game can tell "let go" from "left". A lost release is no click.

**When input goes.** In the browser, keys go to a channel only when `push.input` is true, the session is welcomed, the tab is in front, the window has focus and the viewer is not editing the address. The strip says "Keys go to *host*". The browser's own modifier keeps its keys, Command on macOS and Control-Shift elsewhere. Links stay the browser's on every page. Page selection on a channel that takes input is the channel's: videotex's `*nnn#`, `#` and `*#` are a convention it may implement, and the kits' navigation handles digits and coloured keys for pages that do not use them.

`neottx view` is a terminal receiver of the same protocol. Control-] leaves the channel and returns.

## 17. Typing and forms

**There are no forms in the engine.** The TTI Form Extension was withdrawn on 27 October 2026 (DEC-650), and nothing in a page declares a field. A channel that wants a form draws it and takes the viewer's keys. So a form needs a live channel that takes input: `"push": { "input": true }`.

A field works like this:

1. The page draws the field with ordinary characters.
2. The page places the cursor: `CU,row,column,0,flags` in TTI, `screen.cursor(row, column, CursorFlag.Block)` in TypeScript, `screen.cursor(row, column, block=True)` in Python.
3. The viewer types. Each key goes to the channel at once.
4. The program draws what was typed, on the page, and publishes the changed rows.

**The receiver draws nothing of what is typed.** Provisional echo was withdrawn (engine decision E.134). So a program answers every key by publishing the page.

The cursor is drawn by the receiver, in a style no page can draw: an amber bar, or with BLOCK an amber outline. It shows only on the page it names, only while keys go to its channel. A cursor record's row is 1 to 23, or 255 for none; its column is 0 to 39. Flag value 4 is BLOCK, and 1 and 2 are reserved.

```tti
PN,23000
PS,8000
OL,1,Name: ......
CU,1,6,0,4
```

The third field of `CU` once held the echo width. It is kept in place and written 0. The acknowledgement field is optional and a program never sets it by hand: a channel's server sends the cursor as a record, with the input count.

```ts
function input(session, page, input, context) {
  const text = typed(input);
  if (text !== undefined) {
    name += text;
    redraw(session, context);      // screen.text(...), screen.cursor(...), context.publish(session, ...)
    return true;
  }
  return false;
}
```

```python
async def on_input(self, session, page, event):
    if event.typed:
        self.name += event.typed
        self.redraw(session)        # screen.text(...), screen.cursor(...), self.publish(..., owner=session)
        return True
    return False
```

Answer true for what the page took. Anything else the kit uses for page selection and following links.

The UI library has this done: `TextField`, `SegmentField`, `MultiTapField`, `Autocomplete`, `Checkbox`, `RadioGroup`, `Switch`, `Slider`, `NumberInput`, `Select`, `Button` and more, in its `docs/components/input.md`.

A page still carrying the withdrawn form lines shows its rows alone.

## 18. Controls: cells a page answers itself

Column mode `00101`, reserved in Table 29, declares a run of cells as a control, a button or a row of a list. It draws nothing, and every other decoder skips it, so a page with controls looks the same everywhere.

| Field | Meaning |
|---|---|
| Address | The first column, 0 to 39 |
| Mode | `00101` |
| Data D5 to D0 | The width, 1 to 40, not past column 39 |
| Data D6 | Joined: continues the control on the row above, at the same column and width |

The row is the active row. Rules: rows 1 to 23, local data only, at most 32 a page, no overlaps. A taller control repeats its triplet on each row with D6 set. A triplet breaking a rule is dropped and reported.

| Triplet | Value | Packed | On air |
|---|---|---|---|
| Set Active Position, row 20 | `0x0013C` | <code>&#124;D@</code> | `60 93 80` |
| Control, column 1, width 9 | `0x04941` | `AeD` | `8F 94 89` |

```tti
PN,24000
PS,8000
OL,20, Yes       No
OL,26,@|D@AeDKeD␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C␡␡C
```

A control is only where a click lands. The click still goes to the channel as MOUSE at its cell. What the control adds is in the receiver, while keys go to the channel:

- The pointer is a hand over it.
- **Hover:** each colour of its cells becomes the same entry of the adjacent CLUT, 0 with 1 and 2 with 3. With Table 30's colours, hover is CLUT 1's half intensity. A page chooses its own hover colours by defining CLUTs 2 and 3 in X/28/0 and drawing from them with Re-mapping 6.
- **Pressed:** the hover colours, swapped.

The receiver draws both at once and sends nothing, so a page lights up under the pointer without a copy for each viewer. A finger gets no hover look. Moving onto a control sends HOVER, `kind: "hover"`.

Rust: `triplets.control(column, width, joined)`. TypeScript's `Screen` has no call: the UI library writes these as `OL,26` lines (`src/core/controls.ts`), and every button in it declares one.

The pointer's units are in [DOC-1946](../PROTOCOL.html#DOC-1946): `col` and `row` the cell, `px` and `py` the dot of a 480 by 500 image. Test a click by its cell.

## 19. Audio

A page can make sound, carried as records on data channel 12. The profile is `docs/spec/design/audio.md` in the engine, and [DOC-1785](../PROTOCOL.html#DOC-1785).

| | |
|---|---|
| Stored sounds | An object, sent once and played by commands. At most two minutes |
| Live sounds | Blocks sent as they play |
| Channels | Four, 0 to 3; the latest command on a channel wins |
| A page's sound | Plays while the page is open, when the command names a page |
| Formats | Opus, PCM16 and IMA ADPCM, at 8, 11.025, 16, 22.05, 24, 32, 44.1 and 48 kHz |

**Desktop and phone receivers play Opus alone.** A program encodes it and the server carries it unchanged: constant-rate 16 kbit/s, 20 ms packets. PCM, which the server encodes as IMA ADPCM, is for microcontrollers.

| `kind` | Fields |
|---|---|
| `opus` | `handle`, `generation`, `packet_bytes`, `samples`, `packets` |
| `opus_live`, `opus_packets` | A live Opus sound and its packets |
| `object`, `live`, `blocks` | PCM, stored or live |
| `play` | `channel`, `handle`, `generation`, `gain` 0 to 100, `fade_ms`, `loop`, `after`, `duck` 0 to 6, `page` |
| `stop`, `gain` | `channel`, `fade_ms` |

```ts
const opus = ffmpegOpus().sound(samples, 16000);   // Int16Array, needs ffmpeg with libopus
context.sound({ session }, { opus: { handle: 1, generation: 0, ...opus } });
context.sound({ session }, { play: { channel: 0, handle: 1, generation: 0, gain: 80 } });
```

Python's `sound_object`, `play` and `stop` send PCM, and `neoteletext_app.sound` makes tones, noise and chimes, which reach a microcontroller and not a desktop receiver. The UI library has `sound`, `tone`, streams and an `AudioPlayer` (`docs/audio.md`).

For files, `neottx sound --page 100 chime.wav chime.t42` writes a sound as packets with the command that plays it. Append it to a channel's T42. `--codec pcm`, `--loop`, `--repeat N` and `--live` set the rest. `neottx` itself plays no sound.

## 20. Pictures

A picture is a page of mosaics. Nothing about it is special to a receiver, and there are no bitmaps.

```sh
uv run scripts/image-to-teletext.py picture.png page.tti --level 3.5
```

`scripts/image-to-teletext.py`, in the engine, reduces a picture to 80 by 75 sixels. At Levels 1 and 1.5 it uses the eight colours with spacing attributes, and `--hold-mosaics` uses Hold Mosaics. At Levels 2.5 and 3.5 it redefines the CLUTs and changes colours with non-spacing attributes, so every column is picture. By default it carries the row data in Active objects on a POP, page `1A0`, linked by X/27/4. `--no-objects` keeps it in the page's own X/26, at most 208 triplets.

| Use | Works in |
|---|---|
| `--no-objects`, or Levels 1 and 1.5 | The browser and `neottx`, on any channel |
| Default, with objects on a POP | The browser and an objects build of `neottx`, for a file or static channel holding the POP. Not on a live channel |

To show one from a program: `context.publishTti(owner, page, text)`, or `screen.load_tti(text, first_row=..., last_row=...)` in Python. The UI library has `Picture`. Drawn pictures of your own go through `Sixels` ([section 3.5](#35-mosaics-contiguous-and-separated)), or `Mosaic` and `Icon` in the UI library.

## 21. The phone keyboard and QR codes

**A QR code on a page.** `neottx qr` writes text as a QR code in a page's mosaics.

```sh
neottx qr "https://example.org/story" --page 150 --row 2 qr.tti
```

Any phone camera reads it. `Screen.load_tti` in Python, and `Picture` or `QrPanel` in the UI library, place it in a page. This is the teletext way to give a web address, since a Level 1 set can follow no link.

**A phone as a keyboard.** A phone scans a QR code and becomes a keyboard, through qrkeyboard's relay and protocol 3 ([DOC-2029](../PROTOCOL.html#DOC-2029)).

| | |
|---|---|
| In the browser | From its panel. The phone's keys go to the page, or choose pages, as the viewer's own |
| On any channel from a terminal | `neottx keyboard wss://example.org/push` shows a QR and sends what is typed on the phone to the push WebSocket. `--pin` pairs with a PIN, `--qr-page` and `--qr-output` write the QR as a page |

A phone's text goes as raw text, and its named keys as their functional codes, with colour keys 92 to 97. It carries no modifiers. **A page needs nothing to take a phone's keys.** They arrive as `typed(input)` as any others. One phone at a time; whoever scans the code has the keyboard.

## 22. Other additions

**Sub-pages at the standard's maximum.** 8,190 a page, each addressable, with lists sent only when needed. A channel's lists are SUBPAGES records on a live channel, and `NNN/P.sub` with `NNN/SSSS.t42` on a static one.

**Page titles.** A sub-page's title is what its publisher gave it: `DE` on the first sub-page, or a program's `title`. Failing that, it is row 1's alphanumeric text, trimmed to 40 characters. Row 0 is never used.

**Author log lines.** `LG,level,text` in TTI, `I`, `W` or `E`, reaches the developer console, and `neottx -v` prints it. A program uses `authorLog`, up to 200 bytes.

**Cookies.** RFC 6265bis, scoped to the channel's folder, with names starting `_` kept for the server. A program sees the cookies the connection opened with, and sets them with `cookie`. How a viewer logs in is not designed.

**Redirects.** A program's `redirect`, a REDIRECT record, is the only thing that moves a viewer. A redirect to another channel shows a notice for one second. The viewer's own choice overrides it.

**A small page for web visitors.** A channel's address asked for by a web browser or search engine answers 200: a small page naming the channel, with a `neottx://` link and a link to get NeoTeletext. It runs no script.

**Public pages.** A page is public on the web only when its program says so. The server asks with `describe`, carrying the page number and nothing else, and a kit says no unless told otherwise. A public page shows its title, a picture drawn by the server and its text. Everything in it is readable by anyone. TypeScript: `describe(page)` on an `Application`. Python: `describe(self, page)`. The Cloudflare host asks nothing and answers every page as not public. `neottx html`, which writes the same for a static channel, is on the engine's branch `req-1728-engine` and not in the build this guide was checked against.

**The wall and contents.** The browser's overview of a channel's pages, drawn from its page cache, and its contents view. A channel gives them through `contents.txt` or its index.

**Reveal, hold, mix and zoom.** The viewer's own, in the browser and `neottx view`. Mix makes backgrounds transparent, as text over a picture.

**`neottx`'s other tools.** `convert` between TTI and T42, `list`, `service-info`, `services`, `slice`, `view`, `probe` and `check`. `docs/user-guide.md` in the engine lists them all.

**A channel's offline behaviour.** A page already received stays viewable when the network goes, and shows `?` in the status area once it is stale. That is the receiver's, with nothing for a page to do.

---

## Appendix: where the documents and the code differ

These are the differences found while writing this guide. The code won in each case, and the guide says what the code does.

| Subject | A document says | The code does |
|---|---|---|
| `write-text --help` | Lists 18 sets | Takes 46 |
| `docs/spec/design/capabilities.md` | Calls the 32 colours "switched off in the profile" | True of `modern-classic`, but the browser adds them back |
| The browser's `functionality-gaps.md` | As of 23 October 2026; several rows have since changed | Read it as history |
