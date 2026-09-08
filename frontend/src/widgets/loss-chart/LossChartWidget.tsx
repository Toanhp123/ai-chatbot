import React, { useMemo } from "react";
import {
	Chart as ChartJS,
	CategoryScale,
	LinearScale,
	PointElement,
	LineElement,
	Title,
	Tooltip,
	Legend,
	Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { Card } from "@/shared/ui";
import type { LossStep, EvalStep } from "@/entities/training";

ChartJS.register(
	CategoryScale,
	LinearScale,
	PointElement,
	LineElement,
	Title,
	Tooltip,
	Legend,
	Filler,
);

export interface LossChartWidgetProps {
	historySteps: LossStep[];
	historyEvals: EvalStep[];
	currentLr: number | null;
}

export const LossChartWidget: React.FC<LossChartWidgetProps> = ({
	historySteps,
	historyEvals,
	currentLr,
}) => {
	const chartData = useMemo(() => {
		const valMap = new Map<number, number>();
		historyEvals.forEach((ev) => {
			valMap.set(ev.step, ev.val_loss);
		});

		const labels = historySteps.map((st) => st.step);
		const trainLosses = historySteps.map((st) => st.loss);
		const valLosses = labels.map((step) => valMap.get(step) ?? null);

		return {
			labels,
			datasets: [
				{
					label: "Train Loss",
					data: trainLosses,
					borderColor: "#d97706",
					backgroundColor: "rgba(217, 119, 6, 0.08)",
					borderWidth: 2,
					pointRadius: 0,
					pointHoverRadius: 4,
					tension: 0.3,
					fill: true,
				},
				{
					label: "Val Loss (Đánh Giá)",
					data: valLosses,
					borderColor: "#059669",
					backgroundColor: "#059669",
					borderWidth: 2,
					pointRadius: 4,
					pointHoverRadius: 6,
					showLine: true,
					spanGaps: true,
					tension: 0.2,
				},
			],
		};
	}, [historySteps, historyEvals]);

	const options = useMemo(
		() => ({
			responsive: true,
			maintainAspectRatio: false,
			animation: { duration: 300 },
			scales: {
				x: {
					grid: { color: "rgba(231, 229, 228, 0.7)" },
					ticks: {
						color: "#78716c",
						font: { size: 10, family: "monospace" },
					},
				},
				y: {
					grid: { color: "rgba(231, 229, 228, 0.7)" },
					ticks: {
						color: "#78716c",
						font: { size: 10, family: "monospace" },
					},
				},
			},
			plugins: {
				legend: {
					position: "top" as const,
					labels: {
						color: "#44403c",
						font: { size: 11 },
						boxWidth: 12,
					},
				},
				tooltip: {
					backgroundColor: "#faf8f5",
					titleColor: "#1c1917",
					bodyColor: "#44403c",
					borderColor: "#dad6cb",
					borderWidth: 1,
				},
			},
		}),
		[],
	);

	return (
		<Card
			header="📈 Biểu Đồ Hội Tụ Loss Thời Gian Thực (Live Loss Curves)"
			action={
				currentLr ? (
					<span className="text-xs font-mono text-amber-800 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-200/80">
						LR: {currentLr}
					</span>
				) : undefined
			}
			className="flex flex-col h-full min-h-[410px]"
		>
			<div className="flex-1 w-full h-full relative min-h-[300px]">
				{historySteps.length === 0 ? (
					<div className="absolute inset-0 flex flex-col items-center justify-center text-stone-400 text-xs">
						<span className="text-2xl mb-2">📊</span>
						<span>
							Chưa có dữ liệu bước huấn luyện. Nhấn 'Khởi Chạy
							Huấn Luyện' để bắt đầu.
						</span>
					</div>
				) : (
					<Line data={chartData} options={options} />
				)}
			</div>
		</Card>
	);
};
