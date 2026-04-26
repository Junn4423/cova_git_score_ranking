-- Phase 7 upgrade: make score snapshots repository-aware.
-- Run this once against an existing Laragon/MySQL database.

USE eng_analytics;

SET @has_repo_id := (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'score_snapshots'
    AND COLUMN_NAME = 'repo_id'
);
SET @sql := IF(
  @has_repo_id = 0,
  'ALTER TABLE score_snapshots ADD COLUMN repo_id INT NULL AFTER developer_id',
  'SELECT ''score_snapshots.repo_id already exists'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_idx := (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'score_snapshots'
    AND INDEX_NAME = 'idx_score_repo_period'
);
SET @sql := IF(
  @has_idx = 0,
  'ALTER TABLE score_snapshots ADD INDEX idx_score_repo_period (repo_id, period_start, period_end)',
  'SELECT ''idx_score_repo_period already exists'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_idx := (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'score_snapshots'
    AND INDEX_NAME = 'idx_score_repo_dev_period'
);
SET @sql := IF(
  @has_idx = 0,
  'ALTER TABLE score_snapshots ADD INDEX idx_score_repo_dev_period (repo_id, developer_id, period_start, period_end)',
  'SELECT ''idx_score_repo_dev_period already exists'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_fk := (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'score_snapshots'
    AND CONSTRAINT_NAME = 'fk_score_snapshots_repo'
);
SET @sql := IF(
  @has_fk = 0,
  'ALTER TABLE score_snapshots ADD CONSTRAINT fk_score_snapshots_repo FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE',
  'SELECT ''fk_score_snapshots_repo already exists'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
