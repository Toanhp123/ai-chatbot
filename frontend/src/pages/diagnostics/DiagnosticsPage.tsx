import React from "react";
import {
	HardwareAdvisorWidget,
	VramMatrixWidget,
	QualityGatesAuditWidget,
	ModelInspectorWidget,
	SystemLogsWidget,
} from "@/widgets";
import { PageHeader, PageContainer } from "@/shared/ui";
import { Cpu } from "lucide-react";

export const DiagnosticsPage: React.FC = () => {
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
				onApplyScenario={(scenario) => {
					alert(
						`Đã áp dụng kịch bản:\n- Batch Size: ${scenario.batch_size}\n- Precision: ${scenario.precision}\n- Gradient Checkpointing: ${scenario.gradient_checkpointing}`,
					);
				}}
			/>

			{/* Widget 3: Model Architecture Inspector */}
			<ModelInspectorWidget />

			{/* Widget 4: Quality Gates Audit */}
			<QualityGatesAuditWidget />

			{/* Widget 5: Engine Logs Terminal */}
			<SystemLogsWidget />
		</PageContainer>
	);
};
