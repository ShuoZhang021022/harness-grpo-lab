def solve(x):
    v = x
    v = v // 2
    v = v % 37
    v = abs(v)
    v = v - 11
    return v
