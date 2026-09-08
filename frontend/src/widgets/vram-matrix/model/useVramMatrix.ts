import { useState, useEffect, useCallback } from "react";
import { hardwareApi } from "@/entities/hardware";
import type {
	VramScenariosResponse,
	VramScenarioItem,
} from "@/entities/hardware";

export interface VramScenarioConfig {
	batch_size?: number;
	gradient_accumulation_steps?: number;
	precision?: string;
	gradient_checkpointing?: boolean;
	optimizer_type?: string;
}

export interface UseVramMatrixProps {
	onApplyScenario?: (scenarioConfig: VramScenarioConfig) => void;
}

export function useVramMatrix({ onApplyScenario }: UseVramMatrixProps = {}) {
	const [data, setData] = useState<VramScenariosResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [selectedScenarioId, setSelectedScenarioId] =
		useState<string>("amp_mixed");
	const [appliedId, setAppliedId] = useState<string | null>(null);

	const [params] = useState({
		batch_size: 64,
		block_size: 128,
		n_embd: 192,
		n_layer: 4,
		n_head: 6,
		vocab_size: 129,
		gradient_accumulation_steps: 1,
	});

	const fetchScenarios = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const res = await hardwareApi.getVramScenarios(params);
			setData(res);
			if (res.recommended && !selectedScenarioId) {
				setSelectedScenarioId(res.recommended.id);
			}
		} catch (err: unknown) {
			const errObj = err as Error;
			setError(errObj.message || "Không thể tính toán ma trận VRAM");
		} finally {
			setLoading(false);
		}
	}, [params, selectedScenarioId]);

	useEffect(() => {
		let isMounted = true;
		hardwareApi
			.getVramScenarios(params)
			.then((res) => {
				if (isMounted) {
					setData(res);
					if (res.recommended) {
						setSelectedScenarioId(
							(prev) =>
								prev || res.recommended?.id || "amp_mixed",
						);
					}
				}
			})
			.catch((err: unknown) => {
				if (isMounted) {
					const errObj = err as Error;
					setError(
						errObj.message || "Không thể tính toán ma trận VRAM",
					);
				}
			})
			.finally(() => {
				if (isMounted) setLoading(false);
			});

		return () => {
			isMounted = false;
		};
	}, [params]);

	const handleApply = (sc: VramScenarioItem) => {
		setAppliedId(sc.id);
		if (onApplyScenario) {
			onApplyScenario({
				batch_size: params.batch_size,
				gradient_accumulation_steps: params.gradient_accumulation_steps,
				precision: sc.precision,
				gradient_checkpointing: sc.gradient_checkpointing,
				optimizer_type: sc.optimizer,
			});
		}
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
