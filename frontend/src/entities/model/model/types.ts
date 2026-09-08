export interface LayerParamInfo {
	name: string;
	shape: number[];
	params: number;
	trainable: boolean;
	memory_kb: number;
}

export interface ModelInspectData {
	model_name: string;
	total_parameters: number;
	total_parameters_formatted: string;
	vocab_size: number;
	block_size: number;
	n_embd: number;
	n_head: number;
	n_layer: number;
	layers: LayerParamInfo[];
}

export interface ModelInspectOverrides {
	n_embd?: number;
	n_head?: number;
	n_layer?: number;
	block_size?: number;
}

export interface ModelsResponse {
	models: string[];
}
