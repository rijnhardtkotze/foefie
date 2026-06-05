const test = require("node:test");
const assert = require("node:assert/strict");
const { buildDecisionSummary, parseFlags, run, OPENING } = require("../src/cli");

test("buildDecisionSummary formats expected challenge input", () => {
  const result = buildDecisionSummary({
    decision: "Move to a new city",
    leaning: "Taking the offer because of growth opportunities",
    risk: "Losing support network"
  });

  assert.equal(
    result,
    [
      "Decision: Move to a new city",
      "",
      "Leaning toward: Taking the offer because of growth opportunities",
      "",
      "Risk already identified: Losing support network"
    ].join("\n")
  );
});

test("parseFlags extracts challenge fields", () => {
  const flags = parseFlags([
    "--decision",
    "Start a company",
    "--leaning",
    "Bootstrapping first",
    "--risk",
    "Cash flow instability"
  ]);

  assert.deepEqual(flags, {
    decision: "Start a company",
    leaning: "Bootstrapping first",
    risk: "Cash flow instability"
  });
});

test("parseFlags rejects missing flag values", () => {
  assert.throws(
    () => parseFlags(["--decision"]),
    /Missing value for --decision/
  );
});

test("parseFlags rejects unknown arguments", () => {
  assert.throws(
    () => parseFlags(["--decsion", "Start a company"]),
    /Unknown argument: --decsion/
  );
});

test("run challenge prints the summary", () => {
  let out = "";
  let err = "";
  const code = run(
    [
      "challenge",
      "--decision",
      "Buy now",
      "--leaning",
      "Buying before rates rise",
      "--risk",
      "Overextending monthly budget"
    ],
    {
      stdout: { write: (chunk) => { out += chunk; } },
      stderr: { write: (chunk) => { err += chunk; } }
    }
  );

  assert.equal(code, 0);
  assert.match(out, /Decision: Buy now/);
  assert.match(out, /Leaning toward: Buying before rates rise/);
  assert.match(out, /Risk already identified: Overextending monthly budget/);
  assert.equal(err, "");
});

test("run with no command prints usage including opening", () => {
  let out = "";
  const code = run([], {
    stdout: { write: (chunk) => { out += chunk; } },
    stderr: { write: () => {} }
  });

  assert.equal(code, 0);
  assert.equal(out.includes(`Opening: ${OPENING}`), true);
});
