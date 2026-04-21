# ADR-0001: Monorepo With Django And Vue

## Status

Accepted.

## Context

Burn Rate needs a backend API, PostgreSQL storage, and a phone-friendly frontend. It is a small household app, not a multi-tenant platform.

## Decision

Use a monorepo with:

- Django and Django REST Framework for backend API and business rules.
- PostgreSQL for local durable storage.
- Vue 3, TypeScript, Vite, and Pinia for frontend.
- Versioned internal wiki in `docs/`.

## Consequences

- Backend calculations remain server-authoritative.
- The frontend stays simple and focused on capture and review.
- Future agentic changes have a documented project history to inspect before editing.

