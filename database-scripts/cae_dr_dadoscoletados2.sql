CREATE DATABASE IF NOT EXISTS `cae_dr`; 
USE `cae_dr`;

DROP TABLE IF EXISTS `dadoscoletados2`;
CREATE TABLE `dadoscoletados2` (
  `id` int NOT NULL AUTO_INCREMENT,
  `experiment_id` int DEFAULT NULL,
  `step` int DEFAULT NULL,
  `pulse_train` varchar(9999) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pulse_value` int DEFAULT NULL,
  `time_stamp` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`)
);
