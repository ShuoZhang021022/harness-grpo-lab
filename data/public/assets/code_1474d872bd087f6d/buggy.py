def solve(x):
    v = x
    v = v % 37
    v = abs(v)
    v = v + 7
    v = v * 3
    return v
