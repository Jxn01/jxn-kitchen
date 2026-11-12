# Install or update the kiosk agent as the kiosk user's Windows shell. Run over SSH as the kiosk user (an administrator) after copying
# agent.exe to the profile:  scp agent.exe install.ps1 <user>@<kiosk>:   then   powershell -File install.ps1 [-Restart]
# A running agent.exe is locked but may be RENAMED, so an update renames it to agent.exe.prev (the rollback copy)
# and copies the new one in. -Restart then ends the running agent and starts the new one in the kiosk user's desktop session
# through the interactive scheduled task `kiosk-agent-start` (created here; /IT = runs only in the logged-on
# session, which is where the kiosk's desktop is). Its pre-launch cleanup replaces the old agent's orphaned Chrome.
# A few seconds of blank screen in the kitchen; no logoff, no reboot.
# 🚨 Winlogon does NOT restart a custom shell that is killed, AutoRestartShell=1 or not (measured 2026-10-10: the
# agent stayed gone until started by hand) — so never just Stop-Process it.
# -SelfTest (after the install, and after -Restart when both are given) runs `agent.exe -selftest-reboot` through a
# second interactive task, `kiosk-agent-selftest`, so it has exactly the agent's limited token and desktop session
# (an elevated SSH shell would prove nothing about that token), then prints its `selftest:` lines from agent.log:
# the Wi-Fi state, a scan, the idle time, and shutdown.exe scheduling a reboot in 10 min and aborting it 5 s later.
# Nothing reboots; if the abort ever failed the box would reboot 10 min later (harmless: it reboots every night).
# Revert: copy agent.exe.prev back the same way, or set the Shell value to: wscript.exe "C:\kiosk\shell.vbs"
# (the gut's fallback launcher), or delete it (= Explorer).
param([switch]$Restart, [switch]$SelfTest)
$ErrorActionPreference = 'Stop'
$src = Join-Path $env:USERPROFILE 'agent.exe'
$dst = 'C:\kiosk\agent.exe'
$prev = "$dst.prev"
if (Test-Path $dst) {
  if (Test-Path $prev) { Remove-Item $prev -Force }
  Rename-Item $dst (Split-Path $prev -Leaf)      # works while it runs; Copy-Item over it would not
}
Copy-Item $src $dst -Force
$key = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Winlogon'
$before = (Get-ItemProperty $key -Name Shell -ErrorAction SilentlyContinue).Shell
Set-ItemProperty $key -Name Shell -Value $dst
"shell: '$before' -> '$((Get-ItemProperty $key -Name Shell).Shell)'"
"agent: $((Get-Item $dst).Length) bytes (previous kept as agent.exe.prev)"
if ($Restart) {
  schtasks /Create /TN kiosk-agent-start /TR $dst /SC ONCE /ST 00:00 /SD 01/01/2030 /RU $env:USERNAME /IT /F | Out-Null
  $old = Get-Process agent -EA SilentlyContinue | Where-Object { $_.Path -eq $prev -or $_.Path -eq $dst }
  $old | Stop-Process -Force
  schtasks /Run /TN kiosk-agent-start | Out-Null
  Start-Sleep 5
  $new = Get-Process agent -EA SilentlyContinue | Where-Object { $_.Path -eq $dst -and $_.SessionId -ne 0 }
  if (-not $new) { throw "the new agent did not start in the desktop session - reboot the kiosk (autologon starts it)" }
  "restarted: old pid(s) $($old.Id -join ', ') -> new pid $($new.Id) in session $($new.SessionId)"
}
if ($SelfTest) {
  $log = 'C:\kiosk\logs\agent.log'
  $mark = (Get-Content $log -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
  schtasks /Create /TN kiosk-agent-selftest /TR "$dst -selftest-reboot" /SC ONCE /ST 00:00 /SD 01/01/2030 /RU $env:USERNAME /IT /F | Out-Null
  schtasks /Run /TN kiosk-agent-selftest | Out-Null
  $deadline = (Get-Date).AddSeconds(60)
  do {
    Start-Sleep 2
    $lines = @(Get-Content $log | Select-Object -Skip $mark | Where-Object { $_ -match 'selftest: ' })
  } until (($lines -match 'selftest: (ok|FAILED)') -or (Get-Date) -gt $deadline)
  $lines
  if (-not ($lines -match 'selftest: ok')) { throw "the self-test did not report ok - read C:\kiosk\logs\agent.log" }
}
