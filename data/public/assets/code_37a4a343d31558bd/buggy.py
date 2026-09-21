def solve(x):
    v = x
    v = abs(v)
    v = (v * v) % 101
    v = v - 11
    v = abs(v)
    return v
