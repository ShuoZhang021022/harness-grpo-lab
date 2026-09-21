def solve(x):
    v = x
    v = v // 2
    v = abs(v)
    v = v % 37
    v = v * 3
    return v
