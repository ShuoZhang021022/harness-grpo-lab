def solve(x):
    v = x
    v = (v * v) % 101
    v = (v * v) % 101
    v = -v
    v = v - 11
    return v
