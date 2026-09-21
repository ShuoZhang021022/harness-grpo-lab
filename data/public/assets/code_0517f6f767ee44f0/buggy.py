def solve(x):
    v = x
    v = v - 11
    v = abs(v)
    v = v % 37
    v = (v * v) % 101
    return v
