package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"
)

type Heartbeat struct {
	Agent     string `json:"agent"`
	ChromeOK  bool   `json:"chrome_ok"`
	FreeMB    int    `json:"free_mb"`
	OverlayOK bool   `json:"overlay_ok"` // the Browse overlay's session is up (the app hides Browse when it isn't)
}

func heartbeatLoop(ctx context.Context, cfg Config, overlay *OverlayStatus, heal *NetHeal) {
	for {
		pctx, cancel := context.WithTimeout(ctx, 5*time.Second)
		ok := PageProbe(pctx, cfg.CDPPort) == nil // the page answers — what Gatus' "chrome_ok" should mean
		cancel()
		err := postHeartbeat(ctx, cfg.Server, Heartbeat{Agent: version, ChromeOK: ok, FreeMB: freeMB(), OverlayOK: overlay.OK()})
		if err != nil {
			log.Printf("heartbeat: %v", err)
		}
		if line := heal.Report(ctx, err); line != "" {
			log.Print(line)
		}
		sleepCtx(ctx, cfg.HeartbeatEvery)
		if ctx.Err() != nil {
			return
		}
	}
}

func postHeartbeat(ctx context.Context, server string, hb Heartbeat) error {
	body, _ := json.Marshal(hb)
	cctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	req, _ := http.NewRequestWithContext(cctx, http.MethodPost, server+"/api/kiosk/heartbeat", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	r.Body.Close()
	if r.StatusCode != http.StatusNoContent {
		return fmt.Errorf("status %d", r.StatusCode)
	}
	return nil
}

// errorPageLoop reloads the page when Chrome sits on its own error page (e.g. Wi-Fi not up yet at logon).
func errorPageLoop(ctx context.Context, cfg Config) {
	var since time.Time
	for {
		sleepCtx(ctx, 5*time.Second)
		if ctx.Err() != nil {
			return
		}
		pctx, cancel := context.WithTimeout(ctx, 5*time.Second)
		pages, err := cdpPages(pctx, cfg.CDPPort)
		cancel()
		if err != nil || len(pages) == 0 {
			since = time.Time{}
			continue
		}
		if !IsErrorPage(pages[0].URL) {
			since = time.Time{}
			continue
		}
		if since.IsZero() {
			since = time.Now()
			continue
		}
		if time.Since(since) >= cfg.ErrorReload {
			log.Printf("chrome: error page for %s, navigating back to the app", time.Since(since).Round(time.Second))
			rctx, rcancel := context.WithTimeout(ctx, 10*time.Second)
			_, err := cdpCall(rctx, pages[0].WS, "Page.navigate", map[string]string{"url": cfg.URL})
			rcancel()
			if err != nil {
				log.Printf("chrome: navigate failed: %v", err)
			}
			since = time.Time{}
		}
	}
}
