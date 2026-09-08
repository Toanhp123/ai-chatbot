import React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/shared/lib";

export interface DrawerProps {
	isOpen: boolean;
	onClose: () => void;
	title: string;
	subtitle?: string;
	children: React.ReactNode;
	className?: string;
}

export const Drawer: React.FC<DrawerProps> = ({
	isOpen,
	onClose,
	title,
	subtitle,
	children,
	className,
}) => {
	return (
		<DialogPrimitive.Root
			open={isOpen}
			onOpenChange={(open) => {
				if (!open) onClose();
			}}
		>
			<DialogPrimitive.Portal>
				{/* Backdrop with smooth fade in / fade out */}
				<DialogPrimitive.Overlay className="drawer-overlay fixed inset-0 z-50 bg-stone-900/30 backdrop-blur-[2px]" />

				{/* Slide-over panel with smooth slide in from right / slide out to right */}
				<DialogPrimitive.Content
					className={cn(
						"drawer-content fixed inset-y-0 right-0 z-50 w-screen max-w-md bg-[#faf8f5] border-l border-stone-300/80 shadow-warm-lg flex flex-col justify-between overflow-hidden outline-none",
						className,
					)}
				>
					{/* Header */}
					<div className="p-4 sm:p-5 border-b border-stone-200/70 flex items-start justify-between gap-3 bg-[#f4f3ed] shrink-0 select-none">
						<div>
							<DialogPrimitive.Title className="text-sm font-bold text-stone-900 tracking-tight flex items-center gap-2">
								<span className="w-2 h-2 rounded-full bg-amber-600" />
								{title}
							</DialogPrimitive.Title>
							{subtitle ? (
								<DialogPrimitive.Description className="text-xs text-stone-500 mt-0.5 font-normal">
									{subtitle}
								</DialogPrimitive.Description>
							) : (
								<DialogPrimitive.Description className="sr-only">
									{title}
								</DialogPrimitive.Description>
							)}
						</div>
						<div className="flex items-center gap-1.5">
							<kbd className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-stone-200/70 text-[10px] font-mono text-stone-500">
								Esc
							</kbd>
							<DialogPrimitive.Close asChild>
								<button
									type="button"
									className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-200/60 transition-colors"
									title="Đóng bảng tham số (Esc)"
								>
									<X className="w-4 h-4" />
								</button>
							</DialogPrimitive.Close>
						</div>
					</div>

					{/* Body */}
					<div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-5">
						{children}
					</div>
				</DialogPrimitive.Content>
			</DialogPrimitive.Portal>
		</DialogPrimitive.Root>
	);
};
