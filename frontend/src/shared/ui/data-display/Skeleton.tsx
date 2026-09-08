import React from "react";
import { cn } from "@/shared/lib";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
	variant?: "default" | "circular" | "card";
}

export const Skeleton: React.FC<SkeletonProps> = ({
	className,
	variant = "default",
	...props
}) => {
	return (
		<div
			className={cn(
				"animate-pulse bg-stone-200/80 rounded-lg",
				variant === "circular" && "rounded-full",
				variant === "card" &&
					"rounded-2xl border border-stone-300/80 bg-[#faf8f5] p-5",
				className,
			)}
			{...props}
		/>
	);
};
