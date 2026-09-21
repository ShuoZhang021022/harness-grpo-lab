def solve(x):
    v = x
    v = -v
    v = (v * v) % 101
    v = v - 11
    v = v % 37
    return v
