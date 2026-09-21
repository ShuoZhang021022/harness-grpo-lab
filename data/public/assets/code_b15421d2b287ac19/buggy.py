def solve(x):
    v = x
    v = v + 7
    v = -v
    v = (v * v) % 101
    v = v // 2
    return v
