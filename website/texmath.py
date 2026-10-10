"""
A small LaTeX-to-MathML converter for the formulas used on the course website.

Browsers render MathML natively, so the site needs no MathJax or KaTeX and loads
nothing from a CDN. Only the subset of LaTeX that the notebooks and pages use is
supported. An unknown command raises TexError, so a typo fails the build instead
of ending up on the page.

    from texmath import tex_to_mathml
    tex_to_mathml(r"\\frac{1}{n}\\sum_{t=1}^{n} x_t", display=True)
"""
import html
import re


class TexError(ValueError):
    pass


SYMBOLS = {
    # relations and arrows
    "approx": "≈", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "neq": "≠", "ne": "≠",
    "in": "∈", "sim": "∼", "propto": "∝", "equiv": "≡", "ll": "≪", "gg": "≫",
    "rightarrow": "→", "to": "→", "leftarrow": "←", "gets": "←", "Rightarrow": "⇒", "mapsto": "↦",
    # binary operators
    "cdot": "⋅", "times": "×", "pm": "±", "odot": "⊙", "oplus": "⊕", "circ": "∘",
    # misc
    "dots": "…", "ldots": "…", "cdots": "⋯", "infty": "∞", "partial": "∂", "nabla": "∇",
    "top": "⊤", "ell": "ℓ", "forall": "∀", "exists": "∃",
    "lVert": "‖", "rVert": "‖", "|": "‖", "{": "{", "}": "}",
    "langle": "⟨", "rangle": "⟩",
}
GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ϵ", "varepsilon": "ε",
    "eta": "η", "theta": "θ", "lambda": "λ", "mu": "μ", "pi": "π", "rho": "ρ", "sigma": "σ",
    "tau": "τ", "phi": "ϕ", "varphi": "φ", "omega": "ω", "Delta": "Δ", "Theta": "Θ",
    "Sigma": "Σ", "Omega": "Ω",
}
BIG_OPS = {"sum": "∑", "prod": "∏"}
FUNCTIONS = {"log", "ln", "exp", "cos", "sin", "tanh", "max", "min", "arg", "softmax", "det"}
LIMIT_FUNCTIONS = {"max", "min"}          # subscripts go below in display style
SPACES = {",": "0.167em", ":": "0.222em", ";": "0.278em", " ": "0.25em", "quad": "1em", "qquad": "2em"}
ACCENTS = {"bar": "¯", "hat": "^", "tilde": "~", "vec": "→"}
SIZED = {"big": "1.2em", "Big": "1.6em", "bigg": "2em", "Bigg": "2.4em"}
RELATIONS = set("=<>≈≤≥≠∈∼∝≡→←⇒↦")
OPENERS = set("([{")

# \mathcal: Mathematical Script capitals, with the letters that live in another Unicode block
_SCRIPT_SPECIAL = {"B": "ℬ", "E": "ℰ", "F": "ℱ", "H": "ℋ", "I": "ℐ", "L": "ℒ", "M": "ℳ", "R": "ℛ"}
_BB = {"R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "C": "ℂ", "E": "𝔼", "P": "ℙ"}

_TOKEN = re.compile(r"""
      (?P<rowsep>\\\\)
    | (?P<cmd>\\[A-Za-z]+)
    | (?P<sym>\\.)
    | (?P<num>\d+(?:\.\d+)?)
    | (?P<space>\s+)
    | (?P<char>.)
""", re.X | re.S)


def _script(ch):
    if ch in _SCRIPT_SPECIAL:
        return _SCRIPT_SPECIAL[ch]
    if "A" <= ch <= "Z":
        return chr(0x1D49C + ord(ch) - ord("A"))
    return ch


class Node:
    """One piece of MathML plus what the spacing rules need to know about it."""

    def __init__(self, xml, kind="ord", text=""):
        self.xml, self.kind, self.text = xml, kind, text


class Parser:
    def __init__(self, tex, display):
        self.src, self.pos, self.display = tex, 0, display

    # ------------------------------------------------------------------ tokens
    def peek(self):
        save = self.pos
        tok = self.next()
        self.pos = save
        return tok

    def next(self):
        while self.pos < len(self.src):
            m = _TOKEN.match(self.src, self.pos)
            self.pos = m.end()
            if m.lastgroup == "space":
                continue
            return m.lastgroup, m.group()
        return None, None

    def raw_group(self):
        """The raw text of the next {...} group (for \\text and \\begin)."""
        while self.pos < len(self.src) and self.src[self.pos].isspace():
            self.pos += 1
        if self.pos >= len(self.src) or self.src[self.pos] != "{":
            raise TexError(f"expected '{{' at position {self.pos} in {self.src!r}")
        depth, start = 0, self.pos + 1
        for i in range(self.pos, len(self.src)):
            if self.src[i] == "{":
                depth += 1
            elif self.src[i] == "}":
                depth -= 1
                if depth == 0:
                    self.pos = i + 1
                    return self.src[start:i]
        raise TexError(f"unbalanced braces in {self.src!r}")

    # ------------------------------------------------------------------ grammar
    def row(self, stop=()):
        """Parse until a stop token. Returns a list of Nodes."""
        nodes = []
        while True:
            kind, tok = self.peek()
            if kind is None or tok in stop:
                return nodes
            self.next()
            if tok in ("^", "_"):
                base = nodes.pop() if nodes else Node("<mrow></mrow>")
                nodes.append(self.scripts(base, tok))
            elif tok == "'":
                base = nodes.pop() if nodes else Node("<mrow></mrow>")
                nodes.append(Node(f"<msup>{base.xml}<mo>′</mo></msup>", base.kind, base.text))
            else:
                nodes.append(self.atom(kind, tok, nodes))

    def group(self):
        """A single token or a braced group, as one MathML element."""
        kind, tok = self.next()
        if kind is None:
            raise TexError(f"unexpected end of {self.src!r}")
        if tok == "{":
            nodes = self.row(stop=("}",))
            self.next()
            return self.join(nodes)
        return self.atom(kind, tok, []).xml

    def scripts(self, base, first):
        sub = sup = None
        tok = first
        while True:
            if tok == "_":
                sub = self.group()
            else:
                sup = self.group()
            kind, nxt = self.peek()
            if nxt in ("^", "_") and ((nxt == "_" and sub is None) or (nxt == "^" and sup is None)):
                self.next()
                tok = nxt
            else:
                break
        limits = self.display and base.kind in ("bigop", "limfunc")
        if sub is not None and sup is not None:
            tag = "munderover" if limits else "msubsup"
            xml = f"<{tag}>{base.xml}{sub}{sup}</{tag}>"
        elif sub is not None:
            tag = "munder" if limits else "msub"
            xml = f"<{tag}>{base.xml}{sub}</{tag}>"
        else:
            tag = "mover" if limits else "msup"
            xml = f"<{tag}>{base.xml}{sup}</{tag}>"
        return Node(xml, base.kind, base.text)

    def atom(self, kind, tok, before):
        if kind == "num":
            return Node(f"<mn>{tok}</mn>")
        if kind == "rowsep":
            raise TexError(r"'\\' is only supported inside \begin{cases}")
        if kind == "char":
            return self.char(tok, before)
        if kind == "sym":
            name = tok[1:]
            if name in SPACES:
                return Node(f'<mspace width="{SPACES[name]}"/>', "space")
            if name == "!":
                return Node("", "space")            # negative thin space: nothing to do in MathML
            if name in SYMBOLS:
                return self.symbol(SYMBOLS[name], before)
            raise TexError(f"unknown command {tok!r} in {self.src!r}")
        return self.command(tok[1:], before)

    def char(self, ch, before):
        if ch == "{":
            nodes = self.row(stop=("}",))
            self.next()
            return Node(self.join(nodes))
        if ch == "}":
            raise TexError(f"unexpected '}}' in {self.src!r}")
        if ch == "&":
            raise TexError(r"'&' is only supported inside \begin{cases}")
        if ch.isalpha():
            return Node(f"<mi>{html.escape(ch)}</mi>")
        if ch == "|":
            return Node('<mo stretchy="false" lspace="0" rspace="0">|</mo>', "bar", "|")
        if ch in "()[]":
            return Node(f'<mo stretchy="false">{ch}</mo>', "open" if ch in OPENERS else "close", ch)
        if ch in "+-":
            shown = "−" if ch == "-" else "+"
            prev = self.last_real(before)
            unary = prev is None or prev.kind in ("rel", "bin", "open", "punct")
            if unary:
                return Node(f'<mo form="prefix" lspace="0" rspace="0">{shown}</mo>', "bin", shown)
            return Node(f"<mo>{shown}</mo>", "bin", shown)
        if ch in ",;":
            return Node(f"<mo>{ch}</mo>", "punct", ch)
        if ch == ".":
            return Node('<mo lspace="0" rspace="0">.</mo>', "punct", ch)
        if ch == ":":
            return Node('<mo lspace="0.1em" rspace="0.278em">:</mo>', "punct", ch)
        if ch == "/":
            return Node('<mo lspace="0.1em" rspace="0.1em">/</mo>', "bin", ch)
        return self.symbol(ch, before)

    def symbol(self, ch, before):
        esc = html.escape(ch)
        if ch in RELATIONS:
            # a relation that opens a group, as in x_{<t}, should not be spaced like a relation
            if self.last_real(before) is None:
                return Node(f'<mo lspace="0" rspace="0">{esc}</mo>', "rel", ch)
            return Node(f"<mo>{esc}</mo>", "rel", ch)
        if ch in "{‖⟨":
            return Node(f'<mo stretchy="false" lspace="0" rspace="0">{esc}</mo>', "open", ch)
        if ch in "}⟩":
            return Node(f'<mo stretchy="false" lspace="0" rspace="0">{esc}</mo>', "close", ch)
        if ch in "⋅×±⊙⊕∘":
            return Node(f"<mo>{esc}</mo>", "bin", ch)
        if ch in "…⋯":
            return Node(f"<mo>{esc}</mo>", "ord", ch)
        if ch in "∞∂∇⊤ℓ∀∃":
            return Node(f"<mi mathvariant=\"normal\">{esc}</mi>")
        return Node(f"<mo>{esc}</mo>", "ord", ch)

    def command(self, name, before):
        if name in GREEK:
            return Node(f"<mi>{GREEK[name]}</mi>")
        if name in SYMBOLS:
            return self.symbol(SYMBOLS[name], before)
        if name in SPACES:
            return Node(f'<mspace width="{SPACES[name]}"/>', "space")
        if name in BIG_OPS:
            big = ' largeop="true" movablelimits="false"' if self.display else ""
            return Node(f"<mo{big}>{BIG_OPS[name]}</mo>", "bigop")
        if name in FUNCTIONS:
            return Node(f"<mi>{name}</mi>", "limfunc" if name in LIMIT_FUNCTIONS else "func")
        if name == "mid":
            return Node('<mo lspace="0.278em" rspace="0.278em">∣</mo>', "rel", "∣")
        if name in ("frac", "dfrac", "tfrac"):
            num, den = self.group(), self.group()
            xml = f"<mfrac>{num}{den}</mfrac>"
            if name == "dfrac":
                xml = f'<mstyle displaystyle="true">{xml}</mstyle>'
            return Node(xml)
        if name == "sqrt":
            return Node(f"<msqrt>{self.group()}</msqrt>")
        if name in ("text", "mathrm", "operatorname", "textbf"):
            raw = self.raw_group()
            if name == "text" or name == "textbf":
                weight = ' style="font-weight:700"' if name == "textbf" else ""
                return Node(f"<mtext{weight}>{html.escape(raw)}</mtext>", "text")
            return Node(f'<mi mathvariant="normal">{html.escape(raw.strip())}</mi>',
                        "func" if name == "operatorname" else "ord")
        if name == "mathcal":
            return Node(f"<mi>{''.join(_script(c) for c in self.raw_group().strip())}</mi>")
        if name == "mathbb":
            return Node(f"<mi mathvariant=\"normal\">{''.join(_BB.get(c, c) for c in self.raw_group().strip())}</mi>")
        if name == "mathbf":
            raw = self.raw_group().strip()
            return Node(f'<mi mathvariant="normal" class="tm-bf">{html.escape(raw)}</mi>')
        if name in ACCENTS:
            return Node(f'<mover accent="true">{self.group()}<mo stretchy="false">{ACCENTS[name]}</mo></mover>')
        if name in SIZED:
            kind, tok = self.next()
            ch = SYMBOLS.get(tok[1:], tok[1:]) if tok.startswith("\\") else tok
            size = SIZED[name]
            return Node(f'<mo stretchy="true" minsize="{size}" maxsize="{size}">{html.escape(ch)}</mo>',
                        "open" if ch in OPENERS else "close", ch)
        if name == "left":
            return self.left_right()
        if name == "begin":
            return self.environment()
        if name == "displaystyle":
            return Node("", "space")
        raise TexError(f"unknown command '\\{name}' in {self.src!r}")

    def delimiter(self):
        kind, tok = self.next()
        if tok is None:
            raise TexError(f"missing delimiter in {self.src!r}")
        if tok == ".":
            return ""
        ch = SYMBOLS.get(tok[1:], tok[1:]) if tok.startswith("\\") else tok
        return f'<mo fence="true" stretchy="true">{html.escape(ch)}</mo>'

    def left_right(self):
        left = self.delimiter()
        inner = self.row(stop=("\\right",))
        self.next()
        right = self.delimiter()
        return Node(f"<mrow>{left}{self.join(inner)}{right}</mrow>", "inner")

    def environment(self):
        env = self.raw_group()
        if env != "cases":
            raise TexError(f"unsupported environment {env!r}")
        rows, cells = [], []
        while True:
            nodes = self.row(stop=("&", "\\\\", "\\end"))
            cells.append(self.join(nodes))
            kind, tok = self.next()
            if tok == "&":
                continue
            rows.append(cells)
            cells = []
            if tok == "\\end":
                self.raw_group()
                break
            if tok is None:
                raise TexError(r"missing \end{cases}")
        body = "".join("<mtr>" + "".join(f'<mtd class="tm-left">{c}</mtd>' for c in r) + "</mtr>" for r in rows)
        return Node(f'<mrow><mo fence="true" stretchy="true">{{</mo><mtable>{body}</mtable></mrow>', "inner")

    # ------------------------------------------------------------------ output
    @staticmethod
    def last_real(nodes):
        for n in reversed(nodes):
            if n.kind != "space":
                return n
        return None

    def join(self, nodes):
        """Concatenate nodes into an <mrow>, adding the thin space that follows log, exp, ..."""
        out = []
        for i, n in enumerate(nodes):
            out.append(n.xml)
            if n.kind in ("func", "limfunc") and i + 1 < len(nodes):
                nxt = nodes[i + 1]
                if nxt.kind not in ("open", "space", "inner", "close", "punct"):
                    out.append('<mspace width="0.167em"/>')
        return "<mrow>" + "".join(out) + "</mrow>"


def tex_to_mathml(tex, display=False):
    """Convert one LaTeX formula (without the $ signs) to a <math> element."""
    p = Parser(tex.strip(), display)
    body = p.join(p.row())
    attrs = ' display="block"' if display else ""
    alt = html.escape(" ".join(tex.split()), quote=True)
    out = f'<math class="tm"{attrs} alttext="{alt}">{body}</math>'
    # the wrapper lets a wide formula scroll sideways on a phone
    return f'<span class="math-block">{out}</span>' if display else out


if __name__ == "__main__":
    import sys
    print(tex_to_mathml(" ".join(sys.argv[1:]) or r"\frac{1}{n}\sum_{t=1}^{n} x_t", display=True))
