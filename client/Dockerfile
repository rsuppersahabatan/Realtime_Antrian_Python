# ---- Build stage ----
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
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