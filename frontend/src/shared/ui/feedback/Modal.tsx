import React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/shared/lib";

export interface ModalProps {
	isOpen: boolean;
	onClose: () => void;
	title?: React.ReactNode;
	description?: React.ReactNode;
	children: React.ReactNode;
	footer?: React.ReactNode;
	maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl";
	className?: string;
	bodyClassName?: string;
	disableBodyScroll?: boolean;
}

const maxWidths = {
	sm: "max-w-sm",
	md: "max-w-md",
	lg: "max-w-lg",
	xl: "max-w-xl",
	"2xl": "max-w-2xl",
	"3xl": "max-w-3xl",
	"4xl": "max-w-4xl",
};

export const Modal: React.FC<ModalProps> = ({
	isOpen,
	onClose,
	title,
	description,
	children,
	footer,
	maxWidth = "2xl",
	className,
	bodyClassName,
	disableBodyScroll = false,
}) => {
	return (
		<DialogPrimitive.Root
			open={isOpen}
			onOpenChange={(open) => {
				if (!open) onClose();
			}}
		>
			<DialogPrimitive.Portal>
				<DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-stone-900/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 duration-200" />
				<DialogPrimitive.Content
					className={cn(
						"fixed left-[50%] top-[50%] z-50 translate-x-[-50%] translate-y-[-50%]",
						"w-[calc(100%-2rem)] bg-[#faf8f5] border border-stone-300/80 rounded-2xl",
						"flex flex-col shadow-warm-lg overflow-hidden focus:outline-none",
						"data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
						"data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 duration-200",
						maxWidths[maxWidth],
						className,
					)}
				>
					{/* Header */}
					{title && (
						<div className="flex items-center justify-between px-5 py-4 border-b border-stone-200/80 bg-[#f4f3ed] shrink-0">
							<div className="flex-1 min-w-0 pr-3">
								<DialogPrimitive.Title asChild>
									{typeof title === "string" ? (
										<h3 className="text-sm font-semibold text-stone-900 truncate">
											{title}
										</h3>
									) : (
										title
									)}
								</DialogPrimitive.Title>
								{description && (
									<DialogPrimitive.Description className="text-xs text-stone-500 mt-0.5">
										{description}
									</DialogPrimitive.Description>
								)}
							</div>
							<DialogPrimitive.Close asChild>
								<button
									type="button"
									onClick={onClose}
									className="text-stone-400 hover:text-stone-700 p-1.5 rounded-lg hover:bg-stone-200/60 transition-all text-sm focus:outline-none"
									aria-label="Đóng"
								>
									<X className="w-4 h-4" />
								</button>
							</DialogPrimitive.Close>
						</div>
					)}

					{/* Modal Body */}
					<div
						className={cn(
							"flex-1 min-h-0",
							disableBodyScroll
								? "overflow-hidden flex flex-col p-5"
								: "overflow-y-auto p-5",
							bodyClassName,
						)}
					>
						{children}
					</div>

					{/* Footer */}
					{footer && (
						<div className="px-5 py-3.5 border-t border-stone-200/80 bg-[#f4f3ed] flex items-center justify-end gap-3 shrink-0">
							{footer}
						</div>
					)}
				</DialogPrimitive.Content>
			</DialogPrimitive.Portal>
		</DialogPrimitive.Root>
	);
};
