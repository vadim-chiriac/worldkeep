# Viewer guide

Worldkeep turns a canon folder into an interactive graph delivered as one
self-contained HTML file. It opens in an ordinary browser, needs no network,
and does not change the canon it displays.

Most people use it by asking the agent:

> Show me my world.

That opens one document containing the built-in views and every custom view
saved with the world. This guide explains what you can do inside that document.
For the YAML behind saved views, see [VIEWS.md](VIEWS.md).

## The three parts of the screen

The left panel chooses a view and contains search, temporary type filters, and
the generated legend. The graph is in the centre. Clicking anything opens its
canon details and relations in the inspector on the right.

![Everything shows the whole active canon with neutral styling, temporary
filters on the left, and the selected artifact in the inspector.](assets/viewer-everything.png)

You can:

- drag the background to pan and scroll to zoom;
- click a node, relation node, or edge to inspect it;
- click a relation card or one of its visible participants to navigate;
- expand **Frontmatter** when you need the structured source rather than the
  readable summary.

The inspector groups connections into one card per relation. Each card keeps
the relation's member order and role names, marks the selected item as
**This artifact**, and tells you when another participant is not present in the
active view.

## Find and filter without changing canon

**Find by name** searches artifact names, ids, and types. Matches are listed and
can be highlighted in the graph. The highlight control lets you keep the result
list without dimming the rest of the graph; clearing the query clears the list.

**Filter this view** temporarily hides whole artifact or relation types. The
counts above the filters say how much of the current view remains visible.
**None** clears every type and **All / Reset** restores them. Filtering also
removes relations that can no longer be drawn completely, but it never edits a
view recipe or canon file.

Known node positions and the current pan and zoom are retained while filtering,
so restoring a type does not produce a completely new layout.

## `Everything` and saved views

`Everything` is the neutral audit view. It always exists and shows every active
canon or draft artifact that can be safely rendered. It deliberately ignores
custom selection, styles, emphasis, and relation lenses. Standard directions
and structured state values remain visible because they make the raw graph
readable without turning it into an interpretation.

Use it to answer: *is this fact absent from the world, or only absent from my
custom view?*

A saved view is an interpretation: it chooses what belongs in the picture and
may change layout, colours, shapes, directions, or containment. The Lower Fen
view below selects only the relation families needed to read its bell dispute.

![A saved custom view makes one argument about the same canon: doctrines,
communities, practices, and nested places are arranged for this reading.](assets/viewer-custom-view.png)

Worldkeep also ships two small defaults with a new world:

- **Canon only** removes drafts;
- **Groups** shows members of the standard containment, membership,
  participation, and command relation families.

If a world's groups use custom relation types, ask the agent for a custom view
rather than expecting the default Groups recipe to guess their meaning.

## Focus on one local question

The graph can be temporarily reduced without writing a new view:

- **Focus relation** keeps one relation and its direct participants;
- **Focus neighborhood** keeps one artifact, its direct relations, and all
  participants in those relations.

Focus is deliberately one hop. It honours the active view and current filters,
does not traverse the whole canon, and cannot reveal artifacts the view
excluded. **Clear** appears beside the focus summary in the right inspector;
switching views also clears focus.

![Relation focus isolates one statement and its participants while keeping the
relation's roles readable in the inspector.](assets/viewer-focus.png)

Focus is a reading aid, not a saved view. Ask the agent to create and validate a
named view when the same question should be reusable later.

## Read the generated legend

Expand **Shown in this view** at the bottom of the left panel. The legend is
generated from what is currently rendered, including filters and focus. It
lists the node shapes, colours, relation lines, directions, and counts actually
on screen.

![The expanded legend describes the final visual marks in the current custom
view.](assets/viewer-legend.png)

The legend says *what is drawn*, not *why a rule chose that appearance*.
Colours in a custom view remain presentation, not canon facts. Use view
validation and explanation when you need the module or rule responsible for a
style.

## Ask for a custom view

Natural-language requests are the normal interface:

> Show only the religious conflicts.

> Show the cities, who governs each one, and where they sit.

> Give the rival factions distinct colours and keep districts inside their
> regions.

The agent separates such a request into reusable concerns: artifact selection,
relation policy, style, and relation lens. It previews and validates the result
before saving durable files under `views/` and, where useful,
`view-modules/`. Built-in `Everything` remains unchanged.

For the complete view schema, composition rules, validation, explanations, and
locks, continue with [VIEWS.md](VIEWS.md).

## Current boundaries

- The viewer is a semantic graph, not a geographic map.
- Large worlds remain complete in Everything but naturally become busy; use
  filters, focus, and saved views for particular questions.
- Layout is automatic. It preserves positions during browser-session filters,
  but canon or view changes can produce a new arrangement after rerendering.
- A custom view is only as complete as its explicit selection and relation
  rules. Check it against Everything when completeness matters.

See [LIMITATIONS.md](LIMITATIONS.md) for the current tested scale and other
first-release boundaries.
