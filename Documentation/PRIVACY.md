# Privacy policy

Effective: 15 August 2026

Worldkeep is a local-first, open-source plugin. It has no Worldkeep-operated
server, user account, telemetry, analytics, advertising, or background data
collection.

## What Worldkeep stores

Worldkeep stores the worlds you create as Markdown and YAML files on the file
system you choose. Its local scripts read and modify those files only when you
or your AI agent run them. Worldkeep does not upload the files to a Worldkeep
service because no such service exists.

You control these files. You can inspect, copy, version, or delete them with
ordinary file-system and Git tools.

## Processing by an AI host

Worldkeep runs inside a supported AI host such as Claude or ChatGPT/Codex.
Prompts you send to that host, and canon content the host reads in order to
help you, may be processed by Anthropic or OpenAI under that provider's terms
and privacy policy. Worldkeep does not control that processing.

Do not give an AI host material you are not permitted or willing to have that
provider process. A Worldkeep canon remains readable and editable without an
AI agent, and the validator and viewer can be run as local scripts.

## Viewer network access

A viewer generated with the `--vendor` option contains its browser libraries
in the resulting HTML file and can be opened without network access. A
non-vendored viewer may load browser libraries from a third-party content
delivery network. Canon content is not intentionally sent to that network,
but the network request is governed by the third party's own privacy policy.

## Support and public contributions

If you open a GitHub issue, discussion, or pull request, any information you
choose to include is processed and displayed by GitHub under GitHub's terms
and privacy policy. Do not attach a private canon or sensitive conversation to
a public report. Structural diagnostics and a minimal reproduction are usually
enough.

## Retention and deletion

Worldkeep has no account database and therefore no server-side retention or
deletion process. Delete local Worldkeep files using your normal file-system
tools. Requests concerning data processed by an AI host or GitHub must be
directed to that provider.

## Changes and contact

Material changes to this policy will be recorded in the project changelog.
Questions can be raised through the
[Worldkeep issue tracker](https://github.com/vadim-chiriac/worldkeep/issues).

