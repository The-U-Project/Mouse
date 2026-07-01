---
name: mouse-release
description: Update README.md from the current project state, commit, push, and create a PR on the GitHub repository (The-U-Project/Mouse). Use this when the user wants to release changes, update docs, or submit a pull request upstream.
---

# Mouse Release — Update Docs & Create PR

Use this skill when the user wants to:
- Update `README.md` (and optionally `GETTING_STARTED.md`) to reflect the current state of the project
- Commit documentation changes
- Push to GitHub and create a Pull Request on `The-U-Project/Mouse`

## Workflow

### Step 1 — Scan the project for changes

Before touching anything, scan the project to detect what's new or changed since the last README update:

```bash
# Check git status — what files have changed?
git --no-pager status --short

# Compare README.md to HEAD to see if it's already been modified
git --no-pager diff HEAD -- README.md GETTING_STARTED.md

# List new top-level directories/files not reflected in README
ls -1 | while read f; do
  if ! grep -q "$f" README.md 2>/dev/null; then
    echo "NEW: $f"
  fi
done
```

Also scan for:
- **New source files** — any new subdirectories under `src/`, `Source/`?
- **New skills** — `ls .agents/skills/` and compare with README
- **New profiles** — any new `AGENT_PROFILE.md` or `AI/` files?
- **Tech stack changes** — new languages, tools, or dependencies?
- **Build status changes** — is the project now building successfully?

### Step 2 — Present findings to the user

Report what you found:

> "Here's what I detected that should be updated in README.md:"
> "  - New directory: `scripts/`"
> "  - New skill: `mouse-release`"
> "  - Rust now building ✅"
>
> "Should I update README.md with these changes? Any other sections you'd like to add or modify?"

**Do not proceed without user confirmation.** The user may want to tweak wording or add/remove sections.

### Step 3 — Update README.md

Based on user confirmation, update `README.md`. Common updates include:

| Section | What to check |
|---------|---------------|
| **Supported Systems** | Any new OS/GPU combos? Status changes (🚧 → ✅)? |
| **Tech Stack** | New languages? Status changes? Version bumps? |
| **Project Structure** | New directories? Missing directories? |
| **Getting Started** | Point to `GETTING_STARTED.md` if not already linked |
| **Skills / Tools** | List project-local Zed skills (`.agents/skills/`) |
| **Build Status** | If CI exists, add badges; otherwise a manual checklist |

Also update `GETTING_STARTED.md` if the build commands, prerequisites, or workflows have changed.

### Step 4 — Commit the changes

Once the user approves the README updates:

```bash
# Stage the doc files
git add README.md GETTING_STARTED.md

# Commit with a conventional commit message
git commit -m "docs: update README and getting-started for <brief summary of changes>"
```

Ask the user for the specific commit message, or generate one from the detected changes.

### Step 5 — Push and create PR

#### 5a. Check remote

```bash
git remote -v
```

The remote should be `origin` → `https://github.com/The-U-Project/Mouse.git`.

#### 5b. Determine branch strategy

Ask the user:

> "Should I push directly to `main`, or create a feature branch (e.g., `docs/update-readme`) and open a PR?"

If the user wants a PR:

```bash
# Create and switch to a new branch
git checkout -b docs/update-readme-$(date +%Y%m%d)

# Push the branch
git push -u origin docs/update-readme-$(date +%Y%m%d)
```

If pushing directly to `main`:

```bash
git push origin main
```

#### 5c. Create the PR (if on a branch)

Use the GitHub CLI:

```bash
gh pr create \
  --title "docs: update README and getting-started" \
  --body "$(cat <<'EOF'
## Summary

Updated project documentation to reflect the current state:

- **README.md:** <list specific changes>
- **GETTING_STARTED.md:** <list specific changes, if any>

## Checklist

- [x] README.md updated
- [x] Project structure section current
- [x] Supported systems table current
- [x] Tech stack table current

EOF
)" \
  --base main
```

If `gh` is not installed or not authenticated, tell the user:

> "GitHub CLI (`gh`) is not available. I pushed the branch `docs/update-readme-YYYYMMDD` to origin. Please create the PR manually at:"
> `https://github.com/The-U-Project/Mouse/compare/main...docs/update-readme-YYYYMMDD`

#### 5d. Alternative: manual PR instructions

If the user prefers not to use `gh`, provide the direct URL:

> "Open this URL to create a PR:"
> `https://github.com/The-U-Project/Mouse/compare/main...docs/update-readme-YYYYMMDD?quick_pull=1`

### Step 6 — Report results

After everything is done, summarize:

```markdown
## Release Complete ✅

- **Branch:** `docs/update-readme-YYYYMMDD`
- **Commit:** `abc1234 — docs: update README and getting-started`
- **PR:** `https://github.com/The-U-Project/Mouse/pull/1`

### Changes
- Updated README.md: added X, fixed Y, refreshed Z
- Updated GETTING_STARTED.md: …

### Next steps
- Wait for PR review
- Merge when approved
- Delete the feature branch after merge
```

## Important Notes

- **Always ask before modifying files** — the user may have uncommitted changes.
- **Don't force-push** — never use `--force` unless the user explicitly requests it.
- **Check for uncommitted work** — `git --no-pager stash list` and `git --no-pager status` before branching.
- **Respect the user's commit style** — use conventional commits (`docs:`, `feat:`, `fix:`) per the project's `AGENT_PROFILE.md`.
- **If the remote is inaccessible** (no network, auth issues), push is the last step — the local commit is still valuable.
