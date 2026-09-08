import { useState, useEffect, useCallback, useRef } from "react";
import { hardwareApi } from "@/entities/hardware";
import type { HardwareAdvisorData } from "@/entities/hardware";

export function useHardwareAdvisor() {
	const [data, setData] = useState<HardwareAdvisorData | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const isFetchingRef = useRef(false);
	const queuedRef = useRef(false);

	const fetchAdvisor = useCallback(async () => {
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
					const res = await hardwareApi.getAdvisor();
					setData(res);
				} catch (err: unknown) {
					const errObj = err as Error;
					setError(
						errObj.message ||
							"Không thể tải thông tin cố vấn phần cứng",
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
	}, []);

	useEffect(() => {
		let isMounted = true;
		hardwareApi
			.getAdvisor()
			.then((res) => {
				if (isMounted) setData(res);
			})
			.catch((err: unknown) => {
				if (isMounted) {
					const errObj = err as Error;
					setError(
						errObj.message ||
							"Không thể tải thông tin cố vấn phần cứng",
					);
				}
			})
			.finally(() => {
				if (isMounted) setLoading(false);
			});

		return () => {
			isMounted = false;
		};
	}, []);

	return {
		data,
		loading,
		error,
		fetchAdvisor,
	};
}
