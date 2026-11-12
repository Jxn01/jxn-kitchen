package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/coder/websocket"
)

// fakeKiosk is one test server playing both sides: Chrome's CDP (/json/list + a PERSISTENT page websocket that
// records every call and can push events) and the kitchen server (/overlay.js, /api/health, /api/settings,
// /api/import). The page "is" on pageURL.
type fakeKiosk struct {
	t       *testing.T
	srv     *httptest.Server
	mu      sync.Mutex
	calls   []string            // CDP methods, in order
	params  map[string][]string // method -> raw params
	conns   atomic.Int32
	push    chan string // events to push to the connected client
	kill    chan struct{}
	imports []string
	pageURL string
	build   string
	timers  string // the /api/timers body
}

func newFakeKiosk(t *testing.T) *fakeKiosk {
	f := &fakeKiosk{t: t, params: map[string][]string{}, push: make(chan string, 8), kill: make(chan struct{}, 1),
		pageURL: "https://www.nosalty.hu/recept/paprikas-csirke", build: "b1"}
	f.srv = httptest.NewServer(http.HandlerFunc(f.handle))
	t.Cleanup(f.srv.Close)
	return f
}

func (f *fakeKiosk) port() int {
	u, _ := url.Parse(f.srv.URL)
	p, _ := strconv.Atoi(u.Port())
	return p
}

func (f *fakeKiosk) handle(w http.ResponseWriter, r *http.Request) {
	switch r.URL.Path {
	case "/json/list":
		ws := "ws" + strings.TrimPrefix(f.srv.URL, "http") + "/devtools/page/1"
		fmt.Fprintf(w, `[{"type":"page","url":%q,"webSocketDebuggerUrl":%q}]`, f.pageURL, ws)
	case "/overlay.js":
		fmt.Fprint(w, "/*OVERLAY-SRC*/")
	case "/api/health":
		f.mu.Lock()
		b := f.build
		f.mu.Unlock()
		fmt.Fprintf(w, `{"ok":true,"build":%q}`, b)
	case "/api/settings":
		fmt.Fprint(w, `{"language":"hu","idle_minutes":5}`)
	case "/api/timers":
		f.mu.Lock()
		body := f.timers
		f.mu.Unlock()
		if body == "" {
			body = "[]"
		}
		fmt.Fprint(w, body)
	case "/api/import":
		var body struct {
			URL string `json:"url"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		f.mu.Lock()
		f.imports = append(f.imports, body.URL)
		f.mu.Unlock()
		fmt.Fprint(w, `{"id":42,"draft":false}`)
	case "/devtools/page/1":
		c, err := websocket.Accept(w, r, nil)
		if err != nil {
			return
		}
		f.conns.Add(1)
		ctx, cancel := context.WithCancel(r.Context())
		defer cancel()
		var wmu sync.Mutex
		write := func(s string) { wmu.Lock(); defer wmu.Unlock(); _ = c.Write(ctx, websocket.MessageText, []byte(s)) }
		go func() {
			for {
				select {
				case ev := <-f.push:
					write(ev)
				case <-f.kill:
					c.Close(websocket.StatusGoingAway, "chrome restarted")
					cancel()
					return
				case <-ctx.Done():
					return
				}
			}
		}()
		for {
			_, data, err := c.Read(ctx)
			if err != nil {
				return
			}
			var req struct {
				ID     int64           `json:"id"`
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			_ = json.Unmarshal(data, &req)
			f.mu.Lock()
			f.calls = append(f.calls, req.Method)
			f.params[req.Method] = append(f.params[req.Method], string(req.Params))
			page := f.pageURL
			f.mu.Unlock()
			result := `{}`
			switch req.Method {
			case "Page.addScriptToEvaluateOnNewDocument":
				result = `{"identifier":"7"}`
			case "Runtime.evaluate":
				if strings.Contains(string(req.Params), "location.href") {
					result = fmt.Sprintf(`{"result":{"type":"string","value":%q}}`, page)
				} else {
					result = `{"result":{"type":"undefined"}}`
				}
			}
			write(fmt.Sprintf(`{"id":%d,"result":%s}`, req.ID, result))
		}
	}
}

func (f *fakeKiosk) seen(method string) []string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]string(nil), f.params[method]...)
}

// nonce reads the per-session secret out of the config the agent injected.
func (f *fakeKiosk) nonce() string {
	src := f.seen("Page.addScriptToEvaluateOnNewDocument")
	if len(src) == 0 {
		return ""
	}
	i := strings.Index(src[len(src)-1], `\"nonce\":\"`)
	if i < 0 {
		return ""
	}
	rest := src[len(src)-1][i+len(`\"nonce\":\"`):]
	return rest[:strings.Index(rest, `\"`)]
}

func bindingEvent(url, nonce string) string {
	payload, _ := json.Marshal(map[string]string{"url": url, "nonce": nonce})
	ev, _ := json.Marshal(map[string]any{"method": "Runtime.bindingCalled",
		"params": map[string]any{"name": "kitchenSave", "payload": string(payload), "executionContextId": 1}})
	return string(ev)
}

func (f *fakeKiosk) cfg() Config {
	c := Default()
	c.Server, c.CDPPort, c.URL = f.srv.URL, f.port(), "https://kitchen.example.com/?kiosk=1"
	return c
}

func TestOverlaySetsUpTheSession(t *testing.T) {
	f := newFakeKiosk(t)
	var st OverlayStatus
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go overlayLoop(ctx, f.cfg(), &st, time.Hour, time.Hour)
	waitFor(t, func() bool { return st.OK() })
	if len(f.seen("Page.setBypassCSP")) != 0 {
		t.Fatal("the agent must not switch the site's CSP off (security review)")
	}
	if len(f.nonce()) < 32 {
		t.Fatalf("no per-session secret in the injected config: %q", f.nonce())
	}
	// measured on real Chrome 2026-10-10: without Page.enable a registered script never runs on navigation
	f.mu.Lock()
	order := strings.Join(f.calls, " ")
	f.mu.Unlock()
	if i, j := strings.Index(order, "Page.enable"), strings.Index(order, "Page.addScriptToEvaluateOnNewDocument"); i < 0 || i > j {
		t.Fatalf("Page.enable must come before the script is registered: %s", order)
	}
	for _, m := range []string{"Runtime.enable", "Runtime.addBinding", "Page.addScriptToEvaluateOnNewDocument"} {
		if len(f.seen(m)) == 0 {
			t.Fatalf("%s was never called (calls: %v)", m, f.calls)
		}
	}
	if !strings.Contains(f.seen("Runtime.addBinding")[0], `"kitchenSave"`) {
		t.Fatal("binding name")
	}
	src := f.seen("Page.addScriptToEvaluateOnNewDocument")[0]
	for _, want := range []string{"/*OVERLAY-SRC*/", `\"lang\":\"hu\"`, `\"idleMinutes\":5`, "kitchen.example.com"} {
		if !strings.Contains(src, want) {
			t.Fatalf("injected source lacks %s: %s", want, src)
		}
	}
}

func TestSaveImportsTheCurrentPageAndAnswersTheOverlay(t *testing.T) {
	f := newFakeKiosk(t)
	var st OverlayStatus
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go overlayLoop(ctx, f.cfg(), &st, time.Hour, time.Hour)
	waitFor(t, func() bool { return st.OK() })
	f.push <- bindingEvent("https://www.nosalty.hu/recept/paprikas-csirke", f.nonce())
	waitFor(t, func() bool {
		for _, p := range f.seen("Runtime.evaluate") {
			if strings.Contains(p, "saved(") && strings.Contains(p, `\"id\":42`) {
				return true
			}
		}
		return false
	})
	if len(f.imports) != 1 || f.imports[0] != "https://www.nosalty.hu/recept/paprikas-csirke" {
		t.Fatalf("imports: %v", f.imports)
	}
}

func TestSaveRefusesAURLThatIsNotThePage(t *testing.T) {
	f := newFakeKiosk(t)
	var st OverlayStatus
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go overlayLoop(ctx, f.cfg(), &st, time.Hour, time.Hour)
	waitFor(t, func() bool { return st.OK() })
	// a site's own script calling the binding with somewhere else
	f.push <- bindingEvent("https://evil.example/x", f.nonce())
	waitFor(t, func() bool {
		for _, p := range f.seen("Runtime.evaluate") {
			if strings.Contains(p, "saved(") && strings.Contains(p, `\"ok\":false`) {
				return true
			}
		}
		return false
	})
	if len(f.imports) != 0 {
		t.Fatalf("a foreign URL was imported: %v", f.imports)
	}
}

func TestOverlayReconnectsWhenChromeGoesAway(t *testing.T) {
	f := newFakeKiosk(t)
	var st OverlayStatus
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go overlayLoop(ctx, f.cfg(), &st, time.Hour, time.Hour)
	waitFor(t, func() bool { return st.OK() && f.conns.Load() == 1 })
	f.kill <- struct{}{}
	waitFor(t, func() bool {
		return f.conns.Load() == 2 && st.OK() && len(f.seen("Page.addScriptToEvaluateOnNewDocument")) == 2
	})
}

func TestOverlayReRegistersWhenTheServerBuildChanges(t *testing.T) {
	f := newFakeKiosk(t)
	var st OverlayStatus
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go overlayLoop(ctx, f.cfg(), &st, 20*time.Millisecond, time.Hour)
	waitFor(t, func() bool { return st.OK() })
	f.mu.Lock()
	f.build = "b2"
	f.mu.Unlock()
	waitFor(t, func() bool {
		return len(f.seen("Page.removeScriptToEvaluateOnNewDocument")) == 1 && len(f.seen("Page.addScriptToEvaluateOnNewDocument")) == 2
	})
	if !strings.Contains(f.seen("Page.removeScriptToEvaluateOnNewDocument")[0], `"7"`) {
		t.Fatal("removed the wrong script")
	}
}

func TestSaveWithoutTheSessionSecretIsRefused(t *testing.T) {
	f := newFakeKiosk(t)
	var st OverlayStatus
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go overlayLoop(ctx, f.cfg(), &st, time.Hour, time.Hour)
	waitFor(t, func() bool { return st.OK() })
	// a site's script that found the binding but not the secret
	f.push <- bindingEvent("https://www.nosalty.hu/recept/paprikas-csirke", "guess")
	waitFor(t, func() bool {
		for _, p := range f.seen("Runtime.evaluate") {
			if strings.Contains(p, "saved(") && strings.Contains(p, `\"ok\":false`) {
				return true
			}
		}
		return false
	})
	if len(f.imports) != 0 {
		t.Fatalf("imported without the secret: %v", f.imports)
	}
}

func TestSavesAreRateLimited(t *testing.T) {
	f := newFakeKiosk(t)
	var st OverlayStatus
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go overlayLoop(ctx, f.cfg(), &st, time.Hour, time.Hour)
	waitFor(t, func() bool { return st.OK() })
	for i := 0; i < 5; i++ {
		f.push <- bindingEvent("https://www.nosalty.hu/recept/paprikas-csirke", f.nonce())
	}
	waitFor(t, func() bool {
		n := 0
		for _, p := range f.seen("Runtime.evaluate") {
			if strings.Contains(p, "saved(") {
				n++
			}
		}
		return n == 5
	})
	f.mu.Lock()
	defer f.mu.Unlock()
	if len(f.imports) != 1 {
		t.Fatalf("5 quick saves made %d imports, want 1", len(f.imports))
	}
}

func TestADoneTimerBringsTheKioskBackFromASite(t *testing.T) {
	f := newFakeKiosk(t)
	var st OverlayStatus
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go overlayLoop(ctx, f.cfg(), &st, time.Hour, 20*time.Millisecond)
	waitFor(t, func() bool { return st.OK() })
	time.Sleep(60 * time.Millisecond)
	if len(f.seen("Page.navigate")) != 0 {
		t.Fatal("navigated with no timer done")
	}
	f.mu.Lock()
	f.timers = `[{"id":1,"label":"Tészta","state":"done"}]`
	f.mu.Unlock()
	waitFor(t, func() bool { return len(f.seen("Page.navigate")) > 0 })
	if !strings.Contains(f.seen("Page.navigate")[0], "kitchen.example.com") {
		t.Fatalf("navigated elsewhere: %v", f.seen("Page.navigate"))
	}
}

func TestADoneTimerLeavesTheAppAlone(t *testing.T) {
	f := newFakeKiosk(t)
	f.pageURL = "https://kitchen.example.com/?kiosk=1#/cook/3" // already in the app: its own card rings
	f.timers = `[{"id":1,"label":"x","state":"done"}]`
	var st OverlayStatus
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go overlayLoop(ctx, f.cfg(), &st, time.Hour, 20*time.Millisecond)
	waitFor(t, func() bool { return st.OK() })
	time.Sleep(100 * time.Millisecond)
	if n := len(f.seen("Page.navigate")); n != 0 {
		t.Fatalf("navigated %d times while in the app", n)
	}
}
