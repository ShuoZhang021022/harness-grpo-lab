def solve(x):
    v = x
    v = abs(v)
    v = v - 11
    v = v % 37
    v = v * 3
    return v
