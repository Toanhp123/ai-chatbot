import { request } from "@/shared/api";
import type {
	ModelInspectData,
	ModelInspectOverrides,
	ModelsResponse,
} from "../model/types";

export const modelApi = {
	getModels: () => request<ModelsResponse>("/api/models"),

	inspectModel: (modelName?: string, overrides?: ModelInspectOverrides) => {
		let url = "/api/diagnostics/inspect";
		if (modelName) url += `?model_name=${encodeURIComponent(modelName)}`;
		const append = (key: string, value: number | undefined) => {
			if (value === undefined) return;
			url += `${url.includes("?") ? "&" : "?"}${key}=${value}`;
		};
		append("n_embd", overrides?.n_embd);
		append("n_head", overrides?.n_head);
		append("n_layer", overrides?.n_layer);
		append("block_size", overrides?.block_size);
		return request<ModelInspectData>(url);
	},
};
