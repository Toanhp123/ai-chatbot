import { useState, useRef, useCallback } from "react";
import type { GenerationParams, GenerationStats } from "./types";

export function useGenerateStream() {
	const [isGenerating, setIsGenerating] = useState(false);
	const [generatedText, setGeneratedText] = useState("");
	const [stats, setStats] = useState<GenerationStats | null>(null);
	const abortControllerRef = useRef<AbortController | null>(null);
	const activeReaderRef =
		useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
	const generationIdRef = useRef(0);

	const stop = useCallback(() => {
		generationIdRef.current++;
		if (activeReaderRef.current) {
			activeReaderRef.current.cancel().catch(() => {});
			activeReaderRef.current = null;
		}
		if (abortControllerRef.current) {
			abortControllerRef.current.abort();
			abortControllerRef.current = null;
		}
		setIsGenerating(false);
	}, []);

	const clear = useCallback(() => {
		generationIdRef.current++;
		if (activeReaderRef.current) {
			activeReaderRef.current.cancel().catch(() => {});
			activeReaderRef.current = null;
		}
		if (abortControllerRef.current) {
			abortControllerRef.current.abort();
			abortControllerRef.current = null;
		}
		setIsGenerating(false);
		setGeneratedText("");
		setStats(null);
	}, []);

	const generate = useCallback(
		async (params: GenerationParams, onError?: (err: string) => void) => {
			// Hủy bỏ luồng đang chạy trước đó nếu có
			stop();

			const currentGenId = ++generationIdRef.current;
			setIsGenerating(true);
			setGeneratedText("");
			setStats(null);

			const abortController = new AbortController();
			abortControllerRef.current = abortController;
			const startTime = performance.now();
			let tokensReceived = 0;

			try {
				// Endpoint backend: /api/generate/stream
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
						// ignore
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
						if (line.startsWith("data: ")) {
							const dataStr = line.slice(6).trim();
							if (!dataStr) continue;

							try {
								const parsed = JSON.parse(dataStr);

								// 1. Kiểm tra lỗi trả về từ backend
								if (parsed.error || parsed.type === "error") {
									const errMsg =
										parsed.error ||
										parsed.message ||
										"Lỗi khi sinh văn bản";
									if (
										currentGenId === generationIdRef.current
									) {
										onError?.(errMsg);
									}
									continue;
								}

								// 2. Thu nhận token
								const token = parsed.token ?? parsed.text;
								if (
									typeof token === "string" &&
									currentGenId === generationIdRef.current
								) {
									setGeneratedText((prev) => prev + token);
									tokensReceived += 1;
								}

								// 3. Xử lý sự kiện hoàn tất
								if (
									parsed.type === "done" &&
									currentGenId === generationIdRef.current
								) {
									if (
										parsed.full_text &&
										tokensReceived === 0
									) {
										setGeneratedText(parsed.full_text);
									}
									setStats({
										tps:
											typeof parsed.tps === "number"
												? parsed.tps
												: 0,
										elapsed_sec:
											typeof parsed.elapsed_sec ===
											"number"
												? parsed.elapsed_sec
												: 0,
										token_count:
											typeof parsed.token_count ===
											"number"
												? parsed.token_count
												: tokensReceived,
									});
								} else if (
									parsed.stats &&
									currentGenId === generationIdRef.current
								) {
									setStats(parsed.stats);
								}
							} catch {
								if (currentGenId === generationIdRef.current) {
									setGeneratedText((prev) => prev + dataStr);
									tokensReceived += 1;
								}
							}
						}
					}
				}

				if (currentGenId === generationIdRef.current) {
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
