import { useCallback, useEffect, useRef, useState } from "react";
import { parseSseDataLine, resolveDoneGeneratedText } from "./protocol";
import type { GenerationParams, GenerationStats } from "./types";

export function useGenerateStream() {
	const [isGenerating, setIsGenerating] = useState(false);
	const [generatedText, setGeneratedText] = useState("");
	const [stats, setStats] = useState<GenerationStats | null>(null);
	const abortControllerRef = useRef<AbortController | null>(null);
	const activeReaderRef =
		useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
	const generationIdRef = useRef(0);

	const cancelTransport = useCallback((updateState: boolean) => {
		generationIdRef.current++;
		const reader = activeReaderRef.current;
		activeReaderRef.current = null;
		if (reader) reader.cancel().catch(() => {});
		const controller = abortControllerRef.current;
		abortControllerRef.current = null;
		if (controller) controller.abort();
		if (updateState) setIsGenerating(false);
	}, []);

	const stop = useCallback(() => {
		cancelTransport(true);
	}, [cancelTransport]);

	const clear = useCallback(() => {
		cancelTransport(true);
		setGeneratedText("");
		setStats(null);
	}, [cancelTransport]);

	useEffect(() => {
		return () => cancelTransport(false);
	}, [cancelTransport]);

	const generate = useCallback(
		async (params: GenerationParams, onError?: (err: string) => void) => {
			stop();

			const currentGenId = ++generationIdRef.current;
			setIsGenerating(true);
			setGeneratedText("");
			setStats(null);

			const abortController = new AbortController();
			abortControllerRef.current = abortController;
			const startTime = performance.now();
			let tokensReceived = 0;
			let backendError = false;

			try {
				const response = await fetch("/api/generate/stream", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(params),
					signal: abortController.signal,
				});

				if (currentGenId !== generationIdRef.current) return;

				if (!response.ok) {
					let errMsg = `Lỗi sinh văn bản (${response.status})`;
					try {
						const errJson = await response.json();
						errMsg = errJson.detail || errJson.message || errMsg;
					} catch {
						// Response is not JSON; keep the status-based message.
					}
					throw new Error(errMsg);
				}

				const reader = response.body?.getReader();
				if (!reader) {
					throw new Error("Không thể mở luồng dữ liệu stream");
				}
				activeReaderRef.current = reader;

				const decoder = new TextDecoder();
				let buffer = "";

				while (true) {
					if (currentGenId !== generationIdRef.current) {
						reader.cancel().catch(() => {});
						break;
					}

					const { done, value } = await reader.read();
					if (done || currentGenId !== generationIdRef.current) break;

					buffer += decoder.decode(value, { stream: true });
					const lines = buffer.split("\n");
					buffer = lines.pop() || "";

					for (const line of lines) {
						if (currentGenId !== generationIdRef.current) break;
						let parsed;
						try {
							parsed = parseSseDataLine(line);
						} catch {
							continue;
						}
						if (!parsed) continue;

						if (parsed.error || parsed.type === "error") {
							const errMsg =
								typeof parsed.error === "string"
									? parsed.error
									: typeof parsed.message === "string"
										? parsed.message
										: "Lỗi khi sinh văn bản";
							backendError = true;
							onError?.(errMsg);
							continue;
						}

						const token = parsed.token ?? parsed.text;
						if (typeof token === "string") {
							setGeneratedText((prev) => prev + token);
							tokensReceived += 1;
						}

						if (parsed.type === "done") {
							if (tokensReceived === 0) {
								const fallback = resolveDoneGeneratedText(
									parsed,
									params.prompt,
								);
								if (fallback !== undefined) setGeneratedText(fallback);
							}
							setStats({
								tps: typeof parsed.tps === "number" ? parsed.tps : 0,
								elapsed_sec:
									typeof parsed.elapsed_sec === "number"
										? parsed.elapsed_sec
										: 0,
								token_count:
									typeof parsed.token_count === "number"
										? parsed.token_count
										: tokensReceived,
							});
						} else if (
							typeof parsed.stats === "object" &&
							parsed.stats !== null
						) {
							setStats(parsed.stats as GenerationStats);
						}
					}
				}

				if (currentGenId === generationIdRef.current && !backendError) {
					const elapsedSec = Math.max(
						(performance.now() - startTime) / 1000,
						0.01,
					);
					setStats(
						(prev) =>
							prev || {
								tps: parseFloat(
									(tokensReceived / elapsedSec).toFixed(1),
								),
								elapsed_sec: parseFloat(elapsedSec.toFixed(2)),
								token_count: tokensReceived,
							},
					);
				}
			} catch (err: unknown) {
				if (currentGenId === generationIdRef.current) {
					const error = err as Error;
					if (error.name !== "AbortError") {
						onError?.(error.message || "Lỗi khi sinh văn bản");
					}
				}
			} finally {
				if (currentGenId === generationIdRef.current) {
					setIsGenerating(false);
					activeReaderRef.current = null;
					abortControllerRef.current = null;
				}
			}
		},
		[stop],
	);

	return {
		isGenerating,
		generatedText,
		stats,
		generate,
		stop,
		clear,
	};
}
