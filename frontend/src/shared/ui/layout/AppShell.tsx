import React from "react";
import { cn } from "@/shared/lib";

export interface AppShellProps {
	sidebar?: React.ReactNode;
	header?: React.ReactNode;
	children: React.ReactNode;
	footer?: React.ReactNode;
	className?: string;
}

export const AppShell: React.FC<AppShellProps> = ({
	sidebar,
	header,
	children,
	footer,
	className,
}) => {
	return (
		<div
			className={cn(
				"h-screen w-full bg-[#f4f3ed] text-stone-900 flex flex-row font-sans selection:bg-amber-500/20 selection:text-amber-900 overflow-hidden",
				className,
			)}
		>
			{/* Left ChatGPT-style Sidebar */}
			{sidebar}

			{/* Main Content & Viewport Container */}
			<div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative">
				{/* Top Header (if provided) */}
				{header && (
					<header className="shrink-0 z-30 w-full bg-[#f4f3ed]/90 backdrop-blur-md border-b border-stone-200/80">
						{header}
					</header>
				)}

				{/* Main Scrollable Viewport with Stable Scrollbar Gutter (Zero Layout Shift & Transparent Track) */}
				<main className="flex-1 w-full overflow-y-auto overflow-x-hidden flex flex-col [scrollbar-gutter:stable]">
					<div className="flex-1 w-full">{children}</div>

					{/* Optional Footer */}
					{footer && (
						<footer className="border-t border-stone-300/80 bg-[#faf8f5]/90 backdrop-blur-sm py-3 px-6 text-xs text-stone-500 shrink-0">
							{footer}
						</footer>
					)}
				</main>
			</div>
		</div>
	);
};
