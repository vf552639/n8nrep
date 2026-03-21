import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
} from "@tanstack/react-table"
import { useState } from "react"
import { ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Loader2 } from "lucide-react"

interface ReactTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  isLoading?: boolean
  onRowClick?: (item: TData) => void
}

export function ReactTable<TData, TValue>({
  columns,
  data,
  isLoading,
  onRowClick
}: ReactTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([])

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
    initialState: {
        pagination: {
            pageSize: 50,
        }
    }
  })

  return (
    <div className="space-y-4">
      <div className="rounded-xl border overflow-hidden shadow-sm bg-white relative">
        {isLoading && (
          <div className="absolute inset-0 bg-white/50 backdrop-blur-[1px] z-10 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 border-b border-slate-200 uppercase text-xs text-slate-500">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    return (
                      <th key={header.id} className="py-3 px-4 font-semibold tracking-wider truncate">
                        {header.isPlaceholder ? null : (
                          <div
                            {...{
                              className: header.column.getCanSort()
                                ? 'cursor-pointer select-none flex items-center gap-1 hover:text-slate-900 group'
                                : '',
                              onClick: header.column.getToggleSortingHandler(),
                            }}
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            {{
                              asc: <ChevronUp className="w-4 h-4 text-blue-600" />,
                              desc: <ChevronDown className="w-4 h-4 text-blue-600" />,
                            }[header.column.getIsSorted() as string] ?? (
                              header.column.getCanSort() ? <ChevronUp className="w-4 h-4 opacity-0 group-hover:opacity-30" /> : null
                            )}
                          </div>
                        )}
                      </th>
                    )
                  })}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className={`hover:bg-slate-50/50 transition-colors group ${onRowClick ? 'cursor-pointer' : ''}`}
                    onClick={() => onRowClick && onRowClick(row.original)}
                  >
                    {row.getVisibleCells().map((cell) => {
                      const meta = cell.column.columnDef.meta as { tdClassName?: string } | undefined
                      return (
                      <td
                        key={cell.id}
                        className={`py-3 px-4 ${meta?.tdClassName ?? "whitespace-nowrap"}`}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    )})}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={table.getAllColumns().length || columns.length} className="h-32 text-center text-slate-500">
                    No results found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Pagination Controls */}
      <div className="flex items-center justify-between px-2">
        <div className="text-sm text-slate-500">
            Showing {table.getRowModel().rows.length} of {table.getFilteredRowModel().rows.length} row(s)
        </div>
        <div className="flex items-center space-x-6 text-sm">
            <div className="flex items-center space-x-2">
                <p className="font-medium text-slate-600">Rows per page</p>
                <select
                    value={table.getState().pagination.pageSize}
                    onChange={e => {
                        table.setPageSize(Number(e.target.value))
                    }}
                    className="border-slate-200 border rounded py-1 px-2 outline-none text-slate-700 focus:ring-1 focus:ring-blue-500"
                >
                    {[10, 20, 50, 100].map(pageSize => (
                        <option key={pageSize} value={pageSize}>
                            {pageSize}
                        </option>
                    ))}
                </select>
            </div>
            
            <div className="flex items-center space-x-2">
                <button
                    className="p-1.5 border border-slate-200 rounded cursor-pointer hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                >
                    <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="flex items-center gap-1 text-slate-600 font-medium px-2">
                    <div>Page</div>
                    <strong>
                        {table.getState().pagination.pageIndex + 1} of{" "}
                        {table.getPageCount() || 1}
                    </strong>
                </span>
                <button
                    className="p-1.5 border border-slate-200 rounded cursor-pointer hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                >
                    <ChevronRight className="w-4 h-4" />
                </button>
            </div>
        </div>
      </div>
    </div>
  )
}
