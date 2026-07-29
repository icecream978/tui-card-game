import streamlit as st
import streamlit.components.v1 as components
import random
import time
from streamlit_autorefresh import st_autorefresh
from tui_engine import (
    deal_round, can_play_tui, can_play_sahoo, 
    get_available_tuis, get_available_sahoos, resolve_trick,
    RANK_ORDER, RANK_COUNTS
)

# ---------------------------------------------------------
# 📱 ตั้งค่าหน้าจอ & CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="เกมตุ่ย (Tui Mobile - Multi Room)", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🔄 รีเฟรชอัตโนมัติทุก 2 วินาทีเพื่ออัปเดตสถานะห้อง
st_autorefresh(interval=2000, key="datarefresh")

st.markdown("""
<style>
    .stButton > button {
        border-radius: 10px;
        font-weight: bold;
        font-size: 15px !important;
        padding: 6px 12px !important;
    }
    div[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🇹🇭 แปลภาษายศหมากไทยครบทุกตัว (100%)
# ---------------------------------------------------------
RANK_THAI = {
    "Tee": "ตี่",
    "Bin": "บิน",
    "Chang": "ช้าง",
    "Ruea": "เรือ",
    "Maa": "ม้า",
    "Pao": "เปา",
    "Jut": "จุก"
}

RANK_VAL = {r: i for i, r in enumerate(RANK_ORDER)}

def card_to_thai(card):
    """แปลงหมากเป็นชื่อภาษาไทยสำหรับ Dropdown / List"""
    color_symbol = "🔴" if card.color == "Red" else "⚫"
    rank_th = RANK_THAI.get(card.rank, card.rank)
    color_th = "แดง" if card.color == "Red" else "ดำ"
    return f"{color_symbol} {rank_th} ({color_th})"

def render_card_html(card):
    """สร้าง Card Badge สวยงาม"""
    is_red = card.color == "Red"
    bg_color = "#FFF0F0" if is_red else "#F0F0F0"
    text_color = "#D32F2F" if is_red else "#212121"
    border_color = "#E57373" if is_red else "#9E9E9E"
    rank_th = RANK_THAI.get(card.rank, card.rank)

    return f"""<span style="
        display: inline-block;
        background-color: {bg_color};
        color: {text_color};
        border: 2px solid {border_color};
        border-radius: 8px;
        padding: 4px 10px;
        margin: 2px;
        font-weight: bold;
        font-size: 15px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    ">{'🔴' if is_red else '⚫'} {rank_th}</span>"""

def render_card_back_visual(count):
    """🎴 แสดงการถือไพ่ในมือของเพื่อน (Visual Card Backs)"""
    if count == 0:
        return "<span style='color: #888;'><em>(หมดมือ)</em></span>"
    
    backs = "".join([
        """<span style="
            display: inline-block;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #ffffff;
            border: 1px solid #ffffff;
            border-radius: 5px;
            padding: 3px 6px;
            margin: 1px;
            font-size: 12px;
            box-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        ">🎴</span>""" for _ in range(count)
    ])
    return f"<div>{backs} <small style='color:#666;'>({count} ใบ)</small></div>"

def render_drag_and_drop_board(cards_in_hand):
    """Component ลากวางไพ่ในมือ + โซนลงหมาก ด้วย HTML/SortableJS"""
    cards_html = ""
    for idx, card in enumerate(cards_in_hand):
        is_red = card.color == "Red"
        bg_color = "#FFF0F0" if is_red else "#F0F0F0"
        text_color = "#D32F2F" if is_red else "#212121"
        border_color = "#E57373" if is_red else "#9E9E9E"
        rank_th = RANK_THAI.get(card.rank, card.rank)
        symbol = '🔴' if is_red else '⚫'
        
        cards_html += f"""
        <div class="card-item" data-index="{idx}" style="
            display: inline-flex;
            align-items: center;
            background-color: {bg_color};
            color: {text_color};
            border: 2px solid {border_color};
            border-radius: 10px;
            padding: 6px 12px;
            margin: 3px;
            font-weight: bold;
            font-size: 15px;
            cursor: grab;
            user-select: none;
            box-shadow: 1px 2px 4px rgba(0,0,0,0.15);
            touch-action: none;
        ">
            <span style="margin-right: 4px;">{symbol}</span> {rank_th}
        </div>
        """

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 2px; background: transparent; }}
            .zone-title {{ font-weight: bold; font-size: 13px; color: #444; margin-bottom: 4px; }}
            .drop-zone {{
                min-height: 60px; border: 2px dashed #4CAF50; border-radius: 10px;
                padding: 4px; background-color: #F1F8E9; display: flex; flex-wrap: wrap;
                align-items: center; gap: 2px;
            }}
            .hand-zone {{
                min-height: 60px; border: 2px solid #E0E0E0; border-radius: 10px;
                padding: 4px; background-color: #FAFAFA; display: flex; flex-wrap: wrap;
                align-items: center; gap: 2px;
            }}
            .ghost-card {{ opacity: 0.4; background-color: #C8E6C9 !important; }}
            .placeholder-text {{ color: #888; font-size: 12px; font-style: italic; margin: auto; pointer-events: none; }}
        </style>
    </head>
    <body>
        <div class="zone-title">🎯 โซนลงหมาก (ลากไพ่มาวางที่นี่):</div>
        <div id="board-zone" class="drop-zone">
            <span id="hint-text" class="placeholder-text">🎯 ลากไพ่ลงมาที่นี่</span>
        </div>
        <div style="height: 8px;"></div>
        <div class="zone-title">🎴 ไพ่ในมือคุณ (ลากสลับตำแหน่งเพื่อจัดเรียงได้):</div>
        <div id="hand-zone" class="hand-zone">
            {cards_html}
        </div>
        <script>
            const handEl = document.getElementById('hand-zone');
            const boardEl = document.getElementById('board-zone');
            const hintText = document.getElementById('hint-text');

            function checkHint() {{
                hintText.style.display = boardEl.querySelectorAll('.card-item').length > 0 ? 'none' : 'block';
            }}

            new Sortable(handEl, {{
                group: 'tui-group', animation: 150, ghostClass: 'ghost-card',
                delay: 50, delayOnTouchOnly: true, onEnd: checkHint
            }});
            new Sortable(boardEl, {{
                group: 'tui-group', animation: 150, ghostClass: 'ghost-card',
                onAdd: checkHint, onRemove: checkHint
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=220)

# ---------------------------------------------------------
# 🔀 ฟังก์ชันช่วยจัดเรียงไพ่ในมือ
# ---------------------------------------------------------
def sort_hand(hand, mode="rank_desc"):
    if mode == "rank_desc":
        return sorted(hand, key=lambda c: (-RANK_VAL[c.rank], 0 if c.color == "Red" else 1))
    elif mode == "rank_asc":
        return sorted(hand, key=lambda c: (RANK_VAL[c.rank], 0 if c.color == "Red" else 1))
    elif mode == "color":
        return sorted(hand, key=lambda c: (0 if c.color == "Red" else 1, -RANK_VAL[c.rank]))
    return hand

# ---------------------------------------------------------
# 🧠 ฟังก์ชันตรวจสอบชุดหมาก
# ---------------------------------------------------------
def is_juk(piece):
    return piece.rank == "Jut"

def get_available_sa_juk(hand):
    red_juks = [p for p in hand if is_juk(p) and p.color == "Red"]
    black_juks = [p for p in hand if is_juk(p) and p.color == "Black"]
    res = []
    if len(red_juks) >= 3: res.append(red_juks[:3])
    if len(black_juks) >= 3: res.append(black_juks[:3])
    return res

def get_available_pho_juk(hand):
    red_juks = [p for p in hand if is_juk(p) and p.color == "Red"]
    black_juks = [p for p in hand if is_juk(p) and p.color == "Black"]
    res = []
    if len(red_juks) >= 4: res.append(red_juks[:4])
    if len(black_juks) >= 4: res.append(black_juks[:4])
    return res

def get_available_pho_hoo(hand):
    sahoos = get_available_sahoos(hand)
    res = []
    for s_type, s_cards in sahoos:
        color = s_cards[0].color
        extra_candidates = [p for p in hand if p not in s_cards and p.color == color and p.rank in ["Bin", "Chang"]]
        for extra in extra_candidates:
            extra_th = RANK_THAI.get(extra.rank, extra.rank)
            res.append((f"{s_type} + {extra_th}", s_cards + [extra]))
    return res

def get_available_five_hoo(hand):
    sahoos = get_available_sahoos(hand)
    res = []
    for s_type, s_cards in sahoos:
        color = s_cards[0].color
        bins = [p for p in hand if p not in s_cards and p.color == color and p.rank == "Bin"]
        changs = [p for p in hand if p not in s_cards and p.color == color and p.rank == "Chang"]
        if bins and changs:
            res.append((f"{s_type} + บิน + ช้าง", s_cards + [bins[0], changs[0]]))
    return res

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

# ---------------------------------------------------------
# 🚪 หน้าเลือกห้อง
# ---------------------------------------------------------
if not st.session_state.current_room:
    st.title("🎴 เข้าสู่เกมตุ่ย (Multiplayer)")
    player_name = st.text_input("ชื่อของคุณ:", value=st.session_state.get("player_name", ""), key="name_input", placeholder="กรอกชื่อเล่น...")

    if player_name.strip():
        st.session_state.player_name = player_name.strip()
        st.divider()
        tab1, tab2 = st.tabs(["➕ สร้างห้องใหม่", "🔍 เลือกห้องที่มีอยู่"])
        with tab1:
            new_room_code = st.text_input("ตั้งชื่อห้อง / รหัสห้อง:", placeholder="เช่น ROOM1, TUI88").strip().upper()
            if st.button("🚀 สร้าง / เข้าห้องนี้", type="primary", use_container_width=True):
                if new_room_code:
                    st.session_state.current_room = new_room_code
                    st.rerun()
        with tab2:
            active_rooms = room_manager.rooms
            if not active_rooms:
                st.info("ยังไม่มีห้องเปิดอยู่ สร้างห้องใหม่ได้เลยครับ!")
            else:
                for r_id, r_server in list(active_rooms.items()):
                    p_cnt = len([p for p in r_server.players.values() if p["role"].startswith("P")])
                    c_info, c_btn = st.columns([2, 1])
                    c_info.markdown(f"🏠 **ห้อง: {r_id}** ({p_cnt}/4 คน)")
                    if c_btn.button(f"เข้าร่วม {r_id}", key=f"join_{r_id}", use_container_width=True):
                        st.session_state.current_room = r_id
                        st.rerun()
    else: st.info("👆 กรุณากรอกชื่อผู้เล่นก่อนเริ่มเกม")
    st.stop()

# ---------------------------------------------------------
# 🎮 เข้าสู่ห้องเกม
# ---------------------------------------------------------
room_code = st.session_state.current_room
server = room_manager.get_or_create_room(room_code)

if my_id not in server.players:
    assigned_p_index = len([p for p in server.players.values() if p["role"].startswith("P")])
    if assigned_p_index < 4:
        role, p_idx = f"P{assigned_p_index + 1}", assigned_p_index
    else:
        role, p_idx = "Spectator", -1
    server.players[my_id] = {"name": st.session_state.player_name, "role": role, "p_idx": p_idx}

my_player_info = server.players[my_id]
my_role, my_name, my_p_idx = my_player_info["role"], my_player_info["name"], my_player_info["p_idx"]

col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
col_h1.markdown(f"🏠 **ห้อง: {room_code}** | คุณ: **{my_name}** (`{my_role}`)")
if col_h2.button("🔄 รีเซ็ตห้อง", use_container_width=True):
    server.reset_game()
    st.rerun()
if col_h3.button("🚪 ออกจากห้อง", use_container_width=True):
    del server.players[my_id]
    st.session_state.current_room = None
    st.rerun()

st.divider()

def get_player_name(idx):
    p = next((p for p in server.players.values() if p["p_idx"] == idx), None)
    return p["name"] if p else f"P{idx+1}"

def render_played_tracker(played_pieces):
    played_counts = {}
    for p in played_pieces:
        key = (p.rank, p.color)
        played_counts[key] = played_counts.get(key, 0) + 1

    with st.expander(f"📊 เช็คหมากที่ออกไปแล้ว ({len(played_pieces)}/32 ใบ)", expanded=False):
        c1, c2 = st.columns(2)
        display_ranks = list(reversed(RANK_ORDER))
        with c1:
            st.markdown("**🔴 หมากแดง**")
            for rank in display_ranks:
                total, played = RANK_COUNTS[rank], played_counts.get((rank, "Red"), 0)
                icon = "✅" if played == total else ("🟡" if played > 0 else "⚪")
                st.caption(f"{icon} **{RANK_THAI.get(rank, rank)}**: {played}/{total}")
        with c2:
            st.markdown("**⚫ หมากดำ**")
            for rank in display_ranks:
                total, played = RANK_COUNTS[rank], played_counts.get((rank, "Black"), 0)
                icon = "✅" if played == total else ("🟡" if played > 0 else "⚪")
                st.caption(f"{icon} **{RANK_THAI.get(rank, rank)}**: {played}/{total}")

# ---------------------------------------------------------
# 🚪 PHASE 0: Lobby
# ---------------------------------------------------------
if server.phase == "lobby":
    st.subheader(f"🏠 ห้องพัก {room_code} (รอครบ 4 คน)")
    active_ps = [p for p in server.players.values() if p["role"].startswith("P")]
    specs = [p for p in server.players.values() if p["role"] == "Spectator"]

    c1, c2 = st.columns(2)
    cols = [c1, c2, c1, c2]
    for i in range(4):
        p_found = next((p for p in active_ps if p["p_idx"] == i), None)
        if p_found: cols[i].success(f"**P{i+1}: {p_found['name']}** ✅")
        else: cols[i].warning(f"**P{i+1}: (ว่าง)**")

    if specs: st.info("👀 **คนดู:** " + ", ".join([s["name"] for s in specs]))

    if len(active_ps) == 4:
        st.success("🎉 ผู้เล่นครบ 4 คนแล้ว!")
        if my_role == "P1":
            if st.button("🚀 เริ่มเกมทันที (15 รอบ)", type="primary", use_container_width=True):
                hands, leader, mult = deal_round(None, is_first_round=True)
                server.hands, server.leader, server.current_bidder, server.multiplier = hands, leader, leader, mult
                server.played_pieces = []
                server.phase = "bidding"
                st.rerun()
        else: st.info("รอ P1 กดเริ่มเกม...")

# ---------------------------------------------------------
# 🎲 PHASE 1: Bidding
# ---------------------------------------------------------
elif server.phase == "bidding":
    st.markdown(f"### 🎲 รอบที่ {server.round_num}/15 (ตัวคูณ x{server.multiplier})")
    st.caption(f"👑 Leader เริ่มบิด: **P{server.leader+1} ({get_player_name(server.leader)})**")

    bid_order = [(server.leader + i) % 4 for i in range(4)]
    order_idx = bid_order.index(server.current_bidder) if server.current_bidder in bid_order else 0

    if my_role != "Spectator":
        if my_p_idx == server.current_bidder and not server.bids_entered[my_p_idx]:
            with st.container(border=True):
                st.subheader(f"🎯 ถึงตาคุณ ({my_name}) บิดแต้ม!")
                if order_idx == 3:
                    prev_sum = sum(server.bids[p] for p in bid_order[:3])
                    forbidden_bid = 8 - prev_sum
                    valid_bids = [b for b in range(9) if b != forbidden_bid] if 0 <= forbidden_bid <= 8 else list(range(9))
                    if 0 <= forbidden_bid <= 8: st.warning(f"⚠️ ห้ามบิด **{forbidden_bid}** แต้ม (คนสุดท้าย)")
                else: valid_bids = list(range(9))

                bid_val = st.selectbox("เลือกจำนวนแต้ม:", valid_bids, index=min(2, len(valid_bids)-1))
                if st.button("✅ ยืนยันคำเรียกแต้ม", type="primary", use_container_width=True):
                    server.bids[my_p_idx] = bid_val
                    server.bids_entered[my_p_idx] = True
                    server.current_bidder = (server.current_bidder + 1) % 4
                    st.rerun()
        elif server.bids_entered[my_p_idx]:
            st.success(f"✅ คุณเรียกแต้มแล้ว: **{server.bids[my_p_idx]} แต้ม**")

    st.write("📋 **สถานะการบิดแต้ม:**")
    b_col1, b_col2 = st.columns(2)
    b_cols = [b_col1, b_col2, b_col1, b_col2]
    for idx, p_idx in enumerate(bid_order):
        tag = " 👑" if p_idx == server.leader else ""
        p_n = get_player_name(p_idx)
        if server.bids_entered[p_idx]: b_cols[idx].write(f"• **P{p_idx+1} {p_n}{tag}**: {server.bids[p_idx]} แต้ม")
        elif p_idx == server.current_bidder: b_cols[idx].write(f"👉 **P{p_idx+1} {p_n}{tag}**: *กำลังบิด...*")
        else: b_cols[idx].write(f"• P{p_idx+1} {p_n}{tag}: *รอคิว*")

    st.divider()

    if my_role != "Spectator":
        st.subheader("🎴 จัดเรียง & ดูไพ่ในมือของคุณ")
        sc1, sc2, sc3 = st.columns(3)
        if sc1.button("🔽 ตี่ ➡️ จุก", use_container_width=True):
            server.hands[my_p_idx] = sort_hand(server.hands[my_p_idx], "rank_desc")
            st.rerun()
        if sc2.button("🔼 จุก ➡️ ตี่", use_container_width=True):
            server.hands[my_p_idx] = sort_hand(server.hands[my_p_idx], "rank_asc")
            st.rerun()
        if sc3.button("🔴⚫ เรียงตามสี", use_container_width=True):
            server.hands[my_p_idx] = sort_hand(server.hands[my_p_idx], "color")
            st.rerun()

        render_drag_and_drop_board(server.hands[my_p_idx])

    st.divider()
    st.write("👀 **หมากในมือของเพื่อนร่วมโต๊ะ:**")
    op_cols = st.columns(3)
    c_i = 0
    for i in range(4):
        if i == my_p_idx: continue
        with op_cols[c_i]:
            st.markdown(f"**P{i+1} ({get_player_name(i)})**")
            st.markdown(render_card_back_visual(len(server.hands[i])), unsafe_allow_html=True)
        c_i += 1

    if all(server.bids_entered):
        server.phase = "playing"
        st.rerun()

# ---------------------------------------------------------
# 🃏 PHASE 2: Playing
# ---------------------------------------------------------
elif server.phase == "playing":
    st.markdown(f"### 🃏 รอบที่ {server.round_num}/15")

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
            "play_type": server.current_play_type,
            "cards_won": cards_won_count
        }

        server.leader = winner
        server.current_plays = {}
        st.rerun()

    s_col1, s_col2 = st.columns(2)
    s_cols = [s_col1, s_col2, s_col1, s_col2]
    for i in range(4):
        s_cols[i].caption(f"**P{i+1} {get_player_name(i)}**: กิน **{server.tricks_won[i]}/{server.bids[i]}** แต้ม")

    render_played_tracker(getattr(server, 'played_pieces', []))

    if getattr(server, 'last_trick_summary', None):
        summary = server.last_trick_summary
        w_idx, w_name, pts = summary['winner_idx'], summary['winner_name'], summary.get('cards_won', 1)

        if my_role != "Spectator":
            if my_p_idx == w_idx: st.success(f"🥳 **สะใจ! คุณ ({my_name}) ชนะกินไม้นี้ ได้ไป +{pts} แต้ม!** 👑✨")
            else: st.error(f"😭 **โฮ... คุณ ({my_name}) โดน P{w_idx+1} ({w_name}) กินไป (+{pts} แต้ม)!** 💸🌧️")

        with st.expander(f"🔔 **สรุปผลไม้ล่าสุด:** 🏆 P{w_idx+1} ({w_name}) ชนะกิน (+{pts} แต้ม)", expanded=True):
            for p_i in range(4):
                cards_html = "".join([render_card_html(x) for x in summary['plays'][p_i]])
                tag = "🥳🔥" if p_i == w_idx else "หมก/ทิ้ง"
                st.markdown(f"**P{p_i+1} ({get_player_name(p_i)})**: {cards_html} *({tag})*", unsafe_allow_html=True)

    st.divider()
    st.markdown(f"👑 Leader ไม้นี้: **P{server.leader+1} ({get_player_name(server.leader)})**")

    if any(len(h) > 0 for h in server.hands):
        if my_role != "Spectator":
            my_hand = server.hands[my_p_idx]
            my_hand_indexed = list(enumerate(my_hand))

            # Leader เล่น
            if my_p_idx == server.leader and my_p_idx not in server.current_plays:
                with st.container(border=True):
                    st.subheader("🔥 ถึงตาคุณเปิดหมากนำ (Leader):")
                    play_options = ["เม็ด (1 ใบ)"]
                    if can_play_tui(my_hand): play_options.append("ตุ่ย (คู่ 2 ใบ)")
                    if can_play_sahoo(my_hand): play_options.append("ซาฮู้ (3 ใบ)")
                    if get_available_sa_juk(my_hand): play_options.append("ซาจุก (3 ใบ)")
                    if get_available_pho_juk(my_hand): play_options.append("โฟจุก (4 ใบ)")
                    if get_available_pho_hoo(my_hand): play_options.append("โฟฮู้ (4 ใบ)")
                    if get_available_five_hoo(my_hand): play_options.append("ไฟฟ์ฮู้ (5 ใบ)")

                    play_type = st.radio("เลือกรูปแบบการลง:", play_options, horizontal=True)

                    if "เม็ด" in play_type:
                        sel = st.selectbox("เลือกหมาก 1 ใบ:", my_hand_indexed, format_func=lambda x: f"ใบที่ {x[0]+1}: {card_to_thai(x[1])}")
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = [sel[1]]
                            server.current_play_type = "Med"
                            st.rerun()

                    elif "ตุ่ย" in play_type:
                        tui_pairs = get_available_tuis(my_hand)
                        sel_idx = st.selectbox("เลือกคู่ตุ่ย:", range(len(tui_pairs)), format_func=lambda idx: f"{card_to_thai(tui_pairs[idx][0])} + {card_to_thai(tui_pairs[idx][1])}")
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = tui_pairs[sel_idx]
                            server.current_play_type = "Tui"
                            st.rerun()

                    elif "ซาฮู้" in play_type:
                        sahoo_sets = get_available_sahoos(my_hand)
                        sel_idx = st.selectbox("เลือกชุดซาฮู้:", range(len(sahoo_sets)), format_func=lambda idx: f"{sahoo_sets[idx][0]}")
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = sahoo_sets[sel_idx][1]
                            server.current_play_type = "Sa-Hoo"
                            st.rerun()

                    elif "ซาจุก" in play_type:
                        sajuk_sets = get_available_sa_juk(my_hand)
                        sel_idx = st.selectbox("เลือกชุดซาจุก:", range(len(sajuk_sets)), format_func=lambda idx: ", ".join([card_to_thai(p) for p in sajuk_sets[idx]]))
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = sajuk_sets[sel_idx]
                            server.current_play_type = "Sa-Jut"
                            st.rerun()

                    elif "โฟจุก" in play_type:
                        phojuk_sets = get_available_pho_juk(my_hand)
                        sel_idx = st.selectbox("เลือกชุดโฟจุก:", range(len(phojuk_sets)), format_func=lambda idx: ", ".join([card_to_thai(p) for p in phojuk_sets[idx]]))
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = phojuk_sets[sel_idx]
                            server.current_play_type = "Pho-Jut"
                            st.rerun()

                    elif "โฟฮู้" in play_type:
                        pho_hoo_sets = get_available_pho_hoo(my_hand)
                        sel_idx = st.selectbox("เลือกชุดโฟฮู้:", range(len(pho_hoo_sets)), format_func=lambda idx: f"{pho_hoo_sets[idx][0]}")
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = pho_hoo_sets[sel_idx][1]
                            server.current_play_type = "Pho-Hoo"
                            st.rerun()

                    elif "ไฟฟ์ฮู้" in play_type:
                        five_hoo_sets = get_available_five_hoo(my_hand)
                        sel_idx = st.selectbox("เลือกชุดไฟฟ์ฮู้:", range(len(five_hoo_sets)), format_func=lambda idx: f"{five_hoo_sets[idx][0]}")
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = five_hoo_sets[sel_idx][1]
                            server.current_play_type = "Five-Hoo"
                            st.rerun()

            # Follower เล่น
            elif server.leader in server.current_plays and my_p_idx not in server.current_plays:
                with st.container(border=True):
                    curr_req = min(len(server.current_plays[server.leader]), len(my_hand))
                    st.subheader(f"🃏 ถึงตาคุณลงหมากตาม (เลือก {curr_req} ใบ):")

                    if curr_req == 1:
                        sel = st.selectbox("เลือกหมาก 1 ใบ:", my_hand_indexed, format_func=lambda x: f"ใบที่ {x[0]+1}: {card_to_thai(x[1])}")
                        if st.button("✅ ยืนยันลงหมาก", type="primary", use_container_width=True):
                            server.current_plays[my_p_idx] = [sel[1]]
                            st.rerun()
                    else:
                        sel_mult = st.multiselect(
                            f"เลือกให้ครบ {curr_req} ใบ:", 
                            my_hand_indexed, 
                            format_func=lambda x: f"ใบที่ {x[0]+1}: {card_to_thai(x[1])}", 
                            max_selections=curr_req,
                            key=f"follower_select_{my_p_idx}"
                        )
                        if len(sel_mult) == curr_req:
                            if st.button("✅ ยืนยันลงหมาก", type="primary", use_container_width=True):
                                server.current_plays[my_p_idx] = [item[1] for item in sel_mult]
                                st.rerun()
                        else: st.caption(f"เลือกอีก {curr_req - len(sel_mult)} ใบให้ครบถ้วน")
            elif my_p_idx in server.current_plays:
                st.success("✅ คุณเลือกลงหมากแล้ว 🔒 (รอคนอื่นลงให้ครบ...)")
            else:
                st.info(f"⏳ รอ Leader (**P{server.leader+1} {get_player_name(server.leader)}**) เปิดหมากก่อน...")

        st.write("📌 **สถานะผู้เล่นบนโต๊ะ:**")
        p_col1, p_col2 = st.columns(2)
        p_cols = [p_col1, p_col2, p_col1, p_col2]
        for i in range(4):
            p_n = get_player_name(i)
            if i in server.current_plays: p_cols[i].info(f"**P{i+1} ({p_n})**: ลงแล้ว 🔒")
            else: p_cols[i].warning(f"**P{i+1} ({p_n})**: *ยังไม่ลง*")

        st.divider()

        if my_role != "Spectator":
            with st.expander(f"🎴 ไพ่ในมือของคุณ ({len(server.hands[my_p_idx])} ใบ) - ใช้ Drag & Drop ได้", expanded=True):
                sc1, sc2, sc3 = st.columns(3)
                if sc1.button("🔽 ใหญ่ ➡️ เล็ก", key="s1", use_container_width=True):
                    server.hands[my_p_idx] = sort_hand(server.hands[my_p_idx], "rank_desc")
                    st.rerun()
                if sc2.button("🔼 เล็ก ➡️ ใหญ่", key="s2", use_container_width=True):
                    server.hands[my_p_idx] = sort_hand(server.hands[my_p_idx], "rank_asc")
                    st.rerun()
                if sc3.button("🔴⚫ เรียงตามสี", key="s3", use_container_width=True):
                    server.hands[my_p_idx] = sort_hand(server.hands[my_p_idx], "color")
                    st.rerun()

                render_drag_and_drop_board(server.hands[my_p_idx])

        st.write("👀 **จำนวนไพ่ในมือของเพื่อน:**")
        op_cols = st.columns(3)
        c_i = 0
        for i in range(4):
            if i == my_p_idx: continue
            with op_cols[c_i]:
                st.markdown(f"**P{i+1} ({get_player_name(i)})**")
                st.markdown(render_card_back_visual(len(server.hands[i])), unsafe_allow_html=True)
            c_i += 1

    else:
        server.phase = "round_summary"
        st.rerun()

# ---------------------------------------------------------
# 🏁 PHASE 3: Round Summary
# ---------------------------------------------------------
elif server.phase == "round_summary":
    st.subheader(f"🏁 จบการแข่งขันรอบที่ {server.round_num}!")
    round_results = []
    for i in range(4):
        bid, won = server.bids[i], server.tricks_won[i]
        if bid == 0 and won == 0: base = 3
        elif bid == won: base = bid + 5
        else: base = -abs(won - bid)

        round_score = base * server.multiplier
        round_results.append(round_score)
        st.write(f"• **P{i+1} {get_player_name(i)}**: **{round_score} แต้ม** (เรียก {bid} / กิน {won})")

    if my_role == "P1":
        if st.button("➡️ ไปต่อรอบถัดไป", type="primary", use_container_width=True):
            for i in range(4): server.scores[i] += round_results[i]
            server.prev_leader = server.leader
            server.round_num += 1
            hands, leader, mult = deal_round(server.prev_leader, is_first_round=False)
            server.hands, server.leader, server.current_bidder, server.multiplier = hands, leader, leader, mult
            server.tricks_won = [0, 0, 0, 0]
            server.bids = [0, 0, 0, 0]
            server.bids_entered = [False, False, False, False]
            server.current_plays = {}
            server.last_trick_summary = None
            server.played_pieces = []
            server.phase = "bidding"
            st.rerun()
    else: st.info("รอ P1 กดไปต่อรอบถัดไป...")