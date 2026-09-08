export interface DatasetSampleInfo {
	input_file: string;
	total_lines: number;
	total_chars: number;
	vocab_size: number;
	sample_lines: string[];
}

export interface BinaryExportResult {
	message: string;
	train_tokens: number;
	train_size_mb: number;
	val_tokens: number;
	val_size_mb: number;
	status: string;
}

export interface CleanTextPayload {
	text: string;
	cleaner_type?: "default" | "gemini" | "passthrough" | string;
	clean_line_numbers?: boolean;
	dedup?: boolean;
	dedup_mode?: "consecutive" | "global" | string;
	repetition?: boolean;
	min_length?: number | null;
	max_length?: number | null;
}

export interface CleanTextResult {
	raw: string;
	cleaned: string;
	raw_length: number;
	cleaned_length: number;
	diff_chars: number;
}

export interface TokenDetail {
	id: number;
	raw: string;
}

export interface TokenizeResult {
	text: string;
	tokenizer_type: string;
	token_count: number;
	char_count: number;
	vocab_size: number;
	tokens: TokenDetail[];
}

export interface TokenizerComparisonItem {
	label: string;
	vocab_size: number;
	token_count: number;
	compression_ratio: number;
	sample_token_ids: number[];
}

export interface CompareTokenizersResult {
	text: string;
	comparisons: Record<string, TokenizerComparisonItem>;
}
