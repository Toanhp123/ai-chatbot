import React from "react";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	Badge,
	Button,
	Chip,
	type ChipVariant,
} from "@/shared/ui";
import { useTokenizerVisualizer } from "./model/useTokenizerVisualizer";
import {
	Cpu,
	Hash,
	Scale,
	Sparkles,
	ArrowRightLeft,
	FileText,
	Layers,
} from "lucide-react";

export interface TokenizerVisualizerProps {
	initialText?: string;
}

const SAMPLE_PRESETS = [
	{
		label: "Hội thoại & công nghệ",
		text: "Trí tuệ nhân tạo và học sâu đang định hình lại cách chúng ta làm việc và sáng tạo mỗi ngày.",
	},
	{
		label: "Văn học & thành ngữ",
		text: "Trăm năm trong cõi người ta, chữ tài chữ mệnh khéo là ghét nhau.",
	},
	{
		label: "Mã nguồn & Emoji đa ngữ",
		text: "def predict(prompt: str) -> str: 🚀 return f'Aura Output: {prompt}'",
	},
];

const CHIP_VARIANTS: ChipVariant[] = [
	"indigo",
	"sky",
	"emerald",
	"amber",
	"purple",
	"rose",
];

export const TokenizerVisualizerWidget: React.FC<TokenizerVisualizerProps> = ({
	initialText = "Trí tuệ nhân tạo và học sâu đang định hình lại cách chúng ta làm việc và sáng tạo mỗi ngày.",
}) => {
	const {
		text,
		setText,
		tokenizerType,
		setTokenizerType,
		tokenData,
		comparisonData,
		loading,
		comparing,
		error,
		handleTokenize,
		handleCompareAll,
	} = useTokenizerVisualizer(initialText);

	const samplePresets = SAMPLE_PRESETS;

	return (
		<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
			<CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-stone-200/80">
				<div className="flex items-center gap-3">
					<div className="p-2 rounded-lg bg-amber-50 border border-amber-200/80 text-amber-700">
						<Cpu className="w-5 h-5" />
					</div>
					<div>
						<CardTitle className="text-base text-stone-900 flex items-center gap-2">
							Trực Quan Hóa & Kiểm Thử Bộ Mã Hóa (Tokenizer)
						</CardTitle>
						<p className="text-xs text-stone-500 mt-0.5">
							Phân rã token ID, tỷ lệ nén và đối chiếu trực tiếp
							Char Tokenizer với Byte Tokenizer
						</p>
					</div>
				</div>
				<div className="flex items-center gap-2">
					<Button
						size="sm"
						variant="outline"
						onClick={handleCompareAll}
						disabled={comparing || !text.trim()}
						className="h-8 border-stone-300/80 text-stone-700 hover:bg-[#f4f3ed]"
					>
						<ArrowRightLeft
							className={`w-3.5 h-3.5 mr-1.5 ${comparing ? "animate-spin" : ""}`}
						/>
						{comparing ? "Đang so sánh..." : "So Sánh Tokenizer"}
					</Button>
					<Button
						size="sm"
						variant="primary"
						onClick={handleTokenize}
						disabled={loading || !text.trim()}
						className="h-8 shadow-warm-sm"
					>
						<Sparkles className="w-3.5 h-3.5 mr-1.5" />
						Mã hóa
					</Button>
				</div>
			</CardHeader>

			<CardContent className="pt-5 space-y-5">
				{error && (
					<div className="p-3 bg-rose-50 border border-rose-200/80 rounded-lg text-rose-700 text-xs">
						{error}
					</div>
				)}

				{/* Input & Presets */}
				<div className="space-y-2">
					<div className="flex items-center justify-between">
						<label className="text-xs font-medium text-stone-700">
							Văn bản đầu vào:
						</label>
						<div className="flex items-center gap-1.5">
							<span className="text-[11px] text-stone-400 mr-1">
								Mẫu nhanh:
							</span>
							{samplePresets.map((preset, idx) => (
								<button
									key={idx}
									type="button"
									onClick={() => {
										setText(preset.text);
									}}
									className="px-2 py-0.5 text-[10px] rounded bg-stone-100 text-stone-700 hover:bg-stone-200 transition-colors"
								>
									{preset.label}
								</button>
							))}
						</div>
					</div>
					<textarea
						value={text}
						onChange={(e) => setText(e.target.value)}
						rows={3}
						placeholder="Nhập văn bản hoặc câu từ bất kỳ cần phân tích token hóa..."
						className="w-full px-3 py-2 bg-[#f4f3ed] border border-stone-300/80 rounded-xl text-stone-900 text-sm focus:bg-[#faf8f5] focus:outline-none focus:border-amber-600/70 focus:ring-2 focus:ring-amber-500/10 transition-colors font-serif resize-none"
					/>
				</div>

				{/* Tokenizer Selector Ribbon */}
				<div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-[#f4f3ed] border border-stone-300/80">
					<div className="flex items-center gap-2">
						<span className="text-xs font-semibold text-stone-700">
							Chọn Tokenizer hiển thị:
						</span>
						<div className="flex rounded-lg bg-stone-100 p-0.5 border border-stone-200">
							<button
								type="button"
								onClick={() => setTokenizerType("char")}
								className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
									tokenizerType === "char"
										? "bg-[#faf8f5] text-stone-900 shadow-warm-sm border border-stone-300/80 font-semibold"
										: "text-stone-600 hover:text-stone-900"
								}`}
							>
								Char Tokenizer
							</button>
							<button
								type="button"
								onClick={() => setTokenizerType("byte")}
								className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
									tokenizerType === "byte"
										? "bg-[#faf8f5] text-stone-900 shadow-warm-sm border border-stone-300/80 font-semibold"
										: "text-stone-600 hover:text-stone-900"
								}`}
							>
								Byte Tokenizer (UTF-8)
							</button>
						</div>
					</div>

					{tokenData && (
						<div className="flex items-center gap-4 text-xs">
							<div className="flex items-center gap-1.5 text-stone-600">
								<FileText className="w-3.5 h-3.5 text-stone-400" />
								Ký tự:{" "}
								<span className="font-mono text-stone-900 font-bold">
									{tokenData.char_count}
								</span>
							</div>
							<div className="flex items-center gap-1.5 text-stone-600">
								<Hash className="w-3.5 h-3.5 text-stone-400" />
								Tokens:{" "}
								<span className="font-mono text-amber-700 font-bold">
									{tokenData.token_count}
								</span>
							</div>
							<div className="flex items-center gap-1.5 text-stone-600">
								<Scale className="w-3.5 h-3.5 text-stone-400" />
								Tỷ lệ nén:{" "}
								<span className="font-mono text-emerald-700 font-bold">
									{(
										tokenData.char_count /
										Math.max(tokenData.token_count, 1)
									).toFixed(2)}
									x
								</span>
							</div>
							<div className="flex items-center gap-1.5 text-stone-600">
								<Layers className="w-3.5 h-3.5 text-stone-400" />
								Vocab size:{" "}
								<span className="font-mono text-amber-700 font-bold">
									{tokenData.vocab_size}
								</span>
							</div>
						</div>
					)}
				</div>

				{/* Token Chips Representation */}
				{tokenData?.tokens && (
					<div className="space-y-2">
						<div className="text-xs font-semibold text-stone-700 flex items-center justify-between">
							<span>
								Chuỗi Token Giải Mã ({tokenData.tokens.length}{" "}
								tokens):
							</span>
							<span className="text-[10px] text-stone-500">
								Mỗi chip: [Ký tự / ID]
							</span>
						</div>
						<div className="p-4 rounded-xl bg-[#f4f3ed] border border-stone-300/80 min-h-[100px] flex flex-wrap gap-1.5 max-h-56 overflow-y-auto">
							{tokenData.tokens.map((token, idx) => (
								<Chip
									key={idx}
									variant={
										CHIP_VARIANTS[
											idx % CHIP_VARIANTS.length
										]
									}
									size="sm"
									className="hover:scale-105 transition-transform"
									title={`Index: ${idx} | Token ID: ${token.id}`}
								>
									<span className="font-semibold">
										{token.raw}
									</span>
									<span className="ml-1.5 text-[9px] opacity-70 border-l border-current pl-1 font-mono">
										{token.id}
									</span>
								</Chip>
							))}
						</div>
					</div>
				)}

				{/* Side-by-Side comparison of distinct tokenizer semantics */}
				{comparisonData?.comparisons && (
					<div className="pt-3 border-t border-stone-200/80 space-y-3">
						<div className="text-xs font-semibold text-stone-800 flex items-center gap-2">
							<ArrowRightLeft className="w-4 h-4 text-amber-600" />
							So Sánh Các Bộ Mã Hóa (Side-by-Side):
						</div>
						<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
							{Object.entries(comparisonData.comparisons).map(
								([key, comp]) => (
									<div
										key={key}
										className={`p-3.5 rounded-xl border bg-[#faf8f5] shadow-warm-sm ${
											key === tokenizerType
												? "border-amber-600/70 ring-1 ring-amber-500/30"
												: "border-stone-300/80"
										}`}
									>
										<div className="flex items-center justify-between mb-2">
											<span className="text-xs font-semibold text-stone-900">
												{comp.label}
											</span>
											<Badge
												variant={
													key === "byte"
														? "success"
														: "neutral"
												}
											>
												{key.toUpperCase()}
											</Badge>
										</div>
										<div className="space-y-1.5 text-xs">
											<div className="flex justify-between text-stone-600">
												<span>Kích thước Vocab:</span>
												<span className="font-mono text-stone-900 font-medium">
													{comp.vocab_size?.toLocaleString() ||
														"--"}
												</span>
											</div>
											<div className="flex justify-between text-stone-600">
												<span>Số lượng Tokens:</span>
												<span className="font-mono text-amber-700 font-bold">
													{comp.token_count}
												</span>
											</div>
											<div className="flex justify-between text-stone-600">
												<span>
													Tỷ lệ nén (chars/token):
												</span>
												<span className="font-mono text-emerald-700 font-bold">
													{comp.compression_ratio}x
												</span>
											</div>
											<div className="pt-2 border-t border-stone-200/80 text-[11px] text-stone-500">
												<span className="text-[10px] text-stone-400">
													Mẫu ID:{" "}
												</span>
												<span className="font-mono text-stone-700">
													[
													{comp.sample_token_ids
														?.slice(0, 6)
														.join(", ")}
													...]
												</span>
											</div>
										</div>
									</div>
								),
							)}
						</div>
					</div>
				)}
			</CardContent>
		</Card>
	);
};
