-- upgrade --
ALTER TABLE `pixel` RENAME COLUMN `last_modify` TO `modify_time`;
ALTER TABLE `pixel` ALTER COLUMN `color` SET DEFAULT 'ffffff';
ALTER TABLE `pixel` ADD INDEX `idx_pixel_y_2cdd67` (`y`);
ALTER TABLE `pixel` ADD INDEX `idx_pixel_x_041a10` (`x`);
-- downgrade --
ALTER TABLE `pixel` DROP INDEX `idx_pixel_x_041a10`;
ALTER TABLE `pixel` DROP INDEX `idx_pixel_y_2cdd67`;
ALTER TABLE `pixel` RENAME COLUMN `modify_time` TO `last_modify`;
ALTER TABLE `pixel` ALTER COLUMN `color` DROP DEFAULT;
