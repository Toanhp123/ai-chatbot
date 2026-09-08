import { useState, useEffect, useRef, useCallback } from "react";
import {
	isLatestRequest,
	isNewerTrainingVersion,
	trainingApi,
} from "@/entities/training";
import type {
	TrainingStatus,
	TrainingTerminationReason,
	LossStep,
	EvalStep,
	SampleRecord,
	TrainingConfigForm,
	TrainingOverrideField,
	PreflightMemoryInfo,
	TrainingStateResponse,
	TrainingStreamEvent,
} from "@/entities/training";
import { buildTrainingOverrides } from "@/entities/training";

export function useTrainingControls() {
	const [status, setStatus] = useState<TrainingStatus>("IDLE");
	const [terminationReason, setTerminationReason] =
		useState<TrainingTerminationReason>(null);
	const [errorMessage, setErrorMessage] = useState<string | null>(null);
	const [currentStep, setCurrentStep] = useState(0);
	const [maxIters, setMaxIters] = useState(0);
	const [currentLoss, setCurrentLoss] = useState<number | null>(null);
	const [currentValLoss, setCurrentValLoss] = useState<number | null>(null);
	const [currentLr, setCurrentLr] = useState<number | null>(null);
	const [lastSampleText, setLastSampleText] = useState("");
	const [sampleHistory, setSampleHistory] = useState<SampleRecord[]>([]);
	const [historySteps, setHistorySteps] = useState<LossStep[]>([]);
	const [historyEvals, setHistoryEvals] = useState<EvalStep[]>([]);
	const [preflightInfo, setPreflightInfo] =
		useState<PreflightMemoryInfo | null>(null);

	const eventSourceRef = useRef<EventSource | null>(null);
	const versionRef = useRef({ runId: -1, sequence: -1 });
	const preflightRequestRef = useRef(0);

	const applySnapshot = useCallback((data: TrainingStateResponse) => {
		const previous = versionRef.current;
		if (
			!isNewerTrainingVersion(
				{ runId: data.run_id, sequence: data.sequence },
				previous,
			)
		) {
			return false;
		}

		versionRef.current = { runId: data.run_id, sequence: data.sequence };
		setStatus(data.status);
		setTerminationReason(data.termination_reason ?? null);
		setErrorMessage(data.error_message ?? null);
		setCurrentStep(data.current_step ?? 0);
		setMaxIters(data.max_iters ?? 0);
		setCurrentLoss(data.current_loss ?? null);
		setCurrentValLoss(data.current_val_loss ?? null);
		setCurrentLr(data.current_lr ?? null);
		setLastSampleText(data.last_sample_text ?? "");
		setHistorySteps(data.history_steps ?? []);
		setHistoryEvals(data.history_evals ?? []);
		setSampleHistory(data.sample_history ?? []);
		return true;
	}, []);

	const acceptDelta = useCallback((runId: number, sequence: number) => {
		const previous = versionRef.current;
		if (!isNewerTrainingVersion({ runId, sequence }, previous)) {
			return { accepted: false, newRun: false };
		}
		const newRun = runId > previous.runId;
		versionRef.current = { runId, sequence };
		return { accepted: true, newRun };
	}, []);

	const syncStatus = useCallback(async () => {
		try {
			const data = await trainingApi.getTrainingStatus();
			applySnapshot(data);
		} catch (err) {
			console.warn("Lỗi sync training status:", err);
		}
	}, [applySnapshot]);

	useEffect(() => {
		let isMounted = true;
		let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

		void syncStatus();

		const connectSSE = () => {
			if (!isMounted) return;
			try {
				const es = new EventSource("/api/training/stream");
				eventSourceRef.current = es;

				es.onmessage = (event) => {
					if (!isMounted) return;
					try {
						const data = JSON.parse(event.data) as TrainingStreamEvent;
						if (data.type === "init" || data.type === "status") {
							applySnapshot(data);
							return;
						}

						const accepted = acceptDelta(data.run_id, data.sequence);
						if (!accepted.accepted) return;
						if (accepted.newRun) {
							setTerminationReason(null);
							setErrorMessage(null);
							setCurrentStep(0);
							setCurrentLoss(null);
							setCurrentValLoss(null);
							setCurrentLr(null);
							setLastSampleText("");
							setHistorySteps([]);
							setHistoryEvals([]);
							setSampleHistory([]);
						}

						if (data.type === "step") {
							setCurrentStep(data.step);
							setCurrentLoss(data.loss);
							setCurrentLr(data.lr);
							setHistorySteps((prev) => [...prev, data].slice(-3000));
						} else if (data.type === "eval") {
							setCurrentStep(data.step);
							setCurrentValLoss(data.val_loss);
							setCurrentLr(data.lr);
							setHistoryEvals((prev) => [...prev, data].slice(-1000));
						} else if (data.type === "sample") {
							setLastSampleText(data.text);
							setSampleHistory((prev) => [...prev, data].slice(-200));
						}
					} catch {
						// Ignore malformed third-party/proxy events; REST snapshot repairs gaps.
					}
				};

				es.onerror = () => {
					es.close();
					if (isMounted) {
						reconnectTimer = setTimeout(connectSSE, 3000);
					}
				};
			} catch {
				// Polling below remains an authoritative fallback.
			}
		};

		connectSSE();
		const pollInterval = setInterval(syncStatus, 5000);

		return () => {
			isMounted = false;
			if (reconnectTimer) clearTimeout(reconnectTimer);
			if (eventSourceRef.current) {
				eventSourceRef.current.close();
				eventSourceRef.current = null;
			}
			clearInterval(pollInterval);
		};
	}, [acceptDelta, applySnapshot, syncStatus]);

	const checkFeasibility = useCallback(
		async (
			config: TrainingConfigForm,
			overrideFields: Iterable<TrainingOverrideField> = [],
		) => {
			const requestId = ++preflightRequestRef.current;
			try {
				const res = await trainingApi.checkFeasibility({
					config_path: config.config_path,
					overrides: buildTrainingOverrides(config, overrideFields),
				});
				if (!isLatestRequest(requestId, preflightRequestRef.current)) {
					return null;
				}
				setPreflightInfo(res);
				return res;
			} catch (err) {
				if (isLatestRequest(requestId, preflightRequestRef.current)) {
					console.warn("Lỗi kiểm tra tính khả thi:", err);
				}
				return null;
			}
		},
		[],
	);

	const startTraining = useCallback(
		async (
			config: TrainingConfigForm,
			overrideFields: Iterable<TrainingOverrideField>,
			onDone?: (res: unknown) => void,
		) => {
			try {
				// The start response contains preflight for the exact submitted config;
				// invalidate any older standalone estimate still in flight.
				preflightRequestRef.current += 1;
				const res = await trainingApi.startTraining({
					config_path: config.config_path,
					overrides: buildTrainingOverrides(config, overrideFields),
					resume_checkpoint: config.resume_checkpoint || null,
				});
				applySnapshot(res.state);
				setPreflightInfo(res.preflight);
				onDone?.(res);
				return res;
			} catch (err) {
				await syncStatus();
				throw err;
			}
		},
		[applySnapshot, syncStatus],
	);

	const stopTraining = useCallback(async () => {
		try {
			const res = await trainingApi.stopTraining();
			await syncStatus();
			return res;
		} catch (err) {
			await syncStatus();
			throw err;
		}
	}, [syncStatus]);

	const clearTraining = useCallback(async () => {
		await trainingApi.clearTraining();
		await syncStatus();
	}, [syncStatus]);

	return {
		status,
		terminationReason,
		errorMessage,
		currentStep,
		maxIters,
		currentLoss,
		currentValLoss,
		currentLr,
		lastSampleText,
		sampleHistory,
		historySteps,
		historyEvals,
		preflightInfo,
		checkFeasibility,
		startTraining,
		stopTraining,
		clearTraining,
		syncStatus,
	};
}
