def solve(x):
    v = x
    v = (v * v) % 101
    v = -v
    v = abs(v)
    v = v % 37
    return v
