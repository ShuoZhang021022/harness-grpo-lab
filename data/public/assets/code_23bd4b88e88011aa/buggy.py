def solve(x):
    v = x
    v = v % 37
    v = v + 7
    v = (v * v) % 101
    v = v * 3
    return v
