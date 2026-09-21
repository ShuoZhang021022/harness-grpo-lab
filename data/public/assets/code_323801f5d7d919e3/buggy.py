def solve(x):
    v = x
    v = abs(v)
    v = v % 37
    v = v + 7
    v = v // 2
    return v
