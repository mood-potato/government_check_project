FROM oven/bun:1.2-alpine

WORKDIR /app

COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile

COPY frontend/ ./

ENV NODE_ENV=production \
    PORT=3000

EXPOSE 3000

CMD ["bun", "src/server.ts"]
