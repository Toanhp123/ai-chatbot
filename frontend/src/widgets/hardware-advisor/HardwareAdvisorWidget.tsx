import React from "react";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	Badge,
	Button,
	ProgressBar,
	StatusDot,
} from "@/shared/ui";
import { useHardwareAdvisor } from "./model/useHardwareAdvisor";
import {
	Cpu,
	HardDrive,
	Activity,
	AlertTriangle,
	CheckCircle2,
	XCircle,
	RefreshCw,
	Zap,
	ShieldCheck,
} from "lucide-react";

export const HardwareAdvisorWidget: React.FC = () => {
	const { data, loading, error, fetchAdvisor } = useHardwareAdvisor();

	const getHealthBadge = (status?: string) => {
		switch (status?.toUpperCase()) {
			case "HEALTHY":
				return (
					<Badge
						variant="success"
						className="px-3 py-1 text-sm font-semibold flex items-center gap-1.5"
					>
						<StatusDot color="emerald" pulse />
						<CheckCircle2 className="w-4 h-4 mr-0.5" /> HỆ THỐNG
						KHỎE MẠNH (HEALTHY)
					</Badge>
				);
			case "WARNING":
				return (
					<Badge
						variant="warning"
						className="px-3 py-1 text-sm font-semibold flex items-center gap-1.5"
					>
						<StatusDot color="amber" pulse />
						<AlertTriangle className="w-4 h-4 mr-0.5" /> CẢNH BÁO
						(WARNING)
					</Badge>
				);
			case "CRITICAL":
				return (
					<Badge
						variant="danger"
						className="px-3 py-1 text-sm font-semibold flex items-center gap-1.5"
					>
						<StatusDot color="rose" pulse />
						<XCircle className="w-4 h-4 mr-0.5" /> NGUY CƠ CAO
						(CRITICAL)
					</Badge>
				);
			default:
				return (
					<Badge
						variant="neutral"
						className="px-3 py-1 text-sm flex items-center gap-1.5"
					>
						<StatusDot color="slate" />
						{status || "ĐANG QUÉT"}
					</Badge>
				);
		}
	};

	const primaryGpu = data?.gpu?.primary_gpu;
	const isCudaReady = Boolean(data?.gpu?.cuda_available);

	return (
		<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
			<CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-stone-200/80">
				<div className="flex items-center gap-3">
					<div className="p-2 rounded-lg bg-amber-50 border border-amber-200/80 text-amber-700">
						<Activity className="w-5 h-5" />
					</div>
					<div>
						<CardTitle className="text-base text-stone-900 flex items-center gap-2">
							Cố Vấn Phần Cứng & Nhân Tính Toán SDPA
						</CardTitle>
						<p className="text-xs text-stone-500 mt-0.5">
							Phân tích sâu GPU, nhân gia tốc PyTorch SDPA, I/O
							lưu trữ và phân quyền
						</p>
					</div>
				</div>
				<div className="flex items-center gap-3">
					{data && getHealthBadge(data.health_status)}
					<Button
						size="sm"
						variant="outline"
						onClick={fetchAdvisor}
						className="h-8 shadow-warm-sm"
					>
						<RefreshCw
							className={`w-3.5 h-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}
						/>
						Làm mới
					</Button>
				</div>
			</CardHeader>

			<CardContent className="pt-5 space-y-6">
				{error && (
					<div className="p-3 bg-rose-50 border border-rose-200/80 rounded-lg text-rose-700 text-xs flex items-center gap-2">
						<AlertTriangle className="w-4 h-4 shrink-0" />
						<span>{error}</span>
					</div>
				)}

				{/* Top 3 Cards: GPU, Attention Backends, Disk & IO */}
				<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
					{/* Card 1: GPU Info */}
					<div className="p-4 rounded-xl bg-[#faf8f5] border border-stone-300/80 shadow-warm-sm flex flex-col justify-between">
						<div>
							<div className="flex items-center justify-between text-xs text-stone-600 font-medium mb-2">
								<span className="flex items-center gap-1.5 text-amber-700 font-semibold">
									<Zap className="w-4 h-4" /> THIẾT BỊ TÍNH
									TOÁN
								</span>
								<Badge
									variant={
										isCudaReady ? "success" : "neutral"
									}
								>
									{isCudaReady ? "CUDA SẴN SÀNG" : "CPU MODE"}
								</Badge>
							</div>
							<div
								className="text-sm font-semibold text-stone-900 truncate"
								title={
									primaryGpu?.name ||
									(isCudaReady
										? "NVIDIA GPU"
										: "Chế độ CPU thuần")
								}
							>
								{primaryGpu?.name ||
									(isCudaReady
										? "NVIDIA GPU"
										: "Chế độ CPU thuần")}
							</div>
							<div className="mt-3 space-y-2 text-xs">
								{primaryGpu?.vram_total_gb !== undefined &&
								primaryGpu.vram_total_gb > 0 ? (
									<ProgressBar
										value={
											primaryGpu.vram_free_gb !==
											undefined
												? Math.round(
														((primaryGpu.vram_total_gb -
															primaryGpu.vram_free_gb) /
															primaryGpu.vram_total_gb) *
															100,
													)
												: 0
										}
										label="Mức sử dụng VRAM"
										valueText={
											primaryGpu.vram_free_gb !==
											undefined
												? `${(primaryGpu.vram_total_gb - primaryGpu.vram_free_gb).toFixed(1)} / ${primaryGpu.vram_total_gb} GB`
												: undefined
										}
										size="sm"
									/>
								) : null}
								<div className="flex justify-between text-stone-600">
									<span>Tổng VRAM:</span>
									<span className="font-mono text-stone-900 font-medium">
										{primaryGpu?.vram_total_gb !== undefined
											? `${primaryGpu.vram_total_gb} GB`
											: "N/A"}
									</span>
								</div>
								<div className="flex justify-between text-stone-600">
									<span>VRAM Khả dụng:</span>
									<span className="font-mono text-emerald-700 font-semibold">
										{primaryGpu?.vram_free_gb !== undefined
											? `${primaryGpu.vram_free_gb} GB`
											: "N/A"}
									</span>
								</div>
								<div className="flex justify-between text-stone-600">
									<span>Compute Capability:</span>
									<span className="font-mono text-stone-800">
										{primaryGpu?.compute_capability ||
											"N/A"}
									</span>
								</div>
							</div>
						</div>
						{data?.recommendations?.recommended_precision && (
							<div className="mt-3 pt-2.5 border-t border-stone-200/80 text-[11px] text-amber-800">
								Gợi ý Precision:{" "}
								<span className="font-bold text-amber-900 uppercase">
									{data.recommendations.recommended_precision}
								</span>
							</div>
						)}
					</div>

					{/* Card 2: Attention Backends */}
					<div className="p-4 rounded-xl bg-[#faf8f5] border border-stone-300/80 shadow-warm-sm flex flex-col justify-between">
						<div>
							<div className="flex items-center justify-between text-xs text-stone-600 font-medium mb-2">
								<span className="flex items-center gap-1.5 text-amber-700 font-semibold">
									<Cpu className="w-4 h-4" /> NHÂN SDPA
									PYTORCH
								</span>
								<span className="text-[10px] text-stone-400 font-mono">
									F.scaled_dot_product_attention
								</span>
							</div>
							<div className="text-xs text-stone-600 mb-3">
								Cơ chế tự động điều phối nhân Attention tốc độ
								cao:
							</div>
							<div className="space-y-2">
								<div className="flex items-center justify-between p-2 rounded-lg bg-[#f4f3ed] border border-stone-200/80">
									<span className="text-xs font-medium text-stone-800">
										FlashAttention-2
									</span>
									<Badge
										variant={
											data?.backends?.flash_attention
												? "success"
												: "neutral"
										}
									>
										{data?.backends?.flash_attention
											? "SẴN SÀNG"
											: "KHÔNG HỖ TRỢ"}
									</Badge>
								</div>
								<div className="flex items-center justify-between p-2 rounded-lg bg-[#f4f3ed] border border-stone-200/80">
									<span className="text-xs font-medium text-stone-800">
										CuDNN / Cutlass
									</span>
									<Badge
										variant={
											data?.backends?.memory_efficient
												? "success"
												: "neutral"
										}
									>
										{data?.backends?.memory_efficient
											? "KÍCH HOẠT"
											: "CHƯA CÓ"}
									</Badge>
								</div>
								<div className="flex items-center justify-between p-2 rounded-lg bg-[#f4f3ed] border border-stone-200/80">
									<span className="text-xs font-medium text-stone-800">
										Math Fallback
									</span>
									<Badge variant="info">MẶC ĐỊNH</Badge>
								</div>
							</div>
						</div>
					</div>

					{/* Card 3: Storage & Permissions */}
					<div className="p-4 rounded-xl bg-[#faf8f5] border border-stone-300/80 shadow-warm-sm flex flex-col justify-between">
						<div>
							<div className="flex items-center justify-between text-xs text-stone-600 font-medium mb-2">
								<span className="flex items-center gap-1.5 text-amber-700 font-semibold">
									<HardDrive className="w-4 h-4" /> LƯU TRỮ &
									PHÂN QUYỀN
								</span>
								<span className="text-[10px] text-stone-400">
									I/O CHECK
								</span>
							</div>
							<div className="mt-2 space-y-2">
								{typeof data?.disk?.percent_used === "number" && (
									<ProgressBar
										value={data.disk.percent_used}
										label="Mức dùng đĩa"
										valueText={
											typeof data.disk.total_gb === "number" &&
											typeof data.disk.free_gb === "number"
												? `${(data.disk.total_gb - data.disk.free_gb).toFixed(1)} / ${data.disk.total_gb} GB (${data.disk.percent_used}%)`
												: `${data.disk.percent_used}%`
										}
										size="sm"
									/>
								)}
								<div className="flex justify-between text-xs text-stone-600">
									<span>Ổ đĩa còn trống:</span>
									<span className="text-emerald-700 font-mono font-semibold">
										{data?.disk?.free_gb ?? "--"} GB
									</span>
								</div>
								<div className="flex justify-between text-xs text-stone-600">
									<span>Tổng dung lượng:</span>
									<span className="font-mono text-stone-800">
										{data?.disk?.total_gb ?? "--"} GB
									</span>
								</div>
							</div>
							<div className="mt-3 pt-3 border-t border-stone-200/80">
								<div className="text-xs text-stone-600 mb-2 flex items-center gap-1.5">
									<ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
									Quyền ghi thư mục:
								</div>
								<div className="grid grid-cols-2 gap-1.5">
									{data?.permissions &&
										Object.entries(data.permissions).map(
											([dir, perm]) => (
												<div
													key={dir}
													className="flex items-center justify-between px-2 py-1 bg-[#f4f3ed] rounded border border-stone-200/80 text-[11px]"
												>
													<span className="font-mono text-stone-800 truncate">
														{dir}/
													</span>
													{perm?.writable ? (
														<span className="text-emerald-700 font-bold">
															OK
														</span>
													) : (
														<span className="text-rose-700 font-bold">
															LỖI
														</span>
													)}
												</div>
											),
										)}
								</div>
							</div>
						</div>
					</div>
				</div>

				{/* Suggestions & Warnings */}
				{Boolean(
					data?.suggestions?.length || data?.warnings?.length,
				) && (
					<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
						{Boolean(data?.suggestions?.length) && (
							<div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200/80">
								<div className="text-xs font-semibold text-amber-900 mb-2 flex items-center gap-1.5">
									<Zap className="w-3.5 h-3.5 text-amber-700" />{" "}
									GỢI Ý TỐI ƯU HÓA HIỆU SUẤT
								</div>
								<ul className="space-y-1.5 text-xs text-stone-700">
									{data?.suggestions.map((sug, idx) => (
										<li
											key={idx}
											className="flex items-start gap-2"
										>
											<span className="text-amber-700 font-bold">
												•
											</span>
											<span>{sug}</span>
										</li>
									))}
								</ul>
							</div>
						)}
						{Boolean(data?.warnings?.length) && (
							<div className="p-3.5 rounded-xl bg-rose-50/80 border border-rose-200/80">
								<div className="text-xs font-semibold text-rose-900 mb-2 flex items-center gap-1.5">
									<AlertTriangle className="w-3.5 h-3.5 text-rose-700" />{" "}
									LƯU Ý PHẦN CỨNG
								</div>
								<ul className="space-y-1.5 text-xs text-stone-700">
									{data?.warnings.map((warn, idx) => (
										<li
											key={idx}
											className="flex items-start gap-2"
										>
											<span className="text-rose-600 font-bold">
												•
											</span>
											<span>{warn}</span>
										</li>
									))}
								</ul>
							</div>
						)}
					</div>
				)}
			</CardContent>
		</Card>
	);
};
