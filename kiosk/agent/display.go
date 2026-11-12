package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"
)

// BrightnessArgs is the wmic command line that sets the panel backlight. Clamped to >= 5 %: the display is never
// turned off (Modern Standby box: display-off = standby = Wi-Fi gone).
func BrightnessArgs(pct int) []string {
	if pct < 5 {
		pct = 5
	}
	if pct > 100 {
		pct = 100
	}
	return []string{`/NAMESPACE:\\root\wmi`, "PATH", "WmiMonitorBrightnessMethods", "WHERE", "Active=TRUE", "CALL",
		"WmiSetBrightness", fmt.Sprintf("Brightness=%d", pct), "Timeout=0"}
}

type displayState struct {
	Night      bool `json:"night"`
	Brightness int  `json:"brightness"`
}

// displayLoop follows /api/kiosk/display and applies the backlight whenever the wanted level changes.
func displayLoop(ctx context.Context, cfg Config, setBrightness func(int) error) {
	last := -1
	for {
		if st, err := fetchDisplay(ctx, cfg.Server); err != nil {
			log.Printf("display: %v", err)
		} else if st.Brightness != last {
			if err := setBrightness(st.Brightness); err != nil {
				log.Printf("display: set %d%%: %v", st.Brightness, err)
			} else {
				log.Printf("display: backlight %d%% (night=%v)", st.Brightness, st.Night)
				last = st.Brightness
			}
		}
		sleepCtx(ctx, cfg.DisplayEvery)
		if ctx.Err() != nil {
			return
		}
	}
}

func fetchDisplay(ctx context.Context, server string) (displayState, error) {
	var st displayState
	cctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	req, _ := http.NewRequestWithContext(cctx, http.MethodGet, server+"/api/kiosk/display", nil)
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		return st, err
	}
	defer r.Body.Close()
	if r.StatusCode != http.StatusOK {
		return st, fmt.Errorf("status %d", r.StatusCode)
	}
	return st, json.NewDecoder(r.Body).Decode(&st)
}
