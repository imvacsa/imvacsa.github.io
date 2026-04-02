/*
 * IDNT Admin Portal
 * -----------------
 * Setup:
 *   cd idnt/admin
 *   npm install
 *   npm run dev
 *
 * Opens at http://localhost:3000
 */

import StatCard from "./components/StatCard";
import FailureCard from "./components/FailureCard";
import ActivityFeed from "./components/ActivityFeed";
import QuickActions from "./components/QuickActions";

// ---------------------------------------------------------------------------
// Mock data — structured for easy API replacement
// ---------------------------------------------------------------------------

async function fetchDashboardStats() {
  // TODO: Replace with actual API call
  return {
    issuedToday: 42,
    processing: 0,
    failed: 1,
  };
}

async function fetchFailures() {
  // TODO: Replace with actual API call
  return [
    {
      id: "fail-001",
      employeeName: "박지민",
      department: "마케팅팀",
      timestamp: "2026-04-02 14:23",
      reason: "NFC 칩 인식 실패 — 재발급 필요",
      details:
        "카드 발급 프로세스 중 NFC 칩 초기화 단계에서 통신 오류가 발생했습니다. 칩 제조사 로트번호 NX-2026-0402에서 간헐적 불량이 확인되었으며, 해당 로트의 나머지 카드도 점검이 필요합니다.",
      reissueUrl: "https://idnt.app/reissue/fail-001?token=abc123",
    },
  ];
}

async function fetchRecentActivity() {
  // TODO: Replace with actual API call
  return [
    { id: "act-01", time: "14:32", employeeName: "최유진", department: "인사팀", status: "발급완료" as const },
    { id: "act-02", time: "14:28", employeeName: "정현우", department: "개발팀", status: "발급완료" as const },
    { id: "act-03", time: "14:23", employeeName: "박지민", department: "마케팅팀", status: "실패" as const },
    { id: "act-04", time: "14:15", employeeName: "김도윤", department: "디자인팀", status: "발급완료" as const },
    { id: "act-05", time: "13:58", employeeName: "이서아", department: "재무팀", status: "발급완료" as const },
    { id: "act-06", time: "13:42", employeeName: "한지호", department: "개발팀", status: "발급완료" as const },
    { id: "act-07", time: "13:30", employeeName: "오수빈", department: "기획팀", status: "발급완료" as const },
    { id: "act-08", time: "13:15", employeeName: "윤채원", department: "디자인팀", status: "발급완료" as const },
    { id: "act-09", time: "12:55", employeeName: "장민서", department: "인사팀", status: "발급완료" as const },
    { id: "act-10", time: "12:40", employeeName: "배건우", department: "개발팀", status: "발급완료" as const },
  ];
}

// ---------------------------------------------------------------------------
// Page (Server Component)
// ---------------------------------------------------------------------------

export default async function DashboardPage() {
  const [stats, failures, activities] = await Promise.all([
    fetchDashboardStats(),
    fetchFailures(),
    fetchRecentActivity(),
  ]);

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold tracking-tight">IDNT</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">관리자</span>
          <div className="h-8 w-8 rounded-full bg-white/[0.08] flex items-center justify-center text-xs text-muted">
            A
          </div>
        </div>
      </header>

      {/* Stats */}
      <section className="mt-10 grid grid-cols-3 gap-4">
        <StatCard value={stats.issuedToday} label="오늘 발급" variant="default" />
        <StatCard value={stats.processing} label="처리 중" variant="accent" />
        <StatCard value={stats.failed} label="실패" variant="error" />
      </section>

      {/* Failed Cases */}
      {failures.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-4 text-sm font-medium text-error/80">
            실패 건 ({failures.length})
          </h2>
          <div className="space-y-3">
            {failures.map((failure) => (
              <FailureCard key={failure.id} failure={failure} />
            ))}
          </div>
        </section>
      )}

      {/* Recent Activity */}
      <section className="mt-10">
        <h2 className="mb-4 text-sm font-medium text-muted">최근 발급 이력</h2>
        <ActivityFeed activities={activities} />
      </section>

      {/* Quick Actions */}
      <section className="mt-10 pb-12">
        <h2 className="mb-4 text-sm font-medium text-muted">빠른 작업</h2>
        <QuickActions />
      </section>
    </div>
  );
}
