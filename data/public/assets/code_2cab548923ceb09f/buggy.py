def solve(x):
    v = x
    v = v % 37
    v = v - 11
    v = v // 2
    v = v % 37
    return v
