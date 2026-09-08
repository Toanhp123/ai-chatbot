import React from "react";
import { cn } from "@/shared/lib";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
	label?: string;
	error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
	({ className, label, error, ...props }, ref) => {
		return (
			<div className="w-full space-y-1">
				{label && (
					<label className="block text-xs font-medium text-stone-700">
						{label}
					</label>
				)}
				<input
					ref={ref}
					className={cn(
						"w-full bg-[#faf8f5] border border-stone-300/80 rounded-xl px-3 py-2 text-xs text-stone-900 placeholder-stone-400 outline-none focus:outline-none focus:border-amber-600 focus:ring-1 focus:ring-amber-500/20 transition-colors font-mono",
						error &&
							"border-rose-400 focus:border-rose-500 focus:ring-rose-500",
						className,
					)}
					{...props}
				/>
				{error && (
					<p className="text-[10px] text-rose-600 mt-0.5">{error}</p>
				)}
			</div>
		);
	},
);

Input.displayName = "Input";
