#!/usr/bin/env node

const { run } = require("../src/cli");

const code = run(process.argv.slice(2));
if (code !== 0) {
  process.exitCode = code;
}
