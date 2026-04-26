import { useEffect, useMemo, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu, theme, ConfigProvider, Typography, Space, Tag, Button, Spin } from "antd";
import {
  DashboardOutlined,
  TeamOutlined,
  CodeOutlined,
  PullRequestOutlined,
  SettingOutlined,
  GithubOutlined,
  AppstoreOutlined,
  TrophyOutlined,
  ExperimentOutlined,
  LogoutOutlined,
  PlayCircleOutlined,
} from "@ant-design/icons";

import DashboardPage from "./pages/DashboardPage";
import DevelopersPage from "./pages/DevelopersPage";
import DeveloperDetailPage from "./pages/DeveloperDetailPage";
import RepositoriesPage from "./pages/RepositoriesPage";
import RepositoryDetailPage from "./pages/RepositoryDetailPage";
import PullRequestsPage from "./pages/PullRequestsPage";
import WorkItemsPage from "./pages/WorkItemsPage";
import RankingPage from "./pages/RankingPage";
import AnalysisPage from "./pages/AnalysisPage";
import AdminPage from "./pages/AdminPage";
import LoginPage from "./pages/LoginPage";
import NewEvaluationPage from "./pages/evaluations/NewEvaluationPage";
import EvaluationProgressPage from "./pages/evaluations/EvaluationProgressPage";
import EvaluationReportPage from "./pages/evaluations/EvaluationReportPage";
import {
  clearStoredAuth,
  getCurrentUser,
  getStoredToken,
  getStoredUser,
  setStoredAuth,
  type AuthUser,
} from "./api/client";

const { Header, Sider, Content, Footer } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "Dashboard" },
  { key: "/evaluations/new", icon: <PlayCircleOutlined />, label: "Evaluations" },
  { key: "/ranking", icon: <TrophyOutlined />, label: "Ranking" },
  { key: "/developers", icon: <TeamOutlined />, label: "Developers" },
  { key: "/repositories", icon: <CodeOutlined />, label: "Repositories" },
  { key: "/work-items", icon: <AppstoreOutlined />, label: "Work Items" },
  { key: "/analysis", icon: <ExperimentOutlined />, label: "AI Analysis" },
  { key: "/pull-requests", icon: <PullRequestOutlined />, label: "Pull Requests" },
  { key: "/admin", icon: <SettingOutlined />, label: "Admin" },
];

type AppLayoutProps = {
  currentUser: AuthUser;
  onLogout: () => void;
};

function AppLayout({ currentUser, onLogout }: AppLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { token: themeToken } = theme.useToken();
  const canAccessAdmin = currentUser.role === "admin" || currentUser.role === "lead";

  const visibleMenuItems = useMemo(
    () => menuItems.filter((item) => (
      item.key === "/admin" || item.key === "/evaluations/new" ? canAccessAdmin : true
    )),
    [canAccessAdmin]
  );

  // Determine active menu key based on current path
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.startsWith("/ranking")) return "/ranking";
    if (path.startsWith("/evaluations")) return "/evaluations/new";
    if (path.startsWith("/developers")) return "/developers";
    if (path.startsWith("/repositories")) return "/repositories";
    if (path.startsWith("/work-items")) return "/work-items";
    if (path.startsWith("/analysis")) return "/analysis";
    if (path.startsWith("/pull-requests")) return "/pull-requests";
    if (path.startsWith("/admin")) return "/admin";
    return "/";
  };

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
          selectedKeys={[getSelectedKey()]}
          items={visibleMenuItems}
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
            <Tag color="blue">v0.4.0</Tag>
          </Space>
          <Space>
            <Tag color={canAccessAdmin ? "purple" : "default"}>
              {currentUser.username} ({currentUser.role})
            </Tag>
            <Button icon={<LogoutOutlined />} onClick={onLogout}>
              Đăng xuất
            </Button>
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
            <Route
              path="/evaluations/new"
              element={canAccessAdmin ? <NewEvaluationPage /> : <Navigate to="/" replace />}
            />
            <Route path="/evaluations/:id/report" element={<EvaluationReportPage />} />
            <Route path="/evaluations/:id" element={<EvaluationProgressPage />} />
            <Route path="/ranking" element={<RankingPage />} />
            <Route path="/developers" element={<DevelopersPage />} />
            <Route path="/developers/:id" element={<DeveloperDetailPage />} />
            <Route path="/repositories" element={<RepositoriesPage />} />
            <Route path="/repositories/:id" element={<RepositoryDetailPage />} />
            <Route path="/work-items" element={<WorkItemsPage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/pull-requests" element={<PullRequestsPage />} />
            <Route
              path="/admin"
              element={canAccessAdmin ? <AdminPage /> : <Navigate to="/" replace />}
            />
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
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(getStoredUser());
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setAuthLoading(false);
      return;
    }

    getCurrentUser()
      .then((res) => {
        setStoredAuth(token, res.data.user);
        setCurrentUser(res.data.user);
      })
      .catch(() => {
        clearStoredAuth();
        setCurrentUser(null);
      })
      .finally(() => setAuthLoading(false));
  }, []);

  const handleLogout = () => {
    clearStoredAuth();
    setCurrentUser(null);
  };

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
      {authLoading ? (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Spin size="large" />
        </div>
      ) : currentUser ? (
        <BrowserRouter>
          <AppLayout currentUser={currentUser} onLogout={handleLogout} />
        </BrowserRouter>
      ) : (
        <LoginPage onAuthenticated={setCurrentUser} />
      )}
    </ConfigProvider>
  );
}

export default App;
