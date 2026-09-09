import React from "react";
import {
	HardwareAdvisorWidget,
	VramMatrixWidget,
	QualityGatesAuditWidget,
	ModelInspectorWidget,
	SystemLogsWidget,
} from "@/widgets";
import { PageHeader, PageContainer, useToast } from "@/shared/ui";
import { Cpu } from "lucide-react";
import type { TrainingScenarioOverrides } from "@/entities/training";

export interface DiagnosticsPageProps {
	onApplyTrainingScenario?: (scenario: TrainingScenarioOverrides) => void;
	configRevision?: number;
}

export const DiagnosticsPage: React.FC<DiagnosticsPageProps> = ({
	onApplyTrainingScenario,
	configRevision = 0,
}) => {
	const { toast } = useToast();
	return (
		<PageContainer maxWidth="standard" spacing="normal">
			{/* Unified PageHeader Component */}
			<PageHeader
				icon={<Cpu className="w-6 h-6" />}
				title="Chẩn Đoán Phần Cứng & Kiểm Toán Chất Lượng (Diagnostics & QA)"
				subtitle="Phân tích dung lượng VRAM, nhân Attention SDPA, phân bổ trọng số kiến trúc và 6 Quality Gates"
			/>

			{/* Widget 1: Hardware Advisor */}
			<HardwareAdvisorWidget />

			{/* Widget 2: VRAM Scenarios Matrix */}
			<VramMatrixWidget
				configRevision={configRevision}
				onApplyScenario={(scenario) => {
					onApplyTrainingScenario?.(scenario);
					toast("Đã áp dụng kịch bản VRAM vào cấu hình Training.", "success");
				}}
			/>

			{/* Widget 3: Model Architecture Inspector */}
			<ModelInspectorWidget configRevision={configRevision} />

			{/* Widget 4: Quality Gates Audit */}
			<QualityGatesAuditWidget />

			{/* Widget 5: Engine Logs Terminal */}
			<SystemLogsWidget />
		</PageContainer>
	);
};
