# Use Node 20 for development setup
FROM node:20-alpine

WORKDIR /app

# Copy package config
COPY package.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY . .

# Expose Vite's default dev port
EXPOSE 5173

# Start development server with host exposed to docker bridge
CMD ["npm", "run", "dev", "--", "--host"]
