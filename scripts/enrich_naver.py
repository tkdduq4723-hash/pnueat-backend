"""네이버 지도 별점·리뷰수·업체사진 보강

흐름:
  1. 네이버 Local Search API → place_id 추출
  2. 네이버 모바일 플레이스 페이지 → 별점, 리뷰수 파싱
  3. 네이버 내부 사진 API → 업체(owner) 사진 최대 5장

실패 시 별점/리뷰수는 Google Places API로 폴백.

사용법:
  cd backend
  python scripts/enrich_naver.py
"""
import json, time, os, sys, re, urllib.request, urllib.parse
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

NAVER_ID     = os.getenv("NAVER_CLIENT_ID", "")
NAVER_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
GOOGLE_KEY   = os.getenv("GOOGLE_MAPS_API_KEY", "")

LOCAL_URL  = "https://openapi.naver.com/v1/search/local.json"
PHOTO_URL  = "https://map.naver.com/v5/api/place/photo"
GOOGLE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)


# ── 네이버 place_id 취득 ────────────────────────────────────────────────────

def get_naver_place_id(name: str, address: str) -> str | None:
    params = urllib.parse.urlencode({"query": f"{name} {address}", "display": 1})
    req = urllib.request.Request(
        f"{LOCAL_URL}?{params}",
        headers={
            "X-Naver-Client-Id": NAVER_ID,
            "X-Naver-Client-Secret": NAVER_SECRET,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        items = data.get("items", [])
        if not items:
            return None
        link = items[0].get("link", "")
        m = re.search(r"/place/(\d+)", link)
        return m.group(1) if m else None
    except Exception as e:
        print(f"    naver search 오류: {e}")
    return None


# ── 네이버 모바일 페이지 → 별점·리뷰수 ────────────────────────────────────

def get_naver_rating(place_id: str):
    url = f"https://m.place.naver.com/restaurant/{place_id}/home"
    req = urllib.request.Request(url, headers={"User-Agent": MOBILE_UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")

        # window.__NEXT_DATA__ 안의 JSON에서 파싱
        m = re.search(r"window\.__NEXT_DATA__\s*=\s*(\{.+?\})\s*;?\s*</script>", html, re.S)
        if m:
            try:
                nd = json.loads(m.group(1))
                # props > pageProps > initialState > place > ...
                place = (
                    nd.get("props", {})
                      .get("pageProps", {})
                      .get("initialState", {})
                      .get("place", {})
                )
                rating = place.get("starScore") or place.get("reviewScore")
                reviews = place.get("visitorReviewCount") or place.get("reviewCount")
                if rating is not None:
                    return float(rating), int(reviews or 0)
            except Exception:
                pass

        # 폴백: 정규식으로 직접 파싱
        rm = re.search(r'"starScore"\s*:\s*"?([\d.]+)"?', html)
        vm = re.search(r'"visitorReviewCount"\s*:\s*(\d+)', html)
        if rm:
            return float(rm.group(1)), int(vm.group(1)) if vm else 0
    except Exception as e:
        print(f"    naver rating 오류: {e}")
    return None, None


# ── 네이버 업체 사진 (최대 max_count장) ────────────────────────────────────

def get_naver_photos(place_id: str, max_count: int = 5) -> list[str]:
    """
    type=5 → 업체 등록 사진
    type=1 → 전체 사진 (폴백)
    """
    photos = []
    for photo_type in (5, 1):
        params = urllib.parse.urlencode({
            "id": place_id,
            "type": photo_type,
            "page": 1,
            "display": max_count,
        })
        req = urllib.request.Request(
            f"{PHOTO_URL}?{params}",
            headers={
                "User-Agent": MOBILE_UA,
                "Referer": f"https://m.place.naver.com/restaurant/{place_id}/photo",
                "Accept": "application/json, text/plain, */*",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            items = data.get("photos", data.get("items", []))
            for item in items[:max_count]:
                url = (
                    item.get("url")
                    or item.get("imageUrl")
                    or (item.get("images") or [{}])[0].get("url")
                )
                if url:
                    photos.append(url)
            if photos:
                return photos
        except Exception as e:
            print(f"    naver photo(type={photo_type}) 오류: {e}")
    return photos


# ── Google 폴백: 별점·리뷰수 ───────────────────────────────────────────────

def get_google_rating(name: str, address: str):
    params = urllib.parse.urlencode({
        "input": f"{name} {address}",
        "inputtype": "textquery",
        "fields": "rating,user_ratings_total",
        "language": "ko",
        "key": GOOGLE_KEY,
    })
    try:
        with urllib.request.urlopen(f"{GOOGLE_URL}?{params}", timeout=10) as r:
            data = json.loads(r.read())
        c = data.get("candidates", [])
        if c:
            return c[0].get("rating"), c[0].get("user_ratings_total")
    except Exception as e:
        print(f"    google rating 오류: {e}")
    return None, None


# ── 메인 ───────────────────────────────────────────────────────────────────

def enrich(fpath: str):
    with open(fpath, encoding="utf-8") as f:
        items = json.load(f)

    targets = [i for i in items if "별점" not in i]
    print(f"\n{os.path.basename(fpath)}: {len(targets)}/{len(items)}개 처리 필요\n")

    naver_ok = google_ok = photo_ok = 0

    for idx, item in enumerate(targets):
        name    = item["이름"]
        address = item.get("주소", "부산 금정구")
        prefix  = f"[{idx+1}/{len(targets)}] {name[:16]:16s}"

        # 1) 네이버 place_id
        pid = get_naver_place_id(name, address)
        time.sleep(0.1)

        if pid:
            # 2) 별점·리뷰수
            rating, reviews = get_naver_rating(pid)
            time.sleep(0.15)

            # 3) 업체 사진
            photos = get_naver_photos(pid)
            time.sleep(0.15)
        else:
            rating, reviews, photos = None, None, []

        # 네이버 별점 실패 → Google 폴백
        if rating is None and GOOGLE_KEY:
            rating, reviews = get_google_rating(name, address)
            if rating is not None:
                google_ok += 1
                src = "G"
            else:
                src = "✗"
        elif rating is not None:
            naver_ok += 1
            src = "N"
        else:
            src = "✗"

        if photos:
            photo_ok += 1

        item["별점"]  = rating
        item["리뷰수"] = reviews
        item["사진목록"] = photos  # 여러 장 저장
        # 기존 단일 사진 필드도 첫 번째로 유지
        if photos and not item.get("사진"):
            item["사진"] = photos[0]

        print(
            f"{prefix} 별점:{rating or '-':>5}({src})  "
            f"리뷰:{str(reviews or 0):>5}  사진:{len(photos)}장"
        )

        # 10개마다 중간 저장
        if (idx + 1) % 10 == 0:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"\n완료 — 네이버:{naver_ok}  구글폴백:{google_ok}  사진:{photo_ok}/{len(targets)}\n")


if not NAVER_ID or not NAVER_SECRET:
    print("오류: NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 없음")
    sys.exit(1)

base = os.path.join(os.path.dirname(__file__), "..", "data")
enrich(os.path.join(base, "restaurants.json"))
print("전체 완료!")
