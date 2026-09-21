def solve(x):
    v = x
    v = abs(v)
    v = -v
    v = v % 37
    v = v - 11
    return v
