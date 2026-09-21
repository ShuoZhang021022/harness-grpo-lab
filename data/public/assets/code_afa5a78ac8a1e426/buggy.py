def solve(x):
    v = x
    v = v - 11
    v = -v
    v = v * 3
    v = (v * v) % 101
    return v
