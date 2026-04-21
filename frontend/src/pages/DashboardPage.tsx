import { useEffect, useState } from "react";
import {
  Card, Row, Col, Statistic, Typography, Alert, Spin, Space, Tag,
  Table, Button, Input, message, Avatar, Select,
} from "antd";
import {
  CheckCircleOutlined,
  ApiOutlined,
  TeamOutlined,
  CodeOutlined,
  PullRequestOutlined,
  SyncOutlined,
  BranchesOutlined,
  FileTextOutlined,
  RiseOutlined,
  FireOutlined,
  CalendarOutlined,
  PlusOutlined,
  MinusOutlined,
} from "@ant-design/icons";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import { useNavigate } from "react-router-dom";
import {
  healthCheck, getDashboardOverview, getCommitActivity,
  getRepositories, syncRepo,
} from "../api/client";

const { Title, Text } = Typography;

interface HealthData {
  status: string;
  service: string;
  version: string;
  database: { connected: boolean; error?: string };
}

interface OverviewData {
  period_days: number;
  total_commits: number;
  total_pull_requests: number;
  merged_pull_requests: number;
  total_reviews: number;
  lines_added: number;
  lines_deleted: number;
  active_developers: number;
  top_contributors: {
    id: number;
    github_login: string;
    display_name: string;
    avatar_url: string;
    commit_count: number;
    additions: number;
    deletions: number;
  }[];
  repo_breakdown: {
    id: number;
    full_name: string;
    commit_count: number;
  }[];
}

interface ActivityDay {
  date: string;
  commits: number;
  additions: number;
  deletions: number;
}

interface RepoOption {
  id: number;
  full_name: string;
}

const COLORS = [
  "#1677ff", "#722ed1", "#13c2c2", "#52c41a", "#eb2f96",
  "#fa8c16", "#2f54eb", "#a0d911", "#fa541c", "#597ef7",
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<HealthData | null>(null);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [activity, setActivity] = useState<ActivityDay[]>([]);
  const [repos, setRepos] = useState<RepoOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncInput, setSyncInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(90);
  const [repoFilter, setRepoFilter] = useState<number | undefined>(undefined);

  const fetchAll = () => {
    setLoading(true);
    Promise.all([
      healthCheck().then((r) => setHealth(r.data)),
      getDashboardOverview({ days, repo_id: repoFilter }).then((r) => setOverview(r.data)),
      getCommitActivity({ days, repo_id: repoFilter }).then((r) => setActivity(r.data)),
      getRepositories().then((r) => setRepos(r.data)),
    ])
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchAll(); }, [days, repoFilter]);

  const handleSync = async () => {
    if (!syncInput.trim()) {
      message.warning("Nhập tên repo (ví dụ: owner/repo)");
      return;
    }
    setSyncing(true);
    try {
      const res = await syncRepo({
        full_name: syncInput.trim(),
        max_commit_pages: 2,
        max_pr_pages: 2,
        fetch_files: true,
      });
      message.success(
        `Đồng bộ thành công: ${res.data.new_commits} commits mới, ${res.data.new_prs} PRs mới`
      );
      fetchAll();
    } catch (err: any) {
      message.error("Sync thất bại: " + (err.response?.data?.detail || err.message));
    } finally {
      setSyncing(false);
    }
  };

  const contributorColumns = [
    {
      title: "#",
      key: "rank",
      width: 45,
      render: (_: any, __: any, i: number) => (
        <span style={{
          fontWeight: 700,
          color: i < 3 ? COLORS[i] : "#999",
          fontSize: i < 3 ? 16 : 14,
        }}>
          {i + 1}
        </span>
      ),
    },
    {
      title: "Developer",
      key: "dev",
      render: (_: any, r: any) => (
        <Space>
          <Avatar src={r.avatar_url} size="small">{r.github_login[0]}</Avatar>
          <a onClick={() => navigate(`/developers/${r.id}`)} style={{ cursor: "pointer" }}>
            <div style={{ fontWeight: 500 }}>{r.display_name || r.github_login}</div>
            <Text type="secondary" style={{ fontSize: 11 }}>@{r.github_login}</Text>
          </a>
        </Space>
      ),
    },
    {
      title: "Commits",
      dataIndex: "commit_count",
      key: "commits",
      width: 85,
      render: (v: number) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: "Lines",
      key: "lines",
      width: 130,
      render: (_: any, r: any) => (
        <Space size={4}>
          <Text type="success" style={{ fontSize: 12 }}>
            <PlusOutlined style={{ fontSize: 10 }} /> {r.additions.toLocaleString()}
          </Text>
          <Text type="danger" style={{ fontSize: 12 }}>
            <MinusOutlined style={{ fontSize: 10 }} /> {r.deletions.toLocaleString()}
          </Text>
        </Space>
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>🎯 Dashboard Tổng Quan</Title>
          <Text type="secondary">Hệ thống phân tích đóng góp dev từ GitHub</Text>
        </div>
        <Space>
          <Select
            value={repoFilter}
            onChange={setRepoFilter}
            allowClear
            placeholder="Tất cả repos"
            style={{ width: 220 }}
            options={repos.map((r) => ({ label: r.full_name, value: r.id }))}
          />
          <Select
            value={days}
            onChange={setDays}
            style={{ width: 130 }}
            options={[
              { label: "7 ngày", value: 7 },
              { label: "30 ngày", value: 30 },
              { label: "90 ngày", value: 90 },
              { label: "180 ngày", value: 180 },
              { label: "365 ngày", value: 365 },
            ]}
          />
        </Space>
      </div>

      {error && (
        <Alert type="error" message="Lỗi" description={error} showIcon closable
          style={{ marginBottom: 16 }} onClose={() => setError(null)} />
      )}

      {/* ── System status + Summary stats ─── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ borderLeft: `4px solid ${health?.status === "healthy" ? "#52c41a" : "#ff4d4f"}` }}>
            <Statistic title={<Space><ApiOutlined /> API Status</Space>}
              value={health?.status === "healthy" ? "Healthy" : "Degraded"}
              valueStyle={{ color: health?.status === "healthy" ? "#52c41a" : "#ff4d4f" }}
              prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ borderLeft: "4px solid #1677ff" }}>
            <Statistic title={<Space><BranchesOutlined /> Commits</Space>}
              value={overview?.total_commits || 0}
              valueStyle={{ color: "#1677ff" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ borderLeft: "4px solid #722ed1" }}>
            <Statistic title={<Space><TeamOutlined /> Active Devs</Space>}
              value={overview?.active_developers || 0}
              valueStyle={{ color: "#722ed1" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ borderLeft: "4px solid #13c2c2" }}>
            <Statistic title={<Space><RiseOutlined /> Lines Changed</Space>}
              value={(overview?.lines_added || 0) + (overview?.lines_deleted || 0)}
              valueStyle={{ color: "#13c2c2" }}
              suffix={
                <Text style={{ fontSize: 12 }}>
                  <Text type="success">+{(overview?.lines_added || 0).toLocaleString()}</Text>{" "}
                  <Text type="danger">-{(overview?.lines_deleted || 0).toLocaleString()}</Text>
                </Text>
              } />
          </Card>
        </Col>
      </Row>

      {/* ── Row 2: PRs, Reviews, Repos ─── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="Pull Requests" value={overview?.total_pull_requests || 0}
              prefix={<PullRequestOutlined />}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>
                ({overview?.merged_pull_requests || 0} merged)
              </Text>} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="Reviews" value={overview?.total_reviews || 0}
              prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="Repositories" value={repos.length}
              prefix={<CodeOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* ── Commit Activity Chart ─── */}
      <Card
        title={<Space><CalendarOutlined /> Commit Activity ({days} ngày)</Space>}
        style={{ marginBottom: 24 }}
      >
        {activity.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={activity}>
              <defs>
                <linearGradient id="colorCommits" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1677ff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#1677ff" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorAdds" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#52c41a" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#52c41a" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <ReTooltip
                contentStyle={{ borderRadius: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}
              />
              <Area
                type="monotone" dataKey="commits" name="Commits"
                stroke="#1677ff" fill="url(#colorCommits)" strokeWidth={2}
              />
              <Area
                type="monotone" dataKey="additions" name="Additions"
                stroke="#52c41a" fill="url(#colorAdds)" strokeWidth={1}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ textAlign: "center", padding: 40 }}>
            <Text type="secondary">Không có dữ liệu commit trong khoảng thời gian này</Text>
          </div>
        )}
      </Card>

      {/* ── Top Contributors + Repo Breakdown ─── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={14}>
          <Card title={<Space><FireOutlined style={{ color: "#fa541c" }} /> Top Contributors</Space>}>
            <Table
              dataSource={overview?.top_contributors || []}
              columns={contributorColumns}
              rowKey="id"
              size="small"
              pagination={false}
              onRow={(r) => ({ onClick: () => navigate(`/developers/${r.id}`), style: { cursor: "pointer" } })}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={<Space><CodeOutlined /> Repo Breakdown</Space>}>
            {(overview?.repo_breakdown || []).length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={overview?.repo_breakdown || []}
                    dataKey="commit_count"
                    nameKey="full_name"
                    cx="50%" cy="50%"
                    outerRadius={90}
                    label={({ full_name, commit_count }: any) =>
                      `${full_name.split("/")[1]} (${commit_count})`
                    }
                    labelLine={true}
                  >
                    {(overview?.repo_breakdown || []).map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <ReTooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: "center", padding: 40 }}>
                <Text type="secondary">No data</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* ── Sync box ─── */}
      <Card title={<Space><SyncOutlined /> Đồng Bộ Repository</Space>} style={{ marginBottom: 24 }}>
        <Space.Compact style={{ width: "100%", maxWidth: 500 }}>
          <Input
            placeholder="owner/repo (vd: pallets/flask)"
            value={syncInput}
            onChange={(e) => setSyncInput(e.target.value)}
            onPressEnter={handleSync}
          />
          <Button type="primary" icon={<SyncOutlined />} loading={syncing} onClick={handleSync}>
            Sync
          </Button>
        </Space.Compact>
        <div style={{ marginTop: 8 }}>
          <Text type="secondary">Nhập tên repo GitHub để đồng bộ commits, PRs và reviews.</Text>
        </div>
      </Card>

      <div style={{ marginTop: 24 }}>
        <Tag color="green">Tuần 1: Project Setup ✅</Tag>
        <Tag color="green">Tuần 2: Data Ingestion ✅</Tag>
        <Tag color="green">Tuần 3: Dashboard + Alias ✅</Tag>
        <Tag color="orange">Tuần 4: Work Item Grouping ⏳</Tag>
      </div>
    </div>
  );
}
