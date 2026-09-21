def solve(x):
    v = x
    v = v % 37
    v = (v + 5) // 3
    v = -v
    v = v - 11
    return v
