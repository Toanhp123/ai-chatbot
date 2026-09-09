export interface LoadedCheckpointResult {
	current_checkpoint: string;
}

/** Commit UI selection only after the backend has authoritatively loaded the artifact. */
export async function loadCheckpointThenCommit<T extends LoadedCheckpointResult>(
	load: (path: string) => Promise<T>,
	path: string,
	onLoaded: (path: string, result: T) => void,
): Promise<T> {
	const result = await load(path);
	onLoaded(result.current_checkpoint, result);
	return result;
}
