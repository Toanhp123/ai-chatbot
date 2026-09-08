import React from "react";
import { cn } from "@/shared/lib";

export interface DividerProps {
	label?: React.ReactNode;
	orientation?: "horizontal" | "vertical";
	className?: string;
}

export const Divider: React.FC<DividerProps> = ({
	label,
	orientation = "horizontal",
	className,
}) => {
	if (orientation === "vertical") {
		return (
			<div
				className={cn(
					"w-px self-stretch bg-stone-300/80 mx-2 select-none",
					className,
				)}
			/>
		);
	}

	if (!label) {
		return (
			<hr
				className={cn(
					"w-full border-t border-stone-300/80 my-4 select-none",
					className,
				)}
			/>
		);
	}

	return (
		<div
			className={cn(
				"relative my-5 flex items-center select-none",
				className,
			)}
		>
			<div className="flex-grow border-t border-stone-300/80" />
			<span className="shrink-0 px-3 text-[11px] font-medium text-stone-500 uppercase tracking-wider">
				{label}
			</span>
			<div className="flex-grow border-t border-stone-300/80" />
		</div>
	);
};
