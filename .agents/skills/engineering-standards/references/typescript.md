# TypeScript defaults

Use Bun, Next.js App Router, React 19, strict TypeScript, and Pino. Default to Server Components.

- Prefer `satisfies` to `as`. Justify every `as` cast with a `// SAFETY:` comment.
- Return `Result<T, E>` from Services.
- Wire dependencies at route or page entry points.
- Use `src/{app,components,services,repositories,gateways,lib,db}/` and `[domain].service.ts`, `[domain].repository.ts`, `[provider].gateway.ts`.
- Test with Vitest and Testing Library against user-visible behavior.

Default verification: `bun run lint && bun run test`.
