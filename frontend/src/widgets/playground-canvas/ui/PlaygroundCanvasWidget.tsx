import React, { useRef, useEffect } from "react";
import type { GenerationStats } from "@/features/generate";
import { ChatBubble, PromptInput, PresetCard, Badge } from "@/shared/ui";
import { Sliders, Sparkles, BookOpen, Trash2 } from "lucide-react";

export interface PlaygroundCanvasWidgetProps {
	prompt: string;
	onPromptChange: (newPrompt: string) => void;
	submittedPrompt: string;
	generatedText: string;
	isGenerating: boolean;
	stats: GenerationStats | null;
	onGenerate: (overridePrompt?: string) => void;
	onStop: () => void;
	onClear: () => void;
	onOpenParams?: () => void;
	activeCheckpoint?: string;
}

export const PlaygroundCanvasWidget: React.FC<PlaygroundCanvasWidgetProps> = ({
	prompt,
	onPromptChange,
	submittedPrompt,
	generatedText,
	isGenerating,
	stats,
	onGenerate,
	onStop,
	onClear,
	onOpenParams,
	activeCheckpoint,
}) => {
	const messagesEndRef = useRef<HTMLDivElement | null>(null);

	const presets = [
		{
			title: "Trợ lý viết & biên tập",
			prompt: "Hãy giúp tôi viết một đoạn mở đầu ấn tượng cho bài viết về công nghệ và đời sống:",
			description: "Khởi tạo nội dung bài viết, báo cáo hoặc email",
		},
		{
			title: "Giải thích khái niệm",
			prompt: "Giải thích nguyên lý hoạt động của kiến trúc Transformer và cơ chế Attention một cách trực quan, dễ hiểu:",
			description: "Làm rõ các khái niệm phức tạp một cách súc tích",
		},
		{
			title: "Lập trình & giải thuật",
			prompt: "Viết một hàm Python tối ưu để xử lý chuỗi văn bản và phân tích dữ liệu hiệu quả:",
			description: "Hỗ trợ viết mã nguồn, gỡ lỗi và giải thuật",
		},
		{
			title: "Tóm tắt & phân tích",
			prompt: "Hãy tóm tắt các điểm then chốt và rút ra các bài học hành động từ nội dung sau:",
			description: "Chắt lọc thông tin và cấu trúc lại luận điểm",
		},
	];

	// Auto-scroll to bottom while streaming
	useEffect(() => {
		if (isGenerating && messagesEndRef.current) {
			messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
		}
	}, [generatedText, isGenerating]);

	const hasConversation = Boolean(
		submittedPrompt.trim() || generatedText.trim() || isGenerating,
	);

	const handlePresetClick = (presetPrompt: string) => {
		onGenerate(presetPrompt);
	};

	const modelDisplayName = activeCheckpoint
		? activeCheckpoint.split("/").pop()
		: "Aura AI (124M)";

	return (
		<div className="flex flex-col h-[calc(100vh-4rem)] max-w-5xl mx-auto w-full">
			{/* Top Bar for Chat Canvas */}
			<div className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-stone-200/80 bg-[#f4f3ed]/90 backdrop-blur-sm shrink-0">
				<div className="flex items-center gap-2.5">
					<div className="flex items-center gap-2">
						<span className="text-xs font-semibold text-stone-900">
							Aura AI
						</span>
						<Badge variant="brand" className="text-[10px]">
							Language Model • SDPA
						</Badge>
					</div>
					{activeCheckpoint && (
						<span className="hidden md:inline-block text-[11px] font-mono text-stone-500 border-l border-stone-300 pl-2.5">
							{modelDisplayName}
						</span>
					)}
				</div>

				<div className="flex items-center gap-2">
					{hasConversation && (
						<button
							type="button"
							onClick={onClear}
							className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-stone-600 hover:text-stone-900 hover:bg-stone-200/60 transition-colors"
							title="Làm mới đoạn hội thoại"
						>
							<Trash2 className="w-3.5 h-3.5" />
							<span className="hidden sm:inline">Làm mới</span>
						</button>
					)}

					{onOpenParams && (
						<button
							type="button"
							onClick={onOpenParams}
							className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-stone-300/80 hover:border-amber-500/60 bg-[#faf8f5] hover:bg-[#f4f1e8] text-stone-700 text-xs font-medium shadow-warm-sm transition-all"
							title="Mở cài đặt siêu tham số sinh từ (Temperature, Top-p, Min-p)"
						>
							<Sliders className="w-3.5 h-3.5 text-amber-600" />
							<span>Tham Số Sampling</span>
						</button>
					)}
				</div>
			</div>

			{/* Main Scrollable Chat Stream Area */}
			<div className="flex-1 overflow-y-auto px-2 sm:px-4 py-6 space-y-4">
				{!hasConversation ? (
					/* Claude-style Welcoming Hero & Preset Starters */
					<div className="max-w-2xl mx-auto my-auto py-12 px-4 text-center space-y-6">
						<div className="w-14 h-14 rounded-2xl bg-amber-100/80 text-amber-800 border border-amber-200/80 mx-auto flex items-center justify-center shadow-warm-sm">
							<Sparkles className="w-7 h-7 fill-amber-700/10" />
						</div>

						<div className="space-y-2">
							<h2 className="text-xl sm:text-2xl font-bold text-stone-900 tracking-tight font-serif">
								Chào bạn! Hôm nay tôi có thể giúp gì cho bạn?
							</h2>
							<p className="text-xs sm:text-sm text-stone-500 max-w-lg mx-auto leading-relaxed font-normal">
								Tôi là trợ lý thông minh Aura AI — sẵn sàng hỗ
								trợ bạn trò chuyện, giải đáp thắc mắc, phân tích
								văn bản và đồng hành trong công việc. Hãy gửi
								tin nhắn hoặc chọn một gợi ý bên dưới để bắt
								đầu.
							</p>
						</div>

						{/* Prompt Starter Cards */}
						<div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4 text-left">
							{presets.map((preset, idx) => (
								<PresetCard
									key={idx}
									title={preset.title}
									prompt={preset.prompt}
									description={preset.description}
									onClick={handlePresetClick}
								/>
							))}
						</div>
					</div>
				) : (
					/* Message Thread */
					<div className="space-y-3 pb-6">
						{/* Quick preset pills if user wants to switch prompts */}
						<div className="max-w-3xl mx-auto flex flex-wrap items-center gap-1.5 px-3 mb-2 text-xs">
							<span className="text-stone-400 flex items-center gap-1 text-[11px]">
								<BookOpen className="w-3 h-3 text-amber-600" />{" "}
								Gợi ý chủ đề:
							</span>
							{presets.map((p, idx) => (
								<button
									key={idx}
									type="button"
									onClick={() => onGenerate(p.prompt)}
									className="px-2.5 py-1 rounded-lg bg-[#faf8f5] border border-stone-300/80 hover:border-amber-500/50 hover:bg-[#f4f1e8] text-[11px] text-stone-700 hover:text-stone-900 transition-colors shadow-warm-sm"
								>
									{p.title}
								</button>
							))}
						</div>

						{/* User Message (Pill container on right) */}
						{submittedPrompt && (
							<ChatBubble
								role="user"
								content={submittedPrompt}
								timestamp="Vừa xong"
							/>
						)}

						{/* Assistant Response Message (Floats on canvas with serif typography) */}
						{(generatedText || isGenerating) && (
							<ChatBubble
								role="assistant"
								content={
									generatedText ||
									(isGenerating
										? "Aura AI đang suy nghĩ và phản hồi..."
										: "")
								}
								isStreaming={isGenerating}
								stats={stats}
								onRegenerate={() => onGenerate(submittedPrompt)}
							/>
						)}

						<div ref={messagesEndRef} />
					</div>
				)}
			</div>

			{/* Claude Signature Floating Bottom Prompt Box */}
			<div className="shrink-0 pb-4 pt-2 bg-gradient-to-t from-[#f4f3ed] via-[#f4f3ed] to-transparent">
				<PromptInput
					value={prompt}
					onChange={onPromptChange}
					onSubmit={() => onGenerate()}
					onStop={onStop}
					onClear={hasConversation ? onClear : undefined}
					onOpenParams={onOpenParams}
					modelName={modelDisplayName}
					isGenerating={isGenerating}
					placeholder="Gửi tin nhắn cho Aura AI (ví dụ: Giải thích khái niệm, tóm tắt, viết mã...)..."
				/>
			</div>
		</div>
	);
};
