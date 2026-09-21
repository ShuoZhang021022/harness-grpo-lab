def solve(x):
    v = x
    v = abs(v)
    v = v // 2
    v = (v * v) % 101
    v = abs(v)
    return v
