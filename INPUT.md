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
| 2 | Trusted core | Checks every condition again (requirement REQ-INT-130), applies the rate limit, paces the pointer's moves and numbers the contacts of a touch screen (section 9.8), tracks held keys and the input count, keeps what is not yet acknowledged for a resumption (section 6.4), **encodes the protocol**, and alone sends HELLO, RESUME, RESIZE, PAGE, FOCUS and the releases. |
| 3 | Fetcher | Writes each message it is given to the channel's push WebSocket at once, those given at one moment together; holds a move while the socket's unsent bytes are over a bound (section 9.8); measures the round trip by WebSocket ping and pong (section 9.2). It takes nothing else and opens nothing (requirement REQ-INT-133). |
| 4 | Decoder | Finds cursor and control records in pushed packets and `CU` lines, untrusted, and passes them on. |
| 5 | Trusted core | Checks each cursor and control record; applies WELCOME; passes the interface only what it may draw. |

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
| `0x02` | MOUSE | `flags` u8, `button` u8, `col` uv, `row` uv, `px`? uv, `py`? uv, `mods`? u8 | every press and release over the page; every move that changes the dot, at most 60 a second (section 9.8); gone when the pointer leaves the page or a contact is cancelled |
| `0x03` | WHEEL | `flags` u8, `dx` sv, `dy` sv, `col` uv, `row` uv, `px`? uv, `py`? uv, `mods`? u8 | while the pointer is over the page |
| `0x04` | PASTE | `str`, at most `MAX_PASTE` (4000) bytes | always |
| `0x05` | FOCUS_IN | none | always |
| `0x06` | FOCUS_OUT | none | always |
| `0x07` | RESIZE | `cols` uv, `rows` uv, `pw` uv, `ph` uv | always |
| `0x08` | COMPOSE | `cursor` uv, `str` at most `MAX_COMPOSE` (256) bytes; an empty string ends composition | while an input method composes |
| `0x09` | HELLO | `version` uv, `caps` uv, `agent`? str (at most 64 bytes) | first, once |
| `0x0A` | PAGE | `page` uv: `0x100` to `0x8FF` in teletext's hexadecimal page form, or 0 for none | when the receiver has the PAGE capability |

**HOVER**, an extension (`0x43`, so a channel that does not know it skips it): `uv` length, then `flags` u8 (bit 0: 1 when the pointer left the control, 0 when it entered; others a protocol error), `col` uv and `row` uv, the control's first cell, its top left (section 7.3). It goes as the pointer enters and leaves a control of the open page while keys go to the channel: leaving one control for another sends the leave, then the enter. It lets a channel show something as the pointer passes, a row's summary or a help line, without working out from the moves which control the pointer is over (`RETURN-CHANNEL.md` decision F, REQ-RCH-040). Like a move, it counts no input units (section 7.1) and is not held to the rate (section 8 rule 4). It goes only for a mouse or a pen that hovers, never for a finger (REQ-RCH-049).

**TOUCH**, an extension (`0x44`, so a channel that does not know it skips it, REQ-RCH-043): `uv` length, then `flags` u8 (bits 0 and 1 the action, as MOUSE's: 0 down, 1 up, 2 move, 3 gone; bit 2 `px`, `py` present; bits 3 to 7 a protocol error), `id` u8, `col` uv, `row` uv, `px`? uv, `py`? uv, and nothing after. It is every contact on a touch screen after the first, which goes as MOUSE (section 9.8): `id` is 1 to 9, the contact's number from its beginning to its end, the lowest free when it begins; an `id` of 0 or above 9 is a protocol error. At most `MAX_CONTACTS` (10) contacts are on the page at once, ten fingers. TOUCH is sent only when both sides set TOUCH (section 6.2). Its down and up count one input unit each, as a click's press and release do; a move and gone count none (REQ-RCH-054).

**RESUME**, an extension (`0x45`): `uv` length, then the session's `token` (16 bytes, `TOKEN_BYTES`) and `acked` u16 big-endian, the last acknowledgement the receiver took; exactly 18 bytes of payload. It follows HELLO in a reconnection's first message, when the receiver asks to resume its session (section 6.4); a channel that does not know it skips it, and so begins a new session. It counts nothing.

**MOUSE and WHEEL.**
- `flags` bits 0–1: MOUSE action, 0 press, 1 release, 2 move, 3 gone (unused in WHEEL); bit 2: `px`, `py` present; bit 3: `mods` present; MOUSE's bits 4–5: the device, 0 a mouse or trackpad, 1 touch, 2 a pen, 3 reserved and a protocol error, set only when both sides set TOUCH and otherwise 0 (REQ-RCH-042); bits 6–7 (4–7 in WHEEL) a protocol error.
- `button`: on press and release, 0 left, 1 middle, 2 right, 3 back, 4 forward, 5 and up others; on move and gone, a bit mask of the buttons held.
- **Gone** (action 3, `RETURN-CHANNEL.md` decisions D and J, REQ-RCH-034, REQ-RCH-046): the pointer has gone and nothing it held was pressed. It goes when the pointer leaves the open page or keys stop going to the channel, after the waiting move (section 9.8), and when the system or the receiver cancels a contact (a gesture from the screen's edge, a call, a palm rejected, the receiver's own gesture taking it). `button` is the mask held, `col` and `row` the last position sent; what it held is released **without a click**, and a channel must not act on it as on a release. It counts no input units.
- `col`, `row`: the character cell, from the top left of the page: columns 0 to 39 (to 71 with side panels), rows 0 to 24. `px`, `py`: the dot of the page image from the same origin, 12 to a cell across and 20 down; sent whenever the receiver knows them. Units (REQ-RCH-054): a cell and a dot are counted from 0 at the top left; a dot is the page image's own pixel at the size the receiver draws it, 12 by 20 to a cell whatever the screen's scaling, so a channel never needs the display's; a wheel's delta is in 1/120ths of a line.
- `dx`, `dy`: scroll in 1/120ths of a line, positive right and down. A wheel that moves in notches sends at least a whole line (120) a notch: macOS reports a slow notch as a tenth of a line, and a channel that moves a line at a time would need ten. A faster notch keeps the system's acceleration; a trackpad's continuous scrolling is sent as it comes.

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
| 4 | T: `text` present: the key produced text |
| 5 | B: `base` present: it differs from `key` |
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
| `a` pressed | `FF 01 10 61 01 61` | 6 |
| `a` released | `FF 01 02 61` | 4 |
| `é` committed by an input method | `C3 A9` | 2 |
| Focus lost | `FF 06` | 2 |
| Enter pressed | `FF 01 04 02` | 4 |
| Up pressed | `FF 01 04 09` | 4 |
| Red (Fastext) pressed | `FF 01 04 5C` | 4 |
| Control-C pressed | `FF 01 08 63 04` | 5 |
| Page 100 opened | `FF 0A 80 02` | 4 |
| Click at column 10, row 5 | `FF 02 00 00 0A 05` | 6 |
| The same, with its dot (120, 100) | `FF 02 04 00 0A 05 78 64` | 8 |
| A move to the dot (121, 100), no button | `FF 02 06 00 0A 05 79 64` | 8 |
| The pointer gone, from column 10, row 5 | `FF 02 03 00 0A 05` | 6 |
| Wheel one line down at column 10, row 5 | `FF 03 00 00 F0 01 0A 05` | 8 |
| HOVER, entering the control at column 2, row 20 | `FF 43 03 00 02 14` | 6 |
| A tap: the first finger down, at column 10, row 5 (RCH-055) | `FF 02 10 00 0A 05` | 6 |
| A second finger down, at column 11, row 5 | `FF 44 04 00 01 0B 05` | 7 |
| Two fingers moving, in one write: the first (dot 121, 100) and the second (dot 133, 100) | `FF 02 16 01 0A 05 79 64`, `FF 44 07 06 01 0B 05 85 01 64` | 8 + 10 |
| RESUME, after HELLO | `FF 45 12`, the token, the acknowledgement | 21 |

The version-1 key record took 14 bytes for every key.

## 6. Negotiation

### 6.1 The session

1. When the push WebSocket of a channel that declares input opens, the receiver sends HELLO with version 2 and the capabilities it has.
2. The channel answers with WELCOME (section 7.2): the version it speaks and the subset of the capabilities it will use. A channel that cannot speak the version closes the connection.
3. Then the receiver sends RESIZE, FOCUS_IN or FOCUS_OUT, and PAGE if it has that capability; and from then on the viewer's input.
4. The receiver sends no input before WELCOME. A channel that has not answered within `WELCOME_TIMEOUT` (10 s) is taken not to take input, and the receiver says so.
5. **A reconnection is a new session,** unless both sides set RESUME and the channel still holds the session (section 6.4): HELLO again, nothing held, the input count from zero. The channel pushes the open page again when it receives PAGE. A resumed session goes on as section 6.4 says.

### 6.2 Capabilities

`caps` is a bit set of what a receiver can do. Bits 0 to 15 were input modes until 27 October 2026 (section 6.3): they are reserved, never set, and ignored when a peer still sets them. The capabilities are:

| Value | Capability | Meaning |
|---|---|---|
| 65 536 | PAGE | The receiver shows teletext pages and sends PAGE. |
| 131 072 | CURSOR | The receiver draws the channel's cursor record. |
| 262 144 | — | Retired: ECHO, provisional echo, until 28 October 2026 (the engine's decision E.134). Never set; a peer that still sets it is not refused, and the bit is ignored. |
| 524 288 | AGENT | HELLO carries the receiver's user agent string (section 5.4); in HELLO only, never in WELCOME. |
| 1 048 576 | TOUCH | The receiver sends touch: MOUSE's device bits and TOUCH (section 5.4, REQ-RCH-041 to REQ-RCH-043). Without it touch goes as the mouse, the first contact alone. |
| 2 097 152 | RESUME | A lost connection's session may be resumed (section 6.4, REQ-RCH-013): WELCOME carries the session's token, and a reconnection's first message carries RESUME after HELLO. |

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
4. **On a lost connection** the channel treats every held key, button and contact as released (section 8 rule 3), resumed or not.
5. **A reconnection's first message** is HELLO, with RESUME after it: the token and the last acknowledgement the receiver took. In a resumed session HELLO counts nothing, and the count goes on.
6. **The channel answers** with WELCOME (section 7.2): *resumed*, with the input count it had taken, when it holds a session of that token with no connection of its own, and the count taken is at or after the acknowledgement; otherwise *new*, and the session begins again from HELLO, as section 6.1 says, nothing of the old resent.
7. **The receiver sends again**, before anything else and in the order first sent, every message it keeps that came after the count taken, whole messages only; the count taken is always the end of a message it sent, and one that is not is a protocol error. Then RESIZE, the focus and PAGE as at the start of a session, so the channel pushes the open page again, since pages pushed while the connection was down were lost.
8. **The channel drops** what it has already taken, so a message that reaches it twice is acted on once.
9. **The bounds.** The count is 16 bits and wraps, compared by RFC 1982 serial arithmetic, as the acknowledgement is; what may be kept, 256 messages, is far below half its range. A channel that does not set RESUME, or that answers *new*, keeps the rule of section 6.1: a reconnection is a new session.

The token is a secret of the connection, as the keys are: it goes only on the session's own push WebSocket, which is `wss` for any channel worth typing into (section 11.3).

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
| 6 | reserved | written 0, ignored when read (the echo width until decision E.134) |
| 7 | flags | 4 BLOCK (a block rather than a bar); 1 and 2 reserved, written 0 and ignored when read (ECHO and MASKED until decision E.134); others refused |

No cursor requires column and flags 0. A record that breaks any rule is refused whole. The cursor is optional, as a cursor is: a game sends none, or one with no cursor only to acknowledge.

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

## 8. Behaviour

1. **One message per event, never held back** (REQ-RCH-010). Each event is its own message, written as it happens; messages already waiting at the same moment are written together, in one write and one TLS record where the transport allows. The receiver keeps only the latest of a contact's unsent moves (section 9.8) and sums unsent wheel deltas; nothing else is merged or dropped.
2. **Order** is the stream's order.
3. **Held input.** On FOCUS_OUT or a lost connection the channel treats every held key, button and contact as released, and on gone the buttons and the contact the pointer held; the receiver sends no release for them.
4. **The rate.** A receiver sends at most `MAX_PER_SECOND` (120) input units in any second, counted as the input count counts them, and never drops a release, a key's, a button's or a contact's up, to keep to it. 120 is qrkeyboard's relay limit. A move, gone and HOVER count nothing: a move goes at most 60 a second and only when the dot changes (section 9.8); a HOVER only as a control is crossed. So the pointer can never cost a key. COMPOSE counts nothing in the input count, since it is never acknowledged, but is held to the rate as one unit, since nothing else bounds it.
5. **Protocol errors** close the connection, on either side.
6. **Bounds.** A message over `MAX_MESSAGE`, a field over its maximum, a varint over 5 bytes or not minimal: a protocol error.
7. **Nothing waits on a timer** but the pointer's moves (section 9.8). A receiver sends an event when it happens and draws what comes back when it arrives (decision E.97, REQ-INT-008, REQ-RCH-011); the heartbeat (a ping after 25 s of silence, a pong within 10 s) and the round trip's ping (section 9.2) are the push connection's own.
8. **A host goes to a page by sending it.** A cursor record naming another page of the same channel, while keys go to that channel, opens that page in the receiver, as a terminal shows what its host sends. It is the only thing a channel's record can make a receiver do, within the channel, and never a fetch; the viewer choosing a page overrides it.
9. **Terminal programs.** A channel that feeds an ordinary terminal program translates events into whatever encoding that program asked for.

## 9. The receiver's side

### 9.1 When keys go (NeoTeletext)

Keys go to a channel only while all of these hold: the tab is the active one; the page open in it is the channel's; the channel declares input over a WebSocket whose session has been welcomed; the window has the focus; and the viewer is not editing the address. Then every key goes except the browser's own: those with the browser's modifier (Command on macOS, Control-Shift elsewhere), and the strip, the overview and a background tab, which never take keys, and the magazines and the page list, which take the arrows from a click on them until a click elsewhere (the browser's decision 105). Command-Escape (Control-Shift-Escape elsewhere) leaves the page; plain Escape is the channel's.

When keys start going, the trusted core sends PAGE and FOCUS_IN; when they stop (another tab, another page, the page closed), FOCUS_OUT and PAGE 0, so the channel lets go of a key held as the viewer left (REQ-INT-108); when the window loses the focus or the address is being edited, FOCUS_OUT, and FOCUS_IN when it comes back.

**The mouse.** Every press, release and move over the page goes to the channel while keys go to it (section 6.3), moves paced as section 9.8 says; a click with the browser's modifier is the browser's. A link the page declares is the browser's on every page: a click on it follows it, and nothing pressed on it goes to the channel (section 6.3). When the pointer leaves the page, or keys stop going, the waiting move and then gone (section 5.4). The wheel goes to the channel while the pointer is over the page; over the rest of the window it scrolls the browser.

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

### 9.5 Characters a page cannot show

The receiver sends the viewer's character whatever its script, and draws nothing of it (section 9.3). What the channel draws is the channel's choice: the nearest character of the page's sets, a placeholder, or a page in another set (the engine's area CHR).

### 9.6 `neottx view`

Every key goes while the channel takes input, Control-C included; Control-] leaves and returns. With a terminal that reports releases (the Kitty keyboard protocol), it sends releases too; otherwise a press only. It sends PASTE from bracketed paste, FOCUS from the terminal's focus events, and PAGE when the viewer opens a page.

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

- **The units.** `col`, `row` is the character cell, columns 0 to 39 (71 with both side panels) and rows 0 to 24. `px`, `py` is the dot of the page image, 12 dots to a cell across and 20 down, 480 by 500 for a page without side panels, from the page's top left. The dot is always inside the cell: `px` / 12 = `col` and `py` / 20 = `row`, rounded down.
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
| Keys go somewhere else | The push address is on the channel's origin; the fetcher takes no address; nothing in the protocol names one. |
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

## 12. Requirements

The normative requirements of the input system. Identifiers continue the engine's area INT; on adoption, REQ-INT-001 to REQ-INT-004 are withdrawn (replaced by REQ-INT-101 to REQ-INT-111) and REQ-INT-005 to REQ-INT-008 stand as written there, and the browser's requirements 18.1 to 18.10 are replaced by REQ-INT-130 to REQ-INT-139, which name NeoTeletext.

**The protocol**

**REQ-INT-101 — The input stream.** A receiver shall send input as one ordered stream of raw UTF-8 text and `0xFF`-framed events (sections 5.1 to 5.4), in binary messages on the channel's push WebSocket, each holding whole events and whole characters and at most 4096 bytes. *Verification:* encoder and decoder round trips; the message bound; a fuzz target of the decoder.

**REQ-INT-102 — Encoding.** Varints shall be minimal and at most 5 bytes; strings length-prefixed and within their field's maximum; text without control characters; and a reserved type, an unknown core type, a reserved flag bit, malformed UTF-8 or an over-long field shall be a protocol error that closes the connection. Extension types shall be skipped by their length. *Verification:* decoder tests of each error and of a skipped extension.

**REQ-INT-103 — Events.** The core events shall be KEY, MOUSE, WHEEL, PASTE, FOCUS_IN, FOCUS_OUT, RESIZE, COMPOSE, HELLO and PAGE, with the layouts of sections 5.4 and 5.5; PASTE at most 4000 bytes and COMPOSE at most 256. *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* MOUSE has action 3, gone, and its device in `flags` bits 4 and 5; the extensions are HOVER (`0x43`), TOUCH (`0x44`) and RESUME (`0x45`), each with the layout of section 5.4 (REQ-RCH-034, REQ-RCH-042, REQ-RCH-043, REQ-RCH-013). *Verification:* round trips of every event and every field's bounds.

**REQ-INT-104 — Keys.** Every press, repeat and release of a key shall be sent as KEY, a character key by its unshifted code point and every other by its functional code, with modifiers as the Kitty bit set, `text` when it produced text and `base` when it differs from `key`; raw text shall carry only what does not come from a key (amended 27 October 2026, decision E.125). *Verification:* tests of a letter, a Control combination, a named key, a modifier alone, a release and a non-United-States layout.

**REQ-INT-105 — Functional codes.** The codes of section 5.6 shall be fixed, and only ever added to; codes from 128 shall follow the engine's pinned W3C name table. *Verification:* a test pins the codes of Enter, Up, Red and F1, and the first code from 128.

**REQ-INT-106 — Negotiation.** A receiver shall send HELLO first and no input before WELCOME; it shall use only the capabilities both sides set; a reconnection shall start a new session with nothing held and the input count at zero. *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* unless both sides set RESUME and the channel resumes the session, as REQ-INT-125 says (REQ-RCH-013). *Verification:* a session test; a test that nothing goes before WELCOME; a reconnection test.

**REQ-INT-107 — Withdrawn (modes).** Withdrawn on 27 October 2026 (decision E.125): every event is sent, and there is no mode stack (section 6.3).

**REQ-INT-108 — Held input.** On FOCUS_OUT or a lost connection a channel's decoder shall treat every held key and button as released, and a receiver shall send no release for them. *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* every contact down too, and on gone the buttons or the contact the pointer held, without a click (REQ-RCH-046). *Verification:* a decoder test.

**REQ-INT-109 — The rate.** A sender shall send at most 120 input units in any second, counted as the input count counts them, and never drop a release to keep to it. *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* a release is a key's, a button's or a contact's up; a move, gone and HOVER are not held to the rate, and COMPOSE, which counts no input units, is held to it as one (section 8 rule 4). *Verification:* the 121st unit; a release beyond it, across the clock's wrap.

**REQ-INT-110 — The cursor record and the input count.** The cursor record shall be as section 7.1, its acknowledgement the input count acted on; the receiver shall count what it sends as the channel counts it. *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* what is never acknowledged counts nothing (REQ-INT-126); the acknowledgement may travel in the answer's frame, and a receiver takes it there or alone; one beyond what was sent is ignored (REQ-RCH-012). *Verification:* round trips through a packet; bounds; a sound on the same channel; the count across text, events and a paste; a cursor record among a page's packets.

**REQ-INT-111 — The control record.** WELCOME shall be a record of type 5 as section 7.2, one fragment, checked whole; a record of a withdrawn type (`0x02` to `0x04`) shall be ignored (amended 27 October 2026). *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* with RESUME, WELCOME carries the session's state, its token and, resumed, the count taken (REQ-RCH-013). *Verification:* round trips; refusals; a fuzz target.

**REQ-INT-112 — Immediacy.** Every event shall be written when it happens, one write per event, merging only unsent mouse moves and wheel deltas; nothing shall wait on a timer (with REQ-INT-008). *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* one message per event, never held back: messages already waiting at the same moment shall be written together, in one write and one TLS record where the transport allows; only the pointer's moves are paced (REQ-INT-122), and unsent moves are merged per contact (REQ-RCH-010, decision C). *Verification:* the latency tests of REQ-INT-008 and REQ-INT-135; a test that two messages given together leave in one write, in order, and that a lone one is not delayed.

**REQ-INT-114 — Withdrawn (a page's own modes).** Withdrawn on 27 October 2026 (decision E.125): a page's `IM` line is an unknown line, reported and skipped, and a PAGE_MODES record is ignored.

**REQ-INT-115 — The mouse and the wheel over the page.** *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* every move that changes the dot under the pointer over the open page goes, buttons held or not, at most 60 a second (REQ-INT-122), and gone when it leaves (REQ-INT-123); the move only while a button is held or within a pointer area is withdrawn with pointer areas (REQ-RCH-030, REQ-RCH-037). As written on 27 October 2026: A receiver shall send every MOUSE press and release over the open page, with the cell, the dot and the modifiers, while keys go to its channel, a click with the browser's modifier staying the browser's; a move that changes the dot under the pointer while a button is held, or within a pointer area of the open page (section 7.4), and no other; and WHEEL while the pointer is over the page (amended 27 October 2026, the owner's decisions in section 6.3). *Verification:* receiver tests that a click and a drag go with no request, that a move with no button goes only within a pointer area or a whole-page one, that a move to the same dot is not sent again, and that a click with the modifier follows a link.

**REQ-INT-116 — International keyboards.** A receiver shall send text as the Unicode characters the layout or input method produced, in logical order and in Normalization Form C, never translated into a teletext character set; shall send a dead key as the key `Dead` with no text and the composed character after it; shall not report AltGr as Control and Alt; and shall give a character key's `key` from the active layout and `base` from the United States layout of the same physical key. *Reason:* the protocol carries what the viewer typed, in any language, and leaves its meaning to the channel; a shortcut binds by position, a letter by meaning (section 5.7). *Verification:* receiver tests with Russian, Hebrew, German (AltGr), French (dead keys) and AZERTY layouts, a Japanese input method's preedit and commit, and a decomposed `e` and combining accent sent as U+00E9; a channel test of native digits selecting a page.

**REQ-INT-117 — Controls.** A page shall be able to declare the cells it answers itself by triplets of column mode 00101 in its local enhancement data, as section 7.3: the address the first column, D5 to D0 the width, D6 joining the run to the control above at the same column and width, the row the active row; a triplet in an object shall declare nothing. *Reason:* a reserved mode is part of the page and skipped by every decoder, so controls travel with the rows they describe and change nothing drawn (decision E.127). *Verification:* engine tests of four controls on a row, joined runs, the end of the local data, and that the triplet is still a reserved mode to the enhancement processor; a render of a page with and without controls compared byte for byte.

**REQ-INT-118 — Controls are bounded and checked.** A control triplet outside rows 1 to 23, of no width, past column 39, over a cell of another control, joined to no control above, or beyond 32 controls a page shall be dropped and counted, and the others kept. *Verification:* engine tests of each rule and of the bound.

**REQ-INT-119 — Controls and links under the pointer.** A receiver with a pointer shall show a page's controls only while keys go to its channel, with the pointer it shows over a link; it shall give the control or link under the pointer the hover look, each colour of its cells moved to the same entry of the adjacent CLUT, and while a button is held down on it the pressed look, the hover colours with foreground and background exchanged; it shall send the channel nothing for either. *Reason:* section 9.7: the looks are Level 2.5's own colour operations, the page chooses them with CLUTs 2 and 3, and the pointer's movement stays the viewer's. *Verification:* engine tests of both looks; receiver tests of the pointer, the looks and that nothing is sent.

**REQ-INT-120 — Withdrawn (pointer areas).** Withdrawn on 28 October 2026 (`RETURN-CHANNEL.md` decision E, REQ-RCH-037, the engine's decision E.133): with every move sent they ask for nothing; column mode 01010 is reserved again, as EN 300 706 Table 29 has it, and a page that carries it declares nothing by it. *Verification:* the engine's control triplet tests. As written on 27 October 2026, kept for its history: A page shall be able to declare pointer areas by triplets of column mode 01010 in its local enhancement data, as section 7.4: the control triplet's fields, a width of 0 not joined meaning the whole page, at most 8, overlapping allowed; a triplet that breaks a rule shall be dropped and counted. *Reason:* moves without a button cost a message each, so they go only where a page has a use for them (section 6.3); the declaration travels with the page, as a control's does. *Verification:* engine tests of the triplet, overlap, the whole page and the bound; a receiver test that a move with no button goes only within an area.

**REQ-INT-121 — HOVER.** *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* it stands as built, alongside every move (REQ-RCH-040), counts no input units (REQ-INT-126), and goes only for a mouse or a pen that hovers, never for a finger (REQ-RCH-049). A receiver shall send HOVER, the extension `0x43` of section 5.4, as the pointer enters and leaves each control of the open page while keys go to its channel, the leave before the enter when it goes from one to another, with the control's first cell; the trusted part of the receiver shall send one only for a control of the page's latest image. A channel shall skip it when it does not use it. *Reason:* a channel can show something as the pointer passes for two messages a control crossed (section 5.4). *Verification:* engine tests of the event; receiver tests of enter, leave, and from one control to another.

**REQ-INT-122 — The pointer's moves at 60 a second.** A receiver shall send at most one move of each contact in each period of 1000/60 ms, the *k*th period of a run ending at the run's first move plus *k* × 1,000,000 / 60 µs; a move that comes 1000/60 ms or more after the contact's last move sent shall go at once and begin a run, and one that comes sooner shall wait in the contact's one slot, replacing what waits there, until its period ends; an unchanged position shall not go again; nothing shall run while no move waits; and before any other event is written every waiting move shall be written first; moves of several contacts due at one moment shall be written together. The pace is one named constant, `MOVES_PER_SECOND`, and one implementation, `neoteletext-input`'s `pace::Pacer` (section 9.8). *Reason:* the owner's 60 a second, the first move with no added delay and no wake-up while the pointer is still (REQ-RCH-030 to REQ-RCH-033, REQ-RCH-045). *Verification:* tests of 1,000 moves a second for 10 s (600 sent, no drift), of a move 20 ms and 5 ms after the last, of a flush before a release, and of two contacts; the fuzz target `input_session`.

**REQ-INT-123 — Gone.** A receiver shall send MOUSE with action 3, after the waiting move, when the pointer leaves the open page or keys stop going to its channel, and MOUSE or TOUCH with action 3 when the system or the receiver cancels a contact; a channel shall release what it held without a click (section 5.4). *Reason:* with every move sent a channel must know when the pointer is gone, and a contact the system takes was never released (decisions D and J, REQ-RCH-034, REQ-RCH-046). *Verification:* round trips of action 3; a decoder test that gone releases without a click.

**REQ-INT-124 — Touch.** With TOUCH agreed, the first contact down shall go as MOUSE with device 1 and button 0, further contacts as TOUCH with the lowest free `id` of 1 to 9 kept until they end, at most `MAX_CONTACTS` (10) at once, a further one sending nothing until one ends; a pen shall go as MOUSE with device 2; without TOUCH, TOUCH shall not be sent and MOUSE's device shall be 0, so a channel sees nothing a mouse would not send; device 3, a TOUCH `id` of 0 or above 9, and a reserved TOUCH flag are protocol errors; the trusted part of a receiver numbers the contacts and refuses a contact not begun (section 9.8). *Reason:* every channel answers touch unchanged, and one that wants more fingers reads TOUCH (decision H, REQ-RCH-041 to REQ-RCH-043, REQ-RCH-050, REQ-RCH-053). *Verification:* round trips and refusals of the device bits and TOUCH; a test of ids under ten contacts beginning and ending in turn; a session test with and without TOUCH; the fuzz target `input_stream`.

**REQ-INT-125 — Resumption.** With RESUME agreed, a receiver shall keep every unacknowledged message of input units, bounded by `RESEND_BYTES` and 256 messages, ask in a reconnection's first message to resume with RESUME after HELLO, and on a resumed WELCOME send again, first and in order, only the messages after the count taken; a count taken that is not the end of a message it sent is a protocol error; on a new WELCOME, or without RESUME, a reconnection is a new session (section 6.4). A channel shall hold a lost session at least `RESUME_HOLD_MS`, resume it only for its token and with no connection of its own, and drop what it has taken. *Reason:* the only way no key is lost when a connection drops, and none acted on twice (decision B, REQ-RCH-013); numbering by the input count adds nothing to any event. *Verification:* session tests of a resumption from an acknowledgement and from a later count, of a session not held, of a false count, of the bounds, and of a session that keeps nothing; round trips of RESUME and of WELCOME with the session; the fuzz targets `input_session` and `control_records`; a reconnection test with events in flight, in the server, where each reaches the channel exactly once.

**REQ-INT-126 — What is never acknowledged counts nothing.** A move and gone, MOUSE's and TOUCH's, HOVER, COMPOSE and RESUME shall count no input units, and so never be acknowledged or kept to send again; a contact's down and up count one each, as a click's press and release (section 7.1). *Reason:* an acknowledgement for a move would be a message for nothing at 60 a second (decision A, REQ-RCH-012, REQ-RCH-054). *Verification:* tests of each event's units and that a session counts and keeps none of them.

**REQ-INT-113 — A host goes to a page.** A cursor record naming another page of the same channel shall open that page while keys go to that channel, and do nothing else; the viewer's own choice shall override it. *Verification:* a trusted-core test.

**The receivers**

**REQ-INT-127 — Positions in the page's units.** A receiver shall send every pointer and touch position as the cell and the dot of the page image under it (section 9.9), whatever the size the page is drawn at and whatever the display's scaling, only for the open page at rest; and the trusted part of a receiver shall refuse a cell outside the page, and a dot outside the page image or outside its cell (`px` / 12 ≠ `col` or `py` / 20 ≠ `row`), before encoding. *Reason:* a channel answers the pointer the same at every size without knowing it, and the drawing process is not trusted to say where the pointer was (section 3.6; the owner's question of 28 October 2026 on scaling). *Verification:* interface tests that a click on the same cell gives the same cell and dot at a page drawn at half, the same and three times the image's size; a trusted-core test that a dot outside its cell, or outside 480 by 500, is refused. *State:* written 28 October 2026; the cell's bound is built (NeoTeletext's `protocol` reader), the dot's check is not.

**REQ-INT-130 — When keys go (NeoTeletext).** Keys shall go only under every condition of section 9.1, and the trusted core shall check each again; the browser's own keys and those of the strip, the page list, the overview and a background tab never go. *Verification:* trusted-core tests of each condition; an interface test that Command never goes.

**REQ-INT-131 — The strip.** The strip shall say "Keys go to *host*" while keys go, "Not secure" on plain `ws://`, and the round trip. *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* the round trip of the push connection, by WebSocket ping and pong at most once a second while keys go, not from acknowledgements (REQ-RCH-016). *Verification:* a strip test.

**REQ-INT-132 — The trusted core encodes.** Only the trusted core shall encode the protocol; the interface shall send intents, checked whole; only the trusted core sends HELLO, RESIZE, PAGE and FOCUS. *Verification:* protocol tests of the intents; a hostile-interface test.

**REQ-INT-133 — The fetcher.** The fetcher shall take from the trusted core only encoded input messages of at most 4096 bytes, write them to the push WebSocket at once, and take no address; nothing it takes changes what is fetched (decision 22). *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* messages it is given at one moment it writes together; a message the trusted core marks as a contact's move it holds while the socket's unsent bytes are over the bound, the latest replacing it, and writes before any other message (REQ-RCH-010, REQ-RCH-035). *Verification:* the fetcher reader's tests and fuzz target.

**REQ-INT-134 — Cursor drawn safely.** The cursor shall be drawn by the interface as section 9.3 says, in a style no page can draw, within the record's row; nothing of the viewer's keys shall be drawn by the receiver. *Verification:* interface tests. *Amended 28 October 2026 (the engine's decision E.134):* echo withdrawn. As written before: the cursor and echo drawn in styles no page can draw, within the record's row and width, the echo only of the viewer's own printable keys, provisional and gone on acknowledgement or after 2 s.

**REQ-INT-135 — Latency.** A key shall be written within 1 ms; the push socket shall have `TCP_NODELAY`; a pushed packet of the page being typed into shall be drawn within 20 ms. *Verification:* the timed test, with the round trip's median on the computer's own network held to 2 ms.

**REQ-INT-136 — Mouse, paste and composition (NeoTeletext).** *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* every move over the page, paced by the trusted core (REQ-INT-122), gone when the pointer leaves, and touch as REQ-INT-124 says, every contact on a page that takes input the channel's (REQ-RCH-030, REQ-RCH-036, REQ-RCH-047). *Amended 28 October 2026 (the owner: "revise that decision - links must be acted upon by the client browser"):* a link the page declares is the browser's on every page, a click or tap on it following it with no modifier and nothing pressed on it going to the channel (REQ-RCH-048). Every click and move over the page shall go to the channel while keys go to it, a click with the browser's modifier always following a link; the wheel shall go to the channel over its page and scroll the browser elsewhere; paste shall go as PASTE and the input method's preedit as COMPOSE while keys go (amended 27 October 2026, section 6.3). *Verification:* interface and trusted-core tests.

**REQ-INT-137 — No key is logged, and the round trip is measured.** No receiver shall log a key; the round trip shall be measured from acknowledgements, with at most 256 sends remembered. *Amended 28 October 2026 (`RETURN-CHANNEL.md`, the engine's decision E.133):* the round trip is measured by WebSocket ping and pong (REQ-RCH-016, REQ-INT-131); the 256 messages remembered are those kept for a resumption (REQ-INT-125). *Verification:* a log test; a trusted-core test.

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
| 10 | Acknowledgement by the input count, no sequence numbers and no clock | Both | The stream's order makes numbering redundant; the built system's per-record clock exposed typing rhythm for no use. *Amended 28 October 2026:* echo, which the acknowledgement drove, is withdrawn (decision E.134); the count is also the implicit number a resumption sends again by (section 6.4), and the round trip comes from ping and pong. |
| 11 | Losing focus releases held input, at the channel | Input Event Protocol | No stuck keys, and no burst of releases on the wire; the built system sent releases from the trusted core. |
| 12 | A reconnection is a new session | Input Event Protocol | Simpler and safer than the built system's resume record; PAGE makes the channel push the page again. *Amended 28 October 2026* (`RETURN-CHANNEL.md` decision B): unless both sides set RESUME, by a token in WELCOME and the input count, with nothing added to any event (section 6.4). |
| 13 | The rate of 120 a second, the bounds, the strip, the security model, the phone keyboard | Built system | Measured and reviewed; unchanged. |
| 14 | Mouse only when the channel or the page asks; a page asks for itself (`IM` line, PAGE_MODES) | Input Event Protocol, extended | Agreed by the owner on 21 October 2026; withdrawn on 27 October 2026 with every mode (section 6.3). |
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
   - The trusted core encodes version 2, keeps the input count, and sends HELLO, RESIZE, PAGE and FOCUS.
   - The interface sends intents for mouse, wheel, paste and composition.
   - The decoder finds control records.
   - `neoteletext-site terminal` speaks version 2.
   - Requirements 18.1 to 18.10 replaced by pointers to REQ-INT-130 to REQ-INT-139; `docs/interaction.md` replaced by a pointer here, its sections 16 and 17 kept as history.
3. **Tests:** each requirement's verification above; the latency tests unchanged in what they hold.
