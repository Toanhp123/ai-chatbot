import { useState, useEffect, useCallback } from "react";
import { useTrainingControls } from "@/features/training";
import type { TrainingConfigForm } from "@/entities/training";
import type { Checkpoint } from "@/entities/checkpoint";

export function useTrainingDashboard() {
	const {
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
	} = useTrainingControls();

	const [form, setForm] = useState<TrainingConfigForm>({
		config_path: "configs/truyen_kieu.yaml",
		quick_check: false,
		model_name: "minigpt",
		batch_size: 64,
		learning_rate: 0.0003,
		max_iters: 3000,
		precision: "float32",
		optimizer_type: "adamw",
		gradient_accumulation_steps: 1,
		gradient_checkpointing: false,
		eval_interval: 300,
		eval_iters: 50,
		save_last: true,
		split_ratio: 0.9,
		batch_provider_type: "tensor",
		n_layer: 4,
		n_embd: 192,
		n_head: 6,
		block_size: 128,
		dropout: 0.1,
		seed: 1337,
		lr_scheduler_type: "cosine",
		warmup_iters: 100,
		min_lr: 0.00003,
		weight_decay: 0.1,
		grad_clip: 1.0,
		early_stopping_patience: 10,
		resume_checkpoint: "",
		run_name: "",
		save_top_k: 3,
		cleaner_type: "default",
		tokenizer_type: "char",
	});

	const [resumeTarget, setResumeTarget] = useState<Checkpoint | null>(null);
	const [isStarting, setIsStarting] = useState(false);
	const [isStopping, setIsStopping] = useState(false);

	const handleSelectResume = useCallback((cp: Checkpoint | null) => {
		if (!cp || !cp.path) {
			setResumeTarget(null);
			setForm((prev) => ({ ...prev, resume_checkpoint: "" }));
			return;
		}

		setResumeTarget(cp);
		setForm((prev) => {
			const next = { ...prev, resume_checkpoint: cp.path };
			// Tự động kiểm tra và điều chỉnh max_iters nếu bước của checkpoint >= max_iters hiện tại
			if (cp.step && Number(prev.max_iters) <= cp.step) {
				next.max_iters = cp.step + 1000;
			}
			return next;
		});
	}, []);

	const handleCancelResume = useCallback(() => {
		setResumeTarget(null);
		setForm((prev) => ({ ...prev, resume_checkpoint: "" }));
	}, []);

	const runInitialCheck = useCallback(async () => {
		await checkFeasibility(form);
	}, [checkFeasibility, form]);

	useEffect(() => {
		runInitialCheck();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	const handleStart = async () => {
		if (
			isStarting ||
			isStopping ||
			status === "STARTING" ||
			status === "RUNNING" ||
			status === "STOPPING"
		) {
			return;
		}
		setIsStarting(true);
		try {
			await startTraining(form);
		} catch (err: unknown) {
			const error = err as Error;
			alert(`Lỗi khởi động huấn luyện: ${error.message}`);
		} finally {
			setIsStarting(false);
		}
	};

	const handleStop = async () => {
		if (
			isStopping ||
			status === "STOPPING" ||
			status === "IDLE" ||
			status === "STOPPED" ||
			status === "COMPLETED" ||
			status === "FAILED" ||
			status === "ERROR"
		) {
			return;
		}
		setIsStopping(true);
		try {
			await stopTraining();
			resetMetrics();
		} catch (err: unknown) {
			const error = err as Error;
			alert(`Lỗi dừng huấn luyện: ${error.message}`);
		} finally {
			setIsStopping(false);
		}
	};

	const handleClear = async () => {
		if (
			isStarting ||
			isStopping ||
			status === "STARTING" ||
			status === "RUNNING" ||
			status === "STOPPING"
		) {
			return;
		}
		await clearTraining();
		setResumeTarget(null);
		setForm((prev) => ({ ...prev, resume_checkpoint: "" }));
	};

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
		form,
		setForm,
		checkFeasibility,
		isStarting,
		isStopping,
		handleStart,
		handleStop,
		handleClear,
		resumeTarget,
		handleSelectResume,
		handleCancelResume,
	};
}
