package main

import "time"

// Config is the agent's whole configuration. Defaults fit the kitchen kiosk; every field can be overridden by a
// flag (see main.go and the README's "Kiosk agent" section).
type Config struct {
	URL            string        // what Chrome opens (?kiosk=1 tells the app it is the kiosk)
	Chrome         string        // chrome.exe
	Profile        string        // Chrome's --user-data-dir (CDP needs a non-default one since Chrome 136)
	CDPPort        int           // --remote-debugging-port (Chrome binds it to 127.0.0.1)
	Server         string        // the kitchen app's base URL (heartbeat + display)
	HeartbeatEvery time.Duration // POST /api/kiosk/heartbeat
	DisplayEvery   time.Duration // GET /api/kiosk/display -> backlight
	ProbeEvery     time.Duration // CDP liveness probe
	MaxProbeFails  int           // consecutive failed probes before Chrome is killed and restarted
	RestartDelay   time.Duration // pause before relaunching Chrome
	ErrorReload    time.Duration // how long a chrome-error:// page may stay before Page.reload
	Log            string        // log file (rotated at 1 MB, one .old kept)
	WifiProfile    string        // the saved Wi-Fi profile a dead link is reconnected to ("" = never touch the radio)
	ProbeAddr      string        // host:port the uplink probe dials (public, off the tailnet)
	NetHealAfter   int           // consecutive failed heartbeats before the link is judged dead (0 = disabled)
	NetHealEvery   time.Duration // least time between two Wi-Fi reconnects
	RebootAfter    time.Duration // uplink dead this long with the Wi-Fi not associated -> reboot (0 = never reboot)
	RebootEvery    time.Duration // least time between two of the agent's reboots
	RebootPerDay   int           // most agent reboots in any 24 h
	RebootIdle     time.Duration // the screen must have been untouched this long before a reboot
	RebootHistory  string        // file that keeps the agent's reboots across reboots (cooldown + daily cap)
}

func Default() Config {
	return Config{
		URL:            "https://kitchen.example.com/?kiosk=1",
		Chrome:         `C:\Program Files\Google\Chrome\Application\chrome.exe`,
		Profile:        `C:\kiosk\chrome`,
		CDPPort:        9222,
		Server:         "https://kitchen.example.com",
		HeartbeatEvery: 60 * time.Second,
		DisplayEvery:   60 * time.Second,
		ProbeEvery:     30 * time.Second,
		MaxProbeFails:  3,
		RestartDelay:   3 * time.Second,
		ErrorReload:    10 * time.Second,
		Log:            `C:\kiosk\logs\agent.log`,
		WifiProfile:    "KITCHEN-KIOSK",
		ProbeAddr:      "1.1.1.1:443",
		NetHealAfter:   3,
		NetHealEvery:   5 * time.Minute,
		RebootAfter:    20 * time.Minute,
		RebootEvery:    time.Hour,
		RebootPerDay:   3,
		RebootIdle:     10 * time.Minute,
		RebootHistory:  `C:\kiosk\logs\netheal-reboots.txt`,
	}
}
