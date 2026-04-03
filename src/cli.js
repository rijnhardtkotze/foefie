const OPENING = "What decision are you sitting with?";

function sanitize(text) {
  return String(text ?? "").trim();
}

function buildDecisionSummary(input) {
  const decision = sanitize(input.decision);
  const leaning = sanitize(input.leaning);
  const risk = sanitize(input.risk);

  if (!decision || !leaning || !risk) {
    throw new Error("decision, leaning, and risk are required");
  }

  return [
    `Decision: ${decision}`,
    `Leaning toward: ${leaning}`,
    `Risk already identified: ${risk}`
  ].join("\n\n");
}

function parseFlags(argv) {
  const args = Array.isArray(argv) ? argv : [];
  const out = {};

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") out.help = true;
    if (arg === "--decision" || arg === "--leaning" || arg === "--risk") {
      const value = args[i + 1];
      if (value === undefined || value.startsWith("--")) {
        throw new Error(`Missing value for ${arg}`);
      }
      if (arg === "--decision") out.decision = value;
      if (arg === "--leaning") out.leaning = value;
      if (arg === "--risk") out.risk = value;
      i += 1;
    }
  }

  return out;
}

function usage() {
  return [
    "foefie challenge",
    "",
    `Opening: ${OPENING}`,
    "",
    "Usage:",
    "  foefie challenge --decision \"...\" --leaning \"...\" --risk \"...\"",
    "",
    "Flags:",
    "  --decision  The decision the user is about to make",
    "  --leaning   What they are leaning toward",
    "  --risk      What they think the main risk is"
  ].join("\n");
}

function run(argv, io = { stdout: process.stdout, stderr: process.stderr }) {
  const [command, ...rest] = Array.isArray(argv) ? argv : [];

  if (!command || command === "--help" || command === "-h") {
    io.stdout.write(`${usage()}\n`);
    return 0;
  }

  if (command !== "challenge") {
    io.stderr.write(`Unknown command: ${command}\n`);
    io.stderr.write(`${usage()}\n`);
    return 1;
  }

  const flags = parseFlags(rest);
  if (flags.help) {
    io.stdout.write(`${usage()}\n`);
    return 0;
  }

  try {
    const summary = buildDecisionSummary(flags);
    io.stdout.write(`${summary}\n`);
    return 0;
  } catch (error) {
    io.stderr.write(`${error.message}\n`);
    io.stderr.write(`${usage()}\n`);
    return 1;
  }
}

module.exports = {
  OPENING,
  buildDecisionSummary,
  parseFlags,
  usage,
  run
};
