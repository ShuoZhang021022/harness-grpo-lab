def solve(x):
    v = x
    v = v - 11
    v = abs(v)
    v = v % 37
    v = v // 2
    return v
