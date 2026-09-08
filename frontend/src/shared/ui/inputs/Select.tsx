import React from "react";
import * as SelectPrimitive from "@radix-ui/react-select";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/shared/lib";

export interface SelectOption {
	value: string;
	label: string;
	description?: string;
}

export interface SelectProps {
	value?: string;
	defaultValue?: string;
	onValueChange?: (value: string) => void;
	options?: SelectOption[];
	placeholder?: string;
	label?: string;
	hint?: string;
	error?: string;
	disabled?: boolean;
	className?: string;
	triggerClassName?: string;
	children?: React.ReactNode;
}

export const Select = React.forwardRef<HTMLButtonElement, SelectProps>(
	(
		{
			value,
			defaultValue,
			onValueChange,
			options,
			placeholder = "Chọn một mục...",
			label,
			hint,
			error,
			disabled = false,
			className,
			triggerClassName,
			children,
		},
		ref,
	) => {
		return (
			<div className={cn("w-full space-y-1 select-none", className)}>
				{(label || hint) && (
					<div className="flex items-center justify-between">
						{label && (
							<label className="block text-xs font-medium text-stone-700">
								{label}
							</label>
						)}
						{hint && (
							<span className="text-[10px] text-stone-500 font-sans">
								{hint}
							</span>
						)}
					</div>
				)}

				<SelectPrimitive.Root
					value={value || undefined}
					defaultValue={defaultValue}
					onValueChange={onValueChange}
					disabled={disabled}
				>
					<SelectPrimitive.Trigger
						ref={ref}
						className={cn(
							"w-full flex items-center justify-between bg-[#faf8f5] border border-stone-300/80 rounded-xl px-3 py-2 text-xs text-stone-900 shadow-warm-sm outline-none focus:outline-none focus:border-amber-600 focus:ring-1 focus:ring-amber-500/20 hover:border-stone-400/90 transition-colors font-mono disabled:opacity-50 disabled:cursor-not-allowed group",
							error &&
								"border-rose-400 focus:border-rose-500 focus:ring-rose-500",
							triggerClassName,
						)}
					>
						<SelectPrimitive.Value placeholder={placeholder} />
						<SelectPrimitive.Icon asChild>
							<ChevronDown className="w-3.5 h-3.5 text-stone-500 transition-transform duration-200 group-data-[state=open]:rotate-180 shrink-0 ml-2" />
						</SelectPrimitive.Icon>
					</SelectPrimitive.Trigger>

					<SelectPrimitive.Portal>
						<SelectPrimitive.Content
							position="popper"
							sideOffset={4}
							className="z-50 min-w-[var(--radix-select-trigger-width)] max-h-72 overflow-y-auto rounded-xl border border-stone-300/80 bg-[#faf8f5] p-1 shadow-warm-lg font-mono text-xs animate-in fade-in-0 zoom-in-95"
						>
							<SelectPrimitive.Viewport className="p-0.5 space-y-0.5">
								{options
									? options.map((opt) => (
											<SelectPrimitive.Item
												key={opt.value}
												value={opt.value}
												className="relative flex cursor-pointer select-none items-center justify-between rounded-lg px-2.5 py-1.5 text-xs text-stone-800 outline-none hover:bg-[#f4f1e8] hover:text-stone-900 focus:bg-[#f4f1e8] focus:text-stone-900 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 transition-colors"
											>
												<div className="flex flex-col">
													<SelectPrimitive.ItemText>
														<span className="font-mono font-medium">
															{opt.label}
														</span>
													</SelectPrimitive.ItemText>
													{opt.description && (
														<span className="text-[10px] text-stone-500 font-sans mt-0.5">
															{opt.description}
														</span>
													)}
												</div>
												<SelectPrimitive.ItemIndicator>
													<Check className="w-3.5 h-3.5 text-amber-700 ml-2" />
												</SelectPrimitive.ItemIndicator>
											</SelectPrimitive.Item>
										))
									: children}
							</SelectPrimitive.Viewport>
						</SelectPrimitive.Content>
					</SelectPrimitive.Portal>
				</SelectPrimitive.Root>

				{error && (
					<p className="text-[10px] text-rose-600 mt-0.5 font-sans">
						{error}
					</p>
				)}
			</div>
		);
	},
);

Select.displayName = "Select";
