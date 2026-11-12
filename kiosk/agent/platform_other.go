//go:build !windows

package main

import (
	"context"
	"errors"
	"time"
)

var errNotWindows = errors.New("not Windows")

// Linux/macOS stand-ins so the package builds and tests anywhere; the real ones are in platform_windows.go. None of
// them can reboot anything: rebootNow and runShutdown refuse.
func keepAwake()                                  {}
func setBrightness(int) error                     { return nil }
func freeMB() int                                 { return -1 }
func killStrayChrome()                            {}
func reconnectWifi(context.Context, string) error { return nil }
func wifiState(context.Context) (WifiState, error) {
	return WifiState{}, errNotWindows
}
func scanWifi() error                       { return errNotWindows }
func idleFor() (time.Duration, error)       { return 0, errNotWindows }
func runShutdown(...string) (string, error) { return "", errNotWindows }
func rebootNow(string) error                { return errNotWindows }
