def solve(x):
    v = x
    v = v * 3
    v = v % 37
    v = v // 2
    v = 2 * v + 1
    return v
