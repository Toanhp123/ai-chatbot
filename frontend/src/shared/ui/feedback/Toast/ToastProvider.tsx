import React, { useState, useCallback } from "react";
import { cn } from "@/shared/lib";
import { ToastContext } from "./useToast";
import type { ToastType } from "./useToast";

interface ToastMessage {
	id: string;
	type: ToastType;
	message: string;
}

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({
	children,
}) => {
	const [toasts, setToasts] = useState<ToastMessage[]>([]);

	const toast = useCallback((message: string, type: ToastType = "info") => {
		const id = Math.random().toString(36).substring(2, 9);
		setToasts((prev) => [...prev, { id, type, message }]);
		setTimeout(() => {
			setToasts((prev) => prev.filter((t) => t.id !== id));
		}, 4000);
	}, []);

	return (
		<ToastContext.Provider value={{ toast }}>
			{children}
			<div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
				{toasts.map((t) => (
					<div
						key={t.id}
						className={cn(
							"pointer-events-auto px-4 py-3 rounded-xl shadow-warm-lg border flex items-center space-x-3 text-xs font-medium backdrop-blur-md animate-in slide-in-from-bottom-3 duration-200 bg-[#faf8f5] text-stone-800",
							t.type === "success" &&
								"border-emerald-500/80 text-emerald-950",
							t.type === "error" &&
								"border-rose-500/80 text-rose-950",
							t.type === "warning" &&
								"border-amber-500/80 text-amber-950",
							t.type === "info" &&
								"border-stone-400 text-stone-900",
						)}
					>
						<span>
							{t.type === "success" && "✅"}
							{t.type === "error" && "❌"}
							{t.type === "warning" && "⚠️"}
							{t.type === "info" && "ℹ️"}
						</span>
						<span>{t.message}</span>
					</div>
				))}
			</div>
		</ToastContext.Provider>
	);
};
