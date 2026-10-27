# Fixed rolling admission window

`allow(events, now)` returns true exactly when fewer than two events fall in `(now-10, now]`.
Timestamps are caller-provided numbers. Ignore expired and future events; do not mutate inputs.
