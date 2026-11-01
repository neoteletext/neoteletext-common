# The NeoTeletext servers, and how to program them

This guide is for a programmer who will run the server and write programs for it. Part 1 is the Rust server. Part 2 is the protocol kit and the UI library in TypeScript, and what differs in Python. Part 3 is how the real channels are written, how to test a program, and what usually goes wrong.

To make a channel step by step, read [Creating a channel](creating-a-channel.md). This guide explains what stands behind those steps.

Every example here was run for this guide against a server built from the commit named below. The runs used a free local port, and the output is printed with that port written as `8090`. Where a statement comes from reading the code and not from a run, the guide says so.

## Versions

Every version number belongs in this table. The rest of the guide says "the program protocol" and "the input protocol". The numbers appear elsewhere only in pasted output and in the constants at the top of `probe.ts` (section 3.2).

| What | Now | Where it is defined |
|---|---|---|
| Program protocol, server to program | 6 | `PROTOCOL` in `neoteletext-app-server/crates/teletext-runtime/src/protocol.rs` |
| Its schema | `protocol/schema-6.json` | `neoteletext-app-server`; each kit keeps a copy |
| Input protocol, receiver to server | 7 | `neoteletext_input::VERSION` in the engine; `INPUT.md` section 6.1 |
| WebSocket subprotocol | `neottx.7` | `PUSH_SUBPROTOCOL` in the engine's `neoteletext-web`; `wire-vectors.tsv` |
| TypeScript protocol kit | 5.0.0, speaks program protocol 6 | `neoteletext-server-ts-protocol/package.json` |
| UI library | 11.0.0, on kit 5.0.0 | `neoteletext-server-ts-ui-components/package.json` |
| Python kit | 0.1.0, speaks program protocol 6 | `neoteletext-server-channels/kits/python` |
| Engine, pinned by the server | `8e1f51e` | `neoteletext-app-server/Cargo.toml` |
| Rust | 1.99.0 | `neoteletext-app-server/rust-toolchain.toml` |
| Node | 22.18 or later | each `package.json`; runs here were on 24.21.0 |
| Python | 3.13 or later | `kits/python/pyproject.toml`; runs here were on 3.14.3 |

A kit's version and the protocol's are separate numbers: kit 5.0.0 speaks program protocol 6.

This guide describes these commits, 1 November 2026:

| Repository | Commit |
|---|---|
| `neoteletext-app-server` | `d1fccb1` |
| `neoteletext-server-ts-protocol` | `e4ffa2c` |
| `neoteletext-server-ts-ui-components` | `1ce8db5` |
| `neoteletext-server-channels` | `36b6d21` |

Work in progress at that moment was left out of this guide on purpose. The largest piece is the `describe` and `description` messages, with a public web page for a page a program marks public, which `SERVER.md` section 4.9 describes in a change not yet committed. Check that section once it lands.

## Part 1: the Rust server

### 1.1 What it is for

The server is a teletext application server. Receivers connect to it. A program, in any language, makes each channel's pages. The server stands between them:

- To a receiver it speaks teletext. What it sends is 42-byte packets, and the messages joined together are a plain T42 stream.
- To a program it speaks typed JSON, one object a line.
- It translates between the two, checks everything, and sends each connection only what changed in the one sub-page that connection shows.

The rule that shapes the rest is that **the server relays and the program owns every page** (DEC-1482). The server has no page store. It never answers a viewer from a copy. Every sub-page a viewer sees is one the program sent for them. The program does not have to be fast at this: the kits keep the pages and answer for it.

One program serves every viewer of its channel, and there is no process per viewer.

### 1.2 The crates

The workspace is in `~/devel/neoteletext-app-server`. Teletext itself, the page model, the encoder, the input protocol and the audio profile, comes from the engine at one pinned commit and is never copied.

| Crate | What it holds | What it never does |
|---|---|---|
| `teletext-runtime` | One channel as a state machine: connections, sessions, selections, the program protocol's types and checks, the changed-rows sender, session cookies, and what a channel's address answers | No input or output, no clock, no threads. It is `no_std` |
| `teletext-native` | The server on Linux, macOS and Windows: tokio, hyper, the program supervisor, WebSocket framing, the state directory, the log and the figures. It builds `teletext-server` and the load client `teletext-load` | No teletext logic |
| `teletext-cloudflare` | The same runtime as a Worker and one Durable Object for each channel. See section 1.13 | It is empty on every target but `wasm32` |

The runtime takes events and answers with effects. A host gives it what happened, with the time, and carries out the result:

```
host to runtime:  opened, received, closed, from_program, program_started, program_ended, deadline
runtime to host:  Send (bytes for a connection), Close, ToProgram (a line), Log
```

So a test of the runtime needs no network, and the clock is whatever the test says. In the native host, each channel is one tokio task holding one runtime. A channel is single-threaded, and channels run in parallel. `crates/teletext-native/src/hub.rs` is that task, and it is short enough to read in one sitting.

### 1.3 A request, from a receiver to a program and back

```
receiver ══ WebSocket, packets down, input up ══ server ── lines of JSON ── program
                                                  one task
                                                  a channel
```

A receiver opening a channel does this:

1. **It fetches `<channel>channel.ttx`.** This says the channel is live and gives its first page.
2. **It upgrades `<channel>push` to a WebSocket,** offering the subprotocol. The server answers 101 and sets its signed `_session` cookie. An existing cookie continues the session.
3. **It sends HELLO** with the input protocol's version and its capabilities. The server answers with WELCOME.
4. **It sends SELECT**, naming the page. This is the first selection.
5. **The server tells the program.** It has held `connected` until now, so a shared link goes straight to its page. The wait lasts at most 1.5 seconds. A receiver without the SELECT capability is not waited for.
6. **The program answers with `reply`,** holding the channel's index and the one sub-page.
7. **The server checks the line, encodes the sub-page and sends it.** The index goes as index records, the sub-page as a page frame, and any Link Extension links as a LINKS record.

Each later choice is a new SELECT, which reaches the program as `selected`. The answer is one `page` message.

Here is the real thing, from the example channel of section 2.12 and the small receiver of section 3.2:

```
$ node probe.ts ws://127.0.0.1:8090/guide/push 100 101 wait:1500
open, subprotocol neottx.7
message of 42 bytes
  record WELCOME
> select 100
message of 126 bytes
  record INDEX
  record, fragment 1
  record, fragment 2
message of 504 bytes
  100/0000 header erase "GUIDE"
  packet X/27
  row 1 "  Index"
  row 4 " 101 Clock"
  row 5 " 102 Facts"
  row 6 " 103 Counter"
  row 7 " 104 Picture"
  row 9 " NeoTeletext's home channel"
  row 24 " Clock   Facts"
  record LINKS
  record, fragment 1
  record CURSOR
> select 101
message of 210 bytes
  101/0000 header erase "GUIDE"
  packet X/27
  row 1 "  Clock"
  row 4 " 12:32:54"
  record CURSOR
message of 168 bytes
  101/0000 header keep "GUIDE"
  packet X/27
  row 4 " 12:32:55"
  record CURSOR
...
```

The last message is the point of the design. The program sent the whole clock page again. The server compared it with what that connection was last sent and sent only the header and the one changed row, without the erase bit.

A key goes the other way. The receiver sends KEY, stamped with the page and sub-code on screen. The server checks the stamp against the connection's selection, and if they match, the program gets `input`. The program may then send a new `page`.

Here is the same conversation as the program sees it, from a program with no kit that logs each line (section 2.16):

```
{"type":"start","protocol":6,"epoch_ms":1793535906013,"standard":{"magazines":8,"pages":2022,"pages_per_magazine":253,"pages_in_magazine_1":251,"keyable_pages":800,"subpages":8190,"decimal_subpages":3199},"budgets":{"line_bytes":16777216,"title_characters":120,"author_log_bytes":200,"log_characters":1000,"named_connections":4096,"reply_limit_ms":5000}}
{"type":"connected","connection":1,"session":1836580767750144,"request":1,"cookies":[],"selection":{"page":"100","sub":"3F7F"},"path":"100","query":null}
{"type":"left","connection":1,"page":"100"}
{"type":"selected","connection":1,"request":2,"path":"200","page":"200","sub":"3F7F","query":null}
{"type":"left","connection":1,"page":"200"}
{"type":"selected","connection":1,"request":3,"path":"100/0000","page":"100","sub":"0000","query":null}
{"type":"input","connection":1,"page":"100","sub":"0000","lost":false,"event":{"kind":"key","action":"press","key":"Enter","text":null,"base":null}}
{"type":"input","connection":1,"page":"100","sub":"0000","lost":true,"event":{"kind":"key","action":"release","key":"Enter","text":null,"base":null}}
{"type":"left","connection":1,"page":"100"}
```

The receiver there pressed Enter and closed without letting go, so the program was given the release, marked `lost`. `left` comes before `selected` when the page changes, and it does not come for a step between sub-pages of one page.

### 1.4 The two protocols

The two protocols are kept apart on purpose. The first is binary, for a small trusted receiver. The second is JSON, for people.

**The input protocol** runs on the push WebSocket, and `INPUT.md` is its definition.

- **The upgrade.** The request must offer the subprotocol, or it is answered 426, naming the one spoken. A request that carries `Origin` is answered 403, whatever it offers. A web page's script always sends `Origin`, so a receiver cannot be written in a web page.
- **Upstream.** Binary events, each `0xFF`, a type byte and its fields, at most 8,192 bytes a message: HELLO, SELECT, KEY, MOUSE, WHEEL, PASTE, COMPOSE, FOCUS_IN, FOCUS_OUT, RESIZE, HOVER. Text outside an event is raw text. A message holds whole items and is read alone.
- **Downstream.** Binary messages only, each a whole number of 42-byte packets. Joined, they are a valid T42 file. Page frames carry one sub-page. Everything else is a record on packet 4/31, data channel 12: WELCOME, cursor, index, LOG, SET_COOKIE, LINKS, SUBPAGES, REDIRECT, DENIED, and sound.
- **Closing.** 4000 means the receiver broke the protocol and 4001 means another version, and on either a receiver stops. 4100 means a restart, and a receiver tries again.
- **The bytes.** `neoteletext-common/wire-vectors.tsv` has real messages for each of these. Anyone implementing a receiver should run that file.

Each of those refusals was run:

```
$ curl -si ... -H 'Sec-WebSocket-Protocol: neottx.7' -H 'Origin: https://example.org' http://127.0.0.1:8090/raw/push
HTTP/1.1 403 Forbidden

$ curl -si ... -H 'Sec-WebSocket-Protocol: neottx.6' http://127.0.0.1:8090/raw/push
HTTP/1.1 426 Upgrade Required
upgrade: websocket
sec-websocket-protocol: neottx.7

HELLO version 6: closed 4001
retired PAGE: closed 4000
a stopped server: closed 4100
```

**The program protocol** runs between the server and a program. It is defined once, by the Rust types in `crates/teletext-runtime/src/protocol.rs`, and published as a JSON Schema generated from them, in `protocol/`. `$defs/ServerMessage` is what the server sends and `$defs/ProgramMessage` is what a program sends. The schema is the exact contract. `docs/applications.md` sections 2 and 3 say what each message is for, and section 2.4 of this guide lists them.

- One JSON object a line, UTF-8, ending in `\n`, at most 16 MiB.
- Every message has a `type`. An unknown `type` or field is refused, never skipped.
- Each line is checked whole and refused whole. The program is sent `refused`, and the reason goes to the log. Nothing of a refused line is acted on.

Two kinds of number matter:

- **`connection`** is one browser tab. **`session`** is a viewer, across tabs and reconnections.
- **`request`** is the number of a connection's selection, rising from 1. A program copies it into its answer. The server drops an answer whose number is not current, so a late answer cannot replace the page on screen. The kits copy it for you.

### 1.5 One selection a connection

A connection is one browser tab. It has one **selection**, or none: one page and one sub-code. A sub-code of `3F7F` means the page and none of its sub-pages in particular. It is answered with the page's first sub-page in ascending order, and that sub-page then is the selection.

Three words are defined once in `INPUT.md` section 5.4. **Selected** is what a tab shows. **Active** is what a selected page is to the server: it gets every update, whatever the viewer's input is doing. **Focused** is for input only. A page in a tab behind another stays selected, active and updated.

Nothing rotates on a live channel. The sub-page a connection shows changes only when the receiver selects another, or when the program sends a page redirect.

**What the server keeps**, in memory, for one open connection:

- its session, the cookies it opened with, and its selection with that selection's query and number;
- the one sub-page last sent to it, for taking changed rows against;
- what it holds down, so that releases can be given to the program if the connection goes;
- which version of the page's sub-page list it holds;
- the deadline of its selection.

For a session it keeps a count of open connections, and when the last one closed. For the channel it keeps the sound command numbers. On disk, in the state directory, it keeps the session cookie's keys and the accumulated figures, and nothing of any channel's content.

**What the server relays:**

| A program sends | A viewer gets |
|---|---|
| `reply` | Index records, then the sub-page as a page frame |
| `page` | The sub-page, only if the connection's selection shows it. Whole with the erase bit the first time after a new selection, and after that only the changed rows, or nothing if nothing changed |
| `subpages` | A SUBPAGES record, if the connection does not hold that version |
| `index` | Index records |
| `redirect` | A REDIRECT record. A page redirect is a selection, so the program is then sent `selected` |
| `denied` | A DENIED record. The connection stays open |
| `sound` | Audio records |
| `cookie` | A SET_COOKIE record |
| `author_log` | A LOG record, for the viewer's developer console |
| `packets` | The packets, each checked with the engine's stream check |
| `log` | Nothing: it goes to the server's log |

Every selection has an ending: a page, DENIED, or a deadline. After 5 seconds without an answer, the server sends DENIED 503 itself and logs `program_late`. If no program is running, DENIED 503 goes at once. Run with a program that reads and never answers:

```
$ time node probe.ts ws://127.0.0.1:8090/silent/push 100 wait:5500
> select 100
message of 42 bytes
  record DENIED
closed 1005
... 5.428 total

WARN channel: connection 2: no reply to connected within 5000 ms channel="silent" event="program_late"
```

### 1.6 What an ordinary web browser is answered with

The server answers HTTP only as the URL map says. `SERVER.md` section 4.7 is the definition, and these were run:

| Request | Answer |
|---|---|
| `/guide/` | 200, the small page |
| `/guide/contents`, `/guide/wall`, `/guide/302/0002` | 200, the same small page, repeating that address |
| `/guide` | 308 to `/guide/` |
| `/guide/302/?a=1` | 308 to `/guide/302?a=1` |
| `/guide/channel.ttx` | 200, JSON, generated |
| `/guide/push` | 426 without a proper upgrade |
| `/guide/channel.json`, `/guide/100.tti`, `/guide/302/2`, `/`, `/nothere/` | 404 |

Pages are never served over HTTP. A live channel's pages travel only on its connection.

```
$ curl -si http://127.0.0.1:8090/guide/channel.ttx
HTTP/1.1 200 OK
content-type: application/json
cache-control: no-cache

{"name":"Guide","initial_page":"100","push":{"input":true}}

$ curl -si http://127.0.0.1:8090/guide/
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
cache-control: no-cache
content-security-policy: default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'
x-content-type-options: nosniff
referrer-policy: no-referrer

<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guide</title>
</head>
<body>
<h1>Guide</h1>
<p>This is a teletext channel, which opens in the NeoTeletext browser.</p>
<p><a id="open" href="neottx://http://127.0.0.1:8090/guide/">Open in NeoTeletext</a></p>
<p><a href="https://www.neoteletext.com/">Get NeoTeletext</a></p>
</body>
</html>
```

The small page runs no script and holds nothing from the program, so at this commit every page answers the same way. Only `GET` and `HEAD` reach it. `initial_page` is 100 for every channel, because `main.rs` sets it. The page a viewer really opens on is the program's choice.

### 1.7 The channels file

`--channels FILE` names what the server serves. Without it there are no channels, and every address answers 404.

```json
{"channels":[
  {"folder":"guide","name":"Guide","command":["node","src/main.ts"],"directory":"."},
  {"folder":"service","name":"Service","socket":"sockets/service.sock"}
]}
```

- **`folder`** is the channel's address, of letters, digits, `-` and `_`. The server does not refuse a name the URL map gives another meaning: `100` was accepted when tried. `SERVER.md` section 4.1 says a folder named `contents`, `wall` or like a page number cannot be a channel, so do not use one.
- **`name`** is shown to viewers. It defaults to the folder.
- **`command` and `directory`** have the server start the program, on standard input and output. A relative `directory` is taken from the channels file's own folder, so `../neoteletext-server-channel-demosite` names a repository beside it. The program gets `NEOTELETEXT_CHANNEL`, its folder.
- **`socket`**, in place of those, has the server listen on a Unix domain socket, and the program runs as a service of its own. A relative path is taken from the file's folder. The folder, if made, is `0700` and the socket `0600`, and those permissions are the authentication. One program at a time: a second is closed. Linux and macOS only.

A program that ends is started again after 1 second, then 2, 4 and on up to 30. One that ran for 5 seconds or more was ended and not failing, and is started again at once. Run with a program that exits at once, and then with a steady one killed:

```
INFO program: the program ended channel="crash" reason="its output closed" restart_in_ms=1000
INFO program: the program ended channel="crash" reason="its output closed" restart_in_ms=2000
INFO program: the program ended channel="crash" reason="its output closed" restart_in_ms=4000

INFO program: the program ended channel="guide" reason="its output closed" restart_in_ms=0
INFO program: the program started channel="guide" program="node"
```

A restarted program is sent `start`, then `connected` for every open connection. In that run the viewer on the page received new index records and no page frame, because the page the new program sent was the same as the one the connection already showed.

The repository's real file is `~/devel/neoteletext-server-channels/channels.json`.

### 1.8 Ports and socket activation

| Flag | Default | What it does |
|---|---|---|
| `--listen ADDRESS` | `0.0.0.0:8090` | Where viewers connect |
| `--origin URL` | `http://127.0.0.1:8090` | The address viewers reach it at. It makes the small page's link and sets the session cookie's `Secure` when it begins `https://` |
| `--channels FILE` | none | Section 1.7 |
| `--state DIRECTORY` | `$STATE_DIRECTORY`, else none | The session cookie's keys and the accumulated figures |
| `--admin-listen ADDRESS` | none | `/metrics`, `/stats.json`, `/healthz`, `/readyz`. Never put this on the viewers' address |
| `--log-format auto\|json\|text` | `auto` | JSON when standard error is not a terminal |

The server speaks plain HTTP/1.1 and has no TLS. Something in front of it terminates TLS, as Caddy does in production (section 1.12).

Without `--state`, the session key is made for that run, so a restart ends every session and the figures start from nothing. With it, the folder holds `session.key`, `session.key.previous` if you put one there for rotation, and `figures.json`.

**Socket activation** (REQ-1041, DEC-1767). When systemd passes a listening socket, the server takes it and ignores `--listen`. systemd holds the socket across a restart, so a connection made while the server restarts waits in the socket's queue and is answered, where a socket of the server's own would refuse it. More than one passed socket is an error. The socket is made close-on-exec, so programs do not inherit it.

This was run with a shell standing in for systemd, as `tests/lifecycle.rs` does: `--listen` named an address the server could not have bound, and `channel.ttx` answered on the passed socket. It was not run under a real systemd for this guide. The unit is `deploy/ionos/neoteletext.socket`. Restarting the service keeps the socket. A changed address needs `systemctl restart neoteletext.socket`. A connection to the socket starts the service, so stopping the server for good means stopping the socket unit too.

On `SIGTERM` or `SIGINT` the server closes every viewer with 4100, keeps its figures and exits, within 10 seconds. A stop in the runs above took under a second.

### 1.9 Limits

Maxima are not limits: every page and sub-page the standard allows may exist, and a program learns them in `start`. These are budgets, which bound what is held at once. All come from the code at the commit above, and the ones a program needs are in `start`.

| What | Value | Where |
|---|---|---|
| One line, either way | 16 MiB | `protocol.rs`, `LONGEST_LINE` |
| One upstream WebSocket message | 8 KiB | `websocket.rs`, `MAX_MESSAGE` |
| One downstream WebSocket message | 64 KiB, cut before a sub-page's header where it can be | the engine's `DEFAULT_PUSH_LIMIT`, `frame.rs` |
| Messages waiting for one connection | 256, and the newest are lost beyond that | `hub.rs`, `OUTBOX` |
| Lines waiting for a program | 4,096, and the newest are dropped and logged | `apps.rs`, `WAITING_LINES` |
| Answer to `connected` or `selected` | 5,000 ms, provisional | `channel.rs`, `PROGRAM_REPLY_LIMIT_MS` |
| Wait for a first selection | 1,500 ms | `channel.rs`, `FIRST_SELECTION_WAIT_MS` |
| A session after its last connection closes | 5 minutes | `channel.rs`, `SESSION_GRACE_MS` |
| The `_session` cookie | 30 days | `session_cookie.rs`, `LIFETIME_S` |
| Connections named in one message | 4,096 | `protocol.rs` |
| Cookies passed to a program | 50, each name and value at most 4,096 bytes | `protocol.rs` |
| A title, a magazine name, a section | 120 characters | `protocol.rs` |
| A sub-page's title in its list | 40 characters | `protocol.rs` |
| An operator's log line, an author's log line | 1,000 characters, 200 bytes | `protocol.rs`, the engine |
| A line of a program's standard error | 64 KiB logged, the rest cut | `apps.rs` |
| Keepalive | a connection silent for 35 s is pinged, and one silent 10 s more is dropped | `connection.rs`, from the engine's constants |

Not built, though `SERVER.md` sections 6.3 and 11 discuss them: a rate limit on inbound events, a limit on connections per address, flush policies, and the LIMITS and CHANGED records. Reading `teletext-native` found none of them.

### 1.10 Logging and figures

Events go to standard error through `tracing`, one a line. `RUST_LOG` chooses levels and targets, as `RUST_LOG=info` or `RUST_LOG=channel=debug,info`. The targets are `program`, `channel`, `connection`, `figures` and `state`.

A program's standard error becomes the log, a line an event, under `program`. Its `log` messages appear under `channel`:

```
INFO teletext_server: serving version="0.1.0" listen=127.0.0.1:8090 origin="http://127.0.0.1:8090" channels="guide" state="../state" admin="127.0.0.1:9464"
INFO program: the program started channel="guide" program="node"
INFO channel: application: session 1836580715748352 joined channel="guide" event="program_log"
WARN channel: refused a line from the program: type: NotListed (unknown variant `unknown_message`, expected one of `reply`, ...) channel="raw" event="line_refused"
INFO teletext_server: stopping
INFO teletext_server: stopped
```

The server counts and never records who a viewer is. On the administration listener:

- **`/healthz`** answers `ok`.
- **`/readyz`** answers 200 `ready`, or 503 `no program running: away`. Ready means a program is running or connected, not that it has finished loading.
- **`/metrics`** is the Prometheus text format, since the process started.
- **`/stats.json`** holds the same figures for every channel, with an `all_time` block when there is a state directory. Each channel's figures are recorded once a second, so they lag a moment.

A program gets the same as `stats` every 10 seconds. The kits pass it on, and demosite's page 108 shows it.

```
teletext_connections 1
teletext_connections_total 8
teletext_program_restarts_total 2
teletext_channel_viewers{channel="guide"} 1
teletext_channel_sessions_waiting{channel="guide"} 4
teletext_channel_ready{channel="crash"} 0
```

The figures to watch while writing a program are `refused`, `lines_dropped`, `invalid_packets` and `stale_input`. All should stay at 0, apart from the odd `stale_input`, which is a viewer pressing a key while a page changes.

### 1.11 Build and run it locally

```sh
cd ~/devel/neoteletext-app-server
cargo build -p teletext-native
target/debug/teletext-server --listen 127.0.0.1:8090 --origin http://127.0.0.1:8090 \
    --channels ~/devel/neoteletext-server-channels/channels.json \
    --admin-listen 127.0.0.1:9464 --state tmp/state --log-format text
```

If another worker is using the repository's `target`, set `CARGO_TARGET_DIR` to a folder of your own. For this guide the committed tree was exported with `git archive` and built that way, so uncommitted work could not reach it. The engine comes from its public repository, so a first build needs the network.

The server needs no program to start. `--channels` may name any file you like, and section 2.12 has a one-channel file. `channels.json` above runs all five channels, and two of them want data: the Hackaday channels read `~/devel/neoteletext-hackaday`, and the demo channels read pictures from `tmp/pictures` if they are there.

Stop it with Ctrl-C, or `kill -TERM`.

`scripts/check.sh commit`, `push` and `full` are the repository's gates, and `~/devel/neoteletext-common/gates.md` says how they work. `scripts/try.sh <crate> [filter]` is the edit loop. For this guide `cargo test -p teletext-native --test lifecycle` was run on the commit above: all 16 tests passed. They start the real binary and cover the stop, socket activation, sessions, cookies and the address map.

`teletext-load --url ws://HOST:PORT/FOLDER/push --connections N [--page 105] [--seconds 60]` opens many connections and measures fan-out. It was not run for this guide.

### 1.12 How it is deployed

This describes `deploy/ionos/deploy.sh`, read and not run. It deploys to the `neoteletext` container on crowdwaveaudio.

```
internet ── caddyrouter, TLS ── container Caddy :8080 ── 127.0.0.1:8090 teletext-server
                                                     └── /opt/neoteletext/current/www, the static site
```

- **Names.** `app.neottx.com` is the server's origin. `www.neottx.com` is the static site. `neottx.com` and the `neoteletext.com` names redirect. `caddyrouter` terminates TLS, and `deploy/ionos/caddyrouter.caddy` is its block. The container's Caddy, `deploy/ionos/Caddyfile`, serves port 8080 with `auto_https off`. HSTS is never set.
- **The script's order.** It takes dated backups on the container, builds a static musl server on the Linux build host, and installs the binary. It copies each channel with rsync **from the working trees beside the repository**, so what is deployed is what is on the disk and not a commit. Then it runs `npm ci`, copies the dataset, sets up the Python channel, writes `channels.json`, the service and the socket units and the Caddyfile, validates and restarts, and replaces caddyrouter's block in a checked candidate.
- **The service.** It runs as `ubuntu`, with `StateDirectory=neoteletext`, `--listen 127.0.0.1:8090 --origin https://app.neottx.com --admin-listen 127.0.0.1:9464`, and `TimeoutStopSec=15`. The socket unit keeps connections waiting across a restart.
- **The check.** The script ends by asking each channel's `channel.ttx` from inside the container.

`--no-build` reuses the binary already on the build host. DNS is not touched. `scripts/deploy.sh` is an older script for a systemd user service on a local host.

### 1.13 The Cloudflare host

`crates/teletext-cloudflare` is built, and it has never run on Cloudflare. It compiles for `wasm32-unknown-unknown` and the gates hold it to that. `worker-build` is not installed here, so the code as it stands has not been run at all (TODO-1709). The one run on record is local: on 28 October 2026 its four tests passed under `wrangler dev` (REQ-1021), and the protocol has moved a long way since.

The design is one Durable Object for each channel, running the same `teletext-runtime`. Viewers connect to `/<channel>/push`. A program connects to `/<channel>/program` over a WebSocket with the channel's secret, through `scripts/bridge.ts`, which runs an unchanged program over standard input and output.

Do not plan on it yet. At this commit it does not call `landing::push_upgrade`, so it does not apply the subprotocol and `Origin` rule (TODO-1731). It has no `stats` line or `/metrics` either (TODO-1306).

## Part 2: Node and TypeScript

A program may be written in any language, and section 2.16 has one with no kit. Two libraries make it easy in TypeScript:

- **`neoteletext-server-ts-protocol`,** the protocol kit: the JSON protocol, a place to keep pages, drawing, input, navigation and sound.
- **`neoteletext-server-ts-ui-components`,** the UI library: components, like React class components, on top of the kit.

Node runs the `.ts` files as they are, by stripping their types, so a channel has no build step. Use only syntax Node can strip.

### 2.1 Getting the kit

Neither library is on a registry. Each is a built tarball, committed under a channel's `vendor/`:

```json
{
  "name": "guide-channel",
  "private": true,
  "type": "module",
  "engines": { "node": ">=22.18.0" },
  "dependencies": {
    "neoteletext-server-ts-protocol": "file:vendor/neoteletext-server-ts-protocol-5.0.0.tgz",
    "neoteletext-server-ts-ui-components": "file:vendor/neoteletext-server-ts-ui-components-11.0.0.tgz"
  }
}
```

Copy the tarballs from any channel's `vendor/`, then run `npm install`. Every channel repository is laid out this way. `BUILD.md` in each library says how a release is made.

`dist/` and `src/wire/generated/` are not in the kit's repository: they are built by `scripts/check.sh`. Depend on the tarball and not on the kit's source.

### 2.2 How a program connects

The server starts the command in the channels file. `runChannel` reads lines on standard input, writes lines on standard output, and resolves when standard input closes, which is the server going away:

```ts
await runChannel([application]);
```

**Standard output carries protocol lines and nothing else.** Anything for a person goes to standard error, which the server logs. One `console.log` in a program is a refused line. Use `process.stderr.write`, or `context.log`, which sends a `log` message once the program has started.

For a Unix socket, give `runChannel` other streams. The server's channels file has `"socket":"sockets/service.sock"`:

```ts
// A program that runs as a service of its own, and connects to the server's
// Unix socket: the same kit on other streams. When the connection goes it
// ends, and whatever runs it starts it again.
import { connect } from "node:net";

import { type Application, Colour, runChannel, Screen } from "neoteletext-server-ts-protocol";

const [path = ""] = process.argv.slice(2);
const socket = connect(path);

const hello: Application = {
  pages: () => [{ page: 0x100, title: "Hello" }],
  start(context) {
    const screen = new Screen();
    screen.doubleHeight(2, 0, Colour.Yellow, "Over a socket");
    context.publish("channel", 0x100, screen);
  },
};

await runChannel([hello], {
  streams: {
    input: socket,
    output: (line) => socket.write(`${line}\n`),
    errors: (text) => process.stderr.write(`${text}\n`),
  },
});
```

That ran, as `node src/over-socket.ts sockets/service.sock`:

```
INFO program: waiting for the program to connect channel="service" socket=sockets/service.sock
INFO program: the program connected channel="service"
INFO program: the program went channel="service" reason="its output closed"
```

Nothing connects it again for you. Whatever runs the program as a service must start it again, and it must connect again after the server restarts.

### 2.3 Lifecycle

An `Application` is an object with the pages it serves and the calls it answers. A channel may have several, and the first to name a page serves it.

| The server says | The kit calls, in order | Then the kit answers |
|---|---|---|
| `start` | `start(context)` on every application | Nothing yet: it keeps what you publish |
| `connected` | `joined` if the session is new to the program; `request` for the page; `opened` if this is the session's first connection on the page | One `reply`, then `subpages` if the page has several sub-pages |
| `selected`, a new page | `request`, then `opened` | One `page`, then `subpages` |
| `selected`, the same page | `request` | One `page` |
| `left` | `request` with null; `leftPage` if it was the session's last connection there | Nothing |
| `input` | Navigation first, then `input` if navigation did not take it | Nothing unless you act |
| `closed` | `ended`, and the session's own pages are forgotten | Nothing |
| `stats` | `stats` on every application | Nothing |
| `refused` | Written to standard error | Nothing |

`wake` is the kit's own: ask with `context.wakeIn(ms)` or `wakeAt(ms)`. It fires once, the earliest asked for wins, and you ask again for the next.

Three things catch people out:

- **`joined` comes before the session has a connection.** A sound or an author's log for that session goes nowhere, and `connectionsOf` is empty. Do those in `opened`. This cost a run of the example below: the sound object sent in `joined` never arrived. The Python kit is different, and `on_join` does have the connection.
- **`ended` comes 5 minutes after the viewer went,** because a session waits to see if they come back. If a tab closes, you get `left` at once and `closed` later.
- **A restarted program knows nothing.** It gets `start` and a `connected` for each viewer, and the kit forgets all connections at `start`. Anything a viewer must not lose has to be in a cookie or a store of yours.

`request` is how a selection reaches you as a web request would:

```ts
{ method: "GET", path: "302/0002", query: { a: "1" }, queryText: "a=1", cookies: { name: "value" } }
```

It comes for every selection and before the page opens, so you may publish in it. It comes with null when the viewer leaves the page. A query belongs to one selection: a later selection without it leaves it behind. `query` keeps the last value of a name given twice, and `queryText` keeps what was written. Everything in it but `method` is untrusted, from the viewer. Cookies are those the connection opened with: a cookie you set reaches you on the next connection.

### 2.4 Every message

The kit writes these for you. This table is for reading the log and for writing without a kit. `docs/applications.md` sections 2 and 3 give every field, and the schema is the exact contract.

From the server:

| `type` | Means | Kit |
|---|---|---|
| `start` | The program started. `protocol`, `epoch_ms`, `standard`, `budgets` | `start` |
| `connected` | A connection's first selection came, or 1.5 s passed. `connection`, `session`, `request`, `cookies`, `selection`, `path`, `query`. Answer exactly once with `reply` | `joined`, `request`, `opened` |
| `selected` | A new selection. `connection`, `request`, `path`, `page`, `sub`, `query` | `request`, `opened` |
| `input` | A viewer's input. `connection`, `page`, `sub`, `lost`, `event` | `input` |
| `left` | A selection left a page, or the connection closed | `request` null, `leftPage` |
| `closed` | The session ended, 5 minutes after its last connection. Forget it | `ended` |
| `stats` | The figures, every 10 seconds | `stats` |
| `refused` | A line of yours was refused whole. `message`, `path`, `rule`, `detail` | Standard error |

From the program:

| `type` | What it does | Kit |
|---|---|---|
| `reply` | Answers `connected`: `magazines`, the index, and `selected`, one sub-page or null. With null, a `page`, `redirect` or `denied` must follow | Automatic |
| `page` | One sub-page to named connections. `request` is the selection it answers, or null for a change | `publish`, `publishSubpages`, `publishTti`, `put` |
| `denied` | Ends a selection with 403, 404, 429 or 503. The connection stays | Automatic for 404 only. See below |
| `subpages` | A page's sub-page list, with a `version` | Automatic |
| `index` | The index changed | Automatic; `title` |
| `redirect` | Sends a viewer to a page or an address | `redirect` |
| `sound` | A sound, its data or a command | `sound` |
| `cookie` | Sets one of the program's cookies | `cookie` |
| `author_log` | A line for the viewer's developer console | `authorLog` |
| `log` | A line for the server's log | `log` |
| `packets` | Raw 42-byte packets, base64 | `packets` |

`Context` has no call for `denied`, so a kit program cannot answer 403 or 429. Use `App` and `serveLines` for that, or write the line yourself.

A sub-page on the wire has every field present: `page`, `sub`, 25 `rows` as base64 of 40 seven-bit codes or null, six `links`, `display_row_24`, `link_extension`, `control`, `character_set`, `enhancements`, `packets` and `cursor`. Section 2.16 shows one.

### 2.5 Validation

Before it writes a line, the kit checks the message against the server's schema, with validators compiled from it at build, and then against the rules the schema cannot state: no control or bidirectional character, Unicode normalisation form C, and limits in bytes. A message the server would refuse is never written. `App.send` throws a `ProtocolError` naming the path and the rule.

An application's failure is caught and reported, and the channel goes on. So a mistake shows on standard error, and in the server's log. Here is one, a page numbered in decimal:

```
answering connection 1 failed: ProtocolError: reply: magazines[0].magazine: out_of_range (must be >= 1 ...)
```

Titles, names and log lines the kit fits by itself. Text on a page goes through `englishCodes`, which folds what the English set lacks to the nearest it has. Page numbers are hexadecimal in JSON and numbers in the kit: write `0x100`.

### 2.6 What `Context` does

An application answers through the `Context` it is given. A context belongs to one call: do not keep it.

| Call | What it does |
|---|---|
| `publish(owner, page, screen)` | The page as one sub-page, 0000 |
| `publishSubpages(owner, page, subpages)` | The whole page, numbered by place |
| `publishTti(owner, page, text)` | The whole page from TTI |
| `put(owner, page, subpages)`, `remove(owner, page, subcodes)` | One sub-page in or out, by sub-code, keeping the others |
| `release(session, page)` | Drops a session's own copy: it sees the channel's again |
| `title(page, title)`, `titleOf(page)` | The title in the index |
| `redirect(session, page, sub?)`, `redirect(session, address)` | Section 2.10 |
| `sound(to, member)` | Section 2.12 |
| `authorLog(to, level, text, page?)` | `E`, `W` or `I`, for the viewer's developer console |
| `log(text)` | The server's log |
| `cookie(connection, name, value, options)` | `path`, `maxAge`, `sameSite`, `secure`, `httpOnly`. Names starting `_` are the server's |
| `packets(to, bytes)` | Raw packets |
| `connection()`, `connectionsOf(session)` | The connection this call came from, and a session's tabs |
| `wakeAt(at)`, `wakeIn(delay)` | The `wake` call |
| `now()`, `epochMs()` | Milliseconds since the program started, and the real time by the server's clock |
| `limits()` | What `start` said |
| `random()`, `below(bound)` | For games, never for secrets |

`owner` is `"channel"`, one copy every viewer sees, or a session number, that viewer's own copy. **The kit keeps every page,** so the server need not. When a session has a copy of a page, it sees that copy and not the channel's, until `release`. A change to a page goes to the connections whose selection shows it, and nothing else does anything.

Publish a channel's copy of every page in `start`, even if each viewer will have their own. The index takes its count of a page's sub-pages from the channel's copy.

### 2.7 Sub-pages

A page has one sub-page or many, and every sub-code is a peer. Give a page whole and the kit numbers it by place, as the code of practice says: one sub-page is 0000, and 2 to 79 are 0001 to 0079, decimal, so 0009 is followed by 0010. `put` and `remove` name sub-codes themselves and keep them as given.

```ts
context.publishSubpages("channel", FACTS, [factPage("Three sub-pages"), factPage("One at a time"), factPage("Nothing rotates")]);
```

`Subpage` is `{ screen, subcode?, title? }`, and `title` is its name in the list, at most 40 characters. Only one sub-page goes to a connection at a time, with the list after it:

```
> select 102/0002
message of 210 bytes
  102/0002 header erase "GUIDE"
  packet X/27
  row 1 "  Facts"
  row 4 " One at a time"
  record CURSOR
message of 126 bytes
  record SUBPAGES
  record, fragment 1
  record, fragment 2
```

A selection of a sub-page the page lacks is sent to the page instead, keeping its query:

```
> select 102/0007
message of 42 bytes
  record REDIRECT
message of 210 bytes
  102/0001 header erase "GUIDE"
  record CURSOR
message of 126 bytes
  record SUBPAGES
```

A viewer's own stepping is a selection, so each step costs one round trip to the program. A page's sub-pages do not all go together, so a page may have thousands. The standard allows 8,190, and demosite's page 602 has every picture at every level.

### 2.8 Input

`input(session, page, input, context, sub)` gets everything a viewer does on the page on screen. A key's press and release, every mouse move and every wheel turn all come. Ignore what you do not use.

| `input.kind` | Fields |
|---|---|
| `key` | `action`: `press`, `repeat`, `release`; `key`, a W3C `KeyboardEvent.key` name; `text`; `base`; `lost` |
| `mouse` | `action`: `press`, `release`, `move`; `button` or `buttons`; `column`, `row`; `lost` |
| `wheel` | `dx`, `dy` in 1/120ths of a line, down positive; `column`, `row` |
| `hover` | `action`: `enter`, `leave`; the control's first `column` and `row` |
| `text` | `text`, from an input method or a phone |
| `paste` | `text`. It is data, never keystrokes |
| `focus`, `blur` | The page has, or lost, the keyboard. It stays selected and updated |

The helpers are `pressed(input, key)`, which is true on a press or repeat, `released`, `clicked`, `typed`, which reads text from a key or from raw text, `character`, and `decimalDigit`. `Key` names the keys, among them `Key.Enter`, `Key.Red` and `Key.Up`. A `lost` release means the viewer left or the connection went, and the key never came up. A lost mouse release is not a click.

**Navigation comes first.** In a live channel every key goes to the program, digits and colour keys included, and the receiver selects nothing. So the kit does what a television remote does. On a page that does not claim them, three digits select a page, and F1 to F4 or the coloured keys follow the page's Fastext links. Your `input` never sees those keys. Claim them in the page's entry:

```ts
{ page: QUIZ, title: "Quiz", ownsDigits: true, ownsColourKeys: true }
```

A click comes to `input` first. Answer `true` if the page took it. Otherwise the kit follows what is under it: a Fastext prompt on row 24, or three digits standing alone.

The server drops input stamped with a page other than the selection, except a release, and counts it as `stale_input`. So a key meant for the last page never reaches this one.

### 2.9 Links

There are two kinds, and they travel differently.

- **Fastext links** are in the page's packets (X/27/0): `screen.fastext([red, green, yellow, cyan])`, and `screen.indexLink(page)`. They name pages of this channel. Put the prompts on row 24. The kit follows the keys and clicks on prompts.
- **Link Extension links** are what packets cannot carry, and go in a LINKS record after every frame of the sub-page: `screen.keyLink(key, target, label?)`, `screen.numberLink(number, target)`, `screen.textLink(row, column, length, target)`.

A target is `mpp`, `mpp:ssss`, `name:mpp`, `name:mpp:ssss`, an `http` or `https` address, or `web:` and one. It is printable ASCII without spaces or commas. Each sub-page has at most 8 number links and 8 text links, and a link's target is at most 8,004 bytes. Links go with every frame, so long ones are costly: one whose links are all that long costs about 208 KB an update.

What a receiver does with a link is the receiver's business: `INPUT.md` section 9.7 and `CHANNEL.md` say. This guide confirmed that the LINKS record is sent, as the walk in section 1.3 shows, and did not run a receiver that follows it.

### 2.10 Redirects

`redirect` moves a viewer with no action from them. It is not an HTTP redirect, and a viewer's own choice overrides it.

- **To a page,** `context.redirect(session, 0x100)`, with an optional sub-code. It is a selection: the server records it, and the program is sent `selected`.
- **To an address,** `context.redirect(session, "https://app.neottx.com/home/")`. No selection changes. The receiver shows its notice and goes, and the program gets `left` when the viewer does.

It goes to the connection the call came from when that belongs to the session, and otherwise to each of the session's connections.

```
> key Escape
message of 42 bytes
  record CURSOR
message of 42 bytes
  record REDIRECT
message of 504 bytes
  100/0000 header erase "GUIDE"
  ...
> key Home
message of 42 bytes
  record CURSOR
message of 84 bytes
  record REDIRECT
```

At the first selection, a page the program lacks is redirected to the initial page, which is 100 or the lowest it has. Later, a page it lacks is DENIED 404. Both were run, and the second is:

```
> select 300
message of 42 bytes
  record DENIED
```

### 2.11 Pictures

A page is 40 by 25 cells, so a picture is one of three things:

- **Mosaics you draw.** `Sixels` is a canvas, two across and three down to a cell. `circle.draw(screen, 4, 10, Colour.Green)` draws it, with the colour attribute in the cell before.
- **TTI from a tool.** `context.publishTti(owner, page, text)` takes a converted picture whole, with its X/26 enhancement packets. `readTtiPages` reads TTI into typed sub-pages. In the UI library, `RawSubPage` takes a sub-page of TTI and `Picture` places a TTI's rows in a box. The demo channels read `NAME_l15.tti`, `NAME_l25.tti` and `NAME_l35.tti`, made by the engine's converter and collected by `neoteletext-server-channels/scripts/pictures.py`.
- **Raw packets,** with `context.packets`, each checked by the server.

How a Level 2.5 or 3.5 page's object pages and DRCS pages reach a receiver is not designed yet: `SERVER.md` section 20 item 7.

### 2.12 Sound

Sound is the engine's audio profile. Desktop and phone receivers play Opus alone. The program encodes it and the server checks each packet against the profile and carries it unchanged. PCM, which the server encodes as IMA ADPCM, is for microcontroller receivers.

The pattern is to send the sound once and then play it by handle:

```ts
const chime = opus.sound(chimeSamples(), CHIME_RATE);                  // ffmpegOpus().sound, at start
context.sound({ session }, { opus: { handle: 1, generation: 0, ...chime } });
context.sound({ session }, { play: { channel: 0, handle: 1, generation: 0 } });
```

`to` is `{ session }`, `{ page }` or `{ connections }`. `ffmpegOpus` needs ffmpeg with libopus on the path, and gives constant-rate 16 kbit/s packets of 20 ms. For a stream, `opus.stream(rate)` encodes as samples arrive and `opusLive` and `opusPackets` carry them. A stored sound is at most two minutes. Tests use `fakeOpus` from the testing entry, which the server would refuse, as it does not make real Opus.

Here is what arrives. The records were confirmed. No receiver played them for this guide.

```
> select 103
message of 714 bytes
  record OBJECT
  record DATA
  record, fragment 1
  ...
> key Enter
  ...
message of 42 bytes
  record CONTROL
```

### 2.13 A complete small program

This channel has an index, a clock that changes each second, a page of sub-pages, a counter each viewer has a copy of, a picture, a sound, a cookie, an author's log line and redirects. It is split as every real channel is, so a test can import it. `src/main.ts` runs it:

```ts
import { ffmpegOpus, runChannel } from "neoteletext-server-ts-protocol";
import { guide } from "./guide.ts";

await runChannel([guide(ffmpegOpus())]);
```

`src/guide.ts`:

```ts
// A small channel on the protocol kit: an index, a live clock, a page of
// sub-pages, a page each viewer has a copy of, and a picture.
import { type Application, Colour, type Context, type Input, Key, type OpusEncoder, type PageRequest, Screen, Sixels, pressed } from "neoteletext-server-ts-protocol";

const INDEX = 0x100;
const CLOCK = 0x101;
const FACTS = 0x102;
const COUNTER = 0x103;
const PICTURE = 0x104;
const SECOND_MS = 1_000;
/** The stored sound's handle and generation, chosen by this program. */
const CHIME = { handle: 1, generation: 0 };
const AUDIO_CHANNEL = 0;
const CHIME_RATE = 8_000;
const CHIME_HERTZ = 880;
const CHIME_AMPLITUDE = 8_000;

/** A quarter of a second of a sine wave. */
function chimeSamples(): Int16Array {
  const samples = new Int16Array(CHIME_RATE / 4);
  samples.forEach((_, index) => {
    samples[index] = Math.round(CHIME_AMPLITUDE * Math.sin((2 * Math.PI * CHIME_HERTZ * index) / CHIME_RATE));
  });
  return samples;
}

function titled(title: string): Screen {
  const screen = new Screen();
  screen.header("GUIDE");
  screen.doubleHeight(1, 0, Colour.Yellow, title);
  return screen;
}

function indexPage(): Screen {
  const screen = titled("Index");
  screen.coloured(4, 0, Colour.White, "101 Clock");
  screen.coloured(5, 0, Colour.White, "102 Facts");
  screen.coloured(6, 0, Colour.White, "103 Counter");
  screen.coloured(7, 0, Colour.White, "104 Picture");
  screen.textLink(9, 1, 8, "https://app.neottx.com/home/");
  screen.coloured(9, 0, Colour.Cyan, "NeoTeletext's home channel");
  screen.coloured(24, 0, Colour.Red, "Clock");
  screen.coloured(24, 8, Colour.Green, "Facts");
  screen.fastext([CLOCK, FACTS, null, null]);
  return screen;
}

function clockPage(context: Context): Screen {
  const screen = titled("Clock");
  screen.coloured(4, 0, Colour.White, new Date(context.epochMs()).toISOString().slice(11, 19));
  screen.fastext([INDEX, null, null, null]);
  return screen;
}

function factPage(words: string): { screen: Screen; title: string } {
  const screen = titled("Facts");
  screen.coloured(4, 0, Colour.White, words);
  screen.fastext([INDEX, null, null, null]);
  return { screen, title: words };
}

function counterPage(count: number): Screen {
  const screen = titled("Counter");
  screen.coloured(4, 0, Colour.White, `Count ${count}`);
  screen.coloured(6, 0, Colour.Cyan, "Enter adds one, Escape to the index");
  screen.cursor(4, 8, 0);
  screen.fastext([INDEX, null, null, null]);
  return screen;
}

function picturePage(): Screen {
  const screen = titled("Picture");
  const across = 40;
  const down = 45;
  const circle = new Sixels(across, down);
  for (let degrees = 0; degrees < 360; degrees += 1) {
    const angle = (degrees * Math.PI) / 180;
    circle.set(Math.round(19 + 18 * Math.cos(angle)), Math.round(22 + 21 * Math.sin(angle)), true);
  }
  circle.draw(screen, 4, 10, Colour.Green);
  screen.fastext([INDEX, null, null, null]);
  return screen;
}

/** The channel's one application, which `opus` encodes its sound for. */
export function guide(opus: OpusEncoder): Application {
  const chime = opus.sound(chimeSamples(), CHIME_RATE);
  /** What this program keeps of each viewer: the server keeps nothing of it. */
  const counts = new Map<number, number>();

  return {
    pages: () => [
      { page: INDEX, title: "Index", section: "Guide" },
      { page: CLOCK, title: "Clock" },
      { page: FACTS, title: "Facts" },
      { page: COUNTER, title: "Counter" },
      { page: PICTURE, title: "Picture" },
    ],

    start(context) {
      context.publish("channel", INDEX, indexPage());
      context.publish("channel", CLOCK, clockPage(context));
      context.publishSubpages("channel", FACTS, [factPage("Three sub-pages"), factPage("One at a time"), factPage("Nothing rotates")]);
      context.publish("channel", COUNTER, counterPage(0));
      context.publish("channel", PICTURE, picturePage());
      context.wakeIn(SECOND_MS);
    },

    wake(context) {
      context.publish("channel", CLOCK, clockPage(context));
      context.wakeIn(SECOND_MS);
    },

    joined(session, context) {
      counts.set(session, 0);
      context.log(`session ${session} joined`);
    },

    request(session, page, request: PageRequest | null, context) {
      const start = Number.parseInt(request?.query["start"] ?? "", 10);
      if (page === COUNTER && Number.isSafeInteger(start)) {
        counts.set(session, start);
        context.publish(session, COUNTER, counterPage(start));
      }
    },

    opened(session, page, context) {
      if (page === COUNTER) {
        context.publish(session, COUNTER, counterPage(counts.get(session) ?? 0));
        // Sent here and not in joined: joined comes before the session has a connection.
        context.sound({ session }, { opus: { ...CHIME, ...chime } });
      }
    },

    input(session, page, input: Input, context) {
      if (page !== COUNTER) {
        return;
      }
      if (pressed(input, Key.Enter)) {
        const count = (counts.get(session) ?? 0) + 1;
        counts.set(session, count);
        context.publish(session, COUNTER, counterPage(count));
        context.sound({ session }, { play: { channel: AUDIO_CHANNEL, ...CHIME } });
        context.authorLog({ session }, "I", `count ${count}`);
        const connection = context.connection();
        if (connection !== null) {
          context.cookie(connection, "count", String(count), { maxAge: 3_600 });
        }
      } else if (pressed(input, Key.Escape)) {
        context.redirect(session, INDEX);
      } else if (pressed(input, Key.Home)) {
        context.redirect(session, "https://app.neottx.com/home/");
      }
    },

    leftPage(session, page, context) {
      if (page === COUNTER) {
        context.release(session, COUNTER);
      }
    },

    ended(session) {
      counts.delete(session);
    },
  };
}
```

`channels.json`, in the same folder:

```json
{"channels":[
  {"folder":"guide","name":"Guide","command":["node","src/main.ts"],"directory":"."}
]}
```

Run it:

```sh
npm install
target/debug/teletext-server --listen 127.0.0.1:8090 --origin http://127.0.0.1:8090 \
    --channels channels.json --state state --admin-listen 127.0.0.1:9464 --log-format text
```

A query starts the counter, Enter raises it, and Escape goes to the index:

```
> select 103?start=5
message of 252 bytes
  103/0000 header erase "GUIDE"
  packet X/27
  row 1 "  Counter"
  row 4 " Count 5"
  row 6 " Enter adds one, Escape to the index"
  record CURSOR
> key Enter
message of 42 bytes
  record CURSOR
message of 168 bytes
  103/0000 header keep "GUIDE"
  packet X/27
  row 4 " Count 6"
  record CURSOR
message of 42 bytes
  record CONTROL
message of 42 bytes
  record LOG
message of 42 bytes
  record SET_COOKIE
```

The first CURSOR there is the server's acknowledgement of the key, which it sends at once. The rest is the program's answer. The whole page was published and one row went.

### 2.14 The UI library

`neoteletext-server-ts-ui-components` makes a page a tree of components, as React's class components do: props, state, `setState`, a lifecycle, and `h` in place of JSX. It lays the tree out, draws it, publishes it, routes keys and the pointer to the component they land on, and keeps a viewer's own copy of a page only while it differs from everyone's.

`ComponentChannel` is one `Application`, so `runChannel` runs it. Each page is a `PageSpec`:

| Field | Meaning |
|---|---|
| `page`, `title`, `section` | As an entry |
| `root(params)` | The page's root element |
| `perViewer` | Each viewer gets a mount of their own, with state of their own. When absent, the library works out whether a component needs one |
| `keepWhileAway` | A viewer's mount is kept while they are on other pages, until they go |
| `ownsDigits`, `ownsColourKeys` | When absent, the library asks the components |
| `rollover` | The controls' colours under the pointer |

`src/components.ts`, a counter that an address can start from:

```ts
// A small channel on the component library: an index and a counter each
// viewer has a copy of, which an address can start from: `<channel>101?from=5`.
import { Colour, Key } from "neoteletext-server-ts-protocol";
import { type Child, Component, Frame, h, isPress, type KeyEvent, type PageSpec, Text } from "neoteletext-server-ts-ui-components";

const INDEX = 0x100;
const COUNTER = 0x101;
const PROMPTS: readonly [string, number][] = [["Index", INDEX], ["Counter", COUNTER]];

/** A component with state: a count that Enter raises. */
class Counter extends Component<{ readonly from: number }, { readonly count: number }> {
  override state = { count: this.props.from };

  override focusable(): boolean {
    return true;
  }

  override render(): Child {
    return h(Text, { text: `Count ${this.state.count}` });
  }

  override onKey(event: KeyEvent): boolean {
    if (!isPress(event, Key.Enter)) {
      return false;
    }
    this.setState({ count: this.state.count + 1 });
    return true;
  }
}

/** The address's query is untrusted text: read it and bound it. */
function startingCount(from: string | number | undefined): number {
  const count = Number(from);
  return Number.isSafeInteger(count) ? count : 0;
}

export const pages: readonly PageSpec[] = [
  {
    page: INDEX,
    title: "Index",
    section: "Guide",
    root: () => h(Frame, { title: "Index", background: Colour.Blue, prompts: PROMPTS }, h(Text, { text: "Press green for the counter" })),
  },
  {
    page: COUNTER,
    title: "Counter",
    perViewer: true,
    root: (params) => h(Frame, { title: "Counter", background: Colour.Blue, prompts: PROMPTS }, h(Counter, { from: startingCount(params?.["from"]) })),
  },
];
```

`src/components-main.ts`:

```ts
import { runChannel } from "neoteletext-server-ts-protocol";
import { ComponentChannel } from "neoteletext-server-ts-ui-components";
import { pages } from "./components.ts";

await runChannel([new ComponentChannel(pages)]);
```

```
> select 101?from=5
message of 84 bytes
  record INDEX
  record, fragment 1
message of 294 bytes
  101/0000 header erase ""
  packet X/27
  row 1 "    Counter"
  row 2 ""
  row 3 " Count 5"
  row 24 " Index  Counter"
  record CURSOR
> key Enter
message of 42 bytes
  record CURSOR
message of 168 bytes
  101/0000 header keep ""
  packet X/27
  row 3 " Count 6"
  record CURSOR
```

Inside a component, `this.services` reaches the channel: `session`, which is null on the shared copy; `redirect(session, page, params?)`, which opens a page with `params` that its `root` reads; `redirect(session, address)`; `parameters(session)`, the selection's query; `title`; `play` and `stream`; `now`, `epochMs`, `limits`, `log`, `below`; and `bus`, for what one page's components tell another's, such as `stats`. On a page with `perViewer`, an address's query reaches `root(params)`. Its values are the viewer's untrusted text, so read and bound them.

`setInterval` and `setTimeout` on a component are cleared at unmount. With `{ whileViewed: true }` a timer runs only while someone has the page open, which suits a clock on the copy every viewer shares.

A `Frame` is a sub-page with a title band, a hint row and up to four Fastext prompts. Short sounds are made in the program with `sound`, `tone`, `noise` and `sequence`, and the library encodes them and sends each once to each audience. The library's own documents are good: `docs/how-it-works.md`, `docs/keys-and-focus.md`, `docs/look.md`, `docs/audio.md`, `docs/testing.md`, and `docs/components/` for each part.

### 2.15 What differs in the Python kit

The Python kit is `~/devel/neoteletext-server-channels/kits/python`, with no README. It is thin, and it has no dependencies. It gets only what is needed to keep the old Hackaday channel running until that is retired (DEC-1082), so choose TypeScript for new work.

| | TypeScript | Python |
|---|---|---|
| An application | An object of calls; several may share a channel | A subclass of `App`; one to a program |
| Handlers | `start`, `joined`, `request`, `opened`, `leftPage`, `input`, `wake`, `ended`, `stats`, synchronous | `on_start`, `on_join`, `on_request`, `on_open`, `on_leave`, `on_input`, `on_close`, `on_stats`, all `async` |
| Answering | Through a `Context` given to each call | Methods of `self` |
| Declaring pages | `pages()`, entries with `ownsDigits` and so on | `{page: title}` and `{page: section}` to the constructor. A page takes a key by answering `True` from `on_input` |
| Publishing | `publish`, `publishSubpages`, `publishTti`, `put`, `remove` | One `publish(page, screens, owner=CHANNEL, subcodes=None)`; no screens takes the copy away |
| `on_join` | Before the connection exists | After it exists |
| Timers | `wakeIn`, with one wake for each application | Your own `asyncio` tasks. The connection a handler ran for is carried in a context variable |
| Checking | Every message against the schema, compiled in | Text rules only, in `textrules.py`. The schema check is for tests, by `uvx` |
| Sound | Opus and PCM | PCM only, `sound_object`, `play`, `stop`. So desktop and phone receivers cannot play it |
| Screen | `doubleHeight` | `double_height`, and also `double_width` |
| Tests | `Harness` | No harness: `tests/test_kit.py` feeds lines to `receive` and checks them with `schema_faults` |
| UI library | Yes | No |

The request is a dict of the same shape. A complete program:

```python
"""A channel on the Python kit: one shared page, and a counter for each viewer."""
from neoteletext_app.app import App
from neoteletext_app.event import Event
from neoteletext_app.screen import Colour, Screen

INDEX = 0x100
COUNTER = 0x101


def screen_of(title: str, line: str) -> Screen:
    screen = Screen()
    screen.header("PYTHON")
    screen.double_height(1, 0, Colour.YELLOW, title)
    screen.coloured(4, 0, Colour.WHITE, line)
    screen.fastext([INDEX, COUNTER, None, None])
    return screen


class Hello(App):
    def __init__(self) -> None:
        super().__init__({INDEX: "Index", COUNTER: "Counter"}, {INDEX: "Guide"})
        self.counts: dict[int, int] = {}

    async def on_start(self) -> None:
        self.publish(INDEX, screen_of("Index", "Green for the counter"))
        self.publish(COUNTER, screen_of("Counter", "Count 0"))

    async def on_open(self, session: int, page: int) -> None:
        if page == COUNTER:
            self.counts.setdefault(session, 0)
            self.publish(COUNTER, screen_of("Counter", f"Count {self.counts[session]}"), owner=session)

    async def on_input(self, session: int, page: int, event: Event) -> bool:
        if page == COUNTER and event.kind == "key" and event.action == "press" and event.key == "Enter":
            self.counts[session] += 1
            self.publish(COUNTER, screen_of("Counter", f"Count {self.counts[session]}"), owner=session)
            return True
        return False

    async def on_close(self, session: int) -> None:
        self.counts.pop(session, None)


Hello().run()
```

In the channels file, with the kit on `PYTHONPATH`. The old Hackaday channel uses the uv workspace instead:

```json
{"folder":"python","name":"Python","command":["env","PYTHONPATH=/path/to/kits/python/src","python3","hello.py"],"directory":"."}
```

```
> select 101
message of 210 bytes
  101/0000 header erase "PYTHON"
  packet X/27
  row 1 "  Counter"
  row 4 " Count 0"
  record CURSOR
> key Enter
message of 42 bytes
  record CURSOR
message of 168 bytes
  101/0000 header keep "PYTHON"
  packet X/27
  row 4 " Count 1"
  record CURSOR
```

### 2.16 A program with no kit

The protocol is the interface, and a kit is a convenience. This is the whole of a channel of one page, in the Python standard library. Reading it shows what a kit does for you. Note `flush=True`: a program must flush every line at once (REQ-1348), and standard output to a pipe is otherwise held back.

```python
#!/usr/bin/env python3
"""A channel with no kit: one page, written line by line on the protocol."""
import base64
import json
import sys

COLUMNS = 40
ROWS = 25
BLANK_CONTROL = dict.fromkeys(
    ("erase", "newsflash", "subtitle", "suppress_header", "update",
     "interrupted_sequence", "inhibit_display", "magazine_serial"), False)
INDEX = [{"magazine": 1, "name": "Raw", "pages": [
    {"page": "100", "title": "Raw", "section": None, "subpages": 1}]}]


def row(text):
    """A row: base64 of 40 seven-bit codes (spaces after the text)."""
    return base64.b64encode(text.ljust(COLUMNS).encode("ascii")).decode("ascii")


def subpage(words):
    """Page 100, sub-page 0000: every field is required."""
    rows = [None] * ROWS
    rows[0] = row(" " * 8 + "RAW")
    rows[2] = row(words)
    return {
        "page": "100", "sub": "0000", "rows": rows, "links": [None] * 6,
        "display_row_24": False,
        "link_extension": {"keys": [], "numbers": [], "texts": []},
        "control": BLANK_CONTROL,
        "character_set": {"region": None, "national_option": 0},
        "enhancements": [], "packets": [], "cursor": None,
    }


def send(message):
    """One line, flushed at once."""
    print(json.dumps(message, separators=(",", ":")), flush=True)


for line in sys.stdin:
    print("from server: " + line.strip()[:400], file=sys.stderr, flush=True)
    message = json.loads(line)
    kind = message["type"]
    if kind == "connected":
        wanted = message["selection"]
        if wanted is None or wanted["page"] == "100":
            send({"type": "reply", "connection": message["connection"], "request": message["request"],
                  "magazines": INDEX, "selected": subpage("Hello from raw.py")})
        else:
            send({"type": "reply", "connection": message["connection"], "request": message["request"],
                  "magazines": INDEX, "selected": None})
            send({"type": "denied", "connection": message["connection"], "request": message["request"], "status": 404})
    elif kind == "selected":
        if message["page"] == "100":
            send({"type": "page", "connections": [message["connection"]], "request": message["request"],
                  "page": subpage("You chose " + message["path"])})
        else:
            send({"type": "denied", "connection": message["connection"], "request": message["request"], "status": 404})
    elif kind == "input":
        event = message["event"]
        if event["kind"] == "key" and event["action"] == "press" and event["key"] == "Enter":
            send({"type": "unknown_message"})
            send({"type": "log", "level": "info", "event": "enter_pressed", "text": "Enter on page " + message["page"]})
    elif kind == "refused":
        print("refused: " + line.strip(), file=sys.stderr, flush=True)
```

It keeps no page and sends the index by hand. It also sends a line the server refuses, for the sake of the example, when Enter is pressed:

```
> select 100
message of 42 bytes
  record INDEX
message of 126 bytes
  100/0000 header erase "RAW"
  row 2 "Hello from raw.py"
  record CURSOR
> select 200
message of 42 bytes
  record DENIED
> select 100/0000
message of 126 bytes
  100/0000 header erase "RAW"
  row 2 "You chose 100/0000"
  record CURSOR

{"type":"refused","message":null,"path":"type","rule":"not_listed","detail":"unknown variant `unknown_message`, expected one of `reply`, `page`, `subpages`, `index`, `redirect`, `sound`, `cookie`, `author_log`, `log`, `packets`, `denied`"}
```

## Part 3: how to program them

### 3.1 Patterns the real channels use

Every TypeScript channel has the same shape: `src/main.ts` parses its arguments, loads its data, writes one line to standard error and calls `runChannel([new ComponentChannel(specs)])`. `src/pages.ts` makes the list of `PageSpec`s, so a test can make the same list. `vendor/` holds the tarballs. The small demosite and home channels are the ones to read first.

**One list of pages, one place for numbers.** demosite has `src/site/page-numbers.ts`, and each area in `src/pages/*/area.ts` names its pages. Home has `src/site/page-numbers.ts` too. No page number is written twice.

**Content as data.** Home's `src/channels.ts` is a plain list: adding a channel adds it to the front page and the directory, with its number and links. A page is a function of its data, as in `frontPage(channels)`.

**A shared live page.** demosite's markets, `src/pages/services/markets-page.ts`, is one component on the copy every viewer shares, with `setInterval` in `componentDidMount` and `setState`. The library publishes when the page changes, and the server sends the changed rows. One program does the work once for all viewers.

**A copy for each viewer.** demosite's calendar and adventure pages set `perViewer: true`, and state lives in the component. Where a spec leaves it out, the library asks the components whether they need a copy of their own.

**One page, many things.** Hackaday's reader, page 110, shows one article of thousands: `perViewer`, `keepWhileAway`, and `root: (params) => ...` reading `params?.["article"]`. A list sends the viewer there with `services.redirect(session, PAGES.reader, { article: id })`. demosite's picture page does the same, with `{ picture: name }`. A shared address does the same through the query. Because the value is from the viewer, the page looks it up and shows a placeholder if it is unknown.

**Many sub-pages on one page.** demosite's page 602 is hundreds of `RawSubPage`s, one copy for everyone. `Document` cuts a long text into sub-pages, as in `long-read-page.ts`. Only the sub-page selected ever travels.

**The server's figures on a page.** demosite's page 108 hears `stats` on the bus in `componentDidMount` and lets go in `componentWillUnmount`.

**A kit in one place.** Hackaday's `src/kit.ts` re-exports the protocol kit, so the rest of the program imports from one file.

**Loading at start.** Hackaday loads its library before calling `runChannel`, and reports how long that took on standard error. A page is drawn from what is in memory, so answers are fast. Remember that the 5-second deadline is running while a program starts.

**Reading data.** Hackaday's dataset is read only, by default `~/devel/neoteletext-hackaday`, or `--dataset DIR`. demosite's pictures are `--pictures FOLDER`, and without it the gallery says it has none. A channel with no data still runs.

**The UI demo.** `neoteletext-server-channel-uicomponentsdemo` is the library's own channel, with every component working, a page each. Look there first for how a component is used.

### 3.2 How to test a program

**The harness is the first tool.** `neoteletext-server-ts-protocol/testing` drives a channel as the server does, with no server, and every line is checked against the schema. A session has one connection, numbered as the session. A test is a viewer:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { Key } from "neoteletext-server-ts-protocol";
import { Harness, fakeOpus, shows } from "neoteletext-server-ts-protocol/testing";
import { guide } from "../src/guide.ts";

const [INDEX, CLOCK, FACTS, COUNTER] = [0x100, 0x101, 0x102, 0x103];
const STARTED = Date.UTC(2026, 10, 1, 12, 0, 0);

function channel(): Harness {
  return new Harness([guide(fakeOpus())], { epochMs: STARTED });
}

test("the clock changes with the time", () => {
  const harness = channel();
  harness.join(1, CLOCK);
  assert.ok(shows(harness.seen(1, CLOCK).rows, "12:00:00"));
  harness.advance(1_000);
  assert.ok(shows(harness.seen(1, CLOCK).rows, "12:00:01"));
});

test("a page's sub-pages are numbered by place", () => {
  const harness = channel();
  harness.join(1, FACTS);
  assert.deepEqual(harness.sharedPages(FACTS).map(({ subpage }) => subpage), [1, 2, 3]);
});

test("each viewer has a count of their own, from the address's query", () => {
  const harness = channel();
  harness.join(1, INDEX);
  harness.join(2, COUNTER);
  harness.open(1, COUNTER, undefined, "start=5");
  harness.press(1, Key.Enter);
  assert.ok(shows(harness.seen(1, COUNTER).rows, "Count 6"));
  assert.ok(shows(harness.seen(2, COUNTER).rows, "Count 0"));
  assert.deepEqual(harness.errors, []);
});

test("the sound goes before it is played", () => {
  const harness = channel();
  harness.join(1, COUNTER);
  harness.press(1, Key.Enter);
  assert.deepEqual(harness.sounds(1).map((message) => message["kind"]), ["opus", "play"]);
});

test("Escape goes to the index, and Home to another channel", () => {
  const harness = channel();
  harness.join(1, COUNTER);
  harness.press(1, Key.Escape);
  harness.press(1, Key.Home);
  assert.deepEqual(harness.redirects(1), [INDEX]);
  assert.deepEqual(harness.addressRedirects(1), ["https://app.neottx.com/home/"]);
});
```

And for the UI library:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { Key } from "neoteletext-server-ts-protocol";
import { Harness, shows } from "neoteletext-server-ts-protocol/testing";
import { ComponentChannel } from "neoteletext-server-ts-ui-components";
import { pages } from "../src/components.ts";

const COUNTER = 0x101;

test("each viewer has a count of their own", () => {
  const harness = new Harness([new ComponentChannel(pages)]);
  harness.join(1, COUNTER);
  harness.join(2, COUNTER);
  harness.press(1, Key.Enter);
  assert.ok(shows(harness.seen(1, COUNTER).rows, "Count 1"));
  assert.ok(shows(harness.seen(2, COUNTER).rows, "Count 0"));
  assert.deepEqual(harness.errors, []);
});

test("the address's query starts the count", () => {
  const harness = new Harness([new ComponentChannel(pages)]);
  harness.join(1, 0x100);
  harness.open(1, COUNTER, undefined, "from=5");
  assert.ok(shows(harness.seen(1, COUNTER).rows, "Count 5"));
});

test("green goes to the counter", () => {
  const harness = new Harness([new ComponentChannel(pages)]);
  harness.join(1, 0x100);
  harness.press(1, Key.Green);
  assert.deepEqual(harness.redirects(1), [COUNTER]);
});
```

```
$ node --test test/*.test.ts
ℹ tests 8
ℹ pass 8
ℹ fail 0
```

Name the files: `node --test test/` failed here, on Node 24.21.0.

| Harness | Does |
|---|---|
| `join(session, page)`, `open(session, page, sub?, query?)`, `close(session)` | A viewer comes, selects, goes |
| `press`, `key`, `typeKeys`, `typeText`, `paste`, `clickLeft`, `move`, `wheel`, `hover` | Input |
| `advance(ms)`, `runUntil(ms)` | The clock, waking the channel |
| `seen(session, page)`, `shared(page)`, `sharedPages(page)`, `ownPages(session, page)` | What the channel keeps |
| `shows(rows, words)`, `text(rows, row)`, `rowOf(rows, words)` | Read rows |
| `redirects`, `addressRedirects`, `at`, `sounds`, `sent`, `errors` | What was sent, and what failed |

Assert that `harness.errors` is empty: a failing application is reported there and does not fail the test by itself. The harness's `join` always selects a page, and its `open` goes through `selected`, so it does not reproduce the 1.5-second wait. A `harness.send` carries sub-code 3F7F, which a real receiver never does. It tests your program and not the server.

The real channels check more: `test/pages.test.ts` in each publishes every page and asserts nothing is reported. The UI library has snapshots, a catalogue and pictures (`docs/testing.md`). Each repository's `scripts/check.sh` runs its gates.

**A real receiver of your own.** To see what really goes down the wire, with no browser, this is a receiver in a hundred lines. Node's own `WebSocket`, on 24.21.0 here, sends no `Origin`, so the server takes it. It prints each message's packets and draws nothing. Each step waits for the last answer to go quiet. A slow program looks like silence, so give it a `wait:` when you expect one. It is the source of every transcript here.

```ts
// A receiver in a hundred lines, for looking at what a channel sends:
//   node probe.ts ws://127.0.0.1:8090/guide/push 'place or key:NAME or wait:MS' ...
// Each step runs after the last frame, in order. It is not a browser: it
// prints each message's packets and draws nothing.
const VERSION = 7;
const SELECT_CAPABILITY = 4_194_304;
const CURSOR_CAPABILITY = 131_072;
const EVENT = 0xff;
const HELLO = 0x09;
const SELECT = 0x40;
const KEY = 0x01;
const PACKET_BYTES = 42;
const RECORD_NAMES = new Map([[1, "OBJECT"], [2, "DATA"], [3, "CONTROL"], [4, "CURSOR"], [5, "WELCOME"], [6, "INDEX"], [7, "LOG"], [8, "SET_COOKIE"], [9, "LINKS"], [10, "SUBPAGES"], [11, "REDIRECT"], [12, "DENIED"]]);
const FUNCTIONAL_FLAG = 4;
const KEY_CODES = new Map([["Escape", 1], ["Enter", 2], ["Home", 13]]);
const SETTLE_MS = 400;

/** INPUT.md section 5.2's `uv`. */
function uv(value: number): number[] {
  const bytes: number[] = [];
  let rest = value;
  while (rest >= 0x80) {
    bytes.push((rest % 0x80) | 0x80);
    rest = Math.floor(rest / 0x80);
  }
  return [...bytes, rest];
}

/** The four data bits of a Hamming 8/4 byte (EN 300 706 clause 8.2). */
function hamming(byte: number): number {
  return ((byte >> 1) & 1) | (((byte >> 3) & 1) << 1) | (((byte >> 5) & 1) << 2) | (((byte >> 7) & 1) << 3);
}

const [url = "", ...steps] = process.argv.slice(2);
let onPage = { page: 0, sub: 0 };

function describe(packet: Uint8Array): string {
  const address = hamming(packet[0] ?? 0) | (hamming(packet[1] ?? 0) << 4);
  const magazine = address & 7 || 8;
  const row = address >> 3;
  if (row === 0) {
    const units = hamming(packet[2] ?? 0);
    const tens = hamming(packet[3] ?? 0);
    const sub = hamming(packet[4] ?? 0) | ((hamming(packet[5] ?? 0) & 7) << 4) | (hamming(packet[6] ?? 0) << 8) | ((hamming(packet[7] ?? 0) & 3) << 12);
    const erase = (hamming(packet[5] ?? 0) & 8) !== 0;
    onPage = { page: (magazine << 8) | (tens << 4) | units, sub };
    return `${onPage.page.toString(16).toUpperCase()}/${sub.toString(16).toUpperCase().padStart(4, "0")} header ${erase ? "erase" : "keep"} "${text(packet.slice(10))}"`;
  }
  if (row === 31) {
    const type = packet[7] ?? 0;
    return packet[5] === 0 ? `record ${RECORD_NAMES.get(type) ?? type}` : `record, fragment ${packet[5]}`;
  }
  return row < 26 ? `row ${row} "${text(packet.slice(2))}"` : `packet X/${row}`;
}

/** Display bytes as text: parity off, what is not printable a space. */
function text(bytes: Uint8Array): string {
  return String.fromCharCode(...Array.from(bytes, (byte) => byte & 0x7f).map((code) => (code < 0x20 || code === 0x7f ? 0x20 : code))).trimEnd();
}

function selectEvent(place: string): Uint8Array {
  const bytes = new TextEncoder().encode(place);
  return Uint8Array.from([EVENT, SELECT, ...uv(bytes.length), ...bytes]);
}

function keyEvent(name: string): Uint8Array {
  const code = KEY_CODES.get(name) ?? 0;
  return Uint8Array.from([EVENT, KEY, ...uv(onPage.page), ...uv(onPage.sub), FUNCTIONAL_FLAG, ...uv(code)]);
}

const socket = new WebSocket(url, ["neottx.7"]);
socket.binaryType = "arraybuffer";
let timer: NodeJS.Timeout | undefined;

function nextStep(): void {
  const step = steps.shift();
  if (step === undefined) {
    socket.close(1000);
  } else if (step.startsWith("wait:")) {
    timer = setTimeout(nextStep, Number(step.slice(5)));
  } else if (step.startsWith("key:")) {
    console.log(`> key ${step.slice(4)}`);
    socket.send(keyEvent(step.slice(4)));
    settle();
  } else {
    console.log(`> select ${step}`);
    socket.send(selectEvent(step));
    settle();
  }
}

function settle(): void {
  clearTimeout(timer);
  timer = setTimeout(nextStep, SETTLE_MS);
}

socket.addEventListener("open", () => {
  console.log(`open, subprotocol ${socket.protocol}`);
  socket.send(Uint8Array.from([EVENT, HELLO, ...uv(VERSION), ...uv(SELECT_CAPABILITY | CURSOR_CAPABILITY)]));
  settle();
});
socket.addEventListener("message", (event: MessageEvent<ArrayBuffer>) => {
  const bytes = new Uint8Array(event.data);
  console.log(`message of ${bytes.length} bytes`);
  for (let at = 0; at < bytes.length; at += PACKET_BYTES) {
    console.log(`  ${describe(bytes.slice(at, at + PACKET_BYTES))}`);
  }
  settle();
});
socket.addEventListener("close", (event) => {
  clearTimeout(timer);
  console.log(`closed ${event.code}`);
});
socket.addEventListener("error", () => {
  console.log("the upgrade failed");
});
```

```sh
node probe.ts ws://127.0.0.1:8090/guide/push 100 '103?start=5' key:Enter wait:300
```

`neoteletext-common/wire-vectors.tsv` holds the bytes to check it against. `INPUT.md` section 15.2 lists the required core of a receiver. `neottx view`, in the engine, is a real receiver in a terminal (`INPUT.md` section 9.6). It was not run for this guide.

**Your log.** Run with `--log-format text` and read it. A program that logs each line it reads on standard error, as `raw.py` does, shows the whole conversation. `/stats.json` shows `refused` and `lines_dropped`. `RUST_LOG=connection=debug,info` shows connections open and close.

**Then the browser.** Open `http://127.0.0.1:8090/guide/` with the NeoTeletext browser. The harness and the probe show what was sent, and only the browser shows how it looks. This guide did not open one.

### 3.3 Common faults

| What you see | Why | What to do |
|---|---|---|
| 426 from `push` | The subprotocol is missing or another version | Offer `Sec-WebSocket-Protocol` as the version table says |
| 403 from `push` | The upgrade carried `Origin`, as any web page's script does | A receiver cannot be a web page |
| Closed 4001 | HELLO named another version | Update the receiver |
| Closed 4000 | The receiver broke the protocol. A key stamped with page 0, sent before any page arrived, did this in a run here | Wait for a page before sending input |
| DENIED, `program_late` in the log | The program did not answer within 5 seconds, or none is running | Check that it is running, that it flushes its lines, and that it does not block. It also happened here once just after a restart on a heavily loaded machine, and the cause there was not pinned down |
| 200 from `/readyz`, and viewers still DENIED | Ready means the program started, not that it has loaded | Load fast. A late page for a selection is still shown (`INPUT.md` section 5.4) |
| `refused`, rule `syntax`, path empty | Something other than a protocol line reached standard output, such as a stray print | Write to standard error. A run with one `print` showed `"rule":"syntax","detail":"expected value at line 1 column 1"` |
| Nothing happens and no error | Standard output is buffered | Flush each line. The kits do |
| `ProtocolError` on standard error | The kit refused a message before writing it | Read the path and rule |
| `magazine: out_of_range`, or a page never found | A page number in decimal: `100` is not `0x100` | Write page numbers in hexadecimal |
| `publish: no application serves 1A0` | The page is not in `pages()` | Declare it |
| A sound never plays, a log line never comes | Sent in `joined`, before the connection exists | Send in `opened` |
| A sound is refused | `fakeOpus` output, or packets outside the profile, reached a real server | Use `ffmpegOpus`, and `fakeOpus` only in tests |
| Digits or coloured keys never reach `input` | Navigation took them | Set `ownsDigits` or `ownsColourKeys` |
| A click on row 23's "prompt" does nothing | Prompts are followed on row 24 only | Use row 24, and `screen.fastext` |
| The first letter of a line is lost, or colours run on | An attribute takes a cell | `coloured` writes the attribute at `column` and the text one on |
| A row vanishes under a heading | Double height covers the row below | Leave it empty |
| Row 0's first eight columns are not yours | They are the receiver's | Use `screen.header`. Columns 8 to 39 are the page's, and the server never rewrites them |
| Another viewer sees a viewer's page | Published to `"channel"` | Publish to `session` |
| A session's state is gone, or it lingers | `ended` comes 5 minutes late, and a restart loses memory | Key state by session, drop it in `ended`, keep what matters elsewhere |
| A cookie you set is not in `request.cookies` | Cookies are those the connection opened with | It arrives on the next connection |
| The kit prints `the server speaks protocol N` | The kit is older or newer than the server | Take the matching tarball. There is no compatibility path |
| Hackaday or the gallery is empty | The dataset or pictures are not there | Give `--dataset` or `--pictures` |
| A channel at `/100/` | The server accepts the folder, and the URL map says it cannot be a channel | Choose another name |

## What this guide could not settle

- **Cloudflare.** Nothing here was run on it.
- **A real receiver.** No browser and no `neottx view` was run. The probe proves what is sent. Whether a sound plays, or a link is followed, was not seen.
- **`describe` and public pages.** These were being written as this was. The small page at a page's address will change.
- **The reply limit.** 5,000 ms is marked provisional in the code, until TODO-1521 measures it.
- **Real systemd.** Socket activation was run with a shell standing in for systemd, and `deploy/ionos/deploy.sh` was read and not run.
- **`stale_answers`.** `SERVER.md` section 7.6 says dropped answers are counted. The runtime counts them, but neither `/stats.json` nor `stats` shows that figure at this commit.
- **Flush policy and slow clients.** `SERVER.md` section 20 item 10 leaves them open, and at this commit a connection 256 messages behind loses the newest, which is not what section 6.4 proposes.
