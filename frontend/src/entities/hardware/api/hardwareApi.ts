import { request } from "@/shared/api";
import type {
	HardwareAdvisorData,
	VRAMEstimateRequest,
	VramEstimateBudget,
	VramScenariosResponse,
} from "../model/types";

export const hardwareApi = {
	getAdvisor: () => request<HardwareAdvisorData>("/api/diagnostics/advisor"),

	getSystemInfo: () => request<any>("/api/diagnostics/system"),

	estimateVram: (payload: VRAMEstimateRequest) =>
		request<VramEstimateBudget>("/api/diagnostics/estimate", {
			method: "POST",
			body: JSON.stringify(payload),
		}),

	getVramScenarios: (payload: VRAMEstimateRequest) =>
		request<VramScenariosResponse>("/api/diagnostics/scenarios", {
			method: "POST",
			body: JSON.stringify(payload),
		}),

	getLogs: (lines = 80) =>
		request<{ logs: string[]; total_lines: number; file: string }>(
			`/api/diagnostics/logs?lines=${lines}`,
		),
};
