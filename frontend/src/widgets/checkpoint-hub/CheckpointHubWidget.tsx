import React from "react";
import {
	Database,
	Download,
	Trash2,
	RefreshCw,
	CheckCircle2,
	Sparkles,
	Copy,
	Search,
	RotateCcw,
} from "lucide-react";
import {
	Card,
	Button,
	Badge,
	EmptyState,
	Table,
	TableHeader,
	TableBody,
	TableRow,
	TableHead,
	TableCell,
	ActionMenu,
	SearchInput,
} from "@/shared/ui";
import { useCheckpointHub } from "./model/useCheckpointHub";
import type { Checkpoint } from "@/entities/checkpoint";

export interface CheckpointHubWidgetProps {
	checkpoints?: Checkpoint[];
	onRefresh?: () => void;
	onLoad?: (path: string) => void;
	onDelete?: (filename: string) => void;
	onSelectCheckpoint?: (cp: Checkpoint) => void;
	onSelectResume?: (cp: Checkpoint) => void;
	activeResumePath?: string;
	isLoading?: boolean;
}

export const CheckpointHubWidget: React.FC<CheckpointHubWidgetProps> = ({
	checkpoints: controlledCheckpoints,
	onRefresh: controlledRefresh,
	onLoad: controlledLoad,
	onDelete: controlledDelete,
	onSelectCheckpoint,
	onSelectResume,
	activeResumePath,
	isLoading: controlledLoading,
}) => {
	const {
		checkpoints,
		totalCount,
		filteredCount,
		searchTerm,
		setSearchTerm,
		isLoading,
		handleRefresh,
		handleLoad,
		handleDelete,
		getDownloadUrl,
	} = useCheckpointHub({
		checkpoints: controlledCheckpoints,
		onRefresh: controlledRefresh,
		onLoad: controlledLoad,
		onDelete: controlledDelete,
		isLoading: controlledLoading,
	});

	return (
		<Card
			header={
				<div className="flex items-center space-x-2">
					<Database className="w-4 h-4 text-amber-700" />
					<span className="font-semibold text-stone-900">
						Trung Tâm Quản Lý Checkpoint (Checkpoint Hub)
					</span>
					{totalCount > 0 && (
						<Badge
							variant="neutral"
							className="ml-2 font-mono text-[11px] text-stone-600 bg-[#ebe8df]"
						>
							{searchTerm.trim()
								? `${filteredCount} / ${totalCount} mô hình`
								: `${totalCount} mô hình`}
						</Badge>
					)}
				</div>
			}
			subtitle="Mô hình tốt nhất (Best) luôn được ghim ở đầu, bên dưới sắp xếp theo phiên mới nhất với khung cuộn giới hạn"
			action={
				<div className="flex items-center gap-2.5">
					<SearchInput
						value={searchTerm}
						onValueChange={setSearchTerm}
						placeholder="Lọc checkpoint (vd: best, step100)..."
						wrapperClassName="w-56 sm:w-64"
					/>

					<Button
						variant="secondary"
						size="sm"
						onClick={handleRefresh}
						className="border-stone-300/80 shrink-0"
					>
						<RefreshCw
							className={`w-3.5 h-3.5 mr-1 ${isLoading ? "animate-spin" : ""}`}
						/>
						<span>Làm Mới</span>
					</Button>
				</div>
			}
		>
			<Table>
				<TableHeader>
					<TableRow>
						<TableHead className="w-[34%]">
							Tên File Checkpoint
						</TableHead>
						<TableHead className="w-[10%]" align="center">
							Bước (Step)
						</TableHead>
						<TableHead className="w-[12%]" align="center">
							Val Loss
						</TableHead>
						<TableHead className="w-[12%]" align="right">
							Dung Lượng
						</TableHead>
						<TableHead className="w-[14%]" align="right">
							Thời Gian
						</TableHead>
						<TableHead className="w-[18%]" align="center">
							Thao Tác
						</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody maxHeight="max-h-[360px]">
					{checkpoints.map((c) => (
						<TableRow
							key={c.path}
							active={c.is_active}
							highlight={c.filename === "best_model.pt"}
						>
							<TableCell className="w-[34%]">
								<div className="flex flex-col gap-1 py-1 max-w-full">
									{/* Hàng 1: Tên file chính và trạng thái hoạt động */}
									<div className="flex items-center gap-2 min-w-0">
										<span
											className="font-semibold text-stone-900 font-mono text-xs truncate max-w-[280px]"
											title={c.filename}
										>
											{c.filename}
										</span>
										{c.is_active && (
											<Badge
												variant="emerald"
												className="font-bold flex items-center gap-1 shadow-warm-xs text-[10px] py-0 px-1.5 shrink-0"
											>
												<CheckCircle2 className="w-2.5 h-2.5" />
												Đang Nạp
											</Badge>
										)}
										{activeResumePath === c.path && (
											<Badge
												variant="warning"
												className="font-bold flex items-center gap-1 shadow-warm-xs text-[10px] py-0 px-1.5 shrink-0 bg-amber-100 text-amber-900 border border-amber-300"
											>
												<RotateCcw className="w-2.5 h-2.5" />
												Đang Chọn Resume
											</Badge>
										)}
									</div>

									{/* Hàng 2: Các nhãn/tag mô tả chuyên dụng (chống co ép hàng ngang) */}
									<div className="flex items-center flex-wrap gap-1.5">
										{c.filename === "best_model.pt" && (
											<Badge
												variant="amber"
												className="font-bold flex items-center gap-1 shadow-warm-xs text-[10px] py-0.5 px-2 whitespace-nowrap shrink-0"
												title="Mô hình đạt kỷ lục Loss thấp nhất hệ thống qua mọi phiên"
											>
												<Sparkles className="w-2.5 h-2.5 fill-current text-amber-600" />
												Mô hình Tốt nhất (Best)
											</Badge>
										)}
										{c.filename === "last_model.pt" && (
											<Badge
												variant="neutral"
												className="text-[10px] font-medium text-stone-600 bg-stone-200/80 whitespace-nowrap shrink-0"
												title="Bản sao đồng bộ bước mới nhất toàn hệ thống (phục vụ Resume nhanh)"
											>
												Mới nhất toàn cục
											</Badge>
										)}
										{c.filename !== "best_model.pt" &&
											c.filename !== "last_model.pt" &&
											c.filename.endsWith("_last.pt") && (
												<Badge
													variant="neutral"
													className="text-[10px] font-medium text-stone-600 bg-[#f0eee6] border border-stone-300/70 whitespace-nowrap shrink-0"
													title={`Lưu vết trạng thái khi kết thúc phiên ${c.run_name || ""}`}
												>
													Cuối phiên{" "}
													{c.run_name
														? `(${c.run_name})`
														: ""}
												</Badge>
											)}
										{c.is_best_val &&
											c.filename !== "best_model.pt" && (
												<Badge
													variant="emerald"
													className="text-[10px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 whitespace-nowrap shrink-0"
													title={`Checkpoint này đạt loss thấp kỷ lục: ${c.val_loss}`}
												>
													Kỷ lục Loss ({c.val_loss})
												</Badge>
											)}
									</div>
								</div>
							</TableCell>
							<TableCell
								className="w-[10%] text-stone-600 font-mono text-xs"
								align="center"
							>
								{c.step !== undefined &&
								c.step !== null &&
								c.step > 0
									? c.step
									: "---"}
							</TableCell>
							<TableCell
								className="w-[12%] font-bold"
								align="center"
							>
								<span
									className={
										c.val_loss !== undefined &&
										c.val_loss !== null &&
										c.val_loss > 0
											? "text-emerald-700 font-semibold font-mono"
											: "text-stone-400"
									}
								>
									{c.val_loss !== undefined &&
									c.val_loss !== null &&
									c.val_loss > 0
										? c.val_loss.toFixed(4)
										: "---"}
								</span>
							</TableCell>
							<TableCell
								className="w-[12%] text-stone-600"
								align="right"
							>
								{c.size_mb} MB
							</TableCell>
							<TableCell
								className="w-[14%] text-stone-500 text-[11px]"
								align="right"
							>
								{c.modified_time}
							</TableCell>
							<TableCell className="w-[18%]" align="center">
								<div className="flex items-center justify-center gap-1.5">
									<Button
										variant={
											c.is_active ? "outline" : "primary"
										}
										size="sm"
										disabled={c.is_active}
										onClick={() => {
											handleLoad(c.path);
											onSelectCheckpoint?.(c);
										}}
										className="h-7 px-3 text-xs font-medium shadow-warm-sm"
									>
										{c.is_active
											? "Đang Chọn"
											: "Nạp Mô Hình"}
									</Button>
									<ActionMenu
										align="end"
										items={[
											{
												label:
													activeResumePath === c.path
														? "Hủy chọn Resume"
														: "Tiếp tục huấn luyện từ đây (Resume)",
												icon: (
													<RotateCcw className="w-3.5 h-3.5 text-amber-700" />
												),
												onClick: () => {
													if (
														activeResumePath ===
														c.path
													) {
														onSelectResume?.({
															...c,
															path: "",
														});
													} else {
														onSelectResume?.(c);
													}
												},
											},
											{
												separatorBefore: true,
												label: "Tải file checkpoint (.pt)",
												icon: (
													<Download className="w-3.5 h-3.5 text-stone-600" />
												),
												href: getDownloadUrl(
													c.filename,
												),
												download: c.filename,
											},
											{
												label: "Sao chép đường dẫn file",
												icon: (
													<Copy className="w-3.5 h-3.5 text-stone-600" />
												),
												onClick: () => {
													navigator.clipboard.writeText(
														c.path,
													);
												},
											},
											...(c.filename !==
												"best_model.pt" && !c.is_active
												? [
														{
															separatorBefore: true,
															label: "Xóa checkpoint này",
															icon: (
																<Trash2 className="w-3.5 h-3.5" />
															),
															variant:
																"danger" as const,
															onClick: () =>
																handleDelete(
																	c.filename,
																),
														},
													]
												: []),
										]}
									/>
								</div>
							</TableCell>
						</TableRow>
					))}
					{checkpoints.length === 0 && (
						<tr>
							<td colSpan={6} className="py-8 px-4">
								{searchTerm.trim() ? (
									<EmptyState
										icon={
											<Search className="w-6 h-6 text-stone-400" />
										}
										title="Không tìm thấy checkpoint"
										description={`Không có file checkpoint nào phù hợp với từ khóa "${searchTerm}".`}
										action={
											<Button
												variant="secondary"
												size="sm"
												onClick={() =>
													setSearchTerm("")
												}
												className="mt-2 text-xs border-stone-300/80"
											>
												Xóa bộ lọc tìm kiếm
											</Button>
										}
										className="border-none bg-transparent py-4"
									/>
								) : (
									<EmptyState
										icon={
											<Database className="w-6 h-6 text-stone-400" />
										}
										title="Chưa có checkpoint nào được lưu"
										description="Khởi chạy một phiên huấn luyện mô hình để lưu checkpoint tốt nhất!"
										className="border-none bg-transparent py-4"
									/>
								)}
							</td>
						</tr>
					)}
				</TableBody>
			</Table>
		</Card>
	);
};
