import { useState } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, theme, ConfigProvider, Typography, Space, Tag } from "antd";
import {
  DashboardOutlined,
  TeamOutlined,
  CodeOutlined,
  PullRequestOutlined,
  SettingOutlined,
  GithubOutlined,
} from "@ant-design/icons";

import DashboardPage from "./pages/DashboardPage";

const { Header, Sider, Content, Footer } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "Dashboard" },
  { key: "/developers", icon: <TeamOutlined />, label: "Developers" },
  { key: "/repositories", icon: <CodeOutlined />, label: "Repositories" },
  { key: "/pull-requests", icon: <PullRequestOutlined />, label: "Pull Requests" },
  { key: "/admin", icon: <SettingOutlined />, label: "Admin" },
];

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { token: themeToken } = theme.useToken();

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{
          background: "linear-gradient(180deg, #001529 0%, #002140 100%)",
        }}
      >
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            borderBottom: "1px solid rgba(255,255,255,0.1)",
          }}
        >
          <GithubOutlined style={{ fontSize: 24, color: "#1677ff" }} />
          {!collapsed && (
            <Title level={5} style={{ margin: 0, color: "#fff", whiteSpace: "nowrap" }}>
              Eng Analytics
            </Title>
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: "0 24px",
            background: themeToken.colorBgContainer,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
            boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
          }}
        >
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              Engineering Contribution Analytics
            </Title>
            <Tag color="blue">v0.1.0</Tag>
          </Space>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: themeToken.colorBgContainer,
            borderRadius: themeToken.borderRadiusLG,
            minHeight: 360,
          }}
        >
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/developers" element={<div>Developers (coming soon)</div>} />
            <Route path="/repositories" element={<div>Repositories (coming soon)</div>} />
            <Route path="/pull-requests" element={<div>Pull Requests (coming soon)</div>} />
            <Route path="/admin" element={<div>Admin Settings (coming soon)</div>} />
          </Routes>
        </Content>
        <Footer style={{ textAlign: "center", color: themeToken.colorTextSecondary }}>
          Engineering Contribution Analytics ©2026 — Internal Tool
        </Footer>
      </Layout>
    </Layout>
  );
}

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#1677ff",
          borderRadius: 8,
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
      }}
    >
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
