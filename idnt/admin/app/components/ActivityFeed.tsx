"use client";

interface ActivityItem {
  id: string;
  time: string;
  employeeName: string;
  department: string;
  status: "발급완료" | "처리중" | "실패";
}

interface ActivityFeedProps {
  activities: ActivityItem[];
}

const statusStyles = {
  "발급완료": "bg-success/10 text-success",
  "처리중": "bg-accent/10 text-accent",
  "실패": "bg-error/10 text-error",
};

export default function ActivityFeed({ activities }: ActivityFeedProps) {
  return (
    <div className="space-y-1">
      {activities.map((activity) => (
        <div
          key={activity.id}
          className="flex items-center justify-between rounded-lg px-4 py-3 transition-colors duration-150 hover:bg-white/[0.02]"
        >
          <div className="flex items-center gap-6">
            <span className="tabular-nums text-xs text-muted w-14 shrink-0">
              {activity.time}
            </span>
            <span className="text-sm text-white">
              {activity.employeeName}
            </span>
            <span className="text-sm text-muted">
              {activity.department}
            </span>
          </div>
          <span
            className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${statusStyles[activity.status]}`}
          >
            {activity.status}
          </span>
        </div>
      ))}
    </div>
  );
}
