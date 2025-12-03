import type { Message } from "@/types/chat";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <Card
        className={cn(
          "max-w-[80%] px-4 py-2",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        )}
      >
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <div className="text-sm font-medium mb-1">
              {isUser ? "You" : "Assistant"}
            </div>
            <div className="text-sm whitespace-pre-wrap">
              {message.content || (
                <span className="text-muted-foreground italic">Thinking...</span>
              )}
              {message.isStreaming && (
                <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
              )}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
