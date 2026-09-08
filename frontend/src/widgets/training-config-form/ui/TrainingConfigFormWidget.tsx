import React, { useState } from "react";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	Switch,
	Input,
	Select,
	Badge,
	useToast,
} from "@/shared/ui";
import type {
	TrainingConfigForm,
	TrainingOverrideField,
	PreflightMemoryInfo,
} from "@/entities/training";
import { Sliders, ShieldCheck, Loader2 } from "lucide-react";

export interface TrainingConfigFormWidgetProps {
	form: TrainingConfigForm;
	onFormChange: (
		updated: TrainingConfigForm,
		changedField?: TrainingOverrideField,
	) => void;
	onCheckFeasibility: (
		config: TrainingConfigForm,
		changedField?: TrainingOverrideField,
	) => Promise<PreflightMemoryInfo | null> | void;
	preflightInfo?: PreflightMemoryInfo | null;
}

export const TrainingConfigFormWidget: React.FC<
	TrainingConfigFormWidgetProps
> = ({ form, onFormChange, onCheckFeasibility, preflightInfo }) => {
	const { toast } = useToast();
	const [isChecking, setIsChecking] = useState(false);

	const updateField = <K extends TrainingOverrideField>(
		key: K,
		value: TrainingConfigForm[K],
		triggerCheck = false,
	) => {
		const updated = { ...form, [key]: value };
		onFormChange(updated, key);
		if (triggerCheck) {
			onCheckFeasibility(updated, key);
		}
	};

	const handleManualCheck = async () => {
		setIsChecking(true);
		try {
			const res = await onCheckFeasibility(form);
			if (res) {
				if (res.feasible) {
					toast(
						`Ước tính VRAM: Dự kiến đỉnh ~${res.estimated_gb?.toFixed(2)} GB (${res.estimated_mb?.toFixed(0)} MB). Đây là ước tính tham khảo trước khi tokenizer runtime được chốt.`,
						"success",
					);
				} else {
					toast(
						`Cảnh báo VRAM (ước tính): Dự kiến đỉnh ~${res.estimated_gb?.toFixed(2)} GB vượt ngân sách hiện tại. Hãy giảm Batch Size hoặc bật Gradient Checkpointing trước khi chạy.`,
						"warning",
					);
				}
			}
		} finally {
			setIsChecking(false);
		}
	};

	return (
		<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm h-full flex flex-col justify-between">
			<CardHeader className="pb-3 border-b border-stone-200/80 flex flex-row items-center justify-between gap-2 shrink-0">
				<CardTitle className="text-xs text-stone-900 flex items-center gap-2">
					<Sliders className="w-4 h-4 text-amber-700" />
					<span>Cấu Hình Siêu Tham Số Huấn Luyện</span>
				</CardTitle>
				<div className="flex items-center gap-2">
					{preflightInfo && (
						<Badge
							variant={
								preflightInfo.feasible ? "success" : "warning"
							}
							className="text-[10px] font-mono font-medium hidden sm:inline-flex"
						>
							{preflightInfo.feasible
								? `✓ ${preflightInfo.estimated_gb?.toFixed(2)} GB`
								: `⚠️ ${preflightInfo.estimated_gb?.toFixed(2)} GB`}
						</Badge>
					)}
					<button
						type="button"
						onClick={handleManualCheck}
						disabled={isChecking}
						className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#f4f3ed] hover:bg-stone-200/80 border border-stone-300/80 text-[11px] text-stone-800 font-medium transition-all shadow-warm-sm disabled:opacity-60"
						title="Ước tính tham khảo bộ nhớ GPU trước khi tokenizer runtime được chốt"
					>
						{isChecking ? (
							<Loader2 className="w-3 h-3 text-amber-700 animate-spin" />
						) : (
							<ShieldCheck className="w-3.5 h-3.5 text-amber-700" />
						)}
						<span>
							{isChecking ? "Đang tính..." : "Kiểm tra VRAM"}
						</span>
					</button>
				</div>
			</CardHeader>

			<CardContent className="pt-4 space-y-4 text-xs flex-1 flex flex-col justify-between">
				{/* Model Choice & Precision */}
				<div className="grid grid-cols-2 gap-3">
					<Select
						label="Mô hình kiến trúc"
						value={form.model_name}
						onValueChange={(val) =>
							updateField("model_name", val, true)
						}
						options={[
							{
								value: "minigpt",
								label: "MiniGPT",
								description: "Nhẹ, tối ưu huấn luyện nhanh",
							},
							{
								value: "llama_nano",
								label: "LLaMA Nano",
								description: "RoPE + RMSNorm + SiLU",
							},
						]}
					/>

					<Select
						label="Độ chính xác (Precision)"
						value={form.precision}
						onValueChange={(val) =>
							updateField("precision", val, true)
						}
						options={[
							{
								value: "float32",
								label: "Float32",
								description: "Độ chuẩn cao (32-bit)",
							},
							{
								value: "float16",
								label: "Float16",
								description: "Tiết kiệm 50% VRAM",
							},
							{
								value: "bfloat16",
								label: "BFloat16",
								description: "Dải động rộng (Ampere+)",
							},
						]}
					/>
				</div>

				{/* Batch Size & Grad Accumulation */}
				<div className="grid grid-cols-2 gap-3">
					<Input
						type="number"
						label="Batch Size (Kích thước lô)"
						value={form.batch_size}
						onChange={(e) =>
							updateField(
								"batch_size",
								parseInt(e.target.value, 10) || 1,
								true,
							)
						}
					/>

					<Input
						type="number"
						label="Grad Accumulation (Bước tích lũy)"
						value={form.gradient_accumulation_steps}
						onChange={(e) =>
							updateField(
								"gradient_accumulation_steps",
								parseInt(e.target.value, 10) || 1,
								true,
							)
						}
					/>
				</div>

				{/* Learning Rate & Max Iters */}
				<div className="grid grid-cols-2 gap-3">
					<Input
						type="number"
						step="0.00005"
						label="Learning Rate (Tốc độ học)"
						value={form.learning_rate}
						onChange={(e) =>
							updateField(
								"learning_rate",
								parseFloat(e.target.value) || 0.0003,
							)
						}
					/>

					<Input
						type="number"
						label="Số bước tối đa (Max Iters)"
						value={form.max_iters}
						onChange={(e) =>
							updateField(
								"max_iters",
								parseInt(e.target.value, 10) || 3000,
							)
						}
					/>
				</div>

				{/* Optimizer & Checkpointing */}
				<div className="grid grid-cols-2 gap-3 items-center">
					<Select
						label="Thuật toán Optimizer"
						value={form.optimizer_type}
						onValueChange={(val) =>
							updateField("optimizer_type", val, true)
						}
						options={[
							{
								value: "adamw",
								label: "AdamW",
								description: "Weight Decay chuẩn (Khuyên dùng)",
							},
							{
								value: "8bit_adamw",
								label: "8-bit AdamW",
								description: "Giảm bộ nhớ optimizer (cần bitsandbytes)",
							},
							{
								value: "sgd",
								label: "SGD",
								description: "Stochastic Gradient Descent",
							},
						]}
					/>

					<div className="pt-4">
						<Switch
							checked={Boolean(form.gradient_checkpointing)}
							onChange={(val) =>
								updateField("gradient_checkpointing", val, true)
							}
							label="Gradient Checkpointing"
							description="Tái tính toán kích hoạt để tiết kiệm VRAM"
						/>
					</div>
				</div>
			</CardContent>
		</Card>
	);
};
