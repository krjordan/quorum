"use client";

import { useEffect, useState } from "react";
import { chatApi } from "@/lib/api/chat-api";
import { Badge } from "@/components/ui/badge";

export function BackendStatus() {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await chatApi.healthCheck();
        setIsHealthy(true);
      } catch {
        setIsHealthy(false);
      } finally {
        setIsChecking(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10s

    return () => clearInterval(interval);
  }, []);

  if (isChecking) {
    return (
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="gap-2">
          <div className="w-2 h-2 rounded-full bg-muted-foreground animate-pulse" />
          Checking backend...
        </Badge>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {isHealthy ? (
        <Badge variant="default" className="gap-2 bg-green-500 hover:bg-green-600">
          <div className="w-2 h-2 rounded-full bg-white" />
          Backend connected
        </Badge>
      ) : (
        <Badge variant="destructive" className="gap-2">
          <div className="w-2 h-2 rounded-full bg-white" />
          Backend disconnected - Run: <code className="bg-background/20 px-1 rounded">./scripts/dev.sh</code>
        </Badge>
      )}
    </div>
  );
}
