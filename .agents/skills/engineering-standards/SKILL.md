---
name: engineering-standards
description: Apply personal engineering defaults when designing, implementing, refactoring, or reviewing code. Covers architecture, testing, and observability. Skip for prose-only edits and general discussion unrelated to code design.
---

# Engineering standards

Read the project's instructions, configuration, and nearby code first. Established project conventions take precedence; apply these defaults where the project leaves a choice open. Read only the language references relevant to the task:

- [TypeScript](references/typescript.md) for frontend and TypeScript code.
- [Go](references/go.md) for Go services.
- [Python](references/python.md) for Python services and data work.

Find actual versions, commands, and paths in the project. For a new database, prefer PostgreSQL on Neon or Railway.

## Architecture

Route requests through a Handler, a Service, and a Repository or Gateway before I/O.

| Layer | Responsibility | Dependencies |
|---|---|---|
| Handler | Parse HTTP, authenticate, map domain results to API DTOs | Service interfaces |
| Service | Business rules, orchestration, transaction boundaries | Repository and Gateway interfaces, Domain |
| Repository | Internal database persistence | Database client, Domain |
| Gateway | External APIs, SDKs, queues | External clients, Domain |
| Domain | Types, value objects, sentinel errors | Standard library |

- Define the Service interface the Handler needs first. Inject concrete implementations at the composition root.
- Services own transactions; repositories receive transaction handles. Repositories do not call other repositories, and gateways do not call other gateways.
- Gateways return domain types and make external mutations idempotent. Keep vendor types inside gateways and API DTOs inside handlers.
- Return errors as values in Services and below. Reserve thrown or panicked errors for the Handler boundary.
- One LLM gateway owns LLM instrumentation. Services do not import Langfuse or LangSmith.
- Preserve generated files; change their source and regenerate.
- Wait until the third duplication before introducing an abstraction.

Name service and repository files by domain, such as `orders.service.ts` and `orders.repository.ts`. Name gateways by provider, such as `stripe.gateway.ts`. Use the language's file conventions from its reference.

## Testing

Use the project's configured checks; language references provide defaults when none are documented.

- Enforce at least 80% line coverage in CI.
- Test behavior through public interfaces. Mock only Repository and Gateway boundaries, never the subject or language primitives.
- Use Arrange, Act, Assert with one Act per test and behavior-based names.
- Fix or delete flaky tests within 24 hours.
- Exercise UI changes in the browser and review security-sensitive paths explicitly.

## Observability

- Use one structured JSON logger per process. Redact PII in logger configuration.
- Create a request ID in middleware. Propagate it through child loggers and outbound `X-Request-Id` headers.
- Use OpenTelemetry auto-instrumentation for HTTP and database calls. Limit manual spans to the LLM gateway and business-critical Service methods, applying the Rule of Three.
- Record tokens and cost for every LLM generation.
