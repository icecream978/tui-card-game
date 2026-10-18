import random

RANK_ORDER = ["Jut", "Phao", "Ma", "Rua", "Chang", "Bin", "Tee"]
RANK_VALUE = {name: i for i, name in enumerate(RANK_ORDER)}
COLOR_VALUE = {"Black": 0, "Red": 1}
RANK_COUNTS = {"Tee": 1, "Bin": 2, "Chang": 2, "Rua": 2, "Ma": 2, "Phao": 2, "Jut": 5}

class Piece:
    __slots__ = ("rank", "color")
    def __init__(self, rank, color):
        self.rank = rank
        self.color = color
    def __repr__(self):
        color_th = "🔴" if self.color == "Red" else "⚫"
        return f"{color_th}{self.rank}"
    def value(self):
        return (RANK_VALUE[self.rank], COLOR_VALUE[self.color])
    def is_high(self):
        return RANK_VALUE[self.rank] >= RANK_VALUE["Chang"]
    def key(self):
        return (self.rank, self.color)

    def __eq__(self, other):
        if isinstance(other, Piece):
            return self.key() == other.key()
        return False

    def __hash__(self):
        return hash(self.key())

def build_deck():
    deck = []
    for color in ("Red", "Black"):
        for rank, count in RANK_COUNTS.items():
            for _ in range(count):
                deck.append(Piece(rank, color))
    return deck

SAHOO_SETS = {
    "BigRed": {("Tee", "Red"), ("Bin", "Red"), ("Chang", "Red")},
    "BigBlack": {("Tee", "Black"), ("Bin", "Black"), ("Chang", "Black")},
    "SmallRed": {("Rua", "Red"), ("Ma", "Red"), ("Phao", "Red")},
    "SmallBlack": {("Rua", "Black"), ("Ma", "Black"), ("Phao", "Black")},
}
SAHOO_STRENGTH = {"BigRed": 4, "BigBlack": 3, "SmallRed": 2, "SmallBlack": 1}

def match_sahoo(pieces):
    if len(pieces) != 3:
        return None
    keys = {p.key() for p in pieces}
    for name, s in SAHOO_SETS.items():
        if keys == s:
            return name
    return None

def match_tui(pieces):
    if len(pieces) != 2:
        return False
    return pieces[0].key() == pieces[1].key()

def can_play_tui(hand):
    keys = [p.key() for p in hand]
    return len(keys) != len(set(keys))

def can_play_sahoo(hand):
    keys = {p.key() for p in hand}
    for s in SAHOO_SETS.values():
        if s.issubset(keys):
            return True
    return False

def get_available_tuis(hand):
    keys = [p.key() for p in hand]
    pairs = []
    seen = set()
    for p in hand:
        k = p.key()
        if keys.count(k) >= 2 and k not in seen:
            seen.add(k)
            matching = [x for x in hand if x.key() == k][:2]
            pairs.append(matching)
    return pairs

def get_available_sahoos(hand):
    keys = {p.key() for p in hand}
    sets_found = []
    for name, s in SAHOO_SETS.items():
        if s.issubset(keys):
            needed = list(s)
            play = []
            for p in hand:
                if p.key() in needed:
                    play.append(p)
                    needed.remove(p.key())
            sets_found.append((name, play))
    return sets_found

# ---------------------------------------------------------
# ชุดหมากเพิ่มเติม: จุก / ฮู้ขยาย
# ---------------------------------------------------------
from collections import Counter
from itertools import combinations

SAHOO_TH = {"BigRed": "ใหญ่แดง", "BigBlack": "ใหญ่ดำ", "SmallRed": "เล็กแดง", "SmallBlack": "เล็กดำ"}
RANK_TH = {"Tee": "ตี่", "Bin": "บิน", "Chang": "ช้าง", "Rua": "เรือ", "Ma": "ม้า", "Phao": "เผ่า", "Jut": "จุก"}
# ยศในแต่ละชุดซาฮู้ เช่น BigRed -> {Tee:1, Bin:1, Chang:1}
SAHOO_BASE = {name: Counter(r for r, _c in st) for name, st in SAHOO_SETS.items()}

def _same_color(pieces):
    return len({p.color for p in pieces}) == 1

def match_jut_group(pieces, n):
    """จุกสีเดียวกัน n ใบ (ซาจุก=3, โฟจุก=4, ไฟฟ์จุก=5)"""
    return len(pieces) == n and all(p.rank == "Jut" for p in pieces) and _same_color(pieces)

def _sahoo_with_extras(pieces, n_extra):
    """ซาฮู้ (ใหญ่/เล็ก) + ใบเพิ่ม n_extra ใบ สีเดียวกัน โดยใบเพิ่มต้องเป็นยศในชุดนั้น
    คืนค่า (ชื่อชุด, [ยศใบเพิ่ม]) หรือ None"""
    if len(pieces) != 3 + n_extra or not _same_color(pieces):
        return None
    color = pieces[0].color
    c = Counter(p.rank for p in pieces)
    for name, st in SAHOO_SETS.items():
        if next(iter(st))[1] != color:
            continue
        base = SAHOO_BASE[name]
        if any(c[k] < base[k] for k in base):
            continue
        extra = list((c - base).elements())
        if len(extra) == n_extra and len(set(extra)) == n_extra and all(e in base for e in extra):
            return name, extra
    return None

def match_pho_hoo(pieces):
    """ซาฮู้ + ใบเพิ่ม 1 ใบ คืนค่า (ชื่อชุด, ยศใบเพิ่ม) หรือ None"""
    m = _sahoo_with_extras(pieces, 1)
    return (m[0], m[1][0]) if m else None

def match_five_hoo(pieces):
    """ซาฮู้ + ใบเพิ่ม 2 ใบ คืนค่าชื่อชุด หรือ None"""
    m = _sahoo_with_extras(pieces, 2)
    return m[0] if m else None

def match_six_hoo(pieces):
    """ซาฮู้ + ใบเพิ่ม 3 ใบ คืนค่าชื่อชุด หรือ None (เป็นได้เฉพาะฮู้เล็ก = เรือ ม้า เผ่า ครบ 6 ใบ)"""
    m = _sahoo_with_extras(pieces, 3)
    return m[0] if m else None

def validate_play(play_type, pieces):
    """ตรวจว่าไพ่ที่ Leader เลือกตรงกับประเภทที่ประกาศหรือไม่"""
    if play_type == "Med":
        return len(pieces) == 1
    if play_type == "Tui":
        return match_tui(pieces)
    if play_type == "Sa-Hoo":
        return match_sahoo(pieces) is not None
    if play_type == "Sa-Jut":
        return match_jut_group(pieces, 3)
    if play_type == "Pho-Jut":
        return match_jut_group(pieces, 4)
    if play_type == "Five-Jut":
        return match_jut_group(pieces, 5)
    if play_type == "Pho-Hoo":
        return match_pho_hoo(pieces) is not None
    if play_type == "Five-Hoo":
        return match_five_hoo(pieces) is not None
    if play_type == "Six-Hoo":
        return match_six_hoo(pieces) is not None
    return False

def _of(hand, rank, color):
    return [p for p in hand if p.rank == rank and p.color == color]

def get_available_jut_groups(hand, n):
    res = []
    for color in ("Red", "Black"):
        juts = _of(hand, "Jut", color)
        if len(juts) >= n:
            res.append(juts[:n])
    return res

def get_available_sa_juk(hand):   return get_available_jut_groups(hand, 3)
def get_available_pho_juk(hand):  return get_available_jut_groups(hand, 4)
def get_available_five_juk(hand): return get_available_jut_groups(hand, 5)

def _hoo_options(hand, n_extra):
    res = []
    for name, st in SAHOO_SETS.items():
        color = next(iter(st))[1]
        ranks = sorted((r for r, _c in st), key=lambda r: -RANK_VALUE[r])
        lists = {r: _of(hand, r, color) for r in ranks}
        if any(not lists[r] for r in ranks):
            continue
        base_cards = [lists[r][0] for r in ranks]
        extra_ranks = [r for r in ranks if len(lists[r]) >= 2]
        for combo in combinations(extra_ranks, n_extra):
            cards = base_cards + [lists[r][1] for r in combo]
            label = SAHOO_TH[name] + "".join("+" + RANK_TH[r] for r in combo)
            res.append((label, cards))
    return res

def get_available_pho_hoo(hand):
    return _hoo_options(hand, 1)

def get_available_five_hoo(hand):
    return _hoo_options(hand, 2)

def get_available_six_hoo(hand):
    return _hoo_options(hand, 3)

def deal_new_hands():
    deck = build_deck()
    random.shuffle(deck)
    return [deck[i * 8:(i + 1) * 8] for i in range(4)]

def needs_redeal(hand):
    return not any(p.is_high() for p in hand)

def find_red_tee_holder(hands):
    for i, hand in enumerate(hands):
        for p in hand:
            if p.rank == "Tee" and p.color == "Red":
                return i
    return 0

def deal_step(prev_leader=None, is_first_round=False, multiplier=1, loh_leader=None):
    """แจกไพ่ 1 ครั้ง (ไม่วนซ้ำ) เพื่อให้หน้าเว็บค้างโชว์คนโล้ะก่อนแจกใหม่
    คืนค่า (hands, loh_players, leader, multiplier, loh_leader)
    - มีคนโล้ะ: loh_players ไม่ว่าง, leader=None, multiplier x2, loh_leader=คนโล้ะคนแรก
    - ไม่มีใครโล้ะ: loh_players=[] และ leader พร้อมใช้งาน"""
    hands = deal_new_hands()
    loh_players = [i for i, h in enumerate(hands) if needs_redeal(h)]
    if loh_players:
        return hands, loh_players, None, multiplier * 2, loh_players[0]
    if loh_leader is not None:
        leader = loh_leader
    elif is_first_round:
        leader = find_red_tee_holder(hands)
    else:
        leader = prev_leader if prev_leader is not None else find_red_tee_holder(hands)
    return hands, [], leader, multiplier, loh_leader

def deal_round(prev_leader=None, is_first_round=False):
    multiplier = 1
    current_loh_leader = None
    while True:
        hands = deal_new_hands()
        loh_players = [i for i, h in enumerate(hands) if needs_redeal(h)]
        if not loh_players:
            if current_loh_leader is not None:
                # มีการแจกใหม่เพราะไพ่โล้ะ -> คนโล้ะเป็น Leader (รวมถึงตาแรก)
                leader = current_loh_leader
            elif is_first_round:
                # ตาแรกและไม่มีใครโล้ะ -> คนถือตี่แดงเป็น Leader
                leader = find_red_tee_holder(hands)
            else:
                leader = prev_leader if prev_leader is not None else find_red_tee_holder(hands)
            return hands, leader, multiplier
        else:
            current_loh_leader = loh_players[0]
            multiplier *= 2

def resolve_trick(plays, play_type, leader):
    valid_candidates = []
    for p_idx, pieces in plays.items():
        turn_priority = (4 - (p_idx - leader) % 4)
        if play_type == "Med":
            score = (pieces[0].value()[0], pieces[0].value()[1], turn_priority)
            valid_candidates.append((score, p_idx))
        elif play_type == "Tui" and match_tui(pieces):
            score = (pieces[0].value()[0], pieces[0].value()[1], turn_priority)
            valid_candidates.append((score, p_idx))
        elif play_type == "Sa-Hoo":
            s_name = match_sahoo(pieces)
            if s_name:
                score = (SAHOO_STRENGTH[s_name], turn_priority)
                valid_candidates.append((score, p_idx))
        elif play_type in ("Sa-Jut", "Pho-Jut", "Five-Jut"):
            n = {"Sa-Jut": 3, "Pho-Jut": 4, "Five-Jut": 5}[play_type]
            if match_jut_group(pieces, n):
                # เทียบกันที่สี (แดง > ดำ) แล้วดูลำดับการลง
                score = (COLOR_VALUE[pieces[0].color], turn_priority)
                valid_candidates.append((score, p_idx))
        elif play_type == "Pho-Hoo":
            m = match_pho_hoo(pieces)
            if m:
                name, extra = m
                # ความแรงของชุด (ใหญ่แดง > ใหญ่ดำ > เล็กแดง > เล็กดำ) แล้วยศใบเพิ่ม แล้วลำดับการลง
                score = (SAHOO_STRENGTH[name], RANK_VALUE[extra], turn_priority)
                valid_candidates.append((score, p_idx))
        elif play_type == "Five-Hoo":
            name = match_five_hoo(pieces)
            if name:
                score = (SAHOO_STRENGTH[name], turn_priority)
                valid_candidates.append((score, p_idx))
        elif play_type == "Six-Hoo":
            name = match_six_hoo(pieces)
            if name:
                score = (SAHOO_STRENGTH[name], turn_priority)
                valid_candidates.append((score, p_idx))

    if valid_candidates:
        # 📌 แก้ไขแล้ว: เพิ่มคำว่า lambda เพื่อให้เรียงลำดับได้อย่างถูกต้อง
        valid_candidates.sort(key=lambda x: x[0], reverse=True)
        return valid_candidates[0][1]
    return leader