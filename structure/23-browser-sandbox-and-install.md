# 23. The browser's sandbox and installation crates

`confine`, `launcher`, `update`, `tuf` (its own workspace), `installer`, `os-install`, `release-identity`, `web-opener`, `site`, `stub`, and the fuzz targets of `native/fuzz` and `native/tuf/fuzz`.

| | |
|---|---|
| **Rests on** | A reading of every file of these crates in full at browser commit `494aa91` (23 October 2026), with `scripts/check.sh`, `scripts/tools.sh`, `scripts/try.sh`, `scripts/release/*`, `scripts/updates-e2e.*`, `.githooks/*`, `native/clippy.toml`, `native/rustfmt.toml`, every `Cargo.toml` in scope, requirement 10.12, `docs/sandboxing.md` sections 3 and 7, `docs/installation-and-updates.md` section 14 and `docs/architecture.md` section 14. |
| **Measure** | `00-conventions.md`. |
| **Phase** | `confine` and `update` are B2; the rest B4 (`01-method-and-order.md` section 2). |
| **State** | Plan. Nothing carried out. |

Line numbers are those of the files at `494aa91`.

---

## 1. The crates as they are

### 1.1 `confine`

| | |
|---|---|
| Purpose | The processes' sandboxes on every platform (decision 52), the broker and the trusted core's end of it (decision 56), the local time zone for the confined core (decision 57). |
| Lib/bin | `src/lib.rs` the library; `src/bin/confine-probe.rs` a never-shipped single-thread probe (`test = false, doc = false`) run by `tests/probe.rs` on Linux. |
| Features | None. Imported with `default-features = false` by the workspace and by `tuf`. |
| Lints | `unsafe_code = "deny"` in its own `[lints.rust]` (not the workspace's `forbid`), `clippy::undocumented_unsafe_blocks = "warn"`; the no-panic `#![deny(...)]` list at `lib.rs` 29–38 (in `NO_PANIC_ROOTS`). |
| cfg structure | Four per-OS modules declared in `lib.rs` 46–54: `linux` (`target_os = "linux"`), `macos` (`target_os = "macos"`), `unix`, `windows`. The shared `lib.rs` and `broker.rs` hold 52 `#[cfg]` sites between them (section 2.3): the spawn, the broker's channel, the pipe passing and the core's start are cfg blocks inside shared functions. |
| Dependencies | `libc` (unix), `landlock` + `seccompiler` (linux), `windows-sys` (windows). No workspace crate. |

Module tree:

| File | Lines | Holds |
|---|---|---|
| `src/lib.rs` | 475 | `Role`, `Report`, `apply`, the environment allowlists, `LocalTime`, `Spawn`, `Process`, `spawn` |
| `src/broker.rs` | 1016 | the broker's wire format, the core's client, the broker's server |
| `src/windows.rs` | 717 | job, token, AppContainer, mitigation policy, pipes, ACLs, handle duplication, time zone, spawn |
| `src/linux.rs` | 318 | no-new-privileges, network namespace, Landlock, seccomp, the apply order |
| `src/unix.rs` | 233 | `SCM_RIGHTS` send and receive, `localtime_r` |
| `src/macos.rs` | 196 | `sandbox-exec` profiles |
| `src/bin/confine-probe.rs` | 75 | the probe |
| `tests/probe.rs` | 71 | five Linux tests through the probe |

Public paths and who imports them:

| Path | Importers |
|---|---|
| `confine::{Role, Spawn, Process, spawn, environment}` | `core/src/main.rs` 65, 2418, 2623; `core/tests/confined_keyboard.rs`; `core/tests/confined_core.rs`; `decoder/tests/confined_bookmarks.rs`; `sound/tests/confined.rs`; `tuf/updater/src/bin/updater-drive.rs` 39–49 |
| `confine::apply` | `core/src/main.rs` 2366; `interface/src/main.rs` 1486; `fetcher/src/main.rs` 407; `decoder/src/main.rs` 261; `keyboard/src/keyboard.rs` 157; `sound/src/main.rs` 114; `tuf/updater/src/main.rs` 56 |
| `confine::{LocalTime, MAX_OFFSET}` | `core/src/library.rs` 10; `core/src/history.rs` 36 |
| `confine::broker::{Broker, Exit, Handlers, Helper, Program, UpdaterGrant, COOKIE_KEY_BYTES, start_core, serve}` | `core/src/main.rs` 66, 2386, 2419–2436; `core/src/updates.rs` 18; `core/tests/confined_core.rs` 11 |
| `confine::broker::{decode_request, decode_reply}` | `fuzz/fuzz_targets/broker_requests.rs`, `broker_replies.rs` |
| `confine::remove_containers` (windows) | `launcher/src/windows.rs` 131 |
| `confine::grant_packages_read` (windows) | `installer/src/main.rs` 126 |

### 1.2 `launcher` (`neoteletext-launcher`)

| | |
|---|---|
| Purpose | What the user starts (`installation-and-updates.md` section 3): choose a version, accept a staged one by the pinned signer, count a trial, roll back, start the broker, commit a healthy trial; Linux `--install`; `--uninstall` on every desktop; launcher releases (section 7). |
| Lib/bin | `src/lib.rs` (lib `launcher`), `src/main.rs` (bin `neoteletext-launcher`, `windows_subsystem = "windows"`), `src/bin/launcher-test-broker.rs` (the tests' and `scripts/updates-e2e.*`'s stand-in broker). |
| Features | None. Workspace lints (`unsafe_code = "forbid"`); the no-panic list at `lib.rs` 23–32 and `main.rs` 8–17. |
| cfg structure | `macos` (private, two functions re-exported), `unix` (pub), `windows` (pub); `install.rs` and `start.rs` shared. `lib.rs` carries twelve cfg sites, six of them macOS hooks inside the state machine. |
| Dependencies | `update`, `release-identity`, `os-install`; `rustix` (unix, `process`); `confine` (windows); dev `ring`. |

| File | Lines | Holds |
|---|---|---|
| `src/lib.rs` | 450 | `Launcher`, `Chosen`, `Ended`, the lock, state, acceptance, trial, tidying, commit |
| `src/unix.rs` | 218 | the terminal prompt, the Linux install, the macOS and Linux uninstall |
| `src/macos.rs` | 199 | the bundle swap and reconciliation; translocation and the move to Applications |
| `src/windows.rs` | 137 | the two-copy launcher release; the uninstaller |
| `src/start.rs` | 94 | starting the broker and hearing `healthy` |
| `src/install.rs` | 75 | a launcher release (section 7) |
| `src/main.rs` | 69 | argument dispatch |
| `src/bin/launcher-test-broker.rs` | 101 | the stand-in broker |
| `tests/launcher.rs` | 348 | the life of an update, with fault points |

| Path | Importers |
|---|---|
| `launcher::{Launcher, HEALTH_DEADLINE}` | `src/main.rs`; `tests/launcher.rs` 16 |
| `launcher::{must_move, offer_move}` (macOS) | `src/main.rs` 64–66 |
| `launcher::unix::{install_linux, uninstall}` | `src/main.rs` 42, 60 |
| `launcher::windows::{launcher_copy, shortcut}` | `installer/src/main.rs` 119, 128 |
| `launcher::windows::{UNINSTALL_FROM, AND_SETTINGS, uninstall, uninstall_from}` | `src/main.rs` 50–58 |
| `launcher::windows::CHOICES` | `stub/src/main.rs` 41 (test) |

### 1.3 `update`

| | |
|---|---|
| Purpose | What the launcher, updater, installer and release tool share (decision 54). |
| Lib/bin | Library only. No features. Workspace lints; the no-panic list at `lib.rs` 26–35. |
| cfg structure | No per-OS module; `files.rs` has twelve `cfg(unix)` pairs (modes, folder flush, exchange, executable bit); `layout.rs` and `platform.rs` use `cfg!`. |
| Dependencies | `ring`, `miniz_oxide`, `rustix` (unix, `fs`). |

| File | Lines | Holds |
|---|---|---|
| `src/wire.rs` | 318 | the core↔updater messages |
| `src/files.rs` | 262 | writes that survive a power cut, the folder exchange, bounded reads, tree copy and list |
| `src/accept.rs` | 260 | `Keys`, `Signer`, completeness, acceptance, the Linux and macOS signers |
| `src/state.rs` | 242 | the launcher's state file |
| `src/platform.rs` | 211 | the platforms and each version's files |
| `src/layout.rs` | 208 | where each desktop keeps an installation; the settings folder |
| `src/manifest.rs` | 195 | a release's manifest |
| `src/gzip.rs` | 186 | the release files' gzip, bounded |
| `src/lib.rs` | 113 | `sha256`, `hex`, `from_hex` |
| `src/mark.rs` | 100 | the version mark |
| `src/signature.rs` | 82 | Ed25519 and PEM |
| `src/version.rs` | 79 | `Version` |
| `src/profile.rs` | 70 | settings format files |
| `src/fault.rs` | 39 | fault points |

Importers: `launcher`, `installer`, `os-install`, `release-identity`, `stub` (dev), `core` (`wire`, `profile`, `mark`, `version_mark!`, `version`, `layout`, `state`, `platform`, `files`), `tuf/updater`, `tuf/release`, and the fuzz targets `gzip_member`, `launcher_state`, `release_manifest`, `updater_messages`, `version_mark`. `update::accept::{LinuxSigner, MacosSigner, Signer, Keys, accept, complete}` are named by `launcher/src/lib.rs` 126–131, `launcher/tests/launcher.rs` 18, `tuf/release/src/package.rs` 174–182, `os-install/src/windows.rs` 28, `release-identity/src/lib.rs` 17–18.

### 1.4 `tuf` (a workspace of its own)

| | |
|---|---|
| Purpose | The Update Framework side (`installation-and-updates.md` sections 8.2, 9, 10): the confined updater with `tough`, and the release tool. Apart so `tough`'s dependencies (and `rustls` with `aws-lc-rs`) never reach the browser's crates (section 14 item 1). Own `Cargo.lock`, `deny.toml`, `fuzz/`. |
| Members | `updater` (`neoteletext-updater`): lib `updater` + bin + test bin `updater-drive`; `release` (`neoteletext-release`): bin, plus a second bin `neoteletext-test-host` whose source is `src/host.rs`; `fuzz` (excluded, nightly). |
| cfg structure | `release/src/main.rs` 42, 161 (`signer-key`, Windows); `release/src/package.rs` 177–179 (the Windows signer in `check`). No per-OS module. |

| File | Lines | Holds |
|---|---|---|
| `updater/src/lib.rs` | 249 | `Config`: the TUF client and the staging writer |
| `updater/src/transport.rs` | 235 | HTTPS to one host, the engine's HTTP reader |
| `updater/src/main.rs` | 94 | the process: confine, then the wire loop |
| `updater/src/bin/updater-drive.rs` | 75 | a driver for the end-to-end tests |
| `release/src/repo.rs` | 216 | root, publish, timestamp |
| `release/src/package.rs` | 203 | layout, manifest, Linux signing, check, targets; the `Info.plist` and AppArmor texts |
| `release/src/keys.rs` | 171 | key sources, `tough` key adapters |
| `release/src/main.rs` | 168 | the command line |
| `release/src/host.rs` | 120 | the test HTTPS host (a `[[bin]]`) |
| `release/src/test_identity.rs` | 79 | a test identity |
| `release/tests/updates.rs` | 390 | the release tool and the updater together |
| `fuzz/fuzz_targets/tuf_metadata.rs`, `http_response.rs` | 19, 13 | |

No-panic roots: `updater/src/lib.rs`, `updater/src/main.rs`, `release/src/main.rs`, `release/src/host.rs`. Public paths: `updater::{Config, Https, now, newest, target_name, PARTIAL, COMPRESSED, METADATA, MAX_ATTEMPTS}` (its own `main.rs`, `release/tests/updates.rs`), `updater::transport::{MAX_BODY, read_response}` (`tuf/fuzz`).

### 1.5 `installer`, `os-install`, `release-identity`, `web-opener`, `stub`

| Crate | Files (lines) | Purpose; lints; cfg |
|---|---|---|
| `installer` (`neoteletext-installer`, bin) | `src/main.rs` 164, `src/shortcut.rs` 239, `build.rs` 44 | `NeoTeletext-Setup.exe` (section 4.2); no-panic list at `main.rs` 13–22; `run` exists twice (`cfg(not(windows))` 53–57, `cfg(windows)` 59–147). Deps: `update`, `release-identity`; windows: `os-install`, `confine`, `launcher`. |
| `os-install` (lib) | `src/lib.rs` 71, `src/macos.rs` 95, `src/windows.rs` 233 | Dialogs, Authenticode, the uninstall registry entry (decision 75); `unsafe_code = "deny"` + `undocumented_unsafe_blocks`; unsafe allowed at the head of `macos.rs` (5) and `windows.rs` (6–10); no-panic list at `lib.rs` 16–25. Deps: `update`; windows: `windows-sys`. Public: `ask`, `tell` (launcher, installer), windows `WindowsSigner`, `UninstallEntry`, `uninstall_entry`, `remove_uninstall_entry`, `signer_key` (launcher, installer, `tuf/release`). |
| `release-identity` (lib) | `src/lib.rs` 33, `build.rs` 88 | The release's identity, built in; `keys()`, `HOST`, `PORT`, `TLS_ROOT`, `TUF_ROOT`, `LINUX_RELEASE_KEY`, `MACOS_REQUIREMENT`, `WINDOWS_SIGNER`, `NAME` (launcher, installer, updater, release). |
| `web-opener` (lib) | `src/lib.rs` 135, `src/windows.rs` 29 | Hands a checked address to the system's browser; `unsafe_code = "deny"`, allowed in `windows.rs` 3; no-panic list at `lib.rs` 18–27. Public: `acceptable`, `open`, `OpenError` (`core`, fuzz `link_target`). |
| `stub` (`neoteletext-stub`, bin) | `src/main.rs` 43 | The Windows stub; no dependencies (dev: `update`, `launcher`). |

### 1.6 `site` (`neoteletext-site`, bin, a development tool)

| File | Lines | Holds |
|---|---|---|
| `src/terminal.rs` | 1540 | the terminal channel: TTI pages, seven pages, sound synthesis, the game, the input protocol, the phone thread, the podcast glue, the HTTP and WebSocket server |
| `src/podcast.rs` | 417 | a WAVE reader and the live-sound player |
| `src/build.rs` | 264 | the Halcyon channel from recordings |
| `src/serve.rs` | 199 | HTTP serving with server-sent events |
| `src/websocket.rs` | 147 | the server half of RFC 6455 |
| `src/main.rs` | 64 | three commands |

No per-OS code; not in `NO_PANIC_ROOTS`; not shipped. Deps: `decoder`, `neoteletext-input`, `neoteletext-audio` (`encode`), `neoteletext-web`, `neoteletext-core`, `neoteletext-qrkeyboard`.

### 1.7 The fuzz targets

`native/fuzz` (28 targets, one `[[bin]]` each; `native/tuf/fuzz` two more). Each target's imports, so that a move can check them:

| Target | Crate path exercised |
|---|---|
| `address.rs` | `neoteletext::address::parse` |
| `bookmarks_file.rs` | `neoteletext::bookmarks::{Bookmarks, MAX_DEPTH, MAX_ITEMS}` |
| `broker_replies.rs` | `confine::broker::decode_reply` |
| `broker_requests.rs` | `confine::broker::decode_request` |
| `cookie_file.rs` | `neoteletext::cookies::{PER_CHANNEL, Store, TOTAL}` |
| `core_messages.rs` | `protocol::read_from_core` |
| `decoder_messages.rs` | `protocol::decoder::read_from_decoder` |
| `decoder_requests.rs` | `protocol::decoder::read_from_core` |
| `engine.rs` | `decoder::Engine` |
| `fetcher_commands.rs` | `protocol::fetcher::{MAX_COOKIE_HEADER, ToFetcher, read_to_fetcher}`, `neoteletext_input::{MAX_MESSAGE, event::read_message}` |
| `fetcher_messages.rs` | `protocol::fetcher::read_from_fetcher` |
| `gzip_member.rs` | `update::gzip::{compress, decompress, decompress_at_most}` |
| `history_file.rs` | `neoteletext::history::{History, MAX_FILE, MAX_ROWS}` |
| `input_records.rs` | `neoteletext::typing::{Send, Typing}`, `neoteletext_input::{control::MAX_BODY, cursor::BODY, modes::ALL_MODES}`, `interface_core::canvas::PageKey` |
| `interface_messages.rs` | `protocol::read_from_interface` |
| `launcher_state.rs` | `update::state::{MAX_BAD, State}` |
| `link_target.rs` | `neoteletext::links::{Target, parse_target, web_address}`, `web_opener::acceptable` |
| `netscape_file.rs` | `decoder::netscape::read`, `interface_core::library::MAX_FOLDER_DEPTH`, `protocol::decoder::{BookmarkEntry, MAX_BOOKMARK_ENTRIES, MAX_BOOKMARK_NAME}`, `protocol::MAX_ADDRESS` |
| `page_image.rs` | `protocol::frame::{PAGE_DOTS, base, decode, encode}` |
| `phone_keys.rs` | `protocol::keyboard::{FromKeyboard, MAX_KEY_NAME, MAX_PHONE_TEXT, MAX_QR_SIZE, read_from_keyboard}` |
| `relay_messages.rs` | `neoteletext_qrkeyboard::{json::Value::parse, message::read, message::from_base64url}` |
| `release_manifest.rs` | `update::manifest::{MAX_FILE_BYTES, Manifest}` |
| `session_file.rs` | `neoteletext::restore::{MAX_ENTRIES, MAX_FILE, MAX_TABS, MAX_WINDOWS, Saved}` |
| `settings_file.rs` | `neoteletext::settings::{MAX_LOCAL, MAX_VOLUME, Settings}` |
| `sound_messages.rs` | `protocol::sound::read_from_sound` |
| `sound_requests.rs` | `protocol::sound::read_to_sound` |
| `updater_messages.rs` | `update::wire::{MAX_REASON, FromUpdater, decode_from_updater, decode_to_updater, encode_from_updater, read_from_updater}` |
| `version_mark.rs` | `update::mark::find`, `update::version_mark!` |
| `tuf/fuzz` `http_response.rs` | `updater::transport::{MAX_BODY, read_response}` |
| `tuf/fuzz` `tuf_metadata.rs` | `tough::schema::{Root, Signed, Snapshot, Targets, Timestamp}`, `serde_json` |

The targets that this document's moves can touch are `broker_replies`, `broker_requests`, `gzip_member`, `launcher_state`, `link_target`, `release_manifest`, `updater_messages`, `version_mark`, `http_response`. Every path they name is kept (section 3).

---

## 2. Findings

### 2.1 File by file

**`confine/src/lib.rs` (475).** Crate doc 1–27; `#![deny]` 29–38; `mod` declarations 46–54; `Role` 56–79 with `name` 81–94; `Report` + `Display` 96–108; `apply` 110–139 (four cfg arms: Linux delegates, macOS and Windows return a fixed report, other platforms an error); `grant_packages_read` 141–152 and `remove_containers` 154–159 (Windows); `MAX_OFFSET` 161–163; `LocalTime` + `is_plausible` 165–180; `local_time` 182–201 (clock, then a cfg'd offset); `Spawn` 203–220; the environment allowlists `ENVIRONMENT_NEEDED` (cfg windows/not) 225–242, `ENVIRONMENT_WINDOW` 243–265, `ENVIRONMENT_SOUND` 266–269, `ENVIRONMENT_CORE` 270–272, `ENVIRONMENT_UPDATER` (cfg debug) 274–281; `environment` 283–298; `Input`/`Output` aliases (cfg) 300–311; `Process` 313–327 with the private `inner` (`Child` or `windows::Inner` by cfg); `kill`/`wait` 329–359 (each a cfg pair calling the same method); `spawn` 361–393 (Windows delegates; otherwise builds the `Command`, macOS through `macos::command`); `tests` 395–475 (81 lines; two of them re-run the test binary by test path). Seven concepts: the role model, the apply dispatch, the environment policy, the time, the process handle, the spawn, two Windows installer entry points.

**`confine/src/broker.rs` (1016).** Doc 1–18; bounds 30–44; `KIND_*` 46–61; `COOKIE_KEY_BYTES`, `HTTPS_PORT`, `MAX_UPDATE_STATE` 62–69; `Program` 71–86, `UpdaterGrant` 88–96, `impl Program` 98–156; `Exit` 158–177; `Request` 179–213; `Reply` 215–238; `push_text` 240–248; `Fields` 250–286; `frame` 288–295; `encode_request` 297–338; `decode_request` 340–374; `encode_reply` 376–422; `decode_reply` 424–455; `header` 457–465; `Channel` with cfg'd fields and cfg'd `read_frame`/`write` 467–502; the core's side: `Broker` 506–515, `Helper`/`How` 517–534, `impl Helper` 536–580 (`local` has a cfg pair), `impl Broker` 582–739 (`from_parent` and `ask` each a cfg pair; `spawn`, `read_source`, `local_time`, `cookie_key`, `healthy`, `update_state`, `open_web`); the broker's side: `Handlers` 743–761, `Core` 763–769, `start_core` 771–811 (a unix arm with a macOS/other pair inside, and a windows arm), `Helpers` 813–817, `serve` 819–844, `answer` 846–911, `start_helper` 913–924, `send_spawned` 926–947 (cfg pair); `tests` 949–1016 (68 lines). Six concepts: the wire format (240–465), the program table, the channel, the client, the server, and the per-OS pipe passing threaded through four functions.

**`confine/src/windows.rs` (717).** Doc 1–29; `#![allow(unsafe_code)]` and the module-wide `undocumented_unsafe_blocks` allow with its one argument 31–35; `mod mitigation` 85–101; SIDs and container names 103–118; `remove_containers` 120–130; ACL constants and `ATTRIBUTES` 131–140; `Inner` with `raw_process` (`pub(crate)`), `kill`, `wait`, `Drop` 142–179; `Owned` 181–190; `Sid` 192–209; `ContainerSid` 211–218; `wide` 220–223; `last_error` 225–228; `command_line` 230–263; `environment_block` 265–277; `pipe`, `keep_ours` 279–293; `job` 295–337; `restricted_token` 339–363; `container` 365–386; `Attributes`, `attributes`, `add_attribute`, `add_attribute_at` 388–422; `start` 424–522 (96 lines, `too_many_lines` allowed); `grant`, `grant_packages_read`, `grant_to` 524–585; `duplicate_into` 587–596 (`pub(crate)`); `SECONDS_PER_MINUTE`, `local_offset` 598–616; `file_from_handle_value` 618–627 (`pub(crate)`); `spawn` 629–695; `tests` 697–717 (21 lines). 44 unsafe blocks. Eleven Win32 objects in one file.

**`confine/src/linux.rs` (318).** Doc 1–20; path allowlists 31–47; `families` 49–61; `no_new_privileges` 63–71 and `network_namespace` 73–96 (three unsafe blocks, each with its own statement-level `#[allow(unsafe_code, reason)]` and a SAFETY comment — the only file of the three that gates per statement); `readable` 98–129; `LANDLOCK_ABI`, `read_access` 131–140; `landlock` 142–175; `enforced` 177–184; `architecture` 186–197 (`cfg!(target_arch)`); `number`, `always` 199–208; `seccomp` 210–300 (90 lines; the deny list 214–254 is data; an x86-64 `cfg` at 258); `apply` 302–318. No tests (the probe covers it). Five concepts: path policy, the namespace, Landlock, seccomp, the order.

**`confine/src/macos.rs` (196).** `preamble` 20–33; `home` 35–38; `SYSTEM_READS` 40–45; `profile` 47–144 (96 lines, five role arms of profile text); `command` 146–151; `tests` 153–196 (44 lines). One concept.

**`confine/src/unix.rs` (233).** `#![allow(unsafe_code)]` 9; `MAX_DESCRIPTORS`, `CONTROL_BYTES` 17–21; `control_length` ×2 by cfg 23–33; `send` 35–79; `receive` 81–137 (Linux/macOS cfg at 93–96 and 129–133); `extern "C" tzset` 139–144; `local_offset` 146–167; `tests` 169–233 (65 lines; one re-runs the test binary by path). Eleven unsafe blocks. Two concepts: descriptor passing (decision 56) and the C library's zone (decision 57), sharing only `libc`.

**`confine/src/bin/confine-probe.rs` (75), `confine/tests/probe.rs` (71).** One concept each; the probe needs `seccompiler` and `libc` directly. Unchanged by this plan.

**`launcher/src/lib.rs` (450).** Doc 1–21; `#![deny]` 23–32; mods and re-exports 34–44; `HEALTH_DEADLINE`, `COPYING_SUFFIX` 59–68; `Launcher` + `Debug` 70–89; `Chosen` 91–108; `Ended` 110–119; `pinned_signer` 121–133 (a cfg pair for the Windows arm); `io_text` 135–137; `impl Launcher` 139–450 (312 lines): `this` 145–150, `run` 159–185 (the lock protocol), `open_lock` 187–190, `read_state` 197–208, `recovered` 211–227 (macOS hook 213), `write_state` 233–235, `prepare` 241–295 (macOS hooks 248, 262), `candidates` 300–315, `accept` 318–352 (macOS hook 327), `copy_in` 363–376, `tidy` 380–410 (macOS hooks 391, 408), `commit` 417–438, `tidy_versions` 441–449. No tests (covered by `tests/launcher.rs`). Six concepts: the lock, state I/O and recovery, acceptance and trial, tidying, commit, the signer.

**`launcher/src/main.rs` (69).** `main` 24–35; `run` 37–69: six cfg sites dispatching `--install`, `--uninstall-from`, `--uninstall` and the macOS translocation check. Logic in `main.rs`, against convention 2.

**`launcher/src/install.rs` (75).** `NEW_LAUNCHER`, `OLD_LAUNCHER`, `LINUX_LAUNCHER` 13–19; `launcher_release` 27–40 (cfg arms); `linux_launcher_release` 47–65; `forget_old_launcher` 69–75. One concept — section 7's launcher release — under a name that says installation.

**`launcher/src/start.rs` (94).** `MAX_LINE` 19; `start` 25–81 (`cfg(unix)` process group 30–35); `end_whole` 86–94. One concept.

**`launcher/src/macos.rs` (199).** `version_of` 26–30; `bundle` 32–34; `installed` 37–39; `reconcile` 45–74; `holds_old_current` 78–82; `move_old_current` 86–104; `tidy_previous` 108–120; `must_move` 127–131; `writable_folder` 134–143; `applications` 149–157; `offer_move` 165–187; `tests` 189–199. Two concepts: the bundle swap, and translocation with the move to Applications (a dialog flow through `os_install`).

**`launcher/src/unix.rs` (218).** `confirm` 20–26; `TakeLine` 29–39; `data_home` 42–47; `desktop_entry` 51–53; `path_link` 57–59; `desktop_text` 64–69; `link_on_path` 73–89 (a dead `cfg(not(unix))` arm 84–88 inside a `cfg(unix)` module); `APPARMOR_RESTRICTION`, `APPARMOR_TARGET` 94–96; `install_linux` 107–160; `uninstall` 168–205; `tests` 207–218. Four concepts: a terminal prompt, the XDG desktop entry and path link, the Linux install, the macOS-and-Linux uninstall. The name fits only the last.

**`launcher/src/windows.rs` (137).** `launcher_copy` 20–22; `CHOICES` 25; `shortcut` 29–31; `launcher_release` 40–60; `UNINSTALL_FROM`, `AND_SETTINGS` 63–65; `uninstall` 73–97; `STUB_TRIES`, `STUB_TRY_INTERVAL` 102–103; `uninstall_from` 111–137. Two concepts (release, uninstall), under the size floor.

**`launcher/src/bin/launcher-test-broker.rs` (101), `launcher/tests/launcher.rs` (348).** One concept each; unchanged. The tests need `CARGO_BIN_EXE_launcher-test-broker`, `CARGO_TARGET_TMPDIR`, `ring`, a debug build (fault points), and re-run their own binary with `--exact fault_child`.

**`update/src/*`.** Fourteen files, one concept each, 39–318 lines; every test module 20–60 lines but `accept.rs`'s (84, with two `pub(crate)` helpers nothing else uses). `accept.rs` holds the completeness check and acceptance together with the Linux and macOS signers (122–174) and the `Keys` record (29–37); the Windows signer is in `os-install/src/windows.rs` 124–149 because it needs Win32. `files.rs` carries twelve `cfg(unix)` sites for modes and flushing. `layout.rs` holds the core's `settings_folder` (requirement 19.1) beside the installation layout.

**`tuf/updater/src/lib.rs` (249).** Doc 1–15; `#![deny]` 17–26; `pub mod transport` 28; constants 42–57; `limits` 61–63; `Config` 67–80; `target_name`, `now` 84–92; `impl Config` 94–220: `metadata`, `last_success`, `record_success`, `load` 114–124, `check` 130–135, `fetch` 141–153, `download` 161–219 (59 lines); `sync_tree` 223–230; `newest` 234–237; `chain` 240–249. Two concepts, lightly mixed: the TUF client and the staging writer. Logic in the crate root, against convention 2.

**`tuf/updater/src/main.rs` (94).** `proxy` 39–46; `run` 48–94 (layout, `confine::apply` first, the transport, the runtime, the wire loop). Logic in `main.rs`.

**`tuf/updater/src/transport.rs` (235).** `Https` 42–125 (`new`, `authority`, `connect`, `get`); `read_response` 132–186; the `Transport` impl 192–211; `tests` 213–235. One concept.

**`tuf/release/src/main.rs` (168).** `mod` lines 36–39; the argument helpers 65–101; `run` 103–168 (a sixteen-arm match). Logic in `main.rs`.

**`tuf/release/src/host.rs` (120).** A `[[bin]]` at `src/host.rs` rather than `src/bin/` (the other three test binaries of these crates are under `src/bin/`), and listed in `NO_PANIC_ROOTS` by that path. `run` 45–88, `serve` 90–120. One concept.

**`tuf/release/src/{keys,repo,test_identity}.rs`.** One concept each.

**`tuf/release/src/package.rs` (203).** `BUNDLE_IDENTIFIER`, `MACOS_MINIMUM`, `info_plist` 16–57 (a plist text); `APPARMOR` 59–75 (a profile text); `layout` 82–104; `manifest` 111–126; `sign_linux` 133–145; `sign_file` 152–156; `check` 165–183 (the same signer match as `launcher::pinned_signer`); `targets` 191–203. Two texts beside five operations.

**`tuf/release/tests/updates.rs` (390).** Needs both release binaries, a loopback port with `localhost` resolving, tokio, a debug build. Unchanged.

**`installer/src/main.rs` (164).** `mod payload` 26–29 (`include!` of the generated list); `main` 37–45; `report` 47–51; `run` (not Windows) 53–57; `run` (Windows) 59–147 (88 lines: unpack the payload into `installing/`, accept, place, grant, state, shortcut, uninstall entry, start); `folder_size` 154–164. The whole installer in `main.rs`.

**`installer/src/shortcut.rs` (239).** MS-SHLLINK writer; `tests` 187–239 (53 lines). One concept.

**`os-install/src/lib.rs` (71), `macos.rs` (95).** One concept each (dialog dispatch; CoreFoundation's alert, three unsafe blocks with SAFETY comments).

**`os-install/src/windows.rs` (233).** `wide`, `size_of_u32` 32–40; `ask`, `tell` 42–50; `signer_key` 57–77; `pinned_key` 81–120; `WindowsSigner` 124–149; `UNINSTALL_KEY` 152; `UninstallEntry` 155–171; `Key` 174–180; `set_text`, `set_number` 182–194; `uninstall_entry` 202–223; `remove_uninstall_entry` 229–233. About eighteen unsafe blocks, argued once at 7–10. Three concepts: dialogs, Authenticode, the registry.

**`release-identity`, `web-opener`, `stub`.** One concept each; nothing to do.

**`site/src/terminal.rs` (1540).** Doc 1–22; `CHANNEL`, `DEFAULT_PORT`, `MAX_HEAD`, `FRAME` 44–53; EN 300 706 codes, `ESCAPE`, `ESCAPE_OFFSET`, `PAGE_STATUS`, `ENGLISH_HASH`, `COLUMNS` 55–78; `PAGES`, `PROGRESS_CELLS`, `SOLID_MOSAIC`, `SECONDS_PER_MINUTE` 80–95; `Row` 97–127; `USED` 129–131; `Page` with `tti` 133–188; `page_modes` 190–200; `Push` 202–208; `PIANO`, note and effect constants, handles, `AUDIO_CHANNELS` (asserted against `podcast::CHANNEL`), `AUDIO_SERVICE` 210–263; `fire_sound`, `noise`, `hit_sound`, `click_sound`, `bell_sound`, `tune`, `note` 265–341; playfield constants 343–352; `Happened` 354–361; `Invaders` 363–375 with `new`, `tick` 384–432, `page` 434–473; `Field` 476–483; `Settings` 485–492; `Session` (21 fields) 494–524; `Phone`, `PhoneEvent` 526–539; `impl Session` 541–1054 (514 lines): `new` 542–568, `render` 571–595, `typing` 597–622, `piano` 624–643, `links` 645–656, `phone_page` 658–676, `podcast_page` 678–710, `go` 712–717, `select` 722–763, `item` 766–808, `welcome` 812–820, `release_all` 823–827, `down` 829–896, `up` 898–907, `character` 911–934, `sounds` 938–959, `play` 962–982, `listen` 985–989, `podcast_frame` 993–1004, `frame` 1007–1020, `start_phone` 1022–1027, `phone_events` 1030–1053; `phone` 1056–1095 (the qrkeyboard screen thread); `describe` 1097–1116; `index` 1118–1132; `page_file` 1134–1141; `contents_file` 1143–1151; `respond` 1153–1157; `session` 1159–1207 (the WebSocket loop); `send` 1209–1214; `serve` 1216–1260; `run` 1262–1276; `tests` 1278–1540 (263 lines; they read `Session`'s and `Invaders`'s private fields). Twelve concepts.

**`site/src/podcast.rs` (417).** Constants 19–46 (the WAVE layout among them); `Episode` 49–63; `u16_at`, `u32_at` 65–71; `read` 78–118 (the WAVE parser); `Player` 121–133; `impl Player` 135–260; `encode` 263–270 (names `crate::terminal::AUDIO_SERVICE`); `tests` 272–417 (146 lines). Two concepts; the tests are a third of the file.

**`site/src/build.rs` (264), `serve.rs` (199), `websocket.rs` (147), `main.rs` (64).** One concept each; `build` 177–264 is 88 lines; `serve.rs` mixes HTTP file serving, the SSE push and the live-page rotation, under the ceiling.

### 2.2 Functions over 80 lines and `impl` blocks over 300

| Where | Item | Lines | Note |
|---|---|---|---|
| `confine/src/windows.rs` 427–522 | `start` | 96 | `#[allow(clippy::too_many_lines)]` at 426; one `CreateProcess` with its attributes |
| `confine/src/macos.rs` 49–144 | `profile` | 96 | five role arms of profile text; one function per role would be the split |
| `confine/src/linux.rs` 211–300 | `seccomp` | 90 | the deny list 214–254 is a table |
| `installer/src/main.rs` 60–147 | `run` (Windows) | 88 | four phases |
| `site/src/build.rs` 177–264 | `build` | 88 | |
| `site/src/terminal.rs` 541–1054 | `impl Session` | 514 | |
| `launcher/src/lib.rs` 139–450 | `impl Launcher` | 312 | |

Clippy's `too_many_lines` threshold is 100 and the three longest functions are within four to ten lines of it: no move may add lines to them. Between 50 and 80 lines: `terminal.rs` `down` 68, `broker.rs` `answer` 65, `windows.rs` `spawn` 67, `release/main.rs` `run` 66, `updater/lib.rs` `download` 59, `launcher/lib.rs` `prepare` 55, `transport.rs` `read_response` 55, `unix.rs` `receive` 57, `start.rs` `start` 57, `unix.rs` (launcher) `install_linux` 54.

### 2.3 `cfg` sites inside shared files

`cfg(test)` and `debug_assertions` left out. Dispatch-only files (`os-install/src/lib.rs` 9 sites, `web-opener/src/lib.rs` 4, `launcher/src/main.rs` 6, `installer/src/main.rs` 5, `update/src/files.rs` 12, `update/src/layout.rs` 2, `update/src/platform.rs` 4, `tuf/release/src/main.rs` 2, `tuf/release/src/package.rs` 2, `launcher/src/start.rs` 2, `launcher/src/install.rs` 4) are as convention 3 allows: one item with two forms. The mechanisms inside shared files are these:

| File | Sites | What they gate |
|---|---|---|
| `confine/src/lib.rs` | 47, 49, 51, 53; 120, 124, 129, 134; 149, 156; 193, 195, 197; 225, 241; 301, 304, 307, 310; 321, 323; 335, 339, 350, 354; 367, 371, 374, 376, 387, 389; 453 | the `mod`s; `apply`'s four arms; two Windows entry points; `local_time`'s offset; `ENVIRONMENT_NEEDED`; `Input`/`Output`; `Process.inner`; `kill`/`wait`; `spawn`'s Windows arm and its macOS/other `Command`; a Windows test |
| `confine/src/broker.rs` | 469, 471, 473; 480, 482; 495, 497; 540, 545; 589, 598; 613, 626; 778, 782, 784, 796, 798, 803; 929, 935 | `Channel`'s fields, `read_frame`, `write`; `Helper::local`; `from_parent`; `ask`; `start_core`; `send_spawned` |
| `launcher/src/lib.rs` | 35, 38, 40, 43; 128, 130; 213; 248, 262; 327; 391, 408 | the `mod`s; `pinned_signer`'s Windows arm; macOS hooks in `recovered`, `prepare`, `accept`, `tidy` |
| `launcher/src/unix.rs` | 80, 84 | a dead `cfg(not(unix))` arm inside a `cfg(unix)` module |
| `confine/src/unix.rs` | 25, 30, 93, 95, 129 | Linux against macOS inside a per-OS file (`socklen_t`, `MSG_CMSG_CLOEXEC`, `FD_CLOEXEC`) — one-line differences, as allowed |
| `confine/src/linux.rs` | 188, 190, 192, 258 | `target_arch` inside a per-OS file — allowed |

### 2.4 Duplicated shapes

| # | Shape | Where |
|---|---|---|
| 1 | A bounded field reader (`take`/`u8`/…/`end`), `frame` and a five-byte header | `confine/src/broker.rs` 250–286, 288–295, 457–465 and `update/src/wire.rs` 77–118, 124–132, 135–146; `HEADER_BYTES = 5` at `broker.rs` 44 and `wire.rs` 24 |
| 2 | `wide()` (UTF-16 with a terminator) | `confine/src/windows.rs` 221–223, `os-install/src/windows.rs` 33–35, `web-opener/src/windows.rs` 15–17 |
| 3 | A structure's size as `u32` | `os-install/src/windows.rs` 38–40 `size_of_u32` against inline `u32::try_from(size_of::<T>()).unwrap_or(0)` at `confine/src/windows.rs` 284, 311, 330, 357, 474 |
| 4 | "HOME if absolute" | `confine/src/macos.rs` 36–38, `update/src/layout.rs` 72–74, `launcher/src/unix.rs` 46 and 58, `launcher/src/macos.rs` 154 (without the check), `confine/src/linux.rs` 105, 115 |
| 5 | `XDG_DATA_HOME` resolution | `launcher/src/unix.rs` 42–47 and `update/src/layout.rs` 84–88 |
| 6 | "`path: error`" formatting | `launcher/src/lib.rs` 135–137 `io_text`; `installer/src/main.rs` 79; `tuf/updater/src/lib.rs` 115, 174, 200, 214–216; throughout `tuf/release/src/{package,repo}.rs` |
| 7 | The pinned-signer match with a `cfg(windows)` arm | `launcher/src/lib.rs` 123–133 and `tuf/release/src/package.rs` 173–181; `WindowsSigner { key: release_identity::WINDOWS_SIGNER }` built directly at `launcher/src/windows.rs` 49 and `installer/src/main.rs` 110, bypassing `release_identity::keys()` |
| 8 | A version-folder scan (`read_dir` → `file_name` → `Version::parse`) | `launcher/src/lib.rs` 216–219, 300–309, 383–390, 401–405, 443–447; `launcher/src/unix.rs` 110–116 |
| 9 | An HTTP head reader and `respond` | `site/src/serve.rs` 96–100 and `site/src/terminal.rs` 1153–1157 (`respond`, byte-identical); `serve.rs` 127–143 and `terminal.rs` 1219–1232 (the head loop, `MAX_HEAD` at `serve.rs` 20 and `terminal.rs` 49); `tuf/release/src/host.rs` 94–102 (a third, byte at a time) |
| 10 | TTI escape writing (`ESCAPE`, code + 0x40) | `site/src/build.rs` 119–131 and `site/src/terminal.rs` 160–175; the constants at `build.rs` 32–33, `terminal.rs` 71–72, `serve.rs` 28 |
| 11 | A thread-per-connection accept loop | `site/src/serve.rs` 190–197, `site/src/terminal.rs` 1267–1274, `tuf/release/src/host.rs` 68–83 |
| 12 | A current-thread tokio runtime | `tuf/release/src/main.rs` 99–101, `tuf/updater/src/main.rs` 67, `tuf/release/tests/updates.rs` 162–164 |
| 13 | Scratch-folder test helpers | `update/src/accept.rs` 209–213, `update/src/files.rs` 207–212, `update/src/profile.rs` 53–55, `site/src/podcast.rs` 341–343 (`temp_dir`); `tuf/release/tests/updates.rs` 36–41, `launcher/tests/launcher.rs` 70–75 (`CARGO_TARGET_TMPDIR`) |
| 14 | The reversed-marker trick | `update/src/mark.rs` 25 and `launcher/src/bin/launcher-test-broker.rs` 17, 22 (deliberate, commented at 20–22) |
| 15 | `VoiceSink` test sinks and a `hear` helper | `site/src/podcast.rs` 307–337 (`Heard`) and `site/src/terminal.rs` 1389–1401, 1441–1449 (`Count`) |
| 16 | `Refused` newtypes of two shapes | `update/src/state.rs` 66, `gzip.rs` 72, `mark.rs` 31 (`&'static str`); `manifest.rs` 60 (`String`) |

Shapes 1 and 7 cross the `confine`/`update` and browser/`tuf` boundaries that the plan does not join (no new crate, no new dependency): they are recorded for `30-cross-cutting.md`, not moved. Shapes 9, 10 and 15 are within `site` and are addressed in section 6, not by a move.

### 2.5 Naming

| Where | What the name says | What the file holds | Action |
|---|---|---|---|
| `launcher/src/install.rs` | installing | section 7's launcher release | rename to `launcher_release.rs` (step L1) |
| `launcher/src/unix.rs` | Unix | a terminal prompt, the Linux install, the Unix uninstall | the Linux install into `unix/linux.rs` (step L2) |
| `tuf/release/src/host.rs` | a module | a `[[bin]]` (`neoteletext-test-host`); its siblings' test binaries are under `src/bin/` | move to `src/bin/test_host.rs` (step T4) |
| `launcher/src/lib.rs` `impl Launcher` | — | six concepts | split (steps L3–L5) |
| `confine::Role::Network`'s `name()` | `"fetcher"` | the fetcher and the phone keyboard | left; a wording question for the owner |
| `confine/src/windows.rs` 372 | `Role::Interface => CONTAINER_NETWORK` | a container name for a role that never takes a container | left; noted in section 6 |
| `macos.rs` (confine, launcher, os-install) against `dock-menu/src/mac.rs` | — | — | left; a sibling disagreement for `30-cross-cutting.md` |
| `MAX_HEAD` (site) against `MAX_REQUEST` (host, transport, broker) | — | the same bound | left; `30-cross-cutting.md` |
| `Refused` ×4 in `update` | — | two shapes | left; `30-cross-cutting.md` |

### 2.6 Measured now

| Measure | `confine` | `launcher` | `update` | `tuf` | `site` | others |
|---|---|---|---|---|---|---|
| Files of code (lines, largest / median) | 6 (1016 / 397) | 7 (450 / 137) | 14 (318 / 191) | 10 (249 / 170) | 6 (1540 / 232) | 11 (239 / 88) |
| Files over 500 | 2 | 0 | 0 | 0 | 1 | 0 |
| Functions over 80 lines | 3 | 0 | 0 | 0 | 1 | 1 (`installer`) |
| `impl` blocks over 300 | 0 | 1 | 0 | 0 | 1 | 0 |
| Test lines inline / in `tests.rs` | 279 / 0 | 23 / 0 | about 500 / 0 | 23 / 0 | 435 / 0 | 114 / 0 |
| `cfg` sites in shared files | 52 | 14 | 0 | 0 | 0 | 0 |

---

## 3. The target layout

Every file is named by its concept; a module with children is `foo.rs` beside `foo/` (convention 2); tests over about 60 lines go to `tests.rs` under the concept (convention 5); every public path in section 1 is kept by a `pub use` in the crate root unless a step says otherwise.

### 3.1 `confine`

```
confine/src/
  lib.rs              ~90   crate doc; #![deny] list; mod tree; pub use role::{Role, Report}, time::{LocalTime, MAX_OFFSET, local_time},
                            environment::environment, process::{Process, Input, Output}, spawn::{Spawn, spawn, apply};
                            #[cfg(windows)] pub use windows::{grant_packages_read, remove_containers}; pub mod broker
  role.rs             ~55   Role, Role::name, Report, Display for Report                                       (lib.rs 56–108)
  environment.rs      ~85   ENVIRONMENT_* allowlists, environment()                                              (lib.rs 222–298)
  time.rs             ~50   MAX_OFFSET, LocalTime, is_plausible, local_time() (one cfg pair for the offset)     (lib.rs 161–201)
  process.rs          ~110  Input, Output, Process (fields private), Process::new (pub(crate)), kill, wait,
                            take_files (pub(crate); the pipe-to-File step of Helper::local)                     (lib.rs 300–359; broker.rs 540–546)
  spawn.rs            ~90   Spawn; spawn() and apply() as three-arm dispatches to the platform files            (lib.rs 110–139, 203–220, 361–393)
  spawn/tests.rs      ~85   environment_probe, a_helper_gets_only_the_environment_it_is_given,
                            a_helper_whose_container_cannot_be_made_is_not_started (windows), a_report_reads_as_a_list   (lib.rs 395–475)
  broker.rs           ~150  decision-56 doc; the bounds and KIND_* table; Program, UpdaterGrant, HTTPS_PORT, impl Program;
                            the cfg'd `use` of the platform Channel; mod wire; mod client; mod server; pub use of the API   (broker.rs 1–156)
  broker/wire.rs      ~300  Exit, Request, Reply, push_text, Fields, frame, header, encode/decode ×4; tests inline (68 lines)   (broker.rs 158–465, 949–1016)
  broker/client.rs    ~220  Broker, Helper, How, impl Helper, impl Broker — no cfg                              (broker.rs 506–739)
  broker/server.rs    ~190  Handlers, Core, start_core, Helpers, serve, answer, start_helper, send_spawned — no cfg   (broker.rs 743–947)
  linux.rs            ~50   module doc (the order); pub(crate) fn apply; mod paths; mod namespace; mod landlock; mod seccomp   (linux.rs 1–20, 302–318)
  linux/paths.rs      ~100  RESOLVER_PATHS … SOUND_HOME_PATHS, families(), readable()                            (linux.rs 31–61, 98–129)
  linux/namespace.rs  ~45   no_new_privileges(), network_namespace()                 #![expect(unsafe_code)]    (linux.rs 63–96)
  linux/landlock.rs   ~65   LANDLOCK_ABI, read_access(), landlock(), enforced()                                  (linux.rs 131–184)
  linux/seccomp.rs    ~120  architecture(), number(), always(), seccomp()                                        (linux.rs 186–300)
  macos.rs            ~215  as today, plus pub(crate) fn apply() returning the fixed Report                      (macos.rs; lib.rs 124–128)
  unix.rs             ~100  module doc; command(&Spawn) (macOS through crate::macos::command, else Command::new),
                            spawn(&Spawn) -> Process, start_core(&Spawn) -> (Process, Channel); mod descriptors; mod time; mod channel
                                                                                                                 (lib.rs 371–392; broker.rs 778–802)
  unix/descriptors.rs ~135  MAX_DESCRIPTORS, CONTROL_BYTES, control_length, send, receive; one test inline   #![expect(unsafe_code)]   (unix.rs 17–137, 215–232)
  unix/time.rs        ~90   tzset, local_offset; two tests inline                                          #![expect(unsafe_code)]   (unix.rs 139–167, 175–213)
  unix/channel.rs     ~85   Channel { stream }, from_stdin (the socket check), read_frame, write,
                            receive_reply (header + descriptors), send_spawned (frame + two descriptors)       (broker.rs 467–502 unix arms, 589–597, 613–625, 929–934)
  windows.rs          ~130  module doc (windows.rs 1–29); spawn(&Spawn) -> Process; pub(crate) fn apply(); the two documented
                            pub wrappers grant_packages_read and remove_containers (lib.rs 141–159); mod lines, each with
                            #[allow(clippy::undocumented_unsafe_blocks, reason = <the one argument of windows.rs 32–35>)]   #![expect(unsafe_code)]   (windows.rs 629–695; lib.rs 129–159)
  windows/handles.rs  ~130  Owned, Sid, ContainerSid, wide, last_error, pipe, keep_ours, duplicate_into, file_from_handle_value   #![expect]   (181–228, 279–293, 587–596, 618–627)
  windows/process.rs  ~85   Inner (kill, wait, Drop, raw_process), command_line, environment_block; two tests inline   #![expect]   (142–179, 230–277, 697–717)
  windows/job.rs      ~50   job()                                                                          #![expect]   (295–337)
  windows/token.rs    ~40   LOW_INTEGRITY_SID, ADMINISTRATORS_SID, restricted_token()                      #![expect]   (103–106, 339–363)
  windows/container.rs ~85  INTERNET_CLIENT_SID, PRIVATE_NETWORK_SID, CONTAINER_*, CONTAINERS, container(), remove_containers()   #![expect]   (107–130, 365–386)
  windows/attributes.rs ~165 mod mitigation, ATTRIBUTES, Attributes, attributes(), add_attribute(_at), start()   #![expect]   (85–101, 139–140, 388–522)
  windows/acl.rs      ~80   ALL_APPLICATION_PACKAGES_SID, GENERIC_*, INHERIT_TO_ALL, grant(), grant_packages_read(), grant_to()   #![expect]   (131–138, 524–585)
  windows/time.rs     ~25   SECONDS_PER_MINUTE, local_offset()                                            #![expect]   (598–616)
  windows/channel.rs  ~75   Channel { reader, writer }, from_stdin_stdout, read_frame, write,
                            receive_reply (the 16-byte handle tail), send_spawned (duplicate ×2, re-frame) — no unsafe   (broker.rs 467–502 windows arms, 598–604, 626–640, 935–946)
  bin/confine-probe.rs      unchanged
tests/probe.rs              unchanged
```

**Public paths kept.** `confine::{Role, Report, Spawn, Process, Input, Output, spawn, apply, environment, LocalTime, MAX_OFFSET, local_time, grant_packages_read, remove_containers}` and `confine::broker::{Program, UpdaterGrant, Exit, Request, Reply, Broker, Helper, Handlers, Core, start_core, serve, encode_request, decode_request, encode_reply, decode_reply, MAX_HELPERS, MAX_ARGUMENTS, MAX_TEXT, MAX_REPLY, COOKIE_KEY_BYTES, MAX_UPDATE_STATE}` — every importer in section 1.1 and the two fuzz targets compile unchanged.

**The de-cfg of the broker.** Today `Channel` is one struct whose fields and methods are cfg pairs, and four functions of the client and server (`Helper::local`, `from_parent`, `ask`, `start_core`, `send_spawned`) carry the per-OS halves of pipe passing inline. In the target each platform has a `Channel` of its own with the same five method names (`from_stdin`/`from_stdin_stdout`, `read_frame`, `write`, `receive_reply`, `send_spawned`) in `unix/channel.rs` and `windows/channel.rs`; `broker.rs` holds the two `#[cfg] use` lines that pick one; `client.rs` and `server.rs` call `Channel::…` and carry no `cfg`. Likewise `spawn`'s and `start_core`'s per-OS halves become `unix::spawn`/`unix::start_core` and `windows::spawn`/`windows::start_core` (the latter already exists as `windows::spawn`; `start_core` on Windows is `spawn` plus taking the two pipes), and `spawn.rs` and `server.rs` each keep one `#[cfg] use`. The bytes on the wire, the descriptors sent and the handle values are unchanged: this is a move of code between files, the only reshaping being that a function's two arms become two functions of the same name in two files.

**Departures, with reasons.** (a) `windows/job.rs`, `token.rs`, `time.rs` are under the 150-line floor; the owner asked for one Win32 object per file, and each is one mechanism with its own constants. (b) `linux.rs` and `unix.rs` hold the spine (`apply`'s order; the Unix `spawn`), not re-exports alone, so neither is a parent that convention 2 would flatten. (c) `macos.rs` stays flat: one concept, 196 lines, one child would make a directory of one file.

### 3.2 `launcher`

```
launcher/src/
  lib.rs                  ~60   crate doc; #![deny]; mod tree; pub use launcher::{Launcher, Chosen, Ended, HEALTH_DEADLINE, pinned_signer},
                                command::run; #[cfg(target_os = "macos")] pub use macos::{must_move, offer_move}; pub mod unix; pub mod windows
  launcher.rs             ~150  HEALTH_DEADLINE; Launcher + Debug; Chosen; Ended; pinned_signer; io_text (pub(crate)); impl Launcher { this, run, open_lock }   (lib.rs 59–65, 70–190)
  command.rs              ~50   run(arguments): the argument dispatch, from main.rs                                   (main.rs 37–69)
  state.rs                ~70   impl Launcher { read_state, recovered, write_state }                                  (lib.rs 192–235)
  trial.rs                ~200  COPYING_SUFFIX; impl Launcher { prepare, candidates, accept, copy_in, commit }           (lib.rs 66–68, 237–376, 412–438)
  tidy.rs                 ~55   impl Launcher { tidy, tidy_versions }                                                 (lib.rs 378–410, 440–449)
  start.rs                unchanged
  launcher_release.rs     ~75   renamed from install.rs                                                               (install.rs)
  unix.rs                 ~70   confirm, TakeLine, uninstall; mod linux; pub use linux::install_linux                   (unix.rs 1–39, 162–205)
  unix/linux.rs           ~140  data_home, desktop_entry, path_link, desktop_text, link_on_path, APPARMOR_*, install_linux; the desktop-entry test inline;
                                gated cfg(unix) through its parent, as today   (unix.rs 41–160, 207–218)
  macos.rs                ~125  the bundle: version_of, bundle, installed, reconcile, holds_old_current, move_old_current, tidy_previous;
                                mod translocation; pub use translocation::{must_move, offer_move}                     (macos.rs 1–120)
  macos/translocation.rs  ~85   must_move, writable_folder, applications, offer_move; one test inline                   (macos.rs 122–199)
  windows.rs              unchanged (137 lines; two concepts under one floor — left, see step L6)
  main.rs                 ~30   main() alone, calling launcher::run
  bin/launcher-test-broker.rs   unchanged
tests/launcher.rs               unchanged
```

**Public paths kept.** `launcher::{Launcher, HEALTH_DEADLINE, must_move, offer_move}`, `launcher::unix::{install_linux, uninstall}`, `launcher::windows::*`. New: `launcher::run` (for `main.rs`). The file `launcher.rs` inside the crate `launcher` is the convention's own naming (the type's file); the crate root re-exports it, so no path names the module.

### 3.3 `update`

Left as it is: fourteen files of one concept each, none over 320 lines, every test module but one under 60 lines. The departures tolerated, with reasons: `accept.rs` keeps its 84-line test module inline (the file is 260 lines; a `tests.rs` for one file would make a directory of one test file) and keeps the Linux and macOS signers beside `accept` (they are the only implementers of `Signer` in the crate and 53 lines together). `files.rs`'s twelve `cfg(unix)` sites are one-line differences of file modes and flushing, which convention 3 allows in a shared file.

### 3.4 `tuf`

```
tuf/updater/src/
  lib.rs              ~45   doc; #![deny]; mod tree; pub use client::{Config, newest, target_name, now, METADATA, MAX_ATTEMPTS},
                            staging::{PARTIAL, COMPRESSED}, transport::Https, helper::run
  client.rs           ~130  METADATA, CHECKED, MAX_CHECKED, MAX_ATTEMPTS; limits; Config; target_name; now; impl Config { metadata, last_success, load, check, fetch }; newest; chain   (lib.rs 42–153, 232–249)
  staging.rs          ~95   PARTIAL, COMPRESSED; impl Config { record_success, download }; sync_tree          (lib.rs 54–57, 106–108, 155–230)
  transport.rs        unchanged
  helper.rs           ~75   proxy(); run(): the process as the trusted core's helper (confine, then the wire loop)   (main.rs 38–94)
  main.rs             ~25   main() alone
  bin/updater-drive.rs      unchanged
tuf/release/src/
  main.rs             ~25   #![deny]; mod tree; main() alone
  command.rs          ~145  MAX_MESSAGE; platform, version, path, options, one, timestamp_days, runtime; run   (main.rs 51–168)
  keys.rs, package.rs, repo.rs, test_identity.rs   unchanged
  bin/test_host.rs    120   from src/host.rs; the [[bin]] name neoteletext-test-host stays
tests/updates.rs            unchanged
```

`package.rs` is left as it is: the `Info.plist` and AppArmor texts (16–75) are constants of their one user, and a file for each would be 20 and 45 lines. `updater::transport::{MAX_BODY, read_response}` (the fuzz target) and every path `release/tests/updates.rs` names are kept.

### 3.5 `installer`

```
installer/src/
  main.rs         ~40   #![deny]; mod tree; main(); report()
  payload.rs      ~75   mod payload (the include!), PAYLOAD_STUB, PAYLOAD_LAUNCHER, partial_name, unpack(): the payload written into `installing/`   (main.rs 26–35, 79–108)
  install.rs      ~90   run() for Windows and the not-Windows stub; folder_size, BYTES_PER_KIB                      (main.rs 53–77, 109–164)
  shortcut.rs     unchanged
build.rs          unchanged
```

### 3.6 `os-install`

```
os-install/src/
  lib.rs                 unchanged
  macos.rs               unchanged (95 lines, one concept)
  windows.rs             ~50   wide, size_of_u32, ask, tell; mod authenticode; mod registry; pub use …   #![expect(unsafe_code)]   (windows.rs 1–50)
  windows/authenticode.rs ~105 signer_key, pinned_key, WindowsSigner, impl Signer                      #![expect(unsafe_code)]   (windows.rs 52–149)
  windows/registry.rs    ~90   UNINSTALL_KEY, UninstallEntry, Key, set_text, set_number, uninstall_entry, remove_uninstall_entry   #![expect(unsafe_code)]   (windows.rs 151–233)
```

A departure from the floor (three files of 50–105 lines) for a file that holds three unrelated Win32 areas; the alternative is leaving 233 lines of three concepts.

### 3.7 `site`

```
site/src/
  main.rs, build.rs, serve.rs, websocket.rs   unchanged
  terminal.rs             ~110  module doc; CHANNEL, DEFAULT_PORT, PAGES; Settings; pub fn run; mod tree; pub use sounds::AUDIO_SERVICE   (terminal.rs 1–22, 44–47, 81–89, 485–492, 1262–1276)
  terminal/tti.rs         ~165  the EN 300 706 codes, ESCAPE, ESCAPE_OFFSET, PAGE_STATUS, ENGLISH_HASH, COLUMNS; Row; Page + tti(); page_modes; USED   (55–78, 97–200)
  terminal/sounds.rs      ~165  PIANO, the note and effect constants, the handles, AUDIO_CHANNELS and its assertion, AUDIO_SERVICE; fire_sound … note; library(): the (handle, samples) table of Session::sounds 938–948   (210–341)
  terminal/invaders.rs    ~135  the playfield constants; Happened; Invaders; new, tick, page                         (343–474)
  terminal/pages.rs       ~175  PROGRESS_CELLS, SOLID_MOSAIC, SECONDS_PER_MINUTE; Field; index; impl Session { typing, piano, links, phone_page, podcast_page }; page_file; contents_file   (90–95, 476–483, 597–710, 1118–1151)
  terminal/phone.rs       ~110  Phone, PhoneEvent; impl Session { start_phone, phone_events }; phone()            (526–539, 1022–1095)
  terminal/session.rs     ~330  Push; Session; impl Session { new, render, go, select, item, welcome, release_all, down, up, character, sounds (the packetising), play, listen, podcast_frame, frame }; describe; mod tests   (202–208, 494–524, 541–1020 less the methods above, 1097–1116)
  terminal/session/tests.rs ~265 the test module whole, a child of session so it keeps reading private fields          (1278–1540)
  terminal/server.rs      ~120  MAX_HEAD, FRAME; respond; session; send; serve                                        (48–53, 1153–1260)
  podcast.rs              ~250  the constants; Episode; Player; impl Player; encode; mod wave; mod tests                 (podcast.rs 1–63, 121–270)
  podcast/wave.rs         ~75   the WAVE constants, u16_at, u32_at, read()                                            (35–46, 65–118)
  podcast/tests.rs        ~150  the test module whole                                                                  (272–417)
```

`crate::terminal::AUDIO_SERVICE` (named by `podcast.rs` 267) and `podcast::{CHANNEL, SKIP_SECONDS, Episode, Player}` (named by `terminal.rs`) keep their paths. `Session`'s fields stay private: `pages.rs` and `phone.rs` are `impl Session` blocks, which see them; the tests are a child module. `Invaders`'s fields are read by `session.rs` (`left`, `right`, `ship`, `shots`, `over`) and by the tests (`alive`, `offset`, `drop`, `score`) — those nine of its eleven fields become `pub(super)` (step S1) rather than growing nine accessors in a development tool; a departure from convention 6, with that reason. That so many cross the seam says the game's input handling (`down`, `up`, `character`'s game arms) could later move into `invaders.rs` as its own `impl Session` block; not done here, to keep S1 a move.

### 3.8 `release-identity`, `web-opener`, `stub`

Unchanged. The one lint change asked by convention 8 — `web-opener/src/windows.rs` 3 and `os-install/src/macos.rs` 5 from `#![allow(unsafe_code, …)]` to `#![expect(unsafe_code, …)]` — rides with steps O1 and W1 below.

---

## 4. The moves

Each step is one commit that compiles and passes `scripts/check.sh commit`; a step that touches a platform directory is also run by hand on that platform before its commit (Linux on `foundintelquiet4060` through the full gate's stage, Windows in the virtual machine: `DEVELOPMENT.md` section 12). Every step's diff is a move (`git diff --color-moved=dimmed-zebra`); the non-moved lines are the `mod` lines, `use` lines, visibility words and file doc comments listed under it. The browser's `cargo fmt` is run on the unchanged tree first (`01-method-and-order.md` section 4) so that no move carries formatting.

### Phase B2: `confine` (steps C1–C9) and `update` (none)

**C1. `role.rs`, `time.rs`, `environment.rs` out of `lib.rs`.**
Moves `Role`, `impl Role`, `Report` (lib.rs 56–108) to `role.rs`; `MAX_OFFSET`, `LocalTime`, `local_time` (161–201) to `time.rs`; the five `ENVIRONMENT_*` constants and `environment` (222–298) to `environment.rs`. `lib.rs` gains `mod role; mod time; mod environment;` and `pub use role::{Role, Report}; pub use time::{LocalTime, MAX_OFFSET, local_time}; pub use environment::environment;`. `local_time`'s cfg pair for the offset (193–198) moves with it; `ENVIRONMENT_NEEDED`'s cfg pair (225–242) likewise. Visibility: none changes. Imports elsewhere: none. Tests: none move.

**C2. `process.rs` and `spawn.rs` out of `lib.rs`, with the tests to `spawn/tests.rs`.**
Moves `Input`, `Output`, `Process`, `impl Process` (300–359) to `process.rs`; `Spawn`, `apply`, `spawn` (110–139, 203–220, 361–393) to `spawn.rs`; the `tests` module (395–475) to `spawn/tests.rs`, declared `#[cfg(test)] mod tests;` at the end of `spawn.rs`. Not moved: `Process` gains `pub(crate) fn new(stdin, stdout, inner, report) -> Self` so that `spawn.rs` (and, from C8, the platform files) construct it without seeing its fields, `pub(crate) fn take_files(&mut self) -> (Option<File>, Option<File>)` (the pipe-to-`File` pair of broker.rs 540–546, a one-line cfg difference), and `#[cfg(windows)] pub(crate) fn raw_process(&self) -> HANDLE` forwarding to `Inner::raw_process` so that `broker.rs` 939 no longer reads `inner` (fields stay private, convention 6). `kill`/`wait` lose their cfg pairs (both arms call the same method; the type of `inner` already differs by cfg). `lib.rs`: `mod process; mod spawn; pub use process::{Process, Input, Output}; pub use spawn::{Spawn, spawn, apply};`; the two documented Windows wrappers (141–159) stay in `lib.rs` until C6 moves them into `windows.rs`. `spawn/tests.rs` adds `use crate::{Role, environment};` (they were in scope through `super::*` before). The test argument strings at lib.rs 424 and 457 are re-pointed from `tests::environment_probe` to `spawn::tests::environment_probe` (a test that must change to compile is noted in the commit). Run by hand on Windows: `a_helper_whose_container_cannot_be_made_is_not_started`.

**C3. `broker.rs` becomes `broker.rs` + `broker/{wire,client,server}.rs`.**
`broker.rs` keeps 1–156 (the doc, the bounds, the kinds, `Program`, `UpdaterGrant`) and the `Channel` struct with its cfg'd fields and methods (467–502) for this step; `broker/wire.rs` takes 158–465 and the tests 949–1016 (68 lines, inline); `broker/client.rs` takes 506–739; `broker/server.rs` takes 743–947. Visibility: in `wire.rs`, `Fields`, `frame`, `header`, `push_text`, `HEADER_BYTES`, `MAX_REQUEST`, `KIND_SPAWNED` become `pub(super)` (reached by the sibling `client.rs` and `server.rs`); nothing in `broker.rs` changes, since its children see its private `Channel`, `Program::code` and `from_code`. `broker.rs` gains `mod wire; mod client; mod server;` and `pub use wire::{Exit, Request, Reply, encode_request, decode_request, encode_reply, decode_reply}; pub use client::{Broker, Helper}; pub use server::{Handlers, Core, start_core, serve};` so that `confine::broker::*` is unchanged for `core`, its tests and the fuzz targets `broker_requests`, `broker_replies` (both workspaces' Clippy in the gate).

**C4. `linux.rs` becomes `linux.rs` + `linux/{paths,namespace,landlock,seccomp}.rs`.**
`linux.rs` keeps the doc (1–20) and `apply` (302–318), made `pub(crate)`; `paths.rs` takes 31–61 and 98–129 (`families`, `readable` → `pub(super)`); `namespace.rs` takes 63–96 (`no_new_privileges`, `network_namespace` → `pub(super)`), with `#![expect(unsafe_code, reason = "the C library calls for the network namespace and no-new-privileges (requirement 10.12)")]` at its head and the three statement-level `#[allow(unsafe_code)]` of 68, 81, 85 removed (a statement-level allow would leave a file-level `expect` unfulfilled); the SAFETY comments stay; `landlock.rs` takes 131–184; `seccomp.rs` takes 186–300 (`architecture`, `seccomp` → `pub(super)`). Verified on the Linux host: `confine`'s tests and `tests/probe.rs`.

**C5. `unix.rs` becomes `unix.rs` + `unix/{descriptors,time}.rs`.**
`unix.rs` keeps the doc (1–7) and `mod descriptors; mod time; pub(crate) use descriptors::{send, receive, MAX_DESCRIPTORS}; pub(crate) use time::local_offset;`. `descriptors.rs` takes 17–137 and the test 215–232; `time.rs` takes 139–167 and the tests 175–213. Each leaf carries `#![expect(unsafe_code, reason = …)]` (the reason split from unix.rs 9: descriptors for `sendmsg`/`recvmsg`, time for `tzset`/`localtime_r`); the parent carries none. The test path string at unix.rs 207 is re-pointed to `unix::time::tests::a_change_of_zone_is_seen_at_once`. Both halves verified on macOS and on the Linux host.

**C6. `windows.rs` becomes `windows.rs` + `windows/{handles,process,job,token,container,attributes,acl,time}.rs`.**
`windows.rs` keeps the doc (1–29) and `spawn` (629–695) and declares the eight modules. The two module-wide attributes at 31–35 are replaced by: `#![expect(unsafe_code, reason = …)]` at the head of `windows.rs` and of every leaf (each holds unsafe), and `#[allow(clippy::undocumented_unsafe_blocks, reason = "each call's safety is argued once, at this module's head: every handle and pointer passed is one this module made and still owns")]` as an outer attribute on each `mod` line in `windows.rs` (and as an inner attribute of `windows.rs` for `spawn`), so the argument is written once. Visibility: `Owned`, `Sid`, `ContainerSid`, `wide`, `last_error`, `pipe`, `keep_ours`, `job`, `restricted_token`, `container`, `grant`, `Attributes`, `attributes`, `add_attribute`, `add_attribute_at`, `start`, `command_line`, `environment_block` → `pub(super)`; `Inner::raw_process`, `duplicate_into`, `file_from_handle_value` stay `pub(crate)` (reached from `broker/` until C7, from `windows/channel.rs` after it); `local_offset` stays `pub(crate)`. The two documented wrappers `grant_packages_read` and `remove_containers` (lib.rs 141–159) move into `windows.rs` as `pub fn`, calling `acl::grant_to` and `container::remove_containers`, and `lib.rs` re-exports them (`#[cfg(windows)] pub use windows::{grant_packages_read, remove_containers};`), so `installer/src/main.rs` 126 and `launcher/src/windows.rs` 131 are unchanged. The two tests (697–717) go inline in `process.rs`. Built and its tests run in the virtual machine before the commit.

**C7. The per-OS `Channel`.**
Adds `unix/channel.rs` and `windows/channel.rs` holding, each, `Channel`, `read_frame`, `write` (the arms of broker.rs 467–502), a constructor from standard input (the arms of 589–604), `receive_reply` (the arms of 613–640, returning the payload and the pipes) and `send_spawned` (the arms of 929–946). `broker.rs` loses its `Channel` and gains `#[cfg(unix)] use crate::unix::channel::Channel; #[cfg(windows)] use crate::windows::channel::Channel;` (both `pub(super)`); `client.rs`'s `from_parent`, `ask` and `Helper::local`, and `server.rs`'s `send_spawned`, become single-arm calls on `Channel` and `Process::take_files`. The frame bytes, the descriptor count and the sixteen-byte handle tail are unchanged. Verified on all three platforms (`core/tests/confined_core.rs`, `sound/tests/confined.rs`, `decoder/tests/confined_bookmarks.rs`, and the browser run by hand).

**C8. The per-OS `spawn` and `start_core`.**
Moves the not-Windows arm of `spawn` (lib.rs 371–392, now in `spawn.rs`) and the unix arm of `start_core` (broker.rs 778–802, now in `server.rs`) into `unix.rs` as `command`, `spawn`, `start_core`; the macOS/other pair inside them (374–381, 782–790) becomes a two-arm `command()` in `unix.rs` (one line's difference: `macos::command` or `Command::new`, convention 3's allowance). On Windows `windows::start_core` wraps `windows::spawn` and takes the two pipes (broker.rs 805–809). `spawn.rs::spawn` and `server.rs::start_core` become one `#[cfg] use` and a call each. `macos::command` becomes `pub(crate)`.

**C9. The per-OS `apply`.**
The fixed-report arms of `apply` (lib.rs 124–133) become `pub(crate) fn apply()` in `macos.rs` and `windows.rs`; `spawn.rs::apply` becomes a three-arm dispatch plus the "no sandbox on this platform" error. After C9 the shared files hold only one-line differences: `spawn.rs` the two dispatches, `process.rs` the type aliases, `inner` and `take_files`, `time.rs` the offset, `environment.rs` `ENVIRONMENT_NEEDED`, `broker.rs` the `Channel` `use`; `broker/*.rs` none.

`update`: no steps.

### Phase B4: the outer ring

**L1. Rename `launcher/src/install.rs` to `launcher_release.rs`.** One `mod` line in `lib.rs`; `use` lines at `start.rs` 16 (`install` → `launcher_release`) and `unix.rs` 16 (`crate::install::LINUX_LAUNCHER`). No public path changes (`install` was `pub mod`; nothing outside the crate names it — `grep` over both repositories).

**L2. `unix.rs` becomes `unix.rs` + `unix/linux.rs`.** `unix/linux.rs` takes 41–160 and the test 207–218; the dead `cfg(not(unix))` arm (84–88) is dropped as the function enters a `cfg(target_os = "linux")` file (a change noted in the commit, not a move). `unix.rs` keeps 19–39 and 162–205, declares `mod linux;` (gated `cfg(unix)` by its parent, as `install_linux` is today: it is compiled on macOS and called only on Linux, `main.rs` 41–42) and `pub use linux::install_linux;` so `launcher::unix::install_linux` (main.rs 42) is unchanged. `confirm` becomes `pub(super)` if `linux.rs` needs it (it does not today).

**L3. `launcher.rs`, `state.rs`, `trial.rs`, `tidy.rs` out of `lib.rs`.** `launcher.rs` takes 59–65, 70–190; `state.rs` 192–235; `trial.rs` 66–68 and 237–376, 412–438; `tidy.rs` 378–410, 440–449 — each an `impl Launcher` block. Visibility: `io_text`, `open_lock`, `candidates`, `accept`, `copy_in`, `tidy`, `tidy_versions`, `recovered` → `pub(crate)` (reached across files and from `unix.rs`, `windows.rs`). `lib.rs` keeps the doc, the `#![deny]` list, the `mod` tree and `pub use launcher::{Launcher, Chosen, Ended, HEALTH_DEADLINE, pinned_signer};`. The six macOS hooks stay where they are inside `prepare`, `accept`, `tidy`, `recovered`.

**L4. `command.rs` out of `main.rs`.** `run` (main.rs 37–69) moves to `src/command.rs` in the library, re-exported as `launcher::run`; `main.rs` keeps `main` and the two crate attributes. The no-panic list stays in both roots (`NO_PANIC_ROOTS` names `launcher/src/main.rs`).

**L5. `macos.rs` becomes `macos.rs` + `macos/translocation.rs`.** `translocation.rs` takes 122–199 (its one test inline); `macos.rs` keeps 1–120 and declares `mod translocation; pub use translocation::{must_move, offer_move};` so `lib.rs` 43–44 is unchanged. `writable_folder` stays private to `translocation.rs`.

**L6. `windows.rs`: left.** Two concepts (the release at 20–60, the uninstall at 62–137) in 137 lines; a split would make two files of 45 and 80 lines for no reader's benefit. Recorded as a departure from "one concept per file".

**U1. `tuf/updater`: `client.rs`, `staging.rs`, `helper.rs`.** `client.rs` takes lib.rs 42–53, 58–63, 65–104, 110–153, 232–249; `staging.rs` takes 54–57, 106–108, 155–230 as a second `impl Config`; `helper.rs` takes main.rs 38–94 as `pub fn run() -> Result<(), String>`; `main.rs` keeps `main`. `lib.rs` keeps the doc and lints and re-exports `Config, Https, now, newest, target_name, METADATA, MAX_ATTEMPTS, PARTIAL, COMPRESSED, run`. Visibility: `Config::metadata`, `record_success`, `fetch`, `load` → `pub(super)`; `chain` → `pub(super)`. `tests/updates.rs` (in `release`) and `tuf/fuzz` compile unchanged. Gate: `cargo clippy` and `nextest` in `native/tuf` (part of `check.sh commit`), and `cargo clippy` in `native/tuf/fuzz` (the full gate).

**T1. `tuf/release`: `command.rs` out of `main.rs`.** 51–168 move; `main.rs` keeps the lints, `mod` lines and `main`. The `cfg(windows) use Path` (42) goes with `run`.

**T2. `tuf/release/src/host.rs` to `src/bin/test_host.rs`.** `tuf/release/Cargo.toml`'s `[[bin]] path` changes to `src/bin/test_host.rs` (the `name` `neoteletext-test-host` stays, so `CARGO_BIN_EXE_neoteletext-test-host` and `scripts/updates-e2e.*` are unchanged); `scripts/check.sh` `NO_PANIC_ROOTS` line 43 changes `native/tuf/release/src/host.rs` to `native/tuf/release/src/bin/test_host.rs` in the same commit (convention 8).

**I1. `installer`: `payload.rs` and `install.rs` out of `main.rs`.** `payload.rs` takes 26–35 and the unpack loop 79–108 as `pub(crate) fn unpack(layout) -> Result<(Version, PathBuf), String>`; `install.rs` takes 53–77, 109–147, 150–164; `main.rs` keeps `main` and `report`. The two `run`s keep their cfg pair in `install.rs`. Built and run by hand in the virtual machine (the end-to-end script `scripts/updates-e2e.ps1`). Departure: splitting `run` (88 lines) at the unpack boundary changes its shape (one function becomes two); the bytes written and their order are the same, and the commit says so.

**O1. `os-install/src/windows.rs` becomes `windows.rs` + `windows/{authenticode,registry}.rs`.** `authenticode.rs` takes 52–149; `registry.rs` 151–233; `windows.rs` keeps 1–50 and the `mod` lines with `pub use authenticode::{WindowsSigner, signer_key}; pub use registry::{UninstallEntry, uninstall_entry, remove_uninstall_entry};` so `lib.rs` 33 is unchanged. `wide`, `size_of_u32` → `pub(super)`. The head attributes (6–10) become `#![expect(unsafe_code, …)]` in each of the three files and the `undocumented_unsafe_blocks` allow an outer attribute on the two `mod` lines (as C6). In the same commit, `macos.rs` 5 changes `allow` to `expect` (convention 8). Verified in the virtual machine and on macOS.

**W1. `web-opener/src/windows.rs` 3: `allow` to `expect`.** One word; the file holds one unsafe block. Verified in the virtual machine.

**S1. `site/src/terminal.rs` becomes `terminal.rs` + `terminal/{tti,sounds,invaders}.rs`.** Constants, `Row`, `Page`, `page_modes`, `USED` to `tti.rs`; the sound table, constants and synthesis to `sounds.rs` (with `library()` cut from `Session::sounds` 938–948 as the table it is; the packetising 949–958 stays with `Session`); the game to `invaders.rs`. Visibility: `Row`, `Page`, `page_modes`, `USED`, the colour and escape constants, `PIANO`, the handles, `AUDIO_CHANNELS`, `NOTE_*`, `library`, `Invaders`, `Happened` → `pub(super)`; `Invaders::{left, right, ship, shots, over, alive, offset, drop, score}` → `pub(super)` (read by `Session` and its tests; section 3.7); `AUDIO_SERVICE` stays `pub` and `terminal.rs` re-exports it so `podcast.rs` 267 is unchanged.

**S2. `terminal/{pages,phone,server}.rs`.** `pages.rs` takes `Field`, `index`, the five page methods, `page_file`, `contents_file` and the three page constants; `phone.rs` takes `Phone`, `PhoneEvent`, `phone`, `start_phone`, `phone_events`; `server.rs` takes `MAX_HEAD`, `FRAME`, `respond`, `session`, `send`, `serve`; `run` returns to `terminal.rs`. `Push`, `Settings`, `Session` and its methods used across files (`render`, `item`, `frame`, `podcast_frame`, `phone_events`) → `pub(super)`.

**S3. `terminal/session.rs` and `terminal/session/tests.rs`.** What is left of the old file (`Push`, `Session`, its remaining methods, `describe`) becomes `session.rs`; the test module (1278–1540) moves whole to `session/tests.rs`, declared at the end of `session.rs`, so `use super::*` and the private-field reads compile as before (the tests also name `Invaders` fields, covered by S1's `pub(super)`). `cargo nextest run -p neoteletext-site`.

**S4. `podcast.rs` becomes `podcast.rs` + `podcast/{wave,tests}.rs`.** `wave.rs` takes 35–46 and 65–118 (`read` stays `pub`, re-exported as `podcast::read` for `main.rs` 48); the WAVE constants → private to `wave.rs` but `WAVE_PCM`, `BITS_16` → `pub(super)` for the test's `wave()` builder; `tests.rs` takes 272–417. `Episode` stays in `podcast.rs` (the player's input).

`release-identity`, `stub`, `build.rs`, `serve.rs`, `websocket.rs`: no steps.

---

## 5. Risks particular to these crates

| Risk | Where | How the steps meet it |
|---|---|---|
| **Requirement 10.12 names files.** Its verification clause (`docs/requirements.md` 704) says `confine` allows unsafe "only in `src/linux.rs`, `src/unix.rs` and `src/windows.rs`", and the 23 October amendment (706) says `os-install` "only in `src/macos.rs` and `src/windows.rs`". After C4–C6 and O1 the permitted places are the files `linux.rs`, `unix.rs`, `windows.rs` and the directories beside them. | C4, C5, C6, O1 | The requirement's text is amended in the same commit as the first of these (C4), to name the directories; `CLAUDE.md` 20 (which lists only `dock-menu` and `web-opener`) and `docs/architecture.md` 650 need no change. The `expect` attribute on each leaf makes the check mechanical: a leaf without unsafe cannot carry it, and a file with unsafe outside the set fails `unsafe_code = "deny"`. |
| **Documents name files that move.** `docs/sandboxing.md` 104 (`confine/src/unix.rs`, the descriptor passing → `unix/descriptors.rs`), 161 (`confine/src/lib.rs` for the Windows container test → `spawn/tests.rs`); `docs/history-and-bookmarks.md` 255 (`confine/src/linux.rs`, `readable` → `linux/paths.rs`); `docs/architecture.md` section 14's `confine/` line (`broker.rs`, `unix.rs`); `IMPLEMENTATION-LOG.md` 65 and `docs/installation-and-updates.md` 368 name files that do not move. | C2, C4, C5 | Each commit that moves a named file edits the line that names it; section 14 is rewritten once at B5. |
| **`NO_PANIC_ROOTS` and the `sed` pattern.** `scripts/check.sh` 39–43 lists eleven roots in scope; `check_no_panic_lists` extracts `/^#!\[deny(/,/^)\]/` and compares the eight lines verbatim. | T2; every step | No step makes or renames a root except T2, which edits the list in its commit. The `#![deny(...)]` block stays at column 0 in each root, once; no new file carries one. `lib.rs` files that become small (C-steps, L3, U1) keep the block. |
| **Bin names and `CARGO_BIN_EXE_*`.** `confine-probe` (`tests/probe.rs` 10), `launcher-test-broker` (`tests/launcher.rs` 106; `scripts/updates-e2e.*`), `neoteletext-release` and `neoteletext-test-host` (`tests/updates.rs` 25, 30, 63, 286; the scripts), `updater-drive`, `neoteletext-updater` (the scripts, `scripts/release/*`). | T2 | Only a source path changes; every `[[bin]] name` stays. |
| **Tests that re-run their own binary by test path.** `confine/src/lib.rs` 424, 457 (`tests::environment_probe`), `confine/src/unix.rs` 207 (`unix::tests::a_change_of_zone_is_seen_at_once`): a stale string makes the child run no test and the parent fail (or, for the Windows one, pass for the wrong reason). | C2, C5 | The strings are re-pointed in the step that moves the test, and the commit message lists them. `fault_child` in the two integration tests uses a bare name and is unaffected. |
| **Linux and Windows are not built here.** `linux/` and the Linux arms of `unix/` compile only on the Linux host; `windows/`, `os-install/windows/`, `web-opener/src/windows.rs`, the installer and the stub only in the virtual machine; the macOS arms only here. A split verified on one platform can break another silently until the full gate or the VM run. | C4–C9, O1, W1, I1 | Each such step is run by hand on its platform before its commit (`01-method-and-order.md` section 3); the Linux stage of `scripts/check.sh full` runs before the push. `cargo check --target x86_64-pc-windows-msvc` from macOS would catch Windows type errors early but needs that target's standard library installed, which the rules say not to do unasked. |
| **`missing_docs` and `unused_qualifications` are errors in the gate.** A moved item made `pub` needs a doc comment; an item moved next to its caller can leave a `crate::windows::…` path redundant. | every step | Items crossing a new boundary are `pub(super)` or `pub(crate)` (not subject to `missing_docs`); new `pub` items are only the re-exports named above, which keep their doc. Each new file carries a module doc comment. `cargo clippy -- -D warnings` in the gate catches the rest. |
| **`too_many_lines` at the edge.** `windows::start` 96 (allowed), `macos::profile` 96, `linux::seccomp` 90 against the threshold of 100. | C4, C6 | They move whole; nothing is added to them. |
| **The `tuf` workspace's separate gate.** `check.sh commit` runs `native/tuf`'s Clippy and tests only when a native path is staged (it is), and `native/tuf/fuzz`'s Clippy only in the full gate. | U1, T1, T2 | `cargo clippy` in `native/tuf/fuzz` is run by hand after U1 before the push. |
| **Lockfiles.** `native/fuzz` and `native/tuf/fuzz` keep their own lockfiles, checked `--locked` in the gate. | T2 | T2's `Cargo.toml` edit changes a bin's `path` only, which does not touch a lockfile. No step adds a dependency. |
| **`site` is a development tool with no `deny` list**, so moves there are gated by Clippy pedantic and its tests only. | S1–S4 | The tests move whole and `nextest` runs them; the terminal channel is also run by hand against the browser once after S3 (`cargo run -p neoteletext-site -- terminal`). |

---

## 6. Seen, not part of this plan

For the owner, and for `30-cross-cutting.md` section 5.

- `launcher/src/unix.rs` 84–88: a `#[cfg(not(unix))]` arm inside a module declared `#[cfg(unix)]` — dead code. Dropped in L2 as the function enters a Linux file.
- `site/src/serve.rs` 96–100 and `site/src/terminal.rs` 1153–1157: `respond()` byte-identical; the HTTP head-reading loops at `serve.rs` 127–143 and `terminal.rs` 1219–1232 differ only in whether the whole head is kept (the WebSocket accept needs it). One `http.rs` in `site` (with `media_type` and `MAX_HEAD`) would hold both; not a move, so not in this plan.
- `confine/src/broker.rs` 250–295, 457–465 and `update/src/wire.rs` 77–146: two bounded field readers, two `frame`s, two five-byte headers, in two crates that do not depend on each other (`confine` depends on no workspace crate). Joining them would add a dependency; a cross-cutting question.
- `launcher/src/lib.rs` 123–133 and `tuf/release/src/package.rs` 173–181: the same pinned-signer match, in two workspaces; and `launcher/src/windows.rs` 49, `installer/src/main.rs` 110 build the Windows signer from `release_identity::WINDOWS_SIGNER` directly rather than from `release_identity::keys()`.
- `confine/src/windows.rs` 372: `Role::Interface => CONTAINER_NETWORK` in `container()`, though `spawn` (642–647) never calls `container` for the interface; the arm is unreachable and names the fetcher's container.
- `confine/src/lib.rs` 87: `Role::Network` reports itself as `"fetcher"`, and the phone keyboard shares the role; the helpers' own `confine::apply` reports print that word for the keyboard too.
- `update/src/accept.rs` 186–207: `pub(crate) fn linux_version` and `key_pair` in its test module are used by nothing else in the crate (`launcher/tests/launcher.rs` builds its own fixture).
- `site/src/serve.rs` 108 and 179: the SSE push and the live-page rotation wait by `thread::sleep` in a loop (`DEVELOPMENT.md` section 6, "Waiting"); a development tool, but the only sleeps-and-looks in these crates besides `launcher/src/windows.rs` 119–125 (`STUB_TRIES`, which the file explains: the stub has no pipe to say it ended).
- Five spellings of "the home folder if absolute" (section 2.4, shape 4) and two of the XDG data folder (shape 5); `update::layout` is the place both repositories' installers would read them from.
- `update::layout::settings_folder` (the core's settings, requirement 19.1) lives in the installation-layout module; `confine::environment`'s `ENVIRONMENT_CORE` lists the variables it reads. Two crates each hold half of "where the core's settings are".
- `tuf/release/src/package.rs` `APPARMOR` (64–75) and `launcher/src/unix.rs` `APPARMOR_TARGET` (96): the profile's text and its install path are in two workspaces; a change to one must find the other.
- `os-install/src/windows.rs` 7–10 and `confine/src/windows.rs` 32–35 argue the safety of every Win32 call once at the module head rather than per block (`undocumented_unsafe_blocks` allowed module-wide), where `confine/src/unix.rs`, `confine/src/linux.rs`, `os-install/src/macos.rs` and `web-opener/src/windows.rs` write a SAFETY comment per block. The plan keeps each file's style; whether one style should hold is a question for `30-cross-cutting.md`.
- `dock-menu/src/mac.rs` uses `#![expect(unsafe_code)]`; the five other permitted files use `#![allow]`. Steps C5, C6, O1 and W1 bring them to `expect`, as convention 8 asks.
