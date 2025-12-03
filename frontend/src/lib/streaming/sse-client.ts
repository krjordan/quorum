export interface SSEClientOptions {
  onChunk?: (data: string) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
  maxRetries?: number;
}

export class SSEClient {
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private retryCount = 0;
  private readonly maxRetries: number;
  private readonly options: SSEClientOptions;
  private abortController: AbortController | null = null;

  constructor(options: SSEClientOptions = {}) {
    this.options = options;
    this.maxRetries = options.maxRetries || 5;
  }

  async connect(response: Response): Promise<void> {
    try {
      if (!response.body) {
        throw new Error("Response body is null");
      }

      this.abortController = new AbortController();
      this.reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = '';

      while (true) {
        const { done, value } = await this.reader.read();

        if (done) {
          this.options.onComplete?.();
          break;
        }

        const decoded = decoder.decode(value, { stream: true });
        buffer += decoded;

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim() === '') continue; // Skip empty lines

          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6); // Remove 'data: ' prefix
              const data = JSON.parse(jsonStr);

              if (data.error) {
                console.error("Stream error:", data);
                this.options.onError?.(new Error(data.content || "Stream error"));
                this.disconnect();
                return;
              }

              if (data.done) {
                this.options.onComplete?.();
                this.disconnect();
                return;
              }

              if (data.content) {
                this.options.onChunk?.(data.content);
              }
            } catch (error) {
              console.error("Error parsing SSE data:", error, "Line:", line);
            }
          }
        }
      }

      this.retryCount = 0;
    } catch (error) {
      console.error("SSE stream error:", error);
      this.handleError(error as Error);
    }
  }

  private handleError(error: Error): void {
    this.disconnect();

    if (this.retryCount < this.maxRetries) {
      this.retryCount++;
      const backoffDelay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
      console.log(`Retrying SSE connection (attempt ${this.retryCount}/${this.maxRetries}) in ${backoffDelay}ms`);
      // Note: Actual retry logic would be handled by the hook
    } else {
      this.options.onError?.(error);
    }
  }

  disconnect(): void {
    if (this.reader) {
      this.reader.cancel();
      this.reader = null;
    }
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  isConnected(): boolean {
    return this.reader !== null;
  }
}
