import React from "react";
import { cn } from "@/shared/lib";

export interface SwitchProps {
	checked: boolean;
	onChange: (checked: boolean) => void;
	label?: React.ReactNode;
	description?: React.ReactNode;
	disabled?: boolean;
	className?: string;
	labelClassName?: string;
}

export const Switch: React.FC<SwitchProps> = ({
	checked,
	onChange,
	label,
	description,
	disabled = false,
	className,
	labelClassName,
}) => {
	return (
		<label
			className={cn(
				"flex items-center justify-between gap-3 cursor-pointer select-none group",
				disabled && "opacity-50 cursor-not-allowed",
				className,
			)}
		>
			{(label || description) && (
				<div className="flex flex-col">
					{label && (
						<span
							className={cn(
								"text-xs font-medium text-stone-700 group-hover:text-stone-900 transition-colors",
								labelClassName,
							)}
						>
							{label}
						</span>
					)}
					{description && (
						<span className="text-[10px] text-stone-500">
							{description}
						</span>
					)}
				</div>
			)}

			<button
				type="button"
				role="switch"
				aria-checked={checked}
				disabled={disabled}
				onClick={() => !disabled && onChange(!checked)}
				className={cn(
					"relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 focus-visible:ring-offset-stone-50",
					checked ? "bg-amber-600" : "bg-stone-300",
					disabled && "cursor-not-allowed",
				)}
			>
				<span
					className={cn(
						"pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-warm-sm ring-0 transition duration-200 ease-in-out",
						checked ? "translate-x-4" : "translate-x-0",
					)}
				/>
			</button>
		</label>
	);
};
