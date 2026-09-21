def solve(x):
    v = x
    v = v % 37
    v = v - 11
    v = -v
    v = (v * v) % 101
    return v
