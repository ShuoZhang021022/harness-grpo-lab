def solve(x):
    v = x
    v = (v * v) % 101
    v = v + 7
    v = v // 2
    v = 2 * v + 1
    return v
