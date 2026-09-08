import React from "react";
import { cn } from "@/shared/lib";

export interface SliderProps {
	value: number;
	onChange: (value: number) => void;
	min: number;
	max: number;
	step?: number;
	label?: string;
	valueDisplay?: React.ReactNode;
	disabled?: boolean;
	description?: string;
	className?: string;
}

export const Slider: React.FC<SliderProps> = ({
	value,
	onChange,
	min,
	max,
	step = 1,
	label,
	valueDisplay,
	disabled = false,
	description,
	className,
}) => {
	return (
		<div className={cn("space-y-1.5", className)}>
			<div className="flex items-center justify-between text-xs">
				{label && (
					<label className="font-medium text-stone-700 select-none">
						{label}
					</label>
				)}
				<span className="font-mono text-amber-800 font-semibold text-[11px] px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200/80">
					{valueDisplay ?? value}
				</span>
			</div>

			<input
				type="range"
				min={min}
				max={max}
				step={step}
				value={value}
				disabled={disabled}
				onChange={(e) => onChange(Number(e.target.value))}
				className="w-full h-1.5 bg-stone-200 rounded-lg appearance-none cursor-pointer accent-amber-600 focus:outline-none focus:ring-1 focus:ring-amber-500 disabled:opacity-50 disabled:cursor-not-allowed"
			/>

			<div className="flex items-center justify-between text-[10px] text-stone-400 font-mono select-none">
				<span>{min}</span>
				{description && (
					<span className="text-stone-500 font-sans italic">
						{description}
					</span>
				)}
				<span>{max}</span>
			</div>
		</div>
	);
};
