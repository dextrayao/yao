// Inference provider abstraction. v1 ships a local Ollama provider; a cloud
// provider (e.g. Claude for special moments) can be added later behind this
// same interface without touching whisper logic.

export interface GenerateOptions {
  system?: string;
  maxTokens?: number;
  temperature?: number;
}

export interface InferenceProvider {
  readonly name: string;
  /** Returns generated text, or null on any failure (caller falls back). */
  generate(prompt: string, opts?: GenerateOptions): Promise<string | null>;
  /** Cheap liveness check. */
  available(): Promise<boolean>;
}
