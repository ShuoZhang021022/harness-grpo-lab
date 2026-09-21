def solve(x):
    v = x
    v = v + 7
    v = v - 11
    v = (v * v) % 101
    v = -v
    return v
