def solve(x):
    v = x
    v = abs(v)
    v = abs(v)
    v = (v * v) % 101
    v = v - 11
    return v
