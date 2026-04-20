import { useEffect, useState } from "react";
import {
  Card, Row, Col, Statistic, Typography, Alert, Spin, Space, Tag,
  Table, Button, Input, message, Divider, Avatar, Tooltip,
} from "antd";
import {
  CheckCircleOutlined,
  ApiOutlined,
  DatabaseOutlined,
  GithubOutlined,
  TeamOutlined,
  CodeOutlined,
  PullRequestOutlined,
  SyncOutlined,
  BranchesOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { healthCheck, getSyncStats, getDevelopers, getCommits, syncRepo } from "../api/client";

const { Title, Text } = Typography;

interface HealthData {
  status: string;
  service: string;
  version: string;
  database: { connected: boolean; error?: string };
}

interface SyncStats {
  repositories: number;
  developers: number;
  commits: number;
  pull_requests: number;
  reviews: number;
}

interface Developer {
  id: number;
  github_login: string;
  display_name: string;
  email: string;
  avatar_url: string;
  is_bot: boolean;
  commit_count: number;
}

interface CommitRow {
  id: number;
  sha: string;
  message: string;
  author: string;
  committed_at: string;
  additions: number;
  deletions: number;
  is_merge: boolean;
  repo: string;
}

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [stats, setStats] = useState<SyncStats | null>(null);
  const [developers, setDevelopers] = useState<Developer[]>([]);
  const [commits, setCommits] = useState<CommitRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncInput, setSyncInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fetchAll = () => {
    setLoading(true);
    Promise.all([
      healthCheck().then((r) => setHealth(r.data)),
      getSyncStats().then((r) => setStats(r.data)),
      getDevelopers().then((r) => setDevelopers(r.data)),
      getCommits({ limit: 20 }).then((r) => setCommits(r.data)),
    ])
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchAll(); }, []);

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

  const devColumns = [
    {
      title: "Developer",
      key: "dev",
      render: (_: any, r: Developer) => (
        <Space>
          <Avatar src={r.avatar_url} size="small">{r.github_login[0]}</Avatar>
          <div>
            <div style={{ fontWeight: 500 }}>{r.display_name || r.github_login}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>@{r.github_login}</Text>
          </div>
        </Space>
      ),
    },
    { title: "Email", dataIndex: "email", key: "email", ellipsis: true },
    {
      title: "Commits",
      dataIndex: "commit_count",
      key: "commit_count",
      sorter: (a: Developer, b: Developer) => a.commit_count - b.commit_count,
      defaultSortOrder: "descend" as const,
      render: (v: number) => <Tag color={v > 10 ? "green" : v > 0 ? "blue" : "default"}>{v}</Tag>,
    },
  ];

  const commitColumns = [
    {
      title: "SHA",
      dataIndex: "sha",
      key: "sha",
      width: 90,
      render: (v: string) => (
        <Tooltip title={v}><code>{v.substring(0, 7)}</code></Tooltip>
      ),
    },
    { title: "Author", dataIndex: "author", key: "author", width: 120 },
    {
      title: "Message",
      dataIndex: "message",
      key: "message",
      ellipsis: true,
      render: (v: string) => v.split("\n")[0],
    },
    {
      title: "+/-",
      key: "changes",
      width: 100,
      render: (_: any, r: CommitRow) => (
        <Space size={4}>
          <Text type="success">+{r.additions}</Text>
          <Text type="danger">-{r.deletions}</Text>
        </Space>
      ),
    },
    {
      title: "Repo",
      dataIndex: "repo",
      key: "repo",
      width: 180,
      ellipsis: true,
    },
    {
      title: "Date",
      dataIndex: "committed_at",
      key: "committed_at",
      width: 160,
      render: (v: string) => v ? new Date(v).toLocaleString("vi-VN") : "—",
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
      <Title level={3}>🎯 Dashboard Tổng Quan</Title>
      <Text type="secondary" style={{ marginBottom: 16, display: "block" }}>
        Hệ thống phân tích đóng góp dev từ GitHub
      </Text>

      {error && (
        <Alert type="error" message="Lỗi" description={error} showIcon closable
          style={{ marginBottom: 16 }} onClose={() => setError(null)} />
      )}

      {/* ── Health cards ─── */}
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
          <Card hoverable style={{ borderLeft: `4px solid ${health?.database.connected ? "#52c41a" : "#ff4d4f"}` }}>
            <Statistic title={<Space><DatabaseOutlined /> Database</Space>}
              value={health?.database.connected ? "Connected" : "Disconnected"}
              valueStyle={{ color: health?.database.connected ? "#52c41a" : "#ff4d4f" }}
              prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ borderLeft: "4px solid #1677ff" }}>
            <Statistic title={<Space><GithubOutlined /> Repositories</Space>}
              value={stats?.repositories || 0}
              valueStyle={{ color: "#1677ff" }}
              prefix={<CodeOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ borderLeft: "4px solid #722ed1" }}>
            <Statistic title={<Space><TeamOutlined /> Developers</Space>}
              value={stats?.developers || 0}
              valueStyle={{ color: "#722ed1" }} />
          </Card>
        </Col>
      </Row>

      {/* ── Stats row 2 ─── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card><Statistic title="Commits" value={stats?.commits || 0} prefix={<BranchesOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card><Statistic title="Pull Requests" value={stats?.pull_requests || 0} prefix={<PullRequestOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card><Statistic title="Reviews" value={stats?.reviews || 0} prefix={<FileTextOutlined />} /></Card>
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

      <Divider />

      {/* ── Developers table ─── */}
      <Title level={4}>👥 Developers ({developers.length})</Title>
      <Table
        dataSource={developers}
        columns={devColumns}
        rowKey="id"
        size="small"
        pagination={{ pageSize: 10 }}
        style={{ marginBottom: 24 }}
      />

      {/* ── Recent commits ─── */}
      <Title level={4}>📝 Recent Commits ({commits.length})</Title>
      <Table
        dataSource={commits}
        columns={commitColumns}
        rowKey="id"
        size="small"
        pagination={{ pageSize: 10 }}
      />

      <div style={{ marginTop: 24 }}>
        <Tag color="green">Tuần 1: Project Setup ✅</Tag>
        <Tag color="green">Tuần 2: Data Ingestion ✅</Tag>
        <Tag color="orange">Tuần 3: Dashboard + Alias ⏳</Tag>
      </div>
    </div>
  );
}
