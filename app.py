import streamlit as st
import random
import time
from streamlit_autorefresh import st_autorefresh
from tui_engine import (
    deal_round, can_play_tui, can_play_sahoo, 
    get_available_tuis, get_available_sahoos, resolve_trick
)

# ---------------------------------------------------------
# 📱 ตั้งค่าหน้าจอ & CSS ให้รองรับมือถือแบบสมบูรณ์
# ---------------------------------------------------------
st.set_page_config(
    page_title="เกมตุ่ย (Tui Mobile)", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🔄 รีเฟรชอัตโนมัติทุก 2 วินาที
st_autorefresh(interval=2000, key="datarefresh")

# Custom CSS ตกแต่งให้ปุ่มใหญ่ อ่านง่ายบนจอมือถือ
st.markdown("""
<style>
    /* ปรับแต่งปุ่มกดให้เต็มความกว้างและกดง่ายบนมือถือ */
    .stButton > button {
        border-radius: 10px;
        font-weight: bold;
        font-size: 16px !important;
        padding: 10px 15px !important;
    }
    /* ปรับขนาดตัวหนังสือสำหรับมือถือ */
    .mobile-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 8px;
        border-left: 4px solid #ff4b4b;
    }
    .badge-winner {
        background-color: #28a745;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
    }
    /* ซ่อนแถบควบคุมบางจุดที่ไม่จำเป็น */
    div[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🧠 ระบบแชร์ข้อมูลกลาง (Shared Game Server)
# ---------------------------------------------------------
class GameServer:
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        self.players = {}  # {session_id: {"name": str, "role": "P1"..."Spectator"}}
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
        self.last_trick_summary = None  # สรุปผลไม้ล่าสุด

@st.cache_resource
def get_game_server():
    return GameServer()

server = get_game_server()

# Safe attribute check
if not hasattr(server, 'last_trick_summary'):
    server.last_trick_summary = None

# ---------------------------------------------------------
# 👤 จัดการผู้เล่นเข้าห้อง (Session Tracking)
# ---------------------------------------------------------
if "my_id" not in st.session_state:
    st.session_state.my_id = f"user_{int(time.time() * 1000)}_{random.randint(100, 999)}"

my_id = st.session_state.my_id

if my_id not in server.players:
    st.title("🎴 เข้าสู่เกมตุ่ย")
    player_name = st.text_input("ชื่อผู้เล่น:", value="", key="name_input", placeholder="กรอกชื่อของคุณที่นี่...")
    
    if st.button("🚀 เข้าห้องเกม", type="primary", use_container_width=True) and player_name.strip():
        assigned_p_index = len([p for p in server.players.values() if p["role"].startswith("P")])
        
        if assigned_p_index < 4:
            role = f"P{assigned_p_index + 1}"
            p_idx = assigned_p_index
        else:
            role = "Spectator"
            p_idx = -1

        server.players[my_id] = {
            "name": player_name.strip(),
            "role": role,
            "p_idx": p_idx
        }
        st.rerun()
    st.stop()

my_player_info = server.players[my_id]
my_role = my_player_info["role"]
my_name = my_player_info["name"]
my_p_idx = my_player_info["p_idx"]

# Header สรุปสั้นๆ บนมือถือ
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.markdown(f"🎴 **เกมตุ่ย** | คุณคือ: **{my_name}** (`{my_role}`)")
with col_h2:
    if st.button("🔄 รีเซ็ต", use_container_width=True):
        server.reset_game()
        st.rerun()

st.divider()

# Helper ดึงชื่อตาม index
def get_player_name(idx):
    p = next((p for p in server.players.values() if p["p_idx"] == idx), None)
    return p["name"] if p else f"P{idx+1}"

# ---------------------------------------------------------
# 🚪 PHASE 0: ล็อบบี้ (Lobby)
# ---------------------------------------------------------
if server.phase == "lobby":
    st.subheader("🏠 ล็อบบี้ห้องพัก (รอครบ 4 คน)")
    
    active_ps = [p for p in server.players.values() if p["role"].startswith("P")]
    specs = [p for p in server.players.values() if p["role"] == "Spectator"]

    # แสดงผลแบบ 2x2 Grid สำหรับมือถือ
    c1, c2 = st.columns(2)
    cols = [c1, c2, c1, c2]
    for i in range(4):
        with cols[i]:
            p_found = next((p for p in active_ps if p["p_idx"] == i), None)
            if p_found:
                st.success(f"**P{i+1}: {p_found['name']}** ✅")
            else:
                st.warning(f"**P{i+1}: (ว่าง)**")

    if specs:
        st.info("👀 **คนดู:** " + ", ".join([s["name"] for s in specs]))

    if len(active_ps) == 4:
        st.balloons()
        st.success("🎉 ผู้เล่นครบ 4 คนแล้ว!")
        if my_role == "P1":
            if st.button("🚀 เริ่มเกมทันที (15 รอบ)", type="primary", use_container_width=True):
                hands, leader, mult = deal_round(None, is_first_round=True)
                server.hands = hands
                server.leader = leader
                server.current_bidder = leader
                server.multiplier = mult
                server.phase = "bidding"
                st.rerun()
        else:
            st.info("รอ P1 กดเริ่มเกม...")
    else:
        st.info("⏳ กรุณารอเพื่อนเปิดหน้าเว็บเข้ามาจนครบ 4 คน...")

# ---------------------------------------------------------
# 🎲 PHASE 1: การเรียกแต้ม (Bidding)
# ---------------------------------------------------------
elif server.phase == "bidding":
    st.markdown(f"### 🎲 รอบที่ {server.round_num}/15 (ตัวคูณ x{server.multiplier})")
    st.caption(f"👑 Leader เริ่มบิด: **P{server.leader+1} ({get_player_name(server.leader)})**")

    # 1. Action ส่วนของการบิด (ถ้าถึงตาเรา ให้ขึ้นตรงนี้ทันที!)
    bid_order = [(server.leader + i) % 4 for i in range(4)]
    order_idx = bid_order.index(server.current_bidder) if server.current_bidder in bid_order else 0

    if my_role != "Spectator":
        if my_p_idx == server.current_bidder and not server.bids_entered[my_p_idx]:
            with st.container(border=True):
                st.subheader(f"🎯 ถึงตาคุณ ({my_name}) บิดแต้ม!")

                # 🚫 กฎคนสุดท้าย: ผลรวมแต้มห้ามเท่ากับ 8
                if order_idx == 3:
                    prev_sum = sum(server.bids[p] for p in bid_order[:3])
                    forbidden_bid = 8 - prev_sum
                    if 0 <= forbidden_bid <= 8:
                        valid_bids = [b for b in range(9) if b != forbidden_bid]
                        st.warning(f"⚠️ คุณเป็นคนสุดท้าย! ห้ามบิด **{forbidden_bid}** แต้ม (เพราะผลรวมจะเท่ากับ 8)")
                    else:
                        valid_bids = list(range(9))
                else:
                    valid_bids = list(range(9))

                bid_val = st.selectbox(
                    "เลือกจำนวนแต้มที่คิดว่าจะกินได้:", 
                    valid_bids, 
                    index=min(2, len(valid_bids)-1), 
                    key=f"bid_select_{my_p_idx}",
                )

                if st.button("✅ ยืนยันคำเรียกแต้ม", type="primary", use_container_width=True):
                    server.bids[my_p_idx] = bid_val
                    server.bids_entered[my_p_idx] = True
                    server.current_bidder = (server.current_bidder + 1) % 4
                    st.rerun()
        elif server.bids_entered[my_p_idx]:
            st.success(f"✅ คุณเรียกแต้มแล้ว: **{server.bids[my_p_idx]} แต้ม** (รอเพื่อน...)")
        else:
            st.info(f"⏳ กำลังรอ **P{server.current_bidder+1} ({get_player_name(server.current_bidder)})** บิดแต้ม...")

    # 2. ตารางสรุปการบิด 2x2 บนมือถือ
    st.write("📋 **สถานะการบิดแต้ม:**")
    b_col1, b_col2 = st.columns(2)
    b_cols = [b_col1, b_col2, b_col1, b_col2]
    
    for idx, p_idx in enumerate(bid_order):
        with b_cols[idx]:
            tag = " 👑" if p_idx == server.leader else ""
            p_n = get_player_name(p_idx)
            if server.bids_entered[p_idx]:
                st.write(f"• **P{p_idx+1} {p_n}{tag}**: {server.bids[p_idx]} แต้ม")
            elif p_idx == server.current_bidder:
                st.write(f"👉 **P{p_idx+1} {p_n}{tag}**: *กำลังบิด...*")
            else:
                st.write(f"• P{p_idx+1} {p_n}{tag}: *รอคิว*")

    st.divider()

    # 3. ดูหมากในมือ (จัดกลุ่มด้วย Tabs บนมือถือ)
    st.write("🎴 **ดูหมากในมือ:**")
    tabs = st.tabs(["👤 ไพ่ของคุณ"] + [f"P{i+1}" for i in range(4) if i != my_p_idx])
    
    with tabs[0]:
        if my_role != "Spectator":
            cards_str = " | ".join([f"[{idx+1}] {str(p)}" for idx, p in enumerate(server.hands[my_p_idx])])
            st.info(cards_str)
        else:
            st.write("ดูไพ่ในฐานะ Spectator")

    tab_idx = 1
    for i in range(4):
        if i == my_p_idx: continue
        with tabs[tab_idx]:
            if my_role == "Spectator":
                cards_str = " | ".join([str(p) for p in server.hands[i]])
                st.write(cards_str)
            else:
                st.write(f"🔒 ซ่อนหมาก ({len(server.hands[i])} ใบ)")
        tab_idx += 1

    if all(server.bids_entered):
        server.phase = "playing"
        st.rerun()

# ---------------------------------------------------------
# 🃏 PHASE 2: การเล่นหมาก (Playing)
# ---------------------------------------------------------
elif server.phase == "playing":
    st.markdown(f"### 🃏 รอบที่ {server.round_num}/15")

    # ⚡ 1. คำนวณผู้ชนะอัตโนมัติเมื่อลงครบ 4 คน
    if len(server.current_plays) == 4:
        for p_idx, chosen_list in server.current_plays.items():
            for target_p in chosen_list:
                for hand_p in list(server.hands[p_idx]):
                    if hand_p.key() == target_p.key():
                        server.hands[p_idx].remove(hand_p)
                        break

        winner = resolve_trick(server.current_plays, server.current_play_type, server.leader)
        w_name = get_player_name(winner)

        server.last_trick_summary = {
            "plays": {p_idx: [str(x) for x in server.current_plays[p_idx]] for p_idx in range(4)},
            "winner_idx": winner,
            "winner_name": w_name,
            "play_type": server.current_play_type
        }

        server.tricks_won[winner] += 1
        server.leader = winner
        server.current_plays = {}
        st.rerun()

    # 2. แถบสรุปเป้าหมายและการกิน (2x2 Grid)
    s_col1, s_col2 = st.columns(2)
    s_cols = [s_col1, s_col2, s_col1, s_col2]
    for i in range(4):
        p_n = get_player_name(i)
        won, bid = server.tricks_won[i], server.bids[i]
        s_cols[i].caption(f"**P{i+1} {p_n}**: กิน **{won}/{bid}**")

    # 🔔 3. สรุปผลไม้ล่าสุด
    if getattr(server, 'last_trick_summary', None):
        summary = server.last_trick_summary
        with st.expander(f"🔔 **ไม้ล่าสุด:** 🏆 P{summary['winner_idx']+1} ({summary['winner_name']}) ชนะ!", expanded=False):
            for p_i in range(4):
                p_n = get_player_name(p_i)
                cards_str = ", ".join(summary['plays'][p_i])
                win_tag = " 🏆" if p_i == summary['winner_idx'] else ""
                st.write(f"• **{p_n}**: {cards_str}{win_tag}")

    st.divider()

    # 🎯 4. พื้นที่การเล่นหมากในไม้นี้ (บนโต๊ะ)
    leader_n = get_player_name(server.leader)
    st.markdown(f"👑 Leader ไม้นี้: **P{server.leader+1} ({leader_n})**")

    # ถ้ายังมีหมากเล่นอยู่
    if any(len(h) > 0 for h in server.hands):
        
        # 🟢 Action ของผู้เล่น (ดึงขึ้นบนสุดเพื่อความสะดวก)
        if my_role != "Spectator":
            my_hand_indexed = list(enumerate(server.hands[my_p_idx]))

            # ถ้าเราเป็น Leader
            if my_p_idx == server.leader and my_p_idx not in server.current_plays:
                with st.container(border=True):
                    st.subheader("🔥 ถึงตาคุณเปิดหมากนำ (Leader):")
                    leader_hand = server.hands[server.leader]

                    play_options = ["Med (เม็ด - 1 ใบ)"]
                    if can_play_tui(leader_hand): play_options.append("Tui (ตุ่ย - คู่ 2 ใบ)")
                    if can_play_sahoo(leader_hand): play_options.append("Sa-Hoo (ซาฮู้ - ชุด 3 ใบ)")

                    play_type = st.radio("เลือกรูปแบบการลง:", play_options, horizontal=True)
                    type_code = "Med" if "Med" in play_type else ("Tui" if "Tui" in play_type else "Sa-Hoo")

                    if type_code == "Med":
                        sel = st.selectbox("เลือกหมาก:", my_hand_indexed, format_func=lambda x: f"ใบที่ {x[0]+1}: {str(x[1])}")
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = [sel[1]]
                            server.current_play_type = type_code
                            st.rerun()

                    elif type_code == "Tui":
                        tui_pairs = get_available_tuis(leader_hand)
                        sel_idx = st.selectbox("เลือกคู่ตุ่ย:", range(len(tui_pairs)), format_func=lambda idx: f"{tui_pairs[idx][0]} + {tui_pairs[idx][1]}")
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = tui_pairs[sel_idx]
                            server.current_play_type = type_code
                            st.rerun()

                    elif type_code == "Sa-Hoo":
                        sahoo_sets = get_available_sahoos(leader_hand)
                        sel_idx = st.selectbox("เลือกชุดซาฮู้:", range(len(sahoo_sets)), format_func=lambda idx: f"{sahoo_sets[idx][0]}")
                        if st.button("🚀 ลงหมากนำ!", type="primary", use_container_width=True):
                            server.current_plays[server.leader] = sahoo_sets[sel_idx][1]
                            server.current_play_type = type_code
                            st.rerun()

            # ถ้าผู้ตามลงหมาก
            elif server.leader in server.current_plays and my_p_idx not in server.current_plays:
                with st.container(border=True):
                    type_code = server.current_play_type
                    req_count = 1 if type_code == "Med" else (2 if type_code == "Tui" else 3)
                    curr_req = min(req_count, len(server.hands[my_p_idx]))

                    st.subheader(f"🃏 ถึงตาคุณลงหมากตาม (เลือก {curr_req} ใบ):")
                    
                    if curr_req == 1:
                        sel = st.selectbox("เลือกหมาก 1 ใบ:", my_hand_indexed, format_func=lambda x: f"ใบที่ {x[0]+1}: {str(x[1])}")
                        if st.button("✅ ยืนยันลงหมาก", type="primary", use_container_width=True):
                            server.current_plays[my_p_idx] = [sel[1]]
                            st.rerun()
                    else:
                        sel_mult = st.multiselect(
                            f"เลือกให้ครบ {curr_req} ใบ:", 
                            my_hand_indexed, 
                            format_func=lambda x: f"ใบที่ {x[0]+1}: {str(x[1])}", 
                            max_selections=curr_req,
                            key=f"follower_select_{my_p_idx}"
                        )
                        if len(sel_mult) == curr_req:
                            if st.button("✅ ยืนยันลงหมาก", type="primary", use_container_width=True):
                                server.current_plays[my_p_idx] = [item[1] for item in sel_mult]
                                st.rerun()
                        else:
                            st.caption(f"เลือกอีก {curr_req - len(sel_mult)} ใบให้ครบถ้วน")
            elif my_p_idx in server.current_plays:
                st.success("✅ คุณเลือกลงหมากในไม้นี้แล้ว (รอผู้เล่นท่านอื่น...)")
            else:
                st.info(f"⏳ รอ Leader (**P{server.leader+1} {leader_n}**) เปิดหมากก่อน...")

        # 🃏 5. แสดงหมากที่ลงบนโต๊ะปัจจุบัน
        st.write("📌 **หมากที่ลงบนโต๊ะปัจจุบัน:**")
        p_col1, p_col2 = st.columns(2)
        p_cols = [p_col1, p_col2, p_col1, p_col2]

        for i in range(4):
            with p_cols[i]:
                p_n = get_player_name(i)
                if i in server.current_plays:
                    cards_played = ", ".join([str(c) for c in server.current_plays[i]])
                    st.success(f"**P{i+1} ({p_n})**: {cards_played}")
                else:
                    st.warning(f"**P{i+1} ({p_n})**: *ยังไม่ลง*")

        # 🎴 6. ไพ่ในมือของคุณ
        st.divider()
        if my_role != "Spectator":
            with st.expander(f"🎴 ดูไพ่ในมือของคุณ ({len(server.hands[my_p_idx])} ใบ)", expanded=True):
                for idx, card in enumerate(server.hands[my_p_idx]):
                    st.write(f"• ใบที่ {idx+1}: **{str(card)}**")

    else:
        server.phase = "round_summary"
        st.rerun()

# ---------------------------------------------------------
# 🏁 PHASE 3: สรุปผลประจำรอบ (Round Summary)
# ---------------------------------------------------------
elif server.phase == "round_summary":
    st.subheader(f"🏁 จบการแข่งขันรอบที่ {server.round_num}!")
    
    round_results = []
    for i in range(4):
        bid = server.bids[i]
        won = server.tricks_won[i]
        if bid == 0 and won == 0:
            base = 3
        elif bid == won:
            base = bid + 5
        else:
            base = -abs(won - bid)
        
        round_score = base * server.multiplier
        round_results.append(round_score)
        
        p_n = get_player_name(i)
        st.write(f"• **P{i+1} {p_n}**: **{round_score} แต้ม** (เรียก {bid} / กิน {won})")

    if my_role == "P1":
        if st.button("➡️ ไปต่อรอบถัดไป", type="primary", use_container_width=True):
            for i in range(4):
                server.scores[i] += round_results[i]
            
            server.prev_leader = server.leader
            server.round_num += 1
            hands, leader, mult = deal_round(server.prev_leader, is_first_round=False)
            server.hands = hands
            server.leader = leader
            server.current_bidder = leader
            server.multiplier = mult
            server.tricks_won = [0, 0, 0, 0]
            server.bids = [0, 0, 0, 0]
            server.bids_entered = [False, False, False, False]
            server.current_plays = {}
            server.last_trick_summary = None
            server.phase = "bidding"
            st.rerun()
    else:
        st.info("รอ P1 กดไปต่อรอบถัดไป...")