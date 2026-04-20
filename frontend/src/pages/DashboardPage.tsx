import { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Typography, Alert, Spin, Space, Tag } from "antd";
import {
  CheckCircleOutlined,
  ApiOutlined,
  DatabaseOutlined,
  GithubOutlined,
  TeamOutlined,
  CodeOutlined,
  PullRequestOutlined,
} from "@ant-design/icons";
import { healthCheck } from "../api/client";

const { Title, Text } = Typography;

interface HealthData {
  status: string;
  service: string;
  version: string;
  database: {
    connected: boolean;
    error?: string;
  };
}

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    healthCheck()
      .then((res) => {
        setHealth(res.data);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || "Cannot connect to backend");
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <Title level={3}>🎯 Dashboard Tổng Quan</Title>
      <Text type="secondary" style={{ marginBottom: 24, display: "block" }}>
        Hệ thống phân tích đóng góp dev từ GitHub
      </Text>

      {loading && (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spin size="large" />
        </div>
      )}

      {error && (
        <Alert
          type="error"
          message="Không kết nối được Backend"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {health && (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} lg={6}>
              <Card
                hoverable
                style={{
                  borderLeft: health.status === "healthy" ? "4px solid #52c41a" : "4px solid #ff4d4f",
                }}
              >
                <Statistic
                  title={
                    <Space>
                      <ApiOutlined /> API Status
                    </Space>
                  }
                  value={health.status === "healthy" ? "Healthy" : "Degraded"}
                  valueStyle={{
                    color: health.status === "healthy" ? "#52c41a" : "#ff4d4f",
                  }}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card
                hoverable
                style={{
                  borderLeft: health.database.connected ? "4px solid #52c41a" : "4px solid #ff4d4f",
                }}
              >
                <Statistic
                  title={
                    <Space>
                      <DatabaseOutlined /> Database
                    </Space>
                  }
                  value={health.database.connected ? "Connected" : "Disconnected"}
                  valueStyle={{
                    color: health.database.connected ? "#52c41a" : "#ff4d4f",
                  }}
                  prefix={<DatabaseOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card hoverable style={{ borderLeft: "4px solid #1677ff" }}>
                <Statistic
                  title={
                    <Space>
                      <GithubOutlined /> Service
                    </Space>
                  }
                  value={health.service}
                  valueStyle={{ fontSize: 14, color: "#1677ff" }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card hoverable style={{ borderLeft: "4px solid #722ed1" }}>
                <Statistic
                  title={
                    <Space>
                      <CodeOutlined /> Version
                    </Space>
                  }
                  value={health.version}
                  valueStyle={{ fontSize: 16, color: "#722ed1" }}
                />
              </Card>
            </Col>
          </Row>

          <Title level={4} style={{ marginTop: 32 }}>📊 Thống kê (chưa có dữ liệu)</Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic title="Developers" value={0} prefix={<TeamOutlined />} />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic title="Repositories" value={0} prefix={<CodeOutlined />} />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic title="Pull Requests" value={0} prefix={<PullRequestOutlined />} />
              </Card>
            </Col>
          </Row>

          <div style={{ marginTop: 24 }}>
            <Tag color="green">Tuần 1: Project Setup ✅</Tag>
            <Tag color="orange">Tuần 2: Data Ingestion ⏳</Tag>
          </div>
        </>
      )}
    </div>
  );
}
