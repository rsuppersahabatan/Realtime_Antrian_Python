# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package.json and install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy all files and build
COPY . .
RUN npm run build

# Serve stage using Nginx
FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy custom nginx config (with SPA fallback)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built client assets from build stage
COPY --from=build /app/dist/client /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
