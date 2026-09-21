def solve(x):
    v = x
    v = abs(v)
    v = v % 37
    v = v + 7
    v = 2 * v + 1
    return v
