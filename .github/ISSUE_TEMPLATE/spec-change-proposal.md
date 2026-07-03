---
name: feedpak Enhancement Proposal (FEP)
about: Propose a change or addition to the feedpak format
title: "[FEP] <short title>"
labels: ["proposal"]
---

<!--
See CONTRIBUTING.md for the full process. In short: describe the change and its on-disk
shape here, reach rough consensus, then land it as a PR that updates the spec, the schema(s),
an example, and the CHANGELOG together.
-->

## Summary

<!--
Your elevator pitch: in a sentence or two, and in your own words, say what changes and why it
matters — enough that a reader gets the gist before the detail below. Keep it tight; a wall of
generated text buries the point instead of making it.
-->

## Problem / motivation

What can't be expressed today, or what is awkward? Who needs this?

## Proposed change

What you want to add or change. Be concrete about the **on-disk shape**:

- New / changed **manifest key**(s):
- New / changed **side-file** and its schema:
- Example snippet:

```yaml
# manifest fragment
```

```json
// side-file fragment
```

## Backward compatibility

- How does an **older reader** behave when it sees a pack using this? (It should ignore the
  new optional key/file and still load.)
- Does this remove, rename, or repurpose any existing field? (If so, it's a MAJOR change —
  explain why it's necessary.)

## Version impact

Which bump does this imply, per [spec §4.2](../../spec/feedpak-v1.md#42-compatibility-policy)?

- [ ] PATCH — wording / clarification / metadata only
- [ ] MINOR — new optional key or side-file; older readers unaffected
- [ ] MAJOR — breaking change to required structure or semantics

## Alternatives considered

Other shapes you weighed, and why this one. (In particular: could a new *optional* key avoid a
breaking change?)
