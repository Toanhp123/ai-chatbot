import { request } from "@/shared/api";
import type {
	ModelInspectData,
	ModelInspectOverrides,
	ModelsResponse,
} from "../model/types";

export const modelApi = {
	getModels: () => request<ModelsResponse>("/api/models"),

	inspectModel: (modelName: string, overrides?: ModelInspectOverrides) => {
		let url = `/api/diagnostics/inspect?model_name=${encodeURIComponent(modelName)}`;
		if (overrides?.n_embd) url += `&n_embd=${overrides.n_embd}`;
		if (overrides?.n_head) url += `&n_head=${overrides.n_head}`;
		if (overrides?.n_layer) url += `&n_layer=${overrides.n_layer}`;
		if (overrides?.block_size) url += `&block_size=${overrides.block_size}`;
		return request<ModelInspectData>(url);
	},
};
