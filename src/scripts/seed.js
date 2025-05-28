import { PrismaClient } from '@prisma/client'
import bcrypt from 'bcrypt'

const prisma = new PrismaClient()

async function main() {
  // 기존 데이터 삭제
  await prisma.parcel.deleteMany()
  await prisma.documentUpload.deleteMany()
  await prisma.storeInfo.deleteMany()
  await prisma.driverInfo.deleteMany()
  await prisma.pointTransaction.deleteMany()
  await prisma.user.deleteMany()
  await prisma.subscriptionPlan.deleteMany()

  // 구독제 생성
  await prisma.subscriptionPlan.createMany({
    data: [
      { id: 1, name: 'Lite', price: 300000, grantedPoint: 300 },
      { id: 2, name: 'Lite Plus', price: 400000, grantedPoint: 400 },
      { id: 3, name: 'Standard', price: 500000, grantedPoint: 500 },
      { id: 4, name: 'Standard Plus', price: 700000, grantedPoint: 720 },
      { id: 5, name: 'Premium', price: 950000, grantedPoint: 1000 },
      { id: 6, name: 'Premium Plus', price: 1200000, grantedPoint: 1260 }
    ],
    skipDuplicates: true
  })

  // 배송기사 5명 생성 (CSV 기반, ID 고정)
  const driverSeeds = [
    {
      id: 1,
      email: 'driver1@example.com',
      password: '1234',
      name: '기사1',
      phoneNumber: '010-0000-0001',
      vehicleNumber: '서울 12가 341',
      regionCity: '서울시',
      regionDistrict: '은평구, 서대문구, 마포구'
    },
    {
      id: 2,
      email: 'driver2@example.com',
      password: '1234',
      name: '기사2',
      phoneNumber: '010-0000-0002',
      vehicleNumber: '서울 12가 344',
      regionCity: '서울시',
      regionDistrict: '도봉구, 노원구, 강북구, 성북구'
    },
    {
      id: 3,
      email: 'driver3@example.com',
      password: '1234',
      name: '기사3',
      phoneNumber: '010-0000-0003',
      vehicleNumber: '서울 12가 343',
      regionCity: '서울시',
      regionDistrict: '종로구, 중구, 용산구'
    },
    {
      id: 4,
      email: 'driver4@example.com',
      password: '1234',
      name: '기사4',
      phoneNumber: '010-0000-0004',
      vehicleNumber: '서울 12가 342',
      regionCity: '서울시',
      regionDistrict: '강서구, 양천구, 구로구, 영등포구, 동작구, 관악구, 금천구'
    },
    {
      id: 5,
      email: 'driver5@example.com',
      password: '1234',
      name: '기사5',
      phoneNumber: '010-0000-0005',
      vehicleNumber: '서울 12가 3456',
      regionCity: '서울특별시',
      regionDistrict: '성동구, 광진구, 동대문구, 중랑구, 강동구, 송파구, 강남구, 서초구'
    }
  ]

  for (const driver of driverSeeds) {
    const hashedPassword = await bcrypt.hash(driver.password, 10)
    await prisma.user.create({
      data: {
        id: driver.id,
        email: driver.email,
        password: hashedPassword,
        name: driver.name,
        userType: 'DRIVER',
        isApproved: true,
        driverInfo: {
          create: {
            phoneNumber: driver.phoneNumber,
            vehicleNumber: driver.vehicleNumber,
            regionCity: driver.regionCity,
            regionDistrict: driver.regionDistrict
          }
        }
      }
    })
  }

  // 소상공인 5명 생성
  const ownerPassword = await bcrypt.hash('1234', 10)

  const ownerSeeds = [
    {
      email: 'owner1@example.com',
      name: '김사장1',
      address: '서울시 은평구'
    },
    {
      email: 'owner2@example.com',
      name: '김사장2',
      address: '서울시 노원구'
    },
    {
      email: 'owner3@example.com',
      name: '김사장3',
      address: '서울시 종로구'
    },
    {
      email: 'owner4@example.com',
      name: '김사장4',
      address: '서울시 구로구'
    },
    {
      email: 'owner5@example.com',
      name: '김사장5',
      address: '서울시 강남구'
    }
  ]

  for (const [i, owner] of ownerSeeds.entries()) {
    await prisma.user.create({
      data: {
        email: owner.email,
        password: ownerPassword,
        name: owner.name,
        userType: 'OWNER',
        isApproved: true,
        subscriptionPlan: {
          connect: { id: 1 }
        },
        storeInfo: {
          create: {
            address: owner.address,
            detailAddress: `${i + 1}층 10${i}호`,
            expectedSize: '중형',
            monthlyCount: 50,
            pickupPreference: '월,수'
          }
        },
        points: {
          create: {
            amount: 10000,
            reason: '초기 지급',
            type: 'CHARGE'
          }
        }
      }
    })
  }

  console.log('기사 5명(ID 고정) + 소상공인 5명 생성 완료!')
}

main()
  .catch((e) => {
    console.error('에러 발생:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
