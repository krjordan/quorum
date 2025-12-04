/**
 * StatSection Component
 * Reusable wrapper for sidebar sections with title and children
 */
'use client';

interface StatSectionProps {
  title: string;
  children: React.ReactNode;
}

export function StatSection({ title, children }: StatSectionProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        {title}
      </h3>
      <div className="space-y-2">
        {children}
      </div>
    </div>
  );
}
