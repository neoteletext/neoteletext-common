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

## 5. The owner's decisions

Taken on 28 October 2026, when the owner accepted every recommendation of this section: "re decisions i accept your recommendations ensure all have a requirement documented". Each will be recorded in the decision log of each repository it binds as the requirements are adopted (section 7).

| | Decision | Why | Requirements |
|---|---|---|---|
| A | The channel says when an input is handled (a line on its standard output, `SERVER.md` section 7.2), and the acknowledgement travels inside the answer's frame; a standalone one only when the channel published nothing. | It saves 118 to 236 bytes and 1 to 2 packets a key, and the count means "acted on", as `INPUT.md` section 7.1 says. | RCH-012 |
| B | Every event numbered; the server acknowledges the last handled; the browser resends what was not acknowledged after a reconnection, and the server drops what it has seen. | It is the only way no key is lost when a connection drops. | RCH-013 |
| C | `INPUT.md` principle 2 reads "one message per event, never held back" in place of "one write per event", so frames already waiting share a write. | A HOVER left and entered go from 172 bytes in 2 packets to 98 in 1, with no change of format. Several events in one message (92 bytes) is not adopted: it changes the format to save 6 bytes. | RCH-010 |
| D | MOUSE action 3 means the pointer left the page. | With every move sent, a channel must know when the pointer is gone. | RCH-034 |
| E | Pointer areas (column mode 01010) withdrawn. | With every move sent they ask for nothing. | RCH-037 |
| F | HOVER stays. | It is one event as the pointer crosses a control, checked by the trusted core, and spares every channel working out which control the pointer is over. | RCH-040 |
| H | Touch is the pointer: the first contact goes as MOUSE button 0, MOUSE's flag bits 4 and 5 say mouse, touch or pen, and further contacts go as TOUCH (extension `0x44`), both under a new capability TOUCH. | Every channel answers touch unchanged; a channel that wants more fingers reads TOUCH; one that does not skips it. | RCH-041 to RCH-043 |
| I | Every contact's beginning and end is written at once, never held for gesture recognition; moves paced per contact as the mouse's. | The lowest latency, and the owner's 60 a second for every pointer. | RCH-044, RCH-045 |
| J | Action 3 (decision D) also means a contact was cancelled: its button released without a click. | One meaning, "gone", serves the mouse leaving the page and a contact the system or the browser took. | RCH-046 |
| K | While keys go to a channel every contact on its page is the channel's, pinch included; the browser's gestures act elsewhere, and its zoom on an input page is its own controls. | The owner's rule for the mouse, decision 118: "ALWAYS". | RCH-047 |
| L | A tap on a link follows it on every page, a page that takes input included, and no contact begun on a link goes to the channel. *Revised 28 October 2026:* it was a long press of the platform's own time, until the owner's "revise that decision - links must be acted upon by the client browser". | A link the page declares means only "go to that page", and following pages is the browser's. | RCH-048 |
| M | Pressure, tilt and contact size are not sent. | A page is 40 by 25 cells; the fewest bytes (the owner's instruction). An extension can add them if a channel ever needs them. | RCH-050 |
| N | The system's keyboard appears when a page asks for typing; the browser's own remote sends the remote control's keys as KEY. | No new event: a channel cannot tell them from a keyboard. | RCH-051, RCH-052 |
| G | The transport stays the push WebSocket over TCP and TLS; no UDP, QUIC, WebTransport or WebRTC, no TCP Fast Open or TLS 0-RTT for events, no DSCP marking. | Section 3.2: one reliable ordered stream is needed anyway, and the others cost reach and a second transport. | RCH-018 |

Decisions H to N were taken on 28 October 2026 under the owner's instruction to integrate touch ("now is the time to integrate touch into these decisions. do it"), as recommended here; their details are for the owner to confirm. The pointer's moves at 60 a second (section 4) are the owner's own decision of 28 October 2026, a move going at once when 1000/60 ms have passed since the last was sent (the owner's confirmation of the same day). The faults of sections 2.2 and 2.4 need no decision: each is fixed by its requirement.

---

## 6. Requirements

Area RCH, the return channel. Each requirement names the repository that carries it; when adopted, each becomes or amends a requirement there (the browser's section 18, the engine's area INT, the server's sections 5 to 7) and `INPUT.md` section 12, and is marked so here. Those that come from a decision of section 5 name it.

### 6.1 The browser

**REQ-RCH-001 — The answer drawn as it arrives** (browser). A packet of the page the viewer is typing into or pointing at shall be drawn as soon as it arrives; a frame that changed nothing shall not delay the next. *Verification:* a timed test: an acknowledgement's frame followed 2 ms later by the answer's draws the answer within 2 ms of its arrival. *Built 28 October 2026, the browser's requirement 18.11 (its decision 122):* `the_answer_after_an_acknowledgement_is_drawn_as_it_arrives` (14 ms on the code before, within 2 ms now), `a_frame_that_changed_nothing_does_not_delay_the_next`, `changes_are_paced_from_the_last_frame_presented`, `nothing_is_drawn_while_nothing_changes`, `the_page_under_the_pointer_is_known`.

**REQ-RCH-002 — No hold after an input** (browser). The first frame of a page after an input to it shall not be held by the trusted core's interval between frames (`frames.rs`), and a frame that changes only the hover or pressed look shall not count towards that interval; the bound the interval exists for (finding F-11) shall still hold. *Verification:* a trusted-core test: a click on a control, its look, then the channel's answer within 1 ms: the answer is sent at once. *Built 28 October 2026, the browser's requirement 18.12 (its decision 122):* three clocks of one field a page, content, look and answer, so at most three frames a field; `a_click_on_a_control_its_look_then_the_answer_goes_at_once`, `the_first_frame_after_an_input_is_not_held`, `a_frame_held_before_an_input_keeps_its_clock`, and for F-11 `a_page_s_frames_are_sent_at_most_once_a_field` and `inputs_and_looks_keep_a_page_to_its_clocks`.

**REQ-RCH-003 — Input before drawing** (browser). An input shall be written to the trusted core before any frame it causes is drawn. *Verification:* a test of the interface's order of output. *Built 28 October 2026, the browser's requirement 18.13 (its decision 122):* what an event sends is written once the event is handled; `an_input_reaches_the_core_before_the_frame_it_asks_for`, the event handlers by inspection.

**REQ-RCH-004 — One frame queued** (browser). Each platform's presentation shall keep at most one frame queued. *Verification:* by inspection of each platform's surface configuration; `NEOTELETEXT_FRAME_TRACE` timings. *Met by inspection 28 October 2026, the browser's requirement 18.14 (its decision 122):* softbuffer 0.4.8 on every platform keeps one frame at most, with no swap chain (the browser's `interface/src/app/frame.rs`); not yet timed with `NEOTELETEXT_FRAME_TRACE`.

**REQ-RCH-005 — Every button and modifier** (browser). The middle, right, back and forward buttons and the mouse's modifiers shall be sent as `INPUT.md` section 5.4 says. *Verification:* interface and trusted-core tests of each button and modifier. *Built 28 October 2026, the browser's requirement 18.15 (its decision 122, which lists the conflicts with other browsers' uses of the buttons for the owner):* `every_button_and_modifier_goes_over_the_page`, `every_button_and_modifier_goes_as_input_md_lays_it_out`.

### 6.2 The protocol (`INPUT.md`, the engine's area INT)

**REQ-RCH-010 — One message per event, never held back** (common, engine, browser; decision C). Each event shall be its own WebSocket message, written as it happens; messages already waiting to be written at the same moment shall be written together, in one TLS record where the TLS layer allows; nothing shall be held back to be grouped. Amends `INPUT.md` principle 2, section 8 rule 1 and REQ-INT-112. *Verification:* a fetcher test: two events given together leave in one write, in order; a timed test that a lone event is not delayed.
*Built 28 October 2026 (engine E.133):* `INPUT.md` principle 2, section 8 rule 1 and REQ-INT-112 amended. The engine's web agent sends every frame written while it handles one input as one send (`Input::Send` of an `InputMessage` with `more`); `neottx`'s fetcher marks `more` when another input message waits. Tests: `messages_waiting_together_leave_in_one_write` (`neoteletext-web/tests/agent_replay.rs`). *Built 28 October 2026 (NeoTeletext decision 125), the fetcher's part, the browser's requirement 18.30:* each `ToFetcher::Send` carries `more`; the fetcher's reader gives the loop a moment's messages together (at most a move of every contact and one other event), and the loop hands them to the agent with `more` on all but the last, and on the last too when another moment is already read. Tests: `the_messages_of_one_moment_reach_the_agent_together_and_leave_in_one_write` (`native/fetcher/src/process.rs`), `every_kind_round_trips` (`native/protocol`). The trusted core's setting of `more` is not built.

**REQ-RCH-011 — No tick on the path** (all). No hop of the return channel, the browser's processes, the fetcher, the server and the channel kits, shall send an event or an answer on a timer, save the pointer's moves (section 4); each shall block on readiness. *Verification:* by inspection of each hop; the latency tests.

**REQ-RCH-012 — Acknowledgement in the answer** (server, kits, common; decision A). A channel shall say when it has handled an input; the server shall carry the acknowledgement in the frame of the answer when there is one, and send one alone only when the channel published nothing; a message of no input units (a move, HOVER, COMPOSE) shall not be acknowledged. *Verification:* server tests of each case; a byte count of one keystroke.
*Built 28 October 2026 (engine E.133):* `INPUT.md` section 7.1 says the acknowledgement may travel in the answer's frame and that nothing of no input units is acknowledged (REQ-INT-110, REQ-INT-126). The engine counts a move, gone, HOVER, COMPOSE and RESUME as no units (`event::units`) and takes a cursor record among a page's packets or alone. Tests: `the_input_count_counts_characters_and_events`, `what_is_never_acknowledged_counts_nothing` (`neoteletext-input`), `an_acknowledgement_is_taken_in_the_answers_frame_and_alone` (`neoteletext-cli`). The server's part is not built.

**REQ-RCH-013 — Numbered events, resent after a reconnection** (common, engine, browser, server; decision B). Every event that counts as input shall carry its number in the session; the server shall acknowledge the last number handled; after a reconnection the browser shall resend, in order, what was not acknowledged, and the server shall drop what it has already handled. The number is bounded and wraps as the input count does. *Verification:* a reconnection test with events in flight: each reaches the channel exactly once.
*Built 28 October 2026 (engine E.133):* specified in `INPUT.md` section 6.4 (REQ-INT-125): numbering by the input count, a token in WELCOME, RESUME after HELLO, the count taken in a resumed WELCOME. The receiver's side is `neoteletext_input::session::ResumableSession` (`open`, `close`, `forget`, `welcome`, `resend`, `acknowledged`). Tests: `a_resumed_session_sends_again_only_what_the_channel_had_not_taken`, `a_session_not_held_is_a_new_one_and_a_false_count_is_refused`, `what_is_kept_is_bounded`, `a_session_that_keeps_nothing_never_offers_resume`, `welcome_carries_the_session_with_resume`, `resume_round_trips_and_is_checked`; fuzz target `input_session`. The browser's and the server's parts, and the reconnection test with events in flight, are not built. *Built 28 October 2026 (NeoTeletext decision 125)*, the trusted core's part, the browser's requirement 18.21: each channel's session is a `ResumableSession` offering RESUME; a lost connection closes it, the next opens with HELLO and RESUME, a resumed WELCOME sends again what the channel had not taken, then RESIZE, the focus and PAGE; a new one starts afresh; leaving the channel forgets it. Tests: `a_resumed_session_sends_again_what_the_channel_had_not_taken`, `a_session_not_held_begins_again`, `without_resume_or_after_leaving_a_reconnection_is_new`, `a_false_count_is_refused` (`native/core/src/typing/tests/resume.rs`). The reconnection test with events in flight is the server's.

**REQ-RCH-014 — A warm connection, never replayable** (engine, browser). The push WebSocket shall open with the tab and stay open while the channel's pages are shown, pinging after `PUSH_PING_AFTER_US` (25 s) of silence; a reconnection shall resume the TLS session where the server allows; no event shall travel in TLS 0-RTT data or a TCP Fast Open SYN. *Verification:* tests of the ping and of resumption; by inspection of the TLS configuration.
*Built 28 October 2026 (engine E.133):* the agent's ping after 25 s stays (`a_silent_websocket_is_pinged_then_given_up`); the `Transport` contract asks a port to resume TLS and forbid early data and TCP Fast Open; `neottx`'s transport shares one rustls configuration with its in-memory session store and no early data (`tls_resumes_and_sends_no_early_data`). *Built 28 October 2026 (NeoTeletext decision 125), the browser's requirement 18.33:* the fetcher's transport shares one rustls configuration, resumption on, early data off, and no TCP Fast Open; test `a_reconnection_resumes_the_tls_session_and_sends_no_early_data` (`native/fetcher/src/transport/tests.rs`: the second connection to a local TLS server that would take early data is resumed, and neither sends any).

**REQ-RCH-015 — The push socket alone** (engine, browser). The push WebSocket shall be a connection of its own, over HTTP/1.1, never multiplexed with fetches. *Verification:* by inspection; a fetch of a large file during typing does not delay an answer.
*Built 28 October 2026 (engine E.133):* as it was: `ConnectionId::Push`, an HTTP/1.1 upgrade (`the_push_socket_is_a_connection_of_its_own`).

**REQ-RCH-016 — The round trip measured on the connection** (engine, browser). The strip's round trip shall be measured by WebSocket ping and pong, at most once a second and only while keys go to the channel, not from acknowledgements. Amends REQ-INT-131 and REQ-INT-137. *Verification:* a trusted-core test.
*Built 28 October 2026 (engine E.133):* `Input::MeasureRoundTrip(bool)` and `Event::RoundTrip { microseconds }`: a one-byte ping at most once in `ROUND_TRIP_EVERY_US`; `Session::acknowledged` no longer gives a round trip. Test: `the_round_trip_is_measured_by_ping_and_pong`. *Built 28 October 2026 (NeoTeletext decision 125), the fetcher's part, the browser's requirement 18.32:* `ToFetcher::MeasureRoundTrip(on)` is passed to the agent and `Event::RoundTrip` reaches the trusted core as `FromFetcher::RoundTrip { microseconds }`; tests `the_round_trip_is_measured_and_told_to_the_core` (`native/fetcher/src/process.rs`), `a_move_is_marked_only_as_its_own_contacts` (`native/protocol`). The browser's strip is not built. *Built 28 October 2026 (NeoTeletext decision 125)*, the trusted core's and the strip's part, the browser's requirement 18.22: `ToFetcher::MeasureRoundTrip` on exactly while keys go, `FromFetcher::RoundTrip` shown in the strip in milliseconds to a tenth; acknowledgements give no round trip. Tests: `the_round_trip_is_measured_while_keys_go`, `the_strip_says_where_keys_go`.

**REQ-RCH-017 — Binary frames, uncompressed** (engine, server). Input shall go in binary frames; permessage-deflate shall be refused. Stands as built; recorded so that it stays. *Verification:* the engine's and the server's WebSocket tests.
*Built 28 October 2026 (engine E.133):* stands as built: binary frames (`input_goes_on_the_push_websocket_only_when_declared`), permessage-deflate refused and never asked for (`ws::tests`, `the_push_socket_is_a_connection_of_its_own`).

**REQ-RCH-018 — The transport** (all; decision G). Input and its answers shall travel on the push WebSocket over TCP and TLS, and on no other transport; no event shall be marked for a class of service. *Verification:* by inspection.

### 6.3 The server and the channels

**REQ-RCH-020 — Answers first** (server). Each session's queue to its client shall send, in this order of priority: acknowledgements and answers to input; audio; the header; shared and background pages. Within each class the order is kept. *Verification:* a test: an answer queued behind 175 KB of shared pages leaves first.

**REQ-RCH-021 — The backlog stays where it can be reordered** (server). Each client socket shall keep its unsent bytes in the kernel under a bound (`TCP_NOTSENT_LOWAT` where the platform has it), the rest waiting in the session's queue. *Verification:* by inspection; the test of RCH-020 over a throttled link.

**REQ-RCH-022 — Only the rows that changed** (server). An answer that changes some rows of a page shall send those rows and the header, as `SERVER.md` section 6.3 designs, not the whole page. *Verification:* a byte count of one keystroke on a text field: at most the header, the changed row and the cursor.

**REQ-RCH-023 — Only the sub-page that changed** (server). An answer shall send only the sub-page it changes, never every sub-page of the page; with 8,190 sub-pages allowed (the engine's REQ-NUM-020) nothing else is bounded. *Verification:* a test with a page of many sub-pages.

**REQ-RCH-024 — No line lost** (server). The relay from a channel program shall keep its partly read line across every other event it waits on. *Verification:* a test that interleaves input with long publish lines.

**REQ-RCH-025 — A cursor checked at publish** (server, kits). The server shall refuse at publish a cursor that `INPUT.md` section 7.1 forbids, and still acknowledge without a cursor; the components kit shall write no echo at width 0. *Verification:* the full-field case of section 2.4.

**REQ-RCH-026 — Nothing sent is dropped** (server). The server's runtime shall pass a channel the key modifiers, the mouse's dot and modifiers, and COMPOSE. *Verification:* runtime tests of each field.

**REQ-RCH-027 — A channel's lines flushed** (kits, common). A channel shall flush each line it writes; both kits shall, and `SERVER.md` section 7 shall say so. *Verification:* a kit test with a pipe.

**REQ-RCH-028 — Socket options** (server, deployment). Every socket of the path shall have `TCP_NODELAY`, whatever terminates TLS in front of the server included; the server's sockets shall have `TCP_THIN_LINEAR_TIMEOUTS` on Linux. *Verification:* by inspection of the server and the deployment configuration.

**REQ-RCH-029 — The bytes of section 5.8** (common). `INPUT.md` section 5.8 shall give each event as it is now sent (KEY for every key since E.125). *Verification:* a test that encodes each row of the table.
*Built 28 October 2026 (engine E.133):* `INPUT.md` section 5.8 rewritten; test `the_size_examples_of_section_5_8` encodes every row.

### 6.4 The pointer's moves

**REQ-RCH-030 — Every move over the page** (common, browser). While the pointer is over the open page and keys go to its channel, every change of the dot under it shall reach the channel as MOUSE move, within at most one period of RCH-031, buttons held or not. Amends `INPUT.md` sections 5.4 and 6.3, REQ-INT-136, decision 118. *Verification:* a trusted-core test of moves with and without a button.
*Built 28 October 2026 (engine E.133):* `INPUT.md` sections 5.4, 6.3 and REQ-INT-115, REQ-INT-136 amended. The trusted core's part is the browser's (not built). *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.16: the interface gives each change of the dot over the open page, buttons held or not; the buttons a move holds are those the trusted core sent pressed. Tests: `every_move_goes_with_the_buttons_the_core_sent_held` (`native/core/src/typing/tests/pointer.rs`), `every_move_goes_and_leaving_the_page_is_gone` (`native/interface-core/src/browser/typing/tests.rs`).

**REQ-RCH-031 — Sixty a second** (common, browser, server). At most one move shall go in each period of 1000/60 ms, as one named constant of the engine's input crate. While moves follow each other, the *k*th period ends at the time of the move that began the run plus *k* × 1,000,000 / 60 µs, so the average is exactly 60 a second; a move sent at once (RCH-032) begins a new run. *Verification:* a test of 1,000 moves in one second: 60 sent, with no drift over 10 s.
*Built 28 October 2026 (engine E.133):* `neoteletext_input::MOVES_PER_SECOND` and `pace::Pacer`, the deadlines counted exactly. Tests: `the_period_is_a_sixtieth_of_a_second`, `a_thousand_moves_a_second_go_sixty_with_no_drift` (`neoteletext-input/src/pace/tests.rs`); fuzz target `input_session`. The server's part is not built. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.16: the trusted core paces with `pace::Pacer`, one per channel session, at its one timer. Test: `a_thousand_moves_a_second_go_sixty_a_second` (10,000 moves in 10 s give 600 or 601).

**REQ-RCH-032 — A move goes at once if it can, the latest kept** (browser). Whether a move waits depends only on when the last move was sent: a move that comes 1000/60 ms or more after the last move sent shall go at once; one that comes sooner shall wait in one slot, replacing any position waiting there, and go when 1000/60 ms have passed since the last move sent. An unchanged position shall not go again, and nothing shall run while the pointer is still. *Verification:* trusted-core tests: a move 20 ms after the last goes at once; a move 5 ms after the last goes 16⅔ ms after the last, carrying the latest position; no timer is armed while the slot is empty.
*Built 28 October 2026 (engine E.133):* in `pace::Pacer` (`offer`, `due`, `take_due`), for the trusted core to use. Test: `a_move_goes_at_once_if_it_can_and_the_latest_is_kept`. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.16. Test: `a_move_goes_at_once_if_it_can_and_the_latest_is_kept`.

**REQ-RCH-033 — Order kept** (browser). Before any other event is written, a move waiting in the slot shall be written first. *Verification:* a drag ending in a release within a period: the last move precedes the release.
*Built 28 October 2026 (engine E.133):* `pace::Pacer::flush`. Test: `a_waiting_move_is_flushed_before_any_other_event`. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.16. Test: `a_waiting_move_goes_before_the_release`.

**REQ-RCH-034 — Leaving the page** (common, browser; decision D). When the pointer leaves the page, or keys stop going to the channel, the waiting move shall be written and then MOUSE with action 3. *Verification:* a trusted-core test.
*Built 28 October 2026 (engine E.133):* MOUSE action 3 (`MouseAction::Gone`), `INPUT.md` section 5.4. Tests: `mouse_action_3_is_gone`, `gone_releases_what_the_pointer_held`. The trusted core's part is the browser's. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.17: `Intent::Gone` as the pointer leaves the page (winit's `CursorLeft` included), and the same for the pointer and every contact as keys stop going, before `FOCUS_OUT` or PAGE. Tests: `leaving_the_page_sends_the_waiting_move_then_gone`, `keys_stopping_send_the_waiting_move_then_gone`, `every_move_goes_and_leaving_the_page_is_gone`.

**REQ-RCH-035 — Never behind the network** (engine, browser). The fetcher shall write a move only while the push socket's unsent bytes are under a bound, holding it otherwise in one slot that a newer move replaces; any other event shall first write the held move, then itself, and never wait behind a move. *Verification:* a fetcher test against a stalled socket: after the stall, one move, the latest, is written.
*Built 28 October 2026 (engine E.133):* `Transport::unsent`, `NetInput::Unsent`, `Pump`'s reports at `PUSH_UNSENT_BOUND`, and the agent's slot per contact (`InputMessage::move_of`). Test: `moves_wait_while_the_socket_is_stalled_and_only_the_latest_goes`. `neottx`'s transport reports no unsent bytes (`TECH-DEBT.md`). *Built 28 October 2026 (NeoTeletext decision 125), the fetcher's part, the browser's requirement 18.31:* the fetcher writes each connection on a thread of its own and reports what it was given and has not written (`Transport::unsent`, through `Pump`), and passes the trusted core's `move_of`, which the protocol refuses on anything but one move of that contact; test `a_stalled_socket_is_told_behind_then_drained_and_holds_nothing_up` (`native/fetcher/src/transport/tests.rs`). The operating system's own socket buffer is not seen (it needs unsafe code), so a move is held only once that buffer is full; the trusted core's tagging of moves is not built.

**REQ-RCH-036 — The trusted core paces** (browser). The pacing of RCH-031 to RCH-034 shall be the trusted core's; the interface passes each change of the dot as an intent and nothing it sends can raise the rate. *Verification:* a hostile-interface test sending 1,000 moves a second. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.16. Hostile-interface tests: `a_thousand_moves_a_second_go_sixty_a_second`, `every_move_goes_with_the_buttons_the_core_sent_held`.

**REQ-RCH-037 — Pointer areas withdrawn** (common, engine, browser, kits; decision E). Column mode 01010 shall be read as reserved again, as EN 300 706 Table 29 has it; `INPUT.md` section 7.4, the engine's E.128 and `MAX_POINTER_AREAS` withdrawn. *Verification:* the engine's control triplet tests.
*Built 28 October 2026 (engine E.133):* column mode 01010 reserved again; `MAX_POINTER_AREAS`, `Controls::pointer_areas`, `whole_page`, `MODE_POINTER_AREA` and the author API's pointer areas removed; E.128 withdrawn; `INPUT.md` section 7.4 and REQ-INT-120 withdrawn. Test: `column_mode_01010_is_reserved_again`. The kits' part is not built.

**REQ-RCH-038 — Privacy stated** (common). `INPUT.md` sections 6.3, 11.3 and 11.4 shall say that a channel learns the pointer's position over its own page while keys go to it, and nothing elsewhere: not over another tab, the browser's own controls, or another window. *Verification:* by inspection; the trusted-core test of RCH-030's conditions.
*Built 28 October 2026 (engine E.133):* `INPUT.md` sections 6.3, 11.3 and 11.4.

**REQ-RCH-039 — The server's slot** (server). Each session's moves shall reach its channel program through one slot, the latest replacing any not yet taken, at most 60 a second; moves shall count no input units and never be acknowledged. *Verification:* a server test with a channel that reads slowly: it is given the latest move, never a backlog.

**REQ-RCH-040 — HOVER stays** (common, engine, browser; decision F). HOVER shall go as the pointer enters and leaves each control, as `INPUT.md` section 5.4 says, alongside the moves; the trusted core shall send it only for a control of the open page's latest image. Stands as built. *Verification:* the existing HOVER tests.
*Built 28 October 2026 (engine E.133):* stands as built (`hover_round_trips_and_is_checked`); it now counts no units.


### 6.5 Touch

**REQ-RCH-041 — The first contact is the mouse** (common, engine, browser; decision H). The first contact down on the page shall go as MOUSE, a press of button 0 as it touches, moves with button 0 held, a release as it lifts; a channel that does not set TOUCH shall see nothing that a mouse would not send. *Verification:* a trusted-core test of a tap and a drag; an encoder test with TOUCH not negotiated.
*Built 28 October 2026 (engine E.133):* `TOUCH_CAP` and `Session::send`, which sends MOUSE's device and TOUCH only with it; `contacts::Contacts` gives contact 0 to the first. Tests: `touch_goes_only_when_both_sides_set_it`, `the_mouse_and_a_finger_never_share_mouse_and_inventions_are_refused`. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.18, on Windows and Linux (macOS's trackpads give no touch): TOUCH offered in HELLO; the first contact as MOUSE, device touch, button 0. Tests: `the_first_contact_is_the_mouse_and_the_next_touch`, `without_touch_a_finger_is_the_mouse_alone`, `a_contact_while_a_button_is_held_is_touch`.

**REQ-RCH-042 — Which device** (common, engine, browser; decision H). MOUSE's `flags` bits 4 and 5 shall give the device, 0 mouse or trackpad, 1 touch, 2 pen, 3 reserved and a protocol error, and shall be set only when both sides set the capability TOUCH (`1 << 20`). *Verification:* encoder and decoder round trips; the reserved value refused.
*Built 28 October 2026 (engine E.133):* `Device` in MOUSE's `flags` bits 4 and 5, 3 refused. Test: `mouse_carries_its_device`. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.18: device 1 for a finger; device 2 not sent, since winit 0.30.13 tells no pen from a finger.

**REQ-RCH-043 — Further contacts as TOUCH** (common, engine, browser; decision H). Every contact after the first shall go as TOUCH, extension `0x44`, with the layout of section 4.4, its `id` 1 to 9, the lowest free when it begins and kept until it ends, at most `MAX_CONTACTS` (10) contacts at once, and only when both sides set TOUCH; a further contact sends nothing until one ends. *Verification:* round trips; a test of ids under ten contacts beginning and ending in turn; a decoder fuzz target.
*Built 28 October 2026 (engine E.133):* `Event::Touch`, extension `0x44`, `MAX_CONTACTS`, `MAX_TOUCH_ID`; `contacts::Contacts`. Tests: `touch_round_trips_and_is_checked`, `contacts_take_the_lowest_free_number`; fuzz target `input_stream`. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.18. Tests: `the_first_contact_is_the_mouse_and_the_next_touch`, `a_hostile_interface_cannot_invent_a_contact`.

**REQ-RCH-044 — Down and up at once** (browser; decision I). A contact's beginning and end shall be written when the system reports them, never held to recognise a gesture; the browser's gesture recognition shall run alongside. *Verification:* a trusted-core test: a touch's press is sent within 1 ms of its intent, with a long press recognised later. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.18: a contact's beginning and end go as the intent arrives; the browser has no gestures. Tests: `the_first_contact_is_the_mouse_and_the_next_touch`, `a_contact_on_the_page_goes_to_the_channel`.

**REQ-RCH-045 — Moves per contact** (browser, server; decision I). Each contact's moves shall follow RCH-030 to RCH-035 with a slot and a pace of its own; moves of several contacts waiting at the same moment shall be written together; only the latest of the system's coalesced samples shall be kept, and no predicted position sent. The server's slot (RCH-039) shall be per contact. *Verification:* a test of two contacts moving: at most 60 moves a second each, in shared writes.
*Built 28 October 2026 (engine E.133):* one slot and pace a contact in `pace::Pacer`, the moves due at one moment given together; the agent's slots per contact. Tests: `each_contact_is_paced_alone_and_due_moves_come_together`, `moves_wait_while_the_socket_is_stalled_and_only_the_latest_goes`. The browser's and the server's parts are not built. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's part, its requirement 18.18. Test: `each_contact_is_paced_alone_and_due_moves_leave_together`.

**REQ-RCH-046 — Gone** (common, engine, browser; decisions D and J). A contact the system or the browser cancels shall go as action 3, its button released without a click; a channel shall not act on it as on a release. *Verification:* a trusted-core test of a cancelled contact; the kits' tests that a gone press does not click.
*Built 28 October 2026 (engine E.133):* TOUCH's and MOUSE's action 3; `held::Held` releases without a click. Test: `gone_releases_what_the_pointer_held`. The kits' part is not built. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's part, its requirement 18.18: a cancelled contact, and one that leaves the page, as gone. Tests: `a_cancelled_contact_is_gone`, `a_contact_on_the_page_goes_to_the_channel`.

**REQ-RCH-047 — Whose contacts** (browser; decision K). While keys go to the channel, every contact on its page shall be the channel's, several fingers and a pinch included, except one begun on a link (REQ-RCH-048); the browser's gestures shall act only on pages that do not take input and outside the page, and the system's edge gestures are the system's. *Verification:* interface tests of a pinch on a page that takes input and on one that does not.

**REQ-RCH-048 — A link is the browser's** (browser; decision L, revised 28 October 2026). On every page, a page that takes input included, a click or a contact that begins on a link the page declares shall follow it when released on it, and no press, release or contact begun on a link shall go to the channel; a drag or contact begun off a link stays the channel's when it crosses one. *Verification:* interface tests of a click and a tap on a link of a page that takes input, and of a drag across one. *Built 28 October 2026 for the mouse (NeoTeletext's decision 122, `a_link_on_a_page_that_takes_input_is_the_browsers`); touch with the phone and tablet ports.* *Built 28 October 2026 (NeoTeletext decision 125)* for touch, the browser's requirement 18.19: `a_contact_on_a_link_follows_it_and_never_reaches_the_channel`.

**REQ-RCH-049 — No hover from a finger** (common, browser). No move shall go for a touch contact before it is down or after it lifts, and HOVER shall go only for a mouse or a pen that hovers; a control under a contact shall show the pressed look. *Verification:* trusted-core tests.
*Built 28 October 2026 (engine E.133):* `INPUT.md` sections 5.4, 9.7 and 9.8. The browser's part is not built. *Built 28 October 2026 (NeoTeletext decision 125)* in part, the browser's requirement 18.18: no move for a finger before it is down or after it lifts, and no HOVER from one (`the_first_contact_is_the_mouse_and_the_next_touch`); a control under a contact does not yet take the pressed look.

**REQ-RCH-050 — A pen** (common, browser; decision M). A pen shall go as MOUSE with device 2, touching as button 0 and its barrel button as button 2, hovering as moves with no button and HOVER where the hardware reports it; pressure, tilt and contact size shall not be sent. *Verification:* trusted-core tests.
*Built 28 October 2026 (engine E.133):* `Device::Pen`, `INPUT.md` section 9.8. The browser's part is not built.

**REQ-RCH-051 — The system's keyboard** (browser; decision N). A page whose cursor record asks for typing shall bring up the system's keyboard while keys go to its channel, and the keyboard shall go when the record does; its text shall go as raw text and COMPOSE, and a hardware keyboard's keys as KEY. *Verification:* interface tests on each touch platform.

**REQ-RCH-052 — The remote control's keys** (browser; decision N). A touch device shall show the browser's own remote, the digits, the four Fastext colours, the arrows, OK and page up and down, each sending KEY with its functional code, press and release, as the keyboard's key would. *Verification:* a test that each remote key encodes as its keyboard key.

**REQ-RCH-053 — Contacts checked by the trusted core** (browser). The trusted core shall number the contacts, keep their slots and pace, and check each intent: a contact id the interface invents, a move or end for a contact not begun, or more than `MAX_CONTACTS`, shall be refused. *Verification:* a hostile-interface test.
*Built 28 October 2026 (engine E.133):* `contacts::Contacts` refuses a contact begun twice and numbers none not begun, for the trusted core to use (`the_mouse_and_a_finger_never_share_mouse_and_inventions_are_refused`). The hostile-interface test is the browser's. *Built 28 October 2026 (NeoTeletext decision 125)*, the browser's requirement 18.18. Hostile-interface test: `a_hostile_interface_cannot_invent_a_contact`.

**REQ-RCH-054 — The units of touch** (common). A contact's down and up shall count as input units as a click does; a move and gone shall count none (`INPUT.md` section 8 rule 4). *Verification:* a rate test with ten contacts.
*Built 28 October 2026 (engine E.133):* `event::units`; `INPUT.md` sections 7.1 and 8 rule 4. Tests: `the_input_count_counts_characters_and_events`, `what_is_never_acknowledged_counts_nothing`.

**REQ-RCH-055 — The sizes** (common). `INPUT.md` section 5.8 shall give a tap, a second finger's down and a two-finger move. *Verification:* the test of RCH-029.
*Built 28 October 2026 (engine E.133):* `INPUT.md` section 5.8; test `the_size_examples_of_section_5_8`.

---

## 7. The work

| Repository | Requirements | Notes |
|---|---|---|
| Browser | RCH-001 to 005, 010, 013 to 016, 018, 030 to 036, 040, 041 to 053 | 001 to 003 first: about 10 to 17 ms a key or click, no protocol change. After the second wave of the pages work lands. Touch can be built now for Windows and Linux touch screens, through winit's touch events; the phone and tablet ports take the rest (051, 052). |
| Engine | RCH-010, 013 to 018, 031, 035, 037, 040 to 043, 046 | The input crate's constants and encoder; the web agent's write path. |
| Server | RCH-011, 012, 018, 020 to 028, 039, 045 | Deferred with the server work; another session works in that repository. |
| Kits | RCH-012, 025, 027, 037, 046 | In `neoteletext-server-channels`. |
| `INPUT.md`, `SERVER.md` | RCH-010, 012, 013, 018, 029 to 031, 034, 037, 038, 040 to 043, 046, 049, 050, 054, 055 | Amended as the requirements are adopted; every decision of section 5 is taken. |
