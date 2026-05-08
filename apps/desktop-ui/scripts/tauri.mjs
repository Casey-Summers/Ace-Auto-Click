import { spawn } from "node:child_process";
import { homedir, platform } from "node:os";
import { join } from "node:path";

function defaultCargoTargetDir() {
  if (platform() === "win32") {
    return join(
      process.env.LOCALAPPDATA || join(homedir(), "AppData", "Local"),
      "AceAutoClick",
      "cargo-target"
    );
  }
  if (platform() === "darwin") {
    return join(homedir(), "Library", "Caches", "AceAutoClick", "cargo-target");
  }
  return join(process.env.XDG_CACHE_HOME || join(homedir(), ".cache"), "ace-auto-click", "cargo-target");
}

const env = {
  ...process.env,
  CARGO_TARGET_DIR: process.env.CARGO_TARGET_DIR || defaultCargoTargetDir()
};

const child = spawn(process.execPath, [join("node_modules", "@tauri-apps", "cli", "tauri.js"), ...process.argv.slice(2)], {
  cwd: process.cwd(),
  env,
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
