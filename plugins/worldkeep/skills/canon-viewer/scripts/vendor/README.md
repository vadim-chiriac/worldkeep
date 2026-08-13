# Vendored browser assets

These pinned browser distributions are inlined by `view.py --vendor` so a
generated view opens without network access:

| file | package | version | source |
|---|---|---:|---|
| `cytoscape.min.js` | cytoscape | 3.34.0 | `https://unpkg.com/cytoscape@3.34.0/dist/cytoscape.min.js` |
| `layout-base.js` | layout-base | 2.0.1 | `https://unpkg.com/layout-base@2.0.1/layout-base.js` |
| `cose-base.js` | cose-base | 2.2.0 | `https://unpkg.com/cose-base@2.2.0/cose-base.js` |
| `cytoscape-fcose.js` | cytoscape-fcose | 2.2.0 | `https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js` |
| `cytoscape-dagre.min.js` | cytoscape-dagre | 4.0.0 | `https://unpkg.com/cytoscape-dagre@4.0.0/dist/cytoscape-dagre.min.js` |

The matching package licenses are stored beside the scripts under
`vendor/licenses/`.
