#!/usr/bin/env node

/**
 * QC (Quality Control) Script
 *
 * Runs all quality checks before a build is considered ready:
 * 1. ESLint - code quality and potential bugs
 * 2. Jest tests - unit + component tests
 * 3. Webpack build - ensures both main and renderer compile
 * 4. Bundle size check - warns if bundles are too large
 *
 * Exit code 0 = all checks passed
 * Exit code 1 = one or more checks failed
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');
const PASS = '\x1b[32mPASS\x1b[0m';
const FAIL = '\x1b[31mFAIL\x1b[0m';
const WARN = '\x1b[33mWARN\x1b[0m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

let failures = 0;
const results = [];

function run(label, cmd) {
  process.stdout.write(`\n${BOLD}[QC] ${label}${RESET}\n`);
  try {
    execSync(cmd, { cwd: ROOT, stdio: 'pipe', timeout: 120000 });
    results.push({ label, status: 'pass' });
    console.log(`  ${PASS} ${label}`);
    return true;
  } catch (err) {
    failures++;
    results.push({ label, status: 'fail', output: err.stdout?.toString() || err.stderr?.toString() || '' });
    console.log(`  ${FAIL} ${label}`);
    const output = err.stdout?.toString() || err.stderr?.toString() || '';
    if (output) {
      // Show last 30 lines of output for diagnosis
      const lines = output.trim().split('\n');
      const tail = lines.slice(-30).join('\n');
      console.log(`\n${tail}\n`);
    }
    return false;
  }
}

function checkBundleSize() {
  process.stdout.write(`\n${BOLD}[QC] Bundle Size Check${RESET}\n`);
  const mainPath = path.join(ROOT, 'dist/main/main.js');
  const rendererPath = path.join(ROOT, 'dist/renderer/bundle.js');
  const MAX_MAIN_KB = 200;
  const MAX_RENDERER_KB = 500;

  let ok = true;

  if (fs.existsSync(mainPath)) {
    const sizeKB = Math.round(fs.statSync(mainPath).size / 1024);
    if (sizeKB > MAX_MAIN_KB) {
      console.log(`  ${WARN} main.js: ${sizeKB}KB (limit: ${MAX_MAIN_KB}KB)`);
    } else {
      console.log(`  ${PASS} main.js: ${sizeKB}KB`);
    }
  }

  if (fs.existsSync(rendererPath)) {
    const sizeKB = Math.round(fs.statSync(rendererPath).size / 1024);
    if (sizeKB > MAX_RENDERER_KB) {
      console.log(`  ${WARN} bundle.js: ${sizeKB}KB (limit: ${MAX_RENDERER_KB}KB)`);
    } else {
      console.log(`  ${PASS} bundle.js: ${sizeKB}KB`);
    }
  }

  results.push({ label: 'Bundle Size', status: ok ? 'pass' : 'warn' });
}

// --- Run QC Pipeline ---
console.log(`\n${BOLD}========================================`);
console.log('  Noted App - QC Pipeline');
console.log(`========================================${RESET}\n`);

// 1. Lint
run('ESLint', 'npx eslint src/ --max-warnings 10');

// 2. Tests
run('Jest Tests', 'npx jest --forceExit --no-cache');

// 3. Build
run('Webpack Build (main)', 'npx webpack --config webpack.main.config.js');
run('Webpack Build (renderer)', 'npx webpack --config webpack.renderer.config.js --mode production');

// 4. Bundle size
checkBundleSize();

// --- Summary ---
console.log(`\n${BOLD}========================================`);
console.log('  QC Summary');
console.log(`========================================${RESET}\n`);

results.forEach((r) => {
  const icon = r.status === 'pass' ? PASS : r.status === 'warn' ? WARN : FAIL;
  console.log(`  ${icon}  ${r.label}`);
});

console.log('');
if (failures > 0) {
  console.log(`${FAIL} ${failures} check(s) failed. Fix issues before shipping.\n`);
  process.exit(1);
} else {
  console.log(`${PASS} All checks passed! Ready to ship.\n`);
  process.exit(0);
}
