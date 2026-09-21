def solve(x):
    v = x
    v = v // 2
    v = -v
    v = (v * v) % 101
    v = 2 * v + 1
    return v
