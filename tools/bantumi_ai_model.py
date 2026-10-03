"""Model of Bantumi's search (0x2dd3bc..0x2dd698) to compare with the BAICHILD trace."""
import sys, re
class Node:
    __slots__=('side','alpha','beta','best','pits','first','counter','parent')
    def __init__(s): s.alpha=-32000; s.beta=32000; s.best=-32000; s.first=0xe; s.counter=0; s.parent=None

class Search:
    def __init__(self, board, level, hint=False):
        self.board = board          # the live game board (14), read by the capture quirk
        r = Node(); r.pits = list(board)
        if hint: r.side = 3; self.depth = 5
        else:
            r.side = 4; d = level*2-1
            if d == 9: d = 8
            self.depth = d
        self.root = r; self.cur = r; self.chosen = None; self.children = []; self.iters = 0

    def evaluate(self, node, terminal):
        p = node.pits; v = p[13] - p[6]
        if terminal:
            v += sum(p[7:13]) - sum(p[0:6])
            if v > 0: v += 50
            elif v < 0: v -= 50
        if node.side == 3: v = -v
        return self.s16(v)
    @staticmethod
    def s16(v): v &= 0xffff; return v-0x10000 if v >= 0x8000 else v

    def close(self, node, flag):   # 0x2dd214
        parent = node.parent
        if flag or self.depth == 0:
            node.best = self.evaluate(node, flag)
        v = node.best
        if node.side != parent.side: v = self.s16(-v); node.best = v
        m = parent.best
        if v > m:
            m = v; parent.best = v
            if parent is self.root:
                c = parent.first if parent.counter == 0 else parent.counter - 1
                if parent.side == 4: c += 7
                self.chosen = c
        if m > parent.alpha: parent.alpha = m
        self.depth += 1
        return parent

    def first_move(self, node):    # 0x2dd438
        p = node.pits
        if node.side != 3: base, store = 7, 13
        else: base, store = 0, 6
        for ip in range(store, base-1, -1):
            if p[ip] == store - ip: return ip
        best = -1; found = None
        for i in range(base, base+6):
            c = p[i]
            if c != 0 and i + c < store and p[i+c] == 0:
                v = p[13 - (i+c)]
                if v >= best: best = v; found = i
        if found is not None: return found
        for i in range(base, base+6):
            if p[i] > best: best = p[i]; found = i
        return found

    def next_move(self, node):     # 0x2dd554
        if node.first == 0xe:
            m = self.first_move(node)
            node.first = m if node.side != 4 else m - 7
            return m
        i = node.counter; node.counter += 1
        if i == node.first: i += 1; node.counter += 1
        if node.side == 4: i += 7
        return i

    def child(self, parent, pit):  # 0x2dd28e
        self.depth -= 1
        c = Node(); c.parent = parent; c.pits = list(parent.pits)
        n = c.pits[pit]; c.pits[pit] = 0; p = pit
        if parent.side != 3:
            for _ in range(n):
                p += 1
                if p >= 14: p = 0
                elif p == 6: p += 1
                c.pits[p] += 1
            if p == 13:
                c.alpha, c.beta, c.side = parent.alpha, parent.beta, parent.side
            else:
                c.alpha, c.beta = -parent.beta, -parent.alpha; c.side = 3
                if self.board[p] == 1 and p > 6:        # quirk: reads the live board
                    c.pits[6] += c.pits[12-p] + 1; c.pits[12-p] = 0; c.pits[p] = 0   # quirk: credited to the player's store
        else:
            for _ in range(n):
                p += 1
                if p >= 13: p = 0
                c.pits[p] += 1
            if p == 6:
                c.alpha, c.beta, c.side = parent.alpha, parent.beta, parent.side
            else:
                c.alpha, c.beta = -parent.beta, -parent.alpha; c.side = 4
                if c.pits[p] == 1 and p < 6:
                    c.pits[6] += c.pits[12-p] + 1; c.pits[12-p] = 0; c.pits[p] = 0
        self.children.append(pit)
        return c

    def step(self):                # 0x2dd5ac: one tick, 100 iterations; returns True when done
        for _ in range(100):
            self.iters += 1
            node = self.cur
            if self.depth != 0 and node.counter < 6 and node.best < node.beta:
                p = node.pits
                if all(x == 0 for x in p[0:6]) or all(x == 0 for x in p[7:13]):
                    self.cur = self.close(node, 1); continue
                m = self.next_move(node)
                if node.counter > 6: continue
                if p[m] == 0: continue
                self.cur = self.child(node, m); continue
            if node is not self.root:
                self.cur = self.close(node, 0); continue
            return True
        return False

def run(board, level, hint=False):
    s = Search(board, level, hint); ticks = 0
    while not s.step(): ticks += 1
    return s, ticks + 1

if __name__ == '__main__':
    log = sys.argv[1]
    txt = open(log).read()
    inits = re.findall(r'BAIINIT (\d+) level=(\w+) turn=(\w+)(?: pits=(\w+) (\w+) (\w+) (\w+))?', txt)
    blocks = re.split(r'BAIINIT ', txt)[1:]
    for (fr, lvl, turn, a, b, c, d), blk in zip(inits, blocks):
        pits = list(bytes.fromhex(a + b + c + d))
        trace = [int(x, 16) for x in re.findall(r'BAICHILD \d+ pit=(\w+)', blk)]
        done = re.search(r'BAIDONE (\d+) chosen=(\w+)', blk)
        steps = len(re.findall(r'BAISTEP', blk))
        s = Search(pits, int(lvl, 16), hint=(int(turn, 16) == 6)); ticks = 0
        while not s.step(): ticks += 1
        ticks += 1
        n = min(len(trace), len(s.children))
        ok = trace[:n] == s.children[:n]
        print(f"frame {fr} level {int(lvl,16)} turn {turn} pits {pits}: model chose {s.chosen} in {s.iters} iters/{ticks} ticks ({len(s.children)} children); log: {len(trace)} children, {steps} steps, done {done.group(2) if done else None} at {done.group(1) if done else None}; prefix match {ok}")
        if not ok:
            for i in range(n):
                if trace[i] != s.children[i]: print('  first mismatch at', i, trace[i-3:i+3], s.children[i-3:i+3]); break
