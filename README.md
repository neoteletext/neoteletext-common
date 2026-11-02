# neoteletext-common

What the neoteletext repositories share:

- [`DEVELOPMENT.md`](DEVELOPMENT.md): the development process of `neoteletext-engine` and `neoteletext-browser`.
- [`PROTOCOL.html`](PROTOCOL.html): the protocol document, the one definition of NeoTeletext's protocol, generated from rdm's documentation items.
- [`gates.md`](gates.md) and `gates/`: the gates every repository shares.
- [`guides/`](guides): teaching, which points to the protocol document for the rules.

Each repository's own `CLAUDE.md` says what is particular to it and points here for the rest.

## The protocol document

`PROTOCOL.html` is generated: nobody edits it. Its items have anchors, and `DOC-n` anywhere in these repositories names the item at `PROTOCOL.html#DOC-n`. To change the protocol's text, revise the item in rdm, and then make the byte examples from the engine and generate the document again, naming today's date:

```sh
cd ~/devel/neoteletext-engine && cargo xtask spec-examples "$TMPDIR/spec-examples.json"
cd ~/devel/neoteletext-common && rdm spec -examples "$TMPDIR/spec-examples.json" -o PROTOCOL.html -version "$(date +%F)"
```

`rdm spec -check` with the same `-examples` lists the document's faults, which do not stop generation.
