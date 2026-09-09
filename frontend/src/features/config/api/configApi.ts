import { request } from "@/shared/api";

export interface RawConfigResponse {
	path: string;
	content: string;
}

export interface SaveConfigResponse {
	status: string;
	message: string;
}

export const configApi = {
	getRawConfig: (path?: string) =>
		request<RawConfigResponse>(
			path ? `/api/configs/raw?path=${encodeURIComponent(path)}` : "/api/configs/raw",
		),

	saveRawConfig: (path: string | undefined, content: string) =>
		request<SaveConfigResponse>("/api/configs/save", {
			method: "POST",
			body: JSON.stringify({ path: path || undefined, content }),
		}),
};
