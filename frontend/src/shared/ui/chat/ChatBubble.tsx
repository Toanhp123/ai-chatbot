import React, { useState } from "react";
import { Copy, Check, RotateCcw, Sparkles } from "lucide-react";
import { cn } from "@/shared/lib";

export interface ChatMessageProps {
	role: "user" | "assistant";
	content: string;
	timestamp?: string;
	isStreaming?: boolean;
	stats?: {
		tps?: number;
		elapsed_sec?: number;
		tokens?: number;
	} | null;
	onRegenerate?: () => void;
	className?: string;
}

export const ChatBubble: React.FC<ChatMessageProps> = ({
	role,
	content,
	timestamp,
	isStreaming = false,
	stats,
	onRegenerate,
	className,
}) => {
	const [copied, setCopied] = useState(false);

	const handleCopy = () => {
		navigator.clipboard.writeText(content);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	};

	const isUser = role === "user";

	// Claude-style User Message: Soft organic pill container aligned to the right
	if (isUser) {
		return (
			<div
				className={cn(
					"w-full max-w-3xl mx-auto flex justify-end px-2 sm:px-4 py-2 group",
					className,
				)}
			>
				<div className="relative max-w-[85%] sm:max-w-[75%] rounded-2xl sm:rounded-3xl bg-[#e3e0d5] hover:bg-[#dedad0] text-stone-900 px-4 py-3 shadow-warm-sm transition-all border border-[#d5d1c5]/80">
					<div className="text-sm leading-relaxed whitespace-pre-wrap break-words font-normal">
						{content}
					</div>

					{/* Subtle hover copy button on the side */}
					<button
						type="button"
						onClick={handleCopy}
						className="absolute -left-9 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-200/60 transition-all"
						title="Sao chép tin nhắn"
					>
						{copied ? (
							<Check className="w-3.5 h-3.5 text-emerald-600" />
						) : (
							<Copy className="w-3.5 h-3.5" />
						)}
					</button>
				</div>
			</div>
		);
	}

	// Claude-style Assistant Response: Floats directly on canvas with editorial typography
	return (
		<div
			className={cn(
				"w-full max-w-3xl mx-auto py-4 px-2 sm:px-4 space-y-2 group transition-colors",
				className,
			)}
		>
			{/* Assistant Identity Header */}
			<div className="flex items-center justify-between text-xs text-stone-500 mb-1.5">
				<div className="flex items-center gap-2">
					<div className="w-6 h-6 rounded-lg bg-amber-600/10 text-amber-700 flex items-center justify-center border border-amber-600/20 shadow-warm-sm">
						<Sparkles className="w-3.5 h-3.5 fill-amber-600/20" />
					</div>
					<span className="font-semibold text-stone-900 text-xs">
						Aura AI
					</span>
					<span className="text-[10px] text-amber-800/80 font-mono bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200/60">
						124M • SDPA
					</span>
				</div>
				{timestamp && (
					<span className="text-[11px] text-stone-400 font-normal">
						{timestamp}
					</span>
				)}
			</div>

			{/* Assistant Message Body */}
			<div className="pl-8 text-[15.5px] sm:text-[16px] leading-[1.85] text-stone-900 font-serif font-normal tracking-wide whitespace-pre-wrap break-words select-text">
				{content}
				{isStreaming && (
					<span className="inline-block w-2 h-4 ml-1.5 bg-amber-600 animate-pulse align-baseline rounded-[1px]" />
				)}
			</div>

			{/* Claude-style Micro-Action Toolbar (Copy, Regenerate, TPS metrics) */}
			{!isStreaming && content && (
				<div className="pl-8 pt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-stone-500">
					<div className="flex items-center gap-1">
						<button
							type="button"
							onClick={handleCopy}
							className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg hover:bg-stone-200/60 text-stone-600 hover:text-stone-900 transition-colors"
							title="Sao chép câu trả lời"
						>
							{copied ? (
								<>
									<Check className="w-3.5 h-3.5 text-emerald-600" />
									<span className="text-emerald-700 font-medium">
										Đã sao chép
									</span>
								</>
							) : (
								<>
									<Copy className="w-3.5 h-3.5" />
									<span>Sao chép</span>
								</>
							)}
						</button>

						{onRegenerate && (
							<button
								type="button"
								onClick={onRegenerate}
								className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg hover:bg-stone-200/60 text-stone-600 hover:text-stone-900 transition-colors"
								title="Tạo lại câu trả lời này"
							>
								<RotateCcw className="w-3.5 h-3.5" />
								<span>Tạo lại</span>
							</button>
						)}
					</div>

					{stats && (
						<div className="flex items-center gap-2 font-mono text-[10px] text-stone-500 bg-stone-100/80 px-2 py-0.5 rounded-md border border-stone-200/60">
							{stats.tps && (
								<span className="text-amber-700 font-semibold">
									{stats.tps} TPS
								</span>
							)}
							{stats.elapsed_sec && (
								<span>• {stats.elapsed_sec}s</span>
							)}
							{stats.tokens && (
								<span>• {stats.tokens} tokens</span>
							)}
						</div>
					)}
				</div>
			)}
		</div>
	);
};
