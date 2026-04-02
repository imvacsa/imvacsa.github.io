"use client";

import { useState } from "react";
import { AlertCircle, ChevronDown, ChevronUp, Copy, Check } from "lucide-react";

interface FailureData {
  id: string;
  employeeName: string;
  department: string;
  timestamp: string;
  reason: string;
  details: string;
  reissueUrl: string;
}

interface FailureCardProps {
  failure: FailureData;
}

export default function FailureCard({ failure }: FailureCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(failure.reissueUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for environments without clipboard API
      const textarea = document.createElement("textarea");
      textarea.value = failure.reissueUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="rounded-xl border border-error/20 bg-error/[0.04] p-5 transition-all duration-200">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-error" />
          <div>
            <p className="text-sm font-medium text-white">
              {failure.employeeName}
              <span className="ml-2 text-muted">{failure.department}</span>
            </p>
            <p className="mt-1 text-xs text-muted">{failure.timestamp}</p>
            <p className="mt-2 text-sm text-error/80">{failure.reason}</p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={handleCopyLink}
            className="flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-xs text-muted transition-all duration-150 hover:border-white/[0.15] hover:text-white"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 text-success" />
                복사됨
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                재발급 링크 복사
              </>
            )}
          </button>

          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-xs text-muted transition-all duration-150 hover:border-white/[0.15] hover:text-white"
          >
            상세 보기
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 border-t border-white/[0.06] pt-4">
          <p className="text-xs leading-relaxed text-muted">{failure.details}</p>
        </div>
      )}
    </div>
  );
}
