import * as React from "react";

import { cn } from "../../lib/utils";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const { className, ...rest } = props;
  return (
    <input
      className={cn(
        "h-9 rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:border-info/50 focus:ring-2 focus:ring-info/15",
        className
      )}
      {...rest}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  const { className, ...rest } = props;
  return (
    <select
      className={cn(
        "h-9 rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-info/50 focus:ring-2 focus:ring-info/15",
        className
      )}
      {...rest}
    />
  );
}
