import json
import requests
from flask import Flask, request, jsonify, abort
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

# --- 基礎配置 ---
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN", "6hvWsMRuAwdWKaiFq3F8kn470UC6GaJmTui9QFi0KpIPJIsC1l1GuDYYFp2VMwF7nMG5A/1AhFcXobTbs/PGDIFA+LXg3Re5ZVRusDE8rqGqhO/V6+6/vYLunBZIGdOzLFFDW+7n8dxrkC/f5oljcwdB04t89/1O/w1cDnyilFU=")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "70c03b304a4e165433b82c6d31cf14ec")
FIXED_RTP = 96.89

# 每款遊戲的房號上限
GAME_ROOM_LIMITS = {
    "賽特1": 3000,
    "賽特2": 3000,
    "孫行者": 500,
    "赤三國": 1000,
    "武俠": 500
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

# ==================== 核心邏輯：電子預測 ====================
def calculate_slot_logic(total_bet, score_rate):
    expected_return = total_bet * (FIXED_RTP / 100.0)
    actual_gain = total_bet * (score_rate / 100.0)
    bonus_space = expected_return - actual_gain
    if score_rate >= FIXED_RTP:
        if score_rate > 110:
            level, color = "⚠️ 高位震盪", "#9B59B6"
            desc = f"機台今日表現({score_rate}%)遠超預期，正處於極端吐分波段，隨時可能反轉，建議謹慎操作。"
        else:
            level, color = "🌟 熱機中", "#E67E22"
            desc = "機台數據飽和但動能強勁，目前屬於「連續爆分」波段，建議小量跟進觀察。"
    else:
        if bonus_space >= 500000:
            level, color, desc = "🔥 極致推薦", "#FF4444", "機台積累大量預算，目前處於大回補窗口，爆發力極強！"
        elif bonus_space > 0:
            level, color, desc = "✅ 推薦", "#2ECC71", "機台狀態正向，仍有補償空間，穩定操作。"
        else:
            level, color, desc = "☁️ 觀望", "#7F8C8D", "數據趨於平衡，建議更換房間或等待下一個週期。"
    return {"space": bonus_space, "level": level, "color": color, "desc": desc}

# ==================== Flex 構建 ====================
def build_slot_flex(room, res):
    return {
        "type": "flex", "altText": "電子預測報告",
        "contents": {
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": "#2C3E50", "contents": [
                {"type": "text", "text": "電子數據分析系統", "color": "#ffffff", "weight": "bold", "size": "md", "align": "center"}
            ]},
            "body": {"type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": f"機台房號：{room} | RTP: {FIXED_RTP}%", "size": "xxs", "color": "#888888", "margin": "sm"},
                {"type": "box", "layout": "vertical", "margin": "lg", "backgroundColor": "#F4F6F7", "paddingAll": "md", "cornerRadius": "md", "contents": [
                    {"type": "text", "text": res['level'], "weight": "bold", "size": "lg", "color": res['color'], "align": "center"},
                    {"type": "text", "text": res['desc'], "size": "xs", "wrap": True, "align": "center", "margin": "xs", "color": "#333333"}
                ]}
            ]},
            "footer": {"type": "box", "layout": "vertical", "contents": [
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
                chat_modes[uid] = "slot_choose_game"
                line_reply(tk, sys_bubble("🎰 請選擇電子遊戲：", [
                    {"type": "action", "action": {"type": "message", "label": "賽特1", "text": "選遊戲:賽特1"}},
                    {"type": "action", "action": {"type": "message", "label": "賽特2", "text": "選遊戲:賽特2"}},
                    {"type": "action", "action": {"type": "message", "label": "孫行者", "text": "選遊戲:孫行者"}},
                    {"type": "action", "action": {"type": "message", "label": "赤三國", "text": "選遊戲:赤三國"}},
                    {"type": "action", "action": {"type": "message", "label": "武俠", "text": "選遊戲:武俠"}}
                ]))
            else:
                line_reply(tk, sys_bubble("❌ 權限不足，請先儲值。"))
            continue

        elif mode == "slot_choose_game" and msg.startswith("選遊戲:"):
            game_name = msg.split(":")[-1]
            max_room = GAME_ROOM_LIMITS.get(game_name, 3000)
            chat_modes[uid] = {"state": "slot_choose_room", "game": game_name}
            line_reply(tk, text_with_back(f"✅ 已選 {game_name}\n請輸入房號 (1~{max_room})：\n例如：888"))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_choose_room":
            max_room = GAME_ROOM_LIMITS.get(mode["game"], 3000)
            try:
                room_num = int(msg)
                if room_num < 1 or room_num > max_room:
                    line_reply(tk, sys_bubble(f"⚠️ 房號超出範圍！\n{mode['game']} 的房號範圍為 1~{max_room}，請重新輸入。"))
                    continue
            except ValueError:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤，請輸入純數字房號。"))
                continue
            chat_modes[uid] = {"state": "slot_input_bet", "game": mode["game"], "room": msg}
            line_reply(tk, text_with_back(f"✅ 已鎖定：{mode['game']} 房號 {msg}\n\n第一步：請輸入【今日總下注額】"))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_input_bet":
            try:
                bet = float(msg)
                chat_modes[uid] = {"state": "slot_input_rate", "game": mode["game"], "room": mode["room"], "total_bet": bet}
                line_reply(tk, text_with_back(f"💰 總下注額已設定：{bet:,.0f}\n\n第二步：請輸入【今日得分率】\n(例如：48)"))
            except:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤，請輸入純數字下注額。"))
            continue

        elif isinstance(mode, dict) and mode.get("state") == "slot_input_rate":
            try:
                rate = float(msg)
                total_bet = mode["total_bet"]
                room_display = f"{mode['game']} 房號:{mode['room']}"
                res = calculate_slot_logic(total_bet, rate)
                line_reply(tk, build_slot_flex(room_display, res))
                chat_modes[uid] = {"state": "slot_input_bet", "game": mode["game"], "room": mode["room"]}
            except:
                line_reply(tk, sys_bubble("⚠️ 格式錯誤，請輸入純數字得分率。"))
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

@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "electronic-bot"})

if __name__ == "__main__":
    print("=== Electronic Bot 啟動成功 (port 5002) ===")
    app.run(host="0.0.0.0", port=5002)
