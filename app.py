import streamlit as st
import random
import time
import os
import json
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
from tui_engine import (
    deal_round, can_play_tui, can_play_sahoo, 
    get_available_tuis, get_available_sahoos, resolve_trick,
    RANK_ORDER, RANK_COUNTS
)

# ---------------------------------------------------------
# 📱 ตั้งค่าหน้าจอ & CSS สำหรับมือถือ (Ultra Compact)
# ---------------------------------------------------------
st.set_page_config(
    page_title="เกมตุ่ย Mobile", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# รีเฟรชอัตโนมัติทุก 2 วินาที
st_autorefresh(interval=2000, key="datarefresh")

st.markdown("""
<style>
    .block-container { padding-top: 0.5rem; padding-bottom: 0.5rem; padding-left: 0.3rem; padding-right: 0.3rem; }
    .stButton > button { border-radius: 8px; padding: 2px 5px !important; font-size: 13px !important; font-weight: bold; width: 100%; }
    div[data-testid="stSidebarNav"] { display: none; }
    div[data-testid="stHorizontalBlock"] { gap: 0.2rem; }
    .stAlert { padding: 4px 8px !important; margin-bottom: 4px !important; }
    hr { margin: 4px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🇹🇭 แปลภาษายศหมากไทย (เรือ, เผ่า, ม้า, ช้าง, บิน, ตี่, จุก)
# ---------------------------------------------------------
RANK_THAI = {
    "Tee": "ตี่", "TEE": "ตี่", "tee": "ตี่",
    "Bin": "บิน", "BIN": "บิน", "bin": "บิน",
    "Chang": "ช้าง", "CHANG": "ช้าง", "chang": "ช้าง",
    "Ruea": "เรือ", "RUEA": "เรือ", "ruea": "เรือ", "Rua": "เรือ", "RUA": "เรือ",
    "Maa": "ม้า", "MAA": "ม้า", "maa": "ม้า", "Ma": "ม้า",
    "Pao": "เผ่า", "PAO": "เผ่า", "pao": "เผ่า",
    "Jut": "จุก", "JUT": "จุก", "jut": "จุก", "Juk": "จุก"
}

def get_rank_thai(rank):
    return RANK_THAI.get(str(rank).strip(), str(rank))

def card_label(card):
    symbol = "🔴" if str(card.color).strip().lower() in ["red", "r"] else "⚫"
    return f"{symbol}{get_rank_thai(card.rank)}"

# ---------------------------------------------------------
# 🧠 ฟังก์ชันตรวจสอบชุดหมาก
# ---------------------------------------------------------
def is_juk(piece): return get_rank_thai(piece.rank) == "จุก"

def get_available_sa_juk(hand):
    red_juks = [p for p in hand if is_juk(p) and str(p.color).lower() in ["red", "r"]]
    black_juks = [p for p in hand if is_juk(p) and str(p.color).lower() in ["black", "b"]]
    res = []
    if len(red_juks) >= 3: res.append(red_juks[:3])
    if len(black_juks) >= 3: res.append(black_juks[:3])
    return res

def get_available_pho_juk(hand):
    red_juks = [p for p in hand if is_juk(p) and str(p.color).lower() in ["red", "r"]]
    black_juks = [p for p in hand if is_juk(p) and str(p.color).lower() in ["black", "b"]]
    res = []
    if len(red_juks) >= 4: res.append(red_juks[:4])
    if len(black_juks) >= 4: res.append(black_juks[:4])
    return res

def get_available_pho_hoo(hand):
    sahoos = get_available_sahoos(hand)
    res = []
    for s_type, s_cards in sahoos:
        color = s_cards[0].color
        extra_candidates = [p for p in hand if p not in s_cards and p.color == color and get_rank_thai(p.rank) in ["บิน", "ช้าง"]]
        for extra in extra_candidates:
            extra_th = get_rank_thai(extra.rank)
            res.append((f"{s_type}+{extra_th}", s_cards + [extra]))
    return res

def get_available_five_hoo(hand):
    sahoos = get_available_sahoos(hand)
    res = []
    for s_type, s_cards in sahoos:
        color = s_cards[0].color
        bins = [p for p in hand if p not in s_cards and p.color == color and get_rank_thai(p.rank) == "บิน"]
        changs = [p for p in hand if p not in s_cards and p.color == color and get_rank_thai(p.rank) == "ช้าง"]
        if bins and changs:
            res.append((f"{s_type}+บิน+ช้าง", s_cards + [bins[0], changs[0]]))
    return res

# ---------------------------------------------------------
# 🛠️ สร้าง Streamlit Custom Component
# ---------------------------------------------------------
COMPONENT_DIR = os.path.join(os.path.dirname(__file__), "tui_card_component")
os.makedirs(COMPONENT_DIR, exist_ok=True)

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://cdn.jsdelivr.net/npm/streamlit-component-lib@1.4.0/dist/streamlit-component-lib.js"></script>
<style>
    * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; user-select: none; -webkit-user-select: none; }
    body { margin: 0; padding: 2px; background: transparent; }

    .drop-zone {
        border: 2px dashed #1976D2;
        border-radius: 10px;
        padding: 6px;
        min-height: 55px;
        background: #F0F7FF;
        margin-bottom: 8px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: all 0.2s;
    }
    .drop-zone.hover { border-color: #2E7D32; background: #E8F5E9; }

    .drop-zone-title {
        font-size: 11px;
        color: #1565C0;
        font-weight: bold;
        margin-bottom: 3px;
    }

    .drop-zone-cards {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        justify-content: center;
        width: 100%;
    }

    .empty-hint {
        font-size: 12px;
        color: #78909C;
    }

    /* 4 ใบต่อ 1 แถว */
    .card-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 6px;
        margin-bottom: 8px;
    }

    .card-item {
        background: #FFFFFF;
        border: 2px solid #CFD8DC;
        border-radius: 8px;
        padding: 8px 2px;
        text-align: center;
        font-size: 13px;
        font-weight: bold;
        cursor: grab;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        touch-action: none;
        transition: transform 0.15s, border-color 0.15s;
    }
    .card-item.red { color: #D32F2F; border-color: #EF9A9A; background-color: #FFEBEE; }
    .card-item.black { color: #212121; border-color: #B0BEC5; background-color: #ECEFF1; }
    .card-item.dragging { opacity: 0.4; }

    .drop-card {
        padding: 5px 8px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 1px 3px rgba(0,0,0,0.15);
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .drop-card.red { color: #D32F2F; border: 1.5px solid #EF9A9A; background-color: #FFEBEE; }
    .drop-card.black { color: #212121; border: 1.5px solid #B0BEC5; background-color: #ECEFF1; }
    .drop-card .remove-btn {
        font-size: 11px;
        background: rgba(0,0,0,0.1);
        border-radius: 50%;
        width: 14px;
        height: 14px;
        display: inline-flex;
        justify-content: center;
        align-items: center;
        margin-left: 2px;
    }

    .play-btn {
        width: 100%;
        padding: 9px;
        background-color: #2E7D32;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        font-size: 14px;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }
    .play-btn:disabled { background-color: #B0BEC5; cursor: not-allowed; box-shadow: none; }
</style>
</head>
<body>

<div id="drop-zone" class="drop-zone">
    <div class="drop-zone-title" id="drop-title">🎯 ช่องลงหมาก</div>
    <div id="drop-cards-container" class="drop-zone-cards"></div>
    <div id="empty-hint" class="empty-hint">ลากไพ่มาวางที่นี่ หรือ แตะเลือกไพ่</div>
</div>

<div id="card-grid" class="card-grid"></div>

<button id="submit-btn" class="play-btn" disabled onclick="submitPlay()">🚀 ลงหมากที่เลือก</button>

<script>
    let cardsData = [];
    let reqCount = 1;
    let isDisabled = false;

    let inDropZone = [];
    let inHand = [];

    function onRender(event) {
        const args = event.detail.args;
        cardsData = args.cards || [];
        reqCount = args.req_cnt || 1;
        isDisabled = args.disabled || false;

        inDropZone = [];
        inHand = cardsData.map((_, i) => i);

        render();
    }

    function updateHeight() {
        if (window.Streamlit) {
            window.Streamlit.setFrameHeight(document.body.scrollHeight + 10);
        }
    }

    function render() {
        document.getElementById('drop-title').innerText = `🎯 ช่องลงหมาก (${inDropZone.length}/${reqCount} ใบ)`;
        
        const dropContainer = document.getElementById('drop-cards-container');
        const emptyHint = document.getElementById('empty-hint');
        dropContainer.innerHTML = '';

        if (inDropZone.length === 0) {
            emptyHint.style.display = 'block';
        } else {
            emptyHint.style.display = 'none';
            inDropZone.forEach((cardIdx) => {
                const card = cardsData[cardIdx];
                if (!card) return;
                const el = document.createElement('div');
                el.className = `drop-card ${card.is_red ? 'red' : 'black'}`;
                el.innerHTML = `<span>${card.symbol}${card.label}</span><span class="remove-btn">✕</span>`;
                el.onclick = () => removeFromDropZone(cardIdx);
                dropContainer.appendChild(el);
            });
        }

        const grid = document.getElementById('card-grid');
        grid.innerHTML = '';

        inHand.forEach((cardIdx, handPosition) => {
            const card = cardsData[cardIdx];
            if (!card) return;

            const el = document.createElement('div');
            el.className = `card-item ${card.is_red ? 'red' : 'black'}`;
            el.setAttribute('draggable', isDisabled ? 'false' : 'true');
            el.dataset.cardIdx = cardIdx;
            el.dataset.handPos = handPosition;
            el.innerHTML = `<div>${card.symbol}${card.label}</div>`;

            el.onclick = () => {
                if (isDisabled) return;
                if (inDropZone.length < reqCount) {
                    moveToDropZone(cardIdx);
                } else if (reqCount === 1) {
                    inHand.push(...inDropZone);
                    inDropZone = [cardIdx];
                    inHand = inHand.filter(i => i !== cardIdx);
                    render();
                }
            };

            el.ondragstart = (e) => {
                e.dataTransfer.setData('text/plain', JSON.stringify({cardIdx, handPosition}));
                el.classList.add('dragging');
            };
            el.ondragend = () => el.classList.remove('dragging');

            el.ondragover = (e) => e.preventDefault();
            el.ondrop = (e) => {
                e.preventDefault();
                e.stopPropagation();
                const dataRaw = e.dataTransfer.getData('text/plain');
                if (!dataRaw) return;
                try {
                    const data = JSON.parse(dataRaw);
                    const srcHandPos = data.handPosition;
                    if (srcHandPos !== undefined && srcHandPos !== handPosition) {
                        const temp = inHand[srcHandPos];
                        inHand[srcHandPos] = inHand[handPosition];
                        inHand[handPosition] = temp;
                        render();
                    }
                } catch(err){}
            };

            grid.appendChild(el);
        });

        const dz = document.getElementById('drop-zone');
        dz.ondragover = (e) => { e.preventDefault(); if (!isDisabled) dz.classList.add('hover'); };
        dz.ondragleave = () => dz.classList.remove('hover');
        dz.ondrop = (e) => {
            e.preventDefault();
            dz.classList.remove('hover');
            if (isDisabled) return;
            const dataRaw = e.dataTransfer.getData('text/plain');
            if (!dataRaw) return;
            try {
                const data = JSON.parse(dataRaw);
                if (data.cardIdx !== undefined) moveToDropZone(data.cardIdx);
            } catch(err){}
        };

        setupTouchEvents();

        const btn = document.getElementById('submit-btn');
        btn.disabled = isDisabled || (inDropZone.length !== reqCount);
        btn.innerText = `🚀 ลงหมากที่เลือก (${inDropZone.length}/${reqCount})`;

        setTimeout(updateHeight, 30);
    }

    function moveToDropZone(cardIdx) {
        if (inDropZone.includes(cardIdx)) return;
        if (inDropZone.length < reqCount) {
            inDropZone.push(cardIdx);
            inHand = inHand.filter(i => i !== cardIdx);
            render();
        }
    }

    function removeFromDropZone(cardIdx) {
        inDropZone = inDropZone.filter(i => i !== cardIdx);
        if (!inHand.includes(cardIdx)) inHand.push(cardIdx);
        render();
    }

    let touchSrcIdx = null;
    let touchSrcHandPos = null;

    function setupTouchEvents() {
        const grid = document.getElementById('card-grid');
        grid.ontouchstart = (e) => {
            const cardEl = e.target.closest('.card-item');
            if (cardEl) {
                touchSrcIdx = parseInt(cardEl.dataset.cardIdx);
                touchSrcHandPos = parseInt(cardEl.dataset.handPos);
            }
        };

        grid.ontouchend = (e) => {
            if (touchSrcIdx !== null) {
                const touch = e.changedTouches[0];
                const targetEl = document.elementFromPoint(touch.clientX, touch.clientY);
                
                if (targetEl && targetEl.closest('#drop-zone')) {
                    if (!isDisabled) moveToDropZone(touchSrcIdx);
                } 
                else if (targetEl && targetEl.closest('.card-item')) {
                    const targetCardEl = targetEl.closest('.card-item');
                    const targetPos = parseInt(targetCardEl.dataset.handPos);
                    if (!isNaN(targetPos) && targetPos !== touchSrcHandPos) {
                        const temp = inHand[touchSrcHandPos];
                        inHand[touchSrcHandPos] = inHand[targetPos];
                        inHand[targetPos] = temp;
                        render();
                    }
                }
                touchSrcIdx = null;
                touchSrcHandPos = null;
            }
        };
    }

    function submitPlay() {
        if (inDropZone.length === reqCount && !isDisabled && window.Streamlit) {
            window.Streamlit.setComponentValue(inDropZone);
        }
    }

    if (window.Streamlit) {
        window.Streamlit.events.addEventListener(window.Streamlit.RENDER_EVENT, onRender);
        window.Streamlit.setComponentReady();
    }
</script>
</body>
</html>
"""

with open(os.path.join(COMPONENT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(INDEX_HTML)

tui_card_selector = components.declare_component("tui_card_selector", path=COMPONENT_DIR)

# ---------------------------------------------------------
# 🏠 Global Room Manager & Session
# ---------------------------------------------------------
class GameServer:
    def __init__(self, room_id):
        self.room_id = room_id
        self.reset_game()

    def reset_game(self):
        self.players = {}
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

my_id = st.session_state.my_id

def render_hand_selector(hand, req_cnt=1, disabled=False, key_suffix=""):
    cards_payload = []
    for idx, c in enumerate(hand):
        cards_payload.append({
            "idx": idx,
            "label": get_rank_thai(c.rank),
            "symbol": "🔴" if str(c.color).strip().lower() in ["red", "r"] else "⚫",
            "is_red": str(c.color).strip().lower() in ["red", "r"]
        })

    key = f"tui_select_{my_id}_{len(hand)}_{req_cnt}_{key_suffix}"
    return tui_card_selector(cards=cards_payload, req_cnt=req_cnt, disabled=disabled, key=key)

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

if my_id not in server.players:
    assigned_p_index = len([p for p in server.players.values() if p["role"].startswith("P")])
    role, p_idx = (f"P{assigned_p_index + 1}", assigned_p_index) if assigned_p_index < 4 else ("Spectator", -1)
    server.players[my_id] = {"name": st.session_state.player_name, "role": role, "p_idx": p_idx}

my_player_info = server.players[my_id]
my_role, my_name, my_p_idx = my_player_info["role"], my_player_info["name"], my_player_info["p_idx"]

# Header
c_head, c_reset, c_leave = st.columns([6, 1, 1])
c_head.markdown(f"🏠 **{room_code}** | **{my_name}** (`{my_role}`)")
if c_reset.button("🔄", help="รีเซ็ตห้อง"):
    server.reset_game()
    st.rerun()
if c_leave.button("🚪", help="ออกจากห้อง"):
    del server.players[my_id]
    st.session_state.current_room = None
    st.rerun()

def get_player_name(idx):
    p = next((p for p in server.players.values() if p["p_idx"] == idx), None)
    return p["name"] if p else f"P{idx+1}"

# ---------------------------------------------------------
# 🚪 PHASE 0: Lobby
# ---------------------------------------------------------
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
            hands, leader, mult = deal_round(None, is_first_round=True)
            server.hands, server.leader, server.current_bidder, server.multiplier = hands, leader, leader, mult
            server.phase = "bidding"
            st.rerun()

# ---------------------------------------------------------
# 🎲 PHASE 1: Bidding
# ---------------------------------------------------------
elif server.phase == "bidding":
    st.caption(f"🎲 รอบ {server.round_num}/15 (x{server.multiplier}) | Leader บิด: **P{server.leader+1}**")

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
        st.caption("🎴 ไพ่ในมือคุณ:")
        render_hand_selector(server.hands[my_p_idx], req_cnt=1, disabled=True, key_suffix="bid")

    if all(server.bids_entered):
        server.phase = "playing"
        st.rerun()

# ---------------------------------------------------------
# 🃏 PHASE 2: Playing
# ---------------------------------------------------------
elif server.phase == "playing":
    # ประมวลผลเมื่อลงหมากครบ 4 คน
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
            "cards_won": cards_won_count
        }

        server.leader = winner
        server.current_plays = {}
        st.rerun()

    st.caption(f"🃏 รอบ {server.round_num}/15 | Leader: **P{server.leader+1} ({get_player_name(server.leader)})**")

    # 📜 สรุปไม้ล่าสุด (ใครลงอะไร / ใครได้กิน)
    if getattr(server, 'last_trick_summary', None):
        st.markdown("📜 **ไม้ล่าสุด (ใครลงอะไร / ใครได้กิน):**")
        s = server.last_trick_summary
        cols_summary = st.columns(4)
        for i in range(4):
            played_cards = s["plays"].get(i, [])
            cards_str = " ".join([card_label(c) for c in played_cards]) if played_cards else "ไม่ได้ลง"
            if i == s["winner_idx"]:
                cols_summary[i].success(f"🏆 **P{i+1}**\n\n{cards_str}\n\n*(กิน +{s['cards_won']})*")
            else:
                cols_summary[i].info(f"👤 P{i+1}\n\n{cards_str}")
        st.divider()

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
                if get_available_pho_hoo(my_hand): play_opts.append("โฟฮู้ (4)")
                if get_available_five_hoo(my_hand): play_opts.append("ไฟฟ์ฮู้ (5)")

                play_type = st.radio("ประเภท:", play_opts, horizontal=True, label_visibility="collapsed")
                
                req_cnt = 1
                if "2" in play_type: req_cnt = 2
                elif "3" in play_type: req_cnt = 3
                elif "4" in play_type: req_cnt = 4
                elif "5" in play_type: req_cnt = 5

                played_indices = render_hand_selector(my_hand, req_cnt=req_cnt, disabled=False, key_suffix=f"lead_{req_cnt}")

                if played_indices is not None and len(played_indices) == req_cnt:
                    selected_cards = [my_hand[i] for i in played_indices if i < len(my_hand)]
                    if len(selected_cards) == req_cnt:
                        ptype_map = {"เม็ด": "Med", "ตุ่ย": "Tui", "ซาฮู้": "Sa-Hoo", "ซาจุก": "Sa-Jut", "โฟจุก": "Pho-Jut", "โฟฮู้": "Pho-Hoo", "ไฟฟ์ฮู้": "Five-Hoo"}
                        matched_type = "Med"
                        for k, v in ptype_map.items():
                            if k in play_type: matched_type = v; break

                        server.current_plays[server.leader] = selected_cards
                        server.current_play_type = matched_type
                        st.rerun()

            # Follower ลงตาม
            elif server.leader in server.current_plays and my_p_idx not in server.current_plays:
                curr_req = min(len(server.current_plays[server.leader]), len(my_hand))
                st.write(f"🃏 **ลงหมากตาม (เลือกลาก/แตะ {curr_req} ใบ):**")
                
                played_indices = render_hand_selector(my_hand, req_cnt=curr_req, disabled=False, key_suffix=f"follow_{curr_req}")

                if played_indices is not None and len(played_indices) == curr_req:
                    selected_cards = [my_hand[i] for i in played_indices if i < len(my_hand)]
                    if len(selected_cards) == curr_req:
                        server.current_plays[my_p_idx] = selected_cards
                        st.rerun()

            elif my_p_idx in server.current_plays:
                st.success("✅ คุณลงหมากเรียบร้อย 🔒 (รอคนอื่นลงให้ครบ...)")
                render_hand_selector(my_hand, req_cnt=1, disabled=True, key_suffix="played_wait")
            else:
                st.info(f"⏳ รอ P{server.leader+1} ({get_player_name(server.leader)}) เปิดหมาก...")
                render_hand_selector(my_hand, req_cnt=1, disabled=True, key_suffix="leader_wait")

    else:
        server.phase = "round_summary"
        st.rerun()

# ---------------------------------------------------------
# 🏁 PHASE 3: Round Summary
# ---------------------------------------------------------
elif server.phase == "round_summary":
    st.subheader(f"🏁 สรุปรอบที่ {server.round_num}")
    round_results = []
    for i in range(4):
        bid, won = server.bids[i], server.tricks_won[i]
        base = 3 if (bid == 0 and won == 0) else ((bid + 5) if bid == won else -abs(won - bid))
        round_score = base * server.multiplier
        round_results.append(round_score)
        st.write(f"• **P{i+1} ({get_player_name(i)})**: **{round_score} แต้ม** (เรียก {bid}/กิน {won})")

    if my_role == "P1":
        if st.button("➡️ ไปต่อรอบถัดไป", type="primary", use_container_width=True):
            for i in range(4): server.scores[i] += round_results[i]
            server.prev_leader = server.leader
            server.round_num += 1
            hands, leader, mult = deal_round(server.prev_leader, is_first_round=False)
            server.hands, server.leader, server.current_bidder, server.multiplier = hands, leader, leader, mult
            server.tricks_won, server.bids, server.bids_entered = [0]*4, [0]*4, [False]*4
            server.current_plays, server.last_trick_summary, server.played_pieces = {}, None, []
            server.phase = "bidding"
            st.rerun()
    else: st.info("รอ P1 กดไปต่อรอบถัดไป...")