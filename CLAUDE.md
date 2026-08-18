# CLAUDE.md

This file provides guidance for AI assistants working in this repository.

## Repository Overview

- **Repository**: dextrayao/yao
- **Status**: New project (initial setup)
- **Primary branch**: `main`

## Project Structure

As the project grows, document the directory layout here.

- `hermes-imac/` — Setup scripts and guide for connecting Hermes Agent to an iMac over SSH (LAN or Tailscale) to read and fetch files.

<!--
Example (update when applicable):
```
├── src/          # Source code
├── tests/        # Test suite
├── docs/         # Documentation
├── scripts/      # Build and utility scripts
└── ...
```
-->

## Development Workflow

### Getting Started

1. Clone the repository
2. Check the project's language-specific setup instructions (e.g., `package.json`, `go.mod`, `requirements.txt`) once added

### Branching

- Use feature branches for development
- Branch naming: `feature/<description>`, `fix/<description>`, `docs/<description>`

### Commits

- Write clear, concise commit messages
- Use conventional commit style: `type: short description`
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Keep commits focused on a single logical change

### Testing

- Run the full test suite before pushing changes
- Add tests for new functionality and bug fixes

## Coding Conventions

- Follow the language's standard style guide and formatting tools
- Prefer clarity over cleverness
- Keep functions small and focused
- Name variables and functions descriptively

## AI Assistant Guidelines

- **Read before editing**: Always read existing code before proposing changes
- **Minimal changes**: Only modify what's necessary to accomplish the task
- **Don't over-engineer**: Avoid adding abstractions, features, or error handling beyond what's requested
- **Respect existing patterns**: Match the style and conventions already present in the codebase
- **Test your changes**: Run relevant tests after making modifications
- **No unnecessary files**: Don't create documentation, config files, or helpers unless explicitly requested
