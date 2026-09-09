import { request } from "@/shared/api";
import type {
	CheckpointsResponse,
	GeneratorsResponse,
	LoadCheckpointResponse,
	SelectGeneratorResponse,
	InferenceStateResponse,
} from "../model/types";

export const checkpointApi = {
	getCheckpoints: () => request<CheckpointsResponse>("/api/checkpoints", { skipCache: true }),

	getInferenceState: () =>
		request<InferenceStateResponse>("/api/inference/state", { skipCache: true }),

	loadCheckpoint: (path: string, backend?: string) =>
		request<LoadCheckpointResponse>("/api/checkpoints/load", {
			method: "POST",
			body: JSON.stringify({ path, backend }),
		}),

	deleteCheckpoint: (filename: string) =>
		request<{ status: string; message: string }>(
			`/api/checkpoints/${encodeURIComponent(filename)}`,
			{ method: "DELETE" },
		),

	getCheckpointDownloadUrl: (filename: string) =>
		`/api/checkpoints/${encodeURIComponent(filename)}/download`,

	getGenerators: () => request<GeneratorsResponse>("/api/generators"),

	selectGenerator: (backend: string) =>
		request<SelectGeneratorResponse>("/api/generators/select", {
			method: "POST",
			body: JSON.stringify({ backend }),
		}),
};
