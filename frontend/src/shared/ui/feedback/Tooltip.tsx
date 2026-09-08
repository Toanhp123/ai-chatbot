import React, { useState } from "react";
import { cn } from "@/shared/lib";

export interface TooltipProps {
	content: React.ReactNode;
	position?: "top" | "bottom" | "left" | "right";
	children: React.ReactNode;
	className?: string;
}

const positionMap = {
	top: "bottom-full left-1/2 -translate-x-1/2 mb-1.5",
	bottom: "top-full left-1/2 -translate-x-1/2 mt-1.5",
	left: "right-full top-1/2 -translate-y-1/2 mr-1.5",
	right: "left-full top-1/2 -translate-y-1/2 ml-1.5",
};

export const Tooltip: React.FC<TooltipProps> = ({
	content,
	position = "top",
	children,
	className,
}) => {
	const [isVisible, setIsVisible] = useState(false);

	return (
		<div
			className={cn("relative inline-flex items-center", className)}
			onMouseEnter={() => setIsVisible(true)}
			onMouseLeave={() => setIsVisible(false)}
			onFocus={() => setIsVisible(true)}
			onBlur={() => setIsVisible(false)}
		>
			{children}

			{isVisible && (
				<div
					role="tooltip"
					className={cn(
						"absolute z-50 px-2.5 py-1 text-[11px] font-medium text-stone-100 bg-[#1c1917] border border-stone-700/80 rounded-lg shadow-xl backdrop-blur-md whitespace-nowrap pointer-events-none animate-fadeIn",
						positionMap[position],
					)}
				>
					{content}
				</div>
			)}
		</div>
	);
};
