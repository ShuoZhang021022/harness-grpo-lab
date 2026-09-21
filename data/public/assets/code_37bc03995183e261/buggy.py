def solve(x):
    v = x
    v = v - 11
    v = (v * v) % 101
    v = -v
    v = v // 2
    return v
