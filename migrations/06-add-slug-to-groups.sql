ALTER TABLE `group` ADD COLUMN `url` varchar(50) NOT NULL;

CREATE INDEX `group_a4b49ab` ON `group` (`url`);
