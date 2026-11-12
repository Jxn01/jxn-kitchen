package main

import (
	"context"
	"encoding/binary"
	"errors"
	"net"
	"os"
	"strings"
	"testing"
	"time"
)

// A harness: the uplink probe and the reconnect are fakes, the clock is ours.
type healRig struct {
	h          *NetHeal
	uplink     error // what Probe returns
	reconnects int
	now        time.Time
}

func newHealRig(after int, cooldown time.Duration) *healRig {
	r := &healRig{now: time.Date(2026, 11, 3, 12, 39, 0, 0, time.UTC)}
	r.h = &NetHeal{
		After:     after,
		Cooldown:  cooldown,
		Probe:     func(context.Context) error { return r.uplink },
		Reconnect: func(context.Context) error { r.reconnects++; return nil },
		Now:       func() time.Time { return r.now },
	}
	return r
}

var errDead = errors.New("context deadline exceeded")

func TestNetHealReconnectsAfterNFailuresWhenTheUplinkIsDeadToo(t *testing.T) {
	r := newHealRig(3, 5*time.Minute)
	r.uplink = errDead
	ctx := context.Background()
	if l := r.h.Report(ctx, errDead); l != "net: heartbeat failed 1/3" || r.reconnects != 0 {
		t.Fatalf("1st: %q reconnects=%d", l, r.reconnects)
	}
	if l := r.h.Report(ctx, errDead); l != "net: heartbeat failed 2/3" || r.reconnects != 0 {
		t.Fatalf("2nd: %q reconnects=%d", l, r.reconnects)
	}
	if l := r.h.Report(ctx, errDead); !strings.HasSuffix(l, "Wi-Fi reconnected") || r.reconnects != 1 {
		t.Fatalf("3rd: %q reconnects=%d", l, r.reconnects)
	}
}

func TestNetHealLeavesTheRadioAloneWhileTheUplinkAnswers(t *testing.T) {
	r := newHealRig(3, 5*time.Minute)
	r.uplink = nil // the internet answers: the server is down, not the link
	ctx := context.Background()
	for i := 0; i < 10; i++ {
		l := r.h.Report(ctx, errDead)
		if i >= 2 && !strings.Contains(l, "the server is down, not the link") {
			t.Fatalf("report %d: %q", i+1, l)
		}
	}
	if r.reconnects != 0 {
		t.Fatalf("reconnected %d times with a live uplink", r.reconnects)
	}
}

func TestNetHealHonoursTheCooldownThenActsAgain(t *testing.T) {
	r := newHealRig(3, 5*time.Minute)
	r.uplink = errDead
	ctx := context.Background()
	for i := 0; i < 3; i++ {
		r.h.Report(ctx, errDead)
	}
	if r.reconnects != 1 {
		t.Fatalf("reconnects=%d", r.reconnects)
	}
	r.now = r.now.Add(70 * time.Second)
	if l := r.h.Report(ctx, errDead); !strings.Contains(l, "waiting") || r.reconnects != 1 {
		t.Fatalf("inside cooldown: %q reconnects=%d", l, r.reconnects)
	}
	r.now = r.now.Add(5 * time.Minute)
	if l := r.h.Report(ctx, errDead); !strings.HasSuffix(l, "Wi-Fi reconnected") || r.reconnects != 2 {
		t.Fatalf("after cooldown: %q reconnects=%d", l, r.reconnects)
	}
}

func TestNetHealResetsOnTheFirstGoodHeartbeat(t *testing.T) {
	r := newHealRig(3, 5*time.Minute)
	r.uplink = errDead
	ctx := context.Background()
	r.h.Report(ctx, errDead)
	r.h.Report(ctx, errDead)
	if l := r.h.Report(ctx, nil); l != "net: heartbeat back" {
		t.Fatalf("recovery line: %q", l)
	}
	if l := r.h.Report(ctx, nil); l != "" {
		t.Fatalf("quiet success should log nothing, got %q", l)
	}
	// The count really restarted: two more failures are not enough to act.
	r.h.Report(ctx, errDead)
	r.h.Report(ctx, errDead)
	if r.reconnects != 0 {
		t.Fatalf("reconnected after a reset: %d", r.reconnects)
	}
}

func TestNetHealDisabledNeverProbesNorReconnects(t *testing.T) {
	r := newHealRig(0, 5*time.Minute)
	r.h.Probe = func(context.Context) error { t.Fatal("probed while disabled"); return nil }
	ctx := context.Background()
	for i := 0; i < 5; i++ {
		if l := r.h.Report(ctx, errDead); l != "" {
			t.Fatalf("disabled healer spoke: %q", l)
		}
	}
	if r.reconnects != 0 {
		t.Fatal("reconnected while disabled")
	}
}

func TestNetHealReportsAFailedReconnect(t *testing.T) {
	r := newHealRig(1, time.Minute)
	r.uplink = errDead
	r.h.Reconnect = func(context.Context) error { return errors.New("netsh: exit status 1") }
	if l := r.h.Report(context.Background(), errDead); !strings.Contains(l, "Wi-Fi reconnect failed: netsh: exit status 1") {
		t.Fatalf("%q", l)
	}
}

func TestTCPProbeTellsAnAnsweringPortFromADeadOne(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	go func() {
		for {
			c, err := ln.Accept()
			if err != nil {
				return
			}
			c.Close()
		}
	}()
	if err := tcpProbe(ln.Addr().String())(context.Background()); err != nil {
		t.Fatalf("live port: %v", err)
	}
	dead, _ := net.Listen("tcp", "127.0.0.1:0")
	addr := dead.Addr().String()
	dead.Close() // nothing listens there now
	if err := tcpProbe(addr)(context.Background()); err == nil {
		t.Fatal("closed port probed as alive")
	}
	if err := tcpProbe("")(context.Background()); err == nil {
		t.Fatal("empty address probed as alive")
	}
}

func TestWifiReconnectArgs(t *testing.T) {
	a := WifiReconnectArgs("KITCHEN-KIOSK")
	if len(a) != 2 || strings.Join(a[0], " ") != "wlan disconnect" || strings.Join(a[1], " ") != "wlan connect name=KITCHEN-KIOSK" {
		t.Fatalf("%v", a)
	}
}

// --- The Reboot rung (2026-11-07: a radio that never associated after a boot; only a reboot cured it) ---

type rebootRig struct {
	*healRig
	state   WifiState
	stErr   error
	idle    time.Duration
	reboots []string
	hist    *RebootHistory
}

// newRebootRig: dead uplink, Wi-Fi "disconnected", reconnects that fail like netsh did, a screen untouched for an
// hour, and the REAL file-backed history in a temp dir (no fake kinder than the real thing).
func newRebootRig(t *testing.T) *rebootRig {
	r := &rebootRig{healRig: newHealRig(3, 5*time.Minute), state: WifiState{Interfaces: 1, State: "disconnected"},
		idle: time.Hour, hist: &RebootHistory{Path: t.TempDir() + "/netheal-reboots.txt"}}
	r.uplink = errDead
	r.h.Reconnect = func(context.Context) error { r.reconnects++; return errors.New("exit status 1: network not available") }
	r.h.State = func(context.Context) (WifiState, error) { return r.state, r.stErr }
	r.h.Reboot = func(reason string) error { r.reboots = append(r.reboots, reason); return nil }
	r.h.RebootAfter = 20 * time.Minute
	r.h.RebootEvery = time.Hour
	r.h.RebootPerDay = 3
	r.h.IdleFor = func() (time.Duration, error) { return r.idle, nil }
	r.h.IdleAtLeast = 10 * time.Minute
	r.h.History = r.hist
	return r
}

// minutes reports one failed heartbeat per minute for n minutes and returns the last line.
func (r *rebootRig) minutes(n int) string {
	var l string
	for i := 0; i < n; i++ {
		l = r.h.Report(context.Background(), errDead)
		r.now = r.now.Add(time.Minute)
	}
	return l
}

func TestRebootRungRebootsARadioThatNeverAssociates(t *testing.T) {
	r := newRebootRig(t)
	r.minutes(22) // dead from the 3rd report (minute 2) on: 20 min of it end at minute 22
	if len(r.reboots) != 0 {
		t.Fatalf("rebooted before 20 min of dead uplink: %v", r.reboots)
	}
	l := r.minutes(1)
	if len(r.reboots) != 1 || !strings.HasSuffix(l, ": rebooting") || !strings.Contains(l, "(Wi-Fi disconnected)") {
		t.Fatalf("no reboot after 20 min: reboots=%v line=%q", r.reboots, l)
	}
	if !strings.Contains(r.reboots[0], "no uplink for 20m") || !strings.Contains(r.reboots[0], "Wi-Fi disconnected") {
		t.Fatalf("reboot reason: %q", r.reboots[0])
	}
	times, err := r.hist.Load()
	if err != nil || len(times) != 1 {
		t.Fatalf("history not recorded: %v %v", times, err)
	}
	if r.reconnects == 0 {
		t.Fatal("the cheap rung was never tried first")
	}
}

// The negative control: an internet outage behind a working Wi-Fi (or the firewall-rule proof on the box) must
// never reboot, however long it lasts.
func TestRebootRungNeverRebootsWhileTheWifiIsAssociated(t *testing.T) {
	r := newRebootRig(t)
	r.state = WifiState{Interfaces: 1, State: "connected"}
	l := r.minutes(180)
	if len(r.reboots) != 0 {
		t.Fatalf("rebooted %d times with the Wi-Fi associated", len(r.reboots))
	}
	if !strings.Contains(l, "no reboot: the Wi-Fi is associated") {
		t.Fatalf("the log does not say why: %q", l)
	}
}

func TestRebootRungTreatsAnUnknownWifiStateAsNotAssociated(t *testing.T) {
	r := newRebootRig(t)
	r.stErr = errors.New("WlanOpenHandle: The service has not been started.")
	l := r.minutes(23)
	if len(r.reboots) != 1 || !strings.Contains(l, "Wi-Fi state unknown: WlanOpenHandle") {
		t.Fatalf("reboots=%d line=%q", len(r.reboots), l)
	}
}

func TestRebootRungTreatsNoInterfaceAsNotAssociated(t *testing.T) {
	r := newRebootRig(t)
	r.state = WifiState{}
	l := r.minutes(23)
	if len(r.reboots) != 1 || !strings.Contains(l, "(no Wi-Fi interface)") {
		t.Fatalf("reboots=%d line=%q", len(r.reboots), l)
	}
}

func TestRebootRungWaitsForAnUntouchedScreen(t *testing.T) {
	r := newRebootRig(t)
	r.idle = 2 * time.Minute
	l := r.minutes(40)
	if len(r.reboots) != 0 || !strings.Contains(l, "reboot held: the screen was used 2m0s ago") {
		t.Fatalf("reboots=%d line=%q", len(r.reboots), l)
	}
	r.idle = 11 * time.Minute
	r.minutes(1)
	if len(r.reboots) != 1 {
		t.Fatalf("no reboot once the screen was left alone: %d", len(r.reboots))
	}
}

func TestRebootRungHoldsWhenIdleTimeIsUnknown(t *testing.T) {
	r := newRebootRig(t)
	r.h.IdleFor = func() (time.Duration, error) { return 0, errors.New("GetLastInputInfo: denied") }
	if l := r.minutes(30); len(r.reboots) != 0 || !strings.Contains(l, "reboot held: idle time unknown") {
		t.Fatalf("reboots=%d line=%q", len(r.reboots), l)
	}
}

// The cooldown and the cap are read from the file, so they hold across the reboots they count: each "restart" is
// a fresh NetHeal over the same history file, the way a new agent starts after a reboot.
func TestRebootRungCooldownAndDailyCapSurviveRestarts(t *testing.T) {
	r := newRebootRig(t)
	restart := func() {
		h := *r.h
		h.fails, h.last, h.deadSince = 0, time.Time{}, time.Time{}
		r.h = &h
	}
	r.minutes(23) // reboot 1
	for i := 2; i <= 3; i++ {
		restart()
		l := r.minutes(23) // a deaf boot again: 23 min in, but the last reboot was only ~23 min ago
		if len(r.reboots) != i-1 || !strings.Contains(l, "reboot held: the last agent reboot was") {
			t.Fatalf("cooldown %d: reboots=%d line=%q", i, len(r.reboots), l)
		}
		r.minutes(40) // past the hour since the last reboot
		if len(r.reboots) != i {
			t.Fatalf("no reboot %d after the cooldown: %d", i, len(r.reboots))
		}
	}
	restart()
	l := r.minutes(120)
	if len(r.reboots) != 3 || !strings.Contains(l, "reboot held: 3 agent reboots in the last 24 h already") {
		t.Fatalf("daily cap: reboots=%d line=%q", len(r.reboots), l)
	}
	r.now = r.now.Add(24 * time.Hour)
	restart()
	r.minutes(23)
	if len(r.reboots) != 4 {
		t.Fatalf("the cap never released after 24 h: %d", len(r.reboots))
	}
}

func TestRebootRungNeverRebootsWhatItCannotRecord(t *testing.T) {
	r := newRebootRig(t)
	dir := t.TempDir()
	r.hist.Path = dir // a directory: unreadable as a file, so neither Load nor Add can work
	l := r.minutes(30)
	if len(r.reboots) != 0 || !strings.Contains(l, "reboot held: reboot history unreadable") {
		t.Fatalf("reboots=%d line=%q", len(r.reboots), l)
	}
}

func TestRebootRungFallsBackToReconnectingWhenTheRebootFails(t *testing.T) {
	r := newRebootRig(t)
	r.h.Reboot = func(string) error { return errors.New("exit status 1: Access is denied.(5)") }
	r.minutes(22)
	before := r.reconnects
	r.minutes(1)
	l := r.minutes(5)
	if r.reconnects <= before || !strings.Contains(l, "reboot") {
		t.Fatalf("reconnects %d -> %d, line=%q", before, r.reconnects, l)
	}
}

func TestRebootRungResetsWithTheFirstGoodHeartbeat(t *testing.T) {
	r := newRebootRig(t)
	r.minutes(15)
	r.h.Report(context.Background(), nil)
	r.minutes(15) // 15 + 15 dead minutes, but not 20 in one outage
	if len(r.reboots) != 0 {
		t.Fatalf("the outage clock did not reset: %d", len(r.reboots))
	}
}

func TestRebootRungIgnoresAServerOutage(t *testing.T) {
	r := newRebootRig(t)
	r.uplink = nil // the internet answers
	r.minutes(120)
	if len(r.reboots) != 0 || r.reconnects != 0 {
		t.Fatalf("server outage touched the box: reboots=%d reconnects=%d", len(r.reboots), r.reconnects)
	}
}

func TestRebootRungIsOffWithoutAHistory(t *testing.T) {
	r := newRebootRig(t)
	r.h.History = nil
	r.minutes(60)
	if len(r.reboots) != 0 {
		t.Fatal("rebooted with no place to count reboots")
	}
}

func TestWaitingLineNamesTheLastAttemptNotASuccess(t *testing.T) {
	r := newRebootRig(t)
	r.minutes(3)
	l := r.minutes(1)
	if strings.Contains(l, "reconnected 1m") || !strings.Contains(l, "last reconnect attempt 1m0s ago: waiting") {
		t.Fatalf("%q", l)
	}
}

func TestRebootHistoryRoundTripPruneAndGarbage(t *testing.T) {
	h := &RebootHistory{Path: t.TempDir() + "/sub/r.txt"}
	if ts, err := h.Load(); err != nil || len(ts) != 0 {
		t.Fatalf("missing file: %v %v", ts, err)
	}
	base := time.Date(2026, 11, 7, 3, 53, 0, 0, time.UTC)
	for _, d := range []time.Duration{-8 * 24 * time.Hour, -2 * time.Hour, 0} {
		if err := h.Add(base.Add(d)); err != nil {
			t.Fatal(err)
		}
	}
	f, _ := os.OpenFile(h.Path, os.O_APPEND|os.O_WRONLY, 0)
	f.WriteString("not a time\n")
	f.Close()
	ts, err := h.Load()
	if err != nil || len(ts) != 2 || !ts[1].Equal(base) {
		t.Fatalf("got %v %v (want the 8-day-old entry pruned, garbage ignored)", ts, err)
	}
}

func TestRebootArgs(t *testing.T) {
	a := RebootArgs(30*time.Second, "kiosk-agent: no uplink")
	if strings.Join(a, "|") != "/r|/f|/t|30|/c|kiosk-agent: no uplink" {
		t.Fatalf("%v", a)
	}
	if long := RebootArgs(time.Minute, strings.Repeat("x", 900)); len(long[5]) != 500 {
		t.Fatalf("reason not capped: %d", len(long[5]))
	}
}

func TestOneLine(t *testing.T) {
	in := "\r\nThe network specified by profile \"KITCHEN-KIOSK\" is not available to connect.\r\n\r\n"
	if got := oneLine(in); got != `The network specified by profile "KITCHEN-KIOSK" is not available to connect.` {
		t.Fatalf("%q", got)
	}
	if got := oneLine(strings.Repeat("a ", 400)); len(got) > 304 {
		t.Fatalf("not capped: %d", len(got))
	}
}

func TestParseWlanInterfaceList(t *testing.T) {
	b := make([]byte, 8+2*wlanInterfaceInfoSize)
	binary.LittleEndian.PutUint32(b, 2)
	b[8] = 0xb3 // first GUID byte
	binary.LittleEndian.PutUint32(b[8+16+512:], 4)
	binary.LittleEndian.PutUint32(b[8+wlanInterfaceInfoSize+16+512:], 1)
	ifs, err := parseWlanInterfaceList(b)
	if err != nil || len(ifs) != 2 || ifs[0].GUID[0] != 0xb3 || wlanStateName(ifs[0].State) != "disconnected" ||
		wlanStateName(ifs[1].State) != "connected" {
		t.Fatalf("%+v %v", ifs, err)
	}
	if _, err := parseWlanInterfaceList(b[:100]); err == nil {
		t.Fatal("a truncated list parsed")
	}
	binary.LittleEndian.PutUint32(b, 1000)
	if _, err := parseWlanInterfaceList(b); err == nil {
		t.Fatal("an implausible count parsed")
	}
	if got := wlanStateName(99); got != "state 99" {
		t.Fatal(got)
	}
	if (WifiState{}).String() != "no Wi-Fi interface" || (WifiState{Interfaces: 1, State: "connected"}).Associated() != true {
		t.Fatal("WifiState")
	}
}
