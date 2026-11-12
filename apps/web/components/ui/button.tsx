import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-400 disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        outline: "border border-border bg-card hover:bg-muted",
        ghost: "hover:bg-muted text-muted-foreground hover:text-foreground",
      },
      size: { default: "h-9 px-4", sm: "h-8 px-3 text-xs", icon: "h-9 w-9" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);
function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}
export { Button, buttonVariants };
