# ---- Build stage ----
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# VITE_API_URL HARUS tersedia saat build — Vite meng-inline nilainya ke bundle JS.
# Nilai ini harus URL backend yang BISA DIAKSES DARI BROWSER (IP/domain server),
# BUKAN 'localhost' dan BUKAN nama service Docker 'backend'.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ---- Production SSR stage ----
FROM node:20-alpine
WORKDIR /app

# Copy production build output
COPY --from=build /app/dist /app/dist
COPY --from=build /app/node_modules /app/node_modules
COPY --from=build /app/package.json /app/package.json

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000

# Jalankan TanStack Start SSR server
CMD ["node", "--enable-source-maps", "dist/server/server.js"]