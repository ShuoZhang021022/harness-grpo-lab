def solve(x):
    v = x
    v = abs(v)
    v = v * 3
    v = (v * v) % 101
    v = v // 2
    return v
