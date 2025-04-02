import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  // 1. 구독제 생성
  const subscriptionPlans = await prisma.subscriptionPlan.createMany({
    data: [
      { name: '베이직', price: 10000 },
      { name: '스탠다드', price: 20000 },
      { name: '프리미엄', price: 30000 },
      { name: '엔터프라이즈', price: 50000 }
    ]
  });

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
  );

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
            connect: { name: '베이직' }
          },
          storeInfo: {
            create: {
              address: '서울시 마포구',
              expectedSize: '중형',
              monthlyCount: 50 + i * 10,
              pickupPreference: ['월', '수']
            }
          },
          points: {
            create: {
              amount: 10000,
              reason: '초기 지급'
            }
          }
        }
      })
    )
  );

  // 4. 주문 2개 생성 (owner[0]과 driver[0] 연결)
  const [order1, order2] = await Promise.all([
    prisma.order.create({
      data: {
        userId: owners[0].id,
        driverId: drivers[0].id,
        pickupDays: ['월', '수']
      }
    }),
    prisma.order.create({
      data: {
        userId: owners[0].id,
        driverId: drivers[0].id,
        pickupDays: ['화', '목']
      }
    })
  ]);

  // 5. 소포 7개 생성 (2개의 주문에 분배)
  const statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED'];
  await Promise.all(
    Array.from({ length: 7 }).map((_, i) =>
      prisma.parcel.create({
        data: {
          orderId: i < 4 ? order1.id : order2.id,
          ownerId: owners[0].id,
          driverId: drivers[0].id,
          trackingCode: `TRK00${i + 1}`,
          recipientName: `수령인${i + 1}`,
          recipientAddr: `서울시 ${['강남구', '중구', '종로구', '마포구'][i % 4]}`,
          status: statuses[i % statuses.length],
          deliveryImageUrl: i % 3 === 0 ? 'https://s3.example.com/proof.png' : ''
        }
      })
    )
  );

  console.log('✅ 시드 데이터 생성 완료!');
}

main()
  .then(() => prisma.$disconnect())
  .catch((e) => {
    console.error('❌ 에러 발생:', e);
    prisma.$disconnect();
    process.exit(1);
  });
