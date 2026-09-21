def solve(x):
    v = x
    v = 2 * v + 1
    v = v // 2
    v = v % 37
    v = abs(v)
    return v
