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
# 📱 ตั้งค่าหน้าจอ & CSS ตกแต่งปุ่มให้เหมือนไพ่จริง
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
    /* จัดแต่ง Padding สำหรับมือถือ */
    .block-container { padding-top: 0.5rem; padding-bottom: 0.5rem; padding-left: 0.3rem; padding-right: 0.3rem; }
    div[data-testid="stSidebarNav"] { display: none; }
    div[data-testid="stHorizontalBlock"] { gap: 0.2rem; }
    .stAlert { padding: 4px 8px !important; margin-bottom: 4px !important; }
    hr { margin: 6px 0 !important; }

    /* ตกแต่งปุ่มทั่วไป */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: bold !important;
        transition: all 0.15s ease-in-out !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🇹🇭 แปลภาษายศหมากไทย
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
# 🎴 ระบบแสดงผลไพ่ & ช่องลงหมาก แบบ Native ที่สวยงาม
# ---------------------------------------------------------
def render_pretty_card_board(hand, req_cnt=1, disabled=False):
    sel = st.session_state.selected_cards
    # กรองเอาดรรชนีที่เกินไพ่ในมือออก
    sel = [i for i in sel if i < len(hand)]
    st.session_state.selected_cards = sel

    # 1. 🎯 ช่องลงหมาก (Staging Zone)
    st.markdown(f"##### 🎯 ช่องลงหมาก (`{len(sel)}/{req_cnt}` ใบ)")
    
    if not sel:
        st.info("👇 แตะไพ่ในมือด้านล่างเพื่อย้ายขึ้นมาลงในช่องนี้", icon="ℹ️")
    else:
        # แสดงไพ่ที่ถูกเลือกไว้
        drop_cols = st.columns(max(len(sel), 1))
        for d_idx, c_idx in enumerate(sel):
            card = hand[c_idx]
            if drop_cols[d_idx].button(f"❌ {card_label(card)}", key=f"drop_{d_idx}_{c_idx}"):
                st.session_state.selected_cards.remove(c_idx)
                st.rerun()

    st.markdown("---")

    # 2. 🎴 ไพ่ในมือ (จัดเรียง 4 ใบต่อ 1 แถว)
    st.markdown("##### 🎴 ไพ่ในมือคุณ:")
    
    for row_start in range(0, len(hand), 4):
        cols = st.columns(4)
        for col_idx in range(4):
            card_idx = row_start + col_idx
            if card_idx < len(hand):
                card = hand[card_idx]
                is_sel = card_idx in sel
                
                label = f"✅ {card_label(card)}" if is_sel else card_label(card)
                btn_type = "primary" if is_sel else "secondary"

                # คลิกได้ถ้ายังกดไม่ครบ หรือถ้าเลือกไพ่อื่นแทน
                can_click = not disabled and (is_sel or len(sel) < req_cnt)

                if cols[col_idx].button(
                    label, 
                    key=f"card_hand_{card_idx}", 
                    type=btn_type,
                    disabled=not can_click,
                    use_container_width=True
                ):
                    if is_sel:
                        st.session_state.selected_cards.remove(card_idx)
                    else:
                        st.session_state.selected_cards.append(card_idx)
                    st.rerun()

    st.markdown("---")

    # 3. 🚀 ปุ่มยืนยันลงหมาก
    is_ready = (len(sel) == req_cnt) and not disabled
    if st.button(
        f"🚀 ลงหมากที่เลือก ({len(sel)}/{req_cnt})", 
        type="primary", 
        disabled=not is_ready, 
        use_container_width=True,
        key="btn_confirm_play"
    ):
        chosen = [hand[i] for i in sel if i < len(hand)]
        st.session_state.selected_cards = []  # รีเซ็ต
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
        render_pretty_card_board(server.hands[my_p_idx], req_cnt=1, disabled=True)

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

    # 📜 สรุปไม้ล่าสุด
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

                ptype_map = {"เม็ด": "Med", "ตุ่ย": "Tui", "ซาฮู้": "Sa-Hoo", "ซาจุก": "Sa-Jut", "โฟจุก": "Pho-Jut", "โฟฮู้": "Pho-Hoo", "ไฟฟ์ฮู้": "Five-Hoo"}
                matched_type = "Med"
                for k, v in ptype_map.items():
                    if k in play_type: matched_type = v; break

                played_cards = render_pretty_card_board(my_hand, req_cnt=req_cnt, disabled=False)
                if played_cards:
                    server.current_plays[server.leader] = played_cards
                    server.current_play_type = matched_type
                    st.rerun()

            # Follower ลงตาม
            elif server.leader in server.current_plays and my_p_idx not in server.current_plays:
                curr_req = min(len(server.current_plays[server.leader]), len(my_hand))
                st.write(f"🃏 **ลงหมากตาม (เลือก {curr_req} ใบ):**")
                
                played_cards = render_pretty_card_board(my_hand, req_cnt=curr_req, disabled=False)
                if played_cards:
                    server.current_plays[my_p_idx] = played_cards
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
            st.session_state.selected_cards = []
            server.phase = "bidding"
            st.rerun()
    else: st.info("รอ P1 กดไปต่อรอบถัดไป...")