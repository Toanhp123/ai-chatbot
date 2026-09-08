import React from "react";
import { Sparkles, Activity, Cpu, Binary, FileCode } from "lucide-react";
import { Badge } from "@/shared/ui";
import { cn } from "@/shared/lib";

export type TabId = "playground" | "training" | "diagnostics" | "explorer";

export interface HeaderWidgetProps {
	activeTab: TabId;
	onTabChange: (tab: TabId) => void;
	isTraining: boolean;
	activeCheckpoint: string;
	onOpenConfig?: () => void;
}

export const HeaderWidget: React.FC<HeaderWidgetProps> = ({
	activeTab,
	onTabChange,
	isTraining,
	activeCheckpoint,
	onOpenConfig,
}) => {
	const tabs: {
		id: TabId;
		label: string;
		icon: (isActive: boolean) => React.ReactNode;
	}[] = [
		{
			id: "playground",
			label: "Trò Chuyện & Làm Việc",
			icon: (isActive) => (
				<Sparkles
					className={cn(
						"w-3.5 h-3.5 transition-colors",
						isActive ? "text-amber-600" : "text-stone-800",
					)}
				/>
			),
		},
		{
			id: "training",
			label: "Huấn Luyện",
			icon: (isActive) => (
				<div className="flex items-center gap-1.5">
					<Activity
						className={cn(
							"w-3.5 h-3.5 transition-colors",
							isActive ? "text-amber-600" : "text-stone-800",
						)}
					/>
					{isTraining && (
						<span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
					)}
				</div>
			),
		},
		{
			id: "diagnostics",
			label: "Phần Cứng & VRAM",
			icon: (isActive) => (
				<Cpu
					className={cn(
						"w-3.5 h-3.5 transition-colors",
						isActive ? "text-amber-600" : "text-stone-800",
					)}
				/>
			),
		},
		{
			id: "explorer",
			label: "Tokenizer & Data",
			icon: (isActive) => (
				<Binary
					className={cn(
						"w-3.5 h-3.5 transition-colors",
						isActive ? "text-amber-600" : "text-stone-800",
					)}
				/>
			),
		},
	];

	return (
		<header className="sticky top-0 z-40 bg-[#faf8f5]/90 backdrop-blur-xl border-b border-stone-300/80 px-4 sm:px-8 py-3.5 shadow-warm-sm">
			<div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
				{/* Brand */}
				<div className="flex items-center space-x-3 select-none">
					<div className="w-9 h-9 rounded-xl bg-amber-600 flex items-center justify-center shadow-warm-sm text-white font-bold">
						<span className="text-base">🏛️</span>
					</div>
					<div>
						<div className="flex items-center space-x-2">
							<span className="font-bold text-base tracking-tight text-stone-900 font-sans">
								AI Studio
							</span>
							<Badge
								variant="brand"
								className="font-sans font-semibold"
							>
								FSD v2.1
							</Badge>
						</div>
						<p className="text-[11px] text-stone-500">
							Modular Monolith AI Training & Inference Engine
						</p>
					</div>
				</div>

				{/* Tab Navigation */}
				<nav className="flex space-x-1 bg-[#ebe8df] p-1 rounded-xl border border-stone-300/80 shadow-inner">
					{tabs.map((tab) => {
						const isActive = activeTab === tab.id;
						return (
							<button
								key={tab.id}
								type="button"
								onClick={() => onTabChange(tab.id)}
								className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1.5 select-none ${
									isActive
										? "bg-[#faf8f5] text-stone-900 shadow-warm-sm border border-stone-300/80 font-semibold"
										: "text-stone-600 hover:text-stone-900 hover:bg-[#f4f3ed]"
								}`}
							>
								{tab.icon(isActive)}
								<span>{tab.label}</span>
							</button>
						);
					})}
				</nav>

				{/* Right Actions: Model Indicator & Config Editor */}
				<div className="flex items-center space-x-2">
					{onOpenConfig && (
						<button
							type="button"
							onClick={onOpenConfig}
							className="flex items-center space-x-1.5 text-xs bg-[#faf8f5] hover:bg-[#f4f3ed] text-stone-700 hover:text-stone-900 border border-stone-300/80 px-3 py-1.5 rounded-xl transition-all shadow-warm-sm"
							title="Xem và chỉnh sửa cấu hình YAML"
						>
							<FileCode className="w-3.5 h-3.5 text-amber-600" />
							<span>Cấu hình</span>
						</button>
					)}

					<div className="hidden sm:flex items-center space-x-2 text-xs bg-[#faf8f5] border border-stone-300/80 px-3 py-1.5 rounded-xl">
						<span className="text-stone-500">Mô hình:</span>
						<span className="font-mono text-emerald-700 font-medium truncate max-w-[160px]">
							{activeCheckpoint
								? activeCheckpoint.split("/").pop()
								: "Chưa nạp"}
						</span>
					</div>
				</div>
			</div>
		</header>
	);
};
