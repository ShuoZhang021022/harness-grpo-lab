def solve(x):
    v = x
    v = v // 2
    v = (v * v) % 101
    v = v // 2
    v = v * 3
    return v
