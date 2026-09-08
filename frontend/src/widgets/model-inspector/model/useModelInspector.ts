import { useState, useEffect, useRef, useCallback } from "react";
import { modelApi } from "@/entities/model";
import type { ModelInspectData, LayerParamInfo } from "@/entities/model";

export function useModelInspector(initialModel = "minigpt") {
	const [modelName, setModelName] = useState<string>(initialModel);
	const [data, setData] = useState<ModelInspectData | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [searchTerm, setSearchTerm] = useState("");
	const isFetchingRef = useRef(false);
	const queuedRef = useRef(false);

	const fetchInspection = useCallback(async () => {
		if (isFetchingRef.current) {
			queuedRef.current = true;
			return;
		}

		isFetchingRef.current = true;
		setLoading(true);

		try {
			do {
				queuedRef.current = false;
				setError(null);
				const startTime = Date.now();
				try {
					const res = await modelApi.inspectModel(modelName);
					setData(res);
				} catch (err: unknown) {
					const errObj = err as Error;
					setError(
						errObj.message ||
							"Không thể kiểm tra kiến trúc mô hình",
					);
				}
				const elapsed = Date.now() - startTime;
				const remaining = Math.max(0, 600 - elapsed);
				if (remaining > 0) {
					await new Promise((r) => setTimeout(r, remaining));
				}
			} while (queuedRef.current);
		} finally {
			isFetchingRef.current = false;
			setLoading(false);
		}
	}, [modelName]);

	useEffect(() => {
		let isMounted = true;
		modelApi
			.inspectModel(modelName)
			.then((res) => {
				if (isMounted) setData(res);
			})
			.catch((err: unknown) => {
				if (isMounted) {
					const errObj = err as Error;
					setError(
						errObj.message ||
							"Không thể kiểm tra kiến trúc mô hình",
					);
				}
			});

		return () => {
			isMounted = false;
		};
	}, [modelName]);

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
