/*
  Warnings:

  - You are about to drop the column `pickupDate` on the `Parcel` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE `Parcel` DROP COLUMN `pickupDate`,
    ADD COLUMN `deliveryScheduledDate` DATETIME(3) NULL,
    ADD COLUMN `pickupScheduledDate` DATETIME(3) NULL;
