import { useState, useEffect, useRef, useCallback } from "react";
import { hardwareApi } from "@/entities/hardware";

export function useSystemLogs(initialLineCount = 80) {
	const [logs, setLogs] = useState<string[]>([]);
	const [loading, setLoading] = useState(false);
	const [autoRefresh, setAutoRefresh] = useState(true);
	const [autoScroll, setAutoScroll] = useState(true);
	const [lineCount, setLineCount] = useState(initialLineCount);
	const [copied, setCopied] = useState(false);
	const [logFile, setLogFile] = useState("logs/train.log");
	const logContainerRef = useRef<HTMLDivElement>(null);

	const isFetchingRef = useRef(false);
	const queuedRef = useRef(false);

	const fetchLogs = useCallback(async () => {
		if (isFetchingRef.current) {
			queuedRef.current = true;
			return;
		}

		isFetchingRef.current = true;
		setLoading(true);

		try {
			do {
				queuedRef.current = false;
				const startTime = Date.now();
				try {
					const data = await hardwareApi.getLogs(lineCount);
					setLogs(data.logs || []);
					if (data.file) setLogFile(data.file);
				} catch {
					// ignore
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
	}, [lineCount]);

	useEffect(() => {
		let isMounted = true;
		hardwareApi
			.getLogs(lineCount)
			.then((data) => {
				if (!isMounted) return;
				setLogs(data.logs || []);
				if (data.file) setLogFile(data.file);
			})
			.catch(() => {});

		return () => {
			isMounted = false;
		};
	}, [lineCount]);

	useEffect(() => {
		if (!autoRefresh) return;
		const timer = setInterval(() => {
			fetchLogs();
		}, 3000);
		return () => clearInterval(timer);
	}, [autoRefresh, fetchLogs]);

	useEffect(() => {
		if (autoScroll && logContainerRef.current) {
			logContainerRef.current.scrollTop =
				logContainerRef.current.scrollHeight;
		}
	}, [logs, autoScroll]);

	const handleCopy = () => {
		navigator.clipboard.writeText(logs.join("\n"));
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	};

	return {
		logs,
		loading,
		autoRefresh,
		setAutoRefresh,
		autoScroll,
		setAutoScroll,
		lineCount,
		setLineCount,
		copied,
		logFile,
		logContainerRef,
		fetchLogs,
		handleCopy,
	};
}
