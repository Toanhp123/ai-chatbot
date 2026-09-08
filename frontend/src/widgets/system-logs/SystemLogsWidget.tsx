import React from "react";
import {
	Card,
	CardHeader,
	CardTitle,
	CardContent,
	Button,
	Switch,
	Select,
} from "@/shared/ui";
import { useSystemLogs } from "./model/useSystemLogs";
import { Terminal, RefreshCw, Copy, Check, Pause, Play } from "lucide-react";

export const SystemLogsWidget: React.FC = () => {
	const {
		logs,
		loading,
		autoRefresh,
		setAutoRefresh,
		autoScroll,
		setAutoScroll,
		lineCount,
		setLineCount,
		copied,
		logFile,
		logContainerRef,
		fetchLogs,
		handleCopy,
	} = useSystemLogs();

	const formatLogLine = (line: string, index: number) => {
		let colorClass = "text-stone-300";
		if (line.includes("ERROR") || line.includes("CRITICAL")) {
			colorClass = "text-rose-400 font-semibold";
		} else if (line.includes("WARNING")) {
			colorClass = "text-amber-400";
		} else if (line.includes("INFO")) {
			colorClass = "text-sky-300";
		} else if (line.includes("SUCCESS") || line.includes("PASSED")) {
			colorClass = "text-emerald-400";
		}

		return (
			<div
				key={index}
				className={`font-mono text-[11px] leading-5 ${colorClass}`}
			>
				<span className="text-stone-500 select-none mr-2">
					{String(index + 1).padStart(3, " ")}
				</span>
				<span>{line}</span>
			</div>
		);
	};

	return (
		<Card className="border-stone-300/80 bg-[#faf8f5] shadow-warm-sm">
			<CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-stone-200/80">
				<div className="flex items-center gap-3">
					<div className="p-2 rounded-lg bg-amber-50 border border-amber-200/80 text-amber-700">
						<Terminal className="w-5 h-5" />
					</div>
					<div>
						<CardTitle className="text-base text-stone-900 flex items-center gap-2">
							Nhật Ký Động Cơ Hệ Thống (Engine Logs)
						</CardTitle>
						<p className="text-xs text-stone-500 mt-0.5">
							Theo dõi trực tiếp stdout/stderr và sự kiện từ{" "}
							<span className="font-mono text-stone-700">
								{logFile}
							</span>
						</p>
					</div>
				</div>

				<div className="flex items-center gap-2">
					{/* Auto Refresh Toggle */}
					<Button
						size="sm"
						variant="outline"
						onClick={() => setAutoRefresh(!autoRefresh)}
						className={`h-8 text-xs ${autoRefresh ? "border-emerald-500/50 text-emerald-700 bg-emerald-50/50" : "text-stone-500 border-stone-300/80"}`}
					>
						{autoRefresh ? (
							<>
								<Pause className="w-3.5 h-3.5 mr-1" /> Auto-sync
								ON
							</>
						) : (
							<>
								<Play className="w-3.5 h-3.5 mr-1" /> Auto-sync
								OFF
							</>
						)}
					</Button>

					{/* Copy Button */}
					<Button
						size="sm"
						variant="outline"
						onClick={handleCopy}
						disabled={logs.length === 0}
						className="h-8 text-xs text-stone-700 border-stone-300/80 shadow-warm-sm"
					>
						{copied ? (
							<>
								<Check className="w-3.5 h-3.5 mr-1 text-emerald-600" />{" "}
								Đã chép
							</>
						) : (
							<>
								<Copy className="w-3.5 h-3.5 mr-1" /> Sao chép
							</>
						)}
					</Button>

					{/* Manual Refresh */}
					<Button
						size="sm"
						variant="outline"
						onClick={fetchLogs}
						className="h-8 text-xs text-stone-700 border-stone-300/80 shadow-warm-sm"
					>
						<RefreshCw
							className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
						/>
					</Button>
				</div>
			</CardHeader>

			<CardContent className="pt-4">
				{/* Unified Flat macOS Terminal Window */}
				<div className="rounded-xl overflow-hidden border border-stone-800 bg-[#181716] shadow-warm-md">
					{/* Flat macOS Terminal Header Bar */}
					<div className="flex items-center justify-between px-4 py-2.5 bg-[#24221f] border-b border-stone-800 text-xs select-none">
						<div className="flex items-center gap-3">
							{/* macOS 3 Traffic Light Dots */}
							<div className="flex items-center gap-1.5">
								<span className="w-3 h-3 rounded-full bg-[#ff5f56] inline-block shadow-sm"></span>
								<span className="w-3 h-3 rounded-full bg-[#ffbd2e] inline-block shadow-sm"></span>
								<span className="w-3 h-3 rounded-full bg-[#27c93f] inline-block shadow-sm"></span>
							</div>
							<span className="ml-1 font-mono text-[11px] text-stone-300 font-medium tracking-tight">
								{logFile || "logs/train.log"}
							</span>
						</div>

						<div className="flex items-center gap-3 text-[11px]">
							<Switch
								checked={autoScroll}
								onChange={setAutoScroll}
								label="Cuộn tự động"
								labelClassName="text-[11px] text-stone-300 group-hover:text-stone-100 font-medium"
							/>

							<div className="w-28">
								<Select
									value={String(lineCount)}
									onValueChange={(val) =>
										setLineCount(Number(val))
									}
									triggerClassName="h-7 py-0.5 px-2.5 text-[11px] bg-[#1a1918] border-stone-700/80 text-stone-200 hover:border-stone-600 focus:border-amber-500/50"
									options={[
										{ value: "50", label: "50 dòng" },
										{ value: "80", label: "80 dòng" },
										{ value: "150", label: "150 dòng" },
										{ value: "300", label: "300 dòng" },
									]}
								/>
							</div>
						</div>
					</div>

					{/* Log Box */}
					<div
						ref={logContainerRef}
						className="p-4 bg-[#181716] min-h-[220px] max-h-[420px] overflow-y-auto font-mono text-xs space-y-0.5 selection:bg-amber-500/30 text-stone-200 [scrollbar-gutter:stable]"
					>
						{logs.length > 0 ? (
							logs.map((line, idx) => formatLogLine(line, idx))
						) : (
							<div className="py-14 flex flex-col items-center justify-center text-center space-y-2.5">
								<div className="p-3 rounded-2xl bg-stone-800/80 border border-stone-700/60 text-stone-400 shadow-inner">
									<Terminal className="w-5 h-5 text-stone-400" />
								</div>
								<div className="text-xs font-semibold text-stone-300">
									Chưa phát sinh nhật ký ghi chép
								</div>
								<p className="text-[11px] text-stone-500 max-w-sm">
									Các tác vụ huấn luyện và chẩn đoán sẽ liên
									tục ghi log vào tệp này.
								</p>
							</div>
						)}
					</div>
				</div>
			</CardContent>
		</Card>
	);
};
