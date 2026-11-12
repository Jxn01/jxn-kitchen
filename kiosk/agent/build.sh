#!/usr/bin/env bash
# Build the kiosk agent for the PIPO (32-bit Windows 10): kiosk/agent/agent.exe (gitignored).
set -euo pipefail
cd "$(dirname "$0")"
export GOPATH="${GOPATH:-$HOME/.cache/go}" GOMODCACHE="${GOMODCACHE:-$HOME/.cache/go/mod}"
go test ./...
V="$(git describe --always --dirty 2>/dev/null || echo dev)"
GOOS=windows GOARCH=386 CGO_ENABLED=0 go build -trimpath -ldflags "-H=windowsgui -s -w -X main.version=$V" -o agent.exe .
echo "built agent.exe ($V, $(stat -c %s agent.exe) bytes)"
