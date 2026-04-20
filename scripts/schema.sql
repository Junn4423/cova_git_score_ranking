-- ============================================================
-- Engineering Contribution Analytics - MySQL Schema V1
-- ============================================================

CREATE DATABASE IF NOT EXISTS eng_analytics
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE eng_analytics;

-- -----------------------------------------------------------
-- 1. developers
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS developers (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  github_login    VARCHAR(100) NOT NULL,
  display_name    VARCHAR(200),
  email           VARCHAR(255),
  avatar_url      VARCHAR(500),
  is_bot          TINYINT(1) NOT NULL DEFAULT 0,
  is_active       TINYINT(1) NOT NULL DEFAULT 1,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_dev_login (github_login)
) ENGINE=InnoDB;

-- alias mapping: many emails/logins → one developer
CREATE TABLE IF NOT EXISTS developer_aliases (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  developer_id    INT NOT NULL,
  alias_type      ENUM('email','github_login','name') NOT NULL,
  alias_value     VARCHAR(255) NOT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_alias (alias_type, alias_value),
  FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 2. teams
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS teams (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  name            VARCHAR(200) NOT NULL,
  description     TEXT,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_team_name (name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS team_members (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  team_id         INT NOT NULL,
  developer_id    INT NOT NULL,
  role            VARCHAR(50) DEFAULT 'member',
  joined_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_team_dev (team_id, developer_id),
  FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
  FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 3. repositories
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS repositories (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  github_id       BIGINT NOT NULL,
  full_name       VARCHAR(300) NOT NULL,
  name            VARCHAR(200) NOT NULL,
  description     TEXT,
  default_branch  VARCHAR(100) DEFAULT 'main',
  is_tracked      TINYINT(1) NOT NULL DEFAULT 1,
  exclude_from_ranking TINYINT(1) NOT NULL DEFAULT 0,
  last_synced_at  DATETIME,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_repo_github_id (github_id),
  UNIQUE KEY uq_repo_fullname (full_name)
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 4. commits
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS commits (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  repo_id         INT NOT NULL,
  sha             VARCHAR(40) NOT NULL,
  author_id       INT,
  committer_id    INT,
  message         TEXT,
  committed_at    DATETIME,
  additions       INT DEFAULT 0,
  deletions       INT DEFAULT 0,
  total_changes   INT DEFAULT 0,
  parent_count    INT DEFAULT 0,
  branch          VARCHAR(200),
  is_merge        TINYINT(1) DEFAULT 0,
  raw_author_email VARCHAR(255),
  raw_author_name  VARCHAR(255),
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_repo_sha (repo_id, sha),
  INDEX idx_commit_author (author_id),
  INDEX idx_commit_repo_time (repo_id, committed_at),
  INDEX idx_commit_time (committed_at),
  FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE,
  FOREIGN KEY (author_id) REFERENCES developers(id) ON DELETE SET NULL,
  FOREIGN KEY (committer_id) REFERENCES developers(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 5. commit_files
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS commit_files (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  commit_id       INT NOT NULL,
  filename        VARCHAR(500) NOT NULL,
  status          VARCHAR(20),
  additions       INT DEFAULT 0,
  deletions       INT DEFAULT 0,
  changes         INT DEFAULT 0,
  patch           MEDIUMTEXT,
  is_generated    TINYINT(1) DEFAULT 0,
  is_lockfile     TINYINT(1) DEFAULT 0,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_cfile_commit (commit_id),
  FOREIGN KEY (commit_id) REFERENCES commits(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 6. pull_requests
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS pull_requests (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  repo_id         INT NOT NULL,
  github_pr_number INT NOT NULL,
  title           VARCHAR(500),
  body            MEDIUMTEXT,
  state           VARCHAR(20),
  author_id       INT,
  merged          TINYINT(1) DEFAULT 0,
  merged_at       DATETIME,
  closed_at       DATETIME,
  head_branch     VARCHAR(200),
  base_branch     VARCHAR(200),
  additions       INT DEFAULT 0,
  deletions       INT DEFAULT 0,
  changed_files   INT DEFAULT 0,
  review_comments INT DEFAULT 0,
  github_created_at DATETIME,
  github_updated_at DATETIME,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_pr_repo_number (repo_id, github_pr_number),
  INDEX idx_pr_author (author_id),
  INDEX idx_pr_repo_state (repo_id, state),
  FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE,
  FOREIGN KEY (author_id) REFERENCES developers(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 7. pull_request_commits
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS pull_request_commits (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  pull_request_id INT NOT NULL,
  commit_id       INT NOT NULL,
  UNIQUE KEY uq_pr_commit (pull_request_id, commit_id),
  FOREIGN KEY (pull_request_id) REFERENCES pull_requests(id) ON DELETE CASCADE,
  FOREIGN KEY (commit_id) REFERENCES commits(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 8. reviews
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS reviews (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  pull_request_id INT NOT NULL,
  reviewer_id     INT,
  github_review_id BIGINT,
  state           VARCHAR(30),
  body            TEXT,
  submitted_at    DATETIME,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_review_pr (pull_request_id),
  INDEX idx_review_reviewer (reviewer_id),
  FOREIGN KEY (pull_request_id) REFERENCES pull_requests(id) ON DELETE CASCADE,
  FOREIGN KEY (reviewer_id) REFERENCES developers(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 9. work_items
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS work_items (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  developer_id    INT NOT NULL,
  repo_id         INT,
  pull_request_id INT,
  title           VARCHAR(500),
  grouping_method VARCHAR(50),
  start_time      DATETIME,
  end_time        DATETIME,
  commit_count    INT DEFAULT 0,
  total_additions INT DEFAULT 0,
  total_deletions INT DEFAULT 0,
  file_count      INT DEFAULT 0,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_wi_dev (developer_id),
  INDEX idx_wi_repo (repo_id),
  INDEX idx_wi_time (start_time, end_time),
  FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE,
  FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE SET NULL,
  FOREIGN KEY (pull_request_id) REFERENCES pull_requests(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 10. work_item_commits
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS work_item_commits (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  work_item_id    INT NOT NULL,
  commit_id       INT NOT NULL,
  UNIQUE KEY uq_wi_commit (work_item_id, commit_id),
  FOREIGN KEY (work_item_id) REFERENCES work_items(id) ON DELETE CASCADE,
  FOREIGN KEY (commit_id) REFERENCES commits(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 11. ai_commit_analysis
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_commit_analysis (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  target_type     ENUM('commit','pull_request','work_item') NOT NULL,
  target_id       INT NOT NULL,
  change_type     VARCHAR(50),
  summary         TEXT,
  complexity_score INT,
  risk_score      INT,
  message_alignment_score INT,
  test_presence   TINYINT(1),
  confidence      DECIMAL(3,2),
  notes           JSON,
  model_version   VARCHAR(100),
  prompt_version  VARCHAR(50),
  schema_version  VARCHAR(20),
  raw_response    JSON,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ai_target (target_type, target_id),
  INDEX idx_ai_change_type (change_type)
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 12. score_snapshots
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS score_snapshots (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  developer_id    INT NOT NULL,
  period_start    DATE NOT NULL,
  period_end      DATE NOT NULL,
  activity_score  DECIMAL(6,2),
  quality_score   DECIMAL(6,2),
  impact_score    DECIMAL(6,2),
  final_score     DECIMAL(6,2),
  confidence_score DECIMAL(3,2),
  top_positive_reasons JSON,
  top_negative_reasons JSON,
  evidence_links  JSON,
  calculated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_score_dev (developer_id),
  INDEX idx_score_period (period_start, period_end),
  FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 13. score_breakdowns
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS score_breakdowns (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  snapshot_id     INT NOT NULL,
  component       VARCHAR(100) NOT NULL,
  raw_value       DECIMAL(10,4),
  weight          DECIMAL(5,4),
  weighted_value  DECIMAL(10,4),
  details         JSON,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_breakdown_snapshot (snapshot_id),
  FOREIGN KEY (snapshot_id) REFERENCES score_snapshots(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 14. app_configs
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_configs (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  config_key      VARCHAR(200) NOT NULL,
  config_value    JSON NOT NULL,
  description     TEXT,
  updated_by      INT,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_config_key (config_key)
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 15. job_queue
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_queue (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  job_type        VARCHAR(100) NOT NULL,
  payload         JSON,
  status          ENUM('pending','running','done','failed','retry') NOT NULL DEFAULT 'pending',
  priority        INT DEFAULT 0,
  attempts        INT DEFAULT 0,
  max_attempts    INT DEFAULT 3,
  error_message   TEXT,
  scheduled_at    DATETIME,
  started_at      DATETIME,
  completed_at    DATETIME,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_job_status (status),
  INDEX idx_job_type_status (job_type, status),
  INDEX idx_job_scheduled (scheduled_at)
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 16. audit_logs
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  actor_id        INT,
  action          VARCHAR(100) NOT NULL,
  target_type     VARCHAR(100),
  target_id       INT,
  details         JSON,
  ip_address      VARCHAR(45),
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_actor (actor_id),
  INDEX idx_audit_action (action),
  INDEX idx_audit_time (created_at)
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- 17. users (auth nội bộ)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  username        VARCHAR(100) NOT NULL,
  password_hash   VARCHAR(255) NOT NULL,
  role            ENUM('admin','lead','developer') NOT NULL DEFAULT 'developer',
  developer_id    INT,
  is_active       TINYINT(1) NOT NULL DEFAULT 1,
  last_login      DATETIME,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_username (username),
  FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------------
-- Insert default configs
-- -----------------------------------------------------------
INSERT INTO app_configs (config_key, config_value, description) VALUES
('scoring_weights', '{"activity": 0.15, "quality": 0.50, "impact": 0.35}', 'Trọng số 3 lớp điểm: Activity 15%, Quality 50%, Impact 35%'),
('sync_interval_minutes', '15', 'Chu kỳ đồng bộ GitHub (phút)'),
('work_item_time_window_hours', '8', 'Cửa sổ thời gian gom commit thành work item (giờ)'),
('excluded_file_patterns', '["*.lock", "*.min.js", "*.min.css", "package-lock.json", "yarn.lock", "composer.lock"]', 'Các pattern file được loại trừ khỏi scoring'),
('max_diff_size_for_ai', '50000', 'Số ký tự diff tối đa gửi cho AI phân tích'),
('bot_accounts', '["dependabot[bot]", "renovate[bot]", "github-actions[bot]"]', 'Danh sách bot accounts loại khỏi ranking')
ON DUPLICATE KEY UPDATE config_key = config_key;
