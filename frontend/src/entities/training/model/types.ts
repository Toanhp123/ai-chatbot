export type TrainingStatus =
	| "IDLE"
	| "STARTING"
	| "RUNNING"
	| "STOPPING"
	| "STOPPED"
	| "COMPLETED"
	| "ERROR"
	| "FAILED";

export interface LossStep {
	step: number;
	loss: number;
	lr: number;
	elapsed: number;
}

export interface EvalStep {
	step: number;
	train_loss: number;
	val_loss: number;
	lr: number;
}

export interface SampleRecord {
	type: string;
	step: number;
	text: string;
	timestamp: string;
}

export interface TrainingConfigForm {
	config_path: string;
	quick_check: boolean;
	model_name: string;
	batch_size: number;
	learning_rate: number;
	max_iters: number;
	precision: string;
	optimizer_type: string;
	gradient_accumulation_steps: number;
	gradient_checkpointing: boolean;
	eval_interval: number;
	eval_iters: number;
	save_last: boolean;
	split_ratio: number;
	batch_provider_type: string;
	n_layer: number | null;
	n_embd: number | null;
	n_head: number | null;
	block_size: number | null;
	dropout: number | null;
	seed: number | null;
	lr_scheduler_type: string;
	warmup_iters: number;
	min_lr: number;
	weight_decay: number;
	grad_clip: number;
	early_stopping_patience: number;
	resume_checkpoint: string;
	run_name: string;
	save_top_k: number;
	cleaner_type: string;
	tokenizer_type: string;
}

export interface PreflightMemoryInfo {
	feasible: boolean;
	message: string;
	estimated_gb: number;
	estimated_mb: number;
}

export interface TrainingStateResponse {
	status: TrainingStatus;
	current_step: number;
	max_iters: number;
	current_loss: number | null;
	current_val_loss: number | null;
	current_lr: number | null;
	last_sample_text?: string;
	sample_history?: SampleRecord[];
	history_steps?: LossStep[];
	history_evals?: EvalStep[];
}
