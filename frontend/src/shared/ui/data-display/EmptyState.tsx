import React from "react";
import { cn } from "@/shared/lib";
import { Inbox } from "lucide-react";

export interface EmptyStateProps {
	icon?: React.ReactNode;
	title: string;
	description?: string;
	action?: React.ReactNode;
	className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
	icon = <Inbox className="w-8 h-8 text-stone-400" />,
	title,
	description,
	action,
	className,
}) => {
	return (
		<div
			className={cn(
				"py-10 px-4 flex flex-col items-center justify-center text-center space-y-3 rounded-xl border border-dashed border-stone-300/80 bg-[#f4f3ed]/60",
				className,
			)}
		>
			<div className="p-3 rounded-2xl bg-[#faf8f5] border border-stone-300/80 text-stone-500 shadow-warm-sm">
				{icon}
			</div>

			<div className="space-y-1 max-w-sm">
				<h4 className="text-xs sm:text-sm font-semibold text-stone-800">
					{title}
				</h4>
				{description && (
					<p className="text-[11px] text-stone-500 leading-relaxed">
						{description}
					</p>
				)}
			</div>

			{action && <div className="pt-1">{action}</div>}
		</div>
	);
};
