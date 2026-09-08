import React from "react";
import { cn } from "@/shared/lib";

export interface PageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
	maxWidth?: "narrow" | "standard" | "wide" | "full";
	spacing?: "none" | "tight" | "normal" | "loose";
	children: React.ReactNode;
}

const maxWidthMap = {
	narrow: "max-w-4xl",
	standard: "max-w-7xl",
	wide: "max-w-[1600px]",
	full: "w-full",
};

const spacingMap = {
	none: "space-y-0",
	tight: "space-y-4",
	normal: "space-y-6",
	loose: "space-y-8",
};

export const PageContainer: React.FC<PageContainerProps> = ({
	maxWidth = "standard",
	spacing = "normal",
	className,
	children,
	...props
}) => {
	return (
		<div
			className={cn(
				"w-full mx-auto transition-all",
				maxWidthMap[maxWidth],
				spacingMap[spacing],
				className,
			)}
			{...props}
		>
			{children}
		</div>
	);
};
