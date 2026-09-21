def solve(x):
    v = x
    v = (v * v) % 101
    v = v - 11
    v = v * 3
    v = v - 11
    return v
