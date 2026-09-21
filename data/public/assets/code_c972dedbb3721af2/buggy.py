def solve(x):
    v = x
    v = -v
    v = v % 37
    v = v * 3
    v = v // 2
    return v
