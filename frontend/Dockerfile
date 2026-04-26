# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Copy package config
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Install 'serve'
RUN npm install -g serve

# Copy built assets from builder (node uid 1000 in official image)
COPY --from=builder --chown=1000:1000 /app/dist ./dist

USER node

# Expose production port
EXPOSE 3000

# Start server
CMD ["serve", "-s", "dist", "-l", "3000"]
