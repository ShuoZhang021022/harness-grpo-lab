def solve(x):
    v = x
    v = v // 2
    v = -v
    v = v % 37
    v = 2 * v + 1
    return v
