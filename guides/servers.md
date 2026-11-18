# The NeoTeletext servers, and how to program them

This guide is for a programmer who will run the server and write programs for it. Part 1 is the Rust server. Part 2 is the protocol kit and the UI library in TypeScript, and what differs in Python. Part 3 is how the real channels are written, how to test a program, and what usually goes wrong.

To make a channel step by step, read [Creating a channel](creating-a-channel.md). This guide explains what stands behind those steps. The protocol itself is [PROTOCOL.html](../PROTOCOL.html): where this guide and an item of it differ, the item holds.

This edition describes program protocol 15 and push protocol 10, the second form of the page rule table, as built on the branches named in the version table on 19 November 2026. It was written by reading the code and the generated schema at those commits. One thing was run for it: the small channel of section 2.13 and its test, against the TypeScript kit at the commit named, whose output is pasted there. Everything else the guide shows of messages is written from the schema and the protocol's items, not pasted from a run, and says so where it could be mistaken for one.

## Versions

Every version number belongs in this table. The rest of the guide says "the program protocol" and "the push protocol".

| What | Now | Where it is defined |
|---|---|---|
| Program protocol, server to program | 15 | `PROTOCOL` in `neoteletext-app-server/crates/teletext-runtime/src/protocol.rs` |
| Its schema | `protocol/schema-15.json` | `neoteletext-app-server`; each kit keeps a copy |
| Push protocol, receiver to server | 10 | the engine's `neoteletext-input`; [DOC-1921](../PROTOCOL.html#DOC-1921) |
| WebSocket subprotocol | `neottx.10` | `PUSH_SUBPROTOCOL` in the engine's `neoteletext-web`; `wire-vectors.tsv` |
| TypeScript protocol kit | 17.0.0, speaks program protocol 15 | `neoteletext-server-ts-protocol/package.json`, branch `protocol-15`, `d3b237e` |
| UI library | 25.0.0, on kit 17.0.0 | `neoteletext-server-ts-ui-components/package.json`, branch `protocol-15`, `42d1cb0` |
| Python kit | 0.1.0, speaks program protocol 15 | `neoteletext-server-channels/kits/python`, branch `protocol-15`, `da43bf4` |
| Server | branch `protocol-15`, `3446386` | `neoteletext-app-server` |
| Engine, pinned by the server | `33d90896` | `neoteletext-app-server/Cargo.toml` |
| Rust | 1.99.0 | `neoteletext-app-server/rust-toolchain.toml` |
| Node | 22.18 or later | each `package.json`; the run here was on 24.21.0 |
| Python | 3.13 or later | `kits/python/pyproject.toml` |

A kit's version and the protocol's are separate numbers: kit 17.0.0 speaks program protocol 15. None of these branches was merged or deployed when this was written.

## Part 1: the Rust server

### 1.1 What it is for

The server is a teletext application server. Receivers connect to it. A program, in any language, makes each channel's pages. The server stands between them:

- To a receiver it speaks teletext. What it sends is 42-byte packets, and the messages joined together are a plain T42 stream.
- To a program it speaks typed JSON, one object a line.
- It translates between the two, checks everything, and sends each connection only what changed in the one sub-page that connection shows.

The rule that shapes the rest is that **the server relays and the program owns every page** (DEC-1482). The server has no page store. It never answers a viewer from a copy. Every sub-page a viewer sees is one the program sent for them. The program does not have to be fast at this: the kits keep the pages and answer for it.

The same holds for a page's **rule table**, the declarations by which a page asks for the viewer's input and answers some of it in the browser with no round trip ([the page rule table](../PROTOCOL.html#DOC-6581)). The server checks a table with the receiver's own code and sends it, and keeps none: a program sends a page's table at every selection of it.

One program serves every viewer of its channel, and there is no process per viewer.

### 1.2 The crates

The workspace is in `~/devel/neoteletext-app-server`. Teletext itself, the page model, the encoder, the push protocol, the rule table's codec and checks, and the audio profile, comes from the engine at one pinned commit and is never copied.

| Crate | What it holds | What it never does |
|---|---|---|
| `teletext-runtime` | One channel as a state machine: connections, selections, the program protocol's types and checks, rule tables and their names, timelines, the changed-rows sender, viewer state's handles, and what a channel's address answers | No input or output, no clock, no threads. It is `no_std` |
| `teletext-native` | The server on Linux, macOS and Windows: tokio, hyper, the program supervisor, WebSocket framing, the state directory, the log and the figures. It builds `teletext-server` and the load client `teletext-load` | No teletext logic |
| `teletext-cloudflare` | The same runtime as a Worker and one Durable Object for each channel. See section 1.13 | It is empty on every target but `wasm32` |

The runtime takes events and answers with effects. A host gives it what happened, with the time, and carries out the result:

```
host to runtime:  opened, received, closed, from_program, program_started, program_ended, deadline
runtime to host:  Send (bytes for a connection), Close, ToProgram (a line), Log
```

So a test of the runtime needs no network, and the clock is whatever the test says. In the native host, each channel is one tokio task holding one runtime. A channel is single-threaded, and channels run in parallel. `crates/teletext-native/src/hub.rs` is that task.

### 1.3 A request, from a receiver to a program and back

```
receiver ══ WebSocket, packets down, input up ══ server ── lines of JSON ── program
                                                  one task
                                                  a channel
```

A receiver opening a channel does this:

1. **It fetches `<channel>channel.ttx`.** This says the channel is live and gives its first page. Its `push` object declares nothing of input.
2. **It upgrades `<channel>push` to a WebSocket,** offering the subprotocol. The server answers 101. No cookie is sent or set.
3. **It sends HELLO** with the push protocol's version and its capabilities. The server answers with WELCOME.
4. **It sends SELECT**, naming the page. This is the first selection.
5. **The server tells the program.** It has held `connected` until now, so a shared link goes straight to its page. The wait lasts at most 1.5 seconds. A receiver without the SELECT capability is not waited for.
6. **The program answers with `reply`,** holding the channel's index and the one sub-page, and sends the page's rule table with `rules` if it has one.
7. **The server checks every line and sends.** Before the page it sends a RULES record: the program's table, or the channel's default table, or a record that says the page has no table (section 1.7). The index goes as index records, the sub-page as a page frame, and any Link Extension links as a LINKS record.

Each later choice is a new SELECT, which reaches the program as `selected`. The answer is one `page` message, and the page's table again: every selection is a new one for the table, and the server keeps nothing of the last.

When the same page is sent again with one row changed, the server compares it with what that connection was last sent and sends only the header and the changed row, without the erase bit.

**Input goes the other way, only as the page asked.** The receiver gives the open page's table the viewer's events the moment they happen. The table may answer some itself, in the receiver: play a note, change a look, move an object. What a rule of the table reports, and only that, leaves the receiver as a RULE_EVENT, built by the receiver's trusted part from its own copy of the event. A page with no table sends nothing of what the viewer does. The server unpacks a RULE_EVENT and gives the program `input`, naming the rule that reported it, or `rule_event` for a report with no input event.

What the program sees, written from the schema (not pasted from a run), for a viewer who opens page 101, whose table reports Enter, and presses it:

```
{"type":"start","protocol":15,"epoch_ms":…,"standard":{…},"budgets":{…},"languages":[…]}
{"type":"connected","connection":1,"request":1,"selection":{"page":"101","sub":"3F7F"},"path":"101","query":null,"viewer":null,"remembered":false}
{"type":"input","connection":1,"page":"101","sub":"0000","lost":false,"rule":"enter","row":null,"tick":95,"target":null,"event":{"kind":"key","action":"press","key":"Enter",…}}
{"type":"left","connection":1,"page":"101"}
{"type":"gone","connection":1}
```

`left` comes before `selected` when the page changes, and it does not come for a step between sub-pages of one page. `gone` comes when the connection closes: there is no session that outlives a connection.

### 1.4 The two protocols

The two protocols are kept apart on purpose. The first is binary, for a small trusted receiver. The second is JSON, for people.

**The push protocol** runs on the push WebSocket, and [DOC-1781](../PROTOCOL.html#DOC-1781) and [the page rule table](../PROTOCOL.html#DOC-6581) are its definition.

- **The upgrade.** The request must offer the subprotocol, or it is answered 426, naming the one spoken. A request that carries `Origin` is answered 403, whatever it offers. A web page's script always sends `Origin`, so a receiver cannot be written in a web page.
- **Upstream.** Binary events, each `0xFF`, a type byte and its fields, at most 8,192 bytes a message. At the top level go the session's messages, HELLO, RESIZE, SELECT and RESUME, and viewer state's; the table's reports, RULE_EVENT; and PAGE_STATE and RULES_FAULT. The viewer's input, KEY, MOUSE, WHEEL, PASTE, COMPOSE, TOUCH, FOCUS_IN, FOCUS_OUT, HOVER and raw text, travels only inside a RULE_EVENT: at the top level it is a protocol error, and the server closes the connection with 4000.
- **Downstream.** Binary messages only, each a whole number of 42-byte packets. Joined, they are a valid T42 file. Page frames carry one sub-page. Everything else is a record on packet 4/31, data channel 12: WELCOME, cursor, index, LOG, LINKS, SUBPAGES, REDIRECT, DENIED, sound, the rule table's RULES and RULES_QUERY and its six command records, and animation's records.
- **Closing.** 4000 means the receiver broke the protocol and 4001 means another version, and on either a receiver stops. 4100 means a restart, and a receiver tries again.
- **The bytes.** `neoteletext-common/wire-vectors.tsv` has real messages for each of these, the rule table's worked examples and the default table among them. Anyone implementing a receiver should run that file.

**The program protocol** runs between the server and a program. It is defined once, by the Rust types in `crates/teletext-runtime/src/protocol.rs`, and published as a JSON Schema generated from them, `protocol/schema-15.json`. `$defs/ServerMessage` is what the server sends and `$defs/ProgramMessage` is what a program sends. The schema is the exact contract. [DOC-1968](../PROTOCOL.html#DOC-1968) and [DOC-1970](../PROTOCOL.html#DOC-1970) say what each message is for, and section 2.4 of this guide lists them.

- One JSON object a line, UTF-8, ending in `\n`, at most 16 MiB.
- Every message has a `type`. An unknown `type` or field is refused, never skipped.
- Each line is checked whole and refused whole. The program is sent `refused`, and the reason goes to the log. Nothing of a refused line is acted on. A rule table is checked with the engine's own check, the receiver's code, so a table the server accepts is one every receiver decodes.

Three kinds of number and name matter:

- **`connection`** is one browser tab, from its connection to its `gone`.
- **`viewer`** is the viewer's handle on this channel, when the viewer has given state, the same across that viewer's tabs; otherwise `null` ([connections and viewer state](../PROTOCOL.html#DOC-1924)).
- **`request`** is the number of a connection's selection, rising from 1. A program copies it into its answer. The server drops an answer whose number is not current, so a late answer cannot replace the page on screen. The kits copy it for you.

### 1.5 One selection a connection

A connection is one browser tab. It has one **selection**, or none: one page and one sub-code. A sub-code of `3F7F` means the page and none of its sub-pages in particular. It is answered with the page's first sub-page in ascending order, and that sub-page then is the selection.

**A sub-page is a page.** Everything the rule table and animation do is keyed on the page number and the sub-code together (DEC-6599): each sub-page has its own table, its own variables, its own sprites. Every message that concerns a page's table or its animation names `page` and `sub`, and none may name `3F7F`.

Three words are defined once in [DOC-1933](../PROTOCOL.html#DOC-1933). **Selected** is what a tab shows. **Active** is what a selected page is to the server: it gets every update. **Focused** is for input only. A page in a tab behind another stays selected and updated, and its table is paused: it evaluates nothing and reports nothing.

Nothing rotates on a live channel. The sub-page a connection shows changes only when the receiver selects another, or when the program sends a page redirect.

**What the server keeps**, in memory, for one open connection:

- its selection, with that selection's query and number, and its viewer handle, if any;
- the one sub-page last sent to it, for taking changed rows against;
- whether a table is in place on its page, the names of the last four tables sent (so that a late report can be named), the default table's use, and a generation counter;
- the sheet stream it is being sent for the page selected, its timelines, and an open frame;
- what it holds down that a rule reported, so that releases can be given to the program if the connection goes;
- which version of the page's sub-page list it holds;
- the deadline of its selection.

It keeps no table, animation state, sprites, objects or sheet for a later viewer: a program is told of every selection and sends the page afresh. For the channel it keeps the sound command numbers and the viewer-handle table. On disk, in the state directory, it keeps the viewer-handle secret and the accumulated figures, and nothing of any channel's content.

**What the server relays:**

| A program sends | A viewer gets |
|---|---|
| `reply` | Index records, then the sub-page as a page frame |
| `page` | The sub-page, only if the connection's selection shows it. Whole with the erase bit the first time after a new selection, and after that only the changed rows, or nothing if nothing changed |
| `subpages` | A SUBPAGES record, if the connection does not hold that version |
| `index` | Index records |
| `redirect` | A REDIRECT record. A page redirect is a selection, so the program is then sent `selected` |
| `denied` | A DENIED record. The connection stays open |
| `rules` | RULES records, the table's image in fragments, to the connections that have that page and sub-code selected |
| `local_midi`, `variable`, `timer`, `report`, `run`, `sequence` | One command record each, applied by the page's table |
| `query_state` | A RULES_QUERY record; the answer comes back as `page_state` |
| `frame`, `animate`, `sprites`, `naplps_objects`, `sprite_sheet`, `object_page` | Animation's records, or an object page's packets |
| `timeline` | ANIMATE records, sent by the server as each step falls due on its own clock |
| `sound` | Audio records |
| `regis`, `regis_links`, `regis_cursor`, `naplps` | A ReGIS or NAPLPS picture's own records |
| `request_state`, `end_state`, `offer_remember` | Viewer state's messages on the push connection |
| `author_log` | A LOG record, for the viewer's developer console |
| `packets` | The packets, each checked with the engine's stream check |
| `log` | Nothing: it goes to the server's log |

Every selection has an ending: a page, DENIED, or a deadline. After 5 seconds without an answer, the server sends DENIED 503 itself and logs `program_late`. If no program is running, DENIED 503 goes at once.

### 1.6 What an ordinary web browser is answered with

The server answers HTTP only as the URL map says. [DOC-1914](../PROTOCOL.html#DOC-1914) is the definition.

| Request | Answer |
|---|---|
| `/guide/` | 200, the small page |
| `/guide/contents`, `/guide/wall`, `/guide/302/0002` | 200, the same small page, repeating that address |
| `/guide` | 308 to `/guide/` |
| `/guide/302/?a=1` | 308 to `/guide/302?a=1` |
| `/guide/channel.ttx` | 200, JSON, generated |
| `/guide/push` | 426 without a proper upgrade |
| `/guide/channel.json`, `/guide/100.tti`, `/guide/302/2`, `/`, `/nothere/` | 404 |

Pages are never served over HTTP. A live channel's pages travel only on its connection. A page a program marks public is described to a web visitor in its small page (section 2.4, `describe`).

`channel.ttx` is generated as `{"name":"Guide","initial_page":"100","push":{}}` (the server's test `the_descriptor_names_no_push_address_and_asks_for_no_input`). The empty `push` object makes the channel live; `push.input` and `push.wheel` are withdrawn, and a receiver reads past them ([channel.ttx](../PROTOCOL.html#DOC-1865)). `initial_page` is the channel's entry's `initial_page` in the channels file, 100 when it gives none.

The small page runs no script and holds nothing from the program, and is sent with `content-security-policy: default-src 'none'`, `x-content-type-options: nosniff` and `referrer-policy: no-referrer`. Only `GET` and `HEAD` reach it.

### 1.7 The channels file

`--channels FILE` names what the server serves. Without it there are no channels, and every address answers 404.

```json
{"channels":[
  {"folder":"guide","name":"Guide","command":["node","src/main.ts"],"directory":".","default_rules":"none"},
  {"folder":"home","name":"Home","command":["node","src/main.ts"],"directory":"../home","default_rules":"send_all","wheel":true},
  {"folder":"service","name":"Service","socket":"sockets/service.sock"}
]}
```

- **`folder`** is the channel's address, of letters, digits, `-` and `_`. [DOC-1908](../PROTOCOL.html#DOC-1908) says a folder named `contents`, `wall` or like a page number cannot be a channel, and the server stops naming such a folder.
- **`name`** is shown to viewers. It defaults to the folder.
- **`initial_page`**, three decimal digits, is the page the channel's viewers start on, 100 when left out.
- **`command` and `directory`** have the server start the program, on standard input and output. A relative `directory` is taken from the channels file's own folder. The program gets `NEOTELETEXT_CHANNEL`, its folder.
- **`socket`**, in place of those, has the server listen on a Unix domain socket, and the program runs as a service of its own, connecting with the socket's path in `NEOTELETEXT_SOCKET`. A relative path is taken from the file's folder. The folder, if made, is `0700` and the socket `0600`, and those permissions are the authentication. One program at a time: a second is closed. Linux and macOS only.
- **`secret_variable` or `secret_file`**, in place of those, is for a program that connects over a WebSocket to `<channel>program` with the channel's secret: the environment variable or file that holds it, never the secret itself.
- **`default_rules`**, `"none"` (the default) or `"send_all"`, is what a page has when its program gave it no rule table ([the default table](../PROTOCOL.html#DOC-6600)). With `"none"` such a page is sent a RULES record that says it has no table, and its viewer's input reaches nobody. With `"send_all"` it is sent the default table: twelve rules, `keys`, `keys_up`, `text`, `press`, `release`, `move`, `hover_in`, `hover_out`, `drawing_in`, `drawing_out`, `focus` and `blur`, each reporting every event of its kind, so a channel written before the rule table keeps hearing its input unchanged, each `input` naming one of those rules. The nine channels deployed on 18 November 2026 are given `"send_all"` until each moves to tables of its own; a new channel should have `"none"` and send each page the table it needs.
- **`wheel`**, true or false and false when left out, adds a thirteenth rule, `wheel`, to the default table.

A program that ends is started again after 1 second, then 2, 4 and on up to 30. One that ran for 5 seconds or more was ended and not failing, and is started again at once. A restarted program is sent `start`, then `connected` for every open connection, and each connection's page is sent, for its selection, the empty table or the default, which drops whatever the old program's table held in the receiver: the new program sends each page afresh.

The repository's real file is `~/devel/neoteletext-server-channels/channels.json`.

### 1.8 Ports and socket activation

| Flag | Default | What it does |
|---|---|---|
| `--listen ADDRESS` | `0.0.0.0:8090` | Where viewers connect |
| `--origin URL` | `http://127.0.0.1:8090` | The address viewers reach it at. It makes the small page's link, and each channel's push WebSocket is named on it |
| `--channels FILE` | none | Section 1.7 |
| `--state DIRECTORY` | `$STATE_DIRECTORY`, else none | The viewer-handle secret and the accumulated figures |
| `--admin-listen ADDRESS` | none | `/metrics`, `/stats.json`, `/healthz`, `/readyz`. Never put this on the viewers' address |
| `--log-format auto\|json\|text` | `auto` | JSON when standard error is not a terminal |
| `--trusted-proxy ADDRESS` | none | The reverse proxy in front, whose `X-Forwarded-For` then names each viewer's address for the bound on new viewers from one address |

The server speaks plain HTTP/1.1 and has no TLS. Something in front of it terminates TLS, as Caddy does in production (section 1.12).

Without `--state`, the viewer-handle secret is made for that run, so a restart gives every viewer a new handle and the figures start from nothing. `teletext-server rotate-viewer-secret --state DIRECTORY` makes a new secret for the next start: every channel then forgets every viewer and each program is told `viewers_reset`. Do it only after a breach of a program's data or of the state directory.

**Socket activation** (REQ-1041, DEC-1767). When systemd passes a listening socket, the server takes it and ignores `--listen`. systemd holds the socket across a restart, so a connection made while the server restarts waits in the socket's queue and is answered. More than one passed socket is an error. The socket is made close-on-exec, so programs do not inherit it. The unit is `deploy/ionos/neoteletext.socket`. Restarting the service keeps the socket. A changed address needs `systemctl restart neoteletext.socket`. A connection to the socket starts the service, so stopping the server for good means stopping the socket unit too.

On `SIGTERM` or `SIGINT` the server closes every viewer with 4100, keeps its figures and exits, within 10 seconds.

### 1.9 Limits

The bounds a program and a receiver must keep are in [what the server tells a program](../PROTOCOL.html#DOC-1968), [every address is accepted](../PROTOCOL.html#DOC-1807) and, for a rule table, [the limits](../PROTOCOL.html#DOC-6682). This section says how they feel in use, and defines nothing.

Maxima are not limits: every page and sub-page the standard allows may exist, and a program learns them in `start`. These are budgets, which bound what is held at once.

| What | Value | Where |
|---|---|---|
| One line, either way | 16 MiB | `protocol.rs`, `LONGEST_LINE` |
| One upstream WebSocket message | 8 KiB | `websocket.rs`, `MAX_MESSAGE` |
| One downstream WebSocket message | 64 KiB, cut before a sub-page's header where it can be | the engine's `DEFAULT_PUSH_LIMIT`, `frame.rs` |
| Messages waiting for one connection | 256, and the newest are lost beyond that | `hub.rs`, `OUTBOX` |
| Lines waiting for a program | 4,096, and the newest are dropped and logged | `apps.rs`, `WAITING_LINES` |
| Answer to `connected` or `selected` | 5,000 ms, provisional | `channel.rs`, `PROGRAM_REPLY_LIMIT_MS` |
| Wait for a first selection | 1,500 ms | `channel.rs`, `FIRST_SELECTION_WAIT_MS` |
| Connections named in one message | 4,096 | `protocol.rs` |
| A title, a magazine name, a section | 120 characters | `protocol.rs` |
| A sub-page's title in its list | 40 characters | `protocol.rs` |
| An operator's log line, an author's log line | 1,000 characters, 200 bytes | `protocol.rs`, the engine |
| A rule table: rules, triggers, groups, commands, rows, rectangles, sequences, its image | The constants of the engine's `neoteletext_rules::limits`, stated once in neoteletext-common's REQ-6608 | the engine; a refusal names the constant and its value |
| State queries | one a second for a connection and page; unanswered after 10 seconds | `channel.rs` |
| Timelines | 16 playing for one connection and page, 64 for one connection | the server's animation |
| A line of a program's standard error | 64 KiB logged, the rest cut | `apps.rs` |
| Keepalive | a connection silent for 35 s is pinged, and one silent 10 s more is dropped | `connection.rs`, from the engine's constants |

### 1.10 Logging and figures

Events go to standard error through `tracing`, one a line. `RUST_LOG` chooses levels and targets, as `RUST_LOG=info` or `RUST_LOG=channel=debug,info`. The targets are `program`, `channel`, `connection`, `figures` and `state`. A program's standard error becomes the log, a line an event, under `program`. Its `log` messages appear under `channel`. A receiver's report that it could not decode a page's table (`rules_fault`, `undecodable`) is also written to the log as an error.

The server counts and never records who a viewer is. On the administration listener:

- **`/healthz`** answers `ok`.
- **`/readyz`** answers 200 `ready`, or 503 when a channel's program is not answering. Ready means the channel's program has answered something since it started, so it can answer a viewer. The server asks it with one `describe` when it starts, for the page viewers arrive at. A program that is loading is not ready, and in that time a viewer is told DENIED 503.
- **`/metrics`** is the Prometheus text format, since the process started: among others `teletext_connections`, `teletext_connections_total`, `teletext_program_restarts_total`, and for each channel `teletext_channel_viewers`, `teletext_channel_inputs_total`, `teletext_channel_keys_total`, `teletext_channel_refused_total`, `teletext_channel_stale_input_total`, `teletext_channel_stale_answers_total`, `teletext_channel_subpages_not_forwarded_total`, `teletext_channel_proofs_accepted_total`, `teletext_channel_proofs_refused_total` and `teletext_channel_ready`.
- **`/stats.json`** holds the same figures for every channel, with an `all_time` block when there is a state directory.

A program gets the same as `stats` every 10 seconds. The kits pass it on, and demosite's page 108 shows it.

The figures to watch while writing a program are `refused`, `lines_dropped`, `invalid_packets`, `stale_input` and `stale_answers`. All should stay at 0, apart from the odd `stale_input`, which is a report of a key pressed while a page changed, and the odd `stale_answers`, which is a viewer moving on before the program answered.

### 1.11 Build and run it locally

```sh
cd ~/devel/neoteletext-app-server
cargo build -p teletext-native
target/debug/teletext-server --listen 127.0.0.1:8090 --origin http://127.0.0.1:8090 \
    --channels ~/devel/neoteletext-server-channels/channels.json \
    --admin-listen 127.0.0.1:9464 --state tmp/state --log-format text
```

If another worker is using the repository's `target`, set `CARGO_TARGET_DIR` to a folder of your own. The engine comes from the repository the `Cargo.toml` names, so a first build may need the network.

The server needs no program to start. `--channels` may name any file you like, and section 2.13 has a one-channel program. Stop it with Ctrl-C, or `kill -TERM`.

`scripts/check.sh commit`, `push` and `full` are the repository's gates, and `~/devel/neoteletext-common/DEVELOPMENT.md` section 9 says how they work. `scripts/try.sh <crate> [filter]` is the edit loop. On 19 November 2026 `cargo test -p teletext-runtime --locked` at `3446386` passed 369 tests and ignored one; the rule table's are in `crates/teletext-runtime/src/protocol/tests/rules.rs` and `crates/teletext-runtime/src/channel/tests/rules.rs`, animation's in `channel/tests/animation.rs`.

`teletext-load --url ws://HOST:PORT/FOLDER/push --connections N [--page 105] [--seconds 60]` opens many connections and measures fan-out.

### 1.12 How it is deployed

This describes `deploy/ionos/deploy.sh`, read and not run. It deploys to the `neoteletext` container on crowdwaveaudio.

```
internet ── caddyrouter, TLS ── container Caddy :8080 ── 127.0.0.1:8090 teletext-server
                                                     └── /opt/neoteletext/current/www, the static site
```

- **Names.** `app.neottx.com` is the server's origin. `www.neottx.com` is the static site. `neottx.com` and the `neoteletext.com` names redirect. `caddyrouter` terminates TLS, and `deploy/ionos/caddyrouter.caddy` is its block. The container's Caddy, `deploy/ionos/Caddyfile`, serves port 8080 with `auto_https off`.
- **The script's order.** It takes dated backups on the container, builds a static musl server on the Linux build host, and installs the binary. It copies each channel with rsync **from the working trees beside the repository**, so what is deployed is what is on the disk and not a commit. Then it runs `npm ci`, copies the dataset, sets up the Python channel, writes `channels.json` (with each deployed channel's `default_rules`), the service and the socket units and the Caddyfile, validates and restarts, and replaces caddyrouter's block in a checked candidate.
- **The service.** It runs as `ubuntu`, with `StateDirectory=neoteletext`, `--listen 127.0.0.1:8090 --origin https://app.neottx.com --admin-listen 127.0.0.1:9464`, and `TimeoutStopSec=15`. The socket unit keeps connections waiting across a restart.
- **The check.** The script ends by asking each channel's `channel.ttx` from inside the container.

`--no-build` reuses the binary already on the build host. DNS is not touched.

A server of protocol 15 needs every channel's kit at 17.0.0 (or the Python kit at protocol 15) and a browser of push protocol 10 deployed with it: there is no compatibility path in either protocol.

### 1.13 The Cloudflare host

`crates/teletext-cloudflare` compiles for `wasm32-unknown-unknown` and the gates hold it to that, and it has never run on Cloudflare (TODO-1709). The design is one Durable Object for each channel, running the same `teletext-runtime`. Viewers connect to `/<channel>/push`. A program connects to `/<channel>/program` over a WebSocket with the channel's secret, through `scripts/bridge.ts`, which runs an unchanged program over standard input and output. Its `default_rules` is fixed at `"none"` (page-rules.md section 17, item 8). Do not plan on it yet.

## Part 2: Node and TypeScript

A program may be written in any language, and section 2.16 says what one with no kit must do. Two libraries make it easy in TypeScript:

- **`neoteletext-server-ts-protocol`,** the protocol kit: the JSON protocol, a place to keep pages, drawing, input, navigation, rule tables, animation and sound.
- **`neoteletext-server-ts-ui-components`,** the UI library: components, like React class components, on top of the kit, which write each page's rule table from the components on it.

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
    "neoteletext-server-ts-protocol": "file:vendor/neoteletext-server-ts-protocol-17.0.0.tgz",
    "neoteletext-server-ts-ui-components": "file:vendor/neoteletext-server-ts-ui-components-25.0.0.tgz"
  }
}
```

Copy the tarballs from any channel's `vendor/`, then run `npm install`. `BUILD.md` in each library says how a release is made. `dist/` and the generated types are built by the kit's `scripts/check.sh`. Depend on the tarball and not on the kit's source.

### 2.2 How a program connects

The server starts the command in the channels file. `runChannel` reads lines on standard input, writes lines on standard output, and resolves when standard input closes, which is the server going away:

```ts
await runChannel([application]);
```

**Standard output carries protocol lines and nothing else.** Anything for a person goes to standard error, which the server logs. One `console.log` in a program is a refused line. Use `process.stderr.write`, or `context.log`, which sends a `log` message.

**A program that runs as a service of its own** has `"socket"` in its channels entry and is started with the socket's path in `NEOTELETEXT_SOCKET`. With it set, `runChannel` speaks the same lines over the socket and never resolves: when the server goes it connects again, at once after a connection that heard `start`, otherwise after a pause of 1 second doubling up to 30. Each socket connection starts afresh, since the server sends `start` on it, and lines written while no connection is open are dropped.

### 2.3 Lifecycle

An `Application` is an object with the pages it serves and the calls it answers. A channel may have several, and the first to name a page serves it. Every call that concerns a viewer names a **connection**, one browser tab.

| The server says | The kit calls, in order | Then the kit answers |
|---|---|---|
| `start` | `gone` for every connection it knew, then `start(context)` on every application | Nothing yet: it keeps what you publish |
| `connected` | `joined(connection)`; `request` for the page; `opened` | One `reply`, then `subpages` if the page has several sub-pages |
| `selected`, a new page | `request`, then `opened` | One `page`, then `subpages` |
| `selected`, the same page | `request` | One `page` |
| `left` | `request` with null; `leftPage` | Nothing |
| `input` | Navigation first, then `input` if navigation did not take it | Nothing unless you act |
| `rule_event`, `rules_fault` | `ruleEvent`, `rulesFault` on the application that serves the page | Nothing |
| `gone` | `gone(connection)`: forget it, and the connection's own pages are forgotten | Nothing |
| `viewer_began`, `viewer_left`, `state_refused`, `viewers_reset` | `viewerBegan`, `viewerLeft`, `stateRefused`, `viewersReset` | Nothing |
| `stats` | `stats` on every application | Nothing |
| `refused` | `refused`, or written to standard error | Nothing |

`wake` is the kit's own: ask with `context.wakeIn(ms)` or `wakeAt(ms)`. It fires once, the earliest asked for wins, and you ask again for the next.

Three things catch people out:

- **Send the page's table at every selection.** The server keeps none, so `opened` (or `request`) is where a page's `rules` goes, with the page. A table sent once in `start` reaches only the connections open then.
- **A restarted program knows nothing,** and neither does the viewer's page: the server sends it the empty or the default table when the old program goes. The new program gets `start` and a `connected` for each viewer. What a viewer must not lose belongs in a store of yours, keyed by the viewer's handle where there is one.
- **A connection is not a viewer.** Two tabs of one viewer are two connections. `context.viewer(connection)` is the viewer's handle, or null until the viewer gives state.

`request` is how a selection reaches you as a web request would:

```ts
{ method: "GET", path: "302/0002", query: { a: "1" }, queryText: "a=1" }
```

It comes for every selection and before the page opens, so you may publish in it. It comes with null when the viewer leaves the page. A query belongs to one selection. Everything in it but `method` is untrusted, from the viewer. There are no cookies.

### 2.4 Every message

The kit writes these for you. This table is for reading the log and for writing without a kit. [DOC-1968](../PROTOCOL.html#DOC-1968) and [DOC-1970](../PROTOCOL.html#DOC-1970) give every field, and the schema is the exact contract.

From the server:

| `type` | Means | Kit |
|---|---|---|
| `start` | The program started. `protocol`, `epoch_ms`, `standard`, `budgets`, `languages` | `start` |
| `connected` | A connection's first selection came, or 1.5 s passed. `connection`, `request`, `selection`, `path`, `query`, `viewer`, `remembered`. Answer exactly once with `reply` | `joined`, `request`, `opened` |
| `selected` | A new selection. `connection`, `request`, `path`, `page`, `sub`, `query` | `request`, `opened` |
| `input` | A reported input. `connection`, `page`, `sub`, `lost`, `rule`, `row`, `tick`, `target`, `event` | `input` |
| `rule_event` | A report with no input event: a firing, or a value | `ruleEvent` |
| `page_state` | The answer to `query_state` | `queryState` resolves |
| `rules_fault` | A receiver's fault of the page's table | `rulesFault` |
| `left` | A selection left a page, or the connection closed | `request` null, `leftPage` |
| `gone` | The connection closed and will not come back | `gone` |
| `viewer_began`, `viewer_left`, `state_refused`, `viewers_reset` | Viewer state | `viewerBegan` and the others |
| `stats` | The figures, every 10 seconds | `stats` |
| `describe` | A web visitor is at a page's address. Answer with `description` | `describe` |
| `measured` | The answer to `measure` | `measure` resolves |
| `sound_built` | A stored synthesizer sound was built | `soundBuilt` |
| `refused` | A line of yours was refused whole. `message`, `path`, `rule`, `detail`, `request`, `sound` | `refused` |

From the program:

| `type` | What it does | Kit |
|---|---|---|
| `reply` | Answers `connected`: `magazines`, the index, and `selected`, one sub-page or null | Automatic |
| `page` | One sub-page to named connections. `request` is the selection it answers, or null for a change | `publish`, `publishSubpages`, `publishTti`, `put` |
| `denied` | Ends a selection with 403, 404, 429 or 503. The connection stays | Automatic for 404, and `deny` |
| `subpages` | A page's sub-page list, with a `version` | Automatic |
| `index` | The index changed | Automatic; `title` |
| `redirect` | Sends a viewer to a page or an address | `redirect` |
| `rules` | A page's rule table, or `null` to remove it | `rules` |
| `local_midi`, `variable`, `timer`, `report`, `run`, `sequence` | A rule table's commands, sent directly | `localMidi`, `variable`, `timer`, `report`, `run`, `sequence` |
| `query_state` | Asks one connection for a page's local state | `queryState` |
| `frame`, `animate`, `sprites`, `naplps_objects`, `sprite_sheet`, `object_page`, `timeline`, `timeline_stop` | Animation | `frame`, `animate`, `sprites`, `naplpsObjects`, `spriteSheet`, `objectPage`, `playTimeline`, `stopTimeline` |
| `sound` | A sound, its data or a command | `sound` |
| `regis`, `regis_links`, `regis_cursor`, `naplps` | A ReGIS or NAPLPS picture | `regis`, `regisLinks`, `regisCursor`, `naplps` |
| `request_state`, `end_state`, `offer_remember` | Viewer state | `requestState`, `endState`, `offerRemember` |
| `author_log` | A line for the viewer's developer console | `authorLog` |
| `log` | A line for the server's log | `log` |
| `packets` | Raw 42-byte packets, base64 | `packets` |
| `description` | Answers `describe` | Automatic, from `describe` |
| `measure` | Asks what a sub-page's encoding costs | `measure` |

`context.deny(connection, status)` ends a viewer's selection with no page. Called from `request` or `opened` it is the selection's answer, in place of the page, and for a connection's first selection the kit sends the `reply` first.

### 2.5 Validation

Before it writes a line, the kit checks the message against the server's schema, with validators compiled from it at build, and a page, an index and a log line then against the rules the schema cannot state: no control or bidirectional character, Unicode normalisation form C, and limits in bytes. A message the server would refuse for those is never written: the call throws a `ProtocolError` naming the path and the rule.

A sound, a rule table and every animation message are held to the schema alone. Everything else about them, a name not declared, a condition too deep, groups that run each other, a limit of the table, is the server's to refuse, and its refusal reaches your `refused` handler with the rule (`invalid_rules`, `invalid_group`, `unknown_name`, `rules_over_limit` and the others) and the path of the first fault. Have `refused` do something a person will see.

An application's failure is caught and reported, and the channel goes on. Page numbers are hexadecimal in JSON and numbers in the kit: write `0x100`.

### 2.6 What `Context` does

An application answers through the `Context` it is given. A context belongs to one call: do not keep it. Every call that addresses viewers takes an audience: `{ connection }`, `{ page }`, or `{ connections: [...] }` and `{ connections: "all" }`; of these, a page call reaches only the connections that have that page and sub-code selected.

| Call | What it does |
|---|---|
| `publish(owner, page, screen)` | The page as one sub-page, 0000 |
| `publishSubpages(owner, page, subpages)` | The whole page, numbered by place |
| `publishTti(owner, page, text)` | The whole page from TTI |
| `put(owner, page, subpages)`, `remove(owner, page, subcodes)` | One sub-page in or out, by sub-code, keeping the others |
| `release(connection, page)` | Drops a connection's own copy: it sees the channel's again |
| `title(page, title)`, `titleOf(page)` | The title in the index |
| `redirect(connection, page, sub?)`, `redirect(connection, address)` | Section 2.10 |
| `rules(to, page, sub, table)` | A page's rule table (section 2.8) |
| `localMidi`, `variable`, `timer`, `report`, `run`, `sequence` | A table's commands, sent directly, each `(to, page, sub, …)` |
| `queryState(connection, page, sub)` | A promise of the page's local state in that tab |
| `frame`, `animate`, `sprites`, `naplpsObjects`, `spriteSheet`, `objectPage`, `playTimeline`, `stopTimeline` | Section 2.11 |
| `sound(to, member)` | Section 2.12 |
| `regis`, `regisLinks`, `regisCursor`, `naplps` | A picture in ReGIS or NAPLPS |
| `authorLog(to, level, text, page?)` | `E`, `W` or `I`, for the viewer's developer console |
| `log(text)` | The server's log |
| `packets(to, bytes)` | Raw packets |
| `measure(page, screen)` | A promise of what the sub-page's encoding costs |
| `viewer(connection)`, `remembered(connection)` | The viewer's handle, or null, and whether they chose to be remembered |
| `requestState(connection)`, `offerRemember(connection)`, `endState(viewer)` | Viewer state |
| `connection()` | The connection this call came from |
| `wakeAt(at)`, `wakeIn(delay)` | The `wake` call |
| `now()`, `epochMs()` | Milliseconds since the program started, and the real time by the server's clock |
| `limits()`, `languages()` | What `start` said |
| `random()`, `below(bound)` | For games, never for secrets |

`owner` is `"channel"`, one copy every viewer sees, or a connection number, that tab's own copy. **The kit keeps every page,** so the server need not. When a connection has a copy of a page, it sees that copy and not the channel's, until `release`. Publish a channel's copy of every page in `start`, even if each viewer will have their own: the index takes its count of a page's sub-pages from the channel's copy.

A handle may be used only to provide what the viewer asked for on this channel (a poll's one vote, choices they made, their language), never for advertising, profiling, analytics beyond aggregate counts or sharing; delete what you keep for it at `endState` and at your store's limits, and say on your privacy page what you keep.

### 2.7 Sub-pages

The rules of a sub-page are in [a sub-page](../PROTOCOL.html#DOC-1971). A page has one sub-page or many, and every sub-code is a peer. Give a page whole and the kit numbers it by place, as the code of practice says: one sub-page is 0000, and 2 to 79 are 0001 to 0079, decimal. `put` and `remove` name sub-codes themselves and keep them as given.

```ts
context.publishSubpages("channel", FACTS, [factPage("Three sub-pages"), factPage("One at a time"), factPage("Nothing rotates")]);
```

`Subpage` is `{ screen, subcode?, title? }`, and `title` is its name in the list, at most 40 characters. Only one sub-page goes to a connection at a time, with the list after it. A selection of a sub-page the page lacks is sent to the page instead, keeping its query. A viewer's own stepping is a selection, so each step costs one round trip to the program, and it is a new selection for the rule table: a sub-page with a table of its own is sent it at each step.

The wheel over a page whose number has more than one sub-code steps its sub-pages in the browser, unless the pointer is inside the target of a `wheel` rule of the sub-page's table.

### 2.8 Input and the rule table

What a program hears is defined in [what a program hears of input](../PROTOCOL.html#DOC-1969), and how a page asks for it in [a page asks for input with its rule table](../PROTOCOL.html#DOC-6583).

**A page with no table sends nothing.** A program hears `input` only for an event a rule of the page's table reported. So the first thing a page that takes input does is send its table:

```ts
import type { RuleTable } from "neoteletext-server-ts-protocol/protocol";

const TABLE: RuleTable = {
  rules: [
    // Typed keys and committed text reach the program; a click, a move and the wheel do not.
    { name: "typed", on: [{ event: "key", keys: "any", repeat: true }, { event: "text" }], do: [{ type: "report" }] },
  ],
};

opened(connection, page, context) {
  context.rules({ connection }, page, SUB, TABLE);
}
```

A rule binds one to four triggers (`key`, `key_up`, `press`, `release`, `enter`, `leave`, `move`, `wheel`, `text`, `focus`, `blur`, `open`, `close`, `becomes`, `every`, `after`, `cue`) to one group of commands, named with `run` or written in place with `do`; `when` adds a condition, and `echo: true` reports the firing after the group. The commands are the program's own messages without their audience: a `sound` play, stop or gain; `animate`, `sprites`, `naplps_objects`; and `local_midi`, `variable`, `timer`, `report`, `run` and `sequence`. The browser runs a group the moment its event arrives, so a page can sound a note, light a key or move an object with no round trip, and report only what the program needs. A table also has `rects`, named rectangles a pointer trigger can target; `rows`, row sets by which one rule stands for many (each row one parameter `p`, a key's code or a number); `groups`; `sequences`, steps the browser plays on its own clock; sixteen variables `v0` to `v15` and eight timers `t0` to `t7`. Its full form, with worked examples, is neoteletext-common's `docs/page-rules.md` section 7 and the items of [the page rule table](../PROTOCOL.html#DOC-6581).

The kit's builders make the pieces and check nothing: `physicalKey`, `characterKey`, `namedKey`, `level`, `variable`, `plus`, `row`, `fired`, `phase`, `noteOn`, `noteOff`, and `modes(variable, names)`, a mode set whose `in(mode, condition?)` and `enter(mode)` give a condition and a command.

`input(connection, page, input, context, sub)` gets each reported input, with `input.rule` (the rule's name), `input.ruleRow` (the place of the firing row in its row set, or null), `input.tick` (the page tick, sixty a second from the page's opening) and `input.target` (the control, object or rectangle the pointer was inside, or null).

| `input.kind` | Fields |
|---|---|
| `key` | `action`: `press`, `repeat`, `release`; `key`, a W3C `KeyboardEvent.key` name; `text`; `base`; `lost` |
| `mouse` | `action`: `press`, `release`, `move`, `gone`; `button` or `buttons`; `column`, `row`; `lost` |
| `touch` | A contact after the first: its action, number, cell and dot |
| `wheel` | `dx`, `dy` in 1/120ths of a line, down positive; `column`, `row` |
| `hover` | `action`: `enter`, `leave`; the control's first `column` and `row` |
| `text` | `text`, from an input method or a phone |
| `paste` | `text`. It is data, never keystrokes |
| `focus`, `blur` | The page has, or lost, the keyboard |

A report with no input event, a timer's `after`, a sequence, `open`, `close`, `becomes`, or a value, comes to `ruleEvent(event, context)`, and a fault of the table in a viewer's browser (a table it could not decode, reports dropped, evaluation late) to `rulesFault(fault, context)`. `await context.queryState(connection, page, sub)` reads a page's local state in one tab, for debugging; it is not a way to restore a page.

The helpers are `pressed(input, key)`, true on a press or repeat, `released`, `clicked`, `typed`, `character` and `decimalDigit`. `Key` names the keys. A `lost` release means the viewer left or the page lost the input, and the key never came up; the server gives one only for a press some rule reported.

**Navigation comes first.** On a live channel the kit does what a television remote does with the input a page reports: three digits select a page, and F1 to F4 or the coloured keys follow the page's Fastext links, unless the page claims them (`ownsDigits`, `ownsColourKeys`). It can do so only with what the table reports: a page that should be navigable by its digits and coloured keys must have rules that report them. A click comes to `input` first; answer `true` if the page took it.

**A channel of the old form** keeps hearing its input with `"default_rules": "send_all"` (section 1.7), each input naming a rule of the default table. It is a bridge: give each page its own table and set the channel to `"none"`.

### 2.9 Links

There are two kinds, and they travel differently.

- **Fastext links** are in the page's packets (X/27/0): `screen.fastext([red, green, yellow, cyan])`, and `screen.indexLink(page)`. They name pages of this channel. Put the prompts on row 24.
- **Link Extension links** are what packets cannot carry, and go in a LINKS record after every frame of the sub-page: `screen.keyLink(key, target, label?)`, `screen.numberLink(number, target)`, `screen.textLink(row, column, length, target)`.

A link the page declares is the browser's on every page: the browser follows it itself, and a press on it is never given to the page's table. A target is `mpp`, `mpp:ssss`, `name:mpp`, `name:mpp:ssss`, an `http` or `https` address, or `web:` and one. [DOC-1947](../PROTOCOL.html#DOC-1947) and [DOC-1879](../PROTOCOL.html#DOC-1879) say what a receiver does with one.

### 2.10 Redirects

`redirect` moves a viewer with no action from them. It is not an HTTP redirect, and a viewer's own choice overrides it.

- **To a page,** `context.redirect(connection, 0x100)`, with an optional sub-code. It is a selection: the server records it, and the program is sent `selected`.
- **To an address,** `context.redirect(connection, "https://app.neottx.com/home/")`. No selection changes. The receiver shows its notice and goes, and the program gets `left` when the viewer does.

At the first selection, a page the program lacks is redirected to the initial page, which is 100 or the lowest it has. Later, a page it lacks is DENIED 404.

### 2.11 Pictures and animation

A page is 40 by 25 cells, so a picture is one of these:

- **Mosaics you draw.** `Sixels` is a canvas, two across and three down to a cell.
- **TTI from a tool.** `context.publishTti(owner, page, text)` takes a converted picture whole, with its X/26 enhancement packets. `readTtiPages` reads TTI into typed sub-pages.
- **ReGIS or NAPLPS,** a sub-page drawn by another renderer: `regis` and `naplps`.
- **Raw packets,** with `context.packets`, each checked by the server.

**Animation** ([animation](../PROTOCOL.html#DOC-6582)) moves a page's numbered objects: a teletext sprite, a ReGIS numbered drawing, a NAPLPS object. A rule's group animates at once in the browser; the program does it with these calls, each `(to, page, sub, …)`:

- `frame(to, page, sub, body)` sends what `body` sends as one frame, applied on one tick, so no half-drawn picture is shown.
- `animate` sends operations (`show`, `hide`, `look`, `move`, `order`, `frame`, `cycle`, `stop_cycle`, `reset`); `sprites` a teletext sub-page's sprites; `naplpsObjects` a NAPLPS sub-page's objects; `spriteSheet` the drawings a sub-page's objects use; `objectPage` a teletext object page its sprites show.
- `playTimeline(to, page, sub, timeline, id?)` has the server play a `Timeline` on its own clock, sixty ticks a second, and answers its `id` for `stopTimeline`. A timeline ends for a connection that leaves the page.

```ts
const walk = new Timeline({ loopTicks: 120 });
walk.at(0).show(10).cycle(10, 0, 3, 6);
walk.then(30).move(10, 8, 0, true);
walk.then(30).hide(10);
const id = context.playTimeline({ page: 0x150 }, 0x150, 1, walk);
```

The server keeps none of it for a later viewer: send a page's sheet, sprites and opening state at every selection. For motion that must be exact to the tick and answer the viewer at once, write rules with `after` and `every` triggers; a timeline is for motion the channel directs.

### 2.12 Sound

The sound messages are defined in [sounds](../PROTOCOL.html#DOC-1972). Sound is the engine's audio profile: Opus for desktop and phone receivers, synthesizer sounds of several families, and PCM, which the server encodes as IMA ADPCM, for microcontroller receivers. The pattern is to send the sound once and then play it by handle:

```ts
const chime = opus.sound(chimeSamples(), CHIME_RATE);                  // ffmpegOpus().sound, at start
context.sound({ connection }, { opus: { handle: 1, generation: 0, ...chime } });
context.sound({ connection }, { play: { channel: 0, handle: 1, generation: 0 } });
```

`to` is `{ connection }`, `{ page }` or `{ connections }`. `ffmpegOpus` needs ffmpeg with libopus on the path. Tests use `fakeOpus` from the testing entry, which the server would refuse.

A **local sound** ([local sounds](../PROTOCOL.html#DOC-6601)) is an instrument a page keeps open in the browser, of a synthesizer family that plays notes (the kinds ending `_local`): played with a page scope, and then given notes by the `local_midi` commands of the page's table, so a key sounds a note with no round trip. It ends when its page closes.

### 2.13 A complete small program

This channel has an index and a counter each tab has a copy of. The counter's page asks with its table for the Enter key alone, so nothing else the viewer does on it reaches the program. It was written for this guide and its test was run against the kit at `d3b237e`. `src/guide.ts`:

```ts
// A small channel of program protocol 15: an index, and a counter each
// connection has a copy of, whose page asks with its rule table for the
// Enter key alone.
import { type Application, Colour, Key, pressed, Screen } from "neoteletext-server-ts-protocol";
import type { RuleTable } from "neoteletext-server-ts-protocol/protocol";

export const INDEX = 0x100;
export const COUNTER = 0x101;
const SUB = 0;

/** The counter's table: Enter, pressed or repeated, is reported; nothing else is sent. */
export const COUNTER_TABLE: RuleTable = {
  rules: [{ name: "enter", on: { event: "key", keys: [{ name: "Enter" }], repeat: true }, do: [{ type: "report" }] }],
};

function counterPage(count: number): Screen {
  const screen = new Screen();
  screen.header("GUIDE");
  screen.doubleHeight(2, 0, Colour.Yellow, "Counter");
  screen.text(5, 1, `Count ${count}`);
  screen.fastext([INDEX, null, null, null]);
  return screen;
}

const counts = new Map<number, number>();

export const guide: Application = {
  pages: () => [
    { page: INDEX, title: "Index" },
    { page: COUNTER, title: "Counter" },
  ],
  start(context) {
    const index = new Screen();
    index.header("GUIDE");
    index.doubleHeight(2, 0, Colour.Yellow, "Index");
    index.fastext([COUNTER, null, null, null]);
    context.publish("channel", INDEX, index);
    context.publish("channel", COUNTER, counterPage(0));
  },
  opened(connection, page, context) {
    if (page === COUNTER) {
      context.publish(connection, COUNTER, counterPage(counts.get(connection) ?? 0));
      // The server keeps no table: send it at every selection of the page.
      context.rules({ connection }, COUNTER, SUB, COUNTER_TABLE);
    }
  },
  input(connection, page, input, context) {
    if (page === COUNTER && input.rule === "enter" && pressed(input, Key.Enter)) {
      const count = (counts.get(connection) ?? 0) + 1;
      counts.set(connection, count);
      context.publish(connection, COUNTER, counterPage(count));
      return true;
    }
    return false;
  },
  gone(connection) {
    counts.delete(connection);
  },
};
```

`src/main.ts` is `await runChannel([guide]);`. This program sends the index no table, so on a channel with `"default_rules": "none"` the index sends nothing: a click on its Fastext prompt is a link the browser follows itself, but its coloured keys and digits on the keyboard reach the kit's navigation only when a table reports them. A real index would send a table with a rule reporting the digits and the four colour keys, as the UI library writes for every page of text.

`test/guide.test.ts`:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { Key } from "neoteletext-server-ts-protocol";
import { Harness, shows } from "neoteletext-server-ts-protocol/testing";
import { COUNTER, COUNTER_TABLE, guide } from "../src/guide.ts";

test("the counter sends its table at every selection and counts Enter", () => {
  const harness = new Harness([guide]);
  const connection = harness.join(harness.viewer("alice"), COUNTER);
  const tables = harness.sent.filter((sent) => sent["type"] === "rules");
  assert.deepEqual(tables.map((sent) => sent["table"]), [COUNTER_TABLE]);
  harness.fire(connection, "enter", { kind: "key", action: "press", key: "Enter", mods: 0, text: null, base: null } as never);
  assert.ok(shows(harness.own(connection, COUNTER), "Count 1"));
  harness.press(connection, Key.Enter);
  assert.ok(shows(harness.own(connection, COUNTER), "Count 1"), "an input the default table names is not the counter's rule");
  assert.deepEqual(harness.errors, []);
});
```

Run on 19 November 2026, Node 24.21.0:

```
$ node --test test/guide.test.ts
✔ the counter sends its table at every selection and counts Enter (21.786243ms)
ℹ tests 1
ℹ pass 1
ℹ fail 0
```

`harness.fire` gives the channel what a rule's firing reports; `harness.press` gives an input named by the default table's rule `keys`, as a channel on `"send_all"` hears it, which this page's program ignores because it is not its rule.

### 2.14 The UI library

`neoteletext-server-ts-ui-components` makes a page a tree of components, as React's class components do: props, state, `setState`, a lifecycle, and `h` in place of JSX. It lays the tree out, draws it, publishes it, routes the input a page reports to the component it lands on, and keeps a viewer's own copy of a page only while it differs from everyone's.

**Each page asks for its own input.** The library writes each sub-page's rule table from the components on it, from its own cells: keys where one takes them, a press on a button's cells, the wheel over a list that scrolls, and on a page of text only the digits and the coloured keys the kit selects pages by. A channel on the library writes no table of its own, and its entry in `channels.json` can say `"default_rules": "none"`. `new ComponentChannel(pages, { ruleTables: "none" })` switches this off, leaving every page to the channel's `default_rules`.

`ComponentChannel` is one `Application`, so `runChannel` runs it. Each page is a `PageSpec`:

| Field | Meaning |
|---|---|
| `page`, `title`, `section` | As an entry |
| `root(params)` | The page's root element |
| `perViewer` | Each viewer gets a mount of their own, with state of their own. When absent, the library works out whether a component needs one |
| `keepWhileAway` | A viewer's mount is kept while they are on other pages, until they go |
| `ownsDigits`, `ownsColourKeys` | When absent, the library asks the components |

Inside a component, `this.services` reaches the channel: `connection`, which is null on the shared copy; `redirect(connection, page, params?)`, which opens a page with `params` that its `root` reads; `redirect(connection, address)`; `deny`; `parameters(connection)`, the selection's query; `title`; `play` and `stream`; `now`, `epochMs`, `limits`, `languages`; `forgetViewer(connection)`; and `bus`, for what one page's components tell another's, such as `stats` and `gone`. An address's query reaches `root(params)`; its values are the viewer's untrusted text, so read and bound them.

What must outlast the program goes in a `SqliteStateStore`. A poll's ballot (`Tally`), a component's kept state (`keptAs`) and a viewer's language (`LanguagePicker`) are kept under the viewer's handle, never a connection's number; a connection with no viewer keeps them for its own life, and the library asks for the viewer's state after their input.

The library's own documents are the reference: `docs/how-it-works.md` (its section on the rule table says what each component asks for), `docs/keys-and-focus.md`, `docs/look.md`, `docs/audio.md`, `docs/testing.md`, and `docs/components/` for each part.

### 2.15 What differs in the Python kit

The Python kit is `~/devel/neoteletext-server-channels/kits/python`, the package `neoteletext_app`. It is the TypeScript kit's equal, call for call, as `kit-calls.tsv` lists them, so the guide above holds for it with these differences. It keeps the old Hackaday channel running.

| | TypeScript | Python |
|---|---|---|
| An application | An object of calls; several may share a channel | A subclass of `App`; one to a program |
| Handlers | `start`, `joined`, `request`, `opened`, `leftPage`, `input`, `ruleEvent`, `rulesFault`, `wake`, `gone`, `viewerBegan`, … synchronous | `on_start`, `on_joined`, `on_request`, `on_opened`, `on_left_page`, `on_input`, `on_rule_event`, `on_rules_fault`, `on_wake`, `on_gone`, `on_viewer_began`, … all `async` |
| Answering | Through a `Context` given to each call | Methods of `self`: `self.publish`, `self.rules`, `self.animate` and the others |
| Audiences | `{ connection }`, `{ page }`, `{ connections }` | `connection_hears`, `page_hears`, `connections_hear`, `everyone_hears` |
| Declaring pages | `pages()`, entries with `ownsDigits` and so on | `{page: title}` and `{page: section}` to the constructor. A page takes a key by answering `True` from `on_input` |
| An input's row | `input.ruleRow` | `event.rule_row` (`event.row` is a pointer's cell row) |
| A frame | `frame(to, page, sub, body)` | `with self.frame(to, page, sub):` |
| The mode set | `modes(v, names).in(mode)` | `modes(v, names).in_(mode)`, since `in` is a keyword |
| A state query | a promise; `QueryRefusedError` | `await self.query_state(...)`; raises `QueryRefused` |
| Checking | Every message against the schema, compiled in | Text rules in `textrules.py`; the schema check in its tests |

### 2.16 A program with no kit

A program needs only a JSON library. It reads `start`; answers each `connected` with one `reply` and each `selected` with one `page` (or `denied`), copying the `request`; sends each page that takes input its `rules` at every selection; and reads `input` and `rule_event`. Every message is in [DOC-1968](../PROTOCOL.html#DOC-1968) and [DOC-1970](../PROTOCOL.html#DOC-1970), and [build a program](../PROTOCOL.html#DOC-1978) is the task. A sub-page on the wire has every field present: `page`, `sub`, 25 `rows` as base64 of 40 seven-bit codes or null, six `links`, `display_row_24`, `link_extension`, `control`, `character_set`, `enhancements`, `packets` and `cursor`. A `rules` message is exactly the JSON of the worked examples in neoteletext-common's `docs/rules-examples.jsonl`, each a line the server accepts.

## Part 3: how to program them

### 3.1 Patterns the real channels use

Every TypeScript channel has the same shape: `src/main.ts` parses its arguments, loads its data, writes one line to standard error and calls `runChannel([new ComponentChannel(specs)])`. `src/pages.ts` makes the list of `PageSpec`s, so a test can make the same list. `vendor/` holds the tarballs. The small demosite and home channels are the ones to read first.

**One list of pages, one place for numbers.** demosite has `src/site/page-numbers.ts`, and each area in `src/pages/*/area.ts` names its pages. No page number is written twice.

**Content as data.** Home's `src/channels.ts` is a plain list: adding a channel adds it to the front page and the directory. A page is a function of its data.

**A shared live page.** demosite's markets page is one component on the copy every viewer shares, with `setInterval` in `componentDidMount` and `setState`. The library publishes when the page changes, and the server sends the changed rows.

**A copy for each viewer.** demosite's calendar and adventure pages set `perViewer: true`, and state lives in the component.

**One page, many things.** Hackaday's reader, page 110, shows one article of thousands: `perViewer`, `keepWhileAway`, and `root: (params) => ...` reading `params?.["article"]`. A list sends the viewer there with `services.redirect(connection, PAGES.reader, { article: id })`.

**Many sub-pages on one page.** demosite's page 602 is hundreds of `RawSubPage`s. Only the sub-page selected ever travels, with its own table.

**A page that answers itself.** The music player channel (neoteletext-common's REQ-6541) plays a synthesizer on a key press and lights level meters with no round trip: its page's table holds rows for the thirteen keys, a local sound and groups of `local_midi` and `animate` commands, and reports nothing. Read its table in `docs/page-rules.md`, RULE-93.

**Loading at start.** Hackaday loads its library before calling `runChannel`. Remember that the 5-second deadline is running while a program starts.

**The UI demo.** `neoteletext-server-channel-uicomponentsdemo` is the library's own channel, with every component working, a page each.

### 3.2 How to test a program

**The harness is the first tool.** `neoteletext-server-ts-protocol/testing` drives a channel as the server does, with no server, and every line is checked against the schema. Section 2.13 has a test.

| Harness | Does |
|---|---|
| `viewer(name)`, `privateViewer(name)`, `join(who, page)`, `open(connection, page, sub?, query?)`, `close(connection)` | A viewer comes, selects, goes |
| `press`, `key`, `typeKeys`, `typeText`, `paste`, `click`, `clickLeft`, `move`, `wheel`, `hover`, `send` | Input, each named by the default table's rule that reports it |
| `fire(connection, rule, event?, tick?, target?, row?)` | What a rule's firing reports: an input naming the rule, or a `rule_event` |
| `answerState(query, state?)` | Answers a `query_state` the channel wrote |
| `timelineSends(connection)` | The `animate` messages the server would send as each timeline plays |
| `grantState`, `refuseState`, `remember`, `forget` | Viewer state |
| `advance(ms)`, `runUntil(ms)`, `restart()` | The clock, waking the channel, and a restart |
| `seen`, `shared`, `own`, `sharedPages`, `ownPages` | What the channel keeps |
| `shows(rows, words)`, `text(rows, row)`, `rowOf(rows, words)` | Read rows |
| `sent`, `redirects`, `addressRedirects`, `at`, `sounds`, `errors` | What was sent, and what failed |

Assert that `harness.errors` is empty: a failing application is reported there and does not fail the test by itself. The harness does not evaluate a table: that is the browser's. To see a table evaluated without a browser, `neottx rules-run TABLE INPUTS` runs one against timed inputs and prints what its groups do and what it reports ([neottx](../PROTOCOL.html#DOC-2294)).

The real channels check more: `test/pages.test.ts` in each publishes every page and asserts nothing is reported. Each repository's `scripts/check.sh` runs its gates.

**Then the browser.** Open `http://127.0.0.1:8090/guide/` with the NeoTeletext browser of push protocol 10. Only the browser runs a page's table and shows how it looks.

### 3.3 Common faults

The document's own list is under [troubleshooting](../PROTOCOL.html#DOC-1789).

| What you see | Why | What to do |
|---|---|---|
| A program hears no input, or only some | The page has no rule table, or no rule of it reports that event ([DOC-1984](../PROTOCOL.html#DOC-1984)) | Send the page a table at every selection, with a rule that reports what you need; or, for an old channel, `"default_rules": "send_all"` |
| A table works once and then not after the viewer steps a sub-page or comes back | The server keeps no table, and each sub-page is a page | Send the table at every selection, for that sub-code |
| `refused`, rule `invalid_rules`, `invalid_group`, `unknown_name` or `rules_over_limit` | The server's check of the table, which the kit does not run | Read `path` and `detail`; the limit's constant is named |
| `rules_fault`, `undecodable` | A receiver could not decode the table | Should not happen with a table the server accepted: report it |
| 426 from `push` | The subprotocol is missing or another version | Offer `neottx.10` |
| 403 from `push` | The upgrade carried `Origin`, as any web page's script does | A receiver cannot be a web page |
| Closed 4001 | HELLO named another version | Update the receiver |
| Closed 4000 | The receiver broke the protocol, or sent the viewer's input at the top level of the stream | Send input only inside RULE_EVENT |
| DENIED, `program_late` in the log | The program did not answer within 5 seconds, or none is running | Check that it is running, that it flushes its lines, and that it does not block |
| `refused`, rule `syntax`, path empty | Something other than a protocol line reached standard output, such as a stray print | Write to standard error |
| `ProtocolError` on standard error | The kit refused a message before writing it | Read the path and rule |
| `magazine: out_of_range`, or a page never found | A page number in decimal: `100` is not `0x100` | Write page numbers in hexadecimal |
| `out_of_range` at `sub` | A table or animation message for sub-code `3F7F` | Name the sub-page |
| Digits or coloured keys never reach `input` | The table does not report them, or navigation took them | Report them in the table; set `ownsDigits` or `ownsColourKeys` |
| A click on a link never reaches the program | Links are the browser's | Use a control, not a link, for what the program answers |
| Another viewer sees a viewer's page | Published to `"channel"` | Publish to the connection |
| State lingers after a tab closes | `gone` was not handled | Drop what you keep for the connection in `gone`; keep what a viewer must keep under their handle |
| The kit prints `the server speaks protocol N` | The kit is older or newer than the server | Take the matching tarball. There is no compatibility path |

## What this guide could not settle

- **A real receiver.** No browser and no `neottx view` was run for this edition. Whether a table's group sounds and draws as it should was not seen.
- **Cloudflare.** Nothing here was run on it.
- **The reply limit.** 5,000 ms is marked provisional in the code, until TODO-1521 measures it.
- **Real systemd.** Socket activation and `deploy/ionos/deploy.sh` were read, not run.
- **The branches.** Everything here is on unmerged branches; names and figures may move when they are merged.
