CREATE TABLE `profile` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_id` integer NOT NULL UNIQUE,
    `confirmation_code` varchar(32) NOT NULL UNIQUE,
    `is_confirmed` bool NOT NULL
)
ENGINE=InnoDB CHARSET=utf8;
;
ALTER TABLE `profile` ADD CONSTRAINT `user_id_refs_id_29ac45dc` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
