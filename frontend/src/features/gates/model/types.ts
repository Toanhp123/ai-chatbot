export interface GateResult {
	name: string;
	tool: string;
	passed: boolean;
	elapsed: number;
	details: string;
	error_output?: string;
}

export interface QualityGatesReport {
	all_passed: boolean;
	total_elapsed: number;
	results: GateResult[];
}
