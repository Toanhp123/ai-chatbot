import React from "react";
import { cn } from "@/shared/lib";

export interface SectionProps extends Omit<
	React.HTMLAttributes<HTMLElement>,
	"title"
> {
	title?: React.ReactNode;
	description?: React.ReactNode;
	actions?: React.ReactNode;
	children: React.ReactNode;
	bordered?: boolean;
}

export const Section: React.FC<SectionProps> = ({
	title,
	description,
	actions,
	children,
	bordered = false,
	className,
	...props
}) => {
	return (
		<section
			className={cn(
				"space-y-4",
				bordered &&
					"p-5 rounded-2xl bg-[#faf8f5] border border-stone-300/80 shadow-warm-sm",
				className,
			)}
			{...props}
		>
			{(title || actions) && (
				<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-1 border-b border-stone-200/80">
					<div>
						{title && (
							<h3 className="text-sm sm:text-base font-semibold text-stone-900 flex items-center gap-2">
								{title}
							</h3>
						)}
						{description && (
							<p className="text-xs text-stone-500 mt-0.5">
								{description}
							</p>
						)}
					</div>
					{actions && (
						<div className="flex items-center gap-2 shrink-0">
							{actions}
						</div>
					)}
				</div>
			)}
			{children}
		</section>
	);
};
