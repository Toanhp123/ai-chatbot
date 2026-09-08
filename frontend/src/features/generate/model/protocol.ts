export interface GenerationSseEvent {
	type?: string;
	token?: unknown;
	text?: unknown;
	error?: unknown;
	message?: unknown;
	full_text?: unknown;
	generated_text?: unknown;
	tps?: unknown;
	elapsed_sec?: unknown;
	token_count?: unknown;
	stats?: unknown;
	[key: string]: unknown;
}

export function parseSseDataLine(line: string): GenerationSseEvent | null {
	if (!line.startsWith("data: ")) return null;
	const payload = line.slice(6).trim();
	if (!payload) return null;
	const parsed: unknown = JSON.parse(payload);
	if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
		return null;
	}
	return parsed as GenerationSseEvent;
}

export function resolveDoneGeneratedText(
	event: GenerationSseEvent,
	prompt: string,
): string | undefined {
	if (typeof event.generated_text === "string") {
		return event.generated_text;
	}
	if (typeof event.full_text !== "string") {
		return undefined;
	}
	if (!event.full_text.startsWith(prompt)) {
		return undefined;
	}
	return event.full_text.slice(prompt.length);
}
