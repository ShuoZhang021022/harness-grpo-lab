def solve(x):
    v = x
    v = (v * v) % 101
    v = v + 7
    v = abs(v)
    v = v // 2
    return v
