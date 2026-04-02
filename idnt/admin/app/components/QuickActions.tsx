"use client";

import { useState } from "react";
import { Palette, Shield, Ban, Download, X, Search } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";

export default function QuickActions() {
  const [designOpen, setDesignOpen] = useState(false);
  const [accessOpen, setAccessOpen] = useState(false);
  const [deactivateOpen, setDeactivateOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const handleDownload = () => {
    // Mock CSV download
    const csvContent =
      "이름,부서,발급일,상태\n김서연,디자인팀,2026-04-02,발급완료\n이준호,개발팀,2026-04-02,발급완료\n박지민,마케팅팀,2026-04-02,실패\n";
    const blob = new Blob(["\uFEFF" + csvContent], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `idnt_이력_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const actions = [
    {
      label: "카드 디자인 설정",
      icon: Palette,
      onClick: () => setDesignOpen(true),
    },
    {
      label: "출입 권한 그룹",
      icon: Shield,
      onClick: () => setAccessOpen(true),
    },
    {
      label: "카드 비활성화",
      icon: Ban,
      onClick: () => setDeactivateOpen(true),
    },
    {
      label: "이력 다운로드",
      icon: Download,
      onClick: handleDownload,
    },
  ];

  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={action.onClick}
            className="group flex flex-col items-center gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.02] px-4 py-6 transition-all duration-200 hover:border-white/[0.12] hover:bg-white/[0.05]"
          >
            <action.icon className="h-5 w-5 text-muted transition-colors duration-200 group-hover:text-white" />
            <span className="text-xs text-muted transition-colors duration-200 group-hover:text-white">
              {action.label}
            </span>
          </button>
        ))}
      </div>

      {/* Card Design Modal */}
      <Dialog.Root open={designOpen} onOpenChange={setDesignOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-white/[0.08] bg-[#0a0a0a] p-8 shadow-2xl">
            <div className="flex items-center justify-between">
              <Dialog.Title className="text-lg font-semibold">카드 디자인 설정</Dialog.Title>
              <Dialog.Close className="rounded-lg p-1.5 text-muted transition-colors hover:bg-white/[0.06] hover:text-white">
                <X className="h-4 w-4" />
              </Dialog.Close>
            </div>
            <p className="mt-4 text-sm text-muted">
              카드 디자인 설정 기능은 준비 중입니다. 곧 업데이트될 예정입니다.
            </p>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Access Groups Modal */}
      <Dialog.Root open={accessOpen} onOpenChange={setAccessOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-white/[0.08] bg-[#0a0a0a] p-8 shadow-2xl">
            <div className="flex items-center justify-between">
              <Dialog.Title className="text-lg font-semibold">출입 권한 그룹</Dialog.Title>
              <Dialog.Close className="rounded-lg p-1.5 text-muted transition-colors hover:bg-white/[0.06] hover:text-white">
                <X className="h-4 w-4" />
              </Dialog.Close>
            </div>
            <p className="mt-4 text-sm text-muted">
              출입 권한 그룹 관리 기능은 준비 중입니다. 곧 업데이트될 예정입니다.
            </p>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Deactivate Card Modal */}
      <Dialog.Root open={deactivateOpen} onOpenChange={setDeactivateOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-white/[0.08] bg-[#0a0a0a] p-8 shadow-2xl">
            <div className="flex items-center justify-between">
              <Dialog.Title className="text-lg font-semibold">카드 비활성화</Dialog.Title>
              <Dialog.Close className="rounded-lg p-1.5 text-muted transition-colors hover:bg-white/[0.06] hover:text-white">
                <X className="h-4 w-4" />
              </Dialog.Close>
            </div>
            <div className="mt-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                <input
                  type="text"
                  placeholder="직원 이름 또는 사번으로 검색..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-xl border border-white/[0.08] bg-white/[0.04] py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-muted/60 focus:border-accent/40 focus:outline-none focus:ring-1 focus:ring-accent/20"
                />
              </div>
              {searchQuery && (
                <div className="mt-4 space-y-2">
                  <p className="text-xs text-muted">검색 결과가 없습니다.</p>
                </div>
              )}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
