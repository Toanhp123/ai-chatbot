import React from "react";
import { cn } from "@/shared/lib";

export interface FormFieldProps {
	label?: React.ReactNode;
	required?: boolean;
	hint?: React.ReactNode;
	error?: React.ReactNode;
	className?: string;
	children: React.ReactNode;
}

export const FormField: React.FC<FormFieldProps> = ({
	label,
	required = false,
	hint,
	error,
	className,
	children,
}) => {
	return (
		<div className={cn("space-y-1.5 w-full", className)}>
			{label && (
				<div className="flex items-center justify-between text-xs">
					<label className="font-medium text-stone-700 select-none flex items-center gap-1">
						<span>{label}</span>
						{required && (
							<span className="text-rose-500 font-bold">*</span>
						)}
					</label>
					{hint && (
						<span className="text-[10px] text-stone-400">
							{hint}
						</span>
					)}
				</div>
			)}

			<div className="relative">{children}</div>

			{error && (
				<p className="text-[10px] text-rose-400 font-medium mt-0.5 animate-fadeIn">
					{error}
				</p>
			)}
		</div>
	);
};
