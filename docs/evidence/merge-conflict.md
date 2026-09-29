# Deliberate merge conflict (T-M11-005, rubric A)

A conflict on real code, created on purpose and resolved by hand. This file is committed as part
of the merge commit that resolves it, on `feat/T-M11-007-ui-theme`.

## How it arose

| | Commit | Branch | Change to `frontend/src/App.tsx` |
|---|---|---|---|
| Common base | `4caf695` | `dev` (PR #15) | `<h1>Civic-Station</h1>` |
| Ours | `2194482` | `feat/T-M11-007-ui-theme` | adds the favicon logo inside the `<h1>` |
| Theirs | `d76ba4a` | `feat/T-M11-005-header-tagline`, merged to `dev` first | adds a "Complaint triage" tagline inside the same `<h1>` |

Both branches rewrote the same line of the header from the same base, so neither change could be
applied automatically after the other.

## The conflict

```
$ git checkout feat/T-M11-007-ui-theme
$ git merge origin/dev
Auto-merging frontend/src/App.tsx
CONFLICT (content): Merge conflict in frontend/src/App.tsx
Automatic merge failed; fix conflicts and then commit the result.
```

`frontend/src/App.tsx`, as git left it (the only conflicted file):

```tsx
      <header>
        <h1>
<<<<<<< HEAD (feat/T-M11-007-ui-theme, 2194482)
          <img src="/favicon.svg" alt="" />
          Civic-Station
=======
          Civic-Station <span className="muted">Complaint triage</span>
>>>>>>> origin/dev (d76ba4a)
        </h1>
```

## The resolution

```tsx
      <header>
        <h1>
          <img src="/favicon.svg" alt="" />
          Civic-Station <span className="muted">Complaint triage</span>
        </h1>
```

A first attempt at the resolution kept both sides line for line and repeated the product name
("Civic-Station Civic-Station Complaint triage"); it was caught before committing and reduced to
one name. Verified after resolving: `npm run typecheck` clean, `npx vitest run` 25 of 25 tests
passing.

## Why this version won

Neither side was wrong, so neither side "won" outright: the UI branch added the logo, `dev` added
the tagline, and both are independent additions to the same heading. Taking only ours would have
silently dropped a change that was already on `dev`; taking only theirs
would have lost the logo that the new favicon and theme work depend on. The combined heading keeps
both, with the product name once, and the tagline reuses the existing `muted` class so it follows
the light and dark themes without new CSS.
