import React, { useRef, useEffect } from "react";
import { ArrowUp, Square, Trash2, Sliders } from "lucide-react";
import { cn } from "@/shared/lib";

export interface PromptInputProps {
	value: string;
	onChange: (value: string) => void;
	onSubmit: () => void;
	onStop?: () => void;
	onClear?: () => void;
	onOpenParams?: () => void;
	modelName?: string;
	isGenerating?: boolean;
	disabled?: boolean;
	placeholder?: string;
	className?: string;
}

export const PromptInput: React.FC<PromptInputProps> = ({
	value,
	onChange,
	onSubmit,
	onStop,
	onClear,
	onOpenParams,
	modelName,
	isGenerating = false,
	disabled = false,
	placeholder = "Nhập tin nhắn hoặc câu hỏi cho AI...",
	className,
}) => {
	const textareaRef = useRef<HTMLTextAreaElement | null>(null);

	// Auto-grow textarea height
	useEffect(() => {
		if (textareaRef.current) {
			textareaRef.current.style.height = "auto";
			textareaRef.current.style.height = `${Math.min(
				textareaRef.current.scrollHeight,
				180,
			)}px`;
		}
	}, [value]);

	const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			if (!isGenerating && value.trim() && !disabled) {
				onSubmit();
			}
		}
	};

	const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;

	return (
		<div className={cn("w-full max-w-3xl mx-auto px-4", className)}>
			{/* Claude Signature Floating Card Container */}
			<div className="relative rounded-2xl sm:rounded-3xl bg-[#faf8f5] border border-stone-300/90 shadow-warm-md hover:border-stone-400/80 focus-within:border-amber-600/60 focus-within:bg-[#faf8f5] focus-within:ring-4 focus-within:ring-amber-500/10 transition-all p-3 sm:p-3.5">
				{/* Expanding Input Area */}
				<textarea
					ref={textareaRef}
					rows={1}
					value={value}
					onChange={(e) => onChange(e.target.value)}
					onKeyDown={handleKeyDown}
					placeholder={placeholder}
					disabled={disabled}
					className="w-full bg-transparent resize-none border-0 text-stone-900 placeholder:text-stone-400 text-sm focus:outline-none px-1 py-1 leading-relaxed max-h-44 overflow-y-auto"
				/>

				{/* Claude-style Inside-Bottom Action Toolbar */}
				<div className="flex items-center justify-between pt-2 border-t border-stone-100 mt-1 select-none">
					{/* Left: Model Chip & Param trigger */}
					<div className="flex items-center gap-1.5 sm:gap-2">
						<div
							className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#e3e0d5] hover:bg-[#dedad0] text-[11px] font-medium text-stone-700 transition-colors border border-[#d5d1c5]/80"
							title="Mô hình ngôn ngữ tự hồi quy"
						>
							<span className="w-1.5 h-1.5 rounded-full bg-amber-600 animate-pulse" />
							<span className="font-semibold truncate max-w-[120px] sm:max-w-[180px]">
								{modelName || "Aura AI • 124M"}
							</span>
							<span className="text-[10px] text-stone-400 font-mono hidden sm:inline">
								SDPA
							</span>
						</div>

						{onOpenParams && (
							<button
								type="button"
								onClick={onOpenParams}
								className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-100 transition-colors"
								title="Cài đặt tham số sinh từ (Temperature, Top-p, Min-p)"
							>
								<Sliders className="w-3.5 h-3.5 text-amber-600" />
							</button>
						)}

						{onClear && value && (
							<button
								type="button"
								onClick={onClear}
								title="Xóa nội dung tin nhắn"
								className="p-1.5 rounded-lg hover:bg-stone-100 text-stone-400 hover:text-stone-700 transition-colors"
							>
								<Trash2 className="w-3.5 h-3.5" />
							</button>
						)}
					</div>

					{/* Right: Word count hint & Circular Terracotta Send Button */}
					<div className="flex items-center gap-2 sm:gap-2.5">
						<span className="hidden md:inline-block text-[11px] text-stone-400">
							{wordCount > 0 && `${wordCount} từ • `}
							Enter để gửi
						</span>

						{isGenerating ? (
							<button
								type="button"
								onClick={onStop}
								className="w-8 h-8 rounded-full bg-amber-600 hover:bg-amber-700 text-white flex items-center justify-center shadow-warm-sm transition-transform active:scale-95"
								title="Dừng tạo phản hồi"
							>
								<Square className="w-3.5 h-3.5 fill-current" />
							</button>
						) : (
							<button
								type="button"
								onClick={onSubmit}
								disabled={!value.trim() || disabled}
								className="w-8 h-8 rounded-full bg-stone-900 hover:bg-amber-700 disabled:bg-stone-200 text-white disabled:text-stone-400 flex items-center justify-center transition-all duration-200 active:scale-95 shadow-warm-sm disabled:cursor-not-allowed disabled:hover:bg-stone-200"
								title="Gửi tin nhắn (Enter)"
							>
								<ArrowUp className="w-4 h-4 stroke-[2.5]" />
							</button>
						)}
					</div>
				</div>
			</div>

			<p className="text-center text-[11px] text-stone-400 mt-2">
				Trợ lý Aura AI có thể hỗ trợ đối thoại, giải đáp và xử lý công
				việc. Nhấn{" "}
				<kbd className="px-1 py-0.5 rounded bg-stone-200/70 font-mono text-[10px] text-stone-600">
					Shift + Enter
				</kbd>{" "}
				để xuống dòng.
			</p>
		</div>
	);
};
