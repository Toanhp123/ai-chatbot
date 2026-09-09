export type TrainingStatus =
	| "IDLE"
	| "STARTING"
	| "RUNNING"
	| "STOPPING"
	| "STOPPED"
	| "COMPLETED"
	| "ERROR";

export type TrainingTerminationReason =
	| "COMPLETED"
	| "EARLY_STOPPED"
	| "USER_STOPPED"
	| "ABORTED_STARTUP"
	| "FAILED"
	| null;

export interface VersionedTrainingEvent {
	run_id: number;
	sequence: number;
}

export interface LossStep extends VersionedTrainingEvent {
	type?: "step";
	step: number;
	loss: number;
	lr: number;
	elapsed: number;
}

export interface EvalStep extends VersionedTrainingEvent {
	type?: "eval";
	step: number;
	train_loss: number;
	val_loss: number;
	lr: number;
}

export interface SampleRecord extends VersionedTrainingEvent {
	type: "sample";
	step: number;
	text: string;
	timestamp: string;
}

/**
 * Only fields actually editable in the Training UI live here.
 * Untouched settings remain owned by the YAML EngineConfig and are not sent
 * back as hidden React defaults.
 */
export interface TrainingConfigForm {
	config_path: string;
	model_name: string;
	batch_size: number;
	learning_rate: number;
	max_iters: number;
	precision: string;
	optimizer_type: string;
	gradient_accumulation_steps: number;
	gradient_checkpointing: boolean;
	resume_checkpoint: string;
}

export type TrainingOverrideField = Exclude<
	keyof TrainingConfigForm,
	"config_path" | "resume_checkpoint"
>;


export type TrainingScenarioOverrides = Partial<
	Pick<
		TrainingConfigForm,
		| "batch_size"
		| "precision"
		| "optimizer_type"
		| "gradient_accumulation_steps"
		| "gradient_checkpointing"
	>
>;

export interface TrainingScenarioUpdate {
	revision: number;
	overrides: TrainingScenarioOverrides;
}

export type CanonicalTrainingOverrides = Record<string, string | number | boolean>;

export interface TrainingStartPayload {
	config_path: string;
	overrides?: CanonicalTrainingOverrides;
	resume_checkpoint?: string | null;
}

export interface TrainingFeasibilityPayload {
	config_path: string;
	overrides?: CanonicalTrainingOverrides;
}

export interface PreflightMemoryInfo {
	feasible: boolean;
	advisory: boolean;
	message: string;
	estimated_gb: number;
	estimated_mb: number;
}

export interface ResolvedTrainingConfig {
	system: {
		device: string;
	};
	model: {
		name: string;
		block_size: number;
		n_embd: number;
		n_layer: number;
		n_head: number;
		vocab_size: number;
		model_kwargs?: {
			intermediate_size?: number | null;
			multiple_of?: number;
			[key: string]: unknown;
		};
		tie_word_embeddings?: boolean;
		bias?: boolean;
	};
	training: {
		batch_size: number;
		learning_rate: number;
		max_iters: number;
		precision: string;
		optimizer_type: string;
		gradient_accumulation_steps: number;
		gradient_checkpointing: boolean;
	};
	[key: string]: unknown;
}

export interface TrainingStateResponse extends VersionedTrainingEvent {
	status: TrainingStatus;
	termination_reason: TrainingTerminationReason;
	current_step: number;
	max_iters: number;
	current_loss: number | null;
	current_val_loss: number | null;
	current_lr: number | null;
	last_sample_text: string;
	error_message: string | null;
	sample_history: SampleRecord[];
	history_steps: LossStep[];
	history_evals: EvalStep[];
}

export interface TrainingStatusEvent extends TrainingStateResponse {
	type: "status" | "init";
	message?: string;
}

export type TrainingStreamEvent =
	| TrainingStatusEvent
	| (LossStep & { type: "step" })
	| (EvalStep & { type: "eval" })
	| SampleRecord;
