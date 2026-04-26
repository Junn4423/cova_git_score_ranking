import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Alert, Avatar, Button, Card, Progress, Select, Space, Spin, Table,
  Tag, Tooltip, Typography, message,
} from "antd";
import {
  TrophyOutlined, ThunderboltOutlined, SafetyCertificateOutlined,
  RocketOutlined, SyncOutlined, LikeOutlined, DislikeOutlined,
} from "@ant-design/icons";
import { calculateScores, getRanking, getRepositories, getStoredUser } from "../api/client";

const { Title, Text } = Typography;

interface Repo {
  id: number;
  full_name: string;
  name: string;
}

interface RankedDev {
  rank: number;
  developer_id: number;
  repo_id: number | null;
  repo_full_name: string | null;
  scope: string;
  period_start: string;
  period_end: string;
  github_login: string;
  display_name: string;
  avatar_url: string;
  final_score: number;
  activity_score: number;
  quality_score: number;
  impact_score: number;
  confidence: number;
  top_positive_reasons: string[];
  top_negative_reasons: string[];
  calculated_at: string;
}

const parseRepoId = (value: string | null) => {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
};

export default function RankingPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [repos, setRepos] = useState<Repo[]>([]);
  const [repoId, setRepoId] = useState<number | undefined>(
    parseRepoId(searchParams.get("repo_id"))
  );
  const [ranking, setRanking] = useState<RankedDev[]>([]);
  const [loading, setLoading] = useState(false);
  const [reposLoading, setReposLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [days, setDays] = useState(90);
  const currentUser = getStoredUser();
  const canCalculate = currentUser?.role === "admin" || currentUser?.role === "lead";

  const selectedRepo = useMemo(
    () => repos.find((repo) => repo.id === repoId),
    [repos, repoId]
  );

  useEffect(() => {
    setReposLoading(true);
    getRepositories()
      .then((res) => setRepos(res.data))
      .catch((err) => {
        message.error("Khong tai duoc danh sach repository");
        console.error(err);
      })
      .finally(() => setReposLoading(false));
  }, []);

  useEffect(() => {
    const nextRepoId = parseRepoId(searchParams.get("repo_id"));
    setRepoId(nextRepoId);
  }, [searchParams]);

  const fetchRanking = (currentRepoId: number | undefined) => {
    if (!currentRepoId) {
      setRanking([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    getRanking({ repo_id: currentRepoId, period_days: days, limit: 50 })
      .then((res) => setRanking(res.data))
      .catch((err) => {
        message.error("Khong tai duoc ranking");
        console.error(err);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchRanking(repoId);
  }, [repoId, days]);

  const handleRepoChange = (value?: number) => {
    setRepoId(value);
    if (value) {
      setSearchParams({ repo_id: String(value) });
    } else {
      setSearchParams({});
    }
  };

  const handleCalc = async () => {
    if (!repoId) {
      message.warning("Hay chon repository truoc khi tinh diem");
      return;
    }
    if (!canCalculate) {
      message.error("Chi admin hoac lead moi duoc tinh diem");
      return;
    }

    setCalculating(true);
    try {
      const res = await calculateScores({ repo_id: repoId, period_days: days });
      message.success(res.data.message);
      fetchRanking(repoId);
    } catch (err: any) {
      message.error("Scoring failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setCalculating(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "#52c41a";
    if (score >= 60) return "#1677ff";
    if (score >= 40) return "#faad14";
    return "#ff4d4f";
  };

  const columns = [
    {
      title: "Rank",
      key: "rank",
      width: 70,
      render: (_: any, row: RankedDev) => (
        <Tag color={row.rank <= 3 ? "gold" : "default"} style={{ fontWeight: 700 }}>
          #{row.rank}
        </Tag>
      ),
    },
    {
      title: "Developer",
      key: "dev",
      render: (_: any, row: RankedDev) => (
        <Space>
          <Avatar src={row.avatar_url} size={36}>{(row.github_login || "?")[0]}</Avatar>
          <div>
            <div style={{ fontWeight: 600, fontSize: 14 }}>
              {row.display_name || row.github_login}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>@{row.github_login}</Text>
          </div>
        </Space>
      ),
    },
    {
      title: "Final Score",
      dataIndex: "final_score",
      key: "score",
      width: 140,
      sorter: (a: RankedDev, b: RankedDev) => a.final_score - b.final_score,
      render: (value: number) => (
        <Space>
          <Progress
            type="circle"
            percent={Math.round(value)}
            size={40}
            strokeColor={getScoreColor(value)}
            format={(percent) => (
              <span style={{ fontSize: 11, fontWeight: 700 }}>{percent}</span>
            )}
          />
          <Text strong style={{ fontSize: 16, color: getScoreColor(value) }}>
            {value.toFixed(1)}
          </Text>
        </Space>
      ),
    },
    {
      title: <Tooltip title="Activity (15%)"><ThunderboltOutlined /> Activity</Tooltip>,
      dataIndex: "activity_score",
      key: "activity",
      width: 100,
      render: (value: number) => (
        <Tag color={value >= 50 ? "green" : value >= 20 ? "blue" : "default"}>
          {value.toFixed(0)}
        </Tag>
      ),
    },
    {
      title: <Tooltip title="Quality (50%)"><SafetyCertificateOutlined /> Quality</Tooltip>,
      dataIndex: "quality_score",
      key: "quality",
      width: 100,
      render: (value: number) => (
        <Tag color={value >= 70 ? "green" : value >= 40 ? "blue" : "orange"}>
          {value.toFixed(0)}
        </Tag>
      ),
    },
    {
      title: <Tooltip title="Impact (35%)"><RocketOutlined /> Impact</Tooltip>,
      dataIndex: "impact_score",
      key: "impact",
      width: 100,
      render: (value: number) => (
        <Tag color={value >= 70 ? "green" : value >= 30 ? "blue" : "orange"}>
          {value.toFixed(0)}
        </Tag>
      ),
    },
    {
      title: "Confidence",
      dataIndex: "confidence",
      key: "confidence",
      width: 120,
      render: (value: number) => (
        <Progress
          percent={Math.round(value * 100)}
          size="small"
          strokeColor={value >= 0.5 ? "#1677ff" : "#faad14"}
          format={(percent) => `${percent}%`}
        />
      ),
    },
    {
      title: "Highlights",
      key: "highlights",
      width: 260,
      render: (_: any, row: RankedDev) => (
        <Space direction="vertical" size={2}>
          {(row.top_positive_reasons || []).slice(0, 1).map((reason, index) => (
            <Text key={`p${index}`} style={{ fontSize: 11, color: "#52c41a" }}>
              <LikeOutlined /> {reason}
            </Text>
          ))}
          {(row.top_negative_reasons || []).slice(0, 1).map((reason, index) => (
            <Text key={`n${index}`} style={{ fontSize: 11, color: "#faad14" }}>
              <DislikeOutlined /> {reason}
            </Text>
          ))}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <Title level={3} style={{ margin: 0 }}>
            <TrophyOutlined style={{ marginRight: 8, color: "#faad14" }} />
            {selectedRepo ? `Ranking trong repo ${selectedRepo.full_name}` : "Chon repo de xem ranking"}
          </Title>
          <Text type="secondary">
            Contribution Score = 15% Activity + 50% Quality + 35% Impact
          </Text>
        </div>
        <Space wrap>
          <Select
            allowClear
            showSearch
            loading={reposLoading}
            value={repoId}
            onChange={handleRepoChange}
            placeholder="Chon repository"
            optionFilterProp="label"
            style={{ width: 280 }}
            options={repos.map((repo) => ({ label: repo.full_name, value: repo.id }))}
          />
          <Select
            value={days}
            onChange={setDays}
            style={{ width: 130 }}
            options={[
              { label: "7 ngay", value: 7 },
              { label: "30 ngay", value: 30 },
              { label: "90 ngay", value: 90 },
              { label: "180 ngay", value: 180 },
            ]}
          />
          <Button
            type="primary"
            icon={<SyncOutlined />}
            onClick={handleCalc}
            loading={calculating}
            disabled={!repoId || !canCalculate}
          >
            Calculate Scores
          </Button>
        </Space>
      </div>

      {!repoId && (
        <Alert
          type="warning"
          showIcon
          message="Can chon repository"
          description="Ranking theo roadmap moi phai tinh trong mot repo cu the. Hay chon repo hoac mo /ranking?repo_id=ID."
          style={{ marginBottom: 24 }}
        />
      )}

      {repoId && ranking.length === 0 && !loading && (
        <Alert
          type="info"
          showIcon
          message={`Chua co du lieu scoring cho ${selectedRepo?.full_name || "repo nay"}`}
          description="Bam Calculate Scores de tinh diem trong dung repo dang chon."
          style={{ marginBottom: 24 }}
        />
      )}

      <Card>
        {loading ? (
          <div style={{ textAlign: "center", padding: 80 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Table
            dataSource={ranking}
            columns={columns}
            rowKey={(row) => `${row.repo_id}-${row.developer_id}`}
            size="middle"
            pagination={{ pageSize: 20 }}
            onRow={(row) => ({
              onClick: () => navigate(`/developers/${row.developer_id}?repo_id=${repoId}`),
              style: { cursor: "pointer" },
            })}
          />
        )}
      </Card>
    </div>
  );
}
