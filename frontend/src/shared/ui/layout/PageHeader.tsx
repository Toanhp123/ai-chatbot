import React from "react";
import { cn } from "@/shared/lib";

export interface PageHeaderProps {
	icon?: React.ReactNode;
	title: string;
	subtitle?: string;
	badge?: React.ReactNode;
	actions?: React.ReactNode;
	className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
	icon,
	title,
	subtitle,
	badge,
	actions,
	className,
}) => {
	return (
		<div
			className={cn(
				"p-4 sm:p-5 rounded-2xl bg-[#faf8f5] border border-stone-300/80 shadow-warm-sm flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all",
				className,
			)}
		>
			<div className="flex items-center gap-3.5">
				{icon && (
					<div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200/60 text-amber-700 shrink-0">
						{icon}
					</div>
				)}
				<div className="space-y-0.5">
					<div className="flex flex-wrap items-center gap-2">
						<h1 className="text-base sm:text-lg font-bold text-stone-900 tracking-tight">
							{title}
						</h1>
						{badge}
					</div>
					{subtitle && (
						<p className="text-xs text-stone-500 max-w-2xl leading-relaxed">
							{subtitle}
						</p>
					)}
				</div>
			</div>

			{actions && (
				<div className="flex items-center gap-2 shrink-0 self-end md:self-center">
					{actions}
				</div>
			)}
		</div>
	);
};
