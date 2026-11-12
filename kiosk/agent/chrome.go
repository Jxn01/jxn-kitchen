package main

import (
	"context"
	"fmt"
	"log"
	"os/exec"
	"time"
)

func ChromeArgs(c Config) []string {
	return []string{
		"--kiosk",
		"--user-data-dir=" + c.Profile,
		fmt.Sprintf("--remote-debugging-port=%d", c.CDPPort),
		"--no-first-run",
		"--noerrdialogs",
		"--disable-session-crashed-bubble",
		"--disable-pinch",
		"--overscroll-history-navigation=0",
		"--disable-features=Translate",
		"--autoplay-policy=no-user-gesture-required",
		"--check-for-update-interval=604800",
		c.URL,
	}
}

// Proc is a running Chrome; Launcher starts one. Interfaces so the supervisor is testable on Linux.
type Proc interface {
	Wait() error
	Kill() error
}
type Launcher interface {
	Start() (Proc, error)
}

type execProc struct{ cmd *exec.Cmd }

func (p execProc) Wait() error { return p.cmd.Wait() }
func (p execProc) Kill() error { return p.cmd.Process.Kill() }

type execLauncher struct{ cfg Config }

func (l execLauncher) Start() (Proc, error) {
	cmd := exec.Command(l.cfg.Chrome, ChromeArgs(l.cfg)...)
	if err := cmd.Start(); err != nil {
		return nil, err
	}
	return execProc{cmd}, nil
}

// Supervisor keeps exactly one Chrome alive: relaunch when it exits, kill + relaunch when its page stops answering.
type Supervisor struct {
	Launch        Launcher
	Probe         func(context.Context) error
	RestartDelay  time.Duration
	ProbeEvery    time.Duration
	MaxProbeFails int
	// BeforeStart runs before every launch. On the kiosk it ends any Chrome still holding our profile: otherwise
	// each new chrome.exe hands its window to that one and exits at once, and the supervisor relaunches every
	// RestartDelay, opening a window each time.
	BeforeStart func()
}

func (s *Supervisor) Run(ctx context.Context) {
	for ctx.Err() == nil {
		if s.BeforeStart != nil {
			s.BeforeStart()
		}
		p, err := s.Launch.Start()
		if err != nil {
			log.Printf("chrome: start failed: %v", err)
			sleepCtx(ctx, s.RestartDelay)
			continue
		}
		log.Printf("chrome: started")
		exited := make(chan struct{})
		go func() { _ = p.Wait(); close(exited) }()
		s.watch(ctx, p, exited)
		if ctx.Err() != nil {
			_ = p.Kill()
			<-exited
			return
		}
		log.Printf("chrome: gone, restarting in %s", s.RestartDelay)
		sleepCtx(ctx, s.RestartDelay)
	}
}

// watch returns when Chrome exited, was killed for not answering, or ctx ended.
func (s *Supervisor) watch(ctx context.Context, p Proc, exited <-chan struct{}) {
	t := time.NewTicker(s.ProbeEvery)
	defer t.Stop()
	fails := 0
	for {
		select {
		case <-ctx.Done():
			return
		case <-exited:
			return
		case <-t.C:
			pctx, cancel := context.WithTimeout(ctx, 5*time.Second)
			err := s.Probe(pctx)
			cancel()
			if err == nil {
				fails = 0
				continue
			}
			fails++
			log.Printf("chrome: probe failed (%d/%d): %v", fails, s.MaxProbeFails, err)
			if fails >= s.MaxProbeFails {
				_ = p.Kill()
				<-exited
				return
			}
		}
	}
}

func sleepCtx(ctx context.Context, d time.Duration) {
	select {
	case <-ctx.Done():
	case <-time.After(d):
	}
}
