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
