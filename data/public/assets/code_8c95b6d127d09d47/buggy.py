def solve(x):
    v = x
    v = (v * v) % 101
    v = (v + 5) // 3
    v = v - 11
    v = -v
    return v
