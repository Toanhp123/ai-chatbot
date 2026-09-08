import React from "react";
import {
	TrainingMetricsRibbonWidget,
	TrainingConfigFormWidget,
	LossChartWidget,
	LiveSampleFeedWidget,
	CheckpointHubWidget,
} from "@/widgets";
import { PageContainer, useToast } from "@/shared/ui";
import { useTrainingDashboard } from "./model/useTrainingDashboard";
import type { Checkpoint } from "@/entities/checkpoint";

export interface TrainingPageProps {
	onCheckpointLoaded?: (path: string) => void;
	activeCheckpoint?: string;
}

export const TrainingPage: React.FC<TrainingPageProps> = ({
	onCheckpointLoaded,
}) => {
	const { toast } = useToast();
	const {
		status,
		currentStep,
		maxIters,
		currentLoss,
		currentValLoss,
		currentLr,
		lastSampleText,
		sampleHistory,
		historySteps,
		historyEvals,
		preflightInfo,
		form,
		setForm,
		checkFeasibility,
		isStarting,
		isStopping,
		handleStart,
		handleStop,
		handleClear,
		resumeTarget,
		handleSelectResume,
		handleCancelResume,
	} = useTrainingDashboard();

	const onResumeSelected = (cp: Checkpoint) => {
		handleSelectResume(cp);
		if (cp.path) {
			toast(
				`Đã kích hoạt chế độ Resume từ ${cp.filename}${cp.step ? ` (bước ${cp.step.toLocaleString()})` : ""}. Nhấn 'Tiếp Tục Huấn Luyện' ở trên để chạy tiếp!`,
				"info",
			);
			window.scrollTo({ top: 0, behavior: "smooth" });
		} else {
			toast(
				"Đã hủy chế độ Resume, quay về huấn luyện mới từ đầu.",
				"info",
			);
		}
	};

	return (
		<PageContainer maxWidth="standard" spacing="normal">
			{/* Top Metrics & Status Ribbon Widget */}
			<TrainingMetricsRibbonWidget
				status={status}
				currentStep={currentStep}
				maxIters={maxIters}
				currentLoss={currentLoss}
				currentValLoss={currentValLoss}
				currentLr={currentLr}
				preflightInfo={preflightInfo}
				isStarting={isStarting}
				isStopping={isStopping}
				onStart={handleStart}
				onStop={handleStop}
				onClear={handleClear}
				resumeTarget={resumeTarget}
				onCancelResume={handleCancelResume}
			/>

			{/* Section 2: Real-time Loss Curves & Hyperparameter Configuration */}
			<div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
				{/* Left Column (7 Cols): Real-time Loss Curves */}
				<div className="lg:col-span-7 flex flex-col">
					<LossChartWidget
						historySteps={historySteps}
						historyEvals={historyEvals}
						currentLr={currentLr}
					/>
				</div>

				{/* Right Column (5 Cols): Training Config Form */}
				<div className="lg:col-span-5 flex flex-col">
					<TrainingConfigFormWidget
						form={form}
						onFormChange={setForm}
						onCheckFeasibility={checkFeasibility}
						preflightInfo={preflightInfo}
					/>
				</div>
			</div>

			{/* Section 3: Live Qualitative Output Evaluation */}
			<LiveSampleFeedWidget
				lastSampleText={lastSampleText}
				sampleHistory={sampleHistory}
				onSelectSample={(text) =>
					alert(`Đã chọn mẫu đầu ra: \n${text}`)
				}
			/>

			{/* Section 4: Checkpoint Artifact Hub (Full Width Table) */}
			<CheckpointHubWidget
				onSelectCheckpoint={(cp) => {
					onCheckpointLoaded?.(cp.path);
				}}
				activeResumePath={resumeTarget?.path}
				onSelectResume={onResumeSelected}
			/>
		</PageContainer>
	);
};
