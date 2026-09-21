def solve(x):
    v = x
    v = (v * v) % 101
    v = -v
    v = v % 37
    v = (v * v) % 101
    return v
