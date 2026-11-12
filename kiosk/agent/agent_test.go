package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/coder/websocket"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func TestIsRDP(t *testing.T) {
	cases := map[string]bool{"RDP-Tcp#0": true, "RDP-Tcp#12": true, "Console": false, "": false, "rdp-tcp#1": true}
	for name, want := range cases {
		got := IsRDP(func(string) string { return name })
		if got != want {
			t.Errorf("IsRDP(%q) = %v, want %v", name, got, want)
		}
	}
}

func TestChromeArgs(t *testing.T) {
	c := Default()
	args := ChromeArgs(c)
	want := []string{"--kiosk", "--user-data-dir=" + c.Profile, "--remote-debugging-port=9222", "--no-first-run",
		"--noerrdialogs", "--disable-session-crashed-bubble", "--disable-pinch", "--overscroll-history-navigation=0",
		"--disable-features=Translate", "--autoplay-policy=no-user-gesture-required"}
	joined := strings.Join(args, " ")
	for _, w := range want {
		if !strings.Contains(joined, w) {
			t.Errorf("missing %s in %v", w, args)
		}
	}
	if args[len(args)-1] != c.URL || !strings.Contains(c.URL, "kiosk=1") {
		t.Errorf("URL must be last and carry kiosk=1: %v", args)
	}
}

func TestBrightnessArgs(t *testing.T) {
	got := strings.Join(BrightnessArgs(35), " ")
	want := `/NAMESPACE:\\root\wmi PATH WmiMonitorBrightnessMethods WHERE Active=TRUE CALL WmiSetBrightness Brightness=35 Timeout=0`
	if got != want {
		t.Fatalf("got %q\nwant %q", got, want)
	}
	if strings.Join(BrightnessArgs(0), " ") != strings.Join(BrightnessArgs(5), " ") {
		t.Error("brightness must clamp to >= 5: the display is never turned off")
	}
}

func TestIsErrorPage(t *testing.T) {
	for url, want := range map[string]bool{
		"chrome-error://chromewebdata/": true, "https://kitchen.example.com/?kiosk=1#/": false, "about:blank": false,
	} {
		if IsErrorPage(url) != want {
			t.Errorf("IsErrorPage(%q) != %v", url, want)
		}
	}
}

func TestHeartbeatJSON(t *testing.T) {
	b, _ := json.Marshal(Heartbeat{Agent: "0.1.0", ChromeOK: true, FreeMB: 812, OverlayOK: true})
	if string(b) != `{"agent":"0.1.0","chrome_ok":true,"free_mb":812,"overlay_ok":true}` { // the server's field names
		t.Fatal(string(b))
	}
}

// --- supervisor -------------------------------------------------------------------------------------------

type fakeProc struct {
	done   chan struct{}
	killed atomic.Bool
	once   sync.Once
}

func (p *fakeProc) Wait() error { <-p.done; return nil }
func (p *fakeProc) Kill() error {
	p.killed.Store(true)
	p.once.Do(func() { close(p.done) })
	return nil
}
func (p *fakeProc) exit() { p.once.Do(func() { close(p.done) }) }

type fakeLauncher struct {
	mu    sync.Mutex
	procs []*fakeProc
}

func (l *fakeLauncher) Start() (Proc, error) {
	l.mu.Lock()
	defer l.mu.Unlock()
	p := &fakeProc{done: make(chan struct{})}
	l.procs = append(l.procs, p)
	return p, nil
}
func (l *fakeLauncher) n() int { l.mu.Lock(); defer l.mu.Unlock(); return len(l.procs) }
func (l *fakeLauncher) last() *fakeProc {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.procs[len(l.procs)-1]
}

func waitFor(t *testing.T, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for !cond() {
		if time.Now().After(deadline) {
			t.Fatal("timed out")
		}
		time.Sleep(2 * time.Millisecond)
	}
}

func TestSupervisorRestartsChromeWhenItExits(t *testing.T) {
	l := &fakeLauncher{}
	s := &Supervisor{Launch: l, Probe: func(context.Context) error { return nil },
		RestartDelay: 5 * time.Millisecond, ProbeEvery: time.Hour, MaxProbeFails: 3}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	waitFor(t, func() bool { return l.n() == 1 })
	l.last().exit()
	waitFor(t, func() bool { return l.n() == 2 })
}

func TestSupervisorKillsAHungChromeAfterThreeFailedProbes(t *testing.T) {
	l := &fakeLauncher{}
	var fails atomic.Int32
	probe := func(context.Context) error { fails.Add(1); return errors.New("no answer") }
	s := &Supervisor{Launch: l, Probe: probe, RestartDelay: time.Millisecond, ProbeEvery: 3 * time.Millisecond, MaxProbeFails: 3}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	waitFor(t, func() bool { return l.n() >= 2 })
	if !l.procs[0].killed.Load() {
		t.Fatal("the hung process was not killed")
	}
	if fails.Load() < 3 {
		t.Fatalf("killed after only %d failed probes", fails.Load())
	}
}

func TestSupervisorStopsOnCancel(t *testing.T) {
	l := &fakeLauncher{}
	s := &Supervisor{Launch: l, Probe: func(context.Context) error { return nil }, RestartDelay: time.Millisecond,
		ProbeEvery: time.Hour, MaxProbeFails: 3}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() { s.Run(ctx); close(done) }()
	waitFor(t, func() bool { return l.n() == 1 })
	cancel()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("Run did not return")
	}
	if !l.last().killed.Load() {
		t.Fatal("chrome must be stopped on shutdown")
	}
}

func TestLogRotatesAtLimitKeepingOneOld(t *testing.T) {
	dir := t.TempDir()
	r := &rotatingFile{path: dir + "/agent.log", maxBytes: 100}
	t.Cleanup(func() { r.Close() }) // Windows cannot delete the temp dir while the log is open
	line := []byte(strings.Repeat("x", 39) + "\n")
	for i := 0; i < 6; i++ {
		r.Write(line)
	}
	cur, _ := os.ReadFile(dir + "/agent.log")
	old, err := os.ReadFile(dir + "/agent.log.old")
	if err != nil || len(old) == 0 || len(cur) > 100 {
		t.Fatalf("rotation failed: cur=%d old=%d err=%v", len(cur), len(old), err)
	}
}

// --- review I4: the watchdog must see the PAGE, not only the browser process ------------------------------------

// fakeCDP serves /json/list with one page whose websocket answers Runtime.evaluate the way `answer` says.
func fakeCDP(t *testing.T, answer string) (port int) {
	t.Helper()
	var srv *httptest.Server
	srv = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/json/list":
			ws := "ws" + strings.TrimPrefix(srv.URL, "http") + "/devtools/page/1"
			fmt.Fprintf(w, `[{"type":"page","url":"https://kitchen.example.com/?kiosk=1","webSocketDebuggerUrl":%q}]`, ws)
		case "/devtools/page/1":
			c, err := websocket.Accept(w, r, nil)
			if err != nil {
				return
			}
			defer c.CloseNow()
			_, data, err := c.Read(r.Context())
			if err != nil {
				return
			}
			var req struct {
				ID int64 `json:"id"`
			}
			_ = json.Unmarshal(data, &req)
			switch answer {
			case "ok":
				_ = c.Write(r.Context(), websocket.MessageText, []byte(fmt.Sprintf(`{"id":%d,"result":{"result":{"type":"string","value":"complete"}}}`, req.ID)))
			case "crashed":
				_ = c.Write(r.Context(), websocket.MessageText, []byte(fmt.Sprintf(`{"id":%d,"error":{"code":-32000,"message":"Target crashed"}}`, req.ID)))
			case "hung":
				<-r.Context().Done()
			}
		}
	}))
	t.Cleanup(srv.Close)
	u, _ := url.Parse(srv.URL)
	port, _ = strconv.Atoi(u.Port())
	return port
}

func TestPageProbe(t *testing.T) {
	if err := PageProbe(context.Background(), fakeCDP(t, "ok")); err != nil {
		t.Fatalf("healthy page: %v", err)
	}
	if err := PageProbe(context.Background(), fakeCDP(t, "crashed")); err == nil {
		t.Fatal("an Aw-Snap page must fail the probe")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 300*time.Millisecond)
	defer cancel()
	if err := PageProbe(ctx, fakeCDP(t, "hung")); err == nil {
		t.Fatal("a hung renderer must fail the probe (by timeout)")
	}
}

// --- a Chrome already holding our profile makes every launch hand off and exit: kill it before launching -------
func TestSupervisorClearsTheWayBeforeEachLaunch(t *testing.T) {
	l := &fakeLauncher{}
	var cleared atomic.Int32
	s := &Supervisor{Launch: l, Probe: func(context.Context) error { return nil }, RestartDelay: time.Millisecond,
		ProbeEvery: time.Hour, MaxProbeFails: 3, BeforeStart: func() { cleared.Add(1) }}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	waitFor(t, func() bool { return l.n() == 1 })
	l.last().exit()
	waitFor(t, func() bool { return l.n() == 2 })
	if cleared.Load() < 2 {
		t.Fatalf("BeforeStart ran %d times for 2 launches", cleared.Load())
	}
}
