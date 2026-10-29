# The return channel: input to the channel with the least latency and the fewest bytes

The design for three instructions the owner gave on 28 October 2026:

> "the return channel that transmits user interaction key and mouse data from client pages back to server - this must be super optimised for minimum possible latency [...] we wqnt the minimum possible data transmitted. also research how online games manage to get their latency as low as they can"

> "revise your latency advice given we are using websockets"

> "i also want mouse movement/location events always sent to the back end [...] i want mouse move events sent every 1000/60 milliseconds"

> "this system will be ported to phone and tablets evenutally . now is the time to integrate touch into these decisions. do it"

The return channel is the path of an input event from the viewer's hand to the channel program that answers it, and of that answer back to the screen: the browser's interface, trusted core and fetcher, the push WebSocket, the server, the channel program on its standard input, and back. Its protocol is `INPUT.md`; its server side is `SERVER.md` sections 5 to 7. This document measures it (section 2), sets out what online games do and what of that applies over a WebSocket (section 3), designs the pointer's moves at 60 a second and touch for phones and tablets (section 4), and states the requirements (section 6), area RCH, each naming the repository that carries it. The engine's and the protocol's parts were built on 28 October 2026 (the engine's decision E.133, `INPUT.md` as amended that day); each requirement of section 6 says what is built and where its tests are, and the browser's, the server's and the kits' parts are not built yet. Section 5 records the owner's decisions, every one of which has a requirement in section 6; section 7 lists the work.

---

## 1. The result in brief

- **The work along the path is about 3 ms; what the viewer sees is about 16 ms more, and the browser's own pacing causes it.** Every frame the interface draws holds the next one back 16 ms, the frame drawn for the server's acknowledgement included, so the channel's answer, arriving 1 to 2 ms after it, waits; a click on a control has a second hold of 20 ms in the trusted core; and an input that also asks for a redraw leaves only after that frame is drawn. All three are implementation faults of the browser (requirements RCH-001 to RCH-003).
- **Over a WebSocket the bytes of one event cannot fall much.** A key press is 6 bytes of payload against 6 of WebSocket frame (the 4-byte mask is mandatory, RFC 6455 §5.3), 22 of TLS 1.3 and 52 of TCP/IP. The levers are to let events already waiting share one TLS record and one TCP segment (RCH-010), and not to send messages that carry nothing (RCH-012).
- **The largest risk particular to a WebSocket is the answer queuing behind other data** on the one ordered stream from the server: shared pages, live audio, the header. The server must put answers first and keep its backlog where it can still reorder it (RCH-020, RCH-021).
- **Downstream is where the bytes are:** a one-row change sends the whole page today, 1,222 bytes where about 128 would do (RCH-022), and every sub-page of it, which with 8,190 sub-pages allowed has no bound (RCH-023).
- **The pointer's position goes to the channel at most 60 times a second while it moves over the page, the first move at once** (section 4, RCH-030 to RCH-039): about 5.4 KB a second upstream while the pointer moves, nothing while it is still.
- **Touch is the pointer with fingers** (section 4.4, RCH-041 to RCH-055): the first finger down is the mouse's left button, so every channel works with touch as it is; further fingers go as TOUCH, an extension a channel skips if it does not know it; every contact goes at once and moves at 60 a second like the mouse; while keys go to a channel every contact on its page is its own, and the browser's gestures give way.
- **UDP, QUIC, WebTransport and WebRTC are not worth it here** (section 3.2): key events need one reliable ordered stream anyway, and the cost is reach through firewalls and proxies, a TCP fallback, and a second transport in a security-first tree.

---

## 2. Measurements

Measured on 28 October 2026 on `foundintelquiet4060` (Linux, loaded by other builds: load average 18 to 24 on 20 cores), over loopback, with the server's development build on a port of its own and its kitchensink channel (Node) and a minimal channel on the Python kit; plain `ws`, as the server has no TLS yet (server `architecture.md`). The macOS interface, TLS, IPv6 and the phone path were read from the code, not measured.

### 2.1 Time

| What | Median | Notes |
|---|---|---|
| Key press to the server's acknowledgement | 0.19 ms | p90 0.46 ms |
| Key press to the channel's new page (kitchensink 608) | 0.81 ms | p90 2.58 ms, p99 3.07 ms; n = 90 |
| Raw text `x` to the new page | 0.84 ms | n = 135 |
| Click on a button (page 603) to the new page | 0.79 ms | n = 30 |
| Python kit echo | 0.50 ms | n = 125 |
| Node's work for one key (publish after reading the line) | 1.56 ms | `strace -f` of the server's own copy |
| Server, from reading a publish to writing the socket | 0.13 ms | `strace` |
| Browser: key to pushed page through the real fetcher | 0.283 ms | the browser's own `latency` test |
| Browser: the decoder drawing a page | 1.32 ms | the largest single piece of work per answer |
| Browser: one hop between its processes | about 50 µs | a microbenchmark of its framing, reader thread and outbox |

### 2.2 Where the time goes in the browser (read from the code)

| # | Fault | Where | Cost |
|---|---|---|---|
| 1 | The interface draws at most one frame in 16 ms, and a frame that changed nothing still restarts the 16 ms; the frame drawn for the acknowledgement makes the answer wait. | `native/interface/src/app/frame.rs` (`pace`, `last_frame`), `incoming.rs` | 10 to 14 ms a key or click |
| 2 | The trusted core holds a page's frame if its last frame went less than 20 ms ago; on a click on a control the pressed look goes first and holds the channel's answer. The once-a-second header does the same to about 2% of keys. | `native/core/src/frames.rs` (`MIN_FRAME_INTERVAL`), `pointer/press.rs` | up to 17 ms a click |
| 3 | The interface flushes what it sends to the trusted core only in `about_to_wait`, which winit on macOS runs after the redraw, so an input that also redraws leaves only once the frame is drawn and presented. | `native/interface/src/app.rs` | one frame's drawing |

### 2.3 Bytes

Per message upstream: WebSocket 2 + 4 (mask) = 6; TLS 1.3 record 5 + 1 + 16 = 22; TCP 20 + 12 (timestamps) + IPv4 20 = 52. That is 80 bytes with TLS, 58 on plain `ws`; IPv6 adds 20.

| Event as the browser encodes it | Payload | With TLS, as an IPv4 packet | Server to channel, JSON line |
|---|---|---|---|
| `a` pressed, `FF 01 10 61 01 61` | 6 | 86 | 103 |
| `a` released, `FF 01 02 61` | 4 | 84 | 94 |
| A click at (5,20), dot (66,410) | 9 | 89 | 130 |
| A wheel notch | 11 to 12 | 91 to 92 | 103 |
| HOVER entered or left | 6 | 86 | 119 to 120 |
| A move, with the dot | 9 to 10 | 89 to 90 | about 130 |

Downstream, on kitchensink page 608: the acknowledgement 44 bytes on the WebSocket (118 as a packet), sent for every message, releases, HOVER and COMPOSE included; the answer to a typed character 1,222 bytes (29 packets of teletext); the channel's publish line 868 bytes, the whole page as TTI. **One typed letter: 170 bytes up in 2 packets, 1,532 down in 3**, plus 52 for each TCP acknowledgement not carried by data.

### 2.4 Faults found on the way

- **Acknowledgements stop once a text field is full** (measured): the kitchensink field writes a cursor of width 0 with echo, which `INPUT.md` section 7.1 forbids; the server then sends no acknowledgement and no cursor for every later input. Fix in the components kit, and the server checks `CU` at publish (RCH-025).
- **A channel's line can be lost** (read): the server's relay reads the channel's output with `read_until` inside `tokio::select!`, which is not cancellation-safe, so a part-read publish or sound line is dropped when an input line wins the select (RCH-024).
- **Input sent and then dropped:** the server's runtime drops key modifiers (Control-C reaches the channel as "c"), mouse dots and modifiers and COMPOSE; the browser sends mouse modifiers as 0 and only the left button (RCH-026, RCH-027).
- **`INPUT.md` section 5.8** still gives `a` as 1 byte; since decision E.125 every key goes as KEY with its press and release.

---

## 3. What games do, and what applies over a WebSocket

### 3.1 The techniques

| Technique | What games do | Here |
|---|---|---|
| Nagle and delayed ACK | Nagle holds a small write while earlier data is unacknowledged; the receiver delays that acknowledgement, 40 ms on Linux (`TCP_DELACK_MIN`), 200 ms on Windows (`TcpDelAckTicks`). Games turn Nagle off. | Done at both ends (`TCP_NODELAY`: the fetcher's `transport/opening.rs`, the server's `main.rs`). Whatever terminates TLS in front of the server must keep it (nginx does by default for WebSockets). RCH-028. |
| Send at once, no tick | Valorant at 128 Hz charges about half a tick waiting to be queued; Overwatch's move from 20.8 to 60 Hz cut interpolation delay from about 60 to 20 ms. | Each discrete event goes at once, with no tick anywhere on the path (RCH-011); a channel flushes each line (RCH-029). |
| Numbered inputs, acknowledged | Every reliable game protocol numbers its inputs and acknowledges the last processed (Gambetta; Fiedler; GGPO). | A WebSocket cannot resume: what was in flight when TCP died is lost silently. Numbering lets the browser resend after a reconnect with no duplicate reaching the channel (decision B, RCH-013). |
| Redundant resending | Lockstep and GGPO resend every unacknowledged input in each packet. | Nothing over TCP, which retransmits. |
| Bit packing, deltas, varints | Inputs of a few bits; snapshots quantised and delta-encoded. | The protocol is already varints and 4 to 10 bytes an event; headers are 80. |
| Thin streams | A lone lost segment waits for a timeout (Linux `TCP_RTO_MIN` 200 ms; RFC 6298 recommends 1 s), doubling on each loss. | `TCP_THIN_LINEAR_TIMEOUTS` on the server's sockets: no doubling while fewer than four segments are in flight (RCH-028). No equivalent per socket on macOS or Windows. |
| Warm connections | Keepalives under every idle timeout on the path; GGPO every 200 ms. | One push WebSocket per channel, opened with the tab and kept; the engine pings after 25 s of silence, under nginx's 60 s and Cloudflare's 100 s. A reconnection costs about three round trips (TCP, TLS, the upgrade); TLS resumption saves one; TLS 0-RTT and TCP Fast Open must never carry events, which could be replayed (RCH-014). |
| Local echo, prediction | Clients run their input at once and reconcile with the server. | The page is the channel's program output and cannot be predicted; the browser already draws the hover look and the echo of typed characters itself (decision 117, `INPUT.md` section 9.3). |
| Present on arrival | One queued frame under vsync costs one refresh, 16.7 ms at 60 Hz. | RCH-001 and RCH-004. |
| QoS marking (DSCP) | "Not trusted by the network" (RFC 8837). | No. |
| Busy polling, timer resolution | Microseconds. | No; every hop of the path blocks on readiness, not on a timer. |

Sources: gafferongames.com (UDP vs TCP, deterministic lockstep, reliable ordered messages, snapshot compression); riotgames.com "Peeking into Valorant's netcode"; Parsec's engineering blog (BUD; the browser client); GGPO's `udp_proto.cpp`; RFC 6455, 8446, 6298, 8985, 7413, 8831, 8837, 8325, 5382; man 7 tcp; docs.kernel.org `tcp-thin`; the W3C WebTransport Candidate Recommendation (30 July 2026); nginx's `tcp_nodelay` and WebSocket proxying documents.

### 3.2 Other transports

UDP with its own reliability, QUIC, WebTransport and WebRTC data channels each recover from loss faster, and QUIC removes head-of-line blocking between streams. But every key event must arrive and in order, so all of them would sit on one ordered stream, where QUIC blocks as TCP does. About 4.4% of clients have QUIC blocked (Google, IETF 99); proxies do not carry it; a TCP fallback would still be needed; WebTransport's datagrams need HTTP/3; WebRTC needs ICE, which a server with a public address does not; and each adds a protocol stack to a tree whose first requirement is security. The WebSocket stays.

### 3.3 What a WebSocket fixes and what it leaves to us

- **Fixed:** a mask of 4 bytes on every frame from the browser (RFC 6455 §5.3); a frame header of 2 bytes up to 125 bytes of payload and 4 up to 65,535; one ordered byte stream in each direction.
- **Compression stays off.** permessage-deflate makes a 6-byte payload longer, costs time on both sides, and opens a compression side channel; the engine refuses it (`SERVER.md` section 5.1).
- **Events go as binary frames,** never text, which a receiver would have to check as UTF-8.
- **Frames already waiting may share a write.** Several WebSocket messages may follow each other in one TLS record and one TCP segment; each keeps its own frame, so the format does not change (RCH-010).
- **The one stream from the server is shared** by page frames, audio records, the header and the answers: an answer waits behind whatever the server has already handed to the kernel. 175 KB of shared pages, sent when a connection opens, take 140 ms to drain at 10 Mbit/s (RCH-020, RCH-021).
- **The push socket stays a connection of its own:** never carried over HTTP/2 (RFC 8441), so a sub-page file or a catalogue of up to 524,160 bytes (the engine's decision E.132) never queues ahead of an answer (RCH-015).
- **No resumption:** a dropped connection loses what was in flight (decision B, RCH-013).
- **Ping and pong** measure the round trip of the connection itself, which the strip should show rather than the acknowledgement's, which today measures only the server's receipt (RCH-016).

---

## 4. The pointer: moves at 60 a second, and touch

Today (decision 118, the engine's E.128) a move goes only while a button is held or within a pointer area the page declares. The owner's instruction makes the pointer's position go to the channel whenever it moves over the page, at most every 1000/60 ms.

### 4.1 The design

- **What goes:** MOUSE with action 2 (move), the buttons held, the cell, the dot and the modifiers, whenever the dot under the pointer has changed since the last move sent, while the pointer is over the open page and keys go to its channel (`INPUT.md` section 9.1). Nothing while the pointer is still: an unchanged position is not sent again.
- **How often:** at most one move in each period of 1000/60 ms, which is 16,666⅔ µs. The *k*th deadline is computed as the start plus *k* × 1,000,000 / 60 µs, so the average is exactly 60 a second with no drift; a whole-millisecond timer of 16 ms would give 62.5.
- **A move goes at once if it can, depending on when the last was sent.** If 1000/60 ms or more have passed since the last move went, the move goes as it happens; if less, the latest position waits in one slot, which each newer position replaces, and goes when 1000/60 ms have passed since the last. This is a throttle with its leading edge sent, not the fixed timer of the document the owner supplied (section 4.3): no added delay on the first move, and no wake-up at all while the pointer is still.
- **Order:** before any other event is written (a press, a release, a key, the wheel), the move waiting in the slot is written first, so a release is never seen before the move that ended the drag. The wheel keeps its rule: unsent deltas are summed.
- **Leaving the page:** when the pointer leaves the page, or the page stops taking keys, the waiting move is written and then a MOUSE with action 3 (left), so the channel can stop showing what follows the pointer. Action 3, reserved until now, takes this meaning (decision D).
- **Never queued behind the network:** a move is written only when the push socket's unsent bytes are under a bound; otherwise it waits in the slot, replaced by newer ones. Once written to TCP a move cannot be taken back, so coalescing must happen before the write; without this a congested path delivers a stream of stale positions after the hand has stopped.
- **The trusted core paces.** Requirement 1.2 says security never depends on the interface's code: the interface passes each change of the dot, and the trusted core keeps the slot, applies the 60 a second, checks the conditions of section 9.1, and alone encodes. The fetcher holds the slot against the socket.
- **The server enforces it too:** a session's moves reach its channel program through one slot of its own, latest wins, at most 60 a second, so a client sending more, or a channel slow to read, never builds a queue of moves. Moves are never acknowledged (they count no input units).
- **Drags** follow the same rule. A channel that draws a path joins the samples with lines, as drawing programs do: at 60 a second a fast stroke skips cells, and sending every cell crossed would break the bound.

### 4.2 What it costs

- **Upstream:** a move is 9 or 10 bytes of payload, 89 to 90 bytes as an IPv4 packet with TLS: 5.4 KB a second, 43 kbit/s, while the pointer moves over a page. Nothing while it is still or elsewhere.
- **Downstream:** no acknowledgement for a move (RCH-012); TCP's own acknowledgements, about 30 a second with delayed ACK, 1.6 KB a second.
- **The channel:** about 130 bytes of JSON a move, 60 lines a second for each viewer moving the pointer over its pages. A thousand viewers moving at once are 60,000 lines a second into one channel program. The server's slot bounds what a slow channel is given; a channel that does nothing with moves still has to read them.
- **Privacy:** the channel learns where the viewer's pointer is over its page while keys go to it, the reading behaviour that the pointer areas used to confine to what a page asked for. `INPUT.md` sections 6.3, 11.3 and 11.4 change accordingly (RCH-038).
- **What it replaces:** pointer areas (`INPUT.md` section 7.4, column mode 01010, the engine's E.128) only asked for moves, so they have no use left; they are withdrawn (decision E). HOVER stays (RCH-040): it is discrete, checked by the trusted core against the page's controls, and spares every channel working out which control the pointer is over.

### 4.3 The document the owner supplied

`tui_mouse_events_conversation.html`, a conversation with an assistant on mouse floods in terminal programs. What it gets right, and is adopted here: the position is state, not a transaction, so a slot that the latest position replaces is right for moves and wrong for presses, releases and keys; throttling, not debouncing (a debounce sends nothing while the pointer moves); flush the waiting move before a button changes; hold moves back while the transport is congested; filter at the sending end, since what is sent cannot be unsent; the xterm modes 1000, 1002 and 1003 as the levels of reporting.

What this design does differently:
- **Its fixed `setInterval`** adds up to a whole period to the first move after a pause and wakes the computer 60 times a second for as long as the page is open. Here the first move goes at once, and nothing runs while the pointer is still.
- **Its rates** (20 to 30 a second for hover) are offered as guesses to benchmark; the owner's 60 matches the display's refresh, so a move can reach the channel within the frame in which it happened.
- **It checks for congestion with the socket's `bufferedAmount`** in a browser's JavaScript; here the slot sits in the trusted core and the fetcher, the point where the bytes are about to enter TCP.
- **It leaves out** a trusted boundary that enforces the rate whatever the interface does, the server's own slot towards a channel that reads slowly, the cost of every channel reading every move, and privacy.
- **Its sources** are partly unverified in the document itself (a wterm issue "not evidence of a merged implementation"; frameworks it did not establish implement backpressure); the xterm modes and hterm's note on mode 1003 are the solid ones.


### 4.4 Touch, for phones and tablets

The browser will be ported to phones and tablets, and Windows and Linux computers already have touch screens (winit reports touch on each with a phase of started, moved, ended or cancelled and an identifier per contact). Touch is designed now so that the protocol and every channel take it without a second change.

**The model** is that of the W3C's Pointer Events, which unify mouse, touch and pen as one pointer with a type and an identifier per contact, and of the platforms below them (iOS's `UITouch`, Android's `MotionEvent`): every contact has a beginning, moves and an end, and the system may cancel it.

- **The first finger is the mouse's left button.** The first contact down on the page goes as MOUSE: a press of button 0 (left) as it touches, moves with button 0 held, a release as it lifts. Every channel that answers the mouse, its buttons, drags, controls and the pressed look, works with touch unchanged, as the web's compatibility mouse events made pages written for the mouse work on phones. On a computer with both, a contact that begins while a mouse button is held goes as TOUCH, so the two never share MOUSE.
- **Which device** is in MOUSE's `flags` bits 4 and 5: 0 a mouse or trackpad, 1 touch, 2 a pen, 3 reserved. A channel that cares, to make a target larger or not to wait for hover, reads it; one that does not ignores it. They are sent only when both sides set the new capability TOUCH (`1 << 20`, `INPUT.md` section 6.2); otherwise they are 0 and touch looks like the mouse.
- **Further fingers go as TOUCH,** an extension (`0x44`, so a channel that does not know it skips it, as it does HOVER): `uv` length, `flags` u8 (bits 0 and 1 the action as MOUSE's: 0 down, 1 up, 2 move, 3 gone; bit 2 `px`, `py` present), `id` u8, `col` uv, `row` uv, `px`? uv, `py`? uv. `id` is 1 to 9, the contact's number for as long as it touches, the lowest free one when it begins; the first finger is contact 0 and goes as MOUSE. At most `MAX_CONTACTS` (10) contacts at once, ten fingers; a further one sends nothing until one lifts. TOUCH is sent only when both sides set TOUCH.
- **Down and up at once.** A contact's beginning and end are written the moment the system reports them, never held to tell a tap from a double tap or a long press (the 300 ms the web's browsers once waited before a tap, to see whether a second would follow and zoom). The browser recognises its own gestures alongside, and if one takes the contact, the channel is told it is gone.
- **Moves, as the mouse's:** each contact's moves follow section 4.1, one slot and one 60-a-second pace per contact; the moves of every contact waiting at the end of a period are written together, in one write (RCH-010). A touch screen samples at 120 to 240 a second and the system gathers the samples between frames (coalesced touches); only the latest is kept. No predicted position is sent: the channel is told where the finger was, never where it may be.
- **Gone, not released.** The system cancels a contact when it takes it for itself (a gesture from the screen's edge, a call, a palm rejected); the browser does when one of its gestures takes it. A cancelled contact goes as action 3 (gone, decision D): its button is released *without* a click, so a channel must not act on it as it would on a release. Action 3 also ends the mouse when it leaves the page (section 4.1), so one meaning serves both: the pointer has gone, and nothing it held was pressed.
- **No hover from a finger.** A finger is over the page only while it touches it, so no move goes for a contact before it is down or after it lifts, and HOVER goes only for a mouse or a pen that hovers. The look of a control under a contact is the pressed look (decision 117), as for a held button.
- **A pen is a pointer that may hover.** A pen goes as MOUSE with device 2: touching is button 0; the barrel button is button 2; hovering, where the hardware reports it (Apple Pencil, Android styluses), sends moves with no button and HOVER as a mouse does. Pressure, tilt and a contact's size are not sent (decision M).
- **Whose contacts.** While keys go to the channel (`INPUT.md` section 9.1), every contact on its page is the channel's, two fingers and a pinch included, as every mouse event is (decision 118: "whenever the mouse is over a teletext display then all mouse events go to it - ALWAYS"), except what begins on a link, which is the browser's (the next item). The browser's gestures, a pinch to zoom and a swipe to step sub-pages, act on pages that do not take input and outside the page, and the system's gestures from the screen's edges are always the system's. The browser zooms a page that takes input with its own controls.
- **A link on a page that takes input** is followed on desktop by a plain click, as on any page, and no button pressed on it reaches the channel (the owner's revision of decision 118 on 28 October 2026, "revise that decision - links must be acted upon by the client browser"; NeoTeletext's decision 122). On touch the same: a contact that begins on a link follows it when it lifts on the link, and no contact begun on a link goes to the channel; a contact begun off a link stays the channel's when it crosses one. A channel that needs a cell of its own to answer a touch makes it a control, not a link.
- **Typing on a touch screen.** A page that asks for typing (a cursor record with a width, `INPUT.md` section 7.1) brings up the system's keyboard; what it types goes as the system gives it: raw text and COMPOSE from an input method, KEY from a hardware keyboard. Soft keyboards mostly give text and not key presses, so a channel must take raw text for typing, as `INPUT.md` section 6.3 already says. The keyboard goes away when the cursor record does.
- **The remote control's keys.** A phone has no Fastext keys and no page-up key. The browser shows its own remote, the digits, Red, Green, Yellow, Blue, the arrows, OK and page up and down, and each sends KEY with the functional code the key has on a keyboard (`INPUT.md` section 5.6), press and release, so a channel cannot tell the remote from a keyboard and needs nothing new.
- **What it costs:** a contact's down or up is a MOUSE of 6 to 9 bytes, or a TOUCH of 8 to 10; each moving contact 89 to 90 bytes a move as a packet, 60 a second, about 5.4 KB a second a finger, and two fingers moving share one write: 103 to 106 bytes a period, about 6.3 KB a second. Downs and ups count as input units, as clicks do; moves and gone count none.
- **Trust.** The trusted core numbers the contacts, keeps their slots and the pace, checks every condition, and alone encodes, as for the mouse (requirement 1.2): the interface passes the system's touches as intents and cannot raise the rate, invent a contact id or exceed `MAX_CONTACTS`.

---

## 5. The owner's decisions and 6. Requirements

In rdm since 30 October 2026 (rdm decision DEC-1389): the decisions as `Return channel decision A` to `N`, the requirements as `REQ-RCH-001` onwards.

## 7. The work

| Repository | Requirements | Notes |
|---|---|---|
| Browser | RCH-001 to 005, 010, 013 to 016, 018, 030 to 036, 040, 041 to 053 | 001 to 003 first: about 10 to 17 ms a key or click, no protocol change. After the second wave of the pages work lands. Touch can be built now for Windows and Linux touch screens, through winit's touch events; the phone and tablet ports take the rest (051, 052). |
| Engine | RCH-010, 013 to 018, 031, 035, 037, 040 to 043, 046 | The input crate's constants and encoder; the web agent's write path. |
| Server | RCH-011, 012, 018, 020 to 028, 039, 045 | Deferred with the server work; another session works in that repository. |
| Kits | RCH-012, 025, 027, 037, 046 | In `neoteletext-server-channels`. |
| `INPUT.md`, `SERVER.md` | RCH-010, 012, 013, 018, 029 to 031, 034, 037, 038, 040 to 043, 046, 049, 050, 054, 055 | Amended as the requirements are adopted; every decision of section 5 is taken. |
