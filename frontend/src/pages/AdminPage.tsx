import { useEffect, useState } from "react";
import {
  Card, Typography, Space, Spin, Button, Row, Col, Statistic,
  message, Table, Tag, Modal, InputNumber, Descriptions, Divider,
  Switch, Alert,
} from "antd";
import {
  SettingOutlined, SyncOutlined, DatabaseOutlined, ExperimentOutlined,
  TrophyOutlined, AppstoreOutlined, TeamOutlined, CodeOutlined,
  PullRequestOutlined, FileTextOutlined,
} from "@ant-design/icons";
import api from "../api/client";

const { Title, Text } = Typography;

export default function AdminPage() {
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [configs, setConfigs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [recalcModal, setRecalcModal] = useState(false);
  const [recalcOpts, setRecalcOpts] = useState({
    period_days: 90, rebuild_work_items: false, rerun_analysis: false,
  });
  const [editModal, setEditModal] = useState(false);
  const [editKey, setEditKey] = useState("");
  const [editValue, setEditValue] = useState<string>("");

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      api.get("/api/admin/system-info").then((r: any) => setSystemInfo(r.data)),
      api.get("/api/admin/configs").then((r: any) => setConfigs(r.data)),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const handleRecalculate = async () => {
    setRecalculating(true);
    try {
      const res = await api.post("/api/admin/recalculate", recalcOpts);
      const steps = res.data.steps || [];
      message.success(`Done! ${steps.length} steps completed.`);
      setRecalcModal(false);
      fetchData();
    } catch (err: any) {
      message.error("Failed: " + (err.response?.data?.detail || err.message));
    } finally { setRecalculating(false); }
  };

  const handleSaveConfig = async () => {
    try {
      let parsedValue: any;
      try { parsedValue = JSON.parse(editValue); } catch { parsedValue = editValue; }
      await api.put(`/api/admin/configs/${editKey}`, { value: parsedValue });
      message.success(`Config '${editKey}' updated`);
      setEditModal(false);
      fetchData();
    } catch (err: any) {
      message.error("Failed to save: " + (err.response?.data?.detail || err.message));
    }
  };

  const configColumns = [
    {
      title: "Key",
      dataIndex: "key",
      key: "key",
      render: (v: string) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: "Value",
      dataIndex: "value",
      key: "value",
      render: (v: any) => (
        <Text code style={{ fontSize: 12 }}>
          {typeof v === "object" ? JSON.stringify(v) : String(v)}
        </Text>
      ),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "desc",
      ellipsis: true,
    },
    {
      title: "Action",
      key: "action",
      width: 80,
      render: (_: any, r: any) => (
        <Button size="small" onClick={() => {
          setEditKey(r.key);
          setEditValue(typeof r.value === "object" ? JSON.stringify(r.value, null, 2) : String(r.value));
          setEditModal(true);
        }}>
          Edit
        </Button>
      ),
    },
  ];

  if (loading) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>;
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            <SettingOutlined style={{ marginRight: 8 }} />
            Admin Settings
          </Title>
          <Text type="secondary">Quản lý cấu hình hệ thống và scoring weights</Text>
        </div>
        <Button type="primary" icon={<SyncOutlined />} onClick={() => setRecalcModal(true)}>
          Full Recalculate
        </Button>
      </div>

      {/* System info */}
      {systemInfo && (
        <Row gutter={[12, 12]} style={{ marginBottom: 24 }}>
          <Col xs={12} sm={6} md={3}>
            <Card size="small"><Statistic title="Repos" value={systemInfo.repositories}
              prefix={<CodeOutlined />} /></Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small"><Statistic title="Developers" value={systemInfo.developers}
              prefix={<TeamOutlined />} /></Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small"><Statistic title="Commits" value={systemInfo.commits}
              prefix={<DatabaseOutlined />} /></Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small"><Statistic title="PRs" value={systemInfo.pull_requests}
              prefix={<PullRequestOutlined />} /></Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small"><Statistic title="Reviews" value={systemInfo.reviews}
              prefix={<FileTextOutlined />} /></Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small"><Statistic title="Work Items" value={systemInfo.work_items}
              prefix={<AppstoreOutlined />} /></Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small"><Statistic title="AI Analyses" value={systemInfo.ai_analyses}
              prefix={<ExperimentOutlined />} /></Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card size="small"><Statistic title="Scores" value={systemInfo.score_snapshots}
              prefix={<TrophyOutlined />} /></Card>
          </Col>
        </Row>
      )}

      {/* Config table */}
      <Card
        title={<Space><SettingOutlined /> App Configurations</Space>}
        style={{ marginBottom: 24 }}
      >
        <Table dataSource={configs} columns={configColumns} rowKey="key"
          size="small" pagination={false} />
      </Card>

      {/* Scoring weights info */}
      <Card title="Scoring Formula" style={{ marginBottom: 24 }}>
        <Alert
          type="info"
          showIcon
          message="Contribution Score = 15% Activity + 50% Quality + 35% Impact"
          description={
            <div style={{ marginTop: 8 }}>
              <p><strong>Activity (15%):</strong> Active days, merged PRs, reviews given</p>
              <p><strong>Quality (50%):</strong> Meaningful ratio, coherence, merge ratio, message alignment (AI), message quality</p>
              <p><strong>Impact (35%):</strong> Complexity-weighted lines, bugfix/feature/security bonuses (AI), meaningful ratio</p>
            </div>
          }
        />
      </Card>

      {/* Recalculate modal */}
      <Modal title="Full Recalculate" open={recalcModal} onOk={handleRecalculate}
        onCancel={() => setRecalcModal(false)} confirmLoading={recalculating} okText="Recalculate">
        <Space direction="vertical" style={{ width: "100%" }}>
          <div>
            <Text strong>Period (days):</Text>
            <InputNumber value={recalcOpts.period_days} min={7} max={365}
              onChange={(v) => setRecalcOpts({ ...recalcOpts, period_days: v || 90 })}
              style={{ marginLeft: 8, width: 100 }} />
          </div>
          <div style={{ marginTop: 12 }}>
            <Space>
              <Switch checked={recalcOpts.rebuild_work_items}
                onChange={(v) => setRecalcOpts({ ...recalcOpts, rebuild_work_items: v })} />
              <Text>Rebuild Work Items</Text>
            </Space>
          </div>
          <div>
            <Space>
              <Switch checked={recalcOpts.rerun_analysis}
                onChange={(v) => setRecalcOpts({ ...recalcOpts, rerun_analysis: v })} />
              <Text>Re-run AI Analysis</Text>
            </Space>
          </div>
          <Alert type="warning" message="Recalculate sẽ xóa scores cũ và tính lại từ đầu." style={{ marginTop: 8 }} />
        </Space>
      </Modal>

      {/* Edit config modal */}
      <Modal title={`Edit: ${editKey}`} open={editModal} onOk={handleSaveConfig}
        onCancel={() => setEditModal(false)} okText="Save">
        <textarea
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          rows={6}
          style={{
            width: "100%", fontFamily: "monospace", fontSize: 13,
            padding: 12, borderRadius: 6, border: "1px solid #d9d9d9",
          }}
        />
        <Text type="secondary" style={{ fontSize: 11 }}>JSON format cho objects/arrays</Text>
      </Modal>
    </div>
  );
}
