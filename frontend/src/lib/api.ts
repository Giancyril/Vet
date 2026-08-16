const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export interface ReviewMetrics {
  total_findings: number;
  blocking_count: number;
  suggestion_count: number;
  nitpick_count: number;
  processing_duration_ms: number;
}

export interface ReviewSummary {
  id: string;
  repository_id: string;
  repo_full_name?: string;
  pr_number: number;
  pr_title: string;
  pr_author: string;
  head_sha: string;
  base_sha: string;
  verdict: "APPROVE" | "COMMENT" | "REQUEST_CHANGES";
  summary_markdown: string;
  metrics: ReviewMetrics;
  created_at: string;
}

export interface Finding {
  id: string;
  review_id: string;
  file_path: string;
  line_number: number;
  side: string;
  severity: "blocking" | "suggestion" | "nitpick";
  category: string;
  title: string;
  explanation: string;
  suggested_fix?: string;
  github_comment_id?: number;
  is_resolved: boolean;
  is_breaking_change?: boolean;
  cyclomatic_complexity?: number;
  created_at: string;
}

export interface ReviewDetail extends ReviewSummary {
  findings: Finding[];
}

export interface RepoConfigData {
  id?: string;
  min_severity: "blocking" | "suggestion" | "nitpick";
  auto_request_changes: boolean;
  enabled_categories: string[];
  max_comments_per_pr: number;
  custom_instructions?: string;
}

export interface Repository {
  id: string;
  installation_id: string;
  github_repo_id: number;
  name: string;
  full_name: string;
  owner_name: string;
  private: boolean;
  default_branch: string;
  is_active: boolean;
  created_at: string;
  total_reviews_count: number;
  config?: RepoConfigData;
}

export interface DashboardStats {
  total_reviews: number;
  total_blocking_prevented: number;
  total_suggestions_made: number;
  total_nitpicks: number;
  total_findings: number;
  avg_duration_ms: number;
  active_repositories_count: number;
}

export async function fetchStats(): Promise<DashboardStats> {
  try {
    const res = await fetch(`${API_BASE}/stats`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return {
      total_reviews: 0,
      total_blocking_prevented: 0,
      total_suggestions_made: 0,
      total_nitpicks: 0,
      total_findings: 0,
      avg_duration_ms: 0,
      active_repositories_count: 0,
    };
  }
}

export async function fetchReviews(): Promise<ReviewSummary[]> {
  try {
    const res = await fetch(`${API_BASE}/reviews`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchReviewDetail(id: string): Promise<ReviewDetail | null> {
  try {
    const res = await fetch(`${API_BASE}/reviews/${id}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchRepositories(): Promise<Repository[]> {
  try {
    const res = await fetch(`${API_BASE}/repos`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return [];
  }
}

export async function updateRepoConfig(
  repoId: string,
  config: Partial<RepoConfigData>
): Promise<RepoConfigData | null> {
  try {
    const res = await fetch(`${API_BASE}/repos/${repoId}/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

export async function toggleRepoActive(
  repoId: string,
  isActive: boolean
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/repos/${repoId}/toggle?is_active=${isActive}`, {
      method: "PATCH",
    });
    return res.ok;
  } catch {
    return false;
  }
}
