import { request } from "@/shared/api";
import type {
	PreflightMemoryInfo,
	TrainingStateResponse,
} from "../model/types";

export const trainingApi = {
	getTrainingStatus: () =>
		request<TrainingStateResponse>("/api/training/status"),

	startTraining: (payload: any) =>
		request<{
			status: string;
			message: string;
			preflight: any;
			state: any;
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

	checkFeasibility: (payload: any) =>
		request<PreflightMemoryInfo>("/api/training/check-feasibility", {
			method: "POST",
			body: JSON.stringify(payload),
		}),
};
