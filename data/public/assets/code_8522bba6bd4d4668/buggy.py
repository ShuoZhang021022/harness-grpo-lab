def solve(x):
    v = x
    v = v % 37
    v = v // 2
    v = v // 2
    v = -v
    return v
