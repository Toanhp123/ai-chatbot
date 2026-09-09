import type { GenerationParams, SamplingHyperparams } from "./types";

export interface CanonicalGenerationConfig {
	max_new_tokens: number;
	temperature: number;
	top_k: number | null;
	top_p: number | null;
	min_p: number | null;
	repetition_penalty: number;
	do_sample: boolean;
	use_cache: boolean;
}

export function generationConfigToSamplingParams(
	config: CanonicalGenerationConfig,
): SamplingHyperparams {
	return {
		temperature: config.temperature,
		topK: config.top_k ?? 0,
		topP: config.top_p ?? 1,
		minP: config.min_p ?? 0,
		repetitionPenalty: config.repetition_penalty,
		maxNewTokens: config.max_new_tokens,
		doSample: config.do_sample,
		useCache: config.use_cache,
		stopWords: "",
	};
}


export function buildGenerationSamplingOverrides(
	params: SamplingHyperparams,
	canonicalHydrated: boolean,
	dirtyFields: ReadonlySet<keyof SamplingHyperparams>,
): Partial<GenerationParams> {
	const result: Partial<GenerationParams> = {};
	const include = (field: keyof SamplingHyperparams) =>
		canonicalHydrated || dirtyFields.has(field);

	if (include("temperature")) result.temperature = params.temperature;
	if (include("topK")) result.top_k = params.topK;
	if (include("topP")) result.top_p = params.topP;
	if (include("minP")) result.min_p = params.minP > 0 ? params.minP : null;
	if (include("repetitionPenalty")) {
		result.repetition_penalty = params.repetitionPenalty;
	}
	if (include("maxNewTokens")) result.max_new_tokens = params.maxNewTokens;
	if (include("doSample")) {
		result.greedy = !params.doSample || params.temperature <= 0;
	}
	if (include("useCache")) result.use_cache = params.useCache;
	return result;
}
