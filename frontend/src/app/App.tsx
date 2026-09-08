import { useState, useEffect, useRef, useCallback } from "react";
import type { TabId } from "@/widgets";
import { SidebarWidget, ConfigEditorModal } from "@/widgets";
import {
	PlaygroundPage,
	TrainingPage,
	DiagnosticsPage,
	ExplorerPage,
} from "@/pages";
import { useConfigEditor } from "@/features/config";
import { trainingApi } from "@/entities/training";
import { AppShell } from "@/shared/ui";
import { ToastProvider, useToast } from "./providers";

function AIStudioContent() {
	const [activeTab, setActiveTab] = useState<TabId>("playground");
	const [activeCheckpoint, setActiveCheckpoint] = useState<string>("");
	const [isTraining, setIsTraining] = useState<boolean>(false);
	const [isSidebarCollapsed, setIsSidebarCollapsed] =
		useState<boolean>(false);
	const [configRevision, setConfigRevision] = useState(0);
	const resetPlaygroundRef = useRef<(() => void) | null>(null);

	const { toast } = useToast();
	const configEditor = useConfigEditor();

	// Auto scroll to top on tab change
	useEffect(() => {
		window.scrollTo({ top: 0, left: 0, behavior: "instant" });
		const mainEl = document.querySelector("main");
		if (mainEl) {
			mainEl.scrollTo({ top: 0, left: 0, behavior: "instant" });
		}
	}, [activeTab]);

	// Poll system/training status periodically to keep status indicator up to date
	useEffect(() => {
		let isMounted = true;

		const checkTrainingStatus = async () => {
			try {
				const res = await trainingApi.getTrainingStatus();
				if (isMounted && res) {
					setIsTraining(res.status === "RUNNING");
				}
			} catch {
				// ignore
			}
		};

		checkTrainingStatus();
		const interval = setInterval(checkTrainingStatus, 4000);
		return () => {
			isMounted = false;
			clearInterval(interval);
		};
	}, []);

	const handleCheckpointLoaded = (path: string) => {
		setActiveCheckpoint(path);
		toast(`Đã nạp checkpoint: ${path.split("/").pop()}`, "success");
	};

	const handleSaveConfig = () => {
		configEditor.saveConfig(
			() => {
				setConfigRevision((revision) => revision + 1);
				toast(
					"Cấu hình YAML đã được cập nhật và xác thực an toàn.",
					"success",
				);
			},
			(err) => {
				toast(`Lỗi lưu cấu hình: ${err}`, "error");
			},
		);
	};

	const handleNewSession = useCallback(() => {
		setActiveTab("playground");
		if (resetPlaygroundRef.current) {
			resetPlaygroundRef.current();
			toast("Đã bắt đầu đoạn chat mới", "info");
		}
	}, [toast]);

	// Global shortcut: Ctrl+K / Cmd+K to start a new chat session
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
				e.preventDefault();
				handleNewSession();
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [handleNewSession]);

	return (
		<AppShell
			sidebar={
				<SidebarWidget
					activeTab={activeTab}
					onTabChange={(tab) => setActiveTab(tab)}
					isTraining={isTraining}
					activeCheckpoint={activeCheckpoint}
					onOpenConfig={() =>
						configEditor.openConfig("configs/truyen_kieu.yaml")
					}
					onNewSession={handleNewSession}
					isCollapsed={isSidebarCollapsed}
					onToggleCollapse={() =>
						setIsSidebarCollapsed(!isSidebarCollapsed)
					}
				/>
			}
			footer={
				activeTab !== "playground" ? (
					<div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-stone-500 font-mono">
						<span>
							🏛️ AI Studio • Feature-Sliced Design (FSD v2.1) •
							Nordic Warm Aesthetic
						</span>
						<span>PyTorch SDPA Native • 0ms Tab Retention</span>
					</div>
				) : undefined
			}
		>
			{/* Tab Retention Keep-Alive Viewport (0ms Instant Tab Switching, No Flicker & State Preserved) */}
			<div
				className={
					activeTab === "playground"
						? "h-full w-full block"
						: "hidden"
				}
			>
				<PlaygroundPage
					activeCheckpoint={activeCheckpoint}
					onCheckpointLoaded={handleCheckpointLoaded}
					onRegisterReset={(resetFn) => {
						resetPlaygroundRef.current = resetFn;
					}}
				/>
			</div>

			<div
				className={
					activeTab === "training"
						? "p-4 sm:p-6 pb-20 max-w-7xl mx-auto w-full block"
						: "hidden"
				}
			>
				<TrainingPage
					activeCheckpoint={activeCheckpoint}
					onCheckpointLoaded={handleCheckpointLoaded}
					configRevision={configRevision}
				/>
			</div>

			<div
				className={
					activeTab === "diagnostics"
						? "p-4 sm:p-6 pb-20 max-w-7xl mx-auto w-full block"
						: "hidden"
				}
			>
				<DiagnosticsPage />
			</div>

			<div
				className={
					activeTab === "explorer"
						? "p-4 sm:p-6 pb-20 max-w-7xl mx-auto w-full block"
						: "hidden"
				}
			>
				<ExplorerPage />
			</div>

			{/* Config Editor Modal */}
			<ConfigEditorModal
				isOpen={configEditor.isOpen}
				onClose={() => configEditor.setIsOpen(false)}
				path={configEditor.path}
				content={configEditor.content}
				setContent={configEditor.setContent}
				isLoading={configEditor.isLoading}
				isSaving={configEditor.isSaving}
				onSave={handleSaveConfig}
				onReload={() => configEditor.openConfig(configEditor.path)}
			/>
		</AppShell>
	);
}

export function App() {
	return (
		<ToastProvider>
			<AIStudioContent />
		</ToastProvider>
	);
}
