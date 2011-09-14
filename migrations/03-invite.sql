DROP TABLE IF EXISTS invite; -- things we can do before we launch.

CREATE TABLE `invite` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `inviter` varchar(32) NOT NULL,
    `recipient` varchar(75) NOT NULL,
    `redeemer` varchar(32) NOT NULL,
    `code` varchar(32) NOT NULL UNIQUE,
    `redeemed` datetime,
    `created` datetime NOT NULL
) ENGINE=InnoDB CHARSET=utf8;
