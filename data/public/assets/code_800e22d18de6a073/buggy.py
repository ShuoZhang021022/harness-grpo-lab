def solve(x):
    v = x
    v = v * 3
    v = (v * v) % 101
    v = (v * v) % 101
    v = v + 7
    return v
