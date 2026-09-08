import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/shared/ui";
import { Button } from "@/shared/ui";
import { Badge } from "@/shared/ui";
import { useVramMatrix } from "./model/useVramMatrix";
import type { VramScenarioConfig } from "./model/useVramMatrix";
import {
	Layers,
	Sparkles,
	Zap,
	Check,
	TrendingDown,
	Gauge,
	Sliders,
	Cpu,
} from "lucide-react";

export type { VramScenarioConfig };

export interface VramMatrixWidgetProps {
	onApplyScenario?: (scenarioConfig: VramScenarioConfig) => void;
}

export const VramMatrixWidget: React.FC<VramMatrixWidgetProps> = ({
	onApplyScenario,
}) => {
	const {
		data,
		loading,
		error,
		selectedScenarioId,
		setSelectedScenarioId,
		appliedId,
		fetchScenarios,
		handleApply,
	} = useVramMatrix({ onApplyScenario });

	const getScenarioTheme = (id: string) => {
		switch (id) {
			case "fp32_baseline":
				return {
					badge: "warning",
					border: "border-amber-300 hover:border-amber-500",
					bg: "bg-amber-50/40",
					text: "text-amber-800",
					icon: Gauge,
				};
			case "amp_mixed":
				return {
					badge: "info",
					border: "border-amber-500/60 hover:border-amber-600 ring-1 ring-amber-500/20",
					bg: "bg-amber-50/60",
					text: "text-amber-900",
					icon: Sparkles,
				};
			case "amp_grad_checkpointing":
				return {
					badge: "success",
					border: "border-emerald-300 hover:border-emerald-500",
					bg: "bg-emerald-50/40",
					text: "text-emerald-800",
					icon: TrendingDown,
				};
			case "amp_8bit_optimizer":
				return {
					badge: "purple",
					border: "border-stone-300 hover:border-stone-400",
					bg: "bg-stone-50",
					text: "text-stone-800",
					icon: Zap,
				};
			default:
				return {
					badge: "neutral",
					border: "border-stone-300/80",
					bg: "bg-[#faf8f5]",
					text: "text-stone-800",
					icon: Layers,
				};
		}
	};

	const scenarios = data?.scenarios || [];
	const activeScenario =
		scenarios.find((s) => s.id === selectedScenarioId) ||
		data?.recommended ||
		scenarios[0] ||
		null;

	return (
		<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
			<CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-stone-200/80">
				<div className="flex items-center gap-3">
					<div className="p-2 rounded-lg bg-amber-50 border border-amber-200/80 text-amber-700">
						<Layers className="w-5 h-5" />
					</div>
					<div>
						<CardTitle className="text-base text-stone-900 flex items-center gap-2">
							Ma Trận Dự Toán & Tối Ưu Hóa VRAM
						</CardTitle>
						<p className="text-xs text-stone-500 mt-0.5">
							So sánh 4 kịch bản phân bổ bộ nhớ thời gian thực, tự
							động điều chỉnh siêu tham số
						</p>
					</div>
				</div>
				<Button
					size="sm"
					variant="outline"
					onClick={fetchScenarios}
					disabled={loading}
					className="h-8 border-stone-300/80 text-stone-700 shadow-warm-sm"
				>
					<Sliders
						className={`w-3.5 h-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}
					/>
					Tính toán lại
				</Button>
			</CardHeader>

			<CardContent className="pt-5 space-y-6">
				{error && (
					<div className="p-3 bg-rose-50 border border-rose-200/80 rounded-lg text-rose-700 text-xs">
						{error}
					</div>
				)}

				{/* 4 Scenario Cards Grid */}
				<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
					{scenarios.map((sc) => {
						const theme = getScenarioTheme(sc.id);
						const Icon = theme.icon;
						const isSelected = selectedScenarioId === sc.id;
						const isApplied = appliedId === sc.id;
						const isRecommended = data?.recommended?.id === sc.id;

						return (
							<div
								key={sc.id}
								onClick={() => setSelectedScenarioId(sc.id)}
								className={`cursor-pointer rounded-xl border p-4 transition-all duration-200 flex flex-col justify-between bg-[#faf8f5] ${
									isSelected
										? "border-amber-600 ring-2 ring-amber-500/30 shadow-warm-md"
										: "border-stone-300/80 hover:border-amber-500/50 shadow-warm-sm"
								}`}
							>
								<div>
									<div className="flex items-center justify-between mb-2">
										<span
											className={`p-1.5 rounded-lg bg-[#f4f3ed] border border-stone-200/80 ${theme.text}`}
										>
											<Icon className="w-4 h-4" />
										</span>
										<div className="flex items-center gap-1.5">
											{isRecommended && (
												<Badge
													variant="brand"
													className="text-[9px]"
												>
													GỢI Ý
												</Badge>
											)}
											<span className="text-[10px] uppercase font-mono tracking-wider font-semibold text-stone-500">
												{sc.precision}
											</span>
										</div>
									</div>

									<h4 className="text-sm font-semibold text-stone-900">
										{sc.name}
									</h4>
									<p className="text-[11px] text-stone-600 mb-3 line-clamp-2">
										{sc.description}
									</p>

									<div className="p-2.5 rounded-lg bg-[#f4f3ed] border border-stone-200/80 mb-3">
										<div className="text-[10px] text-stone-500">
											Đỉnh VRAM ước tính:
										</div>
										<div
											className={`text-xl font-bold font-mono ${theme.text}`}
										>
											{Math.round(sc.estimated_mb)} MB
											<span className="text-xs text-stone-500 font-normal ml-1">
												({sc.estimated_gb.toFixed(2)}{" "}
												GB)
											</span>
										</div>
									</div>

									<div className="space-y-1 text-[11px] text-stone-700">
										<div className="flex justify-between">
											<span className="text-stone-500">
												Optimizer:
											</span>
											<span className="font-mono font-medium uppercase text-stone-800">
												{sc.optimizer}
											</span>
										</div>
										<div className="flex justify-between">
											<span className="text-stone-500">
												Checkpointing:
											</span>
											<span className="font-mono font-medium text-stone-800">
												{sc.gradient_checkpointing
													? "Bật"
													: "Tắt"}
											</span>
										</div>
										<div className="flex justify-between">
											<span className="text-stone-500">
												Khả thi:
											</span>
											<span
												className={`font-mono font-semibold ${
													sc.feasible
														? "text-emerald-700"
														: "text-rose-700"
												}`}
											>
												{sc.feasible
													? "AN TOÀN"
													: "NGUY CƠ OOM"}
											</span>
										</div>
									</div>
								</div>

								<Button
									size="sm"
									variant={isSelected ? "primary" : "outline"}
									onClick={(e) => {
										e.stopPropagation();
										handleApply(sc);
									}}
									className={`mt-4 w-full text-xs h-8 ${
										isApplied
											? "bg-emerald-600 hover:bg-emerald-600 text-white"
											: ""
									}`}
								>
									{isApplied ? (
										<>
											<Check className="w-3.5 h-3.5 mr-1" />{" "}
											Đã áp dụng
										</>
									) : (
										"Áp dụng kịch bản"
									)}
								</Button>
							</div>
						);
					})}
				</div>

				{/* Deep Component Breakdown for Selected Scenario */}
				{activeScenario && activeScenario.components && (
					<div className="p-4 rounded-xl bg-[#faf8f5] border border-stone-300/80 shadow-warm-sm">
						<div className="flex items-center justify-between mb-4">
							<div className="text-xs font-semibold text-stone-900 flex items-center gap-2">
								<Cpu className="w-4 h-4 text-amber-700" />
								Chi tiết thành phần bộ nhớ:{" "}
								<span className="text-amber-800 font-bold">
									{activeScenario.name}
								</span>
							</div>
							<span className="text-xs font-mono text-stone-600">
								Tổng: {Math.round(activeScenario.estimated_mb)}{" "}
								MB ({activeScenario.estimated_gb.toFixed(2)} GB)
							</span>
						</div>

						{/* Segmented Progress Bar */}
						<div className="space-y-4">
							<div className="h-3 w-full bg-stone-200 rounded-full overflow-hidden flex border border-stone-300/80">
								<div
									style={{
										width: `${(activeScenario.components.parameters / (activeScenario.estimated_mb || 1)) * 100}%`,
									}}
									className="bg-amber-600 h-full"
									title={`Weights: ${Math.round(activeScenario.components.parameters)} MB`}
								/>
								<div
									style={{
										width: `${(activeScenario.components.gradients / (activeScenario.estimated_mb || 1)) * 100}%`,
									}}
									className="bg-sky-600 h-full"
									title={`Gradients: ${Math.round(activeScenario.components.gradients)} MB`}
								/>
								<div
									style={{
										width: `${(activeScenario.components.optimizer_states / (activeScenario.estimated_mb || 1)) * 100}%`,
									}}
									className="bg-amber-500 h-full"
									title={`Optimizer: ${Math.round(activeScenario.components.optimizer_states)} MB`}
								/>
								<div
									style={{
										width: `${(activeScenario.components.activations / (activeScenario.estimated_mb || 1)) * 100}%`,
									}}
									className="bg-emerald-600 h-full"
									title={`Activations: ${Math.round(activeScenario.components.activations)} MB`}
								/>
								<div
									style={{
										width: `${(activeScenario.components.cuda_context_overhead / (activeScenario.estimated_mb || 1)) * 100}%`,
									}}
									className="bg-rose-500 h-full"
									title={`CUDA Overhead: ${Math.round(activeScenario.components.cuda_context_overhead)} MB`}
								/>
							</div>

							<div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
								<div className="p-2.5 rounded-lg bg-[#f4f3ed] border border-stone-200/80">
									<div className="flex items-center gap-1.5 text-amber-800 font-medium mb-1">
										<span className="w-2 h-2 rounded-full bg-amber-600"></span>{" "}
										Trọng số Model
									</div>
									<div className="text-sm font-mono font-semibold text-stone-900">
										{Math.round(
											activeScenario.components
												.parameters,
										)}{" "}
										MB
									</div>
								</div>
								<div className="p-2.5 rounded-lg bg-[#f4f3ed] border border-stone-200/80">
									<div className="flex items-center gap-1.5 text-sky-800 font-medium mb-1">
										<span className="w-2 h-2 rounded-full bg-sky-600"></span>{" "}
										Gradients
									</div>
									<div className="text-sm font-mono font-semibold text-stone-900">
										{Math.round(
											activeScenario.components.gradients,
										)}{" "}
										MB
									</div>
								</div>
								<div className="p-2.5 rounded-lg bg-[#f4f3ed] border border-stone-200/80">
									<div className="flex items-center gap-1.5 text-amber-800 font-medium mb-1">
										<span className="w-2 h-2 rounded-full bg-amber-500"></span>{" "}
										Optimizer States
									</div>
									<div className="text-sm font-mono font-semibold text-stone-900">
										{Math.round(
											activeScenario.components
												.optimizer_states,
										)}{" "}
										MB
									</div>
								</div>
								<div className="p-2.5 rounded-lg bg-[#f4f3ed] border border-stone-200/80">
									<div className="flex items-center gap-1.5 text-emerald-800 font-medium mb-1">
										<span className="w-2 h-2 rounded-full bg-emerald-600"></span>{" "}
										Activations
									</div>
									<div className="text-sm font-mono font-semibold text-stone-900">
										{Math.round(
											activeScenario.components
												.activations,
										)}{" "}
										MB
									</div>
								</div>
								<div className="p-2.5 rounded-lg bg-[#f4f3ed] border border-stone-200/80">
									<div className="flex items-center gap-1.5 text-rose-800 font-medium mb-1">
										<span className="w-2 h-2 rounded-full bg-rose-500"></span>{" "}
										CUDA Overhead
									</div>
									<div className="text-sm font-mono font-semibold text-stone-900">
										{Math.round(
											activeScenario.components
												.cuda_context_overhead,
										)}{" "}
										MB
									</div>
								</div>
							</div>
						</div>
					</div>
				)}
			</CardContent>
		</Card>
	);
};
