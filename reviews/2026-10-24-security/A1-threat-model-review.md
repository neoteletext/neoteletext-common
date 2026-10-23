# A1: threat-model-driven review of neoteletext-browser and neoteletext-engine

Reviewed read-only on 23 and 24 October 2026: the browser at `main` 494aa91 (`native/`) and the engine at `implementation` e7d8927. The browser pins the engine at fb2dd8a, which differs from e7d8927 only in three small `no_std` `Debug` changes (agent.rs, cookie.rs, dbsc.rs), so every engine finding applies to the pinned code. Nothing was modified and nothing was run. Every finding comes from reading the code. Where a claim depends on kernel or OS behaviour that was not tried on a host, the finding says so.

Method: I read the threat documents first: engine `THREAT-MODEL.md`, `SECURITY.md`, `docs/spec/requirements/sec.md`; browser `security-analysis.md`, `sandboxing*.md`, `cookies-security.md`, `hyperlinks-security.md`, `interaction-security.md`, `installation-and-updates-security.md`, `certificate-errors-security.md`, `menu-bar-security.md`, `history-and-bookmarks-security.md`, `settings-home-console-proxy-security.md`, and `architecture.md` section 6. I then read the code on both sides of every boundary those documents name. Five sub-reviews ran in parallel (engine web parsers; core disk formats and sealing; protocol and core dispatch; launcher and updater; keyboard, unsafe code and sound). I reviewed the TLS path, the proxy reader, `confine` (all platforms) and the broker myself. Before including the sub-reviews' main findings I checked them against the code; the ones checked are marked **[verified]**.

File and line numbers are as of the commits above. Each finding also names the function, because files will move.

Which crate roots deny `clippy::arithmetic_side_effects`, `indexing_slicing`, `unwrap/expect/panic`:
- **Browser:** every crate that reads outside input (protocol, core, confine, fetcher, decoder, interface, sound, keyboard, update, launcher, tuf/updater, web-opener). `dock-menu` has none of them (L-12).
- **Engine:** neoteletext-core, -formats, -web, -input, -audio, -audio-mix, -slicer, -image, -qrkeyboard. `crypto.rs:236` allows arithmetic narrowly, for P-256 group operations.
- **Release profiles:** neither workspace sets `overflow-checks`, so the lints are the only overflow guard.

---

## Summary, ranked

| # | Sev | Boundary | One line |
|---|---|---|---|
| H-1 | **High** | Linux sandbox: fetcher, keyboard, updater, interface, sound | `AF_UNIX` is allowed and nothing hides `/run/user/$UID`, so these helpers can reach the session D-Bus (systemd user manager: run any program unconfined), ssh-agent, gpg-agent and the Secret Service. A compromised fetcher escapes the sandbox. |
| H-2 | **High** | Updater → launcher (Linux) | A staged folder that is a symlink passes acceptance and is *renamed as the link*, so the installed version stays in the updater-writable tree and a later updater turns it into a persistent unconfined launcher. **[verified]** |
| M-1 | Medium | Core → broker | `Read` uses a short denylist that a symlink swap inside the settings folder can bypass. Spawned fetchers take any URL argument. Together: a compromised core reads the user's files and sends them out. |
| M-2 | Medium | Fetcher sandbox, macOS and Linux | Nothing outside the engine's own in-process check stops a compromised fetcher (or keyboard) connecting to loopback and the LAN. REQ-SEC-006 rests on the code that was compromised. Windows does enforce it. |
| M-3 | Medium | Update host → updater | The TUF client always starts from the built-in root and never enforces a floor on the highest root version it has seen, so a host holding rotated-away root keys can roll clients back to them. |
| M-4 | Medium | Updater → launcher (Windows) | The manifest is not covered by any platform signature: signed programs from different releases can be mixed under a new version. |
| M-5 | Medium | Updater → launcher | A refused staged folder marks its *version number* bad, so one write to `staging/` freezes updates indefinitely. |
| M-6 | Medium | Launcher health (coordinator's question) | Two independent clocks (the core's 30 s window, the launcher's 45 s deadline), and "not yet started" counts as "failed". A slow machine rolls back a good version, marks it bad and never offers it again. The failing test is the same effect. |
| M-7 | Medium | Helpers → core | The core's inbound event queue is unbounded: one compromised decoder or fetcher can drive the trusted core out of memory. **[verified: `main.rs:2243` `mpsc::channel()`]** |
| M-8 | Medium | Decoder → core → interface | No per-page frame-rate bound. A decoder alternating two images fills the interface outbox, which ends the browser. |
| M-9 | Medium | Version health | A decoder or fetcher that exits (including one that cannot confine itself) is not counted as a health failure, so a broken release commits. **[verified]** |
| M-10 | Medium | Disk → core (engine cookie jar) | The first expired or over-long record in `cookies.bin` silently ends the import, so every later cookie is lost. **[verified: `cookie.rs:722,735,687`]** |
| M-11 | Medium (engine; not compiled into the browser) | Server → request headers | The DBSC `session_identifier` goes into `Sec-Secure-Session-Id` unescaped for CR/LF: header injection and request smuggling on the kept-alive connection. **[verified]** |
| M-12 | Medium (engine/`neottx`; the browser's core re-scopes) | Push server → cookie jar | Cookies set by the push handshake are not narrowed to the channel folder (REQ-WEB-026). **[verified]** |
| M-13 | Medium (design/doc) | Relay → phone | The relay serves the phone's JavaScript, so "a hostile relay cannot read keys" is false against the operator. |
| M-14 | Medium-low | Updater → launcher (macOS) | `previous/` is filled from any staging entry carrying the current version's mark, and a rollback swaps it in with no signature check. |
| L-1 … L-32 | Low | various | Listed below. |

---

## High

### H-1. Linux helpers can reach the user's session services over `AF_UNIX`: a sandbox escape (not run on a host)

- **Boundary:** a compromised fetcher, keyboard or updater (attacker 1 or 2 through a fault in a network parser), or a compromised interface or sound helper, reaching the user's account.
- **Where:**
  - `native/confine/src/linux.rs:50-61` `families`: `Network` and `Updater` get `AF_UNIX`; `Interface` and `Sound` get `AF_UNIX`.
  - `linux.rs:146-175` `landlock`: Landlock ABI 5 has no right covering `connect(2)` to a *pathname* UNIX socket.
  - `linux.rs:308-311` `apply`: the network roles get no network namespace. The interface and sound helper get one, which only hides *abstract* sockets.
  - `confine/src/lib.rs:246-265` `ENVIRONMENT_WINDOW`: passes `DBUS_SESSION_BUS_ADDRESS` and `XDG_RUNTIME_DIR` to the interface.
  - `linux.rs:73-96` `network_namespace`: maps the uid to itself, so `SO_PEERCRED` shows the real user (done on purpose for PipeWire).
- **Mechanism:** nothing stops a confined helper calling `connect("/run/user/$UID/bus")` (the systemd user bus), `/run/user/$UID/systemd/private`, `/run/user/$UID/gnupg/S.gpg-agent`, `/run/user/$UID/keyring/ssh` and any `SSH_AUTH_SOCK` path. These paths are fixed, so no directory read is needed. D-Bus `EXTERNAL` authentication succeeds because the uid is real. Over the bus:
  - `org.freedesktop.systemd1.Manager.StartTransientUnit` (what `systemd-run --user` does) runs any command as the user, with no sandbox at all.
  - `org.freedesktop.secrets` returns the browser's cookie key and every unlocked secret of the user.
  - ssh-agent signs with the user's keys, which the fetcher can then use over its own network access.
- **Documentation:** `sandboxing-security.md` §2 row "An `AF_UNIX` socket reaches a service the helper should not (D-Bus, the display)" answers "what they reach is then the service's own access control", and §5 rates Linux low. For the session bus that access control is "same uid may do anything", so the property of decision 20 ("a compromised helper gains nothing beyond its pipe") does not hold on Linux for the fetcher, the most exposed process.
- **What an attacker needs:** code execution in the fetcher (an engine reader fault reached from a server or a network path) or in the interface or sound helper.
- **Effect:** full compromise of the user's account on Linux.
- **Not tested on a host.** The reasoning rests on Landlock ABI 5's documented rights and systemd's standard user-bus policy. Confirm with a probe in `confine/tests/probe.rs` that connects a confined `Network` role to `$XDG_RUNTIME_DIR/bus`. It should be refused, and today I expect it to succeed.
- **Fix:**
  1. *Network roles:* drop `AF_UNIX` from `families(Role::Network | Role::Updater)`.
     - Name resolution then needs no NSS socket. Either resolve in the broker (a `Resolve` request returning addresses, after which the fetcher reports the peer as now), or give the fetcher a resolver that reads `/etc/resolv.conf` and speaks UDP DNS. The second is a library choice for the owner.
     - Keep `AF_NETLINK` only if glibc's `getaddrinfo` stays.
  2. *Interface and sound:* they already make a user namespace, so add `CLONE_NEWNS` to the `unshare` in `network_namespace`. Then mount a `tmpfs` over `/run/user/$UID` and `/tmp`, and bind-mount back only the sockets the role needs: `wayland-0`, `.X11-unix/X0` and the Xauthority file for the interface; `pipewire-0` and `pulse/native` for sound. Then apply Landlock and seccomp as now. Set `DBUS_SESSION_BUS_ADDRESS` only if the input method needs it, and in that case put an `xdg-dbus-proxy` filter in front of it, as Flatpak does (a new dependency, the owner's decision).
  3. Add `SYS_pidfd_getfd` to the seccomp deny-list. Landlock's ptrace scoping covers it today; the deny is cheap defence in depth.
  4. Add the probe test above for each role, so the test fails on today's code.

### H-2. Linux: a symlinked staged folder is accepted and renamed as the link **[verified]**

- **Boundary:** the confined updater reaching the unconfined launcher. This breaks the design's central claim, "a compromised updater can stage files but not get them run".
- **Where:**
  - `native/launcher/src/lib.rs:332-345` `Launcher::accept` (Linux and Windows arm): `let from = if staged.is_dir() { staged } else { installed.clone() };` then `update::accept::accept(&from, …)` and `std::fs::rename(&from, &installed)`.
  - `update/src/files.rs:174-190` `list_files`: refuses links only *below* the root. `read_dir(folder)` follows a root that is a link.
  - `update/src/accept.rs:111-114`: checks `folder.file_name()`, which is the link's own name.
  - `lib.rs:388` `tidy`: never cleans `staging/metadata`.
- **Trigger:**
  1. A compromised updater (Landlock grants it `MakeSym` on staging, `linux.rs:166`) copies the genuine, dual-signed 0.3.0 into `staging/metadata/x/` and makes `staging/0.3.0` a symlink to it.
  2. At the next start the signatures pass (the files are real), `rename` moves *the link* to `versions/0.3.0`, and the trial runs out of `staging/metadata/x/`.
  3. The next updater, re-exploited during the trial, rewrites `neoteletext-launcher` there before `commit()` → `install::launcher_release` copies it into `bin/`. The result is a persistent, unconfined attacker launcher. Helpers that are not running at that moment can be replaced the same way and simply never call `confine::apply`.
- **Windows** is safe: `copy_in` copies and re-checks. **macOS:** see M-14.
- **Fix:**
  - Refuse a root that is a symlink: `std::fs::symlink_metadata(&staged)?.file_type().is_symlink()` → error.
  - On Linux too, copy the version into `versions/<v>.copying` with `files::copy_tree` and re-run `accept` on the copy before the rename, as Windows does. That also closes L-9.
  - Limit what `tidy` keeps under `staging/metadata` to tough's own file names.
  - Test: a staging root that is a symlink to a genuine version must be refused.

---

## Medium

### M-1. Broker `Read`: a denylist, a symlink race, and an exfiltration path through spawned fetchers

- **Boundary:** a compromised trusted core using the broker (boundary 10).
- **Where:**
  - `native/core/src/main.rs:2359-2362` `SECRET_FOLDERS`, and `2397-2406` `read_for_core`: `canonicalize`, prefix check, then `Source::read(&canonical)`, which re-resolves the path with `fs::metadata` and `File::open`.
  - `confine/src/broker.rs:849-866`: `Spawn` passes any argument of up to 4,096 bytes to a fetcher.
- **Problems:**
  1. **The denylist is short.** It does not cover `~/.netrc`, `~/.git-credentials`, `~/.config/gh/hosts.yml`, `~/.cargo/credentials.toml`, `~/.npmrc`, `~/.pgpass`, `~/.mozilla`, `~/.config/google-chrome`, `~/Library/Application Support/Google/Chrome`, `~/.local/share/keyrings`, `~/Documents`, or the other browsers' profiles. A denylist cannot list every credential file.
  2. **The check and the open resolve the path separately.** `canonicalize` is checked, then `Source::read` opens by path again. The core may create symlinks and folders in its settings folder, so an intermediate component of the canonical path can change between the two.
  3. **Spawned fetchers take any channel address.** A compromised core is not cut off from the network: whatever it reads, it can pass on in a fetcher's arguments.
- **Matters when:** the trusted core is compromised, the case decision 56 confines it against. `security-analysis.md` §16 rank 4 says such a core gets "not the user's files or the network". With these three points together that is not so.
- **Fix:**
  - Use an allowlist, not a denylist. The broker should read only a file the user chose in a broker-owned file dialog, or one named on the command line at start. If a free path must stay, at least refuse every dot-folder under home, the browser's own settings and update folders, and anything that does not begin with a teletext format's signature (TTI command lines, T42 packet sizes, transport-stream sync bytes).
  - Open without following links and check the descriptor, not the path:
    - Linux: `openat2(…, RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS)`.
    - macOS: `O_NOFOLLOW_ANY`.
    - Windows: `FILE_FLAG_OPEN_REPARSE_POINT`, then `GetFinalPathNameByHandleW`.
    - Then apply the folder rules to the descriptor's real path, read from that descriptor, and in folder mode use `openat` relative to the folder's descriptor.
  - Bound the exfiltration path: the broker checks that a fetcher's first argument parses as an `http`/`https`/`ws(s)` channel address the core's address rules accept, and limits fetcher spawns per minute. This narrows the path; only the user choosing the file closes it.

### M-2. The fetcher's local-network rule is not enforced by the macOS or Linux sandbox

- **Boundary:** a compromised fetcher or keyboard reaching loopback and the LAN (engine REQ-SEC-006; browser requirement 5.10).
- **Where:**
  - `native/confine/src/macos.rs:55-61` `profile`, `Role::Network`: `(allow network-outbound (remote tcp "*:*") …)`.
  - `confine/src/linux.rs:150-152` `landlock`: TCP is not handled for `Role::Network`.
  - `linux.rs:308` `apply`: no network namespace for network roles.
  - The engine's check (`agent.rs:1527-1538` `fetch_connected`, `peer_blocked`) runs inside the process being defended against.
  - Windows holds: an AppContainer without `privateNetworkClientServer` cannot reach the LAN or loopback (`windows.rs:655-660`).
- **Matters when:** a fetcher is compromised. The threat model's asset "the user's local network" then rests only on that compromised code.
- **Fix:**
  - macOS: when `spawn.local_network` is false, add `(deny network-outbound (remote ip "localhost:*"))` after the allow. SBPL cannot name private ranges, so record the LAN as a residual on macOS.
  - Linux: do the connect in the broker. The fetcher asks the broker to connect to host and port; the broker resolves the name, checks the address against the engine's `is_blocked` and the allowed list, connects, and passes the socket over the existing `SCM_RIGHTS` path. The fetcher can then run in an empty network namespace with no `AF_INET` at all, which also removes `AF_UNIX` and `AF_NETLINK` and closes H-1 for this role. This is an architectural change for the owner to decide.
  - Until then, say in `security-analysis.md` §5.1 that on macOS and Linux the local-network rule holds only while the fetcher is not compromised.

### M-3. The TUF client never refuses a root older than one it has reached

- **Boundary:** update host → updater (threat 2 and threat 3).
- **Where:** `native/tuf/updater/src/lib.rs:115-125` `Config::load`: `RepositoryLoader::new(&self.root, …)` always starts from `release_identity::TUF_ROOT` (`main.rs:59-66`). tough walks `N+1.root.json` until the first failure and saves the result, but nothing compares the result with the highest root version reached before.
- **Matters when:** a root key set has been rotated away (after a compromise or a loss), and the update host fails the newer root files on purpose. The client then trusts the old keys again until the built-in root expires.
- **Fix:** after `load()`, read `repository.root().signed.version` and compare it with a `root-version` file the updater keeps in `staging/metadata`. Refuse a lower version, and write the new value after success. Better still, start the loader from the stored `root.json` when its version is above the built-in one. Test: a repository whose `2.root.json` answers 404 after the client has seen version 2 must be refused.

### M-4. Windows: the manifest is not covered by a signature

- **Boundary:** updater → launcher (Windows).
- **Where:** `native/os-install/src/windows.rs:142-149` `WindowsSigner::check`: Authenticode is checked on each program, and the `_manifest` argument is ignored. `update/src/accept.rs:100-109`: only the broker's version mark is compared with the manifest.
- **Matters when:** the staging folder is written by a compromised updater or another program of the user. Programs that the pinned key signed for different releases can then be combined into one "version".
- **Fix:** sign the manifest with the release key on every platform, as Linux already does (`manifest.sig`, Ed25519, verified with `ring` before the platform check). At the least, put a `version_mark!` in every program and check each one against `manifest.version` in `accept`.

### M-5. A refused staged folder marks its version number bad

- **Boundary:** updater, or another program of the user, → launcher.
- **Where:** `native/launcher/src/lib.rs:274-279` `prepare`: `Err(why) => { state.mark_bad(candidate); remove_tree(staged) }`. `candidates()` (`lib.rs:301-316`) takes any folder name that parses as a version. `update/src/state.rs` `mark_bad` evicts the smallest versions once past `MAX_BAD`. `core/src/updates.rs:299-303` `offer` never offers a bad version.
- **Matters when:** folders that are not genuine versions appear under `staging/`. The genuine releases with those numbers are then never offered or accepted. Junk with large numbers can also evict a genuinely bad version from the list, so it is tried again.
- **Fix:** keep "bad" for trials that failed to start. When a staged folder is refused, delete it and leave `bad` alone. If a memory of refusals is wanted, key it by the manifest's SHA-256, not by the version, and limit how many folders are examined per start.

### M-6. The health deadline and trial counting roll a good version back on a slow machine

This is the coordinator's question; the full answer is in the "Health deadline" section below.

- **Where:**
  - `native/launcher/src/lib.rs:64` `HEALTH_DEADLINE` (45 s, counted from spawn).
  - `launcher/src/start.rs:53-67` `start`: a timeout kills the process group and returns `healthy: false`.
  - `lib.rs:178-182` `run`: a killed trial is `!success`, so it is retried and counted again within the same start.
  - `lib.rs:287-292` `prepare`: the count is incremented before the start; at 2 the version is rolled back and `mark_bad`.
  - `core/src/updates.rs:30,106-112` `Health::healthy`: the core's own 30 s `HEALTH_WINDOW`, counted from the core's start, with no deadline of its own.
- **Effect:** when the machine is slow to start a new version (first-launch code checks, antivirus scanning new executables, a loaded disk), a healthy version is killed twice and marked bad for good. A version that starts and is quit quickly counts the same way (the `quiet` path). A missed rollback does not arise, because counting happens before the start and is written first.
- **Fix:** see the "Health deadline" section.

### M-7. The core's inbound event queue is unbounded **[verified]**

- **Boundary:** decoder, fetcher, sound helper and keyboard → trusted core.
- **Where:** `native/core/src/main.rs:2243` `let (events, incoming) = mpsc::channel();`. Every reader thread (`start_decoder` around 183-197, `start_fetcher` around 252-266, sound and phone) sends into it with no bound. The main thread also blocks in broker requests and file writes while readers keep filling it.
- **Matters when:** a helper writes faster than the core handles its messages. A frame costs the core a compare and an encode, which a compromised decoder can outrun.
- **Effect:** the trusted core's memory grows without limit and the whole browser ends. The design (§5.3) says a misbehaving decoder stalls only its own channel.
- **Fix:** give each reader back-pressure, using either option:
  - A bounded `mpsc::sync_channel` per untrusted sender. A full channel blocks only that helper's reader thread, never the core's thread.
  - A per-sender byte budget (16 MB, as `outbox::MAX_QUEUED_BYTES`): the reader adds, the main thread subtracts on handling, and a sender over budget is killed as one that stops reading is.
  
  Test: a decoder that writes frames without pause leaves the core's resident memory bounded.

### M-8. Frames have no per-page rate bound

- **Boundary:** decoder → core → interface.
- **Where:** `native/core/src/frames.rs:43-55` `Frames::accept` refuses only a frame identical to the last. `main.rs:1241-1262` queues every accepted frame for the interface. An interface outbox over 16 MB (`outbox.rs:139-150`) makes `flush` fail (`main.rs:1428`), and that ends the browser.
- **Matters when:** a decoder sends different frames for a visible page faster than the interface draws them.
- **Effect:** the whole browser ends because of one channel's decoder.
- **Fix:**
  - In `Frames::accept`, keep a `last_sent: Instant` per page key. Hold the newest frame and send it at most once per the engine's fastest legitimate change (its flash phase, by name), dropping the frames in between.
  - Count frames per channel per second; a decoder over the bound is put to sleep as `put_to_sleep` does.
  - Do not end the browser when the interface outbox is full because of frames: drop queued frames of non-active pages first.

### M-9. A helper that exits is not counted against the version's health **[verified]**

- **Boundary:** update health (`installation-and-updates.md` §3.2).
- **Where:**
  - `native/core/src/main.rs:1177-1196` `decoder_ended` calls `updates.helper_failed` only when `reason.is_some()`. `reason` is `None` for a clean end of the pipe, which is what a decoder that cannot confine itself produces: it returns `ExitCode::FAILURE` after printing (`decoder/src/main.rs:261-266`).
  - The exit status from `decoder.child.wait()` is thrown away (`let _ =`).
  - `Event::FetcherEnded` (`main.rs:2182-2193`) never calls `helper_failed`.
  - The comment at 1184-1185 describes behaviour the code does not have.
- **Effect:** a release whose decoder or fetcher dies at start (for example because a sandbox layer is missing on the user's machine) is reported healthy and committed, so rollback does not happen.
- **Fix:** carry the `Exit` from `wait()` in `DecoderEnded`/`FetcherEnded`, or wait inside the handler. Call `self.updates.helper_failed(...)` when `reason.is_some() || !exit.success`. Test: a decoder that exits with failure marks the trial unhealthy.

### M-10. Engine cookie import ends at the first expired or over-long record **[verified]**

- **Boundary:** disk (`cookies.bin`, sealed) → trusted core, through the engine's jar.
- **Where:**
  - `neoteletext-engine/crates/neoteletext-web/src/cookie.rs:722` `CookieJar::import_one`: `let lifetime = expires.checked_sub(now)?;`.
  - `cookie.rs:735`: `built.ok()?;` when the rebuilt header does not fit its buffer.
  - `cookie.rs:687` `import`: `let Some(...) = self.import_one(rest, now) else { break };`.
  - The browser ignores the count `import` returns (`native/core/src/cookies.rs:424` `Store::import`).
- **Matters when:** any record has expired between the write and the next start, which is ordinary: a cookie with a short `Max-Age`. A cookie whose name, value and path are near the limits does the same.
- **Effect:** every cookie stored after that record is silently lost, for every channel. The docs (`cookies.md` §6) say a record that breaks a rule is dropped alone.
- **Fix (engine, then re-pin):**
  - Have `import_one` consume the record whatever happens. Use `let lifetime = expires.saturating_sub(now);`, so `store` refuses it as expired and the function returns `Some((false, rest))`. On header overflow, also return `Some((false, rest))`.
  - Engine test: an expired record followed by a live one restores one cookie.
  - Browser: count the record lines and log when fewer were restored.

### M-11. Engine DBSC: the session identifier reaches a request header unchecked **[verified]**

- **Boundary:** server JSON → request headers (engine feature `dbsc`; not enabled in the browser's fetcher, so the engine and `neottx` are affected).
- **Where:**
  - `crates/neoteletext-web/src/agent/bound.rs:141` `write_headers` (`Purpose::Refresh`): `sf_string(session.id.as_bytes(), out)`.
  - `bound.rs:84-95` `sf_string` escapes only `"` and `\`.
  - The id comes from `dbsc::read_instructions` → `text()` (`dbsc.rs:433-444, 518`), which returns decoded JSON strings that can hold CR, LF and NUL.
- **Effect:** a server can put its own header lines into the refresh request, or desynchronise the kept-alive connection. It cannot leave its own origin (`session_of` pins the refresh URL to it). The value is also passed to the port in `Event::BoundSession`.
- **Fix:**
  - In `dbsc.rs`, read `session_identifier` with a reader that refuses an empty value and any byte outside `0x21..=0x7E` (RFC 9651 sf-string characters), returning `InstructionsError::Malformed`.
  - Make `sf_string` return `Err(Overflow)` for any byte outside `0x20..=0x7E`, so no caller can write a control character.
  - Test with `\r\n` and `\u0000` in the identifier.

### M-12. Engine: cookies from the push handshake are not narrowed to the channel folder **[verified]**

- **Boundary:** push server → cookie jar (REQ-WEB-026).
- **Where:** `crates/neoteletext-web/src/agent.rs:2461-2471` `push_head_complete` passes `None` as the scope to `store_response_cookies`. The fetch path passes the channel folder (`agent.rs:1658`).
- **Matters when:** several channels share a host and the agent's own jar is used, as in `neottx`. The browser is not affected, because its core ignores the scope it is given and stores every cookie under the fetcher's own channel folder (`core/src/cookies.rs` `Store::store`).
- **Fix:** at `agent.rs:2466`, pass `self.channel.as_ref().map(Url::path)`, as the fetch path does. Test with two channels on one origin, the push response setting `Path=/`.

### M-13. Documentation: the relay serves the phone's code

- **Boundary:** relay → phone → keyboard process (`interaction-security.md` §4 E).
- **Where:** `docs/interaction-security.md:88-89` claims "A hostile relay reads keys: it cannot". The QR address is `{origin}/app#…` on the relay itself (`neoteletext-qrkeyboard/src/screen.rs:174`), so the page that holds the pairing key and the PIN is the relay's.
- **Effect:** the end-to-end encryption protects against a passive relay and the network path, not against the relay's operator or a compromise of its server. Impact is bounded by §F: a hostile phone is a hostile local keyboard with no modifiers.
- **Fix:** reword the row to "a passive relay or network observer", add a row stating that the relay serves the phone's code, and rank it in §7. Closing it fully needs the phone page hosted apart from the relay.

### M-14. macOS: `previous/` and the rollback are not signature-checked

- **Boundary:** updater → launcher (macOS).
- **Where:**
  - `native/launcher/src/macos.rs:78-82` `holds_old_current` matches by version mark only.
  - `macos.rs:86-104` `move_old_current` considers every entry in `staging/`.
  - `macos.rs:45-63` `reconcile` exchanges `previous` into place, checking only `version_of()`.
- **Matters when:** a staging entry carries the current version's mark but is not the genuine bundle, and a trial then fails twice.
- **Fix:** in `reconcile`, run `MacosSigner::check` and the mark check on the bundle about to be exchanged in, and refuse the rollback (keeping the current bundle) if either fails. In `move_old_current`, consider only the trial's own staging folder.

---

## Low

| Id | Sev | File:line | Item | Defect | Fix |
|---|---|---|---|---|---|
| L-1 | Low **[verified]** | `native/core/src/cookie_control.rs:117-120` | `cookie_reply`, `ReachedQuestion` | Answered for any host the fetcher names, across all channels. That gives one bit about another site's secure cookies; the other two cookie messages are held to the fetcher's channel. | `let reached = owner.as_ref().is_some_and(\|(owner, _)\| owner.host == host) && self.cookies.store.reached_securely(&host, now);` plus a test with a foreign host. |
| L-2 | Low | `native/core/src/library.rs:578,587-616` | `BookmarkRequest::Import(path)` | The interface names the path the broker reads; the result is shown back to the interface in the manager. | The broker opens a native file dialog (`ChooseFile` request) and returns the bytes, so no path comes from the interface. At least refuse dot-folders and the browser's own folders. |
| L-3 | Low | `native/protocol/src/keyboard.rs:134-137` | `clean_name` | Refuses only control characters. A hidden character then makes the core's later `push_text` fail, which ends the browser. | Use `interface_core::editor::hidden` in `clean_name`, and forward `clean(&name, MAX_KEY_NAME)` in the core (`main.rs:1878-1880`). |
| L-4 | Low | `native/protocol/src/lib.rs:685-692` | `Fields::key` | Accepts 0x100..=0x8FF, including hexadecimal page numbers that `page_index` refuses. A `Showing` written from them is refused by the decoder, which restarts and marks health failed. | Validate with `page_index`. In `write_to_decoder(Showing)`, check each page and bound the count to `PAGES`. |
| L-5 | Low | `native/core/src/main.rs:1408-1432`, `sleep.rs:54-59,102` | `flush` / `match_decoders` | A decoder that overflows its outbox is killed and replaced at once, with no back-off, as long as its fetcher keeps sending. | Back off: a channel whose decoder was replaced more than K times in N seconds is marked failed until reloaded. M-7's back-pressure also removes the cause. |
| L-6 | Low | `core/src/history.rs:173`, `restore.rs:249`, `bookmarks.rs:165`, `settings.rs:208`, `cookies.rs:416` | strict readers' `dropped` lists | One `String` per refused line, all held until the start-up log is drained. A large malformed file costs gigabytes. | Keep the first 64 messages and a count, then log "and N more lines dropped". |
| L-7 | Low | `core/src/cookie_control.rs:40,162`, `cookies.rs:454`, `main.rs:2380-2392`, `confine/src/broker.rs:413-418` | cookie key handling | The key is a `Copy` array copied to the stack and into replies, and never cleared. The docs say it is wiped at exit. | A non-`Copy` key type whose `Drop` overwrites the bytes with `ptr::write_volatile` and a `compiler_fence`, held boxed. Or amend the docs. |
| L-8 | Low | `core/src/cookies.rs:407-437` | `Store::import` | Channel lines are keyed by tag only; one channel key under two tags survives deletion and blocking. The file's tags are merged without remapping into tags assigned this run. | Refuse a channel line whose key is already read. Assign fresh tags on import, or assert the tag table is empty. |
| L-9 | Low | `confine/src/broker.rs:838-841`, `launcher/src/start.rs:86-94` | helper life after a broker crash | Helpers are killed only when `serve` returns normally; there is no parent-death signal. An updater that outlives a crashed broker keeps its open files in staging. | `prctl(PR_SET_PDEATHSIG, SIGKILL)` in `confine::apply` on Linux, and kill the process group in `end_whole` after every broker exit. The copy fix of H-2 also closes it. |
| L-10 | Low | `core/src/history.rs:424,466-475`, `settings.rs:321-335`, `main.rs:2415` | settings-folder writes | Temporary files are opened with `create+truncate`, so a link is followed. `0o600` applies only when a file is new. The folder is made 0755. | `remove_file` then `create_new` with `O_NOFOLLOW`. `DirBuilder::new().mode(0o700)`. `set_permissions(0o600)` on an existing file. |
| L-11 | Low | `native/interface-core/src/editor.rs:12-21` | `hidden` | Missing U+00AD, U+034F, U+115F/1160/3164/FFA0, U+180E, U+2028/2029, U+206A–206F, U+FE00–FE0F, U+E0000–E007F, U+E0100–E01EF and other format characters. No bound on runs of combining marks. Display only. | Refuse general categories Cf, Zl, Zp, the variation selectors and the Hangul fillers; limit consecutive Mn/Me in `clean` to a named constant. |
| L-12 | Low | `native/dock-menu/src/lib.rs` (root), `mac.rs:191` | crate lints | Missing the no-panic deny list the other crates that read pipe input carry; one bare `tag += 1`. | Add the same `#![deny(...)]` block and use `saturating_add`. |
| L-13 | Low | `neoteletext-qrkeyboard/src/screen.rs:467-471`, `native/keyboard/src/keyboard.rs:96` | `FromPhone::Up` | A release is passed for any key in the layout, held or not, and releases are not limited, so the 120-a-second bound does not cover them. | Pass `Up` only for a key in `self.held`; otherwise acknowledge and emit nothing. |
| L-14 | Low **[verified]** | `neoteletext-qrkeyboard/src/screen.rs:152-156`, `net.rs:219-221` | owner token | The relay-supplied token is checked only for length and written into `Authorization: Bearer`. | Filter with `message::is_id`'s alphabet (`[A-Za-z0-9_-]`). |
| L-15 | Low | `native/keyboard/src/keyboard.rs:164`, `qrkeyboard/src/net.rs:111-117` | error line | The one stderr line includes rustls's error text, which can contain names from a presented certificate. | Map `Error::Tls(_)` to a fixed sentence before printing. |
| L-16 | Low | `native/web-opener/src/lib.rs:60-63` | `acceptable` | Allows `' ; & $ ( ) * ? [ ] ~ !`. Safe with today's shell-free openers; fragile with `xdg-open` and `$BROWSER`. | Percent-encode those sub-delimiters in the re-serialised address, or refuse them. |
| L-17 | Low | `neoteletext-web/src/agent.rs:1658` | fetch cookie scope | The channel folder scope is applied even to responses from outside the channel (a permitted form target; a same-origin redirect in `neottx`). | `let scope = channel.as_ref().filter(\|f\| channel::is_inside(f, &exchange.url)).map(Url::path);`, and drop or keep unscoped the cookies from outside. |
| L-18 | Low | `neoteletext-web/src/agent.rs:1303-1310`, `consts.rs:488` | `remember_secure` | `SECURE_HOSTS` = 32 fills silently, after which no-downgrade holds only for hosts with a live secure cookie. | Evict the oldest instead of dropping the new one, raise the bound, or record "seen secure" through the port's store. |
| L-19 | Low | `neoteletext-web/src/agent.rs:1997-2019` | `redirect` | A 307/308 of a form submission keeps the body for a new origin without `policy::may_submit` or the first-submission confirmation (REQ-SEC-009). | For `Purpose::Form` with the method kept, require `may_submit` and the confirmation state for the new origin, else fail with `FormRefused::Origin`. |
| L-20 | Low | `neoteletext-web/src/bytes.rs:188-190`, `agent.rs:1977` | `TextBuf::as_str` | Returns "" for non-UTF-8, so a `Location` with obs-text becomes a redirect to the same URL. | At the call site use `core::str::from_utf8` and fail with `UrlError::BadCharacter`. |
| L-21 | Low | `neoteletext-web/src/channel.rs:210-228` | `is_inside`, `redirect_keeps_channel` | A path prefix test; percent-encoded dot segments and slashes after the folder pass. | Refuse `%2E`, `%2F` and `%5C` (either case) in the part after the folder, or require it to be a channel file name. |
| L-22 | Low | `neoteletext-core/src/policy.rs:34-45` | blocked ranges | IPv4-compatible `::a.b.c.d`, NAT64 `64:ff9b::/96`, `192.0.0.0/24` and `198.18.0.0/15` are not blocked. | Add them, and treat 6to4 `2002::/16` by its embedded IPv4 address. |
| L-23 | Low | `native/launcher/src/start.rs:44-50` | health line reader | `take(MAX_LINE)` is renewed per read, so `healthy\n` after 64 other bytes on the same line matches. Only the broker writes this pipe today. | Accept a line only when the previous read ended in `\n`. |
| L-24 | Low | `native/launcher/src/unix.rs:168-192`, `update/src/layout.rs:99` | `--uninstall` | Removes the folder two levels above the binary without checking it is an installation. | Require `layout.state()` or the installed launcher to exist (Linux), and the bundle path to end in `NeoTeletext.app` (macOS), before removing anything. |
| L-25 | Low | `staging/metadata/latest_known_time.json` (tough `datastore.rs:88-119`) | clock guard | One forward jump of the clock leaves "Updates unavailable" for good. | Report `SystemTimeSteppedBackward` distinctly, and remove the file when it is more than a stated bound ahead of now. |
| L-26 | Low | `native/tuf/release/src/package.rs:165-183`, `release-identity/build.rs:49-57`, `scripts/release/publish.sh` | release `check` | Checks with the release tool's own identity, not the launcher's built in; publish runs no identity check, so a test identity left in the environment is published. | Put `release_identity::NAME` in the launcher as a mark; `check` reads it from the built launcher and refuses anything but production unless `--test-identity`; `publish.sh` runs `check` for every platform first. |
| L-27 | Low | `native/update/src/files.rs:124-140` | `copy_tree` (Windows) | Takes `file_type()` from the entry, then reads by path, so the entry can change in between. There is no size bound. | Open each entry with `FILE_FLAG_OPEN_REPARSE_POINT` from a directory handle and check the handle; copy only the manifest's files, each at most its manifest length. |
| L-28 | Low | `native/confine/src/macos.rs:22-33,126,134,140` | `preamble`, `profile` | Paths (the program, the settings or staging folder, the home folder) are put into SBPL string literals without escaping `"` or `\`. | Refuse a path containing `"`, `\` or a control character and fail closed, or escape them as SBPL strings allow. |
| L-29 | Low | `native/confine/src/macos.rs:42-45` | `SYSTEM_READS` | The interface and sound helper may read all of `/private/var/folders`, the per-user temporary and cache folders of every application. | Narrow it to what the measured denials need (the process's own `DARWIN_USER_CACHE_DIR` and `DARWIN_USER_TEMP_DIR` sub-folders), found as the other rules were. |
| L-30 | Low | `native/core/src/restore.rs:159`, `session.rs:55-58,801`, `address.rs` | `kept_address`, restore and import | `file:` addresses and absolute paths are restored from `session.txt` and accepted from imported bookmarks, and up to 64 restored file tabs are read through the broker at start. | Refuse `file:` from restore and import unless the user typed it; read a file tab lazily when it is shown. |
| L-31 | Low | `native/interface/src/main.rs:757-760` | paste | The whole clipboard is read before it is cut to `MAX_PASTE`. | Cut on a character boundary to `MAX_PASTE` right after `get_text()`. |
| L-32 | Low | `native/sound/src/audio.rs:178-181` | mixer per channel | Any operation on an unknown channel makes a mixer; `Define` allocates under the lock the audio callback takes. | Create a mixer only on `Define` or `Stream`, and ignore other operations for unknown channels; allocate outside the lock and swap it in. |

### Information, no change required for security

- `fetcher/src/main.rs:100-117` `Random`: WebSocket masks come from `RandomState`'s SipHash keyed per process. They are unpredictable without the key, which is acceptable; `ring::rand::SystemRandom` is already a dependency of the core if a CSPRNG is preferred.
- `fetcher/src/transport.rs:172,224`: the write timeout stays at 10 s after connecting, so a server that stops reading holds its own fetcher's loop for up to 10 s per send. That channel only.
- `docs/cookies.md` §7 names XChaCha20-Poly1305 or AES-256-GCM; the code seals with ChaCha20-Poly1305 and a random 96-bit nonce per write (`cookies.rs:463`). That is sound at this write rate; the doc should say what is built.
- `core/src/updates.rs:260-263`: the "Updates unavailable" age uses the updater's report of when it checked; stamp the receipt with the broker's `local_time` instead.
- `launcher/src/start.rs:36`: `Chosen::Run` with a missing `versions/<current>` fails hard, with no fallback to `recovered()`.
- The AppArmor profile (`tuf/release/src/package.rs:64-75`) covers only `@{HOME}/.local/share/neoteletext/versions/*`; an `XDG_DATA_HOME` installation is not covered.
- Engine, minor RFC strictness: `Last-Event-ID` may carry C0 controls and DEL (`sse.rs:249-255`); the WebSocket close code is echoed without refusing 1005/1006/1015 (`ws.rs:391-404`); a duplicate member in DBSC instructions overwrites the earlier one (`dbsc.rs:516-533`); `Writer::hex` would overflow its shift for a width over 8 (callers use 2 and 4).
- Not covered by tests: a symlinked or junctioned staging root, Windows mix-and-match, `bad` poisoning, `previous/` poisoning, quick-quit rollback, the root-version floor, and a non-production identity reaching publish. The launcher tests use a `TestSigner`, so the macOS and Windows platform checks run only by hand.

---

## Health deadline and trial counting (the coordinator's question)

**The failing test.** `a_broken_version_is_rolled_back_after_two_starts` asserts at `native/launcher/tests/launcher.rs:241` that the log holds two `0.2.0 crash` lines. Under heavy load:

- The `crash` case runs with `HEALTH_DEADLINE`, 45 s counted from `spawn`.
- The first trial was killed by the deadline before the test broker reached `main`, where it writes its log line. On a loaded machine that gap includes the operating system's first-run check of a new executable, and macOS checks before `main`.
- The launcher counted that start (the count is written in `prepare` before the start, `lib.rs:287-292`) and retried at once (`run`, `lib.rs:178-182`).
- The second trial crashed and logged, and the third pass rolled back.

So the launcher did what its code says: two counted trials, then rollback. The test confused "started" with "ran far enough to log".

**Can a slow machine cause a wrong rollback?** Yes, as M-6 says:

1. Two independent clocks:
   - the core finds a version healthy only if its first frame is drawn within `HEALTH_WINDOW` (30 s from the core's own start, `core/src/updates.rs:30,110`), plus a 2 s settle;
   - the launcher kills at 45 s from `spawn`, which includes the broker's and the core's own starting.
2. A kill by the deadline counts the same as a crash and is retried within the same start. Two slow starts therefore roll a good version back within about 90 s. It is then `mark_bad` and never offered again (`offer`, `core/src/updates.rs:299-303`).
3. A clean quit before health (the `quiet` path) also counts, so quick quits do the same (the launcher review's finding 6, folded into M-6).

**Can it prevent a rollback?** No. The count is written before each start, so a crash, a hang or a kill of the launcher itself leaves the count in the state file. Only a trial that becomes healthy and fails afterwards escapes, and that is the design.

**Fix to the code:**

- *Start the deadline when the program is running, not at spawn.* The broker writes `started\n` on its standard output first thing in `main`, before it starts the core, as a constant beside `HEALTHY_LINE` in `update::layout`. The launcher then waits in two phases:
  - a start deadline: a named constant of minutes, `START_DEADLINE`, for the first line;
  - then `HEALTH_DEADLINE` for `healthy\n`, counted from `started`.
- *Count a trial only once it has started.* A trial killed for not starting at all does not consume a count. Report it, and leave it as the trial for the next start.
- *Count only failures.* Increment `failed` only for an end that is `!success` after `started`, or for a health deadline that expired after `started`. A clean exit before health leaves the count unchanged. Implement this by moving the increment from `prepare` to after `start` returns, with a "started" flag in the state written when `started` is heard, so a crash of the launcher itself still counts.
- *Make the core's window and the launcher's deadline one rule.* Derive `HEALTH_DEADLINE` from `HEALTH_WINDOW` + `HEALTH_SETTLE` + a named margin, in one place both crates use (`update::layout`), and assert the relation at compile time.
- *Do not make a deadline-only rollback permanent.* A version rolled back only because of deadlines is offered again after a stated number of days. A version that crashed stays bad.

**Fix to the test:** give `crash` and `quiet` a deadline far above any start time, a named `NO_DEADLINE_NEEDED` of several minutes, since they end by themselves; only `hang` needs `SHORT_DEADLINE`. Assert on the launcher's own record rather than on lines the broker writes:

- the state: `trial` cleared, `is_bad(NEW)`, `rolled_back == Some(NEW)`;
- the launcher's stderr lines "did not start; trying again" and "was not found healthy in time", if captured.

Keep the log-line count only as "at least one". Add a test that a trial killed by its deadline before `started` is not counted.

---

## Checked and found sound

**Fetcher, TLS and proxy**
- TLS: `rustls` 0.23.46 with `ring`, Mozilla roots from `webpki-roots` 1.0.10, `ServerName` from the URL host, so hostname verification is on. The handshake completes before any use, and any certificate error is a hard stop. There is no custom verifier, no `dangerous()` configuration and no fall-back to plain (`fetcher/src/transport.rs:114-119,199-219`).
- Proxy bytes after the head are fed into `rustls` before the handshake, so nothing is lost or accepted unauthenticated.
- The proxy `CONNECT` answer is read in 1 KB chunks into a head collector bounded by `DEFAULT_HEADER_LIMIT`. Only a 2xx head is accepted, and the bytes after it belong to the tunnel. SOCKS5 replies are read to their exact computed length (`neoteletext-web/src/proxy.rs:136-148,341-390`).
- The `CONNECT` authority comes from the strict URL parser, so no CR/LF can occur. A proxy address with user info, a path, or port 0 is refused.
- Local-network rule (`agent.rs:1259-1285,1527-1538`): applied to the peer actually reached and after each redirect; through a proxy, local names are refused before the proxy is asked.
- The fetcher keeps no cookies (a `CookieJar<0,0>`, asserted at compile time). Questions carry an id and late answers are dropped. The core holds every answer to the fetcher's own channel; the `ReachedQuestion` exception is L-1.

**Sandboxes**
- `confine` Linux:
  - no-new-privileges first;
  - the user namespace maps only the user's own ids;
  - Landlock ABI 5 with `HardRequirement` and refused unless fully enforced;
  - seccomp blocks exec, fork and process `clone`; `clone3` is answered "not implemented";
  - socket families are filtered per role, and the decoder and core can make no sockets;
  - everything is applied before any thread exists (`linux.rs`). The `AF_UNIX` gap is H-1.
- `confine` macOS: every profile is `(deny default)` with `system.sb` and exec of the program alone; the decoder and core look up no services; the updater gets one port and its staging folder (`macos.rs`).
- `confine` Windows:
  - a job with kill-on-close and one active process;
  - the mitigation policy set, including no child processes, no dynamic code, no remote or low-label images, and Win32k off for the windowless roles;
  - only the two pipes and stderr inherited, by handle list;
  - created suspended, assigned to the job, then resumed;
  - an AppContainer for every role but the interface, and less privileged for the decoder and core;
  - no fallback when the container fails;
  - command-line quoting follows the C runtime's rules (`windows.rs`).
- Every child gets `env_clear` and an allow-listed environment.

**Broker**
- Requests are a kind, a length and a payload, bounded before allocation (`MAX_REQUEST`). Text fields are at most 4,096 bytes of UTF-8 and checked to their exact end.
- The program comes from a fixed enumeration and the role from the program, never from the core; at most 512 helpers.
- `SCM_RIGHTS` receive refuses foreign control messages, more than two descriptors, and `MSG_CTRUNC`, and sets close-on-exec. On Windows, handles are duplicated into the core one by one.
- The core's own sandbox is applied before it reads the broker's channel.

**Protocol and core dispatch (sub-review)**
- Framing is bounded before allocation, and every kind is accepted only by the side meant to receive it.
- `frame.rs` run and change decoding is index-safe and re-checks the palette.
- `clean` and `is_clean` agree on the hidden set and the byte bound.
- Audio operations are bounded and `Reset`/`Mute` are refused from a decoder.
- Cookie stores are held to the fetcher's channel host, scheme and folder.
- Links go through `parse_target` and the site-change screen. The click rules hold: equality with the strip, 500 ms, the version window.
- Web hand-off: at most one per 2 s, with focus, re-serialised `https`/`http` only.
- Typing goes only to the open page's channel that declared input.
- Generations prevent stale messages from acting.
- The outbox is bounded at 16 MB.

**Disk formats and sealing (sub-review)**
- The settings, history, session, bookmarks and Netscape readers are bounded and strict: depth 16, entry caps, canonical addresses, titles cleaned exactly.
- `cookies.bin`:
  - AEAD with the magic line as associated data;
  - a short or truncated file is refused;
  - no clear-text fallback;
  - every cookie is re-stored through the engine's rules;
  - a stolen-key file can plant or delete cookies but cannot widen `Secure` or `HttpOnly` or cross the scheme.
- The cookie key travels in one bounded request and is never logged.

**Engine web (sub-review)**
- The URL parser is strict: `@`, backslash, controls and non-ASCII are refused; IPv4 follows WHATWG; the IPv6 grammar is checked; dot segments are removed without escaping the root.
- HTTP framing:
  - `Transfer-Encoding` exactly `chunked`, once, on HTTP/1.1;
  - CL+TE and conflicting CL refused;
  - obsolete folding, bare CR and CTL in values refused;
  - at most 64 headers;
  - chunk sizes at most 8 hex digits;
  - no compression;
  - one absolute deadline per exchange.
- No `Referer` header; no downgrade from HTTPS to HTTP.
- Cookies: host-only, `Secure` and the prefixes enforced, `SameSite` defaulting to Lax, the 400-day cap.
- WebSocket: RSV, mask, opcode, control-frame and length rules enforced; the accept value checked.
- SSE, JSON and the descriptor reader are bounded and strict.
- DBSC keys stay on the responding origin over HTTPS.

**Launcher and updater (sub-review)**
- Versions are compared numerically.
- Manifest paths come from a fixed list, with exact files and SHA-256.
- The gzip reader refuses header flags and concatenated members, and checks the exact length, CRC and ISIZE.
- Linux Ed25519 signatures cover the manifest (version, platform, file list) and every file.
- tough enforces expiry, consistent snapshots, root rotation with both thresholds, and rollback limits.
- Updater TLS is pinned to the host; bodies are at most 64 MiB; wire frames are at most 512 bytes.
- The state file is written synced, renamed and folder-synced, and only the launcher can write it.
- Windows copies, re-checks and verifies Authenticode with a pinned leaf key.
- The production identity accepts nothing.

**Keyboard, unsafe code and sound (sub-review)**
- Phone keyboard cryptography:
  - HKDF directional keys from a 256-bit secret;
  - 96-bit counter nonces, monotonic, advanced after the tag verifies, refused at wrap;
  - SPAKE2 on RustCrypto `p256` with point validation and a transcript bound to the configuration hash;
  - a constant-time confirmation;
  - five-try PIN lockout.
- The phone message has no modifier field. The relay JSON and WebSocket readers are bounded; relay TLS verifies the host.
- `dock-menu` Objective-C: the method signature matches, and returns, retention, the main-thread guard and tag bounds are correct.
- `web-opener`: one argument, no shell, the scheme exactly lowercase `https://` or `http://`, the process reaped and not waited on.
- Sound: sample, channel and voice bounds hold; the core's ledger is 32 MB a channel and 64 MB in all; the callback never allocates.
- The interface accepts no dropped files and diverts browser shortcuts before keys reach a channel.
