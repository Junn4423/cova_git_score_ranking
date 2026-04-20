import { useEffect, useState } from "react";
import {
  Card, Table, Typography, Space, Tag, Spin, Select, Avatar, Tooltip, Empty,
} from "antd";
import {
  PullRequestOutlined, PlusOutlined, MinusOutlined,
  FileOutlined, MessageOutlined,
} from "@ant-design/icons";
import { getPullRequests, getRepositories } from "../api/client";

const { Title, Text } = Typography;

interface PR {
  id: number;
  number: number;
  title: string;
  state: string;
  merged: boolean;
  author: string;
  author_avatar: string;
  repo: string;
  head_branch: string;
  base_branch: string;
  additions: number;
  deletions: number;
  changed_files: number;
  review_count: number;
  created_at: string;
  merged_at: string;
  closed_at: string;
}

interface RepoOption {
  id: number;
  full_name: string;
}

export default function PullRequestsPage() {
  const [prs, setPrs] = useState<PR[]>([]);
  const [repos, setRepos] = useState<RepoOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [repoFilter, setRepoFilter] = useState<number | undefined>(undefined);
  const [stateFilter, setStateFilter] = useState<string | undefined>(undefined);

  useEffect(() => {
    getRepositories().then((r) => setRepos(r.data));
  }, []);

  useEffect(() => {
    setLoading(true);
    getPullRequests({
      repo_id: repoFilter,
      state: stateFilter,
      limit: 100,
    })
      .then((r) => setPrs(r.data))
      .finally(() => setLoading(false));
  }, [repoFilter, stateFilter]);

  const columns = [
    {
      title: "#",
      dataIndex: "number",
      key: "number",
      width: 60,
      render: (v: number, r: PR) => (
        <a
          href={`https://github.com/${r.repo}/pull/${v}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          #{v}
        </a>
      ),
    },
    {
      title: "Title",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
      render: (v: string, r: PR) => (
        <div>
          <div style={{ fontWeight: 500 }}>{v}</div>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {r.head_branch} → {r.base_branch}
          </Text>
        </div>
      ),
    },
    {
      title: "Author",
      key: "author",
      width: 130,
      render: (_: any, r: PR) => (
        <Space>
          <Avatar src={r.author_avatar} size="small">{(r.author || "?")[0]}</Avatar>
          <Text>{r.author || "—"}</Text>
        </Space>
      ),
    },
    {
      title: "State",
      key: "state",
      width: 95,
      render: (_: any, r: PR) => {
        if (r.merged) return <Tag color="purple">Merged</Tag>;
        if (r.state === "closed") return <Tag color="red">Closed</Tag>;
        return <Tag color="green">Open</Tag>;
      },
    },
    {
      title: "Repo",
      dataIndex: "repo",
      key: "repo",
      width: 150,
      ellipsis: true,
      render: (v: string) => v?.split("/")[1],
    },
    {
      title: "+/-",
      key: "changes",
      width: 110,
      render: (_: any, r: PR) => (
        <Space size={4}>
          <Text type="success" style={{ fontSize: 12 }}>
            <PlusOutlined style={{ fontSize: 10 }} /> {r.additions}
          </Text>
          <Text type="danger" style={{ fontSize: 12 }}>
            <MinusOutlined style={{ fontSize: 10 }} /> {r.deletions}
          </Text>
        </Space>
      ),
    },
    {
      title: <Tooltip title="Changed Files"><FileOutlined /></Tooltip>,
      dataIndex: "changed_files",
      key: "files",
      width: 55,
    },
    {
      title: <Tooltip title="Reviews"><MessageOutlined /></Tooltip>,
      dataIndex: "review_count",
      key: "reviews",
      width: 55,
      render: (v: number) => v > 0 ? <Tag color="blue">{v}</Tag> : "—",
    },
    {
      title: "Date",
      dataIndex: "created_at",
      key: "date",
      width: 150,
      render: (v: string) => v ? new Date(v).toLocaleString("vi-VN") : "—",
    },
  ];

  if (loading && prs.length === 0) {
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
            <PullRequestOutlined style={{ marginRight: 8 }} />
            Pull Requests ({prs.length})
          </Title>
          <Text type="secondary">Danh sách tất cả pull requests đã đồng bộ</Text>
        </div>
        <Space>
          <Select
            value={repoFilter}
            onChange={setRepoFilter}
            allowClear
            placeholder="Tất cả repos"
            style={{ width: 200 }}
            options={repos.map((r) => ({ label: r.full_name, value: r.id }))}
          />
          <Select
            value={stateFilter}
            onChange={setStateFilter}
            allowClear
            placeholder="Tất cả states"
            style={{ width: 130 }}
            options={[
              { label: "Open", value: "open" },
              { label: "Closed", value: "closed" },
              { label: "Merged", value: "merged" },
            ]}
          />
        </Space>
      </div>

      <Card>
        {prs.length > 0 ? (
          <Table
            dataSource={prs}
            columns={columns}
            rowKey="id"
            size="middle"
            pagination={{ pageSize: 20, showSizeChanger: true }}
          />
        ) : (
          <Empty description="Chưa có pull requests nào được đồng bộ" />
        )}
      </Card>
    </div>
  );
}
