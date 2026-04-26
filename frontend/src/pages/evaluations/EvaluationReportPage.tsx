import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert, Avatar, Button, Card, Col, Descriptions, List, Progress,
  Result, Row, Space, Spin, Table, Tag, Typography,
} from "antd";
import { ArrowLeftOutlined, TrophyOutlined } from "@ant-design/icons";
import { getEvaluationReport } from "../../api/client";

const { Title, Text, Paragraph } = Typography;

export default function EvaluationReportPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getEvaluationReport(Number(id))
      .then((res) => setReport(res.data))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>;
  }

  if (!report) {
    return <Result status="404" title="Report not found" />;
  }

  const columns = [
    {
      title: "Rank",
      dataIndex: "rank_no",
      key: "rank",
      width: 80,
      render: (value: number) => <Tag color={value <= 3 ? "gold" : "default"}>#{value}</Tag>,
    },
    {
      title: "Developer",
      key: "developer",
      render: (_: any, row: any) => (
        <Space>
          <Avatar src={row.avatar_url}>{(row.github_login || "?")[0]}</Avatar>
          <div>
            <div style={{ fontWeight: 600 }}>{row.display_name || row.github_login}</div>
            <Text type="secondary">@{row.github_login}</Text>
          </div>
        </Space>
      ),
    },
    {
      title: "Final",
      dataIndex: "final_score",
      key: "final",
      width: 120,
      render: (value: number) => <Text strong>{value.toFixed(2)}</Text>,
    },
    {
      title: "Activity",
      dataIndex: "activity_score",
      key: "activity",
      width: 100,
      render: (value: number) => <Tag>{value.toFixed(0)}</Tag>,
    },
    {
      title: "Quality",
      dataIndex: "quality_score",
      key: "quality",
      width: 100,
      render: (value: number) => <Tag color="blue">{value.toFixed(0)}</Tag>,
    },
    {
      title: "Impact",
      dataIndex: "impact_score",
      key: "impact",
      width: 100,
      render: (value: number) => <Tag color="purple">{value.toFixed(0)}</Tag>,
    },
    {
      title: "Confidence",
      dataIndex: "confidence_score",
      key: "confidence",
      width: 140,
      render: (value: number) => <Progress percent={Math.round(value * 100)} size="small" />,
    },
  ];

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate(`/evaluations/${report.evaluation.id}`)}
        style={{ marginBottom: 16 }}
      >
        Back
      </Button>

      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, marginBottom: 20 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            Bao cao danh gia repo: {report.repo.full_name}
          </Title>
          <Text type="secondary">
            {report.summary.period_start} to {report.summary.period_end}
          </Text>
        </div>
        <Button
          icon={<TrophyOutlined />}
          onClick={() => navigate(`/ranking?repo_id=${report.repo.id}`)}
        >
          Ranking repo
        </Button>
      </div>

      {report.evaluation.status !== "done" && (
        <Alert
          type="warning"
          showIcon
          message="Evaluation chua done"
          description="Report co the chua day du neu evaluation dang loi hoac dang chay."
          style={{ marginBottom: 24 }}
        />
      )}

      <Card style={{ marginBottom: 24 }}>
        <Descriptions column={4} bordered size="small">
          <Descriptions.Item label="Developers">{report.summary.developer_count}</Descriptions.Item>
          <Descriptions.Item label="Commits">{report.summary.commit_count}</Descriptions.Item>
          <Descriptions.Item label="PRs">{report.summary.pull_request_count}</Descriptions.Item>
          <Descriptions.Item label="Work items">{report.summary.work_item_count}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="Bang xep hang" style={{ marginBottom: 24 }}>
        <Table
          dataSource={report.ranking}
          columns={columns}
          rowKey="developer_id"
          pagination={false}
        />
      </Card>

      <Row gutter={[16, 16]}>
        {report.ranking.map((item: any) => (
          <Col xs={24} lg={12} key={item.developer_id}>
            <Card
              title={
                <Space>
                  <Tag color="gold">#{item.rank_no}</Tag>
                  <Avatar src={item.avatar_url}>{(item.github_login || "?")[0]}</Avatar>
                  <span>{item.display_name || item.github_login}</span>
                </Space>
              }
            >
              <Paragraph>{item.summary_vi}</Paragraph>
              <List
                size="small"
                header={<Text strong>Diem manh</Text>}
                dataSource={item.strengths}
                renderItem={(value: string) => <List.Item>{value}</List.Item>}
              />
              <List
                size="small"
                header={<Text strong>Can cai thien</Text>}
                dataSource={item.weaknesses}
                renderItem={(value: string) => <List.Item>{value}</List.Item>}
              />
              <List
                size="small"
                header={<Text strong>Khuyen nghi</Text>}
                dataSource={item.recommendations}
                renderItem={(value: string) => <List.Item>{value}</List.Item>}
              />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
