import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cn } from "@/lib/utils"

const Button = React.forwardRef<HTMLButtonElement, any>(
  ({ className, variant = "default", size = "default", asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(
          "inline-flex items-center justify-center rounded-full text-sm font-bold transition-all focus-visible:outline-none active:scale-95 disabled:opacity-50",
          variant === "default" && "bg-primary text-bg hover:brightness-110 shadow-lg shadow-primary/20",
          variant === "outline" && "border-2 border-primary/30 bg-transparent text-primary hover:bg-primary/10",
          variant === "ghost" && "hover:bg-surface2 text-textMuted hover:text-textMain",
          size === "default" && "h-11 px-6 py-2",
          size === "sm" && "h-9 px-4",
          size === "lg" && "h-14 px-10 text-base",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"
export { Button }
