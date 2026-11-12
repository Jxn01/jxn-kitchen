package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"sync/atomic"

	"github.com/coder/websocket"
)

// A tiny Chrome DevTools Protocol client: just what the agent needs.

type cdpTarget struct {
	Type string `json:"type"`
	URL  string `json:"url"`
	WS   string `json:"webSocketDebuggerUrl"`
}

func cdpBase(port int) string { return fmt.Sprintf("http://127.0.0.1:%d", port) }

// CDPVersion is the liveness probe: Chrome answers /json/version while its browser process is healthy.
func CDPVersion(ctx context.Context, port int) error {
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, cdpBase(port)+"/json/version", nil)
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer r.Body.Close()
	if r.StatusCode != http.StatusOK {
		return fmt.Errorf("status %d", r.StatusCode)
	}
	return nil
}

// PageProbe is the watchdog's liveness check: the PAGE must evaluate script. /json/version (CDPVersion) only proves
// the browser process is alive — an "Aw, Snap!" renderer crash or a hung renderer keeps answering it, so the kiosk
// would sit on a dead page until the nightly reboot (review I4, 2026-10-10). A crashed page answers with an error, a
// hung one not at all (the caller's context times out); both fail.
func PageProbe(ctx context.Context, port int) error {
	pages, err := cdpPages(ctx, port)
	if err != nil {
		return err
	}
	if len(pages) == 0 {
		return errors.New("no page open")
	}
	res, err := cdpCall(ctx, pages[0].WS, "Runtime.evaluate",
		map[string]any{"expression": "document.readyState", "returnByValue": true})
	if err != nil {
		return err
	}
	var r struct {
		Result struct {
			Value any `json:"value"`
		} `json:"result"`
	}
	if err := json.Unmarshal(res, &r); err != nil {
		return err
	}
	if _, ok := r.Result.Value.(string); !ok {
		return fmt.Errorf("page did not evaluate: %s", res)
	}
	return nil
}

func cdpPages(ctx context.Context, port int) ([]cdpTarget, error) {
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, cdpBase(port)+"/json/list", nil)
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer r.Body.Close()
	var all []cdpTarget
	if err := json.NewDecoder(r.Body).Decode(&all); err != nil {
		return nil, err
	}
	var pages []cdpTarget
	for _, t := range all {
		if t.Type == "page" {
			pages = append(pages, t)
		}
	}
	return pages, nil
}

var cdpID atomic.Int64

// cdpCall sends one CDP command on a page's websocket and returns its result.
func cdpCall(ctx context.Context, wsURL, method string, params any) (json.RawMessage, error) {
	c, _, err := websocket.Dial(ctx, wsURL, nil)
	if err != nil {
		return nil, err
	}
	defer c.Close(websocket.StatusNormalClosure, "")
	c.SetReadLimit(16 << 20)
	id := cdpID.Add(1)
	msg, _ := json.Marshal(map[string]any{"id": id, "method": method, "params": params})
	if err := c.Write(ctx, websocket.MessageText, msg); err != nil {
		return nil, err
	}
	for {
		_, data, err := c.Read(ctx)
		if err != nil {
			return nil, err
		}
		var r struct {
			ID     int64                     `json:"id"`
			Result json.RawMessage           `json:"result"`
			Error  *struct{ Message string } `json:"error"`
		}
		if json.Unmarshal(data, &r) == nil && r.ID == id {
			if r.Error != nil {
				return nil, fmt.Errorf("%s: %s", method, r.Error.Message)
			}
			return r.Result, nil
		}
	}
}

func IsErrorPage(url string) bool { return strings.HasPrefix(url, "chrome-error://") }
