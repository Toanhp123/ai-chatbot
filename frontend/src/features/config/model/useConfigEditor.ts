import { useState, useCallback } from "react";
import { configApi } from "../api/configApi";

export function useConfigEditor() {
	const [isOpen, setIsOpen] = useState(false);
	const [path, setPath] = useState("configs/truyen_kieu.yaml");
	const [content, setContent] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [isSaving, setIsSaving] = useState(false);

	const openConfig = useCallback(async (configPath: string) => {
		setPath(configPath);
		setIsOpen(true);
		setIsLoading(true);
		const startTime = Date.now();
		try {
			const data = await configApi.getRawConfig(configPath);
			setContent(data.content);
		} catch (err: unknown) {
			const error = err as Error;
			setContent(`# Không thể tải cấu hình: ${error.message}`);
		} finally {
			const elapsed = Date.now() - startTime;
			const remaining = Math.max(0, 600 - elapsed);
			if (remaining > 0) {
				await new Promise((r) => setTimeout(r, remaining));
			}
			setIsLoading(false);
		}
	}, []);

	const saveConfig = useCallback(
		async (onSuccess?: () => void, onError?: (err: string) => void) => {
			setIsSaving(true);
			try {
				await configApi.saveRawConfig(path, content);
				setIsOpen(false);
				onSuccess?.();
			} catch (err: unknown) {
				const error = err as Error;
				onError?.(error.message || "Lỗi khi lưu file YAML");
			} finally {
				setIsSaving(false);
			}
		},
		[path, content],
	);

	return {
		isOpen,
		setIsOpen,
		path,
		content,
		setContent,
		isLoading,
		isSaving,
		openConfig,
		saveConfig,
	};
}
