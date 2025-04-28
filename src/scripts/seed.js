import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  await prisma.parcel.deleteMany();
  await prisma.documentUpload.deleteMany();
  await prisma.storeInfo.deleteMany();
  await prisma.driverInfo.deleteMany();
  await prisma.pointTransaction.deleteMany();
  await prisma.user.deleteMany();
  await prisma.subscriptionPlan.deleteMany();

  // 1. 구독제 생성
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

  // 2. 배송기사 4명 생성
  const drivers = await Promise.all(
    Array.from({ length: 4 }).map((_, i) =>
      prisma.user.create({
        data: {
          email: `driver${i + 1}@example.com`,
          password: 'hashed_pw',
          name: `이기사${i + 1}`,
          userType: 'DRIVER',
          isApproved: true,
          driverInfo: {
            create: {
              phoneNumber: `010-0000-00${i + 1}`,
              vehicleNumber: `서울 12가 34${i + 1}`,
              regionCity: '서울시',
              regionDistrict: ['강남구', '성동구', '관악구', '서초구'][i]
            }
          },
          documents: {
            create: [
              {
                type: 'LICENSE',
                fileUrl: `https://example.com/license_driver${i + 1}.png`
              },
              {
                type: 'CAREER',
                fileUrl: `https://example.com/career_driver${i + 1}.png`
              }
            ]
          }
        }
      })
    )
  )

  // 3. 소상공인 4명 생성
  const owners = await Promise.all(
    Array.from({ length: 4 }).map((_, i) =>
      prisma.user.create({
        data: {
          email: `owner${i + 1}@example.com`,
          password: 'hashed_pw',
          name: `김사장${i + 1}`,
          userType: 'OWNER',
          isApproved: true,
          subscriptionPlan: {
            connect: { id: 1 }
          },
          storeInfo: {
            create: {
              address: '서울시 마포구',
              detailAddress: `${i + 1}층 10${i}호`,
              expectedSize: '중형',
              monthlyCount: 50 + i * 10,
              pickupPreference: '월,수'
            }
          },
          points: {
            create: {
              amount: 10000,
              reason: '초기 지급',
              type: 'CHARGE' // 또는 'USE'
            }
          }
        }
      })
    )
  )

  // 4. 소포 7개 생성 (Parcel 단독 등록)
  const statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED']
  await Promise.all(
    Array.from({ length: 7 }).map((_, i) =>
      prisma.parcel.create({
        data: {
          ownerId: owners[0].id,
          driverId: drivers[0].id,
          productName: `운동화${i + 1}`,
          size: ['소', '중', '대', '특대'][i % 4],
          caution: i % 2 === 0,
          recipientName: `수령인${i + 1}`,
          recipientPhone: `010-1234-56${i + 1}`,
          recipientAddr: `서울시 ${['강남구', '중구', '종로구', '마포구'][i % 4]}`,
          detailAddress: `${i + 1}층`,
          trackingCode: `TRK00${i + 1}`,
          status: statuses[i % statuses.length],
          pickupDate: new Date(`2025-04-${10 + i}`),
          deliveryImageUrl: i % 3 === 0 ? 'https://s3.example.com/proof.png' : ''
        }
      })
    )
  )

  console.log('✅ 시드 데이터 생성 완료!')
}

main()
  .then(() => prisma.$disconnect())
  .catch((e) => {
    console.error('❌ 에러 발생:', e)
    prisma.$disconnect()
    process.exit(1)
  })
