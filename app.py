import streamlit as st
import random
import time
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
    .block-container { padding-top: 0.6rem; padding-bottom: 0.6rem; padding-left: 0.4rem; padding-right: 0.4rem; }
    .stButton > button { border-radius: 8px; padding: 2px 5px !important; font-size: 13px !important; font-weight: bold; width: 100%; }
    div[data-testid="stSidebarNav"] { display: none; }
    div[data-testid="stHorizontalBlock"] { gap: 0.2rem; }
    .stAlert { padding: 4px 8px !important; margin-bottom: 4px !important; }
    hr { margin: 6px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🇹🇭 แปลภาษายศหมากไทย (เผ่า, เรือ, ม้า)
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

my_id = st.session_state.my_id

# ตรวจสอบการส่งข้อมูลการเล่นหมากผ่าน URL Query Parameters
query_params = st.query_params
played_indices_from_js = None
if "play_action" in query_params:
    try:
        raw_val = query_params["play_action"]
        played_indices_from_js = [int(x) for x in raw_val.split(",") if x.strip().isdigit()]
    except Exception:
        pass
    st.query_params.clear()

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

# Header แบบย่อปุ่มเหลือแค่อิโมจิ
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
# 🎴 Drag-and-Drop Card Component (4 หมากต่อ 1 แถว)
# ---------------------------------------------------------
def render_drag_and_drop_hand(hand, req_cnt=1, disabled=False):
    cards_payload = []
    for idx, c in enumerate(hand):
        cards_payload.append({
            "idx": idx,
            "label": RANK_THAI.get(c.rank, c.rank),
            "symbol": "🔴" if c.color == "Red" else "⚫",
            "is_red": c.color == "Red"
        })

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        * {{ box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; user-select: none; }}
        body {{ margin: 0; padding: 2px; background: transparent; }}
        
        /* Dropzone พื้นที่ลากไพ่มาวาง */
        .drop-zone {{
            border: 2px dashed #9E9E9E;
            border-radius: 8px;
            padding: 8px;
            text-align: center;
            font-size: 13px;
            font-weight: bold;
            color: #555;
            background: #FAFAFA;
            margin-bottom: 8px;
            transition: all 0.2s;
        }}
        .drop-zone.hover {{ border-color: #2196F3; background: #E3F2FD; color: #0D47A1; }}

        /* Card Grid: 1 แถวใส่ 4 หมากพอดี */
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
        }}

        .card-item {{
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
        }}
        .card-item.red {{ color: #D32F2F; border-color: #EF9A9A; background-color: #FFEBEE; }}
        .card-item.black {{ color: #212121; border-color: #B0BEC5; background-color: #ECEFF1; }}
        .card-item.selected {{ border: 2.5px solid #1976D2; box-shadow: 0 0 6px rgba(25, 118, 210, 0.6); transform: translateY(-3px); }}
        .card-item.dragging {{ opacity: 0.4; }}

        .play-btn {{
            width: 100%;
            margin-top: 8px;
            padding: 8px;
            background-color: #1976D2;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
            cursor: pointer;
        }}
        .play-btn:disabled {{ background-color: #B0BEC5; cursor: not-allowed; }}
    </style>
    </head>
    <body>

    <div id="drop-zone" class="drop-zone">
        🎯 ลากไพ่มาวางที่นี่ หรือ แตะเลือก ({req_cnt} ใบ)
    </div>

    <div id="card-grid" class="card-grid"></div>

    <button id="submit-btn" class="play-btn" disabled onclick="submitPlay()">🚀 ลงหมากที่เลือก</button>

    <script>
        let cardsData = {json.dumps(cards_payload)};
        let reqCount = {req_cnt};
        let isDisabled = {str(disabled).lower()};
        let selectedIndices = [];

        function renderCards() {{
            const grid = document.getElementById('card-grid');
            grid.innerHTML = '';

            cardsData.forEach((card, idx) => {{
                const el = document.createElement('div');
                el.className = `card-item ${{card.is_red ? 'red' : 'black'}} ${{selectedIndices.includes(idx) ? 'selected' : ''}}`;
                el.setAttribute('draggable', isDisabled ? 'false' : 'true');
                el.dataset.index = idx;
                el.innerHTML = `<div>${{card.symbol}}${{card.label}}</div>`;

                // Tap / Click to select
                el.onclick = () => {{
                    if (isDisabled) return;
                    if (selectedIndices.includes(idx)) {{
                        selectedIndices = selectedIndices.filter(i => i !== idx);
                    }} else {{
                        if (selectedIndices.length < reqCount) {{
                            selectedIndices.push(idx);
                        }} else if (reqCount === 1) {{
                            selectedIndices = [idx];
                        }}
                    }}
                    renderCards();
                }};

                // HTML5 Drag & Drop
                el.ondragstart = (e) => {{
                    e.dataTransfer.setData('text/plain', idx);
                    el.classList.add('dragging');
                }};
                el.ondragend = () => el.classList.remove('dragging');

                el.ondragover = (e) => e.preventDefault();
                el.ondrop = (e) => {{
                    e.preventDefault();
                    const srcIdx = parseInt(e.dataTransfer.getData('text/plain'));
                    if (!isNaN(srcIdx) && srcIdx !== idx) {{
                        // สลับตำแหน่งไพ่จากการลากจัดเรียง
                        const temp = cardsData[srcIdx];
                        cardsData[srcIdx] = cardsData[idx];
                        cardsData[idx] = temp;
                        selectedIndices = [];
                        renderCards();
                    }}
                }};

                grid.appendChild(el);
            }});

            const btn = document.getElementById('submit-btn');
            btn.disabled = isDisabled || (selectedIndices.length !== reqCount);
            btn.innerText = `🚀 ลงหมากที่เลือก (${{selectedIndices.length}}/${{reqCount}})`;
        }}

        // Dropzone drag over / drop
        const dz = document.getElementById('drop-zone');
        dz.ondragover = (e) => {{ e.preventDefault(); dz.classList.add('hover'); }};
        dz.ondragleave = () => dz.classList.remove('hover');
        dz.ondrop = (e) => {{
            e.preventDefault();
            dz.classList.remove('hover');
            const srcIdx = parseInt(e.dataTransfer.getData('text/plain'));
            if (!isNaN(srcIdx) && !selectedIndices.includes(srcIdx) && selectedIndices.length < reqCount) {{
                selectedIndices.push(srcIdx);
                renderCards();
            }}
        }};

        // Touch Drag & Drop support สำหรับจอมือถือ
        let touchSrcIdx = null;
        const grid = document.getElementById('card-grid');
        grid.addEventListener('touchstart', (e) => {{
            const cardEl = e.target.closest('.card-item');
            if (cardEl) {{
                touchSrcIdx = parseInt(cardEl.dataset.index);
            }}
        }}, {{passive: true}});

        grid.addEventListener('touchend', (e) => {{
            if (touchSrcIdx !== null) {{
                const touch = e.changedTouches[0];
                const targetEl = document.elementFromPoint(touch.clientX, touch.clientY)?.closest('.card-item');
                if (targetEl) {{
                    const targetIdx = parseInt(targetEl.dataset.index);
                    if (!isNaN(targetIdx) && targetIdx !== touchSrcIdx) {{
                        const temp = cardsData[touchSrcIdx];
                        cardsData[touchSrcIdx] = cardsData[targetIdx];
                        cardsData[targetIdx] = temp;
                        selectedIndices = [];
                        renderCards();
                    }}
                }}
                touchSrcIdx = null;
            }}
        }});

        function submitPlay() {{
            if (selectedIndices.length === reqCount && !isDisabled) {{
                const parentUrl = new URL(window.parent.location.href);
                parentUrl.searchParams.set('play_action', selectedIndices.join(','));
                parentUrl.searchParams.set('ts', Date.now());
                window.parent.location.href = parentUrl.toString();
            }}
        }}

        renderCards();
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=210)

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

    # สถานะการบิด
    with st.expander("📊 ดูการบิดแต้มเพื่อน", expanded=False):
        for idx, p_idx in enumerate(bid_order):
            p_n = get_player_name(p_idx)
            status = f"{server.bids[p_idx]} แต้ม" if server.bids_entered[p_idx] else ("กำลังบิด..." if p_idx == server.current_bidder else "รอคิว")
            st.write(f"• P{p_idx+1} ({p_n}): {status}")

    if my_role != "Spectator":
        st.caption("🎴 ไพ่ในมือคุณ (จัดเรียงลากสลับตำแหน่งได้):")
        render_drag_and_drop_hand(server.hands[my_p_idx], req_cnt=1, disabled=True)

    if all(server.bids_entered):
        server.phase = "playing"
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
        st.rerun()

    st.caption(f"🃏 รอบ {server.round_num}/15 | Leader: **P{server.leader+1} ({get_player_name(server.leader)})**")

    # 📜 สรุปไม้ล่าสุด (นำกลับมาตามที่ขอ: ใครลงอะไร ใครได้กิน)
    if getattr(server, 'last_trick_summary', None):
        st.markdown("📜 **ไม้ล่าสุด (ใครลงอะไร / ใครได้กิน):**")
        s = server.last_trick_summary
        cols_summary = st.columns(4)
        for i in range(4):
            played_cards = s["plays"].get(i, [])
            cards_str = " ".join([card_label(c) for c in played_cards]) if played_cards else "ไม่ได้ลง"
            p_name = get_player_name(i)
            if i == s["winner_idx"]:
                cols_summary[i].success(f"🏆 **P{i+1}**\n\n{cards_str}\n\n*(กิน +{s['cards_won']})*")
            else:
                cols_summary[i].info(f"👤 P{i+1}\n\n{cards_str}")
        st.divider()

    # แต้มและการกินแบบย่อ
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

                # ประมวลผลเมื่อกดส่งหมากจาก JS Drag Component
                if played_indices_from_js is not None and len(played_indices_from_js) == req_cnt:
                    selected_cards = [my_hand[i] for i in played_indices_from_js if i < len(my_hand)]
                    if len(selected_cards) == req_cnt:
                        ptype_map = {"เม็ด": "Med", "ตุ่ย": "Tui", "ซาฮู้": "Sa-Hoo", "ซาจุก": "Sa-Jut", "โฟจุก": "Pho-Jut", "โฟฮู้": "Pho-Hoo", "ไฟฟ์ฮู้": "Five-Hoo"}
                        matched_type = "Med"
                        for k, v in ptype_map.items():
                            if k in play_type: matched_type = v; break

                        server.current_plays[server.leader] = selected_cards
                        server.current_play_type = matched_type
                        st.rerun()

                render_drag_and_drop_hand(my_hand, req_cnt=req_cnt, disabled=False)

            # Follower ลงตาม
            elif server.leader in server.current_plays and my_p_idx not in server.current_plays:
                curr_req = min(len(server.current_plays[server.leader]), len(my_hand))
                st.write(f"🃏 **ลงหมากตาม (เลือกลาก/แตะ {curr_req} ใบ):**")
                
                if played_indices_from_js is not None and len(played_indices_from_js) == curr_req:
                    selected_cards = [my_hand[i] for i in played_indices_from_js if i < len(my_hand)]
                    if len(selected_cards) == curr_req:
                        server.current_plays[my_p_idx] = selected_cards
                        st.rerun()

                render_drag_and_drop_hand(my_hand, req_cnt=curr_req, disabled=False)

            elif my_p_idx in server.current_plays:
                st.success("✅ คุณลงหมากเรียบร้อย 🔒 (รอคนอื่นลงให้ครบ...)")
                render_drag_and_drop_hand(my_hand, req_cnt=1, disabled=True)
            else:
                st.info(f"⏳ รอ P{server.leader+1} ({get_player_name(server.leader)}) เปิดหมาก...")
                render_drag_and_drop_hand(my_hand, req_cnt=1, disabled=True)

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