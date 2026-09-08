import React from "react";
import { cn } from "@/shared/lib";

export type ProgressBarVariant =
	| "auto"
	| "indigo"
	| "emerald"
	| "amber"
	| "rose"
	| "sky";

export interface ProgressBarProps {
	value: number; // 0 to 100
	max?: number;
	label?: React.ReactNode;
	valueText?: React.ReactNode;
	variant?: ProgressBarVariant;
	size?: "sm" | "md" | "lg";
	showPercent?: boolean;
	className?: string;
}

const sizeMap = {
	sm: "h-1.5",
	md: "h-2.5",
	lg: "h-4",
};

export const ProgressBar: React.FC<ProgressBarProps> = ({
	value,
	max = 100,
	label,
	valueText,
	variant = "auto",
	size = "md",
	showPercent = false,
	className,
}) => {
	const percent = Math.min(100, Math.max(0, (value / max) * 100));

	const getBarColor = () => {
		if (variant === "indigo") return "bg-amber-600";
		if (variant === "emerald") return "bg-emerald-600";
		if (variant === "amber") return "bg-amber-500";
		if (variant === "rose") return "bg-rose-500";
		if (variant === "sky") return "bg-sky-500";

		// "auto" mode: dynamic threshold based on usage
		if (percent >= 90) return "bg-rose-500";
		if (percent >= 75) return "bg-amber-500";
		return "bg-emerald-600";
	};

	return (
		<div className={cn("w-full space-y-1.5", className)}>
			{(label || valueText || showPercent) && (
				<div className="flex items-center justify-between text-xs font-medium">
					{label && <span className="text-stone-700">{label}</span>}
					<div className="flex items-center gap-1.5 font-mono text-[11px] text-stone-500">
						{valueText && <span>{valueText}</span>}
						{showPercent && (
							<span className="font-semibold text-stone-900">
								{percent.toFixed(1)}%
							</span>
						)}
					</div>
				</div>
			)}

			<div
				className={cn(
					"w-full bg-stone-100 border border-stone-200/80 rounded-full overflow-hidden p-0.5",
					sizeMap[size],
				)}
			>
				<div
					className={cn(
						"h-full rounded-full transition-all duration-300 shadow-sm",
						getBarColor(),
					)}
					style={{ width: `${percent}%` }}
				/>
			</div>
		</div>
	);
};
