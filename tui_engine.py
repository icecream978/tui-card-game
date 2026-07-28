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

def deal_new_hands():
    deck = build_deck()
    random.shuffle(deck)
    return [deck[i * 8:(i + 1) * 8] for i in range(4)]

def needs_redeal(hand):
    return not any(p.is_high() for p in hand)

def find_black_tee_holder(hands):
    for i, hand in enumerate(hands):
        for p in hand:
            if p.rank == "Tee" and p.color == "Black":
                return i
    return 0

def deal_round(prev_leader=None, is_first_round=False):
    multiplier = 1
    current_loh_leader = None
    while True:
        hands = deal_new_hands()
        loh_players = [i for i, h in enumerate(hands) if needs_redeal(h)]
        if not loh_players:
            if is_first_round:
                leader = find_black_tee_holder(hands)
            elif current_loh_leader is not None:
                leader = current_loh_leader
            else:
                leader = prev_leader if prev_leader is not None else find_black_tee_holder(hands)
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

    if valid_candidates:
        # 📌 แก้ไขแล้ว: เพิ่มคำว่า lambda เพื่อให้เรียงลำดับได้อย่างถูกต้อง
        valid_candidates.sort(key=lambda x: x[0], reverse=True)
        return valid_candidates[0][1]
    return leader