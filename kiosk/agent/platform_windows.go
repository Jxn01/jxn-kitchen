//go:build windows

package main

import (
	"context"
	"fmt"
	"os/exec"
	"runtime"
	"strings"
	"syscall"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"
)

const createNoWindow = 0x08000000

var (
	kernel32                    = windows.NewLazySystemDLL("kernel32.dll")
	procSetThreadExecutionState = kernel32.NewProc("SetThreadExecutionState")
	procGlobalMemoryStatusEx    = kernel32.NewProc("GlobalMemoryStatusEx")
)

// memoryStatusEx mirrors the Win32 MEMORYSTATUSEX struct.
type memoryStatusEx struct {
	Length               uint32
	MemoryLoad           uint32
	TotalPhys            uint64
	AvailPhys            uint64
	TotalPageFile        uint64
	AvailPageFile        uint64
	TotalVirtual         uint64
	AvailVirtual         uint64
	AvailExtendedVirtual uint64
}

// keepAwake asks Windows to keep the system and the display on, for as long as this process lives. The request
// belongs to a thread, so it runs on a goroutine locked to its OS thread that never ends.
func keepAwake() {
	const esContinuous, esSystemRequired, esDisplayRequired = 0x80000000, 0x00000001, 0x00000002
	go func() {
		runtime.LockOSThread()
		procSetThreadExecutionState.Call(uintptr(esContinuous | esSystemRequired | esDisplayRequired))
		select {}
	}()
}

func setBrightness(pct int) error {
	cmd := exec.Command(`C:\Windows\System32\wbem\wmic.exe`, BrightnessArgs(pct)...)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: createNoWindow}
	return cmd.Run()
}

// reconnectWifi asks the radio for a fresh scan, drops the association and joins the saved profile again: a fresh
// 4-way handshake, which is what a link left dead by a missed re-key needs. The scan is for the other mode, a radio
// whose list of visible networks is empty (netsh refuses every connect without Windows even starting
// one); it is best-effort — a scan that cannot run is noted in the error only if the connect fails too. Everything
// runs on the kiosk user's limited token. The 4 s after the scan is the time drivers are given to finish one; the 3 s after the
// disconnect lets the adapter settle; the disconnect's failure is ignored (an adapter that is already down).
// netsh's own words go into the error: "exit status 1" alone cannot tell "network not available" from "no
// wireless interface".
func reconnectWifi(ctx context.Context, profile string) error {
	note := ""
	if err := scanWifi(); err != nil {
		note = "scan: " + err.Error() + "; "
	} else {
		sleepCtx(ctx, 4*time.Second)
	}
	args := WifiReconnectArgs(profile)
	_, _ = runCapture(netshExe, args[0]...)
	sleepCtx(ctx, 3*time.Second)
	out, err := runCapture(netshExe, args[1]...)
	if err != nil {
		return fmt.Errorf("%s%v: %s", note, err, out)
	}
	return nil
}

const (
	netshExe    = `C:\Windows\System32\netsh.exe`
	shutdownExe = `C:\Windows\System32\shutdown.exe`
)

// runCapture runs a console program without a window and returns its output (stdout and stderr) as one line.
func runCapture(exe string, args ...string) (string, error) {
	cmd := exec.Command(exe, args...)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: createNoWindow}
	out, err := cmd.CombinedOutput()
	return oneLine(string(out)), err
}

// runShutdown runs shutdown.exe; the kiosk user's limited token keeps SeShutdownPrivilege (proven by
// -selftest-reboot, which schedules a reboot and aborts it).
func runShutdown(args ...string) (string, error) { return runCapture(shutdownExe, args...) }

// rebootNow schedules a reboot in 30 s with reason in the System log (event 1074).
func rebootNow(reason string) error {
	out, err := runShutdown(RebootArgs(30*time.Second, reason)...)
	if err != nil {
		return fmt.Errorf("%v: %s", err, out)
	}
	return nil
}

var (
	wlanapi                = windows.NewLazySystemDLL("wlanapi.dll")
	procWlanOpenHandle     = wlanapi.NewProc("WlanOpenHandle")
	procWlanCloseHandle    = wlanapi.NewProc("WlanCloseHandle")
	procWlanEnumInterfaces = wlanapi.NewProc("WlanEnumInterfaces")
	procWlanScan           = wlanapi.NewProc("WlanScan")
	procWlanFreeMemory     = wlanapi.NewProc("WlanFreeMemory")
	user32                 = windows.NewLazySystemDLL("user32.dll")
	procGetLastInputInfo   = user32.NewProc("GetLastInputInfo")
	procGetTickCount       = kernel32.NewProc("GetTickCount")
)

// withWlan opens a WLAN API session, lists the Wi-Fi interfaces and hands both to fn. No elevation needed.
func withWlan(fn func(h uintptr, ifs []wlanIface) error) error {
	if err := procWlanOpenHandle.Find(); err != nil {
		return fmt.Errorf("wlanapi: %w", err)
	}
	var negotiated uint32
	var h uintptr
	if r, _, _ := procWlanOpenHandle.Call(2, 0, uintptr(unsafe.Pointer(&negotiated)), uintptr(unsafe.Pointer(&h))); r != 0 {
		return fmt.Errorf("WlanOpenHandle: %w", syscall.Errno(r))
	}
	defer procWlanCloseHandle.Call(h, 0)
	var list *byte // WLAN_INTERFACE_INFO_LIST, allocated by the API
	if r, _, _ := procWlanEnumInterfaces.Call(h, 0, uintptr(unsafe.Pointer(&list))); r != 0 {
		return fmt.Errorf("WlanEnumInterfaces: %w", syscall.Errno(r))
	}
	if list == nil {
		return fmt.Errorf("WlanEnumInterfaces: no list")
	}
	defer procWlanFreeMemory.Call(uintptr(unsafe.Pointer(list)))
	n := *(*uint32)(unsafe.Pointer(list))
	if n > 64 {
		return fmt.Errorf("WlanEnumInterfaces: implausible count %d", n)
	}
	ifs, err := parseWlanInterfaceList(unsafe.Slice(list, 8+int(n)*wlanInterfaceInfoSize))
	if err != nil {
		return err
	}
	return fn(h, ifs)
}

// wifiState reports the Wi-Fi interfaces and the first one's state, as the WLAN service sees them.
func wifiState(context.Context) (WifiState, error) {
	var st WifiState
	err := withWlan(func(_ uintptr, ifs []wlanIface) error {
		st.Interfaces = len(ifs)
		if len(ifs) > 0 {
			st.State = wlanStateName(ifs[0].State)
		}
		return nil
	})
	return st, err
}

// scanWifi asks every Wi-Fi interface for a fresh scan (what opening the Wi-Fi menu does); it returns at once and
// the driver has up to 4 s to finish.
func scanWifi() error {
	return withWlan(func(h uintptr, ifs []wlanIface) error {
		if len(ifs) == 0 {
			return fmt.Errorf("no Wi-Fi interface")
		}
		var errs []string
		for _, i := range ifs {
			g := i.GUID
			if r, _, _ := procWlanScan.Call(h, uintptr(unsafe.Pointer(&g)), 0, 0, 0); r != 0 {
				errs = append(errs, fmt.Sprintf("WlanScan: %v", syscall.Errno(r)))
			}
		}
		if len(errs) > 0 {
			return fmt.Errorf("%s", strings.Join(errs, "; "))
		}
		return nil
	})
}

// idleFor is the time since the last touch, click or key in this session (GetLastInputInfo; the agent runs in the
// kiosk's desktop session, so that is the kitchen screen).
func idleFor() (time.Duration, error) {
	li := struct{ cbSize, dwTime uint32 }{cbSize: 8}
	if r, _, e := procGetLastInputInfo.Call(uintptr(unsafe.Pointer(&li))); r == 0 {
		return 0, fmt.Errorf("GetLastInputInfo: %v", e)
	}
	now, _, _ := procGetTickCount.Call()
	return time.Duration(uint32(now)-li.dwTime) * time.Millisecond, nil
}

func freeMB() int {
	m := memoryStatusEx{}
	m.Length = uint32(unsafe.Sizeof(m))
	if ok, _, _ := procGlobalMemoryStatusEx.Call(uintptr(unsafe.Pointer(&m))); ok == 0 {
		return -1
	}
	return int(m.AvailPhys / (1 << 20))
}

// killStrayChrome ends every chrome.exe of this user before a launch (the kiosk runs no other Chrome). Without it,
// a Chrome left from before the agent started would swallow each launch (see Supervisor.BeforeStart).
func killStrayChrome() {
	cmd := exec.Command(`C:\Windows\System32\taskkill.exe`, "/F", "/IM", "chrome.exe")
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: createNoWindow}
	_ = cmd.Run() // "not found" is the normal case
}
