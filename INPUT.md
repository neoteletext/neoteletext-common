# The neoteletext input system

| | |
|---|---|
| **Status** | Proposed on 21 October 2026, for the owner to adopt. The owner agreed on 21 October that losing focus releases held input at the channel (section 13 item 11), that everything the channel says about input travels as teletext records (item 9), and that the mouse goes to a channel only when it asks (item 14), a page asking for itself (section 6.4). |
| **Merges** | The input system built on 20 October 2026 (the engine's decisions E.90 to E.94 and E.97, the browser's decisions 44 to 46), and the owner's *Input Event Protocol v1* of 20 October 2026. Section 13 records what was taken from each and why. |
| **Protocol** | Version 2. Version 1, the fixed 14-byte key record, is retired (section 14). |
| **Words** | MUST, SHOULD and MAY as in RFC 2119. A *receiver* is anything that shows a channel and sends input: NeoTeletext, `neottx view`, `neottx keyboard`, a microcontroller receiver. A *channel* (or host) is the server that takes the input. |

---

## 1. What it is for

A teletext channel that takes input is a host, and the receiver is its terminal. The viewer types; each key goes to the channel at once; the channel decides what it means and answers by pushing the rows that changed, and, if it likes, a cursor. Nothing ever executes in the receiver: a game, a form, a chat and a shell are the same to it, a terminal on a line to a host.

**In scope:** keys, committed text, paste, input-method composition, mouse buttons, wheel and motion over the page, focus, the page the viewer opened, the cursor and echo shown while typing, capability negotiation, the phone keyboard as a source of keys, and the security and privacy of all of it.

**Out of scope:** forms (they are page files and HTTP submissions, the engine's area FRM), fetching and push themselves (area WEB), and what a channel does with a key.

## 2. Principles

1. **A terminal, not a browser.** The receiver sends what the viewer did; the channel decides what it means. No page can run code, and no input path can make the receiver fetch, navigate away from the channel, or do anything but draw.
2. **Each event goes at once.** One write per event, no batching (except merged mouse motion and wheel, section 8), `TCP_NODELAY`, nothing waits on a timer (decision E.97).
3. **As few bytes as possible.** Typed text is raw UTF-8, one byte per ASCII character; the commonest events are four bytes or fewer.
4. **No guessing.** An event starts with `0xFF`, which never occurs in UTF-8, so the start of every event is known with no timeout, and its length is known from its type.
5. **Bounded everywhere.** Every length has a maximum; every reader refuses whole what breaks a bound; every reader of outside input is fuzzed.
6. **What comes back is teletext.** The channel answers in pages and packets, and the little it says about input (the cursor, the acknowledgement, the negotiation) travels as records of the audio profile on teletext data channel 12, so a file, a broadcast and a microcontroller receiver carry it as they carry any packet.
7. **Keys go only where the viewer sat down,** and the receiver's own controls always show where that is.
8. **A phone is a keyboard and no more.**

## 3. Architecture

### 3.1 The pieces

| Piece | Repository | What it does |
|---|---|---|
| `neoteletext-input` | engine | The protocol: an encoder for receivers, a streaming decoder for channels, the key tables, the cursor and control records, the rate limiter. `no_std`, no allocation, no floating point, so a microcontroller receiver or channel uses it as the desktop does. |
| `neoteletext-web` | engine | The push WebSocket that carries input (`Input::Send`), the descriptor's `push.input`, the heartbeat. |
| `neoteletext-audio` | engine | The record frame and data-channel-12 carriage the cursor and control records share with sounds; the audio receiver steps over them. |
| `neoteletext-formats` | engine | The TTI `CU` line (a cursor in a page file). |
| `neoteletext-qrkeyboard` | engine | The screen's side of qrkeyboard's protocol 3: a phone as a keyboard. |
| `neottx view`, `neottx keyboard`, `neottx qr` | engine | A terminal receiver; a bridge from a phone to a channel; a QR code in a page. |
| NeoTeletext | browser | A windowed receiver of five processes (section 3.3). |
| `neoteletext-site terminal` | browser | The reference channel: echo, piano, game, podcast and forms over input. |

### 3.2 A key, end to end

```
viewer ─ key ─▶ receiver: is this key the channel's? ─▶ encode ─▶ push WebSocket ─▶ channel
                                                                              │
viewer ◀─ draw ◀─ receiver: render rows; check cursor ◀─ pushed packets / TTI ◀┘
```

The receiver decides only whether a key goes; the channel decides only what it means. The answer is ordinary teletext: rows pushed as packets or a TTI page, and, optionally, a cursor record.

### 3.3 In NeoTeletext

| Step | Process | Does |
|---|---|---|
| 1 | Interface | Takes the window's key, mouse, wheel, paste and composition events. Sends an *intent* to the trusted core only when the active tab's open page takes input and the browser's own modifier (Command on macOS, Control-Shift elsewhere) is not held. Draws the cursor and echo the trusted core allows. |
| 2 | Trusted core | Checks every condition again (requirement REQ-INT-130), applies the rate limit, tracks held keys and the input count, **encodes the protocol**, and alone sends HELLO, RESIZE, PAGE, FOCUS and the releases. Measures the round trip from acknowledgements. |
| 3 | Fetcher | Writes each message it is given to the channel's push WebSocket at once. It takes nothing else and opens nothing (requirement REQ-INT-133). |
| 4 | Decoder | Finds cursor and control records in pushed packets and `CU` lines, untrusted, and passes them on. |
| 5 | Trusted core | Checks each cursor and control record; applies WELCOME and the mode stack; passes the interface only what it may draw. |

The interface never encodes the wire format: it sends intents, so a compromised interface can at worst type into the one channel the trusted core already lets it type into (the browser's open decision 3). The phone keyboard is a sixth process, `neoteletext-keyboard`, which alone holds the pairing secret; its keys go to the trusted core and on to the interface, which treats them as its own (section 10).

### 3.4 In `neottx`

`neottx view` is a terminal receiver: crossterm's key, paste, focus and resize events become the protocol's events in the fetcher process, as in the browser. Control-] leaves and returns to the channel, as telnet's escape character does; it is the one key that never goes. `neottx keyboard` bridges a phone to a channel's push WebSocket: a channel gets a phone keyboard without implementing qrkeyboard.

### 3.5 Microcontroller receivers and channels

Everything in the protocol is fixed-size or length-prefixed and decodable byte by byte, so a microcontroller encodes events into a small buffer and a channel decodes them with a streaming parser of a few dozen bytes of state. The WebSocket, TLS and the phone keyboard's cryptography stay out of microcontroller crates (decision E.38); a microcontroller receiver supplies its transport, as for any push.

### 3.6 Trust boundaries

| Boundary | Crossing it | Checked by |
|---|---|---|
| Viewer → interface | Window events | The interface's routing, then the trusted core again |
| Interface → trusted core | Intents | The trusted core: every condition of REQ-INT-130, every field's bounds |
| Trusted core → fetcher | Encoded messages | The fetcher's reader: the kinds it takes, the message bound |
| Fetcher → channel | The push WebSocket | — (the channel is outside) |
| Channel → decoder | Pages, packets, records | The decoder's readers, fuzzed |
| Decoder → trusted core | Cursor and control records | The trusted core: every field |
| Trusted core → interface | What to draw | The interface again |
| Phone → keyboard process → trusted core | Keys and text | The keyboard process (bounds, no modifiers), then the trusted core |

## 4. Declaring input

A channel takes input when its descriptor says so inside its push object:

```json
"push": { "address": "wss://news.example/push", "method": "websocket", "input": true }
```

- `input` MUST be a JSON boolean; it defaults to false. It is refused with `"method": "sse"`: input goes back only on the push WebSocket.
- The push address MUST be on the channel's own origin, and a descriptor fetched over `https` may not name a `ws://` push address.
- Plain `ws://` is allowed, and the receiver says "Not secure" wherever it says where keys go.
- A page cannot declare input; only the channel's descriptor can.
- The protocol version is not in the descriptor: it is negotiated on the socket (section 6).

## 5. The protocol: receiver to channel

### 5.1 Transport and framing

- **Transport:** the channel's push WebSocket. Each **binary** message the receiver sends is a piece of one ordered input stream, the concatenation of all binary messages on that connection. The only other message a receiver sends is the push subscription (text).
- **Whole events per message.** A message MUST hold whole events and whole UTF-8 characters, so a channel can parse each message alone; text may be split between messages anywhere between characters.
- **At most `MAX_MESSAGE` (4096) bytes a message.**
- The stream is defined so it also works over any reliable ordered byte stream (a microcontroller's serial line, a TCP socket); over TCP, `TCP_NODELAY` is set.

### 5.2 Encoding primitives

| Name | Encoding |
|---|---|
| `u8` | One byte |
| `uv` | Unsigned varint: 7 bits a byte, least significant group first, the high bit set on every byte but the last. 0 to 127 take one byte; at most 5 bytes; a longer or non-minimal encoding is a protocol error. |
| `sv` | Signed varint: zigzag (`(n << 1) ^ (n >> 31)`), then `uv`. −64 to 63 take one byte. |
| `str` | `uv` byte length, then that many bytes of UTF-8, within the field's own maximum. |

Fields marked `?` are present only when the matching flag bit is set.

### 5.3 Text

Any byte other than `0xFF` begins raw UTF-8 text.

- A key press whose result, after the layout applies Shift, AltGr or Caps Lock, is printable text is sent as that text: `a`, `A`, `@` by AltGr, `é`.
- Committed text from an input method, or from a phone, is sent as text.
- Text MUST NOT contain control characters (U+0000 to U+001F, U+007F to U+009F). Enter, Tab, Backspace, Escape and every Control, Alt, Super, Hyper or Meta combination are key events.
- Bytes `0xC0`, `0xC1` and `0xF5` to `0xFE` outside an event, and malformed UTF-8, are protocol errors.
- In the ALL_KEYS mode no raw text is sent; every key is a KEY event carrying its text.

### 5.4 Events

An event is `0xFF`, a type byte, then its fields.

| Type range | Layout |
|---|---|
| `0x01`–`0x3F` | Core events, fixed layout. An unknown core type is a protocol error. |
| `0x40`–`0x7F` | Extensions: `uv` length, then the payload. A receiver of the stream skips one it does not know. |
| `0x00`, `0x80`–`0xFF` | Reserved: a protocol error. |

| Type | Name | Fields | Always sent, or in which mode |
|---|---|---|---|
| `0x01` | KEY | section 5.5 | press of a non-text key always; repeat and release in KEY_RELEASE |
| `0x02` | MOUSE | `flags` u8, `button` u8, `col` uv, `row` uv, `px`? uv, `py`? uv, `mods`? u8 | MOUSE_BUTTONS, MOUSE_DRAG, MOUSE_ALL |
| `0x03` | WHEEL | `flags` u8, `dx` sv, `dy` sv, `col` uv, `row` uv, `px`? uv, `py`? uv, `mods`? u8 | always, while the pointer is over the page (section 6.5) |
| `0x04` | PASTE | `str`, at most `MAX_PASTE` (4000) bytes | always |
| `0x05` | FOCUS_IN | none | always |
| `0x06` | FOCUS_OUT | none | always |
| `0x07` | RESIZE | `cols` uv, `rows` uv, `pw` uv, `ph` uv | always |
| `0x08` | COMPOSE | `cursor` uv, `str` at most `MAX_COMPOSE` (256) bytes; an empty string ends composition | COMPOSE |
| `0x09` | HELLO | `version` uv, `caps` uv, `agent`? str (at most 64 bytes) | first, once |
| `0x0A` | PAGE | `page` uv: `0x100` to `0x8FF` in teletext's hexadecimal page form, or 0 for none | when the receiver has the PAGE capability |

**MOUSE and WHEEL.**
- `flags` bits 0–1: MOUSE action, 0 press, 1 release, 2 move (unused in WHEEL); bit 2: `px`, `py` present; bit 3: `mods` present.
- `button`: on press and release, 0 left, 1 middle, 2 right, 3 back, 4 forward, 5 and up others; on move, a bit mask of the buttons held.
- `col`, `row`: the character cell, from the top left of the page: columns 0 to 39 (to 71 with side panels), rows 0 to 24. `px`, `py`: pixels of the page image from the same origin.
- `dx`, `dy`: scroll in 1/120ths of a line, positive right and down.

**PASTE** is the whole paste as one event. It may contain control characters: the channel treats it as data, never as keystrokes. A paste longer than `MAX_PASTE` is cut at a character boundary.

**COMPOSE**: `cursor` is a code-point offset into the preedit string.

**RESIZE** gives the page's text area in cells and the page image in pixels as the receiver draws it: a teletext page is 40 by 25 cells (72 with both side panels), so RESIZE changes only when the side panels or the drawn size do. Pixels are 0 when unknown.

**HELLO**'s `agent` is the receiver's user agent string, as the engine's REQ-WEB-031 defines it (`NeoTeletext/0.1 (macOS)`, or `product/version (platform) neoteletext/version` for another program on the engine). It is present when `caps` has the AGENT bit (section 6.2), and is sent only over a transport without HTTP, a serial line for instance: over the push WebSocket the channel already has it from the upgrade's `User-Agent` header, so it is not sent twice.

**PAGE** says which page the viewer has open, so the channel knows what to push: sent after RESIZE at the start of a session and whenever the open page changes while keys go to the channel, and with 0 when the viewer leaves the channel's pages.

### 5.5 KEY

`flags` u8, `key` uv, `mods`? u8, `text`? str (at most `MAX_KEY_TEXT`, 32 bytes), `base`? uv

| `flags` bit | Meaning |
|---|---|
| 0–1 | Action: 0 press, 1 repeat, 2 release |
| 2 | F: `key` is a functional code (section 5.6), not a code point |
| 3 | M: `mods` present (omitted when 0) |
| 4 | T: `text` present (ALL_KEYS only) |
| 5 | B: `base` present (BASE_KEY only, when it differs from `key`) |
| 6–7 | Reserved: a protocol error when set |

- **`key`**: for a character key, the Unicode code point of the key without Shift (Control-Shift-A sends `a` with Shift and Control); otherwise a functional code.
- **`mods`**: 1 Shift, 2 Alt (Option on macOS), 4 Control, 8 Super (Command, Windows), 16 Hyper, 32 Meta, 64 Caps Lock, 128 Num Lock, as the Kitty keyboard protocol.
- **`text`**: the text the press produced, if any.
- **`base`**: the code point the same physical key has in a United States layout, so a channel's shortcuts work on any layout.

### 5.6 Functional codes

Every non-character key has one code, which never changes: new keys are only ever added. Codes 1 to 127 take one byte.

| Code | Key | Code | Key |
|---|---|---|---|
| 1–4 | Escape, Enter, Tab, Backspace | 60–69 | Keypad 0–9 |
| 5–6 | Insert, Delete | 70–76 | Keypad . / * − + Enter = |
| 7–10 | Left, Right, Up, Down | 80–85 | Left Shift, Control, Alt, Super, Hyper, Meta |
| 11–14 | Page Up, Page Down, Home, End | 86–91 | Right Shift, Control, Alt, Super, Hyper, Meta |
| 15–20 | Caps Lock, Scroll Lock, Num Lock, Print Screen, Pause, Menu | 92–97 | Red, Green, Yellow, Blue, Grey, Brown (`ColorF0Red` to `ColorF5Brown`: Fastext and remote colour keys) |
| 21–55 | F1–F35 | 98–107 | Teletext, Channel Up, Channel Down, Exit, Info, Guide, Back, Home (browser), Volume Up, Volume Down |
| 56–59 | Reserved | 108–127 | Reserved |

Codes from 128 are the W3C UI Events `KeyboardEvent.key` names not given a code above, in the order of the engine's pinned table (`neoteletext-input`'s `KEY_NAMES`): code 128 plus the name's place among those remaining. A receiver that cannot name a key sends the code of `Unidentified`.

### 5.7 International keyboards

The protocol carries what the viewer typed, in whatever language and on whatever layout, and leaves its meaning to the channel. The rules for every layout, script and input method:

1. **Text is Unicode, after the layout.** A key's result is sent as the characters the operating system's layout produced: `й` on a Russian layout, `ש` on a Hebrew one, `ß` or `@` on a German one, `ç` on a French one. The receiver never translates text into a teletext character set; the channel maps it onto the sets of the page it draws, and decides what to show for a character none of them has (section 9.5).
2. **Logical order.** Text goes in the order it was typed, which for Arabic, Hebrew and other right-to-left scripts is logical order, never the visual order a page may be drawn in.
3. **Normalized.** Text is sent in Unicode Normalization Form C, so `é` typed on any layout or input method arrives as U+00E9, and a channel compares what it receives without normalizing it again.
4. **Dead keys.** A dead key (an accent pressed before its letter) sends no text: in ALL_KEYS it sends KEY with the functional code of `Dead`, and `base`; the key after it sends the composed character as text (`´` then `e` sends `é`), or, when the two do not compose, both characters, as the layout gives them.
5. **AltGr is a level shift, not a modifier.** A character typed with AltGr (the right Alt key of European layouts, `AltGraph`) is sent as text with no modifiers. A receiver on a system that reports AltGr as Control and Alt held together (Windows) MUST NOT report it so: when a key with Control and Alt both held produces printable text, it is text. AltGr itself, in ALL_KEYS or KEY_RELEASE, is the key `AltGraph`.
6. **Input methods.** Chinese, Japanese, Korean and other input methods compose in the receiver: their preedit goes as COMPOSE in that mode, and what they commit as text. Their own keys (`KanaMode`, `HangulMode`, `HanjaMode`, `Convert`, `NonConvert` and the rest of the W3C names) have functional codes from 128 and go as KEY when the receiver passes them on.
7. **`key` follows the layout; `base` follows the position.** A character key's `key` is the unshifted character of the active layout (`я`, `ф`, `a`); `base`, in BASE_KEY, is the character the same physical key has on a United States layout (`z`, `a`, `q` on AZERTY's `a`). A channel binds a letter by `key` and a position (a game's movement keys) by `base`, so both work on any layout, including after the viewer switches layout.
8. **Digits.** The keypad's keys are their functional codes in ALL_KEYS, and their characters as text otherwise. A layout that types native digits (`٣`, `३`) sends those characters; a channel that selects pages by number (section 9.4) SHOULD take the decimal digits of any script, Unicode's `Nd` characters, as the digits 0 to 9.
9. **Lock states and layout changes** send nothing of their own beyond the lock bits in `mods`: the protocol has no event for the layout, and a channel learns of a change only from what is typed, so the viewer's choice of language is never announced.
10. **Phones.** A phone keyboard's text, in any language its keyboard offers, is text under the same rules.

### 5.8 Size

| Input | Bytes | Size |
|---|---|---|
| `a` | `61` | 1 |
| `é` | `C3 A9` | 2 |
| Focus lost | `FF 06` | 2 |
| Enter | `FF 01 04 02` | 4 |
| Up | `FF 01 04 09` | 4 |
| Red (Fastext) | `FF 01 04 5C` | 4 |
| Control-C | `FF 01 08 63 04` | 5 |
| Page 100 opened | `FF 0A 80 02` | 4 |
| Click at column 10, row 5 | `FF 02 00 00 0A 05` | 6 |
| Wheel one line down at column 10, row 5 | `FF 03 00 00 F0 01 0A 05` | 8 |

The version-1 key record took 14 bytes for every key.

## 6. Negotiation and modes

### 6.1 The session

1. When the push WebSocket of a channel that declares input opens, the receiver sends HELLO with version 2 and the capabilities it has.
2. The channel answers with WELCOME (section 7.2): the version it speaks and the subset of the capabilities it will use. A channel that cannot speak the version closes the connection.
3. Then the receiver sends RESIZE, FOCUS_IN or FOCUS_OUT, and PAGE if it has that capability; and from then on the viewer's input.
4. The receiver sends no input before WELCOME. A channel that has not answered within `WELCOME_TIMEOUT` (10 s) is taken not to take input, and the receiver says so.
5. **A reconnection is a new session:** HELLO again, the mode stack empty, nothing held, the input count from zero. The channel pushes the open page again when it receives PAGE.

### 6.2 Capabilities

`caps` is a bit set. Bits 0 to 15 are mode bits, with the values of the mode table below (bits 8 to 15 reserved for future modes). Bits 16 and up are features that are not modes:

| Value | Capability | Meaning |
|---|---|---|
| 65 536 | PAGE | The receiver shows teletext pages and sends PAGE. |
| 131 072 | CURSOR | The receiver draws the channel's cursor record. |
| 262 144 | ECHO | The receiver draws provisional echo while the channel acknowledges (section 7.1). |
| 524 288 | AGENT | HELLO carries the receiver's user agent string (section 5.4); in HELLO only, never in WELCOME. |

A sender uses a new flag bit, field, core type or extension type only when both sides set its capability bit in HELLO and WELCOME. A receiver of the stream that sees an unknown flag bit set treats it as a protocol error.

### 6.3 Modes

Modes form a stack, so a page or program can restore what was on before it. The receiver uses the top entry; an empty stack means 0. The receiver keeps at least 16 entries and drops the oldest beyond that.

| Bit | Mode | Effect |
|---|---|---|
| 1 | ALL_KEYS | Every key as KEY with `text`; no raw text |
| 2 | KEY_RELEASE | Repeat and release actions too |
| 4 | BASE_KEY | `base` when it differs from `key` |
| 8 | MOUSE_BUTTONS | MOUSE press and release |
| 16 | MOUSE_DRAG | MOUSE_BUTTONS, and moves while a button is held |
| 32 | MOUSE_ALL | MOUSE_BUTTONS, and every move over the page |
| 64 | MOUSE_PIXELS | `px`, `py` as well as the cell |
| 128 | COMPOSE | COMPOSE preedit |

Each mouse mode includes the ones above it, as xterm's modes 1000, 1002 and 1003 do: MOUSE_DRAG and MOUSE_ALL send buttons too. The wheel needs no mode (section 6.5); MOUSE_PIXELS still decides whether it carries `px` and `py`. A field a mode does not ask for (`text`, `base`, `px`, `py`) is left out.

**Always on, whatever the mode:** raw text, KEY press of a non-text key, PASTE, FOCUS_IN, FOCUS_OUT, RESIZE, PAGE, and WHEEL over the page. A mode change applies to events generated after the receiver takes it. Two kinds of key are exceptions: a key that only modifies or locks (Shift, Control, Alt, AltGraph, Super, Hyper, Meta, Fn, Symbol, and Caps, Scroll and Num Lock) goes only in ALL_KEYS or KEY_RELEASE, as the Kitty keyboard protocol reports a modifier alone only when asked; and the dead key goes only in ALL_KEYS (section 5.7 rule 4).

### 6.4 A page's own modes

A teletext page is the unit a viewer reads, so a page can ask for the input it wants, such as the mouse for a game or a picture to click on, without the channel's program having to follow the viewer:

- **In a page file**, a line `IM,modes` (the mode bits of section 6.3, decimal), kept by the reader and written back by the writer, as the `CU` line is.
- **In packets**, a control record PAGE_MODES (section 7.2) naming the page and its modes.

Those modes apply only while that page is open, and go when it closes: the modes in force are the top of the session's stack and the open page's own modes together. Nothing has to be popped, so no page can leave the mouse switched on behind it, as a crashed terminal program leaves its modes. A channel may still change modes for the whole session with PUSH_MODE and POP_MODE, for instance when PAGE says which page the viewer opened.

### 6.5 Why the mouse goes only when asked, and the wheel always

A plain click goes to the channel only in a mouse mode, asked for by the channel or the page (the owner's decision of 21 October 2026):
1. **A click keeps its ordinary meaning.** On a channel that does not use the mouse, a plain click on the page follows a link or a page number as on any page; if every click went to the channel, the viewer would need the browser's modifier to follow a link on a page that never wanted the click.
2. **It is how terminals work.** xterm, kitty and the Input Event Protocol report the mouse only to a program that asks.
3. **Little about the pointer leaves unasked.** Motion and buttons go only when asked, so a channel learns nothing of the pointer's movements it did not request; the wheel is the exception below.
4. **It costs a channel that wants clicks one mode, once,** or one line in its page.

The wheel goes to a channel that takes input whenever the pointer is over its page, in any mode or none (the owner's decision of 25 October 2026: "pass the mouse wheel through to the server when the mouse is over the teletext window", answered "Always, over any page"). A channel's page is the content the viewer scrolls, as a web page is, and the wheel over it is the viewer reading on: a page that scrolls inside itself, as a long article does, needs it, and a channel that does not use it lets it go. Over the browser's own parts, beside the page, the wheel stays the browser's. A wheel turn says where the pointer is, as a cell; this is the one thing of the pointer a channel learns unasked, and only while the viewer turns the wheel over its page.

## 7. The protocol: channel to receiver

Everything a channel says about input is teletext: records of the audio profile's frame (the engine's REQ-AUD-003) on data channel 12, a user-defined service of EN 300 708 clause 6.7.3.2, each one fragment carried in one 4/31 packet, which the audio receiver steps over. A channel sends them as binary push messages (packets), and a page file may carry a cursor as a `CU` line.

### 7.1 The cursor record (type 4)

A record of 16 bytes: profile version 2, type 4, body length 8 (big-endian), the body, and the frame's CRC-32.

| Body byte | Field | Range |
|---|---|---|
| 0–1 | page, big-endian | `0x100` to `0x8FF` |
| 2–3 | acknowledged, big-endian | the input count acted on, modulo 65 536 (below); 0 for none yet |
| 4 | row | 1 to 23, or 255 for no cursor (row 0 is the header, row 24 the Fastext row) |
| 5 | column | 0 to 39 |
| 6 | width | 0 to 40: how far echo may run from the column; column + width ≤ 40 |
| 7 | flags | 1 ECHO, 2 MASKED (echo `*`), 4 BLOCK (a block rather than a bar); others refused |

Echo requires a width; MASKED requires ECHO; no cursor requires column, width and flags 0. A record that breaks any rule is refused whole. The cursor is optional, as a cursor is: a game sends none, or one with no cursor only to acknowledge.

**The input count** is how much input of the session the channel has acted on: each event counts one, each character of raw text counts one, and a PASTE counts one. The receiver counts what it sends the same way, and so knows which echoes the channel has answered and how long it took. The count wraps at 65 536 and is compared by RFC 1982 serial arithmetic: an older acknowledgement changes nothing.

**The TTI `CU` line.** A page file may carry its cursor as `CU,row,column,width,flags[,acknowledged]`, decimal, for the page that holds it. The reader keeps the last such line and the writer writes it back; a line that cannot be read is reported and dropped. The engine's encoder does not turn it into a packet: a receiver reads it from the page it already has.

### 7.2 The control record (type 5)

A record whose body is one control message, encoded as receiver events are (`0xFF`, a type, its fields), at most 26 bytes, so the record with its 8 bytes of frame is the 34 bytes of one fragment.

| Type | Name | Fields |
|---|---|---|
| `0x01` | WELCOME | `version` uv, `caps` uv (a subset of the receiver's) |
| `0x02` | PUSH_MODE | `modes` uv |
| `0x03` | POP_MODE | `count` uv |
| `0x04` | PAGE_MODES | `page` uv (`0x100` to `0x8FF`), `modes` uv: the modes of that page while it is open (section 6.4); 0 clears them |

Types `0x40` to `0x7F` are extensions with a length, skipped when unknown, as in section 5.4.

## 8. Behaviour

1. **Send at once.** One write per event. The receiver MAY merge consecutive unsent mouse moves (keeping the latest) and sum unsent wheel deltas; nothing else is merged or dropped.
2. **Order** is the stream's order.
3. **Held input.** On FOCUS_OUT or a lost connection the channel treats every held key and button as released; the receiver sends no release for them.
4. **The rate.** A receiver sends at most `MAX_PER_SECOND` (120) input units in any second, counted as the input count counts them, and never drops a release to keep to it. 120 is qrkeyboard's relay limit.
5. **Protocol errors** close the connection, on either side.
6. **Bounds.** A message over `MAX_MESSAGE`, a field over its maximum, a varint over 5 bytes or not minimal: a protocol error.
7. **Nothing waits on a timer.** A receiver sends an event when it happens and draws what comes back when it arrives (decision E.97, REQ-INT-008); the heartbeat (a ping after 25 s of silence, a pong within 10 s) is the push connection's own.
8. **A host goes to a page by sending it.** A cursor record naming another page of the same channel, while keys go to that channel, opens that page in the receiver, as a terminal shows what its host sends. It is the only thing a channel's record can make a receiver do, within the channel, and never a fetch; the viewer choosing a page overrides it.
9. **Terminal programs.** A channel that feeds an ordinary terminal program translates events into whatever encoding that program asked for.

## 9. The receiver's side

### 9.1 When keys go (NeoTeletext)

Keys go to a channel only while all of these hold: the tab is the active one; the page open in it is the channel's; the channel declares input over a WebSocket whose session has been welcomed; the window has the focus; and the viewer is not editing the address. Then every key goes except the browser's own: those with the browser's modifier (Command on macOS, Control-Shift elsewhere), and the strip, the overview and a background tab, which never take keys, and the magazines and the page list, which take the arrows from a click on them until a click elsewhere (the browser's decision 105). Command-Escape (Control-Shift-Escape elsewhere) leaves the page; plain Escape is the channel's.

When keys start going, the trusted core sends PAGE and FOCUS_IN; when they stop (another tab, another page, the page closed), FOCUS_OUT and PAGE 0, so the channel lets go of a key held as the viewer left (REQ-INT-108); when the window loses the focus or the address is being edited, FOCUS_OUT, and FOCUS_IN when it comes back.

**The mouse.** A plain click on the page goes to the channel only in a MOUSE mode; otherwise it does what it does on any page (a link, a page number). A click with the browser's modifier always follows a link. The wheel goes to the channel while the pointer is over the page, in any mode (section 6.5); over the rest of the window it scrolls the browser.

**Paste and composition.** The browser's paste shortcut pastes into the page as PASTE while keys go to it. The window's input method stays enabled while typing; its preedit goes as COMPOSE in that mode, and its committed text as text.

### 9.2 The strip

The trusted strip says "Keys go to *host*" while keys go, with "Not secure" on a plain `ws://` socket and the round trip measured from acknowledgements. No page can draw into the strip.

### 9.3 Cursor and echo

- The interface draws the cursor as an overlay in a style no page can draw: an amber bar 0.15 of a cell wide, blinking with a half period of 530 ms, or, with BLOCK, an amber outline 0.12 of a cell thick, so the character under it shows. Never an underline (decision 42).
- **Echo** (the ECHO capability): while the cursor record's ECHO flag is set, a printable key the viewer types is drawn at once, provisionally, in amber on a dark cell in the interface's monospace face, `*` when MASKED, at most `width` characters from the cursor. It is the viewer's own key, never the channel's text. It goes when the acknowledgement reaches it, or after 2 s.
- The cursor is shown only on the page it names, only while keys go to its channel.

### 9.4 Page selection

A channel that takes input selects pages by videotex's convention, which it implements: `*nnn#` goes to a page, `#` to the next, `*#` to the one before, `*00` shows the page again; three plain digits where the channel has no other use for them. The receiver interprets none of it: it sends the keys.

### 9.5 Characters a page cannot show

Echo (section 9.3) draws the viewer's own character in the interface's monospace face, whatever its script, one cell a character, a wide character (Chinese, Japanese, Korean) over two; it is the interface's drawing, not the page's, so a character no teletext set has still echoes. What the channel then draws is the channel's choice: the nearest character of the page's sets, a placeholder, or a page in another set (the engine's area CHR).

### 9.6 `neottx view`

Every key goes while the channel takes input, Control-C included; Control-] leaves and returns. With a terminal that reports releases (the Kitty keyboard protocol), it sends releases in KEY_RELEASE; otherwise a press only. It sends PASTE from bracketed paste, FOCUS from the terminal's focus events, and PAGE when the viewer opens a page.

## 10. The phone keyboard

A phone scans a QR code and becomes a keyboard, through qrkeyboard's relay and protocol 3 (the engine's `neoteletext-qrkeyboard`, decision E.93):

- The screen's side computes the configuration's hash as qrkeyboard's canonical JSON does, puts the code, the pairing key (no-PIN mode) and the hash only in the QR address's fragment, pairs by salts and, with a PIN, SPAKE2 on P-256 bound to the code and the hash, and seals every frame with AES-256-GCM under a counter nonce taken once and in order. Five wrong PINs lock. Only the layout's keys are taken; a key held past 15 s is released; a relay WebSocket on another host is refused; frames are at most 1024 bytes and response bodies at most 64 KB.
- **A phone's keys become the protocol's events with no modifiers:** its text becomes text, its named keys their functional codes (its colour keys 92 to 97), as from any keyboard. In NeoTeletext the phone's keys go from the keyboard process to the trusted core and on to the interface, which acts on them exactly as on its own: into a page, or choosing pages. A phone's keys reach the address field only after the viewer puts the caret there with the pointer.
- One phone at a time; Finish in the strip; a dropped phone holds the screen for at most 30 s. The QR is shown only from the panel, with its one-line warning: whoever scans it has the keyboard.
- qrkeyboard.com runs protocol 3 since 21 October 2026.

## 11. Security and privacy

### 11.1 What is protected

The viewer's keystrokes and reading habits; the truth of the screen and the strip; the trusted core's readers; the browser's own keys; the phone's pairing secret.

### 11.2 Attackers

A channel's author; a network attacker; a compromised interface, fetcher, decoder or keyboard process; a hostile relay; anyone who can see the screen; a stranger who scanned the QR.

### 11.3 Threats and answers

| Threat | Answer |
|---|---|
| A page or channel starts taking keys unasked | Only a descriptor declares input; the strip says "Keys go to"; keys go only to the open page of the active tab. |
| Keys go somewhere else | The push address is on the channel's origin; the fetcher takes no address; nothing in the protocol names one. |
| A keylogger on a plain connection | `ws://` is "Not secure" in the strip; `wss` is the default for any channel worth typing into. |
| The channel tracks the pointer | Mouse motion goes only in MOUSE_DRAG or MOUSE_ALL, which the channel must ask for, and only over its own page while keys go to it. |
| Fingerprinting by keyboard layout | `base` goes only in BASE_KEY; lock states only in `mods`, as any terminal sends them. There is no clock: the channel learns typing rhythm only from arrival times, which the network blurs, and no physical key code. |
| A paste runs as keystrokes | PASTE is one length-prefixed event the channel treats as data; it cannot break out of itself. |
| A flood from the channel | Pushed rows are coalesced to the display rate; records are bounded and checked; a protocol error closes the connection. |
| A flood from a receiver | 120 units a second, at the relay, the keyboard process and the trusted core. |
| A forged cursor, echo or strip | The cursor and echo are drawn in styles no page can draw, only within rows 1 to 23 and the record's width; the strip is outside the page. Echo is only of the viewer's own keys. |
| A compromised interface types | It can only send intents for the channel the trusted core already lets it type into, and the trusted core encodes. |
| A compromised fetcher | It holds no keys but those going to its own channel, and reads only bounded messages. |
| A compromised keyboard process | It is a hostile person at the keys: bounded keys, no modifiers, the rate limit, and the address field only after the caret is placed. |
| Someone photographs the QR | The QR shows only from the panel, with its warning; a PIN is offered; one phone; Finish. |
| The session is taken over after a reconnection | A reconnection is a new session with nothing carried over; identity, if any, is the channel's cookies. |

### 11.4 Privacy

Keys are never logged by the receiver. The relay learns a phone keyboard's name, layout, addresses, sizes and timing, nothing of the keys. Nothing persists past the window.

### 11.5 Residual risks, ranked

1. Plain `ws://` (high likelihood where used; narrowed since TLS was built).
2. A compromised interface (low likelihood, medium consequence).
3. An exploited keyboard process (low, medium).
4. A QR photographed on a public screen (medium, medium).
5. An imitation of the cursor, echo or strip (medium, low).

## 12. Requirements

The normative requirements of the input system. Identifiers continue the engine's area INT; on adoption, REQ-INT-001 to REQ-INT-004 are withdrawn (replaced by REQ-INT-101 to REQ-INT-111) and REQ-INT-005 to REQ-INT-008 stand as written there, and the browser's requirements 18.1 to 18.10 are replaced by REQ-INT-130 to REQ-INT-139, which name NeoTeletext.

**The protocol**

**REQ-INT-101 — The input stream.** A receiver shall send input as one ordered stream of raw UTF-8 text and `0xFF`-framed events (sections 5.1 to 5.4), in binary messages on the channel's push WebSocket, each holding whole events and whole characters and at most 4096 bytes. *Verification:* encoder and decoder round trips; the message bound; a fuzz target of the decoder.

**REQ-INT-102 — Encoding.** Varints shall be minimal and at most 5 bytes; strings length-prefixed and within their field's maximum; text without control characters; and a reserved type, an unknown core type, a reserved flag bit, malformed UTF-8 or an over-long field shall be a protocol error that closes the connection. Extension types shall be skipped by their length. *Verification:* decoder tests of each error and of a skipped extension.

**REQ-INT-103 — Events.** The core events shall be KEY, MOUSE, WHEEL, PASTE, FOCUS_IN, FOCUS_OUT, RESIZE, COMPOSE, HELLO and PAGE, with the layouts of sections 5.4 and 5.5; PASTE at most 4000 bytes and COMPOSE at most 256. *Verification:* round trips of every event and every field's bounds.

**REQ-INT-104 — Keys.** A printable result of a key shall be sent as text, except in ALL_KEYS; every other key as KEY, a character key by its unshifted code point and every other by its functional code, with modifiers as the Kitty bit set and `base` only in BASE_KEY. *Verification:* tests of text, a Control combination, a named key and a non-United-States layout.

**REQ-INT-105 — Functional codes.** The codes of section 5.6 shall be fixed, and only ever added to; codes from 128 shall follow the engine's pinned W3C name table. *Verification:* a test pins the codes of Enter, Up, Red and F1, and the first code from 128.

**REQ-INT-106 — Negotiation.** A receiver shall send HELLO first and no input before WELCOME; it shall use only the capabilities both sides set; a reconnection shall start a new session with the mode stack empty, nothing held and the input count at zero. *Verification:* a session test; a test that nothing goes before WELCOME; a reconnection test.

**REQ-INT-107 — Modes.** A receiver shall keep a mode stack of at least 16 entries, apply PUSH_MODE and POP_MODE to events generated after it takes them, and send in each mode exactly what section 6.3 says, the always-on events in every mode. *Verification:* tests of each mode.

**REQ-INT-108 — Held input.** On FOCUS_OUT or a lost connection a channel's decoder shall treat every held key and button as released, and a receiver shall send no release for them. *Verification:* a decoder test.

**REQ-INT-109 — The rate.** A sender shall send at most 120 input units in any second, counted as the input count counts them, and never drop a release to keep to it. *Verification:* the 121st unit; a release beyond it, across the clock's wrap.

**REQ-INT-110 — The cursor record and the input count.** The cursor record shall be as section 7.1, its acknowledgement the input count acted on; the receiver shall count what it sends as the channel counts it. *Verification:* round trips through a packet; bounds; a sound on the same channel; the count across text, events and a paste.

**REQ-INT-111 — The control record.** WELCOME, PUSH_MODE, POP_MODE and PAGE_MODES shall be records of type 5 as section 7.2, one fragment each, checked whole. *Verification:* round trips; refusals; a fuzz target.

**REQ-INT-112 — Immediacy.** Every event shall be written when it happens, one write per event, merging only unsent mouse moves and wheel deltas; nothing shall wait on a timer (with REQ-INT-008). *Verification:* the latency tests of REQ-INT-008 and REQ-INT-135.

**REQ-INT-114 — A page's own modes.** A page shall be able to ask for input modes for itself, by an `IM,modes` line in its page file or a PAGE_MODES record; the receiver shall apply them only while that page is open, together with the top of the session's mode stack, and drop them when it closes; the reader shall keep the line and the writer write it back, and a line or record that breaks a bound shall be dropped and reported. *Reason:* a page is the unit a viewer reads, and modes that go with their page cannot be left on (section 6.4). *Verification:* reader and writer tests of the line; a receiver test that the modes come and go with the page and add to the stack; a fuzz target.

**REQ-INT-115 — The mouse only on request; the wheel over the page.** A receiver shall send MOUSE only in a mouse mode asked for by the channel or the open page, and otherwise give a click its ordinary meaning on the page; it shall send WHEEL, in any mode, while the pointer is over the page (amended 25 October 2026, the owner's decision in section 6.5). *Reason:* section 6.5: a click keeps its ordinary meaning; terminals report the mouse only to a program that asks; little about the pointer leaves unasked; it costs a channel one mode; and the wheel over a page is the viewer reading on, which a page that scrolls itself needs. *Verification:* a receiver test that a click follows a link until a mode or the page asks, and then goes to the channel; and that the wheel goes to the channel over its page with no mode.

**REQ-INT-116 — International keyboards.** A receiver shall send text as the Unicode characters the layout or input method produced, in logical order and in Normalization Form C, never translated into a teletext character set; shall send a dead key as no text (in ALL_KEYS as the key `Dead`) and the composed character after it; shall not report AltGr as Control and Alt; and shall give a character key's `key` from the active layout and `base` from the United States layout of the same physical key. *Reason:* the protocol carries what the viewer typed, in any language, and leaves its meaning to the channel; a shortcut binds by position, a letter by meaning (section 5.7). *Verification:* receiver tests with Russian, Hebrew, German (AltGr), French (dead keys) and AZERTY layouts, a Japanese input method's preedit and commit, and a decomposed `e` and combining accent sent as U+00E9; a channel test of native digits selecting a page.

**REQ-INT-113 — A host goes to a page.** A cursor record naming another page of the same channel shall open that page while keys go to that channel, and do nothing else; the viewer's own choice shall override it. *Verification:* a trusted-core test.

**The receivers**

**REQ-INT-130 — When keys go (NeoTeletext).** Keys shall go only under every condition of section 9.1, and the trusted core shall check each again; the browser's own keys and those of the strip, the page list, the overview and a background tab never go. *Verification:* trusted-core tests of each condition; an interface test that Command never goes.

**REQ-INT-131 — The strip.** The strip shall say "Keys go to *host*" while keys go, "Not secure" on plain `ws://`, and the round trip. *Verification:* a strip test.

**REQ-INT-132 — The trusted core encodes.** Only the trusted core shall encode the protocol; the interface shall send intents, checked whole; only the trusted core sends HELLO, RESIZE, PAGE and FOCUS. *Verification:* protocol tests of the intents; a hostile-interface test.

**REQ-INT-133 — The fetcher.** The fetcher shall take from the trusted core only encoded input messages of at most 4096 bytes, write them to the push WebSocket at once, and take no address; nothing it takes changes what is fetched (decision 22). *Verification:* the fetcher reader's tests and fuzz target.

**REQ-INT-134 — Cursor and echo drawn safely.** The cursor and echo shall be drawn by the interface as section 9.3 says, in styles no page can draw, within the record's row and width, the echo only of the viewer's own printable keys, provisional and gone on acknowledgement or after 2 s. *Verification:* interface tests.

**REQ-INT-135 — Latency.** A key shall be written within 1 ms; the push socket shall have `TCP_NODELAY`; a pushed packet of the page being typed into shall be drawn within 20 ms. *Verification:* the timed test, with the round trip's median on the computer's own network held to 2 ms.

**REQ-INT-136 — Mouse, paste and composition (NeoTeletext).** Clicks shall go to the channel only in a mouse mode and only over its page, a click with the browser's modifier always following a link; the wheel shall go to the channel over its page in any mode, and scroll the browser elsewhere (amended 25 October 2026); paste shall go as PASTE and the input method's preedit as COMPOSE while keys go. *Verification:* interface and trusted-core tests.

**REQ-INT-137 — No key is logged, and the round trip is measured.** No receiver shall log a key; the round trip shall be measured from acknowledgements, with at most 256 sends remembered. *Verification:* a log test; a trusted-core test.

**REQ-INT-138 — The phone keyboard.** As section 10, and the engine's REQ-INT-007; in NeoTeletext, its own sandboxed process alone holding the pairing secret. *Verification:* as REQ-INT-007; the browser's sandbox and panel tests; a real phone by hand.

**REQ-INT-139 — Compiled out.** In NeoTeletext, typing and the phone keyboard shall be features (`interaction`, `phone-keyboard`) that compile out whole. *Verification:* the builds without them.

## 13. Decisions in the merge

| # | Choice | From | Why |
|---|---|---|---|
| 1 | Raw UTF-8 text with `0xFF`-framed events | Input Event Protocol | One byte an ASCII character, against 14; `0xFF` never occurs in UTF-8, so no timeout or escape guessing. |
| 2 | Carried in binary messages of the push WebSocket, whole events per message | Built system | Push is already a WebSocket; messages hold whole events so a channel, or a microcontroller, parses each alone. |
| 3 | Varints, flag-gated optional fields, extension types with a length | Input Event Protocol | Small, extensible; the version-1 record could not grow but by a new version. |
| 4 | HELLO and WELCOME, capabilities, a mode stack | Input Event Protocol | The built system had no negotiation: a boolean in the descriptor was the whole handshake. |
| 5 | Mouse, wheel, paste, composition, resize, releases | Input Event Protocol | Gaps of the built system: only a left click, no paste, no input-method preedit, no release events in `neottx`. |
| 6 | Kitty modifiers, `base` | Input Event Protocol | Super, Hyper, Meta and lock states, and shortcuts on any layout; the built system carried only Shift, Control and Alt. |
| 7 | Functional codes with teletext's keys (colour, Teletext, Channel, Exit, Info, Guide) in one byte, and W3C's names beyond | Both | Remotes and phones send Fastext's colour keys; the W3C table the built system pinned covers every other key. |
| 8 | PAGE | Built system | A teletext channel needs to know which page is open; terminals have no such thing. |
| 9 | Everything back from the channel as teletext records on data channel 12: the cursor (type 4) and, new, the control record (type 5) | Built system, extended | A channel's answer stays teletext, so files, broadcasts and microcontroller receivers carry it; the Input Event Protocol's control messages ride the same carriage. |
| 10 | Acknowledgement by the input count, no sequence numbers and no clock | Both | The stream's order makes numbering redundant; the built system's per-record clock exposed typing rhythm for no use. The acknowledgement still drives echo and the round trip. |
| 11 | Losing focus releases held input, at the channel | Input Event Protocol | No stuck keys, and no burst of releases on the wire; the built system sent releases from the trusted core. |
| 12 | A reconnection is a new session | Input Event Protocol | Simpler and safer than the built system's resume record; PAGE makes the channel push the page again. |
| 13 | The rate of 120 a second, the bounds, the strip, the security model, the phone keyboard | Built system | Measured and reviewed; unchanged. |
| 14 | Mouse only when the channel or the page asks; a page asks for itself (`IM` line, PAGE_MODES) | Input Event Protocol, extended | Agreed by the owner on 21 October 2026, for the reasons of section 6.5; a page's modes go with the page, so none can be left on. |
| 15 | Version 1 retired, not kept beside version 2 | — | Nothing outside these repositories speaks it; two formats would be a shim. |

## 14. Adopting it

Adopted by the owner on 21 October 2026, as the engine's decision E.100 and the browser's decision 48:

1. **The engine:**
   - `neoteletext-input`: the version-2 encoder and streaming decoder, the functional codes, the control record; the version-1 record removed.
   - `neoteletext-web`: `INPUT_MESSAGE_MAX` to 4096.
   - `neoteletext-audio`: record type 5 stepped over.
   - `neottx view`, `neottx keyboard`: version 2.
   - Area INT: REQ-INT-001 to REQ-INT-004 withdrawn, REQ-INT-101 to REQ-INT-116 added; `docs/spec/design/input.md` replaced by a pointer here; `int.md` keeps each number and title, so the traceability table covers them.
2. **The browser:**
   - The trusted core encodes version 2, keeps the mode stack and the input count, and sends HELLO, RESIZE, PAGE and FOCUS.
   - The interface sends intents for mouse, wheel, paste and composition.
   - The decoder finds control records.
   - `neoteletext-site terminal` speaks version 2.
   - Requirements 18.1 to 18.10 replaced by pointers to REQ-INT-130 to REQ-INT-139; `docs/interaction.md` replaced by a pointer here, its sections 16 and 17 kept as history.
3. **Tests:** each requirement's verification above; the latency tests unchanged in what they hold.
