import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/shared/ui";
import { Badge } from "@/shared/ui";
import { Button } from "@/shared/ui";
import { useQualityGates } from "@/features/gates";
import type { GateResult } from "@/features/gates";
import {
	ShieldCheck,
	CheckCircle2,
	XCircle,
	Play,
	Clock,
	ChevronDown,
	ChevronRight,
	Terminal,
	Award,
} from "lucide-react";

export const QualityGatesAuditWidget: React.FC = () => {
	const { isRunning, report, runGates } = useQualityGates();
	const [expandedGates, setExpandedGates] = useState<Record<string, boolean>>(
		{},
	);

	const toggleExpand = (name: string) => {
		setExpandedGates((prev) => ({ ...prev, [name]: !prev[name] }));
	};

	return (
		<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
			<CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-stone-200/80">
				<div className="flex items-center gap-3">
					<div className="p-2 rounded-lg bg-emerald-50 border border-emerald-200/80 text-emerald-700">
						<ShieldCheck className="w-5 h-5" />
					</div>
					<div>
						<CardTitle className="text-base text-stone-900 flex items-center gap-2">
							Kiểm Toán Toàn Diện 6 Cổng Chất Lượng (Quality
							Gates)
						</CardTitle>
						<p className="text-xs text-stone-500 mt-0.5">
							Quy chuẩn kiến trúc Enterprise: Black, Flake8, MyPy,
							Clean Architecture, Diagnostics & Pytest
						</p>
					</div>
				</div>
				<div className="flex items-center gap-3">
					{report && (
						<Badge
							variant={report.all_passed ? "success" : "danger"}
							className="px-3 py-1 text-xs font-semibold"
						>
							{report.all_passed ? (
								<span className="flex items-center gap-1.5">
									<CheckCircle2 className="w-4 h-4" /> 100%
									QUALITY GATES PASSED
								</span>
							) : (
								<span className="flex items-center gap-1.5">
									<XCircle className="w-4 h-4" /> CÓ LỖI
									QUALITY GATE
								</span>
							)}
						</Badge>
					)}
					<Button
						size="sm"
						variant="primary"
						onClick={() => runGates()}
						disabled={isRunning}
						className="h-8 bg-emerald-700 hover:bg-emerald-800 text-white shadow-warm-sm"
					>
						<Play
							className={`w-3.5 h-3.5 mr-1.5 ${isRunning ? "animate-spin" : ""}`}
						/>
						{isRunning
							? "Đang thực thi 6 Gates..."
							: "🚀 Chạy Toàn Bộ Quality Gates"}
					</Button>
				</div>
			</CardHeader>

			<CardContent className="pt-5 space-y-4">
				{/* Banner if all passed */}
				{report && (
					<div
						className={`p-4 rounded-xl border flex items-center justify-between shadow-warm-sm ${
							report.all_passed
								? "bg-emerald-50 border-emerald-300/80 text-emerald-950"
								: "bg-rose-50 border-rose-300/80 text-rose-950"
						}`}
					>
						<div className="flex items-center gap-3">
							<Award className="w-6 h-6 shrink-0" />
							<div>
								<div className="text-sm font-semibold">
									{report.all_passed
										? "Xuất sắc! Mã nguồn đạt 100% chuẩn Enterprise"
										: "Phát hiện lỗi không đạt chuẩn tại một hoặc nhiều Gate"}
								</div>
								<div className="text-xs text-stone-600 mt-0.5">
									Tổng thời gian thực thi:{" "}
									{report.total_elapsed} giây | Đã kiểm tra{" "}
									{report.results?.length || 6} cổng chất
									lượng
								</div>
							</div>
						</div>
						<div className="text-xs font-mono px-2.5 py-1 rounded bg-[#f4f3ed] border border-stone-200/80 text-stone-700">
							Elapsed: {report.total_elapsed}s
						</div>
					</div>
				)}

				{/* Gates list */}
				<div className="space-y-2">
					{report?.results ? (
						report.results.map((gate: GateResult, idx: number) => {
							const isExpanded = !!expandedGates[gate.name];
							return (
								<div
									key={idx}
									className="rounded-xl border border-stone-300/80 bg-[#faf8f5] overflow-hidden transition-all duration-200 shadow-warm-sm"
								>
									<div
										onClick={() => toggleExpand(gate.name)}
										className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-[#f4f1e8]"
									>
										<div className="flex items-center gap-3">
											{gate.passed ? (
												<CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
											) : (
												<XCircle className="w-4 h-4 text-rose-700 shrink-0" />
											)}
											<div>
												<div className="text-xs font-semibold text-stone-900 flex items-center gap-2">
													<span>{gate.name}</span>
													<span className="text-[10px] px-1.5 py-0.5 rounded bg-[#f4f3ed] border border-stone-200/80 text-stone-600 font-mono">
														{gate.tool}
													</span>
												</div>
												<div className="text-[11px] text-stone-500 truncate max-w-lg mt-0.5">
													{gate.details}
												</div>
											</div>
										</div>

										<div className="flex items-center gap-3">
											<div className="flex items-center gap-1 text-[11px] text-stone-500 font-mono">
												<Clock className="w-3 h-3 text-stone-400" />
												{gate.elapsed}s
											</div>
											<Badge
												variant={
													gate.passed
														? "success"
														: "danger"
												}
												className="text-[10px]"
											>
												{gate.passed
													? "PASSED"
													: "FAILED"}
											</Badge>
											{isExpanded ? (
												<ChevronDown className="w-4 h-4 text-stone-400" />
											) : (
												<ChevronRight className="w-4 h-4 text-stone-400" />
											)}
										</div>
									</div>

									{isExpanded && (
										<div className="p-3.5 bg-[#f4f3ed] border-t border-stone-200/80 text-xs space-y-2">
											<div className="text-stone-700 font-mono text-[11px]">
												<span className="text-stone-500">
													Chi tiết kiểm tra:{" "}
												</span>
												{gate.details}
											</div>
											{gate.error_output && (
												<div>
													<div className="text-[11px] text-rose-800 font-semibold mb-1 flex items-center gap-1">
														<Terminal className="w-3 h-3" />{" "}
														Output lỗi / cảnh báo:
													</div>
													<pre className="p-2.5 rounded bg-stone-900 border border-stone-700 text-rose-300 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
														{gate.error_output}
													</pre>
												</div>
											)}
										</div>
									)}
								</div>
							);
						})
					) : (
						<div className="p-8 text-center rounded-xl border border-dashed border-stone-300/80 bg-[#f4f3ed]/60 text-stone-500 text-xs">
							<ShieldCheck className="w-8 h-8 mx-auto mb-2 text-stone-400 opacity-60" />
							Chưa có dữ liệu kiểm toán. Hãy nhấn nút{" "}
							<span className="text-emerald-700 font-semibold">
								"🚀 Chạy Toàn Bộ Quality Gates"
							</span>{" "}
							để bắt đầu kiểm tra.
						</div>
					)}
				</div>
			</CardContent>
		</Card>
	);
};
