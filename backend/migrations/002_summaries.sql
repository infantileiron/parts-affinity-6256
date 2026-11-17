-- 002 分站汇总参与联用挖掘
-- 分站目录
CREATE TABLE IF NOT EXISTS `stations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(40) NOT NULL,
  `name` varchar(100) NOT NULL,
  `created` varchar(40) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
-- 本地补录作业的分站与周期（明细口径，历史数据允许为空）
ALTER TABLE `jobs` ADD COLUMN `station_code` varchar(40) DEFAULT NULL AFTER `note`;
ALTER TABLE `jobs` ADD COLUMN `cycle` varchar(20) DEFAULT NULL AFTER `station_code`;
CREATE INDEX `ix_jobs_scope` ON `jobs` (`station_code`,`cycle`);
-- 分站汇总：待核对/生效/作废；active_scope 仅生效行写入，唯一索引保证每范围一份生效
CREATE TABLE IF NOT EXISTS `summary_reports` (
  `id` int NOT NULL AUTO_INCREMENT,
  `station_code` varchar(40) NOT NULL,
  `cycle` varchar(20) NOT NULL,
  `equipment` varchar(40) NOT NULL,
  `state` varchar(20) NOT NULL DEFAULT 'pending',
  `version` int NOT NULL DEFAULT 1,
  `valid_jobs` int NOT NULL,
  `combo_counts` json NOT NULL,
  `checksum` varchar(64) NOT NULL,
  `supersedes_id` int DEFAULT NULL,
  `note` text,
  `created` varchar(40) DEFAULT NULL,
  `activated` varchar(40) DEFAULT NULL,
  `active_scope` varchar(120) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_summary_version` (`station_code`,`cycle`,`equipment`,`version`),
  UNIQUE KEY `uq_summary_active_scope` (`active_scope`),
  KEY `ix_summary_scope` (`station_code`,`cycle`,`equipment`,`state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
-- 挖掘批次冻结完整来源版本
ALTER TABLE `mining_runs` ADD COLUMN `source_manifest` json DEFAULT NULL AFTER `error`;
ALTER TABLE `mining_runs` ADD COLUMN `snapshot` json DEFAULT NULL AFTER `source_manifest`;
