import { useState, useEffect, useRef, useMemo } from "react";
import { checkpointApi, loadCheckpointThenCommit } from "@/entities/checkpoint";
import type { Checkpoint } from "@/entities/checkpoint";

export interface UseCheckpointHubProps {
	checkpoints?: Checkpoint[];
	onRefresh?: () => void;
	onLoad?: (path: string) => void;
	onDelete?: (filename: string) => void;
	isLoading?: boolean;
	configRevision?: number;
}

export function useCheckpointHub({
	checkpoints: controlledCheckpoints,
	onRefresh: controlledRefresh,
	onLoad: controlledLoad,
	onDelete: controlledDelete,
	isLoading: controlledLoading,
	configRevision = 0,
}: UseCheckpointHubProps = {}) {
	const [internalList, setInternalList] = useState<Checkpoint[]>([]);
	const [loading, setLoading] = useState(false);
	const [searchTerm, setSearchTerm] = useState("");
	const isFetchingRef = useRef(false);
	const queuedRef = useRef(false);
	const requestRef = useRef(0);

	const fetchCheckpoints = async () => {
		++requestRef.current;
		if (isFetchingRef.current) {
			queuedRef.current = true;
			return;
		}

		isFetchingRef.current = true;
		setLoading(true);

		try {
			do {
				queuedRef.current = false;
				const requestId = requestRef.current;
				const startTime = Date.now();
				try {
					const data = await checkpointApi.getCheckpoints();
					if (requestId !== requestRef.current) continue;
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
		const requestId = ++requestRef.current;
		checkpointApi
			.getCheckpoints()
			.then((data) => {
				if (isMounted && requestId === requestRef.current) {
					setInternalList(data.checkpoints || []);
				}
			})
			.catch(() => {});

		return () => {
			isMounted = false;
		};
	}, [controlledCheckpoints, configRevision]);

	const rawCheckpoints = controlledCheckpoints || internalList;

	// Sắp xếp: checkpoint được cấu hình làm best luôn ở đầu, còn lại theo thời gian mới nhất (giảm dần)
	const checkpoints = useMemo(() => {
		return [...rawCheckpoints].sort((a, b) => {
			// 1. Checkpoint best theo cấu hình luôn ở trên đỉnh
			const isBestA = Boolean(a.is_configured_best);
			const isBestB = Boolean(b.is_configured_best);
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

	const handleLoad = async (path: string, onLoaded?: (path: string) => void) => {
		try {
			if (controlledLoad) {
				await Promise.resolve(controlledLoad(path));
				onLoaded?.(path);
				return;
			}

			await loadCheckpointThenCommit(
				(checkpointPath) => checkpointApi.loadCheckpoint(checkpointPath),
				path,
				(loadedPath) => onLoaded?.(loadedPath),
			);
			await fetchCheckpoints();
		} catch (err: unknown) {
			const error = err as Error;
			alert(`Lỗi nạp checkpoint: ${error.message}`);
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
