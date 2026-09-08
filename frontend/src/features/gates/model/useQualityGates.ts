import { useState, useCallback } from "react";
import { gatesApi } from "../api/gatesApi";
import type { QualityGatesReport } from "./types";

export function useQualityGates() {
	const [isRunning, setIsRunning] = useState(false);
	const [report, setReport] = useState<QualityGatesReport | null>(null);

	const runGates = useCallback(
		async (onComplete?: (report: QualityGatesReport) => void) => {
			setIsRunning(true);
			try {
				const data = await gatesApi.runQualityGates();
				setReport(data);
				onComplete?.(data);
				return data;
			} finally {
				setIsRunning(false);
			}
		},
		[],
	);

	return {
		isRunning,
		report,
		runGates,
	};
}
