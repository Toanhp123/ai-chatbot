import type { VRAMEstimateRequest } from "@/entities/hardware";
import type { ResolvedTrainingConfig } from "@/entities/training";

export function resolvedConfigToVramParams(
	config: ResolvedTrainingConfig,
): VRAMEstimateRequest {
	return {
		device: config.system.device,
		model_name: config.model.name,
		batch_size: config.training.batch_size,
		block_size: config.model.block_size,
		n_embd: config.model.n_embd,
		n_layer: config.model.n_layer,
		n_head: config.model.n_head,
		vocab_size: config.model.vocab_size,
		intermediate_size: config.model.model_kwargs?.intermediate_size ?? null,
		multiple_of: config.model.model_kwargs?.multiple_of ?? 64,
		tie_word_embeddings: config.model.tie_word_embeddings ?? true,
		bias: config.model.bias ?? false,
		precision: config.training.precision,
		optimizer_type: config.training.optimizer_type,
		gradient_checkpointing: config.training.gradient_checkpointing,
		gradient_accumulation_steps: config.training.gradient_accumulation_steps,
	};
}
