import React from "react";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	Button,
	Table,
	TableHeader,
	TableBody,
	TableRow,
	TableHead,
	TableCell,
	SearchInput,
} from "@/shared/ui";
import { useModelInspector } from "./model/useModelInspector";
import { Boxes, Cpu, Layers, Database, Hash, RefreshCw } from "lucide-react";

export const ModelInspectorWidget: React.FC = () => {
	const {
		modelName,
		setModelName,
		data,
		loading,
		error,
		searchTerm,
		setSearchTerm,
		filteredLayers,
		fetchInspection,
	} = useModelInspector();

	return (
		<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
			<CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-stone-200/80">
				<div className="flex items-center gap-3">
					<div className="p-2 rounded-lg bg-amber-50 border border-amber-200/80 text-amber-700">
						<Boxes className="w-5 h-5" />
					</div>
					<div>
						<CardTitle className="text-base text-stone-900 flex items-center gap-2">
							Kiểm Tra Chi Tiết Kiến Trúc Mô Hình (Architecture
							Inspector)
						</CardTitle>
						<p className="text-xs text-stone-500 mt-0.5">
							Phân bổ trọng số từng tầng (layer-by-layer), tensor
							shape, bộ nhớ và trạng thái gradient
						</p>
					</div>
				</div>

				<div className="flex items-center gap-3">
					{/* Model Switcher */}
					<div className="flex rounded-lg bg-stone-100 p-0.5 border border-stone-200/80">
						<button
							type="button"
							onClick={() => setModelName("minigpt")}
							className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
								modelName === "minigpt"
									? "bg-[#faf8f5] text-stone-900 shadow-warm-sm border border-stone-300/80 font-semibold"
									: "text-stone-600 hover:text-stone-900"
							}`}
						>
							MiniGPT
						</button>
						<button
							type="button"
							onClick={() => setModelName("llama_nano")}
							className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
								modelName === "llama_nano"
									? "bg-[#faf8f5] text-stone-900 shadow-warm-sm border border-stone-300/80 font-semibold"
									: "text-stone-600 hover:text-stone-900"
							}`}
						>
							LLaMA Nano (RoPE/RMSNorm)
						</button>
					</div>

					<Button
						size="sm"
						variant="outline"
						onClick={fetchInspection}
						className="h-8 text-xs border-stone-300/80 text-stone-700 hover:bg-[#f4f3ed]"
					>
						<RefreshCw
							className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
						/>
					</Button>
				</div>
			</CardHeader>

			<CardContent className="pt-5 space-y-5">
				{error && (
					<div className="p-3 bg-rose-50 border border-rose-200/80 rounded-lg text-rose-700 text-xs">
						{error}
					</div>
				)}

				{/* Metrics Overview Ribbon */}
				{data && (
					<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
						<div className="p-3 rounded-xl bg-stone-50 border border-stone-200/90 shadow-warm-sm">
							<div className="text-[11px] text-stone-500 mb-1 flex items-center gap-1">
								<Hash className="w-3.5 h-3.5 text-amber-600" />{" "}
								Tổng tham số:
							</div>
							<div className="text-base font-bold font-mono text-stone-900">
								{data.total_parameters_formatted}
							</div>
						</div>

						<div className="p-3 rounded-xl bg-stone-50 border border-stone-200/90 shadow-warm-sm">
							<div className="text-[11px] text-stone-500 mb-1 flex items-center gap-1">
								<Layers className="w-3.5 h-3.5 text-sky-600" />{" "}
								Số tầng (n_layer):
							</div>
							<div className="text-base font-bold font-mono text-stone-900">
								{data.n_layer}
							</div>
						</div>

						<div className="p-3 rounded-xl bg-stone-50 border border-stone-200/90 shadow-warm-sm">
							<div className="text-[11px] text-stone-500 mb-1 flex items-center gap-1">
								<Cpu className="w-3.5 h-3.5 text-emerald-600" />{" "}
								Số đầu chú ý (n_head):
							</div>
							<div className="text-base font-bold font-mono text-stone-900">
								{data.n_head}
							</div>
						</div>

						<div className="p-3 rounded-xl bg-stone-50 border border-stone-200/90 shadow-warm-sm">
							<div className="text-[11px] text-stone-500 mb-1 flex items-center gap-1">
								<Boxes className="w-3.5 h-3.5 text-amber-600" />{" "}
								Số chiều nhúng (n_embd):
							</div>
							<div className="text-base font-bold font-mono text-stone-900">
								{data.n_embd}
							</div>
						</div>

						<div className="p-3 rounded-xl bg-stone-50 border border-stone-200/90 shadow-warm-sm">
							<div className="text-[11px] text-stone-500 mb-1 flex items-center gap-1">
								<Database className="w-3.5 h-3.5 text-stone-600" />{" "}
								Context (block_size):
							</div>
							<div className="text-base font-bold font-mono text-stone-900">
								{data.block_size}
							</div>
						</div>

						<div className="p-3 rounded-xl bg-stone-50 border border-stone-200/90 shadow-warm-sm">
							<div className="text-[11px] text-stone-500 mb-1 flex items-center gap-1">
								<Hash className="w-3.5 h-3.5 text-rose-600" />{" "}
								Kích thước Vocab:
							</div>
							<div className="text-base font-bold font-mono text-stone-900">
								{data.vocab_size}
							</div>
						</div>
					</div>
				)}

				{/* Layer Parameters Table */}
				<div className="space-y-3">
					<div className="flex items-center justify-between">
						<div className="text-xs font-semibold text-stone-800">
							Danh Sách Phân Bổ Trọng Số Từng Tầng (
							{data?.layers?.length || 0} layers đại diện):
						</div>
						<SearchInput
							value={searchTerm}
							onValueChange={setSearchTerm}
							placeholder="Lọc tên tầng (vd: attn, mlp, wte)..."
							wrapperClassName="w-64"
						/>
					</div>

					<Table>
						<TableHeader>
							<TableRow>
								<TableHead className="w-[35%] py-2.5 px-3">
									Tên Layer (Param Name)
								</TableHead>
								<TableHead className="w-[20%] py-2.5 px-3">
									Tensor Shape
								</TableHead>
								<TableHead
									className="w-[18%] py-2.5 px-3"
									align="right"
								>
									Số Tham Số
								</TableHead>
								<TableHead
									className="w-[15%] py-2.5 px-3"
									align="right"
								>
									Bộ Nhớ (KB)
								</TableHead>
								<TableHead
									className="w-[12%] py-2.5 px-3"
									align="center"
								>
									Trainable
								</TableHead>
							</TableRow>
						</TableHeader>
						<TableBody maxHeight="max-h-72">
							{filteredLayers && filteredLayers.length > 0 ? (
								filteredLayers.map((layer, idx) => (
									<TableRow key={idx}>
										<TableCell className="w-[35%] py-2 px-3 text-amber-800 font-semibold">
											{layer.name}
										</TableCell>
										<TableCell className="w-[20%] py-2 px-3 text-stone-600">
											[{layer.shape.join(", ")}]
										</TableCell>
										<TableCell
											className="w-[18%] py-2 px-3 text-stone-900 font-semibold"
											align="right"
										>
											{layer.params.toLocaleString()}
										</TableCell>
										<TableCell
											className="w-[15%] py-2 px-3 text-stone-600"
											align="right"
										>
											{layer.memory_kb} KB
										</TableCell>
										<TableCell
											className="w-[12%] py-2 px-3"
											align="center"
										>
											<span className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-300 font-semibold">
												{layer.trainable ? "YES" : "NO"}
											</span>
										</TableCell>
									</TableRow>
								))
							) : (
								<tr>
									<td
										colSpan={5}
										className="py-6 text-center text-stone-500 font-mono text-xs"
									>
										Không tìm thấy layer nào khớp với từ
										khóa tìm kiếm.
									</td>
								</tr>
							)}
						</TableBody>
					</Table>
				</div>
			</CardContent>
		</Card>
	);
};
