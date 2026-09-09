import { useState, useEffect, useRef, useCallback } from "react";
import { modelApi } from "@/entities/model";
import type { ModelInspectData, LayerParamInfo } from "@/entities/model";

export function useModelInspector(configRevision = 0) {
	const [modelName, setModelNameState] = useState<string>("");
	const [data, setData] = useState<ModelInspectData | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [searchTerm, setSearchTerm] = useState("");
	const requestRef = useRef(0);

	const loadInspection = useCallback(async (overrideModel?: string) => {
		const requestId = ++requestRef.current;
		setLoading(true);
		setError(null);
		try {
			const res = overrideModel
				? await modelApi.inspectModel(overrideModel)
				: await modelApi.inspectModel();
			if (requestId !== requestRef.current) return;
			setData(res);
			setModelNameState(res.model_name);
		} catch (err: unknown) {
			if (requestId !== requestRef.current) return;
			const errObj = err as Error;
			setError(errObj.message || "Không thể kiểm tra kiến trúc mô hình");
		} finally {
			if (requestId === requestRef.current) setLoading(false);
		}
	}, []);

	useEffect(() => {
		// Config saves reset the inspector to the canonical model. Explicit switcher
		// choices remain per-request overrides, not a second source of truth.
		void loadInspection();
	}, [configRevision, loadInspection]);

	const setModelName = useCallback(
		(nextModel: string) => {
			setModelNameState(nextModel);
			void loadInspection(nextModel);
		},
		[loadInspection],
	);

	const fetchInspection = useCallback(() => {
		void loadInspection(modelName || undefined);
	}, [loadInspection, modelName]);

	const filteredLayers = data?.layers?.filter((l: LayerParamInfo) =>
		l.name.toLowerCase().includes(searchTerm.toLowerCase()),
	);

	return {
		modelName,
		setModelName,
		data,
		loading,
		error,
		searchTerm,
		setSearchTerm,
		filteredLayers,
		fetchInspection,
	};
}
