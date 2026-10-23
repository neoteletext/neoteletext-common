# The structure plan: how the code of both repositories is to be organised

| | |
|---|---|
| **Asked** | By the owner on 23 October 2026: a full analysis of the structure of the files and code of `neoteletext-engine` and `neoteletext-browser`, as an expert Rust developer would make it, and a plan in several documents for how the code and files should be organised, with the source broken into as many smaller files as makes sense. Not to be implemented yet. |
| **State** | Plan. Nothing here has been carried out. Each document says what it rests on; the readings behind them are of the code at engine `fb2dd8a` and browser `494aa91`. |
| **Where** | Here, in the shared repository, because the plan spans both repositories and `DEVELOPMENT.md` is where the shared process lives. Each repository's own document on where code lives (`ARCHITECTURE.md`, `docs/architecture.md` section 14) is updated when a part of the plan is carried out, not before. |

## The documents

| Document | What it holds |
|---|---|
| [`00-conventions.md`](00-conventions.md) | The rules every move follows: file size, one concept per file, directory layout, where tests go, where `cfg` goes, naming, visibility, the order of items in a file, and what a move commit is. Read first. |
| [`01-method-and-order.md`](01-method-and-order.md) | How the analysis was done, what counts as a finding, the order the work is carried out in across the two repositories, the gates each step passes, and the risks shared by every step. |
| [`10-engine-core.md`](10-engine-core.md) | `neoteletext-core`: findings and the target layout, file by file. |
| [`11-engine-formats-slicer-image.md`](11-engine-formats-slicer-image.md) | `neoteletext-formats`, `neoteletext-slicer`, `neoteletext-image`. |
| [`12-engine-web.md`](12-engine-web.md) | `neoteletext-web`. |
| [`13-engine-app-cli-audio-input.md`](13-engine-app-cli-audio-input.md) | `neoteletext-app`, `neoteletext-cli`, `neoteletext-audio`, `neoteletext-audio-mix`, `neoteletext-input`, `neoteletext-qrkeyboard`, `xtask`, the fuzz targets, the firmware test image. |
| [`20-browser-core.md`](20-browser-core.md) | The browser's trusted core (`native/core`). |
| [`21-browser-interface-core.md`](21-browser-interface-core.md) | The interface core (`native/interface-core`). |
| [`22-browser-protocol-and-processes.md`](22-browser-protocol-and-processes.md) | `protocol`, `decoder`, `fetcher`, `interface`, `draw-vello`, `draw-embedded`, `dock-menu`, `keyboard`, `sound`. |
| [`23-browser-sandbox-and-install.md`](23-browser-sandbox-and-install.md) | `confine`, `launcher`, `update`, `tuf`, `installer`, `os-install`, `release-identity`, `web-opener`, `site`, `stub`, the fuzz targets. |
| [`30-cross-cutting.md`](30-cross-cutting.md) | What the readings found in both repositories at once: the shapes that repeat, the inconsistencies between siblings, and the shared patterns a reorganisation should make the same everywhere. |

## How to read a per-crate document

Each per-crate document has the same five parts, so the whole can be checked against the conventions in one pass:

1. **The crate as it is**: its purpose, features, module tree with line counts.
2. **Findings**: file by file, what each holds and which responsibilities it mixes; functions and `impl` blocks that have grown past the limits in `00-conventions.md`; duplicated shapes; inconsistencies.
3. **The target layout**: the module tree after the work, every file named by its concept, with its intended contents and approximate size.
4. **The moves**: the ordered steps that get from 1 to 3, each a commit that compiles and passes the gate, with the visibility changes and `mod` declarations each needs.
5. **Risks particular to the crate.**

## What the plan does not do

- It adds no crate, no dependency and no feature, and changes no behaviour, protocol byte, file format or public path without saying so in the document and in the commit that does it.
- It does not rename for its own sake. A rename appears only where a name misleads or where siblings disagree.
- It is not a review of correctness. What a reading noticed in passing is listed in `30-cross-cutting.md` under "Seen, not part of this plan", for the owner to take up separately.
