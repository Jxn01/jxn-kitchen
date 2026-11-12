package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"sync"
	"sync/atomic"
	"time"
)

// The Browse overlay (spec §8.2): on every page outside the kitchen app, Chrome runs our overlay script (the Home ·
// Back · Save bar + keyboard, web/src/overlay → the server's /overlay.js). The agent keeps one long-lived CDP session
// on the page and, per session: Runtime.enable (binding events), Page.enable (the registered script only runs with
// it — measured on real Chrome), Runtime.addBinding("kitchenSave"),
// Page.addScriptToEvaluateOnNewDocument(config + source), and the same evaluated into the page already open.
// The site's CSP is left alone (security review 2026-10-10: switching it off weakened every site for nothing — none
// of the built-in sites sends one, and the overlay styles itself through CSSOM).
//
// The save channel is ours alone: the config carries a per-session secret; the overlay takes it and the binding into
// its closure and deletes both globals before any site script runs, and the agent refuses a save without the secret,
// for a URL that is not on the current page's site, or sooner than saveEvery after the last one. The source comes from the server, so the overlay ships with the app;
// when the server's build changes the script is re-registered. "Save" arrives as Runtime.bindingCalled: the agent
// imports the page (only the page the kiosk is on) and answers the overlay with window.__kitchenOverlay.saved().

// OverlayStatus is what the heartbeat reports as overlay_ok: a session is open and the script is registered.
type OverlayStatus struct{ ok atomic.Bool }

func (s *OverlayStatus) OK() bool { return s.ok.Load() }

const bindingName = "kitchenSave"

// saveEvery: at most one import per this long per session (a page calling the binding in a loop can't flood the
// server with imports).
const saveEvery = 3 * time.Second

type saveGate struct {
	mu   sync.Mutex
	busy bool
	last time.Time
}

func (g *saveGate) enter() bool {
	g.mu.Lock()
	defer g.mu.Unlock()
	if g.busy || time.Since(g.last) < saveEvery {
		return false
	}
	g.busy, g.last = true, time.Now()
	return true
}

func (g *saveGate) leave() { g.mu.Lock(); g.busy = false; g.mu.Unlock() }

func newNonce() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func overlayLoop(ctx context.Context, cfg Config, st *OverlayStatus, checkEvery, timerEvery time.Duration) {
	backoff := time.Second
	for ctx.Err() == nil {
		err := overlaySession(ctx, cfg, st, checkEvery, timerEvery)
		st.ok.Store(false)
		if ctx.Err() != nil {
			return
		}
		if err != nil {
			log.Printf("overlay: %v (retry in %s)", err, backoff)
		}
		sleepCtx(ctx, backoff)
		if backoff < 30*time.Second {
			backoff *= 2
		}
		if err == nil {
			backoff = time.Second
		}
	}
}

type overlayCode struct {
	source string // config + overlay.js
	build  string
}

func fetchOverlay(ctx context.Context, cfg Config, nonce string) (overlayCode, error) {
	get := func(path string) ([]byte, error) {
		c, cancel := context.WithTimeout(ctx, 15*time.Second)
		defer cancel()
		req, _ := http.NewRequestWithContext(c, http.MethodGet, cfg.Server+path, nil)
		r, err := http.DefaultClient.Do(req)
		if err != nil {
			return nil, err
		}
		defer r.Body.Close()
		if r.StatusCode != http.StatusOK && !(path == "/api/health" && r.StatusCode == http.StatusServiceUnavailable) {
			return nil, fmt.Errorf("%s: status %d", path, r.StatusCode)
		}
		return io.ReadAll(io.LimitReader(r.Body, 4<<20))
	}
	src, err := get("/overlay.js")
	if err != nil {
		return overlayCode{}, err
	}
	var settings struct {
		Language    string `json:"language"`
		IdleMinutes int    `json:"idle_minutes"`
	}
	var health struct {
		Build string `json:"build"`
	}
	if b, err := get("/api/settings"); err == nil {
		_ = json.Unmarshal(b, &settings)
	}
	if b, err := get("/api/health"); err == nil {
		_ = json.Unmarshal(b, &health)
	}
	if settings.Language == "" {
		settings.Language = "hu"
	}
	if settings.IdleMinutes == 0 {
		settings.IdleMinutes = 2
	}
	conf, _ := json.Marshal(map[string]any{"app": cfg.URL, "lang": settings.Language, "idleMinutes": settings.IdleMinutes,
		"build": health.Build, "nonce": nonce})
	return overlayCode{source: "window.__kitchenOverlayConfig = " + string(conf) + ";\n" + string(src), build: health.Build}, nil
}

func serverBuild(ctx context.Context, cfg Config) string {
	c, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	req, _ := http.NewRequestWithContext(c, http.MethodGet, cfg.Server+"/api/health", nil)
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		return ""
	}
	defer r.Body.Close()
	var h struct {
		Build string `json:"build"`
	}
	_ = json.NewDecoder(r.Body).Decode(&h)
	return h.Build
}

func overlaySession(ctx context.Context, cfg Config, st *OverlayStatus, checkEvery, timerEvery time.Duration) error {
	pctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	pages, err := cdpPages(pctx, cfg.CDPPort)
	cancel()
	if err != nil {
		return err
	}
	if len(pages) == 0 {
		return fmt.Errorf("no page")
	}
	nonce := newNonce()
	gate := &saveGate{}
	code, err := fetchOverlay(ctx, cfg, nonce)
	if err != nil {
		return err
	}
	dctx, dcancel := context.WithTimeout(ctx, 10*time.Second)
	s, err := DialSession(dctx, pages[0].WS)
	dcancel()
	if err != nil {
		return err
	}
	defer s.Close()
	call := func(method string, params any) (json.RawMessage, error) {
		c, cancel := context.WithTimeout(ctx, 10*time.Second)
		defer cancel()
		return s.Call(c, method, params)
	}
	for _, step := range []struct {
		m string
		p any
	}{
		{"Runtime.enable", nil},
		{"Page.enable", nil}, // without it a registered script never runs on navigation (measured on real Chrome)
		{"Runtime.addBinding", map[string]any{"name": bindingName}},
	} {
		if _, err := call(step.m, step.p); err != nil {
			return err
		}
	}
	register := func(c overlayCode) (string, error) {
		raw, err := call("Page.addScriptToEvaluateOnNewDocument", map[string]any{"source": c.source})
		if err != nil {
			return "", err
		}
		var r struct {
			Identifier string `json:"identifier"`
		}
		_ = json.Unmarshal(raw, &r)
		_, _ = call("Runtime.evaluate", map[string]any{"expression": c.source}) // the page already open
		return r.Identifier, nil
	}
	scriptID, err := register(code)
	if err != nil {
		return err
	}
	st.ok.Store(true)
	log.Printf("overlay: session up (server build %s)", code.build)

	tick := time.NewTicker(checkEvery)
	defer tick.Stop()
	timerTick := time.NewTicker(timerEvery)
	defer timerTick.Stop()
	appOrigin := origin(cfg.URL)
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-timerTick.C:
			// A kitchen timer ended while the kiosk is on a recipe site: bring it back to the app, where the "Time's
			// up!" card rings (spec §6.5). Done here, not in the overlay, so the timers API needs no CORS.
			if anyTimerDone(ctx, cfg) {
				raw, err := call("Runtime.evaluate", map[string]any{"expression": "location.href", "returnByValue": true})
				var cur struct {
					Result struct {
						Value string `json:"value"`
					} `json:"result"`
				}
				if err == nil && json.Unmarshal(raw, &cur) == nil && cur.Result.Value != "" && origin(cur.Result.Value) != appOrigin {
					log.Printf("overlay: a timer is done, back to the app from %s", cur.Result.Value)
					_, _ = call("Page.navigate", map[string]any{"url": cfg.URL})
				}
			}
		case <-s.Done():
			return fmt.Errorf("session ended")
		case ev := <-s.Events():
			if ev.Method == "Runtime.bindingCalled" {
				go handleSave(ctx, cfg, s, ev.Params, nonce, gate)
			}
		case <-tick.C:
			if b := serverBuild(ctx, cfg); b != "" && b != code.build {
				fresh, err := fetchOverlay(ctx, cfg, nonce)
				if err != nil {
					continue
				}
				_, _ = call("Page.removeScriptToEvaluateOnNewDocument", map[string]any{"identifier": scriptID})
				if id, err := register(fresh); err == nil {
					scriptID, code = id, fresh
					log.Printf("overlay: re-registered for server build %s", fresh.build)
				}
			}
			// belt and braces: an external page that somehow lacks the overlay gets it (the script itself returns
			// early on the app and on error pages)
			_, _ = call("Runtime.evaluate", map[string]any{"expression": "window.__kitchenOverlay ? 0 : (" +
				jsString(code.source) + ", 0)"})
		}
	}
}

// jsString wraps source as an indirect eval of a JS string literal, so it can be embedded in an expression.
func jsString(src string) string {
	b, _ := json.Marshal(src)
	return "(0, eval)(" + string(b) + ")"
}

// handleSave imports the page the kiosk is on — and only that page: the binding lives in the page's main world, so a
// site's own script could call it too; whatever URL it passes must be on the current page's site.
func handleSave(ctx context.Context, cfg Config, s *Session, params json.RawMessage, nonce string, gate *saveGate) {
	var ev struct {
		Name    string `json:"name"`
		Payload string `json:"payload"`
	}
	if json.Unmarshal(params, &ev) != nil || ev.Name != bindingName {
		return
	}
	answer := func(result map[string]any) {
		b, _ := json.Marshal(result)
		c, cancel := context.WithTimeout(ctx, 10*time.Second)
		defer cancel()
		_, _ = s.Call(c, "Runtime.evaluate", map[string]any{
			"expression": "window.__kitchenOverlay && window.__kitchenOverlay.saved(" + string(b) + ")"})
	}
	var p struct {
		URL   string `json:"url"`
		Nonce string `json:"nonce"`
	}
	_ = json.Unmarshal([]byte(ev.Payload), &p)
	if subtle.ConstantTimeCompare([]byte(p.Nonce), []byte(nonce)) != 1 {
		log.Printf("overlay: refused a save without the session secret")
		answer(map[string]any{"ok": false, "code": "refused"})
		return
	}
	if !gate.enter() {
		answer(map[string]any{"ok": false, "code": "busy"})
		return
	}
	defer gate.leave()
	c, cancel := context.WithTimeout(ctx, 10*time.Second)
	raw, err := s.Call(c, "Runtime.evaluate", map[string]any{"expression": "location.href", "returnByValue": true})
	cancel()
	var cur struct {
		Result struct {
			Value string `json:"value"`
		} `json:"result"`
	}
	if err == nil {
		_ = json.Unmarshal(raw, &cur)
	}
	if !sameSite(p.URL, cur.Result.Value) {
		log.Printf("overlay: refused a save for %q while on %q", p.URL, cur.Result.Value)
		answer(map[string]any{"ok": false, "code": "refused"})
		return
	}
	body, _ := json.Marshal(map[string]string{"url": p.URL})
	ic, icancel := context.WithTimeout(ctx, 60*time.Second)
	defer icancel()
	req, _ := http.NewRequestWithContext(ic, http.MethodPost, cfg.Server+"/api/import", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		answer(map[string]any{"ok": false, "code": "unavailable"})
		return
	}
	defer r.Body.Close()
	var res struct {
		ID    int    `json:"id"`
		Draft bool   `json:"draft"`
		Code  string `json:"code"`
	}
	if r.StatusCode != http.StatusOK || json.NewDecoder(r.Body).Decode(&res) != nil {
		answer(map[string]any{"ok": false})
		return
	}
	log.Printf("overlay: saved %s as recipe %d (draft=%v)", p.URL, res.ID, res.Draft)
	answer(map[string]any{"ok": true, "id": res.ID, "draft": res.Draft, "code": res.Code})
}

func origin(u string) string {
	p, err := url.Parse(u)
	if err != nil {
		return ""
	}
	return p.Scheme + "://" + p.Host
}

func anyTimerDone(ctx context.Context, cfg Config) bool {
	c, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	req, _ := http.NewRequestWithContext(c, http.MethodGet, cfg.Server+"/api/timers", nil)
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		return false
	}
	defer r.Body.Close()
	var ts []struct {
		State string `json:"state"`
	}
	if json.NewDecoder(r.Body).Decode(&ts) != nil {
		return false
	}
	for _, t := range ts {
		if t.State == "done" {
			return true
		}
	}
	return false
}

func sameSite(a, b string) bool {
	ua, err1 := url.Parse(a)
	ub, err2 := url.Parse(b)
	if err1 != nil || err2 != nil || (ua.Scheme != "https" && ua.Scheme != "http") {
		return false
	}
	return ua.Host != "" && ua.Scheme == ub.Scheme && ua.Host == ub.Host
}
