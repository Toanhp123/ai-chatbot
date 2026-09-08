import React from "react";
import { cn } from "@/shared/lib";

export type BadgeVariant =
	| "emerald"
	| "amber"
	| "rose"
	| "brand"
	| "zinc"
	| "purple"
	| "success"
	| "warning"
	| "danger"
	| "info"
	| "neutral";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
	variant?: BadgeVariant;
}

export const Badge: React.FC<BadgeProps> = ({
	children,
	className,
	variant = "zinc",
	...props
}) => {
	const variants: Record<string, string> = {
		emerald: "bg-emerald-50 text-emerald-800 border-emerald-200/80",
		success: "bg-emerald-50 text-emerald-800 border-emerald-200/80",
		amber: "bg-amber-50 text-amber-800 border-amber-200/80",
		warning: "bg-amber-50 text-amber-800 border-amber-200/80",
		rose: "bg-rose-50 text-rose-800 border-rose-200/80",
		danger: "bg-rose-50 text-rose-800 border-rose-200/80",
		brand: "bg-amber-50 text-amber-900 border-amber-200/80",
		info: "bg-sky-50 text-sky-800 border-sky-200/80",
		purple: "bg-stone-100 text-stone-800 border-stone-200/80",
		zinc: "bg-stone-100 text-stone-700 border-stone-200/80",
		neutral: "bg-stone-100 text-stone-700 border-stone-200/80",
	};

	return (
		<span
			className={cn(
				"inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-medium border select-none",
				variants[variant] || variants.zinc,
				className,
			)}
			{...props}
		>
			{children}
		</span>
	);
};
