# Security review: consolidated fix plan

Written 24 October 2026 from three review reports in this folder:

- **A1**: `A1-threat-model-review.md`, threat-model review (ids H-n, M-n, L-n);
- **A3**: `A3-unsafe-supplychain-diff-review.md`, unsafe code, supply chain and diff review (ids Hn, Mn, Ln, In);
- **A4**: `A4-adversarial-input-review.md`, adversarial input and conformance review (ids Wn for the engine, Bn for the browser).

The fourth report, `A2-tool-driven-review.md`, did not exist when this plan was written. Its working folder `A2/` holds two fuzz crash folders (`crashes/tti_enhancement`, `crashes/bookmarks_file`). Those must be merged here once the report is written. Nothing in this plan accounts for them.

Reviewed commits: engine `implementation` at **e7d8927**; the browser pins fb2dd8a, whose only difference is three `no_std` `Debug` removals. Browser `main` is at **494aa91**. Every location below gives the line *at those commits*, together with the function, type or constant, because the restructuring branches (`structure/core`, `structure/interface-core`, `structure/protocol`, `structure/sandbox`) move files now. Browser paths are relative to `native/` unless they start with `docs/` or `scripts/`. Engine paths start with `crates/`.

I re-read these against the code at the reviewed commits, read-only: `families`, `network_namespace`, `landlock`, `seccomp` and `apply` (confine Linux); seccompiler 0.5.0's `build_arch_validation_sequence` (it has no x32 check); `read_for_core`, `SECRET_FOLDERS` and `Source::read`; `Launcher::prepare`, `candidates`, `accept`, `copy_in` and `tidy`; `update::accept::accept`, `complete` and `own_files`; the Windows `spawn` interface branch; `cookie_control` `ReachedQuestion`; `decoder_ended`; the `mpsc::channel()` in `run`; `phone_panel` and `phone_said`; `Frames::accept`; `links::Channel::own_page`; the macOS `preamble` and `profile` (applied through `/usr/bin/sandbox-exec`); `ENVIRONMENT_WINDOW`; and engine `push_head_complete` (passes `None` as the cookie scope). Every one matches what the reports say, except `own_page`, which is probably a false positive (F-86).

Platforms, used throughout:

- **macOS**: this machine.
- **Linux**: the host `foundintelquiet4060` (`NEOTELETEXT_LINUX_HOST`).
- **Windows (by hand)**: only the owner's virtual machine. A Windows-only check cannot be done autonomously. Its fix is marked "implement, verify by hand on Windows", with the check the owner must make.

Every regression test named here must fail on the code at the reviewed commits, and the engineer confirms that it does (the owner's rule). Where a test cannot fail on old code on some host, the finding says so.

---

## 1. Findings, deduplicated

Severity is the highest any report gave; changes are noted in the Defect column. "Browser not affected" means the engine defect does not reach the browser as built (its features or its own core's rules stop it); the engine is still fixed.

After deduplication: **4 High, 22 Medium, 56 Low, 18 Info: 100 findings.**

### High

| Id | Sev | Repo / crate | Items and file:line | Sources | Defect | Fix |
|---|---|---|---|---|---|---|
| F-01 | High | browser / confine | `families` linux.rs:50-61; `network_namespace` linux.rs:73-96; `landlock` linux.rs:146-175; `apply` linux.rs:308-311; `INTERFACE_PATHS`, `SOUND_PATHS` linux.rs:36,44; `ENVIRONMENT_WINDOW` lib.rs:246-265 | A1 H-1; A3 H1; A3 L9 (subsumed) | On Linux the fetcher, keyboard, updater, interface and sound helper may `connect()` by path to any `AF_UNIX` socket, including the session D-Bus (where systemd's `StartTransientUnit` runs any program unconfined), the system bus, ssh-agent and gpg-agent. | Network and updater roles lose `AF_UNIX`, and netlink is held to `NETLINK_ROUTE`. The interface and sound helper get a mount namespace with `/run` and `/tmp` covered by tmpfs, and only their own sockets bound back. `DBUS_SESSION_BUS_ADDRESS` goes from the interface's environment. Seccomp also denies `pidfd_getfd`. |
| F-02 | High (Linux), Medium (macOS) | browser / launcher, update | `Launcher::accept` lib.rs:332-345 (Linux branch `rename`); `Launcher::tidy` lib.rs:385-391; `files::list_files` files.rs:174-190; `accept::accept` accept.rs:111-114; `install::launcher_release` install.rs:27-65 | A1 H-2; A3 H2; A4 B1 | The Linux launcher verifies a staged version in place and then renames the *same* inodes (or a symlinked root) into `versions/`. A confined updater can still write them afterwards, through a hard link in `staging/metadata`, a write descriptor it kept open, or a root that is a symlink. That gives it a persistent, unconfined broker or launcher. | On Linux and macOS, copy the staged version as Windows already does (`copy_in`): copy into a launcher-only folder, accept the copy, then rename or exchange the copy. Refuse a staged root that is a symlink, and keep only tough's own files under `staging/metadata`. |
| F-03 | High | browser / core (broker side) | `read_for_core` main.rs:2397-2407; `SECRET_FOLDERS` main.rs:2359-2362; `Source::read` source.rs:36-69; `import_bookmarks` library.rs:587-616 | A3 H3; A1 M-1 (parts 1-2); A1 L-2; A3 I13 (import oracle); A4 browser info (import) | The broker reads any path for a compromised core. It checks a short deny-list once on the canonical path and then opens by path again, following symbolic links inside a folder channel. So a link the core makes in its settings folder reads `~/.ssh/id_*`, and `~/.netrc`, browser profiles and the rest are not denied at all. | Descriptor-based, link-refusing opens; the browser's own folders, every dot-entry under home and the platform's application-data folders refused; only bytes the engine's `detect` recognises as teletext (or a bookmarks file's fixed first line) returned; a fixed refusal sentence. |
| F-04 | High | browser / confine (Windows) | `spawn` windows.rs:642-646 (the `Role::Interface` branch); `restricted_token` windows.rs:341-369 | A3 H4 | On Windows the interface runs under a restricted low-integrity token with no AppContainer. Low integrity does not stop Winsock, so a compromised interface can read the user's files and send them out, against `sandboxing.md` ("no network"). | Run the interface in an AppContainer with no capabilities, as every other role is. Implement, verify by hand on Windows. |

### Medium

| Id | Sev | Repo / crate | Items and file:line | Sources | Defect | Fix |
|---|---|---|---|---|---|---|
| F-05 | Medium | browser / confine | `profile` `Role::Network` macos.rs:55-61; `landlock` linux.rs:150-152; `apply` linux.rs:308; engine `fetch_connected`/`peer_blocked` agent.rs:1527-1538 | A1 M-2 | On macOS and Linux nothing outside the fetcher's own in-process engine check keeps a compromised fetcher or keyboard off loopback and the LAN (requirement 5.10, engine REQ-SEC-006). | macOS: deny loopback in the profile when `local_network` is false. Linux: the residual is documented, and connecting through the broker is recorded as the planned design (D-4). |
| F-06 | Medium | browser / tuf updater | `Config::load` tuf/updater/src/lib.rs:115-125; `TUF_ROOT` use main.rs:59-66 | A1 M-3 | The TUF client starts from the built-in root every time and keeps no floor on the highest root version it has reached, so a host that withholds newer root files rolls the client back to rotated-away keys. | Keep a `root-version` floor in the updater's metadata folder; refuse a lower loaded root; raise it after success. |
| F-07 | Medium | browser / update, os-install, release | `WindowsSigner::check` os-install/src/windows.rs:142-149 (ignores `_manifest`); `accept::accept` accept.rs:100-109; `own_files` accept.rs | A1 M-4 | On Windows no signature covers the manifest. Programs that the pinned key signed for different releases can be combined under a new version number. | Sign the Windows manifest with the release Ed25519 key, as Linux does (`manifest.sig`), and verify it in `accept` before the platform check. |
| F-08 | Medium | browser / launcher | `Launcher::prepare` lib.rs:267-281 (`state.mark_bad(candidate)` on refusal); `candidates` lib.rs:300-316; `State::mark_bad` update/src/state.rs; `offer` core/src/updates.rs:299-303 | A1 M-5; A4 B2; A4 info (already-staged shortcut) | Any folder under `staging/` whose name parses as a version marks that version bad for good when it is refused. One `mkdir` by a compromised updater freezes genuine updates, and junk can evict a genuinely bad version from `MAX_BAD`. | On refusal, delete the folder and leave `bad` alone; `bad` is only for trials that failed. Examine at most a named number of candidates per start. |
| F-09 | Medium | browser / launcher, update, core | `HEALTH_DEADLINE` launcher/src/lib.rs:64; `start::start` start.rs:53-67; `Launcher::run` lib.rs:178-182; `prepare` lib.rs:287-292; `HEALTH_WINDOW`, `Health::healthy` core/src/updates.rs:30,106-112; test `a_broken_version_is_rolled_back_after_two_starts` launcher/tests/launcher.rs:241 | A1 M-6 (and its "Health deadline" section) | The deadline runs from spawn, on a different clock from the core's 30 s window. A start killed by the deadline, or a quick clean quit, counts as a failed trial. So a slow machine rolls back a good version, marks it bad, and never offers it again; the flaky test is the same effect. | A `started` line from the broker; a start deadline then a health deadline counted from `started`; trials counted only after `started`; one source for both time constants; test asserts on the state. |
| F-10 | Medium | browser / core | `run` main.rs:2243 `mpsc::channel()`; reader threads in `start_decoder` (~183-197), `start_fetcher` (~252-266), sound, phone, interface | A1 M-7 | The trusted core's inbound event queue is unbounded, so one compromised helper writing faster than the core handles messages grows the core's memory until the browser ends. | A per-sender byte budget. The reader thread blocks (back-pressure on that helper's pipe alone) while its queued bytes are over `outbox::MAX_QUEUED_BYTES`. |
| F-11 | Medium | browser / core | `Frames::accept` frames.rs:43-55; frame queueing main.rs:1241-1262; `flush` main.rs:1428; outbox outbox.rs:139-150 | A1 M-8 | No per-page frame-rate bound. A decoder alternating two images fills the interface outbox past 16 MB, and that ends the browser. | Hold the newest frame per page key and send at most one per named minimum interval derived from EN 300 706's fastest legitimate change. |
| F-12 | Medium | browser / core | `decoder_ended` main.rs:1177-1196 (only `reason.is_some()` counts; comment 1184-1185 wrong); `Event::FetcherEnded` main.rs:2182-2193; decoder exit decoder/src/main.rs:261-266 | A1 M-9 | A decoder or fetcher that exits at start (for example one that cannot confine itself) is not counted against the trial's health, so a broken release commits. | An unrequested end of a decoder or fetcher before its first message calls `updates.helper_failed`. |
| F-13 | Medium | engine / neoteletext-web | `CookieJar::import_one` cookie.rs:722 (`checked_sub(now)?`), 735 (`built.ok()?`), 723-737 (path rebuilt into `Path=`); `CookieJar::import` cookie.rs:686-688 (`break`); `MAX_COOKIE_ATTRIBUTE_VALUE` cookie.rs:839; browser `Store::import` core/src/cookies.rs:424 | A1 M-10; A4 W3 | The first expired or over-long record ends the whole import, so every later cookie is lost. A saved path over 1024 bytes is dropped by the attribute limit, and the cookie comes back as `Path=/`. | Consume every record and skip a bad one. Store the path through a path-taking internal call, not a rebuilt `Path=` attribute. The browser logs when fewer records were restored. |
| F-14 | Medium (browser not affected: `dbsc` off) | engine / neoteletext-web | `write_headers` agent/bound.rs:141; `sf_string` bound.rs:84-95; `read_instructions`/`text` dbsc.rs:431-444,518 | A1 M-11; A3 I1 (first item) | A server's DBSC `session_identifier` can hold CR, LF or NUL and is written into `Sec-Secure-Session-Id` unescaped: header injection and request smuggling on the kept-alive connection. | Refuse any identifier byte outside `0x21..=0x7E` when reading the instructions; `sf_string` returns `Overflow` for any byte outside `0x20..=0x7E`. |
| F-15 | Medium (browser not affected: its core re-scopes) | engine / neoteletext-web | `push_head_complete` agent.rs:2461-2471 (scope `None`); fetch path agent.rs:1658 | A1 M-12; A4 W1 (probe A) | Cookies set by a channel's push handshake are stored without the channel's folder scope, so `Path=/` reaches every other channel on the host (REQ-WEB-026). | Pass `self.channel.as_ref().map(Url::path)`, as the fetch path does. |
| F-16 | Medium (reaches the browser) | engine / neoteletext-web | `redirect` agent.rs:1967-2027 (forms keep method and body on 307/308; only rule `Site` → `CrossOriginForm` at 2008-2019); `submit` agent.rs:2185-2200; `form::destination` agent.rs:2133 | A4 W2 (probe E); A1 L-19 | A form POST to a permitted origin that answers 307 or 308 is re-sent to a third origin with the viewer's values and `ttx_token`, with no allow-list check and no first-submission confirmation (REQ-WEB-008, REQ-SEC-009). | Refuse a 307 or 308 redirect of a form to any origin other than the submission's own target (`FormRefused::Origin`). |
| F-17 | Medium | engine / neoteletext-web | `peer_blocked` agent.rs:1281 (false with a proxy); `hidden_local` proxy.rs:71-81 | A3 M7 | With a proxy set, the local-network rule is applied by name only, so `router`, `nas.lan` and `x.home.arpa` reach the LAN through a LAN proxy. | Widen `hidden_local` to single-label names and the private-use suffixes; document that through a proxy the rule is by name. |
| F-18 | Medium (documentation only) | browser / docs | `docs/interaction-security.md:88-89` ("A hostile relay reads keys: it cannot"); engine `screen.rs:174` (QR address is `{origin}/app#…`) | A1 M-13 | The relay serves the phone's own code, so its operator, or anyone who compromises its server, can read the PIN and the keys. The document claims otherwise. | Reword the row to "a passive relay or network observer"; add a row saying the relay serves the phone's code; rank it in §7 (D-11). |
| F-19 | Medium (A1: "Medium-low") | browser / launcher (macOS) | `holds_old_current` launcher/src/macos.rs:78-82; `move_old_current` macos.rs:86-104; `reconcile` macos.rs:45-63 | A1 M-14 | macOS fills `previous/` from any staging entry carrying the current version's mark, and a rollback exchanges it in with no signature check. | `reconcile` runs `MacosSigner::check` and the mark check on the bundle it is about to exchange in; `move_old_current` considers only the trial's own folder. |
| F-20 | Medium | browser / core, interface | `phone_said` core/src/main.rs:1878-1883; `phone_key` interface/src/main.rs:915-948; `link_ui` interface-core/src/browser/link_ui.rs:196-212 | A3 M1 | Phone keys reach the browser's own controls when no page is open for typing. A compromised keyboard process can type an address, change the proxy, or Tab to Go and confirm a web hand-off or site change. | The core forwards only page-navigation keys when no page is open for typing. The interface routes phone keys to the page view only, never to a focused field, prompt or panel. |
| F-21 | Medium | browser / confine | `seccomp` linux.rs:211-300 (`SeccompAction::Allow` as mismatch action, line 288); seccompiler 0.5.0 `build_arch_validation_sequence` | A3 M2 | The seccomp deny-list has no x32 check, so on a kernel with x32 enabled every denied call (`execve`, `bpf`, `io_uring_setup` and the rest) passes under its x32 number. | A third, raw filter on x86-64 returns EPERM for any number with `__X32_SYSCALL_BIT` set. |
| F-22 | Medium | browser / confine | `seccomp` linux.rs (no `ioctl` rule); standard error inherited by `start_core` broker.rs and helpers lib.rs:386 | A3 M3 | A helper started from a terminal shares it as standard error, and `ioctl(2, TIOCSTI)` can queue commands in the user's shell; `TIOCLINUX` does the same on a virtual console. | A seccomp rule returning EPERM for `ioctl` with request `TIOCSTI` or `TIOCLINUX`, in every role. Windows console reach is to be checked by hand. |
| F-23 | Medium | browser / tuf release, launcher | AppArmor profile text tuf/release/src/package.rs:64-75; printed by launcher/src/unix.rs:146-155 | A3 M4; A1 info (`XDG_DATA_HOME` not covered) | The profile an administrator is asked to install gives `userns` to any program at a glob under `~/.local/share`, a path every user writes. That undoes Ubuntu's restriction on unprivileged user namespaces for any program dropped there, and misses an `XDG_DATA_HOME` installation. | Narrow the profile to the exact programs that make namespaces, at the real installation root; document the remaining weakening as a residual (D-10). |
| F-24 | Medium | browser / release-identity, tuf release, scripts/release | `build.rs` release-identity/build.rs:49-66; `scripts/release/build-linux.sh:16`; `check` tuf/release/src/main.rs:114 and package.rs:165-183; `publish.sh` | A3 M5; A1 L-26 | Nothing stops a release being built and published with a test identity (test TLS root, test TUF root, test keys), even an empty variable, so whoever holds the test keys could push updates to that build's users. | An empty variable is unset; release scripts and `check`, `sign-linux` and `publish` refuse a non-production identity, or `file:` keys with production, unless `--test-identity` is given. |
| F-25 | Medium | browser / installer, stub, launcher (Windows) | installer/src/main.rs (no `SetDefaultDllDirectories`, no `/DEPENDENTLOADFLAG`); static imports of `wintrust.dll` and `crypt32.dll` through os-install | A3 M6 | A `wintrust.dll` planted beside `NeoTeletext-Setup.exe` in Downloads is loaded by the installer (CWE-427). | Link with `/DEPENDENTLOADFLAG:0x800` and call `SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32)` first in `main`. Implement, verify by hand on Windows. |
| F-26 | Medium | browser / core, keyboard | `phone_panel` core/src/main.rs:1806-1812 (`child.wait()` on the event thread); keyboard/src/keyboard.rs:48-61 (`Screen::create` before the stdin watcher) | A4 B3 | Closing the phone panel waits for the keyboard helper on the trusted core's one thread while the helper is still blocked connecting to the relay. Every tab freezes for the relay's timeouts, without bound against a trickling relay. | The core never waits on the event thread (it reaps on the helper's end event and kills after a named grace). The helper watches stdin before connecting. |

### Low

| Id | Sev | Repo / crate | Items and file:line | Sources | Defect | Fix |
|---|---|---|---|---|---|---|
| F-27 | Low | browser / core | `cookie_reply` `ReachedQuestion` cookie_control.rs:117-120; `reached_securely` cookies.rs:256-261 | A1 L-1; A3 L11; A4 B6 | Any fetcher learns, for any host and across the private and ordinary jars, whether that host was reached securely. | Answer only for the asking channel's host, from the asking tab's jar. |
| F-28 | Low | browser / protocol | `clean_name` protocol/src/keyboard.rs:134-137; forwarding core/src/main.rs:1878-1880 | A1 L-3; A4 B4 (probe) | A phone key name with a zero-width or bidi character passes `clean_name` but fails `push_text` on the way to the interface, which ends the browser. | `clean_name` refuses everything `is_clean` refuses, so only the keyboard pipe ends. |
| F-29 | Low | browser / protocol | `Fields::key` protocol/src/lib.rs:685-692; `write_to_decoder(Showing)` | A1 L-4 | Page keys 0x100..=0x8FF are accepted with hexadecimal page numbers that `page_index` refuses. The decoder then refuses the `Showing`, restarts, and fails health. | Validate with `page_index`; bound `Showing`'s count to `PAGES`. |
| F-30 | Low | browser / core | `flush` main.rs:1408-1432; `match_decoders` sleep.rs:54-59,102 | A1 L-5 | A decoder that overflows its outbox is killed and replaced at once with no back-off, for as long as its fetcher keeps sending. | A channel whose decoder is replaced more than a named count in a named window is marked failed until reloaded. |
| F-31 | Low | browser / core | `dropped` lists: history.rs:167-175, restore.rs:248-250, bookmarks.rs:164-166, settings.rs:207-209, cookies.rs:416 | A1 L-6; A4 B8 | One `String` and one `eprintln!` per refused line: a large malformed file costs gigabytes before the window opens. | Keep the first 64 messages and a count; skip empty lines. |
| F-32 | Low (documentation only) | browser / docs | cookie key `Copy` array: cookie_control.rs:40,162, cookies.rs:454, main.rs:2380-2392, broker.rs:413-418 | A1 L-7 | The documents say the cookie key is wiped at exit; it is a `Copy` array copied and never cleared. | Amend `cookies.md` and `cookies-security.md` to say what is built (D-14). |
| F-33 | Low | browser / core | `Store::import` cookies.rs:407-437 | A1 L-8 | Channel lines are keyed by tag only: one channel key under two tags survives deletion and blocking, and the file's tags are merged without being remapped. | Refuse a channel line whose key was already read; assign fresh tags on import. |
| F-34 | Low | browser / confine, launcher | `apply` confine linux.rs; `serve` broker.rs:838-841; `end_whole` launcher/src/start.rs:86-94 | A1 L-9 | Helpers are killed only when `serve` returns normally; with no parent-death signal they outlive a crashed broker. | `PR_SET_PDEATHSIG(SIGKILL)` in Linux `apply`; the launcher kills the process group after every broker exit. |
| F-35 | Low | browser / core | private writer history.rs:424,466-475 (moved by `structure/core`), settings.rs:321-335, main.rs:2415 | A1 L-10 | Temporary files are opened `create+truncate` (a link is followed); `0o600` only on new files; the folder is made 0755. | `remove_file` then `create_new` with `O_NOFOLLOW`; folder `0o700`; set `0o600` on existing files. |
| F-36 | Low | browser / interface-core | `hidden` interface-core/src/editor.rs:12-21 | A1 L-11; A4 browser info | The hidden-character set misses U+00AD, U+034F, the Hangul fillers, U+180E, U+2028/2029, U+206A-206F, the variation selectors, the tag characters and others; runs of combining marks are unbounded. Display only. | Refuse the format and separator categories, the variation selectors and the fillers; bound consecutive combining marks. |
| F-37 | Low | browser / dock-menu | crate root dock-menu/src/lib.rs; `tag += 1` mac.rs:191 | A1 L-12 | `dock-menu` lacks the no-panic deny list that the other crates reading pipe input carry, and has one bare increment. | Add the same `#![deny(...)]` block; `saturating_add`. |
| F-38 | Low | engine / neoteletext-qrkeyboard | `FromPhone::Up` screen.rs:467-471; browser keyboard.rs:96 | A1 L-13 | A release is passed for any key in the layout, held or not, and releases are not rate-limited. | Pass `Up` only for a key in `self.held`. |
| F-39 | Low | engine / neoteletext-qrkeyboard | owner token screen.rs:152-156; net.rs:219-221 | A1 L-14 | The relay-supplied owner token is checked only for length before it is written into `Authorization: Bearer`. | Restrict it to `message::is_id`'s alphabet. |
| F-40 | Low | browser / keyboard | error line keyboard/src/keyboard.rs:164 (engine net.rs:111-117 text) | A1 L-15 | The keyboard's one stderr line includes rustls's error text, which can carry names from a presented certificate. | Map TLS errors to a fixed sentence before printing. |
| F-41 | Low | browser / web-opener | `acceptable` web-opener/src/lib.rs:60-63 | A1 L-16 | The address may contain `' ; & $ ( ) * ? [ ] ~ !`: safe with today's shell-free openers, fragile with `xdg-open` and `$BROWSER`. | Percent-encode those sub-delimiters in the re-serialised address. |
| F-42 | Low | engine / neoteletext-web | fetch cookie scope agent.rs:1658 | A1 L-17 | The channel-folder scope is applied even to responses from outside the channel (a permitted form target; a same-origin redirect in `neottx`). | Scope only when `channel::is_inside(folder, &exchange.url)`; do not store cookies from outside. |
| F-43 | Low | engine / neoteletext-web | `remember_secure` agent.rs:1303-1310; `SECURE_HOSTS` consts.rs:488 | A1 L-18 | The 32-host secure-host memory fills silently; after that the no-downgrade rule holds only for hosts with a live secure cookie. | Evict the least recently seen host. |
| F-44 | Low | engine / neoteletext-web | `redirect` agent.rs:1973-1987, 2020-2026; `TextBuf::as_str` bytes.rs:188-190 | A4 W4 (probe B); A1 L-20 | An empty or non-UTF-8 `Location` resolves to the request's own address: six requests for one fetch, outside the fetch interval. | `Failure::BadRedirect` for an empty, non-UTF-8 or same-address `Location`. |
| F-45 | Low | engine / neoteletext-web | `is_inside`, `redirect_keeps_channel` channel.rs:210-228 | A1 L-21 | A path-prefix test: percent-encoded dot segments and slashes after the folder pass. | Refuse `%2E`, `%2F` and `%5C` (either case) after the folder. |
| F-46 | Low | engine / neoteletext-core | blocked ranges, `ipv6_blocked` policy.rs:34-45 | A1 L-22; A3 L14 | Not blocked: `::a.b.c.d`, NAT64 `64:ff9b::/96` and `64:ff9b:1::/48` with private IPv4 inside, `fec0::/10`, `192.0.0.0/24`, `198.18.0.0/15`; 6to4 is not treated by its embedded address. | Block them; apply the IPv4 rule to embedded addresses. |
| F-47 | Low | browser / launcher | health line reader start.rs:44-50 | A1 L-23 | `take(MAX_LINE)` is renewed per read, so `healthy\n` after 64 other bytes on the same line matches. | Accept a line only when the previous read ended in `\n`. |
| F-48 | Low | browser / launcher | `--uninstall` launcher/src/unix.rs:168-192; update/src/layout.rs:99 | A1 L-24 | Removes the folder two levels above the binary without checking that it is an installation. | Require the state file or installed launcher (Linux) or a bundle path ending `NeoTeletext.app` (macOS) first. |
| F-49 | Low | browser / tuf updater | `latest_known_time.json` (tough datastore.rs:88-119) | A1 L-25 | One forward jump of the clock leaves "Updates unavailable" for good. | Report `SystemTimeSteppedBackward` distinctly; remove the file when it is ahead of now by more than a named bound. |
| F-50 | Low | browser / update | `copy_tree` update/src/files.rs:124-140 | A1 L-27 | Takes the type from the directory entry, then reads by path (a race), and has no size bound. With F-02 this is used on every platform. | Copy only the manifest's files, each at most its manifest length; on Windows open with `FILE_FLAG_OPEN_REPARSE_POINT` and check the handle. |
| F-51 | Low | browser / confine (macOS) | `preamble` macos.rs:22-33; `profile` macos.rs:126,134,140 | A1 L-28; A3 L6 | Paths are put into SBPL string literals without escaping, so a bundle in a folder named `x")(allow default)("` gets an unconfined profile. | Pass every path as an `sandbox-exec -D` parameter and use `(param "…")` (D-12). |
| F-52 | Low | browser / confine (macOS) | `SYSTEM_READS` macos.rs:42-45; interface profile macos.rs:73-93 | A1 L-29; A3 L8 | The interface and sound helper may read all of `/private/var/folders` (every application's per-user caches); the interface may reach `launchservicesd` (perhaps opening URLs, a network-equivalent channel) and the pasteboard at any time. | Narrow to this program's own `DARWIN_USER_CACHE_DIR` and `DARWIN_USER_TEMP_DIR`, measured as before; probe `LSOpenCFURLRef` and deny it if it works. |
| F-53 | Low | browser / core | `kept_address` restore.rs:159; session.rs:55-58,801; address.rs | A1 L-30 | `file:` addresses are restored and accepted from imported bookmarks, and up to 64 restored file tabs are read through the broker at start. | Read a file tab only when it is first shown; drop `file:` addresses from other browsers' bookmark files. |
| F-54 | Low | browser / interface | paste interface/src/main.rs:757-760 | A1 L-31 | The whole clipboard is read before it is cut to `MAX_PASTE`. | Cut on a character boundary at `MAX_PASTE` immediately after `get_text()`. |
| F-55 | Low | browser / sound | mixer per channel sound/src/audio.rs:178-181 | A1 L-32 | Any operation on an unknown channel makes a mixer, and `Define` allocates under the lock the audio callback takes. | Make a mixer only on `Define` or `Stream`; allocate outside the lock and swap it in. |
| F-56 | Low | browser / confine | `send`, `receive` unix.rs:41,85 (`[u8; CONTROL_BYTES]`) | A3 L1 | The control buffer has alignment 1 and is cast to `cmsghdr` (alignment 8 or 4): undefined behaviour. | A `#[repr(C, align(8))]` buffer type, and a const assertion of its size against `CMSG_SPACE`. |
| F-57 | Low | browser / confine (macOS) | `receive` unix.rs:114-132 | A3 L2 | On macOS the descriptor loop trusts `cmsg_len` without clamping it to `msg_controllen`, does not check `MSG_CTRUNC` first, and leaves the `fcntl(FD_CLOEXEC)` result unchecked. Defence in depth: only the broker sends. | Check `MSG_CTRUNC` before wrapping; clamp; check `fcntl`. |
| F-58 | Low | browser / confine (Windows) | `environment_block` windows.rs:267-277 | A3 L3 | An empty environment gives a one-NUL block, so `CreateProcess` reads past it (reachable in a test only). | Push an extra NUL when the environment is empty. |
| F-59 | Low | browser / confine (Windows) | attribute list storage windows.rs:405 (`Vec<u8>`) | A3 L4 | `PROC_THREAD_ATTRIBUTE_LIST` is stored with alignment 1. | `Vec<u64>` of `size.div_ceil(8)`. |
| F-60 | Low | browser / confine | `seccomp` linux.rs (`kill`, `tkill`, `tgkill` allowed) | A3 L5 | A confined helper can signal any of the user's processes (SIGSTOP the broker, SIGKILL the editor). | Seccomp: signals only to its own process; `tkill`, `pidfd_open`, `pidfd_send_signal` denied (D-9). |
| F-61 | Low (from A1 M-1 part 3, Medium as a combination; see note) | browser / core (broker side) | `open_web` closure in `broker()` main.rs:2422-2426; `OpenWeb` broker.rs:886-889; `Spawn` broker.rs:849-866 | A3 L7; A1 M-1 (part 3) | The broker opens any http(s) address the core names, with no check of its own, and passes any fetcher argument: an exfiltration channel for a compromised core. | Broker-side rate limit on `OpenWeb`; no argument validation (it would not close the channel, D-3). Residual documented. |
| F-62 | Low | browser / fetcher | `reach`, transport.rs:183-219 | A3 L10; A4 browser info | A name that resolves (or rebinds) to loopback or the LAN receives the TCP handshake and a ClientHello with an attacker-chosen SNI before the engine refuses the peer. | Check each resolved address with the engine's `is_blocked` in `reach()` before connecting, unless local access is allowed. |
| F-63 | Low | browser / fetcher | transport.rs:167-180, 215-217, 375-382 (`Tcp::close`) | A3 L12; A4 B7 | The connecting thread has no overall deadline (DNS unbounded, 10 s per address, per-read TLS timeouts), and `close()` cannot cancel an open in progress, so threads and buffers pile up. | One deadline for the whole open; a cloned stream in `Link::Connecting`, so `close` can shut it. |
| F-64 | Low | browser / core, confine | phone keyboard spawn core/src/main.rs:1834 (`local_network = true`); `ENVIRONMENT_CORE` confine/src/lib.rs (passes `NEOTELETEXT_QRKEYBOARD_RELAY`) | A3 L13 | The phone keyboard always gets local-network access (on Windows the private-network capability), and the relay override is honoured in release builds, `http://` included. | Honour the relay variable, and grant local access, only in debug builds. |
| F-65 | Low | browser / core | `Asking` core/src/links.rs:714 | A3 L15 (iii) | The pending link question is global, not bound to a window and tab, so after a `From(B)` a `Confirm` raised in window A sends B's tab. | Store the window and tab with `Asking`; clear it on a window change. |
| F-66 | Low | browser / core | `opened` core/src/main.rs:1116-1127 | A3 L15 (ii) | The key is not filtered to the active channel, so `PageControl` reaches another tab's decoder. | Refuse a key whose channel is not the active one. |
| F-67 | Low | browser / core | `Opened(Some(key))` main.rs:993 | A3 L15 (i) | A page intent on a start-page bookmark navigates the tab (requirement 4.5). | Apply the requirement 4.5 rule to start-page bookmark intents. |
| F-68 | Low | browser / core | update-check setting main.rs:1753-1756 | A3 L15 (iv) | Turning off update checks is silent. | Log and show a notice when update checks are turned off. |
| F-69 | Low | browser / launcher | `install_linux` launcher/src/unix.rs:118-125 | A3 L16 | `--install` accepts, then copies, and does not check the copy. | Copy first, then accept the copy (the F-02 routine). |
| F-70 | Low (verify) | browser / confine (Windows) | `grant_to` windows.rs:540-585 | A3 L17 | `SetNamedSecurityInfoW` re-applies an inheritable ACE to the core's settings folder at every start; whether its propagation follows a junction made by the container is unmeasured. | Verify by hand on Windows; if it follows, grant with `SetSecurityInfo` on a handle with no propagation. |
| F-71 | Low | engine / neoteletext-qrkeyboard | "Phone connected" on first salt frame; `constant_time_equal` crypto.rs:151-153 | A3 L18 | "Connected" is reported before any frame authenticates, and the OR-fold comparison is not promised to stay constant-time. | Report connected after the first authenticated frame; use `subtle::ConstantTimeEq` (already in the lockfile). |
| F-72 | Low | browser / scripts | scripts/tools.sh | A3 L19 | Tools are pinned by version, not by hash. | Record each tool binary's SHA-256 at install and check it in `check.sh`. |
| F-73 | Low | browser / scripts/release | scripts/release/build-linux.sh:21; build-windows.ps1 | A3 L20 | `curl \| sh` for rustup, unpinned `dnf`, no clean-tree check (nor in `build-windows.ps1`), and the `file://` engine URL cannot be fetched in the container. | Pinned rustup-init by hash, pinned packages, clean-tree refusal, engine supplied as a vendored source. |
| F-74 | Low | browser / fetcher | fetcher `Config::default()` fetcher/src/main.rs:247; `>= MAX_PAYLOAD` protocol/src/fetcher.rs:334; assertion fetcher/src/main.rs:68 | A4 B5 (probe) | A body of exactly `DEFAULT_PAGE_LIMIT` (262,144) bytes is accepted by the engine and refused by the protocol writer, which ends that channel's fetcher. | `page_limit: protocol::MAX_PAYLOAD - 1` (by name) and a const assertion. |
| F-75 | Low | engine / neoteletext-web | `parse_head` http.rs:318-325; `fetch_head_complete` agent.rs:1668-1671 | A4 W5 (probe D) | Every 1xx other than 101 fails the exchange, so a server sending `103 Early Hints` is unusable (RFC 9110 §15.2.1 MUST). | Skip interim 1xx heads and keep reading. |
| F-76 | Low | engine / neoteletext-web | `SseParser::value_byte` sse.rs:249-255; `push_connected` agent.rs:2365-2368 | A4 W6 (probe G); A1 info | `Last-Event-ID` echoes C0, DEL and non-UTF-8 bytes, an invalid field value (RFC 9110 §5.5), so resumption fails against a strict intermediary. | Treat such an id as invalid, as NUL is. |
| F-77 | Low | engine / neoteletext-web | `push_events` agent.rs:2602-2605 | A4 W7 (probe G) | With `Content-Length` framing, the final body step's data is dropped before the SSE parser sees it. | Feed `step.data` first, then handle `done`. |
| F-78 | Low | browser / core | address.rs:42,163,207 (`with_page`) | A4 B9 | The canonical text can exceed `MAX_ADDRESS` after `https://`, `/` and `#NNN` are added, so a 2045-2048-byte address loses its visit, star and restored tab. | Bound the built text; make `with_page` fallible. |
| F-79 | Low | browser / core | bookmark undo bookmarks.rs:433-449, 457-487 | A4 B10 | Undo of a removed folder does not check depth, so the subtree is written past `MAX_DEPTH` and lost at the next read. | Check the subtree's height in `restore`. |
| F-80 | Low | browser / launcher | `read_state`, `recovered` lib.rs:204-227; `start` start.rs:36 | A4 B11; A1 info (`Chosen::Run` with missing version) | An unparsable state makes the newest complete version `current`, checked by hashes only and with no trial. A state over 2 KiB stops the browser starting. A missing `versions/<current>` fails hard. | Accept with the signer in `recovered`, and make the newest the trial; treat `InvalidData` as a refused parse; fall back to `recovered()` when `current` is missing. |
| F-81 | Low | browser / tuf updater | transport.rs:35,91-92,157 | A4 B12 | Every body is buffered up to 64 MiB + 64 KiB before tough's limits apply, with per-read timeouts only. | A size bound by request kind and a total deadline per request. |
| F-82 | Low (A3 rated Info; raised: breaks the owner's no-blanket-suppression rule and requirement 10.12's Verification) | browser / confine, os-install | `#![allow(clippy::undocumented_unsafe_blocks)]` confine/src/windows.rs:32-35, os-install/src/windows.rs:7-10 | A3 I9, I5 (part) | Module-wide suppression of `undocumented_unsafe_blocks`; its blanket justification is untrue for `GetStdHandle`, `duplicate_into` and `file_from_handle_value`. | Remove both allows; one `// SAFETY:` per block. |

### Info

| Id | Sev | Repo / crate | Items and file:line | Sources | Defect | Fix |
|---|---|---|---|---|---|---|
| F-83 | Info | browser / core | `TabToWindow` handling | A3 I13 | Tabs can be moved between private and ordinary windows. | Refuse `TabToWindow` across privacy kinds. |
| F-84 | Info | browser / core | browser-wide log lines main.rs:998, 2029 | A3 I13 | Browser-wide log lines disclose private-tab activity to every window's console. | Log a private tab's lines only in that window's console. |
| F-85 | Info | browser / core | `start_bookmark_reader` main.rs:204-232 | A3 I13 | The bookmark-import decoder has no deadline. | Kill it after a named deadline and report "Not imported". |
| F-86 | Info (probably a false positive) | browser / core | `Channel::own_page` links.rs:262-275 | A4 browser info | Reported as a prefix match with no path boundary. The remainder must be decimal digits plus a page-file extension, so a sibling folder cannot match if `channel_text()` ends in `/`. | Test only: assert that `channel_text()` ends in `/` and that `/a` does not own `/a302.tti`. |
| F-87 | Info (functional) | browser / tuf updater | `proxy.open_tunnel` tuf/updater/src/transport.rs (~97) | A3 I8 | Bytes that arrive with the proxy's CONNECT answer are discarded (engine 953b0a8 now returns them); it fails closed. | Feed the returned bytes into TLS, as the fetcher does. |
| F-88 | Info (gate only) | browser / scripts | engine built with `--cap-lints allow` | A3 I3 | The engine's `forbid(unsafe_code)` is enforced only by the engine's own gate. | `check.sh full` greps the pinned engine source for `unsafe`. |
| F-89 | Info | browser / installer, release-identity | `include_bytes!(r"{path}")` installer/build.rs, release-identity/build.rs | A3 I6 | A build-input path containing `"` would inject Rust (build-time input only). | Format with `{:?}`, or refuse such paths. |
| F-90 | Info (browser not affected) | engine / neoteletext-web | `descriptor.rs:423-432` | A3 I7 | A service's `push.input: true` may send typed keys to a WebSocket on another origin. The browser limits push to the channel's origin. | Engine to check against its push requirements; no browser change. |
| F-91 | Info (browser not affected: `dbsc` off) | engine / neoteletext-web | `bound.rs:217-229, 316-335`; `include_site` | A3 I1 | Repeated registrations create and delete keys without bound; `include_site` has no public-suffix check. | Bound registrations per origin per hour; refuse `include_site` (host-only jar) before any port enables `dbsc`. |
| F-92 | Info | engine / neoteletext-web | ws.rs:391-404 (close code echo); dbsc.rs:516-533 (duplicate member); `Writer::hex` | A1 info | 1005, 1006 and 1015 are echoed as close codes; a duplicate DBSC member overwrites the earlier one; `Writer::hex` overflows for a width over 8 (callers use 2 and 4). | Refuse those close codes; refuse duplicates; assert the width. |
| F-93 | Info | browser / core | "Updates unavailable" age core/src/updates.rs:260-263 | A1 info | The age uses the updater's own report of when it checked. | Stamp the receipt with the broker's `LocalTime`. |
| F-94 | Info (documentation only) | browser / docs, confine | macos.rs:10-12 ("the trusted core itself is not confined"); project `CLAUDE.md` unsafe list; requirement 10.12 Verification; `cookies.md` §7 cipher | A3 I4, I5; A1 info | Stale text: decision 56 confines the core; `confine` and `os-install` may hold `unsafe`; the cookie file is sealed with ChaCha20-Poly1305 (random 96-bit nonce), not the ciphers named. | Correct each text. |
| F-95 | Info (documentation only) | browser / docs | fetcher TLS roots | A4 browser info | Compiled-in webpki roots only: no OS store, no revocation (`CertificateProblem::Revoked` cannot occur). | State the gap in `security-analysis.md` and `certificate-errors.md`. |
| F-96 | Info | engine / neoteletext-web | url.rs origin comparison | A4 1.2 info | IPv6 hosts are compared by text, so the secure-host memory, cookie host and confirmed-origin table split between spellings. It fails closed. | Normalise stored IPv6 host text to RFC 5952. |
| F-97 | Info (test only) | engine, browser | no fuzz target for `contents::read`, `zxnet::parse_message`, `TsReader` with controlled PID/CC/adaptation; launcher tests use `TestSigner` only | A4 1.5, 1.9, §2; A1 info | Coverage gaps, not defects. | Add the three engine fuzz targets; the launcher regression tests named in F-02, F-07, F-08, F-09 and F-19 cover the rest. |
| F-98 | Info (test only) | browser / core | hostile-interface harness `core/src/hostile_tests.rs` (6554b45) | A3 I13 | It runs without a broker, a start-page tab, bookmarks, several windows or private tabs, and checks no hand-offs, bookmarks or decoder views. | Extend the harness to those states. |
| F-99 | Info (false positive for the browser) | engine / neoteletext-web | engine cookie jar partitioning (64c1a97) | A3 I2 (corrects slice (c)'s High) | Slice (c) rated it High for the browser. The browser's core keeps a jar per channel tag and refuses requests outside the folder (`owns`, `header_for`, `store`). For the engine's own jar, F-15 and F-42 are the real defects. | None beyond F-15 and F-42. |
| F-100 | Info (no change) | both | WebSocket masks from `RandomState` (fetcher main.rs:100-117); 10 s write timeout after connect; two AEAD and HMAC stacks; SHA-1 engine pin; dock-menu sender assumption; descriptor names allowing C1 and bidi (the port's duty, which the protocol's `is_clean` does); `history.rs:342-357` lowercase slicing; port text kept verbatim; duplicate settings keys last-wins; stat-then-read of same-user files; qrkeyboard `UnexpectedEof` as a clean close; lenient UTF-8 at an input message's end; leading empty lines and trailer limits in HTTP; `parse_proxy` unbracketed host; duplicate-counter TS packets | A1 info; A3 I10, I11, I12; A4 infos | Noted by the reports as acceptable. | None. |

---

## 2. Fix specifications

Each entry gives: **Change** (what code changes, by item name); **Test** (the regression test, which must fail on the reviewed code); **Verify** (platforms); **Changes to** (protocol bytes, file formats, requirements, documented decisions, by document). Documentation edits are carried out by WP-8 (section 4), so each code package can be done without touching `docs/`.

### F-01: Linux helpers reach session services over `AF_UNIX`

- **Change (confine, Linux):**
  1. *`families`:* for `Role::Network | Role::Updater { .. }`, return `[AF_INET, AF_INET6, AF_NETLINK]`, without `AF_UNIX`. The comment says name resolution then falls through glibc's NSS modules to `dns` over UDP (the nscd, nss-resolve and mdns sockets fail with EPERM, which glibc treats as UNAVAIL).
  2. *`seccomp`:* add a second rule to `SYS_socket` that refuses `domain == AF_NETLINK && protocol != NETLINK_ROUTE`. The rules for one syscall are alternatives; the existing "other family" rule stays. Add `SYS_pidfd_getfd` to `denied`.
  3. *`network_namespace`* (used by Decoder, Core, Interface and Sound): add `CLONE_NEWNS` to the `unshare`. Then, for `Role::Interface` and `Role::Sound` only, in a new function `private_runtime(role)` called from `apply` before `landlock`:
     - `mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL)`;
     - for each socket the role needs, `open_tree(AT_FDCWD, path, OPEN_TREE_CLONE)`. Interface: `$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY` (default `wayland-0`), `/tmp/.X11-unix/X<n>` for `DISPLAY=:n`, and the `XAUTHORITY` file when it lies under `/run` or `/tmp` (GNOME's Xwayland authority does). Sound: `$XDG_RUNTIME_DIR/pipewire-0`, `$XDG_RUNTIME_DIR/pulse/native`, or `PULSE_SERVER`'s path when it is `unix:`;
     - mount a tmpfs (mode 0700, size bounded by a named constant) over `/run` and over `/tmp`;
     - recreate each captured path's parent folders and an empty placeholder, then `move_mount` each captured tree onto it.

     A path that does not exist is skipped. A failed mount is an error and the helper does not run (decision 58). The `unsafe` stays in `linux.rs`, each block with its `// SAFETY:` comment (requirement 10.12).
  4. *`readable`:* keep `/run` and `/tmp` in `INTERFACE_PATHS` and `SOUND_PATHS`; after the tmpfs they hold only the bound sockets. This also closes A3 L9.
  5. *`ENVIRONMENT_WINDOW`* (lib.rs): remove `DBUS_SESSION_BUS_ADDRESS`. Nothing in the interface uses D-Bus: the only `zbus` user is `keyring` in the broker.
- **Test (`confine/tests/probe.rs`, Linux):** the test makes a temporary `XDG_RUNTIME_DIR` holding two listening sockets, `bus` and `wayland-0`, before it starts the confined probe.
  - For `Role::Network` and `Role::Updater`, `UnixStream::connect(bus)` fails with EPERM, and `socket(AF_NETLINK, SOCK_RAW, NETLINK_AUDIT)` fails with EPERM.
  - For `Role::Interface`, connecting to `bus` fails with ENOENT, and connecting to `wayland-0` succeeds.
  - For `Role::Sound`, `bus` fails and `pipewire-0` succeeds when present.
  - Every role: `/run/dbus/system_bus_socket` cannot be reached.
  - Name resolution by `getaddrinfo("localhost")` still works for `Role::Network`.

  On old code the `bus` connections succeed, so the test fails.
- **Verify:** Linux (`foundintelquiet4060`): the probe tests, then the browser started on the host's desktop session, checking that the window draws, typing works with the input method, sound plays, and a web channel loads by name (systemd-resolved stub and plain `resolv.conf` both). macOS and Windows: unaffected; run the full gate.
- **Changes to:** no protocol byte; no file format. Requirements: none (strengthens 3.x sandboxing). Documents: `sandboxing.md` (Linux layers per role), `sandboxing-security.md` §2 (the `AF_UNIX` row now controlled) and §5 (Linux rating), `security-analysis.md` §5. Decision D-1.

### F-02: Linux (and macOS) launcher accepts in place and renames the same inodes

- **Change (launcher, update):**
  1. *`Launcher::accept`:* in the `Family::Windows | Family::Linux` arm, remove the `Family::Windows` condition, so both use `copy_in`. `copy_in` copies into `versions/<v>.copying` with `files::copy_tree` (bounded as F-50), accepts the copy, then renames the copy. The staged folder is never renamed.
  2. *macOS arm:* copy the staged bundle with `files::copy_tree` into a launcher-only folder on the same volume as the installed bundle (`<layout root>/accepting/<v>/`; `renamex_np` needs one volume), run `update::accept::accept` on the copy, then let `macos::reconcile` exchange the copy, not the staged bundle. Preserve file modes and the bundle's `_CodeSignature`; extended attributes are not part of the seal.
  3. *At the top of `accept`:* refuse a staged root that is a symlink: `symlink_metadata(&staged)?.file_type().is_symlink()` gives the error "the staged version is a link". Do the same in `files::list_files` for its root.
  4. *`Launcher::tidy`:* under `staging/metadata`, keep only the names tough's datastore writes (`latest_known_time.json`, `*.root.json`, `timestamp.json`, `snapshot.json`, `targets.json`) and the F-06 floor file; remove anything else.
  5. *`install::launcher_release`* (Linux): copy the new launcher only from the accepted copy in `versions/<v>`, which is now launcher-owned, so its `.sig` was checked with the version.
- **Test (launcher/tests/launcher.rs, Linux and macOS):**
  - (a) `a_hard_link_into_staging_cannot_change_an_accepted_version`: stage a genuine (TestSigner) version, `fs::hard_link` its broker into `staging/metadata/x`, run `prepare`, write through `staging/metadata/x`, and assert that `versions/<v>`'s broker bytes are unchanged.
  - (b) `a_staged_root_that_is_a_link_is_refused`.
  - (c) `an_open_write_descriptor_cannot_change_an_accepted_version`: open the staged broker for writing before `prepare`, write after, and assert unchanged.

  All three fail on old code.
- **Verify:** macOS and Linux (launcher tests; then an end-to-end update with `scripts/updates-e2e.sh` on each). Windows: unchanged path; full gate.
- **Changes to:** no protocol byte. File layout: Linux gains `versions/<v>.copying` (already a Windows name, removed by `tidy`); macOS gains `<root>/accepting/`. Documents: `installation-and-updates.md` §5 and §3.1 (copy on every platform), `installation-and-updates-security.md` 4a (the Windows-only copy becomes general). Decision D-2.

### F-03: the broker's file read

- **Change (core crate, broker side: `read_for_core`, `Source::read`; no wire change):**
  1. Replace `SECRET_FOLDERS` with a rule function `refused_place(canonical) -> bool`, true for:
     - any path with a component beginning with `.` beneath the canonical home folder;
     - beneath `~/Library` on macOS, or `%APPDATA%` and `%LOCALAPPDATA%` on Windows;
     - beneath the browser's own settings folder (`stored::folder()`) or update root (`update::layout`). This refuses every link or hard link the confined core can make, because it can write only there.
  2. Open without following links, then check the descriptor, not the path (std only; no new `unsafe` in the core crate):
     - macOS: `OpenOptionsExt::custom_flags(libc::O_NOFOLLOW_ANY)` on the canonical path;
     - Linux: `custom_flags(libc::O_NOFOLLOW)`, then `fs::read_link("/proc/self/fd/<n>")` must equal the canonical path (the broker is unconfined, so `/proc` is there);
     - Windows: `custom_flags(FILE_FLAG_OPEN_REPARSE_POINT)`, then refuse when `file.metadata()?.file_type().is_symlink()`.

     Then `file.metadata()` (fstat) must be a regular file of at most `MAX_SOURCE_BYTES`, read from that descriptor.
  3. Folder mode in `Source::read`: list the entries, refuse entries whose `file_type()` is a link, open each by the same no-follow routine, and apply `refused_place` to each.
  4. Content: return only bytes the engine recognises, using `neoteletext_formats::detect::detect(prefix, complete)` returning `Detection::Found { format, .. }` with `format.is_compiled()`. Build it with the decoder's feature set, by name in `core/Cargo.toml`. A bookmarks file is recognised instead by `protocol::decoder::is_netscape_bookmarks` or by the first line being `bookmarks::VERSION_LINE`. In folder mode, skip files that are not recognised, and refuse the folder when none is.
  5. Every refusal answers one fixed sentence, "not a channel this browser can open" (no existence or size oracle), and `import_bookmarks` shows one fixed "Not imported" notice for every refusal.
- **Test (core, run with `HOME` set to a temporary folder):**
  - (a) a folder in the settings folder holding a link to `<home>/.ssh/id_test` is refused;
  - (b) `<home>/.netrc` is refused;
  - (c) `<home>/Documents/notes.txt` (not teletext) is refused;
  - (d) a T42 file and a folder of TTI files under `<home>/recordings` are accepted;
  - (e) a Netscape bookmarks file is accepted.

  (a), (b) and (c) fail on old code.
- **Verify:** macOS, Linux. Windows: implement, verify by hand on Windows. The owner checks that a `.t42` in Documents opens, that a TTI folder opens, that a file under `%APPDATA%` is refused, and that a junction inside the settings folder pointing at `%USERPROFILE%\.ssh` is refused.
- **Changes to:** no protocol byte and no file format. Requirement change: the broker refuses non-teletext files and the listed places (amend the requirement that decision 56 introduced for file channels; WP-8 names it). Documents: `security-analysis.md` §16 rank 4 (residual: a compromised core can still read teletext-looking files elsewhere, including any exact 960- or 1000-byte file, which `detect` takes as a screen dump), `sandboxing-security.md` (broker). Decision D-3.

### F-04: the Windows interface has the network

- **Change (confine, Windows):** in `spawn`, remove the `Role::Interface` special case, so the interface takes the container path. `container(Role::Interface)` gets its own AppContainer profile with **no capabilities** (no `internetClient`) and Win32k left on, because it has windows. Keep the job, the mitigation policies and the handle list. Delete `restricted_token` if nothing else uses it. Report "AppContainer, no capabilities". If the container cannot be made, the interface does not run (decision 58).
- **Test:** confine probe with `Role::Interface`: `TcpStream::connect("1.1.1.1:443")` fails, and `fs::read(%USERPROFILE%\Documents\probe.txt)` fails. Both succeed on old code.
- **Verify:** implement, verify by hand on Windows. The owner checks:
  - the window opens and draws, including a teletext page and the strip's text;
  - keyboard typing and an IME composition (for example Japanese) work in the address field;
  - copy and paste in fields;
  - full screen, DPI change and resize;
  - the cursor shapes;
  - the probe's two refusals.

  If the window cannot be created in an AppContainer, stop and report to the owner. The alternative, a restricted token with restricting SIDs that deny `\Device\Afd`, is the owner's decision.
- **Changes to:** no protocol byte. Documents: `sandboxing.md` (interface row on Windows; the "a container cannot reach the desktop" statement in `spawn`'s comment is removed), `sandboxing-security.md` (the Windows gap no longer includes the interface's file reads or network). Decision D-5.

### F-05: local-network rule on macOS and Linux

- **Change (confine, macOS):** in `profile`, `Role::Network`, when `spawn.local_network` is false, append `(deny network-outbound (remote ip "localhost:*"))` after the allow (the later rule wins). SBPL cannot name private ranges, so the LAN remains a macOS residual.
- **Linux:** no code change in this round (D-4).
- **Test (macOS probe):** with `Role::Network` and `local_network = false`, connecting to a loopback listener fails; with `true` it connects. The first case connects on old code.
- **Verify:** macOS.
- **Changes to:** documents: `security-analysis.md` §5.1 and `sandboxing-security.md` say that on Linux, and for the LAN on macOS, the local-network rule holds only while the fetcher is not compromised. Requirement 5.10's Verification notes the residual. Decision D-4.

### F-06: TUF root-version floor

- **Change (tuf updater):** in `Config::load`, after `RepositoryLoader::load()`:
  - read `repository.root().signed.version`;
  - read `staging/metadata/root-version` (decimal, bounded to 20 bytes, written synced and renamed);
  - if the loaded version is lower than the file's, fail with a new error, "the update host offered an older root";
  - otherwise write the loaded version.

  The built-in `TUF_ROOT` stays the trust anchor (D-6).
- **Test (tuf/updater tests, using the test repository the release tool builds, as `scripts/updates-e2e.sh` does):** serve `2.root.json`, load (floor becomes 2); then serve 404 for `2.root.json` and load again; the second load must fail. On old code it succeeds.
- **Verify:** macOS, Linux.
- **Changes to:** new file `staging/metadata/root-version` (kept by `tidy`, F-02 item 4). Documents: `installation-and-updates.md` §8 (requirement 13.8's rollback protection now covers root versions), `installation-and-updates-security.md`. Decision D-6.

### F-07: Windows manifest signature

- **Change:**
  - *`update::accept`:*
    - `own_files` includes `MANIFEST_SIGNATURE` for `Family::Windows`;
    - `accept` verifies `manifest.sig` against the pinned release key for Windows as `LinuxSigner::check` does for the manifest, before `signer.check`, with the code shared by one function;
    - `Keys::linux_release` is renamed `release` and used by both families.
  - *`release-identity/build.rs`* embeds the release key in Windows builds.
  - *`tuf/release` `package`* and *`scripts/release/build-windows.ps1`/signing* sign the Windows manifest with the same Ed25519 release key (`command:` hardware key in production).
- **Test (update, runs on macOS with `Platform` Windows and a test Ed25519 key):**
  - (a) a folder without `manifest.sig` is refused;
  - (b) programs from releases 0.2.0 and 0.3.0 under a 0.4.0 manifest signed by another key are refused;
  - (c) a genuine signed folder is accepted.

  (a) and (b) are accepted on old code.
- **Verify:** macOS (unit tests). Windows: implement, verify by hand on Windows. The owner builds and signs a test-identity release, publishes it to the test host, updates in the VM, and confirms that a version with a tampered `manifest.sig` is refused.
- **Changes to:** **file format:** the Windows release folder gains `manifest.sig`. Documents: `installation-and-updates.md` §4.3 (signatures per platform) and §5, `installation-and-updates-security.md`. Decision D-7.

### F-08: refused folders mark versions bad

- **Change (launcher):**
  - In `Launcher::prepare`, the `Err(why)` arm removes `state.mark_bad(candidate)`; it logs, deletes the staged folder (`files::remove_tree`), and continues.
  - `mark_bad` is called only in the rollback branch.
  - The `candidates` loop examines at most `MAX_CANDIDATES_PER_START` (a named constant of 3, with the comment: each examination hashes up to a version's size; the newest that passes wins and older ones are tidied).
- **Test (update `launcher/tests/launcher.rs:255-264` and add):** a junk `staging/0.3.0` is refused and deleted, and `is_bad(0.3.0)` is false; a genuine 0.3.0 staged afterwards is accepted. It fails on old code.
- **Verify:** macOS, Linux.
- **Changes to:** documents: `installation-and-updates.md` §3.1 step 3 (refusal deletes; "bad" means a failed trial). Launcher state format unchanged.

### F-09: health deadline and trial counting

- **Change:**
  1. *`update::layout`:*
     - add `STARTED_LINE` (`"started\n"`) beside `HEALTHY_LINE`;
     - move the core's `HEALTH_WINDOW` and `HEALTH_SETTLE` here;
     - define `HEALTH_DEADLINE = HEALTH_WINDOW + HEALTH_SETTLE + HEALTH_MARGIN` (named margin, with its reason: the broker starting the core);
     - define `START_DEADLINE` (named, 5 minutes: first-run executable checks and antivirus scans);
     - add `const _: () = assert!(...)` that the deadline exceeds window plus settle.
  2. *Broker* (`broker()` in core/src/main.rs, its first statement, through a new `updates::tell_launcher_started()`): write `STARTED_LINE` on standard output before `start_core`.
  3. *`start::start`:* two phases. Wait up to `START_DEADLINE` for `started`. On expiry, kill the process group and return `Ended { started: false, .. }`. After `started`, wait up to `HEALTH_DEADLINE` for `healthy` (the line reader fixed as F-47).
  4. *`Trial`* (update/src/state.rs) gains `not_started: u8` and `running: bool`.
     - *Before a trial start:* `prepare` increments `not_started` and writes the state.
     - *When `started` is heard:* the launcher sets `not_started = 0` and `running = true`, and writes the state.
     - *On an end that is not success, or a health deadline, after `started`:* `failed += 1`, `running = false`, written.
     - *On a clean exit before health* (the user quit): `running = false`, nothing counted.
     - *At the next `prepare`:* if `running` is still set (the launcher itself died mid-trial), `failed += 1`.
     - *Rollback with `mark_bad`* when `failed >= FAILED_STARTS_TO_ROLL_BACK`, or when `not_started >= NOT_STARTED_TO_ROLL_BACK` (named, 3).
     - *After a start deadline:* `run` runs `state.current` for this start instead of retrying the trial; the trial stays for the next start.
  5. *`core/src/updates.rs`:* use `update::layout::HEALTH_WINDOW` and `HEALTH_SETTLE` by name.
- **Test (launcher/tests/launcher.rs):**
  - (a) `a_trial_killed_before_started_is_not_counted` (fails on old code: counted);
  - (b) `a_clean_quit_before_health_is_not_counted` (fails on old code);
  - (c) `a_broken_version_is_rolled_back_after_two_starts` rewritten. `crash` and `quiet` get `NO_DEADLINE_NEEDED` (several minutes) and only `hang` gets `SHORT_DEADLINE`. It asserts `trial == None`, `is_bad(NEW)` and `rolled_back == Some(NEW)`, and keeps the log-line count only as "at least one".
  - (d) a state-file round trip with the new fields.
- **Verify:** macOS, Linux (launcher tests, and an end-to-end trial on each with a deliberately crashing test version). Windows: implement, verify by hand on Windows. The owner checks that an update trial commits in the VM, and that a test version that crashes rolls back after two starts.
- **Changes to:** **protocol byte:** a new line `started\n` on the broker-to-launcher pipe. **File format:** the launcher state's trial gains two fields (still within `MAX_STATE`). Documents: `installation-and-updates.md` §3.2 and §14, and **decision 80** amended (45 s from spawn becomes a start deadline then a health deadline from `started`). No re-offer of a deadline-only rollback (D-8).

### F-10: unbounded inbound queue

- **Change (core):** a new type `Budget` (core/src/budget.rs): `Arc<(Mutex<usize>, Condvar)>` with `acquire(bytes)`, which blocks while `used + bytes > outbox::MAX_QUEUED_BYTES` (by name), and `release(bytes)`.
  - Each untrusted reader thread (`start_decoder`, `start_fetcher`, the sound and phone readers, `read_interface`) owns one `Budget`, acquires the message's payload length before `events.send`, and puts the size and a clone of the budget in the event.
  - The main thread releases after handling the event.
  - A full budget blocks only that reader thread, so the helper's pipe fills and that helper stalls; the core's thread never blocks on it.
  - A single message larger than the budget cannot occur (`MAX_PAYLOAD` is below it; assert this at compile time).
- **Test:** a fake decoder thread writes valid frames into an in-memory pipe as fast as it can while the core's handling is held for 1 s. The bytes it managed to write must be at most budget + pipe buffer + one frame. On old code it writes without bound, so the test fails.
- **Verify:** macOS, Linux.
- **Changes to:** none outside the core. Documents: `security-analysis.md` §5.3 now true as written.

### F-11: frames without a rate bound

- **Change (core, `Frames`):**
  - Per page key, keep `last_sent: Instant` and `held: Option<frame>`.
  - `accept` sends at once when `MIN_FRAME_INTERVAL` has passed since `last_sent`. Otherwise it holds the newest frame (replacing any held one), and returns nothing.
  - A new `Frames::due(now)` returns the held frames whose interval has passed, encoded against the last frame sent.
  - The main loop's timer calls it.
  - `MIN_FRAME_INTERVAL` is derived, with the clause cited, from EN 300 706's fastest Additional Flash Functions change: the shortest interval between two legitimately different renderings. It is used by name from the engine if the engine has the constant; otherwise the engine gains it by its own process (requirement 2.4).
- **Test:** a decoder sending two alternating frames for one visible page at 1 kHz for 1 s yields at most `ceil(1 s / MIN_FRAME_INTERVAL) + 1` frames to the interface. On old code it yields about 1,000.
- **Verify:** macOS, Linux. Measure with `NEOTELETEXT_FRAME_TRACE=1` on the reference channel (`neoteletext-site terminal`) with a flashing page, before and after: the frames drawn per second must be unchanged.
- **Changes to:** documents: `architecture.md` §10 (step 3 holds frames to the interval).

### F-12: helper exit not counted

- **Change (core):**
  - Each decoder and fetcher record gains `heard: bool`, set on its first message.
  - In `decoder_ended`, after the generation check (which already discards ends the core caused), call `self.updates.helper_failed(..)` when `reason.is_some()` or `!heard`.
  - In the `Event::FetcherEnded` handler, call it when the core did not end that fetcher and `!heard`.
  - Correct the comment at 1184-1185. A helper that ends *after* speaking is not counted, so a hostile server that crashes a fetcher cannot force a rollback.
- **Test:** a stand-in decoder program that exits with failure before writing anything marks the trial unhealthy (`Health::healthy` false). On old code it is healthy.
- **Verify:** macOS, Linux.
- **Changes to:** documents: `installation-and-updates.md` §3.2 ("a helper that ends before it first speaks").

### F-13: engine cookie import

- **Change (engine, `CookieJar`):**
  - `import_one` always consumes the record. An expired record uses `saturating_sub`, so `store` refuses it, and returns `Some((false, rest))`; header overflow returns `Some((false, rest))`.
  - The path is passed to an internal `store_with_path` instead of being rebuilt as a `Path=` attribute, so the 1024-byte attribute limit no longer widens it.
  - `import` stops only on a malformed record.
- Browser: `Store::import` compares the count with the record lines and logs when fewer were restored.
- **Test (engine):**
  - (a) an expired record followed by a live one restores the live one;
  - (b) a cookie with a 1100-byte path (probe C) is sent only inside its folder after export and import.

  Both fail on old code.
- **Verify:** macOS (engine gate), Linux (engine full gate), then re-pin.
- **Changes to:** no file format. Documents: browser `cookies.md` §6 now true; engine REQ-WEB cookie text unchanged.

### F-14: DBSC session identifier

- **Change (engine):** in `dbsc.rs`, read `session_identifier` with a reader that refuses an empty value and any byte outside `0x21..=0x7E` (`InstructionsError::Malformed`); `sf_string` returns `Err(Overflow)` for any byte outside `0x20..=0x7E`.
- **Test:** instructions with `"a\r\nX: y"` and `"a\u0000"` are refused; `sf_string` with LF fails. Both are accepted on old code.
- **Verify:** macOS, Linux (engine, with the `dbsc` feature).
- **Changes to:** engine `docs/spec/requirements/web.md` (the DBSC identifier's allowed bytes).

### F-15: push handshake cookies unscoped

- **Change (engine):** in `push_head_complete`, pass `self.channel.as_ref().map(Url::path)` as the scope to `store_response_cookies`.
- **Test (engine, beside the REQ-WEB-026 tests; probe A):** two channels `/a/` and `/b/` on one origin; the push 101 sets `Path=/`; the cookie is not sent for `/b/100.tti`. Sent on old code.
- **Verify:** macOS, Linux (engine).
- **Changes to:** none (conformance with REQ-WEB-026).

### F-16: form re-posted on 307 or 308

- **Change (engine, `redirect`):** for `Purpose::Form` with the method kept (307 or 308), when `next.origin()` differs from the submission's target origin, fail with `FormRefused::Origin`. 303 and 301/302-on-POST are unchanged (they become GET with no body).
- **Test (engine replay; probe E):** `third.example` receives nothing, and the agent reports `FormRefused::Origin`. On old code `third.example` receives the body.
- **Verify:** macOS, Linux (engine), then re-pin; the browser's fetcher inherits it.
- **Changes to:** engine `sec.md` REQ-SEC-009 and `web.md` REQ-WEB-008 notes (form redirects keep the origin). Decision D-13.

### F-17: proxy local names

- **Change (engine, `hidden_local`):** also refuse single-label names (no dot after removing a trailing dot) and names ending `.home.arpa`, `.lan`, `.corp`, `.intranet`, `.private` and `.localdomain`, case-folded.
- **Test:** `router`, `nas.lan` and `x.home.arpa` are refused through a proxy, and `example.com` is allowed. The first three pass on old code.
- **Verify:** macOS, Linux (engine).
- **Changes to:** engine `sec.md` REQ-SEC-006: through a proxy the rule is by name, with the list. Browser `security-analysis.md` §7 states it (a rebinding name such as `10.0.0.1.nip.io` stays a residual). Decision D-15.

### F-18: relay serves the phone's code (documentation only)

- **Change:** WP-8 edits `docs/interaction-security.md`:
  - §4 E: the row reads "a passive relay or network observer reads keys: it cannot";
  - a new row: "the relay serves the phone's page, so its operator or a compromise of its server reads the PIN and the keys; bounded by §F (a hostile phone is a hostile local keyboard with no modifiers)";
  - §7 ranks it.
- **Test:** none.
- **Verify:** none.
- **Changes to:** `interaction-security.md`. Decision D-11.

### F-19: macOS `previous/` and rollback

- **Change (launcher, macOS):** in `macos::reconcile`, before exchanging `previous` into place, run `MacosSigner::check` and the version-mark check on it. If either fails, keep the current bundle, log, and leave the state's rollback recorded. `move_old_current` considers only `staging/<trial version>`.
- **Test (launcher, macOS, TestSigner):** a `previous/` carrying the current mark but failing the signer is not exchanged in after two failed trials. It is exchanged on old code.
- **Verify:** macOS.
- **Changes to:** `installation-and-updates.md` (macOS rollback).

### F-20: phone keys drive browser controls

- **Change (core, `phone_said`):** when no page is open for typing, forward `PhoneKey::Key` only for the page-navigation set: digits `0`-`9`, the four arrows, and the four Fastext colour keys if the layout has them. These go in one named list in protocol/src/keyboard.rs beside the layout. Drop Enter, Tab, Escape, Backspace and letters.
- **Change (interface, `phone_key`):** deliver phone keys only to the page view's key handler, never to a focused text field, a link or site-change prompt, or a panel. While any of those has focus, phone keys are dropped.
- **Test:**
  - core: with no typing page, `FromKeyboard::Key { name: "Tab" }` and `"Enter"` send nothing to the interface, and `"1"` is forwarded;
  - interface-core: a phone Enter while a link prompt is shown does not produce `Confirm`.

  Both fail on old code.
- **Verify:** macOS, Linux, with the local qrkeyboard relay (`NEOTELETEXT_QRKEYBOARD_RELAY`).
- **Changes to:** documents: `interaction.md` (what phone keys do outside a typing page; amends the departures confirmed with **decision 46**) and `interaction-security.md`. Decision D-16.

### F-21: seccomp x32

- **Change (confine, Linux, `seccomp`, `cfg(target_arch = "x86_64")` only):** a third filter, built by hand as a `BpfProgram` of `sock_filter`:
  - load `arch`; if not `AUDIT_ARCH_X86_64`, `RET ALLOW` (the first filter already kills a wrong architecture);
  - load `nr`; if `nr >= 0x4000_0000` (`__X32_SYSCALL_BIT`, by a named constant citing `asm/unistd.h`), `RET ERRNO(EPERM)`;
  - `RET ALLOW`.

  It is applied with `seccompiler::apply_filter` after the others.
- **Test (Linux probe):** `syscall(__X32_SYSCALL_BIT | SYS_getpid)` returns EPERM. On old code it returns ENOSYS on a kernel without x32 (and succeeds where x32 is on), so the test fails either way.
- **Verify:** Linux.
- **Changes to:** `sandboxing.md` (seccomp layer).

### F-22: `TIOCSTI`

- **Change (confine, Linux, `seccomp`, every role):** rules for `SYS_ioctl` with arg 1 (`Dword`, `Eq`) equal to `TIOCSTI` and to `TIOCLINUX` (libc constants, by name), giving EPERM.
- **Test (Linux probe):** the child opens a pty, makes it its controlling terminal (`setsid`, `TIOCSCTTY`), dups it to fd 2, confines, and calls `ioctl(2, TIOCSTI, &b'x')`, expecting EPERM. On old code it succeeds. On a kernel with `dev.tty.legacy_tiocsti = 0` the old code also fails, so the test checks that file and reports that it cannot show the regression there.
- **Verify:** Linux.
- **Windows:** implement nothing yet; verify by hand on Windows. The owner checks whether a confined helper started from a console can open `CONIN$` and call `WriteConsoleInputW`. If it can, the follow-up is `DETACHED_PROCESS` with a broker-relayed standard-error pipe (decided now as the fix).
- **Changes to:** `sandboxing.md`.

### F-23: AppArmor profile

- **Change:**
  - *`tuf/release` `package`* and the launcher's printed profile (unix.rs): name only the programs whose roles call `network_namespace`, which are the broker/core program and the decoder, interface and sound programs, by their exact file names from the platform's file list. The pattern is `<root>/versions/*/{…}`.
  - The launcher prints it with `<root>` the real installation root (so `XDG_DATA_HOME` is covered); the release copy shows the default root.
  - The printed text tells the administrator, in one sentence, that it allows user namespaces for programs at that path.
- **Test:** a launcher unit test that the printed profile names exactly those four files under the given root (fails on old code: glob `neoteletext{,-*}` under `@{HOME}`).
- **Verify:** Linux, on a host with `kernel.apparmor_restrict_unprivileged_userns=1` (`foundintelquiet4060` if it runs Ubuntu 24.04 or later; otherwise the owner): install the profile, and confirm that the browser runs and that a program copied to `versions/x/neoteletext-fetcher` gets no user namespace.
- **Changes to:** `installation-and-updates.md` (Linux installation), `installation-and-updates-security.md` (residual: any program the user writes at those four names gets user namespaces). Decision D-10.

### F-24: test identity in a release

- **Change:**
  - `release-identity/build.rs` treats an empty `NEOTELETEXT_RELEASE_IDENTITY` as unset.
  - `build-linux.sh` passes it only when set (`${NEOTELETEXT_RELEASE_IDENTITY:+-e …}`).
  - The launcher carries `release_identity::NAME` as a mark (the `version_mark!` mechanism).
  - `neoteletext-release check` reads the mark from the built launcher and exits non-zero unless it is `production` or `--test-identity` is given.
  - `sign-linux` and `publish.sh` run `check` for every platform first, and refuse `file:` keys with a production identity.
  - Every release script refuses to run with the variable set unless `--test` is given.
- **Test:**
  - `tuf/release` test: `check` on a launcher built with a test identity fails without `--test-identity` (passes on old code);
  - script test in `scripts/check.sh full`: `publish.sh --dry-run` with the variable set refuses.
- **Verify:** macOS, Linux.
- **Changes to:** release documentation in `installation-and-updates.md` (release procedure); the launcher binary gains an identity mark (a format the release tool reads).

### F-25: Windows DLL planting

- **Change:**
  - `build.rs` of `installer`, `stub` and `launcher`, for `target_os = "windows"` and `target_env = "msvc"`, prints `cargo::rustc-link-arg=/DEPENDENTLOADFLAG:0x800` (`LOAD_LIBRARY_SEARCH_SYSTEM32`, cited from the linker documentation).
  - A new safe `os_install::restrict_dll_search()` (the `unsafe` stays in os-install) calls `SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32)`, as the first statement of each `main`.
- **Test:** none automatic.
- **Verify:** implement, verify by hand on Windows. The owner:
  - runs `dumpbin /loadconfig NeoTeletext-Setup.exe` and sees `DependentLoadFlags 0x800`;
  - puts a renamed harmless DLL named `wintrust.dll` beside the installer in Downloads;
  - runs it under Process Monitor and sees `wintrust.dll` and `crypt32.dll` loaded from `C:\Windows\System32` only, with the installer still working.
- **Changes to:** `installation-and-updates-security.md` (installer).

### F-26: phone panel blocks the core

- **Change (core, `phone_panel`):**
  - On close, drop the helper's input, record `phone_ending = Some(now + PHONE_END_GRACE)` (named, 2 s), and return without waiting.
  - The phone reader's end event (`PhoneEnded`) reaps with `Wait`, which no longer blocks, because the process has ended.
  - The core's timer sends `Kill` when the grace has passed.
- **Change (keyboard, `keyboard.rs`):** spawn the stdin watcher thread before `Screen::create`. It ends the process when stdin closes, whether or not a screen exists.
- **Test:**
  - core: with a stand-in keyboard helper that ignores stdin closing, `phone_panel(false)` returns within 100 ms, and the helper is killed after the grace (on old code it blocks until the helper exits);
  - keyboard: closing stdin during a blocked `create` (pointed at a listener that never answers) ends the process within 1 s.
- **Verify:** macOS, Linux.
- **Changes to:** none (conformance with `security-analysis.md` §5.3 and decision 53).

### Low and Info findings: changes, tests, platforms

Unless stated otherwise: the test is a unit test beside the code that fails on old code; **Verify** is macOS and Linux; no protocol byte, file format, requirement or decision changes.

| Id | Change (by item) | Regression test | Verify | Changes to |
|---|---|---|---|---|
| F-27 | `cookie_reply` `ReachedQuestion`: `owner.as_ref().is_some_and(\|(owner, private)\| owner.host == host)` and `reached_securely` searches only that `private` jar. | Foreign host answers false; private-jar host answers false to an ordinary tab. | macOS, Linux | `cookies-security.md` |
| F-28 | `protocol::keyboard::clean_name` refuses any name `is_clean` would refuse (the shared hidden set). | `FromKeyboard::Key { name: "a\u{200B}" }` is refused by `read_from_keyboard` (probe case). | macOS, Linux | none |
| F-29 | `Fields::key` validates with `page_index`; `write_to_decoder(Showing)` checks each page and bounds the count to `PAGES`. | Key 0x1A0 refused. | macOS, Linux | none |
| F-30 | `match_decoders`: count replacements per channel; over `MAX_DECODER_RESTARTS` (named, 5) in `RESTART_WINDOW` (named, 60 s), mark the channel failed until reloaded. | A decoder overflowing six times in a minute leaves the channel failed. | macOS, Linux | none |
| F-31 | Each strict reader keeps the first `MAX_DROPPED_REPORTED` (64) messages and a count, and skips empty lines. | A 100,000-line malformed file yields 64 messages and the count. | macOS, Linux | none |
| F-32 | Documentation only: `cookies.md` §7 and `cookies-security.md` say the key is held in the core's memory for its life and not wiped (no `zeroize` dependency, no new `unsafe`). | none | none | `cookies.md`, `cookies-security.md` (D-14) |
| F-33 | `Store::import`: refuse a channel line whose key was already read; assign fresh tags on import. | A file with one key under two tags imports one channel. | macOS, Linux | none |
| F-34 | Confine `apply` (Linux): `prctl(PR_SET_PDEATHSIG, SIGKILL)`, then check `getppid()` against the expected broker. Launcher `start`/`end_whole`: kill the process group after every broker exit. | Linux probe: killing the broker kills a confined child. Launcher: after a broker crash no helper remains in the group. | Linux (both); macOS (the launcher part) | `sandboxing.md` |
| F-35 | The private writer (history's, moved by `structure/core`), settings and the main.rs writer: `remove_file` then `OpenOptions::create_new` with `O_NOFOLLOW`; `DirBuilder::mode(0o700)`; `set_permissions(0o600)` on existing files. | A link at the temporary name is not followed; the folder is 0700. | macOS, Linux | none |
| F-36 | `editor::hidden` refuses general categories Cf, Zl, Zp, U+FE00-FE0F, U+E0100-E01EF, U+115F, U+1160, U+3164, U+FFA0; `clean` bounds consecutive Mn/Me to `MAX_COMBINING_RUN` (named). | Each listed character is refused; 100 combining marks are cut. | macOS, Linux | none |
| F-37 | dock-menu crate root: the same `#![deny(...)]` list as protocol; `tag.saturating_add(1)`. | Clippy is the test. | macOS | none |
| F-38 | Engine qrkeyboard: `FromPhone::Up` emits only for a key in `self.held`; otherwise acknowledge and emit nothing. | An `Up` for an unheld key emits nothing. | macOS, Linux (engine) | none |
| F-39 | Engine qrkeyboard: the owner token must match `message::is_id`'s alphabet. | A token with CR is refused. | macOS, Linux (engine) | none |
| F-40 | Browser keyboard: map `Error::Tls(_)` to the fixed sentence "the relay's certificate was refused" before printing. | The printed line contains no certificate name. | macOS, Linux | none |
| F-41 | `web_opener::acceptable` keeps refusing what it refuses, and the re-serialised address percent-encodes `' ; & $ ( ) * [ ] ~ !` outside the query's `&`/`=` (or, simpler, refuses `'`, `;`, `$`, `(`, `)`, `!`, `` ` ``). Decided: refuse them. | `https://a.example/x;$(id)` refused. | macOS, Linux; Windows by hand (the owner opens one link from a page) | `hyperlinks-security.md` |
| F-42 | Engine fetch path: `let scope = channel.as_ref().filter(\|f\| channel::is_inside(f, &exchange.url)).map(Url::path)`, and do not store cookies from responses outside the channel. | A form-target response's `Set-Cookie` is not stored for the channel. | macOS, Linux (engine) | engine `web.md` REQ-WEB-026 note |
| F-43 | Engine `remember_secure`: evict the least recently seen host when `SECURE_HOSTS` is full. | The 33rd host is remembered and the oldest forgotten. | macOS, Linux (engine) | none |
| F-44 | Engine `redirect`: an empty, non-UTF-8 (`core::str::from_utf8` failing), or same-address-same-method `Location` gives `Failure::BadRedirect`. | Probe B gives one request and `BadRedirect`. | macOS, Linux (engine) | none |
| F-45 | Engine `is_inside`/`redirect_keeps_channel`: refuse `%2E`, `%2F` and `%5C`, in either case, after the folder. | `/a/%2e%2e/b/` is not inside `/a/`. | macOS, Linux (engine) | none |
| F-46 | Engine `policy`: block `::a.b.c.d`, `64:ff9b::/96`, `64:ff9b:1::/48`, `fec0::/10`, `192.0.0.0/24` and `198.18.0.0/15`; for NAT64 and 6to4 (`2002::/16`) apply the IPv4 rule to the embedded address. Each range cites its RFC (6052, 8215, 3879, 6890, 2544, 3056). | Each listed address is blocked. | macOS, Linux (engine) | engine `sec.md` REQ-SEC-006 list |
| F-47 | Launcher health reader: keep a "at line start" flag; accept `healthy\n` or `started\n` only when the previous read ended in `\n`. | 64 bytes then `healthy\n` on one line is not accepted. | macOS, Linux | none |
| F-48 | `--uninstall`: require `layout.state()` or the installed launcher to exist (Linux), or the bundle path to end in `NeoTeletext.app` (macOS), before removing anything. | `--uninstall` from a copied binary elsewhere removes nothing. | macOS, Linux | none |
| F-49 | Updater: report `SystemTimeSteppedBackward` as its own message; remove `latest_known_time.json` when it is more than `CLOCK_STEP_ALLOWED` (named, 1 day) ahead of now, then check again. | A file a year ahead is removed and the check proceeds. | macOS, Linux | `installation-and-updates.md` §8 |
| F-50 | `files::copy_tree` copies only the manifest's files (with the manifest and signature), each read to at most its manifest length; on Windows each entry is opened with `FILE_FLAG_OPEN_REPARSE_POINT` from the directory and the handle is checked. | An extra 100 MB file in the staged folder is not copied; an over-long file is refused. | macOS, Linux; the Windows handle part is implemented and verified by hand on Windows (the owner stages a version with a junction inside and sees it refused) | none |
| F-51 | macOS `preamble`/`profile`: write `(param "PROGRAM")`, `(param "WRITABLE")`, `(param "HOME")` and so on, and pass each with `sandbox-exec -D NAME=value`. | The probe copied into a folder named `x")(allow default)("` cannot read a file outside its rules (it can on old code). | macOS | `sandboxing.md` (D-12) |
| F-52 | macOS `SYSTEM_READS`: replace `/private/var/folders` with the program's own `DARWIN_USER_CACHE_DIR` and `DARWIN_USER_TEMP_DIR` sub-folders, measured by the bisection method of `security-analysis.md` §13. Probe whether the interface can `LSOpenCFURLRef` a web address; if it can, deny `mach-lookup` of `com.apple.coreservices.launchservicesd`, unless the measured run shows the interface needs it, in which case record the residual. The pasteboard stays (fields need it, decision 84). | A probe of another application's cache folder is refused. | macOS | `sandboxing-security.md` |
| F-53 | Restore: a `file:` tab is read through the broker only when first shown. Netscape import drops `file:` addresses. | Restoring 64 file tabs makes no broker read until one is shown; an imported `file:` bookmark is dropped. | macOS, Linux | `history-and-bookmarks.md` (import rule) |
| F-54 | Interface paste: cut to `MAX_PASTE` on a character boundary immediately after `get_text()`. | Covered by inspection; a unit test on the cutting function. | macOS, Linux, Windows by hand (paste into the address field) | none |
| F-55 | Sound `audio.rs`: make a mixer only on `Define` or `Stream`, ignore other operations for unknown channels, and allocate outside the lock and swap it in. | An operation on an unknown channel makes no mixer. | macOS, Linux; Windows by hand (sound plays) | none |
| F-56 | Confine `unix.rs`: `#[repr(C, align(8))] struct Control([u8; CONTROL_BYTES])`, and `const _: () = assert!(CONTROL_BYTES >= CMSG_SPACE(2 * size_of::<c_int>()))` (const on Linux; runtime check on macOS). | Miri or a test that asserts the buffer's alignment. | macOS, Linux | none |
| F-57 | macOS `receive`: check `MSG_CTRUNC` before wrapping any descriptor, clamp `length` to `msg_controllen`, and check `fcntl`'s result. | A sender passing three descriptors gets an error, and no descriptor of the receiver is closed. | macOS | none |
| F-58 | `environment_block`: `if environment.is_empty() { block.push(0) }` before the final NUL. | A unit test of `environment_block` with an empty environment expects two NULs; the existing `a_helper_whose_container_cannot_be_made_is_not_started` then runs clean. | Windows by hand (the confine tests in the VM) | none |
| F-59 | Attribute list storage `Vec<u64>` of `size.div_ceil(8)`. | The confine tests in the VM. | Windows by hand | none |
| F-60 | Confine `seccomp`: `kill`, `tgkill`, `rt_sigqueueinfo` and `rt_tgsigqueueinfo` with arg 0 not equal to the process's own pid (read before the filter; no fork is possible after it), giving EPERM; `tkill`, `pidfd_open` and `pidfd_send_signal` give EPERM. | Linux probe: `kill(getppid(), 0)` gives EPERM; `raise(SIGUSR1)` with a handler still works. | Linux | `sandboxing.md` (D-9) |
| F-61 | The broker's `open_web` closure in `broker()` keeps a last-opened instant and refuses an `OpenWeb` within `OPEN_WEB_INTERVAL`, which is the core's existing one-per-2-s hand-off bound, moved to one shared constant and asserted equal. No `Spawn` argument validation (D-3). | Two `OpenWeb` requests 1 s apart: the second is refused. | macOS, Linux | `security-analysis.md` §16 rank 4 (residual) |
| F-62 | Fetcher `reach`: after `to_socket_addrs`, skip addresses that `neoteletext_core::policy::is_blocked` refuses unless the channel's local access is allowed; fail if none is left. | A name resolving to 127.0.0.1 opens no connection. | macOS, Linux | none |
| F-63 | Fetcher transport: one `CONNECT_DEADLINE` (named) for the whole `open`, covering resolution, connects and the TLS handshake; `Link::Connecting` keeps a cloned `TcpStream`, so `close` shuts it. | Against a black-hole listener, `open` returns within the deadline, and `close` during a connect ends the thread. | macOS, Linux | none |
| F-64 | Core: grant `local_network` to the phone keyboard, and read `NEOTELETEXT_QRKEYBOARD_RELAY`, only under `cfg(debug_assertions)`. Confine `ENVIRONMENT_CORE`: pass the variable only in debug builds, as `ENVIRONMENT_UPDATER` does. | A release-profile unit test: `environment(Role::Core)` omits the variable. | macOS, Linux; Windows by hand (the phone keyboard pairs with qrkeyboard.com in a release build) | project `CLAUDE.md` (the relay variable is for debug builds) |
| F-65 | Links `Asking` stores the window and tab; it is cleared when the window changes; a `Confirm` from another window is ignored. | `From(B)` then `Confirm` in A does not send B's tab. | macOS, Linux | none |
| F-66 | `opened`: refuse a key whose channel is not the active channel. | `PageControl` for another tab's key reaches no decoder. | macOS, Linux | none |
| F-67 | `Opened(Some(key))` on a start-page bookmark follows requirement 4.5's rule (intent is shown, not acted on). | The start-page bookmark intent does not navigate. | macOS, Linux | none |
| F-68 | Turning off update checks logs one line and shows a notice. | The settings change emits the notice. | macOS, Linux | none |
| F-69 | `install_linux`: copy first with the F-02 routine, then accept the copy. | A file changed after acceptance in the source is not installed. | Linux | none |
| F-70 | No change until measured. | none | Windows by hand: the owner makes a junction inside the core's settings folder pointing at `%USERPROFILE%\Documents`, starts the browser, and checks that `Documents`' ACL gained no AppContainer ACE. If it did, `grant_to` changes to `SetSecurityInfo` with `PROTECTED_DACL` and no propagation, granted once at install. | `sandboxing-security.md` |
| F-71 | Engine qrkeyboard: report connected after the first frame that authenticates; `constant_time_equal` uses `subtle::ConstantTimeEq`. | "Connected" is not reported after a salt frame alone. | macOS, Linux (engine) | none |
| F-72 | `scripts/tools.sh` records each installed tool binary's SHA-256 in a tracked `tools.sha256`; `check.sh` refuses a mismatch. | Altering one tool binary makes `check.sh` refuse. | macOS, Linux | `DEVELOPMENT.md` tools section (common repo; the owner's process) |
| F-73 | `build-linux.sh`: rustup-init downloaded with a pinned version and SHA-256, packages pinned, refuses a dirty tree, and the engine passed in as a vendored source at the pinned commit; `build-windows.ps1` refuses a dirty tree. | Running on a dirty tree refuses. | Linux; Windows by hand (the dirty-tree refusal) | none |
| F-74 | Fetcher `Config { page_limit: protocol::MAX_PAYLOAD - 1, .. }` (by name), and `const _: () = assert!(DEFAULT_PAGE_LIMIT < protocol::MAX_PAYLOAD)`. | A body of exactly the engine limit reaches the core (probe case). | macOS, Linux | none |
| F-75 | Engine `fetch_received`/`push_received`: a complete head with status 100..200 other than 101 resets the collector and reading continues; a 1xx after the final head is a desync. | Probe D followed by a 200 gives the page. | macOS, Linux (engine) | none |
| F-76 | Engine `SseParser::value_byte`: an id holding a byte below 0x20, 0x7F or invalid UTF-8 is invalid, as NUL is. | Probe G sends no `Last-Event-ID`. | macOS, Linux (engine) | none |
| F-77 | Engine `push_events`: feed `step.data` before handling `step.done`. | Probe G's first run sets `last_event_id`. | macOS, Linux (engine) | none |
| F-78 | `address.rs`: the built canonical text is bounded to `MAX_ADDRESS`; `with_page` returns `Option`. | A 2046-byte address keeps its visit. | macOS, Linux | none |
| F-79 | Bookmarks `restore` computes the subtree's height and refuses an undo past `MAX_DEPTH` with a notice. | An undo past depth is refused, and the file stays readable. | macOS, Linux | none |
| F-80 | `recovered`: run `accept` with the signer; the newest complete version becomes the trial and the next older the current. `read_state`: treat `InvalidData` as a refused parse. `start`: a missing `versions/<current>` falls back to `recovered()`. | A garbage state rebuilds with a trial; a 3 KiB state is rebuilt. | macOS, Linux | `installation-and-updates.md` §14 |
| F-81 | Updater transport: a body bound by request kind (metadata `MAX_METADATA` by name, targets the manifest's length) and `REQUEST_DEADLINE` (named) per request. | A trickling server is cut at the deadline. | macOS, Linux | none |
| F-82 | Remove both module-wide `allow(clippy::undocumented_unsafe_blocks)`; one `// SAFETY:` per block, true for each. | Clippy for the Windows target is the test. | Windows by hand (Clippy in the VM, or on macOS if the target's standard library is already installed by `scripts/tools.sh`) | requirement 10.12 Verification (WP-8) |
| F-83 | Refuse `TabToWindow` between a private and an ordinary window. | The move is refused. | macOS, Linux | none |
| F-84 | Log lines of a private tab go only to its window's console. | An ordinary window's console shows none. | macOS, Linux | none |
| F-85 | `start_bookmark_reader`: kill the decoder after `BOOKMARK_READ_DEADLINE` (named) and report "Not imported". | A stand-in decoder that never answers yields the notice. | macOS, Linux | none |
| F-86 | Test only: assert `channel_text()` ends in `/` and that `/a` does not own `/a302.tti`. | (Expected to pass on old code; it documents the false positive.) | macOS | none |
| F-87 | Updater: feed the bytes the engine's `open_tunnel` returns into the TLS session. | Update through a proxy that sends its answer and the first TLS bytes together. | macOS, Linux | none |
| F-88 | `check.sh full`: grep the pinned engine source (the checkout at the pin) for `\bunsafe\b` outside comments and fail on a hit. | Gate step. | macOS | none |
| F-89 | `build.rs` files write `include_bytes!({:?})` of the path string. | Build with a path containing `"`. | macOS | none |
| F-90 | Engine to compare `descriptor.rs` push targets with its push requirements; no browser change. | Engine's decision. | engine | engine `web.md` |
| F-91 | Engine DBSC: bound registrations per origin per hour (named); refuse `include_site`. | Repeated registrations are refused past the bound. | macOS, Linux (engine) | engine `web.md` |
| F-92 | Engine: refuse close codes 1005, 1006 and 1015 when echoing; refuse duplicate DBSC members; `debug_assert!` and a const bound on `Writer::hex` widths. | Each case. | macOS, Linux (engine) | none |
| F-93 | Core updates: stamp the receipt of the updater's report with the broker's `LocalTime`. | The age uses the core's clock. | macOS, Linux | none |
| F-94 | WP-8 corrects the stale texts; WP-1 corrects the comment at macos.rs:10-12. | none | none | `CLAUDE.md`, `requirements.md` 10.12, `cookies.md` §7 |
| F-95 | WP-8 states the certificate gap. | none | none | `security-analysis.md`, `certificate-errors.md` |
| F-96 | Engine: store IPv6 host text in RFC 5952 form. | `[0:0:0:0:0:0:0:1]` and `[::1]` are one origin. | macOS, Linux (engine) | none |
| F-97 | Engine fuzz targets `contents`, `zxnet_message` and `ts_packets` (controlled PID, CC and adaptation). | The targets run in the engine's fuzz gate. | macOS (engine) | none |
| F-98 | Extend `hostile_tests.rs` with a broker stand-in, a start-page tab, bookmarks, two windows and a private tab; check hand-offs, bookmarks and decoder views. | The harness. | macOS, Linux | none |
| F-99, F-100 | None. | none | none | none |

---

## 3. Decisions taken while the owner is away

These are to be recorded in `docs/architecture.md` §2 at the next free decision numbers (85 is the last at 494aa91; take whatever is next when WP-8 commits), each marked "Taken while the owner was away", with "Now" set to "Owner to confirm", as decisions 80 to 82 were. Here they are D-1 to D-16. The principle throughout is the least privilege that keeps every helper working and can be verified on macOS or the Linux host.

| D | Finding | Options offered | Chosen | Reason |
|---|---|---|---|---|
| D-1 | F-01 | (a) drop `AF_UNIX` from network roles; (b) mount namespace for interface and sound; (c) `xdg-dbus-proxy` in front of the interface's bus | **(a) and (b), not (c)**. `DBUS_SESSION_BUS_ADDRESS` is removed from the interface, netlink is held to `NETLINK_ROUTE`, and `pidfd_getfd` is denied. | (c) adds a dependency to serve a need that does not exist: the only D-Bus user in the tree is `keyring` in the unconfined broker. (a) costs nothing, because glibc falls back to UDP DNS. (b) reuses the user namespace these roles already make. Everything is verifiable on the Linux host. The broker-connect design (A1 M-2) would also close (a), but it is larger (D-4). |
| D-2 | F-02 | refuse root links only; copy on Linux; copy on Linux and macOS | **Copy, accept the copy, then rename it, on Linux and macOS; also refuse root links and tidy `staging/metadata`.** | One routine closes all three mechanisms (symlink root, hard link, open descriptor) the three reports found. It is already proven on Windows (fc1e579). macOS's kernel code-signing covers code pages but not the bundle's other files. |
| D-3 | F-03, F-61 | broker-owned file dialog (allow-list by user choice); descriptor checks with a wider deny-list; content signature check; validate fetcher `Spawn` arguments and rate-limit spawns; broker confirmation for `OpenWeb` | **Descriptor-based no-follow opens; refuse the browser's own folders, every home dot-entry and the platform's application-data folders; return only bytes the engine's `detect` recognises (or a bookmarks file's fixed first line); one fixed refusal sentence; a broker-side `OpenWeb` interval. No `Spawn` argument validation. The broker-owned file chooser is recorded as the closing design, not built now.** | The file chooser needs native dialogs in the broker on three platforms (and a portal or GTK on Linux), plus a change to how file channels are opened (requirements). The chosen layers stop the reported reads with std calls verifiable on macOS and Linux. `detect` is the engine's recognition (requirement 2.1): bounded, fuzzed and free of `unsafe`. Running it on a file prefix in the broker is a deliberate, small addition to the unconfined process. Argument validation would not close the channel, since any data fits in a valid address, so it is not built. The residual (teletext-looking files, including any 960- or 1000-byte file) is documented. |
| D-4 | F-05 | macOS loopback deny; Linux: connect in the broker and pass the socket (closes Linux and H-1 for the fetcher); document | **macOS loopback deny now; Linux documented as a residual. Broker-connect is recorded as the planned design, needing its own design and security analysis.** | Broker-connect changes the broker protocol, the core's pipes to the fetcher and the fetcher's transport, and the repository's process requires a design with a security analysis for that. D-1 already removes the Linux escape. The residual is a compromised fetcher reaching the LAN, below the High findings. |
| D-5 | F-04 | AppContainer with no capabilities; restricting SIDs denying the AFD device; documentation only | **AppContainer with no capabilities. Implement, verify by hand on Windows.** | It matches every other role, closes the network and the file-read gap together, and Win32 app isolation shows AppContainer processes own windows. If the VM shows it cannot host the window, the engineer stops and the owner chooses; there is no fallback (decision 58). |
| D-6 | F-06 | stored floor file; start the loader from the stored `root.json` | **Floor file `staging/metadata/root-version`; the built-in root stays the anchor.** | Starting from a stored root would make a file the updater writes the trust anchor. The floor only refuses going back, so the chain is always verified from the built-in root. |
| D-7 | F-07 | sign the Windows manifest with the release key; a version mark in every program | **Sign the manifest with the existing Ed25519 release key, verified before Authenticode, sharing Linux's code.** | It covers every file, not only programs, and reuses a key and code that exist. It is testable on macOS. A mark per program would leave non-program files to a hash that the attacker writes. |
| D-8 | F-09 | A1's full redesign, including re-offering a deadline-only rollback after a number of days | **A `started` line, a start deadline then a health deadline, counting only after `started`, and one source for the time constants. No re-offer machinery.** | The two-phase deadline removes the slow-start cause. A version still marked bad is superseded by the next release, so re-offer logic adds state for little gain (the owner's rule against over-engineering). |
| D-9 | F-60 | require Landlock ABI 6 (signal scoping, Linux 6.12); seccomp by pid; document | **Seccomp: signals only to the process's own pid; `tkill` and the pidfd signal calls denied.** | It keeps today's kernel floor (Landlock 5, Linux 6.10) and is verifiable on the host. Raising the floor would cut users and is the owner's call. |
| D-10 | F-23 | root-owned installation in `/opt` with the profile there; avoid user namespaces; narrow the profile | **Narrow the profile to the four namespace-making programs at the real root; document the residual. The root-owned installation is recorded as the closing design.** | The namespaces are needed (F-01's mount namespace uses them), and `/opt` breaks decision 54's per-user updates. Narrowing removes the glob, and the administrator is told what the profile allows. |
| D-11 | F-18 | reword the document; host the phone's page apart from the relay | **Documentation now.** | qrkeyboard.com is not this repository's server (servers not owned are read-only). The effect is bounded by `interaction-security.md` §F. |
| D-12 | F-51 | refuse paths with `"`, `\` or controls; `sandbox-exec -D` parameters | **Parameters.** | The profiles are applied through `/usr/bin/sandbox-exec`, which takes `-D`. No user's path is refused. |
| D-13 | F-16 | re-check `may_submit` and re-run the confirmation for the new origin; convert to GET; refuse cross-origin 307/308 | **Refuse a 307 or 308 form redirect that leaves the submission's target origin.** | It is the least privilege and the simplest to verify. A same-origin 307 still works; a service that redirects a POST across origins is not a teletext form pattern. |
| D-14 | F-32 | a non-`Copy` key wiped with `write_volatile`; the `zeroize` crate; amend the documents | **Amend the documents.** | Wiping needs `unsafe` in the core (not allowed, requirement 10.12) or a new dependency, and an attacker who can read the core's memory already has its cookies. |
| D-15 | F-17 | resolve locally, then CONNECT to the checked address; widen the name list | **Widen `hidden_local`, and document that through a proxy the rule is by name.** | Resolving locally defeats the proxy's name privacy, which is why a user sets a proxy. |
| D-16 | F-20 | interface-side drop while a prompt is focused; core-side key filter; core refuses `Confirm` within the prompt delay after a phone key | **Core filters to the page-navigation keys; the interface sends phone keys to the page view only. No timing rule.** | The core filter is the decisive control and does not depend on the interface's code (decision 20). A timing rule is defeated by a keyboard that waits. |

Also recorded, without options to choose:

- **F-22 on Windows:** `DETACHED_PROCESS` with a relayed standard error, built only if the VM check shows console reach.
- **F-41:** refuse the shell-significant sub-delimiters rather than encode them.
- **F-64:** the relay override and local access only in debug builds.

**Documentation only:** F-18, F-32, F-94, F-95.

**Test or gate only:** F-86, F-88, F-97, F-98.

**False positives:**

- F-99: for the browser; the browser's core partitions jars by channel.
- F-86: probably. The page-file remainder must be digits plus an extension; the test confirms it.

**No change:** F-100.

**Severity changes:**

- F-61 is listed Low, although A1 rated its M-1 Medium as a combination. The read half is F-03 (High). Alone, the channel carries only what a compromised core can already send through any fetcher it starts.
- F-82 is raised from Info to Low. It breaks the owner's rule against blanket suppression and requirement 10.12's Verification.
- F-19 is listed Medium; A1 called it "Medium-low" under its Medium heading.

---

## 4. Work packages

**Restructuring first.** Every package touches files that the restructuring moves now: `structure/core` (cookies, history and the tests), `structure/interface-core` (`browser.rs`), `structure/protocol` (protocol's root and `interface/`), and `structure/sandbox` (confine's `lib.rs` split into its concepts, and the broker split into wire, client and server). The fixes are applied **after those branches merge, against the new file layout**. That is why each package lists items by function, type or constant: the file:line references in section 1 are at the reviewed commits only.

**Rules for every package:**

- Engine work follows the engine's own process; the browser's pin is then moved once (WP-10), as `DEVELOPMENT.md` section 11 says.
- Every package runs `scripts/check.sh full`.
- Documentation edits are WP-8's only.
- Each package's commits cite the decision (D-n, by its recorded number).

**Shared items.** Packages are file-disjoint except for these, where the owner of each item is named:

- `core/src/main.rs` `broker()`: its first statement (the `started` line, through `updates::tell_launcher_started`) is WP-2's; everything else in `main.rs`, including the `open_web` closure and `read_for_core`, is WP-3's. Land WP-2's statement on its own commit.
- `core/src/updates.rs`: WP-2's only (F-09 constants, F-93).
- `native/Cargo.lock`: WP-3 adds `neoteletext-formats` to the core and WP-10 moves the pin; whichever lands second regenerates the lockfile.
- `protocol/src/keyboard.rs`: WP-5's (F-28, and the F-20 navigation key list); WP-3 uses the list by name and lands after WP-5.

### Order

| Order | Package | Highest | Why here |
|---|---|---|---|
| 0 | WP-8 docs: decisions | (records D-1 to D-16) | Code commits cite the decision numbers. |
| 1 | WP-1 browser confine | High (F-01, F-04) | The sandbox escape. |
| 2 | WP-2 browser launcher, update, tuf, release-identity, installer, os-install, release scripts | High (F-02) | Persistent unconfined code. |
| 3 | WP-3 browser core | High (F-03) | The broker read. |
| 4 | WP-6 engine web | Medium (F-13 to F-17) | Needs WP-10 to reach the browser. |
| 5 | WP-5 browser protocol, interface, interface-core, keyboard, sound, dock-menu, web-opener | Medium (F-20b, F-26b) | Before WP-3's F-20a. |
| 6 | WP-7 engine core and qrkeyboard | Low | |
| 7 | WP-4 browser fetcher | Low | |
| 8 | WP-9 gates and tools | Low | |
| 9 | WP-10 engine re-pin | (carries WP-6 and WP-7) | After the engine merges. |
| 10 | WP-8 docs: everything else | Medium (F-18) | Text for what the code packages built. |

WP-5 can run in parallel with WP-1 to WP-3, because its files are disjoint. Only WP-3's F-20a waits for WP-5's key list.

### WP-1: browser confine (sandbox layers)

**Files:** confine's Linux, macOS, Windows and Unix-descriptor modules and its environment table (after `structure/sandbox`: the modules that hold `families`, `network_namespace`, `landlock`, `seccomp`, `apply`, `profile`, `preamble`, `SYSTEM_READS`, `spawn`, `container`, `environment_block`, `send`/`receive`, `ENVIRONMENT_WINDOW`, `ENVIRONMENT_CORE`), and `confine/tests/probe.rs`. Not the broker modules.

**Items, by severity:**

1. **F-01:** `families`, `seccomp` netlink rule and `pidfd_getfd`, `network_namespace` plus a new `private_runtime`, `ENVIRONMENT_WINDOW`.
2. **F-04:** `spawn` interface branch, `container` (verify by hand on Windows).
3. **F-05:** `profile` `Role::Network` loopback deny.
4. **F-21:** x32 filter in `seccomp`.
5. **F-22:** `ioctl` rule in `seccomp`.
6. **F-34a:** `PR_SET_PDEATHSIG` in Linux `apply`.
7. **F-51:** SBPL parameters in `preamble` and `profile`.
8. **F-52:** `SYSTEM_READS`, launchservices probe.
9. **F-56, F-57:** `send`, `receive`.
10. **F-58, F-59:** `environment_block`, attribute list (Windows by hand).
11. **F-60:** signal rules in `seccomp`.
12. **F-64b:** `ENVIRONMENT_CORE` debug-only.
13. **F-70:** measure only (Windows by hand).
14. **F-82a:** confine Windows `SAFETY` comments.
15. **F-94 (comment):** the stale macOS module comment.

**Verify:** Linux host for items 1, 5, 6, 11 and 4; macOS for 3, 7, 8 and 9; the Windows items by hand.

### WP-2: browser launcher, update, tuf, release-identity, installer, os-install, release scripts

**Files:** `launcher/` (`Launcher::accept`, `copy_in`, `prepare`, `candidates`, `tidy`, `run`, `read_state`, `recovered`, `start::start`, the health line reader, `end_whole`, `install_linux`, `--uninstall`, `macos::reconcile`, `move_old_current`, `install::launcher_release`, the printed AppArmor profile); `update/` (`accept::accept`, `own_files`, `Keys`, `files::copy_tree`, `files::list_files`, `layout` constants, `state::Trial`); `tuf/updater/` (`Config::load`, transport); `tuf/release/` (`package`, `check`); `release-identity/build.rs`; `installer/`, `stub/`, `os-install/`; `scripts/release/`; and the shared items `broker()`'s first statement and `core/src/updates.rs`.

**Items, by severity:**

1. **F-02:** `accept`, `copy_in`, root-link refusal, `tidy`, `launcher_release`.
2. **F-06:** root-version floor.
3. **F-07:** Windows manifest signature (by hand on Windows end to end).
4. **F-08:** no `mark_bad` on refusal, `MAX_CANDIDATES_PER_START`.
5. **F-09:** `started` line, two-phase `start`, `Trial` fields, constants.
6. **F-19:** macOS `reconcile`.
7. **F-23:** AppArmor profile.
8. **F-24:** test identity.
9. **F-25:** DLL search (by hand on Windows).
10. **F-34b:** process group kill after a broker exit.
11. **F-47:** health line reader.
12. **F-48:** `--uninstall`.
13. **F-49:** clock guard.
14. **F-50:** `copy_tree` bounds.
15. **F-69:** `install_linux`.
16. **F-80:** recovery.
17. **F-81:** updater transport bounds.
18. **F-82b:** os-install `SAFETY` comments.
19. **F-87:** updater proxy bytes.
20. **F-89:** build.rs paths.
21. **F-73:** `build-linux.sh`, `build-windows.ps1`.
22. **F-93:** receipt stamp in `core/src/updates.rs`.

**Order inside:** F-02 then F-50 (it uses the bounded copy), then F-08 and F-09 together (both in `prepare`), then the rest.

**Verify:** macOS and Linux launcher tests and `scripts/updates-e2e.sh` on both; the Windows items by hand.

### WP-3: browser core (including the broker-side handlers)

**Files:** `core/src/` except `updates.rs` and `broker()`'s first statement. Items: `read_for_core` and its rule function, `Source::read`, `import_bookmarks`, the reader threads and `run`'s event channel, a new `budget` module, `Frames`, `decoder_ended`, `FetcherEnded`, `phone_said`, `phone_panel`, `cookie_reply`, `Store::import`, `match_decoders`, the strict readers' `dropped` lists, the private writer and settings writer, restore and session (`kept_address`), `address` (`with_page`), bookmarks `restore`, `links::Asking`, `opened`, the `open_web` closure, the phone keyboard spawn, `TabToWindow`, the log routing, `start_bookmark_reader`, `hostile_tests`; plus `core/Cargo.toml` (adds `neoteletext-formats`).

**Items, by severity:**

1. **F-03:** the broker read.
2. **F-10:** inbound budget.
3. **F-11:** frame interval (the engine constant may need WP-6 first; if it is missing, WP-3 waits for it).
4. **F-12:** helper exits.
5. **F-20a:** phone key filter (after WP-5's key list).
6. **F-26a:** `phone_panel`.
7. **F-27:** `ReachedQuestion`.
8. **F-30:** decoder back-off.
9. **F-31:** dropped lists.
10. **F-33:** cookie import tags.
11. **F-35:** settings writes.
12. **F-53:** file tabs.
13. **F-61:** `OpenWeb` interval.
14. **F-64a:** relay override debug-only.
15. **F-65, F-66, F-67, F-68:** interface-boundary items.
16. **F-78:** address length.
17. **F-79:** bookmark undo depth.
18. **F-83, F-84, F-85:** Info items.
19. **F-86:** test.
20. **F-98:** harness.

**Verify:** macOS and Linux; F-03's Windows checks by hand.

### WP-4: browser fetcher

**Files:** `fetcher/` (`reach`, `Tcp`/`Link` in transport, `Config` in main).

**Items:**

1. **F-62:** pre-connect address check.
2. **F-63:** one connect deadline, cancellable close.
3. **F-74:** page limit below `MAX_PAYLOAD`.

**Verify:** macOS, Linux.

### WP-5: browser protocol, interface, interface-core, keyboard, sound, dock-menu, web-opener

**Files:** `protocol/` (`clean_name`, `Fields::key`, `write_to_decoder`, the phone navigation key list), `interface/` (`phone_key`, paste), `interface-core/` (`editor::hidden`, `clean`, `link_ui` phone handling), `keyboard/` (stdin watcher, error line), `sound/` (`audio.rs` mixers), `dock-menu/` (crate root, `mac.rs`), `web-opener/` (`acceptable`).

**Items:**

1. **F-20b:** the interface sends phone keys to the page view only, and the navigation key list is added in protocol.
2. **F-26b:** the keyboard watches stdin first.
3. **F-28:** `clean_name`.
4. **F-29:** `Fields::key`.
5. **F-36:** `hidden`.
6. **F-37:** dock-menu lints.
7. **F-40:** keyboard error line.
8. **F-41:** web-opener.
9. **F-54:** paste.
10. **F-55:** sound mixers.

**Verify:** macOS and Linux; F-41, F-54 and F-55 also by hand on Windows.

### WP-6: engine web (`crates/neoteletext-web`)

**Files:** `cookie.rs`, `agent.rs` (and `agent/bound.rs`), `dbsc.rs`, `proxy.rs`, `channel.rs`, `http.rs`, `sse.rs`, `ws.rs`, `url.rs`, `consts.rs`, the engine's web requirements.

**Items:**

1. **F-13:** cookie import.
2. **F-14:** DBSC identifier.
3. **F-15:** push cookie scope.
4. **F-16:** form 307/308.
5. **F-17:** proxy names.
6. **F-42:** fetch scope outside the channel.
7. **F-43:** `SECURE_HOSTS`.
8. **F-44:** empty `Location`.
9. **F-45:** `is_inside`.
10. **F-75:** 1xx.
11. **F-76:** `Last-Event-ID`.
12. **F-77:** final SSE step.
13. **F-91, F-92:** DBSC churn, minor strictness.
14. **F-96:** IPv6 text.
15. **F-90:** review only.
16. **F-11 support:** if no engine constant exists for the fastest legitimate change, add it with its EN 300 706 citation.

**Process:** the engine's own (its gate, its requirement documents); then WP-10. **Verify:** macOS and Linux (engine full gate).

### WP-7: engine core and qrkeyboard (`crates/neoteletext-core`, `crates/neoteletext-qrkeyboard`, fuzz)

**Items:**

1. **F-46:** blocked ranges in `policy`.
2. **F-38:** `FromPhone::Up`.
3. **F-39:** owner token.
4. **F-71:** connected after authentication, `subtle`.
5. **F-97:** fuzz targets `contents`, `zxnet_message`, `ts_packets` (the formats crate is touched only by new fuzz targets; no formats defect was found).

**Verify:** macOS and Linux (engine full gate).

### WP-8: documentation (browser `docs/`, project `CLAUDE.md`, engine docs by the engine's process)

**Part 0, first:** record D-1 to D-16 in `architecture.md` §2.

**Part 10, after the code:**

- **F-18:** `interaction-security.md`.
- **F-32:** `cookies.md`, `cookies-security.md`.
- **F-94:** `CLAUDE.md` unsafe list; requirement 10.12 Verification (also F-82); `cookies.md` §7 cipher.
- **F-95:** certificate gap in `security-analysis.md`, `certificate-errors.md`.
- The text for every finding whose "Changes to" names a document:
  - F-01: `sandboxing.md`, `sandboxing-security.md` §2 and §5, `security-analysis.md` §5;
  - F-02, F-06, F-07, F-08, F-09, F-12, F-19, F-23, F-24, F-25, F-49, F-80: `installation-and-updates.md`, `installation-and-updates-security.md`, and decision 80 amended;
  - F-03, F-61: `security-analysis.md` §16 rank 4, `sandboxing-security.md`, and the requirement for file channels;
  - F-04, F-05, F-21, F-22, F-34, F-51, F-52, F-60, F-70: `sandboxing.md`, `sandboxing-security.md`, `security-analysis.md` §5.1, requirement 5.10 Verification;
  - F-11: `architecture.md` §10;
  - F-17: `security-analysis.md` §7;
  - F-20: `interaction.md`, `interaction-security.md`, decision 46's departures;
  - F-27: `cookies-security.md`;
  - F-41: `hyperlinks-security.md`;
  - F-53: `history-and-bookmarks.md`;
  - F-64: `CLAUDE.md`.
- Engine documents (`sec.md`, `web.md`) are edited inside WP-6 and WP-7 under the engine's process, not here.

### WP-9: gates and tools (`scripts/check.sh`, `scripts/tools.sh`)

**Items:**

1. **F-72:** tool hashes.
2. **F-88:** engine `unsafe` grep.
3. **F-24's script check** (the dry-run refusal) if it is not kept with WP-2's scripts.

**Verify:** macOS and Linux. F-72 also touches `DEVELOPMENT.md` in the common repository; that edit follows that repository's process.

### WP-10: engine re-pin

Move the pin to the engine commit carrying WP-6 and WP-7, in all three workspaces (`check_engine_pin` holds them to one revision). Run the full gate on macOS and Linux, then let the owner build and run once in the Windows VM.

---

## 5. Not covered

- **A2's findings**, including the fuzz crashes in `A2/crashes/tti_enhancement` and `A2/crashes/bookmarks_file`. They must be merged when `A2-tool-driven-review.md` exists. The TTI enhancement crash would be an engine formats or core finding, contradicting A4's "no defect found" in formats and core, so it may need a WP-7 item.
- **Measurements:** none of the kernel- or OS-dependent claims (F-01, F-04, F-21, F-22, F-60, F-70, F-52's launchservices) were measured by the reviews. Each fix's test is the measurement and must be run before the fix is called done.

## Addendum: the tool-driven review (A2), merged 24 October 2026

`A2-tool-driven-review.md` reported after this plan was written. Its findings are added here with the next numbers; its proposed patches are in `A2-patches/`.

| Id | Severity | Repository / crate | Item | Defect | Fix | Package |
|---|---|---|---|---|---|---|
| F-101 | Medium (blocks the push gate) | browser / `native/Cargo.lock`, `native/fuzz/Cargo.lock` | `ctutils` 0.4.3 (RUSTSEC-2026-0385) via `secret-service` ← `keyring`; yanked `clipboard-win` 5.4.1 | `cargo deny check` fails, so `scripts/check.sh full` fails; the vulnerable MAC verification is not reached | `cargo update -p ctutils -p clipboard-win` in both workspaces | done on `main` before the merges |
| F-102 | Low | engine / `neoteletext-formats` | `TtiReader::packed_line` | an X/28 line on a page already holding `RAW_PACKETS` packets sets the page function and coding although the packet is dropped, so write-then-read changes the page | store the packet first; return on capacity failure before setting the function (`A2-patches/tti.diff`); the `tti_enhancement` fuzz reproducer as a unit test | WP-7 |
| F-103 | Low | engine / `neoteletext-formats` | `TtiReader::description`, the `FT` arm of `TtiReader::command`, `TtiReader::set_text` | a value cut to capacity can end in a carriage return, which the writer writes and the next read drops | one helper that cuts, then trims trailing CRs; reproducer 63 × `a` then `\rxyz` | WP-7 |
| F-104 | Low | browser / `core` | `Bookmarks::text`, `Bookmarks::read` | the file is written in tree order but read in file order, so write, read, write is not stable; the `bookmarks_file` fuzz target fails within seconds and can turn the full gate red | number lines in the order `text()` writes them (`A2-patches/bookmarks.diff`); the 52-byte reproducer as a unit test | WP-3 |
| F-105 | Info (hardening) | browser / `interface-core`, `draw-vello`, `draw-embedded` | crate roots | no no-panic deny list; none of the 1,900 strict-lint hits is reachable from untrusted input | add the list to the three roots and to `NO_PANIC_ROOTS` once the restructuring has merged, fixing each hit by bounding it; add `string_slice` to every list | WP-9 |
