# Viewer state: replacing cookies with a per-channel key

| | |
|---|---|
| **Status** | Design document of 18 November 2026, for the owner's review; on approval each numbered requirement becomes an rdm requirement and the proposal decision is confirmed. |
| **Asked for by** | The owner, 18 November 2026: "write it all up as requirements", after the research report on session state and cookies of the same day. |
| **Process** | DEVELOPMENT.md section 2.3 (a proposal, with its own security analysis because it adds an input and an output: section 10 of this document), section 3.5 (every record in full) and section 14 (security). |
| **Legal content** | Section 11 is written for review by a lawyer. It is not legal advice. |
| **Repositories it changes** | neoteletext-renderer-teletext (the engine), neoteletext-browser, neoteletext-app-server, neoteletext-server-ts-protocol (the TypeScript kit), neoteletext-server-ts-ui-components (the component library), neoteletext-server-channels (the Python kit and the old Hackaday channel), and the channels named in section 9. |

---

## 1. Purpose, scope and status

### 1.1 Purpose

A NeoTeletext channel sometimes needs to know that two connections come from the same viewer: a poll that counts one vote per viewer, a page that keeps the choices a viewer made, a channel that shows its pages in the language a viewer chose, and, later, a viewer who signs in. Today that knowledge comes from HTTP cookies, held to stricter rules than the web's (DOC-1924, "Sessions and cookies"). This document replaces cookies entirely with a mechanism designed for NeoTeletext alone: a key pair that the browser makes for one channel when that channel asks for state, and proves possession of by signing a fresh challenge from the channel's server on the channel's own push connection. A channel's program never sees the key; it sees an opaque handle, derived for that channel alone.

The research report of 18 November 2026 (section 16 of this document lists its sources) explains why: thirty years of cookies show that security options nobody is obliged to use protect nobody; the one clean restart the web attempted, HTTP State Tokens, failed only because of an installed base that nobody controlled; and NeoTeletext's browser, server, kits and channels are all under one owner, so a clean restart here costs one migration.

### 1.2 Scope

In scope: every way a NeoTeletext browser, server, kit, component library or channel stores, sends, reads or acts on per-viewer identity, as found in the code on 18 November 2026 (section 1.5); the protocol messages that replace them; the browser's keeping of keys and the viewer's control of them; the server's verification and its derivation of handles; the kits' and the library's programming interface; the clients that are not the desktop browser; the migration; the security analysis; the privacy and legal position.

Out of scope, each with its reason in section 12: keys held in hardware, a login, measures against abuse beyond sign-in, rotation of a key that keeps its continuity, and identity shared between channels.

### 1.3 How this document becomes records

When the owner approves it, the main session records the proposal decision in rdm (in neoteletext-common, with `decides` links to each requirement), creates each requirement numbered `VS-n` here as an rdm requirement in the repository named in its heading (the `VS-n` number becomes its original ID, so that this document's cross-references keep resolving), supersedes the records listed in section 14.7, and creates the to-dos of section 9.3. The open questions of section 13 are answered first, because several requirements carry a value marked *(open question Qn)* that the answer fixes. Until then this document is a proposal and nothing in it is built.

### 1.4 What the owner decided in conversation on 18 November 2026

Every requirement below follows these nine decisions. They are numbered here so that each requirement's Source can name them ("owner's decision 1 of 18 November 2026").

1. **Cookies are removed entirely and replaced.** Nothing a channel writes is stored in or parsed by the browser.
2. **The replacement is a per-channel key pair** made and held by the browser's trusted core, never by the fetcher. It is Ed25519, as the research recommends, unless a reason against it is found in the code, in which case the options are given (section 13, Q1, gives the reason found and the options). It is created only when a channel asks for state. It is proven only by signing a fresh challenge from the server together with the channel's identity, on the channel's own push connection. It is never placed in an address, a redirect, a page or file fetch, or a log.
3. **A channel's program sees only an opaque handle** derived per channel from a hash of the public key: never the key, never a token. Channels cannot relate one another's handles. The server stores only a hash.
4. **Two lifetimes.** A visit key is held in memory and gone when the browser closes. A remembered key is kept, encrypted at rest, only when the viewer chooses "remember me on this channel" in the browser's own interface, with a hard cap of about 400 days (the exact figure is open question Q2). The viewer can forget one channel or all at any time. Private windows have their own keys, thrown away when closed. The channel's only control is to end state (`StateEnd`); it can never set or choose a value.
5. **It behaves identically on encrypted and unencrypted connections.** The owner: "it must work unencrypted because development needs it - even if we flag insecure in the browser", and "it must behave the SAME insecure and secure developers need the same behaviour". The only difference is the browser's insecure badge. There is no separate insecure mechanism, no `secure` flag given to programs, and "remember me" is offered on both. Secure and insecure addresses are different channels anyway, because the channel identity includes the scheme (the browser's requirement 7.1), so they never share a key. The accepted cost on insecure connections (tracking by someone on the network, hijacking of a live connection; replay is still impossible) is stated in the security analysis.
6. **Developer experience.** No cryptography, cookies or parsing in programs. A program receives a `viewer` handle, or none; `requestState()` asks for state; `endState(viewer)` forgets. The library's ballots, kept choices and language key on the handle automatically. Tests use the kits' harness with named fake viewers with fixed handles ("alice in two tabs", "after a reset", "a private window"). `neottx` and tools may keep a test identity in a file. Under DEC-6462 all verification is in the server; the kits are thin and equal, TypeScript and Python.
7. **Legal.** Designed so that NeoTeletext and the demonstration channels need no consent banner: the visit key is strictly necessary for a service the viewer asked for (the exemption of the Article 29 Working Party's Opinion 04/2012, WP 194, as the research reads it), and the remembered key is kept only by the viewer's explicit choice in the browser. A privacy page (transparency and deletion under the General Data Protection Regulation) is still required. Channels are bound by a rule to use the handle only for what the viewer asked for (polls, kept choices, language, sign-in), and the protocol documentation states it. The whole legal section is flagged for review by a lawyer and states that it is not legal advice.
8. **A future login** binds an account to the key's hash on the server. It is not built now.
9. **Abuse and races are not solved by any resettable identity.** Abuse (fresh identities at will) is answered by sign-in where it matters. Races between tabs are answered by atomic updates in the server's and the library's stores; this document specifies what the library and the server must do.

### 1.5 What is replaced: every cookie mechanism found in the code

Found by reading each repository on 18 November 2026 (the engine at `dd0421c6`, the server at `df662b9`, the browser's `livedevelopment`, the TypeScript kit at release 14.0.0, the component library at 22.0.0). Every item here is deleted by this design, in the change that replaces it (DEVELOPMENT.md section 2.1: no compatibility shim).

**The engine, `neoteletext-renderer-teletext`**

| Where | What it is |
|---|---|
| `crates/neoteletext-web/src/cookie.rs`, with `cookie/store.rs`, `cookie/header.rs`, `cookie/date.rs`, `cookie/persist.rs` | The cookie jar (`CookieJar<SLOTS, BYTES>`), RFC 6265bis rules made stricter (decision E.35, REQ-WEB-006, REQ-495, REQ-5156 to REQ-5171), per-channel scope (REQ-515), the `Cookies` trait a port may implement (`cookie.rs` line 166), `wipe`, `clear_site_data`, and the saved format "neoteletext-cookies 3". |
| `crates/neoteletext-web/src/agent/cookies.rs` | `store_response_cookies` (reads `Set-Cookie`, applies `Clear-Site-Data`), `write_cookie_header`, `save_cookies`, `load_cookies`, `wipe_cookies`. |
| `crates/neoteletext-web/src/agent/fetch.rs` lines 212 to 232 | `Set-Cookie` read from page and descriptor fetches. |
| `crates/neoteletext-web/src/agent/push.rs` lines 60 to 100 and 195 to 215 | The `Cookie` header on the push handshake, and `Set-Cookie` read from its 101 response. |
| `crates/neoteletext-web/src/agent/push_data.rs` lines 179 to 196; `crates/neoteletext-web/src/records/cookie.rs` | The SET_COOKIE record, type 8 (DOC-1957), read and stored; `SetCookie::encode`, which the server uses to write it. |
| `crates/neoteletext-web/src/agent/config.rs` lines 43, 44 and 79 | `persist_cookies`, default false (REQ-SEC-013). |
| `crates/neoteletext-web/src/port.rs` line 141 | `CookieStorage`, a port's save and load of cookies. |
| `crates/neoteletext-web/src/dbsc.rs` and submodules, `agent/bound.rs`, `agent/request.rs`, `agent/response.rs` (feature `dbsc`) | Device Bound Session Credentials (REQ-WEB-017, REQ-506, decision E.110, DEC-634), ES256, which bind a cookie session to a device key. Off by default and enabled by no program. |
| `crates/neoteletext-app/src/fetch/web.rs` (`run_web`, `agent_config`) | `neottx`'s live viewing, which keeps cookies for one run in memory. Test `crates/neoteletext-cli/tests/web.rs` line 196, `the_session_cookie_comes_back` (REQ-502). |
| `xtask/src/features.rs` line 62; `xtask/src/size.rs` builds `web-all` | The microcontroller and feature builds compile the `cookies` feature. |

**The browser, `neoteletext-browser`** (all under `native/` unless stated)

| Where | What it is |
|---|---|
| `core/src/cookies.rs` | The jar: one store for ordinary tabs and one for private tabs, each the engine's jar with each channel under a tag `c<n>` (`Store`, `Channel::of`, `Channel::owns`, `header_for`, `store`, `clear_site`, `reached_securely`, `listed`, `delete_channel`, `delete_origin`, `delete_all`, `delete_created`, `block`, `close_private`, `export`, `import`); constants `PER_CHANNEL` 180, `TOTAL` 3,000, `MAX_FILE` 32 MiB. |
| `core/src/cookies/file.rs`; `core/src/private_file.rs` | `cookies.bin`, sealed with ChaCha20-Poly1305 from `ring`, magic line `neoteletext-cookies-sealed 1 chacha20-poly1305`, a fresh 96-bit nonce per write, written 0600 through a temporary file renamed over it. |
| `core/src/broker.rs` lines 46 to 56 and 164 to 180; `confine/src/broker/wire.rs` lines 61 to 63 (`Request::CookieKey`), `confine/src/broker.rs` line 98 (`COOKIE_KEY_BYTES`), `confine/src/broker/client.rs` line 182 | The cookie file's 32-byte key in the platform's secret store under the entry "NeoTeletext cookie file" / "cookies.bin", through `keyring` 4.2.0, made with `ring::rand::SystemRandom`. |
| `core/src/trusted_core/cookies.rs`; `core/src/trusted_core/cookies/panel.rs` | The core's glue: `fetcher_channel`, `cookie_message`, `cookie_reply`, the write debounce, `cookies_at_start`, `open_cookie_file`, `cookies_at_exit`, `cookie_mode_changed`, `private_cookies_closed`, `clear_cookies_since`, the panel's rows by view number. |
| `core/src/trusted_core/run.rs` lines 168 to 182 | `--no-keychain` and `--keychain` (decision 113). |
| `core/src/settings.rs` lines 22 to 29, 78 to 101 and 206 to 266 | Settings lines `cookies keep|close|block` and `cookie-block <channel>`. |
| `fetcher/src/cookies.rs`; `fetcher/src/process.rs` lines 43 to 47 and 495 to 505 | `CoreCookies`, the fetcher's store that asks the core for each request's `Cookie` header and returns each `Set-Cookie` as typed fields (DEC-1765); the agent's own jar held at zero size. |
| `protocol/src/fetcher.rs` lines 269 to 306 and 412 to 425; `protocol/src/fetcher/cookies.rs`; `protocol/src/fetcher/kinds.rs` | Fetcher messages `CookieQuestion` (kind 88), `ReachedQuestion` (89), `CookieSet` (90), `ClearSiteData` (91), `CookieAnswer` (97), `ReachedAnswer` (98). |
| `protocol/src/cookies.rs`; `protocol/src/interface/kinds.rs` lines 90 to 104; `protocol/src/library/history.rs` line 17; `protocol/src/settings.rs` line 47 | Interface messages: the cookies view (kind 57), the cookies request (kind 70), `HistoryRequest::ClearCookies`, `SettingChange::Cookies`. |
| `interface-core/src/browser/cookies_tab.rs`, `interface-core/src/cookies.rs`, `interface-core/src/browser/settings_panel/draw.rs` lines 257 to 271, `settings_panel/input.rs` lines 82 to 84, `console_panel.rs` line 276, `history/draw.rs` line 97, `history/input.rs` lines 118 to 127, `interface-core/src/settings.rs` line 142 | The developer console's Cookies tab, the settings' Keep, Close and Block, "Manage…", and the Cookies switch of clearing with history. |
| `fuzz/fuzz_targets/cookie_file.rs`; `fuzz/regressions/cookie_file/` | The cookie file's fuzz target. |
| `docs/cookies.md`, `docs/cookies-security.md` | The design and security analysis of decision 62 (DEC-955). |

**The server, `neoteletext-app-server`**

| Where | What it is |
|---|---|
| `crates/teletext-runtime/src/session_cookie.rs` (`NAME` `_session`, `first_session`, `signature`, `value`, `set_cookie`, `program_cookies`, `session_of`, `verified`, `same`) | The signed session cookie: `<session>.<expiry>.<HMAC-SHA-256>`, 30 days renewed at each connection, `Path=/<channel>/; HttpOnly; SameSite=Strict`, `Secure` on https (REQ-1040, DOC-1924, DEC-2024 item 4). Session numbers are the start time in milliseconds times 1,024, counted up. |
| `crates/teletext-native/src/http.rs` (`Cookies`, `upgrade`, `session_for` line 297) | The push upgrade reads the `Cookie` header, verifies `_session` under the current and the previous key, always sets `_session` again, and passes the program's own cookies on. |
| `crates/teletext-native/src/state.rs` (`session.key`, `session.key.previous`, `session_keys`, `random_key` reading `/dev/urandom`) | The session key, 32 bytes, 0600. Nothing writes `session.key.previous`; rotation is by hand only. On Windows there is no key, so sessions never continue (TODO-2055). |
| `crates/teletext-runtime/src/protocol.rs` | Program protocol 12 (`PROTOCOL` line 60): `COOKIE_BYTES` 4,096, `MOST_COOKIES` 50; `Connected` carries `session` and `cookies` (line 566); `CookiePair` (595); `Closed { session }`; the program's `Cookie` message (line 2571), checked by `check_cookie` in `protocol/check.rs` line 734. |
| `crates/teletext-runtime/src/channel.rs` (sessions map, `MOST_WAITING_SESSIONS` 65,536 line 196, `SESSION_GRACE_MS` 5 minutes line 184, `opened` line 863, the `cookie` message line 1418); `crates/teletext-runtime/src/records.rs` line 228 | A session waits 5 minutes after its last connection, then the program is told `closed`; a program's `cookie` becomes a SET_COOKIE record (REQ-2963). |
| `crates/teletext-cloudflare/src/lib.rs` (`SESSION_KEY` line 80, `accept_viewer` lines 383 to 401, `welcome` lines 345 to 349) | The Cloudflare host's one session key in Durable Object storage, the `_session` cookie, and an empty cookie list given to `opened` (TODO-4900, DEC-5583). |
| `protocol/schema-12.json`; `fuzz/fuzz_targets/session_cookie.rs`; `crates/teletext-native/tests/lifecycle.rs` (`a_cookie_a_program_sets_reaches_it_on_the_next_connection`, `a_session_continues_with_its_cookie`) | The schema, fuzz target and tests of the above. |

**The TypeScript kit, `neoteletext-server-ts-protocol`, release 14.0.0, protocol 12**

| Where | What it is |
|---|---|
| `src/wire/server-events.ts` lines 13 to 21 | `connected(connection, session, request, selection, cookies, path, query)`; `closed(session)` line 29. |
| `src/wire/server-message.ts` lines 20, 21 and 59 to 70; `src/wire/server-wire.ts` line 121; `src/wire/protocol.ts` lines 253 to 263 | `CookiePair`; the `connected` message's cookies; the program's `cookie` message. |
| `src/channel/request.ts` lines 17, 21 and 27 | `cookiesByName`, `pageRequest`'s cookies. |
| `src/channel/connections.ts` lines 13, 34 and 46 | `Connection.cookies`, `Connections.add`, `forgetSession`. |
| `src/channel/context.ts` lines 27, 53, 54, 195, 200 and 269; `src/channel/host.ts` lines 120 and 192 to 208 | `CookieOptions`, `Context.cookies(session)`, `Context.cookie(connection, …)`, `connectionsOf(session)`. |
| `src/channel/tabs.ts`; `src/channel/channel.ts` lines 146 to 170 and 238 to 246 | Since DEC-6443 each connection is a session to applications (line 157 passes the connection number as the session); `Tabs` keeps each server session's connections so that `closed` ends them all. |
| `src/wire/connection-rules.ts` lines 13, 15 and 23; `src/wire/server-rules.ts` line 216 | `COOKIE_BYTES`, `SERVER_COOKIE_PREFIX`, `cookieFault`. |
| `src/testing/harness.ts` lines 40 to 127 | `Harness.join(session, page, cookies)` always connects with the connection number equal to the session. |

**The component library, `neoteletext-server-ts-ui-components`, release 22.0.0**

| Where | What it is |
|---|---|
| `src/core/viewer-cookies.ts` | `ViewerCookies`, in memory, keyed by session. |
| `src/core/viewer-languages.ts`; `src/core/language.ts` line 17; `src/input/language-picker.ts` line 65; `src/core/channel-options.ts` line 31 | The `language` cookie, one year, `SameSite=Lax`, set on every connection of the session. |
| `src/core/services.ts` lines 62 to 70; `src/core/channel-services.ts` line 58 | `Services.cookies(session)` and `setCookie(session, …)` (REQ-2217). |
| `src/interactive/tally.ts`; `src/interactive/poll.ts` | `Tally` keeps a poll's ballot by session number (`ofSession`, `keepForSession`, lines 69 and 84). |
| `src/core/kept-components.ts` lines 57 and 77; `src/core/component.ts` line 203; `src/core/runtime.ts` line 248 | `keptAs` keeps component state by session number. |
| `src/core/state-store.ts` | `SqliteStateStore`, table `session_value(session INTEGER, …)`, `SESSION_LIFETIME_MS` 30 days, `MOST_SESSION_VALUES` 262,144, no transaction around a read-modify-write. |

Because the kit's session number is the connection number since DEC-6443, and connection numbers start again after a server restart, `tally.ts` lines 69 and 84 and `kept-components.ts` lines 57 and 77 hand one viewer's ballot and kept choices to another viewer whose connection is later given the same number. That is TODO-6463's leak.

**The Python kit, `neoteletext-server-channels/kits/python`, protocol 12**

| Where | What it is |
|---|---|
| `src/neoteletext_app/app.py` lines 152, 168 to 174, 400 to 420, 482, 674 to 700 and 818 | `page_request`'s cookies, `Connection.cookies`, `App.cookie`, `App.cookies_of`, `connections_of(session)`, `_connected` (`on_join` only for a session's first connection), `_closed(session)`. Unlike the TypeScript kit, its handlers are given the server's session, shared by tabs (TODO-6445). |
| `src/neoteletext_app/textrules.py` lines 23, 28, 100 and 114 | `COOKIE_BYTES`, `SERVER_COOKIE_PREFIX`, `_cookie`. |
| `tests/test_kit.py` lines 156 to 170, 467, 560 to 572 and 637 to 672 | The test drivers and cookie tests. |

**The channels**

| Channel | What uses cookies or per-viewer state |
|---|---|
| neoteletext-server-channel-demosite | The cookie area, magazine 7, pages 700 to 705 (`src/pages/cookies/`: visit counter, minute cookie, lifetimes, cookie list, names, attributes; REQ-3838, REQ-3186, DEC-2234); the language choice (`src/pages/languages/language-choice.ts` lines 62 and 71; REQ-2218); the poll's `Tally` (`src/site/site.ts` line 24). |
| neoteletext-server-channel-uicomponentsdemo | The same cookie pages, 110 to 114; the language choice; the poll (`src/site/magazines/play.ts` line 17); `keptAs` on page 304 (`src/pages/lists/choosing-page.ts` line 21), the only user of `keptAs`. |
| neoteletext-server-channel-home-www.neoteletext.com, neoteletext-server-channel-hackaday | The library's in-memory per-viewer state only (no store). |
| neoteletext-server-channel-audiodemo, -naplpsdemo, -regisdemo | Per-session maps in memory, cleared at `ended` (`keyboard-page.ts` line 32; `naplps-demo.ts` lines 54 and 56; `regis-demo.ts` lines 41 to 51, `pages/desktop.ts` line 118). |
| neoteletext-server-channels, old Python Hackaday (`hackaday/src/hackaday/channel.py`) | `viewers` per session (line 179) and a poll of one vote per session (lines 187, 432 to 437, 891 and 892). |
| neoteletext-server-channel-regisgallery | No per-viewer state. |

---

## 2. Terms

Each term is used in this sense throughout.

- **Channel identity.** A channel's address in the canonical form of DOC-1863 ("A channel's address and boundary"): the scheme, `http` or `https`; the host in lower case; the port, written only when it is not the scheme's default; and the folder path, which begins and ends with `/`. Two addresses are the same channel only when all four are equal, compared exactly (the browser's requirement 7.1, the engine's REQ-2874 and REQ-507). `http://example.org/news/` and `https://example.org/news/` are two channels, and so are `https://example.org/news/` and `https://example.org/news/sport/`.
- **Jar.** The set of keys one kind of window uses. There are two: the ordinary jar, shared by every ordinary window and tab, and the private jar, shared by private windows and held in memory only. The word is kept from cookies because the browser's interface already uses it for the same partition.
- **Key** (or **viewer key**). An Ed25519 key pair (RFC 8032) made by the browser's trusted core for one channel identity in one jar. Its private half never leaves the trusted core and the key file of section 3.3.
- **Visit key.** A key held in the trusted core's memory only, never written, gone when the browser closes or at the visit limits of VS-106.
- **Remembered key.** A key the viewer has chosen to keep with "Remember me on this channel" in the browser's own interface, written encrypted to the key file, gone when the viewer forgets it, when the channel ends it, or at the limits of VS-107.
- **Key identifier.** SHA-256 of a domain-separation string, the algorithm number and the public key (VS-302). It is what the server keeps of a key.
- **Handle** (or **viewer handle**). The 128-bit value a channel's program is given for a viewer, derived by the server with a keyed hash from the key identifier and the channel (VS-305), written as 32 lower-case hexadecimal characters. It is meaningless outside that channel and that server secret.
- **Challenge.** 32 bytes from the server's cryptographic random source, sent to the browser in a STATE_CHALLENGE record, valid once, for one connection, for a bounded time.
- **Proof.** The browser's STATE_PROOF message: the algorithm, the lifetime, the public key and an Ed25519 signature over the exact bytes of VS-203, which include the challenge and the channel identity.
- **State request.** A program's request, through its kit, that the viewer on a connection be given state (`requestState`), which the server turns into a challenge asking the browser to create a key if it holds none.
- **State end.** A program's request that a viewer's state end (`endState`), which the server turns into a STATE_END record telling the browser to delete the key, and into the deletion of the server's own record.
- **Gesture.** An input event from the viewer (a key, a click, typed text) received on the connection in question. A state request is honoured only shortly after one (VS-212).
- **Stateless client.** A client that never holds a key: it answers every challenge with STATE_NONE.
- **Push connection.** The channel's WebSocket on which pages and records come down and input goes up (the input protocol, DOC-1923, DOC-1951 to DOC-1961). It is the only place this mechanism travels.
- **Push protocol.** The binary protocol on the push connection, agreed in HELLO and WELCOME (DEC-1447). Today it is version 7 (`neoteletext_input::limits::VERSION`, WebSocket subprotocol `neottx.7`). This design makes it version 8 (subprotocol `neottx.8`), the engine's next version (DEC-6477).
- **Program protocol.** The JSON protocol between the server and a channel's program (`crates/teletext-runtime/src/protocol.rs`). Today it is version 12. This design makes it version 13.

---

## 3. The browser

Each requirement in this section is a requirement of neoteletext-browser unless it says otherwise.

### 3.1 Making and holding keys

**VS-101. Keys are made by the trusted core, from the system's cryptographic random source.**
- **Statement.** When a key is to be created (VS-104), the trusted core MUST create it as an Ed25519 key pair (RFC 8032 section 5.1.5) from a 32-byte seed drawn from the operating system's cryptographic random source through `ring::rand::SystemRandom`, and MUST NOT create, hold, receive or send a private key or seed in any other process: not the fetcher, not the decoder, not the interface, and not the broker, which keeps only the key file's sealing key (VS-108).
- **Reason.** The fetcher speaks to the channel's server and is the process a hostile server compromises first (the browser's requirement 7.5, DEC-1765); the interface may run an attacker's code (requirement 3.9). A key held in either could be copied out. The trusted core already holds every cookie for the same reason (REQ-879), and already draws random nonces from `SystemRandom` in `core/src/cookies/file.rs`.
- **Source.** Owner's decision 2 of 18 November 2026; RFC 8032 section 5.1.5; the browser's REQ-879 and REQ-715 (whose rule this carries over).
- **Verification.** Test: the trusted core's key store creates a key whose seed is 32 bytes and whose public key verifies a signature made with it; a code check (in `scripts/check.sh`) that no crate but `core` names the key store's types or the signing call; the hostile-fetcher harness (DEC-2441) asks for every state message with forged fields and receives no private key material.

**VS-102. One key per channel identity per jar.**
- **Statement.** The trusted core MUST hold at most one key for each pair of jar and channel identity, and MUST use a channel's key only for that exact channel identity: a key made for `https://example.org/news/` MUST NOT be used for `https://example.org/news/sport/`, for `https://example.org/`, for `http://example.org/news/` or for any other port.
- **Reason.** The channel is the unit of isolation (the browser's REQ-712); a folder inside a channel's folder is another channel, often another person on a shared host (REQ-5505, REQ-1885). Exact identity matches what cookies do today (REQ-1883) and keeps secure and insecure addresses apart without a separate rule (owner's decision 5).
- **Source.** Owner's decisions 2 and 5; the browser's requirement 7.1; DOC-1863; open question Q3 (recommended answer: no key covers folders below its channel).
- **Verification.** Test: keys made for the four channels above are four different keys; a challenge on each connection is signed with that connection's channel's key only.

**VS-103. The trusted core decides which channel a key is for, never the fetcher.**
- **Statement.** When the fetcher of a tab asks the trusted core to answer a challenge, the trusted core MUST take the channel identity from the address of the tab that fetcher serves (as `fetcher_channel` does today for cookies, `core/src/trusted_core/cookies.rs` line 100), MUST build the signed bytes itself (VS-203), and MUST ignore any channel, host or path the fetcher's message might carry; the fetcher's message to the core MUST carry only the challenge, the request to create, and a request number.
- **Reason.** A fetcher compromised by its channel's server could otherwise ask for a signature under another channel's key and so impersonate the viewer to that channel.
- **Source.** Owner's decision 2; the browser's REQ-879 and DEC-1765 (the fetcher returns typed fields; the core keeps every rule).
- **Verification.** Test with the hostile-fetcher harness: a fetcher for channel A that asks for a signature can obtain only a signature under A's key over bytes naming A.

**VS-104. A key is created only when a channel asks for state, after a gesture.**
- **Statement.** The trusted core MUST create a key for a channel only when a challenge on that channel's push connection asks to create (VS-205, `create` set), only when that tab has received an input event from the viewer within the last `STATE_GESTURE_MS` (VS-212), only when the viewer has not blocked state for the channel or for all channels (VS-112), and only when the tab's page has been shown to the viewer; otherwise it MUST answer STATE_NONE with the reason that applies. A challenge without `create` MUST never cause a key to be made.
- **Reason.** A channel that never asks never causes anything to be stored (the opt-in that HTTP State Tokens left open, and Gemini's rule that a client never makes a certificate without the user's involvement). Requiring a recent gesture means state begins only when the viewer does something, which is the legal ground of the visit key (section 11) and stops a channel that is only passed through in a redirect from gaining state (the lesson of bounce tracking, research section 1.4).
- **Source.** Owner's decisions 2 and 7; research sections 2.1, 2.5 and 4.4; WP 194 section 3.1.
- **Verification.** Test: a challenge with `create` and no recent input is answered STATE_NONE reason `no_gesture`; with recent input it creates a key; a challenge without `create` on a channel with no key creates nothing; a blocked channel is answered STATE_NONE reason `declined`.

**VS-105. A key is created as a visit key.**
- **Statement.** Every key MUST be created as a visit key, held in the trusted core's memory only; only the viewer's own action in the browser's interface (VS-109) MAY make it a remembered key.
- **Reason.** Persistence across browser sessions needs the viewer's explicit choice (WP 194 section 3.2); the default must be the safe and exempt one (research section 1.3: options nobody is obliged to use protect nobody).
- **Source.** Owner's decision 4; WP 194 section 3.2.
- **Verification.** Test: a newly created key is not in the key file after the next write; it is gone after the trusted core restarts.

**VS-106. Limits of a visit key.**
- **Statement.** A visit key MUST be deleted when the browser closes, and also when it has not been used in a proof for `VISIT_KEY_IDLE_LIMIT` *(open question Q2; recommended 12 hours)* or has existed for `VISIT_KEY_ABSOLUTE_LIMIT` *(open question Q2; recommended 7 days)*, whichever comes first, even while the browser runs.
- **Reason.** A browser left running for weeks would otherwise turn a visit key into a persistent identifier without the viewer's choice. WP 194 says an exempt identifier "must be set to expire once it is not needed"; HTTP State Tokens chose one hour as a default lifetime for the same reason.
- **Source.** Owner's decision 4; WP 194 section 2; research sections 2.1 and 4.7.
- **Verification.** Test with a controlled clock: a visit key unused for the idle limit, and one older than the absolute limit, are deleted, and the next challenge asking to create makes a new, different key.

**VS-107. Limits of a remembered key.**
- **Statement.** A remembered key MUST be deleted when it has not been used in a proof for `REMEMBERED_KEY_IDLE_LIMIT` *(open question Q2; recommended 180 days)* or when `REMEMBERED_KEY_ABSOLUTE_LIMIT` *(open question Q2; recommended 400 days)* has passed since it was first remembered, whichever comes first. It MUST NOT be renewed in a way that keeps the same key beyond the absolute limit; after deletion the viewer is asked again in the ordinary way.
- **Reason.** Silent renewal of the same value is what makes a supercookie (WP 194 footnote 3 says such identifiers are very unlikely ever to be exempt). 400 days is RFC 6265bis's cap on a cookie's life, which the browser applies today (REQ-5159).
- **Source.** Owner's decision 4; research section 4.7; the engine's REQ-5159.
- **Verification.** Test with a controlled clock: a remembered key is deleted at each limit; a key used every day is still deleted at the absolute limit.

**VS-108. Remembered keys are kept only encrypted, in their own file.**
- **Statement.** The trusted core MUST keep remembered keys, and nothing else, in `viewer-keys.bin` in the settings folder, written with mode 0600 in a folder of mode 0700 through a temporary file renamed over it (as `core/src/private_file.rs` does today), sealed with ChaCha20-Poly1305 from `ring` under a 256-bit key that the broker makes once with `SystemRandom` and keeps in the platform's secret store under its own entry ("NeoTeletext viewer keys"), the file's first line naming its format and cipher and authenticated with it, with a fresh random 96-bit nonce for each write. Each entry MUST hold the channel identity, the 32-byte seed, the time the key was created, the time it was remembered and the time it was last used, and no other data. When the sealing key cannot be had, or the browser was started with `--no-keychain` (decision 113), nothing MUST be written, "Remember me" MUST be unavailable with the reason shown, and every key MUST stay a visit key.
- **Reason.** This is the protection cookies have today (the browser's `cookies.md` sections 6 and 7, REQ-882): a copy of the file alone is useless. A separate entry and file mean the cookie file and its key can be deleted outright at migration (VS-603).
- **Source.** Owner's decision 4 ("kept (encrypted at rest)"); the browser's REQ-882, decision 62, decision 113, decision 58 (no weaker mode).
- **Verification.** Tests: the file is sealed, and a byte changed anywhere makes it unreadable; without the sealing key nothing is written and the offer is unavailable; started with `--no-keychain` the broker is never asked. Fuzz target `viewer_key_file` on the reader.

**VS-109. The viewer's choice to be remembered.**
- **Statement.** A visit key MUST become a remembered key only when the viewer chooses "Remember me on this channel" in the browser's own interface, outside the page (the trusted strip, a menu or the settings), where the choice names the channel identity, says that the channel will recognise this browser on later visits until the viewer forgets it or for at most the absolute limit, and is off until the viewer chooses it. The browser MUST offer it from its menu for the channel in the active tab at any time on an ordinary window, and MAY also show it when the channel sends STATE_KEEP_OFFER (VS-208), as decided under open question Q4. It MUST be offered identically on encrypted and unencrypted channels. Forgetting MUST be as easy as remembering.
- **Reason.** WP 194 section 3.2: "a checkbox and a simple information note such as 'remember me (uses cookies)' next to the submit form would be an appropriate means of gaining consent". In the browser's own interface a channel cannot pre-tick it, hide it or imitate it (requirement 14.5, REQ-785, forbids anything in the window being mistakable for the strip).
- **Source.** Owner's decisions 4, 5 and 7; WP 194 section 3.2; open question Q4.
- **Verification.** Test: the menu's choice turns the active tab's visit key into a remembered key and the next proof carries lifetime `remembered`; a STATE_KEEP_OFFER alone changes nothing; review of the wording by the owner and by the lawyer of section 11.

**VS-110. Private windows.**
- **Statement.** Private windows MUST use the private jar: keys held in memory only, created under the same rules as ordinary keys, shared by every private tab of a channel, never written, never listed with the ordinary keys, never remembered (the menu's choice is unavailable and STATE_KEEP_OFFER is ignored without asking the viewer), and deleted when the last private window closes. No key MUST ever move between the private and the ordinary jar.
- **Reason.** What a private window means in every browser, as private cookies do today (REQ-881, REQ-3398, REQ-3400).
- **Source.** Owner's decision 4; the browser's REQ-881, REQ-3398, REQ-3400.
- **Verification.** Test: a channel open in a private and an ordinary tab is given two different keys; after the last private window closes, a new private tab's challenge with `create` makes a new key; the private jar is never in the key file.

**VS-111. Tabs of one channel share its key.**
- **Statement.** Every tab of one jar showing one channel MUST answer challenges with that channel's one key, so that the channel's program sees the same handle on each tab's connection. When a key is created, remembered or forgotten while other tabs of the same channel and jar have push connections open, the trusted core MUST tell each of those connections, through its fetcher, to send STATE_OFFER (after a key is created or remembered) or STATE_NONE with reason `forgotten` (after it is forgotten), so that the server learns of the change on each.
- **Reason.** Tabs are otherwise independent (DEC-6443, REQ-714), but state that must outlive a tab, such as one vote per viewer, needs one identity across a viewer's tabs, as cookies gave (DEC-910 item 1, TODO-6463).
- **Source.** Owner's decisions 2 and 4; DEC-910; DEC-6443 item 3 (cookies shared between tabs), which this replaces.
- **Verification.** Test: two tabs on one channel, a key created through one; the other tab's connection sends STATE_OFFER and, challenged, proves with the same public key; forgetting sends STATE_NONE `forgotten` on both.

### 3.2 The viewer's controls

**VS-112. Forget, block and see.**
- **Statement.** The browser MUST give the viewer, in its settings and not in the developer console alone, a list "Channels that know you" of every channel with a key in the ordinary jar, showing for each its channel identity, whether its key is a visit key or remembered, when it was created and when it was last used, and never the key or any part of it; and MUST offer, for each channel, Forget (delete its key), Remember or Stop remembering, and Block (forget it and answer every later challenge with `create` for that channel with STATE_NONE `declined`), and for all channels Forget all, and a setting "Channels may ask to know you: Allow / Never" (default Allow; Never answers every challenge with `create` with STATE_NONE `declined`). Clearing history (the browser's requirement 20.6) MUST offer to forget the keys created within its time range. Every control MUST act by view numbers as the cookies panel does today, so that the interface process can ask for nothing but deletions it was shown.
- **Reason.** The viewer can forget one channel or all at any time (owner's decision 4); HTTP State Tokens made visible user control mandatory (its section 7.3); Tor Browser's "New Identity" is the model of a reset that works. A settings list, rather than only the developer console's Cookies tab (REQ-3929), puts the control where a viewer looks.
- **Source.** Owner's decision 4; research sections 2.1, 2.6 and 4.7; the browser's REQ-3929, REQ-2902 and requirement 20.6.
- **Verification.** Tests: the list shows created and remembered keys without key material; each control deletes or blocks as stated; the interface cannot delete a row it was not shown; blocked channels are kept in `settings.txt` within `MOST_BLOCKED_CHANNELS` (1,000, the cookie block list's bound).

**VS-113. Forgetting tells the channel nothing that links old and new.**
- **Statement.** When the viewer forgets a channel, the browser MUST delete its key at once, MUST send STATE_NONE with reason `forgotten` on each of that channel's open push connections in that jar, and MUST NOT send anything that relates the forgotten key to any key made later for the same channel.
- **Reason.** After a reset the server must be unable to link the old identity to the new one; a notice naming both would itself link them (research section 4.7).
- **Source.** Owner's decision 4; research section 4.7.
- **Verification.** Test: after Forget, the next key for the channel has a different public key, and no message between the two names the old one.

**VS-114. The strip says when a channel knows the viewer.**
- **Statement.** While a tab's connection carries a key, the trusted strip SHOULD show a small mark that the channel knows this browser ("Known" for a visit key, "Remembered" for a remembered key), which opens the channel's row of VS-112 *(open question Q13)*.
- **Reason.** Transparency: the viewer can see, at the place they look, that state exists and remove it in one step.
- **Source.** Owner's decisions 4 and 7; research section 2.1 (visibility of the token store).
- **Verification.** Test of the strip state; review of the design by the owner.

**VS-115. The insecure badge is the only difference between encrypted and unencrypted channels.**
- **Statement.** The browser MUST create, prove, remember, forget, block and list keys in exactly the same way on `http` and `https` channels and on `ws://` and `wss://` push connections; the only difference shown MUST be the existing "Not secure" badge of the trusted strip (`interface-core/src/browser/toolbar.rs`, decision DEC-1756); and no message to a server or a program MUST carry whether the connection is encrypted for the purpose of this mechanism.
- **Reason.** The owner: "it must behave the SAME insecure and secure developers need the same behaviour". Development channels are served plainly on local hosts, and a developer must see there exactly what viewers will see on the encrypted channel. The two never share a key, because the scheme is part of the channel identity.
- **Source.** Owner's decision 5; DEC-1756 (plain `http` and `ws://` supported, marked Not secure).
- **Verification.** Test: one scripted sequence of create, prove, remember, forget and end, run against the same server over `ws://` and `wss://`, gives identical messages but for the channel identity's scheme and the signature.

### 3.3 Where keys go, and where they never go

**VS-116. A key is shown only on its channel's own push connection.**
- **Statement.** The browser MUST send a proof, STATE_NONE or STATE_OFFER only on the push connection of the channel the key belongs to, opened by that channel's own fetcher, and MUST NOT place a key, a public key, a key identifier, a signature or any value derived from them in an address, a query, a redirect, a page or file fetch, an HTTP header, the history, the session file (`session.txt`), a bookmark, a log line, the developer console, a crash report or a message to the interface process.
- **Reason.** A value that travels on every fetch leaks to shared caches, plain-HTTP proxies and logs; a value that travels only as a signature over a fresh challenge on one connection leaks nothing reusable (research sections 3 and 4.4).
- **Source.** Owner's decision 2.
- **Verification.** Test: a channel visited with a key, its pages and files fetched, a redirect followed; the recorded requests carry no part of the key; a code check that the logging calls in the state modules take no key type.

**VS-117. Redirects and other channels' content.**
- **Statement.** When a channel redirects a tab to another channel (the browser's REQ-701, REQ-1688), or a link leads to another channel, the browser MUST use, on the new channel's push connection, only the new channel's own key in the same jar, or none; nothing of the first channel's key MUST travel with the redirect or the link, and the first channel's key MUST NOT be used for any connection of the second.
- **Reason.** A redirect from A to B must carry nothing of A, and B's key is used only on B's own connection (research section 4.4). No NeoTeletext page embeds another channel, so there is no other case of another channel's content.
- **Source.** Owner's decision 2; research section 4.4; the browser's REQ-701 item 1.
- **Verification.** Test: channel A with a key redirects to channel B; B's connection is challenged and answers STATE_NONE `no_key` (or proves with B's own key when one exists); A's key is unchanged and unused.

**VS-118. A copied profile.**
- **Statement.** When `viewer-keys.bin` cannot be opened under the sealing key the platform's secret store gives (for example because the settings folder was copied to another computer or user without the secret store), the trusted core MUST discard the file's contents, MUST start with no remembered keys, and MUST tell the viewer once in the settings that remembered channels from a copied or restored profile were not carried over; it MUST NOT ask the viewer to supply a key or import keys from anywhere.
- **Reason.** Two machines with one key would be one viewer to every channel. A key sealed under the secret store does not survive a copy without the store, which covers most copies. A copy that includes the secret store (a whole-machine migration) duplicates the key; only a key held in hardware would stop that, which is left out of this design (section 12).
- **Source.** Research sections 3 and 4.12; owner's decision 4.
- **Verification.** Test: a key file sealed under one key, opened under another, yields no keys and the notice once.

### 3.4 The browser's messages

**VS-119. The messages between fetcher and trusted core.**
- **Statement.** The fetcher and the trusted core MUST exchange exactly these state messages, each typed, bounded and checked by its reader: from the fetcher, `StateChallenged { request: u32, challenge: [u8; 32], create: bool }` and `StateEndReceived { key_id: [u8; 32] }` and `StateKeepOffered`; from the core, `StateAnswer { request: u32, answer: Proof { algorithm: u8, lifetime: u8, public_key: [u8; 32], signature: [u8; 64] } | None { reason: u8 } }` and `StateSendOffer` and `StateSendNone { reason: u8 }` (VS-111, VS-113). The core MUST answer each `StateChallenged` once, MUST refuse a second answer request for a challenge it has already signed on that fetcher, and MUST NOT sign more than `MOST_PROOFS_PER_FETCHER_PER_MINUTE` *(recommended 60, open question Q12)*.
- **Reason.** All input is untrusted, including from the browser's own confined processes; a fixed-length, typed message cannot carry a forged channel or an oversized field.
- **Source.** The browser's requirement 3.2; DEC-1765; owner's decision 2.
- **Verification.** Tests of each message's encoder and reader; a fuzz target `state_messages` on the core's reader (replacing the cookie targets that `cookies.md` section 11 named and that were never written).

**VS-120. Session restore.**
- **Statement.** When the browser restores its tabs at start (the browser's REQ-874), it MUST restore no visit key; a restored tab of a channel with a remembered key proves with that key when challenged, and one without answers STATE_NONE.
- **Reason.** A visit key ends when the browser closes; restoring it would make it persistent without the viewer's choice. Session cookies are likewise never written today (REQ-SEC-013).
- **Source.** Owner's decision 4; the engine's REQ-SEC-013.
- **Verification.** Test: restart with two restored tabs, one of a remembered channel and one of a visited channel; only the first proves.

---

## 4. The protocol between browser and server

Each requirement in this section is a requirement of neoteletext-common (the protocol), stated in the documentation items that define the protocol (DEC-2022), and built in the engine's push agent and records, the browser and the server.

### 4.1 Version and order

**VS-201. Push protocol version 8.**
- **Statement.** The state messages MUST be part of push protocol version 8, the version after the engine's 7 (`neoteletext_input::limits::VERSION`), with the WebSocket subprotocol `neottx.8`, agreed in HELLO and WELCOME (DEC-1447); a server that speaks version 8 MUST refuse a HELLO of version 7, and a receiver that speaks version 8 MUST close a connection whose WELCOME names version 7. Version 8 MUST NOT carry a SET_COOKIE record, and its receivers MUST NOT send or accept a `Cookie` or `Set-Cookie` header on the push upgrade or on any fetch. There MUST be no capability that turns state off at the protocol level: a client that keeps no state answers STATE_NONE.
- **Reason.** One protocol, no fallback: a downgrade to a version with cookies would undo the design (DPoP section 11.3: a server must not accept proofs without a nonce once it has issued one; the same holds for falling back to cookies). Input protocol version 1 was retired outright in the same way (DEC-1458).
- **Source.** Owner's decision 1; DEC-1458; RFC 9449 section 11.3; DEC-6477 (the engine's next version, 8, in place of the 3 first written here, which assumed the engine was at version 2).
- **Verification.** Tests: a version 7 HELLO is refused; a WELCOME of version 7 is refused by the engine's agent; no request the browser or `neottx` sends carries a `Cookie` header, and a `Set-Cookie` in a response is ignored.

**VS-202. When the exchange happens.**
- **Statement.** On every push connection, the server MUST send STATE_CHALLENGE (with `create` clear) immediately after WELCOME, before any page; the receiver MUST answer it with STATE_PROOF (when it holds a key for the channel) or STATE_NONE before it sends SELECT; and the server MUST hold the program's `connected` event (which it already holds for the first SELECT, REQ-1471) until the answer arrives or `STATE_ANSWER_MS` *(recommended 10,000 ms, open question Q12)* passes, in which case the connection has no viewer. Later in the connection, the server MAY send further challenges only as VS-205 and VS-212 allow.
- **Reason.** The program must know at `connected` whether the viewer is known, so that it can draw the first page in the viewer's language and with their choices; proof is per connection, not per request (the lesson of DBSC from Token Binding's latency, research section 2.3).
- **Source.** Owner's decision 2; research section 4.1 item 5.
- **Verification.** Tests: the first record after WELCOME is STATE_CHALLENGE; a receiver that sends SELECT before answering is treated as answering STATE_NONE `no_key`; a receiver that never answers gets `connected` with no viewer after `STATE_ANSWER_MS`.

### 4.2 The signed bytes

**VS-203. Exactly what is signed.**
- **Statement.** A proof's signature MUST be the Ed25519 signature (RFC 8032 section 5.1.6, pure Ed25519, no context, no prehash) of exactly this byte string, and of nothing else:
  1. the 27 ASCII bytes `NeoTeletext viewer state v1` followed by one zero byte (domain separation);
  2. one byte, the push protocol version, 8 (the engine's `neoteletext_input::limits::VERSION`, used by name, so that the signed byte follows the version);
  3. one byte, the algorithm number, 1 for Ed25519;
  4. one byte, the lifetime, 0 for a visit key and 1 for a remembered key;
  5. the 32 bytes of the challenge;
  6. two bytes, big-endian, the length in bytes of the channel identity, at least 9 (`http://a/`) and at most `MAX_CHANNEL_IDENTITY_BYTES`;
  7. the channel identity, as ASCII in the canonical form of DOC-1863, with no trailing byte.

  `MAX_CHANNEL_IDENTITY_BYTES` is 523, derived as 8 (`https://`) plus 253 (the longest host name, RFC 1035 section 2.3.4 as clarified by RFC 1123 section 2.1) plus 6 (`:65535`) plus 256 (the longest folder path, DOC-1863), and is defined once, in the engine, and used by name by the browser and the server.
- **Reason.** The signed text names the purpose, the version, the channel and a fresh server challenge, so a proof is useless for any other purpose, any other version, any other channel or any other time; this is DPoP's answer to pre-generation and replay (RFC 9449 sections 11.1 and 11.2) and binds a proof to its channel even if a key were ever shared by mistake. Signing the lifetime stops a network attacker from changing what the browser claims. The version byte stops a proof made for one version being accepted under another (downgrade).
- **Source.** Owner's decision 2 ("signing a fresh challenge from the server together with the channel's identity"); RFC 8032; RFC 9449 section 11; DOC-1863.
- **Verification.** Test vectors in `wire-vectors.tsv` (a seed, a challenge, a channel identity, the expected bytes and signature), checked by the engine, the browser and the server; a test that changing any one byte of any field makes the server refuse the proof.

### 4.3 The messages

All lengths are fixed except where a bound is named; a message of any other length, or with any value not listed, is a protocol error, and the connection is closed with the existing protocol-error close. Record types are allocated in DOC-1951's table, and are the engine's next free ones: 13 is kept for the CHANNEL record (REQ-3581) and 14 to 17 are REGIS, DRAWING_LINKS, REGIS_CURSOR and NAPLPS, so the state records take 18 to 20 (DEC-6477). Control messages from the receiver use the input protocol's 0xFF-prefixed extension form (DEC-1444: `0xFF`, the type, the length, the payload), with the types 0x48 to 0x4A, the next after DRAWING_HOVER (0x47), allocated in the documentation item that defines them. Type 8 (SET_COOKIE) is retired and never reused.

**VS-204. The messages, field by field.**
- **Statement.** Push protocol version 8 MUST define exactly these state messages:

  | Direction | Message | Carried as | Fields, in order | Bytes |
  |---|---|---|---|---|
  | server to receiver | STATE_CHALLENGE | Record type 18, one or more fragments | `challenge`: 32 bytes; `create`: one byte, 0 or 1 | 33 |
  | server to receiver | STATE_END | Record type 19 | `key_id`: 32 bytes, the key identifier (VS-302) of the key to delete | 32 |
  | server to receiver | STATE_KEEP_OFFER | Record type 20 | none | 0 |
  | receiver to server | STATE_PROOF | Extension type 0x48 | `algorithm`: one byte, 1; `lifetime`: one byte, 0 or 1; `public_key`: 32 bytes; `signature`: 64 bytes | 98 |
  | receiver to server | STATE_NONE | Extension type 0x49 | `reason`: one byte: 0 `no_key` (no key for this channel and none asked to be made), 1 `declined` (the viewer blocked or refused), 2 `stateless` (the client never keeps state), 3 `forgotten` (the key in use on this connection has just been forgotten), 4 `no_gesture` (asked to create without a recent gesture) | 1 |
  | receiver to server | STATE_OFFER | Extension type 0x4A | none | 0 |

  The receiver MUST answer each STATE_CHALLENGE with exactly one STATE_PROOF or STATE_NONE; MAY send STATE_NONE `forgotten` and STATE_OFFER unprompted, at most once in each `STATE_OFFER_INTERVAL_MS` *(recommended 10,000 ms)*; and MUST delete its key for the channel on STATE_END only when the key's identifier equals `key_id`.
- **Reason.** These are the research's `StateChallenge`, `StateProof`, `StateNone`, `StateEnd` and `StateKeepRequest` (research section 4.5), with `StateKeepRequest` renamed STATE_KEEP_OFFER because it asks nothing of the browser, and with STATE_OFFER added so that a tab that learns of a new key can be challenged (VS-111). `key_id` in STATE_END stops a delayed STATE_END from deleting a newer key made after a reset. The record types and extension types are the engine's next free ones, as its branch `viewer-state` builds them (commit `793039e5`), a compile-time check there refusing any clash.
- **Source.** Owner's decisions 2 and 4; research section 4.5; DEC-6477 (types 18 to 20 in place of the 13 to 15 first written here, which the engine already uses).
- **Verification.** Tests of every encoder and reader in the engine (which the browser and the server both use, as the engine's records are used today); a fuzz target `state_records` on the receiver's reader and `state_messages` on the server's; the wire vectors.

**VS-205. Challenges: fresh, single, bounded.**
- **Statement.** The server MUST draw each challenge from its operating system's cryptographic random source; MUST keep at most one outstanding challenge per connection, valid for `STATE_ANSWER_MS`; MUST treat it as used once any STATE_PROOF or STATE_NONE arrives, whether or not the proof verifies; MUST refuse a STATE_PROOF when no challenge is outstanding; MUST send a challenge with `create` set only in answer to a program's state request that VS-212 allows; and MUST send at most `MOST_CHALLENGES_PER_CONNECTION_PER_MINUTE` *(recommended 6, open question Q12)* challenges on one connection.
- **Reason.** A challenge used twice, or a proof accepted without one, makes a signature a bearer token (RFC 9449 section 11.2). A bound on challenges stops a hostile program making the browser sign without end.
- **Source.** Owner's decision 2; RFC 9449 sections 11.1 and 11.2.
- **Verification.** Tests: a second proof for one challenge is refused; a proof after `STATE_ANSWER_MS` is refused; a proof with no challenge is refused; challenges beyond the bound are not sent and the program's state request is refused with reason `rate`.

**VS-206. Failure and refusal.**
- **Statement.** When a proof does not verify (an unknown algorithm, a public key that is not a valid encoding, a signature that fails strict verification, or bytes that name another channel identity or version), the server MUST treat the connection as having no viewer, MUST tell the program `connected` (or `state_refused`) with no viewer and reason `invalid`, MUST count it in a metric without any value from the message, and MUST NOT close the connection for that reason alone; a malformed message (VS-204's lengths and values) is a protocol error that closes the connection.
- **Reason.** A failed proof is most often a stale key or a broken client, and the channel must still work without state (research section 4.5, StateNone: "the channel must still work"); a malformed message is not a client the server can reason with.
- **Source.** Owner's decision 2; research section 4.5.
- **Verification.** Tests for each kind of failure.

**VS-207. Reconnects and server restarts.**
- **Statement.** Every new push connection, including one that resumes an input session (DOC-1923) and one made after the server restarted, MUST be challenged afresh and MUST carry a viewer only by a new proof; no state of the mechanism (no challenge, no proof, no handle) MUST survive from an earlier connection on the browser's side apart from the key itself.
- **Reason.** A proof is bound to its challenge and connection. The handle is derived again from the key identifier, so a viewer who reconnects after a restart gets the same handle (VS-305) without the server keeping anything on disk.
- **Source.** Owner's decision 2.
- **Verification.** Test: a server restarted between two connections of the same browser gives the program the same handle on both.

**VS-208. STATE_KEEP_OFFER.**
- **Statement.** A server MUST send STATE_KEEP_OFFER only when the program asks for it on a connection with a viewer whose key is a visit key, at most once per connection; a receiver MUST ignore it in a private window, when the viewer has blocked the channel, when it was already shown for this channel in this browser run, and when `--no-keychain` is in effect; otherwise it MAY show the offer of VS-109 as a notice of the trusted strip that the viewer may accept or dismiss and that never blocks the page *(open question Q4)*.
- **Reason.** A channel knows when remembering would help (after a sign-in, after choosing a language), but only the viewer, in the browser's interface, can choose it.
- **Source.** Owner's decision 4; research section 4.5.
- **Verification.** Tests of each case.

### 4.4 Rules for every party

**VS-209. Nothing of the mechanism is logged.**
- **Statement.** No browser, server, kit, library or channel log line, metric label, crash report or trace MUST contain a challenge, a public key, a signature, a key identifier, a seed or a handle; counts of proofs accepted, refused by reason and STATE_NONE by reason MAY be recorded as metrics without labels that identify a viewer.
- **Reason.** The research's row "ID in logs and crash reports"; the server already logs no cookie value and Caddy redacts `Cookie` by default, and this keeps that line for the new values. The handle is personal data (section 11).
- **Source.** Owner's decision 2 ("never placed in … a log"); research section 4.9.
- **Verification.** Code checks in each repository's commit gate that the state modules' values are not passed to logging calls (a type that does not implement `Display` or `Debug` in Rust; in the kits, a handle type whose `toString` and `__repr__` return a fixed placeholder); a test that the server's debug log of a full session contains none of the values.

**VS-210. A file channel and the start page have no state.**
- **Statement.** A channel opened from files (no push connection), the start page, and a static page written by `neottx html` MUST never have a key, a challenge or a handle.
- **Reason.** Only a push connection carries the mechanism; a file channel has no cookies today either (the browser's requirement 7.8).
- **Source.** Owner's decision 2; the browser's requirement 7.8.
- **Verification.** Test: opening a file channel creates no key, even after input.

**VS-211. Channels cannot relate one another's handles.**
- **Statement.** The browser MUST never use one key for two channel identities (VS-102), and the server MUST derive each channel's handles under a key of that channel alone (VS-305), so that two channels, on one server or on two, can learn no common value for one viewer from this mechanism.
- **Reason.** The research's row "redirects and cross-channel content", and owner's decision 3: "channels cannot relate one another's handles".
- **Source.** Owner's decision 3.
- **Verification.** Test: one browser known to two channels of one server; their programs receive different handles, and neither handle equals any value derived for the other channel.

**VS-212. State is requested only after the viewer acts.**
- **Statement.** The server MUST refuse a program's state request (VS-353) for a connection from which no input event has arrived within the last `STATE_GESTURE_MS`, which is 7,000 ms and defined as `PROGRAM_REPLY_LIMIT_MS` (the time the server already allows a program to answer an event), with the reason `no_gesture`; the browser MUST apply the same rule independently (VS-104).
- **Reason.** The visit key is lawful without consent only as strictly necessary for something the viewer asked for (section 11); a vote, a choice or a sign-in is always an input event. Checking in both places means neither a hostile program nor a hostile server alone can create state unasked.
- **Source.** Owner's decision 7; WP 194 section 3.1; the Storage Access API's use of a user gesture (research section 1.5).
- **Verification.** Tests: a state request in answer to `connected` with no input is refused; one within 7,000 ms of a key event is honoured; one 7,001 ms after is refused.

---

## 5. The server

Each requirement in this section is a requirement of neoteletext-app-server unless it says otherwise. Under DEC-6462 every check is the server's; the kits carry none.

### 5.1 Verification and what is kept

**VS-301. The server verifies every proof itself.**
- **Statement.** The server MUST verify each STATE_PROOF with strict Ed25519 verification (RFC 8032 section 5.1.7, refusing a non-canonical `S` and a public key that is not a valid point encoding) over the bytes of VS-203, built from the connection's outstanding challenge, the push protocol version and each public address configured for the channel (at most `MOST_CHANNEL_ADDRESSES`, 4, so that a channel served under both `http` and `https`, or under two host names, can be verified, each address being its own channel with its own keys), using a library the owner has approved by name (open question Q7).
- **Reason.** The server is the one implementation of every check (DEC-6462). It cannot trust a proxy's `Host` header to name the channel, so it tries the addresses it was configured with; a proof for an address it does not serve fails.
- **Source.** Owner's decisions 2 and 6; DEC-6462; RFC 8032 section 5.1.7.
- **Verification.** Tests against RFC 8032 section 7.1's test vectors and the project's wire vectors; tests that a non-canonical signature, a small-order public key and a proof naming an unconfigured address are refused; a fuzz target on the reader and verifier.

**VS-302. The key identifier.**
- **Statement.** On a verified proof the server MUST compute the key identifier as SHA-256 (FIPS 180-4) of the 21 ASCII bytes `NeoTeletext key id v1` followed by one zero byte, then the algorithm byte, then the 32-byte public key; and MUST then discard the public key and the signature.
- **Reason.** Owner's decision 3: "the server stores only a hash". The domain string keeps this hash distinct from any other hash of the same key.
- **Source.** Owner's decision 3.
- **Verification.** Wire vectors; a test that no structure the server keeps after the proof holds the public key.

**VS-303. What the server keeps, and for how long.**
- **Statement.** The server MUST keep, in memory only, for each channel, a table from key identifier to: the connections that currently present it, the lifetime the last proof claimed, and the time it was last proven; MUST remove an entry when its last connection has been closed for `VIEWER_IDLE_MS` *(recommended 5 minutes, the existing grace of `SESSION_GRACE_MS`)*; MUST bound the table at `MOST_VIEWERS_PER_CHANNEL` *(recommended 262,144, open question Q12)*, removing the entry seen longest ago first; and MUST write nothing of it to disk on the native host or to Durable Object storage on the Cloudflare host. A later login (VS-801) is the only reason the server would ever keep an entry durably.
- **Reason.** The handle is derived again from the key identifier at every proof (VS-305), so nothing need outlast a restart; keeping nothing on disk keeps the server's promise that it is not a database (DOC-1924) and leaves the retention of program data to the program's store, where the data is (VS-405). An entry removed early loses nothing, because the next proof recreates it with the same handle.
- **Source.** Owner's decision 3; DOC-1924; REQ-1474.
- **Verification.** Tests: the table is bounded and evicts the oldest; a restart empties it and the same key yields the same handle.

**VS-304. A flood of fresh identities.**
- **Statement.** The server MUST bound the number of new key identifiers a channel accepts from one network address (as the server sees it, or as the configured trusted proxy states it) to `MOST_NEW_VIEWERS_PER_ADDRESS_PER_HOUR` *(recommended 600, open question Q12)*, answering a proof beyond it as STATE_NONE to the program with reason `rate`, and MUST bound the work of verification by the challenge bounds of VS-205.
- **Reason.** Anyone can make a fresh key at will; the bounds make storage and verification cost linear in connections, which are already bounded, and keep a single address from filling the table of VS-303. The server has no rate limit of any kind today.
- **Source.** Owner's decision 9; DEVELOPMENT.md section 14 (every input bounded).
- **Verification.** Test: the 601st new identifier from one address within an hour is refused; a load test with `teletext-load --mode churn` extended to present fresh keys shows memory bounded.

### 5.2 The handle

**VS-305. Deriving the handle.**
- **Statement.** The server MUST derive the handle for a key identifier on a channel as the first 16 bytes of HMAC-SHA-256 (RFC 2104) keyed by the channel's handle key, over the 28 ASCII bytes `NeoTeletext viewer handle v1` followed by one zero byte and then the 32-byte key identifier, written as 32 lower-case hexadecimal characters; the channel's handle key MUST be HMAC-SHA-256 keyed by the server's handle secret over the 33 ASCII bytes `NeoTeletext channel handle key v1` followed by one zero byte and then the channel's folder path in its canonical form; and the handle secret MUST be 32 bytes from the operating system's cryptographic random source, kept as `viewer-handle.key` in the state directory with mode 0600 (in a folder of mode 0700) on the native host and in the Durable Object's storage on the Cloudflare host, made once and never sent anywhere.
- **Reason.** A program's own data and logs then hold a value meaningless outside that channel and that server; two channels cannot join their records by key even if they share storage; and a breach of a program's data reveals no public key (research section 4.6). 128 bits make a handle unguessable and collision-free for any number of viewers a channel will see.
- **Source.** Owner's decision 3; research section 4.6.
- **Verification.** Wire vectors; tests that two channels' handles for one key differ, and that the same key, channel and secret give the same handle after a restart.

**VS-306. Rotating the handle secret.**
- **Statement.** The server MUST rotate the handle secret only by an explicit operator command (`teletext-server rotate-viewer-secret`, or the Cloudflare host's equivalent administration call), never automatically; on rotation it MUST, before discarding the old secret, tell each running program `viewers_reset` (VS-352), and MUST then make the new secret and clear the table of VS-303, so that every viewer of every channel receives a new handle at their next proof and no program can relate it to the old one. The operator documentation MUST say that rotation makes every channel forget every viewer and when to do it (after a breach of a program's data or of the server's state directory).
- **Reason.** Rotation severs every link at once (research section 4.6), which is right after a breach and wrong at any other time, because it loses every viewer's kept state. Today no session-key rotation tool exists at all (`session.key.previous` is read and never written).
- **Source.** Owner's decision 3; research section 4.6.
- **Verification.** Test: after rotation a returning key yields a different handle, and the program received `viewers_reset` first.

### 5.3 Program protocol 13

Program protocol 13 is one version holding both this mechanism's messages (VS-351 to VS-354) and the synthesizers' sound messages of `audio/server.md` (its SRV-1 to SRV-48), released in one schema, `protocol/schema-13.json`, and one deployment (DEC-6477 answer 3; `audio/server.md` SRV-2). No message type, `kind`, field, server message or `Rule` value of either has two meanings: this section adds the server messages `viewer_began`, `viewer_left`, `state_refused`, `viewers_reset` and `gone`, the program messages `request_state`, `end_state` and `offer_remember`, and the `Rule` values `has_viewer`, `no_gesture` and `unknown_viewer` (VS-353); `audio/server.md` adds the server message `sound_built` and the `Rule` values of its SRV-51, none of which is among these.

**VS-351. What a program is told.**
- **Statement.** Program protocol 13 MUST make these changes to the server's messages to a program, and no others for this mechanism:
  1. `connected` carries `connection`, `request`, `selection`, `path`, `query`, and `viewer`: a handle (a string of exactly 32 characters `0` to `9` and `a` to `f`) or null, and `remembered`: a boolean, false when `viewer` is null; it no longer carries `session` or `cookies`.
  2. `viewer_began` (`connection`, `viewer`, `remembered`): a connection that had no viewer now has one (after a state request, or after the browser sent STATE_OFFER and proved).
  3. `viewer_left` (`connection`): the connection no longer carries a viewer (the browser sent STATE_NONE `forgotten`, or the viewer's state was ended).
  4. `state_refused` (`connection`, `reason`: one of `declined`, `stateless`, `no_gesture`, `no_key`, `invalid`, `rate`, `timeout`, `private`): a state request, or a STATE_KEEP_OFFER, was not granted.
  5. `viewers_reset`: every handle the program knows is void (VS-306).
  6. `gone` (`connection`): the connection has closed and will not come back (it replaces `closed { session }`, see VS-354).
- **Reason.** A program receives a handle or none and learns when state begins and ends (owner's decision 6); nothing a program is given can be replayed or related to another channel.
- **Source.** Owner's decisions 3 and 6.
- **Verification.** The generated schema `protocol/schema-13.json`; tests of each message; the kits' schema copy check.

**VS-352. What a program may ask.**
- **Statement.** Program protocol 13 MUST give a program exactly these requests for this mechanism, and remove the `cookie` message:
  1. `request_state` (`connection`): ask that the viewer on the connection be given state; the server answers later with `viewer_began` or `state_refused`.
  2. `end_state` (`viewer`): end that viewer's state; the server sends STATE_END to every connection presenting the viewer, removes its entry, and tells the program `viewer_left` for each of those connections.
  3. `offer_remember` (`connection`): ask the browser to offer "remember me" (VS-208); refused with `state_refused` when the connection has no viewer, has a remembered key already, or is private.
- **Reason.** The channel's only control over the value is to end it (owner's decision 4); it can ask for state and suggest remembering, and choose nothing.
- **Source.** Owner's decisions 4 and 6.
- **Verification.** Tests of each request and each refusal; a test that a `cookie` message is refused as an unknown type.

**VS-353. Refusing a program that asks for what the viewer has not given.**
- **Statement.** The server MUST refuse, with a typed refusal naming the rule (as `protocol/check.rs` refuses today), each with the `Rule` value given: `request_state` for a connection that is not open (the existing `unknown_connection`), that already has a viewer (`has_viewer`), or that fails VS-212 (`no_gesture`); `end_state` for a handle the channel's table does not hold (`unknown_viewer`); and any message naming a handle in a field the protocol does not define (the existing `unknown_field`). `offer_remember` is answered as VS-352 says, by `state_refused`. A program MUST never be able to choose, set or extend a handle, a key or a lifetime.
- **Reason.** A program is untrusted input to the server (REQ-1475); the mechanism's guarantees hold only if the server refuses what the viewer has not given.
- **Source.** Owner's decisions 4 and 6; REQ-1475.
- **Verification.** Tests for each refusal.

**VS-354. The server session and the `_session` cookie are removed.**
- **Statement.** The server MUST NOT set, read or verify a `_session` cookie, MUST NOT keep a session that spans connections, and MUST remove `session.key`, `session.key.previous`, `SESSION_GRACE_MS`'s use for sessions, `MOST_WAITING_SESSIONS`, `closed { session }` and the session numbers; the continuation of a dropped connection MUST be the input protocol's RESUME (DOC-1923), built in the server as TODO-6444 item 1 asks, and the server MUST tell the program `gone` for a connection once it closes and is not resumed within `RESUME_HOLD_MS` (32,000 ms).
- **Reason.** The server session exists only because of the session cookie; since DEC-6443 programs see each connection as its own session, and the only use left of the server session is to end a viewer's tabs together five minutes after the last closed. A viewer's identity across tabs is now the handle, and a connection's identity across a drop is the RESUME token, which goes only on its own WebSocket. This is a consequence of owner's decision 1 that the owner has not yet ruled on: open question Q9.
- **Source.** Owner's decision 1; DEC-6443; TODO-6444; DOC-1923; open question Q9.
- **Verification.** Tests: no response carries `Set-Cookie`; a connection dropped and resumed within the hold keeps its connection number and the program sees no `gone`; one not resumed is `gone` after the hold.

---

## 6. The kits and the component library

Requirements VS-401 to VS-404 apply equally to the TypeScript kit (neoteletext-server-ts-protocol) and the Python kit (neoteletext-server-channels `kits/python`), which MUST offer the same calls with the same meaning (DEC-6462 item 3). VS-405 to VS-409 are the component library's (neoteletext-server-ts-ui-components).

**VS-401. The kits are thin.**
- **Statement.** Each kit MUST expose this mechanism only as: the `viewer` of a connection (a handle or null) and whether it is remembered; `requestState(connection)` (Python `request_state`); `endState(viewer)` (Python `end_state`); `offerRemember(connection)` (Python `offer_remember`); and the events `viewerBegan`, `viewerLeft`, `stateRefused` and `viewersReset` (Python `on_viewer_began`, `on_viewer_left`, `on_state_refused`, `on_viewers_reset`); with the handle as an opaque type that compares by value and prints as a fixed placeholder. A kit MUST contain no cryptography, no cookie, no parsing of any value of this mechanism, and no check that the server's schema does not express.
- **Reason.** Owner's decision 6 and DEC-6462: the server is the core, the kits are thin and equal.
- **Source.** Owner's decision 6; DEC-6462.
- **Verification.** Each kit's tests; a review that both kits' public interfaces list the same calls; the commit gate's schema copy check against `schema-13.json`.

**VS-402. Every cookie function is removed from the kits.**
- **Statement.** The kits MUST remove `CookiePair`, `cookies` on `connected` and on page requests, `Context.cookie`, `Context.cookies`, `cookiesByName`, `cookieFault`, `COOKIE_BYTES` and `SERVER_COOKIE_PREFIX` (TypeScript), and `App.cookie`, `App.cookies_of`, `page_request`'s cookies, `_cookie`, `COOKIE_BYTES` and `SERVER_COOKIE_PREFIX` (Python), in the release that speaks protocol 13, with no deprecated alias.
- **Reason.** Owner's decision 1; DEVELOPMENT.md section 2.1 (no compatibility shims).
- **Source.** Owner's decision 1.
- **Verification.** A search of each kit for "cookie" in its source finds nothing; the release notes list the removals.

**VS-403. Connections and viewers in the kits.**
- **Statement.** Each kit MUST present each connection to applications as its own unit (DEC-6443), numbered as the connection, and MUST give applications the connection's viewer separately; the Python kit MUST stop presenting the server's session to applications (TODO-6445 item 1), and both kits MUST end a connection's application state at `gone` (VS-351 item 6), not at the end of a server session.
- **Reason.** There is no server session any more (VS-354); the kits must be equal (DEC-6462).
- **Source.** DEC-6443; DEC-6462; TODO-6445.
- **Verification.** Kit tests in both languages: two tabs of one viewer are two connections with one viewer; a closed tab's state ends at its `gone`.

**VS-404. The test harness's fake viewers.**
- **Statement.** Each kit's test harness MUST let a test name fake viewers with fixed handles (for example `const alice = harness.viewer("alice")`, whose handle is a fixed 32-character value derived from the name), connect a named viewer on any number of connections (`harness.join(alice, page)` twice is "alice in two tabs"), connect a connection with no viewer, make a viewer remembered or not (`harness.remember(alice, true)`), simulate a reset (`harness.forget(alice)`, after which `alice` joins with a new handle and `viewerLeft` is sent on her open connections: "after a reset"), simulate a private window (`harness.privateViewer("alice")`, a different handle from `alice`), simulate `requestState` granted (`harness.grantState(connection)`) or refused with each reason (`harness.refuseState(connection, reason)`), and simulate a server restart (`harness.restart()`: connection numbers start again; handles do not change). The same scenarios MUST be available in the Python harness with the same names in `snake_case` (`viewer`, `join`, `remember`, `forget`, `private_viewer`, `grant_state`, `refuse_state`, `restart`), as neoteletext-common's `docs/audio/kit-calls.tsv` lists them.
- **Reason.** Owner's decision 6: tests use named fake viewers with fixed handles, "alice in two tabs", "after a reset", "a private window".
- **Source.** Owner's decision 6.
- **Verification.** Each harness's own tests; the library's tests use it.

**VS-405. The library's store is keyed by handle.**
- **Statement.** The component library's `StateStore` MUST key every per-viewer value by handle and never by a connection number: `ofViewer(viewer, name)` and `keepForViewer(viewer, name, version, value)` replace `ofSession` and `keepForSession`; the SQLite table `viewer_value(viewer TEXT NOT NULL CHECK (length(viewer) = 32), name, version, value, touched_ms, remembered INTEGER, PRIMARY KEY (viewer, name)) STRICT` replaces `session_value` through a numbered migration that drops `session_value` and its rows; values of a handle that is not remembered MUST be deleted `VISIT_VALUE_IDLE_MS` *(recommended 24 hours, open question Q2)* after last use and values of a remembered handle `REMEMBERED_VALUE_IDLE_MS` *(recommended the remembered key's idle limit, 180 days)* after last use; and the bounds of DEC-2463 item 6 MUST apply per handle.
- **Reason.** Keying by handle ends TODO-6463's leak: a handle is unguessable, never reused, and given only to the browser holding the key. The rows keyed by session numbers cannot be mapped to handles and could belong to anyone, so they are dropped once. The program's store is where retention must be enforced, since the server keeps nothing (VS-303).
- **Source.** Owner's decisions 3, 6 and 9; TODO-6463; DEC-2463; REQ-1057; REQ-1058.
- **Verification.** Library tests: a reused connection number after a restart is given nothing; values of a visit handle expire at the idle limit; the migration drops the old table.

**VS-406. Atomic updates.**
- **Statement.** Every read-modify-write of the store MUST run in one SQLite transaction begun with `BEGIN IMMEDIATE`: a `Tally` vote (moving the shared count and writing the viewer's ballot), `keepForViewer` with its pruning, `ofViewer` with its renewal of `touched_ms`, and each component's kept state; the store MUST offer `update(viewer, name, version, change)` that reads, applies `change` and writes within one transaction, and the library's components MUST use it rather than separate reads and writes. The server MUST deliver one connection's events to the program in the order they happened, and MUST apply `end_state` and each proof for one key identifier in the order received.
- **Reason.** Two tabs of one viewer share a handle and can act at once; a vote whose count is written and whose ballot is not (or the reverse), after a crash or an interleaving, counts twice or not at all (owner's decision 9). Today `tally.ts` makes two or three writes with no transaction.
- **Source.** Owner's decision 9; TODO-6463.
- **Verification.** Library tests: alice in two tabs votes in both in interleaved order and the poll counts one vote, her last; a crash simulated between the two writes leaves count and ballot consistent.

**VS-407. Ballots, kept choices and language key on the handle automatically.**
- **Statement.** When a viewer's input on a connection with no viewer leads to a ballot, a kept choice or a language choice, the library MUST call `requestState` for that connection itself, MUST hold the value in memory for the connection until `viewerBegan` (then write it under the handle) or `stateRefused` (then keep it for the connection's life only, and say nothing to the viewer beyond what the page shows), and MUST read the language from the store under the handle at `connected`; a channel's author MUST need no code for this beyond using `Tally`, `keptAs` and the language picker.
- **Reason.** Owner's decision 6: "the library's ballots, kept choices and language key on the handle automatically". The input that triggers it is the gesture VS-212 requires.
- **Source.** Owner's decision 6.
- **Verification.** Library tests with the harness: alice votes with no viewer, state is granted, the ballot is written under her handle; with state refused, the vote counts for that connection's life and is not written per viewer.

**VS-408. The library's cookie services are removed.**
- **Statement.** The library MUST remove `ViewerCookies`, `Services.cookies`, `Services.setCookie`, `LANGUAGE_COOKIE`, `LANGUAGE_COOKIE_SECONDS` and every use of them, in the release that depends on the kit speaking protocol 13; `ViewerLanguages` MUST keep a viewer's language in the store under the handle (name `language`, version 1), and a connection without a viewer MUST keep its language for that connection only.
- **Reason.** Owner's decision 1.
- **Source.** Owner's decision 1; REQ-2217 (superseded).
- **Verification.** A search of the library's source for "cookie" finds nothing; language tests with the harness.

**VS-409. The rule on what a handle may be used for.**
- **Statement.** The protocol's documentation items, each kit's guide and the library's guide MUST state that a channel's program may use a handle only to provide what the viewer asked for on that channel (a poll's one vote, choices the viewer made, the viewer's language, a sign-in the viewer started, and similar features the viewer uses), MUST NOT use it for advertising, profiling, analytics beyond aggregate counts, or sharing with any other party, MUST delete what it keeps for a handle at `end_state` and at the store's limits, and MUST describe what it keeps on its privacy page (VS-702); and the project's own channels MUST follow it.
- **Reason.** Owner's decision 7. The rule cannot be enforced by code, so it is stated where every author reads it, and the project's channels set the example.
- **Source.** Owner's decision 7; WP 194 section 2.4 (a multi-purpose identifier is exempt only if every purpose is).
- **Verification.** Review of the documentation items and guides; review of each project channel.

---

## 7. Clients other than the desktop browser

Each requirement says which repository it belongs to.

**VS-501. `neottx` is stateless by default (engine).**
- **Statement.** `neottx`'s live viewing, `neottx keyboard` and every other engine tool that opens a push connection MUST answer every challenge with STATE_NONE `stateless` unless started with `--identity FILE`, and MUST send no cookie on any request.
- **Reason.** A command-line reader is used for testing and automation; it should create no identity unasked.
- **Source.** Owner's decision 6.
- **Verification.** Test: `neottx` against a channel that requests state is refused with `stateless`.

**VS-502. A test identity in a file (engine).**
- **Statement.** With `--identity FILE`, an engine tool MUST read from `FILE` (refusing it unless it is a regular file owned by the user with no permission for group or others, and exactly the format below), or create it with mode 0600 when it does not exist, a text file of lines `<channel identity> <TAB> <base64 of the 32-byte seed>`, at most `MOST_IDENTITY_FILE_CHANNELS` (64) lines, and MUST use the line of the connection's channel identity as a remembered key for that channel (creating it on a challenge with `create`). The file is never encrypted, and the tool MUST say so in its help text.
- **Reason.** Owner's decision 6: "neottx and tools may keep a test identity in a file". Tests and automation need a reproducible viewer; a plain file is what a developer can inspect and throw away.
- **Source.** Owner's decision 6.
- **Verification.** Tests: a file with group permission is refused; two runs with one file give the program the same handle; a channel not in the file gets a new line on `create`.

**VS-503. Static pages are stateless (engine).**
- **Statement.** `neottx html` and the server's page descriptions for the web (REQ-1728, which already carry no viewer) MUST have no state of any kind.
- **Reason.** Static pages have no push connection.
- **Source.** Owner's decision 2.
- **Verification.** Existing tests of `describe`; a test that `neottx html` output contains no handle or key.

**VS-504. Microcontrollers (engine).**
- **Statement.** The engine's web agent MUST answer STATE_NONE `stateless` unless its port supplies both a cryptographic random source (the existing `RandomSource`, which the firmware test image fills with zeros today) and a signer through a new optional port trait `StateSigner`; with them, it MAY hold one visit key per channel in RAM for the life of the boot, and MUST NOT hold a key fixed at build time or written to flash. No signing library MUST be added to a microcontroller crate until the owner has approved it by name (REQ-161) and its flash cost and time per signature have been measured on `thumbv6m-none-eabi` and the other targets of REQ-GEN-015 (REQ-GEN-017).
- **Reason.** No random source means no safe key; a key fixed at build time is a device identifier that never changes, which WP 194 footnote 3 calls very unlikely ever to be exempt. The research's figure of about 0.5 s per Ed25519 operation on a 48 MHz Cortex-M0 is a third-party benchmark, seen in search only and not measured here.
- **Source.** Owner's decision 2; research section 4.11; REQ-GEN-017; REQ-161.
- **Verification.** Test of the firmware test image: it answers `stateless`; a measurement, recorded with its date and the build's commit, of key generation and one signature on a Cortex-M0 board, before any signer is approved.

**VS-505. The phone companion (neoteletext-common, server and browser; design only, open question Q14).**
- **Statement.** When built, pairing a phone with a viewer on a channel MUST work thus: the viewer chooses "Pair a phone" for the channel in the browser's own interface; the browser sends a pairing request on the channel's push connection (which must already carry a viewer); the server answers with a code of `PAIRING_CODE_SYMBOLS` (8) base-32 symbols (40 bits) from its random source, valid for `PAIRING_CODE_LIFETIME_MS` (120,000 ms), for `PAIRING_CODE_ATTEMPTS` (5) attempts across all connections, shown by the browser in its strip or as a QR code; the phone, a NeoTeletext receiver with its own key for the channel, presents the code on its own push connection after proving its own key; and the server then records that the phone's key identifier is linked to the browser's, so that the program is given the browser's handle on the phone's connections. The browser's key MUST never reach the phone. The link MUST end when either key is forgotten, ended or expired, and MUST be held in the server's table of VS-303 with the same lifetime as the browser's entry.
- **Reason.** A phone used as a keyboard or second screen should be the same viewer to the channel without copying a secret between devices; DBSC's planned cross-origin bindings solve the same shape of problem. Today's QR keyboard pairs a phone with `neottx keyboard` through the relay and has no tie to any channel identity, so it is unaffected.
- **Source.** Research section 4.11.
- **Verification.** When built: tests of the code's bounds, expiry and attempts; a test that the phone's connection carries the browser's handle and that forgetting either ends it.

---

## 8. A future login (not built now)

**VS-801. Login binds an account to a key identifier (neoteletext-common; not built).**
- **Statement.** When sign-in is designed, a successful sign-in MUST bind the account, on the server, to the key identifier of the connection's viewer; signing out MUST unbind it and MAY end the state; each device MUST have its own key bound to the same account; a sign-in on a visit key MUST end when that key ends unless the viewer chooses "remember me"; and the key MUST NOT be the credential that signs in (a password today, passkeys later). Nothing of this is built now, and nothing in this design MUST prevent it.
- **Reason.** Owner's decision 8. WP 194 section 3.2 treats session-length sign-in as exempt and persistent sign-in as needing consent, which the two lifetimes already give. DBSC's specification separates signing in (WebAuthn) from protecting the session after.
- **Source.** Owner's decision 8; WP 194 section 3.2; research sections 2.3 and 4.10.
- **Verification.** Review when sign-in is designed.

---

## 9. Migration

### 9.1 Requirements

**VS-601. One cut-over, no compatibility shim (neoteletext-common).**
- **Statement.** The change MUST be made as one planned cut-over: push protocol 8 and program protocol 13 replace versions 7 and 12 outright; no release of any repository MUST accept both cookies and keys, and the server's dual-run of the research's section 4.13 MUST NOT be built.
- **Reason.** DEVELOPMENT.md section 2.1 forbids compatibility shims; the owner's decision 1 removes cookies entirely; one owner controls every part, so there is no installed base to wait for (research section 4.13). The cost is that every viewer's existing cookie state (a poll ballot, kept choices, a language) is lost once.
- **Source.** Owner's decision 1; DEVELOPMENT.md section 2.1.
- **Verification.** Review of each repository's release; tests of VS-201.

**VS-602. The order of change.**
- **Statement.** The repositories MUST change in this order, each by its own process, each step committed through its gates: (1) neoteletext-common: the documentation items, the wire vectors and the proposal decision; (2) the engine: the state records and messages, push protocol 8 in the agent, `StateSigner`, `--identity`, and the removal of the cookie module, the SET_COOKIE record, `persist_cookies`, `CookieStorage` and (open question Q11) the `dbsc` feature; (3) the server: program protocol 13, verification, handles, the removal of the session cookie and the server session (VS-354), RESUME, and the Cloudflare host's equivalents; (4) the browser: the pin moved to the engine's commit, the key store, the viewer's controls, and the removal of every cookie mechanism of section 1.5; (5) the TypeScript kit and (6) the Python kit, each speaking protocol 13; (7) the component library; (8) the channels: demosite, uicomponentsdemo, home-www.neoteletext.com and hackaday (library releases), audiodemo, naplpsdemo and regisdemo (per-connection state ending at `gone`), and the old Python Hackaday channel (its poll); and (9) one deployment of the server and every channel together, because a program speaking protocol 12 cannot run under a server speaking 13.
- **Reason.** Each step depends on the one before (the browser pins the engine; the kits copy the server's schema); the deployment must be atomic because the kits stop a program whose protocol differs (`streams.ts` lines 39 to 66).
- **Source.** DEVELOPMENT.md sections 2.2 and 11.
- **Verification.** The to-dos of section 9.3, each closed with its commit; the deployment's check that every channel's program reports protocol 13.

**VS-603. Existing cookies are dropped once.**
- **Statement.** At the first start of the browser release that has this design, the trusted core MUST delete `cookies.bin` and the broker MUST delete the secret store's entry "NeoTeletext cookie file", and the settings lines `cookies` and `cookie-block` MUST be dropped (the blocked channels list MUST NOT be carried over, because blocking cookies and blocking state are different choices the viewer did not make); the server MUST delete `session.key` and `session.key.previous` at its first start and the Cloudflare host its `session_key` row; the library's migration MUST drop `session_value` (VS-405). Nothing MUST be converted.
- **Reason.** Nothing in a cookie can become a key: a cookie is a value the channel chose; a key is one the browser makes. Leaving the files would keep credentials no code reads.
- **Source.** Owner's decision 1; research section 4.13.
- **Verification.** Tests: a settings folder with `cookies.bin` has none after the first start; the secret store entry is deleted (by hand on each platform, recorded with its date, since secret stores cannot run unattended); the server's state directory has no session key after start.

**VS-604. Demonstration pages about cookies are replaced (demosite and uicomponentsdemo).**
- **Statement.** The cookie areas (demosite pages 700 to 705, uicomponentsdemo pages 110 to 114) MUST be replaced by pages that show viewer state: whether this connection has a viewer and whether it is remembered, a visit counter kept under the handle, a button that asks for state, a "forget me on this channel" button that calls `endState`, and an explanation of what the channel keeps and for how long; the requirements and decision that define the cookie pages are superseded.
- **Reason.** The pages demonstrate a mechanism that no longer exists; a channel's authors need to see the new one.
- **Source.** Owner's decisions 1 and 6; REQ-3838, REQ-3186, REQ-2218 item 5, DEC-2234 (superseded).
- **Verification.** Each channel's tests with the harness's fake viewers.

### 9.2 What happens to TODO-6463's leak

The leak exists because per-viewer values are keyed by a connection number that is reused after a restart. After this change no per-viewer value is keyed by a connection number at all: values are keyed by a 128-bit handle that only the browser holding the key can cause to be presented (VS-405), and a connection without a viewer keeps nothing beyond its own life. The migration drops every row keyed by a session number. TODO-6463 is then done, with the library's tests of VS-405 and VS-406 as its tests (two tabs of one viewer share a ballot, a reconnect keeps it, a reused connection number after a restart is given nothing).

### 9.3 To-dos the main session creates on approval

One to-do for each step of VS-602 in its repository, each naming the requirements it builds and the to-dos before it; one for TODO-6444 item 2 (`gone`), folded into the server's; and one for each open question's answer to be recorded as a decision.

---

## 10. Security analysis

This is the separate analysis DEVELOPMENT.md section 2.3 requires for a feature that adds an input and an output. The inputs added: STATE_CHALLENGE, STATE_END and STATE_KEEP_OFFER to the browser and to the engine's agent; STATE_PROOF, STATE_NONE and STATE_OFFER to the server; `request_state`, `end_state` and `offer_remember` to the server from a program; the key file to the browser; the identity file to engine tools. The outputs added: the proof (a public key and a signature), and the handle given to programs.

### 10.1 What is protected

1. The private keys: possession is the viewer's identity on a channel.
2. Unlinkability: across channels always; across a reset on one channel; across private and ordinary windows.
3. The viewer's control: no state without the viewer's act, no persistence without the viewer's choice, and deletion at any time.
4. Programs' per-viewer data: reachable only by the viewer it belongs to.
5. Availability of channels without state.

### 10.2 Attackers

A thief of the viewer's disk or backups; malware running as the viewer; someone on the network (passive or active, on encrypted and unencrypted connections); a hostile channel server or program; a hostile fetcher (a fetcher compromised by its channel's server); a hostile interface process; another viewer of the same channel; anyone on the internet able to open connections; an attacker who obtains a channel program's data or the server's state directory.

### 10.3 Threats, mitigations and residual risk

| # | Threat | Mitigation | Residual risk, accepted or not |
|---|---|---|---|
| 1 | **Theft at rest**: the key file copied (backup, another user, a disk read offline) | Visit keys are never written (VS-105). Remembered keys are sealed with ChaCha20-Poly1305 under a key in the platform's secret store (VS-108); mode 0600 in a 0700 folder. | Malware running as the viewer can ask the secret store as the browser does and copy remembered keys. Accepted: every browser has this limit today; only a hardware key fixes it (section 12). |
| 2 | **Theft on the wire** | No secret ever travels: only a public key and a signature over a fresh challenge (VS-203, VS-116). | None for the key. On an unencrypted connection, the public key and the handle's existence are visible (row 9). |
| 3 | **Replay** of a captured proof | The challenge is fresh, single-use and bound to one connection for `STATE_ANSWER_MS` (VS-205), and the signed bytes name the version and channel (VS-203). | None, on encrypted and unencrypted connections alike. |
| 4 | **Relay**: a hostile channel B passes channel A's challenge to the browser on B's connection | The browser signs with B's key over bytes naming B (VS-102, VS-103); A's server verifies against A's identity and finds neither its key nor its name. | None. |
| 5 | **Hijack** of a live connection after its proof | On an encrypted connection, TLS protects it. | On an unencrypted connection an active network attacker can take over a connection after it has been proven and act as the viewer on that connection until it closes. Accepted by owner's decision 5, and shown by the "Not secure" badge (VS-115). The attacker cannot obtain the key or prove on a new connection. |
| 6 | **Fixation**: an attacker plants their own identity in the viewer's browser | The browser alone makes keys (VS-101); no message carries a key or a value to store; STATE_END only deletes, and only a matching key (VS-204). | None. The analogue of cookie fixation does not exist. |
| 7 | **Guessing** a handle or a key | Keys are Ed25519 from the system's random source; handles are 128 bits of HMAC output; a handle is never accepted from a client, only derived by the server (VS-305, VS-353). | None. Knowing a handle (for example from a leaked program log) gives no way to present it. |
| 8 | **Cross-channel linking** | One key per channel identity (VS-102); handles keyed per channel (VS-305); the key identifier never leaves the server. | Two channels run by one operator on one server could, in their programs, compare network addresses and times, as with any other web service. Not addressable by this mechanism. A server operator who reads the server's memory sees key identifiers, which are the same for one key; but one key is only ever used for one channel identity, so this links nothing across channels. |
| 9 | **Tracking on an unencrypted network**: a passive observer recognises the same public key on later connections | None beyond the badge. | Accepted by owner's decision 5: on `http` channels a network observer can recognise the browser across visits to that channel while its key lasts. The observer cannot impersonate it (rows 2 and 3) and cannot link it to the same viewer's key on another channel. |
| 10 | **A hostile channel program** | It sees only a handle (VS-351); it cannot create state without a gesture (VS-212), cannot extend a lifetime or choose a value (VS-353), and can only end state or suggest remembering. Challenges are bounded per connection (VS-205). | A program can keep a visit's data and use it against the rule of VS-409; only the rule and the privacy page constrain that. |
| 11 | **A hostile server** | It can request challenges only on its own channel's connections; the browser signs only for that channel (VS-103) and creates keys only after a gesture (VS-104), at most `MOST_PROOFS_PER_FETCHER_PER_MINUTE`. | A hostile server recognises the viewer on its own channel while the key lasts; that is the purpose. It learns nothing of other channels. |
| 12 | **A hostile fetcher** | It never holds a key; it can ask the core only to sign challenges for its own tab's channel, at a bounded rate; the core builds the signed bytes (VS-103, VS-119). It could ask for a key to be created; the core still checks the gesture, which the core alone sees. | It can obtain signatures for its own channel, which its own channel's server could obtain anyway. |
| 13 | **A hostile interface process** | The viewer's controls act by view numbers (VS-112); no key material is ever sent to it (VS-116). | It can forget or block channels it was shown, which loses state but reveals nothing; "Remember me" is strip input (REQ-675's exception for the strip), so it cannot remember a key the viewer did not choose. |
| 14 | **Storage exhaustion**: a flood of fresh identities | Server: table bounded (VS-303) and new identities per address bounded (VS-304). Library: per-handle bounds and idle expiry (VS-405). Browser: keys bounded at `MOST_KEYS_PER_JAR` (3,000, the cookie total's bound) and the key file at `MAX_KEY_FILE_BYTES` (4 MiB: 3,000 entries of at most 523 + 32 + 24 bytes, encoded, with room). | A distributed attacker with many addresses can fill the server's table, which evicts least recently seen viewers; they reprove on their next connection and lose nothing (VS-303). |
| 15 | **Timing side channels** | Signing and verification use constant-time implementations (`ring`'s; the server's library chosen under Q7 must be constant-time); no secret is compared by the server. The core's answer time does not depend on whether a key exists, because the core answers STATE_NONE after the same path. | Whether a key exists is visible anyway from the answer itself, by design. |
| 16 | **Malformed messages** | Every message has a fixed length and enumerated values (VS-204); fuzz targets on every reader: the receiver's state records, the server's state messages, the core's fetcher messages, the key file and the identity file. | Ordinary fuzzing residual. |
| 17 | **Downgrade between protocol versions** | Version 7 refused both ways (VS-201); the version is signed (VS-203); no fallback to cookies exists in any client. | None. |
| 18 | **Bounce tracking**: a channel only passed through in a redirect gains state | A key is made only after a gesture on a shown page (VS-104). | None. |
| 19 | **Copied profile** | Sealed under the secret store; a copy without it yields no keys (VS-118). | A copy with the secret store (a whole-machine migration) duplicates keys. Accepted until hardware keys (section 12). |
| 20 | **Abuse**: a viewer makes fresh identities to vote again | Rate limit per address (VS-304); polls labelled per visit or per browser, not per person; sign-in where one per person matters. | Not solved, by design: a reset that cannot be undone is the point of the reset (owner's decision 9). |
| 21 | **Races between tabs** | Atomic transactions in the store (VS-406); ordered events in the server. | None, once VS-406 is built. |
| 22 | **Logs and crash reports** | Nothing of the mechanism logged (VS-209). | A program's own logs are its author's; the rule of VS-409 applies. |
| 23 | **A breach of a program's data or the server's state directory** | Data holds handles only; the handle secret can be rotated (VS-306), severing every handle. | Before rotation, a thief of the handle secret and of key identifiers (which exist only in server memory) could relate handles; with only the secret, nothing. |

### 10.4 Findings applied to the design

The table's mitigations are already requirements above. Three came from the analysis itself: the `key_id` in STATE_END (row 6, a delayed end must not delete a newer key); the gesture checked in both the server and the core (rows 11 and 12); and the identical STATE_NONE path in the core whether or not a key exists (row 15).

### 10.5 Findings outside this design, met while reading the code

These are for the main session to record; they are not requirements of this document.

1. The Cloudflare host accepts viewer push connections without the `Origin` check and subprotocol check the native host makes (`crates/teletext-cloudflare/src/lib.rs` line 470 goes straight to `accept_viewer`; the native host's `landing::push_upgrade` refuses any `Origin` with 403).
2. The browser's fetcher draws WebSocket masking keys from `RandomState` and a counter (`native/fetcher/src/agent.rs` lines 15 to 40), not a cryptographic source; RFC 6455 section 5.3 requires masking keys that cannot be predicted.
3. Two fuzz targets that `docs/cookies.md` section 11 lists (`cookie_messages`, `cookie_requests`) were never written. This design deletes what they would have fuzzed, and names its own targets.
4. The server has no rate limit of any kind on connections (only the bound on waiting sessions and the per-receiver input rate).

---

## 11. Privacy and law

**This section is not legal advice. It is written for review by a lawyer before anything in it is relied on.** It records how the design was shaped by the sources the research read, and what it still requires.

### 11.1 The position

1. **The mechanism is in the scope of the ePrivacy Directive, article 5(3), exactly as a cookie is.** EDPB Guidelines 2/2023 (version 2.0, 7 October 2024) read "information" to include non-personal data (paragraph 12), treat information stored by one party and later accessed by another as in scope (paragraph 31), treat instructing a device to send stored information "through the use of a protocol" as gaining access (paragraph 34), and put unique identifiers in scope (paragraphs 61 to 63). A key the browser makes and a proof the server's challenge causes it to send are therefore storage and access under article 5(3). The guidelines expressly do not decide exemptions (paragraphs 4 and 56).
2. **The visit key is designed to fall within the exemption for what is strictly necessary for a service the viewer explicitly requested.** WP 194 (7 June 2012) section 3.1 exempts "user-input" identifiers relying on "a random temporary unique number" that expire when the session ends at the latest; section 3.2 exempts authentication for a session; section 2 says an exempt identifier must have a lifespan in direct relation to its purpose and expire once not needed. The visit key is made only after the viewer acts (VS-104, VS-212), only for the channel the viewer is using (VS-102), held in memory, and ends when the browser closes or at its idle and absolute limits (VS-106). A multi-purpose identifier is exempt only if every purpose is (WP 194 section 2.4), which is why VS-409 restricts the purposes.
3. **The remembered key is not exempt and relies on the viewer's choice.** WP 194 section 3.2: persistent login cookies "are not exempted under CRITERION B", and "a checkbox and a simple information note such as 'remember me (uses cookies)' next to the submit form would be an appropriate means of gaining consent". VS-109 makes "Remember me on this channel" exactly such a choice, off by default, made in the browser's own interface, informed, specific to one channel, and withdrawable at any time (VS-112).
4. **So the design aims for no consent banner** on NeoTeletext's own channels and the demonstration channels: the visit key needs none, and the remembered key's consent is the viewer's explicit choice in the browser.
5. **The handle is personal data under the General Data Protection Regulation.** It is an online identifier relating to a viewer (GDPR article 4(1) and recital 30; *from memory, not re-read in this work*). It is pseudonymous, not anonymous. A channel operator that keeps data under a handle is a controller of it.

### 11.2 Requirements

**VS-701. The legal section is reviewed before release (neoteletext-common).**
- **Statement.** Before the release of VS-602 step 9, this section, the wording of VS-109 and the privacy pages of VS-702 MUST be reviewed by a lawyer competent in European Union and Australian privacy law (and in the law of any other place the owner names), and the review's outcome recorded as a decision.
- **Reason.** Owner's decision 7. The sources read are guidance, not law, and do not settle the questions of section 11.3.
- **Source.** Owner's decision 7.
- **Verification.** Review, recorded.

**VS-702. A privacy page.**
- **Statement.** NeoTeletext's own website and each channel the project operates MUST publish a privacy page, reachable from the channel's index, that states in plain language: what a viewer handle is and that it is personal data; what the channel keeps under it and why (only the purposes of VS-409); for how long (the store's limits); that the viewer can forget the channel in the browser at any time, and can delete what the channel keeps at once with the channel's "forget me" page (which calls `endState` and deletes the viewer's values); who the controller is and how to contact them; and the viewer's rights of access and erasure (GDPR articles 13, 15 and 17; *from memory*). Each kit's guide MUST tell channel authors that their channels need the same.
- **Reason.** Owner's decision 7: no consent banner, but transparency and deletion are still required.
- **Source.** Owner's decision 7.
- **Verification.** Review of each page; the "forget me" page's test with the harness.

**VS-703. The rule binding channels is in the protocol documentation.**
- **Statement.** The protocol's documentation item for viewer state MUST state VS-409's rule as normative text that every channel author is bound by.
- **Reason.** Owner's decision 7.
- **Source.** Owner's decision 7.
- **Verification.** Review of the documentation item.

**VS-704. What a page's rule table lets a channel learn (neoteletext-common).**
- **Statement.** The protocol's privacy rules are these, for the page rule table of `page-rules.md` in its second form (DEC-6587, DEC-6599, DEC-6635), and the protocol's documentation items on input MUST state them as normative text that every channel author is bound by. A page here is one page number and one sub-code together (RULE-112): what is said of a page is said of each sub-page alone.
  1. **Nothing is sent unless the page asks.** A channel receives a viewer's input on a page only through that page's rule table: an input event leaves the receiver only when a rule of the open page's table, fired by that event, runs a group that applies a `REPORT` command of the firing in that event's own handling (REQ-6523; RULE-22, RULE-50, RULE-52). A page with no table is sent nothing of what its viewer does, and a group run by a timer, a sequence, a cue or a command of the server's can report no input event at all.
  2. **What the report command reveals.** A `REPORT` of a firing that the viewer's own input caused carries that event on that page: the key and its modifiers, the text typed, pasted or composed, the pointer's button and position and the control, object or rectangle it was on, the wheel, the gain or loss of the keyboard, with the page tick it belongs to and the rule and row that fired. A `REPORT` of a value carries one number the table reads: one of the page's sixteen variables (which the viewer's keys and clicks may have changed), a key's or a button's state, a timer, a sequence's state, whether an object is shown and where it is, a value of the firing (the key that fired it, the target, the row, the cue), a sound's level or a synthesizer's state on that page. A bare firing says that a rule fired and when.
  3. **What the state query reveals.** The answer to a state query (RULE-38, RULE-47) carries, once, the page's sixteen variables, its timers, its sequences (running, waiting, their passes and positions), for each control and object the table names whether it exists and is shown and its look, frame, position, layer, order and cycling, and the present reading of every value the table reads. It is what the viewer's actions on that page have made of the page's local state, at one tick. It is for reading and debugging, never for restoring a page.
  4. **To whom.** All of these go to that page's own channel, on the connection that page was fetched on, and to no one else: not to another channel, not to another sub-page's or page's channel in another tab, not to any third party. The trusted core builds every report itself from the viewer's own event and gives it only to that channel's connection (RULE-52). No report carries the viewer's volume or mute, anything of another tab, or anything typed outside the open page's picture (RULE-32, RULE-51, RULE-58).
  5. **What a channel may do with them.** A channel's program MUST use what the report command and the state query give it only to provide what the page offers the viewer, under the same rule that binds its use of a viewer's handle (VS-409): not for advertising, profiling, analytics beyond aggregate counts, or sharing with any other party. What it keeps of them under a handle is personal data, as the handle is (section 11.1, item 5), and is described on the channel's privacy page (VS-702).
  6. **A page asks for no more than it uses.** A channel MUST NOT give a page a table that asks for input the page does not use. A channel that runs on the server's default table (`default_rules` `send_all`, RULE-53) is sent every input on every one of its pages until its pages have tables of their own, which is why each such channel is to move to its own tables (RULE-53, RULE-54).
  7. **Nothing of a page is kept after it is left.** Neither side keeps a page's local state after the page is closed or its connection ends (RULE-111): the receiver drops the page's table, its variables, timers, sequences and waiting events, its animation state and its local sounds, and discards every report not yet acknowledged when a connection ends, never sending it on a later one; the server forgets the names of the page's table, its generation counter, its timelines and its unanswered state queries, and keeps no table, animation state or local state for a later or returning viewer (RULE-40). A page in a tab that is not the active one is paused: it evaluates nothing, sounds nothing and reports nothing until the viewer brings it forward.
- **For the browser's privacy page, in the viewer's terms.** "A page is sent what you type or click on it only if the page asks for it, and only that page's own channel receives it. A page can also be asked by its channel what state you have left it in: the settings you changed on it and what it is showing. Nothing you do on one page is sent to any other channel, a page that asks for nothing is sent nothing, and nothing of a page is kept once you leave it or your connection ends."
- **Reason.** DEC-6522 item 12 (the owner, 18 November 2026): the state query and the report reveal what the viewer did on the page to the page's own channel only, and the protocol's privacy rules state this. Item 5 extends VS-409 because the rule cannot be enforced by code; item 6 is REQ-6523's purpose turned on the channel; item 7 is DEC-6587 item 3 (the owner: "after a disconnect i think EVERYTHING should be dropped and the page reloads"). *Revised on 19 November 2026 for the second form: the first form's `send` and `echo` actions are the `REPORT` command (RULE-22), the state query no longer reports which rules are enabled (enabling is withdrawn, DEC-6587 item 8), and item 7 is new.*
- **Source.** DEC-6522 item 12; DEC-6587 items 3 and 8; DEC-6599; REQ-6523; REQ-6615; `page-rules.md` RULE-22, RULE-38, RULE-47, RULE-52, RULE-81, RULE-111.
- **Verification.** Review of the generated protocol document's item on the rule table's privacy rules, of each kit's guide and of the browser's privacy page.

### 11.3 Questions for the lawyer

1. Is a visit key made after a gesture and limited as VS-106 says "strictly necessary" for each of the purposes of VS-409 (a poll's one vote, kept choices, a language), or only for some?
2. Does a choice made in the browser's interface, not on the channel, count as the channel operator's consent under article 5(3) and the GDPR's conditions for consent? (Kari Hurtta's proposal of April 2019 in the HTTP working group, to delegate ePrivacy consent to a mechanism outside the site, is the nearest precedent the research found.)
3. What lawful basis under GDPR article 6 should the project's channels state for data kept under a handle?
4. Do Australia's Privacy Act 1988 and its Australian Privacy Principles, and the United Kingdom's PECR and UK GDPR, change any of this? The research did not examine any law outside the European Union.
5. Is a public key seen by a network observer on an unencrypted connection (section 10.3 row 9) a disclosure the privacy page must mention?

### 11.4 Sources for this section

EDPB Guidelines 2/2023 on the technical scope of article 5(3) of the ePrivacy Directive, version 2.0, 7 October 2024, <https://edpb.europa.eu/system/files/2024-10/edpb_guidelines_202302_technical_scope_art_53_eprivacydirective_v2_en_0.pdf> (read in the research, pages 4 to 10 and 14 to 15). Article 29 Working Party, Opinion 04/2012 on Cookie Consent Exemption (WP 194), 7 June 2012, <https://ec.europa.eu/justice/article-29/documentation/opinion-recommendation/files/2012/wp194_en.pdf> (read in the research, pages 5 to 8). K. Hurtta, HTTP working group, 27 April 2019, <https://lists.w3.org/Archives/Public/ietf-http-wg/2019AprJun/0072.html> (read in the research). The GDPR's articles are cited from memory and were not re-read.

---

## 12. What is left out

| Left out | Why | When to reconsider |
|---|---|---|
| **Keys held in hardware** (the Secure Enclave, a TPM, Android StrongBox), reached through the broker | They are the only answer to malware copying keys and to copied profiles (section 10.3 rows 1 and 19), but each platform's key store needs libraries the owner has not approved (DEC-1425, TODO-3073), and the common hardware stores sign with P-256, not Ed25519 (open question Q1). | When the owner approves the key-store libraries, or when DBSC's software and cross-platform support (research section 2.3) shows the way. |
| **A login** | Owner's decision 8: designed later; VS-801 only keeps the way open. | When a channel needs accounts. |
| **Anti-abuse beyond sign-in** (anonymous rate-limited tokens of the Privacy Pass kind, RFC 9576 to RFC 9578) | It needs an issuer and attestation, a large addition (research section 4.12, option 4). | If polls or games must be fair per person without sign-in. |
| **Rotation that keeps continuity** (an old key signing a new one) | Continuity and privacy pull in opposite directions; nothing here needs it (research section 4.7). | If hardware keys arrive and need re-keying without losing viewers. |
| **Partitioning by an embedding context** | NeoTeletext pages embed nothing, so there is no third party (the browser's `cookies.md` section 1). | If embedding is ever added: an embedded channel's key must then be keyed by the pair of top-level and embedded channel, as CHIPS and Total Cookie Protection do. |
| **Identity shared between channels** (federated sign-in) | Channels must not relate one another's handles (owner's decision 3). | If a browser-mediated sign-in like FedCM is wanted. |

---

## 13. Open questions for the owner

Each with its options and a recommendation.

**Q1. The key type: a reason against Ed25519 was found.**
- *What was found.* The engine's Device Bound Session Credentials use ES256, ECDSA on P-256 (`crates/neoteletext-web/src/dbsc.rs` line 42), because the hardware key stores this design leaves for later sign with P-256: Apple's Secure Enclave offers P-256 only, and TPM 2.0 and Android's StrongBox are commonly limited to P-256 among elliptic curves (*from memory, not re-checked*). `p256` 0.14.0 is already in the engine's and the browser's lockfiles (through `neoteletext-qrkeyboard`), and `ring`, already approved in the browser, signs and verifies both Ed25519 and ECDSA P-256. Changing the key type later means every viewer gets a new key and a new handle once.
- *Options.* (a) Ed25519 now, as decided; when hardware keys come, add algorithm 2 (ES256) in a new protocol version and accept one loss of state for viewers who move to hardware keys. (b) ES256 now, so that hardware keys later need no change of algorithm or handle. ES256 signatures need a random or derived nonce (RFC 6979 makes it deterministic), are slower, and cost more code on a microcontroller.
- *Recommendation.* (a), Ed25519 now: hardware keys have no date, Ed25519's deterministic signatures cannot fail through a weak random nonce, and it is the cheaper choice for microcontrollers. The algorithm byte in VS-203 and VS-204 keeps the change open.

**Q2. The lifetimes and caps.**
- *Options and recommendation.* Visit key: idle 12 hours, absolute 7 days (VS-106); alternatives are HTTP State Tokens' one hour (strict, but a viewer away for lunch loses their poll ballot) or "until the browser closes" with no limit (simplest, but a browser left running becomes persistent). Remembered key: idle 180 days, absolute 400 days (VS-107); 400 days is RFC 6265bis's cap. Library values: a visit handle's values 24 hours after last use; a remembered handle's at the remembered idle limit (VS-405). Server table: 5 minutes after the last connection (VS-303).

**Q3. Does a channel's key cover folders below it?**
- *Options.* (a) No: exact channel identity, as cookies today and HTTP State Tokens. (b) Yes, as Gemini's certificates cover paths below.
- *Recommendation.* (a). A folder inside a channel's folder is often another person on a shared host (REQ-5505).

**Q4. Where "remember me" is offered.**
- *Options.* (a) Only from the browser's menu. (b) Only when the channel sends STATE_KEEP_OFFER. (c) Both: always in the menu, and as a dismissible strip notice when the channel offers, at most once per channel per browser run.
- *Recommendation.* (c). The channel knows the moment (after a sign-in or a language choice); the menu keeps the viewer's control when the channel never offers.

**Q5. Hardware keys now or later.** *Recommendation:* later (section 12), after Q1 and the owner's approval of key-store libraries (DEC-1425).

**Q6. Anti-abuse beyond sign-in.** *Options:* label polls per visit; rate limit per address (VS-304, built); require sign-in for what must be one per person; Privacy Pass tokens. *Recommendation:* the first three, not Privacy Pass.

**Q7. The server's signature library.** The server has no cryptography crate today (its HMAC is hand-written over the engine's SHA-256). *Options:* (a) `ring` 0.17.14, already approved in the browser and in the engine's lockfile through `rustls`, constant-time, and (from memory, to be checked) able to build for the Cloudflare host's `wasm32-unknown-unknown`; (b) `ed25519-dalek`, a new library; (c) an Ed25519 verifier written in the engine like its SHA-256, which is not recommended for curve arithmetic. *Recommendation:* (a), subject to a build of the Cloudflare host with it. Each needs the owner's approval by name (REQ-161).

**Q8. Signing in the engine's tools and on microcontrollers.** *Options:* `neottx` signs with `ring` (already in its tree through `rustls`); microcontrollers stay stateless until a `no_std` signer is measured and approved (VS-504). *Recommendation:* both.

**Q9. The server session.** Removing the `_session` cookie removes the server's session, which today continues a viewer's tabs across a drop and ends them together five minutes after the last closes. *Options:* (a) as VS-354: no server session; RESUME (DOC-1923) for a dropped connection; `gone` per connection. (b) Keep a server session keyed on the key identifier when there is one, and on nothing otherwise. *Recommendation:* (a). Since DEC-6443 the kits already treat each connection as its own; (b) would give two behaviours depending on whether the viewer has state.

**Q10. The engine's cookie jar for web servers that are not NeoTeletext servers.** The engine's agent also reads static channels from ordinary web servers, which may set cookies. *Options:* (a) delete the cookie module entirely; such a server's cookies are ignored. (b) Keep it for non-NeoTeletext servers. *Recommendation:* (a), as owner's decision 1 says: nothing a channel writes is stored or parsed; a static channel needs no state.

**Q11. The engine's Device Bound Session Credentials.** They bind cookie sessions, which no longer exist. *Options:* (a) delete the `dbsc` feature now (REQ-WEB-017, REQ-506, DEC-634 and TODO-1209, TODO-1252 and TODO-3073 superseded), and design hardware keys afresh for viewer keys; (b) keep it. *Recommendation:* (a); its `DeviceKeys` port trait is the pattern to reuse.

**Q12. The numeric bounds.** `STATE_ANSWER_MS` 10,000; `MOST_CHALLENGES_PER_CONNECTION_PER_MINUTE` 6; `MOST_PROOFS_PER_FETCHER_PER_MINUTE` 60; `STATE_OFFER_INTERVAL_MS` 10,000; `MOST_VIEWERS_PER_CHANNEL` 262,144; `MOST_NEW_VIEWERS_PER_ADDRESS_PER_HOUR` 600 (high enough for many viewers behind one carrier-grade address). *Recommendation:* these values, each to be measured under `teletext-load` before release.

**Q13. A "known" mark in the strip.** *Recommendation:* yes (VS-114).

**Q14. The phone companion.** *Options:* build VS-505 with this change, or later. *Recommendation:* later; it adds a pairing protocol and nothing today needs it.

**Q15. `--no-keychain` and "remember me".** *Recommendation:* unavailable without the keychain, as cookies are kept for the run only today (decision 113; VS-108).

**Q16. The global "Never" setting.** *Recommendation:* offer it, default Allow (VS-112).

**Q17. Privacy pages.** *Options:* one page on the project's website that each project channel links to, or a page in each channel. *Recommendation:* a page in each channel (a NeoTeletext viewer reads the channel, not the website), with the website's page for the browser itself (which sends the project nothing).

---

## 14. Differences from what is built today, per repository

### 14.1 neoteletext-renderer-teletext (the engine)

- **Removed:** the cookie module and its submodules; `agent/cookies.rs`; `Set-Cookie` reading in `fetch.rs` and `push.rs`; the `Cookie` header on the push handshake; the SET_COOKIE record (`records/cookie.rs`) and its handling in `push_data.rs`; `persist_cookies`; `CookieStorage`; the `cookies` feature in `xtask` builds; and, under Q11, `dbsc` with `agent/bound.rs` and its tests and fuzz target. Constants `MAX_COOKIE_AGE_DAYS`, `DEFAULT_COOKIES_PER_HOST`, `DEFAULT_COOKIES_TOTAL`, `MAX_COOKIE_NAME_VALUE` and `MAX_COOKIE_ATTRIBUTE_VALUE` go with it.
- **Added:** records 18 to 20 and the receiver's extension messages 0x48 to 0x4A of VS-204, with readers, writers and fuzz targets; push protocol 8 in HELLO and WELCOME (subprotocol `neottx.8`); `MAX_CHANNEL_IDENTITY_BYTES` and the signed-bytes builder of VS-203 (one implementation, used by the browser and the server); the `StateSigner` port trait; `neottx --identity` (VS-502); wire vectors.
- **Changed:** `neottx`, `neottx keyboard` and the firmware test image answer STATE_NONE `stateless`.

### 14.2 neoteletext-browser

- **Removed:** everything in section 1.5's browser table: the jar, `cookies.bin` and its key, the `CookieKey` broker request, the fetcher's `CoreCookies` and its six messages, the cookies view and request, the Cookies tab of the developer console, the settings' Keep, Close and Block and the blocked list, the Cookies switch of clearing with history, `Clear-Site-Data` handling, `reached_securely` (the cookie-based answer to "was this host reached securely", engine REQ-SEC-007, which must be answered another way or withdrawn: the main session to record it), the `cookie_file` fuzz target, and `docs/cookies.md` and `docs/cookies-security.md` (their rules carried into rdm or withdrawn).
- **Added:** the key store in the trusted core (VS-101 to VS-111); `viewer-keys.bin` and its secret store entry (VS-108); the fetcher and core state messages (VS-119); "Channels that know you" in the settings, "Remember me on this channel" in the menu and the strip, the strip's mark, the global setting, and forgetting with history (VS-109, VS-112, VS-114); fuzz targets `viewer_key_file` and `state_messages`.
- **Unchanged:** the "Not secure" badge; private windows' lifetime; the channel identity computation (`Channel::of`, `address.rs`).

### 14.3 neoteletext-app-server

- **Removed:** `session_cookie.rs` and its fuzz target; `Cookies`, `session_for` and the `Cookie` reading in `http.rs`; `session.key`, `session.key.previous`; the server session, `MOST_WAITING_SESSIONS` and the five-minute grace for sessions; `Connected.session`, `Connected.cookies`, `CookiePair`, `Closed`, the program's `Cookie` message, `check_cookie`, `COOKIE_BYTES`, `MOST_COOKIES`; `records::cookie`; the Cloudflare host's `SESSION_KEY` and cookie handling.
- **Added:** program protocol 13 and `schema-13.json` (VS-351, VS-352); challenges, verification and the key identifier (VS-205, VS-301, VS-302); the in-memory viewer table and its bounds (VS-303, VS-304); the handle and `viewer-handle.key` (VS-305); the rotation command (VS-306); RESUME and `gone` (VS-354); a signature library (Q7).

### 14.4 neoteletext-server-ts-protocol (the TypeScript kit)

- **Removed:** every cookie item of section 1.5; `Tabs` and the server session (since there is none); `closed(session)`.
- **Added:** protocol 13 types generated from the schema; `viewer`, `requestState`, `endState`, `offerRemember`, the four events, `gone`; the harness's fake viewers (VS-404). A major release (15.0.0).

### 14.5 neoteletext-server-channels (the Python kit and the old Hackaday channel)

- **Removed:** every cookie item of section 1.5; handlers given the server's session.
- **Added:** the same calls and harness as the TypeScript kit; per-connection presentation (TODO-6445 item 1). The old Hackaday channel's poll keys on the viewer handle, and its viewer state per connection.

### 14.6 neoteletext-server-ts-ui-components (the component library) and the channels

- **Library removed:** `ViewerCookies`, the cookie services, `LANGUAGE_COOKIE`; `session_value`; `ofSession`, `keepForSession`. **Added:** `viewer_value`, `ofViewer`, `keepForViewer`, `update`, transactions (VS-405, VS-406); automatic state requests (VS-407); language under the handle (VS-408). A major release (23.0.0).
- **demosite and uicomponentsdemo:** cookie pages replaced (VS-604); language and polls through the library; uicomponentsdemo's page 304 keeps choices under the handle, and its two texts that TODO-6463 names become true.
- **home-www.neoteletext.com, hackaday:** take the library's release.
- **audiodemo, naplpsdemo, regisdemo:** their per-session maps become per-connection, ended at `gone`.

### 14.7 rdm records that this design supersedes or changes (for the main session)

- **Superseded:** DOC-1924 and DOC-1957 (replaced by new documentation items); DOC-2312 and DOC-2032; the browser's REQ-879, REQ-715, REQ-880 to REQ-889, REQ-3398, REQ-3400, REQ-3924, REQ-4152, REQ-4153, REQ-4847, REQ-3929, REQ-2902, REQ-3537 and DEC-955 (decision 62), DEC-1765, TODO-1248; the engine's REQ-495, REQ-5156 to REQ-5171, REQ-2657, REQ-2658, REQ-2660, REQ-3668, REQ-502, DEC-559, DEC-628 and (under Q11) REQ-506, DEC-634, TODO-1209; the server's REQ-1040, REQ-2963, DEC-2024 items 3 and 4, DEC-2145, TODO-4900, DEC-5583, TODO-2055 item 3; the library's REQ-2217; demosite's REQ-3838, REQ-3186 and DEC-2234.
- **Revised:** DOC-1951 (record types 18 to 20 added, the table completed with types 13 to 17, which the engine already uses, and type 8 retired), the input protocol's documentation item of extension events (types 0x48 to 0x4A), DOC-1968 and DOC-1970 (program protocol 13), DOC-1863 and REQ-1883 and REQ-515 (the boundary is for keys, not cookies); DEC-910 item 1, DEC-1527 item 4, DEC-6443 items 2 and 3, REQ-714 and REQ-1471 item 9; REQ-1057 and REQ-1058 and DEC-2463 items 4 to 6 (keyed by handle); REQ-2218 item 5.
- **Done by this design once built:** TODO-6463; TODO-6444 (item 1 by RESUME, item 2 by `gone`); TODO-6445.

---

## 15. Conflicts found in the code and in rdm

1. **The key type** (Q1): the engine's DBSC and the hardware stores use P-256; the owner's decision names Ed25519.
2. **The server has no cryptography library** (Q7): Ed25519 verification needs one approved by name.
3. **The server session rests on the cookie** (Q9): resumption, the five-minute grace and `closed` all depend on `_session`; DOC-1923's RESUME is not built in the server.
4. **Kit version.** DEC-6443 and TODO-6463 say the per-tab change is kit 13.0.0; the kit is now at 14.0.0 (commits `5eebd42` "Release 14.0.0" and `6d54c3d` "Speak protocol 12").
5. **The kits are not equal today.** The Python kit gives handlers the server's session shared by tabs; the TypeScript kit gives each connection (TODO-6445; DEC-6462 item 3 requires equality).
6. **Requirements that require cookies:** demosite's REQ-3838 and REQ-3186, DEC-2234, REQ-2218 item 5, and the library's REQ-2217 require cookie pages and cookie services; DEC-910 item 1, DEC-1527 item 4 and DEC-6443 item 3 say tabs share cookies.
7. **The engine's general web use** (Q10): the engine's jar also serves ordinary web servers; owner's decision 1 removes it.
8. **The library's store is not atomic**, against owner's decision 9 (VS-406).
9. **Cloudflare host gaps:** no `Origin` check (section 10.5 item 1), no cookies passed to programs (TODO-4900), one session key and no rotation.
10. **`reached_securely`** (the engine's REQ-SEC-007 as the browser answers it) is computed from cookie jars; with no cookies it needs another source or withdrawal.
11. **The push protocol's number** (settled by DEC-6477). This document first said the push protocol was version 2 and made it 3; the engine's is version 7 (`neoteletext_input::limits::VERSION`, subprotocol `neottx.7`), so this design makes it 8 (VS-201, VS-203), as the engine's branch `viewer-state` builds it (commit `af9f6b5d`).
12. **The record types** (settled by DEC-6477). This document first allocated record types 13 to 15, which the engine already uses (13 kept for CHANNEL, 14 REGIS, 15 DRAWING_LINKS); the state records take the next free types, 18 to 20, and the receiver's messages the extension types 0x48 to 0x4A (VS-204), as the engine's branch `viewer-state` builds them (commit `793039e5`).
13. **One program protocol 13 with the synthesizers** (settled by DEC-6477 answer 3). `audio/server.md` defines the synthesizers' sound messages in the same version; section 5.3 states the names each adds, none shared.

---

## 16. Sources

**The research report** of 18 November 2026, *Session state for NeoTeletext without cookies: history, clean restarts, and a recommendation*, whose sources, as it records them, are:

- D. Kristol, "HTTP Cookies: Standards, Privacy, and Politics", 2001: <https://ar5iv.labs.arxiv.org/html/cs/0105018>.
- RFC 6265, "HTTP State Management Mechanism", April 2011: <https://www.rfc-editor.org/rfc/rfc6265.html>.
- draft-ietf-httpbis-rfc6265bis: <https://datatracker.ietf.org/doc/draft-ietf-httpbis-rfc6265bis/>; draft-ietf-httpbis-layered-cookies: <https://httpwg.org/http-extensions/draft-ietf-httpbis-layered-cookies.html>.
- WebKit, "Full Third-Party Cookie Blocking and More", March 2020: <https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/>.
- Mozilla, "Firefox rolls out Total Cookie Protection by default to all users", 14 June 2022: <https://blog.mozilla.org/en/products/firefox/firefox-rolls-out-total-cookie-protection-by-default-to-all-users/>.
- Chrome, CHIPS: <https://developer.chrome.com/docs/privacy-sandbox/chips/>; bounce tracking mitigations: <https://developer.chrome.com/docs/privacy-sandbox/bounce-tracking-mitigations>.
- Privacy Community Group, Storage Access API: <https://privacycg.github.io/storage-access/>; W3C FedCM: <https://w3c-fedid.github.io/FedCM/>.
- M. West, draft-west-http-state-tokens-00, 28 March 2019: <https://datatracker.ietf.org/doc/html/draft-west-http-state-tokens-00>; explainer: <https://github.com/mikewest/http-state-tokens>; status message of 8 April 2021: <https://lists.w3.org/Archives/Public/public-privacycg/2021Apr/0006.html>.
- K. Hurtta, HTTP working group, 10 and 27 April 2019: <https://lists.w3.org/Archives/Public/ietf-http-wg/2019AprJun/0026.html>, <https://lists.w3.org/Archives/Public/ietf-http-wg/2019AprJun/0072.html>.
- RFC 8471, Token Binding Protocol 1.0: <https://www.rfc-editor.org/rfc/rfc8471.html>; N. Harper, "Intent to Remove: Token Binding", 1 August 2018: <https://groups.google.com/a/chromium.org/g/blink-dev/c/OkdLUyYmY1E/m/w2ESAeshBgAJ>; E. Lawrence, "Protecting Auth Tokens", 23 October 2023: <https://textslashplain.com/2023/10/23/protecting-auth-tokens/>.
- W3C, Device Bound Session Credentials, Editor's Draft of 9 November 2026: <https://w3c.github.io/webappsec-dbsc/>; Google Security blog, 9 April 2026: <https://security.googleblog.com/2026/04/protecting-cookies-with-device-bound.html>.
- RFC 9449, OAuth 2.0 DPoP: <https://www.rfc-editor.org/rfc/rfc9449.html>.
- Gemini protocol specification 0.24.1: <https://geminiprotocol.net/docs/protocol-specification.gmi>; technical overview: <https://geminiprotocol.net/docs/tech-overview.gmi>.
- RFC 9576 and RFC 9578, Privacy Pass: <https://www.rfc-editor.org/rfc/rfc9576.html>, <https://www.rfc-editor.org/rfc/rfc9578.html> (search only).
- EDPB Guidelines 2/2023, version 2.0, and WP 194, as in section 11.4.
- Oryx Embedded, CycloneCRYPTO benchmark on STM32F0: <https://www.oryx-embedded.com/benchmark/st/crypto-stm32f0.html> (search only; not verified or measured).

**Standards this design cites directly:** RFC 8032 (Ed25519), sections 5.1.5 to 5.1.7 and 7.1; FIPS 180-4 (SHA-256); RFC 2104 (HMAC); RFC 6455 section 5.3 (masking); RFC 1035 section 2.3.4 and RFC 1123 section 2.1 (host name length); RFC 6979 (deterministic ECDSA). These were cited from knowledge, not re-read in this work; each requirement that rests on one is to be linked to an rdm source with its clause when recorded.

**rdm records read:** DEC-910, REQ-714, DEC-1527, DEC-6443, TODO-6463, TODO-6444, TODO-6445, DEC-2463, REQ-1057, REQ-1058, DEC-6462, DOC-1924, REQ-1040, DOC-1923, DEC-2024, DOC-2312, DEC-1756, DEC-2414, DOC-1951; and, from searches, DOC-1863, REQ-2874, REQ-507, REQ-512, REQ-515, REQ-1883, REQ-5505, REQ-879, REQ-715, REQ-881, REQ-882, REQ-888, REQ-3398, REQ-3400, REQ-3924, REQ-4152, REQ-4153, REQ-4847, REQ-3929, REQ-2902, REQ-495, REQ-5156 to REQ-5171, REQ-2657, REQ-2658, REQ-2660, REQ-3668, REQ-2217, REQ-3838, REQ-3186, REQ-2218, DEC-2234, DEC-955, DEC-1765, DEC-628, DEC-559, REQ-1471, REQ-2963, DOC-1957, DOC-1968, DOC-1970, TODO-4900, DEC-5583, REQ-506, DEC-634, DOC-2032, DEC-1425, TODO-1252, TODO-1209, TODO-3073, REQ-161, REQ-701, REQ-712, REQ-874, REQ-3919, REQ-4827, REQ-1728.

**Code read:** the repositories and files named in section 1.5, at the commits named there.
