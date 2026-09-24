# RealityBridge bounded action grammar — six issue/label lifecycle operations

Operations verified present on the pinned reference build (Gitea 1.24.7,
`/swagger.v1.json` served by the running instance). Verified 2026-09-21 in
Milestone A; swagger methods are lowercase in the JSON, request bodies are
inline `additionalProperties` schemas, so required fields below are the observed
creation contract (create_issue/create_label need a title/name; the rest need
the object handle).

## Grammar (V1 — the project stays at these six)

An action is one of:

```
action  := create_issue(owner, repo, title, [body])             # → issue number
         | get_issue(owner, repo, number)                        # → issue
         | edit_issue(owner, repo, number, [title, state, body]) # → issue
         | add_label(owner, repo, number, label_name)            # → label set
         | remove_label(owner, repo, number, label_id)           # → label set
         | create_label(owner, repo, name, color)                # → label
```

All arguments are synthetic (rbadmin / spec-repo / numbered titles / seeded
labels). No operation outside this set is part of the first transition
comparison; anything else must be reported `unsupported`, never emulated.

## State (the projection's model of the world)

```
state := { open_issues: map[number] -> issue,
           labels:      map[name] -> {name, color, id} }
issue := { number, title, body, state: open|closed, labels: set[name] }
```

Observable per step (after each action, read back that issue):
- for create_issue / edit_issue / get_issue: the issue projection
- for add/remove_label: the issue's label set
- for create_label: the label

## Preconditions and invalids (the permission/lifecycle surface)

| Case | Semantics |
|---|---|
| create_issue without required title | 422 validation_conflict |
| get_issue on absent number | 404 not_found |
| edit_issue on absent number | 404 not_found |
| edit_issue closing an already-closed issue | no-op (idempotent) or ok |
| add_label with a label that does not exist | 404 not_found |
| add_label with a label the issue already has | no-op (no duplicate) |
| remove_label with a label not on the issue | 404 not_found |
| any write as a principal without permission | 403 permission_denied |

These exact rules are the comparison surface: the simulator must reproduce them
or report `undetermined` — never merge them.

## Reset contract

`reset()` must produce a state identical to a fresh seeded reference: repo
`spec-repo`, labels `{bug, ui, api}`, two issues (`issue-one` with `bug`,
`issue-two` empty). A failed reset invalidates the paired trial; it is not a
simulator failure.