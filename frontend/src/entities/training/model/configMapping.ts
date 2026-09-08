import type {
	CanonicalTrainingOverrides,
	ResolvedTrainingConfig,
	TrainingConfigForm,
	TrainingOverrideField,
} from "./types";

export const DEFAULT_TRAINING_CONFIG_PATH = "configs/truyen_kieu.yaml";

const OVERRIDE_PATHS: Record<TrainingOverrideField, string> = {
	model_name: "model.name",
	batch_size: "training.batch_size",
	learning_rate: "training.learning_rate",
	max_iters: "training.max_iters",
	precision: "training.precision",
	optimizer_type: "training.optimizer_type",
	gradient_accumulation_steps: "training.gradient_accumulation_steps",
	gradient_checkpointing: "training.gradient_checkpointing",
};

export function resolvedConfigToTrainingForm(
	config: ResolvedTrainingConfig,
	resumeCheckpoint = "",
): TrainingConfigForm {
	return {
		config_path: DEFAULT_TRAINING_CONFIG_PATH,
		model_name: config.model.name,
		batch_size: config.training.batch_size,
		learning_rate: config.training.learning_rate,
		max_iters: config.training.max_iters,
		precision: config.training.precision,
		optimizer_type: config.training.optimizer_type,
		gradient_accumulation_steps:
			config.training.gradient_accumulation_steps,
		gradient_checkpointing: config.training.gradient_checkpointing,
		resume_checkpoint: resumeCheckpoint,
	};
}

export function applyResumeToTrainingForm(
	form: TrainingConfigForm,
	resumeCheckpoint: string,
	resumeStep?: number,
): { form: TrainingConfigForm; overrideFields: TrainingOverrideField[] } {
	const nextForm: TrainingConfigForm = {
		...form,
		resume_checkpoint: resumeCheckpoint,
	};
	const overrideFields: TrainingOverrideField[] = [];

	if (
		resumeCheckpoint &&
		resumeStep !== undefined &&
		resumeStep > 0 &&
		nextForm.max_iters <= resumeStep
	) {
		nextForm.max_iters = resumeStep + 1000;
		overrideFields.push("max_iters");
	}

	return { form: nextForm, overrideFields };
}

export function buildTrainingOverrides(
	config: TrainingConfigForm,
	fields: Iterable<TrainingOverrideField>,
): CanonicalTrainingOverrides {
	const overrides: CanonicalTrainingOverrides = {};
	for (const field of fields) {
		overrides[OVERRIDE_PATHS[field]] = config[field] as
			| string
			| number
			| boolean;
	}
	return overrides;
}
