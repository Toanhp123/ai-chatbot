import React from "react";
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import { MoreVertical, MoreHorizontal } from "lucide-react";
import { cn } from "@/shared/lib";

// --- Radix Primitives ---

export const DropdownMenu = DropdownMenuPrimitive.Root;
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
export const DropdownMenuGroup = DropdownMenuPrimitive.Group;
export const DropdownMenuPortal = DropdownMenuPrimitive.Portal;
export const DropdownMenuSub = DropdownMenuPrimitive.Sub;
export const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup;

export const DropdownMenuContent = React.forwardRef<
	React.ElementRef<typeof DropdownMenuPrimitive.Content>,
	React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
	<DropdownMenuPrimitive.Portal>
		<DropdownMenuPrimitive.Content
			ref={ref}
			sideOffset={sideOffset}
			className={cn(
				"z-50 min-w-[170px] overflow-hidden rounded-xl border border-stone-300/80 bg-[#faf8f5] p-1 text-xs text-stone-700 shadow-warm-lg focus:outline-none",
				"data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 duration-150",
				className,
			)}
			{...props}
		/>
	</DropdownMenuPrimitive.Portal>
));
DropdownMenuContent.displayName = DropdownMenuPrimitive.Content.displayName;

export const DropdownMenuItem = React.forwardRef<
	React.ElementRef<typeof DropdownMenuPrimitive.Item>,
	React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item> & {
		inset?: boolean;
		variant?: "default" | "danger";
	}
>(({ className, inset, variant = "default", ...props }, ref) => (
	<DropdownMenuPrimitive.Item
		ref={ref}
		className={cn(
			"relative flex cursor-pointer select-none items-center rounded-lg px-2.5 py-1.5 text-xs font-medium outline-none transition-colors",
			"focus:outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-40",
			variant === "danger"
				? "text-rose-600 focus:bg-rose-50 focus:text-rose-700 hover:bg-rose-50 hover:text-rose-700"
				: "text-stone-700 focus:bg-[#ebe8df] focus:text-stone-900 hover:bg-[#ebe8df] hover:text-stone-900",
			inset && "pl-8",
			className,
		)}
		{...props}
	/>
));
DropdownMenuItem.displayName = DropdownMenuPrimitive.Item.displayName;

export const DropdownMenuSeparator = React.forwardRef<
	React.ElementRef<typeof DropdownMenuPrimitive.Separator>,
	React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Separator>
>(({ className, ...props }, ref) => (
	<DropdownMenuPrimitive.Separator
		ref={ref}
		className={cn("-mx-1 my-1 h-px bg-stone-200/80", className)}
		{...props}
	/>
));
DropdownMenuSeparator.displayName = DropdownMenuPrimitive.Separator.displayName;

export const DropdownMenuLabel = React.forwardRef<
	React.ElementRef<typeof DropdownMenuPrimitive.Label>,
	React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Label> & {
		inset?: boolean;
	}
>(({ className, inset, ...props }, ref) => (
	<DropdownMenuPrimitive.Label
		ref={ref}
		className={cn(
			"px-2.5 py-1.5 text-[11px] font-semibold text-stone-500 font-mono",
			inset && "pl-8",
			className,
		)}
		{...props}
	/>
));
DropdownMenuLabel.displayName = DropdownMenuPrimitive.Label.displayName;

// --- High-Level Convenience ActionMenu Component ---

export interface ActionMenuItem {
	key?: string;
	label: React.ReactNode;
	icon?: React.ReactNode;
	onClick?: () => void;
	href?: string;
	download?: boolean | string;
	disabled?: boolean;
	variant?: "default" | "danger";
	separatorBefore?: boolean;
}

export interface ActionMenuProps {
	items: ActionMenuItem[];
	trigger?: React.ReactNode;
	orientation?: "horizontal" | "vertical";
	align?: "start" | "center" | "end";
	className?: string;
	triggerClassName?: string;
}

export const ActionMenu: React.FC<ActionMenuProps> = ({
	items,
	trigger,
	orientation = "vertical",
	align = "end",
	className,
	triggerClassName,
}) => {
	const defaultTrigger = (
		<button
			type="button"
			className={cn(
				"h-7 w-7 rounded-xl flex items-center justify-center text-stone-500 hover:text-stone-900 bg-[#faf8f5] hover:bg-[#ebe8df] border border-stone-300/80 transition-all shadow-warm-xs focus:outline-none focus:ring-1 focus:ring-amber-500/30 data-[state=open]:bg-[#e8e5db] data-[state=open]:text-stone-900",
				triggerClassName,
			)}
			aria-label="Thao tác khác"
		>
			{orientation === "vertical" ? (
				<MoreVertical className="w-3.5 h-3.5" />
			) : (
				<MoreHorizontal className="w-3.5 h-3.5" />
			)}
		</button>
	);

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				{trigger || defaultTrigger}
			</DropdownMenuTrigger>
			<DropdownMenuContent align={align} className={className}>
				{items.map((item, idx) => (
					<React.Fragment key={item.key || idx}>
						{item.separatorBefore && <DropdownMenuSeparator />}
						<DropdownMenuItem
							variant={item.variant}
							disabled={item.disabled}
							onClick={item.onClick}
							asChild={Boolean(item.href)}
						>
							{item.href ? (
								<a
									href={item.href}
									download={item.download}
									className="flex items-center w-full"
								>
									{item.icon && (
										<span className="mr-2 shrink-0">
											{item.icon}
										</span>
									)}
									<span>{item.label}</span>
								</a>
							) : (
								<div className="flex items-center w-full">
									{item.icon && (
										<span className="mr-2 shrink-0">
											{item.icon}
										</span>
									)}
									<span>{item.label}</span>
								</div>
							)}
						</DropdownMenuItem>
					</React.Fragment>
				))}
			</DropdownMenuContent>
		</DropdownMenu>
	);
};
