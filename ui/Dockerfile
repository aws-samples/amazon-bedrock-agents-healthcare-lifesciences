# Step 1: Use Node.js base image
FROM --platform=linux/amd64 public.ecr.aws/docker/library/node:18-alpine3.21 AS builder

# Set working directory
WORKDIR /app

# Copy package.json and install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy the rest of the app and build
COPY . .
RUN npm run build

# Step 2: Create a lightweight production image
FROM --platform=linux/amd64 public.ecr.aws/docker/library/node:18-alpine3.21

WORKDIR /app

# Copy only necessary files from the builder
COPY --from=builder /app ./

# Expose the Next.js default port
EXPOSE 3000

# Start the app in production mode 1
CMD ["npm", "start"]
