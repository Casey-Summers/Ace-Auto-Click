import { spawn } from "node:child_process";

const DEV_URL = "http://127.0.0.1:1420";

async function isViteRunning() {
  try {
    const response = await fetch(DEV_URL, { signal: AbortSignal.timeout(700) });
    return response.ok;
  } catch {
    return false;
  }
}

if (await isViteRunning()) {
  console.log(`Reusing existing Vite dev server at ${DEV_URL}`);
  setInterval(() => undefined, 60_000);
} else {
  const child = spawn(process.execPath, [
    "node_modules/vite/bin/vite.js",
    "--host",
    "127.0.0.1",
    "--port",
    "1420",
    "--strictPort"
  ], {
    cwd: process.cwd(),
    env: process.env,
    stdio: "inherit"
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 1);
  });

  child.on("error", (error) => {
    console.error(error.message);
    process.exit(1);
  });
}
