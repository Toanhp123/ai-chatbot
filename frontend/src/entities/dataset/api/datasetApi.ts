import { request } from "@/shared/api";
import type {
	BinaryExportResult,
	CleanTextPayload,
	CleanTextResult,
	CompareTokenizersResult,
	DatasetSampleInfo,
	TokenizeResult,
} from "../model/types";

export const datasetApi = {
	getDatasetSample: () =>
		request<DatasetSampleInfo>("/api/explorer/dataset-sample"),

	exportBinary: () =>
		request<BinaryExportResult>("/api/explorer/export-binary", {
			method: "POST",
		}),

	cleanText: (payload: CleanTextPayload) =>
		request<CleanTextResult>("/api/explorer/clean", {
			method: "POST",
			body: JSON.stringify(payload),
		}),

	tokenize: (text: string, tokenizer_type = "char") =>
		request<TokenizeResult>("/api/explorer/tokenize", {
			method: "POST",
			body: JSON.stringify({ text, tokenizer_type }),
		}),

	compareTokenizers: (text: string) =>
		request<CompareTokenizersResult>("/api/explorer/compare-tokenizers", {
			method: "POST",
			body: JSON.stringify({ text }),
		}),
};
