export interface TrainingVersion {
	runId: number;
	sequence: number;
}

export function isNewerTrainingVersion(
	incoming: TrainingVersion,
	current: TrainingVersion,
): boolean {
	return (
		incoming.runId > current.runId ||
		(incoming.runId === current.runId && incoming.sequence > current.sequence)
	);
}

export function isLatestRequest(
	requestId: number,
	latestRequestId: number,
): boolean {
	return requestId === latestRequestId;
}
