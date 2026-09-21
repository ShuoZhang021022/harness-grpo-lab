def solve(x):
    v = x
    v = v - 11
    v = (v * v) % 101
    v = abs(v)
    v = v + 7
    return v
