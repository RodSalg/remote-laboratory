CREATE DATABASE IF NOT EXISTS `cae_dr`;
USE `cae_dr`;

DROP TABLE IF EXISTS `dadoscoletados_summary`;
CREATE TABLE `dadoscoletados_summary` (
  `id` int NOT NULL AUTO_INCREMENT unique key,
  `experiment_id` int NOT NULL,
  `pattern` varchar(9999) NOT NULL,
  `time_stamp` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
);
