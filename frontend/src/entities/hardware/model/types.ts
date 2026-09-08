export type ProbeStatus = "OK" | "UNSUPPORTED" | "FAILED";

export interface ProbeMetadata {
	status: ProbeStatus;
	value?: unknown;
	error?: string | null;
}

export interface GpuDevice {
	id: number;
	name: string;
	compute_capability: string;
	multi_processor_count?: number | null;
	vram_total_gb: number;
	vram_free_gb: number;
	vram_used_gb: number;
}

export interface AttentionBackends {
	flash_attention: boolean;
	memory_efficient: boolean;
	math_attention: boolean;
	probe?: ProbeMetadata;
}

export interface HardwareRecommendations {
	device: string;
	recommended_precision: string;
	recommended_batch_size: number;
	gradient_checkpointing: boolean;
	attention_backend: string;
	notes: string;
}

export interface GpuInfo {
	probe?: ProbeMetadata;
	cuda_available: boolean;
	device_count: number;
	devices: GpuDevice[];
	primary_gpu: GpuDevice | null;
	bf16_supported: boolean;
	sdpa_backends: AttentionBackends;
	recommendations: HardwareRecommendations;
}

export interface DiskInfo {
	path: string;
	total_gb: number | null;
	used_gb: number | null;
	free_gb: number | null;
	percent_used: number | null;
	probe: ProbeMetadata;
}

export interface DirectoryPermission {
	exists: boolean;
	readable: boolean;
	writable: boolean;
	probe?: ProbeMetadata;
}

export interface HardwareAdvisorData {
	gpu: GpuInfo;
	backends: AttentionBackends;
	disk: DiskInfo;
	permissions: Record<string, DirectoryPermission>;
	recommendations: HardwareRecommendations;
	health_status: "HEALTHY" | "WARNING" | "CRITICAL" | string;
	warnings: string[];
	suggestions: string[];
}

export interface VramComponentsMb {
	parameters: number;
	gradients: number;
	optimizer_states: number;
	activations: number;
	cuda_context_overhead: number;
}

export interface VramScenarioItem {
	id: string;
	name: string;
	description: string;
	precision: string;
	effective_precision: string;
	optimizer: string;
	effective_optimizer: string;
	effective_device: string;
	fallback_reasons: string[];
	gradient_checkpointing: boolean;
	batch_size: number;
	estimated_mb: number;
	estimated_gb: number;
	feasible: boolean;
	utilization_pct: number;
	components: VramComponentsMb;
}

export interface VramScenariosResponse {
	available_vram_gb: number;
	safety_margin_gb: number;
	scenarios: VramScenarioItem[];
	recommended: VramScenarioItem | null;
}

export interface VRAMEstimateRequest {
	model_name?: string;
	batch_size?: number;
	block_size?: number;
	n_embd?: number;
	n_layer?: number;
	n_head?: number;
	vocab_size?: number;
	intermediate_size?: number | null;
	multiple_of?: number;
	tie_word_embeddings?: boolean;
	bias?: boolean;
	precision?: string;
	optimizer_type?: string;
	gradient_checkpointing?: boolean;
	gradient_accumulation_steps?: number;
}

export interface VramEstimateBudget {
	requested_device?: string;
	device?: string;
	requested_precision?: string;
	precision?: string;
	requested_optimizer_type?: string;
	optimizer_type?: string;
	fallback_reasons?: string[];
	micro_batch_size?: number;
	effective_batch_size?: number;
	peak_vram_mb: number;
	peak_vram_gb: number;
	model_weights_mb: number;
	gradients_mb: number;
	optimizer_states_mb: number;
	activations_mb: number;
	cuda_overhead_mb: number;
	feasible?: boolean;
	total_estimated_mb: number;
	total_estimated_gb: number;
	components_mb?: Record<string, number>;
}
