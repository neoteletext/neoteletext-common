# The script API `nt`, version 1: specification and build plan

22 November 2026. The design document for the build the owner started that day ("THE DESIGN IS AGREED TO AND ADOPTED", rdm DEC-7262). It is the precise form of what these decisions adopted, written for the code sessions that build it: DEC-7246 (request/response; pages are loaded files; QuickJS compiled to WebAssembly), DEC-7247 (each renderer's programming model and the shared core), DEC-7245 (teletext's sixel bitmap), DEC-7266 (scripts in a separate confined process; no zygote), DEC-7264 (isolation by channel identity), DEC-7250 (standard cookies), DEC-7252 (exactly the web's fetch), DEC-7253 (no libcurl), DEC-7254 (the channel file names scripts), DEC-7255 (a page file names its script), DEC-7260 version 2 with DEC-7256 and DEC-7261 (how the web APIs and web client are built), DEC-7191 and DEC-7205 (one API per renderer on one model; one component vocabulary implemented per renderer) and DEC-7208 item 3 (integer versions).

DEVELOPMENT.md section 1 item 6 allows a design document while a design is shaped; this one is carried into rdm as requirements and documentation items at integration and then deleted. Until then, where this document and a decision disagree, the decision holds and this document is corrected. Choices this document makes that no decision made are listed in section 17 and recorded in rdm as one decision that waits for the owner's confirmation.

**Sources and their short names**

| Short | Source |
|---|---|
| RPT | The report "How each of the three renderers is made programmable", `/data/neoteletext-tmp/renderer-models/renderer-programming-models.md` |
| SPIKE | The browser's branch `spike-qjs`, worktree `~/devel/neoteletext-browser-worktrees/spike-qjs`, crate `native/script` |
| R2 | `neoteletext-renderer-regis/docs/regis-v2.md`; RL its `crates/regis/src/limits.rs`; RREF its `docs/reference.html` |
| NREF | `neoteletext-renderer-naplps/docs/reference.html`; NL its `crates/naplps/src/limits.rs`; RAS `neoteletext-common/docs/naplps-raster.md` |
| AN | `neoteletext-common/docs/animation.md` (requirements ANIM-n) |
| PR | `neoteletext-common/docs/page-rules.md` (requirements RULE-n) |
| TC | `neoteletext-renderer-teletext/crates/neoteletext-core/src/` |
| EN | ETSI EN 300 706, by clause and table |
| FETCH, HTML, URL, STREAMS, DOM, WS, ENC, FILEAPI, XHR | The WHATWG standards Fetch, HTML, URL, Streams, DOM, WebSockets, Encoding; the W3C File API; WHATWG XMLHttpRequest (for FormData) |
| COOKIES | RFC 6265 as revised by the IETF draft draft-ietf-httpbis-rfc6265bis ("6265bis") |

**Conventions.** "MUST", "MUST NOT", "SHOULD" and "MAY" are DEVELOPMENT.md section 4's modal verbs. An *int* is a whole number in the signed 32-bit range. Every bound has a name in `SMALL_CAPITALS`; section 10.6 gives each its value and source, and a bound that is a renderer's or the engine's constant is used by that name, never restated as a literal. A call that would pass a bound throws a `RangeError` whose message begins with the bound's name, and changes nothing. A call with a wrong type or a stale handle throws a `TypeError` and changes nothing. TypeScript-like notation describes signatures; it is notation, and the API is JavaScript.

---

## 1. Principles

1. **Security first** (DEVELOPMENT.md section 1 item 5). A script is exactly as untrusted as the channel that served it. Five boundaries stand around it, from the inside out: the flat host call (section 10); the WebAssembly container (wasmi, DEC-7256); the script-host process's confinement (DEC-7266); the typed, bounded messages to the decoder and the fetcher (section 11); and the trusted core's gate on what input a page is given and what leaves.
2. **Each renderer has its own API.** `nt.teletext`, `nt.regis` and `nt.naplps` each expose what is unique to that renderer in that renderer's own terms: teletext's cells, serial attributes, mosaics, enhancement overlay, sprites and sixel bitmap; ReGIS's numbered drawings, writing modes, shading, macrographs, looks, frame lists, paint rates and painted report; NAPLPS's backdrop, textures, DRCS, relative drawing, WAIT, BLINK and cast. No layer equalises them. A name is shared between two renderers only where the verb is truly identical (section 3.9 lists them). What is common lives above the renderers: the event loop, time, events, sound, the budget, the web APIs and the component vocabulary `nt.ui`.
3. **As standard as it can be; every departure explained** (DEC-7250, DEC-7252). Where a web standard covers a thing, the script sees that standard's API: `fetch`, `EventSource`, `WebSocket`, `URL`, `EventTarget` and `Event`, `AbortController`, `setTimeout`, `TextEncoder`, `crypto.getRandomValues`, streams. Each difference is a numbered departure with its reason (section 9.4). A thing no web standard covers (a teletext row, a ReGIS drawing) is NeoTeletext's own and is specified here.
4. **Scripts do not write format bytes** (DEC-7247 item 6). A script calls typed painters; the host's encoders write the teletext, ReGIS and NAPLPS bytes. Version 1 has no raw-bytes escape: RPT section 10.2 finding 6 shows it needs a framing check neither renderer offers as a call, and nothing in the first set of pages needs it.
5. **Fail open** (the owner's event model of 22 November 2026). An event has a default action that happens with no script at all. A script's handler may let it through, cancel it or replace it. A script that throws, is stopped, or is absent leaves every default in force, so a page degrades to the plain page and the viewer can always leave.
6. **One library, two programs.** The script host is one Rust library, `neoteletext-script`. The browser's script-host program and the standalone runner (section 16) both link it and nothing else implements the API, so behaviour cannot differ between them.

---

## 2. The isolation policy (one named place)

The owner accepted DEC-7264 on 22 November 2026: **the unit of isolation for scripts is the channel identity**, not the web origin, because NeoTeletext isolates channels (the browser's REQ-712, neoteletext-common's REQ-1883, the engine's REQ-515) and many channels share one origin (`https://app.neottx.com/home/` and `/demosite/`; every channel of one GitHub Pages user).

The whole policy is implemented in one Rust type, `ChannelPolicy`, in one module of the fetcher's library, constructed only from values the trusted core gives (the channel identity as REQ-2874 compares it, the window's jar, and whether the page came from disk) and never from anything a script sends. No other code decides any of the following; each calls `ChannelPolicy`.

| # | Rule | Method of `ChannelPolicy` |
|---|---|---|
| P1 | A request's *relation* to the requesting channel is one of `InChannel`, `SameOriginOutside` (same origin, not in the channel) or `CrossOrigin`. `InChannel` is decided by the engine's one rule for "inside a channel", `neoteletext_web::channel::is_inside` (the engine's REQ-3518), on the address as the `url` crate parsed it: same scheme, host and port, and a path under the channel's folder; an address whose path holds an encoded slash or backslash (`%2F`, `%5C`), an encoded dot segment (`%2E`), a `;` path parameter, or a `.` or `..` segment is never `InChannel`. No other code tests "same channel": the fetcher, the script host's address resolution (operation 40) and script loading all call this. | `relation(url) -> Relation` |
| P2 | `InChannel` is "same origin" for FETCH. `SameOriginOutside` and `CrossOrigin` are both "cross-origin" for FETCH: CORS mode, preflight, the answer readable only as `Access-Control-Allow-Origin` allows, credentials only under `credentials: "include"` with `Access-Control-Allow-Credentials: true`. The same holds for `EventSource` and `WebSocket`. | `is_same_origin(url) -> bool` |
| P3 | One cookie jar for each pair (window jar, channel identity), where a window jar is the ordinary windows together or one private window. Every request a channel's context causes reads and writes only that jar, whatever address it goes to. Inside a jar COOKIES applies unchanged. | `jar() -> JarKey` |
| P4 | The HTTP cache, the script and bytecode cache, and any state kept for an event stream or a later storage API are keyed by the same `JarKey` first. | `partition() -> JarKey` |
| P5 | A script named by a channel file or a page file is loaded only when its address is `InChannel`. | `may_load_script(url) -> bool` |
| P6 | A page opened from disk has an opaque origin, no jar and no network (section 12.7, pending the owner). | `network_allowed() -> bool` |
| P8 | A channel served over plain `http:` is not a secure context: its scripts' requests, event streams and sockets reach only addresses that are `InChannel` (the web's secure-context idea, DEC-7282 item 3, proposed by the security review; pending the owner, section 18 question 7). | `network_reach() -> Reach` |
| P7 | A request to a loopback, link-local or private address from a channel that is not itself on such an address is refused, on every resolved address and every redirect (DEC-7260 item 6). | `may_connect(resolved_address) -> bool` |

**One process for each partition** (DEC-7268, the security review's finding, pending the owner's ruling and specified here as the safe form; it is the browser's existing REQ-678). A *partition* is a `JarKey`: one window jar and one channel identity. The web client that serves a partition's requests is a confined process that holds only that partition's cookie jar, connections, HTTP cache and preflight cache; it may be the channel's existing fetcher process, which already has exactly one channel identity and one jar. No process ever holds two partitions' cookies or connections. The process is told its partition once, at its start, by the trusted core; a message that names any other partition ends the process (section 11.3). At most `MAX_WEB_CLIENTS` such processes live browser-wide; when one more is needed the least recently used one whose tabs are all asleep is ended, its jar saved first, and if none can be ended the new partition's scripts get no network and the developer log says why. Cookies kept between runs are held by the trusted core, sealed and written for each partition, handed to the process at its start and taken back as they change (at most `MAX_JAR_BYTES`).

P2, P3, P4 and P5 are departures from the standards; section 9.4 lists them (D1 to D4) with REQ-712 as their reason. `ChannelPolicy::relation` has a fuzz target of its own asserting that no address outside the folder is ever judged `InChannel` (TODO-7265's check).

### 2.1 The security review's rules for the open points (DEC-7282, pending the owner)

The independent review proposed a rule for each point DEC-7262 left open. Each is specified here as proposed, pending the owner's ruling on DEC-7282; where this document had drafted something else, the difference is stated.

| DEC-7282 item | The rule as proposed | In this document |
|---|---|---|
| 1. Files not from their channel | A file opened from disk runs no script by default; the strip says it has a script and offers to run it once; run so, it has an opaque origin, no network, no cookies, no stored state, and may load only a script carried inside the file itself | **Differs.** Section 12.7 drafted: the script it names is read from the same folder and runs at once, with no network. Both are put to the owner (section 18 question 1); `ChannelPolicy` P6 holds the choice in one place |
| 2. References stay inside the channel | A script reference must lie inside the channel's folder by REQ-3518's rule | The same and stricter: a script name is a file name in the folder (12.2, P5) |
| 3. Plain HTTP | On an `http:` channel scripts may request only inside their own channel | Adopted as P8 and departure D27, pending the ruling |
| 4. Keys declared, never computed | Declared before any code runs, "in its channel file or page file"; no "any key"; never-claimable keys never reach the script process; Escape only with the hold notice; no default send-everything table | The same rule, **in a different place:** the manifest at the head of the script file (3.1), read before any code runs, because a script named by a page file has no channel file entry to hold it |
| 5. Input that can leave is shown | While a script page holds any key or the pointer the strip shows "Keys go to host"; a text claim shows a typing indication; REQ-6523's report gate cannot hold for script pages and is revised | Adopted. **Differs** from the first draft of 4.6, which showed a lesser indication for a script without the network; 4.6 now follows this rule, and the wording stays the owner's |
| 6. The viewer sees and controls a script | The strip shows that a page's script is running and when it was stopped; a never-claimable browser key stops a page's script, after which the last frame stays and no callback runs | Adopted (3.1, work package F5) |
| 7. Sound needs the viewer | No sound and no synthesizer until the viewer has pressed a key or the pointer in that tab | Adopted: until then `nt.sound` and `nt.synth` calls do nothing and are logged once; `nt.sound.allowed` says which, and an `allowed` event on `nt.sound` tells the script |
| 8. Budgets across tabs | Browser-wide maximums of script processes, their total memory, and requests and connections a second; a hidden tab's ticks slowed and its sound stopped; a page over a browser-wide budget stopped, oldest first | Adopted as `MAX_SCRIPT_HOSTS`, `MAX_SCRIPT_MEMORY_BYTES` and the web client's rates. **Stricter** on hidden tabs: this document pauses a hidden tab's scripts entirely (3.1) |
| 9. One realm only for one channel's scripts | The channel's and its pages' scripts may share one context because all come from the channel's folder | **Stricter:** two realms in one runtime (3.1), sharing only `nt.shared` |
| 10. No scripts on push | A page delivered by a live push connection runs no script | Adopted: a channel whose `channel.ttx` has `push` runs no script, and its `scripts` member is ignored and logged (12.1) |
| 11. Time stays coarse | Ticks are the only clock; no threads, no shared memory, no `Atomics` | The same (D12 to D14); `SharedArrayBuffer` and `Atomics` are removed from the global object by the prelude and absent from the build |

---

## 3. The shared core

### 3.1 Scripts, contexts and the container

- **A script** is one UTF-8 text file of JavaScript, served as `text/javascript`, at most `MAX_SCRIPT_BYTES`. It is a classic script, not a module: version 1 has no `import`, static or dynamic (a module graph is a second loader; a channel bundles what it needs into one file). It is evaluated in strict mode.
- **The manifest** is a declaration that is read, never run (RPT section 9.2 item 14). It is the first thing in the file: a block comment that opens with exactly `/*! nt` and holds one JSON object, at most `MAX_MANIFEST_BYTES` from the file's start to the closing `*/`. The decoder reads it with a strict, bounded JSON reader before any code runs; an unknown member, a duplicate member, a wrong type or a value out of range refuses the script whole. A file with no manifest is refused. Its members:

| Member | Type and bound | Meaning | Default |
|---|---|---|---|
| `api` | int, 1 to the host's highest | The API version the script was written for (DEC-7208 item 3). Required. | none |
| `renderer` | `"teletext"`, `"regis"` or `"naplps"` | For a JavaScript page, the renderer it draws on. For a script attached to a page file it MUST equal the page file's renderer or be absent. A channel-level script omits it. | the page's |
| `keys` | array of at most `MAX_KEY_ASKS` key names, each at most `MAX_KEY_NAME_BYTES` | The keys the script claims (section 4.6). No "any key" entry exists. | `[]` |
| `text` | boolean | Claims committed text (typing, paste, input methods). | `false` |
| `pointer` | `"none"`, `"press"` or `"move"` | `"press"`: press, release, enter, leave and cancel events. `"move"`: also move events. | `"none"` |
| `wheel` | boolean | Wheel events over things that declare `wheel` (section 4.3). | `false` |
| `tick` | int 0 to `MAX_TICK_DIVISOR` | 0: no tick events. n: one tick event every n ticks. | 0 |
| `language` | a language tag at most 16 bytes, from the engine's list (section 5.6) | The language text is encoded for. | the page's |
| `network` | boolean | The script uses `fetch`, `EventSource` or `WebSocket`. When false these fail at once and no fetcher link is given. | `false` |

- **A context** is one JavaScript realm (a QuickJS context) with its own global object, its own `nt`, its own prelude and its own handlers and timers. There are two levels (DEC-7254):
  - the **channel context** runs the channel-level script. It starts when a tab opens the channel and ends when the tab leaves the channel or closes;
  - the **page context** runs the script of the page or sub-page shown. It starts when that page opens and ends when it is left. A sub-page is exactly a page (DEC-6599): changing sub-page ends one page context and starts another, with nothing carried across.
- **A container** is one WebAssembly instance holding one QuickJS runtime with at most those two contexts, in one script-host process. There is one container for each (tab, channel), started with the first script that needs it. Two contexts in one runtime share nothing a script can reach: no object of one realm is ever given to the other. They share state only through `nt.shared` (section 3.6).
- **Lifetimes.**

| Moment | Channel context | Page context |
|---|---|---|
| The tab opens the channel (its first page) | Created; top level runs under `START_TIME_LIMIT` | Created after the channel context's top level returns, if the page has a script |
| The page or sub-page changes inside the channel | Lives on; receives `pagehide` then `pageshow` | Receives `close`; one handling; then every handle, listener, timer, request and socket of it is dropped and the realm freed. The new page's context is created |
| The tab leaves the channel or closes | Receives `close`; one handling; the container and process end | as above |
| The tab is hidden | Both paused: no tick, no timer; held notes released; `visibilitychange` delivered before the pause and after the resume | same |
| A handler throws | The error is logged (section 3.8). Changes made before the throw stand, as on the web. `MAX_CONSECUTIVE_FAILURES` failures in a row stop that context | same |
| A time, memory or stack limit is passed, or the container traps | The whole container is stopped for good and its process ended; it is never entered again and is not restarted until the viewer reloads | same |
| A context is stopped | Every default action stays in force (principle 5). The last committed picture stays. The trusted strip shows that the page's program stopped, with reload (the indication is the trusted core's, REQ to be written) | same |

- **What a page with no script of its own gets.** The channel context still runs and still receives the page's events (section 4.5).
- **What the channel context may draw.** Renderer state belongs to the page. The channel context is given the renderer API of the page shown (`nt.page.renderer` names it) restricted to the overlay layer: teletext sprites in layer 3; ReGIS drawings in layer 3; NAPLPS actors and regions in layer 3 and the symbols they use. A call outside that throws a `TypeError`. Everything it drew is dropped with the page; it redraws on `pageshow`. It holds a reserved share of each table (`CHANNEL_SHARE_*`, section 10.6) so that neither level can starve the other.

### 3.2 The event loop and the clock

- **One thread, run to completion.** The host enters a context for one callback at a time; a callback is never re-entered or interleaved. After each callback the host runs that context's microtasks (promise jobs) to exhaustion, inside the same time limit.
- **A step** is the unit of work and of messages: the decoder sends one STEP for a presentation tick or for input that arrived between ticks, and the host runs, in order: (1) the input events of the step, each to the page context then the channel context (section 4.5); (2) network events that arrived (response heads, body chunks, socket messages), at most `MAX_NETWORK_EVENTS_PER_STEP`; (3) timers that are due, in order of due tick then of creation; (4) the `tick` event if this step is a tick the manifest asked for.
- **The atomic frame.** Everything the callbacks of one step changed leaves as one BATCH and appears together: teletext between FRAME begin and end records (AN ANIM-2), ReGIS as one `D(C)` commit, NAPLPS as one append with its object record and animation operations. There is no draw callback.
- **The clock** is the presentation clock of 60 ticks a second (AN ANIM-1). A context's tick 0 is its first step. A script that falls behind is not sent the ticks it missed; the `tick` event says how many were missed. While paused the tick count does not advance, so a script never sees a jump.
- **Time is a real budget, in wall-clock time, and host time is the script's time.** The security review overran the spike's limits three ways (TODO-7267): a 50 ms limit ran 3.03 s under a loop of 40 MiB `copyWithin` calls, because the clock was read only when a fuel slice ran out and bulk memory operations cost almost no fuel; time inside host calls was not charged; and 31 timers of 19 ms each ran 590 ms every tick without the page ever being stopped. The rules that replace them:
  1. **Three limits.** `START_TIME_LIMIT` for a context's top level. `CALLBACK_TIME_LIMIT` for one callback with its microtasks. `STEP_TIME_BUDGET` for *everything* a step runs in both contexts: every callback, every microtask and every host call. All are measured on the monotonic wall clock from entry to exit, so time spent inside a host call is charged like any other.
  2. **The step budget is hard for starting work.** When a step has used `STEP_TIME_BUDGET`, no further callback of that step starts: remaining timers stay due and remaining events stay queued for the next step (lost releases are delivered first and never deferred). A `tick` event that cannot start is counted in the next one's `missed`.
  3. **A budget over a second.** A container that uses more than `SECOND_TIME_BUDGET` of script time in any `TICKS_PER_SECOND` consecutive ticks is stopped for good, as for any passed limit. This is what stops a page whose every callback is just under its limit.
  4. **Passing `CALLBACK_TIME_LIMIT` or `START_TIME_LIMIT` stops the container for good.**
  5. **The clock check cannot be starved.** Two mechanisms, both required. (a) Inside the container: the fuel slice is at most `FUEL_SLICE`, and the module is built so that no single instruction does unbounded work: it holds no WebAssembly bulk-memory instruction (`memory.copy` and `memory.fill` become loops that are charged for each iteration). Compiling QuickJS and the shim with `-mno-bulk-memory` is not enough: wasi-sdk's prebuilt C library is built with bulk memory, so its `memcpy` and `memset` still hold those instructions; the build therefore rebuilds the C library without them or supplies its own `memcpy`, `memmove` and `memset`, and the reproducible build scans the final module's code section and refuses one that contains either instruction. As a fallback that stays in place, wasmi is configured to charge fuel for each byte a bulk operation copies. (b) Outside it: a watchdog thread in the script-host process, which holds no lock the interpreter can hold, ends the process when a callback or the top level passes its limit by more than `WATCHDOG_GRACE`; and the decoder ends the script through the trusted core when a STEP is not answered within `STEP_DEADLINE`. Neither depends on the interpreter returning.
  6. **Host calls check too:** the clock is read before and after every host call and at least once for every `HOST_COPY_CHECK_BYTES` a host call copies or processes.

### 3.3 `nt`: identity, time and the page

`nt` is a frozen object on the global object of each context. It is an `EventTarget` (DOM): `addEventListener(type, listener, options)`, `removeEventListener`, with the options `once` and `signal`. There is no capture phase and no `dispatchEvent` for host events (a script cannot forge one; `dispatchEvent` works for a script's own custom event types on its own targets).

| Member | Type | Meaning and bounds |
|---|---|---|
| `nt.version` | int | The host's highest API version. The script was promised the version its manifest names; every later version keeps every earlier one working (DEC-7208 item 3). |
| `nt.level` | `"channel"` or `"page"` | Which context this is. |
| `nt.now()` | int | The context's tick count. |
| `nt.hidden` | boolean | Whether the tab is hidden (true only inside `visibilitychange` handlers before a pause). |
| `nt.channel` | frozen `{ url: string, title: string }` | The channel's address (its folder, ending in `/`) and the title its channel file gives. |
| `nt.page` | `{ number: string, subpage: string or null, url: string, renderer: string, title: string }` | The page shown: its number as three hexadecimal digits (`"1A0"`), its sub-page as four digits or null, the address of its file, its renderer. `title` is writable by the page context, at most `MAX_TITLE_BYTES` of UTF-8 with no control character; it names the page to the strip and the screen reader (ReGIS: `D(T'…')`; NAPLPS: the object record's title). In the channel context `nt.page` describes the page shown now and is null before the first `pageshow`. |
| `nt.navigate(target)` | `(string) => void` | Asks the browser to go to another page: `"100"`, `"100/0002"`, or an address. It raises a `navigate` event first (section 4.2). To a page of the same channel it is allowed at any time, at most `MAX_NAVIGATIONS_PER_SECOND`. To another channel it is allowed only while a `keydown`, `pointerup` or component activation of this step is being handled (the web's user activation, HTML section 6.4), and shows the trusted core's usual indication of leaving a channel. Throws `TypeError` for an address that is not `http:` or `https:`. |
| `nt.scope(fn)` | `(fn: () => void) => Scope` | Runs `fn`; every thing, listener, timer and component created during it belongs to the scope. `scope.end()` removes them all. Scopes nest to `MAX_SCOPE_DEPTH`. |
| `nt.budget()` | `() => Budget` | Section 3.7. |
| `nt.log(...values)` | | Same as `console.log`. |

**Standard globals for time and chance** (HTML, W3C High Resolution Time, W3C Web Cryptography): `setTimeout`, `setInterval`, `clearTimeout`, `clearInterval`, `queueMicrotask`, `performance.now()`, `Date`, `Math.random`, `crypto.getRandomValues`, `crypto.randomUUID`, `console` (`log`, `info`, `warn`, `error`, `debug`), `structuredClone` (JSON-representable values and typed arrays only, departure D17), `atob`, `btoa`. At most `MAX_TIMERS` timers a context; a delay is at most `MAX_TIMER_TICKS` ticks. Departures D12 to D16 (section 9.4) cover their resolution: all time is given to one tick.

### 3.4 Keys and the pointer as state

| Member | Meaning |
|---|---|
| `nt.keys.down(name): boolean` | Whether a claimed key is held now. At most `MAX_KEYS_DOWN` keys are followed. |
| `nt.keys.pressed(name): boolean` | Whether it went down during this step. |
| `nt.pointer` | `{ x: int, y: int, buttons: int, inside: boolean, target: Thing or null }`: the pointer as of this step, in the renderer's units (section 4.4), when the manifest's `pointer` is not `"none"`; otherwise `inside` is false and the rest zero and null. |

Only claimed keys are visible; an unclaimed key is never down.

### 3.5 Sound and synthesizers

The same for every renderer (RPT section 8.5). At most `MAX_SOUND_OPERATIONS_PER_CALLBACK` operations a callback and `MAX_SOUND_OPERATIONS_PER_SECOND` a second; stops count as operations (the review's lead: sound stops are rate-limited, not only concurrent sounds). Every held note and playing sound of a context is released when it is paused or ends.

| Member | Meaning and bounds |
|---|---|
| `nt.sound.play(sound, { voice = 0, gain = 100 })` | Plays one of the channel's sounds. `sound` is the handle, 1 to `MAX_SOUND_NUMBER`, of a sound the channel announced by the engine's OBJECT and DATA records in the page's own file or in the channel's `index.t42` (how a JavaScript page with no page file brings sounds of its own is not settled: section 18); `voice` is one of the engine's four audio channels, 0 to `AUDIO_CHANNELS - 1`; `gain` 0 to 100. At most `MAX_LOCAL_SOUNDS` local sounds play at once (the engine's profile). |
| `nt.sound.stop(voice)` | Stops what the voice plays. |
| `nt.synth.start(part, family, { variant = 0, gain = 100 })` | Starts a synthesizer on `part`, one of the same four audio channels (0 to `AUDIO_CHANNELS - 1`). `family` is one of the engine's instrument families by name, each the engine's codec of that number (`neoteletext-audio/src/codec.rs`): `"sid"` (12, 3 voices), `"dx7"` (13, 16 notes), `"juno"` (14, 6 voices), `"synthd"` (15, one voice), `"synth53"` (16, 5 voices), `"synth8"` (17, 8 voices), `"synth80"` (18, 8 voices). A family the engine gains later is a new API version. |
| `nt.synth.note(part, note, { velocity = 100, ticks = 15 })` | A note 0 to 127 held for `ticks` (1 to `MAX_NOTE_TICKS`), released by the receiver on the clock. |
| `nt.synth.noteOn(part, note, velocity)`, `noteOff(part, note)`, `control(part, controller, value)`, `program(part, number)`, `bend(part, value)` | MIDI channel messages 0x90, 0x80, 0xB0, 0xC0, 0xE0, values in MIDI's ranges. |
| `nt.synth.stop(part)` | All notes off and the instrument released. |
| events on `nt.sound` | `cue` (`{ voice, cue }`, a cue point in a playing sound) and `ended` (`{ voice }`), when the decoder reports them. |

### 3.6 State shared by the two levels

`nt.shared` is a small store the host keeps for the container, reachable from both contexts. It lives as long as the channel context, is never written to disk and is never sent anywhere.

| Member | Meaning and bounds |
|---|---|
| `nt.shared.get(key)` | The value, or `undefined`. Each call returns a fresh copy. |
| `nt.shared.set(key, value)` | `key`: a string of at most `MAX_SHARED_KEY_BYTES`. `value`: anything `JSON.stringify` accepts, at most `MAX_SHARED_VALUE_BYTES` as JSON. At most `MAX_SHARED_KEYS` keys and `MAX_SHARED_BYTES` in all. |
| `nt.shared.delete(key)`, `nt.shared.keys()` | |
| event `sharedchange` on `nt` | `{ key }`, delivered to the *other* context in the same step, after the current callback. |

Values cross as JSON text through the host, so no object is shared between realms. Durable state is the server's: a script keeps it with `fetch` and the channel's cookies.

### 3.7 The budget report

`nt.budget()` returns a plain object, built fresh each call. Every entry is `{ used: int, limit: int }` and its name is the bound's name in lower camel case.

| Group | Entries |
|---|---|
| Always | `scriptBytes`, `heapBytes`, `timers`, `listeners`, `requests`, `sockets`, `soundOperations`, `callbackPercent` (the share of `CALLBACK_TIME_LIMIT` the last callback used, a whole percentage so that it is no fine clock), `callbackPercentMax`, `stepPercentMax`, `secondPercent`, `batchBytes`, `hostBytes`, `failures` |
| Teletext | `triplets`, `sprites`, `spriteFrames`, `colours`, `bitmapCellsLossy` (cells of the last `present` that lost a colour) |
| ReGIS | `drawings`, `contentBytes`, `stagedBytes`, `animated`, `cycling`, `watched`, `macrographBytes`, `colours`, `rebuildWork` (from the host's `Validator`) |
| NAPLPS | `symbols`, `symbolBytes`, `drcs`, `textures`, `actors`, `blinks`, `appendedBytesThisSecond`, `waitTicks`, `colours` |
| Components | `components`, `uiNodes` |

A count or size limit throws at the call. A time or work budget of a renderer never throws: painting is late and a `fault` event (section 4.2) says so.

### 3.8 Errors and the log

- `RangeError`: a bound was passed; the message begins with the bound's name. `TypeError`: a wrong type, a stale or foreign handle, a call the context's level may not make, a network failure (FETCH). `DOMException` with the standard's names where a web standard says so (`AbortError`, `TimeoutError`, `SyntaxError`, `InvalidStateError`, `DataCloneError`, `QuotaExceededError`).
- An uncaught exception and an unhandled promise rejection are logged with their stack and count as one failure of the context.
- The log holds at most `MAX_LOG_LINES` lines of `MAX_LOG_CHARS` between two steps; more are counted and dropped. The browser shows it in its developer view for the channel; the runner prints it.

### 3.9 What the three renderer APIs share

Only these, because only these mean the same thing on each:

| Shared | Meaning |
|---|---|
| `colours.define(name, colour)`, `colours.set(entry, colour)` | A palette of named entries the host allocates; changing an entry recolours everything drawn in it. The entries available and the colour forms differ by renderer. |
| Things are `EventTarget`s with `label`, `detectable`, `remove()`, `bounds()` and `overlaps(other)` | A sprite, a drawing, an actor or region. `bounds()` gives `{ x, y, width, height }` in the renderer's units or null when hidden; `overlaps` tests two rectangles. No pixel is ever read back. |
| `frame`, `cycle(first, last, period, { once })`, `stopCycle()` | Receiver-run frame cycling by the `ANIMATE` operations `frame` (17), `cycle` (18) and `stop_cycle` (19) (AN ANIM-6, ANIM-14): frames 0 to 15, period 1 to 3,600 ticks, at most `MAX_CYCLING_OBJECTS` cycling. |
| Layers 0 to 3 | Background, scene, sprites, overlay (AN ANIM-12), where the renderer has them. |
| In a painter: `ink(colour)`, `moveTo(x, y)`, `rect(x, y, width, height)`, `polyline(points)`, `polygon(points)` | The same verbs with the same arguments, in each renderer's own units. Everything else in a painter is that renderer's own. |

A program is written for one renderer's picture model. What transfers between renderers is everything in this section 3 and sections 4, 8 and 9.

---

## 4. Events

### 4.1 The model

Every event is a DOM `Event` (or a subclass named below) delivered to an `EventTarget`. It has `type`, `target`, `cancelable`, `defaultPrevented`, `preventDefault()`, `stopPropagation()` and `stopImmediatePropagation()`, as DOM defines them.

**Each event has a default action**, the thing that happens when no script exists. A handler:
- **lets it through** by doing nothing: the default happens after every handler has run;
- **cancels** it with `event.preventDefault()`: the default does not happen;
- **replaces** it by cancelling and doing something else in the same handler.

The verdict travels in the step's BATCH, so the default is taken, or not, only after the script has answered. If the context is stopped, absent, or passes its time limit in that handler, the default happens. An event whose `cancelable` is false cannot be stopped by any script: that is every event whose default is the viewer leaving, and every event caused by the browser's own controls.

### 4.2 The events

| Type (class) | Target | Fields | Default action | Cancelable |
|---|---|---|---|---|
| `keydown` (`KeyboardEvent`) | `nt` (the focused component first, section 8) | `key` (the W3C UI Events key value), `repeat`, `shiftKey`, `ctrlKey`, `altKey`, `metaKey` | What the browser does with that key on a page that does not claim it: a digit enters a page number; a Fastext colour follows its link; Index, Reveal, Hold and Mix do their function; any other key nothing | yes |
| `keyup` (`KeyboardEvent`) | `nt` | as `keydown`, and `lost: boolean` (the release was not seen: the page lost the keyboard, was paused or is closing) | none | no |
| `text` (`NtTextEvent`) | `nt` (the focused component first) | `data: string`, at most `MAX_TEXT_EVENT_BYTES` | none | no |
| `pointerdown`, `pointerup` (`PointerEvent`) | The thing hit, then outwards (4.4), then `nt` | `pointerId`, `pointerType` (`"mouse"`, `"touch"`, `"pen"`), `isPrimary`, `button`, `buttons`, `x`, `y`, `localX`, `localY`, `things` (every thing under the pointer, at most `MAX_POINTER_OBJECTS`, topmost first), and for teletext `row`, `column` | On a link or a control of the page file: follow or activate it, on `pointerup`. Otherwise none | yes |
| `pointerenter`, `pointerleave` | The thing | as above | The receiver's hover look, which is not an event's default and cannot be cancelled | no |
| `pointermove` | The thing, then outwards, then `nt` | as above; coalesced to the latest for one target | none | no |
| `pointercancel` | The thing that took the press | `pointerId` | none | no |
| `wheel` (`WheelEvent`) | The thing, then outwards | `deltaX`, `deltaY` in lines, summed over the step | Outside a thing created with `wheel: true` the wheel is the viewer's and no event is sent (REQ-6632). Inside one: none | no |
| `focus`, `blur` | `nt` | | none | no |
| `visibilitychange` | `nt` | `nt.hidden` | none | no |
| `tick` (`NtTickEvent`) | `nt` | `tick`, `missed` | none | no |
| `navigate` (`NtNavigateEvent`) | `nt`, page context then channel context | `destination: { url, number, subpage }`, `cause` (`"script"`, `"link"`, `"key"`, `"browser"`) | Go there | yes when `cause` is `"script"`, `"link"` or `"key"` (a key the page claimed); **no** when `"browser"` (the strip, Back, the browser's own page stepping, closing) |
| `pageshow`, `pagehide` | `nt` of the channel context only | `page: { number, subpage, url, renderer }` | none | no |
| `close` | `nt` | | none; one handling of at most `CLOSE_TIME_LIMIT`, in which a `fetch` with `keepalive: true` may still be started | no |
| `sharedchange` | `nt` | `key` | none | no |
| `painted` | A ReGIS drawing; `nt.naplps.backdrop` | | none | no |
| `cycleend` | A thing whose `once` cycle ended | | none | no |
| `cue`, `ended` | `nt.sound` | section 3.5 | none | no |
| `fault` | `nt` | `code` (the renderer's fault code, AN ANIM-16), `bound` (a name) | none | no |
| `error`, `unhandledrejection` | `globalThis` | as HTML defines them for workers | Log it and count a failure; cancelling stops the log line, not the count | yes |

Component events are in section 8. Network events (`message`, `open`, `error`, `close` on `EventSource` and `WebSocket`; `abort` on `AbortSignal`) are their standards'.

`KeyboardEvent` has no `code`, `location` or `keyCode` (departure D18: they describe the viewer's keyboard hardware and layout, which no page needs and which identify a viewer). `PointerEvent` has no `pressure`, `width`, `height`, tilt or twist, and no screen or client coordinates (D19: positions are given only in the page's own units).

### 4.3 Declaring interest

A thing takes part in pointer events only when it is detectable, and wheel events only when created with `wheel: true`. The manifest's `pointer`, `wheel`, `keys` and `text` are the ceiling: a listener for an event the manifest did not claim is never called, and the host logs that once.

### 4.4 Picking and propagation, per renderer

The browser finds what is under the pointer with each renderer's own picking, where it does today (the interface and the trusted core for a teletext cell and control; the trusted core from the pick record the decoder sends for ReGIS and NAPLPS), and the decoder names the thing in the event by the host's handle number. The script host never sees a pixel or a pick record.

| | Teletext | ReGIS | NAPLPS |
|---|---|---|---|
| What can be hit | A detectable sprite; a control or link of the page file; otherwise the cell | A detectable drawing | A shown, detectable actor or region |
| How | The cell under the pointer; a sprite when the cell is inside its rectangle of cells (AN ANIM-13) | `Picture::pick(x, y)` on the renderer's pick record: exact to the pixel, following what is painted so far; a pixel a source, look or frame wrote belongs to the drawing that placed it (R2 "Picking") | `objects_at(x, y)`: every such object whose rectangle holds the dot, in drawing order |
| `x`, `y` | The cell: column 0 to 39, row 0 to 24 | Pixels, 0 to 799 and 0 to 479 | Canvas dots, 0 to 479 and 0 to 459 |
| `localX`, `localY` | The cell within the sprite | The pixel relative to the drawing's origin (`Pick.x`, `Pick.y`) | The dot relative to the actor's rectangle |
| Propagation | The topmost thing with a listener, then `nt` | From the drawing hit up its parent chain (at most `MAX_DRAWING_DEPTH` steps), then `nt`: the event bubbles, and `stopPropagation()` ends it | The topmost thing with a listener, then `nt` |
| `things` | Sprites by layer, order, number, topmost first | The drawing hit and its ancestors | Every object under the dot, topmost first |

A release goes to the thing that took the press, wherever the pointer then is. Touch is delivered as pointer events with `pointerType: "touch"`; at most `MAX_POINTERS` pointers are followed at once, and a further touch is not reported.

### 4.5 Order between the two levels

An input event is dispatched in the page context first (target, outwards, then its `nt`), and then on the channel context's `nt` with the same fields and a `target` of null. `stopPropagation()` in the page context does not hide the event from the channel context; nothing a page script does can blind the channel script, and the reverse. The default action is cancelled if either context cancelled it. A page with no script is dispatched to the channel context alone.

### 4.6 Which keys a script may claim

The rule is REQ-7037 and DEC-7157's, applied to the manifest: a key is offered to a script only when its manifest names it, and the trusted core decides that before the key is sent anywhere. The union of the two contexts' manifests is told to the trusted core in the decoder's existing key-ask message when the contexts are created, and does not change while they live.

- **Never claimable, whatever a manifest says** (PR RULE-51; REQ-2944; REQ-6390): a key pressed with the browser's own modifier; every key the trusted strip, a panel, a list or a dialog holds; Back and the browser's own navigation; the browser's chords. These never reach the decoder or the script host. A manifest that names one is not refused; the name is ignored and logged.
- **Claimable only by name:** every other key, including the digits, the Fastext colours, Index, Reveal, Hold and Mix. There is no "any key" claim. A script that types claims `text`.
- **A claimed key and its default.** This is the one change to REQ-7037 for script pages: a claimed key goes to the script first and then takes its default action unless a handler cancelled it (section 4.2). A game cancels; a page that only wants to watch the digits lets them through. A key no manifest names behaves exactly as today.
- **Escape.** While a script claims Escape, the full-screen notice says "hold Escape to leave" (REQ-7037 item 7); holding it is the browser's and is never delivered.
- **The badge.** While a script's page holds any key or the pointer, the trusted strip shows the "Keys go to host" indication (DEC-7157 item 9; DEC-7282 item 5), because what a script hears it can send; a text claim shows a typing indication as well. The strip also shows that a page's script is running, and a key of the browser's own that no page can claim stops it (DEC-7282 item 6). The wording is the owner's (section 18, question 5).

### 4.7 Queue bounds

The rule table's bounds, by the same names (`neoteletext-rules`): at most `MAX_QUEUED_EVENTS` waiting and `MAX_EVENTS_PER_TICK` handled in a step. Waiting pointer moves for one target become the latest; wheel amounts are summed; waiting key repeats are dropped. A press, a release, an enter, a leave, a key down and a key up are never merged or reordered. On overflow the oldest moves go first; if a key or button event must be lost, the script is given lost releases for everything down. Lost releases are never held back by a budget.

---

## 5. The teletext API, `nt.teletext`

Teletext is programmed as what it retains (DEC-7247 item 2): a Level 1 page plane with serial attributes, an enhancement overlay, numbered sprites, controls, the Colour Map, and beside them the double-buffered sixel bitmap (DEC-7245). Units are cells: column 0 to 39, row 1 to 23. Rows 0 and 24 are the receiver's and are never offered (RPT section 10.2 finding 7). Teletext DRCS stays banned (REQ-2196); the shapes are the character sets and the 64 sixel mosaics.

`nt.teletext.level` is the receiver's presentation level as an int: 10, 15, 25 or 35. The overlay, sprites, controls' looks and defined colours are drawn at 25 and above (AN ANIM-8); at 10 and 15 those calls succeed and show nothing, as an enhanced page degrades on any Level 1 receiver.

### 5.1 The page plane, `nt.teletext.page`

| Call | Meaning, bounds and errors |
|---|---|
| `put(row, column, text, style?) => int` | Writes `text` so that its first character is at (`row`, `column`). The spacing attributes `style` needs are placed in the cells immediately before the text, as a Level 1 page is authored (EN clause 12.2, Table 26); set-after and set-at attributes are placed by the engine's own rules (TC `level1/row.rs`). A cell needed for an attribute MUST be free (hold 0x20); otherwise `RangeError TELETEXT_ATTRIBUTE_CELL` names the row and column and nothing is written. Returns the number of cells written, attributes included. `text` is at most `MAX_TEXT_CHARS` and is encoded by the engine's encoder (5.6). |
| `style` | `{ ink?: Colour8, paper?: Colour8, height?: 1 or 2, flash?: boolean, conceal?: boolean, box?: boolean, mosaic?: false, "contiguous" or "separated", hold?: boolean }`. `Colour8` is 0 to 7 or one of `"black"`, `"red"`, `"green"`, `"yellow"`, `"blue"`, `"magenta"`, `"cyan"`, `"white"`: Level 1 has only these. `paper` costs two cells (the colour, then New Background). `height: 2` takes the row below, which MUST be inside rows 1 to 23. |
| `codes(row, column, codes: Uint8Array)` | Writes raw seven-bit codes (0x00 to 0x7F) for authors who want exact control. A code above 0x7F is a `RangeError`. |
| `blit(codes: Uint8Array)` | Replaces the whole plane, rows 1 to 23: exactly `23 × 40` codes, row by row. One call for a tile map (RPT section 9.2 item 13). The array is copied. |
| `at(row, column) => int` | The code in the host's own copy of the plane. Nothing the renderer drew is read back. |
| `clear(firstRow = 1, lastRow = 23)` | Fills the rows with spaces. |
| `scroll(firstRow, lastRow, rows)` | Moves the rows up (negative) or down by whole rows inside the band; vacated rows are spaces. |
| `settings({ screen?, rowColour?, substitution? })` | The page's X/28/0 format 1 settings (EN clause 9.4.2): default screen colour and default row colour (a Colour Map entry 0 to 31) and black background colour substitution. |

Only rows that changed leave in the step's frame, one packet each.

### 5.2 The overlay, `nt.teletext.overlay`

Cells that carry their own complete look and lie over the page without touching a neighbour: the page's local enhancement data, X/26 (EN clause 12.3), written by the host in the order the standard requires.

| Call | Meaning and bounds |
|---|---|
| `put(row, column, text, { ink?, paper?, flash? })` | Characters with non-spacing attributes (EN Table 29). Colours are Colour Map entries 0 to 31. |
| `fill(row, column, rows, columns, { paper?, ink? })` | Colours a rectangle of cells without changing their characters. |
| `clear()` or `clear(row, column, rows, columns)` | Removes the script's overlay, wholly or in a rectangle. |
| `nt.teletext.overlay.triplets` | `{ used, limit }`: every overlay cell, every diacritical mark or G2 character the encoder placed for page text (5.6), and every control (5.4) is paid for from the page's `LOCAL_TRIPLETS` (208). A call that would pass it throws `RangeError LOCAL_TRIPLETS` and changes nothing. |

### 5.3 Sprites, `nt.teletext.block` and `nt.teletext.sprite`

A sprite is one of the page's at most `MAX_SPRITES` (32) numbered placements of 1 to `MAX_OBJECT_FRAMES` (16) frames, drawn over the page by invoking the frame's object (AN ANIM-7, ANIM-8).

| Call | Meaning and bounds |
|---|---|
| `block(columns, rows) => Block` | A rectangle of cells to draw a frame in, 1 to 40 by 1 to 23. |
| `block.cell(row, column, { char? or sixels?, ink?, paper?, separated? })` | One cell: a character, or a mosaic given as six bits (bit 0 top left, bit 5 bottom right, EN clause 15.6.1). Colours are Colour Map entries 0 to 31. A cell never set is transparent. |
| `block.sixels(lines: string[], { ink?, paper?, separated? })` | Mosaics from lines of `"0"` and `"1"`, two characters a cell across and three lines a cell down. |
| `block.text(row, column, text, { ink?, paper? })` | Characters. |
| `sprite({ frames: Block[], row, column, layer = 2, order = 0, shown = true, detectable = false, wheel = false, label? }) => Sprite` | The host compiles each frame to a Passive object (every cell carries its own attributes, EN clause 13.2) on a host-written object page and declares the sprite in the `SPRITES` record (type 24). Frames of one sprite are one size. A frame that needs more than `OBJECT_BODY_TRIPLETS` (507) triplets is a `RangeError`. `layer` 1 to 3. `label` at most `MAX_LABEL_BYTES`, plain text. |
| `sprite.row`, `sprite.column` (read and write), `moveTo(row, column)`, `moveBy(rows, columns)` | `ANIMATE` move (15). Column −39 to 39, row −24 to 24; no cell outside rows 1 to 23 is drawn. |
| `sprite.shown`, `sprite.layer`, `sprite.order`, `sprite.frame`, `cycle`, `stopCycle` | `ANIMATE` show (5), hide (6), order (16), frame (17), cycle (18), stop_cycle (19). |
| `sprite.remove()`, `bounds()`, `overlaps(other)` | Section 3.9. Bounds are in cells. |

Sprite invocations count toward the page's `OBJECT_INVOCATIONS_PER_TYPE` (127). The host's object page has a page number the decoder reserves for the script; it is never fetched, listed or reachable by a viewer (work package T2 settles the number against the engine's reserved ones).

### 5.4 Controls, `nt.teletext.control`

`control(row, column, columns, { joined = false, label? }) => Control` declares cells the page answers itself (the engine's decision E.127; triplet mode 00101): the receiver shows the hover and pressed looks with no script running. At most `MAX_CONTROLS` (32); each costs one local triplet. A control is a thing: it receives `pointerdown`, `pointerup`, `pointerenter` and `pointerleave`, and `control.look = "hover"`, `"pressed"` or `null` forces a look (`ANIMATE` look, 7).

### 5.5 The Colour Map, `nt.teletext.colours`

| Call | Meaning and bounds |
|---|---|
| `define(name, colour) => int` | Allocates the next free entry of CLUTs 2 and 3 (entries 16 to 31, `TELETEXT_DEFINABLE_COLOURS`) and sets it. `colour` is `"#rgb"` (teletext's 12 bits exactly) or `"#rrggbb"` (the top four bits of each primary). `name` is the script's own, kept for the budget report. A seventeenth is `RangeError TELETEXT_DEFINABLE_COLOURS`. |
| `set(entry, colour)` | Redefines an entry 16 to 31: every cell drawn in it changes and no cell is rewritten. Written as X/28/0 format 1. Held to `MAX_COLOUR_SETS_PER_SECOND` for each entry (section 10.5). |

Entries 0 to 7 are the eight Level 1 colours and 8 to 15 their CLUT 1 copies (entry 8 is transparent); version 1 does not redefine them, so the status rows and components can rely on them. The receiver's own colours, indices 32 to 39, cannot be named.

### 5.6 Text, the encoder and languages

- Text is encoded by the engine's own encoder, `neoteletext_formats::write_runs` (the server's path, DEC-2199), into the page's character sets: a G0 code; ESC to the second G0 set; an X/26 G0 character with a diacritical mark; a G2 character by X/26; NeoTeletext's own row-set triplet. The marks and G2 characters cost local triplets (5.2).
- The page's language is the manifest's `language`, a BCP 47 tag from `neoteletext_formats::languages()` (73 on 22 November 2026: 27 on a standard set, the rest on NeoTeletext's own). `put` and `overlay.put` take `{ language }` for one run in another language.
- **A character the page's sets cannot show is refused, never substituted:** `TypeError` naming the character (the engine's `RunFault::Unshown`).
- `nt.teletext.measure(text, { language? }) => int` gives the cells the text takes.
- `nt.teletext.languages() => { tag, name, direction }[]` lists what the engine has.

### 5.7 The sixel bitmap, `nt.teletext.bitmap`

A double-buffered bitmap of `BITMAP_WIDTH` by `BITMAP_HEIGHT` sixels (80 by 69: two a cell across, three down, over columns 0 to 39 and rows 1 to 23), one colour a sixel (DEC-7245). The script draws into the back buffer; nothing shows until `present()`.

| Call | Meaning and bounds |
|---|---|
| `rows(first, last)` | The rows the bitmap owns (1 to 23 by default). While it owns a row, `page.put`, `page.codes` and `page.blit` on that row throw `TypeError`; text there is `bitmap.text`. |
| `clear(colour = 0)`, `set(x, y, colour)`, `get(x, y) => int`, `line(x0, y0, x1, y1, colour)`, `rect(x, y, width, height, colour, { fill = true })` | Draw in the back buffer. `get` reads the back buffer, which is the script's own. Coordinates outside are clipped. |
| `blit(x, y, width, height, data: Uint8Array, { transparent = 255 })` | One byte a sixel; a byte equal to `transparent` leaves the sixel as it is. The array is copied. |
| `text(row, column, text, { ink?, paper? })` | Reserves cells for characters; those cells hold no sixels until cleared. |
| `present() => { cells: int, lossy: int }` | Converts the back buffer to characters, compares with what is shown, sends only the rows that changed, and returns the cells changed and the cells that lost detail. |

**Colours.** A sixel's colour is 0 to 7, or a defined entry 16 to 31 (5.5).

**The colour rule.** A mosaic cell shows one foreground and one background colour. For each cell the converter counts its six sixels by colour: the commonest is the **background**, the next commonest the **foreground**; a tie goes to the lower entry number; sixels of any third colour are drawn in whichever of the two is nearer in squared 12-bit RGB distance, and the cell is counted in `lossy`.
- **At levels 25 and 35** the two colours are set by X/26 non-spacing foreground and background triplets, only where they differ from the row's Level 1 state, within what `LOCAL_TRIPLETS` leaves; when the triplets run out the remaining cells take the Level 1 rule and are counted lossy if that changes them.
- **At levels 10 and 15** only the eight colours exist (a defined entry is drawn in the nearest of them) and a change of colour costs a cell. Each row is written with Hold Mosaics so that an attribute cell repeats the last mosaic; the mosaic colour is placed in the cell before the first cell that needs it when that cell is empty in the bitmap, otherwise in the cell itself, which then loses its sixels (lossy); a background change costs two cells in the same way.

The conversion is the engine's picture converter's (the crate `neoteletext-picture`, DEC-2325), given an entry point for an indexed raster and this rule, so that there is one converter (work package T3). The buffers are fixed, and a present costs at most one page of changed cells.

**How the models layer.** The bitmap and `page` write the same Level 1 plane, each on the rows it owns. The overlay lies over both; sprites over the overlay in layer and order; controls are cells of the plane.

### 5.8 Worked examples

**A page** (`101.js`): a title, an index and a clock that needs no server.

```js
/*! nt
{ "api": 1, "renderer": "teletext", "tick": 60, "keys": ["1", "2"], "pointer": "press" }
*/
const tt = nt.teletext;
tt.page.put(1, 2, "HARBOUR NEWS", { ink: "yellow", height: 2 });       // codes at columns 0-1
tt.page.put(4, 1, "1 Shipping forecast", { ink: "cyan" });
tt.page.put(5, 1, "2 Tide tables", { ink: "cyan" });
const amber = tt.colours.define("amber", "#fa0");
tt.overlay.fill(22, 0, 1, 40, { paper: amber, ink: 0 });               // a band; no neighbour touched
const forecast = tt.control(4, 1, 19, { label: "Shipping forecast" }); // hover and pressed looks are the receiver's
forecast.addEventListener("pointerup", () => nt.navigate("102"));
nt.addEventListener("keydown", (e) => {
  if (e.key === "1") { nt.navigate("102"); e.preventDefault(); }       // replace the default (page-number entry)
  else if (e.key === "2") { nt.navigate("103"); e.preventDefault(); }
});
nt.addEventListener("tick", () => {
  const t = new Date();
  tt.page.put(22, 31, t.toTimeString().slice(0, 8), { ink: "white" });
});
```

**A small game** (`110.js`): a boat steered between rocks, with sprites and the Colour Map.

```js
/*! nt
{ "api": 1, "renderer": "teletext", "tick": 6, "keys": ["ArrowLeft", "ArrowRight", " "] }
*/
const tt = nt.teletext;
const sea = tt.colours.define("sea", "#024");
tt.overlay.fill(3, 0, 20, 40, { paper: sea });
const hull = tt.block(3, 2).sixels(["011110", "111111", "111111", "100001", "100001", "000000"], { ink: 7 });
const rock = tt.block(2, 1).sixels(["0110", "1111", "1111"], { ink: 3 });
const boat = tt.sprite({ frames: [hull], row: 21, column: 18, layer: 2, label: "Boat" });
const rocks = [];
let score = 0, over = false;
nt.addEventListener("tick", () => {
  if (over) return;
  if (nt.keys.down("ArrowLeft") && boat.column > 0) boat.moveBy(0, -1);
  if (nt.keys.down("ArrowRight") && boat.column < 37) boat.moveBy(0, 1);
  if (Math.random() < 0.2 && rocks.length < 12)
    rocks.push(tt.sprite({ frames: [rock], row: 3, column: Math.floor(Math.random() * 38), layer: 1 }));
  for (const r of rocks.splice(0)) {
    if (r.overlaps(boat)) { over = true; nt.synth.note(0, 36, { ticks: 30 }); tt.colours.set(sea, "#400"); }
    if (r.row >= 22) { r.remove(); score++; } else { r.moveBy(1, 0); rocks.push(r); }
  }
  tt.page.put(1, 30, "SCORE " + String(score).padStart(3, "0"), { ink: "white" });
});
nt.addEventListener("keydown", (e) => { e.preventDefault(); if (e.key === " " && over) nt.navigate(nt.page.number); });
nt.synth.start(0, "sid");
```

---

## 6. The ReGIS API, `nt.regis`

The script's objects are ReGIS v2's numbered drawings themselves (DEC-7247 item 3; R2). Units are pixels, 800 by 480, y down. Translation is the only transform. The host allocates every drawing number (1 to 65,535) and every macrograph letter; a script never sees or chooses one.

### 6.1 Colours, `nt.regis.colours`

The colour map has 16 entries (`REGIS_COLOURS`). ReGIS sets a colour as hue, lightness and saturation; it has no numeric RGB form (RREF, `S(M n(H L S))`).

| Call | Meaning |
|---|---|
| `define(name, colour) => int` | Allocates the next free entry from 1 to 15 and sets it. `colour` is ReGIS's own form `{ h: 0..360, l: 0..100, s: 0..100 }` (hue 0 is blue, 120 red, 240 green), or `"#rgb"` or `"#rrggbb"`, which the host converts to the nearest whole HLS values. |
| `set(entry, colour)` | Redefines entry 0 to 15 (entry 0 is the screen's background). Everything drawn in it changes; nothing is replayed. Held with the step's commit, as the renderer holds a palette change while a batch is open. Rate-held as 5.5. |

### 6.2 Drawings

`nt.regis.drawing(options) => Drawing`. Every option is also a property that can be read and assigned later; an assignment stages the format's own attribute in `D(S n(…))`.

| Option and property | ReGIS attribute | Type and range | Default |
|---|---|---|---|
| `x`, `y` | `X`, `Y` | int, signed 16-bit, relative to the parent | 0 |
| `depth` | `L` | int, signed 16-bit; lowest drawn first | 0 |
| `visible` | `V` | boolean | true |
| `parent` | `P` | Drawing or null; the chain is at most `MAX_DRAWING_DEPTH` (16) | null |
| `source` | `R` | Drawing or null: draw that drawing's contents here | null |
| `detectable` | `I` | boolean | false |
| `hover`, `pressed`, `alternative` | `H`, `A`, `N` | Drawing or null: the looks the receiver draws in this drawing's place | null |
| `clip` | `C(X,Y,W,H)` | `{ x, y, width, height }` or null | null |
| `layer` | `G` | 0 background (kept as its own raster), 1 scene, 2 sprites, 3 overlay; a child is in its top-level ancestor's layer | 1 |
| `frames` | `F(n,…)` | array of 1 to `MAX_OBJECT_FRAMES` Drawings, or null | null |
| `paintRate` | `T` | null (unset: the receiver's default rate applies), 0 (at once) or 1 to `MAX_PAINT_RATE` (32,767), in units of 100 work units a second | null |
| `label` | `U` | string of at most `MAX_LABEL_BYTES` (64) bytes of ISO 8859-1 printable characters, or null | null |
| `wheel` | (host) | boolean: wheel events are sent over it | false |

| Method | Meaning |
|---|---|
| `draw(fn: (p: RegisPainter) => void)` | Defines or redefines the contents: `D(B n) … D(E)`. Redefining keeps attributes and children, replays inside the damage and restarts gradual painting (R2). Contents are at most `REGIS_MAX_CONTENTS_BYTES` a drawing and `REGIS_MAX_TOTAL_CONTENTS_BYTES` a page. |
| `moveTo(x, y)`, `moveBy(dx, dy)` | Assign `x` and `y`. |
| `frame` (property), `cycle(first, last, period, { once })`, `stopCycle()` | Which entry of `frames` is drawn, by the receiver's animation state (`ANIMATE` 17, 18, 19). At most `MAX_ANIMATED_DRAWINGS` (64) drawings hold animation state and `MAX_CYCLING_OBJECTS` (16) cycle. |
| `look` (property) | `null`, `"hover"`, `"pressed"` or `"alternative"`: a forced look (`ANIMATE` look, 7). |
| `remove()` | `D(K n)`: deletes it and its current children. Their handles become stale. |
| `bounds()` | The drawing's rectangle on the screen as of the last step, for a drawing created or set with `track: true` (at most `MAX_TRACKED_DRAWINGS`); null otherwise or when hidden. It is the renderer's `Terminal::bounds`, sent with each step. |
| `overlaps(other)` | Both tracked: their rectangles intersect. |
| event `painted` | The drawing is whole (the painted report, R2). Adding a listener watches it; at most `MAX_WATCHED_PAINTINGS` (32). |

| Function | Meaning |
|---|---|
| `nt.regis.symbol(fn) => Drawing` | A hidden master: a drawing with `visible: false`, named as another's `source`, `hover`, `pressed`, `alternative` or frame. |
| `nt.regis.group(options) => Drawing` | A drawing with no contents, to parent others; with `clip` it is a panel, and moving it scrolls its children. |
| `nt.regis.macrograph(fn: (p) => void) => Macrograph` | Defines one of the 26 macrographs (`@:x … @;`), at most `MAX_MACROGRAPH_BYTES` (16,384) in all. A painter calls it with `p.call(m)`. Macrographs are a global table: a drawing uses them as they stood at the last commit. `m.redefine(fn)` changes it for every later commit. |
| `nt.regis.clear()` | `D(Z)`: deletes every drawing of the page context. |

**Commit.** The host appends one `D(C)` at the end of a step that staged anything, so a step is one atomic commit and one damage repaint. Before it leaves, the host runs the step's bytes through the renderer's own `Validator` (R2 "Checking before sending"); if the commit would fail (the eight `CommitError` codes: contents, staged, depth, cycle, parent, work, malformed, drawings), the whole step's ReGIS changes are discarded, the host's tables are put back, and an `error` event carries a `RangeError` naming the code and the drawing. The base (the v1 bitmap) is not offered: it has no identity; what never moves goes in layer 0.

### 6.3 The painter, `RegisPainter`

Inside `draw`, the painter's calls are encoded by the host as the drawing's contents: default addressing, one unit a pixel, [0,0] at the drawing's own origin, the full signed 16-bit range. It owns write state and string quoting, so the contents are always one well-formed definition. `S`, `L`, `R`, macrograph definitions and `D` are never written inside contents (the renderer ignores them there). Each call returns the painter.

| Call | ReGIS written | Notes and ranges |
|---|---|---|
| `moveTo(x, y)`, `moveBy(dx, dy)` | `P[x,y]`, `P[+dx,+dy]` | |
| `lineTo(x, y)`, `lineBy(dx, dy)`, `dot()` | `V[x,y]`, `V[+dx,+dy]`, `V[]` | |
| `polyline(points)`, `polygon(points)` | `P[..]V[..]…`; closed with `V(B)…(E)` | at most `MAX_POINTS` points |
| `rect(x, y, width, height)` | four vectors | |
| `vector(digits, { multiplier })` | `W(M n)` and `V<pv>` | pixel vectors, digits 0 to 7 |
| `circle(radius)`, `circleThrough(x, y)` | `C[+r,+0]`, `C[x,y]` | about the current position |
| `arc(cx, cy, degrees)` | `C(A d C)[cx,cy]` | −360 to 360, anticlockwise positive |
| `curve(points, { closed = false })` | `C(S)…(E)` or `C(B)…(E)` | the renderer's interpolated curve |
| `fill(fn: (p) => void)` | `F( … )` | fills the outline the calls inside trace, even-odd; at most `MAX_FILL_VERTICES` (4,096) |
| `ink(entry)` | `W(I n)` | a colour-map entry 0 to 15 |
| `mode(m)` | `W(V)`, `W(R)`, `W(C)`, `W(E)` | `"overlay"`, `"replace"`, `"complement"`, `"erase"`: ReGIS's writing modes, applied to the pixels beneath in depth order |
| `negative(on)` | `W(N1)`, `W(N0)` | |
| `pattern(p, { multiplier = 1 })` | `W(P n)`, `W(P n(M m))` | a standard pattern 0 to 9, or eight bits as a string of `"0"` and `"1"`; multiplier 1 to `MAX_PATTERN_MULTIPLIER` (16) |
| `planes(mask)` | `W(F n)` | 0 to 15 |
| `shade(s)` | `W(S1)`, `W(S0)`, `W(S[,y])`, `W(S(X)[x])`, `W(S'c')` | `true`, `false`, `{ toY }`, `{ toX }` or `{ char }`: ReGIS's shading to a line, and shading with a character |
| `text(string, options?)` | `T(…)'…'` | at the current position; at most `MAX_STRING_BYTES` (1,024) bytes after encoding |
| text options | `T(S n)`, `T(S[w,h])`, `T(U[w,h])`, `T(H n)`, `T(D a)`, `T(I a)`, `T[dx,dy]` | `size` 0 to 16; `cell` and `unit` as `[w, h]`; `height` 1 to 256; `tilt` a multiple of 45; `italic` 0, ±22 or ±45; `spacing` `[dx, dy]`; `language` |
| `call(macrograph)` | `@x` | |

**Text and languages.** The host chooses the alphabet from the language: alphabet 0 for ASCII, the provided sets 100 to 154 for the rest (the same 55 sets as teletext), joining Arabic-script letters (R2). A character none of them holds is a `TypeError` naming it. `nt.regis.measure(string, options) => { width, height }` gives the pixels the text takes, computed by the host from the cell sizes the options select (size 0 is 9 by 10, 1 is 9 by 20, n is 9n by 15n; RREF), since the renderer has no measuring call.

### 6.4 Worked examples

**A page:** a painted background, a caption painted gradually, a button with receiver-run looks.

```js
/*! nt
{ "api": 1, "renderer": "regis", "pointer": "press", "keys": ["Enter"] }
*/
const g = nt.regis;
const sky = g.colours.define("sky", { h: 0, l: 25, s: 60 });
const ink = g.colours.define("ink", "#fff");
const hot = g.colours.define("hot", "#f80");
g.drawing({ layer: 0 }).draw((p) => {                        // layer 0 is kept as a raster
  p.ink(sky).fill((q) => q.rect(0, 0, 800, 480));
  p.ink(ink).moveTo(60, 40).text("HARBOUR PATROL", { size: 3 });
});
const caption = g.drawing({ x: 60, y: 420, paintRate: 20 }); // 2,000 work units a second
caption.draw((p) => p.ink(ink).text("Press the button or Enter."));
caption.addEventListener("painted", () => nt.sound.play(1));
const face = (c) => g.symbol((p) => { p.ink(c).fill((q) => q.rect(0, 0, 160, 40)); p.ink(0).moveTo(40, 10).text("START"); });
const button = g.drawing({ x: 320, y: 300, source: face(ink), hover: face(hot), pressed: face(sky), detectable: true, label: "Start" });
const start = () => nt.navigate("106");
button.addEventListener("pointerup", start);
nt.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); start(); } });
```

**A small game:** catch falling crates with a boat; drawings moved by properties, one commit a step.

```js
/*! nt
{ "api": 1, "renderer": "regis", "tick": 2, "keys": ["ArrowLeft", "ArrowRight"] }
*/
const g = nt.regis;
const sea = g.colours.define("sea", "#036"), wood = g.colours.define("wood", "#a62"), ink = g.colours.define("ink", "#fff");
g.drawing({ layer: 0 }).draw((p) => p.ink(sea).fill((q) => q.rect(0, 400, 800, 80)));
const boatShape = g.symbol((p) => p.ink(wood).fill((q) => q.polygon([[0, 0], [80, 0], [64, 20], [16, 20]])));
const crateShape = g.symbol((p) => p.ink(wood).pattern(4).fill((q) => q.rect(0, 0, 16, 16)));
const boat = g.drawing({ source: boatShape, layer: 2, x: 360, y: 380, track: true });
const score = g.drawing({ x: 640, y: 16, layer: 3 });
let crates = [], caught = 0;
const show = () => score.draw((p) => p.ink(ink).text("CAUGHT " + caught, { size: 2 }));
show();
nt.addEventListener("tick", (e) => {
  if (nt.keys.down("ArrowLeft")) boat.x = Math.max(0, boat.x - 8);
  if (nt.keys.down("ArrowRight")) boat.x = Math.min(720, boat.x + 8);
  if (e.tick % 40 === 0 && crates.length < 16)
    crates.push(g.drawing({ source: crateShape, layer: 2, x: Math.floor(Math.random() * 780), y: 0 }));
  crates = crates.filter((c) => {
    c.y += 4;
    const hit = c.y >= 364 && c.y <= 396 && c.x + 16 > boat.x && c.x < boat.x + 80;
    if (hit) { caught++; show(); nt.synth.note(0, 72); }
    if (hit || c.y > 480) { c.remove(); return false; }
    return true;
  });
});
nt.synth.start(0, "juno");
```

---

## 7. The NAPLPS API, `nt.naplps`

NAPLPS keeps no scene: a stream paints a picture and is forgotten. The script holds what the format and NeoTeletext retain (DEC-7247 item 4): a paint-once **backdrop**, the **colour map** as the first animation channel, **definitions** (macros, DRCS characters, textures) and a **cast** of at most 64 actors. Units are dots of the 480 by 460 canvas, origin top left, y down (DEC-6853, DEC-6857); the host maps a dot to raster line + 20 and to the standard's unit square with six-byte operands (RAS-2, RAS-6), so every coordinate is exact.

### 7.1 The colour map, `nt.naplps.colours`

The map has 16 entries (the browser's `PALETTE_BITS` is 4). At the start of every generation the host sets entries 0 to 7 to teletext's eight colours, so that the names `"black"` to `"white"` mean the same as elsewhere; entries 8 to 15 are the script's.

| Call | NAPLPS written | Meaning and bounds |
|---|---|---|
| `define(name, colour) => int` | `SELECT COLOR` and `SET COLOR` | Allocates the next free entry of 8 to 15 and sets it. `colour` is `"#rgb"` or `"#rrggbb"`; the renderer keeps 8 bits a primary. |
| `set(entry, colour)` | the same | Redefines an entry 8 to 15: everything painted in it changes and no pixel is repainted. Rate-held as 5.5. |
| `blink(entry, { to, on = 5, off = 5, delay = 0 })` | `BLINK` | The receiver alternates the entry with entry `to`: `on`, `off` and `delay` in tenths of a second, 0 to 63 each. At most `MAX_BLINKS` (32) blink processes. Played on the colour map alone, with the script not running. |
| `steady(entry)` | `BLINK` with zero intervals | Stops the entry's blinks. |

### 7.2 The backdrop, `nt.naplps.backdrop`

| Call | Meaning and bounds |
|---|---|
| `paint(fn: (p: NaplpsPainter) => void)` | Appends to the picture, in order, over what is there. Nothing painted has an identity; to change it the script paints over it. At most `NAPLPS_MAX_BYTES_PER_CALLBACK` a callback and `NAPLPS_MAX_BYTES_PER_SECOND` a second. |
| `repaint(fn)` | Starts a new generation and paints again from nothing: the one expensive operation, held to one every `NAPLPS_REPAINT_TICKS`; a second call inside that time throws `RangeError`. The host sends the definitions, the colour map and the cast again, so the script sees nothing but the new backdrop; blinks and WAITs restart. |
| event `painted` on `backdrop` | The player is idle: everything appended has been painted and every WAIT has passed (`Player::idle`). |

### 7.3 The painter, `NaplpsPainter`

The painter owns every piece of hidden presentation state (the drawing point, colour mode, DOMAIN, text attributes, texture, the designated and shifted sets) and writes only what differs; a script cannot desynchronise it. Calls return the painter. "abs" and "rel" name the standard's two forms: NAPLPS draws either to an absolute point or by a step from the drawing point, and the relative forms are part of its character (a shape written in steps can be stamped anywhere).

| Call | Opcode (NREF) | Notes |
|---|---|---|
| `moveTo(x, y)`, `moveBy(dx, dy)` | POINT SET abs 24, rel 25 | |
| `pointAt(x, y)`, `pointBy(dx, dy)` | POINT abs 26, rel 27 | one logical pel |
| `lineTo(x, y)`, `lineBy(dx, dy)` | LINE abs 28, rel 29 | from the drawing point |
| `polyline(points)`, `polylineBy(steps)` | SET & LINE 2A, LINE rel 29 | at most `MAX_POINTS` |
| `rect(x, y, width, height)`, `fillRect(x, y, width, height)` | SET & RECT 32, 33 | exact cells of dots (RAS-6) |
| `rectBy(width, height)`, `fillRectBy(width, height)` | RECT 30, 31 | from the drawing point, which then moves by `width`: adjoining rectangles, as bars of a chart |
| `polygon(points)`, `fillPolygon(points)`, `polygonBy(steps)`, `fillPolygonBy(steps)` | SET & POLY 36, 37; POLY 34, 35 | closed; even-odd fill; at most `MAX_VERTICES` |
| `arc(mx, my, ex, ey)`, `fillArc(…)` | SET & ARC 2E, 2F | from the drawing point through a middle point to an end point; filled is arc and chord |
| `circle(cx, cy, radius)`, `disc(cx, cy, radius)` | SET & ARC with one step | a full circle on its diameter |
| `trace(dx, dy, moves)`, `fillTrace(dx, dy, moves)` | INCREMENTAL LINE 3A, POLYGON 3B | a chain of unit moves: `moves` is a string of `"x"`, `"y"`, `"d"` (both), `"u"` and `"n"` (pen up and down), `"<"` and `"^"` (reverse a direction); compact outlines |
| `image(x, y, width, height, pixels: Uint8Array)` | FIELD 38, INCREMENTAL POINT 39 | a small bitmap of colour-map entries, at most `NAPLPS_MAX_IMAGE_PELS` |
| `ink(entry)` | SELECT COLOR, mode 1 | draw with an entry |
| `inkOn(entry, background)` | SELECT COLOR, mode 2 | draw with an entry on a background entry: text fields and texture gaps are filled |
| `pen(width, height)` | DOMAIN | the logical pel, in dots: thick lines |
| `stroke(s)` | TEXTURE | `"solid"`, `"dotted"`, `"dashed"`, `"dotdash"` |
| `fillStyle(s)` | TEXTURE | `"solid"`, `"vertical"`, `"horizontal"`, `"cross"`, or a `Texture` (7.4) |
| `highlight(on)` | TEXTURE | filled shapes are outlined in black |
| `mask(width, height)` | TEXTURE | the pattern's size in dots |
| `text(row, column, string, { size = "normal", language? })` | text on the cell grid | One 12 by 20 cell a character, 40 columns, rows 1 to 23, as RAS-8 places it. `size`: `"normal"`, `"double-height"`, `"double-size"`. This is how text lines up with teletext's grid and with components. |
| `textAt(x, y, string, options)` | TEXT 22 and the size controls | Free text: `{ width, height }` of the character field in dots; `rotation` 0, 90, 180 or 270; `path` `"right"`, `"left"`, `"up"`, `"down"`; `spacing` 1, 1.25, 1.5 or `"proportional"`; `rowSpacing` 1, 1.25, 1.5 or 2; `underline`, `reverse`; `language`. |
| `glyph(drcs)` | the DRCS set | Draws a DRCS character (7.4) at the cursor in the current colour, size and rotation. |
| `stamp(symbol, x, y)` | POINT SET and the macro set | Runs a symbol's macro at a point. |
| `wait(tenths)` | WAIT 3D | Backdrop only: the receiver pauses the painting, for staged reveals. At most `WAIT_BUDGET_TICKS` (3,600 ticks) a generation; beyond that waits pass at once. |

**Text and languages.** The host designates the set for the language: the primary and supplementary sets for ASCII and accented Latin, and NeoTeletext's 55 sets by their private designations for the rest (REQ-6668), with Arabic-script letters joined. A character none holds is a `TypeError`. `nt.naplps.measure(string, options) => { width, height }` is computed by the host from the field size; with `"proportional"` spacing it is the upper bound of fixed spacing, because the renderer offers no measure.

### 7.4 Definitions

| Call | NAPLPS | Meaning and bounds |
|---|---|---|
| `symbol({ width, height }, fn) => Symbol` | DEF MACRO | A macro the host names (96 codes, 0x20 to 0x7F), drawn entirely in relative forms from its own origin, at most `MAX_MACRO_BYTES` (4,096) each and `MAX_ALL_MACRO_BYTES` (65,536) in all. Used as an actor's frame or look, or stamped. |
| `symbol.redefine(fn)` | DEF MACRO | Every actor drawn by it changes: actors are drawn by their macros as last defined (AN ANIM-11). |
| `drcs(fn) => Drcs` | DEF DRCS | A downloadable character: the painter draws a one-bit shape in the unit character field (ink sets a dot, entry 0 clears). 96 codes; at most 128 dots on the longer side. NAPLPS DRCS is allowed (the teletext ban, REQ-2196, is teletext's alone). |
| `texture({ width, height }, fn) => Texture` | DEF TEXTURE | One of four programmable fill patterns (A to D), tiled from the screen's origin. A fifth is `RangeError TEXTURE_MASKS`. |

Inside a symbol used by an actor, colour-map redefinition, BLINK, WAIT, RESET and every definition do nothing, and the macro cannot read the picture (AN ANIM-11); the painter refuses those calls there with a `TypeError` rather than writing bytes that would be ignored.

### 7.5 The cast

| Call | Meaning and bounds |
|---|---|
| `actor({ frames: Symbol[], x, y, width?, height?, originX = 0, originY = 0, layer = 2, order = 0, shown = true, detectable = false, wheel = false, hover?, pressed?, alternative?, label? }) => Actor` | A macro object of the `NAPLPS_OBJECTS` record (type 25): 1 to 16 frames; a rectangle of 1 to 480 by 1 to 460 dots (the first frame's size by default) that clips it; three look macros the receiver shows; `layer` 1 to 3; `order` −128 to 127; `label` at most 64 bytes of UTF-8. At most `MAX_OBJECTS` (64). An actor's macro stops after `MAX_OBJECT_BYTES` (16,384) processed bytes. |
| `region({ x, y, width, height, cover, detectable = true, hover?, pressed?, label? }) => Region` | A region object: shown, it changes nothing; hidden, it covers its rectangle with the entry `cover`. With `detectable` it is how a part of the backdrop takes the pointer. |
| `actor.x`, `actor.y`, `moveTo`, `moveBy`, `shown`, `layer`, `order`, `frame`, `cycle`, `stopCycle`, `look` | The `ANIMATE` operations (5, 6, 7, 15 to 19). |
| `actor.redefine(options)` | Sends the one object again (the record's `ONE` flag); the others and their state are kept. |
| `remove()`, `bounds()`, `overlaps(other)` | Section 3.9; in dots. |

### 7.6 Worked examples

**A page:** a staged reveal, a textured sea, a lamp lit by the colour map.

```js
/*! nt
{ "api": 1, "renderer": "naplps", "keys": ["l", "b"] }
*/
const n = nt.naplps;
const sky = n.colours.define("sky", "#136"), sea = n.colours.define("sea", "#024");
const lamp = n.colours.define("lamp", "#000"), foam = n.colours.define("foam", "#9cf");
const waves = n.texture({ width: 12, height: 6 }, (p) => p.ink(1).polylineBy([[3, 3], [3, -3], [3, 3]]));
n.backdrop.paint((p) => {
  p.ink(sky).fillRect(0, 0, 480, 300);
  p.wait(5);                                             // half a second, played by the receiver
  p.inkOn(foam, sea).fillStyle(waves).fillRect(0, 300, 480, 160);
  p.wait(5);
  p.ink("white").text(2, 4, "HARBOUR LIGHT", { size: "double-height" });
  p.ink(lamp).fillStyle("solid").disc(420, 90, 10);      // painted dark; lit later by the map alone
  p.ink("white").stroke("dashed").moveTo(420, 100).lineBy(0, 200);
});
nt.addEventListener("keydown", (e) => {
  e.preventDefault();
  if (e.key === "l") n.colours.set(lamp, "#fe8");
  else n.colours.blink(lamp, { to: sky, on: 5, off: 5 });
});
```

**A small game:** a gull to steer past kites; actors, frame cycling and rectangle tests.

```js
/*! nt
{ "api": 1, "renderer": "naplps", "tick": 2, "keys": ["ArrowUp", "ArrowDown"] }
*/
const n = nt.naplps;
const sky = n.colours.define("sky", "#136");
n.backdrop.paint((p) => p.ink(sky).fillRect(0, 0, 480, 460));
const wing = (dy) => n.symbol({ width: 24, height: 12 }, (p) => p.ink("white").moveBy(0, 6 + dy).polylineBy([[6, -2 * dy], [6, 2 * dy], [6, -2 * dy], [6, 2 * dy]]));
const gull = n.actor({ frames: [wing(4), wing(-4)], x: 60, y: 220, label: "Gull" });
gull.cycle(0, 1, 15);                                    // the receiver flaps the wings
const kiteShape = n.symbol({ width: 16, height: 24 }, (p) => p.ink("red").moveBy(8, 0).fillPolygonBy([[8, 10], [-8, 14], [-8, -14]]));
let kites = [], passed = 0;
nt.addEventListener("tick", (e) => {
  if (nt.keys.down("ArrowUp")) gull.moveBy(0, -6);
  if (nt.keys.down("ArrowDown")) gull.moveBy(0, 6);
  if (e.tick % 60 === 0 && kites.length < 8)
    kites.push(n.actor({ frames: [kiteShape], x: 470, y: 20 + Math.floor(Math.random() * 400), layer: 1 }));
  kites = kites.filter((k) => {
    k.moveBy(-5, 0);
    if (k.overlaps(gull)) { nt.synth.note(0, 40, { ticks: 20 }); passed = 0; }
    if (k.x < -16) { k.remove(); passed++; return false; }
    return true;
  });
  nt.page.title = "Gull: " + passed;
});
nt.synth.start(0, "synth8");
```

---

## 8. Components, `nt.ui`

One vocabulary, the same names, options and events on every renderer, each implemented on its renderer's own model (DEC-7205). It is the one place a retained, DOM-like tree belongs (DEC-7247 item 1): a component is created once, changed by its options, and reports events; its view state (a highlighted row, a scroll position, a field's text and caret) is the host's. Components are implemented in Rust in the script host, on the same tables and allocators as the script's own things, so the two cannot collide.

**Placement.** Every component takes `at: { row, column, columns, rows }` on the 40 by 23 cell grid, on every renderer: a cell is 12 by 20 NAPLPS dots and 20 by 20 ReGIS pixels (the 800 by 460 pixels below the top 20 rows of pixels are the grid). There is no layout engine in version 1; rows and columns are the author's arithmetic, or a script library's.

**Common options:** `id` (a string at most `MAX_UI_ID_BYTES`, for the script), `label` (spoken by a screen reader), `disabled`, `ink`, `paper` (named colours or entries of the renderer), `language`. **Common members:** `set(options)` changes any option; `remove()`; `focus()`; the component is an `EventTarget`. At most `MAX_COMPONENTS` components and `MAX_UI_ITEMS` items in one.

**Focus and keys.** One component of a context has the focus. A `keydown` or `text` event is offered to the focused component first; what it does with the key is that event's default action, so a listener on the component (or on `nt`, which hears it next) may cancel or replace it. A component uses only keys the manifest claims: a page with a menu claims `ArrowUp`, `ArrowDown` and `Enter`; `nt.ui.keys(kind)` returns the names a kind uses, for the author to copy. `Tab` and `Shift+Tab`, when claimed, move the focus in creation order.

**The first set** (the thirteen the channels use most or that every interactive page needs, from the count of uses in the channel repositories on 22 November 2026):

| Kind | Options | Events (default action) | Keys |
|---|---|---|---|
| `frame` | `title`, `hint`, `prompts` (up to four coloured labels), `bare` | none | none |
| `text` | `text`, `align`, `height` (1 or 2), `fit` (`"refuse"`, `"shrink"`, `"cut"`) | none | none |
| `paragraph` | `text`, `lines`, `more` (a prompt when it does not fit) | `page` (shows the next part) | `" "`, `PageDown`, `PageUp` |
| `band` | `text` | none | none |
| `link` | `text`, `target` (as `nt.navigate`) | `activate` (navigates) | `Enter` |
| `button` | `text` | `activate` | `Enter`, `" "` |
| `menu` | `items: { text, value?, target?, disabled? }[]`, `selected`, `shown` (rows visible) | `move` (moves the highlight), `activate` (navigates when the item has `target`) | `ArrowUp`, `ArrowDown`, `Home`, `End`, `Enter` |
| `table` | `columns: { title, width, align }[]`, `rows: string[][]`, `selectable`, `shown` | `move`, `activate` | as `menu`, and `PageUp`, `PageDown` |
| `field` | `value`, `longest`, `placeholder`, `masked` | `change` (takes the text), `submit`, `cancel` | the manifest's `text` claim; `Enter`, `Escape`, `Backspace`, `ArrowLeft`, `ArrowRight` |
| `toggle` | `text`, `on` | `change` (flips) | `Enter`, `" "` |
| `slider` | `min`, `max`, `step`, `value` | `change` (moves) | `ArrowLeft`, `ArrowRight` |
| `progress` | `value`, `max`, `text` | none | none |
| `clock` | `format` (`"HH:MM"`, `"HH:MM:SS"`), `zone` (`"local"`, `"utc"`) | none | none; drawn by the host each second |

Every event carries `component`, and `value` where there is one; `activate` and `change` are cancelable.

**How each is built** (the pattern; work packages U1 to U3 carry each kind):

| | Teletext | ReGIS | NAPLPS |
|---|---|---|---|
| Static text (`frame`, `text`, `band`, `paragraph`, `progress`) | The page plane, with spacing attributes; a band's colour by the overlay | One drawing in layer 1 for each component, text in the provided sets, shrunk before cut | Painted on the backdrop on the cell grid; a change paints the cells over |
| Things the pointer takes (`button`, `link`, `toggle`, `menu` and `table` rows) | Controls (5.4): hover and pressed looks are the receiver's, by the adjacent CLUT | A child drawing for each, with `hover` and `pressed` looks the receiver draws; a `menu` is a group with a clip, scrolled by moving it | Regions for the pointer; one highlight actor moved over the rows |
| The highlight | A change of row background by the overlay | The `alternative` look forced on one row | An actor |
| `field` | Cells of the plane; the caret a flashing cell | A drawing redefined on change; the caret a child drawing cycling two frames | Painted on the backdrop; the caret an actor with a two-frame cycle |
| `slider` | Mosaic cells | A track drawing and a thumb moved by `x` | A track on the backdrop and a thumb actor |
| `clock` | Cells rewritten each second | One drawing redefined each second | An actor whose frames are digits is too many macros; the cells are painted over each second |
| Accessibility | The cells are text already; controls are announced as today | Each drawing's label | Each object's label |

Components draw in the scene layers and count against the same budgets as the script (`nt.budget()`): a page that runs out is told at the call.

---

## 9. The web APIs

### 9.1 What is provided, by reference to its standard

Each of these is a global of every context, with the names, arguments, results, errors and behaviour its standard gives, except for the numbered departures of 9.4. Nothing else of the web platform exists: there is no `window`, `document`, `navigator`, `location`, `XMLHttpRequest`, `localStorage`, `indexedDB`, `Worker`, `importScripts`, `eval` of fetched text as a module, `WebAssembly` or `Intl`.

| API | Standard | Built how (DEC-7260) |
|---|---|---|
| `fetch`, `Request`, `Response`, `Headers` | FETCH | Our JavaScript in the prelude over host operations 41 to 44; the network half in the partition's web client |
| `ReadableStream`, `WritableStream`, `TransformStream`, the queuing strategies | STREAMS | web-streams-polyfill, pinned and bundled (DEC-7261) |
| `TextDecoderStream`, `TextEncoderStream`, `CompressionStream`: only the first two | ENC | Over the polyfill and `TextDecoder` |
| `AbortController`, `AbortSignal` (`abort`, `timeout`, `any`), `EventTarget`, `Event`, `CustomEvent`, `MessageEvent`, `CloseEvent`, `ErrorEvent`, `PromiseRejectionEvent` | DOM, HTML | Prelude |
| `DOMException` | Web IDL | Prelude |
| `URL`, `URLSearchParams`, `URL.canParse`, `URL.parse` | URL | Parsed by the host with the `url` crate (operation 40), so the script and the fetcher agree on every address |
| `TextEncoder`, `TextDecoder` | ENC | UTF-8 in the prelude; every other encoding of the standard by the host (operation 49, the pure-Rust `encoding_rs`) |
| `Blob`, `File` | FILEAPI | Prelude; no `URL.createObjectURL` (D11) |
| `FormData` | XHR | Prelude; sent as `multipart/form-data`, and parsed from `multipart/form-data` and `application/x-www-form-urlencoded` answers |
| `EventSource` | HTML section 9.2 | The object in the prelude; the event-stream parser, reconnection, `retry` and `Last-Event-ID` in the fetcher, as the fetcher session built them (a request of the kind "event stream"), each event bounded by `MAX_EVENT_TYPE_BYTES`, `MAX_EVENT_ID_BYTES` and `MAX_EVENT_DATA_BYTES` |
| `WebSocket` | WS; RFC 6455 | Prelude over host operations 45 to 47; the handshake and framing in the fetcher |
| `setTimeout`, `setInterval`, `clearTimeout`, `clearInterval`, `queueMicrotask`, `structuredClone`, `atob`, `btoa`, `console`, `reportError` | HTML, Console | Prelude and host |
| `performance.now()`, `performance.timeOrigin` | High Resolution Time | Host, in ticks (D13) |
| `crypto.getRandomValues`, `crypto.randomUUID` | Web Cryptography | Host operation 18, from the host's generator, which the trusted core seeds for each context |

### 9.2 How a request travels

A script never touches the network. `fetch` turns its `Request` into one flat `Start` message (section 11.3); the partition's web client, which alone has the network, applies `ChannelPolicy` (section 2) and the whole of FETCH's network half: the scheme check, bad ports, the referrer and its policy, the `Origin` header, CORS and its preflight with a preflight cache, credentials and the channel's cookie jar, redirects in each mode with no downgrade from `https:`, the cache modes over an RFC 9111 cache, `integrity`, the refusal of local-network addresses (P7), decompression of `gzip`, `deflate` and `br` with a bound on the decompressed size, and every limit and timeout. The answer returns as events: one head, body chunks under a credit window so that a slow script holds the fetcher back and not the reverse, and an end or a failure. A failure reaches the script only as the standard's `TypeError` (or `AbortError`, `TimeoutError`); the reason goes to the developer log, never to the script, so that a script cannot map the viewer's network by error text.

**The origin of a script** is the origin of its channel. The `Origin` header and CORS use it. A script's *base URL* is the address of its own file.

### 9.3 Cookies

Cookies are the fetcher's (DEC-7260 item 8): the `cookie` and `cookie_store` crates, one jar for each `JarKey` (P3), with what COOKIES requires beyond the crates added and tested: SameSite enforcement, the `__Host-` and `__Secure-` prefixes, the cap on a cookie's lifetime, the limits on size and count, and the public suffix list. A script has no access to any cookie: there is no `document.cookie` because there is no document, and version 1 provides no Cookie Store API. That is not a departure (a web worker has none either), and it makes every cookie behave as `HttpOnly` towards scripts. `Set-Cookie` is never visible in `Headers` (FETCH's forbidden response-header name).

### 9.4 The departures, each with its reason

Every difference from a standard is listed here and nowhere else; anything not listed is a fault to be fixed. The web-platform-tests results (work package W3) are kept per test case, and a failing case MUST map to one of these or be fixed.

| # | Standard | The standard says | NeoTeletext does | Reason |
|---|---|---|---|---|
| D1 | FETCH | A request to the same origin is same-origin | A request to the same origin outside the channel's folder is cross-origin: CORS, preflight, credentials only by `include` (P2) | REQ-712: the channel is the unit of isolation, and channels share origins (DEC-7264) |
| D2 | COOKIES | One jar; Domain and Path decide which cookies go | One jar for each channel identity and window jar; inside it the standard's rules (P3) | REQ-712, DEC-7264: Path is no security boundary (RFC 6265 section 8.6) |
| D3 | FETCH, RFC 9111 | One HTTP cache (browsers already partition it by site) | The HTTP cache, the preflight cache and connection-bound state are keyed by channel identity (P4) | REQ-712, DEC-7264 |
| D4 | HTML | A script may be loaded from any origin | A channel's scripts load only from inside its own folder (P5) | REQ-712, DEC-7264, DEC-7255's same-origin recommendation |
| D5 | FETCH | `mode: "no-cors"` gives an opaque response | `mode: "no-cors"` rejects with `TypeError` | An opaque response exists to feed elements (`<img>`, `<script>`) that do not exist here; without them it is only a way to send credentialed requests blind |
| D6 | FETCH | Requests to private addresses are allowed (the Private Network Access work is changing this) | Refused on every resolved address and redirect unless the channel itself is on such an address (P7) | A public page must not reach a viewer's router or devices; the standard's direction, taken early |
| D7 | FETCH | `duplex: "half"` streams a request body | A `ReadableStream` request body is read to its end (at most `MAX_REQUEST_BODY_BYTES`) and sent with its length | Two of three browser engines do not stream uploads either; it needs HTTP/2-only paths; reconsider with a use |
| D8 | FETCH | No limit on body sizes, header sizes or the number of requests | Named bounds (section 10.6): at most `MAX_REQUESTS_IN_FLIGHT` in flight with further ones queued to `MAX_REQUESTS_QUEUED`; `MAX_REQUESTS_PER_STEP` and `MAX_REQUESTS_PER_SECOND` started; URL, header and request-body sizes bounded; a response body is unbounded as a stream but `text()`, `json()`, `arrayBuffer()`, `bytes()`, `blob()` and `formData()` reject with `TypeError` past `MAX_RESPONSE_BUFFER_BYTES`. Beyond a bound the promise rejects with `TypeError` | All input is bounded (DEVELOPMENT.md section 6); the review's lead that requests need rate limits for each callback |
| D9 | FETCH | `keepalive` requests outlive the page | Honoured for requests started in the `close` handling, with the standard's 64 KiB quota and a deadline of `KEEPALIVE_SECONDS`; the answer is discarded | The same purpose, bounded |
| D10 | FETCH | `blob:`, `about:` and `data:` URLs can be fetched | `data:` is fetched (in the prelude); `blob:` and `about:` reject | No object URLs exist (D11) |
| D11 | FILEAPI | `URL.createObjectURL` | Not provided | Nothing can consume an object URL |
| D12 | HTML | Timer delays are milliseconds, clamped to 4 ms when nested | A delay is rounded up to whole ticks of 1/60 s; the least is one tick | One presentation clock (AN ANIM-1); no clock finer than a tick exists for a script (RPT section 7.8 item 4) |
| D13 | High Resolution Time | `performance.now()` is fine-grained | It advances once a tick | The same: no instrument for timing attacks |
| D14 | ECMAScript | `Date` gives milliseconds | The time is given to the tick it was read in | The same |
| D15 | ECMAScript | `Math.random` is unseeded | Seeded for each context from the trusted core's fresh seed; in the runner alone, from its command line. `crypto.getRandomValues` is a cryptographic generator, never predictable from `Math.random` | Deterministic runs in tests (RPT section 9.2 item 2); no shared state between tabs |
| D16 | DOM | `AbortSignal.timeout(ms)` | Rounded up to ticks | D12 |
| D17 | HTML | `structuredClone` copies every serializable type | JSON-representable values, `Date`, `Map`, `Set`, `ArrayBuffer` and typed arrays; no transfer list | No other serializable platform object exists here |
| D18 | UI Events | `KeyboardEvent` has `code`, `location`, `keyCode` | Only `key`, `repeat` and the four modifier flags | The others describe the viewer's hardware and layout and identify a viewer |
| D19 | Pointer Events | Pressure, size, tilt, screen and client coordinates | Only the fields of section 4.2 | Positions are given in the page's own units and nothing else of the device |
| D20 | WS | `permessage-deflate` may be negotiated | Never offered | A decompressor of server-chosen input in the fetcher for no need; the standard makes extensions optional |
| D21 | WS | No limit on a message | A message is at most `MAX_WS_MESSAGE_BYTES`; a longer one closes the socket with code 1009 | Bounded input |
| D22 | HTML | `EventSource` and `WebSocket` have no count limit in the standard (browsers have their own) | At most `MAX_EVENT_STREAMS` and `MAX_SOCKETS` a container, `MAX_SOCKET_OPENS_PER_STEP` opened a step; beyond that the object fires `error` and closes | The review's lead: rate limits, not only concurrency limits |
| D23 | HTML | Scripts may be modules and may `import()` | Classic scripts only | One file, one fetch, one manifest read before run (section 3.1) |
| D24 | ECMA-402 | `Intl` | Absent | quickjs-ng has none; a script formats with its own code |
| D25 | FETCH | `Request.destination`, `Request.referrer` default `"about:client"` resolve against a client document | `destination` is `""`; the default referrer is the script's own address | There is no document |
| D27 | FETCH | A page on plain HTTP may make cross-origin requests | A plain `http:` channel's scripts reach only their own channel (P8) | A network attacker who replaces a plain channel's script must not gain a request cannon or the viewer's cookies elsewhere (DEC-7282 item 3, pending the owner) |
| D26 | HTML | Unhandled errors go to `window.onerror` | To `globalThis` as for a worker (section 4.2), and count as a failure | There is no window |

The standards' editions followed, pinned as rdm sources at integration: the WHATWG living standards as of 22 November 2026 (by commit), RFC 6455, RFC 9110, RFC 9111, RFC 9113, and draft-ietf-httpbis-rfc6265bis in its edition of that date.

---

## 10. The flat host boundary

### 10.1 The one call

The module's shim gives each context's realm one native function, `__host(op, ...ints, payload?)`, which the prelude takes and deletes from the global object before any page code runs. It accepts: the operation, an int; at most `MAX_HOST_INTS` further ints, each checked to be a number that is a finite integer in the signed 32-bit range *without* running script code (no `valueOf`, no `toString`); and at most one payload, which MUST already be a primitive string, a `Uint8Array` or an `Int32Array` (a typed array's bytes are copied once, after its length is checked). It never reads a property of an object, never calls a function and never keeps a reference. It returns an int, a string, a `Uint8Array` or `undefined`, or throws `RangeError`, `TypeError` or `Error`.

Rules every operation obeys (the review's leads):
1. **Bound before copying.** Lengths are checked against the operation's bound and `MAX_HOST_BYTES` before a byte is read from the WebAssembly memory, and a result's length against `MAX_RESULT_BYTES` before a byte is written.
2. **Constant or linear, bounded work,** with the wall clock read as section 3.2 says.
3. **Validate, then change.** An operation that fails changes nothing.
4. **Handles are checked indices.** A handle is an int naming a kind and a slot in a fixed host table of its context; a stale, foreign or forged handle is a `TypeError`. No host pointer exists in the script.
5. **Any trap ends the container for good:** a WebAssembly trap, an import called with a pointer or length outside the linear memory, wasmi's stack limit, the memory cap, or an internal error of the host. The process exits and is not restarted for that page until the viewer reloads.
6. **Rate before work.** Every operation that causes a request, an event stream, a socket, a sound operation, a navigation, a repaint, a log line or a colour change is counted for the callback, the step and the second (10.5) before it does anything, and the count is never given back: a request that is started and aborted has still been counted (the review made 1,240 requests in one step by fetching and aborting).
7. **Host memory is bounded as the script's is.** The container's 64 MiB cap covers only the WebAssembly memory. Every byte the host holds for a container outside it (tables, staged output, the `Validator`'s copy, network buffers, the log, the shared store) is counted against a named bound for its table and against `MAX_HOST_STATE_BYTES` for the container, and one step's output against `MAX_BATCH_BYTES`; a call that would pass any of them throws `RangeError` and changes nothing. The review made the spike's host hold 130 MB and emit one 160 MB frame from 2,048 ReGIS drawings of 63 KiB each. The process also runs under an operating-system limit on its memory, `SCRIPT_PROCESS_MEMORY_BYTES`, so that a counting fault ends the process rather than the machine's memory.

The numbers of 10.2 to 10.4 are defined once, in Rust (`native/script/src/ops.rs`), and written in front of the prelude, so the two halves cannot disagree. A number is never reused; a change is a new API version.

### 10.2 Operations

"p:" names the payload. A handle argument is written `h`.

| # | Name | Ints | p: | Result | Bound or note |
|---|---|---|---|---|---|
| 1 | LOG | level 0 to 4 | text | | `MAX_LOG_CHARS`, `MAX_LOG_LINES` |
| 2 | NOW | | | tick (low 31 bits; high by 2,1) | |
| 3 | INFO | field | | text or int | the fields of `nt.page`, `nt.channel`, `nt.level`, `nt.version` |
| 4 | TIMER | ticks, repeat | | id | `MAX_TIMERS`, `MAX_TIMER_TICKS` |
| 5 | CANCEL | id | | | |
| 6 | BUDGET | | | JSON text the host writes | |
| 7 | KEY_STATE | which (0 down, 1 pressed) | key name | 0 or 1 | `MAX_KEY_NAME_BYTES` |
| 8 | POINTER_STATE | | | text `x,y,buttons,inside,h` | |
| 9 | TITLE | | text | | `MAX_TITLE_BYTES` |
| 10 | NAVIGATE | | target | | `MAX_URL_BYTES`, `MAX_NAVIGATIONS_PER_SECOND` |
| 11 | SCOPE_BEGIN | | | scope | `MAX_SCOPE_DEPTH`, `MAX_SCOPES` |
| 12 | SCOPE_LEAVE | scope | | | stops assigning new things to it |
| 13 | SCOPE_END | scope | | | removes everything in it |
| 14 | SHARED_GET | | key | text or undefined | |
| 15 | SHARED_SET | key length | key then JSON | | `MAX_SHARED_*` |
| 16 | SHARED_DELETE | | key | | |
| 17 | SHARED_KEYS | | | JSON text | |
| 18 | RANDOM | count | | bytes | at most 65,536, the standard's quota |
| 19 | CLOCK | | | text: milliseconds since the epoch, to the tick | |
| 20 | ZONE | | | minutes east of UTC | |
| 21 | LISTEN | h, event kind, on | | | tells the host a thing has a listener: watches `painted`, asks for `pointermove` |
| 30 | SOUND_PLAY | sound, voice, gain | | | `MAX_SOUND_OPERATIONS_*` |
| 31 | SOUND_STOP | voice | | | |
| 32 | SYNTH_START | part, family, variant, gain | | | |
| 33 | SYNTH_MIDI | part, status, data1, data2 | | | status 0x80, 0x90, 0xB0, 0xC0, 0xE0 only |
| 34 | SYNTH_NOTE | part, note, velocity, ticks | | | `MAX_NOTE_TICKS` |
| 35 | SYNTH_STOP | part | | | |
| 40 | URL_PARSE | | input, NUL, base | text: the serialised URL and its component offsets, or undefined | `MAX_URL_BYTES` |
| 41 | FETCH | flags (kind: fetch or event stream; mode, credentials, cache, redirect, referrer policy, keepalive, body follows), head length | UTF-8: method, NUL, URL, NUL, referrer, NUL, integrity, NUL, header lines; then the first body bytes | request id | D8's bounds |
| 42 | FETCH_BODY | id, last | bytes | | `MAX_REQUEST_BODY_BYTES` |
| 43 | FETCH_ABORT | id | | | |
| 44 | FETCH_CREDIT | id, bytes | | | opens the response window |
| 45 | WS_OPEN | | URL, NUL, protocols | socket id | `MAX_SOCKETS`, `MAX_SOCKET_OPENS_PER_STEP` |
| 46 | WS_SEND | id, binary, last | bytes | | `MAX_WS_MESSAGE_BYTES`, `MAX_WS_BUFFERED_BYTES` |
| 47 | WS_CLOSE | id, code | reason | | reason at most 123 bytes |
| 49 | DECODE | encoding index, flags (fatal, ignore BOM, stream), decoder id | bytes | text | the encodings of ENC |
| 60 | UI_CREATE | kind, row, column, columns, rows | options as strict JSON | h | `MAX_COMPONENTS`, `MAX_UI_OPTION_BYTES`, `MAX_UI_ITEMS` |
| 61 | UI_SET | h | options as strict JSON | | |
| 62 | UI_REMOVE | h | | | |
| 63 | UI_FOCUS | h | | | |
| 64 | UI_KEYS | kind | | JSON text | |
| 65 | UI_VALUE | h | | JSON text | |
| 100 | TT_PUT | row, column, ink, paper, height, flags, language | text | cells written | |
| 101 | TT_CODES | row, column | bytes | | |
| 102 | TT_BLIT | | 920 bytes | | |
| 103 | TT_AT | row, column | | code | |
| 104 | TT_CLEAR | first, last | | | |
| 105 | TT_SCROLL | first, last, rows | | | |
| 106 | TT_SETTINGS | screen, row colour, substitution (−1 leaves) | | | |
| 107 | TT_OVERLAY_PUT | row, column, ink, paper, flags, language | text | | `LOCAL_TRIPLETS` |
| 108 | TT_OVERLAY_FILL | row, column, rows, columns, ink, paper | | | |
| 109 | TT_OVERLAY_CLEAR | row, column, rows, columns (0 rows: all) | | | |
| 110 | TT_COLOUR_DEFINE | rgb12 | name | entry | |
| 111 | TT_COLOUR_SET | entry, rgb12 | | | `MAX_COLOUR_SETS_PER_SECOND` |
| 112 | TT_SPRITE | columns, rows, frames, layer, order, row, column, flags | cells, four bytes each: kind, code, ink, paper | h | `MAX_SPRITES`, `MAX_OBJECT_FRAMES`, `OBJECT_BODY_TRIPLETS` |
| 113 | TT_LABEL | h | text | | `MAX_LABEL_BYTES` |
| 114 | TT_ANIMATE | h, operation, a, b, c, d | | | the `ANIMATE` codes 5, 6, 7, 15 to 19 |
| 115 | TT_REMOVE | h | | | sprite or control |
| 116 | TT_CONTROL | row, column, columns, joined | | h | `MAX_CONTROLS` |
| 117 | TT_MEASURE | language | text | cells | |
| 118 | TT_LANGUAGES | | | JSON text | |
| 119 | TT_LEVEL | | | 10, 15, 25 or 35 | |
| 130 | BM_ROWS | first, last | | | |
| 131 | BM_CLEAR | colour | | | |
| 132 | BM_SET | x, y, colour | | | |
| 133 | BM_GET | x, y | | colour | |
| 134 | BM_LINE | x0, y0, x1, y1, colour | | | |
| 135 | BM_RECT | x, y, width, height, colour, fill | | | |
| 136 | BM_BLIT | x, y, width, height, transparent | bytes | | width × height bytes exactly |
| 137 | BM_TEXT | row, column, ink, paper | text | | |
| 138 | BM_PRESENT | | | cells + 65,536 × lossy | |
| 200 | RG_COLOUR_DEFINE | h, l, s | name | entry | |
| 201 | RG_COLOUR_SET | entry, h, l, s | | | |
| 202 | RG_DRAWING | parent, source, layer, x, y, depth, paint rate (−1 unset), flags | | h | `REGIS_MAX_DRAWINGS` |
| 203 | RG_SET | h, property, value | | | properties of 10.4 |
| 204 | RG_CLIP | h, on, x, y, width, height | | | |
| 205 | RG_FRAMES | h | Int32Array of handles | | `MAX_OBJECT_FRAMES` |
| 206 | RG_LABEL | h | text | | |
| 207 | RG_DEFINE | h | painter program | | `MAX_PAINTER_WORDS`, `REGIS_MAX_CONTENTS_BYTES` |
| 208 | RG_REMOVE | h | | | |
| 209 | RG_CLEAR | | | | |
| 210 | RG_ANIMATE | h, operation, a, b, c, d | | | `MAX_ANIMATED_DRAWINGS`, `MAX_CYCLING_OBJECTS` |
| 211 | RG_MACROGRAPH | existing or 0 | painter program | h | 26; `MAX_MACROGRAPH_BYTES` |
| 212 | RG_MEASURE | size, cell w, cell h, height, tilt, language | text | width + 65,536 × height | |
| 213 | RG_BOUNDS | h | | text `x,y,w,h` or undefined | from the last step's report |
| 300 | NP_COLOUR_DEFINE | rgb24 | name | entry | |
| 301 | NP_COLOUR_SET | entry, rgb24 | | | |
| 302 | NP_BLINK | entry, to, on, off, delay | | | `MAX_BLINKS` |
| 303 | NP_PAINT | | painter program | | `NAPLPS_MAX_BYTES_PER_CALLBACK`, `_PER_SECOND` |
| 304 | NP_REPAINT | | painter program | | `NAPLPS_REPAINT_TICKS` |
| 305 | NP_SYMBOL | existing or 0, width, height | painter program | h | `DEFINABLE_CODES`, `MAX_MACRO_BYTES`, `MAX_ALL_MACRO_BYTES` |
| 306 | NP_DRCS | | painter program | h | `DEFINABLE_CODES` |
| 307 | NP_TEXTURE | width, height | painter program | h | `TEXTURE_MASKS` |
| 308 | NP_ACTOR | existing or 0, kind, x, y, width, height, origin x, origin y, layer, order, flags, cover, hover, pressed, alternative | Int32Array of frame handles | h | `MAX_OBJECTS`, `MAX_OBJECT_FRAMES` |
| 309 | NP_LABEL | h | text | | |
| 310 | NP_ANIMATE | h, operation, a, b, c, d | | | |
| 311 | NP_REMOVE | h | | | |
| 312 | NP_MEASURE | width, height, spacing, language | text | width + 65,536 × height | |

A **painter program** is an `Int32Array` of at most `MAX_PAINTER_WORDS`: each call is its number then its ints; a string is its length then its code points; a nested function (`fill`) is its number, its length in words, and its body. The two painters have separate number tables (`RegisPaint`, `NaplpsPaint`), one entry for each row of the tables in 6.3 and 7.3, in that order from 1. The host checks every word, encodes with its own writer, and refuses the whole program on the first fault.

### 10.3 Events given to a context

The shim's entry `nt_event(context, kind, a, b, c, d, payload)` returns an int whose bit 0 is "the default was cancelled". At most one string or byte payload, as for a call.

| # | Kind | a, b, c, d | payload |
|---|---|---|---|
| 1 | TICK | tick, missed | |
| 2 | KEY_DOWN | modifiers and repeat | key name |
| 3 | KEY_UP | modifiers and lost | key name |
| 4 | TEXT | | the text |
| 5 | POINTER | action, button and type packed; x; y; h | Int32Array: pointer id, buttons, local x, local y, then the other handles |
| 6 | WHEEL | delta x, delta y, h | |
| 7 | FOCUS | | |
| 8 | BLUR | | |
| 9 | VISIBILITY | hidden | |
| 10 | TIMER | id | |
| 11 | NAVIGATE | cause | destination |
| 12 | PAGE_SHOW | page, sub-code, renderer | the page's address |
| 13 | PAGE_HIDE | page, sub-code | |
| 14 | CLOSE | | |
| 15 | SHARED | | key |
| 16 | PAINTED | h | |
| 17 | CYCLE_END | h | |
| 18 | SOUND_CUE | voice, cue | |
| 19 | SOUND_ENDED | voice | |
| 20 | FAULT | code | bound name |
| 21 | UI | h, what | value as JSON |
| 30 | FETCH_HEAD | id, status, flags | final URL, NUL, status text, NUL, header lines |
| 31 | FETCH_CHUNK | id | bytes |
| 32 | FETCH_END | id | |
| 33 | FETCH_FAILED | id, kind (network, abort, timeout) | |
| 34 | FETCH_SENT | id, bytes | |
| 35 | WS_OPENED | id | protocol |
| 36 | WS_MESSAGE | id, binary, last | bytes |
| 37 | WS_CLOSED | id, code, clean | reason |
| 38 | WS_SENT | id, bytes | |
| 39 | SSE_OPENED | id | |
| 40 | SSE_EVENT | id, type length, id length | type, last event id, data |
| 41 | SSE_RETRYING | id | |

### 10.4 Properties

`X 1, Y 2, VISIBLE 3, DEPTH 4, LAYER 5, PARENT 6, SOURCE 7, DETECTABLE 8, PAINT_RATE 9, HOVER 10, PRESSED 11, ALTERNATIVE 12, WHEEL 13, TRACK 14`. Frame, cycle, order and forced look are animation operations, not properties.

### 10.5 Rates

Held by the host, which throws or defers at the call so the author is told, and held again by the decoder or the fetcher, which is the authority, since a host that has been subverted cannot be relied on to count.

| Bound | What it holds | Past it |
|---|---|---|
| `MAX_REQUESTS_PER_STEP`, `MAX_REQUESTS_PER_SECOND` | Requests started (`fetch`, `EventSource` connections and reconnections), aborted or not | queued, then `TypeError` (D8) |
| `MAX_EVENT_STREAM_OPENS_PER_STEP`, `MAX_EVENT_STREAMS` | `EventSource` opens | `error` and close (D22) |
| `MAX_SOCKET_OPENS_PER_STEP`, `MAX_SOCKET_OPENS_PER_MINUTE` | `WebSocket` opens | `error` and close (D22) |
| `MAX_SOUND_OPERATIONS_PER_CALLBACK`, `MAX_SOUND_OPERATIONS_PER_STEP`, `MAX_SOUND_OPERATIONS_PER_SECOND` | Plays, stops, notes, MIDI | `RangeError` |
| `MAX_BATCH_BYTES` a step; `MAX_SCRIPT_OUTPUT_BYTES_PER_SECOND` for a channel's tab, held by the decoder | Renderer output of every kind | `RangeError` at the call; the decoder stops the script past the second bound |
| `MAX_NAVIGATIONS_PER_SECOND` | `nt.navigate` | `RangeError` |
| `MAX_COLOUR_SETS_PER_SECOND` | Redefinitions of one colour entry, in every renderer: a whole picture can change colour for a few bytes, and more than three flashes a second is unsafe for viewers (RPT section 10.2 finding 8) | the latest value is applied at the next tick the rate allows; nothing throws |
| `NAPLPS_REPAINT_TICKS`, `NAPLPS_MAX_BYTES_PER_SECOND` | New generations and appended bytes | `RangeError` |
| `MAX_LOG_LINES` a step | Log lines | counted and dropped |
| One commit or frame a step | Renderer output | by construction |

### 10.6 The bounds

Values marked * are starting values to be confirmed by measurement in the build and changed only here.

| Name | Value | Source |
|---|---|---|
| `MAX_SCRIPT_BYTES` | 1,048,576 | SPIKE |
| `MAX_MANIFEST_BYTES` | 4,096 * | this document |
| `WASM_MEMORY_BYTES`, `QUICKJS_HEAP_BYTES`, `QUICKJS_STACK_BYTES`, `WASM_MAX_RECURSION`, `FUEL_SLICE` | 64 MiB, 48 MiB, 768 KiB, 16,384, 1,000,000,000 | DEC-7256 (one container holds both contexts) |
| `START_TIME_LIMIT`, `CALLBACK_TIME_LIMIT`, `STEP_TIME_BUDGET`, `SECOND_TIME_BUDGET`, `CLOSE_TIME_LIMIT`, `WATCHDOG_GRACE`, `STEP_DEADLINE` | 1 s, 50 ms, 12 ms *, 500 ms *, 50 ms *, 10 ms *, 250 ms * | DEC-7256; TODO-7267; this document |
| `HOST_COPY_CHECK_BYTES` | 65,536 * | the review's lead |
| `MAX_CONSECUTIVE_FAILURES` | 16 * | this document |
| `MAX_HOST_INTS`, `MAX_HOST_BYTES`, `MAX_RESULT_BYTES` | 23, 262,144, 1,048,576 | SPIKE |
| `TICKS_PER_SECOND`, `MAX_TICK_DIVISOR`, `MAX_TIMERS`, `MAX_TIMER_TICKS` | 60, 60, 32, 216,000 | AN ANIM-1; SPIKE |
| `MAX_QUEUED_EVENTS`, `MAX_EVENTS_PER_TICK`, `MAX_KEYS_DOWN`, `MAX_POINTER_OBJECTS` | 64, 16, 16, 16 | `neoteletext-rules/src/limits.rs` |
| `MAX_KEY_ASKS`, `MAX_KEY_NAME_BYTES` | 128, 32 | the browser's `protocol/src/rules.rs`; SPIKE |
| `MAX_NETWORK_EVENTS_PER_STEP`, `MAX_POINTERS`, `MAX_TEXT_EVENT_BYTES` | 32 *, 4 *, 4,096 | this document; the browser's input-stream item |
| `MAX_SCOPE_DEPTH`, `MAX_SCOPES` | 8 *, 64 * | this document |
| `MAX_SHARED_KEYS`, `MAX_SHARED_KEY_BYTES`, `MAX_SHARED_VALUE_BYTES`, `MAX_SHARED_BYTES` | 64 *, 64, 16,384 *, 65,536 * | this document |
| `MAX_LOG_LINES`, `MAX_LOG_CHARS` | 64, 400 | SPIKE |
| `MAX_TITLE_BYTES`, `MAX_LABEL_BYTES` | 64, 64 | the renderers' limits |
| `MAX_NAVIGATIONS_PER_SECOND` | 2 * | this document |
| `AUDIO_CHANNELS`, `MAX_LOCAL_SOUNDS`, `MAX_SOUND_NUMBER` | 4, 2, 255 | `neoteletext-audio` |
| `MAX_SOUND_OPERATIONS_PER_CALLBACK`, `_PER_STEP`, `_PER_SECOND`, `MAX_NOTE_TICKS` | 64, 64, 256 *, 600 | SPIKE; this document |
| `MAX_SCRIPT_HOSTS`, `MAX_SCRIPT_MEMORY_BYTES` (browser-wide) | 64 (`MAX_TABS`), 536,870,912 * | DEC-7282 item 8; this document |
| `MAX_BATCH_BYTES`, `MAX_SCRIPT_OUTPUT_BYTES_PER_SECOND`, `MAX_HOST_STATE_BYTES`, `SCRIPT_PROCESS_MEMORY_BYTES` | 262,144 (the engine's `MAX_FRAME_BYTES`), 1,048,576 *, 8,388,608 *, 134,217,728 * | TODO-7267; this document |
| Host state by table: teletext (plane, overlay, sprites, controls, bitmap buffers) fixed; `REGIS_MAX_TOTAL_CONTENTS_BYTES` and the drawings table; NAPLPS macros `MAX_ALL_MACRO_BYTES` and the cast; components `MAX_UI_STATE_BYTES`; network buffers `MAX_NETWORK_BUFFER_BYTES` | fixed; 1,048,576 * and 2,048 records; 65,536 and 64 records; 262,144 *; 4,194,304 (the fetcher's `MAX_ROOM`) | this document |
| `MAX_COLOUR_SETS_PER_SECOND` | 6 (three flashes) | RPT 10.2 finding 8 |
| `LOCAL_TRIPLETS`, `OBJECT_BODY_TRIPLETS`, `OBJECT_INVOCATIONS_PER_TYPE`, `MAX_SPRITES`, `MAX_OBJECT_FRAMES`, `MAX_CONTROLS`, `MAX_CYCLING_OBJECTS` | 208, 507, 127, 32, 16, 32, 16 | TC, by name |
| `TELETEXT_DEFINABLE_COLOURS`, `BITMAP_WIDTH`, `BITMAP_HEIGHT`, `MAX_TEXT_CHARS`, `MAX_POINTS`, `MAX_PAINTER_WORDS` | 16, 80, 69, 1,024, 1,024, 65,536 | EN; DEC-7245; SPIKE |
| `REGIS_COLOURS`, `MAX_DRAWING_DEPTH`, `MAX_PAINT_RATE`, `MAX_ANIMATED_DRAWINGS`, `MAX_WATCHED_PAINTINGS`, `MAX_MACROGRAPH_BYTES`, `MAX_FILL_VERTICES`, `MAX_STRING_BYTES`, `MAX_PATTERN_MULTIPLIER` | 16, 16, 32,767, 64, 32, 16,384, 4,096, 1,024, 16 | RL, by name |
| `REGIS_MAX_DRAWINGS`, `REGIS_MAX_CONTENTS_BYTES`, `REGIS_MAX_TOTAL_CONTENTS_BYTES`, `MAX_TRACKED_DRAWINGS` | 2,048, 65,536, 1,048,576 *, 64 * | SPIKE; this document: far below the renderer's own caps so that one page cannot hold the renderer's whole memory |
| `MAX_BLINKS`, `DEFINABLE_CODES`, `MAX_MACRO_BYTES`, `MAX_ALL_MACRO_BYTES`, `TEXTURE_MASKS`, `MAX_OBJECTS`, `MAX_OBJECT_BYTES`, `MAX_VERTICES`, `WAIT_BUDGET_TICKS` | 32, 96, 4,096, 65,536, 4, 64, 16,384, 4,096, 3,600 | NL, by name |
| `NAPLPS_REPAINT_TICKS`, `NAPLPS_MAX_BYTES_PER_CALLBACK`, `NAPLPS_MAX_BYTES_PER_SECOND`, `NAPLPS_MAX_IMAGE_PELS` | 30, 65,536, 262,144 *, 16,384 * | SPIKE; this document |
| `CHANNEL_SHARE_SPRITES`, `CHANNEL_SHARE_DRAWINGS`, `CHANNEL_SHARE_ACTORS`, `CHANNEL_SHARE_SYMBOLS` | 4 *, 64 *, 8 *, 16 * | this document |
| `MAX_COMPONENTS`, `MAX_UI_ITEMS`, `MAX_UI_OPTION_BYTES`, `MAX_UI_ID_BYTES` | 64 *, 256 *, 16,384 *, 64 | this document |
| `MAX_URL_BYTES`, `MAX_METHOD_BYTES`, `MAX_REQUEST_HEADERS`, `MAX_RESPONSE_HEADERS`, `MAX_HEADER_NAME_BYTES`, `MAX_HEADER_VALUE_BYTES`, `MAX_HEADER_BYTES`, `MAX_STATUS_TEXT_BYTES`, `MAX_INTEGRITY_BYTES` | 8,000, 40, 64, 128, 128, 8,192, 65,536, 128, 512 | the fetcher session's `native/protocol/src/web.rs` as it stood on 22 November 2026 (`MAX_URL`, `MAX_METHOD` and the rest), adopted here by these names |
| `MAX_REQUEST_BODY_BYTES`, `MAX_RESPONSE_BUFFER_BYTES`, `FETCH_WINDOW_BYTES`, `MAX_NETWORK_BUFFER_BYTES`, `MAX_CHUNK_BYTES`, `MAX_DECOMPRESSED_RATIO` | 16,777,216, 8,388,608 *, 262,144, 4,194,304, 65,536, 100 * | the fetcher's `MAX_REQUEST_BODY`, `INITIAL_ROOM`, `MAX_ROOM`, `MAX_BODY_PIECE`; this document |
| `MAX_EVENT_TYPE_BYTES`, `MAX_EVENT_ID_BYTES`, `MAX_EVENT_DATA_BYTES`, `MAX_EVENT_STREAM_OPENS_PER_STEP`, `MAX_WEB_CLIENTS`, `MAX_JAR_BYTES`, `MAX_SUBPROTOCOL_BYTES` | 256, 1,024, 131,072, 2 *, 64 (`MAX_TABS`), 4,194,304, 128 | the fetcher's `web.rs`; this document |
| `MAX_REQUESTS_IN_FLIGHT`, `MAX_REQUESTS_QUEUED`, `MAX_REQUESTS_PER_STEP`, `MAX_REQUESTS_PER_SECOND`, `REQUEST_SECONDS`, `KEEPALIVE_SECONDS` | 8 *, 32 *, 8 *, 32 *, 30 for the head with no limit on a stream that keeps arriving, 30 | this document |
| `MAX_EVENT_STREAMS`, `MAX_SOCKETS`, `MAX_SOCKET_OPENS_PER_STEP`, `MAX_SOCKET_OPENS_PER_MINUTE`, `MAX_WS_MESSAGE_BYTES`, `MAX_WS_BUFFERED_BYTES`, `MAX_WS_PROTOCOLS` | 4 *, 4 *, 2 *, 16 *, 1,048,576 *, 1,048,576 *, 8 | this document |

---

## 11. Processes and messages

### 11.1 The processes

Scripts run in a confined process of their own, the same on every platform (DEC-7266). A prepared parent (a zygote) is not built; it remains possible later behind the same interface.

- **The program** is `neoteletext-script-host`: it links the library `neoteletext-script` (the container, the host, the encoders, the prelude, the messages) and nothing of the decoder, the renderers' drawing code, the network or the interface. The encoders need the engine's text encoder, the renderers' `Validator`s and limits, and the picture converter; they do not need a renderer that draws.
- **Its role** is a new `Role::Script` in the browser's `confine` crate, with exactly the decoder's confinement on each platform (its pipes only: no network, no files, no process creation, the same system-call filter), kept as a role of its own so that the two can diverge only by a recorded decision.
- **Who starts it.** The broker, at the trusted core's request, as it starts every helper: one for each (tab, channel) that has a script, when the decoder reports that a script is to run. It is ended when its tab leaves the channel, and killed if it does not answer a STEP within `STEP_DEADLINE` or its queue passes the core's bound.
- **Its pipes** are its standard input and output, to the trusted core, as every helper's. **The trusted core relays** between it and the decoder, and between it and the channel's fetcher, by the frame's kind and length alone: it never reads a payload of these messages, as it never reads a page's bytes. The core adds the tab number on the fetcher's side, as it does today, and it relays the network kinds only for a context the decoder reported with `network: true` and only while `ChannelPolicy::network_allowed()` holds.
- **One interface.** In the library the split is one trait:

```rust
/// What runs a (tab, channel)'s scripts. The browser's implementation speaks the
/// messages of 11.2 to a script-host process; the runner's calls the library in
/// its own process. Nothing else differs between them.
pub trait ScriptLink {
    fn open(&mut self, context: ContextOpen, source: &[u8]) -> Result<(), LinkError>;
    fn step(&mut self, step: Step) -> Result<Batch, LinkError>;
    fn close(&mut self, context: ContextId);
    fn network(&mut self, event: FromFetcher) ;      // an answer for the script
    fn take_requests(&mut self) -> Vec<ToFetcher>;   // what the script asked of the network
}
```

### 11.2 Script host and decoder

Framing is the browser's own (`native/protocol/src/framing.rs`): a kind byte, a big-endian u32 length, at most `MAX_PAYLOAD` (256 KiB) of payload, parsed strictly, each side accepting only its own kinds. Integers are big-endian; a string or byte field is a u32 length then the bytes; a list is a u16 count then the items; every count and length has the bound named. A frame that breaks a bound, has bytes left over, or names an unknown kind ends the link: the decoder treats the script as stopped. Each message below has an encoder, a decoder and a fuzz target in `native/protocol/src/script.rs` and `native/fuzz`.

**Decoder to script host**

| Kind | Fields |
|---|---|
| HELLO | `link_version: u16` |
| CONTEXT_OPEN | `context: u8` (1 channel, 2 page); `api: u16`; `renderer: u8`; `level: u8`; `page: u16`; `subcode: u16`; `flags: u8` (pointer press, pointer move, wheel, text, network, from disk); `tick_divisor: u8`; `language` ≤ 16; `channel_url`, `page_url`, `script_url` each ≤ `MAX_URL_BYTES`; `channel_title` ≤ 64; `seed: [u8; 32]`; `epoch_seconds: u64`; `zone_minutes: i16`; `keys`: ≤ `MAX_KEY_ASKS` names; `sounds`: ≤ 255 handles; `source_bytes: u32` ≤ `MAX_SCRIPT_BYTES` |
| SOURCE | `context`; `offset: u32`; `bytes` ≤ 131,072. The context starts when `offset + length = source_bytes` |
| STEP | `sequence: u32`; `tick: u64`; `missed: u16`; `flags: u8` (a tick, pausing, resumed, closing); `events`: ≤ `MAX_EVENTS_PER_TICK + MAX_KEYS_DOWN`, each a kind of 10.3 numbered 1 to 21 with its four ints and a payload ≤ 4,096; `painted`: ≤ 32 handles; `cycle_ended`: ≤ 16 handles; `bounds`: ≤ `MAX_TRACKED_DRAWINGS` of (handle, x, y, width, height); `sound`: ≤ 8 cues or ends; `faults`: ≤ 8 |
| CONTEXT_CLOSE | `context` |
| SHUTDOWN | none |

**Script host to decoder**

| Kind | Fields |
|---|---|
| READY | `link_version: u16`; `api_max: u16` |
| BATCH | `sequence: u32`; then sections, each a tag byte, a u32 length and a body, each at most once and in this order; the whole at most `MAX_BATCH_BYTES`, so a batch is always one frame: |
| section VERDICTS | one byte for each event of the STEP: bit 0 default cancelled, bit 1 handled by a listener |
| section TELETEXT_ROWS | ≤ 23 of (`row: u8` 1 to 23, 40 seven-bit codes) |
| section TELETEXT_ENHANCEMENT | the open page's local enhancement data, whole: ≤ `LOCAL_TRIPLETS` triplets of (address, mode, data), which the decoder checks and orders |
| section TELETEXT_SETTINGS | default screen colour, default row colour, substitution flag, and ≤ 16 of (entry 16 to 31, 12-bit colour) |
| section TELETEXT_OBJECTS | ≤ `MAX_SPRITES × MAX_OBJECT_FRAMES` of (object number, ≤ `OBJECT_BODY_TRIPLETS` triplets): the Passive objects sprites' frames are |
| section SPRITES | ≤ `MAX_SPRITES`, each the fields of the engine's `SPRITES` record for one sprite (number, flags, layer, order, column, row, width, height, ≤ 16 object numbers), with no page or sub-code field |
| section ANIMATE | ≤ `MAX_ANIMATE_OPERATIONS` (64) of (code 5, 6, 7 or 15 to 19, target kind and number, operands), with no page or sub-code field |
| section REGIS | ≤ `MAX_BATCH_BYTES` of ReGIS text to append to the open page's one stream |
| section NAPLPS | `new_generation: bool`, then ≤ `MAX_BATCH_BYTES` of NAPLPS bytes to append |
| section NAPLPS_OBJECTS | `one: bool`, a title ≤ 64, and ≤ `MAX_OBJECTS` objects, each the per-object fields of the engine's `NAPLPS_OBJECTS` record |
| section SOUND | ≤ `MAX_SOUND_OPERATIONS_PER_STEP` of: play (voice, sound, gain), stop (voice), synth start (part, family, variant, gain), MIDI (part, status, data 1, data 2), synth stop (part) |
| section WATCH | the painted watch list (≤ 32), the tracked drawings (≤ 64), the wheel things (≤ 16): each sent whole when it changed |
| section LABELS | ≤ 128 of (handle, label ≤ 64) for things whose record carries no label (teletext sprites and controls) |
| section TITLE | ≤ 64 bytes |
| section NAVIGATE | target ≤ `MAX_URL_BYTES` |
| section LOG | ≤ 64 lines of ≤ 400 characters, each with a level and a context |
| section STATE | for each context: running or stopped with a reason code; `failures: u16`; and `next_due: u64`, the tick of the earliest timer, so that the decoder wakes for it and never polls |
| FAILED | `context`; `reason: u8` (time, memory, stack, trap, failures, link); `text` ≤ 400 |

**A script's output never takes the channel's stream path** (the security review's finding, TODO-7267 item 6). The batch holds only the typed drawing commands above, for the page and sub-page that are open and for nothing else: no section names a page, and none can carry an arbitrary record or packet. The decoder builds the packets and records itself (FRAME 27 begin and end around the step, the rows, X/26, X/28, the object page, SPRITES 24, ANIMATE 23, REGIS 14, NAPLPS 17, NAPLPS_OBJECTS 25, CONTROL 3, LOCAL_MIDI 28) and gives them to the engine as the open page's. A script process that has been subverted therefore cannot send a SCRIPT_REF, REDIRECT, LINKS, RULES, INDEX, SUBPAGES, DENIED, LOG or state record, cannot write a row 0 or 24, and cannot touch another page of the channel's store. The ReGIS and NAPLPS sections are still that renderer's language, which the decoder's renderers read as they read a channel's (bounded, fuzzed), so a subverted script process gains nothing a hostile server lacks. As a second line the decoder SHOULD hold both sections to the host encoder's subset before feeding them, with a small validator of its own that is fuzzed: for ReGIS, no macrograph definition outside the forms the host writes, no screen, load or report command, and `D` operations only in the shapes of section 6; for NAPLPS, only the opcodes of section 7.3 and 7.4 and the designations the host uses (work package D1). The decoder holds the rates of 10.5 and the bounds of 10.6 again, as the authority.

The decoder, for its part: reads manifests (it is the process that parses outside input); reports each context's claims to the trusted core in its existing key-ask message, extended to say that a script holds them and whether it has the network; makes STEPs on its own presentation clock and for input between ticks; turns a BATCH into the open page's packets and records and applies them inside one frame; tells the trusted core each event's verdict so that defaults are taken or not; and maps what the pointer hit to the host's handle (a ReGIS drawing's handle is its number; sprites, controls and actors by the numbers the host's records gave them).

### 11.3 Scripts and the web client

The messages are the fetcher session's own (`native/protocol/src/web.rs`, `ToWebClient` and `FromWebClient`, as they stood uncommitted on the browser's branch `reqresp-fetcher` on 22 November 2026), adopted here by their names with the changes marked **(change)**, which work package W1 makes. The framing is the browser's. The trusted core relays them between the script host and the partition's web-client process, adding the tab number on the web client's side.

**What the process knows and from whom.** The web-client process is started for one partition and is told it once, by the trusted core, at its start: the channel identity, the window jar, and the saved cookie jar (`JarKept`). **(change)** `Start` no longer carries a jar and a channel for the process to select by: it carries the partition's token, a 16-byte value the trusted core gave the process at its start and adds to each relayed `Start` itself, and **a `Start` whose token is not the process's own ends the process at once**, as a fetcher's wrong tab does today. A script host never sees the token. `ForgetJar` forgets the process's one jar. The process is confined as a fetcher is (`Role::Network`).

Every field is hostile input to the web client, which checks each against its bound and against `ChannelPolicy` before acting; the script host checks everything arriving as hostile too.

**To the web client**

| Message | Fields |
|---|---|
| `Start` | `id: u32`, unique for the container's life; `context` (channel or page); `kind` (fetch, event stream, socket); `method` ≤ `MAX_METHOD_BYTES`, an RFC 9110 token, never `CONNECT`, `TRACE` or `TRACK`; `url` ≤ `MAX_URL_BYTES`, as the host's parser serialised it, `http:` or `https:`, or `ws:` or `wss:` for a socket; `referrer` (none, the client's default, or an address); `referrer_policy`; `mode` (same-origin, cors); `credentials` (omit, same-origin, include); `cache` (the six modes); `redirect` (follow, error, manual); `integrity` ≤ `MAX_INTEGRITY_BYTES`; `keepalive`; `headers`: ≤ `MAX_REQUEST_HEADERS` of (name ≤ `MAX_HEADER_NAME_BYTES`, value ≤ `MAX_HEADER_VALUE_BYTES`), ≤ `MAX_HEADER_BYTES` in all, forbidden request-header names removed by the prelude and removed again by the web client; `body` (none, bytes of a stated length ≤ `MAX_REQUEST_BODY_BYTES`, or a stream, which version 1's host never sends: D7); for a socket, `protocols`: ≤ `MAX_WS_PROTOCOLS` tokens of ≤ `MAX_SUBPROTOCOL_BYTES`; for an event stream, the last event identifier ≤ `MAX_EVENT_ID_BYTES` |
| `RequestBody` | `id`; bytes ≤ `MAX_CHUNK_BYTES` |
| `RequestBodyEnd` | `id` |
| `Abort` | `id` |
| `More` | `id`; `bytes: u32`: the script consumed this much; the room never exceeds `MAX_NETWORK_BUFFER_BYTES` |
| `SocketSend` | `id`; binary or text; last; bytes ≤ `MAX_CHUNK_BYTES`; a whole message ≤ `MAX_WS_MESSAGE_BYTES` |
| `SocketClose` | `id`; `code: u16`; `reason` ≤ 123 bytes |
| `TabCloses` | the tab: cancel everything of it but keepalive requests. **(change)** also `ContextCloses { context }`, for a page context that ends while its tab stays |

**From the web client**

| Message | Fields |
|---|---|
| `Head` | `id`; `status: u16`; response type (basic, cors, opaque-redirect); `redirected`; `url` ≤ `MAX_URL_BYTES`, the final address; `status_text` ≤ `MAX_STATUS_TEXT_BYTES`; `headers`: ≤ `MAX_RESPONSE_HEADERS`, ≤ `MAX_HEADER_BYTES`, already filtered: for a cors response only the CORS-safelisted names and those the server exposed; never `Set-Cookie` |
| `Body` | `id`; bytes ≤ `MAX_CHUNK_BYTES`, sent only within the room the script has given (`FETCH_WINDOW_BYTES` at first) |
| `End` | `id` |
| `Failed` | `id`; `kind` (network, aborted, timed out) and a `reason` code for the developer log, which the host never gives the script |
| `Opened` | `id`: an event stream or a socket is open; a socket's `protocol` ≤ `MAX_SUBPROTOCOL_BYTES` |
| `Event` | `id`; `type` ≤ `MAX_EVENT_TYPE_BYTES`; `last_event_id` ≤ `MAX_EVENT_ID_BYTES`; `data` ≤ `MAX_EVENT_DATA_BYTES` |
| `Retrying` | `id`: the event stream was lost and is being reconnected (the object's `error` event with `readyState` connecting) |
| `SocketMessage` | `id`; binary or text; last; bytes ≤ `MAX_CHUNK_BYTES` |
| `SocketClosed` | `id`; `code`; clean; `reason` ≤ 123 |
| **(change)** `Sent` | `id`; `bytes: u32`: request body or socket bytes written, for `bufferedAmount` and upload flow |
| `Jar` | to the trusted core only, never relayed to a script host: the partition's jar as it changed, ≤ `MAX_JAR_BYTES` |

The web client holds the authoritative rates of 10.5 and D8 for each container (requests and event-stream and socket opens for each step and second, counted whether or not they are aborted; `MAX_REQUESTS_IN_FLIGHT` at a time). A page's own files and a channel's scripts are fetched as today's page files are, by the trusted core's typed requests (section 12.5), not by these messages.

### 11.4 Fuzz targets the build must have

The security review's list (its analysis, section 6), each attached to the work package that creates what it tests, with two this document adds. Each replays its corpus first and runs in the full gate; the gates check that each exists.

| # | Target | Tests | Work package |
|---|---|---|---|
| 1 | `script_host_ops` | Every host operation with arbitrary ints and payloads, interleaved with steps and input; no panic, host state within `MAX_HOST_STATE_BYTES`, a batch within `MAX_BATCH_BYTES` | F2, extended by T1 to N2 and U1 |
| 2 | `script_imports` | Each import (`nt.call`, `clock_time_get`, `fd_write`, the `fd_*` stubs) with arbitrary pointers and lengths over an arbitrary memory image; bounded time and memory, a trap and never a panic | F2 |
| 3 | `script_js` | Arbitrary JavaScript run under the limits; stopped within each limit's margin, process memory bounded | F2 |
| 4 | `script_manifest` | The manifest reader | F4 |
| 5 | `script_link_to_host`, `script_link_to_decoder` | The message readers of 11.2 | F1 |
| 6 | `script_batch_apply` | An arbitrary BATCH applied by the decoder; only the open page and sub-page change, no channel record is produced, rows 0 and 24 untouched | F4 |
| 7 | `regis_batch_subset`, `naplps_batch_subset` | The decoder's subset validators | D1 |
| 8 | `web_to_client`, `web_from_client` | The messages of 11.3, both ways | F1 |
| 9 | `channel_policy_relation` | `ChannelPolicy::relation` against an oracle that decodes as servers do; nothing outside the folder is `InChannel` | W1 |
| 10 | `cookie_set_cookie` | `Set-Cookie` and the jar's invariants (prefixes, public suffixes, limits, SameSite) | W1 |
| 11 | `cookie_jar_kept` | The jar bytes the trusted core hands back | W1 |
| 12 | `cors_response` | `Access-Control-*` headers, preflight, response filtering | W1 |
| 13 | `integrity_metadata` | The integrity parser | W1 |
| 14 | `content_coding` | gzip, deflate and brotli with bounded room | W1 |
| 15 | `sse_stream` | The event-stream parser | W1 |
| 16 | `websocket_frames` | WebSocket framing | W1 |
| 17 | `web_client_hostile_server` | Arbitrary HTTP/1.1 and HTTP/2 answers, end to end | W1 |
| 18 | `channel_file_scripts` | The `scripts` member, the TTI `JS` line, the `SCRIPT_REF` record | C1 |
| 19 | `bitmap_present` | An arbitrary sixel bitmap and previous frame through the converter | T3 |
| 20 | `script_url_resolve` | The host's URL operation (40) | W2 |
| 21 | `referrer_policy` | The referrer computation | W1 |
| 22 | `painter_programs` | Arbitrary painter programs for ReGIS and for NAPLPS | R2, N1 |
| 23 | `ui_options` | Arbitrary bytes to the component options reader | U1 |

---

## 12. The channel file, page files and their scripts

### 12.1 The channel file is `channel.ttx`

The channel file of DEC-7254 is the channel's existing entry file, `channel.ttx` (the engine's REQ-508 and REQ-513; DEC-594 item 7), which every channel is already opened by: least machinery, one file, one strict reader (`Descriptor::parse_channel`). It gains one member. A channel without the file, or without the member, has no scripts. A live channel (one whose file has the member `push`) runs no script: its `scripts` member is ignored and the fact logged, so that the push system's report gate and rule tables never meet page code (DEC-7282 item 10).

```json
{
  "name": "Harbour",
  "initial_page": "100",
  "scripts": {
    "channel": "channel.js",
    "pages": { "101": "101.js", "110": "boat.js", "1A0/0002": "tides-2.js" }
  }
}
```

| Member | Type and bounds |
|---|---|
| `scripts` | object with the members `channel` and `pages`, each optional; any other member refuses the file, as everywhere in it |
| `scripts.channel` | a script name (12.2): the channel-level script |
| `scripts.pages` | object of at most `MAX_SCRIPT_PAGES` (800, the contents file's page bound) entries. A key is a page, `NNN`, or a page and sub-page, `NNN/SSSS`, in the spelling of the channel's file names (hexadecimal, capitals; REQ-508, DEC-2116). A value is a script name |

**Keys are exact; nothing is inherited** (DEC-6599: a sub-page is exactly a page). `"1A0"` names the script of page 1A0 shown with no sub-code; `"1A0/0002"` names the script of that sub-page and of no other. A sub-page with no entry of its own has no page-level script, whatever its page has.

To hold 800 entries the engine's bound on a channel file, `DEFAULT_DESCRIPTOR_LIMIT`, is raised from 16 KiB to 64 KiB for `channel.ttx`.

### 12.2 Script names and files

A script name is a file name: 1 to 64 characters of `A` to `Z`, `a` to `z`, `0` to `9`, `-` and `_`, then `.js`. It names a file in the channel's own folder, for a sub-page's script too: there is one place a script can be. It is never an address, never has a folder, a query or a fragment, and so can never leave the channel's folder: P5 holds by construction, and a folder inside a channel, which is a different channel (DEC-594 item 1), is never reached. `*.js` in that form is added to the fixed file names of REQ-508.

A script file MUST be served with a JavaScript media type (the MIME Sniffing standard's list: `text/javascript`, `application/javascript` and their legacy aliases); any other type is refused, and the content is never sniffed. It is fetched with the channel's credentials, cached under the channel's partition by RFC 9111 like any file, and revalidated when its page is opened. Version 1 keeps no bytecode or compiled-code cache: a cache written by an untrusted process and read back as code is a way for one run to subvert the next.

### 12.3 A page with a script, and a JavaScript page

- A page that has a page file and a script: the page file is shown first, exactly as with no script (principle 5), and the script then starts with the page's renderer.
- A page that has a script and no page file (`NNN.tti` and `NNN.t42` both absent) is a **JavaScript page** (DEC-7246 item 2): it opens blank in the renderer its manifest names. `contents.txt` lists it as any page.

### 12.4 A page file that names its script (DEC-7255)

**TTI.** A new page-level line, `JS,<script name>`, between a `PN` line and the next: it names the script of that sub-page. The code `JS` is used by none of the lines the engine reads (file level `PN`, `DE`, `DS`, `CT`, `LG`; page level `SC`, `PS`, `OL`, `FL`, `LN`, `LK`, `LT`, `RE`, `PF`, `CK`, `CU`; withdrawn `TF`, `IM`; `neoteletext-formats/src/tti/commands.rs`). At most one for each `PN`; a second, or a name that breaks 12.2, is reported and the line ignored. The engine's reader reports and ignores an unknown code; that other tools that read TTI files do the same is to be checked against them (section 18).

**T42.** A new channel record, `SCRIPT_REF`, **type 37**, carried in packets 4/31 like every channel record (version 2 frame, CRC-32). Types 1 to 35 are in use on the engine's working branch (35 is PAINT; 8 is retired; 13 is reserved); 36 was the two spikes' SCRIPT record on unmerged branches and is left unassigned so that no build of theirs misreads a new file. Body: `page: u16`, `subcode: u16`, `reserved: u8` (0), `name_length: u8` (4 to 67), the script name. One for each page and sub-page; a later one for the same page replaces the earlier. A reader that does not know the type skips the record, as the engine's does for every unknown type. The record also serves ReGIS and NAPLPS pages, which travel as records inside `NNN.t42`.

### 12.5 How scripts are loaded

1. The fetcher's agent reads `channel.ttx` as today. When the trusted core asks for a page, the fetcher also fetches the script `scripts.pages` names for it, and the channel-level script with the channel's first page, and gives each to the trusted core as a new typed message (`FromFetcher::Script { level, page, subcode, name, bytes }`), which the core passes to the decoder unread.
2. The decoder, reading a page file, finds a `JS` line or a `SCRIPT_REF` record and asks for that script by a new typed message that carries the script name only (`FromDecoder::ScriptWanted { page, subcode, name }` to the core; `ToFetcher::FetchScript { page, subcode, name }`). The fetcher takes a name of 12.2's form, never an address (the browser's REQ-2948 is kept in that sense), and resolves it in the channel's folder.
3. The decoder reads the manifest, reports the claims, and has the script host started.

### 12.6 When both name a script for one page

The page file's own reference is used, because it is the more specific and travels with the page (DEC-7258's proposal). The channel file's entry for that page is then not fetched for it, and the decoder logs the difference for the channel's developer. Only one page-level script ever runs for a page. The owner is asked to confirm (section 18, question 2).

### 12.7 A file opened from disk

Today the broker reads a T42 or TTI file the viewer chose and the trusted core passes it to a decoder with no rights; each file is its own channel with no fetcher (DEC-1762). With DEC-7255 such a file may name a script. This is a question for the owner (section 18, question 1). **The recommendation,** which `ChannelPolicy` P6 encodes until the owner rules:

1. The named script is loaded only from the same folder as the page file, by the broker, under the same grant as the page file (no folder grant wider than the page file's), and only when it is a script name of 12.2's form; the read is bounded by `MAX_SCRIPT_BYTES` and refuses a symbolic or hard link. A script carried whole inside a file (the spikes' SCRIPT record) is refused.
2. It runs with an opaque origin, no cookie jar and **no network**: `fetch`, `EventSource` and `WebSocket` fail as a manifest with `network: false` does. Drawing, input (the keys its manifest claims), sound and synthesizers work.
3. `nt.navigate` works to pages of the same file or folder and, to a channel on the network, only on the viewer's activation and through the trusted core's usual prompt for a link out of a file.

**The alternative the security review proposes** (DEC-7282 item 1): the script does not run until the viewer chooses, and the trusted strip says the file has a script. Rules 1 to 3 hold under either. Both are put to the owner.

The reason for no network: a file a viewer was sent and opened is the least trusted way a page can arrive, a local page with the network could carry what it sees to any server that answers CORS, and nothing a local page legitimately does (a game, a demonstration, a page being authored) needs the network; an author testing network code uses the runner or a local web server.

---

## 13. What a host does that the API does not show

For the code sessions, the points the earlier sections imply:

1. **Two realms, one runtime.** The shim creates a context for each level, runs the prelude in each, and never passes a value of one to the other. Ending a page context frees its realm and runs the collector.
2. **Things belong to a context and a scope.** Every table entry records its context and scope; ending either removes its entries and stages their removal in the renderer.
3. **ReGIS bytes are fed and forgotten.** The decoder feeds a batch's REGIS records to the page's `regis::Terminal` and keeps none of them; there is one stream generation for the life of the page context and no restart. The host keeps each drawing's attributes and the byte count of its contents, and its `Validator` keeps what the renderer keeps.
4. **NAPLPS generations.** A page context's backdrop is one generation until `repaint`. A new generation is a new `naplps::Terminal` in the decoder, so the host sends the colour map, definitions and cast again.
5. **Teletext frames.** The host keeps the 23 by 40 plane, the overlay table, the sprite and control tables and the 16 colours, and writes each step's changes as packets between FRAME records.
6. **Paused** means the decoder sends no STEP; on resume the first STEP carries `resumed` and the tick continues from where it stopped.
7. **The seed.** The trusted core draws 32 bytes for each context from the operating system. The host derives two independent values from it with a key-derivation function under distinct labels (HKDF-SHA-256 from `ring`): the state of `Math.random`, and the key of a cryptographic generator (ChaCha20) for `crypto.getRandomValues` and `crypto.randomUUID`. QuickJS's `Math.random` is a small generator whose state a script can recover from a few outputs, so nothing else may depend on it. No two contexts share a seed. The runner's command-line seed exists only in the runner; D15's determinism is `Math.random`'s alone, and in the runner the cryptographic generator is keyed from the same command-line seed only so that runs repeat.

---

## 14. What changes in today's requirements

The build contradicts or outgrows the requirements below. None is revised by this document or by the build's branches; each is revised in rdm at integration (work package Q1), on the owner's word, with DEC-7246, DEC-7262 and the decision named as its reason. "Engine" is neoteletext-renderer-teletext; "common" is neoteletext-common.

| Requirement | Says today | Proposed new wording, in one line |
|---|---|---|
| REQ-417 (engine REQ-SEC-004) | No received content is executed; only the owner's recorded decision may add scripting | Received content is never executed, with two exceptions: a page's rule table, and a channel's JavaScript run in QuickJS compiled to WebAssembly in a confined process with only the capabilities its host gives (DEC-7246, DEC-7266); HTML, plugins and every other interpreter stay forbidden |
| REQ-661 (browser 1.3) | No code from a page, channel, server or file is executed; no interpreter reachable from outside data | The browser executes outside code only as a channel's JavaScript, in the script-host process alone, in QuickJS inside the WebAssembly interpreter wasmi; no other program of the browser holds an interpreter reachable from outside data |
| REQ-668 (browser 3.2) | The gate fails if any program's tree holds a script engine or interpreter | The gate fails if any program's tree but the script host's holds one, and the script host's holds exactly wasmi and the pinned QuickJS module |
| REQ-667 (browser 3.1) | The closed list of processes | Adds one script-host process for each (tab, channel) that runs a script, and one web-client process for each partition (which may be the channel's fetcher) |
| REQ-4848, REQ-714 with REQ-667 | "One decoder per channel" against "each tab its own decoder" | State one rule: each tab has its own decoder and its own script host for the channel it shows |
| REQ-2946 | The fetcher takes only a closed list of messages, each for a file of its own channel named by numbers | The closed list gains `FetchScript` (a script name of the fixed form) and the web-client messages of the script API's section 11.3, each typed and bounded; anything else is refused |
| REQ-2948 | The fetcher takes no address from the trusted core | Kept for page loads; a script's request carries an address, relayed unread by the trusted core from the script host, and is held by `ChannelPolicy` |
| REQ-689 (5.1), REQ-2668, REQ-678 (3.12) | Fetches are only a channel's own resources; a fetcher's requests reach only its own channel's server | A partition's process makes its channel's page loads and its scripts' requests; a script's request may reach another origin under CORS as the Fetch standard and `ChannelPolicy` allow; no process serves two partitions |
| REQ-717 (7.7) | No request carries a credential or identifier to another origin; no cookie is sent | A request carries only its own channel's jar; to another origin or another channel's folder only under `credentials: "include"` and the server's CORS permission, and then only cookies that server set in this channel's jar |
| REQ-702 (5.14) | A fixed `User-Agent` on every request, resting on the cancelled REQ-503 | The browser's own page loads send the fixed, non-identifying header set; a script's request sends the same `User-Agent` unless the script sets one, as the Fetch standard allows |
| REQ-699 (5.11), REQ-3391; engine REQ-424 | Compressed responses are refused; `Accept-Encoding: identity` | The web client accepts `gzip`, `deflate` and `br`, with the decompressed size bounded by `MAX_DECOMPRESSED_RATIO` and the body bounds; the engine's own minimal client keeps `identity` |
| REQ-889 (21.11), REQ-879 (21.1) | No `Cookie` sent; no `Set-Cookie` acted on; a fetcher holds no cookie | In the request/response system cookies follow RFC 6265bis with the listed departures, one jar for each partition, held by that partition's process and kept by the trusted core; the push system keeps no cookie while it exists |
| REQ-3698 | No HTTP/2 push or server-sent events | Server-sent events are supported for scripts by `EventSource`; HTTP/2 server push stays unsupported |
| REQ-490 (engine REQ-WEB-001) | The web module holds HTTP/1.1 and keeps no cookies | Scoped to the engine's own minimal client (its tools and small devices); the browser's web client is the fetcher's, on hyper with HTTP/1.1 and HTTP/2 |
| REQ-501 (engine REQ-WEB-012), REQ-3669, REQ-4670, REQ-426 | Page servers rely on no cookie; no receiver sends one | True of the push system and of the engine's own client; a request/response channel's server may use standard cookies (DEC-7250) |
| REQ-508 (engine REQ-WEB-019), REQ-1884 (common), REQ-1693 | A channel's files have a closed list of names | The list gains `NAME.js`: a script named by the channel file or by a page file, in the channel's folder |
| REQ-513 (engine REQ-WEB-024), REQ-1894 (common), DOC-1865 | `channel.ttx`'s members; unknown members refuse the file; 16 KiB | Adds the member `scripts` (`channel`, `pages`); the file's bound becomes 64 KiB; unknown members still refuse it |
| REQ-3253 (engine) | Any other media type is refused | Adds: a script file is accepted only with a JavaScript media type and is never sniffed |
| REQ-3783 (engine) | The push WebSocket is a channel's only live connection | A channel's scripts may also hold event streams and WebSockets within their named bounds |
| REQ-5329 (engine) | No web-specific content such as a script reaches the decoder | A script's bytes reach the decoder only to have their manifest read and to be passed to the script host; the decoder never runs them |
| REQ-1337 (common) | Fetches use HTTP/1.1 | Scoped to the push system; the web client uses HTTP/1.1 and HTTP/2 |
| REQ-3984 (common) | A WebSocket upgrade carrying `Origin` is answered 403 | Scoped to the push WebSocket at `<channel>push`; a channel's own WebSocket endpoints for scripts receive `Origin` as the standard sends it and decide by it |
| REQ-419 (engine) | The local-network refusal names descriptors, pages and push connections | Widened to every request a script causes and every redirect of one (`ChannelPolicy` P7) |
| REQ-7037 (browser), DEC-7157 | A named key is the page's and no key goes both ways | For a script's page a claimed key goes to the script first and then takes its default action unless a handler cancelled it; no "any key" claim exists for scripts |
| DOC-1794 (common) | Only a live channel can take a viewer's keys | A static channel's page takes the keys, text and pointer its script's manifest claims |
| REQ-712, REQ-1883, REQ-515 | The channel identity is the unit of isolation | Unchanged, and now cited as the reason for departures D1 to D4 |
| REQ-2196 | Teletext DRCS is banned; "no form of bitmap graphics" in its reason | The ban stands; its reason is reworded so that the sixel bitmap of DEC-7245, which is mosaic characters, is plainly not what it forbids |
| REQ-6774 (PAR-42) | Every component renders from one tree to all three renderers | DEC-7205's rule: one vocabulary, each component implemented for its renderer (already decided; revised with the component requirements) |
| REQ-1474 | The server keeps no channel content | Unchanged: DEC-7208's third exception (view state in the server) is withdrawn by DEC-7246, since component state is the client's |
| DOC-2302 | The cancelled minimal profile: GET only, no cookies, no scripting, no cross-origin | Replaced by the web client profile TODO-7251 writes |
| DEVELOPMENT.md sections 7 and 14 | The licence list; "no script engine, web engine or interpreter in the browser (its requirement 1.3)" | Names Unicode-3.0 as accepted for the `url` crate's data (DEC-7261); section 14 says what REQ-661 now says |
| The engine's `records.rs` module comment | "PAINT (34)" | PAINT is 35; 36 is unassigned (the spikes'); 37 is SCRIPT_REF |

New requirements are written at integration from sections 2 to 12 of this document, one for each numbered rule, each linked from the decision that made it.

---

## 15. The build plan

Each work package is one code session's work (architecture and code by Fable sessions; every test, measurement and review by Opus sessions, DEC-7021), is an rdm to-do, and is built in rapid iteration on a branch beside the present system (DEC-7262 item 2). Nothing merges to a working branch for release before the security review is done (DEC-7262 item 3). Branch `reqresp` in each repository unless another is named; the browser's script work is on `reqresp-script`, cut from `livedevelopment`, taking the spike's crate `native/script` from `spike-qjs` as its starting point, and the web client's on `reqresp-fetcher`.

| Id | Repository and branch | Builds | Depends on | Tested by |
|---|---|---|---|---|
| F1 | browser, `reqresp-script` | The messages of sections 11.2 and 11.3 in `native/protocol`: types, encoders, strict decoders, bounds, a fuzz target for each direction | none | Round-trip and refusal tests; fuzzing |
| F2 | browser, `reqresp-script` | The library `neoteletext-script`'s core: the container with two contexts, the flat boundary's rules 1 to 7, operations 1 to 21 and 30 to 35, events, the prelude's `EventTarget`, timers and standard globals, the time budget with the watchdog, host memory accounting, per-step rates | none | Unit tests; the review's three overrun cases as regression tests; a fuzz target over the host call |
| F3 | browser, `reqresp-script` | The program `neoteletext-script-host`, `Role::Script` on Linux, macOS and Windows, started by the broker for the trusted core; the core's relay by kind | F1, F2 | Confinement tests on each platform; a kill test for an unanswered step |
| F4 | browser, `reqresp-script` | The decoder's side: manifest reader, contexts' lifecycle, STEPs on its clock, BATCH turned into the open page's packets and records, the authoritative rates, picking to handles, painted and bounds reports | F1, F3, C1 | A fuzz target over BATCH application; lifecycle tests |
| F5 | browser, `reqresp-script` | The trusted core and interface: key claims from manifests, default actions and verdicts, input for static channels' script pages, `navigate`, the stopped indication, the badge | F4 | Key-routing tests; the never-claimable keys |
| T1 | browser, `reqresp-script` | Teletext: page plane, overlay, Colour Map, settings, controls, text through the engine's encoder, languages | F2 | Golden pictures in the runner |
| T2 | browser, `reqresp-script` | Teletext sprites: blocks compiled to Passive objects on the host's object page, the sprite list, animation operations, labels | T1 | Golden pictures; triplet budget tests |
| T3 | engine `reqresp`; browser `reqresp-script` | The sixel bitmap: the indexed-raster entry point and colour rule in `neoteletext-picture`, frame differences; the host's buffers and `present` | T1 | The colour rule's cases; a timed full-page animation |
| R1 | browser, `reqresp-script` | ReGIS: drawings and their fourteen attributes, commit with the `Validator`, colours, animation operations, the painted report, tracked bounds, picking | F2 | Golden pictures; each `CommitError` refused at the host |
| R2 | browser, `reqresp-script` | The ReGIS painter in full, macrographs, text in the provided sets, measuring | R1 | Encoder tests against the renderer; golden pictures |
| N1 | browser, `reqresp-script` | The NAPLPS painter in full (absolute and relative forms, textures, text and the 55 sets), the backdrop, the colour map and BLINK, WAIT, repaint | F2 | Encoder tests against the renderer; golden pictures |
| N2 | browser, `reqresp-script` | NAPLPS definitions (symbols in relative forms, DRCS, textures) and the cast (objects, regions, `ONE`, animation operations), picking | N1 | Golden pictures; the 64-object and macro bounds |
| U1 | browser, `reqresp-script` | `nt.ui`: the vocabulary, options reader, focus, events with defaults; the thirteen kinds on teletext | T1, T2 | Golden pictures; event tests |
| U2 | browser, `reqresp-script` | The thirteen kinds on ReGIS | U1, R2 | the same |
| U3 | browser, `reqresp-script` | The thirteen kinds on NAPLPS | U1, N2 | the same |
| W1 | browser, `reqresp-fetcher` (in progress) | The web client: hyper, h2, tokio; one process for each partition; `ChannelPolicy`; CORS, redirects, referrer, cache, integrity, the local-network refusal; cookies by the cookie crates; event streams; WebSockets; the messages of 11.3 with the marked changes | F1 for the final message set | TODO-7265's five tests; a fuzz target over `relation`; a local test server |
| W2 | browser, `reqresp-script` | The script-side web APIs in the prelude over operations 40 to 49, with the streams polyfill bundled and pinned | F2 | The spike's 23 checks, extended; a mock web client |
| W3 | browser, `reqresp-script` | The web-platform-tests harness for fetch, URL, encoding, streams, cookies and WebSockets, run in the runner; the per-case expectations that are the published departures | W1, W2, H1 | It is itself the test |
| C1 | engine, `reqresp` | `channel.ttx`'s `scripts` member and bound; the `NAME.js` file name and media type check; the TTI `JS` line; the `SCRIPT_REF` record, type 37; the agent's fetch of scripts | none | Reader tests; fuzz targets extended |
| C2 | browser, `reqresp-script` | Loading: the pin moved to C1; `FromFetcher::Script`, `ScriptWanted`, `FetchScript`; the page file's reference winning; a file from disk as section 12.7 | C1, F4 | End-to-end tests against a static channel |
| H1 | browser, `reqresp-script` | The standalone runner (section 16) | F2; grows with T1 to N2, W2 | Its own golden runs |
| X1 | neoteletext-server-channel-scriptdemo, `reqresp` | The example channel: this document's six worked examples, a channel-level script, a component page for each renderer, a fetch, event-stream and WebSocket page | C2, U3, W2 | The runner's golden runs in the gates; the browser on Xvfb |
| D1 | browser, `reqresp-script`; naplps renderer `reqresp` | The decoder's authoritative limits measured and set: a per-second NAPLPS work budget, the colour-change rate, output bytes a second, and the starred bounds of 10.6 confirmed by measurement | F4, N2, R2 | Timed tests that print their numbers |
| Q1 | common, `reqresp` | Integration: the requirements of section 14 revised and the new ones written in rdm, the documentation items, the security review's findings closed, this document carried into rdm and deleted | everything; the owner's word | The linking phase; every reference resolves |

**Order.** Wave 1, in parallel from the start: F1, F2, C1, and W1 (running). Wave 2, in parallel once F2 stands: F3, T1, R1, N1, W2, H1. Wave 3: F4, T2, T3, R2, N2, then F5 and C2. Wave 4: U1, then U2 and U3 in parallel; W3; D1. Wave 5: X1, then Q1. The renderer packages (T, R, N) never touch one another's files and run in parallel throughout; they are testable in the runner before F3 to F5 exist, because the runner needs only the library.

**F1 comes first for the web client's sake.** The session on `reqresp-fetcher` has a message set already; F1 fixes section 11.3's marked changes with it on the first day, so that W1 and W2 build to one set.

---

## 16. The standalone runner

`neoteletext-script-run` is a first-class deliverable (the owner's question of 22 November 2026: can JavaScript drive the renderers standalone, for testing): for the project's gates and for channel authors. It links the same library, `neoteletext-script`, as the browser's script host, behind the same `ScriptLink` trait, so that a script's behaviour cannot differ between them; and it draws with the decoder's own engine and the sound helper's own mixer, so that a picture is what the browser would show.

| It does | How |
|---|---|
| Runs a channel folder, one page of it, or one script | `run CHANNEL_OR_FILE --page NNN[/SSSS]`; the channel file and page files are read by the engine's own readers |
| Steps time deterministically | No real clock: `--ticks N` steps N ticks as fast as they run; `--pace` runs them on the wall clock for watching. The seed is `--seed`, fixed by default, so two runs are identical (D15) |
| Injects every event of section 4.2 | A script of input, `--input FILE`: lines of `TICK kind fields` for keys, text, pointer (mouse, touch and pen, with pointer ids), wheel, focus, visibility, navigation and close. Recorded from a browser session by its developer view, in the same form |
| Answers the network | `--network none` (every request fails), `--network mock FILE` (a table of request to answer, with body pieces and event-stream and socket messages placed on ticks), `--network replay FILE` (a recording made by `--network record FILE`), or `--network live` through the real web client against a local server it starts from `--serve DIR`. Mock and replay are deterministic and need no socket |
| Snapshots pictures and sound | `--png-every N` and `--png-at TICK,…` write PNG files from the decoder's snapshot of the page's renderer; `--wav FILE` writes the mixer's output |
| Compares with kept results | `--expect DIR` compares every snapshot, the WAV, the log and the budget with the files kept there and fails on any difference; `--bless` writes them. A kept set carries a format version in `expect.json`; a change to pixels raises it and regenerates the set in the same commit (DEVELOPMENT.md section 8) |
| Reports | The budget (`nt.budget()` at the end and its maxima), time for each step (median, ninth decile, worst), bytes of output for each renderer, requests made, events dropped, as text and with `--report FILE` as JSON |
| Tells a caller the result | Exit status 0: ran and matched. 1: a snapshot, log or budget differed. 2: the script was stopped (limit, trap, failures). 3: the script or manifest was refused. 4: bad arguments or files. Usable in continuous integration and in the local gates |
| Reloads | `--watch` restarts the page when its file changes; the runner only |

It reads untrusted scripts like the browser does and so confines itself the same way unless `--network live` is given, which needs the network role.

---

## 17. Choices this document made

Recorded in rdm as one decision that waits for the owner's confirmation. Each was low-stakes or forced by a decision already made; the alternatives are named where there was a real one.

1. **Version 1 has no raw-bytes escape** for ReGIS or NAPLPS (DEC-7247 item 6 left it open). Alternative: raw contents of one drawing or one macro, which needs a framing check neither renderer offers.
2. **The manifest is a leading comment in the script file,** `/*! nt {json} */`, read before run. Alternatives: in the channel file (but a script named by a page file has no channel file entry); a first call in code (code can change its mind).
3. **Two realms in one container,** a channel context and a page context, sharing only `nt.shared`. DEC-7258 proposed one realm with scopes; two realms keep a sub-page exactly a page and cost about 0.3 MB.
4. **Events are DOM events** (`addEventListener`, `preventDefault`), with W3C names, replacing the spike's `nt.onKey` and "return true". Timers are the standard `setTimeout` family; the spike's `nt.after` and `nt.every` are dropped.
5. **A claimed key takes its default unless cancelled** (section 4.6), which amends REQ-7037 for script pages.
6. **A handler's changes before it threw are kept,** as on the web; RPT section 8.1 proposed discarding them.
7. **The channel context draws only in the overlay layer,** with a reserved share of each table.
8. **No `nt.report` and no value events:** under request/response a script tells its server things with `fetch`.
9. **The channel file is `channel.ttx` with a `scripts` member; keys are exact with no inheritance; script names are file names in the channel's folder,** not addresses.
10. **`JS,<name>` for TTI and record type 37, `SCRIPT_REF`, for T42,** leaving 36 unassigned; the page file's reference wins over the channel file's.
11. **The batch is typed drawing commands for the open page only,** which the decoder turns into packets and records (the security review's finding); the encoders for ReGIS and NAPLPS text run in the script host.
12. **The trusted core relays script messages by kind and length without reading them,** rather than a direct pipe between confined processes.
13. **`EventSource` is parsed in the web client,** as the fetcher session built it, rather than in the container over a streaming fetch.
14. **Components are Rust in the script host,** with no layout engine in version 1 and a first set of thirteen.
15. **The sixel bitmap is 80 by 69 over the whole width,** with the colour rule of section 5.7, in place of the spike's 76 by 69 with two reserved columns.
16. **The time budgets and every starred bound of section 10.6.**
17. **Departures D5, D7 to D26.** D1 to D4 and D6 follow decisions already made.

---

## 18. Questions for the owner, and what is not settled

**Questions only the owner can answer** (each an rdm to-do for the owner):

1. **A file opened from disk:** may it run the script it names, and with what? This document recommends: yes, from its own folder, with no network and an opaque origin. The security review proposes instead that it not run until the viewer chooses (DEC-7282 item 1). Section 12.7 gives both.
2. **When the channel file and a page file both name a script for one page:** confirm that the page file's wins (section 12.6).
3. **DEC-7268, one web-client process for each partition:** specified here as the safe form; it needs the owner's ruling, and it costs one process for each channel partition that uses the network.
4. **`mode: "no-cors"` refused (D5), and local-network requests refused (D6):** confirm both departures; they are the two that remove something a web page can do.
5. **The wording of the trusted strip** while a script holds keys (with and without the network), and when a page's program has stopped.
7. **Scripts of a channel served over plain HTTP:** whether their requests are held to the channel itself (P8, the security review's DEC-7282 item 3), which this document specifies pending the ruling.
6. **Whether a channel-level script may cancel navigation** that a page's own link or key caused (section 4.2 allows it; the browser's own controls are never cancellable).

**Not settled by this document:**

- **Sounds of a JavaScript page with no page file:** `nt.sound.play` plays sounds announced by records in a page file or `index.t42`; a script-only page has synthesizers but no way to bring a sampled sound of its own. A sound file format and its fetch are a design of their own.
- **The page number of the host's teletext object page,** against the engine's reserved numbers (work package T2).
- **Whether other tools that read TTI files ignore an unknown `JS` line,** and whether other T42 readers ignore packets 4/31 they do not know: to be checked against the tools themselves (C1).
- **Measurements not made:** a commit a tick on a ReGIS scene of thousands of drawings; the cost of a bitmap `present` at Level 2.5 with X/26 colours; NAPLPS work a second under the byte caps (D1); the memory of one web-client process for each partition; every starred bound.
- **The web client's HTTP cache:** whether version 1 ships one (RFC 9111, partitioned) or treats every script request as `no-store` at first, with `only-if-cached` failing; W1 decides and the departure list records it if so.
- **Where the browser shows a script's log and budget** to a channel's developer.
- **macOS and Windows confinement of `Role::Script`** is specified as the decoder's; that the container runs unchanged under each is unverified until F3.
- **ReGIS text measuring and NAPLPS proportional measuring** are computed by the host from cell sizes because neither renderer has a measuring call; adding one to each renderer would make them exact.
- **The trusted indications** (a script holds the keys; a page's program has stopped): the browser's spoofing review (its `docs/security-analysis.md` section 7) must cover both, and full-screen page-only mode must end or show the indication when a script starts holding keys (TODO-7285 item 6; work package F5).
- **Accessibility:** the decoder has no accessibility-tree message today; labels are specified and carried, and what reads them is outside this document.
