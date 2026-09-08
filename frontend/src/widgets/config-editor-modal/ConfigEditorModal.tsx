import React, { useRef } from "react";
import { Modal, Button, Badge } from "@/shared/ui";
import { Save, RefreshCw, FileCode } from "lucide-react";

interface ConfigEditorModalProps {
	isOpen: boolean;
	onClose: () => void;
	path: string;
	content: string;
	setContent: (content: string) => void;
	isLoading: boolean;
	isSaving: boolean;
	onSave: () => void;
	onReload: () => void;
}

export const ConfigEditorModal: React.FC<ConfigEditorModalProps> = ({
	isOpen,
	onClose,
	path,
	content,
	setContent,
	isLoading,
	isSaving,
	onSave,
	onReload,
}) => {
	const lineCount = content ? content.split("\n").length : 1;
	const textareaRef = useRef<HTMLTextAreaElement>(null);
	const lineNumbersRef = useRef<HTMLDivElement>(null);

	// Đồng bộ cuộn giữa vùng code textarea và cột số thứ tự dòng
	const handleScroll = (e: React.UIEvent<HTMLTextAreaElement>) => {
		if (lineNumbersRef.current) {
			lineNumbersRef.current.scrollTop = e.currentTarget.scrollTop;
		}
	};

	return (
		<Modal
			isOpen={isOpen}
			onClose={onClose}
			disableBodyScroll={true}
			maxWidth="4xl"
			className="h-[84vh] max-h-[850px]"
			title={
				<div className="flex items-center gap-2">
					<FileCode className="w-5 h-5 text-amber-600" />
					<span className="font-semibold text-stone-900">
						Chỉnh Sửa Trực Tiếp Cấu Hình YAML
					</span>
					<Badge
						variant="neutral"
						className="font-mono text-[10px] ml-2"
					>
						{path}
					</Badge>
				</div>
			}
			footer={
				<div className="w-full flex items-center justify-between">
					<div className="text-[11px] text-stone-500 font-mono">
						Độ dài: {content.length.toLocaleString()} ký tự |{" "}
						{lineCount} dòng
					</div>
					<div className="flex items-center gap-2">
						<Button
							size="sm"
							variant="outline"
							onClick={onClose}
							disabled={isSaving}
							className="border-stone-300/80 text-stone-700 hover:bg-[#ebe8df]"
						>
							Hủy
						</Button>
						<Button
							size="sm"
							variant="primary"
							onClick={onSave}
							disabled={isSaving || isLoading}
						>
							<Save
								className={`w-3.5 h-3.5 mr-1.5 ${isSaving ? "animate-spin" : ""}`}
							/>
							{isSaving
								? "Đang lưu & Validate..."
								: "Lưu Cấu Hình YAML"}
						</Button>
					</div>
				</div>
			}
		>
			<div className="flex flex-col h-full space-y-3">
				{/* Thanh công cụ phụ cố định ở đầu */}
				<div className="flex items-center justify-between text-xs text-stone-600 shrink-0">
					<span>
						Chỉnh sửa các tham số Model, Training, Data và
						Callbacks. Cấu hình sẽ được xác thực trước khi áp dụng.
					</span>
					<Button
						size="sm"
						variant="outline"
						onClick={onReload}
						disabled={isSaving}
						className="h-7 text-xs border-stone-300/80 text-stone-700 hover:bg-[#f4f3ed]"
					>
						<RefreshCw
							className={`w-3 h-3 mr-1 ${isLoading ? "animate-spin" : ""}`}
						/>
						Nạp lại
					</Button>
				</div>

				{/* Vùng Editor Code: Chiếm toàn bộ chiều cao còn lại, thanh cuộn chỉ xuất hiện BÊN TRONG khung code */}
				<div className="flex-1 min-h-0 relative rounded-xl border border-stone-300/80 bg-[#faf8f5] font-mono text-xs overflow-hidden flex shadow-warm-sm">
					{/* Cột số dòng được đồng bộ cuộn */}
					<div
						ref={lineNumbersRef}
						className="py-3 px-2.5 bg-[#ebe8df] border-r border-stone-300/80 select-none text-stone-400 text-right font-mono min-w-[3.2rem] overflow-hidden leading-5 text-xs"
					>
						{Array.from({ length: lineCount }).map((_, i) => (
							<div key={i} className="leading-5 h-5">
								{i + 1}
							</div>
						))}
					</div>

					{/* Ô nhập code với thanh cuộn nội bộ */}
					<textarea
						ref={textareaRef}
						value={content}
						onChange={(e) => setContent(e.target.value)}
						onScroll={handleScroll}
						disabled={isLoading || isSaving}
						className="flex-1 h-full py-3 px-3 bg-transparent text-stone-900 focus:outline-none leading-5 resize-none font-mono text-xs selection:bg-amber-500/20 overflow-y-auto [scrollbar-gutter:stable]"
						spellCheck={false}
					/>
				</div>
			</div>
		</Modal>
	);
};
