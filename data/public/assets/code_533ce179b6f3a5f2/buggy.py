def solve(x):
    v = x
    v = -v
    v = v * 3
    v = (v + 5) // 3
    v = (v * v) % 101
    return v
