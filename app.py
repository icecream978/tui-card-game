import streamlit as st
import random
import time
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
    .block-container { padding-top: 0.8rem; padding-bottom: 0.8rem; padding-left: 0.4rem; padding-right: 0.4rem; }
    .stButton > button { border-radius: 8px; padding: 3px 6px !important; font-size: 13px !important; font-weight: bold; width: 100%; }
    div[data-testid="stSidebarNav"] { display: none; }
    div[data-testid="stHorizontalBlock"] { gap: 0.2rem; }
    .stAlert { padding: 4px 8px !important; margin-bottom: 4px !important; }
    hr { margin: 8px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🇹🇭 แปลภาษายศหมากไทย (อัปเดต: เผ่า, เรือ, ม้า)
# ---------------------------------------------------------
RANK_THAI = {
    "Tee": "ตี่",
    "Bin": "บิน",
    "Chang": "ช้าง",
    "Ruea": "เรือ",
    "Maa": "ม้า",
    "Pao": "เผ่า",
    "Jut": "จุก"
}

RANK_VAL = {r: i for i, r in enumerate(RANK_ORDER)}

def card_label(card):
    symbol = "🔴" if card.color == "Red" else "⚫"
    return f"{symbol}{RANK_THAI.get(card.rank, card.rank)}"

def render_card_html(card):
    is_red = card.color == "Red"
    bg = "#FFF0F0" if is_red else "#F0F0F0"
    tc = "#D32F2F" if is_red else "#212121"
    border = "#E57373" if is_red else "#9E9E9E"
    return f"""<span style="background:{bg};color:{tc};border:1px solid {border};border-radius:6px;padding:2px 6px;margin:1px;font-weight:bold;font-size:12px;">{'🔴' if is_red else '⚫'}{RANK_THAI.get(card.rank, card.rank)}</span>"""

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
def is_juk(piece): return piece.rank == "Jut"

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
            res.append((f"{s_type}+{extra_th}", s_cards + [extra]))
    return res

def get_available_five_hoo(hand):
    sahoos = get_available_sahoos(hand)
    res = []
    for s_type, s_cards in sahoos:
        color = s_cards[0].color
        bins = [p for p in hand if p not in s_cards and p.color == color and p.rank == "Bin"]
        changs = [p for p in hand if p not in s_cards and p.color == color and p.rank == "Chang"]
        if bins and changs:
            res.append((f"{s_type}+บิน+ช้าง", s_cards + [bins[0], changs[0]]))
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

if "selected_cards" not in st.session_state:
    st.session_state.selected_cards = []

my_id = st.session_state.my_id

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

# Header แบบย่อเหลือแค่อิโมจิ
c_head, c_reset, c_leave = st.columns([6, 1, 1])
c_head.markdown(f"🏠 **{room_code}** | **{my_name}** (`{my_role}`)")
if c_reset.button("🔄", help="รีเซ็ตห้อง"):
    server.reset_game()
    st.session_state.selected_cards = []
    st.rerun()
if c_leave.button("🚪", help="ออกจากห้อง"):
    del server.players[my_id]
    st.session_state.current_room = None
    st.session_state.selected_cards = []
    st.rerun()

def get_player_name(idx):
    p = next((p for p in server.players.values() if p["p_idx"] == idx), None)
    return p["name"] if p else f"P{idx+1}"

# ---------------------------------------------------------
# 🎴 Component เลือกไพ่ในมือ (Interactive Tap-to-Select)
# ---------------------------------------------------------
def render_interactive_hand(hand, max_select=1):
    st.session_state.selected_cards = [i for i in st.session_state.selected_cards if i < len(hand)]
    
    st.caption(f"🎴 **ไพ่ในมือคุณ** (แตะเพื่อเลือก {len(st.session_state.selected_cards)}/{max_select} ใบ):")
    
    # ปุ่มเรียงไพ่แบบย่อ
    sc1, sc2, sc3 = st.columns(3)
    if sc1.button("🔽 ตี่➡️จุก", use_container_width=True):
        server.hands[my_p_idx] = sort_hand(hand, "rank_desc")
        st.session_state.selected_cards = []
        st.rerun()
    if sc2.button("🔼 จุก➡️ตี่", use_container_width=True):
        server.hands[my_p_idx] = sort_hand(hand, "rank_asc")
        st.session_state.selected_cards = []
        st.rerun()
    if sc3.button("🔴⚫ สี", use_container_width=True):
        server.hands[my_p_idx] = sort_hand(hand, "color")
        st.session_state.selected_cards = []
        st.rerun()

    # แสดงไพ่เป็นปุ่มกดเรียงกริด
    grid_cols = st.columns(4)
    for idx, card in enumerate(hand):
        col = grid_cols[idx % 4]
        is_selected = idx in st.session_state.selected_cards
        btn_label = f"{'✅ ' if is_selected else ''}{card_label(card)}"
        btn_type = "primary" if is_selected else "secondary"
        
        if col.button(btn_label, key=f"card_btn_{idx}", type=btn_type, use_container_width=True):
            if is_selected:
                st.session_state.selected_cards.remove(idx)
            else:
                if max_select == 1:
                    st.session_state.selected_cards = [idx]
                else:
                    if len(st.session_state.selected_cards) < max_select:
                        st.session_state.selected_cards.append(idx)
            st.rerun()

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
            st.session_state.selected_cards = []
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

    # ย่อสถานะการบิด
    with st.expander("📊 ดูการบิดแต้มเพื่อน", expanded=False):
        for idx, p_idx in enumerate(bid_order):
            p_n = get_player_name(p_idx)
            status = f"{server.bids[p_idx]} แต้ม" if server.bids_entered[p_idx] else ("กำลังบิด..." if p_idx == server.current_bidder else "รอคิว")
            st.write(f"• P{p_idx+1} ({p_n}): {status}")

    if my_role != "Spectator":
        render_interactive_hand(server.hands[my_p_idx], max_select=1)

    if all(server.bids_entered):
        server.phase = "playing"
        st.session_state.selected_cards = []
        st.rerun()

# ---------------------------------------------------------
# 🃏 PHASE 2: Playing
# ---------------------------------------------------------
elif server.phase == "playing":
    # ประมวลผลการชนะไม้นี้
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
        st.session_state.selected_cards = []
        st.rerun()

    st.caption(f"🃏 รอบ {server.round_num}/15 | Leader: **P{server.leader+1} ({get_player_name(server.leader)})**")

    # แต้มและการกินแบบย่อ (กดขยายเพื่อดู)
    with st.expander("📊 ดูแต้ม / สถานะการกิน (กดเพื่อดู)", expanded=False):
        for i in range(4):
            st.write(f"• **P{i+1} ({get_player_name(i)})**: เรียก {server.bids[i]} | กิน {server.tricks_won[i]} แต้ม")
        if getattr(server, 'last_trick_summary', None):
            s = server.last_trick_summary
            st.divider()
            st.caption(f"🏆 ไม้ล่าสุด: P{s['winner_idx']+1} ({s['winner_name']}) ชนะกิน (+{s['cards_won']} แต้ม)")

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

                render_interactive_hand(my_hand, max_select=req_cnt)

                selected_indices = st.session_state.selected_cards
                if len(selected_indices) == req_cnt:
                    if st.button("🚀 ลงหมากที่เลือก", type="primary", use_container_width=True):
                        selected_cards = [my_hand[i] for i in selected_indices]
                        
                        # กำหนด Type
                        ptype_map = {"เม็ด": "Med", "ตุ่ย": "Tui", "ซาฮู้": "Sa-Hoo", "ซาจุก": "Sa-Jut", "โฟจุก": "Pho-Jut", "โฟฮู้": "Pho-Hoo", "ไฟฟ์ฮู้": "Five-Hoo"}
                        matched_type = "Med"
                        for k, v in ptype_map.items():
                            if k in play_type: matched_type = v; break

                        server.current_plays[server.leader] = selected_cards
                        server.current_play_type = matched_type
                        st.session_state.selected_cards = []
                        st.rerun()

            # Follower ลงตาม
            elif server.leader in server.current_plays and my_p_idx not in server.current_plays:
                curr_req = min(len(server.current_plays[server.leader]), len(my_hand))
                st.write(f"🃏 **ลงหมากตาม (เลือก {curr_req} ใบ):**")
                
                render_interactive_hand(my_hand, max_select=curr_req)

                selected_indices = st.session_state.selected_cards
                if len(selected_indices) == curr_req:
                    if st.button("✅ ยืนยันลงหมาก", type="primary", use_container_width=True):
                        server.current_plays[my_p_idx] = [my_hand[i] for i in selected_indices]
                        st.session_state.selected_cards = []
                        st.rerun()

            elif my_p_idx in server.current_plays:
                st.success("✅ คุณลงหมากเรียบร้อย 🔒 (รอคนอื่นลงให้ครบ...)")
            else:
                st.info(f"⏳ รอ P{server.leader+1} ({get_player_name(server.leader)}) เปิดหมาก...")

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
            st.session_state.selected_cards = []
            st.rerun()
    else: st.info("รอ P1 กดไปต่อรอบถัดไป...")