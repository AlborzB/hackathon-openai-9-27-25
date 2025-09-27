Wireframes (Textual)

Top Bar
- [Project: payments-rollout]  [Search…]  [Status: Running]

Layout
- Sidebar (left, 280px)
  - Contexts
    - payments-rollout (active)
    - hackathon-9-27
  - Agents (5)
    - Riley (dev)
    - Kai (qa)
    - Zo (sre)
  - Filters
    - Type: decision | incident | progress | task | handoff
    - Repo: org/api | org/web
    - Tags: epic:payments, adr:17, sev:2

- Main Stream (center)
  - [User] “Build auth redirect fix” (timestamp)
  - [Agent Riley] “Plan: add state param, update tests”
  - [Memory] type:progress tags:[auth, bugfix]
    - “Auth flow patched; added state param and tests”
    - refs: file src/auth/redirect.ts
  - [Task Update] task:task_ab12 → done
  - [Handoff] to: Kai — “QA checklist pending” next: “Deploy to staging, run smoke suite”

- Right Panel (contextual)
  - Selected: Memory mem_4821
  - Text, tags, refs list (clickable)
  - Related: 3 items with matching tags
  - Actions: Filter by tag, Copy link, Open in repo

Bottom Composer
- [ /assign @kai ] [ message input … ] [ Attach ] [ Send ]

