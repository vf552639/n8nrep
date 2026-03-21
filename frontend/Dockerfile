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

# Copy built assets from builder
COPY --from=builder /app/dist ./dist

# Expose production port
EXPOSE 3000

# Start server
CMD ["serve", "-s", "dist", "-l", "3000"]
