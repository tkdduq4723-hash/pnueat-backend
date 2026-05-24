import httpx
from app.core.config import KAKAO_API_KEY, PNU_LAT, PNU_LNG
from app.core.utils import calc_walk_time

URL = "https://dapi.kakao.com/v2/local/search/category.json"

FOOD_EXCLUDE = ["샐러드", "간식", "베이커리", "제과", "도시락", "술집", "호프", "야식"]
CAFE_EXCLUDE = ["키즈", "보드", "스파게티", "파스타", "여가", "실내놀이", "방탈출", "노래", "당구", "스크린"]


async def _search(category_code: str, exclude: list[str], radius: int = 1000) -> list[dict]:
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    seen = set()
    results = []

    async with httpx.AsyncClient() as client:
        for page in range(1, 8):
            params = {
                "category_group_code": category_code,
                "x": PNU_LNG,
                "y": PNU_LAT,
                "radius": radius,
                "sort": "distance",
                "size": 15,
                "page": page,
            }
            res = await client.get(URL, headers=headers, params=params)
            data = res.json()

            for doc in data.get("documents", []):
                name = doc["place_name"]
                cat = doc.get("category_name", "")
                if name in seen:
                    continue
                if any(ex in cat for ex in exclude):
                    continue
                seen.add(name)
                dist = doc.get("distance", "-")
                results.append({
                    "이름": name,
                    "주소": doc.get("road_address_name", doc.get("address_name", "")),
                    "카테고리": cat.split(">")[1].strip() if ">" in cat else cat,
                    "거리(m)": dist,
                    "도보시간": calc_walk_time(dist),
                    "출처": "카카오",
                })

            if data.get("meta", {}).get("is_end", True):
                break

    return results


async def get_food() -> list[dict]:
    return await _search("FD6", FOOD_EXCLUDE)


async def get_cafe() -> list[dict]:
    return await _search("CE7", CAFE_EXCLUDE)
