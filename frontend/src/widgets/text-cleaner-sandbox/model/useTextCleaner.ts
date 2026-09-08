import { useState } from "react";
import { datasetApi } from "@/entities/dataset";
import type { CleanTextResult } from "@/entities/dataset";

export function useTextCleaner() {
	const [rawText, setRawText] = useState(
		"001: Trăm   năm trong cõi người ta,\n002: Trăm   năm trong cõi người ta,\n003: Chữ tài chữ mệnh khéo là ghét nhauuuu!!!!!\n004: Trải qua một cuộc bể dâu,",
	);

	const [cleanerType, setCleanerType] = useState<
		"default" | "gemini" | "passthrough"
	>("default");
	const [cleanLineNumbers, setCleanLineNumbers] = useState(true);
	const [dedup, setDedup] = useState(true);
	const [dedupMode, setDedupMode] = useState<"consecutive" | "global">(
		"consecutive",
	);
	const [repetition, setRepetition] = useState(true);
	const [minLength, setMinLength] = useState<number | undefined>(undefined);
	const [maxLength, setMaxLength] = useState<number | undefined>(undefined);

	const [result, setResult] = useState<CleanTextResult | null>(null);
	const [loading, setLoading] = useState(false);
	const [copied, setCopied] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const handleClean = async () => {
		if (!rawText.trim()) return;
		setLoading(true);
		setError(null);
		try {
			const res = await datasetApi.cleanText({
				text: rawText,
				cleaner_type: cleanerType,
				clean_line_numbers: cleanLineNumbers,
				dedup,
				dedup_mode: dedupMode,
				repetition,
				min_length: minLength || null,
				max_length: maxLength || null,
			});
			setResult(res);
		} catch (err: unknown) {
			const errObj = err as Error;
			setError(errObj.message || "Lỗi làm sạch văn bản");
		} finally {
			setLoading(false);
		}
	};

	const handleCopy = () => {
		if (result?.cleaned) {
			navigator.clipboard.writeText(result.cleaned);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		}
	};

	return {
		rawText,
		setRawText,
		cleanerType,
		setCleanerType,
		cleanLineNumbers,
		setCleanLineNumbers,
		dedup,
		setDedup,
		dedupMode,
		setDedupMode,
		repetition,
		setRepetition,
		minLength,
		setMinLength,
		maxLength,
		setMaxLength,
		result,
		loading,
		copied,
		error,
		handleClean,
		handleCopy,
	};
}
