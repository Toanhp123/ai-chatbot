import { useState, useEffect, useCallback, useRef } from "react";
import { hardwareApi } from "@/entities/hardware";
import type {
	VRAMEstimateRequest,
	VramScenariosResponse,
	VramScenarioItem,
} from "@/entities/hardware";
import {
	DEFAULT_TRAINING_CONFIG_PATH,
	trainingApi,
} from "@/entities/training";
import type { TrainingScenarioOverrides } from "@/entities/training";
import { resolvedConfigToVramParams } from "./scenarioMapping";

export type VramScenarioConfig = TrainingScenarioOverrides;

export interface UseVramMatrixProps {
	onApplyScenario?: (scenarioConfig: VramScenarioConfig) => void;
	configRevision?: number;
}

export function useVramMatrix({
	onApplyScenario,
	configRevision = 0,
}: UseVramMatrixProps = {}) {
	const [data, setData] = useState<VramScenariosResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [selectedScenarioId, setSelectedScenarioId] = useState<string>("");
	const [appliedId, setAppliedId] = useState<string | null>(null);
	const [params, setParams] = useState<VRAMEstimateRequest | null>(null);
	const requestRef = useRef(0);

	const fetchScenarios = useCallback(async () => {
		const requestId = ++requestRef.current;
		setLoading(true);
		setError(null);
		try {
			const config = await trainingApi.getResolvedConfig(
				DEFAULT_TRAINING_CONFIG_PATH,
			);
			if (requestId !== requestRef.current) return;
			const canonicalParams = resolvedConfigToVramParams(config);
			const res = await hardwareApi.getVramScenarios(canonicalParams);
			if (requestId !== requestRef.current) return;
			setParams(canonicalParams);
			setData(res);
			setSelectedScenarioId((current) => {
				if (current && res.scenarios.some((item) => item.id === current)) {
					return current;
				}
				return res.recommended?.id ?? res.scenarios[0]?.id ?? "";
			});
		} catch (err: unknown) {
			if (requestId !== requestRef.current) return;
			const errObj = err as Error;
			setError(errObj.message || "Không thể tính toán ma trận VRAM");
		} finally {
			if (requestId === requestRef.current) setLoading(false);
		}
	}, [configRevision]);

	useEffect(() => {
		void fetchScenarios();
	}, [fetchScenarios]);

	const handleApply = (sc: VramScenarioItem) => {
		if (!onApplyScenario) return;
		onApplyScenario({
			batch_size: sc.batch_size,
			gradient_accumulation_steps:
				params?.gradient_accumulation_steps ?? 1,
			precision: sc.precision,
			gradient_checkpointing: sc.gradient_checkpointing,
			optimizer_type: sc.optimizer,
		});
		setAppliedId(sc.id);
	};

	return {
		data,
		loading,
		error,
		selectedScenarioId,
		setSelectedScenarioId,
		appliedId,
		params,
		fetchScenarios,
		handleApply,
	};
}
