import { useState, useEffect } from "react";
import { datasetApi } from "@/entities/dataset";
import type { DatasetSampleInfo, BinaryExportResult } from "@/entities/dataset";

export function useExplorer(configRevision = 0) {
	const [datasetInfo, setDatasetInfo] = useState<DatasetSampleInfo | null>(
		null,
	);
	const [exportingBinary, setExportingBinary] = useState(false);
	const [exportResult, setExportResult] = useState<BinaryExportResult | null>(
		null,
	);
	const [tokenizerInputText, setTokenizerInputText] = useState(
		"Trăm năm trong cõi người ta, chữ tài chữ mệnh khéo là ghét nhau.",
	);

	useEffect(() => {
		let isMounted = true;
		datasetApi
			.getDatasetSample()
			.then((res) => {
				if (isMounted) setDatasetInfo(res);
			})
			.catch(() => {});

		return () => {
			isMounted = false;
		};
	}, [configRevision]);

	const handleExportBinary = async () => {
		setExportingBinary(true);
		try {
			const res = await datasetApi.exportBinary();
			setExportResult(res);
		} catch (err: unknown) {
			const error = err as Error;
			alert(`Lỗi đóng gói nhị phân: ${error.message}`);
		} finally {
			setExportingBinary(false);
		}
	};

	return {
		datasetInfo,
		exportingBinary,
		exportResult,
		tokenizerInputText,
		setTokenizerInputText,
		handleExportBinary,
	};
}
