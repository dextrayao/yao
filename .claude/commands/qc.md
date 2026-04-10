Run the full QC (Quality Control) pipeline for the Noted app before delivering any code.

## Steps

1. **Run the QC script**: Execute `npm run qc` in the project root. This runs:
   - **ESLint** — code quality and potential bugs
   - **Jest Tests** — unit tests (database, Claude API) + component tests (Sidebar, Capture, Ask, Settings)
   - **Webpack Build (main)** — Electron main process compiles cleanly
   - **Webpack Build (renderer)** — React renderer compiles cleanly
   - **Bundle Size Check** — main.js < 200KB, bundle.js < 500KB

2. **Analyze results**: If any check fails:
   - Read the error output carefully
   - Fix the root cause (don't just suppress errors)
   - Re-run `npm run qc` until ALL checks pass

3. **Report**: After all checks pass, show a summary table of results to the user.

## Rules

- **NEVER** skip a failing check — fix it first
- **NEVER** commit code that hasn't passed QC
- If a test fails, read the test file and the source file, understand the failure, then fix
- If ESLint fails, fix the lint issue in the source, not by disabling the rule
- If build fails, check for syntax errors or missing imports
- After fixing, always re-run the full `npm run qc` to confirm everything passes together
