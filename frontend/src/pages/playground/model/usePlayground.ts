import { useState, useEffect, useCallback, useRef } from "react";
import { checkpointApi, loadCheckpointThenCommit } from "@/entities/checkpoint";
import type { Checkpoint } from "@/entities/checkpoint";
import {
	buildGenerationSamplingOverrides,
	generationConfigToSamplingParams,
	useGenerateStream,
} from "@/features/generate";
import type { SamplingHyperparams } from "@/features/generate";

export interface UsePlaygroundProps {
	activeCheckpoint?: string;
	onCheckpointLoaded?: (path: string) => void;
	configRevision?: number;
}

export function usePlayground({
	activeCheckpoint = "",
	onCheckpointLoaded,
	configRevision = 0,
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
	const [samplingHydratedRevision, setSamplingHydratedRevision] = useState(-1);
	const [backendAuthoritative, setBackendAuthoritative] = useState(false);
	const samplingDirtyFieldsRef = useRef<Set<keyof SamplingHyperparams>>(new Set());
	const inferenceStateRequestRef = useRef(0);
	const checkpointListRequestRef = useRef(0);
	const backendMutationVersionRef = useRef(0);

	const [params, setParams] = useState<SamplingHyperparams>({
		temperature: 0.8,
		topK: 40,
		topP: 0.9,
		minP: 0.05,
		repetitionPenalty: 1.1,
		maxNewTokens: 128,
		doSample: true,
		useCache: true,
		stopWords: "",
	});

	const { isGenerating, generatedText, stats, generate, stop, clear } =
		useGenerateStream();

	useEffect(() => {
		if (activeCheckpoint) setSelectedCheckpoint(activeCheckpoint);
	}, [activeCheckpoint]);

	useEffect(() => {
		let isMounted = true;
		const requestId = ++inferenceStateRequestRef.current;
		const backendVersionAtStart = backendMutationVersionRef.current;
		samplingDirtyFieldsRef.current = new Set();
		setSamplingHydratedRevision(-1);
		checkpointApi
			.getInferenceState()
			.then((state) => {
				if (!isMounted || requestId !== inferenceStateRequestRef.current) return;
				const canonicalParams = generationConfigToSamplingParams(state.generation);
				setParams((current) => {
					const merged = { ...canonicalParams };
					for (const field of samplingDirtyFieldsRef.current) {
						(merged as unknown as Record<string, unknown>)[field] = current[field];
					}
					return merged;
				});
				setSamplingHydratedRevision(configRevision);
				if (backendMutationVersionRef.current === backendVersionAtStart) {
					setSelectedGenerator(state.current_backend);
					setBackendAuthoritative(true);
				}
				if (state.current_checkpoint) {
					setSelectedCheckpoint(state.current_checkpoint);
				}
			})
			.catch(() => {});
		return () => {
			isMounted = false;
		};
	}, [configRevision]);

	useEffect(() => {
		let isMounted = true;
		const requestId = ++checkpointListRequestRef.current;
		checkpointApi
			.getCheckpoints()
			.then((data) => {
				if (!isMounted || requestId !== checkpointListRequestRef.current) return;
				const list = data.checkpoints || [];
				setCheckpoints(list);
				setSelectedCheckpoint((current) => {
					if (current && list.some((checkpoint) => checkpoint.path === current)) {
						return current;
					}
					return list[0]?.path ?? "";
				});
			})
			.catch(() => {});

		return () => {
			isMounted = false;
		};
	}, [configRevision]);

	useEffect(() => {
		let isMounted = true;
		const backendVersionAtStart = backendMutationVersionRef.current;
		checkpointApi
			.getGenerators()
			.then((data) => {
				if (!isMounted) return;
				if (data.generators) setGenerators(data.generators);
				if (
					data.current_backend &&
					backendMutationVersionRef.current === backendVersionAtStart
				) {
					setSelectedGenerator(data.current_backend);
					setBackendAuthoritative(true);
				}
			})
			.catch(() => {});

		return () => {
			isMounted = false;
		};
	}, []);

	const handleSelectGenerator = async (gen: string) => {
		if (isGenerating || gen === selectedGenerator) return;
		try {
			await checkpointApi.selectGenerator(gen);
			backendMutationVersionRef.current += 1;
			setSelectedGenerator(gen);
			setBackendAuthoritative(true);
		} catch (err: unknown) {
			const error = err as Error;
			alert(`Không thể đổi generator: ${error.message}`);
		}
	};

	const handleLoadCheckpoint = async () => {
		if (!selectedCheckpoint) return;
		setIsLoadingCp(true);
		try {
			await loadCheckpointThenCommit(
				(path) =>
					checkpointApi.loadCheckpoint(
						path,
						backendAuthoritative ? selectedGenerator : undefined,
					),
				selectedCheckpoint,
				(loadedPath, result) => {
					backendMutationVersionRef.current += 1;
					setSelectedCheckpoint(loadedPath);
					setSelectedGenerator(result.current_backend);
					setBackendAuthoritative(true);
					onCheckpointLoaded?.(loadedPath);
				},
			);
		} catch (err: unknown) {
			const error = err as Error;
			alert(`Lỗi nạp checkpoint: ${error.message}`);
		} finally {
			setIsLoadingCp(false);
		}
	};

	const handleParamsChange = useCallback((next: SamplingHyperparams) => {
		setParams((current) => {
			const dirty = new Set(samplingDirtyFieldsRef.current);
			for (const field of Object.keys(current) as (keyof SamplingHyperparams)[]) {
				if (current[field] !== next[field]) dirty.add(field);
			}
			samplingDirtyFieldsRef.current = dirty;
			return next;
		});
	}, []);

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

			const samplingOverrides = buildGenerationSamplingOverrides(
				params,
				samplingHydratedRevision === configRevision,
				samplingDirtyFieldsRef.current,
			);

			generate(
				{
					prompt: targetPrompt,
					...samplingOverrides,
					backend: backendAuthoritative ? selectedGenerator : undefined,
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
			backendAuthoritative,
			samplingHydratedRevision,
			configRevision,
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
		setParams: handleParamsChange,
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
