import React from "react";
import { cn } from "@/shared/lib";

export type StatusDotColor = "emerald" | "amber" | "rose" | "indigo" | "slate";

export interface StatusDotProps {
	color?: StatusDotColor;
	pulse?: boolean;
	size?: "sm" | "md" | "lg";
	label?: React.ReactNode;
	className?: string;
}

const colorMap: Record<StatusDotColor, { bg: string; ping: string }> = {
	emerald: { bg: "bg-emerald-500", ping: "bg-emerald-400" },
	amber: { bg: "bg-amber-500", ping: "bg-amber-400" },
	rose: { bg: "bg-rose-500", ping: "bg-rose-400" },
	indigo: { bg: "bg-indigo-500", ping: "bg-indigo-400" },
	slate: { bg: "bg-slate-500", ping: "bg-slate-400" },
};

const sizeMap = {
	sm: "w-1.5 h-1.5",
	md: "w-2.5 h-2.5",
	lg: "w-3 h-3",
};

export const StatusDot: React.FC<StatusDotProps> = ({
	color = "emerald",
	pulse = false,
	size = "md",
	label,
	className,
}) => {
	const colors = colorMap[color];

	return (
		<span className={cn("inline-flex items-center gap-1.5", className)}>
			<span className="relative flex">
				{pulse && (
					<span
						className={cn(
							"animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
							colors.ping,
						)}
					/>
				)}
				<span
					className={cn(
						"relative inline-flex rounded-full shadow-sm",
						sizeMap[size],
						colors.bg,
					)}
				/>
			</span>
			{label && (
				<span className="text-xs font-medium text-stone-700">
					{label}
				</span>
			)}
		</span>
	);
};
