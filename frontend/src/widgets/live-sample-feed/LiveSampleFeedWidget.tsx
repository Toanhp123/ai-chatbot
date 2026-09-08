import React, { useState } from "react";
import {
	MessageSquareQuote,
	History,
	ChevronDown,
	ChevronUp,
} from "lucide-react";
import { Card, Badge } from "@/shared/ui";
import type { SampleRecord } from "@/entities/training";

export interface LiveSampleFeedWidgetProps {
	lastSampleText: string;
	sampleHistory: SampleRecord[];
	currentStep?: number;
	onSelectSample?: (text: string) => void;
}

export const LiveSampleFeedWidget: React.FC<LiveSampleFeedWidgetProps> = ({
	lastSampleText,
	sampleHistory,
	currentStep = 0,
	onSelectSample,
}) => {
	const [showHistory, setShowHistory] = useState(false);

	const latestSample =
		lastSampleText ||
		(sampleHistory.length > 0
			? sampleHistory[sampleHistory.length - 1].text
			: "");

	const latestStep =
		sampleHistory.length > 0
			? sampleHistory[sampleHistory.length - 1].step
			: currentStep;

	return (
		<Card
			header={
				<div className="flex items-center space-x-2">
					<MessageSquareQuote className="w-4 h-4 text-amber-700" />
					<span>
						Kiểm Thử Đầu Ra Định Kỳ (Real-time Qualitative Output)
					</span>
				</div>
			}
			subtitle="Mẫu phản hồi tự động sinh tại mỗi chu kỳ đánh giá (eval) để kiểm tra chất lượng suy luận và tạo câu"
			action={
				sampleHistory.length > 0 ? (
					<Badge variant="brand">Mốc bước: {latestStep}</Badge>
				) : undefined
			}
			className="space-y-3"
		>
			{/* Latest Sample View */}
			<div className="bg-[#f4f3ed] p-5 rounded-xl border border-stone-300/80 font-serif text-sm text-stone-900 min-h-[90px] whitespace-pre-wrap leading-relaxed select-text shadow-inner">
				{latestSample ? (
					<div className="text-base text-stone-900 leading-[1.8] italic">
						"{latestSample}"
					</div>
				) : (
					<div className="flex items-center gap-3 py-1 text-stone-500">
						<MessageSquareQuote className="w-5 h-5 text-amber-600/70 shrink-0" />
						<span className="text-xs italic font-sans text-stone-500">
							Chưa có mẫu đầu ra trong phiên hiện tại... Trợ lý
							Aura AI sẽ tự động sinh văn bản kiểm thử khi chạm
							chu kỳ đánh giá (eval) kế tiếp.
						</span>
					</div>
				)}
			</div>

			{/* Historical Samples Collapsible Accordion */}
			{sampleHistory.length > 1 && (
				<div className="pt-2 border-t border-stone-200/80">
					<button
						type="button"
						onClick={() => setShowHistory((prev) => !prev)}
						className="flex items-center justify-between w-full text-xs font-mono text-stone-500 hover:text-stone-800 transition-colors py-1"
					>
						<div className="flex items-center gap-1.5">
							<History className="w-3.5 h-3.5 text-amber-600" />
							<span>
								Xem các mốc kiểm thử trước đó (
								{sampleHistory.length} bản ghi)
							</span>
						</div>
						{showHistory ? (
							<ChevronUp className="w-3.5 h-3.5" />
						) : (
							<ChevronDown className="w-3.5 h-3.5" />
						)}
					</button>

					{showHistory && (
						<div className="mt-3 space-y-2.5 max-h-[260px] overflow-y-auto pr-1 animate-in fade-in duration-200">
							{[...sampleHistory].reverse().map((sample, idx) => (
								<div
									key={idx}
									onClick={() =>
										onSelectSample?.(sample.text)
									}
									className={`p-3 bg-[#faf8f5] rounded-xl border border-stone-300/80 text-xs font-serif text-stone-900 space-y-1.5 transition-all shadow-warm-sm ${
										onSelectSample
											? "cursor-pointer hover:border-amber-500/50"
											: ""
									}`}
								>
									<div className="flex items-center justify-between text-[11px] font-mono text-amber-800 border-b border-stone-200/60 pb-1">
										<span className="font-semibold">
											Mốc bước: {sample.step}
										</span>
										<span className="text-stone-400">
											{sample.timestamp}
										</span>
									</div>
									<div className="whitespace-pre-wrap leading-relaxed">
										{sample.text}
									</div>
								</div>
							))}
						</div>
					)}
				</div>
			)}
		</Card>
	);
};
