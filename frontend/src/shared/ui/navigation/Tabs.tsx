import React, { createContext, useContext, useState } from "react";
import { cn } from "@/shared/lib";

interface TabsContextType {
	value: string;
	onValueChange: (val: string) => void;
}

const TabsContext = createContext<TabsContextType | null>(null);

export interface TabsProps {
	value?: string;
	defaultValue?: string;
	onValueChange?: (value: string) => void;
	className?: string;
	children: React.ReactNode;
}

export const Tabs: React.FC<TabsProps> = ({
	value: controlledValue,
	defaultValue = "",
	onValueChange,
	className,
	children,
}) => {
	const [uncontrolledValue, setUncontrolledValue] = useState(defaultValue);
	const value =
		controlledValue !== undefined ? controlledValue : uncontrolledValue;

	const handleValueChange = (val: string) => {
		if (onValueChange) {
			onValueChange(val);
		} else {
			setUncontrolledValue(val);
		}
	};

	return (
		<TabsContext.Provider
			value={{ value, onValueChange: handleValueChange }}
		>
			<div className={cn("space-y-4 w-full", className)}>{children}</div>
		</TabsContext.Provider>
	);
};

export interface TabsListProps extends React.HTMLAttributes<HTMLDivElement> {
	children: React.ReactNode;
}

export const TabsList: React.FC<TabsListProps> = ({
	className,
	children,
	...props
}) => {
	return (
		<div
			className={cn(
				"inline-flex items-center gap-1 p-1 rounded-xl bg-stone-100 border border-stone-200/90 shadow-inner",
				className,
			)}
			{...props}
		>
			{children}
		</div>
	);
};

export interface TabsTriggerProps {
	value: string;
	disabled?: boolean;
	icon?: React.ReactNode;
	className?: string;
	children: React.ReactNode;
}

export const TabsTrigger: React.FC<TabsTriggerProps> = ({
	value,
	disabled = false,
	icon,
	className,
	children,
}) => {
	const context = useContext(TabsContext);
	if (!context) throw new Error("TabsTrigger must be used within Tabs");

	const isActive = context.value === value;

	return (
		<button
			type="button"
			role="tab"
			aria-selected={isActive}
			disabled={disabled}
			onClick={() => context.onValueChange(value)}
			className={cn(
				"px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1.5 select-none focus:outline-none",
				isActive
					? "bg-[#faf8f5] text-stone-900 shadow-warm-sm border border-stone-300/80 font-medium"
					: "text-stone-600 hover:text-stone-900 hover:bg-stone-200/50",
				disabled && "opacity-50 cursor-not-allowed",
				className,
			)}
		>
			{icon && <span className="shrink-0">{icon}</span>}
			<span>{children}</span>
		</button>
	);
};

export interface TabsContentProps {
	value: string;
	className?: string;
	children: React.ReactNode;
}

export const TabsContent: React.FC<TabsContentProps> = ({
	value,
	className,
	children,
}) => {
	const context = useContext(TabsContext);
	if (!context) throw new Error("TabsContent must be used within Tabs");

	if (context.value !== value) return null;

	return (
		<div
			role="tabpanel"
			className={cn("animate-fadeIn outline-none", className)}
		>
			{children}
		</div>
	);
};
