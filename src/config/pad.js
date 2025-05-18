//date 문자열 오류 제거용 (월, 일)
export const pad = (n) => {
    return n.toString().padStart(2, '0');
}