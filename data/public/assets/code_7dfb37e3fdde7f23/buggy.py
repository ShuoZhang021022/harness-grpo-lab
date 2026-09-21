def solve(x):
    v = x
    v = abs(v)
    v = 2 * v + 1
    v = v % 37
    v = v * 3
    return v
