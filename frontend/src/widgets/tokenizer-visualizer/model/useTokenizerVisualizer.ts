import { useState, useEffect } from "react";
import { datasetApi } from "@/entities/dataset";
import type {
	TokenizeResult,
	CompareTokenizersResult,
} from "@/entities/dataset";

export function useTokenizerVisualizer(
	initialText = "Trăm năm trong cõi người ta, chữ tài chữ mệnh khéo là ghét nhau.",
) {
	const [text, setText] = useState(initialText);
	const [tokenizerType, setTokenizerType] = useState<
		"char" | "byte" | "gemini"
	>("char");
	const [tokenData, setTokenData] = useState<TokenizeResult | null>(null);
	const [comparisonData, setComparisonData] =
		useState<CompareTokenizersResult | null>(null);
	const [loading, setLoading] = useState(false);
	const [comparing, setComparing] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const handleTokenize = async () => {
		if (!text.trim()) return;
		setLoading(true);
		setError(null);
		try {
			const res = await datasetApi.tokenize(text, tokenizerType);
			setTokenData(res);
		} catch (err: unknown) {
			const errObj = err as Error;
			setError(errObj.message || "Lỗi mã hóa văn bản");
		} finally {
			setLoading(false);
		}
	};

	const handleCompareAll = async () => {
		if (!text.trim()) return;
		setComparing(true);
		setError(null);
		try {
			const res = await datasetApi.compareTokenizers(text);
			setComparisonData(res);
		} catch (err: unknown) {
			const errObj = err as Error;
			setError(errObj.message || "Lỗi khi so sánh 3 bộ mã hóa");
		} finally {
			setComparing(false);
		}
	};

	useEffect(() => {
		if (!text.trim()) {
			return;
		}
		let isMounted = true;
		datasetApi
			.tokenize(text, tokenizerType)
			.then((res) => {
				if (isMounted) {
					setTokenData(res);
					setError(null);
				}
			})
			.catch((err: unknown) => {
				if (isMounted) {
					const errObj = err as Error;
					setError(errObj.message || "Lỗi mã hóa văn bản");
				}
			})
			.finally(() => {
				if (isMounted) setLoading(false);
			});

		return () => {
			isMounted = false;
		};
	}, [text, tokenizerType]);

	return {
		text,
		setText,
		tokenizerType,
		setTokenizerType,
		tokenData,
		comparisonData,
		loading,
		comparing,
		error,
		handleTokenize,
		handleCompareAll,
	};
}
