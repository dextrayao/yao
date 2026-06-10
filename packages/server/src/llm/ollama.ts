// Local LLM provider backed by Ollama on the Mac Studio. Free, unlimited,
// private — so whispers can run as often as we like.

import type { GenerateOptions, InferenceProvider } from './client.js';

export class OllamaProvider implements InferenceProvider {
  readonly name = 'ollama';

  constructor(
    private url: string,
    private model: string,
  ) {}

  async generate(prompt: string, opts: GenerateOptions = {}): Promise<string | null> {
    try {
      const res = await fetch(`${this.url}/api/generate`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          model: this.model,
          prompt,
          system: opts.system,
          stream: false,
          options: {
            num_predict: opts.maxTokens ?? 80,
            temperature: opts.temperature ?? 0.9,
          },
        }),
        // Whispers are decorative; never let a slow model stall anything.
        signal: AbortSignal.timeout(20_000),
      });
      if (!res.ok) return null;
      const data = (await res.json()) as { response?: string };
      const text = data.response?.trim();
      return text && text.length > 0 ? text : null;
    } catch {
      return null;
    }
  }

  async available(): Promise<boolean> {
    try {
      const res = await fetch(`${this.url}/api/tags`, {
        signal: AbortSignal.timeout(3_000),
      });
      return res.ok;
    } catch {
      return false;
    }
  }
}
