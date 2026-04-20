import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Row, Col, Typography, Space, Avatar, Tag, Table, Spin,
  Statistic, Divider, Tooltip, Button, Modal, Input, Select, message,
  Descriptions, Empty,
} from "antd";
import {
  ArrowLeftOutlined, CodeOutlined, PullRequestOutlined,
  FileTextOutlined, CalendarOutlined, PlusOutlined,
  MinusOutlined, BranchesOutlined, LinkOutlined,
  UserSwitchOutlined, TagOutlined,
} from "@ant-design/icons";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
  ResponsiveContainer,
} from "recharts";
import {
  getDeveloper, getDeveloperActivity, addDeveloperAlias,
} from "../api/client";

const { Title, Text } = Typography;

interface DevDetail {
  id: number;
  github_login: string;
  display_name: string;
  email: string;
  avatar_url: string;
  is_bot: boolean;
  is_active: boolean;
  created_at: string;
  stats: {
    commit_count: number;
    pr_count: number;
    review_count: number;
    lines_added: number;
    lines_deleted: number;
    active_days: number;
  };
  aliases: { id: number; alias_type: string; alias_value: string }[];
  recent_commits: {
    id: number;
    sha: string;
    message: string;
    committed_at: string;
    additions: number;
    deletions: number;
    is_merge: boolean;
    repo: string;
  }[];
  recent_prs: {
    id: number;
    number: number;
    title: string;
    state: string;
    merged: boolean;
    repo: string;
    created_at: string;
  }[];
  recent_reviews: {
    id: number;
    state: string;
    submitted_at: string;
    pr_title: string;
    pr_number: number;
    repo: string;
  }[];
}

interface ActivityDay {
  date: string;
  commits: number;
  additions: number;
  deletions: number;
}

export default function DeveloperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dev, setDev] = useState<DevDetail | null>(null);
  const [activity, setActivity] = useState<ActivityDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [aliasModal, setAliasModal] = useState(false);
  const [aliasType, setAliasType] = useState("email");
  const [aliasValue, setAliasValue] = useState("");

  const fetchData = () => {
    if (!id) return;
    setLoading(true);
    const devId = parseInt(id);
    Promise.all([
      getDeveloper(devId).then((r) => setDev(r.data)),
      getDeveloperActivity(devId, { days: 180 }).then((r) => setActivity(r.data)),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleAddAlias = async () => {
    if (!aliasValue.trim() || !id) return;
    try {
      await addDeveloperAlias(parseInt(id), {
        alias_type: aliasType,
        alias_value: aliasValue.trim(),
      });
      message.success("Alias added successfully");
      setAliasModal(false);
      setAliasValue("");
      fetchData();
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Failed to add alias");
    }
  };

  const commitColumns = [
    {
      title: "SHA",
      dataIndex: "sha",
      key: "sha",
      width: 90,
      render: (v: string, r: any) => (
        <Tooltip title={v}>
          <a
            href={`https://github.com/${r.repo}/commit/${v}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <code>{v.substring(0, 7)}</code>
          </a>
        </Tooltip>
      ),
    },
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
      width: 110,
      render: (_: any, r: any) => (
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
      render: (v: string) => (
        <a href={`https://github.com/${v}`} target="_blank" rel="noopener noreferrer">
          {v.split("/")[1]}
        </a>
      ),
    },
    {
      title: "Date",
      dataIndex: "committed_at",
      key: "date",
      width: 150,
      render: (v: string) => v ? new Date(v).toLocaleString("vi-VN") : "—",
    },
  ];

  const prColumns = [
    {
      title: "#",
      dataIndex: "number",
      key: "number",
      width: 60,
      render: (v: number, r: any) => (
        <a href={`https://github.com/${r.repo}/pull/${v}`} target="_blank" rel="noopener noreferrer">
          #{v}
        </a>
      ),
    },
    { title: "Title", dataIndex: "title", key: "title", ellipsis: true },
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
      title: "Repo",
      dataIndex: "repo",
      key: "repo",
      width: 150,
      ellipsis: true,
      render: (v: string) => v?.split("/")[1],
    },
    {
      title: "Date",
      dataIndex: "created_at",
      key: "date",
      width: 150,
      render: (v: string) => v ? new Date(v).toLocaleString("vi-VN") : "—",
    },
  ];

  const reviewColumns = [
    {
      title: "PR",
      key: "pr",
      width: 60,
      render: (_: any, r: any) => (
        <a href={`https://github.com/${r.repo}/pull/${r.pr_number}`} target="_blank" rel="noopener noreferrer">
          #{r.pr_number}
        </a>
      ),
    },
    { title: "PR Title", dataIndex: "pr_title", key: "pr_title", ellipsis: true },
    {
      title: "State",
      dataIndex: "state",
      key: "state",
      width: 120,
      render: (v: string) => {
        const colors: Record<string, string> = {
          APPROVED: "green",
          CHANGES_REQUESTED: "orange",
          COMMENTED: "blue",
          DISMISSED: "default",
        };
        return <Tag color={colors[v] || "default"}>{v}</Tag>;
      },
    },
    {
      title: "Date",
      dataIndex: "submitted_at",
      key: "date",
      width: 150,
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

  if (!dev) {
    return <Empty description="Developer not found" />;
  }

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate("/developers")}
        style={{ marginBottom: 16 }}
      >
        Back to Developers
      </Button>

      {/* ── Profile Card ─── */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={24} align="middle">
          <Col>
            <Avatar src={dev.avatar_url} size={80} style={{ border: "3px solid #1677ff" }}>
              {dev.github_login[0].toUpperCase()}
            </Avatar>
          </Col>
          <Col flex="auto">
            <Title level={3} style={{ margin: 0 }}>
              {dev.display_name || dev.github_login}
              {dev.is_bot && <Tag color="orange" style={{ marginLeft: 8 }}>BOT</Tag>}
              {!dev.is_active && <Tag color="red" style={{ marginLeft: 8 }}>Inactive</Tag>}
            </Title>
            <Space>
              <a href={`https://github.com/${dev.github_login}`} target="_blank" rel="noopener noreferrer">
                <Text type="secondary">@{dev.github_login}</Text>
                <LinkOutlined style={{ marginLeft: 4 }} />
              </a>
              {dev.email && <Text type="secondary">· {dev.email}</Text>}
            </Space>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
          <Col xs={8} sm={4}>
            <Statistic title="Commits" value={dev.stats.commit_count}
              prefix={<CodeOutlined />} valueStyle={{ color: "#1677ff" }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="PRs" value={dev.stats.pr_count}
              prefix={<PullRequestOutlined />} valueStyle={{ color: "#722ed1" }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="Reviews" value={dev.stats.review_count}
              prefix={<FileTextOutlined />} valueStyle={{ color: "#13c2c2" }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="Active Days" value={dev.stats.active_days}
              prefix={<CalendarOutlined />} valueStyle={{ color: "#52c41a" }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="Lines Added" value={dev.stats.lines_added}
              prefix={<PlusOutlined />} valueStyle={{ color: "#52c41a", fontSize: 18 }} />
          </Col>
          <Col xs={8} sm={4}>
            <Statistic title="Lines Deleted" value={dev.stats.lines_deleted}
              prefix={<MinusOutlined />} valueStyle={{ color: "#ff4d4f", fontSize: 18 }} />
          </Col>
        </Row>
      </Card>

      {/* ── Activity Chart ─── */}
      <Card
        title={<Space><CalendarOutlined /> Activity (180 ngày)</Space>}
        style={{ marginBottom: 24 }}
      >
        {activity.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={activity}>
              <defs>
                <linearGradient id="devActivity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1677ff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#1677ff" stopOpacity={0} />
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
                stroke="#1677ff" fill="url(#devActivity)" strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ textAlign: "center", padding: 40 }}>
            <Text type="secondary">No activity data</Text>
          </div>
        )}
      </Card>

      {/* ── Aliases ─── */}
      <Card
        title={<Space><TagOutlined /> Aliases ({dev.aliases.length})</Space>}
        extra={
          <Button size="small" icon={<PlusOutlined />} onClick={() => setAliasModal(true)}>
            Add Alias
          </Button>
        }
        style={{ marginBottom: 24 }}
      >
        {dev.aliases.length > 0 ? (
          <Space wrap>
            {dev.aliases.map((a) => (
              <Tag key={a.id} color={a.alias_type === "email" ? "blue" : "green"}>
                {a.alias_type}: {a.alias_value}
              </Tag>
            ))}
          </Space>
        ) : (
          <Text type="secondary">No aliases registered</Text>
        )}
      </Card>

      {/* ── Recent Commits ─── */}
      <Card
        title={<Space><BranchesOutlined /> Recent Commits ({dev.recent_commits.length})</Space>}
        style={{ marginBottom: 24 }}
      >
        <Table
          dataSource={dev.recent_commits}
          columns={commitColumns}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* ── Recent PRs ─── */}
      {dev.recent_prs.length > 0 && (
        <Card
          title={<Space><PullRequestOutlined /> Recent PRs ({dev.recent_prs.length})</Space>}
          style={{ marginBottom: 24 }}
        >
          <Table
            dataSource={dev.recent_prs}
            columns={prColumns}
            rowKey="id"
            size="small"
            pagination={false}
          />
        </Card>
      )}

      {/* ── Recent Reviews ─── */}
      {dev.recent_reviews.length > 0 && (
        <Card
          title={<Space><FileTextOutlined /> Recent Reviews ({dev.recent_reviews.length})</Space>}
          style={{ marginBottom: 24 }}
        >
          <Table
            dataSource={dev.recent_reviews}
            columns={reviewColumns}
            rowKey="id"
            size="small"
            pagination={false}
          />
        </Card>
      )}

      {/* ── Add Alias Modal ─── */}
      <Modal
        title="Add Alias"
        open={aliasModal}
        onOk={handleAddAlias}
        onCancel={() => { setAliasModal(false); setAliasValue(""); }}
        okText="Add"
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Select
            value={aliasType}
            onChange={setAliasType}
            style={{ width: "100%" }}
            options={[
              { label: "Email", value: "email" },
              { label: "GitHub Login", value: "github_login" },
              { label: "Name", value: "name" },
            ]}
          />
          <Input
            placeholder="Alias value"
            value={aliasValue}
            onChange={(e) => setAliasValue(e.target.value)}
          />
        </Space>
      </Modal>
    </div>
  );
}
