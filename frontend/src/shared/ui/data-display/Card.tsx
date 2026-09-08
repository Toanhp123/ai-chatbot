import React from "react";
import { cn } from "@/shared/lib";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
	header?: React.ReactNode;
	subtitle?: React.ReactNode;
	action?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
	children,
	header,
	subtitle,
	action,
	className,
	...props
}) => {
	const hasHeaderProps = Boolean(header || action);

	return (
		<div
			className={cn(
				"bg-[#faf8f5] border border-stone-300/80 rounded-2xl shadow-warm-sm transition-all",
				hasHeaderProps ? "p-5" : "p-0",
				className,
			)}
			{...props}
		>
			{hasHeaderProps && (
				<div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-stone-100 pb-3.5 mb-4 gap-2">
					<div>
						{typeof header === "string" ? (
							<h3 className="text-xs font-semibold text-stone-900 tracking-wide">
								{header}
							</h3>
						) : (
							header
						)}
						{subtitle && (
							<p className="text-[11px] text-stone-500 mt-0.5">
								{subtitle}
							</p>
						)}
					</div>
					{action && (
						<div className="flex items-center gap-2">{action}</div>
					)}
				</div>
			)}
			{children}
		</div>
	);
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
	children,
	className,
	...props
}) => {
	return (
		<div
			className={cn(
				"p-5 flex flex-col space-y-1.5 border-b border-stone-100",
				className,
			)}
			{...props}
		>
			{children}
		</div>
	);
};

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
	children,
	className,
	...props
}) => {
	return (
		<h3
			className={cn(
				"text-sm font-semibold text-stone-900 tracking-tight",
				className,
			)}
			{...props}
		>
			{children}
		</h3>
	);
};

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
	children,
	className,
	...props
}) => {
	return (
		<div className={cn("p-5 pt-4", className)} {...props}>
			{children}
		</div>
	);
};
