import React from "react";
import { cn } from "@/shared/lib";
import { AlertTriangle, CheckCircle2, Info, XCircle, X } from "lucide-react";

export type AlertVariant = "info" | "success" | "warning" | "error";

export interface AlertProps {
	variant?: AlertVariant;
	title?: string;
	children: React.ReactNode;
	onClose?: () => void;
	className?: string;
}

const variantStyles: Record<
	AlertVariant,
	{ bg: string; border: string; text: string; icon: React.ReactNode }
> = {
	info: {
		bg: "bg-sky-50",
		border: "border-sky-200/80",
		text: "text-sky-900",
		icon: <Info className="w-4 h-4 text-sky-600 shrink-0" />,
	},
	success: {
		bg: "bg-emerald-50",
		border: "border-emerald-200/80",
		text: "text-emerald-900",
		icon: <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />,
	},
	warning: {
		bg: "bg-amber-50",
		border: "border-amber-200/80",
		text: "text-amber-900",
		icon: <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />,
	},
	error: {
		bg: "bg-rose-50",
		border: "border-rose-200/80",
		text: "text-rose-900",
		icon: <XCircle className="w-4 h-4 text-rose-600 shrink-0" />,
	},
};

export const Alert: React.FC<AlertProps> = ({
	variant = "info",
	title,
	children,
	onClose,
	className,
}) => {
	const style = variantStyles[variant];

	return (
		<div
			className={cn(
				"p-3.5 rounded-xl border flex items-start gap-3 text-xs transition-all",
				style.bg,
				style.border,
				style.text,
				className,
			)}
		>
			<div className="mt-0.5">{style.icon}</div>

			<div className="flex-1 space-y-0.5">
				{title && (
					<h5 className="font-semibold tracking-tight text-stone-900">
						{title}
					</h5>
				)}
				<div className="text-[11px] leading-relaxed opacity-90">
					{children}
				</div>
			</div>

			{onClose && (
				<button
					type="button"
					onClick={onClose}
					className="p-1 -mr-1 -mt-1 rounded-lg opacity-60 hover:opacity-100 hover:bg-black/20 transition-all"
				>
					<X className="w-3.5 h-3.5" />
				</button>
			)}
		</div>
	);
};
