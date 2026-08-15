export function TableSkeleton() {
  return (
    <div className="animate-pulse divide-y divide-border/60">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="p-6 flex items-center justify-between gap-4">
          <div className="space-y-2 flex-1">
            <div className="h-4 bg-surface-raised rounded w-1/3" />
            <div className="h-3 bg-surface-raised rounded w-1/4" />
          </div>
          <div className="h-6 bg-surface-raised rounded-full w-24" />
          <div className="h-6 bg-surface-raised rounded w-32 hidden md:block" />
          <div className="h-8 bg-surface-raised rounded-lg w-20" />
        </div>
      ))}
    </div>
  );
}

export function ReviewDetailSkeleton() {
  return (
    <div className="animate-pulse space-y-6 max-w-5xl mx-auto pt-8">
      <div className="h-6 bg-surface-raised rounded w-32" />
      <div className="p-6 rounded-xl border border-border bg-surface space-y-4">
        <div className="h-8 bg-surface-raised rounded w-2/3" />
        <div className="h-4 bg-surface-raised rounded w-1/2" />
        <div className="h-20 bg-surface-raised rounded" />
      </div>
      <div className="space-y-4">
        <div className="h-32 bg-surface rounded-xl border border-border" />
        <div className="h-32 bg-surface rounded-xl border border-border" />
      </div>
    </div>
  );
}
