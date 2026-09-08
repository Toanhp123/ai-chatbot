import { useState, useEffect, useRef, useCallback } from "react";
import { trainingApi } from "@/entities/training";
import type {
	TrainingStatus,
	LossStep,
	EvalStep,
	SampleRecord,
	TrainingConfigForm,
	PreflightMemoryInfo,
} from "@/entities/training";

export function useTrainingControls() {
	const [status, setStatus] = useState<TrainingStatus>("IDLE");
	const [currentStep, setCurrentStep] = useState(0);
	const [maxIters, setMaxIters] = useState(3000);
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

	const resetMetrics = useCallback(() => {
		setCurrentStep(0);
		setCurrentLoss(null);
		setCurrentValLoss(null);
		setCurrentLr(null);
		setLastSampleText("");
		setHistorySteps([]);
		setHistoryEvals([]);
		setSampleHistory([]);
	}, []);

	// Đồng bộ trạng thái từ server (với cơ chế chống giật số liệu khi đang huấn luyện)
	const syncStatus = useCallback(async () => {
		try {
			const data = await trainingApi.getTrainingStatus();
			if (!data) return;
			setStatus(data.status || "IDLE");
			if (data.max_iters) setMaxIters(data.max_iters);

			// Nếu đã dừng hoặc IDLE và số bước bằng 0, xóa sạch số liệu
			if (data.status === "STOPPED" || data.status === "IDLE") {
				if (!data.current_step || data.current_step === 0) {
					resetMetrics();
					return;
				}
			}

			// Chống giật lùi (anti-jitter) khi đang RUNNING:
			// Nếu SSE stream đang phát theo thời gian thực, HTTP polling có thể bị trễ.
			// Không bao giờ ghi đè giật lùi currentStep, currentLoss hay historySteps.
			setCurrentStep((prev) => {
				const polledStep = data.current_step || 0;
				if (data.status === "RUNNING" && prev > polledStep) {
					return prev;
				}
				return polledStep;
			});

			setCurrentLoss((prev) => {
				if (data.status === "RUNNING" && prev !== null) {
					return prev;
				}
				return data.current_loss ?? null;
			});

			setCurrentValLoss(data.current_val_loss ?? null);

			setCurrentLr((prev) => {
				if (data.status === "RUNNING" && prev !== null) {
					return prev;
				}
				return data.current_lr ?? null;
			});

			if (data.last_sample_text) setLastSampleText(data.last_sample_text);
			if (data.sample_history && data.sample_history.length > 0) {
				setSampleHistory((prev) =>
					prev.length > data.sample_history!.length
						? prev
						: data.sample_history!,
				);
			} else if (data.status === "STOPPED" || data.status === "IDLE") {
				setSampleHistory([]);
			}
			if (data.history_steps && data.history_steps.length > 0) {
				setHistorySteps((prev) => {
					if (
						data.status === "RUNNING" &&
						prev.length > data.history_steps!.length
					) {
						return prev;
					}
					return data.history_steps!;
				});
			} else if (data.status === "STOPPED" || data.status === "IDLE") {
				setHistorySteps([]);
			}
			if (data.history_evals && data.history_evals.length > 0) {
				setHistoryEvals((prev) =>
					prev.length > data.history_evals!.length
						? prev
						: data.history_evals!,
				);
			} else if (data.status === "STOPPED" || data.status === "IDLE") {
				setHistoryEvals([]);
			}
		} catch (err) {
			console.warn("Lỗi sync training status:", err);
		}
	}, [resetMetrics]);

	// Kết nối SSE Stream & Polling fallback
	useEffect(() => {
		let isMounted = true;

		const init = async () => {
			if (!isMounted) return;
			await syncStatus();
		};
		init();

		const connectSSE = () => {
			if (!isMounted) return;
			try {
				const es = new EventSource("/api/training/stream");
				eventSourceRef.current = es;

				es.onmessage = (event) => {
					if (!isMounted) return;
					try {
						const data = JSON.parse(event.data);
						if (data.type === "step") {
							setCurrentStep(data.step);
							setCurrentLoss(data.loss);
							setCurrentLr(data.lr);
							setHistorySteps((prev) => {
								const next = [...prev, data];
								return next.length > 500
									? next.slice(-500)
									: next;
							});
						} else if (data.type === "eval") {
							setCurrentStep(data.step);
							setCurrentValLoss(data.val_loss);
							setHistoryEvals((prev) => [...prev, data]);
						} else if (data.type === "sample") {
							setLastSampleText(data.text);
							setSampleHistory((prev) => [...prev, data]);
						} else if (data.type === "status") {
							setStatus(data.status);
							if (data.max_iters) setMaxIters(data.max_iters);
							if (
								data.status === "STOPPED" ||
								data.status === "IDLE"
							) {
								resetMetrics();
							}
						}
					} catch {
						// ignore parse error
					}
				};

				es.onerror = () => {
					es.close();
					if (isMounted) {
						setTimeout(connectSSE, 3000);
					}
				};
			} catch {
				// SSE not supported
			}
		};

		connectSSE();
		const pollInterval = setInterval(syncStatus, 5000);

		return () => {
			isMounted = false;
			if (eventSourceRef.current) {
				eventSourceRef.current.close();
				eventSourceRef.current = null;
			}
			clearInterval(pollInterval);
		};
	}, [syncStatus, resetMetrics]);

	const checkFeasibility = useCallback(async (config: TrainingConfigForm) => {
		try {
			const payload = {
				config_path: config.config_path,
				batch_size: Number(config.batch_size) || 64,
				precision: config.precision,
				optimizer_type: config.optimizer_type,
				gradient_checkpointing: Boolean(config.gradient_checkpointing),
				gradient_accumulation_steps:
					Number(config.gradient_accumulation_steps) || 1,
				model_name: config.model_name || "minigpt",
				n_layer: config.n_layer ? Number(config.n_layer) : null,
				n_embd: config.n_embd ? Number(config.n_embd) : null,
				n_head: config.n_head ? Number(config.n_head) : null,
				block_size: config.block_size
					? Number(config.block_size)
					: null,
			};
			const res = await trainingApi.checkFeasibility(payload);
			setPreflightInfo(res);
			return res;
		} catch (err) {
			console.warn("Lỗi kiểm tra tính khả thi:", err);
			return null;
		}
	}, []);

	const startTraining = useCallback(
		async (config: TrainingConfigForm, onDone?: (res: unknown) => void) => {
			setStatus("STARTING");
			const payload = {
				config_path: config.config_path,
				quick_check: Boolean(config.quick_check),
				model_name: config.model_name || "minigpt",
				batch_size: Number(config.batch_size),
				learning_rate: Number(config.learning_rate),
				max_iters: Number(config.max_iters),
				precision: config.precision,
				optimizer_type: config.optimizer_type,
				gradient_accumulation_steps:
					Number(config.gradient_accumulation_steps) || 1,
				gradient_checkpointing: Boolean(config.gradient_checkpointing),
				eval_interval: Number(config.eval_interval) || 300,
				eval_iters: Number(config.eval_iters) || 50,
				save_last: Boolean(config.save_last),
				split_ratio: Number(config.split_ratio) || 0.9,
				batch_provider_type: config.batch_provider_type || "tensor",
				n_layer: config.n_layer ? Number(config.n_layer) : null,
				n_embd: config.n_embd ? Number(config.n_embd) : null,
				n_head: config.n_head ? Number(config.n_head) : null,
				block_size: config.block_size
					? Number(config.block_size)
					: null,
				dropout:
					config.dropout !== null ? Number(config.dropout) : null,
				seed: config.seed !== null ? Number(config.seed) : null,
				lr_scheduler_type: config.lr_scheduler_type || "cosine",
				warmup_iters: Number(config.warmup_iters) || 100,
				min_lr: Number(config.min_lr) || 0.00003,
				weight_decay: Number(config.weight_decay) || 0.1,
				grad_clip: Number(config.grad_clip) || 1.0,
				early_stopping_patience:
					Number(config.early_stopping_patience) || 10,
				resume_checkpoint: config.resume_checkpoint || null,
				run_name: config.run_name?.trim() || null,
				save_top_k: Number(config.save_top_k) || 3,
				cleaner_type: config.cleaner_type || "default",
				tokenizer_type: config.tokenizer_type || "char",
			};

			try {
				const res = await trainingApi.startTraining(payload);
				if (res?.state?.status) {
					setStatus(res.state.status as TrainingStatus);
				}
				onDone?.(res);
				return res;
			} catch (err) {
				await syncStatus();
				throw err;
			}
		},
		[syncStatus],
	);

	const stopTraining = useCallback(async () => {
		setStatus("STOPPING");
		try {
			const res = await trainingApi.stopTraining();
			resetMetrics();
			return res;
		} catch (err) {
			await syncStatus();
			throw err;
		}
	}, [resetMetrics, syncStatus]);

	const clearTraining = useCallback(async () => {
		resetMetrics();
		setStatus("IDLE");
		try {
			await trainingApi.clearTraining();
		} catch (err) {
			console.warn("Lỗi khi gọi clear training:", err);
		}
	}, [resetMetrics]);

	return {
		status,
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
		resetMetrics,
		syncStatus,
	};
}
