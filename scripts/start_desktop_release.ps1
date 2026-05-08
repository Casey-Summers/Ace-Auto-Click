$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$targetRoot = if ($env:CARGO_TARGET_DIR) {
  $env:CARGO_TARGET_DIR
} else {
  Join-Path $env:LOCALAPPDATA "AceAutoClick\cargo-target"
}

$exe = Get-ChildItem -Path (Join-Path $targetRoot "release") -Recurse -Filter "ace-auto-click.exe" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if (-not $exe) {
  throw "Release executable not found. Run: npm.cmd --prefix apps/desktop-ui run tauri build"
}

Start-Process -FilePath $exe.FullName -WorkingDirectory $root
