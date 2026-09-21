def solve(x):
    v = x
    v = v % 37
    v = v - 11
    v = (v + 5) // 3
    v = -v
    return v
