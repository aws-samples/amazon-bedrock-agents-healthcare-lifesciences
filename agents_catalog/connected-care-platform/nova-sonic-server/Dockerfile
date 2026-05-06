FROM --platform=linux/amd64 node:18-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --production=false

COPY tsconfig.json ./
COPY src/ ./src/
COPY public/ ./public/

RUN npx tsc

EXPOSE 3001

CMD ["node", "dist/server.js"]
