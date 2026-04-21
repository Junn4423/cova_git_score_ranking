import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card, Table, Typography, Space, Tag, Spin, Select, Avatar,
  Tooltip, Button, message, Progress, Alert,
} from "antd";
import {
  TrophyOutlined, ThunderboltOutlined, SafetyCertificateOutlined,
  RocketOutlined, SyncOutlined,
  StarOutlined, LikeOutlined, DislikeOutlined,
} from "@ant-design/icons";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip as ReTooltip,
} from "recharts";
import { getRanking, calculateScores } from "../api/client";

const { Title, Text } = Typography;

interface RankedDev {
  rank: number;
  developer_id: number;
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

const MEDAL = ["🥇", "🥈", "🥉"];

export default function RankingPage() {
  const navigate = useNavigate();
  const [ranking, setRanking] = useState<RankedDev[]>([]);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [days, setDays] = useState(90);

  const fetchRanking = () => {
    setLoading(true);
    getRanking({ period_days: days, limit: 50 })
      .then((r) => setRanking(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchRanking(); }, [days]);

  const handleCalc = async () => {
    setCalculating(true);
    try {
      const res = await calculateScores({ period_days: days });
      message.success(res.data.message);
      fetchRanking();
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
      width: 60,
      render: (_: any, r: RankedDev) => (
        <span style={{ fontSize: r.rank <= 3 ? 22 : 16, fontWeight: 700 }}>
          {r.rank <= 3 ? MEDAL[r.rank - 1] : `#${r.rank}`}
        </span>
      ),
    },
    {
      title: "Developer",
      key: "dev",
      render: (_: any, r: RankedDev) => (
        <Space>
          <Avatar src={r.avatar_url} size={36}>{(r.github_login || "?")[0]}</Avatar>
          <div>
            <div style={{ fontWeight: 600, fontSize: 14 }}>
              {r.display_name || r.github_login}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>@{r.github_login}</Text>
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
      render: (v: number) => (
        <Space>
          <Progress
            type="circle"
            percent={v}
            size={40}
            strokeColor={getScoreColor(v)}
            format={(p) => <span style={{ fontSize: 11, fontWeight: 700 }}>{p?.toFixed(0)}</span>}
          />
          <Text strong style={{ fontSize: 16, color: getScoreColor(v) }}>
            {v.toFixed(1)}
          </Text>
        </Space>
      ),
    },
    {
      title: <Tooltip title="Activity (15%)"><ThunderboltOutlined /> Activity</Tooltip>,
      dataIndex: "activity_score",
      key: "activity",
      width: 90,
      render: (v: number) => (
        <Tag color={v >= 50 ? "green" : v >= 20 ? "blue" : "default"}>
          {v.toFixed(0)}
        </Tag>
      ),
    },
    {
      title: <Tooltip title="Quality (50%)"><SafetyCertificateOutlined /> Quality</Tooltip>,
      dataIndex: "quality_score",
      key: "quality",
      width: 90,
      render: (v: number) => (
        <Tag color={v >= 70 ? "green" : v >= 40 ? "blue" : "orange"}>
          {v.toFixed(0)}
        </Tag>
      ),
    },
    {
      title: <Tooltip title="Impact (35%)"><RocketOutlined /> Impact</Tooltip>,
      dataIndex: "impact_score",
      key: "impact",
      width: 90,
      render: (v: number) => (
        <Tag color={v >= 70 ? "green" : v >= 30 ? "blue" : "orange"}>
          {v.toFixed(0)}
        </Tag>
      ),
    },
    {
      title: "Confidence",
      dataIndex: "confidence",
      key: "confidence",
      width: 100,
      render: (v: number) => (
        <Progress
          percent={Math.round(v * 100)}
          size="small"
          strokeColor={v >= 0.5 ? "#1677ff" : "#faad14"}
          format={(p) => `${p}%`}
        />
      ),
    },
    {
      title: "Highlights",
      key: "highlights",
      width: 250,
      render: (_: any, r: RankedDev) => (
        <Space direction="vertical" size={2}>
          {(r.top_positive_reasons || []).slice(0, 1).map((reason, i) => (
            <Text key={`p${i}`} style={{ fontSize: 11, color: "#52c41a" }}>
              <LikeOutlined /> {reason}
            </Text>
          ))}
          {(r.top_negative_reasons || []).slice(0, 1).map((reason, i) => (
            <Text key={`n${i}`} style={{ fontSize: 11, color: "#faad14" }}>
              <DislikeOutlined /> {reason}
            </Text>
          ))}
        </Space>
      ),
    },
  ];

  if (loading && ranking.length === 0) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>;
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            <TrophyOutlined style={{ marginRight: 8, color: "#faad14" }} />
            Developer Ranking
          </Title>
          <Text type="secondary">
            Contribution Score = 15% Activity + 50% Quality + 35% Impact
          </Text>
        </div>
        <Space>
          <Select
            value={days}
            onChange={setDays}
            style={{ width: 130 }}
            options={[
              { label: "7 ngày", value: 7 },
              { label: "30 ngày", value: 30 },
              { label: "90 ngày", value: 90 },
              { label: "180 ngày", value: 180 },
            ]}
          />
          <Button
            type="primary"
            icon={<SyncOutlined />}
            onClick={handleCalc}
            loading={calculating}
          >
            Calculate Scores
          </Button>
        </Space>
      </div>

      {ranking.length === 0 && (
        <Alert
          type="info"
          showIcon
          message="Chưa có dữ liệu scoring"
          description="Bấm 'Calculate Scores' để tính điểm cho tất cả developers."
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Radar chart for top 3 */}
      {ranking.length >= 2 && (
        <Card
          title={<Space><StarOutlined style={{ color: "#faad14" }} /> Top Contributors Radar</Space>}
          style={{ marginBottom: 24 }}
        >
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={[
              { metric: "Activity", ...Object.fromEntries(ranking.slice(0, 3).map((r) => [r.github_login, r.activity_score])) },
              { metric: "Quality", ...Object.fromEntries(ranking.slice(0, 3).map((r) => [r.github_login, r.quality_score])) },
              { metric: "Impact", ...Object.fromEntries(ranking.slice(0, 3).map((r) => [r.github_login, r.impact_score])) },
              { metric: "Final", ...Object.fromEntries(ranking.slice(0, 3).map((r) => [r.github_login, r.final_score])) },
            ]}>
              <PolarGrid />
              <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
              {ranking.slice(0, 3).map((r, i) => (
                <Radar
                  key={r.developer_id}
                  name={r.github_login}
                  dataKey={r.github_login}
                  stroke={["#1677ff", "#722ed1", "#13c2c2"][i]}
                  fill={["#1677ff", "#722ed1", "#13c2c2"][i]}
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
              ))}
              <ReTooltip />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
      )}

      <Card>
        <Table
          dataSource={ranking}
          columns={columns}
          rowKey="developer_id"
          size="middle"
          pagination={{ pageSize: 20 }}
          onRow={(r) => ({
            onClick: () => navigate(`/developers/${r.developer_id}`),
            style: { cursor: "pointer" },
          })}
        />
      </Card>
    </div>
  );
}
