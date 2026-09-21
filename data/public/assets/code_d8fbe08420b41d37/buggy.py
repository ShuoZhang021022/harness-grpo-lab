def solve(x):
    v = x
    v = -v
    v = (v * v) % 101
    v = v + 7
    v = (v + 5) // 3
    return v
