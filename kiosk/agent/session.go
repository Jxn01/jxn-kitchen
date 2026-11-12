package main

import "strings"

// IsRDP: the agent is the kiosk user's Windows shell, so it also starts for an RDP login. RDP gets a normal Explorer desktop
// (maintenance), the console gets the kitchen.
func IsRDP(getenv func(string) string) bool {
	return strings.HasPrefix(strings.ToUpper(getenv("SESSIONNAME")), "RDP-")
}
