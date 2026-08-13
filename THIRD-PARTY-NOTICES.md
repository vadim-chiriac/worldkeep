# Third-party notices

Worldkeep itself is licensed under the [MIT licence](LICENSE). It bundles the
following third-party components, each of which keeps its own licence. All of
them are likewise MIT-licensed; their copyright notices are reproduced with the
components and must be retained in any redistribution.

Everything is vendored on purpose. A rendered view has to open with no network
years from now, and the agent should never have to talk to you about installing
dependencies.

---

## PyYAML

- **Used for:** reading and writing the YAML frontmatter of every artifact, and
  the manifests, view files and view modules.
- **Bundled at:** `src/runtime/_vendor/yaml/`, copied into both skill bundles at
  `scripts/_vendor/yaml/`.
- **Licence:** MIT — full text at `src/runtime/_vendor/PyYAML-LICENSE.txt`.
- **Copyright:** © 2017–2021 Ingy döt Net; © 2006–2016 Kirill Simonov.

## Cytoscape.js

- **Used for:** graph layout and rendering inside every generated HTML view.
- **Bundled at:** `src/viewer/vendor/cytoscape.min.js`.
- **Licence:** MIT — full text at
  `src/viewer/vendor/licenses/cytoscape-LICENSE.txt`.
- **Copyright:** © 2016–2026 The Cytoscape Consortium.

## cytoscape-dagre

- **Used for:** the `dagre` layout, which ranks hierarchies top to bottom.
- **Bundled at:** `src/viewer/vendor/cytoscape-dagre.min.js`.
- **Licence:** MIT — full text at
  `src/viewer/vendor/licenses/cytoscape-dagre-LICENSE.txt`.
- **Copyright:** © 2016–2018, 2020, 2022, 2026 The Cytoscape Consortium.

## cytoscape-fcose

- **Used for:** the default `fcose` force-directed layout.
- **Bundled at:** `src/viewer/vendor/cytoscape-fcose.js`.
- **Licence:** MIT — full text at
  `src/viewer/vendor/licenses/cytoscape-fcose-LICENSE.txt`.
- **Copyright:** © 2018–present iVis-at-Bilkent.

## cose-base

- **Used for:** the layout engine `fcose` builds on.
- **Bundled at:** `src/viewer/vendor/cose-base.js`.
- **Licence:** MIT — full text at
  `src/viewer/vendor/licenses/cose-base-LICENSE.txt`.
- **Copyright:** © 2019–present iVis@Bilkent.

## layout-base

- **Used for:** shared layout primitives required by `cose-base`.
- **Bundled at:** `src/viewer/vendor/layout-base.js`.
- **Licence:** MIT — full text at
  `src/viewer/vendor/licenses/layout-base-LICENSE.txt`.
- **Copyright:** © 2019 iVis@Bilkent.
