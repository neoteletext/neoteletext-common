# 21. The interface core (`native/interface-core`)

| | |
|---|---|
| **Rests on** | A reading of every file of `native/interface-core` at browser commit `494aa91` (35 files, 13,614 lines), with item ranges measured by brace-matching; `docs/architecture.md` sections 11 and 14; `docs/native-interface-design.md` sections 4 and 12; `DEVELOPMENT.md` section 6; `00-conventions.md`. |
| **Phase** | B2 (`01-method-and-order.md` section 2): after `protocol`, independent of `confine` and `update`. |
| **Measured before** | 35 files; largest 2,724 lines, median 231; 9 files over 500; 9 functions over 80 lines; 7 `impl` blocks over 300; 2,712 test lines, all inline; 44 `cfg` sites in `browser.rs`, 5 in `popup_ui.rs`, 3 in `tips_ui.rs`. |

## 1. The crate as it is

### 1.1 Purpose and constraints

The interface core of the native interface design, section 4.1: the window's state, layout, animation, hit-testing and input handling, written once for every target. It draws only through the `Canvas` trait, reads no clock (the host passes `now` in milliseconds), and holds no state the trusted core owns: what it shows arrives through `set_*` methods, what the user does leaves as `Output`s.

| Fact | Where |
|---|---|
| `#![no_std]` with `extern crate alloc`; only `alloc` collections; floating point through `libm` | `lib.rs:11-13`; `Cargo.toml` |
| Dependencies: `libm` always, `neoteletext-input` under `interaction` | `Cargo.toml` |
| Lints: the workspace's (`unsafe_code = "forbid"`, `missing_docs`, `unused_qualifications`, Clippy `pedantic`, `allow_attributes_without_reason`, `dbg_macro`, `todo`, `unimplemented`), errors under the gate's `-D warnings`; `clippy.toml` allows unwrap, expect, panic and indexing in tests | `native/Cargo.toml:126-133`, `native/clippy.toml` |
| **No `#![deny(...)]` list; not in `scripts/check.sh` `NO_PANIC_ROOTS`** (lines 39-43). The crate reads nothing from outside its process; it indexes and does plain arithmetic throughout (`browser.rs:1516, 1756, 1782`; `tabs_ui.rs:135`) | `lib.rs`; `scripts/check.sh` |
| `too_many_lines` at Clippy's default of 100 lines of code; six site allows (section 2.3) | `clippy.toml` sets no threshold |
| `rustfmt`: 160 columns, `use_small_heuristics = "Max"` | `native/rustfmt.toml` |
| Toolchain Rust 1.99.0 | `rust-toolchain.toml` |

### 1.2 Features

| Feature | Default | What it gates |
|---|---|---|
| `links` | on | `pub mod links` (`lib.rs:26-27`); `mod link_ui` and `Browser::links` (`browser.rs:33-34, 616-618, 670-671`); `Output::{Point, Typed, Confirm, Cancel}` (`browser.rs:410-426`); sites in `frame_version`, `add_page`, `pointer_moved`, `cursor`, `pointer_pressed`, `key`, `type_digit`, `draw`, `draw_toolbar` (`browser.rs:683, 749, 950-953, 978, 1034, 1286, 1319, 1576, 1690, 1734-1737`) |
| `interaction` | on | `dep:neoteletext-input`; `pub mod input` (`lib.rs:23-24`); `mod terminal_ui` and `pub use terminal_ui::{CursorView, TypingView}` (`browser.rs:41-46`); `Browser::terminal` (`619-621, 672-673`); `Output::Terminal` (`427-437`); `strip_has_keys` (`895-904`); sites in `frame_interval` (`816-819`, with a `#[cfg(not(...))]` twin), `settle` (`829-832`), `pointer_moved` (`947-948`), `pointer_released` (`1002-1003`), `pointer_pressed` (`1138-1141`), `draw` (`1578-1579`), `draw_toolbar` (`1729-1730`) |
| `phone-keyboard` | on; implies `interaction` | `mod phone_ui` and `pub use phone_ui::{PhoneStatus, PhoneUiView}` (`browser.rs:47-50`); `Browser::phone` (`622-624, 674-675`); `Output::{PhonePanel, PhoneFinish}` (`438-443`); the menu item (`popup_ui.rs:38-39, 57-58, 79-80, 142-143`); `tips_ui.rs:211-212`; `pointer_pressed` (`1029-1032`); `draw` (`1606-1607`); `draw_toolbar` (`1727-1728`) |

`scripts/check.sh:78-85` runs Clippy with every feature, with none, and with each optional area alone; `core`, `protocol` and `decoder` forward the three features to this crate (`core/Cargo.toml:13-18`, `protocol/Cargo.toml:14-20`, `decoder/Cargo.toml:21-24`), and `fetcher` takes the crate only under `links`.

### 1.3 The `Canvas` trait and its back ends

`canvas.rs:87-122`: eleven required methods (`fill`, `dim`, `polygon`, `push_clip`, `pop_clip`, `gradient`, `page`, `screen`, `text`, `text_width`, `line_height`) and `device_scale` with a default of 1.0. Beside it: `PageKey`, `Style`, the raster constants (`COLUMNS`, `ROWS`, `CELL_WIDTH`, `CELL_HEIGHT`, `PAGE_WIDTH`, `PAGE_HEIGHT`, `SCREEN_BORDER`, `SCREEN_SCALE`), `image_within` and `draw_page_on_screen`. Every drawing function in the crate is generic over `C: Canvas + ?Sized`.

| Back end | Crate | Target |
|---|---|---|
| `vello_cpu` + Parley | `draw-vello` | desktops and phones |
| `embedded-graphics` + bitmap fonts | `draw-embedded` | microcontrollers (drawn into a memory display by a test) |
| `Recorder` | this crate, `test_canvas.rs`, `#[cfg(test)]` | the crate's tests |

### 1.4 Module tree with line counts

```
src/
  lib.rs                      35   crate doc, no_std, mod tree (input and links gated, test_canvas cfg(test)); no deny list
  browser.rs                2724   Browser struct, host-facing types, the core impl, strip/toolbar/banks/list/overview drawing, glyphs, 23 tests
  browser/
    bookmarks_ui.rs          867   bookmarks manager (state + input + draw + tests)
    history_ui.rs            688   history panel
    settings_ui.rs           681   settings panel
    terminal_ui.rs           635   typing into a page (interaction)
    console_ui.rs            586   developer console
    link_ui.rs               544   hyperlinks in the window (links)
    popup_ui.rs              527   the menu, Back and Forward lists, address suggestions
    remote_ui.rs             500   remote control
    star_ui.rs               497   the star's popover and the bookmarks bar
    tabs_ui.rs               411   tab overflow and dragging
    cookies_ui.rs            404   the console's Cookies tab
    tips_ui.rs               267   tips
    phone_ui.rs              263   phone keyboard panel and badge (phone-keyboard)
    controls_ui.rs           231   sub-page control and the viewer's keys
    refused_ui.rs            191   certificate-error screen
    widgets.rs                87   button, field, panel, triangle shared by the panels
  wall.rs                   1168   the page area: size control, grid, list, zoom, slide, hover; 14 tests
  library.rs                 407   history and bookmarks views and requests, limits, WindowGeometry
  links.rs                   317   link types and the underline
  editor.rs                  223   single-line text editor
  theme.rs                   159   colours and text styles
  size.rs                    136   page size rules
  settings.rs                132   settings views and changes
  channel.rs                 130   banks and pages, page_number, page_index
  canvas.rs                  122   Canvas, PageKey, Style, raster constants
  tween.rs                   112   timing curves and Tween
  controls.rs                106   page-control types
  console.rs                 105   console entry types
  geometry.rs                 89   Point, Rect
  cookies.rs                  79   cookies view and requests
  input.rs                    74   Intent (interaction)
  test_canvas.rs              60   Recorder (cfg(test))
  ui.rs                       57   label, centred, left_centred, right_centred, outline, border
```

### 1.5 How `Browser` is spread over `browser.rs` and the `*_ui.rs` files

| Where | What |
|---|---|
| `browser.rs:555-625` | `pub struct Browser`, 38 fields (section 2.2) |
| `browser.rs:627-2032` | one `impl Browser` of 1,406 lines: constructor, setters, frame timing, page selection, address editing, focus arbitration, all pointer and key dispatch, and the drawing of the window, strip, toolbar, banks, list and overview |
| `browser.rs:2034-2066` | a second `impl Browser` holding `draw_preview` alone |
| each `browser/*_ui.rs` | a private state struct (`BookmarksUi`, `HistoryUi`, `SettingsUi`, `ConsoleUi`, `CookiesUi`, `TipsUi`, `ControlsUi`, `RemoteUi`, `RefusedUi`, `TabsUi`, `StarUi` and `BarUi`, `PopupUi`, `LinkUi`, `TerminalUi`, `PhoneUi`) stored as a field of `Browser`, and an `impl Browser` of `pub(super)` methods (`xxx_press`, `xxx_key`, `xxx_scroll`, `xxx_tips`, `draw_xxx`, `toggle_xxx`, `set_xxx`) that `browser.rs` calls in a fixed order from `pointer_pressed`, `key`, `scroll_by`, `settle`, `frame_interval`, `draw` and `focused_field` |

What the children reach in the parent (all legal: a child sees its parent's private items):

| Reached | From |
|---|---|
| fields `outputs` (every file), `pointer` (12 files), `regions` (link, popup, star, tabs, tips), `body` (bookmarks, history, settings, star), `wall` (controls, link, phone, remote, terminal, tips), `strip`, `tabs`, `active`, `channel`, `versions`, `editing`, `editor`, `frame`, `digits`, `sounding`, `overview_folded` | the `*_ui.rs` files |
| private methods `stop_editing` (popup, remote, settings), `close_panels` (console, history, bookmarks), `select_page` (terminal, link), `type_digit`, `step_page` (remote), `opened`, `strip_has_keys` (terminal), `all_muted` (tips) | the `*_ui.rs` files |
| `super::MAX_ADDRESS` (`settings_ui.rs:46`), `super::MARGIN` (`remote_ui.rs:134, 205, 212, 450`), `super::star`, `super::STAR_RADIUS` (`popup_ui.rs:380`), `super::{PAGES_PER_BANK, page_number}` re-imported through the parent (`tips_ui.rs:13`), the tab-strip constants, `TabRegion` and `speaker_glyph` (`tabs_ui.rs:11-14`) | by path |
| `console_ui::CONSOLE_HEIGHT` (1549), `star_ui::BAR_HEIGHT` (1543), `self.console.open()` (800, 1548, 1596), `self.console.area` in a test (2722) | `browser.rs` reaching children |

### 1.6 Public paths and who imports them

| Path | Importers |
|---|---|
| `browser::{Browser, Cursor, Frame, Key, Modifiers, Output, StripState, TabInfo, WindowAction}` | `interface/src/main.rs:35`; `draw-vello/src/lib.rs:722`, `examples/write_window.rs:11`; `draw-embedded/examples/write_screen.rs:12`, `tests/memory_display.rs:11` |
| `browser::{CertificateProblem, StripState, TabInfo}` | `core/src/session.rs:10`, `core/src/library.rs:950`, `core/src/main.rs:774, 1297`; `protocol/src/lib.rs:41`, `protocol/src/fetcher.rs:10` (re-exported) |
| `browser::MAX_ADDRESS` | `protocol/src/lib.rs:67` |
| `browser::LINE_HEIGHT`, `browser::{PhoneStatus, PhoneUiView}`, `browser::{CursorView, TypingView}` | `interface/src/main.rs:712, 873, 890, 896` |
| `canvas::{PageKey, CELL_WIDTH, CELL_HEIGHT, PAGE_WIDTH, PAGE_HEIGHT}` | `interface`, `core`, `protocol`, `decoder/src/lib.rs:68, 1338-1339`, `draw-*`, `fuzz/fuzz_targets/input_records.rs:18` |
| `channel::{Channel, page_index, page_number, PAGES}` | `interface`, `core`, `protocol`, `decoder/src/lib.rs:69`, `fetcher/src/main.rs:232` |
| `controls::{ANY_SUBCODE, MAX_SUBPAGES, PageControls, PageControl, FastextKey}` | `core`, `protocol`, `decoder/src/lib.rs:66, 341`, `interface` |
| `console::{Level, ConsoleUpdate}` | `decoder/src/lib.rs:42-58, 1044-1045`, `core`, `protocol`, `interface` |
| `library::{WindowGeometry, MAX_WINDOWS, MAX_FOLDER_DEPTH, MAX_NAME, TabList, Suggestions, StarView, HistoryView, BookmarksView, BarView}` | `core`, `protocol`, `interface`, `decoder/src/netscape.rs:12`, `fuzz/fuzz_targets/netscape_file.rs:7` |
| `settings::{UpdateView, SettingsView, RemotePlace}`, `cookies::CookiesView`, `editor::hidden`, `input::Intent`, `links::*`, `theme::{Colour, TAB_COLOURS}`, `geometry::{Point, Rect}` | `core`, `protocol`, `interface`, `draw-*` |

`Browser` methods called from outside the crate (all `pub fn`; an inherent method may live in any module of the crate, so moving one between files changes nothing for a caller): `draw, key, pointer_moved, pointer_pressed, pointer_released, middle_pressed, new_tab_pressed, secondary_pressed, wheel_lines, scroll_by, settle, frame_interval, cursor, opened, take_outputs, set_tabs, set_channel, set_strip, set_sounding, set_bookmarks, set_bar, set_star, set_history, set_cookies, set_settings, set_update, set_remote, set_page_controls, set_links, set_pointing, set_prompt, set_aliases, set_suggestions, set_tab_list, set_typing, set_phone, set_browser_modifier, show, add_page, page_updated, frame_version, console_update, wall, wall_mut, tab_sounding, tab_place_at, typing_target, terminal_key, terminal_text, terminal_paste, terminal_compose, terminal_wheel, composes_for_channel, fastext_key, selected_text, cut, paste_text`.

## 2. Findings

### 2.1 File by file

Ranges are inclusive; "mixes" names the distinct concerns in one file.

**`browser.rs` (2724).**

| Lines | Size | Holds |
|---|---|---|
| 11-50 | 40 | imports (theme: 31 names), 16 `mod` lines (3 gated), 2 gated `pub use` |
| 52-187 | 136 | `pub const MAX_ADDRESS`; constant groups "Tab strip" (56-78, 18), "Toolbar" (80-124, 36), "Panels" (126-145, 17), "Overview" (147-183, 22); `pub const LINE_HEIGHT`, `DECIMAL_DIGITS` |
| 194-295 | 102 | `Frame`, `TabInfo`, `StripState`, `CertificateProblem` + impl |
| 299-498 | 200 | `WindowAction`, `Output` (312-444, 42 variants, 7 gated), `Key`, `Cursor`, `Modifiers` |
| 502-550 | 49 | `TabRegion`, `Regions` (23 rects), `Regions::clear` |
| 555-625 | 71 | `pub struct Browser` |
| 627-677 | 51 | `new` |
| 680-836 | 157 | setters and timing: `frame_version`, `set_tabs`, `set_sounding`, `tab_sounding`, `all_muted`, `set_strip`, `set_channel`, `add_page`, `page_updated`, `updated_at`, `wall`, `wall_mut`, `take_outputs`, `animating`, `frame_interval`, `settle` |
| 838-932 | 95 | `page_key`, `select_page`, `choose_bank`, `reveal_row`, `bank_pages`, `stop_editing`, `strip_has_keys` (gated), `close_panels`, `start_editing` |
| 934-1250 | 317 | `pointer_moved`, `overview_page`, `opened`, `cursor`, `toggle_overview`, `pointer_released`, `pointer_pressed` (144), `wheel_lines`, `middle_pressed`, `new_tab_pressed`, `open_in_new_tab`, `secondary_pressed`, `scroll_by` |
| 1253-1534 | 282 | `key` (54), `type_digit`, `shortcut` (67), `focused_field`, `selected_text`, `cut`, `paste_text`, `edit` (32), `follow_zoom`, `step_page`, `offset_at`, `cell_index` |
| 1536-2066 | 531 | `draw` (81), `draw_tab_strip`, `draw_toolbar` (108), `draw_address` (43), `draw_banks` (41), `draw_list` (71), `draw_legend`, `draw_overview` (91); second impl: `draw_preview` |
| 2068-2258 | 191 | free glyph functions `chevron`, `draw_window_buttons`, `arrow`, `speaker_glyph`, `padlock`, `house`, `reload_glyph`, `gear`, `star` (a stray doc line at 2189 sits above `house`) |
| 2260-2724 | 464 | `mod tests`: helpers `channel`, `browser`, `press_at`, `cell_centre`; 23 tests |

Mixes twelve concerns: host-facing message types; the aggregate state struct; frame timing; page and bank selection; address-field editing; focus arbitration between seven panels; pointer dispatch in drawing order; key dispatch and the shortcut table; frame layout; the drawing of five parts of the window; vector glyphs; tests of all of them.

**`browser/bookmarks_ui.rs` (867).** Consts 20-40 (16); `Field` 44-48; `Form` 52-61; `Controls` 65-88; `ItemControls` 92-100; `BookmarksUi` 103-118, `Default` 120-136, `editor` 138-146; `impl Browser` 148-685: `bookmarks_tips`, `set_bookmarks`, `bookmarks_open`, `toggle_bookmarks`, `focus_bookmarks`, `unfocus_bookmarks`, `bookmarks_editing`, `start_form`, `submit_form`, `bookmarks_key` (233-287), `bookmarks_field`, `bookmarks_scroll` (296-314), `bookmarks_press` (319-396), `bookmark_at`, `draw_chooser` (412-447), `bookmarks_released` (451-482), `bookmarks_undo_shown`, `bookmarks_deadline`, `draw_bookmarks_panel` (497-684); tests 687-867 (4). Mixes: state and three editors; focus; a form state machine; keys; wheel paging; press hit-testing; drag with a threshold; the chooser popup; the Undo timer; a 188-line draw.

**`browser/history_ui.rs` (688).** Consts and `RANGES` 21-49; `Controls` 53-71; `RowAction` 77-96; `HistoryUi`, `Clears` 99-118; `Default` 120-134; `impl Browser` 136-521: `history_tips`, `set_history` (147-164, remaps the selection by address), `history_open`, `toggle_history`, `set_history_open`, `clear_history_choices`, `unfocus_history`, `history_query`, `history_editing`, `history_key` (218-250), `history_field`, `history_scroll` (258-271), `history_row_at`, `history_press` (284-353), `draw_history_panel` (357-520); tests 523-688 (4). Mixes as bookmarks, plus a row menu and the clearing sub-state.

**`browser/settings_ui.rs` (681).** Consts 21-49 (`HOME_LIMIT = super::MAX_ADDRESS`); `Field` 53-62; `Kind` 66-71; `Controls` 75-94; `SettingsUi` 97-110; `Default` 112-127; `impl SettingsUi { editor, refresh, proxy }` 129-169; `impl Browser` 171-525: `settings_tips`, `set_settings`, `set_update`, `settings_open`, `settings_editing`, `toggle_settings`, `focus_settings`, `unfocus_settings`, `change`, `submit`, `settings_key` (254-284), `settings_field`, `settings_press` (293-356), `settings_area`, `draw_settings_panel` (365-519), `draw_settings_field`; tests 527-681 (4). Mixes as above, plus proxy composition and volume arithmetic.

**`browser/terminal_ui.rs` (635).** Consts 28-53; `pub struct CursorView` 57-66 and `pub struct TypingView` 70-93 (re-exported data in a UI file); `Echo` 97-101; `TerminalUi` 105-117; `cut` 120-126; `impl Browser` 128-416: `set_typing`, `typing_target`, `typing_modes`, `composes_for_channel`, `set_browser_modifier`, `pointer_on_page`, `mouse_is_hosts`, `click_is_hosts`, `send`, `terminal_key`, `terminal_text`, `terminal_paste`, `terminal_compose`, `terminal_button`, `terminal_moved`, `terminal_wheel`, `echo`, `settle_echoes`, `terminal_frame_interval`, `draw_terminal` (351-384), `draw_typing_badge` (390-415); tests 418-635 (9). Mixes: view types; intent numbering and sending; mouse-mode arbitration; the echo buffer; blink timing; the cursor and badge drawing.

**`browser/console_ui.rs` (586).** Consts 23-43 (`pub(super) CONSOLE_HEIGHT`); `ConsoleUi` 46-69, `Default` 71-93; `level_index`, `level_colour` 96-107; `Tab`, `TABS` 111-124; `impl ConsoleUi { open, keep, shown }` 126-156; `impl Browser` 158-433: `console_update`, `console_open`, `toggle_console`, `manage_cookies`, `choose_console_tab`, `set_paused`, `console_press` (222-256), `stop_console_search`, `console_searching`, `console_field`, `console_key`, `console_scroll`, `console_tips`, `draw_console` (337-432); tests 435-586 (5). Mixes: a bounded entry store with a pause queue; the Log filter; cookies-tab delegation; search focus; drawing. `area` is a `pub(super)` field read by a `browser.rs` test.

**`browser/link_ui.rs` (544).** Consts 21-30 (`FIELD_PADDING 12` duplicates `browser.rs:85`); `LinkUi` 34-56; `impl Browser` 58-329: `set_links`, `set_pointing`, `set_prompt`, `set_aliases`, `show`, `show_pending`, `open_links`, `link_under_pointer`, `focused_cell`, `repoint`, `same_run`, `link_cursor`, `link_press`, `link_key` (195-254), `link_typed`, `draw_links`, `draw_prompt` (281-313), `draw_pointing`; tests 331-544 (9). Cohesive; the strip's prompt (its own timer rule) could stand alone.

**`browser/popup_ui.rs` (527).** Consts 17-23; `Item` + impl 27-86 (one gated variant); `PopupUi` 90-107; `impl Browser` 109-422 sectioned by comments: the menu 110-182 (`toggle_menu`, `menu_press`, `draw_menu`), the lists 184-287 (`hold_back_or_forward`, `release_back_or_forward`, `ask_tab_list`, `settle_hold`, `hold_deadline`, `set_tab_list`, `tab_list_press`, `draw_tab_list`), the suggestions 289-395 (`edited`, `set_suggestions`, `choose_suggestion`, `take_chosen_suggestion`, `close_suggestions`, `suggestion_at`, `suggestion_press`, `draw_suggestions`), the three together 397-421 (`draw_popups`, `popups_press`, `popup_open`, `close_popup`); tests 424-527 (3). Mixes three unrelated drop-downs in one state struct. `draw_suggestions` reaches `super::star` and `super::STAR_RADIUS` (380).

**`browser/remote_ui.rs` (500).** Consts 20-39 (`pub(super) REMOTE_WIDTH`); `Button` 43-52; `RemoteUi` 56-74, `out` 76-85 (eases with `STANDARD` by hand rather than a `Tween`); `impl Browser` 87-385: `set_remote`, `move_remote`, `put_remote`, `toggle_remote`, `remote_time`, `remote_shown`, `remote_animating`, `remote_docked_width`, `remote_press` (138-174), `remote_moved`, `remote_released`, `draw_remote` (196-240), `draw_remote_keys` (243-347), `remote_tips` (350-384); free `panel_height`, `corner`, `subpage_words` (400-408 duplicates `controls_ui.rs:128-131`), `key` 387-415; tests 417-500 (3, with a module-level `unwrap_used` allow that `clippy.toml` already grants). Mixes: placement and slide; dragging; press dispatch into digits and controls; drawing every key row; tips.

**`browser/star_ui.rs` (497).** Consts 20-36 (`pub(super) BAR_HEIGHT`); `PopoverControls` 40-48; `StarUi` + `Default` 51-65; `BarUi` 69-76; `impl Browser` 78-403: popover 80-264 (`bar_tips` placed first, `set_star`, `star_open`, `unfocus_star`, `star_done`, `star_editing`, `star_key`, `star_field`, `star_press`, `draw_star_popover` 202-264) and bar 266-402 (`set_bar`, `bar_shown`, `toggle_bar`, `bar_bookmark_at`, `bar_press`, `draw_bar` 324-376, `draw_bar_list`); tests 405-497 (3). Two UIs in one file.

**`browser/tabs_ui.rs` (411).** Imports eighteen names from `super` (11-14); consts 20-32; `Drag` 36-45; `TabsUi` 49-63; `whole`, `arrangement` 66-87; `impl Browser` 89-289: `draw_tabs` (92-127), `draw_tab` (131-159), `draw_tab_overflow` (164-199), `tabs_press`, `tabs_moved`, `tabs_released`, `tab_place_at`, `tabs_cancel`, `tabs_tips`; tests 291-411 (5; one exercises `shortcut` in `browser.rs`). The tabs' constants, `TabRegion`, `speaker_glyph`, `draw_tab_strip`, `draw_window_buttons`, `set_tabs`, `set_sounding`, `tab_sounding` and `all_muted` are the same concept but sit in `browser.rs`.

**`browser/cookies_ui.rs` (404).** Consts 20-34; `Drawn`, `Controls` 39-56; `CookiesUi` + `Default` 59-73; `size` 76-78; `impl Browser` 80-302: `set_cookies`, `cookies_open`, `set_cookies_open`, `unfocus_cookies`, `cookies_query`, `cookies_editing`, `cookies_key` (125-152), `cookies_field`, `cookies_scroll` (160-173, the same 14 lines as `history_scroll`), `cookies_press` (176-205), `cookies_tips`, `draw_cookies` (223-301); tests 304-404 (2). The standard panel shape with a confirm sub-state.

**`browser/tips_ui.rs` (267).** Consts 19-28; `Tip`, `TipsUi` 32-47; `impl TipsUi { at, moved }` 49-67; `impl Browser` 69-214: `keys_named` (used by every panel's tips), `tips_moved`, `tips_pressed`, `tips_deadline`, `tips_settle`, `tip_shown` (cfg(test)), `draw_tips` (111-151, gathers tips from eight modules in a fixed precedence), `strip_tips` (154-189), `body_tips` (192-213); tests 216-267 (2). Cohesive; the strip and body tip texts describe parts drawn elsewhere.

**`browser/phone_ui.rs` (263).** `PhoneStatus`, `PhoneUiView` 18-44 (re-exported data); `pub const WARNING` and consts 46-60; `PhoneUi` 64-70; `impl Browser` 72-204: `phone_tips`, `set_phone`, `phone_connected`, `toggle_phone_panel`, `phone_press`, `draw_phone_badge`, `draw_phone_panel` (134-203); its own `panel_rect(area)` and `draw_qr` 206-227; tests 229-263 (2). Cohesive.

**`browser/controls_ui.rs` (231).** Consts 17-23; `ControlsUi` 27-33; `impl Browser` 35-149: `set_page_controls`, `page_controls`, `ask_control`, `controls_open`, `control_key`, `fastext_key`, `controls_press`, `draw_page_controls`, `controls_tips`; tests 151-231 (2, redundant `unwrap_used` allow). Cohesive.

**`browser/refused_ui.rs` (191).** Consts and texts 16-25; `RefusedUi` 28-33; `wrapped` 36-52 (the crate's only word wrap); `impl Browser` 54-129: `certificate_refused`, `draw_refusal`, `refused_press`; tests 131-191 (2). Cohesive.

**`browser/widgets.rs` (87).** `RADIUS`, `OUTLINE`, `PANEL_RADIUS`, `FIELD_PADDING`, `CARET_WIDTH`, `FIELD_TEXT`; `button`, `field` (31-58, draws an `Editor` with caret and selection, as `Browser::draw_address` does by another method at `browser.rs:1750-1792`), `panel_rect`, `panel`, `TRIANGLE`, `triangle`. No tests. Cohesive.

**`wall.rs` (1168).** Consts 23-87 (control row 13; wall 26 with zoom, hover, wheel, slide and close timings); `WallPage` 91-98; `glow`, `since`, `UPDATE_GLOW_MILLISECONDS`, `UPDATE_MARK_MILLISECONDS`, `MILLISECONDS_PER_SECOND`, `GLOW_WIDTH` 100-125 (update-mark rules used by `browser.rs` too); `CellClick`, `cell_in` 127-152 (used by three other modules); `Drawn` 157-161; `Wall` 165-211 (29 fields); `Default` 213-217; `impl Wall` 219-923: construction 222-261; zoom and slide 266-371; size control 376-403; pointer 406-449; `*_for_tests` 452-464; queries 469-541; hover 545-571; drawing 576-922 (`draw_popped`, `layout`, `animating`, `draw` 610-671, `draw_page`, `zoomed_rect`, `draw_zooming`, `draw_zoomed`, `draw_close`, `bring_into_view`, `draw_grid` 774-839, `draw_list` 842-882, `draw_controls` 884-922); tests 925-1168 (14). Mixes seven concerns in one 705-line impl.

**Root modules.** `library.rs` (407) mixes history, bookmarks, suggestions, tab lists and the session's `WindowGeometry` (376-407); `MAX_PATH = crate::browser::MAX_ADDRESS` (49) and `cookies.rs:13` depend upwards on `browser`. `links.rs` (317) holds the link types (45-191) and the underline drawing (195-247) with 4 tests; cohesive. `editor.rs` (223), `theme.rs` (159), `size.rs` (136), `settings.rs` (132), `channel.rs` (130), `canvas.rs` (122), `tween.rs` (112), `controls.rs` (106), `console.rs` (105), `geometry.rs` (89), `cookies.rs` (79), `input.rs` (74), `test_canvas.rs` (60), `ui.rs` (57): each one concept. `ui.rs` is misnamed: it places text and draws rules, and "ui" is what the `browser/*_ui.rs` suffix means.

### 2.2 The `Browser` fields, by concern

| Concern | Fields (`browser.rs:555-625`) | Handled by |
|---|---|---|
| Window frame | `frame` | `browser.rs` (strip), `popup_ui`, `tips_ui` |
| Tabs | `tabs`, `active`, `sounding`, `tab_strip` | `browser.rs` setters; `tabs_ui.rs` |
| Trusted strip and address field | `strip`, `editor`, `editing`, `field_scroll`, `press_new_tab` | `browser.rs` (`draw_toolbar`, `draw_address`, `edit`, `start_editing`, `stop_editing`, `offset_at`); `popup_ui` reads `editor` |
| Channel, banks, list | `channel`, `bank`, `selected`, `list_scroll`, `digits`, `versions` | `browser.rs` (`set_channel`, `select_page`, `choose_bank`, `reveal_row`, `draw_banks`, `draw_list`, `type_digit`); `remote_ui` reads `digits`, `link_ui` reads `versions` |
| Page area | `wall` | `wall.rs` through its accessors; read directly by six panels |
| Overview | `pulses`, `updates`, `overview_folded`, `previewed`, `visible` | `browser.rs` (`add_page`, `page_updated`, `draw_overview`, `draw_preview`, `toggle_overview`) |
| Layout bookkeeping | `pointer`, `regions`, `body`, `outputs` | every module |
| Panels, one field each | `settings`, `console`, `history`, `cookies`, `tips`, `page_controls`, `remote`, `refused`, `bookmarks`, `star`, `bar`, `popups`, `links` (gated), `terminal` (gated), `phone` (gated) | their `*_ui.rs` |

`Browser` is the aggregate root the design asks for (one core, one `draw`, one output queue); it is a god object only in that 23 fields of six concerns are handled by one 1,406-line impl. The panel fields are already encapsulated. The impl can be split by concern without touching the field list.

### 2.3 Functions over 80 lines and `impl` blocks over 300

| Function | Lines | Interleaves |
|---|---|---|
| `draw_bookmarks_panel` `bookmarks_ui.rs:497-684` | 188 | frame; toolbar; search; tree; path; form; contents rows with three buttons; chooser; footer |
| `draw_history_panel` `history_ui.rs:357-520` | 164 | frame; search and Clear; clearing choices or Remove-selected; closed tabs; day headings and rows; row menu; footer |
| `draw_settings_panel` `settings_ui.rs:365-519` | 155 | frame; eight rows of controls; refusal line |
| `pointer_pressed` `browser.rs:1008-1151` | 144 | tips; drag cancel; eleven z-ordered delegations; address field; Back/Forward hold; gear and menu; eight fixed buttons; bar; strip drag; banks; list; overview; page controls; wall controls; wall cell with terminal arbitration and zoom |
| `draw_toolbar` `browser.rs:1641-1748` | 108 (under 100 of code) | toolbar buttons and glyphs; address field; prompt override; five security prefixes; star; two badges; pointing; notice; address |
| `draw_remote_keys` `remote_ui.rs:243-347` | 105 | title row; readout; pad; page keys; Fastext; Index; sub-pages; toggles |
| `draw_console` `console_ui.rs:337-432` | 96 | tab bar; buttons; Log levels and search; cookies delegation; entry rows |
| `draw_overview` `browser.rs:1941-2031` | 91 | panel, toggle, legend; 800 cells; rings; pulses |
| `draw` `browser.rs:1539-1619` | 81 | geometry; `WallPage`s; wall; three overlays; visible-set diff; fifteen ordered draws; post-draw hover |

Allows at `browser.rs:1007`, `bookmarks_ui.rs:318` and `496`, `history_ui.rs:356`, `remote_ui.rs:242`, `settings_ui.rs:364`.

| `impl` block | Lines |
|---|---|
| `impl Browser` `browser.rs:627-2032` | 1406 |
| `impl Wall` `wall.rs:219-923` | 705 |
| `impl Browser` `bookmarks_ui.rs:148-685` | 538 |
| `impl Browser` `history_ui.rs:136-521` | 386 |
| `impl Browser` `settings_ui.rs:171-525` | 355 |
| `impl Browser` `star_ui.rs:78-403` | 326 |
| `impl Browser` `popup_ui.rs:109-422` | 314 |

### 2.4 Duplicated shapes across the panels

| Shape | Copies (file:lines) | The shared form it would take, behaviour unchanged |
|---|---|---|
| `open` flag, `xxx_open()` getter, `toggle_xxx` or `set_xxx_open` | bookmarks 104, 169-171, 174-187; history 101, 168-170, 173-192; settings 101, 197-199, 207-215; cookies 60, 88-90, 94-105; console 47, 182-184, 188-194; star 104-106; phone 66, 95-98; popup (`menu_open`) 91, 113-115 | Left as it is: each toggle also sends its own `Output` and closes other panels in its own order |
| Focus with `TextInput` outputs: "if not focused { focused = true; push TextInput(true) }" and the inverse | bookmarks 189-203; history 200-205 and 306-312; settings 217-232; cookies 107-112 and 181-187; console 234-240, 258-263; star 108-113, 174-180; `browser.rs` 885-932 | `take_focus(focused: &mut bool, outputs: &mut Vec<Output>)` and `drop_focus(..) -> bool` in `widgets.rs`, each pushing `TextInput` exactly when the flag flips; panels with `Option<Field>` wrap them |
| `xxx_editing()` and `xxx_field()`, chained in `focused_field` (`browser.rs:1400-1420`) and `strip_has_keys` (896-904) | bookmarks 206-208, 290-293; history 213-215, 253-255; settings 202-204, 287-290; cookies 120-122, 155-157; console 266-268, 271-273; star 126-128, 158-160 | A `StripPanel` trait with `open`, `editing`, `field` on each state struct would let the two chains iterate an array in today's order; deferred, since the `press` and `key` methods need `&mut Browser` and stay as they are |
| The editor key block: `Text → insert, Backspace, Delete, Left(shift), Right(shift), Home \| Up → home, End \| Down → end` | bookmarks 251-258; history 235-242; settings 266-273; star 143-150; console 281-288; cookies 138-145; `browser.rs` `edit` 1452-1473 | `edit_key(editor: &mut Editor, key: Key<'_>, shift: bool) -> EditKey { Edited, Moved, Other }` in `widgets.rs`; each `xxx_key` keeps its own `Enter`, `Escape`, `Tab` arms under `Other`; `browser.rs::edit` checks `choose_suggestion` first, as now |
| "The search follows typing": `before = text; …; if text != before { query }` | bookmarks 250, 282-285; history 234, 246-248; cookies 137, 148-150; `browser.rs` 1451, 1476-1479 | Returned by `edit_key` as `Edited` |
| Wheel paging by `WHEEL_ROWS` | history 258-271 and cookies 160-173 (identical but for names); bookmarks 296-314 (two lists); console 297-306 (lines) | `page_by_wheel(first: u32, total: u32, shown: usize, distance: f64) -> Option<u32>` with `WHEEL_ROWS` defined once |
| A `Controls` rect record rebuilt each draw, opened with "`let mut controls = Controls::default(); if !open { self.x.controls = controls; return; }`" | bookmarks 65-88, 498-502, 683; history 53-71, 358-362, 519; settings 75-94, 366-370, 518; cookies 48-56, 224, 300; star (`PopoverControls`) 40-48, 203-207, 263 | Left as it is: the record is each panel's own |
| The panel frame: `panel_rect(self.body, W, H)`, `panel`, insets, heading in `HEADING`/`WHITE`, close button at `right - SMALL_BUTTON` drawn `"\u{00D7}"`; with `PADDING 20`, `HEADING_HEIGHT 34`, `SMALL_BUTTON 32`, `GAP 8`, `CONTROL_HEIGHT`/`ROW 32` declared in each file | bookmarks 503-510 (consts 22-26); history 363-370 (23-27); settings 371-379 (25-33); cookies consts 20-22 | `widgets::panel_frame(canvas, body, width, height, title) -> PanelFrame { area, left, right, heading, close }`, owning the five constants once |
| `xxx_press`: open and area checks, sub-popup first, close, fields to focus, `unfocus`, then an `if`/`else if` ladder over the rects | bookmarks 319-396; history 284-353; settings 293-356; cookies 176-205; console 222-256; star 164-199; remote 138-174; phone 102-114; refused 113-128 | Left as it is |
| `xxx_tips` with the close button's `keys_named(...)` | bookmarks 150-156; history 138-144; settings 173-181; console 309-334 | Part of `panel_frame` (it knows the close rect) |
| Empty-list caption centred over two rows | bookmarks 619-622; history 431-434; cookies 264-267 | Left as it is |
| Hover-highlight row (`if rect.contains(self.pointer) { fill(rect, RULE_SOFT) }`) | bookmarks 549-551, 633-635; history 447-450; cookies 273-276; star 255-257, 392-394; popup 170-172, 266-268, 376-378; bar 354-358 | Left as it is |
| Test helpers: `middle(rect) -> Point` | bookmarks 726; history 565; cookies 338; popup 431; remote 427; star 412; tabs 317; refused 151; controls 220 | One `#[cfg(test)]` fixture module (`browser/fixture.rs`): `middle`, `press_at`, `blank_browser`, `WIDTH`, `HEIGHT` |
| Test helpers: `open()` / `browser()` building `Browser::new(Frame { left_inset: 0.0, window_buttons: false })` and drawing once at 1440 × 900 | bookmarks 716; history 555; settings 546; cookies 327; console 496; browser.rs 2278; popup 435; star 416; terminal 428; thirteen inline copies | The same fixture module |

The shared forms are code changes, not moves; they are recorded here as the shape the duplicates share, and are not steps of section 4 (see section 6).

### 2.5 Naming

| Today | Problem |
|---|---|
| `browser/*_ui.rs` on fifteen files; `browser/widgets.rs`; root `ui.rs` | Siblings disagree; `ui.rs` holds text placement, not a UI |
| `console.rs`/`console_ui.rs`, `cookies.rs`/`cookies_ui.rs`, `settings.rs`/`settings_ui.rs`, `controls.rs`/`controls_ui.rs`, `links.rs`/`link_ui.rs`, `library.rs` serving four panels | A root data module and its panel differ only by suffix; one pair differs singular/plural |
| `star_ui.rs` holds `StarUi` and `BarUi`; `popup_ui.rs` holds three drop-downs; `tabs_ui.rs` holds the overflow but not the tabs | A file name promises less than the file holds, or more |
| View types in root modules for every feature except typing (`terminal_ui::{CursorView, TypingView}`) and the phone (`phone_ui::{PhoneStatus, PhoneUiView}`) | Data in UI files, re-exported through `browser` |
| Field and module differ: `page_controls: controls_ui::ControlsUi`, `tab_strip: tabs_ui::TabsUi`, `popups: popup_ui::PopupUi`, `links: link_ui::LinkUi`, `terminal: terminal_ui::TerminalUi` | Two names for one thing |
| `toggle_*` (nine) against `set_history_open`, `set_cookies_open`, `star_done`; key handlers `xxx_key` against `control_key` and `edit`; frame hooks `*_deadline` against `terminal_frame_interval`, `remote_animating`; settle hooks `settle_echoes`, `settle_hold`, `tips_settle` | Verb order and vocabulary differ between siblings |
| `const PADDING` is 12, 20, 16, 10, 7 or 28 by file; `GAP` 8, 6 or 12; `RADIUS` 4 or 6; `ROW_HEIGHT` 27, 30, 26; `LINE` 17, 22, 32 | The same name for different measurements; each file's privacy makes it legal |

## 3. The target layout

Rules applied: every new file is a child of `browser` or `wall`, so it keeps seeing its parent's private fields; each concept's directory root holds the type, its construction, its setters and the `mod` lines (`00-conventions.md` section 2); tests over about 60 lines go to `tests.rs`; `cfg` stays on the items that have two forms; the `_ui` suffix goes with the directories; public paths stay under `browser::` by `pub use` in `browser.rs`.

```
src/
  lib.rs                            35  unchanged
  browser.rs                      ~300  doc; mod lines; pub use re-exports; MAX_ADDRESS, LINE_HEIGHT; struct Browser; new;
                                        wall, wall_mut, take_outputs
  browser/
    output.rs                     ~160  Output, WindowAction
    shown.rs                      ~110  Frame, TabInfo, StripState, CertificateProblem: what the trusted core shows
    keys.rs                       ~200  Key, Modifiers; key, shortcut; test shift_w_closes_the_window
    pointer.rs                    ~330  Cursor; pointer_moved, cursor, pointer_released, pointer_pressed, wheel_lines,
                                        middle_pressed, new_tab_pressed, open_in_new_tab, secondary_pressed, scroll_by;
                                        three tests
    regions.rs                     ~60  TabRegion, Regions, Regions::clear
    frames.rs                      ~90  animating, frame_interval, settle; the pulse and frame-interval constants; one test
    pages.rs                      ~190  set_channel, add_page, page_updated, updated_at, page_key, select_page, choose_bank,
                                        reveal_row, bank_pages, opened, type_digit, follow_zoom, step_page; DECIMAL_DIGITS; two tests
    address.rs                    ~200  start_editing, stop_editing, edit, offset_at, draw_address; CARET_WIDTH, FIELD_PADDING;
                                        two tests
    focus.rs                       ~70  close_panels, focused_field, selected_text, cut, paste_text
    window.rs                     ~140  draw; BODY_TOP, MARGIN, BANKS_WIDTH, LIST_WIDTH, OVERVIEW_HEIGHT, HEADING_HEIGHT, PADDING;
                                        one test
    toolbar.rs                    ~210  draw_toolbar; the toolbar, padlock, star and menu-bar constants; three tests
    glyphs.rs                     ~230  chevron, arrow, speaker_glyph, padlock, house, reload_glyph, gear, star and their constants
    banks.rs                       ~90  draw_banks; the bank constants; two tests
    page_list.rs                  ~110  draw_list; ROW_HEIGHT, COLUMN_HEAD_HEIGHT, TITLE_COLUMN, SCROLL_BAR_WIDTH
    overview.rs                   ~260  draw_legend, draw_overview, draw_preview, overview_page, cell_index, toggle_overview;
                                        the overview constants
    overview/tests.rs              ~90  four tests
    tab_strip.rs                  ~220  the tab constants, TabRegion stays in regions.rs; Drag, TabsUi, whole, arrangement;
                                        set_tabs, set_sounding, tab_sounding, all_muted, tabs_tips
    tab_strip/draw.rs             ~150  draw_tab_strip, draw_window_buttons, draw_tabs, draw_tab, draw_tab_overflow
    tab_strip/drag.rs             ~110  tabs_press, tabs_moved, tabs_released, tab_place_at, tabs_cancel
    tab_strip/tests.rs            ~210  five tests from tabs_ui.rs and four from browser.rs
    widgets.rs                      87  unchanged
    fixture.rs                     ~70  cfg(test): WIDTH, HEIGHT, channel(), browser(), press_at(), middle(), cell_centre()
    bookmarks.rs                  ~200  doc, consts, Field, Form, Controls, ItemControls, BookmarksUi, Default, editor;
                                        set_bookmarks, bookmarks_open, toggle_bookmarks, focus/unfocus, bookmarks_editing,
                                        bookmarks_field, bookmarks_undo_shown, bookmarks_deadline
    bookmarks/input.rs            ~230  start_form, submit_form, bookmarks_key, bookmarks_scroll, bookmarks_press, bookmark_at,
                                        bookmarks_released
    bookmarks/draw.rs             ~240  draw_bookmarks_panel, draw_chooser, bookmarks_tips
    bookmarks/tests.rs            ~180
    history.rs                    ~180  consts, RANGES, Controls, RowAction, HistoryUi, Clears, Default; set_history, history_open,
                                        toggle_history, set_history_open, clear_history_choices, unfocus_history, history_query,
                                        history_editing, history_field
    history/input.rs              ~130  history_key, history_scroll, history_row_at, history_press
    history/draw.rs               ~190  draw_history_panel, history_tips
    history/tests.rs              ~165
    settings_panel.rs             ~210  consts, Field, Kind, Controls, SettingsUi, Default, editor, refresh, proxy; set_settings,
                                        set_update, settings_open, settings_editing, toggle_settings, focus/unfocus, change,
                                        submit, settings_field, settings_area
    settings_panel/input.rs       ~110  settings_key, settings_press
    settings_panel/draw.rs        ~180  draw_settings_panel, draw_settings_field, settings_tips
    settings_panel/tests.rs       ~155
    typing.rs                     ~260  cfg(interaction): consts, CursorView, TypingView, Echo, TerminalUi, cut; set_typing,
                                        typing_target, typing_modes, composes_for_channel, set_browser_modifier, strip_has_keys,
                                        pointer_on_page, mouse_is_hosts, click_is_hosts, send, terminal_key, terminal_text,
                                        terminal_paste, terminal_compose, terminal_button, terminal_moved, terminal_wheel, echo,
                                        settle_echoes, terminal_frame_interval
    typing/draw.rs                 ~80  draw_terminal, draw_typing_badge; the badge constants
    typing/tests.rs               ~220
    console_panel.rs              ~210  consts, ConsoleUi, Default, level_index, level_colour, Tab, TABS, open, keep, shown;
                                        console_update, console_open, toggle_console, manage_cookies, choose_console_tab, set_paused
    console_panel/input.rs         ~90  console_press, stop_console_search, console_searching, console_field, console_key,
                                        console_scroll
    console_panel/draw.rs         ~130  draw_console, console_tips
    console_panel/tests.rs        ~150
    cookies_tab.rs                ~300  as cookies_ui.rs without its tests
    cookies_tab/tests.rs          ~100
    hyperlinks.rs                 ~330  cfg(links): as link_ui.rs without its tests
    hyperlinks/tests.rs           ~215
    menu.rs                       ~150  Item, MenuUi; toggle_menu, menu_press, draw_menu; MENU_WIDTH; one test
    tab_lists.rs                  ~160  TabListUi; hold_back_or_forward, release_back_or_forward, ask_tab_list, settle_hold,
                                        hold_deadline, set_tab_list, tab_list_press, draw_tab_list; LIST_WIDTH, HOLD_MILLISECONDS
    tab_lists/tests.rs             ~60  back_held_opens_its_list
    suggestions.rs                ~150  SuggestionsUi; edited, set_suggestions, choose_suggestion, take_chosen_suggestion,
                                        close_suggestions, suggestion_at, suggestion_press, draw_suggestions; one test
    popups.rs                      ~40  ROW, GAP shared by the three; draw_popups, popups_press, popup_open, close_popup
    remote.rs                     ~200  consts, Button, RemoteUi, out; set_remote, move_remote, put_remote, toggle_remote,
                                        remote_time, remote_shown, remote_animating, remote_docked_width, remote_press,
                                        remote_moved, remote_released, panel_height, corner
    remote/draw.rs                ~170  draw_remote, draw_remote_keys, key, subpage_words, remote_tips
    remote/tests.rs                ~85
    star.rs                       ~230  the popover: consts, PopoverControls, StarUi, Default; set_star, star_open, unfocus_star,
                                        star_done, star_editing, star_key, star_field, star_press, draw_star_popover
    star/tests.rs                  ~40  the_popover_asks_for_each_change
    bookmarks_bar.rs              ~190  BAR_HEIGHT, the chip constants, BarUi; bar_tips, set_bar, bar_shown, toggle_bar,
                                        bar_bookmark_at, bar_press, draw_bar, draw_bar_list; two tests inline
    page_controls.rs              ~150  as controls_ui.rs without its tests
    page_controls/tests.rs         ~80
    certificate_refused.rs        ~190  as refused_ui.rs (tests of 60 lines stay inline)
    tips.rs                       ~270  as tips_ui.rs (tests of 51 lines stay inline)
    phone.rs                      ~265  cfg(phone-keyboard): as phone_ui.rs (tests of 34 lines stay inline)
  wall.rs                         ~300  doc; mod lines; WallPage, CellClick, cell_in, Drawn, Wall, Default, new, to_top; the
                                        queries (contains, scroll_by, over_bar, cell_at, open, close_button, size_buttons, area,
                                        shown, visible, over_page, zoomed, reveal, layout, animating); the *_for_tests accessors
  wall/
    updates.rs                     ~45  glow, since, UPDATE_GLOW_MILLISECONDS, UPDATE_MARK_MILLISECONDS, MILLISECONDS_PER_SECOND,
                                        GLOW_WIDTH (re-exported from wall.rs)
    zoom.rs                       ~190  zoom, start_zoom, step_zoom, wheel_pages, wheel_notch, switch_zoom, unzoom, zoomed_rect,
                                        draw_zooming, draw_zoomed, draw_close; ZOOM_*, SLIDE_*, WHEEL_*, CLOSE_* constants
    size_control.rs               ~120  set_width, step, width_at, pointer_pressed, pointer_moved, pointer_released, wheel_bar,
                                        draw_controls; the control-row constants
    hover.rs                       ~60  hover, draw_popped; HOVER_* constants
    grid.rs                       ~150  bring_into_view, draw_grid, draw_list; the wall-layout constants
    draw.rs                        ~80  draw, draw_page
    tests.rs                      ~245
  session.rs                       ~40  WindowGeometry, MAX_COORDINATE, MAX_WINDOW_SIZE, MAX_WINDOWS (re-exported from library.rs)
  text.rs                           57  ui.rs renamed
  library.rs, links.rs, editor.rs, theme.rs, size.rs, settings.rs, channel.rs, canvas.rs, tween.rs, controls.rs,
  console.rs, geometry.rs, cookies.rs, input.rs, test_canvas.rs   unchanged
```

About 95 files; the largest about 330 lines (`pointer.rs`, `hyperlinks.rs`); none over 500; `impl` blocks all under 300; about 2,350 of the 2,712 test lines in `tests.rs` files.

**Public paths kept.** `browser.rs` carries: `pub use output::{Output, WindowAction}; pub use shown::{CertificateProblem, Frame, StripState, TabInfo}; pub use keys::{Key, Modifiers}; pub use pointer::Cursor;` and keeps `#[cfg(feature = "interaction")] pub use typing::{CursorView, TypingView};` and `#[cfg(feature = "phone-keyboard")] pub use phone::{PhoneStatus, PhoneUiView};`. `library.rs` carries `pub use crate::session::{WindowGeometry, MAX_COORDINATE, MAX_WINDOW_SIZE, MAX_WINDOWS};`. `wall.rs` carries `pub use updates::{glow, since, UPDATE_GLOW_MILLISECONDS, UPDATE_MARK_MILLISECONDS};`. No importer in `interface`, `core`, `protocol`, `decoder`, `fetcher`, `draw-vello`, `draw-embedded` or `fuzz` changes.

Departure from `00-conventions.md` section 2 ("a crate's public API is named in `lib.rs`"): the API stays under `interface_core::browser::` and the other root modules, as every importer names it today; flattening it into `lib.rs` would change every path in six crates for no structural gain. The re-exports sit in `browser.rs`, which is the module's spine.

**The one change of a field's type.** `Browser::popups: popup_ui::PopupUi` becomes three fields, `menu: menu::MenuUi`, `tab_lists: tab_lists::TabListUi`, `suggestions: suggestions::SuggestionsUi`, each holding the part of `PopupUi` (`popup_ui.rs:90-107`) its file uses. `Browser::new` and every `self.popups.` prefix change with it (step 24). No behaviour changes.

## 4. The moves

Each step is one commit that compiles and passes `scripts/check.sh commit` (Clippy with every feature, with none, and with each area alone; the tests). Items are named with their source line range in the file as it stands before the step. "Promoted" means a method or constant that was private in `browser.rs` and is now called from another file of the `browser` tree: it becomes `pub(super)` while every caller is a direct child of `browser`, and `pub(in crate::browser)` once a caller sits in a panel directory (step 17 onwards). `Browser`'s fields stay private throughout. Every moved file starts with its doc comment and uses absolute `crate::` paths for its imports; items land in the order of `00-conventions.md` section 7.

The order is leaves first: types, then the glyphs and regions that drawing needs, then the fixture that tests need, then logic, then drawing, then the two dispatchers, then the panels, then the wall, then the root modules.

1. **`browser/output.rs`.** Move `WindowAction` (299-308) and `Output` (312-444). Add `mod output; pub use output::{Output, WindowAction};`. The seven gated variants move verbatim; `Output::PageControl` and the five `library` and `cookies` requests keep their `crate::` paths. No promotion. Message: paths unchanged.

2. **`browser/shown.rs`.** Move `Frame` (194-199), `TabInfo` (203-214), `StripState` (220-245, with its `struct_excessive_bools` allow), `CertificateProblem` and its impl (250-295). `mod shown; pub use shown::{CertificateProblem, Frame, StripState, TabInfo};`.

3. **`browser/fixture.rs`** (`#[cfg(test)] mod fixture;`). Move `WIDTH`, `HEIGHT`, `channel()`, `browser()`, `press_at()` (2265-2303) and `cell_centre()` (2515-2522) as `pub(super)`; add `middle(rect: Rect) -> Point` as one more `pub(super)` function (new, nine lines; the only new code in the step). `browser.rs`'s tests import from it. The nine `middle` copies in the panels are not touched here (step 33).

4. **`browser/glyphs.rs`.** Move `chevron`, `arrow`, `speaker_glyph`, `padlock`, `house`, `reload_glyph`, `gear`, `star` (2068-2085, 2108-2258; the stray doc line at 2189 goes above `star`) with `WINDOW_GLYPH`, `WINDOW_GLYPH_THICKNESS` (77-78), `SPEAKER_HALF`, `SPEAKER_LINE` (68-71), `LOCK_*`, `SHACKLE_*` (86-90), `STAR_RADIUS`, `STAR_INNER`, `STAR_POINTS` (92-95), `ARROW_*` (100-102), `HOUSE_*`, `ROOF_HEIGHT`, `DOOR_*` (103-109), `RELOAD_*` (110-119), `GEAR_*` (120-124), `CHEVRON_*` (176-178). All `pub(super)`. `draw_window_buttons` (2087-2106) stays for step 15. `tabs_ui.rs:11-14` and `popup_ui.rs:380` import from `super::glyphs`. `LOCK_WIDTH` and `STAR_RADIUS` are also read by `draw_toolbar` and `draw_suggestions`.

5. **`browser/regions.rs`.** Move `TabRegion` (502-509) and `Regions` with `clear` (513-550); struct, fields and method `pub(super)` (fields: `00-conventions.md` section 6 asks for methods instead of exposed fields; here the record is written by every drawing file and read by every hit-test, and a method per rect would be 23 getters and 23 setters — the fields are the record, as `Controls` is in each panel; said so in the commit).

6. **`browser/frames.rs`.** Move `animating`, `frame_interval`, `settle` (783-836) with `PULSE_MILLISECONDS`, `PULSE_SCALE`, `PULSE_LIMIT`, `SMOOTH_FRAME_MILLISECONDS`, `MARK_FRAME_MILLISECONDS`, `PULSE_FRAME_MILLISECONDS` (153-172) and the test `an_update_in_another_bank_asks_for_frames_only_while_its_ring_bursts` (2426-2442, inline). `frame_interval` keeps its two `cfg(interaction)` lines (816-819) and `settle` its twin (829-832): one item in two forms. `PULSE_*`, `UPDATE_RING_MILLISECONDS` and `PULSE_LIMIT` are read by the overview and `add_page`: `pub(super)`.

7. **`browser/pages.rs`.** Move `set_channel`, `add_page`, `page_updated`, `updated_at` (718-765), `page_key`, `select_page`, `choose_bank`, `reveal_row`, `bank_pages` (838-883), `opened` (965-971), `type_digit` (1308-1328), `follow_zoom`, `step_page` (1483-1508), `DECIMAL_DIGITS` (187), and the tests `three_digits_choose_a_page_and_a_received_page_pulses` and `the_opened_page_is_the_zoomed_one_or_else_the_one_chosen` (2412-2453, inline). Promoted: `updated_at`, `page_key`, `select_page`, `choose_bank`, `reveal_row`, `bank_pages`, `type_digit`, `follow_zoom`, `step_page`. `add_page` and `type_digit` keep their `cfg(links)` lines.

8. **`browser/address.rs`.** Move `stop_editing`, `start_editing` (885-891, 922-932), `edit` (1450-1481), `offset_at` (1511-1522), `draw_address` (1750-1792), `CARET_WIDTH` (96), `FIELD_PADDING` (85), and the tests `typing_an_address_navigates`, `the_focused_field_copies_cuts_and_pastes` (2397-2410, 2676-2698, inline). Promoted: `stop_editing`, `start_editing`, `edit`, `offset_at`, `draw_address`, `FIELD_PADDING` (read by the toolbar).

9. **`browser/focus.rs`.** Move `close_panels` (906-920), `focused_field` (1398-1420), `selected_text`, `cut`, `paste_text` (1422-1448). Promoted: `close_panels`, `focused_field`.

10. **`strip_has_keys` to `terminal_ui.rs`.** Move the gated `strip_has_keys` (893-904) into `terminal_ui.rs`'s `impl Browser`, private, beside `typing_target`, its only caller. This takes a feature-gated item out of a shared file (`00-conventions.md` section 3). One item, one commit.

11. **`browser/toolbar.rs`.** Move `draw_toolbar` (1641-1748) with `TOOLBAR_TOP`, `TOOLBAR_HEIGHT`, `TOOL_SIZE`, `TOOL_INSET`, `LOCK_GAP` (81-84, 91), `MENU_BAR_WIDTH`, `MENU_BAR_HEIGHT`, `MENU_BAR_GAP` (97-99), and the tests `reload_sits_between_forward_and_home_and_has_its_keys`, `home_is_asked_for_by_its_button_and_its_keys`, `the_strip_says_the_notice_and_names_the_start_page` (2599-2674, inline). Its three gated sites move verbatim. Promoted: `draw_toolbar`, `TOOLBAR_TOP`, `TOOLBAR_HEIGHT` (read by `draw`). Calls `self.all_muted()` and `self.settings_open()`, both still visible.

12. **`browser/banks.rs`.** Move `draw_banks` (1794-1834) with `BANK_GAP`, `BANK_MAX_HEIGHT`, `SWATCH_WIDTH`, `SWATCH_INSET`, `BANK_BORDER`, `BANK_RANGE_RISE` (134-140) and the tests `the_first_bank_is_shown_and_reported_visible`, `choosing_a_bank_shows_its_pages` (2305-2324, inline). Promoted: `draw_banks`, `BANK_BORDER` (read by `draw_tab`).

13. **`browser/page_list.rs`.** Move `draw_list` (1836-1906) with `ROW_HEIGHT`, `COLUMN_HEAD_HEIGHT`, `TITLE_COLUMN`, `SCROLL_BAR_WIDTH` (141-145). Promoted: `draw_list`, `ROW_HEIGHT` (read by `reveal_row`).

14. **`browser/overview.rs` and `overview/tests.rs`.** Move `overview_page` (959-963), `toggle_overview` (986-991), `cell_index` (1524-1534), `draw_legend`, `draw_overview` (1908-2031), `draw_preview` (2034-2066), the constants `AXIS_WIDTH`, `CELL_GAP`, `LEGEND_*` (148-152), `ROW_FLASH`, `UPDATE_RING_*`, `UPDATE_DOT_INSET` (162-170), `TOGGLE_SIZE` (175), `PREVIEW_*` (179-183), and the four overview tests (2501-2597) into `overview/tests.rs`. Promoted: `overview_page`, `toggle_overview`, `cell_index`, `draw_overview`, `draw_preview`. The second `impl Browser` block disappears.

15. **`browser/window.rs`.** Move `draw` (1536-1619) with `BODY_TOP`, `MARGIN`, `BANKS_WIDTH`, `LIST_WIDTH`, `OVERVIEW_HEIGHT`, `HEADING_HEIGHT`, `PADDING` (126-133) and the test `the_console_takes_the_overviews_place` (2712-2723, inline). `MARGIN`, `BODY_TOP`, `HEADING_HEIGHT`, `PADDING`, `OVERVIEW_HEIGHT` are read by banks, list, overview, remote, star, tips: `pub(super)`. The three gated sites in `draw` move verbatim. `remote_ui.rs`'s four `super::MARGIN` become `super::window::MARGIN`.

16. **`browser/pointer.rs`.** Move `Cursor` (475-484; `pub use pointer::Cursor;`), `pointer_moved` (936-957), `cursor` (973-984), `pointer_released` (993-1004), `pointer_pressed` (1006-1151, with its allow and four gated sites), `wheel_lines` (1153-1165), `middle_pressed`, `new_tab_pressed`, `open_in_new_tab`, `secondary_pressed` (1167-1220), `scroll_by` (1222-1250), and the tests `a_click_on_a_page_zooms_it_and_escape_returns`, `the_pointer_is_a_hand_only_over_a_page_a_click_would_zoom`, `the_wheel_over_the_page_size_bar_slides_it` (2455-2499, inline). No promotion: everything it calls is already `pub(super)` or public.

17. **`browser/keys.rs`.** Move `Key` (446-473), `Modifiers` (486-498; `pub use keys::{Key, Modifiers};`), `key` (1252-1306, with its gated site), `shortcut` (1330-1396), and the test `shift_w_closes_the_window` (2700-2710, inline). `browser.rs` now holds the struct, `new`, `frame_version`, `set_tabs`, `set_sounding`, `tab_sounding`, `all_muted`, `set_strip`, `wall`, `wall_mut`, `take_outputs`, `draw_tab_strip`, `draw_window_buttons`, the tab constants, and the four tab tests, at about 520 lines until step 18.

18. **`browser/tab_strip.rs`: the tab strip in one place.** `git mv browser/tabs_ui.rs browser/tab_strip.rs`; move into it from `browser.rs` the tab constants `STRIP_HEIGHT` … `WINDOW_BUTTON_GAP` (56-76), `set_tabs`, `set_sounding`, `tab_sounding`, `all_muted` (687-711), `draw_tab_strip` (1621-1639), `draw_window_buttons` (2087-2106), and the tests `a_tab_playing_sound_shows_a_speaker_that_mutes_it`, `the_mute_all_button_mutes_every_tab_until_all_are_muted`, `tabs_back_and_window_buttons_report_what_was_pressed`, `the_middle_button_closes_the_tab_under_it` (2326-2395, 2621-2635). `mod tabs_ui` becomes `mod tab_strip`; `self.tab_strip` already names the field. Promoted: `all_muted`, `draw_tab_strip`, `STRIP_HEIGHT` (read by tips). `browser.rs` is now about 300 lines: the spine.

19. **`browser/tab_strip/{draw,drag,tests}.rs`.** From `tab_strip.rs` (now about 650 lines): `draw.rs` takes `draw_tab_strip`, `draw_window_buttons`, `draw_tabs`, `draw_tab`, `draw_tab_overflow`; `drag.rs` takes `tabs_press`, `tabs_moved`, `tabs_released`, `tab_place_at`, `tabs_cancel`; `tests.rs` takes the nine tests and `browser_with`. `draw_tab` is called from `draw.rs` only: private there. Methods called from `window.rs` and `pointer.rs` (`draw_tab_strip`, `draw_tab_overflow`, `tabs_press`, `tabs_moved`, `tabs_released`, `tabs_cancel`) become `pub(in crate::browser)`. `TabsUi`'s fields are private in `tab_strip.rs` and visible to its children.

20. **`browser/bookmarks` directory.** `git mv bookmarks_ui.rs bookmarks.rs`; `mod bookmarks;`; `self.bookmarks` already names the field. Then `bookmarks/input.rs` (`start_form`, `submit_form` 210-230, `bookmarks_key` 232-287, `bookmarks_scroll` 295-314, `bookmarks_press` 316-396, `bookmark_at` 398-407, `bookmarks_released` 449-482), `bookmarks/draw.rs` (`bookmarks_tips` 149-156, `draw_chooser` 409-447, `draw_bookmarks_panel` 495-684), `bookmarks/tests.rs` (687-867). The root keeps the consts, types, `Default`, `editor`, `set_bookmarks`, `bookmarks_open`, `toggle_bookmarks`, `focus_bookmarks`, `unfocus_bookmarks`, `bookmarks_editing`, `bookmarks_field`, `bookmarks_undo_shown`, `bookmarks_deadline`. Promotions: every method called from outside the directory (`bookmarks_key`, `bookmarks_field`, `bookmarks_scroll`, `bookmarks_press`, `bookmark_at`, `bookmarks_released`, `bookmarks_deadline`, `draw_bookmarks_panel`, `bookmarks_tips`, `toggle_bookmarks`, `bookmarks_editing`) `pub(in crate::browser)`; `focus_bookmarks`, `unfocus_bookmarks`, `start_form`, `submit_form`, `bookmarks_undo_shown` `pub(super)` where a child calls them. The `Controls` fields stay private in the root, visible to the children. One commit for the rename, one for the directory.

    Departure from `00-conventions.md` section 4's example (`browser/history/{state,draw,input}.rs`): the state struct is in the directory's root file, not a `state.rs`, because section 2 puts the type and its construction in the parent and because a sibling `state.rs` would force every field `pub(super)`.

21. **`browser/history` directory**, the same way: rename; root 1-215 and 252-255 (consts, `Controls`, `RowAction`, `HistoryUi`, `Clears`, `Default`, `history_tips` moves to draw, `set_history`, `history_open`, `toggle_history`, `set_history_open`, `clear_history_choices`, `unfocus_history`, `history_query`, `history_editing`, `history_field`); `input.rs` (`history_key` 217-250, `history_scroll` 257-271, `history_row_at` 273-280, `history_press` 282-353); `draw.rs` (`history_tips` 137-144, `draw_history_panel` 355-520); `tests.rs` (523-688). Promotions as in step 20.

22. **`browser/settings_panel` directory.** `git mv settings_ui.rs settings_panel.rs` (named apart from `crate::settings`, which holds the views); the field stays `settings`. Root: 1-251 and 286-290, 358-361; `input.rs` (`settings_key` 253-284, `settings_press` 292-356); `draw.rs` (`settings_tips` 172-181, `draw_settings_panel` 363-519, `draw_settings_field` 521-524); `tests.rs` (527-681).

23. **`browser/typing` directory** (`#[cfg(feature = "interaction")] mod typing;`). `git mv terminal_ui.rs typing.rs`; the field `terminal` becomes `typing` to agree with the module (a rename inside the crate: `self.terminal.` in the file and the three sites in `browser.rs`). `pub use typing::{CursorView, TypingView};`. Then `typing/draw.rs` (`draw_terminal` 349-384, `draw_typing_badge` 386-415, `BADGE_*` 41-44) and `typing/tests.rs` (418-635). `draw_terminal` and `draw_typing_badge` `pub(in crate::browser)`.

24. **`browser/console_panel` directory.** `git mv console_ui.rs console_panel.rs` (apart from `crate::console`); field stays `console`. Root 1-219; `input.rs` (`console_press` 221-256, `stop_console_search` 258-263, `console_searching`, `console_field`, `console_key` 265-293, `console_scroll` 295-306); `draw.rs` (`console_tips` 308-334, `draw_console` 336-432); `tests.rs` (435-586). `CONSOLE_HEIGHT` and `area` stay `pub(in crate::browser)`.

25. **The drop-downs: `menu.rs`, `tab_lists.rs`, `suggestions.rs`, `popups.rs`.** From `popup_ui.rs`: `menu.rs` takes `Item` and its impl (25-86), `MENU_WIDTH` (17), the menu methods (110-182) and the test `the_menu_holds_history_and_bookmarks` (510-526, inline); `tab_lists.rs` takes `LIST_WIDTH`, `HOLD_MILLISECONDS` (18, 22-23), the list methods (184-287) and, in `tab_lists/tests.rs`, `back_held_opens_its_list` (448-488) with the `press` helper; `suggestions.rs` takes the suggestion methods (289-395) and the test `typing_asks_for_suggestions_and_completes_inline` (490-508, inline); `popups.rs` takes `ROW`, `GAP`, `SHORTCUT_GAP` (19-21) and the four joint methods (397-421). `PopupUi` (90-107) splits into `MenuUi { menu_open, menu, menu_area }`, `TabListUi { tab_list, entries, show_all, list_area, held }`, `SuggestionsUi { suggestions, chosen, rows, suggestions_area, deleted }`, and `Browser::popups` becomes `menu`, `tab_lists`, `suggestions` (the change of a field's type named in section 3; `new` and every `self.popups.` prefix updated). The gated `Item::Phone` stays gated. One commit, since the struct cannot be split in two halves that compile.

26. **`browser/remote` directory.** `git mv remote_ui.rs remote.rs`; root 1-191 and 387-397; `draw.rs` (`draw_remote` 193-240, `draw_remote_keys` 242-347, `remote_tips` 349-384, `subpage_words` 399-408, `key` 410-415); `tests.rs` (417-500, dropping the module-level `unwrap_used` allow that `clippy.toml` already grants — noted in the commit).

27. **`browser/star.rs` and `browser/bookmarks_bar.rs`.** From `star_ui.rs`: `star.rs` takes the popover consts (20-29), `PopoverControls`, `StarUi`, `Default` (38-65), the popover methods (88-264) and, in `star/tests.rs`, `the_popover_asks_for_each_change` (422-457) with `middle` and `browser`; `bookmarks_bar.rs` takes `BAR_HEIGHT` and the chip consts (30-36), `BarUi` (67-76), `bar_tips` (79-86), the bar methods (266-402) and the two bar tests (459-496, inline). `mod star; mod bookmarks_bar;`; fields `star` and `bar` unchanged. `BAR_HEIGHT` `pub(in crate::browser)`.

28. **Single-file panels renamed, tests out where they are long.** `git mv cookies_ui.rs cookies_tab.rs` with `cookies_tab/tests.rs` (304-404); `git mv link_ui.rs hyperlinks.rs` (`#[cfg(feature = "links")] mod hyperlinks;`; field `links` unchanged) with `hyperlinks/tests.rs` (331-544); `git mv controls_ui.rs page_controls.rs` (field already `page_controls`) with `page_controls/tests.rs` (151-231, dropping its redundant allow); `git mv refused_ui.rs certificate_refused.rs`, `tips_ui.rs tips.rs`, `phone_ui.rs phone.rs` (tests stay inline: 60, 51 and 34 lines). One commit per file, each updating its `mod` line and the `pub use` for `phone`.

29. **`wall/updates.rs`.** Move `glow`, `since`, `UPDATE_GLOW_MILLISECONDS`, `UPDATE_MARK_MILLISECONDS`, `MILLISECONDS_PER_SECOND`, `GLOW_WIDTH` (`wall.rs:100-125`); `mod updates; pub use updates::{glow, since, UPDATE_GLOW_MILLISECONDS, UPDATE_MARK_MILLISECONDS};` so `crate::wall::glow` in `page_list.rs`, `overview.rs` and `frames.rs` holds. `GLOW_WIDTH` `pub(super)`.

30. **`wall/tests.rs`.** Move 926-1168; `#[cfg(test)] mod tests;`. The tests read `wall.close`, `wall.plus`, `wall.width`, `wall.max`, `wall.slide`: still visible, as a child of `wall`.

31. **`wall/{zoom,size_control,hover,grid,draw}.rs`.** One commit making the directory: `zoom.rs` (263-371, 682-760 and `ZOOM_*`, `SLIDE_*`, `WHEEL_*`, `CLOSE_*` 55-84), `size_control.rs` (373-438, 466-486, 884-922 and the control-row consts 23-36), `hover.rs` (543-595 and `HOVER_*` 61-67), `grid.rs` (762-882 and `WALL_PADDING` … `CAPTION_NUMBER_WIDTH` 39-54), `draw.rs` (602-680). Promoted to `pub(super)`: `start_zoom`, `draw_page`, `zoomed_rect`, `bring_into_view`, `layout`, `draw_zoomed`, `draw_zooming`, `draw_close`, `draw_popped`, `draw_grid`, `draw_list`, `draw_controls`, `set_width`. `wall.rs` keeps `WallPage`, `CellClick`, `cell_in`, `Drawn`, `Wall`, `Default`, `new`, `to_top`, the queries and the `*_for_tests` accessors.

32. **`session.rs` and `text.rs`.** `src/session.rs` takes `WindowGeometry`, `is_plausible`, `MAX_COORDINATE`, `MAX_WINDOW_SIZE` (`library.rs:376-407`) and `MAX_WINDOWS` (30-33); `library.rs` re-exports them so `core/src/session.rs`, `fuzz/fuzz_targets/netscape_file.rs` and `decoder/src/netscape.rs` (which import `MAX_FOLDER_DEPTH`, unmoved) are untouched. `git mv src/ui.rs src/text.rs` with `mod text;` and the import lines in the 20 files that use it (`crate::ui::` → `crate::text::`): a rename because the name misleads (section 2.5). Two commits.

33. **The function splits** (not moves: each cuts one function into named parts in the same order of operations, verified by the tests it already has; `00-conventions.md` section 1 asks for it; one commit per function, the allow removed with it). `pointer_pressed` → `press_overlays` (1017-1043), `press_strip` (1044-1098), `press_body` (1099-1150), each returning `Option<bool>`, called in that order. `draw_bookmarks_panel` → `draw_toolbar_row`, `draw_tree`, `draw_path`, `draw_form`, `draw_contents`, `draw_footer` at its comments (514, 535, 560, 578, 616, 669), each taking `&mut Controls` and the running `y`. `draw_history_panel` → `draw_search_row`, `draw_clearing`, `draw_closed_tabs`, `draw_rows`, `draw_row_menu`, `draw_footer` (374, 384, 408, 427, 483, 508). `draw_settings_panel` → one function per row (385, 394, 411, 435, 445, 459, 481, 511). `draw_remote_keys` → `draw_title_row`, `draw_readout`, `draw_pad`, `draw_page_keys`, `draw_fastext_keys`, `draw_subpage_row`, `draw_toggles` (250, 263, 275, 288, 298, 318, 333). `draw_overview` → `draw_cells`, `draw_rings`, `draw_pulses` (1961, 2004, 2018). `draw_console` → `draw_console_bar`, `draw_console_entries` (342, 410). `draw_toolbar` → `draw_tool_buttons`, `draw_address_field` (1645, 1683). `shortcut` → `shortcut_letter` for the table at 1361-1394. With these, no function in the crate is over 80 lines of code.

34. **The test helpers** (a change to tests, noted per `00-conventions.md` section 5): the nine `middle` and five `open`/`browser` copies in the panels' `tests.rs` files replaced by imports from `browser::fixture`. One commit.

No step adds a `#![deny(...)]` list to `lib.rs`: the crate is not a `NO_PANIC_ROOT` and reads nothing from outside its process (section 1.1); the split makes modules, not a crate root.

Import updates in other crates: none. Every path in section 1.6 is kept by a `pub use`; `core/Cargo.toml`, `protocol/Cargo.toml`, `decoder/Cargo.toml` and `fetcher/Cargo.toml` forward the same three features.

Measured after (expected): about 95 files; largest about 330 lines, median about 150; none over 500; no function over 80 lines of code; no `impl` over 300; about 2,350 test lines in `tests.rs` files; `cfg` sites in shared files down by two (`strip_has_keys`), the rest being single items with two forms.

## 5. Risks particular to this crate

| Risk | Where | How the steps meet it |
|---|---|---|
| A feature shape stops building: a moved `use` is used only under a feature, or a gated call moves away from its `cfg` line | `pointer.rs` (`neoteletext_input::event::MouseAction` at 1003, 1140), `keys.rs` and `pages.rs` (`link_typed`, `link_key`), `frames.rs` (`terminal_frame_interval`, `settle_echoes`), `window.rs` and `toolbar.rs` (`draw_links`, `draw_terminal`, `draw_phone_panel`, `draw_phone_badge`, `draw_typing_badge`, `draw_prompt`, `draw_pointing`) | Each gated line moves with its function unchanged; a `use` needed only by gated code is itself gated. `scripts/check.sh commit` runs the four Clippy shapes at every step. |
| `pub(super)` no longer reaches once a panel is a directory: a method marked `pub(super)` in `browser/bookmarks/input.rs` is visible to `browser::bookmarks` only, not to `browser::pointer` | steps 19-27 | Anything called from outside the panel is `pub(in crate::browser)`; `pub(super)` is for calls inside the panel. The state struct is defined in the directory's root so its private fields stay visible to `draw.rs` and `input.rs`. `use super::widgets` in a nested file would resolve wrongly: every moved file uses `crate::browser::widgets`. |
| `unused_qualifications` fires when a `use crate::theme::Colour` is added to a file that keeps a `crate::theme::Colour` in a signature | `console_ui.rs:101`, `refused_ui.rs:70`, `remote_ui.rs:411` | The qualification is dropped in the step that creates the file; `cargo fmt` and Clippy run before the commit. |
| A child imports a name through the parent's own private `use` line, which stops resolving once the parent no longer imports it | `tips_ui.rs:13` (`super::{PAGES_PER_BANK, page_number}`), `tabs_ui.rs:11-14` (the tab constants and `TabRegion` through `super`) | Each moved file imports from the defining module (`crate::channel`, `crate::browser::tab_strip`, `crate::browser::regions`); the step that empties `browser.rs`'s imports (18) updates `tips` in the same commit. |
| `clippy::module_inception` forbids a child named as its parent | — | No `browser/browser.rs`, `wall/wall.rs`, `tab_strip/tab_strip.rs`; the spines are the parents. |
| `missing_docs` on items whose visibility changes | every promotion | Promotions are to `pub(super)` or `pub(in crate::browser)`, which `missing_docs` does not cover; existing docs are kept. |
| A public path moves | `Output`, `Frame`, `Key`, `Cursor`, `CursorView`, `PhoneStatus` and the rest of section 1.6; `library::WindowGeometry`; `wall::glow` | The `pub use` lines of section 3 land in the same commit as each move; the gate's workspace Clippy build catches a missing one, as `core`, `protocol`, `interface`, `draw-*` and `fuzz` all import these paths. |
| A test that reaches a private field across the new boundary | `browser.rs:2722` (`self.console.area`, already `pub(super)`), the panels' tests (`browser.bookmarks.controls.items[1].row` and the like), `wall`'s tests | They move into `tests.rs` under the module that owns the field, where the descendant rule covers them; the fixture module is `pub(super)` under `browser`. |
| The parent spine shrinks below the convention's 50-line floor | `browser.rs` after step 18 (about 300: the struct, `new`, three accessors, the `mod` tree) | It stays well above it; `wall.rs` likewise (about 300). |
| Documents name files that move | `docs/architecture.md` section 14, the `interface-core/` line: "history panel, bookmarks manager, star's popover, bookmarks bar, menu, Back and Forward lists and suggestions (browser/*_ui.rs, library.rs)"; `docs/native-interface-design.md` section 12.6: "`interface-core/src/browser/tips_ui.rs`" | Rewritten at phase B5 from the final tree (`01-method-and-order.md` section 2); the 12.6 line changes to `browser/tips.rs` in the commit of step 28, since it is a history note naming one file. |
| The `Browser::popups` type change (step 25) is the one move that is not a pure move | `popup_ui.rs:90-107`, `browser.rs:613, 668` | Named in section 3 and in the commit message; the three new structs hold the same fields with the same names; the tests of the three drop-downs run unchanged. |

## 6. Seen, not part of this plan

- `interface-core` carries no `#![deny(...)]` list and is not in `NO_PANIC_ROOTS`, though `protocol`, which is, re-exports its `CertificateProblem` and takes its `MAX_ADDRESS`. Whether it should be in the list is a question for the owner; the code would need its indexing and arithmetic reworked first.
- `MAX_ADDRESS` is defined in `browser.rs:53` and used by `library.rs:49`, `cookies.rs:13`, `settings_ui.rs:46` and `protocol/src/lib.rs:67`: two root data modules depend upwards on the window module for an address-rules limit.
- `widgets::field` (`widgets.rs:31-58`) and `Browser::draw_address` (`browser.rs:1750-1792`) draw an `Editor` two ways (a computed shift against a kept `field_scroll`); `widgets::button` and `remote_ui::key` draw a button two ways; `remote_ui::subpage_words` and `controls_ui.rs:128-131` write the sub-page count twice.
- `remote_ui::RemoteUi::out` (76-85) eases a slide by hand with `STANDARD.at` where `tween::Tween` does the same.
- `phone_ui.rs` has unnamed literals in `draw_phone_badge` and `draw_phone_panel` (`10.0`, `70.0`, `6.0`, `4.0`, `8.0`, `2.0`, `1.5`) against `DEVELOPMENT.md` section 6.
- `phone_ui.rs:187-191` wraps `WARNING` by sentence where `refused_ui::wrapped` (36-52) measures words; one word wrap would serve both.
- Every `*_ui.rs` and nine test modules compute a rectangle's centre by hand; `Rect` has no `centre` method.
- The module-level `#[allow(clippy::unwrap_used, reason = "a test")]` at `controls_ui.rs:152` and `remote_ui.rs:418` is redundant with `clippy.toml`'s `allow-unwrap-in-tests`.
- The doc line "A five-pointed star centred on `centre`." at `browser.rs:2189` sits above `house`, not `star`.
- `library.rs:27` asserts `MAX_STEPS <= u8::MAX`; the equivalent bounds for `MAX_SUGGESTIONS` and `MAX_TAB_LIST` against the `u8`/`u32` fields that carry them are not asserted.
