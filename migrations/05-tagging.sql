CREATE TABLE `tag` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `auto_complete` bool NOT NULL,
    `hidden` bool NOT NULL
)
;
CREATE INDEX `tag_3fc10b3b` ON `tag` (`auto_complete`);
CREATE INDEX `tag_c91f1bf` ON `tag` (`hidden`)

CREATE TABLE `profile_tags` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `userprofile_id` integer NOT NULL,
    `tag_id` integer NOT NULL,
    UNIQUE (`userprofile_id`, `tag_id`)
)
;
ALTER TABLE `profile_tags` ADD CONSTRAINT `tag_id_refs_id_1cbb0b43` FOREIGN KEY (`tag_id`) REFERENCES `tag` (`id`);
ALTER TABLE `profile_tags` ADD CONSTRAINT `userprofile_id_refs_id_4a989baa` FOREIGN KEY (`userprofile_id`) REFERENCES `profile` (`id`);
