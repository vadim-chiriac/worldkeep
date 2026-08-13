# Configuration

There are two configuration files, both optional, both beside your world.
`scribe.yaml` decides how often you are consulted. `world.yaml` declares what
the world is and which specification it was written against.

Neither needs touching to start. The defaults are the cautious ones.

---

## `scribe.yaml` — how often you are asked

```yaml
approval: strict         # strict | material_only | deferred
prose: compose           # compose | quote | none
types: ask               # existing_only | ask | free
extraction: eager        # eager | stated_only
bundles: full            # full | terse | none
```

Those are the defaults; the file only needs the lines you are changing. The
session report states the effective settings and where each came from, so you
never have to guess whether a file is being read:

```
scribe:    approval=strict, prose=compose, types=ask, extraction=eager,
           bundles=full  [scribe.yaml]
```

### `approval` — what reaches canon without you

| value | behaviour |
|---|---|
| `strict` | nothing becomes canon without your word. The default. |
| `material_only` | routine capture goes straight to canon; you are still stopped for new vocabulary, contradictions, `fiat`, and deletions |
| `deferred` | everything is captured silently as drafts and nothing is presented until you ask, or the session ends |

`material_only` is the setting most people reach for second. It keeps the gate
exactly where it earns its cost — on decisions about vocabulary and on things
the agent noticed were in tension — and takes it off the long middle stretch
where you are just describing a place and it is just writing it down.

`deferred` is for thinking out loud. Nothing interrupts, and you review the
whole session at the end. The risk is the obvious one: an hour of drafts is
harder to review than five minutes of them.

### `prose` — whose words end up in the body

| value | behaviour |
|---|---|
| `compose` | the agent writes the body. The default. |
| `quote` | your own words, verbatim |
| `none` | empty bodies; frontmatter only |

Worth understanding, because it is the setting most likely to be wrong for you.
`compose` produces readable artifacts and is why bundles report `added prose:`
— the agent is writing, and says so. If your world's voice matters to you and
you intend to write the prose yourself, `quote` or `none` will annoy you less
than editing composed paragraphs afterwards.

### `types` — inventing vocabulary

| value | behaviour |
|---|---|
| `existing_only` | reuse only; never proposes or creates a type |
| `ask` | reuse the closest truthful existing type; propose a new one only when it earns its own file. The default. |
| `free` | same rule, but creates the type without asking |

All three reuse first. The difference is only what happens when nothing fits:
`existing_only` leaves the artifact untyped, `ask` proposes, `free` writes it.

Leaving an artifact untyped is a legitimate outcome, not a failure. A type
earns its file by being something you will use again and want to constrain or
draw; a type invented for one artifact is a label with extra steps.

### `extraction` — how much is inferred

| value | behaviour |
|---|---|
| `eager` | capture implied structure too, and surface every inference in the bundle. The default. |
| `stated_only` | capture only what you actually asserted |

`eager` is why a bundle says `inferred: population modelled as two states`. It
produces more structure than you said, and tells you where, every time.
`stated_only` is fewer files and less to review, at the cost of the structure
that makes a canon queryable later.

### `bundles` — how much the summary says

`full`, `terse`, or `none`. This affects reporting only; nothing about what is
captured or what reaches canon changes.

---

## `world.yaml` — what this world is

```yaml
kernel_version: "0.17"
name: "The Lower Fen"
calendar: ""
facets: [when, where, valence, weight, members, status, amount, fiat]
std_types: [part_of, subordinate_to, holds, opposes, participates, action,
            action/practice, period, state, precedes]
extensions:
  - scribe
# present: entities/<period>
```

**`kernel_version`** is the one that matters. It records which specification
the world was written against. When it falls behind the packaged kernel, you
are told rather than silently reinterpreted:

```
warnings (1):
  world.yaml kernel_version 0.11 != packaged KERNEL 0.17; re-read KERNEL.md
  before relying on version-specific rules
```

That is a warning, not an error — an old world still loads, validates and
renders. It means the rules may have moved underneath it. There is no migration
tooling yet, so the honest advice is a commit before you change anything.

**`name`** is what the world is called; **`calendar`** is free text you can
leave empty until your world has one, and vagueness in dates is legal
regardless.

**`facets`** and **`std_types`** declare what the world expects to be
available. They are documentation of intent rather than enforcement — adding a
type to the folder is what makes it exist.

**`present:`** is commented out in the seed and worth knowing about. Point it
at a period artifact and you have given the world a *now*, which is what lets
"currently" mean something. Without it, avoid writing `when: now` — it is a
string that will not age well.

---

## Viewer options

The viewer is configured per view rather than globally; see
[VIEWS.md](VIEWS.md). Two flags belong to rendering rather than to any view:

`--vendor` inlines the browser assets, so the file opens with no network. Use
it for anything you intend to keep or send to somebody.

`--all-views` renders every view into one document with a picker, and keeps
node positions stable as you switch, so you are comparing pictures rather than
re-reading them.

---

## Common changes

**"Stop asking me about every village."**
`approval: material_only`.

**"I want to write the prose myself."**
`prose: quote` to keep your words, or `prose: none` for empty bodies.

**"Stop inventing types."**
`types: existing_only`. Expect more untyped artifacts; that is the trade.

**"Capture everything, review at the end."**
`approval: deferred`, and expect a long review.

**"I only want what I actually said."**
`extraction: stated_only`. You will get fewer relations, and relations are
what make the canon answerable later — worth trying on one session before
committing to it.
