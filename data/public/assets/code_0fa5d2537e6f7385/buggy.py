def solve(x):
    v = x
    v = abs(v)
    v = (v * v) % 101
    v = v - 11
    v = (v * v) % 101
    return v
