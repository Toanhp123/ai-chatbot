import { useState, useEffect, useCallback } from "react";
import { checkpointApi } from "@/entities/checkpoint";
import type { Checkpoint } from "@/entities/checkpoint";
import { useGenerateStream } from "@/features/generate";
import type { SamplingHyperparams } from "@/features/generate";

export interface UsePlaygroundProps {
	activeCheckpoint?: string;
	onCheckpointLoaded?: (path: string) => void;
}

export function usePlayground({
	activeCheckpoint = "",
	onCheckpointLoaded,
}: UsePlaygroundProps = {}) {
	const [prompt, setPrompt] = useState("");
	const [submittedPrompt, setSubmittedPrompt] = useState("");
	const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
	const [selectedCheckpoint, setSelectedCheckpoint] = useState<string>(
		activeCheckpoint || "",
	);
	const [generators, setGenerators] = useState<string[]>([
		"default",
		"local",
		"pytorch",
	]);
	const [selectedGenerator, setSelectedGenerator] =
		useState<string>("default");
	const [isLoadingCp, setIsLoadingCp] = useState<boolean>(false);

	const [params, setParams] = useState<SamplingHyperparams>({
		temperature: 0.8,
		topK: 40,
		topP: 0.9,
		minP: 0.05,
		repetitionPenalty: 1.1,
		maxNewTokens: 128,
		useCache: true,
		stopWords: "",
	});

	const { isGenerating, generatedText, stats, generate, stop, clear } =
		useGenerateStream();

	useEffect(() => {
		let isMounted = true;

		checkpointApi
			.getCheckpoints()
			.then((data) => {
				if (!isMounted) return;
				const list = data.checkpoints || [];
				setCheckpoints(list);
				if (list.length > 0 && !selectedCheckpoint) {
					setSelectedCheckpoint(list[0].path);
				}
			})
			.catch(() => {});

		checkpointApi
			.getGenerators()
			.then((data) => {
				if (!isMounted) return;
				if (data.generators) setGenerators(data.generators);
				if (data.current_backend)
					setSelectedGenerator(data.current_backend);
			})
			.catch(() => {});

		return () => {
			isMounted = false;
		};
	}, [selectedCheckpoint]);

	const handleSelectGenerator = async (gen: string) => {
		setSelectedGenerator(gen);
		try {
			await checkpointApi.selectGenerator(gen);
		} catch {
			// ignore
		}
	};

	const handleLoadCheckpoint = async () => {
		if (!selectedCheckpoint) return;
		setIsLoadingCp(true);
		try {
			await checkpointApi.loadCheckpoint(
				selectedCheckpoint,
				selectedGenerator,
			);
			onCheckpointLoaded?.(selectedCheckpoint);
		} catch (err: unknown) {
			const error = err as Error;
			alert(`Lỗi nạp checkpoint: ${error.message}`);
		} finally {
			setIsLoadingCp(false);
		}
	};

	const handleStartGenerate = useCallback(
		(overridePrompt?: string) => {
			const targetPrompt = (
				overridePrompt ??
				(prompt.trim() || submittedPrompt)
			).trim();
			if (!targetPrompt) return;

			if (isGenerating) {
				stop();
			}

			setSubmittedPrompt(targetPrompt);
			setPrompt(""); // Xóa input sau khi gửi chuẩn Claude / ChatGPT

			const stops = params.stopWords
				.split(",")
				.map((s) => s.trim())
				.filter((s) => s.length > 0);

			generate(
				{
					prompt: targetPrompt,
					temperature: params.temperature,
					top_k: params.topK,
					top_p: params.topP,
					min_p: params.minP > 0 ? params.minP : null,
					repetition_penalty: params.repetitionPenalty,
					max_new_tokens: params.maxNewTokens,
					greedy: params.temperature <= 0.05,
					use_cache: params.useCache,
					backend: selectedGenerator,
					stop_words: stops.length > 0 ? stops : undefined,
				},
				(err) => alert(err),
			);
		},
		[
			prompt,
			submittedPrompt,
			isGenerating,
			params,
			selectedGenerator,
			generate,
			stop,
		],
	);

	const handleClearSession = useCallback(() => {
		stop();
		setPrompt("");
		setSubmittedPrompt("");
		clear();
	}, [stop, clear]);

	return {
		prompt,
		setPrompt,
		submittedPrompt,
		setSubmittedPrompt,
		checkpoints,
		selectedCheckpoint,
		setSelectedCheckpoint,
		generators,
		selectedGenerator,
		isLoadingCp,
		params,
		setParams,
		isGenerating,
		generatedText,
		stats,
		handleSelectGenerator,
		handleLoadCheckpoint,
		handleStartGenerate,
		handleClearSession,
		stop,
		clear,
	};
}
