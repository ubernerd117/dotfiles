# Go defaults

Use Go 1.24+, Echo v4, strict oapi-codegen, pgx, sqlc, goose, and slog.

- Treat `api/openapi.yaml` as the API source of truth. Implement the generated `ServerInterface` and register `OapiRequestValidator` middleware.
- Define interfaces at the consumer. Every I/O function takes `context.Context` first and propagates it through downstream calls.
- Keep wiring in `cmd/server/main.go`. Use `internal/{handler,service,repository,gateway,domain,platform}/` and `migrations/`. Use Go's `.go` extension with the shared file naming pattern.
- Use table-driven tests with `t.Run`, `testify/require` for preconditions, and `testify/assert` for checks. Prefer `t.Cleanup` to `defer` in tests.
- Use testcontainers-go for PostgreSQL integration tests. Run tests with `-race`.

Default verification: `go vet ./... && go test -race ./... && golangci-lint run`.
