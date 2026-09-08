import { useState, useEffect, useRef, useMemo } from "react";
import { checkpointApi } from "@/entities/checkpoint";
import type { Checkpoint } from "@/entities/checkpoint";

export interface UseCheckpointHubProps {
	checkpoints?: Checkpoint[];
	onRefresh?: () => void;
	onLoad?: (path: string) => void;
	onDelete?: (filename: string) => void;
	isLoading?: boolean;
}

export function useCheckpointHub({
	checkpoints: controlledCheckpoints,
	onRefresh: controlledRefresh,
	onLoad: controlledLoad,
	onDelete: controlledDelete,
	isLoading: controlledLoading,
}: UseCheckpointHubProps = {}) {
	const [internalList, setInternalList] = useState<Checkpoint[]>([]);
	const [loading, setLoading] = useState(false);
	const [searchTerm, setSearchTerm] = useState("");
	const isFetchingRef = useRef(false);
	const queuedRef = useRef(false);

	const fetchCheckpoints = async () => {
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
					const data = await checkpointApi.getCheckpoints();
					setInternalList(data.checkpoints || []);
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
	};

	useEffect(() => {
		if (controlledCheckpoints) return;
		let isMounted = true;
		checkpointApi
			.getCheckpoints()
			.then((data) => {
				if (isMounted) {
					setInternalList(data.checkpoints || []);
				}
			})
			.catch(() => {});

		return () => {
			isMounted = false;
		};
	}, [controlledCheckpoints]);

	const rawCheckpoints = controlledCheckpoints || internalList;

	// Sắp xếp: best_model.pt luôn ở vị trí đầu tiên, còn lại sắp xếp theo thời gian mới nhất (giảm dần)
	const checkpoints = useMemo(() => {
		return [...rawCheckpoints].sort((a, b) => {
			// 1. best_model.pt luôn ở trên đỉnh
			const isBestA = a.filename === "best_model.pt";
			const isBestB = b.filename === "best_model.pt";
			if (isBestA && !isBestB) return -1;
			if (!isBestA && isBestB) return 1;

			// 2. Sắp xếp theo modified_time mới nhất trước (giảm dần)
			const timeA = a.modified_time
				? new Date(a.modified_time.replace(/-/g, "/")).getTime()
				: 0;
			const timeB = b.modified_time
				? new Date(b.modified_time.replace(/-/g, "/")).getTime()
				: 0;
			if (timeB !== timeA) {
				return timeB - timeA;
			}

			// 3. Nếu cùng thời gian, xếp theo step giảm dần
			const stepA = a.step ?? 0;
			const stepB = b.step ?? 0;
			return stepB - stepA;
		});
	}, [rawCheckpoints]);

	const filteredCheckpoints = useMemo(() => {
		const term = searchTerm.trim().toLowerCase();
		if (!term) return checkpoints;

		return checkpoints.filter((cp) => {
			const matchFilename = cp.filename.toLowerCase().includes(term);
			const matchStep =
				cp.step !== undefined &&
				String(cp.step).toLowerCase().includes(term);
			const matchLoss =
				cp.val_loss !== undefined &&
				cp.val_loss !== null &&
				String(cp.val_loss).toLowerCase().includes(term);
			const matchTime = cp.modified_time
				? cp.modified_time.toLowerCase().includes(term)
				: false;
			return matchFilename || matchStep || matchLoss || matchTime;
		});
	}, [checkpoints, searchTerm]);

	const isLoading = controlledLoading ?? loading;

	const handleRefresh = () => {
		if (controlledRefresh) {
			controlledRefresh();
		} else {
			fetchCheckpoints();
		}
	};

	const handleLoad = async (path: string) => {
		if (controlledLoad) {
			controlledLoad(path);
		} else {
			try {
				await checkpointApi.loadCheckpoint(path);
				fetchCheckpoints();
			} catch (err: unknown) {
				const error = err as Error;
				alert(`Lỗi nạp checkpoint: ${error.message}`);
			}
		}
	};

	const handleDelete = async (filename: string) => {
		if (controlledDelete) {
			controlledDelete(filename);
		} else {
			if (!confirm(`Bạn có chắc chắn muốn xóa ${filename}?`)) return;
			try {
				await checkpointApi.deleteCheckpoint(filename);
				fetchCheckpoints();
			} catch (err: unknown) {
				const error = err as Error;
				alert(`Lỗi xóa checkpoint: ${error.message}`);
			}
		}
	};

	const getDownloadUrl = (filename: string) => {
		return checkpointApi.getCheckpointDownloadUrl(filename);
	};

	return {
		checkpoints: filteredCheckpoints,
		allCheckpoints: checkpoints,
		totalCount: checkpoints.length,
		filteredCount: filteredCheckpoints.length,
		searchTerm,
		setSearchTerm,
		isLoading,
		handleRefresh,
		handleLoad,
		handleDelete,
		getDownloadUrl,
	};
}
