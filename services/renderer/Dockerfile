FROM node:20-bookworm-slim

# headless-gl (`gl`) builds native bindings and needs a software OpenGL stack
# (Mesa) plus the X libs it links against, even though rendering is off-screen.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        make \
        g++ \
        pkg-config \
        libgl1-mesa-dev \
        libxi-dev \
        libglu1-mesa-dev \
        libglew-dev \
        xvfb \
        xauth \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json .
RUN npm install --omit=dev

COPY src/ src/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8002

# entrypoint.sh starts the Xvfb virtual display the Mesa GL context attaches to,
# then execs node as PID 1.
CMD ["./entrypoint.sh"]
