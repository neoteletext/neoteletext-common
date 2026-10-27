# The standard's limits, defined once, and sub-pages on the wire only when needed

The design for two instructions the owner gave on 26 October 2026:

> "NEOTELETEXT MUST ALLOW ENGINE SERVER AND BROWSER ALL TO HAVE THE MAXIMUM AS DEFINED BY THE STANDARD. AND IDEALLY I WANT THEM ALL TO GET THOSE LIMITS FROM EXACTLY ONE PIECE OF CODE SHARED BY ALL"

> "I WANT SUB PAGES TO PASS THE WIRE ONLY WHEN NEEDED"

It is recorded as the engine's decision E.122, the browser's decision 112 and the server's decision 10. The wire it describes is specified in `SERVER.md` (sections 4, 5, 6, 7.3, 11 and 12); this document says why, and lists the work (section 7). Nothing here is built yet.

## 1. What the standard allows

The highest standard is ETSI EN 300 706 V1.2.1 (2003-04), Enhanced Teletext, which defines Levels 1 to 3.5.

| What | The standard's maximum | Where |
|---|---|---|
| Magazines | 8 (magazine 8 is sent as 0) | Clause 7.1.2 |
| Page numbers in a magazine | 00 to FE, two hexadecimal digits: 255 | Clause 9.3.1.1; Annex A.1 rule 1 |
| Reserved page numbers | mFF in every magazine (time filling, never a page); mFD (Magazine Inventory Page) and mFE (Magazine Organization Table) in every magazine; 1BE (Automatic Channel Installation) and 1F0 (Basic TOP Table) | Annex A.1 rules 2 and 3; Annex A.10 |
| Pages for content | 8 × 253 − 2 = **2,022** | The two rows above |
| Pages a viewer can key | 100 to 899, decimal digits: **800** | REQ-NAV-001 ("hexadecimal page numbers cannot be entered"); the others are reached by links |
| Sub-codes | 13 bits, S1 0–F, S2 0–7, S3 0–F, S4 0–3: 0000 to 3F7F, **8,192** values | Clause 9.3.1.2; Annex A.1 rule 1 |
| Sub-code 0000 | A page with no sub-pages | Annex A.1, display rule 1 |
| Sub-code 3F7F | In a link, "any sub-page"; a sub-page so coded cannot be linked to by itself | Clause 9.6.1; the engine's REQ-NAV-003 |
| **Sub-pages of one page** | 0001 to 3F7E: **8,190**, each addressable | The three rows above |
| Sub-pages numbered in decimal | Annex A.1 display rule 2 numbers sub-pages for display 0001 to 0079, decimal digits in S2 and S1. With all four digits decimal (S4 0–3, S3 0–9, S2 0–7, S1 0–9): 0001 to 3979, the tens digit 0 to 7, **3,199**, each of which a viewer can key | Annex A.1; S2 is three bits |

**Decided:** the engine, the server and the browser each accept every page number the standard allows for content (2,022 a channel) and every addressable sub-page (8,190 a page). The figure the browser and the server used, 64 sub-pages, was this project's own (the engine's `viewer::MAX_LISTED_SUBPAGES`), not the standard's, and it goes.

**Numbering the sub-pages of a page:** the nth sub-page has a sub-code fixed by one function. Places 1 to 3,199 take the decimal sub-codes in ascending order (0001 to 0009, 0010 to 0079, 0100 to 0179, and so on to 3979), so every place a viewer can key is a decimal one and Annex A.1's 0001 to 0079 are the first 79. Places 3,200 to 8,190 take the remaining 4,991 sub-codes in ascending order, 3F7F left out; each has a hexadecimal digit, A to F, in S1 or S3, since S2 cannot pass 7 and S4 cannot pass 3. *Owner to confirm (section 6, question 1).*

## 2. Maxima and budgets

Two kinds of number have been mixed. They are kept apart from now on.

- **A maximum is the standard's:** what may exist and be addressed. Every part accepts every page and sub-page the standard allows. No part refuses one for being one too many.
- **A budget is a resource:** how much is held or sent at once (the browser's decoder store, the server's page store, the pages a connection tunes, bytes a message). A budget bounds memory and traffic, as untrusted input requires (the owner's global instructions; the browser's requirement 1.2; the engine's area SEC). It never decides which pages or sub-pages may exist; it decides how many are held at once, and what falls out is fetched again when it is needed.

So the 4,096 slots of the browser's decoder store stop being a ceiling on a channel and become a cache: a channel of 2,022 pages with 8,190 sub-pages each (16.5 million sub-pages, about 18 GB as Level 1 pages) is valid, and the browser holds the part being looked at. A microcontroller port (the engine's `thumbv6m` and Xtensa targets) keeps the same maxima and a much smaller store (the engine's REQ-ACQ-005: the capacity is the caller's).

## 3. One definition

**Possible, and how:**

1. **One module in the engine,** `neoteletext_core::limits`, `no_std`, with no dependency and no feature gate, holds the standard's maxima as constants, each with its clause, and the function that numbers sub-pages (section 1). It is the only place they are written. It replaces the restatements: `consts::pages::{SUBCODE_MASK, SUBCODE_ANY, FIRST_PAGE, LAST_PAGE}` move into it or are re-exported from it; `viewer::MAX_LISTED_SUBPAGES` is withdrawn; `contents::MAX_PAGES` (800) becomes the number of keyable pages from `limits`, and a separate count covers every content page.
2. **The server and the browser are Rust and import it,** at the engine commit each pins (the server's requirement 2.5, the browser's requirement 2.4): `teletext-runtime`'s `MOST_SUBPAGES` and `MOST_PAGES`, the browser's `interface_core::controls::{MAX_SUBPAGES, ANY_SUBCODE}` and the protocol's counts all become `limits` names. The browser's interface core, which today avoids the engine and restates the bound with an assertion, depends on `neoteletext-core` with its default features off: the module compiles alone, and nothing of the decoder comes with it.
3. **The Python and TypeScript kits cannot import Rust.** They get the numbers at run time instead: the server's `start` message to an application carries a `standard` object (the maxima) and a `budgets` object (the server's own), written from the same `limits` constants, and the kits expose them. A kit and a channel never write a limit as a literal; a test of each kit checks that what it uses came from `start`. So the definition is still one piece of code: the kits hold none.
4. **Clients of other makers** learn the server's budgets from the LIMITS control record (`SERVER.md` section 5.5), which now carries the standard's maxima as well, so a receiver of another maker need not assume them.

The engine and the server and browser pin the engine at commits that may differ; the maxima are the standard's and do not change between commits, which is what makes one definition safe across pins.

## 4. Sub-pages pass the wire only when needed

Today the server holds a page as one frame of all its sub-pages, sends the whole frame to every connection when any sub-page changes and again when a page is opened, and the browser decodes every sub-page to list its title. A page of 8,190 sub-pages would be about 9 MB a change. From now on **the sub-page is the unit** held, versioned, changed and sent, on both wires and in the static layout.

**Downstream, server to browser** (`SERVER.md` sections 5 and 6):
1. **A page's catalogue:** for each page a client tunes, the server sends a SUBPAGES control record: the page's sub-codes, each with a version number; about 4 bytes a sub-page, 33 KB for 8,190. When a sub-page is added, removed or changed, the client gets the change to the catalogue, not the sub-page.
2. **Titles by range:** a sub-page's title (the engine's title of its text, made once by the server when the sub-page is published) comes in TITLES records for a range of places the client asks for, so a list of 8,190 sub-pages fetches only the titles scrolled into view.
3. **Content only when tuned:** TUNE names a page and a sub-page (`SERVER.md` section 5.4, which allowed this already). The client tunes the sub-page shown, the sub-pages either side of it within a budget so that stepping is instant, and for a thumbnail the sub-page the thumbnail shows. Only tuned sub-pages are sent, as page frames; the rest pass the wire when the client tunes them.
4. **Rotation** (the engine's REQ-NAV-005, the latest sub-page shown as it arrives): the catalogue's versions say which sub-page changed last; a client showing the latest tunes that one.

**Upstream, application to server** (`SERVER.md` section 7.3, the server's `applications.md`):
5. **`publish` takes sub-pages:** a publication names the sub-pages it puts, by sub-code (`SC` in TTI, four hexadecimal digits) or by place, and a `remove` names those that go; the server keeps the others. A whole page is a publication of all its sub-pages. One message carries a few sub-pages at most, so the 16 MiB line limit is never near.
6. **The server holds each sub-page once,** with its version, its encoded packets and its title (`SERVER.md` section 6.2).

**A channel served as files, with no server** (`SERVER.md` section 4; the engine's REQ-WEB-025 and the static layout):
7. **`NNN.t42` holds a page's first sub-page,** or the page when it has one; **`NNN-SSSS.t42`** holds sub-page SSSS; **`NNN.sub`** lists the sub-codes, their validators and their titles. A page response stays within the 256 KB limit of REQ-WEB-008 at any number of sub-pages, and the browser fetches a sub-page when it needs it, conditionally.
8. **`index.t42`** carries first sub-pages only, so a channel's opening costs the same at any number of sub-pages.

**In the browser:**
9. **The decoder's store is a cache** of sub-pages within its budget, least recently used out first (section 2), not a ceiling.
10. **The sub-page list** (decision 111) is drawn from the catalogue and the titles fetched by range, as a virtual list, so 8,190 rows cost the rows on screen; its counts and places are 16-bit.
11. **The trusted core decides what is tuned,** from what the interface shows, under a rate limit (`SERVER.md` section 6.1; section 5 below).

## 5. Security

- **Maxima bound nothing; budgets bound everything.** Every reader keeps its limits: a catalogue is at most 8,190 entries, a TITLES record at most a budget of places, a sub-code is checked against the mask, a page number against the reserved numbers.
- **Tuning by sub-page tells a channel which sub-page is read.** A channel already learns which page is open; the sub-page adds detail of the same kind. The browser's security analysis (section on push and tuning) and `SERVER.md` section 6.1's accepted consequence are amended to say so.
- **Titles are untrusted text,** cut and folded as page titles are (the browser's `MAX_PAGE_TITLE`).
- **A channel cannot make the browser hold more** than its store budget, whatever it publishes: what is not tuned is not sent.

## 6. Questions for the owner

1. **Numbering past 3,199** (section 1): the decimal sub-codes first, then the rest ascending. Agree?
2. **The row 0 status area** is seven columns (the engine's decision E.10): "P100" and a place such as "/12". A place up to 8,190 needs four digits. Keep the place in the browser's own controls and show in row 0 only what fits, or widen the status area into the header?
3. **Pages with hexadecimal digits** (2,022 pages a channel, 800 of them keyable): the browser's overview shows 800 squares. Show the other 1,222 as well, and how?
4. **Budgets' first values:** sub-pages either side of the shown one that are tuned ahead (suggested 2), titles a TITLES record carries (suggested 64), and the decoder store (unchanged at 256 to 4,096 sub-pages, now a cache).

## 7. The work

In order; each is one commit or a few, through each repository's gates.

**The engine** (one decision, E.122; then a re-pin in the server and the browser):
1. `neoteletext_core::limits`: the maxima of section 1 with their clauses, the reserved pages, `sub_code_of(place)` and `place_of(sub_code)`, with tests of every row of section 1's table.
2. Replace the restatements: `consts::pages` re-exports from `limits`; `contents::MAX_PAGES` and its siblings name `limits`.
3. Withdraw `viewer::MAX_LISTED_SUBPAGES`: the viewer steps and counts sub-pages through the store (next and previous sub-code after a given one, and a count), with no fixed array, so a microcontroller's stack does not grow with the maximum.
4. REQ-NAV-005 amended: up to 8,190 sub-pages, four-digit entry within the decimal places; the status area per question 2.
5. The static layout: `NNN-SSSS.t42`, `NNN.sub` and first sub-pages in `index.t42`; REQ-WEB-025's neighbour requirements amended, the reader of `NNN.sub` written and fuzzed.
6. The TTI reader's `SC` field checked to carry all 8,190 sub-codes (REQ-INP-013).
7. Re-pin the server and the browser at the commit.

**The server:**
8. `teletext-runtime` uses `limits`: `MOST_SUBPAGES` and `MOST_PAGES` withdrawn; a channel may declare every content page.
9. The page store per sub-page (`SERVER.md` section 6.2): held, versioned, titled and encoded per sub-page.
10. `publish` with sub-pages and `remove`, `start` with `standard` and `budgets` (`applications.md`); validation per sub-page.
11. TUNE and UNTUNE with sub-pages, the SUBPAGES and TITLES records, LIMITS with the maxima (`SERVER.md` sections 5.4 and 5.5); fuzzed.
12. The sender per tuned sub-page; catalogue changes for the rest (`SERVER.md` section 6.3).
13. The static files: `NNN-SSSS.t42`, `NNN.sub`, `index.t42` of first sub-pages.
14. The Python kit and the TypeScript kit: limits from `start`, publication by sub-page, a channel's literal limits removed (the Hackaday channel's `MOST_SUBPAGES` and `TEXT_SUBPAGES`); each kit's test that it holds no literal.
15. Measure: a page of 8,190 sub-pages published, tuned, stepped and changed, with bytes on the wire per action, before and after.

**The browser:**
16. Re-pin; `interface_core` depends on `neoteletext-core` with no features and names `limits`; `MAX_SUBPAGES` and `ANY_SUBCODE` withdrawn.
17. The protocol's sub-page counts and places become 16-bit (`FromDecoder::SubPages`, `SubPageTitles`, `ToInterface::SubPages`, `PageControls`), with round-trip and refusal tests at 8,190 and 8,191.
18. The decoder store as a cache of sub-pages (section 2), the fetcher asking for `NNN-SSSS.t42` and `NNN.sub` on static channels.
19. The trusted core tunes sub-pages (the shown one and its neighbours within the budget), with the rate limit of `SERVER.md` section 20 item 2.
20. The sub-page list from the catalogue, titles by range, as a virtual list; the page controls' place and count to 8,190.
21. The security analysis amended (section 5); requirement 22.5 amended; the hostile harness given a channel that publishes 8,190 sub-pages on every page.
22. Measure: memory and bytes with that channel open, before and after.

**Both kits' channels:**
23. The Hackaday channel uses the new limit where a page needs it (a day's headlines, a long thread) and publishes changed sub-pages only.
