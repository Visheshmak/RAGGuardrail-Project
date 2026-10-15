import React from "react";
import { Loader2, AlertCircle, Inbox } from "lucide-react";

export function LoadingState({ message = "Loading data..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <Loader2 className="h-8 w-8 text-indigo-500 animate-spin mb-3" />
      <p className="text-sm font-medium text-slate-400">{message}</p>
    </div>
  );
}

export function ErrorState({
  title = "Failed to load data",
  message = "An error occurred while communicating with the backend API.",
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center max-w-md mx-auto">
      <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mb-4 text-rose-400">
        <AlertCircle className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold text-slate-200 mb-1">{title}</h3>
      <p className="text-sm text-slate-400 mb-5">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  icon: Icon = Inbox,
  title = "No data found",
  description = "Get started by creating a new entry or running an evaluation.",
  action,
}: {
  icon?: React.ElementType;
  title?: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center max-w-md mx-auto">
      <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mb-4 text-slate-400 shadow-inner">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold text-slate-200 mb-1">{title}</h3>
      <p className="text-sm text-slate-400 mb-6">{description}</p>
      {action}
    </div>
  );
}
