def solve(x):
    v = x
    v = abs(v)
    v = -v
    v = v // 2
    v = v % 37
    return v
