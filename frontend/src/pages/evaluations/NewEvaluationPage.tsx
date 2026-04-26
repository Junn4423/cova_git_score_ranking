import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Alert, Button, Card, Checkbox, Form, Input, InputNumber, Select,
  Space, Typography, message,
} from "antd";
import { PlayCircleOutlined } from "@ant-design/icons";
import { createEvaluation } from "../../api/client";

const { Title, Text } = Typography;

export default function NewEvaluationPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      message.loading({ content: "Dang chay evaluation...", key: "evaluation" });
      const res = await createEvaluation(values);
      message.success({ content: "Evaluation da hoan tat", key: "evaluation" });
      navigate(`/evaluations/${res.data.evaluation_run_id}`);
    } catch (err: any) {
      message.error({
        content: err.response?.data?.detail || err.message || "Evaluation failed",
        key: "evaluation",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={3} style={{ margin: 0 }}>Tao evaluation repo</Title>
        <Text type="secondary">Nhap GitHub repo URL, chon khoang thoi gian, roi chay danh gia.</Text>
      </div>

      <Alert
        type="info"
        showIcon
        message="Evaluation hien chay dong bo"
        description="Request co the mat vai phut voi repo lon. Phase sau co the tach worker/background job neu can."
        style={{ marginBottom: 24 }}
      />

      <Card>
        <Form
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            repo_url: searchParams.get("repo") || "",
            period_days: 90,
            max_commit_pages: 5,
            max_pr_pages: 5,
            run_analysis: true,
            force_resync: false,
          }}
        >
          <Form.Item
            label="GitHub repo URL"
            name="repo_url"
            rules={[{ required: true, message: "Nhap repo URL hoac owner/repo" }]}
          >
            <Input placeholder="https://github.com/owner/repo" />
          </Form.Item>

          <Space size="large" wrap>
            <Form.Item label="Khoang thoi gian" name="period_days">
              <Select
                style={{ width: 160 }}
                options={[
                  { label: "7 ngay", value: 7 },
                  { label: "30 ngay", value: 30 },
                  { label: "90 ngay", value: 90 },
                  { label: "180 ngay", value: 180 },
                  { label: "365 ngay", value: 365 },
                ]}
              />
            </Form.Item>
            <Form.Item label="Commit pages" name="max_commit_pages">
              <InputNumber min={1} max={50} style={{ width: 130 }} />
            </Form.Item>
            <Form.Item label="PR pages" name="max_pr_pages">
              <InputNumber min={1} max={50} style={{ width: 130 }} />
            </Form.Item>
          </Space>

          <Form.Item name="run_analysis" valuePropName="checked">
            <Checkbox>Chay rule-based analysis</Checkbox>
          </Form.Item>
          <Form.Item name="force_resync" valuePropName="checked">
            <Checkbox>Force resync va tinh lai du lieu</Checkbox>
          </Form.Item>

          <Button
            type="primary"
            htmlType="submit"
            icon={<PlayCircleOutlined />}
            loading={submitting}
          >
            Bat dau danh gia
          </Button>
        </Form>
      </Card>
    </div>
  );
}
