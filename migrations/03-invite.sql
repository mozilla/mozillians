CREATE TABLE `invite` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `inviter` varchar(32) NOT NULL,
    `destination` varchar(75) NOT NULL,
    `code` varchar(32) NOT NULL UNIQUE,
    `redeemed` datetime,
    `created` datetime NOT NULL
) ENGINE=InnoDB CHARSET=utf8;
