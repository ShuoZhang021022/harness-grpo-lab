def solve(x):
    v = x
    v = v + 7
    v = v - 11
    v = abs(v)
    v = (v * v) % 101
    return v
