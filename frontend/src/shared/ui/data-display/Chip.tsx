import React from "react";
import { cn } from "@/shared/lib";
import { X } from "lucide-react";

export type ChipVariant =
	| "default"
	| "indigo"
	| "sky"
	| "emerald"
	| "amber"
	| "purple"
	| "rose";

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
	variant?: ChipVariant;
	size?: "sm" | "md";
	onRemove?: () => void;
	selected?: boolean;
	children: React.ReactNode;
}

const variantStyles: Record<ChipVariant, string> = {
	default:
		"bg-[#e3e0d5] text-stone-800 border-stone-300/80 hover:bg-[#dedad0] hover:text-stone-900",
	indigo: "bg-amber-100/90 border-amber-300/80 text-amber-900 hover:bg-amber-200/90",
	sky: "bg-sky-100/80 border-sky-300/80 text-sky-900 hover:bg-sky-200/80",
	emerald:
		"bg-emerald-100/80 border-emerald-300/80 text-emerald-900 hover:bg-emerald-200/80",
	amber: "bg-amber-100/90 border-amber-300/90 text-amber-900 hover:bg-amber-200/90",
	purple: "bg-stone-200/90 border-stone-300 text-stone-800 hover:bg-stone-300/90",
	rose: "bg-rose-100/80 border-rose-300/80 text-rose-900 hover:bg-rose-200/80",
};

export const Chip: React.FC<ChipProps> = ({
	variant = "default",
	size = "sm",
	onRemove,
	selected = false,
	className,
	children,
	...props
}) => {
	return (
		<span
			className={cn(
				"inline-flex items-center gap-1 font-mono rounded-lg border transition-all select-none shadow-sm",
				size === "sm"
					? "px-2 py-0.5 text-[11px]"
					: "px-2.5 py-1 text-xs",
				variantStyles[variant],
				selected && "ring-1 ring-amber-500/50 border-amber-500/60",
				className,
			)}
			{...props}
		>
			<span>{children}</span>
			{onRemove && (
				<button
					type="button"
					onClick={(e) => {
						e.stopPropagation();
						onRemove();
					}}
					className="hover:text-rose-400 p-0.5 -mr-0.5 rounded transition-colors"
				>
					<X className="w-3 h-3" />
				</button>
			)}
		</span>
	);
};
