from core.zalo_math import format_zalo_math

tests = [
    r"Phương trình: $x^2 - 5x + 6 = 0$ có $\Delta = b^2 - 4ac$ và nghiệm $x_1, x_2$.",
    r"Hóa học: Phản ứng $2H_2 + O_2 \rightarrow 2H_2O$ và axit $H_2SO_4$.",
    r"Hình học: Tam giác $ABC$ có $\angle ABC = 60^\circ$ và $AB \perp CD$, $d_1 \parallel d_2$.",
    r"Căn thức & phân số: $\sqrt{x^2 + 1} = \frac{a}{b}$",
]

for t in tests:
    print("Gốc: ", t)
    print("Zalo:", format_zalo_math(t))
    print("-" * 50)
