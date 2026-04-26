import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Row, Col, Typography, Space, Avatar, Tag, Table, Spin,
  Statistic, Tooltip, Button, Empty,
} from "antd";
import {
  ArrowLeftOutlined, CodeOutlined, BranchesOutlined,
  PullRequestOutlined, TeamOutlined, FileTextOutlined,
  CalendarOutlined, PlusOutlined, MinusOutlined, LinkOutlined,
  PlayCircleOutlined,
} from "@ant-design/icons";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
  ResponsiveContainer,
} from "recharts";
import { getRepository } from "../api/client";

const { Title, Text } = Typography;

interface RepoDetail {
  id: number;
  github_id: number;
  full_name: string;
  name: string;
  description: string;
  default_branch: string;
  is_tracked: boolean;
  last_synced_at: string;
  stats: {
    commit_count: number;
    pr_count: number;
    merged_pr_count: number;
    review_count: number;
    lines_added: number;
    lines_deleted: number;
  };
  top_contributors: {
    id: number;
    github_login: string;
    display_name: string;
    avatar_url: string;
    commit_count: number;
    additions: number;
    deletions: number;
  }[];
  recent_commits: {
    id: number;
    sha: string;
    message: string;
    author: string;
    committed_at: string;
    additions: number;
    deletions: number;
  }[];
  recent_prs: {
    id: number;
    number: number;
    title: string;
    state: string;
    merged: boolean;
    author: string;
    created_at: string;
  }[];
  commit_activity: { date: string; commits: number }[];
}

const COLORS = [
  "#1677ff", "#722ed1", "#13c2c2", "#52c41a", "#eb2f96",
  "#fa8c16", "#2f54eb", "#a0d911", "#fa541c", "#597ef7",
];

export default function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [repo, setRepo] = useState<RepoDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getRepository(parseInt(id))
      .then((r) => setRepo(r.data))
      .finally(() => setLoading(false));
  }, [id]);

  const contributorColumns = [
    {
      title: "#",
      key: "rank",
      width: 40,
      render: (_: any, __: any, i: number) => (
        <span style={{ fontWeight: 700, color: COLORS[i % COLORS.length] }}>{i + 1}</span>
      ),
    },
    {
      title: "Developer",
      key: "dev",
      render: (_: any, r: any) => (
        <Space>
          <Avatar src={r.avatar_url} size="small">{r.github_login[0]}</Avatar>
          <a onClick={() => navigate(`/developers/${r.id}`)} style={{ cursor: "pointer" }}>
            {r.display_name || r.github_login}
          </a>
        </Space>
      ),
    },
    {
      title: "Commits",
      dataIndex: "commit_count",
      key: "commits",
      width: 80,
      render: (v: number) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: "+/-",
      key: "lines",
      width: 130,
      render: (_: any, r: any) => (
        <Space size={4}>
          <Text type="success" style={{ fontSize: 12 }}>+{r.additions.toLocaleString()}</Text>
          <Text type="danger" style={{ fontSize: 12 }}>-{r.deletions.toLocaleString()}</Text>
        </Space>
      ),
    },
  ];

  const commitColumns = [
    {
      title: "SHA",
      dataIndex: "sha",
      key: "sha",
      width: 90,
      render: (v: string) => (
        <Tooltip title={v}>
          <a
            href={`https://github.com/${repo?.full_name}/commit/${v}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <code>{v.substring(0, 7)}</code>
          </a>
        </Tooltip>
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
      render: (_: any, r: any) => (
        <Space size={4}>
          <Text type="success">+{r.additions}</Text>
          <Text type="danger">-{r.deletions}</Text>
        </Space>
      ),
    },
    {
      title: "Date",
      dataIndex: "committed_at",
      key: "date",
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

  if (!repo) {
    return <Empty description="Repository not found" />;
  }

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate("/repositories")}
        style={{ marginBottom: 16 }}
      >
        Back to Repositories
      </Button>

      {/* ── Repo Header ─── */}
      <Card style={{ marginBottom: 24 }}>
        <Row align="middle" gutter={16}>
          <Col>
            <CodeOutlined style={{ fontSize: 36, color: "#1677ff" }} />
          </Col>
          <Col flex="auto">
            <Title level={3} style={{ margin: 0 }}>
              {repo.full_name}
              <a
                href={`https://github.com/${repo.full_name}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ marginLeft: 8 }}
              >
                <LinkOutlined style={{ fontSize: 16 }} />
              </a>
            </Title>
            {repo.description && <Text type="secondary">{repo.description}</Text>}
            <div style={{ marginTop: 6 }}>
              <Tag>{repo.default_branch}</Tag>
              {repo.last_synced_at && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Last synced: {new Date(repo.last_synced_at).toLocaleString("vi-VN")}
                </Text>
              )}
            </div>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => navigate(`/evaluations/new?repo=${encodeURIComponent(repo.full_name)}`)}
            >
              Danh gia repo nay
            </Button>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
          <Col xs={8} sm={4}>
            <Statistic title="Commits" value={repo.stats.commit_count}
              prefix={<BranchesOutlined />} valueStyle={{ color: "#1677ff" }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="PRs" value={repo.stats.pr_count}
              prefix={<PullRequestOutlined />} valueStyle={{ color: "#722ed1" }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="Merged PRs" value={repo.stats.merged_pr_count}
              valueStyle={{ color: "#52c41a" }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="Reviews" value={repo.stats.review_count}
              prefix={<FileTextOutlined />} valueStyle={{ color: "#13c2c2" }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="Lines Added" value={repo.stats.lines_added}
              prefix={<PlusOutlined />} valueStyle={{ color: "#52c41a", fontSize: 18 }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="Lines Deleted" value={repo.stats.lines_deleted}
              prefix={<MinusOutlined />} valueStyle={{ color: "#ff4d4f", fontSize: 18 }} />
          </Col>
        </Row>
      </Card>

      {/* ── Commit Activity Chart ─── */}
      {repo.commit_activity.length > 0 && (
        <Card
          title={<Space><CalendarOutlined /> Commit Activity (30 ngày)</Space>}
          style={{ marginBottom: 24 }}
        >
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={repo.commit_activity}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <ReTooltip
                contentStyle={{ borderRadius: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}
              />
              <Bar dataKey="commits" name="Commits" fill="#1677ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* ── Top Contributors + Recent Commits ─── */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card
            title={<Space><TeamOutlined /> Top Contributors</Space>}
            style={{ marginBottom: 24 }}
          >
            <Table
              dataSource={repo.top_contributors}
              columns={contributorColumns}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card
            title={<Space><BranchesOutlined /> Recent Commits ({repo.recent_commits.length})</Space>}
            style={{ marginBottom: 24 }}
          >
            <Table
              dataSource={repo.recent_commits}
              columns={commitColumns}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
      </Row>

      {/* ── Recent PRs ─── */}
      {repo.recent_prs.length > 0 && (
        <Card
          title={<Space><PullRequestOutlined /> Recent PRs ({repo.recent_prs.length})</Space>}
        >
          <Table
            dataSource={repo.recent_prs}
            columns={[
              {
                title: "#",
                dataIndex: "number",
                key: "number",
                width: 60,
                render: (v: number) => (
                  <a
                    href={`https://github.com/${repo.full_name}/pull/${v}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    #{v}
                  </a>
                ),
              },
              { title: "Title", dataIndex: "title", key: "title", ellipsis: true },
              { title: "Author", dataIndex: "author", key: "author", width: 120 },
              {
                title: "State",
                key: "state",
                width: 90,
                render: (_: any, r: any) => {
                  if (r.merged) return <Tag color="purple">Merged</Tag>;
                  if (r.state === "closed") return <Tag color="red">Closed</Tag>;
                  return <Tag color="green">Open</Tag>;
                },
              },
              {
                title: "Date",
                dataIndex: "created_at",
                key: "date",
                width: 150,
                render: (v: string) => v ? new Date(v).toLocaleString("vi-VN") : "—",
              },
            ]}
            rowKey="id"
            size="small"
            pagination={false}
          />
        </Card>
      )}
    </div>
  );
}
