import React from "react";
import { Sparkles, ArrowRight } from "lucide-react";
import { cn } from "@/shared/lib";

export interface PresetCardProps {
	title: string;
	prompt: string;
	description?: string;
	onClick: (prompt: string) => void;
	className?: string;
}

export const PresetCard: React.FC<PresetCardProps> = ({
	title,
	prompt,
	description,
	onClick,
	className,
}) => {
	return (
		<button
			type="button"
			onClick={() => onClick(prompt)}
			className={cn(
				"text-left p-4 rounded-2xl bg-[#faf8f5] border border-stone-300/80 shadow-warm-sm hover:shadow-warm-md hover:border-amber-500/60 hover:bg-[#f4f1e8] hover:-translate-y-0.5 transition-all duration-200 group flex flex-col justify-between select-none cursor-pointer w-full",
				className,
			)}
		>
			<div className="flex items-center justify-between gap-2 mb-2 w-full">
				<span className="text-xs font-semibold text-stone-800 group-hover:text-amber-800 transition-colors flex items-center gap-1.5">
					<Sparkles className="w-3.5 h-3.5 text-amber-600/70 group-hover:text-amber-600 transition-colors" />
					{title}
				</span>
				<ArrowRight className="w-3.5 h-3.5 text-stone-300 group-hover:text-amber-600 group-hover:translate-x-0.5 transition-all" />
			</div>
			<p className="text-[13px] font-serif text-stone-700 line-clamp-2 italic leading-relaxed">
				&ldquo;{prompt.trim()}&rdquo;
			</p>
			{description && (
				<span className="text-[10px] text-stone-400 mt-2.5 block font-normal">
					{description}
				</span>
			)}
		</button>
	);
};
