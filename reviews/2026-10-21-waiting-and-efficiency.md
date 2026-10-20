# Threads, polling, async and efficiency: engine and browser

Review of 21 October 2026, on the owner's request, of `neoteletext-engine` at 05dc488 and `neoteletext-browser` at c887b5b: how every program waits, what it does when nothing happens, what it copies, and how the design carries to microcontrollers. Findings marked *confirmed* were checked in the code for this review; *reported* ones come from reading the code but were not checked a second time; *measured* ones were measured on 21 October 2026 on this computer (Apple silicon, macOS) unless another date is given.

## 1. The answer in short

- **Keep threads on desktops; do not adopt an async runtime.** No program here has more than a handful of connections; every process already waits on one channel or one blocking read; the two fetchers, rewritten today to wake on arrival, answer a key in 0.2 to 0.5 ms. `tokio` would be a large dependency to approve, more system calls for the fetchers' sandboxes to allow, and buys nothing at three sockets.
- **Keep the engine's libraries synchronous and sans-IO.** They take time and bytes and return outputs; that shape runs under threads, under an async executor and in a bare main loop alike. Making them `async` would tie them to an executor and make no microcontroller build easier.
- **The one change of design worth making is in the libraries: every state machine should say when it next needs time.** The web agent and the live-feed machine already do (`Output::Timer`); the core decoder and the audio receiver do not, so every port ticks them blindly, and the browser wakes every decoder twelve times a second for it. With deadlines everywhere, a port on any system sleeps until a byte, a key or a deadline, and nothing else.
- **On microcontrollers, async is the natural port shape** (an `embassy` task per machine, or one loop that `select`s), and a superloop with `WFI` is equally valid where the main loop belongs to video (tellyboy's rule: the programmer writes only a main program). The engine needs no change for either; the port does the waiting.
- **The waste left on desktops is timer-driven redrawing, not polling for input.** The browser renders every shown page 12 times a second whether it flashes or not; `neottx view` wakes 25 times a second and holds each page arrival for up to 40 ms; copies and per-message flushes multiply the cost.
- **Three bugs** turned up (section 4).

## 2. How each program waits

### 2.1 The engine

| Part | How it waits | Idle cost |
|---|---|---|
| Libraries (core, formats, web, audio, audio-mix, input, image) | Not at all: no threads, clock, input or output (`cargo xtask check-io`). The caller passes time in; the web agent and the live-feed machine return their next deadline; the core decoder and audio receiver must be ticked. | — |
| `neottx fetch` (the fetcher process) | One channel: requests from the decoder, a reader thread per connection, the pipe's end; sleeps until one comes or the agent's deadline (decision E.97). | None for the web; 5 a second forever once a live feed has given up (section 4). |
| `neottx view` | `crossterm` poll of the terminal for 40 ms (`TICK`), then everything else: the fetcher's frames, the session, a full compose. | 25 wakeups a second, always, each composing the page and comparing the whole grid. |
| `neottx keyboard` | `Screen::poll(50 ms)` on the relay socket. | 20 a second, each allocating 4 KB and setting the socket's timeout. |
| Non-interactive live input (`input.rs`) | `sleep(20 ms)` loop for `--duration`. | 50 a second. |

### 2.2 The browser

| Process | How it waits | Idle cost |
|---|---|---|
| Trusted core | One channel fed by a reader thread per pipe; two timer threads: flash every 83.3 ms, load every 200 ms. | 17 wakeups a second forever. Each flash tick writes a `Tick` to every decoder, shown or not. The load tick does nothing once every file has been read, and nothing at all for web channels. |
| Decoder (one per tab) | Blocking read of the core's pipe. | Woken 12 times a second by the core; renders every shown page each time (3.3 ms a page, release build), whether or not anything on it flashes. Recorded as about 7 s of processor time a minute for the shown channel (`native-interface-design.md`; requirement 9.7, which says it is to be made cheaper). |
| Fetcher | One channel, as `neottx fetch` (decision 46). | None. |
| Interface | winit's `Wait`/`WaitUntil`, paced by what moves on screen; a thread polling the mixers every 250 ms; the audio callback. | The poll 4 times a second; the audio stream plays silence for ever. Each redraw is the whole window, about 13 ms at 1440 × 900 (recorded): 10 a second for 3 s after any update, and for good while a channel updates more often than every 3 s. |
| Keyboard | `Screen::poll(50 ms)`. | 20 a second while open. |
| Reference channel (`neoteletext-site`) | 100 ms socket timeouts per session; 375 ms polls per SSE client. | A development server; noted only. |

## 3. Measurements

| What | Before | After | Notes |
|---|---|---|---|
| Browser: key to the channel's pushed page, median | 6.3 ms | 0.28 ms | Release, five runs each; the fetcher slept 5 ms between socket checks (a3c6775). |
| Browser in the Windows 11 VM, same test | — | 1.16 ms (worst 1.43) | Release. |
| `neottx`: key to pushed page, median | 17 to 21 ms | 0.2 to 0.5 ms | Debug build; 0.33 ms on Linux inside the sandbox (017a38c). |
| Browser fetcher idle for 30 s, connected to the reference channel | 0.11 s of processor time, 5,077 involuntary context switches | 0.01 s, 63 | `/usr/bin/time -l`. |
| `neottx fetch` idle for 30 s, same channel | 0.08 s, 2,871 switches | 0.02 s, 109 | Same. |
| Browser: render, PNG encoding, interface decoding of a page, medians | — | 3.3, 3.7 and 0.4 ms | Release, requirement 18.5 (20 October 2026). |

Not measured in this review: the browser's decoder and core at idle with a flashing and a static page, the interface's redraw cost since 16 October, `neottx view` at idle, and anything on a microcontroller (the engine's test image is linked and sized, never run).

## 4. Bugs found

1. **`neottx keyboard` never reads the channel's socket** (*confirmed*). `crates/neoteletext-cli/src/keyboard.rs:182` calls `receive(Duration::ZERO)`, which becomes `TcpStream::set_read_timeout(Some(ZERO))`; the standard library documents a zero timeout as an error, so the call always fails and the `if let` never matches. The bridge never answers the channel's pings, never sees it close, and the channel's pushes pile up in the kernel's buffer until the server's writes stall.
2. **The live-feed fetcher loses timers** (*confirmed*). In `run_zxnet` (`crates/neoteletext-app/src/fetch.rs`) only the tick's sink records `LiveOutput::Timer`; the general sink drops it. After the handshake the feed's 5-second keepalive deadline is lost behind the 30-second handshake deadline, so the first keepalive is about 25 s late and inactivity goes unnoticed for that time. `run_web` takes the minimum of every timer and is right.
3. **A stopped live feed wakes 5 times a second for ever** (*confirmed*): `next_tick` falls back to now plus 200 ms when the feed asks for no timer. It should then wait with no deadline.

*Reported, not checked:* the viewer does not notice its pipe reader dying on a malformed frame (`live.rs`), and so would wait on a fetcher blocked on a full pipe; `neottx view` does not redraw after a terminal resize; the browser fetcher's `connect` replaces a connection without shutting the old one down, which relies on the engine's `Pump` always closing first.

## 5. Findings, by what they cost

### 5.1 Latency a person sees

1. **`neottx view` holds every page arrival for up to 40 ms** (mean 20 ms), since its loop wakes only for the terminal or the 40 ms tick. Now that the fetcher answers in 0.3 ms, this tick is nearly all of `neottx`'s typing latency; the new typing test talks to the fetcher directly and does not see it. Wake the loop on the pipe reader's frames too (a reader thread for the terminal's keys and one channel, as the fetchers now do), and sleep until the next flash, ticker or freshness deadline instead of a fixed 25 Hz.
2. **Both fetchers connect, resolve names and complete TLS on the loop's thread**, up to 10 s each, so a push reconnecting to a slow host holds keys and page fetches meanwhile. Moving the connect and handshake into the connection's own thread, reporting `Open` through the wake channel, also makes `Transport::connect` "return at once" as the engine's trait says it should.
3. *Corrected 21 October 2026: measured, this is not a risk. The longest an operation holds the lock is 0.37 ms, defining the largest sound, against a device buffer of about 10 ms; a large zeroed allocation costs little on macOS.* **The browser's audio callback takes the mixers' lock for its whole render** (*confirmed*, `interface/src/audio.rs`), and the pipe-reader thread holds the same lock while it defines a sound (allocating up to 11.5 MB) or copies samples. A long define can make the real-time callback miss its deadline: a click or a gap. Prepare sounds outside the lock and hand them over with a swap, or a single-producer queue the callback drains.

### 5.2 Processor time at idle

4. **The browser re-renders shown pages 12 times a second without need.** Render only when a shown page has flashing cells and its flash phase changes; the decoder can compute the next phase change itself and stop asking the core for ticks. Hidden decoders are ticked only for the live-sound clock; with a deadline from the audio receiver (section 6) they need none. Requirement 9.7 already asks for this.
5. **The browser's decoder renders every shown page on every message**, and on every message hashes every complete page in its store with SipHash to find arrivals (*confirmed*, `decoder/src/lib.rs`), while discarding the engine's own `PageCompleted` and `PageUpdated` events. Use the events: render only the shown pages they name.
6. **The core's load timer runs at 5 Hz for ever.** Stop it when every source is done; start it when a file channel opens.
7. **The interface redraws the whole window for small things**: the glow, the "updated" marks, the cursor blink, each a full 13 ms frame. Redraw the damaged region only, or at least keep the page images as cached layers. `surface.resize` runs on every frame.
8. **`neottx view` composes and compares the whole page 25 times a second**, and in iTerm2 mode re-rasterises, PNG-encodes and base64-encodes the page at every flash phase change, two to seven times a second, whether anything on it flashes or not. The core's per-row `ChangeTracker` (REQ-RND-019) is unused.
9. **The polls that remain**: `neottx keyboard` and the browser's keyboard at 50 ms, the browser's mixer poll at 250 ms, the audio stream playing silence. Each can wait on its socket or be signalled; pause the stream when no mixer is active.

### 5.3 Copies, encodings and system calls

10. **The frame path copies 240 KB of indices twice in the decoder** (a clone, then the payload), and again in the core; each reader copies its payload into a new `Vec` rather than taking the buffer it read. Take payloads by move and write from references.
11. **Flashing pages are PNG-encoded (3.7 ms) and decoded (0.4 ms plus a 960 KB expansion) at every phase change**, though they alternate between two images. A per-page cache of phase images, keyed by content, would end the repeats; it changes the protocol between core and interface, so the security trade-off is the owner's.
12. **Fetched bytes are copied about ten times** between the socket and the decoder in both programs. A few KB a page; worth fixing only alongside 10.
13. **Every message is flushed on its own.** A tick that produces links and a frame is three system calls; `neottx`'s fetcher writes through standard output's line buffer, which also splits binary payloads at newline bytes. Buffer, and flush once per handled event: fewer system calls, no added latency.
14. **Audio messages are re-parsed to check themselves when written**, building and discarding a second sample buffer of up to 64 KB each time.

## 6. The libraries: what to change

- **A deadline from every state machine.** Give `neoteletext-core`'s `Decoder` and `neoteletext-audio`'s `Receiver` a `next_deadline()` (the completion timeout and staleness; the live-sound stall and progressive start), as the web agent has. Then no port needs a fixed tick, on any system, and section 5.2 item 4 needs no core timer at all.
- **Smaller web storage per build.** `agent::Storage` defaults to 388 KiB (two 16 KiB heads and requests, a 256 KiB body, a 64 KiB push message, a 4 KiB form). A port can pass smaller buffers, but a set of sizes per feature, recorded beside the measured flash, is owed (implementation log, NOT DONE).
- **`Transport::send` must take a whole message**, so a port without a large TCP transmit buffer needs its own queue of up to 16 KiB per connection. Say so in `porting.md`, or let `send` take part and report how much.
- **Hot-path arithmetic for Cortex-M0**: the row change tracker multiplies 64-bit values per byte (FNV-1a), and flash timing divides 64-bit values once a frame. A 32-bit hash for the tracker on 32-bit targets would avoid the library calls; flash timing once a frame is harmless.
- **Document the largest stack frame** (REQ-GEN-016 asks for it; it is not recorded). Candidates: the 12 KiB `Descriptor` returned by value from parsing, 2 KiB URL buffers in the agent, two 1,017-sample arrays in the audio receiver's live path.

## 7. Microcontrollers

### 7.1 Which model where

| Model | Fits | How the engine maps |
|---|---|---|
| Superloop with `WFI` (lwIP raw API with `NO_SYS`, or smoltcp) | Boards whose main loop is the video, as tellyboy's are; the simplest port. | `Pump`'s documented loop: poll the connections, feed `Input::Net`, send `Output` back; sleep until the minimum of the agent's deadline, a network or key interrupt and the next video frame. tellyboy's STM32H7 port already drives lwIP from its main loop this way. |
| `embassy` (async executor, `embassy-net`) | Boards with networking and room for an executor: ESP32-S3, RP2350, STM32H7. The recommended model where the port is written in Rust. | One task per machine that `select`s on socket-readable, a key channel and `Timer::at(deadline)`, then calls `handle`. Two adapters: the sink copies the bytes it is to send into a queue written after `handle` returns (outputs are borrowed only during the call), and a reader task fills the buffer that `Transport::receive` drains without blocking. |
| ESP-IDF tasks (FreeRTOS) | ESP32 ports in C or Rust with ESP-IDF's network and TLS. | The desktop fetchers' shape: a task per socket waking the agent's task through a queue. The agent then runs in a task of its own, so a blocking connect there is acceptable. |

The rule that carries across all three: **wait on what you need**. A loop that sleeps a fixed interval and looks again is the 5 ms and 10 ms waits removed from the fetchers today; on a battery it also keeps the processor awake.

### 7.2 What does not carry

- **TLS and WebSocket security** belong to the port: a `no_std` TLS client (mbedTLS through ESP-IDF, or `embedded-tls`), about 16 KiB of record buffers each way, root certificates in flash, and a hardware random-number generator for both TLS and the WebSocket masks. Plain `ws://` works without them. The phone keyboard's cryptography stays off microcontrollers (decisions E.90 and E.93).
- **The mixer (`neoteletext-audio-mix`) is for operating systems only**: it allocates, uses 64-bit arithmetic and searches its sounds linearly for every output sample. On a microcontroller the voice sink maps to tellyboy's voices; passing IMA ADPCM blocks undecoded to such a sink is not built yet (area AUD, owed).
- **The browser's interface core is `no_std` but needs an allocator and floating point** throughout (`f64` geometry, `libm`, `format!`), and `draw-embedded` keeps each page as a 240 KB index buffer. That suits a part with a floating-point unit and external RAM (ESP32-S3 with PSRAM), not a Cortex-M0 or M3. A small-device browser would draw from the engine's `render_row` directly into the display, with flash and reveal as palette swaps (`porting.md`), not through the desktop interface.

### 7.3 What is unknown

No engine code has run on a device; there is no timing from a microcontroller, no stack measurement, no flash figure for audio or input, and the Cortex-M0 sizes predate the font slots (`TECH-DEBT.md`). These are the first things to measure before choosing a target.

## 8. Hundreds of tabs and thousands of pages

The owner asked what happens at scale. Measured on 21 October 2026, release builds:

| What | Measured | At 200 tabs | At 1,000 tabs |
|---|---|---|---|
| A decoder process at rest | 16 MB physical, 10.5 MB of it the page store of 4,096 slots allocated up front | 3.2 GB | 16 GB |
| A fetcher process at rest | 3.6 MB peak resident, 1.5 MB footprint | about 0.3 to 0.7 GB | about 1.5 to 3.6 GB |
| An idle mixer (a tab that has played a sound) in the audio callback | 2.0 ms of processor time per second of audio | 41 % of a core, on the real-time thread | over a whole core: every tab's sound breaks up |
| The same, skipping mixers that are not `active()` | 0.28 ms per second for 500 mixers | none to speak of | none to speak of |
| The decoder's scan of its store on every message (section 5.2 item 5) | 0.37 ms at 1,000 complete pages, 1.5 ms at 4,096 | 1.5 cores if each tab takes five messages a second with a full store | — |
| Processes the system allows one user (`kern.maxprocperuid`) | 2,666, of which 329 were in use | — | two per web tab: the limit is reached near 1,100 tabs |
| Threads in one process (`kern.num_taskthreads`) | 4,096 | the core has two reader threads per tab | the core's limit is near 2,000 tabs |

Not measured: the flash ticks (12 a second to every decoder, so 2,400 pipe writes and process wakeups a second at 200 tabs), the interface's tab strip and wall with hundreds of tabs, and a store filling past 4,096 pages and sub-pages.

What follows:
- **The limit at scale is processes and memory per tab, not threads.** An async runtime would change none of it: decoders and fetchers are separate processes for security (the browser's decision 4), and the core's threads are cheap until about 2,000 tabs.
- **Skip silent mixers** in the audio callback: one line, measured above.
- *Corrected 21 October 2026, on the owner's word that teletext is mostly pushed, and against decision 22 ("Fetching never depends on viewing"): a tab whose channel holds a push connection is live and never sleeps, and no fetcher is closed or paused for being behind; only a tab with nothing live has its decoder closed. The two items below that close fetchers and fetch only what is shown were wrong, and were not built.*
- **Put background tabs to sleep**, as other browsers discard tabs: a tab not shown for a while has its decoder stopped and its channel's bytes kept, and its fetcher closed unless it holds a push connection the owner wants kept; showing the tab starts them again. Processes then grow with the tabs in use, not the tabs open.
- **Size the decoder's store by need** rather than 4,096 slots up front, or from the channel's contents file.
- **Use the engine's page events** instead of scanning the store, and stop ticking hidden decoders (sections 5.2 and 6).
- **Fetch politely across tabs, not per tab.** The 200 ms spacing is per fetcher, so 200 tabs of one host ask it 1,000 times a second, and every tab fetches its whole channel when opened: 1,000 pages take 200 s per tab. Background tabs should fetch only what is shown, and fetchers of one host should share its rate.

## 9. Recommended work, in order

Each item is a change of its own, with the measurement that shows it worked.

| # | Change | Repository | Shows it worked |
|---|---|---|---|
| 0 | Skip mixers that are not `active()` in the browser's audio callback. | Browser | The idle-mixer timing of section 8, in a test. |
| 1 | Fix `neottx keyboard`'s channel read (bug 1) with a reader thread per socket and one channel. | Engine | A test where the channel pings and closes; idle wakeups of the bridge. |
| 2 | Keep every live-feed timer, and wait without a deadline once stopped (bugs 2, 3). | Engine | A test of the keepalive's time after the handshake; idle switches of a stopped feed. |
| 3 | `neottx view` wakes on frames and on its next deadline, not a 40 ms tick. | Engine | The typing test extended through the viewer; idle switches with a static page. |
| 4 | Audio callback without the lock held across allocation (5.1 item 3). | Browser | A test defining a large sound while playing, counting late callbacks. |
| 5 | `next_deadline()` for the core decoder and the audio receiver. | Engine | Unit tests of each deadline; then 6. |
| 6 | Decoder renders on engine events and on its own flash deadline; the core's flash and load timers go. | Browser | Processor time of a decoder over a minute, static page and flashing page, before and after (recorded: about 7 s a minute). |
| 7 | Connect and handshake in the connection's thread, in both fetchers. | Both | A test with a slow-accepting server: keys still reach the push connection. |
| 8 | Flush once per handled event; take payloads by move; drop the self-check's re-parse. | Both | System calls per page (`dtruss` or `strace -c`) and the latency test's pipeline numbers. |
| 9 | Redraw damaged regions in the interface; pause the audio stream when silent. | Browser | Interface processor time with a channel that updates every 1.5 s. |
| 10 | Microcontroller groundwork: smaller web storage per feature, stack measurement, the 32-bit row hash, and running the test image on a board. | Engine | Recorded sizes, stack depth and a first timing on hardware. |
