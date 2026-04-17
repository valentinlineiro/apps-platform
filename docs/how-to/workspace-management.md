22---
id: DOC-HT-002
title: Workspace Management (Nx)
audience: [human, ai]
last_updated: 2026-04-17
tags: [how-to, nx, workspace, tasks, generators]
source_of_truth: true
related: [DOC-QS-001, DOC-HT-001]
---

# Workspace Management (Nx)

## Purpose
Define the standard procedures for managing the monorepo, running tasks, and scaffolding code using Nx.

## When to use
Consult these guidelines before running builds, tests, or linters, and whenever you need to generate new applications or libraries.

## Content

### General Guidelines
- **Task Execution**: Always prefer running tasks through `nx` (e.g., `nx run`, `nx run-many`, `nx affected`) instead of calling underlying tools directly.
- **Package Manager**: Prefix `nx` commands with the workspace's package manager (e.g., `pnpm nx build`, `npm exec nx test`) to avoid using global CLI versions.
- **Tooling Discovery**: Use the `nx-workspace` skill or the Nx MCP server to explore projects, targets, and dependencies.
- **Plugin Best Practices**: Check `node_modules/@nx/<plugin>/PLUGIN.md` for specific plugin documentation when available.
- **CLI Flags**: Never guess flags; always check `nx_docs` or use the `--help` flag.

### Scaffolding & Generators
- **Custom Generators**: Always invoke the `nx-generate` skill first when scaffolding new apps, libs, or project structures.
- **Discovery**: The `nx-generate` skill handles generator discovery internally. Use it before attempting manual exploration.

### Tool Selection (AI Agents)
- **`nx_docs`**: Use for advanced configuration, migration guides, and edge cases.
- **Standard Commands**: Do not use `nx_docs` for basic syntax or standard commands that are already well-documented in this workspace.

## References
- [Nx Documentation](https://nx.dev)
- [Project Setup](../quickstart/setup.md)

## Change log
- **2026-04-17**: Centralized Nx guidelines from tool-specific configuration files.
