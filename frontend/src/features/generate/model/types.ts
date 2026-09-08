export interface GenerationParams {
	prompt: string;
	temperature: number;
	top_k: number;
	top_p: number;
	min_p?: number | null;
	repetition_penalty: number;
	max_new_tokens: number;
	greedy: boolean;
	use_cache: boolean;
	backend?: string;
	stop_words?: string[];
}

export interface GenerationStats {
	tps: number;
	elapsed_sec: number;
	token_count: number;
}

export interface SamplingHyperparams {
	temperature: number;
	topK: number;
	topP: number;
	minP: number;
	repetitionPenalty: number;
	maxNewTokens: number;
	useCache: boolean;
	stopWords: string;
}
