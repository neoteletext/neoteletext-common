# `neoteletext-web`

| | |
|---|---|
| **Rests on** | A reading of every file of `crates/neoteletext-web` at engine `fb2dd8a`, with the firmware test image linked from a copy of that tree to read its symbols. The line numbers below are those of `fb2dd8a`. |
| **Baseline** | The commit after `fb2dd8a` on `implementation`, "Keep core::fmt out of the no_std web builds: no Debug on the agent", which removes the `core::fmt::Debug` supertrait from `cookie::Cookies` (`cookie.rs:160`) and `dbsc::DeviceKeys` (`dbsc.rs:85`) and the `#[derive(Debug)]` from `agent::UserAgent` (`agent.rs:759`). It is the fix for the full gate's `web: panic path: core::panicking::assert_failed`: the supertrait put `Debug::fmt` into the `dyn Cookies` table that the agent's own jar is coerced to (`agent.rs:847-855`, reached unconditionally from `Input::WipeCookies` at 1157), and the derived `Debug` of `CookieJar` (six fields) and `Record` (fifteen) is `Formatter::debug_struct_fields_finish`, whose `assert_eq!` on two lengths is the symbol. With the fix applied, the `web` and `web-all` images link with no `panicking`, `_fail` or `failed` symbol. Every step below starts from that commit; it shifts `agent.rs` by three lines after 759, `cookie.rs` by one after 159 and `dbsc.rs` by two after 85 from the numbers given here. |
| **Phase** | E3 (`01-method-and-order.md`): depends on the core only; independent of `input`, `qrkeyboard`, `audio`. |

## 1. The crate as it is

### Purpose

Layer L7 of the engine's `ARCHITECTURE.md`: the sans-IO, `no_std`, allocation-free web user agent (decision E.34) and the zxnet live-feed reader (REQ-INP-022), with the web half of the L8 platform interface in `port`. It is fed bytes, time and requests; it produces bytes to send, timers, TTI or T42 page bytes and events. Its only dependencies are `neoteletext-core` and `embedded-io` (decision E.38; `cargo xtask check-deps`).

### Features

| Feature | Default | What it gates | Where the `cfg` sits |
|---|---|---|---|
| `push` | on | the push connection over WebSocket or server-sent events (REQ-WEB-005) | `cfg!(feature = "push")` tests inside `agent.rs` at 1101, 1105, 1115, 2105, 2243, 2679, 2733; `#[cfg(feature = "push")]` on thirteen tests and helpers of `tests/agent_replay.rs` and one `#[cfg(not(feature = "push"))]` test |
| `forms` | on | form submission (REQ-WEB-010, REQ-WEB-011) | `cfg!` tests in `agent.rs` at 1145, 1153, 1346, 1815; tests gated likewise |
| `cookies` | on | the agent's use of the cookie store (REQ-WEB-006); `cookie.rs` itself is always compiled | `cfg!` tests in `agent.rs` at 877, 908, 1066, 1084, 1292; tests gated likewise |
| `dbsc` | off, implies `cookies` | Device Bound Session Credentials (REQ-WEB-017): `pub mod dbsc`, `agent/bound.rs`, two fields of `UserAgent`, `tests/dbsc.rs` (`required-features`) | `#[cfg(feature = "dbsc")]` on items in `lib.rs:58` and `agent.rs` at 626, 630, 802, 805, 809, 813, 815, 819, 1029, 1031, 1480 |
| `error-trait` | off | `Display` and `core::error::Error` for nine error types (REQ-GEN-011, REQ-GEN-016) | `lib.rs:68-117` |
| `std` | off | `proxy::{Proxy, TunnelError, tunnel}`, the blocking proxy handshake over `std::io` (REQ-WEB-032) | eleven `#[cfg(feature = "std")]` on consecutive items of `proxy.rs` (269-340) and five in its tests |

The two styles are deliberate (decision E.61): `dbsc` and `std` gate whole items; `push`, `forms` and `cookies` are tested with `cfg!` inside functions that exist in every build, so the agent's types are the same in every build and the linker drops the part. Feature `cfg` appears in exactly three files: `agent.rs` (27 sites), `proxy.rs` (11), `lib.rs` (3). The zxnet feed is not a feature: nothing in the agent reaches it, so the linker leaves it out of a port that does not call it.

`cargo xtask features` builds the crate with no feature and with each of `push`, `forms`, `cookies`, `dbsc` alone; the full gate also builds it for `x86_64-unknown-none` and links `firmware/test-image` with `web` (no features) and `web-all` (`default`), reading the symbols (REQ-GEN-019). The `error-trait` and `std` builds are in neither list.

### Module tree with line counts

```
src/lib.rs                 117   crate docs, lint lists, 22 mod lines, error-trait impls
src/consts.rs              494   every web-standard constant, by clause
src/bytes.rs               318   Writer, TextBuf, copy_prefix, ASCII number helpers
src/base64.rs              209   RFC 4648 encode, decode, decode_in_place
src/sha1.rs                169   RFC 3174 (the WebSocket accept value)
src/sha256.rs              235   FIPS 180-4 (used by xtask's font checks; no caller in the crate)
src/json.rs                576   bounded pull reader (RFC 8259)
src/port.rs                265   L8: ConnectionId, Transport, RandomSource, CookieStorage, NetInput, NetOutput, Pump
src/url.rs                 867   strict address parser, IP literals, relative resolution, Origin
src/user_agent.rs          264   the User-Agent string (REQ-WEB-031)
src/http.rs                899   request writing, ResponseHead, HeadCollector, BodyDecoder
src/http/head.rs           472   status line and field lines (RFC 9112 sections 2 to 5), proptest
src/ws.rs                  630   handshake, masking, FrameReader
src/sse.rs                 409   event-stream parser
src/cookie.rs             1410   Cookies trait, CookieJar, Set-Cookie algorithm, dates, export and import
src/dbsc.rs               1184   DeviceKeys trait, RFC 9651 reader, headers, instructions, proofs, Sessions
src/channel.rs             348   channel folder and file rules, is_tti, is_t42
src/contents.rs            339   contents.txt reader
src/descriptor.rs         1056   service descriptor and channel.json reader, template, aliases, services
src/form.rs                184   destination check, urlencoding
src/proxy.rs               604   hidden_local, CONNECT, SOCKS5, parse_proxy, [std] tunnel
src/agent.rs              2764   UserAgent: fetch, cache, redirects, forms, push, cookies glue, time
src/agent/bound.rs         454   the agent's side of DBSC
src/zxnet.rs              1031   zxnet Channel, message grammar, ZxnetFeed, page walk
tests/common/mod.rs        296   Replay transport, Counter, frame and response builders
tests/agent_replay.rs     1599   the agent through Replay (53 tests, gated per feature)
tests/zxnet_replay.rs      417   the feed through Replay (11 tests) and a corpus replay
tests/dbsc.rs              329   bound sessions through Replay (6 tests; required-features = ["dbsc"])
```

Measured (`01-method-and-order.md` section 5): 24 source files, 15,298 lines, of which 2,660 are inline test modules; largest 2,764, median 483; ten files over 500 (`agent`, `cookie`, `dbsc`, `descriptor`, `zxnet`, `http`, `url`, `ws`, `proxy`, `json`); nine functions over 80 lines, four `impl` blocks over 300; 41 feature `cfg` sites in shared files; 2,641 lines of integration tests.

### Public paths and who imports them

Every importer names a path of the form `neoteletext_web::<module>::<Item>`; none names `http::head`, `agent::bound` or any private item. The target layout keeps every one of these through `pub use` in the parent file of each module, so no importer changes.

| Importer | Paths |
|---|---|
| Browser, 12 files: `native/core/src/{cookie_control,cookies,settings,updates}.rs`, `native/fetcher/src/{cookies,main,transport}.rs`, `native/keyboard/src/keyboard.rs`, `native/site/src/{terminal,websocket}.rs`, `native/tuf/updater/src/{main,transport}.rs` | `agent::{Config, Event, Input, Output, Source, Storage, Subscription, UserAgent}`; `bytes::Writer`; `consts::{ALLOWED_LOCAL, CONNECTION_CLOSE, DEFAULT_CONNECT_TIMEOUT_US, DEFAULT_HEADER_LIMIT, DEFAULT_REQUEST_LIMIT, IDENTITY, MAX_URL_LENGTH, STATUS_NOT_FOUND, STATUS_OK, header}`; `contents::{self, read, Entry}`; `cookie::{CookieJar, CookieRejected, Cookies, Site}`; `http::{BodyDecoder, HeadCollector, MediaType, Method, parse_head, write_header, write_request_line}`; `port::{ConnectionId, LinkState, NetInput, NetOutput, Pump, RandomSource, Received, Security, Transport}`; `proxy::{Proxy, ProxyKind, parse_proxy}`; `url::{IpAddress, Url}`; `user_agent::{Product, UserAgentString, os_family}`; `ws::accept_for` |
| Engine crates: `neoteletext-app/src/{fetch,live}.rs`, `neoteletext-cli/src/{contents,keyboard}.rs` and `tests/{contents,typing}.rs`, `neoteletext-qrkeyboard/src/{json,net,phone,screen}.rs` and `tests/{socket,wake}.rs`, `firmware/test-image/src/main.rs` | the above, and `base64::{encode, decode}`; `channel::{self, ChannelFile}`; `consts::{CLOSE_NORMAL, DEFAULT_FETCH_INTERVAL_US, INPUT_MESSAGE_MAX, OPCODE_BINARY, OPCODE_CLOSE, OPCODE_PONG, OPCODE_TEXT, STATUS_SWITCHING_PROTOCOLS, ZXNET_INACTIVITY_US}`; `contents::MAX_TITLE`; `cookie::parse_cookie_date`; `descriptor::{Descriptor, MAX_REFRESH_SECONDS, MIN_REFRESH_SECONDS}`; `form::{FormMethod, FormSubmission}`; `http::Framing`; `json::{self, JsonReader, JsonStr, Token}`; `port::CookieStorage`; `proxy::{read_connect_reply, read_socks_choice, read_socks_reply, socks_reply_length}`; `sse::SseParser`; `user_agent::significant_version`; `ws::{self, FrameReader, WsMessage}`; `zxnet::{Channel, ChannelError, KNOWN_CHANNELS, LiveEvent, LiveInput, LiveOutput, LiveStorage, ZxnetFeed}`; `agent::{BoundChange, Failure}`; `dbsc::{COORDINATE_BYTES, DeviceKeys, KeyHandle, PublicKey, SIGNATURE_BYTES}` |
| Fuzz targets (`fuzz/`, built with `features = ["default", "dbsc"]`) | `address.rs`: `url::Url`; `cookie.rs`: `cookie::{CookieJar, parse_cookie_date}`; `dbsc.rs`: `dbsc::{...}`; `descriptor.rs`: `descriptor::Descriptor`, `url::Url`; `http.rs`: `http::{BodyDecoder, Framing, HeadCollector, parse_head}`; `proxy.rs`: `http::HeadCollector`, `proxy::{read_connect_reply, read_socks_choice, read_socks_reply, socks_reply_length}`; `sse.rs`: `sse::SseParser`; `websocket.rs`: `ws::FrameReader` |
| `xtask` (`src/glyphs.rs`, `src/noto.rs`) | `sha256` |

### Requirements to modules

| Requirement | Code |
|---|---|
| REQ-WEB-001 transport by the port | `port.rs` (`Transport`, `Pump`); `tests/common/mod.rs` |
| REQ-WEB-002 the descriptor | `descriptor.rs` (`Descriptor::parse`); `agent.rs:1783-1810` |
| REQ-WEB-003 fetching pages, the template | `descriptor.rs:227-286`; `agent.rs:1851-1904` (`complete_page`); redirects `agent.rs:1964-2024` |
| REQ-WEB-004 caching, conditional requests | `agent.rs` `CacheEntry` 690-700, `write_request` 1460-1470, `update_cache` 2042-2081; `http.rs` `apply_cache_control` 212-229 |
| REQ-WEB-005 push | `agent.rs:2228-2667`, `ws.rs`, `sse.rs`; the heartbeat `agent.rs:2697-2728`; constants `consts.rs:305-336` |
| REQ-WEB-006 cookies | `cookie.rs`; the agent's glue `agent.rs:845-926`, 1042-1089, 1288-1298 |
| REQ-WEB-007 navigation | `agent.rs` `follow_link` 1212-1232; `cookie::Site::CrossServiceNavigation` |
| REQ-WEB-008 the security baseline and limits | `agent.rs` `Config` 52-128, `refusal` 1256-1273; `consts.rs:469-494` |
| REQ-WEB-010, REQ-WEB-011 forms | `form.rs`; `agent.rs:2113-2226`; the response 1814-1844 |
| REQ-WEB-013 replay tests | `tests/common/mod.rs`, `tests/agent_replay.rs` |
| REQ-WEB-014 the user agent profile | `http.rs`, `http/head.rs`; the header list `consts.rs:124-182`; `tests/agent_replay.rs:200-242` |
| REQ-WEB-015 the origin | `url.rs:675-699` over `neoteletext_core::policy` |
| REQ-WEB-016 the strict address parser | `url.rs` |
| REQ-WEB-017 device-bound sessions | `dbsc.rs` (the records), `agent/bound.rs` (the agent's side) |
| REQ-WEB-018 to REQ-WEB-027 channels | `channel.rs`, `contents.rs`, `descriptor.rs` (`parse_channel`, `channel_defaults`), `agent.rs` `open_channel` 1188-1196, `complete_channel` 1910-1962, `channel_file_media` 928-952, `redirect_keeps_channel` 2030-2040 |
| REQ-WEB-031 the user agent string | `user_agent.rs` |
| REQ-WEB-032 proxies | `proxy.rs`; `Config::proxied`, `agent.rs:1266-1271`, 1281-1283; `zxnet.rs:628-630`, 700-701 |
| REQ-WEB-033 each exchange reported | `agent.rs` `Event::Exchanged` 423-434, `report_exchange` 1726-1737 |
| REQ-INP-022 the zxnet feed | `zxnet.rs`; `tests/zxnet_replay.rs` |
| REQ-SEC-006 the local network | `url.rs:130-140`, `proxy.rs:66-81`, `agent.rs:1256-1283`, `zxnet.rs:697-721` |
| REQ-SEC-007 no downgrade | `agent.rs:1285-1298`, 1985-1993; `descriptor.rs:288-296` |
| REQ-SEC-011 strict HTTP | `http.rs`, `http/head.rs`; limits in `consts.rs` |
| REQ-SEC-013 cookie persistence | `cookie.rs:649-746`, `agent.rs:1056-1089`, `port::CookieStorage` |

## 2. Findings

### File by file

Each row says what the file holds, with line ranges, and which concepts it mixes. "Tests" is the size of the inline `#[cfg(test)] mod tests`. The crate has one `pub(crate)` item (`bytes::copy_prefix`, `bytes.rs:107`) and nine `pub(super)` items, all in `agent/bound.rs` (61, 75, 114, 210, 240, 288, 339, 436).

| File | Contents, by line | Concepts mixed | Tests |
|---|---|---|---|
| `lib.rs` 117 | docs 1-25; `#![no_std]`, `forbid(unsafe_code)`, the no-panic `deny` list 26-38; `extern crate std` under `any(test, feature = "std")` 40-41; 22 `pub mod` lines 43-66; `mod error_trait` under `error-trait` 68-117 with a macro for nine error types (84-94) | One. The macro's list omits `channel::ChannelError`, `contents::ContentsError`, `form::FormRefused`, `json::JsonError`, `base64::Base64Error`, `proxy::ProxyError`, `dbsc::{InstructionsError, ProofError}`, `user_agent::UserAgentError`, `agent::PushProblem`, `zxnet::Malformed` | 17 (100-116) |
| `consts.rs` 494 | time 5-12; addresses 14-42; HTTP and the profile 44-122; `pub mod header` 124-182; accept and coding tokens 184-205; `pub mod media` 207-226; `pub mod cache` 228-236; WebSocket 238-303; SSE and push timing 305-336; cookies 338-385; encodings 387-415; descriptor 417-430; forms 432-439; zxnet 441-467; the agent's defaults 469-494 | One (a table). Module-local limits also live in `contents.rs:22-30`, `channel.rs:23-42`, `descriptor.rs:45-67`, `dbsc.rs:21-65`, `zxnet.rs:36-49`, `proxy.rs:20-42`, `user_agent.rs:8-13`, `sse.rs:15-18`: nine places for "every limit" | none |
| `port.rs` 265 | `ConnectionId` 19-34; `Security`, `LinkState`, `Received` 36-67; `Transport` 69-95; `RandomSource` 97-103; `CookieStorage` 105-117; `NetInput`, `NetOutput` 119-150; `slot` 152-158; `Pump` 160-265 (`execute` 204-226, `poll` 230-264) | One: the L8 contract and its pump. Two more L8 traits sit elsewhere: `cookie::Cookies` (154-192) and `dbsc::DeviceKeys` (80-94), both named by `ARCHITECTURE.md`'s L8 list | none (through `tests/common`) |
| `bytes.rs` 318 | `MAX_U64_DIGITS`, `Overflow` 5-10; `Writer` 12-99; `pub(crate) copy_prefix` 101-112 (the rule against `copy_from_slice`, REQ-GEN-019); `decimal_digits` 114-129; `TextBuf` 131-203; `trim_ows`, `parse_decimal`, `hex_number`, `decimal_number`, `hex_value`, `starts_with_ignore_case`, `split_once` 205-278 | Two small ones: bounded buffers and ASCII lexical helpers | 39 |
| `base64.rs` 209 | `Base64Error` 10-21; lengths 23-33; `alphabet` 35-37; `encode` 39-59; `sextet` 64-74; `decode_group` 76-107; `decode` 109-124 (`copy_from_slice` at 120); `decode_in_place` 126-151 | One | 57 |
| `sha1.rs` 169 | constants 9-21; `Sha1` 23-118 (`update` 46-58, `finish` 62-74, `compress` 86-117); `digest` 120-128 | One | 40 |
| `sha256.rs` 235 | constants 8-32; `Digest` 35; `Sha256` 37-135; `digest` 137-143; `parse_hex` 145-159; `to_hex` 161-171; a private `hex_value` 173-184 | One; no caller inside the crate (REQ-FNT-004's fonts by digest were withdrawn with decision E.111) | 50 |
| `json.rs` 576 | `JsonError`, `JsonErrorKind` 13-39; `JsonStr` 41-121 (`decode_into` 63-110, `equals` 112-120); `Token` 123-144; `State` 146-161; `JsonReader` 163-451 (`next_token` 229-282, `value` 288-317, `number` 341-374, `string` 377-399, `escape` 401-426, `skip` 439-450); `hex4` and surrogates 453-480; `integer` 482-493 | Two: the string decoder and the tokeniser; 494 lines of code | 82 |
| `user_agent.rs` 264 | limits 8-13; `Product` 15-29; `UserAgentError` 31-41; `significant_version` 43-56; `os_family` 58-78; `tchar`, `token`, `comment` 80-97; `UserAgentString` 99-184 (`Default` 106-116, `new` 125-155) | One | 79 |
| `form.rs` 184 | `FormMethod` 13-20; `FormSubmission` 22-38; `FormRefused` 40-57; `destination` 59-84; `encode_component` 86-101; `encode` 103-125 | One (the address rule and the encoding; the state machine half is in `agent.rs:2113-2226`) | 58 |
| `contents.rs` 339 | limits 22-47; `ContentsError`, `Fault` 49-77; `Date` 79-88; `Entry` 90-114; `LineFault` 116-123; `Entries` 128-133; `read` 140-152; `title`, `page`, `date`, `target` 154-209; `first_time` 211-222; `impl Iterator` 224-263 | One | 75 |
| `channel.rs` 348 | file names 23-42; `ChannelError` 44-68; `ChannelFile` + `from_name` 70-111; `check_segment`, `check_folder_path`, `written_path` 113-165; `ChannelAddress` 167-174; `parse_address` 176-205; `is_inside`, `redirect_keeps_channel` 207-228; `file_url` 230-247; `is_tti`, `is_t42` 249-266 | Two small ones: address and folder rules (REQ-WEB-023), content checks (REQ-WEB-027) | 81 |
| `url.rs` 867 | `UrlError` 29-57; `Scheme` 59-107; `Host`, `IpAddress` 109-140; `Url` 142-155; `Parts` 157-165; `check_characters`, `scheme_end`, `split_parts` (194-232), `parse_port` 167-242; `is_path_char`, `check_path` 244-275; `ip_literal`, `parse_ipv4`, `parse_ipv6`, `find_double_colon`, `parse_groups`, `is_numeric_label`, `check_host` 277-410; `impl Url` 412-640 (`build` 421-479, `parse_host_only` 483-494, `join` 498-547, accessors 549-639); `remove_dot_segments` 642-673; `Origin` 675-699 | Six: lexical splitting, host and IP-literal grammar (134 lines on their own), path grammar and dot segments, the normalised value and its accessors, relative resolution, `Origin` | 167 |
| `http.rs` 899 | `mod head` 14-16; `HttpError` 27-58; `Method` 60-78; `write_request_line`, `write_header`, `write_host` 80-102; `MediaType` 104-149; `Framing` 151-162; `ResponseHead` 164-204; `has_token`, `apply_cache_control`, `FramingHeaders`, `read_header` (240-295), `parse_head` (297-364), `each_field` 206-375; `HEAD_END`, `HeadCollector` 377-428; `ChunkState`, `BodyStep`, `BodyDecoder` (`feed_chunked` 571-636), `parse_chunk_size` 430-652 | Four: request writing; the profile's reading of a parsed head (including WebSocket-handshake and `Clear-Site-Data` facts); the byte-level head collector; body framing with chunked decoding. The raw grammar is already in `http/head.rs` | 246 |
| `http/head.rs` 472 | `HeadError` 29-53; `Field` 55-63; `Head`, `Fields` 65-102; `parse` 104-136; `take_line`, `next_field`, `read_status_line`, `read_field` 138-200; `digit_value`, `is_token_character`, `is_field_text` 202-223 | One; private to `http` | 248, with the crate's only `proptest!` (424-471) |
| `ws.rs` 630 | `WsError` 20-46; `HandshakeKey`, `new_key`, `accept_for`, `write_handshake_headers`, `check_handshake` 48-103; `write_frame`, `write_frame_with_mask`, `write_close` 105-153; `WsMessage` 155-173; `ReadState`, `FrameReader` 175-426 (`feed` 259-318, `begin_frame` 321-383, `end_frame` 386-425) | Three: the opening handshake, client frame writing, the server frame reader; 427 lines of code | 203 |
| `sse.rs` 409 | `BOM`, `MAX_FIELD_NAME` 15-18; `SseEvent`, `SseError`, `Field`, `State` 20-60; `SseParser` 62-311 (`byte` 138-189, `dispatch` 292-310) | One | 97 |
| `cookie.rs` 1410 | `MAX_AGE_SECONDS` 22-23; `SameSite`, `Site`, `CookieRejected` 25-74; `Record` (15 fields) 76-113; `Parts`, `Attributes` 115-134; `CookieInfo` 136-152; `Cookies` trait 154-192; `impl Cookies for CookieJar` 194-231; `CookieJar` 233-248; `impl CookieJar` 250-747: primitives 250-395 (`remove` 346-363, `victim` 377-391), `store` 402-412, `store_within` 419-534, `make_room` 536-551, `header_for` 557-628, `sort_key` 630-636, `reached_securely` 642-647, `export` 654-677, `import` 682-691, `import_one` 693-746; export flags 749-788; `check_prefixes` 790-814; `parse_attributes` 816-877; `parse_max_age` 879-891; `default_cookie_path`, `path_matches` 893-911; the cookie-date algorithm and civil calendar 913-1042 | Eight: the L8 `Cookies` contract; the arena store and eviction; the `Set-Cookie` algorithm (RFC 6265bis 5.6, 5.7); attributes and prefix rules; `Cookie` header selection and order (5.8.3); the HTTPS-reached memory (REQ-SEC-007); the persistence format (REQ-SEC-013, version 2); the date algorithm (5.1.1) | 367 |
| `dbsc.rs` 1184 | header names, limits, key sizes 21-65; `KeyHandle`, `PublicKey`, `DeviceKeys` 67-94; the RFC 9651 cursor `Fields` 100-237; `is_tchar` 239-246; `Registration`, `read_registration` (264-332); `Challenge`, `read_challenge` 334-364; `ScopeRule`, `Instructions`, `Answer`, `InstructionsError` 370-423; a typed layer over `json` (`next`, `text`, `string`, `boolean`, `skip`, `object`, `array`) 425-496; `read_instructions` (498-551), `read_scope`, `read_rule`, `read_credentials` 553-643; `ProofError`, `base64url`, `json_text`, `write_proof` (712-762) 649-762; `Session`, `domain_matches`, `covers`, `missing`, `site_member` 768-855; `Sessions` 857-934 | Six: an L8 trait; a structured-field reader; two header readers; the instructions reader; the JWS proof writer with its own base64url; the session model and store | 249 |
| `descriptor.rs` 1056 | limits, `DEFAULT_PAGE`, `SUBCODE_DIGITS` 45-67; `Member`, `DescriptorError`, `PushMethod` 69-146; `LinkedService`, `Descriptor` (13 fields, two `TextBuf` arenas), `Alias` 148-198; `text`, `expect_string`, `parse_mpp`, `check_template` (232-258), `expand_template` (262-286), `address`, `bounded_integer`, `first` 200-317; `impl Descriptor` 319-763: `parse`, `parse_channel`, `channel_defaults`, `empty`, `parse_with` (368-468), `parse_push` (470-526), `parse_origins`, `parse_aliases` (550-591), `alias`, `aliases`, `alias_target`, `parse_services` (610-695), accessors 697-762 | Four: the JSON member grammar with its duplicate and unknown rules; the page template and its SSRF guard; the channel variant's extra rules; the stored model with index pairs into arena strings (158-159, 196-197) | 292 |
| `proxy.rs` 604 | SOCKS constants 20-42; `ProxyKind`, `ProxyError` 44-64; `hidden_local` 66-81; `write_connect`, `decimal`, `read_connect_reply` 83-148; `read_socks_choice`, `write_socks_connect`, `socks_reply_length`, `read_socks_reply` 150-231; `ProxyAddress`, `parse_proxy` 233-266; under `std`: `Proxy` (`parse`, `open_tunnel`), `TunnelError`, `MAX_CONNECT_REPLY`, `CONNECT_READ`, `tunnel` (341-390) 268-390 | Five: a local-name policy used by the agent and the feed, not by the proxy code; HTTP `CONNECT`; SOCKS5; a setting's syntax; the only blocking `std::io` in the crate, under eleven item-level `cfg`s | 213 (the tunnel tests 502-579 under `std`) |
| `zxnet.rs` 1031 | limits 36-49; `KNOWN_CHANNELS` 51-61; `ChannelError` 63-76; `Channel` 78-187 (`from_identifier` 89-127, `from_address` 140-168); `HeaderField`, `Malformed`, `LiveEvent`, `LiveInput`, `LiveOutput` 189-334; `LiveBuffers`, `LiveStorage` 336-375; `Phase`, `Walk`, `LiveSink`, `event` 377-400; `ZxnetFeed` 402-423; `magazine`, `page_index`, `walk_order`, `page_from_walk_order` 425-448; `next_integer`, `next_packet_data` (`copy_from_slice` 466), `Message`, `STATUS_BYTES`, `next_u8`, `next_u16`, `next_magazine`, `next_base64`, `parse_message` (511-569), `cross_check`, `rebuild` (`copy_from_slice` 591) 450-594; `impl ZxnetFeed` 596-1031 (`handle` 652-695, `connected` 712-739, `received` 807-883, `message` 886-956, `walk_next` 959-977, `tick` 979-998, `tick_walk` 1000-1013, `next_deadline` 1015-1030) | Five: the channel-identifier codec; the server-message grammar with packet rebuilding and the decoder cross-check; the I/O vocabulary and buffers; the connection, handshake, keepalive and reconnection machine; the page walk | none (`tests/zxnet_replay.rs`) |
| `agent.rs` 2764 | `T42_PACKET` 49-50; `Config` 52-128; `Buffers`, `Storage` 130-198; `Subscription`, `Input` (15 variants), `Source`, `PageBytes`, `Failure` (16), `PushProblem`, `Event` (34), `BoundChange`, `Output`, `Sink` 200-592; private state `Link`, `PageFile`, `Purpose`, `Exchange`, `Target`, `FetchConnection`, `CacheEntry`, `FormPhase`, `FormState`, `PushPhase`, `PushConnection` 594-751; `UserAgent` (31 fields) 753-807; `mod bound`, `BOUND_INSTRUCTIONS_LIMIT`, the `not(dbsc)` stubs 809-839; `event`, `cookie_store`, `store_response_cookies` (864-894), `write_cookie_header` (899-926), `channel_file_media` (931-952) 841-952; `impl UserAgent` 954-2764: construction 955-1034, accessors and `seconds` 1036-1054, `save_cookies`, `load_cookies` 1056-1089, `handle` 1091-1172, requests 1174-1518 (`dispatch` 1318-1420, `write_request` 1448-1497), fetch events 1520-1737 (`fetch_received` 1581-1642, `fetch_head_complete` 1645-1690), `complete` 1739-1846, `complete_page` 1851-1904, `complete_channel` 1910-1962, `redirect` 1964-2024, `redirect_keeps_channel` 2030-2040, `update_cache` 2042-2081, `open_descriptor` 2083-2111, forms 2113-2226 (`submit` 2117-2198), push 2228-2667 (`push_connected` 2323-2394, `push_head_complete` 2451-2502, `push_frames` 2506-2586, `deliver_event` 2620-2667), time 2669-2764 | Nine at least: the public I/O vocabulary (545 lines of enums); configuration and storage; the fetch connection and exchange lifecycle; the request scheduler with the rate limit, queue and `Retry-After`; the page cache and validators; channel and service opening; redirects and their policy; forms; push over two protocols with the heartbeat; the cookies glue and persistence; the DBSC hooks; timers | none (`tests/agent_replay.rs`, `tests/dbsc.rs`) |
| `agent/bound.rs` 454 | status constants 22-28; `Asked`, `Registering`, `Deferred` 30-57; `Bound` 59-78; `bit`, `sf_string`, `header` 80-107; `write_headers` 109-157; `session_of` 159-191; `impl UserAgent` (dbsc) 193-454: `set_device_keys`, `bound_sessions`, `bound_next` 210-235, `bound_defer` 240-282, `bound_head` 288-336, `bound_complete` 339-432, `bound_failed` 436-453 | One; already the model of a child module adding an `impl` block and reaching the parent's private fields | none (`tests/dbsc.rs`) |
| `tests/common/mod.rs` 296 | `Reply` 12-28; `Connection` 30-39; `Replay` 41-59 (resolution map, scripted replies per `host:port`, `connects`, `sent`, `requests`, 7 bytes per receive, `no_tls`); `ReplayError` 61-81; `header_value` 88-94; `impl Replay` 96-171 (`answer` 127-170 computes the WebSocket accept from the request's key); `impl Transport for Replay` 173-239; `Counter` 241-252; `client_frame`, `server_frame`, `response` 254-296 | The played server of REQ-WEB-013; `#![allow(dead_code)]` because each test binary uses a subset | — |
| `tests/agent_replay.rs` 1599 | harness 33-199 (`settle` 85-101); `assert_profile_headers` 200-242; fetch, cache, limits, timers 253-414; redirects and blocking 416-484; HTTPS, downgrade, TLS, descriptor rejections 486-542; forms 544-709; links 711-732; push 734-881; cookies 883-1052 (`PortCookies` 909-975); user agent 1054-1077; proxy 1079-1101; the exchange report 1103-1126; keep-alive retry 1128-1136; persistence 1138-1183; the three `not(feature)` tests 1185-1259; channels 1261-1523; input and heartbeats 1525-1599 | 53 tests, every feature-dependent one gated | — |
| `tests/zxnet_replay.rs` 417 | live-capture samples 20-27; harness 29-148; 11 tests 150-417, the last replaying `$NEOTELETEXT_CORPUS/zxnet/*.jsonl` when present | — | — |
| `tests/dbsc.rs` 329 | `KeyLog`, `Keys` 27-56; harness 58-132; `proof` and helpers 134-170; `registered` 176-195; 6 tests 197-329 | — | — |

### Functions over 80 lines

Raw lines from signature to closing brace. Clippy's `too_many_lines` counts code lines only (limit 100) and has no allowance anywhere in the crate; the four marked are within a few code lines of it, so any addition inside them fails the gate.

| Function | Lines | Length | |
|---|---|---|---|
| `CookieJar::store_within` | `cookie.rs:419-534` | 116 | near the limit |
| `UserAgent::complete` | `agent.rs:1739-1846` | 108 | near the limit |
| `UserAgent::dispatch` | `agent.rs:1318-1420` | 103 | near the limit |
| `Descriptor::parse_with` | `descriptor.rs:368-468` | 101 | near the limit |
| `UserAgent::bound_complete` | `agent/bound.rs:339-432` | 94 | |
| `Descriptor::parse_services` | `descriptor.rs:610-695` | 86 | |
| `UserAgent::submit` | `agent.rs:2117-2198` | 82 | |
| `UserAgent::push_frames` | `agent.rs:2506-2586` | 81 | |
| `UserAgent::handle` | `agent.rs:1092-1172` | 81 | |

Near 80: `ZxnetFeed::received` 807-883 (77), `CookieJar::header_for` 557-628 (72), `push_connected` 2323-2394 (72), `ZxnetFeed::message` 886-956 (71), `read_registration` 264-332 (69), `feed_chunked` 571-636 (66), `parse_head` 299-364 (66).

### `impl` blocks over 300 lines

| Block | Lines | Length |
|---|---|---|
| `impl UserAgent` | `agent.rs:954-2764` | 1,811 |
| `impl CookieJar` | `cookie.rs:250-747` | 498 |
| `impl Descriptor` | `descriptor.rs:319-763` | 445 |
| `impl ZxnetFeed` | `zxnet.rs:596-1031` | 436 |

### Files over 800 lines

`agent.rs` 2764, `cookie.rs` 1410, `dbsc.rs` 1184, `descriptor.rs` 1056, `zxnet.rs` 1031, `http.rs` 899, `url.rs` 867; and `tests/agent_replay.rs` 1599 (an integration test file, which the conventions leave as one file per area).

### Duplicated shapes

| # | Shape | Where |
|---|---|---|
| 1 | RFC 9110 section 5.6.2 `tchar`, written three times | `user_agent.rs:81-87` (`tchar`), `http/head.rs:209-215` (`is_token_character`), `dbsc.rs:240-246` (`is_tchar`) |
| 2 | hexadecimal digit value | `bytes.rs:256-263` (`pub hex_value`) duplicated privately at `sha256.rs:177-184`; `http/head.rs:203-205` (`digit_value`); the same fold rewritten at `bytes.rs:238`, `json.rs:453-458`, `descriptor.rs:219-225`, `url.rs:364`, `http.rs:651` |
| 3 | three hexadecimal digits to `PageAddress` | `descriptor.rs:219-225`, `channel.rs:99-110`, `contents.rs:164-170` (different digit alphabets by design; the same `from_mpp` tail) |
| 4 | decimal writer | `bytes.rs:115-129` (`decimal_digits`, u64) and `proxy.rs:112-126` (`decimal`, u16, the same loop) |
| 5 | base64 encoder | `consts.rs:392` with `base64.rs:41-59` (standard, padded) and `dbsc.rs:664-687` (URL alphabet, unpadded); the group and shift arithmetic is the same |
| 6 | `name=value` split with OWS | `cookie.rs:437-443` and `cookie.rs:831-837` are the same seven lines; `http.rs:130` and `:215` use `bytes::split_once` for the same thing; `cookie.rs:433-436` splits at `;` by hand |
| 7 | host suffix match, case-insensitive | `dbsc.rs:797-803` (`domain_matches`), `dbsc.rs:848-855` (`site_member`), `proxy.rs:76-79` (`hidden_local`) |
| 8 | printable-ASCII predicates | `url.rs:176`, `zxnet.rs:103`, `zxnet.rs:146`, `user_agent.rs:96`, `contents.rs:236`, `dbsc.rs:154`, `descriptor.rs:205` |
| 9 | write a WebSocket frame into the request buffer, then `Send` | `agent.rs:2283-2288`, 2512-2519, 2559-2567, 2572-2580, 2716-2723, 2741-2748 (six); `zxnet.rs:758-764`, 832-836, 852-863, 866-871 (four); the ping answer `zxnet.rs:847-864` and `agent.rs:2556-2568` are the same twelve lines |
| 10 | head complete, parse, store the cookies | `agent.rs:1645-1664` and 2451-2475; the handshake acceptance `zxnet.rs:810-826` is a third form |
| 11 | `PageBytes { source: Source::Push, .. }` literal | `agent.rs:2533-2539`, 2545-2551, 2628-2634, 2653-2659; the form-response pair 1820-1826 and 1833-1839 |
| 12 | `let too_long = \|_\| UrlError::TooLong;` | `url.rs:434`, 506, `channel.rs:234`, `descriptor.rs:269` |
| 13 | two parallel connection-phase enums | `agent.rs:719-737` (`PushPhase`) and `zxnet.rs:377-384` (`Phase`), the same `Connecting`/`Handshake { deadline }` shape and the same deadline folding (`agent.rs:2753-2763`, `zxnet.rs:1015-1030`) |
| 14 | `copy_from_slice` against the crate's own rule (`bytes.rs:104-106`) | `base64.rs:120`, `zxnet.rs:466`, 548, 591 |

Shapes 9, 10 and 11 are placement: the moves in section 4 give each a named form in the file the copies land in. Shapes 1 to 8 and 12 to 14 are definitions repeated across files; they are listed in section 6, not changed by this plan.

### Naming

| Kind | As it is | Note |
|---|---|---|
| Error types | `UrlError`, `HttpError`, `HeadError`, `WsError`, `SseError`, `JsonError`, `Base64Error`, `ProxyError`, `TunnelError`, `DescriptorError`, `ContentsError`, `InstructionsError`, `ProofError`, `UserAgentError` follow `<Thing>Error`; `CookieRejected`, `FormRefused`, `Failure`, `PushProblem`, `Malformed`, `Fault` do not | Several of the odd ones are deliberate ("rejected", "refused" say the outcome). Not renamed by this plan. |
| Two `ChannelError`s | `channel::ChannelError` (`channel.rs:46`, a web folder's address) and `zxnet::ChannelError` (`zxnet.rs:65`, a feed identifier); only the latter is in `lib.rs`'s `error_trait!` list | Two unrelated nouns called "channel": `channel::ChannelAddress` and `zxnet::Channel`. The plan keeps both names (they are public paths) and keeps them in different directories. |
| Reader verbs | `dbsc` uses `read_*`; `descriptor` and `url` use `parse_*` and `check_*`; `cookie` uses `store` and `parse_*`; `contents` uses `read` plus field functions; `proxy` uses `read_*` and `write_*`; `http` uses `parse_head` and `write_*` | Siblings inside each directory agree; across directories they do not. Not renamed. |
| Module names | `ws`, `sse`, `http`, `dbsc` beside `user_agent`, `descriptor`, `contents` | The abbreviations are the standards' own names (`00-conventions.md` section 4). Kept. |
| Machine vocabularies | `agent::{Input, Output, Event, Sink, Storage, Buffers}` against `zxnet::{LiveInput, LiveOutput, LiveEvent, LiveSink, LiveStorage, LiveBuffers}` | Public paths; kept. The two directories get the same child names (`events.rs`) so the layouts agree. |

### Where the tests are

| Place | Files | Lines |
|---|---|---|
| Inline `mod tests` of 60 lines or fewer (stay) | `lib.rs` 17, `bytes.rs` 39, `sha1.rs` 40, `sha256.rs` 50, `base64.rs` 57, `form.rs` 58 | 261 |
| Inline `mod tests` over 60 lines | `contents.rs` 75, `user_agent.rs` 79, `channel.rs` 81, `json.rs` 82, `sse.rs` 97, `url.rs` 167, `ws.rs` 203, `proxy.rs` 213, `http.rs` 246, `http/head.rs` 248 (with the only `proptest!`), `dbsc.rs` 249, `descriptor.rs` 292, `cookie.rs` 367 | 2,399 |
| No inline tests (state machines, contracts, constants) | `agent.rs`, `agent/bound.rs`, `zxnet.rs`, `port.rs`, `consts.rs` | — |
| Integration (`tests/`) | `agent_replay.rs` (53), `dbsc.rs` (6), `zxnet_replay.rs` (11), over the Replay harness of `tests/common/mod.rs` (`impl Transport` with scripted replies, a seven-byte receive chunk, WebSocket accept computed from the key, `Counter` as the random source) | 2,641 |

Every inline test module carries `#[allow(clippy::unwrap_used, clippy::indexing_slicing, clippy::arithmetic_side_effects, clippy::panic)]`; three use the `reason = "a test"` form (`user_agent.rs:187`, `proxy.rs:393`, `dbsc.rs:937`); `sha256.rs:187` and `contents.rs:266` allow a subset.

## 3. The target layout

The 2018 layout throughout: a parent `foo.rs` holds the concept's spine (the type, its construction, the `mod` lines and the `pub use` lines) and children hold its parts. Every public path of section 1 is kept by `pub use` in the parent, so `lib.rs`'s 22 `mod` lines and `error_trait!` list are unchanged and no importer changes. Sizes are approximate; a file marked † is over 400 lines and says why in section 4.

```
src/lib.rs                      117  unchanged
src/consts.rs                   494  unchanged (a table)
src/bytes.rs                    318  unchanged
src/base64.rs                   209  unchanged
src/sha1.rs                     169  unchanged
src/sha256.rs                   235  unchanged
src/port.rs                     265  unchanged
src/user_agent.rs               185  as it is, less its tests
src/user_agent/tests.rs          80
src/form.rs                     184  unchanged
src/contents.rs                 265  as it is, less its tests
src/contents/tests.rs            75
src/channel.rs                  270  as it is, less its tests
src/channel/tests.rs             80
src/json.rs                     495  as it is, less its tests †
src/json/tests.rs                80
src/sse.rs                      315  as it is, less its tests
src/sse/tests.rs                 95

src/url.rs                      330  UrlError, Scheme, Host, IpAddress, Url, Parts, the lexical split, build, parse_host_only, join, accessors, Origin; pub use host::ip_literal
src/url/host.rs                 140  ip_literal, parse_ipv4, parse_ipv6, find_double_colon, parse_groups, is_numeric_label, check_host
src/url/path.rs                  70  is_path_char, check_path, remove_dot_segments
src/url/tests.rs                170

src/http.rs                     160  HttpError, Method, MediaType, Framing, write_request_line, write_header, write_host; mod head, response, body; pub use
src/http/head.rs                225  the status line and field lines (as it is, less its tests)
src/http/head_tests.rs           --  (no: see response below; head's tests go to http/tests.rs)
src/http/response.rs            270  HEAD_END, HeadCollector, ResponseHead, has_token, apply_cache_control, FramingHeaders, read_header, parse_head, each_field
src/http/body.rs                225  ChunkState, BodyStep, BodyDecoder, parse_chunk_size
src/http/tests.rs               495  the tests of http.rs (246) and of head.rs (248, with the proptest) †

src/ws.rs                       430  as it is, less its tests †  (the three-way split of 4.9 is optional)
src/ws/tests.rs                 205

src/cookie.rs                   360  SameSite, Site, CookieRejected, Record, Parts, CookieInfo, the Cookies trait, impl Cookies for CookieJar, CookieJar and its primitives (new, set_limits, wipe, parts, next_tick, remove, find, victim, count_where, make_room, cookies, info, remove_where, clear_host, len, is_empty); pub use date::parse_cookie_date
src/cookie/store.rs             250  Attributes; impl CookieJar { store, store_within }; check_prefixes, parse_attributes, parse_max_age, default_cookie_path, path_matches
src/cookie/header.rs            100  impl CookieJar { header_for, sort_key, reached_securely }
src/cookie/persist.rs           150  EXPORT_VERSION, the FLAG_ constants, encode_flags, decode_flags; impl CookieJar { export, import, import_one }
src/cookie/date.rs              135  is_date_delimiter, leading_digits, MONTHS, parse_cookie_date, parse_time_token, the calendar constants, is_leap, days_in_month, days_from_civil
src/cookie/tests.rs             370

src/dbsc.rs                     115  header names, limits, key sizes, KeyHandle, PublicKey, DeviceKeys; mod structured, headers, instructions, proof, session; pub use
src/dbsc/structured.rs          150  Fields (the RFC 9651 cursor), is_tchar
src/dbsc/headers.rs             120  Registration, read_registration, Challenge, read_challenge
src/dbsc/instructions.rs        280  ScopeRule, Instructions, Answer, InstructionsError, Read, next, text, string, boolean, skip, object, array, read_instructions, read_scope, read_rule, read_credentials
src/dbsc/proof.rs               120  ProofError, BASE64URL and the shifts, base64url, json_text, PROOF_JSON_BYTES, write_proof
src/dbsc/session.rs             170  Session, domain_matches, covers, missing, site_member, Sessions
src/dbsc/tests.rs               250

src/descriptor.rs               290  limits, DEFAULT_PAGE, Member, DescriptorError, PushMethod, LinkedService, Descriptor, Alias; parse, parse_channel, channel_defaults, empty; the accessors; pub use template::expand_template
src/descriptor/template.rs       80  SUBCODE_DIGITS, check_template, expand_template; impl Descriptor { page_url }
src/descriptor/parse.rs         250  text, expect_string, parse_mpp, address, bounded_integer, first; impl Descriptor { parse_with, parse_push, parse_origins }
src/descriptor/links.rs         140  impl Descriptor { parse_aliases, parse_services }
src/descriptor/tests.rs         295

src/proxy.rs                    130  ProxyKind, ProxyError, hidden_local, ProxyAddress, parse_proxy; mod connect, socks; #[cfg(feature = "std")] mod tunnel; pub use
src/proxy/connect.rs             70  HTTP_SUCCESS, write_connect, decimal, read_connect_reply
src/proxy/socks.rs              110  the SOCKS constants, read_socks_choice, write_socks_connect, socks_reply_length, read_socks_reply
src/proxy/tunnel.rs             210  Proxy, TunnelError, MAX_CONNECT_REPLY, CONNECT_READ, tunnel; its tests (Arrivals and the tunnel test) inline, the module being std-only
src/proxy/tests.rs              130

src/zxnet.rs                    230  limits, KNOWN_CHANNELS, LiveBuffers, LiveStorage, Phase, Walk, LiveSink, event, ZxnetFeed, new, allow_local, through_proxy, name_product, channel, page_exists; mod channel, events, message, feed, walk; pub use
src/zxnet/channel.rs            125  ChannelError, Channel
src/zxnet/events.rs             150  HeaderField, Malformed, LiveEvent, LiveInput, LiveOutput (+ net)
src/zxnet/message.rs            180  magazine, next_integer, next_packet_data, Message, STATUS_BYTES, next_u8, next_u16, next_magazine, next_base64, parse_message, cross_check, rebuild
src/zxnet/feed.rs               330  impl ZxnetFeed { handle, connect, connected, dropped, send_frame, send_text, page_search, opened, received, message, tick, next_deadline }
src/zxnet/walk.rs                75  page_index, walk_order, page_from_walk_order; impl ZxnetFeed { walk_next, tick_walk, walk_deadline }

src/agent.rs                    470  T42_PACKET; Link, PageFile, Purpose, Exchange, Target, FetchConnection, CacheEntry, FormPhase, FormState, PushPhase, PushConnection; UserAgent; new, with_cookies, with_store, descriptor, cookies, seconds, handle, tick, next_deadline, event; the mod lines; mod bound under dbsc and its not(dbsc) stub impl; pub use config::*, events::* †
src/agent/config.rs             150  Config, Default, Buffers, Storage
src/agent/events.rs             395  Subscription, Input, Source, PageBytes, Failure, PushProblem, Event, BoundChange, Output (+ net), Sink
src/agent/cookies.rs            165  cookie_store, store_response_cookies, write_cookie_header; impl UserAgent { save_cookies, load_cookies, is_downgrade, remember_secure, wipe_cookies }
src/agent/request.rs            280  impl UserAgent { refusal, blocked, peer_blocked, report_refusal, dispatch, start_exchange, write_request, send_request }
src/agent/fetch.rs              230  impl UserAgent { fetch_connected, fetch_closed, fetch_lost, fetch_received, fetch_head_complete, abandon_fetch, fail_exchange, finish_purpose, report_exchange }
src/agent/response.rs           190  impl UserAgent { complete, redirect, redirect_keeps_channel }
src/agent/page.rs               135  impl UserAgent { enqueue, take_queued, cache_entry, complete_page, update_cache }
src/agent/service.rs            200  channel_file_media; impl UserAgent { leave_channel, open_channel, folder, fetch_contents, follow_link, complete_channel, open_descriptor }
src/agent/form.rs               165  impl UserAgent { submit, confirm, complete_form }
src/agent/push.rs               350  impl UserAgent { subscribe, write_subscription, send_subscribe, send_push_frame, push_address, push_connect, push_connected, push_lost, push_received, push_head_complete, push_tick, heartbeat_due, heartbeat, send_input }
src/agent/push_data.rs          150  impl UserAgent { push_frames, push_events, deliver_event, deliver_push_page }
src/agent/bound.rs              454  unchanged †

tests/common/mod.rs             296  unchanged
tests/agent_replay.rs          1599  unchanged
tests/zxnet_replay.rs           417  unchanged
tests/dbsc.rs                   329  unchanged
```

(The line `src/http/head_tests.rs -- (no …)` above is a note, not a file: `head.rs` keeps no test file of its own; its tests join `http/tests.rs`, where `#[cfg(test)] mod tests;` in `http.rs` reaches `super::head` as before.)

After the work: 24 source files become 66; largest 495 (`json.rs`, `http/tests.rs`), none over 500; inline test lines fall from 2,660 to 261; item-level feature `cfg` in shared files falls from 25 (`agent` 11 for `dbsc`, `proxy` 11 for `std`, `lib` 3) to 15 (`agent`'s 11 `dbsc` sites, `proxy`'s one `mod tunnel`, `lib`'s 3); the seventeen `cfg!` tests stay by design (section 5).

### Shared forms extracted with the moves, behaviour unchanged

| Form | File | Replaces | Callers |
|---|---|---|---|
| `fn send_push_frame(&mut self, opcode: u8, payload: &[u8], sink)` — write a frame with `ws::write_frame` into `buffers.push_request` and emit `Output::Send` on `ConnectionId::Push` | `agent/push.rs` | shape 9, the six copies at `agent.rs` 2283-2288, 2512-2519 (a close frame: a `send_push_close(code, sink)` twin over `ws::write_close`), 2559-2567, 2572-2580, 2716-2723, 2741-2748 | `send_subscribe`, `push_frames` (three times), `heartbeat`, `send_input` |
| `fn send_frame(&mut self, opcode: u8, payload: &[u8], sink)` and `send_close(code, sink)` — the same for the feed's `buffers.request` and `LiveOutput::Send` | `zxnet/feed.rs` | shape 9, `zxnet.rs` 758-764 (today's `send_text`, which becomes `send_frame(OPCODE_TEXT, ..)`), 832-836, 852-863, 866-871 | `send_text` (`page_search`, `opened`, `message`, `tick`), `received` (three times) |
| `fn deliver_push_page(&self, media: MediaType, len: usize, sink)` — the `PageBytes { source: Source::Push, media, url, secure, bytes }` output from `buffers.push_message[..len]` | `agent/push_data.rs` | shape 11, `agent.rs` 2533-2539, 2545-2551, 2628-2634, 2653-2659 | `push_frames` (text and binary), `deliver_event` (page and packets) |
| `fn complete_form(&mut self, exchange, head, body, sink)` — the `Purpose::Form` arm of `complete` | `agent/form.rs` | the arm at `agent.rs:1814-1844`, so that `complete` drops under the `too_many_lines` limit with room and the form-response pair (shape 11's second half) sits with the form's other steps | `complete` |
| `fn push_tick(&mut self, now, sink)` — the push half of `tick` | `agent/push.rs` | `agent.rs:2679-2694` | `tick` |
| `fn wipe_cookies(&mut self)` — the body of the `Input::WipeCookies` arm | `agent/cookies.rs` | `agent.rs:1157` | `handle` |

Each is a mechanical extraction of lines already present; the diff of its commit shows the copies removed and the one body added.

## 4. The moves

Each step is one commit from the baseline, from the leaves to the roots inside the crate (`proxy`, `http`, `url` are used by the rest; `agent` last), and passes:

- `scripts/check.sh fast` (fmt, Clippy with warnings as errors, the tests, `check-constants`, `check-io`);
- `cargo xtask features` (the crate with no feature and with `push`, `forms`, `cookies`, `dbsc` each alone);
- `cargo test -p neoteletext-web --no-default-features` (the three `not(feature)` tests of `tests/agent_replay.rs:1185-1259`, which `check.sh fast` does not run);
- `cargo build -p neoteletext-web --no-default-features --features error-trait` and `--features std` (neither is in `xtask features`);
- after the steps that touch `cookie`, `dbsc`, `zxnet` or `agent`: `cargo xtask size --target x86_64-unknown-none` (the symbol check that found the baseline's defect);
- `cargo xtask traceability` in every commit that moves a file, so `docs/traceability.md` names the new paths; the commit carries the regenerated file.

Every moved test module is declared in its parent as

```rust
#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::indexing_slicing, clippy::arithmetic_side_effects, clippy::panic)]
mod tests;
```

with exactly the `allow` list the inline module had (the three `reason = "a test"` forms and the two subset lists keep their own text). Each new file begins with a `//!` line naming its concept and the clause or requirement it is written from, then its `use` lines, then its items in the order of `00-conventions.md` section 7. Public items keep their doc comments, so `missing_docs` is satisfied by the move. Tests are moved, not rewritten; a test that reads a private field moves to the `tests.rs` of the directory whose parent defines the field, which keeps it reachable.

No importer changes in any step: every public path is kept by `pub use`. The browser's 12 files and the fuzz targets are listed in section 1 so that the re-pin commit (phase E5) can confirm by `grep` that nothing of this crate's changed; the fuzz targets' eight imports are rechecked with `cargo fuzz build` once, after step 11, since the fuzz build is not in the local gate.

### Step 1: `proxy.rs` becomes `proxy/`

Moves: `HTTP_SUCCESS` 41-42, `write_connect` 83-109, `decimal` 111-126, `read_connect_reply` 128-148 to `proxy/connect.rs`; the SOCKS constants 20-40 and `read_socks_choice`, `write_socks_connect`, `socks_reply_length`, `read_socks_reply` 150-231 to `proxy/socks.rs`; `Proxy`, `TunnelError`, `MAX_CONNECT_REPLY`, `CONNECT_READ`, `tunnel` 268-390 to `proxy/tunnel.rs`, with the `Arrivals` fake and the tunnel test 500-579 as its inline `tests` module (both are `std`-only, so the module's one `cfg` covers them); the remaining tests 392-499 and 581-603 to `proxy/tests.rs`. The parent keeps `ProxyKind`, `ProxyError`, `hidden_local`, `ProxyAddress`, `parse_proxy`.

Declarations in `proxy.rs`: `mod connect; mod socks; #[cfg(feature = "std")] mod tunnel;` and `pub use connect::{read_connect_reply, write_connect}; pub use socks::{SOCKS_GREETING, SOCKS_MAX_REPLY, read_socks_choice, read_socks_reply, socks_reply_length, write_socks_connect}; #[cfg(feature = "std")] pub use tunnel::{Proxy, TunnelError, tunnel};`. The eleven item-level `std` cfgs become one.

Visibility: `socks::SOCKS_MAX_NAME` becomes `pub(super)` (read by `parse_proxy` in the parent and by `tunnel`'s request buffer size).

### Step 2: `http.rs` becomes a parent with `response.rs` and `body.rs`

Moves: `HEAD_END`, `HeadCollector` 377-428 and `ResponseHead`, `has_token`, `apply_cache_control`, `FramingHeaders`, `read_header`, `parse_head`, `each_field` 164-375 to `http/response.rs` (the collector decides where a head ends and the reader interprets it: one concept, the response head, 270 lines); `ChunkState`, `BodyStep`, `BodyDecoder`, `parse_chunk_size` 430-652 to `http/body.rs`; the tests of `http.rs` 654-899 and of `http/head.rs` 225-472 to `http/tests.rs` (495 lines; over 400 because the proptest strategies of `head.rs` are 50 lines of generators that belong with the parser's tests, and the alternative, two test files under one parent, breaks "tests are `tests.rs` in the concept's directory"). `write_request_line`, `write_header`, `write_host` 80-102 stay in the parent: 23 lines is too small for a file.

Declarations in `http.rs`: `mod head; mod response; mod body;` and `pub use response::{HeadCollector, ResponseHead, each_field, parse_head}; pub use body::{BodyDecoder, BodyStep};`. `head` stays private; `response.rs` reaches it as `super::head`, and `tests.rs` reaches `super::head::{parse, HeadError, ...}` the same way.

Visibility: none beyond the re-exports; `head::HeadError` is already reached through `super`.

### Step 3: `url.rs` becomes a parent with `host.rs` and `path.rs`

Moves: `ip_literal`, `parse_ipv4`, `parse_ipv6`, `find_double_colon`, `parse_groups`, `is_numeric_label`, `check_host` 277-410 to `url/host.rs`; `is_path_char`, `check_path` 244-275 and `remove_dot_segments` 642-673 to `url/path.rs`; the tests 701-867 to `url/tests.rs`. `path.rs` at 70 lines is under the 150 aim; it is kept as a file because the path grammar and dot-segment removal are one clause (RFC 3986 sections 3.3 and 5.2.4) and folding them back puts the parent at 400.

Declarations: `mod host; mod path;` and `pub use host::ip_literal;`.

Visibility: `host::{parse_ipv4, parse_ipv6, check_host}` and `path::{check_path, remove_dot_segments}` become `pub(super)` (called by `build`, `parse_host_only` and `join` in the parent).

### Step 4: `cookie.rs` becomes `cookie/`

Moves: `Attributes` 123-134, `store` and `store_within` 397-534, `check_prefixes` 790-814, `parse_attributes` 816-877, `parse_max_age` 879-891, `default_cookie_path`, `path_matches` 893-911 to `cookie/store.rs`; `header_for`, `sort_key` 553-636 and `reached_securely` 638-647 to `cookie/header.rs`; `export`, `import`, `import_one` 649-746 and the export constants and flag functions 749-788 to `cookie/persist.rs`; the date algorithm and calendar 913-1042 to `cookie/date.rs`; the tests 1044-1410 to `cookie/tests.rs`. The parent keeps the types, the trait and its forwarding impl, the struct and its primitives (`new` to `count_where`, `make_room`), so that every child `impl CookieJar` reaches the private fields through the parent and no field changes visibility.

Declarations: `mod store; mod header; mod persist; mod date;` and `pub use date::parse_cookie_date;`.

Visibility: `store::path_matches` becomes `pub(super)` (used by `header_for`); `make_room` stays private in the parent (used by `store_within` in a child: a child sees its parent's private items). The parent is 360 lines.

Departure from the convention's aim: none; this is the split of the 498-line `impl` block into concept files that section 1 of `00-conventions.md` asks for.

### Step 5: `dbsc.rs` becomes `dbsc/`

Moves: `Fields` 100-237 and `is_tchar` 239-246 to `dbsc/structured.rs`; `Registration`, `read_registration`, `Challenge`, `read_challenge` 248-364 to `dbsc/headers.rs`; 370-643 to `dbsc/instructions.rs`; 649-762 to `dbsc/proof.rs`; 768-934 to `dbsc/session.rs`; the tests 936-1184 to `dbsc/tests.rs`. The parent keeps 21-94 (names, limits, `KeyHandle`, `PublicKey`, `DeviceKeys`).

Declarations in `dbsc.rs` (itself under the unchanged `#[cfg(feature = "dbsc")] pub mod dbsc;` of `lib.rs`): `mod structured; mod headers; mod instructions; mod proof; mod session;` and `pub use headers::{Challenge, Registration, read_challenge, read_registration}; pub use instructions::{Answer, Instructions, InstructionsError, ScopeRule, read_instructions}; pub use proof::{ProofError, write_proof}; pub use session::{Session, Sessions};`. `agent/bound.rs`'s `use crate::dbsc::{...}` resolves unchanged.

Visibility: `structured::Fields` and its methods become `pub(super)` (used by `headers.rs` only); `is_tchar` stays private to `structured`.

### Step 6: `descriptor.rs` becomes `descriptor/`

Moves: `SUBCODE_DIGITS` 66-67, `check_template`, `expand_template` 227-286 and `page_url` 717-723 to `descriptor/template.rs`; `text`, `expect_string`, `parse_mpp` 200-225, `address`, `bounded_integer`, `first` 288-317, `parse_with` 368-468, `parse_push` 470-526, `parse_origins` 528-545 to `descriptor/parse.rs`; `parse_aliases` 550-591 and `parse_services` 610-695 to `descriptor/links.rs`; the tests 765-1056 to `descriptor/tests.rs`. The parent keeps the limits, the enums, the three structs, `parse`, `parse_channel`, `channel_defaults`, `empty`, `alias`, `aliases`, `alias_target` and the accessors 697-762; the index fields of `LinkedService` and `Alias` stay private, written only by the children of the module that defines them.

Declarations: `mod template; mod parse; mod links;` and `pub use template::expand_template;`.

Visibility: `parse::{text, expect_string, parse_mpp, address}` and `template::check_template` become `pub(super)` (used by `links.rs` and `parse.rs`); `links::{parse_aliases, parse_services}` and `parse::parse_with` become `pub(super)` (called from `parse_with` and from `parse`/`parse_channel` in the parent).

### Step 7: `zxnet.rs` becomes `zxnet/`

Moves: `ChannelError` 63-76 and `Channel` 78-187 to `zxnet/channel.rs`; `HeaderField`, `Malformed`, `LiveEvent`, `LiveInput`, `LiveOutput` 189-334 to `zxnet/events.rs`; `magazine` 425-431, 450-594 (`next_integer` to `rebuild`) to `zxnet/message.rs`, `rebuild` and `next_packet_data` keeping their `copy_from_slice` (section 6); `page_index`, `walk_order`, `page_from_walk_order` 433-448, `walk_next` 958-977, `tick_walk` 1000-1013 and the walk's three lines of `next_deadline` 1022-1026 (as `walk_deadline`) to `zxnet/walk.rs`; the rest of `impl ZxnetFeed` 652-1030 to `zxnet/feed.rs`, with `send_frame` and `send_close` extracted (section 3). The parent keeps the limits, `KNOWN_CHANNELS`, the buffers, `Phase`, `Walk`, `LiveSink`, `event`, the struct and 596-650 (`new` to `page_exists`).

Declarations: `mod channel; mod events; mod message; mod feed; mod walk;` and `pub use channel::{Channel, ChannelError}; pub use events::{HeaderField, LiveEvent, LiveInput, LiveOutput, Malformed};`.

Visibility: `message::{parse_message, cross_check, rebuild}` become `pub(super)`; `feed::page_search` and `walk::{walk_next, tick_walk, walk_deadline}` become `pub(super)` (called across the two files); `Message` becomes `pub(super)`. `Walk`'s fields stay private (defined in the parent).

### Step 8: `agent.rs` becomes `agent/`: the vocabulary

Moves: `Config`, `Buffers`, `Storage` 52-198 to `agent/config.rs`; 200-592 (`Subscription` to `Sink`) to `agent/events.rs`. The parent gains `mod config; mod events; pub use config::{Buffers, Config, Storage}; pub use events::{BoundChange, Event, Failure, Input, Output, PageBytes, PushProblem, Sink, Source, Subscription};`. `agent/bound.rs`'s `use super::{BoundChange, Event, ..., Sink, ...}` resolves through the re-exports.

`events.rs` is 395 lines: ten public enums that are the agent's whole interface, kept together because a reader of an `Event` needs `Failure` and `PushProblem` beside it; the alternative, `events.rs` and `failures.rs`, would split one vocabulary.

Visibility: none.

### Step 9: `agent/`: the cookies glue and the push and form parts

One commit per child file, each an independent `impl UserAgent` block, in this order so that each compiles on its own:

1. `agent/cookies.rs`: `cookie_store`, `store_response_cookies`, `write_cookie_header` 845-926; `save_cookies`, `load_cookies` 1056-1089; `is_downgrade`, `remember_secure` 1285-1307; the new `wipe_cookies` (the arm at 1157). Visibility: `cookie_store`, `store_response_cookies`, `write_cookie_header` become `pub(super)` (`fetch.rs`, `request.rs`, `push.rs`, `bound.rs`); `is_downgrade`, `remember_secure`, `wipe_cookies` become `pub(super)` methods. The five `cfg!(feature = "cookies")` tests are then all in this one always-present file.
2. `agent/push.rs` and `agent/push_data.rs`: 2228-2502 and 2697-2751 to `push.rs` with `send_push_frame`, `send_push_close`, `push_tick` extracted; 2504-2667 to `push_data.rs` with `deliver_push_page` extracted. Visibility: `push_connect`, `push_connected`, `push_lost`, `push_received`, `subscribe`, `send_input`, `push_tick`, `send_push_frame`, `send_push_close`, `send_subscribe` become `pub(super)`; `push_frames`, `push_events` become `pub(super)`. The seven `cfg!(feature = "push")` tests stay where they are (`handle`, `dispatch`, `open_descriptor`, `subscribe`, `tick`, `send_input`), each in a function present in every build.
3. `agent/form.rs`: `submit`, `confirm` 2113-2226 and the new `complete_form` from 1814-1844. Visibility: all three `pub(super)`. The four `cfg!(feature = "forms")` tests stay in `handle`, `dispatch` and `complete`.

### Step 10: `agent/`: the exchange lifecycle, the pages and the service

One commit per child file, in this order:

1. `agent/service.rs`: `channel_file_media` 928-952; `leave_channel`, `open_channel`, `folder`, `fetch_contents`, `follow_link` 1178-1232; `complete_channel` 1906-1962; `open_descriptor` 2083-2111. Visibility: `channel_file_media` `pub(super)`; the seven methods `pub(super)`.
2. `agent/page.rs`: `enqueue`, `take_queued`, `cache_entry` 1234-1252; `complete_page` 1848-1904; `update_cache` 2042-2081. Visibility: all five `pub(super)`.
3. `agent/request.rs`: `refusal`, `blocked`, `peer_blocked` 1254-1283; `report_refusal` 1309-1315; `dispatch` 1317-1420; `start_exchange`, `write_request`, `send_request` 1422-1518. Visibility: all eight `pub(super)`.
4. `agent/fetch.rs`: 1520-1737. Visibility: `fetch_connected`, `fetch_closed`, `fetch_lost`, `fetch_received`, `abandon_fetch`, `fail_exchange`, `finish_purpose`, `report_exchange` `pub(super)`; `fetch_head_complete` stays private.
5. `agent/response.rs`: `complete` 1739-1846 (less the form arm, now `complete_form`), `redirect`, `redirect_keeps_channel` 1964-2040. Visibility: `complete` `pub(super)`.

What remains in `agent.rs`: 1-50, the private state types 594-751, `UserAgent` 753-807, `mod bound` and its stub 809-839, `event` 841-843, construction and accessors 954-1054, `handle` 1091-1172, the fetch half of `tick` 2673-2678 with a call to `push_tick`, `next_deadline` 2753-2763, and the `mod` and `pub use` lines: about 470 lines. It is over the 400 aim because the eleven state types (158 lines) stay beside the struct whose fields they are, so that no field of theirs needs `pub(super)` ("fields stay private", `00-conventions.md` section 6); the alternative, `agent/state.rs` with every field `pub(super)`, is the wider seam.

The `cfg(not(feature = "dbsc"))` stub `impl` 818-839 stays in the parent beside `mod bound`: it is the one case the convention allows of "one item with two forms" inside a shared file, and a `bound_stub.rs` would be a 22-line file of nothing.

The seam of steps 9 and 10 is about thirty `pub(super)` methods, listed above. It is wide, as a split of an 1,811-line `impl` into its lifecycle must be; each method is reached by one or two siblings along the request → fetch → response → purpose path, which is the order a reader follows. The browser's `impl Browser` across `browser/*_ui.rs` is the precedent `00-conventions.md` names.

### Step 11: the inline tests over 60 lines of the single-file modules

Moves: `user_agent.rs:186-264` to `user_agent/tests.rs`; `contents.rs:265-339` to `contents/tests.rs`; `channel.rs:268-348` to `channel/tests.rs`; `json.rs:495-576` to `json/tests.rs`; `sse.rs:313-409` to `sse/tests.rs`; `ws.rs:428-630` to `ws/tests.rs`. Each parent gains the `#[cfg(test)] #[allow(...)] mod tests;` declaration. `contents/tests.rs` and `user_agent/tests.rs` keep their `std` imports (`std::vec::Vec`, `std::format!`) as they are.

This is one commit: six moves of the same kind, no code touched. `json.rs` stays at 495 lines of code, under the ceiling; `ws.rs` at 430.

### Step 12 (optional): `ws.rs` into `ws/`

Moves: `new_key`, `accept_for`, `write_handshake_headers`, `check_handshake` 51-103 to `ws/handshake.rs`; `write_frame`, `write_frame_with_mask`, `write_close` 105-153 to `ws/frame.rs`; `ReadState`, `FrameReader` 175-426 to `ws/reader.rs`; the parent keeps `WsError`, `HandshakeKey`, `WsMessage` and re-exports. The children are 55, 50 and 255 lines. Optional because after step 11 `ws.rs` is 430 lines of three concepts that the RFC itself presents as one (its sections 4 and 5), under the ceiling; do it if the three-way reading proves easier, skip it otherwise.

## 5. Risks particular to this crate

| Risk | How the steps meet it |
|---|---|
| A `cfg!`-tested feature (`push`, `forms`, `cookies`) needs its functions present in every build; a function moved into a feature-gated file disappears from the no-feature build and the `cfg!`-guarded call site fails to compile | No file of `agent/` is feature-gated except `bound.rs` (already). `push.rs`, `form.rs`, `cookies.rs` compile in every build and keep their `cfg!` tests inside functions; `cargo xtask features` and the `--no-default-features` test run are in every step's gate. |
| A `Debug` supertrait or derive on anything reachable through `dyn` brings `core::fmt` and its `assert_eq!` into the bare-metal image | The baseline removed the two supertraits and the derive. No new file adds `derive(Debug)` to `UserAgent`, `Cookies`, `DeviceKeys` or any type they hold through a trait object; the private state types keep their derives (they are never behind `dyn`). `cargo xtask size --target x86_64-unknown-none` after steps 4, 5, 7, 8, 9 and 10 guards it: the check reports any `core::panicking` or `_fail` symbol. |
| The `error-trait` and `std` builds are in neither `check.sh fast` nor `cargo xtask features` | Both builds are in every step's gate list above; `lib.rs`'s `error_trait!` names only paths this plan keeps. |
| `pub(super)` widens reach: `cookie/`, `descriptor/`, `zxnet/` and `agent/` children can call each other's `pub(super)` methods | Each step lists its `pub(super)` items; fields nowhere change visibility, because every struct stays in the parent of the children that implement it; the arena index fields of `CookieJar`, `Descriptor` and the agent's state are read only through the existing methods (`parts`, `alias_target`, `service_address`). |
| Pedantic lints with warnings as errors: `too_many_lines` (100 code lines), `module_inception`, `missing_docs`, `unused_qualifications` | `complete` loses its form arm (step 9) and drops well under the limit; `dispatch`, `store_within`, `parse_with` move unchanged and stay as near the limit as today (a later, non-structural change may split them). No child is named after its parent (`cookie/store.rs`, not `cookie/cookie.rs`). Doc comments move with their items. `use` lines in new files name each item once, and `crate::consts::X` paths that the moved code wrote in full are left as written (a `use` is added only where the file already imports from that module). |
| The four `copy_from_slice` sites (`base64.rs:120`, `zxnet.rs:466`, 548, 591) are latent `len_mismatch_fail` paths that the symbol check would report the day they become reachable from the agent | They are moved as they are (steps 7 and none for `base64`), because changing them to `bytes::copy_prefix` is a behaviour-neutral but non-structural edit; listed in section 6. |
| `check-constants` and `check-io` walk every `.rs` under `crates/`, so a new file is covered without registration; but a test file moved out of a source file is no longer skipped as test code unless its `mod tests;` declaration is under `#[cfg(test)]` | Every `tests.rs` is declared `#[cfg(test)] mod tests;`; `xtask`'s `non_test_source` skips the inline module by its `#[cfg(test)]`, and a separate `tests.rs` file is scanned whole, so the watched teletext literals (`check-constants`) must not appear in it: none of the moved tests writes one (they use `PageAddress::from_mpp(0x100)` and the like, which are not in the watched list; checked at the first commit of step 11 by the gate itself). |
| `docs/traceability.md` names source paths | Regenerated in each moving commit (`cargo xtask traceability`); the engine's `ARCHITECTURE.md` L7 bullet names `contents`, `channel`, `dbsc` and `agent::bound`, all unchanged paths, so it needs no edit until phase E5's pass over the documents. |

## 6. Seen, not part of this plan

- **Definitions repeated across files** (section 2, shapes 1 to 8, 12 to 14): three `tchar`s (`user_agent.rs:81`, `http/head.rs:209`, `dbsc.rs:240`); two `hex_value`s (`bytes.rs:256`, `sha256.rs:177`) and five rewritten hex folds; two decimal writers (`bytes.rs:115`, `proxy.rs:112`); two base64 encoders (`base64.rs:41`, `dbsc.rs:675`); three case-insensitive host-suffix matchers (`dbsc.rs:797`, `dbsc.rs:848`, `proxy.rs:76`); seven printable-ASCII predicates; the `name=value` split written twice in `cookie.rs` (437, 831) where `bytes::split_once` exists; the `too_long` closure in four files. Each is a candidate for one definition in `bytes.rs` or `base64.rs`; a definitional change, not a move, so it is left to the owner.
- **`copy_from_slice` against `bytes.rs:104-106`'s own rule** at `base64.rs:120`, `zxnet.rs:466`, `548`, `591` (REQ-GEN-019). `copy_prefix` replaces each in a one-line change; the first is reachable from `zxnet::Channel::from_identifier` and the feed, the other three from the feed only, so no linked image shows them today.
- **The two L8 traits outside `port.rs`**: `cookie::Cookies` and `dbsc::DeviceKeys` are port contracts (`ARCHITECTURE.md` L8 names `CookieStorage` and `DeviceKeys`). Moving them to `port.rs` with `pub use crate::port::Cookies;` left in `cookie` would keep the paths, but it moves a public item's home and the rule the baseline learnt ("a port trait has no supertrait that brings `core::fmt`") belongs in `port.rs`'s documentation either way.
- **`lib.rs`'s `error_trait!` list** covers nine of the crate's twenty error types; the other eleven have no `Error` impl under the feature.
- **`sha256.rs`** has no caller in the crate since decision E.111 withdrew fonts by digest; its callers are `xtask`'s font checks. Whether it belongs in the web crate is a question for `13-engine-app-cli-audio-input.md`'s xtask section.
- **Limits in nine places** (section 2, `consts.rs` row): every limit is named and cited, but REQ-GEN-014's "defined once" is met per constant, not per module; a reader wanting all of a protocol's limits looks in two files.
- **`TECH-DEBT.md:177`** lists `Input::FetchContents` and the `Contents*` events as engine pieces with no caller; the moves carry them (`agent/service.rs`) unchanged.
- **The `Debug` derives on the agent's private state types** (`Exchange`, `FetchConnection`, `PushConnection` and the rest) survive the baseline because nothing formats them; they cost nothing in the image today but are the kind of derive the symbol check would catch if one were ever reached through a trait object.
