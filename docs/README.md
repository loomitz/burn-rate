# Burn Rate Internal Wiki

This folder is the source of truth for how Burn Rate works. Every agentic change must update the relevant document and add a dated entry to `agent-history.md`.

## Index

- `product.md`: product scope, principles, and explicit non-goals.
- `domain.md`: business concepts and calculation rules.
- `architecture.md`: monorepo structure, backend/frontend responsibilities, and data flow.
- `api.md`: current API contract.
- `docker-hub-overview.md`: Spanish Docker Hub overview ready to publish.
- `agent-history.md`: chronological implementation history.
- `decisions/`: architecture decision records.

## Change Rule

For every functional change:

1. Update the domain, API, architecture, or product document affected by the change.
2. Add a new entry to `agent-history.md`.
3. Record tests or checks that were run.
