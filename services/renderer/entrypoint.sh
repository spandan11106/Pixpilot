#!/bin/sh
# headless-gl needs an X display to create a GL context, but we render
# off-screen. Start a virtual framebuffer, then hand the container's PID 1 to
# node so it receives signals directly (xvfb-run as PID 1 is unreliable).
set -e

Xvfb :99 -screen 0 1024x1024x24 -nolisten tcp &
export DISPLAY=:99

# Give Xvfb a moment to come up before the first GL context request.
for _ in 1 2 3 4 5 6 7 8 9 10; do
  [ -e /tmp/.X11-unix/X99 ] && break
  sleep 0.3
done

exec node src/server.js
