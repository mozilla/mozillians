CREATE TABLE `group` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `auto_complete` bool NOT NULL,
    `system` bool NOT NULL
) ENGINE=InnoDB CHARSET=utf8;

CREATE INDEX `group_3fc10b3b` ON `group` (`auto_complete`);
CREATE INDEX `group_43de5bc6` ON `group` (`system`);

CREATE TABLE `profile_groups` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `userprofile_id` integer NOT NULL,
    `group_id` integer NOT NULL,
    UNIQUE (`userprofile_id`, `group_id`)
) ENGINE=InnoDB CHARSET=utf8;

ALTER TABLE `profile_groups` ADD CONSTRAINT `group_id_refs_id_1cbb0b43` FOREIGN KEY (`group_id`) REFERENCES `group` (`id`);
ALTER TABLE `profile_groups` ADD CONSTRAINT `userprofile_id_refs_id_4a989baa` FOREIGN KEY (`userprofile_id`) REFERENCES `profile` (`id`);
