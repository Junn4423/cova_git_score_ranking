import { useEffect, useState } from "react";
import {
  Card, Table, Typography, Space, Tag, Spin, Select, Button,
  Row, Col, Statistic, message, Tooltip, Progress, Empty, Modal,
} from "antd";
import {
  ExperimentOutlined, BugOutlined, RocketOutlined, FileTextOutlined,
  ToolOutlined, SafetyCertificateOutlined, SettingOutlined, SyncOutlined,
  ThunderboltOutlined, AlertOutlined, CheckCircleOutlined, CodeOutlined,
} from "@ant-design/icons";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip as ReTooltip, Legend,
} from "recharts";
import {
  getRepositories,
} from "../api/client";
import api from "../api/client";

const { Title, Text } = Typography;

const TYPE_COLORS: Record<string, string> = {
  feature: "#1677ff", bugfix: "#ff4d4f", refactor: "#722ed1",
  test: "#52c41a", docs: "#faad14", config: "#13c2c2",
  chore: "#999", security: "#f5222d", performance: "#fa8c16",
};
const TYPE_ICONS: Record<string, React.ReactNode> = {
  feature: <RocketOutlined />, bugfix: <BugOutlined />, refactor: <ToolOutlined />,
  test: <CheckCircleOutlined />, docs: <FileTextOutlined />, config: <SettingOutlined />,
  chore: <CodeOutlined />, security: <SafetyCertificateOutlined />, performance: <ThunderboltOutlined />,
};

export default function AnalysisPage() {
  const [results, setResults] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<any>(null);
  const [repos, setRepos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [repoFilter, setRepoFilter] = useState<number | undefined>(undefined);
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);
  const [runModal, setRunModal] = useState(false);
  const [runRepoId, setRunRepoId] = useState<number | undefined>(undefined);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      api.get("/api/analysis/results", {
        params: { repo_id: repoFilter, change_type: typeFilter, limit: 100 },
      }).then((r: any) => { setResults(r.data.items); setTotal(r.data.total); }),
      api.get("/api/analysis/stats").then((r: any) => setStats(r.data)),
      getRepositories().then((r) => setRepos(r.data)),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [repoFilter, typeFilter]);

  const handleRun = async () => {
    if (!runRepoId) { message.warning("Chọn repository"); return; }
    setRunning(true);
    try {
      const res = await api.post("/api/analysis/run", { repo_id: runRepoId, force: true });
      message.success(`Analyzed ${res.data.analyzed}/${res.data.total_commits} commits (${res.data.errors} errors)`);
      setRunModal(false);
      fetchData();
    } catch (err: any) {
      message.error("Failed: " + (err.response?.data?.detail || err.message));
    } finally { setRunning(false); }
  };

  const pieData = stats?.by_change_type
    ? Object.entries(stats.by_change_type).map(([name, value]) => ({ name, value }))
    : [];

  const columns = [
    {
      title: "Commit",
      key: "commit",
      width: 300,
      render: (_: any, r: any) => (
        <div>
          <div style={{ fontWeight: 500, fontSize: 13 }}>{r.summary?.slice(0, 80)}</div>
          <Text type="secondary" style={{ fontSize: 11 }}>{r.sha} · {r.repo?.split("/")[1]}</Text>
        </div>
      ),
    },
    {
      title: "Type",
      dataIndex: "change_type",
      key: "type",
      width: 110,
      render: (v: string) => (
        <Tag icon={TYPE_ICONS[v]} color={TYPE_COLORS[v] || "default"}>
          {v}
        </Tag>
      ),
    },
    {
      title: <Tooltip title="Complexity 0-100">Complexity</Tooltip>,
      dataIndex: "complexity_score",
      key: "complexity",
      width: 100,
      sorter: (a: any, b: any) => a.complexity_score - b.complexity_score,
      render: (v: number) => (
        <Progress percent={v} size="small"
          strokeColor={v >= 70 ? "#ff4d4f" : v >= 40 ? "#faad14" : "#52c41a"}
          format={(p) => `${p}`} />
      ),
    },
    {
      title: <Tooltip title="Risk 0-100">Risk</Tooltip>,
      dataIndex: "risk_score",
      key: "risk",
      width: 90,
      sorter: (a: any, b: any) => a.risk_score - b.risk_score,
      render: (v: number) => (
        <Tag color={v >= 50 ? "red" : v >= 20 ? "orange" : "green"}>
          {v >= 50 && <AlertOutlined />} {v}
        </Tag>
      ),
    },
    {
      title: <Tooltip title="Message Alignment">Alignment</Tooltip>,
      dataIndex: "message_alignment_score",
      key: "alignment",
      width: 100,
      render: (v: number) => (
        <Progress percent={v} size="small"
          strokeColor={v >= 60 ? "#52c41a" : v >= 30 ? "#faad14" : "#ff4d4f"}
          format={(p) => `${p}`} />
      ),
    },
    {
      title: "Tests",
      dataIndex: "test_presence",
      key: "tests",
      width: 55,
      render: (v: boolean) => v ? <CheckCircleOutlined style={{ color: "#52c41a" }} /> : <Text type="secondary">—</Text>,
    },
    {
      title: "Author",
      key: "author",
      width: 110,
      ellipsis: true,
      render: (_: any, r: any) => r.author || "—",
    },
    {
      title: "Date",
      key: "date",
      width: 100,
      render: (_: any, r: any) => r.committed_at ? new Date(r.committed_at).toLocaleDateString("vi-VN") : "—",
    },
  ];

  if (loading && results.length === 0) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>;
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            <ExperimentOutlined style={{ marginRight: 8 }} />
            AI Analysis ({total})
          </Title>
          <Text type="secondary">Rule-based commit classification & scoring</Text>
        </div>
        <Space>
          <Select value={repoFilter} onChange={setRepoFilter} allowClear
            placeholder="Tất cả repos" style={{ width: 200 }}
            options={repos.map((r: any) => ({ label: r.full_name, value: r.id }))} />
          <Select value={typeFilter} onChange={setTypeFilter} allowClear
            placeholder="Tất cả types" style={{ width: 140 }}
            options={Object.keys(TYPE_COLORS).map((t) => ({ label: t, value: t }))} />
          <Button type="primary" icon={<ExperimentOutlined />} onClick={() => setRunModal(true)}>
            Run Analysis
          </Button>
        </Space>
      </div>

      {/* Stats row */}
      {stats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={5}>
            <Card><Statistic title="Total Analyzed" value={stats.total_analyzed}
              prefix={<ExperimentOutlined />} valueStyle={{ color: "#1677ff" }} /></Card>
          </Col>
          <Col xs={24} sm={5}>
            <Card><Statistic title="Avg Complexity" value={stats.avg_complexity}
              suffix="/100" valueStyle={{ color: stats.avg_complexity >= 50 ? "#faad14" : "#52c41a" }} /></Card>
          </Col>
          <Col xs={24} sm={5}>
            <Card><Statistic title="Avg Risk" value={stats.avg_risk}
              suffix="/100" valueStyle={{ color: stats.avg_risk >= 30 ? "#ff4d4f" : "#52c41a" }} /></Card>
          </Col>
          <Col xs={24} sm={5}>
            <Card><Statistic title="Avg Alignment" value={stats.avg_alignment}
              suffix="/100" valueStyle={{ color: stats.avg_alignment >= 50 ? "#52c41a" : "#faad14" }} /></Card>
          </Col>
          <Col xs={24} sm={4}>
            <Card><Statistic title="Confidence" value={(stats.avg_confidence * 100).toFixed(0)}
              suffix="%" valueStyle={{ color: "#1677ff" }} /></Card>
          </Col>
        </Row>
      )}

      {/* Pie chart + table */}
      <Row gutter={[16, 16]}>
        {pieData.length > 0 && (
          <Col xs={24} md={8}>
            <Card title={<Space><ExperimentOutlined /> Change Type Distribution</Space>}>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                    outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {pieData.map((entry: any) => (
                      <Cell key={entry.name} fill={TYPE_COLORS[entry.name] || "#999"} />
                    ))}
                  </Pie>
                  <ReTooltip />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        )}
        <Col xs={24} md={pieData.length > 0 ? 16 : 24}>
          <Card>
            {results.length > 0 ? (
              <Table dataSource={results} columns={columns} rowKey="id" size="small"
                pagination={{ pageSize: 15, showSizeChanger: true }} />
            ) : (
              <Empty description="Chưa có analysis data. Bấm 'Run Analysis'." />
            )}
          </Card>
        </Col>
      </Row>

      <Modal title="Run AI Analysis" open={runModal} onOk={handleRun}
        onCancel={() => setRunModal(false)} confirmLoading={running} okText="Analyze">
        <p>Chọn repository để phân tích commit:</p>
        <Select value={runRepoId} onChange={setRunRepoId} placeholder="Chọn repo"
          style={{ width: "100%" }}
          options={repos.map((r: any) => ({ label: r.full_name, value: r.id }))} />
        <p style={{ marginTop: 8 }}>
          <Text type="secondary">Force re-analyze tất cả commits.</Text>
        </p>
      </Modal>
    </div>
  );
}
