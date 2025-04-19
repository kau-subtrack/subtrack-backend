import dotenv from 'dotenv';
dotenv.config();
import jwt from 'jsonwebtoken';
import { pool } from '../config/db.js';

export const jwtMiddleware = async (req, res, next) => {
    const authHeader = req.headers['authorization']; // Authorization 헤더 추출
    try {
        if (!authHeader) return res.status(401).json({ message: '토큰이 존재하지 않습니다.' });

        const token = authHeader && authHeader.split(' ')[1]; // 'Bearer xxx'에서 토큰만 추출

        //if (tokenType !== 'Bearer') return res.status(401).json({ message: '토큰 타입이 일치하지 않습니다.'});

        const decodedToken = jwt.verify(token, process.env.JWT_SECRET);

        /*
        const user = await pool.users.findFirst({
            where: { userId: +userId },
        });
        if (!user) {
            res.clearCookie('authorization');
            throw new Error('토큰 사용자가 존재하지 않습니다.');
        }
        */
        // req.userid에 사용자 정보를 저장합니다.
        req.userId = decodedToken.userId;
        next();
    } catch (error) {
        res.clearCookie('authorization');

        // 토큰이 만료되었거나, 조작되었을 때, 에러 메시지를 다르게 출력합니다.
        switch (error.name) {
            case 'TokenExpiredError':
                return res.status(401).json({ message: '토큰이 만료되었습니다.' });
            case 'JsonWebTokenError':
                return res.status(401).json({ message: '토큰이 조작되었습니다.' });
            default:
                return res
                    .status(401)
                    .json({ message: error.message ?? '비정상적인 요청입니다.' });
        }
    }
}