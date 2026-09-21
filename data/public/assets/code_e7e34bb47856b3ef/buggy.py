def solve(x):
    v = x
    v = v // 2
    v = abs(v)
    v = (v * v) % 101
    v = abs(v)
    return v
