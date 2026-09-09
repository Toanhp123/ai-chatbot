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
import type { TrainingScenarioUpdate } from "@/entities/training";

export interface TrainingPageProps {
	onCheckpointLoaded?: (path: string) => void;
	activeCheckpoint?: string;
	configRevision?: number;
	trainingScenario?: TrainingScenarioUpdate | null;
}

export const TrainingPage: React.FC<TrainingPageProps> = ({
	onCheckpointLoaded,
	configRevision = 0,
	trainingScenario = null,
}) => {
	const { toast } = useToast();
	const {
		status,
		terminationReason,
		errorMessage,
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
		configLoadError,
		form,
		setForm,
		checkFeasibility,
		isStarting,
		isStartDisabled,
		isStopping,
		handleStart,
		handleStop,
		handleClear,
		resumeTarget,
		handleSelectResume,
		handleCancelResume,
	} = useTrainingDashboard(configRevision, trainingScenario);

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
				terminationReason={terminationReason}
				errorMessage={errorMessage}
				currentStep={currentStep}
				maxIters={maxIters}
				currentLoss={currentLoss}
				currentValLoss={currentValLoss}
				currentLr={currentLr}
				preflightInfo={preflightInfo}
				isStarting={isStarting}
				isStartDisabled={isStartDisabled}
				configLoadError={configLoadError}
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
					{form ? (
						<TrainingConfigFormWidget
							form={form}
							onFormChange={setForm}
							onCheckFeasibility={checkFeasibility}
							preflightInfo={preflightInfo}
						/>
					) : (
						<div className="h-full min-h-64 rounded-xl border border-stone-300/80 bg-[#faf8f5] flex items-center justify-center text-sm text-stone-500">
							Đang nạp cấu hình training canonical...
						</div>
					)}
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
				configRevision={configRevision}
				onSelectCheckpoint={(cp) => {
					onCheckpointLoaded?.(cp.path);
				}}
				activeResumePath={resumeTarget?.path}
				onSelectResume={onResumeSelected}
			/>
		</PageContainer>
	);
};
