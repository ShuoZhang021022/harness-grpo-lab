def solve(x):
    v = x
    v = -v
    v = abs(v)
    v = v % 37
    v = v + 7
    return v
