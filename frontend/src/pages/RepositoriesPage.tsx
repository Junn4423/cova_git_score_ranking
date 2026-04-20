import { useEffect, useState } from "react";
import {
  Card, Table, Typography, Space, Tag, Spin, Tooltip,
} from "antd";
import {
  CodeOutlined, BranchesOutlined, PullRequestOutlined,
  TeamOutlined, PlusOutlined, MinusOutlined, ClockCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { getRepositories } from "../api/client";

const { Title, Text } = Typography;

interface Repo {
  id: number;
  github_id: number;
  full_name: string;
  name: string;
  description: string;
  default_branch: string;
  is_tracked: boolean;
  exclude_from_ranking: boolean;
  last_synced_at: string;
  commit_count: number;
  pr_count: number;
  contributor_count: number;
  lines_added: number;
  lines_deleted: number;
}

export default function RepositoriesPage() {
  const navigate = useNavigate();
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getRepositories()
      .then((r) => setRepos(r.data))
      .finally(() => setLoading(false));
  }, []);

  const columns = [
    {
      title: "Repository",
      key: "repo",
      render: (_: any, r: Repo) => (
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>
            <CodeOutlined style={{ marginRight: 6, color: "#1677ff" }} />
            {r.full_name}
          </div>
          {r.description && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {r.description.length > 100 ? r.description.slice(0, 100) + "..." : r.description}
            </Text>
          )}
        </div>
      ),
    },
    {
      title: <Tooltip title="Commits"><BranchesOutlined /> Commits</Tooltip>,
      dataIndex: "commit_count",
      key: "commits",
      width: 100,
      sorter: (a: Repo, b: Repo) => a.commit_count - b.commit_count,
      defaultSortOrder: "descend" as const,
      render: (v: number) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: <Tooltip title="Contributors"><TeamOutlined /> Contributors</Tooltip>,
      dataIndex: "contributor_count",
      key: "contributors",
      width: 120,
      sorter: (a: Repo, b: Repo) => a.contributor_count - b.contributor_count,
      render: (v: number) => <Tag color="purple">{v}</Tag>,
    },
    {
      title: <Tooltip title="Pull Requests"><PullRequestOutlined /> PRs</Tooltip>,
      dataIndex: "pr_count",
      key: "prs",
      width: 80,
      sorter: (a: Repo, b: Repo) => a.pr_count - b.pr_count,
      render: (v: number) => <Tag color={v > 0 ? "cyan" : "default"}>{v}</Tag>,
    },
    {
      title: "Lines Changed",
      key: "lines",
      width: 160,
      sorter: (a: Repo, b: Repo) =>
        (a.lines_added + a.lines_deleted) - (b.lines_added + b.lines_deleted),
      render: (_: any, r: Repo) => (
        <Space size={6}>
          <Text type="success" style={{ fontSize: 12 }}>
            <PlusOutlined style={{ fontSize: 10 }} /> {r.lines_added.toLocaleString()}
          </Text>
          <Text type="danger" style={{ fontSize: 12 }}>
            <MinusOutlined style={{ fontSize: 10 }} /> {r.lines_deleted.toLocaleString()}
          </Text>
        </Space>
      ),
    },
    {
      title: "Branch",
      dataIndex: "default_branch",
      key: "branch",
      width: 90,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: <Tooltip title="Last Synced"><ClockCircleOutlined /> Synced</Tooltip>,
      dataIndex: "last_synced_at",
      key: "synced",
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
      <div style={{ marginBottom: 20 }}>
        <Title level={3} style={{ margin: 0 }}>
          <CodeOutlined style={{ marginRight: 8 }} />
          Repositories ({repos.length})
        </Title>
        <Text type="secondary">Danh sách tất cả repositories đã đồng bộ</Text>
      </div>

      <Card>
        <Table
          dataSource={repos}
          columns={columns}
          rowKey="id"
          size="middle"
          pagination={{ pageSize: 15 }}
          onRow={(r) => ({
            onClick: () => navigate(`/repositories/${r.id}`),
            style: { cursor: "pointer" },
          })}
        />
      </Card>
    </div>
  );
}
