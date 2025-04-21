export const s2point = (size) => {
  if (size === "소") return 1;
  if (size === "중") return 2;
  if (size === "대") return 3;
  if (size === "특대") return 4;
  return 0;
};