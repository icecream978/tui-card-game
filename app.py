import streamlit as st
import random
import time
import os
import base64
import threading
import math
import html as _html
from streamlit_autorefresh import st_autorefresh
from tui_engine import (
    deal_round, deal_step, needs_redeal, can_play_tui, can_play_sahoo,
    get_available_tuis, get_available_sahoos, resolve_trick,
    get_available_sa_juk, get_available_pho_juk, get_available_five_juk,
    get_available_pho_hoo, get_available_five_hoo, get_available_six_hoo, validate_play,
    RANK_ORDER, RANK_COUNTS
)

# ---------------------------------------------------------
# 📱 ตั้งค่าหน้าจอ & CSS สำหรับมือถือ
# ---------------------------------------------------------
st.set_page_config(
    page_title="เกมตุ่ย Mobile", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# รีเฟรชอัตโนมัติทุก 3 วินาที
st_autorefresh(interval=3000, key="datarefresh")

st.markdown("""
<style>
    .block-container { padding-top: 0.5rem; padding-bottom: 0.5rem; padding-left: 0.3rem; padding-right: 0.3rem; }
    div[data-testid="stSidebarNav"] { display: none; }
    .stAlert { padding: 4px 8px !important; margin-bottom: 4px !important; }
    hr { margin: 6px 0 !important; }

    /* 📱 บังคับให้คอลัมน์ไพ่อยู่แถวเดียวกัน 4 ใบเสมอ ไม่ลงมาต่อแถวยาว */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        align-items: flex-start !important;
    }
    
    div[data-testid="stColumn"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        width: auto !important;
        padding: 0 !important;
    }

    /* 🖼️ ปรับขนาดรูปภาพไพ่ */
    div[data-testid="stImage"] img {
        max-height: 85px !important;
        width: 100% !important;
        object-fit: contain !important;
        margin: 0 auto !important;
        display: block !important;
        border-radius: 6px !important;
        pointer-events: none !important;
    }

    /* 🔘 ปรับสไตล์ปุ่มกดเลือกไพ่ใต้รูปให้เต็มช่อง กดง่ายบนมือถือ */
    div[data-testid="stColumn"] .stButton > button {
        width: 100% !important;
        padding: 4px 2px !important;
        font-size: 11px !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        margin-top: 2px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# ✨ เอฟเฟกต์ & ธีม (ปิด/เปิดได้ที่นี่)
# ---------------------------------------------------------
FELT_THEME = True      # โต๊ะสักหลาดเขียว (ตั้งเป็น False ถ้าอยากได้ธีมเดิมของ Streamlit)
TOTAL_ROUNDS = 15

FX_CSS = """
.pc { max-height: 85px; width: 100%; object-fit: contain; display: block; margin: 0 auto; border-radius: 6px; transition: transform .15s ease, box-shadow .15s ease; }
.pc.sel { transform: translateY(-8px) scale(1.07); box-shadow: 0 0 14px 4px rgba(255,215,0,.85); animation: selpulse 1.2s ease-in-out infinite; }
@keyframes selpulse { 0%,100% { box-shadow: 0 0 8px 2px rgba(255,215,0,.6); } 50% { box-shadow: 0 0 18px 6px rgba(255,215,0,1); } }
div[style*="border: 1.5px solid #2e7d32"] { animation: winglow 1.4s ease-in-out infinite; }
@keyframes winglow { 0%,100% { box-shadow: 0 0 0 rgba(76,175,80,0); } 50% { box-shadow: 0 0 12px 2px rgba(76,175,80,.9); } }
.fx-banner { position: fixed; top: 28%; left: 0; right: 0; text-align: center; z-index: 99999; pointer-events: none; animation: fxpop 2.8s ease-out forwards; }
.fx-title { display: inline-block; font-size: 44px; font-weight: 900; padding: 6px 26px; border-radius: 16px; background: rgba(0,0,0,.55); }
.fx-sub { font-size: 14px; color: #fff; margin-top: 6px; text-shadow: 0 1px 4px #000; }
.fx-t2 .fx-title { color: #e8f1ff; text-shadow: 0 0 14px #6aa9ff, 0 0 30px #6aa9ff; }
.fx-t3 .fx-title { color: #ffd54a; text-shadow: 0 0 14px #ff9800, 0 0 32px #ff5722; }
.fx-t4 .fx-title { color: #fff3b0; font-size: 56px; text-shadow: 0 0 18px #ffd700, 0 0 40px #ff3d00, 0 0 60px #ff3d00; animation: firebeat .5s ease-in-out infinite alternate; }
@keyframes fxpop { 0% { opacity: 0; transform: scale(.3); } 12% { opacity: 1; transform: scale(1.18); } 22% { transform: scale(1); } 80% { opacity: 1; } 100% { opacity: 0; transform: scale(1.06); } }
@keyframes firebeat { from { transform: scale(1); } to { transform: scale(1.08); } }
.mult-badge { display: inline-block; font-weight: 800; padding: 3px 12px; border-radius: 999px; background: linear-gradient(90deg,#ff9800,#ff5722); color: #fff; animation: badgepulse 1.3s ease-in-out infinite; }
@keyframes badgepulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.07); } }
"""

FELT_CSS = """
[data-testid="stAppViewContainer"] { background: radial-gradient(ellipse at 50% 15%, #1f6b3f 0%, #0f4a2a 55%, #082b19 100%) !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stMarkdownContainer"]:not([data-testid="stAlert"] *):not(button *), [data-testid="stCaptionContainer"], [data-testid="stHeading"] { color: #f6f1de !important; }
"""
ECO = bool(st.session_state.get("eco_mode", False))

FX2_CSS = """
/* ===== โล้ะ ===== */
.loh-stamp { text-align: center; margin: 8px 0 2px; }
.loh-stamp span { display: inline-block; font-size: 58px; font-weight: 900; color: #ff3b30; border: 5px solid #ff3b30; border-radius: 14px; padding: 0 24px; background: rgba(0,0,0,.4); text-shadow: 0 0 14px #ff3b30; transform: rotate(-6deg); animation: stamp .55s cubic-bezier(.2,1.5,.4,1) both; }
@keyframes stamp { 0% { transform: scale(4) rotate(-6deg); opacity: 0; } 60% { transform: scale(.92) rotate(-6deg); opacity: 1; } 100% { transform: scale(1) rotate(-6deg); } }
@keyframes fxshake { 0%,100% { transform: translate(0,0); } 15% { transform: translate(-6px,3px); } 30% { transform: translate(5px,-4px); } 45% { transform: translate(-4px,-2px); } 60% { transform: translate(4px,3px); } 75% { transform: translate(-2px,2px); } }
.loh-tease { text-align: center; font-size: 15px; font-weight: 700; color: #ffe082; margin: 4px 0 8px; }
.pc.flipc { animation: flipin .4s ease-out backwards; }
@keyframes flipin { 0% { transform: rotateY(90deg) scale(.6); opacity: 0; } 100% { transform: none; opacity: 1; } }
.mult-badge .mult-num { font-size: 1.25em; }
.mult-badge.m4 { background: linear-gradient(90deg,#ff5722,#d50000); }
.mult-badge.m8 { background: linear-gradient(90deg,#d50000,#7f0000); box-shadow: 0 0 14px 4px #ff6d00; }
.mult-badge.m8 .mult-num { font-size: 1.6em; text-shadow: 0 -2px 6px #ffea00, 0 -6px 12px #ff9100, 0 -10px 18px #ff3d00; animation: flicker .25s ease-in-out infinite alternate; }
@keyframes flicker { from { text-shadow: 0 -2px 6px #ffea00, 0 -6px 12px #ff9100, 0 -10px 18px #ff3d00; } to { text-shadow: 0 -4px 8px #ffea00, 0 -10px 16px #ff9100, 0 -16px 26px #ff3d00; } }
/* ===== แจกไพ่ ===== */
.pc.deal { animation: dealin .5s ease-out backwards; }
@keyframes dealin { from { transform: translateY(-150px) rotate(var(--r,0deg)) scale(.5); opacity: 0; } to { transform: none; opacity: 1; } }
/* ===== แถบผู้เล่น / โต๊ะ ===== */
.seats { display: flex; gap: 4px; margin: 4px 0 6px; }
.seat { flex: 1; min-width: 0; background: rgba(0,0,0,.28); border: 1.5px solid rgba(255,255,255,.18); border-radius: 10px; padding: 3px 3px 4px; text-align: center; }
.seat.turn { border-color: #ffd54a; animation: turnblink 1s ease-in-out infinite; }
@keyframes turnblink { 0%,100% { box-shadow: 0 0 0 rgba(255,213,74,0); } 50% { box-shadow: 0 0 10px 3px rgba(255,213,74,.95); } }
.sn { font-size: 10px; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mt { font-size: 10px; margin-top: 2px; color: #f6f1de; white-space: nowrap; }
.bar { height: 6px; border-radius: 4px; background: rgba(255,255,255,.2); overflow: hidden; margin-top: 3px; }
.bar i { display: block; height: 100%; border-radius: 4px; transition: width .6s; }
.cbs { min-height: 22px; margin-top: 3px; }
.cb { display: inline-block; width: 13px; height: 19px; margin: 0 1px; border-radius: 3px; border: 1px solid #fff; background: repeating-linear-gradient(45deg,#b71c1c 0 3px,#7f0000 3px 6px); }
/* ===== เปิดไพ่ / ผู้ชนะไม้ ===== */
.flip { display: inline-block; margin: 0 2px; animation: flipin .45s ease-out both; }
.crown { position: absolute; top: -17px; left: 50%; margin-left: -10px; font-size: 18px; opacity: 0; animation: crownup 1.2s ease-out both; }
@keyframes crownup { 0% { opacity: 0; transform: translateY(8px) scale(.4); } 40% { opacity: 1; transform: translateY(-6px) scale(1.25); } 100% { opacity: 1; transform: translateY(-2px) scale(1); } }
.plus-float { position: absolute; top: -2px; right: 6px; font-size: 14px; font-weight: 900; color: #ffd54a; text-shadow: 0 1px 3px #000; opacity: 0; animation: plusup 1.6s ease-out both; }
@keyframes plusup { 0% { opacity: 0; transform: translateY(8px); } 20% { opacity: 1; } 100% { opacity: 0; transform: translateY(-36px); } }
.sparkle::before, .sparkle::after { content: "✨"; position: absolute; font-size: 14px; animation: twinkle .9s ease-in-out 3; }
.sparkle::before { top: -6px; left: -2px; }
.sparkle::after { bottom: -6px; right: -2px; animation-delay: .3s; }
@keyframes twinkle { 0%,100% { opacity: .15; transform: scale(.6) rotate(0deg); } 50% { opacity: 1; transform: scale(1.3) rotate(40deg); } }
/* ===== เอฟเฟกต์ตามชุด ===== */
.fx-t3 .fx-title { animation: firebeat .5s ease-in-out infinite alternate; }
.fx-flash { position: fixed; inset: 0; z-index: 99998; pointer-events: none; opacity: 0; animation: flash .7s ease-out 2; }
.fx-flash.blue { background: radial-gradient(circle, #d6ebff 0%, #4a90ff 55%, rgba(74,144,255,.2) 100%); }
.fx-flash.white { background: #fff; }
@keyframes flash { 0%,100% { opacity: 0; } 12% { opacity: .85; } 28% { opacity: .1; } 42% { opacity: .7; } }
.fx-fire { position: fixed; inset: 0; z-index: 99997; pointer-events: none; opacity: 0; box-shadow: inset 0 0 36px 14px rgba(255,120,0,.9), inset 0 0 90px 30px rgba(255,40,0,.55); animation: firepulse .5s ease-in-out 6 alternate; }
@keyframes firepulse { from { opacity: .35; } to { opacity: 1; } }
.burst { position: fixed; top: 40%; left: 50%; z-index: 99998; pointer-events: none; }
.burst span { position: absolute; font-size: 26px; animation: burstout 1s ease-out both; }
@keyframes burstout { from { transform: translate(0,0) scale(.3); opacity: 1; } to { transform: translate(var(--dx),var(--dy)) scale(1.3); opacity: 0; } }
.coins span { position: fixed; top: -40px; font-size: 30px; z-index: 99998; pointer-events: none; animation: coinfall 2.6s linear both; }
@keyframes coinfall { to { transform: translateY(115vh) rotate(540deg); } }
/* ===== สรุปคะแนน ===== */
.srow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; background: rgba(0,0,0,.28); border-radius: 10px; padding: 6px 8px; margin: 4px 0; font-size: 13px; color: #f6f1de; }
.srow .nm { font-weight: 700; flex: 1 1 100px; min-width: 0; }
.srow .rs { font-weight: 800; }
.pos { color: #69f0ae; } .neg { color: #ff8a80; }
.arr { font-weight: 800; font-size: 12px; min-width: 32px; }
.arr.up { color: #69f0ae; } .arr.dn { color: #ff8a80; } .arr.eq { opacity: .6; }
.bd { font-size: 11px; font-weight: 700; padding: 1px 8px; border-radius: 999px; background: rgba(255,213,74,.2); border: 1px solid rgba(255,213,74,.5); }
.bd.fire { background: linear-gradient(90deg,#ff9800,#ff3d00); border: none; color: #fff; animation: badgepulse 1.3s ease-in-out infinite; }
.roll { display: inline-block; height: 1.4em; overflow: hidden; vertical-align: bottom; font-weight: 800; }
.roll-in { display: block; animation: rollup calc(var(--n) * .08s + .5s) steps(var(--n)) .6s both; }
.roll-in div { height: 1.4em; line-height: 1.4em; }
@keyframes rollup { to { transform: translateY(calc(var(--n) * -1.4em)); } }
.podium { display: flex; align-items: flex-end; justify-content: center; gap: 8px; margin: 12px 0 4px; }
.pod { flex: 1; max-width: 110px; text-align: center; color: #fff; font-size: 13px; font-weight: 700; }
.pod .blk { border-radius: 8px 8px 0 0; margin-top: 4px; padding-top: 4px; font-size: 24px; transform-origin: bottom; animation: podrise .8s ease-out both; }
.p1 .blk { height: 100px; background: linear-gradient(#ffd54a,#b8860b); }
.p2 .blk { height: 70px; background: linear-gradient(#e0e0e0,#8d8d8d); animation-delay: .3s; }
.p3 .blk { height: 50px; background: linear-gradient(#d7955b,#8a4b1b); animation-delay: .5s; }
@keyframes podrise { from { transform: scaleY(0); } to { transform: scaleY(1); } }
.conf span { position: fixed; top: -20px; width: 8px; height: 14px; z-index: 99998; pointer-events: none; animation: conffall 3.5s linear both; }
@keyframes conffall { to { transform: translateY(115vh) rotate(720deg); } }
/* ===== อีโมจิโต้ตอบ ===== */
.rx-layer { position: fixed; inset: 0; z-index: 99996; pointer-events: none; }
.rx { position: absolute; bottom: 12%; text-align: center; font-size: 38px; animation: rxup 3s ease-out forwards; }
.rx small { display: block; font-size: 11px; color: #fff; text-shadow: 0 1px 3px #000; }
@keyframes rxup { 0% { transform: translateY(0) scale(.5); opacity: 0; } 10% { opacity: 1; transform: translateY(-20px) scale(1.2); } 100% { transform: translateY(-55vh) scale(1); opacity: 0; } }
[class*="st-key-rx_"] button { font-size: 18px !important; padding: 2px 0 !important; }
"""

ECO_CSS = """
.fx-heavy { display: none !important; }
.pc.deal, .pc.flipc, .flip, .crown, .plus-float, .loh-stamp span, .podium .blk, .seat.turn, .mult-badge, .mult-badge .mult-num, .pc.sel, .fx-title, .fx-banner, .rx, .bd.fire, div[style*="border: 1.5px solid #2e7d32"] { animation: none !important; }
.crown { opacity: 1 !important; } .plus-float { display: none !important; }
.sparkle::before, .sparkle::after { display: none !important; }
.roll-in { transform: translateY(calc(var(--n) * -1.4em)) !important; }
"""
st.markdown("<style>" + FX_CSS + FX2_CSS + (FELT_CSS if FELT_THEME else "") + (ECO_CSS if ECO else "") + "</style>", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def img_data_uri(path):
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

# ---------------------------------------------------------
# 🇹🇭 แปลภาษายศหมากไทย & จัดการรูปภาพ
# ---------------------------------------------------------
RANK_THAI = {
    "Tee": "ตี่", "TEE": "ตี่", "tee": "ตี่",
    "Bin": "บิน", "BIN": "บิน", "bin": "บิน",
    "Chang": "ช้าง", "CHANG": "ช้าง", "chang": "ช้าง",
    "Ruea": "เรือ", "RUEA": "เรือ", "ruea": "เรือ", "Rua": "เรือ", "RUA": "เรือ",
    "Maa": "ม้า", "MAA": "ม้า", "maa": "ม้า", "Ma": "ม้า",
    "Pao": "เผ่า", "PAO": "เผ่า", "pao": "เผ่า", "Phao": "เผ่า", "PHAO": "เผ่า", "phao": "เผ่า",
    "Jut": "จุก", "JUT": "จุก", "jut": "จุก", "Juk": "จุก"
}

def get_rank_thai(rank):
    return RANK_THAI.get(str(rank).strip(), str(rank))

def card_label(card):
    symbol = "🔴" if str(card.color).strip().lower() in ["red", "r"] else "⚫"
    return f"{symbol}{get_rank_thai(card.rank)}"

def get_card_image_path(card):
    color = "red" if str(card.color).strip().lower() in ["red", "r"] else "black"
    raw_rank = str(card.rank).strip().lower()
    
    rank_map = {
        "ตี่": "tee", "tee": "tee",
        "บิน": "bin", "bin": "bin",
        "ช้าง": "chang", "chang": "chang",
        "เรือ": "ruea", "ruea": "ruea", "rua": "ruea",
        "ม้า": "maa", "maa": "maa", "ma": "maa",
        "เผ่า": "pao", "pao": "pao", "phao": "pao",
        "จุก": "jut", "jut": "jut", "juk": "jut"
    }
    mapped_rank = rank_map.get(raw_rank, raw_rank)
    
    path_jpg = f"images/{color}_{mapped_rank}.jpg"
    path_png = f"images/{color}_{mapped_rank}.png"
    
    if os.path.exists(path_jpg): return path_jpg
    elif os.path.exists(path_png): return path_png
    return None

# ---------------------------------------------------------
# 🏠 Global Room Manager & Session
# ---------------------------------------------------------
class GameServer:
    def __init__(self, room_id):
        self.room_id = room_id
        self.lock = threading.RLock()
        self.players = {}
        self.reset_game()

    def reset_game(self, keep_players=False):
        if not keep_players:
            self.players = {}
        self.game_id = time.time_ns()
        self.loh_players = []
        self.loh_hands = None
        self.loh_leader = None
        self.deal_prev_leader = None
        self.deal_first = True
        self.game_started = False
        self.round_num = 1
        self.scores = [0, 0, 0, 0]
        self.prev_leader = None
        self.hands = [[], [], [], []]
        self.leader = 0
        self.current_bidder = 0
        self.multiplier = 1
        self.tricks_won = [0, 0, 0, 0]
        self.bids = [0, 0, 0, 0]
        self.bids_entered = [False, False, False, False]
        self.phase = "lobby"
        self.current_plays = {}
        self.current_play_type = "Med"
        self.last_trick_summary = None
        self.played_pieces = []
        self.play_order = []
        self.exact_streak = [0, 0, 0, 0]
        self.reactions = []

class RoomManager:
    def __init__(self): self.rooms = {}
    def get_or_create_room(self, room_id):
        room_id = room_id.strip().upper()
        if room_id not in self.rooms: self.rooms[room_id] = GameServer(room_id)
        return self.rooms[room_id]

@st.cache_resource
def get_room_manager(): return RoomManager()
room_manager = get_room_manager()

if "my_id" not in st.session_state:
    st.session_state.my_id = f"user_{int(time.time() * 1000)}_{random.randint(100, 999)}"

if "current_room" not in st.session_state:
    st.session_state.current_room = None

if "selected_cards" not in st.session_state:
    st.session_state.selected_cards = []

my_id = st.session_state.my_id

# ---------------------------------------------------------
# 🎴 ระบบแสดงผลไพ่
# ---------------------------------------------------------
def render_pretty_card_board(hand, req_cnt=1, disabled=False, validator=None):
    sel = st.session_state.selected_cards
    sel = [i for i in sel if i < len(hand)]
    st.session_state.selected_cards = sel

    st.markdown("##### 🎴 ไพ่ในมือคุณ:")
    deal_key = (server.game_id, server.round_num, server.multiplier)
    deal_anim = server.phase == "bidding" and st.session_state.get("deal_fx") != deal_key
    if deal_anim: st.session_state.deal_fx = deal_key  # แจกอนิเมชันแค่ตอนเริ่มรอบ
    
    for row_start in range(0, len(hand), 4):
        cols = st.columns(4)
        for col_idx in range(4):
            card_idx = row_start + col_idx
            if card_idx < len(hand):
                card = hand[card_idx]
                is_sel = card_idx in sel
                img_path = get_card_image_path(card)
                can_click = not disabled and (is_sel or len(sel) < req_cnt)

                with cols[col_idx]:
                    if img_path:
                        cls = "pc sel" if is_sel else "pc"
                        sty = ""
                        if deal_anim:
                            cls += " deal"
                            sty = f' style="--r:{(card_idx - (len(hand) - 1) / 2) * 4:.1f}deg;animation-delay:{card_idx * 0.09:.2f}s"'
                        st.markdown(f'<img class="{cls}"{sty} src="{img_data_uri(img_path)}">', unsafe_allow_html=True)
                    
                    btn_label = f"✅ {card_label(card)}" if is_sel else card_label(card)
                    btn_type = "primary" if is_sel else "secondary"
                    
                    if st.button(btn_label, key=f"card_hand_{card_idx}", type=btn_type, disabled=not can_click, use_container_width=True):
                        if is_sel:
                            st.session_state.selected_cards.remove(card_idx)
                        else:
                            st.session_state.selected_cards.append(card_idx)
                        st.rerun()

    st.markdown("---")

    target_cnt = min(req_cnt, len(hand))
    valid_ok = True
    if validator and not disabled and len(sel) == target_cnt:
        valid_ok = validator([hand[i] for i in sel if i < len(hand)])
        if not valid_ok:
            st.warning("⚠️ ไพ่ที่เลือกไม่ตรงกับประเภทที่ประกาศ")
    is_ready = (len(sel) == target_cnt) and not disabled and valid_ok
    if st.button(
        f"🚀 ลงหมากที่เลือก ({len(sel)}/{target_cnt})", 
        type="primary", 
        disabled=not is_ready, 
        use_container_width=True,
        key="btn_confirm_play"
    ):
        chosen = [hand[i] for i in sel if i < len(hand)]
        st.session_state.selected_cards = []
        return chosen

    return None

# ---------------------------------------------------------
# 🚪 หน้าเลือกห้อง
# ---------------------------------------------------------
if not st.session_state.current_room:
    st.title("🎴 เกมตุ่ย Mobile")
    player_name = st.text_input("ชื่อผู้เล่น:", value=st.session_state.get("player_name", ""), key="name_input", placeholder="กรอกชื่อ...")

    if player_name.strip():
        st.session_state.player_name = player_name.strip()
        st.divider()
        c_code, c_btn = st.columns([2, 1])
        new_room_code = c_code.text_input("รหัสห้อง:", placeholder="เช่น ROOM1", label_visibility="collapsed").strip().upper()
        if c_btn.button("🚀 เข้าห้อง", type="primary", use_container_width=True):
            if new_room_code:
                st.session_state.current_room = new_room_code
                st.rerun()

        st.caption("หรือเลือกห้องที่มีอยู่:")
        for r_id, r_server in list(room_manager.rooms.items()):
            p_cnt = len([p for p in r_server.players.values() if p["role"].startswith("P")])
            c_info, c_join = st.columns([2, 1])
            c_info.write(f"🏠 **{r_id}** ({p_cnt}/4 คน)")
            if c_join.button(f"เข้า {r_id}", key=f"join_{r_id}", use_container_width=True):
                st.session_state.current_room = r_id
                st.rerun()
    else: st.info("👆 กรุณากรอกชื่อก่อนเริ่มเกม")
    st.stop()

# ---------------------------------------------------------
# 🎮 เข้าสู่ห้องเกม
# ---------------------------------------------------------
room_code = st.session_state.current_room
server = room_manager.get_or_create_room(room_code)
for _k, _v in (('play_order', []), ('exact_streak', [0, 0, 0, 0]), ('reactions', [])):
    if not hasattr(server, _k): setattr(server, _k, list(_v))  # ห้องเก่าที่ค้างในหน่วยความจำ

if my_id not in server.players:
    taken = {p["p_idx"] for p in server.players.values() if p["p_idx"] >= 0}
    free_seats = [i for i in range(4) if i not in taken]
    role, p_idx = (f"P{free_seats[0] + 1}", free_seats[0]) if free_seats else ("Spectator", -1)
    server.players[my_id] = {"name": st.session_state.player_name, "role": role, "p_idx": p_idx}

my_player_info = server.players[my_id]
my_role, my_name, my_p_idx = my_player_info["role"], my_player_info["name"], my_player_info["p_idx"]

# Header
c_head, c_reset, c_leave = st.columns([6, 1, 1])
c_head.markdown(f"🏠 **{room_code}** | **{my_name}** (`{my_role}`)")
if c_reset.button("🔄", help="รีเซ็ตเกม (เฉพาะ P1)", disabled=(my_role != "P1")):
    server.reset_game(keep_players=True)
    st.session_state.selected_cards = []
    st.rerun()
if c_leave.button("🚪", help="ออกจากห้อง"):
    server.players.pop(my_id, None)
    st.session_state.current_room = None
    st.session_state.selected_cards = []
    st.rerun()

def get_player_name(idx):
    p = next((p for p in server.players.values() if p["p_idx"] == idx), None)
    return p["name"] if p else f"P{idx+1}"

FX_TIERS = {
    "Tui": (1, "✨ ตุ่ย!"),
    "Sa-Hoo": (2, "ซาฮู้!"), "Sa-Jut": (2, "ซาจุก!"),
    "Pho-Jut": (3, "🔥 โฟจุก!"), "Pho-Hoo": (3, "🔥 โฟฮู้!"),
    "Five-Jut": (3, "🔥 ไฟฟ์จุก!"), "Five-Hoo": (3, "🔥 ไฟฟ์ฮู้!"),
    "Six-Hoo": (4, "👑 ซิกฮู้!!"),
}

def esc(t):
    return _html.escape(str(t))

def fmt_sc(v):
    return f"+{v}" if v > 0 else str(v)

def mult_badge_html(mult):
    if mult <= 1: return ""
    lv = "m8" if mult >= 8 else ("m4" if mult >= 4 else "m2")
    return f'<span class="mult-badge {lv}">🌀 โล้ะ! คะแนนคูณ <b class="mult-num">x{mult}</b></span>'

LOH_TEASES = [
    "ไพ่ทิ้งกองมาเอง 🤣", "โชคร้ายแต่ได้นำ!", "ตี่ บิน ช้าง หายไปไหนหมด 🕵️",
    "ไพ่เม็ดเล็กๆ น่ารักทั้งมือเลย 🥹", "ฟ้าลิขิตให้ไพ่ทิ้งกอง 🌩️",
    "โล้ะแล้วจ้า ทั้งโต๊ะได้ยิน 📢", "มือนี้เจ็บ แต่คะแนนคูณนะ 😈", "ไม่เป็นไร เปิดนำเองเลย 👑",
]

def loh_fx_html():
    rnd = random.Random(f"{server.game_id}-{server.round_num}-{server.multiplier}-{server.loh_players}")
    shake = "" if ECO else '<style>[data-testid="stAppViewContainer"]{animation:fxshake .6s ease-in-out}</style>'
    return f'{shake}<div class="loh-stamp"><span>โล้ะ!!</span></div><div class="loh-tease">{rnd.choice(LOH_TEASES)}</div>'

# เอฟเฟกต์พิเศษตามชุด (ปิดทั้งหมดเมื่อเปิดโหมดประหยัด)
FX_EXTRA = {"Sa-Hoo": "lightning", "Sa-Jut": "lightning", "Pho-Jut": "fire", "Pho-Hoo": "fire",
            "Five-Jut": "burst", "Five-Hoo": "burst", "Six-Hoo": "coins"}

def fx_extra_html(ptype, seq):
    kind = FX_EXTRA.get(ptype)
    if ECO or not kind: return ""
    if kind == "lightning": return '<div class="fx-heavy fx-flash blue"></div>'
    if kind == "fire": return '<div class="fx-heavy fx-fire"></div>'
    if kind == "burst":
        sp = "".join(f'<span style="--dx:{round(math.cos(k * math.pi / 6) * 130)}px;--dy:{round(math.sin(k * math.pi / 6) * 130)}px">✨</span>' for k in range(12))
        return f'<div class="fx-heavy fx-flash white"></div><div class="fx-heavy burst">{sp}</div>'
    rnd = random.Random(seq)
    coins = "".join(f'<span style="left:{rnd.randint(2, 95)}%;animation-delay:{rnd.random() * 1.6:.2f}s">🪙</span>' for _ in range(22))
    return f'<style>[data-testid="stAppViewContainer"]{{animation:fxshake .6s ease-in-out 2}}</style><div class="fx-heavy coins">{coins}</div>'

def play_trick_fx():
    """เล่นเอฟเฟกต์ของไม้ล่าสุดเพียงครั้งเดียวต่อผู้เล่น (กันเล่นซ้ำตอนหน้าจอรีเฟรชอัตโนมัติ)"""
    s = getattr(server, "last_trick_summary", None)
    if not s:
        return
    ss = st.session_state
    if ss.get("fx_seen") != s.get("seq"):
        ss.fx_seen = s.get("seq")
        ss.fx_html = None
        tier, label = FX_TIERS.get(s.get("play_type"), (0, ""))
        if tier == 1:
            st.toast(f"{label} P{s['winner_idx']+1} ({s['winner_name']}) กินไม้นี้")
        elif tier >= 2:
            who = f"P{s['winner_idx']+1} ({esc(s['winner_name'])}) กินไม้นี้"
            ss.fx_html = fx_extra_html(s.get("play_type"), s.get("seq")) + f'<div class="fx-banner fx-t{tier}"><div class="fx-title">{label}</div><div class="fx-sub">{who}</div></div>'
            ss.fx_until = time.time() + 5
    # คงป้ายไว้ ~5 วินาทีเพื่อไม่ให้ถูกตัดตอนรีเฟรช (HTML เดิม = อนิเมชันไม่เล่นซ้ำ)
    if ss.get("fx_html") and time.time() < ss.get("fx_until", 0):
        st.markdown(ss.fx_html, unsafe_allow_html=True)

def record_play(p_idx, cards):
    """ลงไพ่ + จดลำดับการลง (ใช้พลิกเปิดไล่ทีละคน)"""
    with server.lock:
        server.current_plays[p_idx] = cards
        if p_idx not in server.play_order: server.play_order.append(p_idx)

def trick_summary_html(s, title, mb=6):
    """กล่องสรุปไม้: ไพ่พลิกเปิดไล่ตามลำดับที่ลง, ผู้ชนะขยายนิดๆ + 👑 + ตัวเลข +N ลอยขึ้น"""
    w = s["winner_idx"]
    order = [i for i in s.get("order", []) if 0 <= i < 4]
    order += [i for i in range(4) if i not in order]
    end_d = len(order) * 0.45 + 0.2
    tiles = ""
    for i in range(4):
        cards = s["plays"].get(i, [])
        d0 = order.index(i) * 0.45
        cs = "".join(f'<span class="flip" style="animation-delay:{d0 + j * 0.12:.2f}s">{card_label(c)}</span>' for j, c in enumerate(cards)) or "-"
        if i == w:
            cls = "sparkle" if s.get("play_type") == "Tui" else ""
            extra = f'<span class="crown" style="animation-delay:{end_d:.2f}s">👑</span><span class="plus-float" style="animation-delay:{end_d:.2f}s">+{s["cards_won"]}</span>'
            tiles += f'<div class="{cls}" style="flex: 1; position: relative; z-index: 1; transform: scale(1.05); background: rgba(46, 125, 50, 0.15); border: 1.5px solid #2e7d32; border-radius: 8px; padding: 4px 2px; text-align: center; min-width: 0;">{extra}<div style="font-size: 10px; font-weight: bold; color: #4caf50; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">🏆 P{i+1}</div><div style="font-size: 12px; font-weight: bold; color: var(--text-color); margin-top: 1px;">{cs}</div></div>'
        else:
            tiles += f'<div style="flex: 1; background: var(--background-color); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 4px 2px; text-align: center; min-width: 0;"><div style="font-size: 10px; color: var(--text-color); opacity: 0.7; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">P{i+1}</div><div style="font-size: 12px; font-weight: bold; color: var(--text-color); margin-top: 1px;">{cs}</div></div>'
    return f'<div style="background: var(--secondary-background-color); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 10px; padding: 6px 8px; margin: 14px 0 {mb}px;"><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;"><span style="font-size: 11px; font-weight: bold; color: var(--text-color);">{title}</span><span style="font-size: 10px; font-weight: bold; background: rgba(46, 125, 50, 0.2); color: #4caf50; padding: 2px 8px; border-radius: 10px; border: 1px solid rgba(76, 175, 80, 0.3);">🎉 P{w+1} ({esc(s["winner_name"])}) กิน +{s["cards_won"]}</span></div><div style="display: flex; gap: 4px;">{tiles}</div></div>'

def seat_strip_html(show_table):
    """แถบผู้เล่น: มาตรวัดเรียก/กิน (เขียว=พอดี เหลือง=เกือบ แดง=เกิน) + หลังไพ่ที่ลงแล้วบนโต๊ะ + ไฟกะพริบคนที่ถึงตา"""
    cur = server.current_plays if show_table else {}
    turn = set()
    if server.phase == "bidding":
        turn = {server.current_bidder}
    elif server.phase == "playing":
        turn = {server.leader} if server.leader not in cur else {i for i in range(4) if i not in cur and server.hands[i]}
    tiles = ""
    for i in range(4):
        bid, won = server.bids[i], server.tricks_won[i]
        if server.bids_entered[i]:
            if won == bid: col = "#43a047"
            elif won > bid: col = "#e53935"
            elif bid - won == 1: col = "#fbc02d"
            else: col = "#78909c"
            pct = 100 if bid == 0 else min(100, round(won / bid * 100))
            meter = f'<div class="bar"><i style="width:{pct}%;background:{col}"></i></div><div class="mt" style="color:{col}">เรียก {bid} กินแล้ว {won}</div>'
        else:
            meter = '<div class="bar"><i style="width:0"></i></div><div class="mt">รอเรียกแต้ม</div>'
        cb = '<span class="cb"></span>' * len(cur.get(i, []))
        tag = ("⭐" if i == my_p_idx else "") + ("🎯" if i == server.leader else "")
        tiles += f'<div class="seat{" turn" if i in turn else ""}"><div class="sn">{tag}P{i+1}·{esc(get_player_name(i))}</div>{meter}<div class="cbs">{cb}</div></div>'
    return f'<div class="seats">{tiles}</div>'

REACTS = ["👏", "😭", "🤣", "😈", "🙏"]

def render_reaction_bar():
    cols = st.columns(len(REACTS))
    for k, e in enumerate(REACTS):
        if cols[k].button(e, key=f"rx_{k}", use_container_width=True):
            now = time.time()
            if now - st.session_state.get("rx_last", 0) > 1:  # กันกดรัว
                st.session_state.rx_last = now
                server.reactions.append({"id": time.time_ns(), "t": now, "emoji": e, "who": my_name})
                del server.reactions[:-20]

def render_reactions_layer():
    now = time.time()
    items = [r for r in server.reactions if now - r["t"] < 5]
    if items:
        h = "".join(f'<div class="rx" style="left:{8 + r["id"] % 76}%">{r["emoji"]}<small>{esc(r["who"])}</small></div>' for r in items)
        st.markdown(f'<div class="rx-layer">{h}</div>', unsafe_allow_html=True)

def roll_html(old, new):
    """ตัวเลขวิ่งทีละหน่วยจาก old -> new (CSS ล้วน)"""
    d = new - old
    if d == 0: return f'<b>{fmt_sc(new)}</b>'
    step = max(1, -(-abs(d) // 30))
    vals = list(range(old, new, step if d > 0 else -step)) + [new]
    items = "".join(f"<div>{fmt_sc(v)}</div>" for v in vals)
    return f'<span class="roll"><span class="roll-in" style="--n:{len(vals) - 1}">{items}</span></span>'

def score_rows_html(old_tot, new_tot, rnd_sc, exact, streak, old_rk, new_rk):
    rows = ""
    for i in range(4):
        dr = old_rk[i] - new_rk[i]
        arr = f'<span class="arr up">▲{dr}</span>' if dr > 0 else (f'<span class="arr dn">▼{-dr}</span>' if dr < 0 else '<span class="arr eq">–</span>')
        badges = ('<span class="bd">🎯 เป๊ะ!</span>' if exact[i] else "") + (f'<span class="bd fire">🔥 ไฟลุก x{streak[i]}</span>' if streak[i] >= 3 else "")
        rows += (f'<div class="srow">{arr}<span class="nm">P{i+1} ({esc(get_player_name(i))}) <small>เรียก {server.bids[i]}/กิน {server.tricks_won[i]}</small></span>'
                 f'<span class="rs {"pos" if rnd_sc[i] > 0 else "neg"}">{fmt_sc(rnd_sc[i])}</span>'
                 f'<span>รวม {roll_html(old_tot[i], new_tot[i])}</span>{badges}</div>')
    return rows

def podium_html(totals):
    order = sorted(range(4), key=lambda i: -totals[i])
    def pod(pos, medal, cls):
        p = order[pos]
        return f'<div class="pod {cls}"><div>{esc(get_player_name(p))}</div><div style="font-size:12px">{fmt_sc(totals[p])} แต้ม</div><div class="blk">{medal}</div></div>'
    p4 = order[3]
    return (f'<div class="podium">{pod(1, "🥈", "p2")}{pod(0, "🥇", "p1")}{pod(2, "🥉", "p3")}</div>'
            f'<div style="text-align:center;font-size:13px;color:#f6f1de">4️⃣ P{p4+1} ({esc(get_player_name(p4))}) {fmt_sc(totals[p4])} แต้ม</div>')

def confetti_html():
    rnd = random.Random(7)
    cols = ["#ff5252", "#ffd54a", "#69f0ae", "#40c4ff", "#e040fb", "#fff"]
    return '<div class="fx-heavy conf">' + "".join(f'<span style="left:{rnd.randint(1, 98)}%;background:{rnd.choice(cols)};animation-delay:{rnd.random() * 2:.2f}s"></span>' for _ in range(36)) + "</div>"

def run_deal(prev_leader, is_first_round, multiplier=1, loh_leader=None):
    """แจก 1 ครั้ง: ถ้ามีคนโล้ะ -> ค้างที่หน้า loh_reveal ให้ดูก่อน / ไม่มีใครโล้ะ -> เข้าสู่การบิด"""
    hands, loh, leader, mult, loh_leader = deal_step(prev_leader, is_first_round, multiplier, loh_leader)
    server.deal_prev_leader, server.deal_first = prev_leader, is_first_round
    server.multiplier, server.loh_leader = mult, loh_leader
    if loh:
        server.loh_hands, server.loh_players = hands, loh
        server.phase = "loh_reveal"
    else:
        server.loh_hands, server.loh_players = None, []
        server.hands, server.leader, server.current_bidder = hands, leader, leader
        server.phase = "bidding"

def hand_strip_html(hand):
    parts = []
    for k, c in enumerate(hand):
        p = get_card_image_path(c)
        if p:
            parts.append(f'<img class="pc flipc" style="width:11%;max-height:70px;animation-delay:{k * 0.2:.1f}s" src="{img_data_uri(p)}">')
        else:
            parts.append(f'<span style="padding:2px 6px;border:1px solid #888;border-radius:6px">{card_label(c)}</span>')
    return '<div style="display:flex;flex-wrap:wrap;gap:3px;justify-content:center;margin-bottom:6px">' + "".join(parts) + "</div>"

# ---------------------------------------------------------
# 🚪 PHASE 0: Lobby
# ---------------------------------------------------------
st.toggle("🔋 โหมดประหยัดเอฟเฟกต์ (มือถือเก่า)", key="eco_mode")
if server.phase != "lobby": render_reaction_bar()
render_reactions_layer()

if server.phase == "lobby":
    st.subheader("🏠 รอผู้เล่นครบ 4 คน")
    active_ps = [p for p in server.players.values() if p["role"].startswith("P")]
    c1, c2 = st.columns(2)
    cols = [c1, c2, c1, c2]
    for i in range(4):
        p_found = next((p for p in active_ps if p["p_idx"] == i), None)
        if p_found: cols[i].success(f"P{i+1}: {p_found['name']} ✅")
        else: cols[i].warning(f"P{i+1}: (ว่าง)")

    if len(active_ps) == 4 and my_role == "P1":
        if st.button("🚀 เริ่มเกมทันที", type="primary", use_container_width=True):
            run_deal(None, True)
            st.rerun()

# ---------------------------------------------------------
# 🌀 PHASE 0.5: มีคนโล้ะ (ค้างให้ดูก่อน แล้ว P1 กดแจกใหม่)
# ---------------------------------------------------------
elif server.phase == "loh_reveal":
    st.markdown(loh_fx_html(), unsafe_allow_html=True)
    st.markdown(mult_badge_html(server.multiplier), unsafe_allow_html=True)
    for p_i in server.loh_players:
        st.error(f"P{p_i+1} ({get_player_name(p_i)}) โล้ะ! ไม่มีตี่ / บิน / ช้างเลย")
        st.markdown(hand_strip_html(server.loh_hands[p_i]), unsafe_allow_html=True)
    st.caption("แจกใหม่ คะแนนรอบนี้คูณเพิ่ม และคนโล้ะจะเป็นผู้เปิดนำ (ถ้าแจกใหม่แล้วโล้ะอีก จะคูณต่อ)")
    if my_role == "P1":
        if st.button("🎴 แจกใหม่", type="primary", use_container_width=True):
            run_deal(server.deal_prev_leader, server.deal_first, server.multiplier, server.loh_leader)
            st.rerun()
    else:
        st.info("รอ P1 กดแจกใหม่...")

# ---------------------------------------------------------
# 🎲 PHASE 1: Bidding
# ---------------------------------------------------------
elif server.phase == "bidding":
    st.caption(f"🎲 รอบ {server.round_num}/{TOTAL_ROUNDS} (x{server.multiplier}) | Leader บิด: **P{server.leader+1}**")
    if server.multiplier > 1: st.markdown(mult_badge_html(server.multiplier), unsafe_allow_html=True)

    st.markdown(seat_strip_html(False), unsafe_allow_html=True)
    bid_order = [(server.leader + i) % 4 for i in range(4)]
    order_idx = bid_order.index(server.current_bidder) if server.current_bidder in bid_order else 0

    if my_role != "Spectator" and my_p_idx == server.current_bidder and not server.bids_entered[my_p_idx]:
        st.write(f"👉 **ถึงตาคุณ ({my_name}) บิดแต้ม:**")
        if order_idx == 3:
            prev_sum = sum(server.bids[p] for p in bid_order[:3])
            forbidden_bid = 8 - prev_sum
            valid_bids = [b for b in range(9) if b != forbidden_bid] if 0 <= forbidden_bid <= 8 else list(range(9))
            if 0 <= forbidden_bid <= 8: st.warning(f"⚠️ ห้ามบิด {forbidden_bid} แต้ม")
        else: valid_bids = list(range(9))

        cb1, cb2 = st.columns([2, 1])
        bid_val = cb1.selectbox("แต้ม:", valid_bids, index=min(2, len(valid_bids)-1), label_visibility="collapsed")
        if cb2.button("✅ เรียกแต้ม", type="primary", use_container_width=True):
            server.bids[my_p_idx] = bid_val
            server.bids_entered[my_p_idx] = True
            server.current_bidder = (server.current_bidder + 1) % 4
            st.rerun()

    with st.expander("📊 ดูการบิดแต้มเพื่อน", expanded=False):
        for idx, p_idx in enumerate(bid_order):
            p_n = get_player_name(p_idx)
            status = f"{server.bids[p_idx]} แต้ม" if server.bids_entered[p_idx] else ("กำลังบิด..." if p_idx == server.current_bidder else "รอคิว")
            st.write(f"• P{p_idx+1} ({p_n}): {status}")

    if my_role != "Spectator":
        render_pretty_card_board(server.hands[my_p_idx], req_cnt=1, disabled=True)

    if all(server.bids_entered):
        server.phase = "playing"
        st.rerun()

# ---------------------------------------------------------
# 🃏 PHASE 2: Playing
# ---------------------------------------------------------
elif server.phase == "playing":
    
    resolved_now = False
    with server.lock:
        # ⚡ [AUTO-PLAY 1] สำหรับคนตาม (Followers): ถ้า Leader เปิดหมากแล้ว คนไหนมีไพ่เหลือ <= จำนวนที่ต้องลง -> ดึงไพ่ลงโต๊ะให้อัตโนมัติทันที
        if server.leader in server.current_plays:
            req_cnt = len(server.current_plays[server.leader])
            for p_idx in range(4):
                if p_idx not in server.current_plays:
                    p_hand = server.hands[p_idx]
                    if 0 < len(p_hand) <= req_cnt:
                        record_play(p_idx, list(p_hand))

        # ⚡ [AUTO-PLAY 2] เมื่อไพ่ลงครบ 4 คน -> คำนวณผลชนะ/แพ้ทันที
        if len(server.current_plays) == 4:
            for p_idx, chosen_list in server.current_plays.items():
                for target_p in chosen_list:
                    server.played_pieces.append(target_p)
                    for hand_p in list(server.hands[p_idx]):
                        if hand_p.key() == target_p.key():
                            server.hands[p_idx].remove(hand_p)
                            break

            winner = resolve_trick(server.current_plays, server.current_play_type, server.leader)
            w_name = get_player_name(winner)
            cards_won_count = len(server.current_plays[winner])
            server.tricks_won[winner] += cards_won_count

            server.last_trick_summary = {
                "plays": server.current_plays,
                "winner_idx": winner,
                "winner_name": w_name,
                "cards_won": cards_won_count,
                "play_type": server.current_play_type,
                "order": list(server.play_order),
                "seq": time.time_ns()
            }

            server.leader = winner
            server.current_plays = {}
            server.play_order = []
            resolved_now = True
    if resolved_now:
        st.rerun()

    st.caption(f"🃏 รอบ {server.round_num}/{TOTAL_ROUNDS} | Leader: **P{server.leader+1} ({get_player_name(server.leader)})**")
    if server.multiplier > 1: st.markdown(mult_badge_html(server.multiplier), unsafe_allow_html=True)

    st.markdown(seat_strip_html(True), unsafe_allow_html=True)

    # 📜 สรุปไม้ล่าสุด
    if getattr(server, 'last_trick_summary', None):
        st.markdown(trick_summary_html(server.last_trick_summary, "📜 ไม้ล่าสุด", 6), unsafe_allow_html=True)
        play_trick_fx()

    with st.expander("📊 ดูแต้ม / สถานะการกินรวม", expanded=False):
        for i in range(4):
            st.write(f"• **P{i+1} ({get_player_name(i)})**: เรียก {server.bids[i]} | กินแล้ว {server.tricks_won[i]} แต้ม")

    # ส่วนการเล่นหมาก
    if any(len(h) > 0 for h in server.hands):
        if my_role != "Spectator":
            my_hand = server.hands[my_p_idx]

            # Leader เลือกเปิดหมาก
            if my_p_idx == server.leader and my_p_idx not in server.current_plays:
                st.write("🔥 **ถึงตาคุณเปิดหมากนำ:**")
                play_opts = ["เม็ด (1 ใบ)"]
                if can_play_tui(my_hand): play_opts.append("ตุ่ย (2)")
                if can_play_sahoo(my_hand): play_opts.append("ซาฮู้ (3)")
                if get_available_sa_juk(my_hand): play_opts.append("ซาจุก (3)")
                if get_available_pho_juk(my_hand): play_opts.append("โฟจุก (4)")
                if get_available_five_juk(my_hand): play_opts.append("ไฟฟ์จุก (5)")
                if get_available_pho_hoo(my_hand): play_opts.append("โฟฮู้ (4)")
                if get_available_five_hoo(my_hand): play_opts.append("ไฟฟ์ฮู้ (5)")
                if get_available_six_hoo(my_hand): play_opts.append("ซิกฮู้ (6)")

                play_type = st.radio("ประเภท:", play_opts, horizontal=True, label_visibility="collapsed")
                
                req_cnt = 1
                if "2" in play_type: req_cnt = 2
                elif "3" in play_type: req_cnt = 3
                elif "4" in play_type: req_cnt = 4
                elif "5" in play_type: req_cnt = 5
                elif "6" in play_type: req_cnt = 6

                ptype_map = {"เม็ด": "Med", "ตุ่ย": "Tui", "ซาฮู้": "Sa-Hoo", "ซาจุก": "Sa-Jut", "โฟจุก": "Pho-Jut", "โฟฮู้": "Pho-Hoo", "ไฟฟ์ฮู้": "Five-Hoo", "ไฟฟ์จุก": "Five-Jut", "ซิกฮู้": "Six-Hoo"}
                matched_type = "Med"
                for k, v in ptype_map.items():
                    if k in play_type: matched_type = v; break

                # ⚡ [AUTO-SELECT 3] ถ้าไพ่ในมือ Leader เหลือ <= req_cnt ให้ติ๊กเลือกไพ่ทั้งหมดให้อัตโนมัติทันที
                if len(my_hand) <= req_cnt:
                    st.session_state.selected_cards = list(range(len(my_hand)))

                played_cards = render_pretty_card_board(
                    my_hand, req_cnt=req_cnt, disabled=False,
                    validator=lambda cs, t=matched_type: validate_play(t, cs)
                )
                if played_cards:
                    record_play(server.leader, played_cards)
                    server.current_play_type = matched_type
                    st.rerun()

            # Follower ลงตาม
            elif server.leader in server.current_plays and my_p_idx not in server.current_plays:
                curr_req = min(len(server.current_plays[server.leader]), len(my_hand))
                st.write(f"🃏 **ลงหมากตาม (เลือก {curr_req} ใบ):**")
                
                # ⚡ [AUTO-SELECT 4] ถ้าไพ่ในมือ Follower เหลือ <= curr_req ให้ติ๊กเลือกไพ่อัตโนมัติ
                if len(my_hand) <= curr_req:
                    st.session_state.selected_cards = list(range(len(my_hand)))

                played_cards = render_pretty_card_board(my_hand, req_cnt=curr_req, disabled=False)
                if played_cards:
                    record_play(my_p_idx, played_cards)
                    st.rerun()

            elif my_p_idx in server.current_plays:
                st.success("✅ คุณลงหมากเรียบร้อย 🔒 (รอคนอื่นลงให้ครบ...)")
                render_pretty_card_board(my_hand, req_cnt=1, disabled=True)
            else:
                st.info(f"⏳ รอ P{server.leader+1} ({get_player_name(server.leader)}) เปิดหมาก...")
                render_pretty_card_board(my_hand, req_cnt=1, disabled=True)

    else:
        server.phase = "round_summary"
        st.rerun()

# ---------------------------------------------------------
# 🏁 PHASE 3: Round Summary (สรุปรอบ + รวมคะแนนสะสม)
# ---------------------------------------------------------
elif server.phase == "round_summary":
    st.subheader(f"🏁 สรุปรอบที่ {server.round_num}")

    # 1. ⚡ ผลลัพธ์ขาสุดท้าย (Auto Play)
    if getattr(server, 'last_trick_summary', None):
        st.markdown(trick_summary_html(server.last_trick_summary, "⚡ ผลลัพธ์ขาสุดท้าย (Auto Play)", 12), unsafe_allow_html=True)
        play_trick_fx()

    # 2. 📊 คะแนนรอบนี้ + คะแนนสะสม (ตัวเลขวิ่ง, ลูกศรอันดับ, ป้ายเป๊ะ/ไฟลุก)
    st.markdown("### 📊 ตารางสรุปคะแนน")
    round_results = []
    for i in range(4):
        bid, won = server.bids[i], server.tricks_won[i]
        base = 3 if (bid == 0 and won == 0) else ((bid + 5) if bid == won else -abs(won - bid))
        round_results.append(base * server.multiplier)
    old_tot = list(server.scores)
    new_tot = [old_tot[i] + round_results[i] for i in range(4)]
    rk = lambda arr, i: 1 + sum(1 for t in arr if t > arr[i])
    exact_now = [server.bids[i] == server.tricks_won[i] for i in range(4)]
    streak_now = [(server.exact_streak[i] + 1) if exact_now[i] else 0 for i in range(4)]
    st.markdown(score_rows_html(old_tot, new_tot, round_results, exact_now, streak_now,
                                [rk(old_tot, i) for i in range(4)], [rk(new_tot, i) for i in range(4)]), unsafe_allow_html=True)

    st.markdown("---")

    is_final_round = server.round_num >= TOTAL_ROUNDS
    # 🎈 ฉลอง (ครั้งเดียวต่อรอบต่อผู้เล่น): เรียกตรงเป๊ะ = ลูกโป่ง / จบเกม = พลุกระดาษ
    fx_key = (server.game_id, server.round_num)
    if st.session_state.get("round_fx") != fx_key:
        st.session_state.round_fx = fx_key
        exact = my_role != "Spectator" and exact_now[my_p_idx]
        if is_final_round:
            st.session_state.confetti_until = time.time() + 6
        elif exact:
            st.balloons()
    if is_final_round and not ECO and time.time() < st.session_state.get("confetti_until", 0):
        st.markdown(confetti_html(), unsafe_allow_html=True)

    if is_final_round:
        st.markdown("### 🏆 สรุปผลการแข่งขัน")
        st.markdown(podium_html(new_tot), unsafe_allow_html=True)
        if my_role == "P1":
            if st.button("🎮 เล่นใหม่ (ผู้เล่นชุดเดิม)", type="primary", use_container_width=True):
                server.reset_game(keep_players=True)
                st.session_state.selected_cards = []
                st.rerun()
        else: st.info("รอ P1 กดเล่นใหม่...")
    elif my_role == "P1":
        if st.button("➡️ ไปต่อรอบถัดไป", type="primary", use_container_width=True):
            for i in range(4): server.scores[i] += round_results[i]
            server.exact_streak = list(streak_now)
            server.prev_leader = server.leader
            server.round_num += 1
            server.tricks_won, server.bids, server.bids_entered = [0]*4, [0]*4, [False]*4
            server.current_plays, server.last_trick_summary, server.played_pieces = {}, None, []
            server.play_order = []
            st.session_state.selected_cards = []
            run_deal(server.prev_leader, False)
            st.rerun()
    else: st.info("รอ P1 กดไปต่อรอบถัดไป...")