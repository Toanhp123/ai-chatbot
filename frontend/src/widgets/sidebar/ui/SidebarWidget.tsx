import React from "react";
import {
	Sparkles,
	Activity,
	Cpu,
	Binary,
	Plus,
	FileCode,
	PanelLeftClose,
	PanelLeft,
	Box,
} from "lucide-react";
import { Badge } from "@/shared/ui";
import { cn } from "@/shared/lib";
import type { TabId } from "../../header";

export interface SidebarWidgetProps {
	activeTab: TabId;
	onTabChange: (tab: TabId) => void;
	isTraining?: boolean;
	activeCheckpoint?: string;
	onOpenConfig?: () => void;
	onNewSession?: () => void;
	isCollapsed?: boolean;
	onToggleCollapse?: () => void;
}

export const SidebarWidget: React.FC<SidebarWidgetProps> = ({
	activeTab,
	onTabChange,
	isTraining = false,
	activeCheckpoint = "",
	onOpenConfig,
	onNewSession,
	isCollapsed = false,
	onToggleCollapse,
}) => {
	const navItems: {
		id: TabId;
		label: string;
		desc: string;
		icon: (isActive: boolean) => React.ReactNode;
	}[] = [
		{
			id: "playground",
			label: "Trò Chuyện & Làm Việc",
			desc: "Trợ lý AI thông minh & đối thoại",
			icon: (isActive: boolean) => (
				<Sparkles
					className={cn(
						"w-[18px] h-[18px] transition-colors duration-200",
						isActive ? "text-amber-600" : "text-stone-800",
					)}
				/>
			),
		},
		{
			id: "training",
			label: "Huấn Luyện AI",
			desc: "Tiến độ epoch & loss curve",
			icon: (isActive: boolean) => (
				<div className="relative flex items-center justify-center">
					<Activity
						className={cn(
							"w-[18px] h-[18px] transition-colors duration-200",
							isActive ? "text-amber-600" : "text-stone-800",
						)}
					/>
					{isTraining && (
						<span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
					)}
				</div>
			),
		},
		{
			id: "diagnostics",
			label: "Phần Cứng & VRAM",
			desc: "Khảo sát GPU & Quality Gates",
			icon: (isActive: boolean) => (
				<Cpu
					className={cn(
						"w-[18px] h-[18px] transition-colors duration-200",
						isActive ? "text-amber-600" : "text-stone-800",
					)}
				/>
			),
		},
		{
			id: "explorer",
			label: "Tokenizer & Dữ Liệu",
			desc: "Tập dữ liệu & Vocab",
			icon: (isActive: boolean) => (
				<Binary
					className={cn(
						"w-[18px] h-[18px] transition-colors duration-200",
						isActive ? "text-amber-600" : "text-stone-800",
					)}
				/>
			),
		},
	];

	return (
		<aside
			className={cn(
				"border-r border-stone-200/80 bg-[#faf8f5] flex flex-col justify-between shrink-0 transition-all duration-300 select-none",
				isCollapsed ? "w-16" : "w-64",
			)}
		>
			{/* Top: Branding & New Chat CTA */}
			<div className="p-3 border-b border-stone-200/80 space-y-3">
				{/* Brand Logo & Studio Name */}
				<div
					className={cn(
						"flex items-center",
						isCollapsed
							? "justify-center"
							: "justify-between px-1 pt-1",
					)}
				>
					{!isCollapsed && (
						<div className="flex items-center gap-2.5 min-w-0">
							<div className="w-8 h-8 rounded-xl bg-amber-600 text-white flex items-center justify-center shadow-warm-sm shrink-0 font-bold text-sm">
								✨
							</div>
							<div className="truncate">
								<h2 className="text-sm font-bold text-stone-900 tracking-tight flex items-center gap-1.5 truncate">
									AI Studio
									<span className="text-[9px] font-mono font-medium px-1.5 py-0.2 rounded bg-amber-100/80 text-amber-800 border border-amber-200/60">
										Aura AI
									</span>
								</h2>
								<p className="text-[10px] text-stone-500 truncate">
									PyTorch SDPA • FSD v2.1
								</p>
							</div>
						</div>
					)}

					{/* Collapse Button */}
					{onToggleCollapse && (
						<button
							type="button"
							onClick={onToggleCollapse}
							className={cn(
								"rounded-xl text-stone-500 hover:text-stone-900 hover:bg-stone-200/60 transition-colors flex items-center justify-center",
								isCollapsed ? "w-10 h-10 mx-auto" : "p-1.5",
							)}
							title={
								isCollapsed
									? "Mở rộng thanh bên"
									: "Thu gọn thanh bên"
							}
						>
							{isCollapsed ? (
								<PanelLeft className="w-4 h-4" />
							) : (
								<PanelLeftClose className="w-4 h-4" />
							)}
						</button>
					)}
				</div>

				{/* "+ Đoạn chat mới" (Claude-style New Chat button) */}
				{isCollapsed ? (
					<button
						type="button"
						onClick={() => {
							onTabChange("playground");
							onNewSession?.();
						}}
						className="w-10 h-10 mx-auto rounded-xl bg-amber-50 hover:bg-amber-100 border border-amber-200/80 text-amber-700 shadow-warm-sm flex items-center justify-center transition-all"
						title="Bắt đầu đoạn chat mới (Ctrl+K)"
					>
						<Plus className="w-[18px] h-[18px]" />
					</button>
				) : (
					<button
						type="button"
						onClick={() => {
							onTabChange("playground");
							onNewSession?.();
						}}
						className="w-full flex items-center gap-2 rounded-xl bg-[#f4f3ed] hover:bg-[#faf8f5] border border-stone-300/80 text-stone-800 shadow-warm-sm px-2.5 py-2 text-xs font-semibold transition-all group"
						title="Bắt đầu đoạn chat mới (Ctrl+K)"
					>
						<div className="w-5 h-5 rounded-lg bg-amber-100/70 group-hover:bg-amber-100 text-amber-800 flex items-center justify-center transition-colors shrink-0">
							<Plus className="w-3.5 h-3.5" />
						</div>
						<span className="font-semibold text-xs text-stone-800 flex-1 text-left whitespace-nowrap">
							Đoạn chat mới
						</span>
						<kbd className="inline-block px-1 py-0.5 rounded bg-stone-200/70 border border-stone-300/80 text-[9px] font-mono text-stone-500 shrink-0">
							Ctrl+K
						</kbd>
					</button>
				)}
			</div>

			{/* Main Navigation List */}
			<div
				className={cn(
					"flex-1 space-y-1.5 overflow-y-auto",
					isCollapsed ? "px-2 py-2" : "px-3 py-2",
				)}
			>
				{!isCollapsed && (
					<div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-stone-500">
						Chức Năng Hệ Thống
					</div>
				)}

				<nav
					className={cn(
						isCollapsed
							? "space-y-2 flex flex-col items-center"
							: "space-y-1",
					)}
				>
					{navItems.map((item) => {
						const isActive = activeTab === item.id;
						return (
							<button
								key={item.id}
								type="button"
								onClick={() => onTabChange(item.id)}
								className={cn(
									"transition-all duration-150 flex items-center select-none",
									isCollapsed
										? "w-10 h-10 mx-auto justify-center rounded-xl hover:bg-stone-200/50"
										: "w-full px-3 py-2.5 rounded-xl gap-3 text-left relative",
									isActive
										? isCollapsed
											? "text-amber-600"
											: "bg-[#faf8f5] text-stone-900 shadow-warm-sm border border-stone-300/80 font-medium before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1 before:rounded-r-full before:bg-amber-600"
										: isCollapsed
											? "text-stone-800 hover:text-stone-950"
											: "text-stone-600 hover:text-stone-900 hover:bg-[#e2ded5]/80",
								)}
								title={
									isCollapsed
										? `${item.label}: ${item.desc}`
										: undefined
								}
							>
								<span className="shrink-0 flex items-center justify-center">
									{item.icon(isActive)}
								</span>
								{!isCollapsed && (
									<div className="truncate flex-1 min-w-0">
										<div
											className={cn(
												"text-xs font-semibold truncate transition-colors",
												isActive
													? "text-stone-900"
													: "text-stone-700 hover:text-stone-900",
											)}
										>
											{item.label}
										</div>
										<div className="text-[10px] text-stone-500 truncate mt-0.5">
											{item.desc}
										</div>
									</div>
								)}
							</button>
						);
					})}
				</nav>
			</div>

			{/* Bottom Controls / Checkpoint Status */}
			<div
				className={cn(
					"border-t border-stone-300/60 bg-[#e3e0d5]/30 space-y-2",
					isCollapsed ? "p-2 flex flex-col items-center" : "p-3",
				)}
			>
				{/* Checkpoint Indicator */}
				{!isCollapsed ? (
					<div className="p-2.5 rounded-xl bg-stone-200/50 border border-stone-300/60 shadow-xs space-y-1.5">
						<div className="flex items-center justify-between text-[10px] text-stone-500">
							<span className="flex items-center gap-1 font-medium">
								<Box className="w-3 h-3 text-amber-600" />
								Checkpoint Mô Hình
							</span>
							<Badge
								variant={activeCheckpoint ? "success" : "zinc"}
								className="text-[9px] px-1 py-0"
							>
								{activeCheckpoint ? "Sẵn sàng" : "Chưa nạp"}
							</Badge>
						</div>
						<p
							className="text-[11px] font-mono text-stone-800 truncate font-semibold"
							title={activeCheckpoint || "Chưa nạp checkpoint"}
						>
							{activeCheckpoint
								? activeCheckpoint.split("/").pop()
								: "Mặc định (Chưa chọn file)"}
						</p>
					</div>
				) : (
					<div
						className="w-10 h-10 rounded-xl flex items-center justify-center text-amber-600 hover:bg-stone-200/60 transition-colors"
						title={`Checkpoint: ${activeCheckpoint || "Chưa tải"}`}
					>
						<Box className="w-4 h-4" />
					</div>
				)}

				{/* YAML Config Button */}
				{onOpenConfig && (
					<button
						type="button"
						onClick={onOpenConfig}
						className={cn(
							"transition-all text-xs font-medium",
							isCollapsed
								? "w-10 h-10 rounded-xl flex items-center justify-center text-stone-600 hover:text-stone-900 hover:bg-stone-200/60"
								: "w-full flex items-center gap-2 rounded-xl border border-stone-300/70 hover:border-stone-400 hover:bg-stone-200/60 text-stone-600 hover:text-stone-900 px-3 py-2 shadow-xs",
						)}
						title="Chỉnh sửa cấu hình YAML"
					>
						<FileCode className="w-4 h-4 text-stone-500 shrink-0" />
						{!isCollapsed && (
							<span className="truncate">Cấu Hình YAML</span>
						)}
					</button>
				)}
			</div>
		</aside>
	);
};
