import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card, Table, Typography, Space, Tag, Spin, Select, Avatar,
  Tooltip, Button, Modal, Row, Col, Statistic, message, Empty,
} from "antd";
import {
  AppstoreOutlined, ClockCircleOutlined, PullRequestOutlined,
  PlusOutlined, MinusOutlined, SyncOutlined, BuildOutlined,
  FileOutlined, UserOutlined,
} from "@ant-design/icons";
import {
  getWorkItems, getWorkItemStats, buildWorkItems, getRepositories,
} from "../api/client";

const { Title, Text } = Typography;

interface WI {
  id: number;
  title: string;
  developer: string;
  developer_id: number;
  developer_avatar: string;
  repo: string;
  repo_id: number;
  pr_number: number | null;
  grouping_method: string;
  commit_count: number;
  total_additions: number;
  total_deletions: number;
  file_count: number;
  start_time: string;
  end_time: string;
}

const METHOD_COLORS: Record<string, string> = {
  pr: "purple",
  time_window: "blue",
  lone: "default",
};
const METHOD_LABELS: Record<string, string> = {
  pr: "PR-based",
  time_window: "Time Window",
  lone: "Standalone",
};

export default function WorkItemsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<WI[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<any>(null);
  const [repos, setRepos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [repoFilter, setRepoFilter] = useState<number | undefined>(undefined);
  const [methodFilter, setMethodFilter] = useState<string | undefined>(undefined);
  const [buildModal, setBuildModal] = useState(false);
  const [buildRepoId, setBuildRepoId] = useState<number | undefined>(undefined);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      getWorkItems({
        repo_id: repoFilter,
        grouping_method: methodFilter,
        limit: 100,
      }).then((r) => { setItems(r.data.items); setTotal(r.data.total); }),
      getWorkItemStats().then((r) => setStats(r.data)),
      getRepositories().then((r) => setRepos(r.data)),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [repoFilter, methodFilter]);

  const handleBuild = async () => {
    if (!buildRepoId) {
      message.warning("Chọn repository");
      return;
    }
    setBuilding(true);
    try {
      const res = await buildWorkItems({ repo_id: buildRepoId, rebuild: true });
      message.success(
        `Tạo ${res.data.work_items_created} work items (PR=${res.data.pr_based}, Time=${res.data.time_based}, Lone=${res.data.lone})`
      );
      setBuildModal(false);
      fetchData();
    } catch (err: any) {
      message.error("Failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setBuilding(false);
    }
  };

  const columns = [
    {
      title: "Title",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
      render: (v: string, r: WI) => (
        <div>
          <div style={{ fontWeight: 500 }}>
            {r.pr_number && <PullRequestOutlined style={{ marginRight: 4, color: "#722ed1" }} />}
            {v}
          </div>
        </div>
      ),
    },
    {
      title: "Developer",
      key: "dev",
      width: 150,
      render: (_: any, r: WI) => (
        <Space>
          <Avatar src={r.developer_avatar} size="small">{(r.developer || "?")[0]}</Avatar>
          <a onClick={() => navigate(`/developers/${r.developer_id}`)} style={{ cursor: "pointer" }}>
            {r.developer}
          </a>
        </Space>
      ),
    },
    {
      title: "Method",
      dataIndex: "grouping_method",
      key: "method",
      width: 110,
      render: (v: string) => (
        <Tag color={METHOD_COLORS[v] || "default"}>
          {METHOD_LABELS[v] || v}
        </Tag>
      ),
    },
    {
      title: "Commits",
      dataIndex: "commit_count",
      key: "commits",
      width: 80,
      sorter: (a: WI, b: WI) => a.commit_count - b.commit_count,
      render: (v: number) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: "+/-",
      key: "changes",
      width: 130,
      render: (_: any, r: WI) => (
        <Space size={4}>
          <Text type="success" style={{ fontSize: 12 }}>
            <PlusOutlined style={{ fontSize: 10 }} /> {r.total_additions.toLocaleString()}
          </Text>
          <Text type="danger" style={{ fontSize: 12 }}>
            <MinusOutlined style={{ fontSize: 10 }} /> {r.total_deletions.toLocaleString()}
          </Text>
        </Space>
      ),
    },
    {
      title: <Tooltip title="Files"><FileOutlined /></Tooltip>,
      dataIndex: "file_count",
      key: "files",
      width: 55,
    },
    {
      title: "Repo",
      dataIndex: "repo",
      key: "repo",
      width: 140,
      ellipsis: true,
      render: (v: string) => v?.split("/")[1],
    },
    {
      title: "Time Range",
      key: "time",
      width: 200,
      render: (_: any, r: WI) => {
        if (!r.start_time) return "—";
        const s = new Date(r.start_time);
        const e = new Date(r.end_time);
        if (r.start_time === r.end_time) return s.toLocaleString("vi-VN");
        return `${s.toLocaleString("vi-VN")} → ${e.toLocaleTimeString("vi-VN")}`;
      },
    },
  ];

  if (loading && items.length === 0) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>;
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            <AppstoreOutlined style={{ marginRight: 8 }} />
            Work Items ({total})
          </Title>
          <Text type="secondary">Commits được gom thành cụm công việc logic</Text>
        </div>
        <Space>
          <Select
            value={repoFilter}
            onChange={setRepoFilter}
            allowClear
            placeholder="Tất cả repos"
            style={{ width: 200 }}
            options={repos.map((r: any) => ({ label: r.full_name, value: r.id }))}
          />
          <Select
            value={methodFilter}
            onChange={setMethodFilter}
            allowClear
            placeholder="Tất cả methods"
            style={{ width: 150 }}
            options={[
              { label: "PR-based", value: "pr" },
              { label: "Time Window", value: "time_window" },
              { label: "Standalone", value: "lone" },
            ]}
          />
          <Button
            type="primary"
            icon={<BuildOutlined />}
            onClick={() => setBuildModal(true)}
          >
            Build Work Items
          </Button>
        </Space>
      </div>

      {/* Stats row */}
      {stats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic title="Total" value={stats.total_work_items}
                prefix={<AppstoreOutlined />} valueStyle={{ color: "#1677ff" }} />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic title="PR-based" value={stats.by_method?.pr || 0}
                prefix={<PullRequestOutlined />} valueStyle={{ color: "#722ed1" }} />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic title="Time Window" value={stats.by_method?.time_window || 0}
                prefix={<ClockCircleOutlined />} valueStyle={{ color: "#1677ff" }} />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic title="Standalone" value={stats.by_method?.lone || 0}
                prefix={<UserOutlined />} valueStyle={{ color: "#999" }} />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        {items.length > 0 ? (
          <Table
            dataSource={items}
            columns={columns}
            rowKey="id"
            size="middle"
            pagination={{ pageSize: 20, showSizeChanger: true }}
          />
        ) : (
          <Empty description="Chưa có work items. Bấm 'Build Work Items' để tạo." />
        )}
      </Card>

      {/* Build Modal */}
      <Modal
        title="Build Work Items"
        open={buildModal}
        onOk={handleBuild}
        onCancel={() => setBuildModal(false)}
        confirmLoading={building}
        okText="Build"
      >
        <p>Chọn repository để gom commits thành work items:</p>
        <Select
          value={buildRepoId}
          onChange={setBuildRepoId}
          placeholder="Chọn repo"
          style={{ width: "100%" }}
          options={repos.map((r: any) => ({ label: r.full_name, value: r.id }))}
        />
        <p style={{ marginTop: 8 }}>
          <Text type="secondary">Rebuild sẽ xóa tất cả work items cũ và tạo lại.</Text>
        </p>
      </Modal>
    </div>
  );
}
