import React from "react";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	Badge,
	Button,
	Select,
} from "@/shared/ui";
import { useTextCleaner } from "./model/useTextCleaner";
import {
	Wand2,
	Copy,
	Check,
	ArrowRight,
	Sparkles,
	SlidersHorizontal,
} from "lucide-react";

export interface TextCleanerWidgetProps {
	onSendToTokenizer?: (cleanedText: string) => void;
}

export const TextCleanerWidget: React.FC<TextCleanerWidgetProps> = ({
	onSendToTokenizer,
}) => {
	const {
		rawText,
		setRawText,
		cleanerType,
		setCleanerType,
		cleanLineNumbers,
		setCleanLineNumbers,
		dedup,
		setDedup,
		dedupMode,
		setDedupMode,
		repetition,
		setRepetition,
		minLength,
		setMinLength,
		maxLength,
		setMaxLength,
		result,
		loading,
		copied,
		error,
		handleClean,
		handleCopy,
	} = useTextCleaner();

	return (
		<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
			<CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-stone-200/80">
				<div className="flex items-center gap-3">
					<div className="p-2 rounded-lg bg-amber-50 border border-amber-200/80 text-amber-700">
						<Wand2 className="w-5 h-5" />
					</div>
					<div>
						<CardTitle className="text-base text-stone-900 flex items-center gap-2">
							Hộp Cát Làm Sạch Văn Bản (Text Cleaner Sandbox)
						</CardTitle>
						<p className="text-xs text-stone-500 mt-0.5">
							Chuẩn hóa Unicode NFC, khử trùng lặp dòng, cắt gọt
							số thứ tự và lọc lặp ký tự
						</p>
					</div>
				</div>
				<Button
					size="sm"
					variant="primary"
					onClick={handleClean}
					disabled={loading || !rawText.trim()}
					className="h-8 shadow-warm-sm"
				>
					<Sparkles
						className={`w-3.5 h-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}
					/>
					Làm sạch ngay
				</Button>
			</CardHeader>

			<CardContent className="pt-5 space-y-5">
				{error && (
					<div className="p-3 bg-rose-50 border border-rose-200/80 rounded-lg text-rose-700 text-xs">
						{error}
					</div>
				)}

				{/* Filter Configuration Ribbon */}
				<div className="p-3.5 rounded-xl bg-[#f4f3ed] border border-stone-300/80 space-y-3">
					<div className="flex items-center gap-2 text-xs font-semibold text-stone-800">
						<SlidersHorizontal className="w-3.5 h-3.5 text-amber-600" />
						Cấu hình bộ lọc đường ống tiền xử lý (Preprocessing
						Pipeline):
					</div>

					<div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3 text-xs">
						{/* Cleaner type */}
						<div>
							<Select
								label="Loại Cleaner:"
								value={cleanerType}
								onValueChange={(val) =>
									setCleanerType(
										val as
											| "default"
											| "gemini"
											| "passthrough",
									)
								}
								options={[
									{
										value: "default",
										label: "Default (Unicode NFC)",
									},
									{
										value: "gemini",
										label: "Gemini LLM Optimized",
									},
									{
										value: "passthrough",
										label: "Passthrough (Không đổi)",
									},
								]}
							/>
						</div>

						{/* Line numbers toggle */}
						<div className="flex items-center pt-5">
							<label className="flex items-center gap-2 cursor-pointer text-stone-700">
								<input
									type="checkbox"
									checked={cleanLineNumbers}
									onChange={(e) =>
										setCleanLineNumbers(e.target.checked)
									}
									className="rounded border-stone-300/80 bg-[#faf8f5] text-amber-700 focus:ring-amber-500 w-4 h-4 accent-amber-700"
								/>
								<span>Xóa số dòng (001:...)</span>
							</label>
						</div>

						{/* Repetition filter */}
						<div className="flex items-center pt-5">
							<label className="flex items-center gap-2 cursor-pointer text-stone-700">
								<input
									type="checkbox"
									checked={repetition}
									onChange={(e) =>
										setRepetition(e.target.checked)
									}
									className="rounded border-stone-300/80 bg-[#faf8f5] text-amber-700 focus:ring-amber-500 w-4 h-4 accent-amber-700"
								/>
								<span>Khử lặp ký tự thừa</span>
							</label>
						</div>

						{/* Dedup toggle & mode */}
						<div>
							<label className="flex items-center gap-2 cursor-pointer text-stone-700 mb-1">
								<input
									type="checkbox"
									checked={dedup}
									onChange={(e) => setDedup(e.target.checked)}
									className="rounded border-stone-300/80 bg-[#faf8f5] text-amber-700 focus:ring-amber-500 w-4 h-4 accent-amber-700"
								/>
								<span>Khử trùng lặp dòng:</span>
							</label>
							{dedup && (
								<Select
									value={dedupMode}
									onValueChange={(val) =>
										setDedupMode(
											val as "consecutive" | "global",
										)
									}
									triggerClassName="h-7 py-0.5 px-2 text-[11px]"
									options={[
										{
											value: "consecutive",
											label: "Consecutive (Liền kề)",
										},
										{
											value: "global",
											label: "Global (Toàn văn)",
										},
									]}
								/>
							)}
						</div>

						{/* Line length filter */}
						<div className="flex items-center gap-2">
							<div className="w-1/2">
								<label className="block text-[10px] text-stone-600 mb-0.5">
									Min Len:
								</label>
								<input
									type="number"
									value={minLength ?? ""}
									onChange={(e) =>
										setMinLength(
											e.target.value
												? parseInt(e.target.value, 10)
												: undefined,
										)
									}
									placeholder="1"
									className="w-full px-2 py-1 bg-[#faf8f5] border border-stone-300/80 rounded text-stone-900 text-[11px] font-mono outline-none focus:outline-none focus:border-amber-600"
								/>
							</div>
							<div className="w-1/2">
								<label className="block text-[10px] text-stone-600 mb-0.5">
									Max Len:
								</label>
								<input
									type="number"
									value={maxLength ?? ""}
									onChange={(e) =>
										setMaxLength(
											e.target.value
												? parseInt(e.target.value, 10)
												: undefined,
										)
									}
									placeholder="4096"
									className="w-full px-2 py-1 bg-[#faf8f5] border border-stone-300/80 rounded text-stone-900 text-[11px] font-mono outline-none focus:outline-none focus:border-amber-600"
								/>
							</div>
						</div>
					</div>
				</div>

				{/* 2-Column Split: Raw Input vs Cleaned Output */}
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					{/* Raw Text Input */}
					<div className="space-y-2">
						<div className="flex items-center justify-between text-xs">
							<span className="font-semibold text-stone-900">
								Văn bản thô (Raw Input):
							</span>
							<span className="text-stone-500 font-mono text-[11px]">
								{rawText.length} ký tự |{" "}
								{rawText.split("\n").length} dòng
							</span>
						</div>
						<textarea
							value={rawText}
							onChange={(e) => setRawText(e.target.value)}
							rows={8}
							placeholder="Nhập văn bản thô cần tiền xử lý..."
							className="w-full px-3 py-2.5 bg-[#f4f3ed] border border-stone-300/80 rounded-xl text-stone-900 font-mono text-xs focus:bg-[#faf8f5] focus:outline-none focus:border-amber-600/70 focus:ring-2 focus:ring-amber-500/10 resize-none leading-relaxed selection:bg-amber-500/20"
						/>
					</div>

					{/* Cleaned Output */}
					<div className="space-y-2">
						<div className="flex items-center justify-between text-xs">
							<span className="font-semibold text-stone-900 flex items-center gap-1.5">
								<span>Văn bản sau làm sạch:</span>
								{result && (
									<Badge
										variant="success"
										className="text-[10px]"
									>
										Giảm {result.diff_chars} ký tự (
										{(
											(result.diff_chars /
												(result.raw_length || 1)) *
											100
										).toFixed(1)}
										%)
									</Badge>
								)}
							</span>
							{result?.cleaned && (
								<div className="flex items-center gap-2">
									<button
										type="button"
										onClick={handleCopy}
										className="flex items-center gap-1 text-[11px] text-stone-500 hover:text-stone-800 transition-colors"
									>
										{copied ? (
											<Check className="w-3.5 h-3.5 text-emerald-600" />
										) : (
											<Copy className="w-3.5 h-3.5" />
										)}
										{copied ? "Đã sao chép" : "Sao chép"}
									</button>
									{onSendToTokenizer && (
										<button
											type="button"
											onClick={() =>
												onSendToTokenizer(
													result.cleaned,
												)
											}
											className="flex items-center gap-1 text-[11px] text-amber-700 hover:text-amber-800 font-semibold ml-2 transition-colors"
										>
											<span>Sang Tokenizer</span>
											<ArrowRight className="w-3 h-3" />
										</button>
									)}
								</div>
							)}
						</div>
						<textarea
							readOnly
							value={result?.cleaned || ""}
							rows={8}
							placeholder="Kết quả sau tiền xử lý sẽ hiển thị tại đây sau khi bạn nhấn 'Làm sạch ngay'..."
							className="w-full px-3 py-2.5 bg-[#f4f3ed] border border-stone-300/80 rounded-xl text-stone-900 font-mono text-xs focus:bg-[#faf8f5] focus:outline-none resize-none leading-relaxed selection:bg-amber-500/20"
						/>
					</div>
				</div>
			</CardContent>
		</Card>
	);
};
