import React from "react";
import { cn } from "@/shared/lib";

export type StatCardVariant =
	| "indigo"
	| "emerald"
	| "amber"
	| "rose"
	| "sky"
	| "purple"
	| "neutral";

export interface StatCardProps {
	icon?: React.ReactNode;
	label: string;
	value: React.ReactNode;
	subtext?: React.ReactNode;
	variant?: StatCardVariant;
	className?: string;
}

const variantStyles: Record<
	StatCardVariant,
	{ iconColor: string; valueColor: string; bgHighlight: string }
> = {
	indigo: {
		iconColor: "text-amber-600",
		valueColor: "text-stone-900",
		bgHighlight: "hover:border-amber-500/50",
	},
	emerald: {
		iconColor: "text-emerald-600",
		valueColor: "text-stone-900",
		bgHighlight: "hover:border-emerald-500/50",
	},
	amber: {
		iconColor: "text-amber-600",
		valueColor: "text-stone-900",
		bgHighlight: "hover:border-amber-500/50",
	},
	rose: {
		iconColor: "text-rose-600",
		valueColor: "text-stone-900",
		bgHighlight: "hover:border-rose-500/50",
	},
	sky: {
		iconColor: "text-sky-600",
		valueColor: "text-stone-900",
		bgHighlight: "hover:border-sky-500/50",
	},
	purple: {
		iconColor: "text-stone-700",
		valueColor: "text-stone-900",
		bgHighlight: "hover:border-stone-400",
	},
	neutral: {
		iconColor: "text-stone-500",
		valueColor: "text-stone-900",
		bgHighlight: "hover:border-stone-300",
	},
};

export const StatCard: React.FC<StatCardProps> = ({
	icon,
	label,
	value,
	subtext,
	variant = "neutral",
	className,
}) => {
	const styles = variantStyles[variant];

	return (
		<div
			className={cn(
				"p-3.5 sm:p-4 rounded-xl bg-[#faf8f5] border border-stone-300/80 shadow-warm-sm transition-all duration-200 flex flex-col justify-between",
				styles.bgHighlight,
				className,
			)}
		>
			<div className="flex items-center justify-between gap-2 mb-1.5">
				<span className="text-[11px] font-medium text-stone-500 truncate">
					{label}
				</span>
				{icon && (
					<span className={cn("shrink-0", styles.iconColor)}>
						{icon}
					</span>
				)}
			</div>

			<div
				className={cn(
					"text-lg sm:text-xl font-bold font-mono tracking-tight",
					styles.valueColor,
				)}
			>
				{value}
			</div>

			{subtext && (
				<div className="text-[10px] text-stone-400 mt-1 truncate">
					{subtext}
				</div>
			)}
		</div>
	);
};
