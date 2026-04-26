-- Phase 8 upgrade: evaluation runs and persisted evaluation results.
-- Run after the Phase 7 repo scoring upgrade.

USE eng_analytics;

CREATE TABLE IF NOT EXISTS evaluation_runs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  repo_id INT NOT NULL,
  requested_by_user_id INT NULL,
  status ENUM('pending','running','done','failed','cancelled') NOT NULL DEFAULT 'pending',
  current_step VARCHAR(100) NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  input_repo_url VARCHAR(500) NULL,
  access_mode ENUM('public','server_token','github_app','oauth') NULL,
  sync_started_at DATETIME NULL,
  sync_completed_at DATETIME NULL,
  grouping_completed_at DATETIME NULL,
  analysis_completed_at DATETIME NULL,
  scoring_completed_at DATETIME NULL,
  report_completed_at DATETIME NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_eval_repo_period (repo_id, period_start, period_end),
  INDEX idx_eval_status (status),
  CONSTRAINT fk_eval_run_repo FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE,
  CONSTRAINT fk_eval_run_user FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS evaluation_results (
  id INT AUTO_INCREMENT PRIMARY KEY,
  evaluation_run_id INT NOT NULL,
  developer_id INT NOT NULL,
  repo_id INT NOT NULL,
  rank_no INT NOT NULL,
  final_score DECIMAL(6,2) NOT NULL,
  activity_score DECIMAL(6,2) NULL,
  quality_score DECIMAL(6,2) NULL,
  impact_score DECIMAL(6,2) NULL,
  confidence_score DECIMAL(3,2) NULL,
  summary_vi TEXT NULL,
  strengths JSON NULL,
  weaknesses JSON NULL,
  recommendations JSON NULL,
  evidence JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_eval_dev (evaluation_run_id, developer_id),
  INDEX idx_eval_result_repo_rank (repo_id, rank_no),
  CONSTRAINT fk_eval_result_run FOREIGN KEY (evaluation_run_id) REFERENCES evaluation_runs(id) ON DELETE CASCADE,
  CONSTRAINT fk_eval_result_dev FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE,
  CONSTRAINT fk_eval_result_repo FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
) ENGINE=InnoDB;
