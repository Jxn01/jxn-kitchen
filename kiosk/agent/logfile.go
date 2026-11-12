package main

import (
	"io"
	"log"
	"os"
	"path/filepath"
	"sync"
)

// rotatingFile: append to path; past maxBytes, rename it to path+".old" (one generation kept) and start afresh.
type rotatingFile struct {
	mu       sync.Mutex
	path     string
	maxBytes int64
	f        *os.File
}

func (r *rotatingFile) Write(p []byte) (int, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.f == nil {
		f, err := os.OpenFile(r.path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
		if err != nil {
			return len(p), nil // logging must never take the kiosk down
		}
		r.f = f
	}
	if st, err := r.f.Stat(); err == nil && st.Size()+int64(len(p)) > r.maxBytes {
		r.f.Close()
		_ = os.Rename(r.path, r.path+".old")
		r.f, _ = os.OpenFile(r.path, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o644)
		if r.f == nil {
			return len(p), nil
		}
	}
	return r.f.Write(p)
}

// Close releases the file. The agent never needs it (the log lives as long as the process), but Windows refuses to
// delete or move a file that is still open — a test that leaves it open fails its own cleanup there (seen running
// the windows/386 test binary under Wine).
func (r *rotatingFile) Close() error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.f == nil {
		return nil
	}
	err := r.f.Close()
	r.f = nil
	return err
}

func setupLog(path string) {
	_ = os.MkdirAll(filepath.Dir(path), 0o755)
	var w io.Writer = &rotatingFile{path: path, maxBytes: 1 << 20}
	log.SetOutput(w)
	log.SetFlags(log.LstdFlags)
}
