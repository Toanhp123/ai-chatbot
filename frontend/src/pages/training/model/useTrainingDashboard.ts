import { useState, useEffect, useCallback, useRef } from "react";
import {
	applyResumeToTrainingForm,
	isLatestRequest,
	DEFAULT_TRAINING_CONFIG_PATH,
	resolvedConfigToTrainingForm,
	trainingApi,
} from "@/entities/training";
import { useTrainingControls } from "@/features/training";
import type {
	TrainingConfigForm,
	TrainingOverrideField,
} from "@/entities/training";
import type { Checkpoint } from "@/entities/checkpoint";

const FALLBACK_FORM: TrainingConfigForm = {
	config_path: DEFAULT_TRAINING_CONFIG_PATH,
	model_name: "minigpt",
	batch_size: 64,
	learning_rate: 0.0003,
	max_iters: 3000,
	precision: "float32",
	optimizer_type: "adamw",
	gradient_accumulation_steps: 1,
	gradient_checkpointing: false,
	resume_checkpoint: "",
};

export function useTrainingDashboard(configRevision = 0) {
	const {
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
		checkFeasibility: checkFeasibilityRaw,
		startTraining,
		stopTraining,
		clearTraining,
	} = useTrainingControls();

	const [form, setForm] = useState<TrainingConfigForm>(FALLBACK_FORM);
	const [dirtyFields, setDirtyFields] = useState<Set<TrainingOverrideField>>(
		new Set(),
	);
	const [configLoadState, setConfigLoadState] = useState<{
		revision: number;
		error: string | null;
	}>({ revision: -1, error: null });
	const [resumeTarget, setResumeTarget] = useState<Checkpoint | null>(null);
	const resumeTargetRef = useRef<Checkpoint | null>(null);
	const configLoadRequestRef = useRef(0);
	const [isStarting, setIsStarting] = useState(false);
	const [isStopping, setIsStopping] = useState(false);

	const loadCanonicalConfig = useCallback(async () => {
		const requestId = ++configLoadRequestRef.current;
		try {
			const config = await trainingApi.getResolvedConfig(
				DEFAULT_TRAINING_CONFIG_PATH,
			);
			if (!isLatestRequest(requestId, configLoadRequestRef.current)) return;

			const loadedForm = resolvedConfigToTrainingForm(config);
			const selectedResume = resumeTargetRef.current;
			const effective = applyResumeToTrainingForm(
				loadedForm,
				selectedResume?.path ?? "",
				selectedResume?.step,
			);
			setForm(effective.form);
			setDirtyFields(new Set(effective.overrideFields));
			setConfigLoadState({ revision: configRevision, error: null });
			await checkFeasibilityRaw(effective.form, effective.overrideFields);
		} catch (err) {
			if (!isLatestRequest(requestId, configLoadRequestRef.current)) return;
			const message = err instanceof Error ? err.message : String(err);
			setConfigLoadState({ revision: configRevision, error: message });
			console.warn("Không thể nạp canonical training config:", err);
		}
	}, [checkFeasibilityRaw, configRevision]);

	useEffect(() => {
		void loadCanonicalConfig();
	}, [configRevision, loadCanonicalConfig]);

	const isConfigLoading = configLoadState.revision !== configRevision;
	const isConfigReady =
		configLoadState.revision === configRevision && configLoadState.error === null;
	const configLoadError =
		configLoadState.revision === configRevision ? configLoadState.error : null;

	const handleFormChange = useCallback(
		(updated: TrainingConfigForm, changedField?: TrainingOverrideField) => {
			setForm(updated);
			if (changedField) {
				setDirtyFields((prev) => new Set(prev).add(changedField));
			}
		},
		[],
	);

	const checkFeasibility = useCallback(
		async (
			config: TrainingConfigForm,
			changedField?: TrainingOverrideField,
		) => {
			const fields = new Set(dirtyFields);
			if (changedField) fields.add(changedField);
			return checkFeasibilityRaw(config, fields);
		},
		[checkFeasibilityRaw, dirtyFields],
	);

	const handleSelectResume = useCallback((cp: Checkpoint | null) => {
		if (!cp || !cp.path) {
			resumeTargetRef.current = null;
			setResumeTarget(null);
			setForm((prev) => ({ ...prev, resume_checkpoint: "" }));
			return;
		}

		resumeTargetRef.current = cp;
		setResumeTarget(cp);
		const effective = applyResumeToTrainingForm(form, cp.path, cp.step);
		setForm(effective.form);
		if (effective.overrideFields.length > 0) {
			setDirtyFields((fields) => {
				const next = new Set(fields);
				for (const field of effective.overrideFields) next.add(field);
				return next;
			});
		}
	}, [form]);

	const handleCancelResume = useCallback(() => {
		resumeTargetRef.current = null;
		setResumeTarget(null);
		setForm((prev) => ({ ...prev, resume_checkpoint: "" }));
	}, []);

	const handleStart = async () => {
		if (
			!isConfigReady ||
			isConfigLoading ||
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
			await startTraining(form, dirtyFields);
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
			status === "ERROR"
		) {
			return;
		}
		setIsStopping(true);
		try {
			await stopTraining();
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
		try {
			await clearTraining();
			resumeTargetRef.current = null;
			setResumeTarget(null);
			setForm((prev) => ({ ...prev, resume_checkpoint: "" }));
		} catch (err: unknown) {
			const error = err as Error;
			alert(`Lỗi làm mới trạng thái huấn luyện: ${error.message}`);
		}
	};

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
		configLoadError,
		form,
		setForm: handleFormChange,
		checkFeasibility,
		isStarting,
		isStartDisabled: isConfigLoading || !isConfigReady,
		isStopping,
		handleStart,
		handleStop,
		handleClear,
		resumeTarget,
		handleSelectResume,
		handleCancelResume,
	};
}
