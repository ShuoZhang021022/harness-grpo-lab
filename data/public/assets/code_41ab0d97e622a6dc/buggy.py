def solve(x):
    v = x
    v = v - 11
    v = v + 7
    v = v % 37
    v = (v * v) % 101
    return v
