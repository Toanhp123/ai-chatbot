import React from "react";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	Button,
	Slider,
	Switch,
	Select,
	Input,
} from "@/shared/ui";
import type { Checkpoint } from "@/entities/checkpoint";
import type { SamplingHyperparams } from "@/features/generate";
import { Cpu, Sliders } from "lucide-react";

export type { SamplingHyperparams };

export interface PlaygroundSidebarWidgetProps {
	checkpoints: Checkpoint[];
	selectedCheckpoint: string;
	onSelectCheckpoint: (path: string) => void;
	onLoadCheckpoint: () => void;
	isLoadingCheckpoint?: boolean;
	generators: string[];
	selectedGenerator: string;
	onSelectGenerator: (gen: string) => void;
	params: SamplingHyperparams;
	onParamsChange: (newParams: SamplingHyperparams) => void;
	isGenerating?: boolean;
}

export const PlaygroundSidebarWidget: React.FC<
	PlaygroundSidebarWidgetProps
> = ({
	checkpoints,
	selectedCheckpoint,
	onSelectCheckpoint,
	onLoadCheckpoint,
	isLoadingCheckpoint = false,
	generators,
	selectedGenerator,
	onSelectGenerator,
	params,
	onParamsChange,
	isGenerating = false,
}) => {
	const updateParam = <K extends keyof SamplingHyperparams>(
		key: K,
		value: SamplingHyperparams[K],
	) => {
		onParamsChange({ ...params, [key]: value });
	};

	const checkpointOptions = (checkpoints || []).map((cp) => ({
		value: cp.path,
		label: cp.filename || cp.name || cp.path,
		description: `Val Loss: ${
			cp.val_loss !== undefined && cp.val_loss !== null && cp.val_loss > 0
				? cp.val_loss.toFixed(3)
				: "---"
		}`,
	}));

	return (
		<div className="space-y-4">
			{/* Model & Backend Selector Card */}
			<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
				<CardHeader className="pb-3 border-b border-stone-200/80">
					<CardTitle className="text-xs text-stone-900 flex items-center gap-2">
						<Cpu className="w-4 h-4 text-amber-600" />
						<span>Mô Hình & Nhân Sinh Văn Bản</span>
					</CardTitle>
				</CardHeader>
				<CardContent className="pt-4 space-y-3.5">
					{/* Checkpoint Dropdown */}
					<div>
						<Select
							label="Checkpoint đã lưu:"
							value={selectedCheckpoint}
							onValueChange={onSelectCheckpoint}
							placeholder="Chưa có checkpoint nào"
							disabled={checkpoints.length === 0}
							options={checkpointOptions}
						/>
						<Button
							size="sm"
							variant="outline"
							onClick={onLoadCheckpoint}
							disabled={
								!selectedCheckpoint ||
								isGenerating ||
								isLoadingCheckpoint
							}
							isLoading={isLoadingCheckpoint}
							className="w-full mt-2 h-8 text-xs border-stone-300/80 text-stone-800 hover:bg-[#f4f3ed]"
						>
							Nạp Checkpoint Này
						</Button>
					</div>

					{/* Generator Backend Selector */}
					<div>
						<label className="block text-xs font-medium text-stone-700 mb-1.5">
							Bộ xử lý (Generator Backend):
						</label>
						<div className="grid grid-cols-3 gap-1.5">
							{generators.map((gen) => (
								<button
									key={gen}
									type="button"
									onClick={() => onSelectGenerator(gen)}
									className={`px-2 py-1.5 rounded-lg text-xs font-medium font-mono capitalize transition-all ${
										selectedGenerator === gen
											? "bg-amber-600 text-white shadow-warm-sm"
											: "bg-[#f4f3ed] border border-stone-300/80 text-stone-700 hover:text-stone-900 hover:bg-[#ebe8df]"
									}`}
								>
									{gen}
								</button>
							))}
						</div>
					</div>
				</CardContent>
			</Card>

			{/* Hyperparameters Card */}
			<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
				<CardHeader className="pb-3 border-b border-stone-200/80 flex flex-row items-center justify-between">
					<CardTitle className="text-xs text-stone-900 flex items-center gap-2">
						<Sliders className="w-4 h-4 text-emerald-600" />
						<span>Siêu Tham Số Sinh Văn Bản (Sampling)</span>
					</CardTitle>
				</CardHeader>

				<CardContent className="pt-4 space-y-4 text-xs">
					{/* Temperature Slider */}
					<Slider
						label="Temperature (Độ phong phú)"
						min={0.1}
						max={2.0}
						step={0.05}
						value={params.temperature}
						onChange={(val) => updateParam("temperature", val)}
						valueDisplay={
							typeof params.temperature === "number"
								? params.temperature.toFixed(2)
								: "0.80"
						}
					/>

					{/* Top-P Slider */}
					<Slider
						label="Top-P (Nucleus Sampling)"
						min={0.1}
						max={1.0}
						step={0.05}
						value={params.topP}
						onChange={(val) => updateParam("topP", val)}
						valueDisplay={
							typeof params.topP === "number"
								? params.topP.toFixed(2)
								: "0.90"
						}
					/>

					{/* Min-P Slider */}
					<Slider
						label="Min-P Truncation"
						min={0.0}
						max={0.5}
						step={0.01}
						value={params.minP}
						onChange={(val) => updateParam("minP", val)}
						valueDisplay={
							typeof params.minP === "number"
								? params.minP.toFixed(2)
								: "0.05"
						}
					/>

					{/* Top-K Slider */}
					<Slider
						label="Top-K"
						min={0}
						max={100}
						step={5}
						value={params.topK}
						onChange={(val) => updateParam("topK", val)}
					/>

					{/* Repetition Penalty Slider */}
					<Slider
						label="Repetition Penalty (Khử lặp)"
						min={1.0}
						max={2.0}
						step={0.05}
						value={params.repetitionPenalty}
						onChange={(val) =>
							updateParam("repetitionPenalty", val)
						}
						valueDisplay={
							typeof params.repetitionPenalty === "number"
								? params.repetitionPenalty.toFixed(2)
								: "1.10"
						}
					/>

					{/* Max New Tokens Slider */}
					<Slider
						label="Max Tokens"
						min={16}
						max={512}
						step={16}
						value={params.maxNewTokens}
						onChange={(val) => updateParam("maxNewTokens", val)}
					/>

					{/* KV Cache Switch */}
					<div className="pt-2 border-t border-stone-200/80">
						<Switch
							checked={params.useCache}
							onChange={(val) => updateParam("useCache", val)}
							label="KV Cache Acceleration"
							description="Tăng tốc suy luận tự hồi quy"
						/>
					</div>

					{/* Stop Words */}
					<Input
						label="Từ dừng (Stop Words, cách nhau bằng phẩy):"
						value={params.stopWords}
						onChange={(e) =>
							updateParam("stopWords", e.target.value)
						}
						placeholder="###, \n\n"
					/>
				</CardContent>
			</Card>
		</div>
	);
};
