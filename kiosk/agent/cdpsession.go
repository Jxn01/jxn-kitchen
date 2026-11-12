package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"

	"github.com/coder/websocket"
)

// Session is ONE long-lived CDP connection to a page. The overlay needs it: what a session registers
// (Page.addScriptToEvaluateOnNewDocument, Runtime.addBinding, Page.setBypassCSP) lives only as long as the session,
// so the short dial-send-close calls (cdpCall) can't carry it. A reader goroutine matches replies to calls by id and
// hands events out; Done() closes when the connection ends (Chrome restarted, page gone).
type Session struct {
	c       *websocket.Conn
	next    atomic.Int64
	mu      sync.Mutex
	pending map[int64]chan cdpReply
	events  chan CDPEvent
	done    chan struct{}
	err     error
}

type CDPEvent struct {
	Method string
	Params json.RawMessage
}

type cdpReply struct {
	result json.RawMessage
	err    error
}

var ErrSessionClosed = errors.New("cdp session closed")

func DialSession(ctx context.Context, wsURL string) (*Session, error) {
	c, _, err := websocket.Dial(ctx, wsURL, nil)
	if err != nil {
		return nil, err
	}
	c.SetReadLimit(32 << 20)
	s := &Session{c: c, pending: map[int64]chan cdpReply{}, events: make(chan CDPEvent, 256), done: make(chan struct{})}
	go s.read()
	return s, nil
}

func (s *Session) read() {
	defer func() {
		s.mu.Lock()
		for id, ch := range s.pending {
			ch <- cdpReply{err: ErrSessionClosed}
			delete(s.pending, id)
		}
		s.mu.Unlock()
		close(s.done)
	}()
	for {
		_, data, err := s.c.Read(context.Background())
		if err != nil {
			s.err = err
			return
		}
		var m struct {
			ID     int64           `json:"id"`
			Result json.RawMessage `json:"result"`
			Error  *struct {
				Message string `json:"message"`
			} `json:"error"`
			Method string          `json:"method"`
			Params json.RawMessage `json:"params"`
		}
		if json.Unmarshal(data, &m) != nil {
			continue
		}
		if m.ID != 0 {
			s.mu.Lock()
			ch := s.pending[m.ID]
			delete(s.pending, m.ID)
			s.mu.Unlock()
			if ch != nil {
				r := cdpReply{result: m.Result}
				if m.Error != nil {
					r.err = errors.New(m.Error.Message)
				}
				ch <- r
			}
			continue
		}
		if m.Method != "" {
			select {
			case s.events <- CDPEvent{m.Method, m.Params}:
			default: // nobody keeping up (Runtime.enable is chatty): drop rather than stall replies
			}
		}
	}
}

// Call sends one command and waits for its reply.
func (s *Session) Call(ctx context.Context, method string, params any) (json.RawMessage, error) {
	id := s.next.Add(1)
	ch := make(chan cdpReply, 1)
	s.mu.Lock()
	select {
	case <-s.done:
		s.mu.Unlock()
		return nil, ErrSessionClosed
	default:
	}
	s.pending[id] = ch
	s.mu.Unlock()
	if params == nil {
		params = map[string]any{}
	}
	msg, _ := json.Marshal(map[string]any{"id": id, "method": method, "params": params})
	if err := s.c.Write(ctx, websocket.MessageText, msg); err != nil {
		s.mu.Lock()
		delete(s.pending, id)
		s.mu.Unlock()
		return nil, err
	}
	select {
	case r := <-ch:
		if r.err != nil {
			return nil, fmt.Errorf("%s: %w", method, r.err)
		}
		return r.result, nil
	case <-ctx.Done():
		s.mu.Lock()
		delete(s.pending, id)
		s.mu.Unlock()
		return nil, ctx.Err()
	}
}

func (s *Session) Events() <-chan CDPEvent { return s.events }
func (s *Session) Done() <-chan struct{}   { return s.done }
func (s *Session) Close()                  { s.c.Close(websocket.StatusNormalClosure, "") }
