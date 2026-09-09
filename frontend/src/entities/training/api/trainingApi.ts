import { request } from "@/shared/api";
import type {
	PreflightMemoryInfo,
	ResolvedTrainingConfig,
	TrainingFeasibilityPayload,
	TrainingStartPayload,
	TrainingStateResponse,
} from "../model/types";

export const trainingApi = {
	getTrainingStatus: () =>
		request<TrainingStateResponse>("/api/training/status", {
			skipCache: true,
		}),

	getResolvedConfig: (path?: string) =>
		request<ResolvedTrainingConfig>(
			path ? `/api/training/config?path=${encodeURIComponent(path)}` : "/api/training/config",
			{ skipCache: true },
		),

	startTraining: (payload: TrainingStartPayload) =>
		request<{
			status: string;
			message: string;
			preflight: PreflightMemoryInfo;
			state: TrainingStateResponse;
		}>("/api/training/start", {
			method: "POST",
			body: JSON.stringify(payload),
		}),

	stopTraining: () =>
		request<{ status: string; message: string }>("/api/training/stop", {
			method: "POST",
		}),

	clearTraining: () =>
		request<{ status: string; message: string }>("/api/training/clear", {
			method: "POST",
		}),

	checkFeasibility: (payload: TrainingFeasibilityPayload) =>
		request<PreflightMemoryInfo>("/api/training/check-feasibility", {
			method: "POST",
			body: JSON.stringify(payload),
		}),
};
