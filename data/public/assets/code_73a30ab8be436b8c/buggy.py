def solve(x):
    v = x
    v = abs(v)
    v = v % 37
    v = -v
    v = v * 3
    return v
