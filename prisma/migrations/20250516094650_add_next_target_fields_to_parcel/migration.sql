-- AlterTable
ALTER TABLE `Parcel` ADD COLUMN `isNextDeliveryTarget` BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN `isNextPickupTarget` BOOLEAN NOT NULL DEFAULT false;
