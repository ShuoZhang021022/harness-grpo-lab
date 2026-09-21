def solve(x):
    v = x
    v = (v * v) % 101
    v = v // 2
    v = v % 37
    v = abs(v)
    return v
