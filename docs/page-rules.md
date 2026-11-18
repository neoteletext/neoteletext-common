# The page rule table: binding events to groups of protocol commands in the browser

| | |
|---|---|
| **Status** | The **second form**, specified on 18 November 2026 while the owner was away, for building at once. It replaces the first form of the same day (this document at neoteletext-common commit `85904b0`), which was built and audited and never deployed, so nothing here keeps compatibility with it. The owner's decisions are DEC-6522 (the rule table), REQ-6523 (no input unless asked), DEC-6580 (a key's sound commands run at once), DEC-6587 (the second form), DEC-6599 (a sub-page is a page) and DEC-6635 (events act at once in arrival order, only what time drives runs on the tick, and three mechanisms fewer; revised in place on 18 November 2026, section 18.1). What this document decides beyond them is listed in section 15 and recorded in rdm as DEC-6525 (the first form's choices that survive), DEC-6610 (the second form's) and DEC-6636 (the readings DEC-6635 needed), all waiting for the owner's confirmation. Section 16 lists the rdm requirements that carry this document, section 17 is the record of what the first build changed and, in sections 17.3 and 17.4, of what the second build read and where it falls short, and section 18 lists every change of the second form against the first, with section 18.1 for what DEC-6635 changed and section 18.2 for what the second build changed in this text. |
| **Asked for by** | The owner, 18 November 2026: "I ALSO WANT YOU TO FULL SPECIFY AND DOCUMENT OUR META LANGUAGE, IMPLEMENT IT IN CODE"; then, of the twelve ideas for triggering: "i like them all. implement all. ensure rdm updated. also make it so the ONLY thing that can be triggered is a group of protcol commands. i agree with constraining the number of commands in a group but not work cap. propose cap. why enable and disable rules? after a disconnect i think EVERYTHING should be dropped and the page reloads what do you think? local variables may only store a 32 bit signed integer not anything else. local variables must have hard coded names/designators, a fixed number of them with operations like inc dec and others that you think right."; and: "in neoteletext a sub-page has NO relattionship to its parent page - we treat sub pages EXACTLY as pages." |
| **Process** | DEVELOPMENT.md section 2.3 (a proposal with its own security analysis, section 12 of this document), section 3.5 (every record in full) and section 14 (security). |
| **Companion** | `animation.md` (requirements ANIM-n) defines the objects, records and renderer behaviour that the `ANIMATE`, `SPRITES` and `NAPLPS_OBJECTS` commands and the collision conditions act on. |
| **Repositories it changes** | neoteletext-renderer-teletext (the engine, with the crate `neoteletext-rules`), neoteletext-browser, neoteletext-app-server, neoteletext-server-ts-protocol (the TypeScript kit), neoteletext-server-channels (the Python kit), neoteletext-server-ts-ui-components (the component library), every channel, and neoteletext-server-channel-musicplayer. The ReGIS and NAPLPS renderers are not changed by the second form. |

Requirements are numbered `RULE-n`. Numbers are permanent: a requirement whose meaning survives keeps its number and is revised in place; one that the second form removes is kept as a line beginning "Withdrawn:" with the reason; new requirements take numbers from RULE-118. Each names in brackets the repository that implements it. "MUST", "SHOULD" and "MAY" are used as DEVELOPMENT.md section 4 defines them. Every integer on a wire is big-endian unless a field says otherwise. "The receiver" is any program that shows a page to a viewer; the NeoTeletext browser is the receiver this document specifies in full.

**A page, in this document, is one page number and one sub-code together** (DEC-6599, RULE-112). Wherever this document says "page" without qualification it means that one identity; a sub-page is a page, and nothing here is addressed by a page number alone.

---

## 1. Purpose, model and vocabulary

### 1.1 Purpose

A page may carry a **rule table**: a bounded, declarative list of rules, each binding an event (a key, a pointer action on a target, a timer, the page opening, a condition becoming true, a cue point in a playing sound) to **one group of protocol commands**, which the receiver holds and applies itself. A command is an ordinary record of the push protocol, the same bytes the server sends a receiver to start a sound, play a note on a local sound, show, hide, move or re-look an object, place sprites, change a variable, start a timer or report to the channel. The receiver handles each event the moment it arrives, applying at once every command of the groups it runs, and runs what time drives (timers, sequences, conditions becoming true, frame cycling) on a clock of sixty ticks a second. It gives a page sound and graphics that answer the viewer with no round trip to the server, and it is the only way a page can ask for the viewer's input to be sent to its channel (REQ-6523).

The table is not a program. It has no loops, no jumps, no multiplication or division, no computed addresses, and no command can cause a rule to fire while it is being applied. Its only arithmetic is the saturating addition and subtraction of 32-bit integers in the variable commands and in a command's value (RULE-99, RULE-106). REQ-417 (the engine's REQ-SEC-004) allows it as the one exception to "no executable content", inside the bounds of section 9 and no further.

### 1.2 Terms

| Term | Meaning |
|---|---|
| **Page** | One page number (`0x100` to `0x8FF`) and one sub-code (`0x0000` to `0x3F7E`) together: one identity (RULE-112). |
| **Tick** | One sixtieth of a second on the receiver's presentation clock (ANIM-1). |
| **Page tick** | The number of the last tick step run for the page since it was opened in this view, counted from 0. An event belongs to the page tick current when it is handled (RULE-5). |
| **Event** | Something that reaches the evaluator from outside the table and is handled at once: an input event of the viewer's, a command the server sent directly for the page, or a cue heard (RULE-5, RULE-96). |
| **Handling** | What the evaluator does with one event, or with one tick step: decide which rules fire against the state as it stands, then apply every command of their groups, in order, at once (RULE-5). |
| **Tick step** | The handling of what time drives, once a tick: `open` at page tick 0, timers, sequences, `becomes` and frame cycling (RULE-5). |
| **Rule table** | The one table a page has (RULE-2): rectangles, binding rows, rules, groups and sequences. |
| **Rule** | One or more triggers, an optional condition, optionally a set of binding rows, and the number of one group to run (RULE-3). |
| **Trigger** | An event that can make a rule fire (section 3). |
| **Condition** | An expression of integer comparisons that must hold for the rule to fire (section 4). |
| **Command** | One record of the push protocol that a receiver applies (section 5): `CONTROL`, `LOCAL_MIDI`, `ANIMATE`, `SPRITES`, `NAPLPS_OBJECTS`, `VARIABLE`, `TIMER`, `REPORT`, `RUN` or `SEQUENCE`. The server may send any of them directly; a group holds them for later. |
| **Group** | A numbered, stored list of commands of a page's table (RULE-118). The only thing a rule can trigger. |
| **Run** | Applying a group's commands in written order. A run's size, with every group it runs, is limited (RULE-120). |
| **Fire** | A rule fires when one of its triggers occurs and its condition holds; its group is then run. |
| **Binding row** | One constant integer, `p`, of a table's row list. A rule that names rows is a template: it is matched once for each of its rows, with that row's `p` standing in its triggers' target numbers, its condition's constants and its group's commands, and the row's place choosing its key in a key set given one key a row (RULE-105). |
| **Amount** | A constant, or a constant plus one source (a variable, the row's `p` or a value of the firing), added with saturation and held to the valid range of the field it fills (RULE-106). |
| **Target** | Something on the page that a pointer trigger, an animation operation or a collision test names: the page's picture, a teletext control, an animation object, or a rectangle (RULE-12). |
| **Animation object** | A numbered thing a renderer keeps and can move, show, hide, order and cycle: a teletext sprite (ANIM-7), a ReGIS numbered drawing (ANIM-9) or a NAPLPS object (ANIM-11). |
| **Variable** | One of the fixed set of signed 32-bit integers every page has, designated `v0` to `v15`, zero at opening, never declared (RULE-14). |
| **Timer** | One of the fixed set of tick counters every page has, `t0` to `t7`, stopped at opening, and the page timer that runs from opening (RULE-15). |
| **Sequence** | One of a table's stored lists of steps, each step a tick offset and a group, played by the receiver on its own clock, a stated number of times or until stopped; it may be started to begin at the next tick, at a given page tick, or at a timer's next expiry of a period (RULE-103). |
| **Armed run** | Withdrawn (DEC-6635 item 6): a run for a given tick is a one-step sequence started at that tick (RULE-103). |
| **Cue** | A numbered point in a playing sound's event list, which fires `cue` triggers when it is heard (RULE-109). |
| **Mode** | A value of one variable that rules test in their conditions; the way a page switches sets of rules on and off (RULE-110). |
| **Value** | Something a condition, a `REPORT` or a `set` reads: a variable, a key's state, a timer, a target's state, a sound's level, a synthesizer's state, a sequence's state, a value of the firing (section 6). |
| **Open page** | The one page of the active tab that keys would go to (the browser's REQ-1378). Only the open page's table is evaluated (RULE-58). |
| **Snapshot** | Withdrawn (DEC-6635 item 1): there is one state, which every condition and every command reads as it stands (RULE-7). |
| **Local sound** | A synthesizer sound with no blocks from the server, rendered by the receiver's sound helper and played by `LOCAL_MIDI` commands (RULE-60). |
| **Sound command** | A `CONTROL` or a `LOCAL_MIDI` command. Like every command, it is applied the moment its group runs, and leaves for the sound helper at once (RULE-96). |
| **Audio channel** | One of the four voices of the audio profile, 0 to 3 (the engine's REQ-AUD-010). It is not a MIDI channel. |
| **Part** | A MIDI channel, 1 to 16, of one synthesizer sound (midi-architecture.md MIDI-3). |
| **Program** | A channel's application, which speaks the program protocol to the server. |

### 1.3 Requirements of the model

**RULE-1 [neoteletext-common]. A rule table is event binding, never executable content.**
- **Statement.** A rule table MUST be only what sections 2 to 6 define: rectangles, binding rows, rules (triggers, at most one condition, one group number), groups of commands and sequences of steps. No requirement may add to it a loop, a jump, a conditional inside a group, a command that makes a rule fire while it is being applied (RULE-6), multiplication, division, a bit operation, a random number, a computed address (a variable used to choose a target, a sound, a handle, an audio channel, a group, a timer, a sequence or another variable), a call of a routine, text processing, a command that defines or changes a table, a group, a sequence or a row (RULE-119), or any command that reaches the network other than `REPORT` and the answer to a state query (section 7.4), unless REQ-417 is first changed by the owner's recorded decision. The arithmetic allowed is exactly: comparison of a value with a constant; saturating addition and subtraction of signed 32-bit integers in the `VARIABLE` command (RULE-99) and in an amount (RULE-106); and holding a result to a constant range. The receiver's own timekeeping is not an operation of the table: to find when an `every` trigger is due, a timer's phase (RULE-25) and a sequence's `beat` start (RULE-103), the receiver takes the remainder of its own count of elapsed ticks by a period that is a constant of the table or of the record, checked to be 1 to `MAX_TIMER_TICKS`; no command, operand or condition multiplies, divides or takes a remainder, and no variable can be a period (DEC-6648 item 7; REQ-417).
- **Reason and source.** The owner's ruling of 18 November 2026: "this is not executable logic it is event binding to local actions with simple evaluatios" (DEC-6522 item 1); DEC-6587 items 1, 5 and 9; the lessons of MHEG-5 recorded in DEC-6522 items 13 and 14.
- **Verification.** Inspection of the crate `neoteletext-rules` against this list at each change; the fuzz targets of RULE-83.

**RULE-2 [neoteletext-common]. One table for a page; a sub-page is a page.**
- **Statement.** A page (RULE-112: a page number and a sub-code) MUST have at most one rule table in a view at a time. It belongs to that page alone: it is not shared with, inherited by or visible to any other sub-code of the same page number. A table is replaced whole by a later table for the same page (RULE-41); replacing it drops the page's variables, timers, sequences, `becomes` memory and waiting events, as opening the page does, and fires the new table's `open` rules at its page tick 0. A page with no table evaluates nothing and sends no input (RULE-50).
- **Reason and source.** DEC-6599 (the owner: "we treat sub pages EXACTLY as pages"), which withdraws DEC-6522 item 5's "one table per page, applying to all its sub-pages".
- **Verification.** Tests in `neoteletext-rules` and the browser's decoder: a table for page `101/0001` is not evaluated while `101/0002` is open; going from one to the other closes one and opens the other with every variable zero; a replacement table resets state.

**RULE-3 [engine: neoteletext-rules]. The shape of a rule.**
- **Statement.** A rule MUST consist of: 1 to `MAX_TRIGGERS_PER_RULE` triggers (section 3; RULE-107); a condition (none or one, section 4; a rule with a `becomes` trigger has exactly that one trigger and MUST have a condition, which is the condition whose edge fires it); optionally a run of binding rows (RULE-105); and the number of one group of the same table. It has no action list, no `echo` flag and no enabled flag. A table holds 0 to `MAX_RULES` rules, numbered 0 to 63 in the order written, which is **rule order**.
- **Reason and source.** DEC-6587 item 1 ("A rule is a trigger (or several), an optional condition, and the number of one group to run. It has no action list of its own") and item 8 (the enabled flag withdrawn).
- **Verification.** Codec tests: each shape round-trips; one trigger and one rule over their limits, a group number the table does not have and a `becomes` rule without a condition are each refused whole (RULE-70).

## 2. The clock, the handlings and their order

**RULE-4 [engine: neoteletext-rules; neoteletext-browser]. Sixty ticks a second, counted from the page's opening.**
- **Statement.** The receiver MUST run an open page's tick step (RULE-5) once for each tick of its presentation clock (ANIM-1), 60 ticks a second: tick `n` of the clock is due `n × 50,000 ÷ 3` microseconds (rounded down) after the clock's start, so that the ticks never drift against real time. A page's first tick step is page tick 0, at the first clock tick after the page was opened in the view and its table decoded; each later clock tick is the next page tick. Events are handled between tick steps as they arrive (RULE-5) and are not tick steps. The page tick is a 32-bit unsigned number that stops at 4,294,967,295. When the receiver is late and more than one tick is due, it MUST run each due tick step in order, at most `MAX_CATCH_UP_TICKS` in one wake; when more than that are due, it MUST move the clock's start later by the ticks it will not run, so that page time slows and no page tick is ever skipped. While the page is open but its tab is not the active one, the page is **paused** (RULE-111): no tick step is run, no event is handled and the page tick does not advance; it goes on from the same page tick when the tab is active again.
- **Reason and source.** DEC-6522 item 3 (the owner: "this event system operates on 60 ticks a second"); DEC-6524 item 1. Slowing rather than skipping keeps a recording of inputs by page tick exactly replayable.
- **Verification.** Tests in `neoteletext-rules` with a scripted clock: 3,600 ticks are due in exactly 60 seconds; seven ticks overdue run six tick steps and move the start; the browser's decoder test holds that a paused page runs nothing and resumes at the next page tick.

**RULE-5 [engine: neoteletext-rules]. Handlings: an event is handled at once, and time is handled in the tick step.**
- **Statement.** The evaluator MUST do all its work in **handlings**, one at a time and never interleaved: the handling of one event, or the tick step of one page tick. "Run" means RULE-118's run of a rule's group, with nested groups run in place. Every handling has exactly two phases, in this order:
  1. **Decide.** The handling's firings are determined: each rule, in rule order, and within a rule each of its rows in row order, that the event or the tick step fires, with its condition evaluated against the page's state as it stands at the start of the handling (RULE-7). Nothing changes in this phase but the input state (RULE-8), a sequence's start falling due (step 3 below) and the `becomes` memory (RULE-11).
  2. **Apply.** The group of each firing is run, in the order the firings were decided, and each of its commands takes effect at once, as it is reached (RULE-96). No command applied in this phase changes which rules this handling fires (RULE-6).
- **An event**, for the evaluator, is one of: an input event of the viewer's for the open page; a record the server sent directly for the page that the evaluator carries out (`VARIABLE`, `TIMER`, `REPORT`, `RUN` and `SEQUENCE`, RULE-114, and `RULES_QUERY`, RULE-47); or a cue heard (RULE-109). The records the receiver applies itself whether or not the page has a table (`CONTROL`, `LOCAL_MIDI`, `ANIMATE`, `SPRITES`, `NAPLPS_OBJECTS`) are not events: they are applied on arrival, between handlings, as changes to the world (RULE-7). **Handling an event**:
  1. **Its tick.** An event belongs to the page tick current when it is handled: the tick of the last tick step run. An event that reaches the evaluator before the page's tick step 0 has been run waits, and is handled at once after that step, belonging to page tick 0.
  2. **At once, in arrival order.** The evaluator handles each event as soon as it reaches it, with nothing waiting for a tick, while the budget of the current tick allows. The budget of tick `n` counts the events handled in tick `n` and, of those, the commands their runs apply and the `REPORT` commands among them: an event is handled in tick `n` only when fewer than `MAX_EVENTS_PER_TICK` events have been handled in it, and only when, with the commands of its own firings (each run's count is a constant of the table, RULE-120), the tick's commands stay within `MAX_EVENT_COMMANDS_PER_TICK` and its `REPORT` commands within `MAX_EVENT_REPORTS_PER_TICK`. The first event handled in a tick is always handled, whatever its counts. When an event does not fit, nothing of its decide phase is kept (the change it made to the input state, RULE-8, is put back as it was, and it is decided again from the beginning when it is handled; DEC-6648 item 2), and it and every event that arrives after it while any waits are queued in arrival order, at most `MAX_QUEUED_EVENTS`; an event that arrives at a full queue is dropped and counted (fault 4, RULE-48). Waiting events are handled, in order, at once after the next tick step, belonging to that tick and under its budget. An event is never dropped while the queue has room.
  3. **Decide.** For an input event: update the input state (RULE-8), then match every rule's input triggers against the event. For a cue: match every rule's `cue` triggers. For a record of the server's: there is nothing to match; its one firing is the record itself, applied as a command (a `RUN` runs its group in place). For a state query: there is nothing to match, and it is answered at once from the state as it stands (RULE-47).
  4. **Apply**, as above.
- **Firings a handling keeps.** An event's decide phase keeps at most `MAX_RULE_ROWS` firings, and a tick step's at most `MAX_RULE_ROWS` plus `MAX_SEQUENCES × MAX_SEQUENCE_STEPS`, in fixed arrays sized by those constants. The table's checks already hold the rule-and-row pairs to `MAX_RULE_ROWS`, so only a trigger on "any" control or object in a rule that names rows, which fires once a row for every target under the pointer, can reach the bound; a firing beyond it is dropped and counted (`firings_dropped`, RULE-72; DEC-6648 item 4).
- **The tick step** of page tick `t` (RULE-4) is one handling. Its decide phase determines the firings in exactly this order:
  1. **`open`**, at page tick 0 only: each rule with an `open` trigger whose condition holds.
  2. **Timers**, in identifier order, the page timer first and then `t0` to `t7`: for each timer running, each rule whose `every` or `after` trigger on that timer is due at `t` (RULE-15) and whose condition holds.
  3. **Sequences**, in number order 0 to 7: a sequence waiting to start whose start tick is `t` becomes running at position 0 and pass 0 (RULE-103); then, for each sequence running, each of its steps whose offset equals its position, in step order. A step has no condition.
  4. **`becomes`**: each `becomes` rule, and each of its rows, whose condition holds now and did not hold at its previous check (RULE-11).
- A rule, or one row of it, fires at most once in a tick step, at the first of these places at which it is due, however many of its triggers are due there. The apply phase then runs the decided groups in that order, and after the last of them: 5. **each sequence** that was running when the tick step began, and that no command of this tick step stopped or started again, advances (RULE-103); 6. **frame cycling**: each cycling object whose frame is due at `t` advances (ANIM-14). The waiting events, if any, are then handled (item 2 above).
- **Outputs.** Every output of a handling leaves at once, in the order its command was applied: a sound command to the sound helper, a report to the trusted core (RULE-52), the answer to a state query. A change to the picture is drawn at the next display frame from the state then current (RULE-65), so that several changes before one frame cost one repaint.
- **`close`.** When the page is closed while its connection stands (RULE-111), the evaluator handles the lost releases of RULE-8 as events, whatever the budget, then runs one `close` handling, whose firings are the `close` rules, in rule order, whose condition holds; events still waiting are dropped and counted. No `close` handling is run on a disconnect.
- **Reason and source.** DEC-6635 items 1 to 5 (the owner, 18 November 2026, asking why events wait for the tick instead of "everything happens instantly, maximum once in 1/60 second", and then: "yes record it and do all three simplifications too"), which replace the twelve-step tick of DEC-6610 item 31; DEC-6522 item 13: the order is part of the specification, so no second order ever has to be allowed. `open` is first, alone in tick step 0, and events wait for it, so that a page's opening group has set its variables before any other group reads them (section 15, item 31). The budgets, how an event is counted against them, and their figures are this document's readings of DEC-6635 item 4 (section 15, items 45 and 46).
- **Verification.** A test of `neoteletext-rules` with one table that has a rule of every trigger kind, a sequence and a server command, each writing its own number to a log by `REPORT`: each event's reports are made before `handle` returns, in arrival order; a tick step's reports are in the order `open`, timers, sequences, `becomes`. Budget tests: the event after `MAX_EVENTS_PER_TICK` in one tick waits and is handled, stamped with the next tick, at once after the next tick step; an event whose runs would pass `MAX_EVENT_COMMANDS_PER_TICK` or `MAX_EVENT_REPORTS_PER_TICK` waits, and so does every later event; the first event of a tick is handled whatever its counts; an event at a full queue is dropped and counted. Property test: the same table and the same recorded events give the same outputs on every run.

**RULE-6 [engine: neoteletext-rules]. No cascade within one handling.**
- **Statement.** No command MUST cause a rule to fire while it is being applied, and nothing a command of a handling does MUST change which rules that handling fires: every firing of a handling is decided before any of its commands is applied (RULE-5). What a command changes — a variable, a target shown, hidden, moved or given a frame, a timer started or stopped, a sequence started or stopped, a sound started or stopped — is seen by the conditions of later handlings: of the next event, and of the next tick step. A `becomes` rule on a variable that a group changed therefore fires at the next tick step's check at the earliest, never within the handling that changed it, and a second rule of the same event that tests the variable is decided on its value before the event. A timer or a sequence started by a command runs from the first tick step after the handling in which the command was applied (RULE-15, RULE-103). Within one handling, a later command reads what an earlier command wrote (RULE-7). A `RUN` command that runs another group now is not a cascade: it is part of the same run, within RULE-120's limits. There is no limit on the commands a tick step applies beyond the table's own limits (RULE-57, RULE-120); the budgets of RULE-5 apply to events, which wait rather than being dropped. The first form's `MAX_ACTIONS_PER_TICK` stays withdrawn (DEC-6587 item 2).
- **Reason and source.** DEC-6522 item 14; DEC-6635 item 3; DEC-6587 item 2 (the owner: "not work cap").
- **Verification.** Tests: a key's group sets `v0`, and a `becomes` rule on `v0` fires at the next tick step, never within the key's handling; one key fires two rules, the first's group setting `v0` and the second's condition testing it, and the second is decided on the old value; a second key of the same tick is decided on the new value; a sequence started by a key runs its offset 0 step at the next tick step; a group that stops its own sequence still completes.

**RULE-7 [engine: neoteletext-rules]. One state, read as it stands.**
- **Statement.** The evaluator MUST keep one copy of the page's rule state and change it in place as each command is applied. Every condition reads the state as it stands at the start of its handling's decide phase; every command reads it as it stands when that command is applied, so that `inc v0` followed by a command whose amount names `v0` uses the new value, and a `REPORT` of a variable reports what its own group has just written. There is no snapshot, no working copy and no arrival copy: the second form's snapshot taken at the first arrival, its arrival copy of the variables and its exception for metered values are withdrawn (DEC-6635 item 1). The rule state is: the variables; each timer's running flag and start tick; each sequence's state (stopped; waiting, with its start tick; or running, with its position and passes) and its held row parameter; each `becomes` rule's previous result for each of its rows; the input state (RULE-8); and each named target's local animation state (ANIM-6).
- **The world.** What the evaluator reads but does not own — a target's state and bounding rectangle, the sound on each audio channel (RULE-27), the tracked synthesizer values (RULE-28 to RULE-30) and the newest metered report (RULE-33) — is read as it stands when it is read. A change to it that no handling makes (a record of the server's that the receiver applies itself, a newer metered report, a stream's own change to an object) MUST take effect between handlings, never within one: the receiver applies it before or after a handling, in the order it arrived among the events.
- **Time.** In a handling the present tick is the page tick it belongs to (RULE-5); a timer's elapsed ticks and phase are counted to it.
- **For a recording.** The inputs of a page are its events, the records the server sends it, its metered reports and the other changes made to its world. A recording that stores each with the page tick it was handled or applied in and its place among that tick's inputs, and is replayed in that order with the tick steps at the tick boundaries, gives the same result on every run. Wall-clock time within a tick affects no outcome. Because an event given before tick step 0 and one given after it both belong to page tick 0 (RULE-5), the engine keys each input of a recording by the count of tick steps run when it was given (`counters().ticks`), which places every input exactly among the tick steps; the fuzz target `rules_budget` and `neottx rules-run` replay by it (DEC-6648 item 3).
- **Reason and source.** DEC-6635 items 1 and 5 ("There is one state, not a snapshot and a copy"); DEC-6587 item 7 (counters that are changed and then used).
- **Verification.** Tests: `set v0 5` then `add v0 1` in one group leave 6; a `LOCAL_MIDI` after `inc v0` whose key is `60 + v0` plays the new key; within one event, a rule's condition reads the value before the event's groups ran; a second key of the same tick reads the first key's write; a metered report applied between two keys is read by the second key's rules and by the next tick step's `becomes` check; a recorded run replayed gives the same outputs.

**RULE-8 [engine: neoteletext-rules]. Input state follows the events.**
- **Statement.** The **input state** — which keys are down, which pointer buttons are down, where the pointer is and which targets it is inside — MUST be updated event by event, in the decide phase of each input event's handling and before its rules are matched (RULE-5), so that a condition on a key's state sees the keys as they are just after the triggering event, and a tick step sees them as the events handled so far left them. Input state is not something a command can change, so RULE-6 is not broken. The evaluator tracks at most `MAX_KEYS_DOWN` keys down at once; a press beyond that is treated as not down for conditions (its `key` trigger still fires). When the page loses the keyboard, the pointer leaves, the page is paused or the page closes, the receiver MUST give the evaluator a release (marked lost, as the input protocol's L flag, DOC-1935) for every key and button still down and a leave for every target the pointer was inside, each handled at once as an event whatever the budget, after the events already waiting, so that the order of arrival holds, `key_up`, `release` and `leave` rules fire and no note is left sounding. The evaluator takes such a release as an event of its own kind (`Event::Lost`), which the budgets never hold back; an ordinary release is budgeted like any other event (DEC-6648 item 1).
- **Reason and source.** A chord (a rule on key A when Shift is down) must work when both arrive within one tick; a held note must end when focus is lost (the engine's REQ-207).
- **Verification.** Tests: Shift and then A within one tick fire the rule on A-with-Shift; a blur with two keys down fires both `key_up` rules in order of key arrival.

**RULE-96 [engine: neoteletext-rules; neoteletext-browser]. The one path: every event is handled at once, and every command takes effect as it is applied.**
- **Statement.** When an event (RULE-5) reaches the evaluator for the open page, the evaluator MUST handle it at once, without waiting for the tick, unless the current tick's budget is spent (RULE-5). Every command of every handling, an event's or a tick step's, takes effect the moment it is applied, with its amounts resolved against the state as it then stands (RULE-106):
  1. a **sound command** (`CONTROL`, `LOCAL_MIDI`) is handed to the world, which sends it toward the sound helper before the handling ends;
  2. `VARIABLE`, `TIMER` and `SEQUENCE` change the rule state;
  3. `REPORT` hands a report to the world, which in the browser gives it to the trusted core at once (RULE-52);
  4. `ANIMATE`, `SPRITES` and `NAPLPS_OBJECTS` change the page's animation state through the world at once, and the picture is drawn at the next display frame (RULE-65);
  5. `RUN` runs its group in place.
- There is one path for every command: no command is marked by kind when the table is decoded, and none waits for a tick. The second form's split — sound commands of an input's groups delivered on arrival, everything else at the tick — is withdrawn with the arrival copy of the variables, the snapshot taken at the first arrival and the exception for metered values (DEC-6635 item 1, which supersedes DEC-6580 item 1's split and keeps its aim).
- **The evaluator's interface.** `neoteletext-rules`' evaluator MUST offer exactly these entry points: `Evaluator::handle(event, world)`, which handles one event at once or queues it under the budget; `Evaluator::tick(world)`, which runs the next tick step and then the waiting events that fit; and `Evaluator::close(world)`, which runs the `close` handling of RULE-5. An event is an input event, a record of the server's (its type and body), a cue (audio channel and number) or a state query. The caller applies the changes to the world between calls. The second form's `Evaluator::push` and `Evaluator::push_now` are withdrawn, and with them the record of firings decided on arrival.
- **In the browser** the decoder MUST call `handle` for each event of the open page as soon as it has read it from its pipe — an input event from the trusted core, a record from the fetcher, a cue heard from the trusted core — before any other work that is waiting (a record to decode, a repaint, a tick that is not yet due); MUST write every sound message its world is given during that call to the trusted core, and flush it, before it returns to that other work; MUST give each report to the trusted core at once; and marks the damage of each picture change, which it paints at the next paint point (RULE-65). It reads its pipes by waiting on them, never by looking at intervals (the browser's decision 46). Its record of what plays on each audio channel (RULE-27) changes as each sound command is applied. A tick that falls due while an event is being handled runs after it. `neottx rules-run` uses the same interface; its `--on-arrival` option is withdrawn. It reads a table written as the program protocol's `rules` message in JSON, as a page's author writes it, making names into numbers and `do` and `echo` into groups as the server does, and checks the image whole before it evaluates it; it refuses a group that holds `sprites` or `naplps_objects`, having no renderer to place them (DEC-6647, DEC-6648 item 10).
- **Reason and source.** DEC-6635 items 1, 2 and 5: one path instead of two and one state instead of a snapshot and a copy, with no loss of speed: sound leaves at once as before, and nothing visible can appear sooner than the next display frame. DEC-6580 item 1 (the owner: "yes record 1 to 3 and build them") is the aim kept: a key's sound leaves on its arrival.
- **Verification.** Tests in `neoteletext-rules`: a key's `LOCAL_MIDI` and its `ANIMATE` both reach the world before `handle` returns; a group `inc v0`, `LOCAL_MIDI 60 + v0` delivers key 61 and leaves `v0` at 1 before `handle` returns; two keys of one tick read each other's writes in arrival order; a `REPORT` of a key's group is given to the world before `handle` returns; a replay of the recorded events gives the same outputs. The browser's timed test (RULE-66).

## 3. Triggers

**RULE-9 [engine: neoteletext-rules]. The trigger kinds.**
- **Statement.** A trigger MUST be exactly one of the kinds below. The code is its byte in the table (RULE-43).

| Code | Name | Fires when | Fields |
|---|---|---|---|
| 1 | `key` | a key matching the key set is pressed; with `repeat` set, also on each automatic repeat | key set (RULE-10), `repeat`, `by_row`, modifier mask and value |
| 2 | `key_up` | a key matching the key set is released (or lost, RULE-8) | key set, `by_row`, modifier mask and value |
| 3 | `press` | a pointer button or a touch contact goes down inside the target | target, button |
| 4 | `release` | a button or contact that went down inside the target comes up, wherever the pointer then is | target, button |
| 5 | `enter` | the pointer comes inside the target | target |
| 6 | `leave` | the pointer goes outside the target, or leaves the page (RULE-8) | target |
| 7 | `open` | page tick 0's tick step (RULE-5) | none |
| 8 | `close` | the page is closed while its connection stands (RULE-5, RULE-111) | none |
| 9 | `becomes` | at a tick step, the rule's condition holds and did not at its previous check (RULE-11) | none: the condition is the rule's |
| 10 | `every` | each `ticks` ticks after the timer started, while it runs | timer, `ticks` |
| 11 | `after` | once, `ticks` ticks after the timer started | timer, `ticks` |
| 12 | `text` | text arrives that is not a key: a paste, an input method's composition or its committed text | none |
| 13 | `move` | the pointer moves to another pixel inside the target; with `held` set, only while a button is down | target, `held` |
| 14 | `wheel` | the wheel turns with the pointer inside the target | target |
| 15 | `focus` | the page gains the keyboard | none |
| 16 | `blur` | the page loses the keyboard | none |
| 17 to 20 | — | Withdrawn: `held`, `double`, `press_held` and `double_press` (DEC-6635 item 7). A long press or a double press is two or three rules with a timer and a variable (section 7.5, example 8; RULE-93's `panic` rules). The codes are refused and never reused | — |
| 21 | `cue` | a cue of the sound playing on an audio channel is heard (RULE-109) | audio channel, cue number or any |

- Kinds 1 to 11 are DEC-6522 item 5's; 12 to 16 were added by the first form so that every kind of input REQ-6523 names has a trigger; 21 is DEC-6587 item 5's idea 4. The triggers of kinds 1 to 6 and 12 to 16 are **input triggers**, fired in an input event's handling; 21 is fired in a cue's handling; 7, 9, 10 and 11 are fired in the tick step, and 8 in the `close` handling (RULE-5).
- A button is 0 (left, or a touch contact, or a pen touching), 1 (middle), 2 (right) or 255 (any). The modifier mask and value are the input protocol's modifier bits (DOC-1935: Shift 1, Alt 2, Control 4, Super 8, Hyper 16, Meta 32, Caps Lock 64, Num Lock 128): the trigger matches when `(mods AND mask) = value`; mask 0 ignores modifiers. A key or click made with the browser's own modifier never reaches the evaluator (RULE-51).
- `ticks` of `every` and `after` is 1 to `MAX_TIMER_TICKS`.
- **Reason and source.** DEC-6522 item 5; REQ-6523; DEC-6587 item 5; DEC-6635 item 7.
- **Verification.** One test for each kind in `neoteletext-rules`: the event that fires it, and the nearest events that must not; a trigger of kind 17, 18, 19 or 20 refuses the table.

**RULE-107 [engine: neoteletext-rules]. Several triggers on one rule: any of them fires it.**
- **Statement.** A rule MAY hold up to `MAX_TRIGGERS_PER_RULE` triggers, none of them `becomes`. The rule fires when any one of them occurs and the rule's condition holds. One handling fires a rule (or one row of it) at most once, however many of its triggers the event or the tick step matches (RULE-5). Triggers that belong to different handlings (an input and a timer, say) each fire the rule in their own handling, so a rule may fire several times in one tick: once in each event's handling and once in the tick step, at most, for each row.
- **Reason and source.** DEC-6587 item 5, idea 9: a note played by its computer key or by a press on its drawing is one rule, not two.
- **Verification.** Tests: a rule on a key or a press fires once for each; an event matching two of a rule's triggers fires it once; one trigger over the limit and a `becomes` beside another trigger are refused.

**RULE-10 [engine: neoteletext-rules]. Naming keys.**
- **Statement.** A key set MUST be either **any key** or 1 to `MAX_KEYS_PER_TRIGGER` keys, each one of:
  - **a character key** (kind 1): the Unicode scalar value the active keyboard layout gives the key without Shift, exactly the `key` of the input protocol's KEY event when it is a character (DOC-1935). Letters are the lower-case form.
  - **a named key** (kind 2): a functional key by its code in the input protocol's table (DOC-1936; the engine's `neoteletext_input::keys::code`), written in JSON by its name, the schema's `KeyName` (for example `Enter`, `ArrowLeft`, `F1`, `ColorF0Red`, `ShiftLeft`).
  - **a physical key** (kind 3): the key that carries the given character on a United States layout, whatever the active layout: the KEY event's `base` when it has one, else its `key` when that is a character (DOC-1937). A musical keyboard laid out on the letter rows uses this kind, so that it has the same shape on every layout.
- A key event matches a set when it matches any member. In a rule that names rows, a key set MAY instead be given **one key a row** (`by_row`): it then holds exactly as many keys as the rule names rows, and the row at place `r` among the rule's rows matches the key at place `r` of the set and no other (RULE-105). The same naming is used by a key-state value (RULE-24).
- **Reason and source.** DEC-6522 item 5 ("a named key, a character, or a set"); the input protocol already identifies keys these three ways, so nothing new is defined.
- **Verification.** Tests: on a French layout the physical key `q` matches the key that types `a`; `any` matches a modifier alone; a set one over its limit is refused; a `by_row` set fires each row for its own key alone, and one whose count is not the rule's row count is refused.

**RULE-11 [engine: neoteletext-rules]. `becomes` is an edge.**
- **Statement.** Each `becomes` rule MUST keep one bit for itself, or one for each of its rows, its condition's result at its previous evaluation, false when the page opens. In each tick step, at its `becomes` place (RULE-5), the condition is checked once against the state as it then stands; the rule (or the row) fires when the condition holds and that bit is false, and the bit is then set to the condition's result. A condition is never checked in an event's handling, so a change an event's group makes is first seen at the next tick step's check (RULE-6). A condition that already holds at page tick 0 therefore fires at tick 0. The bits are kept for at most `MAX_RULES × MAX_ROWS` rule-and-row pairs, which is every pair a table can have.
- **Reason and source.** DEC-6522 item 5 ("edge-triggered, false to true"). Firing at opening when true lets a page's meters and indicators agree with the state from the first tick.
- **Verification.** Tests: a level crossing a threshold fires once and not again while above; falling and rising fires again; the opening case; eight rows of one rule with eight thresholds fire independently.

**RULE-12 [engine: neoteletext-rules]. Targets.**
- **Statement.** A target MUST be one of four kinds, written as a kind byte and a 16-bit number:

| Kind | Name | Number | What it is |
|---|---|---|---|
| 0 | page | 0 | the whole page's picture |
| 1 | control | 1 to 32, or 0 for any control | a teletext control of the page (the engine's REQ-INT-117; `neoteletext_core::controls`), numbered from 1 in the order the page declares them |
| 2 | object | 1 to 65,535, or 0 for any object | an animation object of the page: a teletext sprite, a ReGIS numbered drawing or a NAPLPS object, by its number (animation.md) |
| 3 | rectangle | 0 to 15 | a rectangle the table declares (RULE-13) |

- Number 0 ("any") is allowed only in the triggers `press`, `release`, `enter`, `leave`, `move` and `wheel`; it fires once for each control or object concerned, and the firing's `target` value (RULE-116) and the event reported by `REPORT` name which. Animation operations and collision conditions name one control, object or rectangle. In a rule that names rows, a trigger's target number MAY be given as a constant plus the row's `p` (RULE-105).
- **Inside** is decided thus. The page: always. A control: the pointer's cell is one of the control's cells. A ReGIS numbered drawing: the picture's pick record names that drawing at the pointer's pixel, or a drawing that has it as an ancestor (regis-v2.md, "Picking"); only detectable drawings are named. A teletext sprite or a NAPLPS object: it is shown and marked detectable, and the pointer's pixel is within its bounding rectangle (ANIM-13). A rectangle: the pointer's pixel is within it. One pointer event may be inside several targets, and every rule it matches fires, in rule order.
- `enter` and `leave` fire on any pointer event that carries a position (a press, a release, a move, the wheel) when the set of targets under the pointer has changed since the last such event. `move` fires only on a move to another pixel, never on a press or a release, so that a press is reported once; its `held` is met when the move's own button mask or a tracked button says a button is down. The pointer is followed inside at most `MAX_POINTER_OBJECTS` objects at once, the number of ancestors a ReGIS drawing can have.
- A target that does not exist on the page is never inside, reads as not shown, and operations on it do nothing and are counted.
- **Reason and source.** DEC-6522 item 5 ("Targets are integer object numbers within the page"); the kind byte keeps the three renderers' numbers and the controls' apart.
- **Verification.** Tests of each kind's inside rule, with a pointer on an edge pixel; `any` firing once per object with the object named in the report.

**RULE-13 [engine: neoteletext-rules]. Rectangles and the pixel grid.**
- **Statement.** A table MAY declare 0 to `MAX_RECTS` rectangles, each `x`, `y`, `width`, `height` (each 0 to 65,535, width and height at least 1) in the pixels of the page's picture, origin at the top left, x to the right, y down: a teletext page is 480 by 500 dots (a cell is 12 by 20, DOC-1938); a ReGIS picture 800 by 480; a NAPLPS picture 640 by 480. The pointer's pixel given to the evaluator is in the same grid. A rectangle that lies partly outside the picture is cut to it.
- **Reason and source.** DEC-6522 item 5 ("a screen rectangle"); the grids are those the browser already uses for each kind of page (the browser's REQ-6377 for ReGIS).
- **Verification.** Tests on each grid's last pixel.

**RULE-14 [engine: neoteletext-rules]. The sixteen variables.**
- **Statement.** Every page MUST have exactly `VARIABLES` variables, designated `v0` to `v15` in every message and numbered 0 to 15 in every record. A table declares none and names none: the designators are fixed for every page of every channel. Each is a signed 32-bit integer and nothing else, zero when the page opens. Every operation on one saturates at −2,147,483,648 and 2,147,483,647 and is computed without overflow. They are changed only by the `VARIABLE` command (RULE-99). Variables are local to the page in its view, are dropped when the page is closed or its connection ends (RULE-111), and are never shared between pages, sub-pages, tabs or channels.
- **Reason and source.** DEC-6587 item 4 (the owner: "local variables may only store a 32 bit signed integer not anything else. local variables must have hard coded names/designators, a fixed number of them") and item 7. The first form's declared variables with ranges are withdrawn.
- **Verification.** Tests: saturation at both ends for every operation; all sixteen zero at each opening; a record naming variable 16 refused.

**RULE-15 [engine: neoteletext-rules]. The eight timers and the page timer.**
- **Statement.** Every page MUST have exactly `TIMERS` timers, designated `t0` to `t7` and numbered 0 to 7, declared by no table, all stopped when the page opens. A timer is either stopped or running since a start tick. A `TIMER` start (RULE-100) applied in a handling of tick `t` — an event's or the tick step's — makes it running since tick `t + 1`, the first tick step after the handling (RULE-6), replacing any earlier start; a stop stops it. The **page timer** (identifier 255, designated `page`, first in identifier order) always runs since page tick 0, cannot be started or stopped, and is not one of the eight. With `e` the present tick (RULE-7) minus the start tick: an `after N` trigger is due when `e = N`; an `every N` trigger is due when `e > 0` and `e` is a multiple of `N`. Those ticks are the timer's **expiries** of a period of `N` ticks: a condition may test where a running timer stands in such a period (its **phase**, RULE-25), and a sequence may be started to begin at the timer's next expiry of a period (RULE-103). A timer's values in a condition are RULE-25's.
- **Reason and source.** DEC-6522 items 5 and 7 ("timers keyed by identifier: starting a running timer replaces it"); DEC-6587 item 6; fixed and undeclared as the variables are (section 15, item 33).
- **Verification.** Tests: a start applied in an event of tick `t` or in tick step `t` makes `after 1` fire at tick step `t + 2`; restarting replaces; `every 30` on the page timer fires at ticks 30, 60, 90.

Withdrawn: RULE-16 (switching rules on and off) and RULE-17 (rules switched off for a sub-page). DEC-6587 item 8 removes `enable`, `disable`, the per-rule enabled flag and the sub-page off-lists: a mode is a variable that a rule's condition tests (RULE-110). DEC-6599 withdraws the sub-page off-lists a second way: a sub-page has a table of its own.

**RULE-105 [engine: neoteletext-rules]. Binding rows: a rule as a template, one parameter a row.**
- **Statement.** A table MAY hold 0 to `MAX_ROWS` **rows**, numbered from 0 in the order written, each exactly one signed 32-bit constant, the row's **parameter** `p`. A rule MAY name a run of rows by its first row and a count (at least 1, within the table's rows); two rules MAY name the same rows. Such a rule is a template that the **receiver** holds and matches once for each of its rows, in row order, the row standing in these places and no others:
  1. **a key set given one key a row** (`by_row`, RULE-10) of a `key` or `key_up` trigger: the row at place `r` among the rule's rows matches the set's key at place `r`. The set MUST hold exactly as many keys as the rule names rows;
  2. **the number of a trigger's target**, given as a signed 16-bit constant to which `p` is added, which MUST, for every row the rule names, give a valid number for the target's kind (a control 1 to 32, an object 1 to 65,535, a rectangle the table has);
  3. **the constant of a comparison** in the rule's condition (RULE-18), to which `p` is added with saturation;
  4. **an amount** in a command of the group the rule runs, and of every group that group runs (RULE-106), whose source may be `p` or the firing's `row`, and the `fired` value `p` (RULE-116).
- An event fires each row whose triggers, so given, it matches and for which the condition holds, each firing being a run of the rule's group with that row's `p` in force. A rule without rows runs its group with `p` 0. A sequence started by a command of such a run keeps the `p` in force (RULE-103). Rows are constants of the table: nothing changes them, and they are checked when the table is decoded, never when it runs. A value a row needs beyond its one parameter is derived from it, as a constant plus `p` (the music player's drawing `41 + p` for note `p`), or from the row's place, as a constant plus the firing's `row` (the meter's segment `301 + row`), or given by the row's place in a key set; the second form's four parameters `p0` to `p3` are withdrawn (DEC-6635 item 8).
- **Why the receiver holds the rows.** The alternative, the server expanding each row into a plain rule and a plain group, was weighed and not chosen: the music player's thirteen keys, each played by a key or a pointer press and released, would take 26 rules and 26 groups out of `MAX_RULES` and `MAX_GROUPS`, where a template takes 2 rules, 2 groups and 13 rows of 4 bytes; and the mechanism that puts a row's number into a command is the one an amount needs for a variable anyway (RULE-106), so the evaluator gains one source of a number and no new machinery. The table on the wire is smaller and the 64-rule limit is not spent on repetition.
- **Reason and source.** DEC-6587 item 5, idea 2, and item 6; DEC-6635 item 8 ("A row supplies one value, `p`, which the template's trigger and its group's commands may use where the binding table allows (for the keyboard: the note, and the drawing number derived as a constant plus `p`)"). The key set given one key a row, and the firing's `row` as a target's source, are this document's readings of that item (section 15, items 47 and 48).
- **Verification.** Tests: thirteen rows with a `by_row` key set fire the right row for each key and none for another; a `by_row` set whose count is not the rule's row count, and a row whose `p` gives a target number out of range, each refuse the table whole; two rules sharing rows; a `becomes` rule with eight rows and eight thresholds; an `ANIMATE` target `301 + row` names each row's segment.

Withdrawn: RULE-108 (held and double-press triggers). DEC-6635 item 7 withdraws the triggers `held`, `double`, `press_held` and `double_press` (codes 17 to 20, never reused), the memory of recent presses and the record of each key's and button's down tick that they needed, with their limits `MAX_HOLD_TICKS`, `MAX_DOUBLE_TICKS` and `MAX_RECENT_PRESSES`. A long press is a `key` rule that starts a timer, a `key_up` rule that stops it, and an `after` rule on the timer; a double press is a `key` rule that sets a variable and starts a timer when the variable is 0, a second `key` rule that acts when it is 1, and an `after` rule that sets it back to 0 (section 7.5, example 8; RULE-93's `panic` rules).

**RULE-109 [engine: neoteletext-rules, neoteletext-audio, neoteletext-audio-instruments; neoteletext-browser; neoteletext-app-server]. Cue points in a playing sound.**
- **Statement.** A **cue** is a numbered point, 0 to `MAX_CUE`, in the event list of a stored or live synthesizer sound whose blocks the server sends.
  - **In the block.** A cue is carried as the Standard MIDI Files Cue Point meta event with one byte of data, the cue's number: the four bytes `FF 07 01 nn` after its delta time (Standard MIDI Files 1.0, "Meta-Events": `FF 07 len text`, Cue Point; `FF 06 len text` is Marker). The block grammar of midi-architecture.md MIDI-23 already reads a meta event as a `skipped` event passed over by its length, so a receiver that knows no cues is unaffected. This amends MIDI-8 and MIDI-115, which said a block carries no meta event: it now carries this one and no other. A block holds at most `MAX_CUES_PER_BLOCK` (4) cues, a limit of the audio block and not of the rule table, defined in `neoteletext-audio-instruments`; a fifth is passed over and counted.
  - **From a program.** In the program protocol a family's event list MAY hold `{"event":"cue","number":n,"time_us":…}`. When a stored sound is given as a Standard MIDI File (MIDI-112), the `sound` message MAY give `cues`, a list of at most `MAX_CUE + 1` entries `{"text":"…","number":n}`, each `text` 1 to 64 bytes: the server turns each Marker (`FF 06`) and Cue Point (`FF 07`) meta event of the file whose text equals an entry's `text` byte for byte into that cue number at the event's time, and drops the others as before (the server's DEC-6654 item 7; midi-architecture.md MIDI-115). No receiver reads a cue's text. A cue in a local sound's setup is refused, since a local sound has no timeline. The highest cue number is the highest data byte a block carries: `neoteletext-web` asserts at compile time that `MAX_CUE` equals `neoteletext_audio::midi::DATA_MAX`, so that the rule crate needs no dependency on the audio crates (DEC-6648 item 11).
  - **Heard, not rendered.** The decoder renders a sound's blocks ahead of what is heard (by up to `STREAM_TARGET_MS`). When its instrument's event reader passes a cue, the decoder MUST send the sound helper, through the trusted core, a **cue mark**: the audio channel, the position of the cue in the stream as a count of samples from the stream's start, and the number (`Cue`, RULE-63). The sound helper keeps at most `MAX_PENDING_CUE_MARKS` (32) marks for each stream, dropping and counting more. As soon as it has rendered the device buffer that holds a mark's sample, and without waiting for the metering report, it reports `CueHeard` (the view's channel number, the audio channel, the number) to the trusted core, which checks the fields' bounds and that the view has that sound playing, and gives it to that view's decoder; the decoder gives the evaluator the cue as an event, handled at once (RULE-5), which fires the `cue` rules. A cue is therefore acted on within one device buffer, and the pipes' passage, of being heard. A sound that is stopped, or a page that is paused or closed, forgets its marks.
  - **The trigger** names an audio channel, 0 to 3, and a cue number, or 255 for any cue; the firing's `cue` value (RULE-116) is the number.
  - A local sound has no timeline and so no cues. The sound helper is told no rule and no trigger; it echoes numbers its own view's decoder gave it.
- **Reason and source.** DEC-6587 item 5, idea 4. The mark travels with the stream and comes back when heard, because the decoder's own position is up to 400 milliseconds early.
- **Verification.** Engine tests: a block with a cue parses, the instrument reports it at its sample, and a fifth in a block is counted; a server test of each program form and of a file's markers; a helper test with a scripted device that a mark at sample `s` is reported after the buffer holding `s` and before the next; a browser test that the `cue` rule fires when the decoder is given the report, before its next tick step.

**RULE-110 [neoteletext-common; the kits]. Modes are variables.**
- **Statement.** A page that has sets of rules that apply at different times MUST express it with a variable: each rule of a set tests the variable in its condition, and a group changes the variable. Nothing else switches a rule on or off, and no value gives the shown sub-page (DEC-6599: another sub-page is another page with a table of its own). The kits MUST offer a small helper that only builds objects (RULE-55): a mode set names one variable and gives each named mode a number from 0; it yields, for a mode, the condition `{"read":{"of":"variable","variable":"v3"},"op":"==","value":n}` (joined with a rule's own condition by `and`) and the command `{"type":"variable","op":"set","variable":"v3","value":n}`. Because a change of a variable is seen by the conditions of later handlings and never within the handling that made it (RULE-6), a mode changes between handlings: a key that sets the mode is not also decided under the new mode, and the next key is.
- **Reason and source.** DEC-6587 items 5 (idea 6) and 8 (the owner: "why enable and disable rules?"); DEC-6599 item 4.
- **Verification.** Kit tests of the helper's objects; evaluator tests that a key which sets the mode does not also fire that key's rule of the new mode, and that the next key, in the same tick, does.

## 4. Conditions

**RULE-18 [engine: neoteletext-rules]. The condition expression.**
- **Statement.** A condition MUST be a tree of at most `MAX_CONDITION_NODES` nodes, of which at most `MAX_CONDITION_TERMS` are terms, with operators nested at most `MAX_CONDITION_DEPTH` deep (a term directly under that many operators is allowed; one operator level more is refused). The nodes:

| Code | Node | Meaning |
|---|---|---|
| 1 | `and` | 2 to `MAX_AND_OR_CHILDREN` children; true when all are |
| 2 | `or` | 2 to `MAX_AND_OR_CHILDREN` children; true when any is |
| 3 | `not` | 1 child; true when it is false |
| 4 | compare (term) | a value (section 6), one of `==` (1), `!=` (2), `<` (3), `<=` (4), `>` (5), `>=` (6), and a signed 32-bit constant, to which the row's `p` MAY be added (RULE-105) |
| 5 | in range (term) | a value and constants `low ≤ high`; true when `low ≤ value ≤ high` |
| 6 | in set (term) | a value and 1 to `MAX_SET_MEMBERS` constants; true when the value equals one |
| 7 | `overlaps` (term) | two targets; true when their bounding rectangles share at least one pixel (RULE-19) |
| 8 | `inside` (term) | two targets; true when the first's bounding rectangle lies wholly within the second's (RULE-19) |

- Every value is a signed 32-bit integer and every comparison is of a value with a constant of the table; two values are never compared with each other and nothing is computed from them. Evaluation of `and` and `or` MAY stop at the first child that settles it, since no node has an effect.
- **Reason and source.** DEC-6522 item 6; DEC-6524 item 9 for nodes 7 and 8; DEC-6587 item 5 (idea 2) for the row parameter.
- **Verification.** Tests of each node and operator at its boundaries; one term, one node and one level over their limits are each refused whole.

**RULE-19 [engine: neoteletext-rules]. Collision and region tests are on bounding rectangles.**
- **Statement.** For `overlaps` and `inside`, each target's rectangle MUST be: a control's cells in dots; an animation object's bounding rectangle as its renderer reports it for the object's state as it stands (ANIM-13, RULE-7); a declared rectangle; the page's whole picture. A target that does not exist or is not shown has no rectangle, and a test that names it is false. `overlaps` and `inside` MUST name targets of kinds 1, 2 or 3 as the first operand and of kinds 0 to 3 as the second, and never "any" or the row's `p`.
- **Reason and source.** DEC-6524 item 9: "object A overlaps object B" and "object A is inside rectangle R", on bounding rectangles.
- **Verification.** Tests: rectangles that touch at an edge do not overlap; share one pixel, do; a hidden object overlaps nothing.

## 5. Groups and commands

Withdrawn: RULE-20 (the nineteen action kinds). DEC-6587 item 1 removes the rule's action list: the only thing a rule triggers is a group of protocol commands. Each first-form action is now a command: `midi` is `LOCAL_MIDI` (RULE-21); `play`, `stop` and `gain` are the audio profile's `CONTROL` record; `show`, `hide`, `look`, `move`, `order`, `frame`, `cycle` and `stop_cycle` are operations of an `ANIMATE` record (ANIM-6); `set` and `add` are `VARIABLE` (RULE-99); `start_timer` and `stop_timer` are `TIMER` (RULE-100); `send` is `REPORT` (RULE-22); `enable` and `disable` are withdrawn (RULE-110).

**RULE-118 [engine: neoteletext-rules]. A group, and a run of it.**
- **Statement.** A table MAY hold 0 to `MAX_GROUPS` groups, numbered from 0 in the order written. A group is a list of 1 to `MAX_GROUP_COMMANDS` commands. Each command is one record's type and body, exactly the bytes the server would send that record with directly, at most `MAX_COMMAND_BYTES` of body, with up to `MAX_COMMAND_BINDINGS` bindings after it (RULE-106), framed as RULE-45 gives. A group is referenced by its number: by a rule, by a sequence's step and by a `RUN` record. The receiver MUST check every command of every group when the table is decoded — its type against RULE-119's list, its body with the same reader that reads that record when the server sends it, its page against the table's own, its bindings against RULE-106's table — and refuse the whole table for any fault (RULE-70); nothing is checked when a group runs. To **run** a group is to apply its commands in written order, each exactly as the same record sent by the server is applied, with its amounts resolved first; a `RUN` command that runs a group now is replaced, in that order, by the run of that group (RULE-102). A run happens only in a handling of RULE-5, and each of its commands takes effect as it is applied (RULE-96). A command whose target, sound, group, timer or sequence does nothing useful when it runs (an object that does not exist, an audio channel with no sound) does nothing, is counted in the page's `skipped` figure (RULE-72) and never stops the run.
- **Reason and source.** DEC-6587 item 1: "A group is a stored, numbered list of ordinary protocol commands … which the receiver checks and holds when the page arrives and applies when a rule runs the group", so that there is one vocabulary: anything the server can send, a rule can trigger, and it is applied by the code that already applies records.
- **Verification.** Tests in `neoteletext-rules`: a group round-trips byte for byte; each command in a group has the effect of the same record applied directly; one command, one group and one byte of a command over their limits are each refused whole.

**RULE-119 [engine: neoteletext-rules, neoteletext-web]. What a group may hold, and what it may not.**
- **Statement.** A command in a group MUST be a record of one of these types, and its body's page field (and sub-code field, where the record has one) MUST be the table's own page:

| Type | Record | In a group it | Sent directly it is applied |
|---|---|---|---|
| 3 | `CONTROL` (the audio profile's, REQ-AUD-006) | plays a sound the page already has, stops or changes the gain of an audio channel. Its sequence field MUST be 0 and is not read; its page field MUST be the table's page number (a group cannot start a sound for the whole service, which would outlive the page); its flags MUST NOT include "after the current sound" | on arrival, as today |
| 15 | `DRAWING_LINKS` (REQ-6370; renderer parity PAR-2, PAR-20) | replaces the links of the page's picture: the program messages `regis_links` and `naplps_links` without `connections`. Only a whole sending, part 0 of 1, within `MAX_COMMAND_BYTES` | on arrival, as today |
| 16 | `REGIS_CURSOR` (REQ-6371; renderer parity PAR-2, PAR-20) | makes a drawing or object the page's picture's cursor, or none: `regis_cursor` and `naplps_cursor` without `connections` | on arrival, as today |
| 23 | `ANIMATE` (ANIM-6) | changes the animation state of the page's controls and objects: `show`, `hide`, `look`, `move`, `order`, `frame`, `cycle`, `stop_cycle`, `reset` | on arrival, between handlings (RULE-7); drawn at the next display frame |
| 24 | `SPRITES` (ANIM-7) | replaces the page's teletext sprites | on arrival, between handlings |
| 25 | `NAPLPS_OBJECTS` (ANIM-11) | replaces the page's NAPLPS objects | on arrival, between handlings |
| 28 | `LOCAL_MIDI` (RULE-21) | gives one MIDI message to a local sound | on arrival |
| 29 | `VARIABLE` (RULE-99) | changes a variable | at once, as an event of the open page (RULE-5) |
| 30 | `TIMER` (RULE-100) | starts or stops a timer | at once, as an event |
| 31 | `REPORT` (RULE-22) | reports to the page's channel | at once, as an event |
| 32 | `RUN` (RULE-102) | runs another group now | at once, as an event |
| 33 | `SEQUENCE` (RULE-103) | starts or stops a sequence | at once, as an event |

- Every other record type MUST be refused in a group, and the table with it. Each, and why:

| Forbidden in a group | Why |
|---|---|
| `RULES` (21): a table, and with it any definition of a group, a sequence, a row or a rectangle | A page cannot rewrite its own rules when triggered (DEC-6587 item 9). What a table can do is fixed when it is checked, by the server and again by the receiver, and never changes afterwards |
| `REGIS` (14), `NAPLPS` (17), `SHEET` (26) and teletext packets: page content | These are bytes at an offset of a stream the server owns; a stored copy applied at a local time would leave the receiver and the server disagreeing about the stream. A picture is sent ahead (hidden drawings, a sheet, sprites, objects) and a group shows, hides, moves or re-looks it. The 256-byte command limit would not hold a picture in any case |
| `OBJECT` (1), `DATA` (2): a sound's definition and its blocks | Assets are sent ahead; a group plays them. Blocks are a stream the server owns |
| `FRAME` (27) | A run is already applied whole in one handling, and drawn in one display frame; a frame inside it would have nothing to bracket |
| `LINKS` (9), `SUBPAGES` (10) | Where a link leads and which sub-pages a page lists are navigation the browser shows the viewer and follows itself; they must not change at local speed under the pointer |
| `REDIRECT` (11), `DENIED` (12), `INDEX` (6), `LOG` (7) | They concern the channel or the selection, not a page's presentation; a stored `REDIRECT` would let a table move the viewer to another page or channel by a timer |

- *Amended 19 November 2026 (renderer parity PAR-20, DEC-6760, TODO-6794):* `DRAWING_LINKS` (15) and `REGIS_CURSOR` (16) moved from the forbidden list to the allowed one, since PAR-20 makes `naplps_links` and `naplps_cursor` (and so `regis_links` and `regis_cursor`) commands a group may hold. A picture's links stay under every rule of a link the browser follows itself (the destination shown in the strip while the pointer is on the target, the dwell time, the question before leaving the channel, PAR-28, REQ-6376), so a group that changes them at local speed changes what the viewer is shown before anything is followed, never where a press already made goes. A group's `DRAWING_LINKS` is one whole sending (part 0 of 1), bounded by `MAX_COMMAND_BYTES`; a longer set of links is the server's to send directly. `LINKS` and `SUBPAGES` stay forbidden.
| `CURSOR` (4), `INPUT_CONTROL` (5), `STATE_CHALLENGE` (18), `STATE_END` (19), `STATE_KEEP_OFFER` (20), `RULES_QUERY` (22) | They belong to the session, to viewer state or to the server's own question; none is a page's to replay |

- A `SPRITES` or `NAPLPS_OBJECTS` command is held to the 256-byte command limit like any other, so a group can place a few small sprites or objects and not a whole page of them; the whole set is sent ahead by the server and a group moves and shows it with `ANIMATE`.
- **Reason and source.** DEC-6587 items 1, 6 ("a single command in a group is at most 256 bytes, so a group cannot carry a whole picture") and 9; the list of what is forbidden is this document's, each with its reason (section 15, item 34).
- **Verification.** One test for each allowed type (accepted, and applied as the direct record is) and one for each forbidden type (the table refused whole); a `CONTROL` naming another page or no page, and an `ANIMATE` naming another sub-code, each refused.

**RULE-120 [engine: neoteletext-rules]. A group is limited by its commands, not by its work.**
- **Statement.** These limits hold, each a named constant whose figure is stated in RULE-57 and nowhere else, each checked when the table is decoded, and a table over any is refused whole: `MAX_GROUP_COMMANDS` commands a group; `MAX_GROUPS` groups a page; a command's body at most `MAX_COMMAND_BYTES`; all of a page's groups together, as framed, at most `MAX_GROUPS_BYTES`; a group MAY run other groups (a `RUN` command with the mode "now") to a depth of at most `MAX_GROUP_DEPTH`, a group that runs none having depth 1, and no group may run itself directly or through others; and one run of a group, with every group it runs in place, applies at most `MAX_RUN_COMMANDS` commands, each `RUN` counting as one command beside the commands of the group it runs. Because nesting has no cycle and no condition, the number of commands a run applies is a constant of the table, and the receiver never counts commands while running. The receiver MUST NOT put any limit on the work a run does beyond these: no count of actions a tick, no time budget on a triggered group. The receiver's general budgets, which apply to every command however it arrives — the repaint budget (REQ-6368), the animation budget (ANIM-16), the report budgets of the trusted core (RULE-52), the local sound's message queue and overrun stop (RULE-62) — apply to a group's commands exactly as to the server's.
- **Reason and source.** DEC-6587 item 2 (the owner: "i agree with constraining the number of commands in a group but not work cap") and item 6 (the figures, proposed by the session for the owner's confirmation). What a hostile table can cost within these limits is section 12.4.
- **Verification.** Tests: a chain of `MAX_GROUP_DEPTH` groups accepted and of one more refused; a cycle of two and a group that runs itself refused; a group whose expansion is `MAX_RUN_COMMANDS` commands accepted and one more refused; groups of `MAX_GROUPS_BYTES` bytes accepted and one byte more refused.

**RULE-21 [engine: neoteletext-web, neoteletext-rules; neoteletext-browser]. `LOCAL_MIDI`, record type 28: one MIDI message to a local sound.**
- **Statement.** Record type 28, `LOCAL_MIDI`, has a body of 8 bytes: the page (2 bytes); the sub-code (2 bytes); the audio channel (1 byte, 0 to 3); a status byte; and two data bytes. It MUST carry one complete MIDI 1.0 channel voice message with no running status: note off (`0x8n`), note on (`0x9n`), control change (`0xBn`), program change (`0xCn`, whose second data byte is 0 and is not given to the instrument) or pitch bend (`0xEn`, whose 14-bit value is data 1, the low seven bits, and data 2, the high seven), where `n` is the part's MIDI channel less one, and each data byte is 0 to 127 (MIDI 1.0 Detailed Specification, "Channel Voice Messages"). Polyphonic key pressure, channel pressure, system exclusive, system common and system real-time messages MUST be refused by the record's reader. The message is given to the local sound (RULE-60) playing on the named audio channel for that page in the view; when no local sound plays there, the command does nothing and is counted. It is never given to a sound whose blocks the server sends, whose timeline the server owns. It is a sound command (RULE-96). The server MAY send it directly (the program message `local_midi`, RULE-114), and a receiver applies it on arrival when that page is the open page of the view, and otherwise drops and counts it.
- **Reason and source.** DEC-6522 item 7 ("a standard MIDI message to a playing synthesizer sound"); DEC-6587 item 1, which makes it a record the server can also send. Limiting it to local sounds keeps one writer for each instrument's timeline.
- **Verification.** Codec tests for each status; a system exclusive status refused; a browser test that a `LOCAL_MIDI` reaches only a local sound, from a group and from the server.

**RULE-99 [engine: neoteletext-web, neoteletext-rules]. `VARIABLE`, record type 29.**
- **Statement.** Record type 29, `VARIABLE`, changes one variable. Its body: the page (2 bytes); the sub-code (2 bytes); an operation (1 byte); the variable (1 byte, 0 to 15; 255 for all sixteen, with `clear` only); an operand kind (1 byte); and the operand:

| Operand kind | Bytes after it | The operand's value |
|---|---|---|
| 0 | none | none (for `inc`, `dec`, `toggle`, `clear`) |
| 1 | a signed 32-bit constant | the constant |
| 2 | a constant; a variable (1 byte, 0 to 15) | the constant plus that variable's value as it stands, saturating |
| 3 | a constant; a `fired` property (1 byte, 0 to 4, RULE-116) | the constant plus that value of the firing, saturating |
| 4 | a value (8 bytes, RULE-44) | that value as it stands (RULE-7) (`set` only) |
| 5 | two constants `low ≤ high` | the range (`wrap` only) |

| Code | Operation | Operand kinds | Effect on the variable `v` |
|---|---|---|---|
| 1 | `set` | 1 to 4 | `v` becomes the operand |
| 2 | `inc` | 0 | `v` becomes `v + 1`, saturating |
| 3 | `dec` | 0 | `v` becomes `v − 1`, saturating |
| 4 | `add` | 1 to 3 | `v` becomes `v` plus the operand, saturating |
| 5 | `sub` | 1 to 3 | `v` becomes `v` minus the operand, saturating |
| 6 | `toggle` | 0 | 0 becomes 1; anything else becomes 0 |
| 7 | `min` | 1 to 3 | `v` becomes the lesser of `v` and the operand: `v` is held to at most the operand |
| 8 | `max` | 1 to 3 | `v` becomes the greater of `v` and the operand: `v` is held to at least the operand |
| 9 | `wrap` | 5 | when `v > high`, `v` becomes `low`; when `v < low`, `v` becomes `high`; otherwise unchanged. It follows a change, for a counter that cycles; it is a comparison and an assignment, never a division |
| 10 | `clear` | 0 | `v` becomes 0; with variable 255, all sixteen do |

- There is no multiplication, division, remainder, bit operation or random number, and no operation whose variable is chosen by a number computed at run time. Every sum is computed without overflow and saturates at the 32-bit bounds. A record whose body is not exactly its operation's and operand kind's length, or that pairs an operation with an operand kind the table above does not give it, is refused. Sent directly (`variable`, RULE-114) it is an event of the open page, handled at once (RULE-5), where a `fired` operand reads 0.
- **Reason and source.** DEC-6587 item 7 (proposed by the session at the owner's request: "operations like inc dec and others that you think right").
- **Verification.** A test of each operation with each operand kind at the 32-bit bounds; `wrap` at, above and below its range; each disallowed pairing refused.

**RULE-100 [engine: neoteletext-web, neoteletext-rules]. `TIMER`, record type 30.**
- **Statement.** Record type 30, `TIMER`, has a body of 6 bytes: the page; the sub-code; an operation (1 start, 2 stop); a timer (0 to 7). Start makes the timer running since the tick after the one in which the command is applied, replacing an earlier start; stop stops it (RULE-15). The page timer cannot be named.
- **Reason and source.** DEC-6522 item 7; DEC-6587 item 1 (timer start and stop are protocol commands).
- **Verification.** Covered by RULE-15's tests, from a group and from a direct record.

**RULE-22 [engine: neoteletext-web, neoteletext-rules]. `REPORT`, record type 31: the one command that tells the channel.**
- **Statement.** Record type 31, `REPORT`, has a body of 13 bytes: the page; the sub-code; `what` (1 byte); and a value (8 bytes, RULE-44, all zero unless `what` is 1). With `what` 0 it reports **the firing**: in a run made by an input's rule, that the rule fired together with the input event exactly as the viewer made it (and, for a pointer trigger, the target it was inside); in any other run — a timer's, a sequence's, a cue's, `open`, `close`, `becomes`, a command of the server's — only that the rule or the run fired, with no event. With `what` 1 it reports one named value, as it stands when the command is applied (RULE-7). Each `REPORT` applied makes one report (RULE-46), and what leaves the receiver for it, and its limits, are RULE-52's: a report can carry an input event only when a rule the viewer's own event fired ran it in that event's handling, so a group cannot widen what is sent (REQ-6523). The first form's `echo` flag is withdrawn as a part of a rule: the program protocol keeps `"echo": true` as a way of writing "and a `REPORT` of the firing after the group" (RULE-35). Sent directly by the server (`report`, RULE-114), `what` MUST be 1: the server refuses the other, and a receiver that is sent it reports a bare firing with no rule.
- **Reason and source.** DEC-6522 items 7 and 8; DEC-6587 item 1 ("reporting to the server" is a protocol command); `echo` decided in section 15, item 35.
- **Verification.** Tests: the reports of a group with two `REPORT`s, in order; a `REPORT` in a sequence's step carries no event; a `REPORT` of `v0` after `inc v0` in one group reports the new value.

**RULE-102 [engine: neoteletext-web, neoteletext-rules]. `RUN`, record type 32: run a group now.**
- **Statement.** Record type 32, `RUN`, has a body of 5 bytes: the page; the sub-code; a group (1 byte, a group of the page's table). In a group it runs the named group in place, at this point of the run (a nested run, RULE-120). Sent directly by the server it is an event of the open page, handled at once (RULE-5), whose run has no firing: `p` and every `fired` value read 0.
- **Withdrawn: armed runs and quantised start** (DEC-6635 item 6). The second form's modes 1 (`at` a page tick), 2 (`after` a delay) and 3 (`beat`, a timer's next beat), the armed run with its due tick, group and parameters, and the limits `MAX_ARMED_RUNS` and `MAX_ARM_TICKS` are withdrawn. A run at a given page tick is a one-step sequence started at that tick (RULE-103, start `at`); a run after a delay is a sequence whose one step has that offset; a run on a timer's next expiry is a sequence started with `beat` (RULE-103); and a rule's condition may test where a timer stands in a period (its phase, RULE-25). The record kind "armed run" is not a part of any record, message or state, and nothing takes its place in PAGE_STATE.
- **The two clocks.** The page tick is the receiver's: it starts at 0 when the page opens in that view, counts the tick steps the receiver has run, slows when the receiver is late and does not advance while the page is paused. The server has no copy of it. It learns it from the `tick` every report carries (RULE-37) and from a state answer (RULE-38), and estimates the present tick as the last one learnt plus sixty for each second since. A program that wants several viewers' pages to act at one moment of its own clock starts a sequence at a page tick in each view, from that view's own estimate, and accepts that a start for a tick already past happens at the next tick step. Nothing is resynchronised.
- **Reason and source.** DEC-6587 item 5, idea 10 (groups running groups); DEC-6635 item 6.
- **Verification.** Tests: a `RUN` in a group runs its group in place; a `RUN` sent directly runs its group at once with `p` 0; a `RUN` body of any other length is refused.

**RULE-103 [engine: neoteletext-web, neoteletext-rules]. Sequences, and `SEQUENCE`, record type 33.**
- **Statement.** A table MAY hold 0 to `MAX_SEQUENCES` sequences, numbered from 0. A sequence is: a length in ticks (1 to `MAX_SEQUENCE_TICKS`); a repeat count (1 to `MAX_SEQUENCE_REPEAT`, or 0 for "until stopped"); and 1 to `MAX_SEQUENCE_STEPS` steps, each a tick offset (0 to the length less one) and a group, in ascending offset, two steps of one offset being run in written order. A sequence is **stopped**, **waiting** (to start at a page tick it holds) or **running** (since a start tick, with a position and a count of passes), and holds the row parameter `p` its steps' groups run with.
- Record type 33, `SEQUENCE`, has a body of 12 bytes: the page; the sub-code; an operation (1 byte: 1 start, 2 stop); a sequence (1 byte: 0 to 7; 255 for every sequence, with stop only); a start mode (1 byte); a timer (1 byte: 0 to 7 or 255 for the page timer, in start mode 2; else 0); and `ticks` (unsigned 32-bit). With stop, the start mode, the timer and `ticks` MUST be 0.

| Start mode | Name | `ticks` | The start tick `S` |
|---|---|---|---|
| 0 | next | 0 | the first tick step after the handling in which the command is applied: `t + 1`, for a handling of tick `t` |
| 1 | at | a page tick | that page tick. A tick earlier than `t + 1` has passed: the start tick is `t + 1`, and the start is counted as late. A tick more than `MAX_START_TICKS` after `t` is not started, and is counted as skipped (the sequence is left as it was) |
| 2 | beat | a period `P`, 1 to `MAX_TIMER_TICKS` | the named timer's next expiry of period `P`: the first tick, from `t + 1` on, at which an `every P` trigger on that timer would be due (RULE-15), computed when the command is applied from the timer's start tick. When the timer is stopped, `t + 1` |

- **Start**, applied in a handling of tick `t`, replaces any run or waiting start of that sequence, holds the `p` in force (or 0), and sets the start tick `S` by its mode: the sequence is **waiting** for `S`. At the tick step of `S` it becomes running at position 0 and pass 0 (RULE-5, the tick step's sequences place), and its offset-0 steps run in that tick step. At the sequences place of each tick step a running sequence runs every step whose offset equals its position; after the tick step's groups have run, the position goes up by one, and when it reaches the length it returns to 0 and the pass count goes up by one, and when the pass count reaches a repeat count that is not 0 the sequence stops. A sequence that a command of the tick step stopped or started again does not advance in that tick step. **Stop** stops it where it is, or cancels its waiting start; the step groups already run are not undone. A sequence's steps are constants of the table, and its position is a counter, never a division.
- **A one-step sequence is an armed run.** "Run group `g` at tick `T`" is a sequence of length 1, repeat count 1 and one step `{offset 0, g}`, started `at` `T`; "run `g` after `N` ticks" is a sequence of length `N + 1`, repeat 1 and one step `{offset N, g}`, started `next`; "run `g` on the next beat" is such a sequence started `beat` (DEC-6635 item 6).
- **Reason and source.** DEC-6587 item 5, ideas 3 (local sequences, groups with tick offsets) and 11 (repeat counts); item 6; DEC-6635 item 6 ("Armed runs … become a one-step sequence started at a given tick; the server starts it with the sequence command … a sequence may be started to begin at a timer's next expiry"). The three start modes and the start tick's rules are this document's reading of that item (section 15, item 49).
- **Verification.** Tests: a sequence of three steps and length 12, repeated twice, started by a key in tick `t`, runs its groups at tick steps `t+1`, `t+5`, `t+9`, `t+13`, `t+17`, `t+21` and stops; restarting replaces; "until stopped" runs past `MAX_SEQUENCE_REPEAT` passes; a start `at` a past tick runs at `t + 1` and is counted late; a start `at` beyond `MAX_START_TICKS` is skipped and counted; a start `beat` of 8 on a timer started at tick 3, applied in tick 13, begins at tick 20; a stopped timer's `beat` begins at `t + 1`; a waiting sequence stopped never runs; a step offset not below the length, descending offsets, one step over the limit and a stop with a non-zero start mode are refused.

**RULE-106 [engine: neoteletext-rules]. A variable as a command's value: amounts and bindings.**
- **Statement.** A command in a group MAY carry up to `MAX_COMMAND_BINDINGS` **bindings**. A binding names one field of the command and one **source**, and means: when the command runs, the field's value is the constant written in the command's body plus the source's value, added as signed 32-bit integers with saturation, and then held to the field's valid range (below the least becomes the least, above the greatest becomes the greatest). The command is then applied with that value exactly as if the server had sent it so. The sources:

| Source byte | Source | Value |
|---|---|---|
| `0x10` to `0x1F` | a variable `v0` to `v15` | its value as it stands when the command is applied (RULE-7) |
| `0x20` | the row parameter `p` | the `p` in force (RULE-105); 0 when none |
| `0x30` to `0x33` | a value of the firing: the key, the target, the row, the cue (RULE-116) | as RULE-116 gives; 0 when there is none |

- Source bytes `0x21` to `0x23`, the second form's `p1` to `p3`, are withdrawn (DEC-6635 item 8) and refused.
- The fields that accept a binding are exactly these, and a binding of any other field refuses the table:

| Record | Field code | Field | Valid range | Sources allowed |
|---|---|---|---|---|
| `LOCAL_MIDI` | 1 | data 1 (the key, the controller or the program) | 0 to 127 | any |
| `LOCAL_MIDI` | 2 | data 2 (the velocity or the controller's value; not with program change) | 0 to 127 | any |
| `LOCAL_MIDI` | 3 | the 14-bit pitch bend value (status `0xEn` only) | 0 to 16,383 | any |
| `CONTROL` | 1 | gain | 0 to 100 | any |
| `CONTROL` | 2 | fade, in milliseconds | 0 to 10,000 | any |
| `ANIMATE`, operation `move` | 2, 3 | x, y | −32,768 to 32,767 | any |
| `ANIMATE`, operation `frame` | 4 | frame | 0 to 15 | any |
| `ANIMATE`, operation `look` | 5 | look | 0 to 3 | any |
| `ANIMATE`, operation `order` | 6 | order within the layer | −128 to 127 | any |
| `ANIMATE`, operation `cycle` | 7 | period, in ticks | 1 to 3,600 | any |
| `ANIMATE`, every operation | 1 | the target's number | 1 to 32 for a control, 1 to 65,535 for an object | the row's `p` (`0x20`), the firing's target (`0x31`) or the firing's row (`0x32`), **never a variable** |

- A binding's **item** byte is the place of the operation within an `ANIMATE` record, from 0, and 0 for every other record. A field has at most one binding. The target's number is the one field that is an identity and not a quantity: it is not held to a range — a number outside its range makes that one operation do nothing and be counted — and it never takes a variable, because a variable choosing which object is acted on would be a computed address (RULE-1); the row's `p` and the row's place are constants of the table, and the firing's target is the object the viewer's own pointer event named. No audio channel, handle, generation, page, sub-code, status byte, group, timer, sequence, variable designator, layer, flag or count takes a binding. `VARIABLE` has its own operands (RULE-99) and takes none; `TIMER`, `REPORT`, `RUN`, `SEQUENCE`, `SPRITES` and `NAPLPS_OBJECTS` take none. A record the server sends directly has no bindings: its fields are constants.
- An amount is a constant plus **one** source. A value that needs two (a note that is a row's `p` plus an octave variable) is made by a `VARIABLE` command first: `set v2` to the firing's `p`, `add v2` `v0`, then the note's key is `0 + v2`.
- **Reason and source.** DEC-6587 item 5, idea 12: "a variable as a command's value, a constant plus a variable held to the field's valid range", and its amendment of REQ-417 to allow bounded saturating addition and nothing else; DEC-6635 item 8 (one row parameter). The firing's row as a target's source is section 15, item 48.
- **Verification.** A test of each row of the table: the field takes the sum, saturates and is held to its range; a binding of a field not listed, a variable bound to a target number, and two bindings of one field are each refused whole; a target number out of range at run time is a counted no-op.

## 6. The values a condition, a report or a `set` can read

Every value is a signed 32-bit integer. A value is named in a record by 8 bytes: a space byte, a byte `a` and three 16-bit fields `b`, `c`, `d` (RULE-44). A value that cannot be read (no sound on the channel; another family's sound; a property the family does not have) reads as 0, and a property `playing` or `shown` exists in each space to tell "0" from "absent".

**RULE-23 [engine: neoteletext-rules]. Space 1: the variables.**
- **Statement.** `a` is the variable's number, 0 to 15; `b`, `c`, `d` are 0. The value is the variable's as it stands when it is read (RULE-7).
- **Verification.** Covered by RULE-14's and RULE-7's tests.

**RULE-24 [engine: neoteletext-rules]. Space 2: key and pointer state.**
- **Statement.** `a` is the kind: 1 a character key, 2 a named key, 3 a physical key (RULE-10), with the key's 32-bit code in `b` (high half) and `c` (low half): the value is 1 while that key is down, else 0. Kind 4 is a pointer button, `b` the button 0 to 2: 1 while down over the page. Kind 5 is the pointer: `b` 0 gives 1 while the pointer is over the page, `b` 1 its x pixel and `b` 2 its y pixel (0 while it is not over the page). Kind 6 is the count of keys down, 0 to 16. These read the input state (RULE-8).
- **Reason and source.** DEC-6522 item 6 ("key states").
- **Verification.** Tests with the events of RULE-8.

**RULE-25 [engine: neoteletext-rules]. Space 3: timers.**
- **Statement.** `a` is the timer, 0 to 7 or 255 for the page timer; `b` is the property: 0 running (1 or 0); 1 elapsed ticks since its start, `e` of RULE-15 at the present tick (0 while stopped and before its start tick; at most 2,147,483,647); 2 **phase** in a period `P`, given with `c` the high and `d` the low 16 bits of `P` (1 to `MAX_TIMER_TICKS`): `e` less the greatest multiple of `P` that is not above `e`, so 0 at the start tick and at each tick at which an `every P` on the timer is due, and counting up to `P − 1` between (0 while stopped and before its start tick). For properties 0 and 1, `c` and `d` are 0. The receiver keeps the phase as it keeps `every`'s expiries; a table computes nothing from it.
- **Reason and source.** DEC-6635 item 6: "a rule's condition may test a timer's phase", which replaces the second form's quantised start for a rule that should act only near a beat. That the phase is a property of the timer value, with its period in the value's own fields, is section 15, item 49.
- **Verification.** Covered by RULE-15's tests; and: on a timer started at tick 3, the phase in a period of 8 reads 0 at tick 12 and 20, 7 at tick 19; a period of 0 or above `MAX_TIMER_TICKS` refuses the table.

**RULE-26 [engine: neoteletext-rules]. Space 4: target state.**
- **Statement.** `a` is the target's kind (1 control, 2 object), `b` its number, `c` the property: 0 exists (1 or 0), 1 shown, 2 frame (0 to 15), 3 x and 4 y (the object's position in its renderer's units, ANIM-6; a control's first column and row), 5 the look in force (0 to 3), 6 layer, 7 order, 8 cycling (1 or 0), 9 pointer inside (1 or 0). All are read as they stand (RULE-7); 9 is input state.
- **Reason and source.** DEC-6522 item 8 names these as local state.
- **Verification.** Tests after each animation operation: the next event's condition reads the new state.

**RULE-27 [engine: neoteletext-rules; neoteletext-browser]. Space 5: a sound on an audio channel.**
- **Statement.** `a` is the audio channel, 0 to 3; `b` the property:

| `b` | Name | Value |
|---|---|---|
| 0 | `playing` | 1 while any sound plays on the channel in this view, else 0 |
| 1 | `level` | the channel's output level over the last tick, 0 to 255 (RULE-32) |
| 2 | `handle` | the handle, 0 to 255, of the sound playing; −1 when none |
| 3 | `gain` | the channel's gain as last commanded, 0 to 100 |
| 4 | `local` | 1 while the sound playing is a local sound (RULE-60), else 0 |

- A sound is addressed as the program protocol addresses a playing sound: by the audio channel it plays on, and it is told apart by its handle. The rule table has no other name for a sound.
- **Reason and source.** DEC-6522 items 4 and 6.
- **Verification.** Browser tests with a scripted sound helper: each property after a play, a gain and a stop.

**RULE-28 [engine: neoteletext-rules, neoteletext-audio-instruments; neoteletext-browser]. Space 6: a synthesizer's state.**
- **Statement.** `a` is the audio channel, 0 to 3. `b` names the family the rule expects: its high byte the family's codec code of the audio profile (12 the synth6581 family, 13 synth7, 14 the synth106 family, 15 synthD, 16 the synth53 family, 17 synth8, 18 synth80; the engine's `Codec::code`) and its low byte the variant (0, or 1 for synth8580, synth60 and synth52, 2 for synth51, as the OBJECT record's variant and chip tags choose). `c` has the part's MIDI channel less one (0 to 15) in its high byte and the class in its low byte; `d` is the index within the class:

| Class | Name | Index `d` | Value |
|---|---|---|---|
| 0 | `program` | 0 | the part's program, 0 to 127 |
| 1 | `notes` | 0 | how many of the part's keys are down, 0 to 128 |
| 2 | `note` | key 0 to 127 | 1 while that key is down on the part, else 0 |
| 3 | `velocity` | key 0 to 127 | the velocity of that key's note on, 1 to 127; 0 while it is up |
| 4 | `field` | the family's parameter number (appendix A) | that patch field's present value on the part, on the field's own integer scale |
| 5 | `envelope_stage` | 0 | of the part's newest voice: 0 idle, 1 attack, 2 decay, 3 sustain, 4 release (RULE-31) |
| 6 | `envelope_level` | 0 | of the same voice's amplitude envelope, 0 to 255 (RULE-31) |
| 7 | `voices` | 0 | how many of the instrument's voices are not idle, 0 to the family's voice count |
| 8 | `controller` | controller 0 to 127 | the last value of that controller on the part, 0 to 127 (0 before any) |
| 9 | `bend` | 0 | the part's pitch bend, 0 to 16,383, 8,192 at rest |

- When the sound playing on the audio channel is not of the named family and variant, or none plays, every class reads 0.
- For the synth6581 family, which is programmed by register writes and has no notes (synth6581-synth8580.md), classes 0 to 3, 8 and 9 read 0; class 4's index is the register's ASID identifier, 0 to 27 (appendix A.1), and its value the register's last written byte; classes 5 and 6 take the voice, 1 to 3, as the part (high byte of `c` 0 to 2).
- **Reason and source.** DEC-6522 items 4 and 6 (the owner: "evaluations of synth property values with a set of common operators"). The fields are the named, typed fields the program protocol already gives each family's patch (DEC-6462), so nothing is named twice.
- **Verification.** For each family, a test in `neoteletext-audio-instruments` reads every parameter of appendix A after setting it by its control message; browser tests of `note`, `notes` and `program` after `LOCAL_MIDI` commands.

**RULE-116 [engine: neoteletext-rules]. Space 7: the firing.**
- **Statement.** `a` is the property; `b`, `c`, `d` are 0:

| `a` | Name | Value |
|---|---|---|
| 0 | `key` | the code of the key whose event fired the rule: its Unicode scalar value, or its functional code (RULE-10); 0 when no key event did |
| 1 | `target` | the number of the control, object or rectangle the pointer event that fired the rule was inside, for a rule whose trigger named one or "any"; 0 otherwise |
| 2 | `row` | the place, from 0, of the firing row within the rule's rows; 0 without rows |
| 3 | `cue` | the number of the cue that fired the rule; 0 otherwise |
| 4 | `p` | the row parameter in force (RULE-105); 0 when none |
| 5 to 7 | — | Withdrawn: the second form's `p1` to `p3` (DEC-6635 item 8); refused, never reused |

- In a condition these are the values of the event and row being matched. In a command they are those of the run's firing; a nested run has its caller's. A run a sequence makes has the `p` that was held for it and 0 for `key`, `target`, `row` and `cue`; a run of a command the server sent has 0 for all. A page that needs the key later stores it: `set v5` to the firing's `key`.
- **Reason and source.** DEC-6587 item 7: `set` to "a readable value such as … the key that fired the rule".
- **Verification.** Tests: each property in a condition and in a `set`; zeros in a sequence's step; a nested run reads its caller's.

**RULE-117 [engine: neoteletext-rules]. Space 8: sequences.**
- **Statement.** `a` is the sequence, 0 to 7; `b` the property: 0 running (1 or 0), 1 the passes completed since its start (0 to 2,147,483,647), 2 its position in ticks within the pass (0 while not running), 3 waiting (1 while a start is waiting for its start tick, RULE-103, else 0).
- **Verification.** Covered by RULE-103's tests.

**RULE-29 [engine: neoteletext-audio-instruments]. Each family publishes one parameter table.**
- **Statement.** Each family's interface module (`synth7/interface.rs` and the others, built by the feature `interface` alone) MUST publish a constant table `PARAMETERS` of its readable patch fields in the order of appendix A — each entry a name, a least and a greatest value — and a function that reads a field's present value for a part from the family's tracker (the state a sender tracks, MIDI-94). The parameter number is the entry's place in the table, from 0. The table's names, order and ranges MUST be those of the program protocol's `Synth7Parameter`, `Synth106Parameter`, `Synth60Parameter`, `SynthDParameter`, `Synth53Parameter`, `Synth8Parameter` and `Synth80Parameter` types of the server's schema, variant by variant in schema order, which a test of the server asserts; a field whose schema type is an enumeration reads as the ordinal of its value in schema order from 0, and a boolean as 0 or 1. A parameter number is never reused or reordered; new fields are added at the end.
- **Reason and source.** One table serves the server (which turns a field's name into its number and refuses an unknown one) and the receiver (which reads it); DEC-6462.
- **Verification.** The server's test that schema and tables agree; a test that appendix A of this document is the tables' printout (the engine's `cargo xtask` prints it and the commit gate compares).

**RULE-30 [neoteletext-browser]. Where each synthesizer value is read.**
- **Statement.** The decoder MUST read classes 0 to 4, 8 and 9 from the family's tracker that it keeps for the sound: for a local sound, a tracker fed with the sound's setup events (RULE-60) and then with every `LOCAL_MIDI` command in order, so no question is put to the sound helper; for a sound whose blocks the server sends, the tracker of the instrument the decoder renders it with, at the position rendered, which is ahead of what is heard by up to the stream's buffer (`STREAM_TARGET_MS`, 400 milliseconds) and is approximate by that much. Classes 5 to 7 of a local sound are metered by the sound helper (RULE-33); of a server-timed sound they are read from the decoder's instrument at the position rendered.
- **Reason and source.** DEC-6522 item 4: the owner accepted that reading may "cost CPU and be approximate". Tracking in the decoder costs nothing per tick and needs no message.
- **Verification.** Browser tests: `note[60]` reads 1 in the next handling after a note on, with no helper message exchanged.

**RULE-31 [engine: neoteletext-audio-instruments]. Envelope position.**
- **Statement.** The trait `Instrument` MUST have a method `meter(&self, part: u8) -> Meter`, with a default that answers idle and zero, giving for the part's most recently started voice that is not idle (else idle): the stage 0 to 4 of RULE-28, the amplitude envelope's present value scaled linearly to 0 to 255 of the envelope's full scale, and the count of voices not idle. The amplitude envelope is: synth106, synth60, synth53, synth52, synth51, synth8 and synthD, the voice's loudness (VCA) envelope; synth80, channel I's amplifier envelope of the voice; synth7, the envelope generator of operator 1 of the newest note, operator 1 being a carrier in all 32 algorithms; the synth6581 family, the envelope generator of the voice named as the part, its 8-bit counter as it stands. Stages a family does not have are never reported (synth7's four rates map to attack for the first, decay for the second and third while a key is down, sustain when level 3 is reached, release after key off).
- **Reason and source.** DEC-6522 items 4 and 6 ("a voice's envelope position").
- **Verification.** For each family a test: after a note on, the stage passes 1, 2, 3 in order and 4 after note off, and the level is 0 when idle.

**RULE-32 [engine: neoteletext-audio-mix; neoteletext-browser]. `level`.**
- **Statement.** The sound helper MUST meter, for each watched audio channel of each watched view, the largest absolute sample value of that channel's voice after its gain, ramp and ducking and before the master volume and the mute, over the output frames it rendered since its last report, and report `level = min(255, peak ÷ 128)` where peak is on the 16-bit scale 0 to 32,768. The scale is linear: 255 is full scale, 128 is −6 decibels, 64 is −12, 32 is −18, 16 is −24, 8 is −30, 4 is −36. The engine mixer (`neoteletext-audio-mix`) MUST provide the per-voice peak since last asked; nothing is metered for a channel no rule watches.
- **Reason and source.** DEC-6522 item 4: "we only need to capture state 1/60th of a second and only on what the commands say they want to watch". Before the master volume and mute, so that a page's meters show what the page plays, and so that a rule cannot learn the viewer's volume setting.
- **Verification.** A mixer test with a sine at each of the listed levels; a browser test that an unwatched channel costs no meter call.

**RULE-33 [neoteletext-browser]. The message flow of metering.**
- **Statement.** Metering MUST work through these messages and no others:
  1. When the decoder has decoded a table for a page that is open, it sends the trusted core a **watch list** with the page's key: at most `MAX_WATCHED` slots, each an audio channel (0 to 3) and a kind (1 `level`; 2 `envelope_stage`, 3 `envelope_level`, 4 `voices`, each with a part 0 to 15) — exactly the distinct metered values the table's conditions and its groups' `REPORT` and `VARIABLE` commands name. A page with none sends none. When the page is paused or closed, its connection ends, or its table is removed, the decoder sends an empty list.
  2. The trusted core checks the list's bounds and that the page is open in that view, and passes it to the sound helper tagged with the view's channel number, replacing that view's earlier list (`ToSound::Watch`).
  3. The sound helper, after rendering each device buffer, when at least one sixtieth of a second of output frames has been rendered since its last report and a list is in force, sends one report for each view with a list: the slots' values in the list's order, each one byte (`FromSound::Metered`). While the output device is stopped it sends one report of zeros and then none.
  4. The trusted core checks the report's length against the list it passed and gives it to that view's decoder (`ToDecoder::Metered`).
  5. The decoder gives the evaluator each report between handlings, as it arrives (RULE-7), and the newest is what every condition and command then reads. A slot not yet reported reads 0.
- The sound helper is never told a condition, a threshold or a rule; it meters and reports. Reports follow the audio device's clock, so a value read is up to one device buffer and one sixtieth of a second old.
- **Reason and source.** DEC-6522 item 4. The trusted core stays the only path between helpers (the browser's architecture, section 6.2).
- **Verification.** Tests with the scripted helper: the list sent for a table of three watched values; a report of the wrong length dropped by the core; no report while no list is in force; the level seen by a `becomes` rule within two ticks of the helper's report.

## 7. The program protocol: version 15

The program protocol is the line-by-line JSON a channel's program exchanges with the server (the server's `crates/teletext-runtime/src/protocol.rs`; its generated schema is the contract, DEC-6462). The first form made version 14 (`PROTOCOL: u32 = 14`, `protocol/schema-14.json`, on the server's branch `protocol-14`, never deployed). This document and animation.md make version 15. The conventions are unchanged: every message is one object with a `type`; names are snake_case; a page number is a string of three hexadecimal digits (`PageNumber`) and a sub-code a string of four (`SubCode`); an audience is `"all"` or a list of connection numbers (`Connections`); unknown fields are refused; what the schema cannot say is checked by `protocol/check.rs` and answered by a typed `refused`. **Every message of this section that concerns a page carries both `page` and `sub`** (RULE-112); an audience of `"all"` means every connection that has that page selected at that moment.

**RULE-34 [neoteletext-app-server]. Protocol 15.**
- **Statement.** The server MUST raise `PROTOCOL` to 15 and generate `protocol/schema-15.json` from its Rust types, deleting `schema-14.json` in the same change; its `start` message says `"protocol": 15`. It MUST carry the program messages `rules` and `query_state` in their second form, the new program messages `local_midi`, `variable`, `timer`, `report`, `run` and `sequence` (RULE-114), the server messages `input`, `rule_event`, `page_state` and `rules_fault` in their second form (RULE-37, RULE-38, RULE-48), the local sound kinds of RULE-61, the `cue` event and the `cues` list of RULE-109, and the messages animation.md defines. A program that speaks another version is refused as today. Both kits take the schema by copy pinned to the server's commit.
- **Reason and source.** DEC-6522 item 9; DEC-6462; DEC-6587 (the messages change shape, so the number is raised, REQ-2215).
- **Verification.** The server's schema test (the committed schema is the generated one); both kits' pin checks.

**RULE-35 [neoteletext-app-server]. The `rules` message.**
- **Statement.** A program gives a page its table with:

```json
{"type":"rules","connections":[7],"page":"101","sub":"0001","table":{
  "rects":[{"name":"pad","x":40,"y":300,"width":200,"height":100}],
  "rows":{"keys":[60,62]},
  "groups":[
    {"name":"note_on","commands":[
      {"type":"local_midi","channel":0,"message":{"event":"note_on","channel":1,"key":{"plus":0,"row":"p"},"velocity":100}},
      {"type":"animate","ops":[{"action":"look","target":{"object":{"plus":41,"row":"p"}},"look":"pressed"}]}]},
    {"name":"note_off","commands":[
      {"type":"local_midi","channel":0,"message":{"event":"note_off","channel":1,"key":{"plus":0,"row":"p"},"velocity":64}},
      {"type":"animate","ops":[{"action":"look","target":{"object":{"plus":41,"row":"p"}},"look":"normal"}]}]}],
  "sequences":[{"name":"pulse","length":30,"repeat":0,"steps":[{"tick":0,"run":"note_on"},{"tick":15,"run":"note_off"}]}],
  "rules":[
    {"name":"down","on":[{"event":"key","keys":[{"physical":"a"},{"physical":"s"}],"by_row":true},{"event":"press","target":{"object":{"plus":41,"row":"p"}},"button":0}],
     "when":null,"rows":"keys","run":"note_on"},
    {"name":"up","on":[{"event":"key_up","keys":[{"physical":"a"},{"physical":"s"}],"by_row":true},{"event":"release","target":{"object":{"plus":41,"row":"p"}},"button":0}],
     "rows":"keys","run":"note_off"},
    {"name":"typed","on":{"event":"key","keys":"any","repeat":true},"do":[{"type":"report"}]}]}}
```

- `table` is the table, or `null`, which removes the page's table for those connections (and, where the channel's default applies, RULE-53, puts the default back). In a table, `rules` is required (it may be empty); `rects`, `rows` (an object of named row sets, each a list of rows), `groups` and `sequences` default to empty; each is held to its limit of RULE-57 (`MAX_RULES`, `MAX_RECTS`, `MAX_ROWS` rows in all, `MAX_GROUPS`, `MAX_SEQUENCES`). There is no `variables`, `timers` or `subpages` member: the sixteen variables are written `"v0"` to `"v15"` and the timers `"t0"` to `"t7"` and `"page"` wherever one is named.
- **A rule** has `name` and `on` (required); `when` (a condition or `null`, the default); `rows` (the name of a row set, or absent); and exactly one of `run` (the name of a group) and `do` (a list of 1 to `MAX_GROUP_COMMANDS` commands, which the server makes into an unnamed group of the table; two rules whose `do` lists are equal share one group). `echo` (boolean, default `false`) means "after the group, a `report` of the firing": the server appends that command to the rule's `do` group, or for a `run` makes an unnamed group that runs the named one and then reports. Unnamed groups count toward `MAX_GROUPS`.
- **`on`** is one trigger or a list of 1 to `MAX_TRIGGERS_PER_RULE` (RULE-107). A trigger is an object tagged by `event`:

| `event` | Other fields |
|---|---|
| `key` | `keys` (a key set); `repeat` (boolean, default `false`); `by_row` (boolean, default `false`); `mods` (`{"mask":0..255,"value":0..255}`, default both 0) |
| `key_up` | `keys`; `by_row`; `mods` |
| `press`, `release` | `target`; `button` (0, 1, 2 or `"any"`, default `"any"`) |
| `enter`, `leave`, `wheel` | `target` |
| `move` | `target`; `held` (boolean, default `false`) |
| `open`, `close`, `text`, `focus`, `blur` | none |
| `becomes` | none: the rule's `when` is its condition and MUST NOT be `null`; it is the rule's only trigger |
| `every`, `after` | `ticks` (1 to `MAX_TIMER_TICKS`); `timer` (`"t0"` to `"t7"`, or `"page"`, the default) |
| `cue` | `channel` (0 to 3); `number` (0 to `MAX_CUE`, or `"any"`, the default) |

- A **key set** is `"any"` or a list of 1 to `MAX_KEYS_PER_TRIGGER` keys, each `{"char":"a"}` (one Unicode scalar value, a letter in lower case), `{"name":"Enter"}` (a `KeyName` of the schema) or `{"physical":"a"}` (RULE-10). With `by_row` true, which only a rule with `rows` may have, the list has exactly as many keys as the rule's row set has rows, and the row at each place is matched by the key at the same place (RULE-105). The events `held`, `double`, `press_held` and `double_press` are withdrawn (DEC-6635 item 7) and refused (`wrong_type`).
- A **target** is `"page"`, `{"control":n}`, `{"object":n}`, `{"rect":"name"}`, or in the pointer triggers `{"control":"any"}` or `{"object":"any"}` (RULE-12); in a rule with `rows` a trigger's `n`, and in a group's `animate` operation any target's `n`, MAY be `{"row":"p"}`, or in an operation `{"fired":"target"}` or `{"fired":"row"}`, each optionally with `"plus":k`, `k` a signed 16-bit integer in a trigger.
- **A row** is its one parameter `p`: a signed 32-bit integer, or a key written as in a key set (`{"char":…}`, `{"name":…}`, `{"physical":…}`), which stands for that key's code (DEC-6635 item 8; the second form's objects of `p0` to `p3` are withdrawn).
- **`when`** is a condition: `{"and":[c, ...]}`, `{"or":[c, ...]}`, `{"not":c}`, `{"read":v,"op":"==","value":n}` with `op` one of `==`, `!=`, `<`, `<=`, `>`, `>=` and `value` an integer or `{"plus":k,"row":"p"}`, `{"read":v,"in_range":[low,high]}`, `{"read":v,"in_set":[n, ...]}`, `{"overlaps":[t,t]}` or `{"inside":[t,t]}` (RULE-18).
- A **value** `v` is an object tagged by `of`:

| `of` | Other fields | Space |
|---|---|---|
| `variable` | `variable` (`"v0"` to `"v15"`) | 1 |
| `key` | `key` (one key, as in a key set) | 2 |
| `button` | `button` (0 to 2) | 2 |
| `pointer` | `property`: `over`, `x`, `y` | 2 |
| `keys_down` | none | 2 |
| `timer` | `timer` (`"t0"` to `"t7"` or `"page"`); `property`: `running`, `elapsed`, `phase`; and with `phase` a `period` (1 to `MAX_TIMER_TICKS`) | 3 |
| `target` | `target`; `property`: `exists`, `shown`, `frame`, `x`, `y`, `look`, `layer`, `order`, `cycling`, `inside` | 4 |
| `sound` | `channel` (0 to 3); `property`: `playing`, `level`, `handle`, `gain`, `local` | 5 |
| `synth` | `channel` (0 to 3); `family`; `part` (1 to 16; for the synth6581 family the voice, 1 to 3); `property`: `program`, `notes`, `note`, `velocity`, `field`, `envelope_stage`, `envelope_level`, `voices`, `controller`, `bend`; and with `note` or `velocity` a `key` (0 to 127), with `field` a `field` (a name of appendix A for the family), with `controller` a `controller` (0 to 127) | 6 |
| `fired` | `property`: `key`, `target`, `row`, `cue`, `p` | 7 |
| `sequence` | `sequence` (a sequence's name); `property`: `running`, `passes`, `position`, `waiting` | 8 |

- **A group** is `{"name":…,"commands":[…]}` with 1 to `MAX_GROUP_COMMANDS` commands. **A command is a program message without its `connections`, `page` and `sub`**, which the table supplies: one of the `sound` kinds `play`, `stop` and `gain` (as version 14 has them, `play` without `page`, `after` false), `local_midi`, `animate`, `sprites`, `naplps_objects`, `regis_links`, `regis_cursor`, `naplps_links`, `naplps_cursor`, `variable`, `timer`, `report`, `run` and `sequence` (RULE-114; animation.md ANIM-21; the four picture messages by renderer parity PAR-20, written as one whole `DRAWING_LINKS` or a `REGIS_CURSOR`, RULE-119). Any other message type in a group is refused (`invalid_group`). In a group, and nowhere else, a field that RULE-106 lists MAY be given as an **amount** in place of an integer: `{"plus":k,"variable":"v3"}`, `{"plus":k,"row":"p"}` or `{"plus":k,"fired":"key"}` (`key`, `target`, `row`, `cue` or `p`; `{"fired":"p"}` is the row's `p`, binding source `0x20`, since the firing's `p` and the row's are one value, RULE-116), `plus` defaulting to 0. As a `variable` command's value, `{"plus":k,"row":"p"}` is operand kind 3 with the firing's property `p` (RULE-99). An operation's target number given as an amount takes a `plus` of 0 to 65,535, since the `ANIMATE` record's target field is unsigned; a negative `plus` there is refused (`invalid_group`), while a trigger's target takes a signed 16-bit `plus` (RULE-43) (the server's DEC-6654 items 4 and 5). The fields are: a `local_midi` message's `key`, `velocity`, `controller`, `value` and `program`; `play`'s and `gain`'s `gain` and `fade_ms`, and `stop`'s `fade_ms`; and an `animate` operation's `x`, `y`, `frame`, `look` (as its number 0 to 3), `order` and `period`.
- **A sequence** is `{"name":…,"length":n,"repeat":r,"steps":[{"tick":k,"run":"group"}, …]}` (RULE-103): `length` 1 to `MAX_SEQUENCE_TICKS`, `repeat` 0 (until stopped) or 1 to `MAX_SEQUENCE_REPEAT`, 1 to `MAX_SEQUENCE_STEPS` steps in ascending `tick` below `length`.
- **Reason and source.** DEC-6522 item 9; DEC-6462 (the server is where the meaning lives; the kits send this shape and hold no logic), which is why `do` and `echo` are made into groups by the server and not, as DEC-6587 item 9 first proposed, by each kit (section 15, item 36); DEC-6587 items 1, 5 and 7; DEC-6635 items 6 to 8.
- **Verification.** The server's protocol tests accept each worked example of section 7.5 and refuse each fault of RULE-39 with the stated rule and path.

**RULE-114 [neoteletext-app-server; engine: neoteletext-web]. The commands as program messages.**
- **Statement.** Each command a group may hold is also a message a program may send directly, for the connections named that have the page selected; the server encodes the same record either way, with one function. Beside `sound` (`play`, `stop`, `gain`) and animation.md's `animate`, `sprites` and `naplps_objects`, protocol 15 adds:

```json
{"type":"local_midi","connections":[7],"page":"101","sub":"0001","channel":0,
 "message":{"event":"note_on","channel":1,"key":60,"velocity":100}}
{"type":"variable","connections":[7],"page":"101","sub":"0001","op":"set","variable":"v0","value":4}
{"type":"variable","connections":[7],"page":"101","sub":"0001","op":"add","variable":"v0","value":{"plus":0,"variable":"v1"}}
{"type":"variable","connections":[7],"page":"101","sub":"0001","op":"set","variable":"v2","value":{"read":{"of":"sound","channel":0,"property":"level"}}}
{"type":"variable","connections":[7],"page":"101","sub":"0001","op":"wrap","variable":"v0","low":0,"high":3}
{"type":"variable","connections":[7],"page":"101","sub":"0001","op":"clear","variable":"all"}
{"type":"timer","connections":[7],"page":"101","sub":"0001","op":"start","timer":"t0"}
{"type":"report","connections":[7],"page":"101","sub":"0001","value":{"of":"variable","variable":"v0"}}
{"type":"run","connections":[7],"page":"101","sub":"0001","group":"flash"}
{"type":"sequence","connections":[7],"page":"101","sub":"0001","op":"start","sequence":"pulse","at":null}
{"type":"sequence","connections":[7],"page":"101","sub":"0001","op":"start","sequence":"flash_once","at":{"tick":5400}}
{"type":"sequence","connections":[7],"page":"101","sub":"0001","op":"start","sequence":"pulse","at":{"beat":{"timer":"t0","ticks":30}}}
{"type":"sequence","connections":[7],"page":"101","sub":"0001","op":"stop","sequence":null}
```

- `local_midi`'s `message` is one of `{"event":"note_on","channel":1..16,"key":0..127,"velocity":0..127}`, `{"event":"note_off", …}` with the same fields, `{"event":"control_change","channel","controller":0..127,"value":0..127}`, `{"event":"program_change","channel","program":0..127}`, `{"event":"pitch_bend","channel","value":0..16383}` — the schema's event shapes for a family without `time_us`. `variable`'s `op` is `set`, `inc`, `dec`, `add`, `sub`, `toggle`, `min`, `max`, `wrap` or `clear`; `variable` is `"v0"` to `"v15"`, or `"all"` with `clear`; `value` (for `set`, `add`, `sub`, `min`, `max`) is an integer, `{"plus":k,"variable":"vN"}`, `{"plus":k,"fired":…}` (any `fired` property, in a group only), or for `set` alone `{"read":v}`; `wrap` takes `low` and `high`. `timer`'s `op` is `start` or `stop`. `report`'s `value` is a value, or `null` (the default, and allowed only in a group) for the firing. `run` names a group and has no `at`: the second form's `at` is withdrawn (DEC-6635 item 6), and a `run` with `at` is refused (`unknown_field`). `sequence`'s `sequence` is a name, or `null` with `stop` for all; with `start` its `at` is `null` (the default: the next tick), `{"tick":n}` (a page tick) or `{"beat":{"timer":…,"ticks":n}}` (the timer's next expiry of that period) (RULE-103), and with `stop` it MUST be absent or `null`.
- A `run` or `sequence` sent directly names a group or sequence of the table the server last sent that connection for that page, which the server keeps the names of (RULE-36, RULE-40); an unknown name is refused (`unknown_name`) for that connection: the message goes to each connection named that has the page selected and whose table in force has the name, and one `refused` message names the others (the server's DEC-6654 item 6). A message for a page a connection does not have selected is not sent to it.
- **Reason and source.** DEC-6587 item 1: "the rule table's own housekeeping … is therefore made of protocol commands too, and the server may send any of them directly as well."
- **Verification.** Server tests: each example's record equals the same command's bytes inside a group; an amount outside a group refused (`invalid_command`); a `report` of the firing sent directly refused.

**RULE-36 [neoteletext-app-server]. Names exist only between a program and the server.**
- **Statement.** Rule, group, sequence, row-set and rectangle names MUST match `[a-z][a-z0-9_]{0,31}` and be distinct within their kind in a table; `page` is not allowed as a rectangle's name. The server turns each name into its number (its place in the table's list, from 0; unnamed groups after the named) when it encodes the table, and turns numbers back into names in every message it gives the program. No name is sent to a receiver. Variables and timers have no names: `v0` to `v15` and `t0` to `t7` are the same in every message of every page (DEC-6587 item 4); a program that wants `octave` for `v0` writes that in its own code.
- **Reason and source.** A program's author reads names; the record carries numbers so that the receiver parses no text (DEC-6522 item 9).
- **Verification.** Server tests: a duplicate and an unknown name refused; an event's rule number reported by its name.

**RULE-37 [neoteletext-app-server]. What `report` gives the program.**
- **Statement.** When a receiver reports (RULE-46), the server MUST give the program, for the connection it came from:
  - for a report of a firing with an input event, the `input` message unchanged in its `event` shape (`key`, `mouse`, `wheel`, `touch`, `pick`, `hover`, `drawing_hover`, `text`, `compose`, `paste`, `focus`, `blur`), with the fields `rule`, the name of the rule that fired; `row`, the place of the firing row within the rule's row set, or `null`; `tick`, the page tick the event belongs to; and `target`, the target the pointer was inside for a pointer trigger whose rule named a control, an object or a rectangle, else `null`. A pointer event on a page drawn by the ReGIS renderer is followed, as before, by the `input` message of its `pick`, with the same `rule`, `row` and `tick`.

    ```json
    {"type":"input","connection":7,"page":"101","sub":"0001","lost":false,"rule":"typed","row":null,"tick":412,"target":null,
     "event":{"kind":"key","action":"press","key":"a","base":null,"mods":0,"text":"a"}}
    ```
  - for a report of a firing with no event, and for a report of a value, the message `rule_event`, whose `rule` is `null` when the run was not made by a rule (a command the server sent, or a sequence it started):

    ```json
    {"type":"rule_event","connection":7,"page":"101","sub":"0001","rule":"hot","row":null,"tick":9031,"event":{"kind":"fired"}}
    {"type":"rule_event","connection":7,"page":"101","sub":"0001","rule":null,"row":null,"tick":9031,
     "event":{"kind":"value","read":{"of":"variable","variable":"v0"},"value":5}}
    ```
- **The table that names a report.** A report's rule, values and targets are turned into names with the names of the table the connection was sent at the generation the report carries; the server keeps the names of the last four tables it sent a connection while that connection stands, for this. A report of a generation the connection was never sent, or of a rule or value that table does not have, is given to no program and is counted with stale input. A report with no input event (a firing, or a value) is given to the program whatever the connection has selected since, so that a `close` rule's report arrives; an input event stamped with a page that is no longer the connection's selection is dropped, as in version 13.
- **A release the server itself gives.** When a connection closes, or its selection changes, while a key, a button or a contact is held, the server gives the program the release marked `lost` (the engine's REQ-207) only for a press that some rule reported, with that press's `rule`, `row` and `tick`, so that a program still hears nothing no rule asked for.
- A program therefore receives an `input` message only for an event some rule of the page's table reported. Events arrive in the order the receiver sent them.
- **Reason and source.** DEC-6522 item 8 (a) and (b); keeping `input`'s shape means every program's handling of input is unchanged.
- **Verification.** Server tests: each input kind carried in a RULE_EVENT gives the same `event` object version 13 gave for the bare event; the `rule_event` shapes; a row's place reported.

**RULE-38 [neoteletext-app-server]. The state query and its answer.**
- **Statement.** A program asks one connection for one page's local state with `{"type":"query_state","connection":7,"page":"101","sub":"0001","request":42}`, where `request` is 1 to 4,294,967,295 and is the program's own number for the question. The server sends the connection a RULES_QUERY record (RULE-47) when that connection has the page selected, and otherwise refuses with `wrong_page`. It MUST refuse a second query for the same connection and page within one second with `too_frequent`. The receiver answers once (RULE-47) and the server gives the program:

```json
{"type":"page_state","connection":7,"page":"101","sub":"0001","request":42,"tick":9120,"table":true,
 "variables":[4,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
 "timers":{"t0":{"running":true,"elapsed":18}},
 "sequences":{"pulse":{"running":true,"waiting":false,"passes":3,"position":12}},
 "targets":[{"target":{"object":301},"exists":true,"shown":true,"look":"normal","frame":0,"x":700,"y":380,"layer":2,"order":0,"cycling":false}],
 "values":[{"read":{"of":"sound","channel":0,"property":"level"},"value":41}]}
```

- `variables` is always the sixteen values, `v0` first. `timers` lists the timers that are running; `sequences` every sequence of the table by name, `waiting` true while its start waits for its start tick. The second form's `armed` count is withdrawn with armed runs (DEC-6635 item 6). `table` is `false`, and the lists empty and the variables zero, when the page has no table in that view. `targets` holds every control and object the table names by a constant, in the order first named; `values` every distinct value the table reads, as they stand when the query is handled (RULE-47); `tick` is the page tick the query was handled in. When no answer comes within 10 seconds, or the connection ends or leaves the page first, the server MUST give the program a `refused` message with the rule `not_answered` and the query's `request`.
- The query is for a program that wants to read a page's values, and for debugging. It is **not** a means of resynchronising: after a disconnect there is nothing to read (RULE-111).
- **Reason and source.** DEC-6522 item 8 (c), as DEC-6587 item 9 keeps it.
- **Verification.** Server tests: the answer's fields from a recorded PAGE_STATE; the rate refusal; the timeout refusal.

**RULE-39 [neoteletext-app-server]. Refusals.**
- **Statement.** A faulty message of this section MUST be refused whole with the `refused` message (`path`, `rule`, `detail`, `message`), and nothing of it sent to any receiver. Beside the existing rules (`unknown_field`, `missing_field`, `wrong_type`, `out_of_range`, `too_long`, `duplicate`, `not_in_index`, `unknown_connection`, `wrong_page`), the schema's `Rule` has:

| `rule` | When |
|---|---|
| `rules_over_limit` | the table exceeds a limit of section 9 that the schema cannot state: a condition's terms, nodes or levels; the table's distinct values or targets; the rows, or the groups counting the unnamed; the groups' bytes; a command's bytes; the rule-and-row pairs; an encoded table over `MAX_TABLE_BYTES`. `detail` names the limit's constant and its value (REQ-6608) |
| `invalid_rules` | a shape fault the schema cannot state: a rule with both `run` and `do` or neither; a `becomes` rule without a `when` or with a second trigger; `first` above `last`; `low` above `high`; "any" where a single target is required; a `page` target in an operation; a `{"row":…}` or `by_row` in a rule without `rows`; a `by_row` key set whose count is not the rule's row count; a row whose `p` gives a target number out of range where a trigger uses it; a sequence's steps out of order or beyond its length; a `sequence` stop with an `at`; a `sequence` start without a sequence; a timer `phase` without a `period`, or a `period` without `phase` (DEC-6654 item 3) |
| `invalid_group` | a group fault: a message type RULE-119 forbids; a `play` with `page`, `after` true or for the whole service; an amount in a field that takes none, or a variable as a target's number; groups that run each other in a ring; nesting deeper than `MAX_GROUP_DEPTH`; a run that would apply more than `MAX_RUN_COMMANDS` commands; a negative `plus` on an operation's target number; a `variable` command whose operation is paired with an operand it does not take, or whose variable is `"all"` with an operation other than `clear` (DEC-6654 item 3). `detail` names the group and the fault |
| `invalid_command` | a command sent directly that is allowed only in a group (an amount, a `fired` value, a `report` of the firing), or a `variable` command sent directly whose operation and operand do not pair (DEC-6654 item 3) |
| `unknown_name` | a rule, group, sequence, row-set or rectangle name that the table does not have |
| `duplicate_name` | a name declared twice within its kind |
| `unknown_parameter` | a `field` that the named family's table (appendix A) does not have |
| `too_frequent` | a `query_state` within one second of the last for that connection and page |
| `not_answered` | a `query_state` that got no answer (RULE-38) |

- The existing rules answer the faults this table does not name: `page` as a rectangle's name is `reserved`; a key name the engine's table of keys does not have is `not_listed`; a `synth` value without the `key`, `field` or `controller` its property needs is `missing_field`, and with one its property does not use is `invalid_rules`; a letter of a `char` or `physical` key written in upper case is `invalid_rules`; a list longer than the schema states is `too_long`; a name that does not match RULE-36's pattern is `wrong_type`.
- The server MUST also check every table with `neoteletext_rules::check` — the same code the receiver decodes with — after encoding it, and refuse with `invalid_rules` anything that code refuses, so that no receiver is ever sent a table it would refuse (RULE-59).
- **Reason and source.** DEC-6522 item 10: "refused whole, and the refusal is reported, never silently ignored"; the server's existing practice for ReGIS (`invalid_regis`).
- **Verification.** One server test for each row, asserting `rule` and `path`; the kits' `server-rules` tests hold the kits to the same refusals.

**RULE-40 [neoteletext-app-server]. The server sends a table when it is given one, keeps none for later, and drops everything at a disconnect.**
- **Statement.** The server MUST send a connection a page's table at once when the program gives it, to each connection of the audience that has that page (page number and sub-code) selected at that moment, and to no other. It MUST NOT keep a table, an animation state, sprites, objects or a sheet to send a viewer who selects the page later, comes back to it or reconnects: a program is told of every selection (`selected`, with its `page` and `sub`) and sends the page afresh then, its table with it, and that is all a late or returning viewer is sent (RULE-111). Going from one sub-code to another is a selection like any other. For each connection the server keeps only: the page it has selected; whether a table is in place there, and the names of that table (for RULE-36 and RULE-114); the default table's use (RULE-53); a generation counter; and, so that a sheet can be checked whole, the sheet stream it is sending for the page selected (animation.md ANIM-17), dropped when the connection leaves the page and never sent to a later viewer (the server's DEC-6654 item 9). Each RULES record sent on a connection carries a generation one above the last sent on that connection, starting at 1 and passing from 65,535 to 1. At a selection the server sends first, before the program is told, the channel's default table (RULE-53) or a RULES record that says the page has no table, so that the page starts from a known state; the program's own table then replaces it. A selection of the sub-code `3F7F` (a page number's first sub-page) does not yet name a page, so the server sends that record when the program's answer makes the sub-code known, before that sub-page (the server's DEC-6654 item 8).
- **Reason and source.** DEC-6587 item 3 (the owner: "after a disconnect i think EVERYTHING should be dropped and the page reloads") and item 9 ("a page's opening state is what the page sends"); DEC-6599 items 2 and 3. It replaces the first form's tables kept for 64 pages a connection.
- **Verification.** Server tests: a table to `"all"` reaches only the connections with that page and sub-code selected; a connection that selects the page later is sent the default or the empty record and nothing of an earlier `rules` message; a reconnecting viewer is sent nothing that was kept; the generation rises.

### 7.5 Worked examples

Each is a complete message the server accepts (`docs/rules-examples.jsonl` holds them one a line). The music player's whole table is in section 14.

**Example 1: a text field's keys are sent, and nothing else.**

```json
{"type":"rules","connections":"all","page":"120","sub":"0000","table":{"rules":[
  {"name":"typed","on":[{"event":"key","keys":"any","repeat":true},{"event":"text"}],"do":[{"type":"report"}]}]}}
```

**Example 2: a button that lights at once and tells the channel.** Control 3 takes its pressed look locally while it is held; the release is reported.

```json
{"type":"rules","connections":"all","page":"130","sub":"0000","table":{"rules":[
  {"name":"vote_down","on":{"event":"press","target":{"control":3},"button":0},
   "do":[{"type":"animate","ops":[{"action":"look","target":{"control":3},"look":"pressed"}]}]},
  {"name":"vote","on":{"event":"release","target":{"control":3},"button":0},"echo":true,
   "do":[{"type":"animate","ops":[{"action":"look","target":{"control":3},"look":"normal"}]}]}]}}
```

**Example 3: a counter held to a range, reported in the group that changes it.** The arrow keys change `v0` between 0 and 10, starting at 5; the channel is told the new value by the same group, because a `report` of a variable reads it as it stands when the report is applied (RULE-7).

```json
{"type":"rules","connections":"all","page":"140","sub":"0000","table":{
 "groups":[
  {"name":"up","commands":[{"type":"variable","op":"inc","variable":"v0"},{"type":"variable","op":"min","variable":"v0","value":10},
                           {"type":"report","value":{"of":"variable","variable":"v0"}}]},
  {"name":"down","commands":[{"type":"variable","op":"dec","variable":"v0"},{"type":"variable","op":"max","variable":"v0","value":0},
                             {"type":"report","value":{"of":"variable","variable":"v0"}}]}],
 "rules":[
  {"name":"start","on":{"event":"open"},"do":[{"type":"variable","op":"set","variable":"v0","value":5}]},
  {"name":"up","on":{"event":"key","keys":[{"name":"ArrowUp"}],"repeat":true},"run":"up"},
  {"name":"down","on":{"event":"key","keys":[{"name":"ArrowDown"}],"repeat":true},"run":"down"}]}}
```

**Example 4: a sprite that walks with the arrow keys, and a collision.** Object 10 moves 8 pixels a press while the key repeats; when it overlaps object 20 a sound plays, object 20 is hidden and the channel is told.

```json
{"type":"rules","connections":"all","page":"150","sub":"0000","table":{"rules":[
  {"name":"left","on":{"event":"key","keys":[{"name":"ArrowLeft"}],"repeat":true},
   "do":[{"type":"animate","ops":[{"action":"move","target":{"object":10},"x":-8,"y":0,"relative":true}]}]},
  {"name":"right","on":{"event":"key","keys":[{"name":"ArrowRight"}],"repeat":true},
   "do":[{"type":"animate","ops":[{"action":"move","target":{"object":10},"x":8,"y":0,"relative":true}]}]},
  {"name":"hit","on":{"event":"becomes"},"when":{"overlaps":[{"object":10},{"object":20}]},"echo":true,
   "do":[{"type":"sound","kind":"play","channel":1,"handle":5,"generation":1,"gain":100,"fade_ms":5,"duck":0,"loop":false,"after":false},
         {"type":"animate","ops":[{"action":"hide","target":{"object":20}}]}]}]}}
```

**Example 5: a blinking prompt and a timeout.** Object 7 cycles two frames every 30 ticks from opening; after ten seconds without a key the channel is told once.

```json
{"type":"rules","connections":"all","page":"160","sub":"0000","table":{"rules":[
  {"name":"start","on":{"event":"open"},
   "do":[{"type":"animate","ops":[{"action":"cycle","target":{"object":7},"first":0,"last":1,"period":30,"once":false}]},
         {"type":"timer","op":"start","timer":"t0"}]},
  {"name":"awake","on":{"event":"key","keys":"any"},"do":[{"type":"timer","op":"start","timer":"t0"}]},
  {"name":"asleep","on":{"event":"after","ticks":600,"timer":"t0"},"do":[{"type":"report"}]}]}}
```

**Example 6: a synthesizer's own state drives the picture, and a mode.** While any note is down on part 1 of the synth106 sound on audio channel 0, object 50 is shown. The key H sets mode 1 (help), in which the gate rules do nothing; Escape sets mode 0.

```json
{"type":"rules","connections":"all","page":"170","sub":"0000","table":{"rules":[
  {"name":"gate_on","on":{"event":"becomes"},
   "when":{"and":[{"read":{"of":"variable","variable":"v0"},"op":"==","value":0},
                  {"read":{"of":"synth","channel":0,"family":"synth106","part":1,"property":"notes"},"op":">","value":0}]},
   "do":[{"type":"animate","ops":[{"action":"show","target":{"object":50}}]}]},
  {"name":"gate_off","on":{"event":"becomes"},
   "when":{"or":[{"read":{"of":"variable","variable":"v0"},"op":"!=","value":0},
                 {"read":{"of":"synth","channel":0,"family":"synth106","part":1,"property":"notes"},"op":"==","value":0}]},
   "do":[{"type":"animate","ops":[{"action":"hide","target":{"object":50}}]}]},
  {"name":"help","on":{"event":"key","keys":[{"char":"h"}]},"do":[{"type":"variable","op":"set","variable":"v0","value":1}]},
  {"name":"back","on":{"event":"key","keys":[{"name":"Escape"}]},"do":[{"type":"variable","op":"set","variable":"v0","value":0}]},
  {"name":"open_filter","on":{"event":"wheel","target":{"object":51}},"do":[{"type":"report"}]}]}}
```

**Example 7: a sequence started on the next beat, a timer's phase, and a cue.** A metronome timer `t0` starts at opening. Space starts the sequence `fanfare` — three notes eight ticks apart, played twice — at the timer's next expiry of 30 ticks (RULE-103, start `beat`); the key B plays a click and tells the channel only when it is pressed within four ticks after a beat (RULE-25, the timer's `phase`). Each cue 1 of the song on audio channel 1 flashes object 9 by a sequence of its own. The server may also start `fanfare` for a page tick of its choosing with `{"type":"sequence",…,"op":"start","sequence":"fanfare","at":{"tick":5400}}` (RULE-114): a one-step or many-step sequence is how a run is armed for a tick.

```json
{"type":"rules","connections":"all","page":"180","sub":"0000","table":{
 "groups":[
  {"name":"n1","commands":[{"type":"local_midi","channel":0,"message":{"event":"note_on","channel":1,"key":60,"velocity":100}}]},
  {"name":"n2","commands":[{"type":"local_midi","channel":0,"message":{"event":"note_off","channel":1,"key":60,"velocity":64}},
                           {"type":"local_midi","channel":0,"message":{"event":"note_on","channel":1,"key":64,"velocity":100}}]},
  {"name":"n3","commands":[{"type":"local_midi","channel":0,"message":{"event":"note_off","channel":1,"key":64,"velocity":64}},
                           {"type":"local_midi","channel":0,"message":{"event":"note_on","channel":1,"key":67,"velocity":100}}]},
  {"name":"n4","commands":[{"type":"local_midi","channel":0,"message":{"event":"note_off","channel":1,"key":67,"velocity":64}}]},
  {"name":"lit","commands":[{"type":"animate","ops":[{"action":"show","target":{"object":9}}]}]},
  {"name":"unlit","commands":[{"type":"animate","ops":[{"action":"hide","target":{"object":9}}]}]}],
 "sequences":[
  {"name":"fanfare","length":32,"repeat":2,"steps":[{"tick":0,"run":"n1"},{"tick":8,"run":"n2"},{"tick":16,"run":"n3"},{"tick":24,"run":"n4"}]},
  {"name":"flash","length":6,"repeat":1,"steps":[{"tick":0,"run":"lit"},{"tick":5,"run":"unlit"}]}],
 "rules":[
  {"name":"start","on":{"event":"open"},"do":[{"type":"timer","op":"start","timer":"t0"}]},
  {"name":"space","on":{"event":"key","keys":[{"char":" "}]},
   "do":[{"type":"sequence","op":"start","sequence":"fanfare","at":{"beat":{"timer":"t0","ticks":30}}}]},
  {"name":"on_beat","on":{"event":"key","keys":[{"char":"b"}]},
   "when":{"read":{"of":"timer","timer":"t0","property":"phase","period":30},"in_range":[0,3]},"echo":true,
   "do":[{"type":"local_midi","channel":0,"message":{"event":"note_on","channel":10,"key":37,"velocity":110}}]},
  {"name":"bar","on":{"event":"cue","channel":1,"number":1},"do":[{"type":"sequence","op":"start","sequence":"flash"}]}]}}
```

**Example 8: a long press and a double press, with timers and a variable.** The triggers `held` and `double` are withdrawn (DEC-6635 item 7); this is how a page writes them. Holding Enter for half a second (30 ticks) tells the channel once: the press starts `t1`, the release stops it, and `after 30` on `t1` fires only if it is still running. Pressing Space twice within a third of a second (20 ticks) tells the channel once: the first press, with `v0` at 0, sets `v0` to 1 and starts `t2`; a second press while `v0` is 1 is the double; `after 20` on `t2` puts `v0` back to 0. One press never fires both `first` and `second`, because both are decided on `v0` as it stood before the press (RULE-6); three quick presses are one double and one first press.

```json
{"type":"rules","connections":"all","page":"190","sub":"0000","table":{"rules":[
  {"name":"hold_start","on":{"event":"key","keys":[{"name":"Enter"}]},"do":[{"type":"timer","op":"start","timer":"t1"}]},
  {"name":"hold_end","on":{"event":"key_up","keys":[{"name":"Enter"}]},"do":[{"type":"timer","op":"stop","timer":"t1"}]},
  {"name":"long_press","on":{"event":"after","ticks":30,"timer":"t1"},"do":[{"type":"report"}]},
  {"name":"first","on":{"event":"key","keys":[{"char":" "}]},"when":{"read":{"of":"variable","variable":"v0"},"op":"==","value":0},
   "do":[{"type":"variable","op":"set","variable":"v0","value":1},{"type":"timer","op":"start","timer":"t2"}]},
  {"name":"second","on":{"event":"key","keys":[{"char":" "}]},"when":{"read":{"of":"variable","variable":"v0"},"op":"==","value":1},
   "do":[{"type":"variable","op":"set","variable":"v0","value":0},{"type":"timer","op":"stop","timer":"t2"},{"type":"report"}]},
  {"name":"expire","on":{"event":"after","ticks":20,"timer":"t2"},"do":[{"type":"variable","op":"set","variable":"v0","value":0}]}]}}
```

## 8. The records and the input messages: push protocol version 10

The server encodes each message for receivers as a record in the audio profile's record frame on data channel 12, packet 4/31 (the engine's REQ-AUD-003; DOC-1952): a header of version, type and a two-byte body length, the body, and a CRC-32, cut into as many fragments as it needs, the body at most 8,184 bytes (`MAX_FRAMED_BODY`). The first form took types 21 to 27 and the input extension events `0x4B` to `0x4D` (the engine's branch `rules-integrate`, `neoteletext_input::limits::VERSION` 9, subprotocol `neottx.9`), none of it deployed. The second form keeps those numbers for the records whose meaning survives, changes their bodies, and takes the next free record types, 28 to 33. It needs no new extension event: `0x4E` is the next free. Every record of types 21 to 33 is one of the channel's records, which the audio receiver leaves to the page's evaluator and renderers: `neoteletext_audio::record::is_channel_type` lists them, and `neoteletext-web` re-exports the same numbers and asserts that they agree (DEC-6648 item 12).

| Type | Name | Second form | Requirement |
|---|---|---|---|
| 21 | `RULES` | changed: carries a page's table image in one or more fragments, with the sub-code | RULE-41 |
| 22 | `RULES_QUERY` | changed: gains the sub-code | RULE-47 |
| 23 | `ANIMATE` | changed: the sub-code "whichever is shown" is withdrawn | ANIM-6 |
| 24, 25 | `SPRITES`, `NAPLPS_OBJECTS` | unchanged | ANIM-7, ANIM-11 |
| 26 | `SHEET` | changed: gains the sub-code | ANIM-17 |
| 27 | `FRAME` | unchanged | ANIM-2 |
| 28 | `LOCAL_MIDI` | new | RULE-21 |
| 29 | `VARIABLE` | new | RULE-99 |
| 30 | `TIMER` | new | RULE-100 |
| 31 | `REPORT` | new | RULE-22 |
| 32 | `RUN` | new; 5 bytes since DEC-6635 (run now only) | RULE-102 |
| 33 | `SEQUENCE` | new; 12 bytes since DEC-6635 (with a start mode) | RULE-103 |

**RULE-41 [engine: neoteletext-web, neoteletext-rules]. The RULES record, type 21, and the table image.**
- **Statement.** A page's table is one **image** of at most `MAX_TABLE_BYTES` bytes, sent in one or more RULES records. A record's body:

| Bytes | Field | Values |
|---|---|---|
| 0–1 | page | `0x100` to `0x8FF` |
| 2–3 | sub-code | `0x0000` to `0x3F7E` |
| 4–5 | generation | 1 to 65,535 (RULE-40), the same in every fragment of one image |
| 6 | flags | bit 0: a table follows. Clear: the page has no table; total and offset are 0 and the body ends at byte 11. Bits 1 to 7 are 0 |
| 7 | reserved | 0 |
| 8–9 | total | the image's length, 12 to `MAX_TABLE_BYTES` |
| 10–11 | offset | the place of this fragment's first byte in the image |
| 12– | data | 1 to `MAX_TABLE_FRAGMENT` bytes of the image |

- A fragment with offset 0 begins an image and discards any image still incomplete for that page. Each later fragment MUST carry the same generation and total and an offset equal to the bytes already held; one that does not discards the incomplete image, and the receiver reports fault 1 (RULE-48). When the bytes held equal the total, the receiver decodes the image whole (RULE-70); until then the page keeps the table it had. A record with flag bit 0 clear removes the page's table at once. A table of at most `MAX_TABLE_FRAGMENT` bytes is one record. The records are among the channel's records, which the audio receiver leaves alone (`is_channel_type`), and inside an atomic frame they are held with the rest (ANIM-2).
- **The image** begins with a header of 12 bytes:

| Bytes | Field | Values |
|---|---|---|
| 0 | format | 2 |
| 1 | reserved | 0 |
| 2 | rectangles `R` | 0 to `MAX_RECTS` |
| 3 | rows `W` | 0 to `MAX_ROWS` |
| 4 | rules `N` | 0 to `MAX_RULES` |
| 5 | groups `G` | 0 to `MAX_GROUPS` |
| 6 | sequences `Q` | 0 to `MAX_SEQUENCES` |
| 7 | reserved | 0 |
| 8–9 | the bytes of the `G` groups together, as framed (RULE-45) | 0 to `MAX_GROUPS_BYTES` |
| 10–11 | reserved | 0 |

- then `R` rectangles, `W` rows, `N` rules, `G` groups and `Q` sequences, in that order (RULE-42 to RULE-45), and ends exactly at the last sequence.
- The record's reader (`neoteletext_web::records::rules::read`) checks the page, the sub-code, the generation, the total and the offset alone and gives the fragment on; the receiver assembles the image and decodes it with `neoteletext_rules::decode`, so that a table it refuses is reported with its generation (RULE-48, fault 1). The server checks the whole image with `neoteletext_rules::check` before it cuts it into records.
- **Reason and source.** DEC-6522 item 9 (decoded once into fixed arrays); DEC-6587 item 6: `MAX_GROUPS_BYTES` of groups do not fit one record's body (`MAX_FRAMED_BODY`), so the table is one image in fragments, decoded only when whole, and is still never half applied (section 15, item 37).
- **Verification.** Codec tests; a table in one, two and four fragments; a fragment out of place discards the image and the old table stays; the wire vectors of RULE-85.

**RULE-42 [engine: neoteletext-rules]. Rectangles and rows.**
- **Statement.** A rectangle is 8 bytes: `x`, `y`, `width`, `height`, each unsigned 16-bit, width and height at least 1. A row is 4 bytes: its parameter `p`, a signed 32-bit integer (DEC-6635 item 8; the second form's rows of 16 bytes are withdrawn). (The first form's variable and timer declarations and sub-page masks are withdrawn: RULE-14, RULE-15, RULE-17.)
- **Verification.** Codec tests of each bound.

**RULE-43 [engine: neoteletext-rules]. A rule and its triggers.**
- **Statement.** A rule is: a flags byte (bit 0: it names rows; bits 1 to 7 zero); its group (1 byte, below `G`); when bit 0 is set, its first row (1 byte) and row count (1 byte, at least 1, first plus count at most `W`); a trigger count (1 byte, 1 to `MAX_TRIGGERS_PER_RULE`); that many triggers, each its kind byte (the codes of RULE-9) and body; and the condition (RULE-44). The sum, over the table's rules, of each rule's row count (1 for a rule that names none) MUST be at most `MAX_RULE_ROWS`. The trigger bodies:

| Kinds | Body |
|---|---|
| 1 `key`, 2 `key_up` | flags (bit 0 `repeat`, kind 1 only; bit 1 `by_row`, only in a rule that names rows, with `K` equal to the rule's row count; other bits 0); modifier mask; modifier value; key count `K`, 0 for any key, else 1 to `MAX_KEYS_PER_TRIGGER`; `K` keys of 5 bytes each: a kind byte and a 32-bit code |
| 3 `press`, 4 `release` | target (3 bytes: kind, 16-bit number); button (0, 1, 2 or 255) |
| 17 to 20 | withdrawn (DEC-6635 item 7): refused |
| 5 `enter`, 6 `leave`, 14 `wheel` | target |
| 13 `move` | target; flags (bit 0 `held`; other bits 0) |
| 7 `open`, 8 `close`, 9 `becomes`, 12 `text`, 15 `focus`, 16 `blur` | empty |
| 10 `every`, 11 `after` | timer (0 to 7, or 255); ticks (unsigned 32-bit, 1 to `MAX_TIMER_TICKS`) |
| 21 `cue` | audio channel (0 to 3); cue number (0 to `MAX_CUE`, or 255 for any) |

- A key's kind byte is 1 (character), 2 (named) or 3 (physical) with the code a Unicode scalar value for kinds 1 and 3 and a functional code that names a key (`neoteletext_input::keys::is_code`) for kind 2. The second form's key kinds with bit 7 set (a key code taken from a row parameter) are withdrawn and refused: a row chooses its key by place, with `by_row`. A target's kind is 0 to 3 (kind 0 has number 0; kind 3's number is below `R`); or, in a rule that names rows, kind 1, 2 or 3 with bit 7 set, the number field then holding a signed 16-bit constant to which the row's `p` is added. For every row such a rule names, the number so given MUST be valid for its kind, checked when the table is decoded. A `becomes` rule has one trigger and a condition of at least one node.
- **Verification.** Codec tests; every reserved bit set is refused; the sum of row counts at `MAX_RULE_ROWS` accepted and one over refused.

**RULE-44 [engine: neoteletext-rules]. Values and conditions.**
- **Statement.** A value is 8 bytes: space (1 to 8), `a`, and `b`, `c`, `d` (unsigned 16-bit), with the meanings of RULE-23 to RULE-28, RULE-116 and RULE-117; every unused field MUST be 0, and each field is checked against its space's ranges when decoded (a variable 0 to 15, a timer 0 to 7 or 255, a timer property 0 to 2, with a phase's period, `c` and `d` together, 1 to `MAX_TIMER_TICKS`, an audio channel 0 to 3, a part 0 to 15, a class 0 to 9, a key 0 to 127, a parameter number 0 to 255, a family code 12 to 18, a variant 0 to 2, a `fired` property 0 to 4, a sequence below `Q`, a sequence property 0 to 3).
- A condition is a count byte of nodes, 0 (no condition) to `MAX_CONDITION_NODES`, then the nodes in prefix order (a node, then each of its children in order). Each node is its code byte (RULE-18) and:

| Node | Body |
|---|---|
| 1 `and`, 2 `or` | child count, 2 to `MAX_AND_OR_CHILDREN` |
| 3 `not` | nothing; one child follows |
| 4 compare | value (8 bytes); operator (1 to 6); constant (signed 32-bit); a parameter byte: 0 for none, or `0x20` to add the row's `p` to the constant (only in a rule that names rows); `0x21` to `0x23` are withdrawn and refused |
| 5 in range | value; `low`; `high` (signed 32-bit, `low ≤ high`) |
| 6 in set | value; count 1 to `MAX_SET_MEMBERS`; that many signed 32-bit constants |
| 7 `overlaps`, 8 `inside` | two targets (3 bytes each, no bit 7) |

- The nodes MUST form exactly one tree that uses every node counted, and meet RULE-18's limits.
- **Verification.** Codec tests: trees at each limit; a count that leaves nodes over, or runs short, refused.

**RULE-45 [engine: neoteletext-rules, neoteletext-web]. Groups and sequences in the image.**
- **Statement.** A group is a count byte of commands, 1 to `MAX_GROUP_COMMANDS`, then that many **command frames**:

| Bytes | Field | Values |
|---|---|---|
| 0 | type | a record type RULE-119 allows |
| 1 | bindings `B` | 0 to `MAX_COMMAND_BINDINGS` |
| 2–3 | length `L` | the body's length, 1 to `MAX_COMMAND_BYTES` |
| 4– | body | `L` bytes: the record's body exactly as the server sends that record, without the record frame's header and CRC-32 |
| then | `B` bindings of 3 bytes each | item (the operation's place in an `ANIMATE` record, else 0); field code; source (RULE-106) |

- A sequence is: its repeat count (1 byte, 0 for until stopped); its step count (1 byte, 1 to `MAX_SEQUENCE_STEPS`); its length (unsigned 32-bit, 1 to `MAX_SEQUENCE_TICKS`); then each step: an offset (unsigned 32-bit, below the length, not below the step before) and a group (1 byte, below `G`).
- The crate `neoteletext-rules` reads the frames and the bodies of the records it defines (types 28 to 33 and the `ANIMATE` operations); the bodies of `CONTROL`, `SPRITES` and `NAPLPS_OBJECTS` are read by their own crates' readers (`neoteletext-audio`, `neoteletext-web`), which `neoteletext-rules` reaches through a function its caller passes (RULE-56), so that the crate keeps no dependency and every body is still checked, by its one reader, when the table is decoded. The first form's action bodies are withdrawn with RULE-20.
- **Reason and source.** DEC-6587 item 1 ("how a group is carried"): a record holding framed commands.
- **Verification.** Codec tests of each frame bound; a body its record's reader refuses refuses the table; the wire vectors.

**RULE-46 [engine: neoteletext-input]. The RULE_EVENT message, extension type `0x4B`.**
- **Statement.** A receiver makes each report (RULE-22) with the input event of extension type `0x4B`, whose payload is:

| Field | Form |
|---|---|
| stamp | the page and sub-code on screen, as every stamped event has them (DOC-1934) |
| generation | 16-bit: the table's |
| rule | 1 byte, 0 to 63; 255 when the run was not made by a rule |
| row | 1 byte: the place of the firing row within the rule's rows, 0 to 63; 255 when none |
| tick | unsigned 32-bit: the page tick of the firing |
| kind | 1 byte: 0 fired (no event), 1 input, 2 value |
| target | 3 bytes: the kind and number of the control, object or rectangle the pointer was inside for a rule whose pointer trigger named one; else all zero |
| body | kind 0: nothing. Kind 1: one or two whole input events exactly as push protocol 8 encoded them, each from its `0xFF`: KEY, MOUSE, WHEEL, TOUCH, PASTE, COMPOSE, FOCUS_IN, FOCUS_OUT, HOVER or DRAWING_HOVER; and after a MOUSE, TOUCH or WHEEL on a page drawn by the ReGIS renderer, its PICK. In place of an event the body may be one run of raw text (UTF-8, which never begins with `0xFF`; DOC-1781), for text that came from no key. Kind 2: a value (8 bytes) and its reading (signed 32-bit) |

- Under push protocol 10, as under 9, the events KEY, MOUSE, WHEEL, PASTE, COMPOSE, TOUCH, FOCUS_IN, FOCUS_OUT, HOVER, PICK, DRAWING_HOVER and raw text MUST appear only inside a RULE_EVENT. A server MUST treat one at the top level of the stream as a protocol fault and close the connection, and a receiver MUST never write one there. HELLO, RESIZE, SELECT, RESUME and viewer state's three messages stay at the top level. A RULE_EVENT counts as one message for acknowledgement; **one not acknowledged when its connection ends is discarded and never sent again** (RULE-111).
- After the stamp, which is two varints as on every stamped event, every field of RULE_EVENT, PAGE_STATE (RULE-47) and RULES_FAULT (RULE-48) is big-endian and of the fixed width its table gives.
- A target is carried by kind 1 alone: a RULE_EVENT of kind 0 or 2 that names a target is refused by its reader.
- A RULE_EVENT counts one for acknowledgement whatever it carries, so a pointer's move and an input method's composition, which push protocol 8 did not count, are acknowledged, and a move is never dropped or replaced while a connection is congested. PAGE_STATE and RULES_FAULT are no input and count nothing. The input session's limit of 120 messages a second looks at what a RULE_EVENT carries: a release always goes, a move is not held to the limit, and a firing with no event and a value are.
- An `enter` or `leave` on a control is carried as HOVER; on a ReGIS drawing as DRAWING_HOVER; on a teletext sprite, a NAPLPS object or a rectangle as the MOUSE move that caused it, with the target named.
- **Reason and source.** REQ-6523; DEC-6522 items 7 and 8. Wrapping the existing events means the server's existing readers and the programs' existing `input` handling are reused whole.
- **Verification.** Engine tests: each kind round-trips; a bare KEY at top level is a fault; the wire vectors.

**RULE-47 [engine: neoteletext-web, neoteletext-input]. RULES_QUERY, record type 22, and PAGE_STATE, extension type `0x4C`.**
- **Statement.** Record type 22, `RULES_QUERY`, has a body of 8 bytes: the page (2 bytes), the sub-code (2 bytes) and the query's identifier (unsigned 32-bit, which the server chooses and maps to the program's `request`). A receiver that has that page open answers exactly once with the input event of extension type `0x4C`, `PAGE_STATE`, as soon as the query is handled, as an event, in arrival order (RULE-5), and ignores a query for a page that is not open or is paused; it answers at most one query a second for a page and drops the rest, reporting fault 6 (RULE-48). The payload:

| Field | Form |
|---|---|
| stamp | page and sub-code |
| identifier | unsigned 32-bit, the query's |
| generation | 16-bit, the table's; 0 when the page has no table, and then nothing follows but a tick of 0 |
| tick | unsigned 32-bit: the page tick the query was handled in, whose state is reported as it stood then |
| variables | sixteen values (signed 32-bit), `v0` first |
| timers | eight entries, `t0` first, each: flags (bit 0 running) and elapsed ticks (unsigned 32-bit) |
| sequences | count (the table's `Q`), then for each: flags (bit 0 running, bit 1 waiting; other bits 0); passes (unsigned 32-bit); position (unsigned 32-bit) |
| targets | count (0 to `MAX_TABLE_TARGETS`), then for each control and object the table names by a constant, in the order first named: kind; number (16-bit); flags (bit 0 exists, bit 1 shown, bit 2 cycling); look; frame; x; y (signed 16-bit); layer; order (signed 8-bit) — 12 bytes |
| values | count (0 to `MAX_TABLE_VALUES`), then for each distinct value the table reads, in the order first read: the value (8 bytes) and its reading (signed 32-bit) |

- **First named** and **first read** follow the rules in rule order and, within a rule, its trigger's target, then its condition's nodes in order, then the commands of its group in order, and after the rules the groups no rule names, in group order. A value of space 4 names its target.
- The answer is at most `MAX_STATE_BYTES` bytes, within the input protocol's largest message (8,192).
- **Reason and source.** DEC-6522 item 8 (c), kept by DEC-6587 item 9 for reading and debugging, not for resynchronising.
- **Verification.** Engine codec tests; a browser test that a query for a page not open gets no answer and that two queries in one second get one.

**RULE-48 [engine: neoteletext-input; neoteletext-browser; neoteletext-app-server]. RULES_FAULT, extension type `0x4D`.**
- **Statement.** A receiver reports a fault of a page's table with the input event of extension type `0x4D`: the stamp, the table's generation (16-bit), a code (1 byte) and a count (16-bit, how many times since the last report). The codes:

| Code | Name | Meaning |
|---|---|---|
| 1 | `undecodable` | the table image could not be assembled or decoded and was refused whole (the receiver and the server disagree; the page then has no table) |
| 2 | — | Withdrawn: `tick_overrun`. There is no limit of actions a tick (RULE-6). The code is never sent and never reused |
| 3 | `reports_dropped` | reports dropped by the trusted core's budgets (RULE-52) |
| 4 | `events_dropped` | events — input events, commands the server sent and cues — dropped at a full queue (RULE-5) |
| 5 | `commands_skipped` | commands that did nothing for a missing target or sound (RULE-118) |
| 6 | `query_dropped` | a state query dropped |
| 7 | `local_overrun` | a local sound stopped for overrunning its time (RULE-62) |
| 8 | `animation_slowed` | animation slowed by its budget (ANIM-16) |
| 9 | `evaluation_late` | the page's tick steps and handlings took longer than the ticks' own time, so page time slowed (RULE-4, section 12.4) |
| 10 | `queue_full` | a sound command dropped at the trusted core's budget, or a cue mark dropped by the sound helper (RULE-52, RULE-109); a sequence start beyond `MAX_START_TICKS` is counted with it (RULE-103) |

- A receiver sends at most one RULES_FAULT a second for each code and page. The server gives the program `{"type":"rules_fault","connection":7,"page":"101","sub":"0001","generation":3,"fault":"evaluation_late","count":12}` with the fault named as above, and writes code 1 to its operator's log as an error.
- **Reason and source.** DEC-6522 item 10: a refusal is reported, never silently ignored.
- **Verification.** Browser tests that produce each code; the server's test of each name.

**RULE-49 [engine: neoteletext-input; neoteletext-common]. Push protocol version 10.**
- **Statement.** The input protocol's `VERSION` (`neoteletext_input::limits::VERSION`, the number in HELLO, in WELCOME and in the push connection's subprotocol, `neottx.10`) MUST become 10, and every other version MUST be refused both ways. Version 10 is version 8 with: record types 21 to 33 as this section and animation.md give them; the extension events `0x4B` to `0x4D`; the OBJECT record's tag 9 (RULE-60); the Cue Point event in a block (RULE-109); and the rule that input events travel only inside RULE_EVENT (RULE-46). Version 9, the first form's, was never deployed and is not kept. The descriptor's `push.input` and `push.wheel` stay withdrawn. neoteletext-common's `wire-vectors.tsv` gains the version and the vectors of RULE-85.
- **Reason and source.** DEC-6522 item 2; DEC-6587; a hard change of version, with no compatibility shim (DEVELOPMENT.md section 2.1).
- **Verification.** The wire vectors' test in the engine, the server and the browser; a version 9 and a version 8 HELLO refused.

**RULE-50 [neoteletext-browser]. A page with no table.**
- **Statement.** For a page whose view holds no table, the browser MUST evaluate nothing, give the decoder no input event of that page, and send its channel nothing for anything the viewer does on it: no key, text, paste, composition, press, release, move, wheel, hover, pick or focus change. The page is still shown, its links work, its sound plays, the looks under the pointer are drawn locally as today, the commands the server sends it directly that need no table (`CONTROL`, `ANIMATE`, `SPRITES`, `NAPLPS_OBJECTS`) are applied, and SELECT still tells the channel which page the tab shows. A `VARIABLE`, `TIMER`, `REPORT`, `RUN`, `SEQUENCE` or `LOCAL_MIDI` record for a page with no table, or for a page that is not the open page, is dropped and counted.
- **Reason and source.** REQ-6523: "A page with no rule table sends no input at all."
- **Verification.** REQ-6523's tests: for each kind of input, the fetcher's outgoing messages are empty.

**RULE-51 [neoteletext-browser]. What stays the browser's own.**
- **Statement.** Whatever a page's table says, the browser MUST keep for itself, and never give the evaluator or the channel:
  1. a key pressed with the browser's own modifier, which steps the page and sub-page lists (REQ-6390, DEC-6389), and every key the trusted strip or a browser dialog has;
  2. a click made with the browser's modifier (REQ-1384);
  3. a press and release on a link the page declares — a teletext link, a Fastext prompt or a linked ReGIS drawing — which the browser follows itself (REQ-4111, REQ-6376, decision 122); a rule's `press` on a target under a link does not fire;
  4. the wheel over a page whose page number has more than one sub-code, which steps them, unless the page's table has a `wheel` rule whose target the pointer is inside. So that the trusted core can decide without reading a table, the decoder tells it, with the interest mask, at most `MAX_RECTS` rectangles of the page's picture inside which a `wheel` rule applies (the whole picture for the target `page`; an object's bounding rectangle), and tells it again when they change. The rectangles are those of every `wheel` rule of the table, whatever its condition: a mode that should give the wheel back to the browser is not expressible, and a page that needs it uses another page;
  5. everything typed or clicked outside the open page's picture, and everything while the browser's own surfaces over the page have the keys and the pointer, as its tab filmstrip does while it is open: the wheel's owner decides the filmstrip before every other place, whatever a rule's claim (the browser's DEC-6664 item 6).
- **Reason and source.** REQ-4112's exceptions, kept; DEC-6447's wheel rule restated on the table. With the enabled flag withdrawn (DEC-6587 item 8) the rectangles no longer depend on a rule being enabled (section 15, item 38).
- **Verification.** The existing tests of REQ-4112 and REQ-6390, re-pointed at the table; a test that a `wheel` rule takes the wheel from the sub-page list only inside its target.

**RULE-52 [neoteletext-browser]. The trusted core is the gate: nothing leaves that the viewer did not do and the page's view did not report.**
- **Statement.** The trusted core MUST enforce REQ-6523 itself, without reading a table:
  1. **In.** It gives a page's decoder the viewer's input events for the open page only while that decoder has told it the page has a table, and only of the classes the decoder asked for in its **interest mask** (bit 0 keys, bit 1 text, bit 2 pointer buttons, bit 3 pointer moves, bit 4 the wheel, bit 5 focus changes), which the decoder derives from the triggers and key-state values of the table. Each event it gives carries a sequence number, the page's key (page number and sub-code), and what the core already derives for it (the cell, the pixel, the control under the cell, the ReGIS drawing the pick record names).
  2. **Kept.** It keeps the last `INPUT_RING` (64) events it gave each open page.
  3. **Out.** A decoder asks for a report with a message that names the page, the rule, the row, the tick and either an input sequence number, or a value and its reading, or nothing (a bare firing). The decoder never supplies an event's bytes. The trusted core builds the RULE_EVENT itself: for a sequence number, from its own kept copy of that event, and only when the event was given to that decoder for that page within the last `SEND_WINDOW_TICKS` (4) ticks and has not already been reported for that rule and row; otherwise it drops the request and counts it. A group therefore cannot make any input leave that the viewer did not make on that page in those ticks, whatever its commands.
  4. **Where.** It gives the RULE_EVENT only to the fetcher of that page's own channel, on that view's own connection, and only while that page is still the open page of that view or within `SEND_WINDOW_TICKS` of its closing (so that a `close` rule's report leaves), and never after that connection has ended.
  5. **How much.** It sends at most `SEND_BUDGET` (120) reports a second for a page, holding at most 120, of which at most `TIMED_SEND_BUDGET` (20) a second may be reports with no input event (a bare firing or a value). What exceeds a budget is dropped and reported as fault 3. It passes at most `SOUND_COMMAND_BUDGET` (512) sound commands a tick from a view's decoder to the sound helper, however they arose — a group, a sequence or a record of the server — and drops and counts the rest (fault 10). The budget is counted for each presentation tick of the trusted core's clock, over the voice operations `Start`, `Stop`, `Gain`, `Local` and `LocalMidi`; `LocalBank`, `Cue` and samples are not sound commands (the browser's DEC-6659 item 5).
  6. **State.** It passes a PAGE_STATE only in answer to a query its fetcher received for that page on that connection, once, and checks its length.
- **Reason and source.** REQ-6523; the browser's architecture (the trusted core reads no teletext format, so it cannot check a table, but it is the origin of every input event and can refuse to send anything it did not itself receive from the viewer for that page). The sound command budget is a general protection of the core and the sound helper against any decoder, not a cap on a group (section 12.4; section 15, item 39).
- **Verification.** The hostile-decoder harness: a decoder that asks to send a sequence number it was never given, one from another page or another sub-code, an old one, the same one twice for one rule and row, and 1,000 a second, gets none of them sent beyond the budget; 10,000 sound commands in a tick pass 512; the fuzz target of RULE-83.

**RULE-53 [neoteletext-app-server]. Migration: the channel's default table keeps every deployed channel working.**
- **Statement.** A channel's entry in `channels.json` keeps the field `default_rules`, `"none"` (the default when absent) or `"send_all"`; the field `wheel` only shapes the default table. For a channel with `"send_all"`, the server MUST send, at every selection (RULE-40) and whenever the program removes the page's table (`"table":null`), the **default table** below as that page's RULES record. With `"none"`, a RULES record with no table. The default table, in the form of RULE-35:

```json
{"groups":[{"name":"send","commands":[{"type":"report"}]}],
 "rules":[
 {"name":"keys","on":{"event":"key","keys":"any","repeat":true},"run":"send"},
 {"name":"keys_up","on":{"event":"key_up","keys":"any"},"run":"send"},
 {"name":"text","on":{"event":"text"},"run":"send"},
 {"name":"press","on":{"event":"press","target":"page","button":"any"},"run":"send"},
 {"name":"release","on":{"event":"release","target":"page","button":"any"},"run":"send"},
 {"name":"move","on":{"event":"move","target":"page","held":false},"run":"send"},
 {"name":"hover_in","on":{"event":"enter","target":{"control":"any"}},"run":"send"},
 {"name":"hover_out","on":{"event":"leave","target":{"control":"any"}},"run":"send"},
 {"name":"drawing_in","on":{"event":"enter","target":{"object":"any"}},"run":"send"},
 {"name":"drawing_out","on":{"event":"leave","target":{"object":"any"}},"run":"send"},
 {"name":"focus","on":{"event":"focus"},"run":"send"},
 {"name":"blur","on":{"event":"blur"},"run":"send"},
 {"name":"wheel","on":{"event":"wheel","target":"page"},"run":"send"}]}
```

- The last rule, `wheel`, is present only when the channel's `wheel` is `true`. The table is twelve or thirteen rules that each run the one default group, which holds one `REPORT` of the firing. It is built by one function of `neoteletext-rules` (`default_send_all(wheel)`), so its bytes are the same everywhere. With it a page's program receives exactly the `input` messages version 13 gave it (each now naming its rule), so no deployed channel's code changes.
- The deployment (`deploy/ionos/deploy.sh`) gives `"default_rules":"send_all"` to every channel deployed on 18 November 2026: `home`, `hackaday`, `oldhackaday`, `demosite`, `uicomponentsdemo`, `regisgallery`, `regis`, `naplps` and `audio`. A new channel is given `"none"`, and `musicplayer` is the first. Each of the nine is to move to tables of its own (RULE-54) and then to `"none"` (TODO-6544); the default table is deleted from the server when the last has moved.
- **Reason and source.** REQ-6523 requires that the page ask. The channel's operator asking on behalf of every page of a channel, in one reviewed line of configuration, is the least risky way to keep nine deployed channels working through the change.
- **Verification.** Server tests: a `send_all` channel's page is sent the 12- or 13-rule table at selection; `"table":null` puts it back; a `none` channel's page gets none. An end-to-end test for each deployed channel passes unchanged against protocol 15.

**RULE-54 [neoteletext-server-ts-ui-components]. The component library writes each page's table.**
- **Statement.** The component library MUST derive a `rules` table for every page it composes — every page number and sub-code it sends, each from the components mounted on that sub-page alone (RULE-112) — read from their handlers each time the page is drawn, and send it to each connection at every selection of the page and again only when its content changes, so that a page asks for no more than its components can take:
  1. **Keys and text.** The rules `keys` (any key, with repeat) and `keys_up` when any component handles a key, takes text or can hold the keys; `text` when one takes text, a paste or a composition; `focus` and `blur` when one handles the page gaining or losing the keyboard; `hover_in` and `hover_out` (`enter` and `leave` on any control) when the page declares a control and a component handles a hover there.
  2. **The pointer, on rectangles of cells.** The table declares rectangles (`rects`, in dots, a cell 12 by 20) that share no cell and cover exactly the cells where some component takes the press, the release, every move or the wheel, each named for its component's class and numbered (`button_1`), with the rules `press_<name>`, `release_<name>`, `wheel_<name>` and `move_<name>`. Control numbers are not used. The release is asked for only where a component handles it.
  3. **A drag.** The moves of a drag are asked of the whole page: the rule `drag`, a `move` on the target `page` with `held`, present when a component that follows the pointer can be reached, so that a drag is followed wherever the pointer goes. A component that takes every move has `move_<name>` on its own rectangle, without `held` and with the condition that no button is down, so that it and `drag` never send the same move.
  4. **Every rule only reports.** The library's components act on the press and none has a pressed look of its own (the receiver draws a control's hover and pressed looks itself), so every rule of the table is written with the `do` list `[{"type":"report"}]`, which the server makes into one unnamed group that every rule shares (RULE-35), and no `groups`, `rows`, `sequences`, `run`, `echo` or `animate` command is written (DEC-6670 items 1 and 9).
  5. **Page selection.** A page whose table does not ask for every key asks for the keys the protocol kit selects pages by, each unless the page owns them: `select_digits` (the ten keys of the digit row, as physical keys), `select_keypad` (the named keys `Numpad0` to `Numpad9`) and `fastext_keys` (F1 to F4 and the four coloured keys), each the press alone. A table with no rules is sent only for a page that owns both the digits and the coloured keys and has no component that takes input.
  6. **At the table's limits.** A page that would need more than `MAX_RECTS` rectangles, or more rules than `MAX_RULES`, asks for the pointer on the whole page under the default table's rule names (RULE-53), and the channel's log says so, naming the page and sub-code. The protocol kit exports neither constant, so the library finds both from the kit's own check of a program's message, once for the limits `start` gave, and states neither figure (DEC-6670 items 8 and 11).
  7. **Routing.** An `input` is given to its component by where it landed and by which component has the keys, as before protocol 14; its `rule` says which need asked for it.
  9. **Every sub-page its own.** The first build derived the pointer's rectangles from "the first sub-page's cells" of a page. That is withdrawn (DEC-6599): each sub-code the library sends is a page with a table derived from its own cells, sent at its own selection, and nothing is derived for a page number as a whole.
  8. **No tables.** A channel chooses with the option `ruleTables` whether the library writes tables: `"components"` (the default), or `"none"`, with which the library sends no `rules` message for any page, so that every page is left to the channel's `default_rules` (RULE-53).
- **Reason and source.** REQ-6523's purpose: a viewer's input goes nowhere a page has not asked for. DEC-6599 for item 9. The library already knows every interactive component of a page, so the precise table costs its authors nothing.
- **Verification.** Library tests: for each component kind, the table of a page that holds one; a page of static text asks for the page-selection keys alone; a channel with `ruleTables` `"none"` sends no `rules` message; two sub-codes of one page number with different components get two different tables; the demonstration channels' existing tests pass with `default_rules` set to `"none"`.

**RULE-55 [neoteletext-server-ts-protocol; neoteletext-server-channels]. The kits' calls.**
- **Statement.** Both kits MUST offer, as thin calls that only build and send the messages of section 7 (DEC-6462), with the TypeScript names here and the Python names their snake_case forms (a handler with `on_` before it), and list them in `kit-calls.tsv`. Every call that concerns a page takes the page number and the sub-code:

| TypeScript | Python | Message |
|---|---|---|
| `context.rules(to, page, sub, table)` | `app.rules(to, page, sub, table)` | `rules`; `table` is the typed object of RULE-35 or `null` |
| `context.queryState(connection, page, sub): Promise<PageState>` | `app.query_state(connection, page, sub)` (awaitable) | `query_state`, resolved by `page_state`, rejected by `refused` |
| `context.localMidi(to, page, sub, channel, message)` | `app.local_midi(…)` | `local_midi` |
| `context.variable(to, page, sub, command)` | `app.variable(…)` | `variable`; `command` is the message's `op`, `variable` and operand |
| `context.timer(to, page, sub, op, timer)` | `app.timer(…)` | `timer` |
| `context.report(to, page, sub, value)` | `app.report(…)` | `report` |
| `context.run(to, page, sub, group)` | `app.run(to, page, sub, group)` | `run` (no `at`, DEC-6635 item 6) |
| `context.sequence(to, page, sub, op, sequence, at?)` | `app.sequence(…, at=None)` | `sequence`; `at` is `null`, `{tick}` or `{beat}` with `start` (RULE-103) |
| handler `ruleEvent(event, context)` | `on_rule_event(event)` | `rule_event` |
| handler `rulesFault(fault, context)` | `on_rules_fault(fault)` | `rules_fault` |
| the existing input handler | the same | `input`, whose event object has `rule`, `tick` and `target`, and the place of the firing row as `ruleRow` (`rule_row`), since an input's `row` is already a pointer event's cell row (DEC-6662 item 4) |
| `context.objectPage(to, page, sub, objectPage, objectSub, object)` | `app.object_page(…)` | `object_page` (animation.md ANIM-17, ANIM-21) |

- The types (`RuleTable`, `PageRule`, `RuleTrigger`, `RuleCondition`, `RuleValue`, `RuleGroup`, `RuleCommand`, `RuleSequence`, `RuleRow`, `Amount`, `RuleTarget`, `PageState`) are generated from the schema; the schema's existing type `Rule` (the refusal's rule) keeps its name. The kits MAY offer small builders that only construct these objects — for example `physicalKey("a")`, `level(0)`, `variable("v0")`, `plus(12, "v0")`, `row(plus?)` (the row's `p`), `phase(timer, period)`, `noteOn(channel, part, key, velocity)`, `fired(property, plus?)`, `characterKey`, `namedKey`, `noteOff`, and the mode helper of RULE-110 (`modes("v3", ["play", "help"])`, giving `in(mode, condition?)`, which joins a condition given with `and`, and `enter(mode)`; Python's `in_`, since `in` is a keyword) — each listed in `kit-calls.tsv` as a `builder` or `modes` row with the JSON it answers, so that both kits build the same objects (DEC-6662 items 1 to 3 and 5) — and MUST NOT check a table beyond the schema, expand rows, or turn `do` and `echo` into groups: the server does that (RULE-35). Each kit's test harness has `press`, `fire` and `answerState` calls that feed a program the `input`, `rule_event` and `page_state` a receiver would cause. `fire` takes the firing row's place last and a rule of `null` (`None`) for a run no rule made; `answerState` answers the sixteen variables at zero, for the page and sub-code the query named, over the fields a test gives (DEC-6650 item 8, DEC-6662 item 8).
- **Reason and source.** DEC-6462: the kits are thin and equal. DEC-6587 item 8 (the kits provide modes).
- **Verification.** Each kit's public-interface test against `kit-calls.tsv`; `server-rules` tests; the shared fixture `rules-examples.jsonl`.

## 9. Identity, lifetime, limits, and the one crate

**RULE-112 [every repository]. A sub-page is a page: everything is keyed on the page number and sub-code together.**
- **Statement.** Every part of the rule table and of animation MUST treat one page number with one sub-code as one page, with no relationship to any other sub-code of the same number. Each has its own rule table, groups, sequences, rows, timers, sixteen variables, sprites, objects, sheet, animation state, frames, timelines and local sounds. Every record of section 8 and of animation.md, every program message, every kit call and every key of a map in an implementation carries or uses both. Nothing is addressed by a page number alone, and nothing means "every sub-page of" or "whichever sub-page is shown": the first form's sub-code `0x3F7F` in an `ANIMATE` record, its sheet of a page fed to each sub-page, its table for all sub-pages and its sub-page off-lists are withdrawn, and no value gives the shown sub-code. Going from one sub-code to another is leaving one page and opening another (RULE-111). The audio profile's `CONTROL` record names a page number only, which this document does not change: a local sound belongs to the page (number and sub-code) that is open in the view when its play is carried out, whose number the record names, and ends when that page is no longer open.
- **Reason and source.** DEC-6599 (the owner, 18 November 2026: "in neoteletext a sub-page has NO relattionship to its parent page - we treat sub pages EXACTLY as pages"), which applies DEC-1500.
- **Verification.** In each repository, a test that two sub-codes of one page number hold separate tables, variables and animation state, and a review that no map or message of the rule table or animation is keyed on a page number alone (the build plan lists the first build's places).

**RULE-111 [neoteletext-browser; neoteletext-app-server; engine]. Everything local is dropped when a page is left or its connection ends; nothing is resynchronised.**
- **Statement.** A page's **local state** is: its rule table with its groups, sequences, rows and rectangles; its variables, timers, sequences (running or waiting), `becomes` memory and waiting events; its animation state, sprites, objects, sheet and open frame; its local sounds; its cue marks; and its watch list. There are exactly four things that can happen to an open page, and a receiver and a server MUST treat them so:
  1. **The page is closed while its connection stands**: the viewer selects another page or another sub-code, follows a link, or closes the tab. The receiver gives the lost releases of RULE-8, runs the one `close` handling (RULE-5), lets its reports leave (RULE-52 item 4), and then drops all of the page's local state. Coming back to the page later is a new selection: the server and the program send it afresh, and its `open` fires at a new page tick 0.
  2. **The push connection ends** — the view's connection to the server closes, fails or is replaced, for any reason. The receiver MUST at once drop all local state of the page that view had open, with every local sound stopped and every note released, run no `close` handling, discard every RULE_EVENT not yet acknowledged (RULE-46) and keep presenting the last picture as it stood, frozen. The picture's sprites, objects, sheet and animation state are kept only as that frozen picture, evaluated and changed by nothing, until the page is sent afresh, because dropping them would change what the viewer still sees; at a close (case 1) they are dropped with the page (the browser's DEC-6659 item 4). The engine's input session keeps every unacknowledged message for a resumption and offers no way to drop some of them, so the browser forgets a session that ever gave a page's table input and makes the next connection a new session from HELLO; a session that gave none resumes as before (the browser's DEC-6659 item 3, until the engine offers a call that drops the unacknowledged RULE_EVENTs and keeps the session). When a connection is made again, the receiver selects the page as a new selection, whether or not the session is resumed (RESUME restores the session's identity and nothing of a page); the page is sent afresh and its `open` fires again. The server, when a connection ends, MUST forget everything it holds for it of any page: the names of its table, its generation counter, its timelines, its open frame, and its unanswered state queries (each refused `not_answered`).
  3. **The program's connection to the server ends** (the program stops, fails or is restarted). The server MUST, for every connection of that channel, stop every timeline, end any open frame, and send for the page it has selected a RULES record that says the page has no table (or the channel's default table, RULE-53), which makes the receiver drop the table and with it the variables, timers, sequences and waiting events; it holds nothing over for the program's return. When the program is back it is told of each connection's selection as a new one and sends each page afresh.
  4. **The tab stops being the active tab, or the page otherwise stops being the open page while still selected** (another tab is brought forward, the overview or a wall is shown). This is **not** a disconnect and not a close: the page is **paused**. The receiver handles the lost releases of RULE-8 at once, then runs no tick step, handles no event, gives the page no input, makes no report, forgets its cue marks, and has the sound helper stop rendering the page's local sounds (their instruments are kept, silent, with every note released). The page tick does not advance. Records the server sends meanwhile are applied as for any page that is shown but not open (animation operations are; commands that need the evaluator are dropped and counted, RULE-50). When the page is the open page again, evaluation goes on from the next page tick with every variable, timer and sequence as it was; `open` does not fire.
- No state is ever carried across a close or a disconnect, by either side, and none is rebuilt: the state query is not used for it, the server replays no animation state, table, sprites, objects or sheet to a returning viewer, and what a late viewer is sent is what the page's program sends on its selection (RULE-40).
- **Reason and source.** DEC-6587 item 3 (the owner: "after a disconnect i think EVERYTHING should be dropped and the page reloads"); DEC-6599 item 2. Its cost, stated in that decision: a network break stops a page's local sound and resets it. Pausing a background tab, rather than closing it, is this document's (section 15, item 40): a viewer who glances at another tab should not find a counter reset, and a paused page does nothing at all, so nothing is risked by keeping it.
- **Verification.** Browser tests: each of the four cases — after a close, the `close` report leaves and the next selection starts from zero; after the connection ends, no `close` report is made, the unacknowledged RULE_EVENT is not sent on the new connection, and `open` fires again; a paused page evaluates nothing, sounds nothing and resumes with its variables. Server tests: a connection's end forgets its names and timelines; a program's end sends the empty table to each connection; a returning viewer is sent nothing kept.

**RULE-56 [engine]. One crate, `neoteletext-rules`, holds the codec, the checks and the evaluator.**
- **Statement.** The engine's crate `crates/neoteletext-rules` MUST be: `no_std`, without allocation, integer-only, with no dependency of any kind (not even another engine crate), `unsafe_code` forbidden, and denying the panic lints of DEVELOPMENT.md section 6 since it reads outside input. It holds: `limits` (every constant of RULE-57); `table` (the decoded table in fixed arrays, its groups as their checked bytes with an index of commands); `decode`, `encode` and `check` of the table image, of the bodies of the records of types 28 to 33, of PAGE_STATE's payload and of the animation operations shared with the `ANIMATE` record; `default_send_all`; `Evaluator` (the one state of RULE-7, with `handle`, `tick` and `close` of RULE-96 and the handlings of RULE-5), which is given events (input events, the server's records, cues, state queries) and, between handlings, the metered values, and a `World` trait through which it reads target rectangles and tracked synthesizer values and to which it issues outputs at once: every command of a run it does not carry out itself is handed to the `World` as its record type and body, amounts resolved, to be applied by the code that applies that record from the server; and the interest mask and watch list of a table. Because it has no dependency, it reads the bodies of `CONTROL`, `SPRITES` and `NAPLPS_OBJECTS` through a **body check** its caller passes to `decode` and `check` (a function from a record type and a body to accepted or refused, and for a `CONTROL` its page and flags); `neoteletext-web` provides the one such function, built on the records' own readers, and the server and every receiver pass that one. Key codes, family codes and parameter numbers are plain numbers to it; the callers that know them check what the crate cannot. The words of the program protocol for every code of the table (trigger kinds, value spaces and their properties, operations, start modes, the firing's properties and the row parameter `p`) are one table of the crate, `neoteletext_rules::names`, so that the server, `neottx` and the kits use the same words (DEC-6648 item 9).
- **Reason and source.** DEC-6522 item 9: the server checks a table "with the browser's own code". One implementation of decode and check means a table the server accepts is a table every receiver accepts; no dependency means it builds for every engine target, microcontrollers included.
- **Verification.** `cargo xtask check-deps` and `check-io` list it with nothing permitted; it builds for `thumbv6m-none-eabi`; `cargo xtask features` builds it alone.

**RULE-57 [engine: neoteletext-rules; every repository]. The limits: every figure in this one requirement, each a named constant defined once.**
- **Statement.** This requirement is the one place in this document where a limit of a page's rule table is given as a figure; it is rdm requirement REQ-6608, and the two MUST agree. Every other requirement refers to a limit by its constant's name. Each limit is a maximum, never a minimum. Each MUST be one named constant, defined once, in the engine's crate `neoteletext_rules::limits`, and used by name wherever it is applied: by the server when it checks a table, by the receiver when it loads one, and in the kits' documents (generated from the constants, or compared with them by a test); no other file may state one of these figures as a literal. A table that passes any limit, when a program sends it or when a receiver is sent it, MUST be refused whole, with a refusal that names the limit's constant and its value (RULE-39, RULE-70); it is never accepted in part and never cut short. Every limit counts for one page — one page number and sub-code — alone (RULE-112).

| Constant | Value | What it bounds |
|---|---|---|
| `MAX_GROUP_COMMANDS` | 32 | commands in one group |
| `MAX_GROUPS` | 64 | groups a page, the unnamed ones the server makes among them |
| `MAX_GROUP_DEPTH` | 4 | the depth to which a group may run other groups; no cycle is allowed at any depth |
| `MAX_RUN_COMMANDS` | 128 | commands applied by one run of a group, counting every group it runs |
| `MAX_COMMAND_BYTES` | 256 | bytes of one command's body in a group |
| `MAX_GROUPS_BYTES` | 16,384 | bytes of all of a page's groups together, as framed |
| `MAX_RULES` | 64 | rules a page |
| `MAX_ROWS` | 64 | binding rows a page |
| `MAX_SEQUENCES` | 8 | sequences a page |
| `MAX_SEQUENCE_STEPS` | 64 | steps in one sequence |
| `MAX_SEQUENCE_REPEAT` | 255 | the stated repeats of a sequence, 1 to this; or until stopped |
| `TIMERS` | 8 | timers a page, exactly, `t0` to `t7`, beside the page timer |
| `VARIABLES` | 16 | variables a page, exactly, `v0` to `v15`, each a saturating 32-bit signed integer |
| `MAX_CONDITION_TERMS` | 8 | terms in one rule's condition |
| `MAX_CONDITION_DEPTH` | 3 | depth of nesting in one rule's condition |
| `MAX_CONDITION_NODES` | 16 | nodes in one rule's condition, terms and operators together |
| `MAX_SET_MEMBERS` | 8 | constants in an `in_set` |
| `MAX_AND_OR_CHILDREN` | 8 | children of an `and` or an `or` |
| `MAX_TRIGGERS_PER_RULE` | 4 | triggers on one rule, any of which fires it |
| `MAX_KEYS_PER_TRIGGER` | 16 | keys in one trigger's key set |
| `MAX_RULE_ROWS` | 128 | the sum, over a page's rules, of the rows each names, a rule without rows counting one: the most firings one event can cause |
| `MAX_COMMAND_BINDINGS` | 8 | bindings on one command |
| `MAX_RECTS` | 16 | rectangles a page's table declares |
| `MAX_SEQUENCE_TICKS` | 216,000 | a sequence's length in ticks (one hour) |
| `MAX_TIMER_TICKS` | 216,000 | `ticks` of `every` and `after`, the period of a timer's phase and of a sequence's `beat` start (one hour) |
| `MAX_START_TICKS` | 216,000 | how far after the present tick a sequence's start `at` a page tick may be (one hour) |
| `MAX_CUE` | 127 | the highest cue number |
| `MAX_EVENTS_PER_TICK` | 16 | events handled in one tick: input events, the server's records the evaluator carries out, cues and state queries together (a per-tick budget, RULE-5) |
| `MAX_EVENT_COMMANDS_PER_TICK` | 2,048 | commands applied by the runs of the events handled in one tick (a per-tick budget): `MAX_EVENTS_PER_TICK × MAX_RUN_COMMANDS`, asserted |
| `MAX_EVENT_REPORTS_PER_TICK` | 32 | `REPORT` commands applied by the runs of the events handled in one tick (a per-tick budget): `2 × MAX_EVENTS_PER_TICK`, asserted, so that every event of a full tick may report its firing and one value |
| `MAX_QUEUED_EVENTS` | 64 | events waiting for a later tick, in arrival order |
| `MAX_KEYS_DOWN` | 16 | keys tracked as down |
| `MAX_POINTER_OBJECTS` | 16 | objects the pointer is followed inside at once |
| `MAX_TABLE_VALUES` | 64 | distinct values a table reads |
| `MAX_TABLE_TARGETS` | 64 | distinct controls and objects a table names by a constant |
| `MAX_WATCHED` | 32 | distinct metered values a table reads (RULE-33) |
| `MAX_TABLE_BYTES` | 32,768 | a table's image |
| `MAX_TABLE_FRAGMENT` | 8,172 | image bytes in one RULES record: `MAX_FRAMED_BODY` less the 12 bytes before them, asserted |
| `MAX_STATE_BYTES` | 1,800 | a PAGE_STATE payload, asserted from its parts |
| `MAX_CYCLE_PERIOD` | 3,600 | ticks a frame of a cycle (ANIM-14) |
| `MAX_FRAME` | 15 | the highest frame number (ANIM-14) |
| `MAX_CATCH_UP_TICKS` | 6 | overdue ticks run in one wake |
| `TICKS_PER_SECOND` | 60 | the clock (ANIM-1 asserts the engine's and this agree) |

- **The per-tick budgets.** `MAX_EVENTS_PER_TICK`, `MAX_EVENT_COMMANDS_PER_TICK` and `MAX_EVENT_REPORTS_PER_TICK` are the owner's "maximum once in 1/60 second" (DEC-6635 item 4): they count against the tick an event is handled in, and an event over any of them waits for the next tick in the queue of `MAX_QUEUED_EVENTS`, never dropped while the queue has room; the first event of a tick is always handled. They bound events, not the table: a table at every other limit is never refused for them, and they do not apply to a tick step. A rule is not limited to one firing a tick.
- There is no limit on the work a run of a group costs (the owner: "i agree with constraining the number of commands in a group but not work cap"). The receiver's general budgets, which apply to every command however it arrives — the repaint budget (REQ-6368), the animation budget (ANIM-16), the trusted core's report and sound command budgets (RULE-52) and the sound helper's queue and overrun figures (RULE-62) — are not limits of the rule table; each is stated once, in the requirement named, and defined in its own crate.
- Withdrawn with the first form: `MAX_ACTIONS` (actions a rule), `MAX_VARIABLES` (declared variables), `MAX_TIMERS` as a count of declarations, `MAX_SUBPAGE_MASKS`, `MAX_ACTIONS_PER_TICK`, and the server's `MAX_KEPT_TABLES` (the server keeps no table, RULE-40).
- Withdrawn by DEC-6635, with the mechanisms they bounded: `MAX_ARMED_RUNS` and `MAX_ARM_TICKS` (armed runs, item 6; `MAX_START_TICKS` bounds a sequence's start instead); `MAX_HOLD_TICKS`, `MAX_DOUBLE_TICKS` and `MAX_RECENT_PRESSES` (the held and double-press triggers, item 7); `ROW_PARAMETERS` (a row is one parameter, item 8); and `MAX_CUES_PER_TICK` and `MAX_QUEUED_COMMANDS`, whose events are now handled at once in one arrival order and are counted by `MAX_EVENTS_PER_TICK` and `MAX_QUEUED_EVENTS` (item 1; section 15, item 46).
- **Reason and source.** The owner, 18 November 2026: "ensure that set of limits is put into a single requirement" (REQ-6608); DEC-6587 items 2, 6 and 7; DEC-6522 items 6 and 10; the engine's rule that every constant is defined once (REQ-GEN-014, DEC-646). The limits REQ-6608's first version did not name (from `MAX_CONDITION_NODES` down in the table) are this document's (section 15, item 41), and REQ-6608 was revised to hold them; DEC-6635 items 4, 6, 7 and 8 removed the limits of the mechanisms it withdrew and set the per-tick budgets, whose figures are section 15, item 45, and REQ-6608's third version holds them.
- **Verification.** In the engine, for each constant that bounds a table: a table exactly at the limit is accepted and one over is refused whole with that limit's name; for each per-tick budget, events up to it are handled in one tick and the next waits for the following tick (RULE-5's tests); a table with a cycle of groups is refused; a test asserts the constants' values are this table's; `cargo xtask check-constants`. In the server: the same pairs of tables as program messages. In the kits: the documents' table of limits generated from, or compared with, the constants. A check script step fails if one of these figures appears as a literal beside the name of a limit outside `neoteletext-rules`.

**RULE-58 [neoteletext-browser]. Where the table lives in the browser: the decoder evaluates, the trusted core gates.**
- **Statement.** The decoder process of the page's channel — confined, with no network, no file access and no secrets, and already the reader of every record of that channel — MUST assemble and decode the table (with `neoteletext-rules`), hold it, run the evaluator on its own presentation clock, and apply each command of a run with the code that applies the same record from the server. It holds one table at most for each view: that of the page the view has selected, keyed by page number and sub-code. The trusted core names the open page to the decoder (`RulesPage`) as a page number and sub-code only once that sub-page is on screen, from the stamp of the frame drawn, and again when the sub-code on screen changes; a RULES record for another page while one is open is dropped and counted, and one is kept for a page that is not open only while no page is open (as while its tab is paused, or before the trusted core names the page) (the browser's DEC-6659 items 1 and 2). The trusted core MUST NOT decode or evaluate a table, and `neoteletext-rules`' evaluator MUST NOT be linked into it; it does only RULE-52. A table is evaluated only for the **open page**: the one page of the active tab that keys would go to (the browser's REQ-1378). A page that is merely visible in the overview or a wall, or in a tab that is not active, is paused (RULE-111): no evaluator runs, no local sound plays and it is given no input. While no open page has a table, the decoder keeps no 60-a-second wake for rules (it still wakes for flash and animation, ANIM-1).
- **Reason and source.** Evaluation of an untrusted table belongs in a confined process (the browser's requirement 1.2, DEVELOPMENT.md section 1 item 5); the decoder already holds the page, its objects and its instruments' trackers and already applies every record a group can hold.
- **Verification.** The browser's dependency-tree check finds `neoteletext-rules`' evaluator in the decoder and not in the trusted core; a test that an idle page with no table causes no 60-a-second wake.

**RULE-59 [neoteletext-app-server]. The server checks and encodes with the same crates.**
- **Statement.** The server MUST depend on `neoteletext-rules` and `neoteletext-web` at the engine revision it pins, build each table image and each command record with their `encode` — one function for a command whether it is sent directly or put in a group — and pass each image through `check`, with `neoteletext-web`'s body check, before sending (RULE-39). It MUST resolve key names with `neoteletext_input::keys::code` and synthesizer field names with the families' `PARAMETERS` tables (RULE-29), and has no table, key list or parameter list of its own.
- **Reason and source.** DEC-6522 item 9; DEC-6462; DEC-6587 ("the server checks a group by the checks it already runs").
- **Verification.** A server property test: every table the server accepts decodes in `neoteletext-rules` to the same table.

## 10. Latency: from a key to sound and to the picture

**RULE-60 [engine: neoteletext-audio; neoteletext-browser]. A local sound: an instrument the page keeps open, played by `LOCAL_MIDI`.**
- **Statement.** The audio profile has the **local sound**: a synthesizer sound of any family that plays notes (codec codes 13 to 18; not the synth6581 family, which has no note messages) whose OBJECT record carries tag 9, `TAG_LOCAL`, with one value byte, 1. It is announced as a stored sound of one block of that family, and its one block is the **setup**: an event list in the block form of midi-architecture.md MIDI-23 with every event at tick 0, at most `MOST_BLOCK_BYTES` (1,005) bytes, applied in order when the instrument is made. It names its banks as other sounds of its family do. A receiver never renders a local sound from blocks and never streams it: when a play command (a `CONTROL` record, from the server or in a group) starts it on an audio channel, the receiver makes the family's instrument in its sound output stage, applies the setup, and from then on gives it the messages of `LOCAL_MIDI` commands (RULE-21) as they arrive. Stop and gain act on its audio channel as on any sound. A local sound MUST be played with a page scope and belongs to the page that is open when it starts (RULE-112); it is silent while that page is paused and ends, with all notes released, when that page is closed or its connection ends (RULE-111). At most `MOST_LOCAL_SOUNDS` (2) play at once in a view; a third play is refused and counted. A receiver without a sound output stage of this kind ignores a local sound's OBJECT, as it ignores a codec it does not have.
- **Reason and source.** The owner's goal: "INSTANTLY PLAYING ON A KEYPRESS". A local sound has no timeline of the server's to keep, so it needs no buffer.
- **Verification.** Engine tests: the OBJECT with tag 9 parses, and the audio receiver gives a sink the local sound's start instead of a stream; browser tests that a local sound ends when its page closes and when its connection ends.

**RULE-61 [neoteletext-app-server]. The local sound in the program protocol.**
- **Statement.** The `sound` message has the kinds `synth7_local`, `synth106_local`, `synth60_local`, `synthd_local`, `synth53_local`, `synth52_local`, `synth51_local`, `synth8_local` and `synth80_local`. Each has the fields of its family's `_live` kind (`connections`, `handle`, `generation`, `banks`, and the family's own options such as synth8's key mode), and `setup`: a list of at most 64 of the family's events (`Synth106Event` and the others), each with `time_us` 0, which the server packs into the setup block and refuses with `block_full` when they do not fit. `play` of a local sound sent directly MUST name a `page`, with `loop` and `after` false, else `out_of_range`, and reaches only connections that have a sub-code of that page number selected; in a group it takes its page from the table. Example:

```json
{"type":"sound","kind":"synth106_local","connections":"all","handle":1,"generation":1,"banks":[2],
 "setup":[{"event":"program_change","channel":1,"program":0,"time_us":0}]}
```
- **Reason and source.** DEC-6462: the server packs; the kits send typed fields.
- **Verification.** Server tests: the records built for each family; the refusals.

**RULE-62 [neoteletext-browser; engine: neoteletext-audio-mix]. The sound helper renders a local sound in blocks of 128 samples.**
- **Statement.** The sound helper MUST link `neoteletext-audio-instruments` and hold each local sound's instrument. The engine mixer MUST gain a **pulled voice**: a voice whose samples the mixer asks for as it mixes, at 48,000 samples a second, through the mixer's existing resampler to the device's rate. For each device buffer the helper renders each pulled voice just in time, in blocks of `LOCAL_BLOCK_SAMPLES` (128 samples, 2.67 milliseconds), and before each block applies every MIDI message queued for that instrument, in arrival order; the queue holds `LOCAL_MIDI_QUEUE` (256) messages, and one arriving at a full queue is dropped and counted. No buffer is held ahead: a message waits at most one block. While a local sound is open the helper asks the output device for a small buffer (RULE-97). While a local sound plays, the helper keeps the output device running, so that a note never waits for the device to start; a view's speaker mark still follows what is heard (a level above 0). When rendering a view's local sounds takes longer than the time of the buffer it fills for `LOCAL_OVERRUN_BUFFERS` (8) buffers running, the helper stops that view's local sounds with all notes released and reports it (fault 7). Each constant is defined once, in `neoteletext-audio-mix` (`LOCAL_BLOCK_SAMPLES`) and the browser's `sound` crate (the queue and the overrun count).
- While the page a local sound belongs to is paused (RULE-111 case 4) the helper renders nothing for it, with every note released first, and keeps its instrument; when its page is closed or its connection ends the instrument is dropped. The device buffer the helper asks for while a local sound is open is RULE-97's.
- **Reason and source.** Rendering inside the audio callback is the only place where the delay is one block and the device's own buffer. The instruments are `no_std`, integer-only and never allocate, which is what code on an audio thread must be.
- **Verification.** A helper test with a scripted device: a note on queued before a buffer sounds within the first 128 samples of that buffer; the overrun stop; a measured figure for each family's cost of rendering one buffer of eight held notes, recorded with the date.

**RULE-63 [neoteletext-browser]. The messages that carry a local sound, metering and cues.**
- **Statement.** The voice operations of `protocol::audio` are, beside those that existed before the first form:

| Operation | From | Fields |
|---|---|---|
| `LocalBank` | the decoder | audio channel; the sound (handle, generation); bank index 0 to 9; the bank image, at most 16,384 bytes (`MOST_BANK_BYTES`) |
| `Local` | the decoder | audio channel; the sound; family code 13 to 18; variant; the family's option byte; split; gain; fade; duck; the setup block, at most 1,005 bytes. Starts the instrument with the banks given for that channel and sound since the last `Local` |
| `LocalMidi` | the decoder | audio channel; status; data 1; data 2 — to the local sound on that channel |
| `Watch` | the trusted core alone | the watch list of RULE-33: a count 0 to 32 and that many slots of audio channel, kind and part |
| `Cue` | the decoder | a cue mark of RULE-109: audio channel; the sound (handle, generation); the position, an unsigned 64-bit count of samples from the stream's start; the cue number 0 to 127 |
| `Pause` | the trusted core alone | the view's local sounds are silenced with notes released, or resumed (RULE-111 case 4) |

- and the sound helper's messages to the trusted core have `Metered` (the view's channel number, a count and that many bytes, RULE-33), `LocalOverrun`, and `CueHeard` (the view's channel number, the audio channel, the cue number). The trusted core checks every field's bounds, never reads a bank image or a setup block, and passes them on unread, as it passes samples. Between the trusted core and a decoder the messages are: `Input` to the decoder with its sequence number; `Metered` and `CueHeard` to the decoder; `Paused` and `Resumed` to the decoder; `RulesOpen` from the decoder with the interest mask, the watch list and the wheel rectangles of RULE-51; `Report` from the decoder (RULE-52 item 3, with the rule and the row); `PageState` from the decoder; `Fault` from the decoder. The first build took voice operations 12 to 15 (`LocalBank`, `Local`, `LocalMidi`, `Watch`), the sound helper's kinds 5 (`Metered`) and 6 (`LocalOverrun`), and the pipe kinds 178 to 187 (`RuleInput`, `Metered`, `RulesOpen`, `Report`, `PageState`, `RulesFault`, `RulesQuery` to the decoder, `RuleCounters`, `RulesQuery` from the fetcher, `RulesPage`), which stay; `RulesPage` now names the page number and sub-code, or none, and its "none" is the pause of RULE-111. The messages the second form adds (`Cue`, `Pause`, `CueHeard`, and RULE-98's `FramePhase`) take the next operation and kind numbers free across every pipe at the browser's head, as the protocol crate's rule for kind numbers requires.
- **Reason and source.** The existing shape: one payload form on both pipes, each side accepting only the operations meant for it.
- **Verification.** Protocol tests for each message at its bounds, and that the decoder may send neither `Watch` nor `Pause`.

**RULE-64 [neoteletext-browser]. The latency budget from a key to sound.**
- **Statement.** With a local sound playing, the path of a key press is, hop by hop, with the most each may add:

| Hop | Most |
|---|---|
| The interface process reads the key from the operating system and writes its intent to the trusted core | 1 ms |
| The trusted core finds the open page, checks the interest mask and writes the event to the decoder | 1 ms |
| The decoder reads the event, handles it at once (RULE-96) and writes `LocalMidi` to the trusted core, before any other work | 1 ms |
| The trusted core checks it and writes it to the sound helper | 1 ms |
| The sound helper queues it until the next block of 128 samples | 2.7 ms |
| The block is rendered into the device buffer being filled | one device buffer: 5.3 ms at the 256 frames RULE-97 asks for; 2.7 ms at 128; 10 ms at the usual 480 after RULE-97's fallback |

- No hop waits for the tick, and none may wait on a timer of any kind (REQ-1333 as amended). The greatest delay is the sum, `4 + 2.7 + B` milliseconds for a device buffer of `B` milliseconds. The median is the hops as they are when nothing waits (1 millisecond for all four, as measured between threads on 18 November 2026), half a block (1.3) and half a device buffer.
- The browser MUST meet, from the interface process reading the key to the first sample of the note being handed to the output device:

| Device buffer granted (RULE-97) | At most | Median, or less |
|---|---|---|
| 128 frames (2.7 ms) | 10 ms (`4 + 2.7 + 2.7 = 9.4`) | 5 ms (`1 + 1.3 + 1.3 = 3.6`) |
| 256 frames (5.3 ms), the size asked for | **12 ms** (`4 + 2.7 + 5.3 = 12.0`) | **6 ms** (`1 + 1.3 + 2.7 = 5.0`) |
| 480 frames (10 ms), after the fallback or where the device grants no less | 17 ms (`4 + 2.7 + 10 = 16.7`) | 9 ms (`1 + 1.3 + 5 = 7.3`) |

- For a size between two rows the bounds are those of the next row down. The `LocalMidi` message itself MUST leave the decoder within 2 milliseconds of the interface reading the key, at most, whatever the phase of the tick, unless the tick's budget is spent and the event waits (RULE-5), which the test of RULE-66 does not cause. The output device's own delay after its buffer is the machine's and is reported beside the figure.
- Before DEC-6580 the same path was budgeted at 34 milliseconds at most and 20 in the median (a wait of up to 16.7 for the tick and a device buffer of 10), and measured between threads at 24 to 27 at most and 12 to 15 in the median.
- **Reason and source.** The owner's goal of sound "INSTANTLY" on a key press; the owner's decision DEC-6580 items 1 and 2 (18 November 2026), which take the tick's wait and half the device buffer out of the path: "about 5 ms median and 12 to 15 ms at most, the range of a hardware synthesizer's own delay". DEC-6635 item 1 keeps these bounds: sound leaves on arrival as before, and no other effect of an event waits for the tick either.
- **Verification.** RULE-66's measurement.

**RULE-65 [neoteletext-browser]. The latency budget from a key to the picture.**
- **Statement.** A command that changes the picture (`ANIMATE`, `SPRITES`, `NAPLPS_OBJECTS`) changes the page's animation state the moment it is applied, in the event's own handling (RULE-96); it does not wait for a tick (DEC-6635 item 1). The decoder MUST paint the damage at the next **paint point** after the change, as a damage repaint of the changed rectangles only (ANIM-4), from the state then current, so that every change made before one paint point costs one repaint; and give the frame to the trusted core at once, marked as the answer to input so that the core's and the interface's "drawn as it arrives" rule applies (the browser's requirement 18.12, REQ-6400).
- **Paint points.** With the interface's `FramePhase` (RULE-98) in force, a paint point is every moment `TICK_LEAD_MICROSECONDS` (4,000) before one of the interface's compositions, on every display, whether or not the clock is locked to it; the frame painted at a paint point MUST be in that composition. With no `FramePhase` in force, or one older than `PHASE_STALE_MILLISECONDS`, the decoder paints at once after the handling, no more often than the trusted core's least interval between a page's frames (one tick, ANIM-1).
- The path, with `R` the display's refresh period, and the most and the median each part may add:

| Part | Most | Median |
|---|---|---|
| The interface reads the key and the trusted core passes it to the decoder | 2 ms | 0.5 ms |
| The change waits for the next paint point | `R` | `R ÷ 2` |
| The repaint, and the frame's way through the trusted core to the interface, inside the paint point's lead | 4 ms | 4 ms |

- From the interface reading the key to the interface composing the frame that shows the change, the browser MUST take at most `6 + R` milliseconds and `4.5 + R ÷ 2` or less in the median, plus the display's own scan-out:

| Display | At most | Median, or less |
|---|---|---|
| 60 hertz (`R` 16.7 ms) | **23 ms** (`2 + 16.7 + 4 = 22.7`) | **13 ms** (`0.5 + 8.3 + 4 = 12.8`) |
| 120 hertz (`R` 8.3 ms) | 15 ms (`2 + 8.3 + 4 = 14.3`) | 9 ms (`0.5 + 4.2 + 4 = 8.7`) |
| 144 hertz (`R` 6.9 ms), which the clock cannot lock to | 13 ms (`2 + 6.9 + 4 = 12.9`) | 8 ms (`0.5 + 3.5 + 4 = 8.0`) |

- With no `FramePhase`, the bound is that of the trusted core's least frame interval and the display's refresh together: at most `2 + 16.7 + 1 + R` and in the median `0.5 + 8.3 + 1 + R ÷ 2`. Before DEC-6635 an event's picture change waited for the next tick, so these were the 60-hertz figures on every display (and one refresh period more where the clock could not lock); before DEC-6580, 39 milliseconds at most.
- A `becomes` rule on a metered `level` adds the meter's age (RULE-33) and the tick step's check (RULE-11): the note begins at most 12 milliseconds after the key (RULE-64); the report that holds its level leaves the helper within a sixtieth of a second and one device buffer of that (16.7 + 5.3); it reaches the decoder in 2 more and is applied at once (RULE-7); it is checked at the next tick step, at most 16.7 later; and, with the clock locked (RULE-98), that tick step is at a paint point and its frame is composed 4 after it. A meter segment MUST light **at most 57 milliseconds** after the key (`12 + 22 + 2 + 16.7 + 4 = 56.7`) and **30 milliseconds or less in the median** (`5 + 11 + 1 + 8.3 + 4 = 29.3`) on a display the clock locks to; on one it cannot lock to, one refresh period more at most and half of one in the median.
- **Reason and source.** The owner's goal: "INSTANTLY DISPLAYING LEVELS VISUALLY ALSO IN RESPONSE TO THE KEYPRESS"; the owner's decision DEC-6580 item 3; DEC-6635 item 1 ("The picture is drawn at the next display frame from the state then current, so a picture change is seen as soon as the screen can show it and several changes within one frame cost one repaint"). Paint points on every display, locked or not, are section 15, item 50.
- **Verification.** RULE-66's measurement.

**RULE-66 [neoteletext-browser]. The measurement is kept, between real processes, before and after.**
- **Statement.** The browser's repository MUST hold a timed test, built on the script that already times a key to the pixels (DEC-6398 item 8), that runs the browser as it ships — the interface, the trusted core, a confined decoder and the sound helper as four operating-system processes joined by their real pipes, not as threads of one test process — with the music player's page 101 open and its local sound playing. It injects a key at the interface's input and records, on one monotonic clock read in each process: the time the interface read the key; the time the decoder wrote `LocalMidi`; the time the sound helper's test device was handed the first non-zero sample of the note; the time the interface composed the frame that shows the changed rectangle; and the time it composed the frame that shows the first lit meter segment. It does so over at least 200 keys at random phases of the tick and of the device buffer, prints the least, median and greatest of each interval with the device buffer granted and the display's refresh rate, and fails when a bound of RULE-64 or RULE-65 is passed. It builds the programs it times (DEVELOPMENT.md section 8).
- The test MUST be able to run the browser with each of three changes switched off for the measurement alone — events held for the tick (the decoder's host keeping each event and giving it to the evaluator only after the next tick step, so that its sound and its picture both wait for the tick, as they did before DEC-6580), the device buffer left at 480 frames, and the tick left unlocked with paint points at the ticks — by a setting of the test's own that no shipped configuration and no page can reach, and that the evaluator's interface does not offer (RULE-96), so that the same test on the same machine on the same day gives the figures before and after each change. The six sets of figures (each change off, then on) are recorded with the date, the machine and the output device in the rdm requirement that carries this rule, and the change is not called done without them.
- **Reason and source.** DEVELOPMENT.md section 2.1: performance claims carry before and after numbers from an instrument shown to exercise the changed code. DEC-6580: "Each is measured before and after, between real processes"; DEC-6635 changes what the first setting holds back, from sound alone to every effect of an event. The figures of 18 November 2026 were taken between threads of one process, which leaves out the processes' scheduling and their pipes.
- **Verification.** It is the verification.

**RULE-97 [neoteletext-browser]. A small device buffer while a local sound is open.**
- **Statement.** The sound helper opens its output device with a buffer of `USUAL_DEVICE_FRAMES` (480 frames at 48,000 a second, 10 milliseconds; at another rate the same time). While at least one local sound is open in any view — from the `Local` operation that starts it (RULE-63) until it ends, which is when it is stopped or replaced, a paused one still counting as open (the browser's DEC-6659 item 6) — the helper MUST instead run the output device with a buffer of `LOCAL_DEVICE_FRAMES` (256 frames at 48,000 a second, 5.33 milliseconds; at another device rate the number of frames nearest that time):
  1. **Asking.** On the first `Local` operation while no local sound is open, before the instrument is made, the helper asks the device for `LOCAL_DEVICE_FRAMES`. Where the device offers a range, it takes the size in the range nearest 256 and not below `LEAST_DEVICE_FRAMES` (128); where the device grants only its own size, it takes that. A device that grants more than 480 frames is left as it was. The helper records the size granted, which RULE-64's bound follows and RULE-66 prints.
  2. **Changing over.** If the device must be reopened to change its buffer, the helper does so between two buffers, keeps the mixer and every voice in it as they are (no stream is restarted, no instrument reset), and fills the first buffer of the new size from where the last of the old ended. The local sound's start does not wait for more than that one reopening.
  3. **Fallback.** The helper counts an underrun whenever the device reports one, and an overrun whenever filling a buffer took longer than the buffer's own time. On the first underrun or overrun while the small buffer is in use, it changes back to `USUAL_DEVICE_FRAMES` as item 2 says, stays there until every local sound that was open at that moment has ended, and reports it once to each view that had one, as fault 7 (`local_overrun`, RULE-48) with count 0, which distinguishes it from RULE-62's stop, whose count is 1 or more. The local sounds go on playing: only their delay grows, by RULE-64's last row. RULE-62's stop after `LOCAL_OVERRUN_BUFFERS` (8) overrunning buffers is unchanged and is counted at whichever size is in use.
  4. **Returning.** When the last local sound ends, the helper keeps the small buffer for `LOCAL_DEVICE_LINGER_MILLISECONDS` (2,000) and then, if none has opened, changes back to `USUAL_DEVICE_FRAMES`, so that turning from one playing page to another does not reopen the device twice. A local sound that opens after a fallback has ended asks for the small buffer again.
- A page with no local sound never causes any of this: the size is 480 frames as before, for every other sound. Each constant is defined once, in the browser's `sound` crate, beside `LOCAL_MIDI_QUEUE`.
- **Reason and source.** The owner's decision DEC-6580 item 2: "the sound helper asks the audio device for a buffer of 128 or 256 frames … When the device reports an underrun or the helper's own overrun count rises, it falls back to the larger buffer for that sound's life and reports it once (the existing local-overrun fault). Pages without local sounds keep the larger buffer and pay nothing." 256 is asked for and 128 accepted (section 15, item 19).
- **Verification.** Helper tests with a scripted device: the size asked on the first `Local` and the size after the last ends and the linger passes; a second local sound within the linger causes no change; one scripted underrun changes back once, reports fault 7 with count 0 once, and leaves the note sounding without a break in its samples across the change; a device that grants only 480 is left alone; no change of size for a page with ordinary sounds only. RULE-66's figures with the small buffer off and on.

**RULE-98 [neoteletext-browser]. The tick is locked to the display's refresh.**
- **Statement.** The decoder's presentation clock (RULE-4, ANIM-1) MUST be phased against the interface's frames, so that a tick's picture is in the next frame composed and not the one after:
  1. **The interface reports its frames.** The interface process, which alone knows the display, sends the trusted core a `FramePhase` message — the refresh period in microseconds (unsigned 32-bit, 2,000 to 100,000) and the time of its next frame composition on the machine's monotonic clock in microseconds (unsigned 64-bit), which every process of the browser reads the same — when it first knows them, whenever the window moves to a display with another period, and whenever the time it would predict from its last message is wrong by more than `PHASE_REPORT_MICROSECONDS` (500). Where the platform gives it no frame times it sends none.
  2. **The trusted core passes it on**, bounds checked and otherwise unread, to the decoder of each view's open page (`ToDecoder::FramePhase`), and again to a decoder when a page opens in a view. It takes the next kind numbers free, as RULE-63's messages did.
  3. **The decoder locks when it can.** The display can be locked to when its refresh rate is a whole multiple of 60 a second to within `LOCK_TOLERANCE_PARTS_PER_THOUSAND` (5): 59.7 to 60.3 hertz, 119.4 to 120.6, 179.1 to 180.9, 238.8 to 241.2, and so on. The compositions are at the reported time and every whole period before and after it. A **target** is any moment `TICK_LEAD_MICROSECONDS` (4,000) before a composition. Before it waits for each tick, the decoder takes the target nearest that tick's due time and moves its clock's start toward it — earlier or later, whichever is the shorter way — by the distance between them or by `PHASE_SLEW_MICROSECONDS` (100), whichever is less, and by nothing when the distance is under `PHASE_LOCKED_MICROSECONDS` (200). A page that opens puts its page tick 0 on the first target not in the past, with no slew. On a display of 60 hertz every composition then holds one tick's picture; on one of 120 hertz or more every tick is 4,000 microseconds before a frame boundary and every second, third or fourth frame holds a tick's picture. Ticks are still 60 a second by the decoder's clock, counted and never skipped or repeated (RULE-4); the slew is at most 6 parts in a thousand of a tick, so page time follows the display's own clock within that.
  4. **When it cannot.** On a display whose rate is no such multiple (50, 75, 100 or 144 hertz), or with no `FramePhase` for `PHASE_STALE_MILLISECONDS` (1,000), the decoder's clock runs free as RULE-4 gives it. An event's picture change still waits only for the next paint point, which follows the display's own frames whenever a `FramePhase` is in force (RULE-65); what the tick step changes (a timer's group, a sequence's step, a `becomes` rule, a frame cycle) waits one refresh period more at most, as RULE-65's meter bound says.
  5. **The lead holds the work.** `TICK_LEAD_MICROSECONDS` is the time for a tick's evaluation and repaint and for its frame to pass the trusted core and reach the interface before composition: 1 millisecond for each of those three and one to spare. The same lead holds the repaint of a paint point (RULE-65). A tick or a paint point whose frame reaches the interface after the composition it was meant for is counted (`late_frames`, shown with RULE-72's counters), and the frame is in the next composition.
- No record, no page and no channel can read or change the phase; the push protocol and the program protocol are unchanged. The decoder learns from `FramePhase` only the refresh period and phase of the viewer's display, which it does not report anywhere: threat 12 of section 12.3 is unchanged, since a table still reads nothing of time but its page tick. Each constant is defined once, in the browser's `protocol` crate.
- **Reason and source.** The owner's decision DEC-6580 item 3: "The presentation clock's ticks are phased so that a tick's work finishes just before the interface composes a frame … On a display refreshing faster than 60 times a second the tick stays 60 a second and falls on a frame boundary. No record or protocol changes." The slew and what is done on a display that is no multiple of 60 are section 15, items 20 and 21.
- **Verification.** Decoder tests with a scripted clock and scripted `FramePhase` messages: at 60 hertz the ticks come to rest 4,000 microseconds before each composition within 200, having moved no more than 100 a tick; at 120 hertz every tick is 4,000 before a composition; a display of 59.94 hertz is followed with no tick skipped or repeated over 10 minutes; 144 hertz and a stale phase leave the clock free; a page's tick 0 is on the target. A protocol test of `FramePhase` at its bounds. RULE-66's figures with the lock off and on.

Numbers RULE-67 to RULE-69 are not used. RULE-96 (section 2), RULE-97 and RULE-98 were added on 18 November 2026 for DEC-6580.

## 11. Refusal, faults and counters

**RULE-70 [engine: neoteletext-rules; neoteletext-browser]. A table is accepted whole or refused whole.**
- **Statement.** `decode` MUST refuse an image when any field is outside its range, any reserved bit or byte is not 0, any count exceeds its limit, any number refers to a rectangle, row, group or sequence the table does not have, a condition is not one tree, a command's type is not allowed or its body is refused by its record's reader, a binding names a field or a source RULE-106 does not allow, the groups run each other in a ring or too deep or a run would pass `MAX_RUN_COMMANDS` commands, a row's `p` does not give a valid target number where a trigger uses it, a `by_row` key set's count is not its rule's row count, a trigger, a source, a `fired` property or a parameter byte is of a kind DEC-6635 withdrew, the image is short, or bytes follow its end. Nothing of a refused table is kept or evaluated: the page then has no table (and so sends no input, RULE-50), and the receiver reports fault 1 (RULE-48). A receiver never repairs a table, skips a faulty rule or command, or holds a limit lower or higher than RULE-57's.
- **Reason and source.** DEC-6522 item 10; DEC-6587 item 6 ("a table over any of them is refused whole").
- **Verification.** The fuzz target `rules_decode`; a test that each single-byte corruption of a valid table either decodes to a valid table or is refused whole.

**RULE-71 [neoteletext-browser]. A table is trusted for nothing.**
- **Statement.** The decoder MUST treat every number in a table as untrusted when it is used as well as when decoded: an object number that names nothing, a handle with no sound, an audio channel with no local sound and a frame beyond an object's frames each make the command a counted no-op (RULE-118). No table can make the decoder allocate: every structure the evaluator uses is a fixed array sized by RULE-57.
- **Verification.** The fuzz target `rules_evaluate` under a counting allocator that fails the test on any allocation inside a handling.

**RULE-72 [neoteletext-browser]. Counters.**
- **Statement.** For the open page the decoder MUST count, and the browser's console MUST show to the page's author (as it shows a channel's log): tick steps run; events handled, waited and dropped; rules fired, and firings dropped beyond `MAX_RULE_ROWS` (RULE-5); groups run; commands applied; commands skipped; sequence starts late and skipped; cues heard and dropped; reports asked for, sent and dropped; ticks run late and the longest tick step's and handling's time; the sixteen variables; the newest metered values. The counts are the receiver's own and are sent to the channel only as the faults of RULE-48.
- **Verification.** A console test.

## 12. Security analysis

This section is the analysis DEVELOPMENT.md sections 2.3 and 14 require of a feature that reads outside input and adds an output. It is the first form's analysis revised for the second form. Its findings are applied in the requirements named.

### 12.1 What is protected

1. The viewer's machine: its processor, memory, sound output and screen.
2. The viewer's input: what they type and click, on this page and on every other.
3. The viewer's settings and other tabs: volume, mute, which other channels are open and what they play.
4. The separation of channels: a page reaches its own channel and no other.

### 12.2 Attackers

A hostile channel (its server and its program) that sends any bytes it likes as a table, as sounds and as pages; a hostile channel that has also taken over its own decoder or the sound helper through some other fault; someone on the network of an unencrypted connection, who can do what a hostile channel can.

### 12.3 Threats, what answers them, and what remains

| # | Threat | Answer | Remains |
|---|---|---|---|
| 1 | A table that is a program: loops, recursion, unbounded work | RULE-1, RULE-5, RULE-6: each handling decides its firings and then applies them, once, in a fixed order; no command makes a rule fire while it is applied; events are held to the per-tick budgets; groups nest to depth 4 with no ring and no condition inside, so a run is a constant list of at most `MAX_RUN_COMMANDS` commands (RULE-120); a sequence is a constant list of steps | The work of a tick is bounded by the table's constants, but the bound is large and there is no cap below it: section 12.4 |
| 2 | A table built to exhaust memory or to crash the decoder | RULE-56 (no allocation, panic lints denied), RULE-70 (refused whole), RULE-71, the fuzz targets of RULE-83 | A fault in the crate would be confined to that channel's decoder, which holds only that channel's pages |
| 3 | A page that takes input the viewer did not mean for it | RULE-58: only the open page of the active tab is given input, and only the classes its table asks for; RULE-51: the browser's own keys, links and the strip are never given | A page the viewer has open and is typing at can ask for every key typed at it; it cannot have them without a table saying so |
| 4 | Input leaving for somewhere else | RULE-52 items 3 and 4: the trusted core builds each report from its own copy of the event, for the page's own channel on its own connection | Nothing |
| 5 | A decoder taken over, asking the core to send what the viewer never did | RULE-52 item 3: the decoder supplies no event bytes; a sequence number it was never given, or an old one, is dropped | It can cause real input on its own page to reach its own channel, which the channel's table could have asked for |
| 6 | **A group that widens what is sent**: a `REPORT` in a sequence or a nested group reporting input no rule asked for, or reporting it later | RULE-22 and RULE-52: a report carries an input event only as the trusted core's own copy, only for an event given to that page within 4 ticks; a run not made by an input's rule has no event to name. REQ-6523 is enforced where it was, in the core | Nothing new. A table can report that a key was pressed by storing the firing's `key` in a variable and reporting the variable later: that is the page's own viewer's input on that page reaching its own channel, which a `REPORT` in the key's own group does more directly |
| 7 | A covert channel out through values: a report of a value, or the state answer, carrying data chosen by a compromised decoder | RULE-52 item 5: 20 valued or bare reports a second; item 6: one state answer a query, a query a second | A compromised decoder can already send its channel nothing it does not already hold; the budget bounds the rate |
| 8 | Learning the viewer's settings or other tabs through metered values | RULE-32: `level` is measured before the master volume and the mute, per view; RULE-33: the helper reports a view's values only to that view | Nothing in the design. See 9 |
| 9 | A sound helper taken over through an instrument (a hostile bank image or MIDI stream), reporting another view's sound as this view's levels or cues, which a colluding table then sends home | The instruments and the mixer are `no_std`, allocation-free and forbid `unsafe`, and every family's bank reader and message reader is fuzzed (RULE-83); the trusted core accepts a metering report only of the length of the list it passed, and a `CueHeard` only for a sound that view plays; the decoder handles at most `MAX_EVENTS_PER_TICK` events a tick, cues among them | A fault in the instruments that gave control of the helper would let a page learn which other tabs sound, at up to 32 bytes a tick. Recorded for the owner (DEC-6525 item 12) |
| 10 | Sound as a nuisance or a weapon: a table that plays loud notes for ever, or a sequence that never stops | The viewer's volume and mute are outside a page's reach; a local sound is silent while its page is paused and ends when it is closed or disconnected (RULE-111); a group cannot start a sound for the whole service (RULE-119); the audio profile's limiter is unchanged | A page can make sound while it is the open page, as it could with the audio profile |
| 11 | Processor exhaustion through local instruments | `MOST_LOCAL_SOUNDS` 2 a view, only for the open page; RULE-62's overrun stop; the core's `SOUND_COMMAND_BUDGET` | A page can cost up to the overrun bound of processor on the audio thread for 8 buffers before it is stopped |
| 12 | Processor exhaustion through animation commands | The animation budget (ANIM-16) and the repaint budget (REQ-6368), which hold painting however the operations arrive | The state changes themselves are not budgeted: section 12.4 |
| 13 | Timing: a table as a clock for measuring the machine | A page tick is all a table can read of time, and a report carries it; ticks slow under load (RULE-4); fault 9 says so once a second at most | A channel can learn that the machine was late: about one bit a second, of the machine's load |
| 14 | Fingerprinting the keyboard layout through `physical` and `char` keys | The KEY event already carries both, so a page that is sent keys learns the layout today | Unchanged |
| 15 | A table that survives the page: acting after the viewer has left, or after a reconnect | RULE-111: a paused page evaluates nothing, sounds nothing and reports nothing; a closed or disconnected page's state is dropped whole; sequences, running or waiting, and waiting events are dropped with it; nothing is kept by the server | Nothing |
| 16 | **Self-modification**: a table that rewrites its rules, groups, sequences or rows when triggered, so that what was checked is not what runs | RULE-119: no command defines or changes any of them; a table changes only by a new RULES record from the server, checked whole | Nothing |
| 17 | **Computed addresses**: a variable choosing which sound, object, group or variable a command acts on | RULE-106: no audio channel, handle, group, timer, sequence, variable or status takes a binding; a target's number takes only a constant of the table (a row) or the object the viewer's own pointer event named | Nothing |
| 18 | A stored `REDIRECT`, link change or stream write applied at a local time | RULE-119 forbids every record but the ten listed | Nothing |
| 19 | The server starting sequences to act when the viewer is not looking | A sequence runs only in the tick steps of the open page; a paused page runs none; a start is at most `MAX_START_TICKS` ahead, and sequences are dropped at close | Nothing |
| 20 | The default table (RULE-53) sending more than a page needs | It is the behaviour of 18 November 2026 made explicit, chosen for each channel by its operator; RULE-54 and TODO-6544 replace it | Until a channel moves, its pages ask for everything, as they did |
| 22 | Events handled at once (RULE-96, DEC-6635) used to do more work than a tick allows, to send sooner or more than the page's own channel could, or to race the tick; the small device buffer (RULE-97) or the phase message (RULE-98) used against the machine | RULE-5: an event is the viewer's own input passed by the trusted core under RULE-52, a record of the page's own channel, or a cue of the page's own sound; the events of a tick are held to `MAX_EVENTS_PER_TICK`, `MAX_EVENT_COMMANDS_PER_TICK` and `MAX_EVENT_REPORTS_PER_TICK`, and the rest wait, so a burst of input costs no more a tick than the budgets; the order is the arrival order and the tick steps fall at tick boundaries, so a recording replays exactly and wall-clock time decides nothing. A report leaves at once, but only through the trusted core's gate and budgets (RULE-52), which are unchanged: a channel can receive a viewer's input up to 16.7 milliseconds sooner than before, and no more of it. RULE-97: the buffer is small only while a local sound is open, and one underrun or overrun returns it. RULE-98: no page, record or channel can read or change the phase | Nothing |
| 21 | State left on the server about a viewer | RULE-40, RULE-111: the server keeps no table, animation state or local state for a connection beyond its end | Less than the first form kept |

### 12.4 What a hostile table can do with no work cap

The owner ruled that a group is limited by its number of commands and not by a cap on its work (DEC-6587 item 2), and the first form's limit of actions a tick is withdrawn with it. This is what that leaves, stated plainly.

**The bound that remains.** The work of one tick is still bounded by constants of the table, because nothing loops: an event fires at most `MAX_RULE_ROWS` rule-and-row pairs; each firing is one run of at most `MAX_RUN_COMMANDS` commands; at most `MAX_EVENTS_PER_TICK` events are handled a tick. The events of one tick are held to the per-tick budgets: they apply at most `MAX_EVENT_COMMANDS_PER_TICK` commands, beside the first event of the tick, which is always handled and may apply up to `MAX_RULE_ROWS × MAX_RUN_COMMANDS` (16,384 at RULE-57's figures; before DEC-6635, events could apply 262,144 a tick). The tick step, which is not budgeted, applies at most `(MAX_RULE_ROWS + MAX_SEQUENCES × MAX_SEQUENCE_STEPS) × MAX_RUN_COMMANDS` (81,920), from timers that fire every tick, sequences and `becomes` rules. A command is small (a record of at most `MAX_COMMAND_BYTES`; an `ANIMATE` of that size holds about 45 operations, each a few writes to the animation state), but 98,000 of them sixty times a second is several million small operations a tick: more than a tick's time on an ordinary machine.

**What a hostile page can therefore do**, while it is the open page of the active tab and for no longer:
1. **Keep one processor core busy in its own decoder process.** The decoder is confined and holds only that channel's pages. Its ticks then run late, page time slows (RULE-4), fault 9 is reported, and the console shows the longest tick. Other channels' decoders, the trusted core and the interface are other processes and are not slowed by it, except as any busy process slows a machine.
2. **Ask for more painting than can be done.** It cannot make it happen: the animation budget and the repaint budget hold painting to their figures however the operations arrived, and slow the animation, never the viewer's input (ANIM-16).
3. **Flood the sound path** with `LOCAL_MIDI` and `CONTROL` commands. The trusted core passes at most 512 a tick for a view (RULE-52 item 5) and the sound helper queues at most 256 a block and stops a sound that overruns (RULE-62); the rest are dropped and counted. This budget is general — it applies to the server's records too — and is the one protection the second form adds, because the sound path crosses the trusted core, which every tab shares.
4. **Flood reports.** It cannot: the trusted core's report budgets are unchanged.

**Why this is accepted.** A hostile channel could already do the first of these by sending records without pause, at the cost of its own bandwidth; a table does it at no cost to the channel, which is the difference. What is at risk is the viewer's processor for as long as they keep a hostile page in front of them, in a process that can reach nothing: not their input, their files, their network, other channels or other tabs. Closing the page, or bringing another tab forward, ends it at once (RULE-111). No general budget is needed for the variable, timer, sequence and run commands themselves, which cost a few instructions each. The per-tick budgets of DEC-6635 bound what a burst of input costs; they are not a cap on a group's work, and the tick step keeps the bound above.

**The residual risk, for the owner.** A page can make its own tab stutter and use a core's worth of power while it is open, and the only thing that stops it is the viewer leaving. If that proves to matter, the remedy that keeps the owner's ruling is not a cap on a group but a watchdog on the page: suspend a table whose ticks have run late for some seconds, and say so on the page. It is not built; DEC-6587's "when to reconsider" names the case, and RULE-72's counters and fault 9 are how it would be seen.

### 12.5 Requirements of the analysis

**RULE-80 [neoteletext-browser; engine]. The threat models are updated.**
- **Statement.** The engine's `THREAT-MODEL.md` and the browser's `docs/security-analysis.md` MUST hold the table of section 12.3 and the statement of section 12.4, and the browser's `docs/architecture.md` the processes' messages (section 6.4) and the decoder's and the sound helper's holdings (section 6.1: the decoder holds the open page's table, groups and rule state and input; the sound helper holds local instruments and cue marks and reports levels and cues).
- **Verification.** Review, recorded with its date.

**RULE-81 [neoteletext-common]. Privacy: what a channel learns, and the rule channels are bound by.**
- **Statement.** The protocol's privacy rules (viewer-state.md section 11, and the protocol document's items on input) MUST state that: a channel receives a viewer's input on a page only through that page's table; `REPORT` and the state query's answer reveal what the viewer did on that page — keys, clicks, the variables their keys changed, which objects the page showed — to that page's own channel and to no one else; a channel MUST use them only to provide what the page offers the viewer, as it is bound for the viewer's handle (viewer-state.md VS-503); a channel MUST NOT ask for input a page does not use; and neither side keeps a page's local state after the page is left or the connection ends (RULE-111). The browser's privacy page says the same in the viewer's terms.
- **Reason and source.** DEC-6522 item 12; DEC-6587 item 3.
- **Verification.** Review of the generated protocol document's items.

**RULE-82 [neoteletext-browser; engine]. The amendments to REQ-417 and REQ-661.**
- **Statement.** The engine's REQ-417 (REQ-SEC-004) and the browser's REQ-661 (requirement 1.3) MUST state the exception as the second form has it: a page's rule table — rules that bind events to groups of protocol commands, each event handled at once in arrival order within per-tick budgets, and what time drives evaluated once per tick of one sixtieth of a second — may be evaluated, provided that it is decoded and evaluated only by the engine crate `neoteletext-rules`, in the browser only in the confined decoder process and never in the trusted core; that it stays within every limit of RULE-57 (REQ-6608), which is the one place their figures are stated; that its only arithmetic beyond comparison is the saturating addition and subtraction of signed 32-bit integers in the variable commands and in a command's value held to the field's range, with no multiplication, division, loop within a tick or computed address; that no command changes a table, a group, a sequence or a row; that no command makes a rule fire while it is being applied; and that nothing reaches the network because of it but the reports the trusted core itself builds under RULE-52 and the answer to a state query, to the page's own channel on its own connection.
- **Reason and source.** DEC-6522 item 1 and DEC-6587 item 5 amend REQ-417; REQ-661 is the browser's statement of the same rule.
- **Verification.** rdm: REQ-417 and REQ-661 revised with this text.

**RULE-83 [engine; neoteletext-browser; neoteletext-app-server]. Fuzz targets.**
- **Statement.** These targets MUST exist, each replaying first every input that ever found a fault (DEVELOPMENT.md section 8):

| Target | Where | It holds that |
|---|---|---|
| `rules_decode` | engine | any bytes decode to a table within every limit or are refused whole; `encode(decode(x))` decodes to the same table; no accepted table has a ring of groups, a run over 128 commands or a command RULE-119 forbids |
| `rules_evaluate` | engine | any valid table with any script of events, cues, server commands, metered values and world answers runs any number of ticks without panic or allocation, never applies more commands in one run than the table's constant, never reports an input event it was not given, and gives the same outputs when run twice |
| `rules_arrival` | engine | Withdrawn with the arrival copy (DEC-6635 item 1): there is one path, and nothing to compare. Its corpus is replayed by `rules_evaluate` |
| `rules_budget` | engine | for any table and events, no tick handles more events, or applies more commands or `REPORT`s for its events, than RULE-5's budgets allow (the first event of a tick aside), every event is handled in arrival order or dropped at a full queue and counted, and replaying the recorded order gives the same outputs (RULE-5, RULE-7) |
| `rules_no_unasked_send` | engine | (REQ-6523's) for any table and events, every report of an input event is of an event that fired a rule whose run, in that event's handling, applied a `REPORT` of the firing |
| `rule_commands` | engine (`neoteletext-web`) | the readers and writers of record types 28 to 33 agree and refuse what is out of range |
| `rule_event`, `page_state` | engine (`neoteletext-input`) | the two messages' readers and writers agree and refuse what is out of range |
| `local_midi` | engine (`neoteletext-audio-instruments`) | for each family, any setup block, bank images, MIDI messages and blocks with cue events render without panic, and `meter` and the parameter reads stay in range |
| `rules_json` | server | any JSON line as a `rules` message or as a command message is refused or encodes to an image or record the engine accepts |
| `core_report_gate` | browser | any sequence of decoder messages and viewer events never makes the trusted core send an event it did not receive from the viewer for that page, or exceed its budgets, the sound command budget among them |
| `protocol_audio_local` | browser | the voice operations' readers, `Cue` and `Pause` among them, hold their bounds |

- **Verification.** The full gates run each for their stated time.

## 13. Verification

**RULE-84 [every repository]. Each requirement's tests name it.**
- **Statement.** Every test written for this document MUST name the `RULE-n` it verifies and the rdm requirement that carries it, and each requirement above lists the tests it needs under its Verification. A test of the first form whose requirement is withdrawn is deleted with the code it tested.
- **Verification.** Each repository's check that test names cite records that exist.

**RULE-85 [neoteletext-common; engine; neoteletext-app-server; neoteletext-browser]. Shared wire vectors.**
- **Statement.** neoteletext-common's `wire-vectors.tsv` MUST hold, as hexadecimal bytes with the JSON they stand for, at push protocol version 10: the table image of each worked example of section 7.5, of the default table with and without `wheel`, and of the music player's table (section 14), and the RULES record or records each travels in; one record of each of the types 28 to 33, and each `VARIABLE` operation with each operand kind; one RULE_EVENT of each kind; one PAGE_STATE; one RULES_FAULT; one RULES_QUERY; one local sound's OBJECT; one block with a cue. The engine produces them (`cargo xtask`), and the engine's, the server's and the browser's tests each check their own code against the same file. The first form's vectors (version 9) are replaced in the same change.
- **Reason and source.** The existing practice (DEC-6462 item 5).
- **Verification.** The three repositories' vector tests.

Numbers RULE-73 to RULE-79, RULE-86 to RULE-89, RULE-101, RULE-104 and RULE-115 are not used.

## 14. The demonstration: the music player

**RULE-90 [neoteletext-server-channel-musicplayer]. The channel.**
- **Statement.** The repository `neoteletext-server-channel-musicplayer` MUST hold a channel written in TypeScript on the TypeScript kit, served by the deployed server in the folder `musicplayer` (so at `https://app.neottx.com/musicplayer/`), with the `channels.json` entry `{"folder":"musicplayer","name":"Music player","command":["node","src/main.ts"],"directory":"current/neoteletext-server-channel-musicplayer"}` and no `default_rules`, so that every input it receives is one its own tables ask for. It keeps a `CLAUDE.md` importing DEVELOPMENT.md, a `README.md`, `BUILD.md` and `DEPLOYMENT.md`, and the shared gates.
- **Reason and source.** The owner, 18 November 2026: "A MUSIC PLAYER THAT SHOWS SYNTHESIZERS INSTANTLY PLAYING ON A KEYPRESS AND INSTANTLY DISPLAYING LEVELS VISUALLY ALSO IN RESPONSE TO THE KEYPRESS".
- **Verification.** The channel's gate; the deployment's smoke test fetches its index page.

**RULE-91 [neoteletext-server-channel-musicplayer]. Its pages.**
- **Statement.** The channel has these pages, each at sub-code `0001`:

| Page | What it is |
|---|---|
| 100 | The index: a teletext page naming the instruments, each a link to its page. It has a table with no rules, so nothing typed on it is sent |
| 101 | synth106 |
| 102 | synth7 |
| 103 | synthD |
| 104 | synth53 |
| 105 | synth8 |
| 106 | synth80 |
| 107 | synth60 (the first build added it, TODO-6565) |
| 111 | The teletext variant of page 101 (RULE-94) |

- Pages 101 to 107 are each a ReGIS picture over a teletext page whose Fastext row is drawn beneath it (the browser's REQ-6379): red the previous instrument, green the next, yellow the index, and the fourth, cyan (EN 300 706 clause 9.6.1 and the kit name it cyan; this text called it blue), page 111 with the prompt "Teletext" (DEC-6671 item 6). Every page is published at sub-code `0001` with the kit's `put`, and the whole page is sent at every selection through the kit's `request` handler, which is told of every selection, where `opened` is told only of a new page number (DEC-6671 items 4 and 5). Each has one local sound of its instrument on audio channel 0 and one bank of four patches chosen from the instrument's own bank for contrast, programs 0 to 3, on two handles of its own: page `100 + k` has the sound on handle `2k − 1` and the bank on handle `2k` (page 101: 1 and 2; page 102: 3 and 4), every one at generation 1. A receiver keeps a sound by its handle and generation, so one pair of handles for every page would make the second instrument a viewer opened play as the first (found by the first build, DEC-6573). At every selection of one of these pages (`selected`, including a viewer who returns or reconnects, RULE-111) the program sends that connection, in a frame (ANIM-2): the bank, the local sound with a setup of program change 0, the picture, and the page's table. It sends nothing more while the viewer plays: every note and every change of the picture is the receiver's.
- **Verification.** The channel's tests: the messages sent on selecting each page, the same again on a second selection; none sent for a played key.

**RULE-92 [neoteletext-server-channel-musicplayer]. The picture.**
- **Statement.** Each instrument page's ReGIS picture (800 by 480) is built of these numbered drawings (regis-v2.md):

| Drawings | What | Layer |
|---|---|---|
| 1 | The background: the instrument's name in large text at the top, the lines "PLAY: A W S E D F T G Y H U J K OR CLICK   SOUND: 1 2 3 4" and "OCTAVE: UP DOWN   ARPEGGIO: Z   SILENCE: SPACE SPACE", and the meter's frame | 0 |
| 101 to 113 | The thirteen keys for notes 60 to 72 (C4 to C5), drawing `100 + note − 59`: the eight white keys (notes 60, 62, 64, 65, 67, 69, 71, 72) 64 pixels wide and 200 tall from x = 72, 66 pixels apart, top at y = 200; the five black keys (61, 63, 66, 68, 70) 40 wide and 120 tall, centred on the gaps, at a higher order. Each is labelled with its computer key, is detectable (so that a pointer press finds it), and names its pressed look: `D(S101(A201))` and so on | 1 |
| 201 to 213 | The pressed look of each key, drawing `200 + note − 59`: the key filled in a bright colour. Hidden (`V0`), so each is drawn only as a look | 1 |
| 301 to 308 | The meter's eight segments, bottom to top, each 56 wide and 28 tall at x = 700, the lowest with its top at y = 400 and each next 36 higher; segments 1 to 5 green, 6 and 7 yellow, 8 red. Hidden (`V0`) at the start | 2 |
| 401 to 404 | The four sound names, each with a marker; hidden at the start but 401 | 2 |
| 405 | The word "ARPEGGIO" beside the sound names; hidden at the start | 2 |

- The keys' pressed looks are forced by the table's `animate` commands; nothing is redrawn by the channel.
- **Verification.** The picture passes the server's ReGIS check; a golden image of each page at rest and with keys 60, 64 and 67 down and the meter at level 100, made by `regis-render` with a rule script (ANIM-18).

**RULE-93 [neoteletext-server-channel-musicplayer]. The table.**
- **Statement.** Every instrument page carries the table below; it reads no synthesizer field, so it is the same for all seven pages but for one number, the handle of the `start` group's `play`, which is the page's own sound handle (RULE-91; 1 for page 101, as written here). It has 16 rules, 22 groups, one sequence and three row sets of 25 rows in all, each row one parameter (DEC-6635 item 8), where the first form needed 47 rules and could not afford the pointer. It uses: binding rows for the thirteen keys (each row a note, 60 to 72, its computer key given by its place in a key set of one key a row, and its drawing `41 + p`), for the four sounds (each row a program, 0 to 3, its key by place and its name drawing `401 + p`) and for the eight meter segments (each row a level threshold, its segment drawing `301 + row`); a rule fired by either of two triggers (the key, or a press on its drawing); the variables `v0` (the octave's shift in semitones, −24 to 24), `v1` (the mode: 0 playing, 1 arpeggio), `v2` (the note being worked out) and `v3` (a first press of Space is waiting for a second); the timer `t0` (the time a second press of Space may take); an amount that is a constant plus a variable (the note's key); a mode tested by conditions; a sequence that repeats until stopped (the arpeggio: the held key's note, then 4, 7 and 12 semitones above it, a note every eight ticks); a `becomes` rule with a row parameter as its threshold; and a double press written with a timer and a variable (Space twice within twenty ticks silences everything), since the `double` trigger is withdrawn (DEC-6635 item 7). No group has a `report`: the page sends its channel no input at all.

```json
{"type":"rules","connections":[7],"page":"101","sub":"0001","table":{
 "rows":{
  "keys":[60,61,62,63,64,65,66,67,68,69,70,71,72],
  "sounds":[0,1,2,3],
  "meter":[4,8,16,32,64,96,128,192]},
 "groups":[
  {"name":"start","commands":[
   {"type":"sound","kind":"play","channel":0,"handle":1,"generation":1,"gain":100,"fade_ms":5,"duck":0,"loop":false,"after":false}]},
  {"name":"note_on","commands":[
   {"type":"variable","op":"set","variable":"v2","value":{"plus":0,"fired":"p"}},
   {"type":"variable","op":"add","variable":"v2","value":{"plus":0,"variable":"v0"}},
   {"type":"local_midi","channel":0,"message":{"event":"note_on","channel":1,"key":{"plus":0,"variable":"v2"},"velocity":100}},
   {"type":"animate","ops":[{"action":"look","target":{"object":{"plus":41,"row":"p"}},"look":"pressed"}]}]},
  {"name":"note_off","commands":[
   {"type":"variable","op":"set","variable":"v2","value":{"plus":0,"fired":"p"}},
   {"type":"variable","op":"add","variable":"v2","value":{"plus":0,"variable":"v0"}},
   {"type":"local_midi","channel":0,"message":{"event":"note_off","channel":1,"key":{"plus":0,"variable":"v2"},"velocity":64}},
   {"type":"animate","ops":[{"action":"look","target":{"object":{"plus":41,"row":"p"}},"look":"normal"}]}]},
  {"name":"silence","commands":[
   {"type":"local_midi","channel":0,"message":{"event":"control_change","channel":1,"controller":123,"value":0}}]},
  {"name":"arp_start","commands":[
   {"type":"animate","ops":[{"action":"look","target":{"object":{"plus":41,"row":"p"}},"look":"pressed"}]},
   {"type":"sequence","op":"start","sequence":"arpeggio","at":null}]},
  {"name":"arp_stop","commands":[
   {"type":"sequence","op":"stop","sequence":"arpeggio"},
   {"type":"run","group":"silence"},
   {"type":"animate","ops":[{"action":"look","target":{"object":{"plus":41,"row":"p"}},"look":"normal"}]}]},
  {"name":"arp_note","commands":[
   {"type":"run","group":"silence"},
   {"type":"variable","op":"set","variable":"v2","value":{"plus":0,"fired":"p"}},
   {"type":"variable","op":"add","variable":"v2","value":{"plus":0,"variable":"v0"}}]},
  {"name":"arp_0","commands":[{"type":"run","group":"arp_note"},
   {"type":"local_midi","channel":0,"message":{"event":"note_on","channel":1,"key":{"plus":0,"variable":"v2"},"velocity":100}}]},
  {"name":"arp_1","commands":[{"type":"run","group":"arp_note"},
   {"type":"local_midi","channel":0,"message":{"event":"note_on","channel":1,"key":{"plus":4,"variable":"v2"},"velocity":90}}]},
  {"name":"arp_2","commands":[{"type":"run","group":"arp_note"},
   {"type":"local_midi","channel":0,"message":{"event":"note_on","channel":1,"key":{"plus":7,"variable":"v2"},"velocity":90}}]},
  {"name":"arp_3","commands":[{"type":"run","group":"arp_note"},
   {"type":"local_midi","channel":0,"message":{"event":"note_on","channel":1,"key":{"plus":12,"variable":"v2"},"velocity":90}}]},
  {"name":"arp_toggle","commands":[
   {"type":"sequence","op":"stop","sequence":"arpeggio"},
   {"type":"run","group":"silence"},
   {"type":"variable","op":"toggle","variable":"v1"},
   {"type":"animate","ops":[
    {"action":"look","target":{"object":101},"look":"normal"},{"action":"look","target":{"object":102},"look":"normal"},
    {"action":"look","target":{"object":103},"look":"normal"},{"action":"look","target":{"object":104},"look":"normal"},
    {"action":"look","target":{"object":105},"look":"normal"},{"action":"look","target":{"object":106},"look":"normal"},
    {"action":"look","target":{"object":107},"look":"normal"},{"action":"look","target":{"object":108},"look":"normal"},
    {"action":"look","target":{"object":109},"look":"normal"},{"action":"look","target":{"object":110},"look":"normal"},
    {"action":"look","target":{"object":111},"look":"normal"},{"action":"look","target":{"object":112},"look":"normal"},
    {"action":"look","target":{"object":113},"look":"normal"}]}]},
  {"name":"arp_shown","commands":[{"type":"animate","ops":[{"action":"show","target":{"object":405}}]}]},
  {"name":"arp_hidden","commands":[{"type":"animate","ops":[{"action":"hide","target":{"object":405}}]}]},
  {"name":"sound_pick","commands":[
   {"type":"local_midi","channel":0,"message":{"event":"program_change","channel":1,"program":{"plus":0,"row":"p"}}},
   {"type":"animate","ops":[
    {"action":"hide","target":{"object":401}},{"action":"hide","target":{"object":402}},
    {"action":"hide","target":{"object":403}},{"action":"hide","target":{"object":404}},
    {"action":"show","target":{"object":{"plus":401,"row":"p"}}}]}]},
  {"name":"meter_show","commands":[{"type":"animate","ops":[{"action":"show","target":{"object":{"plus":301,"fired":"row"}}}]}]},
  {"name":"meter_hide","commands":[{"type":"animate","ops":[{"action":"hide","target":{"object":{"plus":301,"fired":"row"}}}]}]},
  {"name":"octave_up","commands":[
   {"type":"run","group":"silence"},
   {"type":"variable","op":"add","variable":"v0","value":12},
   {"type":"variable","op":"min","variable":"v0","value":24}]},
  {"name":"octave_down","commands":[
   {"type":"run","group":"silence"},
   {"type":"variable","op":"sub","variable":"v0","value":12},
   {"type":"variable","op":"max","variable":"v0","value":-24}]},
  {"name":"panic_arm","commands":[
   {"type":"variable","op":"set","variable":"v3","value":1},
   {"type":"timer","op":"start","timer":"t0"}]},
  {"name":"panic_fire","commands":[
   {"type":"variable","op":"set","variable":"v3","value":0},
   {"type":"timer","op":"stop","timer":"t0"},
   {"type":"run","group":"silence"}]},
  {"name":"panic_reset","commands":[
   {"type":"variable","op":"set","variable":"v3","value":0}]}],
 "sequences":[
  {"name":"arpeggio","length":32,"repeat":0,"steps":[
   {"tick":0,"run":"arp_0"},{"tick":8,"run":"arp_1"},{"tick":16,"run":"arp_2"},{"tick":24,"run":"arp_3"}]}],
 "rules":[
  {"name":"start","on":{"event":"open"},"run":"start"},
  {"name":"down","rows":"keys","when":{"read":{"of":"variable","variable":"v1"},"op":"==","value":0},"run":"note_on",
   "on":[{"event":"key","by_row":true,"keys":[{"physical":"a"},{"physical":"w"},{"physical":"s"},{"physical":"e"},{"physical":"d"},{"physical":"f"},{"physical":"t"},{"physical":"g"},{"physical":"y"},{"physical":"h"},{"physical":"u"},{"physical":"j"},{"physical":"k"}]},
         {"event":"press","target":{"object":{"plus":41,"row":"p"}},"button":0}]},
  {"name":"up","rows":"keys","when":{"read":{"of":"variable","variable":"v1"},"op":"==","value":0},"run":"note_off",
   "on":[{"event":"key_up","by_row":true,"keys":[{"physical":"a"},{"physical":"w"},{"physical":"s"},{"physical":"e"},{"physical":"d"},{"physical":"f"},{"physical":"t"},{"physical":"g"},{"physical":"y"},{"physical":"h"},{"physical":"u"},{"physical":"j"},{"physical":"k"}]},
         {"event":"release","target":{"object":{"plus":41,"row":"p"}},"button":0}]},
  {"name":"arp_down","rows":"keys","when":{"read":{"of":"variable","variable":"v1"},"op":"==","value":1},"run":"arp_start",
   "on":[{"event":"key","by_row":true,"keys":[{"physical":"a"},{"physical":"w"},{"physical":"s"},{"physical":"e"},{"physical":"d"},{"physical":"f"},{"physical":"t"},{"physical":"g"},{"physical":"y"},{"physical":"h"},{"physical":"u"},{"physical":"j"},{"physical":"k"}]},
         {"event":"press","target":{"object":{"plus":41,"row":"p"}},"button":0}]},
  {"name":"arp_up","rows":"keys","when":{"read":{"of":"variable","variable":"v1"},"op":"==","value":1},"run":"arp_stop",
   "on":[{"event":"key_up","by_row":true,"keys":[{"physical":"a"},{"physical":"w"},{"physical":"s"},{"physical":"e"},{"physical":"d"},{"physical":"f"},{"physical":"t"},{"physical":"g"},{"physical":"y"},{"physical":"h"},{"physical":"u"},{"physical":"j"},{"physical":"k"}]},
         {"event":"release","target":{"object":{"plus":41,"row":"p"}},"button":0}]},
  {"name":"arp_key","on":{"event":"key","keys":[{"physical":"z"}]},"run":"arp_toggle"},
  {"name":"arp_on","on":{"event":"becomes"},"when":{"read":{"of":"variable","variable":"v1"},"op":"==","value":1},"run":"arp_shown"},
  {"name":"arp_off","on":{"event":"becomes"},"when":{"read":{"of":"variable","variable":"v1"},"op":"==","value":0},"run":"arp_hidden"},
  {"name":"sound","rows":"sounds","on":{"event":"key","by_row":true,"keys":[{"char":"1"},{"char":"2"},{"char":"3"},{"char":"4"}]},"run":"sound_pick"},
  {"name":"meter_on","rows":"meter","on":{"event":"becomes"},
   "when":{"read":{"of":"sound","channel":0,"property":"level"},"op":">=","value":{"plus":0,"row":"p"}},"run":"meter_show"},
  {"name":"meter_off","rows":"meter","on":{"event":"becomes"},
   "when":{"read":{"of":"sound","channel":0,"property":"level"},"op":"<","value":{"plus":0,"row":"p"}},"run":"meter_hide"},
  {"name":"octave_up","on":{"event":"key","keys":[{"name":"ArrowUp"}]},"run":"octave_up"},
  {"name":"octave_down","on":{"event":"key","keys":[{"name":"ArrowDown"}]},"run":"octave_down"},
  {"name":"panic_first","on":{"event":"key","keys":[{"char":" "}]},"when":{"read":{"of":"variable","variable":"v3"},"op":"==","value":0},"run":"panic_arm"},
  {"name":"panic","on":{"event":"key","keys":[{"char":" "}]},"when":{"read":{"of":"variable","variable":"v3"},"op":"==","value":1},"run":"panic_fire"},
  {"name":"panic_expire","on":{"event":"after","ticks":20,"timer":"t0"},"run":"panic_reset"}]}}
```

(`connections` names the connection that selected the page; the program sends the same table to each, at every selection.)

- How it runs. A key in mode 0 fires one row of `down`, whose `p` is the note; the event is handled at once (RULE-96): the group's two `variable` commands set `v2` to `p + v0`, the note on leaves for the sound helper at once with that key, and the pressed look of drawing `41 + p` is applied at once and drawn at the next display frame (RULE-65). In mode 1 the same key starts the sequence, which holds the row's `p`, so each step works out the note from the held `p`; the first arpeggio note sounds at the next tick step after the key (a sequence started in tick `t` begins at tick `t + 1`, RULE-103), and the key's release stops the sequence and silences the part. Changing the octave or the mode silences the part first (all notes off, controller 123), so that no note is left sounding under a key whose note has moved. The first press of Space, with `v3` at 0, fires `panic_first` alone (both Space rules are decided on `v3` before the press, RULE-6); a second press within 20 ticks fires `panic`; after 20 ticks `panic_expire` puts `v3` back. A meter row's segment is `301 + row`, the row's place, since its one parameter is its threshold. Neither cue points nor a sequence started on a beat are used here: a local sound has no cues (RULE-109), and a start held for a beat is the opposite of what this page demonstrates; both are shown by example 7 of section 7.5 and by the audio demonstration channel's page (the build plan).
- **Reason and source.** The owner's demonstration; DEC-6587 item 5's ideas 1, 2, 3, 6, 9, 10, 11 and 12 on one page; DEC-6635 items 7 and 8 (the double press as rules; one parameter a row).
- **Verification.** The server accepts the table; its image is a wire vector (RULE-85); RULE-95's test.

**RULE-94 [neoteletext-server-channel-musicplayer]. The teletext variant.**
- **Statement.** Page 111 SHOULD show the same instrument as page 101 on a plain teletext page: the thirteen keys as thirteen teletext controls on rows 12 to 17 (controls 1 to 13 in note order, each three cells wide), the meter as eight teletext sprites (ANIM-7) numbered 1 to 8, each one row of three mosaic cells, placed in a column at the right and hidden at the start. The sprites' frames are passive objects defined in page 111's own packets X/26 (ANIM-7 source 1; EN 300 706 Table 28), not an object page: the `object_page` message carries a sub-page's rows as seven-bit text and so cannot carry an object page's pointer and object packets, which are Hamming 24/18 triplets (EN 300 706 clause 10.5; DEC-6671 item 1). The keys are declared by NeoTeletext's control triplet, all starting on row 12 so that their order of declaration is note order (DEC-6671 item 2). Its table is page 101's with the keys' pointer triggers naming `{"control":{"plus":-59,"row":"p"}}` (control `p − 59`, 1 to 13, for notes 60 to 72; a trigger's constant is signed, RULE-43) and the keys' operations naming `{"control":{"plus":1,"fired":"row"}}` (the same control, from the row's place, since a command's target number is unsigned in its body), the meter's operations naming `{"object":{"plus":1,"fired":"row"}}` (sprites 1 to 8), and no `sounds` rule's name objects or arpeggio marker, which it shows as text: without the rules `arp_on` and `arp_off`, the groups `arp_shown` and `arp_hidden`, and `sound_pick`'s `animate` command, 14 rules and 20 groups; the looks `arp_toggle` puts back name controls 1 to 13 (DEC-6671 item 3).
- **Verification.** A golden image sequence made by `neottx` (ANIM-18).

**RULE-95 [neoteletext-server-channel-musicplayer; neoteletext-browser]. The end-to-end test.**
- **Statement.** A test on the private display (the browser and the server together, as the ReGIS end-to-end test runs) MUST open page 101, press and release the key A, and hold: the sound helper's test device received samples of the note within RULE-64's bound; the picture's key 101 showed its pressed look within RULE-65's bound and lost it on release; at least the lowest meter segment was shown while the note sounded and hidden within one second of its release; a press of Z and then of A gave four different notes within 40 ticks; breaking and remaking the connection left the page silent and then playable again from its opening state; and the fetcher sent the channel nothing but selections between the start and the end of the test.
- **Verification.** It is the verification of the demonstration.

## 15. What this document decided without the owner

Items 1 to 16 were the first form's and are recorded in rdm as DEC-6525 of neoteletext-common (items 17 to 27 of that decision are animation.md's). Those that the second form withdraws are marked. Items 28 to 44 are the second form's and are recorded as DEC-6610, "What specifying the second form of the page rule table decided without the owner". Items 45 to 51 are the readings the owner's decision DEC-6635 needed and are recorded as DEC-6636. All wait for the owner's confirmation. Items that DEC-6635 replaces are marked here and in DEC-6610, whose rulings are unchanged.

1. **Five more triggers** than DEC-6522 item 5 lists — `text`, `move`, `wheel`, `focus`, `blur`.
2. **Key naming** by the input protocol's three existing identities, a `repeat` flag and a modifier mask; **targets** as a kind and a number, with "any" in pointer triggers only.
3. Withdrawn: the first order's unstated steps. RULE-5 is rewritten (item 31).
4. Withdrawn in part: two writes in one tick apply in order to a working copy, which stands; "reads see the tick's start" now holds for conditions only (item 32).
5. **`becomes` fires at opening** when its condition already holds. (Its firing again on enabling is withdrawn with enabling.)
6. Withdrawn: declared variables with ranges and declared timers (DEC-6587 item 4; item 33).
7. **`level`** is linear, 0 to 255, the peak of a tick, measured before the master volume and the mute. **Envelope position** is a stage 0 to 4 and a level 0 to 255 of the part's newest voice.
8. **Tracked values are read in the decoder**, from the family's tracker; only `level`, and a local sound's envelope and voice count, are metered by the sound helper.
9. **Migration by a channel-wide default table** (`default_rules: "send_all"`), now a table of rules that run one default group of one `REPORT`.
10. **Input travels only inside RULE_EVENT**, wrapping the unchanged events.
11. **The trusted core gates without reading tables**: it builds every report from its own copy of the viewer's event.
12. **Local sounds are rendered in the sound helper**; the residual risk is threat 9 of section 12.3.
13. **The synth6581 family has no local sound**.
14. **REQ-1333 gains exceptions**: a rule's reports leave as their `REPORT` command is applied (at the tick that evaluated them, before DEC-6635), and reports with no input event are allowed within `TIMED_SEND_BUDGET`.
15. **The wheel over sub-pages** goes to the page only where a `wheel` rule's target is under the pointer.
16. Withdrawn: the music player's thirteen keys with no mouse playing. Rows and several triggers on a rule give it the pointer (RULE-93).

The amendment of 18 November 2026 for DEC-6580 (items 17 to 22; the numbers 17 to 27 of DEC-6525 itself are animation.md's):

17. Withdrawn by DEC-6635 item 1 (there is no snapshot). It read: **A tick's snapshot is taken once, at the first arrival of its interval** (RULE-7), not at the end of the tick before and not again at the tick. Every condition of a tick then reads one state however its events are timed, and the evaluator used the old way is unchanged. The cost is that a change to the world after that arrival waits one tick more.
18. Withdrawn by DEC-6635 item 1 (there is no exception for metered values). It read: **Metered values are the exception**: steps 3 to 5 read the newest report at the tick (RULE-7), so that a meter is not a tick late in exactly the intervals in which a key arrived. A level may therefore show, in a tick, the sound of a note that an event of that tick began (RULE-6).
19. **256 frames are asked for, 128 accepted** (RULE-97): DEC-6580 item 2 says "128 or 256". 256 meets the decision's 12 milliseconds and halves the audio thread's wakes against 128; a device that grants 128 is used at 128.
20. **The lock is a slew of the clock's start**, at most 100 microseconds a tick (RULE-98), so that page time follows the display's clock by up to 6 parts in a thousand; RULE-4's "never drift against real time" becomes "never skip or repeat a tick".
21. **A display that is no whole multiple of 60 is not locked to** (RULE-98): its ticks cannot all fall the same time before a frame, and RULE-65 adds one refresh period there.
22. **The fallback is reported as fault 7 with count 0** (RULE-97), the decision's "existing local-overrun fault", told from RULE-62's stop by its count; **the small buffer lingers 2 seconds** after the last local sound ends; and **the meter's bound is restated as 57 milliseconds** (RULE-65), counting the report's own interval, which the earlier 45 did not.

The second form's:

28. **The command set**: the ten record types of RULE-119, six of them new (types 28 to 33), one record a command, and one function in the server and one in the receiver for a command whether it arrives directly or in a group.
29. **Binding rows are held by the receiver** and may be shared between rules; the server expands nothing (RULE-105, with the alternative weighed there). Its "four parameters a row" is replaced by DEC-6635 item 8: one parameter, `p`.
30. **An amount is a constant plus one source**, held to its field's range; the fields that take one are RULE-106's table and no others; a target's number takes the row's `p`, the firing's target or (item 48) the firing's row, and never a variable.
31. Replaced by DEC-6635 items 1 and 2: the twelve-step tick is withdrawn. What survives is that `open` is first and alone in tick step 0, and events wait for it. It read: **The evaluation order of RULE-5**: `open` first and alone on tick 0; inputs; holds; the server's commands; armed runs; timers; sequences; cues; `becomes`; animation; apply.
32. Withdrawn by DEC-6635 item 1 (one state; no arrival copy, no working copy, no snapshot). That a command reads what an earlier command of its handling wrote survives in RULE-7. It read: **The arrival copy of the variables** (RULE-96), so that a sound command delivered at once reads the variables its own group has just changed; and commands read variables from the working state while conditions read the snapshot (RULE-7).
33. **Timers are fixed and undeclared**, `t0` to `t7`, all stopped at opening, as the variables are fixed.
34. **What is forbidden in a group**, each with its reason (RULE-119): among them every record of page content, of sound assets, of links and of navigation.
35. **`echo` is not part of a rule on the wire**: it is a `REPORT` command, and `"echo": true` remains in the program protocol as a way of writing it.
36. **The server, not each kit, turns `do` and `echo` into groups** (DEC-6462: the kits hold no logic), where DEC-6587 item 9 proposed the kits.
37. **A table is one image sent in fragments** of the RULES record, since the groups' bytes can pass one record.
38. **The wheel rectangles are those of every `wheel` rule**, whatever its condition.
39. **A sound command budget in the trusted core** (512 a tick for a view, for commands however they arrive), the one general protection the second form adds (section 12.4).
40. **A tab in the background is paused**, not closed and not disconnected: state kept, nothing evaluated, sounded or reported (RULE-111 case 4).
41. **Limits the owner's list does not name**: the triggers a rule, the rule-and-row pairs a table, the bindings a command, the cue and queue figures and the table image's size (their constants and figures are in RULE-57 and REQ-6608). The parameters a row, the hold and double-press figures, the armed runs and how far ahead one may be armed, the cues a tick and the server's commands waiting are withdrawn with their mechanisms by DEC-6635.
42. **`min` and `max` name the operation, not the bound**: `min` leaves the lesser (an upper bound), `max` the greater (a lower bound); **`wrap` goes to the other end** of its range and never divides (RULE-99).
43. **A cue is the Standard MIDI Files Cue Point meta event with one byte**, carried in a block; the mark goes to the sound helper with the stream and comes back when heard (RULE-109). midi-architecture.md MIDI-8 and MIDI-115 are amended by it.
44. **The server keeps no table and no animation state for a later viewer** (RULE-40): a page's opening state is what its program sends at each selection; and **a run armed for a tick already past runs at the next tick**, counted as late, rather than being dropped (RULE-102); since DEC-6635 item 6 this holds of a sequence started `at` a tick already past (RULE-103).

The readings DEC-6635 needed (18 November 2026; recorded as DEC-6636):

45. **The per-tick budgets' figures and how they count** (RULE-5, RULE-57). DEC-6635 item 4 names three budgets — events, commands and reports a tick — and gives no figures. `MAX_EVENTS_PER_TICK` keeps 16; `MAX_EVENT_COMMANDS_PER_TICK` is `MAX_EVENTS_PER_TICK × MAX_RUN_COMMANDS`, 2,048, so that a tick's events may each make one whole run; `MAX_EVENT_REPORTS_PER_TICK` is twice the events, 32, so that every event of a full tick may report its firing and one value. An event's commands and reports are counted from the firings its decide phase finds, each run's count being a constant of the table, so nothing is counted while it runs; an event that does not fit waits and is decided again when it is handled; the first event of a tick is always handled, so that no event waits for ever. The budgets do not apply to a tick step, whose work is bounded by the table's constants (section 12.4) and which cannot wait without moving time.
46. **One arrival order for every event, in one queue** (RULE-5). Inputs, the server's records the evaluator carries out, cues and state queries are handled in one arrival order and wait in one queue of `MAX_QUEUED_EVENTS`, and once one waits every later one waits behind it; so `MAX_CUES_PER_TICK` and `MAX_QUEUED_COMMANDS` are withdrawn, and fault 4 counts every kind of event dropped. Separate queues would let a later event overtake an earlier one and break the recorded order of DEC-6635 item 5. The records the receiver applies whether or not a page has a table (`CONTROL`, `LOCAL_MIDI`, `ANIMATE`, `SPRITES`, `NAPLPS_OBJECTS`) are not events: they are applied on arrival between handlings, as changes to the world (RULE-7).
47. **A row's key is given by its place in a key set of one key a row** (`by_row`, RULE-10, RULE-105). With one parameter a row, the music player's row cannot carry both the note and the computer key, and DEC-6635 item 8 derives only the note and the drawing from `p`; so a `key` or `key_up` trigger of a template may list exactly as many keys as the rule has rows, row `r` matching key `r`. The second form's key codes taken from a row parameter (key kinds with bit 7) are withdrawn.
48. **The firing's row as a target's source, and a trigger's target as a signed constant plus `p`** (RULE-105, RULE-106, RULE-43). The meter's rows carry a threshold, from which no segment number can be derived as a constant plus `p`, so a command's target number may also be a constant plus the row's place (`0x32`), which is a constant of the table and no computed address. A trigger's target is written as a signed 16-bit constant to which `p` is added, so that the teletext variant's controls `p − 59` can be named.
49. **Sequences start in one of three modes, and a timer has a phase** (RULE-103, RULE-25). DEC-6635 item 6 makes an armed run a one-step sequence "started at a given tick" and lets a sequence "be started to begin at a timer's next expiry", and lets a condition "test a timer's phase". The `SEQUENCE` record gains a start mode (0 next tick, 1 at a page tick, 2 at the named timer's next expiry of a period), a timer and a 32-bit `ticks`, 12 bytes in all; a sequence is stopped, waiting or running, and space 8 gains `waiting`; `MAX_START_TICKS` bounds how far ahead a start may be; a start for a tick already past begins at the next tick step and is counted late. A delay is a step's offset, so no "after" mode is needed. The phase is property 2 of a timer's value, with its period in the value's `c` and `d`, read as the elapsed ticks less the greatest multiple of the period not above them.
50. **Paint points on every display** (RULE-65). DEC-6635 item 1 draws "the picture … at the next display frame". The decoder paints at a point `TICK_LEAD_MICROSECONDS` before each of the interface's compositions, from the `FramePhase` messages, whether or not the presentation clock is locked to the display; with no `FramePhase` it paints after the handling, no more often than once a tick. The bound from a key to the picture is therefore `6 + R` milliseconds at most for a refresh period `R`, unchanged at 60 hertz and lower on faster displays.
51. **What a handling is** (RULE-5, RULE-6). Every handling — an event's, the tick step and the `close` handling — decides all its firings before it applies any command, which is how "no cascade within one handling" (DEC-6635 item 3) is kept for two rules of one event and for the tick step's timers and `becomes` rules alike; a sequence advances after the tick step's groups have run. An event belongs to the page tick of the last tick step run, so that a timer or a sequence started by an event of tick `t` runs from tick `t + 1`, as one started by tick step `t` does; an event that arrives before tick step 0 waits for it. At a `close`, events still waiting are dropped and counted, since none of their effects has happened.

## 16. The rdm records

| Record | Repository | Carries |
|---|---|---|
| DEC-6522 | neoteletext-common | The owner's decision: the page rule table (items 5, 7 and 8 replaced by DEC-6587) |
| DEC-6580 | neoteletext-common | The owner's decision: a key's sound commands run at once; the device buffer; the tick locked to the refresh |
| DEC-6587 | neoteletext-common | The owner's decision: the second form |
| DEC-6599 | neoteletext-common | The owner's decision: a sub-page is exactly a page |
| REQ-6523 | neoteletext-common | No input is sent for a page unless its rule table asks |
| REQ-6608 | neoteletext-common | The limits of a page's rule table, in one requirement: RULE-57 |
| DEC-6525 | neoteletext-common | What the first form and animation.md decided without the owner (awaiting confirmation) |
| DEC-6610 | neoteletext-common | What the second form decided without the owner, items 28 to 44 (awaiting confirmation; items 17, 18, 31 and 32 and parts of 29, 41 and 44 replaced by DEC-6635) |
| DEC-6635 | neoteletext-common | The owner's decision: events act at once in arrival order; only time-driven triggers run on the tick; no cascade within a handling; per-tick budgets; armed runs, quantised start, held and double triggers withdrawn; one parameter a row |
| DEC-6636 | neoteletext-common | The readings DEC-6635 needed, items 45 to 51 (awaiting confirmation) |
| REQ-6526 | neoteletext-renderer-teletext | The crate `neoteletext-rules`: RULE-1 to RULE-19, RULE-41 to RULE-45, RULE-56, RULE-70, and the engine's part of RULE-96 |
| REQ-6612 | neoteletext-renderer-teletext | Groups and commands: RULE-118 to RULE-120, RULE-21, RULE-22, RULE-99, RULE-100, RULE-102, RULE-106 |
| REQ-6613 | neoteletext-renderer-teletext | Rows, several triggers, sequences, the values of the firing and of sequences: RULE-103, RULE-105, RULE-107, RULE-116, RULE-117 (RULE-108 withdrawn) |
| REQ-6614 | neoteletext-renderer-teletext | Cue points in the engine's audio crates: RULE-109 |
| REQ-6527 | neoteletext-renderer-teletext | Readable synthesizer state and the local sound in the audio crates: RULE-28, RULE-29, RULE-31, RULE-32, RULE-60, RULE-62 |
| REQ-6528 | neoteletext-renderer-teletext | Push protocol version 10: RULE-41, RULE-46 to RULE-49, RULE-85 |
| REQ-6532 | neoteletext-app-server | Program protocol 15: RULE-34 to RULE-40, RULE-53, RULE-59, RULE-61, RULE-114 |
| REQ-6534 | neoteletext-browser | The decoder evaluates, the trusted core gates: RULE-30, RULE-33, RULE-47, RULE-48, RULE-50 to RULE-52, RULE-58, RULE-63, RULE-70 to RULE-72, RULE-80 |
| REQ-6535 | neoteletext-browser | Local sounds, cues and the latency bounds: RULE-32, RULE-60, RULE-62 to RULE-66, the browser's part of RULE-96, RULE-97, RULE-98, RULE-109 |
| REQ-6615 | neoteletext-common | The disconnect rule and the page identity, for every repository: RULE-111, RULE-112 |
| REQ-6537 | neoteletext-server-ts-protocol | The TypeScript kit: RULE-55, RULE-110 (and ANIM-19) |
| REQ-6538 | neoteletext-server-channels | The Python kit: RULE-55, RULE-110 (and ANIM-19) |
| REQ-6539 | neoteletext-server-ts-ui-components | The component library's tables: RULE-54 |
| REQ-6540 | neoteletext-common | Security analysis applied, privacy, fuzz targets, wire vectors: RULE-80, RULE-81, RULE-83 to RULE-85 (and ANIM-23) |
| REQ-6541 | neoteletext-common, until the channel's repository is in rdm (TODO-6545) | The music player: RULE-90 to RULE-95 |
| REQ-417, REQ-661 | engine, browser | "No executable content", each amended for the second form (RULE-82) |
| DEC-649, REQ-1384, REQ-4112, REQ-1333 | engine, browser, common | Amended on 18 November 2026 by DEC-6522 and REQ-6523 |
| TODO-6542 | neoteletext-common | Restate the remaining input requirements and write the protocol's documentation items |
| TODO-6544 | neoteletext-common | Move each deployed channel to tables of its own, then delete the default table |

## 17. What building changed

The table, its carriage and the music player were built on 18 November 2026 in each repository at once, from this document at commit 85904b0. This section lists every place where what was built departs from that text or settles what it left open (DEVELOPMENT.md section 2.3, step 4). Each reading was taken without the owner and is recorded in rdm, in the record named, for the owner to confirm; where a reading is stated here as built, the requirement it concerns was corrected in place in the same change. Section 17.2 lists the places where the text was left as it is because what was built falls short of it or goes against it: those are faults to correct in code. RULE-5, RULE-7 and RULE-64 to RULE-66 are being revised separately for the owner's decision DEC-6580 (a key's sound actions run at once, a smaller device buffer, the tick locked to the display's refresh) and are not touched here.

**Since written into this text.** This section is the record of the first build, kept as it was written on 18 November 2026. The three decisions of the owner's that followed the build — DEC-6580, DEC-6587 and DEC-6599 — are now what sections 1 to 16 say (the second form), so where this section cites a requirement that the second form rewrote or withdrew (RULE-3, RULE-14, RULE-16, RULE-17, RULE-20, RULE-40 to RULE-45), the citation is to the first form's text at commit 85904b0 as corrected at 595f58c. Section 18 lists every change of the second form; rows 13 and 14 of section 17.2 are answered by it.

### 17.1 Departures and readings, now stated in the requirements

**The engine's crates (TODO-6558, part A).**

1. **RULE-15.** The statement's formula was followed where its verification line disagreed: a timer started in tick `t` runs since tick `t + 1`, so `after 1` fires at tick `t + 2`. The verification line and the prose of example 3 of section 7.5 now say so.
2. **RULE-6, stated in RULE-57.** A rule firing whose actions would take the tick past 256 is dropped whole, so that no more than 256 actions ever run; a rule's `echo` counts as one action. It is written among RULE-57's limits, and RULE-6's own statement is left as it was, because that statement is being revised for DEC-6580 on another branch.
3. **RULE-9, RULE-57.** One limit was added: `MAX_POINTER_OBJECTS` (16), the objects the pointer is followed inside at once.
4. **RULE-9.** `enter` and `leave` fire on any pointer event that carries a position; `move` fires only on a move to another pixel; `held` reads the move's own button mask or a tracked button.
5. **RULE-20.** The actions that do nothing and are counted are listed case by case.
6. **RULE-47.** "First named" and "first read" are defined: rule order, then trigger, condition, actions.
7. **RULE-46.** A report of a value, and a bare firing, name no target, and a reader refuses one that does.
8. **RULE-46 to RULE-48.** After the stamp's two varints every field is big-endian and of fixed width.
9. **RULE-46.** A RULE_EVENT counts one for acknowledgement whatever it carries, so moves and compositions are now acknowledged and resent; the session's limit of 120 messages a second reads what a RULE_EVENT carries; PAGE_STATE and RULES_FAULT count nothing. The session no longer drops a move to the same dot, since the evaluator fires `move` only for another pixel.
10. **RULE-46.** The readers a server uses (`neoteletext_input::event::read_message`, `StreamDecoder::push`) refuse a viewer's input at the top level with `InputError::Bare`; `read_items` and `StreamDecoder::push_items` read what a RULE_EVENT carried; a session refuses to write a viewer's input at the top level.
11. **RULE-41.** The RULES record's reader checks the page and the generation alone; the receiver decodes the body, so that a refused table is reported with its generation.
12. **RULE-49.** `push.input` and `push.wheel` are read past whatever value they hold; the rule that the input session's messages go only to a push connection on the descriptor's own origin is kept as `Descriptor::push_takes_messages`.
13. **RULE-71.** The fuzz target `rules_evaluate` has no counting allocator; that the crate cannot allocate holds by construction.
14. **RULE-57.** A decoded table is about 76 kilobytes and an evaluator about 91.

**The server (DEC-6568).**

15. **RULE-40.** An audience is the connections open when the message arrives; a connection that opens later was in no earlier audience.
16. **RULE-40.** A RULES record is sent at every selection of a page, one generation above the last; a table given again byte for byte is not sent again.
17. **RULE-37.** A report is named by the table of the generation it carries, of which the server keeps the last four sent to a connection; a report with no input event is given to the program whatever is selected since.
18. **RULE-37.** A release the server itself gives names the rule and the tick of the press that some rule sent, and is given for no other press.
19. **RULE-39.** The faults of a table that the table of refusals does not name are answered by the existing rules `reserved`, `not_listed`, `missing_field`, `invalid_rules`, `too_long` and `wrong_type`.
20. **RULE-61.** The server's OBJECT of a local sound names its variant (tag 5), three bytes more than the engine's; both are wire vectors.
21. **RULE-85.** The worked examples' and the music player's RULES bodies are written by the server, not by the engine's `cargo xtask`, because turning a `rules` message's names into numbers is the server's work (RULE-36).

**The browser (DEC-6573).**

22. **RULE-63.** Four messages more than the requirement listed, and the kind numbers 178 to 187 as built: `RulesPage`, the two `RulesQuery` messages and `RuleCounters`. The sound helper gained kind 6, `LocalOverrun`, for fault 7. The `Local` operation also carries synth8's split key and the duck percentage.
23. **RULE-52 item 4.** A page's reports still pass for `SEND_WINDOW_TICKS` (4) ticks after it stops being the open page, so that a `close` rule's `send` leaves; nothing is given to its decoder in that time.
24. **RULE-52 item 3.** A request refused for naming an event that cannot be reported is counted apart from fault 3.
25. **RULE-52 item 1.** The focus is given when a page's table is taken, since nothing may be given before.
26. **RULE-46.** So that a rule's `send` reports the HOVER or the DRAWING_HOVER itself, the trusted core gives a HOVER to the decoder as a pointer move naming the control entered, and a DRAWING_HOVER as an input of its own. A consequence that is not what RULE-12 intends, and is owed in code (the browser's TODO-6576): when the pointer enters and leaves a drawing within one tick, neither rule fires.
27. **RULE-51 item 4.** The interface's existing `wheel` flag now says whether the pointer is inside a wheel rule's rectangle; the trusted core drops a wheel event outside every rectangle.

**The component library (DEC-6566).**

28. **RULE-54.** Rewritten to what release 24.0.0 does: tables read from components' handlers; pointer rules on rectangles of cells and not on control numbers; a drag's moves asked of the whole page; every rule only sends, with no local `look`; a page of text asks for the page-selection keys and is not sent an empty table; input routed by where it landed and not by `rule`; and the channel option `ruleTables`, `"components"` or `"none"`. Three things the protocol kit consumes are not asked for on a page whose components do not take them, and so stop there: text that is digits alone, a click on a page number or a Fastext prompt (which the browser follows itself where it is a link, RULE-51 item 3), and a digit typed by a key that is neither on the digit row nor the keypad.

**The kits (TODO-6559, TODO-6561).**

29. **RULE-55.** The harness calls' arguments, the rule names a harness gives its inputs, what the two new handlers are given, the error a refused query rejects with, the optional `rule`, `tick` and `target` of the TypeScript type, and the TypeScript kit's four builders are stated.
30. **RULE-61.** Each kit writes a local sound's message with `connections` second, where the example writes `kind` second; the two are the same JSON value.

**The music player (TODO-6565).**

31. **RULE-91.** A seventh instrument page, 107, for synth60. The kinds `synth52_local` and `synth51_local` have no page.
32. **RULE-91.** No blue link is declared until page 111 exists.
33. **RULE-91, RULE-92.** The index's links are its page numbers; the synth8's key mode; the patches' source; the background's other contents; the sound names' places and marker; the key labels.

### 17.2 Where the text stands and the code is to change

Each is recorded in the rdm record named, and none is a reading to confirm: the requirement is right and what was built does not meet it. The state given is that of the audit of 18 November 2026, when the browser's two branches were still being merged.

| # | Requirement | What was built | Record |
|---|---|---|---|
| 1 | RULE-58, RULE-82 (REQ-661): `neoteletext-rules` nowhere in the trusted core | The trusted core's dependency tree holds `neoteletext-rules`, because `neoteletext-input` takes a target's and a value's names from it; the core calls neither its decoder nor its evaluator. The names belong in a crate apart from the evaluator's | DEC-6573 item 11 |
| 2 | RULE-65: a meter segment at most 45 milliseconds after the key | The level is reported every second device buffer (RULE-33 item 3); the greatest measured was 49 to 50 milliseconds | DEC-6573 item 9, TODO-6575 |
| 3 | RULE-64, RULE-66: the greatest figure, timed at the interface's input between the real processes, with the picture | The timed test runs each process's code in a thread of one process, holds the bound for nineteen keys in twenty, and does not time the picture | DEC-6573 item 10, TODO-6574 |
| 4 | RULE-20, RULE-26: a rule's `show`, `hide`, `look` and animation actions act on the picture, and target state is read | On the browser's branch `rules` they are counted no-ops and read 0, until the animation picture is given to the evaluator | REQ-6534, REQ-6536 |
| 5 | RULE-27: `playing` is 0 when no sound plays | It stays 1 after a stored sound ends by itself | TODO-6576 |
| 6 | RULE-28, RULE-30: tracked values of a sound played from the server's blocks | They read 0 in the browser until it pins the engine revision that tracks them | REQ-6534 |
| 7 | RULE-48: fault 8 is reported | It is never sent | REQ-6536 |
| 8 | RULE-53: `default_rules` for every host | The Cloudflare host is fixed at `none` | TODO-6571 step 5 |
| 9 | RULE-62: a note on queued before a buffer sounds within its first 128 samples | synth106's first sample is one block late | TODO-6577 |
| 10 | RULE-72: the console shows the counts | One log line is written | REQ-6534 |
| 11 | RULE-85: the browser's vector test | The browser has none | REQ-6540 |
| 12 | RULE-94, RULE-95: page 111 and the end-to-end test | Neither exists | TODO-6564 |
| 13 | The owner's decision DEC-6599: a sub-page's rule table is its own | RULE-2, RULE-17 and RULE-40 as written and built give a page one table for all its sub-pages, a list of rules switched off for a sub-page (RULE-42's sub-page masks), and no RULES record when only the sub-page changes; the server keeps tables by connection and page, the browser's decoder by page, and the component library takes its rectangles from the first sub-page | DEC-6599 |
| 14 | The owner's decision DEC-6587: a rule runs only a group of protocol commands, with sixteen fixed variables | RULE-3, RULE-14, RULE-16, RULE-20 and RULE-41 to RULE-45 as written and built give a rule its own list of actions, declared variables with ranges, and the enabling and disabling of rules | DEC-6587 |

### 17.3 The second build: readings now stated in the requirements

The second form, as DEC-6635 revised it (this document at commit `36ad145`), was built on 18 and 19 November 2026 in each repository on its branch `rules-2` or `protocol-15`. Each building session recorded the readings it took where this text was silent, for the owner's confirmation: the engine's DEC-6647 and DEC-6648, the server's DEC-6654, the browser's DEC-6659 and DEC-6664, the TypeScript kit's DEC-6662, the Python kit's DEC-6650, the component library's DEC-6670, the music player's DEC-6671 and the ReGIS test channel's DEC-6678 (with the specification's own DEC-6636, items 45 to 51 of section 15, already in the text). Each reading below that changes what this document says is now stated in the requirement named, corrected in place on 19 November 2026; the readings these records list and this one does not (the order of a module's fields, a test's helper, the look of the browser's filmstrip) change nothing here. DEC-6656, of the same night, concerns the ReGIS and NAPLPS renderers' labels and titles and changes nothing in this document.

**The engine (DEC-6647, DEC-6648).**

1. **RULE-8.** A lost release is an event of its own kind, handled at once whatever the budgets, after the events already waiting.
2. **RULE-5.** An event that waits leaves no trace: the change it made to the input state is put back, and it is decided again when handled.
3. **RULE-7.** A recording is keyed by the count of tick steps run when each input was given, which places an input given before tick step 0 apart from one given after it.
4. **RULE-5, RULE-72.** A handling keeps at most `MAX_RULE_ROWS` firings (a tick step, `MAX_RULE_ROWS` plus `MAX_SEQUENCES × MAX_SEQUENCE_STEPS`); only "any" can pass it, and the firings beyond are dropped and counted (`firings_dropped`).
5. **RULE-103.** A `SEQUENCE` stop with a nonzero start mode, timer or `ticks` is refused by the record's reader; a beat start counts from the timer's start tick, as `every` does. Both were already this text's.
6. **RULE-1.** The receiver's timekeeping takes a remainder of its own elapsed ticks by a period of the table; the table still asks for no division (REQ-417 version 6).
7. **RULE-48.** A sequence start beyond `MAX_START_TICKS` is reported as fault 10, as this text already said.
8. **RULE-56.** The program protocol's words for every code are one table, `neoteletext_rules::names`.
9. **RULE-96.** `neottx rules-run` reads the `rules` message as JSON, with `serde_json` 1.0.154 (DEC-6647, under the owner's advance approval DEC-6579), and refuses a group holding `sprites` or `naplps_objects`.
10. **RULE-109.** `MAX_CUE` is asserted equal to the highest data byte of a block in `neoteletext-web`, so the rule crate keeps no dependency.
11. **Section 8.** Record types 21 to 33 are channel records the audio receiver leaves alone (`is_channel_type`).

**The server (DEC-6654).**

12. **Animation.md ANIM-17, ANIM-21.** A program sends a page's teletext object pages with the new message `object_page` at each selection, before the page, since the server keeps no page content (REQ-1474, RULE-40).
13. **RULE-119.** The server first refused `sprites` and `naplps_objects` in a group (item 2), the engine writing those bodies only inside its packet encoder; the engine's commit `33d90896` writes them alone, and the server's `8bc159c` holds them in a group as this text says. Nothing of item 2 remains.
14. **RULE-39.** A `variable` command's operation paired with an operand it does not take, `"all"` with an operation other than `clear`, a `sequence` start without a sequence, a `period` without `phase` and a negative `plus` on an operation's target are refused, each by the rule named there.
15. **RULE-35.** `{"fired":"p"}` is the row's `p`; `{"plus":k,"row":"p"}` as a `variable` value is operand kind 3; an operation's target `plus` is 0 to 65,535.
16. **RULE-114.** A `run` or `sequence` sent directly reaches each connection whose table has the name, and one `refused` names the others.
17. **RULE-109.** A file's `cues` list holds at most `MAX_CUE + 1` entries, each text 1 to 64 bytes, compared byte for byte; a cue in a local sound's setup is refused.
18. **RULE-40.** A selection of `3F7F` gets its default or empty table when the program's answer makes the sub-code known; the server holds, for each connection, only the sheet stream it is sending for the page selected.
19. **Animation.md ANIM-21.** Every animation message for the sub-code `3F7F` is refused `out_of_range`, not only `animate`.

**The browser (DEC-6659, DEC-6664).**

20. **RULE-58.** The open page's sub-code comes from the stamp of the frame drawn; a RULES record for another page while one is open is dropped and counted.
21. **RULE-111 case 2.** The browser drops unacknowledged reports by not resuming a session whose pages took input, until the engine offers a call that drops them and keeps the session; a disconnected page's sprites, objects, sheet and animation state are kept only as its frozen picture.
22. **RULE-52 item 5.** The sound command budget is counted for each tick of the trusted core's clock over `Start`, `Stop`, `Gain`, `Local` and `LocalMidi`.
23. **RULE-97.** A local sound ends, for the device buffer, when it is stopped or replaced; a paused one still counts.
24. **RULE-51.** The tab filmstrip, while open, has the wheel and the keys before any rule's claim.

**The kits (DEC-6650, DEC-6662).**

25. **RULE-55.** An input's row place is `ruleRow` (`rule_row`); the builders and the mode set's two methods are rows of `kit-calls.tsv` with the JSON each answers; `in(mode, condition?)` joins a condition with `and`; `fire` takes the row last and a null rule; `answerState` answers sixteen zero variables for the query's own page and sub-code. The kits' own documents are `typescript.md` TS-44 to TS-53 and `python.md` PY-74 to PY-82.
26. **Animation.md ANIM-19.** Text above code point 255 is refused by both kits (DEC-6650 item 1, which the TypeScript kit's release 17.0.0 also follows).

**The component library (DEC-6670).**

27. **RULE-54.** Every rule is written with a `do` list of one `report`, which the server makes one shared group; each sub-page's table comes from its own cells, and every sub-page declares its own controls; `MAX_RECTS` and `MAX_RULES` are found from the kit's own check, since the kit exports neither.

**The music player (DEC-6671).**

28. **RULE-91.** The fourth coloured key is cyan, leading to page 111; every page is at sub-code `0001` and sent at every selection through the kit's `request`.
29. **RULE-94.** Page 111's sprites take their frames from its own local objects in X/26, since `object_page` carries text rows and no object page's triplets; its keys' layout; its table of 14 rules and 20 groups.

**The ReGIS test channel (DEC-6678).** Its pages 130 to 141 were rewritten in the second form (one `animate` command for a first-form rule's actions, `becomes` with its `when`, declared variables and timers as `v0` and `t0` to `t2`, a disabled rule as a mode); no requirement of this document changes.

### 17.4 The second build: where what was built goes against the text or an owner's decision

Each is a defect to correct in code, recorded here and in the rdm to-do named. None is a reading to confirm.

| # | Requirement and decision | What was built | Record |
|---|---|---|---|
| 1 | RULE-112, the owner's decision DEC-6599: nothing is addressed by a page number alone | The browser keys an open atomic frame (ANIM-2) on the page number alone, following the engine's `OpenFrames`, and reads a FRAME record's sub-code without using it (DEC-6659 item 8) | TODO-6681 |
| 2 | RULE-54 item 5 and RULE-112, the owner's decision DEC-6599: a sub-page has no relationship to its parent page | The component library leaves the page-selection rules (`select_digits`, `select_keypad`, `fastext_keys`) out of every sub-page's table of a page number whose kit entry owns those keys, because the protocol kit's page entry belongs to a page number (DEC-6670 item 7) | TODO-6681 |
| 3 | RULE-57 and REQ-6608, the owner's "ensure that set of limits is put into a single requirement": no file but `neoteletext_rules::limits` states a limit's figure | The ReGIS test channel's tests write 64 rules, 32 commands a group, 64 groups and 16 rectangles as literals (DEC-6678 item 9), because the TypeScript kit exports no constant of the rule table's limits; the component library finds them by probing the kit's check instead (DEC-6670 item 8) | TODO-6681 |
| 4 | RULE-55 and DEC-6462: the kits are thin and equal, and send the same lines | For a `sequence` start with no `at` given, the Python kit writes `"at":null` (DEC-6650 item 4) and the TypeScript kit leaves `at` out (DEC-6662 item 7): the server reads both alike, but the two kits write different lines for the same call | TODO-6681 |
| 5 | RULE-111 case 2: a reconnection selects the page afresh, "whether or not the session is resumed" | The browser does not resume the input session of a connection whose pages took input, which RULE-111 allows but which costs RESUME's identity for those channels, until the engine offers a call that drops unacknowledged RULE_EVENTs from a kept session (DEC-6659 item 3) | TODO-6681 |

## 18. What changed in the second form

Every change against the first form (this document at commit `85904b0`), which was built on the branches the audit of 18 November 2026 names and never deployed. The rows describe the second form as DEC-6635 left it; section 18.1 lists what DEC-6635 changed in the second form as first specified (commits `3ae1a21` and `4fc26ed`).

| # | First form | Second form | By |
|---|---|---|---|
| 1 | A rule holds up to 16 actions of 19 kinds (RULE-20, RULE-45) | A rule names one group; a group is a list of protocol commands, the same records the server sends (RULE-118, RULE-119). RULE-20 withdrawn; RULE-45 rewritten | DEC-6587 item 1 |
| 2 | `midi`, `set`, `add`, `start_timer`, `stop_timer`, `send` exist only as actions | Each is a record the server may also send: `LOCAL_MIDI` 28, `VARIABLE` 29, `TIMER` 30, `REPORT` 31; and `RUN` 32 and `SEQUENCE` 33 are new (RULE-21, RULE-22, RULE-99, RULE-100, RULE-102, RULE-103, RULE-114) | DEC-6587 item 1 |
| 3 | 256 actions a tick, then firings dropped (RULE-6, fault 2) | No cap on a group's work; a group is capped by its commands (RULE-120); events are held to per-tick budgets and wait, never dropped below the queue's limit (RULE-5); fault 2 withdrawn, fault 9 reports late evaluation | DEC-6587 item 2; DEC-6635 item 4 |
| 4 | A page closed is reopened from a table the receiver and the server keep; the server keeps tables for 64 pages a connection and replays animation state to a late viewer; the state query is for resynchronising | Everything local is dropped at a close and at a disconnect; the page is sent afresh and `open` fires again; the server keeps nothing; a background tab is paused (RULE-40, RULE-111) | DEC-6587 items 3 and 9 |
| 5 | Up to 32 declared, named variables with ranges; `set` and `add` of constants | Exactly sixteen, `v0` to `v15`, undeclared, zero at opening; ten operations with constant, variable, firing and value operands (RULE-14, RULE-99) | DEC-6587 items 4 and 7 |
| 6 | Up to 8 declared, named timers, optionally running from opening | Exactly eight, `t0` to `t7`, undeclared, stopped at opening (RULE-15) | DEC-6587 item 6; item 33 of section 15 |
| 7 | `enable`, `disable`, the enabled flag, sub-page off-lists (RULE-16, RULE-17) | Withdrawn; a mode is a variable (RULE-110) | DEC-6587 item 8; DEC-6599 |
| 8 | One table for a page and all its sub-pages; sheets, records and messages keyed on a page, some with "whichever sub-page is shown" | A sub-page is a page: everything keyed on page number and sub-code; `rules`, `query_state`, `sprite_sheet`, `timeline_stop`, RULES, RULES_QUERY and SHEET gain the sub-code (RULE-2, RULE-112) | DEC-6599 |
| 9 | One trigger a rule | One to four, any of which fires it (RULE-107) | DEC-6587 idea 9 |
| 10 | — | Binding rows of one parameter `p` (RULE-105) | idea 2; DEC-6635 item 8 |
| 11 | — | Sequences with repeat counts, started at the next tick, at a page tick or at a timer's next expiry (RULE-103) | ideas 3 and 11; DEC-6635 item 6 |
| 12 | — | Cue points (RULE-109); the `cue` trigger; the `Cue` and `CueHeard` messages | idea 4 |
| 13 | — | Groups running groups (RULE-102); a run at a tick is a one-step sequence, and a start on a beat is a sequence's `beat` start or a condition on a timer's phase (RULE-103, RULE-25) | ideas 5, 8 and 10, as DEC-6635 item 6 folds them |
| 14 | — | Nothing: long and double presses are rules with a timer and a variable (section 7.5, example 8) | idea 7, withdrawn by DEC-6635 item 7 |
| 15 | — | Amounts: a constant plus a variable, a row parameter or a value of the firing (RULE-106) | idea 12 |
| 16 | Values in six spaces | Eight: the firing (RULE-116) and sequences (RULE-117) added; a timer's phase; a compare's constant may add the row's `p` | DEC-6587 item 7; DEC-6635 item 6 |
| 17 | A key waits for the tick; every action runs at the tick | Every event is handled at once in arrival order, and every command of its groups takes effect at once; only what time drives runs in the tick step, with `open` first (RULE-5, RULE-96) | DEC-6580; DEC-6635 items 1 and 2 |
| 18 | A `send` of a value reads the snapshot | There is one state: a `REPORT` reads a value as it stands, after the commands before it (RULE-7, RULE-22) | DEC-6635 item 1 |
| 19 | `echo` is a flag of a rule in the record | A `REPORT` command; `"echo": true` only in the program protocol (RULE-22, RULE-35) | item 35 |
| 20 | The RULES record is one body of at most 8,184 bytes, format 1 | A table image of format 2, at most `MAX_TABLE_BYTES`, in fragments (RULE-41 to RULE-45) | item 37 |
| 21 | RULE_EVENT names a rule; PAGE_STATE has an enabled mask and declared variables and timers | RULE_EVENT adds the row and allows "no rule"; PAGE_STATE has the sixteen variables, eight timers and the sequences, each running or waiting (RULE-46, RULE-47) | — |
| 22 | Program protocol 14, push protocol 9 (`neottx.9`) | 15 and 10 (`neottx.10`); 14 and 9 are not kept (RULE-34, RULE-49) | DEC-6587 |
| 23 | `rules` has `variables`, `timers`, `subpages`, and rules with `do` actions tagged by `action` | `rules` has `rows`, `groups`, `sequences`, and rules with `run` or a `do` list of commands tagged by `type`; the server makes `do` and `echo` into groups (RULE-35) | DEC-6587 item 9; item 36 |
| 24 | The kits' `rules(to, page, table)`, `queryState(connection, page)` | Both take the sub-code; six command calls and the mode helper added (RULE-55, RULE-110) | DEC-6599 |
| 25 | Key to sound at most 34 ms, 20 in the median; device buffer 480 frames; meter at most 45 ms | Key to sound 12 ms at most and 6 in the median on a device buffer of `LOCAL_DEVICE_FRAMES` (RULE-64); key to picture `6 + R` at most for a refresh period `R`, 23 at 60 hertz (RULE-65); meter 57 at most | DEC-6580; DEC-6635 item 1 |
| 26 | REQ-417 and REQ-661 allow comparison only | They allow bounded saturating addition and subtraction; no multiplication, division, loop within a tick or computed address (RULE-1, RULE-82) | DEC-6587 item 5 |
| 27 | Security analysis of fifteen threats | Twenty-one, and section 12.4 on the absence of a work cap; a sound command budget in the trusted core | DEC-6587 item 2 |
| 28 | The music player: 47 rules, keys only | 16 rules, 22 groups, 25 rows of one parameter, one sequence; pointer playing, octaves, an arpeggio mode, a double-press silence written with a timer and a variable (RULE-93) | DEC-6587; DEC-6635 items 7 and 8 |
| 29 | RULE-96 to RULE-98 (DEC-6580) written for actions and a cap of 256 a tick | RULE-96 rewritten as the one path for every event and command; RULE-97 unchanged; RULE-98 also places the paint points | DEC-6587 item 9; DEC-6635 item 1 |
| 30 | Limits stated in several requirements | Every limit in RULE-57 alone, named, and every other requirement refers to it by the constant's name | REQ-6608 |

### 18.1 What DEC-6635 changed

The owner's decision DEC-6635 of 18 November 2026 changed the second form as first specified (commits `3ae1a21` and `4fc26ed`), before any of it was deployed, so nothing is kept for compatibility. Requirement numbers withdrawn stay withdrawn; codes and record numbers withdrawn are refused and never reused.

| # | The second form as first specified | Now | DEC-6635 item |
|---|---|---|---|
| 1 | Input events decided on arrival against a snapshot, their sound commands sent at once and every other command applied at the next tick; an arrival copy of the variables; one snapshot a tick taken at the first arrival, with an exception for metered values (RULE-5, RULE-7, RULE-96) | Every event — an input, a record of the server's that the evaluator carries out, a cue, a state query — is handled at once in arrival order, and every command of its groups takes effect at once; one state, read as it stands; the picture is drawn at the next paint point (RULE-5, RULE-7, RULE-96, RULE-65) | 1 |
| 2 | A twelve-step tick: snapshot, `open`, inputs, holds, the server's commands, armed runs, timers, sequences, cues, `becomes`, animation, apply (RULE-5) | A tick step of `open` (tick 0), timers, sequences, `becomes` and frame cycling only (RULE-5) | 2 |
| 3 | No cascade within a tick (RULE-6) | No cascade within one handling: every handling decides its firings before applying any command (RULE-6) | 3 |
| 4 | `MAX_EVENTS_PER_TICK` inputs a tick; `MAX_QUEUED_COMMANDS` and `MAX_CUES_PER_TICK` | Per-tick budgets of events, commands and reports for the events of a tick, counted from their firings; events over them wait in one queue (RULE-5, RULE-57) | 4 |
| 5 | Determinism by page tick, with decisions on arrival or at the tick giving the same result | Determinism by the recorded order of handlings within each tick, with the tick steps at the boundaries (RULE-7) | 5 |
| 6 | `RUN` modes `at`, `after` and `beat`; armed runs (`MAX_ARMED_RUNS`, `MAX_ARM_TICKS`); PAGE_STATE's armed count; `armed` in `page_state` | `RUN` runs a group now (5 bytes); a `SEQUENCE` start has the modes next, `at` a tick and `beat` (12 bytes; `MAX_START_TICKS`); a timer's `phase` value; sequences may be waiting (RULE-102, RULE-103, RULE-25, RULE-117, RULE-47) | 6 |
| 7 | Triggers 17 `held`, 18 `double`, 19 `press_held`, 20 `double_press`; the holds step; the memory of recent presses (`MAX_HOLD_TICKS`, `MAX_DOUBLE_TICKS`, `MAX_RECENT_PRESSES`) (RULE-108) | Withdrawn, codes not reused; a long or double press is two or three rules with a timer and a variable (section 7.5, example 8; RULE-93) | 7 |
| 8 | Rows of four parameters `p0` to `p3` (16 bytes; `ROW_PARAMETERS`); key codes and target numbers from a parameter's index; sources `0x20` to `0x23`; `fired` `p0` to `p3` | Rows of one parameter `p` (4 bytes); a key set given one key a row; a trigger's target a signed constant plus `p`; sources `0x20` (`p`) and `0x32` (the firing's row) for a target; `fired` `p` (RULE-105, RULE-106, RULE-116, RULE-42, RULE-43) | 8 |
| 9 | `Evaluator::push`, `Evaluator::push_now`, `neottx rules-run --on-arrival`; the fuzz target `rules_arrival` | `Evaluator::handle`, `Evaluator::tick`, `Evaluator::close`; the fuzz target `rules_budget` (RULE-96, RULE-83) | 1, 4 |
| 10 | The key-to-picture bound waits for the tick: 23 ms at most on every display | `6 + R` ms at most for a refresh period `R`: 23 at 60 hertz, 15 at 120 (RULE-65) | 1 |
| 11 | The music player: 14 rules, 19 groups, rows of three parameters, `double` | 16 rules, 22 groups, rows of one parameter, the double press as three rules with `v3` and `t0` (RULE-93) | 7, 8 |
| 12 | Section 15's items 17, 18, 31 and 32, and parts of 29, 41 and 44 (DEC-6610) | Marked as replaced; the readings DEC-6635 needed are items 45 to 51 (DEC-6636) | — |

### 18.2 What the second build changed in this text

The second form as built (section 17.3) changed no record, message or figure of section 18's rows. It added to the text, in place, on 19 November 2026: the receiver's timekeeping beside the table's arithmetic (RULE-1); the bound on a handling's firings and the counter of those dropped (RULE-5, RULE-72); how a waiting event leaves no trace, how a lost release is taken, and how a recording is keyed (RULE-5, RULE-8, RULE-7); the channel records 21 to 33 (section 8); the `cues` list's bounds and the cue's bound asserted (RULE-109); the amounts `{"fired":"p"}` and an operation's unsigned target (RULE-35); five refusals (RULE-39); a direct command to connections whose tables differ (RULE-114); the `3F7F` selection and the sheet stream the server holds (RULE-40); a disconnected page's frozen picture and its input session (RULE-111); the sound command budget's count (RULE-52); the open page's sub-code and the one table (RULE-58); when a local sound ends (RULE-97); the filmstrip (RULE-51); the component library's rules and limits (RULE-54); the kits' row place, builders and harness (RULE-55); the names table (RULE-56); `neottx rules-run` reading JSON (RULE-96); and the music player's cyan key, sub-code, local objects and page 111's table (RULE-91, RULE-94). Section 17.4 lists what was built against the text or an owner's decision.

## Appendix A. The readable patch fields of each family

The parameter number is the field's place in its family's table, from 0 (RULE-29). The tables below are the program protocol's parameter types at schema version 13, in schema order; a range written as a list is an enumeration, read as the ordinal of its value from 0.

### A.1 The synth6581 family (synth6581, synth8580): family code 12

The index is the ASID register identifier (synth6581-synth8580.md S6581-11); every value is the register's last written byte, 0 to 255.

| Number | Field |
|---|---|
| 0 | `voice1_frequency_low` |
| 1 | `voice1_frequency_high` |
| 2 | `voice1_pulse_width_low` |
| 3 | `voice1_pulse_width_high` |
| 4 | `voice1_attack_decay` |
| 5 | `voice1_sustain_release` |
| 6 | `voice2_frequency_low` |
| 7 | `voice2_frequency_high` |
| 8 | `voice2_pulse_width_low` |
| 9 | `voice2_pulse_width_high` |
| 10 | `voice2_attack_decay` |
| 11 | `voice2_sustain_release` |
| 12 | `voice3_frequency_low` |
| 13 | `voice3_frequency_high` |
| 14 | `voice3_pulse_width_low` |
| 15 | `voice3_pulse_width_high` |
| 16 | `voice3_attack_decay` |
| 17 | `voice3_sustain_release` |
| 18 | `filter_cutoff_low` |
| 19 | `filter_cutoff_high` |
| 20 | `filter_resonance_routing` |
| 21 | `filter_mode_volume` |
| 22 | `voice1_control` |
| 23 | `voice2_control` |
| 24 | `voice3_control` |
| 25 | `voice1_control_second` |
| 26 | `voice2_control_second` |
| 27 | `voice3_control_second` |

### A.2 synth7: family code 13

Numbers 0 to 125 are the six operators' fields, 21 each: operator `k` (1 to 6) has its field `j` of the table below at number `(k − 1) × 21 + j`, named `op<k>_` and the name.

| `j` | Field (after `op<k>_`) | Range |
|---|---|---|
| 0 | `eg_rate_1` | 0 to 99 |
| 1 | `eg_rate_2` | 0 to 99 |
| 2 | `eg_rate_3` | 0 to 99 |
| 3 | `eg_rate_4` | 0 to 99 |
| 4 | `eg_level_1` | 0 to 99 |
| 5 | `eg_level_2` | 0 to 99 |
| 6 | `eg_level_3` | 0 to 99 |
| 7 | `eg_level_4` | 0 to 99 |
| 8 | `break_point` | 0 to 99 |
| 9 | `left_depth` | 0 to 99 |
| 10 | `right_depth` | 0 to 99 |
| 11 | `left_curve` | 0 to 3 |
| 12 | `right_curve` | 0 to 3 |
| 13 | `rate_scaling` | 0 to 7 |
| 14 | `amplitude_sensitivity` | 0 to 3 |
| 15 | `velocity_sensitivity` | 0 to 7 |
| 16 | `output_level` | 0 to 99 |
| 17 | `oscillator_mode` | 0 to 1 |
| 18 | `frequency_coarse` | 0 to 31 |
| 19 | `frequency_fine` | 0 to 99 |
| 20 | `detune` | 0 to 14 |

The voice's own fields follow:

| Number | Field | Range |
|---|---|---|
| 126 | `pitch_eg_rate_1` | 0 to 99 |
| 127 | `pitch_eg_rate_2` | 0 to 99 |
| 128 | `pitch_eg_rate_3` | 0 to 99 |
| 129 | `pitch_eg_rate_4` | 0 to 99 |
| 130 | `pitch_eg_level_1` | 0 to 99 |
| 131 | `pitch_eg_level_2` | 0 to 99 |
| 132 | `pitch_eg_level_3` | 0 to 99 |
| 133 | `pitch_eg_level_4` | 0 to 99 |
| 134 | `algorithm` | 0 to 31 |
| 135 | `feedback` | 0 to 7 |
| 136 | `oscillator_sync` | 0 to 1 |
| 137 | `lfo_speed` | 0 to 99 |
| 138 | `lfo_delay` | 0 to 99 |
| 139 | `lfo_pitch_depth` | 0 to 99 |
| 140 | `lfo_amplitude_depth` | 0 to 99 |
| 141 | `lfo_sync` | 0 to 1 |
| 142 | `lfo_wave` | 0 to 5 |
| 143 | `pitch_sensitivity` | 0 to 7 |
| 144 | `transpose` | 0 to 48 |
| 145 | `name_1` | 0 to 127 |
| 146 | `name_2` | 0 to 127 |
| 147 | `name_3` | 0 to 127 |
| 148 | `name_4` | 0 to 127 |
| 149 | `name_5` | 0 to 127 |
| 150 | `name_6` | 0 to 127 |
| 151 | `name_7` | 0 to 127 |
| 152 | `name_8` | 0 to 127 |
| 153 | `name_9` | 0 to 127 |
| 154 | `name_10` | 0 to 127 |
| 155 | `operator_switch` | 0 to 63 |
| 156 | `mono_poly` | 0 to 1 |
| 157 | `pitch_bend_range` | 0 to 12 |
| 158 | `pitch_bend_step` | 0 to 12 |
| 159 | `portamento_mode` | 0 to 1 |
| 160 | `glissando` | 0 to 1 |
| 161 | `portamento_time` | 0 to 99 |
| 162 | `modulation_wheel_range` | 0 to 99 |
| 163 | `modulation_wheel_assign` | 0 to 7 |
| 164 | `foot_controller_range` | 0 to 99 |
| 165 | `foot_controller_assign` | 0 to 7 |
| 166 | `breath_controller_range` | 0 to 99 |
| 167 | `breath_controller_assign` | 0 to 7 |
| 168 | `after_touch_range` | 0 to 99 |
| 169 | `after_touch_assign` | 0 to 7 |

### A.3 synth106: family code 14, variant 0

| Number | Field | Range |
|---|---|---|
| 0 | `lfo_rate` | 0 to 127 |
| 1 | `lfo_delay` | 0 to 127 |
| 2 | `dco_lfo` | 0 to 127 |
| 3 | `dco_pwm` | 0 to 127 |
| 4 | `noise_level` | 0 to 127 |
| 5 | `vcf_frequency` | 0 to 127 |
| 6 | `vcf_resonance` | 0 to 127 |
| 7 | `vcf_envelope` | 0 to 127 |
| 8 | `vcf_lfo` | 0 to 127 |
| 9 | `vcf_keyboard` | 0 to 127 |
| 10 | `vca_level` | 0 to 127 |
| 11 | `attack` | 0 to 127 |
| 12 | `decay` | 0 to 127 |
| 13 | `sustain` | 0 to 127 |
| 14 | `release` | 0 to 127 |
| 15 | `sub_level` | 0 to 127 |
| 16 | `range` | `feet_16`, `feet_8`, `feet_4` |
| 17 | `pulse` | `false`, `true` |
| 18 | `sawtooth` | `false`, `true` |
| 19 | `chorus` | `off`, `one`, `two` |
| 20 | `pwm` | `lfo`, `manual` |
| 21 | `envelope_polarity` | `positive`, `negative` |
| 22 | `vca` | `envelope`, `gate` |
| 23 | `hpf` | 0 to 3 |

### A.4 synth60: family code 14, variant 1

| Number | Field | Range |
|---|---|---|
| 0 | `lfo_rate` | 0 to 127 |
| 1 | `lfo_delay` | 0 to 127 |
| 2 | `dco_lfo` | 0 to 127 |
| 3 | `dco_pwm` | 0 to 127 |
| 4 | `noise_level` | 0 to 127 |
| 5 | `vcf_frequency` | 0 to 127 |
| 6 | `vcf_resonance` | 0 to 127 |
| 7 | `vcf_envelope` | 0 to 127 |
| 8 | `vcf_lfo` | 0 to 127 |
| 9 | `vcf_keyboard` | 0 to 127 |
| 10 | `vca_level` | 0 to 127 |
| 11 | `attack` | 0 to 127 |
| 12 | `decay` | 0 to 127 |
| 13 | `sustain` | 0 to 127 |
| 14 | `release` | 0 to 127 |
| 15 | `sub_level` | 0 to 127 |
| 16 | `range` | `feet_16`, `feet_8`, `feet_4` |
| 17 | `pulse` | `false`, `true` |
| 18 | `sawtooth` | `false`, `true` |
| 19 | `chorus` | `off`, `one`, `two`, `both` |
| 20 | `pwm` | `lfo`, `manual`, `envelope` |
| 21 | `envelope_polarity` | `positive`, `negative` |
| 22 | `vca` | `envelope`, `gate` |
| 23 | `hpf` | 0 to 3 |
| 24 | `sub_switch` | `false`, `true` |

### A.5 synthD: family code 15

| Number | Field | Range |
|---|---|---|
| 0 | `glide` | 0 to 16383 |
| 1 | `oscillator_2_frequency` | 0 to 16383 |
| 2 | `oscillator_3_frequency` | 0 to 16383 |
| 3 | `external_input_volume` | 0 to 16383 |
| 4 | `oscillator_1_volume` | 0 to 16383 |
| 5 | `oscillator_2_volume` | 0 to 16383 |
| 6 | `oscillator_3_volume` | 0 to 16383 |
| 7 | `noise_volume` | 0 to 16383 |
| 8 | `cutoff_frequency` | 0 to 16383 |
| 9 | `emphasis` | 0 to 16383 |
| 10 | `filter_attack_time` | 0 to 16383 |
| 11 | `filter_decay_time` | 0 to 16383 |
| 12 | `filter_sustain_level` | 0 to 16383 |
| 13 | `amount_of_contour` | 0 to 16383 |
| 14 | `loudness_attack_time` | 0 to 16383 |
| 15 | `loudness_decay_time` | 0 to 16383 |
| 16 | `loudness_sustain_level` | 0 to 16383 |
| 17 | `glide_switch` | 0 to 127 |
| 18 | `oscillator_1_range_octave` | 0 to 127 |
| 19 | `oscillator_2_range_octave` | 0 to 127 |
| 20 | `oscillator_3_range_octave` | 0 to 127 |
| 21 | `oscillator_3_control` | 0 to 127 |
| 22 | `oscillator_3_range_lo_hi` | 0 to 127 |
| 23 | `external_input_switch` | 0 to 127 |
| 24 | `oscillator_1_switch` | 0 to 127 |
| 25 | `oscillator_2_switch` | 0 to 127 |
| 26 | `oscillator_3_switch` | 0 to 127 |
| 27 | `noise_switch` | 0 to 127 |
| 28 | `decay_switch` | 0 to 127 |
| 29 | `tune` | 0 to 16383 |
| 30 | `modulation_mix` | 0 to 127 |
| 31 | `oscillator_1_range_lo_hi` | 0 to 127 |
| 32 | `oscillator_1_waveform` | 0 to 127 |
| 33 | `oscillator_2_range_lo_hi` | 0 to 127 |
| 34 | `oscillator_2_waveform` | 0 to 127 |
| 35 | `oscillator_3_waveform` | 0 to 127 |
| 36 | `main_output_volume` | 0 to 127 |
| 37 | `oscillator_modulation` | 0 to 127 |
| 38 | `noise_colour` | 0 to 127 |
| 39 | `filter_modulation` | 0 to 127 |
| 40 | `keyboard_control_1` | 0 to 127 |
| 41 | `keyboard_control_2` | 0 to 127 |

### A.6 The synth53 family (synth53, synth52, synth51): family code 16, variants 0, 1 and 2

| Number | Field | Range |
|---|---|---|
| 0 | `osc_a_frequency` | 0 to 120 |
| 1 | `osc_b_frequency` | 0 to 120 |
| 2 | `osc_b_fine_tune` | 0 to 127 |
| 3 | `osc_a_saw` | 0 to 1 |
| 4 | `osc_a_square` | 0 to 1 |
| 5 | `osc_b_saw` | 0 to 1 |
| 6 | `osc_b_tri` | 0 to 1 |
| 7 | `osc_b_square` | 0 to 1 |
| 8 | `osc_a_pulse_width` | 0 to 120 |
| 9 | `osc_b_pulse_width` | 0 to 120 |
| 10 | `osc_sync` | 0 to 1 |
| 11 | `osc_b_low_freq` | 0 to 1 |
| 12 | `osc_b_keyboard` | 0 to 1 |
| 13 | `glide_rate` | 0 to 120 |
| 14 | `osc_a_level` | 0 to 120 |
| 15 | `osc_b_level` | 0 to 120 |
| 16 | `noise_level` | 0 to 120 |
| 17 | `cutoff` | 0 to 120 |
| 18 | `resonance` | 0 to 120 |
| 19 | `filter_keyboard_track` | 0 to 2 |
| 20 | `lfo_frequency` | 0 to 120 |
| 21 | `lfo_initial_amount` | 0 to 120 |
| 22 | `lfo_saw` | 0 to 1 |
| 23 | `lfo_tri` | 0 to 1 |
| 24 | `lfo_square` | 0 to 1 |
| 25 | `lfo_source_mix` | 0 to 120 |
| 26 | `lfo_freq_a` | 0 to 1 |
| 27 | `lfo_freq_b` | 0 to 1 |
| 28 | `lfo_freq_pw_a` | 0 to 1 |
| 29 | `lfo_freq_pw_b` | 0 to 1 |
| 30 | `lfo_filter` | 0 to 1 |
| 31 | `poly_mod_filt_env_amount` | 0 to 127 |
| 32 | `poly_mod_osc_b_amount` | 0 to 120 |
| 33 | `poly_mod_freq_a` | 0 to 1 |
| 34 | `poly_mod_pw` | 0 to 1 |
| 35 | `poly_mod_filter` | 0 to 1 |
| 36 | `vintage` | 0 to 127 |
| 37 | `aftertouch_to_filter` | 0 to 1 |
| 38 | `aftertouch_to_lfo` | 0 to 1 |
| 39 | `env_filter_amount` | 0 to 120 |
| 40 | `velocity_to_filter` | 0 to 1 |
| 41 | `velocity_to_amp` | 0 to 1 |
| 42 | `attack_filter` | 0 to 120 |
| 43 | `attack_vca` | 0 to 120 |
| 44 | `decay_filter` | 0 to 120 |
| 45 | `decay_vca` | 0 to 120 |
| 46 | `sustain_filter` | 0 to 120 |
| 47 | `sustain_vca` | 0 to 120 |
| 48 | `release_filter` | 0 to 120 |
| 49 | `release_vca` | 0 to 120 |
| 50 | `release_switch` | 0 to 1 |
| 51 | `unison` | 0 to 1 |
| 52 | `unison_voice_count` | 0 to 10 |
| 53 | `unison_detune` | 0 to 7 |
| 54 | `unison_note_1` | 0 to 10 |
| 55 | `unison_note_2` | 0 to 10 |
| 56 | `unison_note_3` | 0 to 10 |
| 57 | `unison_note_4` | 0 to 10 |
| 58 | `unison_note_5` | 0 to 10 |
| 59 | `unison_note_6` | 0 to 10 |
| 60 | `unison_note_7` | 0 to 10 |
| 61 | `unison_note_8` | 0 to 10 |
| 62 | `unison_note_9` | 0 to 10 |
| 63 | `unison_note_10` | 0 to 10 |
| 64 | `pitch_wheel_range` | 0 to 11 |
| 65 | `retrigger_and_unison` | 0 to 3 |

### A.7 synth8: family code 17

On synth8 part 1 is the upper patch and part 2 the lower (synth8.md S8-18).

| Number | Field | Range |
|---|---|---|
| 0 | `lfo_rate` | 0 to 127 |
| 1 | `lfo_delay_time` | 0 to 127 |
| 2 | `lfo_waveform` | 0 to 127 |
| 3 | `vco_lfo_mod` | 0 to 127 |
| 4 | `vco_env_mod` | 0 to 127 |
| 5 | `vco_modulator` | 0 to 127 |
| 6 | `pulse_width_mod` | 0 to 127 |
| 7 | `pulse_width_mod_source` | 0 to 127 |
| 8 | `cross_mod` | 0 to 127 |
| 9 | `vco1_range` | 0 to 127 |
| 10 | `vco1_waveform` | 0 to 127 |
| 11 | `vco2_sync` | 0 to 127 |
| 12 | `vco2_low_freq` | 0 to 127 |
| 13 | `vco2_range` | 0 to 127 |
| 14 | `vco2_fine_tune` | 0 to 127 |
| 15 | `vco2_waveform` | 0 to 127 |
| 16 | `vco1_level` | 0 to 127 |
| 17 | `vco2_level` | 0 to 127 |
| 18 | `hpf_cutoff` | 0 to 127 |
| 19 | `vcf_cutoff` | 0 to 127 |
| 20 | `vcf_resonance` | 0 to 127 |
| 21 | `vcf_slope` | 0 to 127 |
| 22 | `vcf_env_mod` | 0 to 127 |
| 23 | `vcf_envelope_select` | 0 to 127 |
| 24 | `vcf_lfo_mod` | 0 to 127 |
| 25 | `vcf_key_follow` | 0 to 127 |
| 26 | `vca_level` | 0 to 127 |
| 27 | `vca_lfo_mod` | 0 to 127 |
| 28 | `env1_attack` | 0 to 127 |
| 29 | `env1_decay` | 0 to 127 |
| 30 | `env1_sustain` | 0 to 127 |
| 31 | `env1_release` | 0 to 127 |
| 32 | `env1_polarity` | 0 to 127 |
| 33 | `env2_attack` | 0 to 127 |
| 34 | `env2_decay` | 0 to 127 |
| 35 | `env2_sustain` | 0 to 127 |
| 36 | `env2_release` | 0 to 127 |
| 37 | `assign_mode` | 0 to 127 |
| 38 | `env1_key_follow` | 0 to 127 |
| 39 | `env2_key_follow` | 0 to 127 |
| 40 | `vco1_bend` | 0 to 127 |
| 41 | `vco2_bend` | 0 to 127 |

### A.8 synth80: family code 18

| Number | Field | Range |
|---|---|---|
| 0 | `feet_1` | 0 to 127 |
| 1 | `feet_2` | 0 to 127 |
| 2 | `detune_channel_2` | 0 to 127 |
| 3 | `mix` | 0 to 127 |
| 4 | `brilliance` | 0 to 127 |
| 5 | `resonance` | 0 to 127 |
| 6 | `keyboard_brilliance_low` | 0 to 127 |
| 7 | `keyboard_brilliance_high` | 0 to 127 |
| 8 | `keyboard_level_low` | 0 to 127 |
| 9 | `keyboard_level_high` | 0 to 127 |
| 10 | `sub_oscillator_function` | 0 to 127 |
| 11 | `sub_oscillator_speed` | 0 to 127 |
| 12 | `sub_oscillator_vco` | 0 to 127 |
| 13 | `sub_oscillator_vcf` | 0 to 127 |
| 14 | `sub_oscillator_vca` | 0 to 127 |
| 15 | `touch_pitch_bend` | 0 to 127 |
| 16 | `touch_speed` | 0 to 127 |
| 17 | `touch_vco` | 0 to 127 |
| 18 | `touch_vcf` | 0 to 127 |
| 19 | `ring_modulator_attack_time` | 0 to 127 |
| 20 | `ring_modulator_decay_time` | 0 to 127 |
| 21 | `ring_modulator_depth` | 0 to 127 |
| 22 | `ring_modulator_speed` | 0 to 127 |
| 23 | `ring_modulator_modulation` | 0 to 127 |
| 24 | `sustain_mode` | 0 to 127 |
| 25 | `sustain` | 0 to 127 |
| 26 | `glide_mode` | 0 to 127 |
| 27 | `glide_speed` | 0 to 127 |
| 28 | `tremolo_chorus` | 0 to 127 |
| 29 | `chorus` | 0 to 127 |
| 30 | `tremolo` | 0 to 127 |
| 31 | `tremolo_chorus_speed` | 0 to 127 |
| 32 | `tremolo_chorus_depth` | 0 to 127 |
| 33 | `channel_1_pwm_speed` | 0 to 127 |
| 34 | `channel_1_pwm` | 0 to 127 |
| 35 | `channel_1_pw` | 0 to 127 |
| 36 | `channel_1_square` | 0 to 127 |
| 37 | `channel_1_sawtooth` | 0 to 127 |
| 38 | `channel_1_noise` | 0 to 127 |
| 39 | `channel_1_hpf` | 0 to 127 |
| 40 | `channel_1_hpf_resonance` | 0 to 127 |
| 41 | `channel_1_lpf` | 0 to 127 |
| 42 | `channel_1_lpf_resonance` | 0 to 127 |
| 43 | `channel_1_filter_initial_level` | 0 to 127 |
| 44 | `channel_1_filter_attack_level` | 0 to 127 |
| 45 | `channel_1_filter_attack` | 0 to 127 |
| 46 | `channel_1_filter_decay` | 0 to 127 |
| 47 | `channel_1_filter_release` | 0 to 127 |
| 48 | `channel_1_vcf_level` | 0 to 127 |
| 49 | `channel_1_sine` | 0 to 127 |
| 50 | `channel_1_amplifier_attack` | 0 to 127 |
| 51 | `channel_1_amplifier_decay` | 0 to 127 |
| 52 | `channel_1_amplifier_sustain` | 0 to 127 |
| 53 | `channel_1_amplifier_release` | 0 to 127 |
| 54 | `channel_1_level` | 0 to 127 |
| 55 | `channel_1_initial_brilliance` | 0 to 127 |
| 56 | `channel_1_initial_level` | 0 to 127 |
| 57 | `channel_1_after_brilliance` | 0 to 127 |
| 58 | `channel_1_after_level` | 0 to 127 |
| 59 | `channel_2_pwm_speed` | 0 to 127 |
| 60 | `channel_2_pwm` | 0 to 127 |
| 61 | `channel_2_pw` | 0 to 127 |
| 62 | `channel_2_square` | 0 to 127 |
| 63 | `channel_2_sawtooth` | 0 to 127 |
| 64 | `channel_2_noise` | 0 to 127 |
| 65 | `channel_2_hpf` | 0 to 127 |
| 66 | `channel_2_hpf_resonance` | 0 to 127 |
| 67 | `channel_2_lpf` | 0 to 127 |
| 68 | `channel_2_lpf_resonance` | 0 to 127 |
| 69 | `channel_2_filter_initial_level` | 0 to 127 |
| 70 | `channel_2_filter_attack_level` | 0 to 127 |
| 71 | `channel_2_filter_attack` | 0 to 127 |
| 72 | `channel_2_filter_decay` | 0 to 127 |
| 73 | `channel_2_filter_release` | 0 to 127 |
| 74 | `channel_2_vcf_level` | 0 to 127 |
| 75 | `channel_2_sine` | 0 to 127 |
| 76 | `channel_2_amplifier_attack` | 0 to 127 |
| 77 | `channel_2_amplifier_decay` | 0 to 127 |
| 78 | `channel_2_amplifier_sustain` | 0 to 127 |
| 79 | `channel_2_amplifier_release` | 0 to 127 |
| 80 | `channel_2_level` | 0 to 127 |
| 81 | `channel_2_initial_brilliance` | 0 to 127 |
| 82 | `channel_2_initial_level` | 0 to 127 |
| 83 | `channel_2_after_brilliance` | 0 to 127 |
| 84 | `channel_2_after_level` | 0 to 127 |
