import json
import requests
from flask import Flask, request, jsonify, abort, send_from_directory
import os
import uuid
from datetime import datetime, timedelta, timezone
import traceback
import random
import threading
import hmac
import hashlib
import base64

app = Flask(__name__)

# --- 圖片基底 URL（部署後自動取得，或手動設定） ---
BASE_URL = os.environ.get("BASE_URL", "https://electronic-line.onrender.com")

# --- 基礎配置 ---
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN", "6hvWsMRuAwdWKaiFq3F8kn470UC6GaJmTui9QFi0KpIPJIsC1l1GuDYYFp2VMwF7nMG5A/1AhFcXobTbs/PGDIFA+LXg3Re5ZVRusDE8rqGqhO/V6+6/vYLunBZIGdOzLFFDW+7n8dxrkC/f5oljcwdB04t89/1O/w1cDnyilFU=")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "70c03b304a4e165433b82c6d31cf14ec")
# ==================== 遊戲館配置 ====================
# ATG 遊戲館
ATG_GAMES = {
    "賽特1":  {"room_limit": 3000, "logo": "ATG/賽特.png"},
    "賽特2":  {"room_limit": 3000, "logo": "ATG/賽特2.png"},
    "孫行者": {"room_limit": 500,  "logo": "ATG/孫行者.png"},
    "赤三國": {"room_limit": 1000, "logo": "ATG/赤三國.png"},
    "武俠":   {"room_limit": 500,  "logo": "ATG/武俠.png"}
}

# AT 遊戲館（房號皆 1~200）
AT_GAMES = {
    "元素連結火": {"room_limit": 200, "logo": "AT/元素連結火.png"},
    "台灣黑熊":   {"room_limit": 200, "logo": "AT/台灣黑熊.png"},
    "哥吉拉覺醒": {"room_limit": 200, "logo": "AT/哥吉拉覺醒.png"},
    "圓桌聖戰":   {"room_limit": 200, "logo": "AT/圓桌聖戰.jpg"},
    "奪寶奇兵":   {"room_limit": 200, "logo": "AT/奪寶奇兵.png"},
    "孫行者":     {"room_limit": 200, "logo": "AT/孫行者.png"},
    "寶石礦工":   {"room_limit": 200, "logo": "AT/寶石礦工.png"},
    "悟空":       {"room_limit": 200, "logo": "AT/悟空.png"},
    "戰神呂布":   {"room_limit": 200, "logo": "AT/戰神呂布.png"},
    "有請財神":   {"room_limit": 200, "logo": "AT/有請財神.png"},
    "水果盤":     {"room_limit": 200, "logo": "AT/水果盤.png"},
    "海盜寶藏":   {"room_limit": 200, "logo": "AT/海盜寶藏.png"},
    "海神之怒":   {"room_limit": 200, "logo": "AT/海神之怒.png"},
    "烈日女神":   {"room_limit": 200, "logo": "AT/烈日女神.png"},
    "石中劍":     {"room_limit": 200, "logo": "AT/石中劍.png"},
    "西遊記":     {"room_limit": 200, "logo": "AT/西遊記.png"},
    "變臉":       {"room_limit": 200, "logo": "AT/變臉.png"},
    "雪怪":       {"room_limit": 200, "logo": "AT/雪怪.png"},
    "雷神之錘":   {"room_limit": 200, "logo": "AT/雷神之錘.png"},
    "駱馬大冒險": {"room_limit": 200, "logo": "AT/駱馬大冒險.png"},
    "魔童哪吒":   {"room_limit": 200, "logo": "AT/魔童哪吒.png"},
    "魔龍傳奇":   {"room_limit": 200, "logo": "AT/魔龍傳奇.png"},
    "麻將又胡了": {"room_limit": 200, "logo": "AT/麻將又胡了.png"},
    "麻雀無雙":   {"room_limit": 200, "logo": "AT/麻雀無雙.png"}
}

# RG 遊戲廳
RG_GAMES = {
    "屠龍勇者":       {"room_limit": 300, "logo": "RG/屠龍勇者.png"},
    "維京Fight":      {"room_limit": 40,  "logo": "RG/維京Fight.png"},
    "大法師":         {"room_limit": 40,  "logo": "RG/大法師.png"},
    "麻將發大財":     {"room_limit": 40,  "logo": "RG/麻將發大財.png"},
    "爆爆怪妞":       {"room_limit": 40,  "logo": "RG/爆爆怪妞.png"},
    "激鬥擂台":       {"room_limit": 40,  "logo": "RG/激鬥擂台.png"},
    "奇幻魔藥":       {"room_limit": 40,  "logo": "RG/奇幻魔藥.png"},
    "忍 Kunoichi":    {"room_limit": 100, "logo": "RG/忍 Kunoichi.png"},
    "神鬼戰士":       {"room_limit": 40,  "logo": "RG/神鬼戰士.png"},
    "強棒 HOMERUN":   {"room_limit": 40,  "logo": "RG/強棒 HOMERUN.png"},
    "異星進化 UpUp":  {"room_limit": 40,  "logo": "RG/異星進化 UpUp.png"},
    "金虎爺":         {"room_limit": 40,  "logo": "RG/金虎爺.png"},
    "RG Star 777":    {"room_limit": 40,  "logo": "RG/RG Star 777.png"},
    "秘寶探險":       {"room_limit": 40,  "logo": "RG/秘寶探險.png"},
    "鬥雞":           {"room_limit": 40,  "logo": "RG/鬥雞.png"},
    "High翻":         {"room_limit": 40,  "logo": "RG/High翻.png"},
    "福爾摩斯":       {"room_limit": 40,  "logo": "RG/福爾摩斯.png"},
    "狂野海盜":       {"room_limit": 40,  "logo": "RG/狂野海盜.png"},
    "魚魚魚":         {"room_limit": 40,  "logo": "RG/魚魚魚.png"},
    "魔獸世界":       {"room_limit": 40,  "logo": "RG/魔獸世界.png"},
    "鮨 Sushi":       {"room_limit": 40,  "logo": "RG/鮨 Sushi.png"},
    "果汁派對":       {"room_limit": 40,  "logo": "RG/果汁派對.png"},
    "Alien Poker":    {"room_limit": 40,  "logo": "RG/Alien Poker.png"}
}

# 賽特訊號圖片路徑
SETTE_SIGNALS = {
    "刀": "ATG/賽特訊號/刀.png",
    "弓": "ATG/賽特訊號/弓.png",
    "眼": "ATG/賽特訊號/眼.png",
    "蛇": "ATG/賽特訊號/蛇.png",
    "甲蟲": "ATG/賽特訊號/甲蟲.png",
    "百倍球": "ATG/賽特訊號/百倍球.png",
    "綠球": "ATG/賽特訊號/綠球.png",
}
SETTE2_SIGNALS = {
    "刀": "ATG/賽特2訊號/刀.png",
    "弓": "ATG/賽特2訊號/弓.png",
    "眼": "ATG/賽特2訊號/眼.png",
    "蛇": "ATG/賽特2訊號/蛇.png",
    "甲蟲": "ATG/賽特2訊號/甲蟲.png",
    "百倍球": "ATG/賽特2訊號/百倍球.png",
    "綠球": "ATG/賽特2訊號/綠球.png",
    "黃金聖甲蟲": "ATG/賽特2訊號/黃金聖甲蟲.png",
}

# 建立圖片 ID 對照表（避免中文 URL 問題）
IMAGE_MAP = {}
_img_id = 1
for _games in [ATG_GAMES, AT_GAMES, RG_GAMES]:
    for _name, _info in _games.items():
        _path = _info["logo"]
        if _path not in IMAGE_MAP.values():
            IMAGE_MAP[str(_img_id)] = _path
            _img_id += 1
# 加入訊號圖片
for _sig_dict in [SETTE_SIGNALS, SETTE2_SIGNALS]:
    for _sname, _spath in _sig_dict.items():
        if _spath not in IMAGE_MAP.values():
            IMAGE_MAP[str(_img_id)] = _spath
            _img_id += 1

# 反向查詢：logo_path -> image_id
IMAGE_PATH_TO_ID = {v: k for k, v in IMAGE_MAP.items()}

def get_game_info(hall, game_name):
    """根據館別和遊戲名取得設定"""
    if hall == "ATG":
        return ATG_GAMES.get(game_name)
    elif hall == "AT":
        return AT_GAMES.get(game_name)
    elif hall == "RG":
        return RG_GAMES.get(game_name)
    return None

def get_logo_url(logo_path):
    """產生圖片完整 URL（使用數字 ID，避免中文編碼問題）"""
    img_id = IMAGE_PATH_TO_ID.get(logo_path, "0")
    return f"{BASE_URL}/img/{img_id}"

def generate_signal(game_name):
    """產生賽特/賽特2 的隨機訊號組合（限制2~4種不同符號）"""
    is_sette2 = (game_name == "賽特2")
    sig_map = SETTE2_SIGNALS if is_sette2 else SETTE_SIGNALS

    total_target = random.randint(8, 13)
    result = {}

    # 1. 紅球（百倍球）最多1個，約15%；綠球約25%，互斥
    has_red = random.random() < 0.15
    if has_red:
        result["百倍球"] = 1
        total_target -= 1
    elif random.random() < 0.25:
        result["綠球"] = 1
        total_target -= 1

    # 2. 甲蟲：0~3個
    beetle_count = random.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0]
    if beetle_count > 0:
        result["甲蟲"] = beetle_count
        total_target -= beetle_count

    # 3. 黃金聖甲蟲（僅賽特2）：甲蟲=3時不出現
    if is_sette2 and beetle_count < 3:
        if random.random() < 0.12:
            result["黃金聖甲蟲"] = 1
            total_target -= 1

    # 4. 主要符號：從刀弓眼蛇中隨機選2~3種來分配剩餘數量
    main_symbols = ["刀", "弓", "眼", "蛇"]
    random.shuffle(main_symbols)
    pick_count = random.randint(2, 3)
    chosen = main_symbols[:pick_count]
    remaining = max(total_target, 0)

    for i, sym in enumerate(chosen):
        if remaining <= 0:
            break
        if i == len(chosen) - 1:
            count = min(remaining, 7)
        else:
            count = random.randint(1, min(7, remaining))
        result[sym] = count
        remaining -= count

    # 組合成列表
    signals = []
    for name, count in result.items():
        url = get_logo_url(sig_map[name])
        signals.append({"name": name, "count": count, "url": url})
    return signals

def build_signal_flex(signals, game_name):
    """建立訊號顯示的 Flex bubble"""
    rows = []
    for sig in signals:
        row = {
            "type": "box", "layout": "horizontal", "alignItems": "center", "margin": "sm",
            "contents": [
                {"type": "image", "url": sig["url"], "size": "xxs", "aspectMode": "cover", "aspectRatio": "1:1", "flex": 0},
                {"type": "text", "text": f"  {sig['name']} ×{sig['count']}", "size": "sm", "color": "#333333", "flex": 3, "gravity": "center"}
            ]
        }
        rows.append(row)

    return {
        "type": "bubble", "size": "kilo",
        "header": {"type": "box", "layout": "vertical", "backgroundColor": "#1A1A2E", "paddingAll": "md", "contents": [
            {"type": "text", "text": f"🔮 {game_name} 訊號預測", "color": "#FFD700", "weight": "bold", "size": "md", "align": "center"}
        ]},
        "body": {"type": "box", "layout": "vertical", "paddingAll": "lg", "contents": [
            {"type": "text", "text": "本次推薦訊號組合：", "size": "xs", "color": "#888888", "margin": "none"},
            {"type": "separator", "margin": "md"},
            *rows,
            {"type": "separator", "margin": "md"},
            {"type": "text", "text": f"共 {sum(s['count'] for s in signals)} 個訊號", "size": "xs", "color": "#888888", "align": "end", "margin": "sm"}
        ]}
    }

# 管理員 UID
ADMIN_UIDS = ["Ub9a0ddfd2b9fd49e3500fa08e2fbbbe7", "U543d02a7d79565a14d475bff5b357f05", "U8ad3ca4119c006d2aa47c346d90de5cf"]

USER_DATA_FILE = "user_data.json"
TIME_CARDS_FILE = "time_cards.json"

# 允許的序號期限
VALID_DURATIONS = {"10M": "10分鐘", "1H": "1小時", "2D": "2天", "7D": "7天", "12D": "12天", "30D": "30天"}

# --- 全局變數初始化 ---
chat_modes = {}
user_access_data = {}
time_cards_data = {"active_cards": {}, "used_cards": {}}

user_data_lock = threading.RLock()
time_cards_data_lock = threading.RLock()

# --- 資料存取 ---
def load_data(f, default_val=None):
    if os.path.exists(f):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                return json.load(file)
        except:
            pass
    return default_val if default_val is not None else {}

def save_data(f, d):
    try:
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(d, file, ensure_ascii=False, indent=4)
    except:
        pass

# 模組載入時讀取資料
user_access_data = load_data(USER_DATA_FILE)
time_cards_data = load_data(TIME_CARDS_FILE, {"active_cards": {}, "used_cards": {}})

# --- 安全驗證 ---
def verify_signature(body, signature):
    hash = hmac.new(LINE_CHANNEL_SECRET.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(hash).decode('utf-8') == signature

# ==================== 核心邏輯：電子預測（ROI + 轉數 綜合模型） ====================
FIXED_RTP = 96.89

def calculate_slot_logic(investment, balance, no_hit_spins=0, prev1=0, prev2=0):
    # --- ROI 分數 ---
    profit = balance - investment
    roi = (profit / investment * 100) if investment > 0 else 0
    expected_roi = FIXED_RTP - 100  # -3.11%
    roi_gap = roi - expected_roi  # 負值越大 → 機台虧越多 → 越可能回補

    roi_score = 0
    if roi_gap < -30:
        roi_score = 20
    elif roi_gap < -15:
        roi_score = 12
    elif roi_gap < -5:
        roi_score = 5
    elif roi_gap > 10:
        roi_score = -10

    # --- 轉數熱度分數 ---
    spin_score = 0
    if no_hit_spins >= 200:
        spin_score = 40
    elif no_hit_spins >= 150:
        spin_score = 30
    elif no_hit_spins >= 100:
        spin_score = 20
    elif no_hit_spins >= 50:
        spin_score = 10
    elif no_hit_spins >= 20:
        spin_score = 5

    # --- 前兩轉趨勢分數 ---
    trend_score = 0
    if investment > 0:
        for pv in [prev1, prev2]:
            ratio = pv / investment * 100
            if ratio == 0:
                trend_score += 5
            elif ratio < 2:
                trend_score += 3
            elif ratio > 30:
                trend_score -= 8
            elif ratio > 15:
                trend_score -= 4

    # --- 綜合分數 ---
    score = roi_score + spin_score + trend_score

    if roi >= 10:
        level, color = "⚠️ 高位震盪", "#9B59B6"
        desc = f"目前回報率 {roi:+.1f}%，遠超機台預期，正處於吐分尾段，隨時可能反轉，建議謹慎操作。"
    elif score >= 45:
        level, color = "🔥 極致推薦", "#FF4444"
        desc = f"目前回報率 {roi:+.1f}%，已空轉 {no_hit_spins} 轉，機台積累大量預算，大回補窗口，爆發力極強！"
    elif score >= 25:
        level, color = "✅ 推薦", "#2ECC71"
        desc = f"目前回報率 {roi:+.1f}%，空轉 {no_hit_spins} 轉，機台狀態正向，仍有補償空間，穩定操作。"
    elif score >= 10:
        level, color = "🌟 熱機中", "#E67E22"
        desc = f"目前回報率 {roi:+.1f}%，空轉 {no_hit_spins} 轉，機台逐步進入回補區間，可小量跟進觀察。"
    else:
        level, color = "☁️ 觀望", "#7F8C8D"
        desc = f"目前回報率 {roi:+.1f}%，空轉 {no_hit_spins} 轉，數據趨於平衡，建議更換房間或等待下一個週期。"

    return {"roi": roi, "score": score, "level": level, "color": color, "desc": desc}

# ==================== Flex 構建 ====================
def build_game_carousel(hall, games_dict, page=1):
    """建立帶有 LOGO 的遊戲選擇 Flex Carousel（每頁最多 12 款）"""
    MAX_PER_PAGE = 11
    items = list(games_dict.items())
    total_pages = (len(items) + MAX_PER_PAGE - 1) // MAX_PER_PAGE
    start = (page - 1) * MAX_PER_PAGE
    end = start + MAX_PER_PAGE
    page_items = items[start:end]

    bubbles = []
    for game_name, info in page_items:
        logo_url = get_logo_url(info["logo"])
        bubble = {
            "type": "bubble", "size": "micro",
            "hero": {
                "type": "image",
                "url": logo_url,
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": game_name, "weight": "bold", "size": "sm", "align": "center"}
                ],
                "paddingAll": "sm"
            },
            "footer": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "button", "action": {"type": "message", "label": "選擇", "text": f"選遊戲:{hall}:{game_name}"}, "style": "primary", "color": "#2C3E50", "height": "sm"}
                ],
                "paddingAll": "sm"
            }
        }
        bubbles.append(bubble)

    if total_pages > 1 and page < total_pages:
        nav_bubble = {
            "type": "bubble", "size": "micro",
            "body": {
                "type": "box", "layout": "vertical", "justifyContent": "center", "alignItems": "center",
                "contents": [
                    {"type": "text", "text": f"第 {page}/{total_pages} 頁", "size": "sm", "color": "#888888", "align": "center"},
                    {"type": "button", "action": {"type": "message", "label": f"下一頁 ▶", "text": f"遊戲頁:{hall}:{page + 1}"}, "style": "primary", "color": "#E67E22", "margin": "md", "height": "sm"}
                ],
                "paddingAll": "lg"
            }
        }
        bubbles.append(nav_bubble)

    title = f"{hall} 遊戲選擇" if total_pages == 1 else f"{hall} 遊戲選擇 ({page}/{total_pages})"
    return {
        "type": "flex", "altText": title,
        "contents": {"type": "carousel", "contents": bubbles}
    }

def build_slot_flex(room, res, signals=None):
    body_contents = [
        {"type": "text", "text": f"機台房號：{room}", "size": "xxs", "color": "#888888", "margin": "sm"},
        {"type": "box", "layout": "vertical", "margin": "lg", "backgroundColor": "#F4F6F7", "paddingAll": "md", "cornerRadius": "md", "contents": [
            {"type": "text", "text": res['level'], "weight": "bold", "size": "lg", "color": res['color'], "align": "center"},
            {"type": "text", "text": res['desc'], "size": "xs", "wrap": True, "align": "center", "margin": "xs", "color": "#333333"}
        ]}
    ]
    # 如果有訊號，合併到同一個 bubble
    if signals:
        body_contents.append({"type": "separator", "margin": "lg"})
        body_contents.append({"type": "text", "text": "🔮 訊號預測", "weight": "bold", "size": "sm", "color": "#1A1A2E", "margin": "lg", "align": "center"})
        for sig in signals:
            row = {
                "type": "box", "layout": "horizontal", "alignItems": "center", "margin": "sm",
                "contents": [
                    {"type": "image", "url": sig["url"], "size": "xxs", "aspectMode": "cover", "aspectRatio": "1:1", "flex": 0},
                    {"type": "text", "text": f"  {sig['name']} ×{sig['count']}", "size": "sm", "color": "#333333", "flex": 3, "gravity": "center"}
                ]
            }
            body_contents.append(row)

    return {
        "type": "flex", "altText": "電子預測報告",
        "contents": {
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": "#2C3E50", "contents": [
                {"type": "text", "text": "電子數據分析系統", "color": "#ffffff", "weight": "bold", "size": "md", "align": "center"}
            ]},
            "body": {"type": "box", "layout": "vertical", "contents": body_contents},
            "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
                {"type": "button", "action": {"type": "message", "label": "🔄 判斷下一桌", "text": "判斷下一桌"}, "style": "primary", "color": "#E67E22"},
                {"type": "button", "action": {"type": "message", "label": "返回主選單", "text": "返回主選單"}, "style": "primary", "color": "#2C3E50"}
            ]}
        }
    }

# ==================== LINE 回覆 ====================
def line_reply(reply_token, payload):
    MENU_QUICK_REPLY = {"items": [
        {"type": "action", "action": {"type": "message", "label": "電子預測", "text": "電子預測"}},
        {"type": "action", "action": {"type": "message", "label": "儲值", "text": "儲值"}},
        {"type": "action", "action": {"type": "message", "label": "返回主選單", "text": "返回主選單"}}
    ]}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    if isinstance(payload, list):
        msgs = payload
    elif isinstance(payload, dict):
        msgs = [payload]
    else:
        msgs = [{"type": "text", "text": str(payload)}]
    if msgs:
        last = msgs[-1]
        if "quickReply" not in last:
            last["quickReply"] = MENU_QUICK_REPLY
    resp = requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json={"replyToken": reply_token, "messages": msgs})
    if resp.status_code != 200:
        print(f"[LINE API ERROR] {resp.status_code}: {resp.text[:300]}")
    else:
        print(f"[LINE API OK] sent {len(msgs)} msg(s)")

def sys_bubble(text, quick_reply_items=None):
    bubble = {
        "type": "flex", "altText": text[:40],
        "contents": {
            "type": "bubble", "size": "kilo",
            "body": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#F7F9FA",
                "borderColor": "#D5D8DC", "borderWidth": "1px", "cornerRadius": "lg",
                "paddingAll": "lg",
                "contents": [{"type": "text", "text": text, "wrap": True, "size": "sm", "color": "#2C3E50", "align": "center"}]
            }
        }
    }
    if quick_reply_items:
        bubble["quickReply"] = {"items": quick_reply_items}
    return bubble

def text_with_back(text):
    return sys_bubble(text, [{"type": "action", "action": {"type": "message", "label": "↩ 返回主選單", "text": "返回主選單"}}])

# ==================== 輔助功能 ====================
def send_main_menu(tk):
    line_reply(tk, sys_bubble("--- 電子 AI 預測系統 ---", [
        {"type": "action", "action": {"type": "message", "label": "電子預測", "text": "電子預測"}},
        {"type": "action", "action": {"type": "message", "label": "儲值", "text": "儲值"}},
        {"type": "action", "action": {"type": "message", "label": "返回主選單", "text": "返回主選單"}}
    ]))

def get_access_status(uid):
    if uid in ADMIN_UIDS:
        return "active", "永久"
    user = user_access_data.get(uid)
    if not user:
        return "none", ""
    expiry = datetime.fromisoformat(user["expiry_date"].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    if now < expiry:
        diff = expiry - now
        return "active", f"{diff.days}天 {diff.seconds // 3600}時"
    return "expired", ""

def use_time_card(uid, code):
    with time_cards_data_lock:
        active = time_cards_data.get("active_cards", {})
        if code not in active:
            return False, "❌ 序號無效"
        dur_str = active[code]["duration"]
        val = int(''.join(filter(str.isdigit, dur_str)))
        now = datetime.now(timezone.utc)
        current_expiry = datetime.fromisoformat(
            user_access_data.get(uid, {"expiry_date": now.isoformat()})["expiry_date"].replace('Z', '+00:00')
        )
        base_time = max(now, current_expiry)
        if 'M' in dur_str:
            delta = timedelta(minutes=val)
        elif 'H' in dur_str:
            delta = timedelta(hours=val)
        else:
            delta = timedelta(days=val)
        new_expiry = (base_time + delta).isoformat().replace("+00:00", "Z")
        user_access_data[uid] = {"expiry_date": new_expiry}
        time_cards_data.setdefault("used_cards", {})[code] = active.pop(code)
        save_data(USER_DATA_FILE, user_access_data)
        save_data(TIME_CARDS_FILE, time_cards_data)
        return True, f"✅ 儲值成功！有效期至：\n{new_expiry[:16]}"

# ==================== Webhook 入口 ====================
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    if not verify_signature(body, signature):
        abort(400)

    data = request.json
    for event in data.get("events", []):
        if event["type"] != "message" or "text" not in event["message"]:
            continue
        uid = event["source"]["userId"]
        tk = event["replyToken"]
        msg = event["message"]["text"].strip()
        print(f"[RECV] uid={uid[-6:]}, msg={msg}, mode={chat_modes.get(uid)}")

        # 1. 基礎指令
        if msg.upper() in ["UID", "查詢ID", "我的ID"]:
            line_reply(tk, sys_bubble(f"📋 您的 UID：\n{uid}"))
            continue

        if uid in ADMIN_UIDS and msg.startswith("產生序號"):
            try:
                _, duration, count = msg.split()
                dur_key = duration.upper()
                if dur_key not in VALID_DURATIONS:
                    valid_list = "\n".join([f"  {k} = {v}" for k, v in VALID_DURATIONS.items()])
                    line_reply(tk, sys_bubble(f"⚠️ 無效期限【{duration}】\n\n可用期限：\n{valid_list}\n\n格式：產生序號 [期限] [數量]"))
                    continue
                codes = []
                with time_cards_data_lock:
                    for _ in range(int(count)):
                        code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=10))
                        time_cards_data["active_cards"][code] = {"duration": dur_key, "created_at": datetime.now(timezone.utc).isoformat()}
                        codes.append(code)
                    save_data(TIME_CARDS_FILE, time_cards_data)
                line_reply(tk, [
                    sys_bubble(f"✅ 已產生 {count} 組【{VALID_DURATIONS[dur_key]}】序號："),
                    {"type": "text", "text": "\n".join(codes)}
                ])
            except:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤：產生序號 [期限] [數量]\n\n可用：10M / 1H / 2D / 7D / 12D / 30D"))
            continue

        if msg == "返回主選單":
            chat_modes.pop(uid, None)
            send_main_menu(tk)
            continue

        # 2. 狀態機與功能入口
        mode = chat_modes.get(uid)
        status, left = get_access_status(uid)

        # --- 電子預測 ---
        if msg == "電子預測":
            if status == "active":
                chat_modes[uid] = "slot_choose_hall"
                line_reply(tk, sys_bubble("🎰 請選擇遊戲館：", [
                    {"type": "action", "action": {"type": "message", "label": "ATG 遊戲館", "text": "選館:ATG"}},
                    {"type": "action", "action": {"type": "message", "label": "AT 遊戲館", "text": "選館:AT"}},
                    {"type": "action", "action": {"type": "message", "label": "RG 遊戲廳", "text": "選館:RG"}}
                ]))
            else:
                line_reply(tk, sys_bubble("❌ 權限不足，請先儲值。"))
            continue

        elif mode == "slot_choose_hall" and msg.startswith("選館:"):
            hall = msg.split(":")[-1]
            if hall == "ATG":
                chat_modes[uid] = {"state": "slot_choose_game", "hall": "ATG"}
                line_reply(tk, build_game_carousel("ATG", ATG_GAMES))
            elif hall == "AT":
                chat_modes[uid] = {"state": "slot_choose_game", "hall": "AT"}
                line_reply(tk, build_game_carousel("AT", AT_GAMES))
            elif hall == "RG":
                chat_modes[uid] = {"state": "slot_choose_game", "hall": "RG"}
                line_reply(tk, build_game_carousel("RG", RG_GAMES))
            else:
                line_reply(tk, sys_bubble("⚠️ 無效的遊戲館，請重新選擇。"))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_choose_game" and msg.startswith("遊戲頁:"):
            parts = msg.split(":")
            hall = parts[1]
            page = int(parts[2])
            games = ATG_GAMES if hall == "ATG" else (RG_GAMES if hall == "RG" else AT_GAMES)
            line_reply(tk, build_game_carousel(hall, games, page))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_choose_game" and msg.startswith("選遊戲:"):
            parts = msg.split(":")
            hall = parts[1] if len(parts) >= 3 else mode.get("hall", "ATG")
            game_name = parts[-1]
            info = get_game_info(hall, game_name)
            if not info:
                line_reply(tk, sys_bubble("⚠️ 找不到該遊戲，請重新選擇。"))
                continue
            max_room = info["room_limit"]
            chat_modes[uid] = {"state": "slot_choose_room", "hall": hall, "game": game_name}
            line_reply(tk, text_with_back(f"✅ 已選【{hall}】{game_name}\n請輸入房號 (1~{max_room})：\n例如：88"))
            continue

        elif msg == "判斷下一桌" and isinstance(mode, dict) and mode.get("hall") and mode.get("game"):
            hall = mode["hall"]
            game_name = mode["game"]
            info = get_game_info(hall, game_name)
            max_room = info["room_limit"] if info else 200
            chat_modes[uid] = {"state": "slot_choose_room", "hall": hall, "game": game_name}
            line_reply(tk, text_with_back(f"🔄 繼續判斷【{hall}】{game_name}\n請輸入下一桌房號 (1~{max_room})："))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_choose_room":
            hall = mode.get("hall", "ATG")
            info = get_game_info(hall, mode["game"])
            max_room = info["room_limit"] if info else 200
            try:
                room_num = int(msg)
                if room_num < 1 or room_num > max_room:
                    line_reply(tk, sys_bubble(f"⚠️ 房號超出範圍！\n{mode['game']} 的房號範圍為 1~{max_room}，請重新輸入。"))
                    continue
            except ValueError:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤，請輸入純數字房號。"))
                continue
            chat_modes[uid] = {"state": "slot_input_invest", "hall": hall, "game": mode["game"], "room": msg}
            line_reply(tk, text_with_back(f"✅ 已鎖定：【{hall}】{mode['game']} 房號 {msg}\n\n第一步：請輸入【總投入金額】\n(例如：5000)"))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_input_invest":
            try:
                invest = float(msg)
                if invest <= 0:
                    line_reply(tk, sys_bubble("⚠️ 總投入金額必須大於 0，請重新輸入。"))
                    continue
                chat_modes[uid] = {"state": "slot_input_balance", "hall": mode.get("hall"), "game": mode["game"], "room": mode["room"], "investment": invest}
                line_reply(tk, text_with_back(f"💰 總投入：{invest:,.0f}\n\n第二步：請輸入【目前餘額】\n(例如：3200)"))
            except:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤，請輸入純數字金額。"))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_input_balance":
            try:
                balance = float(msg)
                chat_modes[uid] = {**mode, "state": "slot_input_nohit", "balance": balance}
                line_reply(tk, text_with_back(f"💰 目前餘額：{balance:,.0f}\n\n第三步：請輸入【未開獎轉數】\n(已經空轉幾轉沒中，例如：80)"))
            except:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤，請輸入純數字餘額。"))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_input_nohit":
            try:
                nohit = int(msg)
                if nohit < 0:
                    line_reply(tk, sys_bubble("⚠️ 轉數不能為負數，請重新輸入。"))
                    continue
                chat_modes[uid] = {**mode, "state": "slot_input_prev1", "nohit": nohit}
                line_reply(tk, text_with_back(f"🎰 空轉：{nohit} 轉\n\n第四步：請輸入【前一轉開出金額】\n(例如：50，沒開輸入 0)"))
            except:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤，請輸入純數字轉數。"))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_input_prev1":
            try:
                prev1 = float(msg)
                chat_modes[uid] = {**mode, "state": "slot_input_prev2", "prev1": prev1}
                line_reply(tk, text_with_back(f"🎰 前一轉：{prev1:,.0f}\n\n第五步：請輸入【前二轉開出金額】\n(例如：0，沒開輸入 0)"))
            except:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤，請輸入純數字金額。"))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_input_prev2":
            try:
                prev2 = float(msg)
                investment = mode["investment"]
                balance = mode["balance"]
                nohit = mode["nohit"]
                prev1 = mode["prev1"]
                room_display = f"【{mode.get('hall')}】{mode['game']} 房號:{mode['room']}"
                res = calculate_slot_logic(investment, balance, nohit, prev1, prev2)
                # 賽特1/賽特2 附帶訊號預測（合併在同一個 bubble）
                signals = None
                if mode["game"] in ("賽特1", "賽特2"):
                    signals = generate_signal(mode["game"])
                line_reply(tk, build_slot_flex(room_display, res, signals))
                chat_modes[uid] = {"state": "slot_input_invest", "hall": mode.get("hall"), "game": mode["game"], "room": mode["room"]}
            except:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤，請輸入純數字金額。"))
            continue

        # 儲值入口
        if msg == "儲值":
            chat_modes[uid] = "input_card"
            line_reply(tk, sys_bubble("請輸入 10 位儲值序號："))
            continue

        elif mode == "input_card":
            success, result_msg = use_time_card(uid, msg.upper())
            chat_modes.pop(uid, None)
            line_reply(tk, sys_bubble(result_msg))
            continue

        # 持久選單出口
        send_main_menu(tk)

    return jsonify({"status": "ok"})

@app.route("/img/<img_id>", methods=["GET"])
def serve_image(img_id):
    logo_path = IMAGE_MAP.get(img_id)
    if not logo_path:
        abort(404)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.join(base_dir, os.path.dirname(logo_path))
    filename = os.path.basename(logo_path)
    return send_from_directory(directory, filename)

@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "electronic-bot"})

if __name__ == "__main__":
    print("=== Electronic Bot 啟動成功 (port 5002) ===")
    app.run(host="0.0.0.0", port=5002)
