# The neoteletext input system

| | |
|---|---|
| **Status** | Proposed on 21 October 2026, for the owner to adopt. The owner agreed on 21 October that losing focus releases held input at the channel (section 13 item 11), that everything the channel says about input travels as teletext records (item 9), and that the mouse goes to a channel only when it asks (item 14), a page asking for itself (withdrawn on 27 October 2026, section 6.3). **Amended on 28 October 2026 for the return channel** (`RETURN-CHANNEL.md`, the owner's decisions A to N of its section 5; the engine's decision E.133): every move over the page at most 60 a second (section 9.8), MOUSE action 3, touch (TOUCH, MOUSE's device), the messages of one moment written together, what is never acknowledged counting nothing, a lost session resumed (section 6.4), the round trip from ping and pong, and pointer areas withdrawn. |
| **Merges** | The input system built on 20 October 2026 (the engine's decisions E.90 to E.94 and E.97, the browser's decisions 44 to 46), and the owner's *Input Event Protocol v1* of 20 October 2026. Section 13 records what was taken from each and why. |
| **Protocol** | Version 2. Version 1, the fixed 14-byte key record, is retired (section 14). |
| **Words** | MUST, SHOULD and MAY as in RFC 2119. A *receiver* is anything that shows a channel and sends input: NeoTeletext, `neottx view`, `neottx keyboard`, a microcontroller receiver. A *channel* (or host) is the server that takes the input. |

---

## 1. What it is for

A teletext channel that takes input is a host, and the receiver is its terminal. The viewer types; each key goes to the channel at once; the channel decides what it means and answers by pushing the rows that changed, and, if it likes, a cursor. Nothing ever executes in the receiver: a game, a form, a chat and a shell are the same to it, a terminal on a line to a host.

**In scope:** keys, committed text, paste, input-method composition, mouse buttons, wheel and motion over the page, touch and pens, focus, the page the viewer opened, the cursor shown while typing, capability negotiation, the phone keyboard as a source of keys, and the security and privacy of all of it.

**Out of scope:** forms (they are page files and HTTP submissions, the engine's area FRM), fetching and push themselves (area WEB), and what a channel does with a key.

## 2. Principles

1. **A terminal, not a browser.** The receiver sends what the viewer did; the channel decides what it means. No page can run code, and no input path can make the receiver fetch, navigate away from the channel, or do anything but draw.
2. **One message per event, never held back.** Each event is its own message, written as it happens; messages already waiting to be written at the same moment are written together, in one write and one TLS record where the transport allows, and nothing is held back to be grouped (`RETURN-CHANNEL.md` decision C, REQ-RCH-010). `TCP_NODELAY`; nothing waits on a timer (decision E.97) but the pointer's moves, at most 60 a second (section 9.8).
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
| 1 | Interface | Takes the window's key, mouse, wheel, paste and composition events. Sends an *intent* to the trusted core only when the active tab's open page takes input and the browser's own modifier (Command on macOS, Control-Shift elsewhere) is not held. Draws the cursor the trusted core allows. |
| 2 | Trusted core | Checks every condition again (requirement REQ-INT-130), applies the rate limit, paces the pointer's moves and numbers the contacts of a touch screen (section 9.8), tracks held keys and the input count, keeps what is not yet acknowledged for a resumption (section 6.4), **encodes the protocol**, and alone sends HELLO, RESUME, RESIZE, SELECT, FOCUS and the releases, stamping every input event with the page on screen (section 5.4). |
| 3 | Fetcher | Writes each message it is given to the channel's push WebSocket at once, those given at one moment together; holds a move while the socket's unsent bytes are over a bound (section 9.8); measures the round trip by WebSocket ping and pong (section 9.2). It takes nothing else and opens nothing (requirement REQ-INT-133). |
| 4 | Decoder | Finds cursor and control records in pushed packets and `CU` lines, untrusted, and passes them on. |
| 5 | Trusted core | Checks each cursor and control record; applies WELCOME; passes the interface only what it may draw. |

The interface never encodes the wire format: it sends intents, so a compromised interface can at worst type into the one channel the trusted core already lets it type into (the browser's open decision 3). The phone keyboard is a sixth process, `neoteletext-keyboard`, which alone holds the pairing secret; its keys go to the trusted core and on to the interface, which treats them as its own (section 10).

### 3.4 In `neottx`

`neottx view` is a terminal receiver: crossterm's key, paste, focus and resize events become the protocol's events in the fetcher process, as in the browser. Control-] leaves and returns to the channel, as telnet's escape character does; it is the one key that never goes. `neottx keyboard` bridges a phone to a channel's push WebSocket: a channel gets a phone keyboard without implementing qrkeyboard. It draws no page, so it sends no SELECT: the connection takes the channel's initial page, and the bridge stamps the phone's keys with the page and sub-code the channel last sent it, sending none before the first.

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
"push": { "method": "websocket", "input": true }
```

- `input` MUST be a JSON boolean; it defaults to false. It is refused with `"method": "sse"`: input goes back only on the push WebSocket.
- The push WebSocket is always `<channel>push` (`SERVER.md` section 4.2), and a descriptor naming another address is refused. Over `https` it is `wss`, and over `http`, `ws`.
- Plain `ws://` is allowed, and the receiver says "Not secure" wherever it says where keys go.
- A page cannot declare input; only the channel's descriptor can.
- The protocol version is not in the descriptor: it is negotiated on the socket (section 6).

## 5. The protocol: receiver to channel

### 5.1 Transport and framing

- **Transport:** the channel's push WebSocket. Each **binary** message the receiver sends is a piece of one ordered input stream, the concatenation of all binary messages on that connection. The only other message a receiver sends is the push subscription (text).
- **Whole events per message.** A message MUST hold whole events and whole UTF-8 characters, so a channel can parse each message alone; text may be split between messages anywhere between characters.
- **At most `MAX_MESSAGE` (8192) bytes a message,** room for a SELECT carrying the longest page parameters (DEC-1715).
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

- Committed text from an input method, or from a phone, is sent as text.
- Text MUST NOT contain control characters (U+0000 to U+001F, U+007F to U+009F). Enter, Tab, Backspace, Escape and every Control, Alt, Super, Hyper or Meta combination are key events.
- Bytes `0xC0`, `0xC1` and `0xF5` to `0xFE` outside an event, and malformed UTF-8, are protocol errors.
- A key is never sent as raw text: every key is a KEY event carrying its text (section 5.5). Raw text is what does not come from a key: an input method's committed text and a phone's.

### 5.4 Events

An event is `0xFF`, a type byte, then its fields.

| Type range | Layout |
|---|---|
| `0x01`–`0x3F` | Core events, fixed layout. An unknown core type is a protocol error. |
| `0x40`–`0x7F` | Extensions: `uv` length, then the payload. A receiver of the stream skips one it does not know. |
| `0x00`, `0x80`–`0xFF` | Reserved: a protocol error. |

| Type | Name | Fields | When |
|---|---|---|---|
| `0x01` | KEY | section 5.5 | every press, repeat and release |
| `0x02` | MOUSE | the stamp, `flags` u8, `button` u8, `col` uv, `row` uv, `px`? uv, `py`? uv, `mods`? u8 | every press and release over the page; every move that changes the dot, at most 60 a second (section 9.8); gone when the pointer leaves the page or a contact is cancelled |
| `0x03` | WHEEL | the stamp, `flags` u8, `dx` sv, `dy` sv, `col` uv, `row` uv, `px`? uv, `py`? uv, `mods`? u8 | while the pointer is over the page |
| `0x04` | PASTE | the stamp, `str`, at most `MAX_PASTE` (4000) bytes | while the page has the keyboard focus |
| `0x05` | FOCUS_IN | none | always |
| `0x06` | FOCUS_OUT | none | always |
| `0x07` | RESIZE | `cols` uv, `rows` uv, `pw` uv, `ph` uv | always |
| `0x08` | COMPOSE | the stamp, `cursor` uv, `str` at most `MAX_COMPOSE` (256) bytes; an empty string ends composition | while an input method composes |
| `0x09` | HELLO | `version` uv, `caps` uv, `agent`? str (at most 64 bytes) | first, once |

Type `0x0A` was PAGE until 31 October 2026 (DEC-1538, REQ-1556). It is unused, so it is a protocol error like any unknown core type.

**HOVER**, an extension (`0x43`, so a channel that does not know it skips it): `uv` length, then the stamp, `flags` u8 (bit 0: 1 when the pointer left the control, 0 when it entered; others a protocol error), `col` uv and `row` uv, the control's first cell, its top left (section 7.3). It goes as the pointer enters and leaves a control of the open page while keys go to the channel: leaving one control for another sends the leave, then the enter. It lets a channel show something as the pointer passes, a row's summary or a help line, without working out from the moves which control the pointer is over (`RETURN-CHANNEL.md` decision F, REQ-RCH-040). Like a move, it counts no input units (section 7.1) and is not held to the rate (section 8 rule 4). It goes only for a mouse or a pen that hovers, never for a finger (REQ-RCH-049).

**TOUCH**, an extension (`0x44`, so a channel that does not know it skips it, REQ-RCH-043): `uv` length, then the stamp, `flags` u8 (bits 0 and 1 the action, as MOUSE's: 0 down, 1 up, 2 move, 3 gone; bit 2 `px`, `py` present; bits 3 to 7 a protocol error), `id` u8, `col` uv, `row` uv, `px`? uv, `py`? uv, and nothing after. It is every contact on a touch screen after the first, which goes as MOUSE (section 9.8): `id` is 1 to 9, the contact's number from its beginning to its end, the lowest free when it begins; an `id` of 0 or above 9 is a protocol error. At most `MAX_CONTACTS` (10) contacts are on the page at once, ten fingers. TOUCH is sent only when both sides set TOUCH (section 6.2). Its down and up count one input unit each, as a click's press and release do; a move and gone count none (REQ-RCH-054).

**Selected, active and focused,** three words defined once (neoteletext-common's DEC-1538, amending DEC-1526 item 5).
- **Selected:** the page and sub-page a tab shows, named by SELECT. A connection has at most one selection, which is what the channel sends, keeps and compares.
- **Active:** what a selected page is to the back end. An active page receives the back end's updates, whatever the viewer's input is doing (REQ-1553). Only a new selection, SELECT page 0 included, ends them.
- **Focused:** what a selected page is for the viewer's input, and only for input. A page has the **keyboard focus** while keys go to it, which FOCUS_IN and FOCUS_OUT tell the channel, and the **pointer focus** while the pointer or a touch is over its page area, which MOUSE gone ends (REQ-1554).

So a page can be active without being focused: in a tab behind another, in a window behind another application, while the viewer types an address, or with the pointer outside it. Losing either focus never changes the selection and never stops updates. "Keys go" in this document means the selected page has the keyboard focus.

**The stamp** (REQ-1555, the owner's "belt and braces"). KEY, PASTE, COMPOSE, MOUSE, WHEEL, TOUCH and HOVER each begin with `page` uv and `sub` uv, before their other fields: the page and sub-code on screen in the tab when the event happened, which is what the viewer was looking at, not merely what was selected. Between a new selection and the arrival of its page the old page is still on screen, and a click or key aimed at it carries the old page.
- `page` is `0x100` to `0x8FF`. `sub` is a sub-code `0x0000` to `0x3F7E`. It is never `0x3F7F`, because a page on screen is always a particular sub-page. Anything else is a protocol error, and so is a page of 0.
- The stamp costs three bytes on a page of sub-code 0000, and four at most.
- **No other event has one.** FOCUS_IN and FOCUS_OUT carry none and are always acted on, since FOCUS_OUT releases held keys and must never be dropped. Nor do HELLO, RESUME, RESIZE and SELECT. Raw text (section 5.3) cannot carry one: a channel takes it for the selection as it stands.
- **The channel's check.** A channel compares each stamp with the connection's selection as last recorded. When the page and sub-code are the same, the event is acted on. When they differ the event is dropped and nothing of it applied, the drop is counted, at most one log line an interval names the count, as for invalid packets (REQ-1462), and the connection is kept.
- **A release is never dropped.** A release whose stamp does not match is still applied, as a release of what the connection holds, so that nothing stays held; so is a pointer's gone. A press with a stamp that does not match is dropped.
- **One truth.** The selection stays the only truth: a stamp can only cause a drop, never send input to a page other than the selection.

**SELECT**, an extension (`0x40`, so a channel that does not know it skips it; REQ-INT-140), decided by the owner on 29 October 2026: "we send an event saying which page the user has selected and if there are subpages then the server transmits them at that time. also the same event should send if the user has selected a subpage", and revised on 30 October 2026 by DEC-1527 (each browser tab has its own self-contained connection and decoder, so a connection has one selection and SELECT carries no view number) and DEC-1526 (every sub-code is a peer). `uv` length, then `page` uv and `sub` uv, then the page parameters to the end of the payload:
- `page` is the page selected, `0x100` to `0x8FF` in teletext's hexadecimal page form, or 0 when the tab no longer shows a page of the channel.
- `sub` is the sub-page selected, a sub-code `0x0000` to `0x3F7E` (EN 300 706 clause 9.3.1.2), or `0x3F7F`, "no particular page sub-code" (clause 9.6.1), when the viewer keyed the page's number alone or followed a link or bookmark that names no sub-page. A value with a bit outside the sub-code's thirteen is a protocol error; with `page` 0 it is `0x3F7F`.
- The **page parameters** are what follows `?` in the fragment of the address selected (`SERVER.md` section 4.6), as written and without the `?`: printable ASCII with no `#`, at most `MAX_PAGE_PARAMETERS` (8,000) bytes, and none when the address has none. With `page` 0 there are none. Anything else is a protocol error. They belong to this one selection: the program receives them with it, and a SELECT that does not carry them leaves them behind (REQ-1693 item 6, DEC-1715).

**What the tab is then sent and shows** (DEC-1500, DEC-1526, REQ-1502). Every sub-code a page has is one of its sub-pages, all of them peers; sub-code 0000 beside others is the page's own content, and the page's order is ascending sub-code, 0000 first when present. With `sub` `0x3F7F` the tab shows the page's **first** sub-page in that order, and that sub-page then is the selection, exactly as if the viewer had chosen it: the channel answers with it, and stepping goes on from it. With a sub-code the tab shows that sub-page alone and is sent only it and its changes, while the page's other sub-pages change, until the tab selects something else. Stepping to the next or previous sub-page, by the keys, the remote, the arrows or the sub-page list (section 7.9), is a selection of that sub-code; nothing else is sent. Sub-pages are never sent with their page, and **nothing rotates on a live channel:** the sub-page shown changes only when the viewer selects another, or when the channel's program moves the tab, which is itself a selection. A broadcast recording played back keeps the broadcast's own behaviour.

It is sent whenever the connection's selection changes: a page keyed or followed by a link, a sub-page stepped to or chosen from the list; at the start of each session, after HELLO (and after RESUME), when the tab shows a page of the channel, so a reconnection is sent its page again; and with page 0 when the tab leaves the channel's pages. It is sent whatever the focus, and focus never changes it. It is the only message that names a selection: a receiver that does not set SELECT has no selection, and is sent no page. It is sent only when both sides set SELECT (section 6.2), counts no input units, and is held to the rate as other events are (section 8).

**RESUME**, an extension (`0x45`): `uv` length, then the session's `token` (16 bytes, `TOKEN_BYTES`) and `acked` u16 big-endian, the last acknowledgement the receiver took; exactly 18 bytes of payload. It follows HELLO in a reconnection's first message, when the receiver asks to resume its session (section 6.4); a channel that does not know it skips it, and so begins a new session. It counts nothing.

**MOUSE and WHEEL.**
- `flags` bits 0–1: MOUSE action, 0 press, 1 release, 2 move, 3 gone (unused in WHEEL); bit 2: `px`, `py` present; bit 3: `mods` present; MOUSE's bits 4–5: the device, 0 a mouse or trackpad, 1 touch, 2 a pen, 3 reserved and a protocol error, set only when both sides set TOUCH and otherwise 0 (REQ-RCH-042); bits 6–7 (4–7 in WHEEL) a protocol error.
- `button`: on press and release, 0 left, 1 middle, 2 right, 3 back, 4 forward, 5 and up others; on move and gone, a bit mask of the buttons held.
- **Gone** (action 3, `RETURN-CHANNEL.md` decisions D and J, REQ-RCH-034, REQ-RCH-046): the pointer has gone and nothing it held was pressed. It goes when the pointer leaves the open page or keys stop going to the channel, after the waiting move (section 9.8), and when the system or the receiver cancels a contact (a gesture from the screen's edge, a call, a palm rejected, the receiver's own gesture taking it). `button` is the mask held, `col` and `row` the last position sent; what it held is released **without a click**, and a channel must not act on it as on a release. It counts no input units.
- `col`, `row`: the character cell, from the top left of the page: columns 0 to 39, rows 0 to 24, and a value beyond them is a protocol error (a page is always 40 by 25, DEC-1636, REQ-1643). `px`, `py`: the dot of the page image from the same origin, 12 to a cell across and 20 down; sent whenever the receiver knows them. Units (REQ-RCH-054): a cell and a dot are counted from 0 at the top left; a dot is the page image's own pixel at the size the receiver draws it, 12 by 20 to a cell whatever the screen's scaling, so a channel never needs the display's; a wheel's delta is in 1/120ths of a line.
- `dx`, `dy`: scroll in 1/120ths of a line, positive right and down. A wheel that moves in notches sends at least a whole line (120) a notch: macOS reports a slow notch as a tenth of a line, and a channel that moves a line at a time would need ten. A faster notch keeps the system's acceleration; a trackpad's continuous scrolling is sent as it comes.

**PASTE** is the whole paste as one event. It may contain control characters: the channel treats it as data, never as keystrokes. A paste longer than `MAX_PASTE` is cut at a character boundary.

**COMPOSE**: `cursor` is a code-point offset into the preedit string.

**RESIZE** gives the page's text area in cells and the page image in pixels as the receiver draws it: a teletext page is always 40 by 25 cells (DEC-1636), and a larger size is a protocol error, so RESIZE changes only when the drawn size does. Pixels are 0 when unknown.

**HELLO**'s `agent` is the receiver's user agent string, as the engine's REQ-WEB-031 defines it (`NeoTeletext/0.1 (macOS)`, or `product/version (platform) neoteletext/version` for another program on the engine). It is present when `caps` has the AGENT bit (section 6.2), and is sent only over a transport without HTTP, a serial line for instance: over the push WebSocket the channel already has it from the upgrade's `User-Agent` header, so it is not sent twice.

### 5.5 KEY

The stamp, `flags` u8, `key` uv, `mods`? u8, `text`? str (at most `MAX_KEY_TEXT`, 32 bytes), `base`? uv

| `flags` bit | Meaning |
|---|---|
| 0–1 | Action: 0 press, 1 repeat, 2 release |
| 2 | F: `key` is a functional code (section 5.6), not a code point |
| 3 | M: `mods` present (omitted when 0) |
| 4 | T: `text` present: the key produced text |
| 5 | B: `base` present: it differs from `key` |
| 6 | L: lost, on a release only: the key did not come up, the page lost the input (section 8 rule 3). A protocol error with any other action |
| 7 | Reserved: a protocol error when set |

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
4. **Dead keys.** A dead key (an accent pressed before its letter) sends no text: it sends KEY with the functional code of `Dead`, and `base`; the key after it sends the composed character as text (`´` then `e` sends `é`), or, when the two do not compose, both characters, as the layout gives them.
5. **AltGr is a level shift, not a modifier.** A character typed with AltGr (the right Alt key of European layouts, `AltGraph`) is sent as KEY with that text and no modifiers. A receiver on a system that reports AltGr as Control and Alt held together (Windows) MUST NOT report it so: when a key with Control and Alt both held produces printable text, it carries that text and no modifiers. AltGr itself is the key `AltGraph`.
6. **Input methods.** Chinese, Japanese, Korean and other input methods compose in the receiver: their preedit goes as COMPOSE, and what they commit as text. Their own keys (`KanaMode`, `HangulMode`, `HanjaMode`, `Convert`, `NonConvert` and the rest of the W3C names) have functional codes from 128 and go as KEY when the receiver passes them on.
7. **`key` follows the layout; `base` follows the position.** A character key's `key` is the unshifted character of the active layout (`я`, `ф`, `a`); `base` is the character the same physical key has on a United States layout (`z`, `a`, `q` on AZERTY's `a`). A channel binds a letter by `key` and a position (a game's movement keys) by `base`, so both work on any layout, including after the viewer switches layout.
8. **Digits.** The keypad's keys are their functional codes, with their characters as `text`. A layout that types native digits (`٣`, `३`) sends those characters; a channel that selects pages by number (section 9.4) SHOULD take the decimal digits of any script, Unicode's `Nd` characters, as the digits 0 to 9.
9. **Lock states and layout changes** send nothing of their own beyond the lock bits in `mods`: the protocol has no event for the layout, and a channel learns of a change only from what is typed, so the viewer's choice of language is never announced.
10. **Phones.** A phone keyboard's text, in any language its keyboard offers, is text under the same rules.

### 5.8 Size

Every key goes as KEY, with its text, since decision E.125 (REQ-RCH-029); raw text is only an input method's or a phone's.

| Input | Bytes | Size |
|---|---|---|
| `a` pressed | `FF 01 80 02 00 10 61 01 61` | 9 |
| `a` released | `FF 01 80 02 00 02 61` | 7 |
| `a` released because the page lost the input | `FF 01 80 02 00 42 61` | 7 |
| `é` committed by an input method | `C3 A9` | 2 |
| Focus lost | `FF 06` | 2 |
| Enter pressed | `FF 01 80 02 00 04 02` | 7 |
| Up pressed | `FF 01 80 02 00 04 09` | 7 |
| Red (Fastext) pressed | `FF 01 80 02 00 04 5C` | 7 |
| Control-C pressed | `FF 01 80 02 00 08 63 04` | 8 |
| Page 100 selected | `FF 40 04 80 02 FF 7E` | 7 |
| Page 302, sub-page 0002, selected with the page parameters `a=1` | `FF 40 06 82 06 02 61 3D 31` | 9 |
| Click at column 10, row 5 | `FF 02 80 02 00 00 00 0A 05` | 9 |
| The same, with its dot (120, 100) | `FF 02 80 02 00 04 00 0A 05 78 64` | 11 |
| A move to the dot (121, 100), no button | `FF 02 80 02 00 06 00 0A 05 79 64` | 11 |
| The pointer gone, from column 10, row 5 | `FF 02 80 02 00 03 00 0A 05` | 9 |
| Wheel one line down at column 10, row 5 | `FF 03 80 02 00 00 00 F0 01 0A 05` | 11 |
| HOVER, entering the control at column 2, row 20 | `FF 43 06 80 02 00 00 02 14` | 9 |
| A tap: the first finger down, at column 10, row 5 (RCH-055) | `FF 02 80 02 00 10 00 0A 05` | 9 |
| A second finger down, at column 11, row 5 | `FF 44 07 80 02 00 00 01 0B 05` | 10 |
| Two fingers moving, in one write: the first (dot 121, 100) and the second (dot 133, 100) | `FF 02 80 02 00 16 01 0A 05 79 64`, `FF 44 0A 80 02 00 06 01 0B 05 85 01 64` | 11 + 13 |
| RESUME, after HELLO | `FF 45 12`, the token, the acknowledgement | 21 |

Each example is on page 100, sub-code 0000, whose stamp is `80 02 00`. On a sub-code of 128 or more the stamp is a byte longer.

The version-1 key record took 14 bytes for every key.

## 6. Negotiation

### 6.1 The session

1. When the push WebSocket of a channel that declares input opens, the receiver sends HELLO with version 5 and the capabilities it has. Version 3 (31 October 2026, DEC-1538) added the stamp to the input events. Version 4 (31 October 2026, DEC-1689) added the REDIRECT record and ended a cursor record's moving a viewer. Version 5 (1 November 2026, DEC-1715) adds page parameters to SELECT, so a channel and a receiver of different versions would disagree on what SELECT holds: both sides speak 5, and there is no compatibility path.
2. The channel answers with WELCOME (section 7.2): the version it speaks and the subset of the capabilities it will use. A channel that cannot speak the version closes the connection.
3. Then the receiver sends RESIZE, FOCUS_IN or FOCUS_OUT, and SELECT when it shows a page of the channel; and from then on the viewer's input.
4. The receiver sends no input before WELCOME. A channel that has not answered within `WELCOME_TIMEOUT` (10 s) is taken not to take input, and the receiver says so.
5. **A reconnection is a new session,** unless both sides set RESUME and the channel still holds the session (section 6.4): HELLO again, nothing held, the input count from zero. The channel pushes the selected page again when it receives SELECT. A resumed session goes on as section 6.4 says.

### 6.2 Capabilities

`caps` is a bit set of what a receiver can do. Bits 0 to 15 were input modes until 27 October 2026 (section 6.3): they are reserved, never set, and ignored when a peer still sets them. The capabilities are:

| Value | Capability | Meaning |
|---|---|---|
| 65 536 | — | Retired: PAGE, until 31 October 2026 (DEC-1538). Never set, and a protocol error when set in HELLO or WELCOME. |
| 131 072 | CURSOR | The receiver draws the channel's cursor record. |
| 262 144 | — | Retired: ECHO, provisional echo, until 28 October 2026 (the engine's decision E.134). Never set; a peer that still sets it is not refused, and the bit is ignored. |
| 524 288 | AGENT | HELLO carries the receiver's user agent string (section 5.4); in HELLO only, never in WELCOME. |
| 1 048 576 | TOUCH | The receiver sends touch: MOUSE's device bits and TOUCH (section 5.4, REQ-RCH-041 to REQ-RCH-043). Without it touch goes as the mouse, the first contact alone. |
| 2 097 152 | RESUME | A lost connection's session may be resumed (section 6.4, REQ-RCH-013): WELCOME carries the session's token, and a reconnection's first message carries RESUME after HELLO. |
| 4 194 304 | SELECT | The receiver shows teletext pages and sends SELECT, the connection's selection (section 5.4); a channel that sets it sends the one sub-page selected, never a page's sub-pages together (DEC-1500). |

A sender uses a new flag bit, field, core type or extension type only when both sides set its capability bit in HELLO and WELCOME. A receiver of the stream that sees an unknown flag bit set treats it as a protocol error.

### 6.3 No modes: everything is sent

Every event goes to the channel whenever keys go to it, and the channel ignores what it does not use. There is nothing to ask for and nothing to switch: no mode stack, no page modes (the owner's decision of 27 October 2026: "simplify all this remove the config", engine decision E.125). Until then a channel asked for each kind of input by a mode, as xterm's modes 1000 to 1003 do; those modes, the records that set them (PUSH_MODE, POP_MODE, PAGE_MODES) and a page's `IM` line are withdrawn.

- **Keys:** every press, repeat and release as KEY, with its `text` when it produced text and its `base` when that differs from `key`, the keys that only modify or lock included, and the dead key (section 5.7). A channel that only types takes `text` from presses and repeats.
- **The mouse:** every press and release over the open page, with the cell, the dot (`px`, `py`) and the modifiers held; every move that changes the dot under the pointer while it is over the open page, buttons held or not, at most 60 a second (section 9.8, REQ-RCH-030, as xterm's mode 1003); and gone when it leaves (section 5.4). The receiver still draws hover itself (section 9.7). The browser's modifier keeps a click the browser's (section 9.1). A link the page declares is the receiver's on every page, a page that takes input included: a click or tap on it follows it, and no press, release or contact on it goes to the channel (the owner's revision of 28 October 2026, "revise that decision - links must be acted upon by the client browser"). A drag begun off a link stays the channel's when it crosses one.
- **Touch and pens** (section 9.8): the first contact as MOUSE, button 0; further contacts as TOUCH; a pen as MOUSE with device 2, hovering where the hardware reports it.
- **The wheel:** over the page, as before.
- **HOVER:** as the pointer enters and leaves each control of the page (section 5.4).
- **COMPOSE:** an input method's preedit, as it changes.
- **Raw text:** what does not come from a key, an input method's committed text and a phone's.

**Why there are no modes.** A mode is configuration that every channel, page and receiver must get right, and a channel that forgot one silently lost input: a slider no one could drag because no one asked for MOUSE_DRAG. Sending everything costs a few bytes an event. Moves are bounded at 60 a second (section 9.8) and count nothing against the rate (section 8 rule 4), so they can never crowd out a key. **What a channel learns of the pointer** (REQ-RCH-038) is its position over the channel's own open page, its clicks, drags and moves, and the contacts on it, while keys go to it; nothing elsewhere: not over another tab, the browser's own controls or the strip, or another window, and nothing while keys do not go to it (section 11.3).

### 6.4 Resumption (decision B)

A WebSocket cannot resume: what was in flight when TCP died is lost silently. When both sides set RESUME (`RETURN-CHANNEL.md` decision B, REQ-RCH-013), a session outlives its connection, so no key is lost when a connection drops and none reaches the channel twice. Events are numbered implicitly, by the input count both sides already keep (section 7.1): the *n*th unit of the session is number *n*, and nothing is added to any event.

1. **The token.** A channel that sets RESUME in WELCOME gives the session a token, 16 bytes from its cryptographic generator, new in every WELCOME (section 7.2).
2. **The receiver keeps** every message of input units it sends, as sent, until an acknowledgement covers it (section 7.1), at most `RESEND_BYTES` (16,384) bytes and 256 messages. A message of no input units, a move, gone, HOVER or COMPOSE, is never acknowledged and never kept. When what is kept would pass either bound the session can no longer be resumed, and the next connection is a new session.
3. **The channel holds** a session whose connection was lost for at least `RESUME_HOLD_MS` (32 seconds, past the push connection's first five retries), with its input count taken: everything it has read of the session, which it passes to the channel program in order. It may drop it sooner, under load, and must drop it after it gives the session to another connection.
4. **On a lost connection** the channel releases every held key, button and contact (section 8 rule 3), resumed or not: a resumed session starts with nothing held.
5. **A reconnection's first message** is HELLO, with RESUME after it: the token and the last acknowledgement the receiver took. In a resumed session HELLO counts nothing, and the count goes on.
6. **The channel answers** with WELCOME (section 7.2): *resumed*, with the input count it had taken, when it holds a session of that token with no connection of its own, and the count taken is at or after the acknowledgement; otherwise *new*, and the session begins again from HELLO, as section 6.1 says, nothing of the old resent.
7. **The receiver sends again**, before anything else and in the order first sent, every message it keeps that came after the count taken, whole messages only; the count taken is always the end of a message it sent, and one that is not is a protocol error. Then RESIZE, the focus and SELECT as at the start of a session, so the channel pushes the selected page again, since pages pushed while the connection was down were lost.
8. **The channel drops** what it has already taken, so a message that reaches it twice is acted on once.
9. **The bounds.** The count is 16 bits and wraps, compared by RFC 1982 serial arithmetic, as the acknowledgement is; what may be kept, 256 messages, is far below half its range. A channel that does not set RESUME, or that answers *new*, keeps the rule of section 6.1: a reconnection is a new session.

The token is a secret of the connection, as the keys are: it goes only on the session's own push WebSocket, which is `wss` for any channel worth typing into (section 11.3).

## 7. The protocol: channel to receiver

Everything a channel says to a receiver beyond its pages is teletext: records of the audio profile's frame (the engine's REQ-AUD-003: profile version 2, a type byte, a big-endian 16-bit body length, the body, and a CRC-32 over the header and body) on data channel 12, a user-defined service of EN 300 708 clause 6.7.3.2, carried in 4/31 packets, which the audio receiver steps over. A channel sends them as binary push messages (packets), and a page file may carry a cursor as a `CU` line.

| Type | Record | Fragments | Section |
|---|---|---|---|
| 1, 2, 3 | The audio profile's OBJECT, DATA and CONTROL | any | the engine's `docs/spec/design/audio.md` |
| 4 | Cursor | one | 7.1 |
| 5 | Control (WELCOME) | one | 7.2 |
| 6 | Index | one or more | 7.5 |
| 7 | LOG | one or more | 7.6 |
| 8 | SET_COOKIE | one or more | 7.7 |
| 9 | LINKS | one or more | 7.8 |
| 10 | SUBPAGES | one or more | 7.9 |
| 11 | REDIRECT | one or more | 7.11 |

Every record type has a type of its own in the frame rather than a kind of the control record (decided 30 October 2026, TODO-1491): the control record is one fragment, 26 bytes of body, and the index, LOG, SET_COOKIE, LINKS, SUBPAGES and REDIRECT records need more; and a receiver that reads only some of the types skips the others by the type byte alone, before reading any field. Section 7.10 says how a record of more than one fragment travels and what a receiver does with a record it cannot use.

### 7.1 The cursor record (type 4)

A record of 16 bytes: profile version 2, type 4, body length 8 (big-endian), the body, and the frame's CRC-32.

| Body byte | Field | Range |
|---|---|---|
| 0–1 | page, big-endian | `0x100` to `0x8FF` |
| 2–3 | acknowledged, big-endian | the input count acted on, modulo 65 536 (below); 0 for none yet |
| 4 | row | 1 to 23, or 255 for no cursor (row 0 is the header, row 24 the Fastext row) |
| 5 | column | 0 to 39 |
| 6 | reserved | written 0, ignored when read (the echo width until decision E.134) |
| 7 | flags | 4 BLOCK (a block rather than a bar); 1 and 2 reserved, written 0 and ignored when read (ECHO and MASKED until decision E.134); others refused |

No cursor requires column and flags 0. A record that breaks any rule is refused whole. The cursor is optional, as a cursor is: a game sends none, or one with no cursor only to acknowledge.

A cursor record never moves a viewer, whatever page it names: the record says where the cursor is and what has been acknowledged, and it travels with every page frame, so one still in flight when a viewer selects another page names the page they left. A channel moves a viewer with a REDIRECT record (section 7.11).

**The input count** is how much input of the session the channel has acted on: each event counts one, each character of raw text counts one, and a PASTE counts one; but what is never acknowledged counts none (REQ-RCH-012, REQ-RCH-054): a move and gone, MOUSE's and TOUCH's, HOVER, COMPOSE and RESUME. HELLO counts one in a new session. The receiver counts what it sends the same way, and so knows which messages a resumed session sends again (section 6.4). The count wraps at 65 536 and is compared by RFC 1982 serial arithmetic: an older acknowledgement changes nothing, and one beyond what was sent is ignored.

**Where the acknowledgement goes** (`RETURN-CHANNEL.md` decision A, REQ-RCH-012). The channel says when it has handled an input; the acknowledgement may travel in the answer's own frame, the cursor record among the page's packets in one binary message, and goes alone only when the channel published nothing. A message of no input units is never acknowledged. A receiver takes a cursor record wherever it comes: alone, or in a message with the packets of the answer.

**The TTI `CU` line.** A page file may carry its cursor as `CU,row,column,width,flags[,acknowledged]`, decimal, for the page that holds it. The reader keeps the last such line and the writer writes it back; a line that cannot be read is reported and dropped. The engine's encoder does not turn it into a packet: a receiver reads it from the page it already has.

### 7.2 The control record (type 5)

A record whose body is one control message, encoded as receiver events are (`0xFF`, a type, its fields), at most 26 bytes, so the record with its 8 bytes of frame is the 34 bytes of one fragment.

| Type | Name | Fields |
|---|---|---|
| `0x01` | WELCOME | `version` uv, `caps` uv (a subset of the receiver's); with RESUME in `caps`, `session` u8 (0 new, 1 resumed, others a protocol error), `token` (16 bytes), and when resumed `taken` u16 big-endian, the input count the channel had taken (section 6.4) |
| `0x02` | (withdrawn) | Was PUSH_MODE. Reserved; a record of it is ignored |
| `0x03` | (withdrawn) | Was POP_MODE. Reserved; a record of it is ignored |
| `0x04` | (withdrawn) | Was PAGE_MODES. Reserved; a record of it is ignored |

Types `0x40` to `0x7F` are extensions with a length, skipped when unknown, as in section 5.4. A resumed WELCOME with every capability set is 26 bytes, the whole body; a capability above bit 27 would take a fifth byte of `caps` and needs a WELCOME of its own design.

### 7.3 Controls (column mode 00101)

A page says which of its cells it answers itself, its buttons and the rows of its lists, so that a receiver can show them as it shows links: a hand over them, and a look under the pointer (section 9.7). The declaration is part of the page, not a record beside it: a triplet in the page's own packets X/26, in column mode 00101, which EN 300 706 Table 29 reserves and every decoder skips. A page with controls therefore looks the same on every receiver, and its controls travel, are stored, coalesced and recorded with its rows, in a page frame, a `.t42` file or a TTI page's `OL,26` lines (the engine's decision E.127).

| Field | Bits | Meaning |
|---|---|---|
| Address | 6 | The control's first column, 0 to 39 |
| Mode | 5 | `00101` |
| Data D5–D0 | 6 | Its width, 1 to 40 cells, not past column 39 |
| Data D6 | 1 | Joined: this run continues the control on the row above, at the same column and width |

- **The row** is the active row: the Set Active Position (or Full Row Colour) triplet before it, as for every column triplet (clause 12.3.2). Rows 1 to 23 only.
- **One triplet is one control** on its row, so four buttons on a row are four triplets, separate even where they touch. A taller control repeats its triplet on each row below with D6 set.
- **Only the page's local enhancement data** declares controls, up to its first Termination Marker or Object Definition; an object declares none.
- **A triplet that breaks a rule is dropped and reported**, and the others are kept: a row outside 1 to 23, no width, a run past column 39, a cell already in a control, a joined run under no control of its column and width, or more than 32 controls (the engine's `MAX_CONTROLS`).

Four buttons on row 20, nine cells each, as transmitted (Hamming 24/18):

| Triplet | Value | Bytes |
|---|---|---|
| Set Active Position, row 20 | `0x0013C` | `60 93 80` |
| Control, column 1, width 9 | `0x04941` | `8f 94 89` |
| Control, column 11, width 9 | `0x0494B` | `dd 94 09` |
| Control, column 21, width 9 | `0x04955` | `24 95 89` |
| Control, column 31, width 9 | `0x0495F` | `76 95 09` |

A control is only where a click lands: the click still goes to the channel as MOUSE, at its cell, as every click over the page does (section 6.3), and the channel decides what it means. Declaring controls asks for nothing and lets the receiver do nothing it could not do before.

### 7.4 Pointer areas (withdrawn)

Withdrawn on 28 October 2026 (`RETURN-CHANNEL.md` decision E, REQ-RCH-037; the engine's decision E.133): column mode 01010 declared where a move with no button went, and with every move over the page sent (section 9.8) it asks for nothing. Column mode 01010 is reserved again, as EN 300 706 Table 29 has it, skipped by every decoder; a page that still carries the triplet declares nothing by it. The engine's `MAX_POINTER_AREAS` and decision E.128 are withdrawn with it.

### 7.5 The index record (type 6)

The channel's magazines and pages, as a program gives them in its `reply` and `index` messages (neoteletext-app-server's DEC-1482, REQ-1477): what fills a receiver's magazines, overview and contents view, and what a static channel's `contents.txt` gives (the engine's REQ-WEB-025). A live channel has no `contents.txt` (DEC-1467); its index comes as these records, at connection and whenever it changes.

**Integers are big-endian. Text** is a `u16` byte length then that many bytes of UTF-8, with no control character (U+0000 to U+001F, U+007F to U+009F) and at most 120 characters (`MAX_TITLE`, the engine's `contents::MAX_TITLE`), so at most 480 bytes.

The body:

| Bytes | Field | Range |
|---|---|---|
| 0–1 | `generation` | Any: the index's version. Every record of one sending of the index carries the same value; the next sending carries another (the sender counts it on by one, wrapping) |
| 2–3 | `part` | 0 to `parts` − 1: this record's place in the sending |
| 4–5 | `parts` | 1 to 2,030 (`USABLE_PAGE_NUMBERS` + `MAGAZINES`: a record for each page, and one for each magazine's name alone): the records of this sending |
| 6 | `magazine` | 1 to 8 |
| 7 on | `name` | text, 0 to 120 characters: the magazine's name; empty when it has none |
| then | pages | zero or more, to the end of the body, in ascending page number |

Each page:

| Field | Range |
|---|---|
| `page`, `u16` | `0x100` to `0x8FF`, of the record's magazine (`page >> 8` is `magazine`, magazine 8 written as 8), never a reserved number (mFD, mFE, mFF, 1BE, 1F0; EN 300 706 Annex A.10) |
| `subpages`, `u16` | 1 to 8,190 (`MAX_SUBPAGES`): how many sub-pages the page has |
| `title`, text | 1 to 120 characters |
| `section`, text | 0 to 120 characters: the heading the page is listed under; empty for none |

**Splitting.** A record holds one magazine's pages, as many as fit in 1,016 bytes of body (`MAX_BODY`, the audio profile's largest); a magazine with more goes on in the next record. The records of a sending are numbered 0 to `parts` − 1 in the order of their magazines and pages, so no page is in two records of one sending. The magazine's name is given in the first record of the magazine in a sending; the records after it in the same magazine and sending give an empty name, which keeps the name given. The largest page is 968 bytes (2 + 2 + 2 × (2 + 480)) and the fixed fields with the longest name are 489 (7 + 2 + 480), so a page may not fit beside a long name: a record may therefore hold no pages, and then carries only the magazine's name.

**Reassembling.** A receiver keeps the index it has and the sending it is receiving:
1. A record of the `generation` it is receiving, whose `parts` agrees with that sending's first record, adds its pages to the sending. A record of another `generation` begins a new sending, and the one in progress is abandoned.
2. Each page a record lists is shown at once with what the record says of it, added to the index or replacing what was there, so a partial sending already shows what it has.
3. When every `part` from 0 to `parts` − 1 of the sending has arrived, the sending is complete: it is the whole index, and every page and magazine it did not list is removed.
4. A partial sending removes nothing: a page is removed only by a complete sending that leaves it out.

**For a viewer,** a section begins wherever a page's `section` differs from the page before it, as `contents.txt`'s `s` lines do; the engine gives each record's pages to the port as `contents.txt`'s entries.

### 7.6 The LOG record (type 7)

A log line for the channel's author, as a TTI `LG` line holds one (the engine's REQ-INP-026 and decision E.109 as amended for DEC-1459): shown only in a developer's view, never on a page.

| Bytes | Field | Range |
|---|---|---|
| 0 | `level` | `E` (0x45, an error), `W` (0x57, a warning) or `I` (0x49, information) |
| 1–2 | `page`, big-endian | the page the line concerns, `0x100` to `0x8FF`, or 0 for none |
| 3 to the end | `text` | UTF-8, 1 to 200 bytes (`MAX_LOG_TEXT_BYTES`), with no control character and no bidirectional formatting character (REQ-INP-026) |

The record is at most 211 bytes of body and 219 with its frame, seven fragments; text is never split across records. A receiver passes on at most 16 LOG records (`MAX_LOG_LINES_PER_PAGE`) for each page frame it receives, and 16 before the first, and drops the rest, so that a channel cannot flood a console.

### 7.7 The SET_COOKIE record (type 8)

A cookie set while the connection is open (`SERVER.md` section 8.2). The body is one `Set-Cookie` header field's value, exactly as an HTTP response carries it after `Set-Cookie:` (RFC 6265bis section 4.1): `name=value` and its attributes (`Path`, `Max-Age`, `Expires`, `SameSite`, `Secure`, `HttpOnly`), separated by `; `.

| Bytes | Field | Range |
|---|---|---|
| 0 to the end | the line | 1 to 1,016 bytes (`MAX_BODY`) of printable ASCII, 0x20 to 0x7E |

- **The receiver** applies the line to its cookie jar with the same parser and the same rules as a `Set-Cookie` header of the push connection's own upgrade response, for the push connection's address: host-only, scoped to the channel's folder, stricter than RFC 6265bis as the engine's REQ-WEB-006 is. A line the jar refuses is reported as a refused cookie, as a header's is.
- **The sender** never writes the line by hand: the server builds it from the program's typed `cookie` message (its name, value, path, maximum age, same-site rule, and the secure and HTTP-only flags) with the engine's encoder, which refuses a name or value the parser would refuse.

### 7.8 The LINKS record (type 9)

A sub-page's TTI Link Extension links (the engine's Appendix E, `docs/spec/design/tti-link-extension.md`), which packets cannot carry (neoteletext-common's DEC-1495, REQ-1494): key links to other services, to addresses and to the web, page-number links (`LK`) and text links (`LT`). The record holds every Link Extension link of the sub-page, the key links to its own service too, so that the links a receiver holds are exactly the page's. The page's Fastext links and row 24 still travel in its own packets X/27/0 and X/24 (Appendix E rule 4).

**Integers are big-endian. A target** is a `u16` byte length then 1 to 8,004 bytes (`LINK_TARGET_BYTES`: the longest address, 8,000 octets by REQ-1661 and DEC-1668, and a `web:` mark) of printable ASCII with no space and no comma, in any form of Appendix E section E.1: `mpp`, `mpp:ssss`, `name:mpp`, `name:mpp:ssss`, an `http` or `https` address, or `web:` and such an address, read by the same parser as a TTI file's.

The body:

| Bytes | Field | Range |
|---|---|---|
| 0–1 | `page` | `0x100` to `0x8FF`: the sub-page's page |
| 2–3 | `sub` | `0x0000` to `0x3F7E`: its sub-code |
| 4 | `part` | 0 to `parts` − 1 |
| 5 | `parts` | 1 to 21, the most links a sub-page has (5 + 8 + 8): the records that carry the sub-page's links this time |
| 6 | `keys` | 0 to 5, then that many key links |
| then | `numbers` | 0 to 8 (`NUMBER_LINKS`), then that many page-number links |
| then | `texts` | 0 to 8 (`TEXT_LINKS`), then that many text links, and nothing after |

| Link | Fields |
|---|---|
| Key link (`LN`) | `key` u8: `R`, `G`, `Y`, `C` or `I`; `target`; `label` u8 length then 0 to 9 bytes of printable ASCII (at most 8 for a target in another service or at an address; none for `I`) |
| Page-number link (`LK`) | `number` u16, a page number `0x100` to `0x8FF` the page shows; `target`, never a `web:` one |
| Text link (`LT`) | `row` u8, 1 to 23; `column` u8, 0 to 39; `length` u8, at least 1, with `column` + `length` at most 40; `target` |

- **Bounds across the parts.** Over all the parts of one sending, a sub-page has at most five key links, each key once and at most four of them coloured, at most eight page-number links, each number once, and at most eight text links. A record that would break one is refused.
- **Splitting.** The links go in order, key links first, then page-number links, then text links, as many in each record as fit in the frame's largest body (`MAX_FRAMED_BODY`, 8,184 bytes); a link is never split, and its largest, a key link, is 8,016 bytes. The most links a sub-page has, about 168 KB at their longest, take at most 21 records of up to 237 packets each, and cost that much every time the sub-page is sent; a typical page's take one record.
- **When it is sent, and what a receiver does.** The server sends a sub-page's LINKS records straight after that sub-page's page frame, every time it sends the sub-page, whenever the sub-page has any Link Extension link. Part 0 replaces every link the receiver held for that page and sub-code; later parts add to it. A sub-page sent without a LINKS record has no Link Extension links: a receiver drops those it held for it. A receiver reads the links exactly as it reads a TTI file's `LN`, `LK` and `LT` lines, by Appendix E's rules (E.2), and puts them in the same store.

### 7.9 The SUBPAGES record (type 10)

A page's list of sub-pages (neoteletext-common's DEC-1500, REQ-1503): sub-pages are never sent with their page, so a receiver learns a page's list from this record, for the list, the count, the view's place ("3/12") and stepping. It is never the sub-pages themselves. The server sends it when a view selects the page or one of its sub-pages and the connection does not hold the list's current version, and again whenever the list changes while a view shows the page.

**Integers are big-endian.** The body:

| Bytes | Field | Range |
|---|---|---|
| 0–1 | `page` | `0x100` to `0x8FF` |
| 2–3 | `version` | Any: the list's version, the same in every record of one sending; it changes whenever the list changes |
| 4–5 | `part` | 0 to `parts` − 1 |
| 6–7 | `parts` | 1 to 8,190: the records of this sending |
| 8–9 | `count` | 1 to 8,190 (`MAX_SUBPAGES`): the page's sub-pages, the same in every record of the sending |
| then | entries | one or more, to the end of the body, in the page's order |

Each entry: `sub` u16, a sub-code `0x0000` to `0x3F7E` with no bit outside the thirteen a sub-code has, each at most once in the list; then `title`, a `u8` byte length and 0 to 160 bytes of UTF-8, at most 40 characters (a teletext row), with no control character; empty for none.

- **Splitting.** The entries go in the page's order, as many in each record as fit in 1,016 bytes of body (`MAX_BODY`, the audio profile's largest), at least six, and an entry is never split; the records are numbered 0 to `parts` − 1 in that order.
- **Reassembling,** as the index record (section 7.5): a record of another `version` of the page begins a new sending; a sending is complete when every part has arrived and its entries number `count`, and then it is the page's whole list. A partial sending shows what it has and removes nothing; a complete one replaces the list held.

### 7.10 Records of several fragments, and records a receiver cannot use

- **Fragments.** A record of more than 34 bytes is cut into fragments of 34 bytes, the last padded with zeros, at most 241 fragments (`MAX_FRAMED_RECORD`, 8,192 bytes, so that a record can hold an address of 8,000 octets with the fields around it; the audio profile's own records stay within 1,024 bytes, `MAX_RECORD`), as the audio profile's records are (the engine's REQ-AUD-007): each fragment one 4/31 packet with the record id, its index, and the CRC-16. The record id counts every record of the service, whatever its type, so two records in flight on one service never share an id. A channel sends a record's fragments in order, fragment 0 first, in one binary message or in consecutive ones; a receiver reassembles them by record id, and knows the record's length, and so its fragments, from fragment 0's frame header.
- **A record a receiver cannot use** (a frame whose CRC-32, version or length fails; a type it does not know; a field outside its range; text that breaks its rule; bytes after the last field) is discarded whole and nothing of it applied, and each of its packets is counted as an invalid packet (neoteletext-common's REQ-1462), without closing the connection; a LINKS record refused leaves its sub-page shown with no Link Extension links. A record of a type the receiver does not read is skipped, not counted.

### 7.11 The REDIRECT record (type 11)

A channel's redirect (DEC-1683, DEC-1689, REQ-1688): what a channel's program sends to move a connection's viewer to another page of the channel, or to another channel. It is the only thing that moves a viewer (section 8 rule 8). An HTTP redirect from a web server (REQ-701) is another thing, and is not carried here; where the two are near, "page redirect" means this record's page form.

**Integers are big-endian.** The body begins with one byte:

| Bytes | Field | Range |
|---|---|---|
| 0 | `form` | 0, a page of this channel; 1, an address |

The page form, 5 bytes of body and one fragment:

| Bytes | Field | Range |
|---|---|---|
| 1–2 | `page` | `0x100` to `0x8FF`, never a reserved number |
| 3–4 | `sub` | `0x0000` to `0x3F7E`, a sub-code with no bit outside the thirteen a sub-code has, or `0x3F7F` for the page |

The address form:

| Bytes | Field | Range |
|---|---|---|
| 1 to the end | `address` | 1 to 8,000 bytes (`MAX_ADDRESS`: the longest address of REQ-1661, its fragment included) of printable ASCII with no space: an `http` or `https` address the engine's strict address parser accepts, and after it, optionally, `#` and what follows it, which the receiver's address rules judge (REQ-505) |

- **The page form.** The server sends the record and records the page as the connection's selection, exactly as it would a SELECT, and the program is then sent `selected` for it. The receiver opens that page and sub-page, whether or not its page has the focus, since a selected page is active whatever its focus (REQ-1553), and sends SELECT for it.
- **The address form.** The server sends the record and changes nothing else: the connection's selection stands until the receiver leaves. A receiver that opens channels puts the address through its own address rules, which alone decide: a redirect leads only to an `http` or `https` address, never a local file, a `web:` hand-off or the browser's own pages. It shows the redirect notice (REQ-1686) and then opens the address as another channel. A receiver that cannot open channels says that the channel redirected and to where, and stays.
- **What a channel cannot do with it.** The record moves a viewer and nothing else. The viewer's own choice overrides it, and a receiver bounds how many redirects it follows in a row with no input from the viewer (REQ-1688 item 6).

## 8. Behaviour

1. **One message per event, never held back** (REQ-RCH-010). Each event is its own message, written as it happens; messages already waiting at the same moment are written together, in one write and one TLS record where the transport allows. The receiver keeps only the latest of a contact's unsent moves (section 9.8) and sums unsent wheel deltas; nothing else is merged or dropped.
2. **Order** is the stream's order.
3. **Held input** (REQ-207). A key or button is held when it went down and has not come up. It is released whenever the page loses the input, and releasing never deselects the page: it stays selected and active.
   - **The signals.** FOCUS_OUT releases every held key, button and contact. A pointer's gone releases the buttons and the contact it held, without a click. A change of selection, SELECT page 0 included, or the program moving the tab, releases everything. A connection closing or dropping, or a session ending without resumption, releases everything.
   - **The receiver's part.** Before the FOCUS_OUT or SELECT that ends the input, a receiver that knows what is held sends a KEY release for each held key with the L flag set (section 5.5), stamped with the page that held it, and gone for the pointer and each contact (section 5.4). Gone is a lost release by its own action, so MOUSE and TOUCH have no L flag.
   - **The channel's part.** A channel keeps what each connection holds. On a signal it treats whatever is still held as released, itself, and acts on nothing else. A receiver may have sent nothing: a dropped connection cannot, and a terminal that reports no releases never does.
   - **The mark.** Every such release, the receiver's or the channel's, is marked as lost input, and reaches a channel's program marked so (`lost: true`), so a game can tell "the player let go" from "the player left". A real key-up or button-up carries no mark.
4. **The rate.** A receiver sends at most `MAX_PER_SECOND` (120) input units in any second, counted as the input count counts them, and never drops a release, a key's, a button's or a contact's up, to keep to it. 120 is qrkeyboard's relay limit. A move, gone and HOVER count nothing: a move goes at most 60 a second and only when the dot changes (section 9.8); a HOVER only as a control is crossed. So the pointer can never cost a key. COMPOSE counts nothing in the input count, since it is never acknowledged, but is held to the rate as one unit, since nothing else bounds it.
5. **Protocol errors** close the connection, on either side.
6. **Bounds.** A message over `MAX_MESSAGE`, a field over its maximum, a varint over 5 bytes or not minimal: a protocol error.
7. **Nothing waits on a timer** but the pointer's moves (section 9.8). A receiver sends an event when it happens and draws what comes back when it arrives (decision E.97, REQ-INT-008, REQ-RCH-011); the heartbeat (a ping after 25 s of silence, a pong within 10 s) and the round trip's ping (section 9.2) are the push connection's own.
8. **A channel moves a viewer with a REDIRECT record** (section 7.11), and nothing else moves one: a cursor record never does, whatever page it names. A redirect to a page of the channel opens that page in the receiver, as a terminal shows what its host sends, and the receiver then sends SELECT for it, since the move is a selection. A redirect to another channel's address is followed after the redirect notice (REQ-1686). It needs no action from the viewer (DEC-1683), and the viewer choosing a page overrides it.
9. **Terminal programs.** A channel that feeds an ordinary terminal program translates events into whatever encoding that program asked for.

## 9. The receiver's side

### 9.1 When input goes (NeoTeletext)

The receiver sends the viewer's input only for the connection's selected page, and only while that page is focused (REQ-1554). While the tab shows "Loading", "Connecting" or nothing of the selected page, no input is sent. Losing either focus never sends SELECT and never stops the page's updates (REQ-1553).

**The keyboard focus.** Keys go to a channel only while all of these hold: the tab is the one in front; the page selected in it is the channel's; the channel declares input over a WebSocket whose session has been welcomed; the window has the focus; and the viewer is not editing the address. Then every key goes except the browser's own: those with the browser's modifier (Command on macOS, Control-Shift elsewhere), and the strip, the overview and a background tab, which never take keys, and the magazines and the page list, which take the arrows from a click on them until a click elsewhere (the browser's decision 105). Command-Escape (Control-Shift-Escape elsewhere) leaves the page; plain Escape is the channel's.

Whatever the keys do, the trusted core sends SELECT on a tab's own connection whenever the tab's page or sub-page changes, and SELECT with page 0 when the tab leaves the channel's pages (section 5.4); each tab has its own connection (DEC-1527).

When keys start going, the trusted core sends FOCUS_IN. When they stop, whether another tab came to the front, the window lost the focus, the address is being edited or another part of the browser took the keys, it sends FOCUS_OUT, so the channel lets go of a key held as the viewer left (section 8 rule 3), and FOCUS_IN when they come back. The page stays selected and active through all of it.

**The pointer focus.** Every press, release and move over the page goes to the channel while keys go to it (section 6.3), moves paced as section 9.8 says; a click with the browser's modifier is the browser's. A link the page declares is the browser's on every page: a click on it follows it, and nothing pressed on it goes to the channel (section 6.3). When the pointer leaves the page, or keys stop going, the waiting move and then gone (section 5.4). The wheel goes to the channel while the pointer is over the page. Outside the page the browser's own actions apply and nothing goes to the channel: the wheel steps to the next or previous page, which is a new selection, sent with SELECT.

**Touch** (REQ-RCH-047, REQ-RCH-048). While keys go to the channel every contact on its page is the channel's, two fingers and a pinch included; the browser's gestures, a pinch to zoom and a swipe to step sub-pages, act on pages that do not take input and outside the page, and the system's gestures from the screen's edges are the system's. The browser zooms a page that takes input with its own controls. A link is the browser's on every page: a contact that begins on a link the page declares follows it when it lifts there, and goes to the channel not at all (section 6.3).

**Paste and composition.** The browser's paste shortcut pastes into the page as PASTE while keys go to it. The window's input method stays enabled while typing; its preedit goes as COMPOSE, and its committed text as text.

### 9.2 The strip

The trusted strip says "Keys go to *host*" while keys go, with "Not secure" on a plain `ws://` socket and the round trip of the push connection itself, measured by WebSocket ping and pong at most once a second while keys go (REQ-RCH-016), not from acknowledgements, which measure only the channel's receipt. No page can draw into the strip.

### 9.3 Cursor

- The interface draws the cursor as an overlay in a style no page can draw: an amber bar 0.15 of a cell wide, blinking with a half period of 530 ms, or, with BLOCK, an amber outline 0.12 of a cell thick, so the character under it shows. Never an underline (decision 42).
- **No echo.** The receiver draws nothing of the viewer's keys: what is typed shows as the channel draws it on its page. Provisional echo, the viewer's own keys drawn at once in amber until the channel acknowledged them, was withdrawn on 28 October 2026 at the owner's word (the engine's decision E.134), with its capability, its flags and its width.
- The cursor is shown only on the page it names, only while keys go to its channel.

### 9.4 Page selection

A channel that takes input selects pages by videotex's convention, which it implements: `*nnn#` goes to a page, `#` to the next, `*#` to the one before, `*00` shows the page again; three plain digits where the channel has no other use for them. The receiver interprets none of it: it sends the keys.

A receiver's own selections are ordinary SELECTs (section 5.4). The wall of pages selects nothing while it is shown, drawing from the tab's cache of page source; it fills a missing visible tile by an ordinary page load, one at a time in screen order, and then sends SELECT with page 0 (DEC-1552).

### 9.5 Characters a page cannot show

The receiver sends the viewer's character whatever its script, and draws nothing of it (section 9.3). What the channel draws is the channel's choice: the nearest character of the page's sets, a placeholder, or a page in another set (the engine's area CHR).

### 9.6 `neottx view`

Every key goes while the channel takes input, Control-C included; Control-] leaves and returns. With a terminal that reports releases (the Kitty keyboard protocol), it sends releases too; otherwise a press only. It sends PASTE from bracketed paste, FOCUS from the terminal's focus events, and SELECT when the viewer opens a page, the page with `0x3F7F`, or a sub-page with its sub-code. It stamps every input event with the page and sub-code it is drawing, and sends none while it draws nothing of the page. Keys stop going when the terminal loses the focus or after Control-], and it sends FOCUS_OUT then, with a lost release of each held key where the terminal reports releases.

### 9.7 Controls and links under the pointer

While keys go to the open page's channel, so that a click goes to it, the page's controls (section 7.3) are shown as links are: the pointer is a hand over them. A control or a link under the pointer takes a look the receiver draws from the page's own colours, with what Level 2.5 already does to them (the engine's decision E.127):
- **Hover:** each colour of its cells becomes the same entry of the adjacent CLUT, the pairing of the Additional Flash Functions' colour flash (CLUT 0 with 1, 2 with 3). A page chooses its hover colours by defining CLUTs 2 and 3 in packet X/28/0 Format 1 and drawing its controls from them; with Table 30's colours, hover is the half-intensity colour of CLUT 1.
- **Pressed,** while a button is held down on it, or a contact is on it: the hover colours with foreground and background exchanged, as Invert Colour exchanges them. A finger gives no hover look (REQ-RCH-049).

The receiver draws both itself, at once, and sends nothing for them: the looks need no message, and a page lights under the pointer without the channel drawing a copy of it for each viewer. While keys do not go to the channel a page's controls are not shown, since a click on them would not reach it.

### 9.8 The pointer's moves and touch

`RETURN-CHANNEL.md` section 4 is the design; `neoteletext-input`'s `pace::Pacer` and `contacts::Contacts` implement it for every receiver.

- **Sixty a second** (REQ-RCH-031). At most one move in each period of 1000/60 ms (`MOVES_PER_SECOND`). While moves follow each other, the *k*th period ends at the time of the move that began the run plus *k* × 1,000,000 / 60 µs, counted exactly, so the average is exactly 60 a second with no drift.
- **At once if it can, the latest kept** (REQ-RCH-032). A move that comes 1000/60 ms or more after the last move sent goes at once, and begins a run; one that comes sooner waits in one slot, replacing any position waiting there, and goes when 1000/60 ms have passed since the last. An unchanged position does not go again, and nothing runs while the pointer is still: no timer while the slot is empty.
- **Order** (REQ-RCH-033). Before any other event is written, the move waiting in the slot is written first, so a release never comes before the move that ended the drag.
- **Never behind the network** (REQ-RCH-035). The part that writes to the socket writes a move only while the socket's unsent bytes are under a bound (the engine's `PUSH_UNSENT_BOUND`, 1 KiB), holding it otherwise in one slot a contact that newer moves replace; any other event first writes the held move, then itself, and never waits behind a move.
- **Touch** (REQ-RCH-041 to REQ-RCH-046, REQ-RCH-049, REQ-RCH-050). The first contact down on the page, while no other is down and no mouse button is held, goes as MOUSE: a press of button 0 as it touches, moves with button 0 held, a release as it lifts, device 1 when both sides set TOUCH. Every further contact goes as TOUCH with the lowest free `id` of 1 to 9, kept until it ends; an eleventh sends nothing until one ends; without TOUCH only the first goes. A contact's beginning and end are written the moment the system reports them, never held to recognise a gesture. Each contact's moves follow the rules above with a slot and a pace of its own, and the moves of several contacts waiting at one moment are written together; only the latest of the system's coalesced samples is kept, and no predicted position is sent. A cancelled contact goes as gone. No move goes for a finger before it is down or after it lifts. A pen goes as MOUSE with device 2: touching is button 0, its barrel button button 2, hovering, where the hardware reports it, moves with no button and HOVER. Pressure, tilt and a contact's size are not sent.
- **Trust** (REQ-RCH-036, REQ-RCH-053). The trusted part of the receiver paces, numbers the contacts, keeps their slots and alone encodes; the drawing process passes each change of the dot and each system touch as an intent, and cannot raise the rate, invent a contact, move or end one not begun, or pass `MAX_CONTACTS`.

### 9.9 Where the pointer is, at any size the page is drawn

A receiver draws a page at whatever size its window, screen or full-screen view allows: smaller than the page image, the same, or many times larger, and on a display whose own scaling (a high-density screen, a system zoom) the receiver may not even choose. Every position it sends is in the page's own units, never the screen's, so a channel answers the pointer the same way at every size and never needs to know the size (section 5.4: RESIZE carries the drawn size as 0, unknown, in NeoTeletext).

- **The units.** `col`, `row` is the character cell, columns 0 to 39 and rows 0 to 24. `px`, `py` is the dot of the page image, 12 dots to a cell across and 20 down, 480 by 500, from the page's top left. The dot is always inside the cell: `px` / 12 = `col` and `py` / 20 = `row`, rounded down.
- **The conversion is the receiver's.** It takes the pointer's position in the units its window system gives (in NeoTeletext the window's logical pixels, the system's scaling already divided out), subtracts the top left of the rectangle where the open page's image was last drawn, and scales by the image's size in dots over the rectangle's size, rounding down: `px` = ⌊(*x* − *left*) × 480 / *width*⌋, and the same down. The rectangle is the page image alone, at the image's own proportions; the border of the screen colour around it, the space beside it and the receiver's own controls are not the page.
- **Only the open page, at rest.** Positions go only for the page keys go to, while it is drawn where the receiver will keep it: not over a page still zooming, sliding to the next or shown as one of many, where a cell under the pointer would be a cell of a moving picture. A pointer that leaves the page, onto the border, the receiver's controls or another window, or a page that stops being the one at rest, gives the waiting move and then gone (section 5.4).
- **Drawn larger.** Several screen pixels show each dot. A move within one dot changes nothing and is not sent (section 9.8), so a page drawn larger costs no more moves; moves stay at most 60 a second at every size.
- **Drawn smaller.** One screen pixel covers more than one dot, so some dots cannot be pointed at and a move may step several dots at once: at half the image's size, two. The cell stays exact until a cell is smaller than a pixel. **A channel tests where a click landed by its cell**, and treats the dot as finer detail that is exact only when the page is drawn at the image's own size or larger; and a channel copes with no dot at all, since a receiver that knows only cells, a terminal, sends `px`, `py` absent (flags bit 2 clear).
- **One dot at a boundary.** The receiver draws the image by sampling each screen pixel at its centre, and rounds the pointer's position down; at a size that is not a whole multiple of the image, the dot sent may be the neighbour of the one drawn under the pointer's tip. It is never another cell's dot, since the cell is computed from the same position.
- **Double height and double size.** The cell sent is the grid cell under the pointer, not the cell where a double-height or double-size character begins; a channel whose control spans two rows answers both. Controls (section 7.3) and HOVER give a control's first cell.
- **Touch.** A contact's position is the point the system reports for it, converted the same way. On a phone a page's cell is drawn some 9 points wide, smaller than a fingertip: that is teletext's own resolution, which the receiver answers by zooming the page with its own controls, never by enlarging what a channel sees.
- **Checked by the trusted part.** The drawing process converts the position, untrusted; the trusted part of the receiver refuses a cell outside the page, and a dot outside the image or outside its cell, before anything is encoded (REQ-INT-127), so a channel never receives a position no pointer could have had.

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
| Keys go somewhere else | The push address is fixed by the channel's own address; the fetcher takes no address; nothing in the protocol names one. |
| A keylogger on a plain connection | `ws://` is "Not secure" in the strip; `wss` is the default for any channel worth typing into. |
| The channel tracks the pointer | It learns the pointer's position over its own open page, its clicks, drags and moves at most 60 a second, and the contacts on it, while keys go to it (REQ-RCH-038): the reading behaviour of that page. Nothing of the pointer anywhere else: not over another tab, the browser's own controls or the strip, or another window, and nothing while keys do not go to it (section 6.3). |
| Fingerprinting by keyboard layout | `base` names a key position, not a layout's name; lock states only in `mods`, as any terminal sends them. There is no clock: the channel learns typing rhythm only from arrival times, which the network blurs, and no physical key code. |
| A paste runs as keystrokes | PASTE is one length-prefixed event the channel treats as data; it cannot break out of itself. |
| A flood from the channel | Pushed rows are coalesced to the display rate; records are bounded and checked; a protocol error closes the connection. |
| A flood from a receiver | 120 units a second, at the relay, the keyboard process and the trusted core. |
| A page dresses a control as a link, or the other way round | A control gives the page no power: its click is the MOUSE event every click over the page already sends. A link's destination is shown only by the trusted strip, never for a control. Controls are bounded (32 a page) and checked like every enhancement triplet. |
| A forged cursor or strip | The cursor is drawn in a style no page can draw, only within rows 1 to 23; the strip is outside the page. (Echo, withdrawn by decision E.134, is no longer drawn.) |
| A compromised interface types | It can only send intents for the channel the trusted core already lets it type into, and the trusted core encodes. |
| A compromised fetcher | It holds no keys but those going to its own channel, and reads only bounded messages. |
| A compromised keyboard process | It is a hostile person at the keys: bounded keys, no modifiers, the rate limit, and the address field only after the caret is placed. |
| Someone photographs the QR | The QR shows only from the panel, with its warning; a PIN is offered; one phone; Finish. |
| The session is taken over after a reconnection | A reconnection is a new session with nothing carried over, unless both sides set RESUME (section 6.4): then only a connection that shows the session's token, 128 bits from the channel's generator, new in each WELCOME, carried only on the session's own push WebSocket, resumes it, and only while the channel holds it with no connection of its own. Identity, if any, is the channel's cookies. |
| A resumed session acts on a key twice, or loses one | Every message of input units is numbered by the count both sides keep; the channel says what it had taken, the receiver sends again only what came after, and the channel drops what it has seen (section 6.4). |
| A flood of moves | At most 60 a second a contact, paced by the trusted part of the receiver, held back while the socket is congested, and counted nothing against the rate, so they never cost a key. |

### 11.4 Privacy

Keys are never logged by the receiver. The relay learns a phone keyboard's name, layout, addresses, sizes and timing, nothing of the keys. Nothing persists past the window. A channel learns where the viewer's pointer and fingers are over its own open page while keys go to it, and nothing elsewhere (REQ-RCH-038): not over another tab, the browser's own controls, or another window.

### 11.5 Residual risks, ranked

1. Plain `ws://` (high likelihood where used; narrowed since TLS was built).
2. A compromised interface (low likelihood, medium consequence).
3. An exploited keyboard process (low, medium).
4. A QR photographed on a public screen (medium, medium).
5. An imitation of the cursor or strip (medium, low).

## 12. Requirements and 13. Decisions in the merge

In rdm since 30 October 2026 (rdm decision DEC-1389): the requirements as `REQ-INT-101` onwards (the engine's area INT), the merge's choices as `Input merge decision 1` to `15`.

## 14. Adopting it

Adopted by the owner on 21 October 2026, as the engine's decision E.100 and the browser's decision 48:

1. **The engine:**
   - `neoteletext-input`: the version-2 encoder and streaming decoder, the functional codes, the control record; the version-1 record removed.
   - `neoteletext-web`: `INPUT_MESSAGE_MAX` to 4096, and to 8192 on 1 November 2026 (DEC-1715).
   - `neoteletext-audio`: record type 5 stepped over.
   - `neottx view`, `neottx keyboard`: version 2.
   - Area INT: REQ-INT-001 to REQ-INT-004 withdrawn, REQ-INT-101 to REQ-INT-116 added; `docs/spec/design/input.md` replaced by a pointer here; `int.md` keeps each number and title, so the traceability table covers them.
2. **The browser:**
   - The trusted core encodes version 2, keeps the input count, and sends HELLO, RESIZE, PAGE and FOCUS.
   - The interface sends intents for mouse, wheel, paste and composition.
   - The decoder finds control records.
   - `neoteletext-site terminal` speaks version 2.
   - Requirements 18.1 to 18.10 replaced by pointers to REQ-INT-130 to REQ-INT-139; `docs/interaction.md` replaced by a pointer here, its sections 16 and 17 kept as history.
3. **Tests:** each requirement's verification above; the latency tests unchanged in what they hold.
