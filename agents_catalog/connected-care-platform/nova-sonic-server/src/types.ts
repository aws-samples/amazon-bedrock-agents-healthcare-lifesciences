export interface InferenceConfig {
  maxTokens: number;
  topP: number;
  temperature: number;
}

export const DefaultAudioInputConfiguration = {
  mediaType: "audio/lpcm",
  sampleRateHertz: 16000,
  sampleSizeBits: 16,
  channelCount: 1,
  audioType: "SPEECH",
  encoding: "base64",
};

export const DefaultAudioOutputConfiguration = {
  mediaType: "audio/lpcm",
  sampleRateHertz: 24000,
  sampleSizeBits: 16,
  channelCount: 1,
  encoding: "base64",
  voiceId: "tiffany",
};

export const DefaultTextConfiguration = {
  mediaType: "text/plain",
};

export const CLINICAL_SYSTEM_PROMPT = `You are Ana, a clinical voice assistant for the Connected Care Platform.

Rules:
- Give ONE sentence answers. Two sentences maximum.
- State the key finding immediately. No preamble.
- Use specific numbers only for critical vitals.
- End with a short follow-up question only if clinically relevant.
- Never read lists, tables, or raw data. Summarize the single most important point.
- Never repeat information the clinician already knows.`;
