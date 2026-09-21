def solve(x):
    v = x
    v = v - 11
    v = (v * v) % 101
    v = v + 7
    v = abs(v)
    return v
