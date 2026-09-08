/**
 * Base HTTP Client for AI Studio with In-Memory Cache.
 * Cung cấp hàm request chuẩn hóa, xử lý lỗi, kiểu dữ liệu Type-Safe và cache TTL chống giật tải.
 */

export interface ApiErrorPayload {
	detail?: string;
	message?: string;
	status?: number;
	error_type?: string;
	error_code?: string;
	severity?: "INFO" | "WARNING" | "ERROR" | "CRITICAL" | "FATAL" | string;
	is_recoverable?: boolean;
	timestamp?: string;
	details?: Record<string, unknown>;
	suggestion?: string | null;
}

export class ApiError extends Error {
	status: number;
	payload?: ApiErrorPayload;

	constructor(status: number, message: string, payload?: ApiErrorPayload) {
		super(message);
		this.name = "ApiError";
		this.status = status;
		this.payload = payload;
	}
}

export interface RequestOptions extends RequestInit {
	ttlMs?: number;
	skipCache?: boolean;
}

interface CacheEntry {
	data: unknown;
	expiresAt: number;
}

const memoryCache = new Map<string, CacheEntry>();

export function clearApiCache(prefix?: string): void {
	if (!prefix) {
		memoryCache.clear();
		return;
	}
	for (const key of memoryCache.keys()) {
		if (key.startsWith(prefix)) {
			memoryCache.delete(key);
		}
	}
}

export async function request<T>(
	url: string,
	options?: RequestOptions,
): Promise<T> {
	const method = options?.method?.toUpperCase() || "GET";
	const isGet = method === "GET";
	const ttl = options?.ttlMs ?? (isGet ? 15_000 : 0);
	const skipCache = options?.skipCache ?? false;

	// Invalidate cache on mutations
	if (!isGet) {
		clearApiCache();
	}

	// Check cache
	if (isGet && !skipCache && ttl > 0) {
		const cached = memoryCache.get(url);
		if (cached && cached.expiresAt > Date.now()) {
			return cached.data as T;
		}
	}

	const res = await fetch(url, {
		headers: {
			"Content-Type": "application/json",
			...options?.headers,
		},
		...options,
	});

	if (!res.ok) {
		let errMsg = `Lỗi máy chủ (${res.status})`;
		let errPayload: ApiErrorPayload | undefined;
		try {
			errPayload = await res.json();
			if (errPayload) {
				errMsg = errPayload.message || errPayload.detail || errMsg;
			}
		} catch {
			// ignore parse error
		}
		throw new ApiError(res.status, errMsg, errPayload);
	}

	// Handle 204 No Content
	if (res.status === 204) {
		return {} as T;
	}

	const data = (await res.json()) as T;

	// Store cache
	if (isGet && ttl > 0) {
		memoryCache.set(url, {
			data,
			expiresAt: Date.now() + ttl,
		});
	}

	return data;
}
