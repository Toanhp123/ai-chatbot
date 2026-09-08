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
	getRawConfig: (path: string) =>
		request<RawConfigResponse>(
			`/api/configs/raw?path=${encodeURIComponent(path)}`,
		),

	saveRawConfig: (path: string, content: string) =>
		request<SaveConfigResponse>("/api/configs/save", {
			method: "POST",
			body: JSON.stringify({ path, content }),
		}),
};
