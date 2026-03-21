export function LoadingSpinner({ message = 'Loading…' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-10">
      <div className="h-7 w-7 animate-spin rounded-full border-[3px] border-muted border-t-primary" />
      <span className="text-sm text-muted-foreground">{message}</span>
    </div>
  )
}
