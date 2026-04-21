import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Space,
  Typography,
  message,
} from "antd";
import { LockOutlined, UserOutlined } from "@ant-design/icons";

import { bootstrapAdmin, login, setStoredAuth, type AuthUser } from "../api/client";

const { Title, Text } = Typography;

type LoginPageProps = {
  onAuthenticated: (user: AuthUser) => void;
};

export default function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (mode: "login" | "bootstrap") => {
    const values = await form.validateFields();
    setLoading(true);
    try {
      const action = mode === "bootstrap" ? bootstrapAdmin : login;
      const res = await action(values);
      const { access_token: token, user } = res.data;
      setStoredAuth(token, user);
      onAuthenticated(user);
      message.success(
        mode === "bootstrap"
          ? "Khởi tạo admin đầu tiên thành công"
          : "Đăng nhập thành công"
      );
    } catch (err: any) {
      message.error(err.response?.data?.detail || "Không thể xác thực");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #f0f5ff 0%, #ffffff 100%)",
        padding: 24,
      }}
    >
      <Card style={{ width: 420, boxShadow: "0 12px 32px rgba(0,0,0,0.08)" }}>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <div>
            <Title level={3} style={{ marginBottom: 8 }}>
              Internal Login
            </Title>
            <Text type="secondary">
              Đăng nhập để truy cập dashboard nội bộ. Nếu hệ thống chưa có user nào,
              dùng nút khởi tạo admin đầu tiên.
            </Text>
          </div>

          <Alert
            type="info"
            showIcon
            message="Phase 6"
            description="Auth nội bộ dùng JWT. Admin/Lead mới xem được khu vực quản trị."
          />

          <Form form={form} layout="vertical">
            <Form.Item
              name="username"
              label="Username"
              rules={[{ required: true, message: "Nhập username" }]}
            >
              <Input prefix={<UserOutlined />} placeholder="admin" autoComplete="username" />
            </Form.Item>

            <Form.Item
              name="password"
              label="Password"
              rules={[{ required: true, message: "Nhập password" }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="********"
                autoComplete="current-password"
              />
            </Form.Item>

            <Space style={{ width: "100%", justifyContent: "space-between" }}>
              <Button type="primary" loading={loading} onClick={() => void handleSubmit("login")}>
                Đăng nhập
              </Button>
              <Button loading={loading} onClick={() => void handleSubmit("bootstrap")}>
                Khởi tạo admin đầu tiên
              </Button>
            </Space>
          </Form>
        </Space>
      </Card>
    </div>
  );
}
