# Connected Care — Nova Sonic Voice Server

Real-time voice interface powered by Amazon Nova Sonic speech-to-speech model.

## Phase 1: Local Testing

### Prerequisites

- Node.js 18+
- AWS credentials configured with Bedrock access
- Amazon Nova Sonic model access enabled in us-east-1

### Setup

```bash
cd nova-sonic-server
npm install
```

### Run

```bash
npm run dev
```

Open http://localhost:3001 in Chrome (needs microphone access).

### Test

1. Click the microphone button
2. Wait for "Listening..." status
3. Speak: "Hello, can you hear me?"
4. Nova Sonic responds with human-like voice
5. Click mic again to stop

### How it works

```
Browser mic → PCM 16kHz audio → Socket.IO → Express server
  → Bedrock bidirectional stream → Nova Sonic
  → Audio response chunks → Socket.IO → Browser speakers
```

The server maintains a persistent bidirectional stream with Nova Sonic.
Audio flows in both directions simultaneously — you can interrupt mid-response.

### System Prompt

Nova Sonic is configured as "Ana", a clinical voice assistant. She responds
in 2-3 sentences with warm, professional language. This is Phase 1 — no
agent integration yet, just direct conversation with Nova Sonic.

### Troubleshooting

- "No audio output": Click anywhere on the page first (browser autoplay policy)
- "Connection failed": Check AWS credentials and Nova Sonic model access
- Choppy audio: Close other tabs using the microphone
