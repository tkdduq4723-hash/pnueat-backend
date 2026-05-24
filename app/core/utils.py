import math
import re


def calc_walk_time(distance_m) -> str:
    """직선거리 × 1.3 ÷ 67m/분"""
    if not distance_m or distance_m == "-":
        return "-"
    real_distance = int(distance_m) * 1.3
    minutes = real_distance / 67
    if minutes < 1:
        return "1분 이내"
    return f"약 {math.ceil(minutes)}분"


def get_main_category(category: str) -> str:
    c = category.replace(" ", "")
    if "치킨" in c:
        return "치킨"
    if "패스트푸드" in c or "햄버거" in c:
        return "패스트푸드"
    if "돈가스" in c or "회" in c or "초밥" in c or "일식" in c:
        return "돈까스·회"
    if "베트남" in c or "아시아" in c or "인도" in c or "태국" in c:
        return "아시안"
    if "족발" in c or "보쌈" in c:
        return "족발·보쌈"
    if "피자" in c:
        return "피자"
    if "찜" in c or "탕" in c or "순대" in c or "국밥" in c:
        return "찜·탕"
    if "중식" in c or "중국" in c:
        return "중식"
    if "분식" in c:
        return "분식"
    if "한식" in c:
        return "한식"
    if "고기" in c or "구이" in c or "삼겹" in c:
        return "고기"
    if "양식" in c or "스테이크" in c or "파스타" in c:
        return "양식"
    return "기타"


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)
