import React from "react";

interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (item: T) => React.ReactNode;
}

interface Props<T> {
  columns: Column<T>[];
  data: T[];
  isLoading?: boolean;
  onRowClick?: (item: T) => void;
}

export default function DataTable<T>({ columns, data, isLoading, onRowClick }: Props<T>) {
  if (isLoading) {
    return <div className="p-8 text-center text-slate-500 bg-white border rounded-lg shadow-sm">Loading data...</div>;
  }

  if (!data || data.length === 0) {
    return <div className="p-8 text-center text-slate-500 border rounded-lg bg-white shadow-sm">No results found.</div>;
  }

  return (
    <div className="overflow-x-auto border rounded-lg bg-white shadow-sm">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b">
          <tr>
            {columns.map((col, i) => (
              <th key={String(col.key) + i} className="px-6 py-3 font-medium">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {data.map((item, rowIndex) => (
            <tr 
              key={rowIndex} 
              className={`last:border-0 hover:bg-slate-50 transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
              onClick={() => onRowClick && onRowClick(item)}
            >
              {columns.map((col, colIndex) => (
                <td key={String(col.key) + colIndex} className="px-6 py-4 whitespace-nowrap">
                  {col.render ? col.render(item) : String(item[col.key as keyof T] || '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
