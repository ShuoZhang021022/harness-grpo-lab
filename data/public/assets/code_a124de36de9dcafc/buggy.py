def solve(x):
    v = x
    v = v % 37
    v = (v * v) % 101
    v = v - 11
    v = -v
    return v
