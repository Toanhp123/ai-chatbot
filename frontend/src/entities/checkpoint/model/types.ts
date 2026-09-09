export interface Checkpoint {
	name?: string;
	filename: string;
	path: string;
	step?: number;
	val_loss?: number;
	size_mb: number;
	modified_time: string;
	is_active?: boolean;
	run_name?: string;
	is_best_val?: boolean;
	is_configured_best?: boolean;
	tag?: "best" | "canonical_last" | "run_last" | "top_k" | "custom";
}

export interface CheckpointsResponse {
	checkpoints: Checkpoint[];
}

export interface GeneratorsResponse {
	generators: string[];
	current_backend: string;
}

export interface LoadCheckpointResponse {
	status: string;
	message: string;
	current_checkpoint: string;
	current_backend: string;
}

export interface SelectGeneratorResponse {
	status: string;
	message: string;
	current_backend: string;
}

export interface InferenceStateResponse {
	current_checkpoint?: string | null;
	current_checkpoint_revision?: string | null;
	current_backend: string;
	checkpoint_dir: string;
	checkpoint_name: string;
	vocab_path: string;
	configured_device: string;
	active_device: string;
	generation: {
		max_new_tokens: number;
		temperature: number;
		top_k: number | null;
		top_p: number | null;
		min_p: number | null;
		repetition_penalty: number;
		do_sample: boolean;
		use_cache: boolean;
	};
}
