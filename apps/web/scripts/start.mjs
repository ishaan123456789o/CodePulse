import { cpSync, existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
// Next standalone output intentionally omits static assets; include them for local startup.
if (!existsSync(".next/standalone/server.js"))
  throw new Error("Run npm run build first");
mkdirSync(".next/standalone/.next", { recursive: true });
cpSync(".next/static", ".next/standalone/.next/static", { recursive: true });
const child = spawn(process.execPath, [".next/standalone/server.js"], {
  stdio: "inherit",
  env: { ...process.env, HOSTNAME: process.env.HOSTNAME || "127.0.0.1" },
});
for (const signal of ["SIGTERM", "SIGINT"])
  process.on(signal, () => child.kill(signal));
child.on("exit", (code) => process.exit(code || 0));
