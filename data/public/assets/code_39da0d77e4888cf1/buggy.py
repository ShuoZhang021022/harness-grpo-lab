def solve(x):
    v = x
    v = (v + 5) // 3
    v = abs(v)
    v = (v * v) % 101
    v = v * 3
    return v
