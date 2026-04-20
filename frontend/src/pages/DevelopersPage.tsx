import { useEffect, useState } from "react";
import {
  Card, Table, Typography, Space, Avatar, Tag, Input, Spin, Tooltip,
} from "antd";
import {
  TeamOutlined, SearchOutlined, CodeOutlined,
  PullRequestOutlined, FileTextOutlined,
  PlusOutlined, MinusOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { getDevelopers } from "../api/client";

const { Title, Text } = Typography;

interface Developer {
  id: number;
  github_login: string;
  display_name: string;
  email: string;
  avatar_url: string;
  is_bot: boolean;
  is_active: boolean;
  commit_count: number;
  pr_count: number;
  review_count: number;
  lines_added: number;
  lines_deleted: number;
  created_at: string;
}

export default function DevelopersPage() {
  const navigate = useNavigate();
  const [developers, setDevelopers] = useState<Developer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    getDevelopers({ search: search || undefined })
      .then((r) => setDevelopers(r.data))
      .finally(() => setLoading(false));
  }, [search]);

  const columns = [
    {
      title: "#",
      key: "rank",
      width: 45,
      render: (_: any, __: any, i: number) => (
        <Text type="secondary">{i + 1}</Text>
      ),
    },
    {
      title: "Developer",
      key: "dev",
      render: (_: any, r: Developer) => (
        <Space>
          <Avatar src={r.avatar_url} size={36}>
            {(r.github_login || "?")[0].toUpperCase()}
          </Avatar>
          <div>
            <div style={{ fontWeight: 600, fontSize: 14 }}>
              {r.display_name || r.github_login}
              {r.is_bot && <Tag color="orange" style={{ marginLeft: 6 }}>BOT</Tag>}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>@{r.github_login}</Text>
            {r.email && (
              <div>
                <Text type="secondary" style={{ fontSize: 11 }}>{r.email}</Text>
              </div>
            )}
          </div>
        </Space>
      ),
      sorter: (a: Developer, b: Developer) =>
        (a.github_login || "").localeCompare(b.github_login || ""),
    },
    {
      title: <Tooltip title="Commits"><CodeOutlined /> Commits</Tooltip>,
      dataIndex: "commit_count",
      key: "commits",
      width: 100,
      sorter: (a: Developer, b: Developer) => a.commit_count - b.commit_count,
      defaultSortOrder: "descend" as const,
      render: (v: number) => (
        <Tag color={v > 20 ? "green" : v > 5 ? "blue" : v > 0 ? "cyan" : "default"}>
          {v}
        </Tag>
      ),
    },
    {
      title: <Tooltip title="Pull Requests"><PullRequestOutlined /> PRs</Tooltip>,
      dataIndex: "pr_count",
      key: "prs",
      width: 80,
      sorter: (a: Developer, b: Developer) => a.pr_count - b.pr_count,
      render: (v: number) => (
        <Tag color={v > 0 ? "purple" : "default"}>{v}</Tag>
      ),
    },
    {
      title: <Tooltip title="Reviews"><FileTextOutlined /> Reviews</Tooltip>,
      dataIndex: "review_count",
      key: "reviews",
      width: 90,
      sorter: (a: Developer, b: Developer) => a.review_count - b.review_count,
      render: (v: number) => (
        <Tag color={v > 0 ? "geekblue" : "default"}>{v}</Tag>
      ),
    },
    {
      title: "Lines Changed",
      key: "lines",
      width: 160,
      sorter: (a: Developer, b: Developer) =>
        (a.lines_added + a.lines_deleted) - (b.lines_added + b.lines_deleted),
      render: (_: any, r: Developer) => (
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
      title: "Status",
      key: "status",
      width: 80,
      render: (_: any, r: Developer) => (
        <Tag color={r.is_active ? "green" : "default"}>
          {r.is_active ? "Active" : "Inactive"}
        </Tag>
      ),
    },
  ];

  if (loading && developers.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            <TeamOutlined style={{ marginRight: 8 }} />
            Developers ({developers.length})
          </Title>
          <Text type="secondary">Danh sách tất cả developers từ GitHub</Text>
        </div>
        <Input
          placeholder="Tìm kiếm developer..."
          prefix={<SearchOutlined />}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 280 }}
          allowClear
        />
      </div>

      <Card>
        <Table
          dataSource={developers}
          columns={columns}
          rowKey="id"
          size="middle"
          pagination={{ pageSize: 15, showSizeChanger: true }}
          onRow={(r) => ({
            onClick: () => navigate(`/developers/${r.id}`),
            style: { cursor: "pointer" },
          })}
        />
      </Card>
    </div>
  );
}
