import React, { useState } from "react";
import { Drawer } from "@/shared/ui";
import { PlaygroundCanvasWidget, PlaygroundSidebarWidget } from "@/widgets";
import { usePlayground } from "./model/usePlayground";

export interface PlaygroundPageProps {
	onCheckpointLoaded?: (path: string) => void;
	activeCheckpoint?: string;
	onRegisterReset?: (resetFn: () => void) => void;
	configRevision?: number;
}

export const PlaygroundPage: React.FC<PlaygroundPageProps> = ({
	onCheckpointLoaded,
	activeCheckpoint = "",
	onRegisterReset,
	configRevision = 0,
}) => {
	const [isParamsOpen, setIsParamsOpen] = useState(false);

	const {
		prompt,
		setPrompt,
		submittedPrompt,
		checkpoints,
		selectedCheckpoint,
		setSelectedCheckpoint,
		generators,
		selectedGenerator,
		isLoadingCp,
		params,
		setParams,
		isGenerating,
		generatedText,
		stats,
		handleSelectGenerator,
		handleLoadCheckpoint,
		handleStartGenerate,
		handleClearSession,
		stop,
	} = usePlayground({ activeCheckpoint, onCheckpointLoaded, configRevision });

	// Register reset function to parent (e.g. sidebar "+ Sáng tác mới")
	React.useEffect(() => {
		if (onRegisterReset) {
			onRegisterReset(handleClearSession);
		}
	}, [onRegisterReset, handleClearSession]);

	return (
		<div className="h-full w-full flex flex-col bg-[#f4f3ed]">
			{/* Flagship ChatGPT Canvas */}
			<PlaygroundCanvasWidget
				prompt={prompt}
				onPromptChange={setPrompt}
				submittedPrompt={submittedPrompt}
				generatedText={generatedText}
				isGenerating={isGenerating}
				stats={stats}
				onGenerate={handleStartGenerate}
				onStop={stop}
				onClear={handleClearSession}
				onOpenParams={() => setIsParamsOpen(true)}
				activeCheckpoint={activeCheckpoint}
			/>

			{/* Slide-over Drawer for Model & Sampling Settings */}
			<Drawer
				isOpen={isParamsOpen}
				onClose={() => setIsParamsOpen(false)}
				title="Cài Đặt Siêu Tham Số Sinh Từ"
				subtitle="Tùy chỉnh nhiệt độ, nhân suy luận và bộ kiểm soát lặp từ"
			>
				{params ? (
					<PlaygroundSidebarWidget
						checkpoints={checkpoints}
						selectedCheckpoint={selectedCheckpoint}
						onSelectCheckpoint={setSelectedCheckpoint}
						onLoadCheckpoint={handleLoadCheckpoint}
						isLoadingCheckpoint={isLoadingCp}
						generators={generators}
						selectedGenerator={selectedGenerator}
						onSelectGenerator={handleSelectGenerator}
						params={params}
						onParamsChange={setParams}
						isGenerating={isGenerating}
					/>
				) : (
					<div className="py-10 text-center text-sm text-stone-500">
						Đang nạp cấu hình generation canonical...
					</div>
				)}
			</Drawer>
		</div>
	);
};
