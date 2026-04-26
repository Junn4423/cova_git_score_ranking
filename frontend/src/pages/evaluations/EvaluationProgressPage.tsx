import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Result, Space, Spin, Steps, Tag, Typography } from "antd";
import { FileTextOutlined, ReloadOutlined, TrophyOutlined } from "@ant-design/icons";
import { getEvaluation } from "../../api/client";

const { Title, Text } = Typography;

const STEP_KEYS = ["sync_repo", "build_work_items", "run_analysis", "calculate_scores", "generate_report", "done"];

export default function EvaluationProgressPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [evaluation, setEvaluation] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchEvaluation = () => {
    if (!id) return;
    setLoading(true);
    getEvaluation(Number(id))
      .then((res) => setEvaluation(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchEvaluation();
  }, [id]);

  if (loading && !evaluation) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>;
  }

  if (!evaluation) {
    return <Result status="404" title="Evaluation not found" />;
  }

  const currentIndex = Math.max(0, STEP_KEYS.indexOf(evaluation.current_step || "sync_repo"));
  const status = evaluation.status === "failed" ? "error" : evaluation.status === "done" ? "finish" : "process";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, marginBottom: 20 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Evaluation #{evaluation.id}</Title>
          <Text type="secondary">{evaluation.repo_full_name}</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchEvaluation}>Refresh</Button>
          <Button
            icon={<TrophyOutlined />}
            onClick={() => navigate(`/ranking?repo_id=${evaluation.repo_id}`)}
          >
            Ranking repo
          </Button>
          <Button
            type="primary"
            icon={<FileTextOutlined />}
            disabled={evaluation.status !== "done"}
            onClick={() => navigate(`/evaluations/${evaluation.id}/report`)}
          >
            Xem report
          </Button>
        </Space>
      </div>

      {evaluation.status === "failed" && (
        <Alert
          type="error"
          showIcon
          message="Evaluation failed"
          description={evaluation.error_message}
          style={{ marginBottom: 24 }}
        />
      )}

      <Card style={{ marginBottom: 24 }}>
        <Steps
          current={currentIndex}
          status={status as any}
          items={[
            { title: "Sync repo" },
            { title: "Work items" },
            { title: "Analysis" },
            { title: "Scoring" },
            { title: "Report" },
            { title: "Done" },
          ]}
        />
      </Card>

      <Card>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Status">
            <Tag color={evaluation.status === "done" ? "green" : evaluation.status === "failed" ? "red" : "blue"}>
              {evaluation.status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Current step">{evaluation.current_step}</Descriptions.Item>
          <Descriptions.Item label="Period">{evaluation.period_start} to {evaluation.period_end}</Descriptions.Item>
          <Descriptions.Item label="Access mode">{evaluation.access_mode || "-"}</Descriptions.Item>
          <Descriptions.Item label="Sync completed">{evaluation.sync_completed_at || "-"}</Descriptions.Item>
          <Descriptions.Item label="Grouping completed">{evaluation.grouping_completed_at || "-"}</Descriptions.Item>
          <Descriptions.Item label="Analysis completed">{evaluation.analysis_completed_at || "-"}</Descriptions.Item>
          <Descriptions.Item label="Scoring completed">{evaluation.scoring_completed_at || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
