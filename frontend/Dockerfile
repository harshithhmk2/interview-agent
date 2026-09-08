# Stage 1: Build static assets using Node
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package configurations
COPY package.json package-lock.json* ./

# Install packages
RUN npm install

# Copy application code
COPY . .

# Run the build script to compile the frontend (Vite compiles to /app/dist)
RUN npm run build

# Stage 2: Serve the compiled static assets using Nginx
FROM nginx:alpine

# Copy built assets from builder stage (Vite builds to /app/dist)
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with API reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]
