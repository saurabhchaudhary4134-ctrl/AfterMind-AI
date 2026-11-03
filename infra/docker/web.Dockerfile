# AfterMind AI — Web frontend Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci --frozen-lockfile

# Copy source and build
COPY apps/web/ .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# ── Runtime stage ──────────────────────────────────────────────
FROM node:20-alpine AS runtime

WORKDIR /app

RUN addgroup -S aftermind && adduser -S aftermind -G aftermind

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public 2>/dev/null || true

RUN chown -R aftermind:aftermind /app
USER aftermind

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget -qO- http://localhost:3000 || exit 1

ENV NODE_ENV=production
ENV PORT=3000
CMD ["node", "server.js"]
