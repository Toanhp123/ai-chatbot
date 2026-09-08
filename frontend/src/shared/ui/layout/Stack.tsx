import React from "react";
import { cn } from "@/shared/lib";

export interface StackProps extends React.HTMLAttributes<HTMLDivElement> {
	direction?: "row" | "column";
	gap?: "none" | "xs" | "sm" | "md" | "lg" | "xl";
	align?: "start" | "center" | "end" | "stretch" | "baseline";
	justify?: "start" | "center" | "end" | "between" | "around";
	wrap?: boolean;
	children: React.ReactNode;
}

const gapMap = {
	none: "gap-0",
	xs: "gap-1",
	sm: "gap-2",
	md: "gap-3",
	lg: "gap-4",
	xl: "gap-6",
};

const alignMap = {
	start: "items-start",
	center: "items-center",
	end: "items-end",
	stretch: "items-stretch",
	baseline: "items-baseline",
};

const justifyMap = {
	start: "justify-start",
	center: "justify-center",
	end: "justify-end",
	between: "justify-between",
	around: "justify-around",
};

export const Stack: React.FC<StackProps> = ({
	direction = "column",
	gap = "md",
	align = "stretch",
	justify = "start",
	wrap = false,
	className,
	children,
	...props
}) => {
	return (
		<div
			className={cn(
				"flex",
				direction === "row" ? "flex-row" : "flex-col",
				gapMap[gap],
				alignMap[align],
				justifyMap[justify],
				wrap && "flex-wrap",
				className,
			)}
			{...props}
		>
			{children}
		</div>
	);
};
