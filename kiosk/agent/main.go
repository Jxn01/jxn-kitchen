// kiosk-agent: the kitchen kiosk's Windows shell (HKCU\...\Winlogon\Shell for the kiosk user). It launches Chrome in kiosk
// mode on the kitchen app, keeps it alive, reports heartbeats, drives the backlight at night and keeps the display
// awake. In an RDP session it starts Explorer instead, so maintenance always has a normal desktop.
package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"time"
)

var version = "dev" // set at build: -X main.version=<git describe>

func main() {
	cfg := Default()
	flag.StringVar(&cfg.URL, "url", cfg.URL, "page Chrome opens")
	flag.StringVar(&cfg.Server, "server", cfg.Server, "kitchen app base URL (heartbeat, display)")
	flag.StringVar(&cfg.Chrome, "chrome", cfg.Chrome, "path to chrome.exe")
	flag.StringVar(&cfg.Profile, "profile", cfg.Profile, "Chrome --user-data-dir")
	flag.IntVar(&cfg.CDPPort, "cdp-port", cfg.CDPPort, "Chrome --remote-debugging-port (127.0.0.1 only)")
	flag.StringVar(&cfg.Log, "log", cfg.Log, "log file (rotated at 1 MB)")
	flag.StringVar(&cfg.WifiProfile, "wifi-profile", cfg.WifiProfile, "saved Wi-Fi profile to reconnect when the link is dead (empty = never)")
	flag.StringVar(&cfg.ProbeAddr, "probe-addr", cfg.ProbeAddr, "host:port dialled to tell a dead link from a dead server")
	flag.IntVar(&cfg.NetHealAfter, "net-heal-after", cfg.NetHealAfter, "consecutive failed heartbeats before a Wi-Fi reconnect (0 = off)")
	flag.DurationVar(&cfg.NetHealEvery, "net-heal-every", cfg.NetHealEvery, "least time between two Wi-Fi reconnects")
	flag.DurationVar(&cfg.RebootAfter, "reboot-after", cfg.RebootAfter, "uplink dead this long with the Wi-Fi not associated: reboot (0 = never)")
	flag.DurationVar(&cfg.RebootEvery, "reboot-every", cfg.RebootEvery, "least time between two of the agent's reboots")
	flag.IntVar(&cfg.RebootPerDay, "reboot-per-day", cfg.RebootPerDay, "most agent reboots in any 24 h")
	flag.DurationVar(&cfg.RebootIdle, "reboot-idle", cfg.RebootIdle, "the screen must have been untouched this long before a reboot")
	flag.StringVar(&cfg.RebootHistory, "reboot-history", cfg.RebootHistory, "file keeping the agent's reboots across reboots")
	selftest := flag.Bool("selftest-reboot", false, "log the Wi-Fi state, a scan, the idle time, schedule a reboot and abort it 5 s later; then exit")
	flag.Parse()

	setupLog(cfg.Log)
	if *selftest {
		os.Exit(selfTestReboot(context.Background()))
	}
	log.Printf("kiosk-agent %s starting (session %q)", version, os.Getenv("SESSIONNAME"))

	if IsRDP(os.Getenv) {
		log.Printf("RDP session: starting Explorer instead of the kiosk")
		if err := exec.Command(`C:\Windows\explorer.exe`).Start(); err != nil {
			log.Printf("explorer: %v", err)
		}
		// Stay alive for the session: we ARE the shell, and Winlogon restarts a shell that exits (AutoRestartShell) —
		// which would start one more Explorer each time. Logoff ends us.
		select {}
	}

	keepAwake() // belt and braces next to the zero power timeouts: never let the display (= the box) sleep

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	overlay := &OverlayStatus{}
	heal := &NetHeal{After: cfg.NetHealAfter, Cooldown: cfg.NetHealEvery, Probe: tcpProbe(cfg.ProbeAddr), Now: time.Now,
		Reconnect: func(c context.Context) error { return reconnectWifi(c, cfg.WifiProfile) },
		State:     wifiState, Reboot: rebootNow, RebootAfter: cfg.RebootAfter, RebootEvery: cfg.RebootEvery,
		RebootPerDay: cfg.RebootPerDay, IdleFor: idleFor, IdleAtLeast: cfg.RebootIdle,
		History: &RebootHistory{Path: cfg.RebootHistory}}
	if cfg.WifiProfile == "" {
		heal.After = 0 // nothing to reconnect to
	}
	go heartbeatLoop(ctx, cfg, overlay, heal)
	go overlayLoop(ctx, cfg, overlay, time.Minute, 5*time.Second)
	go displayLoop(ctx, cfg, setBrightness)
	go errorPageLoop(ctx, cfg)

	sup := &Supervisor{
		Launch:        execLauncher{cfg},
		Probe:         func(c context.Context) error { return PageProbe(c, cfg.CDPPort) },
		BeforeStart:   killStrayChrome,
		RestartDelay:  cfg.RestartDelay,
		ProbeEvery:    cfg.ProbeEvery,
		MaxProbeFails: cfg.MaxProbeFails,
	}
	sup.Run(ctx)
}
