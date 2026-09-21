def solve(x):
    v = x
    v = -v
    v = (v * v) % 101
    v = v % 37
    v = v + 7
    return v
