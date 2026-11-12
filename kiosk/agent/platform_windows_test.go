//go:build windows

package main

import (
	"context"
	"testing"
)

// The real WLAN API and GetLastInputInfo calls, through the real DLLs. Under Wine (how this runs on a Linux dev machine)
// wlanapi is a stub with no interfaces, so this proves only that the calls and the list parsing are memory-safe on
// the empty/error path — the interface and scan paths are proven on the kiosk by -selftest-reboot. Never call
// runShutdown here.
func TestWindowsWlanAndIdleCallsAreSafe_UnderWineOnlyTheEmptyPath(t *testing.T) {
	st, err := wifiState(context.Background())
	t.Logf("wifiState: %+v (%s), err=%v", st, st, err)
	if err == nil && st.Interfaces > 0 && st.State == "" {
		t.Fatal("an interface with no state")
	}
	t.Logf("scanWifi: %v", scanWifi())
	d, err := idleFor()
	t.Logf("idleFor: %v, err=%v", d, err)
	if err == nil && d < 0 {
		t.Fatalf("negative idle %v", d)
	}
}
