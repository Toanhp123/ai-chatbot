import React from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/shared/lib";

export interface SearchInputProps extends Omit<
	React.InputHTMLAttributes<HTMLInputElement>,
	"onChange"
> {
	value: string;
	onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
	onValueChange?: (value: string) => void;
	onClear?: () => void;
	wrapperClassName?: string;
}

export const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
	(
		{
			value,
			onChange,
			onValueChange,
			onClear,
			placeholder = "Tìm kiếm...",
			className,
			wrapperClassName,
			disabled,
			...props
		},
		ref,
	) => {
		const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
			onChange?.(e);
			onValueChange?.(e.target.value);
		};

		const handleClear = () => {
			if (onClear) {
				onClear();
			} else {
				onValueChange?.("");
			}
		};

		return (
			<div className={cn("relative flex items-center", wrapperClassName)}>
				<Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none" />
				<input
					ref={ref}
					type="text"
					value={value}
					onChange={handleChange}
					placeholder={placeholder}
					disabled={disabled}
					className={cn(
						"w-full pl-8 pr-7 py-1.5 bg-[#f4f3ed] border border-stone-300/80 rounded-xl text-xs text-stone-900 focus:bg-[#faf8f5] outline-none focus:outline-none focus:border-amber-600 focus:ring-1 focus:ring-amber-500/20 transition-colors font-mono placeholder:text-stone-400",
						disabled && "opacity-50 cursor-not-allowed",
						className,
					)}
					{...props}
				/>
				{Boolean(value) && !disabled && (
					<button
						type="button"
						onClick={handleClear}
						className="absolute right-2 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600 p-0.5 rounded-full transition-colors"
						title="Xóa tìm kiếm"
						aria-label="Xóa tìm kiếm"
					>
						<X className="w-3 h-3" />
					</button>
				)}
			</div>
		);
	},
);

SearchInput.displayName = "SearchInput";
