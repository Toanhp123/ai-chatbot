import React from "react";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	Button,
	PageHeader,
	PageContainer,
	StatCard,
	Alert,
} from "@/shared/ui";
import { TextCleanerWidget, TokenizerVisualizerWidget } from "@/widgets";
import { useExplorer } from "./model/useExplorer";
import {
	Binary,
	Database,
	FileText,
	Package,
	Layers,
	Hash,
} from "lucide-react";

export const ExplorerPage: React.FC = () => {
	const {
		datasetInfo,
		exportingBinary,
		exportResult,
		tokenizerInputText,
		setTokenizerInputText,
		handleExportBinary,
	} = useExplorer();

	return (
		<PageContainer maxWidth="standard" spacing="normal">
			{/* Unified PageHeader Component */}
			<PageHeader
				icon={<Binary className="w-6 h-6" />}
				title="Dữ Liệu Huấn Luyện & Bộ Mã Hóa (Data & Tokenizer Studio)"
				subtitle="Khảo sát tập dữ liệu văn bản, tiền xử lý chuẩn hóa Unicode NFC, so sánh Tokenizer và đóng gói nhị phân"
			/>

			{/* Dataset Overview & Binary Packager Card */}
			<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
				<CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-stone-200/80">
					<div className="flex items-center gap-3">
						<div className="p-2 rounded-lg bg-amber-50 border border-amber-200/80 text-amber-700">
							<Database className="w-5 h-5" />
						</div>
						<div>
							<CardTitle className="text-base text-stone-900 flex items-center gap-2">
								Tập Dữ Liệu Gốc & Bộ Đóng Gói Nhị Phân (Binary
								Packager)
							</CardTitle>
							<p className="text-xs text-stone-500 mt-0.5">
								Chuyển đổi tập tin thô{" "}
								<span className="font-mono text-stone-700">
									data/input.txt
								</span>{" "}
								thành mảng uint16 nén cho Memmap DataLoader
							</p>
						</div>
					</div>

					<Button
						size="sm"
						variant="primary"
						onClick={handleExportBinary}
						disabled={exportingBinary}
						className="h-8 shadow-warm-sm"
					>
						<Package
							className={`w-3.5 h-3.5 mr-1.5 ${exportingBinary ? "animate-spin" : ""}`}
						/>
						{exportingBinary
							? "Đang đóng gói..."
							: "Đóng Gói Nhị Phân (.bin)"}
					</Button>
				</CardHeader>

				<CardContent className="pt-5 space-y-5">
					{/* Dataset Metric Stats (Built using Reusable StatCard Component) */}
					{datasetInfo && (
						<div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
							<StatCard
								icon={<FileText className="w-4 h-4" />}
								label="File nguồn"
								value={datasetInfo.input_file}
								variant="indigo"
							/>
							<StatCard
								icon={<Layers className="w-4 h-4" />}
								label="Tổng số dòng"
								value={`${datasetInfo.total_lines?.toLocaleString()} dòng`}
								variant="sky"
							/>
							<StatCard
								icon={<Hash className="w-4 h-4" />}
								label="Tổng số ký tự"
								value={`${datasetInfo.total_chars?.toLocaleString()} ký tự`}
								variant="emerald"
							/>
							<StatCard
								icon={<Binary className="w-4 h-4" />}
								label="Kích thước Vocab"
								value={`${datasetInfo.vocab_size} tokens`}
								variant="amber"
							/>
						</div>
					)}

					{/* Export Result Alert Component */}
					{exportResult && (
						<Alert variant="success" title={exportResult.message}>
							<span className="font-mono">
								Train:{" "}
								{exportResult.train_tokens?.toLocaleString()}{" "}
								tokens ({exportResult.train_size_mb} MB) | Val:{" "}
								{exportResult.val_tokens?.toLocaleString()}{" "}
								tokens ({exportResult.val_size_mb} MB)
							</span>
						</Alert>
					)}

					{/* Sample Lines Preview */}
					{datasetInfo?.sample_lines && (
						<div className="space-y-2">
							<div className="text-xs font-semibold text-stone-700">
								Xem trước một số mẫu văn bản tiêu biểu trong tập
								dữ liệu:
							</div>
							<div className="p-3.5 rounded-xl bg-[#f4f3ed] border border-stone-300/80 max-h-36 overflow-y-auto space-y-1">
								{datasetInfo.sample_lines
									.slice(0, 10)
									.map((line, idx) => (
										<div
											key={idx}
											className="text-xs font-serif text-stone-800 flex items-center gap-2"
										>
											<span className="text-[10px] text-stone-400 font-mono select-none">
												{String(idx + 1).padStart(
													2,
													"0",
												)}
												.
											</span>
											<span>{line}</span>
										</div>
									))}
							</div>
						</div>
					)}
				</CardContent>
			</Card>

			{/* Widget: Text Cleaner Sandbox */}
			<TextCleanerWidget
				onSendToTokenizer={(cleaned) => {
					setTokenizerInputText(cleaned);
				}}
			/>

			{/* Widget: Tokenizer Visualizer */}
			<TokenizerVisualizerWidget initialText={tokenizerInputText} />
		</PageContainer>
	);
};
