# Contributing to the feedpak specification

Thanks for helping evolve feedpak. This repository holds a **file-format specification**, so
contributions are a little different from a normal code project: a change here is a change to
a contract that independent implementations rely on. The process below keeps the format stable
and its history clear.

## Licensing of contributions (inbound = outbound)

This repository is dual-licensed, and contributions are accepted under the license that
governs the file you touch:

- **Specification prose / documentation** (`spec/`, `*.md`) — [CC0 1.0](LICENSE). By
  contributing prose you dedicate it to the public domain.
- **Schemas, examples, reference code** (`schemas/`, `examples/`, `tools/`) —
  [MIT](LICENSE-CODE).

By opening a pull request you agree your contribution is licensed under the applicable terms
above.

## Developer Certificate of Origin (DCO)

Every commit must be signed off, certifying you have the right to submit it under the licenses
above (see [developercertificate.org](https://developercertificate.org/)):

```bash
git commit -s -m "your message"
```

This appends a `Signed-off-by: Your Name <you@example.com>` trailer. If you forget, amend with
`git commit --amend -s` (or rebase to sign off earlier commits) and force-push your branch.

## feedpak Enhancement Proposals (FEPs)

Anything that changes what a conformant pack or reader must do goes through a lightweight
proposal so the discussion and rationale are recorded.

1. **Open an issue** using the *feedpak Enhancement Proposal* [template](https://github.com/got-feedback/feedpak-spec/tree/main/.github/ISSUE_TEMPLATE). Describe the problem,
   the proposed change, the on-disk shape (manifest key and/or side-file), backward
   compatibility, and which version bump it implies (see below).
2. **Discuss.** A proposal is refined in the issue until it has a clear shape and rough
   consensus. Editorial fixes (typos, clarifications) skip this and can go straight to a PR.
3. **Land it as a PR** that updates, together:
   - the normative spec (`spec/feedpak-v1.md`),
   - the relevant JSON Schema(s) in `schemas/`,
   - an example in `examples/` that exercises the change (and still validates),
   - the `[Unreleased]` section of `CHANGELOG.md`.

A PR that changes behaviour but touches only one of those is incomplete.

### Which version bump does my change need?

Per [spec §4.2](spec/feedpak-v1.md#42-compatibility-policy):

| Your change | Bump |
|---|---|
| New **optional** manifest key or side-file; older readers keep working by ignoring it | **MINOR** |
| Wording, clarification, fixed example, metadata-only tweak | **PATCH** |
| Removes/renames/repurposes a required field, or changes existing semantics | **MAJOR** |

Prefer additive (minor) changes. If you find yourself proposing a major bump, check first
whether the goal can be met with a new optional key instead — that is almost always the better
design and is how every extension so far has shipped.

When you do bump, the version string lives in several places that **must** all match, and CI
enforces it (`tools/check_versions.py`, in the lint job): the spec header, the §4.1
`feedpak_version` example + writer-SHOULD line, the README version table and citation, the
`examples/extended.feedpak` manifest, and the newest `## [X.Y.Z]` heading in `CHANGELOG.md`.
Update them together; the guard prints exactly which one is out of step if you miss any.
(The `examples/minimal.feedpak` manifest deliberately stays at `1.0.0` and is not checked.)

## Workflow

- Never push directly to `main`. Branch, then open a PR against
  `got-feedback/feedpak-spec:main`.
- CI must pass: the reference validator runs over `examples/`, and the schemas are checked for
  validity. Run it locally first:
  ```bash
  pip install pyyaml jsonschema
  python tools/validate.py examples/minimal.feedpak examples/extended.feedpak
  ```
- Keep commits scoped; short imperative subject, a body explaining *why*, and the
  `Signed-off-by` trailer.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Questions

Not sure whether something is a bug, a clarification, or a full proposal? Open an issue and
ask — much cheaper than guessing.
