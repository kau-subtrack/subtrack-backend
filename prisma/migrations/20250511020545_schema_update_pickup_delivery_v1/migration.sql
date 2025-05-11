/*
  Warnings:

  - You are about to drop the column `completedAt` on the `Parcel` table. All the data in the column will be lost.
  - You are about to drop the column `driverId` on the `Parcel` table. All the data in the column will be lost.
  - You are about to alter the column `size` on the `Parcel` table. The data in that column could be lost. The data in that column will be cast from `VarChar(191)` to `Enum(EnumId(3))`.
  - You are about to alter the column `status` on the `Parcel` table. The data in that column could be lost. The data in that column will be cast from `Enum(EnumId(3))` to `Enum(EnumId(4))`.

*/
-- DropForeignKey
ALTER TABLE `Parcel` DROP FOREIGN KEY `Parcel_driverId_fkey`;

-- DropIndex
DROP INDEX `Parcel_driverId_fkey` ON `Parcel`;

-- AlterTable
ALTER TABLE `Parcel` DROP COLUMN `completedAt`,
    DROP COLUMN `driverId`,
    ADD COLUMN `deliveryCompletedAt` DATETIME(3) NULL,
    ADD COLUMN `deliveryDriverId` INTEGER NULL,
    ADD COLUMN `deliveryTimeWindow` VARCHAR(191) NULL,
    ADD COLUMN `pickupCompletedAt` DATETIME(3) NULL,
    ADD COLUMN `pickupDriverId` INTEGER NULL,
    ADD COLUMN `pickupTimeWindow` VARCHAR(191) NULL,
    MODIFY `size` ENUM('SMALL', 'MEDIUM', 'LARGE', 'XLARGE') NOT NULL,
    MODIFY `status` ENUM('PENDING_PICKUP', 'IN_PICKUP', 'PICKUP_COMPLETED', 'PENDING_DELIVERY', 'IN_DELIVERY', 'DELIVERY_COMPLETED') NOT NULL DEFAULT 'PENDING_PICKUP';

-- AlterTable
ALTER TABLE `User` ADD COLUMN `avgParcelPerMonth` INTEGER NULL,
    ADD COLUMN `expiredAt` DATETIME(3) NULL,
    ADD COLUMN `subscribedAt` DATETIME(3) NULL;

-- CreateTable
CREATE TABLE `ChatbotLog` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `userId` INTEGER NOT NULL,
    `endpoint` VARCHAR(191) NOT NULL,
    `createdAt` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `Parcel` ADD CONSTRAINT `Parcel_pickupDriverId_fkey` FOREIGN KEY (`pickupDriverId`) REFERENCES `User`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Parcel` ADD CONSTRAINT `Parcel_deliveryDriverId_fkey` FOREIGN KEY (`deliveryDriverId`) REFERENCES `User`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `ChatbotLog` ADD CONSTRAINT `ChatbotLog_userId_fkey` FOREIGN KEY (`userId`) REFERENCES `User`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE;
