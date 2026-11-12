package main

import (
	"context"
	"log"
	"os"
	"time"
)

// selfTestReboot proves, from the agent's own token and session, every Windows call the Reboot rung depends on —
// without rebooting: it logs the Wi-Fi state and a scan's outcome, the idle time, then schedules a reboot in
// 10 minutes and aborts it 5 s later, logging both of shutdown.exe's answers. Run it the way the agent runs
// (install.ps1 -SelfTest starts it through an interactive scheduled task); an elevated SSH shell proves nothing
// about the limited token. If the abort ever failed, the box would reboot 10 minutes later: harmless, it reboots
// every night anyway. Returns the process exit code: 0 = shutdown.exe accepted both.
func selfTestReboot(ctx context.Context) int {
	log.Printf("selftest: kiosk-agent %s, session %q", version, os.Getenv("SESSIONNAME"))
	if st, err := wifiState(ctx); err != nil {
		log.Printf("selftest: Wi-Fi state: %v", err)
	} else {
		log.Printf("selftest: Wi-Fi state: %s (%d interface(s))", st, st.Interfaces)
	}
	log.Printf("selftest: Wi-Fi scan: %s", errText(scanWifi()))
	if idle, err := idleFor(); err != nil {
		log.Printf("selftest: idle: %v", err)
	} else {
		log.Printf("selftest: idle: %s", idle.Round(time.Second))
	}
	out, err := runShutdown(RebootArgs(10*time.Minute, "kiosk-agent self-test: aborted 5 s later")...)
	log.Printf("selftest: shutdown /r /t 600: %s %q", errText(err), out)
	time.Sleep(5 * time.Second)
	out2, err2 := runShutdown("/a")
	log.Printf("selftest: shutdown /a: %s %q", errText(err2), out2)
	if err != nil || err2 != nil {
		log.Printf("selftest: FAILED")
		return 1
	}
	log.Printf("selftest: ok")
	return 0
}

func errText(err error) string {
	if err == nil {
		return "ok"
	}
	return err.Error()
}
