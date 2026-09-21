def solve(x):
    v = x
    v = v % 37
    v = v + 7
    v = v // 2
    v = abs(v)
    return v
