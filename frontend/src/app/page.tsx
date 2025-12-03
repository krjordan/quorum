"use client";

import { ChatInterface } from "@/components/chat/ChatInterface";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <header className="mb-8 text-center">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Quorum
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              AI-Powered Chat Interface
            </p>
          </header>
          <ChatInterface />
        </div>
      </div>
    </main>
  );
}
