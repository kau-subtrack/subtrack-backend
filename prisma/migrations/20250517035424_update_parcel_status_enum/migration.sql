/*
  Warnings:

  - You are about to alter the column `status` on the `Parcel` table. The data in that column could be lost. The data in that column will be cast from `Enum(EnumId(4))` to `Enum(EnumId(4))`.

*/
-- AlterTable
ALTER TABLE `Parcel` MODIFY `status` ENUM('PICKUP_PENDING', 'PICKUP_COMPLETED', 'DELIVERY_PENDING', 'DELIVERY_COMPLETED') NOT NULL DEFAULT 'PICKUP_PENDING';
