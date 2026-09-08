import React from "react";
import { cn } from "@/shared/lib";

export interface TableProps extends React.HTMLAttributes<HTMLDivElement> {
	children: React.ReactNode;
}

export const Table: React.FC<TableProps> = ({
	children,
	className,
	...props
}) => {
	return (
		<div
			className={cn(
				"rounded-xl border border-stone-300/80 shadow-warm-sm overflow-hidden bg-[#faf8f5] flex flex-col",
				className,
			)}
			{...props}
		>
			{children}
		</div>
	);
};

export interface TableHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
	tableClassName?: string;
	children: React.ReactNode;
}

export const TableHeader: React.FC<TableHeaderProps> = ({
	children,
	className,
	tableClassName,
	...props
}) => {
	return (
		<div
			className={cn(
				"border-b border-stone-300/80 bg-[#ebe8df] select-none shrink-0 overflow-hidden",
				className,
			)}
			{...props}
		>
			<table
				className={cn(
					"w-full text-left text-xs border-collapse table-fixed",
					tableClassName,
				)}
			>
				<thead>{children}</thead>
			</table>
		</div>
	);
};

export interface TableBodyProps extends React.HTMLAttributes<HTMLDivElement> {
	maxHeight?: string;
	tableClassName?: string;
	children: React.ReactNode;
}

export const TableBody: React.FC<TableBodyProps> = ({
	children,
	className,
	tableClassName,
	maxHeight = "max-h-[360px]",
	...props
}) => {
	return (
		<div
			className={cn(
				"overflow-y-auto overflow-x-hidden [scrollbar-gutter:stable]",
				maxHeight,
				className,
			)}
			{...props}
		>
			<table
				className={cn(
					"w-full text-left text-xs border-collapse table-fixed",
					tableClassName,
				)}
			>
				<tbody className="divide-y divide-stone-200/80 font-mono bg-[#faf8f5]">
					{children}
				</tbody>
			</table>
		</div>
	);
};

export interface TableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
	active?: boolean;
	highlight?: boolean;
	children: React.ReactNode;
}

export const TableRow: React.FC<TableRowProps> = ({
	children,
	className,
	active,
	highlight,
	...props
}) => {
	return (
		<tr
			className={cn(
				"hover:bg-[#f4f1e8] transition-colors",
				active && "bg-amber-50/70 hover:bg-amber-50/90",
				!active && highlight && "bg-amber-50/35 hover:bg-amber-50/55",
				className,
			)}
			{...props}
		>
			{children}
		</tr>
	);
};

export interface TableHeadProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
	align?: "left" | "center" | "right";
	children?: React.ReactNode;
}

export const TableHead: React.FC<TableHeadProps> = ({
	children,
	className,
	align = "left",
	...props
}) => {
	const alignClasses = {
		left: "text-left",
		center: "text-center",
		right: "text-right",
	};

	return (
		<th
			className={cn(
				"py-3 px-4 text-stone-700 font-mono text-[11px] font-semibold bg-[#ebe8df]",
				alignClasses[align],
				className,
			)}
			{...props}
		>
			{children}
		</th>
	);
};

export interface TableCellProps extends React.TdHTMLAttributes<HTMLTableCellElement> {
	align?: "left" | "center" | "right";
	children?: React.ReactNode;
}

export const TableCell: React.FC<TableCellProps> = ({
	children,
	className,
	align = "left",
	...props
}) => {
	const alignClasses = {
		left: "text-left",
		center: "text-center",
		right: "text-right",
	};

	return (
		<td
			className={cn(
				"py-3.5 px-4 text-xs text-stone-800",
				alignClasses[align],
				className,
			)}
			{...props}
		>
			{children}
		</td>
	);
};
