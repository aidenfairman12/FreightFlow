import { cn } from '@/lib/utils'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { EmptyState } from './EmptyState'

interface Column<T> {
  key: string
  label: string
  render?: (row: T) => React.ReactNode
  align?: 'left' | 'center' | 'right'
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  emptyMessage?: string
  maxRows?: number
  onRowClick?: (row: T) => void
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  emptyMessage = 'No data available',
  maxRows,
  onRowClick,
}: DataTableProps<T>) {
  const rows = maxRows ? data.slice(0, maxRows) : data

  if (rows.length === 0) {
    return <EmptyState message={emptyMessage} />
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map(col => (
            <TableHead
              key={col.key}
              className={cn(
                col.align === 'right' && 'text-right',
                col.align === 'center' && 'text-center'
              )}
            >
              {col.label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, i) => (
          <TableRow
            key={i}
            onClick={() => onRowClick?.(row)}
            className={onRowClick ? 'cursor-pointer' : ''}
          >
            {columns.map(col => (
              <TableCell
                key={col.key}
                className={cn(
                  col.align === 'right' && 'text-right',
                  col.align === 'center' && 'text-center'
                )}
              >
                {col.render ? col.render(row) : String(row[col.key] ?? '—')}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
