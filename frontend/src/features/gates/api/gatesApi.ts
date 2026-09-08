import { request } from "@/shared/api";
import type { QualityGatesReport } from "../model/types";

export const gatesApi = {
	runQualityGates: () =>
		request<QualityGatesReport>("/api/diagnostics/gates/run", {
			method: "POST",
		}),
};
