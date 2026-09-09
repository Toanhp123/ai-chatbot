import { useState, useEffect, useCallback, useRef } from "react";
import {
	applyResumeToTrainingForm,
	applyTrainingScenarioUpdate,
	isLatestRequest,
	resolvedConfigToTrainingForm,
	shouldApplyTrainingScenario,
	trainingApi,
} from "@/entities/training";
import { useTrainingControls } from "@/features/training";
import type {
	TrainingConfigForm,
	TrainingOverrideField,
	TrainingScenarioUpdate,
} from "@/entities/training";
import type { Checkpoint } from "@/entities/checkpoint";

export function useTrainingDashboard(
	configRevision = 0,
	externalScenario: TrainingScenarioUpdate | null = null,
) {
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

	const [form, setForm] = useState<TrainingConfigForm | null>(null);
	const [dirtyFields, setDirtyFields] = useState<Set<TrainingOverrideField>>(
		new Set(),
	);
	const [configLoadState, setConfigLoadState] = useState<{
		revision: number;
		error: string | null;
	}>({ revision: -1, error: null });
	const [resumeTarget, setResumeTarget] = useState<Checkpoint | null>(null);
	const resumeTargetRef = useRef<Checkpoint | null>(null);
	const formRef = useRef<TrainingConfigForm | null>(form);
	const dirtyFieldsRef = useRef<Set<TrainingOverrideField>>(dirtyFields);
	formRef.current = form;
	dirtyFieldsRef.current = dirtyFields;
	const configLoadRequestRef = useRef(0);
	const externalScenarioRef = useRef<TrainingScenarioUpdate | null>(
		externalScenario,
	);
	externalScenarioRef.current = externalScenario;
	const appliedScenarioRevisionRef = useRef(-1);
	const [isStarting, setIsStarting] = useState(false);
	const [isStopping, setIsStopping] = useState(false);

	const loadCanonicalConfig = useCallback(async () => {
		const requestId = ++configLoadRequestRef.current;
		try {
			const config = await trainingApi.getResolvedConfig();
			if (!isLatestRequest(requestId, configLoadRequestRef.current))
				return;

			const loadedForm = resolvedConfigToTrainingForm(config);
			const scenario = externalScenarioRef.current;
			const scenarioApplied = applyTrainingScenarioUpdate(
				loadedForm,
				scenario,
				appliedScenarioRevisionRef.current,
			);
			const selectedResume = resumeTargetRef.current;
			const effective = applyResumeToTrainingForm(
				scenarioApplied.form,
				selectedResume?.path ?? "",
				selectedResume?.step,
			);
			const effectiveOverrideFields = [
				...scenarioApplied.overrideFields,
				...effective.overrideFields,
			];
			const nextDirtyFields = new Set(effectiveOverrideFields);
			formRef.current = effective.form;
			dirtyFieldsRef.current = nextDirtyFields;
			setForm(effective.form);
			setDirtyFields(nextDirtyFields);
			appliedScenarioRevisionRef.current =
				scenarioApplied.appliedRevision;
			setConfigLoadState({ revision: configRevision, error: null });
			await checkFeasibilityRaw(effective.form, effectiveOverrideFields);
		} catch (err) {
			if (!isLatestRequest(requestId, configLoadRequestRef.current))
				return;
			const message = err instanceof Error ? err.message : String(err);
			setConfigLoadState({ revision: configRevision, error: message });
			console.warn("Không thể nạp canonical training config:", err);
		}
	}, [checkFeasibilityRaw, configRevision]);

	useEffect(() => {
		void loadCanonicalConfig();
	}, [configRevision, loadCanonicalConfig]);

	useEffect(() => {
		if (!externalScenario) return;
		if (
			!shouldApplyTrainingScenario(
				externalScenario,
				appliedScenarioRevisionRef.current,
			)
		)
			return;
		if (
			configLoadState.revision !== configRevision ||
			configLoadState.error !== null
		)
			return;
		const currentForm = formRef.current;
		if (!currentForm) return;
		const applied = applyTrainingScenarioUpdate(
			currentForm,
			externalScenario,
			appliedScenarioRevisionRef.current,
		);
		appliedScenarioRevisionRef.current = applied.appliedRevision;
		if (applied.overrideFields.length === 0) return;

		const nextFields = new Set(dirtyFieldsRef.current);
		for (const field of applied.overrideFields) nextFields.add(field);
		formRef.current = applied.form;
		dirtyFieldsRef.current = nextFields;
		setForm(applied.form);
		setDirtyFields(nextFields);
		void checkFeasibilityRaw(applied.form, nextFields);
	}, [
		externalScenario?.revision,
		checkFeasibilityRaw,
		configLoadState.revision,
		configLoadState.error,
		configRevision,
	]);

	const isConfigLoading = configLoadState.revision !== configRevision;
	const isConfigReady =
		configLoadState.revision === configRevision &&
		configLoadState.error === null;
	const configLoadError =
		configLoadState.revision === configRevision
			? configLoadState.error
			: null;

	const handleFormChange = useCallback(
		(updated: TrainingConfigForm, changedField?: TrainingOverrideField) => {
			formRef.current = updated;
			setForm(updated);
			if (changedField) {
				setDirtyFields((prev) => {
					const next = new Set(prev).add(changedField);
					dirtyFieldsRef.current = next;
					return next;
				});
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

	const handleSelectResume = useCallback(
		(cp: Checkpoint | null) => {
			if (!cp || !cp.path) {
				resumeTargetRef.current = null;
				setResumeTarget(null);
				setForm((prev) =>
				prev ? { ...prev, resume_checkpoint: "" } : prev,
			);
				return;
			}

			resumeTargetRef.current = cp;
			setResumeTarget(cp);
			const currentForm = formRef.current;
			if (!currentForm) return;
			const effective = applyResumeToTrainingForm(currentForm, cp.path, cp.step);
			formRef.current = effective.form;
			setForm(effective.form);
			if (effective.overrideFields.length > 0) {
				setDirtyFields((fields) => {
					const next = new Set(fields);
					for (const field of effective.overrideFields)
						next.add(field);
					return next;
				});
			}
		},
		[],
	);

	const handleCancelResume = useCallback(() => {
		resumeTargetRef.current = null;
		setResumeTarget(null);
		setForm((prev) => {
			const next = prev ? { ...prev, resume_checkpoint: "" } : prev;
			formRef.current = next;
			return next;
		});
	}, []);

	const handleStart = async () => {
		if (
			!isConfigReady ||
			!form ||
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
			setForm((prev) =>
				prev ? { ...prev, resume_checkpoint: "" } : prev,
			);
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
