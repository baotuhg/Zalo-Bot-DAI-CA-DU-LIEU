r"""
Chuyển đổi công thức Toán học & KHTN (Hóa học, Vật lý) từ định dạng LaTeX/Markdown
sang ký tự Unicode tương thích 100% với ứng dụng Zalo (Mobile & Desktop).
Học tập và tối ưu từ module zalo-math của 2anh-zalo-bot.
"""

import re

SUPERSCRIPT = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ', 'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ', 'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
}

SUBSCRIPT = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ', 'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
    'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ', 'v': 'ᵥ', 'x': 'ₓ',
}

SYMBOLS = {
    # Mũi tên & suy luận
    'rightarrow': '→', 'to': '→', 'leftarrow': '←', 'gets': '←', 'leftrightarrow': '↔',
    'Rightarrow': '⇒', 'implies': '⇒', 'Leftarrow': '⇐', 'Leftrightarrow': '⇔', 'iff': '⇔',
    # So sánh & phép tính
    'le': '≤', 'leq': '≤', 'ge': '≥', 'geq': '≥', 'ne': '≠', 'neq': '≠', 'pm': '±', 'mp': '∓',
    'approx': '≈', 'times': '×', 'div': '÷', 'cdot': '·', 'ast': '∗', 'sqrt': '√',
    'sum': '∑', 'prod': '∏', 'int': '∫', 'infty': '∞',
    # Hình học & tập hợp
    'in': '∈', 'notin': '∉', 'subset': '⊂', 'subseteq': '⊆', 'supset': '⊃', 'cap': '∩', 'cup': '∪',
    'angle': '∠', 'perp': '⊥', 'parallel': '∥', 'degree': '°', 'circ': '°', 'prime': '′',
    'therefore': '∴', 'because': '∵', 'Delta': 'Δ', 'delta': 'δ',
    # Ký tự Hy Lạp phổ biến trong Cấp 2
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'theta': 'θ', 'pi': 'π', 'lambda': 'λ', 'omega': 'ω'
}

def to_superscript(text: str) -> str:
    return "".join(SUPERSCRIPT.get(c, c) for c in text)

def to_subscript(text: str) -> str:
    return "".join(SUBSCRIPT.get(c, c) for c in text)

def format_zalo_math(text: str) -> str:
    """
    Chuyển đổi văn bản chứa ký hiệu LaTeX thành Unicode đẹp đẽ trên Zalo.
    """
    if not text:
        return ""

    out = text

    # 1. Gỡ bỏ dấu bọc $...$ hoặc $$...$$ của LaTeX trước
    out = re.sub(r'\$\$([^\$]+)\$\$', r'\1', out)
    out = re.sub(r'\$([^\$]+)\$', r'\1', out)
    out = re.sub(r'\\\(([^\)]+)\\\)', r'\1', out)
    out = re.sub(r'\\\[([^\]]+)\\\]', r'\1', out)

    # 1.1 Ký hiệu góc độ: 60^\circ hoặc 60^{\circ} -> 60°
    out = re.sub(r'\^\{\\circ\}|\^\\circ', '°', out)

    # 2. Chuyển đổi căn bậc hai: \sqrt{...} hoặc \sqrt(...)
    out = re.sub(r'\\sqrt\{([^}]+)\}', r'√(\1)', out)
    out = re.sub(r'\\sqrt([0-9a-zA-Z])', r'√\1', out)

    # 3. Chuyển đổi phân số: \frac{a}{b} -> (a)/(b)
    out = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', out)

    # 4. Chuyển đổi lũy thừa mũ: x^{2} hoặc x^2 hoặc x^{n+1}
    def replace_sup(match):
        base = match.group(1)
        exp = match.group(2)
        return f"{base}{to_superscript(exp)}"

    out = re.sub(r'([a-zA-Z0-9\)])\^\{([^}]+)\}', replace_sup, out)
    out = re.sub(r'([a-zA-Z0-9\)])\^([0-9a-zA-Z\+\-])', replace_sup, out)

    # 5. Chuyển đổi chỉ số dưới (hóa học & dãy số): H_2O, x_1, x_{12}
    def replace_sub(match):
        base = match.group(1)
        sub = match.group(2)
        return f"{base}{to_subscript(sub)}"

    out = re.sub(r'([a-zA-Z0-9\)])\_\{([^}]+)\}', replace_sub, out)
    out = re.sub(r'([a-zA-Z0-9\)])\_([0-9a-zA-Z\+\-])', replace_sub, out)

    # 6. Thay thế các ký hiệu LaTeX \symbol
    for sym, uni in SYMBOLS.items():
        out = re.sub(rf'\\{sym}(?![A-Za-z])', uni, out)

    # 7. Dọn dẹp khoảng trắng dư thừa quanh phép toán
    out = out.replace('\\cdot', '·').replace('\\times', '×')

    return out
