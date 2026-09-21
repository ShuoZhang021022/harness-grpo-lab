def solve(x):
    v = x
    v = abs(v)
    v = (v * v) % 101
    v = v // 2
    v = -v
    return v
