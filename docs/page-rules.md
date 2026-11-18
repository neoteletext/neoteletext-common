# The page rule table: binding events to local actions in the browser

| | |
|---|---|
| **Status** | Specification of 18 November 2026, written while the owner was away, for building at once. The owner's decisions are DEC-6522 (the rule table) and REQ-6523 (no input unless asked); what this document decides beyond them is listed in section 15 and recorded in rdm as DEC-6525, which waits for the owner's confirmation. Section 16 lists the rdm requirements that carry this document. |
| **Amended** | 18 November 2026, by the owner's decision DEC-6580 ("yes record 1 to 3 and build them"): an input event's rules are evaluated when it arrives and their sound actions delivered then (RULE-5, RULE-7, RULE-8, RULE-96); the sound helper asks for a small device buffer while a local sound is open (RULE-97); and the tick is locked to the display's refresh (RULE-98). RULE-64 to RULE-66 hold the new budgets. What that amendment decided beyond the owner's three items is in section 15, items 17 to 22. |
| **Asked for by** | The owner, 18 November 2026: "I ALSO WANT YOU TO FULL SPECIFY AND DOCUMENT OUR META LANGUAGE, IMPLEMENT IT IN CODE", and a demonstration: "A MUSIC PLAYER THAT SHOWS SYNTHESIZERS INSTANTLY PLAYING ON A KEYPRESS AND INSTANTLY DISPLAYING LEVELS VISUALLY ALSO IN RESPONSE TO THE KEYPRESS". |
| **Process** | DEVELOPMENT.md section 2.3 (a proposal with its own security analysis, section 12 of this document), section 3.5 (every record in full) and section 14 (security). |
| **Companion** | `animation.md` (requirements ANIM-n) defines the objects, records and renderer behaviour that this document's animation actions and collision conditions act on. |
| **Repositories it changes** | neoteletext-renderer-teletext (the engine, with the new crate `neoteletext-rules`), neoteletext-browser, neoteletext-app-server, neoteletext-server-ts-protocol (the TypeScript kit), neoteletext-server-channels (the Python kit), neoteletext-server-ts-ui-components (the component library), every channel, and the new channel neoteletext-server-channel-musicplayer. |

Requirements are numbered `RULE-n`. Each names in brackets the repository that implements it. "MUST", "SHOULD" and "MAY" are used as DEVELOPMENT.md section 4 defines them. Every integer on a wire is big-endian unless a field says otherwise. "The receiver" is any program that shows a page to a viewer; the NeoTeletext browser is the receiver this document specifies in full.

---

## 1. Purpose, model and vocabulary

### 1.1 Purpose

A page may carry a **rule table**: a bounded, declarative list of rules, each binding one event (a key, a pointer action on a target, a timer, the page opening, a condition becoming true) to a short list of local actions (a MIDI message to a synthesizer the page is playing, showing or hiding an object, changing a variable, telling the page's channel). The receiver evaluates the table sixty times a second. It gives a page sound and graphics that answer the viewer within one tick with no round trip to the server, and it is the only way a page can ask for the viewer's input to be sent to its channel (REQ-6523).

The table is not a program. It has no loops, no arithmetic beyond saturating addition of a constant to a declared variable, no function calls, and no rule can cause another to run in the same tick. REQ-417 (the engine's REQ-SEC-004) allows it as the one exception to "no executable content", inside the bounds of section 9 and no further.

### 1.2 Terms

| Term | Meaning |
|---|---|
| **Tick** | One sixtieth of a second on the receiver's presentation clock (ANIM-1). Every rule is evaluated on tick boundaries only. |
| **Page tick** | The number of ticks since the page was opened in this view, counted from 0. |
| **Rule table** | The one table a page has, for all its sub-pages (RULE-2). |
| **Rule** | A trigger, an optional condition and at most 16 actions (RULE-3). |
| **Trigger** | The event that can make a rule fire (section 3). |
| **Condition** | An expression of integer comparisons that must hold for the rule to fire (section 4). |
| **Action** | One local effect (section 5). |
| **Fire** | A rule fires when its trigger occurs and its condition holds; its actions then run in written order. |
| **Target** | Something on the page that a pointer trigger, a `show`, a `move` or a collision test names: the page, a teletext control, an animation object, or a rectangle (RULE-12). |
| **Animation object** | A numbered thing a renderer keeps and can move, show, hide, order and cycle: a teletext sprite (ANIM-7), a ReGIS numbered drawing (ANIM-9) or a NAPLPS object (ANIM-11). |
| **Page variable** | One of at most 32 integers a table declares, each held to its declared range (RULE-14). |
| **Timer** | One of at most 8 tick counters a table declares, plus the page timer that starts at opening (RULE-15). |
| **Value** | Something a condition reads: a variable, a key's state, a timer, a target's state, a sound's level, a synthesizer's state (section 6). |
| **Open page** | The one page of the active tab that keys would go to (the browser's REQ-1378). Only the open page's table is evaluated, and "opened", "shown" and "closed" in this document mean becoming and ceasing to be the open page (RULE-58). |
| **Snapshot** | The values as they stood when a tick began; every condition and every `send` of a value reads the snapshot (RULE-7). |
| **Local sound** | A synthesizer sound with no blocks from the server, rendered by the receiver's sound helper and played by rules' `midi` actions (RULE-60). |
| **Audio channel** | One of the four voices of the audio profile, 0 to 3 (the engine's REQ-AUD-010), named `channel` in the program protocol's `play`, `stop` and `gain`. It is not a MIDI channel. |
| **Part** | A MIDI channel, 1 to 16, of one synthesizer sound (midi-architecture.md MIDI-3). |
| **Program** | A channel's application, which speaks the program protocol to the server. |

### 1.3 Requirements of the model

**RULE-1 [neoteletext-common]. A rule table is event binding, never executable content.**
- **Statement.** A rule table MUST be only what sections 2 to 6 define: declarations (variables, timers, rectangles), rules (one trigger, at most one condition, at most 16 actions) and per-sub-page lists of rules switched off. No requirement may add to it a loop, a jump, a rule that runs another rule within a tick, arithmetic other than `add` of a constant to a variable with saturation at the variable's declared bounds, a call of a routine, text processing, or any action that reaches the network other than `send`, `echo` and the answer to a state query (section 7.4), unless REQ-417 is first changed by the owner's recorded decision.
- **Reason and source.** The owner's ruling of 18 November 2026: "this is not executable logic it is event binding to local actions with simple evaluatios" (DEC-6522 item 1); the lessons of MHEG-5 recorded in DEC-6522 items 13 and 14.
- **Verification.** Inspection of the crate `neoteletext-rules` against this list at each change; the fuzz targets of RULE-83.

**RULE-2 [neoteletext-common]. One table for a page, for all its sub-pages.**
- **Statement.** A page (a magazine and page number, `0x100` to `0x8FF`) MUST have at most one rule table in a view at a time, which applies while any sub-page of that page is the one shown. A table MAY list, for at most 16 sub-codes, the rules that are switched off while that sub-page is shown (RULE-17). A table is replaced whole by a later table for the same page (a higher generation, RULE-41); replacing it resets the page's variables, timers and rule switches to the new table's declarations, as opening the page does, and fires the new table's `open` rules. A page with no table evaluates nothing and sends no input (RULE-50).
- **Reason and source.** DEC-6522 item 5.
- **Verification.** Tests in `neoteletext-rules`: a table applies across a change of sub-page with variables kept; a sub-page's list switches rules off only while it is shown; a replacement table resets state.

**RULE-3 [engine: neoteletext-rules]. The shape of a rule.**
- **Statement.** A rule MUST consist of: a trigger (exactly one, section 3); a condition (none or one, section 4; a `becomes` trigger carries the condition itself and takes no second one); a list of 0 to 16 actions (section 5), where a rule with no actions MUST have `echo` set; the flag `echo`; the flag `enabled`, its state when the page opens. A table holds 0 to 64 rules, numbered 0 to 63 in the order written, which is **rule order**.
- **Reason and source.** DEC-6522 items 5 and 10.
- **Verification.** Codec tests: each shape round-trips; a rule with no actions and no `echo`, a 17th action and a 65th rule are each refused whole (RULE-70).

## 2. The clock and the evaluation order

**RULE-4 [engine: neoteletext-rules; neoteletext-browser]. Sixty ticks a second, counted from the page's opening.**
- **Statement.** The receiver MUST evaluate an open page's table once for each tick of its presentation clock (ANIM-1), 60 ticks a second: tick `n` of the clock is due `n × 50,000 ÷ 3` microseconds (rounded down) after the clock's start, so that the ticks never drift against real time. A page's first evaluation is page tick 0, at the first clock tick after the page was opened in the view and its table decoded; each later clock tick is the next page tick. The page tick is a 32-bit unsigned number that stops at 4,294,967,295. When the receiver is late and more than one tick is due, it MUST evaluate each due tick in order, at most `MAX_CATCH_UP_TICKS` (6) in one wake; when more than that are due, it MUST move the clock's start later by the ticks it will not run, so that page time slows and no page tick is ever skipped. Evaluation stops while the page is not the one shown in its view, and the page is opened afresh when it is shown again. A receiver with a display MAY move the clock's start by small steps to keep the ticks in step with the display's refresh, within the bound of RULE-98; page time then follows the display, and still no page tick is skipped or run twice.
- **Reason and source.** DEC-6522 item 3 (the owner: "this event system operates on 60 ticks a second"); DEC-6524 item 1. Slowing rather than skipping keeps a recording of inputs by page tick exactly replayable.
- **Verification.** Tests in `neoteletext-rules` with a scripted clock: 3,600 ticks are due in exactly 60 seconds; seven ticks overdue evaluate six and move the start; the browser's decoder test holds that a hidden page evaluates nothing.

**RULE-5 [engine: neoteletext-rules]. The fixed order within a tick, and the one step that may be taken early.**
- **Statement.** In each tick the evaluator MUST do exactly this, in this order, and in no other:
  1. **Take the snapshot** (RULE-7): the metered values newest from the sound helper (RULE-33), then every other value as the last tick left it.
  2. **Input events**, those that arrived since the last tick, in arrival order, at most `MAX_EVENTS_PER_TICK` (16); later ones wait for the next tick in a queue of at most `MAX_QUEUED_EVENTS` (64). For each event: update the input state (RULE-8); then, for each rule in rule order that is enabled in the snapshot, whose trigger the event matches (section 3) and whose condition holds, run its actions in written order.
  3. **Timers**, in identifier order: the page timer first, then timers 0 to 7. For each timer that is running in the snapshot, for each enabled rule in rule order whose `after` or `every` trigger on that timer is due this tick (RULE-15) and whose condition holds, run its actions.
  4. **`open`**, on page tick 0 only: each enabled `open` rule in rule order whose condition holds.
  5. **`becomes`**, in rule order: for each enabled `becomes` rule, evaluate its condition; the rule fires when the condition holds now and did not hold at the rule's previous evaluation (RULE-11); run its actions.
  6. **Animation** (ANIM-14): advance each cycling object whose frame is due.
  7. **Apply**: the effects of every action run in this tick become the state the next tick's snapshot shows (RULE-7); outputs (sound operations, picture changes, sends) leave in the order their actions ran.
- A `close` rule is evaluated in one final tick when the page stops being shown, in which steps 2, 3 and 5 are not run.
- **Step 2 on arrival.** A receiver MAY, and the browser MUST (RULE-96), take step 2 for an input event at the moment the event arrives, without waiting for the tick. The event is then an event of the next tick to be evaluated, tick `t`, and is handled exactly as step 2 above handles it: step 1 of tick `t` is taken first if no earlier arrival of the interval has taken it; events are handled in arrival order, an event still waiting in the queue before a later arrival; its rules are matched in rule order against the snapshot of tick `t`; and a rule that fires runs its actions in written order. One thing alone differs: the **sound operations** of those actions — `midi`, `play`, `stop` and `gain` (RULE-20, codes 1 to 4) — leave at once, in the order their actions ran, and every other effect and output of those actions (what they write to variables, timers and rules, their animation operations, their `send` and `echo` reports) is held and applied or sent in step 7 of tick `t`, in the order the actions ran, with the sound operations left out as already delivered. At tick `t` the evaluator MUST NOT evaluate the event again: its rules' conditions, their firings and their counts are those decided on arrival, and tick `t` goes on from step 2's remaining events (those still in the queue, up to the tick's 16 in all) to steps 3 to 7. Every other trigger (`after`, `every`, `open`, `close`, `becomes`) is evaluated only at its tick, and its sound operations leave in step 7.
- **The two ways are one order.** For the same table, the same events in the same arrival order within the same tick intervals, and the same world at each snapshot, a receiver that takes step 2 on arrival and one that takes it at the tick MUST produce the same firings, the same reports with the same page ticks, the same animation operations, the same sound operations in the same order, the same counters (RULE-72) and the same rule state at the end of every tick. Only the real time at which a sound operation leaves differs. A recording of each event with its page tick and its place among that tick's events therefore replays exactly through either.
- **Reason and source.** DEC-6522 item 13: the order is part of the first version, so no second order ever has to be allowed. Steps 4 and 6 and the placement of `close` are this document's (section 15, item 3). Step 2 on arrival is the owner's decision DEC-6580 item 1 (18 November 2026): a key's note waited up to 16.7 milliseconds, 8.3 on average, for the tick, the largest part of the delay from a key to sound (RULE-64). Step 2 is the first step of a tick that reads anything but the snapshot, so taking it early changes nothing a later step can see.
- **Verification.** A test of `neoteletext-rules` with one table that has a rule of every trigger kind writing its own number to a log by `send`: the order of sends in one tick is exactly steps 2 to 5; property test: the same table and the same event script give the same outputs on every run. For step 2 on arrival: a test that a key rule's four sound operations reach the world before the tick and its variable, animation operation, `send` and `echo` at the tick, once; and a property test over random tables and random events at random places in the tick interval, given at the tick, on arrival, and each either way, that compares the sound operations, every other output and the counters at every tick.

**RULE-6 [engine: neoteletext-rules]. No cascade within a tick.**
- **Statement.** Nothing an action does MUST be visible to any condition, trigger or other action's reading in the same tick. A variable set, a target shown, hidden, moved or given a frame, a timer started or stopped, a rule enabled or disabled, and a sound started or stopped by an action in tick `t` are first seen in the snapshot of tick `t + 1`. A rule therefore cannot fire another rule in the same tick, and a rule that disables itself still completes its own actions. The work of a tick is bounded by the table's size and by `MAX_ACTIONS_PER_TICK` (256): once that many actions have run in a tick, further rule firings in that tick are dropped whole, counted, and reported once a second at most as a `tick_overrun` fault (RULE-72). A firing decided on an event's arrival (RULE-5, RULE-96) counts against the tick the event belongs to, and one that would pass the cap is dropped whole there, its sound operations with it. The one thing of an action that the same tick can show is physical: the sound of a sound operation delivered on arrival may already be in the metered values steps 3 to 5 read (RULE-7), as the sound of any note is one tick later; no rule state, target state or sound state (RULE-27) of an action is ever seen in its own tick.
- **Reason and source.** DEC-6522 item 14.
- **Verification.** Tests: rule A sets a variable and rule B's `becomes` on it fires in the next tick, never the same; a rule that disables itself runs all its actions; a table built to fire 64 rules on each of 16 events stops at 256 actions and reports the overrun.

**RULE-7 [engine: neoteletext-rules]. Reads come from the snapshot; writes accumulate in order.**
- **Statement.** The evaluator MUST keep two copies of the page's rule state: the snapshot `S`, read by every condition and every `send` of a value during the tick, and the working state `W`, which starts each tick equal to `S` and to which each action's effect is applied in the order the actions run. `add` reads the variable's value in `W`, so two `add` actions in one tick both count. At step 7 `S` becomes `W`. The rule state is: the variables; each timer's running flag and start tick; each rule's enabled flag and each `becomes` rule's previous result; each named target's local animation state (ANIM-6: shown, position, layer and order, frame, cycling, forced look); and, read only, the metered and tracked sound values of section 6.
- **What the snapshot of tick `t` holds, and when it is taken.** The snapshot is taken once for a tick: at the tick, or, when step 2 is taken on arrival (RULE-5), at the arrival of the first event of the interval before the tick. It holds:
  1. the variables, the timers and the rules' enabled flags exactly as step 7 of tick `t − 1` left them (at page tick 0, as the table declares them). These cannot change between ticks, so they are the same whenever the snapshot is taken;
  2. the world as it is at the moment the snapshot is taken: each named target's state and bounding rectangle, the sound on each audio channel (RULE-27), the tracked synthesizer values (RULE-28 to RULE-30), which sub-page is shown (RULE-17), and the newest metered report (RULE-33). This is the world as tick `t − 1` left it, changed only by what the server or the viewer's browser did since (a record that moved an object, a play command, a turn to another sub-page, a newer metered report).
- Every condition of tick `t` — those of step 2, whenever it is taken, and those of steps 3 to 5 — and every `send` of a value reads that one snapshot, with one exception: when the snapshot was taken on an arrival, steps 3 to 5 of tick `t` read the **metered** values (`level`, `envelope_stage`, `envelope_level`, `voices`) of the newest report at the tick, not of the snapshot, so that a meter is never a tick late because a key arrived. A change to the world that lands after the snapshot of tick `t` — a metered report excepted, as just said — is first seen in the snapshot of tick `t + 1`. A rule evaluated on arrival therefore reads the last completed tick's variables, timers, enabled flags and target states and the metered values of the newest report at the interval's first arrival; never anything a rule of its own interval did.
- **For a recording.** The inputs of a page are its events, its metered reports and the changes others make to its world. A recording that stores each with its page tick and its place among that tick's inputs, and is replayed in that order, gives the same result on every run and through either way of RULE-5. Where every metered report and world change of an interval comes before the interval's first event, the two ways of RULE-5 give the same result as each other.
- **Reason and source.** DEC-6522 item 14; this document's choice of how two writes in one tick combine (section 15, item 4). DEC-6580 item 1: "a rule triggered by an input reads the last completed tick's state". Taking the world once for a tick, at the first arrival, keeps every condition of the tick on one state, so that no rule of a tick can see what another did (RULE-6) however the events are timed; the metered exception is section 15, item 18.
- **Verification.** Tests: `set v 5` then `add v 1` in one tick leave 6; a condition on `v` in the same tick reads the old value. On arrival: a key that sets a variable and a second key of the same interval whose condition reads it, which does not fire until the next interval; a timer started in tick `t` read by an arrival of the interval before tick `t + 2`; a metered report and a sub-page turn after the interval's first arrival, which the interval's later arrivals do not see, the tick's `becomes` rule sees for the metered value alone, and the next interval sees whole.

**RULE-8 [engine: neoteletext-rules]. Input state follows the events, not the snapshot.**
- **Statement.** The **input state** — which keys are down, which pointer buttons are down, where the pointer is and which targets it is inside — MUST be updated event by event in step 2, before the rules are matched against that event, so that a condition on a key's state in step 2 sees the keys as they are just after the triggering event, and steps 3 to 5 see them as they are after all the tick's events. Input state is not something an action can change, so RULE-6 is not broken. The evaluator tracks at most `MAX_KEYS_DOWN` (16) keys down at once; a 17th press is treated as not down for conditions (its `key` trigger still fires). When the page loses the keyboard, the pointer leaves, or the page closes, the receiver MUST give the evaluator a release (marked lost, as the input protocol's L flag, DOC-1935) for every key and button still down and a leave for every target the pointer was inside, so that `key_up`, `release` and `leave` rules fire and no note is left sounding. When step 2 is taken on arrival (RULE-5) the input state is updated on each arrival, in arrival order, exactly as above: an event's rules see the keys and the pointer as every event that arrived before it left them, itself included, whether those events arrived in this interval or an earlier one, and steps 3 to 5 see them as they are at the tick. Which objects a pointer event is inside is settled when the event is handled.
- **Reason and source.** A chord (a rule on key A when Shift is down) must work when both arrive in one tick; a held note must end when focus is lost (the engine's REQ-207).
- **Verification.** Tests: Shift and A in one tick fire the rule on A-with-Shift; a blur with two keys down fires both `key_up` rules in rule order by key arrival. On arrival: a held key and then a key whose rule asks for it sound at once; the same two the other way round do not.

## 3. Triggers

**RULE-9 [engine: neoteletext-rules]. The trigger kinds.**
- **Statement.** A trigger MUST be exactly one of the kinds below. The code is its byte in the record (RULE-43).

| Code | Name | Fires when | Fields |
|---|---|---|---|
| 1 | `key` | a key matching the key set is pressed; with `repeat` set, also on each automatic repeat | key set (RULE-10), `repeat`, modifier mask and value |
| 2 | `key_up` | a key matching the key set is released (or lost, RULE-8) | key set, modifier mask and value |
| 3 | `press` | a pointer button or a touch contact goes down inside the target | target, button |
| 4 | `release` | a button or contact that went down inside the target comes up, wherever the pointer then is | target, button |
| 5 | `enter` | the pointer comes inside the target | target |
| 6 | `leave` | the pointer goes outside the target, or leaves the page (RULE-8) | target |
| 7 | `open` | page tick 0 (RULE-5 step 4) | none |
| 8 | `close` | the page stops being shown (RULE-5) | none |
| 9 | `becomes` | its condition holds now and did not at the rule's previous evaluation (RULE-11) | the condition |
| 10 | `every` | each `ticks` ticks after the timer started, while it runs | timer, `ticks` |
| 11 | `after` | once, `ticks` ticks after the timer started | timer, `ticks` |
| 12 | `text` | text arrives that is not a key: a paste, an input method's composition or its committed text | none |
| 13 | `move` | the pointer moves to another pixel inside the target; with `held` set, only while a button is down | target, `held` |
| 14 | `wheel` | the wheel turns with the pointer inside the target | target |
| 15 | `focus` | the page gains the keyboard | none |
| 16 | `blur` | the page loses the keyboard | none |

- Kinds 1 to 11 are DEC-6522 item 5's. Kinds 12 to 16 are added by this document so that every kind of input REQ-6523 names (typed text, a paste, a movement, the wheel, a focus change) has a trigger a rule can bind and `send` (section 15, item 1).
- A button is 0 (left, or a touch contact, or a pen touching), 1 (middle), 2 (right) or 255 (any). The modifier mask and value are the input protocol's modifier bits (DOC-1935: Shift 1, Alt 2, Control 4, Super 8, Hyper 16, Meta 32, Caps Lock 64, Num Lock 128): the trigger matches when `(mods AND mask) = value`; mask 0 ignores modifiers. A key or click made with the browser's own modifier never reaches the evaluator (RULE-51).
- `ticks` is 1 to `MAX_TIMER_TICKS` (216,000, one hour).
- **Reason and source.** DEC-6522 item 5; REQ-6523.
- **Verification.** One test for each kind in `neoteletext-rules`: the event that fires it, and the nearest events that must not.

**RULE-10 [engine: neoteletext-rules]. Naming keys.**
- **Statement.** A key set MUST be either **any key** or 1 to `MAX_KEYS_PER_TRIGGER` (16) keys, each one of:
  - **a character key** (kind 1): the Unicode scalar value the active keyboard layout gives the key without Shift, exactly the `key` of the input protocol's KEY event when it is a character (DOC-1935). Letters are the lower-case form.
  - **a named key** (kind 2): a functional key by its code in the input protocol's table (DOC-1936; the engine's `neoteletext_input::keys::code`), written in JSON by its name, the schema's `KeyName` (for example `Enter`, `ArrowLeft`, `F1`, `ColorF0Red`, `ShiftLeft`).
  - **a physical key** (kind 3): the key that carries the given character on a United States layout, whatever the active layout: the KEY event's `base` when it has one, else its `key` when that is a character (DOC-1937). A musical keyboard laid out on the letter rows uses this kind, so that it has the same shape on every layout.
- A key event matches a set when it matches any member. The same naming is used by a key-state value (RULE-24).
- **Reason and source.** DEC-6522 item 5 ("a named key, a character, or a set"); the input protocol already identifies keys these three ways, so nothing new is defined.
- **Verification.** Tests: on a French layout the physical key `q` matches the key that types `a`; `any` matches a modifier alone; a set of 17 is refused.

**RULE-11 [engine: neoteletext-rules]. `becomes` is an edge.**
- **Statement.** Each `becomes` rule MUST keep one bit, its condition's result at its previous evaluation, false when the page opens and whenever the rule is disabled. In step 5 an enabled `becomes` rule fires when its condition holds and that bit is false; the bit is then set to the condition's result. A condition that already holds at page tick 0 therefore fires at tick 0, and a rule enabled while its condition holds fires at the next tick. A disabled rule is not evaluated.
- **Reason and source.** DEC-6522 item 5 ("edge-triggered, false to true"). Firing at opening when true lets a page's meters and indicators agree with the state from the first tick.
- **Verification.** Tests: a level crossing a threshold fires once and not again while above; falling and rising fires again; the opening and enabling cases.

**RULE-12 [engine: neoteletext-rules]. Targets.**
- **Statement.** A target MUST be one of four kinds, written in the record as a kind byte and a 16-bit number:

| Kind | Name | Number | What it is |
|---|---|---|---|
| 0 | page | 0 | the whole page's picture |
| 1 | control | 1 to 32, or 0 for any control | a teletext control of the page beneath (the engine's REQ-INT-117; `neoteletext_core::controls`), numbered from 1 in the order the page declares them |
| 2 | object | 1 to 65,535, or 0 for any object | an animation object of the sub-page shown: a teletext sprite, a ReGIS numbered drawing or a NAPLPS object, by its number (animation.md) |
| 3 | rectangle | 0 to 15 | a rectangle the table declares (RULE-13) |

- Number 0 ("any") is allowed only in the triggers `press`, `release`, `enter`, `leave`, `move` and `wheel`; it fires once for each control or object concerned, and the event reported by `send` names which. Actions and collision conditions name one control, object or rectangle.
- **Inside** is decided thus. The page: always. A control: the pointer's cell is one of the control's cells. A ReGIS numbered drawing: the picture's pick record names that drawing at the pointer's pixel, or a drawing that has it as an ancestor (regis-v2.md, "Picking"); only detectable drawings are named. A teletext sprite or a NAPLPS object: it is shown and marked detectable, and the pointer's pixel is within its bounding rectangle (ANIM-13). A rectangle: the pointer's pixel is within it. One pointer event may be inside several targets, and every rule it matches fires, in rule order.
- A target that does not exist on the sub-page shown is never inside, reads as not shown, and actions on it do nothing and are counted.
- **Reason and source.** DEC-6522 item 5 ("Targets are integer object numbers within the page"); the kind byte keeps the three renderers' numbers and the controls' apart.
- **Verification.** Tests of each kind's inside rule, with a pointer on an edge pixel; `any` firing once per object with the object named in the send.

**RULE-13 [engine: neoteletext-rules]. Rectangles and the pixel grid.**
- **Statement.** A table MAY declare 0 to `MAX_RECTS` (16) rectangles, each `x`, `y`, `width`, `height` (each 0 to 65,535, width and height at least 1) in the pixels of the sub-page's picture, origin at the top left, x to the right, y down: a teletext page is 480 by 500 dots (a cell is 12 by 20, DOC-1938); a ReGIS picture 800 by 480; a NAPLPS picture 640 by 480. The pointer's pixel given to the evaluator is in the same grid. A rectangle that lies partly outside the picture is cut to it.
- **Reason and source.** DEC-6522 item 5 ("a screen rectangle"); the grids are those the browser already uses for each kind of page (the browser's REQ-6377 for ReGIS).
- **Verification.** Tests on each grid's last pixel.

**RULE-14 [engine: neoteletext-rules]. Page variables.**
- **Statement.** A table MAY declare 0 to `MAX_VARIABLES` (32) variables, numbered from 0 in the order declared. Each has `min`, `max` and `initial`, signed 32-bit integers with `min ≤ initial ≤ max`. A variable holds its initial value when the page opens. `set` writes a constant, held to the range (a value below `min` becomes `min`, above `max` becomes `max`); `add` adds a signed 32-bit constant with saturation at `min` and `max`, computed without overflow. Variables are local to the page in its view, are not kept when the page is closed, and are never shared between pages, tabs or channels.
- **Reason and source.** DEC-6522 items 6 and 7 ("a small set of numeric page variables", "held to its declared range").
- **Verification.** Tests: saturation at both ends, including `add` of the largest and smallest 32-bit constants; reset at each opening.

**RULE-15 [engine: neoteletext-rules]. Timers.**
- **Statement.** A table MAY declare 0 to `MAX_TIMERS` (8) timers, numbered 0 to 7, each with a flag saying whether it starts running when the page opens. A timer is either stopped or running since a start tick. `start_timer` in tick `t` makes it running since tick `t + 1` (RULE-6), replacing any earlier start; `stop_timer` stops it. A timer that starts at opening runs since page tick 0. The **page timer** (identifier 255 in the record, first in identifier order) always runs since page tick 0, cannot be started or stopped, and is not one of the 8. With `e` the page tick minus the start tick: an `after N` trigger is due when `e = N`; an `every N` trigger is due when `e > 0` and `e` is a multiple of `N`. A timer's value in a condition is 1 while running and 0 while stopped (RULE-25).
- **Reason and source.** DEC-6522 items 5 and 7 ("timers keyed by identifier: starting a running timer replaces it").
- **Verification.** Tests: `after 1` fires one tick after `start_timer`; restarting replaces; `every 30` on the page timer fires at ticks 30, 60, 90.

**RULE-16 [engine: neoteletext-rules]. Switching rules on and off.**
- **Statement.** `enable` and `disable` each name a set of rules of the same table (a 64-bit mask in the record, bit `n` for rule `n`). Their effect is seen from the next tick (RULE-6). A rule's effective state in a tick is: enabled in the snapshot, and not in the list of rules switched off for the sub-page shown (RULE-17).
- **Reason and source.** DEC-6522 items 5 and 7.
- **Verification.** Tests: a rule disabling itself; enabling a `becomes` rule whose condition holds.

**RULE-17 [engine: neoteletext-rules]. Rules switched off for a sub-page.**
- **Statement.** A table MAY carry 0 to `MAX_SUBPAGE_MASKS` (16) entries, each a sub-code (`0x0000` to `0x3F7E`) and a 64-bit mask of rules that are off while that sub-page is the one shown. A sub-code may appear once. Changing the sub-page shown changes nothing else: variables, timers and enabled flags are kept, and `open` does not fire again.
- **Reason and source.** DEC-6522 item 5 ("a sub-page may name rules of the table to switch off while it is shown").
- **Verification.** Test: a rule fires on sub-page 1 and not on sub-page 2, with its `becomes` bit cleared while off.

## 4. Conditions

**RULE-18 [engine: neoteletext-rules]. The condition expression.**
- **Statement.** A condition MUST be a tree of at most `MAX_CONDITION_NODES` (16) nodes, of which at most `MAX_CONDITION_TERMS` (8) are terms, with operators nested at most `MAX_CONDITION_DEPTH` (3) deep (a term directly under three operators is allowed; a fourth operator level is refused). The nodes:

| Code | Node | Meaning |
|---|---|---|
| 1 | `and` | 2 to 8 children; true when all are |
| 2 | `or` | 2 to 8 children; true when any is |
| 3 | `not` | 1 child; true when it is false |
| 4 | compare (term) | a value (section 6), one of `==` (1), `!=` (2), `<` (3), `<=` (4), `>` (5), `>=` (6), and a signed 32-bit constant |
| 5 | in range (term) | a value and constants `low ≤ high`; true when `low ≤ value ≤ high` |
| 6 | in set (term) | a value and 1 to 8 constants; true when the value equals one |
| 7 | `overlaps` (term) | two targets; true when their bounding rectangles share at least one pixel (RULE-19) |
| 8 | `inside` (term) | two targets; true when the first's bounding rectangle lies wholly within the second's (RULE-19) |

- Every value is a signed 32-bit integer and every comparison is of a value with a constant; two values are never compared with each other and nothing is computed from them. Evaluation of `and` and `or` MAY stop at the first child that settles it, since no node has an effect.
- **Reason and source.** DEC-6522 item 6; DEC-6524 item 9 for nodes 7 and 8.
- **Verification.** Tests of each node and operator at its boundaries; a ninth term, a 17th node and a fourth level are each refused whole.

**RULE-19 [engine: neoteletext-rules]. Collision and region tests are on bounding rectangles.**
- **Statement.** For `overlaps` and `inside`, each target's rectangle MUST be: a control's cells in dots; an animation object's bounding rectangle as its renderer reports it for the object's state in the snapshot (ANIM-13); a declared rectangle; the page's whole picture. A target that does not exist or is not shown has no rectangle, and a test that names it is false. `overlaps` and `inside` MUST name targets of kinds 1, 2 or 3 as the first operand and of kinds 0 to 3 as the second, and never "any".
- **Reason and source.** DEC-6524 item 9: "object A overlaps object B" and "object A is inside rectangle R", on bounding rectangles.
- **Verification.** Tests: rectangles that touch at an edge do not overlap; share one pixel, do; a hidden object overlaps nothing.

## 5. Actions

**RULE-20 [engine: neoteletext-rules]. The action kinds.**
- **Statement.** An action MUST be exactly one of the kinds below. A rule's actions run in written order; each is checked against its bounds when the table is decoded, never when it runs.

| Code | Name | Effect | Fields |
|---|---|---|---|
| 1 | `midi` | gives one MIDI channel voice message to the local sound playing on an audio channel (RULE-21) | audio channel 0 to 3; status; two data bytes |
| 2 | `play` | starts a sound the page already has on an audio channel, as the audio profile's play command does (REQ-AUD-010) | audio channel; handle 0 to 255; generation; gain 0 to 100; fade 0 to 10,000 ms; loop |
| 3 | `stop` | ramps an audio channel to silence and stops it | audio channel; fade |
| 4 | `gain` | ramps an audio channel to a gain | audio channel; gain; fade |
| 5 | `show` | makes a control or object shown (ANIM-6) | target |
| 6 | `hide` | makes it hidden | target |
| 7 | `look` | forces a look on a control or object: 0 normal (the pointer decides again), 1 hover, 2 pressed, 3 alternative (ANIM-6) | target; look |
| 8 | `set` | sets a variable to a constant (RULE-14) | variable; value |
| 9 | `add` | adds a constant to a variable with saturation | variable; amount |
| 10 | `start_timer` | starts or restarts a timer (RULE-15) | timer 0 to 7 |
| 11 | `stop_timer` | stops a timer | timer |
| 12 | `enable` | switches rules on (RULE-16) | rule mask |
| 13 | `disable` | switches rules off | rule mask |
| 14 | `send` | reports to the page's channel: the trigger's own event, or one value (RULE-22) | what; value |
| 15 | `move` | puts an object at a position, or moves it by an amount, in its renderer's units (ANIM-6) | target; relative; x; y (signed 16-bit) |
| 16 | `order` | sets an object's layer (0 to 3, or 255 to keep it) and its order within the layer (−128 to 127) (ANIM-12) | target; layer; order |
| 17 | `frame` | shows one frame of an object, 0 to 15 (ANIM-14), and stops any cycle | target; frame |
| 18 | `cycle` | starts cycling an object's frames from `first` to `last`, one frame each `period` ticks (1 to 3,600), looping or once (ANIM-14) | target; first; last; period; once |
| 19 | `stop_cycle` | stops the cycle at the frame shown | target |

- Kinds 1 to 14 are DEC-6522 item 7's. Kinds 15 to 19 are the actions on animation objects that DEC-6524 item 9 and the task of 18 November 2026 call for.
- An action whose target, sound, variable or timer does not exist when it runs does nothing and is counted in the page's `skipped` figure (RULE-72); it is never an error that stops the rule.
- **Reason and source.** DEC-6522 item 7; DEC-6524 items 5 to 10.
- **Verification.** A test of each action's effect and of each field at and beyond its bounds.

**RULE-21 [engine: neoteletext-rules; neoteletext-browser]. The `midi` action.**
- **Statement.** A `midi` action MUST carry one complete MIDI 1.0 channel voice message with no running status: note off (`0x8n`), note on (`0x9n`), control change (`0xBn`), program change (`0xCn`, whose second data byte is 0 in the record and is not given to the instrument) or pitch bend (`0xEn`), where `n` is the part's MIDI channel less one, and each data byte is 0 to 127 (MIDI 1.0 Detailed Specification, "Channel Voice Messages"). Polyphonic key pressure, channel pressure, system exclusive, system common and system real-time messages MUST be refused when the table is decoded. The message is given to the local sound (RULE-60) playing on the named audio channel of the page's view; when no local sound plays there, the action does nothing and is counted. It is never given to a sound whose blocks the server sends, whose timeline the server owns.
- **Reason and source.** DEC-6522 item 7 ("a standard MIDI message to a playing synthesizer sound: note on and off, control change, program change, pitch bend"). Limiting it to local sounds keeps one writer for each instrument.
- **Verification.** Codec tests for each status; a system exclusive status refused; a browser test that a `midi` action reaches only a local sound.

**RULE-22 [engine: neoteletext-rules]. `send` and `echo`.**
- **Statement.** `send` with `what` 0 MUST report that the rule fired together with the trigger's own event: for an input trigger the input event exactly as the viewer made it (and, for a pointer trigger, the target it was inside); for `open`, `close`, `becomes`, `every` and `after`, no event, only that the rule fired. `send` with `what` 1 MUST report the rule and one named value as the snapshot holds it. A rule's `echo` flag is exactly a `send` with `what` 0 added after its last action. A rule MAY hold several `send` actions; each makes one report. What leaves the receiver for a report, and its limits, are RULE-46 and RULE-52.
- **Reason and source.** DEC-6522 items 7 and 8.
- **Verification.** Tests: the reports of a rule with two sends and `echo`, in order.

## 6. The values a condition can read

Every value is a signed 32-bit integer. A value is named in the record by 8 bytes: a space byte, a byte `a` and three 16-bit fields `b`, `c`, `d` (RULE-44). A value that cannot be read (no such variable index is impossible after decoding; no sound on the channel; another family's sound; a property the family does not have) reads as 0, and a property `playing` or `shown` exists in each space to tell "0" from "absent".

**RULE-23 [engine: neoteletext-rules]. Space 1: page variables.**
- **Statement.** `a` is the variable's number, 0 to 31; `b`, `c`, `d` are 0. The value is the variable's value in the snapshot.
- **Verification.** Covered by RULE-14's tests.

**RULE-24 [engine: neoteletext-rules]. Space 2: key and pointer state.**
- **Statement.** `a` is the kind: 1 a character key, 2 a named key, 3 a physical key (RULE-10), with the key's 32-bit code in `b` (high half) and `c` (low half): the value is 1 while that key is down, else 0. Kind 4 is a pointer button, `b` the button 0 to 2: 1 while down over the page. Kind 5 is the pointer: `b` 0 gives 1 while the pointer is over the page, `b` 1 its x pixel and `b` 2 its y pixel (0 while it is not over the page). Kind 6 is the count of keys down, 0 to 16. These read the input state (RULE-8).
- **Reason and source.** DEC-6522 item 6 ("key states").
- **Verification.** Tests with the events of RULE-8.

**RULE-25 [engine: neoteletext-rules]. Space 3: timers.**
- **Statement.** `a` is the timer, 0 to 7 or 255 for the page timer; `b` is the property: 0 running (1 or 0), 1 elapsed ticks since its start (0 while stopped; at most 2,147,483,647).
- **Verification.** Covered by RULE-15's tests.

**RULE-26 [engine: neoteletext-rules]. Space 4: target state.**
- **Statement.** `a` is the target's kind (1 control, 2 object), `b` its number, `c` the property: 0 exists (1 or 0), 1 shown, 2 frame (0 to 15), 3 x and 4 y (the object's position in its renderer's units, ANIM-6; a control's first column and row), 5 the look in force (0 to 3), 6 layer, 7 order, 8 cycling (1 or 0), 9 pointer inside (1 or 0). All are read from the snapshot except 9, which is input state.
- **Reason and source.** DEC-6522 item 8 names these as local state; the task of 18 November 2026 asks for "object states (shown, frame, position)".
- **Verification.** Tests after each animation action, one tick later.

**RULE-27 [engine: neoteletext-rules; neoteletext-browser]. Space 5: a sound on an audio channel.**
- **Statement.** `a` is the audio channel, 0 to 3; `b` the property:

| `b` | Name | Value |
|---|---|---|
| 0 | `playing` | 1 while any sound plays on the channel in this view, else 0 |
| 1 | `level` | the channel's output level over the last tick, 0 to 255 (RULE-32) |
| 2 | `handle` | the handle, 0 to 255, of the sound playing; −1 when none |
| 3 | `gain` | the channel's gain as last commanded, 0 to 100 |
| 4 | `local` | 1 while the sound playing is a local sound (RULE-60), else 0 |

- A sound is addressed as the program protocol addresses a playing sound: by the audio channel it plays on (the `channel` of `play`, `stop` and `gain`), and it is told apart by its handle (the `handle` of `sound` and `play`). The rule table has no other name for a sound.
- **Reason and source.** DEC-6522 items 4 and 6.
- **Verification.** Browser tests with a scripted sound helper: each property after `play`, `gain` and `stop`.

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
- **Verification.** For each family, a test in `neoteletext-audio-instruments` reads every parameter of appendix A after setting it by its control message; browser tests of `note`, `notes` and `program` after rule `midi` actions.

**RULE-29 [engine: neoteletext-audio-instruments]. Each family publishes one parameter table.**
- **Statement.** Each family's interface module (`synth7/interface.rs` and the others, built by the feature `interface` alone) MUST publish a constant table `PARAMETERS` of its readable patch fields in the order of appendix A — each entry a name, a least and a greatest value — and a function that reads a field's present value for a part from the family's tracker (the state a sender tracks, MIDI-94). The parameter number is the entry's place in the table, from 0. The table's names, order and ranges MUST be those of the program protocol's `Synth7Parameter`, `Synth106Parameter`, `Synth60Parameter`, `SynthDParameter`, `Synth53Parameter`, `Synth8Parameter` and `Synth80Parameter` types of the server's schema, variant by variant in schema order, which a test of the server asserts; a field whose schema type is an enumeration reads as the ordinal of its value in schema order from 0, and a boolean as 0 or 1. A parameter number is never reused or reordered; new fields are added at the end.
- **Reason and source.** One table serves the server (which turns a field's name into its number and refuses an unknown one) and the receiver (which reads it); DEC-6462.
- **Verification.** The server's test that schema and tables agree; a test that appendix A of this document is the tables' printout (the engine's `cargo xtask` prints it and the commit gate compares).

**RULE-30 [neoteletext-browser]. Where each synthesizer value is read.**
- **Statement.** The decoder MUST read classes 0 to 4, 8 and 9 from the family's tracker that it keeps for the sound: for a local sound, a tracker fed with the sound's setup events (RULE-60) and then with every `midi` action in order, so no question is put to the sound helper; for a sound whose blocks the server sends, the tracker of the instrument the decoder renders it with, at the position rendered, which is ahead of what is heard by up to the stream's buffer (`STREAM_TARGET_MS`, 400 milliseconds) and is approximate by that much. Classes 5 to 7 of a local sound are metered by the sound helper (RULE-33); of a server-timed sound they are read from the decoder's instrument at the position rendered.
- **Reason and source.** DEC-6522 item 4: the owner accepted that reading may "cost CPU and be approximate". Tracking in the decoder costs nothing per tick and needs no message.
- **Verification.** Browser tests: `note[60]` reads 1 in the tick after a rule's note on with no helper message exchanged.

**RULE-31 [engine: neoteletext-audio-instruments]. Envelope position.**
- **Statement.** The trait `Instrument` MUST gain a method `meter(&self, part: u8) -> Meter`, with a default that answers idle and zero, giving for the part's most recently started voice that is not idle (else idle): the stage 0 to 4 of RULE-28, the amplitude envelope's present value scaled linearly to 0 to 255 of the envelope's full scale, and the count of voices not idle. The amplitude envelope is: synth106, synth60, synth53, synth52, synth51, synth8 and synthD, the voice's loudness (VCA) envelope; synth80, channel I's amplifier envelope of the voice; synth7, the envelope generator of operator 1 of the newest note, operator 1 being a carrier in all 32 algorithms; the synth6581 family, the envelope generator of the voice named as the part, its 8-bit counter as it stands. Stages a family does not have are never reported (synth7's four rates map to attack for the first, decay for the second and third while a key is down, sustain when level 3 is reached, release after key off).
- **Reason and source.** DEC-6522 items 4 and 6 ("a voice's envelope position").
- **Verification.** For each family a test: after a note on, the stage passes 1, 2, 3 in order and 4 after note off, and the level is 0 when idle.

**RULE-32 [engine: neoteletext-audio-mix; neoteletext-browser]. `level`.**
- **Statement.** The sound helper MUST meter, for each watched audio channel of each watched view, the largest absolute sample value of that channel's voice after its gain, ramp and ducking and before the master volume and the mute, over the output frames it rendered since its last report, and report `level = min(255, peak ÷ 128)` where peak is on the 16-bit scale 0 to 32,768. The scale is linear: 255 is full scale, 128 is −6 decibels, 64 is −12, 32 is −18, 16 is −24, 8 is −30, 4 is −36. The engine mixer (`neoteletext-audio-mix`) MUST provide the per-voice peak since last asked; nothing is metered for a channel no rule watches.
- **Reason and source.** DEC-6522 item 4: "we only need to capture state 1/60th of a second and only on what the commands say they want to watch". Before the master volume and mute, so that a page's meters show what the page plays, and so that a rule cannot learn the viewer's volume setting.
- **Verification.** A mixer test with a sine at each of the listed levels; a browser test that an unwatched channel costs no meter call.

**RULE-33 [neoteletext-browser]. The message flow of metering.**
- **Statement.** Metering MUST work through these messages and no others:
  1. When the decoder has decoded a table for a page that is shown, it sends the trusted core a **watch list** with the page's key: at most `MAX_WATCHED` (32) slots, each an audio channel (0 to 3) and a kind (1 `level`; 2 `envelope_stage`, 3 `envelope_level`, 4 `voices`, each with a part 0 to 15) — exactly the distinct metered values the table's conditions and `send` actions name. A page with none sends none. When the page stops being shown, or its table is removed, the decoder sends an empty list.
  2. The trusted core checks the list's bounds and that the page is shown in that view, and passes it to the sound helper tagged with the view's channel number, replacing that view's earlier list (`ToSound::Watch`).
  3. The sound helper, after rendering each device buffer, when at least one sixtieth of a second of output frames has been rendered since its last report and a list is in force, sends one report for each view with a list: the slots' values in the list's order, each one byte (`FromSound::Metered`). While the output device is stopped it sends one report of zeros and then none.
  4. The trusted core checks the report's length against the list it passed and gives it to that view's decoder (`ToDecoder::Metered`).
  5. The decoder keeps the newest report; step 1 of each tick (RULE-5) copies it into the snapshot. A slot not yet reported reads 0.
- The sound helper is never told a condition, a threshold or a rule; it meters and reports. Reports follow the audio device's clock, so a value in a snapshot is up to one report's interval (a sixtieth of a second and one device buffer) and one tick old. Steps 3 to 5 of a tick whose snapshot was taken on an arrival read the newest report at the tick (RULE-7).
- **Reason and source.** DEC-6522 item 4. The trusted core stays the only path between helpers (the browser's architecture, section 6.2).
- **Verification.** Tests with the scripted helper: the list sent for a table of three watched values; a report of the wrong length dropped by the core; no report while no list is in force; the level seen by a `becomes` rule within two ticks of the helper's report.

## 7. The program protocol: version 14

The program protocol is the line-by-line JSON a channel's program exchanges with the server (the server's `crates/teletext-runtime/src/protocol.rs`; its generated schema is the contract, DEC-6462). It is at version 13 today (`PROTOCOL: u32 = 13`, `protocol/schema-13.json`). This document and animation.md make version 14. The conventions are version 13's: every message is one object with a `type`; names are snake_case; a page is a string of three hexadecimal digits (`PageNumber`) and a sub-code a string of four (`SubCode`); an audience is `"all"` or a list of connection numbers (`Connections`); unknown fields are refused; what the schema cannot say is checked by `protocol/check.rs` and answered by a typed `refused`.

**RULE-34 [neoteletext-app-server]. Protocol 14.**
- **Statement.** The server MUST raise `PROTOCOL` to 14 and generate `protocol/schema-14.json` from its Rust types, deleting `schema-13.json` in the same change; its `start` message says `"protocol": 14`. It MUST add the program messages `rules` and `query_state` and the server messages `rule_event`, `page_state` and `rules_fault` of this section, the fields `rule`, `tick` and `target` of `input` (RULE-37), the local sound kinds of RULE-61, and the messages animation.md defines (`animate`, `sprites`, `naplps_objects`, `sprite_sheet`, `frame`). A program that speaks another version is refused as today. Both kits take the schema by copy pinned to the server's commit, as they take version 13's.
- **Reason and source.** DEC-6522 item 9; DEC-6462.
- **Verification.** The server's schema test (the committed schema is the generated one); both kits' pin checks.

**RULE-35 [neoteletext-app-server]. The `rules` message.**
- **Statement.** A program gives a page its table with:

```json
{"type":"rules","connections":"all","page":"101","table":{
  "variables":[{"name":"octave","min":0,"max":8,"initial":4}],
  "timers":[{"name":"beat","running":false}],
  "rects":[{"name":"pad","x":40,"y":300,"width":200,"height":100}],
  "rules":[{"name":"c_down","on":{"event":"key","keys":[{"physical":"a"}]},
            "when":null,"do":[{"action":"midi","channel":0,
            "message":{"event":"note_on","channel":1,"key":60,"velocity":100}}],
            "echo":false,"enabled":true}],
  "subpages":[{"sub":"0002","off":["c_down"]}]}}
```

- `table` is the table, or `null`, which removes the page's table for those connections (and, where the channel's default applies, RULE-53, puts the default back). In a table, `rules` is required (0 to 64 entries); `variables` (at most 32), `timers` (at most 8), `rects` (at most 16) and `subpages` (at most 16) default to empty. In a rule, `name`, `on` and `do` are required; `when` defaults to `null` (no condition), `echo` to `false`, `enabled` to `true`.
- **`on`**, the trigger, is an object tagged by `event`:

| `event` | Other fields |
|---|---|
| `key` | `keys` (a key set); `repeat` (boolean, default `false`); `mods` (`{"mask":0..255,"value":0..255}`, default both 0) |
| `key_up` | `keys`; `mods` |
| `press`, `release` | `target`; `button` (0, 1, 2 or `"any"`, default `"any"`) |
| `enter`, `leave`, `wheel` | `target` |
| `move` | `target`; `held` (boolean, default `false`) |
| `open`, `close`, `text`, `focus`, `blur` | none |
| `becomes` | `condition` (required; the rule's `when` MUST be `null`) |
| `every`, `after` | `ticks` (1 to 216,000); `timer` (a timer's name, or `null` for the page timer, the default) |

- A **key set** is `"any"` or a list of 1 to 16 keys, each `{"char":"a"}` (one Unicode scalar value, a letter in lower case), `{"name":"Enter"}` (a `KeyName` of the schema) or `{"physical":"a"}` (RULE-10).
- A **target** is `"page"`, `{"control":n}`, `{"object":n}`, `{"rect":"name"}`, or in the six pointer triggers `{"control":"any"}` or `{"object":"any"}` (RULE-12).
- **`when`** and `condition` are a condition: `{"and":[c, ...]}`, `{"or":[c, ...]}`, `{"not":c}`, `{"read":v,"op":"==","value":n}` with `op` one of `==`, `!=`, `<`, `<=`, `>`, `>=`, `{"read":v,"in_range":[low,high]}`, `{"read":v,"in_set":[n, ...]}`, `{"overlaps":[t,t]}` or `{"inside":[t,t]}` (RULE-18).
- A **value** `v` is an object tagged by `of`:

| `of` | Other fields | Space |
|---|---|---|
| `variable` | `name` | 1 |
| `key` | `key` (one key, as in a key set) | 2 |
| `button` | `button` (0 to 2) | 2 |
| `pointer` | `property`: `over`, `x`, `y` | 2 |
| `keys_down` | none | 2 |
| `timer` | `name` (a timer's name, or `null` for the page timer); `property`: `running`, `elapsed` | 3 |
| `target` | `target`; `property`: `exists`, `shown`, `frame`, `x`, `y`, `look`, `layer`, `order`, `cycling`, `inside` | 4 |
| `sound` | `channel` (0 to 3); `property`: `playing`, `level`, `handle`, `gain`, `local` | 5 |
| `synth` | `channel` (0 to 3); `family` (`synth6581`, `synth8580`, `synth7`, `synth106`, `synth60`, `synthd`, `synth53`, `synth52`, `synth51`, `synth8`, `synth80`); `part` (1 to 16; for the synth6581 family the voice, 1 to 3); `property`: `program`, `notes`, `note`, `velocity`, `field`, `envelope_stage`, `envelope_level`, `voices`, `controller`, `bend`; and with `note` or `velocity` a `key` (0 to 127), with `field` a `field` (a name of appendix A for the family), with `controller` a `controller` (0 to 127) | 6 |

- **`do`** is a list of 0 to 16 actions, each tagged by `action`:

| `action` | Other fields |
|---|---|
| `midi` | `channel` (the audio channel, 0 to 3); `message`: one of `{"event":"note_on","channel":1..16,"key":0..127,"velocity":0..127}`, `{"event":"note_off", ...}` with the same fields, `{"event":"control_change","channel","controller":0..127,"value":0..127}`, `{"event":"program_change","channel","program":0..127}`, `{"event":"pitch_bend","channel","value":0..16383}` — the schema's event shapes for a family without `time_us` |
| `play` | `channel`; `handle` (0 to 255); `generation` (0 to 65,535); `gain` (0 to 100); `fade_ms` (0 to 10,000); `loop` (boolean) |
| `stop` | `channel`; `fade_ms` |
| `gain` | `channel`; `gain`; `fade_ms` |
| `show`, `hide`, `stop_cycle` | `target` (a control or an object) |
| `look` | `target`; `look`: `normal`, `hover`, `pressed`, `alternative` |
| `set` | `variable` (a name); `value` |
| `add` | `variable`; `amount` |
| `start_timer`, `stop_timer` | `timer` (a name) |
| `enable`, `disable` | `rules` (a list of 1 to 64 rule names) |
| `send` | `value` (a value, or `null` for the trigger's own event, the default) |
| `move` | `target` (an object); `x`, `y` (−32,768 to 32,767); `relative` (boolean, default `false`) |
| `order` | `target`; `layer` (0 to 3, or `null` to keep it); `order` (−128 to 127) |
| `frame` | `target`; `frame` (0 to 15) |
| `cycle` | `target`; `first`, `last` (0 to 15, `first ≤ last`); `period` (1 to 3,600 ticks); `once` (boolean, default `false`) |

- **Reason and source.** DEC-6522 item 9; DEC-6462 (the server is where the meaning lives; the kits send this shape and hold no logic).
- **Verification.** The server's protocol tests accept each worked example of section 7.5 and refuse each fault of RULE-39 with the stated rule and path.

**RULE-36 [neoteletext-app-server]. Names exist only between a program and the server.**
- **Statement.** Rule, variable, timer and rectangle names MUST match `[a-z][a-z0-9_]{0,31}` and be distinct within their kind in a table; `page` is not allowed as a timer's or a rectangle's name. The server turns each name into its number (its place in the table's list, from 0) when it encodes the record, and turns numbers back into names in every message it gives the program. No name is sent to a receiver.
- **Reason and source.** A program's author reads names; the record carries numbers so that the receiver parses no text (DEC-6522 item 9).
- **Verification.** Server tests: a duplicate and an unknown name refused; an event's rule number reported by its name.

**RULE-37 [neoteletext-app-server]. What `send` and `echo` give the program.**
- **Statement.** When a receiver reports a rule's firing (RULE-46), the server MUST give the program, for the connection it came from:
  - for an input trigger, the `input` message of version 13 unchanged in its `event` shape (`key`, `mouse`, `wheel`, `touch`, `pick`, `hover`, `drawing_hover`, `text`, `compose`, `paste`, `focus`, `blur`), with three added fields: `rule`, the name of the rule that sent it; `tick`, the page tick at which it fired; and `target`, the target the pointer was inside for a pointer trigger whose rule named a control, an object or a rectangle, else `null`. A pointer event on a page drawn by the ReGIS renderer is followed, as in version 13, by the `input` message of its `pick`, with the same `rule` and `tick`.

    ```json
    {"type":"input","connection":7,"page":"101","sub":"0001","lost":false,"rule":"keys","tick":412,"target":null,
     "event":{"kind":"key","action":"press","key":"a","base":null,"mods":0,"text":"a"}}
    ```
  - for `open`, `close`, `becomes`, `every` and `after`, and for a `send` of a value, the new message `rule_event`:

    ```json
    {"type":"rule_event","connection":7,"page":"101","sub":"0001","rule":"hot","tick":9031,"event":{"kind":"fired"}}
    {"type":"rule_event","connection":7,"page":"101","sub":"0001","rule":"report","tick":9031,
     "event":{"kind":"value","read":{"of":"variable","name":"octave"},"value":5}}
    ```
- A program therefore receives an `input` message only for an event some rule of the page's table sent. Events arrive in the order the receiver sent them.
- **Reason and source.** DEC-6522 item 8 (a) and (b); keeping `input`'s shape means every program written for version 13 reads version 14's input without change.
- **Verification.** Server tests: each input kind carried in a RULE_EVENT gives the same `event` object version 13 gave for the bare event; the two `rule_event` shapes.

**RULE-38 [neoteletext-app-server]. The state query and its answer.**
- **Statement.** A program asks one connection for one page's local state with `{"type":"query_state","connection":7,"page":"101","request":42}`, where `request` is 1 to 4,294,967,295 and is the program's own number for the question. The server sends the connection a RULES_QUERY record (RULE-47) when that connection has the page selected, and otherwise refuses with `wrong_page`. It MUST refuse a second query for the same connection and page within one second with `too_frequent`. The receiver answers once (RULE-47) and the server gives the program:

```json
{"type":"page_state","connection":7,"page":"101","sub":"0001","request":42,"tick":9120,"table":true,
 "variables":{"octave":5},
 "timers":{"beat":{"running":true,"elapsed":18}},
 "enabled":["c_down","c_up","hot"],
 "targets":[{"target":{"object":301},"exists":true,"shown":true,"look":"normal","frame":0,"x":700,"y":380,"layer":2,"order":0,"cycling":false}],
 "values":[{"read":{"of":"sound","channel":0,"property":"level"},"value":41}]}
```

- `table` is `false`, and every list empty, when the page has no table in that view. `targets` holds every control and object the table names, in the order first named; `values` every distinct value the table's conditions and sends read, as the snapshot of the answering tick holds them. When no answer comes within 10 seconds, or the connection ends or leaves the page first, the server MUST give the program a `refused` message with the rule `not_answered` and the query's `request`, so that a missing answer is never mistaken for an empty state.
- **Reason and source.** DEC-6522 item 8 (c): for resynchronisation after a reconnect and for debugging, not a stream.
- **Verification.** Server tests: the answer's fields from a recorded PAGE_STATE; the rate refusal; the timeout refusal.

**RULE-39 [neoteletext-app-server]. Refusals.**
- **Statement.** A faulty `rules` or `query_state` message MUST be refused whole with the `refused` message of version 13 (`path`, `rule`, `detail`, `message`), and nothing of it sent to any receiver. Beside the existing rules (`unknown_field`, `missing_field`, `wrong_type`, `out_of_range`, `too_long`, `duplicate`, `not_in_index`, `unknown_connection`, `wrong_page`), the schema's `Rule` gains:

| `rule` | When |
|---|---|
| `rules_over_limit` | the table exceeds a limit of section 9 that the schema cannot state: more than 8 terms, 16 nodes or 3 levels in a condition; more than 64 distinct values or 64 distinct targets in the table; an encoded table over `MAX_TABLE_BYTES`. `detail` names the limit and its value |
| `invalid_rules` | a shape fault the schema cannot state: a rule with no actions and no `echo`; a `becomes` rule with a `when`; `first` above `last`; `low` above `high`; `min` above `max` or `initial` outside them; "any" where a single target is required; a `page` target in an action; a sub-code repeated in `subpages` |
| `unknown_name` | a rule, variable, timer or rectangle name that the table does not declare |
| `duplicate_name` | a name declared twice within its kind |
| `unknown_parameter` | a `field` that the named family's table (appendix A) does not have |
| `too_frequent` | a `query_state` within one second of the last for that connection and page |
| `not_answered` | a `query_state` that got no answer (RULE-38) |

- The server MUST also check every table with `neoteletext_rules::check` — the same code the receiver decodes with — after encoding it, and refuse with `invalid_rules` anything that code refuses, so that no receiver is ever sent a table it would refuse (RULE-59).
- **Reason and source.** DEC-6522 item 10: "refused whole, and the refusal is reported, never silently ignored"; the server's existing practice for ReGIS (`invalid_regis`).
- **Verification.** One server test for each row, asserting `rule` and `path`; the kits' `server-rules` tests hold the kits to the same refusals.

**RULE-40 [neoteletext-app-server]. The server keeps and sends tables per connection.**
- **Statement.** The server MUST keep, for each connection and page, the newest table the program gave an audience that includes the connection, at most `MAX_KEPT_TABLES` (64) pages a connection, the oldest dropped first. It MUST send a connection the page's RULES record (RULE-41): when the connection selects the page, before the page's own packets and records, so that the table is in place when the page opens; and at once when the program sends a new table, or removes it, while the connection has the page selected. Each record sent to a connection for a page carries a generation one above the last sent to that connection for that page, starting at 1 and passing from 65,535 to 1. A table is never sent to a connection that has another page selected.
- **Reason and source.** A viewer who joins late or reconnects needs the table as they need the page; one table per page per view (RULE-2).
- **Verification.** Server tests: selection sends the table first; a late joiner gets it; a replacement raises the generation.

### 7.5 Worked examples

Each is a complete `rules` message that the server accepts. The seventh, the music player's whole table, is in section 14.

**Example 1: a text field's keys are sent, and nothing else.** The page takes typed text, the Enter key and the Backspace key; a click, a move and the wheel are not sent.

```json
{"type":"rules","connections":"all","page":"120","table":{"rules":[
  {"name":"typed","on":{"event":"key","keys":"any","repeat":true},"do":[{"action":"send"}]},
  {"name":"composed","on":{"event":"text"},"do":[{"action":"send"}]}]}}
```

**Example 2: a button that lights at once and tells the channel.** Control 3 takes its pressed look locally while it is held; the release is echoed.

```json
{"type":"rules","connections":"all","page":"130","table":{"rules":[
  {"name":"vote_down","on":{"event":"press","target":{"control":3},"button":0},"do":[{"action":"look","target":{"control":3},"look":"pressed"}]},
  {"name":"vote","on":{"event":"release","target":{"control":3},"button":0},"do":[{"action":"look","target":{"control":3},"look":"normal"}],"echo":true}]}}
```

**Example 3: a counter held to a range, reported when it changes.** The arrow keys change `volume` between 0 and 10; the channel is told the new value one tick later, when the `becomes`-free report rule's timer fires.

```json
{"type":"rules","connections":"all","page":"140","table":{
 "variables":[{"name":"volume","min":0,"max":10,"initial":5}],
 "timers":[{"name":"report","running":false}],
 "rules":[
  {"name":"up","on":{"event":"key","keys":[{"name":"ArrowUp"}],"repeat":true},"do":[{"action":"add","variable":"volume","amount":1},{"action":"start_timer","timer":"report"}]},
  {"name":"down","on":{"event":"key","keys":[{"name":"ArrowDown"}],"repeat":true},"do":[{"action":"add","variable":"volume","amount":-1},{"action":"start_timer","timer":"report"}]},
  {"name":"tell","on":{"event":"after","ticks":1,"timer":"report"},"do":[{"action":"send","value":{"of":"variable","name":"volume"}}]}]}}
```

**Example 4: a sprite that walks with the arrow keys, and a collision.** Object 10 moves 8 pixels a press while the key repeats; when it overlaps object 20 a sound plays and the channel is told.

```json
{"type":"rules","connections":"all","page":"150","table":{"rules":[
  {"name":"left","on":{"event":"key","keys":[{"name":"ArrowLeft"}],"repeat":true},"do":[{"action":"move","target":{"object":10},"x":-8,"y":0,"relative":true}]},
  {"name":"right","on":{"event":"key","keys":[{"name":"ArrowRight"}],"repeat":true},"do":[{"action":"move","target":{"object":10},"x":8,"y":0,"relative":true}]},
  {"name":"hit","on":{"event":"becomes","condition":{"overlaps":[{"object":10},{"object":20}]}},
   "do":[{"action":"play","channel":1,"handle":5,"generation":1,"gain":100,"fade_ms":5,"loop":false},{"action":"hide","target":{"object":20}}],"echo":true}]}}
```

**Example 5: a blinking prompt and a timeout.** Object 7 cycles two frames every 30 ticks from opening; after ten seconds without a key the channel is told once.

```json
{"type":"rules","connections":"all","page":"160","table":{
 "timers":[{"name":"idle","running":true}],
 "rules":[
  {"name":"blink","on":{"event":"open"},"do":[{"action":"cycle","target":{"object":7},"first":0,"last":1,"period":30,"once":false}]},
  {"name":"awake","on":{"event":"key","keys":"any"},"do":[{"action":"start_timer","timer":"idle"}]},
  {"name":"asleep","on":{"event":"after","ticks":600,"timer":"idle"},"do":[{"action":"send"}]}]}}
```

**Example 6: a synthesizer's own state drives the picture.** While any note is down on part 1 of the synth106 sound on audio channel 0, object 50 is shown; when the filter's cutoff field passes 100 the alternative look is forced on object 51; a sub-page with the help text switches the note rules off.

```json
{"type":"rules","connections":"all","page":"170","table":{"rules":[
  {"name":"gate_on","on":{"event":"becomes","condition":{"read":{"of":"synth","channel":0,"family":"synth106","part":1,"property":"notes"},"op":">","value":0}},"do":[{"action":"show","target":{"object":50}}]},
  {"name":"gate_off","on":{"event":"becomes","condition":{"read":{"of":"synth","channel":0,"family":"synth106","part":1,"property":"notes"},"op":"==","value":0}},"do":[{"action":"hide","target":{"object":50}}]},
  {"name":"bright","on":{"event":"becomes","condition":{"read":{"of":"synth","channel":0,"family":"synth106","part":1,"property":"field","field":"vcf_frequency"},"op":">","value":100}},"do":[{"action":"look","target":{"object":51},"look":"alternative"}]},
  {"name":"dull","on":{"event":"becomes","condition":{"read":{"of":"synth","channel":0,"family":"synth106","part":1,"property":"field","field":"vcf_frequency"},"op":"<=","value":100}},"do":[{"action":"look","target":{"object":51},"look":"normal"}]},
  {"name":"open_filter","on":{"event":"wheel","target":{"object":51}},"do":[{"action":"send"}]}],
 "subpages":[{"sub":"0002","off":["gate_on","gate_off"]}]}}
```

## 8. The records and the input messages: push protocol version 9

The server encodes each message for receivers as a record in the audio profile's record frame on data channel 12, packet 4/31 (the engine's REQ-AUD-003; DOC-1952): a header of version, type and a two-byte body length, the body, and a CRC-32, cut into as many fragments as it needs, the body at most 8,184 bytes (`MAX_FRAMED_BODY`). The types in use end at 20 (`STATE_KEEP_OFFER`); types 8 and 13 are retired or kept and are not taken. The browser's messages to the server are events of the input protocol (DOC-1931): the byte `0xFF`, a type, and for an extension type (`0x40` to `0x7F`) a varint length and a payload; the extension types in use end at `0x4A` (`STATE_OFFER`).

**RULE-41 [engine: neoteletext-web, neoteletext-rules]. The RULES record, type 21: header.**
- **Statement.** Record type 21, `RULES`, carries one page's table in one record. Its body:

| Bytes | Field | Values |
|---|---|---|
| 0–1 | page | `0x100` to `0x8FF` |
| 2–3 | generation | 1 to 65,535 (RULE-40); a receiver that holds a table for the page replaces it when the generation differs |
| 4 | format | 1 |
| 5 | flags | bit 0: a table follows. Clear: the page has no table, and the body ends at byte 11 with every count 0. Bits 1 to 7 are 0 |
| 6 | variables `V` | 0 to 32 |
| 7 | timers `T` | 0 to 8 |
| 8 | rectangles `R` | 0 to 16 |
| 9 | rules `N` | 0 to 64 |
| 10 | sub-page masks `S` | 0 to 16 |
| 11 | reserved | 0 |
| then | `V` variables, `T` timers, `R` rectangles, `N` rules, `S` sub-page masks, in that order (RULE-42 to RULE-45) | |

- The body ends exactly at the last sub-page mask. The whole body is at most `MAX_TABLE_BYTES` (8,184). The record is one of the channel's records, which the audio receiver leaves alone (`is_channel_type`).
- **Reason and source.** DEC-6522 item 9: decoded once into fixed arrays; one record so that a table is never half arrived.
- **Verification.** Codec tests; the wire vectors of RULE-85.

**RULE-42 [engine: neoteletext-rules]. Declarations.**
- **Statement.** A variable is 12 bytes: `min`, `max`, `initial`, each a signed 32-bit integer. A timer is 1 byte: bit 0 set when it runs from opening, bits 1 to 7 zero. A rectangle is 8 bytes: `x`, `y`, `width`, `height`, each unsigned 16-bit, width and height at least 1. A sub-page mask is 10 bytes: the sub-code (2 bytes, `0x0000` to `0x3F7E`, no bit outside the thirteen a sub-code has) and a 64-bit mask whose bit `n` (bit 0 the least significant) switches rule `n` off; a bit at or above `N` MUST be 0.
- **Verification.** Codec tests of each bound.

**RULE-43 [engine: neoteletext-rules]. A rule and its trigger.**
- **Statement.** A rule is: a flags byte (bit 0 enabled at opening, bit 1 `echo`, bits 2 to 7 zero); the trigger's kind byte (the codes of RULE-9); the trigger's body; the condition (RULE-44); a count byte of actions, 0 to 16; the actions (RULE-45). The trigger bodies:

| Kinds | Body |
|---|---|
| 1 `key`, 2 `key_up` | flags (bit 0 `repeat`, kind 1 only; other bits 0); modifier mask; modifier value; key count `K`, 0 for any key, else 1 to 16; `K` keys of 5 bytes each: kind (1 character, 2 named, 3 physical) and a 32-bit code (a Unicode scalar value for kinds 1 and 3; a functional code that names a key, `neoteletext_input::keys::is_code`, for kind 2) |
| 3 `press`, 4 `release` | target (3 bytes: kind, 16-bit number); button (0, 1, 2 or 255) |
| 5 `enter`, 6 `leave`, 14 `wheel` | target |
| 13 `move` | target; flags (bit 0 `held`; other bits 0) |
| 7 `open`, 8 `close`, 9 `becomes`, 12 `text`, 15 `focus`, 16 `blur` | empty |
| 10 `every`, 11 `after` | timer (0 to `T − 1`, or 255); ticks (unsigned 32-bit, 1 to 216,000) |

- A `becomes` rule's condition MUST have at least one node. In a trigger a target's kind is 0 to 3; kind 0 has number 0; kind 3's number is below `R`.
- **Verification.** Codec tests; every reserved bit set is refused.

**RULE-44 [engine: neoteletext-rules]. Values and conditions.**
- **Statement.** A value is 8 bytes: space (1 to 6), `a`, and `b`, `c`, `d` (unsigned 16-bit), with the meanings of RULE-23 to RULE-28; every unused field MUST be 0, and each field is checked against its space's ranges when decoded (a variable below `V`, a timer below `T` or 255, an audio channel 0 to 3, a part 0 to 15, a class 0 to 9, a key 0 to 127, a parameter number 0 to 255, a family code 12 to 18, a variant 0 to 2).
- A condition is a count byte of nodes, 0 (no condition) to 16, then the nodes in prefix order (a node, then each of its children in order). Each node is its code byte (RULE-18) and:

| Node | Body |
|---|---|
| 1 `and`, 2 `or` | child count, 2 to 8 |
| 3 `not` | nothing; one child follows |
| 4 compare | value (8 bytes); operator (1 to 6); constant (signed 32-bit) |
| 5 in range | value; `low`; `high` (signed 32-bit, `low ≤ high`) |
| 6 in set | value; count 1 to 8; that many signed 32-bit constants |
| 7 `overlaps`, 8 `inside` | two targets (3 bytes each) |

- The nodes MUST form exactly one tree that uses every node counted, and meet RULE-18's limits.
- **Verification.** Codec tests: trees at each limit; a count that leaves nodes over, or runs short, refused.

**RULE-45 [engine: neoteletext-rules]. Actions.**
- **Statement.** An action is its code byte (RULE-20) and:

| Action | Body |
|---|---|
| 1 `midi` | audio channel; status; data 1; data 2 (RULE-21) |
| 2 `play` | audio channel; handle; generation (16-bit); gain; fade (16-bit, milliseconds); flags (bit 0 loop) |
| 3 `stop` | audio channel; fade |
| 4 `gain` | audio channel; gain; fade |
| 5 `show`, 6 `hide`, 19 `stop_cycle` | target (kind 1 or 2, number not 0) |
| 7 `look` | target; look (0 to 3) |
| 8 `set`, 9 `add` | variable; signed 32-bit constant |
| 10 `start_timer`, 11 `stop_timer` | timer (0 to `T − 1`) |
| 12 `enable`, 13 `disable` | 64-bit rule mask, no bit at or above `N` |
| 14 `send` | what (0 or 1); value (8 bytes, all zero when what is 0) |
| 15 `move` | target (kind 2); flags (bit 0 relative); x; y (signed 16-bit) |
| 16 `order` | target (kind 2); layer (0 to 3, or 255); order (signed 8-bit) |
| 17 `frame` | target (kind 2); frame (0 to 15) |
| 18 `cycle` | target (kind 2); first; last; period (16-bit, 1 to 3,600); flags (bit 0 once) |

- A fade below the audio profile's least (`MIN_FADE_MS`, 5) is played as the least. The bodies of actions 5 to 7 and 15 to 19 are the same bytes as the ANIMATE record's operations (ANIM-6), read by one function.
- **Verification.** Codec tests of each action and bound.

**RULE-46 [engine: neoteletext-input]. The RULE_EVENT message, extension type `0x4B`.**
- **Statement.** A receiver reports a rule's `send` or `echo` with the input event of extension type `0x4B`, whose payload is:

| Field | Form |
|---|---|
| stamp | the page and sub-code on screen, as every stamped event has them (DOC-1934) |
| generation | 16-bit: the table's |
| rule | 1 byte, 0 to 63 |
| tick | unsigned 32-bit: the page tick at which the rule fired |
| kind | 1 byte: 0 fired (no event), 1 input, 2 value |
| target | 3 bytes: the kind and number of the control, object or rectangle the pointer was inside for a rule whose pointer trigger named one; else all zero |
| body | kind 0: nothing. Kind 1: one or two whole input events exactly as push protocol 8 encoded them, each from its `0xFF`: KEY, MOUSE, WHEEL, TOUCH, PASTE, COMPOSE, FOCUS_IN, FOCUS_OUT, HOVER or DRAWING_HOVER; and after a MOUSE, TOUCH or WHEEL on a page drawn by the ReGIS renderer, its PICK. In place of an event the body may be one run of raw text (UTF-8, which never begins with `0xFF`; DOC-1781), for text that came from no key. Kind 2: a value (8 bytes) and its reading (signed 32-bit) |

- Under push protocol 9 the events KEY, MOUSE, WHEEL, PASTE, COMPOSE, TOUCH, FOCUS_IN, FOCUS_OUT, HOVER, PICK, DRAWING_HOVER and raw text MUST appear only inside a RULE_EVENT. A server MUST treat one at the top level of the stream as a protocol fault and close the connection, and a receiver MUST never write one there. HELLO, RESIZE, SELECT, RESUME and viewer state's three messages stay at the top level: they are the session, not the viewer's input to a page. A RULE_EVENT counts as one message for acknowledgement and resending (DOC-1923).
- An `enter` or `leave` on a control is carried as HOVER; on a ReGIS drawing as DRAWING_HOVER; on a teletext sprite, a NAPLPS object or a rectangle as the MOUSE move that caused it, with the target named.
- **Reason and source.** REQ-6523; DEC-6522 items 7 and 8. Wrapping the existing events means the server's existing readers and the programs' existing `input` handling are reused whole.
- **Verification.** Engine tests: each kind round-trips; a bare KEY at top level under version 9 is a fault; the wire vectors.

**RULE-47 [engine: neoteletext-web, neoteletext-input]. RULES_QUERY, record type 22, and PAGE_STATE, extension type `0x4C`.**
- **Statement.** Record type 22, `RULES_QUERY`, has a body of 6 bytes: the page (2 bytes) and the query's identifier (unsigned 32-bit, which the server chooses and maps to the program's `request`). A receiver that has that page open answers exactly once with the input event of extension type `0x4C`, `PAGE_STATE`, at the end of the next tick, and ignores a query for a page that is not open; it answers at most one query a second for a page and drops the rest, reporting fault 6 (RULE-48). The payload:

| Field | Form |
|---|---|
| stamp | page and sub-code |
| identifier | unsigned 32-bit, the query's |
| generation | 16-bit, the table's; 0 when the page has no table, and then nothing follows but a tick of 0 |
| tick | unsigned 32-bit page tick of the snapshot reported |
| enabled | 64-bit mask of the rules enabled |
| variables | count (the table's `V`), then each value (signed 32-bit) in order |
| timers | count (`T`), then for each: flags (bit 0 running) and elapsed ticks (unsigned 32-bit) |
| targets | count (0 to 64), then for each control and object the table names, in the order first named: kind; number (16-bit); flags (bit 0 exists, bit 1 shown, bit 2 cycling); look; frame; x; y (signed 16-bit); layer; order (signed 8-bit) — 12 bytes |
| values | count (0 to 64), then for each distinct value the table reads, in the order first read: the value (8 bytes) and its reading (signed 32-bit) |

- The answer is at most 1,800 bytes, within the input protocol's largest message (8,192).
- **Reason and source.** DEC-6522 item 8 (c): the page variables, which targets are shown or hidden, each drawing's look, the running timers and the current values of what the rules read; once, never a stream.
- **Verification.** Engine codec tests; a browser test that a query for a page not open gets no answer and that two queries in one second get one.

**RULE-48 [engine: neoteletext-input; neoteletext-browser; neoteletext-app-server]. RULES_FAULT, extension type `0x4D`.**
- **Statement.** A receiver reports a fault of a page's table with the input event of extension type `0x4D`: the stamp, the table's generation (16-bit), a code (1 byte) and a count (16-bit, how many times since the last report). The codes: 1 the table could not be decoded and was refused whole (the receiver and the server disagree; the page then has no table); 2 `tick_overrun` (RULE-6); 3 sends dropped by the send budget (RULE-52); 4 input events dropped from a full queue (RULE-5); 5 actions skipped for a missing target or sound (RULE-20); 6 a state query dropped; 7 a local sound stopped for overrunning its time (RULE-62); 8 animation slowed by its budget (ANIM-16). A receiver sends at most one RULES_FAULT a second for each code and page. The server gives the program `{"type":"rules_fault","connection":7,"page":"101","generation":3,"fault":"tick_overrun","count":12}` with the fault named `undecodable`, `tick_overrun`, `sends_dropped`, `events_dropped`, `actions_skipped`, `query_dropped`, `local_overrun` or `animation_slowed`, and writes code 1 to its operator's log as an error.
- **Reason and source.** DEC-6522 item 10: a refusal is reported, never silently ignored.
- **Verification.** Browser tests that produce each code; the server's test of each name.

**RULE-49 [engine: neoteletext-input; neoteletext-common]. Push protocol version 9.**
- **Statement.** The input protocol's `VERSION` (`neoteletext_input::limits::VERSION`, the number in HELLO, in WELCOME and in the push connection's subprotocol) MUST become 9, and version 8 MUST be refused both ways, as version 8 refused 7. Version 9 adds record types 21 to 27 (21 and 22 here; 23 to 27 in animation.md), the extension events `0x4B` to `0x4D`, the OBJECT record's tag 9 (RULE-60), and the rule that input events travel only inside RULE_EVENT (RULE-46). The descriptor's `push.input` and `push.wheel` are withdrawn: a server no longer writes them and a receiver ignores them; a page's table is the only thing that asks for input (REQ-6523). neoteletext-common's `wire-vectors.tsv` gains the version and the vectors of RULE-85.
- **Reason and source.** DEC-6522 item 2 ("This replaces the channel-wide `push.input` declaration"); a hard change of version, with no compatibility shim (DEVELOPMENT.md section 2.1).
- **Verification.** The wire vectors' test in the engine, the server and the browser; a version 8 HELLO refused.

**RULE-50 [neoteletext-browser]. A page with no table.**
- **Statement.** For a page whose view holds no table, the browser MUST evaluate nothing, give the decoder no input event of that page, and send its channel nothing for anything the viewer does on it: no key, text, paste, composition, press, release, move, wheel, hover, pick or focus change. The page is still shown, its links work, its sound plays, the looks under the pointer are drawn locally as today (the browser's REQ-6374 and the teletext controls' looks), and SELECT still tells the channel which page and sub-page the tab shows.
- **Reason and source.** REQ-6523: "A page with no rule table sends no input at all."
- **Verification.** REQ-6523's tests: for each kind of input, the fetcher's outgoing messages are empty.

**RULE-51 [neoteletext-browser]. What stays the browser's own.**
- **Statement.** Whatever a page's table says, the browser MUST keep for itself, and never give the evaluator or the channel:
  1. a key pressed with the browser's own modifier, which steps the page and sub-page lists (REQ-6390, DEC-6389), and every key the trusted strip or a browser dialog has;
  2. a click made with the browser's modifier (REQ-1384);
  3. a press and release on a link the page declares — a teletext link, a Fastext prompt or a linked ReGIS drawing — which the browser follows itself (REQ-4111, REQ-6376, decision 122); a rule's `press` on a target under a link does not fire;
  4. the wheel over a page with more than one sub-page, which steps the sub-pages, unless the page's table has an enabled `wheel` rule whose target the pointer is inside (this replaces the channel-wide `push.wheel` of DEC-6447). So that the trusted core can decide without reading a table, the decoder tells it, with the interest mask, at most 16 rectangles of the page's picture inside which an enabled `wheel` rule applies (the whole picture for the target `page`; an object's bounding rectangle), and tells it again when they change;
  5. everything typed or clicked outside the open page's picture.
- **Reason and source.** REQ-4112's exceptions, kept; DEC-6447's wheel rule restated on the table, since the channel-wide declaration is withdrawn.
- **Verification.** The existing tests of REQ-4112 and REQ-6390, re-pointed at the table; a test that a `wheel` rule takes the wheel from the sub-page list only inside its target.

**RULE-52 [neoteletext-browser]. The trusted core is the gate: nothing leaves that the viewer did not do and the page's view did not report.**
- **Statement.** The trusted core MUST enforce REQ-6523 itself, without reading a table:
  1. **In.** It gives a page's decoder the viewer's input events for the open page only while that decoder has told it the page has a table, and only of the classes the decoder asked for in its **interest mask** (bit 0 keys, bit 1 text, bit 2 pointer buttons, bit 3 pointer moves, bit 4 the wheel, bit 5 focus changes), which the decoder derives from the triggers and key-state values of the table. Each event it gives carries a sequence number, the page's key, and what the core already derives for it (the cell, the pixel, the control under the cell, the ReGIS drawing the pick record names).
  2. **Kept.** It keeps the last `INPUT_RING` (64) events it gave each open page.
  3. **Out.** A decoder asks for a report with a message that names the page, the rule, the tick and either an input sequence number, or a value and its reading, or nothing (a bare firing). The decoder never supplies an event's bytes. The trusted core builds the RULE_EVENT itself: for a sequence number, from its own kept copy of that event, and only when the event was given to that decoder for that page within the last `SEND_WINDOW_TICKS` (4) ticks and has not already been reported for that rule; otherwise it drops the request and counts it.
  4. **Where.** It gives the RULE_EVENT only to the fetcher of that page's own channel, on that view's own connection, and only while that page is still the open page of that view.
  5. **How much.** It sends at most `SEND_BUDGET` (120) reports a second for a page, holding at most 120, of which at most `TIMED_SEND_BUDGET` (20) a second may be reports with no input event (a bare firing or a value). What exceeds a budget is dropped and reported as fault 3.
  6. **State.** It passes a PAGE_STATE only in answer to a query its fetcher received for that page on that connection, once, and checks its length.
- **Reason and source.** REQ-6523; the browser's architecture (the trusted core reads no teletext format, so it cannot check a table, but it is the origin of every input event and can refuse to send anything it did not itself receive from the viewer for that page). A decoder taken over by a hostile page can then at most cause that page's own viewer's input on that page to reach that page's own channel — which the channel could have asked for with a table.
- **Verification.** The hostile-decoder harness: a decoder that asks to send a sequence number it was never given, one from another page, an old one, the same one twice for one rule, and 1,000 a second, gets none of them sent beyond the budget; the fuzz target of RULE-83.

**RULE-53 [neoteletext-app-server]. Migration: the channel's default table keeps every deployed channel working.**
- **Statement.** The server's channel configuration (an entry of `channels.json`) MUST gain the field `default_rules`, `"none"` (the default when absent) or `"send_all"`; the field `wheel` stays and now only shapes the default table. For a channel with `"send_all"`, the server MUST send, for every page of the channel for which a connection has been given no table by the program (or was given `"table":null`), the **default table** below, as that page's RULES record, exactly as RULE-40 sends a program's table. With `"none"`, such a page gets a RULES record with no table. The default table, in the form of RULE-35:

```json
{"rules":[
 {"name":"keys","on":{"event":"key","keys":"any","repeat":true},"do":[{"action":"send"}]},
 {"name":"keys_up","on":{"event":"key_up","keys":"any"},"do":[{"action":"send"}]},
 {"name":"text","on":{"event":"text"},"do":[{"action":"send"}]},
 {"name":"press","on":{"event":"press","target":"page","button":"any"},"do":[{"action":"send"}]},
 {"name":"release","on":{"event":"release","target":"page","button":"any"},"do":[{"action":"send"}]},
 {"name":"move","on":{"event":"move","target":"page","held":false},"do":[{"action":"send"}]},
 {"name":"hover_in","on":{"event":"enter","target":{"control":"any"}},"do":[{"action":"send"}]},
 {"name":"hover_out","on":{"event":"leave","target":{"control":"any"}},"do":[{"action":"send"}]},
 {"name":"drawing_in","on":{"event":"enter","target":{"object":"any"}},"do":[{"action":"send"}]},
 {"name":"drawing_out","on":{"event":"leave","target":{"object":"any"}},"do":[{"action":"send"}]},
 {"name":"focus","on":{"event":"focus"},"do":[{"action":"send"}]},
 {"name":"blur","on":{"event":"blur"},"do":[{"action":"send"}]},
 {"name":"wheel","on":{"event":"wheel","target":"page"},"do":[{"action":"send"}]}]}
```

- The last rule, `wheel`, is present only when the channel's `wheel` is `true`. The table is built by one function of `neoteletext-rules` (`default_send_all(wheel)`), so its bytes are the same everywhere. With it a page's program receives exactly the `input` messages version 13 gave it (each now naming its rule), so no deployed channel's code changes.
- The deployment (`deploy/ionos/deploy.sh`) MUST give `"default_rules":"send_all"` to every channel deployed on 18 November 2026: `home`, `hackaday`, `oldhackaday`, `demosite`, `uicomponentsdemo`, `regisgallery`, `regis`, `naplps` and `audio`. A new channel is given `"none"`, and `musicplayer` is the first.
- Each of those channels is to move to tables of its own (RULE-54) and then to `"none"`; that is one to-do for each channel, and the default table is deleted from the server when the last has moved.
- **Reason and source.** REQ-6523 requires that the page ask. The channel's operator asking on behalf of every page of a channel, in one reviewed line of configuration, is the least risky way to keep nine deployed channels working through the change: no channel's program has to be right about which of its pages take which input on the day the protocol changes. The alternatives are weighed in section 15, item 9.
- **Verification.** Server tests: a `send_all` channel's page with no program table gets the 12- or 13-rule table; `"table":null` puts it back; a `none` channel's page gets none. An end-to-end test for each deployed channel (the smoke tests that exist) passes unchanged against protocol 14.

**RULE-54 [neoteletext-server-ts-ui-components]. The component library writes each page's table.**
- **Statement.** The component library MUST derive a `rules` table for every page it composes from the components on it, and send it with the page, so that a page asks for exactly the input its components use: a text field or any component that takes typing, the `key` (any, with repeat), `key_up` and `text` rules; a button, a list row, a tab or any pressable component, `press` and `release` rules on its control (or its drawing, on a ReGIS page) and, where the component shows a server-drawn hover, `enter` and `leave`; a slider or anything dragged, `move` with `held` on its control; a component that scrolls, `wheel` on its rectangle; a page with none of these, a table with no rules. A component that only lights when pressed uses a local `look` action and sends only the release. Each rule is named for its component so that the handler the library already has for that component receives the `input` message by its `rule`.
- **Reason and source.** REQ-6523's purpose: a viewer's input goes nowhere a page has not asked for. The library already knows every interactive component of a page, so the precise table costs its authors nothing.
- **Verification.** Library tests: for each component kind, the table of a page that holds one; a page of static text sends an empty table; the demonstration channels' existing tests pass with `default_rules` set to `"none"`.

**RULE-55 [neoteletext-server-ts-protocol; neoteletext-server-channels]. The kits' calls.**
- **Statement.** Both kits MUST offer, as thin calls that only build and send the messages of this section (DEC-6462), with the TypeScript names here and the Python names their snake_case forms (a handler with `on_` before it), and list them in `kit-calls.tsv`:

| TypeScript | Python | Message |
|---|---|---|
| `context.rules(to, page, table)` | `app.rules(to, page, table)` | `rules`; `table` is the typed object of RULE-35 or `null` |
| `context.queryState(connection, page): Promise<PageState>` | `app.query_state(connection, page)` (awaitable) | `query_state`, resolved by `page_state`, rejected by `refused` |
| handler `ruleEvent(event, context)` | `on_rule_event(event)` | `rule_event` |
| handler `rulesFault(fault, context)` | `on_rules_fault(fault)` | `rules_fault` |
| the existing input handler | the same | `input`, whose event object gains `rule`, `tick` and `target` |

- The types (`RuleTable`, `PageRule`, `RuleTrigger`, `RuleCondition`, `RuleValue`, `RuleAction`, `RuleTarget`, `PageState`) are generated from the schema; the schema's existing type `Rule` (the refusal's rule) keeps its name. The kits MAY offer small builders that only construct these objects (for example `physicalKey("a")`, `level(0)`), and MUST NOT check a table beyond the schema. Each kit's test harness gains `press`, `fire` and `answerState` calls that feed a program the `input`, `rule_event` and `page_state` a receiver would cause.
- **Reason and source.** DEC-6462: the kits are thin and equal.
- **Verification.** Each kit's public-interface test against `kit-calls.tsv`; `server-rules` tests.

## 9. Limits, and the one crate

**RULE-56 [engine]. One crate, `neoteletext-rules`, holds the codec, the checks and the evaluator.**
- **Statement.** The engine repository MUST gain the crate `crates/neoteletext-rules`: `no_std`, without allocation, integer-only, with no dependency of any kind (not even another engine crate), `unsafe_code` forbidden, and denying the panic lints of DEVELOPMENT.md section 6 since it reads outside input. It holds: `limits` (every constant of RULE-57); `table` (the decoded table in fixed arrays); `decode` and `encode` of the RULES record's body, PAGE_STATE's payload and the animation operations shared with the ANIMATE record; `check` (every rule the decoder applies, callable on encoded bytes); `default_send_all`; `Evaluator` (the state of RULE-7 and the tick of RULE-5), which is given events, the metered values, and a `World` trait through which it reads target rectangles and tracked synthesizer values and to which it issues outputs (sound operations, animation operations, reports); and the interest mask and watch list of a table. Key codes, family codes and parameter numbers are plain numbers to it; the callers that know them (the server through `neoteletext-input` and `neoteletext-audio-instruments`' interface modules; the decoder through the trackers) check what the crate cannot.
- **Reason and source.** DEC-6522 item 9: the server checks a table "with the browser's own code". One implementation of decode and check means a table the server accepts is a table every receiver accepts; no dependency means it builds for every engine target, microcontrollers included.
- **Verification.** `cargo xtask check-deps` and `check-io` list it with nothing permitted; it builds for `thumbv6m-none-eabi`; `cargo xtask features` builds it alone.

**RULE-57 [engine: neoteletext-rules]. The limits, each a named constant defined once in `neoteletext_rules::limits`.**
- **Statement.** These are maximums. A table over any of them is refused whole (RULE-70).

| Constant | Value | What it bounds |
|---|---|---|
| `TICKS_PER_SECOND` | 60 | the clock (ANIM-1 asserts the engine's and this agree) |
| `MAX_RULES` | 64 | rules a table (DEC-6522 item 10) |
| `MAX_ACTIONS` | 16 | actions a rule (item 10) |
| `MAX_TIMERS` | 8 | timers a table, beside the page timer (item 10) |
| `MAX_VARIABLES` | 32 | variables a table (item 10) |
| `MAX_RECTS` | 16 | rectangles a table |
| `MAX_SUBPAGE_MASKS` | 16 | sub-pages with rules switched off |
| `MAX_KEYS_PER_TRIGGER` | 16 | keys in a key set |
| `MAX_CONDITION_TERMS` | 8 | terms a condition (item 6) |
| `MAX_CONDITION_NODES` | 16 | nodes a condition |
| `MAX_CONDITION_DEPTH` | 3 | operator nesting (item 6) |
| `MAX_SET_MEMBERS` | 8 | constants in an `in_set` |
| `MAX_AND_OR_CHILDREN` | 8 | children of `and` or `or` |
| `MAX_TABLE_VALUES` | 64 | distinct values a table reads |
| `MAX_TABLE_TARGETS` | 64 | distinct controls and objects a table names |
| `MAX_WATCHED` | 32 | distinct metered values a table reads (RULE-33) |
| `MAX_TABLE_BYTES` | 8,184 | an encoded table (one record body) |
| `MAX_TIMER_TICKS` | 216,000 | `ticks` of `every` and `after` (one hour) |
| `MAX_CYCLE_PERIOD` | 3,600 | ticks a frame of a cycle (one minute) |
| `MAX_FRAME` | 15 | the highest frame number (ANIM-14's `MAX_OBJECT_FRAMES` is 16) |
| `MAX_EVENTS_PER_TICK` | 16 | input events handled a tick |
| `MAX_QUEUED_EVENTS` | 64 | input events waiting |
| `MAX_ACTIONS_PER_TICK` | 256 | actions run a tick (item 10: "evaluation capped per tick") |
| `MAX_KEYS_DOWN` | 16 | keys tracked as down |
| `MAX_CATCH_UP_TICKS` | 6 | overdue ticks run in one wake |
| `MAX_STATE_BYTES` | 1,800 | a PAGE_STATE payload |

- The trusted core's constants live in the browser's `protocol` crate: `INPUT_RING` 64, `SEND_WINDOW_TICKS` 4, `SEND_BUDGET` 120 a second, `TIMED_SEND_BUDGET` 20 a second, `QUERY_INTERVAL_TICKS` 60. The server's `MAX_KEPT_TABLES` 64 lives in `teletext-runtime`. The local sound's constants are RULE-62's.
- The worst case of one tick follows from them: 16 events × 64 rules, each a condition of at most 16 nodes, and at most 256 actions; a few tens of thousands of integer operations, far inside a tick on any target the engine supports.
- **Reason and source.** DEC-6522 item 10; the engine's rule that every constant is defined once (REQ-GEN-014).
- **Verification.** A test for each constant: a table at the limit is accepted and one over is refused; `cargo xtask check-constants`.

**RULE-58 [neoteletext-browser]. Where the table lives in the browser: the decoder evaluates, the trusted core gates.**
- **Statement.** The decoder process of the page's channel — confined, with no network, no file access and no secrets, and already the reader of every record of that channel — MUST decode the RULES record (with `neoteletext-rules`), hold the table and run the evaluator on its own presentation clock. The trusted core MUST NOT decode or evaluate a table, and `neoteletext-rules`' evaluator MUST NOT be linked into it; it does only RULE-52. A table is evaluated only for the **open page**: the one page of the active tab that keys would go to (the browser's REQ-1378). A page that is merely visible in the overview or a wall, or in a tab that is not active, has no evaluator running, plays no local sound and is given no input. While no open page has a table, the decoder keeps no 60-a-second wake for rules (it still wakes for flash and animation, ANIM-1).
- **Reason and source.** Evaluation of an untrusted table belongs in a confined process (the browser's requirement 1.2, DEVELOPMENT.md section 1 item 5); the decoder already holds the page, its objects and its instruments' trackers, so the evaluator needs no new message to read them. A waiting program waits on what it needs (decision 46): no table, no rule wake.
- **Verification.** The browser's dependency-tree check lists `neoteletext-rules` in the decoder and (for RULE-59's check only) nowhere in the trusted core; a test that an idle page with no table causes no 60-a-second wake.

**RULE-59 [neoteletext-app-server]. The server checks and encodes with the same crate.**
- **Statement.** The server MUST depend on `neoteletext-rules` at the engine revision it pins, build each RULES record with its `encode`, and pass the result through its `check` before sending (RULE-39). It MUST resolve key names with `neoteletext_input::keys::code` and synthesizer field names with the families' `PARAMETERS` tables (RULE-29), and has no table, key list or parameter list of its own.
- **Reason and source.** DEC-6522 item 9; DEC-6462. It is how the server already checks ReGIS: with the renderer's own code.
- **Verification.** A server property test: every table the server accepts decodes in `neoteletext-rules` to the same table.

## 10. Latency: from a key to sound and to the picture

**RULE-60 [engine: neoteletext-audio; neoteletext-browser]. A local sound: an instrument the page keeps open, played by rules.**
- **Statement.** The audio profile MUST gain the **local sound**: a synthesizer sound of any family that plays notes (codec codes 13 to 18; not the synth6581 family, which has no note messages) whose OBJECT record carries the new tag 9, `TAG_LOCAL`, with one value byte, 1. It is announced as a stored sound of one block of that family, and its one block is the **setup**: an event list in the block form of midi-architecture.md MIDI-23 with every event at tick 0, at most `MOST_BLOCK_BYTES` (1,005) bytes, applied in order when the instrument is made. It names its banks as other sounds of its family do. A receiver never renders a local sound from blocks and never streams it: when a play command (from the server or from a rule's `play`) starts it on an audio channel, the receiver makes the family's instrument in its sound output stage, applies the setup, and from then on gives it the messages of rules' `midi` actions (RULE-21) as they arrive. `stop` and `gain` act on its audio channel as on any sound. A local sound MUST be played with a page scope (the play command's page) and ends, with all notes released, when that page is no longer the open page. At most `MOST_LOCAL_SOUNDS` (2) play at once in a view; a third play is refused and counted. A receiver without a sound output stage of this kind ignores a local sound's OBJECT, as it ignores a codec it does not have.
- **Reason and source.** The owner's goal: "INSTANTLY PLAYING ON A KEYPRESS". Today every synthesizer sound is rendered ahead in the decoder and streamed, and the mixer holds a stream silent until `STREAM_TARGET_MS` (400 milliseconds) is buffered, so no message can reach a sounding instrument in less. A local sound has no timeline of the server's to keep, so it needs no buffer.
- **Verification.** Engine tests: the OBJECT with tag 9 parses, and the audio receiver gives a sink the local sound's start instead of a stream; a browser test that a local sound ends when its page closes.

**RULE-61 [neoteletext-app-server]. The local sound in the program protocol.**
- **Statement.** The `sound` message MUST gain the kinds `synth7_local`, `synth106_local`, `synth60_local`, `synthd_local`, `synth53_local`, `synth52_local`, `synth51_local`, `synth8_local` and `synth80_local`. Each has the fields of its family's `_live` kind (`connections`, `handle`, `generation`, `banks`, and the family's own options such as synth8's key mode), and `setup`: a list of at most 64 of the family's events (`Synth106Event` and the others), each with `time_us` 0, which the server packs into the setup block and refuses with `block_full` when they do not fit. `play` of a local sound MUST name a `page`, with `loop` and `after` false, else `out_of_range`. Example:

```json
{"type":"sound","kind":"synth106_local","connections":"all","handle":1,"generation":1,"banks":[2],
 "setup":[{"event":"program_change","channel":1,"program":0,"time_us":0}]}
{"type":"sound","kind":"play","connections":"all","channel":0,"handle":1,"generation":1,"gain":100,"fade_ms":5,"duck":0,"loop":false,"after":false,"page":"101"}
```
- **Reason and source.** DEC-6462: the server packs; the kits send typed fields.
- **Verification.** Server tests: the records built for each family; the refusals.

**RULE-62 [neoteletext-browser; engine: neoteletext-audio-mix]. The sound helper renders a local sound in blocks of 128 samples.**
- **Statement.** The sound helper MUST link `neoteletext-audio-instruments` and hold each local sound's instrument. The engine mixer MUST gain a **pulled voice**: a voice whose samples the mixer asks for as it mixes, at 48,000 samples a second, through the mixer's existing resampler to the device's rate. For each device buffer the helper renders each pulled voice just in time, in blocks of `LOCAL_BLOCK_SAMPLES` (128 samples, 2.67 milliseconds), and before each block applies every MIDI message queued for that instrument, in arrival order; the queue holds `LOCAL_MIDI_QUEUE` (256) messages, and one arriving at a full queue is dropped and counted. No buffer is held ahead: a message waits at most one block. While a local sound is open the helper asks the output device for a small buffer (RULE-97). While a local sound plays, the helper keeps the output device running, so that a note never waits for the device to start; a view's speaker mark still follows what is heard (a level above 0). When rendering a view's local sounds takes longer than the time of the buffer it fills for `LOCAL_OVERRUN_BUFFERS` (8) buffers running, the helper stops that view's local sounds with all notes released and reports it (fault 7). Each constant is defined once, in `neoteletext-audio-mix` (`LOCAL_BLOCK_SAMPLES`) and the browser's `sound` crate (the queue and the overrun count).
- **Reason and source.** Rendering inside the audio callback is the only place where the delay is one block and the device's own buffer. The instruments are `no_std`, integer-only and never allocate, which is what code on an audio thread must be.
- **Verification.** A helper test with a scripted device: a note on queued before a buffer sounds within the first 128 samples of that buffer; the overrun stop; a measured figure for each family's cost of rendering one buffer of eight held notes, recorded with the date.

**RULE-63 [neoteletext-browser]. The messages that carry a local sound.**
- **Statement.** The voice operations of `protocol::audio` MUST gain, in the next operation numbers free (12 to 15 on 18 November 2026):

| Operation | From | Fields |
|---|---|---|
| 12 `LocalBank` | the decoder | audio channel; the sound (handle, generation); bank index 0 to 9; the bank image, at most 16,384 bytes (`MOST_BANK_BYTES`) |
| 13 `Local` | the decoder | audio channel; the sound; family code 13 to 18; variant; the family's option byte (synth8's key mode, else 0); gain; fade; the setup block, at most 1,005 bytes. Starts the instrument with the banks given for that channel and sound since the last `Local` |
| 14 `LocalMidi` | the decoder | audio channel; status; data 1; data 2 — to the local sound on that channel |
| 15 `Watch` | the trusted core alone | the watch list of RULE-33: a count 0 to 32 and that many slots of audio channel, kind and part |

- and the sound helper's messages to the trusted core gain kind 5, `Metered`: the view's channel number, a count and that many bytes (RULE-33). The trusted core checks every field's bounds, never reads a bank image or a setup block, and passes them on unread, as it passes samples. Between the trusted core and a decoder the new messages (`Input` to the decoder with its sequence number; `Metered` to the decoder; `RulesOpen` from the decoder with the interest mask, the watch list and the wheel rectangles of RULE-51; `Report` from the decoder, RULE-52 item 3; `PageState` from the decoder; `Fault` from the decoder) take the next kind numbers free across every pipe (178 upward on 18 November 2026), as the protocol crate's rule for kind numbers requires.
- **Reason and source.** The existing shape: one payload form on both pipes, each side accepting only the operations meant for it.
- **Verification.** Protocol tests for each message at its bounds, and that the decoder may not send `Watch`.

**RULE-64 [neoteletext-browser]. The latency budget from a key to sound.**
- **Statement.** With a local sound playing, the path of a key press is, hop by hop, with the most each may add:

| Hop | Most |
|---|---|
| The interface process reads the key from the operating system and writes its intent to the trusted core | 1 ms |
| The trusted core finds the open page, checks the interest mask and writes the event to the decoder | 1 ms |
| The decoder reads the event, evaluates its rules at once (RULE-96) and writes `LocalMidi` to the trusted core, before any other work | 1 ms |
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

- For a size between two rows the bounds are those of the next row down. The `LocalMidi` message itself MUST leave the decoder within 2 milliseconds of the interface reading the key, at most, whatever the phase of the tick. The output device's own delay after its buffer is the machine's and is reported beside the figure.
- Before DEC-6580 the same path was budgeted at 34 milliseconds at most and 20 in the median (a wait of up to 16.7 for the tick and a device buffer of 10), and measured between threads at 24 to 27 at most and 12 to 15 in the median.
- **Reason and source.** The owner's goal of sound "INSTANTLY" on a key press; the owner's decision DEC-6580 items 1 and 2 (18 November 2026), which take the tick's wait and half the device buffer out of the path: "about 5 ms median and 12 to 15 ms at most, the range of a hardware synthesizer's own delay". DEC-6522 item 3's tick remains the one place every other effect of an event waits.
- **Verification.** RULE-66's measurement.

**RULE-65 [neoteletext-browser]. The latency budget from a key to the picture.**
- **Statement.** A rule's `show`, `hide`, `look`, `move`, `frame` or `order` MUST be painted by the decoder in the tick that ran it, as a damage repaint of the changed rectangle only (ANIM-4), and its frame given to the trusted core in that tick, marked as the answer to input so that the core's and the interface's "drawn as it arrives" rule applies (the browser's requirement 18.12, REQ-6400). Picture changes stay on the tick (RULE-5): only sound leaves on arrival. With the tick locked to the display's refresh (RULE-98), a tick is due `TICK_LEAD_MICROSECONDS` (4,000) before the interface composes a frame, and the frame the decoder paints in that tick MUST be in that composition. The path, with the most each part may add:

| Part | Most | Median |
|---|---|---|
| The interface reads the key and the trusted core passes it to the decoder | 2 ms | 0.5 ms |
| The event waits for its tick | 16.7 ms | 8.3 ms |
| The tick's evaluation and repaint, and the frame's way through the trusted core to the interface, all inside the tick's lead | 4 ms | 4 ms |

- From the interface reading the key to the interface composing the frame that shows the change, the browser MUST take **at most 23 milliseconds** (`2 + 16.7 + 4 = 22.7`) and **13 milliseconds or less in the median** (`0.5 + 8.3 + 4 = 12.8`), plus the display's own scan-out, on a display RULE-98 can lock to. On a display it cannot lock to, one refresh period of that display is added to the greatest and half of one to the median. Before DEC-6580 the tick and the display were not aligned, and up to one frame of 16.7 milliseconds was added on every display: 39 at most.
- A `becomes` rule on a metered `level` adds the meter's age (RULE-33). The note begins at most 12 milliseconds after the key (RULE-64); the report that holds its level leaves the helper within a sixtieth of a second and one device buffer of that (16.7 + 5.3); it reaches the decoder in 2 more; it is read at the next tick (RULE-7: the newest report at the tick, even when the tick's snapshot was taken on an arrival), at most 16.7 later; and the frame is composed 4 after the tick. A meter segment MUST light **at most 57 milliseconds** after the key (`12 + 22 + 2 + 16.7 + 4 = 56.7`) and **30 milliseconds or less in the median** (`5 + 11 + 1 + 8.3 + 4 = 29.3`).
- **Reason and source.** The owner's goal: "INSTANTLY DISPLAYING LEVELS VISUALLY ALSO IN RESPONSE TO THE KEYPRESS"; the owner's decision DEC-6580 item 3. The earlier text gave the meter 45 milliseconds at most without counting the report's own interval; the figure here counts every part.
- **Verification.** RULE-66's measurement.

**RULE-66 [neoteletext-browser]. The measurement is kept, between real processes, before and after.**
- **Statement.** The browser's repository MUST hold a timed test, built on the script that already times a key to the pixels (DEC-6398 item 8), that runs the browser as it ships — the interface, the trusted core, a confined decoder and the sound helper as four operating-system processes joined by their real pipes, not as threads of one test process — with the music player's page 101 open and its local sound playing. It injects a key at the interface's input and records, on one monotonic clock read in each process: the time the interface read the key; the time the decoder wrote `LocalMidi`; the time the sound helper's test device was handed the first non-zero sample of the note; the time the interface composed the frame that shows the changed rectangle; and the time it composed the frame that shows the first lit meter segment. It does so over at least 200 keys at random phases of the tick and of the device buffer, prints the least, median and greatest of each interval with the device buffer granted and the display's refresh rate, and fails when a bound of RULE-64 or RULE-65 is passed. It builds the programs it times (DEVELOPMENT.md section 8).
- The test MUST be able to run the browser with each of the three changes of DEC-6580 switched off for the measurement alone — evaluation at the tick (the decoder calling `push` in place of `push_now`), the device buffer left at 480 frames, and the tick left unlocked — by a setting of the test's own that no shipped configuration and no page can reach, so that the same test on the same machine on the same day gives the figures before and after each change. The six sets of figures (each change off, then on) are recorded with the date, the machine and the output device in the rdm requirement that carries this rule, and the change is not called done without them.
- **Reason and source.** DEVELOPMENT.md section 2.1: performance claims carry before and after numbers from an instrument shown to exercise the changed code. DEC-6580: "Each is measured before and after, between real processes". The figures of 18 November 2026 were taken between threads of one process, which leaves out the processes' scheduling and their pipes.
- **Verification.** It is the verification.

**RULE-96 [engine: neoteletext-rules; neoteletext-browser]. An input event's rules are evaluated when it arrives.**
- **Statement.** `neoteletext-rules`' evaluator MUST offer both ways of RULE-5 on one evaluator, freely mixed: `Evaluator::push(event)`, which leaves the event for the tick, and `Evaluator::push_now(event, world)`, which takes step 2 for it at once and gives the world the sound operations of the rules it fires (`World::sound_operation`) before it returns. `Evaluator::tick(world)` then runs the tick with those events already handled. The bounds are the tick's and are the same either way:
  1. at most `MAX_EVENTS_PER_TICK` (16) events are handled for one tick, counting those handled on arrival; the 17th arrival of an interval waits in the queue for the next tick, and its sound operations leave when it is handled, on a later arrival or at a tick;
  2. an event handled on arrival keeps its place among the `MAX_QUEUED_EVENTS` (64) waiting until its tick has run, so the 65th waiting event is dropped and counted whichever way events are given;
  3. every firing counts against its tick's `MAX_ACTIONS_PER_TICK` (256), and one past it is dropped whole (RULE-6);
  4. the snapshot is taken once a tick (RULE-7), never once an event.
- When the page closes with events handled on arrival whose tick has not run, that tick is run before the final tick, so that what those events' rules wrote and reported is not lost when their sound has left.
- **In the browser** the decoder MUST call `push_now` for each input event of the open page as soon as it has read the event from the trusted core's pipe, before any other work that is waiting (a record to decode, a repaint, a tick that is not yet due), and MUST write the `LocalMidi`, play, stop and gain messages its world is given during that call to the trusted core, and flush them, before it returns to that other work. It reads the pipe by waiting on it, never by looking at intervals (the browser's decision 46). Its world's answers during `push_now` are the page as it stands; its own record of what plays on each audio channel (RULE-27) MUST change for a sound operation at the end of the tick the operation belongs to, not when the operation leaves, so that no condition sees a sound operation in its own tick (RULE-6). A tick that falls due while an event is being handled runs after it. Everything else the decoder does for a tick — steps 3 to 7, the repaint, the reports to the trusted core (RULE-52), the animation — is unchanged and happens at the tick.
- The interface and the trusted core change nothing for this rule: they already pass an event as it arrives. A receiver without a sound output of its own (`neottx rules-run`, the server's checks) may use either way; `neottx rules-run --on-arrival` uses the second, and writes the same lines.
- **Reason and source.** The owner's decision DEC-6580 item 1. A table gains nothing from it that it could not do one tick later: see threat 16 of section 12.3.
- **Verification.** The tests of RULE-5, RULE-7 and RULE-8 for arrivals; tests of each bound above (the 17th arrival, the 65th waiting, the cap, the close); the fuzz targets `rules_evaluate` and `rules_no_unasked_send` driven both ways (RULE-83). In the browser: a decoder test that an event read from the pipe while a tick is 10 milliseconds away writes `LocalMidi` before the tick, and RULE-66's interval from the key to `LocalMidi`.

**RULE-97 [neoteletext-browser]. A small device buffer while a local sound is open.**
- **Statement.** The sound helper opens its output device with a buffer of `USUAL_DEVICE_FRAMES` (480 frames at 48,000 a second, 10 milliseconds; at another rate the same time). While at least one local sound is open in any view — from the `Local` operation that starts it (RULE-63) until it ends — the helper MUST instead run the output device with a buffer of `LOCAL_DEVICE_FRAMES` (256 frames at 48,000 a second, 5.33 milliseconds; at another device rate the number of frames nearest that time):
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
  4. **When it cannot.** On a display whose rate is no such multiple (50, 75, 100 or 144 hertz), or with no `FramePhase` for `PHASE_STALE_MILLISECONDS` (1,000), the decoder's clock runs free as RULE-4 gives it, and RULE-65's bound grows as it says.
  5. **The lead holds the work.** `TICK_LEAD_MICROSECONDS` is the time for a tick's evaluation and repaint and for its frame to pass the trusted core and reach the interface before composition: 1 millisecond for each of those three and one to spare. A tick whose frame reaches the interface after the composition it was meant for is counted (`late_frames`, shown with RULE-72's counters), and the frame is in the next composition.
- No record, no page and no channel can read or change the phase; the push protocol and the program protocol are unchanged. The decoder learns from `FramePhase` only the refresh period and phase of the viewer's display, which it does not report anywhere: threat 12 of section 12.3 is unchanged, since a table still reads nothing of time but its page tick. Each constant is defined once, in the browser's `protocol` crate.
- **Reason and source.** The owner's decision DEC-6580 item 3: "The presentation clock's ticks are phased so that a tick's work finishes just before the interface composes a frame … On a display refreshing faster than 60 times a second the tick stays 60 a second and falls on a frame boundary. No record or protocol changes." The slew and what is done on a display that is no multiple of 60 are section 15, items 20 and 21.
- **Verification.** Decoder tests with a scripted clock and scripted `FramePhase` messages: at 60 hertz the ticks come to rest 4,000 microseconds before each composition within 200, having moved no more than 100 a tick; at 120 hertz every tick is 4,000 before a composition; a display of 59.94 hertz is followed with no tick skipped or repeated over 10 minutes; 144 hertz and a stale phase leave the clock free; a page's tick 0 is on the target. A protocol test of `FramePhase` at its bounds. RULE-66's figures with the lock off and on.

Numbers RULE-67 to RULE-69 are not used. RULE-96 to RULE-98, added on 18 November 2026 for DEC-6580, stand above with the latency rules they belong to.

## 11. Refusal, faults and counters

**RULE-70 [engine: neoteletext-rules; neoteletext-browser]. A table is accepted whole or refused whole.**
- **Statement.** `decode` MUST refuse a body when any field is outside its range, any reserved bit or byte is not 0, any count exceeds its limit, any number refers to a variable, timer, rectangle or rule the table does not have, the condition is not one tree, the body is short, or bytes follow its end. Nothing of a refused table is kept or evaluated: the page then has no table (and so sends no input, RULE-50), and the receiver reports fault 1 (RULE-48). A receiver never repairs a table, skips a faulty rule, or holds a limit lower or higher than RULE-57's.
- **Reason and source.** DEC-6522 item 10; the MHEG-5 lesson that errors silently ignored hide a divergence.
- **Verification.** The fuzz target `rules_decode`; a test that each single-byte corruption of a valid table either decodes to a valid table or is refused whole.

**RULE-71 [neoteletext-browser]. A table is trusted for nothing.**
- **Statement.** The decoder MUST treat every number in a table as untrusted when it is used as well as when decoded: an object number that names nothing, a handle with no sound, an audio channel with no local sound and a frame beyond an object's frames each make the action a counted no-op (RULE-20). No table can make the decoder allocate: every structure the evaluator uses is a fixed array sized by RULE-57.
- **Verification.** The fuzz target `rules_evaluate` under a counting allocator that fails the test on any allocation inside a tick.

**RULE-72 [neoteletext-browser]. Counters.**
- **Statement.** For the open page the decoder MUST count, and the browser's console MUST show to the page's author (as it shows a channel's log): ticks evaluated; rules fired; actions run; actions skipped; events dropped; sends asked for, sent and dropped; overruns; the newest metered values. The counts are the receiver's own and are sent to the channel only as the faults of RULE-48.
- **Verification.** A console test.

## 12. Security analysis

This section is the analysis DEVELOPMENT.md sections 2.3 and 14 require of a feature that reads outside input and adds an output. Its findings are applied in the requirements named.

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
| 1 | A table that is a program: loops, recursion, unbounded work | RULE-1, RULE-5, RULE-6: one pass a tick in a fixed order, nothing an action does is seen in the same tick, `MAX_ACTIONS_PER_TICK`; RULE-57's worst case | Nothing: the work of a tick is bounded by constants |
| 2 | A table built to exhaust memory or to crash the decoder | RULE-56 (no allocation, panic lints denied), RULE-70 (refused whole), RULE-71, the fuzz targets of RULE-83 | A fault in the crate would be confined to that channel's decoder, which holds only that channel's pages |
| 3 | A page that takes input the viewer did not mean for it | RULE-58: only the open page of the active tab is given input, and only the classes its table asks for; RULE-51: the browser's own keys, links and the strip are never given; the insecure badge is unchanged | A page the viewer has open and is typing at can ask for every key typed at it, as every page could before this document; it can no longer have them without a table saying so |
| 4 | Input leaving for somewhere else | RULE-52 items 3 and 4: the trusted core builds each report from its own copy of the event, for the page's own channel on its own connection | Nothing |
| 5 | A decoder taken over, asking the core to send what the viewer never did | RULE-52 item 3: the decoder supplies no event bytes; a sequence number it was never given, or an old one, is dropped | It can cause real input on its own page to reach its own channel, which the channel's table could have asked for |
| 6 | A covert channel out through values: a `send` of a value, or the state answer, carrying data chosen by a compromised decoder | RULE-52 item 5: 20 valued or bare reports a second; item 6: one state answer a query, a query a second | A compromised decoder can already send its channel nothing it does not already hold (its own pages and its own page's input); the budget bounds the rate |
| 7 | Learning the viewer's settings or other tabs through metered values | RULE-32: `level` is measured before the master volume and the mute, per view; RULE-33: the helper reports a view's values only to that view | Nothing in the design. See 8 |
| 8 | A sound helper taken over through an instrument (a hostile bank image or MIDI stream), reporting another view's sound as this view's levels, which a colluding table then sends home | The instruments and the mixer are `no_std`, allocation-free and forbid `unsafe`, and every family's bank reader and message reader is fuzzed (RULE-83); the trusted core accepts a report only of the length of the list it passed (RULE-33 item 4), so at most 32 bytes a tick | A fault in the instruments that gave control of the helper would let a page learn which other tabs sound, at up to 32 bytes a tick. The helper already held every tab's sound before this document; what is new is a path back. It is recorded for the owner (section 15, item 12) |
| 9 | Sound as a nuisance or a weapon: a table that plays loud notes for ever | The viewer's volume and mute are outside a page's reach; a local sound ends when its page is no longer open (RULE-60); the audio profile's limiter is unchanged | A page can make sound while open, as it could with the audio profile |
| 10 | Processor exhaustion through local instruments | `MOST_LOCAL_SOUNDS` 2 a view, only for the open page; RULE-62's overrun stop | A page can cost up to the overrun bound of processor on the audio thread for 8 buffers before it is stopped |
| 11 | Processor exhaustion through animation actions | The animation budget (ANIM-16) and the repaint budget (REQ-6368) | As animation.md states |
| 12 | Timing: a table as a clock for measuring the machine | A page tick is all a table can read of time, and `send` reports it; ticks slow under load (RULE-4) | A channel can learn that the machine was late by comparing ticks with its own clock: about one bit a second, of the machine's load |
| 13 | Fingerprinting the keyboard layout through `physical` and `char` keys | The KEY event already carries both (`key` and `base`), so a page that is sent keys learns the layout today | Unchanged |
| 14 | A table that survives the page: acting after the viewer has left | RULE-58: evaluation stops, and local sounds end, when the page is not the open page; variables are not kept (RULE-14) | Nothing |
| 15 | The default table (RULE-53) sending more than a page needs | It is the behaviour of 18 November 2026 made explicit, chosen for each channel by its operator; RULE-54 and the per-channel to-dos replace it | Until a channel moves, its pages ask for everything, as they did |
| 16 | Evaluation on arrival (RULE-96) used to do more work than a tick allows, to act sooner than the page's own channel could, or to see what a tick would not; the small device buffer (RULE-97) or the phase message (RULE-98) used against the machine | RULE-96: an arrival is the viewer's own input, passed by the trusted core under RULE-52 as before; at most 16 are handled for a tick whichever way, each firing counts against that tick's 256 actions, the snapshot is taken once a tick, and an arrival reads only what its tick's step 2 would read. Only `midi`, `play`, `stop` and `gain` leave early, to the page's own audio channels, which the table could command one tick later; a report never leaves before its tick, so nothing reaches the channel sooner. RULE-97: the buffer is small only while a local sound is open, at most 2 a view (RULE-60), and one underrun or overrun returns it to 480 frames. RULE-98: the phase comes from the interface through the trusted core; a table reads nothing of it | A page with a local sound makes the audio thread wake 187 times a second in place of 100 while it is open, until the first overrun |

### 12.4 Requirements of the analysis

**RULE-80 [neoteletext-browser; engine]. The threat models are updated.**
- **Statement.** The engine's `THREAT-MODEL.md` and the browser's `docs/security-analysis.md` MUST gain the table of section 12.3, and the browser's `docs/architecture.md` the processes' new messages (section 6.4) and the decoder's and the sound helper's new holdings (section 6.1: the decoder holds the open page's rule state and input; the sound helper holds local instruments and reports levels).
- **Verification.** Review, recorded with its date.

**RULE-81 [neoteletext-common]. Privacy: what a channel learns, and the rule channels are bound by.**
- **Statement.** The protocol's privacy rules (viewer-state.md section 11, and the protocol document's items on input) MUST state that: a channel receives a viewer's input on a page only through that page's table; `send`, `echo` and the state query's answer reveal what the viewer did on that page — keys, clicks, the variables their keys changed, which objects the page showed — to that page's own channel and to no one else; a channel MUST use them only to provide what the page offers the viewer, as it is bound for the viewer's handle (viewer-state.md VS-503); and a channel MUST NOT ask for input a page does not use. The browser's privacy page says the same in the viewer's terms.
- **Reason and source.** DEC-6522 item 12.
- **Verification.** Review of the generated protocol document's items.

**RULE-82 [neoteletext-browser]. The amendment to REQ-661.**
- **Statement.** The browser's requirement 1.3 (REQ-661) MUST read: "The application MUST NOT execute code supplied by a page, a channel, a server or a file, with one exception: the decoder MAY evaluate a page's rule table as neoteletext-common's `docs/page-rules.md` defines it (DEC-6522) — a declarative list of event bindings evaluated once per tick of one sixtieth of a second — provided that the table is decoded and evaluated only by the engine crate `neoteletext-rules`, only in the confined decoder process and never in the trusted core; that it stays within every bound of that document's RULE-57 (at most 64 rules, 16 actions a rule, 8 timers and 32 variables a page; conditions of at most 8 integer comparisons nested at most 3 deep; at most 256 actions a tick; no rule firing another within a tick); and that nothing reaches the network because of it but the reports the trusted core itself builds under RULE-52 and the answer to a state query, to the page's own channel on its own connection. The rule table is not a script engine, a web engine or a general interpreter, and the inspection of the application's dependency tree continues to find none other than the decoder's WebAssembly interpreter, which runs only the application's own decoder module." Its reason gains the owner's ruling of 18 November 2026, and its verification gains the fuzz targets of RULE-83 and the hostile-decoder harness of RULE-52.
- **Reason and source.** DEC-6522 item 1 amends REQ-417; REQ-661 is the browser's statement of the same rule and needs the same exception.
- **Verification.** rdm: REQ-661 revised with this text.

**RULE-83 [engine; neoteletext-browser; neoteletext-app-server]. Fuzz targets.**
- **Statement.** These targets MUST exist, each replaying first every input that ever found a fault (DEVELOPMENT.md section 8):

| Target | Where | It holds that |
|---|---|---|
| `rules_decode` | engine | any bytes decode to a table within every limit or are refused whole; `encode(decode(x))` decodes to the same table |
| `rules_evaluate` | engine | any valid table with any script of events, metered values and world answers runs any number of ticks without panic or allocation, never runs more than `MAX_ACTIONS_PER_TICK` actions in a tick, never reports an input event it was not given, and gives the same outputs when run twice; all of it with the events given at the tick and given on arrival (RULE-96), and both ways give the same sound operations, the same other outputs and the same counters at every tick |
| `rules_no_unasked_send` | engine | (REQ-6523's) for any table and events, every report of an input event is of an event that matched an enabled rule holding `send` or `echo`, with the events given at the tick and given on arrival |
| `rule_event`, `page_state` | engine (`neoteletext-input`) | the two messages' readers and writers agree and refuse what is out of range |
| `local_midi` | engine (`neoteletext-audio-instruments`) | for each family, any setup block, bank images and MIDI messages render without panic, and `meter` and the parameter reads stay in range |
| `rules_json` | server | any JSON line as a `rules` message is refused or encodes to a record `neoteletext-rules` accepts |
| `core_report_gate` | browser | any sequence of decoder messages and viewer events never makes the trusted core send an event it did not receive from the viewer for that page, or exceed its budgets |
| `protocol_audio_local` | browser | the new voice operations' readers hold their bounds |

- **Verification.** The full gates run each for their stated time.

## 13. Verification

**RULE-84 [every repository]. Each requirement's tests name it.**
- **Statement.** Every test written for this document MUST name the `RULE-n` it verifies and the rdm requirement that carries it, and each requirement above lists the tests it needs under its Verification. In summary, by kind: codec tests at every bound (RULE-3, 9 to 22, 41 to 48, 57, 70); evaluator tests with a scripted clock and world (RULE-4 to 8, 11, 14 to 17, 96); instrument tests for every family (RULE-28, 29, 31); mixer and helper tests with a scripted device (RULE-32, 33, 62, 97); decoder tests with a scripted clock and frame phase (RULE-98); pipe protocol tests (RULE-63); trusted core tests with a hostile decoder (RULE-50 to 52); server protocol tests for every example and refusal (RULE-34 to 40, 53, 59, 61); kit tests against `kit-calls.tsv` and the server's refusals (RULE-55); library tests per component (RULE-54); the timed test (RULE-64 to 66); the fuzz targets (RULE-83); and the music player's end-to-end test (RULE-95).
- **Verification.** Each repository's check that test names cite records that exist.

**RULE-85 [neoteletext-common; engine; neoteletext-app-server; neoteletext-browser]. Shared wire vectors.**
- **Statement.** neoteletext-common's `wire-vectors.tsv` MUST gain, as hexadecimal bytes with the JSON they stand for: the RULES record body of each worked example of section 7.5 and of the default table with and without `wheel`; one RULE_EVENT of each kind; one PAGE_STATE; one RULES_FAULT; one local sound's OBJECT. The engine produces them (`cargo xtask`), and the engine's, the server's and the browser's tests each check their own code against the same file.
- **Reason and source.** The existing practice (DEC-6462 item 5).
- **Verification.** The three repositories' vector tests.

Numbers RULE-86 to RULE-89 are not used.

## 14. The demonstration: the music player

**RULE-90 [neoteletext-server-channel-musicplayer]. A new channel.**
- **Statement.** A new repository, `neoteletext-server-channel-musicplayer`, MUST hold a channel written in TypeScript on the TypeScript kit, as `neoteletext-server-channel-audiodemo` is, served by the deployed server in the folder `musicplayer` (so at `https://app.neottx.com/musicplayer/`), with the `channels.json` entry `{"folder":"musicplayer","name":"Music player","command":["node","src/main.ts"],"directory":"current/neoteletext-server-channel-musicplayer"}` and no `default_rules`, so that every input it receives is one its own tables ask for. It keeps a `CLAUDE.md` importing DEVELOPMENT.md, a `README.md`, `BUILD.md` and `DEPLOYMENT.md`, and the shared gates.
- **Reason and source.** The owner, 18 November 2026: "A MUSIC PLAYER THAT SHOWS SYNTHESIZERS INSTANTLY PLAYING ON A KEYPRESS AND INSTANTLY DISPLAYING LEVELS VISUALLY ALSO IN RESPONSE TO THE KEYPRESS".
- **Verification.** The channel's gate; the deployment's smoke test fetches its index page.

**RULE-91 [neoteletext-server-channel-musicplayer]. Its pages.**
- **Statement.** The channel has these pages:

| Page | What it is |
|---|---|
| 100 | The index: a teletext page naming the six instruments, each a link to its page. It has a table with no rules, so nothing typed on it is sent |
| 101 | synth106 |
| 102 | synth7 |
| 103 | synthD |
| 104 | synth53 |
| 105 | synth8 |
| 106 | synth80 |
| 111 | The teletext variant of page 101 (RULE-94) |

- Pages 101 to 106 are each a ReGIS picture over a teletext page whose Fastext row is drawn beneath it (the browser's REQ-6379): red the previous instrument, green the next, yellow the index, blue page 111. Each has one local sound of its instrument: handle 1 on audio channel 0, with one bank (handle 2) of four patches chosen from the instrument's own bank for contrast, programs 0 to 3. When a connection selects one of these pages the program sends, in a frame (ANIM-2): the bank, the local sound with a setup of program change 0, the picture, and the page's table. It sends nothing more while the viewer plays: every note and every change of the picture is the receiver's.
- **Verification.** The channel's tests: the messages sent on selecting each page; none sent for a played key.

**RULE-92 [neoteletext-server-channel-musicplayer]. The picture.**
- **Statement.** Each instrument page's ReGIS picture (800 by 480) is built of these numbered drawings (regis-v2.md):

| Drawings | What | Layer |
|---|---|---|
| 1 | The background: the instrument's name in large text at the top, the line "PLAY: A W S E D F T G Y H U J K   SOUND: 1 2 3 4", and the meter's frame | 0 |
| 101 to 113 | The thirteen keys for notes 60 to 72 (C4 to C5), drawing `100 + note − 59`: the eight white keys (notes 60, 62, 64, 65, 67, 69, 71, 72) 64 pixels wide and 200 tall from x = 72, 66 pixels apart, top at y = 200; the five black keys (61, 63, 66, 68, 70) 40 wide and 120 tall, centred on the gaps, at a higher order. Each is labelled with its computer key. Each names its pressed look: `D(S101(A201))` and so on | 1 |
| 201 to 213 | The pressed look of each key, drawing `200 + note − 59`: the key filled in a bright colour. Hidden (`V0`), so each is drawn only as a look | 1 |
| 301 to 308 | The meter's eight segments, bottom to top, each 56 wide and 28 tall at x = 700, the lowest with its top at y = 400 and each next 36 higher; segments 1 to 5 green, 6 and 7 yellow, 8 red. Hidden (`V0`) at the start | 2 |
| 401 to 404 | The four sound names, each with a marker; hidden at the start but 401 | 2 |

- The keys' pressed looks are forced by the table's `look` actions; nothing is redrawn by the channel.
- **Verification.** The picture passes the server's ReGIS check; a golden image of each page at rest and with keys 60, 64 and 67 down and the meter at level 100, made by `regis-render` with a rule script (ANIM-18).

**RULE-93 [neoteletext-server-channel-musicplayer]. The table.**
- **Statement.** Every instrument page carries the table below. It reads no synthesizer field, so it is the same table for all six pages. It has 47 rules: for each of the thirteen keys, a `key` rule on the physical key that sends note on (velocity 100, MIDI channel 1) to audio channel 0 and forces the key's pressed look, and a `key_up` rule that sends note off and returns the look; for each of the eight meter segments, a `becomes` rule that shows it when audio channel 0's `level` reaches its threshold (4, 8, 16, 32, 64, 96, 128, 192) and one that hides it when the level falls below; for each of the number keys 1 to 4, a rule that sends the program change and shows that sound's name and hides the other three; and an `open` rule that starts the local sound. No rule has `send` or `echo`: the page sends its channel no input at all.

```json
{"type":"rules","connections":[7],"page":"101","table":{"rules":[
 {"name":"start","on":{"event":"open"},"do":[{"action":"play","channel":0,"handle":1,"generation":1,"gain":100,"fade_ms":5,"loop":false}]},
 {"name":"note60_on","on":{"event":"key","keys":[{"physical":"a"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":60,"velocity":100}},{"action":"look","target":{"object":101},"look":"pressed"}]},
 {"name":"note60_off","on":{"event":"key_up","keys":[{"physical":"a"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":60,"velocity":64}},{"action":"look","target":{"object":101},"look":"normal"}]},
 {"name":"note61_on","on":{"event":"key","keys":[{"physical":"w"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":61,"velocity":100}},{"action":"look","target":{"object":102},"look":"pressed"}]},
 {"name":"note61_off","on":{"event":"key_up","keys":[{"physical":"w"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":61,"velocity":64}},{"action":"look","target":{"object":102},"look":"normal"}]},
 {"name":"note62_on","on":{"event":"key","keys":[{"physical":"s"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":62,"velocity":100}},{"action":"look","target":{"object":103},"look":"pressed"}]},
 {"name":"note62_off","on":{"event":"key_up","keys":[{"physical":"s"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":62,"velocity":64}},{"action":"look","target":{"object":103},"look":"normal"}]},
 {"name":"note63_on","on":{"event":"key","keys":[{"physical":"e"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":63,"velocity":100}},{"action":"look","target":{"object":104},"look":"pressed"}]},
 {"name":"note63_off","on":{"event":"key_up","keys":[{"physical":"e"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":63,"velocity":64}},{"action":"look","target":{"object":104},"look":"normal"}]},
 {"name":"note64_on","on":{"event":"key","keys":[{"physical":"d"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":64,"velocity":100}},{"action":"look","target":{"object":105},"look":"pressed"}]},
 {"name":"note64_off","on":{"event":"key_up","keys":[{"physical":"d"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":64,"velocity":64}},{"action":"look","target":{"object":105},"look":"normal"}]},
 {"name":"note65_on","on":{"event":"key","keys":[{"physical":"f"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":65,"velocity":100}},{"action":"look","target":{"object":106},"look":"pressed"}]},
 {"name":"note65_off","on":{"event":"key_up","keys":[{"physical":"f"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":65,"velocity":64}},{"action":"look","target":{"object":106},"look":"normal"}]},
 {"name":"note66_on","on":{"event":"key","keys":[{"physical":"t"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":66,"velocity":100}},{"action":"look","target":{"object":107},"look":"pressed"}]},
 {"name":"note66_off","on":{"event":"key_up","keys":[{"physical":"t"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":66,"velocity":64}},{"action":"look","target":{"object":107},"look":"normal"}]},
 {"name":"note67_on","on":{"event":"key","keys":[{"physical":"g"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":67,"velocity":100}},{"action":"look","target":{"object":108},"look":"pressed"}]},
 {"name":"note67_off","on":{"event":"key_up","keys":[{"physical":"g"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":67,"velocity":64}},{"action":"look","target":{"object":108},"look":"normal"}]},
 {"name":"note68_on","on":{"event":"key","keys":[{"physical":"y"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":68,"velocity":100}},{"action":"look","target":{"object":109},"look":"pressed"}]},
 {"name":"note68_off","on":{"event":"key_up","keys":[{"physical":"y"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":68,"velocity":64}},{"action":"look","target":{"object":109},"look":"normal"}]},
 {"name":"note69_on","on":{"event":"key","keys":[{"physical":"h"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":69,"velocity":100}},{"action":"look","target":{"object":110},"look":"pressed"}]},
 {"name":"note69_off","on":{"event":"key_up","keys":[{"physical":"h"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":69,"velocity":64}},{"action":"look","target":{"object":110},"look":"normal"}]},
 {"name":"note70_on","on":{"event":"key","keys":[{"physical":"u"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":70,"velocity":100}},{"action":"look","target":{"object":111},"look":"pressed"}]},
 {"name":"note70_off","on":{"event":"key_up","keys":[{"physical":"u"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":70,"velocity":64}},{"action":"look","target":{"object":111},"look":"normal"}]},
 {"name":"note71_on","on":{"event":"key","keys":[{"physical":"j"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":71,"velocity":100}},{"action":"look","target":{"object":112},"look":"pressed"}]},
 {"name":"note71_off","on":{"event":"key_up","keys":[{"physical":"j"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":71,"velocity":64}},{"action":"look","target":{"object":112},"look":"normal"}]},
 {"name":"note72_on","on":{"event":"key","keys":[{"physical":"k"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_on","channel":1,"key":72,"velocity":100}},{"action":"look","target":{"object":113},"look":"pressed"}]},
 {"name":"note72_off","on":{"event":"key_up","keys":[{"physical":"k"}]},"do":[{"action":"midi","channel":0,"message":{"event":"note_off","channel":1,"key":72,"velocity":64}},{"action":"look","target":{"object":113},"look":"normal"}]},
 {"name":"meter1_on","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":">=","value":4}},"do":[{"action":"show","target":{"object":301}}]},
 {"name":"meter1_off","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":"<","value":4}},"do":[{"action":"hide","target":{"object":301}}]},
 {"name":"meter2_on","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":">=","value":8}},"do":[{"action":"show","target":{"object":302}}]},
 {"name":"meter2_off","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":"<","value":8}},"do":[{"action":"hide","target":{"object":302}}]},
 {"name":"meter3_on","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":">=","value":16}},"do":[{"action":"show","target":{"object":303}}]},
 {"name":"meter3_off","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":"<","value":16}},"do":[{"action":"hide","target":{"object":303}}]},
 {"name":"meter4_on","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":">=","value":32}},"do":[{"action":"show","target":{"object":304}}]},
 {"name":"meter4_off","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":"<","value":32}},"do":[{"action":"hide","target":{"object":304}}]},
 {"name":"meter5_on","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":">=","value":64}},"do":[{"action":"show","target":{"object":305}}]},
 {"name":"meter5_off","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":"<","value":64}},"do":[{"action":"hide","target":{"object":305}}]},
 {"name":"meter6_on","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":">=","value":96}},"do":[{"action":"show","target":{"object":306}}]},
 {"name":"meter6_off","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":"<","value":96}},"do":[{"action":"hide","target":{"object":306}}]},
 {"name":"meter7_on","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":">=","value":128}},"do":[{"action":"show","target":{"object":307}}]},
 {"name":"meter7_off","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":"<","value":128}},"do":[{"action":"hide","target":{"object":307}}]},
 {"name":"meter8_on","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":">=","value":192}},"do":[{"action":"show","target":{"object":308}}]},
 {"name":"meter8_off","on":{"event":"becomes","condition":{"read":{"of":"sound","channel":0,"property":"level"},"op":"<","value":192}},"do":[{"action":"hide","target":{"object":308}}]},
 {"name":"sound1","on":{"event":"key","keys":[{"char":"1"}]},"do":[{"action":"midi","channel":0,"message":{"event":"program_change","channel":1,"program":0}},{"action":"show","target":{"object":401}},{"action":"hide","target":{"object":402}},{"action":"hide","target":{"object":403}},{"action":"hide","target":{"object":404}}]},
 {"name":"sound2","on":{"event":"key","keys":[{"char":"2"}]},"do":[{"action":"midi","channel":0,"message":{"event":"program_change","channel":1,"program":1}},{"action":"hide","target":{"object":401}},{"action":"show","target":{"object":402}},{"action":"hide","target":{"object":403}},{"action":"hide","target":{"object":404}}]},
 {"name":"sound3","on":{"event":"key","keys":[{"char":"3"}]},"do":[{"action":"midi","channel":0,"message":{"event":"program_change","channel":1,"program":2}},{"action":"hide","target":{"object":401}},{"action":"hide","target":{"object":402}},{"action":"show","target":{"object":403}},{"action":"hide","target":{"object":404}}]},
 {"name":"sound4","on":{"event":"key","keys":[{"char":"4"}]},"do":[{"action":"midi","channel":0,"message":{"event":"program_change","channel":1,"program":3}},{"action":"hide","target":{"object":401}},{"action":"hide","target":{"object":402}},{"action":"hide","target":{"object":403}},{"action":"show","target":{"object":404}}]}]}}
```

(`connections` names the connection that selected the page; the program sends the same table to each.)

- **Reason and source.** The owner's demonstration; it exercises `key` and `key_up` on physical keys, `midi` on a local sound, forced looks, `becomes` on a metered value, `show` and `hide`, and `open` with `play`.
- **Verification.** The server accepts the table; the encoded record is a wire vector (RULE-85); RULE-95's test.

**RULE-94 [neoteletext-server-channel-musicplayer]. The teletext variant.**
- **Statement.** Page 111 SHOULD show the same instrument as page 101 on a plain teletext page: the thirteen keys as thirteen teletext controls on rows 12 to 17 (controls 1 to 13 in note order, each three cells wide), the meter as eight teletext sprites (ANIM-7) numbered 1 to 8, each one row of three mosaic cells, placed in a column at the right and hidden at the start. Its table is page 101's with each key's `look` action naming `{"control":n}` in place of the drawing and each meter rule naming sprite `{"object":n}`, and no rules for the sound names, which it shows as text. It is built only if the teletext sprites of animation.md are built first; it is the smallest page that exercises them.
- **Verification.** A golden image sequence made by `neottx` (ANIM-18).

**RULE-95 [neoteletext-server-channel-musicplayer; neoteletext-browser]. The end-to-end test.**
- **Statement.** A test on the private display (the browser and the server together, as the ReGIS end-to-end test runs) MUST open page 101, press and release the key A, and hold: the sound helper's test device received samples of the note within RULE-64's bound; the picture's key 101 showed its pressed look within RULE-65's bound and lost it on release; at least the lowest meter segment was shown while the note sounded and hidden within one second of its release; and the fetcher sent the channel nothing between the selection and the end of the test.
- **Verification.** It is the verification of the demonstration.

## 15. What this document decided without the owner

These are recorded in rdm as DEC-6525 of neoteletext-common, "What specifying the page rule table and the animation mechanisms decided without the owner", for the owner's confirmation. Items 17 to 27 of that decision are animation.md's.

1. **Five more triggers** than DEC-6522 item 5 lists — `text`, `move`, `wheel`, `focus`, `blur` — because REQ-6523 requires a rule for every kind of input before it can be sent, and pages use these today.
2. **Key naming** by the input protocol's three existing identities (character, named, physical), a `repeat` flag and a modifier mask; **targets** as a kind (page, control, object, rectangle) and a number, with "any" in pointer triggers only.
3. **The order's unstated steps**: `open` after the timers and before `becomes` on tick 0; frame cycling after `becomes`; `close` in a final tick of its own.
4. **Two writes in one tick** apply in order to a working copy; reads see the tick's start.
5. **`becomes` fires at opening** when its condition already holds, and again on enabling.
6. **Variables** are signed 32-bit with declared `min`, `max` and `initial`, saturating; **timers** are declared, with a page timer that is not one of the eight.
7. **`level`** is linear, 0 to 255, the peak of a tick, measured before the master volume and the mute. **Envelope position** is a stage 0 to 4 and a level 0 to 255 of the part's newest voice; for synth7, operator 1's envelope.
8. **Tracked values are read in the decoder**, from the family's tracker; only `level`, and a local sound's envelope and voice count, are metered by the sound helper.
9. **Migration by a channel-wide default table** (`default_rules: "send_all"`), set for the nine deployed channels, with the component library writing precise tables and each channel then moving to `"none"`. Considered and not chosen: the kits silently attaching a send-everything table to every page (it would hide the request inside a library, and a raw kit user could not tell); the server deriving a table from the controls a page declares (controls do not say whether a page takes typing, and ReGIS and NAPLPS pages declare none); changing every channel's program on the day of the protocol change (the most risk: one page missed is a page that stops answering).
10. **Input travels only inside RULE_EVENT** under push protocol 9, wrapping the unchanged events, and the server gives programs the unchanged `input` message with `rule`, `tick` and `target` added.
11. **The trusted core gates without reading tables**: it builds every report from its own copy of the viewer's event.
12. **Local sounds are rendered in the sound helper**, which therefore links the instruments and reads bank images, and whose level reports flow back to decoders. The residual risk is threat 8 of section 12.3. The alternative — rendering in the decoder and streaming small blocks through the trusted core — keeps the helper as it is and adds two pipe hops of samples 375 times a second and the decoder's scheduling to the delay.
13. **The synth6581 family has no local sound**, since rules send MIDI notes and that family takes register writes.
14. **REQ-1333 gains exceptions**: a rule's reports leave at the tick that evaluated them, and timer- and condition-triggered reports are allowed within `TIMED_SEND_BUDGET`.
15. **The wheel over sub-pages** goes to the page only where an enabled `wheel` rule's target is under the pointer, replacing the channel-wide `push.wheel`.
16. **The music player** has thirteen computer keys and no mouse playing, because a `press` and `release` rule for each key as well would pass 64 rules.

The amendment of 18 November 2026 for the owner's decision DEC-6580 decided these beyond its three items; they are recorded in rdm with the requirements that carry them (REQ-6526 and REQ-6535) and wait for the owner's confirmation:

17. **A tick's snapshot is taken once, at the first arrival of its interval** (RULE-7), not at the end of the tick before and not again at the tick. Every condition of a tick then reads one state however its events are timed, and the evaluator used the old way is unchanged. The cost is that a change to the world after that arrival waits one tick more.
18. **Metered values are the exception**: steps 3 to 5 read the newest report at the tick (RULE-7), so that a meter is not a tick late in exactly the intervals in which a key arrived. A level may therefore show, in a tick, the sound of a note that an event of that tick began (RULE-6).
19. **256 frames are asked for, 128 accepted** (RULE-97): DEC-6580 item 2 says "128 or 256". 256 meets the decision's 12 milliseconds and halves the audio thread's wakes against 128; a device that grants 128 is used at 128.
20. **The lock is a slew of the clock's start**, at most 100 microseconds a tick (RULE-98), so that page time follows the display's clock by up to 6 parts in a thousand; RULE-4's "never drift against real time" becomes "never skip or repeat a tick".
21. **A display that is no whole multiple of 60 is not locked to** (RULE-98): its ticks cannot all fall the same time before a frame, and RULE-65 adds one refresh period there.
22. **The fallback is reported as fault 7 with count 0** (RULE-97), the decision's "existing local-overrun fault", told from RULE-62's stop by its count; **the small buffer lingers 2 seconds** after the last local sound ends; and **the meter's bound is restated as 57 milliseconds** (RULE-65), counting the report's own interval, which the earlier 45 did not.

## 16. The rdm records

| Record | Repository | Carries |
|---|---|---|
| DEC-6522 | neoteletext-common | The owner's decision: the page rule table |
| REQ-6523 | neoteletext-common | No input is sent for a page unless its rule table asks |
| DEC-6525 | neoteletext-common | What this document and animation.md decided without the owner (awaiting confirmation) |
| DEC-6580 | neoteletext-common | The owner's decision of 18 November 2026: a key's sound actions run at once, a smaller device buffer while a local sound is open, the tick locked to the display's refresh |
| REQ-6526 | neoteletext-renderer-teletext | The crate `neoteletext-rules`: RULE-1 to RULE-22, RULE-41 to RULE-45, RULE-56, RULE-57, RULE-70, and the engine's part of RULE-96 |
| REQ-6527 | neoteletext-renderer-teletext | Readable synthesizer state and the local sound in the audio crates: RULE-28, RULE-29, RULE-31, RULE-32, RULE-60, RULE-62 |
| REQ-6528 | neoteletext-renderer-teletext | Push protocol version 9: RULE-41, RULE-46 to RULE-49, RULE-85 |
| REQ-6532 | neoteletext-app-server | Program protocol 14 for the rule table: RULE-34 to RULE-40, RULE-53, RULE-59, RULE-61 |
| REQ-6534 | neoteletext-browser | The decoder evaluates, the trusted core gates: RULE-30, RULE-33, RULE-47, RULE-48, RULE-50 to RULE-52, RULE-58, RULE-63, RULE-70 to RULE-72, RULE-80 |
| REQ-6535 | neoteletext-browser | Local sounds in the sound helper and the latency bounds: RULE-32, RULE-60, RULE-62 to RULE-66, the browser's part of RULE-96, RULE-97 and RULE-98 |
| REQ-6537 | neoteletext-server-ts-protocol | The TypeScript kit: RULE-55 (and ANIM-19) |
| REQ-6538 | neoteletext-server-channels | The Python kit: RULE-55 (and ANIM-19) |
| REQ-6539 | neoteletext-server-ts-ui-components | The component library's tables: RULE-54 |
| REQ-6540 | neoteletext-common | Security analysis applied, privacy, fuzz targets, wire vectors: RULE-80, RULE-81, RULE-83 to RULE-85 (and ANIM-23) |
| REQ-6541 | neoteletext-common, until the channel's repository is in rdm (TODO-6545) | The music player: RULE-90 to RULE-95 |
| REQ-417, REQ-661 | engine, browser | "No executable content", each amended to allow the table (RULE-82) |
| DEC-649, REQ-1384, REQ-4112, REQ-1333 | engine, browser, common | Amended on 18 November 2026 by DEC-6522 and REQ-6523 |
| TODO-6542 | neoteletext-common | Restate the remaining input requirements and write the protocol's documentation items |
| TODO-6544 | neoteletext-common | Move each deployed channel to tables of its own, then delete the default table |

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
