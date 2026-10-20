import React from 'react';

interface DataTableProps {
  title?: React.ReactNode;
  columns: any[];
  data?: any[];
  actionButton?: React.ReactNode;
  isLoading?: boolean;
}

export default function DataTable({ title, columns, data = [], actionButton, isLoading = false }: DataTableProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col h-full">
      <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-white sticky top-0 z-10">
        <h2 className="font-bold text-lg text-slate-800">{title}</h2>
        {actionButton && (
          <div>{actionButton}</div>
        )}
      </div>
      
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-slate-50 text-slate-500 sticky top-0 z-10 border-b border-slate-100">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className="px-5 py-3 font-medium">
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td colSpan={columns.length} className="p-8 text-center text-slate-400">
                  <div className="animate-pulse flex flex-col items-center gap-2">
                    <div className="h-4 w-32 bg-slate-200 rounded"></div>
                    <div className="h-3 w-48 bg-slate-100 rounded"></div>
                  </div>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="p-12 text-center">
                  <p className="text-slate-500 font-medium text-base mb-1">No Data Available</p>
                  <p className="text-slate-400 text-sm">There are no records to display at this time.</p>
                </td>
              </tr>
            ) : (
              data.map((row, rowIdx) => (
                <tr key={row.id || rowIdx} className="hover:bg-slate-50/50 transition duration-150">
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} className={`px-5 py-4 ${col.className || 'text-slate-700'}`}>
                      {col.render ? col.render(row) : row[col.accessor]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
