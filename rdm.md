# Working with rdm

Every neoteletext repository records its requirements, decisions, checklists and to-dos in rdm, through its MCP tools (`DEVELOPMENT.md` sections 1, 3, 4 and 5). Two rules hold for every record and every interaction with rdm, on the owner's instructions of 30 October 2026.

## 1. Every record is fully detailed

The owner: "ensure todos and REQUIREMENTS are DETAILED NEVER ABBREVIATED NEVER TOO CONCISE, must FULLY EXPLAIN WHAT NEEDS TO BE DONE".

A record is read later by someone, or by a session, that never saw the conversation it came from, so it must stand alone:

- **Full narrative sentences**, with every term spelled out the first time it is used. No terse fragments, no abbreviations, no "as above", no "see the chat".
- **A requirement** states the behaviour in full (what must happen, in which part, under which conditions, with every bound named and its source cited), why it is required (the owner's words where they are the reason), where it comes from (the decision that made it), how it will be verified (each test, and that it must fail on the code before), and its state (what exists today, naming the files, and what does not).
- **A to-do** names the decision and requirements it serves; says what exists today and where (files, functions, behaviour); explains each step to be done in sentences, with the file or component it changes and why; gives the order and what it depends on or blocks; says how the work will be checked; and says what "done" means.
- **A decision** says who decided and when, what was chosen in numbered items, why, the alternatives considered, and what it withdraws or changes.
- **A revision** is a complete new version, never a patch that only makes sense beside the old one, with its reason.

## 2. rdm is a graph: every interaction puts the relevant links in place

The owner: "always treat every interaction with RDM as a GRAPH database, be careful to put in place RELEVANT LINKS with EVERY interaction".

A record is only as useful as the records it is linked to. With every create, revision or change of status:

- **Search first** for the records the new one concerns, in this repository and in every other neoteletext repository (`search` with `repository: "all"`), and link them.
- **Use the right kind of link:**
  - `decides`: from a decision to each requirement it makes or amends;
  - `depends_on`: from a record to what must exist or be done first, such as a to-do to the to-do that blocks it, or a requirement to the decision or requirement it relies on;
  - `supersedes`: from the new record to the one it replaces, with the old one's status set to superseded naming the new one;
  - `related`: for everything else that a reader of one should know about the other.
- **Every to-do links** to the decision and the requirements it implements, and to the to-dos that must come before it (`depends_on`).
- **Every requirement** is linked from the decision that made it (`decides`), and to the requirements it builds on or constrains.
- **Every decision links** to the decisions it amends, supersedes or relies on, and decides its requirements.
- **A revision checks the links:** what the new version cites must be linked, and links the change makes wrong must be removed or replaced.
- **Across repositories:** a record that concerns another repository's record is linked to it, whichever repository each is in.
- **Report the links** with the receipt: which records were linked, and how.
