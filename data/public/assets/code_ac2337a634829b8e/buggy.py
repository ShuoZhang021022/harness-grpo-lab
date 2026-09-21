def solve(x):
    v = x
    v = (v * v) % 101
    v = v // 2
    v = abs(v)
    v = v - 11
    return v
