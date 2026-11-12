package main

import (
	"context"
	"encoding/binary"
	"errors"
	"fmt"
	"io/fs"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// NetHeal gets a dead network link back without anyone in the kitchen touching the box. Two failure modes are
// known on the kiosk's Realtek RTL8723BS, and each has its rung:
//
//  1. Missed re-key: the radio missed one of the router's periodic WPA2 re-keys (every 90 min on
//     the guest network) and sat "connected" with a dead link for 90 minutes. A disconnect + connect redoes the
//     handshake and gives the link fresh keys — the Reconnect rung, every Cooldown.
//  2. Deaf radio after a boot: after the nightly reboot the radio never associated at all, and
//     Windows never even started a connection attempt for 11½ hours; every `netsh wlan connect` failed. Only a
//     reboot cured it (1 boot in 27 came up like that). The Reboot rung: when the uplink has been dead for
//     RebootAfter AND the Wi-Fi is not associated, reboot — only while nobody is using the screen, at most once
//     per RebootEvery and RebootPerDay times in 24 h, counted in a file that survives the reboots.
//
// A kitchen-app outage alone never touches the radio: every rung needs consecutive heartbeat failures (After) AND a
// failed Probe (a plain TCP dial to a public address that does not go through the tailnet). And an internet
// outage behind a working Wi-Fi never reboots the box: the Reboot rung needs the Wi-Fi to be NOT associated
// (an unknown state counts as not associated — a wrong reboot costs a minute, a missed one costs hours). The first
// good heartbeat resets everything.
type NetHeal struct {
	After     int                         // consecutive heartbeat failures before acting (0 = disabled)
	Cooldown  time.Duration               // least time between two reconnects
	Probe     func(context.Context) error // independent uplink check; nil = the internet answers
	Reconnect func(context.Context) error // (scan +) disconnect + connect the Wi-Fi profile
	Now       func() time.Time

	State        func(context.Context) (WifiState, error) // the Wi-Fi interface as the WLAN service sees it; nil = unknown
	Reboot       func(reason string) error                // schedule a reboot; nil = never reboot
	RebootAfter  time.Duration                            // how long the uplink must have been dead (0 = never reboot)
	RebootEvery  time.Duration                            // least time between two of the agent's reboots
	RebootPerDay int                                      // most agent reboots in any 24 h
	IdleFor      func() (time.Duration, error)            // time since the last touch or key; nil = no idle gate
	IdleAtLeast  time.Duration                            // the screen must have been untouched this long
	History      *RebootHistory                           // the agent's own reboots, kept across reboots

	fails     int
	last      time.Time // the last reconnect attempt
	deadSince time.Time // the first report that found the uplink dead too, in this outage
}

// Report takes the outcome of one heartbeat and decides. It returns what it did, for the log: "" when there is
// nothing to say (a success after successes), otherwise one line.
func (h *NetHeal) Report(ctx context.Context, hbErr error) string {
	if hbErr == nil {
		h.deadSince = time.Time{}
		if h.fails > 0 {
			h.fails = 0
			return "net: heartbeat back"
		}
		return ""
	}
	h.fails++
	if h.After <= 0 {
		return ""
	}
	if h.fails < h.After {
		return fmt.Sprintf("net: heartbeat failed %d/%d", h.fails, h.After)
	}
	if perr := h.Probe(ctx); perr == nil {
		h.deadSince = time.Time{}
		return fmt.Sprintf("net: heartbeat failed %d/%d, uplink answers: the server is down, not the link", h.fails, h.After)
	}
	now := h.Now()
	if h.deadSince.IsZero() {
		h.deadSince = now
	}
	wifi, associated := h.wifi(ctx)
	head := fmt.Sprintf("net: heartbeat failed %d/%d, uplink dead (%s)", h.fails, h.After, wifi)

	held := ""
	if h.rebootArmed() {
		dead := now.Sub(h.deadSince)
		if ok, why := h.mayReboot(now, dead, associated); ok {
			reason := fmt.Sprintf("kiosk-agent: no uplink for %s, %s", dead.Round(time.Minute), wifi)
			if err := h.History.Add(now); err != nil {
				held = "reboot held: cannot record it: " + err.Error()
			} else if err := h.Reboot(reason); err != nil {
				held = "reboot failed: " + err.Error()
			} else {
				return fmt.Sprintf("%s for %s: rebooting", head, dead.Round(time.Second))
			}
		} else {
			held = why
		}
	}
	tail := ""
	if held != "" {
		tail = "; " + held
	}

	if !h.last.IsZero() && now.Sub(h.last) < h.Cooldown {
		return fmt.Sprintf("%s, last reconnect attempt %s ago: waiting%s", head, now.Sub(h.last).Round(time.Second), tail)
	}
	h.last = now
	if err := h.Reconnect(ctx); err != nil {
		return fmt.Sprintf("%s: Wi-Fi reconnect failed: %v%s", head, err, tail)
	}
	return fmt.Sprintf("%s: Wi-Fi reconnected%s", head, tail)
}

// wifi reads the interface state for the log line and the reboot gate. "Cannot see" is reported as such, never
// as a state: the line says "Wi-Fi state unknown" and the gate treats it as not associated.
func (h *NetHeal) wifi(ctx context.Context) (string, bool) {
	if h.State == nil {
		return "Wi-Fi state unknown", false
	}
	st, err := h.State(ctx)
	if err != nil {
		return "Wi-Fi state unknown: " + err.Error(), false
	}
	return st.String(), st.Associated()
}

func (h *NetHeal) rebootArmed() bool {
	return h.Reboot != nil && h.RebootAfter > 0 && h.History != nil
}

// mayReboot applies every guard of the Reboot rung, in order, and says which one held it ("" while the outage is
// simply not old enough yet — that is no news).
func (h *NetHeal) mayReboot(now time.Time, dead time.Duration, associated bool) (bool, string) {
	if dead < h.RebootAfter {
		return false, ""
	}
	if associated {
		return false, "no reboot: the Wi-Fi is associated, so the outage is past the radio"
	}
	if h.IdleFor != nil {
		idle, err := h.IdleFor()
		if err != nil {
			return false, "reboot held: idle time unknown: " + err.Error()
		}
		if idle < h.IdleAtLeast {
			return false, fmt.Sprintf("reboot held: the screen was used %s ago", idle.Round(time.Second))
		}
	}
	times, err := h.History.Load()
	if err != nil {
		return false, "reboot held: reboot history unreadable: " + err.Error()
	}
	var lastReboot time.Time
	inDay := 0
	for _, t := range times {
		if t.After(now) {
			t = now // a clock that went backwards: count the entry as just now, never as long ago
		}
		if now.Sub(t) < 24*time.Hour {
			inDay++
		}
		if t.After(lastReboot) {
			lastReboot = t
		}
	}
	if h.RebootPerDay > 0 && inDay >= h.RebootPerDay {
		return false, fmt.Sprintf("reboot held: %d agent reboots in the last 24 h already", inDay)
	}
	if !lastReboot.IsZero() && now.Sub(lastReboot) < h.RebootEvery {
		return false, fmt.Sprintf("reboot held: the last agent reboot was %s ago", now.Sub(lastReboot).Round(time.Second))
	}
	return true, ""
}

// WifiState is the Wi-Fi interface as Windows' WLAN service reports it (WlanEnumInterfaces).
type WifiState struct {
	Interfaces int    // Wi-Fi interfaces the WLAN service knows
	State      string // the first one's state ("connected", "disconnected", …); "" when there is none
}

func (s WifiState) Associated() bool { return s.Interfaces > 0 && s.State == "connected" }

func (s WifiState) String() string {
	if s.Interfaces == 0 {
		return "no Wi-Fi interface"
	}
	return "Wi-Fi " + s.State
}

// RebootHistory is the agent's own reboots, one RFC 3339 time per line, so the cooldown and the daily cap hold
// across the reboots they count. Entries older than a week are dropped on each Add; unparsable lines are ignored.
type RebootHistory struct{ Path string }

func (r *RebootHistory) Load() ([]time.Time, error) {
	b, err := os.ReadFile(r.Path)
	if errors.Is(err, fs.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var out []time.Time
	for _, line := range strings.Split(string(b), "\n") {
		if t, err := time.Parse(time.RFC3339, strings.TrimSpace(line)); err == nil {
			out = append(out, t)
		}
	}
	return out, nil
}

// Add records t, written to a temporary file and renamed over the old one, so a power cut never leaves half a file.
func (r *RebootHistory) Add(t time.Time) error {
	times, err := r.Load()
	if err != nil {
		return err
	}
	var b strings.Builder
	for _, old := range times {
		if t.Sub(old) < 7*24*time.Hour {
			b.WriteString(old.Format(time.RFC3339) + "\n")
		}
	}
	b.WriteString(t.Format(time.RFC3339) + "\n")
	if err := os.MkdirAll(filepath.Dir(r.Path), 0o755); err != nil {
		return err
	}
	tmp := r.Path + ".tmp"
	if err := os.WriteFile(tmp, []byte(b.String()), 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, r.Path)
}

// tcpProbe dials addr (host:port) and hangs up: a success means the internet answers from this box.
func tcpProbe(addr string) func(context.Context) error {
	return func(ctx context.Context) error {
		if addr == "" {
			return errors.New("no probe address")
		}
		d := net.Dialer{Timeout: 3 * time.Second}
		c, err := d.DialContext(ctx, "tcp", addr)
		if err != nil {
			return err
		}
		return c.Close()
	}
}

// WifiReconnectArgs are the two netsh command lines of a reconnect, in order: drop the association, then join
// the saved profile again (a fresh 4-way handshake, so fresh keys). netsh wlan needs no elevation for either.
func WifiReconnectArgs(profile string) [][]string {
	return [][]string{
		{"wlan", "disconnect"},
		{"wlan", "connect", "name=" + profile},
	}
}

// RebootArgs is shutdown.exe's command line for a reboot after delay, with reason in the System log's event 1074.
// /f closes Chrome without asking; the delay lets the log line that announces it reach the disk.
func RebootArgs(delay time.Duration, reason string) []string {
	if len(reason) > 500 {
		reason = reason[:500] // shutdown /c takes at most 512 characters
	}
	return []string{"/r", "/f", "/t", strconv.Itoa(int(delay.Seconds())), "/c", reason}
}

// oneLine squeezes a command's output into one log-friendly line: whitespace runs collapsed, at most 300 bytes.
func oneLine(s string) string {
	s = strings.Join(strings.Fields(s), " ")
	if len(s) > 300 {
		s = s[:300] + "…"
	}
	return s
}

// The WLAN API's interface list (WLAN_INTERFACE_INFO_LIST): two DWORDs, then per interface a GUID (16 bytes),
// a WCHAR[256] description (512 bytes) and the WLAN_INTERFACE_STATE (a DWORD). No pointers, so the layout is the
// same on 32- and 64-bit Windows. Parsed here, not in platform_windows.go, so it is tested on any OS.
const wlanInterfaceInfoSize = 16 + 256*2 + 4

type wlanIface struct {
	GUID  [16]byte
	State uint32
}

var wlanStates = [...]string{"not ready", "connected", "ad hoc network formed", "disconnecting", "disconnected",
	"associating", "discovering", "authenticating"}

func wlanStateName(v uint32) string {
	if int(v) < len(wlanStates) {
		return wlanStates[v]
	}
	return fmt.Sprintf("state %d", v)
}

func parseWlanInterfaceList(b []byte) ([]wlanIface, error) {
	if len(b) < 8 {
		return nil, fmt.Errorf("interface list: %d bytes, need 8", len(b))
	}
	n := int(binary.LittleEndian.Uint32(b))
	if n > 64 {
		return nil, fmt.Errorf("interface list: implausible count %d", n)
	}
	if len(b) < 8+n*wlanInterfaceInfoSize {
		return nil, fmt.Errorf("interface list: %d bytes for %d interfaces, need %d", len(b), n, 8+n*wlanInterfaceInfoSize)
	}
	out := make([]wlanIface, n)
	for i := range out {
		off := 8 + i*wlanInterfaceInfoSize
		copy(out[i].GUID[:], b[off:off+16])
		out[i].State = binary.LittleEndian.Uint32(b[off+16+512:])
	}
	return out, nil
}
