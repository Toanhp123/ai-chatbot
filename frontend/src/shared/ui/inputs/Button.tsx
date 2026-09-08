import React from "react";
import { cn } from "@/shared/lib";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
	variant?:
		| "primary"
		| "secondary"
		| "danger"
		| "ghost"
		| "outline"
		| "emerald";
	size?: "sm" | "md" | "lg";
	isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
	children,
	className,
	variant = "primary",
	size = "md",
	isLoading = false,
	disabled,
	...props
}) => {
	const baseStyles =
		"inline-flex items-center justify-center font-medium rounded-xl transition-colors duration-150 outline-none focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 select-none";

	const variants = {
		primary:
			"bg-amber-600 hover:bg-amber-700 text-white shadow-warm-sm border border-amber-700/20",
		secondary:
			"bg-[#ebe8df] hover:bg-[#e2ded5] text-stone-800 border border-stone-300/80",
		emerald:
			"bg-emerald-600 hover:bg-emerald-700 text-white shadow-warm-sm border border-emerald-700/20",
		danger: "bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200",
		ghost: "text-stone-600 hover:text-stone-900 hover:bg-stone-200/50 border border-transparent",
		outline:
			"bg-[#faf8f5] hover:bg-[#f4f1e8] text-stone-700 border border-stone-300/80 shadow-warm-sm",
	};

	const sizes = {
		sm: "text-xs px-3 py-1.5 gap-1.5",
		md: "text-xs px-4 py-2.5 gap-2",
		lg: "text-sm px-5 py-3 gap-2.5",
	};

	return (
		<button
			className={cn(
				baseStyles,
				variants[variant],
				sizes[size],
				className,
			)}
			disabled={disabled || isLoading}
			{...props}
		>
			{isLoading && (
				<svg
					className="animate-spin -ml-1 mr-1.5 h-3.5 w-3.5 text-current"
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
				>
					<circle
						className="opacity-25"
						cx="12"
						cy="12"
						r="10"
						stroke="currentColor"
						strokeWidth="4"
					></circle>
					<path
						className="opacity-75"
						fill="currentColor"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
					></path>
				</svg>
			)}
			{children}
		</button>
	);
};
