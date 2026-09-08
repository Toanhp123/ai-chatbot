import React from "react";
import { Badge, Button, StatCard } from "@/shared/ui";
import type {
	TrainingStatus,
	TrainingTerminationReason,
	PreflightMemoryInfo,
} from "@/entities/training";
import {
	Activity,
	Play,
	Square,
	ShieldCheck,
	TrendingDown,
	CheckCircle2,
	AlertTriangle,
	Zap,
	Loader2,
	RotateCcw,
} from "lucide-react";

export interface TrainingMetricsRibbonWidgetProps {
	status: TrainingStatus;
	terminationReason: TrainingTerminationReason;
	errorMessage: string | null;
	currentStep: number;
	maxIters: number;
	currentLoss: number | null;
	currentValLoss: number | null;
	currentLr: number | null;
	preflightInfo: PreflightMemoryInfo | null;
	isStarting: boolean;
	isStartDisabled?: boolean;
	configLoadError?: string | null;
	isStopping?: boolean;
	onStart: () => void;
	onStop: () => void;
	onClear?: () => void;
	resumeTarget?: {
		filename: string;
		path: string;
		step?: number;
		val_loss?: number;
	} | null;
	onCancelResume?: () => void;
}

export const TrainingMetricsRibbonWidget: React.FC<
	TrainingMetricsRibbonWidgetProps
> = ({
	status,
	terminationReason,
	errorMessage,
	currentStep,
	maxIters,
	currentLoss,
	currentValLoss,
	currentLr,
	preflightInfo,
	isStarting,
	isStartDisabled = false,
	configLoadError = null,
	isStopping,
	onStart,
	onStop,
	onClear,
	resumeTarget,
	onCancelResume,
}) => {
	const isCurrentlyStopping = status === "STOPPING" || Boolean(isStopping);
	const isCurrentlyActive =
		!isCurrentlyStopping &&
		(status === "RUNNING" || status === "STARTING" || isStarting);
	const hasPreviousMetrics =
		currentStep > 0 ||
		currentLoss !== null ||
		currentValLoss !== null ||
		status === "STOPPED" ||
		status === "COMPLETED";

	const getStatusBadge = (st: string) => {
		switch (st) {
			case "STARTING":
				return (
					<Badge
						variant="warning"
						className="px-3 py-1 font-bold text-xs flex items-center"
					>
						<Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />{" "}
						KHỞI TẠO HỆ THỐNG
					</Badge>
				);
			case "RUNNING":
				return (
					<Badge
						variant="success"
						className="px-3 py-1 font-bold text-xs animate-pulse flex items-center"
					>
						<Activity className="w-3.5 h-3.5 mr-1" /> ĐANG HUẤN
						LUYỆN
					</Badge>
				);
			case "STOPPING":
				return (
					<Badge
						variant="warning"
						className="px-3 py-1 font-bold text-xs flex items-center"
					>
						<Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />{" "}
						ĐANG DỪNG TIẾN TRÌNH...
					</Badge>
				);
			case "STOPPED":
				return (
					<Badge
						variant="neutral"
						className="px-3 py-1 font-bold text-xs flex items-center"
					>
						<Square className="w-3.5 h-3.5 mr-1" /> ĐÃ DỪNG
					</Badge>
				);
			case "COMPLETED":
				return (
					<Badge
						variant="info"
						className="px-3 py-1 font-bold text-xs flex items-center"
					>
						<CheckCircle2 className="w-3.5 h-3.5 mr-1" /> HOÀN THÀNH
					</Badge>
				);
			case "ERROR":
				return (
					<Badge
						variant="danger"
						className="px-3 py-1 font-bold text-xs flex items-center"
					>
						<AlertTriangle className="w-3.5 h-3.5 mr-1" /> THẤT BẠI
					</Badge>
				);
			default:
				return (
					<Badge
						variant="neutral"
						className="px-3 py-1 font-bold text-xs flex items-center"
					>
						SẴN SÀNG (IDLE)
					</Badge>
				);
		}
	};

	const progressPercent =
		maxIters > 0
			? Math.min(Math.round((currentStep / maxIters) * 100), 100)
			: 0;

	return (
		<div className="space-y-4">
			{/* Top Status & Metrics Ribbon */}
			<div className="p-4 rounded-2xl bg-[#faf8f5] border border-stone-300/80 shadow-warm-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
				<div className="flex items-center gap-3">
					<div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200/80 text-amber-700">
						<Activity className="w-6 h-6" />
					</div>
					<div>
						<div className="flex items-center gap-2.5">
							<h2 className="text-base font-bold text-stone-900">
								Trung Tâm Huấn Luyện AI Studio
							</h2>
							{getStatusBadge(status)}
						</div>
						<p className="text-xs text-stone-500 mt-0.5">
							Bộ điều khiển tiến trình huấn luyện, hội tụ hàm Loss
							và xuất sinh mẫu tự động
						</p>
					</div>
				</div>

				{/* Action Controls with Smooth, Fixed-width Transition */}
				<div className="flex items-center gap-2 sm:gap-3">
					{!isCurrentlyActive && hasPreviousMetrics && onClear && (
						<Button
							size="md"
							variant="outline"
							onClick={onClear}
							className="font-semibold shadow-warm-sm justify-center text-stone-700 hover:text-stone-900 border-stone-300/90 hover:bg-[#faf8f5]"
							title="Làm mới bảng số liệu và biểu đồ huấn luyện"
						>
							<RotateCcw className="w-4 h-4 mr-1.5" />
							Làm Mới
						</Button>
					)}

					{isCurrentlyStopping ? (
						<Button
							size="md"
							variant="danger"
							disabled
							className="font-semibold shadow-warm-sm min-w-[185px] justify-center opacity-70 cursor-not-allowed"
						>
							<Loader2 className="w-4 h-4 mr-2 animate-spin" />
							Đang Dừng Lại...
						</Button>
					) : isCurrentlyActive ? (
						<Button
							size="md"
							variant="danger"
							onClick={onStop}
							className="font-semibold shadow-warm-sm min-w-[185px] justify-center transition-all duration-200 hover:bg-rose-100"
						>
							{status === "STARTING" || isStarting ? (
								<>
									<Loader2 className="w-4 h-4 mr-2 animate-spin" />
									Dừng (Đang Khởi Tạo)
								</>
							) : (
								<>
									<Square className="w-4 h-4 mr-2 fill-current" />
									Dừng Huấn Luyện
								</>
							)}
						</Button>
					) : resumeTarget ? (
						<Button
							size="md"
							variant="primary"
							onClick={onStart}
							disabled={isStartDisabled}
							className="font-semibold shadow-warm-sm min-w-[210px] justify-center transition-all duration-200 bg-amber-700 hover:bg-amber-800 text-amber-50"
							title={`Tiếp tục huấn luyện từ ${resumeTarget.filename} (bước ${(resumeTarget.step ?? 0) + 1})`}
						>
							<RotateCcw className="w-4 h-4 mr-2" />
							Tiếp Tục Huấn Luyện (Resume)
						</Button>
					) : (
						<Button
							size="md"
							variant="primary"
							onClick={onStart}
							disabled={isStartDisabled}
							className="font-semibold shadow-warm-sm min-w-[185px] justify-center transition-all duration-200"
						>
							<Play className="w-4 h-4 mr-2 fill-current" />
							Khởi Chạy Huấn Luyện
						</Button>
					)}
				</div>
			</div>

			{configLoadError && (
				<div className="p-3 px-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 shadow-warm-xs">
					<strong className="font-semibold">Không thể nạp cấu hình training canonical:</strong>{" "}
					<span className="font-mono break-words">{configLoadError}</span>
					<span> — nút Start được khóa để tránh chạy bằng giá trị fallback hiển thị sai.</span>
				</div>
			)}

			{status === "ERROR" && errorMessage && (
				<div className="p-3 px-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 shadow-warm-xs">
					<strong className="font-semibold">Lỗi huấn luyện:</strong>{" "}
					<span className="font-mono break-words">{errorMessage}</span>
				</div>
			)}

			{status === "COMPLETED" && terminationReason === "EARLY_STOPPED" && (
				<div className="p-3 px-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 shadow-warm-xs">
					Huấn luyện đã hoàn tất bằng Early Stopping; metrics cuối được giữ lại để đánh giá.
				</div>
			)}

			{/* Resume Notification Banner */}
			{!isCurrentlyActive && resumeTarget && (
				<div className="p-3 px-4 rounded-xl bg-amber-50/90 border border-amber-300/90 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-warm-xs animate-in fade-in duration-200">
					<div className="flex items-center gap-2.5 flex-wrap min-w-0">
						<div className="p-1.5 rounded-lg bg-amber-100 text-amber-800 border border-amber-200 shrink-0">
							<RotateCcw className="w-4 h-4" />
						</div>
						<div className="flex items-center gap-1.5 flex-wrap">
							<span className="font-bold text-amber-950">
								Chế độ Resume:
							</span>
							<span className="text-amber-800">
								Sẵn sàng tiếp tục từ
							</span>
							<code className="font-mono bg-white border border-amber-200/90 px-2 py-0.5 rounded text-amber-900 font-semibold text-[11px]">
								{resumeTarget.filename}
							</code>
							{resumeTarget.step !== undefined &&
								resumeTarget.step > 0 && (
									<span className="text-amber-800 font-medium">
										(bước{" "}
										{resumeTarget.step.toLocaleString()})
									</span>
								)}
							{resumeTarget.val_loss !== undefined &&
								resumeTarget.val_loss > 0 && (
									<span className="text-amber-700">
										• Val Loss:{" "}
										<strong className="font-mono">
											{resumeTarget.val_loss.toFixed(4)}
										</strong>
									</span>
								)}
						</div>
					</div>
					{onCancelResume && (
						<button
							type="button"
							onClick={onCancelResume}
							className="shrink-0 inline-flex items-center justify-center gap-1 text-[11px] font-medium text-amber-800 hover:text-amber-950 bg-white/80 hover:bg-white px-2.5 py-1 rounded-lg border border-amber-300/80 transition-colors shadow-warm-xs"
							title="Hủy tiếp tục và quay về huấn luyện mới từ đầu"
						>
							<span>✕ Hủy Resume (Huấn luyện từ đầu)</span>
						</button>
					)}
				</div>
			)}

			{/* Progress & Live Metrics Bar - Standardized using Reusable StatCard Component */}
			<div className="grid grid-cols-2 md:grid-cols-5 gap-3">
				{/* Step Progress */}
				<StatCard
					label="Tiến độ Bước (Step)"
					value={
						<div className="flex items-baseline gap-1">
							<span>{currentStep.toLocaleString()}</span>
							<span className="text-xs text-stone-400 font-normal">
								/ {maxIters.toLocaleString()}
							</span>
						</div>
					}
					icon={
						<span className="text-amber-700 font-bold text-xs">
							{progressPercent}%
						</span>
					}
					subtext={
						<div className="w-full h-1.5 bg-stone-200/80 rounded-full mt-1.5 overflow-hidden">
							<div
								style={{ width: `${progressPercent}%` }}
								className="h-full bg-amber-600 rounded-full transition-all duration-300"
							/>
						</div>
					}
				/>

				{/* Train Loss */}
				<StatCard
					icon={<TrendingDown className="w-3.5 h-3.5" />}
					label="Train Loss"
					value={currentLoss !== null ? currentLoss.toFixed(4) : "--"}
					subtext="Mỗi step cập nhật"
					variant="amber"
				/>

				{/* Val Loss */}
				<StatCard
					icon={<CheckCircle2 className="w-3.5 h-3.5" />}
					label="Validation Loss"
					value={
						currentValLoss !== null
							? currentValLoss.toFixed(4)
							: "--"
					}
					subtext="Đánh giá theo chu kỳ"
					variant="emerald"
				/>

				{/* Learning Rate */}
				<StatCard
					icon={<Zap className="w-3.5 h-3.5" />}
					label="Learning Rate"
					value={
						currentLr !== null ? currentLr.toExponential(2) : "--"
					}
					subtext="Cosine Warmup Decay"
					variant="amber"
				/>

				{/* Preflight VRAM Status */}
				<StatCard
					icon={<ShieldCheck className="w-3.5 h-3.5" />}
					label="Pre-flight Check"
					value={
						<Badge
							variant={
								preflightInfo?.feasible ? "success" : "warning"
							}
							className="text-[10px] font-semibold"
						>
							{preflightInfo?.feasible
								? "KHẢ THI VRAM"
								: "CẢNH BÁO OOM"}
						</Badge>
					}
					subtext={`Đỉnh VRAM: ${preflightInfo?.estimated_gb?.toFixed(2) || "0.00"} GB`}
					variant="sky"
				/>
			</div>
		</div>
	);
};
